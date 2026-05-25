import json

import pytest

from repo_harness.evaluation.episode_parity import (
    Stage16F4ParityError,
    inspect_stage16f4_parity,
    run_stage16f4_parity_audit,
)


def test_stage16f4_inspector_rejects_projection_report_tamper(tmp_path):
    evidence_dir = run_stage16f4_parity_audit(tmp_path / "evidence", clean_output_dir=True)
    report_path = evidence_dir / "stage16f4_projection_binding_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["case_projection_results"][0]["final_patch_sha256"] = "1" * 64
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(Stage16F4ParityError, match="projection_case_results_not_derived_from_cases"):
        inspect_stage16f4_parity(evidence_dir, assert_complete=True)


def test_stage16f4_inspector_rejects_public_hygiene_path_leak(tmp_path):
    evidence_dir = run_stage16f4_parity_audit(tmp_path / "evidence", clean_output_dir=True)
    report_path = evidence_dir / "stage16f4_run_task_run_episode_parity_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["cases"][0]["new"]["final_patch_hygiene_report"]["filtered_files"] = [
        {"path": "runtime_private/secret.py", "reason": "probe"}
    ]
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(Stage16F4ParityError, match="path_or_secret_leak"):
        inspect_stage16f4_parity(evidence_dir, assert_complete=True)


def test_stage16f4_inspector_rejects_hygiene_digest_tamper(tmp_path):
    evidence_dir = run_stage16f4_parity_audit(tmp_path / "evidence", clean_output_dir=True)
    report_path = evidence_dir / "stage16f4_run_task_run_episode_parity_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["cases"][0]["new"]["final_patch_hygiene_report"]["cleaned_patch_sha256"] = "2" * 64
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(Stage16F4ParityError, match="patch_hygiene_binding_failed"):
        inspect_stage16f4_parity(evidence_dir, assert_complete=True)
