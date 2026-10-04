import pytest

from uni_agent.framework.framework import _runner_task_num_cpus


def test_runner_task_num_cpus_defaults_to_one(monkeypatch):
    monkeypatch.delenv("UNI_AGENT_RUNNER_TASK_NUM_CPUS", raising=False)
    assert _runner_task_num_cpus() == 1.0


def test_runner_task_num_cpus_accepts_fraction(monkeypatch):
    monkeypatch.setenv("UNI_AGENT_RUNNER_TASK_NUM_CPUS", "0.5")
    assert _runner_task_num_cpus() == 0.5


@pytest.mark.parametrize("value", ["", "0", "-0.5", "nan", "inf", "not-a-number"])
def test_runner_task_num_cpus_rejects_invalid_values(monkeypatch, value):
    monkeypatch.setenv("UNI_AGENT_RUNNER_TASK_NUM_CPUS", value)
    with pytest.raises(ValueError, match="UNI_AGENT_RUNNER_TASK_NUM_CPUS"):
        _runner_task_num_cpus()
