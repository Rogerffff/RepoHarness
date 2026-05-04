"""V4 final acceptance builders and bundle evidence."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from repo_harness import __version__
from repo_harness.errors import ConfigError
from repo_harness.export.manifest import sha256_file
from repo_harness.schema_versions import (
    V4_ACCEPTANCE_BUNDLE_MANIFEST_VERSION,
    V4_ACCEPTANCE_INPUTS_VERSION,
    V4_ACCEPTANCE_REPORT_VERSION,
    V4_ARTIFACT_INSPECT_TRACKING_TABLE_VERSION,
    V4_COMMAND_LOG_ENTRY_SCHEMA_VERSION,
    V4_RUN_SELECTION_MANIFEST_VERSION,
)
from repo_harness.v2_acceptance import inspect_v2_acceptance
from repo_harness.v3_acceptance import inspect_acceptance_bundle, inspect_v3_acceptance
from repo_harness.v4_agent_run import inspect_v4_agent_run_integration, inspect_v4_trajectory_store
from repo_harness.v4_cards import inspect_v4_cards
from repo_harness.v4_export_quality import inspect_v4_export_quality
from repo_harness.v4_rollout import (
    inspect_resource_locks,
    inspect_resource_usage,
    inspect_rollout_budget,
    inspect_rollout_leases,
    inspect_rollout_queue,
    inspect_rollout_resume,
    inspect_rollout_retry,
    inspect_run_selection_query,
)
from repo_harness.v4_stage1 import (
    V4_REQUIRED_FINAL_ACCEPTANCE_ROLES,
    build_artifact_inspect_tracking_table_payload,
    inspect_v4_artifact_set,
    inspect_v4_inputs,
)
from repo_harness.v4_task_freeze import inspect_v4_task_freeze, inspect_v4_task_validity
from repo_harness.v4_tool_lifecycle import inspect_v4_tool_contract, inspect_v4_tool_lifecycle
from repo_harness.workspace.source_hash import compute_source_tree_hash


V4_RUN_SELECTION_QUERY_SPEC_VERSION = "repo_harness_v4_run_selection_query_spec_v0"
V4_ACCEPTANCE_INPUT_BUILD_INPUTS: tuple[str, ...] = (
    "run_selection",
    "v2_acceptance",
    "v3_acceptance",
    "v3_acceptance_bundle",
    "implementation_inputs",
    "rollout_queue",
    "lease_state",
    "retry_policy",
    "budget_control",
    "resource_locks",
    "resource_usage",
    "batch_resume",
    "run_selection_query",
    "task_freeze",
    "task_validity",
    "tool_contract",
    "tool_lifecycle",
    "agent_run_integration",
    "trajectory_store",
    "export_quality",
    "cards",
    "contamination_scan",
    "command_log",
)


def build_v4_run_selection_manifest(
    *,
    query: str | Path,
    output: str | Path,
    fail_if_output_exists: bool = True,
) -> Path:
    """Build an explicit V4 run selection manifest from a frozen query spec."""

    query_path = Path(query)
    output_path = Path(output)
    if fail_if_output_exists and output_path.exists():
        raise ConfigError(f"run_selection_manifest 输出已存在：{output_path}")
    payload = _read_json(query_path)
    if payload.get("schema_version") != V4_RUN_SELECTION_QUERY_SPEC_VERSION:
        raise ConfigError("V4 query spec schema_version 不匹配。")
    if payload.get("selection_mode") != "explicit":
        raise ConfigError("V4 query spec 必须使用 explicit selection_mode。")
    if payload.get("latest_run_auto_selection") is not False:
        raise ConfigError("V4 query spec 禁止 latest run 自动选择。")
    if not payload.get("query_predicate"):
        raise ConfigError("V4 query spec 缺少 query_predicate。")
    if not payload.get("input_manifest_hash"):
        raise ConfigError("V4 query spec 缺少 input_manifest_hash。")
    entries = payload.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ConfigError("V4 query spec entries 必须是非空列表。")
    normalized_entries: list[dict[str, Any]] = []
    seen_roles: set[str] = set()
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            raise ConfigError(f"V4 query spec entries[{index}] 不是 object。")
        role = str(entry.get("role") or "")
        if not role:
            raise ConfigError(f"V4 query spec entries[{index}] 缺少 role。")
        if role in seen_roles:
            raise ConfigError(f"V4 query spec role 重复：{role}")
        seen_roles.add(role)
        run_ref = str(entry.get("run_ref") or entry.get("path") or "")
        if not run_ref:
            raise ConfigError(f"V4 query spec entries[{index}] 缺少 run_ref。")
        if _looks_like_report_artifact(run_ref):
            raise ConfigError("run_selection_manifest 只允许 selected run refs，不允许报告类产物：" + run_ref)
        run_path = Path(run_ref)
        if not run_path.is_absolute():
            run_path = Path.cwd() / run_path
        if not run_path.exists():
            raise ConfigError(f"run_selection_manifest selected run ref 不存在：{run_ref}")
        normalized_entries.append(
            {
                "entry_id": f"v4-run-selection-{index:03d}",
                "role": role,
                "run_ref": _relative_path(run_path, Path.cwd()),
                "role_ref": entry.get("role_ref") or role,
                "selection_reason": entry.get("selection_reason") or "explicit Stage 8 query selection",
            }
        )
    missing_roles = sorted(set(V4_REQUIRED_FINAL_ACCEPTANCE_ROLES).difference(seen_roles))
    if missing_roles:
        raise ConfigError("run_selection_manifest 缺少必需 role：" + ", ".join(missing_roles))
    manifest = {
        "schema_version": V4_RUN_SELECTION_MANIFEST_VERSION,
        "generated_at": _utc_timestamp(),
        "selection_mode": "explicit",
        "latest_run_auto_selection": False,
        "query_spec_ref": _file_ref(query_path, category="v4_run_selection_query_spec"),
        "query_predicate": payload["query_predicate"],
        "input_manifest_hash": payload["input_manifest_hash"],
        "entries": normalized_entries,
        "role_counts": {
            role: sum(1 for entry in normalized_entries if entry["role"] == role)
            for role in sorted(seen_roles)
        },
    }
    _write_json(output_path, manifest)
    return output_path


def build_v4_acceptance_inputs(
    *,
    output: str | Path,
    pre_acceptance_docs: list[str | Path],
    fail_if_output_exists: bool = True,
    **inputs: str | Path,
) -> Path:
    """Build explicit V4 acceptance inputs from stage machine artifacts."""

    output_path = Path(output)
    if fail_if_output_exists and output_path.exists():
        raise ConfigError(f"v4_acceptance_inputs 输出已存在：{output_path}")
    if not pre_acceptance_docs:
        raise ConfigError("至少需要一个 --pre-acceptance-doc。")
    missing = [name for name in V4_ACCEPTANCE_INPUT_BUILD_INPUTS if name not in inputs or inputs[name] is None]
    if missing:
        raise ConfigError("build-v4-acceptance-inputs 缺少输入：" + ", ".join(missing))
    refs_by_category: dict[str, list[dict[str, Any]]] = {
        "run_selection_manifest": [_file_ref(Path(inputs["run_selection"]), category="run_selection_manifest")],
        "v2_acceptance": [_file_ref(Path(inputs["v2_acceptance"]), category="v2_acceptance")],
        "v3_acceptance": [_file_ref(Path(inputs["v3_acceptance"]), category="v3_acceptance")],
        "v3_acceptance_bundle": [_file_ref(Path(inputs["v3_acceptance_bundle"]), category="v3_acceptance_bundle")],
        "implementation_inputs": [_file_ref(Path(inputs["implementation_inputs"]), category="implementation_inputs")],
        "rollout_queue": [_file_ref(_normalize_dir(inputs["rollout_queue"]), category="rollout_queue")],
        "lease_state": [_file_ref(_normalize_dir(inputs["lease_state"]), category="lease_state")],
        "retry_policy": [_file_ref(_normalize_dir(inputs["retry_policy"]), category="retry_policy")],
        "budget_control": [_file_ref(_normalize_dir(inputs["budget_control"]), category="budget_control")],
        "resource_locks": [_file_ref(_normalize_dir(inputs["resource_locks"]), category="resource_locks")],
        "resource_usage": [_file_ref(_normalize_dir(inputs["resource_usage"]), category="resource_usage")],
        "batch_resume": [_file_ref(_normalize_dir(inputs["batch_resume"]), category="batch_resume")],
        "run_selection_query": [_file_ref(Path(inputs["run_selection_query"]), category="run_selection_query")],
        "task_freeze": [_file_ref(Path(inputs["task_freeze"]), category="task_freeze")],
        "task_validity": [_file_ref(Path(inputs["task_validity"]), category="task_validity")],
        "tool_contract": [_file_ref(_normalize_dir(inputs["tool_contract"]), category="tool_contract")],
        "tool_lifecycle": [_file_ref(_normalize_dir(inputs["tool_lifecycle"]), category="tool_lifecycle")],
        "agent_run_integration": [_file_ref(_normalize_dir(inputs["agent_run_integration"]), category="agent_run_integration")],
        "trajectory_store": [_file_ref(_normalize_dir(inputs["trajectory_store"]), category="trajectory_store")],
        "export_quality": [_file_ref(_normalize_dir(inputs["export_quality"]), category="export_quality")],
        "cards": [_file_ref(_normalize_dir(inputs["cards"]), category="cards")],
        "contamination_scan": [_file_ref(Path(inputs["contamination_scan"]), category="contamination_scan")],
        "command_log": [_file_ref(Path(inputs["command_log"]), category="command_log")],
        "pre_acceptance_docs": [
            _file_ref(Path(doc), category="pre_acceptance_docs")
            for doc in pre_acceptance_docs
        ],
    }
    tracking_table_path = Path("docs/v4/evidence/schema-and-inspect/artifact_inspect_tracking_table.json")
    manifest = {
        "schema_version": V4_ACCEPTANCE_INPUTS_VERSION,
        "generated_at": _utc_timestamp(),
        "selection_mode": "explicit",
        "latest_run_auto_selection": False,
        "required_categories": list(refs_by_category),
        "input_refs_by_category": refs_by_category,
        "run_selection_manifest_ref": refs_by_category["run_selection_manifest"][0],
        "artifact_inspect_tracking_table_ref": _file_ref(tracking_table_path, category="artifact_inspect_tracking_table"),
        "command_log_ref": refs_by_category["command_log"][0],
        "pre_acceptance_doc_refs": refs_by_category["pre_acceptance_docs"],
        "acceptance_policy": {
            "fresh_acceptance_directory_required": True,
            "no_latest_run_discovery": True,
            "explicit_sha256_binding": True,
            "final_verifier_authority_required": True,
        },
    }
    _write_json(output_path, manifest)
    inspect_v4_inputs(output_path, assert_complete=True)
    return output_path


def build_v4_acceptance_report(
    *,
    acceptance_inputs: str | Path,
    output: str | Path,
    fail_if_output_exists: bool = True,
) -> Path:
    """Build a fresh V4 final acceptance report from explicit inputs."""

    started_at = _utc_timestamp()
    input_path = Path(acceptance_inputs)
    output_path = Path(output)
    acceptance_dir = output_path.parent
    if fail_if_output_exists and (acceptance_dir.exists() or output_path.exists()):
        raise ConfigError(f"V4 acceptance output 已存在，不能覆盖旧 evidence：{acceptance_dir}")
    if output_path.exists():
        raise ConfigError(f"v4_acceptance_report 已存在：{output_path}")
    command_log_path = acceptance_dir / "acceptance_command_log.jsonl"
    if command_log_path.exists():
        raise ConfigError(f"acceptance_command_log 已存在：{command_log_path}")
    inspect_v4_inputs(input_path, assert_complete=True)
    input_payload = _read_json(input_path)
    refs = input_payload["input_refs_by_category"]
    role_statuses, role_evidence, checks = _run_final_acceptance_checks(refs)
    task_freeze_payload = _read_json(_path_from_ref(refs["task_freeze"][0]))
    accepted_count = int(task_freeze_payload.get("accepted_auditable_task_definition_count", 0))
    pr_issue_count = int(task_freeze_payload.get("pr_issue_accepted_auditable_task_definition_count", 0))
    failures: list[str] = []
    if accepted_count < 8:
        failures.append("accepted / auditable task definitions 少于 8。")
    if pr_issue_count < 4:
        failures.append("V4 PR / issue accepted / auditable task definitions 少于 4。")
    missing_roles = [role for role in V4_REQUIRED_FINAL_ACCEPTANCE_ROLES if role_statuses.get(role) != "passed"]
    if missing_roles:
        failures.append("final acceptance role 未通过：" + ", ".join(missing_roles))
    acceptance_dir.mkdir(parents=True, exist_ok=False)
    command_log_source = _path_from_ref(refs["command_log"][0])
    shutil.copyfile(command_log_source, command_log_path)
    _append_command_log(
        command_log_path,
        command_name="build-v4-acceptance-report",
        argv=[
            "repo-harness",
            "build-v4-acceptance-report",
            "--acceptance-inputs",
            input_path.as_posix(),
            "--output",
            output_path.as_posix(),
            "--fail-if-output-exists",
        ],
        started_at=started_at,
        input_paths=[input_path],
        output_paths=[],
        self_referential_output_paths=[output_path, command_log_path],
        self_referential_output_reason=(
            "v4_acceptance_report.json binds acceptance_command_log.jsonl; recording the "
            "report or command log sha256 inside the same command log entry would create a "
            "hash cycle. Both files are verified directly by inspect-v4-acceptance and "
            "acceptance bundle inspect."
        ),
        exit_code=0,
    )
    report = {
        "schema_version": V4_ACCEPTANCE_REPORT_VERSION,
        "acceptance_id": acceptance_dir.parent.name,
        "generated_at": _utc_timestamp(),
        "status": "failed" if failures else "passed",
        "acceptance_inputs_ref": _file_ref(input_path, category="v4_acceptance_inputs"),
        "acceptance_command_log_ref": _file_ref(command_log_path, category="acceptance_command_log"),
        "role_statuses": role_statuses,
        "role_evidence_refs": role_evidence,
        "checks": checks,
        "accepted_auditable_task_definition_count": accepted_count,
        "pr_issue_accepted_auditable_task_definition_count": pr_issue_count,
        "final_verifier_authority_preserved": True,
        "trainable_payload_contamination_status": "clean",
        "evaluator_only_evidence_model_visible": False,
        "run_selection_manifest_explicit_and_immutable": True,
        "acceptance_inputs_explicit_and_immutable": True,
        "failures": failures,
    }
    _write_json(output_path, report)
    return output_path


def build_v4_acceptance_bundle(
    *,
    acceptance_report: str | Path,
    output: str | Path,
    documentation_refs: list[str | Path],
    fail_if_output_exists: bool = True,
) -> Path:
    """Bind V4 final acceptance report, command log, inputs, and post docs."""

    report_path = Path(acceptance_report)
    output_path = Path(output)
    if fail_if_output_exists and output_path.exists():
        raise ConfigError(f"V4 acceptance bundle 已存在：{output_path}")
    if not documentation_refs:
        raise ConfigError("至少需要一个 --documentation-ref。")
    if output_path.parent.resolve() != report_path.parent.resolve():
        raise ConfigError("V4 acceptance bundle output 必须与 acceptance report 位于同一 acceptance directory。")
    from repo_harness.v4_stage1 import inspect_v4_acceptance

    inspect_v4_acceptance(report_path, assert_complete=True)
    report_payload = _read_json(report_path)
    input_ref = report_payload["acceptance_inputs_ref"]
    command_log_ref = report_payload["acceptance_command_log_ref"]
    manifest = {
        "schema_version": V4_ACCEPTANCE_BUNDLE_MANIFEST_VERSION,
        "generated_at": _utc_timestamp(),
        "acceptance_dir_ref": {
            "path": _relative_path(report_path.parent, Path.cwd()),
            "kind": "directory",
            "category": "acceptance_dir",
            "hash_policy": "not_hashed_to_avoid_self_referential_bundle_manifest",
        },
        "acceptance_report_ref": _file_ref(report_path, category="v4_acceptance_report"),
        "acceptance_inputs_ref": input_ref,
        "acceptance_command_log_ref": command_log_ref,
        "documentation_refs": [
            _file_ref(Path(doc), category="post_acceptance_documentation")
            for doc in documentation_refs
        ],
        "bundle_policy": {
            "post_acceptance_docs_not_report_inputs": True,
            "inspect_rechecks_v4_acceptance_report": True,
            "no_latest_run_discovery": True,
            "explicit_sha256_binding": True,
        },
    }
    _write_json(output_path, manifest)
    return output_path


def _run_final_acceptance_checks(refs: dict[str, list[dict[str, Any]]]) -> tuple[dict[str, str], dict[str, Any], list[str]]:
    checks: list[str] = []
    evidence: dict[str, Any] = {}
    statuses = {role: "passed" for role in V4_REQUIRED_FINAL_ACCEPTANCE_ROLES}
    inspect_v2_acceptance(_path_from_ref(refs["v2_acceptance"][0]), assert_complete=True)
    checks.append("v2_regression_passed")
    evidence["v2_regression"] = refs["v2_acceptance"][0]
    inspect_v3_acceptance(_path_from_ref(refs["v3_acceptance"][0]), assert_complete=True)
    checks.append("v3_acceptance_passed")
    evidence["v3_regression"] = refs["v3_acceptance"][0]
    inspect_acceptance_bundle(_path_from_ref(refs["v3_acceptance_bundle"][0]), assert_immutable=True)
    checks.append("v3_acceptance_bundle_immutable")
    inspect_v4_task_freeze(_path_from_ref(refs["task_freeze"][0]), assert_complete=True)
    inspect_v4_task_validity(_path_from_ref(refs["task_validity"][0]), assert_complete=True)
    evidence["v4_pr_issue_task_freeze"] = refs["task_freeze"][0]
    evidence["v4_swebench_like_task_freeze"] = refs["task_validity"][0]
    evidence["real_repository_regression"] = refs["task_freeze"][0]
    evidence["swebench_like_regression"] = refs["task_validity"][0]
    checks.append("v4_task_freeze_and_validity_passed")
    rollout_dir = _path_from_ref(refs["rollout_queue"][0])
    inspect_rollout_queue(rollout_dir, assert_complete=True)
    inspect_rollout_leases(_path_from_ref(refs["lease_state"][0]), assert_complete=True)
    inspect_rollout_retry(_path_from_ref(refs["retry_policy"][0]), assert_complete=True)
    inspect_rollout_budget(_path_from_ref(refs["budget_control"][0]), assert_complete=True)
    inspect_resource_locks(_path_from_ref(refs["resource_locks"][0]), assert_complete=True)
    inspect_resource_usage(_path_from_ref(refs["resource_usage"][0]), assert_complete=True)
    inspect_rollout_resume(_path_from_ref(refs["batch_resume"][0]), assert_complete=True)
    inspect_run_selection_query(_path_from_ref(refs["run_selection_query"][0]), assert_complete=True)
    evidence["v4_rollout_orchestration"] = refs["rollout_queue"][0]
    evidence["v4_rollout_resume"] = refs["batch_resume"][0]
    checks.append("v4_rollout_orchestration_passed")
    inspect_v4_tool_contract(_path_from_ref(refs["tool_contract"][0]), assert_frozen=True)
    inspect_v4_tool_lifecycle(_path_from_ref(refs["tool_lifecycle"][0]), assert_complete=True)
    evidence["v4_tool_lifecycle_audit"] = refs["tool_lifecycle"][0]
    checks.append("v4_tool_lifecycle_passed")
    inspect_v4_agent_run_integration(_path_from_ref(refs["agent_run_integration"][0]), assert_complete=True)
    inspect_v4_trajectory_store(_path_from_ref(refs["trajectory_store"][0]), assert_readable=True)
    evidence["v4_agent_run_integration"] = refs["agent_run_integration"][0]
    checks.append("v4_agent_run_integration_passed")
    inspect_v4_export_quality(_path_from_ref(refs["export_quality"][0]), assert_complete=True)
    evidence["v4_export_quality"] = refs["export_quality"][0]
    checks.append("v4_export_quality_passed")
    inspect_v4_cards(_path_from_ref(refs["cards"][0]), assert_complete=True)
    inspect_v4_artifact_set("contamination_scan", _path_from_ref(refs["contamination_scan"][0]), assert_complete=True)
    evidence["v4_cards"] = refs["cards"][0]
    checks.append("v4_cards_and_contamination_scan_passed")
    return statuses, evidence, checks


def _append_command_log(
    path: Path,
    *,
    command_name: str,
    argv: list[str],
    started_at: str,
    input_paths: list[Path],
    output_paths: list[Path],
    exit_code: int,
    self_referential_output_paths: list[Path] | None = None,
    self_referential_output_reason: str | None = None,
) -> None:
    entry = {
        "schema_version": V4_COMMAND_LOG_ENTRY_SCHEMA_VERSION,
        "command_name": command_name,
        "argv": argv,
        "cwd": Path.cwd().as_posix(),
        "input_refs": [
            _artifact_ref(item, artifact_id=f"{command_name}_input_{index}")
            for index, item in enumerate(input_paths, start=1)
            if item.exists()
        ],
        "output_refs": [
            _artifact_ref(item, artifact_id=f"{command_name}_output_{index}")
            for index, item in enumerate(output_paths, start=1)
            if item.exists()
        ],
        "self_referential_output_paths": [
            _relative_path(item, Path.cwd())
            for item in (self_referential_output_paths or [])
        ],
        "self_referential_output_reason": self_referential_output_reason,
        "exit_code": exit_code,
        "tool_or_cli_version": f"repo-harness {__version__}",
        "started_at": started_at,
        "finished_at": _utc_timestamp(),
        "structured_skip_reason": None,
        "structured_failure_reason": None,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")


def _file_ref(path: Path, *, category: str) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"输入路径不存在：{path}")
    return {
        "path": _relative_path(path, Path.cwd()),
        "kind": _kind_for_path(path),
        "category": category,
        "sha256": _hash_path(path),
        "size_bytes": 0 if path.is_dir() else path.stat().st_size,
    }


def _artifact_ref(path: Path, *, artifact_id: str) -> dict[str, Any]:
    return {
        "artifact_id": artifact_id,
        "relative_path": _relative_path(path, Path.cwd()),
        "kind": _kind_for_path(path),
        "sha256": _hash_path(path),
        "size_bytes": 0 if path.is_dir() else path.stat().st_size,
        "redaction_status": "not_required",
        "retention_policy": "keep",
    }


def _path_from_ref(ref: dict[str, Any]) -> Path:
    path = Path(str(ref.get("path") or ref.get("relative_path") or ""))
    return path if path.is_absolute() else Path.cwd() / path


def _normalize_dir(path: str | Path) -> Path:
    target = Path(path)
    if target.is_file():
        return target.parent
    return target


def _hash_path(path: Path) -> str:
    return compute_source_tree_hash(path) if path.is_dir() else sha256_file(path)


def _kind_for_path(path: Path) -> str:
    if path.is_dir():
        return "directory"
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        return "jsonl"
    if suffix == ".json":
        return "json"
    if suffix == ".md":
        return "markdown"
    return suffix.lstrip(".") or "file"


def _relative_path(path: Path, base_dir: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(base_dir.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def _looks_like_report_artifact(path: str) -> bool:
    lowered = path.lower()
    return (
        lowered.endswith(".json")
        or lowered.endswith(".jsonl")
        or lowered.endswith(".md")
        or "_report" in lowered
        or "manifest" in lowered
    )


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"JSON 输入不存在：{path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"JSON 输入无法解析：{path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ConfigError(f"JSON 顶层必须是 object：{path}")
    return payload


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
