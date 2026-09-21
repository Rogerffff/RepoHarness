"""I21（第五组）：评测 attempt 不进训练统计——run 报告与成本汇总把它单列（Codex I21 审查 §3 第 3 条）。

audit 行用真实 writer（`write_execution_audit_record`）产生；评测块由同一个纯函数从 audit 事实派生。
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace as NS

POINT = "0123abcd4567"


def _ev(kind: str, run: str = "r1", bundle: int = 0, **fields) -> dict:
    return {"event": kind, "ts_unix": 1.0, "host": "h", "pid": 1, "run_id": run, "_bundle": bundle, **fields}


def _audit_row(tmp_path: Path, sid: str, *, evaluation: bool, pi: int = 0, outcome: str | None = "resolved", reward=1.0) -> dict:
    from repoharness2.adapters.slime.bringup import write_execution_audit_record
    from repoharness2.adapters.slime.generate import RolloutAudit

    audit = RolloutAudit(trajectory_id=sid, task_id=f"task-{pi}")
    audit.session_id = sid
    audit.physical_attempt_id = f"{sid}#p1-aaaaaaaa"
    audit.evaluation = evaluation
    if evaluation:
        audit.eval_dispatch = {"eval_point_id": POINT, "eval_rollout_id": 0, "target_weight_version": "7", "dataset": "swe_dev",
                               "dataset_index": 0, "prompt_index": pi, "sample_slot": 0, "n_samples_per_eval_prompt": 1, "num_prompts": 2}
    audit.outcome_v2 = {"termination_kind": "completed", "completion_class": "present_complete", "turn_weight_versions": ["7"],
                        "current_version_at_finalize": "7"}
    if outcome is not None:
        grading = NS(outcome=outcome, failure_category=None if outcome == "resolved" else "infra_failure", reward=reward,
                     report_id=f"rpt-{sid}", grader_version="swebench-4.1.0", infra_failure_detail="grading_container_killed", timings=None)
        audit.finalized = NS(grading_report=grading, eligibility_report=NS(report_id=f"elig-{sid}"), group_repair_signal=NS(degraded=False))
    path = tmp_path / f"{sid.replace('#', '_')}.jsonl"
    write_execution_audit_record(None, audit, path, model_name="Qwen/Qwen3-4B")
    row = json.loads(path.read_text().strip())
    row["_bundle"] = 0
    return row


def test_eval_attempts_are_reported_apart_from_training_attempts(world, tmp_path):
    from repoharness2.adapters.miles.run_report import build_run_report

    train = _audit_row(tmp_path, "miles_g0_m0", evaluation=False)
    assert train["evaluation"] is None  # 训练 attempt 没有评测块
    graded = _audit_row(tmp_path, f"eval-{POINT}-d0-p0_m0", evaluation=True, pi=0)
    infra = _audit_row(tmp_path, f"eval-{POINT}-d0-p1_m0", evaluation=True, pi=1, outcome="failed_to_grade", reward=None)
    assert graded["evaluation"]["result_class"] == "graded" and infra["evaluation"]["result_class"] == "reward_unavailable"
    events = [
        _ev("group_consumed", rh2_prompt_group_id="miles_g0", member_count=1),
        _ev("attempt_cost_snapshot", physical_attempt_id=train["physical_attempt_id"], rh2_prompt_group_id="miles_g0", elapsed_seconds=100.0, evaluation=False),
        _ev("attempt_cost_snapshot", physical_attempt_id=graded["physical_attempt_id"], rh2_prompt_group_id=f"eval-{POINT}-d0-p0",
            elapsed_seconds=50.0, evaluation=True, eval_point_id=POINT, disposition_hint="present"),
        _ev("eval_window", rollout_id=0, phase="start", active_groups=3, ok=None),
        _ev("eval_window", rollout_id=0, phase="end", active_groups=1, ok=True),
        _ev("eval_point", rollout_id=0, dataset="swe_dev", eval_point_ids=[POINT], planned=2, received=2, graded=1, resolved=1, unresolved=0,
            reward_unavailable=1, execution_missing=0, payload_missing=0, missing_members=[], duplicate_members=[],
            resolved_rate_graded=1.0, resolved_rate_planned=0.5, target_weight_version="7", observed_weight_versions=["7"],
            binding="verified", complete=False),
    ]
    report = build_run_report(events=events, audits=[train, graded, infra])
    assert report["audit_rows"] == 1 and report["eval_audit_rows"] == 2
    execution = report["facets"]["execution_and_loss"]
    assert execution["attempts_audited"] == 1  # 训练 facet 只数训练 attempt
    costs = execution["costs"]
    assert costs["snapshots"] == 1 and costs["unmatched_snapshots"] == 0  # 评测快照不算未匹配的训练快照
    assert costs["evaluation"]["snapshots"] == 1 and costs["evaluation"]["by_eval_point"][POINT]["members"] == 1
    assert costs["evaluation"]["member_fields"]["elapsed_seconds"]["sum"] == 50.0
    assert costs["terminals"]["consumed"]["member_fields"]["elapsed_seconds"]["sum"] == 100.0  # 训练成本不含评测的 50s

    facet = report["facets"]["evaluation"]
    assert facet["status"] == "collected" and facet["attempt_rows"] == 2
    point = facet["by_eval_point"][POINT]
    assert point["attempts"] == 2 and point["resolved"] == 1 and point["result_classes"] == {"graded": 1, "reward_unavailable": 1}
    assert point["unavailable_reasons"] == {"grading:infra_failure": 1} and point["eval_rollout_ids"] == [0]
    assert point["observed_weight_versions"] == ["7"] and point["target_weight_versions"] == ["7"]
    assert facet["points_complete"] == 0 and facet["points_incomplete"] == 1 and facet["points_binding"] == {"verified": 1}
    assert [w["active_groups"] for w in facet["eval_windows"]] == [3, 1]


def test_no_eval_records_is_not_collected_and_never_reads_as_a_finished_eval(world, tmp_path):
    from repoharness2.adapters.miles.run_report import build_run_report

    train = _audit_row(tmp_path, "miles_g0_m0", evaluation=False)
    report = build_run_report(events=[_ev("group_consumed", rh2_prompt_group_id="miles_g0", member_count=1)], audits=[train])
    facet = report["facets"]["evaluation"]
    assert facet["status"] == "not_collected" and facet["attempt_rows"] == 0 and any("no_eval_records" in r for r in facet["reasons"])
    # 只有 audit 行、没有钩子汇总 → partial：完整性 / 绑定未知，不推造
    only_audit = build_run_report(events=[], audits=[_audit_row(tmp_path, f"eval-{POINT}-d0-p0_m0", evaluation=True)])
    assert only_audit["facets"]["evaluation"]["status"] == "partial"
    assert any("no_eval_point_events" in r for r in only_audit["facets"]["evaluation"]["reasons"])


def test_eval_regrades_do_not_inflate_the_training_retry_statistics(world, tmp_path):
    """Codex I21 实施复核 IR3：重评分事件按 trajectory_id 与 audit 连接分成训练 / 评测 / 归属未知。"""

    from repoharness2.adapters.miles.run_report import build_run_report

    train = _audit_row(tmp_path, "miles_g0_m0", evaluation=False)
    evaluated = _audit_row(tmp_path, f"eval-{POINT}-d0-p0_m0", evaluation=True)

    def regrade(trajectory, op):
        return _ev("grading_regrade", trajectory_id=trajectory, op=op, category="docker_transport", attempt=1, detail="x")

    events = [regrade(train["trajectory_id"], "exec"), regrade(evaluated["trajectory_id"], "run"), regrade("miles_g9_m0", "inspect")]
    report = build_run_report(events=events, audits=[train, evaluated])
    training = report["facets"]["execution_and_loss"]["grading_regrades"]
    assert training["events"] == 1 and training["by_op_and_category"] == {"exec:docker_transport": 1}
    assert training["unattributed_events"] == 1 and training["unattributed_by_op_and_category"] == {"inspect:docker_transport": 1}
    assert report["facets"]["evaluation"]["grading_regrades"] == {"events": 1, "by_op_and_category": {"run:docker_transport": 1}}

    # 只有评测、没有训练 attempt：训练侧重评分为 0（修复前这里是 1）
    only_eval = build_run_report(events=[regrade(evaluated["trajectory_id"], "run")], audits=[evaluated])
    assert only_eval["facets"]["execution_and_loss"]["grading_regrades"]["events"] == 0
    assert only_eval["facets"]["evaluation"]["grading_regrades"]["events"] == 1
