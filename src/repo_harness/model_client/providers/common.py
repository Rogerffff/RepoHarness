"""Shared OpenAI-compatible provider helpers."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from repo_harness.model_client.redaction import (
    REDACTED_CREDENTIAL,
    redact_provider_payload_with_report,
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
PROVIDER_RETRY_POLICY_VERSION = "repo_harness_provider_retry_policy_v0"
PROVIDER_ATTEMPT_SCHEMA_VERSION = "repo_harness_provider_attempt_v0"
RETRYABLE_PROVIDER_ERROR_TYPES = {"rate_limited", "provider_timeout", "provider_error"}
PROVIDER_RETRY_POLICIES = {"provider_retry_v0", "provider_retry_no_sleep_v0"}
TRANSPORT_SOCKET_TIMEOUT_CAP_SEC = 10.0
TRANSPORT_READ_CHUNK_SIZE = 65536


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


def read_response_text_with_deadline(
    response: Any,
    *,
    timeout_seconds: float | None = None,
    deadline_monotonic: float | None = None,
    chunk_size: int = TRANSPORT_READ_CHUNK_SIZE,
) -> str:
    """Read an urllib response while checking a total-call deadline between chunks."""

    if deadline_monotonic is None:
        if timeout_seconds is None:
            raise ValueError("timeout_seconds or deadline_monotonic is required")
        deadline_monotonic = time.monotonic() + timeout_seconds
    chunks: list[bytes] = []
    while True:
        remaining = deadline_monotonic - time.monotonic()
        if remaining <= 0:
            raise ProviderRequestError(
                ProviderErrorInfo(
                    model_error_type="provider_timeout",
                    message="provider request exceeded the configured absolute deadline",
                    retryable=True,
                    payload={"deadline_exceeded": True},
                )
            )
        _set_response_socket_timeout(response, min(TRANSPORT_SOCKET_TIMEOUT_CAP_SEC, remaining))
        try:
            try:
                chunk = response.read(chunk_size)
            except TypeError:
                chunk = response.read()
        except TimeoutError as exc:
            raise ProviderRequestError(
                ProviderErrorInfo(
                    model_error_type="provider_timeout",
                    message=sanitize_provider_error_message(str(exc)),
                    retryable=True,
                    payload={"deadline_exceeded": time.monotonic() >= deadline_monotonic},
                )
            ) from exc
        if not chunk:
            return b"".join(chunks).decode("utf-8")
        if time.monotonic() >= deadline_monotonic:
            raise ProviderRequestError(
                ProviderErrorInfo(
                    model_error_type="provider_timeout",
                    message="provider request exceeded the configured absolute deadline",
                    retryable=True,
                    payload={"deadline_exceeded": True},
                )
            )
        chunks.append(chunk)


def request_for_provider_attempt(
    request: ModelRequestContext,
    *,
    call_deadline_monotonic: float,
) -> ModelRequestContext:
    remaining = call_deadline_monotonic - time.monotonic()
    if remaining <= 0:
        raise _provider_deadline_error()
    facts = {
        **request.request_timeout_policy_facts,
        "provider_retry_deadline_enforced": True,
        "provider_retry_remaining_timeout_sec_before_attempt": round(remaining, 6),
    }
    return request.model_copy(
        update={
            "request_timeout_seconds": max(0.001, remaining),
            "request_timeout_policy_facts": facts,
        }
    )


def sleep_before_provider_retry_with_deadline(
    *,
    delay_ms: int,
    call_deadline_monotonic: float,
) -> None:
    if delay_ms <= 0:
        return
    delay_sec = delay_ms / 1000
    remaining = call_deadline_monotonic - time.monotonic()
    if remaining <= delay_sec:
        raise _provider_deadline_error(
            payload={
                "deadline_exceeded": True,
                "retry_delay_ms": delay_ms,
                "remaining_timeout_sec_before_retry_delay": round(remaining, 6),
            }
        )
    time.sleep(delay_sec)


def _provider_deadline_error(payload: dict[str, Any] | None = None) -> ProviderRequestError:
    return ProviderRequestError(
        ProviderErrorInfo(
            model_error_type="provider_timeout",
            message="provider request exceeded the configured absolute deadline",
            retryable=True,
            payload=payload or {"deadline_exceeded": True},
        )
    )


def _set_response_socket_timeout(response: Any, timeout_seconds: float) -> None:
    try:
        fp = getattr(response, "fp", None)
        raw = getattr(fp, "raw", None)
        sock = getattr(raw, "_sock", None)
        if sock is not None:
            sock.settimeout(timeout_seconds)
    except Exception:
        return


@dataclass(frozen=True)
class ProviderCredential:
    value: str
    source: str
    status: str = "present"


@dataclass(frozen=True)
class ProviderRetryPolicy:
    policy_id: str
    max_attempts: int
    backoff_delays_ms: tuple[int, ...]
    sleep_enabled: bool
    retryable_error_types: tuple[str, ...]


def retry_policy_from_request(request: ModelRequestContext) -> ProviderRetryPolicy:
    """Resolve a deterministic provider retry policy for one model call."""

    policy_id = str(request.retry_policy or "none")
    if policy_id not in PROVIDER_RETRY_POLICIES:
        return ProviderRetryPolicy(
            policy_id=policy_id,
            max_attempts=1,
            backoff_delays_ms=(0,),
            sleep_enabled=False,
            retryable_error_types=tuple(sorted(RETRYABLE_PROVIDER_ERROR_TYPES)),
        )
    return ProviderRetryPolicy(
        policy_id=policy_id,
        max_attempts=3,
        backoff_delays_ms=(0, 250, 1000),
        sleep_enabled=policy_id != "provider_retry_no_sleep_v0",
        retryable_error_types=tuple(sorted(RETRYABLE_PROVIDER_ERROR_TYPES)),
    )


def write_provider_retry_policy_artifact(
    *,
    provider: str,
    recorder: RunRecorder,
    request: ModelRequestContext,
    policy: ProviderRetryPolicy,
) -> ArtifactRef:
    return recorder.write_json_artifact(
        "provider_retry_policy",
        {
            "schema_version": PROVIDER_RETRY_POLICY_VERSION,
            "provider": provider,
            "model_call_id": request.model_call_id,
            "policy_id": policy.policy_id,
            "max_attempts": policy.max_attempts,
            "backoff_delays_ms": list(policy.backoff_delays_ms),
            "sleep_enabled": policy.sleep_enabled,
            "retryable_error_types": list(policy.retryable_error_types),
            "fallback_provider": {"enabled": False},
        },
        {
            "redaction_status": "not_sensitive",
            "retention_policy": "keep",
            "budget_policy": "preserve_json",
        },
    )


def write_provider_attempt_artifact(
    *,
    provider: str,
    recorder: RunRecorder,
    request: ModelRequestContext,
    attempt_index: int,
    retryable: bool,
    error_type: str | None,
    delay_ms: int,
    request_ref: ArtifactRef,
    response_ref: ArtifactRef,
    provider_request_id: str | None,
    duration_ms: int,
    terminal: bool,
) -> ArtifactRef:
    return recorder.write_json_artifact(
        "provider_attempt",
        {
            "schema_version": PROVIDER_ATTEMPT_SCHEMA_VERSION,
            "attempt_index": attempt_index,
            "model_call_id": request.model_call_id,
            "provider": provider,
            "retryable": retryable,
            "error_type": error_type,
            "delay_ms": delay_ms,
            "request_ref": request_ref.model_dump(mode="json"),
            "response_ref": response_ref.model_dump(mode="json"),
            "provider_request_id": provider_request_id,
            "duration_ms": duration_ms,
            "terminal": terminal,
        },
        {
            "redaction_status": "not_sensitive",
            "retention_policy": "keep",
            "budget_policy": "preserve_json",
        },
    )


def should_retry_provider_error(
    *,
    error: ProviderErrorInfo,
    attempt_index: int,
    policy: ProviderRetryPolicy,
) -> bool:
    return (
        attempt_index < policy.max_attempts
        and error.retryable
        and error.model_error_type in set(policy.retryable_error_types)
    )


def retry_delay_ms(*, attempt_index: int, policy: ProviderRetryPolicy) -> int:
    index = min(attempt_index, len(policy.backoff_delays_ms) - 1)
    return policy.backoff_delays_ms[index]


def attach_provider_retry_metadata(
    response: ModelResponse,
    *,
    attempt_refs: list[ArtifactRef],
    retry_policy_ref: ArtifactRef | None,
    terminal_error_type: str | None,
) -> ModelResponse:
    attempt_count = max(1, len(attempt_refs))
    retry_count = max(0, attempt_count - 1)
    event = response.model_call_event
    if event is not None:
        event = event.model_copy(
            update={
                "attempt_count": attempt_count,
                "retry_count": retry_count,
                "terminal_error_type": terminal_error_type,
                "retry_policy_ref": retry_policy_ref,
            }
        )
    return response.model_copy(
        update={
            "provider_attempt_refs": attempt_refs,
            "retry_policy_ref": retry_policy_ref,
            "attempt_count": attempt_count,
            "retry_count": retry_count,
            "terminal_error_type": terminal_error_type,
            "model_call_event": event,
        }
    )


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
    provider_options = request.provider_options.provider_specific_options
    if "temperature" in request.generation_config and not _skip_temperature_for_deepseek_thinking(
        include_deepseek_options=include_deepseek_options,
        provider_options=provider_options,
    ):
        payload["temperature"] = request.generation_config["temperature"]
    max_output_tokens = request.generation_config.get("max_output_tokens")
    if max_output_tokens is not None:
        payload["max_tokens"] = max_output_tokens
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
        "prepared_messages_ref": request.prepared_messages_ref.model_dump(mode="json"),
        "model_input_hash": request.model_input_hash,
        "context_revision": request.context_revision,
        "run_id": request.run_id,
        "task_id": request.task_id,
        "turn": request.turn,
        "model_call_id": request.model_call_id,
        "request_timeout_seconds": request.request_timeout_seconds,
        "request_timeout_policy_facts": request.request_timeout_policy_facts,
        "raw_request_logging_policy": request.raw_request_logging_policy,
        "credential_policy": request.credential_policy.model_dump(mode="json"),
        "authorization": REDACTED_CREDENTIAL,
    }


def _skip_temperature_for_deepseek_thinking(
    *,
    include_deepseek_options: bool,
    provider_options: dict[str, Any],
) -> bool:
    if not include_deepseek_options:
        return False
    thinking = provider_options.get("thinking")
    if isinstance(thinking, dict):
        return thinking.get("type") != "disabled"
    return False


def write_provider_request_artifact(
    *,
    provider: str,
    recorder: RunRecorder,
    payload: dict[str, Any],
    request: ModelRequestContext | None = None,
) -> ArtifactRef:
    redacted_payload, redaction_report = redact_provider_payload_with_report(payload)
    body = _object_to_dict(payload.get("body"))
    redacted_body = _object_to_dict(redacted_payload.get("body")) if isinstance(redacted_payload, dict) else {}
    request_binding = _provider_request_binding(payload=payload, request=request)
    return recorder.write_json_artifact(
        f"raw_{provider}_provider_request",
        {
            **redacted_payload,
            "export_allowed": False,
            "training_payload_allowed": False,
            "provider_body_hash_before_redaction": stable_hash(body),
            "redacted_body_hash": stable_hash(redacted_body),
            "redaction_report": redaction_report,
            "prepared_messages_ref": request_binding["prepared_messages_ref"],
            "tool_schema_snapshot_ref": request_binding["tool_schema_snapshot_ref"],
            "model_input_hash": request_binding["model_input_hash"],
            "model_call_id": request_binding["model_call_id"],
            "request_timeout_seconds": request_binding["request_timeout_seconds"],
            "request_timeout_policy_facts": request_binding[
                "request_timeout_policy_facts"
            ],
            "provider_request_projection_hash": request_binding[
                "provider_request_projection_hash"
            ],
            "provider_request_token_estimate": request_binding[
                "provider_request_token_estimate"
            ],
            "provider_request_token_estimate_breakdown": request_binding[
                "provider_request_token_estimate_breakdown"
            ],
            "context_budget_facts": request_binding["context_budget_facts"],
            "provider_body_message_projection_hash": stable_hash(_project_provider_messages(body)),
            "prepared_messages_projection_hash": request_binding["prepared_messages_projection_hash"],
            "prepared_messages_body_equivalent": request_binding["prepared_messages_body_equivalent"],
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
    request: ModelRequestContext | None = None,
    raw_request_ref: ArtifactRef | None = None,
) -> ArtifactRef:
    redacted_payload, redaction_report = redact_provider_payload_with_report(payload)
    response_body = _response_body_for_hash(payload)
    redacted_response_body = _response_body_for_hash(redacted_payload)
    response_binding = _provider_response_binding(
        payload=payload,
        request=request,
        raw_request_ref=raw_request_ref,
    )
    return recorder.write_json_artifact(
        f"raw_{provider}_provider_response",
        {
            **redacted_payload,
            "export_allowed": False,
            "training_payload_allowed": False,
            "response_body_hash_before_redaction": stable_hash(response_body),
            "redacted_response_body_hash": stable_hash(redacted_response_body),
            "redaction_report": redaction_report,
            "model_call_id": response_binding["model_call_id"],
            "raw_provider_request_ref": response_binding["raw_provider_request_ref"],
            "prepared_messages_ref": response_binding["prepared_messages_ref"],
            "tool_schema_snapshot_ref": response_binding["tool_schema_snapshot_ref"],
            "parsed_tool_calls_hash": response_binding["parsed_tool_calls_hash"],
            "finish_reason": response_binding["finish_reason"],
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
                model_error_type="output_token_limit_reached",
                message="provider response finished because of output length",
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
            metadata={
                "model_error_type": error.model_error_type,
                "provider_error_message": safe_message,
            },
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
    if any(
        marker in text
        for marker in (
            "context_length",
            "context length",
            "maximum context",
            "context limit",
            "prompt too long",
            "too many tokens",
            "maximum tokens",
        )
    ):
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
            if reasoning_content is not None:
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


def _provider_request_binding(
    *,
    payload: dict[str, Any],
    request: ModelRequestContext | None,
) -> dict[str, Any]:
    prepared_ref = (
        request.prepared_messages_ref.model_dump(mode="json")
        if request is not None
        else payload.get("prepared_messages_ref")
    )
    tool_schema_ref = (
        request.tool_schema_snapshot_ref.model_dump(mode="json")
        if request is not None
        else payload.get("tool_schema_snapshot_ref")
    )
    model_input_hash = request.model_input_hash if request is not None else payload.get("model_input_hash")
    model_call_id = request.model_call_id if request is not None else payload.get("model_call_id")
    body_messages = _project_provider_messages(_object_to_dict(payload.get("body")))
    prepared_projection: list[dict[str, Any]] | dict[str, Any] | None
    if request is None:
        prepared_projection = None
    else:
        try:
            prepared_projection = _project_prepared_messages(
                request.prepared_messages,
                provider=str(payload.get("provider") or ""),
            )
        except ProviderRequestError as exc:
            prepared_projection = {
                "projection_error": exc.info.model_error_type,
                "message": sanitize_provider_error_message(exc.info.message),
            }
    return {
        "prepared_messages_ref": prepared_ref,
        "tool_schema_snapshot_ref": tool_schema_ref,
        "model_input_hash": model_input_hash,
        "model_call_id": model_call_id,
        "request_timeout_seconds": (
            request.request_timeout_seconds
            if request is not None
            else payload.get("request_timeout_seconds")
        ),
        "request_timeout_policy_facts": (
            request.request_timeout_policy_facts
            if request is not None
            else payload.get("request_timeout_policy_facts", {})
        ),
        "provider_request_projection_hash": (
            request.provider_request_projection_hash if request is not None else None
        ),
        "provider_request_token_estimate": (
            request.provider_request_token_estimate if request is not None else 0
        ),
        "provider_request_token_estimate_breakdown": (
            request.provider_request_token_estimate_breakdown if request is not None else {}
        ),
        "context_budget_facts": request.context_budget_facts if request is not None else {},
        "prepared_messages_projection_hash": stable_hash(prepared_projection),
        "prepared_messages_body_equivalent": prepared_projection == body_messages,
    }


def _provider_response_binding(
    *,
    payload: dict[str, Any],
    request: ModelRequestContext | None,
    raw_request_ref: ArtifactRef | None,
) -> dict[str, Any]:
    response_payload = _object_to_dict(payload.get("response")) or payload
    choice = _first_choice(response_payload)
    message = _object_to_dict(choice.get("message"))
    parse = _parse_tool_calls(message.get("tool_calls"), request.turn if request is not None else 0)
    parsed_tool_calls: dict[str, Any]
    if parse.error:
        parsed_tool_calls = {"error": parse.error, "tool_calls": []}
    else:
        parsed_tool_calls = {"error": None, "tool_calls": [call.model_dump(mode="json") for call in parse.tool_calls]}
    return {
        "model_call_id": request.model_call_id if request is not None else payload.get("model_call_id"),
        "raw_provider_request_ref": raw_request_ref.model_dump(mode="json") if raw_request_ref else None,
        "prepared_messages_ref": (
            request.prepared_messages_ref.model_dump(mode="json") if request is not None else None
        ),
        "tool_schema_snapshot_ref": (
            request.tool_schema_snapshot_ref.model_dump(mode="json") if request is not None else None
        ),
        "parsed_tool_calls_hash": stable_hash(parsed_tool_calls),
        "finish_reason": choice.get("finish_reason") if isinstance(choice, dict) else None,
    }


def _response_body_for_hash(payload: Any) -> Any:
    if isinstance(payload, dict) and "response" in payload:
        return payload["response"]
    return payload


def _project_provider_messages(body: dict[str, Any]) -> list[dict[str, Any]]:
    messages = body.get("messages")
    if not isinstance(messages, list):
        return []
    projected: list[dict[str, Any]] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        item = {
            "role": message.get("role"),
            "content": message.get("content"),
            "tool_call_id": message.get("tool_call_id"),
            "tool_calls": message.get("tool_calls"),
        }
        projected.append({key: value for key, value in item.items() if value is not None})
    return projected


def _project_prepared_messages(messages: list[dict[str, Any]], *, provider: str) -> list[dict[str, Any]]:
    projected: list[dict[str, Any]] = []
    for message in messages:
        converted = _to_chat_message(message, provider=provider)
        item = {
            "role": converted.get("role"),
            "content": converted.get("content"),
            "tool_call_id": converted.get("tool_call_id"),
            "tool_calls": converted.get("tool_calls"),
        }
        projected.append({key: value for key, value in item.items() if value is not None})
    return projected


def _first_choice(payload: dict[str, Any]) -> dict[str, Any]:
    choices = payload.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        return choices[0]
    return {}


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
        request_timeout_seconds=request.request_timeout_seconds,
        request_timeout_policy_facts=request.request_timeout_policy_facts,
        terminal_error_type=model_error_type,
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
