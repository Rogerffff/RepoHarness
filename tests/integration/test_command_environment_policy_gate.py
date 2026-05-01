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
    assert any(event["event_type"] == "test_feedback_disabled" for event in events)
    assert any(
        event["event_type"] == "tool_denied"
        and event["error_type"] == "test_feedback_disabled"
        and event["data"]["effective_tool_name"] == "run_tests"
        for event in events
    )


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
