#!/usr/bin/env python
"""Scan pre-verl development runs for known DEV23 issue patterns."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SLOW_SYMBOL_SEARCH_MS = 5000
WIDE_SYMBOL_SEARCH_CANDIDATE_THRESHOLD = 120
STATUS_PREFIXES = ("FAILED ", "ERROR ", "PASSED ", "SKIPPED ", "XFAIL ", "XPASS ")
ENVIRONMENT_IMPORT_ERROR_MARKERS = (
    "cannot open shared object file",
    "libgl.so.1",
    "libegl.so",
    "libosmesa",
    "libxrender.so",
    "libxext.so",
    "libsm.so",
    "shared library",
    "dlopen",
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan a pre-verl AgentLoop run directory for DEV23 remediation issue patterns."
    )
    parser.add_argument("run_dir", help="pre-verl AgentLoop run directory containing run_task_runs/")
    parser.add_argument("--fail-on-issues", action="store_true")
    args = parser.parse_args()

    report = scan_run_dir(Path(args.run_dir))
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    if args.fail_on_issues and report["summary"]["issue_count"] > 0:
        return 1
    return 0


def scan_run_dir(run_dir: Path) -> dict[str, Any]:
    run_task_root = run_dir / "run_task_runs"
    issues: list[dict[str, Any]] = []
    if not run_task_root.exists():
        raise SystemExit(f"run_task_runs not found: {run_task_root}")
    for task_run_dir in sorted(path for path in run_task_root.iterdir() if path.is_dir()):
        issues.extend(_scan_final_verifier_result(task_run_dir))
        issues.extend(_scan_symbol_search_events(task_run_dir))
    counts_by_kind: dict[str, int] = {}
    counts_by_task: dict[str, int] = {}
    for issue in issues:
        counts_by_kind[issue["kind"]] = counts_by_kind.get(issue["kind"], 0) + 1
        counts_by_task[issue["task_run_id"]] = counts_by_task.get(issue["task_run_id"], 0) + 1
    return {
        "schema_version": "repo_harness_pre_verl_dev23_issue_scan_v0",
        "run_dir": run_dir.as_posix(),
        "summary": {
            "issue_count": len(issues),
            "counts_by_kind": counts_by_kind,
            "counts_by_task": counts_by_task,
        },
        "issues": issues,
    }


def _scan_final_verifier_result(task_run_dir: Path) -> list[dict[str, Any]]:
    path = task_run_dir / "pre_verl_final_verifier_result.json"
    if not path.exists():
        return []
    payload = _read_json(path)
    issues: list[dict[str, Any]] = []
    for suite in ("fail_to_pass_result", "pass_to_pass_result"):
        result = payload.get(suite) or {}
        if not isinstance(result, dict):
            continue
        suite_name = suite.removesuffix("_result")
        exit_code = result.get("exit_code")
        summary = result.get("summary_counts") or {}
        failed_nodeids = [str(item) for item in result.get("failed_nodeids") or []]
        error_nodeids = [str(item) for item in result.get("error_nodeids") or []]
        failed_count = int(result.get("failed_count") or 0)
        error_count = int(result.get("error_count") or 0)
        if exit_code != 0 and int(summary.get("failed") or 0) > 0 and failed_count == 0:
            issues.append(
                _issue(
                    task_run_dir,
                    kind="failed_summary_without_failed_count",
                    suite=suite_name,
                    details={
                        "exit_code": exit_code,
                        "summary_counts": summary,
                        "failed_count": failed_count,
                        "failed_nodeid_count": len(failed_nodeids),
                    },
                )
            )
        if exit_code != 0 and failed_nodeids and failed_count == 0:
            issues.append(
                _issue(
                    task_run_dir,
                    kind="failed_nodeids_without_failed_count",
                    suite=suite_name,
                    details={
                        "exit_code": exit_code,
                        "failed_count": failed_count,
                        "failed_nodeid_sample": failed_nodeids[:3],
                    },
                )
            )
        if int(summary.get("errors") or 0) > 0 and error_count == 0:
            issues.append(
                _issue(
                    task_run_dir,
                    kind="error_summary_without_error_count",
                    suite=suite_name,
                    details={
                        "exit_code": exit_code,
                        "summary_counts": summary,
                        "error_count": error_count,
                        "error_nodeid_count": len(error_nodeids),
                    },
                )
            )
        if error_nodeids and error_count == 0:
            issues.append(
                _issue(
                    task_run_dir,
                    kind="error_nodeids_without_error_count",
                    suite=suite_name,
                    details={
                        "exit_code": exit_code,
                        "error_count": error_count,
                        "error_nodeid_sample": error_nodeids[:3],
                    },
                )
            )
        prefixed = [
            nodeid
            for nodeid in [*failed_nodeids, *error_nodeids]
            if nodeid.startswith(STATUS_PREFIXES)
        ]
        if prefixed:
            issues.append(
                _issue(
                    task_run_dir,
                    kind="status_prefixed_nodeids",
                    suite=suite_name,
                    details={"nodeid_sample": prefixed[:5]},
                )
            )
        if exit_code == 4:
            missing_output = not _has_split_verifier_output_audit(result)
            if missing_output or not result.get("pytest_exit_reason"):
                issues.append(
                    _issue(
                        task_run_dir,
                        kind="pytest_exit_code_4_missing_output_audit",
                        suite=suite_name,
                        details={
                            "missing_output_audit": missing_output,
                            "pytest_exit_reason": result.get("pytest_exit_reason"),
                            "summary_counts": summary,
                        },
                    )
                )
            combined_output = "\n".join(
                str(result.get(key) or "") for key in ("stdout_preview", "stderr_preview")
            )
            if _looks_like_environment_import_error(combined_output):
                issues.append(
                    _issue(
                        task_run_dir,
                        kind="pytest_exit_code_4_environment_import_error",
                        suite=suite_name,
                        details={"output_preview": combined_output[:500]},
                    )
                )
    return issues


def _scan_symbol_search_events(task_run_dir: Path) -> list[dict[str, Any]]:
    path = task_run_dir / "events.jsonl"
    if not path.exists():
        return []
    issues: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (event.get("event_type") or event.get("type")) != "tool_completed":
            continue
        data = event.get("data") or {}
        if data.get("effective_tool_name") != "symbol_search" and data.get("tool_name") != "symbol_search":
            continue
        typed = data.get("typed") if isinstance(data.get("typed"), dict) else {}
        duration_ms = int(data.get("duration_ms") or typed.get("duration_ms") or typed.get("execution_duration_ms") or 0)
        root = str(
            typed.get("root")
            or (data.get("effective_arguments") or {}).get("root")
            or (data.get("normalized_arguments") or {}).get("root")
            or ""
        )
        candidate_file_count = int(typed.get("candidate_file_count") or 0)
        if duration_ms > SLOW_SYMBOL_SEARCH_MS:
            issues.append(
                _issue(
                    task_run_dir,
                    kind="slow_symbol_search",
                    suite=None,
                    details={
                        "line_number": line_number,
                        "duration_ms": duration_ms,
                        "root": root,
                        "candidate_file_count": candidate_file_count,
                    },
                )
            )
        envelope = typed.get("result_envelope") if isinstance(typed.get("result_envelope"), dict) else {}
        has_recovery = bool(envelope.get("recovery_call") or typed.get("recommended_narrow_roots"))
        result_kind = typed.get("result_kind") or envelope.get("result_kind")
        if root in {"", "."} and candidate_file_count > WIDE_SYMBOL_SEARCH_CANDIDATE_THRESHOLD:
            if not typed.get("slow_scan") and not has_recovery and result_kind != "scan_requires_narrow_root":
                issues.append(
                    _issue(
                        task_run_dir,
                        kind="wide_symbol_search_without_recovery",
                        suite=None,
                        details={
                            "line_number": line_number,
                            "root": root,
                            "candidate_file_count": candidate_file_count,
                            "result_kind": result_kind,
                        },
                    )
                )
    return issues


def _issue(
    task_run_dir: Path,
    *,
    kind: str,
    suite: str | None,
    details: dict[str, Any],
) -> dict[str, Any]:
    issue = {
        "kind": kind,
        "task_run_id": task_run_dir.name,
        "task_run_dir": task_run_dir.as_posix(),
        "details": details,
    }
    if suite is not None:
        issue["suite"] = suite
    return issue


def _looks_like_environment_import_error(text: str) -> bool:
    lowered = text.lower()
    return any(needle in lowered for needle in ENVIRONMENT_IMPORT_ERROR_MARKERS)


def _has_split_verifier_output_audit(result: dict[str, Any]) -> bool:
    return any(
        result.get(key)
        for key in (
            "stdout_ref",
            "stderr_ref",
            "stdout_preview",
            "stderr_preview",
        )
    )


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
