import textwrap
from pathlib import Path

import pytest

from repo_harness.errors import ConfigError
from repo_harness.evaluation.runner import run_task


ROOT = Path(__file__).resolve().parents[2]


def test_docker_mode_is_rejected_without_local_process_fallback(tmp_path: Path):
    config_path = tmp_path / "docker_mode.yaml"
    run_root = tmp_path / "runs"
    config_path.write_text(
        textwrap.dedent(
            f"""
            run_id_prefix: stage14_docker
            model:
              provider: replay
              model_id: replay-script-v0
              replay_script_path: {ROOT / "tests/fixtures/replays/task_001_success.yaml"}
            runtime:
              scaffold_id: simple_react
              execution_mode: docker
              permission_mode: auto
            workspace:
              output_dir: {run_root}
              keep_workspace: true
              default_command_timeout_sec: 60
            """
        ).lstrip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="不会静默降级为 execution_mode=local_process"):
        run_task(
            ROOT / "tests/fixtures/tasks/task_001.yaml",
            config_path=config_path,
            output_dir=run_root,
            run_id="stage14-docker",
        )

    assert not (run_root / "stage14-docker").exists()
