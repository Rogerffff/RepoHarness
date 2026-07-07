"""S1-0 U-H probe for slime's patched SGLang image on Blackwell.

The probe sends a slime-style /generate request with top_p < 1.0 and asks the
server to return both top-p replay tape and routed experts.  It records enough
shape information to decide whether the image can be used as the S1/S4 shape-B
rollout serving base.
"""

from __future__ import annotations

import base64
import json
import os
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
import requests
from transformers import AutoTokenizer


OUT = Path(os.environ.get("RH2_S1_0_PROBE_OUT", "/workspace/rh2_s1_0/sglang_qwen3_30b_topp_probe.json"))
BASE = os.environ.get("SGLANG_BASE", "http://127.0.0.1:30000")
MODEL = os.environ.get("RH2_S1_0_MODEL", "Qwen/Qwen3-30B-A3B")
HF_CACHE = os.environ.get("HF_HOME", "/workspace/hf_cache")
NUM_LAYERS = 48
TOP_K = 8

SLIME_TOP_P_ID_KEYS = ("top_p_token_ids", "top_p_kept_token_ids")
SLIME_TOP_P_OFFSET_KEYS = ("top_p_token_offsets", "top_p_kept_token_offsets")


def summarize(value: Any, depth: int = 0) -> dict[str, Any]:
    if depth > 4:
        return {"type": type(value).__name__}
    if isinstance(value, dict):
        return {
            "type": "dict",
            "keys": sorted(value.keys()),
            "items": {k: summarize(v, depth + 1) for k, v in list(value.items())[:30]},
        }
    if isinstance(value, list):
        return {"type": "list", "len": len(value), "first": summarize(value[0], depth + 1) if value else None}
    if isinstance(value, str):
        return {"type": "str", "len": len(value), "preview": value[:120]}
    return {"type": type(value).__name__, "repr": repr(value)[:160]}


def decode_int32_payload(value: Any) -> dict[str, Any]:
    info: dict[str, Any] = {"present": value is not None, "type": type(value).__name__}
    if value is None:
        return info
    if isinstance(value, str):
        raw = base64.b64decode(value.encode("utf-8"))
        arr = np.frombuffer(raw, dtype=np.int32)
        info.update(
            encoding="base64_int32",
            base64_len=len(value),
            raw_bytes=len(raw),
            int32_count=int(arr.size),
            min=int(arr.min()) if arr.size else None,
            max=int(arr.max()) if arr.size else None,
            preview=arr[:16].tolist(),
        )
        return info
    if isinstance(value, list):
        arr = np.asarray(value, dtype=np.int64).reshape(-1)
        info.update(
            encoding="list",
            int_count=int(arr.size),
            min=int(arr.min()) if arr.size else None,
            max=int(arr.max()) if arr.size else None,
            preview=arr[:16].tolist(),
        )
        return info
    info["summary"] = summarize(value)
    return info


