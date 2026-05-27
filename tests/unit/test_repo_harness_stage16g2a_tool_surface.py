import json
import hashlib
from pathlib import Path

import pytest

from repo_harness.permissions import PermissionContext
from repo_harness.scaffolds import build_planner_coder_verifier_scaffold, build_simple_react_scaffold
from repo_harness.stage16g2_file_surface import (
    STAGE16G2A_CORE_VISIBLE_NEW_TOOL_NAMES,
    STAGE16G2A_NEW_TOOL_NAMES,
    STAGE16G2A_STANDALONE_OPERATION_TOOL_NAMES,
    _scan_public_files,
    build_profile_delta_report,
    build_schema_registration_report,
    inspect_stage16g2a_tool_surface,
    write_stage16g2a_reports,
)
from repo_harness.tools import DEFAULT_TOOL_ORDER, ToolExecutionContext, ToolExecutor, ToolRegistry, build_tool
from repo_harness.tools.schemas import ToolCall
from repo_harness.trajectory import RunRecorder
from repo_harness.workspace import DependencyState, LocalWorkspaceAdapter, RunWorkspace


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def _refresh_summary_digest(output_dir: Path, filename: str, digest_field: str) -> Path:
    summary_path = output_dir / "stage16g2a_acceptance_summary.json"
    summary = json.loads(summary_path.read_text())
    summary[digest_field] = _sha256_file(output_dir / filename)
    _write_json(summary_path, summary)
    return summary_path


def test_stage16g2a_new_tools_are_registered_schema_only() -> None:
    report = build_schema_registration_report()
    records = {record["tool_name"]: record for record in report["tool_records"]}

    assert report["all_new_tools_buildable"] is True
    assert report["all_core_new_tools_in_default_tool_order"] is True
    assert report["standalone_operation_tools_not_in_default_tool_order"] is True
    assert report["core_write_file_upsert_exposed"] is False
    assert report["apply_patch_unified_diff_exposed"] is False
    assert report["apply_patch_operations_support_reason"] is True
    assert report["standalone_delete_move_require_reason"] is True

    for tool_name in STAGE16G2A_NEW_TOOL_NAMES:
        tool = build_tool(tool_name)
        assert tool.is_destructive is True
        assert records[tool_name]["executor_binding_status"] == "schema_only_denial_until_16G2B"
    for tool_name in STAGE16G2A_CORE_VISIBLE_NEW_TOOL_NAMES:
        assert tool_name in DEFAULT_TOOL_ORDER
    for tool_name in STAGE16G2A_STANDALONE_OPERATION_TOOL_NAMES:
        assert tool_name not in DEFAULT_TOOL_ORDER

    write_file = build_tool("write_file")
    assert write_file.input_schema["properties"]["mode"]["enum"] == ["create", "overwrite"]
    assert "upsert" not in write_file.input_schema["properties"]["mode"]["enum"]
    apply_patch = build_tool("apply_patch")
    assert "unified_diff" not in apply_patch.input_schema["properties"]
    assert apply_patch.input_schema["properties"]["operations"]["maxItems"] == 50
    assert "reason" in apply_patch.input_schema["properties"]["operations"]["items"]["properties"]
    assert "reason" in build_tool("delete_file").input_schema["required"]
    assert "reason" in build_tool("move_file").input_schema["required"]


def test_stage16g2a_scaffolds_expose_new_tools_only_to_write_phases() -> None:
    simple = build_simple_react_scaffold()
    planner = build_planner_coder_verifier_scaffold()

    assert all(tool in simple.allowed_tools for tool in STAGE16G2A_CORE_VISIBLE_NEW_TOOL_NAMES)
    assert not any(tool in simple.allowed_tools for tool in STAGE16G2A_STANDALONE_OPERATION_TOOL_NAMES)
    assert not any(tool in planner.allowed_tools_for_phase("planner") for tool in STAGE16G2A_NEW_TOOL_NAMES)
    assert not any(tool in planner.allowed_tools_for_phase("verifier") for tool in STAGE16G2A_NEW_TOOL_NAMES)
    assert all(tool in planner.allowed_tools_for_phase("coder") for tool in STAGE16G2A_CORE_VISIBLE_NEW_TOOL_NAMES)
    assert all(tool in planner.allowed_tools_for_phase("repair") for tool in STAGE16G2A_CORE_VISIBLE_NEW_TOOL_NAMES)
    assert not any(tool in planner.allowed_tools_for_phase("coder") for tool in STAGE16G2A_STANDALONE_OPERATION_TOOL_NAMES)
    assert not any(tool in planner.allowed_tools_for_phase("repair") for tool in STAGE16G2A_STANDALONE_OPERATION_TOOL_NAMES)


