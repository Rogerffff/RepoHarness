from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from repo_harness_verl.stage14_task_pool import (
    Stage14TaskPoolEntry,
    build_stage14_fixture_sha256_report,
    default_stage14_1_task_pool,
    validate_stage14_task_pool_paths,
)


def test_stage14_1_default_task_pool_has_required_categories_and_paths() -> None:
    spec = default_stage14_1_task_pool()

    assert validate_stage14_task_pool_paths(spec) == []
    categories = {entry.task_category for entry in spec.entries}
    assert "accepted_baseline" in categories
    assert "accepted_dependency" in categories
    assert "trainable_negative_control" in categories
    assert "diagnostic_control" in categories
    assert len({entry.task_id for entry in spec.entries if not entry.diagnostic_control}) >= 3


def test_stage14_1_dependency_entry_is_pinned_and_hashable() -> None:
    spec = default_stage14_1_task_pool()
    dependency = next(entry for entry in spec.entries if entry.task_category == "accepted_dependency")

    assert dependency.task_ref == "tests/fixtures/tasks/task_dependency_packaging_smoke.yaml"
    assert dependency.repo_fixture_ref == "tests/fixtures/repos/dependency_packaging_smoke"
    assert dependency.dependency_packages == [
        {
            "name": "tomli",
            "version": "2.0.1",
            "artifact": "tomli-2.0.1-py3-none-any.whl",
            "sha256": "939de3e7a6161af0c887ef91b7d41a53e7c5a1ca976325f429cb46ea9bc30ecc",
        }
    ]
    report = build_stage14_fixture_sha256_report(spec)
    paths = {item["path"] for item in report["files"]}
    assert "tests/fixtures/tasks/task_dependency_packaging_smoke.yaml" in paths
    assert "tests/fixtures/repos/dependency_packaging_smoke/app/config_reader.py" in paths
    assert not any("__pycache__" in path or ".pytest_cache" in path or path.endswith(".pyc") for path in paths)
    assert all(not Path(path).is_absolute() for path in paths)


def test_stage14_1_negative_control_uses_committed_public_safe_fixture() -> None:
    spec = default_stage14_1_task_pool()
    negative = next(entry for entry in spec.entries if entry.task_category == "trainable_negative_control")

    assert negative.task_id == "task_stage14_negative_boundary"
    assert negative.task_ref == "tests/fixtures/tasks/task_stage14_negative_boundary.yaml"
    assert negative.repo_fixture_ref == "tests/fixtures/repos/stage14_negative_boundary"
    task_text = Path(negative.task_ref).read_text(encoding="utf-8")
    lowered = task_text.lower()
    assert "hidden_verifier" not in lowered
    assert "gold_patch" not in lowered
    assert "runtime_private" not in lowered


def test_stage14_1_negative_control_baseline_fails_on_boundary_semantics() -> None:
    fixture = Path("tests/fixtures/repos/stage14_negative_boundary")

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
        cwd=fixture,
        check=False,
        capture_output=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        text=True,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert "ModuleNotFoundError" not in output
    assert "test_closed_range_includes_both_edges" not in output
    assert "test_open_upper_range_excludes_upper_edge" in output
    assert "test_open_lower_range_excludes_lower_edge" in output
    assert "test_open_range_excludes_both_edges" in output


def test_stage14_1_task_pool_rejects_diagnostic_policy_loss_entry() -> None:
    with pytest.raises(ValueError, match="diagnostic_control entries cannot be policy-loss queue eligible"):
        Stage14TaskPoolEntry(
            name="bad",
            task_id="bad",
            task_category="diagnostic_control",
            repo_fixture_ref="side-channel-only",
            task_ref="side-channel-only",
            expected_outcome_class="diagnostic_rejected",
            diagnostic_control=True,
            policy_loss_queue_eligible=True,
        )


def test_stage14_1_task_pool_rejects_forbidden_public_markers() -> None:
    with pytest.raises(ValueError, match="forbidden marker"):
        Stage14TaskPoolEntry(
            name="bad",
            task_id="bad",
            task_category="accepted_baseline",
            repo_fixture_ref="tests/fixtures/repos/security_probe",
            task_ref="tests/fixtures/tasks/task_security_probe.yaml",
            expected_outcome_class="accepted",
            prompt_variant="hidden_verifier_leak",
        )


def test_stage14_1_task_pool_detects_missing_paths(tmp_path: Path) -> None:
    spec = default_stage14_1_task_pool()

    failures = validate_stage14_task_pool_paths(spec, repo_root=tmp_path)

    assert "accepted_baseline:repo_fixture_ref_missing:tests/fixtures/repos/security_probe" in failures
    assert "accepted_baseline:task_ref_missing:tests/fixtures/tasks/task_security_probe.yaml" in failures
