"""I20 R1–R5 修后窄复核：复用上一轮真实 producer 探针，不覆盖原件。

仅在临时目录创建输入；结果同时记录已闭合反例与本次发现的直接余项。
不运行 CC / Docker / GPU；源码不作任何写入。
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace as NS

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("i20_original_probe", HERE.parent / "consumer_probe.py")
original = importlib.util.module_from_spec(spec)
spec.loader.exec_module(original)


def report_paths(paths, run_id=None):
    loaded = original.load_run_inputs(paths)
    return original.build_run_report(events=loaded["events"], audits=loaded["audits"],
                                     bringup=loaded["bringup"], run_id=run_id, sources=loaded["sources"]), loaded


def actual_version_rows(versions):
    """相同 execution 的不同训练行，沿真实 rollout emitter 输出各行版本。"""
    rows = []
    namespace = {"hashlib": hashlib,
                 "rh2_event_log": NS(emit=lambda event, **fields: rows.append(dict(event=event, run_id="r1", **fields)))}
    original.extract("reference/miles-rh2-integration/miles/ray/rollout/train_data_conversion.py", "compute_leaf_ordinals", namespace)
    emit = original.extract("reference/miles-rh2-integration/miles/ray/rollout/rollout_manager.py", "_emit_rollout_evidence", namespace)
    leaves = [NS(index=10, rollout_id=10, group_index=0, metadata={"instance_id": "task-1"},
                 get_reward_value=lambda args: 1.0, rollout_routed_experts=None, weight_versions=value,
                 tokens=[1, 2], status=NS(value="completed"), response_length=1) for value in versions]
    emit(NS(servers={}, weight_version=6, args=NS()), 0, [leaves])
    return rows


def main():
    result = {}
    with tempfile.TemporaryDirectory(prefix="rh2-i20-followup-") as temp:
        root = Path(temp)
        original.make_audit(root / "r1", "s-1")
        report, loaded = report_paths([root / "r1"])
        throughput = report["facets"]["throughput_and_resources"]
        segments = throughput["lifecycle_segments_seconds"]
        assert segments["test"]["sum"] == 40 and segments["sandbox_container_start"]["sum"] == 3.5
        assert "grading_queue_depth_at_enqueue" not in segments
        assert throughput["grading_queue_depth_at_enqueue"]["sum"] == 7
        result["R1_closed"] = {"test_seconds": 40, "container_start_seconds": 3.5,
                                "queue_depth_count": 7, "queue_depth_is_not_seconds": True}
        grading = report["facets"]["reward_and_distribution"]["graded_attempts"]
        assert grading["graded"] == 1 and grading["delivered_without_grading_record"] == 0
        unknown = original.build_run_report(events=[], audits=loaded["audits"], bringup=[])
        assert unknown["facets"]["reward_and_distribution"]["graded_attempts"] is None
        result["R2_closed"] = {"graded": grading["graded"], "without_grading_record": 0,
                                "missing_bringup_is_unknown": True}
        original.make_audit(root / "r2", "s-2")
        steps = original.actual_step_events()
        for row in steps:
            if row["run_id"] == "r1":
                file = root / "r1/rh2_events_probe.jsonl"
                with file.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(row) + "\n")
        # 两个输入 bundle，只有 r1 有可选事件；r2 的 audit / bringup 不具备 run 归属证据。
        mixed, _ = report_paths([root / "r1", root / "r2"], run_id="r1")
        result["R4_remaining_eventless_bundle"] = {
            "runs_seen": mixed["runs_seen"], "actual_r1_audits": mixed["audit_rows"],
            "expected_r1_audits": 1, "unattributed_audits": mixed["unattributed_audit_rows"],
            "expected_unattributed_audits": 1, "actual_r1_bringup_rows": mixed["bringup_rows"],
            "task_names_in_r1_report": sorted(mixed["facets"]["reward_and_distribution"]["graded_attempts"]["by_task"]),
            "reproduced": mixed["audit_rows"] == 2 and mixed["unattributed_audit_rows"] == 0,
        }
        assert result["R4_remaining_eventless_bundle"]["reproduced"]
        for row in steps:
            if row["run_id"] == "r2":
                file = root / "r2/rh2_events_probe.jsonl"
                with file.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(row) + "\n")
        combined, _ = report_paths([root / "r1", root / "r2"])
        totals = {rid: sub["facets"]["dis_and_support"]["totals_restored"]["dis_accepted_tokens"]
                  for rid, sub in combined["per_run"].items()}
        assert totals == {"r1": 16, "r2": 40}
        scoped, _ = report_paths([root / "r1", root / "r2"], run_id="r2")
        assert scoped["audit_rows"] == 1 and scoped["bringup_rows"] == 1
        parent, _ = report_paths([root], run_id="r2")
        assert parent["audit_rows"] == 0 and parent["unattributed_audit_rows"] == 2
        result["R4_positive_controls"] = {"per_run_tokens": totals, "scoped_audits": scoped["audit_rows"],
                                           "mixed_parent_audits_marked_unknown": parent["unattributed_audit_rows"]}
    rows = original.actual_group_events([10, 10, 10, 11], [0, 0, 0, 1])
    group = original.build_run_report(events=rows, audits=[])["facets"]["reward_and_distribution"]["delivered_groups"]
    assert group["members"] == 2 and group["member_rewards"]["count"] == 2 and group["member_rewards"]["sum"] == 1
    assert group["advantage_sign_approximation"]["positive"] == 1 and group["advantage_sign_approximation"]["negative"] == 1
    result["R3_closed"] = {"members": 2, "training_rows": group["training_rows"], "reward_mean": 0.5,
                            "positive": 1, "negative": 1}
    tp = original.tp_copy_probe()
    assert tp["actual_compared_action_tokens"] == tp["expected_compared_action_tokens"] == 16
    unsupported = original.build_run_report(events=[{"event": "sample_dis_accounting", "run_id": "r1", "entries": []}], audits=[])
    label = unsupported["facets"]["dis_and_support"]["sample_dis_accounting"]["tp_copies"]
    assert label.startswith("unsupported")
    result["R5_closed_with_limitation"] = {"compared_action_tokens": 16, "sample_dis_limitation": label,
                                           "sample_dis_raw_accepted_sum_still_contains_tp_copies": tp["actual_accepted_tokens"]}
    def member_versions(values):
        output = original.build_run_report(events=actual_version_rows(values), audits=[])
        return output["facets"]["staleness_and_alignment"]["behavior_versions_per_member"]
    actual = member_versions([["5"], ["6"]])
    first = member_versions([["5"], ["5", "6"]])
    reversed_rows = member_versions([["5", "6"], ["5"]])
    positive = member_versions([["5"], ["5"]])
    result["R6_member_version_regression"] = {
        "two_leaf_versions": [["5"], ["6"]], "actual": actual,
        "expected": {"single_version": 0, "multi_version": 1, "unknown": 0},
        "same_member_first_leaf_single": first, "same_member_leaf_order_reversed": reversed_rows,
        "single_version_positive_control": positive,
        "reproduced": actual["single_version"] == 1 and actual["multi_version"] == 0 and first != reversed_rows,
    }
    assert result["R6_member_version_regression"]["reproduced"]
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
