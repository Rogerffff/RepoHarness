"""I20 首版（第三组 §0/§0.1 第 4 条）：离线 run 报告工具——合成行 + 真实汇总器，双 lane 都跑。

被测 = `repoharness2.adapters.miles.run_report`（纯 stdlib 消费者）。oracle = Brief §3 的统计口径：缺失不填零、
均值 × num_rollouts 还原总量、多 rank 副本只取一份、跨 run 不混连、进行中 / 未知单列、无可比同版本样本显示"无"。
"""

from __future__ import annotations

import json

import pytest


def _ev(kind: str, run: str = "r1", **fields) -> dict:
    return {"event": kind, "ts_unix": 1.0, "host": "h", "pid": 1, "run_id": run, **fields}


def _audit(task="A", *, reward=1.0, outcome="resolved", rows=1, trainable=10, inputs=100, excluding_last=0, clues=(),
           harness_seconds=30.0, segments=None, disposition="delivered", kind="completed") -> dict:
    return {
        "task_id": task,
        "disposition": disposition,
        "termination": {"kind": kind},
        "failure_records": [],
        "context_shrink_reasons": list(clues),
        "grading": {"outcome": outcome, "failure_category": None, "reward": reward,
                    "timings": {"queue_wait_seconds": 2.0, "test_seconds": 40.0}},
        "turn_coverage": {"fork_threshold_tokens": 0, "turns_generated": rows + 1, "turns_trained": rows + 1, "turns_empty_output": 0,
                          "turns_dropped_realign": 0, "turns_dropped_merge": 0, "training_rows": rows,
                          "trainable_tokens_total": trainable, "input_tokens_total": inputs,
                          "input_tokens_excluding_last_row": excluding_last, "fork_events": [{}] * (rows - 1)},
        "timing_summary": {"harness_run_seconds": harness_seconds, "total_audit_seconds": harness_seconds + 5,
                           "lifecycle_timing": {"segments": segments or {"test": 40.0, "grading_queue_wait": None}}},
        "episode_deadline": {"model_call_queue_wait_seconds_total": 1.5},
    }


def _step(rollout, step, *, dp_rank=0, pp_last=True, applied=True, num_rollouts=8, accepted=1000.0, provenance=1250.0,
          candidate=500.0, grad_norm=0.5, adam=(3, 4)) -> dict:
    metrics = None
    if pp_last:
        metrics = {"dis_microbatch_provenance_tokens": provenance, "dis_accepted_tokens": accepted,
                   "dis_rejected_tokens": provenance - accepted, "dis_candidate_signal_tokens": candidate,
                   "dis_singleton_accepted_tokens": 100.0, "dis_zero_advantage_accepted_tokens": 50.0,
                   "dis_rejected_low_tokens": 150.0, "dis_rejected_high_tokens": 100.0,
                   "dis_support_size_1": 100.0, "dis_support_size_2_3": 1150.0, "dis_zero_contribution_microbatch": 0.0}
    return _ev("train_step", rollout_id=rollout, step_id=step, attempt=1, outcome="NORMAL" if applied else "SKIPPED_ZERO_SIGNAL",
               optimizer_step_applied=applied, adam_step_before=adam[0], adam_step_after=adam[1], scheduler_steps_before=0,
               scheduler_steps_after=num_rollouts, num_rollouts=num_rollouts, grad_norm=grad_norm, duration_seconds=1.5,
               zero_signal_scan_seconds=None, rank=dp_rank, dp_rank=dp_rank, is_pp_last_stage=pp_last, metrics=metrics)


@pytest.fixture()
def report():
    from repoharness2.adapters.miles.run_report import build_run_report

    return build_run_report


def test_audits_only_marks_event_facets_not_collected_and_never_zero_loss(report):
    out = report(events=[], audits=[_audit(), _audit(task="B", reward=0.0, outcome="unresolved")])
    cov = out["coverage"]
    assert cov["execution_and_loss"] == "partial" and cov["dis_and_support"] == "not_collected"
    assert cov["optimizer_and_publish"] == "not_collected" and cov["staleness_and_alignment"] == "not_collected"
    ex = out["facets"]["execution_and_loss"]
    assert ex["groups"] is None and ex["costs"] is None  # 不是 0 组 / 0 丢弃
    assert any(r.startswith("no_group_or_cost_events") for r in ex["reasons"])
    assert ex["attempts_audited"] == 2 and ex["in_progress_attempts"] is None
    rw = out["facets"]["reward_and_distribution"]["audit_grading"]
    assert rw["outcomes"] == {"resolved": 1, "unresolved": 1} and rw["reward"]["count"] == 2 and rw["reward"]["unknown"] == 0
    assert out["facets"]["reward_and_distribution"]["by_task"]["B"]["reward_mean"] == 0.0


