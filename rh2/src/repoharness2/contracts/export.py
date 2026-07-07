"""TrainingExportRecord：离线导出记录（S1-8，对接 warm-start 离线过滤契约）。

对接文档：`docs/agentic_RL/training_design/warm_start_offline_data_filtering_design.md`。
该文档 §2 的数据流是：

    TrajectoryArtifact -> TrainingEligibilityReport -> offline_or_sft_candidate
      -> TrajectoryHeuristicAnalyzer -> OfflineFilterReport -> WarmStartDatasetBuilder

本对象就是这条流水线的**入口载体**：离线导出 adapter（`adapters/offline_export/`）
把一条通过资格门的 FinalizedRollout 固化成一条本记录 + 一组 token 级 payload
artifact，后续的 TrajectoryHeuristicAnalyzer / WarmStartDatasetBuilder 只消费
导出目录，不再回读在线训练进程的内存对象。

字段最小集的出处（对齐 warm-start 文档 §3 OfflineFilterReport 草案与 §5 SFT
候选规则，按"导出侧需要预先固化什么"提炼）：

- §3 `source_artifact_id` / `source_trace_ids` -> `trajectory_id` / `source_object_ref`
  / branches 的 `branch_id`；
- §3 `report_id` + analyzer 版本纪律 -> `record_id` + `exporter_version`
  （§4 明说"新增启发式必须记录 analyzer version，并保留输入 artifact 引用，
  方便复算"——导出侧对应物是 exporter 版本 + projection/facts digest 回链）；
- §3 `token_penalty_span_refs` / `decision` 属于**离线过滤之后**的产物，不进
  本记录；本记录只留 §2 要求的可空回链挂点 `offline_filter_report_ref`
  （"在线 rollout 结束时 offline_filter_report_ref 可以为空；离线作业随后生成
  OfflineFilterReport"）；
- §5 条 5 "token provenance 如果不满足 online RL，仍必须能解释文本来源和过滤
  原因" -> 每分支的 `token_fidelity` 显式声明 + `capture_record_refs` 回链 +
  记录级 `eligibility_facts_digest`（资格七维事实的防篡改锚点）；
- §5 条 3 "最终 patch 可以 clean replay" -> `grading_report_ref`（hygiene 与
  clean replay 结论都在评分报告里，离线过滤按引用取用）。

**资格门在 schema 层锁死（本对象最重要的 fail-closed 行为）**：
`training_eligibility_class` 的类型是只含两档的 Literal——
`audit_only_or_rejected` 在本 schema 下**不可表示**。也就是说"把 audit 档样本
导出成训练数据"不是被某个 if 拦住的，而是根本写不出合法的导出记录；
`adapters/offline_export/exporter.py` 在更早的位置还有一道显式拒绝
（reason_code=`audit_tier_not_exportable`），两道防线首尾相接。
"""

from __future__ import annotations

from typing import Literal

from pydantic import AwareDatetime, Field, model_validator

from repoharness2.contracts._base import (
    ArtifactRef,
    NonEmptyStr,
    Sha256Digest,
    StrictModel,
)
from repoharness2.contracts.trajectory import RewardFacts

# 可导出的资格档位：audit_only_or_rejected 刻意不在其中（schema 层拒收）。
ExportableEligibilityClass = Literal[
    "online_policy_loss_eligible",
    "offline_or_sft_candidate",
]

# 分支 token 保真度声明（§5 条 5 的落点）。v1 只定义 token_faithful：
# 分支 token ids / loss mask / logprobs 逐位来自 serving 捕获链（capture 回链 +
# 导出器重建校验通过）。未来若要导出"文本级 SFT 候选"（无 token 身份，例如
# verifiers EvalClient 轨迹），必须先给本 Literal 显式加值并同步改校验器，
# 不允许在 token_faithful 名下静默混入文本级数据。
ExportTokenFidelity = Literal["token_faithful"]


