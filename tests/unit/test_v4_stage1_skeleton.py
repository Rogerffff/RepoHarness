import json
from pathlib import Path

import pytest

from repo_harness.cli.main import main
from repo_harness.errors import ConfigError
from repo_harness.export.manifest import sha256_file
from repo_harness.schema_versions import (
    V4_ACCEPTANCE_BUNDLE_MANIFEST_VERSION,
    V4_ACCEPTANCE_INPUTS_VERSION,
    V4_ACCEPTANCE_REPORT_VERSION,
    V4_AGENT_RUN_INTEGRATION_REPORT_VERSION,
    V4_ALLOWLIST_POLICY_VERSION,
    V4_ARTIFACT_INSPECT_TRACKING_TABLE_VERSION,
    V4_BATCH_RESUME_REPORT_VERSION,
    V4_BUDGET_CONTROL_REPORT_VERSION,
    V4_CARDS_MANIFEST_VERSION,
    V4_CHECKPOINT_STATE_REPORT_VERSION,
    V4_CONTAMINATION_SCAN_REPORT_VERSION,
    V4_CONTAMINATION_DENYLIST_VERSION,
    V4_EXPORT_QUALITY_MANIFEST_VERSION,
    V4_LEASE_STATE_REPORT_VERSION,
    V4_RESOURCE_LOCK_REPORT_VERSION,
    V4_RESOURCE_USAGE_REPORT_VERSION,
    V4_RETRY_POLICY_REPORT_VERSION,
    V4_ROLLOUT_QUEUE_MANIFEST_VERSION,
    V4_RUN_SELECTION_MANIFEST_VERSION,
    V4_RUN_SELECTION_QUERY_REPORT_VERSION,
    V4_TASK_FREEZE_MANIFEST_VERSION,
    V4_TASK_VALIDITY_REPORT_VERSION,
    V4_TOOL_CONTRACT_SNAPSHOT_VERSION,
    V4_TOOL_LIFECYCLE_TRACE_ENTRY_VERSION,
    V4_TRAJECTORY_STORE_INTEGRITY_REPORT_VERSION,
    V4_WORKER_RUN_LOG_ENTRY_VERSION,
)
from repo_harness.v4_visibility import (
    V4_CARD_CLAIM_DENYLIST_VERSION,
    v4_card_claim_denylist_sha256,
    v4_contamination_denylist_sha256,
)
from repo_harness.v4_stage1 import (
    V4_ARTIFACT_SET_SPECS,
    build_artifact_inspect_tracking_table_payload,
    inspect_v4_acceptance,
    inspect_v4_artifact_set,
    inspect_v4_inputs,
)
from repo_harness.v4_task_freeze import build_v4_task_freeze
from repo_harness.workspace.source_hash import compute_source_tree_hash


def test_v4_stage1_artifact_inspect_skeletons_pass(tmp_path: Path) -> None:
    paths = _write_valid_stage1_fixture(tmp_path)

    assert "complete" in inspect_v4_artifact_set("rollout_queue", paths["rollout_dir"], assert_complete=True)
    assert "complete" in inspect_v4_artifact_set("rollout_leases", paths["rollout_dir"], assert_complete=True)
    assert "complete" in inspect_v4_artifact_set("rollout_retry", paths["rollout_dir"], assert_complete=True)
    assert "complete" in inspect_v4_artifact_set("rollout_budget", paths["rollout_dir"], assert_complete=True)
    assert "complete" in inspect_v4_artifact_set("resource_locks", paths["rollout_dir"], assert_complete=True)
    assert "complete" in inspect_v4_artifact_set("resource_usage", paths["rollout_dir"], assert_complete=True)
    assert "complete" in inspect_v4_artifact_set("rollout_resume", paths["rollout_dir"], assert_complete=True)
    assert "complete" in inspect_v4_artifact_set("run_selection_query", paths["run_selection_query"], assert_complete=True)
    assert "complete" in inspect_v4_artifact_set("task_freeze", paths["task_freeze"], assert_complete=True)
    assert "complete" in inspect_v4_artifact_set("task_validity", paths["task_validity"], assert_complete=True)
    assert "frozen" in inspect_v4_artifact_set("tool_contract", paths["tool_dir"], assert_complete=True)
    assert "complete" in inspect_v4_artifact_set("tool_lifecycle", paths["tool_dir"], assert_complete=True)
    assert "complete" in inspect_v4_artifact_set("agent_run_integration", paths["run_dir"], assert_complete=True)
    assert "readable" in inspect_v4_artifact_set("trajectory_store", paths["run_dir"], assert_complete=True)
    assert "complete" in inspect_v4_artifact_set("export_quality", paths["export_dir"], assert_complete=True)
    assert "complete" in inspect_v4_artifact_set("cards", paths["cards_dir"], assert_complete=True)
    assert "clean" in inspect_v4_artifact_set("contamination_scan", paths["scan_report"], assert_complete=True)


