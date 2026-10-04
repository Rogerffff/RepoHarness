import asyncio
import json

import pytest

ALLOWED_SAMPLING_KEYS = frozenset({"temperature", "top_p", "top_k", "max_tokens", "stop"})


def _codex_request(**overrides):
    request = {
        "model": "policy",
        "instructions": "Use the repository tools.",
        "input": [{"type": "message", "role": "user", "content": [{"type": "input_text", "text": "inspect"}]}],
        "tools": [
            {
                "type": "custom",
                "name": "exec",
                "description": "Run a command",
                "format": {"type": "grammar", "syntax": "lark", "definition": "..."},
            }
        ],
        "max_output_tokens": 128,
        "stream": True,
    }
    request.update(overrides)
    return request


def test_responses_to_internal_lowers_codex_exec_and_history():
    from uni_agent.gateway.adapters.responses import responses_to_internal

    payload = _codex_request(
        input=[
            {"type": "message", "role": "user", "content": "inspect"},
            {"type": "reasoning", "summary": [{"type": "summary_text", "text": "need status"}]},
            {"type": "custom_tool_call", "call_id": "call-1", "name": "exec", "input": "git status --short"},
            {"type": "custom_tool_call_output", "call_id": "call-1", "output": " M file.py"},
        ]
    )
    internal = responses_to_internal(
        payload,
        base_sampling_params={"top_p": 0.9},
        allowed_sampling_keys=ALLOWED_SAMPLING_KEYS,
    )

    assert internal["messages"][0] == {"role": "system", "content": "Use the repository tools."}
    assert internal["messages"][1] == {"role": "user", "content": "inspect"}
    assistant = internal["messages"][2]
    assert assistant["reasoning_content"] == "need status"
    assert assistant["tool_calls"][0]["type"] == "custom"
    assert assistant["tool_calls"][0]["function"] == {
        "name": "exec",
        "arguments": {"input": "git status --short"},
    }
    assert internal["messages"][3] == {"role": "tool", "content": " M file.py", "tool_call_id": "call-1"}
    assert internal["tools"] == payload["tools"]
    assert internal["sampling_params"] == {"top_p": 0.9, "max_tokens": 128}


def test_responses_to_internal_merges_reasoning_summary_and_content():
    from uni_agent.gateway.adapters.responses import responses_to_internal

    internal = responses_to_internal(
        _codex_request(
            input=[
                {"type": "message", "role": "user", "content": "inspect"},
                {
                    "type": "reasoning",
                    "summary": [{"type": "summary_text", "text": "short summary"}],
                    "content": [{"type": "reasoning_text", "text": "full reasoning"}],
                },
                {"type": "message", "role": "assistant", "content": "done"},
            ]
        ),
        base_sampling_params={},
        allowed_sampling_keys=ALLOWED_SAMPLING_KEYS,
    )

    assert internal["messages"][-1]["reasoning_content"] == "short summary\nfull reasoning"


def test_responses_to_internal_preserves_single_exec_wrapper_as_input():
    from uni_agent.gateway.adapters.responses import responses_to_internal

    javascript = (
        'const r = await tools.exec_command({"cmd": "git status --short", '
        '"workdir": "/app", "yield_time_ms": 10000});\ntext(r.output);'
    )
    internal = responses_to_internal(
        _codex_request(
            input=[
                {"type": "message", "role": "user", "content": "inspect"},
                {"type": "custom_tool_call", "call_id": "call-1", "name": "exec", "input": javascript},
                {"type": "custom_tool_call_output", "call_id": "call-1", "output": " M file.py"},
            ]
        ),
        base_sampling_params={},
        allowed_sampling_keys=ALLOWED_SAMPLING_KEYS,
    )

    assert internal["messages"][2]["tool_calls"][0]["function"]["arguments"] == {"input": javascript}


def test_complex_codex_exec_javascript_round_trips_as_input_parameter():
    from uni_agent.gateway.adapters.responses import responses_to_internal

    javascript = (
        'const results = await Promise.all([\\n'
        '  tools.exec_command({cmd:"pwd",workdir:"/tmp",yield_time_ms:10000,max_output_tokens:1000}),\\n'
        '  tools.exec_command({cmd:"git status --short",workdir:"/tmp"})\\n'
        ']); for (const r of results) text(r.output);\\n'
    )
    internal = responses_to_internal(
        _codex_request(
            input=[
                {"type": "message", "role": "user", "content": "inspect"},
                {"type": "custom_tool_call", "call_id": "call-1", "name": "exec", "input": javascript},
            ]
        ),
        base_sampling_params={},
        allowed_sampling_keys=ALLOWED_SAMPLING_KEYS,
    )

    call = internal["messages"][-1]["tool_calls"][0]
    assert call["type"] == "custom"
    assert call["function"]["arguments"] == {"input": javascript}


