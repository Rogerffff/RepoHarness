"""slime Sample -> miles Sample 的 canonicalization 边界（miles 迁移 C0）。

背景（spike-log R5-ext B1，已复现的崩溃链）：形态甲下 rh2 复用 vendor slime
的 agent 层，`TrajectoryManager._SampleBuilder.to_sample()`（rh2/src/slime/
agent/trajectory.py）无条件构造 **slime** `Sample`；而 miles fully-async 主链
（buffer 过滤、metrics、rollout_id 校验、train conversion）只认 **miles**
`Sample`。两个类不同、嵌套的 `Status` 枚举互不相等（实测
`SlimeSample.Status.ABORTED == MilesSample.Status.ABORTED -> False`），直接
把 vendor 输出还给 miles 会触发三个真实症状：

1. `fully_async_data_buffer.DefaultDataBuffer.put()` 用
   `s.status == MilesSample.Status.ABORTED` 过滤——slime 的 ABORTED 样本
   **漏过滤**混进 buffer；
2. `DefaultDataBuffer.get_metrics()` 经 `group_oldest_weight_version` 访问
   `s.oldest_weight_version`——slime Sample 没有该属性，AttributeError；
3. `rollout_data_conversion.validate_compact_rollout_ids()` 断言节点
   `isinstance(node, MilesSample)`——slime Sample 直接 AssertionError。

因此规定：**任何 rh2 generate 输出在返回 miles 之前必须经过本模块的
`canonicalize_group()`**（由 generate_fn.Rh2MilesGenerateFn 调用）。

映射原则（fail-closed，宁炸不猜）：

- status 按**字符串值**映射到 miles 枚举（绝不复制枚举对象）；PENDING 拒绝
  （vendor 输出必须是终态，PENDING 意味着生成从未发生）。
- vendor 只在 `metadata["truncated"]`（bool）里记录"最后一轮 finish_reason
  == length"这一事实（to_sample 硬编码 status=COMPLETED，见
  trajectory.py `_chain_to_samples`）；canonicalize 把
  `COMPLETED + metadata truncated=True` 显式升级为 miles
  `Status.TRUNCATED`（miles 训练侧 `truncated` 列与 buffer 准入都依赖
  status，不看 metadata）。ABORTED/FAILED 不被该 flag 改写（中止/失败
  语义优先）；flag 非 bool 直接拒绝。
- miles 输入样本独有的路由/评分/分发字段（`adapter`/`reward_spec`/
  `routing_key`/`generate_function_path`/`multimodal_inputs`）从输入样本
  保留——vendor 输出不可能携带它们。
- slime 独有且 miles 无对应位置的字段：出现非默认值一律拒绝（见
  `_REJECTED_SLIME_FIELDS`），唯一例外是 `session_id`（显式丢弃，miles 侧
  的会话路由身份由输入样本的 `routing_key` 承担）。
- 两侧 dataclass 字段集在模块加载时与硬编码允许集核对，vendor/miles 任何
  一侧加字段都会当场把本模块炸掉，逼迫人工重审映射表（而不是静默丢数据）。

sampling-mask 一等字段（C1′-b 落地，取代原预留位说明）：

- **miles 直通分支**：`rollout_sampling_mask` 是 miles 自有字段，原样直通
  （abort/eval 收口路径样本本就没有或已带正确值）。
- **slime->miles 构造分支**：装配层（sampling_mask_assembly）把各轮引擎
  支持集 + 观察位单例装配成 `AssembledSamplingMask`，以附加属性
  `rh2_sampling_mask` 挂在 vendor 输出样本上；本模块消费该属性、转成
  miles `RolloutSamplingMask`（CSR ids int32 / offsets int64）。
  fail-closed 闸：调用方传入 `rollout_top_p`（miles args.rollout_top_p）
  且 < 1.0 时，slime 构造分支**必须**带装配 mask，缺失即拒绝——top_p<1
  无支持集的样本不可忠实 replay，不得进训练（对照上游"top_p<1.0 即开
  replay"的严格开关，C1′-a 边界事实 (d)）。
- slime 旧 top-p tape 字段（`rollout_top_p_token_ids/offsets`）仍然拒绝
  （见 `_REJECTED_SLIME_FIELDS`）：miles 链路的支持集事实走装配层，
  不从 slime tape 字段静默转换（两套账禁止并行）。
- pin base（无 `rollout_sampling_mask` 字段）上出现装配 mask 一律拒绝
  （`MILES_HAS_SAMPLING_MASK_FIELD` 分流），不存在静默丢弃路径。

R3 routing tape 转换（F4 落地，取代原"非 None 拒绝"挡板）：

- rh2 侧产生点（generate.py `backfill_leaf_sample`/`_shape_routing_experts`）
  的三种形态——torch tensor `(rows, layers, topk)`、无 torch 环境的等价
  嵌套 list、config 缺 layers/topk 时的 flat list——统一经
  `_convert_routed_experts` 转成 **owned contiguous numpy.ndarray[int32]**，
  形状严格 `(len(tokens)-1, moe_num_layers, moe_router_topk)`（miles Sample
  契约：miles/utils/types.py 字段注释 + validate() 行数断言 +
  train_data_conversion 的 int32 wire dtype）。
- fail-closed 面：layers/topk 期望配置缺失、少行/多行、错 layer/topk、
  非整数 dtype、超 int32 值域、ragged/未知形态一律拒绝。
- R3-off（slime 侧字段为 None）：miles 侧保持默认 None，旧路径零改变。

导入面说明：本模块只 import `miles.utils.types`、`slime.utils.types` 与
`numpy`（miles.utils.types 本身依赖 numpy，三者均无 sglang 依赖，CPU 可
导）；不得 import `miles.rollout.*`（base_types 经 data_source ->
chat_template_utils 拉 sglang）；torch 只在 routing tape 真的以 tensor 形态
出现时才在函数内 import（无 tape / R3-off 路径完全不碰 torch）。
"""

