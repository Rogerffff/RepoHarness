import json
from collections import Counter
from pathlib import Path

from scripts.pre_verl.build_stage16g0_baseline_contract_followup import (
    REQUIRED_COMPARISON_CAPABILITIES,
    build_claude_code_baseline_contract,
    build_mini_swe_agent_baseline_contract,
    build_per_capability_baseline_comparison,
    build_stage16g_implementation_requirements,
    write_reports,
)


def test_claude_code_baseline_uses_concrete_tool_sources_not_only_agents_guide() -> None:
    contract = build_claude_code_baseline_contract()
    source_paths = {
        evidence["relative_path"]
        for record in contract["capability_contracts"]
        for evidence in record["source_evidence"]
    }

    assert "reference/claude-code-typescript-src/tools/FileReadTool/FileReadTool.ts" in source_paths
    assert "reference/claude-code-typescript-src/tools/BashTool/BashTool.tsx" in source_paths
    assert "reference/claude-code-typescript-src/AGENTS.md" not in source_paths


def test_mini_swe_agent_baseline_uses_evaluation_worktree_real_run_evidence() -> None:
    contract = build_mini_swe_agent_baseline_contract()
    source_inventory = contract["source_inventory"]
    source_refs = {entry["opaque_ref"] for entry in source_inventory}

    assert any(ref.endswith("mini_swe_agent_deepseek_v4_pro_high.yaml") for ref in source_refs)
    assert any(ref.endswith("public_source_mini_swe_agent_swebench_config_excerpt.txt") for ref in source_refs)
    assert any(ref.endswith("mini_swe_agent_b0_smoke5.stdout_stderr.log") for ref in source_refs)
    assert all(entry["source_worktree_label"] == "evaluation_worktree" for entry in source_inventory)
    assert all(entry["tier"] == "tier2_real_config_or_run_log" for entry in source_inventory)

    safety = next(
        record
        for record in contract["capability_contracts"]
        if record["capability_id"] == "safety_boundary_and_hidden_material_exclusion"
    )
    stable_shell = next(
        record for record in contract["capability_contracts"] if record["capability_id"] == "stable_shell_loop"
    )
    assert safety["primary_source_verification_required"] is True
    assert stable_shell["primary_source_verification_required"] is False


def test_per_capability_comparison_covers_required_fields_and_blocks_to_16g1_through_16g4() -> None:
    comparison = build_per_capability_baseline_comparison()
    records = comparison["comparison_records"]
    capability_ids = {record["capability_id"] for record in records}

    assert set(REQUIRED_COMPARISON_CAPABILITIES).issubset(capability_ids)
    for record in records:
        assert record["claude_code_baseline"]
        assert record["mini_swe_agent_baseline"]
        assert record["repoharness_current_status"]
        assert record["source_evidence"]
        if record["blocking_for_main_swe_rl"]:
            assert record["required_stage"] in {"16G.1", "16G.2", "16G.3", "16G.4"}

    repeated_claude = max(Counter(record["claude_code_baseline"] for record in records).values())
    repeated_mini = max(Counter(record["mini_swe_agent_baseline"] for record in records).values())
    assert repeated_claude <= 5
    assert repeated_mini <= 5


def test_stage16g_requirements_capture_structured_public_command_strategy() -> None:
    requirements = build_stage16g_implementation_requirements()

    assumptions = {item["assumption_id"]: item for item in requirements["design_assumptions"]}
    assert "structured_public_command_first_core_profile" in assumptions
    assert "mini_swe_agent_dynamic_capability_not_shell_shape" in assumptions

    stages = {item["required_stage"] for item in requirements["requirements"]}
    assert {"16G.1", "16G.2", "16G.3", "16G.4", "16G.5"}.issubset(stages)
    stage16g3 = next(
        item
        for item in requirements["requirements"]
        if item["requirement_id"] == "stage16g3_public_command_project_test_and_scratch_python"
    )
    assert stage16g3["priority"] == "P0"
    assert "scratch_python_or_reproduction_script" in stage16g3["source_capability_ids"]


def test_writer_outputs_followup_summary_and_public_safe_json(tmp_path: Path) -> None:
    digests = write_reports(tmp_path)
    expected = {
        "stage16g0_claude_code_baseline_contract.json",
        "stage16g0_mini_swe_agent_baseline_contract.json",
        "stage16g0_per_capability_baseline_comparison.json",
        "stage16g0_stage16g_implementation_requirements.json",
        "stage16g0_followup_acceptance_summary.json",
    }

    assert expected.issubset(digests)

    summary = json.loads((tmp_path / "stage16g0_followup_acceptance_summary.json").read_text())
    comparison = json.loads((tmp_path / "stage16g0_per_capability_baseline_comparison.json").read_text())
    requirements = json.loads((tmp_path / "stage16g0_stage16g_implementation_requirements.json").read_text())

    assert summary["status"] == "passed"
    assert summary["comparison_record_count"] == len(comparison["comparison_records"])
    assert summary["requirement_count"] == len(requirements["requirements"])
    assert summary["first_stage16g0_acceptance_summary_left_immutable"] is True
    assert summary["validation_checks"]["claude_code_evidence_not_all_agents_md"] is True
    assert summary["validation_checks"]["mini_swe_agent_uses_evaluation_worktree_tier2_evidence"] is True
    assert summary["validation_checks"]["baseline_template_repetition_check_passed"] is True
    assert summary["validation_checks"]["blocking_records_map_to_16g1_through_16g4"] is True

    for path in tmp_path.glob("*.json"):
        text = path.read_text()
        assert "/Users/" not in text
        assert "/private/" not in text
        assert "/home/" not in text
        assert "/tmp/" not in text
        assert "/var/folders/" not in text
