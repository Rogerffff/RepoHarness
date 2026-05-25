"""Stage 16F.6 real-model run-episode smoke acceptance."""

from __future__ import annotations

import json
import re
from hashlib import sha256
from pathlib import Path
from typing import Any

from repo_harness.errors import ConfigError
from repo_harness.schema_base import stable_hash


SUMMARY_FILE = "stage16f6_acceptance_summary.json"
EVIDENCE_MAP_FILE = "stage16f6_canonical_evidence_map.json"
CASE_MANIFEST_FILE = "stage16f6_case_manifest.json"
REAL_MODEL_RUN_REPORT_FILE = "stage16f6_real_model_run_report.json"
PROJECTION_VALIDATION_REPORT_FILE = "stage16f6_projection_validation_report.json"
TOOL_AND_CONTEXT_REPORT_FILE = "stage16f6_tool_and_context_report.json"
PROVIDER_ROUTE_POLICY_REPORT_FILE = "stage16f6_provider_route_policy_report.json"
PATCH_HYGIENE_REPORT_FILE = "stage16f6_patch_hygiene_report.json"
PUBLIC_FEEDBACK_REPORT_FILE = "stage16f6_public_feedback_report.json"
DOCKER_OPTIONAL_REPORT_FILE = "stage16f6_docker_optional_report.json"
PUBLIC_LEAK_SCAN_REPORT_FILE = "stage16f6_public_leak_scan_report.json"
TEST_REPORT_FILE = "stage16f6_test_report.json"
RUNTIME_PRIVATE_DIR = "runtime_private"
RUNTIME_PRIVATE_MANIFEST_FILE = "runtime_private/runtime_private_manifest.json"

SUMMARY_SCHEMA_VERSION = "repo_harness_stage16f6_acceptance_summary_v0"
EVIDENCE_MAP_SCHEMA_VERSION = "repo_harness_stage16f6_canonical_evidence_map_v0"
REPORT_SCHEMA_PREFIX = "repo_harness_stage16f6_"

CANONICAL_REPORT_FILES = (
    CASE_MANIFEST_FILE,
    REAL_MODEL_RUN_REPORT_FILE,
    PROJECTION_VALIDATION_REPORT_FILE,
    TOOL_AND_CONTEXT_REPORT_FILE,
    PROVIDER_ROUTE_POLICY_REPORT_FILE,
    PATCH_HYGIENE_REPORT_FILE,
    PUBLIC_FEEDBACK_REPORT_FILE,
    DOCKER_OPTIONAL_REPORT_FILE,
    PUBLIC_LEAK_SCAN_REPORT_FILE,
    TEST_REPORT_FILE,
)

ALLOWED_PUBLIC_FILES = frozenset((SUMMARY_FILE, EVIDENCE_MAP_FILE, *CANONICAL_REPORT_FILES))

EXTERNAL_PROVIDER_ROUTES = frozenset({"deepseek", "openai"})
EXTERNAL_PROVIDER_POLICY_LOSS_REJECTION_REASON = "external_provider_missing_verl_token_provenance"
ALLOWED_DOCKER_STATUSES = frozenset(
    {
        "executed",
        "skipped_missing_local_image",
        "skipped_docker_unavailable",
        "skipped_not_required",
        "failed",
    }
)
PASSING_DOCKER_STATUSES = ALLOWED_DOCKER_STATUSES - {"failed"}

_RUNTIME_PRIVATE_REF_PATTERN = re.compile(r"runtime-private:[a-z0-9_.:-]+:[0-9a-f]{64}")
_RUNTIME_PRIVATE_REF_EXACT_PATTERN = re.compile(r"^runtime-private:([a-z0-9_.-]+):([0-9a-f]{64})$")
_FORBIDDEN_PUBLIC_MARKERS = (
    "/Users/",
    "/private/",
    "/workspace/",
    "/testbed/",
    "/root/",
    "/home/",
    "/tmp/",
    "\\Users\\",
    "runtime_private/",
    "runtime_private\\",
    ".repo_harness_runtime",
    ".repo-harness-runtime",
    ".repo_harness_env_overlay",
    "hidden_verifier",
    "hiddenVerifier",
    "hidden_test_selector",
    "gold_patch",
    "test_patch",
    "provider_secret",
    "FAIL_TO_PASS",
    "PASS_TO_PASS",
    "sk-test",
    "sk-",
)


class Stage16F6SmokeError(ConfigError):
    """Raised when Stage 16F.6 smoke evidence is invalid."""


