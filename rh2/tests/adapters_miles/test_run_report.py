"""I20 首版（第三组 §0/§0.1 第 4 条；Codex 09-11 聚焦复核 R1–R5 修正）：离线 run 报告工具——真实 rh2 writer + 按真实
emitter 形状的事件行 + 真实汇总器，双 lane 都跑。

fixture 来源：audit 行由真实 `RolloutAudit` + `write_execution_audit_record` 写出（含真实 `AttemptLifecycleTiming.to_dict()`
的 `segments_seconds` / 队列深度键）；评分记录由真实 `BringupService.record_event` 写到 bringup_events.jsonl；
rollout_group / train_step 行按 fork emitter 的字段形状（逐叶 sample_indices + leaf_ordinals + rewards；metrics 只在 pp 末段）
手工构造——fork 原函数的 AST 执行版见 test_run_report_real_emitters.py（integration_base）。
oracle = Brief §3：缺失不填零、均值 × num_rollouts 还原、多 rank 副本只取一份、成员先归并再统计、跨 run 不混连、
未知与进行中单列、无可比同版本样本显示"无"。
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace as NS

import pytest


def _ev(kind: str, run: str = "r1", bundle: int = 0, **fields) -> dict:
    return {"event": kind, "ts_unix": 1.0, "host": "h", "pid": 1, "run_id": run, "_bundle": bundle, **fields}


def _write_real_audit(directory: Path, sid: str, *, task="task-A", reward=1.0, outcome="resolved", with_grading=True,
                      test_seconds=40.0, queue_depth=7, backpressure=False):
    """真实 writer：audit 记录（不含评分）+ bringup 交付记录（含评分块）。"""

    from repoharness2.adapters.slime.bringup import BringupService, write_execution_audit_record
    from repoharness2.adapters.slime.generate import RolloutAudit

    directory.mkdir(parents=True, exist_ok=True)
    audit = RolloutAudit(trajectory_id=sid, task_id=task)
    audit.session_id = sid
    audit.physical_attempt_id = f"attempt-{sid}"
    audit.lifecycle_timing.set("test", test_seconds)
    audit.lifecycle_timing.set("sandbox_container_start", 3.5)
    audit.lifecycle_timing.grading_queue_depth_at_enqueue = queue_depth
    audit.lifecycle_timing.grading_backpressure_triggered = backpressure
    grading = NS(outcome=outcome, failure_category=None, reward=reward, timings=None) if with_grading else None
    audit.finalized = NS(
        grading_report=grading,
        eligibility_report=NS(report_id=f"report-{sid}", eligibility_class="valid_for_training"),
        group_repair_signal=NS(degraded=False),
    )
    write_execution_audit_record(None, audit, directory / "fa_execution_audit.jsonl")
    service = NS(orchestrator=NS(audits=[audit]), registry=NS(weight_versions={}, stats={}), events_path=directory / "bringup_events.jsonl")
    BringupService.record_event(service, args=None, sample=NS(session_id=sid, index=10, group_index=0, metadata={"instance_id": task}),
                                result=[], wall_seconds=50.0)
    return audit


def _step(rollout, step, *, run="r1", bundle=0, dp_rank=0, pp_last=True, applied=True, num_rollouts=8, accepted=1000.0,
          provenance=1250.0, candidate=500.0, grad_norm=0.5, adam=(3, 4)) -> dict:
    metrics = None
    if pp_last:
        metrics = {"dis_microbatch_provenance_tokens": provenance, "dis_accepted_tokens": accepted,
                   "dis_rejected_tokens": provenance - accepted, "dis_candidate_signal_tokens": candidate,
                   "dis_singleton_accepted_tokens": 100.0, "dis_zero_advantage_accepted_tokens": 50.0,
                   "dis_rejected_low_tokens": 150.0, "dis_rejected_high_tokens": 100.0,
                   "dis_support_size_1": 100.0, "dis_support_size_2_3": 1150.0, "dis_zero_contribution_microbatch": 0.0}
    return _ev("train_step", run=run, bundle=bundle, rollout_id=rollout, step_id=step, attempt=1, outcome="NORMAL" if applied else "SKIPPED_ZERO_SIGNAL",
               optimizer_step_applied=applied, adam_step_before=adam[0], adam_step_after=adam[1], scheduler_steps_before=0,
               scheduler_steps_after=num_rollouts, num_rollouts=num_rollouts, grad_norm=grad_norm, duration_seconds=1.5,
               zero_signal_scan_seconds=None, rank=dp_rank, dp_rank=dp_rank, is_pp_last_stage=pp_last, metrics=metrics)


def _rollout_group(rollout, group, members: list[tuple[int, list[float]]], *, run="r1") -> dict:
    """按 fork `_emit_rollout_evidence` 的形状：逐叶一行——FORK 成员的 sample_index 重复、leaf_ordinal 递增、reward 逐叶重复。"""

    indices, ordinals, rewards, versions = [], [], [], []
    for sample_index, leaf_rewards in members:
        for ordinal, reward in enumerate(leaf_rewards):
            indices.append(sample_index)
            ordinals.append(ordinal)
            rewards.append(reward)
            versions.append(["5"])
    return _ev("rollout_group", run=run, rollout_id=rollout, group_index=group, instance_id="task-A", sample_indices=indices,
               leaf_ordinals=ordinals, rewards=rewards, behavior_versions=versions, weight_version_spans=[None] * len(indices),
               statuses=["completed"] * len(indices), response_lengths=[1] * len(indices), routing_tape=[None] * len(indices))


@pytest.fixture()
def build():
    from repoharness2.adapters.miles.run_report import build_run_report

    return build_run_report


def test_real_audit_writer_lifecycle_segments_are_seconds_and_queue_depth_is_not(tmp_path):
    """R1：真实 writer 的分段键是 segments_seconds；排队深度 7 是计数，不能进秒数桶；未设的段记 unknown。"""

    from repoharness2.adapters.miles.run_report import build_run_report, load_run_inputs

    _write_real_audit(tmp_path / "run", "s1")
    inputs = load_run_inputs([tmp_path / "run"])
    report = build_run_report(events=[], audits=inputs["audits"], bringup=inputs["bringup"], sources=inputs["sources"])
    tp = report["facets"]["throughput_and_resources"]
    segs = tp["lifecycle_segments_seconds"]
    assert segs["test"]["sum"] == 40.0 and segs["sandbox_container_start"]["sum"] == 3.5
    assert "grading_queue_depth_at_enqueue" not in segs and segs["grading_queue_wait"]["unknown"] == 1
    assert tp["grading_queue_depth_at_enqueue"]["sum"] == 7.0 and tp["grading_backpressure_triggered_attempts"] == 0
    assert tp["audits_without_lifecycle_timing"] == 0


def test_real_bringup_events_carry_grading_and_audit_alone_means_unknown_not_ungraded(tmp_path):
    """R2：评分在 bringup_events.jsonl，不在 audit；只给 audit 时报"无法知道"，给了 bringup 才有已评分总体。"""

    from repoharness2.adapters.miles.run_report import build_run_report, load_run_inputs

    _write_real_audit(tmp_path / "run", "s1", reward=1.0)
    _write_real_audit(tmp_path / "run", "s2", task="task-B", reward=0.0, outcome="unresolved")
    _write_real_audit(tmp_path / "run", "s3", with_grading=False)  # 交付记录在、无评分块 = 已知没有评分
    inputs = load_run_inputs([tmp_path / "run"])
    only_audits = build_run_report(events=[], audits=inputs["audits"], bringup=[])
    rw = only_audits["facets"]["reward_and_distribution"]
    assert rw["graded_attempts"] is None and any(r.startswith("no_bringup_events") for r in rw["reasons"])
    full = build_run_report(events=[], audits=inputs["audits"], bringup=inputs["bringup"])
    graded = full["facets"]["reward_and_distribution"]["graded_attempts"]
    assert graded["delivery_records"] == 3 and graded["graded"] == 2 and graded["delivered_without_grading_record"] == 1
    assert graded["outcomes"] == {"resolved": 1, "unresolved": 1} and graded["reward"]["count"] == 2
    assert graded["by_task"]["task-B"]["reward_mean"] == 0.0 and graded["by_task"]["task-A"]["reward_mean"] == 1.0
    assert graded["audited_attempts_without_delivery_record"] == 0 and graded["eligibility_classes"] == {"valid_for_training": 3}
    assert full["facets"]["throughput_and_resources"]["grading_timings"] == {}  # timings=None：没有就是没有


def test_fork_rows_merge_into_members_before_reward_statistics(build):
    """R3：两个 execution（reward 0 与 1），第一个分三行——真实事件为 sample_indices=[10,10,10,11]、rewards=[0,0,0,1]。
    成员统计：2 个成员、均值 0.5、优势符号正 1 / 负 1；行分布另列（3 行 + 1 行）。"""

    rows = [_rollout_group(0, 0, [(10, [0.0, 0.0, 0.0]), (11, [1.0])]),
            _ev("group_consumed", rh2_prompt_group_id="g0", sample_indices=[10, 10, 10, 11], group_index=0, task_id="task-A", staleness=0)]
    dg = build(events=rows, audits=[])["facets"]["reward_and_distribution"]["delivered_groups"]
    assert dg["groups"] == 1 and dg["members"] == 2 and dg["training_rows"] == 4
    assert dg["member_rewards"] == {"count": 2, "min": 0.0, "p50": 0.0, "p95": 1.0, "max": 1.0, "sum": 1.0, "unknown": 0}
    assert dg["advantage_sign_approximation"]["positive"] == 1 and dg["advantage_sign_approximation"]["negative"] == 1
    assert dg["training_rows_per_member"]["max"] == 3.0 and dg["member_reward_conflicts"] == 0
    assert dg["groups_not_matched_to_consumed_event"] == 0
    # 同成员各叶 reward 不一致 = 数据矛盾：计数，且该成员不进 reward 统计（不静默选第一条）
    conflict = _rollout_group(1, 0, [(20, [1.0, 0.0]), (21, [1.0])])
    dg2 = build(events=[conflict], audits=[])["facets"]["reward_and_distribution"]["delivered_groups"]
    assert dg2["member_reward_conflicts"] == 1 and dg2["member_rewards"]["count"] == 1


def test_train_step_totals_restore_mean_times_num_rollouts_and_dedupe_rank_copies(build):
    events = [
        _step(0, 0, dp_rank=0), _step(0, 0, dp_rank=1),  # 同一 step 的两个 rank 副本
        _step(0, 1, dp_rank=0, num_rollouts=4, accepted=1500.0, provenance=1800.0, candidate=600.0),
        _step(0, 2, dp_rank=0, pp_last=False),  # 非 pp 末段：无 metrics
    ]
    out = build(events=events, audits=[])
    dis = out["facets"]["dis_and_support"]
    assert dis["steps_seen"] == 3 and dis["steps_with_metrics"] == 2
    assert dis["totals_restored"]["dis_accepted_tokens"] == 14000.0  # 1000×8 + 1500×4，不是均值口径
    assert dis["ratios_over_totals"]["candidate_signal_over_accepted"] == round((500 * 8 + 600 * 4) / 14000, 4)
    opt = out["facets"]["optimizer_and_publish"]["train_steps"]
    assert opt["steps"] == 3 and opt["optimizer_steps_applied"] == 3 and opt["applied_steps_with_adam_increment_1"] == 3


def test_same_step_ids_in_two_runs_are_not_collapsed_and_runs_are_reported_apart(build):
    """R4：两 run 各有 (0,0) step——默认输入不混连（逐 run 子报告），指定 run 只取该 run 的事件与归属该 run 的 audit。"""

    events = [_step(0, 0, run="r1", accepted=2.0, provenance=4.0), _step(0, 0, run="r2", bundle=1, accepted=5.0, provenance=8.0),
              _ev("train_step_consumed", run="r1", rollout_id=0, step_id=0, dp_rank=0, rank=0, sample_indices=[10]),
              _ev("train_step_consumed", run="r2", bundle=1, rollout_id=0, step_id=0, dp_rank=0, rank=0, sample_indices=[10])]
    audits = [{"trajectory_id": "a1", "task_id": "A", "disposition": "delivered", "_bundle": 0},
              {"trajectory_id": "b1", "task_id": "B", "disposition": "delivered", "_bundle": 1}]
    combined = build(events=events, audits=audits)
    assert combined["multi_run"] is True and combined["runs_seen"] == ["r1", "r2"] and "facets" not in combined
    assert combined["per_run"]["r1"]["facets"]["dis_and_support"]["totals_restored"]["dis_accepted_tokens"] == 16.0
    assert combined["per_run"]["r2"]["facets"]["dis_and_support"]["totals_restored"]["dis_accepted_tokens"] == 40.0
    assert combined["per_run"]["r1"]["audit_rows"] == 1 and combined["per_run"]["r2"]["audit_rows"] == 1
    scoped = build(events=events, audits=audits, run_id="r2")
    assert scoped["run_id"] == "r2" and scoped["facets"]["dis_and_support"]["totals_restored"]["dis_accepted_tokens"] == 40.0
    assert scoped["audit_rows"] == 1 and scoped["audit_rows_excluded_other_or_unknown_run"] == 1 and scoped["events_foreign_run"] == 2
    assert scoped["facets"]["optimizer_and_publish"]["consumed_samples_per_step"]["count"] == 1
    # bundle 内有两个 run 的事件 → 该 bundle 的 audit 归属未知：默认多 run 时只计数、不并入任何 run
    mixed = build(events=[_step(0, 0, run="r1"), _step(0, 1, run="r2")], audits=[{"trajectory_id": "x", "_bundle": 0}])
    assert mixed["unattributed_audit_rows"] == 1 and mixed["per_run"]["r1"]["audit_rows"] == 0


def test_skipped_steps_longest_run_does_not_cross_runs_and_weight_update_gaps(build):
    events = [_step(0, 0), _step(0, 1, applied=False), _step(0, 2, applied=False),
              _step(0, 0, run="r2", bundle=1, applied=False), _step(0, 1, run="r2", bundle=1, applied=False), _step(0, 2, run="r2", bundle=1),
              _ev("weight_update", rollout_id=0, version_before=5, version_after=6, duration_seconds=2.0),
              _ev("weight_update", rollout_id=1, version_before=6, version_after=8, duration_seconds=2.5)]
    out = build(events=events, audits=[])
    assert out["multi_run"] is True
    assert out["per_run"]["r1"]["facets"]["optimizer_and_publish"]["train_steps"]["longest_run_without_applied_step"] == 2
    assert out["per_run"]["r2"]["facets"]["optimizer_and_publish"]["train_steps"]["longest_run_without_applied_step"] == 2
    wu = out["per_run"]["r1"]["facets"]["optimizer_and_publish"]["weight_updates"]
    assert wu["count"] == 2 and wu["non_increment_by_one"] == 1


def test_staleness_logprob_compare_dedupes_tp_copies_and_flags_no_same_version(build):
    """R5：logprob_compare 逐叶 entries 按 (run, rollout, sample, leaf) 精确去副本；矛盾计数；sample_dis_accounting 不去重只标注。"""

    entry = {"sample_index": 10, "leaf_ordinal": 0, "same_version": False, "num_tokens": 5, "total_tokens": 5, "mean_abs_diff": 0.2, "length_mismatch": False}
    other = {"sample_index": 11, "leaf_ordinal": 0, "same_version": False, "num_tokens": 11, "total_tokens": 11, "mean_abs_diff": 0.1, "length_mismatch": False}
    conflict = dict(entry, mean_abs_diff=0.9)
    events = [
        _ev("logprob_compare", rollout_id=0, dp_rank=0, trainer_current_version=5, entries=[entry]),
        _ev("logprob_compare", rollout_id=0, dp_rank=0, trainer_current_version=5, entries=[entry]),  # TP 副本
        _ev("logprob_compare", rollout_id=0, dp_rank=1, trainer_current_version=5, entries=[other, other]),
        _ev("logprob_compare", rollout_id=0, dp_rank=1, trainer_current_version=5, entries=[conflict]),
        _ev("sample_dis_accounting", entries=[{"sample_index": 10, "leaf_ordinal": 0, "accepted_tokens": 3, "provenance_tokens": 5}] * 2),
        _ev("group_consumed", rh2_prompt_group_id="g1", sample_indices=[10, 11], task_id="A", staleness=2, oldest_weight_version=3, current_weight_version=5),
    ]
    st = build(events=events, audits=[])["facets"]["staleness_and_alignment"]
    lc = st["logprob_compare"]
    assert lc["cross_version"]["rows"] == 2 and lc["cross_version"]["comparable_action_tokens"] == 16
    assert lc["duplicate_entries_dropped"] == 2 and lc["conflicting_entries"] == 1 and lc["no_comparable_same_version_samples"] is True
    assert st["consumed_staleness"]["count"] == 1 and st["consumed_staleness"]["max"] == 2
    dis = build(events=events, audits=[])["facets"]["dis_and_support"]["sample_dis_accounting"]
    assert dis["accepted_tokens_sum"] == 6 and dis["tp_copies"].startswith("unsupported")  # 无 rollout_id：不去重、明说


def test_cli_reads_a_run_bundle_and_never_shows_missing_events_as_zero_loss(tmp_path):
    from repoharness2.adapters.miles import run_report

    run_dir = tmp_path / "run"
    _write_real_audit(run_dir / "artifacts", "s1")
    (run_dir / "events").mkdir(parents=True)
    rows = [_ev("attempt_cost_snapshot", physical_attempt_id="attempt-s1", rh2_prompt_group_id="miles_g0", task_id="task-A", elapsed_seconds=10.0),
            _ev("group_consumed", rh2_prompt_group_id="miles_g0", task_id="task-A", staleness=0, sample_indices=[10], member_count=1),
            _ev("drain_complete", rollout_id=0, current_weight_version=5, target_groups=1, elapsed_seconds=3.0, consumed_total=1, drop_totals={})]
    (run_dir / "events" / "rh2_events_h_1.jsonl").write_text("\n".join(json.dumps({k: v for k, v in r.items() if k != "_bundle"}) for r in rows) + "\n", encoding="utf-8")
    out_file = tmp_path / "report.json"
    assert run_report.main([str(run_dir), "--json", str(out_file)]) == 0
    report = json.loads(out_file.read_text(encoding="utf-8"))
    assert report["schema_id"] == "rh2.run_report.v1" and report["multi_run"] is False and report["runs_seen"] == ["r1"]
    assert report["sources"]["audit_rows"] == 1 and report["sources"]["bringup_rows"] == 1 and report["audit_rows"] == 1
    assert report["coverage"]["throughput_and_resources"] == "collected" and report["coverage"]["reward_and_distribution"] == "partial"
    assert report["facets"]["execution_and_loss"]["costs"]["terminals"]["consumed"]["group_cost_seconds"]["sum"] == 10.0
    # 只给 audit 目录（没有事件文件）：事件面 not_collected，groups/costs 是 None 不是 0
    empty = tmp_path / "audit_only"
    _write_real_audit(empty, "s9")
    assert run_report.main([str(empty)]) == 0
    inputs = run_report.load_run_inputs([empty])
    report2 = run_report.build_run_report(events=inputs["events"], audits=inputs["audits"], bringup=inputs["bringup"])
    ex = report2["facets"]["execution_and_loss"]
    assert ex["groups"] is None and ex["costs"] is None and report2["coverage"]["dis_and_support"] == "not_collected"
