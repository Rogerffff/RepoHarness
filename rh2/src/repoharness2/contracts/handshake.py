"""BackendHandshake：治理层与训练后端的样本交接握手（policy 版本 / staleness / 组信号）。

位置：02 文档 §8 生命周期第 9 步——gate 放行或降级之后、样本进入训练 batch
之前，编排胶水与训练后端就"这批样本是谁生成的、新鲜度如何、组是否完整"
达成一致。设计原则（H10）：staleness 的**使用**归训练后端（丢弃/校正是后端算法
决策），RepoHarness 只负责把事实记录完整并保证降级信号在组装配前可见。

派生视图互检范式在此复用：`staleness_within_threshold` 是可以由
staleness_steps 与 staleness_threshold 推出的派生结论，校验器强制两者一致，
防止"记录说超阈值、结论说没超"这类账实不符。
"""

from __future__ import annotations

from typing import Literal

from pydantic import AwareDatetime, Field, model_validator

from repoharness2.contracts._base import NonEmptyStr, StrictModel

BackendRejectionReason = Literal[
    "staleness_exceeded",  # 新鲜度超阈值，后端拒收
    "group_incomplete",  # 组信号不完整（GRPO 语义要求的组员缺失且未获降级确认）
    "schema_mismatch",  # 契约版本不匹配
    "capacity_backpressure",  # 后端容量反压（P11 下游形态）
    "other",  # 其他（须在 note 里解释）
]


class GroupSignal(StrictModel):
    """GRPO 组语义的握手信号（算法无关原则：仅当后端声明组式算法时才出现本对象）。

    fail-closed 行为：
    - delivered + degraded 不得超过 expected_group_size（凭空多出的样本一定是账错了）；
    - degrade_visible_before_assembly 必须为 True——降级必须在组装配前对后端可见
      （S1-5 验收语义），事后才通知的降级会让后端在残缺组上做组内归一化。
    """

    group_id: NonEmptyStr = Field(description="组 id（同 prompt 的 n 条 rollout 共享）。")
    expected_group_size: int = Field(
        ge=1, description="期望组大小（E2 生产配置 n=8；S1-7a bring-up n=4）。"
    )
    delivered_sample_count: int = Field(
        ge=0, description="实际交付给后端的合格样本数。"
    )
    degraded_sample_count: int = Field(
        ge=0, description="被 gate 降级/拒绝而未交付的样本数。"
    )
    degrade_visible_before_assembly: bool = Field(
        description="降级信号是否在组装配前对后端可见。必须为 True，否则拒收。"
    )

    @model_validator(mode="after")
    def _check_group_contract(self) -> "GroupSignal":
        if self.delivered_sample_count + self.degraded_sample_count > self.expected_group_size:
            raise ValueError(
                f"delivered({self.delivered_sample_count}) + degraded({self.degraded_sample_count}) "
                f"超过 expected_group_size({self.expected_group_size})：组账目不平。"
            )
        if not self.degrade_visible_before_assembly:
            raise ValueError(
                "degrade_visible_before_assembly 必须为 True：降级必须在组装配前对后端可见"
                "（否则后端会在残缺组上做组内归一化，S1-5 验收语义）。"
            )
        return self


