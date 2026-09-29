"""本地 CPU 独立复核：真实 tokenizer + 生产子类/计数/溢出路由。

不运行模型或 CC，不修改已有证据。默认打印；--out 只创建新文件。
生成请求的测试容量固定为 1，验证 400 出现在采样与 pending 之前。
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import json
import os
import sys
from pathlib import Path

REPO = next(
    p for p in Path(__file__).resolve().parents
    if (p / "rh2/src/slime/agent/adapters/common.py").is_file()
)


async def run() -> dict:
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    sys.path.insert(0, str(REPO / "rh2/src"))
    from aiohttp.test_utils import TestClient, TestServer
    from repoharness2.adapters.slime import capture_wire as cw
    from repoharness2.adapters.slime.count_tokens_wire import (
        bind_count_tokens_adapter,
        install_count_tokens_wire,
    )
    from repoharness2.adapters.slime.rh2_anthropic_adapter import (
        rh2_anthropic_adapter_cls,
    )
    from repoharness2.adapters.slime.session_capability import mint_session_capability
    from slime.agent.adapters.common import _render_token_ids
    from transformers import AutoTokenizer

    p6 = REPO / "runs/decision_package_20260924/p6_thinking"
    tok = AutoTokenizer.from_pretrained(
        str(p6 / "hf_tokenizer"), local_files_only=True, trust_remote_code=False
    )
    gateway = REPO / "runs/base_probe_20260922/remote/gateway/q36"
    source = gateway / "bp22-qwen3-6-35b-a3b-dask-8597-a2/requests.jsonl"
    rows = [json.loads(line) for line in source.read_text().splitlines()]
    reminder_body = next(r["body"] for r in rows if r.get("seq") == 16)
    compact_path = REPO / (
        "runs/decision_package_20260924/p8_9_10/remote/"
        "dp_c8_reactive/stub/requests/messages_003.json"
    )
    compact_body = json.loads(compact_path.read_text())

    registry = cw.CaptureRegistry()
    cw.install_capture_wire(registry)
    install_count_tokens_wire()
    adapter = rh2_anthropic_adapter_cls()(
        tokenizer=tok, sglang_url="http://127.0.0.1:9", max_turns_per_sid=10
    )
    bind_count_tokens_adapter(adapter)
    adapter.app.middlewares.append(cw.build_session_guard_middleware(registry))

    class Hook:
        def __init__(self):
            self.records: list = []

    cap = mint_session_capability("falsifier_conditions#p1-cpu")
    sid = "s-falsifier_conditions#p1-cpu"
    hook = Hook()
    registry.register(sid, hook, physical_attempt_id="falsifier_conditions#p1-cpu", capability_token=cap.token)
    adapter.open_session(sid, sampling_defaults={"max_new_tokens": 16}, max_context_tokens=1)
    client = TestClient(TestServer(adapter.app))
    await client.start_server()
    hdr = {"Authorization": f"Bearer {cap.token}"}
    result = {"test_max_context_tokens": 1, "cases": {}}
    try:
        for name, body in (("real_file_reminder", reminder_body), ("real_compaction_instruction", compact_body)):
            translated_body = copy.deepcopy(body)
            adapter._preprocess_body(translated_body)
            once = copy.deepcopy(translated_body)
            adapter._preprocess_body(translated_body)
            translated, tools = adapter._translate(translated_body)
            ids = _render_token_ids(translated, tok, tools=tools, add_generation_prompt=True)
            response = await client.post("/v1/messages/count_tokens", json=body, headers=hdr)
            count = await response.json()
            snap_after_count = registry.turn_budget_snapshot(sid)
            sent = copy.deepcopy(body)
            sent["stream"] = True
            generated = await client.post("/v1/messages", json=sent, headers=hdr)
            error = await generated.json()
            roles = [
                m["role"] for m in translated
                if "CRITICAL: Respond with TEXT ONLY" in str(m.get("content", ""))
            ]
            result["cases"][name] = {
                "preprocess_idempotent": translated_body == once,
                "count_status": response.status,
                "count_tokens": count.get("input_tokens"),
                "generation_render_tokens": len(ids),
                "accepted_after_count": None if snap_after_count is None else snap_after_count["accepted"],
                "generation_status": generated.status,
                "generation_content_type": generated.content_type,
                "generation_error": error,
                "compaction_instruction_roles": roles,
            }
            assert translated_body == once
            assert response.status == 200 and count["input_tokens"] == len(ids)
            assert generated.status == 400 and str(len(ids)) in error["error"]["message"]
            if name == "real_compaction_instruction":
                assert roles == ["user"]
        result["capture_records"] = len(hook.records)
        result["poisoned"] = registry.poison.is_poisoned(sid)
        result["overflow_count"] = registry.stats.get("prompt_too_long")
        result["final_turn_budget"] = registry.turn_budget_snapshot(sid)
    finally:
        await client.close()
        drain = await registry.drain_session_plane(sid)
        result["drain"] = {
            "pending_turns": drain.pending_turns,
            "unfinalized_drafts": drain.unfinalized_drafts,
            "inflight_zero_confirmed": drain.inflight_zero_confirmed,
            "poison_clean": drain.poison_clean,
        }
        registry.unregister(sid)
    assert result["capture_records"] == 0 and not result["poisoned"]
    assert result["overflow_count"] == 2
    assert drain.pending_turns == drain.unfinalized_drafts == 0

    acceptance = json.loads((p6 / "smoosh_acceptance.json").read_text())
    included = []
    for path in sorted(gateway.glob("*/requests.jsonl")):
        data = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        included.append({
            "attempt": path.parent.name, "rows": len(data),
            "non_generation_paths": [r.get("path") for r in data if r.get("seq") is None],
        })
    result["acceptance_denominators"] = {
        "reported_pairs": acceptance["pairs"],
        "reported_attempts": acceptance["attempts"],
        "body_rows": sum(x["rows"] for x in included),
        "non_generation_rows": [x for x in included if x["non_generation_paths"]],
        "single_row_files": [x for x in included if x["rows"] == 1],
        "note": "Acceptance compares prompt prefixes; it does not export training identity spans.",
    }
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    text = json.dumps(asyncio.run(run()), ensure_ascii=False, indent=2) + "\n"
    if args.out:
        with args.out.open("x") as handle:
            handle.write(text)
    else:
        print(text, end="")
