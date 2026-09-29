"""EF1 复核：真实 miles 入口 -> fa_formal 编排 -> writer -> 离线报告。

复用既有 prepared 题包 / Docker / capture / grader 夹具；不运行真实模型或容器。
引擎、资源、评分内容为替身，评分契约、身份、finalize、审计出口、报告为真实代码。
一小时事件窗与评分分段时长为测试输入，不是性能测量。证据只写本轮目录。
运行：RH2_MILES_PATH=<fork> rh2/.venv/bin/python <本文件>
"""
from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
import tempfile
from argparse import Namespace
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "rh2/src/repoharness2").is_dir())
TESTS = ROOT / "rh2/tests"
sys.path[:0] = [str(TESTS / "adapters_miles"), str(TESTS), str(ROOT / "rh2/src")]

spec = importlib.util.spec_from_file_location("ef1_review_world", TESTS / "adapters_miles/conftest.py")
cf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cf)
world_scope = cf._vendor_slime_world.__wrapped__()
next(world_scope)
cf.install_sglang_stub()
world = cf._World()

import test_i21_eval_entry as fx  # noqa: E402
from repoharness2.adapters.miles import generate_fn as gf  # noqa: E402
from repoharness2.adapters.miles.forward_profile import derive_from_tokens  # noqa: E402
from repoharness2.adapters.miles.group_admission import GROUP_ADMISSION_FILTER_PATH  # noqa: E402
from repoharness2.adapters.miles.run_report import build_run_report, load_run_inputs  # noqa: E402
from repoharness2.adapters.slime.bringup import write_execution_audit_record  # noqa: E402
from repoharness2.contracts import GradingTimingRecord  # noqa: E402

# 只替换宿主盖章能力探测：eval 派发字段使用现有夹具，与已审 fork patch 同形。
gf._eval_host_stamp_supported = lambda: True


def events():
    return [
        {"event": "drain_complete", "run_id": "ef1-review", "ts_unix": 1000.0, "rollout_id": 0,
         "elapsed_seconds": 1.0, "target_groups": 1, "_bundle": 0},
        {"event": "weight_publish", "run_id": "ef1-review", "ts_unix": 4600.0, "rollout_id": 1, "_bundle": 0},
    ]


def report(audits, bringup=()):
    return build_run_report(
        events=events(), audits=audits, bringup=list(bringup),
        manifests=[{"run_id": "ef1-review", "forward_profile": derive_from_tokens([]),
                    "topology": {"actor_gpus": 6, "rollout_gpus": 2}}],
    )


def parts(value):
    facets = value["facets"]
    return {"reward": facets["reward_and_distribution"],
            "rates": facets["throughput_and_resources"]["hourly_rates"],
            "timings": facets["throughput_and_resources"]["grading_timings"],
            "evaluation": facets["evaluation"]}