def test_responses_to_internal_does_not_rewrite_arbitrary_custom_exec_javascript():
    from uni_agent.gateway.adapters.responses import responses_to_internal

    javascript = 'const x = await tools.exec_command({"cmd":"pwd"});\ntext(x.output);'
    internal = responses_to_internal(
        _codex_request(
            input=[
                {"type": "message", "role": "user", "content": "inspect"},
                {"type": "custom_tool_call", "call_id": "call-1", "name": "exec", "input": javascript},
            ]
        ),
        base_sampling_params={},
        allowed_sampling_keys=ALLOWED_SAMPLING_KEYS,
    )

    assert internal["messages"][2]["tool_calls"][0]["function"]["arguments"] == {"input": javascript}


def test_responses_preserves_codex_developer_messages_and_additional_tools():
    from uni_agent.gateway.adapters.responses import responses_to_internal

    payload = _codex_request(
        instructions=None,
        tools=[],
        input=[
            {
                "type": "additional_tools",
                "tools": [{"type": "custom", "name": "exec", "description": "Run JavaScript tool calls"}],
            },
            {"type": "message", "role": "developer", "content": "base instructions"},
            {"type": "message", "role": "developer", "content": "tool instructions"},
            {"type": "message", "role": "user", "content": "inspect"},
        ],
    )
    internal = responses_to_internal(
        payload,
        base_sampling_params={},
        allowed_sampling_keys=ALLOWED_SAMPLING_KEYS,
    )

    assert internal["messages"] == [
        {"role": "developer", "content": "base instructions"},
        {"role": "developer", "content": "tool instructions"},
        {"role": "user", "content": "inspect"},
    ]
    assert internal["tools"] == [
        {"type": "custom", "name": "exec", "description": "Run JavaScript tool calls"}
    ]


def test_responses_keeps_hosted_tool_declarations_for_model_boundary():
    from uni_agent.gateway.adapters.responses import responses_to_internal

    hosted = {"type": "web_search", "description": "Search the web"}
    internal = responses_to_internal(
        _codex_request(tools=[hosted]),
        base_sampling_params={},
        allowed_sampling_keys=ALLOWED_SAMPLING_KEYS,
    )

    assert internal["tools"] == [hosted]


def test_responses_maps_hosted_history_calls_and_outputs_without_dropping_payload():
    from uni_agent.gateway.adapters.responses import responses_to_internal

    internal = responses_to_internal(
        _codex_request(
            tools=[{"type": "web_search", "description": "Search the web"}],
            input=[
                {"type": "message", "role": "user", "content": "find it"},
                {"type": "web_search_call", "id": "ws-1", "action": {"query": "Qwen"}},
                {"type": "computer_call", "call_id": "cc-1", "actions": [{"type": "click", "x": 1}]},
                {"type": "computer_call_output", "call_id": "cc-1", "output": "screen"},
                {"type": "compaction", "encrypted_content": "opaque"},
            ],
        ),
        base_sampling_params={},
        allowed_sampling_keys=ALLOWED_SAMPLING_KEYS,
    )

    assistant = next(message for message in internal["messages"] if message.get("role") == "assistant")
    assert [call["function"]["name"] for call in assistant["tool_calls"]] == ["web_search", "computer"]
    assert assistant["tool_calls"][0]["function"]["arguments"] == {"query": "Qwen"}
    assert assistant["tool_calls"][1]["function"]["arguments"] == [{"type": "click", "x": 1}]
    tool_message = next(message for message in internal["messages"] if message.get("tool_call_id") == "cc-1")
    assert tool_message == {"role": "tool", "tool_call_id": "cc-1", "content": "screen"}
    assert internal["messages"][-1] == {"role": "user", "content": ""}


