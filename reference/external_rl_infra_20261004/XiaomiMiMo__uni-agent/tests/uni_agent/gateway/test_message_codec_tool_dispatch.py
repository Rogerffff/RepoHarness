import asyncio
import json
import sys
from types import SimpleNamespace

import pytest

from tests.uni_agent.support import FakeTokenizer

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search",
            "description": "search docs",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer"},
                },
            },
        },
    }
]

CUSTOM_EXEC = [
    {
        "type": "custom",
        "name": "exec",
        "description": "Run JavaScript code",
        "format": {"type": "grammar", "syntax": "lark", "definition": "..."},
    }
]


def test_default_vision_extractor_projects_nested_urls_only_for_qwen_utils(monkeypatch):
    import uni_agent.gateway.session.codec as codec_mod

    captured = {}

    def process_vision_info(messages, **kwargs):
        captured["messages"] = messages
        captured["kwargs"] = kwargs
        return ["image-object"], None

    monkeypatch.setitem(sys.modules, "qwen_vl_utils", type("QwenVL", (), {"process_vision_info": process_vision_info}))
    codec = object.__new__(codec_mod.MessageCodec)
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}},
                {"type": "text", "text": "inspect"},
            ],
        }
    ]

    result = asyncio.run(codec._default_vision_info_extractor(messages, image_patch_size=16))

    assert result == (["image-object"], None)
    assert captured["messages"][0]["content"][0] == {
        "type": "image",
        "image": "data:image/png;base64,AAAA",
    }
    assert captured["kwargs"] == {"image_patch_size": 16, "return_video_metadata": True}
    assert messages[0]["content"][0] == {
        "type": "image_url",
        "image_url": {"url": "data:image/png;base64,AAAA"},
    }


def _ids(text: str) -> list[int]:
    return [ord(char) for char in text]


@pytest.mark.parametrize(
    ("text", "prompt_opens_thinking", "expected"),
    [
        (
            "reasoning\n</think>\n\nvisible answer",
            True,
            ("reasoning", "visible answer"),
        ),
        (
            "<think>reasoning</think>\nvisible answer",
            False,
            ("reasoning", "visible answer"),
        ),
        ("plain answer", True, (None, "plain answer")),
    ],
)
def test_split_generation_thinking_respects_template_owned_prefix(text, prompt_opens_thinking, expected):
    from uni_agent.gateway.session.codec import _split_generation_thinking

    assert _split_generation_thinking(text, prompt_opens_thinking=prompt_opens_thinking) == expected


def test_parser_tool_view_projects_custom_exec_without_mutating_prompt_declaration():
    import uni_agent.gateway.session.codec as codec_mod

    parser_tools = codec_mod._parser_tool_view(CUSTOM_EXEC)

    assert CUSTOM_EXEC[0] == {
        "type": "custom",
        "name": "exec",
        "description": "Run JavaScript code",
        "format": {"type": "grammar", "syntax": "lark", "definition": "..."},
    }
    assert parser_tools == [
        {
            "type": "function",
            "function": {
                "name": "exec",
                "description": "Run JavaScript code",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "input": {"type": "string"},
                    },
                    "required": ["input"],
                    "additionalProperties": False,
                },
            },
        }
    ]


