import json
from pathlib import Path

import pytest

from repo_harness.cli.main import main
from repo_harness.errors import ConfigError
from repo_harness.v4_tool_lifecycle import (
    build_v4_tool_lifecycle,
    inspect_v4_tool_contract,
    inspect_v4_tool_lifecycle,
)


def test_v4_tool_lifecycle_build_and_inspect_pass(tmp_path: Path) -> None:
    contract = build_v4_tool_lifecycle(output_dir=tmp_path / "tool")
    tool_dir = contract.parent

    assert "frozen" in inspect_v4_tool_contract(tool_dir, assert_frozen=True)
    assert "complete" in inspect_v4_tool_lifecycle(tool_dir, assert_complete=True)
    assert main(["inspect-v4-tool-contract", str(tool_dir), "--assert-frozen"]) == 0
    assert main(["inspect-v4-tool-lifecycle", str(tool_dir), "--assert-complete"]) == 0


def test_v4_tool_contract_rejects_missing_policy_refs(tmp_path: Path) -> None:
    tool_dir = _build(tmp_path)
    contract = tool_dir / "tool_contract_v4_snapshot.json"
    payload = _read_json(contract)
    payload.pop("permission_policy_snapshot_ref")
    _write_json(contract, payload)

    with pytest.raises(ConfigError, match="permission_policy_snapshot_ref"):
        inspect_v4_tool_contract(tool_dir, assert_frozen=True)


def test_v4_tool_contract_rejects_dynamic_mcp_discovery(tmp_path: Path) -> None:
    tool_dir = _build(tmp_path)
    contract = tool_dir / "tool_contract_v4_snapshot.json"
    payload = _read_json(contract)
    payload["mcp_enabled"] = True
    payload["dynamic_tool_discovery_allowed"] = True
    _write_json(contract, payload)

    with pytest.raises(ConfigError, match="mcp_enabled|dynamic_tool_discovery"):
        inspect_v4_tool_contract(tool_dir, assert_frozen=True)


def test_v4_tool_contract_rejects_tool_order_and_schema_drift(tmp_path: Path) -> None:
    tool_dir = _build(tmp_path)
    contract = tool_dir / "tool_contract_v4_snapshot.json"
    payload = _read_json(contract)
    payload["stable_tool_order"] = list(reversed(payload["stable_tool_order"]))
    payload["tool_schema_hash"] = "0" * 64
    _write_json(contract, payload)

    with pytest.raises(ConfigError, match="stable_tool_order|tool_schema_hash"):
        inspect_v4_tool_contract(tool_dir, assert_frozen=True)


def test_v4_tool_lifecycle_rejects_hook_entering_model_context_or_modifying_result(tmp_path: Path) -> None:
    tool_dir = _build(tmp_path)
    hook = tool_dir / "hook_audit_report.json"
    payload = _read_json(hook)
    payload["hook_audit_events"][0]["entered_prepared_messages"] = True
    payload["hook_audit_events"][0]["modified_tool_result"] = True
    payload["hook_audit_events"][0]["audit_only"] = False
    _write_json(hook, payload)

    with pytest.raises(ConfigError, match="prepared messages|改写 tool result|audit_only"):
        inspect_v4_tool_lifecycle(tool_dir, assert_complete=True)


def test_v4_tool_lifecycle_rejects_missing_hook_event_type_coverage(tmp_path: Path) -> None:
    tool_dir = _build(tmp_path)
    hook = tool_dir / "hook_audit_report.json"
    payload = _read_json(hook)
    payload["hook_audit_events"] = [event for event in payload["hook_audit_events"] if event["hook_event_type"] != "tool_error"]
    _write_json(hook, payload)

    with pytest.raises(ConfigError, match="hook event type"):
        inspect_v4_tool_lifecycle(tool_dir, assert_complete=True)


def test_v4_tool_lifecycle_rejects_unpaired_tool_result(tmp_path: Path) -> None:
    tool_dir = _build(tmp_path)
    trace = tool_dir / "tool_lifecycle_trace.jsonl"
    records = _read_jsonl(trace)
    records[0]["tool_result_pairing_status"] = "missing"
    records[0]["tool_result_id"] = ""
    _write_jsonl(trace, records)

    with pytest.raises(ConfigError, match="paired tool result|tool_result_id"):
        inspect_v4_tool_lifecycle(tool_dir, assert_complete=True)


def test_v4_tool_lifecycle_rejects_duplicate_tool_pair_ids(tmp_path: Path) -> None:
    tool_dir = _build(tmp_path)
    trace = tool_dir / "tool_lifecycle_trace.jsonl"
    records = _read_jsonl(trace)
    duplicate = dict(records[0])
    duplicate["event_id"] = "tool-call-duplicate"
    records.append(duplicate)
    _write_jsonl(trace, records)

    with pytest.raises(ConfigError, match="tool_call_id 重复|tool_result_id 重复"):
        inspect_v4_tool_lifecycle(tool_dir, assert_complete=True)


def test_v4_tool_lifecycle_rejects_permission_deny_executed_or_safety_reason_lost(tmp_path: Path) -> None:
    tool_dir = _build(tmp_path)
    trace = tool_dir / "permission_decision_trace.jsonl"
    records = _read_jsonl(trace)
    records[1]["executed_as_tool_call"] = True
    records[3]["safety_reason_preserved"] = False
    records[3]["reason"] = ""
    _write_jsonl(trace, records)

    with pytest.raises(ConfigError, match="非 allow decision|safety deny"):
        inspect_v4_tool_lifecycle(tool_dir, assert_complete=True)


