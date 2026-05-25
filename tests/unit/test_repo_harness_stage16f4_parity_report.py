import json

import pytest

from repo_harness.evaluation.episode_parity import (
    Stage16F4ParityError,
    inspect_stage16f4_parity,
    run_stage16f4_parity_audit,
)


def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _canonical_digest(payload):
    import hashlib

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def test_stage16f4_parity_audit_meets_acceptance_thresholds(tmp_path):
    evidence_dir = run_stage16f4_parity_audit(tmp_path / "evidence", clean_output_dir=True)

    summary = _read_json(evidence_dir / "stage16f4_acceptance_summary.json")
    assert summary["status"] == "passed"
    assert summary["parity_task_count"] == 3
    assert summary["run_task_completed_count"] == 3
    assert summary["run_episode_task_completed_count"] == 3
    assert summary["accepted_case_count"] >= 1
    assert summary["rejected_case_count"] >= 1
    assert summary["public_feedback_observed_case_count"] >= 1
    assert summary["nonempty_cleaned_patch_case_count"] >= 1
    assert summary["projection_validator_passed_count"] == summary["run_episode_task_completed_count"]
    assert not (evidence_dir / "runtime_private_runs").exists()

    parsed = json.loads(inspect_stage16f4_parity(evidence_dir, assert_complete=True))
    assert parsed["passed"] is True

    report = _read_json(evidence_dir / "stage16f4_run_task_run_episode_parity_report.json")
    for case in report["cases"]:
        assert case["old"]["reward_score"] == case["new"]["reward_score"]


def test_stage16f4_inspector_rejects_summary_only_spoof(tmp_path):
    evidence_dir = run_stage16f4_parity_audit(tmp_path / "evidence", clean_output_dir=True)
    summary_path = evidence_dir / "stage16f4_acceptance_summary.json"
    summary = _read_json(summary_path)
    summary["accepted_case_count"] += 1
    _write_json(summary_path, summary)

    with pytest.raises(Stage16F4ParityError, match="summary_field_mismatch:accepted_case_count"):
        inspect_stage16f4_parity(evidence_dir, assert_complete=True)


def test_stage16f4_inspector_rejects_reward_score_tamper_even_if_case_digest_is_synced(tmp_path):
    evidence_dir = run_stage16f4_parity_audit(tmp_path / "evidence", clean_output_dir=True)
    report_path = evidence_dir / "stage16f4_run_task_run_episode_parity_report.json"
    summary_path = evidence_dir / "stage16f4_acceptance_summary.json"
    report = _read_json(report_path)
    summary = _read_json(summary_path)
    report["cases"][0]["new"]["reward_score"] = 999
    summary["case_records_digest"] = _canonical_digest(report["cases"])
    _write_json(report_path, report)
    _write_json(summary_path, summary)

    with pytest.raises(Stage16F4ParityError, match="reward_score_difference"):
        inspect_stage16f4_parity(evidence_dir, assert_complete=True)


def test_stage16f4_inspector_rejects_hygiene_semantic_tamper_even_if_case_digest_is_synced(tmp_path):
    evidence_dir = run_stage16f4_parity_audit(tmp_path / "evidence", clean_output_dir=True)
    report_path = evidence_dir / "stage16f4_run_task_run_episode_parity_report.json"
    summary_path = evidence_dir / "stage16f4_acceptance_summary.json"
    report = _read_json(report_path)
    summary = _read_json(summary_path)
    report["cases"][0]["new"]["final_patch_hygiene_report"]["filtered_file_count"] = 99
    summary["case_records_digest"] = _canonical_digest(report["cases"])
    _write_json(report_path, report)
    _write_json(summary_path, summary)

    with pytest.raises(Stage16F4ParityError, match="patch_hygiene_report_semantic_difference"):
        inspect_stage16f4_parity(evidence_dir, assert_complete=True)


def test_stage16f4_inspector_rejects_tool_schema_tamper_without_expected_difference_update(tmp_path):
    evidence_dir = run_stage16f4_parity_audit(tmp_path / "evidence", clean_output_dir=True)
    report_path = evidence_dir / "stage16f4_run_task_run_episode_parity_report.json"
    summary_path = evidence_dir / "stage16f4_acceptance_summary.json"
    report = _read_json(report_path)
    summary = _read_json(summary_path)
    report["cases"][0]["new"]["tool_schema_snapshot_digest"] = "9" * 64
    summary["case_records_digest"] = _canonical_digest(report["cases"])
    _write_json(report_path, report)
    _write_json(summary_path, summary)

    with pytest.raises(Stage16F4ParityError, match="expected_differences_not_derived_from_cases"):
        inspect_stage16f4_parity(evidence_dir, assert_complete=True)


def test_stage16f4_inspector_rejects_non_verl_policy_loss_candidate(tmp_path):
    evidence_dir = run_stage16f4_parity_audit(tmp_path / "evidence", clean_output_dir=True)
    report_path = evidence_dir / "stage16f4_run_task_run_episode_parity_report.json"
    report = _read_json(report_path)
    report["cases"][0]["new"]["policy_loss_candidate"] = True
    _write_json(report_path, report)

    with pytest.raises(Stage16F4ParityError, match="non_verl_policy_loss_candidate_count"):
        inspect_stage16f4_parity(evidence_dir, assert_complete=True)


def test_stage16f4_inspector_rejects_non_verl_formal_online_rl_eligible(tmp_path):
    evidence_dir = run_stage16f4_parity_audit(tmp_path / "evidence", clean_output_dir=True)
    report_path = evidence_dir / "stage16f4_run_task_run_episode_parity_report.json"
    report = _read_json(report_path)
    report["cases"][0]["new"]["formal_online_rl_eligible"] = True
    _write_json(report_path, report)

    with pytest.raises(Stage16F4ParityError, match="non_verl_formal_online_rl_eligible"):
        inspect_stage16f4_parity(evidence_dir, assert_complete=True)


def test_stage16f4_inspector_rejects_public_raw_patch_audit_fields(tmp_path):
    evidence_dir = run_stage16f4_parity_audit(tmp_path / "evidence", clean_output_dir=True)
    report_path = evidence_dir / "stage16f4_projection_binding_report.json"
    report = _read_json(report_path)
    report["raw_patch_sha256"] = "0" * 64
    _write_json(report_path, report)

    with pytest.raises(Stage16F4ParityError, match="forbidden_public_patch_audit_field"):
        inspect_stage16f4_parity(evidence_dir, assert_complete=True)
