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
from collections.abc import Callable, MutableMapping, Sequence
from typing import Any

from repoharness2.adapters.miles.sampling_mask_assembly import (
    ATTACHED_MASK_ATTR,
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


# ---------------------------------------------------------------------------
# B2（R6-ext）：project_from_slime 的 mask 链路包装（冻结面零触碰的接线点）
# ---------------------------------------------------------------------------


def project_group_with_sampler_support(
    project: Callable[[], Any],
    samples: Sequence[Any],
    *,
    top_k: Any,
    store: MutableMapping[str, bytes] | None = None,
) -> Any:
    """把一次 mask 链路的投影跑通并落成 sampler_support_token_ids 事实。

    为什么长这个形状：`adapters/slime/projection.py` 是冻结面，其
    `_build_sampling_mask` 分支只认旧 slime tape 字段
    ``rollout_top_p_token_ids/offsets``——top_p<1.0 且无该字段直接
    fail-closed，mask 链路的样本（支持集在 ``rh2_sampling_mask`` 附加属性
    上）根本跑不进投影。最小侵入做法（冻结面一行不改）分三步：

    1. **临时借道**：把每条样本的装配 CSR 临时写进旧 tape 字段再调
       ``project()``（调用方给的零参闭包 = 原样的 project_from_slime 调用）。
       冻结面对该 CSR 跑的结构校验（offsets 长度/单调/mask=1 非零宽/首尾
       一致）恰是支持集 tape 的真子集校验，不是骗过——是复用。finally
       无条件还原字段为 None（canonicalize 会把残留旧 tape 字段按
       slime_field_rejected 拒绝，还原是硬要求）。
    2. **分支替换**：把每个 BranchProjection 的 SamplingMaskRef 换成
       build_sampler_support_mask_ref（mask_kind=sampler_support_token_ids、
       top_k 硬上界、ids int32/offsets int64 打包），LogprobProvenance 换成
       behavior_support_normalized（T0-B：Sample.rollout_log_probs 列即
       support-normalized 行为 logprob）；同时从 store 删掉第 1 步顺带写出
       的 `_topp_ids/_topp_offsets` 诱饵 artifact（不留一份挂着 top-p 名字
       的支持集 tape 误导审计）。
    3. **整树重校验**：pydantic model_copy 不重跑校验器，替换后经
       model_validate(model_dump()) 全量重校验（分支/树级不变量对新
       mask_kind 再过一遍）。

    fail-closed：任一样本缺装配 mask、样本已带旧 tape 字段、分支缺行为
    logprob provenance、engine 不是 sglang，一律抛 SamplingMaskAssemblyError。
    """

    samples = list(samples)
    attached: list[AssembledSamplingMask] = []
    for position, sample in enumerate(samples):
        mask = getattr(sample, ATTACHED_MASK_ATTR, None)
        if not isinstance(mask, AssembledSamplingMask):
            raise SamplingMaskAssemblyError(
                "projection_mask_not_attached",
                f"mask 链路投影要求每条叶链样本都带装配 mask（{ATTACHED_MASK_ATTR}），"
                f"第 {position} 条缺失/类型错（got {type(mask).__name__}）——"
                "装配步（generate step5）没有跑到或被绕过。",
            )
        if (
            getattr(sample, "rollout_top_p_token_ids", None) is not None
            or getattr(sample, "rollout_top_p_token_offsets", None) is not None
        ):
            raise SamplingMaskAssemblyError(
                "projection_conflicting_top_p_tape",
                f"第 {position} 条样本同时带旧 top-p tape 字段与装配 mask——"
                "两套支持集账并存，禁止投影（借道会覆盖真实旧 tape）。",
            )
        attached.append(mask)

    # 第 1 步：临时借道旧 tape 字段（finally 无条件还原为 None）。
    for sample, mask in zip(samples, attached):
        sample.rollout_top_p_token_ids = list(mask.ids)
        sample.rollout_top_p_token_offsets = list(mask.offsets)
    try:
        projection = project()
    finally:
        for sample in samples:
            sample.rollout_top_p_token_ids = None
            sample.rollout_top_p_token_offsets = None

    # 第 2 步：逐分支替换（project_from_slime 的 branches 与 samples 一一
    # 对应且同序——zip(samples, annotations) 的构造顺序）。
    new_branches = []
    for branch, mask in zip(projection.branches, attached, strict=True):
        old_ref = branch.sampling_mask
        if old_ref.mask_kind != "top_p_kept_token_ids":
            raise SamplingMaskAssemblyError(
                "projection_unexpected_mask_kind",
                f"分支 {branch.branch_id} 借道后 mask_kind={old_ref.mask_kind}"
                "（期望 top_p_kept_token_ids）——冻结面行为漂移，停手重审。",
            )
        if store is not None:
            # 诱饵 artifact 清理：第 1 步让冻结面按旧命名写了一份同内容 tape
            store.pop(f"{projection.trajectory_id}_{branch.branch_id}_topp_ids", None)
            store.pop(f"{projection.trajectory_id}_{branch.branch_id}_topp_offsets", None)
        mask_ref = build_sampler_support_mask_ref(
            mask,
            top_p=old_ref.top_p,
            top_k=top_k,
            trajectory_id=projection.trajectory_id,
            branch_id=branch.branch_id,
            store=store,
        )
        old_provenance = branch.logprob_provenance
        if old_provenance is None:
            raise SamplingMaskAssemblyError(
                "projection_behavior_logprobs_missing",
                f"分支 {branch.branch_id} 无 logprob provenance（rollout_log_probs "
                "缺失）——mask 链路的行为 logprob（support-normalized）是 DIS/TIS "
                "正式分母，缺失不可投影。",
            )
        if old_provenance.engine_name != "sglang":
            raise SamplingMaskAssemblyError(
                "projection_engine_not_sglang",
                f"分支 {branch.branch_id} engine={old_provenance.engine_name}——"
                "sampling-support replay 只存在于 sglang-miles 构建。",
            )
        new_provenance = build_support_logprob_provenance(
            engine_version=old_provenance.engine_version,
            precision=old_provenance.precision,
            sampling_backend=old_provenance.sampling_backend,
            weight_version=old_provenance.weight_version,
        )
        new_branches.append(
            branch.model_copy(
                update={
                    "sampling_mask": mask_ref,
                    "logprob_provenance": new_provenance,
                }
            )
        )

    # 第 3 步：整树重校验。
    updated = projection.model_copy(update={"branches": new_branches})
    return type(projection).model_validate(updated.model_dump())
