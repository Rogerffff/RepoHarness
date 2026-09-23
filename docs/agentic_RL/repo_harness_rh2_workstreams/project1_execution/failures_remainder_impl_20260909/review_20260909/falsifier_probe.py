import asyncio, json, sys, time
from pathlib import Path
root = next(p for p in Path(__file__).resolve().parents if (p / 'rh2/pyproject.toml').is_file())
sys.path[:0] = [str(root / 'rh2/src'), str(root / 'rh2/tests/grading')]
from grading_fixtures import FakeWorkspace, GOOD_PATCH, make_fixture_spec
from repoharness2.grading.manager import SWEGradingManager, GradingManagerConfig, ExecResult, _ContainerRecord
from repoharness2.grading.queue import GradingQueue, GradingQueueConfig

async def main():
    entered, release = asyncio.Event(), asyncio.Event()
    calls = []
    async def blocked_docker(*args, **kwargs):
        calls.append(args[0])
        if args[:2] == ('image', 'inspect'):
            entered.set()
            await release.wait()
        return ExecResult(1, '', 'Cannot connect to the Docker daemon')
    manager = SWEGradingManager(docker=blocked_docker)
    queue = GradingQueue(manager, GradingQueueConfig(concurrency=1, queue_size=1))
    await queue.start()
    submit = asyncio.create_task(queue.submit(trajectory_id='probe', workspace=FakeWorkspace(GOOD_PATCH), spec=make_fixture_spec('a'*40, 'fake-image:v1', checkout_mode='image_embedded')))
    await entered.wait()
    await asyncio.sleep(0.03)
    pending = not submit.done()
    try:
        await asyncio.wait_for(submit, timeout=0.01)
    except TimeoutError:
        pass
    active_after_caller_timeout = queue.active_grading_count
    calls_at_timeout = list(calls)
    release.set()
    await asyncio.sleep(0.01)
    await queue.close()
    print(json.dumps({'probe':'queue_deadline_boundary', 'pending_at_image_inspect_30ms':pending, 'active_worker_after_submitter_timeout':active_after_caller_timeout, 'docker_calls_at_submitter_timeout':calls_at_timeout, 'docker_call_sequence':calls}, ensure_ascii=False))
    async def stopped_docker(*args, **kwargs):
        if args[0] == 'rm':
            return ExecResult(1, '', 'removal of container failed')
        if args[0] == 'inspect':
            return ExecResult(0, 'false\n', '')
        raise AssertionError(args)
    manager2 = SWEGradingManager(GradingManagerConfig(cleanup_timeout_seconds=1), docker=stopped_docker)
    temporary = _ContainerRecord(name='temporary-grader', trajectory_id='probe', created_epoch=time.time(), created_monotonic=time.monotonic())
    await manager2._close_container_scope(temporary)
    closed = await manager2.close()
    print(json.dumps({'probe':'temporary_record_stopped', 'temporary_removed':temporary.removed, 'manager_record_count':len(manager2.container_records), 'close_containers_open':closed['containers_open'], 'cleanup_failure_count':len(closed['cleanup_failures'])}, ensure_ascii=False))

asyncio.run(main())
