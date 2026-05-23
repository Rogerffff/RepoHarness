"""Eval Runner：单任务和批量评测编排。"""

from __future__ import annotations

import json
import re
import shlex
import time
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from repo_harness.agent_loop import AgentLoop
from repo_harness.budget import BudgetManager
from repo_harness.config import RunConfig, load_run_config
from repo_harness.context import ContextBuilder
from repo_harness.errors import ConfigError, RepoHarnessError, WorkspaceError
from repo_harness.schema_base import stable_hash
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
from repo_harness.tasks import (
    RunnableTask,
    build_public_environment_context,
    load_task,
    write_public_environment_context_artifacts,
)
from repo_harness.tools import ToolExecutionContext, ToolExecutor, ToolOutputLimits, ToolPolicy
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
    validate_pre_verl_run_config_entry,
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
        raise ConfigError("Stage 11 run-task 只支持 model.provider=replay、fake、mock、deepseek、openai。")
    if config.evaluation.final_verifier_mode != "strict_patch_replay":
        raise ConfigError("RepoHarness 第一版正式评测只支持 final_verifier_mode=strict_patch_replay。")
    loaded = load_task(task_path)
    scaffold = build_scaffold(config.runtime.scaffold_id)
    feedback_policy = resolve_feedback_policy(
        run_config=config,
        scaffold=scaffold,
        task=loaded.runnable_task,
    )
    allowed_tools = resolve_allowed_tools(scaffold=scaffold, feedback_policy=feedback_policy)
    preflight_report = validate_pre_verl_run_config_entry(
        task_definition_path=task_path,
        config_path=config_path,
        definition=loaded.definition,
        run_config=config,
        expected_resolved_tools=allowed_tools,
    )
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
        _write_json(run_dir / "run_config_preflight_report.json", preflight_report)
        recorder.append_event(
            TrajectoryEvent(
                event_id=recorder.next_event_id("run_config_preflight"),
                timestamp=_timestamp(),
                run_id=actual_run_id,
                task_id=loaded.runnable_task.task_id,
                event_type="run_config_preflight_completed",
                severity="error" if not preflight_report["passed"] else "info",
                data={
                    "preflight_policy_version": preflight_report["preflight_policy_version"],
                    "passed": preflight_report["passed"],
                    "failure_count": len(preflight_report["failures"]),
                    "warning_count": len(preflight_report["warnings"]),
                    "report_path": "run_config_preflight_report.json",
                },
            )
        )
        if not preflight_report["passed"]:
            raise ConfigError(
                "run_config_preflight_failed: "
                + "; ".join(str(item) for item in preflight_report["failures"])
            )
        pre_verl_runtime_plan = load_pre_verl_swebench_dev_runtime_plan(loaded.runnable_task)
        swebench_like_runtime_plan = load_swebench_like_runtime_plan(loaded.runnable_task)
        effective_setup_command = (
            pre_verl_runtime_plan.setup_shell
            if pre_verl_runtime_plan is not None and pre_verl_runtime_plan.setup_shell
            else loaded.runnable_task.setup_command
        )
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
        tool_policy = _tool_policy_for_runtime(
            pre_verl_enabled=pre_verl_runtime_plan is not None,
        )
        _, tool_schema_snapshot_ref, tool_protocol = write_tool_schema_snapshot(
            recorder,
            registry=allowed_tool_registry,
            tool_policy=tool_policy,
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
        model_visible_repo_context = _model_visible_repo_context_summary(
            source_snapshot_ref=source_snapshot_ref,
            repo_context_index_ref=repo_context_index_ref,
            task=loaded.runnable_task,
            source_checkout=source if pre_verl_runtime_plan is not None else None,
            run_config=config,
            recorder=recorder,
        )
        public_environment_context = build_public_environment_context(
            task=loaded.runnable_task,
            resolved_verifier_plan=resolved_plan,
            test_feedback_policy=feedback_policy.resolved_test_feedback_policy.value,
            allowed_tools=allowed_tools,
        )
        public_environment_context_ref, public_environment_prompt_ref = (
            write_public_environment_context_artifacts(
                recorder=recorder,
                context=public_environment_context,
            )
        )
        recorder.append_event(
            TrajectoryEvent(
                event_id=recorder.next_event_id("public_environment_context"),
                timestamp=_timestamp(),
                run_id=actual_run_id,
                task_id=loaded.runnable_task.task_id,
                event_type="public_environment_context_written",
                artifact_refs=[public_environment_context_ref, public_environment_prompt_ref],
                data={
                    "public_environment_context_digest": public_environment_context.context_digest,
                    "public_environment_context_ref": public_environment_context_ref.model_dump(mode="json"),
                    "public_environment_prompt_ref": public_environment_prompt_ref.model_dump(mode="json"),
                },
            )
        )
        initial_messages = ContextBuilder().build_initial_messages(
            task=loaded.runnable_task,
            workspace=run_workspace,
            run_config=config,
            resolved_verifier_plan=resolved_plan,
            allowed_tools=allowed_tools,
            scaffold=scaffold,
            workspace_facade=adapter,
            model_visible_repo_context=model_visible_repo_context,
            public_environment_context=public_environment_context,
        )
        initial_context_profile_ref = _write_initial_context_profile(
            recorder=recorder,
            run_id=actual_run_id,
            task_id=loaded.runnable_task.task_id,
            initial_messages=initial_messages,
            model_visible_repo_context=model_visible_repo_context,
            run_config=config,
        )
        recorder.append_event(
            TrajectoryEvent(
                event_id=recorder.next_event_id("initial_context"),
                timestamp=_timestamp(),
                run_id=actual_run_id,
                task_id=loaded.runnable_task.task_id,
                event_type="initial_context_profile_written",
                artifact_refs=[initial_context_profile_ref],
                data={
                    "initial_context_profile_ref": initial_context_profile_ref.model_dump(
                        mode="json"
                    )
                },
            )
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
            tool_policy=tool_policy,
            test_feedback_policy=feedback_policy.resolved_test_feedback_policy.value,
            feedback_tests_passed_policy=feedback_policy.resolved_feedback_tests_passed_policy,
            budget_manager=budget_manager,
        )
        loop_state = AgentLoop(
            model_client=model,
            tool_executor=ToolExecutor(registry=allowed_tool_registry),
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
            request_timeout_seconds=(
                config.runtime.provider_request_timeout_sec or config.runtime.task_timeout_sec
            ),
            provider_timeout_grace_sec=config.runtime.provider_timeout_grace_sec,
            min_provider_request_timeout_sec=config.runtime.min_provider_request_timeout_sec,
            provider_timeout_policy=config.runtime.provider_timeout_policy,
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
        effective_agent_stop_reason = (
            "task_timeout" if task_timeout_expired else loop_state.agent_stop_reason
        )
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
                agent_stop_reason=effective_agent_stop_reason,
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
        pre_verl_boundary = _pre_verl_boundary_payload(run_dir) if pre_verl_runtime_plan is not None else {}
        final_verifier_ran = True
        if pre_verl_runtime_plan is not None:
            final_status = str(pre_verl_boundary.get("final_verifier_status") or final_status)
            if pre_verl_boundary:
                final_verifier_ran = bool(pre_verl_boundary.get("final_verifier_ran"))
        run_outcome = derive_run_outcome(
            baseline_status=baseline.status,
            final_verifier_status=final_status,
            agent_stop_reason=effective_agent_stop_reason,
            final_verifier_ran=final_verifier_ran,
        )
        metrics = build_metrics_record(
            final_verifier=final_verifier,
            run_outcome=run_outcome,
            final_verifier_status=final_status,
            agent_stop_reason=effective_agent_stop_reason,
            timeout=bool(task_timeout_expired or final_verifier.timeout),
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
            loop_diagnostics_summary=loop_state.loop_diagnostics_summary,
            loop_diagnostic_count=len(loop_state.loop_diagnostics),
        )
        metrics.interaction_efficiency.update(
            {
                "baseline_status": baseline.status,
                "final_verifier_mode": config.evaluation.final_verifier_mode,
                "final_verifier_ran": final_verifier_ran,
                "final_verifier_boundary_failure_category": pre_verl_boundary.get("failure_category"),
                "final_verifier_boundary_failure_owner": pre_verl_boundary.get("failure_owner"),
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
            f"- agent_stop_reason: {effective_agent_stop_reason}\n"
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
                    "agent_stop_reason": effective_agent_stop_reason,
                    "baseline_status": baseline.status,
                    "final_verifier_status": final_status,
                    "final_verifier_ran": final_verifier_ran,
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
            agent_stop_reason=effective_agent_stop_reason,
            final_verifier_mode=config.evaluation.final_verifier_mode,
        )
        write_run_metadata(run_dir, run_metadata)
        _write_backend_status_if_supported(adapter, config)
        recorder.finalize_run(summary)
        adapter.cleanup_workspaces()
    return run_dir


def _pre_verl_boundary_final_verifier_status(run_dir: Path) -> str | None:
    payload = _pre_verl_boundary_payload(run_dir)
    status = payload.get("final_verifier_status")
    if status in {"accepted", "rejected", "not_executed", "timeout", "error"}:
        return str(status)
    return None


def _pre_verl_boundary_payload(run_dir: Path) -> dict[str, Any]:
    boundary_path = run_dir / "final_verifier_boundary.json"
    if not boundary_path.exists():
        return {}
    try:
        payload = json.loads(boundary_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


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
    if not stripped:
        return False
    if any(marker in stripped for marker in ("&&", "||", ";", "|", "\n", "$(", "`")):
        return True
    if stripped.startswith((". ", "source ", "export ", "cd ")):
        return True
    try:
        first = shlex.split(stripped)[0]
    except ValueError:
        return True
    if "=" not in first:
        return False
    name = first.split("=", 1)[0]
    return bool(name) and (name[0].isalpha() or name[0] == "_") and all(
        char.isalnum() or char == "_" for char in name
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


def _write_initial_context_profile(
    *,
    recorder: RunRecorder,
    run_id: str,
    task_id: str,
    initial_messages: list[dict[str, Any]],
    model_visible_repo_context: dict[str, Any] | None,
    run_config: RunConfig,
):
    payload = _initial_context_profile_payload(
        run_id=run_id,
        task_id=task_id,
        initial_messages=initial_messages,
        model_visible_repo_context=model_visible_repo_context,
        run_config=run_config,
    )
    return recorder.write_json_artifact(
        "initial_context_profile",
        payload,
        {
            "redaction_status": "not_sensitive",
            "retention_policy": "keep",
            "budget_policy": "preserve_json",
        },
    )


def _initial_context_profile_payload(
    *,
    run_id: str,
    task_id: str,
    initial_messages: list[dict[str, Any]],
    model_visible_repo_context: dict[str, Any] | None,
    run_config: RunConfig,
) -> dict[str, Any]:
    repo_context = model_visible_repo_context or {}
    first_user_content = _first_user_content(initial_messages)
    repository_context = (
        first_user_content.get("repository_context", [])
        if isinstance(first_user_content, dict)
        else []
    )
    repository_hints = (
        first_user_content.get("repository_hints")
        if isinstance(first_user_content, dict)
        else None
    )
    repository_hints_presence = (
        "present" if isinstance(repository_hints, dict) else "absent"
    )
    repository_hints_absence_reason = _repository_hints_absence_reason(
        first_user_content=first_user_content,
        repository_hints=repository_hints,
        repository_hints_mode=run_config.context_management.repository_hints.mode,
    )
    candidate_files = (
        repository_hints.get("candidate_files", [])
        if isinstance(repository_hints, dict)
        else []
    )
    repository_hints_model_visible_hash = repo_context.get(
        "repository_hints_model_visible_hash"
    )
    if repository_hints_model_visible_hash is None:
        repository_hints_model_visible_hash = stable_hash(
            {
                "field": "repository_hints",
                "state": "present" if isinstance(repository_hints, dict) else "absent",
                "value": repository_hints if isinstance(repository_hints, dict) else None,
            }
        )
    first_user_text = json.dumps(
        first_user_content,
        ensure_ascii=False,
        sort_keys=True,
    )
    public_environment = (
        first_user_content.get("public_environment")
        if isinstance(first_user_content, dict)
        else None
    )
    public_environment_digest = (
        public_environment.get("context_digest")
        if isinstance(public_environment, dict)
        else None
    )
    forbidden_fields = [
        field
        for field in (
            "repository_action_index",
            "repository_action_index_full",
            "repository_context_index",
            "source_text_span_hash",
            "workspace_root",
            "permission_mode",
            "execution_mode",
            "test_command_visibility",
            "max_context_tokens",
        )
        if field in first_user_text
    ]
    return {
        "schema_version": "repo_harness_initial_context_profile_v0",
        "run_id": run_id,
        "task_id": task_id,
        "initial_context_policy_version": (
            run_config.context_management.initial_context_policy_version
        ),
        "repository_hints_mode": run_config.context_management.repository_hints.mode,
        "repository_hints_config": (
            run_config.context_management.repository_hints.resolved_facts()
        ),
        "repository_hints_presence": repository_hints_presence,
        "repository_hints_absence_reason": repository_hints_absence_reason,
        "model_visible_message_count": len(initial_messages),
        "model_visible_messages_hash": stable_hash(initial_messages),
        "first_user_content_hash": stable_hash(first_user_content),
        "first_user_content_char_count": len(first_user_text),
        "first_user_top_level_keys": (
            sorted(first_user_content.keys()) if isinstance(first_user_content, dict) else []
        ),
        "repository_context_entry_count": (
            len(repository_context) if isinstance(repository_context, list) else 0
        ),
        "repository_context_preview_char_count": _repository_context_preview_chars(
            repository_context
        ),
        "repository_hints_candidate_count": (
            len(candidate_files) if isinstance(candidate_files, list) else 0
        ),
        "repository_hints_model_visible_hash": repository_hints_model_visible_hash,
        "repository_hints_model_visible_ref": repo_context.get(
            "repository_hints_model_visible_ref"
        ),
        "public_environment_context_digest": public_environment_digest,
        "public_environment_context_present": isinstance(public_environment, dict),
        "repository_action_index_full_hash": repo_context.get(
            "repository_action_index_full_hash"
        ),
        "repository_action_index_full_ref": repo_context.get(
            "repository_action_index_full_ref"
        ),
        "repository_context_index_full_hash": repo_context.get(
            "repository_context_index_full_hash"
        ),
        "repository_context_index_full_ref": repo_context.get(
            "repository_context_index_full_ref"
        ),
        "forbidden_model_visible_fields_present": forbidden_fields,
    }


def _repository_hints_absence_reason(
    *,
    first_user_content: Any,
    repository_hints: Any,
    repository_hints_mode: str,
) -> str | None:
    if isinstance(repository_hints, dict):
        return None
    if repository_hints_mode == "disabled":
        return "repository_hints_mode_disabled"
    task = first_user_content.get("task", {}) if isinstance(first_user_content, dict) else {}
    expected_files = task.get("expected_files", []) if isinstance(task, dict) else []
    if not isinstance(expected_files, list):
        expected_files = []
    issue_statement = str(task.get("issue_statement") or "") if isinstance(task, dict) else ""
    issue_terms = _action_index_terms(issue_statement)
    if not expected_files and not issue_terms:
        return "no_model_visible_hint_seed"
    return "unexpected_missing_repository_hints"


def _first_user_content(messages: list[dict[str, Any]]) -> Any:
    for message in messages:
        if message.get("role") == "user":
            return message.get("content")
    return None


def _repository_context_preview_chars(repository_context: Any) -> int:
    if not isinstance(repository_context, list):
        return 0
    total = 0
    for entry in repository_context:
        if isinstance(entry, dict):
            total += len(str(entry.get("preview") or ""))
    return total


def _model_visible_repo_context_summary(
    *,
    source_snapshot_ref,
    repo_context_index_ref,
    task: RunnableTask,
    source_checkout: str | Path | None = None,
    run_config: RunConfig | None = None,
    recorder: RunRecorder | None = None,
) -> dict[str, Any] | None:
    visible_task = task.agent_visible_view()
    raw_expected_files = visible_task.get("expected_files", [])
    expected_files = raw_expected_files if isinstance(raw_expected_files, list) else []
    issue_statement = str(visible_task.get("issue_statement") or "")
    issue_terms = _action_index_terms(issue_statement)
    if (
        source_snapshot_ref is None
        and repo_context_index_ref is None
        and not expected_files
        and not issue_terms
    ):
        return None
    candidate_source_entries = _repository_action_entries(
        expected_files=expected_files,
        issue_statement=issue_statement,
        issue_terms=issue_terms,
        source_checkout=Path(source_checkout) if source_checkout is not None else None,
    )
    repository_action_index = {
        "schema_version": "repo_harness_repository_action_index_v1",
        "policy_version": "repo_harness_repository_action_index_v1",
        "candidate_entries": candidate_source_entries,
        "candidate_entry_count": len(candidate_source_entries),
        "evidence_policy": (
            "Candidates are derived only from model-visible issue text, model-visible expected_files, "
            "and a shallow public source path index. Private evaluator selectors, private evaluator "
            "test identities, private reference fixes, targeted smoke hindsight, and human posterior "
            "analysis are excluded."
        ),
        "issue_terms_used": issue_terms[:40],
        "evaluator_only_material_excluded": True,
        "hindsight_sources_excluded": True,
    }
    repository_context_index_full = {
        "schema_version": "repo_harness_model_visible_repo_context_index_v0",
        "context_selection_policy_version": "repo_harness_initial_context_selection_v0",
        "expected_files": expected_files[:40],
        "candidate_source_entries": candidate_source_entries,
        "candidate_source_entry_count": len(candidate_source_entries),
        "repository_action_index": repository_action_index,
        "repository_action_index_hash": stable_hash(repository_action_index),
        "evaluator_only_material_excluded": True,
        "non_model_visible_material_excluded": True,
        "non_model_visible_material_policy": (
            "Only not_sensitive source snapshot and repository index artifact refs are exposed. "
            "Verifier-private materials and scoring artifacts are excluded."
        ),
        "usage_hint": (
            "Use repository_context, expected_files, candidate_source_entries, repository_action_index, "
            "glob_files/list_files for file discovery, symbol_search for Python definitions, "
            "grep with narrow root/glob/output_mode='files_with_matches' for content search, "
            "read_file before edit_file, update_working_state when exploration branches, and git_diff "
            "before the final answer."
        ),
    }
    if source_snapshot_ref is not None:
        repository_context_index_full["source_snapshot_ref"] = (
            _safe_model_visible_artifact_ref(source_snapshot_ref)
        )
    if repo_context_index_ref is not None:
        repository_context_index_full["repo_context_index_ref"] = (
            _safe_model_visible_artifact_ref(repo_context_index_ref)
        )
    hints_config = (
        run_config.context_management.repository_hints
        if run_config is not None
        else None
    )
    repository_hints = _repository_hints_from_action_index(
        action_entries=candidate_source_entries,
        issue_statement=issue_statement,
        config=hints_config,
    )
    action_index_ref = None
    context_index_ref = None
    hints_ref = None
    if recorder is not None:
        action_index_ref = recorder.write_json_artifact(
            "repository_action_index_full",
            repository_action_index,
            {
                "redaction_status": "not_sensitive",
                "retention_policy": "keep",
                "budget_policy": "preserve_json",
            },
        )
        context_index_ref = recorder.write_json_artifact(
            "repository_context_index_full",
            repository_context_index_full,
            {
                "redaction_status": "not_sensitive",
                "retention_policy": "keep",
                "budget_policy": "preserve_json",
            },
        )
        if repository_hints is not None:
            hints_ref = recorder.write_json_artifact(
                "repository_hints_model_visible",
                repository_hints,
                {
                    "redaction_status": "not_sensitive",
                    "retention_policy": "keep",
                    "budget_policy": "preserve_json",
                },
            )
    result: dict[str, Any] = {
        "repository_action_index_full_hash": stable_hash(repository_action_index),
        "repository_context_index_full_hash": stable_hash(repository_context_index_full),
        "repository_hints": repository_hints,
    }
    if action_index_ref is not None:
        result["repository_action_index_full_ref"] = _safe_model_visible_artifact_ref(
            action_index_ref
        )
    if context_index_ref is not None:
        result["repository_context_index_full_ref"] = _safe_model_visible_artifact_ref(
            context_index_ref
        )
    if hints_ref is not None:
        result["repository_hints_model_visible_ref"] = _safe_model_visible_artifact_ref(
            hints_ref
        )
        result["repository_hints_model_visible_hash"] = hints_ref.sha256
    return result


def _repository_hints_from_action_index(
    *,
    action_entries: list[dict[str, Any]],
    issue_statement: str,
    config,
) -> dict[str, Any] | None:
    if config is not None and config.mode == "disabled":
        return None
    max_candidate_files = (
        config.resolved_max_candidate_files if config is not None else 8
    )
    max_matched_terms = (
        config.resolved_max_matched_terms_per_file if config is not None else 6
    )
    max_fallback_terms = (
        config.resolved_max_fallback_search_terms if config is not None else 8
    )
    low_confidence_limit = (
        config.resolved_include_low_confidence_limit if config is not None else 0
    )
    mode = config.mode if config is not None else "balanced_eval"
    candidate_files: list[dict[str, Any]] = []
    low_confidence_count = 0
    for entry in action_entries:
        confidence = _repository_hint_confidence(entry)
        if confidence == "low":
            if low_confidence_count >= low_confidence_limit:
                continue
            low_confidence_count += 1
        candidate_files.append(
            {
                "path": entry["path"],
                "confidence": confidence,
                "matched_terms": _repository_hint_matched_terms(
                    entry.get("matched_terms", []),
                    max_terms=max_matched_terms,
                ),
            }
        )
        if len(candidate_files) >= max_candidate_files:
            break
    fallback_search_terms = _repository_hint_matched_terms(
        _action_index_terms(issue_statement),
        max_terms=max_fallback_terms,
    )
    return {
        "mode": mode,
        "candidate_files": candidate_files,
        "fallback_search_terms": fallback_search_terms,
        "usage_note": "These are starting points for investigation, not answers.",
    }


def _repository_hint_confidence(entry: dict[str, Any]) -> str:
    evidence_source = str(entry.get("evidence_source") or "")
    matched_terms = entry.get("matched_terms")
    ranking_signals = entry.get("ranking_signals")
    signals = ranking_signals if isinstance(ranking_signals, list) else []
    matched_count = len(matched_terms) if isinstance(matched_terms, list) else 0
    if evidence_source == "model_visible_expected_files":
        return "high"
    if "issue_rule_id_path_match" in evidence_source:
        return "high"
    if "issue_rule_id_path_match" in signals or "high_information_path_term_match" in signals:
        return "high"
    if "path_term_match" in signals:
        return "medium"
    if matched_count >= 2:
        return "medium"
    return "low"


_LOW_INFORMATION_HINT_TERMS = {
    "rule",
    "rules",
    "use",
    "instead",
    "error",
    "message",
    "file",
    "line",
    "test",
    "tests",
    "something",
    "likely",
    "might",
}


def _repository_hint_matched_terms(values: list[Any], *, max_terms: int) -> list[str]:
    if max_terms <= 0:
        return []
    terms: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        term = value.strip()
        if not term or term.lower() in _LOW_INFORMATION_HINT_TERMS:
            continue
        key = term.lower()
        if key in seen:
            continue
        seen.add(key)
        terms.append(term)
        if len(terms) >= max_terms:
            break
    return terms


def _repository_action_entries(
    *,
    expected_files: list[Any],
    issue_statement: str,
    issue_terms: list[str],
    source_checkout: Path | None,
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in expected_files:
        if not isinstance(path, str) or not path or path in seen:
            continue
        seen.add(path)
        entries.append(
            {
                "path": path,
                "evidence_source": "model_visible_expected_files",
                "matched_terms": [],
                "source_text_span_hash": stable_hash({"expected_file": path}),
                "ranking_reason": "Task expected_files is model-visible and names this path.",
                "policy_version": "repo_harness_repository_action_index_v1",
            }
        )
        if len(entries) >= 40:
            return entries
    if source_checkout is None or not source_checkout.exists():
        return entries
    issue_path_mentions = _issue_path_mentions(issue_statement)
    scored_candidates: list[dict[str, Any]] = []
    for path in _shallow_source_paths(source_checkout):
        if path in seen:
            continue
        score = _score_action_index_path(
            source_root=source_checkout,
            path=path,
            issue_statement=issue_statement,
            issue_terms=issue_terms,
            issue_path_mentions=issue_path_mentions,
        )
        if score is None:
            continue
        scored_candidates.append(score)
    scored_candidates.sort(
        key=lambda item: (
            -int(item["ranking_score"]),
            int(item["path_depth"]),
            str(item["path"]),
        )
    )
    for candidate in scored_candidates:
        path = str(candidate["path"])
        if path in seen:
            continue
        seen.add(path)
        entries.append(
            {
                "path": path,
                "evidence_source": candidate["evidence_source"],
                "matched_terms": candidate["matched_terms"][:12],
                "source_text_span_hash": stable_hash(
                    {
                        "issue_statement_sha256": stable_hash(issue_statement),
                        "matched_terms": candidate["matched_terms"][:12],
                        "path": path,
                        "public_source_signal_hash": candidate["public_source_signal_hash"],
                    }
                ),
                "ranking_reason": candidate["ranking_reason"],
                "ranking_score": candidate["ranking_score"],
                "ranking_signals": candidate["ranking_signals"],
                "policy_version": "repo_harness_repository_action_index_v1",
            }
        )
        if len(entries) >= 40:
            break
    return entries


def _action_index_terms(issue_statement: str) -> list[str]:
    raw_identifiers = re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}|[A-Za-z]\d{3,}", issue_statement)
    raw_code_tokens = re.findall(r"\b[A-Z]{2,5}\b", issue_statement)
    stop_words = {
        "about",
        "actual",
        "addition",
        "all",
        "also",
        "and",
        "any",
        "appreciated",
        "are",
        "assume",
        "behavior",
        "behaviour",
        "both",
        "but",
        "call",
        "can",
        "code",
        "current",
        "details",
        "does",
        "done",
        "etc",
        "file",
        "files",
        "for",
        "this",
        "that",
        "the",
        "then",
        "these",
        "they",
        "type",
        "with",
        "without",
        "works",
        "from",
        "when",
        "where",
        "which",
        "should",
        "would",
        "could",
        "there",
        "their",
        "expected",
        "actual",
        "error",
        "failed",
        "failure",
        "has",
        "have",
        "import",
        "test",
        "tests",
        "traceback",
        "line",
        "lines",
        "like",
        "list",
        "module",
        "new",
        "not",
        "object",
        "only",
        "output",
        "point",
        "problem",
        "produced",
        "provided",
        "python",
        "range",
        "required",
        "return",
        "sample",
        "same",
        "set",
        "some",
        "structure",
        "thank",
        "try",
        "unable",
        "update",
        "updating",
        "using",
        "value",
        "version",
        "while",
        "you",
        "user",
        "users",
        "attribute",
    }
    terms: list[str] = []
    for raw in [*raw_identifiers, *raw_code_tokens]:
        is_short_code_token = bool(re.fullmatch(r"[A-Z]{2,5}", raw))
        for term in [raw.lower(), *_split_identifier_terms(raw)]:
            if len(term) < 3 and not is_short_code_token:
                continue
            if term in stop_words or term in terms:
                continue
            terms.append(term)
            if len(terms) >= 120:
                break
        if len(terms) >= 80:
            break
    return terms


def _issue_path_mentions(issue_statement: str) -> set[str]:
    mentions = set()
    for raw in re.findall(r"[A-Za-z0-9_./\\-]+\.py", issue_statement):
        mention = raw.replace("\\", "/").strip("./").lower()
        if mention:
            mentions.add(mention)
    return mentions


def _score_action_index_path(
    *,
    source_root: Path,
    path: str,
    issue_statement: str,
    issue_terms: list[str],
    issue_path_mentions: set[str],
) -> dict[str, Any] | None:
    path_lower = path.lower()
    suffix = PurePosixPath(path).suffix.lower()
    parts = tuple(part.lower() for part in PurePosixPath(path).parts)
    if _is_action_index_excluded_path(parts=parts, suffix=suffix):
        return None
    is_test_path = any(part in {"tests", "test"} or part.startswith("test_") for part in parts)
    path_tokens = _path_signal_tokens(path)
    score = _actionable_path_base_score(parts=parts, suffix=suffix)
    matched_terms: list[str] = []
    ranking_signals: list[str] = []
    public_source_signal_hash = "not_scanned"
    if path_lower in issue_path_mentions or any(path_lower.endswith(mention) for mention in issue_path_mentions):
        score += 420
        ranking_signals.append("exact_model_visible_issue_path")
    if any(mention.endswith(path_lower) for mention in issue_path_mentions):
        score += 260
        ranking_signals.append("suffix_model_visible_issue_path")
    root_package_token = parts[0] if parts else ""
    for term in issue_terms:
        if term == root_package_token:
            continue
        term_weight = _action_index_term_weight(term)
        if term in path_lower:
            score += (90 if term in path_tokens else 55) * term_weight
            if term in path_tokens and re.fullmatch(r"[a-z]\d{3,}", term):
                score += 480
                ranking_signals.append("issue_rule_id_path_match")
            elif term in path_tokens and (len(term) >= 8 or "_" in term):
                score += 120
                ranking_signals.append("high_information_path_term_match")
            _append_unique(matched_terms, term)
            ranking_signals.append("path_term_match")
        elif _fuzzy_token_match(term, path_tokens):
            score += 45 * term_weight
            if len(term) >= 8:
                score += 90
                ranking_signals.append("high_information_path_fuzzy_match")
            _append_unique(matched_terms, term)
            ranking_signals.append("path_fuzzy_term_match")
    if not is_test_path and {"save_as", "save"} & set(issue_terms) and path_tokens & {"filewriter", "writer", "write"}:
        score += 420
        _append_unique(matched_terms, "save_as" if "save_as" in issue_terms else "save")
        ranking_signals.append("save_operation_file_writer_path_match")
    source_tokens = _public_source_signal_tokens(source_root / path, suffix=suffix)
    if source_tokens:
        public_source_signal_hash = stable_hash(sorted(source_tokens)[:200])
    for term in issue_terms:
        if term == root_package_token:
            continue
        term_weight = _action_index_term_weight(term)
        if term in source_tokens:
            score += 65 * term_weight
            if re.fullmatch(r"[a-z]\d{3,}", term) or len(term) >= 8 or "_" in term:
                score += 95
                ranking_signals.append("high_information_public_source_term_match")
            _append_unique(matched_terms, term)
            ranking_signals.append("public_source_symbol_or_text_match")
        elif _fuzzy_token_match(term, source_tokens):
            score += 30 * term_weight
            if len(term) >= 8:
                score += 60
                ranking_signals.append("high_information_public_source_fuzzy_match")
            _append_unique(matched_terms, term)
            ranking_signals.append("public_source_fuzzy_symbol_match")
    if re.search(r"\bl\d{3}\b", " ".join(issue_terms)) and "/rules/" in path_lower:
        score += 90
        ranking_signals.append("rule_id_source_directory_boost")
    if is_test_path:
        score -= 900
        ranking_signals.append("test_path_deprioritized")
    if any(part in {"docs", "doc", "examples", "example"} for part in parts):
        score -= 500
        ranking_signals.append("documentation_path_deprioritized")
    if score <= 0 or not matched_terms:
        return None
    return {
        "path": path,
        "matched_terms": matched_terms,
        "ranking_score": score,
        "path_depth": len(parts),
        "ranking_signals": sorted(set(ranking_signals)),
        "public_source_signal_hash": public_source_signal_hash,
        "evidence_source": (
            "model_visible_issue_text_and_public_source_symbol_index"
            if source_tokens
            else "model_visible_issue_text_and_public_source_path_index"
        ),
        "ranking_reason": (
            "Public source path and shallow public source symbols were ranked against "
            "model-visible issue terms."
        ),
    }


def _split_identifier_terms(identifier: str) -> list[str]:
    pieces: list[str] = []
    for chunk in re.split(r"[^A-Za-z0-9]+", identifier):
        if not chunk:
            continue
        camel_parts = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)|\d+", chunk)
        for part in camel_parts:
            lowered = part.lower()
            if len(lowered) >= 3:
                pieces.append(lowered)
        lowered_chunk = chunk.lower()
        if len(lowered_chunk) >= 3:
            pieces.append(lowered_chunk)
    return pieces


def _action_index_term_weight(term: str) -> int:
    if re.fullmatch(r"[a-z]\d{3,}", term):
        return 6
    if len(term) <= 2:
        return 4
    if "_" in term or len(term) >= 12:
        return 5
    if len(term) >= 8:
        return 4
    if len(term) >= 5:
        return 2
    return 1


def _path_signal_tokens(path: str) -> set[str]:
    tokens: set[str] = set()
    normalized = PurePosixPath(path)
    for part in normalized.parts:
        stem = PurePosixPath(part).stem
        for value in [part, stem, *_split_identifier_terms(stem), *_split_identifier_terms(part)]:
            lowered = value.lower()
            if len(lowered) >= 3:
                tokens.add(lowered)
            if lowered.endswith("writer"):
                tokens.add("writer")
                tokens.add("write")
            if lowered.startswith("write"):
                tokens.add("write")
    return tokens


def _public_source_signal_tokens(path: Path, *, suffix: str) -> set[str]:
    if suffix not in {".py", ".pyi", ".js", ".jsx", ".ts", ".tsx", ".rs", ".go", ".java"}:
        return set()
    try:
        text = path.read_text(encoding="utf-8", errors="replace")[:32000]
    except OSError:
        return set()
    tokens: set[str] = set()
    for match in re.finditer(
        r"\b(?:class|def|async\s+def)\s+([A-Za-z_][A-Za-z0-9_]*)|"
        r"\bfrom\s+([A-Za-z_][A-Za-z0-9_\.]*)\s+import\s+([A-Za-z_][A-Za-z0-9_,\s]*)|"
        r"\bimport\s+([A-Za-z_][A-Za-z0-9_\.]*)|"
        r"\b([A-Za-z_][A-Za-z0-9_]{2,})\b",
        text,
    ):
        for group in match.groups():
            if not group:
                continue
            for raw in re.split(r"[\s,\.]+", group):
                if not raw:
                    continue
                lowered = raw.lower()
                if len(lowered) >= 3:
                    tokens.add(lowered)
                tokens.update(_split_identifier_terms(raw))
        if len(tokens) >= 400:
            break
    for code_token in re.findall(r"\b[A-Z]{2,5}\b", text):
        tokens.add(code_token.lower())
        if len(tokens) >= 450:
            break
    return tokens


def _fuzzy_token_match(term: str, tokens: set[str]) -> bool:
    if len(term) < 5:
        return False
    for token in tokens:
        if len(token) < 5:
            continue
        if term.startswith(token) or token.startswith(term):
            return True
        if _without_vowels(term).startswith(_without_vowels(token)) or _without_vowels(token).startswith(_without_vowels(term)):
            return True
    return False


def _without_vowels(value: str) -> str:
    return re.sub(r"[aeiou]", "", value)


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def _is_action_index_excluded_path(*, parts: tuple[str, ...], suffix: str) -> bool:
    if suffix and suffix not in {
        ".py",
        ".pyi",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".rs",
        ".go",
        ".java",
        ".toml",
        ".yaml",
        ".yml",
        ".json",
    }:
        return True
    excluded_parts = {
        ".git",
        ".github",
        ".circleci",
        ".tox",
        ".venv",
        ".pre_verl_venv",
        "__pycache__",
        "node_modules",
        "build",
        "dist",
        "htmlcov",
        "assets",
        "img",
        "images",
        "static",
    }
    return any(part in excluded_parts for part in parts)


def _actionable_path_base_score(*, parts: tuple[str, ...], suffix: str) -> int:
    score = 0
    if suffix in {".py", ".pyi"}:
        score += 130
    elif suffix in {".js", ".jsx", ".ts", ".tsx", ".rs", ".go", ".java"}:
        score += 100
    elif suffix in {".toml", ".yaml", ".yml", ".json"}:
        score += 35
    if any(part in {"src", "lib"} for part in parts):
        score += 70
    if parts and parts[0] not in {"docs", "doc", "tests", "test", "examples", "example"}:
        score += 45
    return score


def _shallow_source_paths(source_root: Path) -> list[str]:
    excluded_parts = {
        ".git",
        ".hg",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        ".pre_verl_venv",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
    }
    paths: list[str] = []
    for path in sorted(source_root.rglob("*")):
        rel = path.relative_to(source_root)
        if any(part in excluded_parts for part in rel.parts):
            continue
        if path.is_file() and not path.is_symlink():
            paths.append(rel.as_posix())
        if len(paths) >= 2000:
            break
    return paths


def _safe_model_visible_artifact_ref(ref) -> dict[str, Any]:
    return {
        "kind": ref.kind,
        "relative_path": ref.relative_path,
        "sha256": ref.sha256,
        "redaction_status": ref.redaction_status,
    }


def _tool_policy_for_runtime(*, pre_verl_enabled: bool) -> ToolPolicy:
    if pre_verl_enabled:
        return ToolPolicy(
            tool_policy_version="repo_harness_tool_policy_pre_verl_read_before_edit_v1",
            require_read_before_edit=True,
        )
    return ToolPolicy()


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
