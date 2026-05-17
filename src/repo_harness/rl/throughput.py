"""Stage 12.5 synchronous throughput baseline evidence helpers."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, model_validator

from repo_harness.schema_base import StrictBaseModel

from .visibility import validate_no_absolute_local_path

STAGE12_5_LOCAL_REQUIRED_FILES = (
    "environment_cache_report.json",
    "workspace_cache_report.json",
    "verifier_recorder_tool_hot_path_report.json",
    "dataproto_padding_profile.json",
    "visibility_and_batch_validation_report.json",
    "stage12_5_local_acceptance_summary.json",
)

STAGE12_5_REMOTE_REQUIRED_FILES = (
    "environment_cache_report.json",
    "workspace_cache_report.json",
    "concurrent_episode_report.json",
    "trainer_throughput_profile.json",
    "verifier_recorder_tool_hot_path_report.json",
    "batch_refill_resample_report.json",
    "dataproto_padding_profile.json",
    "inference_metric_source_inventory.json",
    "inference_server_profile.json",
    "tokenization_profile.json",
    "ray_worker_resource_profile.json",
    "system_resource_profile.json",
    "visibility_and_batch_validation_report.json",
    "stage12_5_acceptance_summary.json",
)

EvidenceScope = Literal["local", "remote"]


class Stage125EvidenceBundleCheck(StrictBaseModel):
    schema_version: str = "repo_harness_stage12_5_evidence_bundle_check_v0"
    scope: EvidenceScope
    required_files: list[str]
    present_files: list[str]
    missing_files: list[str]
    complete: bool

    @model_validator(mode="after")
    def validate_file_names_are_batch_safe(self) -> "Stage125EvidenceBundleCheck":
        for field_name in ["required_files", "present_files", "missing_files"]:
            for value in getattr(self, field_name):
                validate_no_absolute_local_path(value, field_name=field_name)
        return self


class Stage125HotPathReport(StrictBaseModel):
    schema_version: str = "repo_harness_stage12_5_hot_path_report_v0"
    episode_count: int = Field(ge=0)
    manifest_rewrite_count_per_episode: float = Field(ge=0.0)
    manifest_bytes_written_per_episode: float = Field(ge=0.0)
    artifact_write_seconds_p50: float = Field(ge=0.0)
    artifact_write_seconds_p95: float = Field(ge=0.0)
    artifact_count_per_episode: float = Field(ge=0.0)
    artifact_bytes_per_episode: float = Field(ge=0.0)
    tool_seconds_p50: float = Field(ge=0.0)
    tool_seconds_p95: float = Field(ge=0.0)
    tool_call_count_per_episode: float = Field(ge=0.0)
    diagnostics: list[str] = Field(default_factory=list)


class Stage125BaselineProfile(StrictBaseModel):
    schema_version: str = "repo_harness_stage12_5_baseline_profile_v0"
    profile_scope: EvidenceScope = "local"
    dependency_setup_seconds_p50: float | None = Field(default=None, ge=0.0)
    workspace_materialization_seconds_p50: float | None = Field(default=None, ge=0.0)
    verifier_queue_wait_seconds_p50: float | None = Field(default=None, ge=0.0)
    verifier_execution_seconds_p50: float | None = Field(default=None, ge=0.0)
    model_call_seconds_p50: float | None = Field(default=None, ge=0.0)
    tokenizer_seconds_p50: float | None = Field(default=None, ge=0.0)
    prompt_build_seconds_p50: float | None = Field(default=None, ge=0.0)
    hot_path_report: Stage125HotPathReport | None = None
    unsupported_diagnostics: list[str] = Field(default_factory=list)


class Stage125AcceptanceSummary(StrictBaseModel):
    schema_version: str = "repo_harness_stage12_5_acceptance_summary_v0"
    scope: EvidenceScope
    code_commit: str | None = None
    evidence_complete: bool
    evidence_bundle_check: Stage125EvidenceBundleCheck
    formal_batch_validator_passed: bool = False
    visibility_gate_passed: bool = False
    dependency_cache_validated: bool = False
    workspace_cache_validated: bool = False
    valid_sample_refill_validated: bool = False
    trainer_global_step_completed: bool | None = None
    working_tree_clean: bool | None = None
    acceptance_ready: bool = False
    blocking_reasons: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def fill_acceptance_ready(self) -> "Stage125AcceptanceSummary":
        blockers = list(self.blocking_reasons)
        if not self.evidence_complete:
            blockers.append("evidence_bundle_incomplete")
        for field_name in [
            "formal_batch_validator_passed",
            "visibility_gate_passed",
            "dependency_cache_validated",
            "workspace_cache_validated",
            "valid_sample_refill_validated",
        ]:
            if not getattr(self, field_name):
                blockers.append(f"{field_name}_false")
        if self.scope == "remote" and self.trainer_global_step_completed is not True:
            blockers.append("trainer_global_step_not_completed")
        if self.working_tree_clean is False:
            blockers.append("working_tree_dirty_or_untracked")
        object.__setattr__(self, "blocking_reasons", sorted(set(blockers)))
        object.__setattr__(self, "acceptance_ready", not self.blocking_reasons)
        return self


def check_stage12_5_evidence_bundle(
    bundle_dir: str | Path,
    *,
    scope: EvidenceScope,
) -> Stage125EvidenceBundleCheck:
    required = (
        STAGE12_5_LOCAL_REQUIRED_FILES
        if scope == "local"
        else STAGE12_5_REMOTE_REQUIRED_FILES
    )
    root = Path(bundle_dir)
    present = sorted(path.name for path in root.iterdir()) if root.exists() else []
    missing = [name for name in required if name not in present]
    return Stage125EvidenceBundleCheck(
        scope=scope,
        required_files=list(required),
        present_files=present,
        missing_files=missing,
        complete=not missing,
    )


def build_stage12_5_acceptance_summary(
    *,
    bundle_dir: str | Path,
    scope: EvidenceScope,
    code_commit: str | None = None,
    formal_batch_validator_passed: bool = False,
    visibility_gate_passed: bool = False,
    dependency_cache_validated: bool = False,
    workspace_cache_validated: bool = False,
    valid_sample_refill_validated: bool = False,
    trainer_global_step_completed: bool | None = None,
    working_tree_clean: bool | None = None,
    blocking_reasons: Sequence[str] = (),
) -> Stage125AcceptanceSummary:
    check = check_stage12_5_evidence_bundle(bundle_dir, scope=scope)
    check = _treat_acceptance_summary_as_self_produced(check)
    return Stage125AcceptanceSummary(
        scope=scope,
        code_commit=code_commit,
        evidence_complete=check.complete,
        evidence_bundle_check=check,
        formal_batch_validator_passed=formal_batch_validator_passed,
        visibility_gate_passed=visibility_gate_passed,
        dependency_cache_validated=dependency_cache_validated,
        workspace_cache_validated=workspace_cache_validated,
        valid_sample_refill_validated=valid_sample_refill_validated,
        trainer_global_step_completed=trainer_global_step_completed,
        working_tree_clean=working_tree_clean,
        blocking_reasons=list(blocking_reasons),
    )


def _treat_acceptance_summary_as_self_produced(
    check: Stage125EvidenceBundleCheck,
) -> Stage125EvidenceBundleCheck:
    summary_name = (
        "stage12_5_local_acceptance_summary.json"
        if check.scope == "local"
        else "stage12_5_acceptance_summary.json"
    )
    if summary_name not in check.missing_files:
        return check
    present = sorted({*check.present_files, summary_name})
    missing = [name for name in check.missing_files if name != summary_name]
    return check.model_copy(
        update={
            "present_files": present,
            "missing_files": missing,
            "complete": not missing,
        }
    )


def build_hot_path_report(run_dirs: Iterable[str | Path]) -> Stage125HotPathReport:
    per_episode: list[dict[str, float]] = []
    diagnostics: list[str] = []
    for item in run_dirs:
        run_dir = Path(item)
        if not run_dir.exists():
            diagnostics.append(f"missing_run_dir:{run_dir.name}")
            continue
        events = _read_jsonl(run_dir / "events.jsonl")
        artifact_seconds = [
            _duration_seconds(event)
            for event in events
            if _matches(str(event.get("event_type", "")), ("artifact_write", "artifact_created"))
        ]
        tool_seconds = [
            _duration_seconds(event)
            for event in events
            if _matches(str(event.get("event_type", "")), ("tool_call", "tool_execution", "workspace_command"))
        ]
        manifest_stats = _manifest_stats(run_dir)
        per_episode.append(
            {
                "manifest_rewrite_count": manifest_stats["manifest_rewrite_count"],
                "manifest_bytes_written": manifest_stats["manifest_bytes_written"],
                "artifact_count": manifest_stats["artifact_count"],
                "artifact_bytes": manifest_stats["artifact_bytes"],
                "artifact_write_seconds": sum(artifact_seconds),
                "tool_seconds": sum(tool_seconds),
                "tool_call_count": float(len([value for value in tool_seconds if value >= 0.0])),
            }
        )
    if not per_episode:
        return Stage125HotPathReport(
            episode_count=0,
            manifest_rewrite_count_per_episode=0.0,
            manifest_bytes_written_per_episode=0.0,
            artifact_write_seconds_p50=0.0,
            artifact_write_seconds_p95=0.0,
            artifact_count_per_episode=0.0,
            artifact_bytes_per_episode=0.0,
            tool_seconds_p50=0.0,
            tool_seconds_p95=0.0,
            tool_call_count_per_episode=0.0,
            diagnostics=[*diagnostics, "no_run_dirs_available"],
        )
    return Stage125HotPathReport(
        episode_count=len(per_episode),
        manifest_rewrite_count_per_episode=_average(row["manifest_rewrite_count"] for row in per_episode),
        manifest_bytes_written_per_episode=_average(row["manifest_bytes_written"] for row in per_episode),
        artifact_write_seconds_p50=_percentile([row["artifact_write_seconds"] for row in per_episode], 50),
        artifact_write_seconds_p95=_percentile([row["artifact_write_seconds"] for row in per_episode], 95),
        artifact_count_per_episode=_average(row["artifact_count"] for row in per_episode),
        artifact_bytes_per_episode=_average(row["artifact_bytes"] for row in per_episode),
        tool_seconds_p50=_percentile([row["tool_seconds"] for row in per_episode], 50),
        tool_seconds_p95=_percentile([row["tool_seconds"] for row in per_episode], 95),
        tool_call_count_per_episode=_average(row["tool_call_count"] for row in per_episode),
        diagnostics=diagnostics,
    )


def build_baseline_profile_from_run_dirs(
    run_dirs: Iterable[str | Path],
    *,
    profile_scope: EvidenceScope = "local",
    unsupported_diagnostics: Sequence[str] = (),
) -> Stage125BaselineProfile:
    hot_path = build_hot_path_report(run_dirs)
    return Stage125BaselineProfile(
        profile_scope=profile_scope,
        hot_path_report=hot_path,
        unsupported_diagnostics=list(unsupported_diagnostics),
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _duration_seconds(event: Mapping[str, Any]) -> float:
    duration_ms = event.get("duration_ms")
    if isinstance(duration_ms, int | float):
        return max(0.0, float(duration_ms) / 1000.0)
    return 0.0


def _manifest_stats(run_dir: Path) -> dict[str, float]:
    candidates = [run_dir / "artifacts.json", run_dir / "artifact_manifest.json"]
    manifest_path = next((path for path in candidates if path.exists()), None)
    if manifest_path is None:
        return {
            "manifest_rewrite_count": 0.0,
            "manifest_bytes_written": 0.0,
            "artifact_count": 0.0,
            "artifact_bytes": 0.0,
        }
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "manifest_rewrite_count": 1.0,
            "manifest_bytes_written": float(manifest_path.stat().st_size),
            "artifact_count": 0.0,
            "artifact_bytes": 0.0,
        }
    artifacts = payload.get("artifacts") if isinstance(payload, dict) else None
    artifact_count = 0
    artifact_bytes = 0
    if isinstance(artifacts, list):
        for item in artifacts:
            if not isinstance(item, Mapping):
                continue
            artifact_count += 1
            size_bytes = item.get("size_bytes")
            if isinstance(size_bytes, int):
                artifact_bytes += max(0, size_bytes)
    return {
        "manifest_rewrite_count": 1.0,
        "manifest_bytes_written": float(manifest_path.stat().st_size),
        "artifact_count": float(artifact_count),
        "artifact_bytes": float(artifact_bytes),
    }


def _matches(value: str, markers: tuple[str, ...]) -> bool:
    return any(marker in value for marker in markers)


def _average(values: Iterable[float]) -> float:
    items = list(values)
    return 0.0 if not items else sum(items) / len(items)


def _percentile(values: list[float], percentile: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile / 100.0
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction
