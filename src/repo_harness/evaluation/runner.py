"""Eval Runner：单任务和批量评测编排。"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

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
from repo_harness.model_client import ReplayModelClient
from repo_harness.permissions import PermissionContext
from repo_harness.reward import compute_reward_metadata
from repo_harness.tasks import RunnableTask, load_task
from repo_harness.tools import DEFAULT_TOOL_ORDER, ToolExecutionContext, ToolExecutor, ToolOutputLimits
from repo_harness.trajectory import MetricsRecord, RunRecorder, TrajectoryEvent
from repo_harness.verifier import PytestVerifier, build_error_verifier_result
from repo_harness.workspace import ExecutionResult, LocalWorkspaceAdapter


def run_task(
    task_path: str | Path,
    *,
    config_path: str | Path,
    output_dir: str | Path | None = None,
    run_id: str | None = None,
) -> Path:
    run_started = time.monotonic()
    config = load_run_config(config_path, output_dir=output_dir)
    task_deadline_monotonic = run_started + config.runtime.task_timeout_sec
    if config.model.provider != "replay":
        raise ConfigError("RepoHarness 第一版 run-task 只支持 model.provider=replay。")
    if config.runtime.execution_mode != "local_process":
        raise ConfigError("RepoHarness 第一版只支持 runtime.execution_mode=local_process。")
    if config.evaluation.final_verifier_mode != "strict_patch_replay":
        raise ConfigError("RepoHarness 第一版正式评测只支持 final_verifier_mode=strict_patch_replay。")
    loaded = load_task(task_path)
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
        adapter = LocalWorkspaceAdapter(
            run_id=actual_run_id,
            run_dir=run_dir,
            default_command_timeout_sec=config.workspace.default_command_timeout_sec,
            keep_workspace=config.workspace.keep_workspace,
        )
        verifier = PytestVerifier(adapter)
        source = adapter.create_source_checkout(loaded.runnable_task)
        setup = adapter.create_setup_workspace(source)
        setup_result = _run_setup_command(
            adapter=adapter,
            setup_workspace=setup,
            task=loaded.runnable_task,
            recorder=recorder,
        )
        dependency_strategy = (
            "rerun_setup"
            if loaded.runnable_task.setup_command and _setup_succeeded(setup_result)
            else "none"
        )
        dependency_state = adapter.capture_dependency_state(strategy=dependency_strategy)
        _write_json(run_dir / "dependency_state.json", dependency_state.model_dump(mode="json"))
        if setup_result is not None and not _setup_succeeded(setup_result):
            baseline_verifiers = [
                build_error_verifier_result(
                    command=loaded.runnable_task.setup_command or "setup",
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
        baseline_ref = recorder.write_json_artifact(
            "baseline_verifier_results",
            {
                "results": [
                    result.model_dump(mode="json")
                    for result in baseline_verifiers
                ]
            },
        )
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
        if not baseline.can_enter_agent_run:
            _finalize_quality_gate_run(
                run_id=actual_run_id,
                task_id=loaded.runnable_task.task_id,
                baseline=baseline,
                run_dir=run_dir,
                recorder=recorder,
            )
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
            setup_command=loaded.runnable_task.setup_command,
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
            ),
            verifier_feedback_facade=verifier,
            resolved_verifier_plan=resolved_plan,
            output_limits=ToolOutputLimits(
                max_tool_output_chars=config.workspace.max_tool_output_chars,
            ),
            budget_manager=budget_manager,
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
            budget_manager=budget_manager,
            task_deadline_monotonic=task_deadline_monotonic,
        )
        capture = adapter.capture_final_patch(run_workspace, recorder=recorder)
        if _task_timeout_expired(task_deadline_monotonic):
            _append_task_timeout_event(
                run_id=actual_run_id,
                task_id=loaded.runnable_task.task_id,
                recorder=recorder,
                phase="before_final_verifier",
            )
            final_verifier = build_error_verifier_result(
                command="strict_patch_replay",
                error_type="task_timeout",
                verifier_stage="final",
                timeout=True,
            )
        else:
            try:
                verification = adapter.create_verification_workspace(
                    source_checkout=source,
                    dependency_state=dependency_state,
                    final_patch_path=capture.patch_path,
                    setup_command=loaded.runnable_task.setup_command,
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
        recorder.write_json_artifact("reward_metadata", reward.model_dump(mode="json"))
        final_status = derive_final_verifier_status(final_verifier)
        run_outcome = derive_run_outcome(
            baseline_status=baseline.status,
            final_verifier_status=final_status,
            agent_stop_reason=loop_state.agent_stop_reason,
            final_verifier_ran=True,
        )
        metrics = build_metrics_record(
            final_verifier=final_verifier,
            run_outcome=run_outcome,
            agent_stop_reason=loop_state.agent_stop_reason,
            turn_count=loop_state.turn_count,
            tool_call_count=loop_state.tool_call_count,
            test_run_count=_count_test_runs(loop_state.messages),
            patch_stats=capture.patch_stats,
            permission_denial_count=loop_state.permission_denial_count,
            invalid_tool_call_count=loop_state.invalid_tool_call_count,
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
        recorder.finalize_run(summary)
        adapter.cleanup_workspaces()
    return run_dir


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


def _run_setup_command(
    *,
    adapter: LocalWorkspaceAdapter,
    setup_workspace: Path,
    task: RunnableTask,
    recorder: RunRecorder,
) -> ExecutionResult | None:
    if not task.setup_command:
        return None
    result = adapter.run_command(
        setup_workspace,
        task.setup_command,
        timeout_sec=task.timeouts.setup_timeout_sec,
        recorder=recorder,
        command_semantics="setup",
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
    if getattr(result, "parser_confidence", 0.0) < 0.5:
        return "low_parser_confidence"
    error_type = getattr(result, "error_type", None)
    if error_type in {"dependency_error", "low_parser_confidence"}:
        return str(error_type)
    if error_type == "test_command_error" and generated_file_count == 0:
        return "test_command_error"
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
    return sum(1 for message in messages if "run_tests" in str(message))


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
