from __future__ import annotations

import json
from pathlib import Path

import pytest

from repo_harness.cli.main import main
from repo_harness.evaluation.entrypoint_policy import (
    Stage16F5EntrypointPolicyError,
    inspect_stage16f5_entrypoint_policy,
    write_canonical_entrypoint_report,
    write_legacy_entrypoint_report,
)
from repo_harness.schema_base import stable_hash


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_complete_manifest_fixtures(root: Path, *, legacy_dir: Path) -> None:
    run = {"status": "success", "run_id": "legacy", "run_dir": str(legacy_dir)}
    _write_json(root / "batch_manifest.json", {"schema_version": "test", "runs": [run]})
    _write_json(root / "experiment_manifest.json", {"schema_version": "test", "runs": [run]})


def _write_public_evidence_from_report(root: Path, report: dict) -> None:
    _write_json(root / "stage16f5_entrypoint_policy_report.json", report)
    _write_json(
        root / "stage16f5_acceptance_summary.json",
        {
            "schema_version": "repo_harness_stage16f5_acceptance_summary_v0",
            "status": "passed",
            "stage16f5_complete": True,
            "entrypoint_policy_report_sha256": stable_hash(report),
        },
    )


def test_stage16f5_inspector_rejects_legacy_training_candidate_tamper(tmp_path: Path) -> None:
    legacy_dir = tmp_path / "legacy"
    canonical_dir = tmp_path / "canonical"
    write_legacy_entrypoint_report(legacy_dir, run_id="legacy", task_id="task")
    write_canonical_entrypoint_report(
        canonical_dir,
        run_id="canonical",
        task_id="task",
        episode_execution_spec_sha256="a" * 64,
        compat_projection_complete=True,
        provider_route="mock",
        formal_online_rl_eligible=False,
        policy_loss_candidate=False,
    )
    path = legacy_dir / "legacy_entrypoint_report.json"
    payload = _read_json(path)
    payload["formal_training_data_candidate"] = True
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(Stage16F5EntrypointPolicyError, match="legacy_formal_training_data_candidate_count_nonzero"):
        inspect_stage16f5_entrypoint_policy(tmp_path, assert_complete=True)


def test_stage16f5_inspector_rejects_non_verl_policy_loss_candidate(tmp_path: Path) -> None:
    write_legacy_entrypoint_report(tmp_path / "legacy", run_id="legacy", task_id="task")
    write_canonical_entrypoint_report(
        tmp_path / "canonical",
        run_id="canonical",
        task_id="task",
        episode_execution_spec_sha256="a" * 64,
        compat_projection_complete=True,
        provider_route="mock",
        formal_online_rl_eligible=False,
        policy_loss_candidate=True,
    )

    with pytest.raises(Stage16F5EntrypointPolicyError, match="canonical_non_verl_policy_loss_candidate_count_nonzero"):
        inspect_stage16f5_entrypoint_policy(tmp_path, assert_complete=True)


def test_stage16f5_public_evidence_requires_sample_reports(tmp_path: Path) -> None:
    report = {
        "schema_version": "repo_harness_stage16f5_entrypoint_policy_report_v0",
        "legacy_run_task_report_count": 1,
        "canonical_run_episode_task_report_count": 1,
        "legacy_formal_online_rl_eligible_count": 0,
        "legacy_policy_loss_candidate_count": 0,
        "legacy_new_training_data_default_candidate_count": 0,
        "legacy_new_training_data_default_entrypoint_count": 0,
        "legacy_formal_training_data_candidate_count": 0,
        "canonical_non_verl_policy_loss_candidate_count": 0,
        "canonical_training_data_default_entrypoint_count": 1,
        "batch_manifest_legacy_metadata_status": "passed",
        "experiment_manifest_legacy_metadata_status": "passed",
        "run_episode_batch_status": "deferred_to_later_stage",
        "public_path_leak_scan_passed": True,
        "passed": True,
        "errors": [],
    }
    _write_public_evidence_from_report(tmp_path, report)

    with pytest.raises(Stage16F5EntrypointPolicyError, match="missing_public_evidence_file"):
        inspect_stage16f5_entrypoint_policy(tmp_path, assert_complete=True)


