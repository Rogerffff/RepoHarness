"""N3 聚焦反证：真实双 loop、miles 组取消、formal finally 与关停报告；只替换外部 I/O。"""
from __future__ import annotations
import ast
import asyncio
import importlib.util
import json
import logging
import os
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[7]
os.environ['RH2_MILES_PATH'] = str(ROOT / 'reference/miles-rh2-integration')
sys.path[:0] = [str(ROOT / 'rh2/src'), str(ROOT / 'rh2/tests/adapters'), str(ROOT / 'rh2/tests/adapters_miles')]
import pytest
spec = importlib.util.spec_from_file_location('miles_probe_world', ROOT / 'rh2/tests/adapters_miles/conftest.py')
wc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wc)
setup = wc._vendor_slime_world.__wrapped__()
next(setup)
world = wc._World()
import test_w5a_miles_dispose_chain as dual
import test_w5a_shutdown_chain as formal
from repoharness2.adapters.slime import bringup


def actual_group_function(generate_member):
    """读取 fork 原函数逐字编译，避开 tokenizer/sglang 的模块级依赖。没有复制改写组逻辑。"""
    source = ROOT / 'reference/miles-rh2-integration/miles/rollout/inference_rollout/inference_rollout_common.py'
    tree = ast.parse(source.read_text())
    fn = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == 'generate_and_rm_group')
    code = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), fn], type_ignores=[])
    ns = {'asyncio': asyncio, 'logger': logging.getLogger('probe'), 'policy_uses_routing_key': lambda args: False, 'generate_and_rm': generate_member}
    exec(compile(ast.fix_missing_locations(code), str(source), 'exec'), ns)
    return ns['generate_and_rm_group']


async def one_case(*, slow_network: bool, fault: str = 'none'):
    patch = pytest.MonkeyPatch()
    service, tmp = dual._assemble_rh2_service(patch)
    store = formal.FakeFinalizationStore(fail_persist_receipt=(fault == 'receipt'))
    task_spec = formal.make_task(formal.TASK_ID_DENSE)
    def resolver(sample):
        service._bind_owner_loop()
        service.lifecycle.enter_execution(sample.metadata, task_id=task_spec.task_id)
        return task_spec
    turns = formal.dense_turns()
    for turn in turns:
        turn.response['meta_info']['weight_version'] = '5'
    chain = formal.build_dense_chain(config=formal._formal_config(execution_mode='fa_formal'), runtime_quiescence_barrier=formal._Barrier(), turns=turns, finalization_store=store, task=resolver, audit_sink=service._write_execution_audit)
    formal._stamp_fa_identity(chain.base_sample)
    service.orchestrator = chain.orchestrator
    service.egress_relay = chain.orchestrator._egress_relay
    if fault == 'audit':
        def broken_audit(*a, **kw):
            raise OSError('probe audit sink unavailable')
        patch.setattr(bringup, 'write_execution_audit_record', broken_audit)
    if fault == 'optional_snapshot':
        def broken_optional(*a, **kw):
            raise OSError('probe optional snapshot unavailable')
        chain.orchestrator._emit_attempt_cost_snapshot = broken_optional
    entered = threading.Event()
    network_entered = threading.Event()
    network_cancelled = threading.Event()
    class Driver(formal._BlockingDriver):
        async def run(self, *a, **kw):
            entered.set()
            return await super().run(*a, **kw)
    chain.orchestrator._harness_driver = Driver(chain.adapter_ref)
    first_disconnect = True
    async def docker(*args, **kw):
        nonlocal first_disconnect
        if len(args) >= 2 and args[:2] == ('network', 'disconnect') and first_disconnect:
            first_disconnect = False
            network_entered.set()
            try:
                # 对照：首次 .2s 等待已到期、RH2 的 .05s grace 内完成；反例：grace 到期触发真实第二次取消。
                await asyncio.sleep(0.8 if slow_network else 0.22)
            except asyncio.CancelledError:
                network_cancelled.set()
                raise
        return await chain.docker(*args, **kw)
    chain.orchestrator._docker = docker
    patch.setattr(bringup, '_sandbox_docker', lambda: docker)
    async def member(state, sample, sampling_params, evaluation=False):
        return await chain.orchestrator.generate(formal._Args(), chain.base_sample, dict(formal.SAMPLING_PARAMS))
    group = actual_group_function(member)
    args = dual._args(world, rh2_shutdown_deadline_sec=0.2)
    args.rollout_batch_size = 1
    args.n_samples_per_prompt = 1
    args.group_rm = False
    far, fn, _ = dual._build_fn(world, patch, generate=group, args=args)
    drain = asyncio.create_task(dual._drain_like_production(fn))
    assert await asyncio.to_thread(entered.wait, 5), 'harness 未启动'
    from miles.utils.rh2_shutdown import dispose_on_owner_loop
    verdict = await dispose_on_owner_loop(fn, timeout_seconds=10, driver_cause='RuntimeError: probe driver cause' if fault == 'driver' else None)
    try:
        await drain
    except far.RolloutFnClosed:
        pass
    audit = chain.orchestrator.audits[0]
    disk = json.loads((tmp / 'shutdown_report.json').read_text())
    out = {
        'slow_network': slow_network,
        'fault': fault,
        'necessary_records_complete': audit.necessary_records_complete,
        'primary_cause': verdict['primary_cause'],
        'verdict_ok': verdict['ok'],
        'wait_resolved': (verdict['shutdown_failure'] or {}).get('resolved_by_final_closure'),
        'initial_wait_failure': (verdict['shutdown_failure'] or {}).get('problems'),
        'final_state': (verdict['shutdown_failure'] or {}).get('final_state'),
        'execution_closure': disk['execution_closure'],
        'receipt_count': len(store.receipts),
        'execution_audit_file_exists': (tmp / 'fa_execution_audit.jsonl').exists(),
        'lease_released': audit.lease_released,
        'network_entered': network_entered.is_set(),
        'network_cancelled': network_cancelled.is_set(),
        'network_residue': dict(chain.docker.profile_fake.networks),
        'cleanup_failures': [f.step for f in audit.cleanup_failures],
        'record_failure_types': [f.error_type for f in audit.failure_records],
        'inflight': disk['steps'][2]['facts'],
        'evidence_directory_basename': tmp.name,
    }
    (tmp / 'fork_verdict.json').write_text(json.dumps(verdict, indent=2))
    expect_records = not slow_network and fault not in ('receipt', 'audit')
    assert audit.necessary_records_complete is expect_records, out
    assert verdict['ok'] is (expect_records and fault != 'driver'), out
    assert disk['execution_closure']['attempts_records_incomplete'] == (0 if expect_records else 1), out
    patch.undo()
    return out

