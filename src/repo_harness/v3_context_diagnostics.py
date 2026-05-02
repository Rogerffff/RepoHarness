"""V3 context compaction and long rollout diagnostics."""

from __future__ import annotations

import json
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from repo_harness.errors import ConfigError
from repo_harness.evaluation.runner import run_task
from repo_harness.schema_base import stable_hash
from repo_harness.schema_versions import CONTEXT_COMPACTION_FACTS_SCHEMA_VERSION
from repo_harness.trajectory import ArtifactRef, read_jsonl, verify_artifact_manifest
from repo_harness.v3_visibility import V3ContaminationDenylist
from repo_harness.workspace.source_hash import compute_file_sha256, compute_source_tree_hash


CONTEXT_REPORT_VERSION = CONTEXT_COMPACTION_FACTS_SCHEMA_VERSION
LONG_ROLLOUT_DIAGNOSTICS_VERSION = "repo_harness_v3_long_rollout_diagnostics_v0"
CONTEXT_STAGE_REPORT_VERSION = "repo_harness_v3_context_diagnostics_stage_report_v0"


def build_v3_context_diagnostics(
    *,
    output_dir: str | Path,
    task_path: str | Path = "tests/fixtures/tasks/task_001.yaml",
) -> Path:
    """Run a deterministic long-output Agent Loop sample and write V3 context reports."""

    output_root = Path(output_dir)
    if output_root.exists():
        raise ConfigError(f"Stage 9 output directory 已存在，不能覆盖：{output_root}")
    output_root.mkdir(parents=True)
    inputs_dir = output_root / "generated_inputs"
    inputs_dir.mkdir()
    generated_repo = inputs_dir / "long_output_repo"
    generated_task = _write_long_context_task(
        inputs_dir / "long_output_task.yaml",
        base_task_path=Path(task_path),
        repo_dir=generated_repo,
    )
    run_root = output_root / "context_runs"
    run_root.mkdir()
    replay_path = _write_long_output_replay(inputs_dir / "long_output_replay.yaml")
    config_path = _write_context_run_config(
        inputs_dir / "long_output_run_config.yaml",
        replay_path=replay_path,
        output_dir=run_root,
    )
    run_dir = run_task(
        generated_task,
        config_path=config_path,
        output_dir=run_root,
        run_id="v3_stage_09_context_long_output",
    )
    context_report_path = output_root / "context_compaction_report.json"
    long_report_path = output_root / "long_rollout_diagnostics.json"
    context_report = _build_context_report(run_dir=run_dir, output_root=output_root)
    _write_json(context_report_path, context_report)
    long_report = _build_long_rollout_report(run_dir=run_dir, output_root=output_root)
    _write_json(long_report_path, long_report)
    stage_report = {
        "schema_version": CONTEXT_STAGE_REPORT_VERSION,
        "generated_at": _utc_timestamp(),
        "run_ref": _artifact_ref(
            run_dir,
            base_dir=output_root,
            artifact_id="stage9_context_run",
            kind="directory",
        ),
        "context_compaction_report_ref": _artifact_ref(
            context_report_path,
            base_dir=output_root,
            artifact_id="context_compaction_report",
            kind="json",
        ),
        "long_rollout_diagnostics_ref": _artifact_ref(
            long_report_path,
            base_dir=output_root,
            artifact_id="long_rollout_diagnostics",
            kind="json",
        ),
    }
    _write_json(output_root / "v3_context_diagnostics_report.json", stage_report)
    return output_root


