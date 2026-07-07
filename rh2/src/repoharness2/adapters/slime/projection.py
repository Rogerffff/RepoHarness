"""project_from_slime：slime 产物 → 中立投影 TrajectoryProjection 的主线 adapter（S1-3）。

职责与边界（03 执行计划 S1-3 + S1-1b fan-out 定案）：

1. **一次 rollout/session 的全部 slime Sample 进一个投影**：slime TrajectoryManager
   把一个 session 的消息树线性化成若干叶链 Sample（compaction / fan-out 分段），
   本函数把它们并列为同一个 TrajectoryProjection 的 branches，并强制
   `reward_facts.segment_count == len(branches)`；调用方若另行申报分段数
   （`declared_segment_count`，对应 slime 同 rollout sibling 账目），不一致直接拒收。
2. **tape 解码唯一实现点**（S0 结论 5）：SGLang meta_info wire 形态的 base64
   int32 小端字节串、bytes、嵌套 list、带 ``.tolist()`` 的张量都在
   :func:`decode_int32_tape` 一处解码。routing 行数按引擎对齐公式校验——
   SGLang = prompt_len - 1 + generated_len（S1-0 实测 15-1+16=30 行）、
   vLLM = prompt_len + generated_len——差一行报错、绝不静默修正。
3. **loss mask 语义 H4（sampled ∧ role）**：slime ``loss_mask`` 只有 0/1、无理由码，
   映射必须显式——mask=1 → TokenSpan.source_type="sampled_assistant" +
   LossMaskSpan.reason="sampled_assistant_trainable"；mask=0 默认映射为
   "tool_result" + "tool_or_env_context"（工具/观测/模板文本）；其余 mask=0 来源
   （用户消息、兄弟分支重放、re-tokenization 漂移降级）由编排层通过
   :class:`ResponseContextRun` 显式注释，投影自己不猜。
4. **capture 回链（A4）**：每条含 mask=1 的分支必须回链 GenerationCaptureRecord，
   且回链记录必须 ``capture_status="complete"``。这与 capture 层"请求了 tape
   没返回则禁止 complete"的禁令首尾相接：tape 缺失时 capture 只能是 partial，
   而 partial 记录支撑的采样段在这里被拒绝进入投影。schema 本身不可表示
   "top_p<1.0 却没有 tape"（SamplingMaskRef）或"MoE 请求了 routing 却挂 dense
   声明"（RoutingTensorRef），因此投影层的"降级标注"落点 = 拒绝产出投影并抛
   :class:`SlimeProjectionError`，其 ``reason_code``（如
   ``top_p_tape_requested_but_missing``）就是机器可读的降级理由。

具体数值例（fixture 与 s1/uh_probe_result.json 同形）：prompt 15 token、生成
16 token、top_p=0.95 → offsets 长 17、routing tape 形状 [30, 48, 8]（30 =
15-1+16）。多轮分支例：prompt 22 + response 27（12 生成 + 6 工具 + 9 生成）
→ routing 行数 = 22-1+27 = 48 = len(tokens)-1（slime 每轮用最后一轮的全量
tape 整段替换，行数只依赖总 token 数，分支级公式因此恒成立）。
"""

from __future__ import annotations

import base64
import hashlib
import struct
from collections.abc import Mapping, MutableMapping, Sequence
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import Field, model_validator

from repoharness2.contracts import (
    ArtifactRef,
    BranchProjection,
    CompactedSubTraceLineage,
    GenerationCaptureRecord,
    LogprobProvenance,
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

# ---------------------------------------------------------------------------
# 错误类型：reason_code 即机器可读的降级标注
# ---------------------------------------------------------------------------


class SlimeProjectionError(ValueError):
    """投影层 fail-closed 拒收错误。

    ``reason_code`` 是稳定的机器可读标注（单测与上游编排都按它分支），
    例如 ``routing_rows_mismatch`` / ``top_p_tape_requested_but_missing`` /
    ``capture_record_not_complete``。schema 不可表示的降级状态（tape 请求了
    没返回等）没有"带病投影"可产出，唯一合法出口就是本异常。
    """

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"[{reason_code}] {message}")


# ---------------------------------------------------------------------------
# U-G 守门：renderer 类名断言（S1-6 启动期调用）
# ---------------------------------------------------------------------------


def assert_renderer_class(renderer: object, expected_cls_name: str) -> str:
    """断言 renderer 的类名与期望完全一致，防静默降级 DefaultRenderer（U-G）。

    背景（s0/v2_renderer_report.md §4）：用本地权重目录加载 tokenizer 时
    ``tokenizer.name_or_path`` 是路径字符串、renderer 注册表不命中，会**只打
    INFO 日志**就回落 DefaultRenderer——bridge 恒为 None、sampled_mask/is_content
    全空，token 保真训练目标全部失效。因此 S1-6 启动期必须调用本函数：
    ``assert_renderer_class(renderer, "Qwen3Renderer")``。

    参数 ``renderer`` 接受实例（取 ``type(renderer).__name__``）或已经拿到的
    类名字符串（capture record / 投影里的 renderer_cls_name 字段）。
    返回核对通过的实际类名，方便调用方直接写进 evidence。
    """

    actual = renderer if isinstance(renderer, str) else type(renderer).__name__
    if actual != expected_cls_name:
        raise SlimeProjectionError(
            "renderer_class_mismatch",
            f"renderer 类名断言失败：期望 {expected_cls_name!r}，实际 {actual!r}。"
            "最常见成因是本地路径加载 tokenizer 使注册表不命中、静默回落 "
            "DefaultRenderer（U-G）；此时 token 归属/采样掩码全部失效，必须在"
            "启动期拦下而不是等训练后排查。",
        )
    return actual


