from __future__ import annotations

import json
from pathlib import Path

from repo_harness_verl.stage15_inventory import (
    STAGE15_0_ARTIFACTS,
    Stage15PartialRolloutInterfaceInventory,
    inspect_stage15_0_artifacts,
    write_stage15_0_artifacts,
)


def test_stage15_0_artifact_writer_generates_complete_acceptance_bundle(tmp_path: Path) -> None:
    summary = write_stage15_0_artifacts(tmp_path)

    assert summary.passed is True
    assert summary.failures == []
    for artifact in STAGE15_0_ARTIFACTS:
        assert (tmp_path / artifact).exists()
    assert summary.inventory_sha256
    assert summary.patch_plan_sha256
    assert summary.risk_matrix_sha256
    assert summary.static_scan_report_sha256
    assert summary.reference_verl_commit
    assert "fully_async_partial_rollout_interface_inventory.json" in summary.artifact_paths

    inventory = Stage15PartialRolloutInterfaceInventory.model_validate(
        json.loads((tmp_path / "fully_async_partial_rollout_interface_inventory.json").read_text(encoding="utf-8"))
    )
    assert inventory.native_partial_rollout_trigger_chain[
        "weight_sync_calls_checkpoint_manager_update_weights"
    ]
    assert inventory.llm_server_stop_reason_inventory["completed_stop_reason_mapping_checked"]


def test_stage15_0_acceptance_rejects_missing_artifact(tmp_path: Path) -> None:
    write_stage15_0_artifacts(tmp_path)
    (tmp_path / "stage15_partial_rollout_risk_matrix.json").unlink()

    summary = inspect_stage15_0_artifacts(tmp_path)

    assert summary.passed is False
    assert "missing_artifact:stage15_partial_rollout_risk_matrix.json" in summary.failures


def test_stage15_0_acceptance_rejects_inventory_missing_abort_resume_chain(tmp_path: Path) -> None:
    write_stage15_0_artifacts(tmp_path)
    inventory_path = tmp_path / "fully_async_partial_rollout_interface_inventory.json"
    payload = json.loads(inventory_path.read_text(encoding="utf-8"))
    payload["native_partial_rollout_trigger_chain"]["checkpoint_manager_aborts_inflight_requests"] = False
    inventory_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    summary = inspect_stage15_0_artifacts(tmp_path)

    assert summary.passed is False
    assert "inventory_missing_checkpoint_manager_abort" in summary.failures


def test_stage15_0_acceptance_rejects_missing_required_config_key(tmp_path: Path) -> None:
    write_stage15_0_artifacts(tmp_path)
    inventory_path = tmp_path / "fully_async_partial_rollout_interface_inventory.json"
    payload = json.loads(inventory_path.read_text(encoding="utf-8"))
    del payload["config_inventory"]["rollout.total_rollout_steps"]
    inventory_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    summary = inspect_stage15_0_artifacts(tmp_path)

    assert summary.passed is False
    assert "inventory_missing_config_key:rollout.total_rollout_steps" in summary.failures


def test_stage15_0_acceptance_rejects_config_key_missing_stage15_override(tmp_path: Path) -> None:
    write_stage15_0_artifacts(tmp_path)
    inventory_path = tmp_path / "fully_async_partial_rollout_interface_inventory.json"
    payload = json.loads(inventory_path.read_text(encoding="utf-8"))
    del payload["config_inventory"]["async_training.partial_rollout"]["stage15_required_override"]
    inventory_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    summary = inspect_stage15_0_artifacts(tmp_path)

    assert summary.passed is False
    assert (
        "inventory_config_key_missing_field:async_training.partial_rollout:stage15_required_override"
        in summary.failures
    )


def test_stage15_0_acceptance_rejects_config_source_evidence_not_found(tmp_path: Path) -> None:
    write_stage15_0_artifacts(tmp_path)
    inventory_path = tmp_path / "fully_async_partial_rollout_interface_inventory.json"
    payload = json.loads(inventory_path.read_text(encoding="utf-8"))
    payload["config_inventory"]["actor_rollout_ref.rollout.name"]["source_evidence"] = (
        "actor_rollout_ref.rollout.name=definitely_missing"
    )
    inventory_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    summary = inspect_stage15_0_artifacts(tmp_path)

    assert summary.passed is False
    assert (
        "inventory_config_key_source_evidence:actor_rollout_ref.rollout.name:source_evidence_not_found"
        in summary.failures
    )


def test_stage15_0_acceptance_rejects_missing_completed_stop_reason_mapping(tmp_path: Path) -> None:
    write_stage15_0_artifacts(tmp_path)
    inventory_path = tmp_path / "fully_async_partial_rollout_interface_inventory.json"
    payload = json.loads(inventory_path.read_text(encoding="utf-8"))
    payload["llm_server_stop_reason_inventory"]["completed_stop_reason_mapping_checked"] = False
    inventory_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    summary = inspect_stage15_0_artifacts(tmp_path)

    assert summary.passed is False
    assert "inventory_missing_completed_stop_reason_mapping" in summary.failures


