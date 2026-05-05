import json
from pathlib import Path

from repo_harness.v5_evidence import _evidence_ref, inspect_v5_export_pack
from repo_harness.v5_export_pack import build_export_result_pack


def test_v5_export_pack_builder_partitions_records_and_blocks_preference_claim(tmp_path: Path) -> None:
    executed_manifest = _write_executed_manifest(tmp_path)
    claim_gate = _write_stage3_claim_gate(tmp_path)

    manifest_path = build_export_result_pack(
        executed_run_matrix_manifest=executed_manifest,
        stage3_claim_gate_report=claim_gate,
        output_dir=tmp_path / "export_pack",
    )

    assert "Inspect V5 export pack: complete" in inspect_v5_export_pack(
        manifest_path,
        assert_clean=True,
    )
    manifest = _read_json(manifest_path)
    assert manifest["partition_counts"]["real_provider_trainable_records"] == 2
    assert manifest["partition_counts"]["diagnostic_records"] == 1
    assert manifest["partition_counts"]["blocked_records"] == 1
    preference_blocked = _read_json(tmp_path / "export_pack" / "v5_preference_pair_blocked_report.json")
    assert preference_blocked["claim_gate_effect"] == "disable_preference_export_completed_claim"
    stage4_claim_gate = _read_json(tmp_path / "export_pack" / "v5_resume_claim_gate_report.json")
    assert stage4_claim_gate["stage"] == "stage4_partial"
    assert stage4_claim_gate["preference_pair_claim_status"] == "blocked_no_real_comparable_pair"
    assert "preference export completed" in stage4_claim_gate["blocked_claims"]


def _write_executed_manifest(tmp_path: Path) -> Path:
    results_path = tmp_path / "matrix" / "v5_matrix_cell_results.jsonl"
    results = []
    for index in range(3):
        task_id = f"v5_task_{index + 1:03d}"
        run_id = f"v5_stage3b_deepseek_{task_id}"
        run_dir = tmp_path / "runs" / run_id
        run_dir.mkdir(parents=True)
        _write_jsonl(
            run_dir / "transcript.jsonl",
            [
                {"message_id": "initial_0", "role": "system", "content_preview": "system"},
                {"message_id": "initial_1", "role": "user", "content_preview": "sanitized task"},
                {"message_id": "assistant_1", "role": "assistant", "content_preview": "final answer"},
            ],
        )
        events_path = run_dir / "events.jsonl"
        boundary_path = run_dir / "final_verifier_boundary.json"
        _write_jsonl(events_path, [{"event_type": "model_call_completed", "data": {"provider": "deepseek"}}])
        _write_json(boundary_path, {"accepted": False})
        results.append(
            {
                "schema_version": "repo_harness_v5_matrix_cell_result_v0",
                "cell_id": f"cell_{index}",
                "task_id": task_id,
                "provider_id": "deepseek",
                "run_id": run_id,
                "run_dir": run_dir.as_posix(),
                "actual_provider_call_count": 1,
                "final_verifier_status": "not_executed_stage3b_minimal_provider_loop",
                "trajectory_ref": _ref(events_path, "trajectory_events"),
                "final_verifier_boundary_ref": _ref(boundary_path, "final_verifier_boundary"),
            }
        )
    _write_jsonl(results_path, results)
    manifest_path = tmp_path / "matrix" / "v5_run_matrix_manifest_executed.json"
    _write_json(
        manifest_path,
        {
            "schema_version": "repo_harness_v5_run_matrix_manifest_v0",
            "agent_run_started": True,
            "provider_api_called": True,
            "matrix_cell_results_ref": _ref(results_path, "v5_matrix_cell_results"),
        },
    )
    return manifest_path


def _write_stage3_claim_gate(tmp_path: Path) -> Path:
    path = tmp_path / "stage3" / "v5_resume_claim_gate_report.json"
    _write_json(
        path,
        {
            "schema_version": "repo_harness_v5_resume_claim_gate_report_v0",
            "stage": "stage3_partial",
            "allowed_claims": ["core real provider floor satisfied"],
            "blocked_claims": ["multi-provider agent runs", "preference export completed"],
            "blocking_reasons": {"provider": "single provider"},
            "provider_claim_status": "blocked_single_provider_family_deepseek_only",
            "preference_pair_claim_status": "pending_stage4",
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
        inspect_command="inspect-v5-export-pack",
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
