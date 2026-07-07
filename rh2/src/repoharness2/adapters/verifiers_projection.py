"""project_from_verifiers：verifiers Trace dict -> TrajectoryProjection（S1-8，评测/导出线）。

输入形态：verifiers `Trace.to_record()` 的 JSON dict（S0-3 toy_trace_dump 的
`traces[*]` 元素；字段名以 reference/verifiers/verifiers/v1/trace.py 与 graph.py
为准——顶层 `id/task/nodes/rewards/.../stop_condition/errors`，节点
`parent/message/sampled/token_ids/mask/is_content/logprobs/finish_reason/usage`）。
本模块只处理**纯 dict**，不 import verifiers（与 envpack 同一依赖纪律；
分支重建按 graph.leaves 同律自实现：无子节点的 node 即叶，叶回溯到根即分支）。

EvalClient 文本中继模式的显式降级（本模块 S1-8 的核心职责）：

EvalClient 是"一比一代理转发"（verifiers clients/eval.py）——不做客户端
tokenization，Trace 节点的 `token_ids/mask/logprobs/is_content` 全部为空
（S0-3 field_check.md 实测），唯一的 token 级事实是 provider 报告的 usage
计数。因此本投影**不可能 token-faithful**，降级必须显式、机器可读：

    1. token 计数座标系来自 usage（不是 token ids）：第 k 个采样轮的
       input_tokens = prompt_tokens + cached_input_tokens（verifiers
       Usage.input_tokens 同式）。逐轮差分重建计数布局：
       ctx_0 = i_1（首轮 prompt），ctx_k = i_{k+1} - (i_k + c_k)（第 k 轮后
       新增的工具/用户上下文），差分为负即拒收（usage 账目不自洽）。
       具体数值例（default_subprocess_deepseek 轨迹 d703bc8d，3 轮真实 usage）：
       i=[484,554,614]、c=[60,44,20] -> prompt 484，布局
       [484,544) 采样 | [544,554) 工具 | [554,598) 采样 | [598,614) 工具 |
       [614,634) 采样，total=634、response=150；
    2. 采样段 source_type 如实标 `sampled_assistant`（文本确实是模型采样的），
       但 loss mask 全 0 且理由必须是 `token_capture_unavailable_downgraded`
       ——token 身份不可证明的文本，一个 token 都不许申报可训练（H4）；
    3. `logprob_alignment_status="missing"` 且不携带 LogprobProvenance
       （schema 强制两者搭配——伪造一个 sglang/vllm 出处是不可表示的）；
    4. `sampling_mask.mask_kind="not_captured_text_relay"`（top_p=None：采样
       参数在 provider 侧、未捕获，禁止伪造 top_p=1.0）；
    5. `routing.alignment="not_captured_text_relay"`（模型是不是 MoE 都无从
       谈起，禁止谎报 not_applicable_dense_model）；
    6. `renderer_cls_name` / `tokenizer_name` 用显式哨兵值（本模块常量），
       声明"文本中继没有 renderer/tokenizer"而不是伪装某个真实类名。

资格后果（S1 gate 语义，parity-cross 的预期口径）：这种投影经 finalize_rollout
后 `logprob_alignment` 失败（logprob_missing，地板 offline）+
`loss_mask_integrity` 失败（no_trainable_tokens，地板 audit）→ 结论
audit_only_or_rejected，离线导出拒收。EvalClient 轨迹在 S1 的定位就是
评测与治理审计（E10/F1），不是训练数据来源；token-faithful 的 verifiers
路径（TrainClient + capture sidecar）显式不在 S1-8 范围内——节点带 token
字段时本模块直接拒收（reason=token_faithful_trace_not_supported），
绝不把 token-faithful 数据静默降级成文本级。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

from pydantic import Field

from repoharness2.contracts import (
    BranchProjection,
    LossMaskSpan,
    RewardFacts,
    RoutingTensorRef,
    SamplingMaskRef,
    StrictModel,
    TokenSpan,
    TrajectoryProjection,
)
from repoharness2.contracts._base import NonEmptyStr, SafeIdentifier
from repoharness2.contracts.trajectory import (
    CreditAssignmentStrategy,
    LossMaskReason,
    RewardScope,
    TokenSourceType,
)

__all__ = [
    "EVAL_RELAY_RENDERER_CLS_NAME",
    "VerifiersProjectionError",
    "VerifiersRewardInput",
    "eval_relay_tokenizer_name",
    "reward_input_from_trace",
    "project_from_verifiers",
]

# 文本中继哨兵值：显式声明"EvalClient 没有 renderer/tokenizer"，而不是伪装
# 某个真实 renderer 类名（U-G 断言遇到它必然失败——这是特性不是缺陷：
# 谁把 eval 中继投影接进训练主线的 renderer 守门，当场就会炸）。
EVAL_RELAY_RENDERER_CLS_NAME = "VerifiersEvalRelayNoRenderer"

_EVAL_RELAY_TOKENIZER_PREFIX = "eval_relay_untokenized"


def eval_relay_tokenizer_name(model_name: str) -> str:
    """文本中继的 tokenizer 哨兵名（如 eval_relay_untokenized:deepseek-chat）。"""

    return f"{_EVAL_RELAY_TOKENIZER_PREFIX}:{model_name}"


class VerifiersProjectionError(ValueError):
    """verifiers 投影层 fail-closed 拒收错误（reason_code 机器可读）。"""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"[{reason_code}] {message}")


class VerifiersRewardInput(StrictModel):
    """reward 原始事实的调用方输入（与 slime 侧 SlimeRewardInput 同形）。

    分段账目不收：segment_count 由投影按 len(branches) 自填；文本中继投影
    没有可训练 token，rollout_loss_denominator 恒为 None（schema 该字段 >= 1，
    "0 个可训练 token"的唯一诚实表示就是缺席）。
    """

    reward_scope: RewardScope
    raw_reward: float | None = None
    reward_event_refs: list[NonEmptyStr] = Field(default_factory=list)
    components: dict[SafeIdentifier, float] = Field(default_factory=dict)
    credit_assignment_strategy: CreditAssignmentStrategy
    group_id: NonEmptyStr | None = None
    parent_rollout_id: NonEmptyStr | None = None


def reward_input_from_trace(trace: Mapping[str, Any]) -> VerifiersRewardInput:
    """默认 reward 输入：直接取 Trace.rewards（taskset @reward 的逐函数贡献）。

    reward_event_refs 指向 trace 自身的 rewards 记录（评测线没有 GradingReport
    时的出处表示）；走 finalize_rollout 的调用方应改传显式输入、把
    reward_event_refs 指到本次 GradingReport.report_id（gate 会逐值对账）。
    """

    rewards = trace.get("rewards")
    if not isinstance(rewards, Mapping) or not rewards:
        raise VerifiersProjectionError(
            "trace_rewards_missing",
            "Trace.rewards 缺失或为空——没有任何评分事实的轨迹无法申报 reward；"
            "如确属未评分轨迹，请显式构造 VerifiersRewardInput(reward_scope='none')。",
        )
    return VerifiersRewardInput(
        reward_scope="trace_level",
        raw_reward=float(sum(float(v) for v in rewards.values())),
        reward_event_refs=[f"verifiers_trace_rewards:{trace.get('id')}"],
        components={str(k): float(v) for k, v in rewards.items()},
        credit_assignment_strategy="direct_trace_reward",
    )


# ---------------------------------------------------------------------------
# trace dict 读取与分支重建（graph.leaves 同律）
# ---------------------------------------------------------------------------


def _require(condition: bool, reason_code: str, message: str) -> None:
    if not condition:
        raise VerifiersProjectionError(reason_code, message)


def _branch_paths(nodes: Sequence[Mapping[str, Any]]) -> list[list[int]]:
    """叶节点回溯到根：与 verifiers graph.leaves + Trace.branches 同一定义。"""

    has_child = {node.get("parent") for node in nodes if node.get("parent") is not None}
    leaves = [idx for idx in range(len(nodes)) if idx not in has_child]
    paths: list[list[int]] = []
    for leaf in leaves:
        path: list[int] = []
        cursor: int | None = leaf
        while cursor is not None:
            _require(
                0 <= cursor < len(nodes),
                "trace_parent_pointer_invalid",
                f"节点 parent 指针 {cursor} 越界（nodes 共 {len(nodes)} 个）。",
            )
            path.append(cursor)
            cursor = nodes[cursor].get("parent")
        path.reverse()
        paths.append(path)
    return paths


def _usage_input_tokens(usage: Mapping[str, Any]) -> int:
    """verifiers Usage.input_tokens 同式：prompt_tokens + cached_input_tokens。"""

    return int(usage["prompt_tokens"]) + int(usage.get("cached_input_tokens") or 0)


# 轮间上下文段的来源标注：(TokenSpan.source_type, LossMaskSpan.reason) 显式映射。
_INTERSTITIAL_SPAN: dict[str, tuple[TokenSourceType, LossMaskReason]] = {
    "tool": ("tool_result", "tool_or_env_context"),
    "user": ("user_message", "user_or_system_message"),
    "other": ("harness_interstitial", "tool_or_env_context"),
}

# 采样段的显式降级标注（模块 docstring 第 2 条）。
_SAMPLED_SPAN: tuple[TokenSourceType, LossMaskReason] = (
    "sampled_assistant",
    "token_capture_unavailable_downgraded",
)


def _interstitial_kind(roles: Sequence[str]) -> str:
    if "tool" in roles:
        return "tool"
    if "user" in roles:
        return "user"
    return "other"


def _project_branch(
    branch_nodes: Sequence[Mapping[str, Any]], *, branch_id: str, trace_id: str
) -> BranchProjection:
    """一条叶链 -> 一条显式降级的 BranchProjection（usage 计数座标系）。"""

    # 1. token 级字段必须全空——带 token 的 Trace 属 TrainClient 路径，拒绝静默降级。
    for node in branch_nodes:
        for field_name in ("token_ids", "mask", "logprobs", "is_content"):
            if node.get(field_name):
                raise VerifiersProjectionError(
                    "token_faithful_trace_not_supported",
                    f"trace {trace_id}：节点带非空 {field_name}——这是 TrainClient 的 "
                    "token-faithful 轨迹，S1-8 的 project_from_verifiers 只实现 EvalClient "
                    "文本中继的显式降级路径，拒绝把 token-faithful 数据静默降级成文本级。",
                )

    # 2. 采样轮与轮间节点分组。
    sampled_indices = [idx for idx, node in enumerate(branch_nodes) if node.get("sampled")]
    _require(
        bool(sampled_indices),
        "branch_without_sampled_response",
        f"trace {trace_id} 分支 {branch_id}：没有任何模型采样节点，无 response 可投影。",
    )
    turns: list[tuple[int, int]] = []  # (input_tokens_k, completion_k)
    for idx in sampled_indices:
        node = branch_nodes[idx]
        role = (node.get("message") or {}).get("role")
        _require(
            role == "assistant",
            "sampled_node_not_assistant",
            f"trace {trace_id}：sampled 节点的角色是 {role!r}，与 verifiers 语义不符。",
        )
        usage = node.get("usage")
        _require(
            isinstance(usage, Mapping)
            and usage.get("prompt_tokens") is not None
            and usage.get("completion_tokens") is not None,
            "usage_facts_missing",
            f"trace {trace_id} 分支 {branch_id}：采样节点缺 provider usage——"
            "文本中继模式下 usage 是唯一 token 计数事实源，缺失即无坐标系可建。",
        )
        completion = int(usage["completion_tokens"])
        _require(
            completion >= 1,
            "sampled_turn_zero_completion",
            f"trace {trace_id} 分支 {branch_id}：某采样轮 completion_tokens={completion} < 1。",
        )
        turns.append((_usage_input_tokens(usage), completion))

    prompt_len = turns[0][0]
    _require(
        prompt_len >= 1,
        "prompt_token_count_invalid",
        f"trace {trace_id} 分支 {branch_id}：首轮 input_tokens={prompt_len} < 1。",
    )

    # 3. 逐轮差分出轮间上下文 token 数（模块 docstring 的 ctx_k 公式）。
    interstitial: list[tuple[int, str]] = []  # (token 数, kind)
    for k in range(len(turns) - 1):
        i_k, c_k = turns[k]
        i_next = turns[k + 1][0]
        delta = i_next - (i_k + c_k)
        _require(
            delta >= 0,
            "usage_accounting_inconsistent",
            f"trace {trace_id} 分支 {branch_id}：第 {k} 轮后上下文差分为 {delta} < 0"
            f"（i_{k + 1}={i_next} < i_{k}+c_{k}={i_k + c_k}）——provider usage 账目不自洽，"
            "计数座标系无法成立。",
        )
        between_roles = [
            str((node.get("message") or {}).get("role"))
            for node in branch_nodes[sampled_indices[k] + 1 : sampled_indices[k + 1]]
        ]
        interstitial.append((delta, _interstitial_kind(between_roles)))

    # 4. 平铺 TokenSpan / LossMaskSpan（mask 全 0，采样段用显式降级理由）。
    token_spans = [TokenSpan(start=0, end=prompt_len, source_type="prompt_context")]
    mask_spans: list[LossMaskSpan] = []
    cursor = prompt_len
    for k, (_, completion) in enumerate(turns):
        token_spans.append(
            TokenSpan(start=cursor, end=cursor + completion, source_type=_SAMPLED_SPAN[0])
        )
        mask_spans.append(
            LossMaskSpan(start=cursor, end=cursor + completion, mask=0, reason=_SAMPLED_SPAN[1])
        )
        cursor += completion
        if k < len(interstitial):
            delta, kind = interstitial[k]
            if delta > 0:
                source_type, reason = _INTERSTITIAL_SPAN[kind]
                token_spans.append(TokenSpan(start=cursor, end=cursor + delta, source_type=source_type))
                mask_spans.append(LossMaskSpan(start=cursor, end=cursor + delta, mask=0, reason=reason))
                cursor += delta

    return BranchProjection(
        branch_id=branch_id,
        prompt_token_count=prompt_len,
        response_token_count=cursor - prompt_len,
        token_spans=token_spans,
        loss_mask_spans=mask_spans,
        logprob_alignment_status="missing",  # 降级标注 3：无逐 token logprob，且不伪造出处
        logprob_provenance=None,
        routing=RoutingTensorRef(alignment="not_captured_text_relay"),  # 降级标注 5
        sampling_mask=SamplingMaskRef(mask_kind="not_captured_text_relay", top_p=None),  # 降级标注 4
        lineage=None,
        capture_record_refs=[],  # 没有 GenerationCaptureRecord——mask=1 因此不可表示（schema 链）
    )


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------


def project_from_verifiers(
    trace: Mapping[str, Any],
    *,
    model_name: str,
    task_id: str | None = None,
    reward: VerifiersRewardInput | None = None,
    created_at_utc: datetime | None = None,
) -> TrajectoryProjection:
    """把一条 verifiers Trace dict 投影成显式降级的 TrajectoryProjection。

    参数：
    - ``trace``：`Trace.to_record()` 的 dict（toy_trace_dump 的 `traces[*]`）。
    - ``model_name``：provider 模型名（dump 顶层 meta.model，如 "deepseek-chat"）。
      Trace 本体不含模型名，必须由调用方提供；用于 tokenizer 哨兵值。
    - ``task_id``：缺省取 `trace["task"]["name"]`。
    - ``reward``：缺省用 :func:`reward_input_from_trace`（Trace.rewards 直读）；
      走 finalize_rollout 时应显式传入并把 reward_event_refs 指向本次
      GradingReport.report_id（gate 逐值对账）。
    """

    _require(isinstance(trace, Mapping), "verifiers_trace_shape_invalid", "trace 必须是 dict。")
    trace_id = trace.get("id")
    _require(
        isinstance(trace_id, str) and bool(trace_id),
        "verifiers_trace_shape_invalid",
        "trace.id 缺失或为空。",
    )
    nodes = trace.get("nodes")
    _require(
        isinstance(nodes, list),
        "verifiers_trace_shape_invalid",
        f"trace {trace_id}：nodes 缺失或不是列表。",
    )

    paths = _branch_paths(nodes)
    _require(
        bool(paths),
        "trace_has_no_branches",
        f"trace {trace_id}：消息图为空（nodes={len(nodes)}），没有可投影的分支——"
        f"stop_condition={trace.get('stop_condition')!r}，"
        f"errors={[e.get('type') for e in trace.get('errors') or []]}"
        "（首轮模型调用即失败的 error 轨迹属此形态，只可审计不可投影）。",
    )
    if len(paths) > 1:
        raise VerifiersProjectionError(
            "eval_relay_multi_branch_not_supported",
            f"trace {trace_id}：{len(paths)} 条分支（compaction/subagent）。文本中继模式"
            "没有 token 级血缘（fork_point_token_index 无从谈起），CompactedSubTraceLineage "
            "无法诚实构造，S1-8 显式拒绝多分支 eval 轨迹（出现真实用例时再扩展）。",
        )

    if task_id is None:
        task = trace.get("task")
        task_name = task.get("name") if isinstance(task, Mapping) else None
        _require(
            isinstance(task_name, str) and bool(task_name),
            "task_identity_missing",
            f"trace {trace_id}：未显式传 task_id 且 trace.task.name 缺失。",
        )
        task_id = task_name

    reward_input = reward if reward is not None else reward_input_from_trace(trace)
    branches = [
        _project_branch([nodes[idx] for idx in path], branch_id=f"b{i}", trace_id=trace_id)
        for i, path in enumerate(paths)
    ]

    reward_facts = RewardFacts(
        reward_scope=reward_input.reward_scope,
        raw_reward=reward_input.raw_reward,
        components=dict(reward_input.components),
        reward_event_refs=list(reward_input.reward_event_refs),
        credit_assignment_strategy=reward_input.credit_assignment_strategy,
        group_id=reward_input.group_id,
        parent_rollout_id=reward_input.parent_rollout_id,
        segment_index=None,
        segment_count=len(branches),
        rollout_loss_denominator=None,  # 0 个可训练 token：唯一诚实表示是缺席（字段下界 1）
    )

    return TrajectoryProjection(
        trajectory_id=trace_id,
        task_id=task_id,
        source_framework="verifiers",
        source_object_ref=f"verifiers_trace_{trace_id}",
        renderer_cls_name=EVAL_RELAY_RENDERER_CLS_NAME,  # 降级标注 6：哨兵，不伪装真实 renderer
        tokenizer_name=eval_relay_tokenizer_name(model_name),
        chat_template_hash=None,
        branches=branches,
        reward_facts=reward_facts,
        created_at_utc=created_at_utc or datetime.now(timezone.utc),
    )