class ExportBranchTokens(StrictModel):
    """一条可训练分支的导出 token 事实（payload 全部走 ArtifactRef，不内嵌）。

    与 BranchProjection 的分工：BranchProjection 是治理层的 span/tape 账目，
    本对象是离线消费侧的**字节流清单**——token ids / loss mask / logprobs 以
    小端二进制落盘（int32 / int32 / float64），digest 与 byte_size 必填，
    离线消费方读文件前先对 digest。

    fail-closed 校验清单：
    1. 三个 payload 引用的 sha256 与 byte_size 必填（导出面上"没有 digest 的
       引用"不可表示——manifest 对账与防篡改都靠它）；
    2. byte_size 与 token 计数互锁：token_ids 是全序列 int32
       （4 * (prompt+response) 字节）、loss_mask 是 response 段 int32
       （4 * response 字节）、logprobs 是 response 段 float64（8 * response 字节）。
       具体数值例：prompt 12 + response 23 的分支，token_ids 必须恰好
       4*35=140 字节，差 4 字节都说明序列被截断或多写；
    3. trainable_token_count >= 1 且 <= response_token_count（v1 只导出
       token_faithful 分支，零可训练 token 的分支不该出现在导出面）；
    4. capture_record_refs 非空（§5 条 5：token 来源必须可解释、可回链）。
    """

    branch_id: NonEmptyStr = Field(description="分支 id（与 TrajectoryProjection.branches 同名对应）。")
    prompt_token_count: int = Field(ge=1, description="prompt 段 token 数（例：12）。")
    response_token_count: int = Field(ge=1, description="response 段 token 数（例：23）。")
    trainable_token_count: int = Field(
        ge=1,
        description=(
            "mask=1 token 总数（loss mask 展开后重算）。v1 只导出 token_faithful 分支，"
            "至少 1；离线过滤的行为启发式（§4）可直接用它做粗筛。"
        ),
    )
    token_fidelity: ExportTokenFidelity = Field(
        default="token_faithful",
        description="token 保真度声明（§5 条 5）。v1 唯一合法值 token_faithful。",
    )
    token_ids_ref: ArtifactRef = Field(
        description="完整分支 token 序列（prompt+response，小端 int32）的导出 artifact 引用。"
    )
    loss_mask_ref: ArtifactRef = Field(
        description="response 段 loss mask（0/1，小端 int32，长度=response_token_count）的引用。"
    )
    rollout_logprobs_ref: ArtifactRef | None = Field(
        default=None,
        description=(
            "response 段逐 token rollout logprob（小端 float64；mask=0 位为 0.0，"
            "slime 语义）的引用。logprob 缺失的分支为 None——缺失必须显式，不许补零伪装。"
        ),
    )
    capture_record_refs: list[NonEmptyStr] = Field(
        min_length=1,
        description="支撑本分支的 GenerationCaptureRecord.record_id（按轮次序，§5 条 5 的回链）。",
    )

    @model_validator(mode="after")
    def _check_branch_payloads(self) -> "ExportBranchTokens":
        if self.trainable_token_count > self.response_token_count:
            raise ValueError(
                f"trainable_token_count({self.trainable_token_count}) 不得大于 "
                f"response_token_count({self.response_token_count})。"
            )
        total = self.prompt_token_count + self.response_token_count
        expectations = [
            ("token_ids_ref", self.token_ids_ref, 4 * total),
            ("loss_mask_ref", self.loss_mask_ref, 4 * self.response_token_count),
        ]
        if self.rollout_logprobs_ref is not None:
            expectations.append(
                ("rollout_logprobs_ref", self.rollout_logprobs_ref, 8 * self.response_token_count)
            )
        for name, ref, expected_size in expectations:
            if ref.sha256 is None or ref.byte_size is None:
                raise ValueError(
                    f"{name} 的 sha256 与 byte_size 必填（导出面引用必须可对账、可防篡改）。"
                )
            if ref.byte_size != expected_size:
                raise ValueError(
                    f"{name}.byte_size({ref.byte_size}) 与 token 计数不符：期望 {expected_size} 字节"
                    f"（prompt={self.prompt_token_count}, response={self.response_token_count}）。"
                )
        return self