def inspect_context_report(
    run_dir: str | Path,
    *,
    report: str | Path,
    assert_consistent: bool = False,
) -> str:
    root = Path(run_dir)
    report_path = Path(report)
    failures: list[str] = []
    payload = _read_json_for_inspect(report_path, failures)
    if payload.get("schema_version") != CONTEXT_REPORT_VERSION:
        failures.append("context_compaction_report schema_version 无效。")
    run_path = _resolve_run_path(root, payload)
    if run_path is None:
        failures.append("context_compaction_report 缺少 run path。")
    elif not run_path.exists():
        failures.append(f"context run directory 不存在：{run_path}")
    else:
        failures.extend(f"artifact manifest: {error}" for error in verify_artifact_manifest(run_path))
        _inspect_context_events(run_path=run_path, payload=payload, failures=failures)
    contamination = V3ContaminationDenylist().scan_payload(
        surface="context_compaction_report",
        payload=payload,
    )
    if not contamination.clean:
        terms = ", ".join(sorted({finding.matched_term for finding in contamination.findings}))
        failures.append(f"context compaction contamination scan failed: {terms}")
    if assert_consistent:
        if payload.get("compaction_observed") is not True:
            failures.append("assert-consistent requires compaction_observed=true。")
        if payload.get("observation_matches_prepared_messages") is not True:
            failures.append("observation_matches_prepared_messages 必须为 true。")
        if payload.get("diagnostic_only") is True:
            failures.append("consistent context report 不能标记 diagnostic_only。")
    lines = [
        f"Context report directory: {root}",
        f"Context report: {report_path}",
        f"Compaction observed: {payload.get('compaction_observed')}",
        f"Observation matches prepared messages: {payload.get('observation_matches_prepared_messages')}",
    ]
    if failures:
        raise ConfigError("; ".join(failures))
    if assert_consistent:
        lines.append("Inspect context report: consistent")
    lines.append("Inspect context report: passed")
    return "\n".join(lines)


def inspect_long_rollout_diagnostics(
    run_dir: str | Path,
    *,
    report: str | Path,
    assert_complete: bool = False,
) -> str:
    root = Path(run_dir)
    report_path = Path(report)
    failures: list[str] = []
    payload = _read_json_for_inspect(report_path, failures)
    if payload.get("schema_version") != LONG_ROLLOUT_DIAGNOSTICS_VERSION:
        failures.append("long_rollout_diagnostics schema_version 无效。")
    diagnostics = payload.get("diagnostics", [])
    if not isinstance(diagnostics, list):
        failures.append("long_rollout_diagnostics diagnostics 必须是列表。")
        diagnostics = []
    diagnostic_types = {str(item.get("diagnostic_type")) for item in diagnostics if isinstance(item, dict)}
    if assert_complete:
        required_any = {"repeated_tool_call", "no_progress", "context_limit"}
        if not diagnostic_types.intersection(required_any):
            failures.append("long rollout diagnostics 必须至少包含 repeated_tool_call、no_progress 或 context_limit。")
        if payload.get("context_report_ref") is None:
            failures.append("long rollout diagnostics 必须独立引用 context report。")
    ref = payload.get("context_report_ref")
    if isinstance(ref, dict):
        _resolve_ref(root, ref, failures)
    contamination = V3ContaminationDenylist().scan_payload(
        surface="context_compaction_report",
        payload=payload,
    )
    if not contamination.clean:
        terms = ", ".join(sorted({finding.matched_term for finding in contamination.findings}))
        failures.append(f"long rollout diagnostics contamination scan failed: {terms}")
    lines = [
        f"Long rollout diagnostics directory: {root}",
        f"Long rollout diagnostics: {report_path}",
        f"Diagnostic count: {len(diagnostics)}",
        "Diagnostic types: " + ", ".join(sorted(diagnostic_types)),
    ]
    if failures:
        raise ConfigError("; ".join(failures))
    if assert_complete:
        lines.append("Inspect long rollout diagnostics: complete")
    lines.append("Inspect long rollout diagnostics: passed")
    return "\n".join(lines)


