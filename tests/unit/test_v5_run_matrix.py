import json
import tarfile
from pathlib import Path

import pytest

from repo_harness.errors import ConfigError
from repo_harness.schema_versions import (
    V5_MATRIX_CELL_RESULT_VERSION,
    V5_PROVIDER_COST_BUDGET_REPORT_VERSION,
    V5_PROVIDER_CREDENTIAL_GATE_REPORT_VERSION,
    V5_TASK_DEFINITION_VERSION,
    V5_TASK_SET_MANIFEST_VERSION,
)
from repo_harness.v5_evidence import _evidence_ref, inspect_v5_run_matrix
from repo_harness.v5_run_matrix import build_comparison_reports, build_run_matrix_manifest


def test_v5_run_matrix_builder_creates_planned_manifest(tmp_path: Path) -> None:
    task_set = _write_task_set(tmp_path, count=6)
    provider_gate = _write_provider_gate(tmp_path)
    cost_budget = _write_cost_budget(tmp_path)

    manifest_path = build_run_matrix_manifest(
        task_set_manifest=task_set,
        provider_gate_report=provider_gate,
        provider_cost_budget_report=cost_budget,
        output_dir=tmp_path / "matrix",
        task_ids=[f"v5_task_{index:03d}" for index in range(1, 7)],
    )

    payload = _read_json(manifest_path)
    assert payload["planned_matrix_cell_count"] == 6
    assert payload["agent_run_started"] is False
    assert payload["provider_api_called"] is False
    assert {cell["provider_id"] for cell in payload["planned_matrix_cells"]} == {"deepseek"}
    assert "Inspect V5 run matrix: complete" in inspect_v5_run_matrix(
        manifest_path,
        assert_complete=True,
    )


def test_v5_run_matrix_builder_requires_deepseek_credential(tmp_path: Path) -> None:
    task_set = _write_task_set(tmp_path, count=6)
    provider_gate = _write_provider_gate(tmp_path, deepseek_status="missing")
    cost_budget = _write_cost_budget(tmp_path)

    with pytest.raises(ConfigError, match="deepseek active credential"):
        build_run_matrix_manifest(
            task_set_manifest=task_set,
            provider_gate_report=provider_gate,
            provider_cost_budget_report=cost_budget,
            output_dir=tmp_path / "matrix",
            task_ids=[f"v5_task_{index:03d}" for index in range(1, 7)],
        )


def test_v5_run_matrix_builder_can_add_openai_provider_cells(tmp_path: Path) -> None:
    task_set = _write_task_set(tmp_path, count=2)
    provider_gate = _write_provider_gate(tmp_path, openai_status="present")
    cost_budget = _write_cost_budget(tmp_path)

    manifest_path = build_run_matrix_manifest(
        task_set_manifest=task_set,
        provider_gate_report=provider_gate,
        provider_cost_budget_report=cost_budget,
        output_dir=tmp_path / "matrix",
        task_ids=["v5_task_001", "v5_task_002"],
        provider_ids=["deepseek", "openai"],
        openai_model_id="gpt-5.4-nano",
    )

    payload = _read_json(manifest_path)
    assert payload["planned_matrix_cell_count"] == 4
    assert {cell["provider_id"] for cell in payload["planned_matrix_cells"]} == {"deepseek", "openai"}
    openai_cells = [cell for cell in payload["planned_matrix_cells"] if cell["provider_id"] == "openai"]
    assert {cell["model_id"] for cell in openai_cells} == {"gpt-5.4-nano"}
    assert all(cell["provider_mode"] == "primary" for cell in openai_cells)
    assert "Inspect V5 run matrix: complete" in inspect_v5_run_matrix(
        manifest_path,
        assert_complete=True,
    )


