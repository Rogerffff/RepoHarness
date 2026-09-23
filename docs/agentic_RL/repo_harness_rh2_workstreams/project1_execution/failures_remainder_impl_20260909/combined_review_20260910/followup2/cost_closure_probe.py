"""复核 R6 余项：复用原反例输入，核对根因集合成本、终态对照与缺失口径。"""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("original_r6_probe", HERE.parent / "followup1/cost_diagnostic_probe.py")
original = importlib.util.module_from_spec(spec)
spec.loader.exec_module(original)
summarize = original.module.summarize_attempt_costs


def aborted_bucket(rows):
    return summarize(rows)["terminals"]["aborted_member"]


def main():
    first = summarize(original.rows(True))
    second = summarize(original.rows(False))
    assert first != second
    a = first["terminals"]["aborted_member"]["by_root_cause_set"]
    b = second["terminals"]["aborted_member"]["by_root_cause_set"]
    costs_a = {k: v["group_cost_seconds"]["sum"] for k, v in a.items()}
    costs_b = {k: v["group_cost_seconds"]["sum"] for k, v in b.items()}
    assert costs_a == {"harness_crash": 4205.0, "grading_image_pull_failed": 75.0}
    assert costs_b == {"harness_crash": 75.0, "grading_image_pull_failed": 4205.0}

    one = [x for x in original.rows(True) if x["rh2_prompt_group_id"] == "g0"]
    multi = copy.deepcopy(one)
    multi[-2]["reason_code"] = "grading_image_pull_failed"
    multi[0]["reason_code"] = "harness_crash"
    multi[-1]["aborted_members"].append({"physical_attempt_id": "g0#p0"})
    bucket = aborted_bucket(multi)
    combined = bucket["by_root_cause_set"]
    assert list(combined) == ["grading_image_pull_failed|harness_crash"]
    assert next(iter(combined.values()))["group_cost_seconds"]["sum"] == 4205.0
    assert sum(v["groups"] for v in combined.values()) == bucket["groups"] == 1
    multi[-1]["aborted_members"].reverse()
    assert aborted_bucket(multi) == bucket

    partial_rows = copy.deepcopy(one[1:])  # 八个成员只有七份快照，仍保留失败成员快照。
    partial = aborted_bucket(partial_rows)["by_root_cause_set"]["harness_crash"]
    assert partial["group_cost_seconds"]["count"] == 0
    assert partial["group_cost_seconds_known_partial"]["sum"] == 3605.0

    unknown_rows = copy.deepcopy(one)
    for row in unknown_rows[:-1]:
        row["elapsed_seconds"] = None
    unknown = aborted_bucket(unknown_rows)["by_root_cause_set"]["harness_crash"]
    assert unknown["group_cost_seconds"]["sum"] is None
    assert unknown["group_cost_seconds"]["unknown"] == 1
    assert unknown["group_cost_seconds_known_partial"]["count"] == 0

    missing_cause_rows = copy.deepcopy(one[:-2] + one[-1:])
    missing_cause = aborted_bucket(missing_cause_rows)["by_root_cause_set"]["<no_snapshot>"]
    assert missing_cause["group_cost_seconds_known_partial"]["sum"] == 4200.0
    assert missing_cause["group_cost_seconds"]["count"] == 0

    task_rows = copy.deepcopy(one)
    for i, seconds in enumerate((30, 40)):
        task_rows.append(dict(event="attempt_cost_snapshot", run_id="run1", physical_attempt_id=f"g9#p{i}",
                              rh2_prompt_group_id="g9", task_id="task_A", elapsed_seconds=seconds))
    task_rows.append(dict(event="group_consumed", run_id="run1", rh2_prompt_group_id="g9", task_id="task_A", member_count=2))
    task = summarize(task_rows)["by_task"]["task_A"]
    task_costs = {key: task[key]["elapsed_seconds"]["sum"] for key in
                  ("member_fields", "consumed_member_fields", "dropped_member_fields")}
    assert task_costs == {"member_fields": 4275.0, "consumed_member_fields": 70.0, "dropped_member_fields": 4205.0}
    result = dict(swapped_summaries_differ=True, first_costs=costs_a, swapped_costs=costs_b,
                  multi_cause=combined, reordered_causes_equal=True, missing_member=partial,
                  all_elapsed_unknown=unknown, missing_cause_snapshot=missing_cause, task_costs=task_costs)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
