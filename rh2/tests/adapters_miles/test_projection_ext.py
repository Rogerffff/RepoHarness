"""C1′-b delta 测试 (e)：sampler_support_token_ids 新枚举契约 + projection_ext 接线。

覆盖面：
- SamplingMaskRef 新枚举：合法构造 round-trip（model_dump_json →
  model_validate_json 无损）;必填/互斥校验逐条（top_k 必填、top_p<1.0、
  tape 字段齐全、offsets_len=response+1、kept>=response 无零宽下界、
  旧三态不得携带 top_k——新增不改旧）;
- LogprobProvenance.normalization 新字段：三态 + None（旧数据）合法;
- projection_ext：装配产物 → 契约引用（ids 小端 int32 / offsets 小端
  int64 wire dtype、sha256、kept=offsets[-1]）,top_k 上界/类型/空 mask/
  非装配产物拒绝;build_support_logprob_provenance 固定口径。
"""

from __future__ import annotations

import hashlib
import struct

import pytest
from pydantic import ValidationError

from repoharness2.contracts import (
    ArtifactRef,
    LogprobProvenance,
    SamplingMaskRef,
)

pytestmark = pytest.mark.integration_base


def _ref(name: str, payload: bytes = b"\x00" * 8) -> ArtifactRef:
    return ArtifactRef(
        ref_id=name,
        sha256="sha256:" + hashlib.sha256(payload).hexdigest(),
        byte_size=len(payload),
    )


def _support_kwargs(**over):
    kwargs = dict(
        mask_kind="sampler_support_token_ids",
        top_p=0.8,
        top_k=32,
        token_ids_ref=_ref("ids"),
        offsets_ref=_ref("offsets"),
        response_token_count=3,
        offsets_len=4,
        kept_token_count=5,
    )
    kwargs.update(over)
    return {k: v for k, v in kwargs.items() if v is not None}


# ---------------------------------------------------------------------------
# 新枚举契约
# ---------------------------------------------------------------------------


def test_support_kind_round_trip():
    ref = SamplingMaskRef(**_support_kwargs())
    again = SamplingMaskRef.model_validate_json(ref.model_dump_json())
    assert again == ref
    assert again.mask_kind == "sampler_support_token_ids"
    assert again.top_k == 32


@pytest.mark.parametrize(
    ("over", "fragment"),
    [
        ({"top_k": None}, "top_k 必填"),
        ({"top_p": 1.0}, "top_p < 1.0"),
        ({"token_ids_ref": None}, "缺失"),
        ({"offsets_ref": None}, "缺失"),
        ({"kept_token_count": None}, "缺失"),
        ({"offsets_len": 5}, "offsets 长度必须等于"),
        ({"kept_token_count": 2}, "无零宽 span"),  # kept < response:观察位单例保证下界
    ],
)
def test_support_kind_validation_rejections(over, fragment):
    with pytest.raises(ValidationError, match=fragment):
        SamplingMaskRef(**_support_kwargs(**over))


@pytest.mark.parametrize(
    "legacy_kwargs",
    [
        dict(mask_kind="not_applicable_top_p_1", top_p=1.0),
        dict(mask_kind="not_captured_text_relay", top_p=None),
        dict(
            mask_kind="top_p_kept_token_ids",
            top_p=0.95,
            token_ids_ref=_ref("ids"),
            offsets_ref=_ref("offsets"),
            response_token_count=16,
            offsets_len=17,
            kept_token_count=40,
        ),
    ],
)
def test_legacy_kinds_unchanged_and_reject_top_k(legacy_kwargs):
    # 新增不改旧：旧三态原语义可构造……
    SamplingMaskRef(**legacy_kwargs)
    # ……但不得携带新字段 top_k
    with pytest.raises(ValidationError, match="不得携带 top_k"):
        SamplingMaskRef(**{**legacy_kwargs, "top_k": 32})


@pytest.mark.parametrize("normalization", ["behavior_support_normalized", "full_vocab", "not_captured", None])
def test_logprob_provenance_normalization_states(normalization):
    prov = LogprobProvenance(
        engine_name="sglang",
        engine_version="0.5.9",
        precision="bfloat16",
        normalization=normalization,
    )
    again = LogprobProvenance.model_validate_json(prov.model_dump_json())
    assert again.normalization == normalization


def test_logprob_provenance_unknown_normalization_rejected():
    with pytest.raises(ValidationError):
        LogprobProvenance(
            engine_name="sglang",
            engine_version="0.5.9",
            precision="bfloat16",
            normalization="renormalized_somehow",
        )