from __future__ import annotations

from typing import Any

import numpy
from miles.utils.types import Sample as MilesSample
from slime.utils.types import Sample as SlimeSample

from repoharness2.adapters.miles.sampling_mask_assembly import (
    ATTACHED_MASK_ATTR as _ATTACHED_MASK_ATTR,
)
from repoharness2.adapters.miles.sampling_mask_assembly import (
    AssembledSamplingMask,
)


class CanonicalizationError(RuntimeError):
    """canonicalize 边界 fail-closed 错误（reason_code 机器可读）。"""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"[{reason_code}] {message}")


# ---------------------------------------------------------------------------
# 允许集（显式列出，两侧任何字段增删都会触发 import 时报错）
# ---------------------------------------------------------------------------

# slime pin e848052a 的 Sample dataclass 字段全集（30 个）。
_SLIME_FIELDS_EXPECTED = frozenset(
    {
        "group_index", "index", "rollout_id", "prompt", "tokens",
        "multimodal_inputs", "multimodal_train_inputs", "multimodal_train_input_id",
        "apply_chat_template_kwargs", "response", "response_length", "label",
        "reward", "loss_mask", "weight_versions", "rollout_log_probs",
        "rollout_top_p_token_ids", "rollout_top_p_token_offsets",
        "rollout_routed_experts", "remove_sample", "teacher_log_probs", "status",
        "metadata", "generate_function_path", "custom_rm_path", "train_metadata",
        "session_id", "non_generation_time", "spec_info", "prefix_cache_info",
    }
)

# miles pin f2b7c7929 的 Sample dataclass 字段全集（29 个）。
_MILES_FIELDS_PIN = frozenset(
    {
        "group_index", "index", "rollout_id", "prompt", "tokens",
        "multimodal_inputs", "multimodal_train_inputs", "response",
        "response_length", "label", "reward", "loss_mask", "weight_versions",
        "rollout_log_probs", "rollout_routed_experts", "rollout_indexer_topk",
        "remove_sample", "teacher_log_probs", "opd_reverse_kl", "status",
        "metadata", "generate_function_path", "train_metadata", "adapter",
        "reward_spec", "routing_key", "non_generation_time", "spec_info",
        "prefix_cache_info",
    }
)

