"""W4（决策包 D2+B v2 B-2）：drop/consumed 事件流的 run 结束汇总（纯 stdlib 聚合，双 lane 都跑）。

被测 = `repoharness2.adapters.miles.drop_events`（不依赖 miles 运行时；事件 schema 与 miles 侧的一致性
由 test_w4_consume_time_staleness.py 用真实 buffer 产出的事件钉死，本文件只用合成行）。
"""

from __future__ import annotations

import json

import pytest


def _row(event: str, **fields) -> dict:
    return {"event": event, "ts_unix": 1.0, "host": "h", "pid": 1, "run_id": "r1", **fields}


def _drop(stage: str, task: str | None, *, reason: str | None = None, **extra) -> dict:
    fields = {"drop_stage": stage, "reason_code": reason or stage, "reason": reason or stage, "task_id": task}
    fields.update(extra)
    return _row("group_filtered", **fields)


def _consumed(task: str | None, staleness, **extra) -> dict:
    return _row("group_consumed", task_id=task, staleness=staleness, **extra)


@pytest.fixture()
def summarize():
    from repoharness2.adapters.miles.drop_events import summarize_group_events

    return summarize_group_events


def test_totals_and_per_task_denominators(summarize):
    rows = [
        _consumed("A", 0), _consumed("A", 2), _consumed("B", 1),
        _drop("consume_stale", "A", reason="staleness_exceeded", staleness=3, staleness_limit=2),
        _drop("put_aborted", "A", reason="aborted_member", aborted_members=[{"index": 1, "member_slot": 1, "physical_attempt_id": "x"}]),
        _drop("dynamic_filter", "C", reason="zero_std_1.0"),
        _drop("dynamic_filter", "C", reason="admission_reward_scope_none"),
        _row("weight_publish", rollout_id=0),  # 无关事件被忽略
    ]
    s = summarize(rows)
    assert s["schema_id"] == "rh2.group_event_summary.v1" and s["run_id"] is None
    assert s["totals"] == {
        "attempts": 7, "accepted": 3, "dropped": 4,
        "dropped_by_stage": {"put_aborted": 1, "dynamic_filter": 2, "consume_stale": 1},
        "dropped_by_reason": {"aborted_member": 1, "admission_reward_scope_none": 1, "staleness_exceeded": 1, "zero_std_1.0": 1},
    }
    assert s["by_task"] == {
        "A": {"attempts": 4, "accepted": 2, "dropped": 2, "dropped_by_stage": {"put_aborted": 1, "dynamic_filter": 0, "consume_stale": 1}, "drop_ratio": 0.5},
        "B": {"attempts": 1, "accepted": 1, "dropped": 0, "dropped_by_stage": {"put_aborted": 0, "dynamic_filter": 0, "consume_stale": 0}, "drop_ratio": 0.0},
        "C": {"attempts": 2, "accepted": 0, "dropped": 2, "dropped_by_stage": {"put_aborted": 0, "dynamic_filter": 2, "consume_stale": 0}, "drop_ratio": 1.0},
    }
    assert s["consumed_staleness"] == {"count": 3, "min": 0, "max": 2, "mean": 1.0, "histogram": {"0": 1, "1": 1, "2": 1}, "unknown": 0}
    assert s["stale_drops"] == {"count": 1, "min": 3, "max": 3, "mean": 3.0, "histogram": {"3": 1}, "limits_seen": {"2": 1}}
    assert s["aborted_members_total"] == 1
    assert s["rows_skipped"] == {"foreign_run": 0, "malformed": 0, "unknown_drop_stage": 0}


def test_task_key_falls_back_to_instance_id_then_unknown(summarize):
    rows = [_consumed(None, 0, instance_id="django__django-1"), _drop("consume_stale", None, staleness=5), _consumed(None, None)]
    s = summarize(rows)
    assert set(s["by_task"]) == {"django__django-1", "<unknown>"}
    assert s["by_task"]["<unknown>"] == {"attempts": 2, "accepted": 1, "dropped": 1, "dropped_by_stage": {"put_aborted": 0, "dynamic_filter": 0, "consume_stale": 1}, "drop_ratio": 0.5}
    assert s["consumed_staleness"]["unknown"] == 1 and s["consumed_staleness"]["count"] == 1


