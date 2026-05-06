import json
import hashlib
from pathlib import Path

import pytest

from repo_harness.errors import ConfigError
from repo_harness.v5_acceptance import (
    build_acceptance_bundle,
    build_acceptance_inputs,
    build_acceptance_report,
    build_final_command_log,
    build_pre_bundle_command_log,
    inspect_acceptance_bundle,
    plan_acceptance_bundle_build_entry,
    plan_acceptance_bundle_inspect_entry,
)
from repo_harness.v5_evidence import inspect_v5_acceptance, inspect_v5_inputs


def test_v5_acceptance_core_bundle_passes_and_resume_ready_is_blocked(tmp_path: Path) -> None:
    paths = _write_stage6_inputs(tmp_path)
    acceptance_inputs = build_acceptance_inputs(
        output_dir=tmp_path / "acceptance",
        full_test_summary="765 passed in 706.29s",
        v5_implementation_logs=[paths["implementation_log"]],
        v5_review_records=[paths["review_record"]],
        **{key: value for key, value in paths.items() if key not in {"implementation_log", "review_record"}},
    )

    assert "Inspect V5 inputs: complete" in inspect_v5_inputs(acceptance_inputs, assert_complete=True)
    report = build_acceptance_report(acceptance_inputs=acceptance_inputs, output_dir=tmp_path / "acceptance")
    integrity = tmp_path / "acceptance" / "v5_acceptance_report_reference_integrity_report.json"
    core_entry = tmp_path / "acceptance" / "inspect_v5_acceptance_core_command_log_entry.json"
    assert "Inspect V5 acceptance: complete" in inspect_v5_acceptance(
        report,
        assert_core_complete=True,
        reference_integrity_output=integrity,
        command_log_entry_output=core_entry,
    )
    resume_entry = tmp_path / "acceptance" / "inspect_v5_acceptance_resume_ready_command_log_entry.json"
    with pytest.raises(ConfigError):
        inspect_v5_acceptance(
            report,
            assert_resume_ready=True,
            reference_integrity_input=integrity,
            command_log_entry_output=resume_entry,
        )
    assert json.loads(resume_entry.read_text(encoding="utf-8"))["exit_code"] == 1

    pre_bundle = build_pre_bundle_command_log(
        base_command_log=tmp_path / "acceptance" / "v5_stage6_command_log_draft.jsonl",
        command_log_entries=[core_entry, resume_entry],
        output=tmp_path / "acceptance" / "v5_pre_bundle_command_log.jsonl",
    )
    final_doc = _write_json_file(tmp_path / "docs" / "v5" / "final-acceptance.md", {"doc": "final"})
    walkthrough = _write_json_file(tmp_path / "docs" / "v5" / "walkthrough.md", {"doc": "walkthrough"})
    pre_final_bundle = build_acceptance_bundle(
        acceptance_report=report,
        post_report_inspect_output=integrity,
        pre_bundle_command_log=pre_bundle,
        bundle_build_command_log_entry_output=tmp_path / "acceptance" / "build_v5_acceptance_bundle_command_log_entry.json",
        documentation_refs=[final_doc, walkthrough],
        output=tmp_path / "acceptance" / "v5_acceptance_bundle_manifest_pre_final_log.json",
    )
    final_bundle_path = tmp_path / "acceptance" / "v5_acceptance_bundle_manifest.json"
    final_log_path = tmp_path / "acceptance" / "v5_final_acceptance_command_log.jsonl"
    planned_build_entry = plan_acceptance_bundle_build_entry(
        acceptance_report=report,
        post_report_inspect_output=integrity,
        pre_bundle_command_log=pre_bundle,
        documentation_refs=[final_doc, walkthrough],
        bundle_build_command_log_entry_output=tmp_path / "acceptance" / "build_v5_acceptance_bundle_final_command_log_sync_entry.json",
        output_bundle=final_bundle_path,
        final_command_log=final_log_path,
        doc_sync_from_bundle=pre_final_bundle,
        output=tmp_path / "acceptance" / "plan_build_v5_acceptance_bundle_final_command_log_entry.json",
    )
    inspect_entry = plan_acceptance_bundle_inspect_entry(
        acceptance_bundle=final_bundle_path,
        final_command_log=final_log_path,
        self_referential_acceptance_bundle=True,
        output=tmp_path / "acceptance" / "inspect_acceptance_bundle_command_log_entry.json",
    )
    final_log = build_final_command_log(
        pre_bundle_command_log=pre_bundle,
        command_log_entries=[planned_build_entry, inspect_entry],
        output=final_log_path,
    )
    final_bundle = build_acceptance_bundle(
        acceptance_report=report,
        post_report_inspect_output=integrity,
        pre_bundle_command_log=pre_bundle,
        bundle_build_command_log_entry_output=tmp_path / "acceptance" / "build_v5_acceptance_bundle_final_command_log_sync_entry.json",
        documentation_refs=[final_doc, walkthrough],
        output=final_bundle_path,
        doc_sync_from_bundle=pre_final_bundle,
        final_command_log=final_log,
    )
    final_log_entries = [
        json.loads(line)
        for line in final_log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    final_build_entries = [
        entry for entry in final_log_entries if entry.get("command_name") == "build-v5-acceptance-bundle"
    ]
    assert final_build_entries[-1]["self_referential_output_paths"][0] == final_bundle.as_posix()
    final_inspect_entries = [
        entry for entry in final_log_entries if entry.get("command_name") == "inspect-acceptance-bundle"
    ]
    assert final_bundle.as_posix() in final_inspect_entries[-1]["self_referential_input_paths"]
    assert "Inspect acceptance bundle: immutable" in inspect_acceptance_bundle(
        final_bundle,
        final_command_log=final_log,
        assert_immutable=True,
    )


def test_v5_inputs_rejects_tampered_evidence_ref(tmp_path: Path) -> None:
    paths = _write_stage6_inputs(tmp_path)
    acceptance_inputs = build_acceptance_inputs(
        output_dir=tmp_path / "acceptance",
        full_test_summary="765 passed in 706.29s",
        v5_implementation_logs=[paths["implementation_log"]],
        v5_review_records=[paths["review_record"]],
        **{key: value for key, value in paths.items() if key not in {"implementation_log", "review_record"}},
    )
    payload = _read_json(acceptance_inputs)
    payload["v5_evidence_refs"][0]["path"] = "does/not/exist.json"
    payload["v5_evidence_refs"][0]["sha256"] = "0" * 64
    payload["v5_evidence_refs"][0]["size_bytes"] = 999999
    acceptance_inputs.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(ConfigError):
        inspect_v5_inputs(acceptance_inputs, assert_complete=True)


def test_v5_inputs_rejects_tampered_nested_public_demo_artifact_ref(tmp_path: Path) -> None:
    paths = _write_stage6_inputs(tmp_path)
    public_artifact = _write_json_file(tmp_path / "public_artifact.json", {"schema_version": "public_artifact", "status": "passed"})
    public_bundle = _read_json(paths["v5_public_demo_bundle_manifest"])
    public_bundle["artifact_refs"] = [_v5_ref(public_artifact, "v5_public_artifact")]
    paths["v5_public_demo_bundle_manifest"].write_text(
        json.dumps(public_bundle, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    acceptance_inputs = build_acceptance_inputs(
        output_dir=tmp_path / "acceptance",
        full_test_summary="765 passed in 706.29s",
        v5_implementation_logs=[paths["implementation_log"]],
        v5_review_records=[paths["review_record"]],
        **{key: value for key, value in paths.items() if key not in {"implementation_log", "review_record"}},
    )

    public_bundle["artifact_refs"][0]["path"] = (tmp_path / "missing_public_artifact.json").as_posix()
    public_bundle["artifact_refs"][0]["sha256"] = "0" * 64
    public_bundle["artifact_refs"][0]["size_bytes"] = 12345
    paths["v5_public_demo_bundle_manifest"].write_text(
        json.dumps(public_bundle, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _refresh_acceptance_inputs_ref(acceptance_inputs, "v5_public_demo_bundle_manifest", paths["v5_public_demo_bundle_manifest"])

    with pytest.raises(ConfigError):
        inspect_v5_inputs(acceptance_inputs, assert_complete=True)
    report = build_acceptance_report(acceptance_inputs=acceptance_inputs, output_dir=tmp_path / "acceptance_report")
    with pytest.raises(ConfigError):
        inspect_v5_acceptance(report, assert_core_complete=True)


def test_v5_acceptance_core_rejects_failed_reference_integrity(tmp_path: Path) -> None:
    paths = _write_stage6_inputs(tmp_path)
    acceptance_inputs = build_acceptance_inputs(
        output_dir=tmp_path / "acceptance",
        full_test_summary="765 passed in 706.29s",
        v5_implementation_logs=[paths["implementation_log"]],
        v5_review_records=[paths["review_record"]],
        **{key: value for key, value in paths.items() if key not in {"implementation_log", "review_record"}},
    )
    report = build_acceptance_report(acceptance_inputs=acceptance_inputs, output_dir=tmp_path / "acceptance")
    payload = _read_json(report)
    payload["acceptance_inputs_ref"]["path"] = "does/not/exist.json"
    report.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(ConfigError):
        inspect_v5_acceptance(report, assert_core_complete=True)


def test_v5_acceptance_rejects_reference_integrity_input_with_failed_status(tmp_path: Path) -> None:
    paths = _write_stage6_inputs(tmp_path)
    acceptance_inputs = build_acceptance_inputs(
        output_dir=tmp_path / "acceptance",
        full_test_summary="765 passed in 706.29s",
        v5_implementation_logs=[paths["implementation_log"]],
        v5_review_records=[paths["review_record"]],
        **{key: value for key, value in paths.items() if key not in {"implementation_log", "review_record"}},
    )
    report = build_acceptance_report(acceptance_inputs=acceptance_inputs, output_dir=tmp_path / "acceptance")
    integrity = _write_json_file(
        tmp_path / "acceptance" / "v5_acceptance_report_reference_integrity_report.json",
        {
            "schema_version": "repo_harness_v5_acceptance_report_reference_integrity_report_v0",
            "status": "failed",
            "unbound_critical_evidence_finding_count": 0,
            "post_report_output_used_as_report_input_count": 0,
            "bundle_output_used_as_report_input_count": 0,
        },
    )

    with pytest.raises(ConfigError):
        inspect_v5_acceptance(report, assert_core_complete=True, reference_integrity_input=integrity)


def test_v5_acceptance_rejects_reference_integrity_input_with_nonzero_failure_count(tmp_path: Path) -> None:
    paths = _write_stage6_inputs(tmp_path)
    acceptance_inputs = build_acceptance_inputs(
        output_dir=tmp_path / "acceptance",
        full_test_summary="765 passed in 706.29s",
        v5_implementation_logs=[paths["implementation_log"]],
        v5_review_records=[paths["review_record"]],
        **{key: value for key, value in paths.items() if key not in {"implementation_log", "review_record"}},
    )
    report = build_acceptance_report(acceptance_inputs=acceptance_inputs, output_dir=tmp_path / "acceptance")
    integrity = _write_json_file(
        tmp_path / "acceptance" / "v5_acceptance_report_reference_integrity_report.json",
        {
            "schema_version": "repo_harness_v5_acceptance_report_reference_integrity_report_v0",
            "status": "passed",
            "unbound_critical_evidence_finding_count": 0,
            "recursive_evidence_ref_failure_count": 1,
            "post_report_output_used_as_report_input_count": 0,
            "bundle_output_used_as_report_input_count": 0,
        },
    )

    with pytest.raises(ConfigError):
        inspect_v5_acceptance(report, assert_core_complete=True, reference_integrity_input=integrity)


def test_v5_bundle_rejects_tampered_final_command_log(tmp_path: Path) -> None:
    paths = _write_stage6_inputs(tmp_path)
    acceptance_inputs = build_acceptance_inputs(
        output_dir=tmp_path / "acceptance",
        full_test_summary="765 passed in 706.29s",
        v5_implementation_logs=[paths["implementation_log"]],
        v5_review_records=[paths["review_record"]],
        **{key: value for key, value in paths.items() if key not in {"implementation_log", "review_record"}},
    )
    report = build_acceptance_report(acceptance_inputs=acceptance_inputs, output_dir=tmp_path / "acceptance")
    integrity = tmp_path / "acceptance" / "v5_acceptance_report_reference_integrity_report.json"
    core_entry = tmp_path / "acceptance" / "inspect_v5_acceptance_core_command_log_entry.json"
    inspect_v5_acceptance(report, assert_core_complete=True, reference_integrity_output=integrity, command_log_entry_output=core_entry)
    resume_entry = tmp_path / "acceptance" / "inspect_v5_acceptance_resume_ready_command_log_entry.json"
    with pytest.raises(ConfigError):
        inspect_v5_acceptance(report, assert_resume_ready=True, reference_integrity_input=integrity, command_log_entry_output=resume_entry)
    pre_bundle = build_pre_bundle_command_log(
        base_command_log=tmp_path / "acceptance" / "v5_stage6_command_log_draft.jsonl",
        command_log_entries=[core_entry, resume_entry],
        output=tmp_path / "acceptance" / "v5_pre_bundle_command_log.jsonl",
    )
    final_doc = _write_json_file(tmp_path / "docs" / "v5" / "final-acceptance.md", {"doc": "final"})
    walkthrough = _write_json_file(tmp_path / "docs" / "v5" / "walkthrough.md", {"doc": "walkthrough"})
    bundle_entry = tmp_path / "acceptance" / "build_v5_acceptance_bundle_command_log_entry.json"
    pre_final_bundle = build_acceptance_bundle(
        acceptance_report=report,
        post_report_inspect_output=integrity,
        pre_bundle_command_log=pre_bundle,
        bundle_build_command_log_entry_output=bundle_entry,
        documentation_refs=[final_doc, walkthrough],
        output=tmp_path / "acceptance" / "v5_acceptance_bundle_manifest_pre_final_log.json",
    )
    inspect_entry = plan_acceptance_bundle_inspect_entry(
        acceptance_bundle=pre_final_bundle,
        final_command_log=tmp_path / "acceptance" / "v5_final_acceptance_command_log.jsonl",
        output=tmp_path / "acceptance" / "inspect_acceptance_bundle_command_log_entry.json",
    )
    final_log = build_final_command_log(
        pre_bundle_command_log=pre_bundle,
        command_log_entries=[bundle_entry, inspect_entry],
        output=tmp_path / "acceptance" / "v5_final_acceptance_command_log.jsonl",
    )
    final_bundle = build_acceptance_bundle(
        acceptance_report=report,
        post_report_inspect_output=integrity,
        pre_bundle_command_log=pre_bundle,
        bundle_build_command_log_entry_output=tmp_path / "acceptance" / "build_v5_acceptance_bundle_final_command_log_sync_entry.json",
        documentation_refs=[final_doc, walkthrough],
        output=tmp_path / "acceptance" / "v5_acceptance_bundle_manifest.json",
        doc_sync_from_bundle=pre_final_bundle,
        final_command_log=final_log,
    )
    with pytest.raises(ConfigError, match="当前最终 bundle"):
        inspect_acceptance_bundle(final_bundle, final_command_log=final_log, assert_immutable=True)
    entries = [json.loads(line) for line in final_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    for entry in entries:
        if entry.get("command_name") == "inspect-acceptance-bundle":
            entry["argv"][2] = (tmp_path / "acceptance" / "wrong_bundle.json").as_posix()
            entry["input_refs"][0]["path"] = (tmp_path / "acceptance" / "wrong_bundle.json").as_posix()
    final_log.write_text("".join(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n" for entry in entries), encoding="utf-8")

    with pytest.raises(ConfigError):
        inspect_acceptance_bundle(final_bundle, final_command_log=final_log, assert_immutable=True)


def _write_stage6_inputs(tmp_path: Path) -> dict:
    paths = {name: _write_json_file(tmp_path / f"{name}.json", {"schema_version": name, "status": "passed"}) for name in _GENERIC_INPUT_NAMES}
    paths["v4_doc_sync_acceptance_bundle"] = _write_json_file(
        tmp_path / "acceptance_bundle_manifest_doc_sync_20260505T075410Z.json",
        {"schema_version": "repo_harness_v4_acceptance_bundle_manifest_v0", "status": "passed"},
    )
    paths["v5_task_inventory_report"] = _write_json_file(
        tmp_path / "v5_task_inventory_report.json",
        {
            "schema_version": "repo_harness_v5_task_inventory_report_v0",
            "accepted_auditable_task_count": 12,
            "pr_issue_task_count": 8,
            "swebench_like_anchor_count": 4,
            "strict_inventory_gate": "passed",
            "source_mix": {"pr_issue": 8, "swebench_like_anchor": 4},
        },
    )
    paths["v5_executed_run_matrix_manifest"] = _write_json_file(
        tmp_path / "v5_run_matrix_manifest_executed.json",
        {"schema_version": "repo_harness_v5_run_matrix_manifest_v0", "actual_provider_calls": 6, "status": "passed"},
    )
    paths["v5_matrix_compare_scope_report"] = _write_json_file(
        tmp_path / "v5_matrix_compare_scope_report.json",
        {"schema_version": "repo_harness_v5_matrix_compare_scope_report_v0", "comparison_task_count": 4, "status": "diagnostic_only"},
    )
    paths["v5_export_result_pack_manifest"] = _write_json_file(
        tmp_path / "v5_export_result_pack_manifest.json",
        {
            "schema_version": "repo_harness_v5_export_result_pack_manifest_v0",
            "partition_counts": {
                "real_provider_trainable_records": 2,
                "mock_or_replay_records": 0,
                "diagnostic_records": 1,
                "blocked_records": 1,
                "synthetic_safe_stress_records": 0,
            },
            "status": "passed",
        },
    )
    paths["v5_result_summary_table"] = _write_json_file(
        tmp_path / "v5_result_summary_table.json",
        {
            "schema_version": "repo_harness_v5_result_summary_table_v0",
            "real_provider_trainable_records": 2,
            "mock_or_replay_records": 0,
            "diagnostic_records": 1,
            "blocked_records": 1,
            "synthetic_safe_stress_records": 0,
            "real_provider_runs": {"denominator_excludes": ["mock_or_replay_records"]},
        },
    )
    paths["v5_resume_claim_gate_report"] = _write_json_file(
        tmp_path / "v5_resume_claim_gate_report.json",
        {
            "schema_version": "repo_harness_v5_resume_claim_gate_report_v0",
            "stage": "stage5_final",
            "allowed_claims": ["core"],
            "blocked_claims": ["multi-provider agent runs", "preference export completed", "interview-grade evaluation pack"],
            "provider_claim_status": "blocked_single_provider_family_deepseek_only",
            "preference_pair_claim_status": "blocked_no_real_comparable_pair",
            "demo_share_safe_status": "passed",
            "stress_test_claim_status": "not_claimed",
            "real_provider_families_with_actual_runs": ["deepseek"],
        },
    )
    paths["v5_public_demo_bundle_manifest"] = _write_json_file(
        tmp_path / "v5_public_demo_bundle_manifest.json",
        {
            "schema_version": "repo_harness_v5_public_demo_bundle_manifest_v0",
            "provider_raw_content_count": 0,
            "evaluator_only_content_count": 0,
            "model_visible_leak_count": 0,
            "share_safe_status": "passed",
            "artifact_refs": [],
        },
    )
    paths["implementation_log"] = _write_json_file(tmp_path / "implementation-log.md", {"log": "ok"})
    paths["review_record"] = _write_json_file(tmp_path / "review.md", {"review": "ok"})
    return paths


_GENERIC_INPUT_NAMES = (
    "v2_acceptance_report",
    "v3_acceptance_report",
    "v3_acceptance_bundle",
    "v4_acceptance_inputs",
    "v4_acceptance_report",
    "v4_doc_sync_acceptance_bundle",
    "v4_doc_sync_final_command_log",
    "v5_baseline_check_report",
    "v5_v4_closure_report",
    "v5_documentation_sync_report",
    "v5_preflight_input_binding",
    "v5_pre_acceptance_evidence_integrity_report",
    "v5_task_set_manifest",
    "v5_task_diversity_report",
    "v5_task_visibility_scan_report",
    "v5_run_matrix_manifest",
    "v5_provider_credential_gate_report",
    "v5_provider_cost_budget_report",
    "v5_preference_pair_blocked_report",
    "v5_failure_taxonomy_report",
    "v5_reward_source_taxonomy_report",
    "v5_interview_demo_card",
    "v5_canonical_demo_walkthrough",
    "v5_resume_artifact_index",
    "v5_repro_command_index",
    "v5_demo_transcript_index",
    "v5_permission_network_risk_audit_report",
    "v5_claude_code_invariant_mapping",
    "v5_interview_result_pack_manifest",
)


def _write_json_file(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _v5_ref(path: Path, kind: str) -> dict:
    return {
        "schema_version": "repo_harness_v5_evidence_ref_v0",
        "path": path.as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size_bytes": path.stat().st_size,
        "kind": kind,
        "purpose": "test fixture ref",
        "visibility": "public_safe",
        "share_safe": True,
        "producer_command": "test",
        "producer_stage": "test",
        "inspect_command": "test",
    }


def _refresh_acceptance_inputs_ref(acceptance_inputs: Path, kind: str, path: Path) -> None:
    payload = _read_json(acceptance_inputs)
    for ref in payload["v5_evidence_refs"]:
        if ref.get("kind") == kind:
            ref["path"] = path.as_posix()
            ref["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            ref["size_bytes"] = path.stat().st_size
            break
    else:
        raise AssertionError(f"missing acceptance inputs ref kind: {kind}")
    acceptance_inputs.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
