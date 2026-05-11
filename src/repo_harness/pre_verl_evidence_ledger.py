"""Pre-verl 开发集证据 ledger。"""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from repo_harness.agent_loop.loop import PROVIDER_TIMEOUT_POLICY_VERSION
from repo_harness.errors import ConfigError, RepoHarnessError
from repo_harness.pre_verl_agentloop import (
    PRE_VERL_RUN_CONFIG_PREFLIGHT_POLICY_VERSION,
    inspect_model_visible_context,
    validate_pre_verl_run_config_entry,
)

PRE_VERL_EVIDENCE_LEDGER_SCHEMA_VERSION = "repo_harness_pre_verl_evidence_ledger_v0"
PRE_VERL_EVIDENCE_LEDGER_HARNESS_POLICY_VERSION = "repo_harness_pre_verl_dev_evidence_policy_v0"
PRE_VERL_EVIDENCE_LEDGER_INSPECT_POLICY_VERSION = "repo_harness_pre_verl_evidence_ledger_inspect_v0"
DEV23_EXPECTED_FORMAL_DENOMINATOR = 23
DEV23_EXPECTED_RESULT_COUNTS = {"success": 11, "failed": 10, "inconclusive": 2}

ContextInspector = Callable[[Path], tuple[str, str | None]]


def build_pre_verl_evidence_ledger(
    run_root: str | Path,
    *,
    output: str | Path | None = None,
    context_inspector: ContextInspector | None = None,
) -> Path:
    """为一个 pre-verl 开发集批次构建机器可读证据索引。"""

    root = Path(run_root)
    if not root.exists():
        raise ConfigError(f"pre-verl evidence run root 不存在：{root}")
    if not (root / "run_task_runs").is_dir():
        raise ConfigError(f"pre-verl evidence run root 缺少 run_task_runs/：{root}")

    analysis_dir = root / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    output_path = Path(output) if output is not None else analysis_dir / "dev23_evidence_ledger.json"
    preflight_dir = analysis_dir / "run_config_preflight_reports"
    preflight_dir.mkdir(parents=True, exist_ok=True)

    task_order = _task_order(root)
    issue_sections = _issue_sections(root / "analysis" / "dev23_harness_issue_log.md")
    formal_entries = []
    for run_dir in _formal_run_dirs(root):
        entry = _formal_entry(
            root=root,
            run_dir=run_dir,
            preflight_dir=preflight_dir,
            issue_sections=issue_sections,
            context_inspector=context_inspector or _default_context_inspector,
        )
        formal_entries.append(entry)
    formal_entries.sort(key=lambda item: _task_sort_key(item["task_id"], task_order))

    discarded_by_task = _discarded_attempts_by_task(root, [entry["task_id"] for entry in formal_entries])
    for entry in formal_entries:
        entry["discarded_attempts"] = discarded_by_task.get(entry["task_id"], [])

    result_counts = Counter(entry["formal_result"] for entry in formal_entries)
    config_revisions = _config_revision_summary(formal_entries)
    ledger = {
        "schema_version": PRE_VERL_EVIDENCE_LEDGER_SCHEMA_VERSION,
        "created_at": _now(),
        "run_root": root.as_posix(),
        "baseline_id": _baseline_id(root),
        "harness_policy_version": PRE_VERL_EVIDENCE_LEDGER_HARNESS_POLICY_VERSION,
        "preflight_policy_version": PRE_VERL_RUN_CONFIG_PREFLIGHT_POLICY_VERSION,
        "timeout_policy_version": PROVIDER_TIMEOUT_POLICY_VERSION,
        "inspect_policy_version": PRE_VERL_EVIDENCE_LEDGER_INSPECT_POLICY_VERSION,
        "formal_denominator": len(formal_entries),
        "formal_result_counts": {
            "success": result_counts.get("success", 0),
            "failed": result_counts.get("failed", 0),
            "inconclusive": result_counts.get("inconclusive", 0),
        },
        "accepted_rate_denominator_source": "formal_run_entries_only",
        "discarded_attempt_count": sum(len(item["discarded_attempts"]) for item in formal_entries),
        "config_revisions": config_revisions,
        "entries": formal_entries,
    }
    _write_json(output_path, ledger)
    return output_path