def test_v5_run_matrix_inspect_accepts_executed_real_provider_evidence(tmp_path: Path) -> None:
    task_set = _write_task_set(tmp_path, count=6)
    provider_gate = _write_provider_gate(tmp_path)
    cost_budget = _write_cost_budget(tmp_path)
    manifest_path = build_run_matrix_manifest(
        task_set_manifest=task_set,
        provider_gate_report=provider_gate,
        provider_cost_budget_report=cost_budget,
        output_dir=tmp_path / "matrix",
        task_ids=[f"v5_task_{index:03d}" for index in range(1, 7)],
    )
    manifest = _read_json(manifest_path)
    execution_dir = tmp_path / "execution"
    runs_dir = execution_dir / "agent_runs"
    results_path = execution_dir / "v5_matrix_cell_results.jsonl"
    report_path = execution_dir / "v5_stage3b_run_matrix_execution_report.json"
    execution_dir.mkdir(parents=True)
    results = []
    for cell in manifest["planned_matrix_cells"]:
        run_id = f"v5_stage3b_deepseek_{cell['task_id']}"
        run_dir = runs_dir / run_id
        run_dir.mkdir(parents=True)
        _write_json(
            run_dir / "artifacts.json",
            {"schema_version": "repo_harness_schema_v0", "run_id": run_id, "artifacts": []},
        )
        _write_json(
            run_dir / "final_verifier_boundary.json",
            {
                "schema_version": "repo_harness_v5_stage3b_final_verifier_boundary_v0",
                "run_id": run_id,
                "task_id": cell["task_id"],
                "final_verifier_ran": False,
                "accepted": False,
            },
        )
        _write_jsonl(
            run_dir / "events.jsonl",
            [
                {
                    "event_type": "model_call_completed",
                    "data": {
                        "provider": "deepseek",
                        "model_error_type": None,
                        "input_tokens": 10,
                        "output_tokens": 5,
                        "cached_tokens": 0,
                    },
                }
            ],
        )
        _write_jsonl(run_dir / "transcript.jsonl", [{"role": "assistant", "content_preview": "ok"}])
        results.append(
            {
                "schema_version": V5_MATRIX_CELL_RESULT_VERSION,
                "cell_id": cell["cell_id"],
                "task_id": cell["task_id"],
                "provider_id": "deepseek",
                "provider_mode": "primary",
                "model_id": cell.get("model_id", "deepseek-v4-flash"),
                "scaffold_id": cell["scaffold_id"],
                "budget_policy_id": cell["budget_policy_id"],
                "tool_policy_id": cell["tool_policy_id"],
                "context_policy_id": cell["context_policy_id"],
                "environment_id": cell["environment_id"],
                "source_tree_hash": cell["source_tree_hash"],
                "final_verifier_plan_ref": cell.get("final_verifier_plan_ref"),
                "run_id": run_id,
                "run_dir": run_dir.as_posix(),
                "final_verifier_status": "not_executed_stage3b_minimal_provider_loop",
                "trajectory_ref": _ref(run_dir / "events.jsonl", "trajectory_events"),
                "transcript_ref": _ref(run_dir / "transcript.jsonl", "trajectory_transcript"),
                "artifact_manifest_ref": _ref(run_dir / "artifacts.json", "artifact_manifest"),
                "final_verifier_boundary_ref": _ref(run_dir / "final_verifier_boundary.json", "final_verifier_boundary"),
                "controlled_variables_ref": cell["controlled_variables_ref"],
                "normalized_provider_status": "primary_attempted",
                "actual_provider_call_count": 1,
                "provider_api_called": True,
                "raw_provider_redaction": {
                    "raw_provider_artifact_count": 0,
                    "raw_provider_redaction_failure_count": 0,
                    "all_raw_provider_artifacts_redacted": True,
                },
                "counts_toward_primary_accepted_rate": False,
                "counts_toward_core_real_provider_floor": True,
            }
        )
    _write_jsonl(results_path, results)
    _write_json(
        report_path,
        {
            "schema_version": "repo_harness_v5_run_matrix_execution_report_v0",
            "actual_provider_calls": 6,
            "max_real_provider_calls": 24,
            "real_agent_run_task_count": 6,
            "status": "passed",
        },
    )
    executed_path = execution_dir / "v5_run_matrix_manifest_executed.json"
    _write_json(
        executed_path,
        {
            **manifest,
            "agent_run_started": True,
            "provider_api_called": True,
            "matrix_cell_results_ref": _ref(results_path, "v5_matrix_cell_results"),
            "run_matrix_execution_report_ref": _ref(report_path, "v5_run_matrix_execution_report"),
            "actual_provider_calls": 6,
            "real_agent_run_task_count": 6,
            "real_provider_families_with_actual_runs": ["deepseek"],
            "status": "passed",
        },
    )

    assert "Inspect V5 run matrix: complete" in inspect_v5_run_matrix(
        executed_path,
        assert_complete=True,
    )


