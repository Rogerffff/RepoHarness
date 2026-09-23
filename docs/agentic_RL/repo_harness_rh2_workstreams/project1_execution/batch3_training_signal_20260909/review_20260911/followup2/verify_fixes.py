"""2026-09-15：I20 R4 / R6 最终窄复核，复用原 producer 探针，不回写历史证据。

在临时目录写真实 audit / bringup / emitter 形状记录，调用工作区的 loader 与报告。
只运行 CPU；没有 CC、Docker、API、GPU 或源代码修改。
"""
from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("i20_followup1", HERE.parent / "followup1/followup_probe.py")
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
original = previous.original


def append_events(path, rows, run):
    with path.open("a", encoding="utf-8") as fh:
        for row in rows:
            if row["run_id"] == run:
                fh.write(json.dumps(row) + "\n")


def main():
    result = {}
    with tempfile.TemporaryDirectory(prefix="rh2-i20-close-") as temp:
        root = Path(temp)
        original.make_audit(root / "A", "s-1")
        original.make_audit(root / "B", "s-2")
        steps = original.actual_step_events()
        append_events(root / "A/rh2_events_probe.jsonl", steps, "r1")
        summaries = []
        for selected in ("r1", None):
            report, _ = previous.report_paths([root / "A", root / "B"], run_id=selected)
            tasks = sorted(report["facets"]["reward_and_distribution"]["graded_attempts"]["by_task"])
            assert report["run_id"] == "r1" and report["audit_rows"] == report["bringup_rows"] == 1
            assert report["unattributed_audit_rows"] == report["unattributed_bringup_rows"] == 1
            assert tasks == ["task-s-1"]
            summaries.append({"selected_run": selected, "audit_rows": report["audit_rows"],
                              "bringup_rows": report["bringup_rows"], "unknown_audits": report["unattributed_audit_rows"],
                              "unknown_bringup": report["unattributed_bringup_rows"], "tasks": tasks})
        result["R4_fixed"] = summaries
        # B 尚无任何事件：直接读取真实目录，验证未绑定 run 的本地摘要仍然可用。
        audit_only, _ = previous.report_paths([root / "B"])
        assert audit_only["run_id"] is None and audit_only["audit_rows"] == audit_only["bringup_rows"] == 1
        assert audit_only["facets"]["execution_and_loss"]["groups"] is None
        assert audit_only["coverage"]["dis_and_support"] == "not_collected"
        result["audit_only_control"] = {"run_id": None, "audits": 1, "bringup": 1, "dis": "not_collected"}
        append_events(root / "B/rh2_events_probe.jsonl", steps, "r2")
        combined, _ = previous.report_paths([root / "A", root / "B"])
        totals = {rid: sub["facets"]["dis_and_support"]["totals_restored"]["dis_accepted_tokens"]
                  for rid, sub in combined["per_run"].items()}
        assert totals == {"r1": 16, "r2": 40}
        assert all(sub["audit_rows"] == sub["bringup_rows"] == 1 for sub in combined["per_run"].values())
        parent, _ = previous.report_paths([root], run_id="r2")
        assert parent["audit_rows"] == 0 and parent["unattributed_audit_rows"] == 2
        result["two_run_controls"] = {"tokens": totals, "parent_bundle_unknown_audits": 2}

    def versions(values):
        rows = previous.actual_version_rows(values)
        return original.build_run_report(events=rows, audits=[])["facets"]["staleness_and_alignment"]["behavior_versions_per_member"]

    multi = versions([["5"], ["6"]])
    assert multi["members"] == multi["multi_version"] == 1 and multi["single_version"] == multi["unknown"] == 0
    assert multi == versions([["6"], ["5"]])
    assert versions([["5"], ["5", "6"]]) == versions([["5", "6"], ["5"]])
    single = versions([["5"], ["5"]])
    assert single["single_version"] == 1 and single["multi_version"] == single["unknown"] == 0
    partial = versions([["5"], []])
    assert partial["single_version"] == partial["members_with_leaves_missing_versions"] == 1 and partial["unknown"] == 0
    partial_multi = versions([["5", "6"], []])
    assert partial_multi["multi_version"] == partial_multi["members_with_leaves_missing_versions"] == 1
    unknown = versions([[], []])
    assert unknown["unknown"] == 1 and unknown["single_version"] == unknown["multi_version"] == 0
    result["R6_fixed"] = {"multi": multi, "single": single, "partial_single": partial,
                           "partial_multi": partial_multi, "unknown": unknown, "leaf_order_invariant": True}
    rows = original.actual_group_events([10, 10, 10, 11], [0, 0, 0, 1])
    group = original.build_run_report(events=rows, audits=[])["facets"]["reward_and_distribution"]["delivered_groups"]
    assert group["members"] == group["member_rewards"]["count"] == 2 and group["member_rewards"]["sum"] == 1
    assert group["advantage_sign_approximation"]["positive"] == group["advantage_sign_approximation"]["negative"] == 1
    tp = original.tp_copy_probe()
    assert tp["actual_compared_action_tokens"] == 16
    result["R3_R5_unchanged_controls"] = {"members": 2, "reward_mean": 0.5, "positive": 1, "negative": 1,
                                          "compared_action_tokens": 16, "sample_dis_tp_gt_1_still_unsupported": True}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