def inspect_pre_verl_evidence_ledger(
    ledger: str | Path,
    *,
    assert_complete: bool = False,
    expected_formal_denominator: int | None = None,
    expected_result_counts: dict[str, int] | None = None,
) -> str:
    """只读检查 pre-verl evidence ledger，不依赖 latest run 推断。"""

    ledger_path = Path(ledger)
    payload = _read_json(ledger_path)
    failures: list[str] = []
    if payload.get("schema_version") != PRE_VERL_EVIDENCE_LEDGER_SCHEMA_VERSION:
        failures.append("schema_version 不是 repo_harness_pre_verl_evidence_ledger_v0")
    entries = payload.get("entries")
    if not isinstance(entries, list):
        failures.append("entries 必须是列表")
        entries = []
    expected_denominator = (
        expected_formal_denominator
        if expected_formal_denominator is not None
        else DEV23_EXPECTED_FORMAL_DENOMINATOR
    )
    expected_counts = expected_result_counts or DEV23_EXPECTED_RESULT_COUNTS

    if assert_complete:
        _inspect_complete_ledger(
            ledger_path,
            payload,
            entries,
            failures,
            expected_formal_denominator=expected_denominator,
            expected_result_counts=expected_counts,
        )

    lines = [
        f"Pre-verl evidence ledger: {ledger_path}",
        f"Schema: {payload.get('schema_version')}",
        f"Run root: {payload.get('run_root')}",
        f"Formal denominator: {payload.get('formal_denominator')}",
        f"Formal result counts: {payload.get('formal_result_counts')}",
        f"Discarded attempts: {payload.get('discarded_attempt_count')}",
    ]
    if failures:
        if assert_complete:
            raise ConfigError("; ".join(failures))
        lines.append("Failures:")
        lines.extend(f"- {failure}" for failure in failures)
    else:
        lines.append("Inspect pre-verl evidence ledger: complete" if assert_complete else "Inspect pre-verl evidence ledger: readable")
    return "\n".join(lines)


def _formal_entry(
    *,
    root: Path,
    run_dir: Path,
    preflight_dir: Path,
    issue_sections: dict[str, str],
    context_inspector: ContextInspector,
) -> dict[str, Any]:
    metrics = _read_json_if_exists(run_dir / "metrics.json")
    metadata = _read_json_if_exists(run_dir / "run_metadata.json")
    run_status = _read_json(run_dir / "run_status.json")
    boundary = _read_json_if_exists(run_dir / "final_verifier_boundary.json")
    facts = _read_json_if_exists(run_dir / "run_config_facts.json")
    reward = _read_json_if_exists(run_dir / "reward.json")
    events = _read_jsonl_if_exists(run_dir / "events.jsonl")
    task_id = _text(metadata.get("task_id")) or _text(boundary.get("task_id")) or _task_id_from_task_yaml(run_dir)
    if not task_id:
        raise ConfigError(f"formal run 缺少 task_id：{run_dir}")

    config_path = _config_path(root, task_id)
    task_definition_path = _task_definition_path(root, task_id)
    preflight_ref: dict[str, Any] | None = None
    preflight_status = "not_generated"
    preflight_failure_count = 0
    preflight_failures: list[str] = []
    if config_path is not None and task_definition_path is not None:
        preflight_path = preflight_dir / f"{task_id}.json"
        preflight = validate_pre_verl_run_config_entry(
            task_definition_path=task_definition_path,
            config_path=config_path,
            report_path=preflight_path,
            assert_resolved_tools_derived=False,
        )
        preflight_ref = _file_ref(root, preflight_path)
        preflight_failures = [
            str(item)
            for item in preflight.get("failures") or []
        ]
        preflight_failure_count = len(preflight_failures)
        preflight_status = "passed" if preflight.get("passed") else "failed_current_policy"

    context_status, context_error = context_inspector(run_dir)
    export_summary = _export_summary(run_dir)
    compaction_counts = _compaction_counts(events)
    no_progress = _no_progress_signals(events, metadata)
    config_revision = _config_revision(facts, config_path)
    section = issue_sections.get(task_id, "")
    formal_result = _formal_result(metrics, boundary, reward)
    failure_category = _failure_category(boundary, metadata, reward, formal_result)
    return {
        "task_id": task_id,
        "formal_run_dir": _relative(root, run_dir),
        "observed_formal_run_status": run_status.get("status"),
        "formal_result": formal_result,
        "discarded_attempts": [],
        "config_revision": config_revision,
        "config_revision_reason": _config_revision_reason(config_revision),
        "harness_policy_version": PRE_VERL_EVIDENCE_LEDGER_HARNESS_POLICY_VERSION,
        "preflight_policy_version": PRE_VERL_RUN_CONFIG_PREFLIGHT_POLICY_VERSION,
        "timeout_policy_version": _timeout_policy_version(facts),
        "config_preflight_ref": preflight_ref,
        "config_preflight_status": preflight_status,
        "config_preflight_failure_count": preflight_failure_count,
        "config_preflight_failures": preflight_failures,
        "config_preflight_policy_difference_acknowledged": _preflight_difference_acknowledged(
            config_revision,
            preflight_status,
            preflight_failures,
        ),
        "context_inspect_status": context_status,
        "context_inspect_error": context_error,
        "export_audit_status": export_summary["status"],
        "export_summary": export_summary,
        "final_verifier_status": _text(boundary.get("final_verifier_status"))
        or _text(metrics.get("final_verifier_status"))
        or "unknown",
        "final_verifier_failure_category": boundary.get("failure_category"),
        "failure_category": failure_category,
        "compaction_counts": compaction_counts,
        "no_progress_signals": no_progress,
        "harness_issue_refs": _harness_issue_refs(section, metadata),
        "fix_commit_refs": _fix_commit_refs(section),
    }


