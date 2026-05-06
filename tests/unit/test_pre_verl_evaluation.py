import json
from pathlib import Path

import pytest

from repo_harness.errors import RepoHarnessError
from repo_harness.pre_verl_evaluation import (
    _inspect_transcript,
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

    assert payload["current_v5_real_provider_terminal_outcome_count"] == 1
    assert payload["evaluation_scope"] == "current_v5_baseline_provider_outcomes"
    assert payload["expanded_pilot_status"] == "blocked"
    assert payload["actual_agent_run_tasks"] == 1
    assert payload["accepted_count"] == 1
    assert payload["blocked_count"] == 23
    assert payload["status"] == "passed"


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


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


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
