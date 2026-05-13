"""Initial model context inspection for lean pre-verl prompts."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any

from repo_harness.errors import ConfigError
from repo_harness.schema_base import stable_hash


LEAN_FORBIDDEN_FIRST_USER_MARKERS = (
    "repository_context_index",
    "repository_action_index",
    "repository_action_index_full",
    "source_text_span_hash",
    "ranking_score",
    "schema_version",
    "policy_version",
    "workspace_root",
    "permission_mode",
    "execution_mode",
    "test_command_visibility",
    "max_context_tokens",
)

LEAN_FORBIDDEN_TOOL_MARKERS = (
    "repository_action_index",
    "repository_action_index_full",
    "repository_context_index",
)

LEAN_FORBIDDEN_TOOL_SCHEMA_ALIASES = {
    "list_files": {"pattern"},
    "grep": {"pattern"},
    "edit_file": {"expected_content_sha256"},
}

ALLOWED_REPOSITORY_HINT_CANDIDATE_FIELDS = {"path", "confidence", "matched_terms"}


def inspect_initial_context(
    target: str | Path | None = None,
    *,
    first_model_call: bool = False,
    model_call_id: str | None = None,
    prepared_messages: str | Path | None = None,
    raw_provider_request: str | Path | None = None,
    assert_pre_verl_lean: bool = False,
) -> str:
    """Inspect the initial model-visible context and provider request projection."""

    failures: list[str] = []
    if target is not None and prepared_messages is not None:
        failures.append("不能同时传入 run directory 和 --prepared-messages。")
    if target is None and prepared_messages is None:
        failures.append("必须传入 run directory，或者传入 --prepared-messages。")

    if target is not None:
        report = _inspect_run_directory(
            Path(target),
            first_model_call=first_model_call,
            model_call_id=model_call_id,
            failures=failures,
        )
    else:
        report = _inspect_file_pair(
            prepared_messages=Path(str(prepared_messages)),
            raw_provider_request=(
                Path(raw_provider_request) if raw_provider_request is not None else None
            ),
            failures=failures,
        )

    _inspect_lean_requirements(report, failures, require_complete=assert_pre_verl_lean)
    status = "passed" if not failures else "failed"
    payload = {
        "status": status,
        "failure_count": len(failures),
        "failures": failures,
        **report,
    }
    if failures and assert_pre_verl_lean:
        raise ConfigError("; ".join(failures))
    return "Inspect initial context: " + status + "\n" + json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )


def _inspect_run_directory(
    run_path: Path,
    *,
    first_model_call: bool,
    model_call_id: str | None,
    failures: list[str],
) -> dict[str, Any]:
    if not run_path.exists() or not run_path.is_dir():
        failures.append(f"run directory 不存在或不是目录：{run_path}")
        return {"mode": "run_directory", "run_dir": str(run_path)}
    events = _read_jsonl(run_path / "events.jsonl", failures, "events.jsonl")
    if model_call_id is not None and first_model_call:
        failures.append("--first-model-call 和 --model-call-id 不能同时使用。")
    selection = _select_model_call(events, model_call_id=model_call_id)
    if selection is None:
        available_ids = [
            str(event.get("data", {}).get("model_call_id"))
            for event in events
            if event.get("event_type") == "model_call_started"
            and event.get("data", {}).get("model_call_id")
        ]
        failures.append(
            "找不到可检查的 model_call_started 事件；可选 model_call_id："
            + ", ".join(available_ids)
        )
        return {"mode": "run_directory", "run_dir": str(run_path)}

    started = selection
    first_started = _select_model_call(events, model_call_id=None)
    selected_model_call_id = started.get("data", {}).get("model_call_id")
    first_model_call_id = (
        first_started.get("data", {}).get("model_call_id")
        if isinstance(first_started, dict)
        else None
    )
    prepared_ref = _prepared_ref_from_started_event(started)
    if not isinstance(prepared_ref, dict):
        failures.append("model_call_started 缺少 prepared_messages_ref。")
        prepared_payload: dict[str, Any] = {}
    else:
        prepared_payload = _read_ref_json(run_path, prepared_ref, failures, "prepared_messages_ref")

    completed = _matching_completed_event(events, selected_model_call_id)
    raw_request_ref = _raw_ref_from_completed_event(completed, "raw_provider_request_ref")
    raw_response_ref = _raw_ref_from_completed_event(completed, "raw_provider_response_ref")
    raw_request_payload = (
        _read_ref_json(run_path, raw_request_ref, failures, "raw_provider_request_ref")
        if isinstance(raw_request_ref, dict)
        else {}
    )
    raw_response_payload = (
        _read_ref_json(run_path, raw_response_ref, failures, "raw_provider_response_ref")
        if isinstance(raw_response_ref, dict)
        else {}
    )
    tool_schema_ref = (
        raw_request_payload.get("tool_schema_snapshot_ref")
        or started.get("data", {}).get("tool_schema_snapshot_ref")
        or _artifact_ref_by_kind(started, "tool_schema_snapshot")
    )
    tool_schema_payload = (
        _read_ref_json(run_path, tool_schema_ref, failures, "tool_schema_snapshot_ref")
        if isinstance(tool_schema_ref, dict)
        else {}
    )
    profile_ref = _initial_context_profile_ref(run_path, events)
    profile_payload = (
        _read_ref_json(run_path, profile_ref, failures, "initial_context_profile_ref")
        if isinstance(profile_ref, dict)
        else {}
    )

    report = _build_report(
        mode="run_directory",
        target=str(run_path),
        prepared_payload=prepared_payload,
        raw_request_payload=raw_request_payload,
        raw_response_payload=raw_response_payload,
        tool_schema_payload=tool_schema_payload,
        profile_payload=profile_payload,
        prepared_ref=prepared_ref,
        raw_request_ref=raw_request_ref,
        raw_response_ref=raw_response_ref,
        tool_schema_ref=tool_schema_ref,
        profile_ref=profile_ref,
        profile_expected_to_match_selected_call=(
            selected_model_call_id == first_model_call_id
        ),
    )
    report["model_call_selection"] = {
        "model_call_id": selected_model_call_id,
        "selected_by": "model_call_id" if model_call_id else "first_model_call",
    }
    report["available_model_call_ids"] = [
        event.get("data", {}).get("model_call_id")
        for event in events
        if event.get("event_type") == "model_call_started"
    ]
    return report


def _inspect_file_pair(
    *,
    prepared_messages: Path,
    raw_provider_request: Path | None,
    failures: list[str],
) -> dict[str, Any]:
    prepared_payload = _read_file_json(prepared_messages, failures, "prepared_messages")
    raw_request_payload = (
        _read_file_json(raw_provider_request, failures, "raw_provider_request")
        if raw_provider_request is not None
        else {}
    )
    return _build_report(
        mode="file_pair",
        target=str(prepared_messages),
        prepared_payload=prepared_payload,
        raw_request_payload=raw_request_payload,
        raw_response_payload={},
        tool_schema_payload={},
        profile_payload={},
        prepared_ref={"path": str(prepared_messages), "sha256": _safe_sha256(prepared_messages)},
        raw_request_ref=(
            {"path": str(raw_provider_request), "sha256": _safe_sha256(raw_provider_request)}
            if raw_provider_request is not None
            else None
        ),
        raw_response_ref=None,
        tool_schema_ref=None,
        profile_ref=None,
        profile_expected_to_match_selected_call=False,
    )


def _build_report(
    *,
    mode: str,
    target: str,
    prepared_payload: dict[str, Any],
    raw_request_payload: dict[str, Any],
    raw_response_payload: dict[str, Any],
    tool_schema_payload: dict[str, Any],
    profile_payload: dict[str, Any],
    prepared_ref: Any,
    raw_request_ref: Any,
    raw_response_ref: Any,
    tool_schema_ref: Any,
    profile_ref: Any,
    profile_expected_to_match_selected_call: bool,
) -> dict[str, Any]:
    prepared_messages = prepared_payload.get("messages", [])
    if not isinstance(prepared_messages, list):
        prepared_messages = []
    first_user_content = _first_user_content(prepared_messages)
    first_user_text = json.dumps(first_user_content, ensure_ascii=False, sort_keys=True)
    repository_hints = (
        first_user_content.get("repository_hints")
        if isinstance(first_user_content, dict)
        else None
    )
    repository_context = (
        first_user_content.get("repository_context", [])
        if isinstance(first_user_content, dict)
        else []
    )
    prepared_projection = _project_prepared_messages(prepared_messages)
    provider_body_messages = _provider_body_messages(raw_request_payload)
    provider_messages_projection = (
        _training_message_projection(provider_body_messages)
        if provider_body_messages is not None
        else None
    )
    direct_projection_equivalent = (
        prepared_projection == provider_messages_projection
        if provider_messages_projection is not None
        else None
    )
    recorded_equivalence = _recorded_pre_redaction_equivalence(
        raw_request_payload,
        prepared_projection=prepared_projection,
        direct_projection_equivalent=direct_projection_equivalent,
    )
    effective_projection_equivalent = (
        True
        if direct_projection_equivalent is True or recorded_equivalence["usable"]
        else direct_projection_equivalent
    )
    provider_body_tools = _provider_body_tools(raw_request_payload)
    provider_usage = _provider_usage(raw_response_payload)
    return {
        "mode": mode,
        "target": target,
        "prepared_messages": {
            "ref": prepared_ref,
            "message_count": len(prepared_messages),
            "projection_hash": stable_hash(prepared_projection),
            "first_user_content_char_count": len(first_user_text),
            "first_user_top_level_keys": (
                sorted(first_user_content.keys()) if isinstance(first_user_content, dict) else []
            ),
            "forbidden_first_user_markers": _markers_present(
                first_user_text,
                LEAN_FORBIDDEN_FIRST_USER_MARKERS,
            ),
        },
        "repository_hints": _repository_hints_report(repository_hints),
        "repository_context": {
            "entry_count": len(repository_context) if isinstance(repository_context, list) else 0,
            "preview_char_count": _repository_context_preview_chars(repository_context),
        },
        "provider_body": {
            "raw_provider_request_ref": raw_request_ref,
            "available": bool(raw_request_payload),
            "messages_available": provider_messages_projection is not None,
            "message_count": (
                len(provider_messages_projection)
                if provider_messages_projection is not None
                else None
            ),
            "message_projection_hash": (
                stable_hash(provider_messages_projection)
                if provider_messages_projection is not None
                else None
            ),
            "prepared_projection_equivalent": effective_projection_equivalent,
            "redacted_message_projection_equivalent": direct_projection_equivalent,
            "projection_equivalence_source": (
                "direct_redacted_body"
                if direct_projection_equivalent is True
                else "recorded_pre_redaction_binding"
                if recorded_equivalence["usable"]
                else "direct_redacted_body"
                if provider_messages_projection is not None
                else None
            ),
            "recorded_pre_redaction_equivalence": recorded_equivalence,
            "tool_count": len(provider_body_tools),
            "tool_forbidden_markers": _markers_present(
                json.dumps(provider_body_tools, ensure_ascii=False, sort_keys=True),
                LEAN_FORBIDDEN_TOOL_MARKERS,
            ),
            "tool_legacy_alias_fields": _provider_tool_legacy_alias_fields(
                provider_body_tools
            ),
            "top_level_keys": sorted(raw_request_payload.keys()),
        },
        "raw_provider_response": {
            "ref": raw_response_ref,
            "available": bool(raw_response_payload),
        },
        "tool_schema_snapshot": {
            "ref": tool_schema_ref,
            "available": bool(tool_schema_payload),
        },
        "provider_usage": provider_usage,
        "initial_context_profile": _profile_report(
            profile_ref,
            profile_payload,
            prepared_messages=prepared_messages,
            first_user_content=first_user_content,
            first_user_text=first_user_text,
            repository_hints=repository_hints,
            repository_context=repository_context,
            expected_to_match_selected_call=profile_expected_to_match_selected_call,
        ),
    }


def _inspect_lean_requirements(
    report: dict[str, Any],
    failures: list[str],
    *,
    require_complete: bool,
) -> None:
    prepared = report.get("prepared_messages", {})
    provider = report.get("provider_body", {})
    hints = report.get("repository_hints", {})
    profile = report.get("initial_context_profile", {})
    context = report.get("repository_context", {})

    for marker in prepared.get("forbidden_first_user_markers", []):
        failures.append(f"首轮 user content 包含禁止字段：{marker}")
    for marker in provider.get("tool_forbidden_markers", []):
        failures.append(f"provider body.tools 包含旧字段：{marker}")
    for item in provider.get("tool_legacy_alias_fields", []):
        failures.append(
            "provider body.tools 暴露旧参数别名："
            f"{item.get('tool')}.{item.get('field')}"
        )
    if require_complete and not provider.get("available"):
        failures.append("--assert-pre-verl-lean 需要 raw provider request。")
    if require_complete and provider.get("prepared_projection_equivalent") is not True:
        failures.append("prepared messages projection 与 provider body.messages 不等价。")
    if report.get("mode") == "run_directory" and require_complete and not profile.get("available"):
        failures.append("run directory 缺少 initial_context_profile artifact。")
    invalid_candidate_fields = hints.get("invalid_candidate_fields", [])
    for item in invalid_candidate_fields:
        failures.append(
            "repository_hints.candidate_files 字段超出模型可见 allowlist："
            f"{item['path']} -> {', '.join(item['extra_fields'])}"
        )
    resolved_limit = _resolved_hint_limit(report)
    if resolved_limit is not None and hints.get("candidate_count", 0) > resolved_limit:
        failures.append(
            "repository_hints.candidate_files 数量超过配置上限："
            f"{hints.get('candidate_count')} > {resolved_limit}"
        )
    if (
        profile.get("repository_hints_mode") == "disabled"
        and hints.get("candidate_count", 0) > 0
    ):
        failures.append("repository_hints.mode=disabled 时不应暴露候选文件。")
    if require_complete and profile.get("available"):
        profile_presence = profile.get("repository_hints_presence")
        hints_present = bool(hints.get("present"))
        if profile_presence == "present" and not hints_present:
            failures.append("initial_context_profile 记录 repository_hints present，但首轮 user content 中缺失。")
        if profile_presence == "absent" and hints_present:
            failures.append("initial_context_profile 记录 repository_hints absent，但首轮 user content 中存在。")
        if profile.get("repository_hints_mode") != "disabled" and not hints_present:
            absence_reason = profile.get("repository_hints_absence_reason")
            if absence_reason != "no_model_visible_hint_seed":
                failures.append(
                    "非 disabled repository_hints 模式下缺少 repository_hints，"
                    f"absence_reason={absence_reason}"
                )
    if context.get("preview_char_count", 0) > 4000:
        failures.append("repository_context preview 总字符数超过 4000。")
    if require_complete and profile.get("available"):
        for key in profile.get("missing_required_fields", []):
            failures.append(f"initial_context_profile 缺少 {key}。")
        for key in profile.get("mismatched_fields", []):
            failures.append(f"initial_context_profile 与 prepared_messages 不一致：{key}。")
        if profile.get("schema_version") != "repo_harness_initial_context_profile_v0":
            failures.append("initial_context_profile.schema_version 不正确。")


def _select_model_call(events: list[dict[str, Any]], *, model_call_id: str | None) -> dict[str, Any] | None:
    started = [event for event in events if event.get("event_type") == "model_call_started"]
    if model_call_id is None:
        return started[0] if started else None
    for event in started:
        if event.get("data", {}).get("model_call_id") == model_call_id:
            return event
    return None


def _matching_completed_event(events: list[dict[str, Any]], model_call_id: Any) -> dict[str, Any] | None:
    completed = [event for event in events if event.get("event_type") == "model_call_completed"]
    if model_call_id:
        for event in completed:
            if event.get("data", {}).get("model_call_id") == model_call_id:
                return event
        return None
    return completed[0] if completed else None


def _prepared_ref_from_started_event(event: dict[str, Any]) -> dict[str, Any] | None:
    ref = event.get("data", {}).get("prepared_messages_ref")
    if isinstance(ref, dict):
        return ref
    return _artifact_ref_by_kind(event, "prepared_messages")


def _raw_ref_from_completed_event(event: dict[str, Any] | None, key: str) -> dict[str, Any] | None:
    if event is None:
        return None
    ref = event.get("data", {}).get(key)
    if isinstance(ref, dict):
        return ref
    wanted = "request" if "request" in key else "response"
    for artifact_ref in event.get("artifact_refs", []) or []:
        if isinstance(artifact_ref, dict) and wanted in str(artifact_ref.get("kind") or ""):
            return artifact_ref
    return None


def _artifact_ref_by_kind(event: dict[str, Any], kind: str) -> dict[str, Any] | None:
    for artifact_ref in event.get("artifact_refs", []) or []:
        if isinstance(artifact_ref, dict) and artifact_ref.get("kind") == kind:
            return artifact_ref
    return None


def _initial_context_profile_ref(run_path: Path, events: list[dict[str, Any]]) -> dict[str, Any] | None:
    for event in events:
        if event.get("event_type") != "initial_context_profile_written":
            continue
        ref = event.get("data", {}).get("initial_context_profile_ref")
        if isinstance(ref, dict):
            return ref
        ref = _artifact_ref_by_kind(event, "initial_context_profile")
        if isinstance(ref, dict):
            return ref
    manifest = _read_file_json(run_path / "artifacts.json", [], "artifacts.json")
    for artifact in manifest.get("artifacts", []):
        if isinstance(artifact, dict) and artifact.get("kind") == "initial_context_profile":
            return artifact
    return None


def _read_ref_json(
    run_path: Path,
    ref: dict[str, Any],
    failures: list[str],
    label: str,
) -> dict[str, Any]:
    value = ref.get("relative_path") or ref.get("path")
    if not isinstance(value, str) or not value:
        failures.append(f"{label} 缺少 relative_path 或 path。")
        return {}
    path = Path(value)
    resolved = path if path.is_absolute() else run_path / path
    if not _safe_path(run_path, resolved):
        failures.append(f"{label} 路径不安全：{value}")
        return {}
    payload = _read_file_json(resolved, failures, label)
    expected_sha = ref.get("sha256")
    if isinstance(expected_sha, str) and expected_sha and resolved.exists():
        actual_sha = _sha256_file(resolved)
        if actual_sha != expected_sha:
            failures.append(f"{label} sha256 不匹配。")
    return payload


def _safe_path(run_path: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(run_path.resolve())
        return True
    except ValueError:
        return False


def _read_file_json(path: Path | None, failures: list[str], label: str) -> dict[str, Any]:
    if path is None:
        return {}
    if not path.exists():
        failures.append(f"{label} 不存在：{path}")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        failures.append(f"{label} 不是有效 JSON：{exc}")
        return {}
    if not isinstance(payload, dict):
        failures.append(f"{label} 顶层必须是 JSON object。")
        return {}
    return payload


def _read_jsonl(path: Path, failures: list[str], label: str) -> list[dict[str, Any]]:
    if not path.exists():
        failures.append(f"{label} 不存在：{path}")
        return []
    events = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            failures.append(f"{label}:{line_number} 不是有效 JSON：{exc}")
            continue
        if isinstance(value, dict):
            events.append(value)
    return events


def _first_user_content(messages: list[Any]) -> Any:
    for message in messages:
        if isinstance(message, dict) and message.get("role") == "user":
            return message.get("content")
    return None


def _project_prepared_messages(messages: list[Any]) -> list[dict[str, Any]]:
    projected = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = message.get("role")
        item: dict[str, Any] = {"role": role}
        if role == "assistant":
            item["content"] = _content_to_string(message.get("content"))
            tool_calls = message.get("tool_calls") or []
            if tool_calls:
                item["tool_calls"] = [_provider_tool_call(call) for call in tool_calls]
        elif role == "tool":
            item["content"] = _content_to_string(message.get("content"))
            item["tool_call_id"] = str(
                message.get("tool_call_id") or message.get("tool_result_id") or ""
            )
        else:
            item["content"] = _content_to_string(message.get("content"))
        projected.append({key: value for key, value in item.items() if value is not None})
    return projected


def _provider_body_messages(raw_request: dict[str, Any]) -> list[Any] | None:
    body = raw_request.get("body")
    if isinstance(body, dict) and isinstance(body.get("messages"), list):
        return body["messages"]
    return None


def _provider_body_tools(raw_request: dict[str, Any]) -> list[Any]:
    body = raw_request.get("body")
    if isinstance(body, dict) and isinstance(body.get("tools"), list):
        return body["tools"]
    if isinstance(raw_request.get("tools"), list):
        return raw_request["tools"]
    return []


def _provider_tool_legacy_alias_fields(tools: list[Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        function = tool.get("function")
        if not isinstance(function, dict):
            continue
        tool_name = function.get("name")
        if not isinstance(tool_name, str):
            continue
        forbidden_fields = LEAN_FORBIDDEN_TOOL_SCHEMA_ALIASES.get(tool_name, set())
        if not forbidden_fields:
            continue
        parameters = function.get("parameters")
        properties = parameters.get("properties") if isinstance(parameters, dict) else None
        if not isinstance(properties, dict):
            continue
        for field in sorted(forbidden_fields):
            if field in properties:
                findings.append({"tool": tool_name, "field": field})
    return findings


def _training_message_projection(messages: list[Any]) -> list[dict[str, Any]]:
    projected = []
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


def _recorded_pre_redaction_equivalence(
    raw_request: dict[str, Any],
    *,
    prepared_projection: list[dict[str, Any]],
    direct_projection_equivalent: bool | None,
) -> dict[str, Any]:
    prepared_projection_hash = stable_hash(prepared_projection)
    recorded_prepared_hash = raw_request.get("prepared_messages_projection_hash")
    recorded_body_hash = raw_request.get("provider_body_message_projection_hash")
    recorded_equivalent = raw_request.get("prepared_messages_body_equivalent")
    body_message_redaction_paths = _body_message_redaction_paths(raw_request)
    hash_match = (
        recorded_prepared_hash == prepared_projection_hash
        and recorded_body_hash == prepared_projection_hash
    )
    usable = (
        direct_projection_equivalent is False
        and recorded_equivalent is True
        and hash_match
        and bool(body_message_redaction_paths)
    )
    return {
        "usable": usable,
        "recorded_prepared_messages_body_equivalent": recorded_equivalent,
        "recorded_prepared_messages_projection_hash": recorded_prepared_hash,
        "recorded_provider_body_message_projection_hash": recorded_body_hash,
        "prepared_messages_projection_hash": prepared_projection_hash,
        "recorded_hashes_match_prepared_projection": hash_match,
        "body_message_redaction_paths": body_message_redaction_paths,
    }


def _body_message_redaction_paths(raw_request: dict[str, Any]) -> list[str]:
    report = raw_request.get("redaction_report")
    if not isinstance(report, dict):
        return []
    paths: list[str] = []
    for key in (
        "secret_span_paths",
        "secret_field_paths",
        "reasoning_field_paths",
        "ordinary_text_span_paths",
    ):
        values = report.get(key)
        if not isinstance(values, list):
            continue
        paths.extend(str(value) for value in values if isinstance(value, str))
    return sorted(path for path in paths if path.startswith("$.body.messages"))


def _content_to_string(content: Any) -> str | None:
    if content is None:
        return None
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False, sort_keys=True)


def _provider_tool_call(call: Any) -> dict[str, Any]:
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


def _repository_hints_report(repository_hints: Any) -> dict[str, Any]:
    if not isinstance(repository_hints, dict):
        return {"present": False, "candidate_count": 0, "invalid_candidate_fields": []}
    candidates = repository_hints.get("candidate_files", [])
    if not isinstance(candidates, list):
        candidates = []
    invalid = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            invalid.append({"path": "<non-object>", "extra_fields": ["<non-object>"]})
            continue
        extra = sorted(set(candidate) - ALLOWED_REPOSITORY_HINT_CANDIDATE_FIELDS)
        if extra:
            invalid.append({"path": str(candidate.get("path") or ""), "extra_fields": extra})
    return {
        "present": True,
        "candidate_count": len(candidates),
        "invalid_candidate_fields": invalid,
        "fallback_search_terms_count": len(repository_hints.get("fallback_search_terms", []) or []),
    }


def _repository_hints_absence_reason(
    *,
    first_user_content: Any,
    repository_hints: Any,
    repository_hints_mode: str,
) -> str | None:
    if isinstance(repository_hints, dict):
        return None
    if repository_hints_mode == "disabled":
        return "repository_hints_mode_disabled"
    task = first_user_content.get("task", {}) if isinstance(first_user_content, dict) else {}
    expected_files = task.get("expected_files", []) if isinstance(task, dict) else []
    if not isinstance(expected_files, list):
        expected_files = []
    issue_statement = str(task.get("issue_statement") or "") if isinstance(task, dict) else ""
    issue_terms = _hint_terms(issue_statement)
    if not expected_files and not issue_terms:
        return "no_model_visible_hint_seed"
    return "unexpected_missing_repository_hints"


def _hint_terms(text: str) -> list[str]:
    terms: list[str] = []
    current: list[str] = []
    for char in text:
        if char.isalnum() or char in {"_", "-"}:
            current.append(char.lower())
            continue
        if current:
            term = "".join(current).strip("_-")
            if len(term) >= 3:
                terms.append(term)
            current = []
    if current:
        term = "".join(current).strip("_-")
        if len(term) >= 3:
            terms.append(term)
    return sorted(set(terms))


def _repository_context_preview_chars(repository_context: Any) -> int:
    if not isinstance(repository_context, list):
        return 0
    total = 0
    for entry in repository_context:
        if isinstance(entry, dict):
            total += len(str(entry.get("preview") or ""))
    return total


def _profile_report(
    ref: Any,
    payload: dict[str, Any],
    *,
    prepared_messages: list[Any],
    first_user_content: Any,
    first_user_text: str,
    repository_hints: Any,
    repository_context: Any,
    expected_to_match_selected_call: bool,
) -> dict[str, Any]:
    config = payload.get("repository_hints_config", {})
    candidates = (
        repository_hints.get("candidate_files", [])
        if isinstance(repository_hints, dict)
        else []
    )
    if not isinstance(candidates, list):
        candidates = []
    expected = {
        "model_visible_messages_hash": stable_hash(prepared_messages),
        "first_user_content_hash": stable_hash(first_user_content),
        "first_user_content_char_count": len(first_user_text),
        "repository_hints_candidate_count": len(candidates),
        "repository_hints_presence": (
            "present" if isinstance(repository_hints, dict) else "absent"
        ),
        "repository_hints_absence_reason": _repository_hints_absence_reason(
            first_user_content=first_user_content,
            repository_hints=repository_hints,
            repository_hints_mode=str(payload.get("repository_hints_mode") or ""),
        ),
        "repository_context_preview_char_count": _repository_context_preview_chars(
            repository_context
        ),
    }
    required_fields = [
        "schema_version",
        "initial_context_policy_version",
        "repository_hints_mode",
        "repository_hints_config",
        "repository_hints_presence",
        "model_visible_messages_hash",
        "first_user_content_hash",
        "first_user_content_char_count",
        "first_user_top_level_keys",
        "repository_context_entry_count",
        "repository_context_preview_char_count",
        "repository_hints_candidate_count",
        "repository_action_index_full_hash",
        "repository_context_index_full_hash",
        "forbidden_model_visible_fields_present",
    ]
    if payload.get("repository_hints_presence") == "absent":
        required_fields.append("repository_hints_absence_reason")
    if payload.get("repository_hints_mode") != "disabled":
        required_fields.append("repository_hints_model_visible_hash")
    missing = [
        field
        for field in required_fields
        if field not in payload or payload.get(field) is None
    ]
    mismatched = (
        [
            field
            for field, expected_value in expected.items()
            if payload.get(field) is not None and payload.get(field) != expected_value
        ]
        if expected_to_match_selected_call
        else []
    )
    forbidden_fields = payload.get("forbidden_model_visible_fields_present")
    if forbidden_fields not in ([], None):
        mismatched.append("forbidden_model_visible_fields_present")
    return {
        "ref": ref,
        "available": bool(payload),
        "schema_version": payload.get("schema_version"),
        "initial_context_policy_version": payload.get("initial_context_policy_version"),
        "repository_hints_mode": payload.get("repository_hints_mode"),
        "repository_hints_config": config if isinstance(config, dict) else {},
        "repository_hints_presence": payload.get("repository_hints_presence"),
        "repository_hints_absence_reason": payload.get(
            "repository_hints_absence_reason"
        ),
        "model_visible_messages_hash": payload.get("model_visible_messages_hash"),
        "first_user_content_hash": payload.get("first_user_content_hash"),
        "first_user_content_char_count": payload.get("first_user_content_char_count"),
        "repository_hints_candidate_count": payload.get("repository_hints_candidate_count"),
        "repository_context_preview_char_count": payload.get("repository_context_preview_char_count"),
        "provider_prompt_tokens": payload.get("provider_prompt_tokens"),
        "expected_to_match_selected_call": expected_to_match_selected_call,
        "missing_required_fields": missing,
        "mismatched_fields": sorted(set(mismatched)),
    }


def _resolved_hint_limit(report: dict[str, Any]) -> int | None:
    profile = report.get("initial_context_profile", {})
    config = profile.get("repository_hints_config", {})
    if isinstance(config, dict) and isinstance(config.get("resolved_max_candidate_files"), int):
        return config["resolved_max_candidate_files"]
    return None


def _provider_usage(raw_response: dict[str, Any]) -> dict[str, Any]:
    usage = raw_response.get("usage")
    if not isinstance(usage, dict):
        response = raw_response.get("response")
        if isinstance(response, dict):
            usage = response.get("usage")
    if not isinstance(usage, dict):
        return {"available": False, "prompt_tokens": None, "source": None}
    return {
        "available": True,
        "prompt_tokens": usage.get("prompt_tokens") or usage.get("input_tokens"),
        "source": "raw_provider_response.usage",
    }


def _markers_present(text: str, markers: tuple[str, ...]) -> list[str]:
    lowered = text.lower()
    return [marker for marker in markers if marker.lower() in lowered]


def _safe_sha256(path: Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    return _sha256_file(path)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
