"""Hermes-style tool parser for Stage 12-B real model smoke."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from .errors import RepoHarnessVerlGatewayError
from .visibility import VerlVisibilityError, validate_token_output_extra_fields

DEFAULT_STAGE12B_TOOL_NAMES = frozenset({"read_file", "grep", "edit_file", "git_diff"})
TOOL_CALL_BLOCK_RE = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.DOTALL)
FENCED_JSON_RE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL | re.IGNORECASE)


@dataclass(frozen=True)
class ParsedToolText:
    """Model-visible content plus parsed RepoHarness tool calls."""

    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    diagnostics: list[dict[str, Any]] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return not any(diagnostic.get("severity") == "error" for diagnostic in self.diagnostics)


def parse_hermes_tool_calls(
    assistant_text: str,
    *,
    turn: int,
    allowed_tool_names: set[str] | frozenset[str] = DEFAULT_STAGE12B_TOOL_NAMES,
) -> ParsedToolText:
    """Parse one ``<tool_call>{...}</tool_call>`` block from assistant text.

    Parser failures are model format failures. They return diagnostics and no tool calls;
    callers should not turn them into infrastructure errors.

    Stage 12-B keeps Hermes-style blocks as the primary protocol, but real Qwen Coder
    smoke tests can produce a whole-message JSON tool payload. That shape is accepted
    only when the entire assistant message is the JSON object, optionally wrapped in a
    Markdown JSON fence, and the recovered payload passes the same visibility checks.
    """

    text = str(assistant_text or "")
    blocks = list(TOOL_CALL_BLOCK_RE.finditer(text))
    if not blocks:
        if "<tool_call" in text or "</tool_call>" in text:
            return ParsedToolText(
                content=_strip_unclosed_tool_call(text),
                diagnostics=[_diagnostic("model_format_failure", "malformed_tool_call_block", severity="error")],
            )
        recovered = _recover_whole_message_json_tool_call(
            text,
            turn=turn,
            allowed_tool_names=allowed_tool_names,
        )
        if recovered is not None:
            return recovered
        return ParsedToolText(content=text.strip(), tool_calls=[], diagnostics=[])

    diagnostics: list[dict[str, Any]] = []
    if len(blocks) > 1:
        diagnostics.append(
            _diagnostic(
                "ignored_extra_tool_calls",
                "multiple_tool_call_blocks",
                severity="warning",
                ignored_count=len(blocks) - 1,
            )
        )

    content = TOOL_CALL_BLOCK_RE.sub("", text).strip()
    parsed = _parse_one_tool_call_payload(
        blocks[0].group(1),
        turn=turn,
        index=0,
        allowed_tool_names=allowed_tool_names,
    )
    diagnostics.extend(parsed.diagnostics)
    return ParsedToolText(content=content, tool_calls=parsed.tool_calls, diagnostics=diagnostics)


def _parse_one_tool_call_payload(
    payload: str,
    *,
    turn: int,
    index: int,
    allowed_tool_names: set[str] | frozenset[str],
) -> ParsedToolText:
    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError:
        return ParsedToolText(
            content="",
            diagnostics=[_diagnostic("model_format_failure", "invalid_tool_call_json", severity="error")],
        )
    if not isinstance(decoded, dict):
        return ParsedToolText(
            content="",
            diagnostics=[_diagnostic("model_format_failure", "tool_call_payload_not_object", severity="error")],
        )

    name = decoded.get("name")
    if not isinstance(name, str) or not name:
        return ParsedToolText(
            content="",
            diagnostics=[_diagnostic("model_format_failure", "tool_call_missing_name", severity="error")],
        )
    if name not in allowed_tool_names:
        return ParsedToolText(
            content="",
            diagnostics=[
                _diagnostic("model_format_failure", "tool_call_unknown_tool_name", severity="error", tool_name=name)
            ],
        )

    arguments = decoded.get("arguments", {})
    if not isinstance(arguments, dict):
        return ParsedToolText(
            content="",
            diagnostics=[_diagnostic("model_format_failure", "tool_call_arguments_not_object", severity="error")],
        )

    try:
        validate_token_output_extra_fields({"repo_harness_tool_call_arguments": arguments})
    except VerlVisibilityError as exc:
        return ParsedToolText(
            content="",
            diagnostics=[
                _diagnostic(
                    "model_format_failure",
                    "tool_call_arguments_visibility_rejected",
                    severity="error",
                    detail=str(exc),
                )
            ],
        )

    tool_call = {
        "tool_call_id": f"repo_harness_verl_tool_call_{turn}_{index}",
        "tool_name": name,
        "arguments": dict(arguments),
    }
    return ParsedToolText(content="", tool_calls=[tool_call], diagnostics=[])


def _recover_whole_message_json_tool_call(
    text: str,
    *,
    turn: int,
    allowed_tool_names: set[str] | frozenset[str],
) -> ParsedToolText | None:
    stripped = text.strip()
    if not stripped:
        return None

    recovery_code = "model_format_recovered_from_bare_json"
    payload = stripped
    fence_match = FENCED_JSON_RE.match(stripped)
    if fence_match:
        payload = fence_match.group(1).strip()
        recovery_code = "model_format_recovered_from_fenced_json"
    elif not stripped.startswith("{"):
        return None

    parsed = _parse_one_tool_call_payload(
        payload,
        turn=turn,
        index=0,
        allowed_tool_names=allowed_tool_names,
    )
    if not parsed.success:
        return parsed
    if not parsed.tool_calls:
        return None
    return ParsedToolText(
        content="",
        tool_calls=parsed.tool_calls,
        diagnostics=[
            _diagnostic(
                "model_format_recovery",
                recovery_code,
                severity="warning",
            )
        ],
    )


def ensure_tool_parse_success(parsed: ParsedToolText) -> None:
    """Raise a gateway error for callers that explicitly require parsed tools."""

    if parsed.success:
        return
    error_codes = ",".join(str(item.get("code")) for item in parsed.diagnostics if item.get("severity") == "error")
    raise RepoHarnessVerlGatewayError(f"model_format_failure: {error_codes or 'tool_parse_failed'}")


def _strip_unclosed_tool_call(text: str) -> str:
    marker_index = text.find("<tool_call")
    if marker_index < 0:
        return text.strip()
    return text[:marker_index].strip()


def _diagnostic(category: str, code: str, *, severity: str, **extra: Any) -> dict[str, Any]:
    diagnostic: dict[str, Any] = {"category": category, "code": code, "severity": severity}
    diagnostic.update(extra)
    return diagnostic