def test_tool_search_output_keeps_message_level_declarations():
    from uni_agent.gateway.adapters.responses import responses_to_internal

    discovered = [{"type": "function", "name": "lookup", "parameters": {"type": "object"}}]
    internal = responses_to_internal(
        _codex_request(input=[
            {"type": "message", "role": "user", "content": "search"},
            {"type": "tool_search_output", "call_id": "ts-1", "tools": discovered},
        ]),
        base_sampling_params={},
        allowed_sampling_keys=ALLOWED_SAMPLING_KEYS,
    )
    assert next(message for message in internal["messages"] if "tools" in message)["tools"] == discovered


def test_responses_preserves_input_images_for_the_v2_6_template():
    from uni_agent.gateway.adapters.responses import responses_to_internal

    internal = responses_to_internal(
        _codex_request(
            input=[
                {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "inspect"},
                        {"type": "input_image", "image_url": "data:image/png;base64,AAAA"},
                    ],
                }
            ]
        ),
        base_sampling_params={},
        allowed_sampling_keys=ALLOWED_SAMPLING_KEYS,
    )

    assert internal["messages"][1]["content"] == [
        {"type": "text", "text": "inspect"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}},
    ]


def test_responses_control_only_input_gets_an_empty_user_turn():
    from uni_agent.gateway.adapters.responses import responses_to_internal

    internal = responses_to_internal(
        _codex_request(instructions=None, tools=[], input=[{"type": "compaction_trigger"}]),
        base_sampling_params={},
        allowed_sampling_keys=ALLOWED_SAMPLING_KEYS,
    )
    assert internal["messages"] == [{"role": "user", "content": ""}]


def test_responses_merges_identical_top_level_and_additional_tools():
    from uni_agent.gateway.adapters.responses import responses_to_internal

    tool = {"type": "function", "name": "lookup", "parameters": {"type": "object"}}
    internal = responses_to_internal(
        _codex_request(
            tools=[tool],
            input=[{"type": "additional_tools", "tools": [dict(tool)]}, {"type": "message", "role": "user", "content": "go"}],
        ),
        base_sampling_params={},
        allowed_sampling_keys=ALLOWED_SAMPLING_KEYS,
    )
    assert internal["tools"] == [tool]


def test_responses_cleans_top_level_tool_schema_before_rendering():
    from uni_agent.gateway.adapters.responses import responses_to_internal

    tool = {
        "type": "function",
        "name": "lookup",
        "parameters": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Lookup",
            "type": "object",
            "required": [],
            "additionalProperties": {},
        },
    }
    internal = responses_to_internal(
        _codex_request(tools=[tool]),
        base_sampling_params={},
        allowed_sampling_keys=ALLOWED_SAMPLING_KEYS,
    )
    assert internal["tools"] == [{"type": "function", "name": "lookup", "parameters": {"type": "object"}}]


def test_responses_skips_empty_namespace_tool_groups():
    from uni_agent.gateway.adapters.responses import responses_to_internal

    internal = responses_to_internal(
        _codex_request(tools=[{"type": "namespace", "name": "empty_shell", "tools": None}]),
        base_sampling_params={},
        allowed_sampling_keys=ALLOWED_SAMPLING_KEYS,
    )

    assert internal["tools"] is None


@pytest.mark.parametrize("field,value", [("background", True), ("store", True), ("previous_response_id", "resp_x")])
def test_responses_to_internal_rejects_unsupported_stateful_features(field, value):
    from uni_agent.gateway.adapters.responses import responses_to_internal
    from uni_agent.gateway.adapters.types import MalformedRequestError

    with pytest.raises(MalformedRequestError):
        responses_to_internal(
            _codex_request(**{field: value}),
            base_sampling_params={},
            allowed_sampling_keys=ALLOWED_SAMPLING_KEYS,
        )


def test_responses_build_response_preserves_custom_exec():
    from uni_agent.gateway.adapters.responses import responses_build_response
    from uni_agent.gateway.session.session import GenerationOutcome

    body = responses_build_response(
        GenerationOutcome(
            assistant_msg={
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call-1",
                        "type": "function",
                        "function": {"name": "exec", "arguments": {"input": "pwd"}},
                    }
                ],
            },
            finish_reason="tool_calls",
            prompt_tokens=10,
            completion_tokens=3,
        ),
        payload=_codex_request(),
        model="policy",
    )

    assert body["object"] == "response"
    assert body["status"] == "completed"
    assert body["output"][0]["type"] == "custom_tool_call"
    assert body["output"][0]["name"] == "exec"
    assert body["output"][0]["input"] == "pwd"
    assert body["usage"]["total_tokens"] == 13