async def normal_completion():
    patch = pytest.MonkeyPatch()
    service, tmp = dual._assemble_rh2_service(patch)
    store = formal.FakeFinalizationStore()
    task_spec = formal.make_task(formal.TASK_ID_DENSE)
    def resolver(sample):
        service._bind_owner_loop()
        service.lifecycle.enter_execution(sample.metadata, task_id=task_spec.task_id)
        return task_spec
    turns = formal.dense_turns()
    for turn in turns:
        turn.response['meta_info']['weight_version'] = '5'
    chain = formal.build_dense_chain(config=formal._formal_config(execution_mode='fa_formal'), runtime_quiescence_barrier=formal._Barrier(), turns=turns, finalization_store=store, task=resolver, audit_sink=service._write_execution_audit)
    formal._stamp_fa_identity(chain.base_sample)
    service.orchestrator = chain.orchestrator
    service.egress_relay = chain.orchestrator._egress_relay
    patch.setattr(bringup, '_sandbox_docker', lambda: chain.docker)
    delivered = await chain.orchestrator.generate(formal._Args(), chain.base_sample, dict(formal.SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    report = await service.close()
    out = {
        'case': 'normal_completed_formal',
        'delivered_count': len(delivered),
        'reward': delivered[0].reward,
        'necessary_records_complete': audit.necessary_records_complete,
        'receipt_count': len(store.receipts),
        'execution_audit_file_exists': (tmp / 'fa_execution_audit.jsonl').exists(),
        'shutdown_ok': report.ok,
        'execution_closure': report.execution_closure,
        'evidence_directory_basename': tmp.name,
    }
    assert out['necessary_records_complete'] and out['shutdown_ok'] and out['execution_audit_file_exists'], out
    assert out['receipt_count'] == 1 and out['reward'] == 1.0, out
    patch.undo()
    return out

async def main():
    results = [await one_case(slow_network=False), await one_case(slow_network=True)]
    for fault in ('receipt', 'audit', 'optional_snapshot', 'driver'):
        results.append(await one_case(slow_network=False, fault=fault))
    results.append(await normal_completion())
    target = Path(__file__).with_name('n3_followup_result.json')
    target.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(target.read_text())

try:
    asyncio.run(main())
finally:
    try:
        next(setup)
    except StopIteration:
        pass