class TrainingExportRecord(StrictModel):
    """一条离线导出记录（records.jsonl 的行对象，warm-start 过滤流水线的入口）。

    创建者：`adapters/offline_export/exporter.py`（消费 gate 之后的
    FinalizedRollout——wrapper.finalize_rollout 是唯一治理关口，导出器绝不
    接受未经它的裸投影）。
    消费者：TrajectoryHeuristicAnalyzer（warm-start 文档 §2）、
    WarmStartDatasetBuilder、inspect-rh2-artifact、S1-8 parity-core 校验。

    fail-closed 校验清单：
    1. `training_eligibility_class` 只可表示 online / offline 两档——audit 档
       导出在 schema 层不可表示（本模块 docstring 的"两道防线"之一）；
    2. `reward_facts.reward_scope != "none"`：infra 失败（无 reward）的样本在
       gate 层已落 audit 档，这里再锁一遍——"没有 reward 的训练导出"不可表示；
    3. `grading_report_ref` 必须出现在 `reward_facts.reward_event_refs` 里
       （reward 出处与评分引用必须是同一份评分，防止接错线）；
    4. branches 非空、branch_id 唯一；
    5. fan-out 账目互锁：`reward_facts.segment_count`（在场时）== len(branches)，
       `reward_facts.rollout_loss_denominator`（在场时）== 各分支
       trainable_token_count 之和（与 TrajectoryProjection 的账目规则同构，
       导出面独立重锁一遍——导出记录会离开治理进程流转，必须自证）。
    """

    schema_id: Literal["rh2.training_export_record.v1"] = Field(
        default="rh2.training_export_record.v1", description="schema 判别字段。"
    )
    record_id: NonEmptyStr = Field(description="导出记录 id（OfflineFilterReport.source_artifact_id 的指向对象）。")
    trajectory_id: NonEmptyStr = Field(description="被导出轨迹 id（与全部 sidecar 同键）。")
    task_id: NonEmptyStr = Field(description="任务 id（如 psf__requests-2931）。")
    source_framework: Literal["slime", "verifiers"] = Field(
        description="投影来源框架（透传 TrajectoryProjection 的审计事实）。"
    )
    source_object_ref: NonEmptyStr = Field(
        description="来源对象引用（如 slime_rollout_3 / verifiers_trace_<id>）。"
    )
    exporter_version: NonEmptyStr = Field(
        description="导出器版本（§4 的 analyzer version 纪律在导出侧的对应物；改导出语义必须升版本）。"
    )
    projection_schema_id: Literal["rh2.trajectory_projection.v1"] = Field(
        default="rh2.trajectory_projection.v1",
        description="被导出投影的 schema id（导出记录自带上游契约版本锚点）。",
    )
    projection_digest: Sha256Digest = Field(
        description="TrajectoryProjection 规范化 JSON 的 digest（canonical_json_digest；投影 sidecar 防篡改回链）。"
    )
    eligibility_report_ref: NonEmptyStr = Field(
        description="EligibilityReport.report_id（资格判定权威载体的引用，宿主派生视图同款键义）。"
    )
    training_eligibility_class: ExportableEligibilityClass = Field(
        description=(
            "资格档位。只可表示 online_policy_loss_eligible / offline_or_sft_candidate——"
            "audit_only_or_rejected 在本 schema 下不可表示（导出资格门的 schema 层落点）。"
        )
    )
    eligibility_facts_digest: Sha256Digest = Field(
        description="EligibilityReport.facts_digest 的逐字拷贝（离线侧核对七维事实未被改动的锚点）。"
    )
    gate_version: NonEmptyStr = Field(description="产出资格结论的 gate 版本（如 rh2.gate.s1.v1）。")
    grading_report_ref: NonEmptyStr = Field(
        description="GradingReport.report_id（clean replay / hygiene 结论的引用，§5 条 3 的取用通道）。"
    )
    reward_facts: RewardFacts = Field(
        description="reward 原始事实（逐字段透传投影的 RewardFacts——parity-core 逐位比对的对象之一）。"
    )
    renderer_cls_name: NonEmptyStr = Field(description="渲染器类名（SFT 重渲染 / 漂移排查需要）。")
    tokenizer_name: NonEmptyStr = Field(description="tokenizer 名称（离线重 tokenize 的依据）。")
    chat_template_hash: Sha256Digest | None = Field(
        default=None, description="chat template 内容 digest（可选，透传投影）。"
    )
    branches: list[ExportBranchTokens] = Field(
        min_length=1, description="全部导出分支的 token 字节流清单。"
    )
    offline_filter_report_ref: NonEmptyStr | None = Field(
        default=None,
        description=(
            "OfflineFilterReport 的可空回链挂点（warm-start 文档 §2：导出时为空，"
            "离线过滤作业运行后回填新版本记录——不静默改写原始记录）。"
        ),
    )
    exported_at_utc: AwareDatetime = Field(description="导出时间（必须带时区）。")

    @model_validator(mode="after")
    def _check_export_contract(self) -> "TrainingExportRecord":
        branch_ids = [branch.branch_id for branch in self.branches]
        if len(branch_ids) != len(set(branch_ids)):
            raise ValueError(f"branch_id 必须在导出记录内唯一，得到 {branch_ids}。")

        if self.reward_facts.reward_scope == "none":
            raise ValueError(
                "reward_scope=none 的样本不可导出：无 reward（infra 失败）的轨迹在 gate 层"
                "已是 audit 档，训练导出面禁止表示它（P4：infra 绝不伪装训练数据）。"
            )
        if self.grading_report_ref not in self.reward_facts.reward_event_refs:
            raise ValueError(
                f"grading_report_ref({self.grading_report_ref}) 必须出现在 "
                f"reward_facts.reward_event_refs({self.reward_facts.reward_event_refs}) 里"
                "（reward 出处与评分引用必须是同一份评分）。"
            )

        segment_count = self.reward_facts.segment_count
        if segment_count is not None and segment_count != len(self.branches):
            raise ValueError(
                f"reward_facts.segment_count({segment_count}) 与导出分支数({len(self.branches)}) "
                "不一致（fan-out 账目在导出面同样必须互锁）。"
            )
        declared = self.reward_facts.rollout_loss_denominator
        trainable_total = sum(branch.trainable_token_count for branch in self.branches)
        if declared is not None and declared != trainable_total:
            raise ValueError(
                f"reward_facts.rollout_loss_denominator({declared}) 与各分支 trainable_token_count "
                f"之和({trainable_total}) 不一致（loss 账目被改动或分支缺漏）。"
            )
        return self
