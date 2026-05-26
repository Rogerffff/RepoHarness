import json
from pathlib import Path

from scripts.pre_verl.build_stage16g0_capability_gap_inventory import (
    build_capability_probe_report,
    build_claude_code_tool_inventory,
    build_external_reference_inventory,
    build_repoharness_tool_inventory,
    build_scaffold_matrix,
    build_source_inventory,
    write_reports,
)


def test_stage16g0_records_default_scaffold_without_assuming_patch_focused() -> None:
    inventory = build_repoharness_tool_inventory()

    assert inventory["training_default_scaffold_id"] == "simple_react"
    create_file = next(tool for tool in inventory["tools"] if tool["tool_name"] == "create_file")
    execute_bash = next(tool for tool in inventory["tools"] if tool["tool_name"] == "execute_bash")

    assert create_file["model_visible_default"] is True
    assert "simple_react" in create_file["visible_in_scaffolds"]
    assert execute_bash["model_visible_default"] is False
    assert execute_bash["known_limitations"]


def test_stage16g0_scaffold_matrix_marks_mini_shell_absent() -> None:
    matrix = build_scaffold_matrix()

    mini_shell = next(
        record for record in matrix["records"] if record["scaffold_name"] == "patch_focused_react_mini_shell"
    )
    patch_focused = next(record for record in matrix["records"] if record["scaffold_name"] == "patch_focused_react")

    assert mini_shell["exists"] is False
    assert mini_shell["status"] == "not_present_in_current_worktree"
    assert patch_focused["has_create_file"] is False
    assert patch_focused["has_shell"] is False


def test_stage16g0_capability_probe_records_execute_bash_as_narrow_not_empty() -> None:
    report = build_capability_probe_report()

    probe = next(probe for probe in report["probes"] if probe["probe_id"] == "execute_bash_narrow_not_toy")
    decisions = probe["decisions"]
    executable = next(
        probe
        for probe in report["probes"]
        if probe["probe_id"] == "default_scaffold_read_search_edit_patch_reward_loop"
    )

    assert decisions["rg_literal_search_allowed"]["decision"] == "allow"
    assert decisions["pytest_allowed"]["decision"] == "allow"
    assert decisions["unallowlisted_cat_denied"]["decision"] == "deny"
    assert decisions["git_history_denied"]["decision"] == "deny"
    assert executable["actual_status"] == "passed"
    assert executable["tool_loop_executed"] is True
    assert executable["public_test_passed"] is True
    assert executable["final_patch_generated"] is True
    assert executable["reward_metadata_computed"] is True


def test_stage16g0_claude_code_inventory_covers_required_capability_families() -> None:
    inventory = build_claude_code_tool_inventory()
    capability_ids = {record["capability_id"] for record in inventory["capabilities"]}

    assert {
        "non_text_file_read",
        "patch_multi_file_edit",
        "background_command_monitor",
        "testing_and_project_command",
        "deferred_tool_discovery",
        "slash_commands",
        "symbol_or_language_diagnostics",
        "session_context_management",
    }.issubset(capability_ids)


def test_stage16g0_source_and_external_references_cover_required_inputs() -> None:
    source_inventory = build_source_inventory()
    external_inventory = build_external_reference_inventory()

    source_labels = {record["source_label"] for record in source_inventory["source_documents"]}
    reference_ids = {record["reference_id"] for record in external_inventory["references"]}

    assert "worktree_sync_run_episode_unification_plan" in source_labels
    assert {
        "cursor_composer_training_deployment_consistency",
        "codex_workspace_sandbox_approval",
        "mini_swe_agent_stable_shell",
        "openhands_swegym_deepswe_executable_environment",
        "reward_hacking_monitoring",
    }.issubset(reference_ids)


def test_stage16g0_writer_binds_reports_and_preserves_public_safety(tmp_path: Path) -> None:
    write_reports(tmp_path)

    summary = json.loads((tmp_path / "stage16g0_acceptance_summary.json").read_text())
    scan = json.loads((tmp_path / "stage16g0_path_leak_scan_report.json").read_text())
    gaps = json.loads((tmp_path / "stage16g0_capability_gap_matrix.json").read_text())
    probes = json.loads((tmp_path / "stage16g0_capability_probe_report.json").read_text())

    assert summary["status"] == "passed"
    assert summary["capability_gap_count"] == gaps["capability_gap_count"]
    assert summary["capability_probe_count"] == probes["probe_count"]
    assert summary["capability_gap_count"] > 0
    assert summary["p0_gap_count"] > 0
    assert summary["stage17a_schema_only_allowed"] is True
    assert summary["stage17b_real_data_freeze_allowed"] is False
    assert summary["stage20_warm_start_data_generation_allowed"] is False
    assert scan["public_path_leak_scan_passed"] is True

    for path in tmp_path.glob("*.json"):
        text = path.read_text()
        assert "/Users/" not in text
        assert "/private/" not in text
