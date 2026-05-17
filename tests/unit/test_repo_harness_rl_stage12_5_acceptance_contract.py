from __future__ import annotations

import json
from pathlib import Path

from repo_harness.rl import (
    STAGE12_5_LOCAL_REQUIRED_FILES,
    STAGE12_5_REMOTE_REQUIRED_FILES,
    build_stage12_5_acceptance_summary,
    check_stage12_5_evidence_bundle,
)


def test_stage12_5_local_evidence_bundle_contract_reports_missing_files(tmp_path: Path) -> None:
    (tmp_path / "environment_cache_report.json").write_text("{}", encoding="utf-8")

    check = check_stage12_5_evidence_bundle(tmp_path, scope="local")

    assert check.complete is False
    assert "workspace_cache_report.json" in check.missing_files
    assert all(not item.startswith("/") for item in check.required_files)


def test_stage12_5_acceptance_summary_requires_safety_gates_and_evidence(tmp_path: Path) -> None:
    for filename in STAGE12_5_LOCAL_REQUIRED_FILES:
        if filename == "stage12_5_local_acceptance_summary.json":
            continue
        (tmp_path / filename).write_text(json.dumps({"file": filename}), encoding="utf-8")

    summary = build_stage12_5_acceptance_summary(
        bundle_dir=tmp_path,
        scope="local",
        code_commit="abc123",
        formal_batch_validator_passed=True,
        visibility_gate_passed=True,
        dependency_cache_validated=True,
        workspace_cache_validated=True,
        valid_sample_refill_validated=True,
    )

    assert summary.evidence_complete is True
    assert "stage12_5_local_acceptance_summary.json" in summary.evidence_bundle_check.present_files
    assert summary.acceptance_ready is True
    assert summary.blocking_reasons == []


def test_stage12_5_remote_acceptance_requires_trainer_global_step(tmp_path: Path) -> None:
    for filename in STAGE12_5_REMOTE_REQUIRED_FILES:
        (tmp_path / filename).write_text("{}", encoding="utf-8")

    summary = build_stage12_5_acceptance_summary(
        bundle_dir=tmp_path,
        scope="remote",
        formal_batch_validator_passed=True,
        visibility_gate_passed=True,
        dependency_cache_validated=True,
        workspace_cache_validated=True,
        valid_sample_refill_validated=True,
        trainer_global_step_completed=False,
    )

    assert summary.acceptance_ready is False
    assert summary.blocking_reasons == ["trainer_global_step_not_completed"]


def test_stage12_5_acceptance_summary_blocks_dirty_or_untracked_worktree(tmp_path: Path) -> None:
    for filename in STAGE12_5_LOCAL_REQUIRED_FILES:
        if filename == "stage12_5_local_acceptance_summary.json":
            continue
        (tmp_path / filename).write_text(json.dumps({"file": filename}), encoding="utf-8")

    summary = build_stage12_5_acceptance_summary(
        bundle_dir=tmp_path,
        scope="local",
        formal_batch_validator_passed=True,
        visibility_gate_passed=True,
        dependency_cache_validated=True,
        workspace_cache_validated=True,
        valid_sample_refill_validated=True,
        working_tree_clean=False,
    )

    assert summary.acceptance_ready is False
    assert summary.blocking_reasons == ["working_tree_dirty_or_untracked"]
