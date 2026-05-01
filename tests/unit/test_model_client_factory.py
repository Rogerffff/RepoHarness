from pathlib import Path

import pytest

from repo_harness.config import ModelConfig
from repo_harness.errors import ConfigError
from repo_harness.model_client import FakeModelClient, MockProviderClient, ReplayModelClient, create_model_client


def test_model_client_factory_constructs_replay(tmp_path: Path):
    replay_path = _write_replay(tmp_path)

    client = create_model_client(
        ModelConfig(provider="replay", model_id="replay-script-v0", replay_script_path=str(replay_path))
    )

    assert isinstance(client, ReplayModelClient)


def test_model_client_factory_constructs_fake(tmp_path: Path):
    replay_path = _write_replay(tmp_path)

    client = create_model_client(
        ModelConfig(provider="fake", model_id="fake-script-v0", replay_script_path=str(replay_path))
    )

    assert isinstance(client, FakeModelClient)


def test_model_client_factory_constructs_mock():
    client = create_model_client(ModelConfig(provider="mock", model_id="mock-v0"))

    assert isinstance(client, MockProviderClient)


def test_model_client_factory_rejects_unsupported_provider():
    with pytest.raises(ConfigError, match="replay、fake 或 mock"):
        create_model_client(ModelConfig(provider="deepseek", model_id="deepseek-v4-pro"))


def test_model_client_factory_requires_script_path_for_fake():
    with pytest.raises(ConfigError, match="model.replay_script_path"):
        create_model_client(ModelConfig(provider="fake", model_id="fake-script-v0"))


def _write_replay(tmp_path: Path) -> Path:
    replay_path = tmp_path / "replay.yaml"
    replay_path.write_text(
        """
script_id: replay
task_id: task
steps:
  - step_id: final
    action: final_answer
    assistant_text: done
""".lstrip(),
        encoding="utf-8",
    )
    return replay_path