# integration base（rh2-integration-v2 = pin + PR #2595/#2596）的字段全集：
# pin + rollout_sampling_mask（C1′-a 已核实：这是两 PR 唯一的 Sample 新字段）。
# **双 base 过渡期允许集**：canonicalize 同时兼容 pin 与 integration base
# ——匹配到哪个集合决定 MILES_HAS_SAMPLING_MASK_FIELD；两个集合都不匹配
# 仍然当场炸（除该字段外的任何增删照旧触发人工重审）。上游 PR 合并、pin
# 前移后应收敛回单集合并删除本段注释。
_MILES_FIELDS_INTEGRATION = _MILES_FIELDS_PIN | {"rollout_sampling_mask"}


def _resolve_miles_field_set() -> tuple[frozenset[str], bool]:
    actual = frozenset(MilesSample.__dataclass_fields__)
    if actual == _MILES_FIELDS_PIN:
        return _MILES_FIELDS_PIN, False
    if actual == _MILES_FIELDS_INTEGRATION:
        return _MILES_FIELDS_INTEGRATION, True
    base = _MILES_FIELDS_INTEGRATION if "rollout_sampling_mask" in actual else _MILES_FIELDS_PIN
    raise CanonicalizationError(
        "sample_schema_drift",
        "miles（pin f2b7c7929 / rh2-integration-v2）的 Sample 字段集与 canonicalize "
        f"映射表不一致：新增={sorted(actual - base)} 缺失={sorted(base - actual)}。"
        "必须人工重审本模块映射表后更新允许集，禁止静默通过。",
    )


def _assert_field_sets() -> tuple[frozenset[str], bool]:
    actual_slime = frozenset(SlimeSample.__dataclass_fields__)
    if actual_slime != _SLIME_FIELDS_EXPECTED:
        raise CanonicalizationError(
            "sample_schema_drift",
            "slime e848052a 的 Sample 字段集与 canonicalize 映射表不一致："
            f"新增={sorted(actual_slime - _SLIME_FIELDS_EXPECTED)} "
            f"缺失={sorted(_SLIME_FIELDS_EXPECTED - actual_slime)}。"
            "必须人工重审本模块映射表后更新允许集，禁止静默通过。",
        )
    return _resolve_miles_field_set()


# 解析后的 miles 允许集（当前加载的 checkout 实际匹配到的那份）与
# sampling-mask 一等字段在场标志（C1′-b：mask 转换分支按它分流/拒绝）。
_MILES_FIELDS_EXPECTED, MILES_HAS_SAMPLING_MASK_FIELD = _assert_field_sets()


# status 按字符串值映射（不复制枚举对象）。PENDING 有意不在表内：vendor
# 输出必须是终态（COMPLETED/TRUNCATED/ABORTED/FAILED），PENDING 说明生成
# 从未发生，放行会把未完成样本混进训练准入。
_STATUS_BY_VALUE: dict[str, Any] = {
    "completed": MilesSample.Status.COMPLETED,
    "truncated": MilesSample.Status.TRUNCATED,
    "aborted": MilesSample.Status.ABORTED,
    "failed": MilesSample.Status.FAILED,
}

# slime 独有、miles 无对应位置的字段：值偏离 slime dataclass 默认值即拒绝。
# 表内为 {字段名: (默认值判定函数, 拒绝理由)}。
_REJECTED_SLIME_FIELDS: dict[str, tuple[Any, str]] = {
    "multimodal_train_inputs": (
        lambda v: v is None,
        "多模态训练输入的 slime->miles 转换未定义（C0 范围外）",
    ),
    "multimodal_train_input_id": (
        lambda v: v is None,
        "miles Sample 没有 multimodal_train_input_id 字段",
    ),
    "apply_chat_template_kwargs": (
        lambda v: not v,
        "miles Sample 没有 apply_chat_template_kwargs 字段",
    ),
    "rollout_top_p_token_ids": (
        lambda v: v is None,
        "top-p tape -> miles RolloutSamplingMask 的一等字段接线归 C1"
        "（本模块 docstring 的 sampling-mask 预留位），静默丢弃会丢采样支持集事实",
    ),
    "rollout_top_p_token_offsets": (
        lambda v: v is None,
        "同 rollout_top_p_token_ids（成对字段）",
    ),
    "custom_rm_path": (
        lambda v: v is None,
        "miles 侧评分分发由输入样本的 reward_spec 承担，复制路径字符串会造成双事实源",
    ),
    "generate_function_path": (
        lambda v: v is None,
        "miles 侧分发字段从输入样本保留；vendor 输出携带它说明有未知改写",
    ),
}