def test_sglang_freeform_exec_preserves_raw_body_before_qwen_parser():
    from uni_agent.gateway.session.codec import (
        MessageCodec,
        _canonical_tools_hash,
        _parser_tool_view,
    )

    parser_tools = _parser_tool_view(CUSTOM_EXEC + TOOLS)
    codec = MessageCodec(FakeTokenizer(), rollout_backend="sglang")

    class FakeSGLangParser:
        def __init__(self):
            self.seen = []

        def has_tool_call(self, text):
            return "tool_call" in text

        def parse_non_stream(self, text):
            self.seen.append(text)
            return "", [
                SimpleNamespace(name="search", parameters='{"query":"docs"}')
            ]

    parser = FakeSGLangParser()
    codec._tool_parser_cache[("sglang", "qwen3_coder", _canonical_tools_hash(parser_tools))] = parser

    tool_open = "<tool_" + "call>"
    tool_close = "</tool_" + "call>"
    function_open = "<function="
    function_close = "</function>"
    text = (
        "before"
        + tool_open
        + function_open
        + "exec>const r = await tools.exec_command({cmd:\"pwd\"}); text(r.output);"
        + function_close
        + tool_close
        + tool_open
        + function_open
        + "search><parameter=query>docs</parameter>"
        + function_close
        + tool_close
    )

    content, calls = codec._process_tool_calls_sglang(text, parser_tools, "qwen3_coder")

    assert content == "before"
    assert calls[0].name == "exec"
    assert calls[0].arguments == 'const r = await tools.exec_command({cmd:"pwd"}); text(r.output);'
    assert calls[1].name == "search"
    assert calls[1].arguments == '{"query":"docs"}'
    assert len(parser.seen) == 1
    assert "exec" not in parser.seen[0]


def test_sglang_json_body_function_preserves_arguments_without_parser():
    from uni_agent.gateway.session.codec import MessageCodec, _canonical_tools_hash, _parser_tool_view

    codec = MessageCodec(FakeTokenizer(), rollout_backend="sglang")

    class FailingParser:
        def has_tool_call(self, text):
            return True

        def parse_non_stream(self, text):
            raise AssertionError("JSON-body calls must be handled before qwen3_coder")

    parser_tools = _parser_tool_view(TOOLS)
    codec._tool_parser_cache[("sglang", "qwen3_coder", _canonical_tools_hash(parser_tools))] = FailingParser()
    text = (
        "before<tool_call><function=search>{\"query\":\"docs\",\"limit\":2}</function></tool_call>"
        "after"
    )

    content, calls = codec._process_tool_calls_sglang(text, parser_tools, "qwen3_coder")

    assert content == "beforeafter"
    assert len(calls) == 1
    assert calls[0].name == "search"
    assert calls[0].arguments == '{"query":"docs","limit":2}'


def test_sglang_malformed_direct_body_is_forwarded_for_harness_feedback():
    from uni_agent.gateway.session.codec import MessageCodec, _canonical_tools_hash, _parser_tool_view

    codec = MessageCodec(FakeTokenizer(), rollout_backend="sglang")

    class FailingParser:
        def has_tool_call(self, text):
            return True

        def parse_non_stream(self, text):
            raise AssertionError("direct bodies must not be rewritten to an empty dict")

    parser_tools = _parser_tool_view(TOOLS)
    codec._tool_parser_cache[("sglang", "qwen3_coder", _canonical_tools_hash(parser_tools))] = FailingParser()
    text = "<tool_call><function=search>{bad json}</function></tool_call>"

    _, calls = codec._process_tool_calls_sglang(text, parser_tools, "qwen3_coder")

    assert calls[0].arguments == "{bad json}"


def test_sglang_incomplete_direct_body_becomes_non_executable_feedback_call():
    from uni_agent.gateway.session.codec import MessageCodec, _canonical_tools_hash, _parser_tool_view

    codec = MessageCodec(FakeTokenizer(), rollout_backend="sglang")
    parser_tools = _parser_tool_view(TOOLS)

    class Parser:
        def has_tool_call(self, text):
            return True

    codec._tool_parser_cache[("sglang", "qwen3_coder", _canonical_tools_hash(parser_tools))] = Parser()
    text = '<tool_call><function=search>{"query":"docs"}'

    content, calls = codec._process_tool_calls_sglang(text, parser_tools, "qwen3_coder")

    assert content == ""
    assert len(calls) == 1
    assert calls[0].name == "__malformed_tool_call__"
    assert "incomplete tool call" in calls[0].arguments


