"""Stage 16F.5 entrypoint policy reports and inspection."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from repo_harness.errors import ConfigError
from repo_harness.schema_base import stable_hash


LEGACY_ENTRYPOINT_REPORT = "legacy_entrypoint_report.json"
CANONICAL_ENTRYPOINT_REPORT = "entrypoint_report.json"
LEGACY_SCHEMA_VERSION = "repo_harness_stage16f5_legacy_entrypoint_report_v0"
CANONICAL_SCHEMA_VERSION = "repo_harness_stage16f5_entrypoint_report_v0"

_FORBIDDEN_PUBLIC_MARKERS = (
    "/Users/roger",
    "/private",
    "/workspace",
    "/testbed",
    "/root/",
    "/home/",
    "/tmp/",
    "runtime_private/",
    ".repo_harness_runtime",
    ".repo_harness_env_overlay",
    "hidden_verifier",
    "gold_patch",
    "test_patch",
    "provider_secret",
)


class Stage16F5EntrypointPolicyError(ConfigError):
    """Raised when Stage 16F.5 entrypoint policy evidence is invalid."""


def legacy_entrypoint_report_payload(
    *,
    run_id: str,
    task_id: str,
    caller: str = "run_task",
) -> dict[str, Any]:
    """Build the public-safe legacy entrypoint report for ``run_task`` outputs."""

    return {
        "schema_version": LEGACY_SCHEMA_VERSION,
        "run_id": run_id,
        "task_id": task_id,
        "entrypoint": "run_task",
        "entrypoint_caller": caller,
        "entrypoint_classification": "legacy_compatibility",
        "canonical_entrypoint": "run_episode_task",
        "recommended_replacement": "repo-harness run-episode-task",
        "legacy_run_task_still_supported": True,
        "legacy_run_task_internal_run_episode_delegate": False,
        "formal_online_rl_eligible": False,
        "policy_loss_candidate": False,
        "formal_training_data_candidate": False,
        "new_training_data_default_candidate": False,
        "new_training_data_default_entrypoint": False,
        "training_data_eligibility_asserted": False,
        "historical_export_compatibility_allowed": True,
        "compatibility_use_cases": [
            "historical_acceptance",
            "legacy_export",
            "regression_comparison",
            "rollback_path",
        ],
    }


def write_legacy_entrypoint_report(
    run_dir: str | Path,
    *,
    run_id: str,
    task_id: str,
    caller: str = "run_task",
) -> dict[str, Any]:
    """Write ``legacy_entrypoint_report.json`` into a legacy run directory."""

    payload = legacy_entrypoint_report_payload(run_id=run_id, task_id=task_id, caller=caller)
    _write_json(Path(run_dir) / LEGACY_ENTRYPOINT_REPORT, payload)
    return payload


def canonical_entrypoint_report_payload(
    *,
    run_id: str,
    task_id: str,
    episode_execution_spec_sha256: str,
    compat_projection_complete: bool,
    provider_route: str | None,
    formal_online_rl_eligible: bool,
    policy_loss_candidate: bool,
) -> dict[str, Any]:
    """Build the public-safe canonical entrypoint report for ``run-episode-task``."""

    return {
        "schema_version": CANONICAL_SCHEMA_VERSION,
        "run_id": run_id,
        "task_id": task_id,
        "entrypoint": "run_episode_task",
        "entrypoint_classification": "canonical_run_episode_task",
        "canonical_entrypoint": "run_episode_task",
        "episode_execution_spec_sha256": episode_execution_spec_sha256,
        "compat_projection_complete": bool(compat_projection_complete),
        "provider_route": provider_route,
        "formal_online_rl_eligible": bool(formal_online_rl_eligible),
        "policy_loss_candidate": bool(policy_loss_candidate),
        # This field only means "default entrypoint for future training data
        # preparation"; it is not a trainability assertion.
        "new_training_data_default_entrypoint": True,
        "training_data_eligibility_asserted": False,
    }


def write_canonical_entrypoint_report(
    run_dir: str | Path,
    *,
    run_id: str,
    task_id: str,
    episode_execution_spec_sha256: str,
    compat_projection_complete: bool,
    provider_route: str | None,
    formal_online_rl_eligible: bool,
    policy_loss_candidate: bool,
) -> dict[str, Any]:
    """Write ``entrypoint_report.json`` into a canonical run directory."""

    payload = canonical_entrypoint_report_payload(
        run_id=run_id,
        task_id=task_id,
        episode_execution_spec_sha256=episode_execution_spec_sha256,
        compat_projection_complete=compat_projection_complete,
        provider_route=provider_route,
        formal_online_rl_eligible=formal_online_rl_eligible,
        policy_loss_candidate=policy_loss_candidate,
    )
    _write_json(Path(run_dir) / CANONICAL_ENTRYPOINT_REPORT, payload)
    return payload


def inspect_stage16f5_entrypoint_policy(
    evidence: str | Path,
    *,
    assert_complete: bool = False,
) -> str:
    """Inspect Stage 16F.5 legacy/canonical entrypoint policy evidence."""

    root = Path(evidence)
    if not root.exists():
        raise Stage16F5EntrypointPolicyError(f"evidence path does not exist: {root}")
    report_path = root / "stage16f5_entrypoint_policy_report.json"
    if report_path.exists():
        report = _load_public_evidence_report(root, report_path)
    else:
        report = build_stage16f5_entrypoint_policy_report(root)
        if assert_complete:
            complete_errors = _stage16f5_complete_errors(report)
            if complete_errors:
                report = dict(report)
                report["errors"] = sorted(set([*report.get("errors", []), *complete_errors]))
                report["passed"] = False
    if assert_complete and not report["passed"]:
        raise Stage16F5EntrypointPolicyError("; ".join(report["errors"]))
    return json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False)


def build_stage16f5_entrypoint_policy_report(root: str | Path) -> dict[str, Any]:
    """Build a machine-checkable report from run directories or public evidence."""

    base = Path(root)
    legacy_reports = _load_reports(base, LEGACY_ENTRYPOINT_REPORT)
    canonical_reports = _load_reports(base, CANONICAL_ENTRYPOINT_REPORT)
    errors: list[str] = []

    for record in legacy_reports:
        _validate_legacy_report(record["payload"], record["relative_path"], errors)
    for record in canonical_reports:
        _validate_canonical_report(record["payload"], record["relative_path"], errors)

    batch_manifest_checks = _check_legacy_child_manifests(
        base,
        manifest_filename="batch_manifest.json",
        manifest_kind="run_batch",
        errors=errors,
    )
    experiment_manifest_checks = _check_legacy_child_manifests(
        base,
        manifest_filename="experiment_manifest.json",
        manifest_kind="run_experiment",
        errors=errors,
    )
    if not batch_manifest_checks["observed"]:
        batch_manifest_checks["status"] = "not_observed"
    if not experiment_manifest_checks["observed"]:
        experiment_manifest_checks["status"] = "not_observed"

    public_leaks = []
    for record in [*legacy_reports, *canonical_reports]:
        public_leaks.extend(_public_leaks(record["payload"], record["relative_path"]))
    if public_leaks:
        errors.extend(public_leaks)

    legacy_payloads = [record["payload"] for record in legacy_reports]
    canonical_payloads = [record["payload"] for record in canonical_reports]
    summary = {
        "schema_version": "repo_harness_stage16f5_entrypoint_policy_report_v0",
        "evidence_root_label": "stage16f5_input_root",
        "evidence_root_name": base.name,
        "legacy_run_task_report_count": len(legacy_reports),
        "canonical_run_episode_task_report_count": len(canonical_reports),
        "legacy_formal_online_rl_eligible_count": _count_truthy(legacy_payloads, "formal_online_rl_eligible"),
        "legacy_policy_loss_candidate_count": _count_truthy(legacy_payloads, "policy_loss_candidate"),
        "legacy_new_training_data_default_candidate_count": _count_truthy(
            legacy_payloads,
            "new_training_data_default_candidate",
        ),
        "legacy_new_training_data_default_entrypoint_count": _count_truthy(
            legacy_payloads,
            "new_training_data_default_entrypoint",
        ),
        "legacy_formal_training_data_candidate_count": _count_truthy(
            legacy_payloads,
            "formal_training_data_candidate",
        ),
        "canonical_training_data_default_entrypoint_count": _count_truthy(
            canonical_payloads,
            "new_training_data_default_entrypoint",
        ),
        "canonical_training_data_eligibility_asserted_count": _count_truthy(
            canonical_payloads,
            "training_data_eligibility_asserted",
        ),
        "canonical_non_verl_policy_loss_candidate_count": sum(
            1
            for payload in canonical_payloads
            if payload.get("policy_loss_candidate") is True and payload.get("provider_route") != "verl"
        ),
        "batch_manifest_legacy_metadata_status": batch_manifest_checks["status"],
        "experiment_manifest_legacy_metadata_status": experiment_manifest_checks["status"],
        "batch_manifest_legacy_child_count": batch_manifest_checks["child_count"],
        "experiment_manifest_legacy_child_count": experiment_manifest_checks["child_count"],
        "run_episode_batch_status": "deferred_to_later_stage",
        "public_path_leak_scan_passed": not public_leaks,
        "report_records_digest": stable_hash(
            {
                "legacy": [record["payload"] for record in legacy_reports],
                "canonical": [record["payload"] for record in canonical_reports],
                "batch": batch_manifest_checks,
                "experiment": experiment_manifest_checks,
            }
        ),
    }

    if not legacy_reports:
        errors.append("missing_legacy_entrypoint_report")
    if not canonical_reports:
        errors.append("missing_canonical_entrypoint_report")
    if summary["legacy_formal_online_rl_eligible_count"] != 0:
        errors.append("legacy_formal_online_rl_eligible_count_nonzero")
    if summary["legacy_policy_loss_candidate_count"] != 0:
        errors.append("legacy_policy_loss_candidate_count_nonzero")
    if summary["legacy_new_training_data_default_candidate_count"] != 0:
        errors.append("legacy_new_training_data_default_candidate_count_nonzero")
    if summary["legacy_new_training_data_default_entrypoint_count"] != 0:
        errors.append("legacy_new_training_data_default_entrypoint_count_nonzero")
    if summary["legacy_formal_training_data_candidate_count"] != 0:
        errors.append("legacy_formal_training_data_candidate_count_nonzero")
    if summary["canonical_non_verl_policy_loss_candidate_count"] != 0:
        errors.append("canonical_non_verl_policy_loss_candidate_count_nonzero")
    summary["passed"] = not errors
    summary["errors"] = sorted(set(errors))
    return summary


def write_stage16f5_entrypoint_policy_evidence(
    *,
    source_root: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    """Write public-safe Stage 16F.5 evidence derived from run directories."""

    source = Path(source_root)
    report = build_stage16f5_entrypoint_policy_report(source)
    legacy_reports = [record["payload"] for record in _load_reports(source, LEGACY_ENTRYPOINT_REPORT)]
    canonical_reports = [record["payload"] for record in _load_reports(source, CANONICAL_ENTRYPOINT_REPORT)]
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    legacy_sample_report = {
        "schema_version": "repo_harness_stage16f5_legacy_run_task_sample_report_v0",
        "legacy_report_count": len(legacy_reports),
        "legacy_reports": sorted(legacy_reports, key=lambda item: str(item.get("run_id", ""))),
    }
    canonical_sample_report = {
        "schema_version": "repo_harness_stage16f5_run_episode_task_sample_report_v0",
        "canonical_report_count": len(canonical_reports),
        "canonical_reports": sorted(canonical_reports, key=lambda item: str(item.get("run_id", ""))),
    }
    test_report = {
        "schema_version": "repo_harness_stage16f5_test_report_v0",
        "focused_tests": "tests/unit/test_repo_harness_stage16f5_*.py",
        "batch_manifest_legacy_metadata_status": report["batch_manifest_legacy_metadata_status"],
        "experiment_manifest_legacy_metadata_status": report["experiment_manifest_legacy_metadata_status"],
        "batch_manifest_legacy_child_count": report["batch_manifest_legacy_child_count"],
        "experiment_manifest_legacy_child_count": report["experiment_manifest_legacy_child_count"],
        "run_episode_batch_status": report["run_episode_batch_status"],
        "verification_note": "Generated from local Stage 16F.5 smoke runs; detailed command output is kept outside public evidence.",
    }
    _write_json(output / "stage16f5_entrypoint_policy_report.json", report)
    _write_json(output / "stage16f5_legacy_run_task_sample_report.json", legacy_sample_report)
    _write_json(output / "stage16f5_run_episode_task_sample_report.json", canonical_sample_report)
    _write_json(output / "stage16f5_test_report.json", test_report)
    summary = {
        "schema_version": "repo_harness_stage16f5_acceptance_summary_v0",
        "status": "passed" if report["passed"] else "failed",
        "stage16f5_complete": bool(report["passed"]),
        "ready_for_stage16_5": bool(report["passed"]),
        "stage16f4_input_status": "passed",
        "legacy_run_task_still_supported": True,
        "legacy_run_task_internal_run_episode_delegate": False,
        "legacy_run_task_training_candidate_blocked": (
            report["legacy_formal_online_rl_eligible_count"] == 0
            and report["legacy_policy_loss_candidate_count"] == 0
            and report["legacy_formal_training_data_candidate_count"] == 0
        ),
        "canonical_run_episode_task_default_for_new_evaluation": True,
        "run_episode_task_projection_binding_required": True,
        "historical_export_compatibility_preserved": True,
        "run_batch_legacy_metadata_inherited": (
            report["batch_manifest_legacy_metadata_status"] == "passed"
        ),
        "run_experiment_legacy_metadata_status": (
            "covered" if report["experiment_manifest_legacy_metadata_status"] == "passed" else "failed"
        ),
        **{
            key: report[key]
            for key in (
                "legacy_run_task_report_count",
                "canonical_run_episode_task_report_count",
                "legacy_formal_online_rl_eligible_count",
                "legacy_policy_loss_candidate_count",
                "legacy_new_training_data_default_candidate_count",
                "legacy_new_training_data_default_entrypoint_count",
                "legacy_formal_training_data_candidate_count",
                "canonical_training_data_default_entrypoint_count",
                "canonical_non_verl_policy_loss_candidate_count",
                "batch_manifest_legacy_metadata_status",
                "experiment_manifest_legacy_metadata_status",
                "run_episode_batch_status",
                "public_path_leak_scan_passed",
            )
        },
        "errors": report["errors"],
        "blocking_reason_count": len(report["errors"]),
        "entrypoint_policy_report_sha256": stable_hash(report),
        "legacy_run_task_sample_report_sha256": stable_hash(legacy_sample_report),
        "run_episode_task_sample_report_sha256": stable_hash(canonical_sample_report),
        "test_report_sha256": stable_hash(test_report),
    }
    _write_json(output / "stage16f5_acceptance_summary.json", summary)
    return summary


def _load_public_evidence_report(root: Path, report_path: Path) -> dict[str, Any]:
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {
            "schema_version": "repo_harness_stage16f5_entrypoint_policy_report_v0",
            "passed": False,
            "errors": [f"stage16f5_entrypoint_policy_report_json_invalid:{exc}"],
        }
    if not isinstance(report, dict):
        return {
            "schema_version": "repo_harness_stage16f5_entrypoint_policy_report_v0",
            "passed": False,
            "errors": ["stage16f5_entrypoint_policy_report_not_object"],
        }
    errors = _validate_public_evidence_report(root, report)
    merged_errors = sorted(set([*(report.get("errors") or []), *errors]))
    report = dict(report)
    report["errors"] = merged_errors
    report["passed"] = bool(report.get("passed")) and not merged_errors
    return report


def _validate_public_evidence_report(root: Path, report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected_zero_fields = (
        "legacy_formal_online_rl_eligible_count",
        "legacy_policy_loss_candidate_count",
        "legacy_new_training_data_default_candidate_count",
        "legacy_new_training_data_default_entrypoint_count",
        "legacy_formal_training_data_candidate_count",
        "canonical_non_verl_policy_loss_candidate_count",
    )
    required_truthy = (
        "public_path_leak_scan_passed",
    )
    if int(report.get("legacy_run_task_report_count", 0)) < 1:
        errors.append("legacy_run_task_report_count_too_low")
    if int(report.get("canonical_run_episode_task_report_count", 0)) < 1:
        errors.append("canonical_run_episode_task_report_count_too_low")
    for field in expected_zero_fields:
        if int(report.get(field, -1)) != 0:
            errors.append(f"summary_field_must_be_zero:{field}")
    for field in required_truthy:
        if report.get(field) is not True:
            errors.append(f"summary_field_must_be_true:{field}")
    errors.extend(_stage16f5_complete_errors(report))
    legacy_sample_path = root / "stage16f5_legacy_run_task_sample_report.json"
    canonical_sample_path = root / "stage16f5_run_episode_task_sample_report.json"
    test_report_path = root / "stage16f5_test_report.json"
    legacy_sample = _load_required_public_report(
        legacy_sample_path,
        "stage16f5_legacy_run_task_sample_report",
        errors,
    )
    canonical_sample = _load_required_public_report(
        canonical_sample_path,
        "stage16f5_run_episode_task_sample_report",
        errors,
    )
    test_report = _load_required_public_report(
        test_report_path,
        "stage16f5_test_report",
        errors,
    )
    if legacy_sample:
        legacy_reports = legacy_sample.get("legacy_reports")
        if not isinstance(legacy_reports, list) or not legacy_reports:
            errors.append("legacy_sample_report_missing_legacy_reports")
            legacy_reports = []
        for index, payload in enumerate(legacy_reports):
            if isinstance(payload, dict):
                _validate_legacy_report(payload, f"stage16f5_legacy_run_task_sample_report.json[{index}]", errors)
            else:
                errors.append(f"legacy_sample_report_entry_not_object:{index}")
        if int(report.get("legacy_run_task_report_count", -1)) != len(legacy_reports):
            errors.append("legacy_sample_report_count_mismatch")
        if report.get("legacy_formal_online_rl_eligible_count") != _count_truthy(legacy_reports, "formal_online_rl_eligible"):
            errors.append("legacy_sample_formal_online_rl_count_mismatch")
        if report.get("legacy_policy_loss_candidate_count") != _count_truthy(legacy_reports, "policy_loss_candidate"):
            errors.append("legacy_sample_policy_loss_count_mismatch")
        if report.get("legacy_formal_training_data_candidate_count") != _count_truthy(
            legacy_reports,
            "formal_training_data_candidate",
        ):
            errors.append("legacy_sample_formal_training_count_mismatch")
        errors.extend(_public_leaks(legacy_sample, "stage16f5_legacy_run_task_sample_report.json"))
    if canonical_sample:
        canonical_reports = canonical_sample.get("canonical_reports")
        if not isinstance(canonical_reports, list) or not canonical_reports:
            errors.append("canonical_sample_report_missing_canonical_reports")
            canonical_reports = []
        for index, payload in enumerate(canonical_reports):
            if isinstance(payload, dict):
                _validate_canonical_report(payload, f"stage16f5_run_episode_task_sample_report.json[{index}]", errors)
            else:
                errors.append(f"canonical_sample_report_entry_not_object:{index}")
        if int(report.get("canonical_run_episode_task_report_count", -1)) != len(canonical_reports):
            errors.append("canonical_sample_report_count_mismatch")
        if report.get("canonical_training_data_default_entrypoint_count") != _count_truthy(
            canonical_reports,
            "new_training_data_default_entrypoint",
        ):
            errors.append("canonical_sample_default_entrypoint_count_mismatch")
        if report.get("canonical_non_verl_policy_loss_candidate_count") != sum(
            1
            for payload in canonical_reports
            if isinstance(payload, dict)
            and payload.get("policy_loss_candidate") is True
            and payload.get("provider_route") != "verl"
        ):
            errors.append("canonical_sample_non_verl_policy_loss_count_mismatch")
        errors.extend(_public_leaks(canonical_sample, "stage16f5_run_episode_task_sample_report.json"))
    if test_report:
        for field in (
            "batch_manifest_legacy_metadata_status",
            "experiment_manifest_legacy_metadata_status",
            "batch_manifest_legacy_child_count",
            "experiment_manifest_legacy_child_count",
            "run_episode_batch_status",
        ):
            if test_report.get(field) != report.get(field):
                errors.append(f"stage16f5_test_report_field_mismatch:{field}")
        errors.extend(_public_leaks(test_report, "stage16f5_test_report.json"))
    errors.extend(_public_leaks(report, "stage16f5_entrypoint_policy_report.json"))
    summary_path = root / "stage16f5_acceptance_summary.json"
    if not summary_path.exists():
        errors.append("missing_public_evidence_file:stage16f5_acceptance_summary.json")
    else:
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"stage16f5_acceptance_summary_json_invalid:{exc}")
        else:
            if summary.get("entrypoint_policy_report_sha256") != stable_hash(report):
                # The report hash in the summary is calculated before inspector
                # reattaches derived errors, so retry with the file payload.
                raw_report = json.loads((root / "stage16f5_entrypoint_policy_report.json").read_text(encoding="utf-8"))
                if summary.get("entrypoint_policy_report_sha256") != stable_hash(raw_report):
                    errors.append("acceptance_summary_report_sha256_mismatch")
            if summary.get("schema_version") != "repo_harness_stage16f5_acceptance_summary_v0":
                errors.append("acceptance_summary_schema_version_mismatch")
            if legacy_sample and summary.get("legacy_run_task_sample_report_sha256") != stable_hash(legacy_sample):
                errors.append("acceptance_summary_legacy_sample_sha256_mismatch")
            if canonical_sample and summary.get("run_episode_task_sample_report_sha256") != stable_hash(canonical_sample):
                errors.append("acceptance_summary_canonical_sample_sha256_mismatch")
            if test_report and summary.get("test_report_sha256") != stable_hash(test_report):
                errors.append("acceptance_summary_test_report_sha256_mismatch")
            if summary.get("stage16f5_complete") is not True:
                errors.append("acceptance_summary_stage16f5_complete_not_true")
            if summary.get("status") != "passed":
                errors.append("acceptance_summary_status_not_passed")
            _validate_acceptance_summary_fields(summary, report, errors)
            errors.extend(_public_leaks(summary, "stage16f5_acceptance_summary.json"))
    return errors


def _validate_acceptance_summary_fields(
    summary: dict[str, Any],
    report: dict[str, Any],
    errors: list[str],
) -> None:
    expected_from_report = (
        "legacy_run_task_report_count",
        "canonical_run_episode_task_report_count",
        "legacy_formal_online_rl_eligible_count",
        "legacy_policy_loss_candidate_count",
        "legacy_new_training_data_default_candidate_count",
        "legacy_new_training_data_default_entrypoint_count",
        "legacy_formal_training_data_candidate_count",
        "canonical_training_data_default_entrypoint_count",
        "canonical_non_verl_policy_loss_candidate_count",
        "batch_manifest_legacy_metadata_status",
        "experiment_manifest_legacy_metadata_status",
        "run_episode_batch_status",
        "public_path_leak_scan_passed",
    )
    for field in expected_from_report:
        if summary.get(field) != report.get(field):
            errors.append(f"acceptance_summary_field_mismatch:{field}")
    expected_literal = {
        "ready_for_stage16_5": bool(report.get("passed")),
        "stage16f4_input_status": "passed",
        "legacy_run_task_still_supported": True,
        "legacy_run_task_internal_run_episode_delegate": False,
        "legacy_run_task_training_candidate_blocked": (
            report.get("legacy_formal_online_rl_eligible_count") == 0
            and report.get("legacy_policy_loss_candidate_count") == 0
            and report.get("legacy_formal_training_data_candidate_count") == 0
        ),
        "canonical_run_episode_task_default_for_new_evaluation": True,
        "run_episode_task_projection_binding_required": True,
        "historical_export_compatibility_preserved": True,
        "run_batch_legacy_metadata_inherited": (
            report.get("batch_manifest_legacy_metadata_status") == "passed"
        ),
        "run_experiment_legacy_metadata_status": (
            "covered" if report.get("experiment_manifest_legacy_metadata_status") == "passed" else "failed"
        ),
        "blocking_reason_count": len(report.get("errors") or []),
    }
    for field, expected in expected_literal.items():
        if summary.get(field) != expected:
            errors.append(f"acceptance_summary_field_mismatch:{field}")


def _load_required_public_report(path: Path, label: str, errors: list[str]) -> dict[str, Any]:
    if not path.exists():
        errors.append(f"missing_public_evidence_file:{path.name}")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{label}_json_invalid:{exc}")
        return {}
    if not isinstance(payload, dict):
        errors.append(f"{label}_not_object")
        return {}
    return payload


def _stage16f5_complete_errors(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if report.get("batch_manifest_legacy_metadata_status") != "passed":
        errors.append("batch_manifest_legacy_metadata_status_not_passed")
    if report.get("experiment_manifest_legacy_metadata_status") != "passed":
        errors.append("experiment_manifest_legacy_metadata_status_not_passed")
    if report.get("run_episode_batch_status") != "deferred_to_later_stage":
        errors.append("run_episode_batch_status_unexpected")
    return errors


def _validate_legacy_report(payload: dict[str, Any], relative_path: str, errors: list[str]) -> None:
    required_false = (
        "formal_online_rl_eligible",
        "policy_loss_candidate",
        "formal_training_data_candidate",
        "new_training_data_default_candidate",
        "new_training_data_default_entrypoint",
        "training_data_eligibility_asserted",
    )
    expected = {
        "schema_version": LEGACY_SCHEMA_VERSION,
        "entrypoint": "run_task",
        "entrypoint_classification": "legacy_compatibility",
        "canonical_entrypoint": "run_episode_task",
        "recommended_replacement": "repo-harness run-episode-task",
        "legacy_run_task_still_supported": True,
        "legacy_run_task_internal_run_episode_delegate": False,
        "historical_export_compatibility_allowed": True,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            errors.append(f"legacy_report_field_mismatch:{relative_path}:{key}")
    for key in required_false:
        if key not in payload:
            errors.append(f"legacy_report_missing_explicit_false_field:{relative_path}:{key}")
        elif payload.get(key) is not False:
            errors.append(f"legacy_report_field_must_be_false:{relative_path}:{key}")


def _validate_canonical_report(payload: dict[str, Any], relative_path: str, errors: list[str]) -> None:
    expected = {
        "schema_version": CANONICAL_SCHEMA_VERSION,
        "entrypoint": "run_episode_task",
        "entrypoint_classification": "canonical_run_episode_task",
        "canonical_entrypoint": "run_episode_task",
        "new_training_data_default_entrypoint": True,
        "training_data_eligibility_asserted": False,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            errors.append(f"canonical_report_field_mismatch:{relative_path}:{key}")
    if not payload.get("episode_execution_spec_sha256"):
        errors.append(f"canonical_report_missing_episode_execution_spec_sha256:{relative_path}")
    if "compat_projection_complete" not in payload:
        errors.append(f"canonical_report_missing_compat_projection_complete:{relative_path}")
    elif payload.get("compat_projection_complete") is not True:
        errors.append(f"canonical_report_projection_incomplete:{relative_path}")
    provider_route = payload.get("provider_route")
    if not isinstance(provider_route, str) or not provider_route:
        errors.append(f"canonical_report_missing_provider_route:{relative_path}")
    for key in ("formal_online_rl_eligible", "policy_loss_candidate"):
        if key not in payload:
            errors.append(f"canonical_report_missing_training_gate_field:{relative_path}:{key}")
        elif not isinstance(payload.get(key), bool):
            errors.append(f"canonical_report_training_gate_field_not_boolean:{relative_path}:{key}")
    if payload.get("formal_online_rl_eligible") is True and provider_route != "verl":
        errors.append(f"canonical_report_non_verl_formal_online_rl_eligible:{relative_path}")
    if payload.get("policy_loss_candidate") is True and provider_route != "verl":
        errors.append(f"canonical_report_non_verl_policy_loss_candidate:{relative_path}")


def _check_legacy_child_manifests(
    base: Path,
    *,
    manifest_filename: str,
    manifest_kind: str,
    errors: list[str],
) -> dict[str, Any]:
    observed = False
    child_count = 0
    missing: list[str] = []
    for manifest_path in sorted(base.rglob(manifest_filename)):
        observed = True
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            errors.append(f"{manifest_kind}_manifest_json_invalid:{_relative_to(base, manifest_path)}")
            continue
        runs = manifest.get("runs")
        if not isinstance(runs, list):
            continue
        for run in runs:
            if not isinstance(run, dict):
                continue
            if run.get("status") == "error":
                continue
            run_dir_value = run.get("run_dir")
            if not isinstance(run_dir_value, str) or not run_dir_value:
                continue
            run_dir = Path(run_dir_value)
            if not run_dir.is_absolute():
                run_dir = run_dir if run_dir.exists() else manifest_path.parent / run_dir
            child_count += 1
            if not (run_dir / LEGACY_ENTRYPOINT_REPORT).exists():
                missing.append(str(run.get("run_id") or run_dir.name))
    if missing:
        errors.append(f"{manifest_kind}_legacy_entrypoint_report_missing:" + ",".join(sorted(missing)))
    return {
        "observed": observed,
        "status": "passed" if observed and not missing else ("failed" if missing else "not_observed"),
        "child_count": child_count,
        "missing_child_run_ids": sorted(missing),
    }


def _load_reports(base: Path, filename: str) -> list[dict[str, Any]]:
    records = []
    for path in sorted(base.rglob(filename)):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            payload = {"json_parse_error": str(exc)}
        records.append({"relative_path": _relative_to(base, path), "payload": payload})
    return records


def _public_leaks(payload: Any, relative_path: str) -> list[str]:
    leaks: list[str] = []

    def visit(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                visit(item, f"{path}.{key}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, f"{path}[{index}]")
        elif isinstance(value, str):
            for marker in _FORBIDDEN_PUBLIC_MARKERS:
                if marker in value:
                    leaks.append(f"public_path_or_secret_leak:{relative_path}:{path}:{marker}")

    visit(payload, "$")
    return leaks


def _count_truthy(payloads: list[dict[str, Any]], key: str) -> int:
    return sum(1 for payload in payloads if payload.get(key) is True)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _relative_to(base: Path, path: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.name