def _build_context_report(*, run_dir: Path, output_root: Path) -> dict[str, Any]:
    events = read_jsonl(run_dir / "events.jsonl")
    transcript = read_jsonl(run_dir / "transcript.jsonl")
    tool_source_events = {
        str(event.get("data", {}).get("tool_call_id")): event.get("event_id")
        for event in events
        if event.get("event_type") in {"tool_completed", "tool_denied", "tool_failed", "tool_timeout", "tool_interrupted"}
        and event.get("data", {}).get("tool_call_id")
    }
    compaction_events: list[dict[str, Any]] = []
    observation_matches = True
    for event in events:
        if event.get("event_type") != "context_prepared":
            continue
        reduction = event.get("data", {}).get("context_reduction", {})
        replaced_ids = [str(item) for item in reduction.get("replaced_tool_result_ids", [])]
        if not replaced_ids:
            continue
        prepared_ref = _first_artifact_ref(event, kind="prepared_messages")
        state_ref = event.get("data", {}).get("content_replacement_state_ref")
        prepared_payload = _read_json(run_dir / prepared_ref["relative_path"]) if prepared_ref else {}
        prepared_messages = prepared_payload.get("messages", [])
        replaced_checks = _replacement_checks(
            prepared_messages=prepared_messages,
            replaced_tool_result_ids=replaced_ids,
        )
        observation_matches = observation_matches and all(check["matched"] for check in replaced_checks)
        compaction_events.append(
            {
                "context_revision": event.get("data", {}).get("context_revision"),
                "context_event_id": event.get("event_id"),
                "tokens_before": event.get("data", {}).get("tokens_before"),
                "tokens_after": event.get("data", {}).get("tokens_after"),
                "kept_tool_result_ids": _kept_tool_result_ids(transcript, replaced_ids),
                "dropped_tool_result_ids": [],
                "replaced_tool_result_ids": replaced_ids,
                "protected_tool_result_ids": reduction.get("protected_tool_result_ids", []),
                "replacement_artifact_refs": reduction.get("replacement_artifact_refs", []),
                "prepared_messages_ref": prepared_ref,
                "prepared_messages_sha256": (
                    compute_file_sha256(run_dir / prepared_ref["relative_path"]) if prepared_ref else None
                ),
                "model_input_hash": event.get("data", {}).get("model_input_hash"),
                "prepared_model_input_hash": prepared_payload.get("model_input_hash"),
                "context_revision_in_prepared_messages": prepared_payload.get("context_revision"),
                "content_replacement_state_ref": state_ref,
                "content_replacement_state_hash": event.get("data", {}).get("content_replacement_state_hash"),
                "observation_source_event_refs": {
                    tool_result_id: tool_source_events.get(_tool_call_id_from_result(transcript, tool_result_id))
                    for tool_result_id in replaced_ids
                },
                "replacement_checks": replaced_checks,
                "tool_pairing_validation": event.get("data", {}).get("tool_pairing_validation", {}),
            }
        )
    report = {
        "schema_version": CONTEXT_REPORT_VERSION,
        "generated_at": _utc_timestamp(),
        "run_id": run_dir.name,
        "run_ref": _artifact_ref(
            run_dir,
            base_dir=output_root,
            artifact_id="context_run",
            kind="directory",
        ),
        "compaction_policy": "deterministic_preview_replacement",
        "token_estimator_version": "repo_harness_char_estimator_v0",
        "compaction_observed": bool(compaction_events),
        "context_events": compaction_events,
        "observation_matches_prepared_messages": bool(compaction_events) and observation_matches,
        "diagnostic_only": False,
        "training_export_context_revisions": [
            event["context_revision"] for event in compaction_events if event.get("context_revision") is not None
        ],
    }
    return report