def test_sglang_suppressed_unknown_parameter_call_is_forwarded_by_name(monkeypatch):
    from uni_agent.gateway.session.codec import MessageCodec, _canonical_tools_hash, _parser_tool_view

    codec = MessageCodec(FakeTokenizer(), rollout_backend="sglang")
    parser_tools = _parser_tool_view(TOOLS)

    class SuppressingParser:
        def has_tool_call(self, text):
            return True

        def parse_non_stream(self, text):
            return "", []

    codec._tool_parser_cache[("sglang", "qwen3_coder", _canonical_tools_hash(parser_tools))] = SuppressingParser()
    text = "<tool_call><function=Read><parameter=path>/tmp/a</parameter></function></tool_call>"

    _, calls = codec._process_tool_calls_sglang(text, parser_tools, "qwen3_coder")

    assert calls[0].name == "Read"
    assert calls[0].arguments == "<parameter=path>/tmp/a</parameter>"


def test_parser_tool_view_projects_hosted_declaration_without_changing_prompt_view():
    import uni_agent.gateway.session.codec as codec_mod

    hosted = [{"type": "web_search", "description": "Search the web"}]
    parser_tools = codec_mod._parser_tool_view(hosted)

    assert parser_tools == [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web",
                "parameters": {"type": "object", "properties": {}},
            },
        }
    ]
    assert codec_mod._prompt_tool_view(hosted) == hosted


def test_prompt_tool_view_projects_custom_exec_for_qwen_template_without_mutating_wire_tool():
    import uni_agent.gateway.session.codec as codec_mod

    prompt_tools = codec_mod._prompt_tool_view(CUSTOM_EXEC)

    assert CUSTOM_EXEC[0]["type"] == "custom"
    assert prompt_tools == [
        {
            "type": "function",
            "function": {
                "name": "exec",
                "description": prompt_tools[0]["function"]["description"],
                "parameters": {
                    "type": "object",
                    "properties": {"input": {"type": "string"}},
                    "required": ["input"],
                    "additionalProperties": False,
                },
            },
        }
    ]
    description = prompt_tools[0]["function"]["description"]
    assert description == "Run JavaScript code"
    assert prompt_tools[0]["function"]["name"] != "exec_command"


def test_encode_full_passes_prompt_projection_to_chat_template():
    from uni_agent.gateway.session.codec import MessageCodec

    class InspectingTokenizer(FakeTokenizer):
        def __init__(self):
            self.seen_tools = []
            self.seen_messages = []

        def apply_chat_template(self, messages, tokenize=True, add_generation_prompt=True, tools=None, **kwargs):
            self.seen_tools.append(tools)
            self.seen_messages.append(messages)
            return super().apply_chat_template(
                messages,
                tokenize=tokenize,
                add_generation_prompt=add_generation_prompt,
                tools=tools,
                **kwargs,
            )

    tokenizer = InspectingTokenizer()
    MessageCodec(tokenizer).encode_full(
        [{"role": "user", "content": "Inspect the repository."}],
        tools=CUSTOM_EXEC,
    )

    prompt_tools = tokenizer.seen_tools[-1]
    assert prompt_tools[0]["type"] == "function"
    assert prompt_tools[0]["function"]["name"] == "exec"
    assert prompt_tools[0]["function"]["parameters"]["properties"]["input"] == {"type": "string"}
    assert tokenizer.seen_messages[-1] == [{"role": "user", "content": "Inspect the repository."}]


def test_prompt_message_view_does_not_change_non_custom_tool_requests():
    import uni_agent.gateway.session.codec as codec_mod

    messages = [{"role": "user", "content": "Search docs."}]
    assert codec_mod._prompt_message_view(messages, TOOLS) is messages


