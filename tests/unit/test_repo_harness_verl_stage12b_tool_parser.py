from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from repo_harness.rl import LLMGatewayRequest
from repo_harness_verl.gateway import token_output_to_llm_gateway_response
from repo_harness_verl.tool_parser import parse_hermes_tool_calls


@dataclass
class TokenOutputLike:
    token_ids: list[int]
    log_probs: list[float] | None
    stop_reason: str | None = "completed"
    extra_fields: dict[str, Any] = field(default_factory=dict)
    num_preempted: int | None = None
    routed_experts: list[Any] | None = None


class FakeTokenizer:
    def decode(self, ids: list[int], skip_special_tokens: bool = True) -> str:
        return " ".join(f"tok{token_id}" for token_id in ids)


def _request() -> LLMGatewayRequest:
    return LLMGatewayRequest(
        route="verl",
        inference_backend="sglang",
        run_id="run-1",
        task_id="task-1",
        episode_id="episode-1",
        model_call_id="episode-1-turn-0",
        turn=0,
        context_revision=0,
        messages=[{"role": "user", "content": "fix tests"}],
        sampling_params={"temperature": 0.2, "max_tokens": 4},
        sticky_session_id="sticky-episode-1",
    )


def test_stage12b_parser_accepts_read_file_tool_call() -> None:
    parsed = parse_hermes_tool_calls(
        'Before\n<tool_call>\n{"name": "read_file", "arguments": {"path": "calculator.py"}}\n</tool_call>\nAfter',
        turn=3,
    )

    assert parsed.success
    assert parsed.content == "Before\n\nAfter"
    assert parsed.tool_calls == [
        {
            "tool_call_id": "repo_harness_verl_tool_call_3_0",
            "tool_name": "read_file",
            "arguments": {"path": "calculator.py"},
        }
    ]


@pytest.mark.parametrize(
    ("assistant_text", "tool_name"),
    [
        ('<tool_call>{"name": "grep", "arguments": {"query": "divide", "root": "."}}</tool_call>', "grep"),
        (
            '<tool_call>{"name": "edit_file", "arguments": '
            '{"path": "calculator.py", "old_text": "return left / right", "new_text": "return 1"}}</tool_call>',
            "edit_file",
        ),
    ],
)
def test_stage12b_parser_accepts_allowed_tools(assistant_text: str, tool_name: str) -> None:
    parsed = parse_hermes_tool_calls(assistant_text, turn=0)

    assert parsed.success
    assert parsed.tool_calls[0]["tool_name"] == tool_name


def test_stage12b_parser_accepts_final_answer_without_tool_call() -> None:
    parsed = parse_hermes_tool_calls("Final answer: fixed divide.", turn=0)

    assert parsed.success
    assert parsed.content == "Final answer: fixed divide."
    assert parsed.tool_calls == []
    assert parsed.diagnostics == []


def test_stage12b_parser_uses_only_first_tool_call_and_records_diagnostic() -> None:
    parsed = parse_hermes_tool_calls(
        """
<tool_call>{"name": "read_file", "arguments": {"path": "calculator.py"}}</tool_call>
<tool_call>{"name": "git_diff", "arguments": {}}</tool_call>
""",
        turn=1,
    )

    assert parsed.success
    assert [call["tool_name"] for call in parsed.tool_calls] == ["read_file"]
    assert parsed.diagnostics == [
        {
            "category": "ignored_extra_tool_calls",
            "code": "multiple_tool_call_blocks",
            "severity": "warning",
            "ignored_count": 1,
        }
    ]


@pytest.mark.parametrize(
    ("assistant_text", "expected_code"),
    [
        ("<tool_call>{bad json</tool_call>", "invalid_tool_call_json"),
        ('<tool_call>["read_file"]</tool_call>', "tool_call_payload_not_object"),
        ('<tool_call>{"name": "read_file", "arguments": []}</tool_call>', "tool_call_arguments_not_object"),
        ('<tool_call>{"name": "run_tests", "arguments": {}}</tool_call>', "tool_call_unknown_tool_name"),
        ('<tool_call>{"name": "read_file", "arguments": {"path": "/Users/roger/secret.txt"}}</tool_call>', "tool_call_arguments_visibility_rejected"),
        ('<tool_call>{"name": "read_file", "arguments": {"note": "hidden_verifier"}}</tool_call>', "tool_call_arguments_visibility_rejected"),
        ('<tool_call>{"name": "read_file", "arguments": {"groundTruth": "answer"}}</tool_call>', "tool_call_arguments_visibility_rejected"),
        (
            '<tool_call>{"name": "read_file", "arguments": {"reward_extra_info": {"score": 1}}}</tool_call>',
            "tool_call_arguments_visibility_rejected",
        ),
    ],
)
def test_stage12b_parser_rejects_malformed_or_hidden_payloads(
    assistant_text: str,
    expected_code: str,
) -> None:
    parsed = parse_hermes_tool_calls(assistant_text, turn=0)

    assert not parsed.success
    assert parsed.tool_calls == []
    assert parsed.diagnostics[0]["category"] == "model_format_failure"
    assert parsed.diagnostics[0]["code"] == expected_code


def test_stage12b_gateway_parses_real_token_text_without_mutating_token_facts() -> None:
    response = token_output_to_llm_gateway_response(
        TokenOutputLike(
            token_ids=[10, 11, 12],
            log_probs=[-0.1, -0.2, -0.3],
            extra_fields={},
        ),
        request=_request().model_copy(update={"turn": 4}),
        prompt_ids=[1, 2],
        tokenizer=TextTokenizer(
            '<tool_call>{"name": "read_file", "arguments": {"path": "calculator.py"}}</tool_call>'
        ),
        inference_backend="sglang",
        duration_ms=5,
    )

    assert response.assistant_message == {"role": "assistant", "content": ""}
    assert response.tool_calls == [
        {
            "tool_call_id": "repo_harness_verl_tool_call_4_0",
            "tool_name": "read_file",
            "arguments": {"path": "calculator.py"},
        }
    ]
    assert response.output_token_ids == [10, 11, 12]
    assert response.output_logprobs == [-0.1, -0.2, -0.3]
    assert response.response_mask == [1, 1, 1]
    assert "repo_harness_tool_calls" not in response.extra_fields


def test_stage12b_gateway_keeps_parser_failure_as_model_format_diagnostic() -> None:
    response = token_output_to_llm_gateway_response(
        TokenOutputLike(token_ids=[10], log_probs=[-0.1], extra_fields={}),
        request=_request(),
        prompt_ids=[1],
        tokenizer=TextTokenizer("<tool_call>{bad json</tool_call>"),
        inference_backend="sglang",
        duration_ms=5,
    )

    assert response.error is None
    assert response.tool_calls == []
    assert response.extra_fields["repo_harness_tool_parse_error_type"] == "model_format_failure"
    assert response.extra_fields["repo_harness_tool_parse_diagnostics"][0]["code"] == "invalid_tool_call_json"


class TextTokenizer(FakeTokenizer):
    def __init__(self, text: str) -> None:
        self.text = text

    def decode(self, ids: list[int] | Any, skip_special_tokens: bool = True) -> str:
        return self.text
