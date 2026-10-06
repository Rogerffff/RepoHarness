"""只读复核真实 CC 请求：工具/记忆差异、400 探针的真实输入长度与正式溢出实现。

从 rh2/ 用本地 .venv/bin/python 运行；tokenizer 仅读本地，不下载。
stdout 是新证据，调用方写到本审查目录，不覆盖作者产物。
"""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import logging
from pathlib import Path
from types import SimpleNamespace

from transformers import AutoTokenizer

from slime.agent.adapters import common
from slime.agent.adapters.anthropic import (
    _fold_mid_list_system_into_user,
    _tools_to_chat_tools,
    _translate_messages,
)


ROOT = next(p for p in Path(__file__).resolve().parents if (p / "rh2/src").is_dir())
DATA = ROOT / "runs/decision_package_20260924/p8_9_10/remote"


def load(run: str, index: int = 0) -> dict:
    return json.loads((DATA / run / "stub/requests" / f"messages_{index:03}.json").read_text())


def token_count(body: dict, tokenizer) -> int:
    body = copy.deepcopy(body)
    _fold_mid_list_system_into_user(body)
    return len(common._render_token_ids(
        _translate_messages(body.get("messages", []), body.get("system")), tokenizer,
        tools=_tools_to_chat_tools(body.get("tools")), add_generation_prompt=True,
    ))


def flatten(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(flatten(x) for x in value)
    if isinstance(value, dict):
        return flatten(value.get("text", value.get("content", "")))
    return ""


async def production_overflow() -> dict:
    from repoharness2.adapters.slime.capture_wire import CaptureRegistry, install_capture_wire

    registry = CaptureRegistry()
    install_capture_wire(registry)
    adapter = SimpleNamespace(logger=logging.getLogger("review"), max_token_keys=("max_tokens",),
                              stop_keys=("stop_sequences",), sglang_url="http://unused")
    result = await common.call_sglang_generate(
        list(range(33)), common.Session(max_context_tokens=32, sampling_defaults={"max_new_tokens": 8}),
        {"max_tokens": 8}, adapter=adapter, session_id="review-overflow",
    )
    return {"callable_module": common.call_sglang_generate.__module__,
            "callable_qualname": common.call_sglang_generate.__qualname__,
            "scope": "actual installed function; 33 prompt tokens / 32 limit; no engine network call",
            "finish_reason": result.finish_reason, "output_ids": result.output_ids,
            "registry_pending": len(registry.pending)}


async def main() -> None:
    names = ["dp_t10_base", "dp_t10_toolscore", "dp_t10_denyskill", "dp_m9_env"]
    bodies = {name: load(name) for name in names}
    summaries = {}
    for name, body in bodies.items():
        summaries[name] = {
            "tool_names": [t["name"] for t in body["tools"]],
            "has_memory_section": "# Memory" in flatten(body.get("system")),
            "has_skill_listing": any("The following skills are available" in flatten(m.get("content"))
                                     for m in body["messages"]),
        }
    failed, compact = load("dp_c8_reactive", 2), load("dp_c8_reactive", 3)
    counts = {}
    models = {
        "Qwen3-30B-A3B_proxy": "Qwen/Qwen3-30B-A3B",
        "Qwen3.6-35B-A3B_pinned": str(ROOT / "runs/decision_package_20260924/p6_thinking/hf_tokenizer"),
    }
    for name, path in models.items():
        tok = AutoTokenizer.from_pretrained(path, local_files_only=True)
        counts[name] = {
            "template_sha256": hashlib.sha256(tok.chat_template.encode()).hexdigest(),
            "first_requests": {k: token_count(v, tok) for k, v in bodies.items()},
            "reactive_probe": {
                "rejected_prompt_tokens": token_count(failed, tok),
                "compact_prompt_tokens": token_count(compact, tok),
                "claimed_error": "prompt is too long: 40000 tokens > 32768 maximum",
                "actual_guard_limit_used_by_stub": None,
            },
        }
    result = {"scope": "local token replay and installed capture function; no new real CC/GPU run",
              "input_facts": summaries, "counts": counts,
              "production_overflow": await production_overflow()}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