def test_responses_build_response_preserves_exec_input_verbatim():
    from uni_agent.gateway.adapters.responses import responses_build_response
    from uni_agent.gateway.session.session import GenerationOutcome

    body = responses_build_response(
        GenerationOutcome(
            assistant_msg={
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call-1",
                        "type": "function",
                        "function": {
                            "name": "exec",
                        "arguments": {
                            "input": 'const r = await tools.exec_command({"cmd":"git status --short"});\ntext(r.output);',
                        },
                        },
                    }
                ],
            },
            finish_reason="tool_calls",
            prompt_tokens=10,
            completion_tokens=3,
        ),
        payload=_codex_request(),
        model="policy",
    )

    item = body["output"][0]
    assert item["type"] == "custom_tool_call"
    assert item["name"] == "exec"
    assert item["input"] == 'const r = await tools.exec_command({"cmd":"git status --short"});\ntext(r.output);'


@pytest.mark.asyncio
async def test_responses_stream_emits_parsed_heartbeat_and_exec_events():
    from uni_agent.gateway.adapters.responses import responses_stream_response
    from uni_agent.gateway.session.session import GenerationOutcome

    async def generate():
        await asyncio.sleep(0.03)
        return GenerationOutcome(
            assistant_msg={
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call-1",
                        "type": "function",
                        "function": {"name": "exec", "arguments": {"input": "pwd"}},
                    }
                ],
            },
            finish_reason="tool_calls",
            prompt_tokens=10,
            completion_tokens=3,
        )

    response = responses_stream_response(
        generate,
        payload=_codex_request(),
        model="policy",
        heartbeat_interval_s=0.005,
    )
    text = (b"".join([chunk async for chunk in response.body_iterator])).decode()
    events = [line.removeprefix("event: ") for line in text.splitlines() if line.startswith("event: ")]
    data = [json.loads(line.removeprefix("data: ")) for line in text.splitlines() if line.startswith("data: ")]

    assert events[:2] == ["response.created", "response.in_progress"]
    assert events.count("response.in_progress") >= 2
    assert "response.custom_tool_call_input.delta" in events
    assert "response.custom_tool_call_input.done" in events
    assert events[-1] == "response.completed"
    assert [item["sequence_number"] for item in data] == list(range(len(data)))


@pytest.mark.asyncio
async def test_responses_stream_emits_failed_response_and_error_event():
    from uni_agent.gateway.adapters.responses import responses_stream_response

    async def generate():
        raise RuntimeError("backend failed")

    response = responses_stream_response(generate, payload=_codex_request(), model="policy")
    text = (b"".join([chunk async for chunk in response.body_iterator])).decode()
    events = [json.loads(line.removeprefix("data: ")) for line in text.splitlines() if line.startswith("data: ")]

    assert events[-2]["type"] == "response.failed"
    assert events[-2]["response"]["error"] == {
        "code": "internal_error",
        "message": "backend failed",
    }
    assert events[-1]["type"] == "error"
    assert events[-1]["message"] == "backend failed"


def test_responses_build_response_reports_length_as_incomplete():
    """A capacity-exhausted generation must not masquerade as ``completed``:
    upstream reports ``status: incomplete`` + ``incomplete_details.reason``,
    and the mini-swe-agent client keys its non-retry path off that."""
    from uni_agent.gateway.adapters.responses import responses_build_response
    from uni_agent.gateway.session.session import GenerationOutcome

    body = responses_build_response(
        GenerationOutcome(
            assistant_msg={"role": "assistant", "content": ""},
            finish_reason="length",
            prompt_tokens=262142,
            completion_tokens=0,
        ),
        payload=_codex_request(),
        model="policy",
    )

    assert body["status"] == "incomplete"
    assert body["incomplete_details"] == {"reason": "max_output_tokens"}
    assert body["output"] == []


def test_responses_build_response_completed_has_no_incomplete_details():
    from uni_agent.gateway.adapters.responses import responses_build_response
    from uni_agent.gateway.session.session import GenerationOutcome

    body = responses_build_response(
        GenerationOutcome(
            assistant_msg={"role": "assistant", "content": "done"},
            finish_reason="stop",
            prompt_tokens=10,
            completion_tokens=1,
        ),
        payload=_codex_request(),
        model="policy",
    )
    assert body["status"] == "completed"
    assert body["incomplete_details"] is None