def _build_long_rollout_report(*, run_dir: Path, output_root: Path) -> dict[str, Any]:
    events = read_jsonl(run_dir / "events.jsonl")
    diagnostics: list[dict[str, Any]] = []
    repeated = _repeated_tool_calls(events)
    diagnostics.extend(repeated)
    if repeated and not _has_mutating_tool(events):
        diagnostics.append(
            {
                "diagnostic_type": "no_progress",
                "severity": "warning",
                "reason": "repeated tool calls without mutating tool activity",
                "evidence_event_ids": sorted(
                    {
                        event_id
                        for item in repeated
                        for event_id in item.get("evidence_event_ids", [])
                    }
                ),
                "diagnostic_only": True,
            }
        )
    if any(event.get("error_type") == "context_limit" for event in events):
        diagnostics.append(
            {
                "diagnostic_type": "context_limit",
                "severity": "error",
                "reason": "budget exhausted before model call",
                "evidence_event_ids": [
                    str(event.get("event_id"))
                    for event in events
                    if event.get("error_type") == "context_limit"
                ],
                "diagnostic_only": True,
            }
        )
    context_report_path = output_root / "context_compaction_report.json"
    return {
        "schema_version": LONG_ROLLOUT_DIAGNOSTICS_VERSION,
        "generated_at": _utc_timestamp(),
        "run_id": run_dir.name,
        "run_ref": _artifact_ref(
            run_dir,
            base_dir=output_root,
            artifact_id="long_rollout_run",
            kind="directory",
        ),
        "context_report_ref": (
            _artifact_ref(
                context_report_path,
                base_dir=output_root,
                artifact_id="context_compaction_report_for_long_rollout",
                kind="json",
            )
            if context_report_path.exists()
            else None
        ),
        "diagnostics": diagnostics,
        "diagnostic_type_distribution": dict(
            sorted(Counter(item["diagnostic_type"] for item in diagnostics).items())
        ),
    }


def _write_long_output_replay(path: Path) -> Path:
    payload = {
        "script_id": "v3_stage_09_context_long_output",
        "task_id": "task_001",
        "steps": [
            {
                "step_id": "read_long_first",
                "action": "tool_call",
                "tool_call_id": "call_long_output",
                "tool_name": "read_file",
                "arguments": {"path": "long_context.txt"},
            },
            {
                "step_id": "read_long_repeated",
                "action": "tool_call",
                "tool_call_id": "call_long_output_repeat",
                "tool_name": "read_file",
                "arguments": {"path": "long_context.txt"},
            },
            {
                "step_id": "final",
                "action": "final_answer",
                "assistant_text": "Recorded long-output diagnostics.",
            },
        ],
        "metadata": {"fixture_kind": "v3_context_diagnostics"},
    }
    _write_yaml(path, payload)
    return path


def _write_long_context_task(path: Path, *, base_task_path: Path, repo_dir: Path) -> Path:
    base_task = yaml.safe_load(base_task_path.read_text(encoding="utf-8"))
    if not isinstance(base_task, dict):
        raise ConfigError(f"Stage 9 base task 顶层必须是 object：{base_task_path}")
    base_repo = (base_task_path.parent / str(base_task["repo"])).resolve()
    shutil.copytree(base_repo, repo_dir)
    long_text = "\n".join(
        f"context diagnostic line {index:03d} " + ("x" * 80)
        for index in range(260)
    )
    (repo_dir / "long_context.txt").write_text(long_text + "\n", encoding="utf-8")
    task = dict(base_task)
    source_rel = repo_dir.relative_to(path.parent).as_posix()
    task["repo"] = source_rel
    task["repo_source_spec"] = {
        "source_type": "local_repository",
        "source_path": source_rel,
        "current_commit": "stage9-generated-long-context",
        "working_tree_clean": True,
        "allow_dirty_snapshot": False,
        "base_commit": "stage9-generated-long-context",
        "decontamination_status": "stage9_generated_public_fixture",
    }
    task["issue"] = (
        "Read the long diagnostic file twice so the harness can audit deterministic "
        "tool observation compaction."
    )
    task["expected_files"] = list(dict.fromkeys([*task.get("expected_files", []), "long_context.txt"]))
    _write_yaml(path, task)
    return path