def decode_routing(value: Any, *, prompt_len: int, generated_len: int) -> dict[str, Any]:
    info = decode_int32_payload(value)
    count = info.get("int32_count") or info.get("int_count")
    if not count or count % (NUM_LAYERS * TOP_K) != 0:
        info["shape_status"] = "absent_or_not_48x8"
        return info
    rows = int(count // (NUM_LAYERS * TOP_K))
    expected_rows = {
        "completion_only": generated_len,
        "completion_off_by_one_minus": max(generated_len - 1, 0),
        "completion_off_by_one_plus": generated_len + 1,
        "prompt_minus_one_plus_completion": max(prompt_len - 1, 0) + generated_len,
        "prompt_plus_completion": prompt_len + generated_len,
    }
    info.update(
        inferred_shape_if_48x8=[rows, NUM_LAYERS, TOP_K],
        expected_rows=expected_rows,
        row_match_labels=[name for name, expected in expected_rows.items() if expected == rows],
        shape_status="valid_48x8" if rows > 0 else "empty_48x8",
    )
    return info


def decode_top_p(meta: dict[str, Any], *, generated_len: int) -> dict[str, Any]:
    id_key = next((key for key in SLIME_TOP_P_ID_KEYS if key in meta), None)
    offset_key = next((key for key in SLIME_TOP_P_OFFSET_KEYS if key in meta), None)
    ids = decode_int32_payload(meta.get(id_key)) if id_key else {"present": False}
    offsets = decode_int32_payload(meta.get(offset_key)) if offset_key else {"present": False}
    offset_values: list[int] | None = None
    if offset_key and isinstance(meta.get(offset_key), str):
        offset_values = np.frombuffer(base64.b64decode(meta[offset_key].encode("utf-8")), dtype=np.int32).astype(int).tolist()
    elif offset_key and isinstance(meta.get(offset_key), list):
        offset_values = [int(x) for x in meta[offset_key]]
    ids_count = ids.get("int32_count") or ids.get("int_count")
    offsets_count = offsets.get("int32_count") or offsets.get("int_count")
    return {
        "id_key": id_key,
        "offset_key": offset_key,
        "id_payload": ids,
        "offset_payload": offsets,
        "offsets_len_equals_generated_plus_one": offsets_count == generated_len + 1,
        "offsets_monotonic": bool(offset_values) and all(a <= b for a, b in zip(offset_values, offset_values[1:])),
        "offsets_last": offset_values[-1] if offset_values else None,
        "ids_cover_offsets_last": bool(offset_values) and ids_count is not None and ids_count >= offset_values[-1],
    }


def run_case(name: str, *, with_custom_params: bool, input_ids: list[int]) -> dict[str, Any]:
    sampling: dict[str, Any] = {
        "max_new_tokens": 16,
        "temperature": 1.0,
        "top_p": 0.95,
    }
    if with_custom_params:
        sampling["custom_params"] = {"return_top_p_token_ids": True}
    request = {
        "input_ids": input_ids,
        "sampling_params": sampling,
        "return_logprob": True,
        "return_text_in_logprobs": False,
        "logprob_start_len": len(input_ids),
        "return_routed_experts": True,
    }
    started = time.time()
    response = requests.post(f"{BASE}/generate", json=request, timeout=300)
    elapsed = time.time() - started
    try:
        data = response.json()
    except Exception:
        data = {"raw_text": response.text[:4000]}
    case: dict[str, Any] = {
        "name": name,
        "ok": response.ok,
        "status_code": response.status_code,
        "elapsed_seconds": round(elapsed, 3),
        "request_sampling_params": sampling,
    }
    if not response.ok or not isinstance(data, dict):
        case["response_preview"] = response.text[:4000]
        return case
    meta = data.get("meta_info") if isinstance(data.get("meta_info"), dict) else {}
    output_logprobs = meta.get("output_token_logprobs")
    generated_ids = [item[1] for item in output_logprobs] if output_logprobs else []
    case.update(
        text_preview=(data.get("text") or "")[:240],
        meta_info_keys=sorted(meta.keys()),
        keys_containing_top_p=sorted(key for key in meta if "top_p" in key),
        output_token_logprobs={
            "present": output_logprobs is not None,
            "num_entries": len(output_logprobs) if output_logprobs else 0,
            "finite": bool(output_logprobs) and all(np.isfinite(item[0]) for item in output_logprobs),
            "entry_example": summarize(output_logprobs[0]) if output_logprobs else None,
            "completion_tokens_in_meta": meta.get("completion_tokens"),
        },
        generated_token_ids=generated_ids,
        top_p=decode_top_p(meta, generated_len=len(generated_ids)),
        routed_experts=decode_routing(meta.get("routed_experts"), prompt_len=len(input_ids), generated_len=len(generated_ids)),
        meta_info_summary=summarize(meta),
    )
    case["pass_criteria"] = {
        "logprobs_present_and_finite": case["output_token_logprobs"]["present"] and case["output_token_logprobs"]["finite"],
        "top_p_ids_present": bool(case["top_p"]["id_key"]),
        "top_p_offsets_present": bool(case["top_p"]["offset_key"]),
        "top_p_offsets_len_ok": case["top_p"]["offsets_len_equals_generated_plus_one"],
        "top_p_offsets_monotonic": case["top_p"]["offsets_monotonic"],
        "routing_present": case["routed_experts"]["present"],
        "routing_shape_valid": case["routed_experts"].get("shape_status") == "valid_48x8",
        "routing_row_match_known_semantics": bool(case["routed_experts"].get("row_match_labels")),
    }
    case["case_pass"] = all(case["pass_criteria"].values()) if with_custom_params else response.ok
    return case


def main() -> None:
    tokenizer = AutoTokenizer.from_pretrained(MODEL, cache_dir=HF_CACHE)
    messages = [{"role": "user", "content": "Name three colors, comma separated."}]
    rendered = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True)
    if isinstance(rendered, Mapping):
        rendered = rendered["input_ids"]
    elif hasattr(rendered, "data") and isinstance(rendered.data, Mapping) and "input_ids" in rendered.data:
        rendered = rendered.data["input_ids"]
    if hasattr(rendered, "tolist"):
        rendered = rendered.tolist()
    if rendered and isinstance(rendered[0], list):
        rendered = rendered[0]
    input_ids = [int(token_id) for token_id in rendered]
    server_info: dict[str, Any]
    try:
        server_info = requests.get(f"{BASE}/get_server_info", timeout=30).json()
    except Exception as exc:  # noqa: BLE001
        server_info = {"error": repr(exc)}
    result = {
        "probe": "rh2_s1_0_u_h_slime_patched_sglang_top_p_and_routing",
        "date_utc": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "base_url": BASE,
        "model": MODEL,
        "prompt_len": len(input_ids),
        "server_info_subset": {
            key: server_info.get(key)
            for key in (
                "model_path",
                "dtype",
                "device",
                "sampling_backend",
                "attention_backend",
                "moe_runner_backend",
                "enable_return_routed_experts",
                "max_total_tokens",
                "mem_fraction_static",
            )
        },
        "cases": [
            run_case("slime_style_custom_params_top_p_0_95", with_custom_params=True, input_ids=input_ids),
            run_case("control_no_custom_params_top_p_0_95", with_custom_params=False, input_ids=input_ids),
        ],
    }
    main_case = result["cases"][0]
    result["overall_pass"] = bool(main_case.get("case_pass"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(json.dumps(result, indent=2, ensure_ascii=False)[:6000])
    print("\nSAVED:", OUT)


if __name__ == "__main__":
    main()
