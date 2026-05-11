import json
import http.client
from pathlib import Path
from typing import Any

import pytest

from repo_harness.model_client.providers.common import classify_http_status
from repo_harness.model_client.providers.deepseek import DeepSeekProviderClient
from repo_harness.model_client.providers.deepseek import (
    normalize_deepseek_model_id,
    resolve_deepseek_credential,
)
from repo_harness.errors import ConfigError
from repo_harness.model_client.providers.openai import OpenAIProviderClient
from repo_harness.model_client.providers.openai import _sdk_body as _openai_sdk_body
from repo_harness.model_client.providers.common import (
    ProviderCredential,
    ProviderErrorInfo,
    ProviderRequestError,
)
from repo_harness.model_client.redaction import REDACTED_CREDENTIAL, redact_provider_payload
from repo_harness.model_client.schemas import (
    ModelProviderOptions,
    ModelRequestContext,
    ProviderCredentialPolicy,
)
from repo_harness.run_metadata import RunConfigFactsRef
from repo_harness.trajectory import ArtifactRef, RunRecorder


def test_deepseek_provider_uses_openai_compatible_tool_calls(tmp_path: Path):
    client = _DeepSeekStub(
        model_id="deepseek-v4-pro",
        base_url="https://api.deepseek.com",
        credential=ProviderCredential(value="sk-test-secret-value-1234567890", source="environment"),
        response_payload={
            "id": "deepseek-response-1",
            "choices": [
                {
                    "finish_reason": "tool_calls",
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "read_file",
                                    "arguments": "{\"path\":\"calculator.py\"}",
                                },
                            }
                        ],
                    },
                }
            ],
            "usage": {"prompt_tokens": 11, "completion_tokens": 7, "prompt_cache_hit_tokens": 3},
        },
    )
    request = _request(provider="deepseek", model_id="deepseek-v4-pro")
    with RunRecorder("deepseek", tmp_path / "run", task_id="task_001") as recorder:
        response = client.generate(request=request, recorder=recorder)

    assert response.model_error_type is None
    assert response.tool_calls[0].tool_name == "read_file"
    assert response.tool_calls[0].arguments == {"path": "calculator.py"}
    assert response.model_call_event is not None
    assert response.model_call_event.provider == "deepseek"
    assert response.model_call_event.input_tokens == 11
    assert response.model_call_event.cached_tokens == 3
    assert client.last_body["tools"][0]["type"] == "function"
    assert client.last_body["tools"][0]["function"]["name"] == "read_file"
    raw_text = (tmp_path / "run" / response.raw_provider_request_ref.relative_path).read_text(
        encoding="utf-8"
    )
    assert "sk-test-secret-value" not in raw_text
    assert "Authorization: Bearer" not in raw_text


def test_deepseek_thinking_enabled_omits_temperature(tmp_path: Path):
    client = _DeepSeekStub(
        model_id="deepseek-v4-pro",
        base_url="https://api.deepseek.com",
        credential=ProviderCredential(value="sk-test-secret-value-1234567890", source="environment"),
        response_payload={
            "id": "deepseek-response-thinking",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": "done"},
                }
            ],
            "usage": {"prompt_tokens": 11, "completion_tokens": 7},
        },
    )
    request = _request(
        provider="deepseek",
        model_id="deepseek-v4-pro",
        provider_specific_options={
            "thinking": {"type": "enabled"},
            "reasoning_effort": "high",
        },
    )
    with RunRecorder("deepseek-thinking-temperature", tmp_path / "run", task_id="task_001") as recorder:
        response = client.generate(request=request, recorder=recorder)

    assert response.model_error_type is None
    assert "temperature" not in client.last_body
    assert client.last_body["extra_body"] == {"thinking": {"type": "enabled"}}
    assert client.last_body["reasoning_effort"] == "high"
    raw_text = (tmp_path / "run" / response.raw_provider_request_ref.relative_path).read_text(
        encoding="utf-8"
    )
    assert '"temperature"' not in raw_text


def test_deepseek_thinking_tool_call_without_reasoning_is_protocol_error(
    tmp_path: Path,
):
    client = _DeepSeekStub(
        model_id="deepseek-v4-pro",
        base_url="https://api.deepseek.com",
        credential=ProviderCredential(value="sk-test-secret-value-1234567890", source="environment"),
        response_payload={
            "id": "deepseek-response-missing-reasoning",
            "choices": [
                {
                    "finish_reason": "tool_calls",
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "read_file",
                                    "arguments": "{\"path\":\"calculator.py\"}",
                                },
                            }
                        ],
                    },
                }
            ],
        },
    )
    request = _request(
        provider="deepseek",
        model_id="deepseek-v4-pro",
        provider_specific_options={"thinking": {"type": "enabled"}},
    )
    with RunRecorder("deepseek-missing-tool-reasoning", tmp_path / "run", task_id="task_001") as recorder:
        response = client.generate(request=request, recorder=recorder)

    assert response.model_error_type == "provider_protocol_error"
    assert client.last_body["tools"][0]["function"]["name"] == "read_file"


