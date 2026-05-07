"""OpenAI provider adapter for Chat Completions-compatible RepoHarness runs."""

from __future__ import annotations

import importlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from repo_harness.errors import ConfigError
from repo_harness.model_client.providers.common import (
    ProviderCredential,
    ProviderErrorInfo,
    ProviderRequestError,
    attach_provider_retry_metadata,
    build_chat_completion_payload,
    classify_http_status,
    duration_ms_since,
    model_error_response,
    provider_error_payload,
    retry_delay_ms,
    retry_policy_from_request,
    response_from_provider_payload,
    should_retry_provider_error,
    write_provider_attempt_artifact,
    write_provider_request_artifact,
    write_provider_retry_policy_artifact,
    write_provider_response_artifact,
)
from repo_harness.model_client.redaction import sanitize_provider_error_message
from repo_harness.model_client.schemas import ModelRequestContext, ModelResponse
from repo_harness.trajectory import RunRecorder

OPENAI_PROVIDER_VERSION = "repo_harness_openai_provider_v0"
OPENAI_DEFAULT_MODEL = "gpt-5.4-nano"
OPENAI_BASE_URL = "https://api.openai.com/v1"
OPENAI_ENDPOINT_CATEGORY = "openai_chat_completions_sdk"
OPENAI_OFFICIAL_DOCS_URL = "https://developers.openai.com/api/docs/quickstart?language=python"
OPENAI_PRICING_DOCS_URL = "https://developers.openai.com/api/docs/pricing"
OPENAI_CHAT_COMPLETIONS_PATH = "/chat/completions"
OPENAI_STAGE3_ALLOWED_MODELS = {
    "gpt-5.4-nano",
    "gpt-5.5",
    "gpt-5-mini",
}


