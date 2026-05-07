import hashlib
import json
from pathlib import Path

import pytest

import repo_harness.pre_verl_evaluation as pre_verl_evaluation
from repo_harness.errors import RepoHarnessError
from repo_harness.pre_verl_evaluation import (
    _inspect_transcript,
    _source_context_for_prompt,
    build_pre_verl_final,
    build_pre_verl_agent_evaluation,
    build_pre_verl_task_set,
    inspect_pre_verl_agent_evaluation,
    inspect_pre_verl_phase_coverage,
    inspect_pre_verl_task_set,
    inspect_pre_verl_task_visibility,
    inspect_pre_verl_verifier_correctness,
)


def test_runtime_transcript_pairing_uses_tool_call_id_from_events(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    transcript = run_dir / "transcript.jsonl"
    _write_jsonl(
        transcript,
        [
            {"role": "assistant", "tool_call_id": None, "tool_result_id": None},
            {
                "role": "tool",
                "tool_call_id": "call_list",
                "tool_result_id": "call_list_result",
            },
        ],
    )
    _write_jsonl(
        run_dir / "events.jsonl",
        [
            {
                "event_type": "tool_requested",
                "data": {"tool_call_id": "call_list"},
            },
            {
                "event_type": "tool_interrupted",
                "data": {"tool_call_id": "call_list", "tool_result_id": "call_list_result"},
            },
        ],
    )

    finding = _inspect_transcript(
        {
            "run_id": "run_1",
            "task_id": "task_1",
            "transcript_ref": {"path": str(transcript)},
            "final_verifier_status": "not_executed",
        }
    )

    assert finding["tool_use_count"] == 1
    assert finding["tool_result_count"] == 1
    assert finding["unpaired_tool_use_count"] == 0
    assert finding["unpaired_tool_result_count"] == 0


def test_legacy_pre_verl_deepseek_response_artifact_redacts_reasoning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "content": "done",
                    "reasoning_content": "private reasoning from legacy path",
                },
            }
        ],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1},
    }

    class _Response:
        def __enter__(self):  # noqa: ANN001
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
            return False

        def read(self) -> bytes:
            return json.dumps(payload).encode("utf-8")

    monkeypatch.setattr(pre_verl_evaluation, "urlopen", lambda request, timeout: _Response())

    result = pre_verl_evaluation._call_deepseek_for_patch(
        messages=[{"role": "user", "content": "fix"}],
        model_id="deepseek-v4-pro",
        credential_value="sk-test-secret-value-1234567890",
        credential_source="environment",
        run_dir=tmp_path,
        max_output_tokens=32,
        request_timeout_seconds=5,
        temperature=0.0,
    )

    assert result["status"] == "passed"
    response_text = (tmp_path / "raw_deepseek_provider_response_redacted.json").read_text(
        encoding="utf-8"
    )
    assert "private reasoning from legacy path" not in response_text
    assert "<REDACTED_REASONING>" in response_text


