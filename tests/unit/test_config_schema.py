from pathlib import Path

import pytest

from repo_harness.config import RunConfig, load_run_config
from repo_harness.errors import ConfigError
from repo_harness.schema_versions import TOKEN_ESTIMATOR_VERSION


def test_load_run_config_defaults(tmp_path: Path):
    config_path = tmp_path / "run.yaml"
    config_path.write_text(
        """
run_id_prefix: local_eval
tasks:
  - tests/fixtures/tasks/task_001.yaml
model:
  provider: replay
  model_id: replay-success
runtime:
  permission_mode: auto
""",
        encoding="utf-8",
    )

    config = load_run_config(config_path)

    assert config.tasks == ["tests/fixtures/tasks/task_001.yaml"]
    assert config.model.provider == "replay"
    assert config.context_management.token_estimator == TOKEN_ESTIMATOR_VERSION
    assert config.evaluation.final_verifier_mode == "strict_patch_replay"
    assert config.workspace.max_artifact_bytes is None


def test_batch_config_rejects_ask_permission_mode(tmp_path: Path):
    config_path = tmp_path / "run.yaml"
    config_path.write_text(
        """
runtime:
  permission_mode: ask
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="permission_mode=ask"):
        load_run_config(config_path, for_batch=True)


def test_run_config_rejects_unknown_fields():
    with pytest.raises(ValueError):
        RunConfig.model_validate({"runtime": {"permission_mode": "auto", "surprise": True}})


def test_output_dir_override_keeps_other_config():
    config = RunConfig.model_validate({"workspace": {"output_dir": "runs/original"}})

    updated = config.with_output_dir("runs/override")

    assert config.workspace.output_dir == "runs/original"
    assert updated.workspace.output_dir == "runs/override"


def test_run_config_accepts_v3_docker_backend_and_resolves_workers():
    config = RunConfig.model_validate(
        {
            "runtime": {
                "execution_mode": "docker",
                "docker_backend": {
                    "requested_container_platform": "linux/amd64",
                    "network_policy": "deny_agent_run",
                },
            },
            "evaluation": {"concurrency": 2},
            "swebench_like": {"max_workers": 4},
        }
    )

    assert config.runtime.execution_mode == "docker"
    assert config.runtime.docker_backend.requested_container_platform == "linux/amd64"
    assert config.swebench_like.effective_max_workers == 2
    assert config.swebench_like.max_workers_resolution == (
        "min_swebench_like_max_workers_and_evaluation_concurrency"
    )


def test_run_config_defaults_swebench_workers_to_evaluation_concurrency():
    config = RunConfig.model_validate({"evaluation": {"concurrency": 3}})

    assert config.swebench_like.effective_max_workers == 3
    assert config.swebench_like.max_workers_resolution == "unset_uses_evaluation_concurrency"