def test_stage15_0_acceptance_rejects_missing_sglang_stop_reason_inventory(tmp_path: Path) -> None:
    write_stage15_0_artifacts(tmp_path)
    inventory_path = tmp_path / "fully_async_partial_rollout_interface_inventory.json"
    payload = json.loads(inventory_path.read_text(encoding="utf-8"))
    payload["llm_server_stop_reason_inventory"]["normal_completion_stop_reason_by_backend"]["sglang"][
        "returns_raw_finish_reason"
    ] = False
    inventory_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    summary = inspect_stage15_0_artifacts(tmp_path)

    assert summary.passed is False
    assert "inventory_missing_sglang_raw_finish_reason_mapping" in summary.failures


def test_stage15_0_acceptance_rejects_missing_backend_abort_resume_inventory(tmp_path: Path) -> None:
    write_stage15_0_artifacts(tmp_path)
    inventory_path = tmp_path / "fully_async_partial_rollout_interface_inventory.json"
    payload = json.loads(inventory_path.read_text(encoding="utf-8"))
    payload["backend_abort_resume_inventory"] = [
        item for item in payload["backend_abort_resume_inventory"] if item["backend"] != "trtllm"
    ]
    inventory_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    summary = inspect_stage15_0_artifacts(tmp_path)

    assert summary.passed is False
    assert "inventory_missing_backend_abort_resume:trtllm" in summary.failures
    assert "inventory_missing_trtllm_not_implemented_risk" in summary.failures


def test_stage15_0_acceptance_rejects_missing_source_evidence_line(tmp_path: Path) -> None:
    write_stage15_0_artifacts(tmp_path)
    inventory_path = tmp_path / "fully_async_partial_rollout_interface_inventory.json"
    payload = json.loads(inventory_path.read_text(encoding="utf-8"))
    payload["source_evidence"][0]["line"] = None
    inventory_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    summary = inspect_stage15_0_artifacts(tmp_path)

    assert summary.passed is False
    assert any(failure.startswith("inventory_source_evidence_missing_line:") for failure in summary.failures)


def test_stage15_0_acceptance_rejects_tampered_source_evidence_hint(tmp_path: Path) -> None:
    write_stage15_0_artifacts(tmp_path)
    inventory_path = tmp_path / "fully_async_partial_rollout_interface_inventory.json"
    payload = json.loads(inventory_path.read_text(encoding="utf-8"))
    payload["source_evidence"][0]["line_hint"] = "definitely_missing_stage15_source_evidence"
    payload["source_evidence"][0]["line"] = 1
    inventory_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    summary = inspect_stage15_0_artifacts(tmp_path)

    assert summary.passed is False
    assert any(
        failure.endswith(":source_evidence_not_found")
        and failure.startswith("inventory_source_evidence:")
        for failure in summary.failures
    )


def test_stage15_0_acceptance_rejects_no_patch_claim_when_patch_is_required(tmp_path: Path) -> None:
    write_stage15_0_artifacts(tmp_path)
    patch_path = tmp_path / "stage15_partial_rollout_patch_plan.json"
    payload = json.loads(patch_path.read_text(encoding="utf-8"))
    payload["no_patch_required_claim_allowed"] = True
    payload["reference_verl_patch_or_wrapper_required"] = False
    payload["no_patch_rejection_reasons"] = []
    patch_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    summary = inspect_stage15_0_artifacts(tmp_path)

    assert summary.passed is False
    assert "patch_plan_no_patch_claim_conflicts_with_inventory" in summary.failures
    assert "patch_plan_missing_required_patch_or_wrapper_flag" in summary.failures


def test_stage15_0_acceptance_rejects_recommended_combo_without_source_gate(tmp_path: Path) -> None:
    write_stage15_0_artifacts(tmp_path)
    patch_path = tmp_path / "stage15_partial_rollout_patch_plan.json"
    payload = json.loads(patch_path.read_text(encoding="utf-8"))
    payload["recommended_patch_ids"] = ["stage15_agent_loop_owned_partial_side_channel"]
    patch_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    summary = inspect_stage15_0_artifacts(tmp_path)

    assert summary.passed is False
    assert (
        "patch_plan_recommended_combo_missing:stage15_fully_async_rollouter_source_gate_wrapper"
        in summary.failures
    )


def test_stage15_0_acceptance_scans_public_json_for_path_and_secret_leaks(tmp_path: Path) -> None:
    write_stage15_0_artifacts(tmp_path)
    scan_path = tmp_path / "stage15_0_static_scan_report.json"
    payload = json.loads(scan_path.read_text(encoding="utf-8"))
    payload["diagnostics"] = ["leaked /workspace/RepoHarness/runs/example"]
    scan_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    summary = inspect_stage15_0_artifacts(tmp_path)

    assert summary.passed is False
    assert any(
        failure.startswith("public_evidence_path_or_secret_leak:stage15_0_static_scan_report.json")
        for failure in summary.failures
    )


def test_stage15_0_acceptance_scans_jsonl_command_log_for_path_leaks(tmp_path: Path) -> None:
    write_stage15_0_artifacts(tmp_path)
    (tmp_path / "stage15_0_command_log.jsonl").write_text(
        json.dumps({"message": "leaked /workspace/RepoHarness/runs/example"}),
        encoding="utf-8",
    )

    summary = inspect_stage15_0_artifacts(tmp_path)

    assert summary.passed is False
    assert any(
        failure.startswith("public_evidence_path_or_secret_leak:stage15_0_command_log.jsonl")
        for failure in summary.failures
    )