# ---------------------------------------------------------------------------
# tape 解码唯一实现点
# ---------------------------------------------------------------------------


def _flatten_int_sequence(value: Any, field_name: str, out: list[int]) -> None:
    for item in value:
        if isinstance(item, (list, tuple)):
            _flatten_int_sequence(item, field_name, out)
        elif isinstance(item, bool) or not isinstance(item, int):
            raise SlimeProjectionError(
                "tape_element_not_int",
                f"{field_name} 含非整数元素 {item!r}（类型 {type(item).__name__}）。",
            )
        else:
            out.append(item)


def decode_int32_tape(value: Any, *, field_name: str) -> list[int]:
    """把 SGLang / slime 的 tape 载荷解码成 int 列表（全模块唯一解码点）。

    接受四种形态（与 slime `decode_int32_meta_array` 对齐，但不依赖 torch）：

    1. base64 字符串——SGLang meta_info 的 wire 形态，按 int32 **小端**解码
       （与 ``torch.frombuffer(..., dtype=torch.int32)`` 在 x86_64/aarch64
       上的实际字节序一致）；
    2. bytes / bytearray / memoryview——同上；
    3. int 序列（允许嵌套，例如 routing 的 [rows][layers][topk] 三层 list）；
    4. 带 ``.tolist()`` 的张量对象（torch/numpy duck 型，本模块不 import torch）。
    """

    if value is None:
        raise SlimeProjectionError("tape_payload_missing", f"{field_name} 为 None，无法解码。")
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, str):
        try:
            value = base64.b64decode(value.encode("ascii"), validate=True)
        except Exception as exc:  # noqa: BLE001 - 统一转成投影错误
            raise SlimeProjectionError(
                "tape_base64_invalid", f"{field_name} base64 解码失败：{exc}"
            ) from None
    if isinstance(value, (bytes, bytearray, memoryview)):
        raw = bytes(value)
        if len(raw) % 4 != 0:
            raise SlimeProjectionError(
                "tape_bytes_not_int32",
                f"{field_name} 字节数 {len(raw)} 不是 4 的倍数，不能按 int32 小端解码。",
            )
        return list(struct.unpack(f"<{len(raw) // 4}i", raw))
    if isinstance(value, (list, tuple)):
        out: list[int] = []
        _flatten_int_sequence(value, field_name, out)
        return out
    raise SlimeProjectionError(
        "tape_type_unsupported",
        f"{field_name} 类型 {type(value).__name__} 不是可解码的 tape 载荷。",
    )


def _int32_bytes(values: Sequence[int], field_name: str) -> bytes:
    try:
        return struct.pack(f"<{len(values)}i", *values)
    except struct.error as exc:
        raise SlimeProjectionError(
            "tape_value_out_of_int32", f"{field_name} 含超出 int32 范围的值：{exc}"
        ) from None


def _make_artifact_ref(
    ref_id: str, values: Sequence[int], store: MutableMapping[str, bytes] | None
) -> ArtifactRef:
    """把解码后的 tape 规范化为小端 int32 字节流，生成带 digest 的引用。

    契约对象只存引用不存载荷（_base.py 原则 3）；调用方给了 ``store``
    （例如 S1-6 的 artifact 目录写入器）就顺手落盘，没给也不影响 digest。
    """

    payload = _int32_bytes(values, ref_id)
    digest = "sha256:" + hashlib.sha256(payload).hexdigest()
    if store is not None:
        store[ref_id] = payload
    return ArtifactRef(ref_id=ref_id, sha256=digest, byte_size=len(payload))


# ---------------------------------------------------------------------------
# 编排层注释输入（loss mask 来源区分 + capture 回链 + 血缘）
# ---------------------------------------------------------------------------

# mask=0 上下文段的显式来源标注。slime loss_mask 只有 0/1，"这段 0 是工具输出
# 还是兄弟分支重放"只有编排层（TrajectoryManager 树侧）知道，必须显式传入。
ContextRunKind = Literal[
    "tool_result",
    "user_message",
    "system_scaffold",
    "harness_interstitial",
    "replayed_assistant_context",  # 兄弟叶链已训练过、本分支 loss_mask=0 重放（response_trained 语义）
    "retokenization_drift_downgraded",  # REALIGN 修复后无法证明采样来源的降级段
]

# slime loss_mask / 注释 kind → (TokenSpan.source_type, LossMaskSpan.reason) 的显式映射（H4）。
_MASK1_SOURCE_AND_REASON: tuple[TokenSourceType, LossMaskReason] = (
    "sampled_assistant",
    "sampled_assistant_trainable",
)
_MASK0_DEFAULT_SOURCE_AND_REASON: tuple[TokenSourceType, LossMaskReason] = (
    "tool_result",
    "tool_or_env_context",
)
_CONTEXT_KIND_TO_SPAN: dict[str, tuple[TokenSourceType, LossMaskReason]] = {
    "tool_result": ("tool_result", "tool_or_env_context"),
    "user_message": ("user_message", "user_or_system_message"),
    "system_scaffold": ("system_scaffold", "user_or_system_message"),
    "harness_interstitial": ("harness_interstitial", "tool_or_env_context"),
    "replayed_assistant_context": ("replayed_assistant_context", "replayed_sibling_response"),
    "retokenization_drift_downgraded": (
        "replayed_assistant_context",
        "retokenization_drift_downgraded",
    ),
}


