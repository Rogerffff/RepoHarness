"""Stage 16F.4 parity audit for ``run_task`` and ``run_episode`` task runs."""

from __future__ import annotations

import json
import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from repo_harness.errors import RepoHarnessError
from repo_harness.evaluation.episode_projection import (
    ProjectionValidationError,
    validate_run_episode_compat_projection,
)
from repo_harness.evaluation.episode_runner import run_episode_task
from repo_harness.evaluation.runner import run_task
STAGE16F4_SCHEMA_VERSION = "repo_harness_stage16f4_parity_v0"
STAGE16F4_EVIDENCE_DIR = "stage16f_4"

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
    "hidden_test_patch",
    "gold_patch",
    "test_patch",
    "accepted_label",
    "reward_metadata",
    "complete_reward_metadata",
    "provider_secret",
    "FAIL_TO_PASS",
    "PASS_TO_PASS",
)
_FORBIDDEN_PUBLIC_PATCH_AUDIT_FIELDS = {
    "raw_patch_sha256",
    "raw_diff_sha256",
    "raw_patch_ref",
    "raw_diff_ref",
    "raw_final_patch",
    "raw_final_diff",
    "final_patch_ref",
    "final_diff_ref",
}
_PUBLIC_PATCH_HYGIENE_KEYS = {
    "schema_version",
    "patch_hygiene_policy_version",
    "status",
    "structured_diff_facts_status",
    "diff_structured_diff_facts_status",
    "cleaned_patch_sha256",
    "cleaned_diff_sha256",
    "filtered_file_count",
    "flagged_file_count",
    "filtered_files",
    "flagged_files",
    "only_filtered_changes",
    "cleaned_patch_empty",
    "training_target_patch_source",
    "public_report_contains_raw_patch",
    "projection_sanitization_status",
}


class Stage16F4ParityError(RepoHarnessError):
    """Raised when Stage 16F.4 parity evidence is incomplete or unsafe."""


@dataclass(frozen=True)
class Stage16F4ParityCase:
    case_id: str
    task_path: str
    config_path: str
    old_run_id: str
    new_run_id: str
    coverage_tags: tuple[str, ...] = ()
    expected_difference_reason: str | None = None


DEFAULT_STAGE16F4_PARITY_CASES: tuple[Stage16F4ParityCase, ...] = (
    Stage16F4ParityCase(
        case_id="task001_mock_public_feedback",
        task_path="tests/fixtures/tasks/task_001.yaml",
        config_path="tests/fixtures/run_configs/stage16f4_mock_provider_public_feedback.yaml",
        old_run_id="stage16f4_old_task001_public",
        new_run_id="stage16f4_new_task001_public",
        coverage_tags=("accepted", "public_feedback", "nonempty_patch_hygiene"),
    ),
    Stage16F4ParityCase(
        case_id="task001_mock_final_answer_rejected",
        task_path="tests/fixtures/tasks/task_001.yaml",
        config_path="tests/fixtures/run_configs/stage16f4_mock_provider_final_answer.yaml",
        old_run_id="stage16f4_old_task001_rejected",
        new_run_id="stage16f4_new_task001_rejected",
        coverage_tags=("rejected", "empty_patch_hygiene"),
    ),
    Stage16F4ParityCase(
        case_id="v2_calc_zero_mock_public_feedback",
        task_path="tests/fixtures/tasks/v2/calc_zero_001.yaml",
        config_path="tests/fixtures/run_configs/stage16f4_mock_provider_public_feedback.yaml",
        old_run_id="stage16f4_old_v2_calc_zero_public",
        new_run_id="stage16f4_new_v2_calc_zero_public",
        coverage_tags=("accepted", "public_feedback", "nonempty_patch_hygiene"),
    ),
)


def run_stage16f4_parity_audit(
    output_dir: str | Path,
    *,
    cases: tuple[Stage16F4ParityCase, ...] = DEFAULT_STAGE16F4_PARITY_CASES,
    clean_output_dir: bool = False,
    keep_runtime_private_runs: bool = False,
) -> Path:
    """Run the small Stage 16F.4 parity audit and write public-safe evidence."""

    output_path = Path(output_dir)
    if clean_output_dir and output_path.exists():
        shutil.rmtree(output_path)
    output_path.mkdir(parents=True, exist_ok=True)
    runs_root = output_path / "runtime_private_runs"
    if runs_root.exists():
        shutil.rmtree(runs_root)
    old_root = runs_root / "old_run_task"
    new_root = runs_root / "new_run_episode_task"
    case_records: list[dict[str, Any]] = []
    for case in cases:
        old_run_dir = run_task(
            case.task_path,
            config_path=case.config_path,
            output_dir=old_root,
            run_id=case.old_run_id,
        )
        new_run_dir = run_episode_task(
            case.task_path,
            config_path=case.config_path,
            output_dir=new_root,
            run_id=case.new_run_id,
            assert_projection_complete=True,
        )
        case_records.append(
            _case_record(
                case=case,
                old_run_dir=Path(old_run_dir),
                new_run_dir=Path(new_run_dir),
            )
        )
    _write_stage16f4_evidence(output_path, case_records)
    inspect_stage16f4_parity(output_path, assert_complete=True)
    if not keep_runtime_private_runs:
        shutil.rmtree(runs_root, ignore_errors=True)
        _update_runtime_private_runs_status(
            output_path,
            status="removed_after_public_projection",
        )
        inspect_stage16f4_parity(output_path, assert_complete=True)
    return output_path