def test_v2_6_prompt_view_keeps_flat_custom_declaration_and_raw_history():
    import uni_agent.gateway.session.codec as codec_mod

    custom = [{"type": "custom", "name": "exec", "description": "Run JavaScript"}]
    assert codec_mod._prompt_tool_view(custom, freeform_tool_calls=True) is custom

    history = [{
        "role": "assistant",
        "content": "",
        "tool_calls": [{
            "type": "function",
            "function": {"name": "exec", "arguments": '{"input":"const x = 1;"}'},
        }],
    }]
    view = codec_mod._prompt_message_view(history, custom, freeform_tool_calls=True)
    assert view[0]["tool_calls"] == [{"name": "exec", "input": "const x = 1;"}]


def test_message_level_tools_are_added_only_to_parser_view():
    from uni_agent.gateway.session.codec import MessageCodec

    codec = MessageCodec(FakeTokenizer())
    top = [{"type": "function", "function": {"name": "exec", "parameters": {}}}]
    messages = [{
        "role": "tool",
        "content": "",
        "tools": [{"type": "namespace", "name": "collaboration", "tools": [
            {"type": "function", "name": "wait_agent", "parameters": {}}
        ]}],
    }]
    parser_tools = codec.parser_tools_for_messages(top, messages)
    assert parser_tools[0] is top[0]
    assert parser_tools[1]["name"] == "collaboration__wait_agent"
    assert messages[0]["tools"][0]["name"] == "collaboration"


def test_parser_rejects_undeclared_tool_names():
    from uni_agent.gateway.session.codec import MessageCodec

    with pytest.raises(ValueError, match="Undeclared tool"):
        MessageCodec._validate_tool_call_names(
            [SimpleNamespace(name="exec_command")],
            [{"type": "custom", "name": "exec"}],
        )


@pytest.mark.asyncio
async def test_unknown_tool_names_are_forwarded_for_harness_feedback(monkeypatch):
    """Unknown names remain structured calls so the harness can recover."""
    from uni_agent.gateway.session.codec import MessageCodec

    codec = MessageCodec(FakeTokenizer(), rollout_backend="sglang")
    monkeypatch.setattr(
        codec,
        "_process_tool_calls_sglang",
        lambda text, tools, parser_name: (
            text,
            [SimpleNamespace(name="bash", arguments='{"cmd":"pwd"}')],
        ),
    )

    content, calls = await codec._extract_tool_calls(_ids("raw"), TOOLS, "qwen3_coder")

    assert content == "raw"
    assert calls[0].name == "bash"


@pytest.mark.asyncio
async def test_parser_api_failure_is_fatal(monkeypatch):
    from uni_agent.gateway.session.codec import MessageCodec

    def broken_sglang(*args, **kwargs):
        raise ValueError("malformed tool call")

    codec = MessageCodec(FakeTokenizer(), rollout_backend="sglang")
    monkeypatch.setattr(codec, "_process_tool_calls_sglang", broken_sglang)

    with pytest.raises(RuntimeError, match="sglang tool parser 'qwen3_coder' failed") as exc_info:
        await codec._extract_tool_calls(_ids("raw"), TOOLS, "qwen3_coder")
    assert isinstance(exc_info.value.__cause__, ValueError)


@pytest.mark.asyncio
async def test_parser_payload_rejection_becomes_malformed_feedback(monkeypatch):
    from uni_agent.gateway.session.codec import MessageCodec, _canonical_tools_hash, _parser_tool_view

    codec = MessageCodec(FakeTokenizer(), rollout_backend="sglang")
    parser_tools = _parser_tool_view(TOOLS)

    class RejectingParser:
        def has_tool_call(self, text):
            return True

        def parse_non_stream(self, text):
            raise ValueError("invalid JSON arguments")

    codec._tool_parser_cache[("sglang", "qwen3_coder", _canonical_tools_hash(parser_tools))] = RejectingParser()
    text = '<tool_call><function=search><parameter=query>{bad}</parameter></function></tool_call>'

    _, calls = await codec._extract_tool_calls(_ids(text), TOOLS, "qwen3_coder")

    assert len(calls) == 1
    assert calls[0].name == "__malformed_tool_call__"
    assert "raw_body" in calls[0].arguments


