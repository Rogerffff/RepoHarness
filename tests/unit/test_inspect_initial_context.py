from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from repo_harness.cli.main import main
from repo_harness.errors import ConfigError
from repo_harness.inspect_initial_context import (
    _project_prepared_messages,
    inspect_initial_context,
)
from repo_harness.schema_base import stable_hash


def test_inspect_initial_context_passes_lean_run_directory(tmp_path: Path) -> None:
    run_dir = _write_initial_context_run(tmp_path)

    result = inspect_initial_context(
        run_dir,
        first_model_call=True,
        assert_pre_verl_lean=True,
    )

    assert "Inspect initial context: passed" in result
    payload = json.loads(result.split("\n", 1)[1])
    assert payload["provider_body"]["prepared_projection_equivalent"] is True
    assert payload["repository_hints"]["candidate_count"] == 1
    assert payload["initial_context_profile"]["available"] is True


def test_inspect_initial_context_selects_model_call_id(tmp_path: Path) -> None:
    run_dir = _write_initial_context_run(tmp_path, include_second_call=True)

    result = inspect_initial_context(
        run_dir,
        model_call_id="run_context_model_call_0002",
        assert_pre_verl_lean=True,
    )

    payload = json.loads(result.split("\n", 1)[1])
    assert payload["model_call_selection"]["model_call_id"] == "run_context_model_call_0002"
    assert payload["prepared_messages"]["first_user_content_char_count"] > 0


