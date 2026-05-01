import json
from pathlib import Path

from repo_harness.cli.main import main
from repo_harness.evaluation.runner import run_task
from repo_harness.export import ExportPolicy, export_preference_jsonl, export_rl_jsonl, export_sft_jsonl


ROOT = Path(__file__).resolve().parents[2]


def test_sft_export_from_success_run_masks_assistant_actions(tmp_path: Path):
    run_dir = _success_run(tmp_path, "stage12-sft")

    output = export_sft_jsonl(run_dir)
    record = _read_jsonl(output)[0]
    text = output.read_text(encoding="utf-8")

    assert record["filter_status"] == "filtered"
    assert record["invalid_for_training"] is True
    assert record["quality"]["training_eligibility"] == "diagnostic_only"
    assert record["invalid_reason"] == "oracle_hidden_feedback_diagnostic_only"
    assert any(message.get("role") == "assistant" and message.get("tool_calls") for message in record["payload"]["messages"])
    assert any(message.get("role") == "tool" for message in record["payload"]["messages"])
    assert 1 in record["payload"]["loss_mask"]
    assert 1 in record["payload"]["observation_mask"]
    assert record["payload"]["loss_mask"][record["payload"]["observation_mask"].index(1)] == 0
    assert record["payload"]["reward_metadata_ref"]["kind"] == "reward_metadata"
    assert record["payload"]["prepared_message_refs"]
    assert record["payload"]["content_replacement_state_refs"]
    assert any(
        message.get("observation_source") == "prepared_messages"
        for message in record["payload"]["messages"]
        if message.get("role") == "tool"
    )
    assert all(
        message.get("observation_source") == "prepared_messages"
        for message in record["payload"]["messages"]
        if message.get("role") == "tool"
    )
    assert "without_followup_context" not in text
    _assert_refs_exist(run_dir, record)
    _assert_no_hidden_or_local_text(text)
    export_dir = _latest_export_dir(run_dir / "exports")
    canonical_records = _read_jsonl(export_dir / "data.sft.jsonl")
    audit = _read_json(export_dir / "audit_report.json")
    assert canonical_records == []
    assert audit["summary"]["diagnostic_only_count"] == 1
    assert audit["status"] == "passed_with_warnings"


def test_rl_export_uses_final_reward_metadata(tmp_path: Path):
    run_dir = _success_run(tmp_path, "stage12-rl")

    output = export_rl_jsonl(run_dir)
    record = _read_jsonl(output)[0]
    reward = _read_json(run_dir / "reward.json")

    assert record["payload"]["reward"] == reward["final_reward"]
    assert record["payload"]["reward_metadata"]["reward_metadata_ref"]["kind"] == "reward_metadata"
    assert record["payload"]["final_verifier_ref"]["kind"] == "final_verifier_result"
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
    assert record["payload"]["chosen"]["reward"] > record["payload"]["rejected"]["reward"]
    assert canonical_records
    assert canonical_records[0]["quality"]["training_eligibility"] == "trainable"
    assert audit["samples"][0]["source_run_ids"] == [success.name, failure.name]
    _assert_no_hidden_or_local_text(output.read_text(encoding="utf-8"))


def test_cli_export_commands(tmp_path: Path, capsys):
    run_dir = _success_run(tmp_path, "stage12-cli")

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
    for ref_key in ("reward_metadata_ref", "final_verifier_ref"):
        ref = record["payload"][ref_key]
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