class OpenAIProviderClient:
    def __init__(
        self,
        *,
        model_id: str = OPENAI_DEFAULT_MODEL,
        base_url: str = OPENAI_BASE_URL,
        credential: ProviderCredential,
        client_factory: Any | None = None,
    ) -> None:
        self.model_id = normalize_openai_model_id(model_id)
        self.base_url = base_url.rstrip("/")
        self.credential = credential
        self._client_factory = client_factory

    @classmethod
    def from_options(
        cls,
        *,
        model_id: str = OPENAI_DEFAULT_MODEL,
        base_url: str = OPENAI_BASE_URL,
        allow_local_secret_file: bool = False,
    ) -> "OpenAIProviderClient":
        model_id = normalize_openai_model_id(model_id)
        credential = resolve_openai_credential(allow_local_secret_file=allow_local_secret_file)
        if credential is None:
            raise ConfigError("model.provider=openai 缺少 OPENAI_API_KEY 凭证。")
        return cls(model_id=model_id, base_url=base_url, credential=credential)

    def generate(self, *, request: ModelRequestContext, recorder: RunRecorder) -> ModelResponse:
        started = time.monotonic()
        request_payload = build_chat_completion_payload(
            request,
            model_id=self.model_id,
            provider="openai",
            base_url=self.base_url,
        )
        request_payload["provider_adapter_version"] = OPENAI_PROVIDER_VERSION
        request_payload["credential_source"] = self.credential.source
        retry_policy = retry_policy_from_request(request)
        retry_policy_ref = write_provider_retry_policy_artifact(
            provider="openai",
            recorder=recorder,
            request=request,
            policy=retry_policy,
        )
        attempt_refs = []
        for attempt_index in range(1, retry_policy.max_attempts + 1):
            delay_ms = retry_delay_ms(attempt_index=attempt_index - 1, policy=retry_policy)
            if delay_ms and retry_policy.sleep_enabled:
                time.sleep(delay_ms / 1000)
            attempt_payload = {
                **request_payload,
                "attempt_index": attempt_index,
                "retry_policy_ref": retry_policy_ref.model_dump(mode="json"),
            }
            raw_request_ref = write_provider_request_artifact(
                provider="openai",
                recorder=recorder,
                payload=attempt_payload,
                request=request,
            )
            try:
                response_payload = self._create_completion(request_payload["body"], request)
            except ProviderRequestError as exc:
                error = exc.info
                retryable = should_retry_provider_error(
                    error=error,
                    attempt_index=attempt_index,
                    policy=retry_policy,
                )
                raw_response_ref = write_provider_response_artifact(
                    provider="openai",
                    recorder=recorder,
                    payload=provider_error_payload(provider="openai", error=error),
                    request=request,
                    raw_request_ref=raw_request_ref,
                )
                attempt_refs.append(
                    write_provider_attempt_artifact(
                        provider="openai",
                        recorder=recorder,
                        request=request,
                        attempt_index=attempt_index,
                        retryable=retryable,
                        error_type=error.model_error_type,
                        delay_ms=delay_ms,
                        request_ref=raw_request_ref,
                        response_ref=raw_response_ref,
                        provider_request_id=error.provider_request_id,
                        duration_ms=duration_ms_since(started),
                        terminal=not retryable,
                    )
                )
                if retryable:
                    continue
                response = model_error_response(
                    provider="openai",
                    request=request,
                    raw_request_ref=raw_request_ref,
                    raw_response_ref=raw_response_ref,
                    error=error,
                    duration_ms=duration_ms_since(started),
                )
                return attach_provider_retry_metadata(
                    response,
                    attempt_refs=attempt_refs,
                    retry_policy_ref=retry_policy_ref,
                    terminal_error_type=error.model_error_type,
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
                request=request,
                raw_request_ref=raw_request_ref,
            )
            provider_request_id = response_payload.get("_request_id") or response_payload.get("id")
            response = response_from_provider_payload(
                provider="openai",
                request=request,
                raw_request_ref=raw_request_ref,
                raw_response_ref=raw_response_ref,
                payload=response_payload,
                duration_ms=duration_ms_since(started),
                provider_request_id=provider_request_id,
            )
            terminal_error_type = response.model_error_type
            attempt_refs.append(
                write_provider_attempt_artifact(
                    provider="openai",
                    recorder=recorder,
                    request=request,
                    attempt_index=attempt_index,
                    retryable=False,
                    error_type=terminal_error_type,
                    delay_ms=delay_ms,
                    request_ref=raw_request_ref,
                    response_ref=raw_response_ref,
                    provider_request_id=provider_request_id,
                    duration_ms=duration_ms_since(started),
                    terminal=True,
                )
            )
            return attach_provider_retry_metadata(
                response,
                attempt_refs=attempt_refs,
                retry_policy_ref=retry_policy_ref,
                terminal_error_type=terminal_error_type,
            )
        raise AssertionError("provider retry loop exhausted without terminal response")

    def _create_completion(self, body: dict[str, Any], request: ModelRequestContext) -> dict[str, Any]:
        if self._client_factory is None and not openai_sdk_available():
            return self._post_json(body, request)
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

    def _post_json(
        self,
        body: dict[str, Any],
        request: ModelRequestContext,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{OPENAI_CHAT_COMPLETIONS_PATH}"
        data = json.dumps(_sdk_body(body), ensure_ascii=False).encode("utf-8")
        http_request = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.credential.value}",
            },
        )
        try:
            with urllib.request.urlopen(http_request, timeout=request.request_timeout_seconds) as response:
                text = response.read().decode("utf-8")
                payload = json.loads(text)
                if isinstance(payload, dict):
                    request_id = response.headers.get("x-request-id")
                    if request_id and "_request_id" not in payload:
                        payload["_request_id"] = request_id
                    return payload
                raise ProviderRequestError(
                    ProviderErrorInfo(
                        model_error_type="invalid_response",
                        message="OpenAI HTTP response was not a JSON object",
                    )
                )
        except TimeoutError as exc:
            raise ProviderRequestError(
                ProviderErrorInfo(
                    model_error_type="provider_timeout",
                    message=sanitize_provider_error_message(str(exc)),
                    retryable=True,
                )
            ) from exc
        except urllib.error.HTTPError as exc:
            payload = _read_error_payload(exc)
            message = _error_message_from_payload(payload) or f"OpenAI HTTP {exc.code}"
            error_type = classify_http_status(exc.code, payload=payload, message=message)
            raise ProviderRequestError(
                ProviderErrorInfo(
                    model_error_type=error_type,
                    message=message,
                    status_code=exc.code,
                    retryable=exc.code in {429, 500, 503, 504},
                    provider_request_id=exc.headers.get("x-request-id"),
                    payload=payload,
                )
            ) from exc
        except urllib.error.URLError as exc:
            reason = sanitize_provider_error_message(str(exc.reason))
            error_type = "provider_timeout" if "timed out" in reason.lower() else "provider_error"
            raise ProviderRequestError(
                ProviderErrorInfo(
                    model_error_type=error_type,
                    message=reason,
                    retryable=True,
                )
            ) from exc
        except json.JSONDecodeError as exc:
            raise ProviderRequestError(
                ProviderErrorInfo(
                    model_error_type="invalid_response",
                    message=sanitize_provider_error_message(str(exc)),
                )
            ) from exc

    def _build_client(self) -> Any:
        if self._client_factory is not None:
            return self._client_factory(api_key=self.credential.value)
        module = importlib.import_module("openai")
        return module.OpenAI(api_key=self.credential.value)


