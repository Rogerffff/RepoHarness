"""W10（决策包 D2+B v2 B-5b）：MilesRouter worker 池的 rh2 侧客户端——rid 级 abort **广播**，
投递结果三分（delivered / partial / undeliverable），不可证明到达即 run-fatal（codex Wave3 F3 P1）。

为什么需要它（代码事实，integration tree `reference/miles-rh2-integration`）：

- rh2 的采样请求平面经 `--use-miles-router` 起的 MilesRouter（`miles/router/router.py`）。
  它只有两条显式路由 `POST /add_worker`、`GET /list_workers`，其余一切路径落 catch-all
  `/{path:path}` → `do_proxy`：**每个 HTTP 请求独立**取"活跃请求数最小"的 worker
  （`_use_url`），既不读 `X-SMG-Routing-Key`，也不记 rid → worker 的归属。
- 因此 capture wire 在 cancel/超时后发的 `POST /abort_request {"rid": ...}` 若经 router
  单发，只有 1/N 概率落到真正持有该 rid 的 engine；错发时 SGLang 对不认识的 rid 静默无操作、
  router 照样 200——被放弃的生成继续占 engine 槽位直到自然完成（容量泄漏，非样本偏置）。
- miles 自己的 rollout abort（`miles/rollout/inference_rollout/inference_rollout_train.py`
  `abort` → `get_worker_urls`）就是"问 router `/list_workers` 拿全部 worker，**绕过 router**
  逐 worker 直发 `{"abort_all": true}`"。本模块照同一形状做 **rid 级**广播：每个 worker
  都收到同一个 rid，持有者终止，其余 worker 忽略（SGLang 语义），幂等安全。

投递语义（codex Wave3 F3 P1 修复后；`AbortBroadcastResult.outcome`）：

1. **目标集合**：优先 router 实时列表（`GET /list_workers`，fallback 新 sgl-router 的
   `/workers`）；实时列表取不到或为空 → 用**启动时已核对的 worker URL 集合**
   （`verified_workers`，bringup 侧从 `startup_evidence.router_workers` 准备，见下"接缝"）；
   两者都有时取并集（核对集合里而实时列表缺的 worker 记 `drift_missing_from_router`，仍投递）。
   **不再有经 router 单发的回退**——那条路径只在单 worker 池下正确，已删除。
2. **三种结果**：
   - ``delivered``：目标集合非空且每个目标都 2xx → 到达已证明（前提：目标集合 ⊇ 所有可能持有
     rh2 rid 的 engine；首版 profile engine 数固定、MilesRouter 从不摘除 worker，成立）；
   - ``partial``：至少一个目标 2xx、至少一个失败 → **不能证明持有者收到**（router 不告诉我们谁持有
     rid，SGLang 的 200 也不区分"持有/忽略"）→ 调用方（capture_wire）经
     `bringup.notify_run_fatal` 升级为 typed run-fatal `abort_delivery_partial`；
   - ``undeliverable``：目标集合为空（实时列表失败/为空且无核对集合）或全部目标失败 → 同样
     run-fatal `abort_undeliverable`。
   本类**永不抛**，只返回事实；升级动作在 capture_wire（本 attempt 的失败归因不变）。
3. **接缝（bringup 侧，已接线）**：`BringupService._verify_router_worker_set()` 在启动探针阶段取
   `/list_workers`，把规范化去重后的集合与固定 topology 的预期 engine 数
   （`rollout_num_gpus // rollout_num_gpus_per_engine`）做**精确数量核对**；只有相等才调
   `set_verified_workers(...)` 下发，`fa_formal` 下核对不过直接 `StartupCheckError`（不进入 RUNNING）。
   核对的是**集合完整性**，不是逐台可达性——启动时不对每个 worker 单独探活；广播时每个目标
   是否 2xx 才是投递事实。本模块只做 URL 规整（去 `@<rank>` + 去重，镜像
   `miles.utils.http_utils.router_worker_base_urls`）。

刻意不做（B-5b 明示，首版）：rid → worker 粘滞表、`X-SMG-Routing-Key` 定向路由、
dead-engine 回池、`/remove_worker` 弹性回收、service discovery——任一 engine 死亡 = 停 run
按 B-3 重启。本包不 import miles：`repoharness2.adapters.slime` 的 import 面必须零 miles 依赖。
"""

from __future__ import annotations

import asyncio
import dataclasses
import logging
from collections.abc import Iterable
from typing import Any

import aiohttp

logger = logging.getLogger("rh2.engine_router_client")

OUTCOME_DELIVERED = "delivered"
OUTCOME_PARTIAL = "partial"
OUTCOME_UNDELIVERABLE = "undeliverable"

SOURCE_ROUTER_LIST = "router_list"
SOURCE_VERIFIED_SET = "verified_set"
SOURCE_UNION = "router_list+verified_set"
SOURCE_NONE = "none"