def _default_context_inspector(run_dir: Path) -> tuple[str, str | None]:
    try:
        inspect_model_visible_context(
            run_dir,
            assert_no_hidden_test_material=True,
            assert_prepared_messages_bound=True,
            assert_provider_body_equivalent=True,
            assert_tool_results_recoverable=True,
            assert_no_over_redaction=True,
        )
    except RepoHarnessError as exc:
        return "failed", str(exc)
    return "passed", None


def _inspect_complete_ledger(
    ledger_path: Path,
    payload: dict[str, Any],
    entries: list[Any],
    failures: list[str],
    *,
    expected_formal_denominator: int,
    expected_result_counts: dict[str, int],
) -> None:
    root = _ledger_run_root(payload, ledger_path, failures)
    expected_versions = {
        "harness_policy_version": PRE_VERL_EVIDENCE_LEDGER_HARNESS_POLICY_VERSION,
        "preflight_policy_version": PRE_VERL_RUN_CONFIG_PREFLIGHT_POLICY_VERSION,
        "timeout_policy_version": PROVIDER_TIMEOUT_POLICY_VERSION,
        "inspect_policy_version": PRE_VERL_EVIDENCE_LEDGER_INSPECT_POLICY_VERSION,
    }
    for key, expected in expected_versions.items():
        if payload.get(key) != expected:
            failures.append(f"{key} 必须是 {expected}，实际是 {payload.get(key)}")
    if payload.get("formal_denominator") != expected_formal_denominator:
        failures.append(
            f"formal_denominator 必须是 {expected_formal_denominator}，实际是 {payload.get('formal_denominator')}"
        )
    if payload.get("formal_result_counts") != expected_result_counts:
        failures.append(
            f"formal_result_counts 必须是 {expected_result_counts}，实际是 {payload.get('formal_result_counts')}"
        )
    if payload.get("formal_denominator") != len(entries):
        failures.append("formal_denominator 必须等于 entries 数量，不能包含 discarded attempts")
    if payload.get("accepted_rate_denominator_source") != "formal_run_entries_only":
        failures.append("accepted_rate_denominator_source 必须是 formal_run_entries_only")

    seen_tasks: set[str] = set()
    recomputed_counts = Counter()
    recomputed_discarded = 0
    for raw in entries:
        if not isinstance(raw, dict):
            failures.append("entry 必须是对象")
            continue
        task_id = raw.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            failures.append("entry.task_id 缺失")
            continue
        if task_id in seen_tasks:
            failures.append(f"{task_id}: 每个正式任务只能有一个 formal run")
        seen_tasks.add(task_id)
        _inspect_entry(raw, root, failures)
        result = raw.get("formal_result")
        if isinstance(result, str):
            recomputed_counts[result] += 1
        discarded = raw.get("discarded_attempts") or []
        if isinstance(discarded, list):
            recomputed_discarded += len(discarded)
    if dict((key, recomputed_counts.get(key, 0)) for key in ("success", "failed", "inconclusive")) != payload.get(
        "formal_result_counts"
    ):
        failures.append("formal_result_counts 与 entries 聚合结果不一致")
    if payload.get("discarded_attempt_count") != recomputed_discarded:
        failures.append("discarded_attempt_count 与 entries.discarded_attempts 聚合结果不一致")