def test_deepseek_thinking_tool_call_allows_empty_reasoning_for_replay(
    tmp_path: Path,
):
    first_client = _DeepSeekStub(
        model_id="deepseek-v4-pro",
        base_url="https://api.deepseek.com",
        credential=ProviderCredential(value="sk-test-secret-value-1234567890", source="environment"),
        response_payload={
            "id": "deepseek-response-empty-reasoning",
            "choices": [
                {
                    "finish_reason": "tool_calls",
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "reasoning_content": "",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "read_file",
                                    "arguments": "{\"path\":\"calculator.py\"}",
                                },
                            }
                        ],
                    },
                }
            ],
        },
    )
    first_request = _request(
        provider="deepseek",
        model_id="deepseek-v4-pro",
        provider_specific_options={"thinking": {"type": "enabled"}},
    )
    with RunRecorder("deepseek-empty-reasoning-1", tmp_path / "first", task_id="task_001") as recorder:
        first_response = first_client.generate(request=first_request, recorder=recorder)

    assert first_response.model_error_type is None
    assistant_metadata = first_response.assistant_message.metadata
    assert assistant_metadata["provider_private"]["deepseek"]["reasoning_content_present"] is True

    second_client = _DeepSeekStub(
        model_id="deepseek-v4-pro",
        base_url="https://api.deepseek.com",
        credential=ProviderCredential(value="sk-test-secret-value-1234567890", source="environment"),
        response_payload={
            "id": "deepseek-response-empty-reasoning-replay",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": "done"},
                }
            ],
        },
    )
    second_request = _request(
        provider="deepseek",
        model_id="deepseek-v4-pro",
        prepared_messages=[
            {"role": "system", "content": "system"},
            {"role": "user", "content": "fix"},
            {
                "role": "assistant",
                "content": first_response.assistant_message.content,
                "tool_calls": [call.model_dump(mode="json") for call in first_response.tool_calls],
                "metadata": assistant_metadata,
            },
            {"role": "tool", "tool_call_id": "call_1", "content": "file contents"},
        ],
        provider_specific_options={"thinking": {"type": "enabled"}},
    )
    with RunRecorder("deepseek-empty-reasoning-2", tmp_path / "second", task_id="task_001") as recorder:
        second_response = second_client.generate(request=second_request, recorder=recorder)

    assert second_response.model_error_type is None
    assert second_client.last_body["messages"][2]["reasoning_content"] == ""


def test_deepseek_provider_replays_reasoning_content_after_tool_call(tmp_path: Path):
    first_client = _DeepSeekStub(
        model_id="deepseek-v4-pro",
        base_url="https://api.deepseek.com",
        credential=ProviderCredential(value="sk-test-secret-value-1234567890", source="environment"),
        response_payload={
            "id": "deepseek-response-reasoning-1",
            "choices": [
                {
                    "finish_reason": "tool_calls",
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "reasoning_content": "private reasoning that must not enter artifacts",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "read_file",
                                    "arguments": "{\"path\":\"calculator.py\"}",
                                },
                            }
                        ],
                    },
                }
            ],
        },
    )
    first_request = _request(provider="deepseek", model_id="deepseek-v4-pro")
    with RunRecorder("deepseek-reasoning-1", tmp_path / "first", task_id="task_001") as recorder:
        first_response = first_client.generate(request=first_request, recorder=recorder)

    assistant_metadata = first_response.assistant_message.metadata
    deepseek_private = assistant_metadata["provider_private"]["deepseek"]
    assert deepseek_private["reasoning_content_present"] is True
    assert deepseek_private["reasoning_content_required_for_replay"] is True
    metadata_text = json.dumps(assistant_metadata, ensure_ascii=False)
    assert "private reasoning that must not enter artifacts" not in metadata_text
    assert '"reasoning_content":' not in metadata_text
    first_raw_response = (
        tmp_path / "first" / first_response.raw_provider_response_ref.relative_path
    ).read_text(encoding="utf-8")
    assert "private reasoning that must not enter artifacts" not in first_raw_response
    assert "<REDACTED_REASONING>" in first_raw_response
    first_manifest = json.loads((tmp_path / "first" / "artifacts.json").read_text(encoding="utf-8"))
    assert not any(
        artifact["kind"] == "deepseek_provider_reasoning_trace"
        for artifact in first_manifest["artifacts"]
    )

    second_client = _DeepSeekStub(
        model_id="deepseek-v4-pro",
        base_url="https://api.deepseek.com",
        credential=ProviderCredential(value="sk-test-secret-value-1234567890", source="environment"),
        response_payload={
            "id": "deepseek-response-reasoning-2",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": "done"},
                }
            ],
        },
    )
    second_request = _request(
        provider="deepseek",
        model_id="deepseek-v4-pro",
        prepared_messages=[
            {"role": "system", "content": "system"},
            {"role": "user", "content": {"task": "fix calculator"}},
            {
                "role": "assistant",
                "content": first_response.assistant_message.content,
                "tool_calls": [call.model_dump(mode="json") for call in first_response.tool_calls],
                "metadata": assistant_metadata,
            },
            {"role": "tool", "tool_call_id": "call_1", "content": "file contents"},
        ],
    )
    with RunRecorder("deepseek-reasoning-2", tmp_path / "second", task_id="task_001") as recorder:
        second_response = second_client.generate(request=second_request, recorder=recorder)

    assert second_response.model_error_type is None
    assert second_client.last_body["messages"][2]["reasoning_content"] == (
        "private reasoning that must not enter artifacts"
    )
    second_raw_request = (
        tmp_path / "second" / second_response.raw_provider_request_ref.relative_path
    ).read_text(encoding="utf-8")
    assert "private reasoning that must not enter artifacts" not in second_raw_request
    assert "<REDACTED_REASONING>" in second_raw_request


