import json
import shutil
import textwrap
from pathlib import Path

import pytest

from repo_harness.cli.main import main
from repo_harness.errors import ConfigError, TaskValidationError, WorkspaceError
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
    run_metadata = _read_json(run_dir / "run_metadata.json")
    summary = (run_dir / "summary.md").read_text(encoding="utf-8")
    events = _read_jsonl(run_dir / "events.jsonl")

    assert baseline["status"] == "invalid"
    assert metrics["run_outcome"] == "invalid_task"
    assert metrics["final_verifier_status"] == "skipped"
    assert run_metadata["run_status"] == "skipped"
    assert run_metadata["run_config_facts_ref"]["relative_path"] == "run_config_facts.json"
    assert run_metadata["export_readiness"]["training_export_ready"] is False
    assert "has_final_patch" in run_metadata["export_readiness"]["blocking_reasons"]
    assert "resolved_verifier_plan: not_generated" in summary
    assert not (run_dir / "resolved_verifier_plan.json").exists()
    assert not (run_dir / "workspaces/agent_workspace").exists()
    assert not any(event["event_type"] == "model_call_started" for event in events)


def test_docker_execution_mode_missing_image_fails_without_local_fallback(tmp_path: Path):
    config_path = tmp_path / "docker_mode.yaml"
    config_path.write_text(
        f"""
run_id_prefix: stage11_docker
model:
  provider: replay
  model_id: replay-script-v0
  replay_script_path: {ROOT / "tests/fixtures/replays/task_001_success.yaml"}
runtime:
  scaffold_id: simple_react
  execution_mode: docker
  permission_mode: auto
  docker_backend:
    image_ref: repo-harness-v3-missing:stage2
    build_if_missing: false
workspace:
  output_dir: {tmp_path / "runs"}
  keep_workspace: true
  default_command_timeout_sec: 60
""".lstrip(),
        encoding="utf-8",
    )

    with pytest.raises(WorkspaceError, match="build_if_missing=false|Docker backend requested"):
        run_task(
            ROOT / "tests/fixtures/tasks/task_001.yaml",
            config_path=config_path,
            output_dir=tmp_path / "runs",
            run_id="stage11-docker",
        )
    run_dir = tmp_path / "runs" / "stage11-docker"
    assert (run_dir / "docker_backend_status.json").exists()
    assert (run_dir / "docker_stage_status.json").exists()
    assert not (run_dir / "metrics.json").exists()


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
    assert baseline["baseline_rerun_count"] == 2
    assert baseline["dependency_error"] == "flaky_baseline_inconsistent"
    assert metrics["run_outcome"] == "flaky_task"
    assert metrics["final_verifier_status"] == "skipped"
    assert "quality_gate_reason: flaky_baseline_inconsistent" in summary
    assert not (run_dir / "workspaces/agent_workspace").exists()


def test_flaky_tag_alone_does_not_block_agent_run(tmp_path: Path):
    fixture_root = tmp_path / "fixtures"
    task_dir = fixture_root / "tasks"
    repo_dir = fixture_root / "repos" / "tagged_but_stable"
    task_dir.mkdir(parents=True)
    shutil.copytree(ROOT / "tests/fixtures/repos/buggy_calculator", repo_dir)
    task_path = task_dir / "task_tagged_but_stable.yaml"
    source = (ROOT / "tests/fixtures/tasks/task_001.yaml").read_text(encoding="utf-8")
    task_path.write_text(
        source.replace("id: task_001", "id: task_tagged_but_stable")
        .replace("task_version: task_001_v0", "task_version: task_tagged_but_stable_v0")
        .replace("repo: ../repos/buggy_calculator", "repo: ../repos/tagged_but_stable")
        .replace("  - calculator\n", "  - calculator\n  - flaky-task\n"),
        encoding="utf-8",
    )

    run_dir = run_task(
        task_path,
        config_path=ROOT / "tests/fixtures/run_configs/replay_success.yaml",
        output_dir=tmp_path / "runs",
        run_id="stage11-flaky-tag-stable",
    )

    baseline = _read_json(run_dir / "baseline.json")
    metrics = _read_json(run_dir / "metrics.json")
    assert baseline["status"] == "valid"
    assert baseline["baseline_rerun_count"] == 2
    assert metrics["run_outcome"] == "success"
    assert (run_dir / "resolved_verifier_plan.json").exists()


