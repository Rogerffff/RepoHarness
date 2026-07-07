"""S0-6 top-p 动态探针（对应执行计划第 3 条：必须显式 top_p<1.0 防假阴性）。

目的：
1. 在 top_p=0.95、temperature=1.0 下，向 SGLang /generate 发 slime 风格请求：
   input_ids 进、return_logprob=True、return_routed_experts=True、
   sampling_params.custom_params={"return_top_p_token_ids": True}
   （slime/rollout/sglang_rollout.py:108 在 rollout_top_p != 1.0 时就是这样发的）。
2. 记录 meta_info 的完整 key 列表与形状，检查 slime utils/types.py:9-10 期望的
   top_p_token_ids / top_p_kept_token_ids / top_p_token_offsets / top_p_kept_token_offsets
   是否存在。
3. 对照组：同参数但不带 custom_params，确认 stock SGLang 对未知 custom_params 的行为。
4. 顺带验证 top_p=0.95 时 routed_experts tape 仍返回、形状可解析、与生成 token 数对齐。
"""

import base64
import json
import time
from pathlib import Path

import numpy as np
import requests
from transformers import AutoTokenizer

OUT = Path("/workspace/s0_topp_probe/sglang_qwen3_30b_topp_probe.json")
BASE = "http://127.0.0.1:30000"
MODEL = "Qwen/Qwen3-30B-A3B"
NUM_LAYERS, TOP_K = 48, 8  # Qwen3-30B-A3B: 48 层 MoE，每 token 激活 8 个专家

tok = AutoTokenizer.from_pretrained(MODEL, cache_dir="/workspace/hf_cache")
messages = [{"role": "user", "content": "Name three colors, comma separated."}]
input_ids = tok.apply_chat_template(messages, tokenize=True, add_generation_prompt=True)

SLIME_TOP_P_ID_KEYS = ("top_p_token_ids", "top_p_kept_token_ids")
SLIME_TOP_P_OFFSET_KEYS = ("top_p_token_offsets", "top_p_kept_token_offsets")


def summarize(v, depth=0):
    if depth > 4:
        return {"type": type(v).__name__}
    if isinstance(v, dict):
        return {
            "type": "dict",
            "keys": sorted(v.keys()),
            "items": {k: summarize(val, depth + 1) for k, val in list(v.items())[:30]},
        }
    if isinstance(v, list):
        return {"type": "list", "len": len(v), "first": summarize(v[0], depth + 1) if v else None}
    if isinstance(v, str):
        return {"type": "str", "len": len(v), "preview": v[:120]}
    return {"type": type(v).__name__, "repr": repr(v)[:160]}


def decode_routing(routing):
    info = {"present": routing is not None, "type": type(routing).__name__}
    if isinstance(routing, str):
        raw = base64.b64decode(routing.encode("utf-8"))
        arr = np.frombuffer(raw, dtype=np.int32)
        rows = arr.size // (NUM_LAYERS * TOP_K) if arr.size % (NUM_LAYERS * TOP_K) == 0 else None
        info.update(
            base64_len=len(routing),
            raw_bytes=len(raw),
            flat_int32_count=int(arr.size),
            inferred_shape_if_48x8=[rows, NUM_LAYERS, TOP_K] if rows is not None else None,
            expert_id_min=int(arr.min()) if arr.size else None,
            expert_id_max=int(arr.max()) if arr.size else None,
            preview_first_token_first_layer=arr[:TOP_K].tolist(),
        )
    elif isinstance(routing, list):
        info["list_shape_guess"] = summarize(routing)
    return info