def _write_context_run_config(path: Path, *, replay_path: Path, output_dir: Path) -> Path:
    payload = {
        "run_id_prefix": "v3_stage_09_context",
        "model": {
            "provider": "replay",
            "model_id": "replay-script-v0",
            "replay_script_path": replay_path.as_posix(),
        },
        "runtime": {
            "scaffold_id": "simple_react",
            "execution_mode": "local_process",
            "permission_mode": "auto",
            "test_feedback_policy": "disabled",
            "feedback_tests_passed_policy": "continue",
            "max_turns": 4,
            "max_tool_calls": 4,
            "max_test_runs": 0,
            "task_timeout_sec": 120,
        },
        "workspace": {
            "output_dir": output_dir.as_posix(),
            "keep_workspace": True,
            "default_command_timeout_sec": 60,
            "max_tool_output_chars": 30000,
        },
        "context_management": {
            "max_context_tokens": 120000,
            "tool_result_aggregate_budget_chars": 800,
            "keep_recent_turns": 0,
            "keep_recent_test_results": 0,
            "compact_strategy": "deterministic_preview_replacement",
        },
        "evaluation": {
            "concurrency": 1,
            "final_verifier_mode": "strict_patch_replay",
        },
    }
    _write_yaml(path, payload)
    return path


def _inspect_context_events(*, run_path: Path, payload: dict[str, Any], failures: list[str]) -> None:
    for event in payload.get("context_events", []):
        if event.get("tokens_after", 0) >= event.get("tokens_before", 0):
            failures.append("context event tokens_after 必须小于 tokens_before。")
        pairing = event.get("tool_pairing_validation", {})
        if pairing.get("ok") is not True:
            failures.append("compaction 后 tool pairing 必须完整。")
        prepared_ref = event.get("prepared_messages_ref")
        if not isinstance(prepared_ref, dict):
            failures.append("context event 缺少 prepared_messages_ref。")
            continue
        prepared_path = _resolve_ref(run_path, prepared_ref, failures)
        if prepared_path is None:
            continue
        prepared_payload = _read_json_for_inspect(prepared_path, failures)
        if compute_file_sha256(prepared_path) != event.get("prepared_messages_sha256"):
            failures.append("prepared_messages_sha256 不匹配。")
        if prepared_payload.get("model_input_hash") != event.get("model_input_hash"):
            failures.append("model_input_hash 与 prepared messages 不一致。")
        if prepared_payload.get("context_revision") != event.get("context_revision"):
            failures.append("context_revision 与 prepared messages 不一致。")
        for check in event.get("replacement_checks", []):
            if check.get("matched") is not True:
                failures.append(f"替换后的 observation 未出现在 prepared messages：{check}")


