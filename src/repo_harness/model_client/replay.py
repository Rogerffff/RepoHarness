"""Replay model client。"""

from __future__ import annotations

import json
from pathlib import Path
import yaml

from repo_harness.context.schemas import PreparedMessages
from repo_harness.model_client.schemas import ModelCallEvent, ModelMessage, ModelResponse, ReplayScript
from repo_harness.schema_base import stable_hash
from repo_harness.tools import DEFAULT_TOOL_ORDER
from repo_harness.tools.schemas import ToolCall
from repo_harness.trajectory import RunRecorder


class ReplayModelClient:
    def __init__(self, script: ReplayScript) -> None:
        self.script = script
        self.index = 0
        self._validate_script()

    @classmethod
    def from_path(cls, path: str | Path) -> "ReplayModelClient":
        resolved = Path(path)
        if resolved.suffix == ".jsonl":
            steps = [
                json.loads(line)
                for line in resolved.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            raw = {
                "script_id": resolved.stem,
                "task_id": "jsonl_replay",
                "steps": steps,
            }
        else:
            raw = yaml.safe_load(resolved.read_text(encoding="utf-8"))
        return cls(ReplayScript.model_validate(raw))

    def _validate_script(self) -> None:
        seen: set[str] = set()
        duplicates: list[str] = []
        for step in self.script.steps:
            if step.tool_call_id is None:
                continue
            if step.tool_call_id in seen:
                duplicates.append(step.tool_call_id)
            seen.add(step.tool_call_id)
        if duplicates:
            raise ValueError(f"ReplayScript contains duplicate tool_call_id values: {duplicates}")

    def generate(
        self,
        *,
        prepared_messages: PreparedMessages,
        recorder: RunRecorder,
        turn: int,
    ) -> ModelResponse:
        alignment_error = self._validate_prepared_messages(prepared_messages)
        if alignment_error is not None:
            return self._model_error_response(
                prepared_messages=prepared_messages,
                recorder=recorder,
                turn=turn,
                model_error_type=alignment_error,
                content=f"Replay alignment error: {alignment_error}",
            )
        if self.index >= len(self.script.steps):
            step = None
            assistant = ModelMessage(role="assistant", content="Replay script exhausted.")
            tool_calls: list[ToolCall] = []
            finish_reason = "stop"
            model_error_type = "replay_script_exhausted"
        else:
            step = self.script.steps[self.index]
            self.index += 1
            if step.action == "tool_call":
                tool_call = ToolCall(
                    tool_call_id=step.tool_call_id or f"replay_tool_{turn}",
                    tool_name=step.tool_name or "unknown",
                    arguments=step.arguments or {},
                    turn=turn,
                )
                assistant = ModelMessage(
                    role="assistant",
                    content=step.assistant_text,
                    tool_calls=[tool_call],
                    metadata={"replay_step_id": step.step_id},
                )
                tool_calls = [tool_call]
                finish_reason = "tool_calls"
                model_error_type = None
            elif step.action == "model_error":
                assistant = ModelMessage(
                    role="assistant",
                    content=step.assistant_text,
                    metadata={"replay_step_id": step.step_id},
                )
                tool_calls = []
                finish_reason = "error"
                model_error_type = step.model_error_type
            else:
                assistant = ModelMessage(
                    role="assistant",
                    content=step.assistant_text,
                    metadata={"replay_step_id": step.step_id, "action": step.action},
                )
                tool_calls = []
                finish_reason = "stop"
                model_error_type = None
        raw_request_ref = self._write_raw_request(prepared_messages, recorder)
        raw_response_ref = recorder.write_json_artifact(
            "raw_replay_response",
            {
                "step": step.model_visible_payload() if step is not None else None,
                "finish_reason": finish_reason,
                "model_error_type": model_error_type,
            },
        )
        model_call_id = f"{recorder.run_id}_model_call_{turn:04d}"
        model_call_event = ModelCallEvent(
            model_call_id=model_call_id,
            model_id="replay-script-v0",
            provider_request_id=step.step_id if step is not None else None,
            context_revision=prepared_messages.context_revision,
            prepared_messages_ref=prepared_messages.prepared_messages_ref,
            model_input_hash=prepared_messages.model_input_hash,
            provider_message_format="repo_harness_replay_v0",
            tool_schema_hash=stable_hash(DEFAULT_TOOL_ORDER),
            model_error_type=model_error_type,
        )
        return ModelResponse(
            assistant_message=assistant,
            tool_calls=tool_calls,
            raw_provider_request_ref=raw_request_ref,
            raw_provider_response_ref=raw_response_ref,
            finish_reason=finish_reason,
            model_error_type=model_error_type,
            provider_request_id=step.step_id if step is not None else None,
            model_call_event=model_call_event,
        )

    def _validate_prepared_messages(self, prepared_messages: PreparedMessages) -> str | None:
        if self.index == 0:
            return None
        expected_step = self.script.steps[self.index - 1]
        if expected_step.action != "tool_call":
            return None
        assistant_call = _last_assistant_tool_call(prepared_messages.messages)
        if assistant_call is None:
            return "replay_missing_assistant_tool_call"
        if assistant_call.get("tool_call_id") != expected_step.tool_call_id:
            return "replay_tool_order_mismatch"
        if assistant_call.get("tool_name") != expected_step.tool_name:
            return "replay_tool_name_mismatch"
        if assistant_call.get("arguments") != (expected_step.arguments or {}):
            return "replay_tool_arguments_mismatch"
        tool_result = _tool_result_for_call(prepared_messages.messages, str(expected_step.tool_call_id))
        if tool_result is None:
            return "replay_missing_tool_result"
        expected = expected_step.expected_outcome or {}
        if expected.get("status") is not None and tool_result.get("status") != expected["status"]:
            return "replay_tool_result_status_mismatch"
        if expected.get("error_type") is not None and tool_result.get("error_type") != expected["error_type"]:
            return "replay_tool_result_error_mismatch"
        return None

    def _model_error_response(
        self,
        *,
        prepared_messages: PreparedMessages,
        recorder: RunRecorder,
        turn: int,
        model_error_type: str,
        content: str,
    ) -> ModelResponse:
        raw_request_ref = self._write_raw_request(prepared_messages, recorder)
        raw_response_ref = recorder.write_json_artifact(
            "raw_replay_response",
            {
                "finish_reason": "error",
                "model_error_type": model_error_type,
            },
        )
        model_call_event = ModelCallEvent(
            model_call_id=f"{recorder.run_id}_model_call_{turn:04d}",
            model_id="replay-script-v0",
            context_revision=prepared_messages.context_revision,
            prepared_messages_ref=prepared_messages.prepared_messages_ref,
            model_input_hash=prepared_messages.model_input_hash,
            provider_message_format="repo_harness_replay_v0",
            tool_schema_hash=stable_hash(DEFAULT_TOOL_ORDER),
            model_error_type=model_error_type,
        )
        return ModelResponse(
            assistant_message=ModelMessage(role="assistant", content=content),
            raw_provider_request_ref=raw_request_ref,
            raw_provider_response_ref=raw_response_ref,
            finish_reason="error",
            model_error_type=model_error_type,
            model_call_event=model_call_event,
        )

    def _write_raw_request(
        self,
        prepared_messages: PreparedMessages,
        recorder: RunRecorder,
    ):
        return recorder.write_json_artifact(
            "raw_replay_request",
            {
                "prepared_messages_ref": prepared_messages.prepared_messages_ref.model_dump(mode="json"),
                "context_revision": prepared_messages.context_revision,
                "model_input_hash": prepared_messages.model_input_hash,
                "tool_order": DEFAULT_TOOL_ORDER,
                "provider_message_format": "repo_harness_replay_request_v0",
            },
        )


def _last_assistant_tool_call(messages: list[dict[str, object]]) -> dict[str, object] | None:
    for message in reversed(messages):
        if message.get("role") != "assistant":
            continue
        tool_calls = message.get("tool_calls") or []
        if not isinstance(tool_calls, list) or not tool_calls:
            return None
        call = tool_calls[-1]
        return call if isinstance(call, dict) else None
    return None


def _tool_result_for_call(
    messages: list[dict[str, object]],
    tool_call_id: str,
) -> dict[str, object] | None:
    for message in reversed(messages):
        if message.get("role") == "tool" and message.get("tool_call_id") == tool_call_id:
            return message
    return None
