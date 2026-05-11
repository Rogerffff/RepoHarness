"""Deterministic mock provider client for provider protocol tests."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from repo_harness.model_client.schemas import (
    ModelCallEvent,
    ModelMessage,
    ModelRequestContext,
    ModelResponse,
)
from repo_harness.model_client.redaction import REDACTED_CREDENTIAL, redact_provider_payload
from repo_harness.schema_base import stable_hash
from repo_harness.tools import ToolCall
from repo_harness.trajectory import RunRecorder

MOCK_PROVIDER_VERSION = "repo_harness_mock_provider_v0"

ERROR_SCENARIOS = {
    "auth_error": "auth_error",
    "rate_limit": "rate_limited",
    "timeout": "provider_timeout",
    "invalid_response": "invalid_response",
    "malformed_tool_call": "tool_call_parse_failure",
    "context_limit": "context_limit",
    "provider_error": "provider_error",
}


class MockProviderClient:
    def generate(self, *, request: ModelRequestContext, recorder: RunRecorder) -> ModelResponse:
        scenario = str(request.provider_options.provider_specific_options.get("mock_scenario", "tool_call_success"))
        raw_request_ref = recorder.write_json_artifact(
            "raw_mock_provider_request",
            _mock_request_payload(request, scenario=scenario),
            {
                "redaction_status": "redacted",
                "retention_policy": "provider_raw_redacted",
                "budget_policy": "preserve_json",
            },
        )
        if scenario in ERROR_SCENARIOS:
            model_error_type = ERROR_SCENARIOS[scenario]
            raw_response_ref = recorder.write_json_artifact(
                "raw_mock_provider_response",
                {
                    "schema_version": "repo_harness_mock_provider_response_v0",
                    "provider": "mock",
                    "scenario": scenario,
                    "status": "error",
                    "model_error_type": model_error_type,
                    "message": _error_message(model_error_type),
                    "authorization": REDACTED_CREDENTIAL,
                    "checked_at": _timestamp(),
                },
                {
                    "redaction_status": "redacted",
                    "retention_policy": "provider_raw_redacted",
                    "budget_policy": "preserve_json",
                },
            )
            return _response(
                request=request,
                raw_request_ref=raw_request_ref,
                raw_response_ref=raw_response_ref,
                assistant=ModelMessage(role="assistant", content=_error_message(model_error_type)),
                finish_reason="error",
                model_error_type=model_error_type,
                provider_request_id=f"mock-{scenario}-{request.turn}",
            )
        if scenario == "final_answer":
            assistant = ModelMessage(role="assistant", content="Mock provider final answer.")
            tool_calls: list[ToolCall] = []
            finish_reason = "stop"
        else:
            assistant, tool_calls, finish_reason = _tool_call_response(request)
        raw_response_ref = recorder.write_json_artifact(
            "raw_mock_provider_response",
            {
                "schema_version": "repo_harness_mock_provider_response_v0",
                "provider": "mock",
                "scenario": scenario,
                "status": "ok",
                "finish_reason": finish_reason,
                "assistant_message": assistant.model_dump(mode="json"),
                "tool_calls": [call.model_dump(mode="json") for call in tool_calls],
                "usage": {"input_tokens": _token_estimate(request.prepared_messages), "output_tokens": 16},
                "authorization": REDACTED_CREDENTIAL,
                "checked_at": _timestamp(),
            },
            {
                "redaction_status": "redacted",
                "retention_policy": "provider_raw_redacted",
                "budget_policy": "preserve_json",
            },
        )
        return _response(
            request=request,
            raw_request_ref=raw_request_ref,
            raw_response_ref=raw_response_ref,
            assistant=assistant,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
            provider_request_id=f"mock-{scenario}-{request.turn}",
        )


def _tool_call_response(request: ModelRequestContext) -> tuple[ModelMessage, list[ToolCall], str]:
    if _has_successful_feedback_observation(request.prepared_messages):
        return (
            ModelMessage(
                role="assistant",
                content="Mock provider completed the patch after accepted feedback.",
            ),
            [],
            "stop",
        )
    if _has_successful_edit_observation(request.prepared_messages):
        call = ToolCall(
            tool_call_id=f"mock_run_tests_{request.turn}",
            tool_name="run_tests",
            arguments={},
            turn=request.turn,
        )
    else:
        call = ToolCall(
            tool_call_id=f"mock_edit_{request.turn}",
            tool_name="edit_file",
            arguments={
                "path": "calculator.py",
                "old_text": "def divide(left: int, right: int) -> float:\n    return left / right\n",
                "new_text": (
                    "def divide(left: int, right: int) -> float:\n"
                    "    if right == 0:\n"
                    "        raise ValueError(\"division by zero\")\n"
                    "    return left / right\n"
                ),
            },
            turn=request.turn,
        )
    assistant = ModelMessage(role="assistant", content=None, tool_calls=[call])
    return assistant, [call], "tool_calls"


def _has_successful_edit_observation(messages: list[dict[str, Any]]) -> bool:
    for message in reversed(messages):
        if message.get("role") != "tool":
            continue
        if message.get("effective_tool_name") == "edit_file" and message.get("status") == "ok":
            return True
        if "Edited calculator.py" in str(message.get("content", "")):
            return True
    return False


def _has_successful_feedback_observation(messages: list[dict[str, Any]]) -> bool:
    for message in reversed(messages):
        if message.get("role") != "tool":
            continue
        typed = message.get("typed")
        if not isinstance(typed, dict):
            continue
        preview = typed.get("verifier_result_preview")
        if isinstance(preview, dict) and preview.get("accepted") is True:
            return True
    return False


def _mock_request_payload(request: ModelRequestContext, *, scenario: str) -> dict[str, Any]:
    return {
        "schema_version": "repo_harness_mock_provider_request_v0",
        "provider": "mock",
        "mock_provider_version": MOCK_PROVIDER_VERSION,
        "mock_scenario": scenario,
        "model_call_id": request.model_call_id,
        "model_id": request.provider_options.model_id,
        "provider_request_projection_hash": request.provider_request_projection_hash,
        "provider_request_token_estimate": request.provider_request_token_estimate,
        "provider_request_token_estimate_breakdown": (
            request.provider_request_token_estimate_breakdown
        ),
        "context_budget_facts": request.context_budget_facts,
        "messages": request.prepared_messages,
        "tools": request.allowed_tool_definitions,
        "tool_choice": request.tool_choice,
        "tool_schema_snapshot_ref": request.tool_schema_snapshot_ref.model_dump(mode="json"),
        "generation_config": redact_provider_payload(request.generation_config),
        "provider_model_settings": redact_provider_payload(request.provider_model_settings),
        "provider_options": _redacted_provider_options(request),
        "scaffold_id": request.scaffold_id,
        "scaffold_phase": request.scaffold_phase,
        "request_timeout_seconds": request.request_timeout_seconds,
        "request_timeout_policy_facts": request.request_timeout_policy_facts,
        "raw_request_logging_policy": request.raw_request_logging_policy,
        "credential_policy": redact_provider_payload(request.credential_policy.model_dump(mode="json")),
        "authorization": REDACTED_CREDENTIAL,
    }


def _redacted_provider_options(request: ModelRequestContext) -> dict[str, Any]:
    options = redact_provider_payload(request.provider_options.model_dump(mode="json"))
    options["credential_policy"] = redact_provider_payload(request.credential_policy.model_dump(mode="json"))
    options["authorization"] = REDACTED_CREDENTIAL
    return options


def _response(
    *,
    request: ModelRequestContext,
    raw_request_ref,
    raw_response_ref,
    assistant: ModelMessage,
    tool_calls: list[ToolCall] | None = None,
    finish_reason: str,
    model_error_type: str | None = None,
    provider_request_id: str | None = None,
) -> ModelResponse:
    input_tokens = _token_estimate(request.prepared_messages)
    output_tokens = 0 if model_error_type else 16
    event = ModelCallEvent(
        model_call_id=request.model_call_id,
        provider="mock",
        model_id=request.provider_options.model_id,
        provider_request_id=provider_request_id,
        context_revision=request.context_revision,
        prepared_messages_ref=request.prepared_messages_ref,
        model_input_hash=request.model_input_hash,
        provider_message_format=request.provider_message_format,
        tool_schema_hash=stable_hash(request.allowed_tool_definitions),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_tokens=0,
        duration_ms=0,
        request_timeout_seconds=request.request_timeout_seconds,
        request_timeout_policy_facts=request.request_timeout_policy_facts,
        retry_count=0,
        model_error_type=model_error_type,
    )
    return ModelResponse(
        assistant_message=assistant,
        tool_calls=tool_calls or [],
        raw_provider_request_ref=raw_request_ref,
        raw_provider_response_ref=raw_response_ref,
        token_usage={"input_tokens": input_tokens, "output_tokens": output_tokens},
        finish_reason=finish_reason,
        model_error_type=model_error_type,
        provider_request_id=provider_request_id,
        model_call_event=event,
    )


def _error_message(model_error_type: str) -> str:
    return f"mock provider returned structured error: {model_error_type}"


def _token_estimate(value: Any) -> int:
    return max(1, len(str(value)) // 4)


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()
