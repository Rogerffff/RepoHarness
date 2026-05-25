from __future__ import annotations

import json
from pathlib import Path

import pytest

from repo_harness.errors import ConfigError
from repo_harness.evaluation.episode_runner import run_episode_task


def test_stage16f3_fake_provider_maps_to_mock_diagnostic_route(tmp_path: Path) -> None:
    run_dir = run_episode_task(
        "tests/fixtures/tasks/task_001.yaml",
        config_path="tests/fixtures/run_configs/stage16f3_run_episode_task_fake.yaml",
        output_dir=tmp_path / "runs",
        run_id="stage16f3_fake_maps_mock",
        assert_projection_complete=True,
    )

    route_report = json.loads(
        (run_dir / "compat_projection" / "provider_route_qualification.json").read_text(encoding="utf-8")
    )
    assert route_report["provider_route"] == "mock"
    assert route_report["formal_online_rl_eligible"] is False
    assert route_report["policy_loss_candidate"] is False


def test_stage16f3_explicit_route_must_match_run_config_provider(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="gateway_route_mismatch_with_run_config_provider"):
        run_episode_task(
            "tests/fixtures/tasks/task_001.yaml",
            config_path="tests/fixtures/run_configs/replay_success_minimal.yaml",
            output_dir=tmp_path / "runs",
            run_id="stage16f3_route_mismatch",
            gateway_route="mock",
            assert_projection_complete=True,
        )


def test_stage16f3_unsupported_gateway_route_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="只支持 mock、replay、openai、deepseek"):
        run_episode_task(
            "tests/fixtures/tasks/task_001.yaml",
            config_path="tests/fixtures/run_configs/stage16f3_run_episode_task_mock.yaml",
            output_dir=tmp_path / "runs",
            run_id="stage16f3_bad_route",
            gateway_route="local_vllm",
            assert_projection_complete=True,
        )