def run_case(name, with_custom_params):
    sampling = {
        "max_new_tokens": 16,
        "temperature": 1.0,
        "top_p": 0.95,  # 计划明确要求 top_p < 1.0，避免"截断候选集为空"的假阴性
    }
    if with_custom_params:
        sampling["custom_params"] = {"return_top_p_token_ids": True}
    req = {
        "input_ids": input_ids,
        "sampling_params": sampling,
        "return_logprob": True,
        "return_text_in_logprobs": False,
        "logprob_start_len": len(input_ids),
        "return_routed_experts": True,
    }
    started = time.time()
    r = requests.post(f"{BASE}/generate", json=req, timeout=300)
    elapsed = time.time() - started
    try:
        data = r.json()
    except Exception:
        data = {"raw_text": r.text[:2000]}
    meta = data.get("meta_info") if isinstance(data, dict) else None
    case = {
        "name": name,
        "request_sampling_params": sampling,
        "ok": r.ok,
        "status_code": r.status_code,
        "elapsed_seconds": round(elapsed, 3),
    }
    if not r.ok:
        case["error_body"] = r.text[:2000]
        return case
    otl = meta.get("output_token_logprobs") if isinstance(meta, dict) else None
    gen_tokens = [item[1] for item in otl] if otl else []
    case.update(
        completion_text_preview=(data.get("text") or "")[:200],
        meta_info_keys=sorted(meta.keys()) if isinstance(meta, dict) else None,
        top_p_related_keys={
            "id_keys_found": [k for k in SLIME_TOP_P_ID_KEYS if isinstance(meta, dict) and k in meta],
            "offset_keys_found": [k for k in SLIME_TOP_P_OFFSET_KEYS if isinstance(meta, dict) and k in meta],
            "any_key_containing_top_p": sorted(
                k for k in (meta.keys() if isinstance(meta, dict) else []) if "top_p" in k
            ),
        },
        output_token_logprobs_summary={
            "present": otl is not None,
            "num_entries": len(otl) if otl else 0,
            "entry_shape_example": summarize(otl[0]) if otl else None,
            "completion_tokens_in_meta": meta.get("completion_tokens") if isinstance(meta, dict) else None,
            "logprob_values_finite": bool(otl) and all(np.isfinite(item[0]) for item in otl),
        },
        generated_token_ids=gen_tokens,
        routed_experts=decode_routing(meta.get("routed_experts") if isinstance(meta, dict) else None),
        meta_info_summary=summarize(meta),
    )
    if case["routed_experts"].get("inferred_shape_if_48x8"):
        rows = case["routed_experts"]["inferred_shape_if_48x8"][0]
        case["routing_rows_vs_generated_tokens"] = {
            "routing_rows": rows,
            "generated_tokens": len(gen_tokens),
            "aligned_or_off_by_one": rows in (len(gen_tokens), len(gen_tokens) + 1, len(gen_tokens) - 1),
        }
    return case


server_info = {}
try:
    si = requests.get(f"{BASE}/get_server_info", timeout=30).json()
    server_info = {
        k: si.get(k)
        for k in ("version", "model_path", "enable_return_routed_experts", "sampling_backend", "attention_backend")
        if isinstance(si, dict)
    }
    # 有些版本把 server_args 嵌套存放
    if isinstance(si, dict) and not server_info.get("version"):
        server_info["raw_keys"] = sorted(si.keys())[:40]
        server_info["version"] = si.get("version")
except Exception as e:  # noqa: BLE001
    server_info = {"error": repr(e)[:200]}

result = {
    "probe": "s0-6 top-p dynamic probe (slime-style request against stock SGLang)",
    "date": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
    "model": MODEL,
    "sglang_package": "stock PyPI sglang (see pip_show in this file)",
    "server_launch_flags": [
        "--enable-return-routed-experts",
        "--sampling-backend pytorch",
        "--moe-runner-backend triton",
        "--attention-backend triton",
        "--disable-cuda-graph",
    ],
    "server_info": server_info,
    "prompt_len": len(input_ids),
    "cases": [
        run_case("slime_style_with_custom_params_top_p_0.95", True),
        run_case("control_no_custom_params_top_p_0.95", False),
    ],
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False))
print(json.dumps(result, indent=2, ensure_ascii=False)[:4000])
print("\nSAVED:", OUT)