@pytest.mark.parametrize(
    ("tool_name", "arguments"),
    [
        (
            "write_file",
            {
                "path": "notes.txt",
                "content": "changed\n",
                "mode": "overwrite",
                "expected_content_hash": "not-used-in-16g2a",
            },
        ),
        (
            "apply_patch",
            {
                "operations": [
                    {
                        "op": "replace_text",
                        "path": "notes.txt",
                        "old_text": "original",
                        "new_text": "changed",
                        "expected_content_hash": "not-used-in-16g2a",
                    }
                ],
            },
        ),
        (
            "delete_file",
            {
                "path": "notes.txt",
                "expected_content_hash": "not-used-in-16g2a",
                "reason": "Remove obsolete implementation after migration.",
            },
        ),
        (
            "move_file",
            {
                "source_path": "notes.txt",
                "target_path": "renamed.txt",
                "expected_source_hash": "not-used-in-16g2a",
                "reason": "Rename file to match the new module name.",
            },
        ),
        ("mkdir", {"path": "new_dir"}),
    ],
)
def test_stage16g2a_executor_returns_safe_schema_only_denial(
    tmp_path: Path,
    tool_name: str,
    arguments: dict[str, object],
) -> None:
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    (workspace / "notes.txt").write_text("original\n", encoding="utf-8")
    registry = ToolRegistry([build_tool(tool_name)]) if tool_name in STAGE16G2A_STANDALONE_OPERATION_TOOL_NAMES else None
    executor = ToolExecutor(registry=registry) if registry is not None else ToolExecutor()
    before_files = sorted(path.relative_to(workspace).as_posix() for path in workspace.rglob("*"))

    result = executor.execute(
        ToolCall(
            tool_call_id=f"call_{tool_name}_schema_only",
            tool_name=tool_name,
            arguments=arguments,
            turn=1,
        ),
        context,
    )

    assert result.status == "denied"
    assert result.error_type == "stage16g2a_behavior_not_enabled"
    assert result.typed["repository_mutation_performed"] is False
    assert result.typed["next_required_stage"] == "16G.2B"
    assert (workspace / "notes.txt").read_text(encoding="utf-8") == "original\n"
    after_files = sorted(path.relative_to(workspace).as_posix() for path in workspace.rglob("*"))
    assert after_files == before_files


def test_stage16g2a_schema_validation_rejects_upsert_and_empty_patch(tmp_path: Path) -> None:
    context = _tool_context(tmp_path)
    executor = ToolExecutor()

    upsert = executor.validate_input(
        ToolCall(
            tool_call_id="call_upsert",
            tool_name="write_file",
            arguments={"path": "notes.txt", "content": "x", "mode": "upsert"},
            turn=1,
        ),
        context,
    )
    empty_patch = executor.validate_input(
        ToolCall(
            tool_call_id="call_empty_patch",
            tool_name="apply_patch",
            arguments={"operations": []},
            turn=1,
        ),
        context,
    )

    assert upsert is not None
    assert upsert.typed["field"] == "mode"
    assert upsert.typed["expected_type"] == "create|overwrite"
    assert empty_patch is not None
    assert empty_patch.typed["field"] == "operations"
    assert empty_patch.typed["expected_type"] == "non-empty array"


