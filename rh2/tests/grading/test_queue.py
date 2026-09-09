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


# ---------------------------------------------------------------------------
# Codex 联合审查 R5：取消后 scope fatal 的独立接收者 + 关闭中 worker 退出
# ---------------------------------------------------------------------------


class _ScopeFailingManager:
    """grade() 先等 release；提交者取消 / 关闭时按 kind 决定收口异常。"""

    def __init__(self, kind: str):
        self.kind = kind
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.calls = 0

    async def grade(self, **kw):
        from repoharness2.grading.manager import GradingScopeTerminationError

        self.calls += 1
        self.entered.set()
        try:
            await self.release.wait()
        except asyncio.CancelledError:
            if self.kind == "scope_error_on_cancel":
                # 真实 grade() 的 finally：有界收口失败 → ScopeError 替换在途 CancelledError
                raise GradingScopeTerminationError("grading_scope_termination_failed", "closure failed") from None
            raise
        if self.kind == "scope_error":
            raise GradingScopeTerminationError("grading_scope_termination_failed", "still running after closure")
        if self.kind == "plain_error":
            raise RuntimeError("plain grading failure")
        return "report"


async def test_scope_fatal_after_submitter_cancelled_reaches_fatal_sink():
    """提交者取消 → future 已 done；worker 稍后的 GradingScopeTerminationError 经 fatal_sink 到达服务
    （修前：set_exception 被跳过，fatal 无人接收，halt=0）；worker 仍活着、队列可继续；不通知两次。"""

    sink: list = []
    manager = _ScopeFailingManager("scope_error")
    queue = GradingQueue(manager, GradingQueueConfig(concurrency=1, queue_size=1), fatal_sink=sink.append)
    await queue.start()
    submitter = asyncio.create_task(queue.submit(trajectory_id="t1", workspace=None, spec=_spec()))
    await asyncio.wait_for(manager.entered.wait(), 1)
    submitter.cancel()
    with pytest.raises(asyncio.CancelledError):
        await submitter
    manager.release.set()
    await asyncio.wait_for(queue._queue.join(), 1)
    assert [type(e).__name__ for e in sink] == ["GradingScopeTerminationError"]
    assert len(queue.out_of_band_fatals) == 1
    assert not queue._workers[0].done()  # worker 仍在
    await asyncio.wait_for(queue.close(), 1)


async def test_plain_error_after_submitter_cancelled_is_not_escalated():
    """对照：普通 task-local 评分故障在提交者取消后只留在队列隔离语义内，不经 fatal_sink。"""

    sink: list = []
    manager = _ScopeFailingManager("plain_error")
    queue = GradingQueue(manager, GradingQueueConfig(concurrency=1, queue_size=1), fatal_sink=sink.append)
    await queue.start()
    submitter = asyncio.create_task(queue.submit(trajectory_id="t2", workspace=None, spec=_spec()))
    await asyncio.wait_for(manager.entered.wait(), 1)
    submitter.cancel()
    with pytest.raises(asyncio.CancelledError):
        await submitter
    manager.release.set()
    await asyncio.wait_for(queue._queue.join(), 1)
    assert sink == [] and queue.out_of_band_fatals == []
    await asyncio.wait_for(queue.close(), 1)


async def test_close_without_drain_completes_when_grade_finally_raises_scope_error():
    """close(drain=False) 取消 worker，grade() 收口以 ScopeError 替换 CancelledError → worker 把它交给仍在
    等待的提交者后按关闭标志退出，close 在有限时间内完成（修前：worker 回到 while True，close 挂住）。"""

    from repoharness2.grading.manager import GradingScopeTerminationError

    sink: list = []
    manager = _ScopeFailingManager("scope_error_on_cancel")
    queue = GradingQueue(manager, GradingQueueConfig(concurrency=1, queue_size=1), fatal_sink=sink.append)
    await queue.start()
    submitter = asyncio.create_task(queue.submit(trajectory_id="t3", workspace=None, spec=_spec()))
    await asyncio.wait_for(manager.entered.wait(), 1)
    await asyncio.wait_for(queue.close(drain=False), 2)  # 修前此处永久等待
    with pytest.raises(GradingScopeTerminationError):
        await submitter  # 提交者仍在等：异常经 future 交付（由编排转 fatal），不走 sink
    assert sink == [] and queue._workers == []


class _TwoPhaseManager:
    """第一条评分进入后阻塞到 release；用于制造"一条在评、一条排队"的积压。"""

    def __init__(self):
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.calls: list[str] = []

    async def grade(self, **kwargs):
        self.calls.append(kwargs["trajectory_id"])
        if len(self.calls) == 1:
            self.entered.set()
            await self.release.wait()
        return f"report:{kwargs['trajectory_id']}"


async def _backlog(manager):
    queue = GradingQueue(manager, GradingQueueConfig(concurrency=1, queue_size=2))
    await queue.start()
    first = asyncio.create_task(queue.submit(trajectory_id="first", workspace=None, spec=_spec()))
    await asyncio.wait_for(manager.entered.wait(), 1)
    second = asyncio.create_task(queue.submit(trajectory_id="second", workspace=None, spec=_spec()))
    while queue.queue_depth != 1:
        await asyncio.sleep(0)
    return queue, first, second


async def test_close_with_drain_keeps_consuming_the_backlog():
    """R5-F1（Codex 修后复核）：close(drain=True) 期间 worker 必须继续消费已接收条目——关闭标志在排空之后、
    撤 worker 之前才置位（修前：一开始就置位，worker 做完手头一条即退出，第二条无人 task_done，join 永远等不到）。"""

    manager = _TwoPhaseManager()
    queue, first, second = await _backlog(manager)
    closing = asyncio.create_task(queue.close(drain=True))
    await asyncio.sleep(0.02)
    assert not closing.done() and queue._closing is False and not queue._workers[0].done()
    manager.release.set()
    await asyncio.wait_for(closing, 1)  # 修前：永久等待
    assert manager.calls == ["first", "second"]
    assert await first == "report:first" and await second == "report:second"
    assert queue.queue_depth == 0 and queue._workers == [] and queue._closing is True


async def test_close_with_drain_consumes_backlog_whose_submitters_were_cancelled():
    """R5-F1 对照：服务先取消在飞执行 → 两个提交者都不在了，已入队条目仍在；drain 仍要消费完再撤 worker。"""

    manager = _TwoPhaseManager()
    queue, first, second = await _backlog(manager)
    first.cancel()
    second.cancel()
    await asyncio.gather(first, second, return_exceptions=True)
    closing = asyncio.create_task(queue.close(drain=True))
    await asyncio.sleep(0.02)
    assert not closing.done() and queue.queue_depth == 1
    manager.release.set()
    await asyncio.wait_for(closing, 1)
    assert manager.calls == ["first", "second"] and queue.queue_depth == 0 and queue._workers == []
