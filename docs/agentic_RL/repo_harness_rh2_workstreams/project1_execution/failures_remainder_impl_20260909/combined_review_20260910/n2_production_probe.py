"""N2 生产控制流探针：真实 queue/manager + frozen delta + 正式 grader profile，Docker 通道为替身。"""
from __future__ import annotations
import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path.cwd()
sys.path[:0] = [str(ROOT / 'tests/grading'), str(ROOT / 'tests'), str(ROOT / 'tests/adapters')]
from test_b4_frozen_delta import _delta
from test_w3b_grader_profile_unit import ProfileGraderFakeDocker
from grading_fixtures import make_fixture_spec
from sandbox_test_support import make_grader_profile
from repoharness2.grading.manager import SWEGradingManager, GradingManagerConfig, ExecResult
from repoharness2.grading.queue import GradingQueue, GradingQueueConfig
from repoharness2.adapters.slime.sandbox_profile import script_id_of

BASE = 'a' * 40
DIGEST = 'sha256:' + '1' * 64
RESET = 'error during connect: Post "http://%2Fvar%2Frun%2Fdocker.sock/v1.45/containers/create": read: connection reset by peer'
TLS = 'Error response from daemon: Get "https://registry-1.docker.io/v2/": net/http: TLS handshake timeout'


def inputs():
    return make_fixture_spec(BASE, 'fake-image:v1', checkout_mode='image_embedded', image_manifest_digest=DIGEST), _delta([])


class Channel:
    def __init__(self, mode):
        self.mode = mode
        self.fake = ProfileGraderFakeDocker(base_commit=BASE, repo_digests=('docker.io/fake/img@' + DIGEST,))
        self.calls = []
        self.created = []
        self.live = set()
        self.rm = []
        self.cancelled = []
        self.hang_entered = asyncio.Event()
        self.release = asyncio.Event()
        self.pull_calls = 0
        self.on_retry = None

    async def hang(self, phase):
        self.hang_entered.set()
        try:
            await self.release.wait()
        except asyncio.CancelledError:
            self.cancelled.append(phase)
            raise

    async def __call__(self, *args, input_bytes=None):
        self.calls.append(args)
        if args[0] == 'run':
            name = args[args.index('--name') + 1]
            self.created.append(name)
            self.live.add(name)
            if self.mode == 'two_run_reply_losses':
                return ExecResult(1, '', RESET)
            if self.mode == 'run_deadline_reply_loss':
                await self.hang('container_start')
            if self.mode == 'fatal_while_pull' and self.on_retry:
                self.on_retry()
        if args[0] == 'rm':
            self.rm.append(args[-1])
            self.live.discard(args[-1])
        if self.mode == 'fatal_while_pull' and args[0] == 'pull':
            self.pull_calls += 1
            if self.pull_calls == 1:
                await self.hang('first_pull')
                return ExecResult(1, '', TLS)
        if self.mode == 'digest_inspect_hang' and args[0] == 'inspect' and '{{.Image}}' in args:
            await self.hang('image_ref_inspect')
        if self.mode == 'profile_init_hang' and args[0] == 'exec' and script_id_of(args[-1]) == 'grader-trusted-init':
            await self.hang('grader_trusted_init')
        if self.mode == 'peak_read_after_deadline':
            if args[0] == 'exec' and 'rev-parse HEAD' in args[-1]:
                await self.hang('env_reset')
            if args[0] == 'exec' and 'memory.peak' in args[-1]:
                await self.hang('peak_memory_after_deadline')
        return await self.fake(*args, input_bytes=input_bytes)


def make_manager(channel):
    return SWEGradingManager(GradingManagerConfig(cleanup_timeout_seconds=1, sandbox_profile=make_grader_profile()), docker=channel)


async def completed_case(mode):
    channel = Channel(mode)
    manager = make_manager(channel)
    queue = GradingQueue(manager, GradingQueueConfig(concurrency=1, queue_size=2))
    await queue.start()
    spec, source = inputs()
    report = await asyncio.wait_for(queue.submit(trajectory_id='exec_1', workspace=None, spec=spec, frozen_delta=source,
                                                deadline_monotonic=time.monotonic() + (0.1 if mode == 'run_deadline_reply_loss' else 5)), 3)
    await queue.close()
    close = await manager.close()
    out = dict(case=mode, report_outcome=report.outcome, report_detail=report.infra_failure_detail,
               created=channel.created, removed=channel.rm, simulated_live_after_close=sorted(channel.live),
               records=[dict(name=r.name, removed=r.removed) for r in manager.container_records],
               manager_close=close, cancelled=channel.cancelled, regrade_events=len(manager.regrade_events),
               queue_active=queue.active_grading_count)
    if mode == 'control':
        assert report.outcome == 'resolved' and not channel.live
    elif mode == 'two_run_reply_losses':
        assert len(channel.created) == 2 and len(channel.live) == 1 and close['containers_open'] == []
    elif mode == 'run_deadline_reply_loss':
        assert report.infra_failure_detail == 'grading_deadline_exhausted:container_start'
        assert channel.live and not manager.container_records and close['containers_open'] == []
    return out