@pytest.mark.parametrize(
    ("operation", "expected_field", "expected_type"),
    [
        (
            {
                "op": "replace_text",
                "path": "notes.txt",
                "old_text": "a",
                "new_text": "b",
                "expected_content_hash": "h",
                "unified_diff": "---",
            },
            "operations[0].unified_diff",
            "known field",
        ),
        (
            {
                "op": "mkdir",
                "path": "new_dir",
                "command": "rm -rf .",
            },
            "operations[0].command",
            "known field",
        ),
        (
            {"op": "write_file", "content": "x", "mode": "create"},
            "operations[0].path",
            "required field",
        ),
        (
            {"op": "write_file", "path": "notes.txt", "content": "x", "mode": "upsert"},
            "operations[0].mode",
            "create|overwrite",
        ),
        (
            {"op": "write_file", "path": "notes.txt", "content": "x", "mode": "overwrite"},
            "operations[0].expected_content_hash",
            "string required for overwrite",
        ),
        (
            {"op": "delete_file", "path": "notes.txt", "expected_content_hash": "h"},
            "operations[0].reason",
            "required field",
        ),
        (
            {
                "op": "move_file",
                "source_path": "notes.txt",
                "target_path": "renamed.txt",
                "expected_source_hash": "h",
            },
            "operations[0].reason",
            "required field",
        ),
        (
            {"op": "replace_text", "path": "notes.txt", "old_text": "a", "new_text": "b"},
            "operations[0].expected_content_hash",
            "required field",
        ),
    ],
)
def test_stage16g2a_apply_patch_nested_schema_rejects_unsafe_operations(
    tmp_path: Path,
    operation: dict[str, object],
    expected_field: str,
    expected_type: str,
) -> None:
    context = _tool_context(tmp_path)
    result = ToolExecutor().validate_input(
        ToolCall(
            tool_call_id="call_bad_nested_patch",
            tool_name="apply_patch",
            arguments={"operations": [operation]},
            turn=1,
        ),
        context,
    )

    assert result is not None
    assert result.typed["field"] == expected_field
    assert result.typed["expected_type"] == expected_type


def test_stage16g2a_apply_patch_nested_schema_rejects_limits(tmp_path: Path) -> None:
    context = _tool_context(tmp_path)
    too_many = ToolExecutor().validate_input(
        ToolCall(
            tool_call_id="call_too_many_operations",
            tool_name="apply_patch",
            arguments={"operations": [{"op": "mkdir", "path": f"dir_{index}"} for index in range(51)]},
            turn=1,
        ),
        context,
    )
    too_long = ToolExecutor().validate_input(
        ToolCall(
            tool_call_id="call_path_too_long",
            tool_name="apply_patch",
            arguments={"operations": [{"op": "mkdir", "path": "x" * 1025}]},
            turn=1,
        ),
        context,
    )

    assert too_many is not None
    assert too_many.typed["field"] == "operations"
    assert too_many.typed["expected_type"] == "array length <= 50"
    assert too_long is not None
    assert too_long.typed["field"] == "operations[0].path"
    assert too_long.typed["expected_type"] == "string length <= 1024"


def test_stage16g2a_permission_checks_apply_patch_nested_paths(tmp_path: Path) -> None:
    context = _tool_context(tmp_path)
    executor = ToolExecutor()
    decision = executor.check_permission(
        ToolCall(
            tool_call_id="call_apply_patch_escape",
            tool_name="apply_patch",
            arguments={
                "operations": [
                    {
                        "op": "delete_file",
                        "path": "../outside.txt",
                        "expected_content_hash": "h",
                        "reason": "Probe should be denied before any mutation behavior is enabled.",
                    }
                ]
            },
            turn=1,
        ),
        context,
    )

    assert decision.decision == "deny"
    assert decision.matched_rule == "workspace_boundary_or_sensitive_path"


def test_stage16g2a_profile_delta_keeps_new_tools_out_of_policy_loss() -> None:
    report = build_profile_delta_report()
    profiles = {profile["profile_id"]: profile for profile in report["profiles"]}

    assert report["swe_public_core_excludes_persistent_shell"] is True
    assert report["swe_public_core_contains_core_new_tools"] is True
    assert report["swe_public_core_excludes_standalone_operation_tools"] is True
    assert report["swe_public_extended_contains_standalone_operation_tools"] is True
    assert "diagnostic_shell" not in profiles["swe_public_core"]["stage16g2a_tool_names"]
    assert "execute_bash" not in profiles["swe_public_core"]["stage16g2a_tool_names"]
    assert all(tool in profiles["swe_public_core"]["stage16g2a_tool_names"] for tool in STAGE16G2A_CORE_VISIBLE_NEW_TOOL_NAMES)
    assert not any(
        tool in profiles["swe_public_core"]["stage16g2a_tool_names"]
        for tool in STAGE16G2A_STANDALONE_OPERATION_TOOL_NAMES
    )
    assert all(
        tool in profiles["swe_public_extended"]["stage16g2a_tool_names"]
        for tool in STAGE16G2A_STANDALONE_OPERATION_TOOL_NAMES
    )

    for profile in profiles.values():
        for state in profile["training_projection_state_for_new_tools"].values():
            assert state["executor_binding_status"] == "schema_only_denial_until_16G2B"
            assert state["allowed_in_policy_loss_trajectory"] is False


