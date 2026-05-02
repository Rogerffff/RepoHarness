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
    assert redacted["opaque_value"] == REDACTED_CREDENTIAL


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
    assert redacted["provider_adapter_version"] == REDACTED_CREDENTIAL
    assert redacted["nested"]["fallback_policy_version"] == REDACTED_CREDENTIAL


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


def _request(*, provider: str, model_id: str) -> ModelRequestContext:
    return ModelRequestContext(
        run_id=f"{provider}-run",
        task_id="task_001",
        turn=1,
        model_call_id=f"{provider}_model_call_0001",
        prepared_messages=[
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
            provider_specific_options={"thinking": {"type": "disabled"}},
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
