"""Rh2RolloutLifecycle：miles 迁移的最小关闭面（C7 的 close/dispose seam）。

背景（spike-log R5-ext B5 / blockers §7）：miles `FullyAsyncRolloutFn.
_worker_loop` 是无限后台任务；`RolloutManager.dispose()`（reference/miles/
miles/ray/rollout/rollout_manager.py:131-140）只关 data_source、event
analyzer、metric checker、checkpoint-eval fn 和 health monitor，**从不对
generate_rollout 调 close/dispose**——fully-async worker、在飞组、阻塞中的
buffer put/get 在 miles 侧没有任何关闭接口。这是本地源码已确认的缺口，
不改 miles（红线），由 rh2 侧补一个最小 seam。

挂接方式（dispose 缺口的绕行，不动 miles 一行代码）：本 seam 由 rh2
rollout function 层持有——rh2 自有训练入口（train_async 的 rh2 对应物）在
退出路径显式 `await lifecycle.shutdown()`；需要随 adapter/sandbox 一起收尾
的清理动作经 `register_close_hook()` 注册（例如 vendor AnthropicAdapter 的
drain、docker sandbox 的销毁）。miles 的 `rollout_manager.dispose()` 不会
替我们调它，顺序上应当先 `await lifecycle.shutdown()` 再调 miles dispose。
Ray actor kill 场景（kill 后无孤儿 worker、无账外组）归硬件段验证。

shutdown 语义（最小面，按序四步，幂等）：

1. **停止新 submission**：`spawn()` 立即开始拒绝（LifecycleClosedError）；
2. **cancel 并 await 全部在飞 task**：task 自身的 CancelledError 分支可先
   记账（governed put 的背压 cancel 路径、生产 task 的 crash 分支）——
   `mark_crashed_before_put` 幂等，随后的扫尾不会双记；
3. **三类分别记账**（扫账本而不是扫 task，两层已记的账不重复）：
   - 未入 buffer（DISPATCHED）  -> CRASHED_BEFORE_PUT(kind="shutdown")
   - buffer 内（ADMITTED）      -> RETIRED(reason="shutdown")——组物理上仍
     留在 inner DefaultDataBuffer 里（miles 无移除接口），进程即将退出，
     账面先行清场保证审计一致；
   - 已 handed-off 未回执（HANDED_OFF）-> UNCERTAIN_TRAINED(reason=
     "shutdown_without_receipt")——关停时无法证明 drain 出去的批是否已被
     optimizer 消费，按决策包 v4 at-least-once 语义落 uncertain，绝不伪造
     FINALIZED；
4. **幂等**：第二次调用直接返回第一次的报告对象，不产生任何新转移、
   不再跑 close hook、不抛错。
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Coroutine
from typing import Any

from repoharness2.adapters.miles.attempt_ledger import (
    ADMITTED,
    DISPATCHED,
    HANDED_OFF,
    Rh2AttemptLedger,
)


class LifecycleClosedError(RuntimeError):
    """lifecycle 已进入关闭流程，拒绝新的 submission/注册。"""


class Rh2RolloutLifecycle:
    """rollout function 层持有的最小生命周期面：track 在飞 task + 关闭 seam。"""

    def __init__(self, ledger: Rh2AttemptLedger) -> None:
        self._ledger = ledger
        self._tasks: set[asyncio.Task] = set()
        self._close_hooks: list[Callable[[], Awaitable[None]]] = []
        self._accepting = True
        self._report: dict[str, Any] | None = None

    @property
    def accepting(self) -> bool:
        return self._accepting

    def register_close_hook(self, hook: Callable[[], Awaitable[None]]) -> None:
        """注册关闭时（记账之后）要 await 的清理动作（adapter drain、sandbox 销毁）。"""

        if not self._accepting:
            raise LifecycleClosedError("lifecycle 已关闭，不再接受 close hook 注册")
        self._close_hooks.append(hook)

    def spawn(self, coro: Coroutine[Any, Any, Any]) -> asyncio.Task:
        """提交一个生产 task（dispatch→generate→put 的一次尝试）并纳入 track。"""

        if not self._accepting:
            coro.close()  # 显式释放，避免 un-awaited coroutine 泄漏警告
            raise LifecycleClosedError("lifecycle 已关闭，拒绝新的 rollout submission")
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    async def shutdown(self) -> dict[str, Any]:
        """最小关闭面（语义见模块 docstring）。返回记账报告；幂等。"""

        if self._report is not None:
            return self._report  # 幂等：第二次直接返回首次报告，无新转移无新错误
        self._accepting = False  # 1. 停止新 submission（先于 cancel，防关闭窗口内补位）

        # 2. cancel 并 await 全部在飞 task（return_exceptions：task 的异常/
        #    CancelledError 都不打断关闭流程，账目由第 3 步兜底）。
        in_flight = [t for t in self._tasks if not t.done()]
        for task in in_flight:
            task.cancel()
        if in_flight:
            await asyncio.gather(*in_flight, return_exceptions=True)

        # 3. 三类记账（扫账本；task 层已记的 CRASHED_BEFORE_PUT 不会再出现在
        #    DISPATCHED 里，天然不双记）。
        crashed = sorted(self._ledger.attempts_in_state(DISPATCHED))
        for aid in crashed:
            self._ledger.mark_crashed_before_put(aid, kind="shutdown")
        retired = sorted(self._ledger.attempts_in_state(ADMITTED))
        for aid in retired:
            self._ledger.retire(aid, reason="shutdown")
        uncertain = sorted(self._ledger.attempts_in_state(HANDED_OFF))
        for aid in uncertain:
            self._ledger.mark_uncertain_attempt(aid, reason="shutdown_without_receipt")

        # 收尾清理（adapter/sandbox）；单个 hook 失败不阻断其余 hook，
        # 错误进报告供上层决定是否升级。
        hook_errors: list[str] = []
        for hook in self._close_hooks:
            try:
                await hook()
            except Exception as exc:  # noqa: BLE001 —— 关闭路径收集而非扩散
                hook_errors.append(repr(exc))

        self._report = {
            "cancelled_tasks": len(in_flight),
            "crashed_before_put": crashed,
            "retired_in_buffer": retired,
            "uncertain_trained": uncertain,
            "close_hook_errors": hook_errors,
        }
        return self._report
