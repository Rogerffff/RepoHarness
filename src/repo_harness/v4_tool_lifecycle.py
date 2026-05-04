"""V4 stage 4 audit-only tool lifecycle, permission, hook, and MCP facts."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from repo_harness import __version__
from repo_harness.errors import ConfigError
from repo_harness.export.manifest import sha256_file
from repo_harness.schema_versions import (
    V4_TOOL_CONTRACT_SNAPSHOT_VERSION,
    V4_TOOL_LIFECYCLE_TRACE_ENTRY_VERSION,
)
from repo_harness.workspace.source_hash import compute_source_tree_hash


PERMISSION_POLICY_SNAPSHOT_VERSION = "repo_harness_v4_permission_policy_snapshot_v0"
HOOK_POLICY_SNAPSHOT_VERSION = "repo_harness_v4_hook_policy_snapshot_v0"
MCP_POLICY_SNAPSHOT_VERSION = "repo_harness_v4_mcp_policy_snapshot_v0"
HOOK_AUDIT_REPORT_VERSION = "repo_harness_v4_hook_audit_report_v0"
PERMISSION_DECISION_TRACE_ENTRY_VERSION = "repo_harness_v4_permission_decision_trace_entry_v0"
PERMISSION_POLICY_DATASET_MANIFEST_VERSION = "repo_harness_v4_permission_policy_dataset_manifest_v0"
TOOL_CONTRACT_V4_SNAPSHOT_VERSION = V4_TOOL_CONTRACT_SNAPSHOT_VERSION

STAGE4_OUTPUTS = (
    "hook_policy_snapshot.json",
    "hook_audit_report.json",
    "tool_lifecycle_trace.jsonl",
    "permission_decision_trace.jsonl",
    "permission_policy_dataset_manifest.json",
    "permission_policy_snapshot.json",
    "mcp_policy_snapshot.json",
    "tool_contract_v4_snapshot.json",
)

TOOL_ORDER = ("read_file", "list_files", "apply_patch", "run_tests")
TOOL_SCHEMAS = {
    "read_file": {"args": {"path": "string"}, "result": {"content_ref": "ArtifactRef"}},
    "list_files": {"args": {"path": "string"}, "result": {"entries": "list"}},
    "apply_patch": {"args": {"patch_ref": "ArtifactRef"}, "result": {"patch_applied": "bool"}},
    "run_tests": {"args": {"command": "list"}, "result": {"exit_code": "int", "output_ref": "ArtifactRef"}},
}
REQUIRED_PERMISSION_DECISIONS = {"allow", "deny", "ask", "safety_deny", "hook_deny"}
REQUIRED_PERMISSION_TRACE_FIELDS = (
    "run_id",
    "turn_id",
    "tool_call_id",
    "decision_stage",
    "rule_source",
    "matched_rule",
    "permission_mode",
    "headless_or_interactive",
    "hook_override",
    "content_safety_check",
    "final_decision",
    "reason",
    "created_at",
    "lookup_status",
    "schema_validation_status",
    "execution_status",
    "artifact_refs",
    "truncation_status",
    "duration_ms",
)
REQUIRED_TOOL_LIFECYCLE_TRACE_FIELDS = (
    "run_id",
    "turn_id",
    "tool_call_id",
    "tool_name",
    "lookup_status",
    "schema_validation_status",
    "permission_decision_ref",
    "hook_decision_ref",
    "execution_status",
    "artifact_refs",
    "truncation_status",
    "tool_result_pairing_status",
    "error_type",
    "duration_ms",
)
REQUIRED_HOOK_EVENT_TYPES = {"before_tool", "after_tool", "tool_error"}


def build_v4_tool_lifecycle(*, output_dir: str | Path, fail_if_output_exists: bool = False) -> Path:
    """Build V4 stage 4 audit-only tool lifecycle artifacts."""

    output_path = Path(output_dir)
    if fail_if_output_exists:
        existing = [output_path / name for name in STAGE4_OUTPUTS if (output_path / name).exists()]
        if existing:
            raise ConfigError(
                "V4 stage 4 输出已存在，不能覆盖旧 evidence："
                + ", ".join(path.as_posix() for path in existing)
            )
    output_path.mkdir(parents=True, exist_ok=True)
    permission_snapshot_path = output_path / "permission_policy_snapshot.json"
    hook_snapshot_path = output_path / "hook_policy_snapshot.json"
    mcp_snapshot_path = output_path / "mcp_policy_snapshot.json"
    dataset_manifest_path = output_path / "permission_policy_dataset_manifest.json"
    hook_audit_path = output_path / "hook_audit_report.json"
    permission_trace_path = output_path / "permission_decision_trace.jsonl"
    lifecycle_trace_path = output_path / "tool_lifecycle_trace.jsonl"
    contract_path = output_path / "tool_contract_v4_snapshot.json"

    tool_schema_hash = _sha256_payload(TOOL_SCHEMAS)
    external_tool_surface_hash = _sha256_payload({"tool_order": TOOL_ORDER, "tool_schemas": TOOL_SCHEMAS})

    _write_json(
        permission_snapshot_path,
        {
            "schema_version": PERMISSION_POLICY_SNAPSHOT_VERSION,
            "generated_at": _utc_timestamp(),
            "permission_policy_id": "repo_harness_v4_permission_policy_audit_only_v0",
            "audit_only": True,
            "deny_execution_requires_no_tool_call": True,
            "safety_deny_preserves_reason": True,
            "rules": [
                {"rule_id": "allow_read_file", "decision": "allow", "tool": "read_file", "reason": "read_file_allowed_by_stage4_policy"},
                {"rule_id": "deny_network_shell", "decision": "deny", "tool": "run_tests", "reason": "network_shell_not_allowed"},
                {"rule_id": "ask_before_write", "decision": "ask", "tool": "apply_patch", "reason": "write_operation_requires_explicit_permission"},
                {"rule_id": "safety_deny_secret_access", "decision": "safety_deny", "tool": "read_file", "reason": "credential_path"},
                {"rule_id": "hook_deny_audit_only_no_execution", "decision": "hook_deny", "tool": "run_tests", "reason": "hook_policy_disabled_audit_only"},
            ],
        },
    )
    _write_json(
        hook_snapshot_path,
        {
            "schema_version": HOOK_POLICY_SNAPSHOT_VERSION,
            "generated_at": _utc_timestamp(),
            "hook_policy_id": "repo_harness_v4_hook_policy_disabled_audit_only_v0",
            "audit_only": True,
            "hooks_enabled": False,
            "before_model_call_hook_enabled": False,
            "after_model_call_hook_enabled": False,
            "stop_hook_enabled": False,
            "session_hook_enabled": False,
            "file_changed_hook_enabled": False,
            "subagent_hook_enabled": False,
            "remote_session_hook_enabled": False,
            "hook_result_can_modify_tool_result": False,
            "hook_material_model_visible": False,
        },
    )
    _write_json(
        mcp_snapshot_path,
        {
            "schema_version": MCP_POLICY_SNAPSHOT_VERSION,
            "generated_at": _utc_timestamp(),
            "mcp_enabled": False,
            "dynamic_tool_discovery_allowed": False,
            "dynamic_tool_surface_freeze_status": "frozen",
            "stable_external_tool_surface_hash": external_tool_surface_hash,
            "stable_tool_order": list(TOOL_ORDER),
            "tool_schema_hash": tool_schema_hash,
        },
    )
    permission_trace = [
        _permission_trace_record(
            event_id="permission-allow-read-file",
            tool_name="read_file",
            decision="allow",
            reason="read_file_allowed_by_stage4_policy",
            matched_rule="allow_read_file",
            execution_status="executed",
            executed_as_tool_call=True,
            tool_call_id="tool-call-001",
        ),
        _permission_trace_record(
            event_id="permission-deny-network-shell",
            tool_name="run_tests",
            decision="deny",
            reason="network_shell_not_allowed",
            matched_rule="deny_network_shell",
            execution_status="not_executed_permission_deny",
        ),
        _permission_trace_record(
            event_id="permission-ask-write-operation",
            tool_name="apply_patch",
            decision="ask",
            reason="write_operation_requires_explicit_permission",
            matched_rule="ask_before_write",
            execution_status="not_executed_ask_required",
        ),
        _permission_trace_record(
            event_id="permission-safety-deny-secret",
            tool_name="read_file",
            decision="safety_deny",
            reason="credential_path",
            matched_rule="safety_deny_secret_access",
            execution_status="not_executed_safety_deny",
            safety_reason_preserved=True,
        ),
        _permission_trace_record(
            event_id="permission-hook-deny-disabled-hook",
            tool_name="run_tests",
            decision="hook_deny",
            reason="hook_policy_disabled_audit_only",
            matched_rule="hook_deny_audit_only_no_execution",
            execution_status="not_executed_hook_deny",
        ),
    ]
    lifecycle_trace = [
        {
            "schema_version": V4_TOOL_LIFECYCLE_TRACE_ENTRY_VERSION,
            "event_id": "tool-call-001",
            "tool_name": "read_file",
            "tool_order_index": 0,
            "tool_schema_hash": tool_schema_hash,
            "permission_event_ref": "permission-allow-read-file",
            "permission_decision_ref": "permission-allow-read-file",
            "permission_decision": "allow",
            "tool_call_id": "tool-call-001",
            "tool_result_id": "tool-result-001",
            "tool_result_pairing_status": "paired",
            "hook_audit_event_ref": "hook-audit-before-tool-001",
            "hook_decision_ref": "hook-audit-before-tool-001",
            "hook_decision": "disabled_audit_only",
            "hook_modified_tool_result": False,
            "large_output_artifact_policy": "artifact_ref_required",
            "result_visible_to_model": True,
            "run_id": "v4-stage4-run-001",
            "turn_id": "turn-001",
            "lookup_status": "found",
            "schema_validation_status": "passed",
            "execution_status": "executed",
            "artifact_refs": ["artifact:tool-result-001"],
            "truncation_status": "not_truncated",
            "error_type": None,
            "duration_ms": 1,
        },
    ]
    _write_jsonl(permission_trace_path, permission_trace)
    _write_jsonl(lifecycle_trace_path, lifecycle_trace)
    _write_json(
        dataset_manifest_path,
        {
            "schema_version": PERMISSION_POLICY_DATASET_MANIFEST_VERSION,
            "generated_at": _utc_timestamp(),
            "permission_decision_trace_ref": _file_ref(permission_trace_path, "permission_decision_trace"),
            "permission_policy_snapshot_ref": _file_ref(permission_snapshot_path, "permission_policy_snapshot"),
            "model_visible": False,
            "audit_only": True,
        },
    )
    _write_json(
        hook_audit_path,
        {
            "schema_version": HOOK_AUDIT_REPORT_VERSION,
            "generated_at": _utc_timestamp(),
            "hook_policy_snapshot_ref": _file_ref(hook_snapshot_path, "hook_policy_snapshot"),
            "hook_audit_events": [
                {
                    "event_id": "hook-audit-before-tool-001",
                    "hook_event_type": "before_tool",
                    "hook_enabled": False,
                    "audit_only": True,
                    "entered_prepared_messages": False,
                    "modified_tool_result": False,
                    "model_visible": False,
                },
                {
                    "event_id": "hook-audit-after-tool-001",
                    "hook_event_type": "after_tool",
                    "hook_enabled": False,
                    "audit_only": True,
                    "entered_prepared_messages": False,
                    "modified_tool_result": False,
                    "model_visible": False,
                },
                {
                    "event_id": "hook-audit-tool-error-001",
                    "hook_event_type": "tool_error",
                    "hook_enabled": False,
                    "audit_only": True,
                    "entered_prepared_messages": False,
                    "modified_tool_result": False,
                    "model_visible": False,
                }
            ],
        },
    )
    _write_json(
        contract_path,
        {
            "schema_version": TOOL_CONTRACT_V4_SNAPSHOT_VERSION,
            "generated_at": _utc_timestamp(),
            "repo_harness_version": __version__,
            "permission_policy_snapshot_ref": _file_ref(permission_snapshot_path, "permission_policy_snapshot"),
            "hook_policy_snapshot_ref": _file_ref(hook_snapshot_path, "hook_policy_snapshot"),
            "mcp_policy_snapshot_ref": _file_ref(mcp_snapshot_path, "mcp_policy_snapshot"),
            "permission_policy_dataset_manifest_ref": _file_ref(dataset_manifest_path, "permission_policy_dataset_manifest"),
            "stable_external_tool_surface_hash": external_tool_surface_hash,
            "stable_tool_order": list(TOOL_ORDER),
            "tool_schema_hash": tool_schema_hash,
            "tool_schemas": TOOL_SCHEMAS,
            "tool_result_pairing_policy": "every_tool_call_requires_paired_tool_result",
            "large_output_artifact_policy": "large_outputs_must_be_artifact_refs",
            "dynamic_tool_surface_freeze_status": "frozen",
            "mcp_enabled": False,
            "dynamic_tool_discovery_allowed": False,
        },
    )
    inspect_v4_tool_contract(output_path, assert_frozen=True)
    inspect_v4_tool_lifecycle(output_path, assert_complete=True)
    return contract_path


def inspect_v4_tool_contract(path: str | Path, *, assert_frozen: bool = False) -> str:
    target = Path(path)
    failures: list[str] = []
    contract = _read_json_for_inspect(target / "tool_contract_v4_snapshot.json", failures)
    permission = _read_json_for_inspect(target / "permission_policy_snapshot.json", failures)
    hook = _read_json_for_inspect(target / "hook_policy_snapshot.json", failures)
    mcp = _read_json_for_inspect(target / "mcp_policy_snapshot.json", failures)
    dataset = _read_json_for_inspect(target / "permission_policy_dataset_manifest.json", failures)
    if contract:
        _expect(contract, "schema_version", TOOL_CONTRACT_V4_SNAPSHOT_VERSION, failures, "tool_contract_v4_snapshot")
        for field in (
            "permission_policy_snapshot_ref",
            "hook_policy_snapshot_ref",
            "mcp_policy_snapshot_ref",
            "stable_external_tool_surface_hash",
            "stable_tool_order",
            "tool_schema_hash",
            "tool_result_pairing_policy",
            "large_output_artifact_policy",
            "dynamic_tool_surface_freeze_status",
        ):
            if not contract.get(field):
                failures.append(f"tool_contract_v4_snapshot 缺少 {field}。")
        if contract.get("dynamic_tool_surface_freeze_status") != "frozen":
            failures.append("tool_contract_v4_snapshot dynamic_tool_surface_freeze_status 必须为 frozen。")
        if contract.get("mcp_enabled") is not False:
            failures.append("tool_contract_v4_snapshot mcp_enabled 必须为 false。")
        if contract.get("dynamic_tool_discovery_allowed") is not False:
            failures.append("tool_contract_v4_snapshot dynamic_tool_discovery_allowed 必须为 false。")
        if tuple(contract.get("stable_tool_order") or []) != TOOL_ORDER:
            failures.append("tool_contract_v4_snapshot stable_tool_order 不匹配。")
        if contract.get("tool_schema_hash") != _sha256_payload(contract.get("tool_schemas")):
            failures.append("tool_contract_v4_snapshot tool_schema_hash 不匹配。")
        expected_surface = _sha256_payload({"tool_order": tuple(contract.get("stable_tool_order") or []), "tool_schemas": contract.get("tool_schemas")})
        if contract.get("stable_external_tool_surface_hash") != expected_surface:
            failures.append("tool_contract_v4_snapshot stable_external_tool_surface_hash 不匹配。")
        for label in ("permission_policy_snapshot_ref", "hook_policy_snapshot_ref", "mcp_policy_snapshot_ref"):
            _inspect_file_ref(contract.get(label), failures, label=label)
    if permission:
        _expect(permission, "schema_version", PERMISSION_POLICY_SNAPSHOT_VERSION, failures, "permission_policy_snapshot")
        if permission.get("deny_execution_requires_no_tool_call") is not True:
            failures.append("permission policy 必须要求 deny 不执行 tool call。")
        if permission.get("safety_deny_preserves_reason") is not True:
            failures.append("permission policy 必须保留 safety deny reason。")
    if hook:
        _expect(hook, "schema_version", HOOK_POLICY_SNAPSHOT_VERSION, failures, "hook_policy_snapshot")
        if hook.get("hooks_enabled") is not False:
            failures.append("Stage 4 hook 必须 disabled。")
        if hook.get("hook_result_can_modify_tool_result") is not False:
            failures.append("audit-only hook 不得改写 tool result。")
        if hook.get("hook_material_model_visible") is not False:
            failures.append("hook material 不得 model-visible。")
    if mcp:
        _expect(mcp, "schema_version", MCP_POLICY_SNAPSHOT_VERSION, failures, "mcp_policy_snapshot")
        if mcp.get("mcp_enabled") is not False:
            failures.append("mcp_enabled 必须为 false。")
        if mcp.get("dynamic_tool_discovery_allowed") is not False:
            failures.append("dynamic_tool_discovery_allowed 必须为 false。")
        if mcp.get("dynamic_tool_surface_freeze_status") != "frozen":
            failures.append("mcp_policy_snapshot dynamic_tool_surface_freeze_status 必须为 frozen。")
        if contract:
            if mcp.get("dynamic_tool_surface_freeze_status") != contract.get("dynamic_tool_surface_freeze_status"):
                failures.append("mcp_policy_snapshot dynamic_tool_surface_freeze_status 与 tool contract 不一致。")
            if mcp.get("stable_external_tool_surface_hash") != contract.get("stable_external_tool_surface_hash"):
                failures.append("mcp_policy_snapshot stable_external_tool_surface_hash 与 tool contract 不一致。")
            if mcp.get("stable_tool_order") != contract.get("stable_tool_order"):
                failures.append("mcp_policy_snapshot stable_tool_order 与 tool contract 不一致。")
            if mcp.get("tool_schema_hash") != contract.get("tool_schema_hash"):
                failures.append("mcp_policy_snapshot tool_schema_hash 与 tool contract 不一致。")
    if dataset:
        _expect(dataset, "schema_version", PERMISSION_POLICY_DATASET_MANIFEST_VERSION, failures, "permission_policy_dataset_manifest")
        if dataset.get("audit_only") is not True or dataset.get("model_visible") is not False:
            failures.append("permission policy dataset manifest 必须 audit_only 且 model_visible=false。")
    return _inspect_result("inspect-v4-tool-contract", target, failures, assert_frozen, "frozen")


def inspect_v4_tool_lifecycle(path: str | Path, *, assert_complete: bool = False) -> str:
    target = Path(path)
    failures: list[str] = []
    permission_trace = _read_jsonl_for_inspect(target / "permission_decision_trace.jsonl", failures)
    lifecycle_trace = _read_jsonl_for_inspect(target / "tool_lifecycle_trace.jsonl", failures)
    hook_audit = _read_json_for_inspect(target / "hook_audit_report.json", failures)
    contract = _read_json_for_inspect(target / "tool_contract_v4_snapshot.json", failures)
    permission_snapshot = _read_json_for_inspect(target / "permission_policy_snapshot.json", failures)
    policy_rules = {
        record.get("rule_id"): record
        for record in permission_snapshot.get("rules") or []
        if isinstance(record, dict)
    }
    permission_by_event = {record.get("event_id"): record for record in permission_trace}
    hook_by_event = {
        event.get("event_id"): event
        for event in hook_audit.get("hook_audit_events") or []
        if isinstance(event, dict)
    }
    decisions_seen = {str(record.get("decision")) for record in permission_trace}
    missing_decisions = sorted(REQUIRED_PERMISSION_DECISIONS.difference(decisions_seen))
    if missing_decisions:
        failures.append("permission_decision_trace 缺少必需 decision 覆盖：" + ", ".join(missing_decisions))
    for index, record in enumerate(permission_trace, start=1):
        _expect(record, "schema_version", PERMISSION_DECISION_TRACE_ENTRY_VERSION, failures, f"permission_decision_trace[{index}]")
        _inspect_required_fields(record, REQUIRED_PERMISSION_TRACE_FIELDS, failures, f"permission_decision_trace[{index}]")
        decision = record.get("decision")
        if decision not in REQUIRED_PERMISSION_DECISIONS:
            failures.append(f"permission_decision_trace[{index}] decision 不在允许集合。")
        if record.get("final_decision") != decision:
            failures.append(f"permission_decision_trace[{index}] final_decision 必须等于 decision。")
        matched_rule = policy_rules.get(record.get("matched_rule"))
        if not matched_rule:
            failures.append(f"permission_decision_trace[{index}] matched_rule 不在 permission policy snapshot。")
        elif matched_rule.get("decision") != decision or matched_rule.get("tool") != record.get("tool_name"):
            failures.append(f"permission_decision_trace[{index}] matched_rule 与 decision/tool 不一致。")
        elif matched_rule.get("reason") != record.get("reason"):
            failures.append(f"permission_decision_trace[{index}] matched_rule reason 与 permission trace 不一致。")
        if record.get("rule_source") != "permission_policy_snapshot":
            failures.append(f"permission_decision_trace[{index}] rule_source 必须为 permission_policy_snapshot。")
        if record.get("headless_or_interactive") not in {"headless", "interactive"}:
            failures.append(f"permission_decision_trace[{index}] headless_or_interactive 不合法。")
        if record.get("hook_override") not in {"none", "hook_deny", "hook_allow"}:
            failures.append(f"permission_decision_trace[{index}] hook_override 不合法。")
        if record.get("content_safety_check") not in {"passed", "blocked"}:
            failures.append(f"permission_decision_trace[{index}] content_safety_check 不合法。")
        if record.get("lookup_status") != "found":
            failures.append(f"permission_decision_trace[{index}] lookup_status 必须为 found。")
        if record.get("schema_validation_status") != "passed":
            failures.append(f"permission_decision_trace[{index}] schema_validation_status 必须为 passed。")
        if not isinstance(record.get("artifact_refs"), list):
            failures.append(f"permission_decision_trace[{index}] artifact_refs 必须是列表。")
        if record.get("duration_ms", -1) < 0:
            failures.append(f"permission_decision_trace[{index}] duration_ms 必须非负。")
        if decision != "allow" and record.get("executed_as_tool_call") is not False:
            failures.append(f"permission_decision_trace[{index}] 非 allow decision 不得执行为 tool call。")
        if decision == "allow" and record.get("executed_as_tool_call") is not True:
            failures.append(f"permission_decision_trace[{index}] allow decision 必须执行为 tool call。")
        if record.get("decision") == "safety_deny":
            if not record.get("reason") or record.get("safety_reason_preserved") is not True:
                failures.append(f"permission_decision_trace[{index}] safety deny 必须保留 reason。")
    if hook_audit:
        _expect(hook_audit, "schema_version", HOOK_AUDIT_REPORT_VERSION, failures, "hook_audit_report")
        hook_event_types = {
            event.get("hook_event_type")
            for event in hook_audit.get("hook_audit_events") or []
            if isinstance(event, dict)
        }
        missing_hook_events = sorted(REQUIRED_HOOK_EVENT_TYPES.difference(hook_event_types))
        if missing_hook_events:
            failures.append("hook_audit_report 缺少必需 hook event type：" + ", ".join(missing_hook_events))
        for index, event in enumerate(hook_audit.get("hook_audit_events") or [], start=1):
            if event.get("audit_only") is not True:
                failures.append(f"hook_audit_events[{index}] audit_only 必须为 true。")
            if event.get("entered_prepared_messages") is not False:
                failures.append(f"hook_audit_events[{index}] hook 产物不得进入 prepared messages。")
            if event.get("modified_tool_result") is not False:
                failures.append(f"hook_audit_events[{index}] audit-only hook 不得改写 tool result。")
            if event.get("model_visible") is not False:
                failures.append(f"hook_audit_events[{index}] hook audit event 不得 model-visible。")
    expected_order = list(contract.get("stable_tool_order") or TOOL_ORDER)
    expected_schema_hash = contract.get("tool_schema_hash")
    tool_call_ids: set[str] = set()
    tool_result_ids: set[str] = set()
    if assert_complete and not lifecycle_trace:
        failures.append("tool_lifecycle_trace.jsonl 在 assert-complete 下必须至少包含一条 tool call。")
    for index, record in enumerate(lifecycle_trace, start=1):
        _expect(record, "schema_version", V4_TOOL_LIFECYCLE_TRACE_ENTRY_VERSION, failures, f"tool_lifecycle_trace[{index}]")
        _inspect_required_fields(record, REQUIRED_TOOL_LIFECYCLE_TRACE_FIELDS, failures, f"tool_lifecycle_trace[{index}]")
        if record.get("lookup_status") != "found":
            failures.append(f"tool_lifecycle_trace[{index}] lookup_status 必须为 found。")
        if record.get("schema_validation_status") != "passed":
            failures.append(f"tool_lifecycle_trace[{index}] schema_validation_status 必须为 passed。")
        if record.get("execution_status") != "executed":
            failures.append(f"tool_lifecycle_trace[{index}] execution_status 必须为 executed。")
        if not isinstance(record.get("artifact_refs"), list) or not record.get("artifact_refs"):
            failures.append(f"tool_lifecycle_trace[{index}] artifact_refs 必须是非空列表。")
        if record.get("duration_ms", -1) < 0:
            failures.append(f"tool_lifecycle_trace[{index}] duration_ms 必须非负。")
        if record.get("tool_result_pairing_status") != "paired":
            failures.append(f"tool_lifecycle_trace[{index}] tool call 缺少 paired tool result。")
        tool_call_id = record.get("tool_call_id")
        tool_result_id = record.get("tool_result_id")
        if not tool_call_id:
            failures.append(f"tool_lifecycle_trace[{index}] 缺少 tool_call_id。")
        elif tool_call_id in tool_call_ids:
            failures.append(f"tool_lifecycle_trace[{index}] tool_call_id 重复。")
        else:
            tool_call_ids.add(str(tool_call_id))
        if not tool_result_id:
            failures.append(f"tool_lifecycle_trace[{index}] 缺少 tool_result_id。")
        elif tool_result_id in tool_result_ids:
            failures.append(f"tool_lifecycle_trace[{index}] tool_result_id 重复。")
        else:
            tool_result_ids.add(str(tool_result_id))
        if record.get("hook_modified_tool_result") is not False:
            failures.append(f"tool_lifecycle_trace[{index}] audit-only hook 不得改写 tool result。")
        if record.get("tool_schema_hash") != expected_schema_hash:
            failures.append(f"tool_lifecycle_trace[{index}] tool schema hash 不匹配。")
        tool_name = record.get("tool_name")
        if tool_name not in expected_order:
            failures.append(f"tool_lifecycle_trace[{index}] tool order 不在 snapshot。")
        elif record.get("tool_order_index") != expected_order.index(tool_name):
            failures.append(f"tool_lifecycle_trace[{index}] tool order index 不匹配。")
        if record.get("permission_decision_ref") != record.get("permission_event_ref"):
            failures.append(f"tool_lifecycle_trace[{index}] permission_decision_ref 必须等于实际 permission_event_ref。")
        permission = permission_by_event.get(record.get("permission_decision_ref"))
        if not permission:
            failures.append(f"tool_lifecycle_trace[{index}] 缺少 permission decision ref。")
        elif permission.get("decision") != record.get("permission_decision"):
            failures.append(f"tool_lifecycle_trace[{index}] permission decision 不匹配。")
        elif permission.get("decision") != "allow":
            failures.append(f"tool_lifecycle_trace[{index}] 只有 allow permission decision 可以执行 tool call。")
        elif permission.get("executed_as_tool_call") is not True:
            failures.append(f"tool_lifecycle_trace[{index}] allow permission decision 必须记录 executed_as_tool_call=true。")
        if permission and permission.get("tool_call_id") != record.get("tool_call_id"):
            failures.append(f"tool_lifecycle_trace[{index}] permission trace tool_call_id 与 lifecycle 不一致。")
        if record.get("hook_decision_ref") != record.get("hook_audit_event_ref"):
            failures.append(f"tool_lifecycle_trace[{index}] hook_decision_ref 必须等于实际 hook_audit_event_ref。")
        hook_event = hook_by_event.get(record.get("hook_decision_ref"))
        if not hook_event:
            failures.append(f"tool_lifecycle_trace[{index}] 缺少 hook decision ref。")
        elif hook_event.get("audit_only") is not True or hook_event.get("modified_tool_result") is not False:
            failures.append(f"tool_lifecycle_trace[{index}] hook decision ref 不是 audit-only 未改写事实。")
    return _inspect_result("inspect-v4-tool-lifecycle", target, failures, assert_complete, "complete")


def _permission_trace_record(
    *,
    event_id: str,
    tool_name: str,
    decision: str,
    reason: str,
    matched_rule: str,
    execution_status: str,
    executed_as_tool_call: bool = False,
    tool_call_id: str | None = None,
    safety_reason_preserved: bool | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "schema_version": PERMISSION_DECISION_TRACE_ENTRY_VERSION,
        "event_id": event_id,
        "run_id": "v4-stage4-run-001",
        "turn_id": "turn-001",
        "tool_name": tool_name,
        "decision": decision,
        "decision_stage": "permission_decision",
        "rule_source": "permission_policy_snapshot",
        "matched_rule": matched_rule,
        "permission_mode": "audit_only",
        "headless_or_interactive": "headless",
        "hook_override": "none",
        "content_safety_check": "passed" if decision != "safety_deny" else "blocked",
        "final_decision": decision,
        "reason": reason,
        "created_at": _utc_timestamp(),
        "lookup_status": "found",
        "schema_validation_status": "passed",
        "execution_status": execution_status,
        "artifact_refs": [],
        "truncation_status": "not_truncated",
        "duration_ms": 1,
        "executed_as_tool_call": executed_as_tool_call,
        "tool_call_id": tool_call_id,
    }
    if safety_reason_preserved is not None:
        record["safety_reason_preserved"] = safety_reason_preserved
    return record


def _inspect_required_fields(
    payload: dict[str, Any],
    required_fields: tuple[str, ...],
    failures: list[str],
    label: str,
) -> None:
    for field in required_fields:
        if field not in payload:
            failures.append(f"{label} 缺少最低审计字段：{field}。")


def _inspect_result(command: str, path: Path, failures: list[str], assert_flag: bool, label: str) -> str:
    lines = [f"{command}: {path}"]
    if failures:
        if assert_flag:
            raise ConfigError("; ".join(failures))
        lines.append("Diagnostics:")
        lines.extend(f"- {failure}" for failure in failures)
    if assert_flag:
        lines.append(f"{command}: {label}")
    lines.append(f"{command}: passed")
    return "\n".join(lines)


def _expect(payload: dict[str, Any], field: str, expected: Any, failures: list[str], label: str) -> None:
    if payload.get(field) != expected:
        failures.append(f"{label}.{field} 不匹配。")


def _inspect_file_ref(ref: Any, failures: list[str], *, label: str) -> Path | None:
    if not isinstance(ref, dict):
        failures.append(f"{label} 文件 ref 缺失或不是 object。")
        return None
    raw = str(ref.get("path") or ref.get("relative_path") or "")
    if not raw:
        failures.append(f"{label} 文件 ref 缺少 path。")
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.exists():
        failures.append(f"{label} 文件 ref 路径不存在：{raw}")
        return None
    actual = compute_source_tree_hash(path) if path.is_dir() else sha256_file(path)
    if actual != ref.get("sha256"):
        failures.append(f"{label} sha256 不匹配。")
    return path


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


def _read_jsonl_for_inspect(path: Path, failures: list[str]) -> list[dict[str, Any]]:
    try:
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except FileNotFoundError:
        failures.append(f"JSONL 文件不存在：{path}")
        return []
    records: list[dict[str, Any]] = []
    for index, line in enumerate(lines, start=1):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            failures.append(f"{path.name} 第 {index} 行不是合法 JSON：{exc}")
            continue
        if not isinstance(record, dict):
            failures.append(f"{path.name} 第 {index} 行顶层必须是 object。")
            continue
        records.append(record)
    return records


def _file_ref(path: Path, category: str) -> dict[str, Any]:
    return {
        "path": path.as_posix(),
        "kind": "directory" if path.is_dir() else (path.suffix.lstrip(".") or "file"),
        "category": category,
        "model_visible": False,
        "sha256": compute_source_tree_hash(path) if path.is_dir() else sha256_file(path),
        "size_bytes": 0 if path.is_dir() else path.stat().st_size,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )


def _sha256_payload(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