def test_v5_comparison_reports_block_resume_ready_multi_provider_claim(tmp_path: Path) -> None:
    executed_path = _write_executed_run_matrix_fixture(tmp_path)
    provider_gate = _write_provider_gate(tmp_path)

    compare_scope_path = build_comparison_reports(
        executed_run_matrix_manifest=executed_path,
        provider_gate_report=provider_gate,
        output_dir=tmp_path / "comparison",
    )

    assert "Inspect V5 run matrix: complete" in inspect_v5_run_matrix(
        compare_scope_path,
        assert_complete=True,
    )
    claim_gate = _read_json(tmp_path / "comparison" / "v5_resume_claim_gate_report.json")
    assert claim_gate["stage"] == "stage3_partial"
    assert "multi-provider agent runs" in claim_gate["blocked_claims"]
    assert claim_gate["provider_claim_status"] == "blocked_missing_two_task_deepseek_openai_provider_pairs"
    provider_report = _read_json(tmp_path / "comparison" / "v5_provider_comparison_report.json")
    assert provider_report["resume_ready_provider_comparison_satisfied"] is False
    assert provider_report["provider_families_with_actual_runs"] == ["deepseek"]


def test_v5_comparison_reports_accept_two_task_openai_deepseek_pairs(tmp_path: Path) -> None:
    executed_path = _write_executed_run_matrix_fixture(tmp_path)
    openai_executed_path = _write_openai_executed_run_matrix_fixture(tmp_path)
    provider_gate = _write_provider_gate(tmp_path, openai_status="present")

    compare_scope_path = build_comparison_reports(
        executed_run_matrix_manifest=executed_path,
        additional_executed_run_matrix_manifests=[openai_executed_path],
        provider_gate_report=provider_gate,
        output_dir=tmp_path / "comparison",
    )

    assert "Inspect V5 run matrix: complete" in inspect_v5_run_matrix(
        compare_scope_path,
        assert_complete=True,
    )
    claim_gate = _read_json(tmp_path / "comparison" / "v5_resume_claim_gate_report.json")
    assert claim_gate["provider_claim_status"] == "provider_axis_satisfied_two_task_deepseek_openai_pairs"
    assert "provider-axis supplemental comparison proof for two tasks across DeepSeek and OpenAI" in claim_gate["allowed_claims"]
    assert "multi-provider agent runs" not in claim_gate["allowed_claims"]
    assert "controlled multi-provider comparison" not in claim_gate["allowed_claims"]
    assert "controlled multi-provider comparison completed" in claim_gate["blocked_claims"]
    provider_report = _read_json(tmp_path / "comparison" / "v5_provider_comparison_report.json")
    assert provider_report["provider_axis_comparison_satisfied"] is True
    assert provider_report["resume_ready_provider_comparison_satisfied"] is False
    assert provider_report["counts_toward_resume_ready_acceptance"] is False
    assert provider_report["comparison_validity"] == "valid"
    assert provider_report["actual_records_by_provider"]["openai"] == 2


def test_v5_comparison_reports_reject_mismatched_final_verifier_plan(tmp_path: Path) -> None:
    executed_path = _write_executed_run_matrix_fixture(tmp_path)
    openai_executed_path = _write_openai_executed_run_matrix_fixture(
        tmp_path,
        mismatched_final_verifier_plan=True,
    )
    provider_gate = _write_provider_gate(tmp_path, openai_status="present")

    build_comparison_reports(
        executed_run_matrix_manifest=executed_path,
        additional_executed_run_matrix_manifests=[openai_executed_path],
        provider_gate_report=provider_gate,
        output_dir=tmp_path / "comparison_mismatch",
    )

    provider_report = _read_json(tmp_path / "comparison_mismatch" / "v5_provider_comparison_report.json")
    assert provider_report["comparison_validity"] == "invalid"
    assert provider_report["resume_ready_provider_comparison_satisfied"] is False
    assert provider_report["provider_pairs"] == []


