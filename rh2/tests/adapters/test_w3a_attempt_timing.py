"""W3a 计时工具单测：AttemptLifecycleTiming / SegmentStopwatch / 最近秩百分位 / run 级聚合 / CLI；
exporter 的 segment_sink；SWEGradingManager 的 grader 分段暂存（取走即删、FIFO 上限）；
GradingQueue.backpressure_count。"""

from __future__ import annotations

import base64
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "grading"))
from grading_fixtures import GOOD_FAKE_LOG, FakeDocker, make_fixture_spec  # noqa: E402

from repoharness2.adapters.slime import attempt_timing as at  # noqa: E402
from repoharness2.adapters.slime.attempt_timing import (  # noqa: E402
    LIFECYCLE_SEGMENTS,
    AttemptLifecycleTiming,
    SegmentStopwatch,
    aggregate_lifecycle_timings,
    percentile_nearest_rank,
)
from repoharness2.adapters.slime.patch_exporter import PatchExportError, export_frozen_patch  # noqa: E402
from repoharness2.contracts.baseline_manifest import (  # noqa: E402
    BASELINE_MANIFEST_POLICY_V1,
    BaselineWorkspaceManifestV1,
    compute_policy_digest,
)
from repoharness2.grading.manager import (  # noqa: E402
    GRADER_PHASE_SEGMENTS,
    GraderPhaseTiming,
    GradingManagerConfig,
    SWEGradingManager,
)
from repoharness2.grading.manager import _GRADER_PHASE_TIMING_RETENTION  # noqa: E402

BASE = "a" * 40


def test_segments_are_exactly_the_thirteen_from_the_decision_package():
    assert LIFECYCLE_SEGMENTS == (
        "runtime_quiescence", "baseline_census", "post_census", "artifact_capture", "artifact_persist",
        "grading_queue_wait", "grader_start_and_verify", "grader_baseline_rebuild", "delta_apply", "test",
        "parser_and_report", "grader_cleanup", "rollout_container_hold_after_freeze",
    )
    assert set(GRADER_PHASE_SEGMENTS) < set(LIFECYCLE_SEGMENTS)


def test_timing_set_get_roundtrip_and_validation():
    t = AttemptLifecycleTiming()
    assert all(t.get(name) is None for name in LIFECYCLE_SEGMENTS)
    t.set("test", 1.23456789)
    assert t.get("test") == pytest.approx(1.234568, abs=1e-6)
    with pytest.raises(KeyError):
        t.set("not_a_segment", 1.0)
    with pytest.raises(ValueError):
        t.set("test", -0.1)
    with pytest.raises(ValueError):
        t.set("test", float("nan"))
    t.grading_backpressure_triggered = True
    t.grading_queue_depth_at_enqueue = 3
    t.apply_grader_segments({"delta_apply": 0.5, "grader_cleanup": None}, origin="manager")
    d = t.to_dict()
    assert d["schema_id"] == "rh2.attempt_lifecycle_timing.v1"
    assert d["segments_seconds"]["delta_apply"] == 0.5 and d["segments_seconds"]["grader_cleanup"] is None
    back = AttemptLifecycleTiming.from_dict(json.loads(json.dumps(d)))
    assert back.to_dict() == d


def test_stopwatch_accumulates_and_rejects_unbalanced_stop():
    t = AttemptLifecycleTiming()
    sw = SegmentStopwatch(t)
    sw.start("delta_apply")
    first = sw.stop("delta_apply")
    sw.start("delta_apply")
    second = sw.stop("delta_apply")
    assert t.get("delta_apply") == pytest.approx(first + second, abs=1e-3)
    with pytest.raises(KeyError):
        sw.stop("delta_apply")
    with pytest.raises(KeyError):
        sw.start("unknown_segment")


def test_percentile_nearest_rank():
    assert percentile_nearest_rank([], 50) is None
    assert percentile_nearest_rank([5.0], 95) == 5.0
    values = [float(i) for i in range(1, 21)]  # 1..20
    assert percentile_nearest_rank(values, 50) == 10.0
    assert percentile_nearest_rank(values, 95) == 19.0
    assert percentile_nearest_rank(values, 100) == 20.0
    assert percentile_nearest_rank(values, 0) == 1.0
    with pytest.raises(ValueError):
        percentile_nearest_rank(values, 101)


def test_aggregate_counts_only_present_segments_and_backpressure():
    def rec(**segs):
        return {"segments_seconds": segs, "grading_backpressure_triggered": segs.pop("bp", False),
                "grading_queue_depth_at_enqueue": segs.pop("depth", None), "grader_segment_source": "manager"}

    records = [rec(test=1.0, depth=0), rec(test=3.0, bp=True, depth=2), rec(post_census=0.2)]
    agg = aggregate_lifecycle_timings(records)
    assert agg["attempts"] == 3 and agg["attempts_with_backpressure"] == 1
    assert agg["segments"]["test"] == {"count": 2, "p50": 1.0, "p95": 3.0, "max": 3.0, "mean": 2.0}
    assert agg["segments"]["post_census"]["count"] == 1
    assert agg["segments"]["delta_apply"] == {"count": 0, "p50": None, "p95": None, "max": None, "mean": None}
    assert agg["queue_depth_at_enqueue_p95"] == 2.0
    assert agg["grader_segment_source_counts"] == {"manager": 3}


