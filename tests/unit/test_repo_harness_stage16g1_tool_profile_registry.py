import hashlib
import json
from pathlib import Path

import pytest

from repo_harness.errors import RepoHarnessError
from repo_harness.stage16g_tool_profile import (
    _scan_public_files,
    build_current_code_facts,
    build_profile_registry_inspection_report,
    build_profile_taxonomy,
    build_tool_registry_contract,
    inspect_stage16g1_tool_profile,
    write_stage16g1_reports,
)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_stage16g1_registry_covers_comparison_and_preserves_owner_stage() -> None:
    registry = build_tool_registry_contract()
    records = registry["records"]

    assert registry["record_count"] == 27
    assert {record["capability_id"] for record in records}

    blocking = [record for record in records if record["blocking_for_main_swe_rl"]]
    post_optional = [record for record in records if record["owner_stage"] == "post_16G_optional"]
    assert len(blocking) == 17
    assert len(post_optional) == 4

    for record in records:
        assert record["owner_stage"] == record["required_stage_from_stage16g0"]
        assert record["allowed_artifact_visibility"]
        assert record["denial_feedback_policy"]
        policy = record["training_projection_policy"]
        assert policy["tool_event_policy_loss_unit"] == "not_an_individual_policy_loss_sample"
        assert "allowed_in_policy_loss_trajectory" in policy
        assert "sample_policy_loss_candidate_effect" in policy
        if record["executor_binding_status"] == "not_implemented":
            assert policy["allowed_in_policy_loss_trajectory"] is False


def test_stage16g1_profile_taxonomy_keeps_persistent_shell_out_of_core() -> None:
    registry = build_tool_registry_contract()
    taxonomy = build_profile_taxonomy(registry)
    profiles = {profile["profile_id"]: profile for profile in taxonomy["profiles"]}

    assert set(profiles) == {
        "safe_structured_only",
        "swe_public_core",
        "swe_public_extended",
        "redteam_restricted",
    }
    assert "persistent_diagnostic_session" not in profiles["swe_public_core"]["allowed_capability_ids"]
    assert "persistent_diagnostic_session" in profiles["swe_public_core"]["must_not_include"]
    assert "persistent_diagnostic_session" in profiles["swe_public_extended"]["planned_capability_ids"]
    assert "session_reset_required" in profiles["swe_public_extended"]["required_safety_boundaries"]
    assert "artifact_hygiene_required" in profiles["swe_public_extended"]["required_safety_boundaries"]
    assert "path_redaction_required" in profiles["swe_public_extended"]["required_safety_boundaries"]
    assert "public_safe_projection_required" in profiles["swe_public_extended"]["required_safety_boundaries"]
    assert profiles["redteam_restricted"]["primary_training_default"] is False


def test_stage16g1_current_code_facts_are_machine_checked() -> None:
    facts = build_current_code_facts()

    assert facts["runtime_default_scaffold_is_simple_react"] is True
    assert facts["simple_react_exposes_create_file"] is True
    assert facts["patch_focused_react_mini_shell_present"] is False
    assert facts["execute_bash_narrow_but_nonempty"] is True
    assert facts["diagnostic_shell_not_core_default"] is True


def test_stage16g1_inspection_rejects_owner_stage_drift() -> None:
    registry = build_tool_registry_contract()
    mutated = json.loads(json.dumps(registry))
    for record in mutated["records"]:
        if record["capability_id"] == "bash_or_public_command_execution":
            record["owner_stage"] = "16G.2"
            break

    report = build_profile_registry_inspection_report(registry=mutated)
    assert report["status"] == "failed"
    assert "owner_stage_mismatch:bash_or_public_command_execution" in report["failures"]


def test_stage16g1_inspection_rejects_unimplemented_policy_loss_eligibility() -> None:
    registry = build_tool_registry_contract()
    mutated = json.loads(json.dumps(registry))
    for record in mutated["records"]:
        if record["capability_id"] == "apply_patch_or_multi_file_edit":
            record["training_projection_policy"]["allowed_in_policy_loss_trajectory"] = True
            break

    report = build_profile_registry_inspection_report(registry=mutated)
    assert report["status"] == "failed"
    assert "not_implemented_policy_loss_allowed:apply_patch_or_multi_file_edit" in report["failures"]


def test_stage16g1_inspection_rejects_missing_extended_session_boundary() -> None:
    registry = build_tool_registry_contract()
    taxonomy = build_profile_taxonomy(registry)
    mutated = json.loads(json.dumps(taxonomy))
    for profile in mutated["profiles"]:
        if profile["profile_id"] == "swe_public_extended":
            profile["required_safety_boundaries"].remove("session_reset_required")
            break

    report = build_profile_registry_inspection_report(registry=registry, taxonomy=mutated)
    assert report["status"] == "failed"
    assert "swe_public_extended_missing_boundary:session_reset_required" in report["failures"]


