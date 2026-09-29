"""真实 adapter HTTP/解析/record_turn；只有引擎返回固定 ID。不是模型发生率实验。

从仓库根运行：rh2/.venv/bin/python <本文件>。读取本地已有 Qwen3.6 tokenizer，禁止下载。
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT / "rh2/src"))

from aiohttp.test_utils import TestClient, TestServer
from transformers import AutoTokenizer

from repoharness2.adapters.slime import parse_wire
from repoharness2.adapters.slime.rh2_anthropic_adapter import rh2_anthropic_adapter_cls
from slime.agent import parsing
from slime.agent.adapters import common
from slime.agent.trajectory import TurnRecord


async def main():
    tokenizer = AutoTokenizer.from_pretrained(
        ROOT / "runs/decision_package_20260924/p6_thinking/hf_tokenizer",
        local_files_only=True,
    )
    encode = lambda s: tokenizer.encode(s, add_special_tokens=False)
    eos = tokenizer.eos_token
    # 合法的普通 token 序列也能拼出 EOS 的字面量；不含 eos_token_id。
    ordinary_literal = encode("The token is ") + encode("<|im_") + encode("end|>")
    assert tokenizer.eos_token_id not in ordinary_literal
    assert tokenizer.decode(ordinary_literal, skip_special_tokens=False).endswith(eos)
    valid_tool = '<tool_call>\n<function=Bash>\n<parameter=command>\necho ok\n</parameter>\n</function>\n</tool_call>'
    cases = {
        "true_eos": (encode("Finished.") + [tokenizer.eos_token_id], "stop"),
        "ordinary_literal_length": (ordinary_literal, "length"),
        "normal_text_with_tag": (encode("Use the literal tag <tool_call> in a parser test.") + [tokenizer.eos_token_id], "stop"),
        "one_good_one_dangling": (encode(valid_tool + "\n<tool_call>") + [tokenizer.eos_token_id], "stop"),
        "dangling_only": (encode("Starting a tool: <tool_call>") + [tokenizer.eos_token_id], "stop"),
        "normal_tool": (encode(valid_tool) + [tokenizer.eos_token_id], "stop"),
    }
    output = {"tokenizer_eos_id": tokenizer.eos_token_id, "scope": "real HTTP adapter, tokenizer, parser and trajectory; engine stub only", "cases": {}}
    original_call = common.call_sglang_generate
    original_parse = common.parse_model_output
    try:
        for mode in ("old", "new"):
            observations = {}

            async def engine(prompt_ids, session, body, *, adapter, session_id):
                ids, finish = cases[session_id]
                return TurnRecord(prompt_ids, list(ids), finish, [-0.2] * len(ids))

            def observed(sid, translated, schema, message, turn):
                observations[sid] = {"manager_message": message, "ill_formed": turn.ill_formed,
                                     "output_ids_preserved": turn.output_ids == cases[sid][0],
                                     "finish": turn.finish_reason}

            common.call_sglang_generate = engine
            if mode == "new":
                parse_wire.install_parse_wire(eos_token=eos)
            else:
                common.parse_model_output = parsing.parse_model_output
            adapter = rh2_anthropic_adapter_cls()(tokenizer=tokenizer, sglang_url="http://unused", fork_threshold_tokens=0, debug_callback=observed)
            async with TestClient(TestServer(adapter.app)) as client:
                for name, (ids, finish) in cases.items():
                    response = await client.post("/v1/messages", headers={"X-Api-Key": name}, json={
                        "messages": [{"role": "user", "content": "Write a parser test."}],
                        "tools": [{"name": "Bash", "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}}}],
                        "max_tokens": 256,
                    })
                    assert response.status == 200, await response.text()
                    data = await response.json()
                    output["cases"].setdefault(name, {"raw": tokenizer.decode(ids, skip_special_tokens=False), "eos_in_ids": tokenizer.eos_token_id in ids, "engine_finish": finish})[mode] = {
                        "content": data["content"], "stop_reason": data["stop_reason"], **observations[name],
                    }
    finally:
        common.call_sglang_generate = original_call
        common.parse_model_output = original_parse
    path = Path(__file__).with_name("probe_parse_boundary.json")
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
