import json
from pathlib import Path

from repo_harness.evaluation.runner import run_task


ROOT = Path(__file__).resolve().parents[2]


def test_create_file_replay_succeeds(tmp_path):
    run_dir = run_task(
        ROOT / "tests/fixtures/tasks/task_003_create_file.yaml",
        config_path=ROOT / "tests/fixtures/run_configs/replay_create_file.yaml",
        output_dir=tmp_path / "runs",
        run_id="stage08-create-file",
    )

    verifier = _read_json(run_dir / "verifier.json")
    metrics = _read_json(run_dir / "metrics.json")
    assert verifier["accepted"] is True
    assert metrics["run_outcome"] == "success"
    assert "app/helpers.py" in (run_dir / "final.diff").read_text(encoding="utf-8")


def test_bash_pytest_routes_to_run_tests(tmp_path):
    run_dir = run_task(
        ROOT / "tests/fixtures/tasks/task_001.yaml",
        config_path=ROOT / "tests/fixtures/run_configs/replay_bash_pytest.yaml",
        output_dir=tmp_path / "runs",
        run_id="stage08-bash-pytest",
    )

    events = _read_jsonl(run_dir / "events.jsonl")
    bash_result = next(
        event["data"]
        for event in events
        if event["event_type"] == "tool_completed"
        and event["data"]["tool_call_id"] == "call_bash_pytest"
    )
    permission = next(
        event["data"]
        for event in events
        if event["event_type"] == "permission_decision"
        and event["data"]["tool_call_id"] == "call_bash_pytest"
    )

    assert bash_result["requested_tool_name"] == "bash"
    assert bash_result["effective_tool_name"] == "run_tests"
    assert bash_result["route_reason"] == "recognized_task_test_command"
    assert permission["effective_tool_name"] == "run_tests"
    assert _read_json(run_dir / "verifier.json")["accepted"] is True


def test_schema_error_returns_tool_result_without_permission_decision(tmp_path):
    run_dir = run_task(
        ROOT / "tests/fixtures/tasks/task_001.yaml",
        config_path=ROOT / "tests/fixtures/run_configs/replay_schema_error.yaml",
        output_dir=tmp_path / "runs",
        run_id="stage08-schema-error",
    )

    events = _read_jsonl(run_dir / "events.jsonl")
    transcript = _read_jsonl(run_dir / "transcript.jsonl")
    assert any(
        event["event_type"] == "tool_validation_failed"
        and event["data"]["tool_call_id"] == "call_invalid_read"
        for event in events
    )
    assert not any(
        event["event_type"] == "permission_decision"
        and event["data"]["tool_call_id"] == "call_invalid_read"
        for event in events
    )
    tool_result = next(record for record in transcript if record.get("tool_call_id") == "call_invalid_read")
    assert tool_result["tool_result_id"] == "call_invalid_read_result"
    assert "schema_validation_failed" in tool_result["content_preview"]
    _assert_tool_calls_are_paired(events)


def test_unknown_tool_returns_paired_invalid_tool_result(tmp_path):
    run_dir = run_task(
        ROOT / "tests/fixtures/tasks/task_001.yaml",
        config_path=ROOT / "tests/fixtures/run_configs/replay_unknown_tool.yaml",
        output_dir=tmp_path / "runs",
        run_id="stage08-unknown-tool",
    )

    events = _read_jsonl(run_dir / "events.jsonl")
    assert any(event["event_type"] == "invalid_tool" for event in events)
    assert not any(event["event_type"] == "permission_decision" for event in events)
    _assert_tool_calls_are_paired(events)


def test_security_negative_replay_counts_permission_denials(tmp_path):
    run_dir = run_task(
        ROOT / "tests/fixtures/tasks/task_security_probe.yaml",
        config_path=ROOT / "tests/fixtures/run_configs/replay_security_negative_minimal.yaml",
        output_dir=tmp_path / "runs",
        run_id="stage08-security-negative",
    )

    metrics = _read_json(run_dir / "metrics.json")
    summary = (run_dir / "summary.md").read_text(encoding="utf-8")
    assert metrics["permission_denial_count"] == 4
    assert "permission_denial_count: 4" in summary
    assert "permission_denial_reasons" in summary
    assert "Command is denied by default: curl" in summary
    _assert_tool_calls_are_paired(_read_jsonl(run_dir / "events.jsonl"))


def test_dangerous_pytest_shell_syntax_is_denied_in_agent_loop(tmp_path):
    replay_path, config_path = _write_single_bash_replay(
        tmp_path,
        command="pytest -q | tee out.txt",
        run_id="stage08-pytest-pipe",
    )
    run_dir = run_task(
        ROOT / "tests/fixtures/tasks/task_001.yaml",
        config_path=config_path,
        output_dir=tmp_path / "runs",
        run_id="stage08-pytest-pipe",
    )

    events = _read_jsonl(run_dir / "events.jsonl")
    decision = next(event["data"] for event in events if event["event_type"] == "permission_decision")
    assert replay_path.exists()
    assert decision["decision"] == "deny"
    assert decision["effective_tool_name"] == "bash"
    assert "Unsupported shell syntax" in decision["reason"]
    _assert_tool_calls_are_paired(events)


def test_bash_cwd_escape_returns_denied_tool_result(tmp_path):
    _, config_path = _write_single_bash_replay(
        tmp_path,
        command="pwd",
        cwd="../outside",
        run_id="stage08-cwd-escape",
    )
    run_dir = run_task(
        ROOT / "tests/fixtures/tasks/task_001.yaml",
        config_path=config_path,
        output_dir=tmp_path / "runs",
        run_id="stage08-cwd-escape",
    )

    events = _read_jsonl(run_dir / "events.jsonl")
    transcript = _read_jsonl(run_dir / "transcript.jsonl")
    decision = next(event["data"] for event in events if event["event_type"] == "permission_decision")
    tool_result = next(record for record in transcript if record.get("tool_call_id") == "call_bash")
    assert decision["decision"] == "deny"
    assert "workspace" in decision["reason"]
    assert tool_result["tool_result_id"] == "call_bash_result"
    _assert_tool_calls_are_paired(events)


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


def _write_single_bash_replay(
    tmp_path: Path,
    *,
    command: str,
    run_id: str,
    cwd: str | None = None,
) -> tuple[Path, Path]:
    replay_path = tmp_path / f"{run_id}.yaml"
    cwd_block = f"\n      cwd: {json.dumps(cwd)}" if cwd is not None else ""
    replay_path.write_text(
        f"""
script_id: {run_id}
task_id: task_001
steps:
  - step_id: bash_request
    action: tool_call
    tool_call_id: call_bash
    tool_name: bash
    arguments:
      command: {json.dumps(command)}{cwd_block}
  - step_id: final
    action: final_answer
    assistant_text: "Done."
""".lstrip(),
        encoding="utf-8",
    )
    config_path = tmp_path / f"{run_id}_config.yaml"
    config_path.write_text(
        f"""
run_id_prefix: stage08
model:
  provider: replay
  model_id: replay-script-v0
  replay_script_path: {replay_path}
runtime:
  scaffold_id: simple_react
  execution_mode: local_process
  permission_mode: auto
  max_turns: 4
  max_tool_calls: 8
  max_test_runs: 2
workspace:
  output_dir: {tmp_path / "runs"}
  keep_workspace: true
  default_command_timeout_sec: 60
""".lstrip(),
        encoding="utf-8",
    )
    return replay_path, config_path
