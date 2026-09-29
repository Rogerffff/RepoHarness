"""#5 复核：真实 tokenizer、HTTP adapter、capture wire；引擎固定返回 ID。

从仓库根运行 rh2/.venv/bin/python 本文件。只读本地 tokenizer，不下载、不运行模型。
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "rh2/pyproject.toml").exists())
sys.path.insert(0, str(ROOT / "rh2/src"))

from aiohttp.test_utils import TestClient, TestServer
from transformers import AutoTokenizer

from repoharness2.adapters.slime import capture_wire as cw, parse_wire as pw
from repoharness2.adapters.slime.generate import GenerationCaptureHook
from repoharness2.adapters.slime.rh2_anthropic_adapter import rh2_anthropic_adapter_cls
from repoharness2.adapters.slime.session_capability import mint_session_capability


class Response:
    status = 200

    def __init__(self, payload):
        self.payload = payload

    async def __aenter__(self):
        await asyncio.sleep(0)  # 交错多个 session，不人工发布 terminal fact
        return self

    async def __aexit__(self, *args):
        return False

    async def json(self, **kwargs):
        return self.payload


class FakeAiohttp:
    class ClientError(Exception):
        pass

    def __init__(self, cases):
        self.cases = cases

    def ClientTimeout(self, **kwargs):
        return None

    def ClientSession(self, **kwargs):
        outer = self

        class Session:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            def post(self, url, json=None, headers=None):
                ids, finish = outer.cases[headers["X-SMG-Routing-Key"]]
                return Response({"meta_info": {
                    "id": json["rid"], "weight_version": "1",
                    "finish_reason": {"type": finish},
                    "output_token_logprobs": [[-0.2, token, None] for token in ids],
                }})

        return Session()


async def main():
    tokenizer = AutoTokenizer.from_pretrained(
        ROOT / "runs/decision_package_20260924/p6_thinking/hf_tokenizer", local_files_only=True,
    )
    encode = lambda text: tokenizer.encode(text, add_special_tokens=False)
    eos_id = tokenizer.eos_token_id
    literal_ids = encode("The token is ") + encode("<|im_") + encode("end|>")
    assert eos_id not in literal_ids
    call = '<tool_call>\n<function=Bash>\n<parameter=command>\necho ok\n</parameter>\n</function>\n</tool_call>'
    cases = {
        "true_eos": (encode("Finished.") + [eos_id], "stop"),
        "ordinary_literal_length": (literal_ids, "length"),
        "normal_text_with_tag": (encode("Use the literal tag <tool_call> in a parser test.") + [eos_id], "stop"),
        "one_good_one_dangling": (encode(call + "\n<tool_call>") + [eos_id], "stop"),
        "dangling_only": (encode("Starting a tool: <tool_call>") + [eos_id], "stop"),
        "normal_tool": (encode(call) + [eos_id], "stop"),
    }
    registry = cw.CaptureRegistry()
    cw.install_capture_wire(registry)
    pw.install_parse_wire(eos_token=tokenizer.eos_token, eos_token_id=eos_id)
    observations = {}

    def observed(sid, translated, tools, message, turn):
        observations[sid] = {"manager_message": message, "ill_formed": turn.ill_formed,
                             "output_ids_preserved": turn.output_ids == cases[sid][0],
                             "output_logprobs_preserved": turn.output_log_probs == [-0.2] * len(cases[sid][0])}

    adapter = rh2_anthropic_adapter_cls()(tokenizer=tokenizer, sglang_url="http://fake-engine",
                                       fork_threshold_tokens=0, debug_callback=observed)
    adapter.app.middlewares.append(cw.build_session_guard_middleware(registry))
    headers, hooks = {}, {}
    for sid in cases:
        physical = f"exec_{sid}#p1-test"
        cap = mint_session_capability(physical)
        hook = GenerationCaptureHook(trajectory_id=f"exec_{sid}", model_name="m", backend_name="sglang",
                                     backend_version="test", renderer_cls_name="r", tokenizer_name="local-q36",
                                     template_hash="sha256:" + "0" * 64)
        registry.register(sid, hook, physical_attempt_id=physical, capability_token=cap.token)
        adapter.open_session(sid)
        headers[sid] = {"Authorization": f"Bearer {cap.token}"}
        hooks[sid] = hook

    saved = cw.aiohttp
    cw.aiohttp = FakeAiohttp(cases)
    try:
        async with TestClient(TestServer(adapter.app)) as client:
            async def run(sid):
                response = await client.post("/v1/messages", headers=headers[sid], json={
                    "messages": [{"role": "user", "content": "Write a parser test."}],
                    "tools": [{"name": "Bash", "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}}}],
                    "max_tokens": 256,
                })
                assert response.status == 200, await response.text()
                data = await response.json()
                return sid, {"content": data["content"], "stop_reason": data["stop_reason"],
                             "captured_records": len(hooks[sid].records), **observations[sid]}

            results = dict(await asyncio.gather(*(run(sid) for sid in cases)))
        checks = {
            "real_eos_removed": results["true_eos"]["content"] == [{"type": "text", "text": "Finished."}],
            "ordinary_literal_preserved": results["ordinary_literal_length"]["content"] == [{"type": "text", "text": "The token is <|im_end|>"}],
            "prose_not_ill_formed": not results["normal_text_with_tag"]["ill_formed"],
            "mixed_dangling_detected": results["one_good_one_dangling"]["ill_formed"],
            "single_dangling_detected": results["dangling_only"]["ill_formed"],
            "normal_tool_not_ill_formed": not results["normal_tool"]["ill_formed"],
            "all_ids_and_logprobs_preserved": all(r["output_ids_preserved"] and r["output_logprobs_preserved"] for r in results.values()),
            "all_capture_records_committed_once": all(r["captured_records"] == 1 for r in results.values()),
            "production_publisher_present": pw.parse_wire_stats()["eos_fact_missing"] == 0,
        }
        for sid in cases:
            drained = await registry.drain_session_plane(sid)
            assert drained.pending_turns == 0 and drained.unfinalized_drafts == 0
            registry.unregister(sid)
        output = {"scope": "Real RH2 HTTP adapter/capture/parser + local Qwen3.6 tokenizer; fixed-ID engine stub; six concurrent sessions",
                  "eos_id": eos_id, "cases": results, "stats": pw.parse_wire_stats(), "checks": checks,
                  "all_checks_pass": all(checks.values())}
        Path(__file__).with_suffix(".json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({"checks": checks, "all_checks_pass": output["all_checks_pass"]}, ensure_ascii=False))
        assert output["all_checks_pass"]
    finally:
        cw.aiohttp = saved


if __name__ == "__main__":
    asyncio.run(main())
