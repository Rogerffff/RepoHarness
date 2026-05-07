import json
from pathlib import Path

from repo_harness.evaluation.runner import run_task


ROOT = Path(__file__).resolve().parents[2]


def test_disabled_feedback_policy_blocks_bash_pytest_bypass_in_full_run(tmp_path: Path):
    config_path = tmp_path / "disabled_bash_pytest.yaml"
    config_path.write_text(
        f"""
run_id_prefix: command-policy
model:
  provider: replay
  model_id: replay-script-v0
  replay_script_path: {ROOT / "tests/fixtures/replays/task_001_bash_pytest.yaml"}
runtime:
  scaffold_id: simple_react
  execution_mode: local_process
  permission_mode: auto
  test_feedback_policy: disabled
  max_turns: 4
  max_tool_calls: 6
  max_test_runs: 2
workspace:
  output_dir: {tmp_path / "runs"}
  keep_workspace: true
  default_command_timeout_sec: 60
""",
        encoding="utf-8",
    )

    run_dir = run_task(
        ROOT / "tests/fixtures/tasks/task_001.yaml",
        config_path=config_path,
        output_dir=tmp_path / "runs",
        run_id="disabled-bash-policy",
    )

    events = _read_jsonl(run_dir / "events.jsonl")
    denied = next(
        event["data"]
        for event in events
        if event["event_type"] == "tool_denied"
        and event["data"]["tool_call_id"] == "call_bash_pytest"
    )
    typed = denied["typed"]
    policy_decision = denied["effective_arguments"]["command_policy_decision"]
    assert denied["requested_tool_name"] == "bash"
    assert denied["effective_tool_name"] == "bash"
    assert denied["error_type"] == "permission_denied"
    assert typed["reason_code"] == "denied_by_final_only_feedback_policy"
    assert typed["command_category"] == "public_test"
    assert policy_decision["matched_rule"] == "test_feedback_disabled_blocks_bash_test"
    assert policy_decision["safe_argv"] == ["pytest", "-q"]
    assert not any(
        event["event_type"] == "tool_completed"
        and event["data"]["tool_call_id"] == "call_bash_pytest"
        for event in events
    )
    metrics = _read_json(run_dir / "metrics.json")
    assert metrics["interaction_efficiency"]["test_feedback_policy"] == "disabled"
    assert metrics["interaction_efficiency"]["public_tests_ran"] is False


def test_run_config_records_stage12_command_policy_and_environment_hash(tmp_path: Path):
    run_dir = run_task(
        ROOT / "tests/fixtures/tasks/task_001.yaml",
        config_path=ROOT / "tests/fixtures/run_configs/replay_success_minimal.yaml",
        output_dir=tmp_path / "runs",
        run_id="environment-policy-facts",
    )

    facts = _read_json(run_dir / "run_config_facts.json")
    workspace_execution = facts["environment_fingerprint"]["workspace_execution"]
    assert facts["shell_command_policy_version"] == "repo_harness_command_policy_v0"
    assert workspace_execution["shell_command_policy_version"] == "repo_harness_command_policy_v0"
    assert len(facts["environment_fingerprint"]["environment_spec_hash"]) == 64
    assert workspace_execution["source_checkout"]["source_type"] == "fixture_path"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
