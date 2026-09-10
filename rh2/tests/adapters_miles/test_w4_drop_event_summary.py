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
    # R6（Codex 集成审查）：唯一成员 elapsed 未知 → 组成本"未知"，不再输出数值 0
    assert consumed["group_cost_seconds"] == {"count": 0, "min": None, "p50": None, "max": None, "sum": None, "unknown": 1}
    assert consumed["groups_cost_unknown"] == 1 and consumed["groups_with_unknown_members"] == 1
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


# ---------------------------------------------------------------------------
# Codex 第 2 组剩余集成审查 R5 / R6：连接键含 run 身份；按根因 / 按 task 的成本分布；缺失与未知口径
# ---------------------------------------------------------------------------


def test_same_group_id_in_two_runs_is_not_joined_without_run_filter(costs):
    """R5：组 id（miles_g{index}）只在 run 内唯一。A 消费组 10s、B 丢弃组 100s，默认汇总不得各成 110s。"""

    rows = [
        _snap("a#p1", "miles_g0", elapsed=10.0, run="run_a"), _consumed("A", 0, rh2_prompt_group_id="miles_g0", run_id="run_a"),
        _snap("b#p1", "miles_g0", elapsed=100.0, run="run_b", hint="aborted", reason="harness_crash"),
        _drop("put_aborted", "A", reason="aborted_member", rh2_prompt_group_id="miles_g0", run_id="run_b",
              aborted_members=[{"index": 0, "member_slot": 0, "physical_attempt_id": "b#p1"}]),
    ]
    s = costs(rows)  # 不指定 run：仍按 (run_id, 组) 连接
    assert s["terminals"]["consumed"]["members_observed"] == 1 and s["terminals"]["consumed"]["group_cost_seconds"]["sum"] == 10.0
    assert s["terminals"]["aborted_member"]["members_observed"] == 1 and s["terminals"]["aborted_member"]["group_cost_seconds"]["sum"] == 100.0
    assert s["terminals"]["aborted_member"]["root_cause_reasons"] == {"harness_crash": 1}
    assert s["unmatched_snapshots"] == 0
    only_a = costs(rows, run_id="run_a")
    assert set(only_a["terminals"]) == {"consumed"} and only_a["rows_skipped"]["foreign_run"] == 2


def test_cost_by_root_cause_and_by_task_keep_the_dimensions_apart(costs):
    """R6：拉镜像失败 10s 与 hard wall 900s 两个根因、两个 task——分布按根因与 task 分开，不混成一个耗时分布。"""

    rows = [
        _snap("a#p1", "g1", elapsed=10.0, hint="aborted", reason="grading_image_pull_failed"),
        _drop("put_aborted", "A", reason="aborted_member", rh2_prompt_group_id="g1", member_count=1,
              aborted_members=[{"index": 0, "member_slot": 0, "physical_attempt_id": "a#p1"}]),
        _row("attempt_cost_snapshot", physical_attempt_id="b#p1", rh2_prompt_group_id="g2", task_id="B",
             disposition_hint="present", reason_code="hard_wall_timeout", elapsed_seconds=900.0, accepted_turns=25),
        _drop("put_aborted", "B", reason="aborted_member", rh2_prompt_group_id="g2", member_count=1,
              aborted_members=[{"index": 0, "member_slot": 0, "physical_attempt_id": "b#p1"}]),
        _snap("c#p1", "g3", elapsed=50.0), _consumed("A", 1, rh2_prompt_group_id="g3", member_count=1),
    ]
    s = costs(rows, run_id="r1")
    aborted = s["terminals"]["aborted_member"]
    assert aborted["root_cause_reasons"] == {"grading_image_pull_failed": 1, "hard_wall_timeout": 1}
    cause = aborted["by_root_cause"]
    assert cause["grading_image_pull_failed"]["members"] == 1 and cause["grading_image_pull_failed"]["member_fields"]["elapsed_seconds"]["max"] == 10.0
    assert cause["hard_wall_timeout"]["member_fields"]["elapsed_seconds"]["min"] == 900.0
    assert cause["hard_wall_timeout"]["member_fields"]["accepted_turns"]["sum"] == 25.0
    assert aborted["group_cost_seconds"] == {"count": 2, "min": 10.0, "p50": 10.0, "max": 900.0, "sum": 910.0, "unknown": 0}
    by_task = s["by_task"]
    assert (by_task["A"]["groups"], by_task["A"]["consumed_groups"], by_task["A"]["dropped_groups"], by_task["A"]["members_observed"]) == (
        2, 1, {"aborted_member": 1}, 2
    )
    assert by_task["A"]["member_fields"]["elapsed_seconds"] == {"count": 2, "min": 10.0, "p50": 10.0, "max": 50.0, "sum": 60.0, "unknown": 0}
    assert by_task["B"]["dropped_groups"] == {"aborted_member": 1} and by_task["B"]["member_fields"]["elapsed_seconds"]["sum"] == 900.0


