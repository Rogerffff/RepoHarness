"""独立审查探针：只注入替身，不改实现、不运行 GPU/Docker。"""
import asyncio
import errno
import json
import sys
from pathlib import Path

root = next(p for p in Path(__file__).resolve().parents if (p/'rh2/pyproject.toml').is_file()) / 'rh2'
sys.path[:0] = [str(root/'tests'), str(root/'tests/adapters')]
from test_w1b_delivery_face import _formal_chain
from test_slime_generate import _Args, SAMPLING_PARAMS, FakeFinalizationStore
from repoharness2.adapters.slime.async_worker import FatalExecutionInfrastructureError
from repoharness2.adapters.slime.capture_wire import CaptureRegistry, PendingTurn

class FullDiskStore(FakeFinalizationStore):
    def persist_receipt(self, receipt):
        raise OSError(errno.ENOSPC, 'No space left on device')

async def main():
    # 真 CaptureRegistry.stage/commit + 真 hook；只去掉响应的 meta_info.id。
    # HTTP、vendor tree 和 Docker 用既有夹具；下游真实编排照常执行。
    chain = _formal_chain()
    original_factory = chain.orchestrator._adapter_factory
    commit_facts = []
    def wire_factory(hook, defaults):
        adapter = original_factory(hook, defaults)
        adapter.turns[0].response['meta_info'].pop('id', None)
        async def run_with_registry():
            registry = CaptureRegistry()
            sid = adapter.opened[0]
            registry.register(sid, hook, physical_attempt_id='exec_F22#p1-cafe1234')
            for index, turn in enumerate(adapter.turns):
                registry.stage(sid, PendingTurn(prompt_ids=turn.prompt_ids,
                    capture_params=defaults, raw_response=turn.response,
                    weight_version='5', request_id=f'outbound-rid-{index}'))
                ref = registry.commit(sid)
                commit_facts.append({'ref': ref, 'capture_status': hook.records[-1].capture_status,
                                     'tape_count': len(hook.tapes)})
            registry.unregister(sid)
        adapter.run_all_turns = run_with_registry
        return adapter
    chain.orchestrator._adapter_factory = wire_factory
    result = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert commit_facts[0]['ref'] and commit_facts[0]['capture_status'] == 'failed'
    assert commit_facts[0]['tape_count'] == 0
    assert result[0].status == 'aborted' and audit.outcome_v2['reason_code'] == 'capture_record_unknown_in_backfill'
    print(json.dumps({'probe': 'wire_commit_missing_meta_info_id', 'commit_facts': commit_facts,
        'status': result[0].status, 'remove_sample': result[0].remove_sample,
        'outcome': audit.outcome_v2}, ensure_ascii=False, default=str))
    for name in ('leaf_count_mismatch', 'unknown_programming_bug'):
        chain = _formal_chain()
        if name == 'leaf_count_mismatch':
            chain.orchestrator._leaf_facts_fn = lambda *args: []
        else:
            def broken(*args):
                raise TypeError('internal leaf facts programming bug')
            chain.orchestrator._leaf_facts_fn = broken
        result = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
        audit = chain.orchestrator.audits[0]
        assert result[0].status == 'aborted' and result[0].remove_sample is True
        assert audit.outcome_v2['completion_class'] == 'missing'
        print(json.dumps({'probe': name, 'status': result[0].status,
            'remove_sample': result[0].remove_sample, 'outcome': audit.outcome_v2,
            'failure_records': [f.__dict__ for f in audit.failure_records]}, ensure_ascii=False, default=str))
    chain = _formal_chain(store=FullDiskStore(), crash=RuntimeError('harness process failed'))
    raised = None
    try:
        await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    except FatalExecutionInfrastructureError as exc:
        raised = str(exc)
    audit = chain.orchestrator.audits[0]
    assert raised and 'finalization_receipt_write_failed' in raised
    assert not audit.lease_released and chain.orchestrator.cleanup_quarantine
    assert chain.docker.removed == [] and chain.adapter_ref['adapter'].dropped == []
    print(json.dumps({'probe': 'harness_crash_and_receipt_ENOSPC', 'raised': raised,
        'cleanup_quarantine': chain.orchestrator.cleanup_quarantine,
        'lease_released': audit.lease_released, 'steps': [x.step for x in audit.timeline],
        'docker_removed': chain.docker.removed, 'adapter_dropped': chain.adapter_ref['adapter'].dropped},
        ensure_ascii=False, default=str))

asyncio.run(main())
