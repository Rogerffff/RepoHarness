import json
from pathlib import Path

import pytest

from repo_harness.errors import ConfigError
from repo_harness.evaluation.runner import run_task
from repo_harness.tools import build_tool


ROOT = Path(__file__).resolve().parents[2]


def test_replay_success_vertical_slice(tmp_path):
    run_dir = run_task(
        ROOT / "tests/fixtures/tasks/task_001.yaml",
        config_path=ROOT / "tests/fixtures/run_configs/replay_success_minimal.yaml",
        output_dir=tmp_path / "runs",
        run_id="stage07-success",
    )

    assert (run_dir / "dependency_state.json").is_file()
    assert (run_dir / "final.diff").is_file()
    assert (run_dir / "final.patch").is_file()
    assert (run_dir / "verifier.json").is_file()
    assert (run_dir / "summary.md").is_file()

    verifier = _read_json(run_dir / "verifier.json")
    metrics = _read_json(run_dir / "metrics.json")
    reward = _read_json(run_dir / "reward.json")
    assert verifier["accepted"] is True
    assert metrics["run_outcome"] == "success"
    assert metrics["final_verifier_status"] == "accepted"
    assert reward["sources"]["final_verifier_ref"]["artifact_id"]
    assert reward["sources"]["final_patch_ref"]["sha256"]
    assert reward["sources"]["final_diff_ref"]["sha256"]
    assert reward["sources"]["events_ref"]["relative_path"] == "events.jsonl"

    events = _read_jsonl(run_dir / "events.jsonl")
    event_types = {event["event_type"] for event in events}
    assert "model_call_started" in event_types
    assert "model_call_completed" in event_types
    assert "tool_requested" in event_types
    assert "permission_decision" in event_types
    assert "tool_completed" in event_types
    assert "verifier_final" in event_types
    assert "run_finished" in event_types
    _assert_tool_calls_are_paired(events)
    _assert_model_calls_have_prepared_messages(events)

    prepared_payloads = _artifact_payloads(run_dir, kind="prepared_messages")
    prepared_text = json.dumps(prepared_payloads, ensure_ascii=False)
    assert "gold_patch" not in prepared_text
    assert "fail_to_pass_tests" not in prepared_text
    assert "expected_outcome" not in prepared_text
    assert "repo_source" not in prepared_text
    assert "tests/fixtures/repos" not in prepared_text

    with pytest.raises(ConfigError, match="run directory 已存在"):
        run_task(
            ROOT / "tests/fixtures/tasks/task_001.yaml",
            config_path=ROOT / "tests/fixtures/run_configs/replay_success_minimal.yaml",
            output_dir=tmp_path / "runs",
            run_id="stage07-success",
        )


def test_replay_failure_still_writes_reviewable_artifacts(tmp_path):
    run_dir = run_task(
        ROOT / "tests/fixtures/tasks/task_001.yaml",
        config_path=ROOT / "tests/fixtures/run_configs/replay_failure_minimal.yaml",
        output_dir=tmp_path / "runs",
        run_id="stage07-failure",
    )

    verifier = _read_json(run_dir / "verifier.json")
    metrics = _read_json(run_dir / "metrics.json")
    assert verifier["accepted"] is False
    assert metrics["run_outcome"] == "failed"
    assert (run_dir / "final.diff").is_file()
    assert (run_dir / "summary.md").is_file()
    _assert_tool_calls_are_paired(_read_jsonl(run_dir / "events.jsonl"))


def test_security_negative_replay_records_permission_denials(tmp_path):
    run_dir = run_task(
        ROOT / "tests/fixtures/tasks/task_security_probe.yaml",
        config_path=ROOT / "tests/fixtures/run_configs/replay_security_negative_minimal.yaml",
        output_dir=tmp_path / "runs",
        run_id="stage07-security-negative",
    )

    events = _read_jsonl(run_dir / "events.jsonl")
    denied = [
        event
        for event in events
        if event["event_type"] == "permission_decision"
        and event["data"]["decision"] == "deny"
    ]
    invalid = [event for event in events if event["event_type"] == "invalid_tool"]
    assert len(denied) == 4
    assert len(invalid) == 0
    _assert_tool_calls_are_paired(events)

    transcript = _read_jsonl(run_dir / "transcript.jsonl")
    tool_results = [record for record in transcript if record["role"] == "tool"]
    assert {record["tool_call_id"] for record in tool_results} == {
        "call_read_outside",
        "call_read_env",
        "call_curl",
        "call_git_fetch",
    }


