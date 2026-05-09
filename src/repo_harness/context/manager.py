"""Context Manager。"""

from __future__ import annotations

import json
from typing import Any

from repo_harness.config import ContextManagementConfig
from repo_harness.context.schemas import (
    ContentReplacementRecord,
    ContentReplacementState,
    PreparedMessages,
)
from repo_harness.context.tool_result_artifacts import (
    ToolResultArtifactIndex,
    build_persisted_tool_result_preview,
    persist_tool_result_content,
)
from repo_harness.schema_base import stable_hash
from repo_harness.schema_versions import CONTEXT_POLICY_VERSION
from repo_harness.trajectory import ArtifactRef, RunRecorder, TrajectoryEvent

PROVIDER_READY_TOKEN_ESTIMATOR_VERSION = "provider_body_char4_token_estimator_v1"
CONTEXT_REPLACEMENT_RUNTIME_POLICY_VERSION = "fresh_tool_result_budget_runtime_v1"
REPLACEMENT_PREVIEW_MAX_CHARS = 1200


class ContextManager:
    def __init__(self) -> None:
        self.context_revision = 0
        self._records_by_tool_result_id: dict[str, ContentReplacementRecord] = {}
        self._replacement_text_by_tool_result_id: dict[str, str] = {}
        self._candidate_records_by_revision: dict[
            int, dict[str, ContentReplacementRecord]
        ] = {}
        self._candidate_replacement_text_by_revision: dict[int, dict[str, str]] = {}

    def prepare_messages(
        self,
        *,
        messages: list[dict[str, object]],
        recorder: RunRecorder,
        task_id: str,
        turn: int,
        context_config: ContextManagementConfig | None = None,
        provider_name: str = "generic",
        tool_result_artifact_index: ToolResultArtifactIndex | None = None,
    ) -> PreparedMessages:
        self.context_revision += 1
        config = context_config or ContextManagementConfig()
        (
            prepared_messages,
            reduction_data,
            candidate_records,
            candidate_replacement_text,
        ) = self._reduce_messages(
            messages,
            recorder,
            config,
            tool_result_artifact_index,
        )
        self._candidate_records_by_revision[self.context_revision] = candidate_records
        self._candidate_replacement_text_by_revision[
            self.context_revision
        ] = candidate_replacement_text
        model_input_hash = stable_hash(prepared_messages)
        internal_char_estimate_before = _internal_char_estimate(messages)
        internal_char_estimate = _internal_char_estimate(prepared_messages)
        internal_token_estimate_before = _char4_token_estimate_from_chars(
            internal_char_estimate_before
        )
        internal_token_estimate = _char4_token_estimate_from_chars(internal_char_estimate)
        provider_body_projection = _provider_body_projection(
            prepared_messages,
            provider_name=provider_name,
        )
        provider_body_char_estimate = _json_char_estimate(provider_body_projection)
        provider_ready_token_estimate = _char4_token_estimate_from_chars(
            provider_body_char_estimate
        )
        reduction_data = {
            **reduction_data,
            "provider_ready_token_estimate": provider_ready_token_estimate,
            "provider_body_char_estimate": provider_body_char_estimate,
            "internal_token_estimate_after": internal_token_estimate,
            "replacement_applied_but_insufficient_context_limit": bool(
                reduction_data.get("replaced_tool_result_ids")
                and provider_ready_token_estimate > config.max_context_tokens
            ),
        }
        pairing_validation = _validate_tool_pairing(prepared_messages)
        state_records = {
            **self._records_by_tool_result_id,
            **candidate_records,
        }
        state = ContentReplacementState(
            seen_tool_result_ids=sorted(state_records),
            records=[
                state_records[tool_result_id]
                for tool_result_id in sorted(state_records)
            ],
            state_hash=self._state_hash(state_records),
            last_context_revision=self.context_revision,
        )
        state_ref = recorder.write_json_artifact(
            "content_replacement_state",
            state.model_dump(mode="json"),
            {"budget_policy": "preserve_json"},
        )
        prepared_ref = recorder.write_json_artifact(
            "prepared_messages",
            {
                "messages": prepared_messages,
                "context_revision": self.context_revision,
                "model_input_hash": model_input_hash,
                "provider_format": "repo_harness_messages_v0",
                "provider_body_projection_format": "repo_harness_provider_body_projection_v1",
                "provider_body_char_estimate": provider_body_char_estimate,
                "provider_ready_token_estimate": provider_ready_token_estimate,
                "internal_char_estimate": internal_char_estimate,
                "internal_token_estimate": internal_token_estimate,
                "threshold_decision_source": "provider_ready_token_estimate",
                "content_replacement_state_ref": state_ref.model_dump(mode="json"),
            },
            {"budget_policy": "preserve_json"},
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
                "token_estimator_version": PROVIDER_READY_TOKEN_ESTIMATOR_VERSION,
                "provider_ready_token_estimator_version": PROVIDER_READY_TOKEN_ESTIMATOR_VERSION,
                "threshold_decision_source": "provider_ready_token_estimate",
                "tokens_before": _char4_token_estimate_from_chars(
                    _json_char_estimate(
                        _provider_body_projection(messages, provider_name=provider_name)
                    )
                ),
                "tokens_after": provider_ready_token_estimate,
                "provider_ready_token_estimate": provider_ready_token_estimate,
                "provider_body_char_estimate": provider_body_char_estimate,
                "provider_body_projection_format": "repo_harness_provider_body_projection_v1",
                "provider_returned_prompt_tokens": None,
                "provider_usage_metadata_status": "unavailable_before_provider_call",
                "estimator_error_ratio": None,
                "internal_char_estimate_before": internal_char_estimate_before,
                "internal_char_estimate_after": internal_char_estimate,
                "internal_token_estimate_before": internal_token_estimate_before,
                "internal_token_estimate_after": internal_token_estimate,
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
            token_estimate=provider_ready_token_estimate,
            token_estimator_version=PROVIDER_READY_TOKEN_ESTIMATOR_VERSION,
            internal_char_estimate=internal_char_estimate,
            internal_token_estimate=internal_token_estimate,
            provider_body_char_estimate=provider_body_char_estimate,
            provider_ready_token_estimate=provider_ready_token_estimate,
            provider_ready_token_estimator_version=PROVIDER_READY_TOKEN_ESTIMATOR_VERSION,
            threshold_decision_source="provider_ready_token_estimate",
        )

    def _reduce_messages(
        self,
        messages: list[dict[str, object]],
        recorder: RunRecorder,
        config: ContextManagementConfig,
        tool_result_artifact_index: ToolResultArtifactIndex | None,
    ) -> tuple[
        list[dict[str, object]],
        dict[str, Any],
        dict[str, ContentReplacementRecord],
        dict[str, str],
    ]:
        prepared: list[dict[str, object]] = []
        replaced_tool_result_ids: list[str] = []
        fresh_tool_result_ids: list[str] = []
        candidate_full_visible_tool_result_ids: list[str] = []
        already_persisted_tool_result_ids: list[str] = []
        reapplied_persisted_tool_result_ids: list[str] = []
        provider_committed_full_visible_tool_result_ids: list[str] = []
        replacement_refs: list[ArtifactRef] = []
        candidate_records: dict[str, ContentReplacementRecord] = {}
        candidate_replacement_text: dict[str, str] = {}
        tool_infos = _tool_message_infos(messages)
        internal_tokens_before_reduction = _char4_token_estimate_from_chars(
            _internal_char_estimate(messages)
        )
        fresh_infos = [
            info
            for info in tool_infos
            if str(info["tool_result_id"]) not in self._records_by_tool_result_id
            and not bool(info.get("already_persisted_preview"))
            and not bool(info.get("skip_tool_result_budget"))
        ]
        replace_tool_result_ids = _fresh_replacement_candidates_by_turn(
            fresh_infos,
            budget_chars=config.max_tool_results_per_turn_chars,
        )
        for message in messages:
            if message.get("role") != "tool":
                prepared.append(dict(message))
                continue
            tool_result_id = str(message.get("tool_result_id") or message.get("tool_call_id") or "")
            content = str(message.get("content", ""))
            committed_record = self._records_by_tool_result_id.get(tool_result_id)
            if committed_record is not None:
                if committed_record.replacement_decision == "provider_committed_persisted_preview":
                    replacement = self._replacement_text_by_tool_result_id.get(tool_result_id, content)
                    replaced = dict(message)
                    replaced["content"] = replacement
                    replaced["context_replacement"] = True
                    prepared.append(replaced)
                    replaced_tool_result_ids.append(tool_result_id)
                    reapplied_persisted_tool_result_ids.append(tool_result_id)
                    replacement_refs.extend(committed_record.replacement_artifact_refs)
                    continue
                provider_committed_full_visible_tool_result_ids.append(tool_result_id)
                prepared.append(dict(message))
                continue

            fresh_tool_result_ids.append(tool_result_id)
            if _is_persisted_tool_result_message(message):
                copied = dict(message)
                prepared.append(copied)
                already_persisted_tool_result_ids.append(tool_result_id)
                record = self._candidate_record_for_tool_result(
                    tool_result_id=tool_result_id,
                    message=message,
                    visible_content=content,
                    replaced=True,
                    replacement_artifact_refs=_artifact_refs_from_message(message),
                )
                candidate_records[tool_result_id] = record
                candidate_replacement_text[tool_result_id] = content
                replacement_refs.extend(record.replacement_artifact_refs)
                continue

            if tool_result_id in replace_tool_result_ids:
                replacement, ref = self._persisted_replacement_for_tool_result(
                    tool_result_id=tool_result_id,
                    message=message,
                    original_content=content,
                    recorder=recorder,
                    tool_result_artifact_index=tool_result_artifact_index,
                    reason="tool_result_aggregate_budget_exceeded",
                )
                replaced = dict(message)
                replaced["content"] = replacement
                replaced["context_replacement"] = True
                typed = dict(replaced.get("typed") or {})
                typed["aggregate_tool_result_persisted"] = True
                typed["aggregate_tool_result_original_chars"] = len(content)
                typed["aggregate_tool_result_artifact_id"] = ref.artifact_id
                typed["aggregate_tool_result_recovery_unlocked"] = False
                replaced["typed"] = typed
                replaced["artifact_refs"] = [
                    *[ref.model_dump(mode="json") for ref in _artifact_refs_from_message(message)],
                    ref.model_dump(mode="json"),
                ]
                prepared.append(replaced)
                replaced_tool_result_ids.append(tool_result_id)
                replacement_refs.append(ref)
                record = self._candidate_record_for_tool_result(
                    tool_result_id=tool_result_id,
                    message=message,
                    visible_content=replacement,
                    replaced=True,
                    replacement_artifact_refs=[ref],
                )
                candidate_records[tool_result_id] = record
                candidate_replacement_text[tool_result_id] = replacement
            else:
                candidate_full_visible_tool_result_ids.append(tool_result_id)
                candidate_records[tool_result_id] = self._candidate_record_for_tool_result(
                    tool_result_id=tool_result_id,
                    message=message,
                    visible_content=content,
                    replaced=False,
                    replacement_artifact_refs=[],
                )
                prepared.append(dict(message))
        return prepared, {
            "replaced_tool_result_ids": replaced_tool_result_ids,
            "fresh_tool_result_ids": fresh_tool_result_ids,
            "candidate_full_visible_tool_result_ids": candidate_full_visible_tool_result_ids,
            "already_persisted_tool_result_ids": already_persisted_tool_result_ids,
            "reapplied_persisted_tool_result_ids": reapplied_persisted_tool_result_ids,
            "provider_committed_full_visible_tool_result_ids": (
                provider_committed_full_visible_tool_result_ids
            ),
            "protected_tool_result_ids": [],
            "replacement_artifact_refs": [ref.model_dump(mode="json") for ref in replacement_refs],
            "context_replacement_runtime_policy_version": CONTEXT_REPLACEMENT_RUNTIME_POLICY_VERSION,
            "compact_threshold_ratio": config.compact_threshold_ratio,
            "compact_threshold_ratio_runtime_effect": "reserved_for_autocompact_v1",
            "tool_result_aggregate_budget_chars": config.tool_result_aggregate_budget_chars,
            "max_tool_results_per_turn_chars": config.max_tool_results_per_turn_chars,
            "effective_tool_result_aggregate_budget_chars": config.max_tool_results_per_turn_chars,
            "effective_budget_reason": "fresh_tool_results_grouped_by_turn",
            "legacy_history_tool_result_replacement": config.legacy_history_tool_result_replacement,
            "tool_result_compact_policy": config.tool_result_compact_policy,
            "freeze_tool_result_budget_decisions": config.freeze_tool_result_budget_decisions,
            "freeze_tool_result_decisions_at": config.freeze_tool_result_decisions_at,
            "prepared_candidate_tool_result_ids": sorted(candidate_records),
            "internal_tokens_before_reduction": internal_tokens_before_reduction,
            "replacement_preview_max_chars": REPLACEMENT_PREVIEW_MAX_CHARS,
            "replacement_preview_total_chars": sum(
                len(candidate_replacement_text.get(tool_result_id, ""))
                for tool_result_id in replaced_tool_result_ids
            ),
            "replacement_cooldown_policy": (
                "provider_committed_decisions_replayed_by_tool_result_id"
            ),
        }, candidate_records, candidate_replacement_text

    def _candidate_record_for_tool_result(
        self,
        *,
        tool_result_id: str,
        message: dict[str, object],
        visible_content: str,
        replaced: bool,
        replacement_artifact_refs: list[ArtifactRef],
    ) -> ContentReplacementRecord:
        return ContentReplacementRecord(
            tool_call_id=str(message.get("tool_call_id") or tool_result_id),
            original_tool_result_id=tool_result_id,
            replacement_decision="prepared_candidate",
            replaced=replaced,
            first_visible_form="replacement" if replaced else "full",
            first_visible_content_hash=stable_hash(visible_content),
            replacement_allowed_after_first_seen=True,
            replacement_text_hash=stable_hash(visible_content) if replaced else None,
            replacement_artifact_refs=replacement_artifact_refs,
            replacement_preview_hash=stable_hash(visible_content) if replaced else None,
            first_replaced_at_context_revision=self.context_revision if replaced else None,
            first_seen_at_context_revision=self.context_revision,
        )

    def _persisted_replacement_for_tool_result(
        self,
        *,
        tool_result_id: str,
        message: dict[str, object],
        original_content: str,
        recorder: RunRecorder,
        tool_result_artifact_index: ToolResultArtifactIndex | None,
        reason: str,
    ) -> tuple[str, ArtifactRef]:
        tool_name = str(
            message.get("effective_tool_name")
            or message.get("requested_tool_name")
            or message.get("tool_name")
            or "unknown_tool"
        )
        record = persist_tool_result_content(
            recorder=recorder,
            tool_result_id=tool_result_id,
            tool_call_id=str(message.get("tool_call_id") or tool_result_id),
            tool_name=tool_name,
            content=original_content,
            publishable_after_visibility_scan=True,
            contamination_scan_status="clean",
        )
        if tool_result_artifact_index is not None:
            tool_result_artifact_index.add(record)
        replacement = build_persisted_tool_result_preview(record, original_content)
        return replacement, record.artifact_ref

    def commit_prepared_tool_result_decisions(
        self,
        *,
        context_revision: int,
        prepared_messages_ref: ArtifactRef,
        model_call_id: str,
        tool_result_artifact_index: ToolResultArtifactIndex | None = None,
    ) -> dict[str, Any]:
        candidate_records = self._candidate_records_by_revision.pop(context_revision, {})
        candidate_replacement_text = self._candidate_replacement_text_by_revision.pop(
            context_revision,
            {},
        )
        committed_ids: list[str] = []
        committed_full_visible_ids: list[str] = []
        committed_persisted_preview_ids: list[str] = []
        unlocked_artifact_ids: list[str] = []
        for tool_result_id in sorted(candidate_records):
            candidate = candidate_records[tool_result_id]
            decision = (
                "provider_committed_persisted_preview"
                if candidate.replaced
                else "provider_committed_full_visible"
            )
            committed = candidate.model_copy(
                update={
                    "replacement_decision": decision,
                    "replacement_allowed_after_first_seen": False,
                }
            )
            self._records_by_tool_result_id[tool_result_id] = committed
            committed_ids.append(tool_result_id)
            if candidate.replaced:
                committed_persisted_preview_ids.append(tool_result_id)
                replacement_text = candidate_replacement_text.get(tool_result_id)
                if replacement_text is not None:
                    self._replacement_text_by_tool_result_id[tool_result_id] = replacement_text
                if tool_result_artifact_index is not None:
                    for artifact_ref in candidate.replacement_artifact_refs:
                        if artifact_ref.kind != "tool_result_original_content":
                            continue
                        if artifact_ref.artifact_id not in tool_result_artifact_index.records_by_artifact_id:
                            continue
                        tool_result_artifact_index.unlock_after_provider_commit(
                            artifact_ref.artifact_id
                        )
                        unlocked_artifact_ids.append(artifact_ref.artifact_id)
            else:
                committed_full_visible_ids.append(tool_result_id)
        committed_state = ContentReplacementState(
            seen_tool_result_ids=sorted(self._records_by_tool_result_id),
            records=[
                self._records_by_tool_result_id[tool_result_id]
                for tool_result_id in sorted(self._records_by_tool_result_id)
            ],
            state_hash=self._state_hash(self._records_by_tool_result_id),
            last_context_revision=context_revision,
        )
        return {
            "model_call_id": model_call_id,
            "context_revision": context_revision,
            "prepared_messages_ref": prepared_messages_ref.model_dump(mode="json"),
            "committed_tool_result_ids": committed_ids,
            "committed_full_visible_tool_result_ids": committed_full_visible_ids,
            "committed_persisted_preview_tool_result_ids": committed_persisted_preview_ids,
            "unlocked_tool_result_artifact_ids": unlocked_artifact_ids,
            "content_replacement_state": committed_state,
        }

    def _state_hash(
        self,
        records: dict[str, ContentReplacementRecord] | None = None,
    ) -> str:
        source = records if records is not None else self._records_by_tool_result_id
        return stable_hash(
            [
                source[tool_result_id].model_dump(mode="json")
                for tool_result_id in sorted(source)
            ]
        )


