"""最小 Context Manager。"""

from __future__ import annotations

from repo_harness.context.schemas import ContentReplacementState, PreparedMessages
from repo_harness.schema_base import stable_hash
from repo_harness.schema_versions import CONTEXT_POLICY_VERSION
from repo_harness.trajectory import RunRecorder, TrajectoryEvent


class ContextManager:
    def __init__(self) -> None:
        self.context_revision = 0

    def prepare_messages(
        self,
        *,
        messages: list[dict[str, object]],
        recorder: RunRecorder,
        task_id: str,
        turn: int,
    ) -> PreparedMessages:
        self.context_revision += 1
        model_input_hash = stable_hash(messages)
        prepared_ref = recorder.write_json_artifact(
            "prepared_messages",
            {"messages": messages, "context_revision": self.context_revision},
        )
        event = TrajectoryEvent(
            event_id=recorder.next_event_id("context"),
            timestamp=_timestamp(),
            run_id=recorder.run_id,
            task_id=task_id,
            turn=turn,
            event_type="context_prepared",
            artifact_refs=[prepared_ref],
            data={
                "context_revision": self.context_revision,
                "model_input_hash": model_input_hash,
                "context_policy_version": CONTEXT_POLICY_VERSION,
            },
        )
        state = ContentReplacementState(
            seen_tool_result_ids=[],
            records=[],
            state_hash=stable_hash({"context_revision": self.context_revision}),
            last_context_revision=self.context_revision,
        )
        return PreparedMessages(
            messages=messages,
            prepared_messages_ref=prepared_ref,
            model_input_hash=model_input_hash,
            context_revision=self.context_revision,
            context_event=event,
            content_replacement_state=state,
            token_estimate=max(1, len(str(messages)) // 4),
        )


def _timestamp() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
