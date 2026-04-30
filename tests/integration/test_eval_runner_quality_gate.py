import json
import shutil
from pathlib import Path

from repo_harness.cli.main import main
from repo_harness.evaluation.runner import run_batch, run_task
from repo_harness.trajectory import inspect_run


ROOT = Path(__file__).resolve().parents[2]


def test_invalid_baseline_blocks_agent_run(tmp_path: Path):
    run_dir = run_task(
        ROOT / "tests/fixtures/tasks/task_invalid.yaml",
        config_path=ROOT / "tests/fixtures/run_configs/replay_success.yaml",
        output_dir=tmp_path / "runs",
        run_id="stage11-invalid",
    )

    baseline = _read_json(run_dir / "baseline.json")
    metrics = _read_json(run_dir / "metrics.json")
    summary = (run_dir / "summary.md").read_text(encoding="utf-8")
    events = _read_jsonl(run_dir / "events.jsonl")

    assert baseline["status"] == "invalid"
    assert metrics["run_outcome"] == "invalid_task"
    assert metrics["final_verifier_status"] == "skipped"
    assert "resolved_verifier_plan: not_generated" in summary
    assert not (run_dir / "resolved_verifier_plan.json").exists()
    assert not (run_dir / "workspaces/agent_workspace").exists()
    assert not any(event["event_type"] == "model_call_started" for event in events)


def test_test_command_error_without_generated_file_policy_blocks_agent_run(tmp_path: Path):
    fixture_root = tmp_path / "fixtures"
    task_dir = fixture_root / "tasks"
    repo_dir = fixture_root / "repos" / "missing_helper_file"
    task_dir.mkdir(parents=True)
    shutil.copytree(ROOT / "tests/fixtures/repos/missing_helper_file", repo_dir)
    task_path = task_dir / "task_test_command_error.yaml"
    source = (ROOT / "tests/fixtures/tasks/task_003_create_file.yaml").read_text(encoding="utf-8")
    task_path.write_text(
        source.replace("id: task_003_create_file", "id: task_test_command_error")
        .replace(
            "task_version: task_003_create_file_v0",
            "task_version: task_test_command_error_v0",
        )
        .replace(
            """
generated_files:
  - path_pattern: app/helpers.py
    allowed_stage: agent_run
    include_in_final_patch: true
    reason: "The task requires adding the missing helper module."
    artifact_policy: record
""".lstrip(),
            "generated_files: []\n",
        ),
        encoding="utf-8",
    )

    run_dir = run_task(
        task_path,
        config_path=ROOT / "tests/fixtures/run_configs/replay_success.yaml",
        output_dir=tmp_path / "runs",
        run_id="stage11-test-command-error",
    )

    baseline = _read_json(run_dir / "baseline.json")
    metrics = _read_json(run_dir / "metrics.json")
    assert baseline["status"] == "invalid"
    assert baseline["dependency_error"] == "test_command_error"
    assert metrics["run_outcome"] == "invalid_task"
    assert not (run_dir / "workspaces/agent_workspace").exists()


def test_flaky_baseline_blocks_agent_run(tmp_path: Path):
    run_dir = run_task(
        ROOT / "tests/fixtures/tasks/task_flaky.yaml",
        config_path=ROOT / "tests/fixtures/run_configs/replay_success.yaml",
        output_dir=tmp_path / "runs",
        run_id="stage11-flaky",
    )

    baseline = _read_json(run_dir / "baseline.json")
    metrics = _read_json(run_dir / "metrics.json")
    summary = (run_dir / "summary.md").read_text(encoding="utf-8")

    assert baseline["status"] == "flaky"
    assert metrics["run_outcome"] == "flaky_task"
    assert metrics["final_verifier_status"] == "skipped"
    assert "quality_gate_reason: baseline_marked_flaky" in summary
    assert not (run_dir / "workspaces/agent_workspace").exists()


def test_final_verifier_failure_derives_failed_outcome(tmp_path: Path):
    run_dir = run_task(
        ROOT / "tests/fixtures/tasks/task_001.yaml",
        config_path=ROOT / "tests/fixtures/run_configs/replay_failure_minimal.yaml",
        output_dir=tmp_path / "runs",
        run_id="stage11-final-failed",
    )

    metrics = _read_json(run_dir / "metrics.json")
    summary = (run_dir / "summary.md").read_text(encoding="utf-8")
    assert metrics["final_verifier_status"] == "failed"
    assert metrics["run_outcome"] == "failed"
    assert "baseline_status: valid" in summary


