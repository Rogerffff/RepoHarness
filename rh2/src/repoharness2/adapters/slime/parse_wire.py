"""#5（基座探针交接包 §9；T1；第六组 README §8.1 第 2 条与 review_next_slices R1/R2 的口径）：
可见末尾的 EOS 字面量与悬空 `<tool_call>`。

事实：capture wire 复用 vendored `_sampling_params`（`skip_special_tokens=False`、`no_stop_trim=True`），模型的 EOS
token 以字面量留在 decode 出的 `raw_output` 末尾；vendored `parse_model_output` 只 `.strip()`。但普通 token 也能拼出同一个
字面量（Codex R1 探针：`The token is <|im_end|>` 全序列不含 EOS id、finish=length）——字符串本身证明不了它是终止 token。

修法（只改可见文本与 `ill_formed` 事实；采样 id / logprob / mask / capture 原样）：
- **真实 EOS 事实**由产出 `TurnRecord` 的一方在 `_run_turn` 的任务上下文里发布（`publish_turn_terminal`：最后一个采样 id
  是否等于服务 tokenizer 的 `eos_token_id`）。生产由 capture wire 的 `rh2_call_sglang_generate` 发布；探针 / 没装 capture
  wire 的部署用 `install_turn_terminal_publisher()` 包一层当前的 `call_sglang_generate`。包装解析器只在事实说"最后一个 id
  是 EOS"时剥掉可见末尾的那一个字面量；没有事实（fail-closed）或最后一个 id 不是 EOS 时原样保留，分别计数。
- 悬空调用（R2）只看**解析后的可见残余**：最后一个 `<tool_call>` 之后没有 `</tool_call>`，且其后内容为空或以已支持的调用
  语法开头（XML `<function=` / JSON `{`）→ `ill_formed=True`。正文里提到标签、后面跟普通文字不算；已解析出有效调用也不掩盖
  其后的悬空片段。若解析器吞掉了片段（可见残余里没有标签），再对去掉 reasoning 的原文用同一规则。覆盖范围就是这两种形态，
  不宣称完整坏调用检测。只是事实：不拒样、不改 reward、不纠正动作。

挂接：`slime.agent.adapters.common._run_turn` 按模块名调用 `parse_model_output`——替换 `slime_common.parse_model_output`
（vendored 零改动）。事实用 ContextVar 传递：`call_sglang_generate` → decode → `parse_model_output` 在同一任务里顺序执行，
解析时取走并清空（一次性，不串到下一轮）。
"""

from __future__ import annotations

import contextvars
import dataclasses
from typing import Any

_TOOL_CALL_OPEN = "<tool_call>"
_TOOL_CALL_CLOSE = "</tool_call>"
_THINK_CLOSE = "</think>"
_STATE: dict[str, Any] = {
    "eos": None,
    "eos_id": None,
    "original": None,
    "stats": {"eos_stripped": 0, "eos_literal_kept": 0, "eos_fact_missing": 0, "dangling_tool_call": 0},
}
TURN_TERMINAL: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar("rh2_turn_terminal", default=None)


def publish_turn_terminal(output_ids: Any, finish_reason: Any) -> dict[str, Any]:
    """产出 TurnRecord 的一方调用：记录"最后一个采样 id 是否 EOS"。`eos_id` 未配置或没有输出 → `eos_last=None`（不剥）。"""

    ids = list(output_ids or [])
    last = ids[-1] if ids else None
    eos_id = _STATE["eos_id"]
    eos_last = (last == eos_id) if (eos_id is not None and last is not None) else None
    fact = {"last_id": last, "eos_last": eos_last, "finish": finish_reason}
    TURN_TERMINAL.set(fact)
    return fact


def _take_turn_terminal() -> dict[str, Any] | None:
    fact = TURN_TERMINAL.get()
    TURN_TERMINAL.set(None)
    return fact


