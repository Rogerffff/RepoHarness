"""阶段七最小 run-task 编排器。"""

from __future__ import annotations

import json
from pathlib import Path

from repo_harness.agent_loop import AgentLoop
from repo_harness.budget import BudgetManager
from repo_harness.config import RunConfig, load_run_config
from repo_harness.context import ContextBuilder
from repo_harness.errors import ConfigError, WorkspaceError
from repo_harness.evaluation.metrics import (
    build_metrics_record,
    derive_final_verifier_status,
    derive_run_outcome,
)
from repo_harness.evaluation.schemas import BaselineResult, ResolvedVerifierPlan
from repo_harness.model_client import ReplayModelClient
from repo_harness.permissions import PermissionContext
from repo_harness.reward import compute_reward_metadata
from repo_harness.tasks import load_task
from repo_harness.tools import DEFAULT_TOOL_ORDER, ToolExecutionContext, ToolExecutor, ToolOutputLimits
from repo_harness.trajectory import MetricsRecord, RunRecorder, TrajectoryEvent
from repo_harness.verifier import PytestVerifier, build_error_verifier_result
from repo_harness.workspace import LocalWorkspaceAdapter


def run_task(
    task_path: str | Path,
    *,
    config_path: str | Path,
    output_dir: str | Path | None = None,
    run_id: str | None = None,
) -> Path:
    config = load_run_config(config_path, output_dir=output_dir)
    if config.model.provider != "replay":
        raise ConfigError("阶段七 run-task 只支持 model.provider=replay。")
    loaded = load_task(task_path)
    actual_run_id = run_id or f"{config.run_id_prefix}_{loaded.runnable_task.task_id}"
    run_dir = Path(config.workspace.output_dir) / actual_run_id
    if run_dir.exists():
        raise ConfigError(f"run directory 已存在，请使用新的 run id 或先手动归档：{run_dir}")
    with RunRecorder(actual_run_id, run_dir, task_id=loaded.runnable_task.task_id) as recorder:
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
        adapter = LocalWorkspaceAdapter(
            run_id=actual_run_id,
            run_dir=run_dir,
            default_command_timeout_sec=config.workspace.default_command_timeout_sec,
            keep_workspace=config.workspace.keep_workspace,
        )
        verifier = PytestVerifier(adapter)
        source = adapter.create_source_checkout(loaded.runnable_task)
        setup = adapter.create_setup_workspace(source)
        dependency_state = adapter.capture_dependency_state(strategy="none")
        _write_json(run_dir / "dependency_state.json", dependency_state.model_dump(mode="json"))
        baseline_verifier = verifier.run_baseline(setup, loaded.verifier_config, recorder)
        baseline_ref = recorder.write_json_artifact(
            "baseline_verifier_result", baseline_verifier.model_dump(mode="json")
        )
        baseline = BaselineResult(
            task_id=loaded.runnable_task.task_id,
            status="valid" if baseline_verifier.parser_confidence >= 0.5 else "invalid",
            setup_exit_code=0,
            baseline_exit_code=baseline_verifier.exit_code,
            baseline_verifier_result_ref=baseline_ref,
            parser_confidence=baseline_verifier.parser_confidence,
            baseline_rerun_count=1,
            initial_fail_to_pass_tests=loaded.verifier_config.fail_to_pass_tests,
            initial_pass_to_pass_tests=loaded.verifier_config.pass_to_pass_tests,
            dependency_state=dependency_state,
            agent_run_start_policy={
                "create_from": "source_checkout",
                "restore_dependency_state": False,
                "diff_base_policy": "create_agent_start_snapshot_after_dependency_restore",
            },
        )
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
        if not baseline.can_enter_agent_run:
            metrics = MetricsRecord(
                run_outcome="invalid_task",
                final_verifier_status="skipped",
                interaction_efficiency={"baseline_status": baseline.status},
            )
            _write_json(run_dir / "metrics.json", metrics.model_dump(mode="json"))
            summary = (
                f"# RepoHarness Run Summary\n\n"
                f"- run_id: {actual_run_id}\n"
                f"- task_id: {loaded.runnable_task.task_id}\n"
                f"- agent_stop_reason: skipped_invalid_baseline\n"
                f"- final_verifier_status: skipped\n"
                f"- run_outcome: invalid_task\n"
            )
            recorder.append_event(
                TrajectoryEvent(
                    event_id=recorder.next_event_id("run"),
                    timestamp=_timestamp(),
                    run_id=actual_run_id,
                    task_id=loaded.runnable_task.task_id,
                    event_type="run_finished",
                    data={
                        "agent_stop_reason": "skipped_invalid_baseline",
                        "final_verifier_status": "skipped",
                        "run_outcome": "invalid_task",
                    },
                )
            )
            recorder.finalize_run(summary)
            return run_dir
        resolved_plan = ResolvedVerifierPlan(
            verifier_config=loaded.verifier_config,
            initial_fail_to_pass_tests=baseline.initial_fail_to_pass_tests,
            initial_pass_to_pass_tests=baseline.initial_pass_to_pass_tests,
            flaky_tests=[],
            parser_confidence=baseline.parser_confidence,
            resolved_verifier_plan_id=f"{actual_run_id}_verifier_plan",
        )
        run_workspace = adapter.create_agent_workspace(
            task=loaded.runnable_task,
            source_checkout=source,
            dependency_state=dependency_state,
            recorder=recorder,
        )
        initial_messages = ContextBuilder().build_initial_messages(
            task=loaded.runnable_task,
            workspace=run_workspace,
            run_config=config,
            resolved_verifier_plan=resolved_plan,
            allowed_tools=DEFAULT_TOOL_ORDER,
        )
        replay_path = config.model.replay_script_path
        if replay_path is None:
            raise ConfigError("阶段七 run-task 需要 model.replay_script_path。")
        model = ReplayModelClient.from_path(replay_path)
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
            ),
            verifier_feedback_facade=verifier,
            resolved_verifier_plan=resolved_plan,
            output_limits=ToolOutputLimits(
                max_tool_output_chars=config.workspace.max_tool_output_chars,
            ),
        )
        loop_state = AgentLoop(
            model_client=model,
            tool_executor=ToolExecutor(),
        ).run(
            run_id=actual_run_id,
            task_id=loaded.runnable_task.task_id,
            initial_messages=initial_messages,
            tool_context=tool_context,
            recorder=recorder,
            max_turns=config.runtime.max_turns,
            context_config=config.context_management,
            budget_manager=BudgetManager.from_run_config(config),
        )
        capture = adapter.capture_final_patch(run_workspace, recorder=recorder)
        try:
            verification = adapter.create_verification_workspace(
                source_checkout=source,
                dependency_state=dependency_state,
                final_patch_path=capture.patch_path,
                recorder=recorder,
            )
            final_verifier = verifier.run_final(verification, resolved_plan, recorder)
        except WorkspaceError:
            final_verifier = build_error_verifier_result(
                command="git apply final.patch",
                error_type="patch_apply_failed",
                verifier_stage="final",
            )
        final_verifier_ref = recorder.write_json_artifact(
            "final_verifier_result", final_verifier.model_dump(mode="json")
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
        reward = compute_reward_metadata(
            final_verifier,
            patch_stats={"added_lines": capture.added_lines, "removed_lines": capture.removed_lines},
            event_counts={
                "turn_count": loop_state.turn_count,
                "tool_call_count": loop_state.tool_call_count,
                "test_run_count": _count_test_runs(loop_state.messages),
            },
        )
        final_status = derive_final_verifier_status(final_verifier)
        run_outcome = derive_run_outcome(final_status)
        metrics = build_metrics_record(
            final_verifier=final_verifier,
            run_outcome=run_outcome,
            agent_stop_reason=loop_state.agent_stop_reason,
            turn_count=loop_state.turn_count,
            tool_call_count=loop_state.tool_call_count,
            test_run_count=_count_test_runs(loop_state.messages),
            patch_stats={"added_lines": capture.added_lines, "removed_lines": capture.removed_lines},
            permission_denial_count=loop_state.permission_denial_count,
            invalid_tool_call_count=loop_state.invalid_tool_call_count,
        )
        _write_json(run_dir / "verifier.json", final_verifier.model_dump(mode="json"))
        _write_json(run_dir / "reward.json", reward.model_dump(mode="json"))
        _write_json(run_dir / "metrics.json", metrics.model_dump(mode="json"))
        summary = (
            f"# RepoHarness Run Summary\n\n"
            f"- run_id: {actual_run_id}\n"
            f"- task_id: {loaded.runnable_task.task_id}\n"
            f"- agent_stop_reason: {loop_state.agent_stop_reason}\n"
            f"- final_verifier_status: {final_status}\n"
            f"- run_outcome: {run_outcome}\n"
            f"- permission_denial_count: {loop_state.permission_denial_count}\n"
            f"{_permission_denial_summary(loop_state.permission_denial_reasons)}"
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
                    "final_verifier_status": final_status,
                    "run_outcome": run_outcome,
                },
            )
        )
        recorder.finalize_run(summary)
    return run_dir


def _write_json(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _timestamp() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _count_test_runs(messages: list[dict[str, object]]) -> int:
    return sum(1 for message in messages if "run_tests" in str(message))


def _permission_denial_summary(reasons: list[str]) -> str:
    if not reasons:
        return ""
    unique_reasons = list(dict.fromkeys(reasons))
    lines = ["- permission_denial_reasons:"]
    lines.extend(f"  - {reason}" for reason in unique_reasons[:5])
    return "\n".join(lines) + "\n"