async def exercise(root):
    package = fx.prepare_synthetic(root / "prepared", iids=(fx.IIDS[0],))
    face = fx._load_face(package)
    audit_path = root / "fa_execution_audit.jsonl"
    cases = []
    for kind, evaluation, missing in [
        ("resolved", False, False), ("unresolved", False, False),
        ("failed_to_grade", False, False), ("resolved", False, True),
        ("resolved", True, False),
    ]:
        registry, face_for = fx._registry(face, face)
        chain = fx._chain(world, registry=registry, face_for=face_for, grading_kind=kind,
                          docker=fx._NoDocker() if missing else None)
        chain.orchestrator._audit_sink = lambda audit: write_execution_audit_record(None, audit, audit_path)
        original_submit = chain.orchestrator._grading_submit

        async def submit_with_timings(_submit=original_submit, **kw):
            grading = await _submit(**kw)
            timing = GradingTimingRecord(
                record_id=f"tm-{grading.report_id}", trajectory_id=grading.trajectory_id,
                task_id=grading.task_id, image_pull_seconds=1, env_reset_seconds=2,
                prep_seconds=3, test_seconds=4, total_grading_seconds=10,
                queue_wait_seconds=0.5, container_peak_memory_mb=128,
            )
            return grading.model_copy(update={"timings": timing})

        chain.orchestrator._grading_submit = submit_with_timings
        sample = fx._eval_samples(package)[0] if evaluation else fx._dispatch_groups(package, n=1)[0][0]
        args = Namespace(rh2_orchestrator=chain.orchestrator, rh2_attempt_assignments=registry,
                         n_samples_per_prompt=1, dynamic_sampling_filter_path=GROUP_ADMISSION_FILTER_PATH)
        result = await world.Rh2MilesGenerateFn()(fx._gi(args, sample, evaluation=evaluation))
        audit = chain.orchestrator.audits[0]
        cases.append({"kind": kind, "evaluation": evaluation, "materialize_failed": missing,
                      "outputs": len(result.samples), "grading_calls": len(chain.grading_calls),
                      "trajectory_id": audit.trajectory_id, "physical_attempt_id": audit.physical_attempt_id})
        assert len(registry) == 0

    inputs = load_run_inputs([root])
    rows = inputs["audits"]
    assert len(rows) == 5 and inputs["bringup"] == []
    assert len({a["physical_attempt_id"] for a in rows}) == 5
    assert [a["grading"]["reward"] if a["grading"] else None for a in rows] == [1, 0, None, None, 1]
    assert len({a["trajectory_id"] for a in rows[:4]}) == 1  # 同逻辑成员重试，不同 physical attempt 各计一次
    base = parts(report(rows))
    rates = base["rates"]
    assert rates["effective_gradings"]["total"] == {"count": 2, "per_hour": 2.0, "per_gpu_hour": 0.25}
    assert rates["effective_gradings"]["resolved"]["count"] == 1
    assert rates["effective_gradings"]["trusted_zero"]["count"] == 1
    assert rates["gradings_not_effective"]["reward_unknown"] == 1
    assert rates["gradings_not_effective"]["evaluation_attempts_excluded"] == 1
    assert rates["grading_coverage"]["with_grading_block"] == 3
    assert rates["grading_coverage"]["executions_audited"] == 4
    assert any(r.startswith("partial_grading_coverage: 3/4") for r in rates["reasons"])
    assert base["reward"]["graded_attempts"]["graded"] == 3
    assert base["timings"]["test_seconds"]["count"] == 3
    assert base["timings"]["test_seconds"]["sum"] == 12

    repeated = parts(report(rows + [rows[0]]))
    assert repeated["rates"]["effective_gradings"] == rates["effective_gradings"]
    assert repeated["timings"] == base["timings"]
    assert repeated["rates"]["gradings_not_effective"]["duplicate_execution_records_collapsed"] == 1

    lifecycle = [{"event": "shutdown_started", "_bundle": 0}, {"event": "shutdown_completed", "_bundle": 0}]
    life_only = parts(report([], lifecycle))
    assert life_only["rates"]["effective_gradings"] is None
    assert life_only["reward"]["graded_attempts"] is None
    assert life_only["timings"] is None
    assert any(r.startswith("no_grading_records") for r in life_only["rates"]["reasons"])
    with_lifecycle = parts(report(rows, lifecycle))
    assert with_lifecycle["rates"]["effective_gradings"] == rates["effective_gradings"]

    legacy_rows = [{"session_id": row["trajectory_id"], "grading": row["grading"], "_bundle": 0}
                   for row in rows[:1]]
    legacy = parts(report([], legacy_rows))
    assert legacy["rates"]["effective_gradings"]["total"]["count"] == 1
    assert legacy["reward"]["graded_attempts"]["source"] == "bringup_events_legacy"
    precedence = parts(report(rows, legacy_rows))
    assert precedence["rates"]["effective_gradings"] == rates["effective_gradings"]

    # 记录新旧两种 writer 记录混放的可兼容边界；这是离线人为组合，不冒充当前运行实测。
    old_row = dict(rows[3])
    old_row.pop("grading")
    mixed = parts(report([rows[0], old_row]))
    return {
        "scope": __doc__, "all_required_checks_pass": True, "cases": cases,
        "base": base, "duplicate": repeated["rates"], "lifecycle_only": life_only,
        "with_lifecycle_delivery_fields": with_lifecycle["reward"]["graded_attempts"],
        "legacy": legacy["rates"], "mixed_writer_fixture_only": mixed["rates"],
    }


try:
    with tempfile.TemporaryDirectory(prefix="rh2-ef1-review-") as temp:
        result = asyncio.run(exercise(Path(temp)))
    (HERE / "probe_audit_grading.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"all_required_checks_pass": result["all_required_checks_pass"],
                      "formal_attempts": len(result["cases"]), "rates": result["base"]["rates"]}, ensure_ascii=False))
finally:
    next(world_scope, None)
