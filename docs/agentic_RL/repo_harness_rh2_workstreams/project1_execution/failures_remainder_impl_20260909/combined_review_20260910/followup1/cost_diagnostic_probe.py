"""R6 余项：失败成员成本与整组连带成本不是同一项观测。只调用真实离线汇总器。"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[7]
spec = importlib.util.spec_from_file_location(
    "drop_cost_followup", ROOT / "rh2/src/repoharness2/adapters/miles/drop_events.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def rows(first_long: bool):
    out = []
    settings = [
        ("g0", "harness_crash", 600 if first_long else 10),
        ("g1", "grading_image_pull_failed", 10 if first_long else 600),
    ]
    for group, reason, seconds in settings:
        for member in range(8):
            out.append(dict(
                event="attempt_cost_snapshot", run_id="run1", physical_attempt_id=f"{group}#p{member}",
                rh2_prompt_group_id=group, task_id="task_A", elapsed_seconds=5 if member == 7 else seconds,
                reason_code=reason if member == 7 else None,
            ))
        out.append(dict(
            event="group_filtered", run_id="run1", rh2_prompt_group_id=group, task_id="task_A",
            member_count=8, drop_stage="put_aborted", reason_code="aborted_member",
            aborted_members=[dict(physical_attempt_id=f"{group}#p7")],
        ))
    return out


if __name__ == "__main__":
    first = module.summarize_attempt_costs(rows(True))
    second = module.summarize_attempt_costs(rows(False))
    result = dict(
        same_summary_when_collateral_costs_swap=(first == second),
        truth_first=dict(harness_crash_group_seconds=4205, grading_image_pull_failed_group_seconds=75),
        truth_second=dict(harness_crash_group_seconds=75, grading_image_pull_failed_group_seconds=4205),
        reported_by_root_cause=first["terminals"]["aborted_member"]["by_root_cause"],
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
