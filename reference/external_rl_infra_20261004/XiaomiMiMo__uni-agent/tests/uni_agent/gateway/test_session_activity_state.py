import asyncio
from types import SimpleNamespace

import pytest

from tests.uni_agent.support import FakeTokenizer
from uni_agent.gateway.adapters.openai import openai_to_internal
from uni_agent.gateway.session import GatewaySession, MessageCodec, SessionHandle
from verl.workers.rollout.replica import TokenOutput

_ALLOWED_SAMPLING_KEYS = frozenset({"temperature", "top_p", "top_k", "max_tokens", "stop"})


class _ControlledBackend:
    def __init__(self, responses: list[str]):
        self.responses = list(responses)
        self.calls: list[asyncio.Event] = []
        self.call_started = asyncio.Event()

    async def generate(self, request_id, *, prompt_ids, sampling_params, image_data=None, video_data=None):
        release = asyncio.Event()
        self.calls.append(release)
        self.call_started.set()
        self.call_started = asyncio.Event()
        await release.wait()
        text = self.responses.pop(0)
        token_ids = [ord(char) for char in text]
        return TokenOutput(token_ids=token_ids, log_probs=None, stop_reason="completed")

    async def wait_for_calls(self, count: int) -> None:
        while len(self.calls) < count:
            await asyncio.wait_for(self.call_started.wait(), timeout=1)

    def release(self, index: int) -> None:
        self.calls[index].set()


async def _fake_extract_tool_calls(self, response_ids, tools, parser_name):
    text = self._tokenizer.decode(response_ids, skip_special_tokens=False)
    if text == "TOOL":
        return "", [SimpleNamespace(name="exec", arguments='{"cmd":"pwd"}')]
    return text, []


def _request(messages: list[dict], tools: list[dict] | None = None):
    return openai_to_internal(
        {"model": "model", "messages": messages, "tools": tools or []},
        base_sampling_params={},
        allowed_sampling_keys=_ALLOWED_SAMPLING_KEYS,
    )


@pytest.mark.asyncio
async def test_tool_call_arms_followup_wait_and_next_request_clears_it(monkeypatch):
    monkeypatch.setattr(MessageCodec, "_extract_tool_calls", _fake_extract_tool_calls)
    session = GatewaySession(
        SessionHandle(session_id="activity"),
        MessageCodec(FakeTokenizer(), tool_parser_name="qwen3_xml"),
    )
    backend = _ControlledBackend(["TOOL", "DONE"])
    tools = [{"type": "function", "function": {"name": "exec", "parameters": {"type": "object"}}}]

    first_task = asyncio.create_task(session.run_generation(_request([{"role": "user", "content": "inspect"}], tools), backend))
    await backend.wait_for_calls(1)
    assert session.snapshot_state()["in_flight_requests"] == 1
    backend.release(0)
    first = await first_task

    tool_call = first.assistant_msg["tool_calls"][0]
    state = session.snapshot_state()
    assert state["in_flight_requests"] == 0
    assert state["awaiting_external_followup"] is True
    assert state["pending_tool_call_ids"] == [tool_call["id"]]

    messages = [
        {"role": "user", "content": "inspect"},
        first.assistant_msg,
        {"role": "tool", "tool_call_id": tool_call["id"], "content": "/repo"},
    ]
    second_task = asyncio.create_task(session.run_generation(_request(messages, tools), backend))
    await backend.wait_for_calls(2)
    state = session.snapshot_state()
    assert state["in_flight_requests"] == 1
    assert state["awaiting_external_followup"] is True

    backend.release(1)
    await second_task
    state = session.snapshot_state()
    assert state["in_flight_requests"] == 0
    assert state["awaiting_external_followup"] is False
    assert state["pending_tool_call_ids"] == []