def test_inspect_initial_context_requires_matching_completed_event_for_model_call_id(
    tmp_path: Path,
) -> None:
    run_dir = _write_initial_context_run(tmp_path, include_second_call=True)
    events_path = run_dir / "events.jsonl"
    events = [
        json.loads(line)
        for line in events_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    for event in events:
        if (
            event.get("event_type") == "model_call_completed"
            and event.get("data", {}).get("model_call_id") == "run_context_model_call_0002"
        ):
            event["data"]["model_call_id"] = "run_context_model_call_missing"
    events_path.write_text(
        "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="raw provider request"):
        inspect_initial_context(
            run_dir,
            model_call_id="run_context_model_call_0002",
            assert_pre_verl_lean=True,
        )


def test_inspect_initial_context_rejects_artifact_ref_outside_run_dir(
    tmp_path: Path,
) -> None:
    run_dir = _write_initial_context_run(tmp_path)
    outside_path = tmp_path / "outside_prepared_messages.json"
    outside_path.write_text(
        json.dumps({"messages": []}, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    events_path = run_dir / "events.jsonl"
    events = [
        json.loads(line)
        for line in events_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    events[0]["data"]["prepared_messages_ref"] = {
        "kind": "prepared_messages",
        "path": str(outside_path),
        "sha256": hashlib.sha256(outside_path.read_bytes()).hexdigest(),
    }
    events_path.write_text(
        "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="路径不安全"):
        inspect_initial_context(run_dir, first_model_call=True, assert_pre_verl_lean=True)


def test_inspect_initial_context_rejects_full_index_leak(tmp_path: Path) -> None:
    run_dir = _write_initial_context_run(
        tmp_path,
        user_content={
            "task": {"issue_statement": "Fix it"},
            "repository_action_index": {"candidate_source_entries": []},
        },
    )

    with pytest.raises(ConfigError, match="repository_action_index"):
        inspect_initial_context(run_dir, first_model_call=True, assert_pre_verl_lean=True)


def test_inspect_initial_context_rejects_provider_tool_legacy_alias_schema(
    tmp_path: Path,
) -> None:
    run_dir = _write_initial_context_run(tmp_path)
    raw_request_path = run_dir / "artifacts" / "raw_provider_request_1.json"
    raw_request = json.loads(raw_request_path.read_text(encoding="utf-8"))
    raw_request["body"]["tools"] = [
        {
            "type": "function",
            "function": {
                "name": "grep",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "pattern": {"type": "string"},
                    },
                },
            },
        }
    ]
    raw_request_path.write_text(
        json.dumps(raw_request, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _refresh_event_and_manifest_ref(run_dir, raw_request_path.relative_to(run_dir).as_posix())

    with pytest.raises(ConfigError, match="grep.pattern"):
        inspect_initial_context(run_dir, first_model_call=True, assert_pre_verl_lean=True)


def test_inspect_initial_context_file_mode_requires_raw_request_for_assert(
    tmp_path: Path,
) -> None:
    run_dir = _write_initial_context_run(tmp_path)
    prepared_path = run_dir / "artifacts" / "prepared_messages_1.json"
    raw_request_path = run_dir / "artifacts" / "raw_provider_request_1.json"

    with pytest.raises(ConfigError, match="raw provider request"):
        inspect_initial_context(
            prepared_messages=prepared_path,
            assert_pre_verl_lean=True,
        )

    result = inspect_initial_context(
        prepared_messages=prepared_path,
        raw_provider_request=raw_request_path,
        assert_pre_verl_lean=True,
    )

    assert "Inspect initial context: passed" in result


def test_inspect_initial_context_accepts_redacted_raw_request_body_messages(
    tmp_path: Path,
) -> None:
    run_dir = _write_initial_context_run(
        tmp_path,
        user_content={
            "task": {"issue_statement": "Fix parser"},
            "constraints": {"tests": "Final verifier command is not exposed."},
            "repository_context": [
                {
                    "path": "README.rst",
                    "preview": "badge.svg?token=Buxy4WptLb\nProject guide",
                }
            ],
            "repository_hints": {
                "candidate_files": [
                    {
                        "path": "src/parser.py",
                        "confidence": "high",
                        "matched_terms": ["parser"],
                    }
                ],
                "fallback_search_terms": ["parser"],
                "usage_note": "These are starting points for investigation, not answers.",
            },
        },
    )
    prepared_path = run_dir / "artifacts" / "prepared_messages_1.json"
    raw_request_path = run_dir / "artifacts" / "raw_provider_request_1.json"
    prepared = json.loads(prepared_path.read_text(encoding="utf-8"))
    raw_request = json.loads(raw_request_path.read_text(encoding="utf-8"))
    pre_redaction_projection_hash = stable_hash(
        _project_prepared_messages(prepared["messages"])
    )
    raw_request["prepared_messages_projection_hash"] = pre_redaction_projection_hash
    raw_request["provider_body_message_projection_hash"] = pre_redaction_projection_hash
    raw_request["prepared_messages_body_equivalent"] = True
    raw_request["body"]["messages"][1]["content"] = raw_request["body"]["messages"][1][
        "content"
    ].replace("token=Buxy4WptLb", "token=<REDACTED_CREDENTIAL>")
    raw_request["redaction_report"] = {
        "schema_version": "repo_harness_provider_redaction_report_v0",
        "redaction_policy": "key_aware_span_based_v0",
        "secret_span_paths": ["$.body.messages[1].content"],
        "secret_span_redaction_count": 1,
    }
    raw_request_path.write_text(
        json.dumps(raw_request, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _refresh_event_and_manifest_ref(run_dir, raw_request_path.relative_to(run_dir).as_posix())

    result = inspect_initial_context(
        run_dir,
        first_model_call=True,
        assert_pre_verl_lean=True,
    )

    payload = json.loads(result.split("\n", 1)[1])
    provider_body = payload["provider_body"]
    assert provider_body["prepared_projection_equivalent"] is True
    assert provider_body["redacted_message_projection_equivalent"] is False
    assert (
        provider_body["projection_equivalence_source"]
        == "recorded_pre_redaction_binding"
    )
    assert provider_body["recorded_pre_redaction_equivalence"]["usable"] is True


def test_inspect_initial_context_allows_disabled_repository_hints_profile(
    tmp_path: Path,
) -> None:
    run_dir = _write_initial_context_run(
        tmp_path,
        user_content={
            "task": {"issue_statement": "Fix parser"},
            "constraints": {"tests": "Final verifier command is not exposed."},
            "repository_context": [{"path": "README.md", "preview": "Project guide"}],
        },
        repository_hints_mode="disabled",
    )

    result = inspect_initial_context(
        run_dir,
        first_model_call=True,
        assert_pre_verl_lean=True,
    )

    payload = json.loads(result.split("\n", 1)[1])
    assert payload["initial_context_profile"]["repository_hints_mode"] == "disabled"
    assert payload["repository_hints"]["candidate_count"] == 0


def test_inspect_initial_context_rejects_missing_hints_in_enabled_mode(
    tmp_path: Path,
) -> None:
    run_dir = _write_initial_context_run(
        tmp_path,
        user_content={
            "task": {"issue_statement": "Fix parser"},
            "constraints": {"tests": "Final verifier command is not exposed."},
            "repository_context": [{"path": "README.md", "preview": "Project guide"}],
        },
        repository_hints_mode="balanced_eval",
    )

    with pytest.raises(ConfigError, match="非 disabled repository_hints"):
        inspect_initial_context(run_dir, first_model_call=True, assert_pre_verl_lean=True)


def test_inspect_initial_context_rejects_incomplete_profile(tmp_path: Path) -> None:
    run_dir = _write_initial_context_run(tmp_path)
    profile_path = run_dir / "artifacts" / "initial_context_profile.json"
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    profile.pop("model_visible_messages_hash")
    profile_path.write_text(
        json.dumps(profile, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _refresh_manifest_ref(run_dir, "initial_context_profile")

    with pytest.raises(ConfigError, match="model_visible_messages_hash"):
        inspect_initial_context(run_dir, first_model_call=True, assert_pre_verl_lean=True)


def test_inspect_initial_context_rejects_profile_count_drift(tmp_path: Path) -> None:
    run_dir = _write_initial_context_run(tmp_path)
    profile_path = run_dir / "artifacts" / "initial_context_profile.json"
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    profile["repository_hints_candidate_count"] = 999
    profile_path.write_text(
        json.dumps(profile, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _refresh_manifest_ref(run_dir, "initial_context_profile")

    with pytest.raises(ConfigError, match="repository_hints_candidate_count"):
        inspect_initial_context(run_dir, first_model_call=True, assert_pre_verl_lean=True)


def test_inspect_initial_context_cli_dispatches(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    run_dir = _write_initial_context_run(tmp_path)

    result = main(
        [
            "inspect-initial-context",
            str(run_dir),
            "--first-model-call",
            "--assert-pre-verl-lean",
        ]
    )

    assert result == 0
    assert "Inspect initial context: passed" in capsys.readouterr().out


def _write_initial_context_run(
    tmp_path: Path,
    *,
    user_content: dict | None = None,
    include_second_call: bool = False,
    repository_hints_mode: str = "balanced_eval",
) -> Path:
    run_dir = tmp_path / "run_context"
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True)
    content = user_content or {
        "task": {"issue_statement": "Fix parser"},
        "constraints": {"tests": "Final verifier command is not exposed."},
        "repository_context": [{"path": "README.md", "preview": "Project guide"}],
        "repository_hints": {
            "candidate_files": [
                {
                    "path": "src/parser.py",
                    "confidence": "high",
                    "matched_terms": ["parser"],
                }
            ],
            "fallback_search_terms": ["parser"],
            "usage_note": "These are starting points for investigation, not answers.",
        },
    }
    first = _write_call_artifacts(
        run_dir,
        artifacts_dir,
        index=1,
        user_content=content,
        model_call_id="run_context_model_call_0001",
    )
    events = [*first["events"]]
    if include_second_call:
        second = _write_call_artifacts(
            run_dir,
            artifacts_dir,
            index=2,
            user_content={
                **content,
                "repository_hints": {
                    **content.get("repository_hints", {}),
                    "candidate_files": [
                        {
                            "path": "src/second.py",
                            "confidence": "medium",
                            "matched_terms": ["second"],
                        }
                    ],
                },
            },
            model_call_id="run_context_model_call_0002",
        )
        events.extend(second["events"])
    repository_hints = content.get("repository_hints")
    repository_hints_present = isinstance(repository_hints, dict)
    repository_hints_candidates = (
        repository_hints.get("candidate_files", []) if repository_hints_present else []
    )
    if not isinstance(repository_hints_candidates, list):
        repository_hints_candidates = []
    repository_context = content.get("repository_context", [])
    if not isinstance(repository_context, list):
        repository_context = []
    repository_context_preview_count = sum(
        len(str(entry.get("preview") or ""))
        for entry in repository_context
        if isinstance(entry, dict)
    )
    profile_ref = _write_json_ref(
        run_dir,
        artifacts_dir / "initial_context_profile.json",
        {
            "schema_version": "repo_harness_initial_context_profile_v0",
            "initial_context_policy_version": (
                "repo_harness_initial_context_policy_v1_lean_hints"
            ),
            "repository_hints_mode": repository_hints_mode,
            "repository_hints_config": {
                "mode": repository_hints_mode,
                "resolved_max_candidate_files": 0
                if repository_hints_mode == "disabled"
                else 8,
            },
            "repository_hints_presence": (
                "present" if repository_hints_present else "absent"
            ),
            "repository_hints_absence_reason": _test_repository_hints_absence_reason(
                content=content,
                repository_hints_present=repository_hints_present,
                repository_hints_mode=repository_hints_mode,
            ),
            "model_visible_messages_hash": stable_hash(first["prepared_messages"]),
            "first_user_content_hash": stable_hash(content),
            "first_user_content_char_count": len(
                json.dumps(content, ensure_ascii=False, sort_keys=True)
            ),
            "first_user_top_level_keys": sorted(content.keys()),
            "repository_context_entry_count": len(repository_context),
            "repository_hints_candidate_count": len(repository_hints_candidates),
            "repository_context_preview_char_count": repository_context_preview_count,
            "repository_hints_model_visible_hash": None
            if repository_hints_mode == "disabled"
            else "1" * 64,
            "repository_action_index_full_hash": "2" * 64,
            "repository_context_index_full_hash": "3" * 64,
            "forbidden_model_visible_fields_present": [],
        },
        "initial_context_profile",
    )
    events.append(
        {
            "event_type": "initial_context_profile_written",
            "data": {"initial_context_profile_ref": profile_ref},
            "artifact_refs": [profile_ref],
        }
    )
    (run_dir / "events.jsonl").write_text(
        "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events),
        encoding="utf-8",
    )
    manifest = {
        "artifacts": [
            *first["refs"],
            *(second["refs"] if include_second_call else []),
            profile_ref,
        ]
    }
    (run_dir / "artifacts.json").write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return run_dir


def _test_repository_hints_absence_reason(
    *,
    content: dict,
    repository_hints_present: bool,
    repository_hints_mode: str,
) -> str | None:
    if repository_hints_present:
        return None
    if repository_hints_mode == "disabled":
        return "repository_hints_mode_disabled"
    task = content.get("task", {})
    expected_files = task.get("expected_files", []) if isinstance(task, dict) else []
    issue_statement = str(task.get("issue_statement") or "") if isinstance(task, dict) else ""
    has_seed = bool(expected_files) or any(
        len(term) >= 3 for term in issue_statement.replace("_", " ").split()
    )
    return "unexpected_missing_repository_hints" if has_seed else "no_model_visible_hint_seed"


def _write_call_artifacts(
    run_dir: Path,
    artifacts_dir: Path,
    *,
    index: int,
    user_content: dict,
    model_call_id: str,
) -> dict[str, list[dict]]:
    prepared_messages = {
        "messages": [
            {"role": "system", "content": "system"},
            {"role": "user", "content": user_content},
        ],
        "model_input_hash": "a" * 64,
        "context_revision": index,
    }
    prepared_ref = _write_json_ref(
        run_dir,
        artifacts_dir / f"prepared_messages_{index}.json",
        prepared_messages,
        "prepared_messages",
    )
    body_messages = [
        {"role": "system", "content": "system"},
        {
            "role": "user",
            "content": json.dumps(user_content, ensure_ascii=False, sort_keys=True),
        },
    ]
    tool_ref = _write_json_ref(
        run_dir,
        artifacts_dir / f"tool_schema_snapshot_{index}.json",
        {"snapshot_sha256": "b" * 64},
        "tool_schema_snapshot",
    )
    raw_request_ref = _write_json_ref(
        run_dir,
        artifacts_dir / f"raw_provider_request_{index}.json",
        {
            "body": {
                "messages": body_messages,
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": "symbol_search",
                            "description": "Use repository_hints as starting points.",
                        },
                    }
                ],
            },
            "prepared_messages_ref": prepared_ref,
            "tool_schema_snapshot_ref": tool_ref,
            "model_call_id": model_call_id,
        },
        "raw_provider_request",
    )
    raw_response_ref = _write_json_ref(
        run_dir,
        artifacts_dir / f"raw_provider_response_{index}.json",
        {
            "usage": {"prompt_tokens": 42 + index},
            "raw_provider_request_ref": raw_request_ref,
        },
        "raw_provider_response",
    )
    events = [
        {
            "event_type": "model_call_started",
            "data": {
                "model_call_id": model_call_id,
                "prepared_messages_ref": prepared_ref,
                "tool_schema_snapshot_ref": tool_ref,
            },
            "artifact_refs": [prepared_ref, tool_ref],
        },
        {
            "event_type": "model_call_completed",
            "data": {
                "model_call_id": model_call_id,
                "raw_provider_request_ref": raw_request_ref,
                "raw_provider_response_ref": raw_response_ref,
            },
            "artifact_refs": [raw_request_ref, raw_response_ref],
        },
    ]
    return {
        "events": events,
        "refs": [prepared_ref, tool_ref, raw_request_ref, raw_response_ref],
        "prepared_messages": prepared_messages["messages"],
    }


def _write_json_ref(
    run_dir: Path,
    path: Path,
    payload: dict,
    kind: str,
) -> dict:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "kind": kind,
        "artifact_id": path.stem,
        "relative_path": path.relative_to(run_dir).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def _refresh_manifest_ref(run_dir: Path, kind: str) -> None:
    manifest_path = run_dir / "artifacts.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for artifact in manifest["artifacts"]:
        if artifact.get("kind") != kind:
            continue
        path = run_dir / artifact["relative_path"]
        artifact["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _refresh_event_and_manifest_ref(run_dir: Path, relative_path: str) -> None:
    path = run_dir / relative_path
    sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest_path = run_dir / "artifacts.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for artifact in manifest["artifacts"]:
        if artifact.get("relative_path") == relative_path:
            artifact["sha256"] = sha256
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    events_path = run_dir / "events.jsonl"
    events = [
        json.loads(line)
        for line in events_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    for event in events:
        _refresh_nested_ref(event, relative_path=relative_path, sha256=sha256)
    events_path.write_text(
        "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events),
        encoding="utf-8",
    )


def _refresh_nested_ref(value: object, *, relative_path: str, sha256: str) -> None:
    if isinstance(value, dict):
        if value.get("relative_path") == relative_path:
            value["sha256"] = sha256
        for child in value.values():
            _refresh_nested_ref(child, relative_path=relative_path, sha256=sha256)
    elif isinstance(value, list):
        for child in value:
            _refresh_nested_ref(child, relative_path=relative_path, sha256=sha256)
