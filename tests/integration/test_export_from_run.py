import json
from pathlib import Path

from repo_harness.cli.main import main
from repo_harness.evaluation.runner import run_task
from repo_harness.export import ExportPolicy, export_preference_jsonl, export_rl_jsonl, export_sft_jsonl


ROOT = Path(__file__).resolve().parents[2]


def test_sft_export_from_success_run_filters_default_oracle_feedback(tmp_path: Path):
    run_dir = _success_run(tmp_path, "stage12-sft")

    output = export_sft_jsonl(run_dir)
    default_records = _read_jsonl(output)
    text = output.read_text(encoding="utf-8")
    default_export_dir = _latest_export_dir(run_dir / "exports")
    canonical_records = _read_jsonl(default_export_dir / "data.sft.jsonl")
    audit = _read_json(default_export_dir / "audit_report.json")

    assert default_records == []
    assert canonical_records == []
    assert audit["summary"]["diagnostic_only_count"] == len(audit["samples"])
    assert audit["status"] == "passed_with_warnings"
    assert all(
        sample["training_eligibility"] == "diagnostic_only"
        for sample in audit["samples"]
    )
    assert all(
        sample["invalid_reason"] == "oracle_hidden_feedback_diagnostic_only"
        for sample in audit["samples"]
    )
    assert "without_followup_context" not in text
    _assert_no_hidden_or_local_text(text)

    output = export_sft_jsonl(
        run_dir,
        policy=ExportPolicy(allow_oracle_feedback_training=True),
    )
    records = _read_jsonl(output)
    record = records[0]
    text = output.read_text(encoding="utf-8")
    explicit_export_dir = _latest_export_dir(run_dir / "exports")
    explicit_canonical_records = _read_jsonl(explicit_export_dir / "data.sft.jsonl")
    explicit_audit = _read_json(explicit_export_dir / "audit_report.json")

    assert records
    assert all(item["filter_status"] == "included" for item in records)
    assert all(item["invalid_for_training"] is False for item in records)
    assert all(item["quality"]["training_eligibility"] == "trainable" for item in records)
    assert any(
        message.get("role") == "assistant" and message.get("tool_calls")
        for item in records
        for message in item["payload"]["messages"]
    )
    tool_record = next(
        item
        for item in records
        if any(message.get("role") == "tool" for message in item["payload"]["messages"])
    )
    assert 1 in record["payload"]["loss_mask"]
    assert 1 in tool_record["payload"]["observation_mask"]
    assert (
        tool_record["payload"]["loss_mask"][
            tool_record["payload"]["observation_mask"].index(1)
        ]
        == 0
    )
    assert "reward_metadata_ref" not in record["payload"]
    assert "final_verifier_ref" not in record["payload"]
    assert record["payload"]["prepared_message_refs"]
    assert record["payload"]["content_replacement_state_refs"]
    tool_message_indexes = [
        index
        for index, message in enumerate(tool_record["payload"]["messages"])
        if message.get("role") == "tool"
    ]
    audit_bindings_by_index = {
        binding["message_index"]: binding
        for binding in tool_record["payload"].get("prompt_message_audit_bindings", [])
    }
    assert any(
        audit_bindings_by_index[index].get("observation_source") == "prepared_messages"
        for index in tool_message_indexes
    )
    assert all(
        audit_bindings_by_index[index].get("observation_source") == "prepared_messages"
        for index in tool_message_indexes
    )
    assert "without_followup_context" not in text
    _assert_refs_exist(run_dir, record)
    _assert_refs_exist(run_dir, tool_record)
    _assert_no_hidden_or_local_text(text)
    assert all(
        item["quality"]["training_eligibility"] == "trainable"
        for item in explicit_canonical_records
    )
    assert explicit_audit["status"] == "passed"