def worker_base_urls(urls: Iterable[str]) -> list[str]:
    """镜像 miles `router_worker_base_urls`：去掉 dp-aware 路由加的 `@<rank>` 后缀，
    同一 engine 的多个 rank 合并为一个地址；保持首次出现顺序。"""

    bases: list[str] = []
    for url in urls:
        url = str(url).rstrip("/")
        base, sep, rank = url.rpartition("@")
        if sep and rank.isdigit():
            url = base
        if url not in bases:
            bases.append(url)
    return bases


@dataclasses.dataclass(frozen=True)
class AbortBroadcastResult:
    """一次 rid abort 的投递事实（本类不抛异常，交调用方记账/升级）。

    - ``outcome``：``delivered`` / ``partial`` / ``undeliverable``（模块 docstring 第 2 条）；
    - ``targets_source``：目标集合来源 ``router_list`` / ``verified_set`` /
      ``router_list+verified_set`` / ``none``；
    - ``targets`` / ``delivered`` / ``failed``：目标、2xx 的目标、目标 → 错误摘要；
    - ``list_error``：实时列表取不到/为空时的原因（有核对集合时只是事实，不是失败）；
    - ``drift_missing_from_router``：核对集合里有、实时列表里没有的 worker（已一并投递）。
    """

    rid: str
    outcome: str
    targets_source: str
    targets: tuple[str, ...]
    delivered: tuple[str, ...]
    failed: dict[str, str]
    list_error: str | None = None
    drift_missing_from_router: tuple[str, ...] = ()

    @property
    def proven(self) -> bool:
        """到达已证明 ⟺ outcome == delivered。partial/undeliverable 都是"不能证明持有者收到"。"""

        return self.outcome == OUTCOME_DELIVERED

    def to_dict(self) -> dict[str, Any]:
        return {
            "rid": self.rid,
            "outcome": self.outcome,
            "targets_source": self.targets_source,
            "targets": list(self.targets),
            "delivered": list(self.delivered),
            "failed": dict(self.failed),
            "list_error": self.list_error,
            "drift_missing_from_router": list(self.drift_missing_from_router),
            "proven": self.proven,
        }


class AbortDeliveryUnprovenError(RuntimeError):
    """typed run-fatal：rid abort 不能证明到达持有者（partial / undeliverable / abort 机制自身异常）。

    `reason_code` 供 bringup `_on_run_fatal` 命名关停原因（`run_fatal:<reason_code>`）：
    ``abort_delivery_partial`` / ``abort_undeliverable``。与 group filter fatal 走同一进程级通道
    `bringup.notify_run_fatal`。
    """

    def __init__(self, result: AbortBroadcastResult, *, detail: str | None = None) -> None:
        self.result = result
        self.reason_code = "abort_delivery_partial" if result.outcome == OUTCOME_PARTIAL else "abort_undeliverable"
        message = (
            f"{self.reason_code}: rid={result.rid} targets_source={result.targets_source} "
            f"targets={list(result.targets)} delivered={list(result.delivered)} failed={result.failed} "
            f"list_error={result.list_error!r}"
        )
        if detail:
            message = f"{message} detail={detail}"
        super().__init__(message)

    @classmethod
    def from_exception(cls, rid: str, exc: BaseException) -> "AbortDeliveryUnprovenError":
        """abort 机制自身抛出异常（不该发生）= 同样不能证明到达，按 undeliverable 升级，异常原文进 detail。"""

        result = AbortBroadcastResult(
            rid=rid,
            outcome=OUTCOME_UNDELIVERABLE,
            targets_source=SOURCE_NONE,
            targets=(),
            delivered=(),
            failed={},
            list_error=f"abort_path_exception: {type(exc).__name__}: {exc}"[:300],
        )
        return cls(result, detail=f"{type(exc).__name__}: {exc}"[:300])


def classify_outcome(targets: Iterable[str], delivered: Iterable[str], failed: dict[str, str]) -> str:
    targets = list(targets)
    delivered = list(delivered)
    if not targets or not delivered:
        return OUTCOME_UNDELIVERABLE
    if failed:
        return OUTCOME_PARTIAL
    return OUTCOME_DELIVERED


