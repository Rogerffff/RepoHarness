"""E3 计划边界探针：真实旧函数 + Brief 的局部表示草图；不是生产实现验收。"""

from __future__ import annotations

import array
import base64
import gc
import hashlib
import json
import struct
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch
from repoharness2.adapters.slime import generate as g
from repoharness2.adapters.slime import projection as p


def old_payload(value):
    return p._int32_bytes(p.decode_int32_tape(value, field_name="probe"), "probe")


def brief_bytes_sketch(value):
    """逐字落实 Brief 对 bytes-like 直接返回的提议，显式包含 memoryview。"""
    if isinstance(value, str):
        value = base64.b64decode(value.encode("ascii"), validate=True)
    if isinstance(value, (bytes, bytearray, memoryview)):
        raw = bytes(value)
        if len(raw) % 4:
            raise p.SlimeProjectionError("tape_bytes_not_int32", "probe")
        return raw
    return old_payload(value)


def payload_result(fn, value):
    try:
        raw = fn(value)
        return {
            "values": list(struct.unpack(f"<{len(raw) // 4}i", raw)),
            "byte_size": len(raw),
        }
    except Exception as exc:  # noqa: BLE001 - 记录旧函数与草图的异常，不用于生产处置
        return {"exception": type(exc).__name__, "reason": getattr(exc, "reason_code", None)}


def project_result(value):
    try:
        ref = p._build_routing(
            SimpleNamespace(rollout_routed_experts=value),
            branch_id="b", trajectory_id="probe", prompt_len=2, response_len=1,
            engine_name="sglang", tape_requested=True, moe_num_layers=2,
            moe_router_topk=2, store={},
        )
        return {"rows": ref.num_rows, "sha256": ref.tensor_ref.sha256}
    except Exception as exc:  # noqa: BLE001 - 保留真实旧函数的反例结果
        return {"exception": type(exc).__name__, "reason": getattr(exc, "reason_code", None)}


raw = struct.pack("<i", 1)
forms = {
    "bytes": raw,
    "bytearray": bytearray(raw),
    "base64": base64.b64encode(raw).decode("ascii"),
    "memoryview_bytes": memoryview(raw),
    "memoryview_int32": memoryview(array.array("i", [1])),
    "memoryview_float32": memoryview(array.array("f", [1.0])),
}
forms_result = {
    name: {"old": payload_result(old_payload, value), "brief_sketch": payload_result(brief_bytes_sketch, value)}
    for name, value in forms.items()
}
assert forms_result["bytes"]["old"] == forms_result["bytes"]["brief_sketch"]
assert forms_result["memoryview_bytes"]["old"]["values"] == [1, 0, 0, 0]
assert forms_result["memoryview_bytes"]["brief_sketch"]["values"] == [1]

small = torch.arange(8, dtype=torch.int32).reshape(2, 2, 2)
large_i64 = small.to(torch.int64)
large_i64[0, 0, 0] = 2**31
projection_cases = {
    "int32": small,
    "int64_in_range": small.to(torch.int64),
    "int64_overflow": large_i64,
    "float32": small.to(torch.float32),
    "bool": small.to(torch.bool),
    "config_shape_mismatch": torch.arange(12, dtype=torch.int32).reshape(2, 3, 2),
}
projection_result = {name: project_result(value) for name, value in projection_cases.items()}
assert projection_result["int32"] == projection_result["int64_in_range"]
assert projection_result["config_shape_mismatch"]["reason"] == "routing_shape_mismatch"

hook = g.GenerationCaptureHook(
    trajectory_id="probe", model_name="m", backend_name="sglang", backend_version="v",
    renderer_cls_name="r", tokenizer_name="t", template_hash="sha256:" + "0" * 64,
)
try:
    hook.on_generate_response(
        prompt_token_ids=[10, 11],
        sampling_params={"temperature": 1.0, "top_p": 1.0, "max_new_tokens": 1,
                         "return_top_p_token_ids": False, "return_routed_experts": True},
        response={"text": "x", "meta_info": {"id": "rid", "weight_version": "1",
                  "output_token_logprobs": [[-0.1, 12, None]], "routed_experts": [2**31]}},
    )
except Exception as exc:  # noqa: BLE001 - 捕获与投影本来就有不同的错误包装
    capture_overflow = {"exception": type(exc).__name__, "reason": getattr(exc, "reason_code", None)}
else:
    raise AssertionError("old capture unexpectedly accepted an out-of-range int")
assert capture_overflow == {"exception": "error", "reason": None}

array_cases = {
    "int32_edges": np.array([-(2**31), -1, 0, 1, 127, 128, 256, 2**31 - 1], dtype=np.int32).reshape(2, 2, 2),
    "noncontiguous": np.arange(16, dtype=np.int32).reshape(2, 2, 4)[:, :, ::2],
    "big_endian_array": np.arange(8, dtype=">i4").reshape(2, 2, 2),
}
array_result = {}
for name, value in array_cases.items():
    flat, rows, layers, topk = p._routing_flat_and_dims(value, branch_id="b", moe_num_layers=2, moe_router_topk=2)
    before = p._int32_bytes(flat, "probe")
    after = np.ascontiguousarray(value, dtype="<i4").tobytes()
    array_result[name] = {"equal": before == after, "shape": [rows, layers, topk]}
    assert before == after

artifact = struct.pack("<8i", *range(8))


def new_leaf():
    return torch.frombuffer(bytearray(artifact), dtype=torch.int32).reshape(2, 2, 2)


leaf1, leaf2 = new_leaf(), new_leaf()
gc.collect()
leaf1[0, 0, 0] = -99
ownership = {
    "artifact_unchanged": artifact == struct.pack("<8i", *range(8)),
    "other_leaf_unchanged": int(leaf2[0, 0, 0]) == 0,
    "tensor_valid_after_local_buffer_scope": leaf1.flatten().tolist() == [-99, 1, 2, 3, 4, 5, 6, 7],
}
assert all(ownership.values())
print(json.dumps({
    "python": sys.version.split()[0], "torch": torch.__version__, "numpy": np.__version__,
    "byteorder": sys.byteorder,
    "projection_source_sha256": hashlib.sha256(Path(p.__file__).read_bytes()).hexdigest(),
    "decode_forms": forms_result, "old_projection": projection_result,
    "old_capture_overflow": capture_overflow,
    "array_bytes": array_result, "buffer_ownership": ownership,
    "scope": "CPU 小载荷；草图未装入 RH2。非生产 memoryview 反例不等于已发生训练污染。",
}, ensure_ascii=False, indent=2))