def _write_task_set(tmp_path: Path, *, count: int) -> Path:
    task_refs = []
    for index in range(1, count + 1):
        task_id = f"v5_task_{index:03d}"
        archive = _write_archive(tmp_path / f"{task_id}.tar")
        adapter_input = tmp_path / f"{task_id}_adapter_visible.json"
        _write_json(
            adapter_input,
            {
                "schema_version": "repo_harness_v5_adapter_visible_task_input_v0",
                "task_id": task_id,
                "task_statement": f"Fix the sanitized task {task_id}.",
                "visible_constraints": ["Use only sanitized task input."],
                "ecosystem": "python",
                "visibility": "model_visible",
                "share_safe": True,
                "final_verifier_command": ["python", "-m", "pytest", "-q", "tests/test_example.py"],
            },
        )
        task_path = tmp_path / f"{task_id}.json"
        task_payload = {
            "schema_version": V5_TASK_DEFINITION_VERSION,
            "task_id": task_id,
            "task_family": "unit_test_fixture",
            "source_kind": "pr_issue_flow",
            "repo_url_or_archive_id": "local",
            "repository": "owner/repo",
            "base_commit": "a" * 40,
            "resolved_commit": "b" * 40,
            "source_archive_sha256": _sha256(archive),
            "source_tree_hash": "c" * 64,
            "task_input_hash": "d" * 64,
            "agent_run_ready": True,
            "comparison_ready": True,
            "accepted_auditable": True,
            "environment_id": "local_process_python",
            "adapter_visible_input_ref": _ref(adapter_input, "adapter_visible_task_input"),
            "evaluator_only_evidence_ref": _ref(task_path, "placeholder", exists=False),
            "baseline_verifier_plan_ref": _ref(task_path, "placeholder", exists=False),
            "final_verifier_plan_ref": _stable_final_verifier_plan_ref(task_id),
            "fail_to_pass_evidence_ref": _ref(task_path, "placeholder", exists=False),
            "pass_to_pass_evidence_ref": _ref(task_path, "placeholder", exists=False),
            "flaky_probe_report_ref": _ref(task_path, "placeholder", exists=False),
            "license_provenance_ref": _ref(task_path, "placeholder", exists=False),
            "dependency_cache_ref": _ref(task_path, "placeholder", exists=False),
            "environment_stability_ref": _ref(task_path, "placeholder", exists=False),
            "contamination_scan_ref": _ref(task_path, "placeholder", exists=False),
            "visibility_scan_ref": _ref(task_path, "placeholder", exists=False),
            "task_diversity_ref": _ref(task_path, "placeholder", exists=False),
            "source_archive_ref": _ref(archive, "source_archive"),
            "tool_policy_id": "stage3b_no_tool_calls",
            "context_policy_id": "stage3b_default_context_compaction",
            "budget_policy_id": "stage3b_constrained",
            "scaffold_id": "simple_react",
        }
        _write_json(task_path, task_payload)
        task_refs.append(_ref(task_path, "v5_task_definition"))
    task_set = tmp_path / "v5_task_set_manifest.json"
    _write_json(
        task_set,
        {
            "schema_version": V5_TASK_SET_MANIFEST_VERSION,
            "task_set_stage": "stage2b_merged_12",
            "strict_inventory_gate": "passed",
            "accepted_auditable_task_count": count,
            "pr_issue_task_count": count,
            "swebench_like_anchor_count": 3,
            "agent_run_ready_count": count,
            "comparison_ready_count": count,
            "task_refs": task_refs,
            "inventory_report_ref": {},
            "visibility_scan_ref": {},
            "status": "passed",
        },
    )
    return task_set


