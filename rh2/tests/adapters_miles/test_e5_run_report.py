"""E5（第六组 I24；Codex 复核 §4）：run_report 的 logprob 三态、合格组 / 有效评分每小时速率、learner 时间线。

oracle：
- 三态来自**有效配置 + 真实 producer**：启动证据（run_manifest.json 的 forward_profile，launch 从最终参数推导）证明额外
  forward 关闭且没有 logprob_compare → unavailable_by_configuration；诊断档或配置未知 / 无效 / 冲突而没有事件 → missing（原
  reason 不变）；关闭却有事件 → contradicts_configuration。按配置不可用时该面仍是 partial（不借 unavailable 升 collected）。
- 速率只用已有计数与事件时间窗；有效评分 = resolved + 可信 0 分（binary_v1 契约），reward 未知与评测 session 不计；缺计数 /
  缺窗口 / 缺卡数时速率是 None 不是 0。
- learner 时间线只由事件时间戳与 duration 字段相减；不推算重算 token 数或 cache 命中。
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace as NS
from typing import get_args

import pytest

FAITHFUL = "repoharness2.adapters.miles.faithful_dis_loss.faithful_dis_loss_function"
RECIPE = ["--loss-type", "custom_loss", "--custom-loss-function-path", FAITHFUL, "--kl-coef", "0.0", "--use-rollout-routing-replay"]


def _ev(kind: str, run: str = "r1", bundle: int = 0, ts: float = 1.0, **fields) -> dict:
    return {"event": kind, "ts_unix": ts, "host": "h", "pid": 1, "run_id": run, "_bundle": bundle, **fields}


def _manifest(profile: str | None, *, run: str = "r1", bundle: int = 0, block: dict | None = None, topology=None) -> dict:
    from repoharness2.adapters.miles.forward_profile import derive_from_tokens

    if block is None and profile is not None:
        block = derive_from_tokens(RECIPE + (["--use-rollout-logprobs"] if profile == "efficiency" else []))
    return {"_bundle": bundle, "_source_file": f"run_manifest_{run}_{bundle}.json", "run_id": run, "forward_profile": block,
            "topology": topology if topology is not None else {"actor_gpus": 6, "rollout_gpus": 2}}


COMPARE_ENTRY = {"sample_index": 10, "leaf_ordinal": 0, "same_version": True, "num_tokens": 5, "total_tokens": 5,
                 "mean_abs_diff": 0.01, "length_mismatch": False}


def _base_events(*, with_compare: bool) -> list[dict]:
    rows = [_ev("group_consumed", rh2_prompt_group_id="g0", sample_indices=[10], task_id="A", staleness=0),
            _ev("rollout_group", rollout_id=0, group_index=0, instance_id="A", sample_indices=[10], leaf_ordinals=[0],
                rewards=[1.0], behavior_versions=[["5"]], weight_version_spans=[None], statuses=["completed"],
                response_lengths=[1], routing_tape=[None])]
    if with_compare:
        rows.append(_ev("logprob_compare", rollout_id=0, dp_rank=0, trainer_current_version=5, entries=[COMPARE_ENTRY]))
    return rows


def _report(events, manifests):
    from repoharness2.adapters.miles.run_report import build_run_report

    return build_run_report(events=events, audits=[], manifests=manifests)


@pytest.mark.parametrize(
    ("profile", "with_compare", "state", "reason_prefix", "status"),
    [
        ("diagnostic", True, "present", None, "collected"),
        ("diagnostic", False, "missing", "no_logprob_compare_events", "partial"),
        ("efficiency", False, "unavailable_by_configuration", "logprob_compare_unavailable_by_configuration", "partial"),
        ("efficiency", True, "contradicts_configuration", "logprob_compare_contradicts_configuration", "collected"),
        (None, False, "missing", "no_logprob_compare_events", "partial"),  # 没有启动证据：配置未知 = 缺证据
        (None, True, "present", None, "collected"),
    ],
)
def test_logprob_state_comes_from_effective_configuration_plus_real_producer(profile, with_compare, state, reason_prefix, status):
    manifests = [_manifest(profile)] if profile else []
    report = _report(_base_events(with_compare=with_compare), manifests)
    facet = report["facets"]["staleness_and_alignment"]
    assert facet["logprob_compare_state"] == state and facet["status"] == status
    assert report["forward_profile"]["observed_producers"] == {"logprob_compare": state}
    tri = [r for r in facet["reasons"] if r.split(":")[0] in (
        "no_logprob_compare_events", "logprob_compare_unavailable_by_configuration", "logprob_compare_contradicts_configuration")]
    assert tri == ([] if reason_prefix is None else [r for r in tri if r.startswith(reason_prefix)]) and len(tri) == (reason_prefix is not None)
    fwd = report["forward_profile"]
    if profile is None:
        assert fwd["status"] == "unknown" and fwd["reason"].startswith("no_run_manifest")
    else:
        assert fwd["status"] == "known" and fwd["profile"] == profile
        assert fwd["extra_logprob_forward"] is (profile == "diagnostic")
    if profile == "efficiency":
        assert "rh2_event:logprob_compare" in fwd["unavailable_observations"] and "G1 parity" in fwd["note"]


def test_unknown_invalid_or_conflicting_configuration_never_yields_unavailable():
    """只有 known 且证明关闭才算按配置不可用：旧启动证据（无块）、被改写的块、同一 run 两份结论不同都当配置未知。"""
    from repoharness2.adapters.miles.forward_profile import derive_from_tokens

    eff = derive_from_tokens(RECIPE + ["--use-rollout-logprobs"])
    tampered = dict(eff, profile="diagnostic", extra_logprob_forward=True, unavailable_observations=[])
    cases = {
        "unknown": [_manifest(None)],  # run_manifest.json 在但没有 forward_profile（E5 之前的启动器）
        "invalid": [_manifest(None, block=tampered)],
        "conflict": [_manifest("efficiency"), _manifest("diagnostic", bundle=1)],
    }
    for status, manifests in cases.items():
        report = _report(_base_events(with_compare=False), manifests)
        assert report["forward_profile"]["status"] == status, status
        assert report["facets"]["staleness_and_alignment"]["logprob_compare_state"] == "missing", status
    invalid = _report(_base_events(with_compare=False), cases["invalid"])["forward_profile"]
    assert "recorded_block_inconsistent" in invalid["errors"][0]


def test_manifests_attach_by_their_own_run_id_and_runs_are_not_mixed():
    from repoharness2.adapters.miles.run_report import build_run_report

    events = _base_events(with_compare=False) + [dict(r, run_id="r2", _bundle=1) for r in _base_events(with_compare=True)]
    manifests = [_manifest("efficiency", run="r1"), _manifest("diagnostic", run="r2", bundle=1),
                 _manifest("diagnostic", run="ghost", bundle=1)]  # 不属于任何事件 run 的启动证据只计数
    report = _report(events, manifests)
    assert report["multi_run"] is True and report["unattributed_manifest_rows"] == 1
    per = report["per_run"]
    assert per["r1"]["facets"]["staleness_and_alignment"]["logprob_compare_state"] == "unavailable_by_configuration"
    assert per["r2"]["facets"]["staleness_and_alignment"]["logprob_compare_state"] == "present"
    scoped = build_run_report(events=events, audits=[], manifests=manifests, run_id="r1")
    assert scoped["forward_profile"]["profile"] == "efficiency"


def test_cli_discovers_run_manifest_in_the_evidence_layout(tmp_path):
    """launch 的证据布局：evidence/run_manifest.json + evidence/events/rh2_events_*.jsonl。"""
    from repoharness2.adapters.miles import run_report
    from repoharness2.adapters.miles.forward_profile import derive_from_tokens

    ev = tmp_path / "run" / "evidence"
    (ev / "events").mkdir(parents=True)
    rows = [{k: v for k, v in r.items() if k != "_bundle"} for r in _base_events(with_compare=False)]
    (ev / "events" / "rh2_events_h_1.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    (ev / "run_manifest.json").write_text(json.dumps({
        "run_id": "r1", "topology": {"actor_gpus": 6, "rollout_gpus": 2},
        "forward_profile": derive_from_tokens(RECIPE + ["--use-rollout-logprobs"])}), encoding="utf-8")
    (tmp_path / "broken").mkdir()
    (tmp_path / "broken" / "run_manifest.json").write_text("{not json", encoding="utf-8")
    inputs = run_report.load_run_inputs([tmp_path / "run", tmp_path / "broken"])
    assert inputs["sources"]["manifest_rows"] == 1 and inputs["sources"]["malformed_manifest_files"] == 1
    out = tmp_path / "report.json"
    assert run_report.main([str(tmp_path / "run"), "--json", str(out)]) == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["forward_profile"]["status"] == "known" and report["forward_profile"]["profile"] == "efficiency"
    assert report["facets"]["staleness_and_alignment"]["logprob_compare_state"] == "unavailable_by_configuration"
    assert report["facets"]["throughput_and_resources"]["hourly_rates"]["gpu_count"] == 8


def _real_bringup_rows(directory: Path, specs: list[tuple[str, str | None, str | None, float | None]]) -> list[dict]:
    """真实 writer（BringupService.record_event）写评分块：(session, outcome, failure_category, reward)；outcome=None = 无评分。"""
    from repoharness2.adapters.miles.run_report import load_run_inputs
    from repoharness2.adapters.slime.bringup import BringupService
    from repoharness2.adapters.slime.generate import RolloutAudit

    directory.mkdir(parents=True, exist_ok=True)
    for sid, outcome, category, reward in specs:
        audit = RolloutAudit(trajectory_id=sid, task_id="task-A")
        grading = None if outcome is None else NS(outcome=outcome, failure_category=category, reward=reward, timings=None)
        audit.finalized = NS(grading_report=grading, eligibility_report=NS(report_id=f"rep-{sid}", eligibility_class="valid_for_training"),
                             group_repair_signal=NS(degraded=False))
        service = NS(orchestrator=NS(audits=[audit]), registry=NS(weight_versions={}, stats={}), events_path=directory / "bringup_events.jsonl")
        BringupService.record_event(service, args=None, sample=NS(session_id=sid, index=1, group_index=0, metadata={"instance_id": "task-A"}),
                                    result=[], wall_seconds=1.0)
    return load_run_inputs([directory])["bringup"]


def test_hourly_rates_count_qualified_groups_and_effective_gradings_including_trusted_zero(tmp_path):
    from repoharness2.adapters.miles.run_report import build_run_report

    bringup = _real_bringup_rows(tmp_path / "b", [
        ("s1", "resolved", None, 1.0), ("s2", "resolved", None, 1.0), ("s3", "resolved", None, 1.0),
        ("s4", "unresolved", "tests_failed", 0.0), ("s5", "unresolved", "patch_apply_failed", 0.0),
        ("s6", "failed_to_grade", "infra_failure", None),  # infra 族：reward 未知，不是 0 分
        ("s7", "unresolved", "infra_failure", 0.0),  # 违反 binary_v1 的组合：单列 inconsistent，不计有效评分
        ("s8", None, None, None),  # 交付了但没有评分块
        ("e1", "resolved", None, 1.0),  # 评测 session：不进训练速率
    ])
    events = [_ev("drain_complete", ts=1000.0, rollout_id=0, elapsed_seconds=5.0, target_groups=1)]
    events += [_ev("group_consumed", ts=2000.0 + i, rh2_prompt_group_id=f"g{i}", sample_indices=[i], task_id="A", staleness=0) for i in range(6)]
    events += [_ev("group_filtered", ts=2100.0, drop_stage="dynamic_filter", reason_code="zero_std", rh2_prompt_group_id="gz",
                   sample_indices=[99], task_id="A")]
    for step in range(4):
        for rank, pp_last in ((0, False), (1, True)):  # 多 rank 副本只取一份
            events.append(_ev("train_step", ts=3000.0 + step, rollout_id=step // 2, step_id=step % 2, attempt=0, outcome="NORMAL",
                              optimizer_step_applied=step != 3, rank=rank, dp_rank=0, is_pp_last_stage=pp_last, num_rollouts=8,
                              metrics={"dis_accepted_tokens": 1.0} if pp_last else None, duration_seconds=1.0))
    events.append(_ev("weight_publish", ts=1000.0 + 7200.0, rollout_id=1))  # 窗口恰好 2 小时
    audits = [{"trajectory_id": "e1", "task_id": "task-A", "evaluation": {"eval": {"eval_point_id": "p0"}}, "_bundle": 0}]
    bringup = [dict(r, _bundle=0) for r in bringup] + [{"ts": 1.0, "event": "shutdown_report", "_bundle": 0}]  # 生命周期行
    report = build_run_report(events=events, audits=audits, bringup=bringup, manifests=[_manifest("efficiency")])
    rates = report["facets"]["throughput_and_resources"]["hourly_rates"]
    assert rates["window"]["hours"] == 2.0 and rates["gpu_count"] == 8
    assert rates["qualified_groups"]["count"] == 6 and rates["qualified_groups"]["per_hour"] == 3.0
    assert rates["qualified_groups"]["per_gpu_hour"] == 0.375
    assert rates["applied_optimizer_steps"]["count"] == 3 and rates["applied_optimizer_steps"]["per_hour"] == 1.5
    eff = rates["effective_gradings"]
    assert (eff["resolved"]["count"], eff["trusted_zero"]["count"], eff["total"]["count"]) == (3, 2, 5)
    assert eff["total"]["per_hour"] == 2.5 and eff["trusted_zero"]["per_gpu_hour"] == 0.125
    assert rates["gradings_not_effective"] == {"reward_unknown": 1, "inconsistent": 1, "executions_without_grading_block": 1,
                                               "evaluation_attempts_excluded": 1, "duplicate_execution_records_collapsed": 0,
                                               "rows_without_session_id": 1}
    assert rates["effective_gradings"]["source"].startswith("旧 bringup_events")  # E5 之前的证据形态：回退路径


def test_rates_are_unavailable_not_zero_without_window_counts_or_topology():
    from repoharness2.adapters.miles.run_report import build_run_report

    single = build_run_report(events=[_ev("drain_complete", rollout_id=0, elapsed_seconds=1.0)], audits=[])
    rates = single["facets"]["throughput_and_resources"]["hourly_rates"]
    assert rates["window"] is None and rates["qualified_groups"] == {"count": None, "per_hour": None, "per_gpu_hour": None,
                                                                     "source": rates["qualified_groups"]["source"]}
    assert rates["effective_gradings"] is None and rates["applied_optimizer_steps"]["count"] is None
    assert any(r.startswith("no_event_window") for r in rates["reasons"]) and any(r.startswith("no_topology") for r in rates["reasons"])
    two = build_run_report(events=[_ev("group_consumed", ts=0.0, rh2_prompt_group_id="g", sample_indices=[1], task_id="A"),
                                   _ev("group_consumed", ts=1800.0, rh2_prompt_group_id="h", sample_indices=[2], task_id="A")],
                           audits=[], manifests=[_manifest("diagnostic", topology={"actor_gpus": 6})])
    q = two["facets"]["throughput_and_resources"]["hourly_rates"]["qualified_groups"]
    assert q["per_hour"] == 4.0 and q["per_gpu_hour"] is None  # 卡数不全：每 GPU 小时不可用


def test_trusted_zero_categories_match_the_grading_contract():
    from repoharness2.adapters.miles.run_report import TRUSTED_ZERO_FAILURE_CATEGORIES
    from repoharness2.contracts.grading import INFRA_FAILURE_CATEGORIES, GradingFailureCategory

    assert set(TRUSTED_ZERO_FAILURE_CATEGORIES) == set(get_args(GradingFailureCategory)) - set(INFRA_FAILURE_CATEGORIES)


def _timeline_events(*, diagnostic: bool) -> list[dict]:
    rows = [_ev("weight_update", ts=90.0, rollout_id=None, version_before=0, version_after=1, duration_seconds=30.0)]  # bootstrap
    for rid, base in ((0, 100.0), (1, 200.0)):
        rows.append(_ev("drain_complete", ts=base, rollout_id=rid, elapsed_seconds=20.0, target_groups=8))
        rows.append(_ev("train_rollout", ts=base + 2.0, rollout_id=rid, trainer_current_version=rid + 1))
        for rank in (0, 1):
            rows.append(_ev("replay_fill", ts=base + 3.0 + rank * 0.5, rollout_id=rid, rank=rank, dp_rank=rank, manager="routing"))
        if diagnostic:
            rows.append(_ev("logprob_compare", ts=base + 10.0, rollout_id=rid, dp_rank=0, trainer_current_version=rid + 1,
                            entries=[COMPARE_ENTRY]))
        first_step_end = base + (18.0 if diagnostic else 12.0)
        for step in (0, 1):
            for rank, skew in ((0, 0.0), (1, 0.4)):
                rows.append(_ev("train_step", ts=first_step_end + step * 6.0 + skew, rollout_id=rid, step_id=step, attempt=0,
                                outcome="NORMAL", optimizer_step_applied=True, rank=rank, dp_rank=rank, is_pp_last_stage=True,
                                num_rollouts=32, metrics={}, duration_seconds=6.0 - skew))
        last_end = first_step_end + 6.0 + 0.4
        rows.append(_ev("weight_update", ts=last_end + 9.0, rollout_id=rid, version_before=rid + 1, version_after=rid + 2,
                        duration_seconds=5.0))
        rows.append(_ev("weight_publish", ts=last_end + 9.5, rollout_id=rid))
    return rows


def test_learner_timeline_is_rebuilt_from_event_timestamps_only():
    from repoharness2.adapters.miles.run_report import build_run_report

    diag = build_run_report(events=_timeline_events(diagnostic=True), audits=[], manifests=[_manifest("diagnostic")])
    tl = diag["facets"]["optimizer_and_publish"]["learner_timeline"]
    assert tl["rollouts_total"] == 2 and tl["negative_intervals"] == 0 and tl["hosts"] == ["h"]
    first = tl["rollouts"][0]
    assert first["logprob_compare"] == {"state": "present", "end_ts": 110.0}
    assert [s["step_id"] for s in first["steps"]] == [0, 1]
    assert first["steps"][0] == {"step_id": 0, "end_ts": 118.4, "start_ts": 112.0, "duration_seconds": 6.0}  # 多 rank 取包络
    iv = first["intervals_seconds"]
    assert iv == {
        "drain_wait": 20.0,
        "drain_end_to_train_start": 2.0,
        "train_start_to_replay_fill": 1.5,
        "train_start_to_logprob_compare": 8.0,
        "logprob_compare_to_first_step_start": 2.0,
        "train_start_to_first_step_start": 10.0,
        "optimizer_steps_span": 12.4,
        "last_step_end_to_update_start": 4.0,
        "weight_update": 5.0,
        "update_end_to_publish": 0.5,
        "publish_to_next_train_start": round(202.0 - 133.9, 3),
    }
    assert tl["rollouts"][1]["intervals_seconds"]["publish_to_next_train_start"] is None  # 最后一轮没有下一轮：未知不填 0
    assert tl["intervals_seconds_summary"]["train_start_to_first_step_start"]["count"] == 2
    assert tl["bootstrap_updates"] == [{"ts": 90.0, "duration_seconds": 30.0}]
    assert set(tl["not_derivable"]) == {"recompute_tokens_after_publish", "prefix_cache_hit", "per_phase_gpu_memory"}
    assert all(v.startswith("not_collected") for v in tl["not_derivable"].values())

    eff = build_run_report(events=_timeline_events(diagnostic=False), audits=[], manifests=[_manifest("efficiency")])
    etl = eff["facets"]["optimizer_and_publish"]["learner_timeline"]
    e0 = etl["rollouts"][0]
    assert e0["logprob_compare"] == {"state": "unavailable_by_configuration", "end_ts": None}
    assert e0["intervals_seconds"]["train_start_to_logprob_compare"] is None
    assert e0["intervals_seconds"]["train_start_to_first_step_start"] == 4.0  # 同一锚点口径，两档可直接对比
    unknown = build_run_report(events=_timeline_events(diagnostic=False), audits=[])  # 没有启动证据：缺对拍 = 缺证据
    assert unknown["facets"]["optimizer_and_publish"]["learner_timeline"]["rollouts"][0]["logprob_compare"]["state"] == "missing"
    clash = build_run_report(events=_timeline_events(diagnostic=True), audits=[], manifests=[_manifest("efficiency")])
    assert clash["facets"]["optimizer_and_publish"]["learner_timeline"]["rollouts"][0]["logprob_compare"]["state"] == "contradicts_configuration"


def test_negative_intervals_are_counted_not_rewritten():
    from repoharness2.adapters.miles.run_report import build_run_report

    rows = [_ev("drain_complete", ts=100.0, rollout_id=0, elapsed_seconds=1.0),
            _ev("train_rollout", ts=99.0, rollout_id=0, trainer_current_version=1)]  # 跨进程时钟偏差的形态
    tl = build_run_report(events=rows, audits=[])["facets"]["optimizer_and_publish"]["learner_timeline"]
    assert tl["rollouts"][0]["intervals_seconds"]["drain_end_to_train_start"] == -1.0 and tl["negative_intervals"] == 1


# ---- Codex EF1：评分摘要走每次 execution 的审计出口；缺记录保持未知 ---------------------------------------------------------


def _audit_row(key: str, outcome, category, reward, *, evaluation=None, ts: float = 10.0, task="task-A") -> dict:
    """与 write_execution_audit_record 同形的最小行（只含报告读的键）。outcome=None = 审计了但没有评分块（例如 aborted）。"""
    grading = None if outcome is None else {"report_id": f"rpt_{key}", "outcome": outcome, "failure_category": category,
                                            "reward": reward, "timings": None}
    return {"schema_id": "rh2.fa.execution_audit.v1", "trajectory_id": f"traj-{key}", "physical_attempt_id": key, "task_id": task,
            "wall_end_epoch": ts, "evaluation": evaluation, "grading": grading, "_bundle": 0}


def _window_events() -> list[dict]:
    return [_ev("drain_complete", ts=1000.0, rollout_id=0, elapsed_seconds=5.0, target_groups=1),
            _ev("weight_publish", ts=1000.0 + 3600.0, rollout_id=1)]  # 窗口 1 小时


async def test_effective_gradings_travel_through_the_execution_audit_exit(tmp_path):
    """真实 RolloutOrchestrator + write_execution_audit_record（假 Docker / driver / 模型；评分替身给 resolved 与 infra 两种真实
    契约形态）→ load_run_inputs → build_run_report：不经过旧 bringup.record_event（正式 miles 路径就是这样）。"""
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "adapters"))  # 与同目录其它测试同法取 dense 链夹具
    from test_slime_generate import SAMPLING_PARAMS, _Args, build_dense_chain

    from repoharness2.adapters.miles.run_report import build_run_report, load_run_inputs
    from repoharness2.adapters.slime.bringup import write_execution_audit_record

    audit_path = tmp_path / "fa_execution_audit.jsonl"
    for infra in (False, True):
        chain = build_dense_chain(infra_grading=infra, audit_sink=lambda audit: write_execution_audit_record(None, audit, audit_path))
        await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    inputs = load_run_inputs([tmp_path])
    assert len(inputs["audits"]) == 2 and inputs["bringup"] == []  # 没有 bringup_events.jsonl
    gradings = [a["grading"] for a in inputs["audits"]]
    assert {g["outcome"] for g in gradings} == {"resolved", "failed_to_grade"} and all("report_id" in g for g in gradings)
    report = build_run_report(events=_window_events(), audits=inputs["audits"], bringup=[], manifests=[_manifest("diagnostic")])
    eff = report["facets"]["throughput_and_resources"]["hourly_rates"]["effective_gradings"]
    assert (eff["resolved"]["count"], eff["trusted_zero"]["count"], eff["total"]["count"]) == (1, 0, 1)
    assert eff["total"]["per_hour"] == 1.0 and eff["source"].startswith("execution audit")
    assert report["facets"]["throughput_and_resources"]["hourly_rates"]["gradings_not_effective"]["reward_unknown"] == 1  # infra ≠ 0 分
    graded = report["facets"]["reward_and_distribution"]["graded_attempts"]
    assert graded["source"] == "execution_audit" and graded["graded"] == 2 and graded["outcomes"] == {"failed_to_grade": 1, "resolved": 1}
    assert graded["delivery_records"] is None  # 交付记录来自 bringup_events，此处确实没有——不猜


def test_lifecycle_rows_alone_keep_effective_gradings_unknown_not_zero():
    """Codex EF1 反例：只有 shutdown 两行（无 session_id、无评分块）、没有任何带 grading 块的 audit → 未知，不是 0 / 小时。"""
    from repoharness2.adapters.miles.run_report import build_run_report

    lifecycle = [{"ts": 1.0, "event": "shutdown_started", "_bundle": 0}, {"ts": 2.0, "event": "shutdown_completed", "_bundle": 0}]
    old_audit = {"trajectory_id": "t0", "task_id": "task-A", "_bundle": 0}  # E5 之前的审计行：没有 grading 键
    report = build_run_report(events=_window_events(), audits=[old_audit], bringup=lifecycle, manifests=[_manifest("diagnostic")])
    rates = report["facets"]["throughput_and_resources"]["hourly_rates"]
    assert rates["effective_gradings"] is None and rates["gradings_not_effective"] is None and rates["grading_coverage"] is None
    assert any(r.startswith("no_grading_records") for r in rates["reasons"])
    reward = report["facets"]["reward_and_distribution"]
    assert reward["graded_attempts"] is None and any(r.startswith("no_grading_records") for r in reward["reasons"])
    assert report["facets"]["throughput_and_resources"]["grading_timings"] is None


def test_eval_infra_and_duplicate_execution_records_are_not_counted_as_effective():
    from repoharness2.adapters.miles.run_report import build_run_report

    audits = [
        _audit_row("a1", "resolved", None, 1.0),
        _audit_row("a2", "unresolved", "tests_failed", 0.0),                      # 可信 0 分
        _audit_row("a3", "failed_to_grade", "infra_failure", None),               # infra：reward 未知
        _audit_row("a2", "unresolved", "tests_failed", 0.0, ts=20.0),             # 同一 execution 的重复记录（重评分）：只计一次
        _audit_row("e1", "resolved", None, 1.0, evaluation={"eval": {"eval_point_id": "p0"}}),  # 评测 attempt：单列不计
        _audit_row("a4", None, None, None),                                       # 审计了但没有评分块（aborted）
    ]
    report = build_run_report(events=_window_events(), audits=audits, bringup=[], manifests=[_manifest("diagnostic")])
    rates = report["facets"]["throughput_and_resources"]["hourly_rates"]
    eff = rates["effective_gradings"]
    assert (eff["resolved"]["count"], eff["trusted_zero"]["count"], eff["total"]["count"]) == (1, 1, 2)
    assert rates["gradings_not_effective"] == {"reward_unknown": 1, "inconsistent": 0, "executions_without_grading_block": 1,
                                               "evaluation_attempts_excluded": 1, "duplicate_execution_records_collapsed": 1,
                                               "rows_without_session_id": 0}
    assert rates["grading_coverage"] == {"executions_audited": 4, "with_grading_block": 3, "without_grading_block": 1,
                                         "audit_rows_without_grading_block": 1}
    assert any(r.startswith("partial_grading_coverage: 3/4") for r in rates["reasons"])
    graded = report["facets"]["reward_and_distribution"]["graded_attempts"]
    assert graded["graded"] == 3 and graded["by_task"]["task-A"]["graded"] == 3 and graded["reward"]["unknown"] == 1


def test_audit_grading_blocks_take_precedence_over_legacy_bringup_rows():
    """两种来源同时在场（过渡期）：以 execution audit 为准，不把旧 bringup 块再算一遍。"""
    from repoharness2.adapters.miles.run_report import build_run_report

    audits = [_audit_row("a1", "resolved", None, 1.0)]
    legacy = [{"ts": 1.0, "session_id": "traj-a1", "grading": {"outcome": "resolved", "failure_category": None, "reward": 1.0}, "_bundle": 0},
              {"ts": 1.0, "session_id": "traj-zz", "grading": {"outcome": "resolved", "failure_category": None, "reward": 1.0}, "_bundle": 0}]
    report = build_run_report(events=_window_events(), audits=audits, bringup=legacy, manifests=[_manifest("diagnostic")])
    eff = report["facets"]["throughput_and_resources"]["hourly_rates"]["effective_gradings"]
    assert eff["total"]["count"] == 1 and eff["source"].startswith("execution audit")
    graded = report["facets"]["reward_and_distribution"]["graded_attempts"]
    assert graded["source"] == "execution_audit" and graded["graded"] == 1 and graded["delivery_records"] == 2
