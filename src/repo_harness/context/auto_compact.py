"""AutoCompact runner and post-compact message rebuilding."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import ValidationError

from repo_harness.config import ContextManagementConfig
from repo_harness.context.budget import (
    build_provider_request_projection,
    estimate_provider_request_projection,
    resolve_context_budget,
)
from repo_harness.context.schemas import (
    AutoCompactRecord,
    AutoCompactResult,
    CompactSummary,
)
from repo_harness.context.tool_result_artifacts import ToolResultArtifactIndex
from repo_harness.model_client.protocol import ModelClient
from repo_harness.model_client.schemas import ModelProviderOptions, ModelRequestContext
from repo_harness.run_metadata import RunConfigFactsRef
from repo_harness.schema_base import stable_hash
from repo_harness.trajectory import ArtifactRef, RunRecorder, TrajectoryEvent
from repo_harness.v4_visibility import V4ContaminationDenylist

AUTO_COMPACT_POLICY_VERSION = "repo_harness_auto_compact_v1"
COMPACT_PROVIDER_MESSAGE_FORMAT = "repo_harness_compact_summary_request_v0"
POST_COMPACT_MESSAGE_FORMAT = "repo_harness_post_compact_messages_v0"


class AutoCompactRunner:
    """Runs a compact-only model call and rebuilds model-visible context."""

    def __init__(self) -> None:
        self._attempt_count = 0

    def run(
        self,
        *,
        mode: Literal["proactive", "hard_preflight", "emergency"],
        trigger_reason: str,
        source_prepared: Any,
        recorder: RunRecorder,
        task_id: str,
        turn: int,
        context_config: ContextManagementConfig,
        provider_options: ModelProviderOptions,
        model_client: ModelClient,
        tool_schema_snapshot_ref: ArtifactRef,
        run_config_facts_ref: RunConfigFactsRef,
        tool_result_artifact_index: ToolResultArtifactIndex | None = None,
        generation_config: dict[str, Any] | None = None,
        provider_model_settings: dict[str, Any] | None = None,
        budget_state: dict[str, Any] | None = None,
        request_timeout_seconds: float = 60.0,
        raw_request_logging_policy: str = "redact_secrets",
        retry_policy: str = "none",
        scaffold_id: str = "context_compaction",
    ) -> AutoCompactResult:
        self._attempt_count += 1
        compact_id = f"{recorder.run_id}_auto_compact_{turn:04d}_{self._attempt_count:02d}"
        generation_config = {
            **(generation_config or {}),
            "max_output_tokens": context_config.auto_compact_summary_max_output_tokens,
        }
        provider_model_settings = dict(provider_model_settings or {})
        context_budget = resolve_context_budget(
            config=context_config,
            provider=provider_options.provider,
            model_id=provider_options.model_id,
        )
        source_visible_messages = provider_visible_messages_for_compact(
            source_prepared.messages
        )
        compact_messages = _build_compact_request_messages(
            compact_id=compact_id,
            mode=mode,
            trigger_reason=trigger_reason,
            source_prepared=source_prepared,
            source_visible_messages=source_visible_messages,
        )
        compact_source_ref = recorder.write_json_artifact(
            "auto_compact_source_messages",
            {
                "schema_version": "repo_harness_auto_compact_source_messages_v1",
                "policy_version": AUTO_COMPACT_POLICY_VERSION,
                "compact_id": compact_id,
                "mode": mode,
                "trigger_reason": trigger_reason,
                "source_prepared_messages_ref": (
                    source_prepared.prepared_messages_ref.model_dump(mode="json")
                ),
                "source_model_input_hash": source_prepared.model_input_hash,
                "provider_visible_source_messages": source_visible_messages,
                "compact_request_messages": compact_messages,
                "provider_visible_projection_applied": True,
            },
            {"budget_policy": "preserve_json", "redaction_status": "not_sensitive"},
        )
        compact_projection = build_provider_request_projection(
            provider=provider_options.provider,
            model_id=provider_options.model_id,
            provider_message_format=COMPACT_PROVIDER_MESSAGE_FORMAT,
            messages=compact_messages,
            tools=[],
            tool_choice="none",
            generation_config=generation_config,
            provider_model_settings=provider_model_settings,
        )
        compact_projection_estimate = estimate_provider_request_projection(
            projection=compact_projection,
            budget_facts=context_budget,
        )
        tokens_before = _source_token_estimate(source_prepared)
        if (
            compact_projection_estimate.provider_request_token_estimate
            > context_budget.hard_context_limit_tokens
        ):
            return _failed_result(
                compact_id=compact_id,
                mode=mode,
                trigger_reason=trigger_reason,
                source_prepared=source_prepared,
                recorder=recorder,
                task_id=task_id,
                turn=turn,
                failure_reason="auto_compact_source_too_large",
                compact_source_messages_ref=compact_source_ref,
                compact_source_projection_hash=(
                    compact_projection_estimate.provider_request_projection_hash
                ),
                tokens_before=tokens_before,
                effective_context_budget_tokens=(
                    context_budget.effective_context_budget_tokens
                ),
                post_compact_target_tokens=context_budget.post_compact_target_tokens,
                hard_context_limit_tokens=context_budget.hard_context_limit_tokens,
            )

        compact_model_call_id = f"{compact_id}_model_call"
        recorder.append_event(
            TrajectoryEvent(
                event_id=recorder.next_event_id("auto_compact"),
                timestamp=_timestamp(),
                run_id=recorder.run_id,
                task_id=task_id,
                turn=turn,
                event_type="auto_compact_model_call_started",
                artifact_refs=[compact_source_ref],
                data={
                    "schema_version": "repo_harness_auto_compact_model_call_started_v1",
                    "policy_version": AUTO_COMPACT_POLICY_VERSION,
                    "compact_id": compact_id,
                    "mode": mode,
                    "trigger_reason": trigger_reason,
                    "model_call_id": compact_model_call_id,
                    "source_prepared_messages_ref": (
                        source_prepared.prepared_messages_ref.model_dump(mode="json")
                    ),
                    "compact_source_messages_ref": compact_source_ref.model_dump(
                        mode="json"
                    ),
                    "provider_request_projection_hash": (
                        compact_projection_estimate.provider_request_projection_hash
                    ),
                    "provider_request_projection_estimate": (
                        compact_projection_estimate.model_dump(mode="json")
                    ),
                    "scaffold_phase": "compact",
                    "allowed_tools": [],
                    "tool_choice": "none",
                    "trainable": False,
                },
            )
        )
        compact_request = ModelRequestContext(
            run_id=recorder.run_id,
            task_id=task_id,
            turn=turn,
            model_call_id=compact_model_call_id,
            prepared_messages=compact_messages,
            prepared_messages_ref=compact_source_ref,
            model_input_hash=stable_hash(compact_messages),
            context_revision=source_prepared.context_revision,
            provider_message_format=COMPACT_PROVIDER_MESSAGE_FORMAT,
            context_truncation_facts={
                "source_prepared_messages_ref": (
                    source_prepared.prepared_messages_ref.model_dump(mode="json")
                ),
                "source_model_input_hash": source_prepared.model_input_hash,
                "compact_id": compact_id,
            },
            omitted_context_facts={},
            generation_config=generation_config,
            provider_model_settings=provider_model_settings,
            allowed_tool_definitions=[],
            tool_choice="none",
            tool_schema_snapshot_ref=tool_schema_snapshot_ref,
            provider_options=provider_options,
            scaffold_id=scaffold_id,
            scaffold_phase="compact",
            run_config_facts_ref=run_config_facts_ref,
            budget_state=budget_state or {},
            request_timeout_seconds=request_timeout_seconds,
            raw_request_logging_policy=raw_request_logging_policy,
            credential_policy=provider_options.credential_policy,
            retry_policy=retry_policy,
            provider_request_projection_hash=(
                compact_projection_estimate.provider_request_projection_hash
            ),
            provider_request_token_estimate=(
                compact_projection_estimate.provider_request_token_estimate
            ),
            provider_request_token_estimate_breakdown=(
                compact_projection_estimate.model_dump(mode="json")
            ),
            context_budget_facts=context_budget.model_dump(mode="json"),
        )
        response = model_client.generate(request=compact_request, recorder=recorder)
        compact_model_call_ref = recorder.write_json_artifact(
            "auto_compact_model_call",
            {
                "schema_version": "repo_harness_auto_compact_model_call_v1",
                "policy_version": AUTO_COMPACT_POLICY_VERSION,
                "compact_id": compact_id,
                "model_call_id": compact_model_call_id,
                "trainable": False,
                "scaffold_phase": "compact",
                "allowed_tools": [],
                "tool_choice": "none",
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
                "model_error_type": response.model_error_type,
                "finish_reason": response.finish_reason,
            },
            {"budget_policy": "preserve_json", "redaction_status": "not_sensitive"},
        )
        recorder.append_event(
            TrajectoryEvent(
                event_id=recorder.next_event_id("auto_compact"),
                timestamp=_timestamp(),
                run_id=recorder.run_id,
                task_id=task_id,
                turn=turn,
                event_type="auto_compact_model_call_completed",
                artifact_refs=[
                    ref
                    for ref in [
                        compact_model_call_ref,
                        response.raw_provider_request_ref,
                        response.raw_provider_response_ref,
                    ]
                    if ref is not None
                ],
                data={
                    "schema_version": "repo_harness_auto_compact_model_call_completed_v1",
                    "policy_version": AUTO_COMPACT_POLICY_VERSION,
                    "compact_id": compact_id,
                    "model_call_id": compact_model_call_id,
                    "trainable": False,
                    "model_error_type": response.model_error_type,
                    "finish_reason": response.finish_reason,
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
        failure_reason = _compact_response_failure_reason(response)
        if failure_reason is not None:
            return _failed_result(
                compact_id=compact_id,
                mode=mode,
                trigger_reason=trigger_reason,
                source_prepared=source_prepared,
                recorder=recorder,
                task_id=task_id,
                turn=turn,
                failure_reason=failure_reason,
                compact_source_messages_ref=compact_source_ref,
                compact_source_projection_hash=(
                    compact_projection_estimate.provider_request_projection_hash
                ),
                compact_model_call_ref=compact_model_call_ref,
                compact_model_request_ref=response.raw_provider_request_ref,
                compact_model_response_ref=response.raw_provider_response_ref,
                tokens_before=tokens_before,
                effective_context_budget_tokens=(
                    context_budget.effective_context_budget_tokens
                ),
                post_compact_target_tokens=context_budget.post_compact_target_tokens,
                hard_context_limit_tokens=context_budget.hard_context_limit_tokens,
            )
        try:
            summary = _parse_compact_summary(response.assistant_message.content or "")
            _assert_summary_clean(summary)
            _validate_summary_recovery_index(
                summary,
                tool_result_artifact_index=tool_result_artifact_index,
            )
        except (ValueError, ValidationError) as exc:
            return _failed_result(
                compact_id=compact_id,
                mode=mode,
                trigger_reason=trigger_reason,
                source_prepared=source_prepared,
                recorder=recorder,
                task_id=task_id,
                turn=turn,
                failure_reason=f"invalid_compact_summary:{type(exc).__name__}",
                compact_source_messages_ref=compact_source_ref,
                compact_source_projection_hash=(
                    compact_projection_estimate.provider_request_projection_hash
                ),
                compact_model_call_ref=compact_model_call_ref,
                compact_model_request_ref=response.raw_provider_request_ref,
                compact_model_response_ref=response.raw_provider_response_ref,
                tokens_before=tokens_before,
                effective_context_budget_tokens=(
                    context_budget.effective_context_budget_tokens
                ),
                post_compact_target_tokens=context_budget.post_compact_target_tokens,
                hard_context_limit_tokens=context_budget.hard_context_limit_tokens,
            )
        summary_ref = recorder.write_json_artifact(
            "auto_compact_summary",
            {
                "schema_version": "repo_harness_auto_compact_summary_artifact_v1",
                "policy_version": AUTO_COMPACT_POLICY_VERSION,
                "compact_id": compact_id,
                "summary": summary.model_dump(mode="json"),
                "source_prepared_messages_ref": (
                    source_prepared.prepared_messages_ref.model_dump(mode="json")
                ),
                "source_model_input_hash": source_prepared.model_input_hash,
                "visibility_policy": "model_visible_only",
                "trainable": False,
            },
            {"budget_policy": "preserve_json", "redaction_status": "not_sensitive"},
        )
        rebuilt_messages = rebuild_messages_after_auto_compact(
            compact_id=compact_id,
            mode=mode,
            trigger_reason=trigger_reason,
            source_prepared=source_prepared,
            source_runtime_messages=source_prepared.messages,
            summary=summary,
            summary_ref=summary_ref,
            context_config=context_config,
            effective_context_budget_tokens=context_budget.effective_context_budget_tokens,
            post_compact_target_tokens=context_budget.post_compact_target_tokens,
            tool_result_artifact_index=tool_result_artifact_index,
        )
        rebuilt_ref = recorder.write_json_artifact(
            "auto_compact_rebuilt_messages",
            {
                "schema_version": "repo_harness_auto_compact_rebuilt_messages_v1",
                "policy_version": AUTO_COMPACT_POLICY_VERSION,
                "compact_id": compact_id,
                "messages": rebuilt_messages,
                "source_prepared_messages_ref": (
                    source_prepared.prepared_messages_ref.model_dump(mode="json")
                ),
                "summary_artifact_ref": summary_ref.model_dump(mode="json"),
                "trainable": False,
            },
            {"budget_policy": "preserve_json", "redaction_status": "not_sensitive"},
        )
        post_projection = build_provider_request_projection(
            provider=provider_options.provider,
            model_id=provider_options.model_id,
            provider_message_format=POST_COMPACT_MESSAGE_FORMAT,
            messages=rebuilt_messages,
            tools=[],
            tool_choice="none",
            generation_config={},
            provider_model_settings={},
        )
        post_estimate = estimate_provider_request_projection(
            projection=post_projection,
            budget_facts=context_budget,
        )
        post_compact_above_target = (
            post_estimate.provider_request_token_estimate
            > context_budget.post_compact_target_tokens
        )
        record_ref = _write_auto_compact_record(
            compact_id=compact_id,
            mode=mode,
            trigger_reason=trigger_reason,
            source_prepared=source_prepared,
            recorder=recorder,
            compact_source_messages_ref=compact_source_ref,
            compact_source_projection_hash=(
                compact_projection_estimate.provider_request_projection_hash
            ),
            tokens_before=tokens_before,
            tokens_after=post_estimate.provider_request_token_estimate,
            effective_context_budget_tokens=context_budget.effective_context_budget_tokens,
            summary_artifact_ref=summary_ref,
            compact_model_call_ref=compact_model_call_ref,
            rebuilt_messages_ref=rebuilt_ref,
            post_compact_above_target=post_compact_above_target,
            status="applied",
            failure_reason=None,
        )
        recorder.append_event(
            TrajectoryEvent(
                event_id=recorder.next_event_id("auto_compact"),
                timestamp=_timestamp(),
                run_id=recorder.run_id,
                task_id=task_id,
                turn=turn,
                event_type="auto_compact_applied",
                artifact_refs=[record_ref, summary_ref, rebuilt_ref],
                data={
                    "schema_version": "repo_harness_auto_compact_applied_v1",
                    "policy_version": AUTO_COMPACT_POLICY_VERSION,
                    "compact_id": compact_id,
                    "mode": mode,
                    "trigger_reason": trigger_reason,
                    "source_prepared_messages_ref": (
                        source_prepared.prepared_messages_ref.model_dump(mode="json")
                    ),
                    "summary_artifact_ref": summary_ref.model_dump(mode="json"),
                    "rebuilt_messages_ref": rebuilt_ref.model_dump(mode="json"),
                    "tokens_before": tokens_before,
                    "tokens_after": post_estimate.provider_request_token_estimate,
                    "effective_context_budget_tokens": (
                        context_budget.effective_context_budget_tokens
                    ),
                    "post_compact_target_tokens": (
                        context_budget.post_compact_target_tokens
                    ),
                    "hard_context_limit_tokens": context_budget.hard_context_limit_tokens,
                    "post_compact_above_target": post_compact_above_target,
                    "trainable": False,
                    "hidden_metadata_excluded": True,
                },
            )
        )
        return AutoCompactResult(
            compact_id=compact_id,
            mode=mode,
            trigger_reason=trigger_reason,
            status="applied",
            source_prepared_messages_ref=source_prepared.prepared_messages_ref,
            source_model_input_hash=source_prepared.model_input_hash,
            compact_source_messages_ref=compact_source_ref,
            compact_source_projection_hash=(
                compact_projection_estimate.provider_request_projection_hash
            ),
            compact_model_request_ref=response.raw_provider_request_ref,
            compact_model_response_ref=response.raw_provider_response_ref,
            summary_artifact_ref=summary_ref,
            rebuilt_messages_ref=rebuilt_ref,
            record_ref=record_ref,
            tokens_before=tokens_before,
            tokens_after=post_estimate.provider_request_token_estimate,
            effective_context_budget_tokens=context_budget.effective_context_budget_tokens,
            post_compact_target_tokens=context_budget.post_compact_target_tokens,
            hard_context_limit_tokens=context_budget.hard_context_limit_tokens,
            post_compact_above_target=post_compact_above_target,
            rebuilt_messages=rebuilt_messages,
            summary=summary,
        )


def provider_visible_messages_for_compact(
    messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [_provider_visible_message(message) for message in messages]


def runtime_messages_for_post_compact_rebuild(
    messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [_runtime_message_for_rebuild(message) for message in messages]


def rebuild_messages_after_auto_compact(
    *,
    compact_id: str,
    mode: str,
    trigger_reason: str,
    source_prepared: Any,
    source_runtime_messages: list[dict[str, Any]],
    summary: CompactSummary,
    summary_ref: ArtifactRef,
    context_config: ContextManagementConfig,
    effective_context_budget_tokens: int,
    post_compact_target_tokens: int,
    tool_result_artifact_index: ToolResultArtifactIndex | None = None,
) -> list[dict[str, Any]]:
    source_runtime_messages = runtime_messages_for_post_compact_rebuild(
        source_runtime_messages
    )
    foundation_messages, historical_messages = _split_foundation_messages(
        source_runtime_messages
    )
    preserved_tail = _select_preserved_tail(
        historical_messages,
        keep_recent_turns=context_config.preserve_recent_turns_after_compact,
        token_budget=_effective_tail_token_budget(
            context_config=context_config,
            effective_context_budget_tokens=effective_context_budget_tokens,
            post_compact_target_tokens=post_compact_target_tokens,
        ),
    )
    recovery_entries = _recoverable_tool_result_entries(tool_result_artifact_index)
    return [
        *foundation_messages,
        {
            "role": "user",
            "content": {
                "repo_harness_auto_compact_boundary": {
                    "schema_version": "repo_harness_auto_compact_boundary_message_v1",
                    "policy_version": AUTO_COMPACT_POLICY_VERSION,
                    "compact_id": compact_id,
                    "mode": mode,
                    "trigger_reason": trigger_reason,
                    "context_revision_before": source_prepared.context_revision,
                    "source_prepared_messages_ref": (
                        source_prepared.prepared_messages_ref.model_dump(mode="json")
                    ),
                    "source_model_input_hash": source_prepared.model_input_hash,
                    "summary_artifact_ref": summary_ref.model_dump(mode="json"),
                    "summarized_message_count": max(
                        0,
                        len(historical_messages) - len(preserved_tail),
                    ),
                    "preserved_message_count": len(preserved_tail),
                    "visibility_policy": "model_visible_only",
                }
            },
            "metadata": {
                "source": "repo_harness_auto_compact",
                "trainable": False,
                "compact_id": compact_id,
            },
        },
        {
            "role": "user",
            "content": {
                "repo_harness_auto_compact_summary": summary.model_dump(mode="json")
            },
            "metadata": {
                "source": "repo_harness_auto_compact",
                "trainable": False,
                "compact_id": compact_id,
            },
        },
        *preserved_tail,
        {
            "role": "user",
            "content": {
                "repo_harness_auto_compact_recovery_index": {
                    "schema_version": "repo_harness_auto_compact_recovery_index_v1",
                    "compact_id": compact_id,
                    "recovery_tool": "read_tool_result_artifact",
                    "recoverable_tool_results": recovery_entries,
                    "policy": (
                        "Only artifacts that passed visibility scanning and were unlocked "
                        "after provider commit are listed here."
                    ),
                }
            },
            "metadata": {
                "source": "repo_harness_auto_compact",
                "trainable": False,
                "compact_id": compact_id,
            },
        },
    ]


def _build_compact_request_messages(
    *,
    compact_id: str,
    mode: str,
    trigger_reason: str,
    source_prepared: Any,
    source_visible_messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    source_payload = {
        "compact_id": compact_id,
        "mode": mode,
        "trigger_reason": trigger_reason,
        "source_context_revision": source_prepared.context_revision,
        "source_model_input_hash": source_prepared.model_input_hash,
        "source_prepared_messages_ref": (
            source_prepared.prepared_messages_ref.model_dump(mode="json")
        ),
        "messages": source_visible_messages,
    }
    return [
        {
            "role": "system",
            "content": (
                "You are RepoHarness AutoCompact. Summarize only the model-visible "
                "context provided in the next message. Do not invent hidden tests, "
                "private reference fixes, private verifier logs, private scoring data, "
                "accepted outcomes, or evaluator-only metadata. Return only valid "
                "JSON matching the requested schema."
            ),
        },
        {
            "role": "user",
            "content": (
                "Create a context summary for continuing a software engineering task. "
                "The JSON object must contain: schema_version, task_intent, "
                "repository_facts, actions_taken, patch_state.changed_files, "
                "patch_state.important_diffs, test_state.commands_run, "
                "test_state.passing, test_state.failing, test_state.unknown, "
                "tool_recovery_index, open_questions, next_step, and "
                "visibility_policy='model_visible_only'.\n\n"
                f"MODEL_VISIBLE_SOURCE_CONTEXT:\n{json.dumps(source_payload, ensure_ascii=False, sort_keys=True)}"
            ),
        },
    ]


def _provider_visible_message(message: dict[str, Any]) -> dict[str, Any]:
    role = str(message.get("role") or "user")
    converted: dict[str, Any] = {"role": role}
    if "turn" in message:
        converted["turn"] = message.get("turn")
    if role == "assistant":
        converted["content"] = _content_to_string(message.get("content"))
        tool_calls = message.get("tool_calls") or []
        if isinstance(tool_calls, list) and tool_calls:
            converted["tool_calls"] = [
                _provider_visible_tool_call(call) for call in tool_calls
            ]
        return converted
    if role == "tool":
        converted["content"] = _content_to_string(message.get("content"))
        converted["tool_call_id"] = str(
            message.get("tool_call_id") or message.get("tool_result_id") or ""
        )
        return converted
    converted["content"] = _content_to_string(message.get("content"))
    return converted


def _runtime_message_for_rebuild(message: dict[str, Any]) -> dict[str, Any]:
    role = str(message.get("role") or "user")
    if role == "tool":
        return _runtime_tool_message_for_rebuild(message)
    allowed = {
        "role",
        "content",
        "turn",
        "tool_calls",
        "metadata",
        "model_error_type",
        "scaffold_phase",
    }
    return {key: value for key, value in message.items() if key in allowed}


def _runtime_tool_message_for_rebuild(message: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "role",
        "content",
        "turn",
        "tool_call_id",
        "tool_result_id",
        "tool_name",
        "requested_tool_name",
        "effective_tool_name",
        "normalized_input_hash",
        "status",
        "error_type",
        "artifact_refs",
        "content_artifact_refs",
    }
    rebuilt = {key: value for key, value in message.items() if key in allowed}
    typed = message.get("typed")
    if isinstance(typed, dict):
        safe_typed = {
            key: value
            for key, value in typed.items()
            if key.startswith("single_tool_result_")
            or key.startswith("aggregate_tool_result_")
        }
        if safe_typed:
            rebuilt["typed"] = safe_typed
    return rebuilt


def _provider_visible_tool_call(call: Any) -> dict[str, Any]:
    if hasattr(call, "model_dump"):
        call = call.model_dump(mode="json")
    if not isinstance(call, dict):
        call = {}
    function = call.get("function") if isinstance(call.get("function"), dict) else {}
    arguments = call.get("arguments", function.get("arguments", {}))
    return {
        "id": str(call.get("tool_call_id") or call.get("id") or ""),
        "type": "function",
        "function": {
            "name": str(call.get("tool_name") or function.get("name") or ""),
            "arguments": (
                arguments
                if isinstance(arguments, str)
                else json.dumps(arguments, ensure_ascii=False, sort_keys=True)
            ),
        },
    }


def _content_to_string(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False, sort_keys=True)


def _source_token_estimate(source_prepared: Any) -> int:
    for attr in (
        "provider_ready_token_estimate",
        "token_estimate",
        "internal_token_estimate",
    ):
        value = int(getattr(source_prepared, attr, 0) or 0)
        if value > 0:
            return value
    return max(1, len(json.dumps(source_prepared.messages, ensure_ascii=False)) // 4)


def _compact_response_failure_reason(response: Any) -> str | None:
    if response.model_error_type:
        return f"compact_model_error:{response.model_error_type}"
    if response.tool_calls:
        return "compact_model_returned_tool_calls"
    if not (response.assistant_message.content or "").strip():
        return "empty_compact_summary"
    return None


def _parse_compact_summary(content: str) -> CompactSummary:
    text = content.strip()
    if text.startswith("```"):
        text = _extract_fenced_json(text)
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("compact summary must be a JSON object")
    return CompactSummary.model_validate(payload)


def _extract_fenced_json(text: str) -> str:
    lines = text.splitlines()
    if len(lines) >= 3 and lines[0].startswith("```") and lines[-1].startswith("```"):
        return "\n".join(lines[1:-1]).strip()
    return text


def _assert_summary_clean(summary: CompactSummary) -> None:
    V4ContaminationDenylist().assert_clean(
        surface="context_compaction_or_replacement",
        payload=summary.model_dump(mode="json"),
        adapter_visible=False,
    )


def _validate_summary_recovery_index(
    summary: CompactSummary,
    *,
    tool_result_artifact_index: ToolResultArtifactIndex | None,
) -> None:
    for entry in summary.tool_recovery_index:
        if entry.recovery_status != "artifact_recoverable":
            continue
        if not entry.artifact_id:
            raise ValueError("artifact_recoverable entry requires artifact_id")
        if tool_result_artifact_index is None:
            raise ValueError("artifact_recoverable entry requires artifact index")
        record = tool_result_artifact_index.records_by_artifact_id.get(entry.artifact_id)
        if record is None or not record.model_visible_recoverable:
            raise ValueError("artifact_id is not unlocked for model recovery")
        if entry.sha256 is not None and entry.sha256 != record.content_sha256:
            raise ValueError("artifact recovery sha256 does not match index")
        if entry.tool_result_id is not None and entry.tool_result_id != record.tool_result_id:
            raise ValueError("artifact recovery tool_result_id does not match index")
        if entry.tool_call_id is not None and entry.tool_call_id != record.tool_call_id:
            raise ValueError("artifact recovery tool_call_id does not match index")
        if (
            entry.tool_name is not None
            and record.tool_name is not None
            and entry.tool_name != record.tool_name
        ):
            raise ValueError("artifact recovery tool_name does not match index")


def _split_foundation_messages(
    messages: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    foundation: list[dict[str, Any]] = []
    history_start = 0
    initial_user_kept = False
    for index, message in enumerate(messages):
        role = message.get("role")
        if role == "system" and not initial_user_kept:
            foundation.append(dict(message))
            history_start = index + 1
            continue
        if role == "user" and not initial_user_kept:
            foundation.append(dict(message))
            history_start = index + 1
            initial_user_kept = True
            continue
        break
    if not foundation and messages:
        foundation.append(dict(messages[0]))
        history_start = 1
    return foundation, [dict(message) for message in messages[history_start:]]


def _select_preserved_tail(
    messages: list[dict[str, Any]],
    *,
    keep_recent_turns: int,
    token_budget: int,
) -> list[dict[str, Any]]:
    if keep_recent_turns <= 0 or token_budget <= 0:
        return []
    groups = _message_groups_by_turn(messages)
    selected: list[list[dict[str, Any]]] = []
    total = 0
    for group in reversed(groups[-keep_recent_turns:]):
        group_tokens = max(1, len(json.dumps(group, ensure_ascii=False)) // 4)
        if selected and total + group_tokens > token_budget:
            break
        if not selected and group_tokens > token_budget:
            break
        selected.insert(0, group)
        total += group_tokens
    flattened = [dict(message) for group in selected for message in group]
    return _drop_orphaned_tool_boundary(flattened)


def _message_groups_by_turn(messages: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    groups: list[list[dict[str, Any]]] = []
    current_turn: Any = object()
    for message in messages:
        turn = message.get("turn")
        if turn is None:
            groups.append([message])
            current_turn = object()
            continue
        if not groups or turn != current_turn:
            groups.append([message])
            current_turn = turn
        else:
            groups[-1].append(message)
    return groups


def _drop_orphaned_tool_boundary(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    trimmed = list(messages)
    while trimmed and trimmed[0].get("role") == "tool":
        trimmed.pop(0)
    return trimmed


def _effective_tail_token_budget(
    *,
    context_config: ContextManagementConfig,
    effective_context_budget_tokens: int,
    post_compact_target_tokens: int,
) -> int:
    return max(
        0,
        min(
            context_config.preserve_recent_tail_token_budget,
            int(post_compact_target_tokens * 0.50),
            int(effective_context_budget_tokens * 0.35),
        ),
    )


def _recoverable_tool_result_entries(
    tool_result_artifact_index: ToolResultArtifactIndex | None,
) -> list[dict[str, Any]]:
    if tool_result_artifact_index is None:
        return []
    entries = []
    for record in tool_result_artifact_index.records_by_artifact_id.values():
        if not record.model_visible_recoverable:
            continue
        entries.append(
            {
                "artifact_id": record.artifact_id,
                "tool_result_id": record.tool_result_id,
                "tool_call_id": record.tool_call_id,
                "tool_name": record.tool_name,
                "sha256": record.content_sha256,
                "size_chars": record.size_chars,
                "recovery_call": (
                    "read_tool_result_artifact("
                    f"artifact_id={record.artifact_id!r}, offset=0, limit=8000)"
                ),
            }
        )
    return entries


def _failed_result(
    *,
    compact_id: str,
    mode: Literal["proactive", "hard_preflight", "emergency"],
    trigger_reason: str,
    source_prepared: Any,
    recorder: RunRecorder,
    task_id: str,
    turn: int,
    failure_reason: str,
    compact_source_messages_ref: ArtifactRef | None,
    compact_source_projection_hash: str | None,
    tokens_before: int,
    effective_context_budget_tokens: int,
    post_compact_target_tokens: int,
    hard_context_limit_tokens: int,
    compact_model_call_ref: ArtifactRef | None = None,
    compact_model_request_ref: ArtifactRef | None = None,
    compact_model_response_ref: ArtifactRef | None = None,
) -> AutoCompactResult:
    record_ref = _write_auto_compact_record(
        compact_id=compact_id,
        mode=mode,
        trigger_reason=trigger_reason,
        source_prepared=source_prepared,
        recorder=recorder,
        compact_source_messages_ref=compact_source_messages_ref,
        compact_source_projection_hash=compact_source_projection_hash,
        tokens_before=tokens_before,
        tokens_after=tokens_before,
        effective_context_budget_tokens=effective_context_budget_tokens,
        summary_artifact_ref=None,
        compact_model_call_ref=compact_model_call_ref,
        rebuilt_messages_ref=None,
        post_compact_above_target=False,
        status="failed",
        failure_reason=failure_reason,
    )
    recorder.append_event(
        TrajectoryEvent(
            event_id=recorder.next_event_id("auto_compact"),
            timestamp=_timestamp(),
            run_id=recorder.run_id,
            task_id=task_id,
            turn=turn,
            event_type="auto_compact_failed",
            severity="warning",
            error_type=failure_reason,
            artifact_refs=[
                ref
                for ref in [
                    record_ref,
                    compact_source_messages_ref,
                    compact_model_call_ref,
                    compact_model_request_ref,
                    compact_model_response_ref,
                ]
                if ref is not None
            ],
            data={
                "schema_version": "repo_harness_auto_compact_failed_v1",
                "policy_version": AUTO_COMPACT_POLICY_VERSION,
                "compact_id": compact_id,
                "mode": mode,
                "trigger_reason": trigger_reason,
                "failure_reason": failure_reason,
                "source_prepared_messages_ref": (
                    source_prepared.prepared_messages_ref.model_dump(mode="json")
                ),
                "compact_source_messages_ref": (
                    compact_source_messages_ref.model_dump(mode="json")
                    if compact_source_messages_ref
                    else None
                ),
                "compact_source_projection_hash": compact_source_projection_hash,
                "tokens_before": tokens_before,
                "effective_context_budget_tokens": effective_context_budget_tokens,
                "post_compact_target_tokens": post_compact_target_tokens,
                "hard_context_limit_tokens": hard_context_limit_tokens,
                "trainable": False,
            },
        )
    )
    return AutoCompactResult(
        compact_id=compact_id,
        mode=mode,
        trigger_reason=trigger_reason,
        status="failed",
        failure_reason=failure_reason,
        source_prepared_messages_ref=source_prepared.prepared_messages_ref,
        source_model_input_hash=source_prepared.model_input_hash,
        compact_source_messages_ref=compact_source_messages_ref,
        compact_source_projection_hash=compact_source_projection_hash,
        compact_model_request_ref=compact_model_request_ref,
        compact_model_response_ref=compact_model_response_ref,
        record_ref=record_ref,
        tokens_before=tokens_before,
        tokens_after=tokens_before,
        effective_context_budget_tokens=effective_context_budget_tokens,
        post_compact_target_tokens=post_compact_target_tokens,
        hard_context_limit_tokens=hard_context_limit_tokens,
    )


def _write_auto_compact_record(
    *,
    compact_id: str,
    mode: Literal["proactive", "hard_preflight", "emergency"],
    trigger_reason: str,
    source_prepared: Any,
    recorder: RunRecorder,
    compact_source_messages_ref: ArtifactRef | None,
    compact_source_projection_hash: str | None,
    tokens_before: int,
    tokens_after: int,
    effective_context_budget_tokens: int,
    summary_artifact_ref: ArtifactRef | None,
    compact_model_call_ref: ArtifactRef | None,
    rebuilt_messages_ref: ArtifactRef | None,
    post_compact_above_target: bool,
    status: Literal["applied", "failed", "skipped"],
    failure_reason: str | None,
) -> ArtifactRef:
    record = AutoCompactRecord(
        compact_id=compact_id,
        trigger_reason=trigger_reason,
        mode=mode,
        source_prepared_messages_ref=source_prepared.prepared_messages_ref,
        source_model_input_hash=source_prepared.model_input_hash,
        compact_source_messages_ref=compact_source_messages_ref,
        compact_source_projection_hash=compact_source_projection_hash,
        tokens_before=tokens_before,
        tokens_after=tokens_after,
        effective_context_budget_tokens=effective_context_budget_tokens,
        summary_artifact_ref=summary_artifact_ref,
        compact_model_call_ref=compact_model_call_ref,
        rebuilt_messages_ref=rebuilt_messages_ref,
        post_compact_above_target=post_compact_above_target,
        status=status,
        failure_reason=failure_reason,
    )
    return recorder.write_json_artifact(
        "auto_compact_record",
        record.model_dump(mode="json"),
        {"budget_policy": "preserve_json", "redaction_status": "not_sensitive"},
    )


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = [
    "AUTO_COMPACT_POLICY_VERSION",
    "AutoCompactRunner",
    "provider_visible_messages_for_compact",
    "rebuild_messages_after_auto_compact",
    "runtime_messages_for_post_compact_rebuild",
]
