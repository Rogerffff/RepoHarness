"""W2a 中立 termination 事实记录（A5 未拍板前的唯一实现面）。

06 计划 A5 的"批准前边界"（2026-09-02 D0 拍板原文）：**代码只实现
termination 事实与观测；A5 未拍板前不实现任何新的 admission / gradient
mask / 补采语义**。本模块就是那条边界的落点：

- 只记**事实**（发生了什么、何时、哪些收尾条件成立），不做 disposition
  （该不该训练/该不该补采/记不记负样本——那些是 D1/C 的决策，未注入前
  下游按 W1b 的 fail-fast 纪律处理）。
- 计时是**粗粒度单区间**（资源占用起点 → 终止时刻，A5-c"episode 计时起点
  改为资源占用"），刻意不建计时归因系统——A5-b 复核已裁定：粗粒度计时
  无法区分"590s 排队 + 10s 行动"与"600s 真实行动"，不为无实验需求的
  选项建设归因基建。
- `termination_kind` 复用 contracts/fa_runtime.py 的五族封闭枚举（D1a
  已批语义，本模块不新增枚举值）；"触发者是 policy-owned horizon 还是
  hard wall"以布尔事实冗余存储，validator 钉死与 kind 五族划分一致——
  矛盾事实（如 hard_wall_timeout 却声称 policy horizon 触发）不可表示。
- `environment_package_digest` + `task_id` 作 join 锚随记录走（与
  training_view.py 的 digest 贯穿同一纪律），后续 eligibility/baseline
  join 用它对账，不靠隐式上下文。
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from repoharness2.contracts._base import (
    NonEmptyStr,
    Sha256Digest,
    StrictModel,
)
from repoharness2.contracts.fa_runtime import (
    TERMINATION_KINDS_POLICY_HORIZON,
    TERMINATION_KINDS_WATCHDOG,
    TerminationKind,
)


class TerminationFactsV1(StrictModel):
    """一次 rollout 尝试的终止事实（中立、record-only）。

    字段全部是"已发生的可观测事实"：布尔收尾条件 + 粗粒度计时区间 +
    终止 trigger。**没有** disposition / admission / reward / mask 字段，
    也没有任何计算处置的方法——A5 拍板后处置逻辑在别的模块消费本记录。
    """

    schema_id: Literal["rh2.termination_facts.v1"] = Field(
        default="rh2.termination_facts.v1", description="schema 判别字段。"
    )
    task_id: NonEmptyStr = Field(
        description='source-qualified 任务主键（"<source>::<instance_id>"，join 锚之一）。'
    )
    environment_package_digest: Sha256Digest = Field(
        description="EnvironmentPackageV1.digest()——与 typed view 同一贯穿锚。"
    )
    termination_kind: TerminationKind = Field(
        description="终止 trigger（contracts/fa_runtime.py 五族封闭枚举，不新增值）。"
    )
    resource_occupancy_started_unix_s: float = Field(
        ge=0.0,
        description="粗粒度计时区间起点：episode 开始占用资源的 unix 秒"
        "（A5-c：计时起点 = 资源占用，不是首 token）。",
    )
    terminated_unix_s: float = Field(
        ge=0.0,
        description="粗粒度计时区间终点：终止时刻的 unix 秒。只此一个区间，"
        "不做排队/推理/沙箱的分段归因。",
    )
    capture_closed: bool = Field(
        description="轨迹 capture 是否闭合（终止后无未落账的模型调用/工具事件）。"
    )
    execution_scope_quiescent: bool = Field(
        description="execution scope 是否 quiescent（沙箱内无残留写手，屏障已过）。"
    )
    canonical_frozen_patch_formed: bool = Field(
        description="canonical frozen patch 是否已形成（评分消费的不可变 delta）。"
    )
    fresh_grading_complete: bool = Field(
        description="fresh grading 是否完整跑完（评分产物齐全；不含结果好坏判断）。"
    )
    triggered_by_policy_horizon: bool = Field(
        description="触发者是否 policy-owned horizon（token/turn/context 三种确定性 "
        "horizon）。冗余布尔事实，validator 钉死 == kind ∈ policy horizon 族。"
    )
    triggered_by_hard_wall: bool = Field(
        description="触发者是否 hard wall 看门狗（墙钟超时，可能混入 infra 抖动，"
        "事实完整只证可评分不证归因于 policy）。validator 钉死 == kind ∈ 看门狗族。"
    )

    @model_validator(mode="after")
    def _check_facts_consistency(self) -> "TerminationFactsV1":
        if self.terminated_unix_s < self.resource_occupancy_started_unix_s:
            raise ValueError(
                f"计时区间倒挂：terminated={self.terminated_unix_s} < "
                f"started={self.resource_occupancy_started_unix_s}"
            )
        expect_policy = self.termination_kind in TERMINATION_KINDS_POLICY_HORIZON
        if self.triggered_by_policy_horizon != expect_policy:
            raise ValueError(
                f"triggered_by_policy_horizon={self.triggered_by_policy_horizon} 与 "
                f"termination_kind={self.termination_kind}（policy horizon 族成员判定 "
                f"{expect_policy}）矛盾——矛盾事实不可表示"
            )
        expect_wall = self.termination_kind in TERMINATION_KINDS_WATCHDOG
        if self.triggered_by_hard_wall != expect_wall:
            raise ValueError(
                f"triggered_by_hard_wall={self.triggered_by_hard_wall} 与 "
                f"termination_kind={self.termination_kind}（看门狗族成员判定 "
                f"{expect_wall}）矛盾——矛盾事实不可表示"
            )
        return self

    @property
    def coarse_duration_s(self) -> float:
        """粗粒度占用时长（秒）。只是区间差，不是归因结论。"""
        return self.terminated_unix_s - self.resource_occupancy_started_unix_s


# 中立性导入断言：字段名里不许出现处置类词根。谁往这个记录里加
# disposition/admission/reward/mask/train 字段，import 即炸——那属于
# A5/D1 拍板后的**另一个**模块，不属于事实记录。
_DISPOSITION_TOKENS = ("disposition", "admission", "reward", "mask", "train", "penal", "sample")
_violations = [
    name for name in TerminationFactsV1.model_fields
    if any(tok in name.lower() for tok in _DISPOSITION_TOKENS)
]
assert not _violations, f"TerminationFactsV1 出现处置类字段名（违反 A5 批准前边界）：{_violations}"

__all__ = ["TerminationFactsV1"]
