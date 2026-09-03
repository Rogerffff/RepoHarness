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
