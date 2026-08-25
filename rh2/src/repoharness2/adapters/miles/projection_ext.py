"""sampler_support_token_ids 新枚举的投影接线（miles 迁移 C1′-b，delta 清单第 3 项）。

为什么是新模块而不是改 `adapters/slime/projection.py`：projection 属 slime
冻结面（回退面语义，改动会污染既有 321 测试面的对照基准）；新枚举只被
miles 链路产出，接线放 adapters/miles 侧，冻结面零触碰。

职责：把装配层产物 `AssembledSamplingMask`（引擎支持集 + 观察位单例，CSR）
落成契约对象：

- `build_sampler_support_mask_ref` -> `SamplingMaskRef(mask_kind=
  "sampler_support_token_ids")`，tape 载荷按上游训练 wire dtype 打包：
  ids 小端 int32、offsets 小端 **int64**（miles train_data_conversion
  ROLLOUT_DATA_TENSOR_DTYPES 的 rollout_sampling_mask_ids/offsets 约定；
  注意与旧 top-p tape 的 int32 offsets 不同，消费方按 mask_kind 选解码宽度）。
- `build_support_logprob_provenance` -> `LogprobProvenance(normalization=
  "behavior_support_normalized")`（T0-B：Sample.rollout_log_probs 列 =
  support-normalized 行为 logprob，正式 DIS/TIS 分母；全词表列仅诊断）。
"""

from __future__ import annotations

import hashlib
import struct
from collections.abc import MutableMapping, Sequence

from repoharness2.adapters.miles.sampling_mask_assembly import (
    AssembledSamplingMask,
    SamplingMaskAssemblyError,
)
from repoharness2.contracts import ArtifactRef, LogprobProvenance, SamplingMaskRef


def _pack_artifact(
    ref_id: str,
    values: Sequence[int],
    fmt_char: str,
    store: MutableMapping[str, bytes] | None,
) -> ArtifactRef:
    """小端定宽整数打包 + digest 引用（同 projection._make_artifact_ref 范式，
    但支持 int64（fmt_char="q"）——offsets 的 wire dtype 是 int64）。"""

    payload = struct.pack(f"<{len(values)}{fmt_char}", *values)
    digest = "sha256:" + hashlib.sha256(payload).hexdigest()
    if store is not None:
        store[ref_id] = payload
    return ArtifactRef(ref_id=ref_id, sha256=digest, byte_size=len(payload))


def build_sampler_support_mask_ref(
    assembled: AssembledSamplingMask,
    *,
    top_p: float,
    top_k: int,
    trajectory_id: str,
    branch_id: str,
    store: MutableMapping[str, bytes] | None = None,
) -> SamplingMaskRef:
    """装配产物 -> sampler_support_token_ids 契约引用（fail-closed）。

    校验分层：CSR 结构不变量（offsets 递增/无零宽/int32 值域）已由
    AssembledSamplingMask.__post_init__ 强制；本函数补契约侧事实：
    top_p 必须 <1.0（replay 开关）、top_k 有限正、且**每个位置的支持集
    大小 <= top_k**（top_k 是硬上界——超界说明 tape 损坏或 top_k 记录错，
    进契约前拦截）。
    """

    if not isinstance(assembled, AssembledSamplingMask):
        raise SamplingMaskAssemblyError(
            "projection_wrong_type",
            f"期望 AssembledSamplingMask，得到 {type(assembled).__name__}。",
        )
    if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k <= 0:
        raise SamplingMaskAssemblyError(
            "projection_top_k_invalid",
            f"top_k={top_k!r} 必须为有限正整数（支持集硬上界，T0-A）。",
        )
    if assembled.response_token_count < 1:
        # 契约层 response_token_count ge=1 / offsets_len ge=2 本就不可表示
        # 零 token tape；这里提前拦成可读错误（也避免下面 max() 对空序列炸）。
        raise SamplingMaskAssemblyError(
            "projection_empty_mask",
            "零 response token 的装配 mask 不可投影——空分支没有可声明的支持集事实。",
        )
    widest = max(
        b - a for a, b in zip(assembled.offsets, assembled.offsets[1:])
    )
    if widest > top_k:
        raise SamplingMaskAssemblyError(
            "projection_support_exceeds_top_k",
            f"存在宽度 {widest} 的支持集超出 top_k={top_k}——top_k 是引擎侧硬上界，"
            "超界即 tape 损坏或生效值记录错误。",
        )

    ids_ref = _pack_artifact(
        f"{trajectory_id}_{branch_id}_support_ids", assembled.ids, "i", store
    )
    offsets_ref = _pack_artifact(
        f"{trajectory_id}_{branch_id}_support_offsets", assembled.offsets, "q", store
    )
    return SamplingMaskRef(
        mask_kind="sampler_support_token_ids",
        top_p=top_p,  # 契约层强制 <1.0（SamplingMaskRef 校验器）
        top_k=top_k,
        token_ids_ref=ids_ref,
        offsets_ref=offsets_ref,
        response_token_count=assembled.response_token_count,
        offsets_len=len(assembled.offsets),
        kept_token_count=assembled.offsets[-1],
    )


def build_support_logprob_provenance(
    *,
    engine_version: str,
    precision: str,
    sampling_backend: str | None = None,
    weight_version: str | None = None,
) -> LogprobProvenance:
    """support-normalized 行为 logprob 列的出处标注（T0-B 正式分母列）。

    engine_name 固定 "sglang"（sampling-support replay 只存在于 sglang-miles
    构建）；normalization 固定 "behavior_support_normalized"——全词表诊断列
    如需标注应另建对象填 "full_vocab"，两列口径不得共用一个 provenance。
    """

    return LogprobProvenance(
        engine_name="sglang",
        engine_version=engine_version,
        precision=precision,  # type: ignore[arg-type]  # 契约 Literal 校验兜底
        sampling_backend=sampling_backend,
        weight_version=weight_version,
        normalization="behavior_support_normalized",
    )
