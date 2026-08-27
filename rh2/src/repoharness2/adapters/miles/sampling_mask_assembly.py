"""sampling-support mask 的捕获校验与装配（miles 迁移 C1′-b，delta 清单第 1 项）。

背景：sglang-miles 引擎（integration base = pin f2b7c7929 + 上游 PR #2595/#2596）
对 `return_sampling_mask: true` 的 /generate 请求会在 meta_info 里返回

    output_token_sampling_mask      # ragged：每个生成 token 的支持集 token ids
    output_token_sampling_logprobs  # 每个生成 token 的 support-normalized logprob

本模块承担三件事，全部是 **rh2 侧独立实现**——语义逐条对照上游
`reference/miles-rh2-integration/miles/rollout/generate_utils/sampling_mask.py`
（should_return_sampling_mask / _sampling_mask_from_supports /
append_forced_sampling_tokens / merge_sampling_masks），但**不 import 上游
私有函数**（上游是 reference 只读 checkout，且这些符号只在 integration base
存在；rh2 测试面必须在 pin base 上也可导入本模块）：

1. **请求前置校验** `validate_sampling_mask_request`：top_k 必须有限、
   温度必须与会话配置一致、penalties/logit_bias/custom_logit_processor
   一律拒绝——不可忠实 replay 的请求 fail-closed，不发出去。
2. **响应解析校验** `parse_turn_sampling_support`：逐 token
   sampled ∈ support、支持集非空、长度对齐；abort 且零输出时允许空结果
   （对照上游 append_sampling_metadata 的 abort 分支）。
3. **跨轮装配** `assemble_leaf_sampling_mask`：把各轮引擎支持集按
   token 同一性锚定到叶链 response 上（复用
   `repoharness2.adapters.slime.generate` 的 `_mask1_runs` /
   `_match_turns_to_runs`——rh2 自己的模块，"冻结"指不修改，不禁 import；
   run<->turn 锚定语义必须与 top-p tape 回填是同一份实现，防两套账），
   观察/工具 token（loss_mask=0，含掉落轮残留上下文）补**单例支持集
   {该 token}**（= 上游 append_forced_sampling_tokens 语义，也是
   spike P0-3 定案的候选 (b)：slime 零宽 span 的精确等价物），
   跨轮拼接时 offsets 重基（= 上游 RolloutSamplingMask.concatenate 语义）。
   输出 CSR：ids 按 int32、offsets 按 int64（上游训练 wire dtype，
   `miles/ray/rollout/train_data_conversion.py` ROLLOUT_DATA_TENSOR_DTYPES）。

产物 `AssembledSamplingMask` 是纯 Python 容器（不含 torch/miles 依赖）；
转成 miles `RolloutSamplingMask` 一等字段发生在 canonicalize 的 slime->miles
构造分支（integration base 才有该字段，见 canonicalize.MILES_HAS_SAMPLING_MASK_FIELD）。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from repoharness2.adapters.slime.generate import (
    TurnIdentitySpan,
    _mask1_runs,
    _match_turns_to_runs,
    _runs_from_identity_spans,
)

__all__ = [
    "ATTACHED_MASK_ATTR",
    "IDS_WIRE_DTYPE",
    "OFFSETS_WIRE_DTYPE",
    "AssembledSamplingMask",
    "SamplingMaskAssemblyError",
    "TurnSupport",
    "assemble_leaf_sampling_mask",
    "attach_assembled_mask",
    "parse_turn_sampling_support",
    "validate_sampling_mask_request",
]

# 上游训练 wire dtype（train_data_conversion.ROLLOUT_DATA_TENSOR_DTYPES）：
# rollout_sampling_mask_ids=int32，rollout_sampling_mask_offsets=int64。
IDS_WIRE_DTYPE = "int32"
OFFSETS_WIRE_DTYPE = "int64"

_INT32_MIN = -(2**31)
_INT32_MAX = 2**31 - 1

# 装配产物挂在 vendor slime Sample 上的属性名（slime Sample 没有
# rollout_sampling_mask 字段，只能以附加属性携带；canonicalize 的 slime
# 分支消费并剥除它——见 canonicalize._convert_slime_sample）。
ATTACHED_MASK_ATTR = "rh2_sampling_mask"


class SamplingMaskAssemblyError(RuntimeError):
    """mask 捕获/装配的 fail-closed 错误（reason_code 机器可读）。"""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"[{reason_code}] {message}")


# ---------------------------------------------------------------------------
# 1. 请求前置校验（对照上游 should_return_sampling_mask）
# ---------------------------------------------------------------------------

# 不可忠实 replay 的 logit 变换参数：训练端只重放 温度 + 支持集掩蔽，
# 这些参数会改写引擎侧 logits、trainer 无法重现（上游同款拒绝表，
# generate_utils/sampling_mask.py:49-55）。表值 = 各参数的"中性值"允许集。
_UNSUPPORTED_LOGIT_PARAMS: dict[str, tuple[Any, ...]] = {
    "frequency_penalty": (0, 0.0, None),
    "presence_penalty": (0, 0.0, None),
    "repetition_penalty": (1, 1.0, None),
    "logit_bias": ({}, None),
    "custom_logit_processor": (None,),
}


def validate_sampling_mask_request(
    sampling_params: Mapping[str, Any],
    *,
    expected_temperature: float,
    configured_top_k: int | None = None,
) -> dict[str, Any]:
    """校验一次开启 return_sampling_mask 的训练请求可被忠实 replay。

    与上游 should_return_sampling_mask 的对应关系：上游用 args.rollout_*
    作为参照系；rh2 capture 链没有 miles args，参照系 = 会话配置
    （session.sampling_defaults，由 rh2 编排层写入，调用方以
    ``expected_temperature`` / ``configured_top_k`` 传入）。逐条对照：

    - top_p 必须显式且 0 < top_p < 1.0（top_p=1.0 没有截断、不该开
      mask 捕获；上游同判）；
    - top_k 必须显式、为 int 且 > 0（**有限支持集上界**——top_p-only
      的支持集大小无界，引擎侧会直接 abort，这里提前拒绝）；且当
      ``configured_top_k`` 非 None 时必须 <= 它（上游同款
      0 < request_top_k <= configured_top_k：请求 body 不得静默放大
      会话配置的支持集硬上界）。None = 会话未配置 top_k 上界，只查
      有限正性（T0-A：top_k 校验无上界,vocab-size K 合法）；
    - temperature 必须显式且与会话配置一致（trainer 用同一温度缩放
      logits 才能重现支持集内分布）；
    - penalties/logit_bias/custom_logit_processor 非中性值一律拒绝。

    返回生效值 dict {"top_p", "top_k", "temperature"}（capture_params
    补记用）。任何违规抛 SamplingMaskAssemblyError（fail-closed：
    这种请求根本不该发到引擎）。
    """

    def _explicit(name: str) -> Any:
        value = sampling_params.get(name)
        if value is None:
            raise SamplingMaskAssemblyError(
                "sampling_mask_param_missing",
                f"return_sampling_mask 请求要求显式 {name}（上游 should_return_sampling_mask "
                "同款：缺省值不可作为 replay 事实记录）。",
            )
        return value

    top_p = float(_explicit("top_p"))
    if not (0.0 < top_p < 1.0):
        raise SamplingMaskAssemblyError(
            "sampling_mask_top_p_invalid",
            f"return_sampling_mask 要求 0 < top_p < 1.0，得到 {top_p}"
            "（top_p=1.0 无核截断不该开 mask；越界值不可 replay）。",
        )

    top_k_raw = _explicit("top_k")
    if not isinstance(top_k_raw, int) or isinstance(top_k_raw, bool) or top_k_raw <= 0:
        raise SamplingMaskAssemblyError(
            "sampling_mask_top_k_unbounded",
            f"return_sampling_mask 要求有限正整数 top_k，得到 {top_k_raw!r}"
            "（top_p-only 支持集大小无界，sglang-miles 引擎侧会 abort——T0-A："
            "top_k 是支持集的硬上界，必须显式给出）。",
        )
    if configured_top_k is not None and top_k_raw > configured_top_k:
        raise SamplingMaskAssemblyError(
            "sampling_mask_top_k_exceeds_configured",
            f"请求 top_k={top_k_raw} 超过会话配置上界 {configured_top_k}"
            "（上游 should_return_sampling_mask 同款 request<=configured：请求 body "
            "不得静默放大支持集硬上界）。",
        )

    temperature = float(_explicit("temperature"))
    if temperature != float(expected_temperature):
        raise SamplingMaskAssemblyError(
            "sampling_mask_temperature_mismatch",
            f"请求 temperature={temperature} 与会话配置 {expected_temperature} 不一致"
            "（trainer 按配置温度缩放 logits 重放支持集内分布，温度漂移即分布漂移）。",
        )

    for name, allowed in _UNSUPPORTED_LOGIT_PARAMS.items():
        if sampling_params.get(name) not in allowed:
            raise SamplingMaskAssemblyError(
                "sampling_mask_unsupported_logit_param",
                f"{name}={sampling_params.get(name)!r} 与 sampling-support replay 不兼容："
                "trainer 无法重现该 logit 变换（上游同款拒绝表）。",
            )

    return {"top_p": top_p, "top_k": int(top_k_raw), "temperature": temperature}


# ---------------------------------------------------------------------------
# 2. 响应解析校验（对照上游 append_sampling_metadata + _sampling_mask_from_supports）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TurnSupport:
    """一轮 /generate 的采样支持集事实（解析校验后的形态）。

    与 `adapters.slime.generate.TurnTape` 同型的锚定接口
    （output_ids / response_token_count），使 `_match_turns_to_runs`
    可以直接复用同一 run<->turn 锚定实现。
    """

    output_ids: tuple[int, ...]
    supports: tuple[tuple[int, ...], ...] = field(repr=False)  # 每 token 的支持集

    def __post_init__(self) -> None:
        if len(self.supports) != len(self.output_ids):
            raise SamplingMaskAssemblyError(
                "turn_support_length_mismatch",
                f"支持集条数 {len(self.supports)} != 输出 token 数 {len(self.output_ids)}。",
            )
        for pos, (token, support) in enumerate(zip(self.output_ids, self.supports)):
            if not support:
                raise SamplingMaskAssemblyError(
                    "turn_support_empty",
                    f"第 {pos} 个生成 token 的支持集为空（上游构造器同禁：每个采样"
                    " token 至少含它自己）。",
                )
            if int(token) not in support:
                raise SamplingMaskAssemblyError(
                    "turn_sampled_not_in_support",
                    f"第 {pos} 个生成 token {token} 不在其支持集内——引擎出站有 "
                    "force-include 保证，出现此况即传输错位或数据损坏（fail-closed）。",
                )

    @property
    def response_token_count(self) -> int:  # _match_turns_to_runs 锚定接口
        return len(self.output_ids)


def parse_turn_sampling_support(
    output_ids: Sequence[int],
    meta_info: Mapping[str, Any],
) -> tuple[TurnSupport, list[float]]:
    """解析一轮响应 meta_info 的 sampling mask + support-normalized logprobs。

    语义对照上游 append_sampling_metadata（generate_utils/sampling_mask.py:80-101）：

    - 两个字段必须同时在场；唯一豁免是 abort 且零输出 token（引擎中止时
      什么都没采样，返回空结果）；
    - logprob 条数必须等于输出 token 数；
    - 支持集经 TurnSupport 校验（非空 + sampled ∈ support，对应上游
      _sampling_mask_from_supports 的逐 token 检查）。

    返回 (TurnSupport, support-normalized logprobs)。后者是 T0-B 拍板的
    **正式 DIS/TIS 分母列**（behavior_support_logprob）；全词表 logprob
    仍留在 raw_response 的 output_token_logprobs 里作诊断列，本函数不动它。
    """

    supports_raw = meta_info.get("output_token_sampling_mask")
    logprobs_raw = meta_info.get("output_token_sampling_logprobs")
    if supports_raw is None or logprobs_raw is None:
        finish = meta_info.get("finish_reason") or {}
        if isinstance(finish, Mapping) and finish.get("type") == "abort" and not output_ids:
            return TurnSupport(output_ids=(), supports=()), []
        raise SamplingMaskAssemblyError(
            "sampling_mask_missing_in_response",
            "请求了 return_sampling_mask 但响应 meta_info 缺 output_token_sampling_mask/"
            "output_token_sampling_logprobs——引擎不是带原生 sampling-mask primitive 的 "
            "sglang-miles 构建（stock SGLang 静默忽略形态，fail-closed）。",
        )

    if len(logprobs_raw) != len(output_ids):
        raise SamplingMaskAssemblyError(
            "sampling_logprob_length_mismatch",
            f"support-normalized logprob 条数 {len(logprobs_raw)} != 输出 token 数 "
            f"{len(output_ids)}。",
        )
    if len(supports_raw) != len(output_ids):
        raise SamplingMaskAssemblyError(
            "sampling_mask_length_mismatch",
            f"支持集条数 {len(supports_raw)} != 输出 token 数 {len(output_ids)}。",
        )

    supports = tuple(tuple(int(t) for t in support) for support in supports_raw)
    turn = TurnSupport(output_ids=tuple(int(t) for t in output_ids), supports=supports)
    return turn, [float(v) for v in logprobs_raw]


# ---------------------------------------------------------------------------
# 3. 跨轮装配（对照上游 merge_sampling_masks/concatenate + 单例补齐）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AssembledSamplingMask:
    """一条叶链 response 的完整支持集，CSR 形态（纯 Python，无 torch 依赖）。

    不变量（__post_init__ 强制，均对照上游 RolloutSamplingMask.__post_init__）：
    offsets[0]=0、严格递增（**无零宽 span**——观察位已被单例补齐）、
    offsets[-1]==len(ids)、len(offsets)==response_token_count+1、
    ids 全部落在 int32 值域（wire dtype：ids int32 / offsets int64）。
    """

    ids: tuple[int, ...]
    offsets: tuple[int, ...]
    response_token_count: int
    sampled_token_count: int  # 引擎采样位（支持集来自引擎）数
    singleton_token_count: int  # 观察/工具位（单例补齐）数

    def __post_init__(self) -> None:
        if len(self.offsets) != self.response_token_count + 1:
            raise SamplingMaskAssemblyError(
                "assembled_offsets_length",
                f"offsets 长度 {len(self.offsets)} != response_token_count+1 "
                f"({self.response_token_count + 1})。",
            )
        if not self.offsets or self.offsets[0] != 0 or self.offsets[-1] != len(self.ids):
            raise SamplingMaskAssemblyError(
                "assembled_offsets_bounds",
                "offsets 必须以 0 起、以 ids 总数收（上游 RolloutSamplingMask 同款）。",
            )
        if any(b <= a for a, b in zip(self.offsets, self.offsets[1:])):
            raise SamplingMaskAssemblyError(
                "assembled_zero_width_span",
                "offsets 必须严格递增：每个 response token 都要有非空支持集"
                "（观察位由单例补齐，零宽 span 不合法——上游构造器同禁）。",
            )
        if self.sampled_token_count + self.singleton_token_count != self.response_token_count:
            raise SamplingMaskAssemblyError(
                "assembled_position_accounting",
                f"采样位 {self.sampled_token_count} + 单例位 {self.singleton_token_count} "
                f"!= response token 数 {self.response_token_count}。",
            )
        for value in self.ids:
            if not (_INT32_MIN <= value <= _INT32_MAX):
                raise SamplingMaskAssemblyError(
                    "assembled_id_out_of_int32",
                    f"支持集 token id {value} 超出 int32 值域（wire dtype ids={IDS_WIRE_DTYPE}）。",
                )

    def support_at(self, position: int) -> tuple[int, ...]:
        return self.ids[self.offsets[position] : self.offsets[position + 1]]


def assemble_leaf_sampling_mask(
    response_tokens: Sequence[int],
    loss_mask: Sequence[int],
    turns: Sequence[TurnSupport],
    *,
    identity_spans: Sequence[TurnIdentitySpan] | None = None,
) -> AssembledSamplingMask:
    """把各轮引擎支持集装配成叶链 response 的完整 CSR mask。

    步骤（每步的语义出处见模块 docstring）：

    1. run<->turn 锚定分两档（F1 身份制修复，与 backfill_leaf_sample 同款
       双路径）：``identity_spans`` 非 None = 身份路径，归属由树侧身份
       span 直取、token 相等降级为校验断言（`_runs_from_identity_spans`，
       漂移 fail-closed；调用方保证 turns[i] 与 spans[i] 同轮）；None =
       旧链，loss_mask=1 连续段必须被捕获轮的 output_ids 按序逐位平铺
       （`_match_turns_to_runs`，与 top-p tape 回填同一实现——掉落轮
       跳过，段无法平铺当场炸）；
    2. 采样位（mask=1）取该轮引擎支持集；防御性复检 response token ∈ 支持集
       （parse 层已按轮校验过 sampled∈support，这里按最终座标再核一次，
       防跨轮拼接错位）；
    3. 观察位（mask=0，含工具结果/模板文本/掉落轮残留上下文）补单例支持集
       {该 token}（上游 append_forced_sampling_tokens 语义；spike P0-3 已证
       与 slime 零宽 pad 在 logprob/梯度/熵三个口径精确等价）；
    4. 拼接即重基：CSR 顺序写入，offsets 天然是"前缀 id 总数"（上游
       concatenate 的 `offsets[1:] + id_count` 等价形态）。
    """

    if len(response_tokens) != len(loss_mask):
        raise SamplingMaskAssemblyError(
            "response_loss_mask_length_mismatch",
            f"response token 数 {len(response_tokens)} != loss_mask 长度 {len(loss_mask)}。",
        )
    if any(v not in (0, 1) for v in loss_mask):
        raise SamplingMaskAssemblyError(
            "loss_mask_not_binary",
            "loss_mask 只允许 0/1（provenance 语义，装配层不解释其他值）。",
        )

    runs = _mask1_runs(list(loss_mask))
    try:
        if identity_spans is not None:
            per_run, _used = _runs_from_identity_spans(
                list(response_tokens), runs, list(turns), list(identity_spans)
            )
        else:
            per_run, _used = _match_turns_to_runs(
                list(response_tokens), runs, list(turns)
            )
    except Exception as exc:  # SlimeBindingError：转成本模块错误类型，reason 保留
        raise SamplingMaskAssemblyError(
            "turns_vs_runs_mismatch",
            f"轮次与 loss_mask 段锚定失败：{exc}",
        ) from exc

    per_position: list[tuple[int, ...] | None] = [None] * len(response_tokens)
    for (start, _end), segment in zip(runs, per_run):
        position = start
        for turn in segment:
            for token, support in zip(turn.output_ids, turn.supports):
                if int(response_tokens[position]) not in support:
                    raise SamplingMaskAssemblyError(
                        "assembled_sampled_not_in_support",
                        f"response 第 {position} 个 token {response_tokens[position]} "
                        "不在锚定轮的支持集内（跨轮拼接错位或数据损坏）。",
                    )
                per_position[position] = support
                position += 1

    sampled = sum(1 for s in per_position if s is not None)
    for position, support in enumerate(per_position):
        if support is None:
            if loss_mask[position] == 1:  # pragma: no cover - _match_turns_to_runs 已保证
                raise SamplingMaskAssemblyError(
                    "trainable_token_without_support",
                    f"mask=1 的 token {position} 没有引擎支持集。",
                )
            per_position[position] = (int(response_tokens[position]),)  # 单例补齐

    ids: list[int] = []
    offsets: list[int] = [0]
    for support in per_position:
        assert support is not None
        ids.extend(support)
        offsets.append(len(ids))

    return AssembledSamplingMask(
        ids=tuple(ids),
        offsets=tuple(offsets),
        response_token_count=len(response_tokens),
        sampled_token_count=sampled,
        singleton_token_count=len(response_tokens) - sampled,
    )


def attach_assembled_mask(slime_sample: Any, assembled: AssembledSamplingMask) -> None:
    """把装配产物挂到 vendor slime Sample 上（canonicalize slime 分支消费）。

    slime Sample dataclass 没有 rollout_sampling_mask 字段，一等字段只在
    miles 侧存在；装配产物以 ``rh2_sampling_mask`` 附加属性随样本走到
    canonicalize 边界，由 `_convert_slime_sample` 剥除并转成 miles
    `RolloutSamplingMask`。fail-closed：长度必须与样本 response_length 一致。
    """

    response_length = int(getattr(slime_sample, "response_length", 0) or 0)
    if assembled.response_token_count != response_length:
        raise SamplingMaskAssemblyError(
            "attached_mask_length_mismatch",
            f"装配 mask 覆盖 {assembled.response_token_count} 个 token，样本 "
            f"response_length={response_length}——不许挂半截 mask。",
        )
    setattr(slime_sample, ATTACHED_MASK_ATTR, assembled)