def _inspect_entry(entry: dict[str, Any], root: Path, failures: list[str]) -> None:
    task_id = str(entry.get("task_id"))
    formal_run_dir = entry.get("formal_run_dir")
    if not isinstance(formal_run_dir, str) or not formal_run_dir.startswith("run_task_runs/"):
        failures.append(f"{task_id}: formal_run_dir 必须位于 run_task_runs/ 下")
        formal_path = None
    else:
        formal_path = _resolve_relative_dir(
            root,
            formal_run_dir,
            failures,
            owner=task_id,
            label="formal_run_dir",
        )
        if formal_path is not None:
            status = _read_json_if_exists(formal_path / "run_status.json").get("status")
            if status != "FINALIZED":
                failures.append(f"{task_id}: formal run 必须是 FINALIZED，实际是 {status}")
            if entry.get("observed_formal_run_status") != "FINALIZED":
                failures.append(
                    f"{task_id}: observed_formal_run_status 必须是 FINALIZED，实际是 {entry.get('observed_formal_run_status')}"
                )
    for key in ("harness_policy_version", "preflight_policy_version", "timeout_policy_version"):
        if not isinstance(entry.get(key), str) or not entry.get(key):
            failures.append(f"{task_id}: 缺少 {key}")
    if not entry.get("config_revision"):
        failures.append(f"{task_id}: 缺少 config_revision")
    if entry.get("config_preflight_ref") is None:
        failures.append(f"{task_id}: 缺少 config_preflight_ref")
    else:
        _inspect_file_ref(
            entry.get("config_preflight_ref"),
            root,
            failures,
            owner=task_id,
            label="config_preflight_ref",
        )
    _inspect_preflight_consistency(entry, failures)
    if entry.get("config_preflight_status") != "passed" and not entry.get(
        "config_preflight_policy_difference_acknowledged"
    ):
        failures.append(f"{task_id}: config preflight 未通过且没有记录策略差异确认")
    if entry.get("context_inspect_status") != "passed":
        failures.append(f"{task_id}: context inspect 未通过")

    _inspect_export_expectations(entry, formal_path, failures)
    _inspect_discarded_attempts(entry, root, failures)
    _inspect_verifier_consistency(entry, failures)


def _inspect_preflight_consistency(entry: dict[str, Any], failures: list[str]) -> None:
    task_id = str(entry.get("task_id"))
    status = entry.get("config_preflight_status")
    raw_failures = entry.get("config_preflight_failures")
    if not isinstance(raw_failures, list) or not all(isinstance(item, str) for item in raw_failures):
        failures.append(f"{task_id}: config_preflight_failures 必须是字符串列表")
        raw_failures = []
    failure_count = entry.get("config_preflight_failure_count")
    if failure_count != len(raw_failures):
        failures.append(f"{task_id}: config_preflight_failure_count 与 config_preflight_failures 数量不一致")
    expected_acknowledged = _preflight_difference_acknowledged(
        str(entry.get("config_revision") or ""),
        str(status or ""),
        [str(item) for item in raw_failures],
    )
    if entry.get("config_preflight_policy_difference_acknowledged") is not expected_acknowledged:
        failures.append(f"{task_id}: config_preflight_policy_difference_acknowledged 与失败内容不一致")
    if status == "passed" and raw_failures:
        failures.append(f"{task_id}: config preflight 已通过时不能记录失败项")
    if status == "failed_current_policy" and not raw_failures:
        failures.append(f"{task_id}: config preflight 未通过时必须记录失败项")
    if status not in {"passed", "failed_current_policy", "not_generated"}:
        failures.append(f"{task_id}: config_preflight_status 不合法：{status}")


def _inspect_export_expectations(entry: dict[str, Any], formal_path: Path | None, failures: list[str]) -> None:
    task_id = str(entry.get("task_id"))
    result = entry.get("formal_result")
    export = entry.get("export_summary") if isinstance(entry.get("export_summary"), dict) else {}
    trainable = int(export.get("trainable_count") or 0)
    invalid = int(export.get("invalid_count") or 0)
    skipped = int(export.get("skipped_count") or 0)
    status = entry.get("export_audit_status")
    if result == "success":
        if status != "passed" or trainable <= 0 or invalid != 0:
            failures.append(f"{task_id}: success run 必须有 clean trainable export")
    elif result == "failed":
        if trainable != 0:
            failures.append(f"{task_id}: failed run 不能包含 trainable samples")
        if status != "failed":
            failures.append(f"{task_id}: failed run 的 export audit status 必须是 failed")
    elif result == "inconclusive":
        if trainable != 0 or invalid != 0 or skipped <= 0:
            failures.append(f"{task_id}: inconclusive run 必须只有 skipped samples，不能有 trainable 或 invalid")
        if status != "passed_with_warnings":
            failures.append(f"{task_id}: inconclusive run 的 export audit status 必须是 passed_with_warnings")
    else:
        failures.append(f"{task_id}: formal_result 必须是 success、failed 或 inconclusive")
    export_refs = export.get("export_manifest_refs")
    if not isinstance(export_refs, list):
        failures.append(f"{task_id}: export_manifest_refs 必须是列表")
        return
    if formal_path is None:
        return
    for index, ref in enumerate(export_refs):
        _inspect_file_ref(
            ref,
            formal_path,
            failures,
            owner=task_id,
            label=f"export_manifest_refs[{index}]",
        )