def test_keep_workspace_false_cleans_success_and_quality_gate_workspaces(tmp_path: Path):
    success_config = _write_replay_config(
        tmp_path,
        replay_path=ROOT / "tests/fixtures/replays/task_003_create_file_success.yaml",
        output_dir=tmp_path / "runs",
        run_id_prefix="stage11_keep_false_success",
        keep_workspace=False,
    )
    success_run = run_task(
        ROOT / "tests/fixtures/tasks/task_003_create_file.yaml",
        config_path=success_config,
        output_dir=tmp_path / "runs",
        run_id="stage11-keep-false-success",
    )

    invalid_config = _write_replay_config(
        tmp_path,
        replay_path=ROOT / "tests/fixtures/replays/task_001_success.yaml",
        output_dir=tmp_path / "runs",
        run_id_prefix="stage11_keep_false_invalid",
        keep_workspace=False,
    )
    invalid_run = run_task(
        ROOT / "tests/fixtures/tasks/task_invalid.yaml",
        config_path=invalid_config,
        output_dir=tmp_path / "runs",
        run_id="stage11-keep-false-invalid",
    )

    assert (success_run / "final.patch").exists()
    assert (success_run / "final.diff").exists()
    assert not (success_run / "workspaces").exists()
    assert _read_json(invalid_run / "metrics.json")["run_outcome"] == "invalid_task"
    assert not (invalid_run / "workspaces").exists()


def test_injected_test_command_is_rejected_by_static_task_validation(tmp_path: Path):
    fixture_root = tmp_path / "fixtures"
    task_dir = fixture_root / "tasks"
    repo_dir = fixture_root / "repos" / "injected_test_command"
    task_dir.mkdir(parents=True)
    shutil.copytree(ROOT / "tests/fixtures/repos/buggy_calculator", repo_dir)
    task_path = task_dir / "task_injected_test_command.yaml"
    source = (ROOT / "tests/fixtures/tasks/task_001.yaml").read_text(encoding="utf-8")
    task_path.write_text(
        source.replace("id: task_001", "id: task_injected_test_command")
        .replace("task_version: task_001_v0", "task_version: task_injected_test_command_v0")
        .replace("repo: ../repos/buggy_calculator", "repo: ../repos/injected_test_command")
        .replace('test_command: "pytest -q"', 'test_command: "pytest -q; printf RH_TEST_COMMAND_INJECTION"'),
        encoding="utf-8",
    )

    with pytest.raises(TaskValidationError, match="test_command"):
        run_task(
            task_path,
            config_path=ROOT / "tests/fixtures/run_configs/replay_success.yaml",
            output_dir=tmp_path / "runs",
            run_id="stage11-injected-test-command",
        )

    assert not (tmp_path / "runs" / "stage11-injected-test-command").exists()