# miles 输入样本身上允许出现的**非字段**属性（rh2 编排层 setattr 所致）。
# session_id：generate.py `_session_id()` 会把会话 id 写回输入样本
# （sample.session_id = sid）；miles Sample 没有该字段，canonicalize 时剥除
# （miles 侧路由身份 = routing_key，会话 id 已进 audit/capture 记录）。
_ALLOWED_MILES_EXTRA_ATTRS = frozenset({"session_id"})


# ---------------------------------------------------------------------------
# 单样本
# ---------------------------------------------------------------------------


def canonicalize_sample(
    slime_sample: Any,
    *,
    miles_input_sample: Any,
    rollout_top_p: float | None = None,
    moe_num_layers: int | None = None,
    moe_router_topk: int | None = None,
) -> Any:
    """把一条 rh2 generate 输出样本转换/校验为 miles Sample。

    两个合法输入形态（rh2 generate 的真实输出面）：

    1. vendor slime `Sample`（TrajectoryManager 叶链产物）——构造新的 miles
       Sample，逐字段按模块映射表复制；
    2. miles `Sample`（abort/eval 收口路径把**输入样本本体**原地改写后返回，
       见 generate.py `_abort_result` / `_deliver` 评测分支）——校验后原对象
       返回（剥除 rh2 附加的 session_id 属性，回填输入侧保留字段）。

    其余类型一律拒绝。

    ``rollout_top_p``：miles `args.rollout_top_p`（调用方 = generate_fn 透传；
    None = 调用方不携带该配置，闸不生效）。< 1.0 时 slime 构造分支强制要求
    装配 mask 在场（见模块 docstring 的 sampling-mask 段）。

    ``moe_num_layers``/``moe_router_topk``：R3 routing tape 的形状期望
    （调用方 = generate_fn 从 orchestrator 的 SlimeBindingConfig 透传，与
    backfill 产生 tape 用的是同一份配置）。仅当 slime 输出真的携带
    `rollout_routed_experts` 时消费；tape 在场而期望缺失 = fail-closed。
    """

    if miles_input_sample is None or not isinstance(miles_input_sample, MilesSample):
        raise CanonicalizationError(
            "miles_input_sample_invalid",
            f"miles_input_sample 必须是 miles Sample，got {type(miles_input_sample).__name__}。",
        )

    if isinstance(slime_sample, MilesSample):
        return _canonicalize_miles_passthrough(slime_sample, miles_input_sample)
    if isinstance(slime_sample, SlimeSample):
        return _convert_slime_sample(
            slime_sample,
            miles_input_sample,
            rollout_top_p=rollout_top_p,
            moe_num_layers=moe_num_layers,
            moe_router_topk=moe_router_topk,
        )
    raise CanonicalizationError(
        "unexpected_output_type",
        f"generate 输出节点类型 {type(slime_sample).__name__} 不是 slime/miles Sample。",
    )


def _map_status(status: Any, metadata: dict, *, source: str) -> Any:
    """status 字符串值映射 + truncated metadata 显式升级（fail-closed）。"""

    value = getattr(status, "value", None)
    if not isinstance(value, str) or value not in _STATUS_BY_VALUE:
        raise CanonicalizationError(
            "status_unmappable",
            f"{source} 样本 status={status!r}（value={value!r}）不在允许映射集 "
            f"{sorted(_STATUS_BY_VALUE)} 内（PENDING/未知值一律拒绝）。",
        )
    mapped = _STATUS_BY_VALUE[value]

    if "truncated" in metadata:
        flag = metadata["truncated"]
        if not isinstance(flag, bool):
            raise CanonicalizationError(
                "truncated_flag_not_bool",
                f"{source} 样本 metadata['truncated']={flag!r} 不是 bool——"
                "vendor 只会写 bool，其他类型说明上游数据被污染。",
            )
        if flag and mapped is MilesSample.Status.COMPLETED:
            # vendor to_sample 硬编码 COMPLETED，截断事实只在 metadata 里；
            # miles buffer/训练侧只看 status，这里显式恢复 TRUNCATED。
            mapped = MilesSample.Status.TRUNCATED
    return mapped


