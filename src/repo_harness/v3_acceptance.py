"""V3 acceptance input binding, report, bundle, and read-only inspectors."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, ValidationError, model_validator

from repo_harness import __version__
from repo_harness.errors import ConfigError
from repo_harness.export.manifest import sha256_file
from repo_harness.schema_base import StrictBaseModel
from repo_harness.schema_versions import (
    COMMAND_LOG_ENTRY_SCHEMA_VERSION,
    V3_CONTAMINATION_DENYLIST_VERSION,
    V3_ACCEPTANCE_REPORT_SCHEMA_VERSION,
    V3_VISIBILITY_POLICY_VERSION,
)
from repo_harness.trajectory import ArtifactRef, read_jsonl, verify_artifact_manifest
from repo_harness.v3_visibility import V3ContaminationDenylist, V3_VISIBILITY_SURFACES
from repo_harness.workspace import WorkspaceBackendError, inspect_workspace_backend_status
from repo_harness.workspace.source_hash import compute_source_tree_hash


V3_RUN_SELECTION_MANIFEST_VERSION = "repo_harness_v3_run_selection_manifest_v0"
V3_ACCEPTANCE_INPUTS_VERSION = "repo_harness_v3_acceptance_inputs_v0"
V3_ACCEPTANCE_BUNDLE_MANIFEST_VERSION = "repo_harness_v3_acceptance_bundle_manifest_v0"

V3_REQUIRED_RUN_SELECTION_ROLES = (
    "replay",
    "mock_provider",
    "credential_gated_real_provider",
    "real_repository",
    "swebench_like",
    "resume",
    "context",
    "long_rollout",
    "failure_diagnostics",
)
V3_TRAJECTORY_RUN_ROLES = {
    "replay",
    "mock_provider",
    "credential_gated_real_provider",
    "real_repository",
    "swebench_like",
}
V3_REQUIRED_DOCKER_BACKEND_ROLES = {
    "real_repository",
    "swebench_like",
}
V3_CORE_AGENT_LOOP_ROLES = {
    "real_repository",
    "swebench_like",
}
V3_REQUIRED_ACCEPTANCE_INPUT_CATEGORIES = (
    "run_selection_manifest",
    "export_root",
    "v2_report",
    "pre_acceptance_docs",
    "documentation_manifest",
    "command_log",
    "test_evidence",
)
V3_REQUIRED_PRE_ACCEPTANCE_DOCS = (
    "docs/v3/scope-and-roadmap.md",
    "docs/v3/implementation-plan.md",
    "docs/v3/review/scope-review.md",
    "docs/v3/review/implementation-plan-review.md",
    "docs/v3/review/swe-task-feasibility-results.md",
    "docs/v3/swe-task-feasibility-experiment-plan.md",
)
V3_REQUIRED_TRAJECTORY_FILES = (
    "transcript.jsonl",
    "events.jsonl",
    "artifacts.json",
    "run_config_facts.json",
)
V3_DOCKER_BACKEND_STATUS_FILES = (
    "docker_backend_status.json",
    "docker_stage_status.json",
)


class CommandLogEntry(StrictBaseModel):
    schema_version: str = COMMAND_LOG_ENTRY_SCHEMA_VERSION
    command_name: str
    argv: list[str] = Field(min_length=1)
    cwd: str
    input_refs: list[ArtifactRef] = Field(default_factory=list)
    output_refs: list[ArtifactRef] = Field(default_factory=list)
    self_referential_output_paths: list[str] = Field(default_factory=list)
    self_referential_output_reason: str | None = None
    exit_code: int | None = None
    tool_or_cli_version: str
    started_at: str
    finished_at: str | None = None
    structured_skip_reason: str | None = None
    structured_failure_reason: str | None = None

    @model_validator(mode="after")
    def terminal_entries_need_result(self) -> "CommandLogEntry":
        if self.finished_at and self.exit_code is None and not self.structured_skip_reason:
            raise ValueError("finished command log entry 必须记录 exit_code 或 structured skip reason。")
        if self.self_referential_output_paths and not self.self_referential_output_reason:
            raise ValueError("self-referential output path 必须记录 reason。")
        return self


class V3AcceptanceReport(StrictBaseModel):
    schema_version: str = V3_ACCEPTANCE_REPORT_SCHEMA_VERSION
    acceptance_id: str
    status: Literal["passed", "failed", "blocked"]
    visibility_policy_version: Literal[V3_VISIBILITY_POLICY_VERSION] = V3_VISIBILITY_POLICY_VERSION
    contamination_denylist_version: Literal[V3_CONTAMINATION_DENYLIST_VERSION] = (
        V3_CONTAMINATION_DENYLIST_VERSION
    )
    input_manifest_ref: ArtifactRef
    command_log_ref: ArtifactRef
    run_selection_manifest_ref: ArtifactRef | None = None
    report_generated_at: str
    checks: list[str] = Field(default_factory=list)
    contamination_scan_refs: list[ArtifactRef] = Field(default_factory=list)
    contamination_scan_surfaces: list[str] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def failures_match_status(self) -> "V3AcceptanceReport":
        if self.status == "passed" and self.failures:
            raise ValueError("passed acceptance report 不能包含 failures。")
        if self.status == "passed" and not self.checks:
            raise ValueError("passed acceptance report 必须包含 checks。")
        if self.status == "passed" and not self.contamination_scan_refs:
            raise ValueError("passed acceptance report 必须引用 contamination scan evidence。")
        if self.status == "passed":
            missing_surfaces = sorted(
                set(V3_VISIBILITY_SURFACES).difference(self.contamination_scan_surfaces)
            )
            if missing_surfaces:
                raise ValueError(
                    "passed acceptance report 缺少 contamination scan surfaces："
                    + ", ".join(missing_surfaces)
                )
        if self.status != "passed" and not self.failures:
            raise ValueError("failed / blocked acceptance report 必须包含 failures。")
        return self


def inspect_trajectory_store(
    run_dir: str | Path,
    *,
    assert_readable: bool = False,
) -> str:
    """Read-only V3 trajectory store inspection."""

    run_path = Path(run_dir)
    failures: list[str] = []
    if not run_path.exists() or not run_path.is_dir():
        failures.append(f"run directory 不存在或不是目录：{run_path}")

    missing = [name for name in V3_REQUIRED_TRAJECTORY_FILES if not (run_path / name).exists()]
    failures.extend(f"trajectory store 缺少必需文件：{name}" for name in missing)

    transcript = _read_jsonl_for_inspect(run_path / "transcript.jsonl", failures)
    events = _read_jsonl_for_inspect(run_path / "events.jsonl", failures)
    artifact_errors = []
    if (run_path / "artifacts.json").exists():
        try:
            artifact_errors = verify_artifact_manifest(run_path)
        except (OSError, json.JSONDecodeError) as exc:
            artifact_errors = [f"artifact manifest 无法读取：{exc}"]
    failures.extend(f"artifact manifest 无效：{error}" for error in artifact_errors)

    transcript_projection = [
        {
            "role": record.get("role"),
            "content_preview": record.get("content_preview"),
            "content_artifact_refs": _safe_scan_projection(record.get("content_artifact_refs", [])),
        }
        for record in transcript
        if record.get("model_visible")
    ]
    _append_scan_failures(
        failures,
        surface="transcript",
        payload=transcript_projection,
        label="model-visible transcript",
    )

    run_status = _read_json_if_exists(run_path / "run_status.json")
    metrics = _read_json_if_exists(run_path / "metrics.json")
    metadata = _read_json_if_exists(run_path / "run_metadata.json")
    interrupted_or_crashed = _is_interrupted_or_crashed(run_status, metrics, metadata)
    if not interrupted_or_crashed and not (run_path / "run_metadata.json").exists():
        failures.append("completed / terminal run 必须包含 run_metadata.json。")
    if metadata:
        _inspect_run_metadata_refs(run_path, metadata, failures)

    lines = [
        f"Trajectory store: {run_path}",
        f"Transcript records: {len(transcript)}",
        f"Events: {len(events)}",
        f"Artifact manifest errors: {len(artifact_errors)}",
        f"Run metadata: {'present' if (run_path / 'run_metadata.json').exists() else 'missing'}",
        f"Interrupted or crashed: {interrupted_or_crashed}",
    ]
    if failures:
        if assert_readable:
            raise ConfigError("; ".join(failures))
        lines.append("Diagnostics:")
        lines.extend(f"- {failure}" for failure in failures)
    if assert_readable:
        lines.append("Inspect trajectory store: readable")
    lines.append("Inspect trajectory store: passed")
    return "\n".join(lines)


def inspect_tool_contract(
    run_dir: str | Path,
    *,
    assert_frozen: bool = False,
) -> str:
    """Read-only V3 tool contract and policy snapshot inspection."""

    run_path = Path(run_dir)
    failures: list[str] = []
    facts = _read_json_for_inspect(run_path / "run_config_facts.json", failures)
    tool_protocol = facts.get("tool_protocol") if isinstance(facts, dict) else None
    if not isinstance(tool_protocol, dict):
        failures.append("run_config_facts.json 缺少 tool_protocol。")
        tool_protocol = {}

    snapshot_ref = tool_protocol.get("tool_schema_snapshot_ref")
    snapshot_path = _inspect_artifact_ref(run_path, snapshot_ref, failures, label="tool_schema_snapshot_ref")
    expected_snapshot_sha = tool_protocol.get("tool_schema_snapshot_sha256")
    snapshot_payload = _read_json_for_inspect(snapshot_path, failures) if snapshot_path else {}
    if snapshot_payload:
        canonical_payload = {
            "tool_order": snapshot_payload.get("tool_order"),
            "tool_parser_version": snapshot_payload.get("tool_parser_version"),
            "tool_result_format_version": snapshot_payload.get("tool_result_format_version"),
            "tools": snapshot_payload.get("tools", []),
        }
        payload_sha = _stable_json_sha256(canonical_payload)
        if isinstance(expected_snapshot_sha, str):
            if snapshot_payload.get("snapshot_sha256") != expected_snapshot_sha:
                failures.append("tool_schema_snapshot_sha256 与 snapshot_sha256 字段不一致。")
            if payload_sha != expected_snapshot_sha:
                failures.append("tool_schema_snapshot_sha256 与 snapshot 规范内容哈希不一致。")
        tool_order = snapshot_payload.get("tool_order")
        tool_names = [tool.get("name") for tool in snapshot_payload.get("tools", []) if isinstance(tool, dict)]
        if isinstance(tool_order, list) and tool_order != tool_names:
            failures.append("tool schema snapshot tool_order 与 tools 稳定顺序不一致。")

    for field in (
        "tool_order",
        "tool_parser_version",
        "tool_result_format_version",
        "tool_policy_version",
    ):
        if field not in tool_protocol:
            failures.append(f"tool_protocol 缺少字段：{field}")
    for field in (
        "allowed_tools_policy",
        "permission_mode",
        "permission_policy_version",
        "shell_command_policy_version",
        "context_policy_version",
        "context_builder_version",
    ):
        if not facts.get(field):
            failures.append(f"run_config_facts.json 缺少策略快照字段：{field}")

    explicit_contract_ref = facts.get("tool_contract_snapshot_ref")
    if explicit_contract_ref is not None:
        _inspect_artifact_ref(run_path, explicit_contract_ref, failures, label="tool_contract_snapshot_ref")
        contract_status = "explicit"
    else:
        contract_status = "derived_from_v2_tool_protocol_and_v3_policy_facts"
    hook_status = facts.get("hook_policy_snapshot_ref") or "hooks_disabled_inferred"
    mcp_status = facts.get("mcp_policy_snapshot_ref") or "mcp_disabled_inferred"

    lines = [
        f"Tool contract run directory: {run_path}",
        f"Tool contract snapshot status: {contract_status}",
        f"Tool schema snapshot: {'present' if snapshot_path else 'missing'}",
        f"Tool order count: {len(tool_protocol.get('tool_order', [])) if isinstance(tool_protocol.get('tool_order'), list) else 0}",
        f"Hook policy snapshot status: {hook_status}",
        f"MCP policy snapshot status: {mcp_status}",
    ]
    if failures:
        if assert_frozen:
            raise ConfigError("; ".join(failures))
        lines.append("Diagnostics:")
        lines.extend(f"- {failure}" for failure in failures)
    if assert_frozen:
        lines.append("Inspect tool contract: frozen")
    lines.append("Inspect tool contract: passed")
    return "\n".join(lines)


def build_v3_run_selection_manifest(
    *,
    run_refs: list[str],
    output: str | Path,
) -> Path:
    """Build an explicit typed V3 run-selection manifest."""

    if not run_refs:
        raise ConfigError("至少需要一个 --run-ref。")
    output_path = Path(output)
    entries = []
    seen_roles: set[str] = set()
    for index, raw in enumerate(run_refs, start=1):
        parsed = _parse_run_ref(raw)
        role = parsed["role"]
        if role in seen_roles:
            raise ConfigError(f"run selection role 重复：{role}")
        seen_roles.add(role)
        path = Path(parsed["path"])
        if not path.exists():
            raise ConfigError(f"run selection path 不存在：{path}")
        entry = _run_selection_entry(index=index, role=role, path=path, raw=parsed)
        entries.append(entry)
    manifest = {
        "schema_version": V3_RUN_SELECTION_MANIFEST_VERSION,
        "generated_at": _utc_timestamp(),
        "required_roles": list(V3_REQUIRED_RUN_SELECTION_ROLES),
        "entries": entries,
        "role_counts": {role: sum(1 for entry in entries if entry.get("role") == role) for role in sorted(seen_roles)},
    }
    _write_json(output_path, manifest)
    return output_path


def build_v3_acceptance_inputs(
    *,
    run_selection_manifest: str | Path,
    export_root: str | Path,
    v2_report: str | Path,
    pre_acceptance_docs: list[str | Path],
    output: str | Path,
    documentation_manifest: str | Path | None = None,
    command_log: str | Path | None = None,
    test_evidence: str | Path | None = None,
) -> Path:
    """Build explicit V3 acceptance input manifest."""

    if not pre_acceptance_docs:
        raise ConfigError("至少需要一个 --pre-acceptance-doc。")
    output_path = Path(output)
    refs_by_category: dict[str, list[dict[str, Any]]] = {
        "run_selection_manifest": [_file_ref(Path(run_selection_manifest), category="run_selection_manifest")],
        "export_root": [_file_ref(Path(export_root), category="export_root")],
        "v2_report": [_file_ref(Path(v2_report), category="v2_report")],
        "pre_acceptance_docs": [
            _file_ref(Path(doc), category="pre_acceptance_docs")
            for doc in pre_acceptance_docs
        ],
    }
    if documentation_manifest is not None:
        refs_by_category["documentation_manifest"] = [
            _file_ref(Path(documentation_manifest), category="documentation_manifest")
        ]
    if command_log is not None:
        refs_by_category["command_log"] = [_file_ref(Path(command_log), category="command_log")]
    if test_evidence is not None:
        refs_by_category["test_evidence"] = [_file_ref(Path(test_evidence), category="test_evidence")]

    manifest = {
        "schema_version": V3_ACCEPTANCE_INPUTS_VERSION,
        "generated_at": _utc_timestamp(),
        "required_categories": list(V3_REQUIRED_ACCEPTANCE_INPUT_CATEGORIES),
        "input_refs_by_category": refs_by_category,
        "run_selection_manifest_ref": refs_by_category["run_selection_manifest"][0],
        "export_root_refs": refs_by_category["export_root"],
        "v2_report_ref": refs_by_category["v2_report"][0],
        "pre_acceptance_doc_refs": refs_by_category["pre_acceptance_docs"],
        "documentation_manifest_ref": refs_by_category.get("documentation_manifest", [None])[0],
        "command_log_ref": refs_by_category.get("command_log", [None])[0],
        "test_evidence_ref": refs_by_category.get("test_evidence", [None])[0],
    }
    _inspect_acceptance_inputs_payload(manifest, assert_complete=False)
    _write_json(output_path, manifest)
    return output_path


def build_v3_acceptance_report(
    *,
    acceptance_dir: str | Path,
    input_manifest: str | Path,
    output: str | Path,
) -> Path:
    """Build a fresh V3 acceptance report from explicit inputs."""

    started_at = _utc_timestamp()
    acceptance_path = Path(acceptance_dir)
    output_path = Path(output)
    if acceptance_path.exists():
        raise ConfigError(f"ACCEPTANCE_DIR 必须是不存在的新目录，当前已存在：{acceptance_path}")
    if output_path.parent.resolve() != acceptance_path.resolve():
        raise ConfigError("--output 必须位于 --acceptance-dir 内。")
    input_path = Path(input_manifest)
    input_payload = _read_json_for_inspect(input_path, [])
    _inspect_acceptance_inputs_payload(input_payload, assert_complete=False)

    acceptance_path.mkdir(parents=True)
    copied_input_path = acceptance_path / "acceptance_inputs_manifest.json"
    shutil.copyfile(input_path, copied_input_path)
    run_selection_source = _resolve_file_ref(input_payload["run_selection_manifest_ref"])
    copied_run_selection_path = acceptance_path / "run_selection_manifest.json"
    shutil.copyfile(run_selection_source, copied_run_selection_path)
    scan_results = _scan_acceptance_surfaces(input_payload, run_selection_payload=_read_json_for_inspect(copied_run_selection_path, []))
    scan_path = acceptance_path / "contamination_scan_results.json"
    _write_json(scan_path, {"schema_version": "repo_harness_v3_acceptance_contamination_scan_v0", "results": scan_results})

    command_log_path = acceptance_path / "acceptance_command_log.jsonl"
    _append_command_log(
        command_log_path,
        command_name="build-v3-acceptance-report",
        argv=[
            "repo-harness",
            "build-v3-acceptance-report",
            "--acceptance-dir",
            acceptance_path.as_posix(),
            "--input-manifest",
            input_path.as_posix(),
            "--output",
            output_path.as_posix(),
        ],
        started_at=started_at,
        input_paths=[input_path],
        output_paths=[copied_input_path, copied_run_selection_path, scan_path],
        self_referential_output_paths=[output_path],
        self_referential_output_reason=(
            "v3_acceptance_report.json binds acceptance_command_log.jsonl; recording "
            "the report file sha256 inside that same command log would create a hash cycle. "
            "The report file is instead verified directly by inspect-v3-acceptance and by "
            "acceptance_bundle_manifest.json."
        ),
        base_dir=Path.cwd(),
        exit_code=0,
    )
    failures = _scan_failures_from_results(scan_results)
    report = V3AcceptanceReport(
        acceptance_id=acceptance_path.name,
        status="failed" if failures else "passed",
        input_manifest_ref=_artifact_ref(
            copied_input_path,
            base_dir=acceptance_path,
            artifact_id="v3_acceptance_input_manifest",
            kind="json",
        ),
        command_log_ref=_artifact_ref(
            command_log_path,
            base_dir=acceptance_path,
            artifact_id="v3_acceptance_command_log",
            kind="jsonl",
        ),
        run_selection_manifest_ref=_artifact_ref(
            copied_run_selection_path,
            base_dir=acceptance_path,
            artifact_id="v3_acceptance_run_selection_manifest",
            kind="json",
        ),
        report_generated_at=_utc_timestamp(),
        checks=[
            "explicit_acceptance_inputs_bound",
            "fresh_acceptance_directory_enforced",
            "run_selection_manifest_bound",
            "command_log_bound",
            "contamination_scans_bound",
        ],
        contamination_scan_refs=[
            _artifact_ref(
                scan_path,
                base_dir=acceptance_path,
                artifact_id="v3_acceptance_contamination_scan",
                kind="json",
            )
        ],
        contamination_scan_surfaces=list(V3_VISIBILITY_SURFACES),
        failures=failures,
    )
    _write_json(output_path, report.model_dump(mode="json"))
    return output_path


def inspect_v3_acceptance(
    report: str | Path,
    *,
    assert_complete: bool = False,
) -> str:
    """Inspect V3 acceptance report and all bound evidence."""

    report_path = Path(report)
    acceptance_path = report_path.parent
    failures: list[str] = []
    report_payload = _read_json_for_inspect(report_path, failures)
    try:
        parsed = V3AcceptanceReport.model_validate(report_payload)
    except ValidationError as exc:
        failures.append(f"v3_acceptance_report.json schema 无效：{exc}")
        parsed = None
    input_manifest_path = _inspect_artifact_ref(
        acceptance_path,
        report_payload.get("input_manifest_ref"),
        failures,
        label="input_manifest_ref",
    )
    command_log_path = _inspect_artifact_ref(
        acceptance_path,
        report_payload.get("command_log_ref"),
        failures,
        label="command_log_ref",
    )
    run_selection_path = _inspect_artifact_ref(
        acceptance_path,
        report_payload.get("run_selection_manifest_ref"),
        failures,
        label="run_selection_manifest_ref",
    )
    for index, ref in enumerate(report_payload.get("contamination_scan_refs", []), start=1):
        scan_path = _inspect_artifact_ref(
            acceptance_path,
            ref,
            failures,
            label=f"contamination_scan_refs[{index}]",
        )
        if scan_path is not None:
            _inspect_contamination_scan(scan_path, failures)
    input_payload = _read_json_for_inspect(input_manifest_path, failures) if input_manifest_path else {}
    if input_payload:
        try:
            _inspect_acceptance_inputs_payload(input_payload, assert_complete=assert_complete)
        except ConfigError as exc:
            failures.append(str(exc))
        _inspect_manifest_safe_for_acceptance(input_payload, failures, label="ACCEPTANCE_INPUTS")
    run_selection_payload = _read_json_for_inspect(run_selection_path, failures) if run_selection_path else {}
    if run_selection_payload:
        try:
            _inspect_run_selection_manifest_payload(run_selection_payload, assert_complete=assert_complete)
        except ConfigError as exc:
            failures.append(str(exc))
        _inspect_manifest_safe_for_acceptance(run_selection_payload, failures, label="RUN_SELECTION_MANIFEST")
        if input_payload:
            source_ref = input_payload.get("run_selection_manifest_ref", {})
            if source_ref.get("sha256") and source_ref.get("sha256") != _hash_path(run_selection_path):
                failures.append("report 内 run_selection_manifest copy 与 ACCEPTANCE_INPUTS sha256 不一致。")
    if command_log_path is not None:
        _inspect_command_log(command_log_path, failures)
        _inspect_acceptance_command_log_consistency(
            command_log_path,
            input_manifest_path=input_manifest_path,
            failures=failures,
        )
    if parsed is not None and parsed.status == "passed" and failures:
        failures.append("report status=passed 但重新读取 evidence 后发现失败。")
    if assert_complete and report_payload.get("status") != "passed":
        failures.append("assert-complete 要求 V3 acceptance report status=passed。")

    lines = [
        f"V3 acceptance report: {report_path}",
        f"Acceptance directory: {acceptance_path}",
        f"Report status: {report_payload.get('status')}",
        f"Checks: {len(report_payload.get('checks', []))}",
        f"Contamination scan refs: {len(report_payload.get('contamination_scan_refs', []))}",
    ]
    if failures:
        raise ConfigError("; ".join(failures))
    if assert_complete:
        lines.append("Inspect V3 acceptance: complete")
    lines.append("Inspect V3 acceptance: passed")
    return "\n".join(lines)


def build_v3_acceptance_bundle(
    *,
    acceptance_dir: str | Path,
    input_manifest: str | Path,
    report: str | Path,
    documentation_refs: list[str | Path],
    output: str | Path,
) -> Path:
    """Bind post-acceptance documentation and acceptance evidence in a bundle manifest."""

    acceptance_path = Path(acceptance_dir)
    output_path = Path(output)
    if not acceptance_path.exists() or not acceptance_path.is_dir():
        raise ConfigError(f"acceptance directory 不存在：{acceptance_path}")
    if output_path.parent.resolve() != acceptance_path.resolve():
        raise ConfigError("--output 必须位于 --acceptance-dir 内。")
    if not documentation_refs:
        raise ConfigError("至少需要一个 --documentation-ref。")
    input_path = Path(input_manifest)
    report_path = Path(report)
    command_log_path = acceptance_path / "acceptance_command_log.jsonl"
    manifest = {
        "schema_version": V3_ACCEPTANCE_BUNDLE_MANIFEST_VERSION,
        "generated_at": _utc_timestamp(),
        "acceptance_dir_ref": {
            "path": _relative_path(acceptance_path, Path.cwd()),
            "kind": "directory",
            "category": "acceptance_dir",
            "hash_policy": "not_hashed_to_avoid_self_referential_bundle_manifest",
        },
        "input_manifest_ref": _file_ref(input_path, category="acceptance_inputs"),
        "report_ref": _file_ref(report_path, category="v3_acceptance_report"),
        "acceptance_command_log_ref": (
            _file_ref(command_log_path, category="acceptance_command_log")
            if command_log_path.exists()
            else None
        ),
        "documentation_refs": [
            _file_ref(Path(doc), category="post_acceptance_documentation")
            for doc in documentation_refs
        ],
        "bundle_policy": {
            "post_acceptance_docs_not_report_inputs": True,
            "inspect_recomputes_all_sha256": True,
            "inspect_rechecks_v3_acceptance_report": True,
            "no_latest_run_discovery": True,
        },
    }
    _write_json(output_path, manifest)
    return output_path


def inspect_acceptance_bundle(
    manifest: str | Path,
    *,
    assert_immutable: bool = False,
) -> str:
    """Inspect V3 acceptance bundle immutability."""

    manifest_path = Path(manifest)
    failures: list[str] = []
    payload = _read_json_for_inspect(manifest_path, failures)
    if payload.get("schema_version") != V3_ACCEPTANCE_BUNDLE_MANIFEST_VERSION:
        failures.append("acceptance_bundle_manifest.json schema_version 无效。")
    for label in (
        "input_manifest_ref",
        "report_ref",
        "acceptance_command_log_ref",
    ):
        ref = payload.get(label)
        if ref is None and label == "acceptance_command_log_ref":
            failures.append("acceptance bundle 缺少 acceptance_command_log_ref。")
            continue
        _inspect_file_ref(ref, failures, label=label)
    acceptance_dir_ref = payload.get("acceptance_dir_ref")
    if not isinstance(acceptance_dir_ref, dict):
        failures.append("acceptance bundle 缺少 acceptance_dir_ref。")
    else:
        acceptance_dir_path = Path(str(acceptance_dir_ref.get("path", "")))
        if not acceptance_dir_path.is_absolute():
            acceptance_dir_path = Path.cwd() / acceptance_dir_path
        if not acceptance_dir_path.exists() or not acceptance_dir_path.is_dir():
            failures.append("acceptance_dir_ref 指向的目录不存在。")
        if acceptance_dir_ref.get("hash_policy") != "not_hashed_to_avoid_self_referential_bundle_manifest":
            failures.append("acceptance_dir_ref 必须声明非自引用 hash policy。")
    docs = payload.get("documentation_refs", [])
    if not isinstance(docs, list) or not docs:
        failures.append("acceptance bundle 必须绑定 post-acceptance documentation refs。")
    for index, ref in enumerate(docs, start=1):
        _inspect_file_ref(ref, failures, label=f"documentation_refs[{index}]")
    _inspect_manifest_safe_for_acceptance(payload, failures, label="acceptance_bundle_manifest")
    _inspect_post_acceptance_docs_not_report_inputs(payload, failures)

    report_ref = payload.get("report_ref")
    if isinstance(report_ref, dict):
        report_path = _resolve_file_ref(report_ref)
        if report_path.exists():
            report_payload = _read_json_for_inspect(report_path, failures)
            input_ref = payload.get("input_manifest_ref", {})
            report_input_ref = report_payload.get("input_manifest_ref", {})
            if (
                isinstance(input_ref, dict)
                and isinstance(report_input_ref, dict)
                and input_ref.get("sha256") != report_input_ref.get("sha256")
            ):
                failures.append("bundle input_manifest_ref 与 report input_manifest_ref sha256 不一致。")
            try:
                inspect_v3_acceptance(report_path, assert_complete=assert_immutable)
            except ConfigError as exc:
                failures.append(f"acceptance bundle 传递性复查 v3_acceptance_report 失败：{exc}")
    lines = [
        f"V3 acceptance bundle: {manifest_path}",
        f"Documentation refs: {len(docs) if isinstance(docs, list) else 0}",
    ]
    if failures:
        raise ConfigError("; ".join(failures))
    if assert_immutable:
        lines.append("Inspect acceptance bundle: immutable")
    lines.append("Inspect acceptance bundle: passed")
    return "\n".join(lines)


def _inspect_post_acceptance_docs_not_report_inputs(
    payload: dict[str, Any],
    failures: list[str],
) -> None:
    docs = payload.get("documentation_refs", [])
    if not isinstance(docs, list):
        return
    post_doc_paths = {
        _normalise_manifest_path(ref.get("path") or ref.get("relative_path"))
        for ref in docs
        if isinstance(ref, dict)
    }
    input_ref = payload.get("input_manifest_ref")
    if not isinstance(input_ref, dict):
        return
    input_path = _resolve_file_ref(input_ref)
    if not input_path.exists():
        return
    inputs = _read_json_for_inspect(input_path, failures)
    report_input_doc_paths = _acceptance_input_documentation_paths(inputs, failures)
    overlap = sorted(post_doc_paths.intersection(report_input_doc_paths))
    if overlap:
        failures.append(
            "post-acceptance documentation 不能同时作为 acceptance report input："
            + ", ".join(overlap)
        )


def _acceptance_input_documentation_paths(
    inputs: dict[str, Any],
    failures: list[str],
) -> set[str]:
    paths: set[str] = set()
    for ref in inputs.get("pre_acceptance_doc_refs", []):
        if isinstance(ref, dict):
            raw = ref.get("path") or ref.get("relative_path")
            if raw:
                paths.add(_normalise_manifest_path(raw))
    refs_by_category = inputs.get("input_refs_by_category", {})
    if isinstance(refs_by_category, dict):
        for ref in refs_by_category.get("pre_acceptance_docs", []):
            if isinstance(ref, dict):
                raw = ref.get("path") or ref.get("relative_path")
                if raw:
                    paths.add(_normalise_manifest_path(raw))
    documentation_ref = inputs.get("documentation_manifest_ref")
    if isinstance(documentation_ref, dict):
        documentation_path = _resolve_file_ref(documentation_ref)
        if documentation_path.exists():
            documentation_payload = _read_json_for_inspect(documentation_path, failures)
            paths.update(_collect_documentation_manifest_paths(documentation_payload))
    return paths


def _collect_documentation_manifest_paths(value: Any) -> set[str]:
    paths: set[str] = set()
    if isinstance(value, dict):
        for key, nested in value.items():
            if str(key) == "excluded_post_acceptance_docs":
                continue
            if str(key) in {"path", "relative_path"} and _looks_like_documentation_path(nested):
                paths.add(_normalise_manifest_path(nested))
            paths.update(_collect_documentation_manifest_paths(nested))
    elif isinstance(value, list):
        for nested in value:
            paths.update(_collect_documentation_manifest_paths(nested))
    elif _looks_like_documentation_path(value):
        paths.add(_normalise_manifest_path(value))
    return paths


def _looks_like_documentation_path(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    suffix = Path(value).suffix.lower()
    return suffix in {".md", ".markdown"}


def _parse_run_ref(raw: str) -> dict[str, str]:
    parts = {}
    for chunk in raw.split(","):
        if "=" not in chunk:
            raise ConfigError(f"--run-ref 必须使用 key=value 片段：{raw}")
        key, value = chunk.split("=", 1)
        parts[key.strip()] = value.strip()
    if not parts.get("role") or not parts.get("path"):
        raise ConfigError(f"--run-ref 必须至少包含 role 和 path：{raw}")
    return parts


def _run_selection_entry(*, index: int, role: str, path: Path, raw: dict[str, str]) -> dict[str, Any]:
    path_ref = _file_ref(path, category=f"run_selection:{role}")
    entry: dict[str, Any] = {
        "index": index,
        "role": role,
        "path_ref": path_ref,
        "path_kind": _kind_for_path(path),
        "stage_family": _stage_family_for_path(path),
        "run_state": raw.get("run_state") or _infer_run_state(path),
        "accepted": _parse_optional_bool(raw.get("accepted")),
        "structured_skip_reason": raw.get("structured_skip_reason") or _infer_skip_reason(path),
        "evidence_refs": {},
    }
    if path.is_dir():
        for name in (
            "summary.md",
            "transcript.jsonl",
            "events.jsonl",
            "artifacts.json",
            "run_config_facts.json",
            "run_metadata.json",
            "docker_backend_status.json",
            "docker_stage_status.json",
            "source_materialization_report.json",
            "context_compaction_report.json",
            "long_rollout_diagnostics.json",
            "failure_diagnostics_core_report.json",
            "failure_distribution_report.json",
        ):
            candidate = path / name
            if candidate.exists():
                entry["evidence_refs"][name] = _file_ref(candidate, category=f"run_selection:{role}:{name}")
        facts = _read_json_if_exists(path / "run_config_facts.json")
        metadata = _read_json_if_exists(path / "run_metadata.json")
        entry["run_id"] = facts.get("run_id") or metadata.get("run_id") or path.name
        entry["task_id"] = facts.get("task_id") or metadata.get("task_id")
        entry["run_outcome"] = metadata.get("run_outcome") or _read_json_if_exists(path / "metrics.json").get("run_outcome")
        entry["run_status"] = metadata.get("run_status") or _read_json_if_exists(path / "run_status.json").get("status")
        entry["final_verifier_status"] = metadata.get("final_verifier_status") or _read_json_if_exists(path / "metrics.json").get("final_verifier_status")
        if facts:
            entry["provider"] = facts.get("provider")
            entry["actual_provider"] = facts.get("actual_provider")
            entry["requested_provider"] = facts.get("requested_provider")
            entry["workspace_backend"] = (
                facts.get("environment_fingerprint", {})
                .get("workspace_execution", {})
                .get("workspace_backend", {})
                .get("backend")
            )
            entry["source_tree_hash"] = (
                facts.get("environment_fingerprint", {})
                .get("workspace_execution", {})
                .get("source_checkout", {})
                .get("source_tree_hash")
            )
    else:
        payload = _read_json_if_exists(path)
        entry["run_id"] = payload.get("run_id") or payload.get("id") or path.stem
        entry["report_status"] = payload.get("status")
        entry["provider"] = payload.get("provider") or payload.get("actual_provider") or payload.get("requested_provider")
        entry["actual_provider"] = payload.get("actual_provider")
        entry["requested_provider"] = payload.get("requested_provider")
        entry["credential_status"] = payload.get("credential_status")
        entry["run_outcome"] = payload.get("run_outcome")
        entry["final_verifier_status"] = payload.get("final_verifier_status")
        entry["run_state"] = raw.get("run_state") or _infer_run_state(path)
    return entry


def _inspect_run_selection_manifest_payload(payload: dict[str, Any], *, assert_complete: bool) -> None:
    failures: list[str] = []
    if payload.get("schema_version") != V3_RUN_SELECTION_MANIFEST_VERSION:
        failures.append("RUN_SELECTION_MANIFEST schema_version 无效。")
    entries = payload.get("entries", [])
    if not isinstance(entries, list) or not entries:
        failures.append("RUN_SELECTION_MANIFEST 必须包含 entries。")
        entries = []
    roles = {entry.get("role") for entry in entries if isinstance(entry, dict)}
    if assert_complete:
        missing = sorted(set(V3_REQUIRED_RUN_SELECTION_ROLES).difference(roles))
        if missing:
            failures.append("RUN_SELECTION_MANIFEST 缺少 required roles：" + ", ".join(missing))
    for entry in entries:
        if not isinstance(entry, dict):
            failures.append("RUN_SELECTION_MANIFEST entry 必须是 object。")
            continue
        role = str(entry.get("role") or "")
        _inspect_file_ref(entry.get("path_ref"), failures, label=f"run_selection[{role}].path_ref")
        for name, ref in entry.get("evidence_refs", {}).items():
            _inspect_file_ref(ref, failures, label=f"run_selection[{role}].evidence_refs.{name}")
        if (
            role == "credential_gated_real_provider"
            and entry.get("structured_skip_reason")
            and (entry.get("accepted") is True or str(entry.get("run_state", "")).lower() in {"accepted", "completed", "success"})
        ):
            failures.append("credential-gated real provider skip 不能伪装成 accepted run。")
        if assert_complete and role == "credential_gated_real_provider":
            if entry.get("structured_skip_reason"):
                if _has_non_real_provider_identity(entry):
                    failures.append("credential-gated real provider skip 不能绑定 replay/mock provider evidence。")
                if entry.get("accepted") is True or _entry_is_success(entry):
                    failures.append("credential-gated real provider skip 不能有 accepted/success 状态。")
            else:
                if not _is_real_provider_entry(entry):
                    failures.append("credential-gated real provider 必须是真实 provider evidence 或结构化 skip。")
                if not _entry_is_success(entry):
                    failures.append("credential-gated real provider 有凭证路径必须 accepted/success。")
        if assert_complete and role == "mock_provider" and not entry.get("structured_skip_reason"):
            if not _is_mock_provider_entry(entry):
                failures.append("mock_provider role 必须绑定 mock provider evidence。")
            if not _entry_is_success(entry):
                failures.append("mock_provider role 必须 accepted/success。")
        if assert_complete and role == "replay" and not entry.get("structured_skip_reason"):
            if str(entry.get("provider") or "").lower() != "replay":
                failures.append("replay role 必须绑定 replay provider evidence。")
            if not _entry_is_success(entry):
                failures.append("replay role 必须 success/accepted。")
        if assert_complete and role in V3_CORE_AGENT_LOOP_ROLES:
            if entry.get("structured_skip_reason"):
                failures.append(f"{role} role 是 V3 核心 Agent Loop evidence，不能用 structured skip 通过 acceptance。")
            if not _entry_is_success(entry):
                failures.append(f"{role} role 必须 success/accepted，不能用失败 run 通过 acceptance。")
            if not _is_real_provider_entry(entry):
                failures.append(f"{role} role 必须绑定真实 provider Agent Loop evidence，不能由 replay/mock/fake 替代。")
            if not _entry_entered_agent_loop(entry):
                failures.append(f"{role} role 必须绑定实际进入 Agent Loop 的 run evidence。")
        if (
            assert_complete
            and role in V3_TRAJECTORY_RUN_ROLES
            and not entry.get("structured_skip_reason")
        ):
            path_ref = entry.get("path_ref", {})
            path = _resolve_file_ref(path_ref) if isinstance(path_ref, dict) else Path("")
            if path.is_dir() and (path / "run_config_facts.json").exists():
                try:
                    inspect_trajectory_store(path, assert_readable=True)
                    inspect_tool_contract(path, assert_frozen=True)
                except ConfigError as exc:
                    failures.append(f"{role} run inspection failed：{exc}")
                _inspect_selected_docker_backend_status(entry, path, failures)
            elif role not in {"credential_gated_real_provider", "mock_provider"}:
                failures.append(f"{role} run ref 必须指向包含 run_config_facts.json 的 run directory。")
        if assert_complete and entry.get("stage_family") == "pre_v3" and role not in {"mock_provider", "credential_gated_real_provider"}:
            failures.append(f"{role} run ref 指向 V3 之前的旧 RUN_DIR。")
    if failures:
        raise ConfigError("; ".join(failures))


def _inspect_selected_docker_backend_status(
    entry: dict[str, Any],
    run_dir: Path,
    failures: list[str],
) -> None:
    role = str(entry.get("role") or "")
    backend = str(entry.get("workspace_backend") or "").lower()
    requires_docker_backend = role in V3_REQUIRED_DOCKER_BACKEND_ROLES or backend == "docker"
    if not requires_docker_backend:
        return
    evidence_refs = entry.get("evidence_refs", {})
    if not isinstance(evidence_refs, dict):
        evidence_refs = {}
    inspected_status_files = []
    for name in V3_DOCKER_BACKEND_STATUS_FILES:
        status_path = run_dir / name
        if not status_path.exists():
            continue
        inspected_status_files.append(name)
        try:
            inspect_workspace_backend_status(
                status_file=status_path,
                assert_docker_backend=True,
            )
        except WorkspaceBackendError as exc:
            failures.append(f"{role} docker backend inspection failed ({name})：{exc}")
    if not inspected_status_files:
        failures.append(f"{role} docker backend run 缺少 docker_backend_status.json。")
    elif "docker_backend_status.json" not in inspected_status_files:
        failures.append(f"{role} docker backend run 缺少 V3 docker_backend_status.json。")
    for name in inspected_status_files:
        if name not in evidence_refs:
            failures.append(f"{role} run_selection evidence_refs 缺少 {name}。")


def _inspect_acceptance_inputs_payload(payload: dict[str, Any], *, assert_complete: bool) -> None:
    failures: list[str] = []
    if payload.get("schema_version") != V3_ACCEPTANCE_INPUTS_VERSION:
        failures.append("ACCEPTANCE_INPUTS schema_version 无效。")
    refs_by_category = payload.get("input_refs_by_category")
    if not isinstance(refs_by_category, dict):
        failures.append("ACCEPTANCE_INPUTS 缺少 input_refs_by_category。")
        refs_by_category = {}
    if assert_complete:
        missing = [
            category
            for category in V3_REQUIRED_ACCEPTANCE_INPUT_CATEGORIES
            if not refs_by_category.get(category)
        ]
        if missing:
            failures.append("ACCEPTANCE_INPUTS 缺少必需类别：" + ", ".join(missing))
    for category, refs in refs_by_category.items():
        if not isinstance(refs, list):
            failures.append(f"input_refs_by_category.{category} 必须是列表。")
            continue
        for index, ref in enumerate(refs, start=1):
            _inspect_file_ref(ref, failures, label=f"{category}[{index}]")
    if assert_complete:
        doc_paths = {
            _normalise_manifest_path(ref.get("path") or ref.get("relative_path"))
            for ref in refs_by_category.get("pre_acceptance_docs", [])
            if isinstance(ref, dict)
        }
        missing_docs = [
            doc
            for doc in V3_REQUIRED_PRE_ACCEPTANCE_DOCS
            if _normalise_manifest_path(doc) not in doc_paths
        ]
        if missing_docs:
            failures.append("ACCEPTANCE_INPUTS 缺少必需 pre-acceptance 文档：" + ", ".join(missing_docs))
        for ref in refs_by_category.get("v2_report", []):
            v2_path = _inspect_file_ref(ref, failures, label="v2_report")
            if v2_path is not None:
                _inspect_v2_acceptance_report(v2_path, failures)
        for ref in refs_by_category.get("command_log", []):
            command_log_path = _inspect_file_ref(ref, failures, label="pre_acceptance_command_log")
            if command_log_path is not None:
                _inspect_command_log(command_log_path, failures)
    _inspect_manifest_safe_for_acceptance(payload, failures, label="ACCEPTANCE_INPUTS")
    if failures:
        raise ConfigError("; ".join(failures))


def _inspect_acceptance_command_log_consistency(
    command_log_path: Path,
    *,
    input_manifest_path: Path | None,
    failures: list[str],
) -> None:
    records = _read_jsonl_for_inspect(command_log_path, failures)
    build_entries = [record for record in records if record.get("command_name") == "build-v3-acceptance-report"]
    if not build_entries:
        failures.append("acceptance_command_log.jsonl 缺少 build-v3-acceptance-report 记录。")
        return
    if input_manifest_path is None:
        return
    expected_sha = sha256_file(input_manifest_path)
    if not any(
        any(ref.get("sha256") == expected_sha for ref in record.get("input_refs", []) if isinstance(ref, dict))
        for record in build_entries
    ):
        failures.append("acceptance_command_log.jsonl 未绑定 report 使用的 input manifest sha256。")
    if not any(record.get("self_referential_output_paths") for record in build_entries):
        failures.append("acceptance_command_log.jsonl 未记录 self-referential acceptance report output path。")


def _inspect_v2_acceptance_report(path: Path, failures: list[str]) -> None:
    from repo_harness.v2_acceptance import inspect_v2_acceptance

    try:
        inspect_v2_acceptance(path, assert_complete=True)
    except Exception as exc:
        failures.append(f"V2 acceptance report 复查失败：{exc}")


def _entry_is_success(entry: dict[str, Any]) -> bool:
    accepted = entry.get("accepted") is True
    status_values = {
        str(entry.get("run_state") or "").lower(),
        str(entry.get("run_outcome") or "").lower(),
        str(entry.get("final_verifier_status") or "").lower(),
        str(entry.get("report_status") or "").lower(),
    }
    bound_status_values = _bound_status_values(entry)
    status_values.update(bound_status_values)
    failure_values = {
        "failed",
        "failure",
        "error",
        "timeout",
        "rejected",
        "invalid_task",
        "flaky_task",
        "inconclusive",
    }
    if status_values.intersection(failure_values):
        return False
    success_values = {
        "success",
        "accepted",
        "accepted_with_credentials",
        "passed",
    }
    if bound_status_values:
        return bool(bound_status_values.intersection(success_values))
    return accepted or bool(status_values.intersection(success_values))


def _bound_status_values(entry: dict[str, Any]) -> set[str]:
    values: set[str] = set()
    path_ref = entry.get("path_ref")
    if isinstance(path_ref, dict):
        values.update(_status_values_from_path(_resolve_file_ref(path_ref)))
    evidence_refs = entry.get("evidence_refs")
    if isinstance(evidence_refs, dict):
        for ref in evidence_refs.values():
            if isinstance(ref, dict):
                values.update(_status_values_from_path(_resolve_file_ref(ref)))
    values.discard("")
    return values


def _status_values_from_path(path: Path) -> set[str]:
    payloads = _provider_and_status_payloads(path)
    values: set[str] = set()
    for payload in payloads:
        for key in (
            "status",
            "run_state",
            "run_status",
            "run_outcome",
            "final_verifier_status",
            "task_success",
        ):
            value = payload.get(key)
            if isinstance(value, str) and value:
                values.add(value.lower())
            elif isinstance(value, bool):
                values.add("success" if value else "failed")
        metrics = payload.get("metrics_summary")
        if isinstance(metrics, dict):
            for key in ("run_outcome", "final_verifier_status"):
                value = metrics.get(key)
                if isinstance(value, str) and value:
                    values.add(value.lower())
    return values


def _is_real_provider_entry(entry: dict[str, Any]) -> bool:
    providers = _provider_values(entry)
    return bool(providers.intersection({"deepseek", "openai"})) and not providers.intersection({"mock", "replay", "fake"})


def _is_mock_provider_entry(entry: dict[str, Any]) -> bool:
    providers = _provider_values(entry)
    return "mock" in providers


def _has_non_real_provider_identity(entry: dict[str, Any]) -> bool:
    providers = _provider_values(entry)
    return bool(providers.intersection({"mock", "replay", "fake"}))


def _provider_values(entry: dict[str, Any]) -> set[str]:
    providers = {
        str(entry.get("provider") or "").lower(),
        str(entry.get("actual_provider") or "").lower(),
        str(entry.get("requested_provider") or "").lower(),
    }
    providers.update(_bound_provider_values(entry))
    providers.discard("")
    return providers


def _bound_provider_values(entry: dict[str, Any]) -> set[str]:
    providers: set[str] = set()
    path_ref = entry.get("path_ref")
    if isinstance(path_ref, dict):
        providers.update(_provider_values_from_path(_resolve_file_ref(path_ref)))
    evidence_refs = entry.get("evidence_refs")
    if isinstance(evidence_refs, dict):
        for ref in evidence_refs.values():
            if isinstance(ref, dict):
                providers.update(_provider_values_from_path(_resolve_file_ref(ref)))
    return providers


def _provider_values_from_path(path: Path) -> set[str]:
    payloads = _provider_and_status_payloads(path)
    providers: set[str] = set()
    for payload in payloads:
        for key in ("provider", "actual_provider", "requested_provider"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                providers.add(value.lower())
    return providers


def _provider_and_status_payloads(path: Path) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    if path.is_dir():
        for name in (
            "run_config_facts.json",
            "run_metadata.json",
            "metrics.json",
            "run_status.json",
            "real_provider_smoke_report.json",
            "mock_provider_smoke_report.json",
        ):
            payload = _read_json_if_exists(path / name)
            if payload:
                payloads.append(payload)
    else:
        payload = _read_json_if_exists(path)
        if payload:
            payloads.append(payload)
    return payloads


def _entry_entered_agent_loop(entry: dict[str, Any]) -> bool:
    path_ref = entry.get("path_ref")
    if not isinstance(path_ref, dict):
        return False
    path = _resolve_file_ref(path_ref)
    if not path.is_dir():
        return False
    events_path = path / "events.jsonl"
    if not events_path.exists():
        return False
    try:
        return any(
            event.get("event_type") == "model_call_started"
            for event in read_jsonl(events_path)
            if isinstance(event, dict)
        )
    except Exception:
        return False


def _inspect_command_log(path: Path, failures: list[str]) -> None:
    records = _read_jsonl_for_inspect(path, failures)
    if not records:
        failures.append(f"command log 为空：{path}")
    for index, record in enumerate(records, start=1):
        try:
            CommandLogEntry.model_validate(record)
        except ValidationError as exc:
            failures.append(f"command log 第 {index} 行 schema 无效：{exc}")
            continue
        for label in ("input_refs", "output_refs"):
            refs = record.get(label, [])
            if not isinstance(refs, list):
                failures.append(f"command log 第 {index} 行 {label} 必须是列表。")
                continue
            for ref_index, ref in enumerate(refs, start=1):
                _inspect_command_log_artifact_ref(ref, failures, label=f"command_log[{index}].{label}[{ref_index}]")
        for ref_index, relative_path in enumerate(record.get("self_referential_output_paths", []), start=1):
            path_value = Path(str(relative_path))
            output_path = path_value if path_value.is_absolute() else Path.cwd() / path_value
            if not output_path.exists():
                failures.append(f"command_log[{index}].self_referential_output_paths[{ref_index}] 路径不存在。")


def _inspect_command_log_artifact_ref(ref_payload: Any, failures: list[str], *, label: str) -> None:
    if not isinstance(ref_payload, dict):
        failures.append(f"{label} 缺失或不是 object。")
        return
    try:
        ref = ArtifactRef.model_validate(ref_payload)
    except ValidationError as exc:
        failures.append(f"{label} schema 无效：{exc}")
        return
    path = _resolve_artifact_ref_path(ref, base_dir=Path.cwd())
    if not path.exists():
        failures.append(f"{label} 路径不存在：{ref.relative_path}")
        return
    actual_sha = _hash_path(path)
    if actual_sha != ref.sha256:
        failures.append(f"{label} sha256 不匹配：{ref.relative_path}")
    if not path.is_dir() and path.stat().st_size != ref.size_bytes:
        failures.append(f"{label} size_bytes 不匹配：{ref.relative_path}")


def _inspect_contamination_scan(path: Path, failures: list[str]) -> None:
    payload = _read_json_for_inspect(path, failures)
    results = payload.get("results", [])
    if not isinstance(results, list):
        failures.append("contamination scan results 必须是列表。")
        return
    surfaces = {result.get("surface") for result in results if isinstance(result, dict)}
    missing = sorted(set(V3_VISIBILITY_SURFACES).difference(surfaces))
    if missing:
        failures.append("contamination scan 缺少 surfaces：" + ", ".join(missing))
    for result in results:
        if not isinstance(result, dict):
            failures.append("contamination scan result 必须是 object。")
            continue
        if result.get("clean") is not True:
            failures.append(f"contamination scan failed: {result.get('surface')}")
        source_errors = result.get("source_errors", [])
        if isinstance(source_errors, list) and source_errors:
            failures.append(
                f"contamination scan source errors: {result.get('surface')}:{len(source_errors)}"
            )


def _inspect_manifest_safe_for_acceptance(payload: Any, failures: list[str], *, label: str) -> None:
    _append_scan_failures(
        failures,
        surface="acceptance_input",
        payload=_safe_scan_projection(payload),
        label=label,
    )


def _scan_acceptance_surfaces(input_payload: dict[str, Any], *, run_selection_payload: dict[str, Any]) -> list[dict[str, Any]]:
    denylist = V3ContaminationDenylist()
    payloads, source_errors = _collect_acceptance_scan_payloads(
        input_payload,
        run_selection_payload=run_selection_payload,
    )
    results = []
    for surface in V3_VISIBILITY_SURFACES:
        raw_payload = payloads.get(surface, {"surface": surface, "sources": []})
        payload = _safe_scan_projection(raw_payload)
        result = denylist.scan_payload(surface=surface, payload=payload)
        errors = source_errors.get(surface, [])
        results.append(
            {
                "surface": surface,
                "clean": result.clean and not errors,
                "findings": [finding.model_dump(mode="json") for finding in result.findings],
                "source_count": len(payload.get("sources", [])) if isinstance(payload, dict) else 0,
                "source_errors": errors,
            }
        )
    return results


def _collect_acceptance_scan_payloads(
    input_payload: dict[str, Any],
    *,
    run_selection_payload: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, list[str]]]:
    payloads = {
        surface: {"surface": surface, "sources": []}
        for surface in V3_VISIBILITY_SURFACES
    }
    errors = {surface: [] for surface in V3_VISIBILITY_SURFACES}
    payloads["acceptance_input"]["sources"].append(
        {
            "source": "acceptance_inputs_and_run_selection_manifest",
            "acceptance_inputs": _safe_scan_projection(input_payload),
            "run_selection_manifest": _safe_scan_projection(run_selection_payload),
        }
    )
    for entry in _run_selection_entries(run_selection_payload):
        path = _entry_path(entry)
        if path is None or not path.exists():
            continue
        if path.is_dir():
            _collect_run_transcript_scan_payloads(payloads, errors, entry=entry, run_dir=path)
            _collect_prepared_message_scan_payloads(payloads, errors, entry=entry, run_dir=path)
            _collect_checkpoint_scan_payloads(payloads, errors, entry=entry, run_dir=path)
            _collect_context_scan_payloads(payloads, errors, entry=entry, run_dir=path)
        else:
            payloads["acceptance_input"]["sources"].append(
                {
                    "source": _relative_path(path, Path.cwd()),
                    "label": f"run_selection:{entry.get('role')}",
                    "path_ref": _safe_scan_projection(entry.get("path_ref", {})),
                    "path_kind": entry.get("path_kind"),
                }
            )
    _collect_export_scan_payloads(payloads, errors, input_payload=input_payload)
    return payloads, errors


def _run_selection_entries(run_selection_payload: dict[str, Any]) -> list[dict[str, Any]]:
    entries = run_selection_payload.get("entries", [])
    return [entry for entry in entries if isinstance(entry, dict)]


def _entry_path(entry: dict[str, Any]) -> Path | None:
    ref = entry.get("path_ref")
    if not isinstance(ref, dict):
        return None
    return _resolve_file_ref(ref)


def _collect_run_transcript_scan_payloads(
    payloads: dict[str, dict[str, Any]],
    errors: dict[str, list[str]],
    *,
    entry: dict[str, Any],
    run_dir: Path,
) -> None:
    transcript_path = run_dir / "transcript.jsonl"
    if not transcript_path.exists():
        return
    records = _read_jsonl_for_scan(transcript_path, errors["transcript"])
    model_visible = [
        {
            "run_role": entry.get("role"),
            "run_id": entry.get("run_id"),
            "record_id": record.get("record_id"),
            "role": record.get("role"),
            "content_preview": record.get("content_preview"),
            "content_artifact_refs": record.get("content_artifact_refs", []),
            "context_revision": record.get("context_revision"),
        }
        for record in records
        if record.get("model_visible")
    ]
    payloads["transcript"]["sources"].append(
        {
            "source": _relative_path(transcript_path, Path.cwd()),
            "records": _safe_scan_projection(model_visible),
        }
    )
    tool_records = [
        record
        for record in model_visible
        if record.get("role") == "tool" or record.get("content_artifact_refs")
    ]
    if tool_records:
        payloads["tool_observation"]["sources"].append(
            {
                "source": _relative_path(transcript_path, Path.cwd()),
                "records": _safe_scan_projection(tool_records),
            }
        )


def _collect_prepared_message_scan_payloads(
    payloads: dict[str, dict[str, Any]],
    errors: dict[str, list[str]],
    *,
    entry: dict[str, Any],
    run_dir: Path,
) -> None:
    for ref_payload in _artifact_refs_by_kind(run_dir, "prepared_messages", errors["prepared_messages"]):
        artifact_path = _artifact_path_for_scan(run_dir, ref_payload, errors["prepared_messages"])
        if artifact_path is None:
            continue
        payload = _read_file_payload_for_scan(artifact_path, errors["prepared_messages"])
        if payload is None:
            continue
        payloads["prepared_messages"]["sources"].append(
            {
                "source": _relative_path(artifact_path, Path.cwd()),
                "run_role": entry.get("role"),
                "run_id": entry.get("run_id"),
                "artifact_ref": _safe_scan_projection(ref_payload),
                "payload": _safe_scan_projection(payload),
            }
        )
        messages = payload.get("messages", []) if isinstance(payload, dict) else []
        prompt_messages = [
            message
            for message in messages
            if isinstance(message, dict) and str(message.get("role")) in {"system", "developer", "user"}
        ]
        payloads["prompt"]["sources"].append(
            {
                "source": _relative_path(artifact_path, Path.cwd()),
                "run_role": entry.get("role"),
                "run_id": entry.get("run_id"),
                "messages": _safe_scan_projection(prompt_messages),
            }
        )


def _collect_checkpoint_scan_payloads(
    payloads: dict[str, dict[str, Any]],
    errors: dict[str, list[str]],
    *,
    entry: dict[str, Any],
    run_dir: Path,
) -> None:
    if entry.get("role") != "resume":
        return
    candidates = [
        run_dir / "run_checkpoint_manifest.json",
        run_dir / "experiment_resume_manifest.json",
        run_dir / "checkpoint_manifest.json",
    ]
    checkpoint_dir = run_dir / "checkpoints"
    if checkpoint_dir.exists():
        candidates.extend(sorted(checkpoint_dir.glob("*.json")))
    for path in candidates:
        if path.exists():
            _collect_file_scan_payload(
                payloads["checkpoint"]["sources"],
                errors["checkpoint"],
                path=path,
                label=f"checkpoint:{entry.get('role')}",
            )


def _collect_context_scan_payloads(
    payloads: dict[str, dict[str, Any]],
    errors: dict[str, list[str]],
    *,
    entry: dict[str, Any],
    run_dir: Path,
) -> None:
    if entry.get("role") not in {"context", "long_rollout"}:
        return
    context_path = run_dir / "context_compaction_report.json"
    if context_path.exists():
        _collect_file_scan_payload(
            payloads["context_compaction_report"]["sources"],
            errors["context_compaction_report"],
            path=context_path,
            label=f"context_compaction_report:{entry.get('role')}",
        )


def _collect_export_scan_payloads(
    payloads: dict[str, dict[str, Any]],
    errors: dict[str, list[str]],
    *,
    input_payload: dict[str, Any],
) -> None:
    for ref_payload in _input_refs(input_payload, "export_root"):
        export_root = _resolve_file_ref(ref_payload)
        if not export_root.exists() or not export_root.is_dir():
            errors["sft_export"].append(f"export root missing or not a directory: {export_root}")
            errors["rl_export"].append(f"export root missing or not a directory: {export_root}")
            errors["preference_export"].append(f"export root missing or not a directory: {export_root}")
            continue
        manifest = _read_json_if_exists(export_root / "export_manifest.json")
        if not manifest:
            for surface in ("sft_export", "rl_export", "preference_export"):
                errors[surface].append(f"export_manifest.json missing or invalid: {export_root}")
            continue
        for export in manifest.get("format_exports", []):
            if not isinstance(export, dict):
                continue
            surface = _surface_for_export_format(str(export.get("format") or export.get("export_id") or ""))
            if surface is None:
                continue
            payloads[surface]["sources"].append(
                {
                    "source": _relative_path(export_root / "export_manifest.json", Path.cwd()),
                    "export_summary": _safe_scan_projection(export),
                }
            )
            for ref in _export_data_refs(export):
                _collect_export_ref_payload(
                    payloads[surface]["sources"],
                    errors[surface],
                    export_root=export_root,
                    ref_payload=ref,
                    surface=surface,
                )


def _input_refs(input_payload: dict[str, Any], category: str) -> list[dict[str, Any]]:
    refs = input_payload.get("input_refs_by_category", {}).get(category, [])
    return [ref for ref in refs if isinstance(ref, dict)]


def _surface_for_export_format(format_name: str) -> str | None:
    lowered = format_name.lower()
    if "preference" in lowered:
        return "preference_export"
    if "sft" in lowered or "supervised" in lowered:
        return "sft_export"
    if "rl" in lowered or "rollout" in lowered:
        return "rl_export"
    return None


def _export_data_refs(export: dict[str, Any]) -> list[dict[str, Any]]:
    refs = []
    for key in ("convenience_ref",):
        ref = export.get(key)
        if isinstance(ref, dict):
            refs.append(ref)
    refs.extend(ref for ref in export.get("data_file_refs", []) if isinstance(ref, dict))
    return refs


def _collect_export_ref_payload(
    sources: list[dict[str, Any]],
    errors: list[str],
    *,
    export_root: Path,
    ref_payload: dict[str, Any],
    surface: str,
) -> None:
    artifact_path = _artifact_path_for_scan(export_root, ref_payload, errors)
    if artifact_path is not None:
        payload = _read_file_payload_for_scan(artifact_path, errors)
        if payload is None:
            return
        sources.append(
            {
                "source": _relative_path(artifact_path, Path.cwd()),
                "label": "formal_training_payload",
                "payload": _safe_scan_projection(_project_export_payload_for_scan(surface, payload)),
            }
        )


def _project_export_payload_for_scan(surface: str, payload: Any) -> Any:
    if isinstance(payload, list):
        return [_project_export_row_for_scan(surface, row) for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        return _project_export_row_for_scan(surface, payload)
    return payload


def _project_export_row_for_scan(surface: str, row: dict[str, Any]) -> dict[str, Any]:
    projected: dict[str, Any] = {
        "sample_id": row.get("sample_id"),
        "task_id": row.get("task_id"),
        "filter_status": row.get("filter_status"),
        "invalid_for_training": row.get("invalid_for_training"),
        "metadata": _project_export_metadata_for_scan(row.get("metadata", {})),
    }
    payload = row.get("payload", {})
    if not isinstance(payload, dict):
        projected["payload"] = payload
        return projected
    if surface in {"sft_export", "rl_export"}:
        target = payload.get("target")
        projected["payload"] = {
            "messages": payload.get("messages"),
            "trainable_messages": payload.get("trainable_messages"),
            "loss_mask": payload.get("loss_mask"),
            "observation_mask": payload.get("observation_mask"),
            "target": (
                {"final_patch": target.get("final_patch")}
                if isinstance(target, dict)
                else target
            ),
        }
    elif surface == "preference_export":
        chosen = payload.get("chosen")
        rejected = payload.get("rejected")
        projected["payload"] = {
            "chosen": _project_preference_side_for_scan(chosen),
            "rejected": _project_preference_side_for_scan(rejected),
        }
    else:
        projected["payload"] = payload
    return projected


def _project_export_metadata_for_scan(metadata: Any) -> dict[str, Any]:
    if not isinstance(metadata, dict):
        return {}
    allowed = {
        "context_policy_version",
        "dataset_name",
        "dataset_split",
        "execution_mode",
        "export_format",
        "export_policy_version",
        "model_id",
        "permission_mode",
        "provider",
        "repo_base_commit",
        "scaffold_id",
        "scaffold_version",
        "source_archive_sha256",
        "source_tree_hash",
        "task_version",
        "tool_policy_version",
        "tool_schema_snapshot_hash",
    }
    return {key: metadata.get(key) for key in sorted(allowed) if key in metadata}


def _project_preference_side_for_scan(value: Any) -> Any:
    if isinstance(value, dict):
        return {"final_patch": value.get("final_patch")}
    return value


def _artifact_refs_by_kind(run_dir: Path, kind: str, errors: list[str]) -> list[dict[str, Any]]:
    manifest_path = run_dir / "artifacts.json"
    if not manifest_path.exists():
        return []
    manifest = _read_file_payload_for_scan(manifest_path, errors)
    if not isinstance(manifest, dict):
        return []
    refs = manifest.get("artifacts", [])
    if not isinstance(refs, list):
        errors.append(f"artifact manifest artifacts must be a list: {manifest_path}")
        return []
    return [
        ref
        for ref in refs
        if isinstance(ref, dict) and ref.get("kind") == kind
    ]


def _artifact_path_for_scan(base_dir: Path, ref_payload: dict[str, Any], errors: list[str]) -> Path | None:
    try:
        ref = ArtifactRef.model_validate(ref_payload)
    except ValidationError as exc:
        errors.append(f"artifact ref schema invalid: {exc}")
        return None
    path = _resolve_artifact_ref_path(ref, base_dir=base_dir)
    try:
        path.resolve().relative_to(base_dir.resolve())
    except ValueError:
        errors.append(f"artifact ref escapes base directory: {ref.relative_path}")
        return None
    if not path.exists() or not path.is_file():
        errors.append(f"artifact ref target missing: {ref.relative_path}")
        return None
    if _hash_path(path) != ref.sha256:
        errors.append(f"artifact ref sha256 mismatch: {ref.relative_path}")
    if path.stat().st_size != ref.size_bytes:
        errors.append(f"artifact ref size mismatch: {ref.relative_path}")
    return path


def _collect_file_scan_payload(
    sources: list[dict[str, Any]],
    errors: list[str],
    *,
    path: Path,
    label: str,
) -> None:
    payload = _read_file_payload_for_scan(path, errors)
    if payload is None:
        return
    sources.append(
        {
            "source": _relative_path(path, Path.cwd()),
            "label": label,
            "payload": _safe_scan_projection(payload),
        }
    )


def _read_jsonl_for_scan(path: Path, errors: list[str]) -> list[dict[str, Any]]:
    try:
        rows = read_jsonl(path)
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"jsonl read failed: {path}:{exc}")
        return []
    return [row for row in rows if isinstance(row, dict)]


def _read_file_payload_for_scan(path: Path, errors: list[str]) -> Any:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        errors.append(f"file read failed: {path}:{exc}")
        return None
    suffix = path.suffix.lower()
    if suffix == ".json":
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            errors.append(f"json read failed: {path}:{exc}")
            return None
    if suffix == ".jsonl":
        rows = []
        for index, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"jsonl read failed: {path}:{index}:{exc}")
                return None
            rows.append(row)
        return rows
    return text


def _append_scan_failures(failures: list[str], *, surface: str, payload: Any, label: str) -> None:
    result = V3ContaminationDenylist().scan_payload(surface=surface, payload=payload)
    if not result.clean:
        terms = ", ".join(sorted({finding.matched_term for finding in result.findings}))
        failures.append(f"{label} 包含 V3 污染项：{terms}")


def _scan_failures_from_results(results: list[dict[str, Any]]) -> list[str]:
    failures = []
    for result in results:
        source_errors = result.get("source_errors", [])
        if isinstance(source_errors, list) and source_errors:
            failures.append(f"{result.get('surface')}:source_errors:{len(source_errors)}")
        if result.get("clean") is not True:
            terms = ", ".join(
                sorted(
                    {
                        str(finding.get("matched_term"))
                        for finding in result.get("findings", [])
                        if isinstance(finding, dict)
                    }
                )
            )
            failures.append(f"{result.get('surface')}:contamination:{terms}")
    return failures


def _safe_scan_projection(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            _safe_scan_key(str(key)): (
                _safe_path_text(nested)
                if str(key) in {"path", "relative_path", "cwd", "source"} and isinstance(nested, str)
                else _safe_scan_projection(nested)
            )
            for key, nested in value.items()
        }
    if isinstance(value, list):
        return [_safe_scan_projection(item) for item in value]
    if isinstance(value, str):
        return _safe_path_text(value)
    return value


def _safe_scan_key(key: str) -> str:
    lowered = key.lower()
    if "run_outcome" in lowered:
        return "audit_control_label"
    return key


def _safe_path_text(text: str) -> str:
    cwd = Path.cwd().resolve().as_posix()
    if text.startswith(cwd + "/"):
        return text[len(cwd) + 1 :]
    for prefix in ("/Users/", "/private/", "/var/folders/"):
        if text.startswith(prefix):
            return "<REDACTED_PATH>/" + Path(text).name
    return text


def _inspect_run_metadata_refs(run_path: Path, metadata: dict[str, Any], failures: list[str]) -> None:
    ref = metadata.get("run_config_facts_ref")
    if isinstance(ref, dict):
        config_path = run_path / str(ref.get("relative_path", "run_config_facts.json"))
        if not config_path.exists():
            failures.append("run_metadata.json 引用的 run_config_facts.json 不存在。")
        elif ref.get("sha256") != sha256_file(config_path):
            failures.append("run_metadata.json 中的 run_config_facts_ref sha256 不匹配。")
    tool_ref = metadata.get("tool_protocol", {}).get("tool_schema_snapshot_ref")
    if isinstance(tool_ref, dict):
        _inspect_artifact_ref(run_path, tool_ref, failures, label="run_metadata.tool_schema_snapshot_ref")


def _is_interrupted_or_crashed(
    run_status: dict[str, Any],
    metrics: dict[str, Any],
    metadata: dict[str, Any],
) -> bool:
    values = {
        str(run_status.get("status", "")).lower(),
        str(metrics.get("run_outcome", "")).lower(),
        str(metadata.get("run_outcome", "")).lower(),
        str(metadata.get("run_status", "")).lower(),
    }
    return bool(values.intersection({"interrupted", "crashed", "corrupt_partial"}))


def _inspect_artifact_ref(root: Path, ref_payload: Any, failures: list[str], *, label: str) -> Path | None:
    if not isinstance(ref_payload, dict):
        failures.append(f"{label} 缺失或不是 object。")
        return None
    try:
        ref = ArtifactRef.model_validate(ref_payload)
    except ValidationError as exc:
        failures.append(f"{label} schema 无效：{exc}")
        return None
    relative = Path(ref.relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        failures.append(f"{label} relative_path 必须留在根目录内：{ref.relative_path}")
        return None
    path = root / relative
    if not path.exists():
        failures.append(f"{label} 路径不存在：{ref.relative_path}")
        return None
    actual_sha = _hash_path(path)
    if actual_sha != ref.sha256:
        failures.append(f"{label} sha256 不匹配：{ref.relative_path}")
    if not path.is_dir() and path.stat().st_size != ref.size_bytes:
        failures.append(f"{label} size_bytes 不匹配：{ref.relative_path}")
    return path


def _inspect_file_ref(ref_payload: Any, failures: list[str], *, label: str) -> Path | None:
    if not isinstance(ref_payload, dict):
        failures.append(f"{label} 缺失或不是 object。")
        return None
    for field in ("path", "sha256", "kind", "category"):
        if field not in ref_payload:
            failures.append(f"{label} 缺少字段：{field}")
            return None
    path = _resolve_file_ref(ref_payload)
    if not path.exists():
        failures.append(f"{label} 路径不存在：{ref_payload.get('path')}")
        return None
    actual_sha = _hash_path(path)
    if actual_sha != ref_payload.get("sha256"):
        failures.append(f"{label} sha256 不匹配：{ref_payload.get('path')}")
    if not path.is_dir() and path.stat().st_size != ref_payload.get("size_bytes"):
        failures.append(f"{label} size_bytes 不匹配：{ref_payload.get('path')}")
    return path


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


def _artifact_ref(
    path: Path,
    *,
    base_dir: Path,
    artifact_id: str,
    kind: str,
) -> dict[str, Any]:
    return ArtifactRef(
        artifact_id=artifact_id,
        relative_path=_relative_path(path, base_dir),
        kind=kind,
        sha256=_hash_path(path),
        size_bytes=0 if path.is_dir() else path.stat().st_size,
        redaction_status="not_required",
        retention_policy="keep",
    ).model_dump(mode="json")


def _append_command_log(
    path: Path,
    *,
    command_name: str,
    argv: list[str],
    started_at: str,
    input_paths: list[Path],
    output_paths: list[Path],
    self_referential_output_paths: list[Path] | None = None,
    self_referential_output_reason: str | None = None,
    base_dir: Path,
    exit_code: int,
) -> None:
    entry = CommandLogEntry(
        command_name=command_name,
        argv=argv,
        cwd=Path.cwd().as_posix(),
        input_refs=[
            ArtifactRef(
                artifact_id=f"{command_name}_input_{index}",
                relative_path=_relative_path(item, base_dir),
                kind=_kind_for_path(item),
                sha256=_hash_path(item),
                size_bytes=0 if item.is_dir() else item.stat().st_size,
                redaction_status="not_required",
                retention_policy="keep",
            )
            for index, item in enumerate(input_paths, start=1)
            if item.exists()
        ],
        output_refs=[
            ArtifactRef(
                artifact_id=f"{command_name}_output_{index}",
                relative_path=_relative_path(item, base_dir),
                kind=_kind_for_path(item),
                sha256=_hash_path(item),
                size_bytes=0 if item.is_dir() else item.stat().st_size,
                redaction_status="not_required",
                retention_policy="keep",
            )
            for index, item in enumerate(output_paths, start=1)
            if item.exists()
        ],
        self_referential_output_paths=[
            _relative_path(item, base_dir)
            for item in (self_referential_output_paths or [])
        ],
        self_referential_output_reason=self_referential_output_reason,
        exit_code=exit_code,
        tool_or_cli_version=f"repo-harness {__version__}",
        started_at=started_at,
        finished_at=_utc_timestamp(),
    )
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry.model_dump(mode="json"), ensure_ascii=False, sort_keys=True) + "\n")


def _resolve_file_ref(ref_payload: dict[str, Any]) -> Path:
    raw = str(ref_payload.get("path") or ref_payload.get("relative_path") or "")
    path = Path(raw)
    if path.is_absolute():
        return path
    return Path.cwd() / path


def _resolve_artifact_ref_path(ref: ArtifactRef, *, base_dir: Path) -> Path:
    relative = Path(ref.relative_path)
    if relative.is_absolute():
        return relative
    return base_dir / relative


def _hash_path(path: Path) -> str:
    return compute_source_tree_hash(path) if path.is_dir() else sha256_file(path)


def _kind_for_path(path: Path) -> str:
    if path.is_dir():
        return "directory"
    return path.suffix.lower().lstrip(".") or "file"


def _relative_path(path: Path, base_dir: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(base_dir.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def _stage_family_for_path(path: Path) -> str:
    text = path.as_posix()
    name = path.name
    if "/v3-" in text or name.startswith("v3") or "v3_stage" in text:
        return "v3"
    if "/v2-" in text or name.startswith("v2") or "v2_" in text:
        return "pre_v3"
    return "unknown"


def _infer_run_state(path: Path) -> str:
    status = _read_json_if_exists(path / "run_status.json") if path.is_dir() else {}
    metrics = _read_json_if_exists(path / "metrics.json") if path.is_dir() else {}
    report = _read_json_if_exists(path) if path.is_file() else {}
    return str(
        metrics.get("run_outcome")
        or status.get("status")
        or report.get("status")
        or "unknown"
    ).lower()


def _infer_skip_reason(path: Path) -> str | None:
    candidates = []
    if path.is_file():
        candidates.append(_read_json_if_exists(path))
    elif path.is_dir():
        for name in ("skip_report.json", "real_provider_smoke_report.json", "run_metadata.json"):
            if (path / name).exists():
                candidates.append(_read_json_if_exists(path / name))
    for payload in candidates:
        for key in ("structured_skip_reason", "skip_reason", "reason"):
            value = payload.get(key)
            status = str(payload.get("status", "")).lower()
            if isinstance(value, str) and value and ("skip" in status or "credential" in value.lower()):
                return value
    return None


def _parse_optional_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "accepted"}:
        return True
    if normalized in {"0", "false", "no", "rejected"}:
        return False
    raise ConfigError(f"布尔字段无法解析：{value}")


def _normalise_manifest_path(value: Any) -> str:
    path = Path(str(value))
    if path.is_absolute():
        try:
            return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
        except ValueError:
            return path.as_posix()
    return path.as_posix()


def _stable_json_sha256(payload: Any) -> str:
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    import hashlib

    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists() or path.is_dir():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_json_for_inspect(path: Path | None, failures: list[str]) -> dict[str, Any]:
    if path is None:
        failures.append("JSON 路径缺失。")
        return {}
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


def _read_jsonl_for_inspect(path: Path, failures: list[str]) -> list[dict[str, Any]]:
    try:
        return read_jsonl(path)
    except FileNotFoundError:
        failures.append(f"JSONL 文件不存在：{path}")
    except json.JSONDecodeError as exc:
        failures.append(f"JSONL 文件无效：{path}: {exc}")
    except OSError as exc:
        failures.append(f"JSONL 文件无法读取：{path}: {exc}")
    return []


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