def test_run_id_filter_and_legacy_rows_are_counted_not_hidden(summarize):
    rows = [
        _consumed("A", 0),
        {**_consumed("A", 0), "run_id": "other"},
        {"event": "group_filtered", "reason": "zero_std_0.0", "group_index": 3, "run_id": "r1"},  # W4 之前的 emitter：无 drop_stage
        {"event": "_malformed"},
    ]
    s = summarize(rows, run_id="r1")
    assert s["run_id"] == "r1"
    assert s["totals"]["accepted"] == 1 and s["totals"]["dropped"] == 1 and s["totals"]["attempts"] == 2
    assert s["totals"]["dropped_by_stage"] == {"put_aborted": 0, "dynamic_filter": 0, "consume_stale": 0}
    assert s["totals"]["dropped_by_reason"] == {"zero_std_0.0": 1}
    assert s["rows_skipped"] == {"foreign_run": 1, "malformed": 1, "unknown_drop_stage": 1}


def test_boolean_staleness_is_not_a_number(summarize):
    s = summarize([_consumed("A", True), _drop("consume_stale", "A", staleness=False)])
    assert s["consumed_staleness"]["count"] == 0 and s["consumed_staleness"]["unknown"] == 1
    assert s["stale_drops"]["count"] == 0


def test_cli_reads_directory_and_writes_json(tmp_path, capsys):
    from repoharness2.adapters.miles import drop_events

    events = tmp_path / "events"
    events.mkdir()
    lines = [json.dumps(_consumed("A", 1)), "not json", json.dumps(_drop("put_aborted", "A", reason="aborted_member"))]
    (events / "rh2_events_h_1.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (events / "unrelated.txt").write_text("ignored", encoding="utf-8")
    out = tmp_path / "summary.json"
    assert drop_events.main([str(events), "--run-id", "r1", "--json", str(out)]) == 0
    summary = json.loads(out.read_text(encoding="utf-8"))
    assert summary["totals"]["attempts"] == 2 and summary["rows_skipped"]["malformed"] == 1
    assert drop_events.main([str(events / "rh2_events_h_1.jsonl")]) == 0
    assert json.loads(capsys.readouterr().out)["totals"]["accepted"] == 1


# ---------------------------------------------------------------------------
# N1（第 2 组 §4 / I15-I20）：attempt_cost_snapshot 与组终局事件的连接汇总
# ---------------------------------------------------------------------------


def _snap(paid: str, group: str, *, elapsed, turns=None, tokens=None, trainable=None, inputs=None,
          hint="present", reason=None, failure=None, run="r1") -> dict:
    return _row(
        "attempt_cost_snapshot", run_id=run, physical_attempt_id=paid, rh2_prompt_group_id=group, task_id="A",
        disposition_hint=hint, reason_code=reason, last_failure=failure, elapsed_seconds=elapsed,
        accepted_turns=turns, captured_output_tokens=tokens, trainable_tokens_total=trainable,
        input_tokens_total=inputs,
    )


@pytest.fixture()
def costs():
    from repoharness2.adapters.miles.drop_events import summarize_attempt_costs

    return summarize_attempt_costs


def test_group_cost_is_the_sum_over_all_known_members_not_the_failing_one(costs):
    """七个 600s 成功成员 + 一个 5s 失败成员：整组连带成本 4205s（不是 5s，也不是八条完整轨迹）；
    根因取失败成员快照的原因；被消费组另成一桶。"""

    rows = [_snap(f"g1#p{i}", "g1", elapsed=600.0, turns=20, tokens=4000) for i in range(7)]
    rows.append(_snap("g1#p7", "g1", elapsed=5.0, hint="aborted", reason="harness_bootstrap_failed"))
    rows.append(_drop("put_aborted", "A", reason="aborted_member", rh2_prompt_group_id="g1",
                      aborted_members=[{"index": 7, "member_slot": 7, "physical_attempt_id": "g1#p7"}]))
    rows += [_snap(f"g2#p{i}", "g2", elapsed=100.0, turns=5, tokens=800) for i in range(8)]
    rows.append(_consumed("A", 1, rh2_prompt_group_id="g2"))
    s = costs(rows, run_id="r1")
    assert s["schema_id"] == "rh2.attempt_cost_summary.v1" and s["snapshots"] == 16
    aborted = s["terminals"]["aborted_member"]
    assert aborted["groups"] == 1 and aborted["members_observed"] == 8
    assert aborted["group_cost_seconds"] == {"count": 1, "min": 4205.0, "p50": 4205.0, "max": 4205.0, "sum": 4205.0, "unknown": 0}
    assert aborted["member_fields"]["elapsed_seconds"]["count"] == 8 and aborted["member_fields"]["elapsed_seconds"]["max"] == 600.0
    assert aborted["member_fields"]["accepted_turns"] == {"count": 7, "min": 20.0, "p50": 20.0, "max": 20.0, "sum": 140.0, "unknown": 1}
    assert aborted["root_cause_reasons"] == {"harness_bootstrap_failed": 1}
    assert aborted["disposition_hints"] == {"aborted": 1, "present": 7}
    consumed = s["terminals"]["consumed"]
    assert consumed["groups"] == 1 and consumed["members_observed"] == 8
    assert consumed["group_cost_seconds"]["sum"] == 800.0 and consumed["member_fields"]["captured_output_tokens"]["sum"] == 6400.0
    assert s["unmatched_snapshots"] == 0 and s["legacy_rows"] == 0


def test_fork_rows_same_attempt_are_counted_once_and_multi_root_causes_are_kept(costs):
    rows = [
        _snap("g1#p0", "g1", elapsed=30.0), _snap("g1#p0", "g1", elapsed=31.0),  # 同一 attempt 两条（FORK 行）
        _snap("g1#p1", "g1", elapsed=2.0, hint="aborted", reason="rollout_container_start_failed"),
        _snap("g1#p2", "g1", elapsed=3.0, hint="aborted", failure={"stage": "harness_run", "error_type": "harness_crash"}),
        _drop("put_aborted", "A", reason="aborted_member", rh2_prompt_group_id="g1", aborted_members=[
            {"index": 1, "member_slot": 1, "physical_attempt_id": "g1#p1"},
            {"index": 2, "member_slot": 2, "physical_attempt_id": "g1#p2"},
            {"index": 3, "member_slot": 3, "physical_attempt_id": "g1#p3"},  # 没有快照的成员
        ]),
    ]
    s = costs(rows)
    b = s["terminals"]["aborted_member"]
    assert s["duplicate_snapshots"] == 1 and b["members_observed"] == 3
    assert b["group_cost_seconds"]["sum"] == 36.0  # 31 + 2 + 3：重复快照只取最后一条
    assert b["root_cause_reasons"] == {"<no_snapshot>": 1, "harness_crash": 1, "rollout_container_start_failed": 1}


def test_unknowns_legacy_rows_foreign_runs_and_unmatched_snapshots_are_kept_separate(costs):
    rows = [
        _snap("g1#p0", "g1", elapsed=None, tokens=None),  # 未知：不填 0
        _consumed("A", 0, rh2_prompt_group_id="g1"),
        _consumed("A", 0),  # 旧格式：无组身份
        _drop("consume_stale", "A", reason="staleness_exceeded", rh2_prompt_group_id="g9"),  # 无快照的组
        _snap("gx#p0", "gx", elapsed=1.0),  # 无终局事件的快照
        _snap("gz#p0", "gz", elapsed=1.0, run="other"),  # 外 run
        {"event": "_malformed"},
    ]
    s = costs(rows, run_id="r1")
    consumed = s["terminals"]["consumed"]
    assert consumed["member_fields"]["elapsed_seconds"] == {"count": 0, "min": None, "p50": None, "max": None, "sum": None, "unknown": 1}
    assert consumed["group_cost_seconds"] == {"count": 1, "min": 0.0, "p50": 0.0, "max": 0.0, "sum": 0.0, "unknown": 1}
    assert s["terminals"]["staleness_exceeded"]["groups_without_snapshots"] == 1
    assert s["legacy_rows"] == 1 and s["unmatched_snapshots"] == 1
    assert s["rows_skipped"] == {"foreign_run": 1, "malformed": 1}


def test_cli_costs_flag_writes_cost_summary(tmp_path):
    from repoharness2.adapters.miles import drop_events

    events = tmp_path / "events"
    events.mkdir()
    lines = [json.dumps(_snap("g1#p0", "g1", elapsed=12.0)), json.dumps(_consumed("A", 1, rh2_prompt_group_id="g1"))]
    (events / "rh2_events_h_1.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    out = tmp_path / "costs.json"
    assert drop_events.main([str(events), "--run-id", "r1", "--costs", "--json", str(out)]) == 0
    summary = json.loads(out.read_text(encoding="utf-8"))
    assert summary["schema_id"] == "rh2.attempt_cost_summary.v1"
    assert summary["terminals"]["consumed"]["group_cost_seconds"]["sum"] == 12.0