def _reject_unknown_extras(sample: Any, allowed: frozenset[str], fields: frozenset[str], *, source: str) -> None:
    extras = set(sample.__dict__) - set(fields) - set(allowed)
    if extras:
        raise CanonicalizationError(
            "unknown_sample_attrs",
            f"{source} 样本携带映射表外属性 {sorted(extras)}——fail-closed，"
            "先在 canonicalize 映射表登记去向（复制/拒绝/丢弃）再放行。",
        )


def _canonicalize_miles_passthrough(sample: Any, miles_input_sample: Any) -> Any:
    """miles Sample 直通分支（abort/eval 收口路径）：校验 + 清理 + 回填。"""

    _reject_unknown_extras(
        sample, _ALLOWED_MILES_EXTRA_ATTRS, _MILES_FIELDS_EXPECTED, source="miles 直通"
    )
    # 剥除 rh2 编排层 setattr 的会话 id（见 _ALLOWED_MILES_EXTRA_ATTRS 注释）。
    sample.__dict__.pop("session_id", None)

    metadata = sample.metadata or {}
    sample.status = _map_status(sample.status, metadata, source="miles 直通")

    # 输入侧保留字段回填（同对象时是恒等写；不同对象时对齐输入事实）。
    sample.adapter = miles_input_sample.adapter
    sample.reward_spec = miles_input_sample.reward_spec
    sample.routing_key = miles_input_sample.routing_key
    sample.generate_function_path = miles_input_sample.generate_function_path
    return sample


