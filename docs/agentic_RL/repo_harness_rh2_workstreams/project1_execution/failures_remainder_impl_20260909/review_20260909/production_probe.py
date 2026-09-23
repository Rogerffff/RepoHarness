import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace

root = next(p for p in Path(__file__).resolve().parents if (p / 'rh2/pyproject.toml').is_file())
sys.path[:0] = [str(root / 'rh2/src'), str(root / 'rh2/tests/adapters')]

from repoharness2.grading.queue import GradingQueue, GradingQueueConfig
from repoharness2.shutdown.chain import LifecycleState, close_inflight_executions

async def queue_probe():
    entered = asyncio.Event()
    release = asyncio.Event()
    class Manager:
        cancelled = False
        async def grade(self, **kw):
            entered.set()
            try:
                await release.wait()
                return None
            except asyncio.CancelledError:
                self.cancelled = True
                raise
    manager = Manager()
    queue = GradingQueue(manager, GradingQueueConfig(concurrency=1, queue_size=1))
    await queue.start()
    waiter = asyncio.create_task(queue.submit(trajectory_id='probe', workspace=None, spec=SimpleNamespace(task_id='task')))
    await entered.wait()
    try:
        await asyncio.wait_for(waiter, timeout=0.01)
    except TimeoutError:
        pass
    result = {
        'submitter_cancelled': waiter.cancelled(),
        'worker_grade_cancelled': manager.cancelled,
        'active_grading_after_submitter_timeout': queue.active_grading_count,
    }
    release.set()
    await queue.close()
    return result

async def receipt_probe(fail):
    from test_w5a_shutdown_chain import (
        FakeFinalizationStore, dense_turns, make_task, TASK_ID_DENSE,
        build_dense_chain, _formal_config, _Barrier, _stamp_fa_identity,
        _BlockingDriver, _Args, SAMPLING_PARAMS,
    )
    state = LifecycleState()
    store = FakeFinalizationStore(fail_persist_receipt=fail)
    turns = dense_turns()
    for turn in turns:
        turn.response['meta_info']['weight_version'] = '5'
    spec = make_task(TASK_ID_DENSE)
    def resolver(sample):
        state.enter_execution(sample.metadata, task_id=spec.task_id)
        return spec
    chain = build_dense_chain(config=_formal_config(execution_mode='fa_formal'), runtime_quiescence_barrier=_Barrier(), turns=turns, finalization_store=store, task=resolver)
    _stamp_fa_identity(chain.base_sample)
    driver = _BlockingDriver(chain.adapter_ref)
    chain.orchestrator._harness_driver = driver
    run = asyncio.create_task(chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS)))
    await asyncio.wait_for(driver.entered.wait(), 5)
    facts = await close_inflight_executions(state, grace_seconds=0.01, cancel_wait_seconds=2)
    return {
        'injected_receipt_failure': fail,
        'run_cancelled': run.cancelled(),
        'unfinished_after_cancel_wait': facts['unfinished_after_cancel_wait'],
        'run_fatal_count': len(state.fatal_seen),
        'receipt_count': len(store.receipts),
        'containers_removed': len(chain.docker.removed),
        'audit_errors': [f.error_type for f in chain.orchestrator.audits[0].failure_records],
    }

async def main():
    print(json.dumps({'queue_timeout': await queue_probe(), 'cancel_receipt_success': await receipt_probe(False), 'cancel_receipt_failure': await receipt_probe(True)}, ensure_ascii=False, indent=2))

asyncio.run(main())
