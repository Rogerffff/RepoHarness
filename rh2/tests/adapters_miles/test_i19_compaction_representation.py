"""第三组 I19（owner 2026-09-10 定案）：恢复 harness 正常压缩后的表示层事实——真实接缝 CPU 测试。

真实组件：vendor TrajectoryManager（fork_threshold_tokens=0）、capture stage/commit 与身份绑定、bringup_leaf_facts、
RolloutOrchestrator（fa_formal）、projection、canonicalize、miles 组准入与训练数据转换。替身：输入消息 / token、模型回复、
Docker、评分、排空屏障。它不把合成请求形态当作真实 Claude Code 压缩证据（目标 CC 的真实请求面由 owner 在基座诊断时核对）。
两案取自 Codex 09-10 五案探针（同路径 token 收缩、同入口生成摘要再作 prompt），装配方式逐字沿用，不另写一套替身。
"""

from __future__ import annotations

import tempfile
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.integration_base


def _msg(role, text):
    return {"role": role, "content": text}


def _scenarios():
    p1, o1 = list(range(1000, 1100)), [5000, 5001, 5002]
    p2, o2 = p1 + o1 + list(range(6000, 6057)), [5100, 5101]
    p3, o3 = list(range(9000, 9040)), [5200, 5201, 5202, 5203]
    p4, o4 = p3 + o3 + [6100, 6101], [5300, 5301]
    h1 = [_msg("user", "修复任务")]
    a1, a2, a3, a4 = [_msg("assistant", f"动作{i}") for i in range(1, 5)]
    h2 = h1 + [a1, _msg("tool", "较长工具输出")]
    h3 = h2 + [a2, _msg("tool", "待压缩工具输出")]
    h4 = h3 + [a3, _msg("tool", "新的工具输出")]
    normal = [(p1, o1, h1, a1), (p2, o2, h2, a2)]
    # 同一消息路径，只有传给模型的 token 前缀大幅收缩（100→160→40→46）：第 3 轮分行，不拒绝
    same_path = normal + [(p3, o3, h3, a3), (p4, o4, h4, a4)]
    # 摘要本身经同一 sid 捕获生成（第 3 轮延续前缀），随后作为新 prompt 的组成部分（第 4 轮分行）
    summary_output = [5700, 5701, 5702]
    summary_request = normal + [
        (p2 + o2 + [6400], summary_output, h2 + [a2, _msg("user", "请生成压缩摘要")], _msg("assistant", "模型生成的摘要")),
        (list(range(9000, 9037)) + summary_output, o3, [_msg("user", "摘要已作为新的上下文传入")], a3),
    ]
    return {"same_message_path_token_shrink": same_path, "captured_summary_generation": summary_request}


