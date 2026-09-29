"""R2 最终窄复核：生产 queue/manager + formal profile + frozen delta；只替换 Docker I/O。"""
from __future__ import annotations
import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[7] / 'rh2'
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tests/grading'), str(ROOT / 'tests')]
from test_b4_frozen_delta import _delta
from test_w3b_grader_profile_unit import ProfileGraderFakeDocker
from grading_fixtures import make_fixture_spec
from sandbox_test_support import make_grader_profile
from repoharness2.grading.manager import (
    ExecResult, GradingManagerConfig, GradingScopeTerminationError,
    SandboxProfileViolation, SWEGradingManager,
)
from repoharness2.grading.queue import GradingQueue, GradingQueueConfig

BASE = 'a' * 40
DIGEST = 'sha256:' + '1' * 64
RESET = 'error during connect: Post "http://%2Fvar%2Frun%2Fdocker.sock/v1.45/containers/create": read: connection reset by peer'


class Docker:
    def __init__(self, *, branch='normal', mode='fast'):
        self.fake = ProfileGraderFakeDocker(base_commit=BASE, repo_digests=('docker.io/fake/img@' + DIGEST,))
        if branch == 'init_failure':
            self.fake.profile_fake.trusted_init_fail = True
        elif branch == 'check_violation':
            self.fake.profile_fake.grader_probe_overrides = {'UID': '0'}
        self.mode = mode
        self.created = []
        self.live = set()
        self.removed_calls = []
        self.cancelled = []
        self.rm_entered = asyncio.Event()
        self.rm_started = None
        self.rm_cancel_elapsed = None

    async def __call__(self, *args, input_bytes=None):
        if args[0] == 'run':
            name = args[args.index('--name') + 1]
            self.created.append(name)
            self.live.add(name)
            if self.mode == 'two_reply_losses':
                return ExecResult(1, '', RESET)
            if self.mode == 'start_deadline':
                try:
                    await asyncio.Event().wait()
                except asyncio.CancelledError:
                    self.cancelled.append('container_start')
                    raise
        if args[0] == 'rm':
            self.removed_calls.append(args[-1])
            if self.mode == 'slow_rm' and len(self.removed_calls) == 1:
                self.rm_started = time.monotonic()
                self.rm_entered.set()
                try:
                    await asyncio.Event().wait()  # 无人工放行；必须由生产独立清理期限取消
                except asyncio.CancelledError:
                    self.cancelled.append('first_rm')
                    self.rm_cancel_elapsed = time.monotonic() - self.rm_started
                    raise
            self.live.discard(args[-1])
        return await self.fake(*args, input_bytes=input_bytes)


def assemble(docker):
    manager = SWEGradingManager(
        GradingManagerConfig(cleanup_timeout_seconds=1, sandbox_profile=make_grader_profile()), docker=docker,
    )
    fatals = []
    queue = GradingQueue(manager, GradingQueueConfig(concurrency=1, queue_size=2), fatal_sink=fatals.append)
    spec = make_fixture_spec(BASE, 'fake-image:v1', checkout_mode='image_embedded', image_manifest_digest=DIGEST)
    return manager, queue, fatals, spec, _delta([])


