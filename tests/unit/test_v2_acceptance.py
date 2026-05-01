import hashlib
import json
from pathlib import Path

import pytest

from repo_harness.errors import ConfigError
from repo_harness.v2_acceptance import (
    build_v2_acceptance_report,
    inspect_feedback_policy_coverage,
    inspect_v2_acceptance,
)
from repo_harness.workspace import build_workspace_backend_status


def test_feedback_policy_coverage_report_asserts_complete(tmp_path: Path):
    experiment_dir = _write_experiment(tmp_path)
    report = tmp_path / "feedback_policy_report.json"

    output = inspect_feedback_policy_coverage(
        experiment_dir=experiment_dir,
        output=report,
        assert_complete=True,
    )
    payload = _read_json(report)

    assert payload["status"] == "passed"
    assert set(payload["test_feedback_policy_coverage"]) == {
        "disabled",
        "public_only",
        "structured_public_feedback",
        "oracle_hidden_feedback",
    }
    assert "feedback_policy_coverage=passed" in output


def test_build_and_inspect_v2_acceptance_report(tmp_path: Path):
    paths = _write_acceptance_inputs(tmp_path)
    acceptance = tmp_path / "acceptance" / "v2_acceptance_report.json"

    build_v2_acceptance_report(
        v1_regression_dir=paths["v1_dir"],
        task_set_manifest=paths["task_manifest"],
        mock_provider_report=paths["mock_report"],
        real_provider_report=paths["real_report"],
        feedback_policy_report=paths["feedback_report"],
        export_audit_roots=[paths["exports_root"]],
        docker_status=paths["docker_status"],
        output=acceptance,
    )
    output = inspect_v2_acceptance(acceptance, assert_complete=True)
    payload = _read_json(acceptance)

    assert payload["status"] == "passed"
    assert payload["export_audits"]["format_distribution"] == {
        "preference_jsonl": 1,
        "rl_jsonl": 1,
        "sft_jsonl": 1,
    }
    assert "v2_acceptance=passed" in output


def test_inspect_v2_acceptance_rejects_fallback_masquerading_as_deepseek(tmp_path: Path):
    paths = _write_acceptance_inputs(tmp_path)
    _write_json(
        paths["real_report"],
        {
            "status": "accepted_with_credentials",
            "requested_provider": "deepseek",
            "actual_provider": "openai",
            "provider_model": "gpt-5-mini",
            "provider_base_url": None,
            "provider_endpoint_category": "openai_chat_completions_sdk",
            "fallback_used": True,
            "fallback_reason": "deepseek_primary_provider_error",
            "fallback_policy_version": "repo_harness_real_provider_fallback_v0",
            "credential_status": "present",
            "credential_source": "environment",
            "model_error_type": None,
            "run_dir": "runs/example",
            "redaction_status": "redacted",
            "final_verifier_status": "accepted",
            "run_outcome": "success",
            "official_docs_checked": True,
            "official_docs_url": "https://api-docs.deepseek.com/zh-cn/",
            "checked_at_date": "2026-05-01",
        },
    )
    acceptance = tmp_path / "acceptance" / "v2_acceptance_report.json"
    build_v2_acceptance_report(
        v1_regression_dir=paths["v1_dir"],
        task_set_manifest=paths["task_manifest"],
        mock_provider_report=paths["mock_report"],
        real_provider_report=paths["real_report"],
        feedback_policy_report=paths["feedback_report"],
        export_audit_roots=[paths["exports_root"]],
        docker_status=paths["docker_status"],
        output=acceptance,
    )

    with pytest.raises(ConfigError, match="OpenAI fallback"):
        inspect_v2_acceptance(acceptance, assert_complete=True)


def test_inspect_v2_acceptance_rejects_missing_evidence_ref(tmp_path: Path):
    paths = _write_acceptance_inputs(tmp_path)
    acceptance = tmp_path / "acceptance" / "v2_acceptance_report.json"
    build_v2_acceptance_report(
        v1_regression_dir=paths["v1_dir"],
        task_set_manifest=paths["task_manifest"],
        mock_provider_report=paths["mock_report"],
        real_provider_report=paths["real_report"],
        feedback_policy_report=paths["feedback_report"],
        export_audit_roots=[paths["exports_root"]],
        docker_status=paths["docker_status"],
        output=acceptance,
    )
    payload = _read_json(acceptance)
    del payload["evidence_refs"]["task_set_manifest"]
    _write_json(acceptance, payload)

    with pytest.raises(ConfigError, match="missing required evidence refs"):
        inspect_v2_acceptance(acceptance, assert_complete=True)