async def _run_case(world, monkeypatch, name, script):
    import sys

    from slime.agent.adapters.anthropic import AnthropicAdapter
    from slime.agent.trajectory import TurnRecord
    from repoharness2.adapters.slime.bringup import FORK_THRESHOLD_TOKENS, bringup_leaf_facts, make_per_rollout_adapter
    from repoharness2.adapters.slime.capture_wire import CaptureRegistry, PendingTurn, install_capture_wire
    from repoharness2.adapters.slime.generate import detect_context_shrink
    from test_w1a_formal_chain import _sglang_response
    from test_w1b_group_admission import BOTH_OK, _buffer, _build_chain, _convert, _dispatch_group, _entry, _miles_args

    world.install_sglang_stub()
    # 进程级单代归属重置为"新进程"（与 test_budget_loop / W3b 启动测试同一约定）；取 install_capture_wire
    # 实际 import 的那个模块对象（stub 安装之后再取）
    slime_common = sys.modules["slime.agent.adapters.common"]
    monkeypatch.setattr(slime_common, "_rh2_capture_wire_installed", False, raising=False)
    monkeypatch.setattr(slime_common, "_rh2_capture_wire_registry", None, raising=False)
    monkeypatch.setattr(slime_common, "_rh2_turn_budget_wire_registry", None, raising=False)
    registry = CaptureRegistry()
    install_capture_wire(registry)
    shared = AnthropicAdapter(
        tokenizer=SimpleNamespace(decode=lambda ids, **kw: "解码占位"), sglang_url="http://unused",
        fork_threshold_tokens=FORK_THRESHOLD_TOKENS,
    )
    assert shared.manager._fork_threshold == 0
    active: dict = {"script": script}
    rows_per_member: list[list[dict]] = []

    def factory(hook, defaults):
        adapter = make_per_rollout_adapter(registry, shared, hook)
        original_open = adapter.open_session

        def open_session(sid, **kwargs):
            active.update(sid=sid, defaults=defaults, prompts={})
            return original_open(sid, **kwargs)

        adapter.open_session = open_session
        return adapter

    class Driver:
        name = "mock_harness"

        async def run(self, *args, **kwargs):
            sid = active["sid"]
            for index, (prompt, output, history, answer) in enumerate(active["script"], 1):
                response = _sglang_response(f"i19-{index}", output)
                pending = PendingTurn(
                    prompt_ids=list(prompt), capture_params=dict(active["defaults"]), raw_response=response,
                    weight_version="5", request_id=f"i19-{index}",
                )
                assert registry.stage(sid, pending)
                shared.manager.record_turn(
                    sid,
                    turn=TurnRecord(
                        prompt_ids=list(prompt), output_ids=list(output), finish_reason="stop",
                        output_log_probs=[pair[0] for pair in response["meta_info"]["output_token_logprobs"]],
                    ),
                    prompt_messages=list(history), response_message=dict(answer),
                )
                record_id = registry.turn_capture_binding(sid, index)  # 由真实 record_turn 绑定
                assert record_id is not None
                active["prompts"][record_id] = list(prompt)
            return 0

    def facts_spy(sid, samples, hook):
        facts = bringup_leaf_facts(sid, samples, hook)
        tape_by_id = hook.tape_by_record_id
        rows = []
        for sample, fact in zip(samples, facts):
            prompt_len = len(sample.tokens) - len(sample.loss_mask)
            turns = [tape_by_id[rid] for rid in fact.capture_record_ids]
            for span in fact.turn_spans:
                tape = tape_by_id[span.capture_record_id]
                start = prompt_len + span.start
                assert sample.tokens[:start] == active["prompts"][span.capture_record_id]  # 每个动作的输入 = 捕获 prompt
                assert sample.tokens[start:start + span.length] == list(tape.output_ids)
            rows.append({"turn_indices": [t.turn_index for t in turns], "branch_shrink": detect_context_shrink(turns)})
        rows_per_member.append(rows)
        return facts

    try:
        with tempfile.TemporaryDirectory(prefix="i19-") as directory:
            chain = _build_chain(world, Path(directory), grading_kinds=BOTH_OK)
            chain.orchestrator._adapter_factory = factory
            chain.orchestrator._harness_driver = Driver()
            chain.orchestrator._leaf_facts_fn = facts_spy
            prompt_group, group = await _dispatch_group(world, chain)
            expected_tokens = sum(len(turn[1]) for turn in script)
            for member in group:
                assert all(leaf.remove_sample is False for leaf in member)  # 不拒绝
                assert sum(sum(leaf.loss_mask) for leaf in member) == expected_tokens
                assert len({leaf.metadata["rh2_rollout_execution_id"] for leaf in member}) == 1
            output_ids = [token for turn in script for token in turn[1]]
            trained = Counter()
            occurrences = Counter()
            for leaf in group[0]:
                full_mask = [0] * (len(leaf.tokens) - len(leaf.loss_mask)) + list(leaf.loss_mask)
                occurrences.update(leaf.tokens)
                trained.update(token for token, mask in zip(leaf.tokens, full_mask) if mask)
            assert trained == Counter(output_ids)  # 每个生成 token 恰好训练一次
            audits = chain.orchestrator.audits
            assert all(any(r.startswith("session:") for r in a.context_shrink_reasons) for a in audits)  # 线索
            assert all(not any(r.startswith("branch ") for r in a.context_shrink_reasons) for a in audits)
            args = _miles_args(world, chain)
            buffer, _recycled = _buffer(world, args)
            await buffer.put(_entry(world, prompt_group, group))
            delivered = await buffer.get(current_version=5)
            converted = _convert(world, args, delivered.group)
            assert converted["rollout_mask_sums"] == [expected_tokens] * sum(map(len, group))  # 分母 = 同成员唯一动作 token
            return {"rows": rows_per_member[0], "member_rows": [len(m) for m in group], "occurrences": occurrences,
                    "trained": trained, "script": script}
    finally:
        registry.close()


async def test_same_path_token_shrink_forks_a_new_row_and_is_not_rejected(world, monkeypatch):
    out = await _run_case(world, monkeypatch, "same_message_path_token_shrink", _scenarios()["same_message_path_token_shrink"])
    assert out["member_rows"] == [2, 2] and [r["turn_indices"] for r in out["rows"]] == [[0, 1], [2, 3]]
    assert all(not r["branch_shrink"] for r in out["rows"])  # 行内 prompt 单调不降：叶链级检测无事可做


async def test_captured_summary_generation_is_trained_once_and_reinjected_as_prompt(world, monkeypatch):
    """同策略捕获入口生成的摘要 = 一次真实动作（训练一次）；重注入后只是 prompt（token 出现两次、训练位一次）。"""

    out = await _run_case(world, monkeypatch, "captured_summary_generation", _scenarios()["captured_summary_generation"])
    assert out["member_rows"] == [2, 2] and [r["turn_indices"] for r in out["rows"]] == [[0, 1, 2], [3]]
    for token in out["script"][2][1]:  # 摘要的三个 token
        assert out["occurrences"][token] == 2 and out["trained"][token] == 1
