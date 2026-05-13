"""阶段七最小 Agent Loop。"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable

from repo_harness.agent_loop.schemas import AgentLoopState
from repo_harness.budget import BudgetManager, BudgetState
from repo_harness.config import ContextManagementConfig
from repo_harness.context.auto_compact import AutoCompactRunner
from repo_harness.context import (
    ContextManager,
    ModelInputSnapshot,
    ToolResultArtifactIndex,
    build_persisted_tool_result_preview,
    build_provider_request_projection,
    estimate_provider_request_projection,
    persist_tool_result_content,
    resolve_context_budget,
)
from repo_harness.model_client import (
    ModelCallEvent,
    ModelClient,
    ModelProviderOptions,
    ModelRequestContext,
    ModelResponse,
)
from repo_harness.model_client.provider_private_state import (
    provider_private_state_store,
    sanitize_provider_private_metadata_for_messages,
)
from repo_harness.run_metadata import RunConfigFactsRef
from repo_harness.schema_base import stable_hash
from repo_harness.scaffolds.patch_action import PatchActionParseResult, parse_patch_action
from repo_harness.scaffolds import ScaffoldDefinition, build_scaffold
from repo_harness.tools import ToolCall
from repo_harness.tools import ToolDefinition, ToolExecutionContext, ToolExecutor, ToolResult
from repo_harness.trajectory import ArtifactRef, RunRecorder, TranscriptRecord, TrajectoryEvent


NO_PROGRESS_DIAGNOSTIC_POLICY_VERSION = "repo_harness_loop_no_progress_diagnostic_v0"
NO_PROGRESS_READ_ONLY_TOOL_NAMES = frozenset({"list_files", "glob_files", "read_file", "read_tool_result_artifact", "grep", "symbol_search", "git_diff"})
NO_PROGRESS_PATCH_TOOL_NAMES = frozenset({"edit_file", "create_file"})
NO_PROGRESS_READ_ONLY_STREAK_THRESHOLD = 10
NO_PROGRESS_REPEATED_INPUT_THRESHOLD = 3
NO_PROGRESS_EMPTY_SEARCH_THRESHOLD = 4
CONVERGENCE_NUDGE_POLICY_VERSION = "repo_harness_convergence_nudge_v3"
CONVERGENCE_NUDGE_MAX_PER_RUN = 3
CONVERGENCE_NUDGE_MIN_TURN_GAP = 4
NEAR_BUDGET_WITH_PATCH_TURN_THRESHOLD = 4
CONTEXT_WARNING_POLICY_VERSION = "repo_harness_context_warning_v1"
PROVIDER_TIMEOUT_POLICY_VERSION = "task_deadline_clamped_provider_request_v0"
MODEL_INPUT_NOT_ACCEPTED_ERROR_TYPES = frozenset(
    {
        "context_limit",
        "prompt_too_long",
        "prompt too long",
        "request_too_large",
        "payload_too_large",
    }
)
MODEL_INPUT_ACCEPTED_ERROR_TYPES = frozenset(
    {
        "output_token_limit_reached",
        "tool_call_parse_failure",
    }
)


def _cleanup_provider_private_state_on_exit(func: Callable[..., AgentLoopState]) -> Callable[..., AgentLoopState]:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> AgentLoopState:
        run_id = kwargs.get("run_id")
        try:
            return func(*args, **kwargs)
        finally:
            if isinstance(run_id, str):
                provider_private_state_store().clear_run(run_id)

    return wrapper


def _model_input_was_accepted(response: ModelResponse) -> bool:
    if response.model_error_type is None:
        return True
    if response.model_error_type in MODEL_INPUT_NOT_ACCEPTED_ERROR_TYPES:
        return False
    return response.model_error_type in MODEL_INPUT_ACCEPTED_ERROR_TYPES


def _provider_context_limit_rejected_input(
    response: ModelResponse,
    terminal_error_type: str | None,
) -> bool:
    return (
        terminal_error_type in MODEL_INPUT_NOT_ACCEPTED_ERROR_TYPES
        or response.model_error_type in MODEL_INPUT_NOT_ACCEPTED_ERROR_TYPES
    )


class AgentLoop:
    def __init__(
        self,
        *,
        model_client: ModelClient,
        tool_executor: ToolExecutor,
        scaffold: ScaffoldDefinition | None = None,
        allowed_tool_names: list[str] | None = None,
        test_feedback_policy: str = "oracle_hidden_feedback",
        feedback_tests_passed_policy: str = "stop_immediately",
        hidden_feedback_visible_to_model: bool = True,
    ) -> None:
        self.model_client = model_client
        self.tool_executor = tool_executor
        self.context_manager = ContextManager()
        self.auto_compact_runner = AutoCompactRunner()
        self.scaffold = scaffold or build_scaffold("simple_react")
        self.allowed_tool_names = allowed_tool_names or list(self.scaffold.allowed_tools)
        self.test_feedback_policy = test_feedback_policy
        self.feedback_tests_passed_policy = feedback_tests_passed_policy
        self.hidden_feedback_visible_to_model = hidden_feedback_visible_to_model

    @_cleanup_provider_private_state_on_exit
    def run(
        self,
        *,
        run_id: str,
        task_id: str,
        initial_messages: list[dict[str, object]],
        tool_context: ToolExecutionContext,
        recorder: RunRecorder,
        max_turns: int,
        context_config: ContextManagementConfig | None = None,
        budget_manager: BudgetManager | None = None,
        task_deadline_monotonic: float | None = None,
        run_config_facts_ref: RunConfigFactsRef | None = None,
        tool_schema_snapshot_ref: ArtifactRef | None = None,
        provider_options: ModelProviderOptions | None = None,
        generation_config: dict[str, object] | None = None,
        provider_model_settings: dict[str, object] | None = None,
        request_timeout_seconds: float = 60.0,
        provider_timeout_grace_sec: float = 2.0,
        min_provider_request_timeout_sec: float = 5.0,
        provider_timeout_policy: str = PROVIDER_TIMEOUT_POLICY_VERSION,
        raw_request_logging_policy: str = "redact_secrets",
        retry_policy: str = "none",
    ) -> AgentLoopState:
        context_config_resolved = context_config or ContextManagementConfig()
        budget_manager_was_provided = budget_manager is not None
        budget_manager = budget_manager or _default_budget_manager(max_turns)
        if (
            tool_context is not None
            and tool_context.tool_result_artifact_index is None
        ):
            tool_context.tool_result_artifact_index = ToolResultArtifactIndex(
                run_dir=recorder.run_dir
            )
        loop_started = time.monotonic()
        messages = list(initial_messages)
        state = AgentLoopState(
            run_id=run_id,
            task_id=task_id,
            messages=messages,
            budget_state=BudgetState(started_at=_timestamp()),
            current_phase=self.scaffold.initial_phase,
            test_feedback_policy=self.test_feedback_policy,
            feedback_tests_passed_policy=self.feedback_tests_passed_policy,
            hidden_feedback_visible_to_model=self.hidden_feedback_visible_to_model,
        )
        for index, message in enumerate(initial_messages):
            recorder.append_transcript(
                TranscriptRecord(
                    record_id=recorder.next_record_id(),
                    run_id=run_id,
                    task_id=task_id,
                    message_id=f"initial_{index}",
                    turn=0,
                    role=message["role"],  # type: ignore[arg-type]
                    content_preview=str(message.get("content", ""))[:4000],
                    model_visible=True,
                    trainable=False,
                    created_at=_timestamp(),
                )
        )

        malformed_tool_call_repair_count = 0
        provider_options_resolved = provider_options or ModelProviderOptions(
            provider="replay",
            model_id="replay-script-v0",
        )
        context_budget_facts = resolve_context_budget(
            config=context_config_resolved,
            provider=provider_options_resolved.provider,
            model_id=provider_options_resolved.model_id,
        )
        runtime_context_budget_tokens = (
            min(context_budget_facts.effective_context_budget_tokens, budget_manager.max_context_tokens)
            if budget_manager_was_provided
            else context_budget_facts.effective_context_budget_tokens
        )
        runtime_hard_context_limit_tokens = (
            min(
                context_budget_facts.hard_context_limit_tokens,
                max(1, int(runtime_context_budget_tokens * context_config_resolved.hard_context_limit_ratio)),
            )
            if budget_manager_was_provided
            else context_budget_facts.hard_context_limit_tokens
        )
        context_budget_payload = {
            **context_budget_facts.model_dump(mode="json"),
            "runtime_context_budget_tokens": runtime_context_budget_tokens,
            "runtime_hard_context_limit_tokens": runtime_hard_context_limit_tokens,
            "budget_manager_was_explicit": budget_manager_was_provided,
        }
        emitted_context_warning_levels: set[str] = set()
        emitted_no_progress_signal_keys: set[str] = set()
        emitted_convergence_nudge_scopes: set[str] = set()
        convergence_nudge_count = 0
        last_convergence_nudge_turn_by_level: dict[str, int] = {}
        max_loop_iterations = (
            budget_manager.max_turns
            + context_config_resolved.reactive_compact_retry_limit
        )
        for turn in range(1, max_loop_iterations + 1):
            if turn > budget_manager.max_turns + state.reactive_compact_retry_count:
                state.agent_stop_reason = "max_turns"
                state.budget_state.stop_reason = "max_turns"
                break
            state.turn_count = min(turn, budget_manager.max_turns)
            state.budget_state.turn_count = state.turn_count
            budget_stop = _budget_stop_reason(
                budget_manager,
                state,
                loop_started,
                task_deadline_monotonic=task_deadline_monotonic,
            )
            if budget_stop is not None:
                _record_budget_exhausted(
                    run_id=run_id,
                    task_id=task_id,
                    turn=turn,
                    reason=budget_stop,
                    state=state,
                    recorder=recorder,
                )
                break
            current_phase = state.current_phase or self.scaffold.initial_phase
            phase_allowed_tool_names = _allowed_tools_for_phase(
                scaffold=self.scaffold,
                phase=current_phase,
                resolved_allowed_tool_names=self.allowed_tool_names,
                test_feedback_policy=self.test_feedback_policy,
            )
            phase_allowed_tool_definitions = _tool_definitions_for_allowed_tools(
                self.tool_executor,
                phase_allowed_tool_names,
            )
            phase_start_test_run_count = state.budget_state.test_run_count
            context_messages = _messages_with_phase_metadata(
                messages=messages,
                scaffold=self.scaffold,
                phase=current_phase,
                allowed_tool_names=phase_allowed_tool_names,
            )
            prepared = self.context_manager.prepare_messages(
                messages=context_messages,
                recorder=recorder,
                task_id=task_id,
                turn=turn,
                context_config=context_config_resolved,
                provider_name=provider_options_resolved.provider,
                tool_result_artifact_index=tool_context.tool_result_artifact_index
                if tool_context
                else None,
                context_budget_facts=context_budget_payload,
            )
            state.context_revision = prepared.context_revision
            recorder.append_event(prepared.context_event)
            pairing_validation = prepared.context_event.data.get("tool_pairing_validation", {})
            if not pairing_validation.get("ok", True):
                state.agent_stop_reason = "context_integrity_error"
                state.budget_state.stop_reason = "context_integrity_error"
                state.last_model_error = "context_integrity_error"
                recorder.append_event(
                    TrajectoryEvent(
                        event_id=recorder.next_event_id("context_integrity"),
                        timestamp=_timestamp(),
                        run_id=run_id,
                        task_id=task_id,
                        turn=turn,
                        event_type="context_integrity_error",
                        severity="error",
                        error_type="tool_call_result_pairing_failed",
                        artifact_refs=[prepared.prepared_messages_ref],
                        data={
                            "context_revision": prepared.context_revision,
                            "model_input_hash": prepared.model_input_hash,
                            "tool_pairing_validation": pairing_validation,
                            "formal_policy": "stop_before_provider_request",
                            "tainted": False,
                        },
                    )
                )
                break
            projection_estimate = _build_provider_request_projection_estimate(
                prepared_messages=prepared.messages,
                provider_options=provider_options_resolved,
                allowed_tool_definitions=phase_allowed_tool_definitions,
                generation_config=generation_config or {},
                provider_model_settings=provider_model_settings or {},
                provider_message_format=f"repo_harness_{provider_options_resolved.provider}_messages_v0",
                context_budget_facts=context_budget_facts,
            )
            warning_level = _context_warning_level(
                token_estimate=projection_estimate.provider_request_token_estimate,
                max_context_tokens=runtime_context_budget_tokens,
                emitted_levels=emitted_context_warning_levels,
            )
            if warning_level is not None:
                _record_context_warning(
                    run_id=run_id,
                    task_id=task_id,
                    turn=turn,
                    state=state,
                    recorder=recorder,
                    messages=messages,
                    prepared=prepared,
                    provider_request_projection_estimate=projection_estimate.model_dump(mode="json"),
                    warning_level=warning_level,
                    max_context_tokens=runtime_context_budget_tokens,
                )
                emitted_context_warning_levels.add(warning_level)
                context_messages = _messages_with_phase_metadata(
                    messages=messages,
                    scaffold=self.scaffold,
                    phase=current_phase,
                    allowed_tool_names=phase_allowed_tool_names,
                )
                prepared = self.context_manager.prepare_messages(
                    messages=context_messages,
                    recorder=recorder,
                    task_id=task_id,
                    turn=turn,
                    context_config=context_config_resolved,
                    provider_name=provider_options_resolved.provider,
                    tool_result_artifact_index=tool_context.tool_result_artifact_index
                    if tool_context
                    else None,
                    context_budget_facts=context_budget_payload,
                )
                state.context_revision = prepared.context_revision
                recorder.append_event(prepared.context_event)
                pairing_validation = prepared.context_event.data.get("tool_pairing_validation", {})
                if not pairing_validation.get("ok", True):
                    state.agent_stop_reason = "context_integrity_error"
                    state.budget_state.stop_reason = "context_integrity_error"
                    state.last_model_error = "context_integrity_error"
                    recorder.append_event(
                        TrajectoryEvent(
                            event_id=recorder.next_event_id("context_integrity"),
                            timestamp=_timestamp(),
                            run_id=run_id,
                            task_id=task_id,
                            turn=turn,
                            event_type="context_integrity_error",
                            severity="error",
                            error_type="tool_call_result_pairing_failed",
                            artifact_refs=[prepared.prepared_messages_ref],
                            data={
                                "context_revision": prepared.context_revision,
                                "model_input_hash": prepared.model_input_hash,
                                "tool_pairing_validation": pairing_validation,
                                "formal_policy": "stop_before_provider_request",
                                "tainted": False,
                                "after_context_warning_reprepare": True,
                            },
                        )
                    )
                    break
                projection_estimate = _build_provider_request_projection_estimate(
                    prepared_messages=prepared.messages,
                    provider_options=provider_options_resolved,
                    allowed_tool_definitions=phase_allowed_tool_definitions,
                    generation_config=generation_config or {},
                    provider_model_settings=provider_model_settings or {},
                    provider_message_format=f"repo_harness_{provider_options_resolved.provider}_messages_v0",
                    context_budget_facts=context_budget_facts,
                )
            auto_compact_applied_this_turn = False
            auto_compact_trigger_tokens = max(
                1,
                int(
                    runtime_context_budget_tokens
                    * context_config_resolved.auto_compact_trigger_ratio
                ),
            )
            if (
                context_config_resolved.auto_compact_enabled
                and context_config_resolved.auto_compact_max_consecutive_failures > 0
                and state.auto_compact_consecutive_failures
                < context_config_resolved.auto_compact_max_consecutive_failures
                and projection_estimate.provider_request_token_estimate
                >= auto_compact_trigger_tokens
            ):
                recorder.append_event(
                    TrajectoryEvent(
                        event_id=recorder.next_event_id("auto_compact"),
                        timestamp=_timestamp(),
                        run_id=run_id,
                        task_id=task_id,
                        turn=turn,
                        event_type="auto_compact_triggered",
                        severity="warning",
                        artifact_refs=[prepared.prepared_messages_ref],
                        data={
                            "schema_version": "repo_harness_auto_compact_triggered_v1",
                            "trigger_reason": "projection_above_auto_compact_trigger",
                            "context_revision": prepared.context_revision,
                            "prepared_messages_ref": prepared.prepared_messages_ref.model_dump(
                                mode="json"
                            ),
                            "model_input_hash": prepared.model_input_hash,
                            "provider_request_projection_hash": (
                                projection_estimate.provider_request_projection_hash
                            ),
                            "provider_request_token_estimate": (
                                projection_estimate.provider_request_token_estimate
                            ),
                            "auto_compact_trigger_tokens": auto_compact_trigger_tokens,
                            "auto_compact_trigger_ratio": (
                                context_config_resolved.auto_compact_trigger_ratio
                            ),
                            "runtime_context_budget_tokens": runtime_context_budget_tokens,
                            "hard_context_limit_tokens": runtime_hard_context_limit_tokens,
                            "consecutive_failures": (
                                state.auto_compact_consecutive_failures
                            ),
                            "trainable": False,
                        },
                    )
                )
                auto_compact_timeout = _resolve_provider_call_timeout(
                    configured_request_timeout_seconds=request_timeout_seconds,
                    task_deadline_monotonic=task_deadline_monotonic,
                    provider_timeout_grace_sec=provider_timeout_grace_sec,
                    min_provider_request_timeout_sec=min_provider_request_timeout_sec,
                    provider_timeout_policy=provider_timeout_policy,
                )
                if not auto_compact_timeout["should_call_provider"]:
                    _record_provider_call_skipped_due_to_deadline(
                        run_id=run_id,
                        task_id=task_id,
                        turn=turn,
                        state=state,
                        recorder=recorder,
                        timeout_facts=auto_compact_timeout["facts"],
                        call_site="proactive_auto_compact",
                    )
                    break
                auto_compact_result = self.auto_compact_runner.run(
                    mode="proactive",
                    trigger_reason="projection_above_auto_compact_trigger",
                    source_prepared=prepared,
                    recorder=recorder,
                    task_id=task_id,
                    turn=turn,
                    context_config=context_config_resolved,
                    provider_options=provider_options_resolved,
                    model_client=self.model_client,
                    tool_schema_snapshot_ref=tool_schema_snapshot_ref
                    or _placeholder_artifact_ref("tool_schema_snapshot"),
                    run_config_facts_ref=run_config_facts_ref
                    or RunConfigFactsRef(sha256="0" * 64),
                    tool_result_artifact_index=tool_context.tool_result_artifact_index
                    if tool_context
                    else None,
                    generation_config=generation_config or {},
                    provider_model_settings=provider_model_settings or {},
                    budget_state=state.budget_state.model_dump(mode="json"),
                    request_timeout_seconds=auto_compact_timeout["effective_request_timeout_seconds"],
                    request_timeout_policy_facts=auto_compact_timeout["facts"],
                    raw_request_logging_policy=raw_request_logging_policy,
                    retry_policy=retry_policy,
                    scaffold_id=self.scaffold.scaffold_id,
                )
                state.last_auto_compact_record_ref = (
                    auto_compact_result.record_ref.model_dump(mode="json")
                    if auto_compact_result.record_ref is not None
                    else None
                )
                state.last_auto_compact_summary_ref = (
                    auto_compact_result.summary_artifact_ref.model_dump(mode="json")
                    if auto_compact_result.summary_artifact_ref is not None
                    else None
                )
                state.last_auto_compact_context_revision_before = prepared.context_revision
                if auto_compact_result.status == "applied":
                    state.auto_compact_count += 1
                    state.auto_compact_consecutive_failures = 0
                    messages = [dict(message) for message in auto_compact_result.rebuilt_messages]
                    context_messages = _messages_with_phase_metadata(
                        messages=messages,
                        scaffold=self.scaffold,
                        phase=current_phase,
                        allowed_tool_names=phase_allowed_tool_names,
                    )
                    prepared = self.context_manager.prepare_messages(
                        messages=context_messages,
                        recorder=recorder,
                        task_id=task_id,
                        turn=turn,
                        context_config=context_config_resolved,
                        provider_name=provider_options_resolved.provider,
                        tool_result_artifact_index=tool_context.tool_result_artifact_index
                        if tool_context
                        else None,
                        context_budget_facts=context_budget_payload,
                    )
                    state.context_revision = prepared.context_revision
                    state.last_auto_compact_context_revision_after = prepared.context_revision
                    recorder.append_event(prepared.context_event)
                    recorder.append_event(
                        TrajectoryEvent(
                            event_id=recorder.next_event_id("auto_compact"),
                            timestamp=_timestamp(),
                            run_id=run_id,
                            task_id=task_id,
                            turn=turn,
                            event_type="context_post_compact_prepared",
                            artifact_refs=[
                                ref
                                for ref in [
                                    prepared.prepared_messages_ref,
                                    auto_compact_result.rebuilt_messages_ref,
                                    auto_compact_result.summary_artifact_ref,
                                ]
                                if ref is not None
                            ],
                            data={
                                "schema_version": (
                                    "repo_harness_context_post_compact_prepared_v1"
                                ),
                                "compact_id": auto_compact_result.compact_id,
                                "context_revision_before": (
                                    state.last_auto_compact_context_revision_before
                                ),
                                "context_revision_after": prepared.context_revision,
                                "prepared_messages_ref": prepared.prepared_messages_ref.model_dump(
                                    mode="json"
                                ),
                                "model_input_hash": prepared.model_input_hash,
                                "rebuilt_messages_ref": (
                                    auto_compact_result.rebuilt_messages_ref.model_dump(
                                        mode="json"
                                    )
                                    if auto_compact_result.rebuilt_messages_ref
                                    else None
                                ),
                                "summary_artifact_ref": (
                                    auto_compact_result.summary_artifact_ref.model_dump(
                                        mode="json"
                                    )
                                    if auto_compact_result.summary_artifact_ref
                                    else None
                                ),
                                "trainable": False,
                            },
                        )
                    )
                    pairing_validation = prepared.context_event.data.get(
                        "tool_pairing_validation", {}
                    )
                    if not pairing_validation.get("ok", True):
                        state.agent_stop_reason = "context_integrity_error"
                        state.budget_state.stop_reason = "context_integrity_error"
                        state.last_model_error = "context_integrity_error"
                        recorder.append_event(
                            TrajectoryEvent(
                                event_id=recorder.next_event_id("context_integrity"),
                                timestamp=_timestamp(),
                                run_id=run_id,
                                task_id=task_id,
                                turn=turn,
                                event_type="context_integrity_error",
                                severity="error",
                                error_type="tool_call_result_pairing_failed",
                                artifact_refs=[prepared.prepared_messages_ref],
                                data={
                                    "context_revision": prepared.context_revision,
                                    "model_input_hash": prepared.model_input_hash,
                                    "tool_pairing_validation": pairing_validation,
                                    "formal_policy": "stop_before_provider_request",
                                    "tainted": False,
                                    "after_auto_compact": True,
                                },
                            )
                        )
                        break
                    projection_estimate = _build_provider_request_projection_estimate(
                        prepared_messages=prepared.messages,
                        provider_options=provider_options_resolved,
                        allowed_tool_definitions=phase_allowed_tool_definitions,
                        generation_config=generation_config or {},
                        provider_model_settings=provider_model_settings or {},
                        provider_message_format=f"repo_harness_{provider_options_resolved.provider}_messages_v0",
                        context_budget_facts=context_budget_facts,
                    )
                    state.post_compact_above_target = (
                        projection_estimate.provider_request_token_estimate
                        > context_budget_facts.post_compact_target_tokens
                    )
                    auto_compact_applied_this_turn = True
                else:
                    state.auto_compact_consecutive_failures += 1
                    state.loop_diagnostics_summary = {
                        **state.loop_diagnostics_summary,
                        "last_auto_compact_failure_reason": (
                            auto_compact_result.failure_reason
                        ),
                        "auto_compact_consecutive_failures": (
                            state.auto_compact_consecutive_failures
                        ),
                    }
                    if (
                        projection_estimate.provider_request_token_estimate
                        > runtime_hard_context_limit_tokens
                    ):
                        state.agent_stop_reason = "auto_compact_failed_preflight"
                        state.budget_state.stop_reason = "auto_compact_failed_preflight"
                        recorder.append_event(
                            TrajectoryEvent(
                                event_id=recorder.next_event_id("budget"),
                                timestamp=_timestamp(),
                                run_id=run_id,
                                task_id=task_id,
                                turn=turn,
                                event_type="budget_exhausted",
                                severity="warning",
                                error_type="auto_compact_failed_preflight",
                                data={
                                    "token_estimate": (
                                        projection_estimate.provider_request_token_estimate
                                    ),
                                    "provider_request_projection_hash": (
                                        projection_estimate.provider_request_projection_hash
                                    ),
                                    "provider_request_projection_estimate": (
                                        projection_estimate.model_dump(mode="json")
                                    ),
                                    "auto_compact_failure_reason": (
                                        auto_compact_result.failure_reason
                                    ),
                                    "auto_compact_record_ref": (
                                        state.last_auto_compact_record_ref
                                    ),
                                    "max_context_tokens": runtime_context_budget_tokens,
                                    "hard_context_limit_tokens": (
                                        runtime_hard_context_limit_tokens
                                    ),
                                    "context_budget_facts": context_budget_payload,
                                },
                            )
                        )
                        break
            if projection_estimate.provider_request_token_estimate > runtime_hard_context_limit_tokens:
                stop_reason = (
                    "context_limit_preflight_after_autocompact"
                    if auto_compact_applied_this_turn
                    else "context_limit"
                )
                state.agent_stop_reason = stop_reason
                state.budget_state.stop_reason = stop_reason
                recorder.append_event(
                    TrajectoryEvent(
                        event_id=recorder.next_event_id("budget"),
                        timestamp=_timestamp(),
                        run_id=run_id,
                        task_id=task_id,
                        turn=turn,
                        event_type="budget_exhausted",
                        severity="warning",
                        error_type=stop_reason,
                        data={
                            "token_estimate": projection_estimate.provider_request_token_estimate,
                            "provider_ready_token_estimate": prepared.provider_ready_token_estimate,
                            "provider_body_char_estimate": prepared.provider_body_char_estimate,
                            "internal_token_estimate": prepared.internal_token_estimate,
                            "provider_request_projection_hash": (
                                projection_estimate.provider_request_projection_hash
                            ),
                            "provider_request_projection_estimate": (
                                projection_estimate.model_dump(mode="json")
                            ),
                            "threshold_decision_source": "provider_request_projection_estimate",
                            "provider_returned_prompt_tokens": None,
                            "provider_usage_metadata_status": "unavailable_before_provider_call",
                            "estimator_error_ratio": None,
                            "max_context_tokens": runtime_context_budget_tokens,
                            "hard_context_limit_tokens": runtime_hard_context_limit_tokens,
                            "context_budget_facts": context_budget_payload,
                            "auto_compact_applied_this_turn": auto_compact_applied_this_turn,
                            "auto_compact_record_ref": state.last_auto_compact_record_ref,
                            "auto_compact_summary_ref": state.last_auto_compact_summary_ref,
                        },
                    )
                )
                break
            model_call_timeout = _resolve_provider_call_timeout(
                configured_request_timeout_seconds=request_timeout_seconds,
                task_deadline_monotonic=task_deadline_monotonic,
                provider_timeout_grace_sec=provider_timeout_grace_sec,
                min_provider_request_timeout_sec=min_provider_request_timeout_sec,
                provider_timeout_policy=provider_timeout_policy,
            )
            if not model_call_timeout["should_call_provider"]:
                _record_provider_call_skipped_due_to_deadline(
                    run_id=run_id,
                    task_id=task_id,
                    turn=turn,
                    state=state,
                    recorder=recorder,
                    timeout_facts=model_call_timeout["facts"],
                    call_site="main_model_call",
                )
                break
            recorder.append_event(
                TrajectoryEvent(
                    event_id=recorder.next_event_id("model"),
                    timestamp=_timestamp(),
                    run_id=run_id,
                    task_id=task_id,
                    turn=turn,
                    event_type="model_call_started",
                    artifact_refs=[prepared.prepared_messages_ref],
                    data={
                        "model_call_id": f"{run_id}_model_call_{turn:04d}",
                        "context_revision": prepared.context_revision,
                        "prepared_messages_ref": prepared.prepared_messages_ref.model_dump(mode="json"),
                        "model_input_hash": prepared.model_input_hash,
                        "provider_request_projection_hash": (
                            projection_estimate.provider_request_projection_hash
                        ),
                        "provider_request_projection_estimate": (
                            projection_estimate.model_dump(mode="json")
                        ),
                        "context_budget_facts": context_budget_payload,
                        "scaffold_id": self.scaffold.scaffold_id,
                        "scaffold_phase": current_phase,
                        "scaffold_policy_snapshot": _scaffold_policy_snapshot(self.scaffold),
                        "budget_state": state.budget_state.model_dump(mode="json"),
                        "allowed_tools": phase_allowed_tool_names,
                        "tool_schema_snapshot_ref": (
                            tool_schema_snapshot_ref.model_dump(mode="json")
                            if tool_schema_snapshot_ref is not None
                            else None
                        ),
                        "run_config_facts_ref": (
                            run_config_facts_ref.model_dump(mode="json")
                            if run_config_facts_ref is not None
                            else None
                        ),
                    },
                )
            )
            model_request = _build_model_request_context(
                run_id=run_id,
                task_id=task_id,
                turn=turn,
                prepared_messages=prepared.messages,
                prepared_messages_ref=prepared.prepared_messages_ref,
                model_input_hash=prepared.model_input_hash,
                context_revision=prepared.context_revision,
                provider_options=provider_options_resolved,
                scaffold=self.scaffold,
                scaffold_phase=current_phase,
                allowed_tool_definitions=phase_allowed_tool_definitions,
                tool_schema_snapshot_ref=tool_schema_snapshot_ref
                or _placeholder_artifact_ref("tool_schema_snapshot"),
                run_config_facts_ref=run_config_facts_ref
                or RunConfigFactsRef(sha256="0" * 64),
                budget_state=state.budget_state.model_dump(mode="json"),
                generation_config=generation_config or {},
                provider_model_settings=provider_model_settings or {},
                request_timeout_seconds=model_call_timeout["effective_request_timeout_seconds"],
                request_timeout_policy_facts=model_call_timeout["facts"],
                raw_request_logging_policy=raw_request_logging_policy,
                retry_policy=retry_policy,
                provider_request_projection_hash=projection_estimate.provider_request_projection_hash,
                provider_request_token_estimate=projection_estimate.provider_request_token_estimate,
                provider_request_token_estimate_breakdown=projection_estimate.model_dump(mode="json"),
                context_budget_facts=context_budget_payload,
            )
            response = self.model_client.generate(
                request=model_request,
                recorder=recorder,
            )
            model_call_event = response.model_call_event or _synthetic_model_call_event(
                request=model_request,
                response=response,
                terminal_error_type=getattr(response, "terminal_error_type", None)
                or getattr(response, "model_error_type", None),
            )
            if response.model_call_event is None:
                recorder.append_event(
                    TrajectoryEvent(
                        event_id=recorder.next_event_id("model"),
                        timestamp=_timestamp(),
                        run_id=run_id,
                        task_id=task_id,
                        turn=turn,
                        event_type="model_call_event_reconstructed",
                        severity="warning",
                        artifact_refs=[
                            ref
                            for ref in [
                                getattr(response, "raw_provider_request_ref", None),
                                getattr(response, "raw_provider_response_ref", None),
                            ]
                            if ref is not None
                        ],
                        data={
                            "model_call_id": model_call_event.model_call_id,
                            "reason": "provider_response_missing_model_call_event",
                            "trainable": False,
                        },
                    )
                )
            state.budget_state.input_tokens += model_call_event.input_tokens
            state.budget_state.output_tokens += model_call_event.output_tokens
            if _model_input_was_accepted(response):
                commit_result = self.context_manager.commit_prepared_tool_result_decisions(
                    context_revision=prepared.context_revision,
                    prepared_messages_ref=prepared.prepared_messages_ref,
                    model_call_id=model_request.model_call_id,
                    tool_result_artifact_index=tool_context.tool_result_artifact_index
                    if tool_context
                    else None,
                )
                committed_state = commit_result.pop("content_replacement_state")
                committed_state_ref = recorder.write_json_artifact(
                    "content_replacement_state",
                    committed_state.model_dump(mode="json"),
                    {"budget_policy": "preserve_json"},
                )
                context_policy_snapshot_ref = _write_context_policy_snapshot_artifact(
                    recorder
                )
                model_input_snapshot = ModelInputSnapshot(
                    model_call_id=model_request.model_call_id,
                    prepared_messages_ref=prepared.prepared_messages_ref,
                    model_input_hash=prepared.model_input_hash,
                    provider_request_projection_hash=(
                        projection_estimate.provider_request_projection_hash
                    ),
                    context_policy_snapshot_ref=context_policy_snapshot_ref,
                    provider_request_artifact_ref=response.raw_provider_request_ref,
                    provider_response_artifact_ref=response.raw_provider_response_ref,
                    context_compact_state_ref=committed_state_ref,
                    trainable=response.model_error_type is None,
                )
                model_input_snapshot_ref = recorder.write_json_artifact(
                    "model_input_snapshot",
                    model_input_snapshot.model_dump(mode="json"),
                    {
                        "redaction_status": "not_sensitive",
                        "retention_policy": "model_input_snapshot",
                        "budget_policy": "preserve_json",
                    },
                )
                recorder.append_event(
                    TrajectoryEvent(
                        event_id=recorder.next_event_id("model_input"),
                        timestamp=_timestamp(),
                        run_id=run_id,
                        task_id=task_id,
                        turn=turn,
                        event_type="model_input_accepted",
                        artifact_refs=[
                            ref
                            for ref in [
                                prepared.prepared_messages_ref,
                                committed_state_ref,
                                context_policy_snapshot_ref,
                                model_input_snapshot_ref,
                                response.raw_provider_request_ref,
                                response.raw_provider_response_ref,
                            ]
                            if ref is not None
                        ],
                        data={
                            **commit_result,
                            "model_call_id": model_request.model_call_id,
                            "model_input_hash": prepared.model_input_hash,
                            "provider_request_projection_hash": (
                                projection_estimate.provider_request_projection_hash
                            ),
                            "provider_request_projection_estimate": (
                                projection_estimate.model_dump(mode="json")
                            ),
                            "provider_request_projection_status": "materialized_before_provider_call",
                            "content_replacement_state_hash": committed_state.state_hash,
                            "content_replacement_state_ref": committed_state_ref.model_dump(
                                mode="json"
                            ),
                            "context_policy_snapshot_ref": (
                                context_policy_snapshot_ref.model_dump(mode="json")
                                if context_policy_snapshot_ref is not None
                                else None
                            ),
                            "model_input_snapshot_ref": model_input_snapshot_ref.model_dump(
                                mode="json"
                            ),
                            "provider_request_artifact_ref": (
                                response.raw_provider_request_ref.model_dump(mode="json")
                                if response.raw_provider_request_ref is not None
                                else None
                            ),
                            "provider_response_artifact_ref": (
                                response.raw_provider_response_ref.model_dump(mode="json")
                                if response.raw_provider_response_ref is not None
                                else None
                            ),
                            "trainable": response.model_error_type is None,
                            "model_input_acceptance_policy": (
                                "commit_after_non_context_limit_provider_response_v1"
                            ),
                        },
                    )
                )
            provider_attempt_refs = list(getattr(response, "provider_attempt_refs", []) or [])
            retry_policy_ref = getattr(response, "retry_policy_ref", None)
            attempt_count = int(getattr(response, "attempt_count", max(1, len(provider_attempt_refs))) or 1)
            retry_count = int(getattr(response, "retry_count", max(0, attempt_count - 1)) or 0)
            terminal_error_type = getattr(response, "terminal_error_type", response.model_error_type)
            budget_decision_trace_ref = None
            budget_decision_trace_ref = _write_budget_decision_trace_artifact(
                recorder=recorder,
                run_id=run_id,
                task_id=task_id,
                turn=turn,
                budget_manager=budget_manager,
                state=state,
                response=response,
                model_call_event=model_call_event,
            )
            recorder.append_event(
                TrajectoryEvent(
                    event_id=recorder.next_event_id("model"),
                    timestamp=_timestamp(),
                    run_id=run_id,
                    task_id=task_id,
                    turn=turn,
                    event_type="model_call_completed",
                    artifact_refs=[
                        ref
                        for ref in [
                            response.raw_provider_request_ref,
                            response.raw_provider_response_ref,
                            retry_policy_ref,
                            budget_decision_trace_ref,
                            *provider_attempt_refs,
                        ]
                        if ref is not None
                    ],
                    data={
                        **model_call_event.model_dump(mode="json"),
                        "turn": turn,
                        "scaffold_id": self.scaffold.scaffold_id,
                        "scaffold_phase": current_phase,
                        "budget_state": state.budget_state.model_dump(mode="json"),
                        "allowed_tools": phase_allowed_tool_names,
                        "run_config_facts_ref": (
                            run_config_facts_ref.model_dump(mode="json")
                            if run_config_facts_ref is not None
                            else None
                        ),
                        "raw_provider_request_ref": (
                            response.raw_provider_request_ref.model_dump(mode="json")
                            if response.raw_provider_request_ref
                            else None
                        ),
                        "raw_provider_response_ref": (
                            response.raw_provider_response_ref.model_dump(mode="json")
                            if response.raw_provider_response_ref
                            else None
                        ),
                        "provider_attempt_refs": [
                            ref.model_dump(mode="json") for ref in provider_attempt_refs
                        ],
                        "retry_policy_ref": (
                            retry_policy_ref.model_dump(mode="json")
                            if retry_policy_ref
                            else None
                        ),
                        "attempt_count": attempt_count,
                        "retry_count": retry_count,
                        "terminal_error_type": terminal_error_type,
                        "model_call_event_reconstructed": response.model_call_event is None,
                        "model_call_event_source": (
                            "agent_loop_synthetic_missing_provider_event"
                            if response.model_call_event is None
                            else "provider_response"
                        ),
                        "budget_decision_trace_ref": (
                            budget_decision_trace_ref.model_dump(mode="json")
                            if budget_decision_trace_ref
                            else None
                        ),
                    },
                )
            )
            if _provider_context_limit_rejected_input(response, terminal_error_type):
                state.last_model_error = terminal_error_type or response.model_error_type
                recorder.append_event(
                    TrajectoryEvent(
                        event_id=recorder.next_event_id("reactive_compact"),
                        timestamp=_timestamp(),
                        run_id=run_id,
                        task_id=task_id,
                        turn=turn,
                        event_type="reactive_compact_triggered",
                        severity="warning",
                        error_type="provider_context_limit",
                        artifact_refs=[
                            ref
                            for ref in [
                                prepared.prepared_messages_ref,
                                response.raw_provider_request_ref,
                                response.raw_provider_response_ref,
                            ]
                            if ref is not None
                        ],
                        data={
                            "schema_version": "repo_harness_reactive_compact_triggered_v1",
                            "trigger_reason": "provider_context_limit_retry",
                            "model_call_id": model_request.model_call_id,
                            "context_revision": prepared.context_revision,
                            "prepared_messages_ref": prepared.prepared_messages_ref.model_dump(
                                mode="json"
                            ),
                            "model_input_hash": prepared.model_input_hash,
                            "terminal_error_type": terminal_error_type,
                            "model_error_type": response.model_error_type,
                            "raw_provider_request_ref": (
                                response.raw_provider_request_ref.model_dump(mode="json")
                                if response.raw_provider_request_ref is not None
                                else None
                            ),
                            "raw_provider_response_ref": (
                                response.raw_provider_response_ref.model_dump(mode="json")
                                if response.raw_provider_response_ref is not None
                                else None
                            ),
                            "token_gap_status": "unknown",
                            "ordinary_assistant_message_appended": False,
                            "trainable": False,
                        },
                    )
                )
                if (
                    not context_config_resolved.reactive_compact_enabled
                    or context_config_resolved.reactive_compact_retry_limit <= 0
                ):
                    state.agent_stop_reason = "context_limit_reactive_compact_disabled"
                    state.budget_state.stop_reason = "context_limit_reactive_compact_disabled"
                    recorder.append_event(
                        TrajectoryEvent(
                            event_id=recorder.next_event_id("reactive_compact"),
                            timestamp=_timestamp(),
                            run_id=run_id,
                            task_id=task_id,
                            turn=turn,
                            event_type="reactive_compact_skipped",
                            severity="warning",
                            error_type="context_limit_reactive_compact_disabled",
                            artifact_refs=[
                                ref
                                for ref in [
                                    prepared.prepared_messages_ref,
                                    response.raw_provider_request_ref,
                                    response.raw_provider_response_ref,
                                ]
                                if ref is not None
                            ],
                            data={
                                "schema_version": "repo_harness_reactive_compact_skipped_v1",
                                "reason": "reactive_compact_disabled_or_retry_limit_zero",
                                "reactive_compact_enabled": (
                                    context_config_resolved.reactive_compact_enabled
                                ),
                                "reactive_compact_retry_limit": (
                                    context_config_resolved.reactive_compact_retry_limit
                                ),
                                "trainable": False,
                            },
                        )
                    )
                    break
                if (
                    state.reactive_compact_retry_count
                    >= context_config_resolved.reactive_compact_retry_limit
                ):
                    state.agent_stop_reason = "context_limit_after_reactive_compact"
                    state.budget_state.stop_reason = "context_limit_after_reactive_compact"
                    recorder.append_event(
                        TrajectoryEvent(
                            event_id=recorder.next_event_id("reactive_compact"),
                            timestamp=_timestamp(),
                            run_id=run_id,
                            task_id=task_id,
                            turn=turn,
                            event_type="reactive_compact_retry_limit_exhausted",
                            severity="error",
                            error_type="context_limit_after_reactive_compact",
                            artifact_refs=[
                                ref
                                for ref in [
                                    prepared.prepared_messages_ref,
                                    response.raw_provider_request_ref,
                                    response.raw_provider_response_ref,
                                ]
                                if ref is not None
                            ],
                            data={
                                "schema_version": (
                                    "repo_harness_reactive_compact_retry_limit_exhausted_v1"
                                ),
                                "reactive_compact_retry_count": (
                                    state.reactive_compact_retry_count
                                ),
                                "reactive_compact_retry_limit": (
                                    context_config_resolved.reactive_compact_retry_limit
                                ),
                                "trainable": False,
                            },
                        )
                    )
                    break
                emergency_timeout = _resolve_provider_call_timeout(
                    configured_request_timeout_seconds=request_timeout_seconds,
                    task_deadline_monotonic=task_deadline_monotonic,
                    provider_timeout_grace_sec=provider_timeout_grace_sec,
                    min_provider_request_timeout_sec=min_provider_request_timeout_sec,
                    provider_timeout_policy=provider_timeout_policy,
                )
                if not emergency_timeout["should_call_provider"]:
                    _record_provider_call_skipped_due_to_deadline(
                        run_id=run_id,
                        task_id=task_id,
                        turn=turn,
                        state=state,
                        recorder=recorder,
                        timeout_facts=emergency_timeout["facts"],
                        call_site="emergency_auto_compact",
                    )
                    break
                emergency_result = self.auto_compact_runner.run(
                    mode="emergency",
                    trigger_reason="provider_context_limit_retry",
                    source_prepared=prepared,
                    recorder=recorder,
                    task_id=task_id,
                    turn=turn,
                    context_config=context_config_resolved,
                    provider_options=provider_options_resolved,
                    model_client=self.model_client,
                    tool_schema_snapshot_ref=tool_schema_snapshot_ref
                    or _placeholder_artifact_ref("tool_schema_snapshot"),
                    run_config_facts_ref=run_config_facts_ref
                    or RunConfigFactsRef(sha256="0" * 64),
                    tool_result_artifact_index=tool_context.tool_result_artifact_index
                    if tool_context
                    else None,
                    generation_config=generation_config or {},
                    provider_model_settings=provider_model_settings or {},
                    budget_state=state.budget_state.model_dump(mode="json"),
                    request_timeout_seconds=emergency_timeout["effective_request_timeout_seconds"],
                    request_timeout_policy_facts=emergency_timeout["facts"],
                    raw_request_logging_policy=raw_request_logging_policy,
                    retry_policy=retry_policy,
                    scaffold_id=self.scaffold.scaffold_id,
                )
                if emergency_result.status == "applied":
                    state.auto_compact_count += 1
                    state.reactive_compact_count += 1
                    state.reactive_compact_retry_count += 1
                    state.last_auto_compact_record_ref = (
                        emergency_result.record_ref.model_dump(mode="json")
                        if emergency_result.record_ref is not None
                        else None
                    )
                    state.last_auto_compact_summary_ref = (
                        emergency_result.summary_artifact_ref.model_dump(mode="json")
                        if emergency_result.summary_artifact_ref is not None
                        else None
                    )
                    state.last_reactive_compact_record_ref = state.last_auto_compact_record_ref
                    state.last_reactive_compact_summary_ref = state.last_auto_compact_summary_ref
                    messages = [dict(message) for message in emergency_result.rebuilt_messages]
                    recorder.append_event(
                        TrajectoryEvent(
                            event_id=recorder.next_event_id("reactive_compact"),
                            timestamp=_timestamp(),
                            run_id=run_id,
                            task_id=task_id,
                            turn=turn,
                            event_type="reactive_compact_applied",
                            severity="warning",
                            artifact_refs=[
                                ref
                                for ref in [
                                    emergency_result.record_ref,
                                    emergency_result.summary_artifact_ref,
                                    emergency_result.rebuilt_messages_ref,
                                ]
                                if ref is not None
                            ],
                            data={
                                "schema_version": "repo_harness_reactive_compact_applied_v1",
                                "compact_id": emergency_result.compact_id,
                                "trigger_reason": "provider_context_limit_retry",
                                "mode": "emergency",
                                "source_prepared_messages_ref": (
                                    emergency_result.source_prepared_messages_ref.model_dump(
                                        mode="json"
                                    )
                                ),
                                "summary_artifact_ref": (
                                    emergency_result.summary_artifact_ref.model_dump(
                                        mode="json"
                                    )
                                    if emergency_result.summary_artifact_ref
                                    else None
                                ),
                                "rebuilt_messages_ref": (
                                    emergency_result.rebuilt_messages_ref.model_dump(
                                        mode="json"
                                    )
                                    if emergency_result.rebuilt_messages_ref
                                    else None
                                ),
                                "reactive_compact_retry_count": (
                                    state.reactive_compact_retry_count
                                ),
                                "reactive_compact_retry_limit": (
                                    context_config_resolved.reactive_compact_retry_limit
                                ),
                                "ordinary_assistant_message_appended": False,
                                "trainable": False,
                            },
                        )
                    )
                    continue
                ptl_result = _truncate_head_for_ptl_retry(
                    messages=messages,
                    recorder=recorder,
                    run_id=run_id,
                    task_id=task_id,
                    turn=turn,
                    ordinary_turn=state.turn_count,
                    context_config=context_config_resolved,
                    provider_options=provider_options_resolved,
                    allowed_tool_definitions=phase_allowed_tool_definitions,
                    generation_config=generation_config or {},
                    provider_model_settings=provider_model_settings or {},
                    context_budget_facts=context_budget_facts,
                    hard_context_limit_tokens=runtime_hard_context_limit_tokens,
                    original_model_call_id=model_request.model_call_id,
                    original_prepared_messages_ref=prepared.prepared_messages_ref,
                    original_model_input_hash=prepared.model_input_hash,
                    original_provider_request_ref=response.raw_provider_request_ref,
                    original_provider_response_ref=response.raw_provider_response_ref,
                    emergency_compact_record_ref=emergency_result.record_ref,
                    emergency_compact_failure_reason=emergency_result.failure_reason,
                )
                if ptl_result["status"] == "applied":
                    state.reactive_compact_count += 1
                    state.reactive_compact_retry_count += 1
                    state.ptl_truncation_count += 1
                    state.last_ptl_truncation_ref = ptl_result[
                        "ptl_truncation_ref"
                    ].model_dump(mode="json")
                    messages = [dict(message) for message in ptl_result["messages"]]
                    recorder.append_event(
                        TrajectoryEvent(
                            event_id=recorder.next_event_id("ptl_truncation"),
                            timestamp=_timestamp(),
                            run_id=run_id,
                            task_id=task_id,
                            turn=turn,
                            event_type="ptl_truncation_applied",
                            severity="warning",
                            artifact_refs=[ptl_result["ptl_truncation_ref"]],
                            data={
                                "schema_version": "repo_harness_ptl_truncation_applied_v1",
                                "ptl_truncation_ref": ptl_result[
                                    "ptl_truncation_ref"
                                ].model_dump(mode="json"),
                                "original_model_call_id": model_request.model_call_id,
                                "ordinary_turn": state.turn_count,
                                "recovery_retry_index": (
                                    state.reactive_compact_retry_count
                                ),
                                "omitted_round_count": ptl_result[
                                    "omitted_round_count"
                                ],
                                "synthetic_marker_id": ptl_result[
                                    "synthetic_marker_id"
                                ],
                                "token_estimate_before": ptl_result[
                                    "token_estimate_before"
                                ],
                                "token_estimate_after": ptl_result[
                                    "token_estimate_after"
                                ],
                                "post_truncation_above_hard_limit": ptl_result[
                                    "post_truncation_above_hard_limit"
                                ],
                                "trainable": False,
                            },
                        )
                    )
                    continue
                state.agent_stop_reason = "reactive_compact_failed"
                state.budget_state.stop_reason = "reactive_compact_failed"
                recorder.append_event(
                    TrajectoryEvent(
                        event_id=recorder.next_event_id("reactive_compact"),
                        timestamp=_timestamp(),
                        run_id=run_id,
                        task_id=task_id,
                        turn=turn,
                        event_type="reactive_compact_failed",
                        severity="error",
                        error_type=emergency_result.failure_reason
                        or "emergency_auto_compact_failed",
                        artifact_refs=[
                            ref
                            for ref in [
                                emergency_result.record_ref,
                                emergency_result.compact_model_request_ref,
                                emergency_result.compact_model_response_ref,
                                ptl_result.get("ptl_truncation_ref"),
                            ]
                            if ref is not None
                        ],
                        data={
                            "schema_version": "repo_harness_reactive_compact_failed_v1",
                            "compact_id": emergency_result.compact_id,
                            "failure_reason": emergency_result.failure_reason,
                            "status": emergency_result.status,
                            "ptl_fallback_status": ptl_result["status"],
                            "ptl_fallback_failure_reason": ptl_result.get(
                                "failure_reason"
                            ),
                            "ptl_truncation_ref": (
                                ptl_result["ptl_truncation_ref"].model_dump(mode="json")
                                if ptl_result.get("ptl_truncation_ref") is not None
                                else None
                            ),
                            "ordinary_assistant_message_appended": False,
                            "trainable": False,
                        },
                    )
                )
                break
            assistant_artifact_ref = _write_assistant_message_artifact(
                recorder=recorder,
                content=response.assistant_message.content,
                tool_calls=response.tool_calls,
                finish_reason=response.finish_reason,
                model_error_type=response.model_error_type,
            )
            assistant_preview = _assistant_transcript_preview(
                content=response.assistant_message.content,
                tool_calls=response.tool_calls,
            )
            recorder.append_transcript(
                TranscriptRecord(
                    record_id=recorder.next_record_id(),
                    run_id=run_id,
                    task_id=task_id,
                    message_id=f"assistant_{turn}",
                    turn=turn,
                    role="assistant",
                    model_call_id=model_call_event.model_call_id,
                    content_preview=assistant_preview[:4000],
                    content_artifact_refs=[assistant_artifact_ref],
                    model_visible=True,
                    trainable=response.model_error_type is None,
                    created_at=_timestamp(),
                )
            )
            assistant_message = {
                "role": "assistant",
                "content": response.assistant_message.content,
                "tool_calls": [call.model_dump(mode="json") for call in response.tool_calls],
                "model_error_type": response.model_error_type,
                "scaffold_phase": current_phase,
            }
            safe_metadata = sanitize_provider_private_metadata_for_messages(
                response.assistant_message.metadata
            )
            if safe_metadata:
                assistant_message["metadata"] = safe_metadata
            messages.append(assistant_message)
            budget_stop = _budget_stop_reason(
                budget_manager,
                state,
                loop_started,
                task_deadline_monotonic=task_deadline_monotonic,
            )
            if budget_stop is not None:
                _record_budget_exhausted(
                    run_id=run_id,
                    task_id=task_id,
                    turn=turn,
                    reason=budget_stop,
                    state=state,
                    recorder=recorder,
                )
                _record_interrupted_tool_calls(
                    tool_result_artifact_index=tool_context.tool_result_artifact_index if tool_context else None,
                    context_config=context_config_resolved,
                    run_id=run_id,
                    task_id=task_id,
                    turn=turn,
                    tool_calls=response.tool_calls,
                    reason=budget_stop,
                    state=state,
                    recorder=recorder,
                    messages=messages,
                    emit_tool_requested=True,
                )
                break
            if response.model_error_type:
                if (
                    response.model_error_type == "tool_call_parse_failure"
                    and malformed_tool_call_repair_count < 1
                ):
                    malformed_tool_call_repair_count += 1
                    repair_message = _tool_call_parse_repair_message(response)
                    messages.append(repair_message)
                    recorder.append_transcript(
                        TranscriptRecord(
                            record_id=recorder.next_record_id(),
                            run_id=run_id,
                            task_id=task_id,
                            message_id=f"tool_call_repair_{turn}",
                            turn=turn,
                            role="user",
                            content_preview=str(repair_message["content"])[:4000],
                            model_visible=True,
                            trainable=False,
                            created_at=_timestamp(),
                        )
                    )
                    recorder.append_event(
                        TrajectoryEvent(
                            event_id=recorder.next_event_id("tool_call_repair"),
                            timestamp=_timestamp(),
                            run_id=run_id,
                            task_id=task_id,
                            turn=turn,
                            event_type="tool_call_repair_requested",
                            severity="warning",
                            error_type="tool_call_parse_failure",
                            data={
                                "repair_attempt": malformed_tool_call_repair_count,
                                "max_attempts": 1,
                                "model_error_type": response.model_error_type,
                                "provider_error_message": response.assistant_message.metadata.get(
                                    "provider_error_message"
                                ),
                                "raw_provider_artifact_visible": False,
                            },
                        )
                    )
                    continue
                if response.model_error_type == "tool_call_parse_failure":
                    state.agent_stop_reason = "tool_call_parse_failure_unrecovered"
                    state.budget_state.stop_reason = "tool_call_parse_failure_unrecovered"
                elif response.model_error_type == "output_token_limit_reached":
                    state.agent_stop_reason = "output_token_limit_reached"
                    state.budget_state.stop_reason = "output_token_limit_reached"
                else:
                    state.agent_stop_reason = "model_error"
                    state.budget_state.stop_reason = "model_error"
                state.last_model_error = response.model_error_type
                _record_interrupted_tool_calls(
                    tool_result_artifact_index=tool_context.tool_result_artifact_index if tool_context else None,
                    context_config=context_config_resolved,
                    run_id=run_id,
                    task_id=task_id,
                    turn=turn,
                    tool_calls=response.tool_calls,
                    reason=response.model_error_type,
                    state=state,
                    recorder=recorder,
                    messages=messages,
                    emit_tool_requested=True,
                )
                break
            if not response.tool_calls:
                if self.scaffold.scaffold_id == "single_shot_patch":
                    patch_applied = _handle_single_shot_patch_response(
                        run_id=run_id,
                        task_id=task_id,
                        turn=turn,
                        content=response.assistant_message.content,
                        tool_context=tool_context,
                        state=state,
                        recorder=recorder,
                        messages=messages,
                    )
                    state.agent_stop_reason = "final_answer" if patch_applied else "model_error"
                    state.budget_state.stop_reason = state.agent_stop_reason
                    break
                if _uses_phase_transitions(self.scaffold) and current_phase != "final":
                    _record_phase_transition(
                        run_id=run_id,
                        task_id=task_id,
                        turn=turn,
                        from_phase=current_phase,
                        to_phase=_next_phase_after_assistant_message(current_phase),
                        reason="assistant_message_without_tool",
                        scaffold=self.scaffold,
                        state=state,
                        recorder=recorder,
                    )
                    continue
                if self.scaffold.is_valid_final_answer(
                    response.assistant_message.content,
                    response.finish_reason,
                ):
                    state.agent_stop_reason = "final_answer"
                else:
                    state.agent_stop_reason = "model_error"
                    state.last_model_error = "invalid_final_answer"
                state.budget_state.stop_reason = state.agent_stop_reason
                break
            if self.scaffold.scaffold_id == "single_shot_patch":
                for tool_call in response.tool_calls:
                    _record_tool_requested(
                        run_id=run_id,
                        task_id=task_id,
                        turn=turn,
                        tool_call=tool_call,
                        recorder=recorder,
                    )
                    state.tool_call_count += 1
                    state.budget_state.tool_call_count = state.tool_call_count
                    _record_tool_result(
                        tool_result_artifact_index=tool_context.tool_result_artifact_index if tool_context else None,
                        context_config=context_config_resolved,
                        run_id=run_id,
                        task_id=task_id,
                        turn=turn,
                        tool_result=self.tool_executor.disallowed_tool_result(
                            tool_call,
                            reason=(
                                "single_shot_patch accepts one patch action and does not allow "
                                "model tool calls or intermediate test feedback."
                            ),
                        ),
                        state=state,
                        recorder=recorder,
                        messages=messages,
                    )
                state.agent_stop_reason = "model_error"
                state.budget_state.stop_reason = "model_error"
                state.last_model_error = "single_shot_patch_tool_call_not_allowed"
                break
            stop_after_tools = False
            successful_tool_observation = False
            for tool_index, tool_call in enumerate(response.tool_calls):
                _record_tool_requested(
                    run_id=run_id,
                    task_id=task_id,
                    turn=turn,
                    tool_call=tool_call,
                    recorder=recorder,
                )
                budget_stop = _budget_stop_reason(
                    budget_manager,
                    state,
                    loop_started,
                    task_deadline_monotonic=task_deadline_monotonic,
                )
                if budget_stop is not None:
                    _record_budget_exhausted(
                        run_id=run_id,
                        task_id=task_id,
                        turn=turn,
                        reason=budget_stop,
                        state=state,
                        recorder=recorder,
                    )
                    _record_tool_result(
                        tool_result_artifact_index=tool_context.tool_result_artifact_index if tool_context else None,
                        context_config=context_config_resolved,
                        run_id=run_id,
                        task_id=task_id,
                        turn=turn,
                        tool_result=_interrupted_tool_result(tool_call, budget_stop),
                        state=state,
                        recorder=recorder,
                        messages=messages,
                    )
                    _record_interrupted_tool_calls(
                        tool_result_artifact_index=tool_context.tool_result_artifact_index if tool_context else None,
                        context_config=context_config_resolved,
                        run_id=run_id,
                        task_id=task_id,
                        turn=turn,
                        tool_calls=response.tool_calls[tool_index + 1 :],
                        reason=budget_stop,
                        state=state,
                        recorder=recorder,
                        messages=messages,
                        emit_tool_requested=True,
                    )
                    stop_after_tools = True
                    break
                if state.tool_call_count >= budget_manager.max_tool_calls:
                    state.agent_stop_reason = "max_tool_calls"
                    state.budget_state.stop_reason = "max_tool_calls"
                    _record_tool_result(
                        tool_result_artifact_index=tool_context.tool_result_artifact_index if tool_context else None,
                        context_config=context_config_resolved,
                        run_id=run_id,
                        task_id=task_id,
                        turn=turn,
                        tool_result=_interrupted_tool_result(tool_call, "max_tool_calls"),
                        state=state,
                        recorder=recorder,
                        messages=messages,
                    )
                    _record_interrupted_tool_calls(
                        tool_result_artifact_index=tool_context.tool_result_artifact_index if tool_context else None,
                        context_config=context_config_resolved,
                        run_id=run_id,
                        task_id=task_id,
                        turn=turn,
                        tool_calls=response.tool_calls[tool_index + 1 :],
                        reason="max_tool_calls",
                        state=state,
                        recorder=recorder,
                        messages=messages,
                        emit_tool_requested=True,
                    )
                    stop_after_tools = True
                    break
                state.tool_call_count += 1
                state.budget_state.tool_call_count = state.tool_call_count
                if (
                    self.tool_executor.is_known(tool_call.tool_name)
                    and tool_call.tool_name not in phase_allowed_tool_names
                ):
                    recorder.append_event(
                        TrajectoryEvent(
                            event_id=recorder.next_event_id("tool"),
                            timestamp=_timestamp(),
                            run_id=run_id,
                            task_id=task_id,
                            turn=turn,
                            event_type="tool_not_allowed",
                            severity="warning",
                            error_type="tool_not_allowed_by_scaffold",
                            data={
                                **tool_call.model_dump(mode="json"),
                                "allowed_tools": phase_allowed_tool_names,
                                "scaffold_id": self.scaffold.scaffold_id,
                                "scaffold_phase": current_phase,
                            },
                        )
                    )
                    _record_tool_result(
                        tool_result_artifact_index=tool_context.tool_result_artifact_index if tool_context else None,
                        context_config=context_config_resolved,
                        run_id=run_id,
                        task_id=task_id,
                        turn=turn,
                        tool_result=self.tool_executor.disallowed_tool_result(
                            tool_call,
                            reason=(
                                f"Tool {tool_call.tool_name!r} is not allowed by scaffold "
                                f"{self.scaffold.scaffold_id!r} with the resolved runtime policy."
                            ),
                        ),
                        state=state,
                        recorder=recorder,
                        messages=messages,
                    )
                    continue
                if not self.tool_executor.is_known(tool_call.tool_name):
                    state.invalid_tool_call_count += 1
                    recorder.append_event(
                        TrajectoryEvent(
                            event_id=recorder.next_event_id("tool"),
                            timestamp=_timestamp(),
                            run_id=run_id,
                            task_id=task_id,
                            turn=turn,
                            event_type="invalid_tool",
                            severity="warning",
                            error_type="unknown_tool",
                            data=tool_call.model_dump(mode="json"),
                        )
                    )
                    _record_tool_result(
                        tool_result_artifact_index=tool_context.tool_result_artifact_index if tool_context else None,
                        context_config=context_config_resolved,
                        run_id=run_id,
                        task_id=task_id,
                        turn=turn,
                        tool_result=self.tool_executor.invalid_tool_result(tool_call),
                        state=state,
                        recorder=recorder,
                        messages=messages,
                    )
                    continue
                validation_error = self.tool_executor.validate_input(tool_call, tool_context)
                if validation_error is not None:
                    recorder.append_event(
                        TrajectoryEvent(
                            event_id=recorder.next_event_id("tool"),
                            timestamp=_timestamp(),
                            run_id=run_id,
                            task_id=task_id,
                            turn=turn,
                            event_type="tool_validation_failed",
                            severity="warning",
                            error_type=validation_error.error_type,
                            artifact_refs=validation_error.artifact_refs,
                            data=validation_error.model_dump(mode="json"),
                        )
                    )
                    _record_tool_result(
                        tool_result_artifact_index=tool_context.tool_result_artifact_index if tool_context else None,
                        context_config=context_config_resolved,
                        run_id=run_id,
                        task_id=task_id,
                        turn=turn,
                        tool_result=validation_error,
                        state=state,
                        recorder=recorder,
                        messages=messages,
                    )
                    continue
                normalized_request = self.tool_executor.normalize(tool_call, tool_context)
                if (
                    normalized_request.effective_tool_name == "run_tests"
                    and self.test_feedback_policy == "disabled"
                ):
                    recorder.append_event(
                        TrajectoryEvent(
                            event_id=recorder.next_event_id("tool"),
                            timestamp=_timestamp(),
                            run_id=run_id,
                            task_id=task_id,
                            turn=turn,
                            event_type="test_feedback_disabled",
                            severity="warning",
                            error_type="test_feedback_disabled",
                            data={
                                **tool_call.model_dump(mode="json"),
                                "route_reason": normalized_request.route_reason,
                                "requested_tool_name": normalized_request.requested_tool_name,
                                "effective_tool_name": normalized_request.effective_tool_name,
                                "test_feedback_policy": self.test_feedback_policy,
                            },
                        )
                    )
                    _record_tool_result(
                        tool_result_artifact_index=tool_context.tool_result_artifact_index if tool_context else None,
                        context_config=context_config_resolved,
                        run_id=run_id,
                        task_id=task_id,
                        turn=turn,
                        tool_result=self.tool_executor.disabled_test_feedback_result(
                            tool_call,
                            normalized_request,
                        ),
                        state=state,
                        recorder=recorder,
                        messages=messages,
                    )
                    continue
                if (
                    self.tool_executor.is_known(normalized_request.effective_tool_name)
                    and normalized_request.effective_tool_name not in phase_allowed_tool_names
                ):
                    recorder.append_event(
                        TrajectoryEvent(
                            event_id=recorder.next_event_id("tool"),
                            timestamp=_timestamp(),
                            run_id=run_id,
                            task_id=task_id,
                            turn=turn,
                            event_type="tool_not_allowed",
                            severity="warning",
                            error_type="tool_not_allowed_by_scaffold",
                            data={
                                **tool_call.model_dump(mode="json"),
                                "allowed_tools": phase_allowed_tool_names,
                                "scaffold_id": self.scaffold.scaffold_id,
                                "scaffold_phase": current_phase,
                                "requested_tool_name": normalized_request.requested_tool_name,
                                "effective_tool_name": normalized_request.effective_tool_name,
                                "route_reason": normalized_request.route_reason,
                            },
                        )
                    )
                    _record_tool_result(
                        tool_result_artifact_index=tool_context.tool_result_artifact_index if tool_context else None,
                        context_config=context_config_resolved,
                        run_id=run_id,
                        task_id=task_id,
                        turn=turn,
                        tool_result=self.tool_executor.disallowed_tool_result(
                            tool_call,
                            normalized=normalized_request,
                            reason=(
                                f"Tool {normalized_request.effective_tool_name!r} is not allowed by scaffold "
                                f"{self.scaffold.scaffold_id!r} in phase {current_phase!r} after tool normalization."
                            ),
                        ),
                        state=state,
                        recorder=recorder,
                        messages=messages,
                    )
                    continue
                budget_stop = _budget_stop_reason(
                    budget_manager,
                    state,
                    loop_started,
                    task_deadline_monotonic=task_deadline_monotonic,
                )
                if budget_stop is not None:
                    _record_budget_exhausted(
                        run_id=run_id,
                        task_id=task_id,
                        turn=turn,
                        reason=budget_stop,
                        state=state,
                        recorder=recorder,
                    )
                    _record_tool_result(
                        tool_result_artifact_index=tool_context.tool_result_artifact_index if tool_context else None,
                        context_config=context_config_resolved,
                        run_id=run_id,
                        task_id=task_id,
                        turn=turn,
                        tool_result=_interrupted_tool_result(tool_call, budget_stop),
                        state=state,
                        recorder=recorder,
                        messages=messages,
                    )
                    _record_interrupted_tool_calls(
                        tool_result_artifact_index=tool_context.tool_result_artifact_index if tool_context else None,
                        context_config=context_config_resolved,
                        run_id=run_id,
                        task_id=task_id,
                        turn=turn,
                        tool_calls=response.tool_calls[tool_index + 1 :],
                        reason=budget_stop,
                        state=state,
                        recorder=recorder,
                        messages=messages,
                        emit_tool_requested=True,
                    )
                    stop_after_tools = True
                    break
                if normalized_request.effective_tool_name == "run_tests":
                    if state.budget_state.test_run_count >= budget_manager.max_test_runs:
                        state.agent_stop_reason = "max_test_runs"
                        state.budget_state.stop_reason = "max_test_runs"
                        _record_tool_result(
                            tool_result_artifact_index=tool_context.tool_result_artifact_index if tool_context else None,
                            context_config=context_config_resolved,
                            run_id=run_id,
                            task_id=task_id,
                            turn=turn,
                            tool_result=_interrupted_tool_result(tool_call, "max_test_runs"),
                            state=state,
                            recorder=recorder,
                            messages=messages,
                        )
                        _record_interrupted_tool_calls(
                            tool_result_artifact_index=tool_context.tool_result_artifact_index if tool_context else None,
                            context_config=context_config_resolved,
                            run_id=run_id,
                            task_id=task_id,
                            turn=turn,
                            tool_calls=response.tool_calls[tool_index + 1 :],
                            reason="max_test_runs",
                            state=state,
                            recorder=recorder,
                            messages=messages,
                            emit_tool_requested=True,
                        )
                        stop_after_tools = True
                        break
                permission = self.tool_executor.check_permission(tool_call, tool_context)
                recorder.append_event(
                    TrajectoryEvent(
                        event_id=recorder.next_event_id("permission"),
                        timestamp=_timestamp(),
                        run_id=run_id,
                        task_id=task_id,
                        turn=turn,
                        event_type="permission_decision",
                        severity="warning" if permission.decision == "deny" else "info",
                        error_type="permission_denied" if permission.decision == "deny" else None,
                        data=permission.model_dump(mode="json"),
                    )
                )
                if permission.decision == "deny":
                    state.permission_denial_count += 1
                    state.permission_denial_reasons.append(permission.reason)
                    _record_tool_result(
                        tool_result_artifact_index=tool_context.tool_result_artifact_index if tool_context else None,
                        context_config=context_config_resolved,
                        run_id=run_id,
                        task_id=task_id,
                        turn=turn,
                        tool_result=self.tool_executor.denied_result(
                            tool_call,
                            permission,
                            tool_context,
                        ),
                        state=state,
                        recorder=recorder,
                        messages=messages,
                    )
                    continue
                tool_started = time.monotonic()
                tool_result = self.tool_executor.execute(tool_call, tool_context)
                tool_duration_ms = int((time.monotonic() - tool_started) * 1000)
                tool_result = _attach_tool_duration(tool_result, tool_duration_ms)
                _record_tool_result(
                    tool_result_artifact_index=tool_context.tool_result_artifact_index if tool_context else None,
                    context_config=context_config_resolved,
                    run_id=run_id,
                    task_id=task_id,
                    turn=turn,
                    tool_result=tool_result,
                    state=state,
                    recorder=recorder,
                    messages=messages,
                )
                if tool_result.status == "ok":
                    successful_tool_observation = True
                if (
                    tool_result.status == "ok"
                    and tool_result.effective_tool_name == "update_working_state"
                ):
                    working_state = tool_result.typed.get("working_state")
                    if isinstance(working_state, dict):
                        state.working_state = working_state
                if tool_result.effective_tool_name == "run_tests":
                    state.budget_state.test_run_count += 1
                    state.last_verifier_result = tool_result.typed.get("verifier_result_preview")
                    state.public_tests_ran = state.public_tests_ran or bool(
                        tool_result.typed.get("public_tests_ran")
                    )
                    state.hidden_feedback_ran = state.hidden_feedback_ran or bool(
                        tool_result.typed.get("hidden_feedback_ran")
                    )
                    if (
                        isinstance(state.last_verifier_result, dict)
                        and state.last_verifier_result.get("accepted") is True
                    ):
                        state.feedback_verifier_accepted = True
                        if state.first_feedback_accept_turn is None:
                            state.first_feedback_accept_turn = turn
                            state.first_feedback_accept_ref = tool_result.typed.get(
                                "verifier_result_ref"
                            )
                        if self.feedback_tests_passed_policy == "stop_immediately":
                            state.agent_stop_reason = "feedback_tests_passed"
                            state.budget_state.stop_reason = "feedback_tests_passed"
                            _record_interrupted_tool_calls(
                                tool_result_artifact_index=tool_context.tool_result_artifact_index if tool_context else None,
                                context_config=context_config_resolved,
                                run_id=run_id,
                                task_id=task_id,
                                turn=turn,
                                tool_calls=response.tool_calls[tool_index + 1 :],
                                reason="feedback_tests_passed",
                                state=state,
                                recorder=recorder,
                                messages=messages,
                                emit_tool_requested=True,
                            )
                            stop_after_tools = True
                            break
            loop_progress_summary = _build_loop_progress_summary(
                messages=messages,
                state=state,
                budget_manager=budget_manager,
            )
            nudge_dedupe_scope, _, new_signal_keys = _loop_progress_signal_dedupe(
                summary=loop_progress_summary,
                emitted_signal_keys=emitted_no_progress_signal_keys,
            )
            nudge_level = _convergence_nudge_level(loop_progress_summary)
            nudge_dedupe_scope = _convergence_nudge_dedupe_scope(
                level=nudge_level,
                base_scope=nudge_dedupe_scope,
            )
            should_inject_nudge = _should_inject_convergence_nudge(
                summary=loop_progress_summary,
                new_signal_keys=new_signal_keys,
                turn=turn,
                max_turns=budget_manager.max_turns,
                stop_after_tools=stop_after_tools,
                nudge_count=convergence_nudge_count,
                last_nudge_turn=last_convergence_nudge_turn_by_level.get(
                    nudge_level,
                    -CONVERGENCE_NUDGE_MIN_TURN_GAP,
                ),
                nudge_level=nudge_level,
                dedupe_scope=nudge_dedupe_scope,
                emitted_nudge_scopes=emitted_convergence_nudge_scopes,
            )
            diagnostic = _record_loop_progress_diagnostic(
                run_id=run_id,
                task_id=task_id,
                turn=turn,
                state=state,
                recorder=recorder,
                messages=messages,
                budget_manager=budget_manager,
                emitted_signal_keys=emitted_no_progress_signal_keys,
                summary=loop_progress_summary,
                dedupe_scope=nudge_dedupe_scope,
                new_signal_keys=new_signal_keys,
                model_visible_message_injected=should_inject_nudge,
            )
            if stop_after_tools:
                break
            if should_inject_nudge and diagnostic is not None:
                _record_convergence_nudge(
                    run_id=run_id,
                    task_id=task_id,
                    turn=turn,
                    state=state,
                    recorder=recorder,
                    messages=messages,
                    diagnostic=diagnostic,
                    nudge_count=convergence_nudge_count + 1,
                    max_nudges=CONVERGENCE_NUDGE_MAX_PER_RUN,
                    min_turn_gap=CONVERGENCE_NUDGE_MIN_TURN_GAP,
                    nudge_level=nudge_level,
                    dedupe_scope=nudge_dedupe_scope,
                )
                convergence_nudge_count += 1
                last_convergence_nudge_turn_by_level[nudge_level] = turn
                emitted_convergence_nudge_scopes.add(nudge_dedupe_scope)
            if _uses_phase_transitions(self.scaffold) and successful_tool_observation:
                next_phase, transition_reason = _next_phase_after_tools(
                    current_phase=current_phase,
                    state=state,
                    phase_start_test_run_count=phase_start_test_run_count,
                )
                if next_phase != current_phase:
                    _record_phase_transition(
                        run_id=run_id,
                        task_id=task_id,
                        turn=turn,
                        from_phase=current_phase,
                        to_phase=next_phase,
                        reason=transition_reason,
                        scaffold=self.scaffold,
                        state=state,
                        recorder=recorder,
                    )
        else:
            state.agent_stop_reason = "max_turns"
            state.budget_state.stop_reason = "max_turns"
        state.loop_diagnostics_summary = _build_loop_progress_summary(
            messages=messages,
            state=state,
            budget_manager=budget_manager,
        )
        state.messages = messages
        return state


def _handle_single_shot_patch_response(
    *,
    run_id: str,
    task_id: str,
    turn: int,
    content: str | None,
    tool_context: ToolExecutionContext,
    state: AgentLoopState,
    recorder: RunRecorder,
    messages: list[dict[str, object]],
) -> bool:
    parse = parse_patch_action(content)
    if parse.success:
        patch_ref = recorder.write_artifact(
            "single_shot_patch_action",
            parse.patch_text,
            {"suffix": ".patch", "budget_policy": "preserve_json"},
        )
        unsafe = _unsafe_patch_path(parse, tool_context)
        if unsafe is not None:
            failed = parse.model_copy(
                update={
                    "success": False,
                    "error_type": "unsafe_patch_path",
                    "message": unsafe,
                }
            )
            _record_patch_parse_failed(
                run_id=run_id,
                task_id=task_id,
                turn=turn,
                parse=failed,
                recorder=recorder,
                patch_ref=patch_ref,
            )
            _record_patch_action_transcript(
                run_id=run_id,
                task_id=task_id,
                turn=turn,
                content=f"single_shot_patch parse failed: {unsafe}",
                recorder=recorder,
                messages=messages,
                status="error",
                error_type="unsafe_patch_path",
            )
            state.last_model_error = "unsafe_patch_path"
            return False
        recorder.append_event(
            TrajectoryEvent(
                event_id=recorder.next_event_id("patch_action"),
                timestamp=_timestamp(),
                run_id=run_id,
                task_id=task_id,
                turn=turn,
                event_type="patch_action_parsed",
                artifact_refs=[patch_ref],
                data=_patch_parse_event_data(parse),
            )
        )
        recorder.append_event(
            TrajectoryEvent(
                event_id=recorder.next_event_id("patch_apply"),
                timestamp=_timestamp(),
                run_id=run_id,
                task_id=task_id,
                turn=turn,
                event_type="patch_apply_started",
                artifact_refs=[patch_ref],
                data={"changed_paths": parse.changed_paths},
            )
        )
        result = tool_context.workspace_adapter.apply_patch(
            tool_context.run_workspace.workspace_path,
            recorder.run_dir / patch_ref.relative_path,
            recorder=recorder,
        )
        apply_summary_ref = recorder.write_json_artifact(
            "single_shot_patch_apply_result",
            {
                "success": result.exit_code == 0 and not result.timeout,
                "patch_ref": patch_ref.model_dump(mode="json"),
                "changed_paths": parse.changed_paths,
                "execution_result": result.model_dump(mode="json"),
            },
        )
        event_type = (
            "patch_apply_completed"
            if result.exit_code == 0 and not result.timeout
            else "patch_apply_failed"
        )
        recorder.append_event(
            TrajectoryEvent(
                event_id=recorder.next_event_id("patch_apply"),
                timestamp=_timestamp(),
                run_id=run_id,
                task_id=task_id,
                turn=turn,
                event_type=event_type,
                severity="info" if event_type == "patch_apply_completed" else "error",
                error_type=None if event_type == "patch_apply_completed" else "patch_apply_failed",
                artifact_refs=[
                    ref
                    for ref in [patch_ref, result.output_artifact_ref, apply_summary_ref]
                    if ref is not None
                ],
                data={
                    "changed_paths": parse.changed_paths,
                    "exit_code": result.exit_code,
                    "timeout": result.timeout,
                    "apply_result_ref": apply_summary_ref.model_dump(mode="json"),
                },
            )
        )
        if result.exit_code != 0 or result.timeout:
            _record_patch_action_transcript(
                run_id=run_id,
                task_id=task_id,
                turn=turn,
                content=f"single_shot_patch apply failed: {result.stderr_preview or result.stdout_preview}",
                recorder=recorder,
                messages=messages,
                status="error",
                error_type="patch_apply_failed",
            )
            state.last_model_error = "patch_apply_failed"
            return False
        _record_patch_action_transcript(
            run_id=run_id,
            task_id=task_id,
            turn=turn,
            content=f"single_shot_patch applied successfully: {', '.join(parse.changed_paths)}",
            recorder=recorder,
            messages=messages,
            status="ok",
            error_type=None,
        )
        return True
    parse_ref = recorder.write_json_artifact(
        "single_shot_patch_parse_failed",
        parse.model_dump(mode="json"),
    )
    _record_patch_parse_failed(
        run_id=run_id,
        task_id=task_id,
        turn=turn,
        parse=parse,
        recorder=recorder,
        patch_ref=parse_ref,
    )
    _record_patch_action_transcript(
        run_id=run_id,
        task_id=task_id,
        turn=turn,
        content=f"single_shot_patch parse failed: {parse.error_type}",
        recorder=recorder,
        messages=messages,
        status="error",
        error_type=parse.error_type,
    )
    state.last_model_error = parse.error_type or "patch_action_parse_failed"
    return False


def _unsafe_patch_path(
    parse: PatchActionParseResult,
    tool_context: ToolExecutionContext,
) -> str | None:
    for changed_path in parse.changed_paths:
        try:
            tool_context.workspace_adapter.resolve_workspace_path(
                tool_context.run_workspace.workspace_path,
                changed_path,
            )
        except Exception as exc:  # noqa: BLE001 - path safety errors become structured patch failures
            return str(exc)
    return None


def _record_patch_parse_failed(
    *,
    run_id: str,
    task_id: str,
    turn: int,
    parse: PatchActionParseResult,
    recorder: RunRecorder,
    patch_ref: ArtifactRef,
) -> None:
    recorder.append_event(
        TrajectoryEvent(
            event_id=recorder.next_event_id("patch_action"),
            timestamp=_timestamp(),
            run_id=run_id,
            task_id=task_id,
            turn=turn,
            event_type="patch_action_parse_failed",
            severity="error",
            error_type=parse.error_type,
            artifact_refs=[patch_ref],
            data=_patch_parse_event_data(parse),
        )
    )


def _patch_parse_event_data(parse: PatchActionParseResult) -> dict[str, object]:
    return {
        "schema_version": parse.schema_version,
        "success": parse.success,
        "patch_sha256": parse.patch_sha256,
        "changed_paths": parse.changed_paths,
        "error_type": parse.error_type,
        "message": parse.message,
        "patch_text_artifact_only": bool(parse.patch_text),
    }


def _record_patch_action_transcript(
    *,
    run_id: str,
    task_id: str,
    turn: int,
    content: str,
    recorder: RunRecorder,
    messages: list[dict[str, object]],
    status: str,
    error_type: str | None,
) -> None:
    message_id = f"single_shot_patch_result_{turn}"
    recorder.append_transcript(
        TranscriptRecord(
            record_id=recorder.next_record_id(),
            run_id=run_id,
            task_id=task_id,
            message_id=message_id,
            turn=turn,
            role="tool",
            content_preview=content[:4000],
            model_visible=True,
            trainable=False,
            created_at=_timestamp(),
        )
    )
    messages.append(
        {
            "role": "tool",
            "turn": turn,
            "tool_name": "single_shot_patch",
            "content": content,
            "status": status,
            "error_type": error_type,
        }
    )


def _uses_phase_transitions(scaffold: ScaffoldDefinition) -> bool:
    return len(scaffold.phases()) > 1


def _scaffold_policy_snapshot(scaffold: ScaffoldDefinition) -> dict[str, object]:
    phases = scaffold.phases()
    return {
        "schema_version": "repo_harness_scaffold_policy_snapshot_v0",
        "scaffold_id": scaffold.scaffold_id,
        "scaffold_version": scaffold.scaffold_version,
        "allowed_tools_policy": scaffold.allowed_tools_policy,
        "phase_transition_policy": scaffold.phase_transition_policy,
        "default_stop_policy": scaffold.default_stop_policy,
        "initial_phase": scaffold.initial_phase,
        "phase_sequence": phases,
        "phase_allowed_tools": {
            phase: scaffold.allowed_tools_for_phase(phase) for phase in phases
        },
        "phase_prompt_fragments": {
            phase: scaffold.prompt_fragment_for_phase(phase) for phase in phases
        },
    }


def _allowed_tools_for_phase(
    *,
    scaffold: ScaffoldDefinition,
    phase: str,
    resolved_allowed_tool_names: list[str],
    test_feedback_policy: str,
) -> list[str]:
    allowed = [
        name
        for name in scaffold.allowed_tools_for_phase(phase)
        if name in resolved_allowed_tool_names
    ]
    if test_feedback_policy == "disabled":
        allowed = [name for name in allowed if name != "run_tests"]
    return allowed


def _messages_with_phase_metadata(
    *,
    messages: list[dict[str, object]],
    scaffold: ScaffoldDefinition,
    phase: str,
    allowed_tool_names: list[str],
) -> list[dict[str, object]]:
    if not _uses_phase_transitions(scaffold):
        return messages
    return [
        *messages,
        {
            "role": "user",
            "content": {
                "scaffold_phase": {
                    "phase": phase,
                    "allowed_tools": allowed_tool_names,
                    "instruction": scaffold.prompt_fragment_for_phase(phase),
                }
            },
        },
    ]


def _next_phase_after_assistant_message(current_phase: str) -> str:
    transitions = {
        "planner": "coder",
        "coder": "verifier",
        "verifier": "final",
        "repair": "verifier",
    }
    return transitions.get(current_phase, current_phase)


def _tool_call_parse_repair_message(response: object) -> dict[str, object]:
    metadata = getattr(getattr(response, "assistant_message", None), "metadata", {}) or {}
    provider_error_message = metadata.get("provider_error_message")
    if not isinstance(provider_error_message, str) or not provider_error_message:
        provider_error_message = "provider tool call payload could not be parsed"
    return {
        "role": "user",
        "content": (
            "上一轮 provider 返回的 tool call 结构不合法，RepoHarness 没有执行任何工具。"
            "\n错误类别：tool_call_parse_failure。"
            f"\n安全错误摘要：{provider_error_message[:400]}。"
            "\n请重新输出一个合法 tool call，或者在已经完成修复时输出 final answer。"
            "\n合法 tool call 必须包含唯一的 tool_call_id、function.name，"
            "并且 function.arguments 必须是 JSON object；不要返回半截 JSON、数组或字符串参数。"
        ),
        "metadata": {
            "repair_policy": "malformed_tool_call_repair_v0",
            "repair_attempt": 1,
            "max_attempts": 1,
        },
    }


def _context_warning_level(
    *,
    token_estimate: int,
    max_context_tokens: int,
    emitted_levels: set[str],
) -> str | None:
    if max_context_tokens <= 0:
        return None
    estimate = int(token_estimate)
    if estimate > max_context_tokens:
        return None
    ratio = estimate / max_context_tokens
    if ratio >= 0.9 and "critical_90" not in emitted_levels:
        return "critical_90"
    if ratio >= 0.8 and "warning_80" not in emitted_levels and "critical_90" not in emitted_levels:
        return "warning_80"
    return None


def _record_context_warning(
    *,
    run_id: str,
    task_id: str,
    turn: int,
    state: AgentLoopState,
    recorder: RunRecorder,
    messages: list[dict[str, object]],
    prepared: Any,
    provider_request_projection_estimate: dict[str, object],
    warning_level: str,
    max_context_tokens: int,
) -> None:
    estimate = int(
        provider_request_projection_estimate.get(
            "provider_request_token_estimate",
            getattr(prepared, "provider_ready_token_estimate", prepared.token_estimate),
        )
    )
    content = {
        "repo_harness_control_message": {
            "type": "context_warning",
            "policy_version": CONTEXT_WARNING_POLICY_VERSION,
            "trainable": False,
            "turn": turn,
            "warning_level": warning_level,
            "provider_ready_token_estimate": estimate,
            "provider_request_token_estimate": estimate,
            "provider_request_projection_hash": provider_request_projection_estimate.get(
                "provider_request_projection_hash"
            ),
            "max_context_tokens": max_context_tokens,
            "threshold_decision_source": "provider_request_projection_estimate",
            "instruction": (
                "当前对话已经接近上下文预算。请优先使用具体文件路径、最小必要读取范围和"
                "可验证的补丁行动，避免重复读取大段内容。"
            ),
            "input_scope_policy": (
                "This warning is generated only from the current model-visible transcript and public budget state."
            ),
        }
    }
    ref = recorder.write_json_artifact(
        "context_warning",
        {
            "schema_version": "repo_harness_context_warning_artifact_v0",
            "policy_version": CONTEXT_WARNING_POLICY_VERSION,
            "run_id": run_id,
            "task_id": task_id,
            "turn": turn,
            "trainable": False,
            "resolved_trainable": False,
            "message": content,
            "prepared_context_revision_before_warning": prepared.context_revision,
            "prepared_messages_ref_before_warning": prepared.prepared_messages_ref.model_dump(mode="json"),
            "provider_ready_token_estimate_before_warning": estimate,
            "provider_request_projection_estimate_before_warning": (
                provider_request_projection_estimate
            ),
            "provider_body_char_estimate_before_warning": prepared.provider_body_char_estimate,
            "internal_token_estimate_before_warning": prepared.internal_token_estimate,
            "max_context_tokens": max_context_tokens,
            "warning_level": warning_level,
        },
    )
    recorder.append_transcript(
        TranscriptRecord(
            record_id=recorder.next_record_id(),
            run_id=run_id,
            task_id=task_id,
            message_id=f"context_warning_{turn}_{warning_level}",
            turn=turn,
            role="user",
            content_preview=json.dumps(content, ensure_ascii=False)[:4000],
            content_artifact_refs=[ref],
            model_visible=True,
            trainable=False,
            created_at=_timestamp(),
        )
    )
    messages.append(
        {
            "role": "user",
            "turn": turn,
            "content": content,
            "metadata": {
                "source": "harness_context_warning",
                "policy_version": CONTEXT_WARNING_POLICY_VERSION,
                "trainable": False,
                "resolved_trainable": False,
            },
        }
    )
    recorder.append_event(
        TrajectoryEvent(
            event_id=recorder.next_event_id("context_warning"),
            timestamp=_timestamp(),
            run_id=run_id,
            task_id=task_id,
            turn=turn,
            event_type="context_warning_injected",
            severity="warning",
            artifact_refs=[ref],
            data={
                "schema_version": "repo_harness_context_warning_event_v0",
                "policy_version": CONTEXT_WARNING_POLICY_VERSION,
                "trainable": False,
                "resolved_trainable": False,
                "model_visible": True,
                "warning_level": warning_level,
                "provider_ready_token_estimate": estimate,
                "provider_body_char_estimate": prepared.provider_body_char_estimate,
                "internal_token_estimate": prepared.internal_token_estimate,
                "max_context_tokens": max_context_tokens,
                "inserted_after_prepare_messages": True,
                "requires_prepare_messages_rerun": True,
                "provider_request_created_before_warning": False,
            },
        )
    )
    state.loop_diagnostics_summary = {
        **state.loop_diagnostics_summary,
        "context_warning_level": warning_level,
        "context_warning_turn": turn,
    }


def _write_context_policy_snapshot_artifact(recorder: RunRecorder) -> ArtifactRef | None:
    run_config_path = recorder.run_dir / "run_config_facts.json"
    if not run_config_path.exists():
        return None
    try:
        run_config = json.loads(run_config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    snapshot = run_config.get("context_policy_snapshot")
    if not isinstance(snapshot, dict):
        return None
    return recorder.write_json_artifact(
        "context_policy_snapshot",
        snapshot,
        {
            "redaction_status": "not_sensitive",
            "retention_policy": "context_policy_snapshot",
            "budget_policy": "preserve_json",
        },
    )


def _truncate_head_for_ptl_retry(
    *,
    messages: list[dict[str, object]],
    recorder: RunRecorder,
    run_id: str,
    task_id: str,
    turn: int,
    ordinary_turn: int,
    context_config: ContextManagementConfig,
    provider_options: ModelProviderOptions,
    allowed_tool_definitions: list[dict[str, object]],
    generation_config: dict[str, object],
    provider_model_settings: dict[str, object],
    context_budget_facts: Any,
    hard_context_limit_tokens: int,
    original_model_call_id: str,
    original_prepared_messages_ref: ArtifactRef,
    original_model_input_hash: str,
    original_provider_request_ref: ArtifactRef | None,
    original_provider_response_ref: ArtifactRef | None,
    emergency_compact_record_ref: ArtifactRef | None,
    emergency_compact_failure_reason: str | None,
) -> dict[str, Any]:
    if context_config.ptl_retry_policy not in {
        "auto_compact_then_round_truncate",
        "round_truncate",
    }:
        return {
            "status": "failed",
            "failure_reason": "ptl_retry_policy_disabled",
        }
    prefix_count = _ptl_protected_prefix_count(messages)
    groups = _ptl_round_groups(messages, start_index=prefix_count)
    protected_group_ids = {
        group["group_id"]
        for group in groups
        if any(_message_has_compact_summary(messages[index]) for index in group["indices"])
    }
    droppable_groups = [
        group
        for group in groups
        if group["group_id"] not in protected_group_ids
    ]
    keep_recent_groups = 2
    if len(droppable_groups) > keep_recent_groups:
        droppable_groups = droppable_groups[:-keep_recent_groups]
    elif len(droppable_groups) > 1:
        droppable_groups = droppable_groups[:-1]
    else:
        droppable_groups = []
    if not droppable_groups:
        return {
            "status": "failed",
            "failure_reason": "ptl_no_complete_round_available_to_drop",
        }

    token_estimate_before = _ptl_provider_token_estimate(
        messages=messages,
        provider_options=provider_options,
        allowed_tool_definitions=allowed_tool_definitions,
        generation_config=generation_config,
        provider_model_settings=provider_model_settings,
        context_budget_facts=context_budget_facts,
    )
    selected_messages: list[dict[str, object]] | None = None
    selected_dropped_groups: list[dict[str, Any]] = []
    selected_token_estimate_after = token_estimate_before
    for drop_count in range(1, len(droppable_groups) + 1):
        dropped_groups = droppable_groups[:drop_count]
        dropped_ids = {group["group_id"] for group in dropped_groups}
        candidate_messages = _ptl_messages_after_drop(
            messages=messages,
            prefix_count=prefix_count,
            groups=groups,
            dropped_group_ids=dropped_ids,
            original_model_call_id=original_model_call_id,
            omitted_round_count=len(dropped_groups),
        )
        token_estimate_after = _ptl_provider_token_estimate(
            messages=candidate_messages,
            provider_options=provider_options,
            allowed_tool_definitions=allowed_tool_definitions,
            generation_config=generation_config,
            provider_model_settings=provider_model_settings,
            context_budget_facts=context_budget_facts,
        )
        selected_messages = candidate_messages
        selected_dropped_groups = dropped_groups
        selected_token_estimate_after = token_estimate_after
        if token_estimate_after <= hard_context_limit_tokens:
            break
    if selected_messages is None or selected_token_estimate_after >= token_estimate_before:
        return {
            "status": "failed",
            "failure_reason": "ptl_truncation_did_not_reduce_projection",
        }

    synthetic_marker = selected_messages[prefix_count]
    synthetic_marker_id = str(
        (synthetic_marker.get("metadata") or {}).get("synthetic_marker_id")
        if isinstance(synthetic_marker.get("metadata"), dict)
        else ""
    )
    omitted_rounds = [
        _ptl_round_record(group, messages=messages)
        for group in selected_dropped_groups
    ]
    retained_rounds = [
        _ptl_round_record(group, messages=messages)
        for group in groups
        if group not in selected_dropped_groups
    ]
    record_payload = {
        "schema_version": "repo_harness_ptl_truncation_record_v1",
        "policy": context_config.ptl_retry_policy,
        "reason": "provider_context_limit_retry",
        "original_model_call_id": original_model_call_id,
        "original_prepared_messages_ref": original_prepared_messages_ref.model_dump(
            mode="json"
        ),
        "original_model_input_hash": original_model_input_hash,
        "original_provider_request_ref": (
            original_provider_request_ref.model_dump(mode="json")
            if original_provider_request_ref
            else None
        ),
        "original_provider_response_ref": (
            original_provider_response_ref.model_dump(mode="json")
            if original_provider_response_ref
            else None
        ),
        "emergency_compact_record_ref": (
            emergency_compact_record_ref.model_dump(mode="json")
            if emergency_compact_record_ref
            else None
        ),
        "emergency_compact_failure_reason": emergency_compact_failure_reason,
        "ordinary_turn": ordinary_turn,
        "loop_turn": turn,
        "synthetic_marker_id": synthetic_marker_id,
        "synthetic_marker_message": synthetic_marker,
        "omitted_rounds": omitted_rounds,
        "retained_rounds": retained_rounds,
        "omitted_round_count": len(omitted_rounds),
        "retained_round_count": len(retained_rounds),
        "message_count_before": len(messages),
        "message_count_after": len(selected_messages),
        "token_estimate_before": token_estimate_before,
        "token_estimate_after": selected_token_estimate_after,
        "hard_context_limit_tokens": hard_context_limit_tokens,
        "post_truncation_above_hard_limit": (
            selected_token_estimate_after > hard_context_limit_tokens
        ),
        "tool_pairing_preservation_policy": "drop_complete_rounds_only_v1",
        "trainable": False,
    }
    ref = recorder.write_json_artifact(
        "ptl_truncation_record",
        record_payload,
        {
            "redaction_status": "not_sensitive",
            "retention_policy": "context_compaction_audit",
            "budget_policy": "preserve_json",
        },
    )
    return {
        "status": "applied",
        "messages": selected_messages,
        "ptl_truncation_ref": ref,
        "omitted_round_count": len(omitted_rounds),
        "synthetic_marker_id": synthetic_marker_id,
        "token_estimate_before": token_estimate_before,
        "token_estimate_after": selected_token_estimate_after,
        "post_truncation_above_hard_limit": (
            selected_token_estimate_after > hard_context_limit_tokens
        ),
    }


def _ptl_protected_prefix_count(messages: list[dict[str, object]]) -> int:
    index = 0
    while index < len(messages) and messages[index].get("role") == "system":
        index += 1
    if index < len(messages) and messages[index].get("role") == "user":
        index += 1
    return index


def _ptl_round_groups(
    messages: list[dict[str, object]],
    *,
    start_index: int,
) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    index = start_index
    group_id = 0
    while index < len(messages):
        start = index
        role = messages[index].get("role")
        if role == "user":
            index += 1
            while index < len(messages) and messages[index].get("role") not in {
                "user",
                "system",
            }:
                index += 1
        elif role == "assistant":
            index += 1
            while index < len(messages) and messages[index].get("role") == "tool":
                index += 1
        else:
            index += 1
        indices = list(range(start, index))
        groups.append(
            {
                "group_id": f"round_{group_id:04d}",
                "start_index": start,
                "end_index_exclusive": index,
                "indices": indices,
            }
        )
        group_id += 1
    return groups


def _ptl_messages_after_drop(
    *,
    messages: list[dict[str, object]],
    prefix_count: int,
    groups: list[dict[str, Any]],
    dropped_group_ids: set[str],
    original_model_call_id: str,
    omitted_round_count: int,
) -> list[dict[str, object]]:
    dropped_indices = {
        index
        for group in groups
        if group["group_id"] in dropped_group_ids
        for index in group["indices"]
    }
    marker_id = f"ptl_marker_{stable_hash({'model_call_id': original_model_call_id, 'omitted': sorted(dropped_group_ids)})[:12]}"
    marker = {
        "role": "user",
        "content": {
            "repo_harness_ptl_truncation_marker": {
                "policy_version": "repo_harness_ptl_round_truncate_v1",
                "reason": "provider_context_limit_retry",
                "original_model_call_id": original_model_call_id,
                "omitted_round_count": omitted_round_count,
                "instruction": (
                    "Earlier conversation rounds were omitted because the provider "
                    "rejected the previous request as too long. Continue using the "
                    "visible task, any visible compact summary, and the remaining "
                    "recent context. Do not infer facts from omitted rounds."
                ),
            }
        },
        "metadata": {
            "synthetic": True,
            "synthetic_marker_id": marker_id,
            "model_visible": True,
            "trainable": False,
        },
    }
    kept = [
        dict(message)
        for index, message in enumerate(messages)
        if index not in dropped_indices
    ]
    return [*kept[:prefix_count], marker, *kept[prefix_count:]]


def _ptl_round_record(
    group: dict[str, Any],
    *,
    messages: list[dict[str, object]],
) -> dict[str, Any]:
    group_messages = [messages[index] for index in group["indices"]]
    return {
        "group_id": group["group_id"],
        "start_index": group["start_index"],
        "end_index_exclusive": group["end_index_exclusive"],
        "message_count": len(group_messages),
        "roles": [message.get("role") for message in group_messages],
        "message_hash": stable_hash(group_messages),
        "char_estimate": len(json.dumps(group_messages, ensure_ascii=False, sort_keys=True)),
        "token_estimate": max(
            1,
            len(json.dumps(group_messages, ensure_ascii=False, sort_keys=True)) // 4,
        ),
        "tool_call_ids": _tool_call_ids_in_messages(group_messages),
        "tool_result_ids": [
            str(message.get("tool_result_id") or "")
            for message in group_messages
            if message.get("role") == "tool" and message.get("tool_result_id")
        ],
    }


def _tool_call_ids_in_messages(messages: list[dict[str, object]]) -> list[str]:
    ids: list[str] = []
    for message in messages:
        for call in message.get("tool_calls") or []:
            if isinstance(call, dict) and call.get("tool_call_id"):
                ids.append(str(call["tool_call_id"]))
        if message.get("role") == "tool" and message.get("tool_call_id"):
            ids.append(str(message["tool_call_id"]))
    return sorted(set(ids))


def _message_has_compact_summary(message: dict[str, object]) -> bool:
    return "repo_harness_auto_compact_summary" in json.dumps(
        message,
        ensure_ascii=False,
        sort_keys=True,
    )


def _ptl_provider_token_estimate(
    *,
    messages: list[dict[str, object]],
    provider_options: ModelProviderOptions,
    allowed_tool_definitions: list[dict[str, object]],
    generation_config: dict[str, object],
    provider_model_settings: dict[str, object],
    context_budget_facts: Any,
) -> int:
    estimate = _build_provider_request_projection_estimate(
        prepared_messages=messages,
        provider_options=provider_options,
        allowed_tool_definitions=allowed_tool_definitions,
        generation_config=generation_config,
        provider_model_settings=provider_model_settings,
        provider_message_format=f"repo_harness_{provider_options.provider}_messages_v0",
        context_budget_facts=context_budget_facts,
    )
    return estimate.provider_request_token_estimate


def _synthetic_model_call_event(
    *,
    request: ModelRequestContext,
    response: ModelResponse,
    terminal_error_type: str | None,
) -> ModelCallEvent:
    usage = getattr(response, "token_usage", None) or {}
    return ModelCallEvent(
        model_call_id=request.model_call_id,
        provider=request.provider_options.provider,
        model_id=request.provider_options.model_id,
        provider_request_id=getattr(response, "provider_request_id", None),
        context_revision=request.context_revision,
        prepared_messages_ref=request.prepared_messages_ref,
        model_input_hash=request.model_input_hash,
        provider_message_format=request.provider_message_format,
        tool_schema_hash=stable_hash(request.allowed_tool_definitions),
        input_tokens=int(usage.get("input_tokens") or usage.get("prompt_tokens") or 0),
        output_tokens=int(usage.get("output_tokens") or usage.get("completion_tokens") or 0),
        cached_tokens=int(usage.get("cached_tokens") or 0),
        duration_ms=0,
        request_timeout_seconds=request.request_timeout_seconds,
        request_timeout_policy_facts=request.request_timeout_policy_facts,
        attempt_count=int(getattr(response, "attempt_count", 1) or 1),
        retry_count=int(getattr(response, "retry_count", 0) or 0),
        terminal_error_type=terminal_error_type,
        retry_policy_ref=getattr(response, "retry_policy_ref", None),
        model_error_type=getattr(response, "model_error_type", None),
    )


def _write_budget_decision_trace_artifact(
    *,
    recorder: RunRecorder,
    run_id: str,
    task_id: str,
    turn: int,
    budget_manager: BudgetManager,
    state: AgentLoopState,
    response: ModelResponse,
    model_call_event: ModelCallEvent | None = None,
) -> ArtifactRef:
    usage = getattr(response, "token_usage", None) or {}
    event = model_call_event or response.model_call_event
    input_tokens = int(usage.get("input_tokens", event.input_tokens if event else 0))
    output_tokens = int(usage.get("output_tokens", event.output_tokens if event else 0))
    cached_tokens = int(usage.get("cached_tokens", event.cached_tokens if event else 0))
    max_cost_enforcement = "unavailable" if budget_manager.max_cost is not None else "disabled"
    payload = {
        "schema_version": "repo_harness_budget_decision_trace_v0",
        "run_id": run_id,
        "task_id": task_id,
        "turn": turn,
        "model_call_id": event.model_call_id if event else None,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cached_tokens": cached_tokens,
        "token_source": "provider_usage_metadata_or_estimator",
        "cost_source": "provider_usage_metadata_missing",
        "cost_available": False,
        "estimated_cost": None,
        "max_cost_enforcement": max_cost_enforcement,
        "remaining_turn_budget": max(0, budget_manager.max_turns - turn),
        "remaining_tool_call_budget": max(0, budget_manager.max_tool_calls - state.tool_call_count),
        "remaining_test_run_budget": max(0, budget_manager.max_test_runs - state.budget_state.test_run_count),
        "decision": "continue_or_terminal_by_agent_loop",
        "decision_reason": (
            "Token usage was recorded for audit. Provider did not return trusted cost, "
            f"so cost_available=false and max_cost_enforcement={max_cost_enforcement}."
        ),
        "agent_stop_reason_at_record_time": state.agent_stop_reason,
        "model_error_type": response.model_error_type,
    }
    return recorder.write_json_artifact(
        "budget_decision_trace",
        payload,
        {
            "redaction_status": "not_sensitive",
            "retention_policy": "keep",
            "budget_policy": "preserve_json",
        },
    )


def _next_phase_after_tools(
    *,
    current_phase: str,
    state: AgentLoopState,
    phase_start_test_run_count: int,
) -> tuple[str, str]:
    if current_phase == "planner":
        return "coder", "planner_phase_completed"
    if current_phase == "coder":
        return "verifier", "coder_phase_completed"
    if current_phase == "verifier":
        if state.feedback_verifier_accepted:
            return "final", "feedback_verifier_accepted"
        if state.budget_state.test_run_count > phase_start_test_run_count:
            return "repair", "feedback_verifier_not_accepted"
        return "final", "verifier_phase_completed_without_test_feedback"
    if current_phase == "repair":
        return "verifier", "repair_phase_completed"
    return current_phase, "phase_unchanged"


def _record_phase_transition(
    *,
    run_id: str,
    task_id: str,
    turn: int,
    from_phase: str,
    to_phase: str,
    reason: str,
    scaffold: ScaffoldDefinition,
    state: AgentLoopState,
    recorder: RunRecorder,
) -> None:
    if from_phase == to_phase:
        return
    record = {
        "schema_version": "repo_harness_scaffold_phase_transition_v0",
        "scaffold_id": scaffold.scaffold_id,
        "scaffold_version": scaffold.scaffold_version,
        "phase_transition_policy": scaffold.phase_transition_policy,
        "scaffold_policy_snapshot": _scaffold_policy_snapshot(scaffold),
        "from_phase": from_phase,
        "to_phase": to_phase,
        "reason": reason,
        "turn": turn,
        "phase_sequence": scaffold.phases(),
    }
    state.current_phase = to_phase
    state.phase_history.append(record)
    recorder.append_event(
        TrajectoryEvent(
            event_id=recorder.next_event_id("phase"),
            timestamp=_timestamp(),
            run_id=run_id,
            task_id=task_id,
            turn=turn,
            event_type="scaffold_phase_transition",
            data=record,
        )
    )


def _build_model_request_context(
    *,
    run_id: str,
    task_id: str,
    turn: int,
    prepared_messages: list[dict[str, object]],
    prepared_messages_ref: ArtifactRef,
    model_input_hash: str,
    context_revision: int,
    provider_options: ModelProviderOptions,
    scaffold: ScaffoldDefinition,
    scaffold_phase: str,
    allowed_tool_definitions: list[dict[str, object]],
    tool_schema_snapshot_ref: ArtifactRef,
    run_config_facts_ref: RunConfigFactsRef,
    budget_state: dict[str, object],
    generation_config: dict[str, object],
    provider_model_settings: dict[str, object],
    request_timeout_seconds: float,
    request_timeout_policy_facts: dict[str, object],
    raw_request_logging_policy: str,
    retry_policy: str,
    provider_request_projection_hash: str | None,
    provider_request_token_estimate: int,
    provider_request_token_estimate_breakdown: dict[str, object],
    context_budget_facts: dict[str, object],
) -> ModelRequestContext:
    return ModelRequestContext(
        run_id=run_id,
        task_id=task_id,
        turn=turn,
        model_call_id=f"{run_id}_model_call_{turn:04d}",
        prepared_messages=prepared_messages,
        prepared_messages_ref=prepared_messages_ref,
        model_input_hash=model_input_hash,
        context_revision=context_revision,
        provider_message_format=f"repo_harness_{provider_options.provider}_messages_v0",
        context_truncation_facts={},
        omitted_context_facts={},
        generation_config=generation_config,
        provider_model_settings=provider_model_settings,
        allowed_tool_definitions=allowed_tool_definitions,
        tool_schema_snapshot_ref=tool_schema_snapshot_ref,
        provider_options=provider_options,
        scaffold_id=scaffold.scaffold_id,
        scaffold_phase=scaffold_phase,
        run_config_facts_ref=run_config_facts_ref,
        budget_state=budget_state,
        request_timeout_seconds=request_timeout_seconds,
        request_timeout_policy_facts=request_timeout_policy_facts,
        raw_request_logging_policy=raw_request_logging_policy,
        credential_policy=provider_options.credential_policy,
        retry_policy=retry_policy,
        provider_request_projection_hash=provider_request_projection_hash,
        provider_request_token_estimate=provider_request_token_estimate,
        provider_request_token_estimate_breakdown=provider_request_token_estimate_breakdown,
        context_budget_facts=context_budget_facts,
    )


def _build_provider_request_projection_estimate(
    *,
    prepared_messages: list[dict[str, object]],
    provider_options: ModelProviderOptions,
    allowed_tool_definitions: list[dict[str, object]],
    generation_config: dict[str, object],
    provider_model_settings: dict[str, object],
    provider_message_format: str,
    context_budget_facts: Any,
):
    projection = build_provider_request_projection(
        provider=provider_options.provider,
        model_id=provider_options.model_id,
        provider_message_format=provider_message_format,
        messages=[dict(message) for message in prepared_messages],
        tools=[dict(tool) for tool in allowed_tool_definitions],
        tool_choice=None,
        generation_config=dict(generation_config),
        provider_model_settings=dict(provider_model_settings),
    )
    return estimate_provider_request_projection(
        projection=projection,
        budget_facts=context_budget_facts,
    )


def _tool_definitions_for_allowed_tools(
    executor: ToolExecutor,
    allowed_tool_names: list[str],
) -> list[dict[str, object]]:
    definitions: list[dict[str, object]] = []
    for name in allowed_tool_names:
        if not executor.is_known(name):
            continue
        definition: ToolDefinition = executor.registry.get(name)
        definitions.append(
            {
                "name": definition.name,
                "tool_version": definition.tool_version,
                "description": definition.model_visible_description,
                "model_visible_prompt": definition.model_visible_prompt,
                "input_schema": definition.input_schema,
                "output_schema": definition.output_schema,
                "read_only": definition.is_read_only,
                "destructive": definition.is_destructive,
            }
        )
    return definitions


def _placeholder_artifact_ref(kind: str) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=f"{kind}_unavailable",
        relative_path=f"artifacts/{kind}_unavailable.json",
        kind=kind,
        sha256="0" * 64,
        size_bytes=0,
    )


def _record_loop_progress_diagnostic(
    *,
    run_id: str,
    task_id: str,
    turn: int,
    state: AgentLoopState,
    recorder: RunRecorder,
    messages: list[dict[str, object]],
    budget_manager: BudgetManager,
    emitted_signal_keys: set[str],
    summary: dict[str, Any] | None = None,
    dedupe_scope: str | None = None,
    new_signal_keys: list[str] | None = None,
    model_visible_message_injected: bool = False,
) -> dict[str, Any] | None:
    summary = summary or _build_loop_progress_summary(
        messages=messages,
        state=state,
        budget_manager=budget_manager,
    )
    state.loop_diagnostics_summary = summary
    dedupe_scope, signal_dedupe_keys, computed_new_signal_keys = _loop_progress_signal_dedupe(
        summary=summary,
        emitted_signal_keys=emitted_signal_keys,
    )
    new_signal_keys = computed_new_signal_keys if new_signal_keys is None else new_signal_keys
    if not new_signal_keys:
        return None
    emitted_signal_keys.update(signal_dedupe_keys[signal_key] for signal_key in new_signal_keys)
    diagnostic = {
        **summary,
        "diagnostic_dedupe_scope": dedupe_scope,
        "new_signal_keys": new_signal_keys,
        "agent_stop_reason_before_event": state.agent_stop_reason,
        "agent_stop_reason_changed": False,
        "model_visible_message_injected": model_visible_message_injected,
    }
    state.loop_diagnostics.append(diagnostic)
    recorder.append_event(
        TrajectoryEvent(
            event_id=recorder.next_event_id("loop_progress"),
            timestamp=_timestamp(),
            run_id=run_id,
            task_id=task_id,
            turn=turn,
            event_type="loop_progress_diagnostic",
            severity="warning",
            error_type="no_progress_suspected",
            data=diagnostic,
        )
    )
    return diagnostic


def _loop_progress_signal_dedupe(
    *,
    summary: dict[str, Any],
    emitted_signal_keys: set[str],
) -> tuple[str, dict[str, str], list[str]]:
    signal_keys = [str(signal["signal_key"]) for signal in summary["signals"]]
    dedupe_scope = str(summary.get("last_patch_progress_tool_result_id") or "run_start")
    signal_dedupe_keys = {
        signal_key: f"{dedupe_scope}:{signal_key}"
        for signal_key in signal_keys
    }
    new_signal_keys = [
        signal_key
        for signal_key in signal_keys
        if signal_dedupe_keys[signal_key] not in emitted_signal_keys
    ]
    return dedupe_scope, signal_dedupe_keys, new_signal_keys


def _should_inject_convergence_nudge(
    *,
    summary: dict[str, Any],
    new_signal_keys: list[str],
    turn: int,
    max_turns: int,
    stop_after_tools: bool,
    nudge_count: int,
    last_nudge_turn: int,
    nudge_level: str,
    dedupe_scope: str,
    emitted_nudge_scopes: set[str],
) -> bool:
    if stop_after_tools or not new_signal_keys:
        return False
    if turn >= max_turns:
        return False
    if nudge_count >= CONVERGENCE_NUDGE_MAX_PER_RUN:
        return False
    if turn - last_nudge_turn < CONVERGENCE_NUDGE_MIN_TURN_GAP:
        return False
    if dedupe_scope in emitted_nudge_scopes:
        return False
    if summary.get("diagnostic_status") != "no_progress_suspected":
        return False
    if nudge_level == "none":
        return False
    if int(summary.get("patch_tool_call_count") or 0) > 0 and not summary.get(
        "analysis_window_started_after_patch_tool_call"
    ):
        return False
    return True


def _convergence_nudge_level(summary: dict[str, Any]) -> str:
    signal_keys = {str(signal.get("signal_key")) for signal in summary.get("signals", [])}
    if "near_turn_budget_with_patch" in signal_keys:
        return "near_budget_finalize_patch"
    if "near_turn_budget_without_patch" in signal_keys:
        return "near_budget_patch_or_stop"
    if signal_keys:
        return "exploration_no_progress"
    return "none"


def _convergence_nudge_dedupe_scope(*, level: str, base_scope: str) -> str:
    return f"{level}:{base_scope}"


def _record_convergence_nudge(
    *,
    run_id: str,
    task_id: str,
    turn: int,
    state: AgentLoopState,
    recorder: RunRecorder,
    messages: list[dict[str, object]],
    diagnostic: dict[str, Any],
    nudge_count: int,
    max_nudges: int,
    min_turn_gap: int,
    nudge_level: str,
    dedupe_scope: str,
) -> None:
    signal_keys = [str(signal_key) for signal_key in diagnostic.get("new_signal_keys", [])]
    nudge_reason, instruction = _convergence_nudge_text(nudge_level)
    next_action_constraint = _convergence_nudge_next_action_constraint(nudge_level)
    summary = diagnostic
    content = {
        "repo_harness_control_message": {
            "type": "convergence_nudge",
            "policy_version": CONVERGENCE_NUDGE_POLICY_VERSION,
            "trainable": False,
            "turn": turn,
            "nudge_level": nudge_level,
            "reason": nudge_reason,
            "signals": signal_keys,
            "instruction": instruction,
            "next_action_constraint": next_action_constraint,
            "input_scope_policy": (
                "This reminder is generated only from the current model-visible transcript and public budget state."
            ),
            "turns_remaining": summary.get("remaining_turns"),
            "has_patch": bool(summary.get("patch_tool_call_count")),
            "first_edit_turn": summary.get("first_patch_progress_turn"),
            "last_mutating_tool_turn": summary.get("last_patch_progress_turn"),
            "git_diff_called_after_patch": summary.get("git_diff_called_after_patch"),
            "nudge_count": nudge_count,
            "max_nudges_per_run": max_nudges,
            "min_turn_gap": min_turn_gap,
            "dedupe_scope": dedupe_scope,
        }
    }
    ref = recorder.write_json_artifact(
        "convergence_nudge",
        {
            "schema_version": "repo_harness_convergence_nudge_artifact_v0",
            "policy_version": CONVERGENCE_NUDGE_POLICY_VERSION,
            "run_id": run_id,
            "task_id": task_id,
            "turn": turn,
            "trainable": False,
            "message": content,
            "diagnostic": diagnostic,
            "dedupe_scope": dedupe_scope,
            "nudge_level": nudge_level,
            "nudge_reason": nudge_reason,
            "nudge_count": nudge_count,
            "max_nudges_per_run": max_nudges,
            "min_turn_gap": min_turn_gap,
            "next_action_constraint": next_action_constraint,
            "resolved_trainable": False,
        },
    )
    recorder.append_transcript(
        TranscriptRecord(
            record_id=recorder.next_record_id(),
            run_id=run_id,
            task_id=task_id,
            message_id=f"convergence_nudge_{turn}_{nudge_count}",
            turn=turn,
            role="user",
            content_preview=json.dumps(content, ensure_ascii=False)[:4000],
            content_artifact_refs=[ref],
            model_visible=True,
            trainable=False,
            created_at=_timestamp(),
        )
    )
    messages.append(
        {
            "role": "user",
            "turn": turn,
            "content": content,
            "metadata": {
                "source": "harness_convergence_nudge",
                "policy_version": CONVERGENCE_NUDGE_POLICY_VERSION,
                "trainable": False,
                "resolved_trainable": False,
                "dedupe_scope": dedupe_scope,
                "nudge_level": nudge_level,
            },
        }
    )
    recorder.append_event(
        TrajectoryEvent(
            event_id=recorder.next_event_id("convergence"),
            timestamp=_timestamp(),
            run_id=run_id,
            task_id=task_id,
            turn=turn,
            event_type="convergence_nudge_injected",
            severity="warning",
            artifact_refs=[ref],
            data={
                "schema_version": "repo_harness_convergence_nudge_event_v0",
                "policy_version": CONVERGENCE_NUDGE_POLICY_VERSION,
                "trainable": False,
                "resolved_trainable": False,
                "model_visible": True,
                "inserted_after_all_tool_results": True,
                "inserted_before_next_prepare_messages": True,
                "max_nudges_per_run": max_nudges,
                "min_turn_gap": min_turn_gap,
                "nudge_level": nudge_level,
                "nudge_reason": nudge_reason,
                "turns_remaining": summary.get("remaining_turns"),
                "has_patch": bool(summary.get("patch_tool_call_count")),
                "first_edit_turn": summary.get("first_patch_progress_turn"),
                "last_mutating_tool_turn": summary.get("last_patch_progress_turn"),
                "git_diff_called_after_patch": summary.get("git_diff_called_after_patch"),
                "post_nudge_action": "pending_observation",
                "next_action_constraint": next_action_constraint,
                "nudge_count": nudge_count,
                "dedupe_scope": dedupe_scope,
                "signal_keys": signal_keys,
            },
        )
    )
    state.loop_diagnostics_summary = {
        **state.loop_diagnostics_summary,
        "convergence_nudge_count": nudge_count,
        "last_convergence_nudge_turn": turn,
        "last_convergence_nudge_level": nudge_level,
    }


def _convergence_nudge_text(level: str) -> tuple[str, str]:
    if level == "near_budget_patch_or_stop":
        return (
            "剩余工具轮数已经很少，并且当前还没有补丁，需要立即选择一个可完成路径。",
            (
                "请停止大范围探索。下一次 assistant action 必须只选择一个可完成路径："
                "如果已经知道最小安全修改，请调用 edit_file；如果只缺少 edit_file.old_text，"
                "最多调用一次带精确 path 和行号范围的 read_file，然后立即编辑；"
                "如果已经有补丁，请调用 git_diff；如果仍然无法定位安全修改，"
                "请直接给出 final answer，明确说明未提交补丁。不要再做宽泛 grep、list_files、symbol_search 或等价重复搜索。"
            ),
        )
    if level == "near_budget_finalize_patch":
        return (
            "当前已经存在补丁且剩余工具轮数很少，需要收尾而不是继续大范围探索。",
            (
                "请调用 git_diff 检查真实补丁，只做必要的小范围修正，然后给出 final answer。"
                "如果补丁已经足够，请不要继续等价搜索。"
            ),
        )
    return (
        "多轮只读探索已经触发收敛诊断，需要把下一步收束到可验证的最小行动。",
        (
            "请先用一句话写出当前最可能的定位假设，然后选择一个最小下一步："
            "读取一个具体文件、编辑一个具体文件，或者在已经完成时给出 final answer。"
            "如果当前假设和候选文件已经形成，请先用 update_working_state 简短记录。"
            "不要重复等价搜索；如果搜索结果是 partial_scan_no_match，先收窄 root 或 glob。"
        ),
    )


def _convergence_nudge_next_action_constraint(level: str) -> dict[str, Any]:
    if level == "near_budget_patch_or_stop":
        return {
            "constraint_kind": "patch_or_stop",
            "required_behavior": (
                "The next assistant action must be one of the listed allowed paths; broad exploration is no longer useful."
            ),
            "allowed_next_actions": [
                "edit_file when the minimal safe change is known",
                "read_file exactly once with a precise path and line range when old_text is the only missing input",
                "git_diff only if a patch was just created",
                "final_answer explaining that no safe patch was submitted",
            ],
            "disallowed_next_actions": [
                "broad grep",
                "broad list_files",
                "broad symbol_search",
                "repeating equivalent searches",
                "reading multiple files without a concrete patch plan",
            ],
            "max_additional_read_file_calls_before_patch": 1,
        }
    if level == "near_budget_finalize_patch":
        return {
            "constraint_kind": "finalize_existing_patch",
            "required_behavior": (
                "The next assistant actions should verify and finish the existing patch rather than restart exploration."
            ),
            "allowed_next_actions": [
                "git_diff",
                "edit_file only for a small necessary correction",
                "final_answer when the diff is sufficient",
            ],
            "disallowed_next_actions": [
                "broad repository search",
                "unrelated file reads",
                "starting a new hypothesis without checking the current diff",
            ],
            "max_additional_read_file_calls_before_patch": 0,
        }
    return {
        "constraint_kind": "minimal_next_step",
        "required_behavior": (
            "Choose one concrete next step that advances a patch hypothesis; do not repeat equivalent read-only exploration."
        ),
        "allowed_next_actions": [
            "update_working_state with the current hypothesis",
            "read_file for one concrete file",
            "edit_file for one concrete file",
            "final_answer if the task is already complete or blocked",
        ],
        "disallowed_next_actions": [
            "repeating the same grep/list_files query",
            "wide search without a narrowed root or glob",
        ],
        "max_additional_read_file_calls_before_patch": None,
    }


def _build_loop_progress_summary(
    *,
    messages: list[dict[str, object]],
    state: AgentLoopState,
    budget_manager: BudgetManager,
) -> dict[str, Any]:
    tool_messages = [message for message in messages if message.get("role") == "tool"]
    analysis_tool_messages, last_patch_message = _tool_messages_after_last_patch_progress(tool_messages)
    patch_tool_call_count = sum(1 for message in tool_messages if _is_patch_progress_tool_result(message))
    patch_progress_messages = [
        message for message in tool_messages if _is_patch_progress_tool_result(message)
    ]
    total_read_only_tool_call_count = sum(1 for message in tool_messages if _is_read_only_tool_result(message))
    read_only_tool_call_count = sum(1 for message in analysis_tool_messages if _is_read_only_tool_result(message))
    consecutive_read_only_tool_calls = _consecutive_read_only_tool_calls(analysis_tool_messages)
    empty_search_count = sum(1 for message in analysis_tool_messages if _is_empty_search_tool_result(message))
    consecutive_empty_search_count = _consecutive_empty_search_tool_calls(analysis_tool_messages)
    repeated_input = _repeated_tool_input_summary(analysis_tool_messages)
    remaining_turns = max(0, budget_manager.max_turns - state.turn_count)
    near_turn_budget_threshold = _near_turn_budget_threshold(budget_manager.max_turns)
    has_patch = patch_tool_call_count > 0
    first_patch_progress_turn = (
        min(int(message.get("turn") or 0) for message in patch_progress_messages)
        if patch_progress_messages
        else None
    )
    last_patch_progress_turn = (
        int(last_patch_message.get("turn") or 0) if last_patch_message is not None else None
    )
    git_diff_called_after_patch = any(
        _effective_tool_name(message) == "git_diff" and str(message.get("status")) == "ok"
        for message in analysis_tool_messages
    )
    terminal_final_answer = state.agent_stop_reason == "final_answer"
    signals: list[dict[str, Any]] = []

    if consecutive_read_only_tool_calls >= NO_PROGRESS_READ_ONLY_STREAK_THRESHOLD:
        signals.append(
            {
                "signal_key": "long_read_only_streak",
                "severity": "warning",
                "value": consecutive_read_only_tool_calls,
                "threshold": NO_PROGRESS_READ_ONLY_STREAK_THRESHOLD,
                "meaning": "模型已经连续多次使用只读工具，但没有产生补丁修改。",
            }
        )
    if repeated_input["max_repeated_input_count"] >= NO_PROGRESS_REPEATED_INPUT_THRESHOLD:
        signals.append(
            {
                "signal_key": "repeated_tool_input",
                "severity": "warning",
                "value": repeated_input["max_repeated_input_count"],
                "threshold": NO_PROGRESS_REPEATED_INPUT_THRESHOLD,
                "meaning": "模型重复调用了等价的工具输入，探索可能已经进入循环。",
            }
        )
    if (
        empty_search_count >= NO_PROGRESS_EMPTY_SEARCH_THRESHOLD
        or consecutive_empty_search_count >= max(2, NO_PROGRESS_EMPTY_SEARCH_THRESHOLD - 1)
    ):
        signals.append(
            {
                "signal_key": "empty_search_accumulation",
                "severity": "warning",
                "value": empty_search_count,
                "consecutive_value": consecutive_empty_search_count,
                "threshold": NO_PROGRESS_EMPTY_SEARCH_THRESHOLD,
                "meaning": "模型多次搜索没有得到匹配结果，需要重新选择定位假设或改用更具体的路径。",
            }
        )
    if (
        not terminal_final_answer
        and not has_patch
        and state.turn_count >= 3
        and remaining_turns <= near_turn_budget_threshold
    ):
        signals.append(
            {
                "signal_key": "near_turn_budget_without_patch",
                "severity": "high",
                "value": remaining_turns,
                "threshold": near_turn_budget_threshold,
                "meaning": "任务接近轮次预算上限，但仍然没有任何补丁修改工具调用。",
            }
        )
    if (
        not terminal_final_answer
        and has_patch
        and remaining_turns <= NEAR_BUDGET_WITH_PATCH_TURN_THRESHOLD
    ):
        signals.append(
            {
                "signal_key": "near_turn_budget_with_patch",
                "severity": "high",
                "value": remaining_turns,
                "threshold": NEAR_BUDGET_WITH_PATCH_TURN_THRESHOLD,
                "meaning": "任务已经存在补丁并接近轮次预算上限，应优先检查 diff 并完成最终回答。",
                "git_diff_called_after_patch": git_diff_called_after_patch,
            }
        )

    return {
        "schema_version": "repo_harness_loop_progress_diagnostic_v0",
        "policy_version": NO_PROGRESS_DIAGNOSTIC_POLICY_VERSION,
        "diagnostic_status": "no_progress_suspected" if signals else "ok",
        "hard_stop_enabled": False,
        "model_visible_message_injected": False,
        "turn_count": state.turn_count,
        "max_turns": budget_manager.max_turns,
        "remaining_turns": remaining_turns,
        "near_turn_budget_threshold": near_turn_budget_threshold,
        "tool_call_count": state.tool_call_count,
        "patch_tool_call_count": patch_tool_call_count,
        "has_patch": has_patch,
        "read_only_tool_call_count": read_only_tool_call_count,
        "total_read_only_tool_call_count": total_read_only_tool_call_count,
        "analysis_window_tool_call_count": len(analysis_tool_messages),
        "analysis_window_started_after_patch_tool_call": last_patch_message is not None,
        "first_patch_progress_turn": first_patch_progress_turn,
        "last_patch_progress_turn": last_patch_progress_turn,
        "last_patch_progress_tool_result_id": (
            last_patch_message.get("tool_result_id") if last_patch_message is not None else None
        ),
        "consecutive_read_only_tool_calls": consecutive_read_only_tool_calls,
        "empty_search_count": empty_search_count,
        "consecutive_empty_search_count": consecutive_empty_search_count,
        "repeated_tool_input_count": repeated_input["repeated_tool_input_count"],
        "max_repeated_input_count": repeated_input["max_repeated_input_count"],
        "most_repeated_tool_input": repeated_input["most_repeated_tool_input"],
        "git_diff_called_after_patch": git_diff_called_after_patch,
        "signals": signals,
    }


def _tool_messages_after_last_patch_progress(
    tool_messages: list[dict[str, object]],
) -> tuple[list[dict[str, object]], dict[str, object] | None]:
    for index in range(len(tool_messages) - 1, -1, -1):
        if _is_patch_progress_tool_result(tool_messages[index]):
            return tool_messages[index + 1 :], tool_messages[index]
    return tool_messages, None


def _near_turn_budget_threshold(max_turns: int) -> int:
    return max(1, min(6, max_turns // 4))


def _is_read_only_tool_result(message: dict[str, object]) -> bool:
    return (
        str(message.get("status")) == "ok"
        and _effective_tool_name(message) in NO_PROGRESS_READ_ONLY_TOOL_NAMES
    )


def _is_patch_progress_tool_result(message: dict[str, object]) -> bool:
    return (
        str(message.get("status")) == "ok"
        and _effective_tool_name(message) in NO_PROGRESS_PATCH_TOOL_NAMES
    )


def _effective_tool_name(message: dict[str, object]) -> str:
    return str(message.get("effective_tool_name") or message.get("tool_name") or "")


def _consecutive_read_only_tool_calls(tool_messages: list[dict[str, object]]) -> int:
    count = 0
    for message in reversed(tool_messages):
        if _is_patch_progress_tool_result(message):
            break
        if _is_read_only_tool_result(message):
            count += 1
    return count


def _is_empty_search_tool_result(message: dict[str, object]) -> bool:
    if _effective_tool_name(message) != "grep" or str(message.get("status")) != "ok":
        return False
    typed = message.get("typed")
    if not isinstance(typed, dict):
        return False
    result_kind = str(typed.get("result_kind") or "")
    if result_kind in {"complete_no_match", "partial_scan_no_match", "page_empty_out_of_range"}:
        return True
    total_match_count = typed.get("total_match_count")
    match_count = typed.get("match_count")
    return total_match_count == 0 and match_count in {0, None}


def _consecutive_empty_search_tool_calls(tool_messages: list[dict[str, object]]) -> int:
    count = 0
    for message in reversed(tool_messages):
        if _is_patch_progress_tool_result(message):
            break
        if _is_empty_search_tool_result(message):
            count += 1
    return count


def _repeated_tool_input_summary(tool_messages: list[dict[str, object]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    labels: dict[str, dict[str, str]] = {}
    for message in tool_messages:
        normalized_input_hash = message.get("normalized_input_hash")
        if not normalized_input_hash:
            continue
        tool_name = _effective_tool_name(message)
        key = stable_hash({"tool_name": tool_name, "normalized_input_hash": normalized_input_hash})
        counts[key] = counts.get(key, 0) + 1
        labels[key] = {
            "tool_name": tool_name,
            "normalized_input_hash": str(normalized_input_hash),
        }
    if not counts:
        return {
            "repeated_tool_input_count": 0,
            "max_repeated_input_count": 0,
            "most_repeated_tool_input": None,
        }
    most_repeated_key = max(counts, key=counts.get)
    return {
        "repeated_tool_input_count": sum(max(0, count - 1) for count in counts.values()),
        "max_repeated_input_count": counts[most_repeated_key],
        "most_repeated_tool_input": {
            **labels[most_repeated_key],
            "count": counts[most_repeated_key],
        },
    }


def _record_tool_requested(
    *,
    run_id: str,
    task_id: str,
    turn: int,
    tool_call: ToolCall,
    recorder: RunRecorder,
) -> None:
    recorder.append_event(
        TrajectoryEvent(
            event_id=recorder.next_event_id("tool"),
            timestamp=_timestamp(),
            run_id=run_id,
            task_id=task_id,
            turn=turn,
            event_type="tool_requested",
            data=tool_call.model_dump(mode="json"),
        )
    )


def _record_tool_result(
    *,
    tool_result_artifact_index: ToolResultArtifactIndex | None = None,
    context_config: ContextManagementConfig | None = None,
    run_id: str,
    task_id: str,
    turn: int,
    tool_result: ToolResult,
    state: AgentLoopState,
    recorder: RunRecorder,
    messages: list[dict[str, object]],
) -> None:
    tool_result = _apply_single_tool_result_budget(
        tool_result,
        recorder=recorder,
        context_config=context_config or ContextManagementConfig(),
        tool_result_artifact_index=tool_result_artifact_index,
    )
    if tool_result.duration_ms is None:
        tool_result = _attach_tool_duration(tool_result, 0)
    state.tool_pairing_state.completed_tool_call_ids.append(tool_result.tool_call_id)
    state.tool_pairing_state.tool_result_ids[tool_result.tool_call_id] = tool_result.tool_result_id
    recorder.append_event(
        TrajectoryEvent(
            event_id=recorder.next_event_id("tool"),
            timestamp=_timestamp(),
            run_id=run_id,
            task_id=task_id,
            turn=turn,
            event_type=_tool_event_type(tool_result),
            error_type=tool_result.error_type,
            duration_ms=tool_result.duration_ms,
            artifact_refs=tool_result.artifact_refs,
            data=tool_result.model_dump(mode="json"),
        )
    )
    recorder.append_transcript(
        TranscriptRecord(
            record_id=recorder.next_record_id(),
            run_id=run_id,
            task_id=task_id,
            message_id=tool_result.tool_result_id,
            turn=turn,
            role="tool",
            tool_call_id=tool_result.tool_call_id,
            tool_result_id=tool_result.tool_result_id,
            content_preview=tool_result.content_preview,
            content_artifact_refs=tool_result.artifact_refs,
            model_visible=True,
            trainable=False,
            created_at=_timestamp(),
        )
    )
    messages.append(
        {
            "role": "tool",
            "turn": turn,
            "tool_call_id": tool_result.tool_call_id,
            "tool_result_id": tool_result.tool_result_id,
            "tool_name": tool_result.tool_name,
            "requested_tool_name": tool_result.requested_tool_name,
            "effective_tool_name": tool_result.effective_tool_name,
            "requested_arguments": tool_result.requested_arguments,
            "normalized_arguments": tool_result.normalized_arguments,
            "effective_arguments": tool_result.effective_arguments,
            "normalized_input_hash": tool_result.normalized_input_hash,
            "content": tool_result.content_preview,
            "status": tool_result.status,
            "error_type": tool_result.error_type,
            "typed": tool_result.typed,
            "artifact_refs": [ref.model_dump(mode="json") for ref in tool_result.artifact_refs],
        }
    )


def _apply_single_tool_result_budget(
    tool_result: ToolResult,
    *,
    recorder: RunRecorder,
    context_config: ContextManagementConfig,
    tool_result_artifact_index: ToolResultArtifactIndex | None,
) -> ToolResult:
    if tool_result.effective_tool_name == "read_tool_result_artifact":
        return tool_result
    content = tool_result.content_preview
    if len(content) <= context_config.max_single_tool_result_chars:
        return tool_result
    record = persist_tool_result_content(
        recorder=recorder,
        tool_result_id=tool_result.tool_result_id,
        tool_call_id=tool_result.tool_call_id,
        tool_name=tool_result.effective_tool_name,
        content=content,
        publishable_after_visibility_scan=True,
        contamination_scan_status="clean",
    )
    if tool_result_artifact_index is not None:
        tool_result_artifact_index.add(record)
    replacement = build_persisted_tool_result_preview(record, content)
    typed = dict(tool_result.typed)
    typed["single_tool_result_persisted"] = True
    typed["single_tool_result_original_chars"] = len(content)
    typed["single_tool_result_artifact_id"] = record.artifact_id
    typed["single_tool_result_content_sha256"] = record.content_sha256
    typed["single_tool_result_recovery_unlocked"] = record.recovery_unlocked_after_provider_commit
    envelope = typed.get("result_envelope")
    if isinstance(envelope, dict):
        updated_envelope = dict(envelope)
        updated_envelope["model_visible_text_truncated"] = True
        updated_envelope["artifact_backed_full_result"] = True
        updated_envelope["recovery_call"] = (
            "read_tool_result_artifact("
            f"artifact_id={record.artifact_id!r}, offset=0, limit=8000)"
        )
        updated_envelope["recovery_hint"] = (
            "Use read_tool_result_artifact after this persisted preview has entered "
            "an accepted model input."
        )
        context_effects = list(updated_envelope.get("context_effects") or [])
        if "tool_result_recoverable" not in context_effects:
            context_effects.append("tool_result_recoverable")
        updated_envelope["context_effects"] = context_effects
        typed["result_envelope"] = updated_envelope
    return tool_result.model_copy(
        update={
            "content_preview": replacement,
            "truncated": True,
            "artifact_refs": [*tool_result.artifact_refs, record.artifact_ref],
            "typed": typed,
        }
    )


def _attach_tool_duration(tool_result: ToolResult, duration_ms: int) -> ToolResult:
    duration = max(0, int(duration_ms))
    typed = dict(tool_result.typed)
    typed["duration_ms"] = duration
    typed["execution_duration_ms"] = duration
    envelope = typed.get("result_envelope")
    if isinstance(envelope, dict):
        updated_envelope = dict(envelope)
        updated_envelope["duration_ms"] = duration
        updated_envelope["execution_duration_ms"] = duration
        typed["result_envelope"] = updated_envelope
    return tool_result.model_copy(update={"duration_ms": duration, "typed": typed})


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_assistant_message_artifact(
    *,
    recorder: RunRecorder,
    content: str | None,
    tool_calls: list[ToolCall],
    finish_reason: str | None,
    model_error_type: str | None,
) -> ArtifactRef:
    return recorder.write_json_artifact(
        "assistant_message",
        {
            "schema_version": "repo_harness_assistant_message_transcript_payload_v0",
            "content": content,
            "tool_calls": [call.model_dump(mode="json") for call in tool_calls],
            "finish_reason": finish_reason,
            "model_error_type": model_error_type,
        },
        {"budget_policy": "preserve_json"},
    )


def _assistant_transcript_preview(*, content: str | None, tool_calls: list[ToolCall]) -> str:
    parts: list[str] = []
    if content:
        parts.append(content)
    if tool_calls:
        calls = [call.model_dump(mode="json") for call in tool_calls]
        parts.append("tool_calls=" + json.dumps(calls, ensure_ascii=False, sort_keys=True))
    return "\n".join(parts) if parts else ""


def _tool_event_type(tool_result: ToolResult) -> str:
    if tool_result.status == "ok":
        return "tool_completed"
    if tool_result.status == "denied":
        return "tool_denied"
    if tool_result.status == "timeout":
        return "tool_timeout"
    if tool_result.status == "interrupted":
        return "tool_interrupted"
    return "tool_failed"


def _budget_stop_reason(
    budget_manager: BudgetManager,
    state: AgentLoopState,
    loop_started: float,
    *,
    task_deadline_monotonic: float | None = None,
) -> str | None:
    deadline = (
        task_deadline_monotonic
        if task_deadline_monotonic is not None
        else loop_started + budget_manager.task_timeout_sec
    )
    if time.monotonic() >= deadline:
        return "timeout"
    if budget_manager.max_cost is not None and state.budget_state.cost >= budget_manager.max_cost:
        return "max_cost"
    return None


def _resolve_provider_call_timeout(
    *,
    configured_request_timeout_seconds: float,
    task_deadline_monotonic: float | None,
    provider_timeout_grace_sec: float,
    min_provider_request_timeout_sec: float,
    provider_timeout_policy: str,
) -> dict[str, Any]:
    now = time.monotonic()
    facts: dict[str, Any] = {
        "timeout_policy_version": provider_timeout_policy,
        "task_deadline_monotonic_present": task_deadline_monotonic is not None,
        "configured_request_timeout_seconds": configured_request_timeout_seconds,
        "provider_timeout_grace_sec": provider_timeout_grace_sec,
        "min_provider_request_timeout_sec": min_provider_request_timeout_sec,
        "absolute_deadline_enforced": task_deadline_monotonic is not None,
    }
    if task_deadline_monotonic is None:
        facts.update(
            {
                "remaining_task_time_sec_before_provider_call": None,
                "effective_request_timeout_seconds": configured_request_timeout_seconds,
                "deadline_skip_reason": None,
            }
        )
        return {
            "should_call_provider": True,
            "effective_request_timeout_seconds": configured_request_timeout_seconds,
            "facts": facts,
        }
    remaining = task_deadline_monotonic - now
    effective = min(
        configured_request_timeout_seconds,
        max(0.0, remaining - provider_timeout_grace_sec),
    )
    should_call = effective >= min_provider_request_timeout_sec
    facts.update(
        {
            "remaining_task_time_sec_before_provider_call": round(remaining, 6),
            "effective_request_timeout_seconds": round(effective, 6),
            "deadline_skip_reason": None if should_call else "task_timeout_before_provider_call",
        }
    )
    return {
        "should_call_provider": should_call,
        "effective_request_timeout_seconds": max(effective, 0.001),
        "facts": facts,
    }


def _record_provider_call_skipped_due_to_deadline(
    *,
    run_id: str,
    task_id: str,
    turn: int,
    state: AgentLoopState,
    recorder: RunRecorder,
    timeout_facts: dict[str, Any],
    call_site: str,
) -> None:
    state.agent_stop_reason = "timeout"
    state.budget_state.stop_reason = "timeout"
    recorder.append_event(
        TrajectoryEvent(
            event_id=recorder.next_event_id("budget"),
            timestamp=_timestamp(),
            run_id=run_id,
            task_id=task_id,
            turn=turn,
            event_type="provider_call_skipped_due_to_task_deadline",
            severity="warning",
            error_type="task_timeout_before_provider_call",
            data={
                "reason": "task_timeout_before_provider_call",
                "call_site": call_site,
                "timeout_policy_facts": timeout_facts,
            },
        )
    )
    _record_budget_exhausted(
        run_id=run_id,
        task_id=task_id,
        turn=turn,
        reason="timeout",
        state=state,
        recorder=recorder,
        details={
            "provider_call_skipped_due_to_task_deadline": True,
            "provider_call_site": call_site,
            "timeout_policy_facts": timeout_facts,
        },
    )


def _record_budget_exhausted(
    *,
    run_id: str,
    task_id: str,
    turn: int,
    reason: str,
    state: AgentLoopState,
    recorder: RunRecorder,
    details: dict[str, Any] | None = None,
) -> None:
    state.agent_stop_reason = reason  # type: ignore[assignment]
    state.budget_state.stop_reason = reason
    recorder.append_event(
        TrajectoryEvent(
            event_id=recorder.next_event_id("budget"),
            timestamp=_timestamp(),
            run_id=run_id,
            task_id=task_id,
            turn=turn,
            event_type="budget_exhausted",
            severity="warning",
            error_type=reason,
            data={
                "reason": reason,
                **(details or {}),
                "budget_state": state.budget_state.model_dump(mode="json"),
            },
        )
    )


def _default_budget_manager(max_turns: int) -> BudgetManager:
    return BudgetManager(
        max_turns=max_turns,
        max_tool_calls=1000,
        max_test_runs=1000,
        task_timeout_sec=3600,
        command_timeout_sec=120,
        verifier_timeout_sec=120,
        max_tool_output_chars=12000,
        max_context_tokens=120000,
        max_output_tokens=4096,
    )


def _record_interrupted_tool_calls(
    *,
    tool_result_artifact_index: ToolResultArtifactIndex | None = None,
    context_config: ContextManagementConfig | None = None,
    run_id: str,
    task_id: str,
    turn: int,
    tool_calls: list[ToolCall],
    reason: str,
    state: AgentLoopState,
    recorder: RunRecorder,
    messages: list[dict[str, object]],
    emit_tool_requested: bool,
) -> None:
    for remaining in tool_calls:
        if remaining.tool_call_id in state.tool_pairing_state.tool_result_ids:
            continue
        if emit_tool_requested:
            _record_tool_requested(
                run_id=run_id,
                task_id=task_id,
                turn=turn,
                tool_call=remaining,
                recorder=recorder,
            )
        _record_tool_result(
            tool_result_artifact_index=tool_result_artifact_index,
            context_config=context_config,
            run_id=run_id,
            task_id=task_id,
            turn=turn,
            tool_result=_interrupted_tool_result(remaining, reason),
            state=state,
            recorder=recorder,
            messages=messages,
        )


def _interrupted_tool_result(tool_call: ToolCall, reason: str) -> ToolResult:
    return ToolResult(
        tool_result_id=f"{tool_call.tool_call_id}_result",
        tool_call_id=tool_call.tool_call_id,
        tool_name=tool_call.tool_name,
        requested_tool_name=tool_call.tool_name,
        effective_tool_name=tool_call.tool_name,
        requested_arguments=tool_call.arguments,
        normalized_arguments=tool_call.arguments,
        effective_arguments=tool_call.arguments,
        normalized_input_hash=stable_hash(tool_call.arguments),
        status="interrupted",
        content_preview=f"Tool call interrupted before execution: {reason}",
        error_type=reason,
        typed={"status": "interrupted", "error_type": reason},
    )
