"""W10（决策包 D2+B v2 B-5b）：MilesRouter worker 池的 rh2 侧客户端——rid 级 abort **广播**。

为什么需要它（代码事实，integration tree `reference/miles-rh2-integration`）：

- rh2 的采样请求平面经 `--use-miles-router` 起的 MilesRouter（`miles/router/router.py`）。
  它只有两条显式路由 `POST /add_worker`、`GET /list_workers`，其余一切路径落 catch-all
  `/{path:path}` → `do_proxy`：**每个 HTTP 请求独立**取"活跃请求数最小"的 worker
  （`_use_url`），既不读 `X-SMG-Routing-Key`，也不记 rid → worker 的归属。
- 因此 capture wire 在 cancel/超时后发的 `POST /abort_request {"rid": ...}` 若经 router
  单发，只有 1/N 概率落到真正持有该 rid 的 engine；错发时 SGLang 对不认识的 rid 静默无操作、
  router 照样 200——被放弃的生成继续占 engine 槽位直到自然完成（容量泄漏，非样本偏置）。
  单 engine 下该问题结构性不存在，这正是此前把 engine 数钉死为 1 的原因；B-5b 裁定该钉死
  不得转为正式资格语义。
- miles 自己的 rollout abort（`miles/rollout/inference_rollout/inference_rollout_train.py`
  `abort` → `get_worker_urls`）就是"问 router `/list_workers` 拿全部 worker，**绕过 router**
  逐 worker 直发 `{"abort_all": true}`"。本模块照同一形状做 **rid 级**广播：每个 worker
  都收到同一个 rid，持有者终止，其余 worker 忽略（SGLang 语义），幂等安全。

刻意不做（B-5b 明示，首版）：rid → worker 粘滞表、`X-SMG-Routing-Key` 定向路由、
dead-engine 回池、`/remove_worker` 弹性回收——任一 engine 死亡 = 停 run 按 B-3 重启。

worker 列表形状（与 miles `get_worker_urls` 双形态对齐，不依赖 sglang_router 版本号）：
MilesRouter / 旧 sgl-router（<=0.2.1）`GET /list_workers` → `{"urls": [...]}`；
新 sgl-router `GET /workers` → `{"workers": [{"url": ...}, ...]}`。URL 规整
（去 `@<rank>` 后缀 + 去重）镜像 `miles.utils.http_utils.router_worker_base_urls`
（本包不 import miles：`repoharness2.adapters.slime` 的 import 面必须零 miles 依赖）。
"""

from __future__ import annotations

import asyncio
import dataclasses
import logging
from typing import Any

import aiohttp

logger = logging.getLogger("rh2.engine_router_client")


def worker_base_urls(urls: list[str]) -> list[str]:
    """镜像 miles `router_worker_base_urls`：去掉 dp-aware 路由加的 `@<rank>` 后缀，
    同一 engine 的多个 rank 合并为一个地址；保持首次出现顺序。"""

    bases: list[str] = []
    for url in urls:
        base, sep, rank = str(url).rpartition("@")
        if sep and rank.isdigit():
            url = base
        if url not in bases:
            bases.append(url)
    return bases


@dataclasses.dataclass(frozen=True)
class AbortBroadcastResult:
    """一次 rid abort 的投递事实（不抛异常，交调用方记账/打印）。

    - ``mode``：``"broadcast"`` = 已从 router 取到 worker 列表并逐 worker 直发；
      ``"router_single_send"`` = worker 列表取不到（非 MilesRouter / router 不可达），退回
      stock 形状经 router 单发——**只在单 worker 池下语义正确**，多 engine 下可能错发。
    - ``delivered``：HTTP 2xx 的 worker；``failed``：worker → 错误摘要。
    """

    rid: str
    mode: str
    workers: tuple[str, ...]
    delivered: tuple[str, ...]
    failed: dict[str, str]
    list_error: str | None = None

    @property
    def fully_delivered(self) -> bool:
        return self.mode == "broadcast" and not self.failed and bool(self.workers)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rid": self.rid,
            "mode": self.mode,
            "workers": list(self.workers),
            "delivered": list(self.delivered),
            "failed": dict(self.failed),
            "list_error": self.list_error,
            "fully_delivered": self.fully_delivered,
        }


