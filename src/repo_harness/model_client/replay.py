"""Replay model client。"""

from __future__ import annotations

from pathlib import Path

import yaml

from repo_harness.context.schemas import PreparedMessages
from repo_harness.model_client.schemas import ModelCallEvent, ModelMessage, ModelResponse, ReplayScript
from repo_harness.schema_base import stable_hash
from repo_harness.tools.schemas import ToolCall
from repo_harness.trajectory import RunRecorder


class ReplayModelClient:
    def __init__(self, script: ReplayScript) -> None:
        self.script = script
        self.index = 0

    @classmethod
    def from_path(cls, path: str | Path) -> "ReplayModelClient":
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        return cls(ReplayScript.model_validate(raw))

    def generate(
        self,
        *,
        prepared_messages: PreparedMessages,
        recorder: RunRecorder,
        turn: int,
    ) -> ModelResponse:
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
            tool_schema_hash=stable_hash(["read_file", "edit_file", "run_tests", "git_diff"]),
            model_error_type=model_error_type,
        )
        return ModelResponse(
            assistant_message=assistant,
            tool_calls=tool_calls,
            raw_provider_request_ref=prepared_messages.prepared_messages_ref,
            raw_provider_response_ref=raw_response_ref,
            finish_reason=finish_reason,
            model_error_type=model_error_type,
            provider_request_id=step.step_id if step is not None else None,
            model_call_event=model_call_event,
        )