class MilesRouterWorkerClient:
    """router 地址（`http://{sglang_router_ip}:{sglang_router_port}`）上的 worker 池视图 + rid 级
    abort 广播。每次广播都重新取实时列表（与 miles abort 同款；abort 只发生在 cancel/超时路径，
    不在采样热路径）；实时列表不可用时对启动核对集合广播。"""

    def __init__(
        self,
        router_url: str,
        *,
        verified_workers: Iterable[str] | None = None,
        list_timeout_seconds: float = 5.0,
        abort_timeout_seconds: float = 5.0,
    ) -> None:
        self.router_url = router_url.rstrip("/")
        self._list_timeout = float(list_timeout_seconds)
        self._abort_timeout = float(abort_timeout_seconds)
        self._verified_workers: tuple[str, ...] = ()
        if verified_workers is not None:
            self.set_verified_workers(verified_workers)

    # -- 接缝：启动时已核对的 worker 集合 ---------------------------------------------

    def set_verified_workers(self, urls: Iterable[str]) -> tuple[str, ...]:
        """bringup 接线点：启动探针阶段**数量核对已通过**的 worker URL 集合
        （`startup_evidence.router_workers.urls`，且该段 `verified: true`）。规整（去 `@rank`、去重、
        去尾斜杠）后保存；返回保存的元组。空集合 = 无核对集合。

        调用方合同：**不得下发未核对/不完整的集合**——本类会把"集合里每个 URL 都 2xx"直接判成
        `delivered`，集合缺一台 engine 就等于把一次实际没到持有者的 abort 报成已证明到达。
        """

        self._verified_workers = tuple(worker_base_urls(urls))
        return self._verified_workers

    @property
    def verified_workers(self) -> tuple[str, ...]:
        return self._verified_workers

    # -- worker 列表 ----------------------------------------------------------------

    async def list_workers(self) -> list[str]:
        """router 实时注册的全部 worker base URL（规整后）。取不到即抛 RuntimeError（调用方决定处置）。"""

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

    async def resolve_targets(self) -> tuple[list[str], str, str | None, list[str]]:
        """决定本次广播的目标集合。返回 (targets, targets_source, list_error, drift_missing_from_router)。

        - 实时列表非空：targets = 实时列表 ∪ 核对集合（核对集合里缺席于实时列表的 worker 记 drift，仍投递）；
        - 实时列表失败或为空：targets = 核对集合（list_error 记原因）；
        - 两者皆无：targets 空（source=none）→ 调用方按 undeliverable 处置。
        """

        live: list[str] = []
        list_error: str | None = None
        try:
            live = await self.list_workers()
            if not live:
                list_error = "router_worker_list_empty"
        except Exception as exc:  # noqa: BLE001 —— 记事实，退回核对集合（不是退回经 router 单发）
            list_error = f"{type(exc).__name__}: {exc}"[:300]
        verified = list(self._verified_workers)
        if live:
            drift = [w for w in verified if w not in live]
            targets = live + drift
            source = SOURCE_UNION if drift else SOURCE_ROUTER_LIST
            return targets, source, list_error, drift
        if verified:
            return verified, SOURCE_VERIFIED_SET, list_error, []
        return [], SOURCE_NONE, list_error, []

    # -- 广播 ----------------------------------------------------------------------

    async def _post_abort(self, sess: aiohttp.ClientSession, url: str, rid: str) -> None:
        async with sess.post(f"{url}/abort_request", json={"rid": rid}) as r:
            if r.status >= 400:
                text = await r.text()
                raise RuntimeError(f"HTTP {r.status}: {text[:200]}")

    async def broadcast_abort(self, rid: str) -> AbortBroadcastResult:
        """对目标集合的每个 worker 直发同一 rid 的 `/abort_request`。永不抛异常；结果三分见模块 docstring。"""

        targets, source, list_error, drift = await self.resolve_targets()
        if list_error is not None:
            logger.warning(
                "[rh2-router-client] router worker 列表不可用（%s），abort rid=%s 改对启动核对集合广播（%d 个）",
                list_error,
                rid,
                len(targets),
            )
        if drift:
            logger.warning("[rh2-router-client] 核对集合里的 worker 缺席于 router 实时列表，仍投递：%s", drift)
        delivered_list: list[str] = []
        failed_map: dict[str, str] = {}
        if targets:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self._abort_timeout)) as sess:
                results = await asyncio.gather(
                    *(self._post_abort(sess, url, rid) for url in targets), return_exceptions=True
                )
            for url, result in zip(targets, results, strict=True):
                if isinstance(result, BaseException):
                    failed_map[url] = f"{type(result).__name__}: {result}"[:300]
                    logger.warning("[rh2-router-client] abort rid=%s 投递 worker %s 失败：%s", rid, url, failed_map[url])
                else:
                    delivered_list.append(url)
        else:
            logger.error("[rh2-router-client] abort rid=%s 无目标可投递（实时列表：%s；核对集合为空）", rid, list_error)
        outcome = classify_outcome(targets, delivered_list, failed_map)
        return AbortBroadcastResult(
            rid=rid,
            outcome=outcome,
            targets_source=source,
            targets=tuple(targets),
            delivered=tuple(delivered_list),
            failed=failed_map,
            list_error=list_error,
            drift_missing_from_router=tuple(drift),
        )