def test_minimal_tool_factory_uses_conservative_defaults():
    edit_tool = build_tool("edit_file")
    run_tests_tool = build_tool("run_tests")
    read_tool = build_tool("read_file")

    assert edit_tool.is_read_only is False
    assert edit_tool.is_concurrency_safe is False
    assert edit_tool.is_destructive is False
    assert run_tests_tool.is_concurrency_safe is False
    assert read_tool.is_read_only is True
    assert read_tool.is_concurrency_safe is True


def test_plan_and_ask_modes_deny_non_read_tools(tmp_path):
    for mode in ("plan", "ask", "deny"):
        config_path = _write_mode_config(tmp_path, mode)
        run_dir = run_task(
            ROOT / "tests/fixtures/tasks/task_001.yaml",
            config_path=config_path,
            output_dir=tmp_path / "runs",
            run_id=f"stage07-{mode}",
        )
        decisions = [
            event["data"]
            for event in _read_jsonl(run_dir / "events.jsonl")
            if event["event_type"] == "permission_decision"
        ]
        by_call = {decision["tool_call_id"]: decision for decision in decisions}

        assert by_call["call_read_calculator"]["decision"] == "allow"
        assert by_call["call_edit_divide"]["decision"] == "deny"
        assert by_call["call_run_tests"]["decision"] == "deny"
        if mode == "ask":
            assert by_call["call_edit_divide"]["requires_user_input"] is True
            assert by_call["call_edit_divide"]["non_interactive_resolution"] == "deny"

        metrics = _read_json(run_dir / "metrics.json")
        assert metrics["permission_denial_count"] == 2


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _assert_tool_calls_are_paired(events: list[dict]) -> None:
    requested = {
        event["data"]["tool_call_id"]
        for event in events
        if event["event_type"] == "tool_requested"
    }
    completed = {
        event["data"]["tool_call_id"]
        for event in events
        if event["event_type"] in {
            "tool_completed",
            "tool_denied",
            "tool_failed",
            "tool_timeout",
            "tool_interrupted",
        }
    }
    assert requested == completed


def _assert_model_calls_have_prepared_messages(events: list[dict]) -> None:
    completed = [event for event in events if event["event_type"] == "model_call_completed"]
    assert completed
    for event in completed:
        assert event["data"]["prepared_messages_ref"]["relative_path"].startswith("artifacts/")
        assert event["data"]["raw_provider_request_ref"]["relative_path"].startswith("artifacts/")
        assert event["data"]["raw_provider_request_ref"] != event["data"]["prepared_messages_ref"]
        assert event["data"]["model_input_hash"]


def _artifact_payloads(run_dir: Path, *, kind: str) -> list[dict]:
    manifest = _read_json(run_dir / "artifacts.json")
    payloads = []
    for artifact in manifest["artifacts"]:
        if artifact["kind"] == kind:
            payloads.append(_read_json(run_dir / artifact["relative_path"]))
    return payloads


def _write_mode_config(tmp_path: Path, mode: str) -> Path:
    config_path = tmp_path / f"replay_{mode}.yaml"
    config_path.write_text(
        f"""
run_id_prefix: stage07
model:
  provider: replay
  model_id: replay-script-v0
  replay_script_path: {ROOT / "tests/fixtures/replays/task_001_success.yaml"}
runtime:
  scaffold_id: simple_react
  execution_mode: local_process
  permission_mode: {mode}
  max_turns: 8
  max_tool_calls: 20
  max_test_runs: 4
workspace:
  output_dir: {tmp_path / "runs"}
  keep_workspace: true
  default_command_timeout_sec: 60
""".lstrip(),
        encoding="utf-8",
    )
    return config_path
