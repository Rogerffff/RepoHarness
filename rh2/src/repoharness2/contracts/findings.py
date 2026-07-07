"""AntiCheatFinding / TrajectoryQualityFinding：反作弊与轨迹质量事实（§5.3 / §16.11）。

attempted 与 executed 的区分是本模块的核心语义（设计文档 2 §5.3 定案第 3 条）：

  attempted_blocked  作弊被在线拦截，泄漏内容**没有**进入模型上下文。
                     轨迹仍可训练（agent 学到"此路不通"正是训练信号），
                     可选 process penalty；必须回链产生它的 AntiHackEvent。
  executed           作弊实际发生（内容已进模型上下文 / 篡改已落盘）。
                     EligibilityGate 的 security_and_leakage 维度失败，
                     结论 fail-closed 降到 audit_only_or_rejected。

两类 finding 都是 runtime-private 审计资产（描述作弊细节天然要引用私有路径），
在 marker 扫描中属豁免名单，禁止进入 public projection。
"""

from __future__ import annotations

from typing import Literal

from pydantic import AwareDatetime, Field, model_validator

from repoharness2.contracts._base import NonEmptyStr, StrictModel

AntiCheatCategory = Literal[
    "internet_answer_lookup",  # 互联网搜答案（含 GitHub raw/Pages/release/gist 下载）
    "git_history_mining",  # 本地 git 历史找 solution commit / 未来对象恢复
    "test_tampering",  # 篡改测试文件或测试基建
    "deceptive_success",  # 谎报成功（声称完成/通过但无证据事件支撑）
    "hidden_asset_access",  # 访问运行时私有 / grader-only 资产
    "other_suspicious",  # 规则集暂未细分的可疑行为
]

DetectionLayer = Literal[
    "structural_isolation",  # 结构隔离（资产根本不在场而触发的访问失败）
    "online_interception",  # 运行期在线拦截（对应 AntiHackEvent）
    "post_hoc_scan",  # 事后检测（评分期 test reset / monkeypatch / claim checking）
    "llm_judge_review",  # LLM judge 异步意图复核（不阻塞 rollout）
]

Enforcement = Literal["attempted_blocked", "executed"]

TrajectoryPhase = Literal["materialization", "rollout", "grading"]


class AntiCheatFinding(StrictModel):
    """一条反作弊事实结论（gate 的 security_and_leakage 维度的证据单元）。

    创建者：在线拦截层（attempted_blocked）或事后检测/评分 hygiene（executed）。
    消费者：EligibilityGate、warm-start/SFT 过滤、审计与红队。

    fail-closed 行为：
    - enforcement=attempted_blocked 必须回链 anti_hack_event_ref（没有拦截事件
      存证的"attempted"不可表示——防止把 executed 谎报成 attempted 逃过降级）；
    - judge_precision 只在 llm_judge_review 层出现且取值 [0,1]。
    """

    schema_id: Literal["rh2.anti_cheat_finding.v1"] = Field(
        default="rh2.anti_cheat_finding.v1", description="schema 判别字段。"
    )
    finding_id: NonEmptyStr = Field(description="finding id（DimensionFact.evidence_refs 指向它）。")
    trajectory_id: NonEmptyStr = Field(description="涉事轨迹 id。")
    category: AntiCheatCategory = Field(description="作弊类别（四类定案 + 私有资产访问 + 兜底）。")
    phase: TrajectoryPhase = Field(description="发生阶段：物化期 / 运行期 / 评分期。")
    enforcement: Enforcement = Field(
        description="attempted_blocked=拦截成功（轨迹仍可训练）；executed=实际发生（fail-closed 降级）。"
    )
    detection_layer: DetectionLayer = Field(description="检出防线层（纵深防御的哪一层抓到的）。")
    anti_hack_event_ref: NonEmptyStr | None = Field(
        default=None,
        description="产生本 finding 的 AntiHackEvent.event_id。attempted_blocked 时必填。",
    )
    evidence_refs: list[NonEmptyStr] = Field(
        default_factory=list,
        description="其他证据引用（命令事件日志、diff 存证等 opaque ref id）。",
    )
    judge_precision: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="LLM judge 异步复核回写的置信度（仅 llm_judge_review 层，不阻塞 rollout）。",
    )
    description: NonEmptyStr = Field(
        description="人读描述（runtime-private，可包含私有路径；本对象禁止进入 public projection）。"
    )
    detected_at_utc: AwareDatetime = Field(description="检出时间（必须带时区）。")

    @model_validator(mode="after")
    def _check_finding_contract(self) -> "AntiCheatFinding":
        if self.enforcement == "attempted_blocked" and self.anti_hack_event_ref is None:
            raise ValueError(
                "enforcement=attempted_blocked 必须回链 anti_hack_event_ref："
                "没有拦截事件存证就不能主张\"已拦截\"（防止 executed 伪装成 attempted 逃过降级）。"
            )
        if self.judge_precision is not None and self.detection_layer != "llm_judge_review":
            raise ValueError(
                f"judge_precision 只允许出现在 detection_layer=llm_judge_review，"
                f"得到 {self.detection_layer}。"
            )
        return self


QualityCategory = Literal[
    "unfinished_trajectory",  # 轨迹未完成（abort / 中断）
    "timeout",  # 超时
    "max_turns_reached",  # 轮次打满
    "malformed_tool_call",  # 畸形工具调用
    "repeated_rejected_action",  # 反复被拒的动作循环
    "deceptive_success_claim",  # 成功声明缺证据事件（claim checking 命中）
    "empty_patch",  # 最终 patch 为空
    "oversized_context",  # 上下文异常膨胀
]

QualitySeverity = Literal["info", "warning", "violation"]


class TrajectoryQualityFinding(StrictModel):
    """一条轨迹质量事实（§16.11 末段：过程问题走质量 finding，不反向修改 loss_mask）。

    消费面：warm-start/SFT 过滤（离线导出前的候选筛选）、process reward 分量、
    审计。它不直接决定资格，但 gate 与过滤器会消费它。
    """

    schema_id: Literal["rh2.trajectory_quality_finding.v1"] = Field(
        default="rh2.trajectory_quality_finding.v1", description="schema 判别字段。"
    )
    finding_id: NonEmptyStr = Field(description="finding id。")
    trajectory_id: NonEmptyStr = Field(description="涉事轨迹 id。")
    category: QualityCategory = Field(description="质量问题类别。")
    severity: QualitySeverity = Field(description="严重度：info/warning/violation。")
    evidence_refs: list[NonEmptyStr] = Field(
        default_factory=list, description="证据引用（opaque ref id）。"
    )
    description: NonEmptyStr = Field(description="人读描述（runtime-private）。")
    detected_at_utc: AwareDatetime = Field(description="检出时间（必须带时区）。")
