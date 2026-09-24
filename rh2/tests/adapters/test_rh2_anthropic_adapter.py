"""决策包 §8 切片 4：#6(a) 只把约定的 <system-reminder> 提醒并入相邻 tool_result，其余角色不动。"""

from __future__ import annotations

import copy
import json

from repoharness2.adapters.slime.rh2_anthropic_adapter import rh2_anthropic_adapter_cls, smoosh_system_reminders_into_last_tool_result

REMINDER = "<system-reminder>\nTask reminder: …\n</system-reminder>\n"
SUMMARY_INSTRUCTION = "CRITICAL: Respond with TEXT ONLY. Do NOT call any tools. Summarize the conversation so far…"


class _Tok:
    def apply_chat_template(self, messages, tools=None, tokenize=True, add_generation_prompt=True, **_kw):
        return [1] * len(messages)

    def decode(self, ids, **_kw):
        return ""


def _adapter():
    return rh2_anthropic_adapter_cls()(tokenizer=_Tok(), sglang_url="http://unused", max_turns_per_sid=3)


def _body(user_blocks, *, mid_system=None):
    msgs = [
        {"role": "user", "content": [{"type": "text", "text": "fix it"}]},
        {"role": "assistant", "content": [{"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "ls"}}]},
        {"role": "user", "content": user_blocks},
    ]
    if mid_system is not None:
        msgs.append({"role": "system", "content": mid_system})
    return {"model": "m", "max_tokens": 8, "messages": msgs}


def test_reminder_after_tool_result_is_merged_into_that_tool_result_and_translated_as_tool_content():
    body = _body([{"type": "tool_result", "tool_use_id": "t1", "content": "out\n"}, {"type": "text", "text": REMINDER}])
    n = smoosh_system_reminders_into_last_tool_result(body)
    blocks = body["messages"][2]["content"]
    assert n == 1 and [b["type"] for b in blocks] == ["tool_result"]
    assert blocks[0]["content"] == "out\n\n\n<system-reminder>\nTask reminder: …\n</system-reminder>"
    translated, _ = _adapter()._translate(body)
    assert [m["role"] for m in translated] == ["user", "assistant", "tool"]  # 没有独立的 role:user 提醒
    assert translated[-1]["content"].endswith("</system-reminder>")


def test_mid_list_system_is_folded_by_vendored_then_merged_by_rh2_preprocess():
    body = _body([{"type": "tool_result", "tool_use_id": "t1", "content": "out"}], mid_system="Task reminder: …")
    adapter = _adapter()
    adapter._preprocess_body(body)  # vendored fold → <system-reminder> text 块 → smoosh
    msgs = body["messages"]
    assert [m["role"] for m in msgs] == ["user", "assistant", "user"] and [b["type"] for b in msgs[2]["content"]] == ["tool_result"]
    assert "<system-reminder>" in msgs[2]["content"][0]["content"]
    translated, _ = adapter._translate(body)
    assert [m["role"] for m in translated] == ["user", "assistant", "tool"]


def test_plain_user_text_summary_instruction_and_skill_body_keep_their_role():
    # Codex 复核 R2 的反例：压缩摘要指令跟在 tool_result 之后，必须仍是独立的 user 指令
    body = _body([{"type": "tool_result", "tool_use_id": "t1", "content": "out"}, {"type": "text", "text": SUMMARY_INSTRUCTION}])
    assert smoosh_system_reminders_into_last_tool_result(body) == 0
    translated, _ = _adapter()._translate(body)
    assert [m["role"] for m in translated] == ["user", "assistant", "tool", "user"] and translated[-1]["content"] == SUMMARY_INSTRUCTION
    # 提醒 + 指令：只并提醒，指令保留；提醒之后的顺序不被打乱
    body = _body([{"type": "tool_result", "tool_use_id": "t1", "content": "out"}, {"type": "text", "text": REMINDER}, {"type": "text", "text": SUMMARY_INSTRUCTION}])
    assert smoosh_system_reminders_into_last_tool_result(body) == 1
    translated, _ = _adapter()._translate(body)
    assert [m["role"] for m in translated] == ["user", "assistant", "tool", "user"] and translated[-1]["content"] == SUMMARY_INSTRUCTION
    assert translated[2]["content"].endswith("</system-reminder>")
    # 指令在前、提醒在后：提醒不越过指令（保持相对顺序），两者都不动
    body = _body([{"type": "tool_result", "tool_use_id": "t1", "content": "out"}, {"type": "text", "text": SUMMARY_INSTRUCTION}, {"type": "text", "text": REMINDER}])
    assert smoosh_system_reminders_into_last_tool_result(body) == 0
    # Skill 正文（非 <system-reminder> 开头的大段 user 文本）：不动
    body = _body([{"type": "tool_result", "tool_use_id": "t1", "content": "out"}, {"type": "text", "text": "# Skill: verify\n…(11k chars)…"}])
    assert smoosh_system_reminders_into_last_tool_result(body) == 0


def test_user_message_without_tool_result_and_list_shaped_tool_result():
    body = {"model": "m", "messages": [{"role": "user", "content": [{"type": "text", "text": REMINDER}]}]}
    assert smoosh_system_reminders_into_last_tool_result(body) == 0  # 没有 tool_result 可并：保持 user
    body = _body([{"type": "tool_result", "tool_use_id": "t1", "content": [{"type": "text", "text": "out"}]}, {"type": "text", "text": REMINDER}])
    assert smoosh_system_reminders_into_last_tool_result(body) == 1
    tr = body["messages"][2]["content"][0]
    assert [b["type"] for b in tr["content"]] == ["text", "text"] and tr["content"][1]["text"].startswith("\n\n<system-reminder>")
    # 两个 tool_result 时只并入最后一个之后的提醒；第一个之后的 text 不动
    body = _body([{"type": "tool_result", "tool_use_id": "t1", "content": "a"}, {"type": "text", "text": REMINDER},
                  {"type": "tool_result", "tool_use_id": "t2", "content": "b"}, {"type": "text", "text": REMINDER}])
    before = copy.deepcopy(body)
    assert smoosh_system_reminders_into_last_tool_result(body) == 1
    blocks = body["messages"][2]["content"]
    assert [b["type"] for b in blocks] == ["tool_result", "text", "tool_result"] and blocks[2]["content"].endswith("</system-reminder>")
    assert blocks[1] == before["messages"][2]["content"][1]


def test_count_tokens_and_generation_share_the_preprocessing():
    """count_tokens wire 调 adapter._preprocess_body → 与生成看到同一形状。"""
    adapter = _adapter()
    body = _body([{"type": "tool_result", "tool_use_id": "t1", "content": "out"}, {"type": "text", "text": REMINDER}])
    seen = json.loads(json.dumps(body))
    adapter._preprocess_body(seen)
    assert [b["type"] for b in seen["messages"][2]["content"]] == ["tool_result"]


def test_subclass_is_rebuilt_on_the_current_vendored_base_class(monkeypatch):
    """vendored 模块被重置（测试隔离）后，工厂返回绑在**当前**基类上的子类；同一基类下缓存复用。"""
    import slime.agent.adapters.anthropic as anthropic_mod

    cls1 = rh2_anthropic_adapter_cls()
    assert cls1 is rh2_anthropic_adapter_cls() and issubclass(cls1, anthropic_mod.AnthropicAdapter)
    fresh_base = type("AnthropicAdapter", (anthropic_mod.AnthropicAdapter,), {})  # 模拟重置后的"新"vendored 类
    monkeypatch.setattr(anthropic_mod, "AnthropicAdapter", fresh_base)
    cls2 = rh2_anthropic_adapter_cls()
    assert cls2 is not cls1 and cls2.__mro__[1] is fresh_base