class ResponseContextRun(StrictModel):
    """response 段内一段 mask=0 token 的显式来源标注（半开区间，全序列座标）。

    座标系与 TokenSpan 相同：0 起、含 prompt 段偏移。例如 prompt 22、生成 12
    后接 6 个工具 token，则工具段是 [34, 40)。只允许标注 mask=0 的 token——
    标到 mask=1 上说明编排层与 loss_mask 打架，直接拒收。
    """

    start: int = Field(ge=0, description="区间起点（含），全序列 0 起下标。")
    end: int = Field(gt=0, description="区间终点（不含），必须大于 start。")
    kind: ContextRunKind = Field(description="本段 mask=0 token 的真实来源。")

    @model_validator(mode="after")
    def _check_interval(self) -> "ResponseContextRun":
        if self.end <= self.start:
            raise ValueError(f"ResponseContextRun 区间非法：end({self.end}) <= start({self.start})。")
        return self


class SlimeBranchAnnotation(StrictModel):
    """一条 slime Sample（叶链分段）的编排层注释，与 samples 一一对应。

    为什么是显式参数而不是塞 Sample.metadata：宿主 metadata 是 S1-5 派生视图
    白名单管的地盘（只许两个白名单键），治理事实经私货 key 走私会绕开扫描；
    注释作为函数参数进来，fixture 与真实编排走同一条显式通道。
    """

    branch_id: NonEmptyStr = Field(description="分支 id（投影内唯一），例如 b0/b1。")
    capture_record_ids: list[NonEmptyStr] = Field(
        default_factory=list,
        description="支撑本分支采样段的 GenerationCaptureRecord.record_id（按轮次序）。",
    )
    lineage: CompactedSubTraceLineage | None = Field(
        default=None, description="compaction/分叉血缘；根分支为 None。"
    )
    context_runs: list[ResponseContextRun] = Field(
        default_factory=list,
        description="mask=0 段的显式来源标注；未标注的 mask=0 token 默认 tool_result。",
    )


class SlimeRewardInput(StrictModel):
    """reward 原始事实的调用方输入（RewardFacts 的去分段账目版）。

    分段账目两项不收：``segment_count`` 由投影按 len(branches) 自填、
    ``rollout_loss_denominator`` 按全分支 mask=1 token 总数自算
    （slime rollout_mask_sums 语义）——账目由投影层自证，调用方只给 reward 事实。
    """

    reward_scope: RewardScope
    raw_reward: float | None = None
    reward_event_refs: list[NonEmptyStr] = Field(default_factory=list)
    components: dict[SafeIdentifier, float] = Field(default_factory=dict)
    credit_assignment_strategy: CreditAssignmentStrategy
    group_id: NonEmptyStr | None = None
    parent_rollout_id: NonEmptyStr | None = None


# ---------------------------------------------------------------------------
# slime Sample duck 型读取（不 import slime / torch）
# ---------------------------------------------------------------------------

_PROJECTABLE_STATUSES = frozenset({"completed", "truncated"})


def _to_int_list(value: Any, field_name: str) -> list[int]:
    if value is None:
        raise SlimeProjectionError("sample_field_missing", f"{field_name} 缺失（None）。")
    if hasattr(value, "tolist"):
        value = value.tolist()
    if not isinstance(value, (list, tuple)):
        raise SlimeProjectionError(
            "sample_field_type", f"{field_name} 类型 {type(value).__name__} 不是整数序列。"
        )
    out: list[int] = []
    _flatten_int_sequence(value, field_name, out)
    return out


def _to_float_list(value: Any, field_name: str) -> list[float]:
    if hasattr(value, "tolist"):
        value = value.tolist()
    if not isinstance(value, (list, tuple)):
        raise SlimeProjectionError(
            "sample_field_type", f"{field_name} 类型 {type(value).__name__} 不是浮点序列。"
        )
    out: list[float] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise SlimeProjectionError(
                "sample_field_type", f"{field_name} 含非数值元素 {item!r}。"
            )
        out.append(float(item))
    return out


def _normalized_status(sample: Any) -> str:
    status = getattr(sample, "status", None)
    value = getattr(status, "value", status)
    if not isinstance(value, str) or not value:
        raise SlimeProjectionError(
            "sample_status_missing", "Sample.status 缺失或不是字符串/枚举，无法判断可投影性。"
        )
    return value.lower()


def _uniform_capture_fact(
    records: Sequence[GenerationCaptureRecord], field_name: str
) -> Any:
    values = {getattr(record, field_name) for record in records}
    if len(values) != 1:
        raise SlimeProjectionError(
            "capture_facts_not_uniform",
            f"capture 记录的 {field_name} 不一致：{sorted(map(repr, values))}——"
            "一个投影只对应一个 serving 事实组合（混引擎/混模板必须拆投影）。",
        )
    return values.pop()


# ---------------------------------------------------------------------------
# 分支装配内部件
# ---------------------------------------------------------------------------


def _merge_runs(values: Sequence[tuple[Any, ...]], offset: int) -> list[tuple[int, int, tuple[Any, ...]]]:
    """把逐 token 标签压成 (start, end, label) 连续段；start/end 已加 offset。"""

    runs: list[tuple[int, int, tuple[Any, ...]]] = []
    for idx, label in enumerate(values):
        pos = offset + idx
        if runs and runs[-1][2] == label and runs[-1][1] == pos:
            runs[-1] = (runs[-1][0], pos + 1, label)
        else:
            runs.append((pos, pos + 1, label))
    return runs


