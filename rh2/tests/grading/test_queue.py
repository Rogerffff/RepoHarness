"""GradingQueue 单测：F5 默认参数（并发 4/队列 8）、P11 有界 + 反压事件、等待计时。

用 SlowFakeManager 桩（grade 睡固定时长后回显参数），不碰 docker。
"""

import asyncio

import pytest
from grading_fixtures import (
    GOOD_PATCH,
    FakeDocker,
    FakeWorkspace,
    SlowFakeManager,
    make_fixture_spec,
)

from repoharness2.grading.manager import GradingManagerConfig, SWEGradingManager
from repoharness2.grading.queue import (
    BACKPRESSURE_REASON_CODE,
    BackpressureEvent,
    GradingQueue,
    GradingQueueConfig,
)

BASE = "a" * 40


def _spec():
    return make_fixture_spec(BASE, "fake-image:v1", checkout_mode="image_embedded")


def test_f5_defaults_and_configurability():
    """F5 用户收紧版：默认并发 4、队列 8；两个参数都可配置且必须为正。"""

    config = GradingQueueConfig()
    assert config.concurrency == 4
    assert config.queue_size == 8
    custom = GradingQueueConfig(concurrency=8, queue_size=16)
    assert (custom.concurrency, custom.queue_size) == (8, 16)
    with pytest.raises(ValueError):
        GradingQueueConfig(concurrency=0)
    with pytest.raises(ValueError):
        GradingQueueConfig(queue_size=-1)


async def test_concurrency_is_bounded():
    manager = SlowFakeManager(grade_delay=0.05)
    queue = GradingQueue(manager, GradingQueueConfig(concurrency=2, queue_size=4))
    async with queue:
        await asyncio.gather(
            *(
                queue.submit(trajectory_id=f"traj_{i}", workspace=FakeWorkspace(), spec=_spec())
                for i in range(6)
            )
        )
    assert manager.max_active_seen <= 2  # 并发上限被信号量（worker 数）钉死
    assert len(manager.grade_calls) == 6


async def test_queue_full_emits_backpressure_event():
    """P11：队列打满 → 产出 BackpressureEvent（EligibilityReport 可直接消费的事实）。"""

    manager = SlowFakeManager(grade_delay=0.08)
    queue = GradingQueue(manager, GradingQueueConfig(concurrency=1, queue_size=1))
    async with queue:
        results = await asyncio.gather(
            *(
                queue.submit(trajectory_id=f"traj_{i}", workspace=FakeWorkspace(), spec=_spec())
                for i in range(4)
            )
        )
    assert len(results) == 4  # block_submitter 策略：反压但不丢请求
    assert queue.events, "队列打满必须产出反压事件"
    event = queue.events[0]
    assert isinstance(event, BackpressureEvent)
    assert event.reason_code == BACKPRESSURE_REASON_CODE
    assert event.policy_applied == "block_submitter"
    assert event.queue_capacity == 1 and event.queue_depth == 1
    assert event.concurrency_limit == 1
    assert event.task_id and event.trajectory_id
    # 事件对象过严格 schema（未知字段拒收 / 时区必须在场）
    BackpressureEvent.model_validate(event.model_dump(mode="json"))
    # 被反压请求的事实旗标已传给 manager（最终落 GradingTimingRecord）
    assert any(call["backpressure_triggered"] for call in manager.grade_calls)


async def test_queue_wait_seconds_measured_from_submit():
    """排队等待计时：后到请求的 queue_wait 必然大于第一批（worker 只有 1 个）。"""

    manager = SlowFakeManager(grade_delay=0.05)
    queue = GradingQueue(manager, GradingQueueConfig(concurrency=1, queue_size=4))
    async with queue:
        first, last = await asyncio.gather(
            queue.submit(trajectory_id="traj_first", workspace=FakeWorkspace(), spec=_spec()),
            queue.submit(trajectory_id="traj_last", workspace=FakeWorkspace(), spec=_spec()),
        )
    assert last["queue_wait_seconds"] >= 0.04  # 至少等完前一条的 grade_delay
    assert last["queue_wait_seconds"] > first["queue_wait_seconds"]
    assert first["queue_depth_at_enqueue"] == 0
    assert last["queue_depth_at_enqueue"] >= 0


async def test_single_failure_does_not_kill_queue():
    """故障域：某条评分抛异常只影响它自己的 future，队列与后续请求照常。"""

    class FlakyManager(SlowFakeManager):
        async def grade(self, **kwargs):
            if kwargs["trajectory_id"] == "traj_bad":
                raise RuntimeError("boom")
            return await super().grade(**kwargs)

    manager = FlakyManager(grade_delay=0.01)
    queue = GradingQueue(manager, GradingQueueConfig(concurrency=2, queue_size=2))
    async with queue:
        bad = queue.submit(trajectory_id="traj_bad", workspace=FakeWorkspace(), spec=_spec())
        with pytest.raises(RuntimeError, match="boom"):
            await bad
        good = await queue.submit(
            trajectory_id="traj_good", workspace=FakeWorkspace(), spec=_spec()
        )
    assert good["trajectory_id"] == "traj_good"


async def test_submit_before_start_rejected():
    queue = GradingQueue(SlowFakeManager())
    with pytest.raises(RuntimeError, match="未启动"):
        await queue.submit(trajectory_id="t", workspace=FakeWorkspace(), spec=_spec())


async def test_queue_with_real_manager_fake_docker_propagates_facts():
    """queue -> 真 manager（FakeDocker）整链：队列事实落进 GradingReport.timings。"""

    fake = FakeDocker(base_commit=BASE)
    manager = SWEGradingManager(GradingManagerConfig(), docker=fake)
    queue = GradingQueue(manager, GradingQueueConfig(concurrency=1, queue_size=1))
    async with queue:
        reports = await asyncio.gather(
            *(
                queue.submit(
                    trajectory_id=f"traj_q{i}",
                    workspace=FakeWorkspace(GOOD_PATCH),
                    spec=_spec(),
                )
                for i in range(3)
            )
        )
    assert all(r.outcome == "resolved" for r in reports)
    assert all(r.timings is not None for r in reports)
    # 至少有一条经历了排队（并发 1，三连发必然串行）
    assert max(r.timings.queue_wait_seconds for r in reports) > 0.0
    if queue.events:  # 打满与否取决于时序，打满了就必须有对应旗标
        assert any(r.timings.backpressure_triggered for r in reports)