@pytest.mark.asyncio
async def test_empty_backend_result_for_incomplete_envelope_becomes_feedback(monkeypatch):
    from uni_agent.gateway.session.codec import MessageCodec

    codec = MessageCodec(FakeTokenizer(), rollout_backend="vllm")
    monkeypatch.setattr(codec, "_process_tool_calls_vllm", lambda text, tools, parser_name: (text, []))
    text = '<tool_call><function=search>{"query":"docs"}'

    _, calls = await codec._extract_tool_calls(_ids(text), TOOLS, "qwen3_coder")

    assert calls[0].name == "__malformed_tool_call__"


def test_decoded_custom_tool_keeps_marker_for_history_replay(monkeypatch):
    from uni_agent.gateway.session.codec import MessageCodec

    codec = MessageCodec(FakeTokenizer())
    codec._tool_parser_name = "fake"

    async def fake_extract(_response_ids, _tools, _parser_name):
        return "", [SimpleNamespace(name="exec", arguments='{"input":"JS"}')]

    monkeypatch.setattr(codec, "_extract_tool_calls", fake_extract)
    message, reason = __import__("asyncio").run(
        codec.decode_response(
            [ord("x")],
            tools=[{"type": "custom", "name": "exec"}],
        )
    )
    assert reason == "tool_calls"
    assert message["tool_calls"][0]["type"] == "custom"


def test_prompt_message_view_preserves_codex_system_wording_for_custom_exec():
    import uni_agent.gateway.session.codec as codec_mod

    messages = [
        {
            "role": "system",
            "content": (
                "Exercise caution for exec_command calls. "
                "Use `apply_patch` for local file edits. "
                "Do not use Python when a simple shell command or `apply_patch` is enough."
            ),
        },
        {"role": "user", "content": "Edit the repository."},
    ]

    view = codec_mod._prompt_message_view(messages, CUSTOM_EXEC)
    content = view[0]["content"]

    assert content == messages[0]["content"]
    assert "exec_command" in content
    assert "apply_patch" in content
    assert messages[0]["content"].startswith("Exercise caution for exec_command calls")


def test_prefix_canonicalization_matches_function_and_custom_tool_envelopes():
    from uni_agent.gateway.session.codec import MessageCodec

    codec = MessageCodec(FakeTokenizer())
    function_message = {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "generated-id",
                "type": "function",
                "function": {"name": "exec", "arguments": {"input": "pwd"}},
            }
        ],
    }
    custom_history = {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "wire-call-id",
                "type": "custom",
                "function": {"name": "exec", "arguments": '{"input":"pwd"}'},
            }
        ],
    }

    assert codec.canonicalize_message_for_prefix_comparison(
        function_message
    ) == codec.canonicalize_message_for_prefix_comparison(custom_history)


def test_prefix_canonicalization_matches_direct_custom_body_and_responses_input_wrapper():
    from uni_agent.gateway.session.codec import MessageCodec

    javascript = 'const r = await tools.exec_command({"cmd": "pwd"});\ntext(r.output);'
    codec = MessageCodec(FakeTokenizer())
    generated_direct_body = {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "generated-id",
                "type": "custom",
                "function": {"name": "exec", "arguments": javascript},
            }
        ],
    }
    responses_history = {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "wire-call-id",
                "type": "custom",
                "function": {"name": "exec", "arguments": {"input": javascript}},
            }
        ],
    }

    assert codec.canonicalize_message_for_prefix_comparison(
        generated_direct_body
    ) == codec.canonicalize_message_for_prefix_comparison(responses_history)


def test_qwen_vllm_parser_uses_tool_schema_for_argument_types():
    from uni_agent.gateway.session.codec import MessageCodec

    class QwenTokenizer(FakeTokenizer):
        def get_vocab(self):
            return {"<tool_call>": 1, "</tool_call>": 2}

    text = (
        "<tool_call>\n"
        "<function=search>\n"
        "<parameter=query>docs</parameter>\n"
        "<parameter=limit>2</parameter>\n"
        "</function>\n"
        "</tool_call>"
    )
    content, calls = MessageCodec(QwenTokenizer())._process_tool_calls_vllm(text, TOOLS, "qwen3_coder")

    assert content == ""
    assert json.loads(calls[0].arguments) == {"query": "docs", "limit": 2}