def test_missing_member_snapshots_give_a_lower_bound_not_a_complete_group_cost(costs):
    """R6：终局说 8 个成员、只有 7 份快照 → 已知部分和 4200 只作下界（known_partial），不进完整组成本；
    7 份齐全但其中 1 份 elapsed 未知 → 同样只是下界；全部齐全已知 → 完整。"""

    rows = [_snap(f"g1#p{i}", "g1", elapsed=600.0) for i in range(7)]
    rows.append(_consumed("A", 0, rh2_prompt_group_id="g1", member_count=8))
    rows += [_snap(f"g2#p{i}", "g2", elapsed=600.0) for i in range(6)] + [_snap("g2#p6", "g2", elapsed=None)]
    rows.append(_consumed("A", 0, rh2_prompt_group_id="g2", member_count=7))
    rows += [_snap(f"g3#p{i}", "g3", elapsed=100.0) for i in range(2)]
    rows.append(_consumed("A", 0, rh2_prompt_group_id="g3", member_count=2))
    consumed = costs(rows, run_id="r1")["terminals"]["consumed"]
    assert consumed["groups"] == 3 and consumed["members_observed"] == 16
    assert consumed["groups_with_missing_members"] == 1 and consumed["groups_with_unknown_members"] == 1
    assert consumed["group_cost_seconds"] == {"count": 1, "min": 200.0, "p50": 200.0, "max": 200.0, "sum": 200.0, "unknown": 0}
    assert consumed["group_cost_seconds_known_partial"] == {"count": 2, "min": 3600.0, "p50": 3600.0, "max": 4200.0, "sum": 7800.0, "unknown": 2}
    assert consumed["groups_cost_unknown"] == 0


def _aborted_group(group: str, reason: str, normal_elapsed: float, *, task: str = "A", run: str = "r1") -> list[dict]:
    """八成员组：7 个正常成员各 normal_elapsed 秒 + 第 8 个成员 5 秒失败（根因 reason）→ put_aborted。"""

    rows = [_snap(f"{group}#p{i}", group, elapsed=normal_elapsed, run=run) for i in range(7)]
    rows.append(_snap(f"{group}#p7", group, elapsed=5.0, hint="aborted", reason=reason, run=run))
    rows.append(_drop("put_aborted", task, reason="aborted_member", rh2_prompt_group_id=group, member_count=8, run_id=run,
                      aborted_members=[{"index": 7, "member_slot": 7, "physical_attempt_id": f"{group}#p7"}]))
    return rows