def _inspect_discarded_attempts(entry: dict[str, Any], root: Path, failures: list[str]) -> None:
    task_id = str(entry.get("task_id"))
    discarded = entry.get("discarded_attempts")
    if not isinstance(discarded, list):
        failures.append(f"{task_id}: discarded_attempts 必须是列表")
        return
    for attempt in discarded:
        if not isinstance(attempt, dict):
            failures.append(f"{task_id}: discarded attempt 必须是对象")
            continue
        run_dir = attempt.get("run_dir")
        if not isinstance(run_dir, str) or not run_dir.startswith("discarded_runs/"):
            failures.append(f"{task_id}: discarded attempt 必须位于 discarded_runs/ 下")
        else:
            _resolve_relative_dir(
                root,
                run_dir,
                failures,
                owner=task_id,
                label="discarded attempt run_dir",
            )
        if not isinstance(attempt.get("discard_reason"), str) or not attempt.get("discard_reason"):
            failures.append(f"{task_id}: discarded attempt 缺少 discard_reason")
        if attempt.get("excluded_from_denominator") is not True:
            failures.append(f"{task_id}: discarded attempt 必须 excluded_from_denominator=true")


def _inspect_verifier_consistency(entry: dict[str, Any], failures: list[str]) -> None:
    task_id = str(entry.get("task_id"))
    result = entry.get("formal_result")
    verifier = entry.get("final_verifier_status")
    if result == "success" and verifier != "accepted":
        failures.append(f"{task_id}: success 必须对应 final_verifier_status=accepted")
    if result == "failed" and verifier != "rejected":
        failures.append(f"{task_id}: failed 必须对应 final_verifier_status=rejected")
    if result == "inconclusive" and verifier not in {"not_executed", "skipped"}:
        failures.append(f"{task_id}: inconclusive 必须对应 final_verifier_status=not_executed 或 skipped")


def _ledger_run_root(payload: dict[str, Any], ledger_path: Path, failures: list[str]) -> Path:
    raw = payload.get("run_root")
    if not isinstance(raw, str) or not raw:
        failures.append("run_root 缺失")
        return ledger_path.parent
    configured = Path(raw)
    candidates: list[Path] = [configured]
    if not configured.is_absolute():
        candidates.append((ledger_path.parent / configured))
    if ledger_path.parent.name == "analysis":
        candidates.append(ledger_path.parent.parent)
    for candidate in candidates:
        if (candidate / "run_task_runs").is_dir():
            return candidate
    failures.append(f"run_root 不存在或缺少 run_task_runs/：{raw}")
    return configured


def _resolve_relative_dir(
    base: Path,
    relative: str,
    failures: list[str],
    *,
    owner: str,
    label: str,
) -> Path | None:
    resolved = _resolve_inside_base(base, relative)
    if resolved is None:
        failures.append(f"{owner}: {label} 越过证据根目录：{relative}")
        return None
    if not resolved.is_dir():
        failures.append(f"{owner}: {label} 指向的目录不存在：{relative}")
        return None
    return resolved


def _inspect_file_ref(
    ref: Any,
    base: Path,
    failures: list[str],
    *,
    owner: str,
    label: str,
) -> None:
    if not isinstance(ref, dict):
        failures.append(f"{owner}: {label} 必须是对象")
        return
    path = ref.get("path")
    expected_sha = ref.get("sha256")
    if not isinstance(path, str) or not path:
        failures.append(f"{owner}: {label}.path 缺失")
        return
    resolved = _resolve_inside_base(base, path)
    if resolved is None:
        failures.append(f"{owner}: {label}.path 越过证据根目录：{path}")
        return
    if not resolved.is_file():
        failures.append(f"{owner}: {label}.path 指向的文件不存在：{path}")
        return
    if not isinstance(expected_sha, str) or not expected_sha:
        failures.append(f"{owner}: {label}.sha256 缺失")
        return
    actual_sha = _sha256(resolved)
    if actual_sha != expected_sha:
        failures.append(f"{owner}: {label}.sha256 不匹配：{path}")


