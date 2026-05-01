import json
from pathlib import Path

from repo_harness.evaluation.runner import run_task
from repo_harness.export import export_run_or_runs
from repo_harness.model_client.mock_smoke import build_mock_provider_smoke_report


ROOT = Path(__file__).resolve().parents[2]


def test_mock_provider_e2e_smoke_run_and_report(tmp_path: Path):
    run_dir = run_task(
        ROOT / "tests/fixtures/tasks/task_001.yaml",
        config_path=ROOT / "tests/fixtures/run_configs/v2/mock_provider_smoke.yaml",
        output_dir=tmp_path / "runs",
        run_id="mock-provider-smoke",
    )

    metrics = _read_json(run_dir / "metrics.json")
    events = _read_jsonl(run_dir / "events.jsonl")
    manifest = _read_json(run_dir / "artifacts.json")
    report = build_mock_provider_smoke_report(run_dir)

    assert metrics["run_outcome"] == "success"
    assert metrics["final_verifier_status"] == "accepted"
    assert metrics["interaction_efficiency"]["agent_stop_reason"] == "final_answer"
    assert report["status"] == "accepted"
    assert report["provider"] == "mock"
    assert report["raw_artifact_redaction_status"] == "redacted"
    assert not report["failures"]
    assert any(event["event_type"] == "model_call_completed" for event in events)
    assert any(
        event["event_type"] == "model_call_completed"
        and event["data"]["provider"] == "mock"
        for event in events
    )
    raw_kinds = {
        artifact["kind"]: artifact["redaction_status"]
        for artifact in manifest["artifacts"]
        if artifact["kind"].startswith("raw_mock_provider")
    }
    assert raw_kinds == {
        "raw_mock_provider_request": "redacted",
        "raw_mock_provider_response": "redacted",
    }


def test_mock_provider_error_path_records_model_error_type(tmp_path: Path):
    config_path = tmp_path / "mock_auth_error.yaml"
    config_path.write_text(
        f"""
run_id_prefix: stage10
model:
  provider: mock
  model_id: mock-provider-v0
  provider_specific_options:
    mock_scenario: auth_error
runtime:
  scaffold_id: simple_react
  execution_mode: local_process
  permission_mode: auto
  test_feedback_policy: public_only
  max_turns: 2
  max_tool_calls: 4
  max_test_runs: 1
workspace:
  output_dir: {tmp_path / "runs"}
  keep_workspace: true
  default_command_timeout_sec: 60
""".lstrip(),
        encoding="utf-8",
    )

    run_dir = run_task(
        ROOT / "tests/fixtures/tasks/task_001.yaml",
        config_path=config_path,
        output_dir=tmp_path / "runs",
        run_id="mock-auth-error",
    )

    metrics = _read_json(run_dir / "metrics.json")
    events = _read_jsonl(run_dir / "events.jsonl")
    assert metrics["run_outcome"] == "failed"
    assert metrics["interaction_efficiency"]["agent_stop_reason"] == "model_error"
    assert any(
        event["event_type"] == "model_call_completed"
        and event["data"]["model_error_type"] == "auth_error"
        for event in events
    )

    export_run_or_runs(run_dir, export_format="sft_jsonl")
    export_dir = next((run_dir / "exports").glob("sft_*"))
    data_path = export_dir / "data.sft.jsonl"
    audit = _read_json(export_dir / "audit_report.json")
    transcript = _read_jsonl(run_dir / "transcript.jsonl")
    assert data_path.read_text(encoding="utf-8") == ""
    assert audit["samples"][0]["training_eligibility"] == "invalid"
    assert audit["samples"][0]["invalid_reason"] == "model_error:auth_error"
    assert not any(
        record["role"] == "assistant" and record.get("trainable")
        for record in transcript
    )


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
