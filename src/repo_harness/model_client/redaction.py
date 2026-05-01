"""Provider artifact redaction helpers."""

from __future__ import annotations

import re
from typing import Any

REDACTED_CREDENTIAL = "<REDACTED_CREDENTIAL>"
REDACTED_REASONING = "<REDACTED_REASONING>"

_OPENAI_STYLE_KEY_RE = re.compile(r"\bsk-[A-Za-z0-9_\-]{8,}\b")
_BEARER_RE = re.compile(r"bearer\s+[A-Za-z0-9_\-./=:+]{6,}", re.IGNORECASE)


def redact_provider_payload(value: Any, *, redact_reasoning: bool = True) -> Any:
    """Recursively redact credentials and provider-only reasoning fields."""

    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, nested in value.items():
            key_text = str(key)
            if _secret_key(key_text):
                redacted[key] = REDACTED_CREDENTIAL
            elif redact_reasoning and _reasoning_key(key_text):
                redacted[key] = REDACTED_REASONING
            else:
                redacted[key] = redact_provider_payload(
                    nested,
                    redact_reasoning=redact_reasoning,
                )
        return redacted
    if isinstance(value, list):
        return [
            redact_provider_payload(item, redact_reasoning=redact_reasoning)
            for item in value
        ]
    if isinstance(value, str):
        if _looks_secret_like(value):
            return REDACTED_CREDENTIAL
    return value


def sanitize_provider_error_message(message: str) -> str:
    """Return an exception string safe for reports and artifacts."""

    redacted = _BEARER_RE.sub("Bearer " + REDACTED_CREDENTIAL, message)
    redacted = _OPENAI_STYLE_KEY_RE.sub(REDACTED_CREDENTIAL, redacted)
    return redacted[:2000]


def payload_contains_blocked_secret_text(value: Any) -> bool:
    text = str(value).lower()
    return (
        "authorization: bearer" in text
        or "bearer sk-" in text
        or bool(_OPENAI_STYLE_KEY_RE.search(str(value)))
    )


def _secret_key(key: str) -> bool:
    lowered = key.lower().replace("-", "_")
    if any(marker in lowered for marker in ("api_key", "apikey", "authorization", "password", "secret")):
        return True
    return lowered == "token" or lowered.endswith("_token")


def _reasoning_key(key: str) -> bool:
    lowered = key.lower().replace("-", "_")
    return lowered in {"reasoning_content", "reasoning_summary", "hidden_thoughts"}


def _looks_secret_like(text: str) -> bool:
    if _OPENAI_STYLE_KEY_RE.search(text):
        return True
    if _BEARER_RE.search(text):
        return True
    compact = text.replace("_", "").replace("-", "")
    return len(compact) >= 32 and any(char.isdigit() for char in compact) and any(
        char.isalpha() for char in compact
    )