def _resolve_inside_base(base: Path, relative: str) -> Path | None:
    candidate = (base / relative).resolve(strict=False)
    base_resolved = base.resolve(strict=False)
    try:
        candidate.relative_to(base_resolved)
    except ValueError:
        return None
    return candidate


def _formal_run_dirs(root: Path) -> list[Path]:
    run_dirs = []
    for child in sorted((root / "run_task_runs").iterdir()):
        if not child.is_dir() or not (child / "run_status.json").exists():
            continue
        status = _read_json(child / "run_status.json").get("status")
        if status != "FINALIZED":
            raise ConfigError(f"formal run 尚未 FINALIZED，不能纳入 evidence ledger：{child} status={status}")
        run_dirs.append(child)
    return run_dirs


def _discarded_attempts_by_task(root: Path, task_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
    discarded_root = root / "discarded_runs"
    result: dict[str, list[dict[str, Any]]] = {task_id: [] for task_id in task_ids}
    if not discarded_root.is_dir():
        return result
    for run_dir in sorted(child for child in discarded_root.iterdir() if child.is_dir()):
        task_id = next((candidate for candidate in task_ids if candidate in run_dir.name), None)
        if task_id is None:
            continue
        reason = _discard_reason(run_dir.name, task_id)
        status = _read_json_if_exists(run_dir / "run_status.json")
        metrics = _read_json_if_exists(run_dir / "metrics.json")
        result[task_id].append(
            {
                "run_dir": _relative(root, run_dir),
                "discard_reason": reason,
                "excluded_from_denominator": True,
                "observed_run_status": status.get("status"),
                "observed_run_outcome": metrics.get("run_outcome"),
                "observed_final_verifier_status": metrics.get("final_verifier_status"),
            }
        )
    return result


def _discard_reason(run_name: str, task_id: str) -> str | None:
    index = run_name.find(task_id)
    if index < 0:
        return None
    suffix = run_name[index + len(task_id) :].strip("_")
    markers = ("deepseek_deepseek-v4-pro", "deepseek_v4_pro", "openai")
    for marker in markers:
        if suffix.startswith(marker):
            suffix = suffix[len(marker) :].strip("_")
            break
    return suffix or None


def _export_summary(run_dir: Path) -> dict[str, Any]:
    export_dirs = sorted(
        child
        for child in (run_dir / "exports").glob("*")
        if child.is_dir() and (child / "export_manifest.json").exists()
    )
    statuses: list[str] = []
    formats: list[str] = []
    trainable = 0
    invalid = 0
    skipped = 0
    diagnostic_only = 0
    export_refs = []
    for export_dir in export_dirs:
        manifest = _read_json_if_exists(export_dir / "export_manifest.json")
        audit = _read_json_if_exists(export_dir / "audit_report.json")
        status = _text(audit.get("status")) or "missing"
        statuses.append(status)
        fmt = _text(manifest.get("format")) or _text(audit.get("format")) or "unknown"
        formats.append(fmt)
        summary = audit.get("summary") if isinstance(audit.get("summary"), dict) else {}
        trainable += int(summary.get("trainable_count") or manifest.get("included_count") or 0)
        invalid += int(summary.get("invalid_count") or manifest.get("invalid_count") or 0)
        skipped += int(summary.get("skipped_count") or manifest.get("skipped_count") or 0)
        diagnostic_only += int(
            summary.get("diagnostic_only_count") or manifest.get("diagnostic_only_count") or 0
        )
        export_refs.append(_file_ref(run_dir, export_dir / "export_manifest.json"))
    return {
        "status": _aggregate_export_status(statuses),
        "formats": sorted(set(formats)),
        "export_dir_count": len(export_dirs),
        "trainable_count": trainable,
        "invalid_count": invalid,
        "skipped_count": skipped,
        "diagnostic_only_count": diagnostic_only,
        "export_manifest_refs": export_refs,
    }


def _aggregate_export_status(statuses: list[str]) -> str:
    if not statuses:
        return "not_generated"
    if any(status == "failed" for status in statuses):
        return "failed"
    if any(status == "passed_with_warnings" for status in statuses):
        return "passed_with_warnings"
    if all(status == "passed" for status in statuses):
        return "passed"
    return "unknown"


def _compaction_counts(events: list[dict[str, Any]]) -> dict[str, int]:
    l0_ids: set[str] = set()
    microcompact = 0
    for event in events:
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        if event.get("event_type") == "context_prepared":
            reduction = data.get("context_reduction") if isinstance(data.get("context_reduction"), dict) else {}
            for tool_result_id in reduction.get("replaced_tool_result_ids") or []:
                if isinstance(tool_result_id, str):
                    l0_ids.add(tool_result_id)
            if reduction.get("microcompact_applied") is True:
                microcompact += 1
        if event.get("event_type") == "tool_completed":
            typed = data.get("typed") if isinstance(data.get("typed"), dict) else {}
            if typed.get("single_tool_result_persisted") is True:
                tool_result_id = data.get("tool_result_id") or typed.get("tool_result_id")
                if isinstance(tool_result_id, str):
                    l0_ids.add(tool_result_id)
    return {
        "l0_persistence": len(l0_ids),
        "microcompact": microcompact,
        "auto_compact": sum(1 for event in events if event.get("event_type") == "auto_compact_applied"),
        "reactive_compact": sum(1 for event in events if event.get("event_type") == "reactive_compact_applied"),
        "ptl_truncation": sum(1 for event in events if event.get("event_type") == "ptl_truncation_applied"),
    }


def _no_progress_signals(events: list[dict[str, Any]], metadata: dict[str, Any]) -> dict[str, Any]:
    diagnostics = [
        event for event in events if event.get("event_type") == "loop_progress_diagnostic"
    ]
    nudge_events = [
        event for event in events if event.get("event_type") == "convergence_nudge_injected"
    ]
    max_read_only = 0
    patch_tool_call_count = 0
    signal_keys: set[str] = set()
    for event in diagnostics:
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        max_read_only = max(max_read_only, int(data.get("consecutive_read_only_tool_calls") or 0))
        patch_tool_call_count = max(patch_tool_call_count, int(data.get("patch_tool_call_count") or 0))
        for signal in data.get("signals") or []:
            if isinstance(signal, dict) and isinstance(signal.get("signal_key"), str):
                signal_keys.add(signal["signal_key"])
    ignored = False
    for item in metadata.get("failure_diagnostics") or []:
        if not isinstance(item, dict):
            continue
        details = item.get("details") if isinstance(item.get("details"), dict) else {}
        subtypes = details.get("diagnostic_subtypes") or []
        if "nudge_ignored_empty_patch" in subtypes:
            ignored = True
        summary = details.get("convergence_nudge_summary")
        if isinstance(summary, dict) and summary.get("post_latest_nudge_action") == "no_observed_action_after_nudge":
            ignored = True
    return {
        "no_progress_suspected": bool(diagnostics),
        "consecutive_read_only_tool_calls": max_read_only,
        "convergence_nudge_count": len(nudge_events),
        "convergence_nudge_ignored": ignored,
        "patch_tool_call_count": patch_tool_call_count,
        "signal_keys": sorted(signal_keys),
    }


def _formal_result(
    metrics: dict[str, Any],
    boundary: dict[str, Any],
    reward: dict[str, Any],
) -> str:
    outcome = _text(metrics.get("run_outcome"))
    if outcome in {"success", "failed", "inconclusive"}:
        return outcome
    if boundary.get("accepted") is True:
        return "success"
    if boundary.get("final_verifier_status") == "rejected":
        return "failed"
    if reward.get("invalid_for_training") is True:
        return "inconclusive"
    return "inconclusive"


def _failure_category(
    boundary: dict[str, Any],
    metadata: dict[str, Any],
    reward: dict[str, Any],
    formal_result: str,
) -> str | None:
    if formal_result == "success":
        return None
    boundary_category = _text(boundary.get("failure_category"))
    if boundary_category:
        return boundary_category
    for item in metadata.get("failure_diagnostics") or []:
        if isinstance(item, dict):
            failure_type = _text(item.get("failure_type"))
            if failure_type:
                return failure_type
    return _text(reward.get("invalid_reason"))


def _config_revision(facts: dict[str, Any], config_path: Path | None) -> str:
    explicit = _text(facts.get("config_revision"))
    if explicit:
        return explicit
    max_tokens = facts.get("max_output_tokens")
    if max_tokens is None and config_path is not None:
        try:
            import yaml

            raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            max_tokens = ((raw.get("model") or {}).get("max_output_tokens"))
        except Exception:
            max_tokens = None
    if isinstance(max_tokens, int) and max_tokens >= 32768:
        return "dev23_config_r1"
    if isinstance(max_tokens, int):
        return "dev23_config_r0"
    return "unknown"


def _config_revision_reason(config_revision: str) -> str | None:
    if config_revision == "dev23_config_r0":
        return "初始 dev23 配置，DeepSeek thinking 输出预算为 8192，后来由 task 014 暴露输出预算不足风险。"
    if config_revision == "dev23_config_r1":
        return "修订后 dev23 配置，DeepSeek thinking 输出预算和主输出预留提升到 32768。"
    return None


def _preflight_difference_acknowledged(
    config_revision: str,
    preflight_status: str,
    failures: list[str],
) -> bool:
    if preflight_status == "passed":
        return True
    if config_revision != "dev23_config_r0" or not failures:
        return False
    return all("model.max_output_tokens>=32768" in failure for failure in failures)


def _timeout_policy_version(facts: dict[str, Any]) -> str:
    return _text(facts.get("provider_timeout_policy")) or PROVIDER_TIMEOUT_POLICY_VERSION


def _config_revision_summary(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[str]] = {}
    for entry in entries:
        grouped.setdefault(str(entry.get("config_revision") or "unknown"), []).append(str(entry.get("task_id")))
    return [
        {
            "config_revision": revision,
            "task_ids": task_ids,
            "task_count": len(task_ids),
            "reason": _config_revision_reason(revision),
        }
        for revision, task_ids in sorted(grouped.items())
    ]


def _config_path(root: Path, task_id: str) -> Path | None:
    candidates = sorted((root / "run_configs").glob(f"{task_id}_*.yaml"))
    return candidates[0] if candidates else None


def _task_definition_path(root: Path, task_id: str) -> Path | None:
    path = root / "task_definitions" / f"{task_id}.yaml"
    return path if path.exists() else None


def _task_id_from_task_yaml(run_dir: Path) -> str | None:
    path = run_dir / "task.yaml"
    if not path.exists():
        return None
    try:
        import yaml

        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return None
    return _text(payload.get("id"))


def _task_order(root: Path) -> list[str]:
    path = root / "analysis" / "dev23_task_order.txt"
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _task_sort_key(task_id: str, task_order: list[str]) -> tuple[int, str]:
    try:
        return (task_order.index(task_id), task_id)
    except ValueError:
        return (len(task_order), task_id)


def _issue_sections(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    matches = list(re.finditer(r"^###\s+\d+\.\s+`([^`]+)`\s*$", text, flags=re.MULTILINE))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1)] = text[start:end]
    return sections