def inspect_stage16f6_real_model_smoke(
    evidence: str | Path,
    *,
    assert_complete: bool = False,
) -> str:
    """Inspect Stage 16F.6 real-model smoke evidence."""

    root = Path(evidence)
    report = build_stage16f6_real_model_smoke_report(root)
    if assert_complete and not report["passed"]:
        raise Stage16F6SmokeError("; ".join(report["errors"]))
    return json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False)


def build_stage16f6_real_model_smoke_report(root: str | Path) -> dict[str, Any]:
    """Build a machine-checkable Stage 16F.6 acceptance report."""

    evidence_root = Path(root)
    errors: list[str] = []
    if not evidence_root.exists():
        raise Stage16F6SmokeError(f"evidence path does not exist: {evidence_root}")
    if not evidence_root.is_dir():
        raise Stage16F6SmokeError(f"evidence path is not a directory: {evidence_root}")

    public_files = _public_files(evidence_root)
    unknown_files = sorted(path for path in public_files if path not in ALLOWED_PUBLIC_FILES)
    errors.extend(f"unknown_public_evidence_file:{path}" for path in unknown_files)
    for filename in ALLOWED_PUBLIC_FILES:
        if filename not in public_files:
            errors.append(f"missing_public_evidence_file:{filename}")

    payloads = {
        filename: _load_json_report(evidence_root / filename, filename, errors)
        for filename in sorted(public_files & ALLOWED_PUBLIC_FILES)
    }
    summary = payloads.get(SUMMARY_FILE, {})
    evidence_map = payloads.get(EVIDENCE_MAP_FILE, {})

    errors.extend(_validate_canonical_evidence_map(evidence_root, evidence_map, payloads))
    if summary:
        errors.extend(_validate_summary(summary, evidence_map, payloads))

    derived = _derive_stage16f6_counts(payloads, errors)
    errors.extend(_validate_case_consistency(payloads))
    errors.extend(_validate_provider_route_policy(payloads))
    private_manifest = _load_runtime_private_manifest(evidence_root, errors)
    errors.extend(_validate_projection_and_patch_reports(payloads, evidence_root, private_manifest))
    errors.extend(_validate_public_feedback(payloads))
    errors.extend(_validate_docker_optional_report(payloads))
    errors.extend(_validate_tool_and_context_report(payloads))
    errors.extend(_validate_test_report(payloads))
    errors.extend(_scan_public_evidence_for_leaks(evidence_root, public_files))

    leak_scan = payloads.get(PUBLIC_LEAK_SCAN_REPORT_FILE, {})
    if leak_scan:
        if leak_scan.get("public_path_leak_scan_passed") is not True:
            errors.append("public_leak_scan_report_not_passed")
        if int(leak_scan.get("finding_count", 0)) != 0:
            errors.append("public_leak_scan_report_finding_count_nonzero")

    passed = not errors
    report = {
        "schema_version": "repo_harness_stage16f6_inspection_report_v0",
        "evidence_root_label": "stage16f6_input_root",
        "evidence_root_name": evidence_root.name,
        "passed": passed,
        "errors": sorted(set(errors)),
        **derived,
    }
    return report


def _public_files(root: Path) -> set[str]:
    files: set[str] = set()
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        if relative == RUNTIME_PRIVATE_DIR or relative.startswith(f"{RUNTIME_PRIVATE_DIR}/"):
            continue
        if path.is_file():
            files.add(relative)
        elif path.is_dir() and path != root:
            # Public evidence is intentionally flat in Stage 16F.6.  A directory
            # usually means raw runtime output leaked into the evidence root.
            files.add(relative + "/")
    return files


def _load_json_report(path: Path, label: str, errors: list[str]) -> dict[str, Any]:
    if not path.exists():
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