def inspect_stage16f4_parity(evidence_dir: str | Path, *, assert_complete: bool = False) -> str:
    """Inspect Stage 16F.4 parity evidence and optionally fail closed."""

    evidence_path = Path(evidence_dir)
    summary = _read_json(evidence_path / "stage16f4_acceptance_summary.json")
    parity_report = _read_json(evidence_path / "stage16f4_run_task_run_episode_parity_report.json")
    blocking = _read_json(evidence_path / "stage16f4_blocking_differences.json")
    projection = _read_json(evidence_path / "stage16f4_projection_binding_report.json")
    expected = _read_json(evidence_path / "stage16f4_expected_differences.json")
    test_report = _read_json(evidence_path / "stage16f4_test_report.json")

    errors: list[str] = []
    cases = parity_report.get("cases")
    if not isinstance(cases, list):
        errors.append("parity_cases_not_list")
        cases = []
    derived = _derive_summary_from_cases(cases)
    for key, expected_value in derived.items():
        if summary.get(key) != expected_value:
            errors.append(f"summary_field_mismatch:{key}")
    if blocking.get("blocking_difference_count") != len(blocking.get("blocking_differences", [])):
        errors.append("blocking_difference_count_mismatch")
    if blocking.get("blocking_difference_count") != summary.get("blocking_difference_count"):
        errors.append("summary_blocking_difference_count_mismatch")
    derived_blocking = _derive_blocking_differences_from_case_payloads(cases)
    if blocking.get("blocking_difference_count") != len(derived_blocking):
        errors.append("blocking_difference_count_not_derived_from_cases")
        errors.extend(
            f"derived_blocking_difference:{item.get('reason')}"
            for item in derived_blocking
            if isinstance(item, dict)
        )
    if _sha256_canonical_json(blocking.get("blocking_differences", [])) != _sha256_canonical_json(derived_blocking):
        errors.append("blocking_differences_not_derived_from_cases")
    if expected.get("expected_difference_count") != len(expected.get("expected_differences", [])):
        errors.append("expected_difference_count_mismatch")
    derived_expected = _derive_expected_differences_from_case_payloads(cases)
    if expected.get("expected_difference_count") != len(derived_expected):
        errors.append("expected_difference_count_not_derived_from_cases")
    if _sha256_canonical_json(expected.get("expected_differences", [])) != _sha256_canonical_json(derived_expected):
        errors.append("expected_differences_not_derived_from_cases")
    unexpected_counts = _derive_unexpected_difference_counts(cases, derived_expected)
    for key, expected_value in unexpected_counts.items():
        if summary.get(key) != expected_value:
            errors.append(f"summary_field_mismatch:{key}")
    if projection.get("projection_validator_passed_count") != summary.get("projection_validator_passed_count"):
        errors.append("projection_validator_passed_count_mismatch")
    derived_projection_results = [
        {
            "case_id": case.get("case_id"),
            "projection_validator_passed": case.get("new", {}).get("projection_validator_passed"),
            "projection_validation_errors": case.get("new", {}).get("projection_validation_errors", []),
            "final_patch_sha256": case.get("new", {}).get("final_patch_sha256"),
            "final_diff_sha256": case.get("new", {}).get("final_diff_sha256"),
            "final_patch_hygiene_report_digest": _sha256_canonical_json(
                case.get("new", {}).get("final_patch_hygiene_report")
            ),
            "final_patch_hygiene_binding": _public_hygiene_binding_summary(
                case.get("new", {}).get("final_patch_hygiene_report", {}),
                final_patch_sha256=case.get("new", {}).get("final_patch_sha256"),
                final_diff_sha256=case.get("new", {}).get("final_diff_sha256"),
            ),
        }
        for case in cases
    ]
    if _sha256_canonical_json(projection.get("case_projection_results", [])) != _sha256_canonical_json(
        derived_projection_results
    ):
        errors.append("projection_case_results_not_derived_from_cases")
    errors.extend(_validate_case_record_bindings(cases))
    if test_report.get("stage16f4_focused_tests_status") not in {"passed", "not_run_in_helper"}:
        errors.append("stage16f4_test_report_status_invalid")
    errors.extend(_scan_public_evidence_for_leaks(evidence_path))
    errors.extend(_find_forbidden_patch_audit_fields_in_public_json(evidence_path))

    if assert_complete:
        required = {
            "stage16f4_complete": True,
            "status": "passed",
            "ready_for_stage16f5": True,
            "public_path_leak_scan_passed": True,
            "blocking_difference_count": 0,
            "public_raw_patch_audit_field_count": 0,
            "non_verl_policy_loss_candidate_count": 0,
            "non_verl_formal_online_rl_eligible_count": 0,
            "patch_hygiene_policy_difference_count": 0,
            "resolved_verifier_plan_unexpected_difference_count": 0,
            "tool_schema_unexpected_difference_count": 0,
            "public_environment_unexpected_difference_count": 0,
        }
        for key, expected_value in required.items():
            if summary.get(key) != expected_value:
                errors.append(f"acceptance_field_mismatch:{key}")
        minimums = {
            "parity_task_count": 3,
            "run_task_completed_count": 3,
            "run_episode_task_completed_count": 3,
            "accepted_case_count": 1,
            "rejected_case_count": 1,
            "public_feedback_case_count": 1,
            "patch_hygiene_case_count": 1,
            "nonempty_cleaned_patch_case_count": 1,
            "public_feedback_observed_case_count": 1,
            "final_verifier_accepted_case_count": 1,
            "final_verifier_rejected_case_count": 1,
        }
        for key, minimum in minimums.items():
            if int(summary.get(key, 0) or 0) < minimum:
                errors.append(f"acceptance_minimum_not_met:{key}")
        if summary.get("projection_validator_passed_count") != summary.get("run_episode_task_completed_count"):
            errors.append("projection_validator_count_not_equal_completed_new_runs")
    if errors:
        message = "; ".join(sorted(dict.fromkeys(errors)))
        if assert_complete:
            raise Stage16F4ParityError(message)
        return json.dumps(
            {"passed": False, "error_count": len(errors), "errors": sorted(dict.fromkeys(errors))},
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
    return json.dumps(
        {"passed": True, "error_count": 0, "stage16f4_complete": summary.get("stage16f4_complete")},
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    )


def _case_record(
    *,
    case: Stage16F4ParityCase,
    old_run_dir: Path,
    new_run_dir: Path,
) -> dict[str, Any]:
    old = _old_run_projection(old_run_dir)
    new = _new_run_projection(new_run_dir)
    expected_differences = _expected_differences(case, old, new)
    blocking_differences = _blocking_differences(case, old, new)
    return {
        "schema_version": "repo_harness_stage16f4_case_record_v0",
        "case_id": case.case_id,
        "task_ref": _public_ref("task", case.task_path),
        "config_ref": _public_ref("run-config", case.config_path),
        "coverage_tags": list(case.coverage_tags),
        "old_run_ref": _run_ref("old", case.old_run_id),
        "new_run_ref": _run_ref("new", case.new_run_id),
        "old": old,
        "new": new,
        "expected_differences": expected_differences,
        "blocking_differences": blocking_differences,
        "case_passed": not blocking_differences,
    }


def _old_run_projection(run_dir: Path) -> dict[str, Any]:
    metrics = _read_optional_json(run_dir / "metrics.json") or {}
    verifier = _read_optional_json(run_dir / "verifier.json") or {}
    reward = _read_optional_json(run_dir / "reward.json") or {}
    hygiene = _public_patch_hygiene(_read_optional_json(run_dir / "final_patch_hygiene_report.json") or {})
    final_patch = _read_optional_text(run_dir / "final.patch")
    final_diff = _read_optional_text(run_dir / "final.diff")
    run_config_facts = _read_optional_json(run_dir / "run_config_facts.json") or {}
    feedback = _public_feedback_observation(run_dir)
    return {
        "entrypoint": "run_task",
        "run_completed": bool(metrics),
        "run_outcome": metrics.get("run_outcome"),
        "final_verifier_status": metrics.get("final_verifier_status"),
        "final_verifier_accepted": verifier.get("accepted"),
        "reward_score": reward.get("final_reward"),
        "invalid_for_training": reward.get("invalid_for_training"),
        "invalid_reason": reward.get("invalid_reason"),
        "test_feedback_policy": run_config_facts.get("test_feedback_policy"),
        "feedback_tests_passed_policy": run_config_facts.get("feedback_tests_passed_policy"),
        "scaffold_id": run_config_facts.get("scaffold_id"),
        "tool_policy": run_config_facts.get("allowed_tools_policy"),
        "tool_registry_digest": None,
        "tool_schema_snapshot_digest": None,
        "allowed_tool_names_digest": None,
        "public_environment_context_digest": run_config_facts.get("public_environment_context_digest"),
        "resolved_verifier_plan_digest": _sha256_canonical_json(_read_optional_json(run_dir / "resolved_verifier_plan.json")),
        "final_patch_sha256": _sha256_text(final_patch),
        "final_diff_sha256": _sha256_text(final_diff),
        "final_patch_hygiene_report": hygiene,
        "cleaned_patch_empty": hygiene.get("cleaned_patch_empty"),
        "nonempty_cleaned_patch_observed": hygiene.get("cleaned_patch_empty") is False,
        "public_feedback_observed": feedback["observed"],
        "public_feedback_tool_call_id_or_event_ref": feedback["event_ref"],
        "public_feedback_observation_digest": feedback["observation_digest"],
        "training_view_available": False,
        "generation_records_available": False,
        "response_logprobs_available": False,
        "formal_online_rl_eligible": False,
        "policy_loss_candidate": False,
    }


def _new_run_projection(run_dir: Path) -> dict[str, Any]:
    projection_dir = run_dir / "compat_projection"
    try:
        validation_report = validate_run_episode_compat_projection(projection_dir, assert_complete=True)
    except ProjectionValidationError as exc:
        validation_report = {
            "projection_complete": False,
            "errors": [str(exc)],
        }
    manifest = _read_optional_json(projection_dir / "compat_projection_manifest.json") or {}
    status = _read_optional_json(projection_dir / "compat_projection_status.json") or {}
    verifier = _read_optional_json(projection_dir / "verifier_summary.json") or {}
    reward = _read_optional_json(projection_dir / "reward_summary.json") or {}
    metrics = _read_optional_json(projection_dir / "metrics.json") or {}
    route = _read_optional_json(projection_dir / "provider_route_qualification.json") or {}
    training_view = _read_optional_json(projection_dir / "training_view_projection.json") or {}
    generation_records = _read_optional_json(projection_dir / "generation_records_projection.json") or {}
    hygiene = _read_optional_json(projection_dir / "final_patch_hygiene_report.json") or {}
    feedback = _public_feedback_observation(run_dir)
    verifier_summary = verifier.get("verifier_summary") if isinstance(verifier.get("verifier_summary"), dict) else {}
    reward_summary = reward.get("reward_summary") if isinstance(reward.get("reward_summary"), dict) else {}
    return {
        "entrypoint": "run_episode_task",
        "run_completed": bool(status),
        "run_outcome": metrics.get("run_outcome"),
        "final_verifier_status": verifier_summary.get("status"),
        "final_verifier_accepted": verifier_summary.get("accepted"),
        "reward_score": reward_summary.get("score"),
        "invalid_for_training": reward_summary.get("invalid_for_training"),
        "invalid_reason": reward_summary.get("invalid_reason"),
        "test_feedback_policy": manifest.get("test_feedback_policy"),
        "feedback_tests_passed_policy": manifest.get("feedback_tests_passed_policy"),
        "scaffold_id": (_read_optional_json(projection_dir / "run_config_projection.json") or {}).get("scaffold_id"),
        "tool_registry_digest": manifest.get("tool_registry_digest"),
        "tool_schema_snapshot_digest": manifest.get("tool_schema_snapshot_digest"),
        "allowed_tool_names_digest": manifest.get("allowed_tool_names_digest"),
        "public_environment_context_digest": manifest.get("public_environment_context_digest"),
        "resolved_verifier_plan_digest": manifest.get("resolved_verifier_plan_digest"),
        "final_patch_sha256": manifest.get("final_patch_sha256"),
        "final_diff_sha256": manifest.get("final_diff_sha256"),
        "final_patch_hygiene_report": hygiene,
        "cleaned_patch_empty": hygiene.get("cleaned_patch_empty"),
        "nonempty_cleaned_patch_observed": hygiene.get("cleaned_patch_empty") is False,
        "public_feedback_observed": feedback["observed"],
        "public_feedback_tool_call_id_or_event_ref": feedback["event_ref"],
        "public_feedback_observation_digest": feedback["observation_digest"],
        "provider_route": route.get("provider_route"),
        "llm_gateway_route": route.get("llm_gateway_route"),
        "formal_online_rl_eligible": route.get("formal_online_rl_eligible"),
        "policy_loss_candidate": route.get("policy_loss_candidate"),
        "training_view_available": bool(training_view),
        "generation_records_available": int(generation_records.get("record_count", 0) or 0) > 0,
        "response_logprobs_available": False,
        "projection_validator_passed": validation_report.get("projection_complete") is True,
        "projection_validation_errors": validation_report.get("errors", []),
    }


def _blocking_differences(
    case: Stage16F4ParityCase,
    old: dict[str, Any],
    new: dict[str, Any],
) -> list[dict[str, Any]]:
    differences: list[dict[str, Any]] = []
    if not old.get("run_completed"):
        differences.append(_difference(case, "old_run_not_completed"))
    if not new.get("run_completed"):
        differences.append(_difference(case, "new_run_not_completed"))
    if not new.get("projection_validator_passed"):
        differences.append(_difference(case, "new_projection_validator_failed"))
    if new.get("provider_route") != "verl" and new.get("policy_loss_candidate") is True:
        differences.append(_difference(case, "non_verl_route_policy_loss_candidate"))
    if new.get("provider_route") != "verl" and new.get("formal_online_rl_eligible") is True:
        differences.append(_difference(case, "non_verl_route_formal_online_rl_eligible"))
    for key in ("test_feedback_policy", "feedback_tests_passed_policy"):
        if old.get(key) is not None and new.get(key) is not None and old.get(key) != new.get(key):
            differences.append(_difference(case, f"{key}_unexpected_difference"))
    if _normalize_run_outcome(old.get("run_outcome")) != _normalize_run_outcome(new.get("run_outcome")):
        differences.append(
            _difference(
                case,
                "run_outcome_difference",
                detail={"old_run_outcome": old.get("run_outcome"), "new_run_outcome": new.get("run_outcome")},
            )
        )
    for key in ("invalid_for_training", "invalid_reason"):
        if old.get(key) != new.get(key):
            differences.append(
                _difference(
                    case,
                    f"{key}_difference",
                    detail={f"old_{key}": old.get(key), f"new_{key}": new.get(key)},
                )
            )
    if not _float_equal(old.get("reward_score"), new.get("reward_score")):
        differences.append(
            _difference(
                case,
                "reward_score_difference",
                detail={"old_reward_score": old.get("reward_score"), "new_reward_score": new.get("reward_score")},
            )
        )
    for key in ("final_patch_sha256", "final_diff_sha256"):
        if old.get(key) != new.get(key):
            differences.append(
                _difference(
                    case,
                    f"{key}_difference",
                    detail={f"old_{key}": old.get(key), f"new_{key}": new.get(key)},
                )
            )
    if old.get("public_feedback_observed") != new.get("public_feedback_observed"):
        differences.append(_difference(case, "public_feedback_observed_difference"))
    if (
        old.get("public_feedback_observed") is True
        and new.get("public_feedback_observed") is True
        and old.get("public_feedback_observation_digest") != new.get("public_feedback_observation_digest")
    ):
        differences.append(_difference(case, "public_feedback_observation_digest_difference"))
    if (
        old.get("cleaned_patch_empty") is not None
        and new.get("cleaned_patch_empty") is not None
        and old.get("cleaned_patch_empty") != new.get("cleaned_patch_empty")
    ):
        differences.append(_difference(case, "patch_hygiene_cleaned_patch_empty_difference"))
    old_hygiene = _hygiene_semantic_projection(old.get("final_patch_hygiene_report"))
    new_hygiene = _hygiene_semantic_projection(new.get("final_patch_hygiene_report"))
    if old_hygiene != new_hygiene:
        differences.append(
            _difference(
                case,
                "patch_hygiene_report_semantic_difference",
                detail={
                    "old_hygiene_digest": _sha256_canonical_json(old_hygiene),
                    "new_hygiene_digest": _sha256_canonical_json(new_hygiene),
                    "changed_hygiene_fields": _changed_hygiene_fields(old_hygiene, new_hygiene),
                },
            )
        )
    if old.get("final_verifier_accepted") != new.get("final_verifier_accepted"):
        differences.append(
            _difference(
                case,
                "final_verifier_acceptance_difference",
                detail={
                    "old_final_verifier_accepted": old.get("final_verifier_accepted"),
                    "new_final_verifier_accepted": new.get("final_verifier_accepted"),
                },
            )
        )
    return differences


def _expected_differences(
    case: Stage16F4ParityCase,
    old: dict[str, Any],
    new: dict[str, Any],
) -> list[dict[str, Any]]:
    differences: list[dict[str, Any]] = []
    if old.get("training_view_available") != new.get("training_view_available"):
        differences.append(_difference(case, "new_entrypoint_has_training_view_projection"))
    if old.get("generation_records_available") != new.get("generation_records_available"):
        differences.append(_difference(case, "new_entrypoint_has_generation_records_projection"))
    if old.get("resolved_verifier_plan_digest") != new.get("resolved_verifier_plan_digest"):
        differences.append(
            _difference(
                case,
                "verifier_plan_digest_algorithm_difference",
                detail={
                    "old_resolved_verifier_plan_digest": old.get("resolved_verifier_plan_digest"),
                    "new_resolved_verifier_plan_digest": new.get("resolved_verifier_plan_digest"),
                },
            )
        )
    if old.get("public_environment_context_digest") != new.get("public_environment_context_digest"):
        differences.append(
            _difference(
                case,
                "legacy_public_environment_digest_projection_missing_or_different",
                detail={
                    "old_public_environment_context_digest": old.get("public_environment_context_digest"),
                    "new_public_environment_context_digest": new.get("public_environment_context_digest"),
                },
            )
        )
    for key in ("tool_registry_digest", "tool_schema_snapshot_digest", "allowed_tool_names_digest"):
        if old.get(key) != new.get(key):
            differences.append(
                _difference(
                    case,
                    f"legacy_{key}_projection_missing_or_different",
                    detail={f"old_{key}": old.get(key), f"new_{key}": new.get(key)},
                )
            )
    return differences


def _write_stage16f4_evidence(output_path: Path, case_records: list[dict[str, Any]]) -> None:
    parity_report = {
        "schema_version": STAGE16F4_SCHEMA_VERSION,
        "stage": "16F.4",
        "cases": case_records,
        "case_count": len(case_records),
    }
    blocking_differences = [
        difference
        for case in case_records
        for difference in case.get("blocking_differences", [])
    ]
    expected_differences = [
        difference
        for case in case_records
        for difference in case.get("expected_differences", [])
    ]
    derived = _derive_summary_from_cases(case_records)
    unexpected_counts = _derive_unexpected_difference_counts(case_records, expected_differences)
    projection_report = {
        "schema_version": "repo_harness_stage16f4_projection_binding_report_v0",
        "projection_validator_passed_count": derived["projection_validator_passed_count"],
        "projection_validator_failed_count": derived["run_episode_task_completed_count"]
        - derived["projection_validator_passed_count"],
        "case_projection_results": [
            {
                "case_id": case["case_id"],
                "projection_validator_passed": case["new"].get("projection_validator_passed"),
                "projection_validation_errors": case["new"].get("projection_validation_errors", []),
                "final_patch_sha256": case["new"].get("final_patch_sha256"),
                "final_diff_sha256": case["new"].get("final_diff_sha256"),
                "final_patch_hygiene_report_digest": _sha256_canonical_json(
                    case["new"].get("final_patch_hygiene_report")
                ),
                "final_patch_hygiene_binding": _public_hygiene_binding_summary(
                    case["new"].get("final_patch_hygiene_report", {}),
                    final_patch_sha256=case["new"].get("final_patch_sha256"),
                    final_diff_sha256=case["new"].get("final_diff_sha256"),
                ),
            }
            for case in case_records
        ],
    }
    summary = {
        "schema_version": "repo_harness_stage16f4_acceptance_summary_v0",
        "status": "passed" if not blocking_differences else "failed",
        "stage16f4_complete": not blocking_differences,
        "ready_for_stage16f5": not blocking_differences,
        "stage16f3_input_status": "passed",
        "blocking_reasons": [difference["reason"] for difference in blocking_differences],
        "blocking_difference_count": len(blocking_differences),
        "public_path_leak_scan_passed": True,
        "public_raw_patch_audit_field_count": 0,
        "patch_hygiene_policy_difference_count": 0,
        **unexpected_counts,
        **derived,
    }
    input_manifest = {
        "schema_version": "repo_harness_stage16f4_parity_input_manifest_v0",
        "case_count": len(case_records),
        "cases": [
            {
                "case_id": case["case_id"],
                "task_ref": case["task_ref"],
                "config_ref": case["config_ref"],
                "old_run_ref": case["old_run_ref"],
                "new_run_ref": case["new_run_ref"],
            }
            for case in case_records
        ],
        "runtime_private_runs_status": "not_public_evidence",
    }
    test_report = {
        "schema_version": "repo_harness_stage16f4_test_report_v0",
        "stage16f4_focused_tests_status": "not_run_in_helper",
        "regression_status": "not_run_in_helper",
    }
    files = {
        "stage16f4_acceptance_summary.json": summary,
        "stage16f4_parity_input_manifest.json": input_manifest,
        "stage16f4_run_task_run_episode_parity_report.json": parity_report,
        "stage16f4_blocking_differences.json": {
            "schema_version": "repo_harness_stage16f4_blocking_differences_v0",
            "blocking_difference_count": len(blocking_differences),
            "blocking_differences": blocking_differences,
        },
        "stage16f4_expected_differences.json": {
            "schema_version": "repo_harness_stage16f4_expected_differences_v0",
            "expected_difference_count": len(expected_differences),
            "expected_differences": expected_differences,
        },
        "stage16f4_projection_binding_report.json": projection_report,
        "stage16f4_test_report.json": test_report,
    }
    for filename, payload in files.items():
        _write_json(output_path / filename, payload)


def _update_runtime_private_runs_status(output_path: Path, *, status: str) -> None:
    manifest_path = output_path / "stage16f4_parity_input_manifest.json"
    manifest = _read_json(manifest_path)
    manifest["runtime_private_runs_status"] = status
    _write_json(manifest_path, manifest)


def _derive_summary_from_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    run_task_completed = sum(1 for case in cases if case.get("old", {}).get("run_completed"))
    run_episode_completed = sum(1 for case in cases if case.get("new", {}).get("run_completed"))
    accepted = sum(
        1
        for case in cases
        if case.get("old", {}).get("final_verifier_accepted") is True
        and case.get("new", {}).get("final_verifier_accepted") is True
    )
    rejected = sum(
        1
        for case in cases
        if case.get("old", {}).get("final_verifier_accepted") is False
        and case.get("new", {}).get("final_verifier_accepted") is False
    )
    public_feedback = sum(
        1
        for case in cases
        if case.get("old", {}).get("public_feedback_observed") is True
        and case.get("new", {}).get("public_feedback_observed") is True
    )
    nonempty_patch = sum(
        1
        for case in cases
        if case.get("old", {}).get("nonempty_cleaned_patch_observed") is True
        and case.get("new", {}).get("nonempty_cleaned_patch_observed") is True
    )
    policy_loss = sum(
        1
        for case in cases
        if case.get("new", {}).get("policy_loss_candidate") is True
        and case.get("new", {}).get("provider_route") != "verl"
    )
    formal_eligible = sum(
        1
        for case in cases
        if case.get("new", {}).get("formal_online_rl_eligible") is True
        and case.get("new", {}).get("provider_route") != "verl"
    )
    patch_hygiene_difference = sum(
        1
        for case in cases
        if _hygiene_semantic_projection(case.get("old", {}).get("final_patch_hygiene_report"))
        != _hygiene_semantic_projection(case.get("new", {}).get("final_patch_hygiene_report"))
    )
    projection_passed = sum(1 for case in cases if case.get("new", {}).get("projection_validator_passed") is True)
    return {
        "case_records_digest": _sha256_canonical_json(cases),
        "parity_task_count": len(cases),
        "run_task_completed_count": run_task_completed,
        "run_episode_task_completed_count": run_episode_completed,
        "accepted_case_count": accepted,
        "rejected_case_count": rejected,
        "public_feedback_case_count": public_feedback,
        "patch_hygiene_case_count": nonempty_patch,
        "nonempty_cleaned_patch_case_count": nonempty_patch,
        "public_feedback_observed_case_count": public_feedback,
        "final_verifier_accepted_case_count": accepted,
        "final_verifier_rejected_case_count": rejected,
        "projection_validator_passed_count": projection_passed,
        "non_verl_policy_loss_candidate_count": policy_loss,
        "non_verl_formal_online_rl_eligible_count": formal_eligible,
        "patch_hygiene_policy_difference_count": patch_hygiene_difference,
    }


def _derive_unexpected_difference_counts(
    cases: list[dict[str, Any]],
    expected_differences: list[dict[str, Any]],
) -> dict[str, int]:
    expected_reasons_by_case = {
        (str(item.get("case_id")), str(item.get("reason")))
        for item in expected_differences
        if isinstance(item, dict)
    }
    resolved_verifier_unexpected = 0
    tool_schema_unexpected = 0
    public_environment_unexpected = 0
    for case in cases:
        case_id = str(case.get("case_id") or "unknown_case")
        old = case.get("old", {}) if isinstance(case.get("old"), dict) else {}
        new = case.get("new", {}) if isinstance(case.get("new"), dict) else {}
        if old.get("resolved_verifier_plan_digest") != new.get("resolved_verifier_plan_digest"):
            if (case_id, "verifier_plan_digest_algorithm_difference") not in expected_reasons_by_case:
                resolved_verifier_unexpected += 1
        if old.get("public_environment_context_digest") != new.get("public_environment_context_digest"):
            reason = "legacy_public_environment_digest_projection_missing_or_different"
            if (case_id, reason) not in expected_reasons_by_case:
                public_environment_unexpected += 1
        for key in ("tool_registry_digest", "tool_schema_snapshot_digest", "allowed_tool_names_digest"):
            if old.get(key) != new.get(key):
                reason = f"legacy_{key}_projection_missing_or_different"
                if (case_id, reason) not in expected_reasons_by_case:
                    tool_schema_unexpected += 1
    return {
        "resolved_verifier_plan_unexpected_difference_count": resolved_verifier_unexpected,
        "tool_schema_unexpected_difference_count": tool_schema_unexpected,
        "public_environment_unexpected_difference_count": public_environment_unexpected,
    }


def _derive_blocking_differences_from_case_payloads(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    differences: list[dict[str, Any]] = []
    for case_payload in cases:
        case = _case_identity_from_payload(case_payload)
        differences.extend(
            _blocking_differences(
                case,
                case_payload.get("old", {}) if isinstance(case_payload.get("old"), dict) else {},
                case_payload.get("new", {}) if isinstance(case_payload.get("new"), dict) else {},
            )
        )
    return differences


def _derive_expected_differences_from_case_payloads(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    differences: list[dict[str, Any]] = []
    for case_payload in cases:
        case = _case_identity_from_payload(case_payload)
        differences.extend(
            _expected_differences(
                case,
                case_payload.get("old", {}) if isinstance(case_payload.get("old"), dict) else {},
                case_payload.get("new", {}) if isinstance(case_payload.get("new"), dict) else {},
            )
        )
    return differences


def _case_identity_from_payload(case_payload: dict[str, Any]) -> Stage16F4ParityCase:
    return Stage16F4ParityCase(
        case_id=str(case_payload.get("case_id") or "unknown_case"),
        task_path="",
        config_path="",
        old_run_id="",
        new_run_id="",
    )


def _validate_case_record_bindings(cases: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for case in cases:
        case_id = str(case.get("case_id") or "unknown_case")
        for entry_name in ("old", "new"):
            entry = case.get(entry_name)
            if not isinstance(entry, dict):
                errors.append(f"case_entry_not_dict:{case_id}:{entry_name}")
                continue
            hygiene = entry.get("final_patch_hygiene_report")
            if isinstance(hygiene, dict):
                binding = _public_hygiene_binding_summary(
                    hygiene,
                    final_patch_sha256=entry.get("final_patch_sha256"),
                    final_diff_sha256=entry.get("final_diff_sha256"),
                )
                if binding.get("binding_status") != "passed":
                    errors.append(f"patch_hygiene_binding_failed:{case_id}:{entry_name}")
            else:
                errors.append(f"patch_hygiene_report_missing:{case_id}:{entry_name}")
            errors.extend(_validate_public_feedback_shape(case_id, entry_name, entry))
        new = case.get("new", {}) if isinstance(case.get("new"), dict) else {}
        if new.get("provider_route") != "verl" and new.get("formal_online_rl_eligible") is True:
            errors.append(f"non_verl_formal_online_rl_eligible:{case_id}")
    return errors


def _public_hygiene_binding_summary(
    hygiene: dict[str, Any],
    *,
    final_patch_sha256: Any,
    final_diff_sha256: Any,
) -> dict[str, Any]:
    unexpected_keys = sorted(set(hygiene) - _PUBLIC_PATCH_HYGIENE_KEYS)
    checks = {
        "public_key_set_safe": not unexpected_keys,
        "cleaned_patch_sha256_matches_final_patch": hygiene.get("cleaned_patch_sha256") == final_patch_sha256,
        "cleaned_diff_sha256_matches_final_diff": hygiene.get("cleaned_diff_sha256") == final_diff_sha256,
        "public_report_contains_raw_patch_false": hygiene.get("public_report_contains_raw_patch") is False,
        "training_target_patch_source_cleaned": hygiene.get("training_target_patch_source") == "cleaned_patch_projection",
    }
    return {
        "binding_status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "unexpected_public_hygiene_keys": unexpected_keys,
    }


def _hygiene_semantic_projection(report: Any) -> dict[str, Any]:
    if not isinstance(report, dict):
        return {}
    return {
        key: report.get(key)
        for key in sorted(_PUBLIC_PATCH_HYGIENE_KEYS)
    }


def _changed_hygiene_fields(left: dict[str, Any], right: dict[str, Any]) -> list[str]:
    return [
        key
        for key in sorted(set(left) | set(right))
        if left.get(key) != right.get(key)
    ]


def _validate_public_feedback_shape(case_id: str, entry_name: str, entry: dict[str, Any]) -> list[str]:
    observed = entry.get("public_feedback_observed")
    event_ref = entry.get("public_feedback_tool_call_id_or_event_ref")
    digest = entry.get("public_feedback_observation_digest")
    if observed is True:
        if not (isinstance(event_ref, str) and event_ref.startswith("event:")):
            return [f"public_feedback_event_ref_invalid:{case_id}:{entry_name}"]
        if not _is_sha256_hex(digest):
            return [f"public_feedback_digest_invalid:{case_id}:{entry_name}"]
    if observed is False and (event_ref is not None or digest is not None):
        return [f"public_feedback_unobserved_has_ref_or_digest:{case_id}:{entry_name}"]
    return []


def _is_sha256_hex(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _float_equal(left: Any, right: Any, *, tolerance: float = 1e-9) -> bool:
    if left is None or right is None:
        return left is right
    try:
        return abs(float(left) - float(right)) <= tolerance
    except (TypeError, ValueError):
        return False


def _normalize_run_outcome(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    mapping = {
        "success": "succeeded",
        "succeeded": "succeeded",
        "failure": "failed",
        "failed": "failed",
    }
    return mapping.get(text, text)


def _public_feedback_observation(run_dir: Path) -> dict[str, Any]:
    for line in _read_jsonl_lines(run_dir / "events.jsonl"):
        event_type = line.get("event_type")
        data = line.get("data") if isinstance(line.get("data"), dict) else {}
        if event_type == "tool_completed" and data.get("effective_tool_name") == "run_tests":
            observation = {
                "event_type": event_type,
                "content_preview": data.get("content_preview"),
                "status": data.get("status"),
                "error_type": data.get("error_type"),
            }
            return {
                "observed": True,
                "event_ref": f"event:{_sha256_canonical_json({'event_id': line.get('event_id')})}",
                "observation_digest": _sha256_canonical_json(observation),
            }
    return {"observed": False, "event_ref": None, "observation_digest": None}


def _difference(
    case: Stage16F4ParityCase,
    reason: str,
    *,
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "case_id": case.case_id,
        "reason": reason,
        "detail": detail or {},
    }


def _public_ref(kind: str, path: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "relative_path": path,
        "sha256": _sha256_text(Path(path).read_text(encoding="utf-8")),
    }


def _run_ref(kind: str, run_id: str) -> str:
    return f"stage16f4:{kind}:{_sha256_text(run_id)}"


def _public_patch_hygiene(report: dict[str, Any]) -> dict[str, Any]:
    public = {key: value for key, value in report.items() if key in _PUBLIC_PATCH_HYGIENE_KEYS}
    if public:
        public["projection_sanitization_status"] = "private_audit_fields_removed"
    return public


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_optional_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    return _read_json(path)


def _read_optional_text(path: Path) -> str | None:
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def _read_jsonl_lines(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    lines: list[dict[str, Any]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        try:
            payload = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            lines.append(payload)
    return lines


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _sha256_text(text: str | None) -> str | None:
    if text is None:
        return None
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_canonical_json(payload: Any) -> str | None:
    if payload is None:
        return None
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _scan_public_evidence_for_leaks(evidence_path: Path) -> list[str]:
    findings: list[str] = []
    for path in sorted(evidence_path.glob("stage16f4_*.json")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for marker in _FORBIDDEN_PUBLIC_MARKERS:
            if marker in text:
                findings.append(f"path_or_secret_leak:{path.name}:{marker}")
    return findings


def _find_forbidden_patch_audit_fields(payload: Any, *, path: str) -> list[str]:
    findings: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            child_path = f"{path}.{key}"
            if key in _FORBIDDEN_PUBLIC_PATCH_AUDIT_FIELDS:
                findings.append(f"forbidden_public_patch_audit_field:{child_path}")
            findings.extend(_find_forbidden_patch_audit_fields(value, path=child_path))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            findings.extend(_find_forbidden_patch_audit_fields(value, path=f"{path}[{index}]"))
    return findings


def _find_forbidden_patch_audit_fields_in_public_json(evidence_path: Path) -> list[str]:
    findings: list[str] = []
    for path in sorted(evidence_path.glob("stage16f4_*.json")):
        try:
            payload = _read_json(path)
        except json.JSONDecodeError:
            findings.append(f"public_json_not_parseable:{path.name}")
            continue
        findings.extend(_find_forbidden_patch_audit_fields(payload, path=path.name))
    return findings
