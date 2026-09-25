"""#8(iii)（决策包 §8）的溢出 400，一份构造两处用（A→B 接线交接 §6.1 的 A 待办）。

- **capture wire**（正式链）：`rh2_call_sglang_generate` 在引擎调用与 pending 暂存之前判溢出，用 `prompt_too_long_error`
  抛出——不伪造采样、不留 pending、不进 capture。
- **没装 capture wire 的部署**（B 线基座探针的 adapter 进程）：`install_overflow_400_wire()` 给当前
  `slime_common.call_sglang_generate` 包一层，同一判据、同一响应。vendored 自己在溢出时只回 `finish_reason=length` 的空
  输出，CC 2.1.205 拿不到 400 就不会走被动压缩（会追加 "Output token limit hit. Resume directly…" 重发、4 次后退出 1）。

响应形状：HTTP 400、`{"type":"error","error":{"type":"invalid_request_error","message":"prompt is too long: N tokens > M maximum"}}`
（CC 2.1.205 实测认得并压缩后重发）。判据：会话配置了窗口（`max_context_tokens > 0`）且 prompt token 数 ≥ 窗口。
"""

from __future__ import annotations

import json
from typing import Any


def prompt_overflows(prompt_tokens: int, max_context_tokens: int) -> bool:
    return int(max_context_tokens) > 0 and int(max_context_tokens) - int(prompt_tokens) <= 0


def prompt_too_long_body(prompt_tokens: int, max_context_tokens: int) -> dict[str, Any]:
    return {
        "type": "error",
        "error": {
            "type": "invalid_request_error",
            "message": f"prompt is too long: {int(prompt_tokens)} tokens > {int(max_context_tokens)} maximum",
        },
    }


def prompt_too_long_error(prompt_tokens: int, max_context_tokens: int):
    """aiohttp 的 400 异常（在请求处理器里抛出即返回该响应）。"""

    from aiohttp import web as aiohttp_web

    return aiohttp_web.HTTPBadRequest(
        text=json.dumps(prompt_too_long_body(prompt_tokens, max_context_tokens)), content_type="application/json",
    )


def install_overflow_400_wire() -> None:
    """没装 capture wire 的部署：给当前 `slime_common.call_sglang_generate` 包一层，溢出时抛 400。幂等；正式链由 capture wire
    自己判（两者叠装也无害：先判的一层抛出，另一层不会被调用）。"""

    from slime.agent.adapters import common as slime_common

    current = slime_common.call_sglang_generate
    if getattr(current, "_rh2_overflow_400", False):
        return

    async def overflow_checked_call_sglang_generate(prompt_ids, session, body, *, adapter, session_id=None, **kwargs):
        max_context = int(getattr(session, "max_context_tokens", 0) or 0)
        if prompt_overflows(len(prompt_ids), max_context):
            raise prompt_too_long_error(len(prompt_ids), max_context)
        return await current(prompt_ids, session, body, adapter=adapter, session_id=session_id, **kwargs)

    overflow_checked_call_sglang_generate._rh2_overflow_400 = True  # type: ignore[attr-defined]
    slime_common.call_sglang_generate = overflow_checked_call_sglang_generate


def overflow_400_wire_installed() -> bool:
    from slime.agent.adapters import common as slime_common

    return bool(getattr(slime_common.call_sglang_generate, "_rh2_overflow_400", False))
