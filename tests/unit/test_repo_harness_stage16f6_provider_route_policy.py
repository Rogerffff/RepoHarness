from __future__ import annotations

from pathlib import Path

import pytest

from repo_harness.evaluation.stage16f6_smoke import (
    Stage16F6SmokeError,
    inspect_stage16f6_real_model_smoke,
)

from stage16f6_test_helpers import refresh_evidence_map, read_json, write_json, write_valid_stage16f6_evidence


def test_stage16f6_rejects_external_provider_policy_loss_candidate(tmp_path: Path) -> None:
    write_valid_stage16f6_evidence(tmp_path)
    route_path = tmp_path / "stage16f6_provider_route_policy_report.json"
    payload = read_json(route_path)
    payload["case_route_results"][0]["policy_loss_candidate"] = True
    write_json(route_path, payload)

    with pytest.raises(Stage16F6SmokeError, match="non_verl_policy_loss_candidate"):
        inspect_stage16f6_real_model_smoke(tmp_path, assert_complete=True)


def test_stage16f6_rejects_route_report_case_id_mismatch(tmp_path: Path) -> None:
    write_valid_stage16f6_evidence(tmp_path)
    route_path = tmp_path / "stage16f6_provider_route_policy_report.json"
    payload = read_json(route_path)
    payload["case_route_results"][0]["case_id"] = "different-case"
    write_json(route_path, payload)

    with pytest.raises(Stage16F6SmokeError, match="case_manifest_provider_route_policy_report_case_id_mismatch"):
        inspect_stage16f6_real_model_smoke(tmp_path, assert_complete=True)


def test_stage16f6_rejects_external_provider_training_eligibility_assertion(tmp_path: Path) -> None:
    write_valid_stage16f6_evidence(tmp_path)
    route_path = tmp_path / "stage16f6_provider_route_policy_report.json"
    payload = read_json(route_path)
    payload["case_route_results"][0]["training_data_eligibility_asserted"] = True
    write_json(route_path, payload)

    with pytest.raises(Stage16F6SmokeError, match="non_verl_training_data_eligibility_asserted"):
        inspect_stage16f6_real_model_smoke(tmp_path, assert_complete=True)


def test_stage16f6_rejects_real_model_report_policy_loss_mismatch(tmp_path: Path) -> None:
    write_valid_stage16f6_evidence(tmp_path)
    run_report_path = tmp_path / "stage16f6_real_model_run_report.json"
    payload = read_json(run_report_path)
    payload["case_records"][0]["formal_online_rl_eligible"] = True
    payload["case_records"][0]["policy_loss_candidate"] = True
    write_json(run_report_path, payload)
    refresh_evidence_map(tmp_path)

    with pytest.raises(Stage16F6SmokeError, match="real_model_provider_route_field_mismatch:case-001"):
        inspect_stage16f6_real_model_smoke(tmp_path, assert_complete=True)


def test_stage16f6_requires_reason_not_policy_loss_candidate(tmp_path: Path) -> None:
    write_valid_stage16f6_evidence(tmp_path)
    route_path = tmp_path / "stage16f6_provider_route_policy_report.json"
    payload = read_json(route_path)
    payload["case_route_results"][0].pop("reason_not_policy_loss_candidate")
    write_json(route_path, payload)
    refresh_evidence_map(tmp_path)

    with pytest.raises(Stage16F6SmokeError, match="missing_reason_not_policy_loss_candidate:case-001"):
        inspect_stage16f6_real_model_smoke(tmp_path, assert_complete=True)


def test_stage16f6_requires_exact_external_provider_policy_loss_rejection_reason(tmp_path: Path) -> None:
    write_valid_stage16f6_evidence(tmp_path)
    route_path = tmp_path / "stage16f6_provider_route_policy_report.json"
    payload = read_json(route_path)
    payload["case_route_results"][0]["reason_not_policy_loss_candidate"] = "some_other_nonempty_reason"
    write_json(route_path, payload)
    refresh_evidence_map(tmp_path)

    with pytest.raises(
        Stage16F6SmokeError,
        match="external_provider_policy_loss_rejection_reason_mismatch:case-001",
    ):
        inspect_stage16f6_real_model_smoke(tmp_path, assert_complete=True)


def test_stage16f6_public_feedback_requires_real_observation(tmp_path: Path) -> None:
    write_valid_stage16f6_evidence(tmp_path)
    feedback_path = tmp_path / "stage16f6_public_feedback_report.json"
    payload = read_json(feedback_path)
    payload["case_public_feedback_results"][0]["public_feedback_observed"] = False
    payload["case_public_feedback_results"][0]["public_feedback_event_count"] = 0
    payload["case_public_feedback_results"][0]["run_tests_tool_call_observed"] = False
    payload["public_feedback_observed_case_count"] = 0
    payload["public_feedback_event_count"] = 0
    write_json(feedback_path, payload)

    with pytest.raises(Stage16F6SmokeError, match="public_feedback_observed_case_count_too_low"):
        inspect_stage16f6_real_model_smoke(tmp_path, assert_complete=True)


def test_stage16f6_public_feedback_observation_requires_run_tests_call(tmp_path: Path) -> None:
    write_valid_stage16f6_evidence(tmp_path)
    feedback_path = tmp_path / "stage16f6_public_feedback_report.json"
    payload = read_json(feedback_path)
    payload["case_public_feedback_results"][0]["run_tests_tool_call_observed"] = False
    write_json(feedback_path, payload)

    with pytest.raises(Stage16F6SmokeError, match="public_feedback_without_run_tests"):
        inspect_stage16f6_real_model_smoke(tmp_path, assert_complete=True)
