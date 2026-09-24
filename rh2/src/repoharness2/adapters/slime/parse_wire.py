"""#5（基座探针交接包 §9；T1，Codex 第六组 README §8.1 第 2 条的口径）：`<|im_end|>` 进 content 与悬空 `<tool_call>`。

事实：capture wire 复用 vendored `_sampling_params`（`skip_special_tokens=False`、`no_stop_trim=True`），所以模型的 EOS
token 以字面量留在 decode 出的 `raw_output` 末尾；vendored `parse_model_output` 只 `.strip()`，`ill_formed` 只在 JSON 解析
失败时置位。B 线探针 44 条自部署里 33 个无工具调用的末轮有 32 个把 `<|im_end|>` 字面量交给了 CC；1 个悬空调用
（原始输出以 `<tool_call><|im_end|>` 结束）被解析器丢掉、按 end_turn 收尾而 `ill_formed=False`。

修法（只改可见文本与 `ill_formed` 事实；采样 id / logprob / mask / capture 原样）：
- 只剥**可见末尾**的一个真实终止 token 字面量（当前服务 tokenizer 的 `eos_token`）；正文中间的同名字面量不动。
  `no_stop_trim` 下末尾字面量只来自 EOS token 本身，等价于"finish=stop 且最后一个 token 是 EOS"。
- 原始输出含 `<tool_call>` 却没解析出任何调用 → `ill_formed=True`。这只是事实（进 vendored `TurnRecord.ill_formed`
  与 to_sample 的 metadata），不新增拒样、不改 reward、不纠正动作。

挂接：`slime.agent.adapters.common._run_turn` 按模块名调用 `parse_model_output`，与 capture wire 替换
`call_sglang_generate` 同一机制——把 `slime_common.parse_model_output` 换成本模块的包装（调用时查找，安装顺序无关；
bringup 仍"先安装后构造"），vendored 零改动。
"""

from __future__ import annotations

import dataclasses
from typing import Any

_TOOL_CALL_OPEN = "<tool_call>"
_STATE: dict[str, Any] = {"eos": None, "original": None, "stats": {"eos_stripped": 0, "dangling_tool_call": 0}}


def _strip_trailing_eos(raw: str, eos: str) -> tuple[str, bool]:
    body = raw.rstrip()
    if eos and body.endswith(eos):
        return body[: -len(eos)], True
    return raw, False


def rh2_parse_model_output(raw_output: str, *, tools_schema, tool_parser_name, reasoning_parser_name):
    original = _STATE["original"]
    eos = _STATE["eos"] or ""
    text, stripped = _strip_trailing_eos(raw_output or "", eos)
    parsed = original(text, tools_schema=tools_schema, tool_parser_name=tool_parser_name, reasoning_parser_name=reasoning_parser_name)
    if stripped:
        _STATE["stats"]["eos_stripped"] += 1
    if _TOOL_CALL_OPEN in (raw_output or "") and not parsed.tool_uses and not parsed.ill_formed:
        parsed = dataclasses.replace(parsed, ill_formed=True)
        _STATE["stats"]["dangling_tool_call"] += 1
    return parsed


def install_parse_wire(*, eos_token: str | None) -> None:
    """把 `slime_common.parse_model_output` 换成包装；幂等；`eos_token` 取当前服务 tokenizer 的 `eos_token`
    （None / 空 = 不剥字面量，只做悬空调用标记）。"""

    from slime.agent import parsing as slime_parsing
    from slime.agent.adapters import common as slime_common

    if _STATE["original"] is None:
        _STATE["original"] = slime_parsing.parse_model_output
    _STATE["eos"] = eos_token or None
    slime_common.parse_model_output = rh2_parse_model_output


def assert_parse_wire_installed() -> None:
    from slime.agent.adapters import common as slime_common

    if getattr(slime_common, "parse_model_output", None) is not rh2_parse_model_output:
        raise RuntimeError("parse wire 未安装：slime_common.parse_model_output 不是 rh2_parse_model_output（#5 未生效）。")


def parse_wire_stats() -> dict[str, int]:
    return dict(_STATE["stats"])