def _repeated_tool_calls(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        if event.get("event_type") != "tool_requested":
            continue
        data = event.get("data", {})
        tool_name = str(data.get("tool_name") or "")
        arguments = data.get("arguments") or {}
        key = stable_hash({"tool_name": tool_name, "arguments": arguments})
        by_key[key].append(event)
    diagnostics = []
    for key, grouped in by_key.items():
        if len(grouped) < 2:
            continue
        first = grouped[0].get("data", {})
        diagnostics.append(
            {
                "diagnostic_type": "repeated_tool_call",
                "severity": "warning",
                "tool_name": first.get("tool_name"),
                "normalized_arguments_hash": key,
                "count": len(grouped),
                "tool_call_ids": [
                    str(event.get("data", {}).get("tool_call_id")) for event in grouped
                ],
                "evidence_event_ids": [str(event.get("event_id")) for event in grouped],
                "diagnostic_only": True,
            }
        )
    return diagnostics


def _has_mutating_tool(events: list[dict[str, Any]]) -> bool:
    mutating = {"edit_file", "create_file"}
    return any(
        event.get("event_type") == "tool_requested"
        and event.get("data", {}).get("tool_name") in mutating
        for event in events
    )


def _replacement_checks(
    *,
    prepared_messages: list[dict[str, Any]],
    replaced_tool_result_ids: list[str],
) -> list[dict[str, Any]]:
    checks = []
    for tool_result_id in replaced_tool_result_ids:
        matched = False
        for message in prepared_messages:
            if message.get("role") != "tool":
                continue
            message_result_id = str(message.get("tool_result_id") or message.get("tool_call_id") or "")
            if message_result_id == tool_result_id and message.get("context_replacement") is True:
                matched = True
                break
        checks.append({"tool_result_id": tool_result_id, "matched": matched})
    return checks


def _kept_tool_result_ids(transcript: list[dict[str, Any]], replaced_ids: list[str]) -> list[str]:
    replaced = set(replaced_ids)
    return sorted(
        {
            str(record.get("tool_result_id") or record.get("tool_call_id"))
            for record in transcript
            if record.get("role") == "tool"
            and str(record.get("tool_result_id") or record.get("tool_call_id")) not in replaced
        }
    )


def _tool_call_id_from_result(transcript: list[dict[str, Any]], tool_result_id: str) -> str:
    for record in transcript:
        result_id = str(record.get("tool_result_id") or record.get("tool_call_id") or "")
        if result_id == tool_result_id:
            return str(record.get("tool_call_id") or result_id)
    return tool_result_id


def _first_artifact_ref(event: dict[str, Any], *, kind: str) -> dict[str, Any] | None:
    for ref in event.get("artifact_refs", []):
        if ref.get("kind") == kind:
            return ref
    return None


def _resolve_run_path(root: Path, payload: dict[str, Any]) -> Path | None:
    ref = payload.get("run_ref")
    if not isinstance(ref, dict):
        return None
    relative = Path(str(ref.get("relative_path", "")))
    return relative if relative.is_absolute() else root / relative


def _resolve_ref(base_dir: Path, ref_payload: dict[str, Any], failures: list[str]) -> Path | None:
    try:
        ref = ArtifactRef.model_validate(ref_payload)
    except ValidationError as exc:
        failures.append(f"ArtifactRef schema 无效：{exc}")
        return None
    relative = Path(ref.relative_path)
    path = relative if relative.is_absolute() else base_dir / relative
    if not path.exists():
        failures.append(f"ArtifactRef 路径不存在：{ref.relative_path}")
        return None
    actual_sha = compute_source_tree_hash(path) if path.is_dir() else compute_file_sha256(path)
    if actual_sha != ref.sha256:
        failures.append(f"ArtifactRef sha256 不匹配：{ref.relative_path}")
    if not path.is_dir() and path.stat().st_size != ref.size_bytes:
        failures.append(f"ArtifactRef size_bytes 不匹配：{ref.relative_path}")
    return path


def _artifact_ref(
    path: Path,
    *,
    base_dir: Path,
    artifact_id: str,
    kind: str,
    redaction_status: str = "not_required",
) -> dict[str, Any]:
    if path.is_dir():
        digest = compute_source_tree_hash(path)
        size_bytes = 0
    else:
        digest = compute_file_sha256(path)
        size_bytes = path.stat().st_size
    return ArtifactRef(
        artifact_id=artifact_id,
        relative_path=_relative_path(path, base_dir),
        kind=kind,
        sha256=digest,
        size_bytes=size_bytes,
        redaction_status=redaction_status,
        retention_policy="keep",
    ).model_dump(mode="json")


def _relative_path(path: Path, base_dir: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(base_dir.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_json_for_inspect(path: Path, failures: list[str]) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        failures.append(f"JSON 文件不存在：{path}")
        return {}
    except json.JSONDecodeError as exc:
        failures.append(f"JSON 文件无效：{path}: {exc}")
        return {}
    if not isinstance(payload, dict):
        failures.append(f"JSON 顶层必须是 object：{path}")
        return {}
    return payload


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_yaml(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