def test_task_timeout_before_final_verifier_skips_strict_replay(tmp_path: Path):
    fixture_root = tmp_path / "fixtures"
    task_dir = fixture_root / "tasks"
    repo_dir = fixture_root / "repos" / "slow_valid_baseline"
    task_dir.mkdir(parents=True)
    shutil.copytree(ROOT / "tests/fixtures/repos/buggy_calculator", repo_dir)
    shutil.rmtree(repo_dir / "tests")
    (repo_dir / "tests").mkdir()
    (repo_dir / "tests/test_sleep.py").write_text(
        "import time\n\n\ndef test_slow_pass():\n    time.sleep(0.6)\n    assert True\n",
        encoding="utf-8",
    )
    task_path = task_dir / "task_slow_valid_baseline.yaml"
    task_path.write_text(
        textwrap.dedent(
            """
            id: task_slow_valid_baseline
            task_version: task_slow_valid_baseline_v0
            dataset_name: repo_harness_micro
            source_kind: micro_repo_fixture
            dataset_split: dev
            created_at: "2026-04-30"
            repo: ../repos/slow_valid_baseline
            base_commit: fixture
            issue: "Exercise final verifier budget cutoff."
            setup_command: null
            test_command: "pytest -q"
            timeouts:
              setup_timeout_sec: 60
              test_timeout_sec: 30
              agent_timeout_sec: 120
              final_verifier_timeout_sec: 60
            environment:
              execution_image: "python:3.12-slim"
              python_version: "3.12"
              node_version: null
              package_manager: pip
              lockfile_hashes: []
              setup_cache_key_inputs:
                - pyproject.toml
              required_system_packages: []
              setup_network_policy: deny
            expected_files: []
            fail_to_pass_tests: []
            pass_to_pass_tests: []
            visibility:
              issue: model_visible
              expected_files: model_visible
              fail_to_pass_tests: verifier_only
              pass_to_pass_tests: verifier_only
              gold_patch: hidden_reference
            decontamination:
              status: manual_checked
              known_public_solution: false
              source_url: null
              overlap_check_notes: "hand-written fixture"
              notes: null
            declared_setup_mutations: []
            generated_files: []
            tags:
              - python
              - timeout
            """
        ).lstrip(),
        encoding="utf-8",
    )
    replay_path = tmp_path / "list_then_final.yaml"
    replay_path.write_text(
        """
script_id: list_then_final
task_id: task_slow_valid_baseline
steps:
  - step_id: list
    action: tool_call
    tool_call_id: call_list
    tool_name: list_files
    arguments:
      root: "."
      pattern: "*.py"
  - step_id: final
    action: final_answer
    assistant_text: "No changes required."
""".lstrip(),
        encoding="utf-8",
    )
    config_path = _write_replay_config(
        tmp_path,
        replay_path=replay_path,
        output_dir=tmp_path / "runs",
        run_id_prefix="stage11_final_timeout",
        task_timeout_sec=1,
    )

    run_dir = run_task(
        task_path,
        config_path=config_path,
        output_dir=tmp_path / "runs",
        run_id="stage11-final-timeout",
    )

    metrics = _read_json(run_dir / "metrics.json")
    verifier = _read_json(run_dir / "verifier.json")
    events = _read_jsonl(run_dir / "events.jsonl")
    event_types = [event["event_type"] for event in events]
    assert metrics["final_verifier_status"] == "timeout"
    assert metrics["run_outcome"] == "inconclusive"
    assert verifier["timeout"] is True
    assert verifier["verifier_stage"] == "final"
    assert event_types.index("budget_exhausted") < event_types.index("verifier_final")
    assert "model_call_started" not in event_types
    assert "tool_completed" not in event_types
    assert any(
        event["event_type"] == "budget_exhausted"
        and event["data"].get("phase") == "before_final_verifier"
        for event in events
    )


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