def test_stage16g1_writer_outputs_public_safe_evidence_and_cli_inspector(tmp_path: Path) -> None:
    digests = write_stage16g1_reports(output_dir=tmp_path)
    expected = {
        "stage16g1_source_inventory.json",
        "stage16g1_tool_registry_contract.json",
        "stage16g1_profile_taxonomy.json",
        "stage16g1_training_eligibility_gate_spec.json",
        "stage16g1_profile_registry_inspection_report.json",
        "stage16g1_run_episode_profile_smoke_report.json",
        "stage16g1_public_evidence_policy.json",
        "stage16g1_path_leak_scan_report.json",
        "stage16g1_human_readable_tool_profile_summary.md",
        "stage16g1_acceptance_summary.json",
    }
    assert expected.issubset(digests)

    summary = json.loads((tmp_path / "stage16g1_acceptance_summary.json").read_text())
    inspection = json.loads((tmp_path / "stage16g1_profile_registry_inspection_report.json").read_text())
    smoke = json.loads((tmp_path / "stage16g1_run_episode_profile_smoke_report.json").read_text())

    assert summary["status"] == "passed"
    assert summary["comparison_record_count"] == 27
    assert summary["blocking_for_main_swe_rl_count"] == 17
    assert summary["post_16g_optional_count"] == 4
    assert summary["source_inventory_sha256"]
    assert summary["machine_inspector_passed"] is True
    assert inspection["checks"]["owner_stage_matches_stage16g0_required_stage"] is True
    assert inspection["checks"]["counts_derived_from_stage16g0_comparison"] is True
    assert smoke["not_json_only"] is True
    assert smoke["smoke_route"] == "run_episode_task_real_episode_mock_projection"
    assert smoke["actual_run_episode_task_invoked"] is True
    assert smoke["projection_manifest_facts"]["projection_created_from_run_episode"] is True
    assert smoke["projection_validation_facts"]["projection_complete"] is True
    assert smoke["profile_or_registry_version_carried_to_public_projection"] is True

    cli_report = json.loads(
        inspect_stage16g1_tool_profile(
            tmp_path / "stage16g1_acceptance_summary.json",
            assert_complete=True,
        )
    )
    assert cli_report["status"] == "passed"

    for path in tmp_path.glob("stage16g1_*"):
        if path.suffix not in {".json", ".md"}:
            continue
        text = path.read_text()
        assert "/Users/" not in text
        assert "/private/" not in text
        assert "/home/" not in text
        assert "/tmp/" not in text
        assert "/var/folders/" not in text


def test_stage16g1_cli_inspector_rejects_summary_count_and_gate_drift(tmp_path: Path) -> None:
    write_stage16g1_reports(output_dir=tmp_path)
    summary_path = tmp_path / "stage16g1_acceptance_summary.json"
    summary = json.loads(summary_path.read_text())
    summary["comparison_record_count"] = 999
    summary["blocking_for_main_swe_rl_count"] = 999
    summary["post_16g_optional_count"] = 999
    summary["profile_count"] = 999
    summary["registry_record_count"] = 999
    summary["stage17b_real_data_freeze_allowed"] = True
    summary["stage20_warm_start_data_generation_allowed"] = True
    summary["stage21_formal_rl_allowed"] = True
    summary_path.write_text(json.dumps(summary, indent=2))

    with pytest.raises(RepoHarnessError) as exc_info:
        inspect_stage16g1_tool_profile(summary_path, assert_complete=True)
    report = json.loads(str(exc_info.value))
    assert "acceptance_summary_field_mismatch:comparison_record_count" in report["failures"]
    assert "acceptance_summary_field_mismatch:stage17b_real_data_freeze_allowed" in report["failures"]


def test_stage16g1_cli_inspector_rejects_source_inventory_tamper_even_if_digest_updated(tmp_path: Path) -> None:
    write_stage16g1_reports(output_dir=tmp_path)
    inventory_path = tmp_path / "stage16g1_source_inventory.json"
    summary_path = tmp_path / "stage16g1_acceptance_summary.json"
    inventory = json.loads(inventory_path.read_text())
    inventory["source_inputs"] = []
    inventory_path.write_text(json.dumps(inventory, indent=2))
    summary = json.loads(summary_path.read_text())
    summary["source_inventory_sha256"] = _sha256_file(inventory_path)
    summary_path.write_text(json.dumps(summary, indent=2))

    with pytest.raises(RepoHarnessError) as exc_info:
        inspect_stage16g1_tool_profile(summary_path, assert_complete=True)
    report = json.loads(str(exc_info.value))
    assert "source_inventory_input_labels_mismatch" in report["failures"]
    assert "source_inventory_missing_input:stage16g0_per_capability_baseline_comparison.json" in report["failures"]


def test_stage16g1_cli_inspector_rescans_current_public_evidence(tmp_path: Path) -> None:
    write_stage16g1_reports(output_dir=tmp_path)
    summary_path = tmp_path / "stage16g1_acceptance_summary.json"
    summary = json.loads(summary_path.read_text())
    summary["tampered_local_path"] = "/Users/roger/secret"
    summary_path.write_text(json.dumps(summary, indent=2))

    with pytest.raises(RepoHarnessError) as exc_info:
        inspect_stage16g1_tool_profile(summary_path, assert_complete=True)
    report = json.loads(str(exc_info.value))
    assert "public_path_leak_scan_failed_current_files" in report["failures"]
    assert "path_leak_scan_report_stale_or_mismatched" in report["failures"]
    assert "acceptance_summary_unexpected_field:tampered_local_path" in report["failures"]


def test_stage16g1_cli_inspector_rejects_digest_mismatch(tmp_path: Path) -> None:
    write_stage16g1_reports(output_dir=tmp_path)
    registry_path = tmp_path / "stage16g1_tool_registry_contract.json"
    registry = json.loads(registry_path.read_text())
    registry["records"][0]["owner_stage"] = "16G.2"
    registry_path.write_text(json.dumps(registry, indent=2))

    with pytest.raises(RepoHarnessError):
        inspect_stage16g1_tool_profile(
            tmp_path / "stage16g1_acceptance_summary.json",
            assert_complete=True,
        )


def test_stage16g1_public_scan_rejects_common_secret_tokens(tmp_path: Path) -> None:
    (tmp_path / "stage16g1_token_probe.json").write_text(
        json.dumps({"token": "sk-testtoken1234567890"}),
    )

    report = _scan_public_files(tmp_path)
    assert report["public_path_leak_scan_passed"] is False
    assert report["finding_count"] == 1