def test_run_batch_writes_manifest_for_success_invalid_and_flaky(tmp_path: Path):
    manifest_path = run_batch(
        config_path=ROOT / "tests/fixtures/run_configs/batch_replay.yaml",
        output_dir=tmp_path / "batch",
    )

    manifest = _read_json(manifest_path)
    statuses = {record["task_id"]: record["status"] for record in manifest["runs"]}
    assert statuses == {
        "task_001": "success",
        "task_invalid": "invalid_task",
        "task_flaky": "flaky_task",
    }
    assert manifest["concurrency"] == 1
    for record in manifest["runs"]:
        text = inspect_run(record["run_dir"])
        assert "Run outcome:" in text
        assert "Key artifacts:" in text


def test_cli_end_to_end_commands(tmp_path: Path, capsys):
    assert main(["validate-task", str(ROOT / "tests/fixtures/tasks/task_001.yaml")]) == 0
    assert "任务校验通过：task_001" in capsys.readouterr().out

    run_id = "stage11-cli-success"
    assert (
        main(
            [
                "run-task",
                str(ROOT / "tests/fixtures/tasks/task_001.yaml"),
                "--config",
                str(ROOT / "tests/fixtures/run_configs/replay_success.yaml"),
                "--output-dir",
                str(tmp_path / "runs"),
                "--run-id",
                run_id,
            ]
        )
        == 0
    )
    run_dir = tmp_path / "runs" / run_id
    assert run_dir.exists()

    assert main(["inspect-run", str(run_dir)]) == 0
    inspect_output = capsys.readouterr().out
    assert "Task id: task_001" in inspect_output
    assert "Run outcome: success" in inspect_output
    assert "Final verifier status: accepted" in inspect_output


def test_cli_fail_on_invalid_task_returns_nonzero(tmp_path: Path):
    config_path = tmp_path / "fail_on_invalid.yaml"
    config_path.write_text(
        f"""
run_id_prefix: stage11
model:
  provider: replay
  model_id: replay-script-v0
  replay_script_path: {ROOT / "tests/fixtures/replays/task_001_success.yaml"}
runtime:
  scaffold_id: simple_react
  execution_mode: local_process
  permission_mode: auto
  max_turns: 8
  max_tool_calls: 20
  max_test_runs: 4
workspace:
  output_dir: {tmp_path / "runs"}
  keep_workspace: true
  default_command_timeout_sec: 60
evaluation:
  fail_on_invalid_task: true
""".lstrip(),
        encoding="utf-8",
    )

    assert (
        main(
            [
                "run-task",
                str(ROOT / "tests/fixtures/tasks/task_invalid.yaml"),
                "--config",
                str(config_path),
                "--output-dir",
                str(tmp_path / "runs"),
                "--run-id",
                "stage11-invalid-cli",
            ]
        )
        == 1
    )


def test_cli_run_batch_returns_nonzero_for_task_load_error(tmp_path: Path):
    config_path = tmp_path / "batch_error.yaml"
    config_path.write_text(
        f"""
run_id_prefix: stage11_batch_error
tasks:
  - {tmp_path / "missing_task.yaml"}
model:
  provider: replay
  model_id: replay-script-v0
  replay_script_path: {ROOT / "tests/fixtures/replays/task_001_success.yaml"}
runtime:
  scaffold_id: simple_react
  execution_mode: local_process
  permission_mode: auto
workspace:
  output_dir: {tmp_path / "batch"}
  keep_workspace: true
  default_command_timeout_sec: 60
evaluation:
  fail_on_invalid_task: false
""".lstrip(),
        encoding="utf-8",
    )

    assert main(["run-batch", "--config", str(config_path)]) == 1
    manifest = _read_json(tmp_path / "batch" / "batch_manifest.json")
    assert manifest["should_fail_command"] is True
    assert manifest["runs"][0]["status"] == "error"


def _read_json(path: Path | str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
