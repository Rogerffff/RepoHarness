"""Deterministic MicroCompact for old model-visible tool results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from repo_harness.config import ContextManagementConfig
from repo_harness.context.schemas import MicroCompactRecord
from repo_harness.schema_base import stable_hash

MICROCOMPACT_COMPACTABLE_TOOL_NAMES = frozenset(
    {
        "read_file",
        "grep",
        "list_files",
        "glob_files",
        "symbol_search",
        "git_diff",
    }
)


@dataclass(frozen=True)
class MicroCompactResult:
    messages: list[dict[str, object]]
    record: MicroCompactRecord | None


def apply_microcompact(
    *,
    messages: list[dict[str, object]],
    config: ContextManagementConfig,
    context_revision: int,
    eligible_tool_result_ids: set[str],
) -> MicroCompactResult:
    if not config.microcompact_enabled:
        return MicroCompactResult(messages=[dict(message) for message in messages], record=None)

    compactable = [
        _compactable_info(index=index, message=message, config=config)
        for index, message in enumerate(messages)
    ]
    compactable = [
        info
        for info in compactable
        if info is not None and info["tool_result_id"] in eligible_tool_result_ids
    ]
    compactable_count = len(compactable)
    compactable_chars = sum(int(info["content_chars"]) for info in compactable)
    if compactable_count < config.microcompact_trigger_compactable_tool_result_count:
        return MicroCompactResult(messages=[dict(message) for message in messages], record=None)
    if compactable_chars < config.microcompact_trigger_compactable_tool_result_chars:
        return MicroCompactResult(messages=[dict(message) for message in messages], record=None)

    keep_recent = config.microcompact_keep_recent_compactable_tool_results
    kept_infos = compactable[-keep_recent:] if keep_recent > 0 else []
    kept_ids = {str(info["tool_result_id"]) for info in kept_infos}
    cleared_infos = [info for info in compactable if str(info["tool_result_id"]) not in kept_ids]
    if not cleared_infos:
        return MicroCompactResult(messages=[dict(message) for message in messages], record=None)

    cleared_indexes = {int(info["index"]) for info in cleared_infos}
    cleared_ids = [str(info["tool_result_id"]) for info in cleared_infos]
    output: list[dict[str, object]] = []
    for index, message in enumerate(messages):
        if index not in cleared_indexes:
            output.append(dict(message))
            continue
        output.append(_cleared_message(message, config=config))

    record = MicroCompactRecord(
        context_revision=context_revision,
        compactable_tool_result_count_before=compactable_count,
        compactable_tool_result_chars_before=compactable_chars,
        cleared_tool_result_ids=cleared_ids,
        kept_recent_tool_result_ids=[str(info["tool_result_id"]) for info in kept_infos],
        cleared_message_hash=stable_hash(config.microcompact_cleared_message),
    )
    return MicroCompactResult(messages=output, record=record)


def _compactable_info(
    *,
    index: int,
    message: dict[str, object],
    config: ContextManagementConfig,
) -> dict[str, Any] | None:
    if message.get("role") != "tool":
        return None
    tool_result_id = str(message.get("tool_result_id") or message.get("tool_call_id") or "")
    if not tool_result_id:
        return None
    tool_name = str(
        message.get("effective_tool_name")
        or message.get("requested_tool_name")
        or message.get("tool_name")
        or ""
    )
    if tool_name not in MICROCOMPACT_COMPACTABLE_TOOL_NAMES:
        return None
    if tool_name == config.tool_result_recovery_tool:
        return None
    status = message.get("status")
    if isinstance(status, str) and status not in {"ok"}:
        return None
    content = str(message.get("content", ""))
    if content == config.microcompact_cleared_message:
        return None
    if content.startswith("<persisted-output>"):
        return None
    typed = message.get("typed")
    if isinstance(typed, dict) and (
        typed.get("single_tool_result_persisted")
        or typed.get("aggregate_tool_result_persisted")
        or typed.get("microcompact_cleared")
    ):
        return None
    return {
        "index": index,
        "tool_result_id": tool_result_id,
        "content_chars": len(content),
    }


def _cleared_message(
    message: dict[str, object],
    *,
    config: ContextManagementConfig,
) -> dict[str, object]:
    original_content = str(message.get("content", ""))
    cleared = dict(message)
    cleared["content"] = config.microcompact_cleared_message
    cleared["microcompact_cleared"] = True
    typed = dict(cleared.get("typed") or {})
    typed["microcompact_cleared"] = True
    typed["microcompact_policy"] = config.microcompact_policy
    typed["microcompact_original_chars"] = len(original_content)
    typed["microcompact_original_content_hash"] = stable_hash(original_content)
    typed["microcompact_recovery_status"] = _recovery_status(cleared)
    cleared["typed"] = typed
    return cleared


def _recovery_status(message: dict[str, object]) -> str:
    for raw in message.get("artifact_refs") or message.get("content_artifact_refs") or []:
        if isinstance(raw, dict) and raw.get("kind") == "tool_result_original_content":
            return "artifact_recoverable_if_unlocked"
        kind = getattr(raw, "kind", None)
        if kind == "tool_result_original_content":
            return "artifact_recoverable_if_unlocked"
    return "raw_trajectory_only"