def normalize_openai_model_id(model_id: str | None) -> str:
    if model_id in {None, "", "replay-script-v0"}:
        return OPENAI_DEFAULT_MODEL
    if model_id not in OPENAI_STAGE3_ALLOWED_MODELS:
        raise ConfigError(
            "OpenAI V5 provider comparison 当前只允许 gpt-5.4-nano、gpt-5.5 或 gpt-5-mini。"
        )
    return str(model_id)


def resolve_openai_credential(*, allow_local_secret_file: bool = False) -> ProviderCredential | None:
    value = os.environ.get("OPENAI_API_KEY")
    if not value:
        if os.environ.get("REPO_HARNESS_DISABLE_LOCAL_SECRET_FILE") == "1":
            return None
        if not allow_local_secret_file:
            return None
        local_secret = _read_local_openai_secret()
        if local_secret:
            return ProviderCredential(value=local_secret, source="local_secret_file_redacted")
        return None
    return ProviderCredential(value=value, source="environment")


def openai_credential_status(*, allow_local_secret_file: bool = False) -> dict[str, str]:
    credential = resolve_openai_credential(allow_local_secret_file=allow_local_secret_file)
    if credential is None:
        return {"credential_status": "missing", "credential_source": "none"}
    return {"credential_status": "present", "credential_source": credential.source}


def openai_sdk_available() -> bool:
    return importlib.util.find_spec("openai") is not None


def _sdk_body(body: dict[str, Any]) -> dict[str, Any]:
    payload = dict(body)
    payload.pop("extra_body", None)
    model_id = str(payload.get("model") or "")
    if model_id.startswith("gpt-5") and "max_tokens" in payload:
        payload["max_completion_tokens"] = payload.pop("max_tokens")
    if model_id.startswith("gpt-5"):
        payload.pop("temperature", None)
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


def _read_local_openai_secret() -> str | None:
    path = Path("reference/deepseek_api.md")
    if not path.exists() or not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    match = re.search(r"(?im)^\s*OPENAI_API_KEY\s*:\s*(sk-[^\s`]+)\s*$", text)
    return match.group(1) if match else None


def _read_error_payload(exc: urllib.error.HTTPError) -> dict[str, Any]:
    try:
        text = exc.read().decode("utf-8")
    except Exception:
        return {"error": {"message": f"HTTP {exc.code}"}}
    try:
        payload = json.loads(text)
        return payload if isinstance(payload, dict) else {"raw_error": text}
    except json.JSONDecodeError:
        return {"raw_error": text}


def _error_message_from_payload(payload: dict[str, Any]) -> str | None:
    error = payload.get("error")
    if isinstance(error, dict):
        message = error.get("message")
        return sanitize_provider_error_message(str(message)) if message is not None else None
    message = payload.get("message")
    return sanitize_provider_error_message(str(message)) if message is not None else None


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
