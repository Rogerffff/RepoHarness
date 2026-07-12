"""TrajectoryProjection：框架中立的轨迹投影契约（治理层唯一消费的轨迹形态）。

对应设计文档 2 §5.7"中立投影契约"与 02 文档 §8 生命周期第 7 步：
`project_from_slime`（训练主线）和 `project_from_verifiers`（评测/导出线）
把各自框架的轨迹对象投影成本模块的 `TrajectoryProjection`；
EligibilityGate、投影扫描、离线导出从此只认这一个契约，
看不出样本来自 slime Sample 还是 verifiers Trace——这就是"多后端解耦"的物理形态。

token 座标系约定（全模块统一，避免 slime/verifiers 两家各说各话）：

- 一条分支（BranchProjection）的完整 token 序列 = prompt 段 + response 段，
  下标从 0 开始；`total = prompt_token_count + response_token_count`。
- `TokenSpan` 覆盖整个 [0, total)；`LossMaskSpan` 只覆盖 response 段
  [prompt_token_count, total)（对齐 slime `loss_mask` 长度 == response_length 的语义）。
- 具体数值例子：prompt 15 个 token、生成 16 个 token（S1-0 探针的真实形状），
  则 total=31，TokenSpan 覆盖 [0,31)，LossMaskSpan 覆盖 [15,31)。

tape 对齐约定（S1-0/S0-5 实测，两引擎不同构，必须显式编码）：

- SGLang routing 行数 = prompt_len - 1 + generated_len（15-1+16=30 行）；
- vLLM routing 行数 = prompt_len + generated_len（13+8=21 行）；
- top-p offsets 长度 = response_token_count + 1，offsets[0]=0，
  offsets[-1] = 全部保留 token 总数（uh_probe_result.json：gen 16 -> offsets 长 17）。

fan-out 建模定案（S1-1b）：**单投影多 branches 为权威**——

- 一个 rollout/session 产一个 TrajectoryProjection；compaction/fan-out 的
  全部分段都作为它的 branches，不拆成多个投影对象；
- RewardFacts.segment_count 必须等于 len(branches)（投影层校验器互检，
  branches=2 却申报 segment_count=5 直接拒收）；
- parent_rollout_id 只用于跨 rollout 的 GRPO 同题兄弟组（同一 prompt 的
  n 条 rollout），**不用于 rollout 内分段**——rollout 内分段就是 branches。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from pydantic import AwareDatetime, Field, model_validator

from repoharness2.contracts._base import (
    ArtifactRef,
    NonEmptyStr,
    SafeIdentifier,
    Sha256Digest,
    StrictModel,
)

# ---------------------------------------------------------------------------
# token 归属与 loss mask
# ---------------------------------------------------------------------------

TokenSourceType = Literal[
    "sampled_assistant",  # 模型本轮真实采样出的 assistant token（唯一可训练来源）
    "prompt_context",  # 首轮 prompt / 历史上下文重放
    "tool_result",  # 工具 / 环境返回文本
    "user_message",  # 用户（或用户模拟器）消息
    "system_scaffold",  # system prompt / harness 拼接的脚手架
    "harness_interstitial",  # harness 在轮间插入的过渡文本
    "replayed_assistant_context",  # 兄弟分支已训练过、本分支作为上下文重放的模型输出
]


class TokenSpan(StrictModel):
    """一段连续 token 的来源归属（半开区间 [start, end)）。

    fail-closed 行为：BranchProjection 校验所有 TokenSpan 必须无缝、无重叠地
    平铺整个 token 序列——任何"没人认领"的 token 段都会被拒收，
    因为无法归属来源的 token 不可能证明训练安全（H4）。
    """

    start: int = Field(ge=0, description="区间起点（含），基于分支完整 token 序列的 0 起下标。")
    end: int = Field(gt=0, description="区间终点（不含），必须大于 start。")
    source_type: TokenSourceType = Field(
        description=(
            "本段 token 的来源类型。只有 sampled_assistant 段允许被 loss_mask=1 覆盖；"
            "tool_result / user_message / system_scaffold / harness_interstitial /"
            "replayed_assistant_context 都是上下文，参训即污染（H4：sampled ∧ role）。"
        )
    )

    @model_validator(mode="after")
    def _check_interval(self) -> "TokenSpan":
        if self.end <= self.start:
            raise ValueError(f"TokenSpan 区间非法：end({self.end}) 必须大于 start({self.start})。")
        return self


LossMaskReason = Literal[
    "sampled_assistant_trainable",  # 模型真实采样且允许训练 -> mask=1 的唯一合法理由
    "prompt_context",  # prompt / 历史上下文
    "tool_or_env_context",  # 工具或环境输出
    "user_or_system_message",  # 用户 / system 消息
    "replayed_sibling_response",  # 兄弟分支重放（第一次已训练，避免重复计入 loss）
    "retokenization_drift_downgraded",  # token 漂移无法证明采样来源，降级为上下文
    "token_capture_unavailable_downgraded",  # 文本中继（verifiers EvalClient）无 token 级捕获，采样身份不可证明，降级为上下文（S1-8）
]


class LossMaskSpan(StrictModel):
    """一段连续 token 的 loss mask 值与理由（半开区间 [start, end)，只覆盖 response 段）。

    fail-closed 行为：mask=1 当且仅当 reason == "sampled_assistant_trainable"；
    mask 与 reason 不一致（例如 mask=1 却标着 tool_or_env_context）直接拒收——
    这是"loss mask 可解释"（H1 第 3 条）在 schema 层的落点。

    provenance/algorithmic 分离（FA-0 第 4 条，faithful DIS 前置约定）：本对象
    是 **provenance loss mask**——回答"token 是否由模型真实采样、角色是否允许
    进 policy loss"，属于投影的不可变历史事实。训练侧的 DIS/staleness 算法
    掩码（dis_mask / importance_weight）回答的是"本次 trainer step 中
    current/rollout ratio 是否在信任区间"，逐 step 变化，**不得改写本对象**；
    正确实现保留原始 mask、另出 step-local 张量（完整定义见
    contracts/fa_runtime.py 模块 docstring 与 05 计划 FA-4）。
    """

    start: int = Field(ge=0, description="区间起点（含），同 TokenSpan 座标系。")
    end: int = Field(gt=0, description="区间终点（不含），必须大于 start。")
    mask: Literal[0, 1] = Field(description="loss mask 值：1=参与 policy loss，0=纯上下文。")
    reason: LossMaskReason = Field(
        description="本段 mask 取值的理由码。mask=1 只允许 sampled_assistant_trainable。"
    )

    @model_validator(mode="after")
    def _check_mask_reason_consistency(self) -> "LossMaskSpan":
        if self.end <= self.start:
            raise ValueError(f"LossMaskSpan 区间非法：end({self.end}) 必须大于 start({self.start})。")
        if self.mask == 1 and self.reason != "sampled_assistant_trainable":
            raise ValueError(
                "mask=1 的 span 只能以 sampled_assistant_trainable 为理由，"
                f"得到 reason={self.reason!r}（fail-closed：上下文 token 禁止参训）。"
            )
        if self.mask == 0 and self.reason == "sampled_assistant_trainable":
            raise ValueError(
                "mask=0 与 reason=sampled_assistant_trainable 矛盾：可训练理由必须配 mask=1；"
                "被降级的采样 token 应使用 replayed_sibling_response / "
                "retokenization_drift_downgraded / token_capture_unavailable_downgraded 等降级理由。"
            )
        return self


# ---------------------------------------------------------------------------
# logprob / routing / top-p tape 事实
# ---------------------------------------------------------------------------


class LogprobProvenance(StrictModel):
    """rollout logprob 的出处标注（设计文档 2 §5.7 M4：logprob_source）。

    透传无损是必要非充分：同权重下推理引擎与训练引擎的分布仍系统性不同（ROME 实证），
    训练侧的 IS/TIS 校正归训练后端（H10）；本对象只负责把 serving 事实记全，
    让后端知道这些 logprob 是"谁、哪个版本、什么精度"算出来的。
    """

    engine_name: Literal["sglang", "vllm"] = Field(
        description=(
            "产生 logprob 的推理引擎。取值封闭（fail-closed）：接入新引擎必须先扩契约，"
            "不允许用自由字符串静默混入未知引擎。"
        )
    )
    engine_version: NonEmptyStr = Field(
        description="推理引擎版本号，例如 \"0.5.9\"（SGLang，S0-6 探针实测值）。"
    )
    precision: Literal["float32", "bfloat16", "float16", "float64"] = Field(
        description="serving 计算精度（S1-0 探针：Qwen3-30B-A3B 为 bfloat16）。"
    )
    sampling_backend: NonEmptyStr | None = Field(
        default=None,
        description="采样后端（如 \"pytorch\"）。Blackwell 上曾必须关 FLASHINFER sampler，该事实要可审计。",
    )
    weight_version: NonEmptyStr | None = Field(
        default=None,
        description="引擎侧权重版本标签（SGLang meta_info.weight_version，例如 \"default\"）。",
    )


RoutingAlignment = Literal[
    "sglang_prompt_minus1_plus_gen",  # SGLang：行数 = prompt_len - 1 + generated_len
    "vllm_prompt_plus_gen",  # vLLM：行数 = prompt_len + generated_len
    "not_applicable_dense_model",  # dense 模型没有 routing tape（必须显式声明，禁止静默缺席）
    "not_captured_text_relay",  # 文本中继（verifiers EvalClient）没有任何 token 级捕获——
    # 模型是不是 MoE 都无从谈起，禁止谎报 dense 声明（S1-8 显式降级标注）
]

# "声明无 tape"的两种合法形态：dense 模型（确知没有 routing）与文本中继
# （根本没有 token 级捕获）。两者都必须与任何 tensor 字段互斥。
_ROUTING_NO_TAPE_ALIGNMENTS = ("not_applicable_dense_model", "not_captured_text_relay")


class RoutingTensorRef(StrictModel):
    """MoE routing tape（routed_experts）的引用与对齐声明（M1 硬前提）。

    引擎行数约定不同构（S1-0 实测）：SGLang 是 prompt_len-1+generated_len
    （15-1+16=30），vLLM 是 prompt_len+generated_len（13+8=21）。
    `alignment` 必须显式编码引擎约定；tape 解码只在 projection 层做一次，
    解码者必须按本字段选公式，禁止假设两引擎同构。

    fail-closed 行为：
    - alignment 是必填字段——"tensor 在场但没说对齐约定"在本 schema 下不可表示；
    - alignment=not_applicable_dense_model 时禁止携带 tensor 引用与形状
      （防止 dense 路径误挂 MoE tape）；
    - alignment 为引擎值时必须携带 tensor 引用、形状与 token 计数，
      且行数必须精确满足该引擎的公式，差一行都拒收。
    """

    alignment: RoutingAlignment = Field(
        description=(
            "routing 行与 token 的对齐约定。dense 模型必须显式填 "
            "not_applicable_dense_model（A2：routing 缺失不得静默成功）；"
            "verifiers EvalClient 文本中继（无任何 token 级捕获）必须显式填 "
            "not_captured_text_relay，不得谎报 dense 声明（S1-8）。"
        )
    )
    tensor_ref: ArtifactRef | None = Field(
        default=None,
        description="routing tape 张量的 opaque 引用（int32/uint8，形状 [num_rows, num_layers, router_topk]）。",
    )
    num_rows: int | None = Field(
        default=None,
        ge=1,
        description="tape 行数。SGLang 例：prompt 15 + 生成 16 -> 30 行；vLLM 例：13+8 -> 21 行。",
    )
    num_layers: int | None = Field(
        default=None, ge=1, description="MoE 层数（Qwen3-30B-A3B 为 48）。"
    )
    router_topk: int | None = Field(
        default=None, ge=1, description="每 token 每层选中的专家数（Qwen3-30B-A3B 为 8）。"
    )
    dtype: Literal["int32", "uint8"] | None = Field(
        default=None,
        description="张量元素类型：slime 解码为 int32；专家 id 0..127 也可紧凑存为 uint8。",
    )
    prompt_token_count: int | None = Field(
        default=None, ge=1, description="产生本 tape 的 prompt token 数（对齐公式的输入之一）。"
    )
    generated_token_count: int | None = Field(
        default=None, ge=1, description="产生本 tape 的生成 token 数（对齐公式的输入之一）。"
    )
    routed_experts_start_len: int = Field(
        default=0,
        ge=0,
        description=(
            "tape 起始行偏移（FA-0 第 8 条扩展位，2026-07-12 自 S2-0 迁入）。"
            "上游 slime 680824dd 改为 expected_rows = len(tokens)-1-start_len 的"
            "中段拼接语义（token 级真续跑时新 tape 只覆盖续跑段，torch.cat 拼回）；"
            "该语义在本仓库尚未实现，当前必须为 0——真续跑递延项（05 计划 §6 第 7 条）"
            "启用并 cherry-pick 680824dd 后才解除此断言。"
        ),
    )

    @model_validator(mode="after")
    def _check_alignment_contract(self) -> "RoutingTensorRef":
        if self.routed_experts_start_len != 0:
            raise ValueError(
                f"routed_experts_start_len={self.routed_experts_start_len} 尚不支持："
                "中段拼接（上游 680824dd）是真续跑递延项的基建，当前实现只接受 0"
                "（fail-closed 留位，不静默接受未实现语义）。"
            )
        tensor_fields = {
            "tensor_ref": self.tensor_ref,
            "num_rows": self.num_rows,
            "num_layers": self.num_layers,
            "router_topk": self.router_topk,
            "dtype": self.dtype,
            "prompt_token_count": self.prompt_token_count,
            "generated_token_count": self.generated_token_count,
        }
        if self.alignment in _ROUTING_NO_TAPE_ALIGNMENTS:
            present = [name for name, value in tensor_fields.items() if value is not None]
            if present:
                raise ValueError(
                    f"alignment={self.alignment} 时不得携带 routing 张量字段，"
                    f"但发现 {present}（fail-closed：无 tape 声明与 tape 在场互斥）。"
                )
            return self

        missing = [name for name, value in tensor_fields.items() if value is None]
        if missing:
            raise ValueError(
                f"alignment={self.alignment} 时必须携带完整 routing 张量字段，缺失 {missing}"
                "（fail-closed：有对齐声明就必须有可校验的 tape 事实）。"
            )
        assert self.num_rows is not None  # for type checkers
        assert self.prompt_token_count is not None and self.generated_token_count is not None
        if self.alignment == "sglang_prompt_minus1_plus_gen":
            expected = self.prompt_token_count - 1 + self.generated_token_count
        else:  # vllm_prompt_plus_gen
            expected = self.prompt_token_count + self.generated_token_count
        if self.num_rows != expected:
            raise ValueError(
                f"routing 行数与引擎约定不符：alignment={self.alignment}，"
                f"prompt={self.prompt_token_count}，generated={self.generated_token_count}，"
                f"期望 {expected} 行，实际 {self.num_rows} 行。"
            )
        return self


SamplingMaskKind = Literal[
    "top_p_kept_token_ids",  # top-p 核集合重放 tape（ragged：ids + offsets）
    "not_applicable_top_p_1",  # top_p=1.0 时不存在采样截断，无 tape（必须显式声明）
    "not_captured_text_relay",  # 文本中继（verifiers EvalClient）：采样发生在 provider 侧，
    # top_p 数值与核集合都未被捕获——禁止伪造 top_p=1.0 或空 tape（S1-8 显式降级标注）
]


class SamplingMaskRef(StrictModel):
    """top-p 采样 tape（保留核集合）的引用与形状事实（E2 top_p=0.95 的硬依赖）。

    语义（对齐 slime `rollout_top_p_token_ids/offsets` 与 uh_probe_result.json）：
    对 response 第 i 个 token，保留的核集合是 ids[offsets[i]:offsets[i+1]]。
    因此 offsets 长度必须等于 response_token_count + 1，offsets[0]=0，
    offsets[-1] == 保留 token 总数。具体数值例：生成 16 个 token 时
    offsets 长度 = 17（S1-0 探针实测 top_p_token_offsets_len=17）。

    fail-closed 行为：top_p < 1.0 却缺 tape（stock SGLang 的静默忽略形态，
    S0-6 分水岭证据）在本 schema 下不可表示——要么带全 tape 事实，
    要么 top_p 恰为 1.0 并显式声明 not_applicable。
    """

    mask_kind: SamplingMaskKind = Field(
        description=(
            "tape 类型：top_p<1.0 必须是 top_p_kept_token_ids；top_p=1.0 必须显式 "
            "not_applicable_top_p_1；文本中继（采样参数未捕获）必须显式 not_captured_text_relay。"
        )
    )
    top_p: float | None = Field(
        gt=0.0,
        le=1.0,
        description=(
            "rollout 实际使用的 top_p（E2 定案 0.95；bring-up 应急才允许 1.0）。"
            "None 只允许与 mask_kind=not_captured_text_relay 搭配——采样发生在 provider "
            "侧、参数未被捕获时禁止伪造任何数值（S1-8）。"
        ),
    )
    token_ids_ref: ArtifactRef | None = Field(
        default=None, description="保留核集合 token ids（ragged 拼接后的一维 int32）的引用。"
    )
    offsets_ref: ArtifactRef | None = Field(
        default=None, description="ragged offsets（一维 int32，长度 = response_token_count + 1）的引用。"
    )
    response_token_count: int | None = Field(
        default=None, ge=1, description="tape 覆盖的 response token 数（生成 16 个 token 即 16）。"
    )
    offsets_len: int | None = Field(
        default=None, ge=2, description="offsets 数组长度，必须等于 response_token_count + 1（16 -> 17）。"
    )
    kept_token_count: int | None = Field(
        default=None,
        ge=0,
        description=(
            "保留 token 总数（== offsets[-1]，生产者写入，inspector 可对 tape 重算比对）。"
            "下界语义（S1-7a 真实多轮数据修正）：只有**引擎采样**的 response token "
            "才有核集合（≥1）；多轮 agent 序列里的工具观察/上下文 token 从未被采样，"
            "其 span 为零宽（slime `_pad_rollout_top_p_offsets` 同语义）。因此本层只锁 "
            ">= 0；'每个可训练 token 至少 1 个核'的强下界在 BranchProjection 层与 "
            "loss mask 交叉校验（kept >= Σ mask=1 长度）——真实反例：django-11099 "
            "多轮轨迹 response 3317 token 中 mask=1 仅 456，kept=1302 完全合法。"
        ),
    )

    @model_validator(mode="after")
    def _check_tape_contract(self) -> "SamplingMaskRef":
        tape_fields = {
            "token_ids_ref": self.token_ids_ref,
            "offsets_ref": self.offsets_ref,
            "response_token_count": self.response_token_count,
            "offsets_len": self.offsets_len,
            "kept_token_count": self.kept_token_count,
        }
        if self.mask_kind == "not_captured_text_relay":
            if self.top_p is not None:
                raise ValueError(
                    f"mask_kind=not_captured_text_relay 要求 top_p 为 None，得到 {self.top_p}"
                    "（文本中继根本没捕获采样参数，携带数值即伪造事实）。"
                )
            present = [name for name, value in tape_fields.items() if value is not None]
            if present:
                raise ValueError(
                    f"mask_kind=not_captured_text_relay 时不得携带 tape 字段，但发现 {present}"
                    "（没有捕获就不可能有 tape）。"
                )
            return self

        if self.top_p is None:
            raise ValueError(
                f"mask_kind={self.mask_kind} 要求 top_p 数值必填；top_p=None 只允许与 "
                "not_captured_text_relay 搭配（未捕获的采样参数不得静默缺席）。"
            )

        if self.mask_kind == "not_applicable_top_p_1":
            if self.top_p != 1.0:
                raise ValueError(
                    f"mask_kind=not_applicable_top_p_1 要求 top_p 恰为 1.0，得到 {self.top_p}"
                    "（fail-closed：top_p<1.0 缺 tape 即 stock SGLang 静默降级形态，必须拒收）。"
                )
            present = [name for name, value in tape_fields.items() if value is not None]
            if present:
                raise ValueError(
                    f"mask_kind=not_applicable_top_p_1 时不得携带 tape 字段，但发现 {present}。"
                )
            return self

        # mask_kind == "top_p_kept_token_ids"
        if self.top_p >= 1.0:
            raise ValueError(
                "mask_kind=top_p_kept_token_ids 要求 top_p < 1.0（top_p=1.0 不存在核截断，"
                "应声明 not_applicable_top_p_1）。"
            )
        missing = [name for name, value in tape_fields.items() if value is None]
        if missing:
            raise ValueError(
                f"top_p={self.top_p} < 1.0 时必须携带完整 top-p tape 字段，缺失 {missing}"
                "（E2 硬依赖：没有 tape 的 top-p 采样不可重放，不得进入训练）。"
            )
        assert self.offsets_len is not None and self.response_token_count is not None
        if self.offsets_len != self.response_token_count + 1:
            raise ValueError(
                f"top-p offsets 长度必须等于 response_token_count + 1："
                f"offsets_len={self.offsets_len}，response_token_count={self.response_token_count}。"
            )
        assert self.kept_token_count is not None
        # N-4 强下界（kept >= 可训练 token 数）在 BranchProjection 层与 loss mask
        # 交叉校验——response_token_count 含从未被采样的上下文 token（零宽 span），
        # 在本层用它作下界会把真实多轮轨迹全部误拒（S1-7a 实测）。
        return self


# ---------------------------------------------------------------------------
# reward 事实与 compaction 血缘
# ---------------------------------------------------------------------------

RewardScope = Literal["trace_level", "session_level", "group_level", "process_level", "none"]

CreditAssignmentStrategy = Literal[
    "direct_trace_reward",
    "prefix_merged_session_reward",
    "backend_group_normalized",
    "debug_only_no_policy_loss",
    "unknown",
]


class RewardFacts(StrictModel):
    """reward 原始事实（重定位文档 §16.11 的 schema 落点）。

    职责边界：RepoHarness 只输出 raw reward / components / group 信号，
    归一化与 advantage 计算归训练后端。scope=unknown 或字段互相矛盾时
    fail-closed（gate 会把 unknown scope 降级出 online 档）。

    fan-out reward 权威语义（FA-0 / D-FA-7，2026-07-12 定案）：一次
    RolloutExecution 的 raw reward **整体广播给它的每个 branch**（我方
    adapter 实际行为，generate.py 交付段 `leaf.reward = grading_reward`），
    重复放大由 `rollout_loss_denominator`（rollout 级分母聚合）防住——
    branch 数变化不得改变该 execution 对 loss 的总贡献。slime README 声称
    的 "reward/K 分摊" 与其源码（TrajectoryManager.get_trajectory 写整
    reward）不符，本项目一律以广播 + rollout 分母为准，不做除法。
    """

    reward_scope: RewardScope = Field(
        description=(
            "reward 的作用域。group_level 必须带全组信号防止 fan-out 重复放大；"
            "none 表示尚无可用 reward（例如评分 infra_failure），此时禁止携带数值。"
        )
    )
    raw_reward: float | None = Field(
        default=None,
        description=(
            "原始标量 reward（S1：1.0 当且仅当官方 parser 判 RESOLVED_FULL，其余 0.0）。"
            "scope=none 时必须为 None——infra_failure 绝不允许伪装成 reward=0.0。"
        ),
    )
    components: dict[SafeIdentifier, float] = Field(
        default_factory=dict,
        description="命名 reward 分量（如 process penalty），key 必须是安全标识符。",
    )
    reward_event_refs: list[NonEmptyStr] = Field(
        default_factory=list,
        description="评分事件引用（GradingReport.report_id 等）。trace_level reward 至少要有一条出处。",
    )
    credit_assignment_strategy: CreditAssignmentStrategy = Field(
        description="信用分配策略。unknown 允许表示（审计需要），但 gate 会拒绝其进入 online 档。"
    )
    group_id: NonEmptyStr | None = Field(
        default=None, description="GRPO 组 id（同 prompt 的 n 条 rollout 共享）。"
    )
    parent_rollout_id: NonEmptyStr | None = Field(
        default=None,
        description=(
            "跨 rollout 的 GRPO 同题兄弟组标识（同一 prompt 的 n 条 rollout 共享）。"
            "**不用于 rollout 内分段**——rollout 内的 compaction/fan-out 分段是"
            "同一 TrajectoryProjection 的 branches（S1-1b fan-out 建模定案）。"
        ),
    )
    segment_index: int | None = Field(
        default=None, ge=0, description="fan-out 分段序号（0 起，须小于 segment_count）。"
    )
    segment_count: int | None = Field(
        default=None,
        ge=1,
        description=(
            "同一 rollout 的训练分段总数。权威建模下分段即投影的 branches，"
            "本字段必须等于所属 TrajectoryProjection 的 len(branches)（投影层互检）。"
        ),
    )
    rollout_loss_denominator: int | None = Field(
        default=None,
        ge=1,
        description="同一 rollout 全体分段的 loss mask token 总数（slime rollout_mask_sums 语义），防重复放大。",
    )

    @model_validator(mode="after")
    def _check_scope_contract(self) -> "RewardFacts":
        if self.reward_scope == "none":
            if self.raw_reward is not None:
                raise ValueError(
                    "reward_scope=none 时 raw_reward 必须为 None"
                    "（fail-closed：评分缺失/不可信时禁止携带任何数值 reward，"
                    "尤其禁止 infra_failure 伪装成 0.0）。"
                )
            if self.components:
                raise ValueError("reward_scope=none 时不得携带 components 分量。")
        else:
            if self.raw_reward is None:
                raise ValueError(
                    f"reward_scope={self.reward_scope} 时 raw_reward 必填；"
                    "没有数值就应声明 reward_scope=none。"
                )
        if self.reward_scope == "trace_level" and not self.reward_event_refs:
            raise ValueError(
                "trace_level reward 必须携带至少一条 reward_event_refs 指向评分事件（§16.11 规则 1）。"
            )
        if self.reward_scope == "group_level":
            missing = [
                name
                for name, value in {
                    "group_id": self.group_id,
                    "parent_rollout_id": self.parent_rollout_id,
                    "segment_count": self.segment_count,
                    "rollout_loss_denominator": self.rollout_loss_denominator,
                }.items()
                if value is None
            ]
            if missing:
                raise ValueError(
                    f"group_level reward 必须带全组信号，缺失 {missing}"
                    "（§16.11 规则 3：防止 fan-out 后奖励/loss 重复放大）。"
                )
        if self.credit_assignment_strategy == "backend_group_normalized" and self.reward_scope != "group_level":
            raise ValueError(
                "credit_assignment_strategy=backend_group_normalized 只在 reward_scope=group_level 下有意义。"
            )
        if (
            self.segment_index is not None
            and self.segment_count is not None
            and self.segment_index >= self.segment_count
        ):
            raise ValueError(
                f"segment_index({self.segment_index}) 必须小于 segment_count({self.segment_count})。"
            )
        return self


CompactionKind = Literal[
    "context_compaction",  # 上下文压缩产生的续写分支（GLM-5.2 sub-trace 语义）
    "subagent_fork",  # 子 agent 分叉
    "retokenization_drift_fork",  # token 漂移过大，TrajectoryManager FORK
]


class CompactedSubTraceLineage(StrictModel):
    """compaction / 分叉子轨迹的血缘记录（GLM-5.2"所有 sub-trace 皆可训练"的前提事实）。

    fail-closed 行为：`replay_prefix_loss_masked` 必须为 True——兄弟分支重放的
    父前缀若没有全部 loss_mask=0，同一段模型输出会被重复训练，
    这样的分支在 schema 层直接拒收（对齐 slime TrajectoryManager 的分支语义）。
    """

    parent_trajectory_id: NonEmptyStr = Field(
        description="父轨迹 id（compaction 分支通常与本轨迹同 rollout；子 agent 分叉指向宿主轨迹）。"
    )
    parent_branch_id: NonEmptyStr | None = Field(
        default=None, description="父分支 id（可为 None：父级是未导出的中间态）。"
    )
    compaction_event_id: NonEmptyStr = Field(
        description="产生本分支的分叉事件 id（同一事件可派生多个兄弟分支）。"
    )
    fork_point_token_index: int = Field(
        ge=0, description="分叉点在父分支 token 序列中的下标（0 起）。"
    )
    compaction_kind: CompactionKind = Field(description="分叉类型（压缩续写 / 子 agent / token 漂移）。")
    replay_prefix_loss_masked: bool = Field(
        description="重放的父前缀在本分支中是否已全部 loss_mask=0。必须为 True，否则拒收。"
    )

    @model_validator(mode="after")
    def _check_replay_masked(self) -> "CompactedSubTraceLineage":
        if not self.replay_prefix_loss_masked:
            raise ValueError(
                "replay_prefix_loss_masked 必须为 True：重放前缀未全部置 0 会导致同一段"
                "模型输出被重复训练（fail-closed 拒收，而不是交给下游修复）。"
            )
        return self


# ---------------------------------------------------------------------------
# staleness 记账握手（preflight §8 H-1，S1-9 落地）
# ---------------------------------------------------------------------------


def derive_weight_version_max_lag(weight_versions: Sequence[str]) -> int | None:
    """从原始版本列表派生 max_lag（版本跨度 = max - min）。

    slime 引擎的 weight_version 是十进制整数字符串（update_weights 计数器，
    S1-7a 实测 "1"）；全部可解析时返回跨度，任一不可解析（如 "default"、
    "step_0"）返回 None——派生口径的选择权留给升级档位的准入设计（H-1），
    这里绝不猜测非数值版本的先后关系。

    具体数值例：["1", "1", "3"] -> 3-1 = 2；["default"] -> None。
    """

    try:
        numeric = [int(version, 10) for version in weight_versions]
    except ValueError:
        return None
    if not numeric:
        return None
    return max(numeric) - min(numeric)


class WeightVersionsHandshake(StrictModel):
    """staleness 记账（preflight §8 H-1）：Sample.weight_versions 原始透传 + 派生 max_lag。

    背景：slime 的 `_convert_samples_to_train_data`（ray/rollout.py:735）**不透传**
    `Sample.weight_versions`——训练侧 train_data 里已经没有它。因此采集必须发生在
    projection 层（转换前的 Sample），本对象就是那次采集的落点；gate（S1-5）读它
    把 staleness 分布（列表长度 + 版本跨度）写进 policy_staleness 维 evidence，
    **只记录不准入**（准入界的设计留给升级档位，见 preflight §1.6 定案）。

    两口径并存（H-1 原文要求）：
    - `weight_versions`：原始 list，按（分支序, 轮次序）展平，保留重复——
      长度即"这条轨迹的入训轮跨了几次版本记录"；
    - `max_lag`：派生视图（全部版本为十进制整数时 = max-min，否则 None），
      校验器强制与 `derive_weight_version_max_lag` 重算结果一致（派生视图互检
      范式，同 BackendHandshake.staleness_within_threshold）。
    """

    weight_versions: list[NonEmptyStr] = Field(
        min_length=1,
        description=(
            "rollout 期间引擎逐轮报告的权重版本（slime Sample.weight_versions 语义，"
            "跨分支按分支序展平，保留重复）。"
        ),
    )
    max_lag: int | None = Field(
        default=None,
        ge=0,
        description=(
            "派生的版本跨度（max-min，全部版本可解析为十进制整数时必填且必须等于"
            "重算值；含非数值版本时必须为 None——不可派生就不派生）。"
        ),
    )

    @model_validator(mode="after")
    def _check_max_lag_derivation(self) -> "WeightVersionsHandshake":
        expected = derive_weight_version_max_lag(self.weight_versions)
        if self.max_lag != expected:
            raise ValueError(
                f"max_lag({self.max_lag}) 与重算结果不符：weight_versions="
                f"{list(self.weight_versions)} => 应为 {expected}"
                "（派生视图互检失败；含非数值版本时必须为 None）。"
            )
        return self


# ---------------------------------------------------------------------------
# 分支与轨迹投影
# ---------------------------------------------------------------------------

LogprobAlignmentStatus = Literal[
    "aligned_per_token",  # 每个采样 token 都有 logprob 且长度对齐
    "missing",  # rollout 未返回 logprob
    "partial_or_mismatch",  # 有 logprob 但与 token 对不上
]


class BranchProjection(StrictModel):
    """一条可训练分支的完整投影（token 归属 + loss mask + tape 引用 + 捕获回链）。

    fail-closed 校验清单（任一失败即整个对象拒收）：
    1. TokenSpan 无缝平铺 [0, prompt+response)；
    2. LossMaskSpan 无缝平铺 response 段 [prompt, prompt+response)；
    3. 每个 mask=1 的 span 必须完全落在 sampled_assistant 类型的 TokenSpan 内；
    4. mask=0 的 span 若与 sampled_assistant 区间有重叠，reason 必须是降级类
       （replayed_sibling_response / retokenization_drift_downgraded）——
       模型采样出的 token 不训练必须给降级理由，标成 prompt_context /
       tool_or_env_context 这类"本来就是上下文"的理由等于抹掉降级事实（N-3）；
    5. 存在 mask=1 的 span 时必须有 capture_record_refs（审计事实回链到
       GenerationCaptureRecord，A4：不允许从训练后的 Sample 反推）；
    6. logprob_alignment_status=aligned_per_token 时必须携带 LogprobProvenance；
    7. routing / sampling_mask 的 token 计数必须与本分支的计数一致。
    """

    branch_id: NonEmptyStr = Field(description="分支 id，在所属 TrajectoryProjection 内唯一。")
    prompt_token_count: int = Field(ge=1, description="prompt 段 token 数（例：15）。")
    response_token_count: int = Field(ge=1, description="response 段 token 数（例：16）。")
    token_spans: list[TokenSpan] = Field(
        min_length=1,
        description="来源归属 span 列表，必须无缝无重叠平铺 [0, prompt+response)。",
    )
    loss_mask_spans: list[LossMaskSpan] = Field(
        min_length=1,
        description="loss mask span 列表，必须无缝无重叠平铺 response 段 [prompt, prompt+response)。",
    )
    logprob_alignment_status: LogprobAlignmentStatus = Field(
        description="rollout logprob 与采样 token 的对齐结论。missing/partial 会被 gate 挡在 online 档外。"
    )
    logprob_provenance: LogprobProvenance | None = Field(
        default=None,
        description="logprob 出处（M4）。aligned_per_token 时必填；missing 时必须为 None。",
    )
    routing: RoutingTensorRef = Field(
        description="MoE routing tape 引用。dense 模型也必须显式给 not_applicable_dense_model（禁止省略字段）。"
    )
    sampling_mask: SamplingMaskRef = Field(
        description="top-p tape 引用。top_p=1.0 也必须显式给 not_applicable_top_p_1（禁止省略字段）。"
    )
    lineage: CompactedSubTraceLineage | None = Field(
        default=None, description="compaction/分叉血缘；根分支（未分叉）为 None。"
    )
    capture_record_refs: list[NonEmptyStr] = Field(
        default_factory=list,
        description="支撑本分支采样段的 GenerationCaptureRecord.record_id 列表（按轮次序）。",
    )

    @model_validator(mode="after")
    def _check_branch_invariants(self) -> "BranchProjection":
        total = self.prompt_token_count + self.response_token_count

        # 1. TokenSpan 无缝平铺 [0, total)
        spans = sorted(self.token_spans, key=lambda span: span.start)
        cursor = 0
        for span in spans:
            if span.start != cursor:
                raise ValueError(
                    f"TokenSpan 未无缝平铺：期望下一段起点 {cursor}，得到 {span.start}"
                    "（存在缝隙或重叠——无人认领的 token 无法证明训练安全）。"
                )
            cursor = span.end
        if cursor != total:
            raise ValueError(
                f"TokenSpan 覆盖不完整：覆盖到 {cursor}，但 prompt+response={total}。"
            )

        # 2. LossMaskSpan 无缝平铺 response 段 [prompt, total)
        mask_spans = sorted(self.loss_mask_spans, key=lambda span: span.start)
        cursor = self.prompt_token_count
        for span in mask_spans:
            if span.start != cursor:
                raise ValueError(
                    f"LossMaskSpan 未无缝平铺 response 段：期望起点 {cursor}，得到 {span.start}"
                    f"（response 段为 [{self.prompt_token_count}, {total})）。"
                )
            cursor = span.end
        if cursor != total:
            raise ValueError(
                f"LossMaskSpan 覆盖不完整：覆盖到 {cursor}，response 段终点应为 {total}。"
            )

        # 3. mask=1 的 span 必须完全落在 sampled_assistant 区间内（先合并相邻区间）
        sampled_intervals: list[tuple[int, int]] = []
        for span in spans:
            if span.source_type != "sampled_assistant":
                continue
            if sampled_intervals and sampled_intervals[-1][1] == span.start:
                sampled_intervals[-1] = (sampled_intervals[-1][0], span.end)
            else:
                sampled_intervals.append((span.start, span.end))
        for span in mask_spans:
            if span.mask != 1:
                continue
            contained = any(start <= span.start and span.end <= end for start, end in sampled_intervals)
            if not contained:
                raise ValueError(
                    f"mask=1 的 span [{span.start},{span.end}) 未完全落在 sampled_assistant "
                    "token 区间内（H4：只有模型真实采样的 assistant token 允许参训）。"
                )

        # 3b. mask=0 的 span 与 sampled_assistant 区间重叠时，reason 必须是降级类（N-3）：
        #     采样 token 不训练只有三种合法故事——兄弟分支已训练（replayed_sibling_response）、
        #     漂移降级（retokenization_drift_downgraded）、文本中继无 token 捕获
        #     （token_capture_unavailable_downgraded，S1-8）；标 prompt_context 类
        #     "本来就是上下文"的理由会把降级事实伪装成正常上下文，审计线索就断了。
        downgrade_reasons = (
            "replayed_sibling_response",
            "retokenization_drift_downgraded",
            "token_capture_unavailable_downgraded",
        )
        for span in mask_spans:
            if span.mask != 0:
                continue
            overlaps_sampled = any(
                span.start < end and start < span.end for start, end in sampled_intervals
            )
            if overlaps_sampled and span.reason not in downgrade_reasons:
                raise ValueError(
                    f"mask=0 的 span [{span.start},{span.end}) 覆盖了 sampled_assistant 来源的 "
                    f"token，reason 必须是降级类 {downgrade_reasons}，得到 {span.reason!r}"
                    "（N-3：采样 token 不参训必须留下可审计的降级理由，不得标成普通上下文）。"
                )

        # 4. 有可训练 token 就必须有捕获记录回链
        has_trainable = any(span.mask == 1 for span in mask_spans)
        if has_trainable and not self.capture_record_refs:
            raise ValueError(
                "存在 mask=1 的 span 但 capture_record_refs 为空：可训练 token 必须能回链到 "
                "GenerationCaptureRecord 原始捕获事实（A4），否则 provenance 不成立。"
            )

        # 5. logprob 对齐结论与 provenance 的一致性
        if self.logprob_alignment_status == "aligned_per_token" and self.logprob_provenance is None:
            raise ValueError(
                "logprob_alignment_status=aligned_per_token 时必须携带 logprob_provenance（M4）。"
            )
        if self.logprob_alignment_status == "missing" and self.logprob_provenance is not None:
            raise ValueError(
                "logprob_alignment_status=missing 与 logprob_provenance 同时在场自相矛盾。"
            )

        # 6. tape 计数与分支计数互检（无 tape 声明——dense / 文本中继——没有可核对的计数）
        if self.routing.alignment not in _ROUTING_NO_TAPE_ALIGNMENTS:
            if self.routing.prompt_token_count != self.prompt_token_count:
                raise ValueError(
                    f"routing.prompt_token_count({self.routing.prompt_token_count}) 与分支 "
                    f"prompt_token_count({self.prompt_token_count}) 不一致。"
                )
            if self.routing.generated_token_count != self.response_token_count:
                raise ValueError(
                    f"routing.generated_token_count({self.routing.generated_token_count}) 与分支 "
                    f"response_token_count({self.response_token_count}) 不一致。"
                )
        if (
            self.sampling_mask.mask_kind == "top_p_kept_token_ids"
            and self.sampling_mask.response_token_count != self.response_token_count
        ):
            raise ValueError(
                f"sampling_mask.response_token_count({self.sampling_mask.response_token_count}) 与分支 "
                f"response_token_count({self.response_token_count}) 不一致。"
            )
        if self.sampling_mask.mask_kind == "top_p_kept_token_ids":
            # N-4 强下界（S1-7a 从 SamplingMaskRef 层移到本层）：每个可训练
            # token 都是引擎采样产物，核集合至少 1 个 -> kept >= Σ mask=1 长度。
            # response_token_count 不能作下界——多轮序列的工具观察/上下文 token
            # 从未被采样、span 恒零宽（真实反例见 SamplingMaskRef.kept_token_count 注释）。
            trainable_total = sum(
                span.end - span.start for span in mask_spans if span.mask == 1
            )
            kept = self.sampling_mask.kept_token_count or 0
            if kept < trainable_total:
                raise ValueError(
                    f"sampling_mask.kept_token_count({kept}) 小于分支 mask=1 token 总数 "
                    f"({trainable_total})：可训练 token 每个至少保留 1 个核 token，"
                    "tape 不完整或计数错误（N-4，S1-7a 座标修正版）。"
                )
        return self


class TrajectoryProjection(StrictModel):
    """框架中立的轨迹投影（治理层与所有训练后端 adapter 的唯一输入契约）。

    创建者：project_from_slime（训练主线）/ project_from_verifiers（评测、导出线）。
    消费者：EligibilityGate、public projection 扫描、离线导出 adapter、parity 校验。
    tape 解码只允许在投影层做一次（S0 结论 5），本对象即解码结果的落点。

    fan-out 建模（S1-1b 定案）：**单投影多 branches 为权威**——一个 rollout/session
    产一个本对象，compaction/fan-out 分段全部作为 branches。因此校验器强制
    reward_facts.segment_count == len(branches)（在场时），且多分支投影必须申报
    segment_count——否则 fan-out 的 loss 账目（防重复放大）无从核对。
    """

    schema_id: Literal["rh2.trajectory_projection.v1"] = Field(
        default="rh2.trajectory_projection.v1",
        description="schema 判别字段（inspect-rh2-artifact 用它选择校验模型）。",
    )
    trajectory_id: NonEmptyStr = Field(
        description="轨迹 id，与 EligibilityReport / GradingReport sidecar 的关联键。"
    )
    task_id: NonEmptyStr = Field(description="任务 id（如 django__django-11099）。")
    source_framework: Literal["slime", "verifiers"] = Field(
        description="投影来源框架（审计事实；治理逻辑不得按它分支，否则解耦失效）。"
    )
    source_object_ref: NonEmptyStr = Field(
        description="来源对象引用：slime 为 rollout/sample 标识，verifiers 为 trace_id。"
    )
    renderer_cls_name: NonEmptyStr = Field(
        description="渲染器类名（U-G：启动期断言用，防止静默降级 DefaultRenderer）。"
    )
    tokenizer_name: NonEmptyStr = Field(description="tokenizer 名称（如 Qwen/Qwen3-30B-A3B）。")
    chat_template_hash: Sha256Digest | None = Field(
        default=None, description="chat template 内容 digest（可选，renderer 漂移排查用）。"
    )
    branches: list[BranchProjection] = Field(
        min_length=1,
        description=(
            "可训练分支列表。单投影多 branches 为权威建模：一个 rollout 的全部 "
            "compaction/fan-out 分段并列于此，不拆成多个投影对象（S1-1b 定案）。"
        ),
    )
    reward_facts: RewardFacts = Field(
        description="轨迹级 reward 原始事实（归一化归训练后端，见 §16.11）。"
    )
    handshake: WeightVersionsHandshake | None = Field(
        default=None,
        description=(
            "staleness 记账（preflight §8 H-1）：Sample.weight_versions 原始 list + "
            "派生 max_lag 两口径。slime 主线由 project_from_slime 采集（训练侧转换会"
            "丢弃该字段，projection 层是唯一采集点）；文本中继（verifiers EvalClient）"
            "或来源 Sample 无版本事实时为 None。gate 只记录分布、不据此准入。"
        ),
    )
    created_at_utc: AwareDatetime = Field(
        description="投影生成时间（必须带时区；evidence 时间线核对用）。"
    )

    @model_validator(mode="after")
    def _check_projection_invariants(self) -> "TrajectoryProjection":
        branch_ids = [branch.branch_id for branch in self.branches]
        if len(branch_ids) != len(set(branch_ids)):
            raise ValueError(f"branch_id 必须在轨迹内唯一，得到 {branch_ids}。")

        # fan-out 账目互检（S1-1b 定案：单投影多 branches 为权威，分段即 branches）
        segment_count = self.reward_facts.segment_count
        if segment_count is not None and segment_count != len(self.branches):
            raise ValueError(
                f"reward_facts.segment_count({segment_count}) 与 len(branches)({len(self.branches)}) "
                "不一致：fan-out 分段全部作为本投影的 branches，两个计数必须相等"
                "（账目对不上说明分段被拆到了别的投影，或申报数被凭空放大）。"
            )
        if segment_count is None and len(self.branches) > 1:
            raise ValueError(
                f"多分支投影（len(branches)={len(self.branches)}）必须申报 "
                "reward_facts.segment_count：没有分段账目就无法防止 fan-out 后 "
                "reward/loss 重复放大（§16.11）。"
            )
        return self
