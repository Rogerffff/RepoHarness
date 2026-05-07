"""Provider artifact redaction helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

REDACTED_CREDENTIAL = "<REDACTED_CREDENTIAL>"
REDACTED_REASONING = "<REDACTED_REASONING>"

_OPENAI_STYLE_KEY_RE = re.compile(r"\bsk-[A-Za-z0-9_\-]{8,}\b")
_BEARER_RE = re.compile(r"bearer\s+[A-Za-z0-9_\-./=:+]{6,}", re.IGNORECASE)
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?P<key>\b(?:api[_-]?key|token|password|secret|authorization)\b\s*[:=]\s*)"
    r"(?P<quote>['\"]?)"
    r"(?P<value>[A-Za-z0-9_\-./=:+]{6,})"
    r"(?P=quote)",
    re.IGNORECASE,
)


@dataclass
class RedactionStats:
    secret_field_paths: list[str] = field(default_factory=list)
    secret_span_paths: list[str] = field(default_factory=list)
    reasoning_field_paths: list[str] = field(default_factory=list)

    def report(self) -> dict[str, Any]:
        return {
            "schema_version": "repo_harness_provider_redaction_report_v0",
            "redaction_policy": "key_aware_span_based_v0",
            "secret_field_redaction_count": len(self.secret_field_paths),
            "secret_span_redaction_count": len(self.secret_span_paths),
            "reasoning_field_redaction_count": len(self.reasoning_field_paths),
            "secret_field_paths": self.secret_field_paths,
            "secret_span_paths": self.secret_span_paths,
            "reasoning_field_paths": self.reasoning_field_paths,
            "ordinary_text_whole_field_redaction_allowed": False,
        }


def redact_provider_payload(
    value: Any,
    *,
    redact_reasoning: bool = True,
    _parent_key: str | None = None,
) -> Any:
    """Recursively redact credentials and provider-only reasoning fields."""

    return redact_provider_payload_with_report(
        value,
        redact_reasoning=redact_reasoning,
        _parent_key=_parent_key,
    )[0]


def redact_provider_payload_with_report(
    value: Any,
    *,
    redact_reasoning: bool = True,
    _parent_key: str | None = None,
) -> tuple[Any, dict[str, Any]]:
    stats = RedactionStats()
    redacted = _redact_provider_payload(
        value,
        redact_reasoning=redact_reasoning,
        parent_key=_parent_key,
        path="$",
        stats=stats,
    )
    return redacted, stats.report()


def _redact_provider_payload(
    value: Any,
    *,
    redact_reasoning: bool,
    parent_key: str | None,
    path: str,
    stats: RedactionStats,
) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, nested in value.items():
            key_text = str(key)
            nested_path = f"{path}.{key_text}"
            if _secret_key(key_text):
                stats.secret_field_paths.append(nested_path)
                redacted[key] = REDACTED_CREDENTIAL
            elif redact_reasoning and _reasoning_key(key_text):
                stats.reasoning_field_paths.append(nested_path)
                redacted[key] = REDACTED_REASONING
            else:
                redacted[key] = _redact_provider_payload(
                    nested,
                    redact_reasoning=redact_reasoning,
                    parent_key=key_text,
                    path=nested_path,
                    stats=stats,
                )
        return redacted
    if isinstance(value, list):
        return [
            _redact_provider_payload(
                item,
                redact_reasoning=redact_reasoning,
                parent_key=parent_key,
                path=f"{path}[{index}]",
                stats=stats,
            )
            for index, item in enumerate(value)
        ]
    if isinstance(value, str):
        redacted_text, redacted_count = _redact_secret_spans(value)
        if redacted_count:
            stats.secret_span_paths.extend([path] * redacted_count)
            return redacted_text
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
    lowered = _normalize_secret_key(key)
    if any(marker in lowered for marker in ("api_key", "apikey", "authorization", "password", "secret")):
        return True
    return lowered == "token" or lowered.endswith("_token")


def _reasoning_key(key: str) -> bool:
    lowered = key.lower().replace("-", "_")
    return lowered in {"reasoning_content", "reasoning_summary", "hidden_thoughts"}


def _non_secret_value_key(key: str | None) -> bool:
    if key is None:
        return False
    lowered = _normalize_secret_key(key)
    if _secret_key(lowered):
        return False
    return lowered in {
        "schema_version",
        "provider_adapter_version",
        "adapter_version",
        "protocol_version",
    } or lowered.endswith("_version") or lowered.endswith("_policy_version")


def _looks_secret_like(text: str) -> bool:
    if _contains_explicit_secret(text):
        return True
    compact = text.replace("_", "").replace("-", "")
    return len(compact) >= 32 and any(char.isdigit() for char in compact) and any(
        char.isalpha() for char in compact
    )


def _contains_explicit_secret(text: str) -> bool:
    if _OPENAI_STYLE_KEY_RE.search(text):
        return True
    if _BEARER_RE.search(text):
        return True
    return False


def _redact_secret_spans(text: str) -> tuple[str, int]:
    redacted_count = 0

    def _mark(_match: re.Match[str]) -> str:
        nonlocal redacted_count
        redacted_count += 1
        return REDACTED_CREDENTIAL

    value = _BEARER_RE.sub(lambda match: "Bearer " + _mark(match), text)
    value = _OPENAI_STYLE_KEY_RE.sub(_mark, value)

    def _assignment(match: re.Match[str]) -> str:
        nonlocal redacted_count
        redacted_count += 1
        quote = match.group("quote")
        return match.group("key") + quote + REDACTED_CREDENTIAL + quote

    value = _SECRET_ASSIGNMENT_RE.sub(_assignment, value)
    return value, redacted_count


def _normalize_secret_key(key: str) -> str:
    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", key)
    return value.lower().replace("-", "_")