def _build_response_labels(
    loss_mask: Sequence[int],
    annotation: SlimeBranchAnnotation,
    prompt_len: int,
    total: int,
    branch_id: str,
) -> list[tuple[TokenSourceType, LossMaskReason]]:
    """逐 response token 生成 (source_type, reason)：显式映射 + 注释覆盖。"""

    labels: list[tuple[TokenSourceType, LossMaskReason]] = [
        _MASK1_SOURCE_AND_REASON if mask == 1 else _MASK0_DEFAULT_SOURCE_AND_REASON
        for mask in loss_mask
    ]
    claimed = [False] * len(loss_mask)
    for run in annotation.context_runs:
        if run.start < prompt_len or run.end > total:
            raise SlimeProjectionError(
                "context_run_out_of_response",
                f"分支 {branch_id} 的注释段 [{run.start},{run.end}) 越出 response 段 "
                f"[{prompt_len},{total})——注释只能标 response 段的 mask=0 token。",
            )
        for pos in range(run.start, run.end):
            rel = pos - prompt_len
            if claimed[rel]:
                raise SlimeProjectionError(
                    "context_runs_overlap",
                    f"分支 {branch_id} 的注释段在 token {pos} 处重叠——同一 token 只许一个来源。",
                )
            if loss_mask[rel] == 1:
                raise SlimeProjectionError(
                    "context_run_covers_trainable_token",
                    f"分支 {branch_id} 的注释段 [{run.start},{run.end}) 覆盖了 mask=1 的 "
                    f"token {pos}：上下文注释与 loss_mask 矛盾（H4：采样 token 不是上下文）。",
                )
            claimed[rel] = True
            labels[rel] = _CONTEXT_KIND_TO_SPAN[run.kind]
    return labels


def _build_sampling_mask(
    sample: Any,
    *,
    branch_id: str,
    trajectory_id: str,
    response_len: int,
    loss_mask: Sequence[int],
    top_p: float,
    tape_requested: bool,
    store: MutableMapping[str, bytes] | None,
) -> SamplingMaskRef:
    ids_raw = getattr(sample, "rollout_top_p_token_ids", None)
    offsets_raw = getattr(sample, "rollout_top_p_token_offsets", None)
    if (ids_raw is None) != (offsets_raw is None):
        raise SlimeProjectionError(
            "top_p_tape_incomplete_pair",
            f"分支 {branch_id} 的 top-p tape 只有一半（ids 与 offsets 必须成对，slime 同款约束）。",
        )

    if top_p >= 1.0:
        if ids_raw is not None:
            raise SlimeProjectionError(
                "unexpected_top_p_tape",
                f"分支 {branch_id}：top_p=1.0 不存在核截断，却带了 top-p tape——"
                "参数与载荷矛盾，禁止静默取舍。",
            )
        return SamplingMaskRef(mask_kind="not_applicable_top_p_1", top_p=1.0)

    if ids_raw is None:
        if tape_requested:
            raise SlimeProjectionError(
                "top_p_tape_requested_but_missing",
                f"分支 {branch_id}：capture 记录申明请求了 top-p tape"
                "（return_top_p_token_ids=True 且 top_p<1.0），但 Sample 上没有 "
                "rollout_top_p_token_ids/offsets。这是 stock SGLang 静默忽略的典型形态"
                "（S0-6 分水岭证据）——capture 层禁止此时标 complete，投影层同样拒绝"
                "产出投影（schema 不可表示缺 tape 的 top_p<1.0）。",
            )
        raise SlimeProjectionError(
            "top_p_tape_required",
            f"分支 {branch_id}：top_p={top_p} < 1.0 却没有 top-p tape 且请求侧也没开"
            " return_top_p_token_ids——E2 硬依赖：没有 tape 的 top-p 采样不可重放，"
            "不得进入训练。",
        )

    ids = decode_int32_tape(ids_raw, field_name=f"{branch_id}.rollout_top_p_token_ids")
    offsets = decode_int32_tape(
        offsets_raw, field_name=f"{branch_id}.rollout_top_p_token_offsets"
    )
    if len(offsets) != response_len + 1:
        raise SlimeProjectionError(
            "top_p_offsets_length_mismatch",
            f"分支 {branch_id}：top-p offsets 长度必须等于 response_token_count + 1 "
            f"= {response_len + 1}，实际 {len(offsets)}（差一也必须报错，不做修正）。",
        )
    if offsets[0] != 0:
        raise SlimeProjectionError(
            "top_p_offsets_not_zero_based", f"分支 {branch_id}：offsets[0] 必须为 0，得到 {offsets[0]}。"
        )
    for idx in range(response_len):
        width = offsets[idx + 1] - offsets[idx]
        if width < 0:
            raise SlimeProjectionError(
                "top_p_offsets_not_monotonic",
                f"分支 {branch_id}：offsets 在第 {idx} 个 token 处递减"
                f"（{offsets[idx]} -> {offsets[idx + 1]}）。",
            )
        if width == 0 and loss_mask[idx] == 1:
            raise SlimeProjectionError(
                "top_p_empty_span_for_trainable_token",
                f"分支 {branch_id}：第 {idx} 个 response token 是 mask=1 采样 token，"
                "top-p 核集合却是零宽——采样 token 的核集合至少含 1 个 token；"
                "零宽 pad 只允许出现在工具/上下文（mask=0）token 上（slime pad 语义）。",
            )
    if offsets[-1] != len(ids):
        raise SlimeProjectionError(
            "top_p_ids_offsets_mismatch",
            f"分支 {branch_id}：offsets[-1]={offsets[-1]} 与 ids 总数 {len(ids)} 不一致。",
        )

    ids_ref = _make_artifact_ref(f"{trajectory_id}_{branch_id}_topp_ids", ids, store)
    offsets_ref = _make_artifact_ref(f"{trajectory_id}_{branch_id}_topp_offsets", offsets, store)
    return SamplingMaskRef(
        mask_kind="top_p_kept_token_ids",
        top_p=top_p,
        token_ids_ref=ids_ref,
        offsets_ref=offsets_ref,
        response_token_count=response_len,
        offsets_len=len(offsets),
        kept_token_count=offsets[-1],
    )