def _validate_canonical_evidence_map(
    root: Path,
    evidence_map: dict[str, Any],
    payloads: dict[str, dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    if not evidence_map:
        return ["missing_canonical_evidence_map_payload"]
    if evidence_map.get("schema_version") != EVIDENCE_MAP_SCHEMA_VERSION:
        errors.append("canonical_evidence_map_schema_version_mismatch")
    items = evidence_map.get("items")
    if not isinstance(items, list):
        errors.append("canonical_evidence_map_items_not_list")
        return errors
    records: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"canonical_evidence_map_item_not_object:{index}")
            continue
        relative_path = item.get("relative_path")
        if not isinstance(relative_path, str):
            errors.append(f"canonical_evidence_map_item_missing_relative_path:{index}")
            continue
        if relative_path in records:
            errors.append(f"canonical_evidence_map_duplicate_item:{relative_path}")
            continue
        records[relative_path] = item
    expected_paths = set(CANONICAL_REPORT_FILES)
    missing = sorted(expected_paths - set(records))
    extra = sorted(set(records) - expected_paths)
    errors.extend(f"canonical_evidence_map_missing_item:{path}" for path in missing)
    errors.extend(f"canonical_evidence_map_unexpected_item:{path}" for path in extra)
    for relative_path, item in sorted(records.items()):
        if item.get("required_for_assert_complete") is not True:
            errors.append(f"canonical_evidence_map_item_not_required:{relative_path}")
        artifact_kind = item.get("artifact_kind")
        if not isinstance(artifact_kind, str) or not artifact_kind:
            errors.append(f"canonical_evidence_map_missing_artifact_kind:{relative_path}")
        expected_payload = payloads.get(relative_path)
        if expected_payload is None:
            errors.append(f"canonical_evidence_map_points_to_missing_payload:{relative_path}")
            continue
        expected_sha = stable_hash(expected_payload)
        if item.get("sha256") != expected_sha:
            errors.append(f"canonical_evidence_map_sha256_mismatch:{relative_path}")
        file_path = root / relative_path
        if not file_path.exists():
            errors.append(f"canonical_evidence_map_file_missing:{relative_path}")
    return errors


def _validate_summary(
    summary: dict[str, Any],
    evidence_map: dict[str, Any],
    payloads: dict[str, dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    if summary.get("schema_version") != SUMMARY_SCHEMA_VERSION:
        errors.append("acceptance_summary_schema_version_mismatch")
    if summary.get("status") != "passed":
        errors.append("acceptance_summary_status_not_passed")
    if summary.get("stage16f6_complete") is not True:
        errors.append("acceptance_summary_stage16f6_complete_not_true")
    if summary.get("ready_for_stage16_5") is not True:
        errors.append("acceptance_summary_ready_for_stage16_5_not_true")
    if summary.get("ready_for_stage17_data_registry_planning") is not True:
        errors.append("acceptance_summary_ready_for_stage17_not_true")
    if evidence_map and summary.get("canonical_evidence_map_sha256") != stable_hash(evidence_map):
        errors.append("acceptance_summary_canonical_evidence_map_sha256_mismatch")
    derived = _derive_stage16f6_counts(payloads, [])
    for field in (
        "real_model_case_count",
        "completed_real_model_episode_count",
        "projection_complete_count",
        "legacy_run_task_invocation_count",
        "policy_loss_candidate_count",
        "external_provider_case_count",
        "public_feedback_enabled_case_count",
        "public_feedback_observed_case_count",
        "public_feedback_event_count",
        "blocking_reason_count",
    ):
        if summary.get(field) != derived.get(field):
            errors.append(f"acceptance_summary_field_mismatch:{field}")
    if summary.get("docker_case_status") != derived.get("docker_case_status"):
        errors.append("acceptance_summary_field_mismatch:docker_case_status")
    if summary.get("public_path_leak_scan_passed") is not True:
        errors.append("acceptance_summary_public_path_leak_scan_not_true")
    if summary.get("provider_secret_leak_scan_passed") is not True:
        errors.append("acceptance_summary_provider_secret_leak_scan_not_true")
    return errors


def _derive_stage16f6_counts(
    payloads: dict[str, dict[str, Any]],
    errors: list[str],
) -> dict[str, Any]:
    case_manifest = payloads.get(CASE_MANIFEST_FILE, {})
    real_model_report = payloads.get(REAL_MODEL_RUN_REPORT_FILE, {})
    projection_report = payloads.get(PROJECTION_VALIDATION_REPORT_FILE, {})
    route_report = payloads.get(PROVIDER_ROUTE_POLICY_REPORT_FILE, {})
    feedback_report = payloads.get(PUBLIC_FEEDBACK_REPORT_FILE, {})
    docker_report = payloads.get(DOCKER_OPTIONAL_REPORT_FILE, {})

    cases = _list_field(case_manifest, "cases", errors, CASE_MANIFEST_FILE)
    case_records = _list_field(real_model_report, "case_records", errors, REAL_MODEL_RUN_REPORT_FILE)
    projection_records = _list_field(
        projection_report,
        "case_projection_results",
        errors,
        PROJECTION_VALIDATION_REPORT_FILE,
    )
    route_records = _list_field(route_report, "case_route_results", errors, PROVIDER_ROUTE_POLICY_REPORT_FILE)

    completed_count = sum(1 for record in case_records if record.get("episode_completed") is True)
    projection_complete_count = sum(1 for record in projection_records if record.get("projection_complete") is True)
    policy_loss_count = sum(1 for record in route_records if record.get("policy_loss_candidate") is True)
    external_count = sum(1 for record in route_records if record.get("provider_route") in EXTERNAL_PROVIDER_ROUTES)
    legacy_invocation_count = int(real_model_report.get("legacy_run_task_invocation_count", 0) or 0)

    return {
        "real_model_case_count": len(cases),
        "completed_real_model_episode_count": completed_count,
        "projection_complete_count": projection_complete_count,
        "legacy_run_task_invocation_count": legacy_invocation_count,
        "policy_loss_candidate_count": policy_loss_count,
        "external_provider_case_count": external_count,
        "public_feedback_enabled_case_count": int(
            feedback_report.get("public_feedback_enabled_case_count", 0) or 0
        ),
        "public_feedback_observed_case_count": int(
            feedback_report.get("public_feedback_observed_case_count", 0) or 0
        ),
        "public_feedback_event_count": int(feedback_report.get("public_feedback_event_count", 0) or 0),
        "docker_case_status": docker_report.get("docker_case_status"),
        "blocking_reason_count": 0,
    }


def _validate_case_consistency(payloads: dict[str, dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    case_manifest = payloads.get(CASE_MANIFEST_FILE, {})
    real_model_report = payloads.get(REAL_MODEL_RUN_REPORT_FILE, {})
    cases = case_manifest.get("cases") if isinstance(case_manifest.get("cases"), list) else []
    case_records = real_model_report.get("case_records") if isinstance(real_model_report.get("case_records"), list) else []
    manifest_ids = _case_ids(cases, "case_manifest", errors)
    run_ids = _case_ids(case_records, "real_model_run_report", errors)
    if manifest_ids != run_ids:
        errors.append("case_manifest_real_model_report_case_id_mismatch")
    for record in cases:
        if isinstance(record, dict) and record.get("entrypoint") != "run_episode_task":
            errors.append(f"case_manifest_entrypoint_not_run_episode_task:{record.get('case_id')}")
    report_case_fields = (
        (PROJECTION_VALIDATION_REPORT_FILE, "case_projection_results", "projection_validation_report"),
        (PROVIDER_ROUTE_POLICY_REPORT_FILE, "case_route_results", "provider_route_policy_report"),
        (PATCH_HYGIENE_REPORT_FILE, "case_patch_hygiene_results", "patch_hygiene_report"),
        (PUBLIC_FEEDBACK_REPORT_FILE, "case_public_feedback_results", "public_feedback_report"),
    )
    for filename, field, label in report_case_fields:
        payload = payloads.get(filename, {})
        records = payload.get(field) if isinstance(payload.get(field), list) else []
        report_ids = _case_ids(records, label, errors)
        if manifest_ids != report_ids:
            errors.append(f"case_manifest_{label}_case_id_mismatch")
    if int(real_model_report.get("real_model_case_count", -1)) != len(cases):
        errors.append("real_model_report_case_count_mismatch")
    completed_count = sum(1 for record in case_records if record.get("episode_completed") is True)
    if int(real_model_report.get("completed_real_model_episode_count", -1)) != completed_count:
        errors.append("real_model_report_completed_count_mismatch")
    if int(real_model_report.get("run_episode_task_invocation_count", -1)) != len(cases):
        errors.append("run_episode_task_invocation_count_mismatch")
    if int(real_model_report.get("legacy_run_task_invocation_count", -1)) != 0:
        errors.append("legacy_run_task_invocation_count_nonzero")
    if int(real_model_report.get("infrastructure_failure_count", 0)) != 0:
        errors.append("infrastructure_failure_count_nonzero")
    if int(real_model_report.get("provider_failure_count", 0)) != 0:
        errors.append("provider_failure_count_nonzero")
    if int(real_model_report.get("provider_rate_limit_count", 0)) != 0:
        errors.append("provider_rate_limit_count_nonzero")
    if int(real_model_report.get("tool_error_count", 0)) != 0:
        errors.append("tool_error_count_nonzero")
    if len(cases) < 3:
        errors.append("real_model_case_count_too_low")
    if completed_count < 2:
        errors.append("completed_real_model_episode_count_too_low")
    return errors


def _validate_projection_and_patch_reports(
    payloads: dict[str, dict[str, Any]],
    root: Path,
    private_manifest: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    projection_report = payloads.get(PROJECTION_VALIDATION_REPORT_FILE, {})
    patch_report = payloads.get(PATCH_HYGIENE_REPORT_FILE, {})
    real_model_report = payloads.get(REAL_MODEL_RUN_REPORT_FILE, {})
    projection_records = projection_report.get("case_projection_results")
    patch_records = patch_report.get("case_patch_hygiene_results")
    if not isinstance(projection_records, list):
        return ["projection_validation_case_results_missing"]
    if not isinstance(patch_records, list):
        return ["patch_hygiene_case_results_missing"]
    if _case_ids(projection_records, "projection_validation_report", errors) != _case_ids(
        patch_records,
        "patch_hygiene_report",
        errors,
    ):
        errors.append("projection_patch_case_id_mismatch")
    projection_by_case = {
        record.get("case_id"): record
        for record in projection_records
        if isinstance(record, dict) and isinstance(record.get("case_id"), str)
    }
    real_model_by_case = {
        record.get("case_id"): record
        for record in real_model_report.get("case_records", [])
        if isinstance(record, dict) and isinstance(record.get("case_id"), str)
    }
    private_records = _runtime_private_manifest_records(private_manifest, errors)
    for record in projection_records:
        case_id = record.get("case_id")
        if record.get("projection_complete") is not True:
            errors.append(f"projection_incomplete:{case_id}")
        if record.get("entrypoint") != "run_episode_task":
            errors.append(f"projection_entrypoint_not_run_episode_task:{case_id}")
        validation_errors = record.get("projection_validation_errors")
        if validation_errors != []:
            errors.append(f"projection_validation_errors_nonempty:{case_id}")
        compat_projection_sha256 = record.get("compat_projection_sha256")
        if not _is_sha256(compat_projection_sha256):
            errors.append(f"projection_missing_or_invalid_compat_projection_sha256:{case_id}")
        real_model_record = real_model_by_case.get(case_id)
        if real_model_record is not None and real_model_record.get("compat_projection_sha256") != compat_projection_sha256:
            errors.append(f"projection_real_model_compat_projection_sha256_mismatch:{case_id}")
        _validate_runtime_private_ref(
            root,
            private_records,
            record.get("compat_projection_ref"),
            expected_kind="compat-projection",
            expected_sha256=compat_projection_sha256,
            context=f"projection_compat_projection_ref:{case_id}",
            errors=errors,
        )
        for field in ("final_patch_sha256", "final_diff_sha256", "final_patch_hygiene_report_sha256"):
            if not _is_sha256(record.get(field)):
                errors.append(f"projection_missing_or_invalid_{field}:{case_id}")
        for ref_field, sha_field, expected_kind in (
            ("final_patch_ref", "final_patch_sha256", "final-patch"),
            ("final_diff_ref", "final_diff_sha256", "final-diff"),
            ("final_patch_hygiene_report_ref", "final_patch_hygiene_report_sha256", "final-patch-hygiene-report"),
        ):
            _validate_runtime_private_ref(
                root,
                private_records,
                record.get(ref_field),
                expected_kind=expected_kind,
                expected_sha256=record.get(sha_field),
                context=f"projection_{ref_field}:{case_id}",
                errors=errors,
            )
    for record in patch_records:
        case_id = record.get("case_id")
        if record.get("patch_hygiene_status") != "passed":
            errors.append(f"patch_hygiene_status_not_passed:{case_id}")
        if record.get("public_report_contains_raw_patch") is not False:
            errors.append(f"patch_hygiene_raw_patch_public:{case_id}")
        projection_record = projection_by_case.get(case_id)
        for field in ("final_patch_sha256", "final_diff_sha256", "final_patch_hygiene_report_sha256"):
            if not _is_sha256(record.get(field)):
                errors.append(f"patch_hygiene_missing_or_invalid_{field}:{case_id}")
            if projection_record is not None and record.get(field) != projection_record.get(field):
                errors.append(f"patch_projection_digest_mismatch:{case_id}:{field}")
        for ref_field in ("final_patch_ref", "final_diff_ref", "final_patch_hygiene_report_ref"):
            if projection_record is not None and record.get(ref_field) != projection_record.get(ref_field):
                errors.append(f"patch_projection_ref_mismatch:{case_id}:{ref_field}")
        if record.get("cleaned_patch_sha256") != record.get("final_patch_sha256"):
            errors.append(f"patch_hygiene_cleaned_patch_sha256_mismatch:{case_id}")
        if record.get("cleaned_diff_sha256") != record.get("final_diff_sha256"):
            errors.append(f"patch_hygiene_cleaned_diff_sha256_mismatch:{case_id}")
    return errors


def _validate_provider_route_policy(payloads: dict[str, dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    route_report = payloads.get(PROVIDER_ROUTE_POLICY_REPORT_FILE, {})
    real_model_report = payloads.get(REAL_MODEL_RUN_REPORT_FILE, {})
    case_manifest = payloads.get(CASE_MANIFEST_FILE, {})
    records = route_report.get("case_route_results")
    if not isinstance(records, list):
        return ["provider_route_case_results_missing"]
    real_records = {
        record.get("case_id"): record
        for record in real_model_report.get("case_records", [])
        if isinstance(record, dict) and isinstance(record.get("case_id"), str)
    }
    manifest_records = {
        record.get("case_id"): record
        for record in case_manifest.get("cases", [])
        if isinstance(record, dict) and isinstance(record.get("case_id"), str)
    }
    external_count = 0
    for record in records:
        case_id = record.get("case_id")
        route = record.get("provider_route")
        if route in EXTERNAL_PROVIDER_ROUTES:
            external_count += 1
        real_record = real_records.get(case_id)
        manifest_record = manifest_records.get(case_id)
        if real_record is not None:
            for field in ("provider_route", "formal_online_rl_eligible", "policy_loss_candidate"):
                if real_record.get(field) != record.get(field):
                    errors.append(f"real_model_provider_route_field_mismatch:{case_id}:{field}")
        if manifest_record is not None:
            if manifest_record.get("expected_formal_online_rl_eligible") != record.get("formal_online_rl_eligible"):
                errors.append(f"case_manifest_formal_online_rl_expectation_mismatch:{case_id}")
            if manifest_record.get("expected_policy_loss_candidate") != record.get("policy_loss_candidate"):
                errors.append(f"case_manifest_policy_loss_expectation_mismatch:{case_id}")
        if route != "verl":
            reason_not_policy_loss_candidate = record.get("reason_not_policy_loss_candidate")
            if record.get("route_is_verl") is True:
                errors.append(f"non_verl_route_is_verl_true:{case_id}")
            if record.get("formal_online_rl_eligible") is True:
                errors.append(f"non_verl_formal_online_rl_eligible:{case_id}")
            if record.get("policy_loss_candidate") is True:
                errors.append(f"non_verl_policy_loss_candidate:{case_id}")
            if record.get("training_data_eligibility_asserted") is True:
                errors.append(f"non_verl_training_data_eligibility_asserted:{case_id}")
            if not isinstance(reason_not_policy_loss_candidate, str) or not reason_not_policy_loss_candidate:
                errors.append(f"missing_reason_not_policy_loss_candidate:{case_id}")
            elif route in EXTERNAL_PROVIDER_ROUTES and (
                reason_not_policy_loss_candidate != EXTERNAL_PROVIDER_POLICY_LOSS_REJECTION_REASON
            ):
                errors.append(f"external_provider_policy_loss_rejection_reason_mismatch:{case_id}")
    if external_count < 3:
        errors.append("external_provider_case_count_too_low")
    return errors


def _validate_public_feedback(payloads: dict[str, dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    report = payloads.get(PUBLIC_FEEDBACK_REPORT_FILE, {})
    records = report.get("case_public_feedback_results")
    if not isinstance(records, list):
        return ["public_feedback_case_results_missing"]
    enabled = int(report.get("public_feedback_enabled_case_count", 0) or 0)
    observed = int(report.get("public_feedback_observed_case_count", 0) or 0)
    event_count = int(report.get("public_feedback_event_count", 0) or 0)
    derived_enabled = sum(1 for record in records if record.get("public_feedback_enabled") is True)
    derived_observed = sum(1 for record in records if record.get("public_feedback_observed") is True)
    derived_events = sum(int(record.get("public_feedback_event_count", 0) or 0) for record in records)
    if enabled != derived_enabled:
        errors.append("public_feedback_enabled_count_mismatch")
    if observed != derived_observed:
        errors.append("public_feedback_observed_count_mismatch")
    if event_count != derived_events:
        errors.append("public_feedback_event_count_mismatch")
    if enabled < 1:
        errors.append("public_feedback_enabled_case_count_too_low")
    if observed < 1:
        errors.append("public_feedback_observed_case_count_too_low")
    if event_count < 1:
        errors.append("public_feedback_event_count_too_low")
    for record in records:
        if record.get("public_feedback_observed") is True:
            if record.get("run_tests_tool_call_observed") is not True:
                errors.append(f"public_feedback_without_run_tests:{record.get('case_id')}")
            if record.get("hidden_feedback_not_exposed") is not True:
                errors.append(f"public_feedback_hidden_feedback_exposed:{record.get('case_id')}")
    return errors


def _validate_docker_optional_report(payloads: dict[str, dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    report = payloads.get(DOCKER_OPTIONAL_REPORT_FILE, {})
    status = report.get("docker_case_status")
    if status not in ALLOWED_DOCKER_STATUSES:
        errors.append("docker_case_status_invalid")
    elif status not in PASSING_DOCKER_STATUSES:
        errors.append("docker_case_status_failed")
    if report.get("docker_case_required") is not False:
        errors.append("docker_case_required_not_false")
    if status == "executed":
        for field in ("selected_image_ref", "selected_image_id", "selected_image_digest_status"):
            if not report.get(field):
                errors.append(f"docker_executed_missing_field:{field}")
    selected_image_ref = str(report.get("selected_image_ref") or "")
    if _looks_like_swebench_cached_image(selected_image_ref) and report.get("swebench_cached_image_used") is not True:
        errors.append("swebench_cached_image_ref_not_declared")
    if report.get("swebench_cached_image_used") is True:
        for field in ("task_manifest_ref", "why_safe_for_stage16f6"):
            if not report.get(field):
                errors.append(f"swebench_cached_image_missing_binding:{field}")
        for field in ("task_manifest_sha256", "source_snapshot_digest", "verifier_plan_digest"):
            if not _is_sha256(report.get(field)):
                errors.append(f"swebench_cached_image_invalid_sha256_binding:{field}")
        image_digest = report.get("image_digest")
        if not (
            isinstance(image_digest, str)
            and image_digest.startswith("sha256:")
            and _is_sha256(image_digest.removeprefix("sha256:"))
        ):
            errors.append("swebench_cached_image_invalid_image_digest")
    elif "reason_swebench_cached_image_not_used" not in report:
        errors.append("missing_reason_swebench_cached_image_not_used")
    return errors


def _looks_like_swebench_cached_image(image_ref: str) -> bool:
    return (
        image_ref.startswith("sweb.env.")
        or image_ref.startswith("sweb.base.")
        or image_ref.startswith("swebench/")
        or image_ref.startswith("repo-harness-swebench-verified-agent:")
    )


def _validate_tool_and_context_report(payloads: dict[str, dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    report = payloads.get(TOOL_AND_CONTEXT_REPORT_FILE, {})
    for field in (
        "public_environment_context_present",
        "public_environment_context_digest",
        "tool_schema_snapshot_digest",
        "allowed_tool_names",
        "run_tests_feedback_policy",
    ):
        if field not in report:
            errors.append(f"tool_and_context_missing_field:{field}")
    if report.get("legacy_run_task_context_used") is not False:
        errors.append("legacy_run_task_context_used")
    allowed_tools = report.get("allowed_tool_names")
    if not isinstance(allowed_tools, list) or not allowed_tools:
        errors.append("allowed_tool_names_missing_or_empty")
    return errors


def _validate_test_report(payloads: dict[str, dict[str, Any]]) -> list[str]:
    report = payloads.get(TEST_REPORT_FILE, {})
    if not report:
        return []
    if report.get("stage16f6_tests_status") not in {"passed", "not_run_diagnostic_only"}:
        return ["stage16f6_test_report_status_invalid"]
    return []


def _load_runtime_private_manifest(root: Path, errors: list[str]) -> dict[str, Any]:
    path = root / RUNTIME_PRIVATE_MANIFEST_FILE
    if not path.exists():
        return {}
    payload = _load_json_report(path, RUNTIME_PRIVATE_MANIFEST_FILE, errors)
    if payload and payload.get("schema_version") != "repo_harness_stage16f6_runtime_private_manifest_v0":
        errors.append("runtime_private_manifest_schema_version_mismatch")
    return payload


def _runtime_private_manifest_records(manifest: dict[str, Any], errors: list[str]) -> dict[str, dict[str, Any]]:
    if not manifest:
        return {}
    items = manifest.get("items")
    if not isinstance(items, list):
        errors.append("runtime_private_manifest_items_not_list")
        return {}
    records: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"runtime_private_manifest_item_not_object:{index}")
            continue
        ref = item.get("ref")
        if not isinstance(ref, str) or not _RUNTIME_PRIVATE_REF_EXACT_PATTERN.fullmatch(ref):
            errors.append(f"runtime_private_manifest_item_invalid_ref:{index}")
            continue
        if ref in records:
            errors.append(f"runtime_private_manifest_duplicate_ref:{ref}")
            continue
        records[ref] = item
    return records


def _validate_runtime_private_ref(
    root: Path,
    records: dict[str, dict[str, Any]],
    ref: Any,
    *,
    expected_kind: str,
    expected_sha256: Any,
    context: str,
    errors: list[str],
) -> None:
    if not isinstance(ref, str):
        errors.append(f"runtime_private_ref_missing:{context}")
        return
    match = _RUNTIME_PRIVATE_REF_EXACT_PATTERN.fullmatch(ref)
    if match is None:
        errors.append(f"runtime_private_ref_invalid:{context}")
        return
    ref_kind, ref_sha256 = match.groups()
    if ref_kind != expected_kind:
        errors.append(f"runtime_private_ref_kind_mismatch:{context}")
    if _is_sha256(expected_sha256) and ref_sha256 != expected_sha256:
        errors.append(f"runtime_private_ref_sha256_mismatch:{context}")
    item = records.get(ref)
    if item is None:
        errors.append(f"runtime_private_ref_missing_manifest_item:{context}")
        return
    if item.get("artifact_kind") != expected_kind:
        errors.append(f"runtime_private_manifest_artifact_kind_mismatch:{context}")
    if item.get("sha256") != ref_sha256:
        errors.append(f"runtime_private_manifest_sha256_mismatch:{context}")
    relative_path = item.get("relative_path")
    if not isinstance(relative_path, str):
        errors.append(f"runtime_private_manifest_missing_relative_path:{context}")
        return
    path = Path(relative_path)
    if path.is_absolute() or ".." in path.parts or not relative_path.startswith(f"{RUNTIME_PRIVATE_DIR}/"):
        errors.append(f"runtime_private_manifest_unsafe_relative_path:{context}")
        return
    artifact_path = root / relative_path
    if not artifact_path.exists() or not artifact_path.is_file():
        errors.append(f"runtime_private_artifact_missing:{context}")
        return
    actual_sha256 = sha256(artifact_path.read_bytes()).hexdigest()
    if actual_sha256 != ref_sha256:
        errors.append(f"runtime_private_artifact_sha256_mismatch:{context}")


def _scan_public_evidence_for_leaks(root: Path, public_files: set[str]) -> list[str]:
    findings: list[str] = []
    for relative_path in sorted(public_files):
        if relative_path.endswith("/"):
            findings.append(f"public_evidence_directory_not_allowed:{relative_path}")
            continue
        path = root / relative_path
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            findings.append(f"public_evidence_not_utf8:{relative_path}")
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            sanitized = _RUNTIME_PRIVATE_REF_PATTERN.sub("runtime-private:<redacted>", text)
            for marker in _FORBIDDEN_PUBLIC_MARKERS:
                if marker in sanitized:
                    findings.append(f"{relative_path}:{marker}")
            continue
        findings.extend(_scan_json_string_values(payload, relative_path))
    return [f"path_or_secret_leak:{finding}" for finding in findings]


def _scan_json_string_values(payload: Any, relative_path: str) -> list[str]:
    findings: list[str] = []
    if isinstance(payload, str):
        sanitized = _RUNTIME_PRIVATE_REF_PATTERN.sub("runtime-private:<redacted>", payload)
        for marker in _FORBIDDEN_PUBLIC_MARKERS:
            if marker in sanitized:
                findings.append(f"{relative_path}:{marker}")
        return findings
    if isinstance(payload, list):
        for item in payload:
            findings.extend(_scan_json_string_values(item, relative_path))
        return findings
    if isinstance(payload, dict):
        for value in payload.values():
            findings.extend(_scan_json_string_values(value, relative_path))
    return findings


def _validate_case_consistency_records(
    left: list[dict[str, Any]],
    right: list[dict[str, Any]],
    *,
    left_label: str,
    right_label: str,
) -> list[str]:
    errors: list[str] = []
    if _case_ids(left, left_label, errors) != _case_ids(right, right_label, errors):
        errors.append(f"{left_label}_{right_label}_case_id_mismatch")
    return errors


def _case_ids(records: list[Any], label: str, errors: list[str]) -> set[str]:
    ids: set[str] = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(f"{label}_record_not_object:{index}")
            continue
        case_id = record.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            errors.append(f"{label}_record_missing_case_id:{index}")
            continue
        if case_id in ids:
            errors.append(f"{label}_duplicate_case_id:{case_id}")
        ids.add(case_id)
    return ids


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-f]{64}", value))


def _list_field(
    payload: dict[str, Any],
    field: str,
    errors: list[str],
    label: str,
) -> list[dict[str, Any]]:
    value = payload.get(field)
    if not isinstance(value, list):
        errors.append(f"{label}_missing_list_field:{field}")
        return []
    return [item for item in value if isinstance(item, dict)]