def test_runtime_transcript_pairing_reports_missing_terminal_event(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    transcript = run_dir / "transcript.jsonl"
    _write_jsonl(transcript, [{"role": "assistant"}])
    _write_jsonl(run_dir / "events.jsonl", [{"event_type": "tool_requested", "data": {"tool_call_id": "call_read"}}])

    finding = _inspect_transcript(
        {
            "run_id": "run_1",
            "task_id": "task_1",
            "transcript_ref": {"path": str(transcript)},
            "final_verifier_status": "not_executed",
        }
    )

    assert finding["tool_use_count"] == 1
    assert finding["tool_result_count"] == 0
    assert finding["unpaired_tool_use_count"] == 1
    assert finding["unpaired_tool_result_count"] == 0


def test_final_report_separates_readiness_from_blocked_claims(tmp_path: Path) -> None:
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    baseline = _write_json(inputs / "baseline.json", {"status": "passed"})
    task_set = _write_json(
        inputs / "task_set.json",
        {
            "status": "passed",
            "planned_denominator": 83,
            "bound_task_denominator": 83,
            "runnable_denominator": 83,
            "real_provider_terminal_outcome_denominator": 23,
        },
    )
    verifier = _write_json(inputs / "verifier.json", {"status": "passed"})
    agent_eval = _write_json(
        inputs / "agent_eval.json",
        {
            "status": "passed",
            "expanded_pilot_status": "passed",
            "accepted_count": 1,
            "accepted_rate_denominator_value": 7,
            "accepted_rate_point_estimate": 0.142857,
            "accepted_rate_wilson_interval_95": {"low": 0.02568, "high": 0.513128},
        },
    )
    runtime = _write_json(inputs / "pre_verl_agent_runtime_trace_report.json", {"status": "passed"})
    _write_json(
        inputs / "pre_verl_context_compaction_stress_report.json",
        {
            "status": "passed",
            "stress_run_count": 7,
            "long_context_stress_status": "deferred_until_verl_adapter_or_partial_rollout_work",
        },
    )
    export = _write_json(inputs / "export.json", {"status": "passed", "partition_counts": {}})

    report = build_pre_verl_final(
        output_dir=tmp_path / "final",
        baseline_binding=baseline,
        task_set_manifest=task_set,
        verifier_correctness_report=verifier,
        agent_evaluation_report=agent_eval,
        runtime_trace_report=runtime,
        export_pack_manifest=export,
    )
    payload = json.loads(report.read_text(encoding="utf-8"))

    assert "context_compaction_stress_report_ref" in payload
    assert payload["status"] == "passed"
    assert payload["verl_readiness"]["status"] == "passed"
    assert "long-context context compaction stress run completed" in payload["blocked_claims"]
    assert "model training completed" in payload["blocked_claims"]
    summary = json.loads((tmp_path / "final" / "pre_verl_result_summary_table.json").read_text(encoding="utf-8"))
    assert summary["runtime_audit"]["context_compaction_stress_status"] == "passed"
    assert summary["pre_verl_readiness_status"] == "passed"


def test_task_set_expansion_binds_counts_and_blocks_non_runnable_swebench_tasks(tmp_path: Path) -> None:
    v5_task_set, inventory, visibility, supplemental = _write_v5_task_sources(tmp_path)
    dev_rows = tmp_path / "dev_rows.jsonl"
    test_rows = tmp_path / "test_rows.jsonl"
    _write_jsonl(dev_rows, [_swebench_row(f"dev_repo__issue-{index}", repo=f"dev/repo{index % 3}") for index in range(1, 4)])
    _write_jsonl(test_rows, [_swebench_row(f"test_repo__issue-{index}", repo=f"test/repo{index % 4}") for index in range(1, 6)])

    manifest = build_pre_verl_task_set(
        output_dir=tmp_path / "pre_verl",
        v5_task_set_manifest=v5_task_set,
        v5_task_inventory_report=inventory,
        v5_task_visibility_scan_report=visibility,
        swebench_lite_dev_rows=dev_rows,
        swebench_lite_test_rows=test_rows,
        supplemental_pr_issue_candidate_report=supplemental,
        planned_dev_instances=3,
        planned_curated_lite=5,
        planned_github_issue=2,
    )
    payload = json.loads(manifest.read_text(encoding="utf-8"))

    assert payload["status"] == "passed"
    assert payload["planned_denominator"] == 10
    assert payload["bound_task_denominator"] == 10
    assert payload["swebench_lite_development_task_count"] == 3
    assert payload["swebench_lite_curated_task_count"] == 5
    assert payload["pr_issue_task_count"] == 2
    assert payload["blocked_task_count"] == 8
    blocked = json.loads((tmp_path / "pre_verl" / "pre_verl_task_blocked_report.json").read_text(encoding="utf-8"))
    assert blocked["blocked_task_count"] == 8
    assert blocked["missing_blocked_reason_count"] == 0
    assert "Inspect pre-verl task set: passed" in inspect_pre_verl_task_set(manifest, assert_task_freeze_complete=True)
    assert "Inspect pre-verl task visibility: passed" in inspect_pre_verl_task_visibility(
        tmp_path / "pre_verl" / "pre_verl_task_visibility_scan_report.json",
        assert_clean=True,
    )


def test_agent_evaluation_counts_only_expanded_development_instance_runs(tmp_path: Path) -> None:
    task_def = _write_json(
        tmp_path / "pre_verl_dev_task.json",
        {
            "task_id": "pre_verl_dev_001",
            "tier": "swebench_lite_development",
            "source_instance_id": "dev_repo__issue-1",
        },
    )
    task_set = _write_json(
        tmp_path / "task_set.json",
        {
            "planned_denominator": 83,
            "agent_evaluation_planned_denominator": 23,
            "task_definition_refs": [{"path": task_def.as_posix()}],
        },
    )
    matrix_results = tmp_path / "matrix_results.jsonl"
    _write_jsonl(
        matrix_results,
        [
            {
                "run_id": "v5_run",
                "task_id": "v5_task_008",
                "actual_provider_call_count": 1,
                "accepted": True,
                "final_verifier_status": "accepted",
                "final_verifier_boundary_ref": {"path": "boundary.json"},
            }
        ],
    )
    matrix = _write_json(tmp_path / "matrix.json", {"matrix_cell_results_ref": {"path": matrix_results.as_posix()}})
    summary = _write_json(tmp_path / "summary.json", {})

    report = build_pre_verl_agent_evaluation(
        output_dir=tmp_path / "agent_eval",
        pre_verl_task_set_manifest=task_set,
        executed_run_matrix_manifest=matrix,
        v5_result_summary_table=summary,
    )
    payload = json.loads(report.read_text(encoding="utf-8"))

    assert payload["raw_terminal_outcome_count"] == 1
    assert payload["rejected_non_agentloop_result_count"] == 1
    assert payload["current_v5_real_provider_terminal_outcome_count"] == 0
    assert payload["evaluation_scope"] == "current_v5_baseline_provider_outcomes"
    assert payload["expanded_pilot_status"] == "blocked"
    assert payload["actual_agent_run_tasks"] == 0
    assert payload["accepted_count"] == 0
    assert payload["blocked_count"] == 23
    assert payload["status"] == "blocked"


def test_agent_evaluation_failure_counts_separate_patch_and_verifier_failures(tmp_path: Path) -> None:
    refs = []
    for index in range(1, 5):
        refs.append(
            {
                "path": _write_json(
                    tmp_path / f"pre_verl_dev_{index:03d}.json",
                    {
                        "task_id": f"pre_verl_dev_{index:03d}",
                        "tier": "swebench_lite_development",
                        "source_instance_id": f"dev_repo__issue-{index}",
                    },
                ).as_posix()
            }
        )
    task_set = _write_json(
        tmp_path / "task_set.json",
        {
            "planned_denominator": 4,
            "agent_evaluation_planned_denominator": 4,
            "task_definition_refs": refs,
        },
    )
    matrix_results = tmp_path / "matrix_results.jsonl"
    _write_jsonl(
        matrix_results,
        [
            {
                **_formal_agentloop_lineage(
                    tmp_path,
                    "pre_verl_dev_001",
                    accepted=True,
                    final_verifier_status="accepted",
                    failure_category=None,
                ),
                "task_id": "pre_verl_dev_001",
                "actual_provider_call_count": 1,
                "accepted": True,
                "final_patch_ref": {"path": "accepted.diff"},
                "final_verifier_status": "accepted",
                "failure_category": None,
            },
            {
                **_formal_agentloop_lineage(
                    tmp_path,
                    "pre_verl_dev_002",
                    accepted=False,
                    final_verifier_status="not_executed",
                    failure_category="patch_apply_failed",
                ),
                "task_id": "pre_verl_dev_002",
                "actual_provider_call_count": 1,
                "accepted": False,
                "final_patch_ref": {"path": "bad_path.diff"},
                "final_verifier_status": "not_executed",
                "failure_category": "patch_apply_failed",
            },
            {
                **_formal_agentloop_lineage(
                    tmp_path,
                    "pre_verl_dev_003",
                    accepted=False,
                    final_verifier_status="not_executed",
                    failure_category="empty_patch",
                ),
                "task_id": "pre_verl_dev_003",
                "actual_provider_call_count": 1,
                "accepted": False,
                "final_verifier_status": "not_executed",
                "failure_category": "empty_patch",
            },
            {
                **_formal_agentloop_lineage(
                    tmp_path,
                    "pre_verl_dev_004",
                    accepted=False,
                    final_verifier_status="rejected",
                    failure_category="model_patch_rejected_by_final_verifier",
                ),
                "task_id": "pre_verl_dev_004",
                "actual_provider_call_count": 1,
                "accepted": False,
                "final_patch_ref": {"path": "wrong_fix.diff"},
                "final_verifier_status": "rejected",
                "failure_category": "model_patch_rejected_by_final_verifier",
            },
        ],
    )
    matrix = _write_json(tmp_path / "matrix.json", {"matrix_cell_results_ref": {"path": matrix_results.as_posix()}})
    summary = _write_json(tmp_path / "summary.json", {})

    report = build_pre_verl_agent_evaluation(
        output_dir=tmp_path / "agent_eval",
        pre_verl_task_set_manifest=task_set,
        executed_run_matrix_manifest=matrix,
        v5_result_summary_table=summary,
    )
    payload = json.loads(report.read_text(encoding="utf-8"))

    assert payload["actual_agent_run_tasks"] == 4
    assert payload["accepted_count"] == 1
    assert payload["patch_apply_failed_count"] == 1
    assert payload["empty_patch_count"] == 1
    assert payload["model_patch_rejected_by_final_verifier_count"] == 1
    assert payload["final_verifier_reached_count"] == 4
    assert payload["final_verifier_not_executed_count"] == 2
    assert payload["verifier_failed_count"] == 1
    assert payload["verifier_failure_rate_point_estimate"] == 0.25
    assert payload["failure_category_distribution"] == {
        "accepted": 1,
        "empty_patch": 1,
        "model_patch_rejected_by_final_verifier": 1,
        "patch_apply_failed": 1,
    }


def test_agent_evaluation_rejects_forged_agentloop_lineage_refs(tmp_path: Path) -> None:
    task_def = _write_json(
        tmp_path / "pre_verl_dev_001.json",
        {
            "task_id": "pre_verl_dev_001",
            "tier": "swebench_lite_development",
            "source_instance_id": "dev_repo__issue-1",
        },
    )
    task_set = _write_json(
        tmp_path / "task_set.json",
        {
            "planned_denominator": 1,
            "agent_evaluation_planned_denominator": 1,
            "task_definition_refs": [{"path": task_def.as_posix()}],
        },
    )
    run_dir = tmp_path / "forged_run"
    run_dir.mkdir()
    forged_result = {
        "task_id": "pre_verl_dev_001",
        "run_id": "forged-run",
        "actual_provider_call_count": 1,
        "accepted": True,
        "final_verifier_status": "accepted",
        "baseline_source": "repo_harness_agentloop_run_task",
        "run_task_run_dir": run_dir.as_posix(),
        "run_task_entrypoint": "repo-harness run-task",
        "scaffold_id": "patch_focused_react",
        "run_task_command_log_entry_ref": {"path": (run_dir / "missing_command.json").as_posix()},
        "tool_schema_snapshot_ref": {"path": (run_dir / "missing_tool_schema.json").as_posix()},
        "event_log_ref": {"path": (run_dir / "missing_events.jsonl").as_posix()},
        "transcript_ref": {"path": (run_dir / "missing_transcript.jsonl").as_posix()},
        "final_verifier_boundary_ref": {"path": (run_dir / "missing_boundary.json").as_posix()},
        "raw_provider_request_refs": [{"path": (run_dir / "missing_request.json").as_posix()}],
        "raw_provider_response_refs": [{"path": (run_dir / "missing_response.json").as_posix()}],
    }
    matrix_results = tmp_path / "matrix_results.jsonl"
    _write_jsonl(matrix_results, [forged_result])
    matrix = _write_json(tmp_path / "matrix.json", {"matrix_cell_results_ref": {"path": matrix_results.as_posix()}})
    summary = _write_json(tmp_path / "summary.json", {})

    report = build_pre_verl_agent_evaluation(
        output_dir=tmp_path / "agent_eval",
        pre_verl_task_set_manifest=task_set,
        executed_run_matrix_manifest=matrix,
        v5_result_summary_table=summary,
    )
    payload = json.loads(report.read_text(encoding="utf-8"))

    assert payload["actual_agent_run_tasks"] == 0
    assert payload["accepted_count"] == 0
    assert payload["rejected_non_agentloop_result_count"] == 1
    assert payload["status"] == "blocked"
    reasons = payload["rejected_non_agentloop_result_reasons"][0]["reasons"]
    assert "run_task_command_log_entry_ref_path_missing" in reasons
    assert "events_jsonl_empty_or_unreadable" in reasons


def test_agent_evaluation_rejects_boundary_payload_mismatch(tmp_path: Path) -> None:
    task_def = _write_json(
        tmp_path / "pre_verl_dev_001.json",
        {
            "task_id": "pre_verl_dev_001",
            "tier": "swebench_lite_development",
            "source_instance_id": "dev_repo__issue-1",
        },
    )
    task_set = _write_json(
        tmp_path / "task_set.json",
        {
            "planned_denominator": 1,
            "agent_evaluation_planned_denominator": 1,
            "task_definition_refs": [{"path": task_def.as_posix()}],
        },
    )
    forged_result = {
        **_formal_agentloop_lineage(
            tmp_path,
            "pre_verl_dev_001",
            accepted=False,
            final_verifier_status="rejected",
            failure_category="model_patch_rejected_by_final_verifier",
        ),
        "task_id": "pre_verl_dev_001",
        "actual_provider_call_count": 1,
        "accepted": True,
        "final_verifier_status": "accepted",
        "failure_category": None,
    }
    matrix_results = tmp_path / "matrix_results.jsonl"
    _write_jsonl(matrix_results, [forged_result])
    matrix = _write_json(tmp_path / "matrix.json", {"matrix_cell_results_ref": {"path": matrix_results.as_posix()}})
    summary = _write_json(tmp_path / "summary.json", {})

    report = build_pre_verl_agent_evaluation(
        output_dir=tmp_path / "agent_eval",
        pre_verl_task_set_manifest=task_set,
        executed_run_matrix_manifest=matrix,
        v5_result_summary_table=summary,
    )
    payload = json.loads(report.read_text(encoding="utf-8"))

    assert payload["actual_agent_run_tasks"] == 0
    reasons = payload["rejected_non_agentloop_result_reasons"][0]["reasons"]
    assert "final_verifier_boundary_accepted_mismatch" in reasons
    assert "final_verifier_boundary_status_mismatch" in reasons


def test_agent_evaluation_rejects_unfingerprinted_legacy_refs(tmp_path: Path) -> None:
    task_def = _write_json(
        tmp_path / "pre_verl_dev_001.json",
        {
            "task_id": "pre_verl_dev_001",
            "tier": "swebench_lite_development",
            "source_instance_id": "dev_repo__issue-1",
        },
    )
    task_set = _write_json(
        tmp_path / "task_set.json",
        {
            "planned_denominator": 1,
            "agent_evaluation_planned_denominator": 1,
            "task_definition_refs": [{"path": task_def.as_posix()}],
        },
    )
    result = {
        **_formal_agentloop_lineage(
            tmp_path,
            "pre_verl_dev_001",
            accepted=True,
            final_verifier_status="accepted",
            failure_category=None,
        ),
        "task_id": "pre_verl_dev_001",
        "actual_provider_call_count": 1,
        "accepted": True,
        "final_verifier_status": "accepted",
    }
    result["final_verifier_boundary_ref"] = {
        "relative_path": str(result["final_verifier_boundary_ref"]["relative_path"])
    }
    matrix_results = tmp_path / "matrix_results.jsonl"
    _write_jsonl(matrix_results, [result])
    matrix = _write_json(tmp_path / "matrix.json", {"matrix_cell_results_ref": {"path": matrix_results.as_posix()}})
    summary = _write_json(tmp_path / "summary.json", {})

    report = build_pre_verl_agent_evaluation(
        output_dir=tmp_path / "agent_eval",
        pre_verl_task_set_manifest=task_set,
        executed_run_matrix_manifest=matrix,
        v5_result_summary_table=summary,
    )
    payload = json.loads(report.read_text(encoding="utf-8"))

    assert payload["actual_agent_run_tasks"] == 0
    reasons = payload["rejected_non_agentloop_result_reasons"][0]["reasons"]
    assert "final_verifier_boundary_ref_missing_sha256" in reasons
    assert "final_verifier_boundary_ref_missing_size_bytes" in reasons


def test_agent_evaluation_rejects_missing_legacy_semantic_fields(tmp_path: Path) -> None:
    task_def = _write_json(
        tmp_path / "pre_verl_dev_001.json",
        {
            "task_id": "pre_verl_dev_001",
            "tier": "swebench_lite_development",
            "source_instance_id": "dev_repo__issue-1",
        },
    )
    task_set = _write_json(
        tmp_path / "task_set.json",
        {
            "planned_denominator": 1,
            "agent_evaluation_planned_denominator": 1,
            "task_definition_refs": [{"path": task_def.as_posix()}],
        },
    )
    result = {
        **_formal_agentloop_lineage(
            tmp_path,
            "pre_verl_dev_001",
            accepted=True,
            final_verifier_status="accepted",
            failure_category=None,
        ),
        "task_id": "pre_verl_dev_001",
        "actual_provider_call_count": 1,
    }
    matrix_results = tmp_path / "matrix_results.jsonl"
    _write_jsonl(matrix_results, [result])
    matrix = _write_json(tmp_path / "matrix.json", {"matrix_cell_results_ref": {"path": matrix_results.as_posix()}})
    summary = _write_json(tmp_path / "summary.json", {})

    report = build_pre_verl_agent_evaluation(
        output_dir=tmp_path / "agent_eval",
        pre_verl_task_set_manifest=task_set,
        executed_run_matrix_manifest=matrix,
        v5_result_summary_table=summary,
    )
    payload = json.loads(report.read_text(encoding="utf-8"))

    assert payload["actual_agent_run_tasks"] == 0
    reasons = payload["rejected_non_agentloop_result_reasons"][0]["reasons"]
    assert "missing_accepted" in reasons
    assert "missing_final_verifier_status" in reasons
    assert "missing_failure_category" in reasons


def test_agent_evaluation_rejects_old_pilot_flag_mismatch(tmp_path: Path) -> None:
    task_def = _write_json(
        tmp_path / "pre_verl_dev_001.json",
        {
            "task_id": "pre_verl_dev_001",
            "tier": "swebench_lite_development",
            "source_instance_id": "dev_repo__issue-1",
        },
    )
    task_set = _write_json(
        tmp_path / "task_set.json",
        {
            "planned_denominator": 1,
            "agent_evaluation_planned_denominator": 1,
            "task_definition_refs": [{"path": task_def.as_posix()}],
        },
    )
    result = {
        **_formal_agentloop_lineage(
            tmp_path,
            "pre_verl_dev_001",
            accepted=True,
            final_verifier_status="accepted",
            failure_category=None,
        ),
        "task_id": "pre_verl_dev_001",
        "actual_provider_call_count": 1,
        "accepted": True,
        "final_verifier_status": "accepted",
        "failure_category": None,
        "old_pilot_used": True,
    }
    matrix_results = tmp_path / "matrix_results.jsonl"
    _write_jsonl(matrix_results, [result])
    matrix = _write_json(tmp_path / "matrix.json", {"matrix_cell_results_ref": {"path": matrix_results.as_posix()}})
    summary = _write_json(tmp_path / "summary.json", {})

    report = build_pre_verl_agent_evaluation(
        output_dir=tmp_path / "agent_eval",
        pre_verl_task_set_manifest=task_set,
        executed_run_matrix_manifest=matrix,
        v5_result_summary_table=summary,
    )
    payload = json.loads(report.read_text(encoding="utf-8"))

    assert payload["actual_agent_run_tasks"] == 0
    reasons = payload["rejected_non_agentloop_result_reasons"][0]["reasons"]
    assert "result_old_pilot_used" in reasons
    assert "final_verifier_boundary_old_pilot_used_mismatch" in reasons


def test_readiness_inspects_do_not_claim_full_expanded_completion(tmp_path: Path) -> None:
    verifier = _write_json(
        tmp_path / "verifier.json",
        {
            "status": "passed",
            "final_verifier_boundary_missing_count": 0,
            "expanded_sweep_status": "blocked",
        },
    )
    assert "passed" in inspect_pre_verl_verifier_correctness(verifier, assert_verifier_readiness_complete=True)
    with pytest.raises(RepoHarnessError):
        inspect_pre_verl_verifier_correctness(verifier, assert_verifier_correctness_complete=True)

    phase = _write_json(
        tmp_path / "phase.json",
        {
            "status": "passed",
            "full_expanded_phase_coverage_status": "partial",
        },
    )
    assert "passed" in inspect_pre_verl_phase_coverage(phase, assert_minimum_complete=True)
    with pytest.raises(RepoHarnessError):
        inspect_pre_verl_phase_coverage(phase, assert_complete=True)

    agent_eval = _write_json(
        tmp_path / "agent_eval.json",
        {
            "status": "passed",
            "expanded_pilot_status": "blocked",
        },
    )
    assert "passed" in inspect_pre_verl_agent_evaluation(agent_eval, assert_agent_evaluation_readiness_complete=True)
    with pytest.raises(RepoHarnessError):
        inspect_pre_verl_agent_evaluation(agent_eval, assert_agent_evaluation_pilot_complete=True)


def test_final_report_requires_expanded_pilot_for_verl_readiness(tmp_path: Path) -> None:
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    baseline = _write_json(inputs / "baseline.json", {"status": "passed"})
    task_set = _write_json(inputs / "task_set.json", {"status": "passed"})
    verifier = _write_json(inputs / "verifier.json", {"status": "passed"})
    agent_eval = _write_json(
        inputs / "agent_eval.json",
        {
            "status": "passed",
            "expanded_pilot_status": "blocked",
            "accepted_count": 0,
            "accepted_rate_denominator_value": 1,
            "accepted_rate_point_estimate": 0.0,
            "accepted_rate_wilson_interval_95": {"low": 0.0, "high": 0.0},
        },
    )
    runtime = _write_json(inputs / "pre_verl_agent_runtime_trace_report.json", {"status": "passed"})
    _write_json(inputs / "pre_verl_context_compaction_stress_report.json", {"status": "passed"})
    export = _write_json(inputs / "export.json", {"status": "passed", "partition_counts": {}})

    report = build_pre_verl_final(
        output_dir=tmp_path / "final",
        baseline_binding=baseline,
        task_set_manifest=task_set,
        verifier_correctness_report=verifier,
        agent_evaluation_report=agent_eval,
        runtime_trace_report=runtime,
        export_pack_manifest=export,
    )
    payload = json.loads(report.read_text(encoding="utf-8"))

    assert payload["status"] == "blocked"
    assert payload["verl_readiness"]["status"] == "blocked"
    assert "expanded development Pilot complete" in payload["verl_readiness"]["blocking_reasons"]
    assert "pre-verl readiness passed for safe verl adapter smoke and micro-RL integration" not in payload["allowed_claims"]
    assert "pre-verl readiness passed for safe verl adapter smoke and micro-RL integration" in payload["blocked_claims"]


def test_final_report_blocks_when_baseline_binding_failed(tmp_path: Path) -> None:
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    baseline = _write_json(inputs / "baseline.json", {"status": "blocked"})
    task_set = _write_json(inputs / "task_set.json", {"status": "passed"})
    verifier = _write_json(inputs / "verifier.json", {"status": "passed"})
    agent_eval = _write_json(
        inputs / "agent_eval.json",
        {
            "status": "passed",
            "expanded_pilot_status": "passed",
            "accepted_count": 1,
            "accepted_rate_denominator_value": 1,
            "accepted_rate_point_estimate": 1.0,
            "accepted_rate_wilson_interval_95": {"low": 0.206549, "high": 1.0},
        },
    )
    runtime = _write_json(inputs / "pre_verl_agent_runtime_trace_report.json", {"status": "passed"})
    _write_json(inputs / "pre_verl_context_compaction_stress_report.json", {"status": "passed"})
    export = _write_json(inputs / "export.json", {"status": "passed", "partition_counts": {}})

    report = build_pre_verl_final(
        output_dir=tmp_path / "final",
        baseline_binding=baseline,
        task_set_manifest=task_set,
        verifier_correctness_report=verifier,
        agent_evaluation_report=agent_eval,
        runtime_trace_report=runtime,
        export_pack_manifest=export,
    )
    payload = json.loads(report.read_text(encoding="utf-8"))

    assert payload["status"] == "blocked"
    assert payload["verl_readiness"]["status"] == "blocked"
    assert "V5 core acceptance baseline evidence present" in payload["verl_readiness"]["blocking_reasons"]
    assert "V5 core acceptance evidence reused as pre-verl baseline" not in payload["allowed_claims"]
    assert "V5 core acceptance evidence reused as pre-verl baseline" in payload["blocked_claims"]


def test_source_context_matches_traceback_paths_under_src_prefix(tmp_path: Path) -> None:
    source = tmp_path / "source"
    (source / "src" / "marshmallow").mkdir(parents=True)
    (source / "src" / "marshmallow" / "schema.py").write_text("class Placeholder:\n    pass\n", encoding="utf-8")
    (source / "src" / "marshmallow" / "fields.py").write_text("class Placeholder:\n    pass\n", encoding="utf-8")

    context = _source_context_for_prompt(
        source_dir=source,
        problem_statement='Traceback: File "/venv/lib/python3.11/site-packages/marshmallow/fields.py", line 1.',
        max_source_context_chars=2000,
    )

    assert "--- src/marshmallow/fields.py ---" in context
    assert context.index("--- src/marshmallow/fields.py ---") < context.index("--- src/marshmallow/schema.py ---")


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


def _formal_agentloop_lineage(
    tmp_path: Path,
    run_id: str,
    *,
    accepted: bool = True,
    final_verifier_status: str = "accepted",
    failure_category: str | None = None,
) -> dict[str, object]:
    run_dir = tmp_path / "run_task_runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    tool_schema_path = _write_json(run_dir / "tool_schema.json", {"kind": "tool_schema"})
    raw_request_path = _write_json(run_dir / "raw_request.json", {"kind": "raw_request"})
    raw_response_path = _write_json(run_dir / "raw_response.json", {"kind": "raw_response"})
    command_path = _write_json(
        run_dir / "run_task_command.json",
        {
            "command_name": "run-task",
            "argv": ["repo-harness", "run-task", "task.yaml", "--run-id", run_id],
            "exit_code": 0,
        },
    )
    _write_json(run_dir / "run_metadata.json", {"run_id": run_id, "scaffold_id": "patch_focused_react"})
    _write_json(
        run_dir / "run_config_facts.json",
        {
            "run_id": run_id,
            "final_verifier_mode": "strict_patch_replay",
            "test_feedback_policy": "disabled",
            "scaffold_id": "patch_focused_react",
            "tool_protocol": {"tool_schema_snapshot_ref": _file_ref(tool_schema_path, run_dir)},
        },
    )
    final_boundary_path = _write_json(
        run_dir / "final_verifier_boundary.json",
        {
            "baseline_source": "repo_harness_agentloop_run_task",
            "run_task_entrypoint": "repo-harness run-task",
            "accepted": accepted,
            "final_verifier_status": final_verifier_status,
            "failure_category": failure_category,
            "old_pilot_used": False,
            "legacy_v3_adapter_used": False,
        },
    )
    events = [
        {"event_type": "run_started", "data": {}},
        {"event_type": "baseline_completed", "data": {}},
        {"event_type": "context_prepared", "data": {}},
        {"event_type": "model_call_started", "data": {"model_call_id": "model-call-1"}},
        {
            "event_type": "model_call_completed",
            "data": {
                "model_call_id": "model-call-1",
                "provider": "deepseek",
                "raw_provider_request_ref": _file_ref(raw_request_path, run_dir),
                "raw_provider_response_ref": _file_ref(raw_response_path, run_dir),
            },
        },
        {"event_type": "run_finished", "data": {}},
    ]
    events_path = run_dir / "events.jsonl"
    events_path.write_text(
        "".join(json.dumps(event, sort_keys=True) + "\n" for event in events),
        encoding="utf-8",
    )
    transcript_path = run_dir / "transcript.jsonl"
    transcript_path.write_text("{}\n", encoding="utf-8")
    return {
        "baseline_source": "repo_harness_agentloop_run_task",
        "run_task_run_dir": run_dir.as_posix(),
        "run_task_command_log_entry_ref": _file_ref(command_path, run_dir),
        "run_task_entrypoint": "repo-harness run-task",
        "scaffold_id": "patch_focused_react",
        "tool_schema_snapshot_ref": _file_ref(tool_schema_path, run_dir),
        "event_log_ref": _file_ref(events_path, run_dir),
        "transcript_ref": _file_ref(transcript_path, run_dir),
        "final_verifier_boundary_ref": _file_ref(final_boundary_path, run_dir),
        "raw_provider_request_refs": [_file_ref(raw_request_path, run_dir)],
        "raw_provider_response_refs": [_file_ref(raw_response_path, run_dir)],
    }


def _file_ref(path: Path, run_dir: Path) -> dict[str, object]:
    return {
        "relative_path": path.relative_to(run_dir).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size_bytes": path.stat().st_size,
    }


def _swebench_row(instance_id: str, *, repo: str) -> dict[str, object]:
    return {
        "instance_id": instance_id,
        "repo": repo,
        "base_commit": "abc123",
        "version": "1.0",
        "problem_statement": f"Fix {instance_id}",
        "patch": "diff --git a/file.py b/file.py\n",
        "test_patch": "diff --git a/test_file.py b/test_file.py\n",
        "FAIL_TO_PASS": ["tests/test_file.py::test_fix"],
        "PASS_TO_PASS": ["tests/test_file.py::test_existing"],
        "environment_setup_commit": "def456",
        "hints_text": "",
    }


def _write_v5_task_sources(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    task_dir = tmp_path / "v5_tasks"
    task_dir.mkdir()
    refs = []
    for index in range(1, 3):
        task = _write_json(
            task_dir / f"task_{index}.json",
            {
                "task_id": f"v5_issue_{index}",
                "source_kind": "pr_issue_flow",
                "candidate_id": f"owner/repo#{index}",
                "repository": "owner/repo",
                "base_commit": "abc123",
                "task_family": "issue_flow",
                "accepted_auditable": True,
                "agent_run_ready": True,
                "verifier_ready": True,
                "adapter_visible_input_ref": None,
            },
        )
        refs.append({"path": task.as_posix()})
    v5_task_set = _write_json(
        tmp_path / "v5_task_set.json",
        {
            "accepted_auditable_task_count": 2,
            "pr_issue_task_count": 2,
            "swebench_like_anchor_count": 0,
            "agent_run_ready_count": 2,
            "task_refs": refs,
        },
    )
    inventory = _write_json(tmp_path / "inventory.json", {"status": "passed"})
    visibility = _write_json(tmp_path / "visibility.json", {"hidden_artifact_leakage_finding_count": 0, "status": "passed"})
    supplemental = _write_json(tmp_path / "supplemental.json", {"candidate_records": []})
    return v5_task_set, inventory, visibility, supplemental
