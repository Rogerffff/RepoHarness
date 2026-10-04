import asyncio

import pytest

from uni_agent.framework.framework import (
    AgentRequestTimeout,
    OpenAICompatibleAgentFramework,
    _framework_failure_metadata,
)


class _StateManager:
    def __init__(self, state: dict[str, object]):
        self.state = state
        self.calls = 0

    async def get_session_state(self, session_id: str) -> dict[str, object]:
        self.calls += 1
        return dict(self.state)


def _framework(state: dict[str, object]) -> OpenAICompatibleAgentFramework:
    framework = object.__new__(OpenAICompatibleAgentFramework)
    framework.gateway_manager = _StateManager(state)
    framework._RUNNER_ACTIVITY_POLL_SECONDS = 0.001
    return framework


@pytest.mark.asyncio
async def test_request_idle_watchdog_raises_distinct_timeout():
    framework = _framework(
        {
            "in_flight_requests": 0,
            "awaiting_external_followup": True,
            "awaiting_external_followup_seconds": 12.0,
            "pending_tool_call_ids": ["call-1"],
        }
    )
    runner = asyncio.get_running_loop().create_future()

    with pytest.raises(AgentRequestTimeout) as exc_info:
        await framework._wait_for_runner_task(
            runner,
            session_id="session-1",
            session_timeout_seconds=1.0,
            request_idle_timeout_seconds=10.0,
        )

    metadata = _framework_failure_metadata(exc_info.value)
    assert metadata["status"] == "timeout"
    assert metadata["termination_kind"] == "agent_request_timeout"
    assert metadata["agent_status"] == "agent_timeout"
    assert metadata["pending_tool_call_ids"] == ["call-1"]
    assert metadata["idle_seconds"] == 12.0


@pytest.mark.asyncio
async def test_in_flight_gateway_request_is_not_killed_by_idle_watchdog():
    framework = _framework(
        {
            "in_flight_requests": 1,
            "awaiting_external_followup": True,
            "awaiting_external_followup_seconds": 60.0,
            "pending_tool_call_ids": ["call-1"],
        }
    )
    runner = asyncio.get_running_loop().create_future()
    asyncio.get_running_loop().call_later(0.02, runner.set_result, None)

    await framework._wait_for_runner_task(
        runner,
        session_id="session-1",
        session_timeout_seconds=1.0,
        request_idle_timeout_seconds=0.005,
    )

    assert framework.gateway_manager.calls > 0


@pytest.mark.asyncio
async def test_session_wall_timeout_remains_the_final_backstop():
    framework = _framework(
        {
            "in_flight_requests": 0,
            "awaiting_external_followup": False,
            "awaiting_external_followup_seconds": None,
            "pending_tool_call_ids": [],
        }
    )
    runner = asyncio.get_running_loop().create_future()

    with pytest.raises(asyncio.TimeoutError, match="wall timeout"):
        await framework._wait_for_runner_task(
            runner,
            session_id="session-1",
            session_timeout_seconds=0.01,
            request_idle_timeout_seconds=1.0,
        )

    assert not runner.cancelled()
    runner.cancel()


@pytest.mark.asyncio
async def test_agent_finished_disables_idle_watchdog_during_grading():
    framework = _framework(
        {
            "in_flight_requests": 0,
            "awaiting_external_followup": True,
            "awaiting_external_followup_seconds": 3600.0,
            "pending_tool_call_ids": ["call-1"],
            "agent_finished": True,
        }
    )
    runner = asyncio.get_running_loop().create_future()
    asyncio.get_running_loop().call_later(0.02, runner.set_result, None)

    await framework._wait_for_runner_task(
        runner,
        session_id="session-1",
        session_timeout_seconds=1.0,
        request_idle_timeout_seconds=0.005,
    )

    assert framework.gateway_manager.calls > 0
