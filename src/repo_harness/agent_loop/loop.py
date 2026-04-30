"""阶段七最小 Agent Loop。"""

from __future__ import annotations

from datetime import datetime, timezone

from repo_harness.agent_loop.schemas import AgentLoopState
from repo_harness.budget import BudgetState
from repo_harness.config import ContextManagementConfig
from repo_harness.context import ContextManager
from repo_harness.model_client import ReplayModelClient
from repo_harness.tools import ToolExecutionContext, ToolExecutor, ToolResult
from repo_harness.trajectory import RunRecorder, TranscriptRecord, TrajectoryEvent


class AgentLoop:
    def __init__(self, *, model_client: ReplayModelClient, tool_executor: ToolExecutor) -> None:
        self.model_client = model_client
        self.tool_executor = tool_executor
        self.context_manager = ContextManager()

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
    ) -> AgentLoopState:
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

        for turn in range(1, max_turns + 1):
            state.turn_count = turn
            prepared = self.context_manager.prepare_messages(
                messages=messages,
                recorder=recorder,
                task_id=task_id,
                turn=turn,
                context_config=context_config,
            )
            state.context_revision = prepared.context_revision
            recorder.append_event(prepared.context_event)
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
                state.last_model_error = response.model_error_type
                break
            if not response.tool_calls:
                state.agent_stop_reason = "final_answer"
                break
            for tool_call in response.tool_calls:
                state.tool_call_count += 1
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
        else:
            state.agent_stop_reason = "max_turns"
        state.messages = messages
        return state


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
