"""Stage 16F.3 experimental run_episode task runner.

The runner is intentionally small: it builds the shared
``EpisodeExecutionSpec`` from an existing task/config pair, calls
``RepoHarnessRuntime.run_episode(real_episode)``, and writes a sanitized
compatibility projection for evaluation tooling.  It does not migrate the
legacy ``run_task`` path yet.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

from repo_harness.config import RunConfig, load_run_config
from repo_harness.errors import ConfigError, RepoHarnessError
from repo_harness.evaluation.schemas import ResolvedVerifierPlan
from repo_harness.execution import EpisodeExecutionSpec, EpisodeExecutionSpecBuilder
from repo_harness.model_client.factory import create_model_client
from repo_harness.rl import (
    EpisodeBudgets,
    EpisodeTaskRef,
    ProviderRoutePolicy,
    RepoHarnessEpisodeRequest,
    RepoHarnessRuntime,
    RepoHarnessRuntimeOptions,
)
from repo_harness.rl.provider_gateway import build_llm_gateway_for_route
from repo_harness.schema_base import stable_hash
from repo_harness.tasks import LoadedTask, RunnableTask, load_task
from repo_harness.verifier import VerifierResult
from repo_harness.workspace import DependencyState, RunWorkspace, create_workspace_adapter

from .entrypoint_policy import write_canonical_entrypoint_report
from .episode_projection import ProjectionWriteResult, write_run_episode_compat_projection

RUN_EPISODE_TASK_RUN_MODES = frozenset({"training_fast", "training_debug", "full_audit"})


def run_episode_task(
    task_path: str | Path,
    *,
    config_path: str | Path,
    output_dir: str | Path | None = None,
    run_id: str | None = None,
    gateway_route: str | None = None,
    run_mode: str = "training_fast",
    assert_projection_complete: bool = False,
) -> Path:
    """Run one task through the canonical ``run_episode(real_episode)`` path."""

    selected_run_mode = _validate_run_mode(run_mode)
    loaded_task = load_task(task_path)
    config = load_run_config(config_path, output_dir=output_dir)
    actual_run_id = run_id or f"{config.run_id_prefix}_{loaded_task.runnable_task.task_id}"
    runs_root = Path(config.workspace.output_dir)
    run_dir = runs_root / actual_run_id
    if run_dir.exists():
        raise ConfigError(f"run directory already exists: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=True)

    source_checkout = _materialize_source_for_spec(
        loaded_task=loaded_task,
        config=config,
        run_id=actual_run_id,
        run_dir=run_dir,
    )
    resolved_verifier_plan = _resolved_verifier_plan(loaded_task, actual_run_id)
    workspace = RunWorkspace(
        run_id=actual_run_id,
        workspace_path=source_checkout.as_posix(),
        repo_base_commit=loaded_task.runnable_task.base_commit,
        execution_mode=config.runtime.execution_mode,
        artifact_dir=(run_dir / "artifacts").as_posix(),
        dependency_state=DependencyState(),
    )
    spec = EpisodeExecutionSpecBuilder().build_spec_from_loaded_task(
        task=loaded_task.runnable_task,
        workspace=workspace,
        run_config=config,
        resolved_verifier_plan=resolved_verifier_plan,
        run_id=actual_run_id,
        task_ref=_opaque_task_ref(loaded_task),
        run_config_ref=_opaque_run_config_ref(config),
    )
    route = _resolve_gateway_route(config.model.provider)
    if gateway_route is not None:
        requested_route = _resolve_gateway_route(gateway_route)
        if requested_route != route:
            raise ConfigError(
                "gateway_route_mismatch_with_run_config_provider: "
                f"requested={requested_route!r}, configured={route!r}"
            )
        route = requested_route
    request = _episode_request_from_spec(
        spec=spec,
        task=loaded_task.runnable_task,
        loaded_task=loaded_task,
        route=route,
        config=config,
        run_mode=selected_run_mode,
    )
    gateway = _build_gateway(config, route=route, run_dir=run_dir)
    runtime = RepoHarnessRuntime(
        RepoHarnessRuntimeOptions(
            config_path=config_path,
            output_dir=runs_root,
            runtime_execution_mode="real_episode",
            executor_max_workers=1,
            episode_timeout_seconds=float(loaded_task.runnable_task.timeouts.agent_timeout_sec),
            real_episode_source_resolver=lambda _request: source_checkout,
            real_episode_final_verifier_factory=_final_verifier_factory(
                resolved_verifier_plan=resolved_verifier_plan,
            ),
            tool_observation_token_projector=lambda content: _debug_tool_observation_tokens(content),
        )
    )
    try:
        result = asyncio.run(runtime.run_episode(request, llm_gateway=gateway, execution_spec=spec))
    finally:
        close = getattr(gateway, "close", None)
        if callable(close):
            close()

    projection = write_run_episode_compat_projection(
        run_dir=run_dir,
        task=loaded_task.runnable_task,
        request=request,
        execution_spec=spec,
        result=result,
        provider_route=route,
    )
    if assert_projection_complete and not projection.validation_report.get("projection_complete"):
        raise ConfigError("run_episode projection did not pass validation")
    route_qualification = _read_json_if_exists(
        run_dir / "compat_projection" / "provider_route_qualification.json",
    )
    write_canonical_entrypoint_report(
        run_dir,
        run_id=request.run_id,
        task_id=request.task_id,
        episode_execution_spec_sha256=spec.spec_payload_sha256,
        compat_projection_complete=bool(projection.validation_report.get("projection_complete")),
        provider_route=route_qualification.get("provider_route") if route_qualification else route,
        formal_online_rl_eligible=bool(route_qualification.get("formal_online_rl_eligible")),
        policy_loss_candidate=bool(route_qualification.get("policy_loss_candidate")),
    )
    stage16_5_reports = _write_stage16_5_prebaseline_reports(
        run_dir=run_dir,
        request=request,
        spec=spec,
        result_status=result.status,
        projection=projection,
        provider_route=route,
    )
    _write_runner_summary(
        run_dir=run_dir,
        request=request,
        spec=spec,
        result_status=result.status,
        projection=projection,
        stage16_5_reports=stage16_5_reports,
    )
    return run_dir


def _materialize_source_for_spec(
    *,
    loaded_task: LoadedTask,
    config: RunConfig,
    run_id: str,
    run_dir: Path,
) -> Path:
    adapter = create_workspace_adapter(config=config, run_id=run_id, run_dir=run_dir)
    return adapter.create_source_checkout(loaded_task.runnable_task)


def _resolved_verifier_plan(loaded_task: LoadedTask, run_id: str) -> ResolvedVerifierPlan:
    verifier_config = loaded_task.verifier_config
    return ResolvedVerifierPlan(
        verifier_config=verifier_config,
        initial_fail_to_pass_tests=list(verifier_config.fail_to_pass_tests),
        initial_pass_to_pass_tests=list(verifier_config.pass_to_pass_tests),
        flaky_tests=[],
        parser_confidence=1.0,
        resolved_verifier_plan_id=f"{run_id}:resolved-verifier-plan",
    )


def _episode_request_from_spec(
    *,
    spec: EpisodeExecutionSpec,
    task: RunnableTask,
    loaded_task: LoadedTask,
    route: str,
    config: RunConfig,
    run_mode: str,
) -> RepoHarnessEpisodeRequest:
    provider_route_policy_examples: list[ProviderRoutePolicy] = [
        ProviderRoutePolicy(
            route=route,  # type: ignore[arg-type]
            invalid_for_online_rl=True,
            allowed_uses=(
                ["evaluation", "offline_diagnostic_replay"]
                if route in {"openai", "deepseek"}
                else []
            ),
        )
    ]
    return RepoHarnessEpisodeRequest(
        episode_id=spec.run_id,
        run_id=spec.run_id,
        task_id=spec.task_id,
        llm_gateway_route=route,  # type: ignore[arg-type]
        inference_backend=None,
        provider_route_policy_examples=provider_route_policy_examples,
        raw_prompt=[],
        raw_prompt_source="episode_execution_spec",
        task_ref=EpisodeTaskRef(
            task_id=task.task_id,
            task_ref=_opaque_task_ref(loaded_task),
            dataset_name=task.dataset_name,
            dataset_split=task.metadata.get("dataset_split"),
            base_commit=task.base_commit,
            source_archive_ref=task.source_archive_sha256,
            model_visible_summary=f"{task.dataset_name}:{task.task_id}",
        ),
        episode_execution_spec_ref=f"rh://episode-execution-spec/{spec.spec_payload_sha256}",
        episode_execution_spec_sha256=spec.spec_payload_sha256,
        task_definition_sha256=spec.task_facts.task_definition_sha256,
        run_config_sha256=spec.run_config_facts.run_config_sha256,
        permission_mode=spec.run_config_facts.permission_mode,
        network_policy=spec.run_config_facts.network_policy,
        run_mode_hint=spec.run_config_facts.run_mode_hint,
        allowed_tool_names=spec.allowed_tool_names,
        tool_registry_digest=spec.tool_facts.tool_registry_digest,
        resolved_verifier_plan_digest=spec.verifier_facts.resolved_verifier_plan_digest,
        test_feedback_policy=spec.feedback_facts.test_feedback_policy,
        feedback_tests_passed_policy=spec.feedback_facts.feedback_tests_passed_policy,
        run_config_ref=_opaque_run_config_ref(config),
        run_mode=run_mode,  # type: ignore[arg-type]
        budgets=EpisodeBudgets(
            max_turns=spec.budget_facts.max_turns,
            max_tool_calls=spec.budget_facts.max_tool_calls,
            max_test_runs=spec.budget_facts.max_test_runs,
            max_tool_observation_tokens=spec.budget_facts.max_tool_output_chars,
            max_model_calls=max(1, spec.budget_facts.max_turns or 1),
            max_output_tokens=config.model.max_output_tokens,
            request_timeout_seconds=config.runtime.provider_request_timeout_sec,
            max_artifact_bytes=config.workspace.max_artifact_bytes or 5_000_000,
        ),
    )


def _build_gateway(config: RunConfig, *, route: str, run_dir: Path):
    if route == "mock":
        if config.model.provider_specific_options.get("mock_gateway_kind") == "model_client":
            model_client = create_model_client(config.model)
            return build_llm_gateway_for_route(
                "mock",
                model_client=model_client,
                run_dir_root=run_dir / "llm_gateway",
                max_workers=1,
                default_model_id=config.model.model_id,
                default_provider_specific_options=config.model.provider_specific_options,
            )
        return build_llm_gateway_for_route("mock")
    model_client = create_model_client(config.model)
    return build_llm_gateway_for_route(
        route,
        model_client=model_client,
        run_dir_root=run_dir / "llm_gateway",
        max_workers=1,
        default_model_id=config.model.model_id,
        default_provider_specific_options=config.model.provider_specific_options,
    )


def _resolve_gateway_route(route: str) -> str:
    if route == "fake":
        return "mock"
    if route not in {"mock", "replay", "openai", "deepseek"}:
        raise ConfigError(
            "Stage 16F.3 run-episode-task 只支持 mock、replay、openai、deepseek；"
            f"收到 {route!r}。"
        )
    return route


def _validate_run_mode(run_mode: str | None) -> str:
    selected = str(run_mode or "training_fast")
    if selected not in RUN_EPISODE_TASK_RUN_MODES:
        allowed = ", ".join(sorted(RUN_EPISODE_TASK_RUN_MODES))
        raise ConfigError(f"unsupported run_episode_task run_mode: {selected!r}; allowed={allowed}")
    return selected


def _final_verifier_factory(*, resolved_verifier_plan: ResolvedVerifierPlan):
    def factory(context: Any):
        def verify() -> VerifierResult:
            return _run_final_verifier_command(
                workspace_path=Path(context.workspace_path),
                resolved_verifier_plan=resolved_verifier_plan,
            )

        return verify

    return factory


def _run_final_verifier_command(
    *,
    workspace_path: Path,
    resolved_verifier_plan: ResolvedVerifierPlan,
) -> VerifierResult:
    config = resolved_verifier_plan.verifier_config
    argv = _pytest_command_argv(config.test_command)
    try:
        completed = subprocess.run(
            argv,
            cwd=workspace_path,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=config.final_verifier_timeout_sec,
            check=False,
        )
        accepted = completed.returncode == 0
        fail_to_pass = _run_declared_pytest_tests(
            workspace_path,
            resolved_verifier_plan.initial_fail_to_pass_tests,
            timeout_seconds=config.final_verifier_timeout_sec,
        )
        pass_to_pass = _run_declared_pytest_tests(
            workspace_path,
            resolved_verifier_plan.initial_pass_to_pass_tests,
            timeout_seconds=config.final_verifier_timeout_sec,
        )
        declared_total = fail_to_pass["total"] + pass_to_pass["total"]
        declared_passed = fail_to_pass["passed"] + pass_to_pass["passed"]
        return VerifierResult(
            verifier_stage="final",
            parser_confidence=1.0,
            command=config.test_command,
            accepted=accepted,
            pass_ratio=(declared_passed / declared_total if declared_total else (1.0 if accepted else 0.0)),
            fail_to_pass=fail_to_pass,
            pass_to_pass=pass_to_pass,
            exit_code=completed.returncode,
            error_type=None if accepted else "pytest_failed",
        )
    except subprocess.TimeoutExpired:
        return VerifierResult(
            verifier_stage="final",
            parser_confidence=1.0,
            command=config.test_command,
            accepted=False,
            pass_ratio=0.0,
            fail_to_pass={"passed": 0, "total": len(resolved_verifier_plan.initial_fail_to_pass_tests)},
            pass_to_pass={"passed": 0, "total": len(resolved_verifier_plan.initial_pass_to_pass_tests)},
            exit_code=None,
            timeout=True,
            error_type="timeout",
        )


def _run_declared_pytest_tests(
    workspace_path: Path,
    test_ids: list[str],
    *,
    timeout_seconds: int,
) -> dict[str, int]:
    passed = 0
    seen: set[str] = set()
    for test_id in test_ids:
        if test_id in seen:
            continue
        seen.add(test_id)
        try:
            completed = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", test_id],
                cwd=workspace_path,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            continue
        if completed.returncode == 0:
            passed += 1
    return {"passed": passed, "total": len(seen)}


def _pytest_command_argv(command: str) -> list[str]:
    try:
        parts = shlex.split(command)
    except ValueError as exc:
        raise ConfigError("final verifier command is not parseable") from exc
    if not parts:
        raise ConfigError("final verifier command is empty")
    if parts[0] == "pytest":
        return [sys.executable, "-m", "pytest", *parts[1:]]
    if parts[:3] == ["python", "-m", "pytest"]:
        return [sys.executable, "-m", "pytest", *parts[3:]]
    raise ConfigError("Stage 16F.3 final verifier factory only supports pytest commands")


def _debug_tool_observation_tokens(content: str) -> list[int]:
    if not content:
        return []
    digest = stable_hash({"content": content})
    return [100_000 + int(digest[index : index + 2], 16) for index in range(0, min(16, len(digest)), 2)]


def _opaque_task_ref(loaded_task: LoadedTask) -> str:
    return f"rh://task/{stable_hash({'task_id': loaded_task.runnable_task.task_id})}"


def _opaque_run_config_ref(config: RunConfig) -> str:
    return f"rh://run-config/{stable_hash(config.model_dump(mode='json'))}"


def _write_runner_summary(
    *,
    run_dir: Path,
    request: RepoHarnessEpisodeRequest,
    spec: EpisodeExecutionSpec,
    result_status: str,
    projection: ProjectionWriteResult,
    stage16_5_reports: dict[str, Any],
) -> None:
    payload = {
        "schema_version": "repo_harness_stage16f3_run_episode_task_summary_v0",
        "run_id": request.run_id,
        "task_id": request.task_id,
        "llm_gateway_route": request.llm_gateway_route,
        "run_mode": request.run_mode,
        "stage16_5_diagnostic_baseline_reports": stage16_5_reports,
        "result_status": result_status,
        "episode_execution_spec_sha256": spec.spec_payload_sha256,
        "compat_projection_manifest": "compat_projection/compat_projection_manifest.json",
        "projection_complete": projection.validation_report.get("projection_complete"),
    }
    path = run_dir / "run_episode_task_summary.json"
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_stage16_5_prebaseline_reports(
    *,
    run_dir: Path,
    request: RepoHarnessEpisodeRequest,
    spec: EpisodeExecutionSpec,
    result_status: str,
    projection: ProjectionWriteResult,
    provider_route: str,
) -> dict[str, Any]:
    provider_report = _provider_failure_accounting_report(
        run_dir=run_dir,
        request=request,
        result_status=result_status,
    )
    provider_report_path = run_dir / "stage16_5_provider_failure_accounting.json"
    _write_json_file(provider_report_path, provider_report)

    official_report = _official_prediction_eligibility_report(
        run_dir=run_dir,
        projection=projection,
        request=request,
    )
    official_report_path = run_dir / "stage16_5_official_prediction_eligibility.json"
    _write_json_file(official_report_path, official_report)

    inventory = _case_artifact_inventory_report(
        run_dir=run_dir,
        request=request,
        spec=spec,
        projection=projection,
        provider_route=provider_route,
        provider_report_path=provider_report_path,
        official_report_path=official_report_path,
    )
    inventory_path = run_dir / "stage16_5_case_artifact_inventory.json"
    _write_json_file(inventory_path, inventory)

    return {
        "schema_version": "repo_harness_stage16_5_prebaseline_report_refs_v0",
        "provider_failure_accounting": _relative_file_ref(run_dir, provider_report_path),
        "official_prediction_eligibility": _relative_file_ref(run_dir, official_report_path),
        "case_artifact_inventory": _relative_file_ref(run_dir, inventory_path),
        "provider_failure_accounting_sha256": _sha256_file(provider_report_path),
        "official_prediction_eligibility_sha256": _sha256_file(official_report_path),
        "case_artifact_inventory_sha256": _sha256_file(inventory_path),
    }


def _provider_failure_accounting_report(
    *,
    run_dir: Path,
    request: RepoHarnessEpisodeRequest,
    result_status: str,
) -> dict[str, Any]:
    gateway_artifacts = _collect_llm_gateway_artifacts(run_dir)
    model_call_error_types: list[str] = []
    provider_attempt_error_types: list[str] = []
    fallback_artifact_error_types: list[str] = []
    response_artifacts: list[dict[str, Any]] = []
    request_artifacts: list[dict[str, Any]] = []
    projection_fact_artifacts: list[dict[str, Any]] = []
    provider_request_projection_facts: list[dict[str, Any]] = []
    provider_response_projection_facts: list[dict[str, Any]] = []
    provider_attempt_records: list[dict[str, Any]] = []
    model_call_events: list[dict[str, Any]] = []
    retry_counts_from_model_call_event: list[int] = []

    for artifact in gateway_artifacts:
        kind = artifact.get("kind")
        public_record = _public_gateway_artifact_record(artifact)
        if kind == "model_call_event":
            model_call_events.append(public_record)
        if isinstance(kind, str) and "provider_request" in kind:
            request_artifacts.append(public_record)
        if isinstance(kind, str) and "provider_response" in kind:
            response_artifacts.append(public_record)
        payload = _read_gateway_artifact_payload(artifact)
        if isinstance(payload, dict):
            if kind == "model_call_event":
                retry_count = payload.get("retry_count")
                if isinstance(retry_count, int):
                    retry_counts_from_model_call_event.append(retry_count)
            if kind == "provider_attempt":
                attempt_record = _public_provider_attempt_record(payload, artifact)
                provider_attempt_records.append(attempt_record)
                attempt_error_type = attempt_record.get("error_type")
                if isinstance(attempt_error_type, str) and attempt_error_type:
                    provider_attempt_error_types.append(attempt_error_type)
            if kind == "artifact_projection_facts":
                projection_fact_artifacts.append(public_record)
                target_kind = payload.get("target_kind")
                if isinstance(target_kind, str) and "provider_request" in target_kind:
                    provider_request_projection_facts.append(public_record)
                if isinstance(target_kind, str) and "provider_response" in target_kind:
                    provider_response_projection_facts.append(public_record)
            error_type = payload.get("model_error_type") or payload.get("error_type")
            if isinstance(error_type, str) and error_type:
                if kind == "model_call_event":
                    model_call_error_types.append(error_type)
                elif isinstance(kind, str) and "provider_response" in kind:
                    fallback_artifact_error_types.append(error_type)

    terminal_attempt_error_types = [
        str(record["error_type"])
        for record in provider_attempt_records
        if record.get("terminal") is True and record.get("error_type")
    ]
    error_types = model_call_error_types or terminal_attempt_error_types or fallback_artifact_error_types
    provider_timeout_count = error_types.count("provider_timeout")
    invalid_response_count = error_types.count("invalid_response")
    empty_response_count = error_types.count("empty_response")
    retry_exhausted_count = error_types.count("retry_exhausted")
    provider_error_count = sum(
        1
        for error_type in error_types
        if error_type in {
            "auth_error",
            "rate_limited",
            "provider_error",
            "context_limit",
        }
    )
    tool_call_parse_failure_count = error_types.count("tool_call_parse_failure")
    provider_infrastructure_failure_count = len(error_types)
    model_semantic_failure_count = 1 if provider_infrastructure_failure_count == 0 and result_status == "failed" else 0
    raw_payload_persisted = _raw_payload_persisted_status(
        raw_artifact_count=len(request_artifacts) + len(response_artifacts),
        projection_fact_count=len(provider_request_projection_facts) + len(provider_response_projection_facts),
    )

    return {
        "schema_version": "repo_harness_stage16_5_provider_failure_accounting_v0",
        "run_id": request.run_id,
        "task_id": request.task_id,
        "run_mode": request.run_mode,
        "llm_gateway_route": request.llm_gateway_route,
        "provider_artifact_visibility": "runtime_private_digest_only",
        "raw_provider_request_artifact_count": len(request_artifacts),
        "raw_provider_response_artifact_count": len(response_artifacts),
        "provider_request_projection_fact_count": len(provider_request_projection_facts),
        "provider_response_projection_fact_count": len(provider_response_projection_facts),
        "artifact_projection_fact_count": len(projection_fact_artifacts),
        "raw_payload_persisted": raw_payload_persisted,
        "model_call_event_count": len(model_call_events),
        "provider_error_types": sorted(set(error_types)),
        "provider_attempt_count": len(provider_attempt_records),
        "provider_attempt_error_types": sorted(set(provider_attempt_error_types)),
        "retryable_attempt_count": len(
            [record for record in provider_attempt_records if record.get("retryable") is True]
        ),
        "terminal_attempt_count": len(
            [record for record in provider_attempt_records if record.get("terminal") is True]
        ),
        "retry_count_from_model_call_event": sum(retry_counts_from_model_call_event),
        "max_retry_count_from_model_call_event": (
            max(retry_counts_from_model_call_event) if retry_counts_from_model_call_event else 0
        ),
        "provider_timeout_count": provider_timeout_count,
        "empty_response_count": empty_response_count,
        "invalid_response_body_count": invalid_response_count,
        "retry_exhausted_count": retry_exhausted_count,
        "tool_call_parse_failure_count": tool_call_parse_failure_count,
        "provider_error_count": provider_error_count,
        "provider_infrastructure_failure_count": provider_infrastructure_failure_count,
        "model_semantic_failure_count": model_semantic_failure_count,
        "failure_owner": (
            "provider_or_infrastructure"
            if provider_infrastructure_failure_count
            else ("model_or_task" if model_semantic_failure_count else "none")
        ),
        "request_artifacts": request_artifacts,
        "response_artifacts": response_artifacts,
        "provider_request_projection_facts": provider_request_projection_facts,
        "provider_response_projection_facts": provider_response_projection_facts,
        "provider_attempt_records": provider_attempt_records,
        "model_call_events": model_call_events,
    }


def _official_prediction_eligibility_report(
    *,
    run_dir: Path,
    projection: ProjectionWriteResult,
    request: RepoHarnessEpisodeRequest,
) -> dict[str, Any]:
    projection_dir = projection.projection_dir
    hygiene_report = _read_json_if_exists(projection_dir / "final_patch_hygiene_report.json")
    final_patch_path = projection_dir / "final.patch"
    final_diff_path = projection_dir / "final.diff"
    final_patch_sha256 = _sha256_file(final_patch_path) if final_patch_path.exists() else None
    final_diff_sha256 = _sha256_file(final_diff_path) if final_diff_path.exists() else None
    cleaned_patch_sha256 = hygiene_report.get("cleaned_patch_sha256")
    exclusion_reasons: list[str] = []

    if not hygiene_report:
        exclusion_reasons.append("missing_final_patch_hygiene_report")
    if projection.validation_report.get("projection_complete") is not True:
        exclusion_reasons.append("compat_projection_incomplete")
    if hygiene_report and hygiene_report.get("status") != "passed":
        exclusion_reasons.append("final_patch_hygiene_not_passed")
    if final_patch_sha256 and cleaned_patch_sha256 and final_patch_sha256 != cleaned_patch_sha256:
        exclusion_reasons.append("final_patch_not_cleaned_patch")
    if hygiene_report.get("cleaned_patch_empty") is True or hygiene_report.get("only_filtered_changes") is True:
        exclusion_reasons.append("empty_or_only_filtered_patch")

    return {
        "schema_version": "repo_harness_stage16_5_official_prediction_eligibility_v0",
        "run_id": request.run_id,
        "task_id": request.task_id,
        "official_prediction_uses_cleaned_patch": final_patch_sha256 is not None
        and cleaned_patch_sha256 == final_patch_sha256,
        "cleaned_patch_sha256": cleaned_patch_sha256,
        "final_patch_sha256": final_patch_sha256,
        "final_diff_sha256": final_diff_sha256,
        "final_patch_hygiene_status": hygiene_report.get("status"),
        "cleaned_patch_empty": hygiene_report.get("cleaned_patch_empty"),
        "only_filtered_changes": hygiene_report.get("only_filtered_changes"),
        "duplicate_instance_detected": False,
        "duplicate_instance_policy": "single_case_no_duplicate_manifest",
        "official_prediction_eligible": not exclusion_reasons,
        "exclusion_reasons": exclusion_reasons,
    }


def _case_artifact_inventory_report(
    *,
    run_dir: Path,
    request: RepoHarnessEpisodeRequest,
    spec: EpisodeExecutionSpec,
    projection: ProjectionWriteResult,
    provider_route: str,
    provider_report_path: Path,
    official_report_path: Path,
) -> dict[str, Any]:
    gateway_artifacts = _collect_llm_gateway_artifacts(run_dir)
    files = {
        "transcript": run_dir / "transcript.jsonl",
        "events": run_dir / "events.jsonl",
        "artifacts_manifest": run_dir / "artifacts.json",
        "compat_projection_manifest": projection.manifest_path,
        "projection_validation_report": projection.projection_dir / "projection_validation_report.json",
        "final_patch": projection.projection_dir / "final.patch",
        "final_diff": projection.projection_dir / "final.diff",
        "final_patch_hygiene_report": projection.projection_dir / "final_patch_hygiene_report.json",
        "verifier_summary": projection.projection_dir / "verifier_summary.json",
        "reward_summary": projection.projection_dir / "reward_summary.json",
        "provider_failure_accounting": provider_report_path,
        "official_prediction_eligibility": official_report_path,
    }
    return {
        "schema_version": "repo_harness_stage16_5_case_artifact_inventory_v0",
        "run_id": request.run_id,
        "task_id": request.task_id,
        "episode_execution_spec_sha256": spec.spec_payload_sha256,
        "run_mode": request.run_mode,
        "provider_route": provider_route,
        "raw_run_directory_status": "local_private_path_not_projected",
        "compat_projection_status": projection.validation_report.get("projection_complete"),
        "artifact_records": {
            name: _file_inventory_record(run_dir, path)
            for name, path in files.items()
        },
        "llm_gateway_artifact_count": len(gateway_artifacts),
        "llm_gateway_artifacts": [_public_gateway_artifact_record(artifact) for artifact in gateway_artifacts],
        "runtime_private_evidence_policy": "provider_payload_content_not_public; digest_and_size_only",
    }


def _collect_llm_gateway_artifacts(run_dir: Path) -> list[dict[str, Any]]:
    gateway_root = run_dir / "llm_gateway"
    if not gateway_root.exists():
        return []
    collected: list[dict[str, Any]] = []
    for manifest_path in sorted(gateway_root.rglob("artifacts.json")):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(manifest, dict):
            artifacts = manifest.get("artifacts")
        else:
            artifacts = manifest
        if not isinstance(artifacts, list):
            continue
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                continue
            record = dict(artifact)
            record["_manifest_path"] = manifest_path
            record["_artifact_path"] = manifest_path.parent / str(artifact.get("relative_path", ""))
            collected.append(record)
    return collected


def _read_gateway_artifact_payload(artifact: dict[str, Any]) -> Any:
    artifact_path = artifact.get("_artifact_path")
    if not isinstance(artifact_path, Path) or not artifact_path.exists():
        return None
    if artifact_path.suffix != ".json":
        return None
    try:
        return json.loads(artifact_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _public_gateway_artifact_record(artifact: dict[str, Any]) -> dict[str, Any]:
    artifact_path = artifact.get("_artifact_path")
    payload_sha256 = artifact.get("sha256")
    return {
        "artifact_id": artifact.get("artifact_id"),
        "kind": artifact.get("kind"),
        "sha256": payload_sha256,
        "size_bytes": artifact.get("size_bytes"),
        "redaction_status": artifact.get("redaction_status"),
        "retention_policy": artifact.get("retention_policy"),
        "content_visibility": "not_public",
        "runtime_private_ref": (
            f"runtime-private:{artifact.get('kind')}:{payload_sha256}"
            if isinstance(payload_sha256, str) and len(payload_sha256) == 64
            else None
        ),
        "artifact_present": isinstance(artifact_path, Path) and artifact_path.exists(),
    }


def _public_provider_attempt_record(payload: dict[str, Any], artifact: dict[str, Any]) -> dict[str, Any]:
    request_ref = payload.get("request_ref")
    response_ref = payload.get("response_ref")
    return {
        "artifact": _public_gateway_artifact_record(artifact),
        "attempt_index": payload.get("attempt_index"),
        "model_call_id": payload.get("model_call_id"),
        "provider": payload.get("provider"),
        "retryable": payload.get("retryable"),
        "terminal": payload.get("terminal"),
        "error_type": payload.get("error_type"),
        "delay_ms": payload.get("delay_ms"),
        "duration_ms": payload.get("duration_ms"),
        "provider_request_id_present": bool(payload.get("provider_request_id")),
        "request_ref_kind": _artifact_ref_field(request_ref, "kind"),
        "request_ref_sha256": _artifact_ref_field(request_ref, "sha256"),
        "response_ref_kind": _artifact_ref_field(response_ref, "kind"),
        "response_ref_sha256": _artifact_ref_field(response_ref, "sha256"),
    }


def _artifact_ref_field(ref: Any, field: str) -> Any:
    if not isinstance(ref, dict):
        return None
    value = ref.get(field)
    return value if isinstance(value, (str, int, bool)) or value is None else None


def _raw_payload_persisted_status(*, raw_artifact_count: int, projection_fact_count: int) -> bool | str | None:
    if raw_artifact_count and projection_fact_count:
        return "mixed"
    if raw_artifact_count:
        return True
    if projection_fact_count:
        return False
    return None


def _file_inventory_record(run_dir: Path, path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"present": False, "relative_path": _relative_path_or_name(run_dir, path)}
    return {
        "present": True,
        "relative_path": _relative_path_or_name(run_dir, path),
        "sha256": _sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def _relative_file_ref(run_dir: Path, path: Path) -> dict[str, Any]:
    return {
        "relative_path": _relative_path_or_name(run_dir, path),
        "sha256": _sha256_file(path),
    }


def _relative_path_or_name(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def _write_json_file(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