def _routing_flat_and_dims(
    raw: Any,
    *,
    branch_id: str,
    moe_num_layers: int | None,
    moe_router_topk: int | None,
) -> tuple[list[int], int, int, int]:
    """解码 routing tape 并推断 (rows, layers, topk)。

    嵌套 list / 张量（slime `rollout_routed_experts` reshape 后的形态）自带形状；
    base64 / bytes / 扁平 list（SGLang wire 形态）必须由调用方给 moe_num_layers
    与 moe_router_topk 才能切行。
    """

    field_name = f"{branch_id}.rollout_routed_experts"
    if hasattr(raw, "tolist"):
        raw = raw.tolist()
    if isinstance(raw, (list, tuple)) and raw and isinstance(raw[0], (list, tuple)):
        rows = len(raw)
        layer_lens = {len(row) for row in raw}
        cell_lens = {len(cell) for row in raw for cell in row}
        if len(layer_lens) != 1 or len(cell_lens) != 1:
            raise SlimeProjectionError(
                "routing_shape_ragged", f"{field_name} 各行/各层长度不一致，不是规整 [rows][layers][topk]。"
            )
        layers, topk = layer_lens.pop(), cell_lens.pop()
        if (moe_num_layers is not None and moe_num_layers != layers) or (
            moe_router_topk is not None and moe_router_topk != topk
        ):
            raise SlimeProjectionError(
                "routing_shape_mismatch",
                f"{field_name} 自带形状 [*, {layers}, {topk}] 与调用方申报 "
                f"[*, {moe_num_layers}, {moe_router_topk}] 不一致。",
            )
        flat = decode_int32_tape(raw, field_name=field_name)
        return flat, rows, layers, topk

    flat = decode_int32_tape(raw, field_name=field_name)
    if moe_num_layers is None or moe_router_topk is None:
        raise SlimeProjectionError(
            "routing_shape_unknown",
            f"{field_name} 是扁平载荷（base64/bytes/一维 list），必须提供 "
            "moe_num_layers 与 moe_router_topk 才能切行（Qwen3-30B-A3B 为 48 与 8）。",
        )
    per_row = moe_num_layers * moe_router_topk
    if per_row <= 0 or len(flat) % per_row != 0:
        raise SlimeProjectionError(
            "routing_numel_mismatch",
            f"{field_name} 元素数 {len(flat)} 不能按每行 {per_row}"
            f"（{moe_num_layers}x{moe_router_topk}）整除。",
        )
    return flat, len(flat) // per_row, moe_num_layers, moe_router_topk


def _build_routing(
    sample: Any,
    *,
    branch_id: str,
    trajectory_id: str,
    prompt_len: int,
    response_len: int,
    engine_name: str,
    tape_requested: bool,
    moe_num_layers: int | None,
    moe_router_topk: int | None,
    store: MutableMapping[str, bytes] | None,
) -> RoutingTensorRef:
    raw = getattr(sample, "rollout_routed_experts", None)
    if raw is None:
        if tape_requested:
            raise SlimeProjectionError(
                "routing_tape_requested_but_missing",
                f"分支 {branch_id}：capture 记录申明请求了 routing tape"
                "（return_routed_experts=True），但 Sample 上没有 rollout_routed_experts。"
                "A2：routing 缺失不得静默成功，也不得谎报 not_applicable_dense_model"
                "（那是 dense 模型专用声明）；capture 层此时禁止 complete，投影层拒绝产出。",
            )
        return RoutingTensorRef(alignment="not_applicable_dense_model")

    if not tape_requested:
        raise SlimeProjectionError(
            "unexpected_routing_tape",
            f"分支 {branch_id}：请求侧未开 return_routed_experts，Sample 却带了 routing tape"
            "——事实与请求矛盾，禁止静默取舍。",
        )

    flat, rows, layers, topk = _routing_flat_and_dims(
        raw, branch_id=branch_id, moe_num_layers=moe_num_layers, moe_router_topk=moe_router_topk
    )
    if engine_name == "sglang":
        alignment = "sglang_prompt_minus1_plus_gen"
        expected_rows = prompt_len - 1 + response_len
    else:  # vllm
        alignment = "vllm_prompt_plus_gen"
        expected_rows = prompt_len + response_len
    if rows != expected_rows:
        raise SlimeProjectionError(
            "routing_rows_mismatch",
            f"分支 {branch_id}：routing 行数与引擎约定不符——engine={engine_name}，"
            f"prompt={prompt_len}，generated={response_len}，期望 {expected_rows} 行，"
            f"实际 {rows} 行。差一行也必须报错，绝不静默裁剪或补行（S1-0 对齐事实）。",
        )
    tensor_ref = _make_artifact_ref(f"{trajectory_id}_{branch_id}_routing_tape", flat, store)
    return RoutingTensorRef(
        alignment=alignment,
        tensor_ref=tensor_ref,
        num_rows=rows,
        num_layers=layers,
        router_topk=topk,
        dtype="int32",
        prompt_token_count=prompt_len,
        generated_token_count=response_len,
    )