@pytest.mark.parametrize(
    "constructor_accepts_tools",
    [False, True],
    ids=["tokenizer-only", "tokenizer-and-tools"],
)
def test_vllm_parser_supports_tool_schema_constructor_contracts(monkeypatch, constructor_accepts_tools):
    from vllm.entrypoints.openai.chat_completion.protocol import ChatCompletionToolsParam
    from vllm.tool_parsers import ToolParserManager

    from uni_agent.gateway.session.codec import MessageCodec

    seen = {}

    class ParserBase:
        def extract_tool_calls(self, text, request):
            seen["request"] = request
            return SimpleNamespace(
                tools_called=True,
                content="visible",
                tool_calls=[SimpleNamespace(function=SimpleNamespace(name="search", arguments='{"query":"x"}'))],
            )

    class ParserWithoutConstructorTools(ParserBase):
        def __init__(self, tokenizer):
            seen["tokenizer"] = tokenizer

    class ParserWithConstructorTools(ParserBase):
        def __init__(self, tokenizer, *, tools):
            seen["tokenizer"] = tokenizer
            seen["tools"] = tools

    parser_cls = ParserWithConstructorTools if constructor_accepts_tools else ParserWithoutConstructorTools

    monkeypatch.setattr(
        ToolParserManager,
        "get_tool_parser",
        classmethod(lambda cls, name: parser_cls),
    )

    tokenizer = FakeTokenizer()
    content, calls = MessageCodec(tokenizer)._process_tool_calls_vllm("raw", TOOLS, "qwen3_coder")

    assert content == "visible"
    assert calls[0].name == "search"
    assert seen["tokenizer"] is tokenizer
    assert len(seen["request"].tools) == 1
    assert isinstance(seen["request"].tools[0], ChatCompletionToolsParam)
    if constructor_accepts_tools:
        assert seen["tools"] is seen["request"].tools
    else:
        assert "tools" not in seen


@pytest.mark.asyncio
async def test_tool_call_dispatch_uses_sglang_for_sglang_rollout(monkeypatch):
    from uni_agent.gateway.session.codec import MessageCodec

    seen = {}

    def fake_sglang(text, tools, parser_name):
        seen["sglang"] = (text, tools, parser_name)
        return "visible", [SimpleNamespace(name="search", arguments='{"query":"x"}')]

    def fail_vllm(*args, **kwargs):
        raise AssertionError("vLLM should not run when SGLang succeeds")

    async def fail_verl(*args, **kwargs):
        raise AssertionError("verl should not run when an engine succeeds")

    codec = MessageCodec(FakeTokenizer(), rollout_backend="sglang")
    monkeypatch.setattr(codec, "_process_tool_calls_sglang", fake_sglang)
    monkeypatch.setattr(codec, "_process_tool_calls_vllm", fail_vllm)
    monkeypatch.setattr(codec, "_process_tool_calls_verl", fail_verl)

    content, calls = await codec._extract_tool_calls(_ids("raw"), TOOLS, "hermes")

    assert content == "visible"
    assert calls[0].name == "search"
    assert seen["sglang"] == ("raw", TOOLS, "hermes")


