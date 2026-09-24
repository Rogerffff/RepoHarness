"""#6(a)（基座探针决策包 §8，2026-09-24 用户批准）：只把**约定的提醒**并入相邻工具结果，其余角色不动。

机制（决策包 §1.2，实测）：CC 在最新 tool_result 之后追加会话中 `role:system` 提醒；vendored fold 把它包成
`<system-reminder>…</system-reminder>` 的 text 块追加到工具结果所在的 user 消息；`_translate_messages` 又把该 text 块拆成
独立的 `role:user`；Qwen3.x 模板把最后一条真实 user 当作新 query，此前所有 assistant 的 thinking 都不再渲染
（74/74 次插入 ↔ 清空）。这里在 fold 之后、翻译之前，把**同一条 user 消息里、紧跟在 tool_result 之后、以
`<system-reminder>` 开头的 text 块**并入该消息最后一个 tool_result 的内容尾部（CC 源码 smooshSystemReminderSiblings
的口径）。普通 user 文本、压缩摘要指令（"CRITICAL: Respond with TEXT ONLY…"，Codex 复核 R2 的反例）、Skill 正文
都保持原角色——不采用 a2，不启用 preserve_thinking。

RH2 层子类（vendored 零改动）：`Rh2AnthropicAdapter._preprocess_body` = vendored fold → smoosh。生成与 count_tokens
共用 `_preprocess_body`，所以计数看到的与生成一致。
"""

from __future__ import annotations

from typing import Any

SYSTEM_REMINDER_PREFIX = "<system-reminder>"


def _is_reminder_text_block(block: Any) -> bool:
    return isinstance(block, dict) and block.get("type") == "text" and str(block.get("text", "")).lstrip().startswith(SYSTEM_REMINDER_PREFIX)


def _append_text_to_tool_result(tool_result: dict, text: str) -> None:
    content = tool_result.get("content")
    if isinstance(content, list):
        content.append({"type": "text", "text": text})
    elif isinstance(content, str) or content is None:
        tool_result["content"] = (content or "") + text
    else:  # 其它形状（dict 等）：不动，避免破坏未知契约
        raise TypeError("unsupported tool_result content shape")


def smoosh_system_reminders_into_last_tool_result(body: dict) -> int:
    """就地修改 body["messages"]；返回并入的提醒块数。只处理 role=user 且 content 为块列表的消息：
    从最后一个 tool_result 之后开始，连续的 reminder text 块并入该 tool_result；遇到第一个非 reminder 块即停（其后
    的块——包括更后面的 reminder——保持原样，避免把普通指令的相对顺序打乱）。"""

    msgs = body.get("messages")
    if not isinstance(msgs, list):
        return 0
    merged = 0
    for msg in msgs:
        if not isinstance(msg, dict) or msg.get("role") != "user" or not isinstance(msg.get("content"), list):
            continue
        blocks = msg["content"]
        last_tr = max((i for i, b in enumerate(blocks) if isinstance(b, dict) and b.get("type") == "tool_result"), default=None)
        if last_tr is None:
            continue
        j = last_tr + 1
        absorbed: list[str] = []
        while j < len(blocks) and _is_reminder_text_block(blocks[j]):
            absorbed.append(str(blocks[j]["text"]))
            j += 1
        if not absorbed:
            continue
        try:
            _append_text_to_tool_result(blocks[last_tr], "".join("\n\n" + t.strip("\n") for t in absorbed))
        except TypeError:
            continue
        del blocks[last_tr + 1:j]
        merged += len(absorbed)
    return merged


_SUBCLASS_CACHE: list[tuple[type, type]] = []  # (当前 vendored 基类, 子类)


def rh2_anthropic_adapter_cls() -> type:
    """生产 adapter 类：**调用时**取当前 vendored `AnthropicAdapter` 再子类化（测试会在模块之间重置 vendored `slime.*`
    模块；模块顶层静态子类化会绑在过期基类上，路由 / turn 预算 wire 的启动核对就会失败——与 bringup 里所有 vendored
    类都延迟导入是同一纪律）。vendored 行为 + #6(a) 的提醒并入；构造顺序与 vendored 相同（先安装各 wire，后构造）。"""

    from slime.agent.adapters.anthropic import AnthropicAdapter

    for base, cls in _SUBCLASS_CACHE:
        if base is AnthropicAdapter:
            return cls

    class Rh2AnthropicAdapter(AnthropicAdapter):
        def _preprocess_body(self, body: dict) -> None:
            super()._preprocess_body(body)  # vendored：会话中 role:system → 前一条 user 的 <system-reminder> text 块
            smoosh_system_reminders_into_last_tool_result(body)

    _SUBCLASS_CACHE.append((AnthropicAdapter, Rh2AnthropicAdapter))
    return Rh2AnthropicAdapter
