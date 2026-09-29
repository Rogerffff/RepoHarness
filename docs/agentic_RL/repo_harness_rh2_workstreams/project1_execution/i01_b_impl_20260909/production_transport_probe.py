"""Production Tracer 的 CPU 接缝探针；仅用现有 fake Docker/评分/排空屏障。

真实组件：AnthropicAdapter 生命周期、TrajectoryManager、生产 finish 包装、
RolloutOrchestrator、audit 写盘、canonicalize、组准入、训练数据转换。
替身：生成响应与消息脚本、capture commit 绑定、Docker、评分、排空屏障。
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parents[5]
TESTS = REPO / "rh2/tests/adapters_miles"
os.environ["RH2_MILES_PATH"] = str(REPO / "reference/miles-rh2-integration")
sys.path.insert(0, str(TESTS))
spec = importlib.util.spec_from_file_location("i01_probe_world", TESTS / "conftest.py")
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


async def probe():
    from slime.agent.adapters.anthropic import AnthropicAdapter
    from slime.agent.trajectory import TurnRecord

    from repoharness2.adapters.slime.bringup import (
        bringup_leaf_facts,
        make_per_rollout_adapter,
        write_execution_audit_record,
    )
    from repoharness2.adapters.slime.capture_wire import CaptureRegistry
    from test_w1a_formal_chain import _dense_turns
    from test_w1b_group_admission import (
        BOTH_OK,
        _buffer,
        _build_chain,
        _convert,
        _dispatch_group,
        _entry,
        _miles_args,
    )

    world = fixture._World()
    world.install_sglang_stub()
    registry = CaptureRegistry()
    shared = AnthropicAdapter(
        tokenizer=SimpleNamespace(decode=lambda ids, **kw: "decoded"),
        sglang_url="http://unused",
        fork_threshold_tokens=0,
    )
    active = {}

    def factory(hook, session_defaults):
        adapter = make_per_rollout_adapter(registry, shared, hook)
        original_open = adapter.open_session

        def open_session(sid, **kwargs):
            active.update(sid=sid, hook=hook, defaults=session_defaults)
            return original_open(sid, **kwargs)

        adapter.open_session = open_session
        return adapter

    class Driver:
        name = "mock_harness"

        async def run(self, *args, **kwargs):
            sid = active["sid"]
            history = [{"role": "user", "content": "task"}]
            for index, scripted in enumerate(_dense_turns()):
                prompt_ids = list(scripted.prompt_ids)
                if index == 1:
                    prompt_ids[14] = 9999  # 分歧位于上一响应内，0 阈值应保留两行。
                record = active["hook"].on_generate_response(
                    prompt_token_ids=prompt_ids,
                    sampling_params=active["defaults"],
                    response=scripted.response,
                )
                rows = scripted.response["meta_info"]["output_token_logprobs"]
                turn = TurnRecord(
                    prompt_ids=prompt_ids,
                    output_ids=[row[1] for row in rows],
                    output_log_probs=[row[0] for row in rows],
                    finish_reason="stop",
                )
                answer = {"role": "assistant", "content": f"answer-{index}"}
                shared.manager.record_turn(
                    sid, turn=turn, prompt_messages=list(history), response_message=answer
                )
                registry.bind_turn_identity(sid, index + 1, record.record_id)
                history += [answer, {"role": "tool", "content": f"observation-{index}"}]
            return 0

    try:
        with tempfile.TemporaryDirectory(prefix="i01-production-transport-") as directory:
            temp = Path(directory)
            chain = _build_chain(world, temp, grading_kinds=BOTH_OK)
            chain.orchestrator._adapter_factory = factory
            chain.orchestrator._harness_driver = Driver()
            chain.orchestrator._leaf_facts_fn = bringup_leaf_facts
            audit_path = temp / "execution_audit.jsonl"
            chain.orchestrator._audit_sink = lambda audit: write_execution_audit_record(None, audit, audit_path)
            prompt_group, group = await _dispatch_group(world, chain)
            records = [json.loads(line) for line in audit_path.read_text().splitlines()]
            assert len(records) == 2
            assert [len(member) for member in group] == [2, 2]
            for record in records:
                coverage = record["turn_coverage"]
                assert coverage["fork_threshold_tokens"] == 0
                assert coverage["turns_generated"] == coverage["turns_trained"] == 2
                assert coverage["training_rows"] == 2
                assert coverage["row_tokens"] == [22, 35]
                assert coverage["row_trainable_tokens"] == [10, 8]
            for member in group:
                for leaf in member:
                    assert isinstance(leaf, world.MS)
                    assert "rh2_turn_coverage" not in leaf.__dict__
                    assert "rh2_turn_identity_spans" not in leaf.__dict__
                    assert "rh2_turn_coverage" not in leaf.metadata
            args = _miles_args(world, chain)
            buffer, recycled = _buffer(world, args)
            await buffer.put(_entry(world, prompt_group, group))
            delivered = await buffer.get(current_version=5)
            assert delivered.group is group and not recycled
            converted = _convert(world, args, delivered.group)
            assert converted["rollout_ids"] == [0, 0, 1, 1]
            assert converted["rollout_mask_sums"] == [18, 18, 18, 18]
            assert converted["raw_reward"] == [1.0, 1.0, 0.0, 0.0]
            return {
                "status": "passed",
                "miles_base": "rh2-integration",
                "member_rows": [len(member) for member in group],
                "audit_turn_coverage": [record["turn_coverage"] for record in records],
                "rollout_ids": converted["rollout_ids"],
                "rollout_mask_sums": converted["rollout_mask_sums"],
                "raw_reward": converted["raw_reward"],
                "diagnostic_attrs_on_miles_samples": False,
            }
    finally:
        registry.close()


if __name__ == "__main__":
    environment = fixture._vendor_slime_world.__wrapped__()
    next(environment)
    try:
        print(json.dumps(asyncio.run(probe()), ensure_ascii=False, indent=2))
    finally:
        next(environment, None)
