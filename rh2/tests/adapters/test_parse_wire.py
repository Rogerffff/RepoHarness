"""#5（T1；Codex R1/R2 修订）：EOS 字面量只按"最后一个采样 id 是 EOS"的已发布事实从可见末尾剥一个；悬空 `<tool_call>`
只看解析后可见残余的未闭合片段。采样 id 不动（wire 根本拿不到 id，只拿到事实）。
反例文本取自 B 线探针留证（coder_adapter dask-8597-a2 turns.jsonl 的工具轮与末轮、q36 的纯文本末轮）与 Codex R1/R2 探针。"""

from __future__ import annotations

import pytest

from repoharness2.adapters.slime import parse_wire as pw

EOS = "<|im_end|>"
EOS_ID = 151645
TOOLS = [{"type": "function", "function": {"name": "Bash", "parameters": {"type": "object", "properties": {"command": {"type": "string"}}}}},
         {"type": "function", "function": {"name": "Write", "parameters": {"type": "object", "properties": {"file_path": {"type": "string"}}}}}]
BASH_CALL = "<tool_call>\n<function=Bash>\n<parameter=command>\ncd /testbed && ls\n</parameter>\n</function>\n</tool_call>"
TOOL_TURN = "I'll investigate and fix the issue.\n\nFirst, let me check the current directory:\n\n" + BASH_CALL + EOS
DANGLING = "I have successfully fixed the issue. Here's a summary of what I did:\n\n## Problem Analysis\n...\n<tool_call>" + EOS
TEXT_END = "The fix reduces the build time, resulting in much faster builds." + EOS
MID_LITERAL = "The token " + EOS + " is the chat terminator; explain it." + EOS
SPELLED_LITERAL = "The token is " + EOS  # Codex R1：普通 token 拼出的同名字面量，finish=length，末尾 id 不是 EOS


@pytest.fixture(autouse=True)
def _installed(monkeypatch):
    from slime.agent import parsing as slime_parsing
    from slime.agent.adapters import common as slime_common

    monkeypatch.setattr(pw, "_STATE", {"eos": None, "eos_id": None, "original": None,
                                       "stats": {"eos_stripped": 0, "eos_literal_kept": 0, "eos_fact_missing": 0, "dangling_tool_call": 0}})
    monkeypatch.setattr(slime_common, "parse_model_output", slime_parsing.parse_model_output)
    pw.TURN_TERMINAL.set(None)
    pw.install_parse_wire(eos_token=EOS, eos_token_id=EOS_ID)
    pw.assert_parse_wire_installed()
    yield
    pw.TURN_TERMINAL.set(None)


def _parse(raw: str, *, ids=None, finish="stop", tools=TOOLS):
    """ids=None = 不发布事实（没装发布器的路径）；否则先按 ids 发布再解析。"""
    from slime.agent.adapters import common as slime_common

    if ids is not None:
        pw.publish_turn_terminal(ids, finish)
    return slime_common.parse_model_output(raw, tools_schema=tools, tool_parser_name=None, reasoning_parser_name=None)


REAL_EOS = [11, 22, EOS_ID]
NO_EOS = [11, 22, 33]


# ---- R1：字面量只按采样事实剥 ---------------------------------------------------------------------------------------------


def test_tool_call_turn_with_real_eos_keeps_the_call_and_loses_only_the_trailing_literal():
    parsed = _parse(TOOL_TURN, ids=REAL_EOS)
    assert [t["name"] for t in parsed.tool_uses] == ["Bash"] and parsed.tool_uses[0]["input"]["command"] == "cd /testbed && ls"
    assert EOS not in parsed.text and parsed.ill_formed is False
    assert pw.parse_wire_stats()["eos_stripped"] == 1


def test_spelled_out_literal_from_ordinary_tokens_stays_in_the_text():
    parsed = _parse(SPELLED_LITERAL, ids=NO_EOS, finish="length")
    assert parsed.text == SPELLED_LITERAL and parsed.ill_formed is False
    assert pw.parse_wire_stats() == {"eos_stripped": 0, "eos_literal_kept": 1, "eos_fact_missing": 0, "dangling_tool_call": 0}


def test_without_a_published_fact_nothing_is_stripped_and_it_is_counted():
    parsed = _parse(TEXT_END, ids=None)
    assert parsed.text == TEXT_END
    assert pw.parse_wire_stats()["eos_fact_missing"] == 1 and pw.parse_wire_stats()["eos_stripped"] == 0


def test_text_end_with_real_eos_is_stripped_and_only_the_last_literal_goes():
    assert _parse(TEXT_END, ids=REAL_EOS).text == TEXT_END[: -len(EOS)]
    parsed = _parse(MID_LITERAL, ids=REAL_EOS)
    assert parsed.text == "The token " + EOS + " is the chat terminator; explain it."
    assert pw.parse_wire_stats()["eos_stripped"] == 2


