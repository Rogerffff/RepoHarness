"""#8(i)（基座探针决策包 §8，2026-09-24 用户批准；Codex §14.3 同意先做的 T1）：`/v1/messages/count_tokens` 回真实计数。

vendored `slime.agent.adapters.anthropic._count_tokens` 恒回 0（注释称"每轮都调、只作提示"）；实测 CC 2.1.205
只在整文件 Read 且自估超过上限 1/4 时调用它，回 0 让 25,000 token 的 Read 上限失效（超限内容整段进入工具结果）。
这里用**当前服务的 tokenizer、消息处理与模板**——与生成同一路径（`_preprocess_body` → `_translate` →
`_render_token_ids`）——计数；不建生成轮、不进 capture、不计 turn 预算（不经 `_run_turn`）。

安装方式与 `install_capture_wire` 相同：**先安装、后构造** adapter——vendored 构造器在 `__init__` 里按模块名把
`_count_tokens` 函数对象登记成路由，后装无效；`bind_count_tokens_adapter` 在构造后把 adapter 挂到 app 上供
handler 取 tokenizer；`assert_count_tokens_bound` 是启动核对（顺序被改回时 typed 停止）。
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from aiohttp import web

RH2_ADAPTER_APP_KEY: web.AppKey[Any] = web.AppKey("rh2_count_tokens_adapter", object)
COUNT_TOKENS_PATH = "/v1/messages/count_tokens"


def _error(status: int, message: str) -> web.Response:
    body = {"type": "error", "error": {"type": "invalid_request_error", "message": message[:400]}}
    return web.json_response(body, status=status)


async def rh2_count_tokens(request: web.Request) -> web.Response:
    """真实计数：与 `_run_turn` 前半段同一路径（预处理 fold → 翻译 → 模板渲染），在执行器线程里跑 tokenizer。"""

    adapter = request.app.get(RH2_ADAPTER_APP_KEY)
    if adapter is None:
        return _error(500, "count_tokens wire unbound: adapter not attached to app (bind_count_tokens_adapter)")
    try:
        body = await request.json()
    except Exception as exc:  # noqa: BLE001 - 客户端错误
        return _error(400, f"count_tokens: invalid JSON body ({type(exc).__name__})")
    if not isinstance(body, dict):
        return _error(400, "count_tokens: body must be an object")

    def count() -> int:
        from slime.agent.adapters.common import _render_token_ids

        adapter._preprocess_body(body)
        translated, tools_schema = adapter._translate(body)
        return len(_render_token_ids(translated, adapter.tokenizer, tools=tools_schema, add_generation_prompt=True))

    try:
        n = await asyncio.get_running_loop().run_in_executor(None, count)
    except Exception as exc:  # noqa: BLE001 - 模板 / tokenizer 拒绝该消息形状：报给客户端，不影响会话
        return _error(400, f"count_tokens: {type(exc).__name__}: {exc}")
    return web.json_response({"input_tokens": int(n)})


def install_count_tokens_wire() -> None:
    """把 vendored 模块级 `_count_tokens` 换成 RH2 handler。幂等；必须在构造 AnthropicAdapter 之前调用。"""

    import slime.agent.adapters.anthropic as anthropic_mod

    if getattr(anthropic_mod, "_count_tokens", None) is rh2_count_tokens:
        return
    anthropic_mod._count_tokens = rh2_count_tokens


def bind_count_tokens_adapter(adapter: Any) -> None:
    """构造后把 adapter 挂到它自己的 app 上（handler 由此取 tokenizer / 预处理 / 翻译），并做启动核对。"""

    adapter.app[RH2_ADAPTER_APP_KEY] = adapter
    assert_count_tokens_bound(adapter.app)


def assert_count_tokens_bound(app: web.Application) -> None:
    """启动核对：POST count_tokens 路由绑的必须是 rh2_count_tokens，且 app 上已挂 adapter。"""

    routes = [r for r in app.router.routes() if r.method == "POST" and getattr(r.resource, "canonical", None) == COUNT_TOKENS_PATH]
    if not routes:
        raise RuntimeError(f"adapter app 没有 POST {COUNT_TOKENS_PATH} 路由。")
    for route in routes:
        if route.handler is not rh2_count_tokens:
            name = getattr(route.handler, "__name__", type(route.handler).__name__)
            raise RuntimeError(
                f"POST {COUNT_TOKENS_PATH} 绑定的 handler 不是 rh2_count_tokens（路由持有 {name}）——adapter 在"
                " install_count_tokens_wire 之前构造，count_tokens 仍恒回 0。"
            )
    if app.get(RH2_ADAPTER_APP_KEY) is None:
        raise RuntimeError("count_tokens wire 未绑定 adapter（bind_count_tokens_adapter 未调用）。")


def count_tokens_error_body(text: str) -> dict:
    """测试 / 诊断用：解析本模块的错误体。"""

    return json.loads(text)