def test_deepseek_reasoning_trace_training_opt_in_writes_dedicated_source_artifact(
    tmp_path: Path,
):
    client = _DeepSeekStub(
        model_id="deepseek-v4-pro",
        base_url="https://api.deepseek.com",
        credential=ProviderCredential(value="sk-test-secret-value-1234567890", source="environment"),
        response_payload={
            "id": "deepseek-response-reasoning-trace",
            "choices": [
                {
                    "finish_reason": "tool_calls",
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "reasoning_content": "provider trace target for explicit training",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "read_file",
                                    "arguments": "{\"path\":\"calculator.py\"}",
                                },
                            }
                        ],
                    },
                }
            ],
        },
    )
    request = _request(
        provider="deepseek",
        model_id="deepseek-v4-pro",
        provider_specific_options={
            "thinking": {"type": "enabled"},
            "provider_reasoning_trace_training_export": {"enabled": True},
        },
    )

    with RunRecorder("deepseek-reasoning-trace", tmp_path / "run", task_id="task_001") as recorder:
        response = client.generate(request=request, recorder=recorder)

    assert response.model_error_type is None
    metadata_text = json.dumps(response.assistant_message.metadata, ensure_ascii=False)
    assert "provider trace target for explicit training" not in metadata_text
    manifest = json.loads((tmp_path / "run" / "artifacts.json").read_text(encoding="utf-8"))
    trace_refs = [
        artifact for artifact in manifest["artifacts"] if artifact["kind"] == "deepseek_provider_reasoning_trace"
    ]
    assert len(trace_refs) == 1
    trace_payload = json.loads((tmp_path / "run" / trace_refs[0]["relative_path"]).read_text(encoding="utf-8"))
    assert trace_payload["reasoning_content"] == "provider trace target for explicit training"
    assert trace_payload["ordinary_sft_target_allowed"] is False
    assert trace_payload["requires_explicit_reasoning_export_policy"] is True
    raw_response = (tmp_path / "run" / response.raw_provider_response_ref.relative_path).read_text(
        encoding="utf-8"
    )
    assert "provider trace target for explicit training" not in raw_response
    assert "<REDACTED_REASONING>" in raw_response


def test_deepseek_provider_protocol_error_when_required_reasoning_state_is_missing(
    tmp_path: Path,
):
    client = _DeepSeekStub(
        model_id="deepseek-v4-pro",
        base_url="https://api.deepseek.com",
        credential=ProviderCredential(value="sk-test-secret-value-1234567890", source="environment"),
        response_payload={
            "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "done"}}]
        },
    )
    request = _request(
        provider="deepseek",
        model_id="deepseek-v4-pro",
        prepared_messages=[
            {"role": "system", "content": "system"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [],
                "metadata": {
                    "provider_private": {
                        "deepseek": {
                            "state_id": "missing-state",
                            "reasoning_content_required_for_replay": True,
                        }
                    }
                },
            },
        ],
    )

    with RunRecorder("deepseek-missing-reasoning", tmp_path / "run", task_id="task_001") as recorder:
        response = client.generate(request=request, recorder=recorder)

    assert response.model_error_type == "provider_protocol_error"
    assert client.last_body == {}