def test_strict_patch_replay_failure_derives_inconclusive_outcome(tmp_path: Path):
    fixture_root = tmp_path / "fixtures"
    task_dir = fixture_root / "tasks"
    repo_dir = fixture_root / "repos" / "buggy_calculator_patch_replay"
    task_dir.mkdir(parents=True)
    shutil.copytree(ROOT / "tests/fixtures/repos/buggy_calculator", repo_dir)
    (repo_dir / "setup_mutation.py").write_text(
        textwrap.dedent(
            """
            from pathlib import Path

            p = Path("calculator.py")
            text = p.read_text()
            marker = Path.cwd().name
            p.write_text(text.replace(
                "    return left / right\\n",
                f"    return left / right  # {marker}\\n",
            ))
            """
        ).lstrip(),
        encoding="utf-8",
    )
    task_path = task_dir / "task_patch_replay_failure.yaml"
    task_path.write_text(
        textwrap.dedent(
            """
            id: task_patch_replay_failure
            task_version: task_patch_replay_failure_v0
            dataset_name: repo_harness_micro
            source_kind: micro_repo_fixture
            dataset_split: dev
            created_at: "2026-04-30"
            repo: ../repos/buggy_calculator_patch_replay
            base_commit: fixture
            issue: "Update calculator.divide so division by zero raises ValueError with a clear message."
            setup_command: "python setup_mutation.py"
            test_command: "pytest -q"
            timeouts:
              setup_timeout_sec: 60
              test_timeout_sec: 30
              agent_timeout_sec: 120
              final_verifier_timeout_sec: 60
            environment:
              execution_image: "python:3.12-slim"
              python_version: "3.12"
              node_version: null
              package_manager: pip
              lockfile_hashes: []
              setup_cache_key_inputs:
                - pyproject.toml
              required_system_packages: []
              setup_network_policy: deny
            expected_files:
              - calculator.py
            fail_to_pass_tests:
              - tests/test_calculator.py::test_divide_zero
            pass_to_pass_tests:
              - tests/test_calculator.py::test_add
              - tests/test_calculator.py::test_divide_regular_numbers
            visibility:
              issue: model_visible
              expected_files: model_visible
              fail_to_pass_tests: verifier_only
              pass_to_pass_tests: verifier_only
              gold_patch: hidden_reference
            decontamination:
              status: manual_checked
              known_public_solution: false
              source_url: null
              overlap_check_notes: "hand-written fixture"
              notes: null
            declared_setup_mutations:
              - path_pattern: calculator.py
                allowed_stage: setup
                include_in_final_patch: false
                reason: "Integration test creates workspace-specific setup state."
                artifact_policy: record
            generated_files: []
            tags:
              - python
              - patch-replay-failure
            """
        ).lstrip(),
        encoding="utf-8",
    )
    replay_path = tmp_path / "patch_replay_failure_replay.yaml"
    replay_path.write_text(
        textwrap.dedent(
            """
            script_id: patch_replay_failure
            task_id: task_patch_replay_failure
            steps:
              - step_id: edit_divide
                action: tool_call
                tool_call_id: call_edit_divide
                tool_name: edit_file
                arguments:
                  path: calculator.py
                  old_text: "def divide(left: int, right: int) -> float:\\n    return left / right  # agent_workspace\\n"
                  new_text: "def divide(left: int, right: int) -> float:\\n    if right == 0:\\n        raise ValueError(\\"division by zero\\")\\n    return left / right\\n"
              - step_id: final
                action: final_answer
                assistant_text: "This replay intentionally creates a patch that fails strict replay."
            metadata:
              fixture_kind: patch_replay_failure
            """
        ).lstrip(),
        encoding="utf-8",
    )
    config_path = _write_replay_config(
        tmp_path,
        replay_path=replay_path,
        output_dir=tmp_path / "runs",
        run_id_prefix="stage13",
    )

    run_dir = run_task(
        task_path,
        config_path=config_path,
        output_dir=tmp_path / "runs",
        run_id="stage13-patch-replay-failure",
    )

    verifier = _read_json(run_dir / "verifier.json")
    reward = _read_json(run_dir / "reward.json")
    metrics = _read_json(run_dir / "metrics.json")
    assert verifier["error_type"] == "patch_apply_failed"
    assert verifier["verifier_stage"] == "final"
    assert metrics["final_verifier_status"] == "error"
    assert metrics["run_outcome"] == "inconclusive"
    assert reward["invalid_for_training"] is True
    assert reward["invalid_reason"] == "patch_apply_failed"