def test_the_fact_is_consumed_once_and_empty_or_unknown_eos_id_never_strips():
    _parse(TEXT_END, ids=REAL_EOS)
    assert _parse(TEXT_END, ids=None).text == TEXT_END  # 上一轮的事实不串到下一轮
    assert pw.parse_wire_stats()["eos_fact_missing"] == 1
    pw.install_parse_wire(eos_token=EOS, eos_token_id=None)  # 没配 id → 事实 eos_last=None → 不剥
    assert _parse(TEXT_END, ids=REAL_EOS).text == TEXT_END
    assert _parse("plain text", ids=[]).text == "plain text"


# ---- R2：悬空调用只看解析后的可见残余 -------------------------------------------------------------------------------------


def test_prose_mentioning_the_tag_is_not_ill_formed():
    parsed = _parse("Use the literal tag <tool_call> in a parser test." + EOS, ids=REAL_EOS)
    assert parsed.ill_formed is False and parsed.tool_uses == []
    assert pw.parse_wire_stats()["dangling_tool_call"] == 0


def test_complete_call_followed_by_a_dangling_fragment_is_ill_formed_but_keeps_the_call():
    parsed = _parse("Running it:\n" + BASH_CALL + "\n<tool_call>" + EOS, ids=REAL_EOS)
    assert [t["name"] for t in parsed.tool_uses] == ["Bash"] and parsed.ill_formed is True


@pytest.mark.parametrize("raw", [
    DANGLING,
    "Let me write it.\n<tool_call>\n<function=Write>\n<parameter=file_path>/tmp/x" + EOS,  # XML 片段未闭合
    "Let me write it.\n<tool_call>\n{\"name\": \"Bash\", \"arguments\": {" + EOS,             # JSON 片段未闭合
])
def test_dangling_fragments_set_only_the_ill_formed_fact(raw):
    parsed = _parse(raw, ids=REAL_EOS)
    assert parsed.ill_formed is True and parsed.tool_uses == []
    assert parsed.text.startswith(raw.split("<tool_call>")[0].strip()[:10])  # 文本保留，不纠正动作
    assert pw.parse_wire_stats()["dangling_tool_call"] == 1


def test_plain_text_and_no_eos_are_untouched():
    parsed = _parse("no terminator here", ids=NO_EOS, finish="length")
    assert parsed.text == "no terminator here" and parsed.ill_formed is False
    assert pw.parse_wire_stats() == {"eos_stripped": 0, "eos_literal_kept": 0, "eos_fact_missing": 0, "dangling_tool_call": 0}


# ---- 挂接与发布器 -----------------------------------------------------------------------------------------------------


def test_assert_fails_when_not_installed(monkeypatch):
    from slime.agent import parsing as slime_parsing
    from slime.agent.adapters import common as slime_common

    monkeypatch.setattr(slime_common, "parse_model_output", slime_parsing.parse_model_output)
    with pytest.raises(RuntimeError, match="parse wire 未安装"):
        pw.assert_parse_wire_installed()


def test_run_turn_looks_the_wrapper_up_by_module_name():
    import inspect

    from slime.agent.adapters import common as slime_common

    # 全量套件里 turn 预算 wire 可能已把 BaseAdapter._run_turn 换成 rh2_run_turn（原函数留在 _rh2_original_run_turn）；
    # 断言对象是 vendored 原函数：它按模块全局名调用 parse_model_output → 替换模块属性即生效（与 capture wire 同机制）
    vendored = getattr(slime_common, "_rh2_original_run_turn", None) or slime_common.BaseAdapter._run_turn
    src = inspect.getsource(vendored)
    assert "parse_model_output(" in src and "call_sglang_generate(" in src
    assert slime_common.parse_model_output is pw.rh2_parse_model_output


async def test_publisher_wraps_the_current_generate_and_publishes_in_the_same_task(monkeypatch):
    from slime.agent.adapters import common as slime_common
    from slime.agent.trajectory import TurnRecord

    async def fake_generate(prompt_ids, session, body, *, adapter, session_id):  # noqa: ARG001
        return TurnRecord(prompt_ids=list(prompt_ids), output_ids=[5, EOS_ID], finish_reason="stop")

    monkeypatch.setattr(slime_common, "call_sglang_generate", fake_generate)
    pw.install_turn_terminal_publisher()
    pw.install_turn_terminal_publisher()  # 幂等
    turn = await slime_common.call_sglang_generate([1], None, {}, adapter=None, session_id="s")
    assert turn.output_ids == [5, EOS_ID]
    assert pw.TURN_TERMINAL.get() == {"last_id": EOS_ID, "eos_last": True, "finish": "stop"}
    assert _parse(TEXT_END).text == TEXT_END[: -len(EOS)]  # 解析取走事实
    assert pw.TURN_TERMINAL.get() is None