def test_deepseek_provider_maps_malformed_tool_call_to_model_error(tmp_path: Path):
    client = _DeepSeekStub(
        model_id="deepseek-v4-pro",
        base_url="https://api.deepseek.com",
        credential=ProviderCredential(value="sk-test-secret-value-1234567890", source="environment"),
        response_payload={
            "id": "deepseek-response-2",
            "choices": [
                {
                    "finish_reason": "tool_calls",
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_bad",
                                "type": "function",
                                "function": {"name": "read_file", "arguments": "{bad json"},
                            }
                        ],
                    },
                }
            ],
        },
    )
    with RunRecorder("deepseek-bad-tool", tmp_path / "run", task_id="task_001") as recorder:
        response = client.generate(
            request=_request(provider="deepseek", model_id="deepseek-v4-pro"),
            recorder=recorder,
        )

    assert response.model_error_type == "tool_call_parse_failure"
    assert response.tool_calls == []
    raw_response = json.loads(
        (tmp_path / "run" / response.raw_provider_response_ref.relative_path).read_text(
            encoding="utf-8"
        )
    )
    assert raw_response["response"]["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] == "{bad json"


def test_deepseek_provider_retries_retryable_error_and_records_attempts(tmp_path: Path):
    client = _DeepSeekSequenceStub(
        model_id="deepseek-v4-pro",
        base_url="https://api.deepseek.com",
        credential=ProviderCredential(value="sk-test-secret-value-1234567890", source="environment"),
        outcomes=[
            ProviderRequestError(
                ProviderErrorInfo(
                    model_error_type="rate_limited",
                    message="rate limit",
                    status_code=429,
                    retryable=True,
                    provider_request_id="deepseek-request-rate-limited",
                )
            ),
            {
                "id": "deepseek-response-after-retry",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "done"},
                    }
                ],
                "usage": {"prompt_tokens": 17, "completion_tokens": 3},
            },
        ],
    )
    request = _request(
        provider="deepseek",
        model_id="deepseek-v4-pro",
        retry_policy="provider_retry_no_sleep_v0",
    )

    with RunRecorder("deepseek-retry", tmp_path / "run", task_id="task_001") as recorder:
        response = client.generate(request=request, recorder=recorder)

    assert response.model_error_type is None
    assert response.attempt_count == 2
    assert response.retry_count == 1
    assert len(response.provider_attempt_refs) == 2
    assert response.model_call_event is not None
    assert response.model_call_event.retry_count == 1
    first_attempt = json.loads(
        (tmp_path / "run" / response.provider_attempt_refs[0].relative_path).read_text(encoding="utf-8")
    )
    assert first_attempt["error_type"] == "rate_limited"
    assert first_attempt["retryable"] is True
    assert first_attempt["terminal"] is False
    second_attempt = json.loads(
        (tmp_path / "run" / response.provider_attempt_refs[1].relative_path).read_text(encoding="utf-8")
    )
    assert second_attempt["terminal"] is True


def test_deepseek_retry_stops_before_delay_would_exceed_provider_deadline(tmp_path: Path):
    client = _DeepSeekSequenceStub(
        model_id="deepseek-v4-pro",
        base_url="https://api.deepseek.com",
        credential=ProviderCredential(value="sk-test-secret-value-1234567890", source="environment"),
        outcomes=[
            ProviderRequestError(
                ProviderErrorInfo(
                    model_error_type="provider_timeout",
                    message="timed out",
                    retryable=True,
                    provider_request_id="deepseek-timeout-1",
                )
            ),
            {
                "id": "deepseek-response-should-not-be-called",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "late"},
                    }
                ],
            },
        ],
    )
    request = _request(
        provider="deepseek",
        model_id="deepseek-v4-pro",
        retry_policy="provider_retry_v0",
        request_timeout_seconds=0.05,
        request_timeout_policy_facts={
            "provider_timeout_policy": "task_deadline_clamped_provider_request_v0",
            "effective_request_timeout_seconds": 0.05,
        },
    )

    with RunRecorder("deepseek-retry-deadline", tmp_path / "run", task_id="task_001") as recorder:
        response = client.generate(request=request, recorder=recorder)

    assert response.model_error_type == "provider_timeout"
    assert response.terminal_error_type == "provider_timeout"
    assert response.attempt_count == 2
    assert response.retry_count == 1
    assert client.post_count == 1
    assert client.request_timeouts_seen[0] <= 0.05

    first_raw_request = json.loads(
        (tmp_path / "run" / response.provider_attempt_refs[0].relative_path).read_text(
            encoding="utf-8"
        )
    )
    first_request_artifact = json.loads(
        (tmp_path / "run" / first_raw_request["request_ref"]["relative_path"]).read_text(
            encoding="utf-8"
        )
    )
    assert first_request_artifact["request_timeout_seconds"] <= 0.05
    assert (
        first_request_artifact["request_timeout_policy_facts"][
            "provider_timeout_policy"
        ]
        == "task_deadline_clamped_provider_request_v0"
    )
    assert (
        first_request_artifact["request_timeout_policy_facts"][
            "provider_retry_deadline_enforced"
        ]
        is True
    )

    second_attempt = json.loads(
        (tmp_path / "run" / response.provider_attempt_refs[1].relative_path).read_text(
            encoding="utf-8"
        )
    )
    assert second_attempt["error_type"] == "provider_timeout"
    assert second_attempt["terminal"] is True


