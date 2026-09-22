"""E3（第六组 I23）：routing tape 紧凑表示——快路径与旧路径逐位等价、旧拒绝语义不变、叶张量生命周期。

差分口径（Codex E3 计划复核 ER1–ER3）：

- wire 形态（base64 / bytes / bytearray）直通，与 `decode_int32_tape` + `_int32_bytes` 的旧归一化逐位相同；
- memoryview / 带 `.tolist()` 的对象 / list 保持旧归一化与旧错误分类（memoryview 不修正）；
- 投影层：3 维 int32 数组走快路径但保留配置轴对照与引擎行数公式；int64 值域内接受、超界 / float / bool
  拒绝、空张量、1 维张量、非小端主机都回落旧路径，旧的错误顺序不变；
- capture hook：store 与 TurnTape 引用同一个 bytes；list 形态的超界仍是原生 struct.error；
- backfill：前缀裁剪按字节切片；每叶自有可写张量，修改一叶不影响捕获工件与另一叶；无配置保底仍交付 list。
"""

from __future__ import annotations

import array
import base64
import gc
import hashlib
import struct
import sys
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fixtures.common import FixtureSlimeSample, b64_int32, routing_flat

from repoharness2.adapters.slime import generate as G
from repoharness2.adapters.slime import projection as P
from repoharness2.adapters.slime.generate import GenerationCaptureHook, backfill_leaf_sample

LAYERS, TOPK = 2, 2
PER_ROW = LAYERS * TOPK
EDGE = [-(2**31), -1, 0, 1, 127, 128, 256, 2**31 - 1]
SP = {
    "temperature": 1.0,
    "top_p": 1.0,
    "max_new_tokens": 64,
    "return_top_p_token_ids": False,
    "return_routed_experts": True,
}


def _packed(values):
    return struct.pack(f"<{len(values)}i", *values)