def _project_branch(
    sample: Any,
    annotation: SlimeBranchAnnotation,
    *,
    trajectory_id: str,
    records_by_id: Mapping[str, GenerationCaptureRecord],
    engine_name: str,
    engine_version: str,
    top_p: float,
    serving_precision: str,
    serving_sampling_backend: str | None,
    moe_num_layers: int | None,
    moe_router_topk: int | None,
    store: MutableMapping[str, bytes] | None,
) -> tuple[BranchProjection, int]:
    """一条 slime Sample -> 一条 BranchProjection；返回 (分支, mask=1 token 数)。"""

    branch_id = annotation.branch_id

    if bool(getattr(sample, "remove_sample", False)):
        raise SlimeProjectionError(
            "sample_marked_removed",
            f"分支 {branch_id}：Sample.remove_sample=True（slime 会把它的 loss mask 清零丢弃），"
            "不应进入投影。",
        )
    status = _normalized_status(sample)
    if status not in _PROJECTABLE_STATUSES:
        raise SlimeProjectionError(
            "sample_status_not_projectable",
            f"分支 {branch_id}：Sample.status={status!r} 不可投影"
            "（只接受 completed/truncated；aborted/failed/pending 属于未完成产物）。",
        )

    tokens = _to_int_list(getattr(sample, "tokens", None), f"{branch_id}.tokens")
    response_len = getattr(sample, "response_length", None)
    if not isinstance(response_len, int) or response_len < 1:
        raise SlimeProjectionError(
            "response_empty", f"分支 {branch_id}：response_length={response_len!r} 非正整数。"
        )
    prompt_len = len(tokens) - response_len
    if prompt_len < 1:
        raise SlimeProjectionError(
            "prompt_length_invalid",
            f"分支 {branch_id}：len(tokens)={len(tokens)} 减 response_length={response_len} "
            f"得 prompt 段 {prompt_len} token——投影要求 prompt/response 段都至少 1 个 token。",
        )
    total = len(tokens)

    loss_mask_raw = getattr(sample, "loss_mask", None)
    if loss_mask_raw is None:
        raise SlimeProjectionError(
            "loss_mask_missing",
            f"分支 {branch_id}：loss_mask 缺失。slime 语义下缺省等于整段 response 参训，"
            "投影层拒绝这种隐式全 1——必须显式携带（H1 loss mask 可解释）。",
        )
    loss_mask = _to_int_list(loss_mask_raw, f"{branch_id}.loss_mask")
    if len(loss_mask) != response_len:
        raise SlimeProjectionError(
            "loss_mask_length_mismatch",
            f"分支 {branch_id}：loss_mask 长度 {len(loss_mask)} != response_length {response_len}"
            "（slime 自身不变量已破坏，上游数据不可信）。",
        )
    if any(mask not in (0, 1) for mask in loss_mask):
        raise SlimeProjectionError(
            "loss_mask_value_invalid", f"分支 {branch_id}：loss_mask 含 0/1 以外的值。"
        )
    trainable_count = sum(loss_mask)
    if trainable_count == 0:
        raise SlimeProjectionError(
            "branch_without_trainable_tokens",
            f"分支 {branch_id}：没有任何 mask=1 token。slime TrajectoryManager 只输出 "
            "has_trained_response 的叶链分段，零可训练分段不应出现在投影输入里。",
        )

    labels = _build_response_labels(loss_mask, annotation, prompt_len, total, branch_id)

    # capture 回链：先解析引用，tape 检查给出更具体的 reason 后，再兜底核对完整性。
    if not annotation.capture_record_ids:
        raise SlimeProjectionError(
            "capture_backlink_missing",
            f"分支 {branch_id} 含 {trainable_count} 个 mask=1 token 却没有 capture 回链"
            "（A4：可训练 token 必须回链 GenerationCaptureRecord，禁止从训练后的 Sample 反推）。",
        )
    linked_records: list[GenerationCaptureRecord] = []
    for record_id in annotation.capture_record_ids:
        record = records_by_id.get(record_id)
        if record is None:
            raise SlimeProjectionError(
                "capture_record_unknown",
                f"分支 {branch_id} 回链的 capture 记录 {record_id!r} 不在传入的 capture_records 里。",
            )
        linked_records.append(record)

    top_p_requested = any(
        record.sampling_params.return_top_p_token_ids for record in linked_records
    )
    routing_requested = any(
        record.sampling_params.return_routed_experts for record in linked_records
    )

    sampling_mask = _build_sampling_mask(
        sample,
        branch_id=branch_id,
        trajectory_id=trajectory_id,
        response_len=response_len,
        loss_mask=loss_mask,
        top_p=top_p,
        tape_requested=top_p_requested,
        store=store,
    )
    routing = _build_routing(
        sample,
        branch_id=branch_id,
        trajectory_id=trajectory_id,
        prompt_len=prompt_len,
        response_len=response_len,
        engine_name=engine_name,
        tape_requested=routing_requested,
        moe_num_layers=moe_num_layers,
        moe_router_topk=moe_router_topk,
        store=store,
    )

    # 对齐 capture 层 complete 禁令：partial/failed 记录支撑的采样段不得进投影。
    not_complete = [
        record.record_id for record in linked_records if record.capture_status != "complete"
    ]
    if not_complete:
        raise SlimeProjectionError(
            "capture_record_not_complete",
            f"分支 {branch_id} 回链的 capture 记录 {not_complete} 不是 complete——"
            "未完整捕获（tape 缺失/abort 截断）的轮次支撑不了 mask=1 采样段，"
            "投影层与 capture 层的 complete 禁令首尾相接，一律拒收。",
        )
    backing = sum(record.response_token_count for record in linked_records)
    if backing < trainable_count:
        raise SlimeProjectionError(
            "capture_backing_insufficient",
            f"分支 {branch_id}：回链 capture 记录合计 response_token_count={backing}，"
            f"小于分支 mask=1 token 数 {trainable_count}——存在没有捕获凭据的可训练 token。",
        )

    # logprob 对齐结论 + 出处
    logprobs_raw = getattr(sample, "rollout_log_probs", None)
    if logprobs_raw is None:
        logprob_status = "missing"
        provenance = None
    else:
        logprobs = _to_float_list(logprobs_raw, f"{branch_id}.rollout_log_probs")
        if len(logprobs) != response_len:
            raise SlimeProjectionError(
                "rollout_log_probs_length_mismatch",
                f"分支 {branch_id}：rollout_log_probs 长度 {len(logprobs)} != "
                f"response_length {response_len}（slime 自身不变量已破坏）。",
            )
        logprob_status = "aligned_per_token"
        weight_versions = list(getattr(sample, "weight_versions", None) or [])
        unique_versions = sorted(set(weight_versions))
        weight_version = unique_versions[0] if len(unique_versions) == 1 else None
        provenance = LogprobProvenance(
            engine_name=engine_name,  # type: ignore[arg-type]
            engine_version=engine_version,
            precision=serving_precision,  # type: ignore[arg-type]
            sampling_backend=serving_sampling_backend,
            weight_version=weight_version,
        )

    token_spans = [TokenSpan(start=0, end=prompt_len, source_type="prompt_context")]
    for start, end, label in _merge_runs([(lbl[0],) for lbl in labels], prompt_len):
        token_spans.append(TokenSpan(start=start, end=end, source_type=label[0]))
    loss_mask_spans = []
    for start, end, label in _merge_runs(
        [(mask, lbl[1]) for mask, lbl in zip(loss_mask, labels)], prompt_len
    ):
        loss_mask_spans.append(
            LossMaskSpan(start=start, end=end, mask=label[0], reason=label[1])
        )

    branch = BranchProjection(
        branch_id=branch_id,
        prompt_token_count=prompt_len,
        response_token_count=response_len,
        token_spans=token_spans,
        loss_mask_spans=loss_mask_spans,
        logprob_alignment_status=logprob_status,  # type: ignore[arg-type]
        logprob_provenance=provenance,
        routing=routing,
        sampling_mask=sampling_mask,
        lineage=annotation.lineage,
        capture_record_refs=list(annotation.capture_record_ids),
    )
    return branch, trainable_count


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------