def test_rl_export_uses_final_reward_metadata(tmp_path: Path):
    run_dir = _success_run(tmp_path, "stage12-rl")

    output = export_rl_jsonl(
        run_dir,
        policy=ExportPolicy(allow_oracle_feedback_training=True),
    )
    record = _read_jsonl(output)[0]
    reward = _read_json(run_dir / "reward.json")

    assert record["payload"]["reward"] == reward["final_reward"]
    assert "reward_metadata" not in record["payload"]
    assert "final_verifier_ref" not in record["payload"]
    assert record["payload"]["prepared_message_refs"]
    assert record["payload"]["content_replacement_state_refs"]
    assert record["payload"]["trajectory"]
    assert record["payload"]["prompt"]["model_input_hash"]
    assert any(
        step["observation"].get("observation_source") == "prepared_messages"
        for step in record["payload"]["trajectory"]
    )
    for step in record["payload"]["trajectory"]:
        source = step["observation"].get("observation_source")
        assert source in {"prepared_messages", "not_observed_by_model"}
        if source == "not_observed_by_model":
            assert "preview" not in step["observation"]
            assert "artifact_refs" not in step["observation"]
    _assert_no_hidden_or_local_text(output.read_text(encoding="utf-8"))


def test_preference_export_pairs_two_runs_for_same_task(tmp_path: Path):
    success = _success_run(tmp_path, "stage12-pref-success")
    failure = run_task(
        ROOT / "tests/fixtures/tasks/task_001.yaml",
        config_path=ROOT / "tests/fixtures/run_configs/replay_failure_minimal.yaml",
        output_dir=tmp_path / "runs",
        run_id="stage12-pref-failure",
    )

    output = export_preference_jsonl(
        tmp_path / "runs",
        policy=ExportPolicy(allow_oracle_feedback_training=True),
    )
    record = _read_jsonl(output)[0]
    export_dir = _latest_export_dir(tmp_path / "runs" / "exports")
    canonical_records = _read_jsonl(export_dir / "data.preference.jsonl")
    audit = _read_json(export_dir / "audit_report.json")

    assert success.name in record["payload"]["chosen"]["source_run_id"]
    assert failure.name in record["payload"]["rejected"]["source_run_id"]
    assert "reward" not in record["payload"]["chosen"]
    assert "reward" not in record["payload"]["rejected"]
    assert "run_outcome" not in record["payload"]["chosen"]
    assert "run_outcome" not in record["payload"]["rejected"]
    assert canonical_records
    assert canonical_records[0]["quality"]["training_eligibility"] == "trainable"
    assert audit["samples"][0]["source_run_ids"] == [success.name, failure.name]
    pair_audit = [
        item
        for item in audit["samples"][0]["audit_items"]
        if item["name"] == "preference_pairing_policy_satisfied"
    ]
    assert pair_audit and pair_audit[0]["status"] == "passed"
    _assert_no_hidden_or_local_text(output.read_text(encoding="utf-8"))


def test_cli_export_commands(tmp_path: Path, capsys):
    run_dir = _success_run(tmp_path, "stage12-cli")
    _add_reasoning_trace_artifact(run_dir, "cli reasoning trace target")

    assert main(["export", str(run_dir), "--format", "sft_jsonl"]) == 0
    assert "导出完成" in capsys.readouterr().out
    assert (run_dir / "exports/sft.jsonl").exists()
    assert _latest_export_dir(run_dir / "exports").joinpath("export_manifest.json").exists()

    assert main(["export", str(run_dir), "--format", "rl_jsonl"]) == 0
    assert (run_dir / "exports/rl.jsonl").exists()
    assert _latest_export_dir(run_dir / "exports").joinpath("audit_report.json").exists()
    assert main(["inspect-export", str(run_dir / "exports"), "--all"]) == 0

    assert main(["export", str(tmp_path / "runs"), "--format", "preference_jsonl"]) == 0
    assert (tmp_path / "runs/exports/preference_skipped.json").exists()
    assert _latest_export_dir(tmp_path / "runs" / "exports").joinpath("audit_report.md").exists()
    assert main(["inspect-export", str(tmp_path / "runs" / "exports"), "--all"]) == 0

    assert main(["export", str(tmp_path / "runs"), "--format", "sft_jsonl"]) == 0
    assert (tmp_path / "runs/exports/sft.jsonl").exists()

    assert main(["export", str(tmp_path / "runs"), "--format", "rl_jsonl"]) == 0
    assert (tmp_path / "runs/exports/rl.jsonl").exists()

    assert main(
        [
            "export",
            str(run_dir),
            "--format",
            "provider_reasoning_trace_training_export",
            "--allow-oracle-feedback-training",
            "--allow-provider-reasoning-trace-training",
        ]
    ) == 0
    reasoning_output = run_dir / "exports/provider_reasoning_trace_training_export.jsonl"
    assert reasoning_output.exists()
    assert "cli reasoning trace target" in reasoning_output.read_text(encoding="utf-8")


