"""N2 R1/R2/R4 一次聚焦复核：真实 queue/manager、冻结产物、正式 profile，Docker 故障注入。"""
from __future__ import annotations
import asyncio
import importlib.util
import json
import time
from pathlib import Path

old_path = Path(__file__).resolve().parent.parent / 'n2_production_probe.py'
spec = importlib.util.spec_from_file_location('previous_probe', old_path)
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
from repoharness2.grading.manager import GradingScopeTerminationError


class Channel(previous.Channel):
    async def __call__(self, *args, input_bytes=None):
        if self.mode == 'second_run_deadline':
            if args[0] == 'run':
                name = args[args.index('--name') + 1]
                self.calls.append(args)
                self.created.append(name)
                self.live.add(name)
                if len(self.created) == 1:
                    return previous.ExecResult(1, '', previous.RESET)
                await self.hang('second_container_start')
        if self.mode == 'digest_second_inspect_hang' and args[0] == 'image' and 'RepoDigests' in ' '.join(args):
            await self.hang('image_digest_inspect')
        if self.mode == 'prelaunch_probe_hang' and args[0] == 'exec' and previous.script_id_of(args[-1]) == 'grader-prelaunch-probe':
            await self.hang('grader_prelaunch_check')
        if self.mode == 'cleanup_consumes_work_budget':
            if args[0] == 'run':
                name = args[args.index('--name') + 1]
                self.calls.append(args)
                self.created.append(name)
                self.live.add(name)
                return previous.ExecResult(1, '', previous.RESET)
            if args[0] == 'rm':
                await asyncio.sleep(0.15)
        if self.mode == 'prelaunch_violation_rm_hang' and args[0] == 'rm' and not self.rm:
            # 第一次 rm 挂住，不改变 daemon 端对象；强制取消后下一次收口正常，便于探针退出。
            self.rm.append(args[-1])
            await self.hang('prelaunch_unbounded_remove')
        if self.mode == 'run_cancel_cleanup_unknown':
            if args[0] == 'run':
                name = args[args.index('--name') + 1]
                self.calls.append(args)
                self.created.append(name)
                self.live.add(name)
                await self.hang('container_start')
            if args[0] == 'rm':
                self.rm.append(args[-1])
                return previous.ExecResult(1, '', 'Cannot connect to the Docker daemon')
            if args[0] == 'inspect' and '{{.State.Running}}' in args:
                return previous.ExecResult(1, '', 'Cannot connect to the Docker daemon')
        return await super().__call__(*args, input_bytes=input_bytes)


def manager_for(channel, stop_requested=None):
    return previous.SWEGradingManager(
        previous.GradingManagerConfig(cleanup_timeout_seconds=1, sandbox_profile=previous.make_grader_profile()),
        docker=channel, stop_requested=stop_requested,
    )


async def bounded_case(mode):
    channel = Channel(mode)
    manager = manager_for(channel)
    queue = previous.GradingQueue(manager, previous.GradingQueueConfig(concurrency=1, queue_size=2))
    await queue.start()
    spec, source = previous.inputs()
    started = time.monotonic()
    budget = 2 if mode in ('control', 'two_run_reply_losses') else .1
    report = await asyncio.wait_for(queue.submit(trajectory_id='exec_1', workspace=None, spec=spec, frozen_delta=source,
                                                deadline_monotonic=started + budget), 3)
    elapsed = time.monotonic() - started
    result = dict(case=mode, elapsed_seconds=round(elapsed, 3), outcome=report.outcome,
                  detail=report.infra_failure_detail, created=len(channel.created), removed=len(channel.rm),
                  live=sorted(channel.live), cancelled=channel.cancelled, queue_active=queue.active_grading_count,
                  regrade_total=manager.regrade_total, records=[r.removed for r in manager.container_records],
                  peak_reads=sum(a[0] == 'exec' and 'memory.peak' in a[-1] for a in channel.calls))
    assert not channel.live and queue.active_grading_count == 0 and all(r.removed for r in manager.container_records)
    if mode == 'control':
        assert report.outcome == 'resolved'
    else:
        assert report.outcome == 'failed_to_grade'
    if mode in ('two_run_reply_losses', 'second_run_deadline'):
        assert len(channel.created) == 2
    if mode == 'cleanup_consumes_work_budget':
        assert len(channel.created) == 1 and elapsed >= budget and manager.regrade_total == 0
    if mode == 'peak_read_after_deadline':
        assert result['peak_reads'] == 0
    await queue.close()
    result['close'] = await manager.close()
    return result


