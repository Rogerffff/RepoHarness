import json
from pathlib import Path

from repo_harness.evaluation.runner import run_task


ROOT = Path(__file__).resolve().parents[2]


def test_agent_loop_replay_stops_on_feedback_tests_passed(tmp_path):
    run_dir = run_task(
        ROOT / "tests/fixtures/tasks/task_001.yaml",
        config_path=ROOT / "tests/fixtures/run_configs/replay_success_minimal.yaml",
        output_dir=tmp_path / "runs",
        run_id="stage10-feedback",
    )

    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    summary = (run_dir / "summary.md").read_text(encoding="utf-8")
    assert metrics["interaction_efficiency"]["agent_stop_reason"] == "feedback_tests_passed"
    assert "agent_stop_reason: feedback_tests_passed" in summary
    assert json.loads((run_dir / "verifier.json").read_text(encoding="utf-8"))["accepted"] is True


def test_agent_loop_replay_schema_error_can_continue(tmp_path):
    run_dir = run_task(
        ROOT / "tests/fixtures/tasks/task_001.yaml",
        config_path=ROOT / "tests/fixtures/run_configs/replay_schema_error.yaml",
        output_dir=tmp_path / "runs",
        run_id="stage10-schema-error",
    )

    events = _read_jsonl(run_dir / "events.jsonl")
    summary = (run_dir / "summary.md").read_text(encoding="utf-8")
    assert any(event["event_type"] == "tool_validation_failed" for event in events)
    assert "agent_stop_reason: final_answer" in summary
    _assert_tool_calls_are_paired(events)


def test_agent_loop_replay_permission_denial_can_continue(tmp_path):
    run_dir = run_task(
        ROOT / "tests/fixtures/tasks/task_security_probe.yaml",
        config_path=ROOT / "tests/fixtures/run_configs/replay_security_negative_minimal.yaml",
        output_dir=tmp_path / "runs",
        run_id="stage10-denied",
    )

    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    summary = (run_dir / "summary.md").read_text(encoding="utf-8")
    assert metrics["permission_denial_count"] == 4
    assert "agent_stop_reason: final_answer" in summary
    assert "permission_denial_reasons" in summary


def test_agent_loop_replay_max_turns(tmp_path):
    replay_path = tmp_path / "long.yaml"
    replay_path.write_text(
        """
script_id: long
task_id: task_001
steps:
  - step_id: read_one
    action: tool_call
    tool_call_id: call_read_one
    tool_name: read_file
    arguments:
      path: calculator.py
  - step_id: read_two
    action: tool_call
    tool_call_id: call_read_two
    tool_name: read_file
    arguments:
      path: calculator.py
""".lstrip(),
        encoding="utf-8",
    )
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        f"""
run_id_prefix: stage10
model:
  provider: replay
  model_id: replay-script-v0
  replay_script_path: {replay_path}
runtime:
  scaffold_id: simple_react
  execution_mode: local_process
  permission_mode: auto
  max_turns: 1
  max_tool_calls: 20
  max_test_runs: 4
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
        run_id="stage10-max-turns",
    )

    assert "agent_stop_reason: max_turns" in (run_dir / "summary.md").read_text(encoding="utf-8")


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