class MilesRouterWorkerClient:
    """router 地址（`http://{sglang_router_ip}:{sglang_router_port}`）上的 worker 池只读视图
    + rid 级 abort 广播。无状态：每次广播都重新取 worker 列表（与 miles abort 同款；abort
    只发生在 cancel/超时路径，不在采样热路径）。"""

    def __init__(
        self,
        router_url: str,
        *,
        list_timeout_seconds: float = 5.0,
        abort_timeout_seconds: float = 5.0,
    ) -> None:
        self.router_url = router_url.rstrip("/")
        self._list_timeout = float(list_timeout_seconds)
        self._abort_timeout = float(abort_timeout_seconds)

    async def list_workers(self) -> list[str]:
        """全部已注册 worker 的 base URL（规整后）。取不到即抛 RuntimeError（调用方决定处置）。"""

        timeout = aiohttp.ClientTimeout(total=self._list_timeout)
        async with aiohttp.ClientSession(timeout=timeout) as sess:
            async with sess.get(f"{self.router_url}/list_workers") as r:
                if r.status == 200:
                    body = await r.json(content_type=None)
                    urls = body.get("urls") if isinstance(body, dict) else None
                    if not isinstance(urls, list):
                        raise RuntimeError(f"/list_workers 返回体缺 urls 列表：{str(body)[:200]}")
                    return worker_base_urls([str(u) for u in urls])
                first_status = r.status
            # 新 sgl-router 形态（miles get_worker_urls 的另一分支）
            async with sess.get(f"{self.router_url}/workers") as r:
                if r.status == 200:
                    body = await r.json(content_type=None)
                    workers = body.get("workers") if isinstance(body, dict) else None
                    if not isinstance(workers, list):
                        raise RuntimeError(f"/workers 返回体缺 workers 列表：{str(body)[:200]}")
                    return worker_base_urls([str(w.get("url")) for w in workers if isinstance(w, dict)])
                raise RuntimeError(
                    f"router 不提供 worker 列表：/list_workers -> {first_status}，/workers -> {r.status}"
                )

    async def _post_abort(self, sess: aiohttp.ClientSession, url: str, rid: str) -> None:
        async with sess.post(f"{url}/abort_request", json={"rid": rid}) as r:
            if r.status >= 400:
                text = await r.text()
                raise RuntimeError(f"HTTP {r.status}: {text[:200]}")

    async def broadcast_abort(self, rid: str) -> AbortBroadcastResult:
        """对全部 worker 广播同一 rid 的 `/abort_request`。永不抛异常。"""

        try:
            workers = await self.list_workers()
        except Exception as exc:  # noqa: BLE001 —— 记事实，退回 stock 单发
            list_error = f"{type(exc).__name__}: {exc}"[:300]
            logger.warning("[rh2-router-client] list_workers 失败，退回经 router 单发 abort rid=%s：%s", rid, list_error)
            failed: dict[str, str] = {}
            delivered: tuple[str, ...] = ()
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self._abort_timeout)) as sess:
                    await self._post_abort(sess, self.router_url, rid)
                delivered = (self.router_url,)
            except Exception as exc2:  # noqa: BLE001
                failed[self.router_url] = f"{type(exc2).__name__}: {exc2}"[:300]
            return AbortBroadcastResult(
                rid=rid,
                mode="router_single_send",
                workers=(self.router_url,),
                delivered=delivered,
                failed=failed,
                list_error=list_error,
            )

        delivered_list: list[str] = []
        failed_map: dict[str, str] = {}
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self._abort_timeout)) as sess:
            results = await asyncio.gather(
                *(self._post_abort(sess, url, rid) for url in workers), return_exceptions=True
            )
        for url, result in zip(workers, results, strict=True):
            if isinstance(result, BaseException):
                failed_map[url] = f"{type(result).__name__}: {result}"[:300]
                logger.warning("[rh2-router-client] abort rid=%s 投递 worker %s 失败：%s", rid, url, failed_map[url])
            else:
                delivered_list.append(url)
        if not workers:
            logger.warning("[rh2-router-client] router worker 池为空，abort rid=%s 无处投递", rid)
        return AbortBroadcastResult(
            rid=rid,
            mode="broadcast",
            workers=tuple(workers),
            delivered=tuple(delivered_list),
            failed=failed_map,
            list_error=None,
        )