def project_from_slime(
    samples: Sequence[Any],
    capture_records: Sequence[GenerationCaptureRecord],
    *,
    task_id: str,
    annotations: Sequence[SlimeBranchAnnotation],
    reward: SlimeRewardInput,
    serving_precision: Literal["float32", "bfloat16", "float16", "float64"],
    serving_sampling_backend: str | None = None,
    expected_renderer_cls_name: str | None = None,
    declared_segment_count: int | None = None,
    moe_num_layers: int | None = None,
    moe_router_topk: int | None = None,
    artifact_store: MutableMapping[str, bytes] | None = None,
    created_at_utc: datetime | None = None,
) -> TrajectoryProjection:
    """把一次 rollout/session 的全部 slime Sample 投影成一个 TrajectoryProjection。

    参数要点：

    - ``samples``：slime TrajectoryManager 对该 session 输出的全部叶链 Sample
      （duck 型读取 tokens/response_length/loss_mask/rollout_log_probs/
      rollout_top_p_token_ids/rollout_top_p_token_offsets/rollout_routed_experts/
      weight_versions/status/rollout_id/index，不 import slime）。
      注意：TrajectoryManager 的叶链产物**本身不带 tape 字段**（TurnRecord 只有
      prompt/output ids 与 logprobs），S1-6 编排必须先用 capture 钩子把逐轮 tape
      合并回填到 Sample 上再调本函数（字段在 slime Sample 上都存在、可写）。
    - ``capture_records``：本 trajectory 的全部 GenerationCaptureRecord；
      renderer/tokenizer/template/引擎版本等 serving 事实从这里取并要求全体一致。
    - ``annotations``：与 samples 一一对应的编排层注释（分支 id、capture 回链、
      血缘、mask=0 来源标注）。
    - ``serving_precision`` / ``serving_sampling_backend``：LogprobProvenance 的
      精度与采样后端事实。capture schema 没有这两个字段，事实源是引擎
      server_info（S1-0 探针：dtype=bfloat16、sampling_backend=pytorch）。
    - ``declared_segment_count``：slime 侧对本 rollout 分段数的申报（同
      rollout_id 的 sibling 数）；与 len(branches) 不一致直接拒收。
    - ``artifact_store``：可选 ``MutableMapping[str, bytes]``——解码后的分支级
      tape 以小端 int32 字节流落盘，key 即 ArtifactRef.ref_id。
    """

    if not samples:
        raise SlimeProjectionError("no_samples", "samples 为空：没有可投影的 slime Sample。")
    if len(annotations) != len(samples):
        raise SlimeProjectionError(
            "annotations_length_mismatch",
            f"annotations 数量 {len(annotations)} 与 samples 数量 {len(samples)} 不一致"
            "（注释与叶链分段一一对应）。",
        )
    branch_ids = [annotation.branch_id for annotation in annotations]
    if len(branch_ids) != len(set(branch_ids)):
        raise SlimeProjectionError("duplicate_branch_id", f"branch_id 重复：{branch_ids}。")
    if not capture_records:
        raise SlimeProjectionError(
            "no_capture_records", "capture_records 为空：投影必须回链原始捕获事实（A4）。"
        )
    records_by_id: dict[str, GenerationCaptureRecord] = {}
    for record in capture_records:
        if record.record_id in records_by_id:
            raise SlimeProjectionError(
                "duplicate_capture_record_id", f"capture record_id 重复：{record.record_id!r}。"
            )
        records_by_id[record.record_id] = record

    # serving 事实全体一致（一个投影 = 一个 serving 事实组合）
    trajectory_id = _uniform_capture_fact(capture_records, "trajectory_id")
    engine_name = _uniform_capture_fact(capture_records, "backend_name")
    engine_version = _uniform_capture_fact(capture_records, "backend_version")
    renderer_cls_name = _uniform_capture_fact(capture_records, "renderer_cls_name")
    tokenizer_name = _uniform_capture_fact(capture_records, "tokenizer_name")
    template_hash = _uniform_capture_fact(capture_records, "template_hash")
    _uniform_capture_fact(capture_records, "model_name")
    top_p_values = {record.sampling_params.top_p for record in capture_records}
    if len(top_p_values) != 1:
        raise SlimeProjectionError(
            "mixed_sampling_top_p",
            f"capture 记录的 top_p 不一致：{sorted(top_p_values)}——"
            "同一 trajectory 的采样配方必须一致，否则分支级 SamplingMaskRef 无法归一。",
        )
    top_p = top_p_values.pop()

    if expected_renderer_cls_name is not None:
        assert_renderer_class(renderer_cls_name, expected_renderer_cls_name)

    # rollout 身份：同一投影的全部 Sample 必须属于同一次 rollout（slime sibling 语义）
    rollout_ids = set()
    for sample in samples:
        rid = getattr(sample, "rollout_id", None)
        if rid is None:
            rid = getattr(sample, "index", None)
        if rid is None:
            raise SlimeProjectionError(
                "rollout_identity_missing",
                "Sample 的 rollout_id 与 index 均为 None，无法确定 rollout 归属。",
            )
        rollout_ids.add(rid)
    if len(rollout_ids) != 1:
        raise SlimeProjectionError(
            "mixed_rollout_ids",
            f"samples 分属不同 rollout：{sorted(map(str, rollout_ids))}——"
            "单投影多 branches 的前提是同一次 rollout 的分段（S1-1b 定案）；"
            "跨 rollout 的 GRPO 兄弟组请用 parent_rollout_id 表达。",
        )
    source_object_ref = f"slime_rollout_{rollout_ids.pop()}"

    branches: list[BranchProjection] = []
    total_trainable = 0
    for sample, annotation in zip(samples, annotations):
        branch, trainable_count = _project_branch(
            sample,
            annotation,
            trajectory_id=trajectory_id,
            records_by_id=records_by_id,
            engine_name=engine_name,
            engine_version=engine_version,
            top_p=top_p,
            serving_precision=serving_precision,
            serving_sampling_backend=serving_sampling_backend,
            moe_num_layers=moe_num_layers,
            moe_router_topk=moe_router_topk,
            store=artifact_store,
        )
        branches.append(branch)
        total_trainable += trainable_count

    # fan-out 账目：分段即 branches；申报数与实际不一致拒收（两叶链申报 1 段的形态）
    segment_count = len(branches)
    if declared_segment_count is not None and declared_segment_count != segment_count:
        raise SlimeProjectionError(
            "segment_count_mismatch",
            f"调用方申报 segment_count={declared_segment_count}，但本 rollout 实际产出 "
            f"{segment_count} 条叶链分支——fan-out 账目对不上（分段被拆去了别的投影，"
            "或申报数被凭空缩放），拒收。",
        )

    reward_facts = RewardFacts(
        reward_scope=reward.reward_scope,
        raw_reward=reward.raw_reward,
        components=dict(reward.components),
        reward_event_refs=list(reward.reward_event_refs),
        credit_assignment_strategy=reward.credit_assignment_strategy,
        group_id=reward.group_id,
        parent_rollout_id=reward.parent_rollout_id,
        segment_index=None,
        segment_count=segment_count,
        rollout_loss_denominator=total_trainable,
    )

    return TrajectoryProjection(
        trajectory_id=trajectory_id,
        task_id=task_id,
        source_framework="slime",
        source_object_ref=source_object_ref,
        renderer_cls_name=renderer_cls_name,
        tokenizer_name=tokenizer_name,
        chat_template_hash=template_hash,
        branches=branches,
        reward_facts=reward_facts,
        created_at_utc=created_at_utc or datetime.now(timezone.utc),
    )
