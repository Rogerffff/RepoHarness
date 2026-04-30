"""Context Manager。"""

from __future__ import annotations

from typing import Any

from repo_harness.config import ContextManagementConfig
from repo_harness.context.schemas import (
    ContentReplacementRecord,
    ContentReplacementState,
    PreparedMessages,
)
from repo_harness.schema_base import stable_hash
from repo_harness.schema_versions import CONTEXT_POLICY_VERSION
from repo_harness.trajectory import ArtifactRef, RunRecorder, TrajectoryEvent


class ContextManager:
    def __init__(self) -> None:
        self.context_revision = 0
        self._records_by_tool_result_id: dict[str, ContentReplacementRecord] = {}
        self._replacement_text_by_tool_result_id: dict[str, str] = {}

    def prepare_messages(
        self,
        *,
        messages: list[dict[str, object]],
        recorder: RunRecorder,
        task_id: str,
        turn: int,
        context_config: ContextManagementConfig | None = None,
    ) -> PreparedMessages:
        self.context_revision += 1
        config = context_config or ContextManagementConfig()
        prepared_messages, reduction_data = self._reduce_messages(
            messages,
            recorder,
            config,
        )
        model_input_hash = stable_hash(prepared_messages)
        pairing_validation = _validate_tool_pairing(prepared_messages)
        state = ContentReplacementState(
            seen_tool_result_ids=list(self._records_by_tool_result_id.keys()),
            records=list(self._records_by_tool_result_id.values()),
            state_hash=self._state_hash(),
            last_context_revision=self.context_revision,
        )
        state_ref = recorder.write_json_artifact(
            "content_replacement_state",
            state.model_dump(mode="json"),
        )
        prepared_ref = recorder.write_json_artifact(
            "prepared_messages",
            {
                "messages": prepared_messages,
                "context_revision": self.context_revision,
                "model_input_hash": model_input_hash,
                "provider_format": "repo_harness_messages_v0",
                "content_replacement_state": state.model_dump(mode="json"),
                "content_replacement_state_ref": state_ref.model_dump(mode="json"),
            },
        )
        event = TrajectoryEvent(
            event_id=recorder.next_event_id("context"),
            timestamp=_timestamp(),
            run_id=recorder.run_id,
            task_id=task_id,
            turn=turn,
            event_type="context_prepared",
            artifact_refs=[prepared_ref, state_ref],
            data={
                "context_revision": self.context_revision,
                "model_input_hash": model_input_hash,
                "context_policy_version": CONTEXT_POLICY_VERSION,
                "token_estimator_version": "repo_harness_char_estimator_v0",
                "tokens_before": max(1, len(str(messages)) // 4),
                "tokens_after": max(1, len(str(prepared_messages)) // 4),
                "tool_pairing_validation": pairing_validation,
                "context_reduction": reduction_data,
                "content_replacement_state_hash": state.state_hash,
                "content_replacement_state_ref": state_ref.model_dump(mode="json"),
            },
        )
        return PreparedMessages(
            messages=prepared_messages,
            prepared_messages_ref=prepared_ref,
            model_input_hash=model_input_hash,
            context_revision=self.context_revision,
            context_event=event,
            content_replacement_state=state,
            token_estimate=max(1, len(str(prepared_messages)) // 4),
        )

    def _reduce_messages(
        self,
        messages: list[dict[str, object]],
        recorder: RunRecorder,
        config: ContextManagementConfig,
    ) -> tuple[list[dict[str, object]], dict[str, Any]]:
        prepared: list[dict[str, object]] = []
        aggregate_tool_chars = 0
        replaced_tool_result_ids: list[str] = []
        replacement_refs: list[ArtifactRef] = []
        for message in messages:
            if message.get("role") != "tool":
                prepared.append(dict(message))
                continue
            tool_result_id = str(message.get("tool_result_id") or message.get("tool_call_id") or "")
            content = str(message.get("content", ""))
            aggregate_tool_chars += len(content)
            should_replace = (
                tool_result_id in self._replacement_text_by_tool_result_id
                or len(content) > config.tool_result_aggregate_budget_chars
                or aggregate_tool_chars > config.tool_result_aggregate_budget_chars
            )
            if should_replace:
                replacement, ref = self._replacement_for_tool_result(
                    tool_result_id=tool_result_id,
                    message=message,
                    original_content=content,
                    recorder=recorder,
                    reason="tool_result_aggregate_budget_exceeded",
                )
                replaced = dict(message)
                replaced["content"] = replacement
                replaced["context_replacement"] = True
                prepared.append(replaced)
                replaced_tool_result_ids.append(tool_result_id)
                replacement_refs.append(ref)
            else:
                self._record_first_visible(
                    tool_result_id=tool_result_id,
                    tool_call_id=str(message.get("tool_call_id") or tool_result_id),
                    content=content,
                )
                prepared.append(dict(message))
        return prepared, {
            "replaced_tool_result_ids": replaced_tool_result_ids,
            "replacement_artifact_refs": [ref.model_dump(mode="json") for ref in replacement_refs],
        }

    def _record_first_visible(self, *, tool_result_id: str, tool_call_id: str, content: str) -> None:
        if not tool_result_id or tool_result_id in self._records_by_tool_result_id:
            return
        record = ContentReplacementRecord(
            tool_call_id=tool_call_id,
            original_tool_result_id=tool_result_id,
            replaced=False,
            first_visible_form="preview",
            first_visible_content_hash=stable_hash(content),
            replacement_allowed_after_first_seen=True,
            first_seen_at_context_revision=self.context_revision,
        )
        self._records_by_tool_result_id[tool_result_id] = record

    def _replacement_for_tool_result(
        self,
        *,
        tool_result_id: str,
        message: dict[str, object],
        original_content: str,
        recorder: RunRecorder,
        reason: str,
    ) -> tuple[str, ArtifactRef]:
        existing = self._replacement_text_by_tool_result_id.get(tool_result_id)
        if existing is not None:
            record = self._records_by_tool_result_id[tool_result_id]
            return existing, record.replacement_artifact_refs[0]

        artifact_refs = message.get("artifact_refs") or message.get("content_artifact_refs") or []
        artifact = artifact_refs[0] if artifact_refs else None
        if hasattr(artifact, "model_dump"):
            artifact_data = artifact.model_dump(mode="json")
        elif isinstance(artifact, dict):
            artifact_data = artifact
        else:
            artifact_data = {}
        head, tail = _head_tail(original_content)
        replacement = (
            f"[tool result replaced]\n"
            f"tool_result_id: {tool_result_id}\n"
            f"artifact_id: {artifact_data.get('artifact_id', 'none')}\n"
            f"sha256: {artifact_data.get('sha256', stable_hash(original_content))}\n"
            f"reason: {reason}\n"
            f"head:\n{head}\n"
            f"tail:\n{tail}"
        )
        replacement_ref = recorder.write_json_artifact(
            "context_replacement",
            {
                "tool_result_id": tool_result_id,
                "replacement_preview": replacement,
                "reason": reason,
                "source_artifact_ref": artifact_data,
            },
        )
        existing_record = self._records_by_tool_result_id.get(tool_result_id)
        record = ContentReplacementRecord(
            tool_call_id=str(message.get("tool_call_id") or tool_result_id),
            original_tool_result_id=tool_result_id,
            replaced=True,
            first_visible_form=existing_record.first_visible_form if existing_record else "replacement",
            first_visible_content_hash=(
                existing_record.first_visible_content_hash
                if existing_record
                else stable_hash(replacement)
            ),
            replacement_allowed_after_first_seen=True,
            replacement_text_hash=stable_hash(replacement),
            replacement_artifact_refs=[replacement_ref],
            replacement_preview_hash=stable_hash(replacement),
            first_replaced_at_context_revision=self.context_revision,
            first_seen_at_context_revision=(
                existing_record.first_seen_at_context_revision
                if existing_record
                else self.context_revision
            ),
        )
        self._replacement_text_by_tool_result_id[tool_result_id] = replacement
        self._records_by_tool_result_id[tool_result_id] = record
        return replacement, replacement_ref

    def _state_hash(self) -> str:
        return stable_hash(
            [
                record.model_dump(mode="json")
                for record in self._records_by_tool_result_id.values()
            ]
        )


def _timestamp() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _head_tail(text: str, line_count: int = 3) -> tuple[str, str]:
    lines = text.splitlines()
    head = "\n".join(lines[:line_count])
    tail = "\n".join(lines[-line_count:]) if len(lines) > line_count else head
    return head, tail


def _validate_tool_pairing(messages: list[dict[str, object]]) -> dict[str, Any]:
    requested: list[str] = []
    observed: list[str] = []
    for message in messages:
        if message.get("role") == "assistant":
            for tool_call in message.get("tool_calls", []) or []:
                if isinstance(tool_call, dict) and tool_call.get("tool_call_id"):
                    requested.append(str(tool_call["tool_call_id"]))
        elif message.get("role") == "tool" and message.get("tool_call_id"):
            observed.append(str(message["tool_call_id"]))
    missing = [tool_call_id for tool_call_id in requested if tool_call_id not in observed]
    orphaned = [tool_call_id for tool_call_id in observed if tool_call_id not in requested]
    return {
        "ok": not missing and not orphaned,
        "missing_tool_result_ids": missing,
        "orphaned_tool_result_ids": orphaned,
    }