class BackendHandshake(StrictModel):
    """一次样本交接的握手记录（后端接受或拒收的完整事实）。

    创建者：训练后端 adapter（slime 绑定 / 离线导出）。
    消费者：EligibilityGate 的 policy_staleness 维度（事实来源）、
    审计（拒收原因分布）、F5/吞吐画像。

    accepted 语义定案（S1-1b）：**accepted 仅表示后端物理接收了这份样本；
    可训练性的唯一权威是 EligibilityReport（policy_staleness 维度消费本对象的
    staleness 事实）**。因此 accepted=True 与 staleness_within_threshold=False
    可以并存（后端有权按自己的算法策略接收过期样本，H10），资格判定不看
    accepted——本契约刻意不新增第二个"可训练"字段（R2 单一权威原则）。

    fail-closed 校验清单：
    1. accepted 与 rejection_reason 互斥互补（接受了就不能有拒收原因，反之必有）；
    2. staleness_within_threshold 必须等于 staleness_steps <= staleness_threshold
       的重算结果（派生视图互检）；
    3. weight_versions_seen 至少一个（rollout 期间引擎必然报告过权重版本）。
    """

    schema_id: Literal["rh2.backend_handshake.v1"] = Field(
        default="rh2.backend_handshake.v1", description="schema 判别字段。"
    )
    handshake_id: NonEmptyStr = Field(description="握手记录 id。")
    trajectory_id: NonEmptyStr = Field(description="交接的轨迹 id。")
    backend_name: Literal["slime", "verl", "offline_export"] = Field(
        description="目标后端（取值封闭：新后端先扩契约）。"
    )
    policy_version: NonEmptyStr = Field(
        description=(
            "策略版本单值口径（FA-0 收窄，codex 轮次 3 #5）：= **finalize 时刻的 "
            "current version**（staleness 计算基准）。一次执行可跨多个版本——多版本"
            "事实的权威序列是 weight_versions_seen（逐轮真实值），执行级派生视图"
            "（intra_execution_version_span 等）在 RolloutAttemptOutcome；"
            "禁止把多版本事实压回本字段。"
        )
    )
    weight_versions_seen: list[NonEmptyStr] = Field(
        min_length=1,
        description="rollout 期间引擎报告过的权重版本列表（slime Sample.weight_versions 语义；跨版本即 mid-rollout 权重更新的证据）。",
    )
    staleness_steps: int = Field(
        ge=0, description="off-policy 步数（当前训练 step - 生成时 policy 版本的 step）。"
    )
    staleness_threshold: int = Field(
        ge=0, description="后端声明的 staleness 阈值（超过即应拒收或降级）。"
    )
    staleness_within_threshold: bool = Field(
        description="staleness 是否在阈值内（派生结论，校验器强制与两个整数字段一致）。"
    )
    group_signal: GroupSignal | None = Field(
        default=None,
        description="组信号（仅组式算法后端出现；num_samples=1 的 PPO 形态为 None，算法无关原则）。",
    )
    accepted: bool = Field(
        description=(
            "后端是否物理接收本样本。仅此而已——可训练性唯一权威是 "
            "EligibilityReport（policy_staleness 维度），accepted=True 不构成任何资格背书。"
        )
    )
    backend_rejection_reason: BackendRejectionReason | None = Field(
        default=None, description="拒收原因（accepted=False 时必填；True 时必须为 None）。"
    )
    rejection_note: NonEmptyStr | None = Field(
        default=None, description="拒收补充说明（rejection_reason=other 时必填）。"
    )
    handshaked_at_utc: AwareDatetime = Field(description="握手时间（必须带时区）。")

    @model_validator(mode="after")
    def _check_handshake_contract(self) -> "BackendHandshake":
        expected_within = self.staleness_steps <= self.staleness_threshold
        if self.staleness_within_threshold != expected_within:
            raise ValueError(
                f"staleness_within_threshold({self.staleness_within_threshold}) 与重算结果不符："
                f"staleness_steps={self.staleness_steps}, threshold={self.staleness_threshold} "
                f"=> 应为 {expected_within}（派生视图互检失败）。"
            )
        if self.accepted and self.backend_rejection_reason is not None:
            raise ValueError("accepted=True 时不得携带 backend_rejection_reason。")
        if not self.accepted and self.backend_rejection_reason is None:
            raise ValueError("accepted=False 时必须给出 backend_rejection_reason（拒收不可无因）。")
        if self.backend_rejection_reason == "other" and self.rejection_note is None:
            raise ValueError("backend_rejection_reason=other 时必须提供 rejection_note。")
        if self.backend_rejection_reason != "other" and self.rejection_note is not None:
            raise ValueError("rejection_note 只允许与 backend_rejection_reason=other 搭配。")
        return self
