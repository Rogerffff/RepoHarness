"""aiohttp 1c1c0ea3 的事后诊断（不计入 reward）：Ctrl+C 之后 cleanup_ctx 抛出的错误，是被报告、被抛出，还是被静默丢掉。

背景（第二批主审卡 C3）：run_app 的 finally 先取消主任务；主任务在 cleanup 阶段抛出的错误，
base 交给 loop 的异常处理器报告，gold 改为从 run_app 抛出。候选 C3 用 gather(return_exceptions=True)
取消主任务，错误既不报告也不抛出。隐藏测试没有覆盖这一点，这里单独判定：
- "raised"：run_app 抛出含 "cleanup failed" 的异常；
- "reported"：异常处理器收到含 "cleanup failed" 的异常；
- "lost"：两者都没有。
"raised" 或 "reported" 判通过（不要求与 gold 同一种方式），"lost" 判未通过。输出一行 RH2_POSTCHECK= JSON。
在应用了候选补丁的 /testbed 里、用 /testbed/.venv 的 python 运行。
"""

from __future__ import annotations

import asyncio
import json
import sys


def main() -> int:
    sys.path.insert(0, "/testbed")
    from aiohttp import web

    calls: list[dict] = []

    async def ctx(app):
        yield
        raise RuntimeError("cleanup failed")

    app = web.Application()
    app.cleanup_ctx.append(ctx)
    loop = asyncio.new_event_loop()
    loop.set_exception_handler(lambda lp, c: calls.append({"message": c.get("message"), "exception": repr(c.get("exception"))}))

    def raise_interrupt():
        raise KeyboardInterrupt

    def stopper(*args, **kwargs):
        loop.call_soon(raise_interrupt)

    raised = None
    try:
        web.run_app(app, host="127.0.0.1", port=0, print=stopper, loop=loop)
    except BaseException as exc:  # noqa: BLE001
        raised = f"{type(exc).__name__}: {exc}"
    reported = sum(1 for c in calls if "cleanup failed" in (c["exception"] or ""))
    if raised and "cleanup failed" in raised:
        outcome = "raised"
    elif reported:
        outcome = "reported"
    else:
        outcome = "lost"
    failed = [] if outcome in ("raised", "reported") else ["cleanup_error_lost"]
    print("RH2_POSTCHECK=" + json.dumps({"task": "aiohttp__1c1c0ea3", "verdict": "pass" if not failed else "fail",
                                         "failed": failed, "outcome": outcome, "raised": raised,
                                         "handler_calls": calls}, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
