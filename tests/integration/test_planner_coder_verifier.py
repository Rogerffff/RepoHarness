import json
from pathlib import Path

from repo_harness.evaluation.runner import run_task


ROOT = Path(__file__).resolve().parents[2]


def test_planner_coder_verifier_replay_completes_phase_path(tmp_path: Path):
    run_dir = run_task(
        ROOT / "tests/fixtures/tasks/task_001.yaml",
        config_path=ROOT / "tests/fixtures/run_configs/v2/planner_coder_verifier_success.yaml",
        output_dir=tmp_path / "runs",
        run_id="planner-coder-verifier-success",
    )

    facts = _read_json(run_dir / "run_config_facts.json")
    metadata = _read_json(run_dir / "run_metadata.json")
    metrics = _read_json(run_dir / "metrics.json")
    events = _read_jsonl(run_dir / "events.jsonl")

    assert facts["scaffold_id"] == "planner_coder_verifier"
    assert facts["feedback_tests_passed_policy"] == "require_model_final"
    assert facts["phase_policy"] == "repo_harness_planner_coder_verifier_linear_v0"
    assert metadata["scaffold_id"] == "planner_coder_verifier"
    assert metadata["scaffold_facts"]["phase_policy"] == facts["phase_policy"]
    assert metrics["run_outcome"] == "success"
    assert metrics["interaction_efficiency"]["agent_stop_reason"] == "final_answer"
    assert metrics["test_run_count"] == 1
    assert metrics["interaction_efficiency"]["feedback_verifier_accepted"] is True
    assert _phase_pairs(events) == [
        ("planner", "coder"),
        ("coder", "verifier"),
        ("verifier", "final"),
    ]
    assert _model_call_phases(events) == ["planner", "coder", "verifier", "final"]
    assert any(event["event_type"] == "verifier_final" for event in events)


def test_planner_phase_blocks_edit_before_permission(tmp_path: Path):
    config_path = _write_planner_coder_verifier_config(
        tmp_path,
        replay_path=ROOT / "tests/fixtures/replays/task_001_planner_coder_verifier_planner_edit.yaml",
        max_turns=1,
    )

    run_dir = run_task(
        ROOT / "tests/fixtures/tasks/task_001.yaml",
        config_path=config_path,
        output_dir=tmp_path / "runs",
        run_id="planner-edit-blocked",
    )

    metrics = _read_json(run_dir / "metrics.json")
    events = _read_jsonl(run_dir / "events.jsonl")
    assert metrics["run_outcome"] == "failed"
    assert any(
        event["event_type"] == "tool_denied"
        and event["error_type"] == "tool_not_allowed_by_scaffold"
        and event["data"]["tool_name"] == "edit_file"
        for event in events
    )
    assert any(
        event["event_type"] == "tool_not_allowed"
        and event["data"]["scaffold_phase"] == "planner"
        and "edit_file" not in event["data"]["allowed_tools"]
        for event in events
    )
    assert not any(event["event_type"] == "permission_decision" for event in events)


def test_coder_phase_blocks_bash_pytest_after_normalization(tmp_path: Path):
    replay_path = tmp_path / "coder_bash_pytest.yaml"
    replay_path.write_text(
        """
script_id: coder_bash_pytest
task_id: task_001
steps:
  - step_id: planner_message
    action: final_answer
    assistant_text: "Plan: edit the calculator, then verify later."
  - step_id: coder_bash_pytest
    action: tool_call
    tool_call_id: call_coder_bash_pytest
    tool_name: bash
    arguments:
      command: "pytest -q"
""".lstrip(),
        encoding="utf-8",
    )
    config_path = _write_planner_coder_verifier_config(
        tmp_path,
        replay_path=replay_path,
        max_turns=2,
    )

    run_dir = run_task(
        ROOT / "tests/fixtures/tasks/task_001.yaml",
        config_path=config_path,
        output_dir=tmp_path / "runs",
        run_id="coder-bash-pytest-blocked",
    )

    metrics = _read_json(run_dir / "metrics.json")
    events = _read_jsonl(run_dir / "events.jsonl")
    assert metrics["interaction_efficiency"]["hidden_feedback_ran"] is False
    assert metrics["test_run_count"] == 0
    assert any(
        event["event_type"] == "tool_not_allowed"
        and event["data"]["scaffold_phase"] == "coder"
        and event["data"]["requested_tool_name"] == "bash"
        and event["data"]["effective_tool_name"] == "run_tests"
        for event in events
    )
    assert not any(
        event["event_type"] == "tool_completed"
        and event["data"].get("effective_tool_name") == "run_tests"
        for event in events
    )


def test_planner_coder_verifier_can_enter_repair_after_failed_feedback(tmp_path: Path):
    config_path = _write_planner_coder_verifier_config(
        tmp_path,
        replay_path=ROOT / "tests/fixtures/replays/task_002_planner_coder_verifier_repair.yaml",
        max_turns=8,
    )

    run_dir = run_task(
        ROOT / "tests/fixtures/tasks/task_002.yaml",
        config_path=config_path,
        output_dir=tmp_path / "runs",
        run_id="planner-coder-verifier-repair",
    )

    metrics = _read_json(run_dir / "metrics.json")
    events = _read_jsonl(run_dir / "events.jsonl")
    assert metrics["run_outcome"] == "success"
    assert metrics["interaction_efficiency"]["agent_stop_reason"] == "final_answer"
    assert metrics["test_run_count"] == 2
    assert _phase_pairs(events) == [
        ("planner", "coder"),
        ("coder", "verifier"),
        ("verifier", "repair"),
        ("repair", "verifier"),
        ("verifier", "final"),
    ]
    assert _model_call_phases(events) == [
        "planner",
        "coder",
        "verifier",
        "repair",
        "verifier",
        "final",
    ]
    assert any(
        event["event_type"] == "scaffold_phase_transition"
        and event["data"]["reason"] == "feedback_verifier_not_accepted"
        for event in events
    )
    assert any(event["event_type"] == "verifier_final" for event in events)


def _write_planner_coder_verifier_config(
    tmp_path: Path,
    *,
    replay_path: Path,
    max_turns: int,
) -> Path:
    config_path = tmp_path / "planner_coder_verifier.yaml"
    config_path.write_text(
        f"""
run_id_prefix: stage09
model:
  provider: replay
  model_id: replay-script-v0
  replay_script_path: {replay_path}
runtime:
  scaffold_id: planner_coder_verifier
  execution_mode: local_process
  permission_mode: auto
  max_turns: {max_turns}
  max_tool_calls: 20
  max_test_runs: 2
workspace:
  output_dir: {tmp_path / "runs"}
  keep_workspace: true
  default_command_timeout_sec: 60
""".lstrip(),
        encoding="utf-8",
    )
    return config_path


def _phase_pairs(events: list[dict]) -> list[tuple[str, str]]:
    return [
        (event["data"]["from_phase"], event["data"]["to_phase"])
        for event in events
        if event["event_type"] == "scaffold_phase_transition"
    ]


def _model_call_phases(events: list[dict]) -> list[str]:
    return [
        event["data"]["scaffold_phase"]
        for event in events
        if event["event_type"] == "model_call_started"
    ]


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
