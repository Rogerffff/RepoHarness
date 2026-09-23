"""只读加载生产函数；使用本仓库已有导入替身；不启动 Docker/GPU。"""
import asyncio
import importlib.util
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

ROOT = next(p for p in Path(__file__).resolve().parents if (p/'rh2/pyproject.toml').is_file())
os.environ['RH2_MILES_PATH'] = str(ROOT / 'reference/miles-rh2-integration')
TESTS = ROOT / 'rh2/tests/adapters_miles'
sys.path.insert(0, str(TESTS))
spec = importlib.util.spec_from_file_location('runtime_probe_conftest', TESTS / 'conftest.py')
cf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cf)
fixture = cf._vendor_slime_world.__wrapped__()
next(fixture)
import pytest
import test_w5a_miles_dispose_chain as helpers

async def shutdown_case(delay, deadline):
    mp = pytest.MonkeyPatch()
    world = cf._World()
    async def unused(*a, **kw):
        raise AssertionError('探针不调用引擎')
    _, fn, _ = helpers._build_fn(world, mp, generate=unused, args=helpers._args(world))
    from miles.rollout.fully_async_data_buffer import DataBufferConstructorInput, DefaultDataBuffer
    fn._output = DefaultDataBuffer(DataBufferConstructorInput(args=fn.args, unused_handler_fn=fn._handle_unused))
    service, _ = helpers._assemble_rh2_service(mp)
    from repoharness2.shutdown import ShutdownTimeouts
    from miles.utils.rh2_shutdown import close_rollout_fn_and_rh2
    service.shutdown_timeouts = ShutdownTimeouts(inflight_grace=.2, inflight_cancel_wait=.2)
    entered = asyncio.Event()
    cleaned = []
    async def group():
        service.lifecycle.enter_execution({}, task_id='probe')
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            await asyncio.sleep(delay)
            cleaned.append('cleanup_completed')
            service.lifecycle.exit_execution()
    task = asyncio.create_task(group())
    await entered.wait()
    fn._active_groups.add(task)
    verdict = await close_rollout_fn_and_rh2(fn, deadline_seconds=deadline)
    print(json.dumps({'case':'shutdown', 'cleanup_delay':delay, 'first_deadline':deadline,
                     'final_task_done':task.done(), 'cleanup_completed':bool(cleaned),
                     'ok':verdict['ok'], 'first_deadline_unfinished':verdict['rollout_fn']['active_groups_unfinished'],
                     'rh2_residue':verdict['rh2']['residue']}, default=str))
    assert task.done() and cleaned
    assert verdict['ok'] is (delay < deadline)
    mp.undo()

async def other_cases():
    from slime.agent.sandbox import ensure_agent_user
    scripts = []
    class FakeSandbox:
        async def exec(self, command, **kwargs):
            scripts.append(command)
            return (0, '', '')
    await ensure_agent_user(FakeSandbox(), '/testbed')
    sh = 'id() { return 0; }; useradd() { echo USERADD; }; chown() { echo CHOWN; }; git() { echo GIT; }; ' + scripts[0]
    shell_result = subprocess.run(['bash','-c',sh],capture_output=True,text=True,check=True)
    assert shell_result.stdout.splitlines()==['CHOWN','GIT']
    print(json.dumps({'case':'existing_agent_user_shell', 'called':shell_result.stdout.splitlines()}))
    from slime.agent.adapters.common import BaseAdapter
    adapter = SimpleNamespace(max_turns_per_sid=25, _sid_turn_count={}, logger=logging.getLogger('cap'), log_prefix='probe')
    responses = [BaseAdapter._check_turn_cap(adapter, 'shared-sid') for _ in range(27)]
    assert all(x is None for x in responses[:25]) and all(x.status==429 for x in responses[25:])
    print(json.dumps({'case':'sid_cap', 'statuses':[None if x is None else x.status for x in responses], 'accepted_count':adapter._sid_turn_count['shared-sid']}))
    from repoharness2.adapters.slime.async_worker import ModelCallProxy, StaticActiveCoordinator, ResourceLimits, SessionPoisonRegistry
    limits = ResourceLimits({'model_call':1})
    proxy = ModelCallProxy(StaticActiveCoordinator(lambda:'1'), limits=limits, attempt_timeout_seconds=900)
    poison = SessionPoisonRegistry()
    start = time.monotonic()
    send_started=[]
    async def send(_):
        send_started.append(time.monotonic()-start)
        await asyncio.sleep(.005)
        return {'meta_info':{'weight_version':'1'}}
    async with limits.acquire('model_call'):
        call = asyncio.create_task(proxy.call('paid','t1',send,session_id='sid',poison_registry=poison,
                                              deadline_monotonic=start+.02,min_attempt_budget_seconds=.001))
        await asyncio.sleep(.04)
    await call
    assert send_started[0]>.02
    print(json.dumps({'case':'proxy_deadline_queue', 'send_started_after_seconds':round(send_started[0],3), 'deadline_seconds':.02, 'success_after_seconds':round(time.monotonic()-start,3), 'backpressure':limits.backpressure_counts['model_call']}))
    from repoharness2.adapters.slime.capture_wire import CaptureRegistry
    from repoharness2.adapters.slime.generate import RolloutOrchestrator
    registry = CaptureRegistry()
    registry.register('drain-sid',None,physical_attempt_id='paid')
    registry._inflight_enter('drain-sid')
    result = await registry.drain_session_plane('drain-sid',timeout_seconds=.001)
    orchestrator = object.__new__(RolloutOrchestrator)
    async def owner(sid):
        return result
    orchestrator._session_drain_owner = owner
    try:
        await orchestrator._drain_session_plane_owned('drain-sid','paid')
    except Exception as exc:
        print(json.dumps({'case':'drain_timeout', 'inflight_zero_confirmed':result.inflight_zero_confirmed, 'exception':type(exc).__name__, 'reason_code':getattr(exc,'reason_code',None)}))
    registry._inflight_exit('drain-sid')

async def main():
    await shutdown_case(.002,.03)
    await shutdown_case(.06,.01)
    await other_cases()

asyncio.run(main())