def test_deepseek_provider_does_not_retry_non_retryable_auth_error(tmp_path: Path):
    client = _DeepSeekSequenceStub(
        model_id="deepseek-v4-pro",
        base_url="https://api.deepseek.com",
        credential=ProviderCredential(value="sk-test-secret-value-1234567890", source="environment"),
        outcomes=[
            ProviderRequestError(
                ProviderErrorInfo(
                    model_error_type="auth_error",
                    message="invalid api key",
                    status_code=401,
                    retryable=False,
                    provider_request_id="deepseek-request-auth",
                )
            )
        ],
    )
    request = _request(
        provider="deepseek",
        model_id="deepseek-v4-pro",
        retry_policy="provider_retry_no_sleep_v0",
    )

    with RunRecorder("deepseek-auth", tmp_path / "run", task_id="task_001") as recorder:
        response = client.generate(request=request, recorder=recorder)

    assert response.model_error_type == "auth_error"
    assert response.attempt_count == 1
    assert response.retry_count == 0
    assert len(response.provider_attempt_refs) == 1


def test_deepseek_http_incomplete_read_is_retryable_transport_error(monkeypatch: pytest.MonkeyPatch):
    class _BrokenResponse:
        headers: dict[str, str] = {}

        def __enter__(self) -> "_BrokenResponse":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            raise http.client.IncompleteRead(b"")

    monkeypatch.setattr("urllib.request.urlopen", lambda *_args, **_kwargs: _BrokenResponse())
    client = DeepSeekProviderClient(
        model_id="deepseek-v4-pro",
        base_url="https://api.deepseek.com",
        credential=ProviderCredential(value="sk-test-secret-value-1234567890", source="environment"),
    )

    with pytest.raises(ProviderRequestError) as exc_info:
        client._post_json(
            {"model": "deepseek-v4-pro", "messages": [{"role": "user", "content": "hello"}]},
            _request(provider="deepseek", model_id="deepseek-v4-pro"),
        )

    assert exc_info.value.info.model_error_type == "provider_error"
    assert exc_info.value.info.retryable is True
    assert exc_info.value.info.payload == {"exception_type": "IncompleteRead"}


def test_provider_finish_reason_length_is_output_token_limit(tmp_path: Path):
    client = _DeepSeekStub(
        model_id="deepseek-v4-pro",
        base_url="https://api.deepseek.com",
        credential=ProviderCredential(value="sk-test-secret-value-1234567890", source="environment"),
        response_payload={
            "id": "deepseek-response-length",
            "choices": [
                {
                    "finish_reason": "length",
                    "message": {"role": "assistant", "content": "partial"},
                }
            ],
        },
    )

    with RunRecorder("deepseek-length", tmp_path / "run", task_id="task_001") as recorder:
        response = client.generate(
            request=_request(provider="deepseek", model_id="deepseek-v4-pro"),
            recorder=recorder,
        )

    assert response.model_error_type == "output_token_limit_reached"
    assert response.terminal_error_type == "output_token_limit_reached"


def test_provider_http_status_error_taxonomy():
    assert classify_http_status(401) == "auth_error"
    assert classify_http_status(429) == "rate_limited"
    assert classify_http_status(408) == "provider_timeout"
    assert classify_http_status(413) == "context_limit"
    assert classify_http_status(422) == "invalid_response"
    assert classify_http_status(503) == "provider_error"
    assert classify_http_status(400, message="maximum context length exceeded") == "context_limit"
    assert classify_http_status(400, message="prompt too long") == "context_limit"
    assert classify_http_status(400, message="context length exceeded") == "context_limit"
    assert classify_http_status(400, payload={"error": {"message": "rate limit reached"}}) == "rate_limited"


