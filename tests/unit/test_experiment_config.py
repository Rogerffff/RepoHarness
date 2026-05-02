from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from repo_harness.evaluation.experiment import _run_config_payload, load_experiment_config
from repo_harness.evaluation.schemas import ExperimentConfig, ExperimentMinimums


ROOT = Path(__file__).resolve().parents[2]


def test_experiment_config_loads_smoke_fixture():
    config = load_experiment_config(ROOT / "tests/fixtures/run_configs/v2/experiment_smoke.yaml")

    assert config.experiment_id == "v2_exp_smoke"
    assert config.model_provider == "replay"
    assert config.scaffold_id == "simple_react"
    assert config.rollout_count == 2
    assert config.generate_preference_export is True


def test_experiment_config_accepts_v3_docker_backend_fixture():
    config = load_experiment_config(ROOT / "tests/fixtures/run_configs/v3/docker_experiment_smoke.yaml")
    payload = _run_config_payload(config, task_path=config.tasks[0])

    assert config.execution_mode == "docker"
    assert config.docker_backend.image_ref == "repo-harness-v3-python:stage2"
    assert config.docker_backend.requested_container_platform == "linux/arm64"
    assert config.swebench_like.effective_max_workers == 1
    assert config.swebench_like.max_workers_resolution == "experiment_runner_v3_stage1_serial_cap"
    assert payload["runtime"]["execution_mode"] == "docker"
    assert payload["runtime"]["docker_backend"]["requested_container_platform"] == "linux/arm64"
    assert payload["swebench_like"]["effective_max_workers"] == 1


def test_experiment_config_allows_fake_provider_after_model_client_factory():
    config = ExperimentConfig(
        experiment_id="fake_provider",
        tasks=["tests/fixtures/tasks/task_001.yaml"],
        rollout_count=1,
        model_provider="fake",
        replay_script_path="tests/fixtures/replays/task_001_success.yaml",
    )

    assert config.model_provider == "fake"


def test_experiment_config_allows_mock_provider_after_stage10():
    config = ExperimentConfig(
        experiment_id="mock_provider",
        tasks=["tests/fixtures/tasks/task_001.yaml"],
        rollout_count=1,
        model_provider="mock",
    )

    assert config.model_provider == "mock"


def test_experiment_config_allows_real_provider_after_stage11():
    config = ExperimentConfig(
        experiment_id="deepseek_provider",
        tasks=["tests/fixtures/tasks/task_001.yaml"],
        rollout_count=1,
        model_provider="deepseek",
        model_id="deepseek-v4-pro",
    )

    assert config.model_provider == "deepseek"


def test_experiment_config_rejects_stage11_out_of_scope_provider():
    with pytest.raises(ValidationError, match="replay、fake、mock 或 deepseek"):
        ExperimentConfig(
            experiment_id="bad_provider",
            tasks=["tests/fixtures/tasks/task_001.yaml"],
            rollout_count=1,
            model_provider="anthropic",
        )


def test_experiment_config_allows_single_shot_patch_after_scaffold_registry():
    config = ExperimentConfig(
        experiment_id="single_shot",
        tasks=["tests/fixtures/tasks/task_001.yaml"],
        rollout_count=1,
        scaffold_id="single_shot_patch",
    )

    assert config.scaffold_id == "single_shot_patch"


def test_experiment_config_allows_planner_coder_verifier_after_stage09():
    config = ExperimentConfig(
        experiment_id="planner_coder_verifier",
        tasks=["tests/fixtures/tasks/task_001.yaml"],
        rollout_count=1,
        scaffold_id="planner_coder_verifier",
    )

    assert config.scaffold_id == "planner_coder_verifier"


def test_experiment_config_rejects_stage09_unregistered_scaffold():
    with pytest.raises(ValidationError, match="planner_coder_verifier"):
        ExperimentConfig(
            experiment_id="bad_scaffold",
            tasks=["tests/fixtures/tasks/task_001.yaml"],
            rollout_count=1,
            scaffold_id="unknown_scaffold",
        )


def test_experiment_config_rejects_run_id_template_missing_required_dimensions():
    with pytest.raises(ValidationError, match="run_id_template"):
        ExperimentConfig(
            experiment_id="bad_template",
            tasks=["tests/fixtures/tasks/task_001.yaml"],
            rollout_count=1,
            run_id_template="{experiment_id}_{rollout_index:03d}",
        )


def test_experiment_minimums_loads_fixture():
    config = ExperimentMinimums.model_validate(
        {
            "min_total_runs": 2,
            "min_recorded_runs": 2,
            "require_experiment_manifest": True,
            "require_aggregate_metrics": True,
            "require_failure_records": True,
            "require_no_all_skipped_success": True,
        }
    )

    assert config.min_total_runs == 2
    assert config.require_failure_records is True
