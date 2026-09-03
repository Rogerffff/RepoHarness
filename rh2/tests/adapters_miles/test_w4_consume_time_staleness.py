"""W4（决策包 D2+B v2 B-1/B-2/B-4/B-6；06 计划 §1.5、§3 W4 行）：consume-time staleness 唯一权威接线。

被测对象全部是 miles 集成分支的**真实**对象（RH2_MILES_PATH=reference/miles-rh2-integration）：
`DefaultDataBuffer`（put/get 三分支 + 负 lag/版本缺失 typed fatal + 四终局结构化事件）、
`FullyAsyncRolloutFn`（no-progress 停止规则、drain 计时事件、fatal 经 `call_rollout_function` 传到
driver → `dispose_on_owner_loop` → rh2 关停链首因）、`train_async.py` 的 JIT drain 顺序（源码事实
+ 用真实 rollout fn 的行为模型证明 booked staleness == trainer 消费时刻的真实 lag）。

分组：
  A. buffer 级（合成 formal 组，不挂真实复合 filter）——参数化 N=0/1/2/4；
  B. 真实 fa_formal 链（prepared registry → Rh2MilesGenerateFn → 真实复合 filter）——事件里的
     六字段身份来自真实铸造；
  C. rollout fn 级（W5a 的双 loop 生产拓扑替身）——fatal 通道 / no-progress / drain 顺序；
  D. 常量钉死（miles 侧字面量镜像 == rh2 源码）。
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration_base

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
if str(_HERE.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent))

from w4_helpers import formal_group, read_events  # noqa: E402

THRESHOLDS = (0, 1, 2, 4)


# ---------------------------------------------------------------------------
# 共用装配
# ---------------------------------------------------------------------------


def _buffer(world, **args_over):
    from miles.rollout.fully_async_data_buffer import DataBufferConstructorInput, DefaultDataBuffer

    args_over.setdefault("dynamic_sampling_filter_path", None)
    args = world.mk_miles_args(**args_over)
    recycled: list = []
    buf = DefaultDataBuffer(DataBufferConstructorInput(args=args, unused_handler_fn=recycled.append))
    return buf, recycled


def _entry(world, prompt_group, group):
    from miles.rollout.fully_async_data_buffer import DataBufferInput

    return DataBufferInput(prompt_group=prompt_group, group=group)


@pytest.fixture()
def events_dir(tmp_path, monkeypatch):
    from miles.utils import rh2_event_log

    d = tmp_path / "events"
    monkeypatch.setenv(rh2_event_log.EVENT_DIR_ENV, str(d))
    monkeypatch.setenv(rh2_event_log.RUN_ID_ENV, "w4-run")
    return d


# ===========================================================================
# A. buffer 级：唯一权威判定
# ===========================================================================


@pytest.mark.parametrize("limit", THRESHOLDS)
async def test_exact_threshold_passes_and_one_over_goes_to_handler(world, events_dir, limit):
    """恰等阈值放行（consumed 事件记 staleness=N）；超阈一代交 unused handler（consume_stale 事件带
    oldest/current/staleness/limit），buffer 累计计数同步。"""

    from miles.utils.rh2_event_log import DROP_STAGE_CONSUME_STALE

    buf, recycled = _buffer(world, max_weight_staleness=limit)
    current = 10
    pg_ok, g_ok = formal_group(world, versions_per_member=[[str(current - limit)], [str(current)]], group_index=0, task_id="tA")
    pg_stale, g_stale = formal_group(world, versions_per_member=[[str(current - limit - 1)], [str(current)]], group_index=1, task_id="tB")
    await buf.put(_entry(world, pg_stale, g_stale))
    await buf.put(_entry(world, pg_ok, g_ok))

    got = await buf.get(current_version=current)
    assert got.group is g_ok
    assert recycled == [pg_stale]  # 超阈组本次不回队、不立即重试（B-2 drop：handler 只是被调用）
    assert buf.consumed_total == 1 and buf.drop_totals == {"put_aborted": 0, "dynamic_filter": 0, DROP_STAGE_CONSUME_STALE: 1}
    assert buf.get_metrics()["rollout/fully_async/stale_groups_filtered"] == 1

    [drop] = read_events(events_dir, ("group_filtered",))
    assert drop["drop_stage"] == DROP_STAGE_CONSUME_STALE and drop["reason_code"] == drop["reason"] == "staleness_exceeded"
    assert (drop["oldest_weight_version"], drop["current_weight_version"], drop["staleness"], drop["staleness_limit"]) == (
        current - limit - 1, current, limit + 1, limit)
    assert drop["task_id"] == "tB" and drop["rh2_prompt_group_id"] == "miles_g1" and drop["group_index"] == 1 and drop["formal"] is True
    assert drop["sample_indices"] == [2, 3] and drop["rewards"] == [0.0, 1.0] and drop["run_id"] == "w4-run" and "ts_unix" in drop
    [consumed] = read_events(events_dir, ("group_consumed",))
    assert consumed["staleness"] == limit and consumed["staleness_limit"] == limit and consumed["task_id"] == "tA"
    assert consumed["oldest_weight_version"] == current - limit and consumed["current_weight_version"] == current


@pytest.mark.parametrize("limit", THRESHOLDS)
@pytest.mark.parametrize("claim_formal", [True, False])
async def test_negative_lag_is_accounting_fatal_not_fresh(world, limit, claim_formal):
    """oldest > current（负 lag）不是"新鲜到满足任何阈值"，而是版本账目矛盾：typed fatal，formal 与否都拒。"""

    from miles.rollout.fully_async_data_buffer import DefaultDataBuffer, WeightVersionAccountingError

    buf, recycled = _buffer(world, max_weight_staleness=limit)
    pg, g = formal_group(world, versions_per_member=[["6"], ["7"]], claim_formal=claim_formal)
    assert DefaultDataBuffer._staleness(g, 5) == -1  # 纯算术层仍是负数（get_metrics 观测用，未改）
    await buf.put(_entry(world, pg, g))
    with pytest.raises(WeightVersionAccountingError) as info:
        await buf.get(current_version=5)
    err = info.value
    assert err.reason_code == "negative_consume_time_staleness"
    assert (err.oldest_weight_version, err.current_weight_version) == (6, 5)
    assert err.group_facts["rh2_prompt_group_id"] == "miles_g0" and err.group_facts["formal"] is claim_formal
    assert "negative_consume_time_staleness" in str(err) and "miles_g0" in str(err)
    assert recycled == [] and buf.consumed_total == 0 and sum(buf.drop_totals.values()) == 0  # 既非 drop 也非 consume


@pytest.mark.parametrize("versions", [[], ["step_0"], ["v5", "v5"]])
async def test_formal_group_without_version_facts_is_fatal(world, versions):
    from miles.rollout.fully_async_data_buffer import WeightVersionAccountingError

    buf, _ = _buffer(world, max_weight_staleness=2)
    pg, g = formal_group(world, versions_per_member=[versions, versions])
    await buf.put(_entry(world, pg, g))
    with pytest.raises(WeightVersionAccountingError) as info:
        await buf.get(current_version=5)
    assert info.value.reason_code == "weight_version_facts_missing" and info.value.oldest_weight_version is None


async def test_formal_group_without_current_version_is_fatal(world):
    from miles.rollout.fully_async_data_buffer import WeightVersionAccountingError

    buf, _ = _buffer(world, max_weight_staleness=2)
    pg, g = formal_group(world, versions_per_member=[["5"], ["5"]])
    await buf.put(_entry(world, pg, g))
    with pytest.raises(WeightVersionAccountingError) as info:
        await buf.get(current_version=None)
    assert info.value.reason_code == "current_version_missing" and info.value.oldest_weight_version == 5


@pytest.mark.parametrize("versions", [[], ["step_0"]])
async def test_non_formal_group_without_version_facts_keeps_stock_behaviour(world, versions):
    """无 admission 载荷的组（s1_compat/mock 链）缺版本事实时不判定、原样交出——stock 语义零改变。"""

    buf, recycled = _buffer(world, max_weight_staleness=0)
    pg, g = formal_group(world, versions_per_member=[versions, versions], claim_formal=False)
    await buf.put(_entry(world, pg, g))
    assert (await buf.get(current_version=5)).group is g
    pg2, g2 = formal_group(world, versions_per_member=[["3"], ["3"]], claim_formal=False, group_index=1)
    await buf.put(_entry(world, pg2, g2))
    assert (await buf.get(current_version=None)).group is g2  # current=None：不判定
    assert recycled == [] and buf.consumed_total == 2


@pytest.mark.parametrize("limit", THRESHOLDS)
async def test_oldest_is_the_minimum_over_every_member_and_turn(world, events_dir, limit):
    """跨版本 rollout（一个成员多轮跨 publish）+ 多 member：oldest 取全组全部轮的最小值。"""

    current = 20
    versions = [[str(current - limit), str(current)], [str(current - limit - 1), str(current), str(current)]]
    buf, recycled = _buffer(world, max_weight_staleness=limit)
    pg, g = formal_group(world, versions_per_member=versions)
    await buf.put(_entry(world, pg, g))
    pg_ok, g_ok = formal_group(world, versions_per_member=[[str(current - limit), str(current)], [str(current)]], group_index=1)
    await buf.put(_entry(world, pg_ok, g_ok))
    got = await buf.get(current_version=current)
    assert got.group is g_ok and recycled == [pg]  # 第二成员第一轮 current-limit-1 决定整组超阈
    [drop] = read_events(events_dir, ("group_filtered",))
    assert drop["oldest_weight_version"] == current - limit - 1 and drop["staleness"] == limit + 1
    [ok] = read_events(events_dir, ("group_consumed",))
    assert ok["oldest_weight_version"] == current - limit and ok["staleness"] == limit


async def test_none_limit_never_filters_but_still_records_staleness(world, events_dir):
    buf, recycled = _buffer(world, max_weight_staleness=None)
    pg, g = formal_group(world, versions_per_member=[["1"], ["3"]])
    await buf.put(_entry(world, pg, g))
    assert (await buf.get(current_version=41)).group is g and recycled == []
    [ok] = read_events(events_dir, ("group_consumed",))
    assert ok["staleness"] == 40 and ok["staleness_limit"] is None and ok["oldest_weight_version"] == 1
    assert buf.get_metrics()["rollout/fully_async/max_staleness"] == 40


async def test_three_drop_branches_emit_full_schema_and_aggregate_per_task(world, events_dir):
    """三分支 drop 事件字段齐全（put ABORTED / dynamic filter keep=False / get stale）+ consumed，
    再用 rh2 聚合函数按 task 得到尝试/接受/丢弃分母。"""

    from miles.utils.rh2_event_log import DROP_STAGES
    from repoharness2.adapters.miles.drop_events import summarize_group_events

    # 分支 1：put ABORTED（成员 1 中止）
    buf, recycled = _buffer(world, max_weight_staleness=1)
    pg_a, g_a = formal_group(world, versions_per_member=[["5"], ["5"]], group_index=0, task_id="long-task")
    g_a[1][0].status = world.MS.Status.ABORTED
    g_a[1][0].reward = None
    await buf.put(_entry(world, pg_a, g_a))
    assert recycled == [pg_a] and buf.drop_totals["put_aborted"] == 1
    # 分支 2：dynamic filter keep=False（独立 buffer 挂拒绝一切的 filter）
    buf_f, _ = _buffer(world, max_weight_staleness=1, dynamic_sampling_filter_path="w4_helpers.reject_all_filter")
    pg_f, g_f = formal_group(world, versions_per_member=[["5"], ["5"]], group_index=1, task_id="long-task")
    await buf_f.put(_entry(world, pg_f, g_f))
    assert buf_f.drop_totals["dynamic_filter"] == 1 and buf_f._buffer == []
    # 分支 3：get stale（同一 task 再来一组，超阈）；再来一组新鲜的（被消费）
    pg_s, g_s = formal_group(world, versions_per_member=[["3"], ["4"]], group_index=2, task_id="long-task")
    pg_ok, g_ok = formal_group(world, versions_per_member=[["5"], ["5"]], group_index=3, task_id="short-task")
    await buf.put(_entry(world, pg_s, g_s))
    await buf.put(_entry(world, pg_ok, g_ok))
    assert (await buf.get(current_version=5)).group is g_ok

    drops = {r["drop_stage"]: r for r in read_events(events_dir, ("group_filtered",))}
    assert set(drops) == set(DROP_STAGES)
    common = {"group_index", "sample_indices", "member_count", "task_id", "instance_id", "prompt_id",
              "rh2_prompt_group_id", "formal", "rewards", "reason", "reason_code", "drop_stage", "ts_unix", "run_id"}
    for row in drops.values():
        assert common <= set(row), row
    ab = drops["put_aborted"]
    assert ab["reason_code"] == "aborted_member" and ab["aborted_members"] == [
        {"index": 1, "member_slot": 1, "physical_attempt_id": "miles_g0_m1#p1-long-task"}]
    assert ab["rewards"] == [0.0, None] and ab["rh2_prompt_group_id"] == "miles_g0"
    assert drops["dynamic_filter"]["reason_code"] == "test_reject_all" and drops["dynamic_filter"]["rh2_prompt_group_id"] == "miles_g1"
    st = drops["consume_stale"]
    assert (st["oldest_weight_version"], st["current_weight_version"], st["staleness"], st["staleness_limit"]) == (3, 5, 2, 1)
    # 事件不携带内容：没有 prompt/response/patch 字段
    for row in list(drops.values()) + read_events(events_dir, ("group_consumed",)):
        assert not ({"prompt", "response", "tokens", "patch", "metadata"} & set(row))

    summary = summarize_group_events(read_events(events_dir), run_id="w4-run")
    assert summary["totals"] == {
        "attempts": 4, "accepted": 1, "dropped": 3,
        "dropped_by_stage": {"put_aborted": 1, "dynamic_filter": 1, "consume_stale": 1},
        "dropped_by_reason": {"aborted_member": 1, "staleness_exceeded": 1, "test_reject_all": 1},
    }
    assert summary["by_task"]["long-task"] == {
        "attempts": 3, "accepted": 0, "dropped": 3,
        "dropped_by_stage": {"put_aborted": 1, "dynamic_filter": 1, "consume_stale": 1}, "drop_ratio": 1.0}
    assert summary["by_task"]["short-task"] == {
        "attempts": 1, "accepted": 1, "dropped": 0,
        "dropped_by_stage": {"put_aborted": 0, "dynamic_filter": 0, "consume_stale": 0}, "drop_ratio": 0.0}
    assert summary["consumed_staleness"]["histogram"] == {"0": 1} and summary["stale_drops"]["limits_seen"] == {"1": 1}
    assert summary["aborted_members_total"] == 1 and summary["rows_skipped"] == {"foreign_run": 0, "malformed": 0, "unknown_drop_stage": 0}


async def test_events_are_silent_when_event_dir_unset_but_counters_still_run(world, monkeypatch, tmp_path):
    from miles.utils import rh2_event_log

    monkeypatch.delenv(rh2_event_log.EVENT_DIR_ENV, raising=False)
    buf, _ = _buffer(world, max_weight_staleness=0)
    pg, g = formal_group(world, versions_per_member=[["1"], ["1"]])
    await buf.put(_entry(world, pg, g))
    pg2, g2 = formal_group(world, versions_per_member=[["5"], ["5"]], group_index=1)
    await buf.put(_entry(world, pg2, g2))
    assert (await buf.get(current_version=5)).group is g2
    assert buf.drop_totals["consume_stale"] == 1 and buf.consumed_total == 1
    assert not list(tmp_path.glob("**/rh2_events_*.jsonl"))


# ===========================================================================
# B. 真实 fa_formal 链：事件里的身份来自真实铸造
# ===========================================================================


async def test_real_formal_chain_events_carry_minted_identity(world, tmp_path, events_dir):
    world.install_sglang_stub()
    from test_w1b_group_admission import BOTH_OK, POLICY_VERSION, _build_chain, _dispatch_group, _miles_args
    from w1b_synthetic_tasks import TID1

    from miles.rollout.fully_async_data_buffer import DataBufferConstructorInput, DefaultDataBuffer
    from miles.rollout.fully_async_data_buffer import group_claims_formal

    chain = _build_chain(world, tmp_path, grading_kinds=BOTH_OK)
    prompt_group, group = await _dispatch_group(world, chain)
    assert group_claims_formal(group)  # 真实交付面带 rh2_admission
    recycled: list = []
    buf = DefaultDataBuffer(DataBufferConstructorInput(args=_miles_args(world, chain, max_weight_staleness=2), unused_handler_fn=recycled.append))
    current = int(POLICY_VERSION)

    await buf.put(_entry(world, prompt_group, group))  # 真实复合 filter keep=True
    got = await buf.get(current_version=current)
    assert got.group is group
    [ok] = read_events(events_dir, ("group_consumed",))
    assert ok["rh2_prompt_group_id"] == "miles_g0" and ok["task_id"] == TID1 and ok["formal"] is True
    assert ok["staleness"] == 0 and ok["oldest_weight_version"] == current and ok["sample_indices"] == [0, 1]

    # 同一条链再派一组，消费时刻已发布版本前进 3 代 → 超阈 2 → consume_stale，身份仍是真实铸造的
    # （丢弃后 buffer 空，get 继续等待：用 task 观察丢弃事实后取消它）
    chain2 = _build_chain(world, tmp_path / "second", grading_kinds=BOTH_OK)
    pg2, g2 = await _dispatch_group(world, chain2)
    await buf.put(_entry(world, pg2, g2))
    pending_get = asyncio.create_task(buf.get(current_version=current + 3))
    await asyncio.sleep(0.05)
    assert not pending_get.done() and recycled == [pg2] and buf._buffer == []
    pending_get.cancel()
    with pytest.raises(asyncio.CancelledError):
        await pending_get
    [stale] = read_events(events_dir, ("group_filtered",))
    assert stale["drop_stage"] == "consume_stale" and stale["rh2_prompt_group_id"] == "miles_g0" and stale["task_id"] == TID1
    assert (stale["oldest_weight_version"], stale["current_weight_version"], stale["staleness"], stale["staleness_limit"]) == (current, current + 3, 3, 2)

    # ABORTED 分支：真实铸造的 member_slot / physical_attempt_id 进事件
    chain3 = _build_chain(world, tmp_path / "third", grading_kinds=BOTH_OK)
    pg4, g4 = await _dispatch_group(world, chain3)
    g4[1][0].status = world.MS.Status.ABORTED
    await buf.put(_entry(world, pg4, g4))
    aborted = [r for r in read_events(events_dir, ("group_filtered",)) if r["drop_stage"] == "put_aborted"]
    [ab] = aborted
    [member] = ab["aborted_members"]
    assert member["index"] == 1 and member["member_slot"] == 1
    assert member["physical_attempt_id"] == g4[1][0].metadata["rh2_physical_attempt_id"]
    assert member["physical_attempt_id"].startswith("miles_g0_m1#p1-")


# ===========================================================================
# C. rollout fn 级：fatal 通道 / no-progress / drain 顺序（W5a 双 loop 生产拓扑替身）
# ===========================================================================


def _fn(world, monkeypatch, *, generate, **args_over):
    """= test_w5a_miles_dispose_chain._args 的 miles args 面 + 本文件的覆盖项（rollout_batch_size 等可覆盖）。"""

    from test_w5a_miles_dispose_chain import _build_fn

    base = dict(
        rollout_submission_granularity="group", async_unused_samples_handler="drop", rollout_sample_filter_path=None,
        custom_async_data_buffer_path=None, async_max_concurrent_samples=None, rollout_global_dataset=True,
        rollout_batch_size=2, n_samples_per_prompt=2, dynamic_sampling_filter_path=None,
    )
    base.update(args_over)
    return _build_fn(world, monkeypatch, generate=generate, args=world.mk_miles_args(**base))


async def _drain(fn, *, weight_version: int, rollout_id: int = 0):
    """= RolloutManager._get_rollout_data 的调用形状：to_thread(call_rollout_function) → owner loop。"""

    from miles.rollout.base_types import RolloutFnTrainInput
    from miles.rollout.inference_rollout.compatibility import call_rollout_function

    return await asyncio.to_thread(
        call_rollout_function, fn, RolloutFnTrainInput(rollout_id=rollout_id, weight_version=weight_version)
    )


async def _close(fn):
    from miles.utils.rh2_shutdown import dispose_on_owner_loop

    return await dispose_on_owner_loop(fn, timeout_seconds=10.0)


def _generate_factory(world, versions_of_group, *, delay: float = 0.0, task_id: str = "t"):
    """generate_and_rm_group 替身：第 k 个组的行为版本由 versions_of_group(k) 给出（可读外部状态）。"""

    counter = {"k": 0}

    async def generate(state, prompt_group, *, sampling_params, evaluation, sample_done_callback):
        k = counter["k"]
        counter["k"] += 1
        if delay:
            await asyncio.sleep(delay)
        versions = versions_of_group(k)
        for p in prompt_group:
            p.group_index = k
        _pg, group = formal_group(
            world, versions_per_member=[[str(v) for v in versions]] * len(prompt_group), group_index=k,
            task_id=task_id, prompt_group=prompt_group, reward_values=[float(i % 2) for i in range(len(prompt_group))],
        )
        return group

    return generate, counter


async def test_negative_lag_fatal_surfaces_to_driver_and_becomes_shutdown_first_cause(world, monkeypatch):
    """get() 侧 fatal 的 run-fatal 通道：经 call_rollout_function 传回调用方线程（= driver 的 generate
    调用失败）→ train_async finally 的 dispose(driver_cause) → rh2 关停报告首因 = 本异常（磁盘报告一致）。"""

    import json

    from test_w5a_miles_dispose_chain import _assemble_rh2_service

    from miles.rollout.fully_async_data_buffer import WeightVersionAccountingError
    from miles.utils.rh2_shutdown import serialize_driver_cause

    generate, _ = _generate_factory(world, lambda k: [9])  # 行为版本 9 > 已发布 5
    far, fn, _source = _fn(world, monkeypatch, generate=generate, max_weight_staleness=2, rollout_batch_size=1)
    service, tmp = _assemble_rh2_service(monkeypatch)
    with pytest.raises(WeightVersionAccountingError) as info:
        await _drain(fn, weight_version=5)
    assert info.value.reason_code == "negative_consume_time_staleness"
    driver_cause = serialize_driver_cause(info.value)  # = train_async finally 的序列化
    assert driver_cause.startswith("WeightVersionAccountingError: negative_consume_time_staleness")

    report = await _close_with_cause(fn, driver_cause)
    assert report["ok"] is False and report["trigger"] == "driver_error" and report["primary_cause"] == driver_cause
    assert report["rollout_fn"]["worker_state"] == "cancelled"  # worker 本身没死：fatal 出自消费侧
    disk = json.loads((tmp / "shutdown_report.json").read_text(encoding="utf-8"))
    assert disk["ok"] is False and disk["first_cause"] == driver_cause


async def _close_with_cause(fn, driver_cause):
    from miles.utils.rh2_shutdown import dispose_on_owner_loop

    return await dispose_on_owner_loop(fn, driver_cause=driver_cause, timeout_seconds=10.0)


@pytest.mark.parametrize("bad", [0, -1.5])
def test_no_progress_limit_must_be_positive(world, monkeypatch, bad):
    generate, _ = _generate_factory(world, lambda k: [5])
    with pytest.raises(ValueError, match="must be > 0"):
        _fn(world, monkeypatch, generate=generate, rh2_max_time_without_accepted_group=bad)


async def test_no_progress_fires_when_groups_keep_completing_but_all_are_dropped(world, monkeypatch, events_dir):
    """持续完成又持续 drop 不算 progress：stale 组源源不断，计时不重置，到期 typed fatal，消息带累计计数。"""

    from miles.rollout.fully_async_rollout import NoProgressTimeout

    generate, counter = _generate_factory(world, lambda k: [1], delay=0.02)  # 永远 v1，消费时刻 v5，N=0 全部 stale
    far, fn, _ = _fn(world, monkeypatch, generate=generate, max_weight_staleness=0, rollout_batch_size=1,
                     rh2_max_time_without_accepted_group=0.5)
    started = time.monotonic()
    try:
        with pytest.raises(NoProgressTimeout) as info:
            await _drain(fn, weight_version=5)
        elapsed = time.monotonic() - started
        err = info.value
        assert err.reason_code == "no_accepted_group_within_limit" and err.limit_seconds == 0.5
        assert 0.45 <= err.waited_seconds <= 2.0 and 0.45 <= elapsed <= 3.0
        assert err.facts["consumed_total"] == 0 and err.facts["drop_totals"]["consume_stale"] >= 3  # 一直在丢，从未重置
        assert err.facts["staleness_limit"] == 0 and err.facts["current_weight_version"] == 5 and err.facts["worker_alive"] is True
        assert counter["k"] >= 3
        assert "no_accepted_group_within_limit" in str(err) and "consume_stale" in str(err)
    finally:
        report = await _close(fn)
    assert report["rollout_fn"]["worker_state"] == "cancelled"
    assert not read_events(events_dir, ("group_consumed",)) and not read_events(events_dir, ("drain_complete",))


async def test_no_progress_clock_resets_on_an_accepted_group(world, monkeypatch):
    """有一组被消费即重置：第一组新鲜（被接受），之后全 stale——fatal 在"接受后 limit 秒"而不是"开始后 limit 秒"。"""

    from miles.rollout.fully_async_rollout import NoProgressTimeout

    def versions(k):
        return [5] if k == 0 else [1]

    generate, _ = _generate_factory(world, versions, delay=0.3)  # 第一组 0.3s 后到达并被接受
    far, fn, _ = _fn(world, monkeypatch, generate=generate, max_weight_staleness=0, rollout_batch_size=2,
                     rh2_max_time_without_accepted_group=0.6)
    started = time.monotonic()
    try:
        with pytest.raises(NoProgressTimeout) as info:
            await _drain(fn, weight_version=5)
        elapsed = time.monotonic() - started
        err = info.value
        assert err.facts["consumed_total"] == 1  # 第一组确实被接受过
        assert 0.55 <= err.waited_seconds <= 2.0  # 从接受时刻重新计时
        assert elapsed >= 0.85  # 0.3（第一组）+ 0.6（limit）：不是从 drain 开始就算
    finally:
        await _close(fn)


async def test_no_progress_disabled_by_default_keeps_waiting(world, monkeypatch):
    from miles.rollout import fully_async_rollout as far_mod

    generate, _ = _generate_factory(world, lambda k: [1], delay=0.01)
    far, fn, _ = _fn(world, monkeypatch, generate=generate, max_weight_staleness=0, rollout_batch_size=1)
    assert fn._no_progress_limit is None and far_mod.no_progress_limit_seconds(fn.args) is None
    try:
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(_drain(fn, weight_version=5), timeout=0.8)  # 只会一直等（stock 30s 告警循环）
    finally:
        await _close(fn)


async def test_drain_complete_event_and_progress_anchor_cleared(world, monkeypatch, events_dir):
    generate, _ = _generate_factory(world, lambda k: [5])
    far, fn, _ = _fn(world, monkeypatch, generate=generate, max_weight_staleness=1, rollout_batch_size=2)
    try:
        out = await _drain(fn, weight_version=6, rollout_id=3)
        assert len(out.samples) == 2 and fn._progress_anchor is None
        [ev] = read_events(events_dir, ("drain_complete",))
        assert ev["rollout_id"] == 3 and ev["current_weight_version"] == 6 and ev["target_groups"] == 2
        assert ev["consumed_total"] == 2 and ev["drop_totals"] == {"put_aborted": 0, "dynamic_filter": 0, "consume_stale": 0}
        assert 0.0 <= ev["elapsed_seconds"] < 5.0
        assert [r["staleness"] for r in read_events(events_dir, ("group_consumed",))] == [1, 1]
    finally:
        await _close(fn)


# ---------------------------------------------------------------------------
# drain 顺序：JIT（publish 之后才取下一组）vs stock 预取（publish 之前取）
# ---------------------------------------------------------------------------


async def _run_driver(world, monkeypatch, *, order: str, limit, events_dir):
    """按 train_async 的两种顺序驱动真实 rollout fn（batch=1 组）。返回每个训练批的 (booked, true_lag)。

    published["v"] 模拟"已发布给 rollout engine 的版本"（publish = +1）；generate 替身在生成时刻读它作为
    组的行为版本。true_lag = 训练该批时的 published 版本 − 该批最老行为版本。
    """

    from miles.utils import rh2_event_log

    events_dir = events_dir / order  # 每种顺序各自的事件目录（group_index 在两次驱动里都从 0 起）
    monkeypatch.setenv(rh2_event_log.EVENT_DIR_ENV, str(events_dir))
    published = {"v": 1}
    generate, _ = _generate_factory(world, lambda k: [published["v"]])
    far, fn, _ = _fn(world, monkeypatch, generate=generate, max_weight_staleness=limit, rollout_batch_size=1)
    results: list[tuple[int, int]] = []
    pending: list[asyncio.Task] = []

    def oldest(out):
        from miles.rollout.fully_async_data_buffer import iter_samples

        return min(int(v) for g in out.samples for s in iter_samples(g) for v in s.weight_versions)

    def booked(out):
        """该批唯一一组在 get() 记账的 staleness（按 group_index 从 group_consumed 事件取；metrics 的
        max_staleness 窗口把被丢弃的 stale 组也计入，不能当作被消费组的记账）。"""
        from miles.rollout.fully_async_data_buffer import iter_samples

        [group] = out.samples
        gi = next(iter_samples(group)).group_index
        rows = [r for r in read_events(events_dir, ("group_consumed",)) if r["group_index"] == gi]
        assert len(rows) == 1, rows
        return int(rows[0]["staleness"])

    async def publish():
        published["v"] += 1  # = actor_model.update_weights → rollout_manager.set_weight_version

    try:
        if order == "stock_prefetch":
            nxt = await _drain(fn, weight_version=published["v"], rollout_id=0)  # 循环前预取 batch0
            for rollout_id in range(2):
                curr = nxt
                if rollout_id + 1 < 2:
                    nxt_task = asyncio.create_task(_drain(fn, weight_version=published["v"], rollout_id=rollout_id + 1))
                    pending.append(nxt_task)
                results.append((booked(curr), published["v"] - oldest(curr)))  # train(curr) 发生在这里
                if rollout_id + 1 < 2:
                    nxt = await nxt_task  # sync 在 publish 之前（stock 的预取 sync 行）
                await publish()
        else:
            for rollout_id in range(2):
                curr = await _drain(fn, weight_version=published["v"], rollout_id=rollout_id)  # publish 之后才取
                results.append((booked(curr), published["v"] - oldest(curr)))
                await publish()
    finally:
        await _close(fn)
        await asyncio.gather(*pending, return_exceptions=True)  # 关停后仍在飞的预取 drain 以 RolloutFnClosed 收尾
    return results


async def test_jit_drain_books_true_trainer_consumption_staleness(world, monkeypatch, events_dir):
    """W4 证明测试：JIT 顺序下每批 booked staleness == 训练时刻真实 lag；stock 预取顺序下 publish 之后训练的
    那批 booked 比真实低报恰好一代（负对照）。阈值 None 只比较记账。"""

    jit = await _run_driver(world, monkeypatch, order="jit", limit=None, events_dir=events_dir)
    assert all(booked == true for booked, true in jit), jit
    assert [true for _b, true in jit] == [0, 1]  # batch1 的组在 v1 生成、v2 训练：真实 lag 1，记账 1

    stock = await _run_driver(world, monkeypatch, order="stock_prefetch", limit=None, events_dir=events_dir)
    assert stock[0] == (0, 0)
    assert stock[1][1] == 1 and stock[1][0] == 0  # publish 之前已按 v1 取走：记账 0，真实 lag 1——低报一代


async def test_jit_drain_with_zero_limit_drops_pre_publish_groups_instead_of_training_them(world, monkeypatch, events_dir):
    """N=0：JIT 下 publish 前生成的组在 publish 后被 get() 判 stale 丢弃（consume_stale 事件），训练的是 v2 的组；
    stock 预取会把同样的组在 publish 前取走并在 v2 训练（buffer 语义相同，差别只在取的时点）。"""

    jit = await _run_driver(world, monkeypatch, order="jit", limit=0, events_dir=events_dir)
    assert jit == [(0, 0), (0, 0)]
    stale = [r for r in read_events(events_dir / "jit", ("group_filtered",)) if r["drop_stage"] == "consume_stale"]
    assert stale and all(r["oldest_weight_version"] == 1 and r["current_weight_version"] == 2 for r in stale)


def test_train_async_jit_drain_source_facts(world):
    """钉死 train_async.py 的顺序事实（Ray/megatron import 链不可导，读源码文本）：
    --fully-async → jit_drain；JIT 分支在循环顶部 await generate(rollout_id)，位于 train 之前、上一轮
    update_weights 之后；publish 前的"sync 预取"只留在非 JIT 分支；非 fully-async 的 stock 预取原样保留。"""

    src = (world.miles_root / "train_async.py").read_text(encoding="utf-8")
    i_flag = src.index("jit_drain = bool(args.fully_async)")
    i_head_guard = src.index("if not jit_drain:\n            rollout_data_next_future = rollout_manager.generate.remote(args.start_rollout_id)")
    i_loop = src.index("for rollout_id in range(args.start_rollout_id, args.num_rollout):")
    i_jit_if = src.index("            if jit_drain:\n", i_loop)
    i_jit_get = src.index("rollout_data_curr_ref = await rollout_manager.generate.remote(rollout_id)")
    i_else = src.index("            else:\n", i_jit_if)
    i_prefetch_next = src.index("rollout_data_next_future = rollout_manager.generate.remote(rollout_id + 1)")
    i_train = src.index("await actor_model.train(rollout_id, rollout_data_curr_ref)")
    i_sync_guard = src.index("if not jit_drain:\n                        # sync generate before update weights")
    i_sync = src.index("rollout_data_curr_ref = (await x) if (x := rollout_data_next_future) is not None else None")
    i_update = src.index("await actor_model.update_weights(rollout_id=rollout_id)")

    assert i_flag < i_head_guard < i_loop < i_jit_if < i_jit_get < i_else < i_prefetch_next < i_train
    assert i_train < i_sync_guard < i_sync < i_update  # 预取 sync 只在非 JIT 分支，且仍在 update_weights 之前
    assert src.count("rollout_manager.generate.remote(") == 3  # 循环前 stock 预取 / JIT 取本批 / stock 预取下一批
    # JIT 取批在循环内只出现一次，且紧跟 `if jit_drain:`（中间无其它语句）
    between = src[i_jit_if + len("            if jit_drain:\n"): i_jit_get]
    assert all(line.strip().startswith("#") or not line.strip() for line in between.splitlines())
    # update_weights 在循环体内、下一轮循环顶部的 JIT 取批之前（顺序 = drain N → train N → publish → drain N+1）
    assert i_jit_get < i_update


# ===========================================================================
# D. 字面量镜像钉死
# ===========================================================================


def test_metadata_key_literals_and_drop_stages_match_rh2_sources(world):
    from miles.rollout import fully_async_data_buffer as buf_mod
    from miles.utils import rh2_event_log
    from repoharness2.adapters.miles import drop_events
    from repoharness2.adapters.miles.identity import ATTEMPT_ID_KEY, GROUP_ID_KEY, MEMBER_SLOT_KEY
    from repoharness2.governance.admission import ADMISSION_METADATA_KEY

    assert buf_mod.RH2_ADMISSION_METADATA_KEY == ADMISSION_METADATA_KEY
    assert buf_mod.RH2_PROMPT_GROUP_ID_KEY == GROUP_ID_KEY
    assert buf_mod.RH2_MEMBER_SLOT_KEY == MEMBER_SLOT_KEY
    assert buf_mod.RH2_PHYSICAL_ATTEMPT_ID_KEY == ATTEMPT_ID_KEY
    assert rh2_event_log.DROP_STAGES == drop_events.DROP_STAGES
    assert rh2_event_log.GROUP_DROP_EVENT == drop_events.GROUP_DROP_EVENT == "group_filtered"
    assert rh2_event_log.GROUP_CONSUMED_EVENT == drop_events.GROUP_CONSUMED_EVENT
    # get() 仍是唯一判定点：DefaultDataBuffer 之外的 miles 源码不消费阈值（W0 锁的补强）
    src = (world.miles_root / "miles" / "rollout" / "fully_async_rollout.py").read_text(encoding="utf-8")
    assert "self._output.get(current_version=current_version)" in src