def test_inspect_v2_acceptance_rejects_accepted_provider_without_credentials(tmp_path: Path):
    paths = _write_acceptance_inputs(tmp_path)
    _write_json(
        paths["real_report"],
        {
            "status": "accepted_with_credentials",
            "requested_provider": "deepseek",
            "actual_provider": "deepseek",
            "provider_model": "deepseek-v4-pro",
            "provider_base_url": "https://api.deepseek.com",
            "provider_endpoint_category": "deepseek_openai_compatible_chat_completions",
            "fallback_used": False,
            "fallback_reason": None,
            "fallback_policy_version": None,
            "credential_status": "missing_all",
            "credential_source": "none",
            "model_error_type": None,
            "run_dir": "runs/example",
            "redaction_status": "redacted",
            "final_verifier_status": "accepted",
            "run_outcome": "success",
            "official_docs_checked": True,
            "official_docs_url": "https://api-docs.deepseek.com/zh-cn/",
            "checked_at_date": "2026-05-01",
        },
    )
    acceptance = tmp_path / "acceptance" / "v2_acceptance_report.json"
    build_v2_acceptance_report(
        v1_regression_dir=paths["v1_dir"],
        task_set_manifest=paths["task_manifest"],
        mock_provider_report=paths["mock_report"],
        real_provider_report=paths["real_report"],
        feedback_policy_report=paths["feedback_report"],
        export_audit_roots=[paths["exports_root"]],
        docker_status=paths["docker_status"],
        output=acceptance,
    )

    with pytest.raises(ConfigError, match="credential_status=present"):
        inspect_v2_acceptance(acceptance, assert_complete=True)


def test_inspect_v2_acceptance_rejects_docker_summary_mismatch(tmp_path: Path):
    paths = _write_acceptance_inputs(tmp_path)
    acceptance = tmp_path / "acceptance" / "v2_acceptance_report.json"
    build_v2_acceptance_report(
        v1_regression_dir=paths["v1_dir"],
        task_set_manifest=paths["task_manifest"],
        mock_provider_report=paths["mock_report"],
        real_provider_report=paths["real_report"],
        feedback_policy_report=paths["feedback_report"],
        export_audit_roots=[paths["exports_root"]],
        docker_status=paths["docker_status"],
        output=acceptance,
    )
    payload = _read_json(acceptance)
    payload["docker_stage"]["mode"] = "docker_backend"
    payload["docker_stage"]["docker_backend_implemented"] = True
    _write_json(acceptance, payload)

    with pytest.raises(ConfigError, match="docker_stage summary does not match"):
        inspect_v2_acceptance(acceptance, assert_complete=True)


def test_inspect_v2_acceptance_rejects_provider_raw_marker_in_training_payload(tmp_path: Path):
    paths = _write_acceptance_inputs(tmp_path)
    acceptance = tmp_path / "acceptance" / "v2_acceptance_report.json"
    build_v2_acceptance_report(
        v1_regression_dir=paths["v1_dir"],
        task_set_manifest=paths["task_manifest"],
        mock_provider_report=paths["mock_report"],
        real_provider_report=paths["real_report"],
        feedback_policy_report=paths["feedback_report"],
        export_audit_roots=[paths["exports_root"]],
        docker_status=paths["docker_status"],
        output=acceptance,
    )
    raw_file = Path(paths["exports_root"]) / "sft_export" / "data.sft.jsonl"
    raw_file.write_text('{"quality":{"training_eligibility":"trainable"},"raw_response":true}\n', encoding="utf-8")
    manifest_path = Path(paths["exports_root"]) / "sft_export" / "export_manifest.json"
    manifest = _read_json(manifest_path)
    manifest["data_files"][0]["sha256"] = _sha256(raw_file)
    _write_json(manifest_path, manifest)

    with pytest.raises(ConfigError, match="provider raw response markers"):
        inspect_v2_acceptance(acceptance, assert_complete=True)


