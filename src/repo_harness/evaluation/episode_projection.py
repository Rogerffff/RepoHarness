"""Stage 16F.3 run_episode compatibility projection.

This module writes a public-safe compatibility projection for runs produced by
``RepoHarnessRuntime.run_episode(real_episode)``.  The projection is deliberately
separate from the raw runtime run directory because the raw directory may
contain audit-only artifacts, runtime-private paths, or provider debug material.
"""

from __future__ import annotations

import json
import re
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from repo_harness.errors import RepoHarnessError
from repo_harness.execution import EpisodeExecutionSpec
from repo_harness.rl.episode import RepoHarnessEpisodeRequest, RepoHarnessEpisodeResult
from repo_harness.schema_base import stable_hash
from repo_harness.tasks import RunnableTask


PROJECTION_SCHEMA_VERSION = "repo_harness_stage16f3_compat_projection_v0"
PROJECTION_DIR_NAME = "compat_projection"
REQUIRED_PROJECTION_FILES = frozenset(
    {
        "task_projection.json",
        "run_config_projection.json",
        "episode_execution_spec_report.json",
        "public_environment_context_report.json",
        "provider_route_qualification.json",
        "training_view_projection.json",
        "generation_records_projection.json",
        "verifier_summary.json",
        "reward_summary.json",
        "metrics.json",
        "compat_projection_status.json",
        "final.patch",
        "final.diff",
        "final_patch_hygiene_report.json",
    }
)

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
_RUNTIME_PRIVATE_REF_PATTERN = re.compile(r"runtime-private:[a-z0-9_.:-]+:[0-9a-f]{64}")
_PUBLIC_PATCH_HYGIENE_KEYS = frozenset(
    {
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
    }
)
_FORBIDDEN_PUBLIC_PATCH_HYGIENE_KEYS = frozenset(
    {
        "raw_patch_sha256",
        "raw_diff_sha256",
        "raw_patch_ref",
        "raw_diff_ref",
        "raw_patch_nonempty",
        "raw_patch_visibility",
        "final_patch_ref",
        "final_diff_ref",
    }
)


class ProjectionValidationError(RepoHarnessError):
    """Raised when a Stage 16F.3 compatibility projection is incomplete."""


@dataclass(frozen=True)
class ProjectionWriteResult:
    projection_dir: Path
    manifest_path: Path
    validation_report: dict[str, Any]


