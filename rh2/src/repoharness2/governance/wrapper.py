"""统一 finalize 关口（S1-5）：`finalize_rollout` 是治理层唯一公开入口。

对应设计文档 2 §5.6"载体与执行位置"定案 3/4：

- TrainingEligibilityGate 挂在**两种拓扑共享的必经位置**——rollout 完成之后、
  样本进入任何训练后端 adapter 之前。trainer_native 直调路径同样必须经过
  同一个关口；任何绕过它把样本交给训练后端的实现路径都视为违规；
- EnvServer 出站扫描只是 service_driven 拓扑的第二道防线，不是唯一防线。

本函数把「grade -> project -> gate」三步固化为一次调用：

    1. grade    执行传入的评分动作（S1-4 manager/queue 的一次 grade），
                拿到 GradingReport；
    2. project  用该 GradingReport 执行传入的投影动作（S1-3
                project_from_slime 或 S1-8 project_from_verifiers），
                拿到 TrajectoryProjection——投影必然晚于评分，因为
                RewardFacts 要引用评分报告的 report_id；
    3. gate     七维合取判定（gate._evaluate）。

    历史第 3 步"scan"（对投影做 public projection 泄漏扫描并作为 security 维事实）
    已按决策包 D2-4（2026-09-04 owner 已批）删除：`TrajectoryProjection` 是 rollout
    结束后的 trainer/offline-export 中立投影，不是模型可见输入，扫描发生在 rollout
    与评分之后、不解引用 token/artifact 内容，测不到 prompt/mount/env/工具输出里的
    泄漏，却会因 `fail_to_pass_bonus` 这类字段名误报丢整组。真模型可见面
    （envpack 的 PublicTaskBundle / RolloutTaskView）的 `scan_for_forbidden_markers`
    整树检查原样保留；hidden/grader 泄漏的主验证改为结构/数据流证据 + canary 反例
    （W3b）。`projection_scan.py` 只留冻结兼容读路径。

S1-6 编排纪律：**只准调本函数**，不准直接调用 gate 的内部函数
（模块私有 `_` 前缀；tests/governance 的 API 面测试断言
`repoharness2.governance` 里唯一公开可调用函数就是 finalize_rollout）。

grade/project 以可调用形式注入而不是直接传对象，是为了把调用**顺序**也
固化在关口里（例如 project 回调拿到的 GradingReport 一定是本次 grade 的
产物，S1-6 无法把两条轨迹的评分与投影接错线——接错线会在 gate 的
trajectory_id 接线检查处当场炸）。两个回调允许是协程函数：评分队列
（GradingQueue.submit）本身是 async 的。
"""

from __future__ import annotations

import inspect
import uuid
from collections.abc import Awaitable, Callable, Sequence
from datetime import datetime, timezone

from pydantic import Field, model_validator

from repoharness2.contracts import (
    AntiCheatFinding,
    BackendHandshake,
    EligibilityReport,
    GenerationCaptureRecord,
    GradingReport,
    StrictModel,
    TrajectoryProjection,
)
from repoharness2.governance.gate import (
    GateInputError,
    GateOutcome,
    GroupRepairSignal,
    _evaluate,
)
from repoharness2.grading.queue import BackpressureEvent

__all__ = [
    "FinalizedRollout",
    "finalize_rollout",
]

# grade / project 两步的回调类型：允许普通函数或协程函数。
GradeFn = Callable[[], GradingReport | Awaitable[GradingReport]]
ProjectFn = Callable[[GradingReport], TrajectoryProjection | Awaitable[TrajectoryProjection]]


class FinalizedRollout(StrictModel):
    """finalize_rollout 的完整产物：三步的全部 evidence + 资格结论。

    S1-6 消费方式：
    - `eligibility_report` 作为 sidecar 与 Sample 同键落盘，宿主对象只写
      两个白名单派生视图键（eligibility_report_ref / training_eligibility_class，
      值直接取 report.derived_view_*）；
    - `group_repair_signal` 在组装配前转发训练后端（P4）；
    - `projection` / `grading_report` 原样归档供审计与 parity。

    本对象是进程内聚合值，不是落盘 schema（sidecar 按四类分别落盘）；历史字段
    `scan_result`（ProjectionScanResult）已随 D2-4 删除，不留 Optional 占位。
    """

    grading_report: GradingReport = Field(description="第 1 步产物：评分报告。")
    projection: TrajectoryProjection = Field(description="第 2 步产物：中立投影。")
    eligibility_report: EligibilityReport = Field(
        description="第 3 步产物：资格判定权威载体。"
    )
    group_repair_signal: GroupRepairSignal = Field(
        description="第 3 步产物：组修复信号（一等暴露，组装配前转发后端）。"
    )

    @model_validator(mode="after")
    def _check_finalized_consistency(self) -> "FinalizedRollout":
        traj = self.projection.trajectory_id
        pairs = {
            "grading_report": self.grading_report.trajectory_id,
            "eligibility_report": self.eligibility_report.trajectory_id,
            "group_repair_signal": self.group_repair_signal.trajectory_id,
        }
        mismatched = {name: value for name, value in pairs.items() if value != traj}
        if mismatched:
            raise ValueError(
                f"FinalizedRollout 各产物 trajectory_id 必须一致（投影={traj}），"
                f"不一致项：{mismatched}。"
            )
        if self.group_repair_signal.report_ref != self.eligibility_report.report_id:
            raise ValueError(
                "group_repair_signal.report_ref 必须指向本次的 eligibility_report.report_id。"
            )
        return self