def _convert_slime_sample(
    s: Any,
    miles_input_sample: Any,
    *,
    rollout_top_p: float | None,
    moe_num_layers: int | None,
    moe_router_topk: int | None,
) -> Any:
    """vendor slime Sample -> 新 miles Sample（逐字段显式映射）。"""

    # C1′-b：装配 mask 附加属性（sampling_mask_assembly.attach_assembled_mask
    # 挂上；是唯一允许的 slime 侧附加属性，消费后不进 miles 对象 __dict__ 外挂）。
    attached_mask = getattr(s, _ATTACHED_MASK_ATTR, None)
    _reject_unknown_extras(s, frozenset({_ATTACHED_MASK_ATTR}), _SLIME_FIELDS_EXPECTED, source="slime")

    if rollout_top_p is not None and float(rollout_top_p) < 1.0 and attached_mask is None:
        raise CanonicalizationError(
            "sampling_mask_required",
            f"rollout_top_p={rollout_top_p} < 1.0 的 slime->miles 构造分支缺装配 mask"
            "（rh2_sampling_mask 附加属性）——top_p<1 无支持集不可忠实 replay，"
            "fail-closed 拒绝（对照上游 top_p<1.0 即开 replay 的严格开关）。",
        )

    for name, (is_default, why) in _REJECTED_SLIME_FIELDS.items():
        value = getattr(s, name)
        if not is_default(value):
            raise CanonicalizationError(
                f"slime_field_rejected:{name}",
                f"slime 样本字段 {name}={value!r} 无 miles 对应位置：{why}。",
            )

    # 身份一致性：叶链样本的 index/group_index 由 to_sample 从 base_sample
    # 复制而来，必须与本次 generate 的 miles 输入一致（防串组，B4 验收项）。
    for name in ("index", "group_index"):
        if getattr(s, name) != getattr(miles_input_sample, name):
            raise CanonicalizationError(
                "identity_mismatch",
                f"slime 输出样本 {name}={getattr(s, name)!r} != miles 输入 "
                f"{getattr(miles_input_sample, name)!r}——输出不属于本次 generate 的输入。",
            )

    metadata = dict(s.metadata or {})
    out = MilesSample(
        # -- 身份（来自 vendor 输出；rollout_id 保留 vendor 的
        #    "None 回退 index / sibling 共享" 语义，不改写）
        group_index=s.group_index,
        index=s.index,
        rollout_id=s.rollout_id,
        # -- prompt/response 事实（vendor 输出逐字段复制；容器浅拷贝，
        #    防止 miles 侧 reset_for_retry 等原地改写波及 vendor 侧持有的引用）
        prompt=s.prompt,
        tokens=list(s.tokens or []),
        response=s.response,
        response_length=s.response_length,
        label=s.label,
        reward=s.reward,
        loss_mask=None if s.loss_mask is None else list(s.loss_mask),
        weight_versions=list(s.weight_versions or []),
        rollout_log_probs=None if s.rollout_log_probs is None else list(s.rollout_log_probs),
        teacher_log_probs=None if s.teacher_log_probs is None else list(s.teacher_log_probs),
        remove_sample=s.remove_sample,
        metadata=metadata,
        train_metadata=None if s.train_metadata is None else dict(s.train_metadata),
        non_generation_time=s.non_generation_time,
        # -- status：字符串值映射 + truncated metadata 升级
        status=_map_status(s.status, metadata, source="slime"),
        # -- miles 输入侧保留字段（vendor 输出不可能携带）
        adapter=miles_input_sample.adapter,
        reward_spec=miles_input_sample.reward_spec,
        routing_key=miles_input_sample.routing_key,
        generate_function_path=miles_input_sample.generate_function_path,
        multimodal_inputs=miles_input_sample.multimodal_inputs,
        # -- miles 独有的响应侧字段：vendor 链路不产生，保持默认 None
        #    （rollout_indexer_topk / opd_reverse_kl；multimodal_train_inputs
        #    同理——slime 侧非 None 已在上方拒绝；rollout_routed_experts 见
        #    下方 F4 转换分支）
    )
    # 统计信息容器：两侧嵌套类同构但类型不同，经 dict 往返换成 miles 类实例。
    out.spec_info = MilesSample.SpecInfo.from_dict(s.spec_info.to_dict())
    out.prefix_cache_info = MilesSample.PrefixCacheInfo.from_dict(s.prefix_cache_info.to_dict())
    if attached_mask is not None:
        out.rollout_sampling_mask = _to_miles_sampling_mask(attached_mask, out)
    # F4（R3 routing tape）：slime 侧 tape 在场才转换；R3-off（None）保持
    # miles 默认 None，旧路径零改变。
    if s.rollout_routed_experts is not None:
        out.rollout_routed_experts = _convert_routed_experts(
            s.rollout_routed_experts,
            expected_rows=len(out.tokens) - 1,
            moe_num_layers=moe_num_layers,
            moe_router_topk=moe_router_topk,
        )
    return out