def write_run_episode_compat_projection(
    *,
    run_dir: str | Path,
    task: RunnableTask,
    request: RepoHarnessEpisodeRequest,
    execution_spec: EpisodeExecutionSpec,
    result: RepoHarnessEpisodeResult,
    provider_route: str,
) -> ProjectionWriteResult:
    """Write sanitized run_task-compatible projection files for one episode."""

    run_dir_path = Path(run_dir)
    projection_dir = run_dir_path / PROJECTION_DIR_NAME
    projection_dir.mkdir(parents=True, exist_ok=True)

    route_qualification = _provider_route_qualification(
        provider_route=provider_route,
        request=request,
        result=result,
    )
    task_projection = _task_projection(task, execution_spec)
    spec_report = _execution_spec_report(execution_spec, request)
    verifier_summary = None if result.verifier_summary is None else result.verifier_summary.model_dump(mode="json")
    reward_summary = None if result.reward is None else {
        "score": result.reward.score,
        "invalid_for_training": result.reward.invalid_for_training,
        "invalid_reason": result.reward.invalid_reason,
        "audit_metadata_ref_present": result.reward.reward_metadata_ref is not None,
    }
    generation_records_projection = [
        {
            "model_call_id": record.model_call_id,
            "gateway_route": record.gateway_route,
            "inference_backend": record.inference_backend,
            "output_token_count": len(record.output_token_ids),
            "has_output_logprobs": record.output_logprobs is not None,
            "schema_version": record.schema_version,
        }
        for record in result.generation_records
    ]
    training_view_projection = {
        "schema_version": "repo_harness_stage16f3_training_view_projection_v0",
        "response_token_count": len(result.training_view.response_ids),
        "response_mask_count": len(result.training_view.response_mask),
        "response_span_count": len(result.training_view.response_spans),
        "route": result.training_view.extra_fields.get("repo_harness_llm_gateway_route"),
        "online_rl_eligible": result.training_view.online_rl_eligible,
        "reward_score": result.training_view.reward_score,
        "invalid_for_training": result.invalid_for_training,
        "invalid_for_online_rl": result.invalid_for_online_rl,
        "invalid_reason": result.status_reason,
    }
    status = {
        "schema_version": "repo_harness_stage16f3_projection_status_v0",
        "episode_id": result.episode_id,
        "run_id": result.run_id,
        "task_id": result.task_id,
        "status": result.status,
        "status_reason": result.status_reason,
        "invalid_for_training": result.invalid_for_training,
        "invalid_for_online_rl": result.invalid_for_online_rl,
        "formal_online_rl_eligible": route_qualification["formal_online_rl_eligible"],
        "policy_loss_candidate": route_qualification["policy_loss_candidate"],
    }
    metrics = {
        "schema_version": "repo_harness_stage16f3_metrics_projection_v0",
        "run_outcome": result.status,
        "status_reason": result.status_reason,
        "attempted_reward_score": result.attempted_reward_score,
        "invalid_for_training": result.invalid_for_training,
        "invalid_for_online_rl": result.invalid_for_online_rl,
    }
    final_patch_text = _read_required_text(run_dir_path / "final.patch")
    final_diff_text = _read_required_text(run_dir_path / "final.diff")
    final_patch_hygiene_report = _public_patch_hygiene_report(
        _read_required_json(run_dir_path / "final_patch_hygiene_report.json")
    )

    files = {
        "task_projection.json": task_projection,
        "run_config_projection.json": _run_config_projection(execution_spec, request),
        "episode_execution_spec_report.json": spec_report,
        "public_environment_context_report.json": {
            "schema_version": "repo_harness_stage16f3_public_environment_context_report_v0",
            "public_environment_context_digest": execution_spec.context_facts.public_environment_context_digest,
            "content_status": "digest_only",
        },
        "provider_route_qualification.json": route_qualification,
        "training_view_projection.json": training_view_projection,
        "generation_records_projection.json": {
            "schema_version": "repo_harness_stage16f3_generation_records_projection_v0",
            "record_count": len(generation_records_projection),
            "records": generation_records_projection,
            "generation_records_digest": stable_hash(
                [record.model_dump(mode="json") for record in result.generation_records]
            ),
        },
        "verifier_summary.json": {
            "schema_version": "repo_harness_stage16f3_verifier_summary_projection_v0",
            "verifier_summary": verifier_summary,
        },
        "reward_summary.json": {
            "schema_version": "repo_harness_stage16f3_reward_summary_projection_v0",
            "reward_summary": reward_summary,
        },
        "metrics.json": metrics,
        "compat_projection_status.json": status,
        "final.patch": final_patch_text,
        "final.diff": final_diff_text,
        "final_patch_hygiene_report.json": final_patch_hygiene_report,
    }
    for filename, payload in files.items():
        _write_projection_file(projection_dir / filename, payload)

    manifest = _manifest_payload(
        execution_spec=execution_spec,
        request=request,
        result=result,
        route_qualification=route_qualification,
        files=files,
        final_patch_text=final_patch_text,
        final_diff_text=final_diff_text,
        final_patch_hygiene_report=final_patch_hygiene_report,
    )
    manifest_path = projection_dir / "compat_projection_manifest.json"
    _write_json(manifest_path, manifest)
    validation_report = validate_run_episode_compat_projection(
        projection_dir,
        execution_spec=execution_spec,
        result=result,
        assert_complete=True,
    )
    _write_json(projection_dir / "projection_validation_report.json", validation_report)
    return ProjectionWriteResult(
        projection_dir=projection_dir,
        manifest_path=manifest_path,
        validation_report=validation_report,
    )