def test_v4_acceptance_inputs_and_report_skeleton_pass(tmp_path: Path) -> None:
    paths = _write_valid_stage1_fixture(tmp_path)

    assert "Inspect V4 inputs: complete" in inspect_v4_inputs(paths["acceptance_inputs"], assert_complete=True)
    assert "Inspect V4 acceptance: complete" in inspect_v4_acceptance(paths["acceptance_report"], assert_complete=True)
    assert main(["inspect-v4-inputs", str(paths["acceptance_inputs"]), "--assert-complete"]) == 0
    assert main(["inspect-v4-acceptance", str(paths["acceptance_report"]), "--assert-complete"]) == 0
    assert main(["inspect-acceptance-bundle", str(paths["acceptance_bundle"]), "--assert-immutable"]) == 0


def test_v4_stage1_cli_exposes_required_inspect_commands(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    output = capsys.readouterr().out
    for command in build_artifact_inspect_tracking_table_payload()["required_inspect_commands"]:
        assert command in output


def test_v4_stage1_schema_fixture_directory_covers_required_versions() -> None:
    fixture = Path("tests/fixtures/v4/stage1/valid/schema_fixtures.json")
    payload = _read_json(fixture)
    fixture_versions = {record["schema_version"] for record in payload["fixtures"]}
    required_versions = {
        V4_ACCEPTANCE_BUNDLE_MANIFEST_VERSION,
        V4_ACCEPTANCE_INPUTS_VERSION,
        V4_ACCEPTANCE_REPORT_VERSION,
        V4_ARTIFACT_INSPECT_TRACKING_TABLE_VERSION,
        V4_RUN_SELECTION_MANIFEST_VERSION,
        V4_CONTAMINATION_SCAN_REPORT_VERSION,
    }
    for spec in V4_ARTIFACT_SET_SPECS.values():
        if spec.direct_schema_version:
            required_versions.add(spec.direct_schema_version)
        for _, schema_version in spec.required_files:
            if schema_version:
                required_versions.add(schema_version)
        for _, schema_version in spec.jsonl_files:
            if schema_version:
                required_versions.add(schema_version)
    assert required_versions.difference(fixture_versions) == set()
    assert Path("tests/fixtures/v4/stage1/negative/missing_schema_version.json").exists()
    assert Path("tests/fixtures/v4/stage1/negative/sha_mismatch_v4_inputs.json").exists()


def test_v4_stage1_tracking_table_matches_code_contract() -> None:
    table = _read_json(Path("docs/v4/evidence/schema-and-inspect/artifact_inspect_tracking_table.json"))
    assert table == build_artifact_inspect_tracking_table_payload()


def test_v4_acceptance_recursively_rejects_bound_artifact_contract_failure(tmp_path: Path) -> None:
    paths = _write_valid_stage1_fixture(tmp_path)
    (paths["cards_dir"] / "run_card.json").unlink()

    with pytest.raises(ConfigError, match="cards 绑定产物递归复核失败"):
        inspect_v4_inputs(paths["acceptance_inputs"], assert_complete=True)


def test_v4_acceptance_recursively_uses_stage2_task_validity_inspect(tmp_path: Path) -> None:
    paths = _write_valid_stage1_fixture(tmp_path)
    validity = paths["task_validity"]
    payload = _read_json(validity)
    payload["accepted_task_definitions"][0]["flaky_probe_status"] = "flaky_probe_unstable"
    _write_json(validity, payload)
    task_freeze = paths["task_freeze"]
    task_freeze_payload = _read_json(task_freeze)
    task_freeze_payload["artifact_refs_by_name"]["task_validity_report.json"] = _file_ref(validity, "task_validity_report")
    _write_json(task_freeze, task_freeze_payload)
    _refresh_ref_in_inputs(paths["acceptance_inputs"], "task_freeze", task_freeze)
    _refresh_ref_in_inputs(paths["acceptance_inputs"], "task_validity", validity)

    with pytest.raises(ConfigError, match="task_validity 绑定产物递归复核失败|flaky probe 未通过"):
        inspect_v4_inputs(paths["acceptance_inputs"], assert_complete=True)


def test_v4_stage1_rejects_missing_schema_version(tmp_path: Path) -> None:
    paths = _write_valid_stage1_fixture(tmp_path)
    queue_manifest = paths["rollout_dir"] / "rollout_queue_manifest.json"
    payload = _read_json(queue_manifest)
    del payload["schema_version"]
    _write_json(queue_manifest, payload)

    with pytest.raises(ConfigError, match="schema_version"):
        inspect_v4_artifact_set("rollout_queue", paths["rollout_dir"], assert_complete=True)


def test_v4_stage1_rejects_schema_version_mismatch(tmp_path: Path) -> None:
    paths = _write_valid_stage1_fixture(tmp_path)
    retry_report = paths["rollout_dir"] / "retry_policy_report.json"
    payload = _read_json(retry_report)
    payload["schema_version"] = "wrong"
    _write_json(retry_report, payload)

    with pytest.raises(ConfigError, match="schema_version 不匹配"):
        inspect_v4_artifact_set("rollout_retry", paths["rollout_dir"], assert_complete=True)


def test_v4_contamination_scan_rejects_missing_card_claim_policy(tmp_path: Path) -> None:
    paths = _write_valid_stage1_fixture(tmp_path)
    payload = _read_json(paths["scan_report"])
    payload.pop("card_claim_denylist_sha256")
    _write_json(paths["scan_report"], payload)

    with pytest.raises(ConfigError, match="card_claim_denylist_sha256"):
        inspect_v4_artifact_set("contamination_scan", paths["scan_report"], assert_complete=True)


def test_v4_contamination_scan_rejects_stale_clean_with_findings(tmp_path: Path) -> None:
    paths = _write_valid_stage1_fixture(tmp_path)
    payload = _read_json(paths["scan_report"])
    payload["findings"] = [
        {
            "schema_version": "repo_harness_v4_card_claim_finding_v0",
            "surface": "dataset_card",
            "path": "$",
            "matched_term": "forbidden-card-claim-fixture",
            "category": "forbidden_card_claim",
            "policy_version": V4_CARD_CLAIM_DENYLIST_VERSION,
        }
    ]
    _write_json(paths["scan_report"], payload)

    with pytest.raises(ConfigError, match="findings 必须为空"):
        inspect_v4_artifact_set("contamination_scan", paths["scan_report"], assert_complete=True)


def test_v4_inputs_reject_missing_sha_and_sha_mismatch(tmp_path: Path) -> None:
    paths = _write_valid_stage1_fixture(tmp_path)
    payload = _read_json(paths["acceptance_inputs"])
    payload["input_refs_by_category"]["cards"][0].pop("sha256")
    missing_sha = tmp_path / "missing_sha_inputs.json"
    _write_json(missing_sha, payload)
    with pytest.raises(ConfigError, match="缺少 sha256"):
        inspect_v4_inputs(missing_sha, assert_complete=True)

    payload = _read_json(paths["acceptance_inputs"])
    payload["input_refs_by_category"]["cards"][0]["sha256"] = "0" * 64
    mismatch = tmp_path / "sha_mismatch_inputs.json"
    _write_json(mismatch, payload)
    with pytest.raises(ConfigError, match="sha256 不匹配"):
        inspect_v4_inputs(mismatch, assert_complete=True)


def test_v4_inputs_reject_report_artifacts_in_run_selection(tmp_path: Path) -> None:
    paths = _write_valid_stage1_fixture(tmp_path)
    selection = _read_json(paths["run_selection"])
    selection["entries"][0]["run_ref"] = "runs/v4-final/acceptance/v4_acceptance_report.json"
    _write_json(paths["run_selection"], selection)
    _refresh_ref_in_inputs(paths["acceptance_inputs"], "run_selection_manifest", paths["run_selection"])

    with pytest.raises(ConfigError, match="不能绑定报告类产物"):
        inspect_v4_inputs(paths["acceptance_inputs"], assert_complete=True)


def test_v4_inputs_reject_missing_p1_categories(tmp_path: Path) -> None:
    paths = _write_valid_stage1_fixture(tmp_path)
    payload = _read_json(paths["acceptance_inputs"])
    del payload["input_refs_by_category"]["tool_contract"]
    del payload["input_refs_by_category"]["cards"]
    bad = tmp_path / "missing_p1_inputs.json"
    _write_json(bad, payload)

    with pytest.raises(ConfigError, match="tool_contract|cards"):
        inspect_v4_inputs(bad, assert_complete=True)


def test_v4_inputs_reject_latest_run_auto_selection(tmp_path: Path) -> None:
    paths = _write_valid_stage1_fixture(tmp_path)
    payload = _read_json(paths["acceptance_inputs"])
    payload["latest_run_auto_selection"] = True
    bad = tmp_path / "latest_inputs.json"
    _write_json(bad, payload)

    with pytest.raises(ConfigError, match="latest run"):
        inspect_v4_inputs(bad, assert_complete=True)


def test_v4_inputs_reject_run_selection_latest_run_auto_selection(tmp_path: Path) -> None:
    paths = _write_valid_stage1_fixture(tmp_path)
    selection = _read_json(paths["run_selection"])
    selection["latest_run_auto_selection"] = True
    _write_json(paths["run_selection"], selection)
    _refresh_ref_in_inputs(paths["acceptance_inputs"], "run_selection_manifest", paths["run_selection"])

    with pytest.raises(ConfigError, match="RUN_SELECTION_MANIFEST 禁止 latest run"):
        inspect_v4_inputs(paths["acceptance_inputs"], assert_complete=True)


def _write_valid_stage1_fixture(tmp_path: Path) -> dict[str, Path]:
    rollout_dir = tmp_path / "rollout"
    tool_dir = tmp_path / "tool"
    run_dir = tmp_path / "run"
    export_dir = tmp_path / "export"
    cards_dir = tmp_path / "cards"
    for directory in (rollout_dir, tool_dir, run_dir, export_dir, cards_dir):
        directory.mkdir(parents=True)

    _write_json(rollout_dir / "rollout_queue_manifest.json", {"schema_version": V4_ROLLOUT_QUEUE_MANIFEST_VERSION})
    _write_jsonl(rollout_dir / "worker_run_log.jsonl", [{"schema_version": V4_WORKER_RUN_LOG_ENTRY_VERSION}])
    _write_json(rollout_dir / "lease_state_report.json", {"schema_version": V4_LEASE_STATE_REPORT_VERSION})
    _write_json(rollout_dir / "retry_policy_report.json", {"schema_version": V4_RETRY_POLICY_REPORT_VERSION})
    _write_json(rollout_dir / "budget_control_report.json", {"schema_version": V4_BUDGET_CONTROL_REPORT_VERSION})
    _write_json(rollout_dir / "resource_lock_report.json", {"schema_version": V4_RESOURCE_LOCK_REPORT_VERSION})
    _write_json(rollout_dir / "resource_usage_report.json", {"schema_version": V4_RESOURCE_USAGE_REPORT_VERSION})
    _write_json(rollout_dir / "batch_resume_report.json", {"schema_version": V4_BATCH_RESUME_REPORT_VERSION})
    _write_json(rollout_dir / "checkpoint_state_report.json", {"schema_version": V4_CHECKPOINT_STATE_REPORT_VERSION})

    run_selection_query = tmp_path / "run_selection_query_report.json"
    _write_json(
        run_selection_query,
        {
            "schema_version": V4_RUN_SELECTION_QUERY_REPORT_VERSION,
            "query_predicate": {"status": "selected"},
            "input_manifest_hash": "1" * 64,
        },
    )
    task_freeze = build_v4_task_freeze(
        implementation_inputs=Path("docs/v4/evidence/implementation-inputs/v4_implementation_input_manifest.json"),
        output_dir=tmp_path / "task-freeze-artifacts",
    )
    task_validity = task_freeze.parent / "task_validity_report.json"

    _write_json(tool_dir / "permission_policy_snapshot.json", {"schema_version": "repo_harness_v4_permission_policy_snapshot_v0"})
    _write_json(tool_dir / "hook_policy_snapshot.json", {"schema_version": "repo_harness_v4_hook_policy_snapshot_v0"})
    _write_json(tool_dir / "mcp_policy_snapshot.json", {"schema_version": "repo_harness_v4_mcp_policy_snapshot_v0"})
    _write_json(tool_dir / "tool_contract_v4_snapshot.json", {"schema_version": V4_TOOL_CONTRACT_SNAPSHOT_VERSION})
    _write_json(tool_dir / "hook_audit_report.json", {"schema_version": "repo_harness_v4_hook_audit_report_v0"})
    _write_jsonl(tool_dir / "permission_decision_trace.jsonl", [{"schema_version": "repo_harness_v4_permission_decision_trace_entry_v0"}])
    _write_jsonl(tool_dir / "tool_lifecycle_trace.jsonl", [{"schema_version": V4_TOOL_LIFECYCLE_TRACE_ENTRY_VERSION}])

    _write_json(run_dir / "v4_agent_run_integration_report.json", {"schema_version": V4_AGENT_RUN_INTEGRATION_REPORT_VERSION})
    _write_json(run_dir / "runspec_metadata_report.json", {"schema_version": "repo_harness_v4_runspec_metadata_report_v0"})
    _write_json(run_dir / "final_verifier_boundary_report.json", {"schema_version": "repo_harness_v4_final_verifier_boundary_report_v0"})
    _write_json(run_dir / "prepared_messages_binding_report.json", {"schema_version": "repo_harness_v4_prepared_messages_binding_report_v0"})
    _write_json(run_dir / "interrupted_run_recovery_report.json", {"schema_version": "repo_harness_v4_interrupted_run_recovery_report_v0"})
    _write_jsonl(run_dir / "transcript.jsonl", [{"schema_version": "repo_harness_v4_transcript_record_v0"}])
    _write_jsonl(run_dir / "events.jsonl", [{"schema_version": "repo_harness_v4_event_record_v0"}])
    _write_json(run_dir / "artifacts.json", {"schema_version": "repo_harness_v4_artifacts_manifest_v0"})
    _write_json(run_dir / "run_config_facts.json", {"schema_version": "repo_harness_v4_run_config_facts_v0"})
    _write_json(run_dir / "run_metadata.json", {"schema_version": "repo_harness_v4_run_metadata_v0"})
    _write_json(run_dir / "interrupted_run_facts.json", {"schema_version": "repo_harness_v4_interrupted_run_facts_v0"})
    _write_json(run_dir / "crash_facts.json", {"schema_version": "repo_harness_v4_crash_facts_v0"})
    _write_json(run_dir / "trajectory_store_integrity_report.json", {"schema_version": V4_TRAJECTORY_STORE_INTEGRITY_REPORT_VERSION})
    _write_json(export_dir / "trajectory_quality_manifest.json", {"schema_version": V4_EXPORT_QUALITY_MANIFEST_VERSION})
    _write_json(export_dir / "sample_tier_manifest.json", {"schema_version": "repo_harness_v4_sample_tier_manifest_v0"})
    _write_jsonl(export_dir / "failure_dataset.jsonl", [{"schema_version": "repo_harness_v4_failure_dataset_entry_v0"}])
    _write_json(export_dir / "packing_manifest.json", {"schema_version": "repo_harness_v4_packing_manifest_v0"})
    _write_json(export_dir / "reward_audit_report.json", {"schema_version": "repo_harness_v4_reward_audit_report_v0"})
    _write_json(export_dir / "reward_hacking_risk_audit_report.json", {"schema_version": "repo_harness_v4_reward_hacking_risk_audit_report_v0"})
    _write_json(export_dir / "patch_quality_report.json", {"schema_version": "repo_harness_v4_patch_quality_report_v0"})
    _write_json(export_dir / "test_overfitting_risk_audit_report.json", {"schema_version": "repo_harness_v4_test_overfitting_risk_audit_report_v0"})
    _write_json(export_dir / "preference_pair_trainability_report.json", {"schema_version": "repo_harness_v4_preference_pair_trainability_report_v0"})
    _write_json(export_dir / "blocked_pair_report.json", {"schema_version": "repo_harness_v4_blocked_pair_report_v0"})
    _write_json(cards_dir / "cards_manifest.json", {"schema_version": V4_CARDS_MANIFEST_VERSION})
    (cards_dir / "dataset_card.md").write_text("# Dataset card\n", encoding="utf-8")
    _write_json(cards_dir / "dataset_card.json", {"schema_version": "repo_harness_v4_dataset_card_v0"})
    _write_json(cards_dir / "run_card.json", {"schema_version": "repo_harness_v4_run_card_v0"})
    _write_json(cards_dir / "export_card.json", {"schema_version": "repo_harness_v4_export_card_v0"})
    _write_json(cards_dir / "provenance_summary.json", {"schema_version": "repo_harness_v4_provenance_summary_v0"})
    _write_json(cards_dir / "contamination_scan_summary.json", {"schema_version": "repo_harness_v4_contamination_scan_summary_v0"})
    _write_json(cards_dir / "repro_command_index.json", {"schema_version": "repo_harness_v4_repro_command_index_v0"})
    task_visibility_scan = tmp_path / "task_visibility_scan_report.json"
    _write_json(task_visibility_scan, {"schema_version": "repo_harness_v4_task_visibility_scan_report_v0"})
    scan_summary = tmp_path / "contamination_scan_summary.json"
    _write_json(scan_summary, {"schema_version": "repo_harness_v4_contamination_scan_summary_v0"})
    scan_report = tmp_path / "contamination_scan_report.json"
    _write_json(
        scan_report,
        {
            "schema_version": V4_CONTAMINATION_SCAN_REPORT_VERSION,
            "clean": True,
            "findings": [],
            "denylist_version": V4_CONTAMINATION_DENYLIST_VERSION,
            "denylist_sha256": v4_contamination_denylist_sha256(),
            "allowlist_policy_version": V4_ALLOWLIST_POLICY_VERSION,
            "card_claim_denylist_version": V4_CARD_CLAIM_DENYLIST_VERSION,
            "card_claim_denylist_sha256": v4_card_claim_denylist_sha256(),
            "artifact_refs_by_name": {
                "task_visibility_scan_report.json": _file_ref(task_visibility_scan, "task_visibility_scan"),
                "contamination_scan_summary.json": _file_ref(scan_summary, "contamination_scan_summary")
            },
        },
    )

    tracking = tmp_path / "artifact_inspect_tracking_table.json"
    _write_json(tracking, build_artifact_inspect_tracking_table_payload())
    run_selection = tmp_path / "run_selection_manifest.json"
    _write_json(
        run_selection,
        {
            "schema_version": V4_RUN_SELECTION_MANIFEST_VERSION,
            "selection_mode": "explicit",
            "latest_run_auto_selection": False,
            "entries": [{"role": "v4_rollout_orchestration", "run_ref": "runs/v4-selected-run"}],
        },
    )
    command_log = tmp_path / "acceptance_command_log.jsonl"
    _write_jsonl(command_log, [{"schema_version": "repo_harness_command_log_entry_v4_v0", "command_name": "fixture"}])
    doc = tmp_path / "pre_acceptance_doc.md"
    doc.write_text("# Pre acceptance\n", encoding="utf-8")

    acceptance_inputs = tmp_path / "v4_acceptance_inputs.json"
    refs_by_category = {
        "run_selection_manifest": [_file_ref(run_selection, "run_selection_manifest")],
        "v2_acceptance": [_file_ref(task_freeze, "v2_acceptance")],
        "v3_acceptance": [_file_ref(task_freeze, "v3_acceptance")],
        "v3_acceptance_bundle": [_file_ref(task_freeze, "v3_acceptance_bundle")],
        "implementation_inputs": [_file_ref(task_freeze, "implementation_inputs")],
        "rollout_queue": [_file_ref(rollout_dir, "rollout_queue")],
        "lease_state": [_file_ref(rollout_dir, "lease_state")],
        "retry_policy": [_file_ref(rollout_dir, "retry_policy")],
        "budget_control": [_file_ref(rollout_dir, "budget_control")],
        "resource_locks": [_file_ref(rollout_dir, "resource_locks")],
        "resource_usage": [_file_ref(rollout_dir, "resource_usage")],
        "batch_resume": [_file_ref(rollout_dir, "batch_resume")],
        "run_selection_query": [_file_ref(run_selection_query, "run_selection_query")],
        "task_freeze": [_file_ref(task_freeze, "task_freeze")],
        "task_validity": [_file_ref(task_validity, "task_validity")],
        "tool_contract": [_file_ref(tool_dir, "tool_contract")],
        "tool_lifecycle": [_file_ref(tool_dir, "tool_lifecycle")],
        "agent_run_integration": [_file_ref(run_dir, "agent_run_integration")],
        "trajectory_store": [_file_ref(run_dir, "trajectory_store")],
        "export_quality": [_file_ref(export_dir, "export_quality")],
        "cards": [_file_ref(cards_dir, "cards")],
        "command_log": [_file_ref(command_log, "command_log")],
        "pre_acceptance_docs": [_file_ref(doc, "pre_acceptance_docs")],
    }
    _write_json(
        acceptance_inputs,
        {
            "schema_version": V4_ACCEPTANCE_INPUTS_VERSION,
            "selection_mode": "explicit",
            "latest_run_auto_selection": False,
            "input_refs_by_category": refs_by_category,
            "artifact_inspect_tracking_table_ref": _file_ref(tracking, "artifact_inspect_tracking_table"),
        },
    )
    acceptance_report = tmp_path / "v4_acceptance_report.json"
    _write_json(
        acceptance_report,
        {
            "schema_version": V4_ACCEPTANCE_REPORT_VERSION,
            "status": "passed",
            "acceptance_inputs_ref": _file_ref(acceptance_inputs, "v4_acceptance_inputs"),
            "acceptance_command_log_ref": _file_ref(command_log, "acceptance_command_log"),
            "role_statuses": {
                "v3_regression": "passed",
                "v2_regression": "passed",
                "real_repository_regression": "passed",
                "swebench_like_regression": "passed",
                "v4_pr_issue_task_freeze": "passed",
                "v4_swebench_like_task_freeze": "passed",
                "v4_rollout_orchestration": "passed",
                "v4_rollout_resume": "passed",
                "v4_agent_run_integration": "passed",
                "v4_export_quality": "passed",
                "v4_tool_lifecycle_audit": "passed",
                "v4_cards": "passed",
            },
        },
    )
    acceptance_bundle = tmp_path / "acceptance_bundle_manifest.json"
    _write_json(
        acceptance_bundle,
        {
            "schema_version": V4_ACCEPTANCE_BUNDLE_MANIFEST_VERSION,
            "acceptance_report_ref": _file_ref(acceptance_report, "v4_acceptance_report"),
            "acceptance_inputs_ref": _file_ref(acceptance_inputs, "v4_acceptance_inputs"),
            "acceptance_command_log_ref": _file_ref(command_log, "acceptance_command_log"),
        },
    )
    return {
        "rollout_dir": rollout_dir,
        "tool_dir": tool_dir,
        "run_dir": run_dir,
        "export_dir": export_dir,
        "cards_dir": cards_dir,
        "run_selection_query": run_selection_query,
        "task_freeze": task_freeze,
        "task_validity": task_validity,
        "scan_report": scan_report,
        "run_selection": run_selection,
        "acceptance_inputs": acceptance_inputs,
        "acceptance_report": acceptance_report,
        "acceptance_bundle": acceptance_bundle,
    }


def _refresh_ref_in_inputs(path: Path, category: str, target: Path) -> None:
    payload = _read_json(path)
    payload["input_refs_by_category"][category][0] = _file_ref(target, category)
    _write_json(path, payload)


def _file_ref(path: Path, category: str) -> dict:
    return {
        "path": path.as_posix(),
        "kind": "directory" if path.is_dir() else (path.suffix.lstrip(".") or "file"),
        "category": category,
        "sha256": compute_source_tree_hash(path) if path.is_dir() else sha256_file(path),
        "size_bytes": 0 if path.is_dir() else path.stat().st_size,
    }


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