def test_unknown_reward_and_missing_turn_coverage_are_counted_not_zeroed(report):
    a = _audit(reward=None)
    b = _audit(task="B")
    del b["turn_coverage"]
    out = report(events=[], audits=[a, b])
    rw = out["facets"]["reward_and_distribution"]["audit_grading"]["reward"]
    assert rw["count"] == 1 and rw["unknown"] == 1
    cov = out["facets"]["action_coverage"]
    assert cov["status"] == "partial" and cov["attempts_without_turn_coverage"] == 1 and cov["attempts_with_turn_coverage"] == 1


def test_fork_rows_are_one_attempt_and_clues_are_not_compaction_counts(report):
    out = report(events=[], audits=[_audit(rows=3, trainable=30, inputs=900, excluding_last=500, clues=("session: turn 3: prompt 40 < 0.6 x max_seen 160",))])
    cov = out["facets"]["action_coverage"]
    assert cov["sums"]["training_rows"] == 3 and cov["training_rows_per_attempt"]["count"] == 1  # 三行一题
    assert cov["fork_events_total"] == 2 and cov["sums"]["input_tokens_excluding_last_row"] == 500
    assert cov["context_length_drop_clues"] == {"attempts_with_clues": 1, "clue_lines_total": 1,
                                                "note": cov["context_length_drop_clues"]["note"]}
    assert "不是压缩次数" in cov["context_length_drop_clues"]["note"]


def test_train_step_totals_restore_mean_times_num_rollouts_and_dedupe_rank_copies(report):
    events = [
        _step(0, 0, dp_rank=0), _step(0, 0, dp_rank=1),  # 同一 step 的两个 rank 副本
        _step(0, 1, dp_rank=0, num_rollouts=4, accepted=1500.0, provenance=1800.0, candidate=600.0),
        _step(0, 2, dp_rank=0, pp_last=False),  # 非 pp 末段：无 metrics
    ]
    out = report(events=events, audits=[])
    dis = out["facets"]["dis_and_support"]
    assert dis["steps_seen"] == 3 and dis["steps_with_metrics"] == 2
    # 均值 × num_rollouts：1000×8 + 1500×4 = 14000（不是 2500 的均值口径）
    assert dis["totals_restored"]["dis_accepted_tokens"] == 14000.0
    assert dis["totals_restored"]["dis_microbatch_provenance_tokens"] == 1250 * 8 + 1800 * 4
    assert dis["ratios_over_totals"]["accepted_over_provenance"] == round(14000 / (1250 * 8 + 1800 * 4), 4)
    assert dis["ratios_over_totals"]["candidate_signal_over_accepted"] == round((500 * 8 + 600 * 4) / 14000, 4)
    opt = out["facets"]["optimizer_and_publish"]["train_steps"]
    assert opt["steps"] == 3 and opt["optimizer_steps_applied"] == 3 and opt["applied_steps_with_adam_increment_1"] == 3


def test_skipped_steps_longest_run_and_weight_update_gaps(report):
    events = [_step(0, 0), _step(0, 1, applied=False), _step(0, 2, applied=False), _step(0, 3),
              _ev("weight_update", rollout_id=0, version_before=5, version_after=6, duration_seconds=2.0),
              _ev("weight_update", rollout_id=1, version_before=6, version_after=8, duration_seconds=2.5),
              _ev("train_step_consumed", rollout_id=0, step_id=0, dp_rank=0, rank=0, sample_indices=[0, 1]),
              _ev("train_step_consumed", rollout_id=0, step_id=0, dp_rank=1, rank=1, sample_indices=[1, 2, 3]),
              _ev("train_step_consumed", rollout_id=0, step_id=1, dp_rank=0, rank=0, sample_indices=None, error="step attribution failed")]
    opt = report(events=events, audits=[])["facets"]["optimizer_and_publish"]
    assert opt["train_steps"]["optimizer_steps_not_applied"] == 2 and opt["train_steps"]["longest_run_without_applied_step"] == 2
    assert opt["weight_updates"]["count"] == 2 and opt["weight_updates"]["non_increment_by_one"] == 1
    assert opt["consumed_samples_per_step"]["count"] == 1 and opt["consumed_samples_per_step"]["max"] == 4.0  # 两 rank 并集 {0,1,2,3}
    assert opt["train_step_consumed_error_rows"] == 1 and opt["status"] == "collected"