def validate_run_episode_compat_projection(
    projection_dir: str | Path,
    *,
    execution_spec: EpisodeExecutionSpec | None = None,
    result: RepoHarnessEpisodeResult | None = None,
    assert_complete: bool = False,
) -> dict[str, Any]:
    """Inspect a Stage 16F.3 projection and optionally fail closed."""

    projection_path = Path(projection_dir)
    manifest_path = projection_path / "compat_projection_manifest.json"
    errors: list[str] = []
    if not manifest_path.exists():
        errors.append("missing_compat_projection_manifest")
        report = _validation_report(projection_path, errors)
        if assert_complete:
            raise ProjectionValidationError("; ".join(errors))
        return report
    manifest = _read_json(manifest_path)
    required_fields = {
        "schema_version",
        "compat_projection_schema_version",
        "projection_created_from_run_episode",
        "episode_execution_spec_sha256",
        "episode_execution_spec_schema_version",
        "task_definition_sha256",
        "run_config_sha256",
        "tool_registry_digest",
        "tool_schema_snapshot_digest",
        "allowed_tool_names_digest",
        "budget_facts_digest",
        "public_environment_context_digest",
        "resolved_verifier_plan_digest",
        "test_feedback_policy",
        "feedback_tests_passed_policy",
        "permission_mode",
        "network_policy",
        "provider_route",
        "provider_route_policy",
        "llm_gateway_route",
        "run_mode_hint",
        "initial_messages_digest",
        "raw_prompt_digest",
        "formal_online_rl_eligible",
        "policy_loss_candidate",
        "projection_source_episode_id",
        "projection_source_run_id",
        "projection_source_result_digest",
        "projection_source_training_view_digest",
        "projection_source_generation_records_digest",
        "projection_file_digests",
        "final_patch_sha256",
        "final_diff_sha256",
        "final_patch_hygiene_report_sha256",
    }
    missing = sorted(field for field in required_fields if field not in manifest)
    errors.extend(f"missing_manifest_field:{field}" for field in missing)
    if manifest.get("schema_version") != PROJECTION_SCHEMA_VERSION:
        errors.append("projection_schema_version_mismatch")
    file_digests = manifest.get("projection_file_digests")
    if not isinstance(file_digests, dict):
        errors.append("projection_file_digests_not_mapping")
    else:
        missing_digest_files = sorted(REQUIRED_PROJECTION_FILES - set(file_digests))
        errors.extend(f"missing_projection_file_digest:{filename}" for filename in missing_digest_files)
        extra_digest_files = sorted(set(file_digests) - REQUIRED_PROJECTION_FILES)
        errors.extend(f"unexpected_projection_file_digest:{filename}" for filename in extra_digest_files)
        for filename in sorted(REQUIRED_PROJECTION_FILES):
            file_path = projection_path / filename
            if not file_path.exists():
                errors.append(f"missing_projection_file:{filename}")
        for filename, expected_digest in sorted(file_digests.items()):
            file_path = projection_path / filename
            if not file_path.exists():
                continue
            actual_digest = _projection_file_digest(file_path)
            if actual_digest != expected_digest:
                errors.append(f"projection_file_digest_mismatch:{filename}")
    errors.extend(_validate_final_patch_projection(projection_path, manifest))
    errors.extend(_validate_projection_training_qualification(projection_path, manifest))
    if execution_spec is not None:
        if manifest.get("episode_execution_spec_sha256") != execution_spec.spec_payload_sha256:
            errors.append("episode_execution_spec_sha256_mismatch")
        if manifest.get("resolved_verifier_plan_digest") != execution_spec.verifier_facts.resolved_verifier_plan_digest:
            errors.append("resolved_verifier_plan_digest_mismatch")
        if manifest.get("tool_registry_digest") != execution_spec.tool_facts.tool_registry_digest:
            errors.append("tool_registry_digest_mismatch")
        if manifest.get("run_config_sha256") != execution_spec.run_config_facts.run_config_sha256:
            errors.append("run_config_sha256_mismatch")
        if manifest.get("task_definition_sha256") != execution_spec.task_facts.task_definition_sha256:
            errors.append("task_definition_sha256_mismatch")
    if result is not None:
        if manifest.get("projection_source_episode_id") != result.episode_id:
            errors.append("projection_source_episode_id_mismatch")
        expected_result_digest = _result_digest(result)
        if manifest.get("projection_source_result_digest") != expected_result_digest:
            errors.append("projection_source_result_digest_mismatch")
        if bool(manifest.get("formal_online_rl_eligible")) != (
            not result.invalid_for_training and not result.invalid_for_online_rl and manifest.get("provider_route") == "verl"
        ):
            errors.append("formal_online_rl_eligibility_mismatch")
    leak_findings = _scan_public_projection_for_leaks(projection_path)
    errors.extend(f"path_or_secret_leak:{finding}" for finding in leak_findings)
    report = _validation_report(projection_path, errors)
    if assert_complete and errors:
        raise ProjectionValidationError("; ".join(errors))
    return report