def test_cli_main_reads_audit_jsonl_and_sidecar(tmp_path, capsys):
    timing = AttemptLifecycleTiming()
    timing.set("test", 2.0)
    audit_line = {"schema_id": "rh2.fa.execution_audit.v1", "timing_summary": {"lifecycle_timing": timing.to_dict()}}
    jsonl = tmp_path / "audit.jsonl"
    jsonl.write_text(json.dumps(audit_line) + "\n" + json.dumps({"timing_summary": {}}) + "\n")
    sidecar = tmp_path / "attempt_lifecycle_timing.json"
    sidecar.write_text(json.dumps(timing.to_dict()))
    assert at.main([str(jsonl), str(sidecar)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["attempts"] == 2 and out["segments"]["test"]["count"] == 2
    assert at.main([]) == 2


# ---------------------------------------------------------------------------
# exporter segment_sink
# ---------------------------------------------------------------------------


def _baseline() -> BaselineWorkspaceManifestV1:
    return BaselineWorkspaceManifestV1(
        task_id="t", workdir="/testbed", public_bundle_digest="sha256:" + "e" * 64,
        runtime_image_digest="sha256:" + "1" * 64, materialized_head=BASE, task_base_commit=BASE,
        policy=BASELINE_MANIFEST_POLICY_V1, policy_digest=compute_policy_digest(BASELINE_MANIFEST_POLICY_V1),
        entries=(),
    )


class _Ws:
    def __init__(self, census: str, contents: str = "", *, census_exit: int = 0):
        self.census, self.contents, self.census_exit = census, contents, census_exit

    async def run_bash(self, script):
        if "find ." in script:
            return SimpleNamespace(exit_code=self.census_exit, stdout=self.census, stderr="boom")
        return SimpleNamespace(exit_code=0, stdout=self.contents, stderr="")


async def test_exporter_records_post_census_and_artifact_capture():
    content = b"x\n"
    sha = hashlib.sha256(content).hexdigest()
    b64 = base64.b64encode(content).decode()
    sink: dict[str, float] = {}
    art = await export_frozen_patch(
        _Ws(f"regular\t100644\t{sha}\tsrc/a.py\n", f"src/a.py\t{b64}\n"), _baseline(),
        rollout_execution_id="exec_1", physical_attempt_id="exec_1#p1-aaaa", segment_sink=sink,
    )
    assert [e.path for e in art.entries] == ["src/a.py"]
    assert set(sink) == {"post_census", "artifact_capture"} and all(v >= 0 for v in sink.values())


async def test_exporter_records_post_census_even_when_census_fails():
    sink: dict[str, float] = {}
    with pytest.raises(PatchExportError, match="post_census_failed"):
        await export_frozen_patch(
            _Ws("", census_exit=1), _baseline(), rollout_execution_id="exec_1",
            physical_attempt_id="exec_1#p1-aaaa", segment_sink=sink,
        )
    assert set(sink) == {"post_census"}


async def test_exporter_without_sink_unchanged():
    art = await export_frozen_patch(_Ws(""), _baseline(), rollout_execution_id="exec_1", physical_attempt_id="p")
    assert art.entries == ()


# ---------------------------------------------------------------------------
# manager 分段暂存
# ---------------------------------------------------------------------------


async def test_manager_phase_timing_taken_once_and_bounded():
    fake = FakeDocker(base_commit=BASE, eval_log=GOOD_FAKE_LOG)
    manager = SWEGradingManager(GradingManagerConfig(), docker=fake)
    spec = make_fixture_spec(BASE, "fake-image:v1", checkout_mode="image_embedded")
    from grading_fixtures import GOOD_PATCH, FakeWorkspace

    report = await manager.grade(trajectory_id="traj_t", workspace=FakeWorkspace(GOOD_PATCH), spec=spec)
    phase = manager.take_grader_phase_timing(report.timings.record_id)
    assert isinstance(phase, GraderPhaseTiming) and phase.frozen_delta_path is False
    assert phase.trajectory_id == "traj_t"
    for name in ("grader_start_and_verify", "delta_apply", "test", "parser_and_report", "grader_cleanup"):
        assert phase.segments[name] is not None and phase.segments[name] >= 0.0
    assert phase.segments["grader_baseline_rebuild"] is None  # S1 路径无 baseline 重建
    assert phase.segments["test"] == pytest.approx(report.timings.test_seconds, abs=1e-3)
    assert manager.take_grader_phase_timing(report.timings.record_id) is None  # 取走即删
    assert phase.to_dict()["record_id"] == report.timings.record_id
    # FIFO 上限：无人取走时最旧记录被淘汰
    for i in range(_GRADER_PHASE_TIMING_RETENTION + 3):
        manager._retain_phase_timing(GraderPhaseTiming(record_id=f"r{i}", trajectory_id="t", task_id="k"))
    assert len(manager._phase_timings) == _GRADER_PHASE_TIMING_RETENTION
    assert manager.take_grader_phase_timing("r0") is None and manager.take_grader_phase_timing("r3") is not None


def test_grader_phase_timing_add_rejects_unknown_and_accumulates():
    phase = GraderPhaseTiming(record_id="r", trajectory_id="t", task_id="k")
    phase.add("test", 0.25)
    phase.add("test", 0.25)
    assert phase.segments["test"] == 0.5
    with pytest.raises(KeyError):
        phase.add("nope", 1.0)
