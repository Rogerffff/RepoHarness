import json
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
from repo_harness.model_client.providers.common import ProviderCredential
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


def test_provider_http_status_error_taxonomy():
    assert classify_http_status(401) == "auth_error"
    assert classify_http_status(429) == "rate_limited"
    assert classify_http_status(408) == "provider_timeout"
    assert classify_http_status(413) == "context_limit"
    assert classify_http_status(422) == "invalid_response"
    assert classify_http_status(503) == "provider_error"
    assert classify_http_status(400, message="maximum context length exceeded") == "context_limit"
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


def _request(
    *,
    provider: str,
    model_id: str,
    prepared_messages: list[dict[str, Any]] | None = None,
    provider_specific_options: dict[str, Any] | None = None,
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
        request_timeout_seconds=10,
        raw_request_logging_policy="redact_secrets",
        credential_policy=ProviderCredentialPolicy(
            credential_source="env_only",
            required_env_vars=["DEEPSEEK_API_KEY"] if provider == "deepseek" else ["OPENAI_API_KEY"],
        ),
        retry_policy="none",
    )


def _artifact_ref(kind: str) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=kind,
        relative_path=f"artifacts/{kind}.json",
        kind=kind,
        sha256="0" * 64,
        size_bytes=0,
    )
