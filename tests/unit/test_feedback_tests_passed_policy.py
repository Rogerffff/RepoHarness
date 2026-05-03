import json
from pathlib import Path

from repo_harness.evaluation.runner import run_task


ROOT = Path(__file__).resolve().parents[2]


def test_feedback_tests_passed_stop_immediately_preserves_replay_default(tmp_path: Path):
    run_dir = run_task(
        ROOT / "tests/fixtures/tasks/task_001.yaml",
        config_path=ROOT / "tests/fixtures/run_configs/replay_success_minimal.yaml",
        output_dir=tmp_path / "runs",
        run_id="policy-stop",
    )

    metrics = _read_json(run_dir / "metrics.json")
    facts = _read_json(run_dir / "run_config_facts.json")
    metadata = _read_json(run_dir / "run_metadata.json")
    assert metrics["interaction_efficiency"]["agent_stop_reason"] == "feedback_tests_passed"
    assert metrics["interaction_efficiency"]["feedback_tests_passed_policy"] == "stop_immediately"
    assert metrics["interaction_efficiency"]["feedback_verifier_accepted"] is True
    assert facts["test_feedback_policy"] == "oracle_hidden_feedback"
    assert facts["feedback_tests_passed_policy"] == "stop_immediately"
    assert metadata["scaffold_id"] == "simple_react"
    assert metadata["scaffold_version"] == "repo_harness_simple_react_v1"
    assert metadata["test_feedback_policy"] == "oracle_hidden_feedback"
    assert metadata["feedback_tests_passed_policy"] == "stop_immediately"
    assert metadata["feedback_policy_resolution"]["resolved_feedback_tests_passed_policy"] == "stop_immediately"
    assert (
        facts["feedback_policy_resolution"]["scaffold_default_feedback_tests_passed_policy"]
        == "stop_immediately"
    )


def test_feedback_tests_passed_require_model_final_consumes_replay_final_answer(tmp_path: Path):
    config_path = _write_config(
        tmp_path,
        feedback_tests_passed_policy="require_model_final",
    )

    run_dir = run_task(
        ROOT / "tests/fixtures/tasks/task_001.yaml",
        config_path=config_path,
        output_dir=tmp_path / "runs",
        run_id="policy-require-final",
    )

    metrics = _read_json(run_dir / "metrics.json")
    transcript = _read_jsonl(run_dir / "transcript.jsonl")
    assert metrics["interaction_efficiency"]["agent_stop_reason"] == "final_answer"
    assert metrics["interaction_efficiency"]["feedback_tests_passed_policy"] == "require_model_final"
    assert metrics["interaction_efficiency"]["feedback_verifier_accepted"] is True
    assert _read_json(run_dir / "run_config_facts.json")["feedback_policy_resolution"][
        "runtime_feedback_tests_passed_policy"
    ] == "require_model_final"
    assert any(
        record["role"] == "assistant"
        and "Implemented the divide-by-zero guard" in record["content_preview"]
        for record in transcript
    )


def test_feedback_tests_passed_continue_keeps_negative_final_verifier_sample(tmp_path: Path):
    replay_path = tmp_path / "regress_after_feedback.yaml"
    replay_path.write_text(
        """
script_id: regress_after_feedback
task_id: task_001
steps:
  - step_id: edit_good
    action: tool_call
    tool_call_id: call_edit_good
    tool_name: edit_file
    arguments:
      path: calculator.py
      old_text: "def divide(left: int, right: int) -> float:\\n    return left / right\\n"
      new_text: "def divide(left: int, right: int) -> float:\\n    if right == 0:\\n        raise ValueError(\\"division by zero\\")\\n    return left / right\\n"
  - step_id: run_tests
    action: tool_call
    tool_call_id: call_run_tests
    tool_name: run_tests
    arguments: {}
  - step_id: edit_bad
    action: tool_call
    tool_call_id: call_edit_bad
    tool_name: edit_file
    arguments:
      path: calculator.py
      old_text: "def divide(left: int, right: int) -> float:\\n    if right == 0:\\n        raise ValueError(\\"division by zero\\")\\n    return left / right\\n"
      new_text: "def divide(left: int, right: int) -> float:\\n    return left / right\\n"
  - step_id: final
    action: final_answer
    assistant_text: "Continuing after feedback caused a regression."
""".lstrip(),
        encoding="utf-8",
    )
    config_path = _write_config(
        tmp_path,
        replay_path=replay_path,
        feedback_tests_passed_policy="continue",
    )

    run_dir = run_task(
        ROOT / "tests/fixtures/tasks/task_001.yaml",
        config_path=config_path,
        output_dir=tmp_path / "runs",
        run_id="policy-continue-regression",
    )

    metrics = _read_json(run_dir / "metrics.json")
    assert metrics["interaction_efficiency"]["agent_stop_reason"] == "final_answer"
    assert metrics["interaction_efficiency"]["feedback_tests_passed_policy"] == "continue"
    assert metrics["interaction_efficiency"]["feedback_verifier_accepted"] is True
    assert metrics["final_verifier_status"] == "failed"
    assert metrics["run_outcome"] == "failed"


def _write_config(
    tmp_path: Path,
    *,
    replay_path: Path | None = None,
    feedback_tests_passed_policy: str,
) -> Path:
    replay = replay_path or ROOT / "tests/fixtures/replays/task_001_success.yaml"
    config_path = tmp_path / f"{feedback_tests_passed_policy}.yaml"
    config_path.write_text(
        f"""
run_id_prefix: stage07
model:
  provider: replay
  model_id: replay-script-v0
  replay_script_path: {replay}
runtime:
  scaffold_id: simple_react
  execution_mode: local_process
  permission_mode: auto
  test_feedback_policy: oracle_hidden_feedback
  feedback_tests_passed_policy: {feedback_tests_passed_policy}
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


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
