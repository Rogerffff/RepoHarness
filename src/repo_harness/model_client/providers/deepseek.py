"""DeepSeek OpenAI-compatible provider adapter."""

from __future__ import annotations

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
    build_chat_completion_payload,
    classify_http_status,
    duration_ms_since,
    model_error_response,
    provider_error_payload,
    response_from_provider_payload,
    write_provider_request_artifact,
    write_provider_response_artifact,
)
from repo_harness.model_client.redaction import REDACTED_CREDENTIAL, sanitize_provider_error_message
from repo_harness.model_client.schemas import ModelRequestContext, ModelResponse
from repo_harness.trajectory import RunRecorder

DEEPSEEK_PROVIDER_VERSION = "repo_harness_deepseek_provider_v0"
DEEPSEEK_DEFAULT_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_DEFAULT_MODEL = "deepseek-v4-pro"
DEEPSEEK_ALLOWED_MODELS = {"deepseek-v4-pro", "deepseek-v4-flash"}
DEEPSEEK_DEPRECATED_MODELS = {"deepseek-chat", "deepseek-reasoner"}
DEEPSEEK_OFFICIAL_DOCS_URL = "https://api-docs.deepseek.com/zh-cn/"
DEEPSEEK_CHAT_COMPLETIONS_PATH = "/chat/completions"


class DeepSeekProviderClient:
    def __init__(
        self,
        *,
        model_id: str = DEEPSEEK_DEFAULT_MODEL,
        base_url: str = DEEPSEEK_DEFAULT_BASE_URL,
        credential: ProviderCredential,
    ) -> None:
        self.model_id = normalize_deepseek_model_id(model_id)
        self.base_url = base_url.rstrip("/")
        self.credential = credential

    @classmethod
    def from_options(
        cls,
        *,
        model_id: str = DEEPSEEK_DEFAULT_MODEL,
        base_url: str = DEEPSEEK_DEFAULT_BASE_URL,
        allow_local_secret_file: bool = False,
    ) -> "DeepSeekProviderClient":
        model_id = normalize_deepseek_model_id(model_id)
        credential = resolve_deepseek_credential(allow_local_secret_file=allow_local_secret_file)
        if credential is None:
            raise ConfigError("model.provider=deepseek 缺少 DEEPSEEK_API_KEY 凭证。")
        return cls(model_id=model_id, base_url=base_url, credential=credential)

    def generate(self, *, request: ModelRequestContext, recorder: RunRecorder) -> ModelResponse:
        started = time.monotonic()
        request_payload = build_chat_completion_payload(
            request,
            model_id=self.model_id,
            provider="deepseek",
            base_url=self.base_url,
            include_deepseek_options=True,
        )
        request_payload["provider_adapter_version"] = DEEPSEEK_PROVIDER_VERSION
        request_payload["credential_source"] = self.credential.source
        raw_request_ref = write_provider_request_artifact(
            provider="deepseek",
            recorder=recorder,
            payload=request_payload,
        )
        try:
            response_payload, provider_request_id = self._post_json(request_payload["body"], request)
        except ProviderRequestError as exc:
            error = exc.info
            raw_response_ref = write_provider_response_artifact(
                provider="deepseek",
                recorder=recorder,
                payload=provider_error_payload(provider="deepseek", error=error),
            )
            return model_error_response(
                provider="deepseek",
                request=request,
                raw_request_ref=raw_request_ref,
                raw_response_ref=raw_response_ref,
                error=error,
                duration_ms=duration_ms_since(started),
            )
        raw_response_ref = write_provider_response_artifact(
            provider="deepseek",
            recorder=recorder,
            payload={
                "schema_version": "repo_harness_deepseek_provider_response_v0",
                "provider": "deepseek",
                "provider_adapter_version": DEEPSEEK_PROVIDER_VERSION,
                "status": "ok",
                "provider_request_id": provider_request_id,
                "response": response_payload,
            },
        )
        return response_from_provider_payload(
            provider="deepseek",
            request=request,
            raw_request_ref=raw_request_ref,
            raw_response_ref=raw_response_ref,
            payload=response_payload,
            duration_ms=duration_ms_since(started),
            provider_request_id=provider_request_id,
        )

    def _post_json(
        self,
        body: dict[str, Any],
        request: ModelRequestContext,
    ) -> tuple[dict[str, Any], str | None]:
        url = f"{self.base_url}{DEEPSEEK_CHAT_COMPLETIONS_PATH}"
        data = json.dumps(_sdk_body_to_http_body(body), ensure_ascii=False).encode("utf-8")
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
                return payload, response.headers.get("x-request-id") or payload.get("id")
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
            raise ProviderRequestError(
                ProviderErrorInfo(
                    model_error_type=classify_http_status(
                        exc.code,
                        payload=payload,
                        message=_error_message_from_payload(payload),
                    ),
                    message=_error_message_from_payload(payload) or f"DeepSeek HTTP {exc.code}",
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


def normalize_deepseek_model_id(model_id: str | None) -> str:
    if model_id in {None, "", "replay-script-v0"}:
        return DEEPSEEK_DEFAULT_MODEL
    if model_id in DEEPSEEK_DEPRECATED_MODELS:
        raise ConfigError(
            "DeepSeek Stage 11 不允许使用即将弃用的 deepseek-chat 或 deepseek-reasoner；"
            "请使用 deepseek-v4-pro 或 deepseek-v4-flash。"
        )
    if model_id not in DEEPSEEK_ALLOWED_MODELS:
        raise ConfigError(
            "DeepSeek Stage 11 只允许 deepseek-v4-pro 或 deepseek-v4-flash。"
        )
    return str(model_id)


def resolve_deepseek_credential(*, allow_local_secret_file: bool = False) -> ProviderCredential | None:
    value = os.environ.get("DEEPSEEK_API_KEY")
    if value:
        return ProviderCredential(value=value, source="environment")
    if os.environ.get("REPO_HARNESS_DISABLE_LOCAL_SECRET_FILE") == "1":
        return None
    if not allow_local_secret_file:
        return None
    local_secret = _read_local_deepseek_secret()
    if local_secret:
        return ProviderCredential(value=local_secret, source="local_secret_file_redacted")
    return None


def deepseek_credential_status(*, allow_local_secret_file: bool = False) -> dict[str, str]:
    credential = resolve_deepseek_credential(allow_local_secret_file=allow_local_secret_file)
    if credential is None:
        return {"credential_status": "missing", "credential_source": "none"}
    return {"credential_status": "present", "credential_source": credential.source}


def _read_local_deepseek_secret() -> str | None:
    path = Path("reference/deepseek_api.md")
    if not path.exists() or not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    match = re.search(r"\bsk-[A-Za-z0-9_\-]{8,}\b", text)
    return match.group(0) if match else None


def _sdk_body_to_http_body(body: dict[str, Any]) -> dict[str, Any]:
    http_body = dict(body)
    extra_body = http_body.pop("extra_body", None)
    if isinstance(extra_body, dict):
        http_body.update(extra_body)
    return http_body


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
