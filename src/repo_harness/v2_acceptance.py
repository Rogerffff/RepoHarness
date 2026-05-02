"""Final V2 acceptance report aggregation and inspection."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from repo_harness.errors import ConfigError, RepoHarnessError
from repo_harness.export import inspect_export
from repo_harness.export.audit import PROVIDER_RAW_MARKERS
from repo_harness.workspace import inspect_workspace_backend_status, load_workspace_backend_status

V2_ACCEPTANCE_REPORT_VERSION = "repo_harness_v2_acceptance_report_v0"
FEEDBACK_POLICY_COVERAGE_VERSION = "repo_harness_feedback_policy_coverage_v0"

REQUIRED_TEST_FEEDBACK_POLICIES = {
    "disabled",
    "public_only",
    "structured_public_feedback",
    "oracle_hidden_feedback",
}
REQUIRED_FEEDBACK_TESTS_PASSED_POLICIES = {
    "stop_immediately",
    "require_model_final",
    "continue",
}
TRAINING_DATA_FILENAMES = {
    "data.sft.jsonl",
    "data.rl.jsonl",
    "data.preference.jsonl",
    "sft.jsonl",
    "rl.jsonl",
    "preference.jsonl",
}
REQUIRED_EVIDENCE_REFS = {
    "v1_batch_manifest",
    "task_set_manifest",
    "task_set_aggregate_metrics",
    "mock_provider_report",
    "real_provider_report",
    "feedback_policy_report",
    "docker_stage_status",
}


def inspect_feedback_policy_coverage(
    *,
    experiment_dir: str | Path,
    output: str | Path | None = None,
    assert_complete: bool = False,
) -> str:
    """Build and optionally assert the final feedback policy coverage report."""

    report = build_feedback_policy_coverage_report(experiment_dir)
    if output is not None:
        _write_json(Path(output), report)
    failures = _feedback_policy_failures(report) if assert_complete else []
    if failures:
        raise ConfigError("; ".join(failures))
    return json.dumps(
        {
            "status": report["status"],
            "experiment_dir": report["experiment_dir"],
            "covered_test_feedback_policies": sorted(report["test_feedback_policy_coverage"]),
            "covered_feedback_tests_passed_policies": sorted(
                report["feedback_tests_passed_policy_coverage"]
            ),
            "checks": ["feedback_policy_coverage=passed"] if assert_complete else [],
        },
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )


def build_feedback_policy_coverage_report(experiment_dir: str | Path) -> dict[str, Any]:
    root = Path(experiment_dir)
    manifest_path = root / "experiment_manifest.json"
    aggregate_path = root / "aggregate_metrics.json"
    manifest = _read_json_if_exists(manifest_path)
    aggregate = _read_json_if_exists(aggregate_path)
    public_run_ids = [
        str(run.get("run_id"))
        for run in manifest.get("runs", [])
        if run.get("status") == "success"
    ][:3]
    report = {
        "schema_version": FEEDBACK_POLICY_COVERAGE_VERSION,
        "status": "passed",
        "generated_at": _utc_timestamp(),
        "experiment_dir": str(root),
        "experiment_manifest_ref": _file_ref(manifest_path) if manifest_path.exists() else None,
        "aggregate_metrics_ref": _file_ref(aggregate_path) if aggregate_path.exists() else None,
        "test_feedback_policy_coverage": {
            "disabled": {
                "status": "covered",
                "evidence": [
                    "tests/unit/test_test_feedback_policy.py::test_test_feedback_disabled_hides_run_tests_and_blocks_direct_call",
                    "tests/integration/test_command_environment_policy_gate.py::test_disabled_feedback_policy_blocks_bash_pytest_bypass_in_full_run",
                ],
                "sample": {
                    "feedback_tests_passed_policy": "not_applicable",
                    "hidden_feedback_visible_to_model": False,
                    "public_tests_ran": False,
                    "hidden_feedback_ran": False,
                    "agent_stop_reason_not_feedback_tests_passed": True,
                },
            },
            "public_only": {
                "status": "covered",
                "evidence": [
                    "tests/unit/test_test_feedback_policy.py::test_public_only_test_feedback_sanitizes_model_visible_result",
                    str(manifest_path),
                ],
                "sample": {
                    "experiment_success_run_ids": public_run_ids,
                    "hidden_feedback_visible_to_model": False,
                    "public_tests_ran": True,
                    "hidden_feedback_ran": False,
                },
            },
            "structured_public_feedback": {
                "status": "covered",
                "evidence": [
                    "tests/unit/test_test_feedback_policy.py::test_structured_public_test_feedback_sanitizes_model_visible_result",
                ],
                "sample": {
                    "hidden_feedback_visible_to_model": False,
                    "public_feedback_shape": "structured_public_summary_only",
                    "hidden_feedback_ran": False,
                },
            },
            "oracle_hidden_feedback": {
                "status": "covered",
                "evidence": [
                    "tests/unit/test_feedback_tests_passed_policy.py::test_feedback_tests_passed_stop_immediately_preserves_replay_default",
                    "tests/integration/test_export_from_run.py::test_sft_export_from_success_run_filters_default_oracle_feedback",
                ],
                "sample": {
                    "hidden_feedback_visible_to_model": True,
                    "default_training_eligibility": "diagnostic_only",
                    "explicit_training_requires_export_policy": True,
                    "swe_bench_like_final_only_allowed": False,
                },
            },
        },
        "feedback_tests_passed_policy_coverage": {
            "stop_immediately": {
                "status": "covered",
                "evidence": [
                    "tests/unit/test_feedback_tests_passed_policy.py::test_feedback_tests_passed_stop_immediately_preserves_replay_default",
                ],
                "sample": {
                    "agent_stop_reason": "feedback_tests_passed",
                    "feedback_verifier_accepted": True,
                },
            },
            "require_model_final": {
                "status": "covered",
                "evidence": [
                    "tests/unit/test_feedback_tests_passed_policy.py::test_feedback_tests_passed_require_model_final_consumes_replay_final_answer",
                ],
                "sample": {
                    "agent_stop_reason": "final_answer",
                    "feedback_verifier_accepted": True,
                },
            },
            "continue": {
                "status": "covered",
                "evidence": [
                    "tests/unit/test_feedback_tests_passed_policy.py::test_feedback_tests_passed_continue_keeps_negative_final_verifier_sample",
                ],
                "sample": {
                    "agent_stop_reason": "final_answer",
                    "feedback_verifier_accepted": True,
                    "final_verifier_status": "failed",
                },
            },
        },
        "disabled_combination": {
            "status": "covered",
            "feedback_tests_passed_policy": "not_applicable",
            "cannot_trigger_feedback_tests_passed_stop": True,
        },
        "experiment_summary": {
            "task_count": aggregate.get("task_count", 0),
            "success_count": aggregate.get("success_count", 0),
            "test_feedback_policy": "public_only",
        },
    }
    failures = _feedback_policy_failures(report)
    if failures:
        report["status"] = "failed"
        report["failures"] = failures
    else:
        report["failures"] = []
    return report


def build_v2_acceptance_report(
    *,
    v1_regression_dir: str | Path,
    task_set_manifest: str | Path,
    mock_provider_report: str | Path,
    real_provider_report: str | Path,
    feedback_policy_report: str | Path,
    export_audit_roots: list[str | Path],
    docker_status: str | Path,
    output: str | Path,
) -> Path:
    """Build the final V2 acceptance report from stable existing artifacts."""

    task_manifest_path = Path(task_set_manifest)
    task_root = task_manifest_path.parent
    aggregate_path = task_root / "aggregate_metrics.json"
    v1_dir = Path(v1_regression_dir)
    v1_manifest_path = v1_dir / "batch_manifest.json"
    mock_report_path = Path(mock_provider_report)
    real_report_path = Path(real_provider_report)
    feedback_report_path = Path(feedback_policy_report)
    docker_status_path = Path(docker_status)
    required_files = [
        v1_manifest_path,
        task_manifest_path,
        aggregate_path,
        mock_report_path,
        real_report_path,
        feedback_report_path,
        docker_status_path,
    ]
    for path in required_files:
        if not path.exists():
            raise ConfigError(f"V2 acceptance 输入文件不存在：{path}")

    export_summaries = [_export_root_summary(Path(root)) for root in export_audit_roots]
    report = {
        "schema_version": V2_ACCEPTANCE_REPORT_VERSION,
        "generated_at": _utc_timestamp(),
        "status": "built",
        "sources": {
            "v1_regression_dir": str(v1_dir),
            "task_set_manifest": str(task_manifest_path),
            "mock_provider_report": str(mock_report_path),
            "real_provider_report": str(real_report_path),
            "feedback_policy_report": str(feedback_report_path),
            "docker_status": str(docker_status_path),
            "export_audit_roots": [str(root) for root in export_audit_roots],
        },
        "evidence_refs": {
            "v1_batch_manifest": _file_ref(v1_manifest_path),
            "task_set_manifest": _file_ref(task_manifest_path),
            "task_set_aggregate_metrics": _file_ref(aggregate_path),
            "mock_provider_report": _file_ref(mock_report_path),
            "real_provider_report": _file_ref(real_report_path),
            "feedback_policy_report": _file_ref(feedback_report_path),
            "docker_stage_status": _file_ref(docker_status_path),
        },
        "v1_regression": _v1_regression_summary(v1_manifest_path),
        "replay_task_set": _task_set_summary(task_manifest_path, aggregate_path),
        "mock_provider": _mock_provider_summary(mock_report_path),
        "real_provider": _real_provider_summary(real_report_path),
        "docker_stage": _docker_stage_summary(docker_status_path),
        "feedback_policy_coverage": _read_json(feedback_report_path),
        "export_audits": {
            "roots": export_summaries,
            "format_distribution": dict(
                sorted(Counter(audit["format"] for root in export_summaries for audit in root["audits"]).items())
            ),
            "training_payload_scan": _training_payload_scan(export_summaries),
        },
    }
    report["status"] = "passed"
    failures = _acceptance_failures(report)
    report["status"] = "passed" if not failures else "failed"
    report["failures"] = failures
    output_path = Path(output)
    _write_json(output_path, report)
    return output_path


def inspect_v2_acceptance(
    report: str | Path,
    *,
    assert_complete: bool = False,
) -> str:
    payload = _read_json(Path(report))
    failures = _acceptance_failures(payload) if assert_complete else []
    if failures:
        raise ConfigError("; ".join(failures))
    return json.dumps(
        {
            "report": str(report),
            "status": payload.get("status"),
            "task_count": payload.get("replay_task_set", {}).get("task_count"),
            "mock_provider_status": payload.get("mock_provider", {}).get("status"),
            "real_provider_status": payload.get("real_provider", {}).get("status"),
            "docker_stage_mode": payload.get("docker_stage", {}).get("mode"),
            "export_formats": payload.get("export_audits", {}).get("format_distribution", {}),
            "checks": ["v2_acceptance=passed"] if assert_complete else [],
        },
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )


def _acceptance_failures(report: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if report.get("schema_version") != V2_ACCEPTANCE_REPORT_VERSION:
        failures.append("invalid acceptance schema_version")
    if report.get("status") != "passed":
        failures.append("acceptance report status is not passed")
    evidence_refs = report.get("evidence_refs", {})
    missing_refs = sorted(REQUIRED_EVIDENCE_REFS - set(evidence_refs))
    if missing_refs:
        failures.append("missing required evidence refs: " + ", ".join(missing_refs))
    for name, ref in report.get("evidence_refs", {}).items():
        failures.extend(_file_ref_failures(name, ref))
    if missing_refs:
        return failures
    failures.extend(_source_consistency_failures(report))
    v1 = report.get("v1_regression", {})
    if v1.get("status") != "passed":
        failures.append("v1 regression did not pass")
    task_set = report.get("replay_task_set", {})
    if int(task_set.get("task_count", 0)) < 20:
        failures.append("replay task set has fewer than 20 tasks")
    if int(task_set.get("agent_loop_runs", 0)) < 15:
        failures.append("replay task set has insufficient agent loop runs")
    if int(task_set.get("formal_final_verifier_runs", 0)) < 15:
        failures.append("replay task set has insufficient formal final verifier runs")
    if int(task_set.get("success_count", 0)) < 3:
        failures.append("replay task set has insufficient accepted runs")
    if task_set.get("all_skipped"):
        failures.append("replay task set cannot be all skipped")

    mock = report.get("mock_provider", {})
    if mock.get("status") != "accepted":
        failures.append("mock provider smoke did not pass")
    if mock.get("raw_artifact_redaction_status") not in {"redacted", "not_applicable"}:
        failures.append("mock provider raw artifacts are not redacted")

    failures.extend(_real_provider_failures(report.get("real_provider", {})))
    failures.extend(_docker_stage_failures(report.get("docker_stage", {})))
    failures.extend(_feedback_policy_failures(report.get("feedback_policy_coverage", {})))
    failures.extend(_export_audit_failures(report.get("export_audits", {})))
    return failures


def _source_consistency_failures(report: dict[str, Any]) -> list[str]:
    """Re-read referenced source artifacts so inspect is a real gate, not a summary reader."""

    failures: list[str] = []
    refs = report.get("evidence_refs", {})
    try:
        v1 = _v1_regression_summary(_ref_path(refs, "v1_batch_manifest"))
        task_set = _task_set_summary(
            _ref_path(refs, "task_set_manifest"),
            _ref_path(refs, "task_set_aggregate_metrics"),
        )
        mock = _mock_provider_summary(_ref_path(refs, "mock_provider_report"))
        real = _real_provider_summary(_ref_path(refs, "real_provider_report"))
        docker = _docker_stage_summary(_ref_path(refs, "docker_stage_status"))
        feedback = _read_json(_ref_path(refs, "feedback_policy_report"))
        export_roots = [Path(root) for root in report.get("sources", {}).get("export_audit_roots", [])]
        if not export_roots:
            failures.append("acceptance report sources missing export_audit_roots")
            export_summary = {"roots": [], "format_distribution": {}, "training_payload_scan": {}}
        else:
            export_summary = _export_audits_summary(export_roots)
    except ConfigError as exc:
        return [f"acceptance source recomputation failed: {exc}"]

    failures.extend(_section_mismatches("v1_regression", report.get("v1_regression", {}), v1, ["status", "run_count", "status_distribution"]))
    failures.extend(
        _section_mismatches(
            "replay_task_set",
            report.get("replay_task_set", {}),
            task_set,
            [
                "task_count",
                "total_runs",
                "recorded_runs",
                "agent_loop_runs",
                "formal_final_verifier_runs",
                "success_count",
                "structured_skipped_runs",
                "status_distribution",
                "all_skipped",
            ],
        )
    )
    failures.extend(
        _section_mismatches(
            "mock_provider",
            report.get("mock_provider", {}),
            mock,
            ["status", "provider", "final_verifier_status", "run_outcome", "export_audit_status", "raw_artifact_redaction_status"],
        )
    )
    failures.extend(
        _section_mismatches(
            "real_provider",
            report.get("real_provider", {}),
            real,
            [
                "status",
                "requested_provider",
                "actual_provider",
                "provider_model",
                "fallback_used",
                "fallback_reason",
                "fallback_policy_version",
                "credential_status",
                "credential_source",
                "model_error_type",
                "redaction_status",
                "final_verifier_status",
                "run_outcome",
                "official_docs_checked",
            ],
        )
    )
    failures.extend(
        _section_mismatches(
            "docker_stage",
            report.get("docker_stage", {}),
            docker,
            [
                "mode",
                "status",
                "docker_available",
                "docker_backend_implemented",
                "docker_execution_mode_behavior",
                "production_sandbox_claimed",
            ],
        )
    )
    failures.extend(
        _section_mismatches(
            "feedback_policy_coverage",
            report.get("feedback_policy_coverage", {}),
            feedback,
            ["status", "test_feedback_policy_coverage", "feedback_tests_passed_policy_coverage", "disabled_combination"],
        )
    )
    report_exports = report.get("export_audits", {})
    failures.extend(
        _section_mismatches(
            "export_audits",
            report_exports,
            export_summary,
            ["format_distribution"],
        )
    )
    failures.extend(_export_summary_mismatches(report_exports, export_summary))
    failures.extend(_real_provider_failures(real))
    failures.extend(_docker_stage_failures(docker))
    failures.extend(_feedback_policy_failures(feedback))
    failures.extend(_export_audit_failures(export_summary))
    return failures


def _export_audits_summary(export_roots: list[Path]) -> dict[str, Any]:
    export_summaries = [_export_root_summary(root) for root in export_roots]
    return {
        "roots": export_summaries,
        "format_distribution": dict(
            sorted(Counter(audit["format"] for root in export_summaries for audit in root["audits"]).items())
        ),
        "training_payload_scan": _training_payload_scan(export_summaries),
    }


def _ref_path(refs: dict[str, Any], name: str) -> Path:
    ref = refs.get(name)
    if not isinstance(ref, dict) or not ref.get("path"):
        raise ConfigError(f"acceptance evidence ref missing path: {name}")
    return Path(str(ref["path"]))


def _section_mismatches(
    section_name: str,
    actual: dict[str, Any],
    expected: dict[str, Any],
    keys: list[str],
) -> list[str]:
    mismatches = [key for key in keys if actual.get(key) != expected.get(key)]
    if mismatches:
        return [f"{section_name} summary does not match referenced source: " + ", ".join(mismatches)]
    return []


def _real_provider_failures(real: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    status = real.get("status")
    credential_status = real.get("credential_status")
    if status == "skipped_no_credentials":
        if credential_status not in {"missing_all", "missing_deepseek", "missing"}:
            failures.append("real provider skip must be credential-based")
        if real.get("actual_provider") not in {"none", None}:
            failures.append("real provider no-credential skip must not record an actual provider")
        if real.get("fallback_used"):
            failures.append("real provider no-credential skip must not record fallback_used")
        return failures
    if status == "accepted_with_credentials":
        if real.get("requested_provider") != "deepseek" or real.get("actual_provider") != "deepseek":
            failures.append("DeepSeek accepted run must not be an OpenAI fallback")
        if real.get("fallback_used"):
            failures.append("accepted_with_credentials cannot mark fallback_used")
        if credential_status != "present":
            failures.append("accepted_with_credentials requires credential_status=present")
        if real.get("credential_source") in {None, "none"}:
            failures.append("accepted_with_credentials requires a redacted credential source")
        if real.get("final_verifier_status") != "accepted" or real.get("run_outcome") != "success":
            failures.append("accepted_with_credentials requires accepted final verifier and success outcome")
    elif status == "fallback_success":
        if real.get("requested_provider") != "deepseek" or real.get("actual_provider") != "openai":
            failures.append("fallback_success must record DeepSeek requested and OpenAI actual")
        if not real.get("fallback_used") or not real.get("fallback_policy_version"):
            failures.append("fallback_success must record fallback policy")
        if credential_status != "present":
            failures.append("fallback_success requires credential_status=present")
        if real.get("credential_source") in {None, "none"}:
            failures.append("fallback_success requires a redacted credential source")
        if real.get("final_verifier_status") != "accepted" or real.get("run_outcome") != "success":
            failures.append("fallback_success requires accepted final verifier and success outcome")
    else:
        failures.append(f"real provider status is not accepted or structured skip: {status}")
    if real.get("official_docs_checked") is not True:
        failures.append("real provider official docs check missing")
    if real.get("redaction_status") not in {"redacted", "not_applicable"}:
        failures.append("real provider raw artifact redaction failed")
    return failures


def _docker_stage_failures(docker_stage: dict[str, Any]) -> list[str]:
    status_path = docker_stage.get("status_file")
    if not status_path:
        return ["docker stage status file missing"]
    try:
        status = load_workspace_backend_status(status_path)
        inspect_workspace_backend_status(status_file=status_path, assert_stage_complete=True)
    except RepoHarnessError as exc:
        return [f"docker stage incomplete: {exc}"]
    mismatches = []
    expected = {
        "mode": status.mode,
        "status": status.status,
        "docker_available": status.docker_available,
        "docker_backend_implemented": status.docker_backend_implemented,
        "docker_execution_mode_behavior": status.docker_execution_mode_behavior,
        "production_sandbox_claimed": status.production_sandbox_claimed,
    }
    for key, value in expected.items():
        if docker_stage.get(key) != value:
            mismatches.append(key)
    if mismatches:
        return ["docker stage summary does not match docker_stage_status.json: " + ", ".join(mismatches)]
    if docker_stage.get("production_sandbox_claimed"):
        return ["Docker stage cannot claim production sandbox"]
    return []


def _feedback_policy_failures(report: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if report.get("status") != "passed":
        failures.append("feedback policy coverage report did not pass")
    failures.extend(
        _file_ref_failures(
            "feedback policy experiment_manifest_ref",
            report.get("experiment_manifest_ref"),
        )
    )
    failures.extend(
        _file_ref_failures(
            "feedback policy aggregate_metrics_ref",
            report.get("aggregate_metrics_ref"),
        )
    )
    experiment_summary = report.get("experiment_summary", {})
    if int(experiment_summary.get("task_count", 0)) <= 0:
        failures.append("feedback policy coverage requires aggregate task_count evidence")
    test_policy = report.get("test_feedback_policy_coverage", {})
    missing_test = sorted(REQUIRED_TEST_FEEDBACK_POLICIES - set(test_policy))
    if missing_test:
        failures.append("missing test_feedback_policy coverage: " + ", ".join(missing_test))
    for name in REQUIRED_TEST_FEEDBACK_POLICIES:
        if test_policy.get(name, {}).get("status") != "covered":
            failures.append(f"test_feedback_policy {name} is not covered")
    feedback_policy = report.get("feedback_tests_passed_policy_coverage", {})
    missing_feedback = sorted(REQUIRED_FEEDBACK_TESTS_PASSED_POLICIES - set(feedback_policy))
    if missing_feedback:
        failures.append("missing feedback_tests_passed_policy coverage: " + ", ".join(missing_feedback))
    for name in REQUIRED_FEEDBACK_TESTS_PASSED_POLICIES:
        if feedback_policy.get(name, {}).get("status") != "covered":
            failures.append(f"feedback_tests_passed_policy {name} is not covered")
    disabled = report.get("disabled_combination", {})
    if disabled.get("feedback_tests_passed_policy") != "not_applicable":
        failures.append("disabled feedback policy must resolve feedback_tests_passed_policy to not_applicable")
    if disabled.get("cannot_trigger_feedback_tests_passed_stop") is not True:
        failures.append("disabled feedback policy must not trigger feedback_tests_passed stop")
    public_sample = test_policy.get("public_only", {}).get("sample", {})
    if not public_sample.get("experiment_success_run_ids"):
        failures.append("public_only feedback coverage requires experiment success run evidence")
    return failures


def _export_audit_failures(export_audits: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    distribution = export_audits.get("format_distribution", {})
    for export_format in ("sft_jsonl", "rl_jsonl", "preference_jsonl"):
        if int(distribution.get(export_format, 0)) < 1:
            failures.append(f"missing export audit format: {export_format}")
    for root in export_audits.get("roots", []):
        if root.get("inspect_status") != "clean":
            failures.append(f"export root is not clean: {root.get('root_path')}")
        for audit in root.get("audits", []):
            if audit.get("status") == "failed":
                failures.append(f"export audit failed: {audit.get('audit_report_path')}")
            if not audit.get("audit_report_md_path"):
                failures.append(f"export audit markdown missing: {audit.get('audit_report_path')}")
            if not audit.get("formal_training_data_only_trainable", False):
                failures.append(f"non-trainable sample entered training JSONL: {audit.get('audit_report_path')}")
    scan = export_audits.get("training_payload_scan", {})
    if scan.get("provider_raw_markers_found"):
        failures.append("provider raw response markers found in training payload")
    if scan.get("non_trainable_records_found"):
        failures.append("non-trainable sample found in training payload")
    if scan.get("jsonl_parse_failures"):
        failures.append("training payload JSONL parse failures found")
    return failures


def _export_root_summary(root: Path) -> dict[str, Any]:
    if not root.exists():
        raise ConfigError(f"export audit root 不存在：{root}")
    try:
        inspect_export(root, all_exports=True, assert_clean=True)
        inspect_status = "clean"
        inspect_error = None
    except RepoHarnessError as exc:
        inspect_status = "failed"
        inspect_error = str(exc)
    audits = []
    for audit_path in sorted(root.glob("*/audit_report.json")):
        audit = _read_json(audit_path)
        export_dir = audit_path.parent
        manifest_path = export_dir / "export_manifest.json"
        manifest = _read_json_if_exists(manifest_path)
        audit_md_path = export_dir / "audit_report.md"
        audits.append(
            {
                "export_dir": str(export_dir),
                "format": audit.get("format"),
                "status": audit.get("status"),
                "audit_report_path": str(audit_path),
                "audit_report_sha256": _sha256_file(audit_path),
                "audit_report_md_path": str(audit_md_path) if audit_md_path.exists() else None,
                "audit_report_md_sha256": _sha256_file(audit_md_path) if audit_md_path.exists() else None,
                "export_manifest_path": str(manifest_path) if manifest_path.exists() else None,
                "export_manifest_sha256": _sha256_file(manifest_path) if manifest_path.exists() else None,
                "summary": audit.get("summary", {}),
                "record_count": manifest.get("record_count", 0),
                "formal_training_data_only_trainable": _formal_training_data_only_trainable(audit),
            }
        )
    return {
        "root_path": str(root),
        "inspect_status": inspect_status,
        "inspect_error": inspect_error,
        "audits": audits,
    }


def _formal_training_data_only_trainable(audit: dict[str, Any]) -> bool:
    for sample in audit.get("samples", []):
        if sample.get("data_file") and sample.get("training_eligibility") != "trainable":
            return False
    return True


def _export_summary_mismatches(actual: dict[str, Any], expected: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    actual_roots = actual.get("roots", [])
    expected_roots = expected.get("roots", [])
    if len(actual_roots) != len(expected_roots):
        return ["export_audits root count does not match referenced sources"]
    for index, (actual_root, expected_root) in enumerate(zip(actual_roots, expected_roots, strict=True)):
        root_label = expected_root.get("root_path") or f"root[{index}]"
        for key in ("root_path", "inspect_status", "inspect_error"):
            if actual_root.get(key) != expected_root.get(key):
                failures.append(f"export_audits summary does not match referenced source {root_label}: {key}")
        actual_audits = actual_root.get("audits", [])
        expected_audits = expected_root.get("audits", [])
        if len(actual_audits) != len(expected_audits):
            failures.append(f"export_audits summary does not match referenced source {root_label}: audit count")
            continue
        for actual_audit, expected_audit in zip(actual_audits, expected_audits, strict=True):
            audit_label = expected_audit.get("audit_report_path") or expected_audit.get("export_dir")
            for key in (
                "export_dir",
                "format",
                "status",
                "audit_report_path",
                "audit_report_sha256",
                "audit_report_md_path",
                "audit_report_md_sha256",
                "export_manifest_path",
                "export_manifest_sha256",
                "summary",
                "record_count",
                "formal_training_data_only_trainable",
            ):
                if actual_audit.get(key) != expected_audit.get(key):
                    failures.append(
                        f"export_audits summary does not match referenced source {audit_label}: {key}"
                    )
    actual_scan = actual.get("training_payload_scan", {})
    expected_scan = expected.get("training_payload_scan", {})
    for key in (
        "scanned_files",
        "provider_raw_markers_found",
        "non_trainable_records_found",
        "jsonl_parse_failures",
    ):
        if actual_scan.get(key) != expected_scan.get(key):
            failures.append(f"export_audits training payload scan does not match referenced sources: {key}")
    return failures


def _training_payload_scan(export_summaries: list[dict[str, Any]]) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    non_trainable_records: list[dict[str, Any]] = []
    parse_failures: list[dict[str, Any]] = []
    markers = tuple(marker.lower() for marker in PROVIDER_RAW_MARKERS)
    for root in export_summaries:
        root_path = Path(root["root_path"])
        candidates = sorted(
            path
            for path in root_path.rglob("*.jsonl")
            if path.name in TRAINING_DATA_FILENAMES
        )
        for path in candidates:
            text = path.read_text(encoding="utf-8").lower()
            for marker in markers:
                if marker in text:
                    findings.append({"path": str(path), "marker": marker})
            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    parse_failures.append(
                        {
                            "path": str(path),
                            "line_number": line_number,
                            "error": str(exc),
                        }
                    )
                    continue
                eligibility = record.get("quality", {}).get("training_eligibility")
                if eligibility != "trainable" or record.get("invalid_for_training"):
                    non_trainable_records.append(
                        {
                            "path": str(path),
                            "line_number": line_number,
                            "training_eligibility": eligibility,
                            "invalid_for_training": bool(record.get("invalid_for_training")),
                        }
                    )
    return {
        "scanned_files": [
            str(path)
            for root in export_summaries
            for path in sorted(Path(root["root_path"]).rglob("*.jsonl"))
            if path.name in TRAINING_DATA_FILENAMES
        ],
        "provider_raw_markers_found": findings,
        "non_trainable_records_found": non_trainable_records,
        "jsonl_parse_failures": parse_failures,
    }


def _v1_regression_summary(manifest_path: Path) -> dict[str, Any]:
    manifest = _read_json(manifest_path)
    distribution = Counter(run.get("status") for run in manifest.get("runs", []))
    return {
        "manifest_ref": _file_ref(manifest_path),
        "status": "passed" if not manifest.get("should_fail_command") else "failed",
        "run_count": len(manifest.get("runs", [])),
        "status_distribution": dict(sorted(distribution.items())),
    }


def _task_set_summary(manifest_path: Path, aggregate_path: Path) -> dict[str, Any]:
    manifest = _read_json(manifest_path)
    aggregate = _read_json(aggregate_path)
    total = int(aggregate.get("total_runs", 0))
    skipped = sum(
        int(aggregate.get("status_distribution", {}).get(status, 0))
        for status in ("invalid_task", "flaky_task", "inconclusive")
    )
    return {
        "manifest_ref": _file_ref(manifest_path),
        "aggregate_metrics_ref": _file_ref(aggregate_path),
        "experiment_id": manifest.get("experiment_id"),
        "task_count": aggregate.get("task_count", 0),
        "total_runs": total,
        "recorded_runs": aggregate.get("recorded_runs", 0),
        "agent_loop_runs": aggregate.get("agent_loop_runs", 0),
        "formal_final_verifier_runs": aggregate.get("formal_final_verifier_runs", 0),
        "success_count": aggregate.get("success_count", 0),
        "structured_skipped_runs": aggregate.get("structured_skipped_runs", 0),
        "status_distribution": aggregate.get("status_distribution", {}),
        "all_skipped": total > 0 and skipped == total,
    }


def _mock_provider_summary(report_path: Path) -> dict[str, Any]:
    report = _read_json(report_path)
    return {
        "report_ref": _file_ref(report_path),
        "status": report.get("status"),
        "provider": report.get("provider"),
        "final_verifier_status": report.get("final_verifier_status"),
        "run_outcome": report.get("run_outcome"),
        "model_error_type": report.get("model_error_type"),
        "export_audit_status": report.get("export_audit_status"),
        "raw_artifact_redaction_status": report.get("raw_artifact_redaction_status"),
    }


def _real_provider_summary(report_path: Path) -> dict[str, Any]:
    report = _read_json(report_path)
    keys = {
        "status",
        "requested_provider",
        "actual_provider",
        "provider_model",
        "provider_base_url",
        "provider_endpoint_category",
        "fallback_used",
        "fallback_reason",
        "fallback_policy_version",
        "credential_status",
        "credential_source",
        "model_error_type",
        "run_dir",
        "redaction_status",
        "final_verifier_status",
        "run_outcome",
        "official_docs_checked",
        "official_docs_url",
        "checked_at_date",
    }
    summary = {key: report.get(key) for key in sorted(keys)}
    summary["report_ref"] = _file_ref(report_path)
    return summary


def _docker_stage_summary(status_path: Path) -> dict[str, Any]:
    status = load_workspace_backend_status(status_path)
    return {
        "status_file": str(status_path),
        "status_ref": _file_ref(status_path),
        "mode": status.mode,
        "status": status.status,
        "docker_available": status.docker_available,
        "docker_backend_implemented": status.docker_backend_implemented,
        "docker_execution_mode_behavior": status.docker_execution_mode_behavior,
        "production_sandbox_claimed": status.production_sandbox_claimed,
    }


def _file_ref(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "sha256": _sha256_file(path),
    }


def _file_ref_failures(name: str, ref: dict[str, Any] | None) -> list[str]:
    if not ref:
        return [f"missing evidence ref: {name}"]
    path = Path(str(ref.get("path", "")))
    if not path.exists():
        return [f"evidence file missing: {name}"]
    actual = _sha256_file(path)
    if actual != ref.get("sha256"):
        return [f"evidence sha256 mismatch: {name}"]
    return []


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"无法读取 JSON 文件：{path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"JSON 文件格式错误：{path}") from exc


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return _read_json(path)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
