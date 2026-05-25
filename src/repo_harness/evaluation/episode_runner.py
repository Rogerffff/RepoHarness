"""Stage 16F.3 experimental run_episode task runner.

The runner is intentionally small: it builds the shared
``EpisodeExecutionSpec`` from an existing task/config pair, calls
``RepoHarnessRuntime.run_episode(real_episode)``, and writes a sanitized
compatibility projection for evaluation tooling.  It does not migrate the
legacy ``run_task`` path yet.
"""

from __future__ import annotations

import asyncio
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

from .episode_projection import ProjectionWriteResult, write_run_episode_compat_projection


def run_episode_task(
    task_path: str | Path,
    *,
    config_path: str | Path,
    output_dir: str | Path | None = None,
    run_id: str | None = None,
    gateway_route: str | None = None,
    assert_projection_complete: bool = False,
) -> Path:
    """Run one task through the canonical ``run_episode(real_episode)`` path."""

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
    _write_runner_summary(
        run_dir=run_dir,
        request=request,
        spec=spec,
        result_status=result.status,
        projection=projection,
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
        run_mode="training_fast",
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
        return build_llm_gateway_for_route("mock")
    model_client = create_model_client(config.model)
    return build_llm_gateway_for_route(
        route,
        model_client=model_client,
        run_dir_root=run_dir / "llm_gateway",
        max_workers=1,
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
        return VerifierResult(
            verifier_stage="final",
            parser_confidence=1.0,
            command=config.test_command,
            accepted=accepted,
            pass_ratio=1.0 if accepted else 0.0,
            fail_to_pass={
                "passed": len(resolved_verifier_plan.initial_fail_to_pass_tests) if accepted else 0,
                "total": len(resolved_verifier_plan.initial_fail_to_pass_tests),
            },
            pass_to_pass={
                "passed": len(resolved_verifier_plan.initial_pass_to_pass_tests) if accepted else 0,
                "total": len(resolved_verifier_plan.initial_pass_to_pass_tests),
            },
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
) -> None:
    payload = {
        "schema_version": "repo_harness_stage16f3_run_episode_task_summary_v0",
        "run_id": request.run_id,
        "task_id": request.task_id,
        "llm_gateway_route": request.llm_gateway_route,
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