def test_deepseek_model_defaults_and_rejects_deprecated_models():
    assert normalize_deepseek_model_id("replay-script-v0") == "deepseek-v4-pro"
    assert normalize_deepseek_model_id("deepseek-v4-flash") == "deepseek-v4-flash"

    with pytest.raises(ConfigError, match="deepseek-chat"):
        normalize_deepseek_model_id("deepseek-chat")

    with pytest.raises(ConfigError, match="deepseek-v4-pro"):
        normalize_deepseek_model_id("deepseek-custom")


def test_deepseek_local_secret_helper_reports_source_without_exposing_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("REPO_HARNESS_DISABLE_LOCAL_SECRET_FILE", raising=False)
    (tmp_path / "reference").mkdir()
    (tmp_path / "reference" / "deepseek_api.md").write_text(
        "local key: sk-local-secret-value-1234567890",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    credential = resolve_deepseek_credential(allow_local_secret_file=True)

    assert credential is not None
    assert credential.source == "local_secret_file_redacted"
    assert credential.value.startswith("sk-")


def test_deepseek_local_secret_helper_is_disabled_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("REPO_HARNESS_DISABLE_LOCAL_SECRET_FILE", raising=False)
    (tmp_path / "reference").mkdir()
    (tmp_path / "reference" / "deepseek_api.md").write_text(
        "local key: sk-local-secret-value-1234567890",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    assert resolve_deepseek_credential() is None


def test_reference_deepseek_api_file_is_gitignored():
    gitignore = (Path(__file__).resolve().parents[2] / ".gitignore").read_text(encoding="utf-8")

    assert "reference/deepseek_api.md" in gitignore


def test_provider_redaction_preserves_non_secret_version_fields():
    payload = {
        "schema_version": "repo_harness_deepseek_provider_response_v0",
        "provider_adapter_version": "repo_harness_deepseek_adapter_v2_v0",
        "api_key": "sk-test-secret-value-1234567890",
        "opaque_value": "repo_harness_deepseek_provider_response_v0",
    }

    redacted = redact_provider_payload(payload)

    assert redacted["schema_version"] == "repo_harness_deepseek_provider_response_v0"
    assert redacted["provider_adapter_version"] == "repo_harness_deepseek_adapter_v2_v0"
    assert redacted["api_key"] == REDACTED_CREDENTIAL
    assert redacted["opaque_value"] == "repo_harness_deepseek_provider_response_v0"


def test_provider_redaction_redacts_explicit_secrets_in_version_fields():
    payload = {
        "schema_version": "sk-test-secret-value-1234567890",
        "provider_adapter_version": "Bearer sk-test-secret-value-1234567890",
        "nested": {
            "fallback_policy_version": "Bearer visible-token-12345",
        },
    }

    redacted = redact_provider_payload(payload)

    assert redacted["schema_version"] == REDACTED_CREDENTIAL
    assert redacted["provider_adapter_version"] == f"Bearer {REDACTED_CREDENTIAL}"
    assert redacted["nested"]["fallback_policy_version"] == f"Bearer {REDACTED_CREDENTIAL}"


def test_openai_provider_uses_sdk_shape_with_injected_client(tmp_path: Path):
    client = OpenAIProviderClient(
        model_id="gpt-5-mini",
        credential=ProviderCredential(value="sk-test-openai-secret-1234567890", source="environment"),
        client_factory=lambda api_key: _FakeOpenAIClient(api_key),
    )
    request = _request(provider="openai", model_id="gpt-5-mini")
    with RunRecorder("openai", tmp_path / "run", task_id="task_001") as recorder:
        response = client.generate(request=request, recorder=recorder)

    assert response.model_error_type is None
    assert response.assistant_message.content == "done"
    assert response.model_call_event is not None
    assert response.model_call_event.provider == "openai"
    raw_text = (tmp_path / "run" / response.raw_provider_request_ref.relative_path).read_text(
        encoding="utf-8"
    )
    assert "sk-test-openai-secret" not in raw_text


def test_openai_provider_retries_retryable_error_and_records_attempts(tmp_path: Path):
    client = _OpenAISequenceStub(
        model_id="gpt-5-mini",
        credential=ProviderCredential(value="sk-test-openai-secret-1234567890", source="environment"),
        outcomes=[
            ProviderRequestError(
                ProviderErrorInfo(
                    model_error_type="provider_timeout",
                    message="timed out",
                    retryable=True,
                    provider_request_id="openai-timeout-1",
                )
            ),
            {
                "id": "openai-response-after-retry",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "done"},
                    }
                ],
                "usage": {"prompt_tokens": 13, "completion_tokens": 2},
            },
        ],
    )
    request = _request(
        provider="openai",
        model_id="gpt-5-mini",
        retry_policy="provider_retry_no_sleep_v0",
    )

    with RunRecorder("openai-retry", tmp_path / "run", task_id="task_001") as recorder:
        response = client.generate(request=request, recorder=recorder)

    assert response.model_error_type is None
    assert response.attempt_count == 2
    assert response.retry_count == 1
    assert len(response.provider_attempt_refs) == 2
    assert response.model_call_event is not None
    assert response.model_call_event.retry_policy_ref == response.retry_policy_ref
    assert response.model_call_event.retry_count == 1