def _write_executed_run_matrix_fixture(tmp_path: Path) -> Path:
    task_set = _write_task_set(tmp_path, count=6)
    provider_gate = _write_provider_gate(tmp_path)
    cost_budget = _write_cost_budget(tmp_path)
    manifest_path = build_run_matrix_manifest(
        task_set_manifest=task_set,
        provider_gate_report=provider_gate,
        provider_cost_budget_report=cost_budget,
        output_dir=tmp_path / "matrix_for_comparison",
        task_ids=[f"v5_task_{index:03d}" for index in range(1, 7)],
    )
    manifest = _read_json(manifest_path)
    execution_dir = tmp_path / "execution_for_comparison"
    runs_dir = execution_dir / "agent_runs"
    results_path = execution_dir / "v5_matrix_cell_results.jsonl"
    report_path = execution_dir / "v5_stage3b_run_matrix_execution_report.json"
    execution_dir.mkdir(parents=True)
    results = []
    for cell in manifest["planned_matrix_cells"]:
        run_id = f"v5_stage3b_deepseek_{cell['task_id']}"
        run_dir = runs_dir / run_id
        run_dir.mkdir(parents=True)
        _write_json(
            run_dir / "artifacts.json",
            {"schema_version": "repo_harness_schema_v0", "run_id": run_id, "artifacts": []},
        )
        _write_json(run_dir / "final_verifier_boundary.json", {"accepted": False})
        _write_jsonl(
            run_dir / "events.jsonl",
            [{"event_type": "model_call_completed", "data": {"provider": "deepseek"}}],
        )
        _write_jsonl(run_dir / "transcript.jsonl", [{"role": "assistant", "content_preview": "ok"}])
        results.append(
            {
                "schema_version": V5_MATRIX_CELL_RESULT_VERSION,
                "cell_id": cell["cell_id"],
                "task_id": cell["task_id"],
                "provider_id": "deepseek",
                "provider_mode": "primary",
                "model_id": cell.get("model_id", "deepseek-v4-flash"),
                "scaffold_id": cell["scaffold_id"],
                "budget_policy_id": cell["budget_policy_id"],
                "tool_policy_id": cell["tool_policy_id"],
                "context_policy_id": cell["context_policy_id"],
                "environment_id": cell["environment_id"],
                "source_tree_hash": cell["source_tree_hash"],
                "final_verifier_plan_ref": cell.get("final_verifier_plan_ref"),
                "run_id": run_id,
                "run_dir": run_dir.as_posix(),
                "final_verifier_status": "not_executed_stage3b_minimal_provider_loop",
                "trajectory_ref": _ref(run_dir / "events.jsonl", "trajectory_events"),
                "transcript_ref": _ref(run_dir / "transcript.jsonl", "trajectory_transcript"),
                "artifact_manifest_ref": _ref(run_dir / "artifacts.json", "artifact_manifest"),
                "final_verifier_boundary_ref": _ref(run_dir / "final_verifier_boundary.json", "final_verifier_boundary"),
                "controlled_variables_ref": cell["controlled_variables_ref"],
                "normalized_provider_status": "primary_attempted",
                "actual_provider_call_count": 1,
                "provider_api_called": True,
                "raw_provider_redaction": {
                    "raw_provider_artifact_count": 0,
                    "raw_provider_redaction_failure_count": 0,
                    "all_raw_provider_artifacts_redacted": True,
                },
                "counts_toward_primary_accepted_rate": False,
                "counts_toward_core_real_provider_floor": True,
            }
        )
    _write_jsonl(results_path, results)
    _write_json(
        report_path,
        {
            "schema_version": "repo_harness_v5_run_matrix_execution_report_v0",
            "actual_provider_calls": 6,
            "max_real_provider_calls": 24,
            "real_agent_run_task_count": 6,
            "status": "passed",
        },
    )
    executed_path = execution_dir / "v5_run_matrix_manifest_executed.json"
    _write_json(
        executed_path,
        {
            **manifest,
            "agent_run_started": True,
            "provider_api_called": True,
            "matrix_cell_results_ref": _ref(results_path, "v5_matrix_cell_results"),
            "run_matrix_execution_report_ref": _ref(report_path, "v5_run_matrix_execution_report"),
            "actual_provider_calls": 6,
            "real_agent_run_task_count": 6,
            "real_provider_families_with_actual_runs": ["deepseek"],
            "status": "passed",
        },
    )
    return executed_path