@pytest.mark.asyncio
async def test_plain_assistant_completion_does_not_arm_followup_wait():
    session = GatewaySession(SessionHandle(session_id="plain"), MessageCodec(FakeTokenizer()))
    backend = _ControlledBackend(["DONE"])

    task = asyncio.create_task(session.run_generation(_request([{"role": "user", "content": "answer"}]), backend))
    await backend.wait_for_calls(1)
    backend.release(0)
    await task

    state = session.snapshot_state()
    assert state["in_flight_requests"] == 0
    assert state["awaiting_external_followup"] is False
    assert state["awaiting_since"] is None


@pytest.mark.asyncio
async def test_concurrent_plain_sibling_does_not_clear_pending_tool_chain(monkeypatch):
    monkeypatch.setattr(MessageCodec, "_extract_tool_calls", _fake_extract_tool_calls)
    session = GatewaySession(
        SessionHandle(session_id="siblings"),
        MessageCodec(FakeTokenizer(), tool_parser_name="qwen3_xml"),
    )
    backend = _ControlledBackend(["TOOL", "DONE"])
    tools = [{"type": "function", "function": {"name": "exec", "parameters": {"type": "object"}}}]

    pending_task = asyncio.create_task(
        session.run_generation(_request([{"role": "user", "content": "needs tool"}], tools), backend)
    )
    sibling_task = asyncio.create_task(
        session.run_generation(_request([{"role": "user", "content": "plain sibling"}], tools), backend)
    )
    await backend.wait_for_calls(2)
    backend.release(0)
    backend.release(1)
    first, _ = await asyncio.gather(pending_task, sibling_task)

    state = session.snapshot_state()
    assert state["in_flight_requests"] == 0
    assert state["awaiting_external_followup"] is True
    assert state["pending_tool_call_ids"] == [first.assistant_msg["tool_calls"][0]["id"]]


@pytest.mark.asyncio
async def test_later_request_on_another_chain_resets_followup_idle_clock(monkeypatch):
    """Compaction/retries replay a new history: the orphaned chain keeps its pending
    tool calls, but the session is clearly alive, so idle must restart from the
    latest request rather than from the abandoned tool call."""
    monkeypatch.setattr(MessageCodec, "_extract_tool_calls", _fake_extract_tool_calls)
    session = GatewaySession(
        SessionHandle(session_id="compaction"),
        MessageCodec(FakeTokenizer(), tool_parser_name="qwen3_xml"),
    )
    backend = _ControlledBackend(["TOOL", "DONE"])
    tools = [{"type": "function", "function": {"name": "exec", "parameters": {"type": "object"}}}]

    first_task = asyncio.create_task(session.run_generation(_request([{"role": "user", "content": "needs tool"}], tools), backend))
    await backend.wait_for_calls(1)
    backend.release(0)
    await first_task

    # Pretend the tool call was issued long ago and nothing happened since.
    session.updated_at -= 1000.0
    session.active_chains[0].awaiting_external_followup_since -= 1000.0
    stale = session.snapshot_state()
    assert stale["awaiting_external_followup"] is True
    assert stale["awaiting_external_followup_seconds"] >= 1000.0
    assert stale["session_idle_seconds"] >= 1000.0

    # A summarized history (no tool result for the pending call) starts a new chain.
    second_task = asyncio.create_task(
        session.run_generation(_request([{"role": "user", "content": "summary of the work so far"}], tools), backend)
    )
    await backend.wait_for_calls(2)
    backend.release(1)
    await second_task

    fresh = session.snapshot_state()
    assert fresh["awaiting_external_followup"] is True, "the orphaned tool call is still pending"
    assert fresh["awaiting_external_followup_seconds"] < 5.0, "but idle restarts from the latest request"
    assert fresh["session_idle_seconds"] < 5.0
    assert fresh["agent_finished"] is False


@pytest.mark.asyncio
async def test_agent_finished_marker_is_exposed_in_state():
    session = GatewaySession(SessionHandle(session_id="finished"), MessageCodec(FakeTokenizer()))
    assert session.snapshot_state()["agent_finished"] is False
    await session.set_reward_info({"agent_finished": True, "agent_status": "Completed"})
    assert session.snapshot_state()["agent_finished"] is True
    await session.set_reward_info({"reward": 1.0, "finished": True})
    assert session.snapshot_state()["agent_finished"] is False