def test_openai_retry_stops_before_delay_would_exceed_provider_deadline(tmp_path: Path):
    client = _OpenAISequenceStub(
        model_id="gpt-5-mini",
        credential=ProviderCredential(value="sk-test-openai-secret-1234567890", source="environment"),
        outcomes=[
            ProviderRequestError(
                ProviderErrorInfo(
                    model_error_type="provider_timeout",
                    message="timed out",
                    retryable=True,
                    provider_request_id="openai-timeout-1",
                )
            ),
            {
                "id": "openai-response-should-not-be-called",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "late"},
                    }
                ],
            },
        ],
    )
    request = _request(
        provider="openai",
        model_id="gpt-5-mini",
        retry_policy="provider_retry_v0",
        request_timeout_seconds=0.05,
        request_timeout_policy_facts={
            "provider_timeout_policy": "task_deadline_clamped_provider_request_v0",
            "effective_request_timeout_seconds": 0.05,
        },
    )

    with RunRecorder("openai-retry-deadline", tmp_path / "run", task_id="task_001") as recorder:
        response = client.generate(request=request, recorder=recorder)

    assert response.model_error_type == "provider_timeout"
    assert response.terminal_error_type == "provider_timeout"
    assert response.attempt_count == 2
    assert response.retry_count == 1
    assert client.post_count == 1
    assert client.request_timeouts_seen[0] <= 0.05

    first_attempt = json.loads(
        (tmp_path / "run" / response.provider_attempt_refs[0].relative_path).read_text(
            encoding="utf-8"
        )
    )
    first_request_artifact = json.loads(
        (tmp_path / "run" / first_attempt["request_ref"]["relative_path"]).read_text(
            encoding="utf-8"
        )
    )
    assert first_request_artifact["request_timeout_seconds"] <= 0.05
    assert (
        first_request_artifact["request_timeout_policy_facts"][
            "provider_retry_deadline_enforced"
        ]
        is True
    )


def test_openai_provider_does_not_retry_non_retryable_auth_error(tmp_path: Path):
    client = _OpenAISequenceStub(
        model_id="gpt-5-mini",
        credential=ProviderCredential(value="sk-test-openai-secret-1234567890", source="environment"),
        outcomes=[
            ProviderRequestError(
                ProviderErrorInfo(
                    model_error_type="auth_error",
                    message="invalid api key",
                    status_code=401,
                    retryable=False,
                    provider_request_id="openai-auth",
                )
            )
        ],
    )
    request = _request(
        provider="openai",
        model_id="gpt-5-mini",
        retry_policy="provider_retry_no_sleep_v0",
    )

    with RunRecorder("openai-auth", tmp_path / "run", task_id="task_001") as recorder:
        response = client.generate(request=request, recorder=recorder)

    assert response.model_error_type == "auth_error"
    assert response.attempt_count == 1
    assert response.retry_count == 0
    assert len(response.provider_attempt_refs) == 1


def test_openai_http_incomplete_read_is_retryable_transport_error(monkeypatch: pytest.MonkeyPatch):
    class _BrokenResponse:
        headers: dict[str, str] = {}

        def __enter__(self) -> "_BrokenResponse":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            raise http.client.IncompleteRead(b"")

    monkeypatch.setattr("urllib.request.urlopen", lambda *_args, **_kwargs: _BrokenResponse())
    client = OpenAIProviderClient(
        model_id="gpt-5-mini",
        credential=ProviderCredential(value="sk-test-openai-secret-1234567890", source="environment"),
    )

    with pytest.raises(ProviderRequestError) as exc_info:
        client._post_json(
            {"model": "gpt-5-mini", "messages": [{"role": "user", "content": "hello"}]},
            _request(provider="openai", model_id="gpt-5-mini"),
        )

    assert exc_info.value.info.model_error_type == "provider_error"
    assert exc_info.value.info.retryable is True
    assert exc_info.value.info.payload == {"exception_type": "IncompleteRead"}