def _write_openai_executed_run_matrix_fixture(
    tmp_path: Path,
    *,
    mismatched_final_verifier_plan: bool = False,
) -> Path:
    task_set = _write_task_set(tmp_path / "openai", count=2)
    provider_gate = _write_provider_gate(tmp_path / "openai", openai_status="present")
    cost_budget = _write_cost_budget(tmp_path / "openai")
    manifest_path = build_run_matrix_manifest(
        task_set_manifest=task_set,
        provider_gate_report=provider_gate,
        provider_cost_budget_report=cost_budget,
        output_dir=tmp_path / "openai" / "matrix_for_comparison",
        task_ids=["v5_task_001", "v5_task_002"],
        provider_ids=["openai"],
        openai_model_id="gpt-5.5",
    )
    manifest = _read_json(manifest_path)
    execution_dir = tmp_path / "openai" / "execution_for_comparison"
    runs_dir = execution_dir / "agent_runs"
    results_path = execution_dir / "v5_matrix_cell_results.jsonl"
    report_path = execution_dir / "v5_stage3b_run_matrix_execution_report.json"
    execution_dir.mkdir(parents=True)
    results = []
    for cell in manifest["planned_matrix_cells"]:
        run_id = f"v5_stage3b_openai_{cell['task_id']}"
        run_dir = runs_dir / run_id
        run_dir.mkdir(parents=True)
        _write_json(
            run_dir / "artifacts.json",
            {"schema_version": "repo_harness_schema_v0", "run_id": run_id, "artifacts": []},
        )
        _write_json(run_dir / "final_verifier_boundary.json", {"accepted": False})
        _write_jsonl(
            run_dir / "events.jsonl",
            [{"event_type": "model_call_completed", "data": {"provider": "openai"}}],
        )
        _write_jsonl(run_dir / "transcript.jsonl", [{"role": "assistant", "content_preview": "ok"}])
        final_verifier_plan_ref = cell.get("final_verifier_plan_ref")
        if mismatched_final_verifier_plan:
            final_verifier_plan_ref = {
                "schema_version": "repo_harness_v5_evidence_ref_v0",
                "path": f"mismatched/{cell['task_id']}.json",
                "sha256": "f" * 64,
                "size_bytes": 1,
                "kind": "final_verifier_plan",
                "purpose": "mismatched final verifier plan for negative test",
                "visibility": "evaluator_only",
                "share_safe": False,
                "producer_command": "test",
                "producer_stage": "test",
                "inspect_command": "inspect-v5-run-matrix",
            }
        results.append(
            {
                "schema_version": V5_MATRIX_CELL_RESULT_VERSION,
                "cell_id": cell["cell_id"],
                "task_id": cell["task_id"],
                "provider_id": "openai",
                "provider_mode": "primary",
                "model_id": cell["model_id"],
                "scaffold_id": cell["scaffold_id"],
                "budget_policy_id": cell["budget_policy_id"],
                "tool_policy_id": cell["tool_policy_id"],
                "context_policy_id": cell["context_policy_id"],
                "environment_id": cell["environment_id"],
                "source_tree_hash": cell["source_tree_hash"],
                "final_verifier_plan_ref": final_verifier_plan_ref,
                "run_id": run_id,
                "run_dir": run_dir.as_posix(),
                "final_verifier_status": "not_executed_stage3b_minimal_provider_loop",
                "trajectory_ref": _ref(run_dir / "events.jsonl", "trajectory_events"),
                "transcript_ref": _ref(run_dir / "transcript.jsonl", "trajectory_transcript"),
                "artifact_manifest_ref": _ref(run_dir / "artifacts.json", "artifact_manifest"),
                "final_verifier_boundary_ref": _ref(run_dir / "final_verifier_boundary.json", "final_verifier_boundary"),
                "controlled_variables_ref": cell["controlled_variables_ref"],
                "normalized_provider_status": "primary_attempted",
                "actual_provider_call_count": 1,
                "provider_api_called": True,
                "raw_provider_redaction": {
                    "raw_provider_artifact_count": 0,
                    "raw_provider_redaction_failure_count": 0,
                    "all_raw_provider_artifacts_redacted": True,
                },
                "counts_toward_primary_accepted_rate": False,
                "counts_toward_core_real_provider_floor": True,
            }
        )
    _write_jsonl(results_path, results)
    _write_json(
        report_path,
        {
            "schema_version": "repo_harness_v5_run_matrix_execution_report_v0",
            "actual_provider_calls": 2,
            "max_real_provider_calls": 24,
            "real_agent_run_task_count": 2,
            "status": "blocked",
        },
    )
    executed_path = execution_dir / "v5_run_matrix_manifest_executed.json"
    _write_json(
        executed_path,
        {
            **manifest,
            "agent_run_started": True,
            "provider_api_called": True,
            "matrix_cell_results_ref": _ref(results_path, "v5_matrix_cell_results"),
            "run_matrix_execution_report_ref": _ref(report_path, "v5_run_matrix_execution_report"),
            "actual_provider_calls": 2,
            "real_agent_run_task_count": 2,
            "real_provider_families_with_actual_runs": ["openai"],
            "status": "blocked",
        },
    )
    return executed_path