def test_inspect_v2_acceptance_rejects_non_trainable_formal_jsonl(tmp_path: Path):
    paths = _write_acceptance_inputs(tmp_path)
    acceptance = tmp_path / "acceptance" / "v2_acceptance_report.json"
    build_v2_acceptance_report(
        v1_regression_dir=paths["v1_dir"],
        task_set_manifest=paths["task_manifest"],
        mock_provider_report=paths["mock_report"],
        real_provider_report=paths["real_report"],
        feedback_policy_report=paths["feedback_report"],
        export_audit_roots=[paths["exports_root"]],
        docker_status=paths["docker_status"],
        output=acceptance,
    )
    data_file = Path(paths["exports_root"]) / "rl_export" / "data.rl.jsonl"
    data_file.write_text(
        json.dumps(
            {
                "quality": {"training_eligibility": "diagnostic_only"},
                "invalid_for_training": True,
                "invalid_reason": "unit_test",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    manifest_path = Path(paths["exports_root"]) / "rl_export" / "export_manifest.json"
    manifest = _read_json(manifest_path)
    manifest["data_files"][0]["sha256"] = _sha256(data_file)
    _write_json(manifest_path, manifest)

    with pytest.raises(ConfigError, match="export root is not clean"):
        inspect_v2_acceptance(acceptance, assert_complete=True)


def _write_acceptance_inputs(tmp_path: Path) -> dict[str, Path]:
    v1_dir = tmp_path / "v1"
    v1_dir.mkdir()
    _write_json(
        v1_dir / "batch_manifest.json",
        {
            "should_fail_command": False,
            "runs": [
                {"status": "success"},
                {"status": "invalid_task"},
                {"status": "flaky_task"},
            ],
        },
    )
    experiment_dir = _write_experiment(tmp_path)
    feedback_report = experiment_dir / "feedback_policy_report.json"
    inspect_feedback_policy_coverage(
        experiment_dir=experiment_dir,
        output=feedback_report,
        assert_complete=True,
    )
    mock_report = tmp_path / "mock_provider_smoke_report.json"
    _write_json(
        mock_report,
        {
            "status": "accepted",
            "provider": "mock",
            "final_verifier_status": "accepted",
            "run_outcome": "success",
            "model_error_type": None,
            "export_audit_status": "clean",
            "raw_artifact_redaction_status": "redacted",
        },
    )
    real_report = tmp_path / "real_provider_smoke_report.json"
    _write_json(
        real_report,
        {
            "status": "skipped_no_credentials",
            "requested_provider": "deepseek",
            "actual_provider": "none",
            "provider_model": "deepseek-v4-pro",
            "provider_base_url": "https://api.deepseek.com",
            "provider_endpoint_category": "deepseek_openai_compatible_chat_completions",
            "fallback_used": False,
            "fallback_reason": None,
            "fallback_policy_version": None,
            "credential_status": "missing_all",
            "credential_source": "none",
            "model_error_type": None,
            "run_dir": None,
            "redaction_status": "not_applicable",
            "final_verifier_status": None,
            "run_outcome": None,
            "official_docs_checked": True,
            "official_docs_url": "https://api-docs.deepseek.com/zh-cn/",
            "checked_at_date": "2026-05-01",
        },
    )
    docker_status = tmp_path / "docker_stage_status.json"
    _write_json(
        docker_status,
        build_workspace_backend_status(
            mode="interface_only",
            docker_available=False,
            docker_available_reason="unit_test",
        ).model_dump(mode="json"),
    )
    exports_root = tmp_path / "exports"
    _write_export(exports_root, "sft_export", "sft_jsonl", "data.sft.jsonl")
    _write_export(exports_root, "rl_export", "rl_jsonl", "data.rl.jsonl")
    _write_export(exports_root, "pref_export", "preference_jsonl", "data.preference.jsonl")
    return {
        "v1_dir": v1_dir,
        "task_manifest": experiment_dir / "experiment_manifest.json",
        "mock_report": mock_report,
        "real_report": real_report,
        "feedback_report": feedback_report,
        "docker_status": docker_status,
        "exports_root": exports_root,
    }


def _write_experiment(tmp_path: Path) -> Path:
    experiment_dir = tmp_path / "experiment"
    experiment_dir.mkdir(exist_ok=True)
    _write_json(
        experiment_dir / "experiment_manifest.json",
        {
            "experiment_id": "unit_v2_task_set",
            "runs": [{"run_id": f"run_{index}", "status": "success"} for index in range(20)],
        },
    )
    _write_json(
        experiment_dir / "aggregate_metrics.json",
        {
            "task_count": 20,
            "total_runs": 20,
            "recorded_runs": 20,
            "agent_loop_runs": 18,
            "formal_final_verifier_runs": 18,
            "success_count": 18,
            "structured_skipped_runs": 2,
            "status_distribution": {"success": 18, "invalid_task": 2},
        },
    )
    return experiment_dir


def _write_export(root: Path, dirname: str, export_format: str, data_file: str) -> None:
    export_dir = root / dirname
    export_dir.mkdir(parents=True)
    data_path = export_dir / data_file
    data_path.write_text(
        json.dumps({"quality": {"training_eligibility": "trainable"}, "invalid_for_training": False}) + "\n",
        encoding="utf-8",
    )
    audit = {
        "export_id": dirname,
        "format": export_format,
        "status": "passed",
        "summary": {"trainable_count": 1},
        "samples": [
            {
                "sample_id": "sample",
                "data_file": data_file,
                "line_number": 1,
                "training_eligibility": "trainable",
                "audit_items": [],
            }
        ],
    }
    _write_json(export_dir / "audit_report.json", audit)
    (export_dir / "audit_report.md").write_text("# Audit\n", encoding="utf-8")
    manifest = {
        "export_id": dirname,
        "format": export_format,
        "audit_report_path": "audit_report.json",
        "audit_report_sha256": _sha256(export_dir / "audit_report.json"),
        "audit_report_md_path": "audit_report.md",
        "audit_report_md_sha256": _sha256(export_dir / "audit_report.md"),
        "data_files": [
            {
                "relative_path": data_file,
                "sha256": _sha256(data_path),
                "record_count": 1,
            }
        ],
        "record_count": 1,
        "included_count": 1,
        "invalid_count": 0,
        "diagnostic_only_count": 0,
        "skipped_count": 0,
    }
    _write_json(export_dir / "export_manifest.json", manifest)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