def _harness_issue_refs(section: str, metadata: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    lowered = section.lower()
    if "harness issue found and fixed" in lowered or "harness issue" in lowered:
        refs.append("issue_log:harness_issue_found")
    if "harness observation" in lowered:
        refs.append("issue_log:harness_observation")
    for item in metadata.get("failure_diagnostics") or []:
        if isinstance(item, dict) and item.get("source_component") not in {None, "final_verifier"}:
            refs.append(f"failure_diagnostics:{item.get('source_component')}:{item.get('failure_type')}")
    return sorted(set(refs))


def _fix_commit_refs(section: str) -> list[str]:
    commits = re.findall(r"`([0-9a-f]{7,40})\s+fix:[^`]+`", section)
    commits.extend(re.findall(r"commit\s+`?([0-9a-f]{7,40})", section, flags=re.IGNORECASE))
    return sorted(set(commits))


def _baseline_id(root: Path) -> str:
    name = root.name
    if name.endswith("Z") and "-" in name:
        name = re.sub(r"-\d{8}T\d{6}Z$", "", name)
    return name.replace("-", "_")


def _relative(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _file_ref(root: Path, path: Path) -> dict[str, Any]:
    return {
        "path": _relative(root, path),
        "sha256": _sha256(path) if path.exists() and path.is_file() else None,
    }


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        raise ConfigError(f"JSON 文件不可读：{path}") from exc
    if not isinstance(payload, dict):
        raise ConfigError(f"JSON 文件必须是对象：{path}")
    return payload


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return _read_json(path)


def _read_jsonl_if_exists(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ConfigError(f"JSONL 解析失败：{path}:{line_number}") from exc
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


__all__ = [
    "DEV23_EXPECTED_FORMAL_DENOMINATOR",
    "DEV23_EXPECTED_RESULT_COUNTS",
    "PRE_VERL_EVIDENCE_LEDGER_SCHEMA_VERSION",
    "build_pre_verl_evidence_ledger",
    "inspect_pre_verl_evidence_ledger",
]