def test_stage16f5_inspector_rejects_incomplete_canonical_projection(tmp_path: Path) -> None:
    legacy_dir = tmp_path / "legacy"
    write_legacy_entrypoint_report(legacy_dir, run_id="legacy", task_id="task")
    write_canonical_entrypoint_report(
        tmp_path / "canonical",
        run_id="canonical",
        task_id="task",
        episode_execution_spec_sha256="a" * 64,
        compat_projection_complete=False,
        provider_route="mock",
        formal_online_rl_eligible=False,
        policy_loss_candidate=False,
    )
    _write_complete_manifest_fixtures(tmp_path, legacy_dir=legacy_dir)

    with pytest.raises(Stage16F5EntrypointPolicyError, match="canonical_report_projection_incomplete"):
        inspect_stage16f5_entrypoint_policy(tmp_path, assert_complete=True)


def test_stage16f5_inspector_rejects_non_verl_formal_online_rl_eligible(tmp_path: Path) -> None:
    legacy_dir = tmp_path / "legacy"
    write_legacy_entrypoint_report(legacy_dir, run_id="legacy", task_id="task")
    write_canonical_entrypoint_report(
        tmp_path / "canonical",
        run_id="canonical",
        task_id="task",
        episode_execution_spec_sha256="a" * 64,
        compat_projection_complete=True,
        provider_route="mock",
        formal_online_rl_eligible=True,
        policy_loss_candidate=False,
    )
    _write_complete_manifest_fixtures(tmp_path, legacy_dir=legacy_dir)

    with pytest.raises(Stage16F5EntrypointPolicyError, match="canonical_report_non_verl_formal_online_rl_eligible"):
        inspect_stage16f5_entrypoint_policy(tmp_path, assert_complete=True)


def test_stage16f5_inspector_rejects_missing_canonical_gate_fields(tmp_path: Path) -> None:
    legacy_dir = tmp_path / "legacy"
    write_legacy_entrypoint_report(legacy_dir, run_id="legacy", task_id="task")
    canonical_dir = tmp_path / "canonical"
    write_canonical_entrypoint_report(
        canonical_dir,
        run_id="canonical",
        task_id="task",
        episode_execution_spec_sha256="a" * 64,
        compat_projection_complete=True,
        provider_route="mock",
        formal_online_rl_eligible=False,
        policy_loss_candidate=False,
    )
    path = canonical_dir / "entrypoint_report.json"
    payload = _read_json(path)
    payload.pop("provider_route")
    payload.pop("formal_online_rl_eligible")
    payload.pop("policy_loss_candidate")
    _write_json(path, payload)
    _write_complete_manifest_fixtures(tmp_path, legacy_dir=legacy_dir)

    with pytest.raises(Stage16F5EntrypointPolicyError, match="canonical_report_missing_provider_route"):
        inspect_stage16f5_entrypoint_policy(tmp_path, assert_complete=True)


def test_stage16f5_public_evidence_requires_acceptance_summary(tmp_path: Path) -> None:
    legacy_dir = tmp_path / "legacy"
    write_legacy_entrypoint_report(legacy_dir, run_id="legacy", task_id="task")
    write_canonical_entrypoint_report(
        tmp_path / "canonical",
        run_id="canonical",
        task_id="task",
        episode_execution_spec_sha256="a" * 64,
        compat_projection_complete=True,
        provider_route="mock",
        formal_online_rl_eligible=False,
        policy_loss_candidate=False,
    )
    _write_complete_manifest_fixtures(tmp_path, legacy_dir=legacy_dir)
    # Build a public report, but intentionally omit the summary file.
    from repo_harness.evaluation.entrypoint_policy import write_stage16f5_entrypoint_policy_evidence

    output = tmp_path / "public"
    write_stage16f5_entrypoint_policy_evidence(source_root=tmp_path, output_dir=output)
    (output / "stage16f5_acceptance_summary.json").unlink()

    with pytest.raises(Stage16F5EntrypointPolicyError, match="missing_public_evidence_file:stage16f5_acceptance_summary.json"):
        inspect_stage16f5_entrypoint_policy(output, assert_complete=True)


