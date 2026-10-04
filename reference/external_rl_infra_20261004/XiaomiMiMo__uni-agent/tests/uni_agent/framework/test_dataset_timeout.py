from uni_agent.framework.framework import _RunnerConfig, _session_timeout_for_sample


def test_runner_config_parses_request_idle_timeout():
    config = _RunnerConfig.from_config(
        "runner",
        {
            "runner_fqn": "runner",
            "dispatch_mode": "ray_task",
            "max_concurrent_sessions": 1,
            "agent_request_idle_timeout_seconds": 720,
        },
    )

    assert config.agent_request_idle_timeout_seconds == 720.0


def test_dataset_timeout_overrides_global_session_timeout():
    config = _RunnerConfig(
        runner_fqn="runner",
        runner_kwargs={},
        dispatch_mode="ray_task",
        max_concurrent_sessions=1,
        session_timeout_seconds=3600,
        trajectory_timeout_by_dataset={"swebench": 3600, "swebench-pro": 5400},
    )

    assert _session_timeout_for_sample(config, {"extra_info": {"dataset_type": "swebench"}}) == 3600
    assert _session_timeout_for_sample(config, {"extra_info": {"dataset_type": "swebench-pro"}}) == 5400
    assert _session_timeout_for_sample(config, {"extra_info": {"dataset_type": "deepswe"}}) == 3600