def test_stage16g2a_writer_outputs_public_safe_evidence_and_inspector(tmp_path: Path) -> None:
    digests = write_stage16g2a_reports(output_dir=tmp_path)

    expected = {
        "implementation-notes.md",
        "stage16g2a_source_inventory.json",
        "stage16g2a_stage16g1_preflight_report.json",
        "stage16g2a_schema_registration_report.json",
        "stage16g2a_scaffold_exposure_report.json",
        "stage16g2a_tool_surface_delta.json",
        "stage16g2a_profile_delta_report.json",
        "stage16g2a_path_leak_scan_report.json",
        "stage16g2a_acceptance_summary.json",
    }
    assert expected.issubset(digests)

    summary = json.loads((tmp_path / "stage16g2a_acceptance_summary.json").read_text())
    assert summary["status"] == "passed"
    assert summary["stage16g2a_complete"] is True
    assert summary["stage16g2b_allowed_to_start"] is True
    assert summary["stage16g3_allowed_to_start"] is False
    assert summary["stage17b_real_data_freeze_allowed"] is False
    assert summary["stage16g1_preflight_inspection_passed"] is True
    assert summary["failure_count"] == 0

    cli_report = json.loads(
        inspect_stage16g2a_tool_surface(
            tmp_path / "stage16g2a_acceptance_summary.json",
            assert_complete=True,
        )
    )
    assert cli_report["status"] == "passed"


def test_stage16g2a_inspector_rescans_current_public_evidence(tmp_path: Path) -> None:
    write_stage16g2a_reports(output_dir=tmp_path)
    summary_path = tmp_path / "stage16g2a_acceptance_summary.json"
    summary = json.loads(summary_path.read_text())
    summary["tampered_local_path"] = "/Users/example/secret"
    summary_path.write_text(json.dumps(summary, indent=2))

    with pytest.raises(Exception) as exc_info:
        inspect_stage16g2a_tool_surface(summary_path, assert_complete=True)
    report = json.loads(str(exc_info.value))
    assert "public_path_leak_scan_failed" in report["failures"]
    assert "path_leak_scan_report_stale_or_mismatched" in report["failures"]
    assert "acceptance_summary_unexpected_field:tampered_local_path" in report["failures"]


def test_stage16g2a_inspector_rejects_source_inventory_tamper_even_if_digest_updated(tmp_path: Path) -> None:
    write_stage16g2a_reports(output_dir=tmp_path)
    inventory_path = tmp_path / "stage16g2a_source_inventory.json"
    inventory = json.loads(inventory_path.read_text())
    inventory["source_inputs"] = []
    _write_json(inventory_path, inventory)
    summary_path = _refresh_summary_digest(
        tmp_path,
        "stage16g2a_source_inventory.json",
        "source_inventory_sha256",
    )

    with pytest.raises(Exception) as exc_info:
        inspect_stage16g2a_tool_surface(summary_path, assert_complete=True)
    report = json.loads(str(exc_info.value))
    assert "source_inventory_input_names_mismatch" in report["failures"]
    assert "source_inventory_missing_input:stage16g1_tool_registry_contract.json" in report["failures"]