def test_low_parser_confidence_blocks_agent_run(tmp_path: Path):
    fixture_root = tmp_path / "fixtures"
    task_dir = fixture_root / "tasks"
    repo_dir = fixture_root / "repos" / "buggy_calculator_low_parser"
    task_dir.mkdir(parents=True)
    shutil.copytree(ROOT / "tests/fixtures/repos/buggy_calculator", repo_dir)
    shutil.rmtree(repo_dir / "tests")
    (repo_dir / "tests").mkdir()
    task_path = task_dir / "task_low_parser_confidence.yaml"
    task_path.write_text(
        textwrap.dedent(
            """
            id: task_low_parser_confidence
            task_version: task_low_parser_confidence_v0
            dataset_name: repo_harness_micro
            source_kind: micro_repo_fixture
            dataset_split: dev
            created_at: "2026-04-30"
            repo: ../repos/buggy_calculator_low_parser
            base_commit: fixture
            issue: "Exercise the baseline quality gate for a low-confidence verifier parse."
            setup_command: null
            test_command: "pytest -q"
            timeouts:
              setup_timeout_sec: 60
              test_timeout_sec: 30
              agent_timeout_sec: 120
              final_verifier_timeout_sec: 60
            environment:
              execution_image: "python:3.12-slim"
              python_version: "3.12"
              node_version: null
              package_manager: pip
              lockfile_hashes: []
              setup_cache_key_inputs:
                - pyproject.toml
              required_system_packages: []
              setup_network_policy: deny
            expected_files:
              - calculator.py
            fail_to_pass_tests: []
            pass_to_pass_tests: []
            visibility:
              issue: model_visible
              expected_files: model_visible
              fail_to_pass_tests: verifier_only
              pass_to_pass_tests: verifier_only
              gold_patch: hidden_reference
            decontamination:
              status: manual_checked
              known_public_solution: false
              source_url: null
              overlap_check_notes: "hand-written fixture"
              notes: null
            declared_setup_mutations: []
            generated_files: []
            tags:
              - python
              - low-parser-confidence
            """
        ).lstrip(),
        encoding="utf-8",
    )
    config_path = _write_replay_config(
        tmp_path,
        replay_path=ROOT / "tests/fixtures/replays/task_001_success.yaml",
        output_dir=tmp_path / "runs",
        run_id_prefix="stage13",
    )

    run_dir = run_task(
        task_path,
        config_path=config_path,
        output_dir=tmp_path / "runs",
        run_id="stage13-low-parser",
    )

    baseline = _read_json(run_dir / "baseline.json")
    metrics = _read_json(run_dir / "metrics.json")
    summary = (run_dir / "summary.md").read_text(encoding="utf-8")
    assert baseline["status"] == "invalid"
    assert baseline["parser_confidence"] < 0.5
    assert baseline["dependency_error"] == "low_parser_confidence"
    assert metrics["run_outcome"] == "invalid_task"
    assert "quality_gate_reason: low_parser_confidence" in summary
    assert not (run_dir / "workspaces/agent_workspace").exists()


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


def _write_replay_config(
    tmp_path: Path,
    *,
    replay_path: Path,
    output_dir: Path,
    run_id_prefix: str,
    keep_workspace: bool = True,
    task_timeout_sec: int = 900,
) -> Path:
    config_path = tmp_path / f"{run_id_prefix}_replay.yaml"
    config_path.write_text(
        textwrap.dedent(
            f"""
            run_id_prefix: {run_id_prefix}
            model:
              provider: replay
              model_id: replay-script-v0
              replay_script_path: {replay_path}
            runtime:
              scaffold_id: simple_react
              execution_mode: local_process
              permission_mode: auto
              max_turns: 8
              max_tool_calls: 20
              max_test_runs: 4
              task_timeout_sec: {task_timeout_sec}
            workspace:
              output_dir: {output_dir}
              keep_workspace: {str(keep_workspace).lower()}
              default_command_timeout_sec: 60
            evaluation:
              fail_on_invalid_task: false
            """
        ).lstrip(),
        encoding="utf-8",
    )
    return config_path