def _validate_projection_training_qualification(
    projection_path: Path,
    manifest: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    route_report = _read_optional_json(projection_path / "provider_route_qualification.json")
    status_report = _read_optional_json(projection_path / "compat_projection_status.json")
    training_view_report = _read_optional_json(projection_path / "training_view_projection.json")

    provider_route = manifest.get("provider_route")
    llm_gateway_route = manifest.get("llm_gateway_route")
    manifest_formal = bool(manifest.get("formal_online_rl_eligible"))
    manifest_policy_loss = bool(manifest.get("policy_loss_candidate"))

    if route_report is not None:
        if route_report.get("provider_route") != provider_route:
            errors.append("provider_route_qualification_provider_route_mismatch")
        if route_report.get("llm_gateway_route") != llm_gateway_route:
            errors.append("provider_route_qualification_llm_gateway_route_mismatch")
        if bool(route_report.get("formal_online_rl_eligible")) != manifest_formal:
            errors.append("provider_route_qualification_formal_online_rl_mismatch")
        if bool(route_report.get("policy_loss_candidate")) != manifest_policy_loss:
            errors.append("provider_route_qualification_policy_loss_mismatch")
    if status_report is not None:
        if bool(status_report.get("formal_online_rl_eligible")) != manifest_formal:
            errors.append("projection_status_formal_online_rl_mismatch")
        if bool(status_report.get("policy_loss_candidate")) != manifest_policy_loss:
            errors.append("projection_status_policy_loss_mismatch")
    if provider_route != "verl" or llm_gateway_route != "verl":
        if manifest_formal:
            errors.append("non_verl_route_marked_formal_online_rl_eligible")
        if manifest_policy_loss:
            errors.append("non_verl_route_marked_policy_loss_candidate")
        if route_report is not None and bool(route_report.get("policy_loss_candidate")):
            errors.append("non_verl_route_report_marked_policy_loss_candidate")
        if status_report is not None and bool(status_report.get("policy_loss_candidate")):
            errors.append("non_verl_status_marked_policy_loss_candidate")
        if training_view_report is not None and bool(training_view_report.get("online_rl_eligible")):
            errors.append("non_verl_training_view_marked_online_rl_eligible")
    if manifest_policy_loss and not manifest_formal:
        errors.append("policy_loss_candidate_without_formal_online_rl_eligible")
    if status_report is not None:
        expected_formal = (
            provider_route == "verl"
            and llm_gateway_route == "verl"
            and not bool(status_report.get("invalid_for_training"))
            and not bool(status_report.get("invalid_for_online_rl"))
        )
        if manifest_formal != expected_formal:
            errors.append("formal_online_rl_eligibility_status_mismatch")
    return errors


def _validate_final_patch_projection(
    projection_path: Path,
    manifest: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    patch_path = projection_path / "final.patch"
    diff_path = projection_path / "final.diff"
    hygiene_path = projection_path / "final_patch_hygiene_report.json"
    if not patch_path.exists() or not diff_path.exists() or not hygiene_path.exists():
        return errors

    patch_text = patch_path.read_text(encoding="utf-8")
    diff_text = diff_path.read_text(encoding="utf-8")
    hygiene_report = _read_json(hygiene_path)
    if not isinstance(hygiene_report, dict):
        errors.append("final_patch_hygiene_report_not_mapping")
        return errors

    patch_sha256 = _sha256_text(patch_text)
    diff_sha256 = _sha256_text(diff_text)
    hygiene_sha256 = _sha256_canonical_json(hygiene_report)
    if manifest.get("final_patch_sha256") != patch_sha256:
        errors.append("final_patch_sha256_mismatch")
    if manifest.get("final_diff_sha256") != diff_sha256:
        errors.append("final_diff_sha256_mismatch")
    if manifest.get("final_patch_hygiene_report_sha256") != hygiene_sha256:
        errors.append("final_patch_hygiene_report_sha256_mismatch")
    if hygiene_report.get("cleaned_patch_sha256") != patch_sha256:
        errors.append("final_patch_hygiene_cleaned_patch_sha256_mismatch")
    if hygiene_report.get("cleaned_diff_sha256") != diff_sha256:
        errors.append("final_patch_hygiene_cleaned_diff_sha256_mismatch")
    if hygiene_report.get("training_target_patch_source") != "cleaned_patch_projection":
        errors.append("final_patch_hygiene_training_target_source_mismatch")
    if hygiene_report.get("public_report_contains_raw_patch") is not False:
        errors.append("final_patch_hygiene_raw_patch_visibility_mismatch")
    forbidden_hygiene_keys = sorted(set(hygiene_report) & _FORBIDDEN_PUBLIC_PATCH_HYGIENE_KEYS)
    errors.extend(f"forbidden_public_patch_hygiene_key:{key}" for key in forbidden_hygiene_keys)

    source_run_dir = projection_path.parent
    source_artifacts = {
        "final.patch": (source_run_dir / "final.patch", patch_sha256),
        "final.diff": (source_run_dir / "final.diff", diff_sha256),
    }
    for filename, (source_path, expected_sha256) in source_artifacts.items():
        if not source_path.exists():
            errors.append(f"missing_source_patch_artifact:{filename}")
            continue
        actual_sha256 = (
            _sha256_canonical_json(_read_json(source_path))
            if filename.endswith(".json")
            else _sha256_text(source_path.read_text(encoding="utf-8"))
        )
        if actual_sha256 != expected_sha256:
            errors.append(f"source_patch_artifact_mismatch:{filename}")
    source_hygiene_path = source_run_dir / "final_patch_hygiene_report.json"
    if not source_hygiene_path.exists():
        errors.append("missing_source_patch_artifact:final_patch_hygiene_report.json")
    else:
        source_public_hygiene = _public_patch_hygiene_report(_read_json(source_hygiene_path))
        if _sha256_canonical_json(source_public_hygiene) != hygiene_sha256:
            errors.append("source_patch_artifact_mismatch:final_patch_hygiene_report.json")
    return errors


def _manifest_payload(
    *,
    execution_spec: EpisodeExecutionSpec,
    request: RepoHarnessEpisodeRequest,
    result: RepoHarnessEpisodeResult,
    route_qualification: dict[str, Any],
    files: dict[str, Any],
    final_patch_text: str,
    final_diff_text: str,
    final_patch_hygiene_report: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": PROJECTION_SCHEMA_VERSION,
        "compat_projection_schema_version": PROJECTION_SCHEMA_VERSION,
        "projection_created_from_run_episode": True,
        "episode_execution_spec_sha256": execution_spec.spec_payload_sha256,
        "episode_execution_spec_schema_version": execution_spec.schema_version,
        "task_definition_sha256": execution_spec.task_facts.task_definition_sha256,
        "run_config_sha256": execution_spec.run_config_facts.run_config_sha256,
        "tool_registry_digest": execution_spec.tool_facts.tool_registry_digest,
        "tool_schema_snapshot_digest": execution_spec.tool_facts.tool_schema_snapshot_digest,
        "allowed_tool_names_digest": stable_hash(execution_spec.allowed_tool_names),
        "budget_facts_digest": stable_hash(execution_spec.budget_facts.model_dump(mode="json")),
        "public_environment_context_digest": execution_spec.context_facts.public_environment_context_digest,
        "resolved_verifier_plan_digest": execution_spec.verifier_facts.resolved_verifier_plan_digest,
        "test_feedback_policy": execution_spec.feedback_facts.test_feedback_policy,
        "feedback_tests_passed_policy": execution_spec.feedback_facts.feedback_tests_passed_policy,
        "permission_mode": execution_spec.run_config_facts.permission_mode,
        "network_policy": execution_spec.run_config_facts.network_policy,
        "run_mode_hint": execution_spec.run_config_facts.run_mode_hint,
        "run_mode": request.run_mode,
        "initial_messages_digest": execution_spec.context_facts.initial_messages_digest,
        "raw_prompt_digest": execution_spec.context_facts.raw_prompt_digest,
        "provider_route_policy": [
            policy.model_dump(mode="json")
            for policy in request.provider_route_policy_examples
        ],
        "provider_route": route_qualification["provider_route"],
        "llm_gateway_route": request.llm_gateway_route,
        "formal_online_rl_eligible": route_qualification["formal_online_rl_eligible"],
        "policy_loss_candidate": route_qualification["policy_loss_candidate"],
        "projection_source_episode_id": result.episode_id,
        "projection_source_run_id": result.run_id,
        "projection_source_result_digest": _result_digest(result),
        "projection_source_training_view_digest": stable_hash(
            result.training_view.model_dump(mode="json", exclude_none=True)
        ),
        "projection_source_generation_records_digest": stable_hash(
            [record.model_dump(mode="json") for record in result.generation_records]
        ),
        "final_patch_sha256": _sha256_text(final_patch_text),
        "final_diff_sha256": _sha256_text(final_diff_text),
        "final_patch_hygiene_report_sha256": _sha256_canonical_json(final_patch_hygiene_report),
        "projection_file_digests": {
            filename: stable_hash(payload)
            for filename, payload in sorted(files.items())
        },
    }


def _public_patch_hygiene_report(report: dict[str, Any]) -> dict[str, Any]:
    public_report = {
        key: value
        for key, value in report.items()
        if key in _PUBLIC_PATCH_HYGIENE_KEYS
    }
    public_report["projection_sanitization_status"] = "private_audit_fields_removed"
    return public_report


def _task_projection(task: RunnableTask, execution_spec: EpisodeExecutionSpec) -> dict[str, Any]:
    return {
        "schema_version": "repo_harness_stage16f3_task_projection_v0",
        "task_id": task.task_id,
        "task_version": task.task_version,
        "dataset_name": task.dataset_name,
        "dataset_split": task.metadata.get("dataset_split"),
        "issue_statement": task.issue_statement,
        "expected_files": list(task.expected_files),
        "task_definition_sha256": execution_spec.task_facts.task_definition_sha256,
        "base_commit": execution_spec.task_facts.base_commit,
    }


def _execution_spec_report(
    execution_spec: EpisodeExecutionSpec,
    request: RepoHarnessEpisodeRequest,
) -> dict[str, Any]:
    return {
        "schema_version": "repo_harness_stage16f3_episode_execution_spec_report_v0",
        "spec_id": execution_spec.spec_id,
        "spec_payload_sha256": execution_spec.spec_payload_sha256,
        "task_id": execution_spec.task_id,
        "run_id": execution_spec.run_id,
        "task_definition_sha256": execution_spec.task_facts.task_definition_sha256,
        "run_config_sha256": execution_spec.run_config_facts.run_config_sha256,
        "initial_messages_digest": execution_spec.context_facts.initial_messages_digest,
        "raw_prompt_digest": execution_spec.context_facts.raw_prompt_digest,
        "tool_registry_digest": execution_spec.tool_facts.tool_registry_digest,
        "tool_schema_snapshot_digest": execution_spec.tool_facts.tool_schema_snapshot_digest,
        "allowed_tool_names": list(execution_spec.allowed_tool_names),
        "resolved_verifier_plan_digest": execution_spec.verifier_facts.resolved_verifier_plan_digest,
        "test_feedback_policy": execution_spec.feedback_facts.test_feedback_policy,
        "feedback_tests_passed_policy": execution_spec.feedback_facts.feedback_tests_passed_policy,
        "raw_prompt_source": request.raw_prompt_source,
        "episode_execution_spec_ref": request.episode_execution_spec_ref,
    }


def _run_config_projection(
    execution_spec: EpisodeExecutionSpec,
    request: RepoHarnessEpisodeRequest,
) -> dict[str, Any]:
    return {
        "schema_version": "repo_harness_stage16f3_run_config_projection_v0",
        "run_id": execution_spec.run_id,
        "run_config_sha256": execution_spec.run_config_facts.run_config_sha256,
        "scaffold_id": execution_spec.run_config_facts.scaffold_id,
        "permission_mode": execution_spec.run_config_facts.permission_mode,
        "network_policy": execution_spec.run_config_facts.network_policy,
        "run_mode_hint": execution_spec.run_config_facts.run_mode_hint,
        "request_run_mode": request.run_mode,
        "output_dir_status": "not_projected",
    }


def _provider_route_qualification(
    *,
    provider_route: str,
    request: RepoHarnessEpisodeRequest,
    result: RepoHarnessEpisodeResult,
) -> dict[str, Any]:
    formal_online_rl_eligible = (
        provider_route == "verl"
        and request.llm_gateway_route == "verl"
        and not result.invalid_for_training
        and not result.invalid_for_online_rl
    )
    return {
        "schema_version": "repo_harness_stage16f3_provider_route_qualification_v0",
        "provider_route": provider_route,
        "llm_gateway_route": request.llm_gateway_route,
        "result_invalid_for_training": result.invalid_for_training,
        "result_invalid_for_online_rl": result.invalid_for_online_rl,
        "formal_online_rl_eligible": formal_online_rl_eligible,
        "policy_loss_candidate": formal_online_rl_eligible,
        "qualification_reason": (
            "route_verl_formal_online_rl_candidate"
            if formal_online_rl_eligible
            else "non_verl_or_diagnostic_route_not_policy_loss_candidate"
        ),
    }


def _scan_public_projection_for_leaks(projection_dir: Path) -> list[str]:
    findings: list[str] = []
    for path in sorted(projection_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix not in {".json", ".jsonl", ".md", ".txt", ".log", ".yaml", ".yml", ".patch", ".diff"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        normalized_text = _RUNTIME_PRIVATE_REF_PATTERN.sub("runtime-private:<kind>:<sha256>", text)
        for marker in _FORBIDDEN_PUBLIC_MARKERS:
            if marker in normalized_text:
                findings.append(f"{path.relative_to(projection_dir)}:{marker}")
    return findings


def _result_digest(result: RepoHarnessEpisodeResult) -> str:
    return stable_hash(result.model_dump(mode="json", exclude_none=True))


def _validation_report(projection_path: Path, errors: list[str]) -> dict[str, Any]:
    return {
        "schema_version": "repo_harness_stage16f3_projection_validation_report_v0",
        "projection_dir_name": projection_path.name,
        "projection_complete": not errors,
        "error_count": len(errors),
        "errors": errors,
    }


def _write_projection_file(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
        return
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _write_json(path: Path, payload: Any) -> None:
    _write_projection_file(path, payload)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_optional_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    return _read_json(path)


def _read_required_text(path: Path) -> str:
    if not path.exists():
        raise ProjectionValidationError(f"missing source patch artifact: {path.name}")
    return path.read_text(encoding="utf-8")


def _read_required_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ProjectionValidationError(f"missing source patch artifact: {path.name}")
    payload = _read_json(path)
    if not isinstance(payload, dict):
        raise ProjectionValidationError(f"source patch artifact is not a JSON object: {path.name}")
    return payload


def _projection_file_digest(path: Path) -> str:
    if path.suffix in {".patch", ".diff"}:
        return stable_hash(path.read_text(encoding="utf-8"))
    return stable_hash(_read_json(path))


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_canonical_json(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return _sha256_text(encoded)