@pytest.mark.asyncio
async def test_tool_call_dispatch_uses_vllm_for_vllm_rollout_with_name_mapping(monkeypatch):
    from uni_agent.gateway.session.codec import MessageCodec

    seen = {}

    def fail_sglang(*args, **kwargs):
        raise AssertionError("SGLang should not run for a vLLM rollout")

    def fake_vllm(text, tools, parser_name):
        seen["vllm"] = (text, tools, parser_name)
        return "", [SimpleNamespace(name="search", arguments='{"query":"x"}')]

    async def fail_verl(*args, **kwargs):
        raise AssertionError("verl should not run when an engine succeeds")

    codec = MessageCodec(FakeTokenizer(), rollout_backend="vllm")
    monkeypatch.setattr(codec, "_process_tool_calls_sglang", fail_sglang)
    monkeypatch.setattr(codec, "_process_tool_calls_vllm", fake_vllm)
    monkeypatch.setattr(codec, "_process_tool_calls_verl", fail_verl)

    content, calls = await codec._extract_tool_calls(_ids("raw"), TOOLS, "qwen25")

    assert content == ""
    assert calls[0].arguments == '{"query":"x"}'
    assert seen["vllm"] == ("raw", TOOLS, "qwen3_xml")


@pytest.mark.asyncio
async def test_tool_call_dispatch_uses_verl_for_other_rollout_backends(monkeypatch):
    from uni_agent.gateway.session.codec import MessageCodec

    seen = {}

    def fail_engine(*args, **kwargs):
        raise AssertionError("engine parser should not run for another rollout backend")

    async def fake_verl(response_ids, tools, parser_name):
        seen["verl"] = (response_ids, tools, parser_name)
        return "thinking", [SimpleNamespace(name="search", arguments='{"query":"docs"}')]

    codec = MessageCodec(FakeTokenizer(), rollout_backend="hf")
    monkeypatch.setattr(codec, "_process_tool_calls_sglang", fail_engine)
    monkeypatch.setattr(codec, "_process_tool_calls_vllm", fail_engine)
    monkeypatch.setattr(codec, "_process_tool_calls_verl", fake_verl)

    text = 'thinking\n<tool_call>\n{"name": "search", "arguments": {"query": "docs"}}\n</tool_call>'
    content, calls = await codec._extract_tool_calls(_ids(text), TOOLS, "hermes")

    assert content == "thinking"
    assert calls[0].name == "search"
    assert seen["verl"] == (_ids(text), TOOLS, "hermes")


@pytest.mark.asyncio
async def test_tool_call_dispatch_surfaces_selected_parser_failure_without_fallback(monkeypatch):
    from uni_agent.gateway.session.codec import MessageCodec

    def broken_vllm(*args, **kwargs):
        raise ModuleNotFoundError("vllm")

    async def fail_verl(*args, **kwargs):
        raise AssertionError("verl must not hide a selected vLLM parser failure")

    codec = MessageCodec(FakeTokenizer(), rollout_backend="vllm")
    monkeypatch.setattr(codec, "_process_tool_calls_vllm", broken_vllm)
    monkeypatch.setattr(codec, "_process_tool_calls_verl", fail_verl)

    with pytest.raises(RuntimeError, match="vllm tool parser 'hermes' failed") as exc_info:
        await codec._extract_tool_calls(_ids("plain text"), TOOLS, "hermes")

    assert isinstance(exc_info.value.__cause__, ModuleNotFoundError)


@pytest.mark.asyncio
async def test_selected_parser_empty_result_is_not_an_error(monkeypatch):
    from uni_agent.gateway.session.codec import MessageCodec

    codec = MessageCodec(FakeTokenizer(), rollout_backend="sglang")
    monkeypatch.setattr(
        codec,
        "_process_tool_calls_sglang",
        lambda text, tools, parser_name: (text, []),
    )

    async def fail_verl(*args, **kwargs):
        raise AssertionError("verl should not run when an engine already answered")

    def fail_vllm(*args, **kwargs):
        raise AssertionError("vLLM should not run when SGLang already answered")

    monkeypatch.setattr(codec, "_process_tool_calls_vllm", fail_vllm)
    monkeypatch.setattr(codec, "_process_tool_calls_verl", fail_verl)

    text = '<tool_call>\n{"name": "search", "arguments": {"query": "docs"}}\n</tool_call>'
    content, calls = await codec._extract_tool_calls(_ids(text), TOOLS, "hermes")

    assert content == text
    assert calls == []


