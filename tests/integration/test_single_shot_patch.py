import json
from pathlib import Path

import pytest

from repo_harness.evaluation.runner import run_task
from repo_harness.errors import ConfigError


ROOT = Path(__file__).resolve().parents[2]


def test_single_shot_patch_replay_can_fix_fixture_task(tmp_path: Path):
    run_dir = run_task(
        ROOT / "tests/fixtures/tasks/task_001.yaml",
        config_path=ROOT / "tests/fixtures/run_configs/v2/single_shot_patch_success.yaml",
        output_dir=tmp_path / "runs",
        run_id="single-shot-success",
    )

    facts = _read_json(run_dir / "run_config_facts.json")
    metadata = _read_json(run_dir / "run_metadata.json")
    metrics = _read_json(run_dir / "metrics.json")
    events = _read_jsonl(run_dir / "events.jsonl")

    assert facts["scaffold_id"] == "single_shot_patch"
    assert facts["test_feedback_policy"] == "disabled"
    assert facts["feedback_tests_passed_policy"] == "not_applicable"
    assert facts["tool_protocol"]["tool_order"] == []
    assert metadata["scaffold_id"] == "single_shot_patch"
    assert metrics["test_run_count"] == 0
    assert metrics["run_outcome"] == "success"
    assert any(event["event_type"] == "patch_action_parsed" for event in events)
    assert any(event["event_type"] == "patch_apply_completed" for event in events)
    assert not any(
        event["event_type"] == "tool_completed"
        and event["data"].get("effective_tool_name") == "run_tests"
        for event in events
    )


def test_single_shot_patch_apply_failure_is_structured(tmp_path: Path):
    config_path = _write_single_shot_config(
        tmp_path,
        replay_path=ROOT / "tests/fixtures/replays/task_001_single_shot_patch_bad_patch.yaml",
    )

    run_dir = run_task(
        ROOT / "tests/fixtures/tasks/task_001.yaml",
        config_path=config_path,
        output_dir=tmp_path / "runs",
        run_id="single-shot-bad-patch",
    )

    metrics = _read_json(run_dir / "metrics.json")
    events = _read_jsonl(run_dir / "events.jsonl")
    assert metrics["interaction_efficiency"]["agent_stop_reason"] == "model_error"
    assert metrics["run_outcome"] == "failed"
    assert any(event["event_type"] == "patch_apply_failed" for event in events)
    assert any(event["event_type"] == "verifier_final" for event in events)


def test_single_shot_patch_parse_failure_is_structured(tmp_path: Path):
    config_path = _write_single_shot_config(
        tmp_path,
        replay_path=ROOT / "tests/fixtures/replays/task_001_single_shot_patch_malformed.yaml",
    )

    run_dir = run_task(
        ROOT / "tests/fixtures/tasks/task_001.yaml",
        config_path=config_path,
        output_dir=tmp_path / "runs",
        run_id="single-shot-malformed-patch",
    )

    metrics = _read_json(run_dir / "metrics.json")
    events = _read_jsonl(run_dir / "events.jsonl")
    assert metrics["interaction_efficiency"]["agent_stop_reason"] == "model_error"
    assert metrics["run_outcome"] == "failed"
    assert any(
        event["event_type"] == "patch_action_parse_failed"
        and event["error_type"] == "missing_unified_diff"
        for event in events
    )
    assert not any(event["event_type"] == "patch_apply_started" for event in events)
    assert any(event["event_type"] == "verifier_final" for event in events)


def test_single_shot_patch_blocks_run_tests_tool_call(tmp_path: Path):
    config_path = _write_single_shot_config(
        tmp_path,
        replay_path=ROOT / "tests/fixtures/replays/task_001_single_shot_patch_run_tests.yaml",
    )

    run_dir = run_task(
        ROOT / "tests/fixtures/tasks/task_001.yaml",
        config_path=config_path,
        output_dir=tmp_path / "runs",
        run_id="single-shot-run-tests-blocked",
    )

    metrics = _read_json(run_dir / "metrics.json")
    events = _read_jsonl(run_dir / "events.jsonl")
    assert metrics["test_run_count"] == 0
    assert metrics["interaction_efficiency"]["agent_stop_reason"] == "model_error"
    assert any(
        event["event_type"] == "tool_denied"
        and event["error_type"] == "tool_not_allowed_by_scaffold"
        for event in events
    )
    assert not any(
        event["event_type"] == "permission_decision"
        for event in events
    )


def test_single_shot_patch_rejects_oracle_feedback_override(tmp_path: Path):
    config_path = _write_single_shot_config(
        tmp_path,
        replay_path=ROOT / "tests/fixtures/replays/task_001_single_shot_patch_success.yaml",
        extra_runtime="  test_feedback_policy: oracle_hidden_feedback\n",
    )

    with pytest.raises(ConfigError, match="single_shot_patch scaffold requires"):
        run_task(
            ROOT / "tests/fixtures/tasks/task_001.yaml",
            config_path=config_path,
            output_dir=tmp_path / "runs",
            run_id="single-shot-invalid-policy",
        )


def _write_single_shot_config(
    tmp_path: Path,
    *,
    replay_path: Path,
    extra_runtime: str = "",
) -> Path:
    config_path = tmp_path / "single_shot.yaml"
    config_path.write_text(
        f"""
run_id_prefix: stage08
model:
  provider: replay
  model_id: replay-script-v0
  replay_script_path: {replay_path}
runtime:
  scaffold_id: single_shot_patch
  execution_mode: local_process
  permission_mode: auto
{extra_runtime}  max_turns: 1
  max_tool_calls: 0
  max_test_runs: 0
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
