"""阶段七最小 Agent Loop。"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from repo_harness.agent_loop.schemas import AgentLoopState
from repo_harness.budget import BudgetManager, BudgetState
from repo_harness.config import ContextManagementConfig
from repo_harness.context import ContextManager
from repo_harness.model_client import ReplayModelClient
from repo_harness.schema_base import stable_hash
from repo_harness.scaffolds import SimpleReactScaffold, build_scaffold
from repo_harness.tools import ToolCall
from repo_harness.tools import ToolExecutionContext, ToolExecutor, ToolResult
from repo_harness.trajectory import RunRecorder, TranscriptRecord, TrajectoryEvent


class AgentLoop:
    def __init__(
        self,
        *,
        model_client: ReplayModelClient,
        tool_executor: ToolExecutor,
        scaffold: SimpleReactScaffold | None = None,
    ) -> None:
        self.model_client = model_client
        self.tool_executor = tool_executor
        self.context_manager = ContextManager()
        self.scaffold = scaffold or build_scaffold("simple_react")

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
    ) -> AgentLoopState:
        budget_manager = budget_manager or _default_budget_manager(max_turns)
        loop_started = time.monotonic()
        messages = list(initial_messages)
        state = AgentLoopState(
            run_id=run_id,
            task_id=task_id,
            messages=messages,
            budget_state=BudgetState(started_at=_timestamp()),
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

        for turn in range(1, budget_manager.max_turns + 1):
            state.turn_count = turn
            state.budget_state.turn_count = turn
            budget_stop = _budget_stop_reason(budget_manager, state, loop_started)
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
            prepared = self.context_manager.prepare_messages(
                messages=messages,
                recorder=recorder,
                task_id=task_id,
                turn=turn,
                context_config=context_config,
            )
            state.context_revision = prepared.context_revision
            recorder.append_event(prepared.context_event)
            if prepared.token_estimate > budget_manager.max_context_tokens:
                state.agent_stop_reason = "context_limit"
                state.budget_state.stop_reason = "context_limit"
                recorder.append_event(
                    TrajectoryEvent(
                        event_id=recorder.next_event_id("budget"),
                        timestamp=_timestamp(),
                        run_id=run_id,
                        task_id=task_id,
                        turn=turn,
                        event_type="budget_exhausted",
                        severity="warning",
                        error_type="context_limit",
                        data={
                            "token_estimate": prepared.token_estimate,
                            "max_context_tokens": budget_manager.max_context_tokens,
                        },
                    )
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
                        "model_input_hash": prepared.model_input_hash,
                    },
                )
            )
            response = self.model_client.generate(
                prepared_messages=prepared,
                recorder=recorder,
                turn=turn,
            )
            if response.model_call_event is not None:
                state.budget_state.input_tokens += response.model_call_event.input_tokens
                state.budget_state.output_tokens += response.model_call_event.output_tokens
            if response.model_call_event:
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
                            ]
                            if ref is not None
                        ],
                        data={
                            **response.model_call_event.model_dump(mode="json"),
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
                        },
                    )
                )
            assistant_preview = response.assistant_message.content or str(
                [call.model_dump(mode="json") for call in response.tool_calls]
            )
            recorder.append_transcript(
                TranscriptRecord(
                    record_id=recorder.next_record_id(),
                    run_id=run_id,
                    task_id=task_id,
                    message_id=f"assistant_{turn}",
                    turn=turn,
                    role="assistant",
                    model_call_id=response.model_call_event.model_call_id
                    if response.model_call_event
                    else None,
                    content_preview=assistant_preview[:4000],
                    model_visible=True,
                    trainable=True,
                    created_at=_timestamp(),
                )
            )
            messages.append(
                {
                    "role": "assistant",
                    "content": response.assistant_message.content,
                    "tool_calls": [call.model_dump(mode="json") for call in response.tool_calls],
                    "model_error_type": response.model_error_type,
                }
            )
            if response.model_error_type:
                state.agent_stop_reason = "model_error"
                state.budget_state.stop_reason = "model_error"
                state.last_model_error = response.model_error_type
                break
            if not response.tool_calls:
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
            stop_after_tools = False
            for tool_index, tool_call in enumerate(response.tool_calls):
                _record_tool_requested(
                    run_id=run_id,
                    task_id=task_id,
                    turn=turn,
                    tool_call=tool_call,
                    recorder=recorder,
                )
                if state.tool_call_count >= budget_manager.max_tool_calls:
                    state.agent_stop_reason = "max_tool_calls"
                    state.budget_state.stop_reason = "max_tool_calls"
                    _record_tool_result(
                        run_id=run_id,
                        task_id=task_id,
                        turn=turn,
                        tool_result=_interrupted_tool_result(tool_call, "max_tool_calls"),
                        state=state,
                        recorder=recorder,
                        messages=messages,
                    )
                    _record_interrupted_tool_calls(
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
                if normalized_request.effective_tool_name == "run_tests":
                    if state.budget_state.test_run_count >= budget_manager.max_test_runs:
                        state.agent_stop_reason = "max_test_runs"
                        state.budget_state.stop_reason = "max_test_runs"
                        _record_tool_result(
                            run_id=run_id,
                            task_id=task_id,
                            turn=turn,
                            tool_result=_interrupted_tool_result(tool_call, "max_test_runs"),
                            state=state,
                            recorder=recorder,
                            messages=messages,
                        )
                        _record_interrupted_tool_calls(
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
                tool_result = self.tool_executor.execute(tool_call, tool_context)
                _record_tool_result(
                    run_id=run_id,
                    task_id=task_id,
                    turn=turn,
                    tool_result=tool_result,
                    state=state,
                    recorder=recorder,
                    messages=messages,
                )
                if tool_result.effective_tool_name == "run_tests":
                    state.budget_state.test_run_count += 1
                    state.last_verifier_result = tool_result.typed.get("verifier_result_preview")
                    if (
                        isinstance(state.last_verifier_result, dict)
                        and state.last_verifier_result.get("accepted") is True
                    ):
                        state.agent_stop_reason = "feedback_tests_passed"
                        state.budget_state.stop_reason = "feedback_tests_passed"
                        _record_interrupted_tool_calls(
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
            if stop_after_tools:
                break
        else:
            state.agent_stop_reason = "max_turns"
            state.budget_state.stop_reason = "max_turns"
        state.messages = messages
        return state


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
    run_id: str,
    task_id: str,
    turn: int,
    tool_result: ToolResult,
    state: AgentLoopState,
    recorder: RunRecorder,
    messages: list[dict[str, object]],
) -> None:
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
            "tool_call_id": tool_result.tool_call_id,
            "tool_result_id": tool_result.tool_result_id,
            "content": tool_result.content_preview,
            "status": tool_result.status,
            "error_type": tool_result.error_type,
            "typed": tool_result.typed,
            "artifact_refs": [ref.model_dump(mode="json") for ref in tool_result.artifact_refs],
        }
    )


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


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
) -> str | None:
    if time.monotonic() - loop_started >= budget_manager.task_timeout_sec:
        return "timeout"
    if budget_manager.max_cost is not None and state.budget_state.cost >= budget_manager.max_cost:
        return "max_cost"
    return None


def _record_budget_exhausted(
    *,
    run_id: str,
    task_id: str,
    turn: int,
    reason: str,
    state: AgentLoopState,
    recorder: RunRecorder,
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
