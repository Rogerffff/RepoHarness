import json
from pathlib import Path

from repo_harness.v5_demo_artifacts import build_demo_artifacts, build_interview_result_pack
from repo_harness.v5_evidence import _evidence_ref, inspect_v5_demo_artifacts


def test_v5_demo_artifacts_and_interview_pack_are_share_safe(tmp_path: Path) -> None:
    task_set = _write_task_set(tmp_path)
    executed_manifest = _write_executed_manifest(tmp_path)
    export_pack = _write_export_pack_manifest(tmp_path)
    claim_gate = _write_stage4_claim_gate(tmp_path)

    resume_index = build_demo_artifacts(
        task_set_manifest=task_set,
        executed_run_matrix_manifest=executed_manifest,
        export_pack_manifest=export_pack,
        stage4_claim_gate_report=claim_gate,
        output_dir=tmp_path / "stage5",
    )

    assert "Inspect V5 demo artifacts: complete" in inspect_v5_demo_artifacts(resume_index, assert_share_safe=True)
    stage5_claim_gate = _read_json(tmp_path / "stage5" / "v5_resume_claim_gate_report.json")
    assert stage5_claim_gate["stage"] == "stage5_final"
    assert stage5_claim_gate["demo_share_safe_status"] == "passed"
    assert "preference export completed" in stage5_claim_gate["blocked_claims"]
    result_summary = _read_json(tmp_path / "stage5" / "v5_result_summary_table.json")
    assert result_summary["real_provider_runs"]["denominator"] == 3
    assert result_summary["real_provider_runs"]["accepted_count"] == 0
    assert result_summary["accepted_rate_by_provider_family"]["deepseek"]["accepted"] == 0
    assert result_summary["accepted_rate_by_task_family"]["cli_error_formatting"]["accepted"] == 0
    assert result_summary["accepted_rate_by_task_family"]["cli_error_formatting"]["denominator"] == 3
    assert "mock_or_replay_records" in result_summary["real_provider_runs"]["denominator_excludes"]
    assert result_summary["task_inventory"]["accepted_auditable_task_count"] == 15
    assert result_summary["task_inventory"]["pr_issue_task_count"] == 9
    assert result_summary["task_inventory"]["swebench_like_anchor_task_count"] == 6
    assert result_summary["task_inventory"]["threshold_source"] == task_set.as_posix()
    walkthrough = (tmp_path / "stage5" / "v5_canonical_demo_walkthrough.md").read_text(encoding="utf-8")
    assert "生成导出分区结构和审计证据" in walkthrough
    assert "生成 sanitized SFT / rollout 格式样本" not in walkthrough
    repro = _read_json(tmp_path / "stage5" / "v5_repro_command_index.json")
    assert export_pack.as_posix() in repro["commands"][1]["command"]

    docs12 = tmp_path / "docs" / "12-resume-narrative-and-demo-artifacts.md"
    docs12.parent.mkdir(parents=True)
    docs12.write_text("# Resume Artifacts\n", encoding="utf-8")
    interview_manifest = build_interview_result_pack(
        resume_artifact_index=resume_index,
        stage5_claim_gate_report=tmp_path / "stage5" / "v5_resume_claim_gate_report.json",
        docs12_path=docs12,
        output_dir=tmp_path / "stage5",
    )

    assert "Inspect V5 demo artifacts: complete" in inspect_v5_demo_artifacts(
        interview_manifest,
        assert_share_safe=True,
    )
    pack = _read_json(interview_manifest)
    assert pack["blocked_claims_enforced"] is True
    assert pack["copy_safe_blocked_claims_count"] == 0
    resume_bullets = (tmp_path / "stage5" / "v5_resume_bullets.md").read_text(encoding="utf-8")
    assert "分区导出审计" in resume_bullets
    assert "分区训练导出" not in resume_bullets


