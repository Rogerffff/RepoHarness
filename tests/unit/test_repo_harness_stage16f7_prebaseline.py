from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from repo_harness.cli.main import main
from repo_harness.evaluation.episode_runner import (
    _provider_failure_accounting_report,
    run_episode_task,
)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_stage16f7_run_episode_task_default_remains_training_fast(tmp_path: Path) -> None:
    run_dir = run_episode_task(
        "tests/fixtures/tasks/task_001.yaml",
        config_path="tests/fixtures/run_configs/stage16f3_run_episode_task_mock.yaml",
        output_dir=tmp_path / "runs",
        run_id="stage16f7_default_training_fast",
        gateway_route="mock",
        assert_projection_complete=True,
    )

    summary = _read_json(run_dir / "run_episode_task_summary.json")
    run_config_projection = _read_json(run_dir / "compat_projection" / "run_config_projection.json")

    assert summary["run_mode"] == "training_fast"
    assert run_config_projection["request_run_mode"] == "training_fast"


def test_stage16f7_training_fast_reports_projection_facts_not_raw_payloads(tmp_path: Path) -> None:
    run_dir = run_episode_task(
        "tests/fixtures/tasks/task_001.yaml",
        config_path="tests/fixtures/run_configs/stage16f4_mock_provider_public_feedback.yaml",
        output_dir=tmp_path / "runs",
        run_id="stage16f7_training_fast_projection",
        gateway_route="mock",
        assert_projection_complete=True,
    )

    provider_report = _read_json(run_dir / "stage16_5_provider_failure_accounting.json")

    assert provider_report["run_mode"] == "training_fast"
    assert provider_report["raw_provider_request_artifact_count"] == 0
    assert provider_report["raw_provider_response_artifact_count"] == 0
    assert provider_report["provider_request_projection_fact_count"] >= 1
    assert provider_report["provider_response_projection_fact_count"] >= 1
    assert provider_report["raw_payload_persisted"] is False


def test_stage16f7_full_audit_writes_provider_and_inventory_reports(tmp_path: Path) -> None:
    run_dir = run_episode_task(
        "tests/fixtures/tasks/task_001.yaml",
        config_path="tests/fixtures/run_configs/stage16f4_mock_provider_public_feedback.yaml",
        output_dir=tmp_path / "runs",
        run_id="stage16f7_full_audit",
        gateway_route="mock",
        run_mode="full_audit",
        assert_projection_complete=True,
    )

    summary = _read_json(run_dir / "run_episode_task_summary.json")
    provider_report = _read_json(run_dir / "stage16_5_provider_failure_accounting.json")
    official_report = _read_json(run_dir / "stage16_5_official_prediction_eligibility.json")
    inventory = _read_json(run_dir / "stage16_5_case_artifact_inventory.json")

    assert summary["run_mode"] == "full_audit"
    assert provider_report["run_mode"] == "full_audit"
    assert provider_report["raw_provider_request_artifact_count"] >= 1
    assert provider_report["raw_provider_response_artifact_count"] >= 1
    assert provider_report["raw_payload_persisted"] is True
    assert provider_report["provider_attempt_count"] == 0
    assert all(
        artifact["content_visibility"] == "not_public"
        for artifact in provider_report["request_artifacts"] + provider_report["response_artifacts"]
    )
    assert official_report["official_prediction_uses_cleaned_patch"] is True
    assert official_report["final_patch_sha256"] == official_report["cleaned_patch_sha256"]
    assert inventory["run_mode"] == "full_audit"
    assert inventory["artifact_records"]["final_patch"]["present"] is True
    assert inventory["artifact_records"]["provider_failure_accounting"]["present"] is True


def test_stage16f7_provider_invalid_response_is_accounted_separately(tmp_path: Path) -> None:
    config_path = tmp_path / "invalid_response_config.yaml"
    config_path.write_text(
        "\n".join(
            [
                "run_id_prefix: stage16f7",
                "tasks:",
                "  - tests/fixtures/tasks/task_001.yaml",
                "model:",
                "  provider: mock",
                "  model_id: mock-stage16f7",
                "  provider_specific_options:",
                "    mock_gateway_kind: model_client",
                "    mock_scenario: invalid_response",
                "runtime:",
                "  scaffold_id: simple_react",
                "  execution_mode: local_process",
                "  permission_mode: auto",
                "  test_feedback_policy: public_only",
                "  feedback_tests_passed_policy: require_model_final",
                "  max_turns: 1",
                "  max_tool_calls: 2",
                "  max_test_runs: 1",
                "workspace:",
                f"  output_dir: {tmp_path / 'runs'}",
                "  keep_workspace: true",
                "  default_command_timeout_sec: 60",
                "  max_tool_output_chars: 8000",
                "  network_policy: deny_agent_run",
                "",
            ]
        ),
        encoding="utf-8",
    )

    run_dir = run_episode_task(
        "tests/fixtures/tasks/task_001.yaml",
        config_path=config_path,
        run_id="stage16f7_invalid_response",
        gateway_route="mock",
        run_mode="full_audit",
        assert_projection_complete=True,
    )

    provider_report = _read_json(run_dir / "stage16_5_provider_failure_accounting.json")

    assert provider_report["invalid_response_body_count"] == 1
    assert provider_report["provider_infrastructure_failure_count"] == 1
    assert provider_report["model_semantic_failure_count"] == 0
    assert provider_report["failure_owner"] == "provider_or_infrastructure"
    assert provider_report["retry_count_from_model_call_event"] == 0


