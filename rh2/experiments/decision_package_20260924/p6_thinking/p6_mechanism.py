#!/usr/bin/env python3
"""#6 机制核对：用同一份 Qwen3.6 chat_template 渲染几个最小例子，说明 thinking 保留条件。

例子（全部经真实 tokenizer.apply_chat_template 渲染，不手拼字符串）：
  E1 基线：system, user(问题), assistant(think A1 + 工具调用), tool, assistant(think A2 + 工具调用), tool
  E2 = E1 + 末尾追加 role:user "<system-reminder>…"（adapter fold+translate 之后提醒的样子）
  E3 = E1，但提醒并入最后一个 tool 消息内容（候选 (a) 的样子）
  E4 = E2 + preserve_thinking=True（候选 (b)）
  E5 = E1 + 末尾 role:user，内容本身被 <tool_response>…</tool_response> 包住（模板的“不算 query”分支）
  E6 = 直接把 role:system 留在列表中间（不经 adapter fold）→ 模板抛异常
  E7 = 真实请求：moto-5134-a1 seq 11 在不经 fold 时的渲染结果（验证生产若不 fold 会失败）
输出 runs/decision_package_20260924/p6_thinking/mechanism_examples.json。
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "rh2/src"))
OUT = REPO / "runs/decision_package_20260924/p6_thinking"
TOK_DIR = OUT / "hf_tokenizer"


def main() -> None:
    from transformers import AutoTokenizer

    from slime.agent.adapters.anthropic import _translate_messages, _tools_to_chat_tools

    tok = AutoTokenizer.from_pretrained(str(TOK_DIR), trust_remote_code=True)

    def render(msgs, tools=None, **kw):
        text = tok.apply_chat_template(msgs, tools=tools, tokenize=False, add_generation_prompt=True, **kw)
        ids = tok.apply_chat_template(msgs, tools=tools, tokenize=True, add_generation_prompt=True, **kw)
        ids = list(ids["input_ids"] if hasattr(ids, "__getitem__") and "input_ids" in ids else ids)
        return text, len(ids)

    tc = lambda name, **a: {"type": "function", "function": {"name": name, "arguments": a}}  # noqa: E731
    base = [
        {"role": "system", "content": "You are a coding agent."},
        {"role": "user", "content": "Fix the bug in foo.py"},
        {"role": "assistant", "content": "", "reasoning_content": "A1: I should read foo.py first.", "tool_calls": [tc("Read", file_path="foo.py")]},
        {"role": "tool", "content": "def foo(): return 1"},
        {"role": "assistant", "content": "", "reasoning_content": "A2: foo returns 1, should be 2.", "tool_calls": [tc("Edit", file_path="foo.py")]},
        {"role": "tool", "content": "edited"},
    ]
    reminder = "<system-reminder>\nThe task tools haven't been used recently.\n</system-reminder>\n"
    e2 = base + [{"role": "user", "content": reminder}]
    e3 = copy.deepcopy(base)
    e3[-1]["content"] = "edited" + "\n\n" + reminder.strip()
    e5 = base + [{"role": "user", "content": "<tool_response>\nsome output\n</tool_response>"}]

    out: dict = {}
    for name, msgs, kw in [
        ("E1_baseline", base, {}),
        ("E2_reminder_as_user", e2, {}),
        ("E3_reminder_inside_tool", e3, {}),
        ("E4_reminder_as_user_preserve_thinking", e2, {"preserve_thinking": True}),
        ("E5_user_wrapped_tool_response", e5, {}),
    ]:
        text, n = render(msgs, **kw)
        out[name] = {
            "prompt_tokens": n,
            "A1_thinking_rendered": "A1: I should read" in text,
            "A2_thinking_rendered": "A2: foo returns 1" in text,
            "rendered_after_system": text[text.find("<|im_start|>user") :],
        }

    # E6: a mid-list role:system message straight into the template
    e6 = base + [{"role": "system", "content": "The task tools haven't been used recently."}]
    try:
        render(e6)
        out["E6_mid_list_system"] = {"raised": False}
    except Exception as exc:  # noqa: BLE001
        out["E6_mid_list_system"] = {"raised": True, "error_type": type(exc).__name__, "error": str(exc)[:200]}

    # E7: real request (moto-5134-a1 seq 11) translated WITHOUT the adapter's fold
    req = [
        json.loads(l)
        for l in (REPO / "runs/base_probe_20260922/remote/gateway/q36/bp22-qwen3-6-35b-a3b-moto-5134-a1/requests.jsonl")
        .read_text()
        .splitlines()
    ][10]
    assert req["seq"] == 11
    translated = _translate_messages(req["body"]["messages"], req["body"].get("system"))
    tools = _tools_to_chat_tools(req["body"].get("tools"))
    roles = [m["role"] for m in translated]
    try:
        render(translated, tools=tools)
        out["E7_real_request_without_fold"] = {"raised": False, "roles_tail": roles[-6:]}
    except Exception as exc:  # noqa: BLE001
        out["E7_real_request_without_fold"] = {
            "raised": True,
            "error_type": type(exc).__name__,
            "error": str(exc)[:200],
            "system_indices": [i for i, r in enumerate(roles) if r == "system"],
        }

    # the exact template lines that decide thinking retention
    tmpl = tok.chat_template.splitlines()
    keep = [i for i, l in enumerate(tmpl) if "last_query_index" in l or "preserve_thinking" in l or "System message must be" in l
            or "tool_response" in l]
    out["template_lines"] = {str(i + 1): tmpl[i] for i in keep}
    (OUT / "mechanism_examples.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    for k, v in out.items():
        if k == "template_lines":
            continue
        print(k, {kk: vv for kk, vv in v.items() if kk != "rendered_after_system"})


if __name__ == "__main__":
    main()
