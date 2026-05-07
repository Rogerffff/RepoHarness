"""Eval Runner：单任务和批量评测编排。"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Literal

from repo_harness.agent_loop import AgentLoop
from repo_harness.budget import BudgetManager
from repo_harness.config import RunConfig, load_run_config
from repo_harness.context import ContextBuilder
from repo_harness.errors import ConfigError, RepoHarnessError, WorkspaceError
from repo_harness.evaluation.metrics import (
    build_metrics_record,
    derive_final_verifier_status,
)
from repo_harness.evaluation.outcome_policy import OUTCOME_POLICY_VERSION, derive_run_outcome
from repo_harness.evaluation.schemas import BaselineResult, ResolvedVerifierPlan
from repo_harness.model_client import create_model_client, provider_options_from_model_config
from repo_harness.permissions import PermissionContext
from repo_harness.reward import compute_reward_metadata
from repo_harness.run_metadata.fingerprint import build_local_environment_fingerprint
from repo_harness.run_metadata.tool_snapshot import write_tool_schema_snapshot
from repo_harness.run_metadata.writer import (
    build_run_config_facts,
    build_run_metadata,
    write_run_config_facts,
    write_run_metadata,
)
from repo_harness.tasks import RunnableTask, load_task
from repo_harness.tools import ToolExecutionContext, ToolExecutor, ToolOutputLimits
from repo_harness.trajectory import MetricsRecord, RunRecorder, TrajectoryEvent
from repo_harness.v3_agent_runtime import (
    build_swebench_like_baseline_verifier,
    load_swebench_like_runtime_plan,
    run_swebench_like_final_verifier,
)
from repo_harness.pre_verl_agentloop import (
    PRE_VERL_AGENTLOOP_BASELINE_SOURCE,
    build_pre_verl_baseline_verifier,
    load_pre_verl_swebench_dev_runtime_plan,
    run_pre_verl_swebench_dev_final_verifier,
)
from repo_harness.pre_verl_run_facts import (
    PRE_VERL_FORBIDDEN_SCAFFOLD_IDS,
    provider_axis_scope_for_config,
    write_permission_policy_manifest,
    write_source_snapshot_and_context_index,
)
from repo_harness.verifier import PytestVerifier, build_error_verifier_result
from repo_harness.verifier.parser_policy import VerifierParserPolicy
from repo_harness.workspace import (
    ExecutionResult,
    WorkspaceAdapter,
    build_workspace_backend_status,
    create_workspace_adapter,
)
from repo_harness.workspace.backend_factory import DockerBackendInitializationError
from repo_harness.scaffolds import (
    build_scaffold,
    resolve_allowed_tools,
    resolve_feedback_policy,
    tool_registry_for_allowed_tools,
)


InjectInterruptPoint = Literal["baseline", "agent_loop", "final_verifier"]


class InjectedInterruptError(RepoHarnessError):
    """Raised after writing structured interrupted run facts for V3 resume tests."""

    def __init__(self, *, phase: InjectInterruptPoint, run_dir: Path) -> None:
        self.phase = phase
        self.run_dir = run_dir
        super().__init__(f"Injected V3 experiment interruption after {phase}: {run_dir}")


def run_task(
    task_path: str | Path,
    *,
    config_path: str | Path,
    output_dir: str | Path | None = None,
    run_id: str | None = None,
    inject_interrupt_after: InjectInterruptPoint | None = None,
) -> Path:
    run_started = time.monotonic()
    config = load_run_config(config_path, output_dir=output_dir)
    task_deadline_monotonic = run_started + config.runtime.task_timeout_sec
    if config.model.provider not in {"replay", "fake", "mock", "deepseek", "openai"}:
        raise ConfigError("Stage 11 run-task 只支持 model.provider=replay、fake、mock、deepseek；openai 只允许作为 DeepSeek fallback 内部运行。")
    if config.model.provider == "openai" and not _is_openai_fallback_config(config.model.provider_specific_options):
        raise ConfigError("model.provider=openai 只允许作为 DeepSeek fallback smoke run，不能作为 primary provider。")
    if config.evaluation.final_verifier_mode != "strict_patch_replay":
        raise ConfigError("RepoHarness 第一版正式评测只支持 final_verifier_mode=strict_patch_replay。")
    loaded = load_task(task_path)
    pre_verl_runtime_plan = load_pre_verl_swebench_dev_runtime_plan(loaded.runnable_task)
    swebench_like_runtime_plan = load_swebench_like_runtime_plan(loaded.runnable_task)
    effective_setup_command = (
        pre_verl_runtime_plan.setup_shell
        if pre_verl_runtime_plan is not None and pre_verl_runtime_plan.setup_shell
        else loaded.runnable_task.setup_command
    )
    scaffold = build_scaffold(config.runtime.scaffold_id)
    feedback_policy = resolve_feedback_policy(
        run_config=config,
        scaffold=scaffold,
        task=loaded.runnable_task,
    )
    allowed_tools = resolve_allowed_tools(scaffold=scaffold, feedback_policy=feedback_policy)
    actual_run_id = run_id or f"{config.run_id_prefix}_{loaded.runnable_task.task_id}"
    run_dir = Path(config.workspace.output_dir) / actual_run_id
    if run_dir.exists():
        raise ConfigError(f"run directory 已存在，请使用新的 run id 或先手动归档：{run_dir}")
    with RunRecorder(
        actual_run_id,
        run_dir,
        task_id=loaded.runnable_task.task_id,
        max_artifact_bytes=config.workspace.max_artifact_bytes,
    ) as recorder:
        recorder.append_event(
            TrajectoryEvent(
                event_id=recorder.next_event_id("run"),
                timestamp=_timestamp(),
                run_id=actual_run_id,
                task_id=loaded.runnable_task.task_id,
                event_type="run_started",
                data={"task_path": str(task_path)},
            )
        )
        _write_json(run_dir / "task.yaml", loaded.definition.model_dump(mode="json"))
        try:
            adapter = create_workspace_adapter(config=config, run_id=actual_run_id, run_dir=run_dir)
        except DockerBackendInitializationError as exc:
            _write_docker_backend_initialization_failure(
                run_dir=run_dir,
                config=config,
                reason=exc.structured_failure_reason,
                message=str(exc),
            )
            recorder.append_event(
                TrajectoryEvent(
                    event_id=recorder.next_event_id("docker"),
                    timestamp=_timestamp(),
                    run_id=actual_run_id,
                    task_id=loaded.runnable_task.task_id,
                    event_type="docker_backend_initialization_failed",
                    severity="error",
                    error_type=exc.structured_failure_reason,
                    data={
                        "failure_reason": exc.structured_failure_reason,
                        "message": str(exc),
                        "execution_mode": config.runtime.execution_mode,
                    },
                )
            )
            raise WorkspaceError(str(exc)) from exc
        _write_backend_status_if_supported(adapter, config)
        verifier = PytestVerifier(adapter)
        source = adapter.create_source_checkout(loaded.runnable_task)
        _record_docker_phase_noop(
            adapter=adapter,
            workspace_path=source,
            recorder=recorder,
            command_semantics="source_checkout",
        )
        setup = adapter.create_setup_workspace(source)
        setup_result = _run_setup_command(
            adapter=adapter,
            setup_workspace=setup,
            task=loaded.runnable_task,
            setup_command=effective_setup_command,
            recorder=recorder,
        )
        if setup_result is None:
            _record_docker_phase_noop(
                adapter=adapter,
                workspace_path=setup,
                recorder=recorder,
                command_semantics="setup",
            )
        dependency_strategy = (
            "rerun_setup"
            if effective_setup_command and _setup_succeeded(setup_result)
            else "none"
        )
        dependency_state = adapter.capture_dependency_state(strategy=dependency_strategy)
        _write_json(run_dir / "dependency_state.json", dependency_state.model_dump(mode="json"))
        dependency_state_ref = recorder.write_json_artifact(
            "dependency_state",
            dependency_state.model_dump(mode="json"),
            {"budget_policy": "preserve_json"},
        )
        if (
            (pre_verl_runtime_plan is not None or swebench_like_runtime_plan is not None)
            and setup_result is not None
            and not _setup_succeeded(setup_result)
        ):
            baseline_verifiers = [
                build_error_verifier_result(
                    command=effective_setup_command or "setup",
                    error_type="setup_failed" if not setup_result.timeout else "setup_timeout",
                    verifier_stage="baseline",
                    timeout=setup_result.timeout,
                    raw_output_ref=setup_result.output_artifact_ref,
                )
            ]
            baseline_status = "invalid"
            baseline_dependency_error = "setup_failed" if not setup_result.timeout else "setup_timeout"
        elif pre_verl_runtime_plan is not None:
            baseline_verifiers = [build_pre_verl_baseline_verifier(pre_verl_runtime_plan)]
            baseline_status = "valid"
            baseline_dependency_error = None
        elif swebench_like_runtime_plan is not None:
            baseline_verifiers = [build_swebench_like_baseline_verifier(swebench_like_runtime_plan)]
            baseline_status = "valid"
            baseline_dependency_error = None
        elif setup_result is not None and not _setup_succeeded(setup_result):
            baseline_verifiers = [
                build_error_verifier_result(
                    command=effective_setup_command or "setup",
                    error_type="setup_failed" if not setup_result.timeout else "setup_timeout",
                    verifier_stage="baseline",
                    timeout=setup_result.timeout,
                    raw_output_ref=setup_result.output_artifact_ref,
                )
            ]
        else:
            baseline_verifiers = [
                verifier.run_baseline(setup, loaded.verifier_config, recorder)
                for _ in range(2)
            ]
        baseline_verifier = baseline_verifiers[0]
        baseline_artifact_metadata = {"budget_policy": "preserve_json"}
        if pre_verl_runtime_plan is not None or swebench_like_runtime_plan is not None:
            baseline_artifact_metadata["redaction_status"] = "evaluator_only"
        baseline_ref = recorder.write_json_artifact(
            "baseline_verifier_results",
            {
                "results": [
                    result.model_dump(mode="json")
                    for result in baseline_verifiers
                ]
            },
            baseline_artifact_metadata,
        )
        if pre_verl_runtime_plan is None and swebench_like_runtime_plan is None:
            baseline_status, baseline_dependency_error = _derive_baseline_status(
                generated_file_count=len(loaded.runnable_task.generated_files_policy),
                verifier_results=baseline_verifiers,
                setup_result=setup_result,
            )
        baseline_artifact_refs = [
            result.raw_output_ref
            for result in baseline_verifiers
            if result.raw_output_ref is not None
        ]
        baseline = BaselineResult(
            task_id=loaded.runnable_task.task_id,
            status=baseline_status,
            setup_exit_code=setup_result.exit_code if setup_result else 0,
            baseline_exit_code=baseline_verifier.exit_code,
            baseline_verifier_result_ref=baseline_ref,
            setup_artifact_refs=(
                [setup_result.output_artifact_ref]
                if setup_result and setup_result.output_artifact_ref is not None
                else []
            ),
            baseline_artifact_refs=baseline_artifact_refs,
            parser_confidence=min(result.parser_confidence for result in baseline_verifiers),
            baseline_rerun_count=(
                0
                if setup_result is not None and not _setup_succeeded(setup_result)
                else len(baseline_verifiers)
            ),
            initial_fail_to_pass_tests=loaded.verifier_config.fail_to_pass_tests,
            initial_pass_to_pass_tests=loaded.verifier_config.pass_to_pass_tests,
            flaky_tests=(
                loaded.verifier_config.pass_to_pass_tests
                if baseline_status == "flaky"
                else []
            ),
            dependency_error=(
                baseline_dependency_error if baseline_status in {"invalid", "flaky"} else None
            ),
            dependency_state=dependency_state,
            agent_run_start_policy={
                "create_from": "source_checkout",
                "restore_dependency_state": dependency_strategy != "none",
                "diff_base_policy": "create_agent_start_snapshot_after_dependency_restore",
            },
        )
        _write_json(run_dir / "baseline.json", baseline.model_dump(mode="json"))
        recorder.append_event(
            TrajectoryEvent(
                event_id=recorder.next_event_id("baseline"),
                timestamp=_timestamp(),
                run_id=actual_run_id,
                task_id=loaded.runnable_task.task_id,
                event_type="baseline_completed",
                artifact_refs=[baseline_ref],
                data=baseline.model_dump(mode="json"),
            )
        )
        allowed_tool_registry = tool_registry_for_allowed_tools(allowed_tools)
        _, tool_schema_snapshot_ref, tool_protocol = write_tool_schema_snapshot(
            recorder,
            registry=allowed_tool_registry,
        )
        environment_fingerprint = build_local_environment_fingerprint(
            task_definition=loaded.definition,
            source_checkout=source,
            dependency_state=dependency_state,
            dependency_state_ref=dependency_state_ref,
            setup_artifact_hash=(
                setup_result.output_artifact_ref.sha256
                if setup_result is not None and setup_result.output_artifact_ref is not None
                else ("missing" if setup_result is not None else "none")
            ),
            command_timeout_sec=config.workspace.default_command_timeout_sec,
            network_policy=config.workspace.network_policy,
            source_checkout_facts=(
                getattr(adapter, "last_source_checkout").facts
                if getattr(adapter, "last_source_checkout", None) is not None
                else None
            ),
            execution_mode=config.runtime.execution_mode,
        )
        permission_policy_manifest_ref = None
        source_snapshot_ref = None
        repo_context_index_ref = None
        provider_axis_scope = None
        baseline_source = None
        forbidden_scaffold_ids: list[str] = []
        if pre_verl_runtime_plan is not None:
            permission_policy_manifest_ref = write_permission_policy_manifest(
                recorder=recorder,
                config=config,
                feedback_policy=feedback_policy,
                allowed_tools=allowed_tools,
            )
            source_snapshot_ref, repo_context_index_ref = write_source_snapshot_and_context_index(
                recorder=recorder,
                task_definition=loaded.definition,
                config=config,
                scaffold=scaffold,
                source_checkout=source,
                allowed_tools=allowed_tools,
            )
            provider_axis_scope = provider_axis_scope_for_config(config)
            baseline_source = PRE_VERL_AGENTLOOP_BASELINE_SOURCE
            forbidden_scaffold_ids = PRE_VERL_FORBIDDEN_SCAFFOLD_IDS
        run_config_facts = build_run_config_facts(
            run_id=actual_run_id,
            task_definition=loaded.definition,
            config=config,
            scaffold=scaffold,
            feedback_policy=feedback_policy,
            tool_protocol=tool_protocol,
            environment_fingerprint=environment_fingerprint,
            permission_policy_manifest_ref=permission_policy_manifest_ref,
            source_snapshot_ref=source_snapshot_ref,
            repo_context_index_ref=repo_context_index_ref,
            provider_axis_scope=provider_axis_scope,
            baseline_source=baseline_source,
            forbidden_scaffold_ids=forbidden_scaffold_ids,
        )
        run_config_facts_ref = write_run_config_facts(run_dir, run_config_facts)
        recorder.append_event(
            TrajectoryEvent(
                event_id=recorder.next_event_id("run_config_facts"),
                timestamp=_timestamp(),
                run_id=actual_run_id,
                task_id=loaded.runnable_task.task_id,
                event_type="run_config_facts_written",
                data={"run_config_facts_ref": run_config_facts_ref.model_dump(mode="json")},
            )
        )
        if inject_interrupt_after == "baseline":
            _interrupt_run_for_v3_resume(
                phase="baseline",
                run_id=actual_run_id,
                task_id=loaded.runnable_task.task_id,
                run_dir=run_dir,
                recorder=recorder,
                adapter=adapter,
                config=config,
            )
        if not baseline.can_enter_agent_run:
            _finalize_quality_gate_run(
                run_id=actual_run_id,
                task_id=loaded.runnable_task.task_id,
                baseline=baseline,
                run_dir=run_dir,
                recorder=recorder,
                run_config_facts_ref=run_config_facts_ref,
                tool_protocol=tool_protocol,
            )
            _write_backend_status_if_supported(adapter, config)
            adapter.cleanup_workspaces()
            return run_dir
        resolved_plan = ResolvedVerifierPlan(
            verifier_config=loaded.verifier_config,
            initial_fail_to_pass_tests=baseline.initial_fail_to_pass_tests,
            initial_pass_to_pass_tests=baseline.initial_pass_to_pass_tests,
            flaky_tests=[],
            parser_confidence=baseline.parser_confidence,
            resolved_verifier_plan_id=f"{actual_run_id}_verifier_plan",
        )
        _write_json(run_dir / "resolved_verifier_plan.json", resolved_plan.model_dump(mode="json"))
        run_workspace = adapter.create_agent_workspace(
            task=loaded.runnable_task,
            source_checkout=source,
            dependency_state=dependency_state,
            setup_command=effective_setup_command,
            setup_timeout_sec=loaded.runnable_task.timeouts.setup_timeout_sec,
            recorder=recorder,
        )
        initial_messages = ContextBuilder().build_initial_messages(
            task=loaded.runnable_task,
            workspace=run_workspace,
            run_config=config,
            resolved_verifier_plan=resolved_plan,
            allowed_tools=allowed_tools,
            scaffold=scaffold,
            workspace_facade=adapter,
        )
        replay_path = config.model.replay_script_path
        if config.model.provider in {"replay", "fake"} and replay_path is None:
            raise ConfigError("replay/fake run-task 需要 model.replay_script_path。")
        model = create_model_client(config.model)
        budget_manager = BudgetManager.from_run_config(config)
        tool_context = ToolExecutionContext(
            run_id=actual_run_id,
            task_id=loaded.runnable_task.task_id,
            workspace_facade=adapter,
            run_workspace=run_workspace,
            artifact_writer=recorder,
            permission_context=PermissionContext(
                mode=config.runtime.permission_mode,
                network_policy=config.workspace.network_policy,
                test_command=resolved_plan.verifier_config.test_command,
                test_feedback_policy=feedback_policy.resolved_test_feedback_policy.value,
            ),
            verifier_feedback_facade=verifier,
            resolved_verifier_plan=resolved_plan,
            output_limits=ToolOutputLimits(
                max_tool_output_chars=config.workspace.max_tool_output_chars,
            ),
            test_feedback_policy=feedback_policy.resolved_test_feedback_policy.value,
            feedback_tests_passed_policy=feedback_policy.resolved_feedback_tests_passed_policy,
            budget_manager=budget_manager,
        )
        loop_state = AgentLoop(
            model_client=model,
            tool_executor=ToolExecutor(),
            scaffold=scaffold,
            allowed_tool_names=allowed_tools,
            test_feedback_policy=feedback_policy.resolved_test_feedback_policy.value,
            feedback_tests_passed_policy=feedback_policy.resolved_feedback_tests_passed_policy,
            hidden_feedback_visible_to_model=feedback_policy.hidden_feedback_visible_to_model,
        ).run(
            run_id=actual_run_id,
            task_id=loaded.runnable_task.task_id,
            initial_messages=initial_messages,
            tool_context=tool_context,
            recorder=recorder,
            max_turns=config.runtime.max_turns,
            context_config=config.context_management,
            budget_manager=budget_manager,
            task_deadline_monotonic=task_deadline_monotonic,
            run_config_facts_ref=run_config_facts_ref,
            tool_schema_snapshot_ref=tool_schema_snapshot_ref,
            provider_options=provider_options_from_model_config(config.model),
            generation_config={
                "temperature": config.model.temperature,
                "max_output_tokens": config.model.max_output_tokens,
                "seed": config.runtime.seed,
            },
            provider_model_settings={},
            request_timeout_seconds=config.runtime.task_timeout_sec,
            raw_request_logging_policy=config.model.provider_request_logging,
            retry_policy=config.model.retry_policy,
        )
        if inject_interrupt_after == "agent_loop":
            _interrupt_run_for_v3_resume(
                phase="agent_loop",
                run_id=actual_run_id,
                task_id=loaded.runnable_task.task_id,
                run_dir=run_dir,
                recorder=recorder,
                adapter=adapter,
                config=config,
        )
        capture = adapter.capture_final_patch(run_workspace, recorder=recorder)
        task_timeout_expired = _task_timeout_expired(task_deadline_monotonic)
        if task_timeout_expired:
            _append_task_timeout_event(
                run_id=actual_run_id,
                task_id=loaded.runnable_task.task_id,
                recorder=recorder,
                phase="before_final_verifier",
            )
        if task_timeout_expired and pre_verl_runtime_plan is not None:
            final_verifier = run_pre_verl_swebench_dev_final_verifier(
                plan=pre_verl_runtime_plan,
                source_checkout=source,
                dependency_state=dependency_state,
                final_patch_path=capture.patch_path,
                run_dir=run_dir,
                adapter=adapter,
                recorder=recorder,
                setup_command=effective_setup_command,
                agent_stop_reason="task_timeout",
            )
        elif task_timeout_expired:
            final_verifier = build_error_verifier_result(
                command="strict_patch_replay",
                error_type="task_timeout",
                verifier_stage="final",
                timeout=True,
            )
        elif pre_verl_runtime_plan is not None:
            final_verifier = run_pre_verl_swebench_dev_final_verifier(
                plan=pre_verl_runtime_plan,
                source_checkout=source,
                dependency_state=dependency_state,
                final_patch_path=capture.patch_path,
                run_dir=run_dir,
                adapter=adapter,
                recorder=recorder,
                setup_command=effective_setup_command,
                agent_stop_reason=loop_state.agent_stop_reason,
            )
        elif swebench_like_runtime_plan is not None:
            try:
                final_verifier = run_swebench_like_final_verifier(
                    plan=swebench_like_runtime_plan,
                    final_patch_path=capture.patch_path,
                    run_dir=run_dir,
                    adapter=adapter,
                    recorder=recorder,
                )
            except WorkspaceError:
                final_verifier = build_error_verifier_result(
                    command="swebench_like_strict_patch_replay",
                    error_type="patch_apply_failed",
                    verifier_stage="final",
                )
        else:
            try:
                verification = adapter.create_verification_workspace(
                    source_checkout=source,
                    dependency_state=dependency_state,
                    final_patch_path=capture.patch_path,
                    setup_command=loaded.runnable_task.setup_command,
                    setup_timeout_sec=loaded.runnable_task.timeouts.setup_timeout_sec,
                    recorder=recorder,
                )
                final_verifier = verifier.run_final(verification, resolved_plan, recorder)
            except WorkspaceError as exc:
                replay_error = (
                    "patch_apply_failed"
                    if "final.patch" in str(exc)
                    else "verification_workspace_error"
                )
                final_verifier = build_error_verifier_result(
                    command="strict_patch_replay",
                    error_type=replay_error,
                    verifier_stage="final",
                )
        final_artifact_metadata = {"budget_policy": "preserve_json"}
        if pre_verl_runtime_plan is not None or swebench_like_runtime_plan is not None:
            final_artifact_metadata["redaction_status"] = "evaluator_only"
        final_verifier_ref = recorder.write_json_artifact(
            "final_verifier_result",
            final_verifier.model_dump(mode="json"),
            final_artifact_metadata,
        )
        recorder.append_event(
            TrajectoryEvent(
                event_id=recorder.next_event_id("verifier"),
                timestamp=_timestamp(),
                run_id=actual_run_id,
                task_id=loaded.runnable_task.task_id,
                event_type="verifier_final",
                artifact_refs=[final_verifier_ref],
                data=final_verifier.model_dump(mode="json"),
            )
        )
        if inject_interrupt_after == "final_verifier":
            _interrupt_run_for_v3_resume(
                phase="final_verifier",
                run_id=actual_run_id,
                task_id=loaded.runnable_task.task_id,
                run_dir=run_dir,
                recorder=recorder,
                adapter=adapter,
                config=config,
            )
        reward = compute_reward_metadata(
            final_verifier,
            patch_stats=capture.patch_stats,
            event_counts={
                "turn_count": loop_state.turn_count,
                "tool_call_count": loop_state.tool_call_count,
                "test_run_count": _count_test_runs(loop_state.messages),
            },
            source_refs={
                "final_verifier_ref": final_verifier_ref.model_dump(mode="json"),
                "final_patch_ref": capture.patch_artifact_ref.model_dump(mode="json"),
                "final_diff_ref": capture.diff_artifact_ref.model_dump(mode="json"),
                "events_ref": {
                    "kind": "events",
                    "relative_path": "events.jsonl",
                    "exists": (run_dir / "events.jsonl").exists(),
                },
            },
        )
        recorder.write_json_artifact(
            "reward_metadata",
            reward.model_dump(mode="json"),
            {"budget_policy": "preserve_json"},
        )
        final_status = derive_final_verifier_status(final_verifier)
        if pre_verl_runtime_plan is not None:
            final_status = _pre_verl_boundary_final_verifier_status(run_dir) or final_status
        run_outcome = derive_run_outcome(
            baseline_status=baseline.status,
            final_verifier_status=final_status,
            agent_stop_reason=loop_state.agent_stop_reason,
            final_verifier_ran=True,
        )
        metrics = build_metrics_record(
            final_verifier=final_verifier,
            run_outcome=run_outcome,
            final_verifier_status=final_status,
            agent_stop_reason=loop_state.agent_stop_reason,
            turn_count=loop_state.turn_count,
            tool_call_count=loop_state.tool_call_count,
            test_run_count=_count_test_runs(loop_state.messages),
            patch_stats=capture.patch_stats,
            permission_denial_count=loop_state.permission_denial_count,
            invalid_tool_call_count=loop_state.invalid_tool_call_count,
            feedback_verifier_accepted=loop_state.feedback_verifier_accepted,
            first_feedback_accept_turn=loop_state.first_feedback_accept_turn,
            first_feedback_accept_ref=loop_state.first_feedback_accept_ref,
            feedback_tests_passed_policy=loop_state.feedback_tests_passed_policy,
            test_feedback_policy=loop_state.test_feedback_policy,
            hidden_feedback_visible_to_model=loop_state.hidden_feedback_visible_to_model,
            public_tests_ran=loop_state.public_tests_ran,
            hidden_feedback_ran=loop_state.hidden_feedback_ran,
        )
        metrics.interaction_efficiency.update(
            {
                "baseline_status": baseline.status,
                "final_verifier_mode": config.evaluation.final_verifier_mode,
            }
        )
        _write_json(run_dir / "verifier.json", final_verifier.model_dump(mode="json"))
        _write_json(run_dir / "reward.json", reward.model_dump(mode="json"))
        _write_json(run_dir / "metrics.json", metrics.model_dump(mode="json"))
        summary = (
            f"# RepoHarness Run Summary\n\n"
            f"- run_id: {actual_run_id}\n"
            f"- task_id: {loaded.runnable_task.task_id}\n"
            f"- baseline_status: {baseline.status}\n"
            f"- agent_stop_reason: {loop_state.agent_stop_reason}\n"
            f"- final_verifier_status: {final_status}\n"
            f"- final_verifier_mode: {config.evaluation.final_verifier_mode}\n"
            f"- run_outcome: {run_outcome}\n"
            f"- outcome_policy_version: {OUTCOME_POLICY_VERSION}\n"
            f"- permission_denial_count: {loop_state.permission_denial_count}\n"
            f"{_permission_denial_summary(loop_state.permission_denial_reasons)}"
            f"{_patch_stats_summary(capture.patch_stats)}"
            f"- resolved_verifier_plan: resolved_verifier_plan.json\n"
            f"- run_config_facts: {run_config_facts_ref.relative_path}\n"
            f"- run_metadata: run_metadata.json\n"
            f"- final.patch: final.patch\n"
            f"- final.diff: final.diff\n"
        )
        recorder.append_event(
            TrajectoryEvent(
                event_id=recorder.next_event_id("run"),
                timestamp=_timestamp(),
                run_id=actual_run_id,
                task_id=loaded.runnable_task.task_id,
                event_type="run_finished",
                data={
                    "agent_stop_reason": loop_state.agent_stop_reason,
                    "baseline_status": baseline.status,
                    "final_verifier_status": final_status,
                    "final_verifier_mode": config.evaluation.final_verifier_mode,
                    "run_outcome": run_outcome,
                    "outcome_policy_version": OUTCOME_POLICY_VERSION,
                },
            )
        )
        run_metadata = build_run_metadata(
            run_dir=run_dir,
            run_id=actual_run_id,
            task_id=loaded.runnable_task.task_id,
            run_config_facts_ref=run_config_facts_ref,
            tool_protocol=tool_protocol,
            baseline=baseline,
            run_outcome=run_outcome,
            final_verifier_status=final_status,
            agent_stop_reason=loop_state.agent_stop_reason,
            final_verifier_mode=config.evaluation.final_verifier_mode,
        )
        write_run_metadata(run_dir, run_metadata)
        _write_backend_status_if_supported(adapter, config)
        recorder.finalize_run(summary)
        adapter.cleanup_workspaces()
    return run_dir


def _pre_verl_boundary_final_verifier_status(run_dir: Path) -> str | None:
    boundary_path = run_dir / "final_verifier_boundary.json"
    if not boundary_path.exists():
        return None
    try:
        payload = json.loads(boundary_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    status = payload.get("final_verifier_status")
    if status in {"accepted", "rejected", "not_executed", "timeout", "error"}:
        return str(status)
    return None


def run_batch(
    *,
    config_path: str | Path,
    output_dir: str | Path | None = None,
) -> Path:
    """顺序运行 RunConfig.tasks，并写出 batch_manifest.json。"""

    config = load_run_config(config_path, for_batch=True, output_dir=output_dir)
    if not config.tasks:
        raise ConfigError("run-batch 需要 RunConfig.tasks 至少包含一个任务。")
    batch_dir = Path(config.workspace.output_dir)
    batch_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    for index, task_path in enumerate(config.tasks, start=1):
        task_id = _load_task_id_for_manifest(task_path)
        run_id = f"{config.run_id_prefix}_{index:03d}_{task_id}"
        try:
            run_dir = run_task(
                task_path,
                config_path=config_path,
                output_dir=batch_dir,
                run_id=run_id,
            )
            metrics = _read_json(run_dir / "metrics.json")
            status = str(metrics.get("run_outcome", "unknown"))
            records.append(
                {
                    "task_path": str(task_path),
                    "task_id": task_id,
                    "run_id": run_id,
                    "run_dir": str(run_dir),
                    "status": status,
                    "agent_stop_reason": metrics.get("interaction_efficiency", {}).get(
                        "agent_stop_reason"
                    ),
                    "final_verifier_status": metrics.get("final_verifier_status"),
                    "failure_reason": None if status == "success" else status,
                    "key_artifacts": _batch_key_artifacts(run_dir),
                }
            )
        except RepoHarnessError as exc:
            records.append(
                {
                    "task_path": str(task_path),
                    "task_id": task_id,
                    "run_id": run_id,
                    "run_dir": str(batch_dir / run_id),
                    "status": "error",
                    "failure_reason": str(exc),
                    "key_artifacts": {},
                }
            )
    manifest = {
        "schema_version": "repo_harness_batch_manifest_v0",
        "config_path": str(config_path),
        "output_dir": str(batch_dir),
        "concurrency": config.evaluation.concurrency,
        "fail_on_invalid_task": config.evaluation.fail_on_invalid_task,
        "should_fail_command": any(record["status"] == "error" for record in records)
        or (
            config.evaluation.fail_on_invalid_task
            and any(record["status"] in {"invalid_task", "flaky_task"} for record in records)
        ),
        "runs": records,
    }
    manifest_path = batch_dir / "batch_manifest.json"
    _write_json(manifest_path, manifest)
    return manifest_path


def _interrupt_run_for_v3_resume(
    *,
    phase: InjectInterruptPoint,
    run_id: str,
    task_id: str,
    run_dir: Path,
    recorder: RunRecorder,
    adapter: WorkspaceAdapter,
    config: RunConfig,
) -> None:
    facts = {
        "schema_version": "repo_harness_v3_interrupted_run_facts_v0",
        "run_id": run_id,
        "task_id": task_id,
        "interrupted_after": phase,
        "created_at": _timestamp(),
        "resume_policy": "run_level_continuation_new_run_id",
        "run_metadata_expected": False,
        "required_files": {
            "transcript_jsonl": (run_dir / "transcript.jsonl").exists(),
            "events_jsonl": (run_dir / "events.jsonl").exists(),
            "artifacts_json": (run_dir / "artifacts.json").exists(),
            "run_config_facts_json": (run_dir / "run_config_facts.json").exists(),
            "run_metadata_json": (run_dir / "run_metadata.json").exists(),
        },
        "event_offset": _jsonl_record_count(run_dir / "events.jsonl"),
        "transcript_offset": _jsonl_record_count(run_dir / "transcript.jsonl"),
        "resume_eligibility": "eligible",
        "blocked_resume_input_categories": [
            "evaluator_only_verifier_outputs",
            "post_run_scoring_artifacts",
            "terminal_result_facts",
            "evaluator_only_failure_details",
        ],
    }
    _write_json(run_dir / "interrupted_run_facts.json", facts)
    recorder.append_event(
        TrajectoryEvent(
            event_id=recorder.next_event_id("run"),
            timestamp=_timestamp(),
            run_id=run_id,
            task_id=task_id,
            event_type="run_interrupted",
            severity="warning",
            error_type="injected_v3_resume_interrupt",
            data=facts,
        )
    )
    _write_backend_status_if_supported(adapter, config)
    adapter.cleanup_workspaces()
    recorder.mark_interrupted(
        "# RepoHarness Interrupted Run\n\n"
        f"- run_id: {run_id}\n"
        f"- task_id: {task_id}\n"
        f"- interrupted_after: {phase}\n"
        "- run_metadata: not written before final metadata boundary\n"
    )
    raise InjectedInterruptError(phase=phase, run_dir=run_dir)


def _run_setup_command(
    *,
    adapter: WorkspaceAdapter,
    setup_workspace: Path,
    task: RunnableTask,
    setup_command: str | None = None,
    recorder: RunRecorder,
) -> ExecutionResult | None:
    command = setup_command if setup_command is not None else task.setup_command
    if not command:
        return None
    result = adapter.run_command(
        setup_workspace,
        command,
        timeout_sec=task.timeouts.setup_timeout_sec,
        recorder=recorder,
        command_semantics="setup",
        allow_shell=_requires_shell_command(command),
    )
    recorder.append_event(
        TrajectoryEvent(
            event_id=recorder.next_event_id("setup"),
            timestamp=_timestamp(),
            run_id=recorder.run_id,
            task_id=task.task_id,
            event_type="setup_completed",
            severity="warning" if not _setup_succeeded(result) else "info",
            error_type="setup_failed" if not _setup_succeeded(result) else None,
            artifact_refs=[result.output_artifact_ref] if result.output_artifact_ref else [],
            data=result.model_dump(mode="json"),
        )
    )
    return result


def _requires_shell_command(command: str | list[str]) -> bool:
    if not isinstance(command, str):
        return False
    stripped = command.strip()
    return any(marker in stripped for marker in ("&&", "||", ";", "|")) or stripped.startswith(
        (". ", "source ")
    )


def _jsonl_record_count(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _write_backend_status_if_supported(adapter: WorkspaceAdapter, config: RunConfig) -> None:
    writer = getattr(adapter, "write_backend_status", None)
    if writer is None:
        return
    writer(
        evaluation_concurrency=config.evaluation.concurrency,
        swebench_like_effective_max_workers=config.swebench_like.effective_max_workers,
    )


def _write_docker_backend_initialization_failure(
    *,
    run_dir: Path,
    config: RunConfig,
    reason: str,
    message: str,
) -> None:
    status = build_workspace_backend_status(
        mode="docker_backend",
        docker_available=False,
        docker_available_reason=f"{reason}:{message}",
        evaluation_concurrency=config.evaluation.concurrency,
        swebench_like_effective_max_workers=config.swebench_like.effective_max_workers,
        requested_container_platform=config.runtime.docker_backend.requested_container_platform,
        network_policy=config.runtime.docker_backend.network_policy,
        mount_policy=config.runtime.docker_backend.mount_policy,
        command_timeout_sec=config.runtime.docker_backend.command_timeout_sec,
        cleanup_policy=config.runtime.docker_backend.cleanup_policy,
        cleanup_status="failed",
    )
    payload = status.model_dump(mode="json")
    _write_json(run_dir / "docker_backend_status.json", payload)
    _write_json(run_dir / "docker_stage_status.json", payload)


def _record_docker_phase_noop(
    *,
    adapter: WorkspaceAdapter,
    workspace_path: str | Path,
    recorder: RunRecorder,
    command_semantics: str,
) -> None:
    backend = getattr(adapter, "backend", None)
    if getattr(backend, "value", backend) != "docker":
        return
    adapter.run_command(
        workspace_path,
        ["python", "-c", "pass"],
        timeout_sec=30,
        recorder=recorder,
        command_semantics=command_semantics,
    )


def _is_openai_fallback_config(options: dict[str, Any]) -> bool:
    return (
        options.get("requested_provider") == "deepseek"
        and options.get("actual_provider") == "openai"
        and bool(options.get("fallback_reason"))
        and bool(options.get("fallback_policy_version"))
    )


def _setup_succeeded(result: ExecutionResult | None) -> bool:
    return result is None or (result.exit_code == 0 and not result.timeout)


def _derive_baseline_status(
    *,
    generated_file_count: int = 0,
    verifier_results: list[object],
    setup_result: ExecutionResult | None,
) -> tuple[str, str | None]:
    if not _setup_succeeded(setup_result):
        return "invalid", "setup_failed"
    result = verifier_results[0]
    for candidate in verifier_results:
        hard_error = _baseline_hard_error(candidate, generated_file_count)
        if hard_error is not None:
            return "invalid", hard_error
    if len({_baseline_signature(candidate) for candidate in verifier_results}) > 1:
        return "flaky", "flaky_baseline_inconsistent"
    if getattr(result, "timeout", False):
        return "invalid", "test_timeout"
    parser_policy_issue = _baseline_parser_policy_issue(result)
    if parser_policy_issue is not None:
        return "invalid", parser_policy_issue
    if getattr(result, "parser_confidence", 0.0) < 0.5:
        return "invalid", "low_parser_confidence"
    if getattr(result, "error_type", None) in {
        "dependency_error",
        "low_parser_confidence",
    }:
        return "invalid", getattr(result, "error_type", None)
    if getattr(result, "error_type", None) == "test_command_error" and generated_file_count == 0:
        return "invalid", "test_command_error"
    pass_to_pass = getattr(result, "pass_to_pass", {"passed": 0, "total": 0})
    if pass_to_pass.get("passed", 0) < pass_to_pass.get("total", 0):
        return "invalid", "pass_to_pass_initial_failure"
    fail_to_pass = getattr(result, "fail_to_pass", {"passed": 0, "total": 0})
    if fail_to_pass.get("total", 0) and fail_to_pass.get("passed", 0) == fail_to_pass.get("total", 0):
        return "invalid", "fail_to_pass_initially_passing"
    return "valid", None


def _baseline_hard_error(result: object, generated_file_count: int) -> str | None:
    if getattr(result, "timeout", False):
        return "test_timeout"
    parser_policy_issue = _baseline_parser_policy_issue(result)
    if parser_policy_issue is not None:
        return parser_policy_issue
    error_type = getattr(result, "error_type", None)
    if error_type in {"dependency_error", "low_parser_confidence"}:
        return str(error_type)
    if error_type == "test_command_error" and generated_file_count == 0:
        return "test_command_error"
    return None


def _baseline_parser_policy_issue(result: object) -> str | None:
    parser_id = str(getattr(result, "parser_id", "pytest") or "pytest")
    if parser_id not in {"pytest", "generic_exit_code"}:
        return "unsupported_parser"
    policy = VerifierParserPolicy(
        parser_id=parser_id,  # type: ignore[arg-type]
        parser_version=str(getattr(result, "parser_version", "unknown")),
        low_confidence_threshold=0.5,
    )
    confidence = float(getattr(result, "parser_confidence", 0.0))
    if policy.block_low_confidence and confidence < policy.low_confidence_threshold:
        return "low_parser_confidence"
    return None


def _baseline_signature(result: object) -> str:
    test_cases = getattr(result, "test_cases", [])
    case_signature = tuple(
        (getattr(case, "test_id", None), getattr(case, "status", None))
        for case in test_cases
    )
    payload = {
        "accepted": getattr(result, "accepted", None),
        "exit_code": getattr(result, "exit_code", None),
        "timeout": getattr(result, "timeout", None),
        "error_type": getattr(result, "error_type", None),
        "pass_ratio": getattr(result, "pass_ratio", None),
        "fail_to_pass": getattr(result, "fail_to_pass", None),
        "pass_to_pass": getattr(result, "pass_to_pass", None),
        "test_cases": case_signature,
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _finalize_quality_gate_run(
    *,
    run_id: str,
    task_id: str,
    baseline: BaselineResult,
    run_dir: Path,
    recorder: RunRecorder,
    run_config_facts_ref,
    tool_protocol,
) -> None:
    run_outcome = derive_run_outcome(
        baseline_status=baseline.status,
        final_verifier_status="skipped",
        final_verifier_ran=False,
    )
    agent_stop_reason = (
        "skipped_flaky_baseline" if baseline.status == "flaky" else "skipped_invalid_baseline"
    )
    reason = _quality_gate_reason(baseline)
    metrics = MetricsRecord(
        run_outcome=run_outcome,  # type: ignore[arg-type]
        final_verifier_status="skipped",
        interaction_efficiency={
            "agent_stop_reason": agent_stop_reason,
            "baseline_status": baseline.status,
            "quality_gate_reason": reason,
            "resolved_verifier_plan": "not_generated",
            "final_verifier_mode": "skipped",
            "outcome_policy_version": OUTCOME_POLICY_VERSION,
        },
    )
    _write_json(run_dir / "metrics.json", metrics.model_dump(mode="json"))
    summary = (
        f"# RepoHarness Run Summary\n\n"
        f"- run_id: {run_id}\n"
        f"- task_id: {task_id}\n"
        f"- baseline_status: {baseline.status}\n"
        f"- quality_gate: blocked\n"
        f"- quality_gate_reason: {reason}\n"
        f"- agent_stop_reason: {agent_stop_reason}\n"
        f"- final_verifier_status: skipped\n"
        f"- final_verifier_mode: skipped\n"
        f"- run_outcome: {run_outcome}\n"
        f"- resolved_verifier_plan: not_generated\n"
        f"- run_config_facts: {run_config_facts_ref.relative_path}\n"
        f"- run_metadata: run_metadata.json\n"
        f"- outcome_policy_version: {OUTCOME_POLICY_VERSION}\n"
    )
    recorder.append_event(
        TrajectoryEvent(
            event_id=recorder.next_event_id("run"),
            timestamp=_timestamp(),
            run_id=run_id,
            task_id=task_id,
            event_type="run_finished",
            data={
                "agent_stop_reason": agent_stop_reason,
                "baseline_status": baseline.status,
                "final_verifier_status": "skipped",
                "run_outcome": run_outcome,
                "quality_gate_reason": reason,
                "resolved_verifier_plan": "not_generated",
                "outcome_policy_version": OUTCOME_POLICY_VERSION,
            },
        )
    )
    run_metadata = build_run_metadata(
        run_dir=run_dir,
        run_id=run_id,
        task_id=task_id,
        run_config_facts_ref=run_config_facts_ref,
        tool_protocol=tool_protocol,
        baseline=baseline,
        run_outcome=run_outcome,
        final_verifier_status="skipped",
        agent_stop_reason=agent_stop_reason,
        final_verifier_mode="skipped",
    )
    write_run_metadata(run_dir, run_metadata)
    recorder.finalize_run(summary)


def _quality_gate_reason(baseline: BaselineResult) -> str:
    if baseline.status == "flaky":
        return baseline.dependency_error or "flaky_baseline_inconsistent"
    if baseline.dependency_error:
        return baseline.dependency_error
    if baseline.parser_confidence < 0.5:
        return "low_parser_confidence"
    return "baseline_invalid"


def _write_json(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_task_id_for_manifest(task_path: str | Path) -> str:
    try:
        return load_task(task_path).runnable_task.task_id
    except RepoHarnessError:
        return Path(task_path).stem


def _batch_key_artifacts(run_dir: Path) -> dict[str, str]:
    artifacts: dict[str, str] = {}
    for name in [
        "summary.md",
        "metrics.json",
        "baseline.json",
        "verifier.json",
        "reward.json",
        "final.patch",
        "final.diff",
    ]:
        path = run_dir / name
        if path.exists():
            artifacts[name] = str(path)
    return artifacts


def _task_timeout_expired(task_deadline_monotonic: float) -> bool:
    return time.monotonic() >= task_deadline_monotonic


def _append_task_timeout_event(
    *,
    run_id: str,
    task_id: str,
    recorder: RunRecorder,
    phase: str,
) -> None:
    recorder.append_event(
        TrajectoryEvent(
            event_id=recorder.next_event_id("budget"),
            timestamp=_timestamp(),
            run_id=run_id,
            task_id=task_id,
            event_type="budget_exhausted",
            severity="warning",
            error_type="timeout",
            data={
                "reason": "timeout",
                "phase": phase,
            },
        )
    )


def _timestamp() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _count_test_runs(messages: list[dict[str, object]]) -> int:
    return sum(
        1
        for message in messages
        if message.get("role") == "tool"
        and message.get("effective_tool_name") == "run_tests"
        and message.get("status") in {"ok", "timeout"}
    )


def _permission_denial_summary(reasons: list[str]) -> str:
    if not reasons:
        return ""
    unique_reasons = list(dict.fromkeys(reasons))
    lines = ["- permission_denial_reasons:"]
    lines.extend(f"  - {reason}" for reason in unique_reasons[:5])
    return "\n".join(lines) + "\n"


def _patch_stats_summary(patch_stats: dict[str, object]) -> str:
    deleted = patch_stats.get("deleted_files") or []
    binary = patch_stats.get("binary_files") or []
    symlinks = patch_stats.get("symlink_files") or []
    untracked_text = patch_stats.get("untracked_text_files") or []
    if not any([deleted, binary, symlinks, untracked_text]):
        return ""
    return (
        "- patch_stats:\n"
        f"  - untracked_text_files: {len(untracked_text)}\n"
        f"  - deleted_files: {len(deleted)}\n"
        f"  - binary_files: {len(binary)}\n"
        f"  - symlink_files: {len(symlinks)}\n"
    )