async def cancel_case(mode):
    channel = Channel(mode)
    manager = manager_for(channel)
    fatals = []
    queue = previous.GradingQueue(manager, previous.GradingQueueConfig(concurrency=1, queue_size=2), fatal_sink=fatals.append)
    await queue.start()
    spec, source = previous.inputs()
    submitter = asyncio.create_task(queue.submit(trajectory_id='exec_1', workspace=None, spec=spec, frozen_delta=source,
                                               deadline_monotonic=time.monotonic() + 5))
    await asyncio.wait_for(channel.hang_entered.wait(), 2)
    submitter.cancel()
    await asyncio.gather(submitter, return_exceptions=True)
    # 生产的 force-close 撤真实 worker，容器清理完成或 typed fatal 必须到达独立接收者。
    await asyncio.wait_for(queue.close(drain=False), 2)
    out = dict(case=mode, created=len(channel.created), removed_calls=len(channel.rm), live=sorted(channel.live),
               records=[r.removed for r in manager.container_records], queue_active=queue.active_grading_count,
               fatals=[type(e).__name__ for e in fatals], cancelled=channel.cancelled)
    assert queue.active_grading_count == 0
    if mode == 'run_cancel_cleanup_unknown':
        assert len(fatals) == 1 and isinstance(fatals[0], GradingScopeTerminationError)
        assert manager.container_records and not manager.container_records[0].removed
        channel.mode = 'control'
    else:
        assert not channel.live and not fatals and all(r.removed for r in manager.container_records)
    out['close'] = await manager.close()
    return out


async def stop_case():
    import pytest
    from dataclasses import replace
    from test_w5a_shutdown_chain import _assemble_service, FAST
    from repoharness2.adapters.slime import bringup
    from repoharness2.adapters.slime.async_worker import FatalExecutionInfrastructureError
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(bringup, 'sandbox_profile_enabled', lambda: False)
        service, _ = _assemble_service(Path('/tmp/rh2_n2_followup_0313991c/fatal'), mp,
                                      timeouts=replace(FAST, inflight_grace=.05, grading_drain=2.0))
        channel = Channel('fatal_while_pull')
        channel.fake.image_present = False
        # 与 BringupService.__init__ 的生产接线一致，替换 manager 时保留该谓词。
        manager = manager_for(channel, service._grading_stop_requested)
        queue = previous.GradingQueue(manager, previous.GradingQueueConfig(concurrency=1, queue_size=2), fatal_sink=service.dispatch_run_fatal)
        service.grading_manager, service.grading_queue = manager, queue
        await queue.start()
        service._queue_started = True
        spec, source = previous.inputs()
        submitter = asyncio.create_task(service._grading_submit(trajectory_id='exec_1', workspace=None, spec=spec,
                                                               frozen_delta=source, deadline_monotonic=time.monotonic() + 5))
        await asyncio.wait_for(channel.hang_entered.wait(), 2)
        service.dispatch_run_fatal(FatalExecutionInfrastructureError('probe_fatal', '探针首因'))
        await asyncio.sleep(.1)
        before = dict(fatal_seen=len(service.lifecycle.fatal_seen), accepting=service.lifecycle.accepting,
                      grading_open=service.lifecycle.grading_open, manager_closed=manager.closed)
        channel.release.set()
        report = await asyncio.wait_for(submitter, 2)
        shutdown = await asyncio.wait_for(service._close_task, 5)
        assert channel.pull_calls == 1 and not channel.created and manager.regrade_total == 0
        assert report.outcome == 'failed_to_grade' and len(manager.regrade_declined) == 1 and not shutdown.ok
        return dict(case='fatal_while_pull', before_release=before, outcome=report.outcome, pulls=channel.pull_calls,
                    created=len(channel.created), regrade_declined=manager.regrade_declined, shutdown_ok=shutdown.ok)


async def prelaunch_remove_seam():
    channel = Channel('prelaunch_violation_rm_hang')
    channel.fake.profile_fake.trusted_init_fail = True
    manager = manager_for(channel)
    queue = previous.GradingQueue(manager, previous.GradingQueueConfig(concurrency=1, queue_size=2))
    await queue.start()
    spec, source = previous.inputs()
    budget = .1
    started = time.monotonic()
    submitter = asyncio.create_task(queue.submit(trajectory_id='exec_1', workspace=None, spec=spec, frozen_delta=source,
                                               deadline_monotonic=started + budget))
    await asyncio.wait_for(channel.hang_entered.wait(), 2)
    await asyncio.sleep(1.25)
    out = dict(case='prelaunch_violation_rm_hang', work_budget=budget, cleanup_budget=1,
               elapsed_seconds=round(time.monotonic() - started, 3), submitter_done=submitter.done(),
               queue_active=queue.active_grading_count, live=sorted(channel.live),
               records=[dict(name=r.name, removed=r.removed) for r in manager.container_records],
               cleanup_failures=list(manager.cleanup_failures))
    assert not submitter.done() and queue.active_grading_count == 1 and channel.live
    submitter.cancel()
    await asyncio.gather(submitter, return_exceptions=True)
    await asyncio.wait_for(queue.close(drain=False), 2)
    out['after_forced_close'] = await manager.close()
    return out


async def main():
    results = []
    for mode in ('control', 'two_run_reply_losses', 'run_deadline_reply_loss', 'second_run_deadline',
                 'digest_inspect_hang', 'digest_second_inspect_hang', 'profile_init_hang', 'prelaunch_probe_hang',
                 'peak_read_after_deadline', 'cleanup_consumes_work_budget'):
        results.append(await bounded_case(mode))
    for mode in ('run_deadline_reply_loss', 'profile_init_hang', 'prelaunch_probe_hang', 'run_cancel_cleanup_unknown'):
        results.append(await cancel_case(mode))
    results.append(await stop_case())
    results.append(await prelaunch_remove_seam())
    path = Path(__file__).with_name('n2_followup_result.json')
    path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n')
    print(path.read_text())


if __name__ == '__main__':
    asyncio.run(main())
