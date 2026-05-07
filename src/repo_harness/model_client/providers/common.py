"""Shared OpenAI-compatible provider helpers."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from repo_harness.model_client.redaction import (
    REDACTED_CREDENTIAL,
    redact_provider_payload,
    sanitize_provider_error_message,
)
from repo_harness.model_client.provider_private_state import deepseek_reasoning_from_metadata
from repo_harness.model_client.schemas import (
    ModelCallEvent,
    ModelMessage,
    ModelRequestContext,
    ModelResponse,
)
from repo_harness.schema_base import stable_hash
from repo_harness.tools import ToolCall
from repo_harness.trajectory import ArtifactRef, RunRecorder

PROVIDER_ARTIFACT_RETENTION_POLICY = "provider_raw_redacted"
OPENAI_COMPATIBLE_MESSAGE_FORMAT_VERSION = "repo_harness_openai_compatible_chat_v0"
TOOL_CALL_PARSER_VERSION = "repo_harness_openai_compatible_tool_parser_v0"


@dataclass(frozen=True)
class ProviderErrorInfo:
    model_error_type: str
    message: str
    status_code: int | None = None
    retryable: bool = False
    provider_request_id: str | None = None
    payload: dict[str, Any] | None = None


class ProviderRequestError(Exception):
    def __init__(self, info: ProviderErrorInfo) -> None:
        super().__init__(info.message)
        self.info = info


@dataclass(frozen=True)
class ProviderCredential:
    value: str
    source: str
    status: str = "present"


def build_chat_completion_payload(
    request: ModelRequestContext,
    *,
    model_id: str,
    provider: str,
    base_url: str,
    include_deepseek_options: bool = False,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model_id,
        "messages": [
            _to_chat_message(message, provider=provider)
            for message in request.prepared_messages
        ],
        "stream": False,
    }
    tools = [_to_chat_tool(tool) for tool in request.allowed_tool_definitions]
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = request.tool_choice or "auto"
    else:
        payload["tool_choice"] = "none"
    if "temperature" in request.generation_config:
        payload["temperature"] = request.generation_config["temperature"]
    max_output_tokens = request.generation_config.get("max_output_tokens")
    if max_output_tokens is not None:
        payload["max_tokens"] = max_output_tokens
    provider_options = request.provider_options.provider_specific_options
    if include_deepseek_options:
        thinking = provider_options.get("thinking")
        if thinking is not None:
            payload["extra_body"] = {"thinking": thinking}
        reasoning_effort = provider_options.get("reasoning_effort")
        if reasoning_effort is not None:
            payload["reasoning_effort"] = reasoning_effort
    return {
        "schema_version": "repo_harness_provider_chat_completion_request_v0",
        "provider": provider,
        "base_url": base_url,
        "body": payload,
        "tool_schema_snapshot_ref": request.tool_schema_snapshot_ref.model_dump(mode="json"),
        "model_call_id": request.model_call_id,
        "request_timeout_seconds": request.request_timeout_seconds,
        "raw_request_logging_policy": request.raw_request_logging_policy,
        "credential_policy": request.credential_policy.model_dump(mode="json"),
        "authorization": REDACTED_CREDENTIAL,
    }


def write_provider_request_artifact(
    *,
    provider: str,
    recorder: RunRecorder,
    payload: dict[str, Any],
) -> ArtifactRef:
    return recorder.write_json_artifact(
        f"raw_{provider}_provider_request",
        {
            "export_allowed": False,
            "training_payload_allowed": False,
            **redact_provider_payload(payload),
        },
        {
            "redaction_status": "redacted",
            "retention_policy": PROVIDER_ARTIFACT_RETENTION_POLICY,
            "budget_policy": "preserve_json",
        },
    )


def write_provider_response_artifact(
    *,
    provider: str,
    recorder: RunRecorder,
    payload: dict[str, Any],
) -> ArtifactRef:
    return recorder.write_json_artifact(
        f"raw_{provider}_provider_response",
        {
            "export_allowed": False,
            "training_payload_allowed": False,
            **redact_provider_payload(payload),
        },
        {
            "redaction_status": "redacted",
            "retention_policy": PROVIDER_ARTIFACT_RETENTION_POLICY,
            "budget_policy": "preserve_json",
        },
    )


def response_from_provider_payload(
    *,
    provider: str,
    request: ModelRequestContext,
    raw_request_ref: ArtifactRef,
    raw_response_ref: ArtifactRef,
    payload: dict[str, Any],
    duration_ms: int,
    provider_request_id: str | None = None,
) -> ModelResponse:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return model_error_response(
            provider=provider,
            request=request,
            raw_request_ref=raw_request_ref,
            raw_response_ref=raw_response_ref,
            error=ProviderErrorInfo(
                model_error_type="invalid_response",
                message="provider response did not contain choices",
                provider_request_id=provider_request_id or _payload_request_id(payload),
                payload=payload,
            ),
            duration_ms=duration_ms,
        )
    choice = choices[0]
    if not isinstance(choice, dict):
        return model_error_response(
            provider=provider,
            request=request,
            raw_request_ref=raw_request_ref,
            raw_response_ref=raw_response_ref,
            error=ProviderErrorInfo(
                model_error_type="invalid_response",
                message="provider choice was not an object",
                provider_request_id=provider_request_id or _payload_request_id(payload),
                payload=payload,
            ),
            duration_ms=duration_ms,
        )
    message = choice.get("message")
    if not isinstance(message, dict):
        return model_error_response(
            provider=provider,
            request=request,
            raw_request_ref=raw_request_ref,
            raw_response_ref=raw_response_ref,
            error=ProviderErrorInfo(
                model_error_type="invalid_response",
                message="provider choice did not contain a message object",
                provider_request_id=provider_request_id or _payload_request_id(payload),
                payload=payload,
            ),
            duration_ms=duration_ms,
        )
    finish_reason = choice.get("finish_reason")
    if finish_reason == "length":
        return model_error_response(
            provider=provider,
            request=request,
            raw_request_ref=raw_request_ref,
            raw_response_ref=raw_response_ref,
            error=ProviderErrorInfo(
                model_error_type="context_limit",
                message="provider response finished because of length",
                provider_request_id=provider_request_id or _payload_request_id(payload),
                payload=payload,
            ),
            duration_ms=duration_ms,
        )
    parse = _parse_tool_calls(message.get("tool_calls"), request.turn)
    if parse.error is not None:
        return model_error_response(
            provider=provider,
            request=request,
            raw_request_ref=raw_request_ref,
            raw_response_ref=raw_response_ref,
            error=ProviderErrorInfo(
                model_error_type="tool_call_parse_failure",
                message=parse.error,
                provider_request_id=provider_request_id or _payload_request_id(payload),
                payload=payload,
            ),
            duration_ms=duration_ms,
        )
    assistant = ModelMessage(
        role="assistant",
        content=message.get("content"),
        tool_calls=parse.tool_calls,
    )
    event = _model_call_event(
        provider=provider,
        request=request,
        payload=payload,
        duration_ms=duration_ms,
        provider_request_id=provider_request_id or _payload_request_id(payload),
        model_error_type=None,
    )
    return ModelResponse(
        assistant_message=assistant,
        tool_calls=parse.tool_calls,
        raw_provider_request_ref=raw_request_ref,
        raw_provider_response_ref=raw_response_ref,
        token_usage=_token_usage(payload, request),
        finish_reason=str(finish_reason) if finish_reason is not None else None,
        model_error_type=None,
        provider_request_id=event.provider_request_id,
        model_call_event=event,
    )


def model_error_response(
    *,
    provider: str,
    request: ModelRequestContext,
    raw_request_ref: ArtifactRef,
    raw_response_ref: ArtifactRef,
    error: ProviderErrorInfo,
    duration_ms: int,
) -> ModelResponse:
    safe_message = sanitize_provider_error_message(error.message)
    payload = error.payload or {}
    event = _model_call_event(
        provider=provider,
        request=request,
        payload=payload,
        duration_ms=duration_ms,
        provider_request_id=error.provider_request_id,
        model_error_type=error.model_error_type,
    )
    return ModelResponse(
        assistant_message=ModelMessage(
            role="assistant",
            content=f"{provider} provider returned structured error: {error.model_error_type}",
        ),
        tool_calls=[],
        raw_provider_request_ref=raw_request_ref,
        raw_provider_response_ref=raw_response_ref,
        token_usage=_token_usage(payload, request, model_error_type=error.model_error_type),
        finish_reason="error",
        model_error_type=error.model_error_type,
        provider_request_id=error.provider_request_id,
        model_call_event=event,
    )


def provider_error_payload(
    *,
    provider: str,
    error: ProviderErrorInfo,
) -> dict[str, Any]:
    return {
        "schema_version": "repo_harness_provider_error_response_v0",
        "provider": provider,
        "status": "error",
        "model_error_type": error.model_error_type,
        "message": sanitize_provider_error_message(error.message),
        "status_code": error.status_code,
        "retryable": error.retryable,
        "provider_request_id": error.provider_request_id,
        "payload": error.payload or {},
        "checked_at": _timestamp(),
    }


def classify_http_status(
    status_code: int,
    *,
    payload: dict[str, Any] | None = None,
    message: str | None = None,
) -> str:
    text = f"{message or ''} {payload or {}}".lower()
    if any(marker in text for marker in ("context_length", "maximum context", "context limit", "too many tokens")):
        return "context_limit"
    if "rate limit" in text or "rate_limit" in text:
        return "rate_limited"
    if "invalid api key" in text or "authentication" in text or "unauthorized" in text:
        return "auth_error"
    if "timeout" in text or "timed out" in text:
        return "provider_timeout"
    if status_code == 401:
        return "auth_error"
    if status_code == 429:
        return "rate_limited"
    if status_code in {400, 422}:
        return "invalid_response"
    if status_code in {408, 504}:
        return "provider_timeout"
    if status_code in {413}:
        return "context_limit"
    return "provider_error"


def duration_ms_since(started: float) -> int:
    return max(0, int((time.monotonic() - started) * 1000))


def _to_chat_message(message: dict[str, Any], *, provider: str) -> dict[str, Any]:
    role = message.get("role")
    converted: dict[str, Any] = {"role": role}
    if role == "assistant":
        converted["content"] = _content_to_string(message.get("content"))
        tool_calls = message.get("tool_calls") or []
        if tool_calls:
            converted["tool_calls"] = [_to_provider_tool_call(call) for call in tool_calls]
        if provider == "deepseek":
            reasoning_content, replay_required = deepseek_reasoning_from_metadata(
                message.get("metadata")
            )
            if reasoning_content:
                converted["reasoning_content"] = reasoning_content
            elif replay_required:
                raise ProviderRequestError(
                    ProviderErrorInfo(
                        model_error_type="provider_protocol_error",
                        message=(
                            "DeepSeek reasoning_content is required for replay, "
                            "but the live provider private state is unavailable."
                        ),
                    )
                )
        return converted
    if role == "tool":
        converted["content"] = _content_to_string(message.get("content"))
        converted["tool_call_id"] = str(message.get("tool_call_id") or message.get("tool_result_id") or "")
        return converted
    converted["content"] = _content_to_string(message.get("content"))
    return converted


def _to_provider_tool_call(call: Any) -> dict[str, Any]:
    if hasattr(call, "model_dump"):
        call = call.model_dump(mode="json")
    if not isinstance(call, dict):
        call = {}
    return {
        "id": str(call.get("tool_call_id") or call.get("id") or ""),
        "type": "function",
        "function": {
            "name": str(call.get("tool_name") or call.get("name") or ""),
            "arguments": json.dumps(call.get("arguments") or {}, ensure_ascii=False, sort_keys=True),
        },
    }


def _to_chat_tool(tool: dict[str, Any]) -> dict[str, Any]:
    parameters = dict(tool.get("input_schema") or {})
    parameters.setdefault("type", "object")
    properties = dict(parameters.get("properties") or {})
    required = list(parameters.get("required") or [])
    for name in required:
        properties.setdefault(name, {"type": "string"})
    parameters["properties"] = properties
    description = str(tool.get("description") or tool.get("model_visible_prompt") or tool.get("name"))
    prompt = tool.get("model_visible_prompt")
    if prompt and str(prompt) not in description:
        description = f"{description}\n{prompt}"
    return {
        "type": "function",
        "function": {
            "name": str(tool.get("name")),
            "description": description,
            "parameters": parameters,
        },
    }


def _content_to_string(content: Any) -> str | None:
    if content is None:
        return None
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False, sort_keys=True)


@dataclass(frozen=True)
class _ToolCallParse:
    tool_calls: list[ToolCall]
    error: str | None = None


def _parse_tool_calls(raw_tool_calls: Any, turn: int) -> _ToolCallParse:
    if raw_tool_calls in (None, []):
        return _ToolCallParse(tool_calls=[])
    if not isinstance(raw_tool_calls, list):
        return _ToolCallParse(tool_calls=[], error="provider tool_calls was not a list")
    tool_calls: list[ToolCall] = []
    for index, raw_call in enumerate(raw_tool_calls):
        call = _object_to_dict(raw_call)
        function = _object_to_dict(call.get("function"))
        name = function.get("name")
        arguments_text = function.get("arguments")
        if not isinstance(name, str) or not name:
            return _ToolCallParse(tool_calls=[], error="provider tool call missing function name")
        if isinstance(arguments_text, str):
            try:
                arguments = json.loads(arguments_text) if arguments_text else {}
            except json.JSONDecodeError:
                return _ToolCallParse(tool_calls=[], error="provider tool call arguments were not valid JSON")
        elif isinstance(arguments_text, dict):
            arguments = arguments_text
        elif arguments_text is None:
            arguments = {}
        else:
            return _ToolCallParse(tool_calls=[], error="provider tool call arguments had unsupported type")
        if not isinstance(arguments, dict):
            return _ToolCallParse(tool_calls=[], error="provider tool call arguments were not a JSON object")
        tool_calls.append(
            ToolCall(
                tool_call_id=str(call.get("id") or f"provider_tool_call_{turn}_{index}"),
                tool_name=name,
                arguments=arguments,
                turn=turn,
            )
        )
    return _ToolCallParse(tool_calls=tool_calls)


def _model_call_event(
    *,
    provider: str,
    request: ModelRequestContext,
    payload: dict[str, Any],
    duration_ms: int,
    provider_request_id: str | None,
    model_error_type: str | None,
) -> ModelCallEvent:
    usage = _token_usage(payload, request, model_error_type=model_error_type)
    return ModelCallEvent(
        model_call_id=request.model_call_id,
        provider=provider,
        model_id=request.provider_options.model_id,
        provider_request_id=provider_request_id,
        context_revision=request.context_revision,
        prepared_messages_ref=request.prepared_messages_ref,
        model_input_hash=request.model_input_hash,
        provider_message_format=OPENAI_COMPATIBLE_MESSAGE_FORMAT_VERSION,
        tool_schema_hash=stable_hash(request.allowed_tool_definitions),
        input_tokens=usage["input_tokens"],
        output_tokens=usage["output_tokens"],
        cached_tokens=usage["cached_tokens"],
        duration_ms=duration_ms,
        retry_count=0,
        model_error_type=model_error_type,
    )


def _token_usage(
    payload: dict[str, Any],
    request: ModelRequestContext,
    model_error_type: str | None = None,
) -> dict[str, int]:
    usage = _object_to_dict(payload.get("usage"))
    input_tokens = _int_or_default(
        usage.get("prompt_tokens") or usage.get("input_tokens"),
        max(1, len(str(request.prepared_messages)) // 4),
    )
    output_tokens = _int_or_default(
        usage.get("completion_tokens") or usage.get("output_tokens"),
        0 if model_error_type else max(1, len(str(payload)) // 8),
    )
    cached_tokens = _int_or_default(
        usage.get("prompt_cache_hit_tokens")
        or usage.get("cached_tokens")
        or _object_to_dict(usage.get("prompt_tokens_details")).get("cached_tokens"),
        0,
    )
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cached_tokens": cached_tokens,
    }


def _payload_request_id(payload: dict[str, Any]) -> str | None:
    value = payload.get("id") or payload.get("request_id") or payload.get("_request_id")
    return str(value) if value is not None else None


def _object_to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="json")
        return dumped if isinstance(dumped, dict) else {}
    if hasattr(value, "to_dict"):
        dumped = value.to_dict()
        return dumped if isinstance(dumped, dict) else {}
    result: dict[str, Any] = {}
    for key in dir(value):
        if key.startswith("_"):
            continue
        try:
            nested = getattr(value, key)
        except Exception:
            continue
        if callable(nested):
            continue
        result[key] = nested
    return result


def _int_or_default(value: Any, default: int) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()
