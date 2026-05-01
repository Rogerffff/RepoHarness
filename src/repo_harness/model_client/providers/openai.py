"""OpenAI fallback provider adapter using the official Python SDK when available."""

from __future__ import annotations

import importlib
import json
import os
import time
from typing import Any

from repo_harness.errors import ConfigError
from repo_harness.model_client.providers.common import (
    ProviderCredential,
    ProviderErrorInfo,
    ProviderRequestError,
    build_chat_completion_payload,
    classify_http_status,
    duration_ms_since,
    model_error_response,
    provider_error_payload,
    response_from_provider_payload,
    write_provider_request_artifact,
    write_provider_response_artifact,
)
from repo_harness.model_client.redaction import sanitize_provider_error_message
from repo_harness.model_client.schemas import ModelRequestContext, ModelResponse
from repo_harness.trajectory import RunRecorder

OPENAI_PROVIDER_VERSION = "repo_harness_openai_provider_v0"
OPENAI_DEFAULT_MODEL = "gpt-5-mini"
OPENAI_BASE_URL = "https://api.openai.com/v1"
OPENAI_ENDPOINT_CATEGORY = "openai_chat_completions_sdk"
OPENAI_OFFICIAL_DOCS_URL = "https://developers.openai.com/api/docs/quickstart?language=python"


class OpenAIProviderClient:
    def __init__(
        self,
        *,
        model_id: str = OPENAI_DEFAULT_MODEL,
        credential: ProviderCredential,
        client_factory: Any | None = None,
    ) -> None:
        self.model_id = model_id
        self.credential = credential
        self._client_factory = client_factory

    @classmethod
    def from_options(
        cls,
        *,
        model_id: str = OPENAI_DEFAULT_MODEL,
    ) -> "OpenAIProviderClient":
        credential = resolve_openai_credential()
        if credential is None:
            raise ConfigError("model.provider=openai 缺少 OPENAI_API_KEY 凭证。")
        if not openai_sdk_available():
            raise ConfigError("model.provider=openai 需要安装官方 openai Python SDK。")
        return cls(model_id=model_id, credential=credential)

    def generate(self, *, request: ModelRequestContext, recorder: RunRecorder) -> ModelResponse:
        started = time.monotonic()
        request_payload = build_chat_completion_payload(
            request,
            model_id=self.model_id,
            provider="openai",
            base_url=OPENAI_BASE_URL,
        )
        request_payload["provider_adapter_version"] = OPENAI_PROVIDER_VERSION
        request_payload["credential_source"] = self.credential.source
        raw_request_ref = write_provider_request_artifact(
            provider="openai",
            recorder=recorder,
            payload=request_payload,
        )
        try:
            response_payload = self._create_completion(request_payload["body"], request)
        except ProviderRequestError as exc:
            error = exc.info
            raw_response_ref = write_provider_response_artifact(
                provider="openai",
                recorder=recorder,
                payload=provider_error_payload(provider="openai", error=error),
            )
            return model_error_response(
                provider="openai",
                request=request,
                raw_request_ref=raw_request_ref,
                raw_response_ref=raw_response_ref,
                error=error,
                duration_ms=duration_ms_since(started),
            )
        raw_response_ref = write_provider_response_artifact(
            provider="openai",
            recorder=recorder,
            payload={
                "schema_version": "repo_harness_openai_provider_response_v0",
                "provider": "openai",
                "provider_adapter_version": OPENAI_PROVIDER_VERSION,
                "status": "ok",
                "response": response_payload,
            },
        )
        return response_from_provider_payload(
            provider="openai",
            request=request,
            raw_request_ref=raw_request_ref,
            raw_response_ref=raw_response_ref,
            payload=response_payload,
            duration_ms=duration_ms_since(started),
            provider_request_id=response_payload.get("_request_id") or response_payload.get("id"),
        )

    def _create_completion(self, body: dict[str, Any], request: ModelRequestContext) -> dict[str, Any]:
        try:
            client = self._build_client()
            response = client.chat.completions.create(
                **_sdk_body(body),
                timeout=request.request_timeout_seconds,
            )
        except Exception as exc:  # noqa: BLE001 - SDK exception classes vary by installed version
            raise ProviderRequestError(_classify_openai_exception(exc)) from exc
        payload = _object_to_dict(response)
        if not payload:
            raise ProviderRequestError(
                ProviderErrorInfo(
                    model_error_type="invalid_response",
                    message="OpenAI SDK returned an empty response object",
                )
            )
        return payload

    def _build_client(self) -> Any:
        if self._client_factory is not None:
            return self._client_factory(api_key=self.credential.value)
        module = importlib.import_module("openai")
        return module.OpenAI(api_key=self.credential.value)


def resolve_openai_credential() -> ProviderCredential | None:
    value = os.environ.get("OPENAI_API_KEY")
    if not value:
        return None
    return ProviderCredential(value=value, source="environment")


def openai_credential_status() -> dict[str, str]:
    credential = resolve_openai_credential()
    if credential is None:
        return {"credential_status": "missing", "credential_source": "none"}
    return {"credential_status": "present", "credential_source": credential.source}


def openai_sdk_available() -> bool:
    return importlib.util.find_spec("openai") is not None


def _sdk_body(body: dict[str, Any]) -> dict[str, Any]:
    payload = dict(body)
    payload.pop("extra_body", None)
    return payload


def _classify_openai_exception(exc: Exception) -> ProviderErrorInfo:
    status_code = getattr(exc, "status_code", None)
    payload = _exception_payload(exc)
    message = sanitize_provider_error_message(str(exc))
    if isinstance(status_code, int):
        error_type = classify_http_status(status_code, payload=payload, message=message)
    elif "timed out" in message.lower() or "timeout" in type(exc).__name__.lower():
        error_type = "provider_timeout"
    else:
        error_type = "provider_error"
    return ProviderErrorInfo(
        model_error_type=error_type,
        message=message,
        status_code=status_code if isinstance(status_code, int) else None,
        retryable=error_type in {"rate_limited", "provider_timeout", "provider_error"},
        provider_request_id=getattr(exc, "request_id", None),
        payload={"exception_type": type(exc).__name__, **payload},
    )


def _exception_payload(exc: Exception) -> dict[str, Any]:
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            data = response.json()
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        return body
    return {}


def _object_to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="json")
        return dumped if isinstance(dumped, dict) else {}
    if hasattr(value, "to_dict"):
        dumped = value.to_dict()
        return dumped if isinstance(dumped, dict) else {}
    if hasattr(value, "to_json"):
        try:
            dumped = json.loads(value.to_json())
            return dumped if isinstance(dumped, dict) else {}
        except Exception:
            return {}
    return {}
