import json
import shutil
from pathlib import Path

import pytest

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
    assert "app/helpers.py" in metrics["patch_stats"]["added_files"]
    assert "app/helpers.py" in metrics["patch_stats"]["untracked_text_files"]
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


def test_bash_git_diff_no_index_outside_path_is_denied(tmp_path):
    _, config_path = _write_single_bash_replay(
        tmp_path,
        command="git diff --no-index /etc/hosts calculator.py",
        run_id="stage08-git-diff-no-index",
    )
    run_dir = run_task(
        ROOT / "tests/fixtures/tasks/task_001.yaml",
        config_path=config_path,
        output_dir=tmp_path / "runs",
        run_id="stage08-git-diff-no-index",
    )

    events = _read_jsonl(run_dir / "events.jsonl")
    transcript = _read_jsonl(run_dir / "transcript.jsonl")
    decision = next(event["data"] for event in events if event["event_type"] == "permission_decision")
    tool_result = next(record for record in transcript if record.get("tool_call_id") == "call_bash")
    assert decision["decision"] == "deny"
    assert decision["matched_rule"] == "bash_command_safety"
    assert "--no-index" in decision["reason"]
    assert tool_result["tool_result_id"] == "call_bash_result"
    assert "root:" not in tool_result["content_preview"]
    _assert_tool_calls_are_paired(events)


def test_bash_git_show_head_does_not_expose_sensitive_history(tmp_path):
    task_path = _write_sensitive_repo_task(tmp_path, task_id="task_sensitive_git_history")
    _, config_path = _write_single_bash_replay(
        tmp_path,
        command="git show HEAD",
        run_id="stage08-sensitive-git-history",
        task_id="task_sensitive_git_history",
    )

    run_dir = run_task(
        task_path,
        config_path=config_path,
        output_dir=tmp_path / "runs",
        run_id="stage08-sensitive-git-history",
    )

    events = _read_jsonl(run_dir / "events.jsonl")
    transcript = _read_jsonl(run_dir / "transcript.jsonl")
    decision = next(event["data"] for event in events if event["event_type"] == "permission_decision")
    tool_result = next(record for record in transcript if record.get("tool_call_id") == "call_bash")
    assert decision["decision"] == "deny"
    assert decision["matched_rule"] == "bash_command_safety"
    assert "explicit safe path" in decision["reason"]
    assert "SUPER_SECRET" not in tool_result["content_preview"]
    assert "id_rsa" not in tool_result["content_preview"]
    _assert_tool_calls_are_paired(events)


def test_grep_does_not_expose_sensitive_file_content(tmp_path):
    task_path = _write_sensitive_repo_task(tmp_path, task_id="task_sensitive_grep")
    replay_path = tmp_path / "sensitive_grep.yaml"
    replay_path.write_text(
        """
script_id: sensitive_grep
task_id: task_sensitive_grep
steps:
  - step_id: grep_secret
    action: tool_call
    tool_call_id: call_grep
    tool_name: grep
    arguments:
      query: "needle"
      root: "."
  - step_id: final
    action: final_answer
    assistant_text: "Searched files."
""".lstrip(),
        encoding="utf-8",
    )
    config_path = _write_replay_config(tmp_path, replay_path, run_id="stage08-sensitive-grep")

    run_dir = run_task(
        task_path,
        config_path=config_path,
        output_dir=tmp_path / "runs",
        run_id="stage08-sensitive-grep",
    )

    transcript = _read_jsonl(run_dir / "transcript.jsonl")
    tool_result = next(record for record in transcript if record.get("tool_call_id") == "call_grep")
    assert "SUPER_SECRET" not in tool_result["content_preview"]
    assert "id_rsa" not in tool_result["content_preview"]
    for ref in tool_result["content_artifact_refs"]:
        artifact_text = (run_dir / ref["relative_path"]).read_text(encoding="utf-8")
        assert "SUPER_SECRET" not in artifact_text
        assert "id_rsa" not in artifact_text


@pytest.mark.parametrize("command", ["find .", "ls -a ."])
def test_bash_file_enumeration_does_not_expose_sensitive_names(tmp_path, command):
    task_id = f"task_sensitive_bash_{command.split()[0]}"
    task_path = _write_sensitive_repo_task(tmp_path, task_id=task_id)
    _, config_path = _write_single_bash_replay(
        tmp_path,
        command=command,
        run_id=f"stage08-sensitive-bash-{command.split()[0]}",
        task_id=task_id,
    )

    run_dir = run_task(
        task_path,
        config_path=config_path,
        output_dir=tmp_path / "runs",
        run_id=f"stage08-sensitive-bash-{command.split()[0]}",
    )

    events = _read_jsonl(run_dir / "events.jsonl")
    transcript = _read_jsonl(run_dir / "transcript.jsonl")
    decision = next(event["data"] for event in events if event["event_type"] == "permission_decision")
    tool_result = next(record for record in transcript if record.get("tool_call_id") == "call_bash")
    assert decision["decision"] == "deny"
    assert decision["matched_rule"] == "bash_command_safety"
    assert tool_result["tool_result_id"] == "call_bash_result"
    assert ".env" not in tool_result["content_preview"]
    assert "id_rsa" not in tool_result["content_preview"]
    _assert_tool_calls_are_paired(events)