def test_whole_group_collateral_cost_is_attributed_to_the_root_cause_set(costs):
    """R6 余项（Codex 复核）：失败成员自身都是 5s，不能回答"哪类故障连带丢掉长轨迹"。整组连带成本按根因归属：
    harness 失败组 4205s、拉镜像失败组 75s；交换正常成员成本后两个桶随之交换（汇总必须不同）。"""

    first = costs(_aborted_group("g0", "harness_crash", 600.0) + _aborted_group("g1", "grading_image_pull_failed", 10.0), run_id="r1")
    second = costs(_aborted_group("g0", "harness_crash", 10.0) + _aborted_group("g1", "grading_image_pull_failed", 600.0), run_id="r1")
    assert first != second
    b1, b2 = first["terminals"]["aborted_member"], second["terminals"]["aborted_member"]
    assert b1["by_root_cause"]["harness_crash"]["member_fields"]["elapsed_seconds"]["sum"] == 5.0  # 失败成员自身成本不变
    assert b1["by_root_cause_set"]["harness_crash"]["group_cost_seconds"]["sum"] == 4205.0
    assert b1["by_root_cause_set"]["grading_image_pull_failed"]["group_cost_seconds"]["sum"] == 75.0
    assert b2["by_root_cause_set"]["harness_crash"]["group_cost_seconds"]["sum"] == 75.0
    assert b2["by_root_cause_set"]["grading_image_pull_failed"]["group_cost_seconds"]["sum"] == 4205.0
    assert all(v["groups"] == 1 for v in b1["by_root_cause_set"].values())
    assert b1["group_cost_seconds"]["sum"] == 4280.0  # 桶总量 = 两组之和，与按根因归属的分项相加一致（无重叠）


def test_multi_cause_group_cost_goes_to_the_combined_key_only(costs):
    """同组两个根因：整组成本归 "a|b" 组合键一次，不重复计入 a 与 b 各自的分项；成员缺失的组只给下界。"""

    rows = [_snap("g1#p0", "g1", elapsed=100.0), _snap("g1#p1", "g1", elapsed=100.0),
            _snap("g1#p2", "g1", elapsed=2.0, hint="aborted", reason="harness_crash"),
            _snap("g1#p3", "g1", elapsed=3.0, hint="aborted", reason="rollout_container_start_failed"),
            _drop("put_aborted", "A", reason="aborted_member", rh2_prompt_group_id="g1", member_count=4, aborted_members=[
                {"index": 2, "member_slot": 2, "physical_attempt_id": "g1#p2"},
                {"index": 3, "member_slot": 3, "physical_attempt_id": "g1#p3"},
            ])]
    rows += [_snap("g2#p0", "g2", elapsed=50.0), _snap("g2#p1", "g2", elapsed=1.0, hint="aborted", reason="harness_crash"),
             _drop("put_aborted", "A", reason="aborted_member", rh2_prompt_group_id="g2", member_count=8,  # 8 个成员只有 2 份快照
                   aborted_members=[{"index": 1, "member_slot": 1, "physical_attempt_id": "g2#p1"}])]
    b = costs(rows, run_id="r1")["terminals"]["aborted_member"]
    assert set(b["by_root_cause_set"]) == {"harness_crash|rollout_container_start_failed", "harness_crash"}
    combined = b["by_root_cause_set"]["harness_crash|rollout_container_start_failed"]
    assert combined["groups"] == 1 and combined["group_cost_seconds"]["sum"] == 205.0
    single = b["by_root_cause_set"]["harness_crash"]
    assert single["groups"] == 1 and single["group_cost_seconds"]["count"] == 0  # 成员缺失：不进完整成本
    assert single["group_cost_seconds_known_partial"] == {"count": 1, "min": 51.0, "p50": 51.0, "max": 51.0, "sum": 51.0, "unknown": 0}
    assert b["root_cause_reasons"] == {"harness_crash": 2, "rollout_container_start_failed": 1}  # 成员级计数不受影响


def test_by_task_keeps_consumed_and_dropped_member_costs_apart(costs):
    rows = _aborted_group("g0", "harness_crash", 600.0) + [_snap("g9#p0", "g9", elapsed=30.0), _snap("g9#p1", "g9", elapsed=40.0),
                                                            _consumed("A", 1, rh2_prompt_group_id="g9", member_count=2)]
    task = costs(rows, run_id="r1")["by_task"]["A"]
    assert task["consumed_groups"] == 1 and task["dropped_groups"] == {"aborted_member": 1} and task["members_observed"] == 10
    assert task["consumed_member_fields"]["elapsed_seconds"] == {"count": 2, "min": 30.0, "p50": 30.0, "max": 40.0, "sum": 70.0, "unknown": 0}
    assert task["dropped_member_fields"]["elapsed_seconds"]["sum"] == 4205.0 and task["dropped_member_fields"]["elapsed_seconds"]["count"] == 8
    assert task["member_fields"]["elapsed_seconds"]["sum"] == 4275.0  # 合计仍保留