def _strip_trailing_eos(raw: str, eos: str, fact: dict[str, Any] | None) -> tuple[str, str]:
    body = raw.rstrip()
    if not eos or not body.endswith(eos):
        return raw, "no_literal"
    if fact is None or fact.get("eos_last") is None:
        return raw, "eos_fact_missing"  # fail-closed：没有采样事实就不剥
    if fact["eos_last"]:
        return body[: -len(eos)], "eos_stripped"
    return raw, "eos_literal_kept"  # 普通 token 拼出的同名字面量：属于正文


def _dangling_tool_call(text: str) -> bool:
    """最后一个 `<tool_call>` 之后没有闭合，且其后为空或以已支持的调用语法开头。"""

    i = text.rfind(_TOOL_CALL_OPEN)
    if i < 0:
        return False
    tail = text[i + len(_TOOL_CALL_OPEN) :]
    if _TOOL_CALL_CLOSE in tail:
        return False
    t = tail.strip()
    return t == "" or t.startswith("<function=") or t.startswith("{")


def rh2_parse_model_output(raw_output: str, *, tools_schema, tool_parser_name, reasoning_parser_name):
    original = _STATE["original"]
    stats = _STATE["stats"]
    fact = _take_turn_terminal()
    text, state = _strip_trailing_eos(raw_output or "", _STATE["eos"] or "", fact)
    if state != "no_literal":
        stats[state] += 1
    parsed = original(text, tools_schema=tools_schema, tool_parser_name=tool_parser_name, reasoning_parser_name=reasoning_parser_name)
    if not parsed.ill_formed:
        body = text.split(_THINK_CLOSE, 1)[-1] if _THINK_CLOSE in text else text
        visible = parsed.text or ""
        if _dangling_tool_call(visible) or (_TOOL_CALL_OPEN not in visible and _dangling_tool_call(body)):
            parsed = dataclasses.replace(parsed, ill_formed=True)
            stats["dangling_tool_call"] += 1
    return parsed


def install_parse_wire(*, eos_token: str | None, eos_token_id: int | None = None) -> None:
    """把 `slime_common.parse_model_output` 换成包装；幂等。`eos_token` / `eos_token_id` 取当前服务 tokenizer 的同一对值
    （任一缺失 = 不剥字面量，只做悬空调用标记）。"""

    from slime.agent import parsing as slime_parsing
    from slime.agent.adapters import common as slime_common

    if _STATE["original"] is None:
        _STATE["original"] = slime_parsing.parse_model_output
    _STATE["eos"] = eos_token or None
    _STATE["eos_id"] = int(eos_token_id) if eos_token_id is not None else None
    slime_common.parse_model_output = rh2_parse_model_output


def install_turn_terminal_publisher() -> None:
    """没装 capture wire 的部署（探针）：给当前 `slime_common.call_sglang_generate` 包一层，返回 TurnRecord 前发布事实。
    幂等；生产链由 capture wire 直接发布，不需要这个。"""

    from slime.agent.adapters import common as slime_common

    current = slime_common.call_sglang_generate
    if getattr(current, "_rh2_terminal_publisher", False):
        return

    async def publishing_call_sglang_generate(*args, **kwargs):
        turn = await current(*args, **kwargs)
        publish_turn_terminal(getattr(turn, "output_ids", None), getattr(turn, "finish_reason", None))
        return turn

    publishing_call_sglang_generate._rh2_terminal_publisher = True  # type: ignore[attr-defined]
    slime_common.call_sglang_generate = publishing_call_sglang_generate


def assert_parse_wire_installed() -> None:
    from slime.agent.adapters import common as slime_common

    if getattr(slime_common, "parse_model_output", None) is not rh2_parse_model_output:
        raise RuntimeError("parse wire 未安装：slime_common.parse_model_output 不是 rh2_parse_model_output（#5 未生效）。")


def parse_wire_stats() -> dict[str, int]:
    return dict(_STATE["stats"])
