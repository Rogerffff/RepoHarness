"""第二版 run facts 写入器。"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from repo_harness.config import RunConfig
from repo_harness.context.budget import resolve_context_budget
from repo_harness.context.schemas import ContextPolicySnapshot
from repo_harness.evaluation.schemas import BaselineResult, ResolvedFeedbackPolicyFacts
from repo_harness.run_metadata.schemas import (
    EnvironmentFingerprint,
    ExportReadinessFacts,
    FailureCategory,
    FailureDiagnostics,
    FailureType,
    RunConfigFacts,
    RunConfigFactsRef,
    RunMetadata,
    RunMetadataRef,
    SourceCheckoutFacts,
    ToolProtocolFacts,
)
from repo_harness.schema_versions import OUTCOME_POLICY_VERSION, REWARD_VERSION
from repo_harness.schema_base import stable_hash
from repo_harness.scaffolds import ScaffoldDefinition, build_scaffold, resolve_feedback_policy
from repo_harness.tasks import TaskDefinition
from repo_harness.tasks.command_policy import COMMAND_POLICY_VERSION
from repo_harness.trajectory import verify_artifact_manifest
from repo_harness.trajectory import ArtifactRef


def build_run_config_facts(
    *,
    run_id: str,
    task_definition: TaskDefinition,
    config: RunConfig,
    scaffold: ScaffoldDefinition | None = None,
    feedback_policy: ResolvedFeedbackPolicyFacts | None = None,
    tool_protocol: ToolProtocolFacts,
    environment_fingerprint: EnvironmentFingerprint,
    permission_policy_manifest_ref: ArtifactRef | None = None,
    source_snapshot_ref: ArtifactRef | None = None,
    repo_context_index_ref: ArtifactRef | None = None,
    provider_axis_scope: str | None = None,
    baseline_source: str | None = None,
    forbidden_scaffold_ids: list[str] | None = None,
) -> RunConfigFacts:
    verifier_config = task_definition.to_verifier_config()
    scaffold = scaffold or build_scaffold(config.runtime.scaffold_id)
    feedback_policy = feedback_policy or resolve_feedback_policy(
        run_config=config,
        scaffold=scaffold,
        task=task_definition,
    )
    context_policy_snapshot = _context_policy_snapshot(config)
    repository_hints_facts = config.context_management.repository_hints.resolved_facts()
    context_budget_facts = resolve_context_budget(
        config=config.context_management,
        provider=config.model.provider,
        model_id=config.model.model_id,
    )
    return RunConfigFacts(
        run_id=run_id,
        task_id=task_definition.id,
        task_version=task_definition.task_version,
        dataset_name=task_definition.dataset_name,
        source_kind=task_definition.source_kind,
        base_commit=task_definition.base_commit,
        source_archive_sha256=task_definition.source_archive_sha256,
        provider=config.model.provider,
        model_id=config.model.model_id,
        requested_provider=config.model.provider_specific_options.get(
            "requested_provider",
            config.model.provider,
        ),
        actual_provider=config.model.provider_specific_options.get(
            "actual_provider",
            config.model.provider,
        ),
        fallback_reason=config.model.provider_specific_options.get("fallback_reason"),
        fallback_policy_version=config.model.provider_specific_options.get("fallback_policy_version"),
        provider_base_url=config.model.provider_specific_options.get("base_url"),
        provider_endpoint_category=config.model.provider_specific_options.get("endpoint_category"),
        credential_source=config.model.provider_specific_options.get("credential_source"),
        temperature=config.model.temperature,
        seed=config.runtime.seed,
        max_output_tokens=config.model.max_output_tokens,
        retry_policy=config.model.retry_policy,
        credential_policy=config.model.credential_policy,
        provider_request_logging_policy=config.model.provider_request_logging,
        scaffold_id=config.runtime.scaffold_id,
        scaffold_version=scaffold.scaffold_version,
        allowed_tools_policy=scaffold.allowed_tools_policy,
        phase_policy=scaffold.phase_transition_policy,
        stop_policy=scaffold.default_stop_policy,
        test_feedback_policy=feedback_policy.resolved_test_feedback_policy.value,
        feedback_tests_passed_policy=feedback_policy.resolved_feedback_tests_passed_policy,
        feedback_policy_resolution=feedback_policy.model_dump(mode="json"),
        hidden_feedback_visible_to_model=feedback_policy.hidden_feedback_visible_to_model,
        swe_bench_like_final_only=feedback_policy.swe_bench_like_final_only,
        tool_protocol=tool_protocol,
        permission_policy_manifest_ref=permission_policy_manifest_ref,
        source_snapshot_ref=source_snapshot_ref,
        repo_context_index_ref=repo_context_index_ref,
        provider_axis_scope=provider_axis_scope,
        baseline_source=baseline_source,
        forbidden_scaffold_ids=forbidden_scaffold_ids or [],
        search_fact_policy_version="repo_harness_search_fact_trust_v1",
        repository_action_index_policy_version="repo_harness_repository_action_index_v1",
        convergence_nudge_policy_version="repo_harness_convergence_nudge_v3",
        context_warning_policy_version="repo_harness_context_warning_v1",
        context_replacement_runtime_policy_version="fresh_tool_result_budget_runtime_v1",
        provider_ready_token_estimator_version="provider_body_char4_token_estimator_v1",
        context_threshold_decision_source="provider_request_projection_estimate",
        compact_threshold_ratio_runtime_effect="reserved_for_autocompact_v1",
        context_policy_snapshot_version=(
            config.context_management.context_policy_snapshot_version
        ),
        context_policy_snapshot_hash=stable_hash(context_policy_snapshot),
        context_policy_snapshot=context_policy_snapshot,
        initial_context_policy_version=config.context_management.initial_context_policy_version,
        repository_hints_mode=config.context_management.repository_hints.mode,
        repository_hints_config=repository_hints_facts,
        repository_hints_resolved_max_candidate_files=(
            config.context_management.repository_hints.resolved_max_candidate_files
        ),
        repository_hints_resolved_max_matched_terms_per_file=(
            config.context_management.repository_hints.resolved_max_matched_terms_per_file
        ),
        repository_hints_resolved_max_fallback_search_terms=(
            config.context_management.repository_hints.resolved_max_fallback_search_terms
        ),
        repository_hints_resolved_include_low_confidence_limit=(
            config.context_management.repository_hints.resolved_include_low_confidence_limit
        ),
        context_budget_policy=config.context_management.context_budget_policy,
        tool_result_compact_policy=config.context_management.tool_result_compact_policy,
        microcompact_policy=config.context_management.microcompact_policy,
        auto_compact_enabled=config.context_management.auto_compact_enabled,
        reactive_compact_policy=config.context_management.reactive_compact_policy,
        harness_control_message_export_policy=(
            "exclude_harness_generated_untrainable_control_messages_v1"
        ),
        tool_call_repair_policy_version="malformed_tool_call_repair_v0",
        context_builder_version=config.versions.context_builder_version,
        context_policy_version=config.context_management.context_policy_version,
        prompt_template_version=config.versions.prompt_template_version,
        token_estimator_version=config.context_management.token_estimator,
        permission_mode=config.runtime.permission_mode,
        permission_policy_version=config.versions.permission_policy_version,
        network_policy=config.workspace.network_policy,
        shell_command_policy_version=COMMAND_POLICY_VERSION,
        verifier_name=verifier_config.parser,
        verifier_version=verifier_config.parser_version,
        final_verifier_mode=config.evaluation.final_verifier_mode,
        reward_formula_version=REWARD_VERSION,
        outcome_policy_version=OUTCOME_POLICY_VERSION,
        max_turns=config.runtime.max_turns,
        max_tool_calls=config.runtime.max_tool_calls,
        max_test_runs=config.runtime.max_test_runs,
        task_timeout_sec=config.runtime.task_timeout_sec,
        provider_request_timeout_sec=config.runtime.provider_request_timeout_sec,
        provider_timeout_grace_sec=config.runtime.provider_timeout_grace_sec,
        min_provider_request_timeout_sec=config.runtime.min_provider_request_timeout_sec,
        provider_timeout_policy=config.runtime.provider_timeout_policy,
        command_timeout_sec=config.workspace.default_command_timeout_sec,
        context_budget_tokens=context_budget_facts.effective_context_budget_tokens,
        model_context_window_tokens=context_budget_facts.model_context_window_tokens,
        model_context_window_resolution=(
            context_budget_facts.model_context_window_resolution
        ),
        effective_context_budget_tokens=(
            context_budget_facts.effective_context_budget_tokens
        ),
        hard_context_limit_tokens=context_budget_facts.hard_context_limit_tokens,
        main_output_reserve_tokens=context_budget_facts.main_output_reserve_tokens,
        estimator_safety_margin_tokens=(
            context_budget_facts.estimator_safety_margin_tokens
        ),
        artifact_budget_bytes=config.workspace.max_artifact_bytes,
        environment_fingerprint=environment_fingerprint,
    )


def _context_policy_snapshot(config: RunConfig) -> dict[str, Any]:
    context = config.context_management
    snapshot = {
        "schema_version": context.context_policy_snapshot_version,
        "initial_context_policy_version": context.initial_context_policy_version,
        "repository_hints": context.repository_hints.resolved_facts(),
        "context_budget_policy": context.context_budget_policy,
        "model_context_window_tokens": context.model_context_window_tokens,
        "harness_context_cap_tokens": context.harness_context_cap_tokens,
        "main_output_reserve_tokens": context.main_output_reserve_tokens,
        "estimator_safety_margin_ratio": context.estimator_safety_margin_ratio,
        "estimator_safety_margin_min_tokens": context.estimator_safety_margin_min_tokens,
        "max_context_tokens": context.max_context_tokens,
        "tool_result_aggregate_budget_chars": context.tool_result_aggregate_budget_chars,
        "keep_recent_turns": context.keep_recent_turns,
        "keep_recent_test_results": context.keep_recent_test_results,
        "summarize_old_test_outputs": context.summarize_old_test_outputs,
        "compact_strategy": context.compact_strategy,
        "compact_threshold_ratio": context.compact_threshold_ratio,
        "tool_result_compact_policy": context.tool_result_compact_policy,
        "freeze_tool_result_budget_decisions": (
            context.freeze_tool_result_budget_decisions
        ),
        "freeze_tool_result_decisions_at": context.freeze_tool_result_decisions_at,
        "max_single_tool_result_chars": context.max_single_tool_result_chars,
        "max_tool_results_per_turn_chars": context.max_tool_results_per_turn_chars,
        "tool_result_recovery_tool": context.tool_result_recovery_tool,
        "legacy_history_tool_result_replacement": (
            context.legacy_history_tool_result_replacement
        ),
        "microcompact_enabled": context.microcompact_enabled,
        "microcompact_policy": context.microcompact_policy,
        "microcompact_trigger_compactable_tool_result_count": (
            context.microcompact_trigger_compactable_tool_result_count
        ),
        "microcompact_trigger_compactable_tool_result_chars": (
            context.microcompact_trigger_compactable_tool_result_chars
        ),
        "microcompact_keep_recent_compactable_tool_results": (
            context.microcompact_keep_recent_compactable_tool_results
        ),
        "microcompact_cleared_message": context.microcompact_cleared_message,
        "auto_compact_enabled": context.auto_compact_enabled,
        "auto_compact_trigger_ratio": context.auto_compact_trigger_ratio,
        "hard_context_limit_ratio": context.hard_context_limit_ratio,
        "post_compact_target_ratio": context.post_compact_target_ratio,
        "post_compact_target_max_tokens": context.post_compact_target_max_tokens,
        "auto_compact_max_consecutive_failures": (
            context.auto_compact_max_consecutive_failures
        ),
        "auto_compact_summary_max_output_tokens": (
            context.auto_compact_summary_max_output_tokens
        ),
        "preserve_recent_turns_after_compact": (
            context.preserve_recent_turns_after_compact
        ),
        "preserve_recent_tail_token_budget": (
            context.preserve_recent_tail_token_budget
        ),
        "reactive_compact_enabled": context.reactive_compact_enabled,
        "local_context_limit_policy": context.local_context_limit_policy,
        "reactive_compact_policy": context.reactive_compact_policy,
        "ptl_retry_policy": context.ptl_retry_policy,
        "reactive_compact_retry_limit": context.reactive_compact_retry_limit,
        "context_policy_version": context.context_policy_version,
        "token_estimator": context.token_estimator,
    }
    return ContextPolicySnapshot.model_validate(snapshot).model_dump(mode="json")


def write_run_config_facts(run_dir: str | Path, facts: RunConfigFacts) -> RunConfigFactsRef:
    path = Path(run_dir) / "run_config_facts.json"
    if path.exists():
        raise FileExistsError(f"run_config_facts.json 已存在，不能改写不可变配置事实：{path}")
    digest = _write_json_atomic(path, facts.model_dump(mode="json"))
    return RunConfigFactsRef(relative_path="run_config_facts.json", sha256=digest)


def build_run_metadata(
    *,
    run_dir: str | Path,
    run_id: str,
    task_id: str,
    run_config_facts_ref: RunConfigFactsRef,
    tool_protocol: ToolProtocolFacts,
    baseline: BaselineResult,
    run_outcome: str,
    final_verifier_status: str,
    agent_stop_reason: str | None,
    final_verifier_mode: str | None,
) -> RunMetadata:
    run_path = Path(run_dir)
    metrics = _read_json_if_exists(run_path / "metrics.json")
    artifact_errors = verify_artifact_manifest(run_path)
    failure_diagnostics = _failure_diagnostics(
        baseline=baseline,
        run_path=run_path,
        run_outcome=run_outcome,
        final_verifier_status=final_verifier_status,
        agent_stop_reason=agent_stop_reason,
    )
    export_readiness = _export_readiness(run_path, artifact_errors)
    config_facts = _read_json_if_exists(run_path / run_config_facts_ref.relative_path)
    feedback_policy_resolution = config_facts.get("feedback_policy_resolution", {})
    workspace_execution = config_facts.get("environment_fingerprint", {}).get(
        "workspace_execution",
        {},
    )
    source_checkout = _source_checkout_from_config(workspace_execution)
    return RunMetadata(
        run_id=run_id,
        task_id=task_id,
        run_config_facts_ref=run_config_facts_ref,
        tool_protocol=tool_protocol,
        run_status="skipped" if baseline.status in {"invalid", "flaky"} else "completed",
        agent_stop_reason=agent_stop_reason,
        run_outcome=run_outcome,
        reward_status="present" if (run_path / "reward.json").exists() else "missing",
        final_verifier_status=final_verifier_status,  # type: ignore[arg-type]
        final_verifier_mode=final_verifier_mode,
        source_checkout=source_checkout,
        environment_spec_hash=workspace_execution.get("environment_spec_hash"),
        scaffold_id=config_facts.get("scaffold_id"),
        scaffold_version=config_facts.get("scaffold_version"),
        scaffold_facts={
            "scaffold_id": config_facts.get("scaffold_id"),
            "scaffold_version": config_facts.get("scaffold_version"),
            "allowed_tools_policy": config_facts.get("allowed_tools_policy"),
            "phase_policy": config_facts.get("phase_policy"),
            "stop_policy": config_facts.get("stop_policy"),
        },
        feedback_policy_resolution=feedback_policy_resolution,
        test_feedback_policy=config_facts.get("test_feedback_policy"),
        feedback_tests_passed_policy=config_facts.get("feedback_tests_passed_policy"),
        hidden_feedback_visible_to_model=config_facts.get("hidden_feedback_visible_to_model"),
        metrics_summary=_metrics_summary(metrics),
        tool_call_summary={
            "tool_call_count": metrics.get("tool_call_count", 0),
            "test_run_count": metrics.get("test_run_count", 0),
            "permission_denial_count": metrics.get("permission_denial_count", 0),
            "invalid_tool_call_count": metrics.get("invalid_tool_call_count", 0),
        },
        model_call_summary=_model_call_summary(run_path),
        initial_context_artifacts=_initial_context_artifacts(run_path),
        artifact_manifest_status="ok" if not artifact_errors else "invalid",
        failure_diagnostics=failure_diagnostics,
        export_readiness=export_readiness,
    )


def write_run_metadata(run_dir: str | Path, metadata: RunMetadata) -> RunMetadataRef:
    path = Path(run_dir) / "run_metadata.json"
    if path.exists():
        raise FileExistsError(f"run_metadata.json 已存在，不能改写最终运行元数据：{path}")
    digest = _write_json_atomic(path, metadata.model_dump(mode="json"))
    return RunMetadataRef(relative_path="run_metadata.json", sha256=digest)


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(text, encoding="utf-8")
    digest = _sha256_bytes(text.encode("utf-8"))
    os.replace(tmp_path, path)
    return digest


def _sha256_bytes(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _source_checkout_from_config(workspace_execution: dict[str, Any]) -> SourceCheckoutFacts | None:
    raw = workspace_execution.get("source_checkout")
    if not isinstance(raw, dict):
        return None
    return SourceCheckoutFacts.model_validate(raw)


def _metrics_summary(metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_success": metrics.get("task_success"),
        "final_verifier_status": metrics.get("final_verifier_status"),
        "run_outcome": metrics.get("run_outcome"),
        "turn_count": metrics.get("turn_count", 0),
        "tool_call_count": metrics.get("tool_call_count", 0),
        "test_run_count": metrics.get("test_run_count", 0),
    }


def _model_call_summary(run_path: Path) -> dict[str, Any]:
    events = _read_jsonl_if_exists(run_path / "events.jsonl")
    if not events:
        return {"model_call_count": 0, "model_error_count": 0}
    model_calls = 0
    model_errors = 0
    for event in events:
        if event.get("event_type") != "model_call_completed":
            continue
        model_calls += 1
        if event.get("data", {}).get("model_error_type"):
            model_errors += 1
    latest_ptl = _latest_ptl_truncation_summary(run_path, events)
    summary: dict[str, Any] = {
        "model_call_count": model_calls,
        "model_error_count": model_errors,
        "reactive_compact_applied_count": sum(
            1 for event in events if event.get("event_type") == "reactive_compact_applied"
        ),
        "ptl_truncation_count": sum(
            1 for event in events if event.get("event_type") == "ptl_truncation_applied"
        ),
    }
    if latest_ptl:
        summary["latest_ptl_truncation"] = latest_ptl
    return summary


def _initial_context_artifacts(run_path: Path) -> dict[str, Any]:
    manifest = _read_json_if_exists(run_path / "artifacts.json")
    artifacts = [
        artifact
        for artifact in manifest.get("artifacts", [])
        if isinstance(artifact, dict)
    ]
    profile_refs = [
        artifact
        for artifact in artifacts
        if artifact.get("kind") == "initial_context_profile"
    ]
    latest_profile = profile_refs[-1] if profile_refs else None
    profile_payload = (
        _read_json_if_exists(run_path / str(latest_profile.get("relative_path")))
        if latest_profile and latest_profile.get("relative_path")
        else {}
    )
    return {
        "initial_context_profile_ref": latest_profile,
        "initial_context_policy_version": profile_payload.get(
            "initial_context_policy_version"
        ),
        "repository_hints_mode": profile_payload.get("repository_hints_mode"),
        "repository_hints_presence": profile_payload.get("repository_hints_presence"),
        "repository_hints_absence_reason": profile_payload.get(
            "repository_hints_absence_reason"
        ),
        "repository_hints_model_visible_hash": profile_payload.get(
            "repository_hints_model_visible_hash"
        ),
        "repository_hints_model_visible_ref": profile_payload.get(
            "repository_hints_model_visible_ref"
        ),
        "repository_action_index_full_hash": profile_payload.get(
            "repository_action_index_full_hash"
        ),
        "repository_action_index_full_ref": profile_payload.get(
            "repository_action_index_full_ref"
        ),
        "repository_context_index_full_hash": profile_payload.get(
            "repository_context_index_full_hash"
        ),
        "repository_context_index_full_ref": profile_payload.get(
            "repository_context_index_full_ref"
        ),
        "forbidden_model_visible_fields_present": profile_payload.get(
            "forbidden_model_visible_fields_present",
            [],
        ),
    }


def _export_readiness(run_path: Path, artifact_errors: list[str]) -> ExportReadinessFacts:
    final_patch = run_path / "final.patch"
    has_final_patch = final_patch.exists() and final_patch.stat().st_size > 0
    verifier = _read_json_if_exists(run_path / "verifier.json")
    metrics = _read_json_if_exists(run_path / "metrics.json")
    boundary = _read_json_if_exists(run_path / "final_verifier_boundary.json")
    has_formal_final_verifier = (
        verifier.get("verifier_stage") == "final"
        and metrics.get("interaction_efficiency", {}).get("final_verifier_mode") == "strict_patch_replay"
    )
    readiness = {
        "has_final_patch": has_final_patch,
        "has_formal_final_verifier": has_formal_final_verifier,
        "has_reward_metadata": (run_path / "reward.json").exists(),
        "clean_transcript": (run_path / "transcript.jsonl").exists(),
        "clean_artifact_manifest": not artifact_errors,
    }
    training_checks = {
        "accepted_by_final_verifier": metrics.get("final_verifier_status") == "accepted",
        "successful_run_outcome": metrics.get("run_outcome") == "success",
        "not_budget_exhausted": metrics.get("interaction_efficiency", {}).get("agent_stop_reason")
        not in {
            "max_turns",
            "max_tool_calls",
            "timeout",
            "task_timeout",
            "context_limit",
            "context_limit_preflight_after_autocompact",
            "auto_compact_failed_preflight",
            "reactive_compact_failed",
            "context_limit_after_reactive_compact",
            "context_limit_reactive_compact_disabled",
        },
    }
    if boundary.get("final_verifier_status") == "not_executed":
        training_checks["accepted_by_final_verifier"] = False
    blockers = [
        name
        for name, ok in readiness.items()
        if not ok
    ]
    blockers.extend(name for name, ok in training_checks.items() if not ok)
    return ExportReadinessFacts(
        **readiness,
        training_export_ready=not blockers,
        blocking_reasons=blockers,
    )


def _failure_diagnostics(
    *,
    baseline: BaselineResult,
    run_path: Path,
    run_outcome: str,
    final_verifier_status: str,
    agent_stop_reason: str | None,
) -> list[FailureDiagnostics]:
    search_false_fact = _search_backend_false_fact_suspected(run_path)
    prefix_diagnostics = [search_false_fact] if search_false_fact is not None else []
    boundary = _read_json_if_exists(run_path / "final_verifier_boundary.json")
    if baseline.status in {"invalid", "flaky"}:
        return [
            FailureDiagnostics(
                failure_category=FailureCategory.task_quality_failure,
                failure_type=FailureType.baseline_quality_failed,
                recoverable=False,
                source_component="eval_runner",
                message=baseline.dependency_error or f"baseline status: {baseline.status}",
            )
        ]
    provider_timeout_diagnostic = _provider_timeout_diagnostic(
        run_path=run_path,
        agent_stop_reason=agent_stop_reason,
    )
    boundary_not_executed = _not_executed_boundary_diagnostic(
        boundary=boundary,
        run_path=run_path,
        agent_stop_reason=agent_stop_reason,
    )
    if boundary_not_executed is not None:
        diagnostics = [*prefix_diagnostics, boundary_not_executed]
        if provider_timeout_diagnostic is not None:
            diagnostics.append(provider_timeout_diagnostic)
        return diagnostics
    if provider_timeout_diagnostic is not None:
        return [*prefix_diagnostics, provider_timeout_diagnostic]
    if agent_stop_reason in {"max_turns", "max_tool_calls"} and _final_patch_empty(run_path):
        nudge_injected = _event_exists(run_path, "convergence_nudge_injected")
        nudge_summary = _convergence_nudge_summary(run_path)
        return [
            *prefix_diagnostics,
            FailureDiagnostics(
                failure_category=FailureCategory.model_failure,
                failure_type=(
                    FailureType.nudge_ignored_empty_patch
                    if nudge_injected
                    else FailureType.no_nudge_empty_patch
                ),
                recoverable=True,
                source_component="agent_loop",
                message=(
                    "agent reached the interaction budget without producing a non-empty final patch"
                ),
                details={
                    "agent_stop_reason": agent_stop_reason,
                    "convergence_nudge_injected": nudge_injected,
                    "convergence_nudge_summary": nudge_summary,
                },
            ),
        ]
    if final_verifier_status in {"failed", "rejected"}:
        boundary_failure_category = boundary.get("failure_category")
        boundary_failure_owner = boundary.get("failure_owner")
        late_edit = _late_edit_summary(run_path)
        if (
            final_verifier_status == "rejected"
            and boundary.get("final_verifier_status") == "rejected"
            and boundary_failure_owner == "model_wrong_fix"
        ):
            return [
                *prefix_diagnostics,
                FailureDiagnostics(
                    failure_category=FailureCategory.model_failure,
                    failure_type=FailureType.final_verifier_failed,
                    recoverable=False,
                    source_component="final_verifier",
                    message="formal final verifier rejected the model patch",
                    details={
                        "final_verifier_boundary_status": boundary.get("final_verifier_status"),
                        "final_verifier_boundary_failure_category": boundary_failure_category,
                        "final_verifier_boundary_failure_owner": boundary_failure_owner,
                        "diagnostic_subtypes": (
                            [FailureType.model_wrong_fix_after_late_edit.value]
                            if late_edit.get("model_wrong_fix_after_late_edit")
                            else []
                        ),
                        "late_edit_summary": late_edit,
                    },
                )
            ]
        return [
            *prefix_diagnostics,
            FailureDiagnostics(
                failure_category=FailureCategory.environment_failure,
                failure_type=FailureType.final_verifier_failed,
                recoverable=False,
                source_component="final_verifier",
                message="formal final verifier failed",
            )
        ]
    if agent_stop_reason == "auto_compact_failed_preflight":
        return [
            *prefix_diagnostics,
            FailureDiagnostics(
                failure_category=FailureCategory.model_failure,
                failure_type=FailureType.auto_compact_failed_preflight,
                recoverable=True,
                source_component="context_manager",
                message=(
                    "local hard preflight stopped the run because AutoCompact failed "
                    "and the provider request projection was still above the hard context limit"
                ),
                details=_auto_compact_preflight_failure_details(run_path),
            ),
        ]
    if agent_stop_reason == "reactive_compact_failed":
        return [
            *prefix_diagnostics,
            FailureDiagnostics(
                failure_category=FailureCategory.model_failure,
                failure_type=FailureType.reactive_compact_failed,
                recoverable=True,
                source_component="context_manager",
                message=(
                    "provider returned context_limit and Reactive Compact could not "
                    "produce a retryable provider request"
                ),
                details=_reactive_compact_failure_details(run_path),
            ),
        ]
    if agent_stop_reason == "context_limit_after_reactive_compact":
        return [
            *prefix_diagnostics,
            FailureDiagnostics(
                failure_category=FailureCategory.model_failure,
                failure_type=FailureType.context_limit_after_reactive_compact,
                recoverable=True,
                source_component="context_manager",
                message=(
                    "provider still returned context_limit after a Reactive Compact "
                    "or PTL fallback retry"
                ),
                details=_context_limit_after_reactive_compact_details(run_path),
            ),
        ]
    if agent_stop_reason == "context_limit":
        compaction_insufficient = _compaction_applied_but_insufficient(run_path)
        return [
            *prefix_diagnostics,
            FailureDiagnostics(
                failure_category=FailureCategory.model_failure,
                failure_type=(
                    FailureType.compaction_applied_but_insufficient_context_limit
                    if compaction_insufficient
                    else FailureType.context_limit
                ),
                recoverable=True,
                source_component="context_manager" if compaction_insufficient else "agent_loop",
                message=(
                    "context replacement was applied but provider-ready context still exceeded the limit"
                    if compaction_insufficient
                    else "context limit reached"
                ),
                details=_latest_context_limit_details(run_path),
            )
        ]
    if agent_stop_reason == "context_limit_preflight_after_autocompact":
        details = _latest_context_limit_details(
            run_path,
            error_type="context_limit_preflight_after_autocompact",
        )
        details.update(_latest_context_compaction_event_details(run_path))
        return [
            *prefix_diagnostics,
            FailureDiagnostics(
                failure_category=FailureCategory.model_failure,
                failure_type=FailureType.compaction_applied_but_insufficient_context_limit,
                recoverable=True,
                source_component="context_manager",
                message=(
                    "AutoCompact was applied but the provider request projection "
                    "remained above the local hard context limit"
                ),
                details=details,
            ),
        ]
    if run_outcome in {"success", "failed"}:
        return prefix_diagnostics
    return [
        *prefix_diagnostics,
        FailureDiagnostics.unknown(
            source_component="eval_runner",
            message=f"run_outcome={run_outcome}",
        )
    ]


def _provider_timeout_diagnostic(
    *,
    run_path: Path,
    agent_stop_reason: str | None,
) -> FailureDiagnostics | None:
    if agent_stop_reason not in {"timeout", "task_timeout", "model_error"}:
        return None
    provider_timeout_details = _latest_provider_timeout_details(run_path)
    if provider_timeout_details.get("provider_call_skipped_due_to_task_deadline"):
        return FailureDiagnostics(
            failure_category=FailureCategory.budget_or_timeout_failure,
            failure_type=FailureType.task_timeout_before_provider_call,
            recoverable=True,
            source_component="agent_loop",
            message="task deadline was too close to safely start another provider request",
            details=provider_timeout_details,
        )
    if provider_timeout_details.get("model_error_type") == "provider_timeout":
        return FailureDiagnostics(
            failure_category=FailureCategory.provider_failure,
            failure_type=FailureType.provider_timeout,
            recoverable=True,
            source_component="provider_client",
            message="provider request timed out before the model call completed",
            details=provider_timeout_details,
        )
    return None


def _latest_provider_timeout_details(run_path: Path) -> dict[str, Any]:
    events = _read_jsonl_if_exists(run_path / "events.jsonl")
    skipped = [
        event
        for event in events
        if event.get("event_type") == "provider_call_skipped_due_to_task_deadline"
    ]
    if skipped:
        event = skipped[-1]
        data = event.get("data") or {}
        return {
            "event_id": event.get("event_id"),
            "turn": event.get("turn"),
            "provider_call_skipped_due_to_task_deadline": True,
            "reason": data.get("reason"),
            "call_site": data.get("call_site"),
            "timeout_policy_facts": data.get("timeout_policy_facts") or {},
        }
    provider_timeouts = [
        event
        for event in events
        if event.get("event_type") == "model_call_completed"
        and (event.get("data") or {}).get("model_error_type") == "provider_timeout"
    ]
    if not provider_timeouts:
        return {}
    event = provider_timeouts[-1]
    data = event.get("data") or {}
    timeout_facts = data.get("request_timeout_policy_facts") or {}
    return {
        "event_id": event.get("event_id"),
        "turn": event.get("turn"),
        "model_call_id": data.get("model_call_id"),
        "model_error_type": data.get("model_error_type"),
        "terminal_error_type": data.get("terminal_error_type"),
        "request_timeout_seconds": data.get("request_timeout_seconds"),
        "request_timeout_policy_facts": timeout_facts,
        "deadline_aware_provider_timeout": bool(
            timeout_facts.get("absolute_deadline_enforced")
            or timeout_facts.get("provider_retry_deadline_enforced")
        ),
    }


def _not_executed_boundary_diagnostic(
    *,
    boundary: dict[str, Any],
    run_path: Path,
    agent_stop_reason: str | None,
) -> FailureDiagnostics | None:
    if boundary.get("final_verifier_status") != "not_executed":
        return None
    boundary_failure_category = str(boundary.get("failure_category") or "")
    if not boundary_failure_category:
        return None
    boundary_failure_owner = str(boundary.get("failure_owner") or "")
    nudge_injected = _event_exists(run_path, "convergence_nudge_injected")
    nudge_summary = _convergence_nudge_summary(run_path)
    diagnostic_subtypes: list[str] = []
    if boundary_failure_category == "budget_exhausted_empty_patch":
        diagnostic_subtypes.append(
            FailureType.nudge_ignored_empty_patch.value
            if nudge_injected
            else FailureType.no_nudge_empty_patch.value
        )
    failure_category = _failure_category_from_boundary_owner(boundary_failure_owner)
    failure_type = _failure_type_from_boundary_failure(boundary_failure_category)
    return FailureDiagnostics(
        failure_category=failure_category,
        failure_type=failure_type,
        recoverable=failure_category
        in {
            FailureCategory.budget_or_timeout_failure,
            FailureCategory.model_failure,
            FailureCategory.provider_failure,
        },
        source_component="final_verifier_boundary",
        message=_boundary_failure_message(boundary_failure_category),
        details={
            "agent_stop_reason": agent_stop_reason,
            "final_verifier_boundary_status": boundary.get("final_verifier_status"),
            "final_verifier_boundary_failure_category": boundary_failure_category,
            "final_verifier_boundary_failure_owner": boundary_failure_owner,
            "final_verifier_ran": boundary.get("final_verifier_ran"),
            "invalid_for_training": True,
            "diagnostic_subtypes": diagnostic_subtypes,
            "convergence_nudge_injected": nudge_injected,
            "convergence_nudge_summary": nudge_summary,
        },
    )


def _failure_category_from_boundary_owner(owner: str) -> FailureCategory:
    if owner == "budget_or_timeout":
        return FailureCategory.budget_or_timeout_failure
    if owner in {"harness_or_environment", "harness_or_verifier_input"}:
        return FailureCategory.environment_failure
    if owner == "provider_or_model":
        return FailureCategory.provider_failure
    if owner in {
        "model_wrong_fix",
        "model_patch_quality",
        "model_patch_format_or_path",
        "model_no_patch_generated",
    }:
        return FailureCategory.model_failure
    return FailureCategory.unknown_failure


def _failure_type_from_boundary_failure(boundary_failure_category: str) -> FailureType:
    mapping = {
        "task_timeout_before_final_verifier": FailureType.task_timeout_before_final_verifier,
        "budget_exhausted_empty_patch": FailureType.budget_exhausted_empty_patch,
        "context_limit": FailureType.context_limit,
        "environment_setup_failed": FailureType.environment_setup_failed,
        "final_verifier_environment_error": FailureType.final_verifier_environment_error,
        "verification_workspace_creation_failed": FailureType.environment_setup_failed,
        "verification_workspace_error": FailureType.environment_setup_failed,
    }
    return mapping.get(boundary_failure_category, FailureType.final_verifier_not_executed)


def _boundary_failure_message(boundary_failure_category: str) -> str:
    if boundary_failure_category == "task_timeout_before_final_verifier":
        return "task timeout expired before the formal final verifier could execute"
    if boundary_failure_category == "budget_exhausted_empty_patch":
        return "agent exhausted the interaction budget without producing a non-empty final patch"
    if boundary_failure_category == "final_verifier_environment_error":
        return "formal final verifier could not execute task assertions because the verifier environment failed"
    return f"formal final verifier did not execute: {boundary_failure_category}"


def _convergence_nudge_summary(run_path: Path) -> dict[str, Any]:
    events = _read_jsonl_if_exists(run_path / "events.jsonl")
    nudges = [
        event for event in events if event.get("event_type") == "convergence_nudge_injected"
    ]
    if not nudges:
        return {
            "nudge_count": 0,
            "levels": [],
            "latest_nudge_turn": None,
            "post_latest_nudge_action": "not_applicable",
        }
    latest = nudges[-1]
    latest_turn = int(latest.get("turn") or 0)
    tool_events_after = [
        event
        for event in events
        if int(event.get("turn") or 0) > latest_turn
        and event.get("event_type") == "tool_completed"
    ]
    edited_after = any(
        ((event.get("data") or {}).get("effective_tool_name") in {"edit_file", "create_file"})
        for event in tool_events_after
    )
    git_diff_after = any(
        ((event.get("data") or {}).get("effective_tool_name") == "git_diff")
        for event in tool_events_after
    )
    final_answer_turn = _final_answer_turn(run_path)
    final_answer_after = final_answer_turn is not None and final_answer_turn > latest_turn
    if edited_after:
        post_action = "edited_after_nudge"
    elif git_diff_after:
        post_action = "git_diff_after_nudge"
    elif final_answer_after:
        post_action = "final_answer_after_nudge"
    else:
        post_action = "no_observed_action_after_nudge"
    return {
        "nudge_count": len(nudges),
        "levels": [str((event.get("data") or {}).get("nudge_level") or "unknown") for event in nudges],
        "latest_nudge_turn": latest_turn,
        "latest_nudge_level": str((latest.get("data") or {}).get("nudge_level") or "unknown"),
        "latest_turns_remaining": (latest.get("data") or {}).get("turns_remaining"),
        "latest_has_patch": (latest.get("data") or {}).get("has_patch"),
        "edited_after_latest_nudge": edited_after,
        "git_diff_after_latest_nudge": git_diff_after,
        "final_answer_after_latest_nudge": final_answer_after,
        "post_latest_nudge_action": post_action,
    }


def _final_patch_empty(run_path: Path) -> bool:
    patch_path = run_path / "final.patch"
    if not patch_path.exists():
        return True
    return not patch_path.read_text(encoding="utf-8", errors="replace").strip()


def _event_exists(run_path: Path, event_type: str) -> bool:
    return any(event.get("event_type") == event_type for event in _read_jsonl_if_exists(run_path / "events.jsonl"))


def _search_backend_false_fact_suspected(run_path: Path) -> FailureDiagnostics | None:
    samples: list[dict[str, Any]] = []
    for event in _read_jsonl_if_exists(run_path / "events.jsonl"):
        if event.get("event_type") not in {"tool_completed", "tool_failed"}:
            continue
        data = event.get("data") or {}
        if not isinstance(data, dict):
            continue
        typed = data.get("typed") if isinstance(data.get("typed"), dict) else data
        if not isinstance(typed, dict):
            continue
        result_kind = str(typed.get("result_kind") or "")
        total_match_count = int(typed.get("total_match_count") or typed.get("match_count") or 0)
        can_form_absence_fact = result_kind in {
            "partial_scan_no_match",
            "complete_no_match",
            "page_empty_out_of_range",
            "incomplete_file_listing",
        } or total_match_count == 0
        search_issue = can_form_absence_fact and (
            typed.get("backend_mismatch_detected") is True
            or int(typed.get("read_error_count") or 0) > 0
            or int(typed.get("visibility_error_count") or 0) > 0
        )
        if not search_issue:
            continue
        samples.append(
            {
                "turn": event.get("turn"),
                "tool_call_id": data.get("tool_call_id"),
                "tool_name": data.get("effective_tool_name") or data.get("tool_name"),
                "result_kind": result_kind,
                "scan_complete": typed.get("scan_complete"),
                "scan_complete_reason": typed.get("scan_complete_reason"),
                "backend_mismatch_detected": typed.get("backend_mismatch_detected"),
                "read_error_count": typed.get("read_error_count"),
                "visibility_error_count": typed.get("visibility_error_count"),
                "absence_fact_risk": True,
            }
        )
        if len(samples) >= 5:
            break
    if not samples:
        return None
    return FailureDiagnostics(
        failure_category=FailureCategory.tool_protocol_failure,
        failure_type=FailureType.search_backend_false_fact_suspected,
        recoverable=True,
        source_component="tool_system",
        message=(
            "search or listing results contained auditable backend/read/visibility anomalies; "
            "complete-no-match facts from this run should be treated cautiously"
        ),
        details={"samples": samples},
    )


def _auto_compact_preflight_failure_details(run_path: Path) -> dict[str, Any]:
    events = _read_jsonl_if_exists(run_path / "events.jsonl")
    budget_event = _latest_event(
        events,
        event_type="budget_exhausted",
        error_type="auto_compact_failed_preflight",
    )
    auto_event = _latest_event(events, event_type="auto_compact_failed")
    details = _context_policy_details(run_path)
    budget_data = _event_data(budget_event)
    auto_data = _event_data(auto_event)
    details.update(
        {
            "agent_stop_reason": "auto_compact_failed_preflight",
            "source_prepared_messages_ref": auto_data.get("source_prepared_messages_ref"),
            "summary_artifact_ref": auto_data.get("summary_artifact_ref"),
            "auto_compact_record_ref": (
                budget_data.get("auto_compact_record_ref")
                or _event_artifact_ref(auto_event, kind="auto_compact_record")
            ),
            "failure_reason": (
                budget_data.get("auto_compact_failure_reason")
                or auto_data.get("failure_reason")
            ),
            "tokens_before": auto_data.get("tokens_before") or budget_data.get("token_estimate"),
            "tokens_after": auto_data.get("tokens_after") or auto_data.get("tokens_before"),
            "effective_context_budget_tokens": _first_present(
                auto_data.get("effective_context_budget_tokens"),
                _context_budget_fact(budget_data, "effective_context_budget_tokens"),
            ),
            "hard_context_limit_tokens": _first_present(
                budget_data.get("hard_context_limit_tokens"),
                auto_data.get("hard_context_limit_tokens"),
                _context_budget_fact(budget_data, "hard_context_limit_tokens"),
            ),
            "provider_request_projection_hash": budget_data.get(
                "provider_request_projection_hash"
            ),
            "event_refs": _event_refs([auto_event, budget_event]),
        }
    )
    return _drop_none_values(details)


def _reactive_compact_failure_details(run_path: Path) -> dict[str, Any]:
    events = _read_jsonl_if_exists(run_path / "events.jsonl")
    failed_event = _latest_event(events, event_type="reactive_compact_failed")
    failed_data = _event_data(failed_event)
    trigger_event = _latest_event(events, event_type="reactive_compact_triggered")
    trigger_data = _event_data(trigger_event)
    auto_failed_event = _latest_event(events, event_type="auto_compact_failed")
    auto_failed_data = _event_data(auto_failed_event)
    details = _context_policy_details(run_path)
    details.update(
        {
            "agent_stop_reason": "reactive_compact_failed",
            "source_prepared_messages_ref": (
                auto_failed_data.get("source_prepared_messages_ref")
                or trigger_data.get("prepared_messages_ref")
            ),
            "summary_artifact_ref": failed_data.get("summary_artifact_ref"),
            "failure_reason": failed_data.get("failure_reason"),
            "compact_id": failed_data.get("compact_id"),
            "ptl_fallback_status": failed_data.get("ptl_fallback_status"),
            "ptl_fallback_failure_reason": failed_data.get(
                "ptl_fallback_failure_reason"
            ),
            "tokens_before": auto_failed_data.get("tokens_before"),
            "tokens_after": auto_failed_data.get("tokens_after")
            or auto_failed_data.get("tokens_before"),
            "effective_context_budget_tokens": auto_failed_data.get(
                "effective_context_budget_tokens"
            ),
            "hard_context_limit_tokens": auto_failed_data.get("hard_context_limit_tokens"),
            "original_model_call_id": trigger_data.get("model_call_id"),
            "original_provider_request_ref": trigger_data.get("raw_provider_request_ref"),
            "original_provider_response_ref": trigger_data.get("raw_provider_response_ref"),
            "event_refs": _event_refs([trigger_event, auto_failed_event, failed_event]),
        }
    )
    ptl_details = _ptl_details_from_ref(run_path, failed_data.get("ptl_truncation_ref"))
    if ptl_details:
        details["ptl_fallback"] = ptl_details
    return _drop_none_values(details)


def _context_limit_after_reactive_compact_details(run_path: Path) -> dict[str, Any]:
    events = _read_jsonl_if_exists(run_path / "events.jsonl")
    exhausted_index, exhausted_event = _latest_event_with_index(
        events,
        event_type="reactive_compact_retry_limit_exhausted",
    )
    exhausted_data = _event_data(exhausted_event)
    latest_trigger = _latest_event(events, event_type="reactive_compact_triggered")
    trigger_data = _event_data(latest_trigger)
    latest_applied = _latest_event(events, event_type="reactive_compact_applied")
    applied_data = _event_data(latest_applied)
    latest_ptl_summary = _latest_ptl_truncation_summary(run_path, events)
    details = _context_policy_details(run_path)
    details.update(
        {
            "agent_stop_reason": "context_limit_after_reactive_compact",
            "source_prepared_messages_ref": (
                applied_data.get("source_prepared_messages_ref")
                or trigger_data.get("prepared_messages_ref")
            ),
            "summary_artifact_ref": applied_data.get("summary_artifact_ref"),
            "retry_model_call_id": _retry_model_call_id_after_recovery(
                events,
                before_index=exhausted_index,
            )
            or trigger_data.get("model_call_id"),
            "rejected_retry_model_call_id": trigger_data.get("model_call_id"),
            "reactive_compact_retry_count": exhausted_data.get(
                "reactive_compact_retry_count"
            ),
            "reactive_compact_retry_limit": exhausted_data.get(
                "reactive_compact_retry_limit"
            ),
            "original_provider_request_ref": trigger_data.get("raw_provider_request_ref"),
            "original_provider_response_ref": trigger_data.get("raw_provider_response_ref"),
            "event_refs": _event_refs([latest_applied, latest_trigger, exhausted_event]),
        }
    )
    if latest_ptl_summary:
        details["ptl_fallback"] = latest_ptl_summary
        details.setdefault(
            "ptl_truncation_ref",
            latest_ptl_summary.get("ptl_truncation_ref"),
        )
        details.setdefault(
            "synthetic_marker_id",
            latest_ptl_summary.get("synthetic_marker_id"),
        )
        details.setdefault(
            "omitted_round_count",
            latest_ptl_summary.get("omitted_round_count"),
        )
        details.setdefault(
            "tokens_before",
            latest_ptl_summary.get("token_estimate_before"),
        )
        details.setdefault(
            "tokens_after",
            latest_ptl_summary.get("token_estimate_after"),
        )
        details.setdefault(
            "hard_context_limit_tokens",
            latest_ptl_summary.get("hard_context_limit_tokens"),
        )
    return _drop_none_values(details)


def _latest_context_compaction_event_details(run_path: Path) -> dict[str, Any]:
    events = _read_jsonl_if_exists(run_path / "events.jsonl")
    latest_applied = _latest_event(events, event_type="auto_compact_applied")
    applied_data = _event_data(latest_applied)
    details = _context_policy_details(run_path)
    details.update(
        {
            "source_prepared_messages_ref": applied_data.get(
                "source_prepared_messages_ref"
            ),
            "summary_artifact_ref": applied_data.get("summary_artifact_ref"),
            "tokens_before": applied_data.get("tokens_before"),
            "tokens_after": applied_data.get("tokens_after"),
            "effective_context_budget_tokens": applied_data.get(
                "effective_context_budget_tokens"
            ),
            "hard_context_limit_tokens": applied_data.get("hard_context_limit_tokens"),
            "event_refs": _event_refs([latest_applied]),
        }
    )
    return _drop_none_values(details)


def _latest_ptl_truncation_summary(
    run_path: Path,
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    ptl_index, ptl_event = _latest_event_with_index(events, event_type="ptl_truncation_applied")
    ptl_data = _event_data(ptl_event)
    ptl_ref = ptl_data.get("ptl_truncation_ref")
    record = _artifact_payload_from_ref(run_path, ptl_ref)
    summary = {
        "ptl_truncation_ref": ptl_ref,
        "original_model_call_id": _first_present(
            ptl_data.get("original_model_call_id"),
            record.get("original_model_call_id"),
        ),
        "retry_model_call_id": _retry_model_call_id_after_recovery(
            events,
            before_index=ptl_index,
        ),
        "synthetic_marker_id": _first_present(
            ptl_data.get("synthetic_marker_id"),
            record.get("synthetic_marker_id"),
        ),
        "omitted_round_count": _first_present(
            ptl_data.get("omitted_round_count"),
            record.get("omitted_round_count"),
        ),
        "retained_round_count": record.get("retained_round_count"),
        "token_estimate_before": _first_present(
            ptl_data.get("token_estimate_before"),
            record.get("token_estimate_before"),
        ),
        "token_estimate_after": _first_present(
            ptl_data.get("token_estimate_after"),
            record.get("token_estimate_after"),
        ),
        "hard_context_limit_tokens": record.get("hard_context_limit_tokens"),
        "post_truncation_above_hard_limit": _first_present(
            ptl_data.get("post_truncation_above_hard_limit"),
            record.get("post_truncation_above_hard_limit"),
        ),
    }
    return _drop_none_values(summary)


def _ptl_details_from_ref(run_path: Path, ref: Any) -> dict[str, Any]:
    record = _artifact_payload_from_ref(run_path, ref)
    if not record and not isinstance(ref, dict):
        return {}
    details = {
        "ptl_truncation_ref": ref,
        "original_model_call_id": record.get("original_model_call_id"),
        "synthetic_marker_id": record.get("synthetic_marker_id"),
        "omitted_round_count": record.get("omitted_round_count"),
        "retained_round_count": record.get("retained_round_count"),
        "token_estimate_before": record.get("token_estimate_before"),
        "token_estimate_after": record.get("token_estimate_after"),
        "hard_context_limit_tokens": record.get("hard_context_limit_tokens"),
        "post_truncation_above_hard_limit": record.get(
            "post_truncation_above_hard_limit"
        ),
    }
    return _drop_none_values(details)


def _context_policy_details(run_path: Path) -> dict[str, Any]:
    config_facts = _read_json_if_exists(run_path / "run_config_facts.json")
    snapshot = config_facts.get("context_policy_snapshot")
    if not isinstance(snapshot, dict):
        snapshot = {}
    return _drop_none_values(
        {
            "local_context_limit_policy": (
                snapshot.get("local_context_limit_policy")
                or config_facts.get("local_context_limit_policy")
            ),
            "reactive_compact_policy": (
                snapshot.get("reactive_compact_policy")
                or config_facts.get("reactive_compact_policy")
            ),
            "effective_context_budget_tokens": (
                config_facts.get("effective_context_budget_tokens")
                or config_facts.get("context_budget_tokens")
            ),
            "hard_context_limit_tokens": config_facts.get("hard_context_limit_tokens"),
        }
    )


def _context_budget_fact(data: dict[str, Any], key: str) -> Any:
    facts = data.get("context_budget_facts")
    return facts.get(key) if isinstance(facts, dict) else None


def _latest_event(
    events: list[dict[str, Any]],
    *,
    event_type: str,
    error_type: str | None = None,
) -> dict[str, Any]:
    _, event = _latest_event_with_index(
        events,
        event_type=event_type,
        error_type=error_type,
    )
    return event


def _latest_event_with_index(
    events: list[dict[str, Any]],
    *,
    event_type: str,
    error_type: str | None = None,
) -> tuple[int | None, dict[str, Any]]:
    for index in range(len(events) - 1, -1, -1):
        event = events[index]
        if event.get("event_type") != event_type:
            continue
        if error_type is not None and event.get("error_type") != error_type:
            continue
        return index, event
    return None, {}


def _event_data(event: dict[str, Any]) -> dict[str, Any]:
    data = event.get("data")
    return data if isinstance(data, dict) else {}


def _event_artifact_ref(event: dict[str, Any], *, kind: str) -> dict[str, Any] | None:
    refs = event.get("artifact_refs")
    if not isinstance(refs, list):
        return None
    for ref in refs:
        if isinstance(ref, dict) and ref.get("kind") == kind:
            return ref
    return None


def _event_refs(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for event in events:
        if not event:
            continue
        refs.append(
            _drop_none_values(
                {
                    "event_id": event.get("event_id"),
                    "event_type": event.get("event_type"),
                    "turn": event.get("turn"),
                    "error_type": event.get("error_type"),
                }
            )
        )
    return refs


def _retry_model_call_id_after_recovery(
    events: list[dict[str, Any]],
    *,
    before_index: int | None,
) -> str | None:
    if before_index is None:
        return None
    for event in events[before_index + 1 :]:
        if event.get("event_type") != "model_input_accepted":
            continue
        data = _event_data(event)
        model_call_id = data.get("model_call_id")
        if isinstance(model_call_id, str) and model_call_id:
            return model_call_id
    for event in events[before_index + 1 :]:
        if event.get("event_type") != "model_call_started":
            continue
        data = _event_data(event)
        model_call_id = data.get("model_call_id")
        if isinstance(model_call_id, str) and model_call_id:
            return model_call_id
    return None


def _artifact_payload_from_ref(run_path: Path, ref: Any) -> dict[str, Any]:
    if not isinstance(ref, dict):
        return {}
    relative_path = ref.get("relative_path")
    if not isinstance(relative_path, str) or not relative_path:
        return {}
    artifact_path = run_path / relative_path
    try:
        resolved = artifact_path.resolve()
        run_root = run_path.resolve()
    except OSError:
        return {}
    if run_root not in resolved.parents and resolved != run_root:
        return {}
    if not artifact_path.exists():
        return {}
    try:
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _drop_none_values(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}


def _compaction_applied_but_insufficient(run_path: Path) -> bool:
    for event in _read_jsonl_if_exists(run_path / "events.jsonl"):
        if event.get("event_type") != "context_prepared":
            continue
        reduction = (event.get("data") or {}).get("context_reduction") or {}
        if isinstance(reduction, dict) and reduction.get(
            "replacement_applied_but_insufficient_context_limit"
        ):
            return True
    return False


def _latest_context_limit_details(
    run_path: Path,
    *,
    error_type: str = "context_limit",
) -> dict[str, Any]:
    latest_context: dict[str, Any] = {}
    latest_budget: dict[str, Any] = {}
    for event in _read_jsonl_if_exists(run_path / "events.jsonl"):
        if event.get("event_type") == "context_prepared":
            latest_context = event.get("data") if isinstance(event.get("data"), dict) else {}
        if event.get("event_type") == "budget_exhausted" and event.get("error_type") == error_type:
            latest_budget = event.get("data") if isinstance(event.get("data"), dict) else {}
    return {
        "latest_context_prepared": {
            "context_revision": latest_context.get("context_revision"),
            "provider_ready_token_estimate": latest_context.get("provider_ready_token_estimate"),
            "provider_body_char_estimate": latest_context.get("provider_body_char_estimate"),
            "internal_token_estimate_after": latest_context.get("internal_token_estimate_after"),
            "threshold_decision_source": latest_context.get("threshold_decision_source"),
            "context_reduction": latest_context.get("context_reduction"),
        },
        "budget_exhausted": latest_budget,
    }


def _late_edit_summary(run_path: Path) -> dict[str, Any]:
    tool_events = [
        event
        for event in _read_jsonl_if_exists(run_path / "events.jsonl")
        if event.get("event_type") == "tool_completed"
    ]
    if not tool_events:
        return {"model_wrong_fix_after_late_edit": False}
    max_turn = max(int(event.get("turn") or 0) for event in tool_events)
    edit_turns = [
        int(event.get("turn") or 0)
        for event in tool_events
        if (event.get("data") or {}).get("effective_tool_name")
        in {"edit_file", "create_file"}
    ]
    if not edit_turns:
        return {"model_wrong_fix_after_late_edit": False}
    last_edit_turn = max(edit_turns)
    final_answer_turn = _final_answer_turn(run_path)
    near_budget = _near_turn_budget_from_run_config(run_path)
    late_edit = (
        near_budget
        and final_answer_turn is not None
        and final_answer_turn - last_edit_turn <= 1
        and last_edit_turn >= max(1, max_turn - 1)
    )
    return {
        "model_wrong_fix_after_late_edit": late_edit,
        "last_edit_turn": last_edit_turn,
        "max_observed_tool_turn": max_turn,
        "final_answer_turn": final_answer_turn,
        "near_turn_budget": near_budget,
        "late_edit_policy": "requires_near_budget_and_edit_immediately_before_final_answer",
    }


def _final_answer_turn(run_path: Path) -> int | None:
    transcript_path = run_path / "transcript.jsonl"
    if transcript_path.exists():
        for record in _read_jsonl_if_exists(transcript_path):
            if record.get("role") != "assistant":
                continue
            preview = str(record.get("content_preview") or "")
            if "tool_calls=" in preview:
                continue
            turn = record.get("turn")
            if isinstance(turn, int):
                return turn
    for event in _read_jsonl_if_exists(run_path / "events.jsonl"):
        if event.get("event_type") in {"agent_finished", "model_final_answer", "final_answer"}:
            turn = event.get("turn")
            if isinstance(turn, int):
                return turn
        data = event.get("data")
        if isinstance(data, dict) and data.get("agent_stop_reason") == "final_answer":
            turn = event.get("turn")
            if isinstance(turn, int):
                return turn
    return None


def _near_turn_budget_from_run_config(run_path: Path) -> bool:
    facts = _read_json_if_exists(run_path / "run_config_facts.json")
    max_turns = facts.get("max_turns")
    if not isinstance(max_turns, int) or max_turns <= 0:
        return False
    max_observed_turn = max(
        [int(event.get("turn") or 0) for event in _read_jsonl_if_exists(run_path / "events.jsonl")]
        or [0]
    )
    threshold = max(1, min(6, max_turns // 4))
    return max_turns - max_observed_turn <= threshold


def _read_jsonl_if_exists(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records
