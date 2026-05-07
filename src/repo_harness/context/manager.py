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
            {"budget_policy": "preserve_json"},
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
        replaced_tool_result_ids: list[str] = []
        replacement_refs: list[ArtifactRef] = []
        tool_infos = _tool_message_infos(messages)
        protected_tool_result_ids = _protected_tool_result_ids(
            tool_infos,
            keep_recent_turns=config.keep_recent_turns,
            keep_recent_test_results=config.keep_recent_test_results,
        )
        replace_tool_result_ids = _replacement_candidates(
            tool_infos,
            protected_tool_result_ids,
            existing_replacement_ids=set(self._replacement_text_by_tool_result_id),
            budget_chars=config.tool_result_aggregate_budget_chars,
        )
        for message in messages:
            if message.get("role") != "tool":
                prepared.append(dict(message))
                continue
            tool_result_id = str(message.get("tool_result_id") or message.get("tool_call_id") or "")
            content = str(message.get("content", ""))
            if tool_result_id in replace_tool_result_ids:
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
            "protected_tool_result_ids": sorted(protected_tool_result_ids),
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
        recovery = _replacement_recovery(message)
        safe_artifact_data = _artifact_data_for_replacement(artifact_data)
        include_preview = not safe_artifact_data.get("redacted")
        if not include_preview:
            recovery = _redacted_recovery(recovery)
        replacement_sha256 = _replacement_sha256_for_model_visible_text(
            safe_artifact_data=safe_artifact_data,
            original_content=original_content,
        )
        replacement = (
            f"[tool result replaced]\n"
            f"tool_result_id: {tool_result_id}\n"
            f"tool_name: {recovery['tool_name']}\n"
            f"artifact_id: {safe_artifact_data.get('artifact_id', 'none')}\n"
            f"sha256: {replacement_sha256}\n"
            f"reason: {reason}\n"
            f"normalized_arguments_sha256: {recovery['normalized_arguments_sha256']}\n"
            f"key_arguments: {recovery['key_arguments_preview']}\n"
            f"recovery_call: {recovery['recommended_call']}\n"
            f"recovery_hint: {recovery['recovery_hint']}\n"
        )
        if include_preview:
            replacement += f"head:\n{head}\n" f"tail:\n{tail}"
        else:
            replacement += "preview_redacted: source artifact is evaluator-only or secret\n"
        replacement_ref = recorder.write_json_artifact(
            "context_replacement",
            {
                "tool_result_id": tool_result_id,
                "replacement_preview": replacement,
                "reason": reason,
                "source_artifact_ref": safe_artifact_data,
                "recovery": recovery,
            },
            {"budget_policy": "preserve_json"},
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
                "content_chars": len(str(message.get("content", ""))),
                "turn": turn,
                "is_test_result": _is_test_result_message(message),
            }
        )
    return infos


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