def test_stage16g2a_inspector_rebuilds_scaffold_report_instead_of_trusting_flags(tmp_path: Path) -> None:
    write_stage16g2a_reports(output_dir=tmp_path)
    scaffold_path = tmp_path / "stage16g2a_scaffold_exposure_report.json"
    scaffold = json.loads(scaffold_path.read_text())
    scaffold["simple_react_allowed_tools"].remove("write_file")
    scaffold["planner_coder_verifier_phase_allowed_tools"]["planner"].append("write_file")
    assert scaffold["simple_react_exposes_core_new_tools"] is True
    assert scaffold["planner_exposes_write_tools"] is False
    _write_json(scaffold_path, scaffold)
    summary_path = _refresh_summary_digest(
        tmp_path,
        "stage16g2a_scaffold_exposure_report.json",
        "scaffold_exposure_report_sha256",
    )

    with pytest.raises(Exception) as exc_info:
        inspect_stage16g2a_tool_surface(summary_path, assert_complete=True)
    report = json.loads(str(exc_info.value))
    assert "scaffold_exposure_report_stale_or_mismatched" in report["failures"]


def test_stage16g2a_inspector_rebuilds_schema_report_instead_of_trusting_flags(tmp_path: Path) -> None:
    write_stage16g2a_reports(output_dir=tmp_path)
    schema_path = tmp_path / "stage16g2a_schema_registration_report.json"
    schema = json.loads(schema_path.read_text())
    records = {record["tool_name"]: record for record in schema["tool_records"]}
    records["write_file"]["mode_enum"].append("upsert")
    assert schema["core_write_file_upsert_exposed"] is False
    _write_json(schema_path, schema)
    summary_path = _refresh_summary_digest(
        tmp_path,
        "stage16g2a_schema_registration_report.json",
        "schema_registration_report_sha256",
    )

    with pytest.raises(Exception) as exc_info:
        inspect_stage16g2a_tool_surface(summary_path, assert_complete=True)
    report = json.loads(str(exc_info.value))
    assert "schema_registration_report_stale_or_mismatched" in report["failures"]


def test_stage16g2a_inspector_rebuilds_profile_report_instead_of_trusting_flags(tmp_path: Path) -> None:
    write_stage16g2a_reports(output_dir=tmp_path)
    profile_path = tmp_path / "stage16g2a_profile_delta_report.json"
    profile = json.loads(profile_path.read_text())
    profiles = {record["profile_id"]: record for record in profile["profiles"]}
    profiles["swe_public_core"]["stage16g2a_tool_names"].remove("write_file")
    assert profile["swe_public_core_contains_core_new_tools"] is True
    _write_json(profile_path, profile)
    summary_path = _refresh_summary_digest(
        tmp_path,
        "stage16g2a_profile_delta_report.json",
        "profile_delta_report_sha256",
    )

    with pytest.raises(Exception) as exc_info:
        inspect_stage16g2a_tool_surface(summary_path, assert_complete=True)
    report = json.loads(str(exc_info.value))
    assert "profile_delta_report_stale_or_mismatched" in report["failures"]


def test_stage16g2a_public_scan_rejects_common_secret_tokens(tmp_path: Path) -> None:
    (tmp_path / "stage16g2a_token_probe.json").write_text(
        json.dumps({"token": "sk-testtoken1234567890"}),
    )

    report = _scan_public_files(tmp_path)
    assert report["public_path_leak_scan_passed"] is False
    assert report["finding_count"] == 1


def _tool_context(tmp_path: Path) -> ToolExecutionContext:
    run_dir = tmp_path / "run"
    workspace = run_dir / "workspaces" / "agent_workspace"
    workspace.mkdir(parents=True)
    recorder = RunRecorder("stage16g2a-tool-test", run_dir, task_id="task")
    adapter = LocalWorkspaceAdapter(run_id="stage16g2a-tool-test", run_dir=run_dir)
    return ToolExecutionContext(
        run_id="stage16g2a-tool-test",
        task_id="task",
        workspace_facade=adapter,
        run_workspace=RunWorkspace(
            run_id="stage16g2a-tool-test",
            workspace_path=workspace.as_posix(),
            artifact_dir=(run_dir / "artifacts").as_posix(),
            dependency_state=DependencyState(),
        ),
        artifact_writer=recorder,
        permission_context=PermissionContext(mode="auto"),
        verifier_feedback_facade=None,  # type: ignore[arg-type]
        resolved_verifier_plan=None,  # type: ignore[arg-type]
    )