def _timestamp() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _head_tail(text: str, line_count: int = 3, max_chars: int = REPLACEMENT_PREVIEW_MAX_CHARS) -> tuple[str, str]:
    lines = text.splitlines()
    head = "\n".join(lines[:line_count])
    tail = "\n".join(lines[-line_count:]) if len(lines) > line_count else head
    per_side_budget = max(80, max_chars // 2)
    head = _truncate_preview_side(head, per_side_budget)
    tail = _truncate_preview_side(tail, per_side_budget)
    return head, tail


def _truncate_preview_side(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n[preview truncated]"


def _replacement_recovery(message: dict[str, object]) -> dict[str, Any]:
    tool_name = str(
        message.get("effective_tool_name")
        or message.get("requested_tool_name")
        or message.get("tool_name")
        or "unknown_tool"
    )
    normalized_arguments = _dict_value(message.get("normalized_arguments"))
    if not normalized_arguments:
        normalized_arguments = _dict_value(message.get("effective_arguments"))
    if not normalized_arguments:
        normalized_arguments = _dict_value(message.get("requested_arguments"))
    typed = _dict_value(message.get("typed"))
    normalized_arguments_sha256 = str(
        message.get("normalized_input_hash") or stable_hash(normalized_arguments)
    )
    recommended_call, recovery_hint = _recommended_recovery_call(
        tool_name=tool_name,
        arguments=normalized_arguments,
        typed=typed,
    )
    envelope = _dict_value(typed.get("result_envelope"))
    envelope_recovery_call = envelope.get("recovery_call")
    envelope_recovery_hint = envelope.get("recovery_hint")
    if isinstance(envelope_recovery_call, str) and envelope_recovery_call:
        recommended_call = envelope_recovery_call
    if isinstance(envelope_recovery_hint, str) and envelope_recovery_hint:
        recovery_hint = envelope_recovery_hint
    return {
        "tool_name": tool_name,
        "requested_tool_name": message.get("requested_tool_name") or message.get("tool_name"),
        "effective_tool_name": message.get("effective_tool_name") or tool_name,
        "normalized_arguments": normalized_arguments,
        "normalized_arguments_sha256": normalized_arguments_sha256,
        "key_arguments_preview": _json_preview(_key_arguments(tool_name, normalized_arguments, typed)),
        "recommended_call": recommended_call,
        "recovery_hint": recovery_hint,
    }


def _redacted_recovery(recovery: dict[str, Any]) -> dict[str, Any]:
    return {
        "tool_name": recovery.get("tool_name", "unknown_tool"),
        "requested_tool_name": recovery.get("requested_tool_name"),
        "effective_tool_name": recovery.get("effective_tool_name"),
        "normalized_arguments": {"redacted": True},
        "normalized_arguments_sha256": recovery.get("normalized_arguments_sha256"),
        "key_arguments_preview": '{"redacted":true}',
        "recommended_call": "not_available_evaluator_only_source_artifact",
        "recovery_hint": "Recovery arguments are redacted because the source artifact is evaluator-only or secret.",
    }


def _recommended_recovery_call(
    *,
    tool_name: str,
    arguments: dict[str, Any],
    typed: dict[str, Any],
) -> tuple[str, str]:
    if tool_name == "read_file":
        path = _string_arg(arguments, "path")
        next_start = typed.get("next_start_line")
        start_line = next_start if isinstance(next_start, int) else arguments.get("start_line")
        if not isinstance(start_line, int) or start_line <= 0:
            start_line = 1
        call = f"read_file(path={path!r}, start_line={start_line})"
        if isinstance(next_start, int):
            return call, "Continue reading from next_start_line to recover omitted content."
        return call, "Re-read this file range with read_file when the omitted content is needed."
    if tool_name == "grep":
        query = _string_arg(arguments, "query")
        mode = _string_arg(arguments, "mode", default="literal")
        root = _string_arg(arguments, "root", default=".")
        glob = _optional_string_arg(arguments, "glob")
        max_matches = arguments.get("max_matches")
        context_lines = arguments.get("context_lines")
        next_offset = typed.get("next_offset")
        offset = next_offset if isinstance(next_offset, int) else arguments.get("offset")
        if not isinstance(offset, int) or offset < 0:
            offset = 0
        parts = [f"query={query!r}", f"mode={mode!r}", f"root={root!r}", f"offset={offset}"]
        if glob:
            parts.append(f"glob={glob!r}")
        if isinstance(max_matches, int):
            parts.append(f"max_matches={max_matches}")
        if isinstance(context_lines, int):
            parts.append(f"context_lines={context_lines}")
        call = f"grep({', '.join(parts)})"
        if isinstance(next_offset, int):
            return call, "Use the next_offset page to continue the same search."
        return call, "Re-run or narrow the grep query, root, or glob to recover omitted matches."
    if tool_name == "list_files":
        root = _string_arg(arguments, "root", default=".")
        glob = _optional_string_arg(arguments, "glob")
        max_entries = arguments.get("max_entries")
        kind = _optional_string_arg(arguments, "kind")
        next_offset = typed.get("next_offset")
        offset = next_offset if isinstance(next_offset, int) else arguments.get("offset")
        if not isinstance(offset, int) or offset < 0:
            offset = 0
        parts = [f"root={root!r}", f"offset={offset}"]
        if glob:
            parts.append(f"glob={glob!r}")
        if kind:
            parts.append(f"kind={kind!r}")
        if isinstance(max_entries, int):
            parts.append(f"max_entries={max_entries}")
        call = f"list_files({', '.join(parts)})"
        if isinstance(next_offset, int):
            return call, "Use the next_offset page to continue listing files."
        return call, "Re-run list_files with the same root or a narrower glob."
    if tool_name == "git_diff":
        changed_files = typed.get("changed_files")
        path = _optional_string_arg(arguments, "path")
        if not path and isinstance(changed_files, list):
            path = next((str(item) for item in changed_files if item), None)
        if path:
            return f"git_diff(path={path!r})", "Re-run git_diff for this changed file."
        return "git_diff()", "Re-run git_diff to recover the current patch context."
    return (
        f"{tool_name}(...)",
        "Re-run the original tool with the same normalized arguments if the omitted content is needed.",
    )


def _key_arguments(tool_name: str, arguments: dict[str, Any], typed: dict[str, Any]) -> dict[str, Any]:
    if tool_name == "read_file":
        return {
            "path": arguments.get("path"),
            "start_line": arguments.get("start_line"),
            "end_line": typed.get("end_line"),
            "total_lines": typed.get("total_lines"),
            "next_start_line": typed.get("next_start_line"),
        }
    if tool_name == "grep":
        return {
            "query": arguments.get("query"),
            "mode": arguments.get("mode"),
            "root": arguments.get("root"),
            "glob": arguments.get("glob"),
            "offset": arguments.get("offset"),
            "max_matches": arguments.get("max_matches"),
            "context_lines": arguments.get("context_lines"),
            "next_offset": typed.get("next_offset"),
        }
    if tool_name == "list_files":
        return {
            "root": arguments.get("root"),
            "glob": arguments.get("glob"),
            "offset": arguments.get("offset"),
            "max_entries": arguments.get("max_entries"),
            "kind": arguments.get("kind"),
            "next_offset": typed.get("next_offset"),
        }
    if tool_name == "git_diff":
        return {
            "path": arguments.get("path"),
            "changed_files": typed.get("changed_files"),
        }
    return dict(arguments)


def _artifact_data_for_replacement(artifact_data: dict[str, Any]) -> dict[str, Any]:
    redaction_status = str(artifact_data.get("redaction_status") or "not_scanned")
    retention_policy = str(artifact_data.get("retention_policy") or "")
    kind = str(artifact_data.get("kind") or "")
    if (
        redaction_status in {"evaluator_only", "secret", "credential", "provider_raw"}
        or retention_policy
        in {
            "provider_raw_redacted",
            "provider_private_state_redacted",
            "provider_reasoning_trace_training_opt_in",
        }
        or kind in {"raw_provider_request", "raw_provider_response", "provider_private_state"}
    ):
        return {
            "artifact_id": "redacted_sensitive_artifact",
            "kind": "redacted_sensitive_artifact",
            "redaction_status": redaction_status,
            "retention_policy": retention_policy or None,
            "sha256_redacted": True,
            "redacted": True,
        }
    return dict(artifact_data)


def _replacement_sha256_for_model_visible_text(
    *,
    safe_artifact_data: dict[str, Any],
    original_content: str,
) -> str:
    if safe_artifact_data.get("redacted"):
        return "redacted_sensitive_artifact_sha256"
    sha256 = safe_artifact_data.get("sha256")
    if isinstance(sha256, str) and sha256:
        return sha256
    return stable_hash(original_content)


def _dict_value(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _string_arg(arguments: dict[str, Any], key: str, *, default: str = "") -> str:
    value = arguments.get(key)
    if isinstance(value, str) and value:
        return value
    return default


def _optional_string_arg(arguments: dict[str, Any], key: str) -> str | None:
    value = arguments.get(key)
    if isinstance(value, str) and value:
        return value
    return None


def _json_preview(value: dict[str, Any]) -> str:
    compact = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    if len(compact) <= 800:
        return compact
    return compact[:800] + "...[truncated]"


def _internal_char_estimate(value: Any) -> int:
    return len(str(value))


def _json_char_estimate(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def _char4_token_estimate_from_chars(chars: int) -> int:
    return max(1, chars // 4)


def _provider_body_projection(
    messages: list[dict[str, object]],
    *,
    provider_name: str,
) -> dict[str, Any]:
    return {
        "provider": provider_name,
        "projection_format": "repo_harness_provider_body_projection_v1",
        "messages": [_provider_message_projection(message) for message in messages],
    }


def _provider_message_projection(message: dict[str, object]) -> dict[str, Any]:
    projected: dict[str, Any] = {
        "role": message.get("role"),
        "content": message.get("content"),
    }
    for key in ("tool_call_id", "tool_calls", "name"):
        if key in message:
            projected[key] = message[key]
    metadata = message.get("metadata")
    if isinstance(metadata, dict) and "provider_private" in metadata:
        projected["metadata"] = {"provider_private": metadata["provider_private"]}
    return projected


def _effective_tool_result_budget_chars(
    *,
    config: ContextManagementConfig,
    internal_tokens_before_reduction: int,
) -> tuple[int, str]:
    base_budget = config.tool_result_aggregate_budget_chars
    if internal_tokens_before_reduction >= int(config.max_context_tokens * 0.9):
        return max(4000, base_budget // 4), "internal_estimate_at_or_above_90_percent_threshold"
    if internal_tokens_before_reduction >= int(
        config.max_context_tokens * config.compact_threshold_ratio
    ):
        return max(8000, base_budget // 2), "internal_estimate_at_or_above_compact_threshold"
    return base_budget, "below_compact_threshold"


def _tool_message_infos(messages: list[dict[str, object]]) -> list[dict[str, Any]]:
    infos: list[dict[str, Any]] = []
    inferred_turn: int | None = None
    for index, message in enumerate(messages):
        if message.get("role") == "assistant":
            inferred_turn = _message_turn(message, fallback=inferred_turn)
            continue
        if message.get("role") != "tool":
            continue
        tool_result_id = str(message.get("tool_result_id") or message.get("tool_call_id") or "")
        if not tool_result_id:
            continue
        turn = _message_turn(message, fallback=inferred_turn)
        infos.append(
            {
                "index": index,
                "tool_result_id": tool_result_id,
                "tool_call_id": str(message.get("tool_call_id") or tool_result_id),
                "tool_name": str(
                    message.get("effective_tool_name")
                    or message.get("requested_tool_name")
                    or message.get("tool_name")
                    or "unknown_tool"
                ),
                "content_chars": len(str(message.get("content", ""))),
                "turn": turn,
                "is_test_result": _is_test_result_message(message),
                "already_persisted_preview": _is_persisted_tool_result_message(message),
                "skip_tool_result_budget": (
                    str(message.get("effective_tool_name") or message.get("tool_name") or "")
                    == "read_tool_result_artifact"
                ),
            }
        )
    return infos


def _fresh_replacement_candidates_by_turn(
    tool_infos: list[dict[str, Any]],
    *,
    budget_chars: int,
) -> set[str]:
    replace_ids: set[str] = set()
    groups: dict[object, list[dict[str, Any]]] = {}
    for info in tool_infos:
        groups.setdefault(info.get("turn"), []).append(info)
    for group in groups.values():
        remaining = sum(int(info["content_chars"]) for info in group)
        if remaining <= budget_chars:
            continue
        for info in sorted(group, key=lambda item: int(item["content_chars"]), reverse=True):
            if remaining <= budget_chars:
                break
            tool_result_id = str(info["tool_result_id"])
            replace_ids.add(tool_result_id)
            remaining -= int(info["content_chars"])
    return replace_ids


def _artifact_refs_from_message(message: dict[str, object]) -> list[ArtifactRef]:
    refs: list[ArtifactRef] = []
    for raw in message.get("artifact_refs") or message.get("content_artifact_refs") or []:
        if isinstance(raw, ArtifactRef):
            refs.append(raw)
        elif isinstance(raw, dict):
            try:
                refs.append(ArtifactRef.model_validate(raw))
            except Exception:
                continue
    return refs


def _is_persisted_tool_result_message(message: dict[str, object]) -> bool:
    typed = message.get("typed")
    if isinstance(typed, dict) and (
        typed.get("single_tool_result_persisted")
        or typed.get("aggregate_tool_result_persisted")
    ):
        return True
    content = str(message.get("content", ""))
    if content.startswith("<persisted-output>"):
        return True
    return any(ref.kind == "tool_result_original_content" for ref in _artifact_refs_from_message(message))


def _protected_tool_result_ids(
    tool_infos: list[dict[str, Any]],
    *,
    keep_recent_turns: int,
    keep_recent_test_results: int,
) -> set[str]:
    protected: set[str] = set()
    turns = [info["turn"] for info in tool_infos if isinstance(info.get("turn"), int)]
    if keep_recent_turns > 0 and turns:
        oldest_kept_turn = max(turns) - keep_recent_turns + 1
        protected.update(
            str(info["tool_result_id"])
            for info in tool_infos
            if isinstance(info.get("turn"), int) and info["turn"] >= oldest_kept_turn
        )
    if keep_recent_test_results > 0:
        test_infos = [info for info in tool_infos if info.get("is_test_result")]
        protected.update(str(info["tool_result_id"]) for info in test_infos[-keep_recent_test_results:])
    return protected


def _replacement_candidates(
    tool_infos: list[dict[str, Any]],
    protected_tool_result_ids: set[str],
    *,
    existing_replacement_ids: set[str],
    budget_chars: int,
) -> set[str]:
    replace_ids = {
        str(info["tool_result_id"])
        for info in tool_infos
        if str(info["tool_result_id"]) in existing_replacement_ids
        and str(info["tool_result_id"]) not in protected_tool_result_ids
    }
    total_chars = sum(
        int(info["content_chars"])
        for info in tool_infos
        if str(info["tool_result_id"]) not in replace_ids
    )
    for info in tool_infos:
        tool_result_id = str(info["tool_result_id"])
        if total_chars <= budget_chars:
            break
        if tool_result_id in replace_ids or tool_result_id in protected_tool_result_ids:
            continue
        replace_ids.add(tool_result_id)
        total_chars -= int(info["content_chars"])
    return replace_ids


def _message_turn(message: dict[str, object], *, fallback: int | None) -> int | None:
    turn = message.get("turn")
    if isinstance(turn, int):
        return turn
    tool_calls = message.get("tool_calls")
    if isinstance(tool_calls, list):
        for tool_call in tool_calls:
            if isinstance(tool_call, dict) and isinstance(tool_call.get("turn"), int):
                return int(tool_call["turn"])
    return fallback


def _is_test_result_message(message: dict[str, object]) -> bool:
    if message.get("effective_tool_name") == "run_tests" or message.get("tool_name") == "run_tests":
        return True
    typed = message.get("typed")
    return isinstance(typed, dict) and "verifier_result_preview" in typed


def _validate_tool_pairing(messages: list[dict[str, object]]) -> dict[str, Any]:
    requested: list[str] = []
    observed: list[str] = []
    out_of_order: list[str] = []
    pending_block: list[str] = []
    pending_block_index: int | None = None
    for index, message in enumerate(messages):
        if message.get("role") == "assistant":
            if pending_block:
                out_of_order.extend(pending_block)
                pending_block = []
                pending_block_index = None
            for tool_call in message.get("tool_calls", []) or []:
                if isinstance(tool_call, dict) and tool_call.get("tool_call_id"):
                    tool_call_id = str(tool_call["tool_call_id"])
                    requested.append(tool_call_id)
                    pending_block.append(tool_call_id)
            if pending_block:
                pending_block_index = index
            continue
        if message.get("role") == "tool" and message.get("tool_call_id"):
            tool_call_id = str(message["tool_call_id"])
            observed.append(tool_call_id)
            if pending_block_index is None or not pending_block:
                out_of_order.append(tool_call_id)
            elif tool_call_id != pending_block[0]:
                out_of_order.append(tool_call_id)
            else:
                pending_block.pop(0)
                if not pending_block:
                    pending_block_index = None
            continue
        if pending_block:
            out_of_order.extend(pending_block)
            pending_block = []
            pending_block_index = None
    if pending_block:
        out_of_order.extend(pending_block)
    duplicate_requested = _duplicates(requested)
    duplicate_observed = _duplicates(observed)
    observed_set = set(observed)
    requested_set = set(requested)
    missing = [tool_call_id for tool_call_id in requested if tool_call_id not in observed_set]
    orphaned = [tool_call_id for tool_call_id in observed if tool_call_id not in requested_set]
    ok = not missing and not orphaned and not duplicate_requested and not duplicate_observed and not out_of_order
    return {
        "ok": ok,
        "missing_tool_result_ids": missing,
        "orphaned_tool_result_ids": orphaned,
        "duplicate_tool_call_ids": duplicate_requested,
        "duplicate_tool_result_ids": duplicate_observed,
        "out_of_order_tool_result_ids": out_of_order,
    }


def _duplicates(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for value in values:
        if value in seen and value not in duplicates:
            duplicates.append(value)
        seen.add(value)
    return duplicates