async def _resolve(value: object, step_name: str, expected_type: type) -> object:
    """执行回调返回值：协程则 await，随后做类型 fail-closed 检查。"""

    if inspect.isawaitable(value):
        value = await value
    if not isinstance(value, expected_type):
        raise GateInputError(
            f"{step_name} 回调必须返回 {expected_type.__name__}，"
            f"得到 {type(value).__name__}（fail-closed：错误类型的产物不进入后续步骤）。"
        )
    return value


async def finalize_rollout(
    *,
    grade: GradeFn,
    project: ProjectFn,
    capture_records: Sequence[GenerationCaptureRecord],
    handshake: BackendHandshake | None,
    findings: Sequence[AntiCheatFinding] = (),
    backpressure_events: Sequence[BackpressureEvent] = (),
    require_real_weight_versions: bool = True,
    report_id: str | None = None,
    created_at_utc: datetime | None = None,
) -> FinalizedRollout:
    """治理层唯一公开入口：grade -> project -> gate 一次走完。

    参数：
    - grade：无参回调，执行本轨迹的评分（通常包一层
      `lambda: queue.submit(trajectory_id=..., workspace=..., spec=...)`），
      返回 GradingReport（可以是协程）。
    - project：接收第 1 步的 GradingReport，返回本轨迹的
      TrajectoryProjection（可以是协程）。评分先于投影是硬顺序——
      RewardFacts.reward_event_refs 要引用评分报告 id。
    - capture_records：本轨迹全部 GenerationCaptureRecord（A4 sidecar，
      token_provenance 维的事实源）。
    - handshake：版本事实（policy_staleness 维的事实源：weight_versions_seen /
      policy_version；staleness_steps 只作观测）。**必须显式传参**：暂无事实就
      显式传 None（该维将 fail-closed 失败并降级），不给默认值是为了防止编排层
      "忘了接"被静默当成"没有"。
    - findings：本轨迹的反作弊 finding（executed 级触发 security 维失败）。
    - backpressure_events：评分队列反压事件流（可以混含其他轨迹的事件，
      gate 只取本轨迹的；理由码写进报告，不构成降级）。
    - require_real_weight_versions：policy_staleness 维的版本契约开关（与
      `SlimeBindingConfig.require_real_weight_versions` 同名同义）。默认 True
      （fail-closed：版本必须全部可解析为十进制 int 且无未来版本，否则
      `staleness_facts_invalid`）；只有 S1 兼容 / 测试路径按其配置传 False，
      允许静态哨兵版本（evidence 如实记 legacy_sentinel_allowed）。formal 链的
      启动校验强制该旗标为 True。
    - report_id / created_at_utc：EligibilityReport 的 id 与时间戳；缺省时
      自动生成（id 形如 elig_1a2b3c4d5e6f，时间取当前 UTC）。需要逐字节
      可复现的报告（如 parity 对照）时由调用方显式传入。

    返回 FinalizedRollout；组修复信号在其中一等暴露（P4：S1-6 必须在组
    装配前转发后端）。
    """

    grading_report = await _resolve(grade(), "grade", GradingReport)
    projection = await _resolve(project(grading_report), "project", TrajectoryProjection)
    outcome: GateOutcome = _evaluate(
        projection=projection,
        grading_report=grading_report,
        capture_records=capture_records,
        findings=findings,
        handshake=handshake,
        backpressure_events=backpressure_events,
        require_real_weight_versions=require_real_weight_versions,
        report_id=report_id if report_id is not None else f"elig_{uuid.uuid4().hex[:12]}",
        created_at_utc=(
            created_at_utc if created_at_utc is not None else datetime.now(timezone.utc)
        ),
    )
    return FinalizedRollout(
        grading_report=grading_report,
        projection=projection,
        eligibility_report=outcome.report,
        group_repair_signal=outcome.group_repair_signal,
    )