async def hung_case(mode):
    channel = Channel(mode)
    manager = make_manager(channel)
    queue = GradingQueue(manager, GradingQueueConfig(concurrency=1, queue_size=2))
    await queue.start()
    spec, source = inputs()
    submitter = asyncio.create_task(queue.submit(trajectory_id='exec_1', workspace=None, spec=spec, frozen_delta=source,
                                               deadline_monotonic=time.monotonic() + 0.1))
    await asyncio.wait_for(channel.hang_entered.wait(), 2)
    await asyncio.sleep(0.25)
    out = dict(case=mode, elapsed_since_hang_seconds=0.25, work_budget_seconds=0.1,
               submitter_done=submitter.done(), queue_active=queue.active_grading_count,
               simulated_live_before_forced_close=sorted(channel.live), removed_before_forced_close=list(channel.rm),
               cancelled_before_forced_close=list(channel.cancelled))
    assert queue.active_grading_count == 1 and not submitter.done() and not channel.rm
    # 仅取消提交者：真实 worker 仍在独立 task 里等待，故随后显式关闭 queue 来回收探针。
    submitter.cancel()
    await asyncio.gather(submitter, return_exceptions=True)
    out['queue_active_after_submitter_cancel'] = queue.active_grading_count
    await asyncio.wait_for(queue.close(drain=False), 2)
    out['manager_close'] = await manager.close()
    out['cancelled_after_forced_close'] = channel.cancelled
    out['simulated_live_after_forced_close'] = sorted(channel.live)
    return out


async def fatal_case():
    import pytest
    from test_w5a_shutdown_chain import _assemble_service, FAST
    from repoharness2.adapters.slime import bringup
    from repoharness2.adapters.slime.async_worker import FatalExecutionInfrastructureError
    from dataclasses import replace
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(bringup, 'sandbox_profile_enabled', lambda: False)
        service, _ = _assemble_service(Path('/tmp/rh2_n2_review_06dd7c06/fatal_service'), mp,
                                      timeouts=replace(FAST, inflight_grace=0.05, grading_drain=2.0))
        channel = Channel('fatal_while_pull')
        channel.fake.image_present = False
        manager = make_manager(channel)
        queue = GradingQueue(manager, GradingQueueConfig(concurrency=1, queue_size=2), fatal_sink=service.dispatch_run_fatal)
        service.grading_manager, service.grading_queue = manager, queue
        await queue.start()
        service._queue_started = True
        spec, source = inputs()
        retried_state = []
        channel.on_retry = lambda: retried_state.append(dict(fatal_seen=len(service.lifecycle.fatal_seen),
            accepting=service.lifecycle.accepting, grading_open=service.lifecycle.grading_open,
            queue_closing=queue._closing, manager_closed=manager.closed))
        submitter = asyncio.create_task(service._grading_submit(trajectory_id='exec_1', workspace=None, spec=spec,
                                                               frozen_delta=source, deadline_monotonic=time.monotonic() + 5))
        await asyncio.wait_for(channel.hang_entered.wait(), 2)
        assert service.dispatch_run_fatal(FatalExecutionInfrastructureError('probe_fatal', '探针首因'))
        await asyncio.sleep(0.1)
        channel.release.set()
        report = await asyncio.wait_for(submitter, 2)
        shutdown = await asyncio.wait_for(service._close_task, 5)
        assert retried_state and retried_state[0]['fatal_seen'] == 1 and not retried_state[0]['grading_open']
        return dict(case='fatal_while_pull', pull_calls=channel.pull_calls, state_when_new_container_started=retried_state,
                    report_outcome=report.outcome, regrade_events=len(manager.regrade_events),
                    shutdown_ok=shutdown.ok, shutdown_first_cause=shutdown.first_cause)


async def main():
    results = []
    for case in ['control', 'two_run_reply_losses', 'run_deadline_reply_loss']:
        results.append(await completed_case(case))
    for case in ['digest_inspect_hang', 'profile_init_hang', 'peak_read_after_deadline']:
        results.append(await hung_case(case))
    results.append(await fatal_case())
    Path(__file__).with_name('n2_production_probe_result.json').write_text(json.dumps(results, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    asyncio.run(main())