def _write_provider_gate(
    tmp_path: Path,
    *,
    deepseek_status: str = "present",
    openai_status: str = "missing",
) -> Path:
    path = tmp_path / "v5_provider_credential_gate_report.json"
    _write_json(
        path,
        {
            "schema_version": V5_PROVIDER_CREDENTIAL_GATE_REPORT_VERSION,
            "provider_families": ["openai", "deepseek", "anthropic_claude"],
            "credential_status_by_provider": {
                "deepseek": deepseek_status,
                "openai": openai_status,
                "anthropic_claude": "missing",
            },
            "adapter_status_by_provider": {
                "deepseek": "primary_supported",
                "openai": "primary_supported",
                "anthropic_claude": "adapter_not_implemented",
            },
            "structured_skips": [],
            "raw_secret_value_present": False,
            "provider_raw_content_policy": "audit_only_redacted_never_model_visible",
            "status": "passed",
        },
    )
    return path


def _write_cost_budget(tmp_path: Path) -> Path:
    path = tmp_path / "v5_provider_cost_budget_report.json"
    _write_json(
        path,
        {
            "schema_version": V5_PROVIDER_COST_BUDGET_REPORT_VERSION,
            "max_real_provider_calls": 24,
            "max_cost_usd": 5.0,
            "cost_proxy_formula": "test",
            "actual_real_provider_calls": 0,
            "actual_cost_proxy_usd": 0.0,
            "cost_limited_structured_skip": [],
            "budget_exhausted_before_run": False,
            "status": "passed",
        },
    )
    return path


def _write_archive(path: Path) -> Path:
    root = path.parent / f"{path.stem}_root"
    tests = root / "tests"
    tests.mkdir(parents=True)
    (tests / "test_example.py").write_text("def test_example():\n    assert True\n", encoding="utf-8")
    with tarfile.open(path, "w") as archive:
        archive.add(root, arcname=root.name)
    return path


def _ref(path: Path, kind: str, *, exists: bool = True) -> dict:
    if not exists and not path.exists():
        path.write_text("{}", encoding="utf-8")
    return _evidence_ref(
        path,
        kind=kind,
        purpose=kind,
        visibility="audit_only",
        producer_command="test",
        producer_stage="test",
        inspect_command="inspect-v5-run-matrix",
    )


def _stable_final_verifier_plan_ref(task_id: str) -> dict:
    return {
        "schema_version": "repo_harness_v5_evidence_ref_v0",
        "path": f"stable/{task_id}_final_verifier_plan.json",
        "sha256": "e" * 64,
        "size_bytes": 1,
        "kind": "final_verifier_plan",
        "purpose": f"stable final verifier plan for {task_id}",
        "visibility": "evaluator_only",
        "share_safe": False,
        "producer_command": "test",
        "producer_stage": "test",
        "inspect_command": "inspect-v5-run-matrix",
    }


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, payloads: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n" for payload in payloads),
        encoding="utf-8",
    )
