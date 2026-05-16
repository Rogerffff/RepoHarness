from pathlib import Path

import pytest

from repo_harness.errors import ConfigError
from repo_harness.evaluation.runner import run_task


def test_run_task_does_not_reject_openai_primary_before_other_config_checks(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "openai_primary.yaml"
    config_path.write_text(
        """
model:
  provider: openai
  model_id: gpt-5.5
runtime:
  execution_mode: docker
evaluation:
  final_verifier_mode: unsupported_mode_for_gate_test
""".lstrip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="strict_patch_replay") as exc_info:
        run_task(
            tmp_path / "missing_task.yaml",
            config_path=config_path,
            output_dir=tmp_path / "runs",
            run_id="openai_primary_gate_test",
        )

    assert "fallback smoke" not in str(exc_info.value)
