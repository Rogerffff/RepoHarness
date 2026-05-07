import json
from pathlib import Path

import pytest

from repo_harness.config import RunConfig
from repo_harness.evaluation.runner import run_task


ROOT = Path(__file__).resolve().parents[2]


def test_runtime_rejects_not_applicable_as_user_feedback_policy():
    with pytest.raises(ValueError):
        RunConfig.model_validate(
            {
                "runtime": {
                    "test_feedback_policy": "disabled",
                    "feedback_tests_passed_policy": "not_applicable",
                }
            }
        )


def test_test_feedback_disabled_hides_run_tests_and_blocks_direct_call(tmp_path: Path):
    replay_path = tmp_path / "direct_run_tests_disabled.yaml"
    replay_path.write_text(
        """
script_id: direct_run_tests_disabled
task_id: task_001
steps:
  - step_id: run_tests
    action: tool_call
    tool_call_id: call_run_tests
    tool_name: run_tests
    arguments: {}
  - step_id: final
    action: final_answer
    assistant_text: "Stopped without model-visible test feedback."
""".lstrip(),
        encoding="utf-8",
    )
    config_path = _write_config(tmp_path, replay_path=replay_path, test_feedback_policy="disabled")

    run_dir = run_task(
        ROOT / "tests/fixtures/tasks/task_001.yaml",
        config_path=config_path,
        output_dir=tmp_path / "runs",
        run_id="feedback-disabled-direct",
    )

    facts = _read_json(run_dir / "run_config_facts.json")
    events = _read_jsonl(run_dir / "events.jsonl")
    assert facts["test_feedback_policy"] == "disabled"
    assert facts["feedback_tests_passed_policy"] == "not_applicable"
    assert "run_tests" not in facts["tool_protocol"]["tool_order"]
    assert any(event["event_type"] == "tool_not_allowed" for event in events)
    assert not any(event["event_type"] == "verifier_final" and event["data"]["accepted"] for event in events)


def test_test_feedback_disabled_blocks_bash_pytest_bypass(tmp_path: Path):
    config_path = _write_config(
        tmp_path,
        replay_path=ROOT / "tests/fixtures/replays/task_001_bash_pytest.yaml",
        test_feedback_policy="disabled",
    )

    run_dir = run_task(
        ROOT / "tests/fixtures/tasks/task_001.yaml",
        config_path=config_path,
        output_dir=tmp_path / "runs",
        run_id="feedback-disabled-bash",
    )

    events = _read_jsonl(run_dir / "events.jsonl")
    metrics = _read_json(run_dir / "metrics.json")
    denied_bash_tests = [
        event
        for event in events
        if event["event_type"] == "tool_denied"
        and event["error_type"] == "permission_denied"
        and event["data"]["requested_tool_name"] == "bash"
    ]
    assert denied_bash_tests
    denied_typed = denied_bash_tests[0]["data"]["typed"]
    assert denied_typed["policy_decision"] == "deny"
    assert denied_typed["command_category"] == "public_test"
    assert denied_typed["reason_code"] == "denied_by_final_only_feedback_policy"
    assert denied_typed["safe_argv"] == ["pytest", "-q"]
    assert denied_typed["shell_execution"] is False
    assert any(
        event["event_type"] == "tool_denied"
        and event["error_type"] == "permission_denied"
        for event in events
    )
    assert metrics["interaction_efficiency"]["agent_stop_reason"] == "final_answer"
    assert metrics["interaction_efficiency"]["hidden_feedback_ran"] is False


def test_public_only_test_feedback_sanitizes_model_visible_result(tmp_path: Path):
    config_path = _write_config(tmp_path, test_feedback_policy="public_only")

    run_dir = run_task(
        ROOT / "tests/fixtures/tasks/task_001.yaml",
        config_path=config_path,
        output_dir=tmp_path / "runs",
        run_id="feedback-public-only",
    )

    facts = _read_json(run_dir / "run_config_facts.json")
    metrics = _read_json(run_dir / "metrics.json")
    feedback_artifact = _first_feedback_artifact(run_dir)
    transcript_text = (run_dir / "transcript.jsonl").read_text(encoding="utf-8")
    assert facts["test_feedback_policy"] == "public_only"
    assert facts["hidden_feedback_visible_to_model"] is False
    assert metrics["interaction_efficiency"]["public_tests_ran"] is True
    assert metrics["interaction_efficiency"]["hidden_feedback_ran"] is False
    assert feedback_artifact["fail_to_pass"] == {"passed": 0, "total": 0}
    assert feedback_artifact["pass_to_pass"] == {"passed": 0, "total": 0}
    assert feedback_artifact["test_cases"] == []
    assert "fail_to_pass" not in transcript_text
    assert "pass_to_pass" not in transcript_text


def test_structured_public_test_feedback_sanitizes_model_visible_result(tmp_path: Path):
    config_path = _write_config(tmp_path, test_feedback_policy="structured_public_feedback")

    run_dir = run_task(
        ROOT / "tests/fixtures/tasks/task_001.yaml",
        config_path=config_path,
        output_dir=tmp_path / "runs",
        run_id="feedback-structured-public",
    )

    transcript_text = (run_dir / "transcript.jsonl").read_text(encoding="utf-8")
    metrics = _read_json(run_dir / "metrics.json")
    feedback_artifact = _first_feedback_artifact(run_dir)
    assert "public_feedback" in transcript_text
    assert "fail_to_pass" not in transcript_text
    assert "pass_to_pass" not in transcript_text
    assert feedback_artifact["fail_to_pass"] == {"passed": 0, "total": 0}
    assert feedback_artifact["pass_to_pass"] == {"passed": 0, "total": 0}
    assert feedback_artifact["test_cases"] == []
    assert metrics["interaction_efficiency"]["public_tests_ran"] is True


def _write_config(
    tmp_path: Path,
    *,
    replay_path: Path | None = None,
    test_feedback_policy: str,
) -> Path:
    replay = replay_path or ROOT / "tests/fixtures/replays/task_001_success.yaml"
    config_path = tmp_path / f"{test_feedback_policy}.yaml"
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
  test_feedback_policy: {test_feedback_policy}
  feedback_tests_passed_policy: stop_immediately
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


def _first_feedback_artifact(run_dir: Path) -> dict:
    events = _read_jsonl(run_dir / "events.jsonl")
    for event in events:
        if event["event_type"] != "tool_completed":
            continue
        data = event["data"]
        if data.get("effective_tool_name") != "run_tests":
            continue
        ref = data["typed"]["verifier_result_ref"]
        return _read_json(run_dir / ref["relative_path"])
    raise AssertionError("feedback verifier artifact not found")