async def profile_failure(branch, mode, *, cancel_submitter=False):
    docker = Docker(branch=branch, mode=mode)
    manager, queue, fatals, spec, delta = assemble(docker)
    await queue.start()
    workers = list(queue._workers)
    started = time.monotonic()
    submitter = asyncio.create_task(queue.submit(
        trajectory_id='exec_r2', workspace=None, spec=spec, frozen_delta=delta,
        deadline_monotonic=started + .1,
    ))
    received = None
    if cancel_submitter:
        await asyncio.wait_for(docker.rm_entered.wait(), 2)
        submitter.cancel()  # 只撤提交者，worker 仍独立受原清理预算约束
        await asyncio.gather(submitter, return_exceptions=True)
        await asyncio.wait_for(queue._queue.join(), 3)
        assert len(fatals) == 1, fatals
        received = fatals[0]
    else:
        try:
            await asyncio.wait_for(submitter, 3)
        except (SandboxProfileViolation, GradingScopeTerminationError) as exc:
            received = exc
        assert received is not None, '预期 prelaunch 失败，却得到正常评分'
        assert not fatals, '有等待提交者时应走原 future 异常通道'
        await asyncio.wait_for(queue._queue.join(), 1)
    elapsed = time.monotonic() - started
    expected = GradingScopeTerminationError if mode == 'slow_rm' else SandboxProfileViolation
    assert type(received) is expected, type(received)
    assert queue.active_grading_count == 0 and manager.regrade_total == 0
    assert len(docker.created) == 1 and len(manager.container_records) == 1
    record = manager.container_records[0]
    if mode == 'slow_rm':
        assert not record.removed and docker.live == {record.name}
        assert .9 <= docker.rm_cancel_elapsed < 2.5, docker.rm_cancel_elapsed
        assert isinstance(received.__context__, SandboxProfileViolation)
        assert any('cleanup_budget_exhausted' in f for f in manager.cleanup_failures)
    else:
        assert record.removed and not docker.live
        reason = 'grader_trusted_init_failed' if branch == 'init_failure' else 'grader_sandbox_profile_violation'
        assert reason in str(received), str(received)
    out = {
        'case': f'{branch}_{mode}' + ('_submitter_cancelled' if cancel_submitter else ''),
        'work_budget_seconds': .1, 'cleanup_budget_seconds': 1,
        'elapsed_seconds': round(elapsed, 3),
        'exception_type': type(received).__name__, 'exception': str(received),
        'context_type': type(received.__context__).__name__ if received.__context__ else None,
        'fatal_sink_types': [type(e).__name__ for e in fatals],
        'queue_active_after_cleanup': queue.active_grading_count,
        'queue_join_returned': True, 'created': len(docker.created),
        'removed_before_close': record.removed, 'live_before_close': sorted(docker.live),
        'rm_calls_before_close': len(docker.removed_calls),
        'rm_cancel_elapsed_seconds': round(docker.rm_cancel_elapsed, 3) if docker.rm_cancel_elapsed else None,
        'cancelled': docker.cancelled, 'regrade_total': manager.regrade_total,
        'cleanup_failures': list(manager.cleanup_failures),
    }
    await asyncio.wait_for(queue.close(drain=True), 1)
    assert all(w.done() for w in workers)
    out['worker_tasks_finished_after_normal_close'] = True
    out['manager_close'] = await asyncio.wait_for(manager.close(), 2)
    out['rm_calls_after_close'] = len(docker.removed_calls)
    assert all(r.removed for r in manager.container_records) and not docker.live
    assert not out['manager_close']['containers_open']
    return out


async def control(mode):
    docker = Docker(mode=mode)
    manager, queue, fatals, spec, delta = assemble(docker)
    await queue.start()
    started = time.monotonic()
    report = await asyncio.wait_for(queue.submit(
        trajectory_id='exec_control', workspace=None, spec=spec, frozen_delta=delta,
        deadline_monotonic=started + (.1 if mode == 'start_deadline' else 3),
    ), 4)
    assert not fatals and queue.active_grading_count == 0
    assert all(r.removed for r in manager.container_records) and not docker.live
    assert report.outcome == ('resolved' if mode == 'fast' else 'failed_to_grade')
    if mode == 'two_reply_losses':
        assert len(docker.created) == 2 and len(docker.removed_calls) == 2 and manager.regrade_total == 1
    if mode == 'start_deadline':
        assert report.infra_failure_detail == 'grading_deadline_exhausted:container_start'
        assert len(docker.created) == 1 and docker.cancelled == ['container_start']
    out = {
        'case': 'control_' + mode, 'outcome': report.outcome, 'detail': report.infra_failure_detail,
        'elapsed_seconds': round(time.monotonic() - started, 3),
        'created': len(docker.created), 'removed': len(docker.removed_calls),
        'records_removed': [r.removed for r in manager.container_records],
        'queue_active': queue.active_grading_count, 'regrade_total': manager.regrade_total,
    }
    await queue.close()
    out['manager_close'] = await manager.close()
    return out


async def main():
    results = [await control(mode) for mode in ('fast', 'start_deadline', 'two_reply_losses')]
    for branch in ('init_failure', 'check_violation'):
        results.append(await profile_failure(branch, 'fast'))
        results.append(await profile_failure(branch, 'slow_rm'))
        results.append(await profile_failure(branch, 'slow_rm', cancel_submitter=True))
    output = {'head': 'f7521d94ee25a6f6720e7b7994a4a29ea052db70', 'case_count': len(results), 'results': results}
    target = Path(__file__).with_name('r2_probe_result.json')
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(target.read_text())


if __name__ == '__main__':
    asyncio.run(main())