def test_openai_gpt5_chat_body_uses_max_completion_tokens():
    body = {
        "model": "gpt-5.4-nano",
        "messages": [{"role": "user", "content": "hello"}],
        "max_tokens": 32,
        "temperature": 0.0,
    }

    payload = _openai_sdk_body(body)

    assert "max_tokens" not in payload
    assert "temperature" not in payload
    assert payload["max_completion_tokens"] == 32


class _DeepSeekStub(DeepSeekProviderClient):
    def __init__(self, *, response_payload: dict[str, Any], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.response_payload = response_payload
        self.last_body: dict[str, Any] = {}

    def _post_json(self, body: dict[str, Any], request: ModelRequestContext) -> tuple[dict[str, Any], str | None]:
        self.last_body = body
        return self.response_payload, "deepseek-request-1"


class _DeepSeekSequenceStub(DeepSeekProviderClient):
    def __init__(self, *, outcomes: list[Any], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.outcomes = list(outcomes)
        self.last_body: dict[str, Any] = {}
        self.post_count = 0
        self.request_timeouts_seen: list[float] = []

    def _post_json(self, body: dict[str, Any], request: ModelRequestContext) -> tuple[dict[str, Any], str | None]:
        self.last_body = body
        self.post_count += 1
        self.request_timeouts_seen.append(request.request_timeout_seconds)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, ProviderRequestError):
            raise outcome
        return outcome, str(outcome.get("id") or "deepseek-request-sequence")


class _FakeOpenAIClient:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.chat = _FakeChat()


class _FakeChat:
    def __init__(self) -> None:
        self.completions = _FakeCompletions()


class _FakeCompletions:
    def create(self, **kwargs: Any) -> dict[str, Any]:
        return {
            "id": "openai-response-1",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": "done"},
                }
            ],
            "usage": {"prompt_tokens": 5, "completion_tokens": 1},
        }


class _OpenAISequenceStub(OpenAIProviderClient):
    def __init__(self, *, outcomes: list[Any], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.outcomes = list(outcomes)
        self.post_count = 0
        self.request_timeouts_seen: list[float] = []

    def _create_completion(self, body: dict[str, Any], request: ModelRequestContext) -> dict[str, Any]:
        self.post_count += 1
        self.request_timeouts_seen.append(request.request_timeout_seconds)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, ProviderRequestError):
            raise outcome
        return outcome


def _request(
    *,
    provider: str,
    model_id: str,
    prepared_messages: list[dict[str, Any]] | None = None,
    provider_specific_options: dict[str, Any] | None = None,
    retry_policy: str = "none",
    request_timeout_seconds: float = 10,
    request_timeout_policy_facts: dict[str, Any] | None = None,
) -> ModelRequestContext:
    return ModelRequestContext(
        run_id=f"{provider}-run",
        task_id="task_001",
        turn=1,
        model_call_id=f"{provider}_model_call_0001",
        prepared_messages=prepared_messages
        or [
            {"role": "system", "content": "system"},
            {"role": "user", "content": {"task": "fix calculator"}},
        ],
        prepared_messages_ref=_artifact_ref("prepared_messages"),
        model_input_hash="a" * 64,
        context_revision=1,
        provider_message_format="repo_harness_messages_v0",
        context_truncation_facts={},
        omitted_context_facts={},
        generation_config={"temperature": 0.0, "max_output_tokens": 128},
        provider_model_settings={},
        allowed_tool_definitions=[
            {
                "name": "read_file",
                "description": "Read a file",
                "model_visible_prompt": "Use read_file with path.",
                "input_schema": {"type": "object", "required": ["path"]},
            }
        ],
        tool_choice="auto",
        tool_schema_snapshot_ref=_artifact_ref("tool_schema"),
        provider_options=ModelProviderOptions(
            provider=provider,
            model_id=model_id,
            provider_specific_options=provider_specific_options or {"thinking": {"type": "disabled"}},
        ),
        scaffold_id="simple_react",
        scaffold_phase="react",
        run_config_facts_ref=RunConfigFactsRef(sha256="b" * 64),
        budget_state={"turn_count": 1},
        request_timeout_seconds=request_timeout_seconds,
        request_timeout_policy_facts=request_timeout_policy_facts or {},
        raw_request_logging_policy="redact_secrets",
        credential_policy=ProviderCredentialPolicy(
            credential_source="env_only",
            required_env_vars=["DEEPSEEK_API_KEY"] if provider == "deepseek" else ["OPENAI_API_KEY"],
        ),
        retry_policy=retry_policy,
    )


def _artifact_ref(kind: str) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=kind,
        relative_path=f"artifacts/{kind}.json",
        kind=kind,
        sha256="0" * 64,
        size_bytes=0,
    )