def _convert_routed_experts(
    value: Any,
    *,
    expected_rows: int,
    moe_num_layers: int | None,
    moe_router_topk: int | None,
) -> "numpy.ndarray":
    """RH2 routing tape -> miles 契约的 owned contiguous numpy.ndarray[int32]。

    输入三形态（rh2 产生点 = generate.py `_shape_routing_experts`，逐一对照）：

    1. torch tensor，形状 `(rows, layers, topk)`（torch 在场的正常路径）；
    2. 等价嵌套 list `[rows][layers][topk]`（无 torch 的轻量环境回退）；
    3. flat list（backfill 时 config 缺 layers/topk 的保底形态）。

    输出严格 `(expected_rows, moe_num_layers, moe_router_topk)`、dtype int32、
    C-contiguous 且**拥有自己的内存**（不与 torch tensor / 输入 list 共享，
    miles 侧 buffer/train conversion 持有期间 rh2 侧释放引用也安全）。

    fail-closed（宁炸不猜）：期望配置缺失或非正、行数少/多（backfill 已做过
    唯一允许的前缀裁剪，这里不再二次猜测）、layer/topk 与配置不符、非整数
    dtype（含 bool/float）、超 int32 值域、ragged/混型/未知形态一律拒绝。
    """

    if moe_num_layers is None or moe_router_topk is None:
        raise CanonicalizationError(
            "routed_experts_config_missing",
            "slime 输出携带 rollout_routed_experts，但 canonicalize 未拿到 "
            f"moe_num_layers/moe_router_topk 期望（got {moe_num_layers!r}/"
            f"{moe_router_topk!r}）——无形状期望不做转换（generate_fn 应从 "
            "orchestrator 的 SlimeBindingConfig 透传，与 backfill 同源）。",
        )
    layers = int(moe_num_layers)
    topk = int(moe_router_topk)
    if layers <= 0 or topk <= 0:
        raise CanonicalizationError(
            "routed_experts_config_invalid",
            f"moe_num_layers={layers}/moe_router_topk={topk} 必须为正整数。",
        )
    if expected_rows <= 0:
        raise CanonicalizationError(
            "routed_experts_rows_mismatch",
            f"样本 tokens 不足 2 个（len(tokens)-1={expected_rows}），"
            "不存在合法的 routing 行。",
        )

    # -- 形态识别（只接产生点的三形态；其余 fail-closed）--------------------
    value_module = type(value).__module__ or ""
    if value_module == "torch" or value_module.startswith("torch."):
        # torch 只在 tape 真以 tensor 形态出现时才 import（见模块 docstring）。
        import torch

        if not isinstance(value, torch.Tensor):
            raise CanonicalizationError(
                "routed_experts_unknown_form",
                f"routing tape 类型 {type(value).__name__}（torch 模块下的非 "
                "Tensor 对象）不是已知产生形态。",
            )
        try:
            arr = value.detach().cpu().numpy()
        except Exception as exc:  # noqa: BLE001 - numpy 不支持的 torch dtype 等
            raise CanonicalizationError(
                "routed_experts_malformed",
                f"torch tensor -> numpy 转换失败（dtype={value.dtype}）：{exc}",
            ) from exc
    elif isinstance(value, (list, tuple)):
        try:
            arr = numpy.asarray(value)
        except (ValueError, TypeError, OverflowError) as exc:
            raise CanonicalizationError(
                "routed_experts_malformed",
                f"routing tape list 无法构成规则数组（ragged/混型/超界）：{exc}",
            ) from exc
        if arr.dtype == object:
            raise CanonicalizationError(
                "routed_experts_malformed",
                "routing tape list 构成 object 数组（ragged 或混型元素）——"
                "不是规则的 [rows][layers][topk] / flat 形态。",
            )
    else:
        raise CanonicalizationError(
            "routed_experts_unknown_form",
            f"routing tape 类型 {type(value).__name__} 不是已知产生形态"
            "（torch tensor / 嵌套 list / flat list）。",
        )

    # -- dtype：必须是整数（bool kind='b'、float kind='f' 都在此拒绝）--------
    if arr.dtype.kind not in ("i", "u"):
        raise CanonicalizationError(
            "routed_experts_not_integer",
            f"routing tape dtype={arr.dtype} 不是整数——expert 索引必须为整数。",
        )

    # -- 形状：flat 按期望 reshape；3 维逐轴核对；其余维度拒绝 ---------------
    if arr.ndim == 1:
        expected_numel = expected_rows * layers * topk
        if arr.size != expected_numel:
            raise CanonicalizationError(
                "routed_experts_numel_mismatch",
                f"flat routing tape 元素数 {arr.size} != 期望 {expected_numel}"
                f"（rows={expected_rows} x layers={layers} x topk={topk}）。",
            )
        arr = arr.reshape(expected_rows, layers, topk)
    elif arr.ndim == 3:
        rows_actual, layers_actual, topk_actual = arr.shape
        if layers_actual != layers or topk_actual != topk:
            raise CanonicalizationError(
                "routed_experts_shape_mismatch",
                f"routing tape 形状 {tuple(arr.shape)} 的 (layers, topk)="
                f"({layers_actual}, {topk_actual}) != 配置期望 ({layers}, {topk})。",
            )
        if rows_actual != expected_rows:
            raise CanonicalizationError(
                "routed_experts_rows_mismatch",
                f"routing tape {rows_actual} 行 != len(tokens)-1={expected_rows}"
                "（少行/多行都拒绝；唯一允许的前缀裁剪已在 backfill 完成）。",
            )
    else:
        raise CanonicalizationError(
            "routed_experts_unknown_form",
            f"routing tape ndim={arr.ndim} 不是 1（flat）或 3（rows, layers, topk）。",
        )

    # -- 值域：int32 收窄必须无损（miles wire dtype = int32）-----------------
    info = numpy.iinfo(numpy.int32)
    if int(arr.min()) < info.min or int(arr.max()) > info.max:
        raise CanonicalizationError(
            "routed_experts_out_of_int32_range",
            f"routing tape 值域 [{int(arr.min())}, {int(arr.max())}] 超出 int32"
            "——收窄会静默改写 expert 索引，拒绝。",
        )
    # copy=True + order="C"：owned、contiguous（不与输入共享内存）。
    return numpy.array(arr, dtype=numpy.int32, order="C", copy=True)