# ---------------------------------------------------------------------------
# projection_ext 接线
# ---------------------------------------------------------------------------


@pytest.fixture()
def ext(world):
    from repoharness2.adapters.miles import projection_ext, sampling_mask_assembly

    return projection_ext, sampling_mask_assembly


def _assembled(sma):
    turns = [
        sma.TurnSupport(output_ids=(4, 5), supports=((4, 9, 10), (5, 2))),
        sma.TurnSupport(output_ids=(7,), supports=((7, 8),)),
    ]
    return sma.assemble_leaf_sampling_mask([4, 5, 6, 7], [1, 1, 0, 1], turns)


def test_build_support_mask_ref_wire_payloads(ext):
    projection_ext, sma = ext
    assembled = _assembled(sma)
    store: dict[str, bytes] = {}
    ref = projection_ext.build_sampler_support_mask_ref(
        assembled,
        top_p=0.8,
        top_k=32,
        trajectory_id="traj1",
        branch_id="b0",
        store=store,
    )

    assert ref.mask_kind == "sampler_support_token_ids"
    assert ref.top_k == 32 and ref.top_p == 0.8
    assert ref.response_token_count == 4
    assert ref.offsets_len == 5
    # kept = 3+2+1+2 = 8（采样位支持集 + 观察位单例,无零宽）
    assert ref.kept_token_count == assembled.offsets[-1] == len(assembled.ids) == 8

    ids_payload = store["traj1_b0_support_ids"]
    offsets_payload = store["traj1_b0_support_offsets"]
    # wire dtype：ids 小端 int32,offsets 小端 int64（上游训练 wire 约定;
    # 与旧 top-p tape 的 int32 offsets 不同,消费方按 mask_kind 选解码宽度）
    assert struct.unpack(f"<{len(assembled.ids)}i", ids_payload) == assembled.ids
    assert struct.unpack(f"<{len(assembled.offsets)}q", offsets_payload) == assembled.offsets
    assert len(ids_payload) == 4 * len(assembled.ids)
    assert len(offsets_payload) == 8 * len(assembled.offsets)
    assert ref.token_ids_ref.sha256 == "sha256:" + hashlib.sha256(ids_payload).hexdigest()
    assert ref.offsets_ref.sha256 == "sha256:" + hashlib.sha256(offsets_payload).hexdigest()

    # 契约 round-trip（接线产物直接可入投影层）
    assert SamplingMaskRef.model_validate_json(ref.model_dump_json()) == ref


def test_build_support_mask_ref_rejections(ext):
    projection_ext, sma = ext
    assembled = _assembled(sma)
    err = sma.SamplingMaskAssemblyError

    with pytest.raises(err) as exc:
        projection_ext.build_sampler_support_mask_ref(
            assembled, top_p=0.8, top_k=2, trajectory_id="t", branch_id="b"
        )  # 存在宽度 3 的支持集 > top_k=2
    assert exc.value.reason_code == "projection_support_exceeds_top_k"

    for bad_top_k in (0, -1, True, "32"):
        with pytest.raises(err) as exc:
            projection_ext.build_sampler_support_mask_ref(
                assembled, top_p=0.8, top_k=bad_top_k, trajectory_id="t", branch_id="b"
            )
        assert exc.value.reason_code == "projection_top_k_invalid"

    with pytest.raises(err) as exc:
        projection_ext.build_sampler_support_mask_ref(
            ([1], [0, 1]), top_p=0.8, top_k=4, trajectory_id="t", branch_id="b"
        )
    assert exc.value.reason_code == "projection_wrong_type"

    empty = sma.AssembledSamplingMask(
        ids=(), offsets=(0,), response_token_count=0, sampled_token_count=0, singleton_token_count=0
    )
    with pytest.raises(err) as exc:
        projection_ext.build_sampler_support_mask_ref(
            empty, top_p=0.8, top_k=4, trajectory_id="t", branch_id="b"
        )
    assert exc.value.reason_code == "projection_empty_mask"


def test_build_support_logprob_provenance_fixed_semantics(ext):
    projection_ext, _ = ext
    prov = projection_ext.build_support_logprob_provenance(
        engine_version="0.5.9-miles",
        precision="bfloat16",
        sampling_backend="pytorch",
        weight_version="w7",
    )
    assert prov.engine_name == "sglang"
    assert prov.normalization == "behavior_support_normalized"
    assert LogprobProvenance.model_validate_json(prov.model_dump_json()) == prov