def _success_run(tmp_path: Path, run_id: str) -> Path:
    return run_task(
        ROOT / "tests/fixtures/tasks/task_001.yaml",
        config_path=ROOT / "tests/fixtures/run_configs/replay_success.yaml",
        output_dir=tmp_path / "runs",
        run_id=run_id,
    )


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _assert_refs_exist(run_dir: Path, record: dict) -> None:
    for ref_key in ("prepared_message_refs", "content_replacement_state_refs"):
        for ref in record["payload"][ref_key]:
            assert ref["artifact_id"]
            assert ref["sha256"]
            assert ref["size_bytes"] > 0
            assert ref["relative_path"].startswith("artifacts/")
            assert (run_dir / ref["relative_path"]).exists()


def _assert_no_hidden_or_local_text(text: str) -> None:
    forbidden = [
        "gold_patch",
        "fail_to_pass_tests",
        "pass_to_pass_tests",
        "baseline raw",
        "baseline_stdout",
        "baseline_stderr",
        "/Users/",
        "/private/",
        "expected_outcome",
    ]
    for marker in forbidden:
        assert marker not in text


def _latest_export_dir(exports_dir: Path) -> Path:
    export_dirs = [
        path
        for path in exports_dir.iterdir()
        if path.is_dir() and (path / "export_manifest.json").exists()
    ]
    assert export_dirs
    return max(export_dirs, key=lambda path: path.stat().st_mtime_ns)


def _add_reasoning_trace_artifact(run_dir: Path, reasoning_content: str) -> None:
    artifact_path = run_dir / "artifacts" / "deepseek_reasoning_trace.json"
    artifact_path.write_text(
        json.dumps(
            {
                "schema_version": "repo_harness_provider_reasoning_trace_training_source_v0",
                "provider": "deepseek",
                "state_id": f"{run_dir.name}_model_call_0001_deepseek_reasoning",
                "run_id": run_dir.name,
                "model_call_id": f"{run_dir.name}_model_call_0001",
                "target_kind": "provider_reasoning_trace",
                "reasoning_content": reasoning_content,
                "reasoning_trace_training_allowed": True,
                "ordinary_sft_target_allowed": False,
                "default_training_payload_allowed": False,
                "not_public_safe_by_default": True,
                "public_demo_allowed": False,
                "requires_explicit_reasoning_export_policy": True,
                "raw_provider_artifact": False,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    manifest_path = run_dir / "artifacts.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.setdefault("artifacts", []).append(
        {
            "schema_version": "repo_harness_artifact_v0",
            "artifact_id": "artifact_deepseek_reasoning_trace",
            "relative_path": "artifacts/deepseek_reasoning_trace.json",
            "kind": "deepseek_provider_reasoning_trace",
            "sha256": _sha256_file(artifact_path),
            "size_bytes": artifact_path.stat().st_size,
            "redaction_status": "not_redacted_explicit_reasoning_trace_opt_in",
            "retention_policy": "provider_reasoning_trace_training_opt_in",
        }
    )
    manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")


def _sha256_file(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()