def _to_miles_sampling_mask(attached: Any, out: Any) -> Any:
    """AssembledSamplingMask -> miles RolloutSamplingMask（C1′-b 转换点）。

    fail-closed 三闸：类型必须是装配层产物（不接受任意 CSR 二元组）；
    当前 miles base 必须有 rollout_sampling_mask 一等字段（pin base 拒绝，
    禁止把 mask 静默丢掉或塞 metadata——P0-3 已证 metadata 不透传训练侧）；
    覆盖长度必须等于 response_length（miles Sample.validate 同款不变量，
    这里提前到边界抛可读错误）。
    """

    if not isinstance(attached, AssembledSamplingMask):
        raise CanonicalizationError(
            "sampling_mask_wrong_type",
            f"rh2_sampling_mask 附加属性类型 {type(attached).__name__} 不是 "
            "AssembledSamplingMask——装配必须经 sampling_mask_assembly。",
        )
    if not MILES_HAS_SAMPLING_MASK_FIELD:
        raise CanonicalizationError(
            "sampling_mask_field_absent",
            "当前 miles checkout（pin f2b7c7929）的 Sample 没有 rollout_sampling_mask "
            "一等字段——mask 链路要求 integration base（rh2-integration-v2）；"
            "静默丢弃或走 metadata 都被禁止（metadata 不在训练 wire 白名单）。",
        )
    if attached.response_token_count != out.response_length:
        raise CanonicalizationError(
            "sampling_mask_length_mismatch",
            f"装配 mask 覆盖 {attached.response_token_count} 个 token != 样本 "
            f"response_length={out.response_length}。",
        )
    # lazy import：pin/integration base 都有该模块（primitive #2200 已在 pin 内），
    # 放函数内只为让"无 mask 输入"的 canonicalize 路径完全不碰 torch。
    from miles.utils.sampling_mask import RolloutSamplingMask

    return RolloutSamplingMask(ids=list(attached.ids), offsets=list(attached.offsets))


# ---------------------------------------------------------------------------
# 递归组
# ---------------------------------------------------------------------------


def canonicalize_group(
    output: Any,
    *,
    miles_input_sample: Any,
    rollout_top_p: float | None = None,
    moe_num_layers: int | None = None,
    moe_router_topk: int | None = None,
) -> Any:
    """递归转换 rh2 generate 的整个输出（Sample | list，任意嵌套深度）。

    形状原样保留：list 结构、元素顺序、fan-out sibling 的 rollout_id 共享
    都不改写（rollout_id 逐样本复制，siblings 天然继续共享）。空 list 拒绝
    （无事实的输出形状，放行会在 miles flatten/校验层制造更晦涩的错误）。
    ``rollout_top_p`` 逐样本透传（见 canonicalize_sample 的 mask 闸说明）；
    ``moe_num_layers``/``moe_router_topk`` 同样逐样本透传（R3 routing tape
    的形状期望，见 canonicalize_sample 说明）。
    """

    if isinstance(output, list):
        if not output:
            raise CanonicalizationError(
                "empty_output_list",
                "generate 输出出现空 list——上游必须显式给出样本或抛错，不许交空壳。",
            )
        return [
            canonicalize_group(
                item,
                miles_input_sample=miles_input_sample,
                rollout_top_p=rollout_top_p,
                moe_num_layers=moe_num_layers,
                moe_router_topk=moe_router_topk,
            )
            for item in output
        ]
    return canonicalize_sample(
        output,
        miles_input_sample=miles_input_sample,
        rollout_top_p=rollout_top_p,
        moe_num_layers=moe_num_layers,
        moe_router_topk=moe_router_topk,
    )