def _sha(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _old_payload(value, field="probe"):
    """旧归一化：展开成 Python 整数再打包（生产里仍是慢路径本身）。"""

    return P._int32_bytes(P.decode_int32_tape(value, field_name=field), field)


def _nested(flat, rows):
    return [
        [flat[r * PER_ROW + layer * TOPK : r * PER_ROW + layer * TOPK + TOPK] for layer in range(LAYERS)]
        for r in range(rows)
    ]


def _hook(trajectory_id="e3"):
    return GenerationCaptureHook(
        trajectory_id=trajectory_id,
        model_name="Qwen/Qwen3-30B-A3B",
        backend_name="sglang",
        backend_version="0.5.13",
        renderer_cls_name="Qwen3Renderer",
        tokenizer_name="Qwen/Qwen3-30B-A3B",
        template_hash="sha256:" + "a" * 64,
    )


def _response(routed, *, gen):
    return {
        "text": "x",
        "meta_info": {
            "id": "rid",
            "weight_version": "1",
            "finish_reason": {"type": "stop"},
            "output_token_logprobs": [[-(i + 1) * 0.05, t, None] for i, t in enumerate(gen)],
            G._ROUTED_EXPERTS_META_KEY: routed,
        },
    }


def _routing(value, *, prompt_len=3, response_len=2, layers=LAYERS, topk=TOPK, store=None):
    return P._build_routing(
        SimpleNamespace(rollout_routed_experts=value),
        branch_id="b0",
        trajectory_id="t",
        prompt_len=prompt_len,
        response_len=response_len,
        engine_name="sglang",
        tape_requested=True,
        moe_num_layers=layers,
        moe_router_topk=topk,
        store=store,
    )


def _leaf(tokens, gen_len):
    return FixtureSlimeSample(
        tokens=list(tokens),
        response_length=gen_len,
        loss_mask=[1] * gen_len,
        rollout_log_probs=[-(i + 1) * 0.05 for i in range(gen_len)],
        rollout_id=9,
        index=0,
    )


# ---------------------------------------------------------------------------
# 解码直通点
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("form", ["base64", "bytes", "bytearray"])
def test_wire_forms_bypass_python_ints_and_match_the_old_normalization(form):
    values = EDGE + routing_flat(250, LAYERS, TOPK)
    raw = _packed(values)
    value = {"base64": base64.b64encode(raw).decode("ascii"), "bytes": raw, "bytearray": bytearray(raw)}[form]
    fast = P.decode_int32_tape_bytes(value, field_name="x")
    assert isinstance(fast, bytes) and fast == raw == _old_payload(value)


def test_non_wire_forms_keep_the_old_normalization_and_error_codes():
    mv = memoryview(_packed([1]))
    # ER1：memoryview 在旧实现里先 .tolist()（bytes 底座 -> 逐字节整数），这里不修正
    assert P.decode_int32_tape_bytes(mv, field_name="x") == _old_payload(mv) == _packed([1, 0, 0, 0])
    assert P.decode_int32_tape_bytes(_nested([1, 2, 3, 4], 1), field_name="x") == _packed([1, 2, 3, 4])
    for value, reason in [
        (memoryview(array.array("f", [1.0])), "tape_element_not_int"),
        ([1.5], "tape_element_not_int"),
        ([True], "tape_element_not_int"),
        ([2**31], "tape_value_out_of_int32"),
        ("not base64!!", "tape_base64_invalid"),
        (b"\x01\x00\x00\x00\x00", "tape_bytes_not_int32"),
        (bytearray(b"\x01\x00\x00"), "tape_bytes_not_int32"),
        (None, "tape_payload_missing"),
        (object(), "tape_type_unsupported"),
    ]:
        with pytest.raises(P.SlimeProjectionError) as new_exc:
            P.decode_int32_tape_bytes(value, field_name="x")
        with pytest.raises(P.SlimeProjectionError) as old_exc:
            _old_payload(value)
        assert new_exc.value.reason_code == old_exc.value.reason_code == reason, value


# ---------------------------------------------------------------------------
# 投影层（_build_routing 是生产的分支级调用点）
# ---------------------------------------------------------------------------


def test_build_routing_fast_and_old_paths_produce_the_same_artifact_bit_for_bit():
    torch = pytest.importorskip("torch")
    numpy = pytest.importorskip("numpy")
    values = EDGE * 2  # 4 行 x 2 层 x 2
    raw = _packed(values)
    strided = numpy.zeros((4, LAYERS, 2 * TOPK), dtype="<i4")
    strided[:, :, ::2] = numpy.array(values, dtype="<i4").reshape(4, LAYERS, TOPK)
    noncontiguous = strided[:, :, ::2]
    assert not noncontiguous.flags.c_contiguous
    forms = {
        # 快路径
        "int32_tensor": torch.tensor(values, dtype=torch.int32).reshape(4, LAYERS, TOPK),
        "big_endian_ndarray": numpy.array(values, dtype=">i4").reshape(4, LAYERS, TOPK),
        "noncontiguous_ndarray": noncontiguous,
        "base64": base64.b64encode(raw).decode("ascii"),
        "bytes": raw,
        # 旧路径（回退，不是拒绝）
        "int64_tensor_in_range": torch.tensor(values, dtype=torch.int64).reshape(4, LAYERS, TOPK),
        "int32_tensor_1d": torch.tensor(values, dtype=torch.int32),
        "nested_list": _nested(values, 4),
        "flat_list": list(values),
    }
    for name, value in forms.items():
        store: dict[str, bytes] = {}
        ref = _routing(value, store=store)
        facts = (
            ref.alignment, ref.dtype, ref.num_rows, ref.num_layers, ref.router_topk,
            ref.tensor_ref.sha256, ref.tensor_ref.byte_size,
        )
        assert facts == ("sglang_prompt_minus1_plus_gen", "int32", 4, LAYERS, TOPK, _sha(raw), len(raw)), name
        assert store[ref.tensor_ref.ref_id] == raw, name
    # 空张量：快路径不启用（回旧分支）；零行本来就过不了 RoutingTensorRef 契约（num_rows >= 1），
    # 空张量与空 list 在同一处、以同一类异常被拒——不为零行另建支持能力（Codex ER2）
    import pydantic

    empty = torch.empty((0, LAYERS, TOPK), dtype=torch.int32)
    assert P._routing_int32_array_payload(empty) is None
    for value in (empty, []):
        with pytest.raises(pydantic.ValidationError, match="num_rows"):
            _routing(value, prompt_len=1, response_len=0)


def test_build_routing_keeps_old_rejections_precedence_and_fallbacks():
    torch = pytest.importorskip("torch")
    small = torch.tensor(EDGE * 2, dtype=torch.int32).reshape(4, LAYERS, TOPK)
    overflow = small.to(torch.int64)
    overflow[0, 0, 0] = 2**31
    cases = [
        (overflow, {}, "tape_value_out_of_int32"),
        (small.to(torch.float32), {}, "tape_element_not_int"),
        (small.to(torch.bool), {}, "tape_element_not_int"),
        # 快路径保留配置轴对照；旧路径同一判据同一文案
        (torch.arange(24, dtype=torch.int32).reshape(4, 3, TOPK), {}, "routing_shape_mismatch"),
        (torch.arange(24, dtype=torch.int64).reshape(4, 3, TOPK), {}, "routing_shape_mismatch"),
        # 快路径仍过 _build_routing 的引擎行数公式
        (small, {"response_len": 3}, "routing_rows_mismatch"),
        (b64_int32(list(range(16))), {"layers": None, "topk": None}, "routing_shape_unknown"),
        (b64_int32(list(range(15))), {}, "routing_numel_mismatch"),
        (b"\x00" * 15, {}, "tape_bytes_not_int32"),
        # 旧顺序：先行数公式，后打包（超界 + 行数错的双重非法输入报行数）
        (overflow, {"response_len": 3}, "routing_rows_mismatch"),
    ]
    for value, overrides, reason in cases:
        with pytest.raises(P.SlimeProjectionError) as exc:
            _routing(value, **overrides)
        assert exc.value.reason_code == reason, (reason, overrides)


def test_array_fast_path_is_disabled_off_little_endian_hosts(monkeypatch):
    torch = pytest.importorskip("torch")
    small = torch.tensor(EDGE * 2, dtype=torch.int32).reshape(4, LAYERS, TOPK)
    monkeypatch.setattr(sys, "byteorder", "big")
    assert P._routing_int32_array_payload(small) is None
    assert _routing(small).tensor_ref == _routing(list(EDGE * 2)).tensor_ref  # 走旧路径，结果不变


# ---------------------------------------------------------------------------
# capture hook
# ---------------------------------------------------------------------------


def test_capture_hook_shares_one_bytes_object_between_store_and_turn_tape():
    flat = routing_flat(4, LAYERS, TOPK)  # prompt 3 - 1 + gen 2 = 4 行
    hook = _hook()
    record = hook.on_generate_response(
        prompt_token_ids=[1, 2, 3], sampling_params=SP, response=_response(b64_int32(flat), gen=[5, 6])
    )
    payload = hook.artifact_store[f"{record.record_id}_routing"]
    assert hook.tapes[-1].routed_experts_le_int32 is payload  # 同一个对象，不是第二份
    assert payload == _packed(flat) and record.capture_status == "complete"
    assert (record.routed_experts_ref.sha256, record.routed_experts_ref.byte_size) == (_sha(payload), len(payload))
    # 旧形态（list）照旧可用且字节相同
    other = _hook()
    rec2 = other.on_generate_response(
        prompt_token_ids=[1, 2, 3], sampling_params=SP, response=_response(list(flat), gen=[5, 6])
    )
    assert other.artifact_store[f"{rec2.record_id}_routing"] == payload
    # ER2：list 形态里的超界整数仍是旧的原生 struct.error，不是投影错误
    with pytest.raises(struct.error):
        _hook().on_generate_response(
            prompt_token_ids=[1, 2, 3], sampling_params=SP, response=_response([2**31] + flat[1:], gen=[5, 6])
        )


def test_capture_records_are_identical_across_wire_and_nested_forms(monkeypatch):
    monkeypatch.setattr(G, "_now_utc", lambda: datetime(2026, 9, 22, tzinfo=timezone.utc))
    flat = routing_flat(4, LAYERS, TOPK)
    a, b = _hook(), _hook()
    ra = a.on_generate_response(
        prompt_token_ids=[1, 2, 3], sampling_params=SP, response=_response(b64_int32(flat), gen=[5, 6])
    )
    rb = b.on_generate_response(
        prompt_token_ids=[1, 2, 3], sampling_params=SP, response=_response(_nested(flat, 4), gen=[5, 6])
    )
    # 原始 meta_info 本来就不同（base64 串 vs 嵌套 list），其摘要之外的全部字段逐一相等
    assert ra.model_dump(exclude={"raw_meta_info_digest"}) == rb.model_dump(exclude={"raw_meta_info_digest"})
    assert ra.raw_meta_info_digest != rb.raw_meta_info_digest
    assert a.tapes[-1] == b.tapes[-1]
    assert a.artifact_store == b.artifact_store


# ---------------------------------------------------------------------------
# backfill / 叶张量生命周期
# ---------------------------------------------------------------------------


def test_backfill_trims_prefix_by_bytes_and_each_leaf_owns_a_writable_tensor():
    torch = pytest.importorskip("torch")
    capture_prompt = [1000 + i for i in range(15)]
    leaf_prompt = capture_prompt[2:]
    gen = [2000 + i for i in range(16)]
    capture_rows, leaf_rows = 15 - 1 + 16, 13 - 1 + 16  # 30 / 28
    flat = routing_flat(capture_rows, LAYERS, TOPK)
    hook = _hook("trim")
    hook.on_generate_response(
        prompt_token_ids=capture_prompt, sampling_params=SP, response=_response(b64_int32(flat), gen=gen)
    )
    key = f"{hook.records[0].record_id}_routing"
    snapshot = bytes(hook.artifact_store[key])
    expected = torch.tensor(flat[2 * PER_ROW :], dtype=torch.int32).reshape(leaf_rows, LAYERS, TOPK)

    leaf1, leaf2 = _leaf(leaf_prompt + gen, 16), _leaf(leaf_prompt + gen, 16)
    used = backfill_leaf_sample(leaf1, hook.tapes, moe_num_layers=LAYERS, moe_router_topk=TOPK)
    backfill_leaf_sample(leaf2, hook.tapes, moe_num_layers=LAYERS, moe_router_topk=TOPK)
    assert [t.record_id for t in used] == [hook.tapes[0].record_id]
    t1, t2 = leaf1.rollout_routed_experts, leaf2.rollout_routed_experts
    assert torch.equal(t1, expected) and t1.dtype == torch.int32 and t1.is_contiguous()
    assert leaf1.metadata["rh2_routing_backfill_trimmed_prefix_rows"] == 2
    assert leaf1.metadata["rh2_routing_backfill_actual_rows"] == capture_rows
    assert leaf1.metadata["rh2_routing_backfill_expected_rows"] == leaf_rows
    # 生命周期（ER3）：改一叶不影响另一叶，也不影响不可变的捕获工件与 TurnTape
    t1[0, 0, 0] = -99
    assert torch.equal(t2, expected)
    assert hook.artifact_store[key] == snapshot and hook.tapes[0].routed_experts_le_int32 == snapshot
    # 释放 hook / 叶引用后张量仍有效（bytearray 由 PyTorch 持有）
    del hook, leaf1, used
    gc.collect()
    assert int(t1[0, 0, 0]) == -99 and torch.equal(t1[1:], expected[1:])


def test_backfill_without_moe_config_still_delivers_the_flat_list():
    flat = routing_flat(4, LAYERS, TOPK)
    hook = _hook("flat")
    hook.on_generate_response(
        prompt_token_ids=[1, 2, 3], sampling_params=SP, response=_response(b64_int32(flat), gen=[5, 6])
    )
    leaf = _leaf([1, 2, 3, 5, 6], 2)
    backfill_leaf_sample(leaf, hook.tapes)
    assert isinstance(leaf.rollout_routed_experts, list) and leaf.rollout_routed_experts == flat


def test_shape_routing_experts_empty_payload_big_endian_and_no_torch_fallbacks(monkeypatch):
    torch = pytest.importorskip("torch")
    payload = _packed(list(range(8)))
    expected = torch.arange(8, dtype=torch.int32).reshape(2, LAYERS, TOPK)
    empty = G._shape_routing_experts(b"", rows=0, layers=LAYERS, topk=TOPK)
    assert tuple(empty.shape) == (0, LAYERS, TOPK) and empty.dtype == torch.int32
    monkeypatch.setattr(sys, "byteorder", "big")  # 非小端主机：旧的 torch.tensor(list) 构造
    assert torch.equal(G._shape_routing_experts(payload, rows=2, layers=LAYERS, topk=TOPK), expected)
    monkeypatch.setitem(sys.modules, "torch", None)  # 无 torch：等价嵌套 list
    assert G._shape_routing_experts(payload, rows=2, layers=LAYERS, topk=TOPK) == [[[0, 1], [2, 3]], [[4, 5], [6, 7]]]