def test_v4_tool_lifecycle_rejects_lifecycle_call_with_denied_permission(tmp_path: Path) -> None:
    tool_dir = _build(tmp_path)
    trace = tool_dir / "tool_lifecycle_trace.jsonl"
    records = _read_jsonl(trace)
    records[0]["permission_event_ref"] = "permission-deny-network-shell"
    records[0]["permission_decision_ref"] = "permission-deny-network-shell"
    records[0]["permission_decision"] = "deny"
    _write_jsonl(trace, records)

    with pytest.raises(ConfigError, match="只有 allow permission decision"):
        inspect_v4_tool_lifecycle(tool_dir, assert_complete=True)


def test_v4_tool_contract_rejects_mcp_snapshot_drift(tmp_path: Path) -> None:
    tool_dir = _build(tmp_path)
    mcp = tool_dir / "mcp_policy_snapshot.json"
    payload = _read_json(mcp)
    payload["stable_external_tool_surface_hash"] = "0" * 64
    payload["stable_tool_order"] = list(reversed(payload["stable_tool_order"]))
    payload["tool_schema_hash"] = "1" * 64
    payload["dynamic_tool_surface_freeze_status"] = "dynamic"
    _write_json(mcp, payload)

    with pytest.raises(ConfigError, match="mcp_policy_snapshot"):
        inspect_v4_tool_contract(tool_dir, assert_frozen=True)


def test_v4_tool_contract_rejects_contract_not_frozen(tmp_path: Path) -> None:
    tool_dir = _build(tmp_path)
    contract = tool_dir / "tool_contract_v4_snapshot.json"
    payload = _read_json(contract)
    payload["dynamic_tool_surface_freeze_status"] = "dynamic"
    _write_json(contract, payload)

    with pytest.raises(ConfigError, match="dynamic_tool_surface_freeze_status"):
        inspect_v4_tool_contract(tool_dir, assert_frozen=True)


def test_v4_tool_lifecycle_rejects_missing_permission_decision_coverage(tmp_path: Path) -> None:
    tool_dir = _build(tmp_path)
    trace = tool_dir / "permission_decision_trace.jsonl"
    records = [record for record in _read_jsonl(trace) if record["decision"] not in {"ask", "hook_deny"}]
    _write_jsonl(trace, records)

    with pytest.raises(ConfigError, match="缺少必需 decision 覆盖"):
        inspect_v4_tool_lifecycle(tool_dir, assert_complete=True)


def test_v4_tool_lifecycle_rejects_matched_rule_not_in_policy_snapshot(tmp_path: Path) -> None:
    tool_dir = _build(tmp_path)
    trace = tool_dir / "permission_decision_trace.jsonl"
    records = _read_jsonl(trace)
    records[2]["matched_rule"] = "missing_rule"
    _write_jsonl(trace, records)

    with pytest.raises(ConfigError, match="matched_rule"):
        inspect_v4_tool_lifecycle(tool_dir, assert_complete=True)


def test_v4_tool_lifecycle_rejects_matched_rule_reason_or_source_drift(tmp_path: Path) -> None:
    tool_dir = _build(tmp_path)
    trace = tool_dir / "permission_decision_trace.jsonl"
    records = _read_jsonl(trace)
    records[1]["reason"] = "wrong_reason"
    records[1]["rule_source"] = "runtime_override"
    _write_jsonl(trace, records)

    with pytest.raises(ConfigError, match="reason|rule_source"):
        inspect_v4_tool_lifecycle(tool_dir, assert_complete=True)


def test_v4_tool_lifecycle_rejects_empty_lifecycle_trace(tmp_path: Path) -> None:
    tool_dir = _build(tmp_path)
    (tool_dir / "tool_lifecycle_trace.jsonl").write_text("", encoding="utf-8")

    with pytest.raises(ConfigError, match="至少包含一条 tool call"):
        inspect_v4_tool_lifecycle(tool_dir, assert_complete=True)


def test_v4_tool_lifecycle_rejects_missing_minimum_audit_fields(tmp_path: Path) -> None:
    tool_dir = _build(tmp_path)
    permission_trace = tool_dir / "permission_decision_trace.jsonl"
    permission_records = _read_jsonl(permission_trace)
    permission_records[0].pop("run_id")
    permission_records[0].pop("decision_stage")
    permission_records[0].pop("headless_or_interactive")
    permission_records[0].pop("hook_override")
    permission_records[0].pop("content_safety_check")
    permission_records[0].pop("created_at")
    _write_jsonl(permission_trace, permission_records)
    lifecycle_trace = tool_dir / "tool_lifecycle_trace.jsonl"
    lifecycle_records = _read_jsonl(lifecycle_trace)
    lifecycle_records[0].pop("artifact_refs")
    lifecycle_records[0].pop("duration_ms")
    lifecycle_records[0].pop("permission_decision_ref")
    lifecycle_records[0].pop("hook_decision_ref")
    lifecycle_records[0].pop("error_type")
    _write_jsonl(lifecycle_trace, lifecycle_records)

    with pytest.raises(ConfigError, match="最低审计字段"):
        inspect_v4_tool_lifecycle(tool_dir, assert_complete=True)


def test_v4_tool_lifecycle_rejects_permission_or_hook_ref_drift(tmp_path: Path) -> None:
    tool_dir = _build(tmp_path)
    trace = tool_dir / "tool_lifecycle_trace.jsonl"
    records = _read_jsonl(trace)
    records[0]["permission_decision_ref"] = "permission-deny-network-shell"
    records[0]["hook_decision_ref"] = "hook-audit-after-tool-001"
    _write_jsonl(trace, records)

    with pytest.raises(ConfigError, match="permission_decision_ref|hook_decision_ref"):
        inspect_v4_tool_lifecycle(tool_dir, assert_complete=True)


def _build(tmp_path: Path) -> Path:
    return build_v4_tool_lifecycle(output_dir=tmp_path / "tool").parent


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