def test_list_files_does_not_expose_sensitive_file_names(tmp_path):
    task_path = _write_sensitive_repo_task(tmp_path, task_id="task_sensitive_listing")
    replay_path = tmp_path / "sensitive_listing.yaml"
    replay_path.write_text(
        """
script_id: sensitive_listing
task_id: task_sensitive_listing
steps:
  - step_id: list_root
    action: tool_call
    tool_call_id: call_list
    tool_name: list_files
    arguments:
      path: "."
      pattern: "**/*"
  - step_id: final
    action: final_answer
    assistant_text: "Listed files."
""".lstrip(),
        encoding="utf-8",
    )
    config_path = _write_replay_config(tmp_path, replay_path, run_id="stage08-sensitive-listing")

    run_dir = run_task(
        task_path,
        config_path=config_path,
        output_dir=tmp_path / "runs",
        run_id="stage08-sensitive-listing",
    )

    transcript = _read_jsonl(run_dir / "transcript.jsonl")
    tool_result = next(record for record in transcript if record.get("tool_call_id") == "call_list")
    assert "calculator.py" in tool_result["content_preview"]
    assert ".env" not in tool_result["content_preview"]
    assert "private.pem" not in tool_result["content_preview"]
    assert "id_rsa" not in tool_result["content_preview"]


def test_run_tests_timeout_returns_tool_timeout_event(tmp_path):
    fixture_root = tmp_path / "fixtures"
    task_dir = fixture_root / "tasks"
    repo_dir = fixture_root / "repos" / "feedback_timeout"
    task_dir.mkdir(parents=True)
    shutil.copytree(ROOT / "tests/fixtures/repos/buggy_calculator", repo_dir)
    task_path = task_dir / "task_feedback_timeout.yaml"
    source = (ROOT / "tests/fixtures/tasks/task_001.yaml").read_text(encoding="utf-8")
    task_path.write_text(
        source.replace("id: task_001", "id: task_feedback_timeout")
        .replace("task_version: task_001_v0", "task_version: task_feedback_timeout_v0")
        .replace("repo: ../repos/buggy_calculator", "repo: ../repos/feedback_timeout")
        .replace("test_timeout_sec: 30", "test_timeout_sec: 1")
        .replace("final_verifier_timeout_sec: 60", "final_verifier_timeout_sec: 1"),
        encoding="utf-8",
    )
    replay_path = tmp_path / "feedback_timeout.yaml"
    replay_path.write_text(
        """
script_id: feedback_timeout
task_id: task_feedback_timeout
steps:
  - step_id: slow_tests
    action: tool_call
    tool_call_id: call_slow_tests
    tool_name: edit_file
    arguments:
      path: tests/test_calculator.py
      old_text: "import pytest\\n\\nfrom calculator import add, divide\\n"
      new_text: "import pytest\\nimport time\\n\\ntime.sleep(2)\\n\\nfrom calculator import add, divide\\n"
  - step_id: run_tests
    action: tool_call
    tool_call_id: call_run_tests
    tool_name: run_tests
    arguments: {}
  - step_id: final
    action: final_answer
    assistant_text: "The feedback verifier is expected to time out."
""".lstrip(),
        encoding="utf-8",
    )
    config_path = _write_replay_config(tmp_path, replay_path, run_id="stage08-feedback-timeout")

    run_dir = run_task(
        task_path,
        config_path=config_path,
        output_dir=tmp_path / "runs",
        run_id="stage08-feedback-timeout",
    )

    events = _read_jsonl(run_dir / "events.jsonl")
    timeout_event = next(
        event
        for event in events
        if event["data"].get("tool_call_id") == "call_run_tests"
        and event["event_type"].startswith("tool_")
        and event["event_type"] != "tool_requested"
    )
    assert timeout_event["event_type"] == "tool_timeout"
    assert timeout_event["data"]["status"] == "timeout"
    assert timeout_event["data"]["error_type"] == "test_timeout"
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


def _write_sensitive_repo_task(tmp_path: Path, *, task_id: str) -> Path:
    fixture_root = tmp_path / "fixtures"
    task_dir = fixture_root / "tasks"
    repo_dir = fixture_root / "repos" / task_id
    task_dir.mkdir(parents=True)

    shutil.copytree(ROOT / "tests/fixtures/repos/buggy_calculator", repo_dir)
    (repo_dir / ".env").write_text("TOKEN=secret\n", encoding="utf-8")
    (repo_dir / "private.pem").write_text("-----BEGIN PRIVATE KEY-----\n", encoding="utf-8")
    (repo_dir / "id_rsa").write_text("needle SUPER_SECRET\n", encoding="utf-8")
    (repo_dir / "nested").mkdir()
    (repo_dir / "nested" / "id_ed25519").write_text("nested secret\n", encoding="utf-8")
    task_path = task_dir / f"{task_id}.yaml"
    source = (ROOT / "tests/fixtures/tasks/task_001.yaml").read_text(encoding="utf-8")
    task_path.write_text(
        source.replace("id: task_001", f"id: {task_id}")
        .replace("task_version: task_001_v0", f"task_version: {task_id}_v0")
        .replace("repo: ../repos/buggy_calculator", f"repo: ../repos/{task_id}"),
        encoding="utf-8",
    )
    return task_path


def _write_single_bash_replay(
    tmp_path: Path,
    *,
    command: str,
    run_id: str,
    task_id: str = "task_001",
    cwd: str | None = None,
) -> tuple[Path, Path]:
    replay_path = tmp_path / f"{run_id}.yaml"
    cwd_block = f"\n      cwd: {json.dumps(cwd)}" if cwd is not None else ""
    replay_path.write_text(
        f"""
script_id: {run_id}
task_id: {task_id}
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


def _write_replay_config(tmp_path: Path, replay_path: Path, *, run_id: str) -> Path:
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
    return config_path
