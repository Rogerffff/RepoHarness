"""第二版 run facts 写入器。"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from repo_harness.config import RunConfig
from repo_harness.evaluation.schemas import BaselineResult
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
    ToolProtocolFacts,
)
from repo_harness.schema_versions import OUTCOME_POLICY_VERSION, REWARD_VERSION
from repo_harness.tasks import TaskDefinition
from repo_harness.trajectory import verify_artifact_manifest


def build_run_config_facts(
    *,
    run_id: str,
    task_definition: TaskDefinition,
    config: RunConfig,
    tool_protocol: ToolProtocolFacts,
    environment_fingerprint: EnvironmentFingerprint,
) -> RunConfigFacts:
    verifier_config = task_definition.to_verifier_config()
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
        temperature=config.model.temperature,
        seed=config.runtime.seed,
        max_output_tokens=config.model.max_output_tokens,
        retry_policy=config.model.retry_policy,
        credential_policy=config.model.credential_policy,
        provider_request_logging_policy=config.model.provider_request_logging,
        scaffold_id=config.runtime.scaffold_id,
        scaffold_version="repo_harness_simple_react_v0",
        allowed_tools_policy=config.versions.tool_policy_version,
        phase_policy="repo_harness_simple_react_single_phase_v0",
        stop_policy="repo_harness_feedback_tests_passed_stop_v0",
        test_feedback_policy="oracle_hidden_feedback",
        feedback_tests_passed_policy="stop_immediately",
        hidden_feedback_visible_to_model=True,
        swe_bench_like_final_only=False,
        tool_protocol=tool_protocol,
        context_builder_version=config.versions.context_builder_version,
        context_policy_version=config.context_management.context_policy_version,
        prompt_template_version=config.versions.prompt_template_version,
        token_estimator_version=config.context_management.token_estimator,
        permission_mode=config.runtime.permission_mode,
        permission_policy_version=config.versions.permission_policy_version,
        network_policy=config.workspace.network_policy,
        shell_command_policy_version="repo_harness_shell_policy_v0",
        verifier_name=verifier_config.parser,
        verifier_version=verifier_config.parser_version,
        final_verifier_mode=config.evaluation.final_verifier_mode,
        reward_formula_version=REWARD_VERSION,
        outcome_policy_version=OUTCOME_POLICY_VERSION,
        max_turns=config.runtime.max_turns,
        max_tool_calls=config.runtime.max_tool_calls,
        max_test_runs=config.runtime.max_test_runs,
        task_timeout_sec=config.runtime.task_timeout_sec,
        command_timeout_sec=config.workspace.default_command_timeout_sec,
        context_budget_tokens=config.context_management.max_context_tokens,
        artifact_budget_bytes=config.workspace.max_artifact_bytes,
        environment_fingerprint=environment_fingerprint,
    )


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
        run_outcome=run_outcome,
        final_verifier_status=final_verifier_status,
        agent_stop_reason=agent_stop_reason,
    )
    export_readiness = _export_readiness(run_path, artifact_errors)
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
        metrics_summary=_metrics_summary(metrics),
        tool_call_summary={
            "tool_call_count": metrics.get("tool_call_count", 0),
            "test_run_count": metrics.get("test_run_count", 0),
            "permission_denial_count": metrics.get("permission_denial_count", 0),
            "invalid_tool_call_count": metrics.get("invalid_tool_call_count", 0),
        },
        model_call_summary=_model_call_summary(run_path),
        artifact_manifest_status="ok" if not artifact_errors else "invalid",
        failure_diagnostics=failure_diagnostics,
        export_readiness=export_readiness,
    )


def write_run_metadata(run_dir: str | Path, metadata: RunMetadata) -> RunMetadataRef:
    path = Path(run_dir) / "run_metadata.json"
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
    events_path = run_path / "events.jsonl"
    if not events_path.exists():
        return {"model_call_count": 0, "model_error_count": 0}
    model_calls = 0
    model_errors = 0
    for line in events_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        if event.get("event_type") != "model_call_completed":
            continue
        model_calls += 1
        if event.get("data", {}).get("model_error_type"):
            model_errors += 1
    return {"model_call_count": model_calls, "model_error_count": model_errors}


def _export_readiness(run_path: Path, artifact_errors: list[str]) -> ExportReadinessFacts:
    has_final_patch = (run_path / "final.patch").exists()
    verifier = _read_json_if_exists(run_path / "verifier.json")
    metrics = _read_json_if_exists(run_path / "metrics.json")
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
    blockers = [
        name
        for name, ok in readiness.items()
        if not ok
    ]
    return ExportReadinessFacts(
        **readiness,
        training_export_ready=not blockers,
        blocking_reasons=blockers,
    )


def _failure_diagnostics(
    *,
    baseline: BaselineResult,
    run_outcome: str,
    final_verifier_status: str,
    agent_stop_reason: str | None,
) -> list[FailureDiagnostics]:
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
    if final_verifier_status == "failed":
        return [
            FailureDiagnostics(
                failure_category=FailureCategory.environment_failure,
                failure_type=FailureType.final_verifier_failed,
                recoverable=False,
                source_component="final_verifier",
                message="formal final verifier failed",
            )
        ]
    if agent_stop_reason == "context_limit":
        return [
            FailureDiagnostics(
                failure_category=FailureCategory.model_failure,
                failure_type=FailureType.context_limit,
                recoverable=True,
                source_component="agent_loop",
                message="context limit reached",
            )
        ]
    if run_outcome in {"success", "failed"}:
        return []
    return [
        FailureDiagnostics.unknown(
            source_component="eval_runner",
            message=f"run_outcome={run_outcome}",
        )
    ]