def test_stage16f5_public_evidence_rejects_summary_count_tamper(tmp_path: Path) -> None:
    legacy_dir = tmp_path / "legacy"
    write_legacy_entrypoint_report(legacy_dir, run_id="legacy", task_id="task")
    write_canonical_entrypoint_report(
        tmp_path / "canonical",
        run_id="canonical",
        task_id="task",
        episode_execution_spec_sha256="a" * 64,
        compat_projection_complete=True,
        provider_route="mock",
        formal_online_rl_eligible=False,
        policy_loss_candidate=False,
    )
    _write_complete_manifest_fixtures(tmp_path, legacy_dir=legacy_dir)

    from repo_harness.evaluation.entrypoint_policy import write_stage16f5_entrypoint_policy_evidence

    output = tmp_path / "public"
    write_stage16f5_entrypoint_policy_evidence(source_root=tmp_path, output_dir=output)
    summary_path = output / "stage16f5_acceptance_summary.json"
    summary = _read_json(summary_path)
    summary["legacy_policy_loss_candidate_count"] = 999
    summary["legacy_run_task_report_count"] = 999
    _write_json(summary_path, summary)

    with pytest.raises(Stage16F5EntrypointPolicyError, match="acceptance_summary_field_mismatch:legacy_policy_loss_candidate_count"):
        inspect_stage16f5_entrypoint_policy(output, assert_complete=True)


def test_stage16f5_public_evidence_rejects_summary_schema_tamper(tmp_path: Path) -> None:
    legacy_dir = tmp_path / "legacy"
    write_legacy_entrypoint_report(legacy_dir, run_id="legacy", task_id="task")
    write_canonical_entrypoint_report(
        tmp_path / "canonical",
        run_id="canonical",
        task_id="task",
        episode_execution_spec_sha256="a" * 64,
        compat_projection_complete=True,
        provider_route="mock",
        formal_online_rl_eligible=False,
        policy_loss_candidate=False,
    )
    _write_complete_manifest_fixtures(tmp_path, legacy_dir=legacy_dir)

    from repo_harness.evaluation.entrypoint_policy import write_stage16f5_entrypoint_policy_evidence

    output = tmp_path / "public"
    write_stage16f5_entrypoint_policy_evidence(source_root=tmp_path, output_dir=output)
    summary_path = output / "stage16f5_acceptance_summary.json"
    summary = _read_json(summary_path)
    summary["schema_version"] = "wrong"
    _write_json(summary_path, summary)

    with pytest.raises(Stage16F5EntrypointPolicyError, match="acceptance_summary_schema_version_mismatch"):
        inspect_stage16f5_entrypoint_policy(output, assert_complete=True)


def test_stage16f5_inspector_cli_passes_valid_entrypoint_policy(tmp_path: Path, capsys) -> None:
    legacy_dir = tmp_path / "legacy"
    write_legacy_entrypoint_report(legacy_dir, run_id="legacy", task_id="task")
    write_canonical_entrypoint_report(
        tmp_path / "canonical",
        run_id="canonical",
        task_id="task",
        episode_execution_spec_sha256="a" * 64,
        compat_projection_complete=True,
        provider_route="mock",
        formal_online_rl_eligible=False,
        policy_loss_candidate=False,
    )
    _write_complete_manifest_fixtures(tmp_path, legacy_dir=legacy_dir)

    exit_code = main(["inspect-stage16f5-entrypoint-policy", str(tmp_path), "--assert-complete"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["passed"] is True
    assert payload["legacy_formal_online_rl_eligible_count"] == 0
    assert payload["canonical_training_data_default_entrypoint_count"] == 1