def test_staleness_and_logprob_compare_show_no_comparable_samples_instead_of_zero(report):
    events = [
        _ev("group_consumed", rh2_prompt_group_id="g1", sample_indices=[0, 1], task_id="A", staleness=2, oldest_weight_version=3, current_weight_version=5),
        _ev("rollout_group", rollout_id=0, group_index=0, sample_indices=[0, 1], rewards=[1.0, 0.0], behavior_versions=[["3", "4"], ["4"]]),
        _ev("rollout_group", rollout_id=0, group_index=1, sample_indices=[2, 3], rewards=[1.0, 1.0], behavior_versions=[["5"], ["5"]]),
        _ev("logprob_compare", rollout_id=0, dp_rank=0, trainer_current_version=5,
            entries=[{"sample_index": 0, "leaf_ordinal": 0, "same_version": False, "num_tokens": 10, "total_tokens": 12, "mean_abs_diff": 0.3, "length_mismatch": False}]),
    ]
    out = report(events=events, audits=[])
    st = out["facets"]["staleness_and_alignment"]
    assert st["consumed_staleness"]["count"] == 1 and st["consumed_staleness"]["max"] == 2  # 来自 summarize_group_events 的 _stats 口径
    assert st["behavior_versions_per_sample"] == {"single_version": 3, "multi_version": 1, "unknown": 0}
    assert st["logprob_compare"]["no_comparable_same_version_samples"] is True
    assert st["logprob_compare"]["same_version"]["rows"] == 0 and st["logprob_compare"]["cross_version"]["comparable_action_tokens"] == 10
    rw = out["facets"]["reward_and_distribution"]["rollout_groups"]
    assert rw["groups"] == 2 and rw["zero_variance_groups"] == 1 and rw["all_one_groups"] == 1
    assert rw["consumed_member_rewards"]["count"] == 2 and rw["groups_not_matched_to_consumed_event"] == 1
    assert rw["advantage_sign_approximation"]["positive"] == 1 and rw["advantage_sign_approximation"]["zero"] == 2


def test_run_id_scoping_keeps_runs_apart_and_cli_writes_json(tmp_path):
    from repoharness2.adapters.miles import run_report

    run_dir = tmp_path / "run"
    (run_dir / "events").mkdir(parents=True)
    rows = [
        _ev("attempt_cost_snapshot", physical_attempt_id="a#p1", rh2_prompt_group_id="miles_g0", task_id="A", elapsed_seconds=10.0),
        _ev("group_consumed", rh2_prompt_group_id="miles_g0", task_id="A", staleness=0, sample_indices=[0], member_count=1),
        _ev("attempt_cost_snapshot", run="r2", physical_attempt_id="b#p1", rh2_prompt_group_id="miles_g0", task_id="A", elapsed_seconds=100.0),
        _ev("group_consumed", run="r2", rh2_prompt_group_id="miles_g0", task_id="A", staleness=0, sample_indices=[0], member_count=1),
        _ev("drain_complete", rollout_id=0, current_weight_version=5, target_groups=1, elapsed_seconds=3.0, consumed_total=1, drop_totals={}),
    ]
    (run_dir / "events" / "rh2_events_h_1.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    (run_dir / "fa_execution_audit.jsonl").write_text(json.dumps(_audit()) + "\n" + "not json\n", encoding="utf-8")
    out_file = tmp_path / "report.json"
    assert run_report.main([str(run_dir), "--json", str(out_file)]) == 0
    report = json.loads(out_file.read_text(encoding="utf-8"))
    assert report["schema_id"] == "rh2.run_report.v1" and report["sources"]["audit_rows"] == 1 and report["sources"]["malformed_audit_rows"] == 1
    costs = report["facets"]["execution_and_loss"]["costs"]["terminals"]["consumed"]
    assert costs["groups"] == 2 and costs["group_cost_seconds"]["max"] == 100.0 and costs["group_cost_seconds"]["min"] == 10.0  # 两 run 不混连
    assert report["coverage"]["throughput_and_resources"] == "collected"
    assert report["facets"]["throughput_and_resources"]["drain_complete"]["count"] == 1
    assert report["facets"]["throughput_and_resources"]["lifecycle_segments_seconds"]["grading_queue_wait"]["unknown"] == 1
    scoped = run_report.build_run_report(events=rows, audits=[], run_id="r1")
    assert scoped["events_foreign_run"] == 2 and scoped["facets"]["execution_and_loss"]["costs"]["terminals"]["consumed"]["groups"] == 1