def test_stage16f7_provider_attempt_records_are_summarized_without_raw_refs(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    artifact_dir = run_dir / "llm_gateway" / "run" / "call" / "artifacts"
    artifact_dir.mkdir(parents=True)
    request_ref = {
        "kind": "raw_deepseek_provider_request",
        "sha256": "a" * 64,
        "relative_path": "artifacts/raw_request.json",
    }
    response_ref = {
        "kind": "raw_deepseek_provider_response",
        "sha256": "b" * 64,
        "relative_path": "artifacts/raw_response.json",
    }
    attempt_payload = {
        "schema_version": "repo_harness_provider_attempt_v0",
        "attempt_index": 1,
        "model_call_id": "call",
        "provider": "deepseek",
        "retryable": True,
        "error_type": "provider_timeout",
        "delay_ms": 100,
        "request_ref": request_ref,
        "response_ref": response_ref,
        "provider_request_id": "provider-private-request-id",
        "duration_ms": 200,
        "terminal": False,
    }
    event_payload = {
        "schema_version": "repo_harness_model_call_event_v0",
        "model_call_id": "call",
        "provider": "deepseek",
        "retry_count": 1,
        "model_error_type": None,
    }
    (artifact_dir / "attempt.json").write_text(json.dumps(attempt_payload), encoding="utf-8")
    (artifact_dir / "event.json").write_text(json.dumps(event_payload), encoding="utf-8")
    (artifact_dir.parent / "artifacts.json").write_text(
        json.dumps(
            {
                "schema_version": "repo_harness_artifacts_v0",
                "run_id": "run",
                "artifacts": [
                    {
                        "artifact_id": "attempt",
                        "relative_path": "artifacts/attempt.json",
                        "kind": "provider_attempt",
                        "sha256": "c" * 64,
                        "size_bytes": 10,
                        "redaction_status": "not_sensitive",
                        "retention_policy": "keep",
                    },
                    {
                        "artifact_id": "event",
                        "relative_path": "artifacts/event.json",
                        "kind": "model_call_event",
                        "sha256": "d" * 64,
                        "size_bytes": 10,
                        "redaction_status": "not_needed",
                        "retention_policy": "keep",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    report = _provider_failure_accounting_report(
        run_dir=run_dir,
        request=SimpleNamespace(
            run_id="run",
            task_id="task",
            run_mode="full_audit",
            llm_gateway_route="deepseek",
        ),
        result_status="succeeded",
    )

    assert report["provider_attempt_count"] == 1
    assert report["provider_attempt_error_types"] == ["provider_timeout"]
    assert report["retryable_attempt_count"] == 1
    assert report["terminal_attempt_count"] == 0
    assert report["retry_count_from_model_call_event"] == 1
    assert report["provider_infrastructure_failure_count"] == 0
    attempt_record = report["provider_attempt_records"][0]
    assert attempt_record["provider_request_id_present"] is True
    assert attempt_record["request_ref_sha256"] == "a" * 64
    assert "relative_path" not in attempt_record


def test_stage16f7_cli_accepts_explicit_full_audit_run_mode(tmp_path: Path) -> None:
    output_dir = tmp_path / "runs"

    exit_code = main(
        [
            "run-episode-task",
            "tests/fixtures/tasks/task_001.yaml",
            "--config",
            "tests/fixtures/run_configs/stage16f4_mock_provider_public_feedback.yaml",
            "--output-dir",
            str(output_dir),
            "--run-id",
            "stage16f7_cli_full_audit",
            "--gateway-route",
            "mock",
            "--run-mode",
            "full_audit",
            "--assert-projection-complete",
        ]
    )

    assert exit_code == 0
    summary = _read_json(output_dir / "stage16f7_cli_full_audit" / "run_episode_task_summary.json")
    assert summary["run_mode"] == "full_audit"
