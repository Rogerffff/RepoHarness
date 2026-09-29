"""E3 差分探针：同一固定场景，在旧树 / 新树各跑一次（独立进程），输出可 diff 的 JSON。

只调用两棵树都有的**生产入口**（capture hook、backfill_leaf_sample、_build_routing、canonicalize），
不碰 TurnTape 内部字段。用法：

    PYTHONPATH=<tree>/rh2/src RH2_MILES_PATH=<miles fork> .venv/bin/python differential_probe.py > <out>.json
    diff old.json new.json   # 期望：除 "tree" 字段外逐字节相同
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import struct
import sys
from datetime import datetime, timezone
from types import SimpleNamespace

miles_path = os.environ.get("RH2_MILES_PATH")
if miles_path and miles_path not in sys.path:
    sys.path.insert(0, miles_path)

from repoharness2.adapters.slime import generate as G  # noqa: E402
from repoharness2.adapters.slime import projection as P  # noqa: E402

LAYERS, TOPK = 2, 2
PER_ROW = LAYERS * TOPK
EDGE = [-(2**31), -1, 0, 1, 127, 128, 256, 2**31 - 1]
SP = {"temperature": 1.0, "top_p": 1.0, "max_new_tokens": 64, "return_top_p_token_ids": False,
      "return_routed_experts": True}
G._now_utc = lambda: datetime(2026, 9, 22, tzinfo=timezone.utc)  # 固定非输入事实（Codex §3.4）


def sha(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def values(rows: int) -> list[int]:
    return [(i * 13 + 7) % 128 for i in range(rows * PER_ROW)]


def packed(vals) -> bytes:
    return struct.pack(f"<{len(vals)}i", *vals)


def nested(flat, rows):
    return [[flat[r * PER_ROW + layer * TOPK: r * PER_ROW + layer * TOPK + TOPK] for layer in range(LAYERS)]
            for r in range(rows)]


def response(rid, gen, routed):
    return {"text": "x", "meta_info": {"id": rid, "weight_version": "1", "finish_reason": {"type": "stop"},
            "output_token_logprobs": [[-(i + 1) * 0.05, t, None] for i, t in enumerate(gen)],
            "routed_experts": routed}}


def tensor_facts(value):
    if hasattr(value, "detach"):
        arr = value.detach().cpu().contiguous().numpy()
        return {"kind": "tensor", "dtype": str(value.dtype), "shape": list(value.shape), "sha256": sha(arr.tobytes())}
    if isinstance(value, list) and value and isinstance(value[0], list):
        return {"kind": "nested", "sha256": sha(json.dumps(value).encode())}
    return {"kind": type(value).__name__, "sha256": sha(packed(value))}


def leaf(tokens, gen_len):
    return SimpleNamespace(tokens=list(tokens), loss_mask=[1] * gen_len, response_length=gen_len,
                           rollout_log_probs=[-(i + 1) * 0.05 for i in range(gen_len)], metadata={},
                           weight_versions=[], rollout_top_p_token_ids=None, rollout_top_p_token_offsets=None,
                           rollout_routed_experts=None)


def build_routing(value, *, prompt_len, response_len, store, layers=LAYERS, topk=TOPK):
    return P._build_routing(SimpleNamespace(rollout_routed_experts=value), branch_id="b0", trajectory_id="diff",
                            prompt_len=prompt_len, response_len=response_len, engine_name="sglang",
                            tape_requested=True, moe_num_layers=layers, moe_router_topk=topk, store=store)


def error_of(fn):
    try:
        fn()
    except Exception as exc:  # noqa: BLE001 - 记录类别与 reason_code 供差分
        return {"type": type(exc).__name__, "reason": getattr(exc, "reason_code", None)}
    return None


def main():
    out = {"tree": os.environ.get("PYTHONPATH", ""), "byteorder": sys.byteorder}
    hook = G.GenerationCaptureHook(trajectory_id="diff", model_name="Qwen/Qwen3-30B-A3B", backend_name="sglang",
                                   backend_version="0.5.13", renderer_cls_name="Qwen3Renderer",
                                   tokenizer_name="Qwen/Qwen3-30B-A3B", template_hash="sha256:" + "a" * 64)
    prompt0, gen0 = [1, 2, 3, 4], [101, 102, 103]
    prompt1, gen1 = prompt0 + gen0 + [201, 202], [301, 302]
    prompt2, gen2 = prompt1 + gen1 + [203], [401, 402, 403]
    turns = [(prompt0, gen0, "base64"), (prompt1, gen1, "nested"), (prompt2, gen2, "base64")]
    for i, (prompt, gen, form) in enumerate(turns):
        rows = len(prompt) - 1 + len(gen)
        vals = values(rows) if i != 2 else EDGE * (rows * PER_ROW // len(EDGE)) + values(rows)[: rows * PER_ROW % len(EDGE)]
        routed = base64.b64encode(packed(vals)).decode("ascii") if form == "base64" else nested(vals, rows)
        hook.on_generate_response(prompt_token_ids=prompt, sampling_params=SP, response=response(f"rid{i}", gen, routed))
    out["records"] = [r.model_dump(mode="json") for r in hook.records]
    out["store"] = {k: [sha(v), len(v)] for k, v in sorted(hook.artifact_store.items())}

    leaves = {"exact": (prompt2 + gen2, prompt2), "trimmed_2_rows": (prompt2[2:] + gen2, prompt2[2:])}
    out["backfill"], out["projection"], out["canonicalize"] = {}, {}, {}
    for name, (tokens, prompt) in leaves.items():
        s = leaf(tokens, len(gen2))
        used = G.backfill_leaf_sample(s, hook.tapes, moe_num_layers=LAYERS, moe_router_topk=TOPK)
        out["backfill"][name] = {"used": [t.record_id for t in used], "routing": tensor_facts(s.rollout_routed_experts),
                                 "metadata": s.metadata, "weight_versions": s.weight_versions}
        store = {}
        ref = build_routing(s.rollout_routed_experts, prompt_len=len(prompt), response_len=len(gen2), store=store)
        out["projection"][name] = {"ref": ref.model_dump(mode="json"), "store": {k: [sha(v), len(v)] for k, v in store.items()}}
        try:
            from repoharness2.adapters.miles.canonicalize import _convert_routed_experts

            arr = _convert_routed_experts(s.rollout_routed_experts, expected_rows=len(tokens) - 1,
                                          moe_num_layers=LAYERS, moe_router_topk=TOPK)
            out["canonicalize"][name] = {"dtype": str(arr.dtype), "shape": list(arr.shape), "sha256": sha(arr.tobytes()),
                                         "c_contiguous": bool(arr.flags.c_contiguous)}
        except Exception as exc:  # noqa: BLE001 - miles 不在路径时如实记录
            out["canonicalize"][name] = f"unavailable: {type(exc).__name__}: {exc}"[:200]
    s = leaf(prompt2 + gen2, len(gen2))
    G.backfill_leaf_sample(s, hook.tapes)
    out["backfill_no_config"] = tensor_facts(s.rollout_routed_experts)

    # 错误矩阵（Codex ER2）：只记类别与 reason_code
    import torch

    small = torch.tensor(EDGE * 2, dtype=torch.int32).reshape(4, LAYERS, TOPK)
    overflow = small.to(torch.int64)
    overflow[0, 0, 0] = 2**31
    matrix = {
        "int32_ok": (small, 3, 2, LAYERS, TOPK), "int64_in_range": (small.to(torch.int64), 3, 2, LAYERS, TOPK),
        "int64_overflow": (overflow, 3, 2, LAYERS, TOPK), "float32": (small.to(torch.float32), 3, 2, LAYERS, TOPK),
        "bool": (small.to(torch.bool), 3, 2, LAYERS, TOPK),
        "config_axis_mismatch": (torch.arange(24, dtype=torch.int32).reshape(4, 3, TOPK), 3, 2, LAYERS, TOPK),
        "rows_off_by_one": (small, 3, 3, LAYERS, TOPK), "overflow_and_rows_wrong": (overflow, 3, 3, LAYERS, TOPK),
        "flat_no_config": (base64.b64encode(packed(list(range(16)))).decode(), 3, 2, None, None),
        "numel_mismatch": (base64.b64encode(packed(list(range(15)))).decode(), 3, 2, LAYERS, TOPK),
        "bytes_not_int32": (b"\x00" * 15, 3, 2, LAYERS, TOPK), "empty": (torch.empty((0, LAYERS, TOPK), dtype=torch.int32), 1, 0, LAYERS, TOPK),
        "int32_1d": (torch.tensor(EDGE * 2, dtype=torch.int32), 3, 2, LAYERS, TOPK),
    }
    out["projection_matrix"] = {}
    for name, (value, pl, rl, layers, topk) in matrix.items():
        store = {}
        err = error_of(lambda: build_routing(value, prompt_len=pl, response_len=rl, store=store, layers=layers, topk=topk))
        out["projection_matrix"][name] = err or {"store": {k: [sha(v), len(v)] for k, v in store.items()}}
    out["hook_overflow_list"] = error_of(lambda: G.GenerationCaptureHook(
        trajectory_id="x", model_name="m", backend_name="sglang", backend_version="v", renderer_cls_name="r",
        tokenizer_name="t", template_hash="sha256:" + "0" * 64).on_generate_response(
        prompt_token_ids=[1, 2, 3], sampling_params=SP, response=response("r", [5, 6], [2**31] + values(4)[1:])))
    print(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
