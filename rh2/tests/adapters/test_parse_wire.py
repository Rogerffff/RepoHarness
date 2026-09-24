"""#5（T1）：EOS 字面量只从可见末尾剥掉、悬空 <tool_call> 只置 ill_formed；采样 id 不动（wire 根本拿不到 id）。
反例文本取自 B 线探针留证（coder_adapter dask-8597-a2 turns.jsonl 的工具轮与末轮、q36 的纯文本末轮）的真实形状。"""

from __future__ import annotations

import pytest

from repoharness2.adapters.slime import parse_wire as pw

EOS = "<|im_end|>"
TOOLS = [{"type": "function", "function": {"name": "Bash", "parameters": {"type": "object", "properties": {"command": {"type": "string"}}}}},
         {"type": "function", "function": {"name": "Write", "parameters": {"type": "object", "properties": {"file_path": {"type": "string"}}}}}]
TOOL_TURN = ("I'll investigate and fix the issue.\n\nFirst, let me check the current directory:\n\n"
             "<tool_call>\n<function=Bash>\n<parameter=command>\ncd /testbed && ls\n</parameter>\n</function>\n</tool_call>" + EOS)
DANGLING = "I have successfully fixed the issue. Here's a summary of what I did:\n\n## Problem Analysis\n...\n<tool_call>" + EOS
TEXT_END = "The fix reduces the build time, resulting in much faster builds." + EOS
MID_LITERAL = "The token " + EOS + " is the chat terminator; explain it." + EOS


@pytest.fixture(autouse=True)
def _installed(monkeypatch):
    from slime.agent import parsing as slime_parsing
    from slime.agent.adapters import common as slime_common

    monkeypatch.setattr(pw, "_STATE", {"eos": None, "original": None, "stats": {"eos_stripped": 0, "dangling_tool_call": 0}})
    monkeypatch.setattr(slime_common, "parse_model_output", slime_parsing.parse_model_output)
    pw.install_parse_wire(eos_token=EOS)
    pw.assert_parse_wire_installed()
    yield


def _parse(raw: str, tools=TOOLS):
    from slime.agent.adapters import common as slime_common

    return slime_common.parse_model_output(raw, tools_schema=tools, tool_parser_name=None, reasoning_parser_name=None)


def test_tool_call_turn_keeps_the_call_and_loses_only_the_trailing_eos():
    parsed = _parse(TOOL_TURN)
    assert [t["name"] for t in parsed.tool_uses] == ["Bash"] and parsed.tool_uses[0]["input"]["command"] == "cd /testbed && ls"
    assert EOS not in parsed.text and parsed.text.endswith("check the current directory:") and parsed.ill_formed is False


def test_pure_text_end_turn_loses_the_trailing_eos_and_nothing_else():
    parsed = _parse(TEXT_END)
    assert parsed.text == "The fix reduces the build time, resulting in much faster builds." and not parsed.tool_uses and not parsed.ill_formed
    assert pw.parse_wire_stats()["eos_stripped"] == 1


def test_dangling_tool_call_is_flagged_ill_formed_but_text_and_calls_are_untouched():
    parsed = _parse(DANGLING)
    assert parsed.tool_uses == [] and parsed.ill_formed is True
    assert parsed.text.endswith("<tool_call>") and EOS not in parsed.text  # 文本照旧（只剥末尾 EOS），只加事实
    assert pw.parse_wire_stats()["dangling_tool_call"] == 1


def test_literal_in_the_body_is_kept_only_the_visible_end_is_stripped():
    parsed = _parse(MID_LITERAL)
    assert parsed.text == "The token " + EOS + " is the chat terminator; explain it."


def test_no_eos_and_length_finish_shapes_are_untouched():
    parsed = _parse("partial output without terminator")
    assert parsed.text == "partial output without terminator" and pw.parse_wire_stats()["eos_stripped"] == 0
    parsed = _parse("")
    assert parsed.text == "" and parsed.ill_formed is False


def test_install_without_eos_only_flags_dangling_calls_and_is_idempotent():
    pw.install_parse_wire(eos_token=None)
    pw.install_parse_wire(eos_token=None)
    parsed = _parse(TEXT_END)
    assert parsed.text.endswith(EOS)  # 不知道 EOS 字面量就不剥
    assert _parse(DANGLING).ill_formed is True


def test_run_turn_looks_the_wrapper_up_by_module_name():
    import inspect

    from slime.agent.adapters import common as slime_common

    # 全量套件里 turn 预算 wire 可能已把 BaseAdapter._run_turn 换成 rh2_run_turn（原函数留在 _rh2_original_run_turn）；
    # 断言对象是 vendored 原函数：它按模块全局名调用 parse_model_output → 替换模块属性即生效（与 capture wire 同机制）
    vendored = getattr(slime_common, "_rh2_original_run_turn", None) or slime_common.BaseAdapter._run_turn
    src = inspect.getsource(vendored)
    assert "parse_model_output(" in src
    assert slime_common.parse_model_output is pw.rh2_parse_model_output