@pytest.mark.asyncio
async def test_verl_parser_parses_hermes_envelope():
    from uni_agent.gateway.session.codec import MessageCodec

    text = 'thinking\n<tool_call>\n{"name": "search", "arguments": {"query": "docs", "limit": 2}}\n</tool_call>'
    content, calls = await MessageCodec(FakeTokenizer())._process_tool_calls_verl(_ids(text), TOOLS, "hermes")

    assert content == "thinking\n"
    assert calls[0].name == "search"
    assert json.loads(calls[0].arguments) == {"query": "docs", "limit": 2}


@pytest.mark.asyncio
async def test_decode_response_uses_gateway_dispatcher_for_tool_calls(monkeypatch):
    from uni_agent.gateway.session.codec import MessageCodec

    seen = {}

    async def fake_dispatch(response_ids, tools, parser_name):
        seen["dispatch"] = (response_ids, tools, parser_name)
        return "", [SimpleNamespace(name="search", arguments='{"query":"weather"}')]

    tokenizer = FakeTokenizer()
    codec = MessageCodec(tokenizer, tool_parser_name="qwen3_xml")
    monkeypatch.setattr(codec, "_extract_tool_calls", fake_dispatch)
    response_ids = [ord(char) for char in "<tool_call>ignored</tool_call>"]
    message, finish_reason = await codec.decode_response(
        response_ids,
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "search",
                    "description": "search docs",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "target": {"anyOf": [{"const": "file"}, {"type": "string"}]},
                        },
                    },
                },
            }
        ],
        stop_reason="stop",
    )

    assert finish_reason == "tool_calls"
    assert message["content"] == ""
    assert message["tool_calls"][0]["type"] == "function"
    assert message["tool_calls"][0]["function"] == {"name": "search", "arguments": '{"query":"weather"}'}
    assert seen["dispatch"][0] == response_ids
    assert seen["dispatch"][2] == "qwen3_xml"


@pytest.mark.asyncio
async def test_decode_response_strips_trailing_stop_token_from_tool_call_content(monkeypatch):
    """The tool-call branch keeps special tokens for <think> handling; the
    closing EOS must not leak into the visible assistant text (it did, and
    clients replayed it as a second EOS inside the turn)."""
    from uni_agent.gateway.session.codec import MessageCodec

    async def fake_dispatch(response_ids, tools, parser_name):
        return "Let me read the file.\n\n<|im_end|>", [SimpleNamespace(name="search", arguments='{"query":"x"}')]

    tokenizer = FakeTokenizer()
    tokenizer.eos_token = "<|im_end|>"
    codec = MessageCodec(tokenizer, tool_parser_name="qwen3_xml")
    monkeypatch.setattr(codec, "_extract_tool_calls", fake_dispatch)
    message, finish_reason = await codec.decode_response(_ids("ignored"), tools=TOOLS, stop_reason="stop")

    assert finish_reason == "tool_calls"
    assert message["content"] == "Let me read the file."
    assert message["tool_calls"][0]["function"]["name"] == "search"


@pytest.mark.asyncio
async def test_decode_response_keeps_tool_call_content_without_stop_token(monkeypatch):
    from uni_agent.gateway.session.codec import MessageCodec

    async def fake_dispatch(response_ids, tools, parser_name):
        return "visible <|im_end|> mid-text", [SimpleNamespace(name="search", arguments="{}")]

    tokenizer = FakeTokenizer()
    tokenizer.eos_token = "<|im_end|>"
    codec = MessageCodec(tokenizer, tool_parser_name="qwen3_xml")
    monkeypatch.setattr(codec, "_extract_tool_calls", fake_dispatch)
    message, _ = await codec.decode_response(_ids("ignored"), tools=TOOLS, stop_reason="stop")
    assert message["content"] == "visible <|im_end|> mid-text"

