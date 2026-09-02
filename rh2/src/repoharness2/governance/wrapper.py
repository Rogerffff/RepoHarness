"""统一 finalize 关口（S1-5）：`finalize_rollout` 是治理层唯一公开入口。

对应设计文档 2 §5.6"载体与执行位置"定案 3/4：

- TrainingEligibilityGate 挂在**两种拓扑共享的必经位置**——rollout 完成之后、
  样本进入任何训练后端 adapter 之前。trainer_native 直调路径同样必须经过
  同一个关口；任何绕过它把样本交给训练后端的实现路径都视为违规；
- EnvServer 出站扫描只是 service_driven 拓扑的第二道防线，不是唯一防线。

本函数把「grade -> project -> scan -> gate」四步固化为一次调用：

    1. grade    执行传入的评分动作（S1-4 manager/queue 的一次 grade），
                拿到 GradingReport；
    2. project  用该 GradingReport 执行传入的投影动作（S1-3
                project_from_slime 或 S1-8 project_from_verifiers），
                拿到 TrajectoryProjection——投影必然晚于评分，因为
                RewardFacts 要引用评分报告的 report_id；
    3. scan     对投影做 public projection 泄漏扫描（projection_scan）；
    4. gate     七维合取判定（gate._evaluate），扫描结论作为
                security_and_leakage 维的事实输入进入报告。

    顺序说明（S1-5 任务原文写作 grade->project->gate->scan；本实现为
    grade->project->scan->gate）：EligibilityReport 是 frozen 的自证对象
    （facts_digest 在构造时锁定），扫描结论要成为 security 维的事实
    就必须先于 gate 装配产出——"先 gate 后 scan"在该 schema 下物理上
    不可实现（事后写入 = 篡改 facts_digest = 校验拒收），故按更严的
    "扫描先行、结论进报告"执行，已记 implementation-notes。

S1-6 编排纪律：**只准调本函数**，不准分别调用 gate / projection_scan 的
内部函数（它们都是模块私有 `_` 前缀；tests/governance 的 API 面测试断言
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
    SandboxCapabilityFacts,
    _evaluate,
)
from repoharness2.governance.projection_scan import (
    ProjectionScanResult,
    _scan_public_projection,
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
    """finalize_rollout 的完整产物：四步的全部 evidence + 资格结论。

    S1-6 消费方式：
    - `eligibility_report` 作为 sidecar 与 Sample 同键落盘，宿主对象只写
      两个白名单派生视图键（eligibility_report_ref / training_eligibility_class，
      值直接取 report.derived_view_*）；
    - `group_repair_signal` 在组装配前转发训练后端（P4）；
    - `projection` / `grading_report` / `scan_result` 原样归档供审计与 parity。
    """

    grading_report: GradingReport = Field(description="第 1 步产物：评分报告。")
    projection: TrajectoryProjection = Field(description="第 2 步产物：中立投影。")
    scan_result: ProjectionScanResult = Field(description="第 3 步产物：泄漏扫描结论。")
    eligibility_report: EligibilityReport = Field(
        description="第 4 步产物：资格判定权威载体。"
    )
    group_repair_signal: GroupRepairSignal = Field(
        description="第 4 步产物：组修复信号（一等暴露，组装配前转发后端）。"
    )

    @model_validator(mode="after")
    def _check_finalized_consistency(self) -> "FinalizedRollout":
        traj = self.projection.trajectory_id
        pairs = {
            "grading_report": self.grading_report.trajectory_id,
            "scan_result": self.scan_result.trajectory_id,
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
    sandbox_capability_facts: SandboxCapabilityFacts | None = None,
    sandbox_capability_facts_required: bool = True,
    sandbox_lease_id: str | None = None,
    report_id: str | None = None,
    created_at_utc: datetime | None = None,
) -> FinalizedRollout:
    """治理层唯一公开入口：grade -> project -> scan -> gate 一次走完。

    参数：
    - grade：无参回调，执行本轨迹的评分（通常包一层
      `lambda: queue.submit(trajectory_id=..., workspace=..., spec=...)`），
      返回 GradingReport（可以是协程）。
    - project：接收第 1 步的 GradingReport，返回本轨迹的
      TrajectoryProjection（可以是协程）。评分先于投影是硬顺序——
      RewardFacts.reward_event_refs 要引用评分报告 id。
    - capture_records：本轨迹全部 GenerationCaptureRecord（A4 sidecar，
      token_provenance 维的事实源）。
    - handshake：staleness 事实（policy_staleness 维的事实源）。**必须显式
      传参**：暂无事实就显式传 None（该维将 fail-closed 失败并降级），
      不给默认值是为了防止编排层"忘了接"被静默当成"没有"。
    - findings：本轨迹的反作弊 finding（executed 级触发 security 维失败）。
    - backpressure_events：评分队列反压事件流（可以混含其他轨迹的事件，
      gate 只取本轨迹的；理由码写进报告，不构成降级）。
    - sandbox_capability_facts / sandbox_capability_facts_required（A3，W1b
      第二段）：security 维的正向 sandbox 能力事实。默认 **required=True**
      （fail-closed：事实缺席 = `sandbox_capability_facts_missing`，非 online）；
      只有 s1_compat 冻结路径显式传 required=False（evidence 如实记
      not_required）。W3b 落地前 formal 路径传 None 是预期形态。
    - sandbox_lease_id（复核修复 #5）：本次 attempt 实际使用的 SandboxLease.lease_id；
      required=True 时必传，能力事实的 lease_id 必须逐字相等（GateInputError）。
    - report_id / created_at_utc：EligibilityReport 的 id 与时间戳；缺省时
      自动生成（id 形如 elig_1a2b3c4d5e6f，时间取当前 UTC）。需要逐字节
      可复现的报告（如 parity 对照）时由调用方显式传入。

    返回 FinalizedRollout；组修复信号在其中一等暴露（P4：S1-6 必须在组
    装配前转发后端）。
    """

    grading_report = await _resolve(grade(), "grade", GradingReport)
    projection = await _resolve(project(grading_report), "project", TrajectoryProjection)
    scan_result = _scan_public_projection(projection)
    outcome: GateOutcome = _evaluate(
        projection=projection,
        grading_report=grading_report,
        capture_records=capture_records,
        scan_result=scan_result,
        findings=findings,
        handshake=handshake,
        backpressure_events=backpressure_events,
        sandbox_capability_facts=sandbox_capability_facts,
        sandbox_capability_facts_required=sandbox_capability_facts_required,
        sandbox_lease_id=sandbox_lease_id,
        report_id=report_id if report_id is not None else f"elig_{uuid.uuid4().hex[:12]}",
        created_at_utc=(
            created_at_utc if created_at_utc is not None else datetime.now(timezone.utc)
        ),
    )
    return FinalizedRollout(
        grading_report=grading_report,
        projection=projection,
        scan_result=scan_result,
        eligibility_report=outcome.report,
        group_repair_signal=outcome.group_repair_signal,
    )