def _write_task_set(tmp_path: Path) -> Path:
    adapter_input = tmp_path / "task" / "adapter_visible.json"
    _write_json(
        adapter_input,
        {
            "schema_version": "repo_harness_v5_adapter_visible_task_draft_v0",
            "task_id": "v5_task_003",
            "repository": "pallets/click",
            "task_statement": "Command error output should show a helpful hint only when the relevant help option exists.",
            "share_safe": True,
        },
    )
    task_definition = tmp_path / "task" / "v5_task_003.json"
    _write_json(
        task_definition,
        {
            "schema_version": "repo_harness_v5_task_definition_v0",
            "task_id": "v5_task_003",
            "candidate_id": "pallets/click#3208",
            "repository": "pallets/click",
            "source_kind": "pr_issue_flow",
            "task_family": "cli_error_formatting",
            "adapter_visible_input_ref": _ref(adapter_input, "adapter_visible_task_input"),
        },
    )
    task_set = tmp_path / "task" / "v5_task_set_manifest.json"
    _write_json(
        task_set,
        {
            "schema_version": "repo_harness_v5_task_set_manifest_v0",
            "accepted_auditable_task_count": 15,
            "pr_issue_task_count": 9,
            "swebench_like_anchor_count": 6,
            "initial_task_refs": [_ref(task_definition, "v5_task_definition")],
            "supplemental_task_refs": [],
            "status": "passed",
        },
    )
    return task_set


def _write_executed_manifest(tmp_path: Path) -> Path:
    results_path = tmp_path / "matrix" / "v5_matrix_cell_results.jsonl"
    results = []
    for index in range(3):
        run_id = f"v5_stage3b_deepseek_v5_task_003_{index}"
        run_dir = tmp_path / "runs" / run_id
        run_dir.mkdir(parents=True)
        transcript_path = run_dir / "transcript.jsonl"
        _write_jsonl(
            transcript_path,
            [
                {"message_id": "initial_0", "role": "system", "run_id": run_id, "task_id": "v5_task_003", "turn": 0, "content_preview": "system"},
                {"message_id": "initial_1", "role": "user", "run_id": run_id, "task_id": "v5_task_003", "turn": 0, "content_preview": "sanitized task"},
                {"message_id": "assistant_1", "role": "assistant", "run_id": run_id, "task_id": "v5_task_003", "turn": 1, "content_preview": "plan"},
            ],
        )
        results.append(
            {
                "schema_version": "repo_harness_v5_matrix_cell_result_v0",
                "task_id": "v5_task_003",
                "run_id": run_id,
                "run_dir": run_dir.as_posix(),
                "provider_id": "deepseek",
                "scaffold_id": "simple_react",
                "budget_policy_id": "stage3b_constrained_one_turn_no_tool_calls",
                "actual_provider_call_count": 1,
                "accepted": False,
                "final_verifier_status": "accepted" if index == 0 else "not_executed_stage3b_minimal_provider_loop",
                "source_tree_hash": "a" * 64,
                "started_at": "2026-05-05T16:00:00Z",
                "finished_at": "2026-05-05T16:00:02Z",
                "token_usage": {"input_tokens": 10, "output_tokens": 2, "cached_tokens": 0},
                "transcript_ref": _ref(transcript_path, "trajectory_transcript"),
            }
        )
    _write_jsonl(results_path, results)
    manifest = tmp_path / "matrix" / "v5_run_matrix_manifest_executed.json"
    _write_json(
        manifest,
        {
            "schema_version": "repo_harness_v5_run_matrix_manifest_v0",
            "actual_provider_calls": 3,
            "agent_run_started": True,
            "provider_api_called": True,
            "matrix_cell_results_ref": _ref(results_path, "v5_matrix_cell_results"),
        },
    )
    return manifest


def _write_export_pack_manifest(tmp_path: Path) -> Path:
    path = tmp_path / "export" / "v5_export_result_pack_manifest.json"
    _write_json(
        path,
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
    return path


def _write_stage4_claim_gate(tmp_path: Path) -> Path:
    path = tmp_path / "claim" / "v5_resume_claim_gate_report.json"
    _write_json(
        path,
        {
            "schema_version": "repo_harness_v5_resume_claim_gate_report_v0",
            "stage": "stage4_partial",
            "allowed_claims": ["partitioned export pack generated"],
            "blocked_claims": ["multi-provider agent runs", "preference export completed"],
            "blocking_reasons": {"provider": "single provider", "preference_pair": "blocked"},
            "provider_claim_status": "blocked_single_provider_family_deepseek_only",
            "preference_pair_claim_status": "blocked_no_real_comparable_pair",
            "demo_share_safe_status": "pending_stage5",
            "stress_test_claim_status": "not_claimed",
            "source_reports": [],
        },
    )
    return path


def _ref(path: Path, kind: str) -> dict:
    return _evidence_ref(
        path,
        kind=kind,
        purpose=kind,
        visibility="audit_only",
        producer_command="test",
        producer_stage="test",
        inspect_command="inspect-v5-demo-artifacts",
    )


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
