"""I19 生产接缝 CPU 探针：不请求 CLI/API/GPU，不修改仓库。

真实组件：vendor TrajectoryManager、capture stage/commit 与身份绑定、生产
finish 包装、bringup_leaf_facts、RolloutOrchestrator、projection、canonicalize、
miles 组准入和训练数据转换。替身：输入消息/token、模型回复、Docker、评分、
排空屏障；不把合成请求形态当作真实 Claude Code 压缩证据。
"""

from __future__ import annotations

import asyncio
from collections import Counter
import importlib.util
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
from types import SimpleNamespace

REPO = next(p for p in Path(__file__).resolve().parents if (p / 'rh2/pyproject.toml').is_file())
TESTS = REPO / 'rh2/tests/adapters_miles'
OUT = Path(__file__).resolve().parent
os.environ['RH2_MILES_PATH'] = str(REPO / 'reference/miles-rh2-integration')
sys.path.insert(0, str(TESTS))
spec = importlib.util.spec_from_file_location('i19_probe_world', TESTS / 'conftest.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


def msg(role, text):
    return {'role': role, 'content': text}


def scenarios():
    p1, o1 = list(range(1000, 1100)), [5000, 5001, 5002]
    p2, o2 = p1 + o1 + list(range(6000, 6057)), [5100, 5101]
    p3, o3 = list(range(9000, 9040)), [5200, 5201, 5202, 5203]
    p4, o4 = p3 + o3 + [6100, 6101], [5300, 5301]
    h1 = [msg('user', '修复任务')]
    a1, a2, a3, a4 = [msg('assistant', f'动作{i}') for i in range(1, 5)]
    h2 = h1 + [a1, msg('tool', '较长工具输出')]
    h3 = h2 + [a2, msg('tool', '待压缩工具输出')]
    h4 = h3 + [a3, msg('tool', '新的工具输出')]
    normal = [(p1, o1, h1, a1), (p2, o2, h2, a2)]
    # 消息树还是同一条路径，只有传给模型的 token 前缀发生大幅收缩。
    same_path = normal + [(p3, o3, h3, a3), (p4, o4, h4, a4)]
    # 摘要替换了原来的消息路径，旧路径保持为另一个 routing leaf。
    summary = [msg('user', '压缩摘要：保留目标与关键发现')]
    summary_branch = normal + [(p3, o3, summary, a3),
                              (p4, o4, summary + [a3, msg('tool', '新的工具输出')], a4)]
    # 摘要分支仍共享早期生成节点，验证共享动作仅在第一条训练行训练一次。
    shared_summary = h1 + [a1, msg('user', '后续历史已压缩为摘要')]
    shared_prefix = normal + [(p3, o3, shared_summary, a3),
                             (p4, o4, shared_summary + [a3, msg('tool', '新的工具输出')], a4)]
    # 主 agent 暂停，子 agent 使用新的短上下文，随后主 agent 正常继续。
    sp1, so1 = list(range(9200, 9220)), [5400, 5401, 5402]
    sp2, so2 = sp1 + so1 + [6200, 6201], [5500, 5501]
    sa1, sa2 = msg('assistant', '子动作1'), msg('assistant', '子动作2')
    sh1 = [msg('user', '子任务')]
    subagent = normal + [(sp1, so1, sh1, sa1),
                         (sp2, so2, sh1 + [sa1, msg('tool', '子工具输出')], sa2),
                         (p2 + o2 + [6300, 6301], [5600, 5601], h3, msg('assistant', '主动作3'))]
    # 如果摘要本身是经同一 sid 捕获的模型生成，当前代码也把它视为采样动作。
    # 这不是断言真实 CC 一定如此调用，只测试该输入事实进入当前管道后的行为。
    summary_output = [5700, 5701, 5702]
    summary_request = normal + [
        (p2 + o2 + [6400], summary_output, h2 + [a2, msg('user', '请生成压缩摘要')],
         msg('assistant', '模型生成的摘要')),
        (list(range(9000, 9037)) + summary_output, o3,
         [msg('user', '摘要已作为新的上下文传入')], a3),
    ]
    return {
        'same_message_path_token_shrink': same_path,
        'summary_message_tree_branch': summary_branch,
        'shared_prefix_summary_branch': shared_prefix,
        'main_long_then_subagent_short': subagent,
        'captured_summary_generation': summary_request,
    }


async def probe():
    from slime.agent.adapters.anthropic import AnthropicAdapter
    from slime.agent.trajectory import DriftKind, TurnRecord, _SampleBuilder
    from repoharness2.adapters.slime.bringup import (
        FORK_THRESHOLD_TOKENS, bringup_leaf_facts, make_per_rollout_adapter,
    )
    from repoharness2.adapters.slime.capture_wire import (
        CaptureRegistry, PendingTurn, install_capture_wire,
    )
    from repoharness2.adapters.slime.generate import detect_context_shrink
    from test_w1a_formal_chain import _sglang_response
    from test_w1b_group_admission import (
        BOTH_OK, _buffer, _build_chain, _convert, _dispatch_group, _entry, _miles_args,
    )

    world = fixture._World()
    world.install_sglang_stub()
    registry = CaptureRegistry()
    install_capture_wire(registry)
    shared = AnthropicAdapter(
        tokenizer=SimpleNamespace(decode=lambda ids, **kw: '探针解码占位'),
        sglang_url='http://unused', fork_threshold_tokens=FORK_THRESHOLD_TOKENS,
    )
    assert shared.manager._fork_threshold == 0
    active, completed = {}, []

    def factory(hook, defaults):
        adapter = make_per_rollout_adapter(registry, shared, hook)
        original_open = adapter.open_session

        def open_session(sid, **kwargs):
            active.update(sid=sid, hook=hook, defaults=defaults, prompts={})
            return original_open(sid, **kwargs)

        adapter.open_session = open_session
        return adapter

    class Driver:
        name = 'mock_harness'

        async def run(self, *args, **kwargs):
            sid = active['sid']
            for index, (prompt, output, history, answer) in enumerate(active['script'], 1):
                response = _sglang_response(f'i19-{index}', output)
                pending = PendingTurn(
                    prompt_ids=list(prompt), capture_params=dict(active['defaults']),
                    raw_response=response, weight_version='5', request_id=f'i19-{index}',
                )
                assert registry.stage(sid, pending)
                shared.manager.record_turn(
                    sid, turn=TurnRecord(
                        prompt_ids=list(prompt), output_ids=list(output), finish_reason='stop',
                        output_log_probs=[pair[0] for pair in response['meta_info']['output_token_logprobs']],
                    ), prompt_messages=list(history), response_message=dict(answer),
                )
                # capture id 由真实 record_turn 包装 commit 并绑定，不手写对应关系。
                record_id = registry.turn_capture_binding(sid, index)
                assert record_id is not None
                active['prompts'][record_id] = list(prompt)
            return 0

    def facts_spy(sid, samples, hook):
        facts = bringup_leaf_facts(sid, samples, hook)
        tape_by_id = hook.tape_by_record_id
        seen = Counter()
        rows = []
        for sample, fact in zip(samples, facts):
            prompt_len = len(sample.tokens) - len(sample.loss_mask)
            turns = [tape_by_id[record_id] for record_id in fact.capture_record_ids]
            input_checks = []
            for span in fact.turn_spans:
                tape = tape_by_id[span.capture_record_id]
                seen[tape.turn_index] += 1
                start = prompt_len + span.start
                input_checks.append(sample.tokens[:start] == active['prompts'][span.capture_record_id])
                assert sample.tokens[start:start + span.length] == list(tape.output_ids)
            rows.append({
                'branch_id': fact.branch_id,
                'turn_indices': [t.turn_index for t in turns],
                'turn_prompt_lengths': [t.prompt_token_count for t in turns],
                'row_prompt_length': prompt_len,
                'row_token_length': len(sample.tokens),
                'row_trainable_tokens': sum(sample.loss_mask),
                'row_context_tokens_in_response': len(sample.loss_mask) - sum(sample.loss_mask),
                'every_action_input_equals_captured_prompt': all(input_checks),
                'branch_shrink_reasons': detect_context_shrink(turns),
                'lineage': fact.lineage,
                'context_runs': list(fact.context_runs),
            })
        assert seen == Counter({i: 1 for i in range(len(active['script']))})
        assert all(r['every_action_input_equals_captured_prompt'] for r in rows)
        assert not any(r['branch_shrink_reasons'] for r in rows)
        completed.append({
            'rows': rows, 'trained_capture_count_per_turn': dict(seen),
            'session_shrink_reasons': detect_context_shrink(hook.tapes),
        })
        return facts

    results = []
    controls = []
    for threshold in (0, 1024):
        builder = _SampleBuilder(threshold)
        builder.append_turn(TurnRecord(list(range(100)), [100, 101], 'stop'), DriftKind.CLEAN)
        incoming = TurnRecord(list(range(40)), [200], 'stop')
        kind = builder.classify_token_drift(incoming)
        assert kind is DriftKind.FORK
        controls.append({'fork_threshold': threshold, 'old_prompt': 100, 'new_prompt': 40,
                         'drift_kind': kind.value})
    try:
        for name, script in scenarios().items():
            active['script'] = script
            completed.clear()
            with tempfile.TemporaryDirectory(prefix='i19-fake-run-') as directory:
                chain = _build_chain(world, Path(directory), grading_kinds=BOTH_OK)
                chain.orchestrator._adapter_factory = factory
                chain.orchestrator._harness_driver = Driver()
                chain.orchestrator._leaf_facts_fn = facts_spy
                prompt_group, group = await _dispatch_group(world, chain)
                assert len(completed) == 2
                expected_tokens = sum(len(turn[1]) for turn in script)
                for member in group:
                    assert all(leaf.remove_sample is False for leaf in member)
                    assert sum(sum(leaf.loss_mask) for leaf in member) == expected_tokens
                    assert len({leaf.metadata['rh2_rollout_execution_id'] for leaf in member}) == 1
                    assert len({leaf.metadata['rh2_member_slot'] for leaf in member}) == 1
                # 合成数据中每个输出 token 的 id 唯一；即便重放到摘要 prompt，训练位仍恰有一次。
                output_ids = [token for turn in script for token in turn[1]]
                trained_ids = Counter()
                token_occurrences = Counter()
                for leaf in group[0]:
                    full_mask = [0] * (len(leaf.tokens) - len(leaf.loss_mask)) + list(leaf.loss_mask)
                    token_occurrences.update(leaf.tokens)
                    trained_ids.update(token for token, mask in zip(leaf.tokens, full_mask) if mask)
                assert trained_ids == Counter(output_ids)
                assert all(a.context_shrink_reasons for a in chain.orchestrator.audits)
                assert all(not any(r.startswith('branch ') for r in a.context_shrink_reasons)
                           for a in chain.orchestrator.audits)
                args = _miles_args(world, chain)
                buffer, recycled = _buffer(world, args)
                await buffer.put(_entry(world, prompt_group, group))
                assert len(buffer._buffer) == 1
                delivered = await buffer.get(current_version=5)
                converted = _convert(world, args, delivered.group)
                assert converted['rollout_mask_sums'] == [expected_tokens] * sum(map(len, group))
                projection = chain.orchestrator.audits[0].finalized.projection
                results.append({
                    'case': name, 'status': 'passed', 'execution_mode': 'fa_formal',
                    'reject_context_shrink': chain.orchestrator.config.reject_context_shrink,
                    'fork_threshold_tokens': shared.manager._fork_threshold,
                    'capture_prompt_lengths': [len(t[0]) for t in script],
                    'capture_output_lengths': [len(t[1]) for t in script],
                    'member_rows': [len(member) for member in group],
                    'first_member': completed[0],
                    'turn_coverage': chain.orchestrator.audits[0].turn_coverage,
                    'projection_lineages': [b.lineage for b in projection.branches],
                    'projection_token_sources': [
                        [{'start': s.start, 'end': s.end, 'source_type': s.source_type} for s in b.token_spans]
                        for b in projection.branches
                    ],
                    'rollout_ids': converted['rollout_ids'],
                    'rollout_mask_sums': converted['rollout_mask_sums'],
                    'raw_reward': converted['raw_reward'],
                    'same_execution_and_member_within_each_member': True,
                    'output_token_training_occurrences': {token: trained_ids[token] for token in output_ids},
                    'summary_replay_control': (
                        {token: {'token_occurrences': token_occurrences[token],
                                 'training_occurrences': trained_ids[token]}
                         for token in script[2][1]}
                        if name == 'captured_summary_generation' else None
                    ),
                })
    finally:
        registry.close()
    return {'status': 'passed', 'source_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip(),
            'real_cli_or_api_used': False, 'shrink_classification_controls': controls, 'cases': results}


if __name__ == '__main__':
    environment = fixture._vendor_slime_world.__wrapped__()
    next(environment)
    try:
        result = asyncio.run(probe())
        (OUT / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({'status': result['status'], 'cases': [
            {'case': c['case'], 'member_rows': c['member_rows'],
             'row_turns': [r['turn_indices'] for r in c['first_member']['rows']],
             'session_signals': len(c['first_member']['session_shrink_reasons']),
             'branch_signals': sum(len(r['branch_shrink_reasons']) for r in c['first_member']['rows']),
             'rollout_mask_sums': c['rollout_mask_sums']}
            for c in result['cases']]}, ensure_ascii=False, indent=2))
    finally:
        next(environment, None)
