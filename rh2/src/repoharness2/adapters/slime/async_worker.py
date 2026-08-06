"""FA-1：持续 RolloutExecution worker、有界交付队列、资源分类限额、
model proxy 边界（D-FA-3 内部重生成）、局部幂等重试白名单。

出处：05 计划 FA-1；机制论证见 `fully_async_rollout_pipeline_design_discussion.md`
§3.2/§4/§6 与 D-FA-3。本版含 FA-1 follow-up（codex 轮次 6 审查全项采纳，
存档 `s2/codex_reviews.md`）：sink 失败的 durable fallback + run-halt、
取消/任务源故障/关闭协议收口、attempt 全局身份、capture 两阶段事务、
恢复必须达到 abort 窗口 target_version、attempt 超时、audit 有界存储、
资源限额接入执行生命周期。

与 slime 的绑定边界：本模块 **零 slime import**——所有运行时组件可注入；
slime 侧生产薄壳在 `rh2/experiments/fa_bringup/rollout_entry.py`（惰性
import，本机静态审查 + 假件测试，GPU 行为验证归 FA-5）。

对 stock fully_async 三缺陷的修复对应（表面契约测试 pin 的三处）：

- **N1 task 异常静默泄漏** → 每个异常执行经 failure_sink 落账；sink 自身
  失败进 worker 内部 durable fallback（`unrecorded_failures`）并触发
  **run-halt**（停止 top-up、收尾后抛 `WorkerHalted`）——账平但无记录的
  形态被消灭；
- **N2 阻塞式 put 停摆** → 非阻塞 try_put + 待投列表 + 反压传导；stop 后
  消费者死亡有 drain 超时协议（未投样本进 `abandoned_deliveries` 显式
  记账，绝不静默等死）；
- **ABORTED 整组回队** → abort 在 proxy 层内部重生成，worker 面不存在
  ABORTED 样本。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import random
import time
import uuid
from datetime import datetime, timezone
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field, replace
from typing import Any, Literal, Protocol

from repoharness2.contracts.fa_runtime import (
    ModelCallAttempt,
    TrainingRuntimeWindow,
)

__all__ = [
    "ArtifactSinkWriteError",
    "FatalExecutionInfrastructureError",
    "canonical_artifact_bytes",
    "BoundedDeliveryQueue",
    "ContinuousExecutionWorker",
    "DEFAULT_RETRY_WHITELIST",
    "DeliveredDraft",
    "ExecutionTaskSpec",
    "ModelCallProxy",
    "NonRetryableError",
    "ProxyCallResult",
    "ResourceClassName",
    "ResourceLimits",
    "RetryAttemptRecord",
    "RetrySpec",
    "SessionPoisonRegistry",
    "SessionPoisonedError",
    "StaticActiveCoordinator",
    "UnattributableModelCallError",
    "WorkerHalted",
    "retry_local_operation",
]


# ---------------------------------------------------------------------------
# 资源分类限额（codex 轮次 3 #9；轮次 6：必须接入真实生命周期，见 worker/proxy）
# ---------------------------------------------------------------------------

ResourceClassName = Literal[
    "sandbox", "model_call", "grading_container", "pending_group", "ready_group"
]

_DEFAULT_LIMITS: dict[str, int] = {
    "sandbox": 16,
    "model_call": 32,
    "grading_container": 8,
    "pending_group": 64,
    "ready_group": 64,
}


class ResourceLimits:
    """按资源类分离的并发限额：一类打满只反压自己的上游，不饿死其他类。

    接入点（轮次 6 修正——限额必须真实生效，不是独立摆设）：
    `ContinuousExecutionWorker(execution_limits=...)` 把整次执行圈进
    `sandbox` 类；`ModelCallProxy(limits=...)` 把每次 send 圈进
    `model_call` 类；评分容器类由 GradingQueue 侧接（F5 既有并发面），
    pending/ready 组类由 FA-2 assembler 接。
    """

    def __init__(self, limits: Mapping[str, int] | None = None) -> None:
        merged = dict(_DEFAULT_LIMITS)
        if limits:
            for name, value in limits.items():
                if name not in _DEFAULT_LIMITS:
                    raise ValueError(f"未知资源类 {name!r}（封闭枚举，扩类先改契约）。")
                if value < 1:
                    raise ValueError(f"资源类 {name} 限额必须 >= 1，得到 {value}。")
                merged[name] = value
        self._semaphores = {name: asyncio.Semaphore(value) for name, value in merged.items()}
        self.limits = merged
        self.backpressure_counts: dict[str, int] = {name: 0 for name in merged}
        self.in_use: dict[str, int] = {name: 0 for name in merged}

    def acquire(self, class_name: ResourceClassName) -> "_ResourceLease":
        return _ResourceLease(self, class_name)


class _ResourceLease:
    def __init__(self, limits: ResourceLimits, class_name: str) -> None:
        self._limits = limits
        self._class = class_name

    async def __aenter__(self) -> None:
        sem = self._limits._semaphores[self._class]
        if sem.locked():
            self._limits.backpressure_counts[self._class] += 1
        await sem.acquire()
        self._limits.in_use[self._class] += 1

    async def __aexit__(self, *exc_info: Any) -> None:
        self._limits.in_use[self._class] -= 1
        self._limits._semaphores[self._class].release()


# ---------------------------------------------------------------------------
# 有界交付队列（N2 修复：非阻塞投递 + 反压计数）
# ---------------------------------------------------------------------------


class BoundedDeliveryQueue:
    """有界队列：生产侧只用非阻塞 `try_put`（满 = 反压信号，不悬挂协程）。"""

    def __init__(self, maxsize: int) -> None:
        if maxsize < 1:
            raise ValueError("maxsize 必须 >= 1。")
        self._queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=maxsize)
        self.backpressure_events = 0

    def try_put(self, item: Any) -> bool:
        try:
            self._queue.put_nowait(item)
            return True
        except asyncio.QueueFull:
            self.backpressure_events += 1
            return False

    async def get(self) -> Any:
        return await self._queue.get()

    def qsize(self) -> int:
        return self._queue.qsize()


# ---------------------------------------------------------------------------
# 局部幂等重试白名单（讨论稿 §4；默认不在表中 = 不自动重试）
# ---------------------------------------------------------------------------


class NonRetryableError(RuntimeError):
    """显式永久错误标记：任何操作里抛出它都立即终止重试（认证失败、契约
    冲突、digest 不符等——重复执行不可能改变结果的错误）。"""


@dataclass(frozen=True)
class RetrySpec:
    max_attempts: int  # 含首次
    base_delay_seconds: float = 0.5
    max_delay_seconds: float = 8.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError(f"max_attempts={self.max_attempts} 必须 >= 1（含首次）。")
        if not (0.0 < self.base_delay_seconds <= self.max_delay_seconds):
            raise ValueError(
                f"delay 非法：base={self.base_delay_seconds}, max={self.max_delay_seconds}"
                "——须 0 < base <= max。"
            )


# 键 = 操作名（讨论稿 §4 白名单表的代码化）。整环境+harness 重跑、
# 已产生 token 后的模型调用**刻意不在表中**——那是 D-FA-3/缺员语义的领地。
DEFAULT_RETRY_WHITELIST: dict[str, RetrySpec] = {
    "docker_image_inspect": RetrySpec(3),
    "docker_image_pull": RetrySpec(3),
    "container_create": RetrySpec(3),  # 调用方必须用唯一名/幂等键
    "container_remove": RetrySpec(3),
    "lease_release": RetrySpec(3),
    "artifact_atomic_write": RetrySpec(3),
    "model_request_before_send": RetrySpec(3),
    "grading_stage": RetrySpec(2),  # 评分阶段整段重试 ≤1 次（首次+1）
}


@dataclass(frozen=True)
class RetryAttemptRecord:
    operation: str
    attempt_number: int
    backoff_seconds: float
    error: str | None
    succeeded: bool


async def retry_local_operation(
    operation: str,
    fn: Callable[[], Awaitable[Any]],
    *,
    whitelist: Mapping[str, RetrySpec] | None = None,
    ledger: list[RetryAttemptRecord] | None = None,
    rng: random.Random | None = None,
    sleeper: Callable[[float], Awaitable[None]] = asyncio.sleep,
    retryable: Callable[[BaseException], bool] | None = None,
) -> Any:
    """白名单式局部重试（full-jitter 指数退避）。

    不在白名单的操作**只执行一次**；`NonRetryableError` 与 `retryable`
    判负的异常**立即终止**（轮次 6：认证失败/契约冲突/digest 不符等永久
    错误不许烧重试预算）。重试记录追加进 ledger（RolloutAudit 时间线的
    数据源，不新增公共 schema）。
    """

    table = DEFAULT_RETRY_WHITELIST if whitelist is None else whitelist
    spec = table.get(operation)
    rng = rng or random.Random()
    records = ledger if ledger is not None else []
    max_attempts = spec.max_attempts if spec is not None else 1
    for attempt in range(1, max_attempts + 1):
        try:
            result = await fn()
        except Exception as exc:  # noqa: BLE001 —— 分类就在下面两行
            permanent = isinstance(exc, NonRetryableError) or (
                retryable is not None and not retryable(exc)
            )
            is_final = permanent or attempt >= max_attempts
            backoff = 0.0
            if not is_final:
                assert spec is not None
                cap = min(spec.max_delay_seconds, spec.base_delay_seconds * (2 ** (attempt - 1)))
                backoff = rng.uniform(0.0, cap)  # full jitter
            records.append(
                RetryAttemptRecord(
                    operation=operation,
                    attempt_number=attempt,
                    backoff_seconds=backoff,
                    error=f"{type(exc).__name__}: {exc}",
                    succeeded=False,
                )
            )
            if is_final:
                raise
            await sleeper(backoff)
            continue
        records.append(
            RetryAttemptRecord(
                operation=operation,
                attempt_number=attempt,
                backoff_seconds=0.0,
                error=None,
                succeeded=True,
            )
        )
        return result
    raise AssertionError("unreachable")  # pragma: no cover


# ---------------------------------------------------------------------------
# model proxy 边界（D-FA-3 实现主体：同一逻辑轮内的内部重生成）
# ---------------------------------------------------------------------------


class SessionPoisonedError(RuntimeError):
    """session 已中毒：后续同 session 的模型调用一律拒绝（codex 轮次 7——
    CC 会对 5xx 指数退避重试且 20s 内不放弃，实测 2.1.205；仅靠 turn 去重
    不够，execution 判缺员后必须整 session 拒绝）。"""

    def __init__(self, session_id: str, reason: str) -> None:
        super().__init__(f"session_poisoned: {session_id}: {reason}")
        self.session_id = session_id
        self.reason = reason


class SessionPoisonRegistry:
    """session 中毒登记：不可归因故障/预算耗尽后，同 session 的一切后续
    请求快速拒绝，并**主动通知 execution owner 终止**（codex 轮次 9 P0-4）。

    线程模型（codex 轮次 10 P0-3）：生产拓扑是 Ray actor loop（orchestrator/
    subscribe）+ aiohttp adapter 线程（proxy/poison）**跨线程并发**——所有
    状态转换在 `threading.Lock` 内原子完成（check-then-subscribe 与
    poison-then-extract 的窗口竞态会丢通知）；回调复制出来在**锁外**调用
    （防死锁），且回调自身必须线程安全（owner 用 call_soon_threadsafe）。

    生命周期（轮次 10 P0-4——不再 FIFO 淘汰活跃毒）：active poison 保留到
    execution 清理 ACK（`release()`，由 CaptureRegistry.unregister 触发）；
    释放后归档为有界摘要（audit 用）。active 数量受 rollout 并发自然约束。"""

    def __init__(self, max_archived: int = 4096) -> None:
        if max_archived < 1:
            raise ValueError("max_archived 必须 >= 1。")
        import threading

        self._lock = threading.Lock()
        self._active: dict[str, str] = {}
        self._archived: dict[str, str] = {}
        self._max_archived = max_archived
        self._subscribers: dict[str, list[Callable[[str, str], None]]] = {}
        self.archived_evictions = 0
        self.notify_failures = 0
        self.notify_failure_records: list[tuple[str, str]] = []

    def subscribe(self, session_id: str, callback: Callable[[str, str], None]) -> None:
        """execution owner 注册终止回调。已中毒则立即回调（锁外）。回调必须
        非阻塞且线程安全——owner 侧标准形态：
        `loop.call_soon_threadsafe(task.cancel)`（poison 可能来自 adapter 线程）。"""

        with self._lock:
            # 轮次 11：归档毒也立即回调——SID 复用（同题补采/下一 epoch 的
            # 稳定 ID）不得静默挂上订阅装作健康。execution 唯一身份是 FA-2
            # 第一验收项，这里是 registry 侧兜底。
            reason = self._active.get(session_id) or self._archived.get(session_id)
            if reason is None:
                self._subscribers.setdefault(session_id, []).append(callback)
                return
        self._invoke(callback, session_id, reason)

    def unsubscribe(self, session_id: str) -> None:
        with self._lock:
            self._subscribers.pop(session_id, None)

    def poison(self, session_id: str, reason: str) -> None:
        with self._lock:
            if session_id in self._active or session_id in self._archived:
                return
            self._active[session_id] = reason
            callbacks = self._subscribers.pop(session_id, [])
        for callback in callbacks:  # 锁外调用（防死锁）
            self._invoke(callback, session_id, reason)

    def release(self, session_id: str) -> None:
        """execution 清理 ACK：active -> 有界归档（活跃毒绝不被容量淘汰）。"""

        with self._lock:
            reason = self._active.pop(session_id, None)
            if reason is None:
                return
            while len(self._archived) >= self._max_archived:
                oldest = next(iter(self._archived))
                del self._archived[oldest]
                self.archived_evictions += 1
            self._archived[session_id] = reason

    def _invoke(self, callback: Callable[[str, str], None], sid: str, reason: str) -> None:
        try:
            callback(sid, reason)
        except Exception as exc:  # noqa: BLE001 - 通知失败不掩盖 poison 本身
            with self._lock:  # 轮次 11：计数上锁 + 有界记录（控制面可查）
                self.notify_failures += 1
                self.notify_failure_records.append((sid, f"{type(exc).__name__}: {exc}"))
                del self.notify_failure_records[:-64]

    def is_poisoned(self, session_id: str) -> bool:
        with self._lock:
            return session_id in self._active or session_id in self._archived

    def reason(self, session_id: str) -> str | None:
        with self._lock:
            return self._active.get(session_id) or self._archived.get(session_id)

    def check(self, session_id: str) -> None:
        with self._lock:
            reason = self._active.get(session_id) or self._archived.get(session_id)
        if reason is not None:
            raise SessionPoisonedError(session_id, reason)


class CoordinatorView(Protocol):
    """TrainingRuntimeCoordinator 协议的消费端形状（FA-0 3b）。"""

    def current_window(self) -> TrainingRuntimeWindow: ...


class StaticActiveCoordinator:
    """真实协调器（trainer 侧，FA-4 接线）就位前的保守替身：永远 ACTIVE。

    语义后果（刻意保守）：没有窗口事实 → **任何中断都不可归因** → proxy
    不做内部重生成，一律 poison + 缺员。这正是"协调器缺席时的正确行为"
    ——宁可缺员也不猜测 abort 归因。版本由注入的 provider 提供
    （glue 的权威 engine 版本）。"""

    def __init__(
        self,
        version_provider: Callable[[], str],
        *,
        cache_ttl_seconds: float = 2.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._provider = version_provider
        # codex 轮次 9 一般 3：provider 可能是同步 HTTP（glue 的
        # /get_weight_version）——本类在 proxy 热路径每次窗口读取都被调，
        # 无缓存会把 event loop 反复阻塞。TTL 缓存把调用压到 <=1 次/TTL；
        # 版本至多滞后 TTL 秒（bring-up 可接受；FA-4 用 coordinator 发布的
        # consensus version 取代整个替身）。
        self._cache_ttl = cache_ttl_seconds
        self._clock = clock
        self._cached_version: str | None = None
        self._cached_at: float = float("-inf")

    def current_window(self) -> TrainingRuntimeWindow:
        now_ts = self._clock()
        if self._cached_version is None or now_ts - self._cached_at >= self._cache_ttl:
            self._cached_version = str(self._provider())
            self._cached_at = now_ts
        version = self._cached_version
        try:
            old = str(int(version, 10) - 1)
        except ValueError:
            old = f"{version}_prev"
        now = datetime.now(timezone.utc)
        return TrainingRuntimeWindow(
            update_epoch=0,
            phase="ACTIVE",
            old_version=old,
            target_version=version,
            active_version=version,
            window_started_at=now,
            window_completed_at=now,
            fencing_token="static_active",
        )


class UnattributableModelCallError(RuntimeError):
    """不可归因中断：走缺员分支（RolloutAttemptOutcome missing_after_local_retry）。"""

    def __init__(self, reason_code: str, message: str) -> None:
        super().__init__(f"{reason_code}: {message}")
        self.reason_code = reason_code


class ArtifactSinkWriteError(UnattributableModelCallError):
    """持久 sink 写失败（codex 轮次 11 P0-2）：正式链 fail-closed——
    evidence 无法持久化时训练不得继续该 execution（磁盘满/权限/路径冲突
    继续跑会留下悬空 evidence_refs）。作为 UnattributableModelCallError
    子类走 call() 外层统一 poison + 缺员。"""

    def __init__(self, message: str) -> None:
        super().__init__("artifact_sink_write_failed", message)


@dataclass(frozen=True)
class DeliveredDraft:
    """delivered attempt 的草案（capture 两阶段事务的中间态，轮次 6 严重 5）。

    proxy 在响应返回时**不**直接生成 delivered 的 ModelCallAttempt——
    capture 持久化成功之前，`capture_record_ref` 是"声称存在"的悬空引用。
    正确顺序：proxy 返回草案 → 调用方完成 capture 持久化 →
    `ProxyCallResult.finalize_delivered(ref)` 落账。未 finalize 的交付在
    `ModelCallProxy.unfinalized_deliveries` 可见（FA-2/审计对账面）。
    """

    scoped_turn_id: str
    attempt_id: str
    attempt_number: int
    weight_version: str
    physical_attempt_id: str | None = None


@dataclass
class ProxyCallResult:
    """一次逻辑轮的交付：响应 + 已定案的非交付 attempts + 待 finalize 草案。"""

    response: Mapping[str, Any]
    prior_attempts: tuple[ModelCallAttempt, ...]
    draft: DeliveredDraft
    _proxy: "ModelCallProxy" = field(repr=False)
    _finalized: ModelCallAttempt | None = field(default=None, repr=False)

    @property
    def delivered_attempt_number(self) -> int:
        return self.draft.attempt_number

    @property
    def attempts(self) -> tuple[ModelCallAttempt, ...]:
        if self._finalized is None:
            return self.prior_attempts
        return (*self.prior_attempts, self._finalized)

    def abandon_delivered(self, reason: str) -> ModelCallAttempt:
        """capture 未能持久化（flush 失败/客户端断连）时显式关闭 draft
        （codex 轮次 7：unfinalized 不能只有"可见"，还要有出口）。

        事务语义（codex 轮次 12 P0）：本方法在 call() 返回**之后**被调，
        sink 失败不经过 call() 外层统一 poison——所以必须**先关 draft、
        落最小 FailureFact 账**，再把 ArtifactSinkWriteError 抛给调用方
        （由调用方 poison；unregister 路径在调用前已 poison）。绝不允许
        "抛了异常但 draft 还 pending、账上没记录"的中间态。"""

        if self._finalized is not None:
            raise ValueError(f"{self.draft.attempt_id} 已 finalize，不能再 abandon。")
        sink_failure: ArtifactSinkWriteError | None = None
        evidence: list[str] = []
        try:
            evidence = [self._proxy._store_artifact(f"{self.draft.attempt_id}_abandon", reason)]
        except ArtifactSinkWriteError as exc:
            sink_failure = exc  # 先关账再抛
        attempt = ModelCallAttempt(
            logical_turn_id=self.draft.scoped_turn_id,
            model_call_attempt_id=f"{self.draft.attempt_id}_abandoned",
            attempt_number=self.draft.attempt_number,
            delivery_status="non_delivered_failed",
            evidence_refs=evidence,
            physical_attempt_id=self.draft.physical_attempt_id,
        )
        self._finalized = attempt
        with self._proxy._ledger_lock:
            self._proxy.attempts_ledger.append(attempt)
            self._proxy._pending_drafts.discard(self.draft.attempt_id)
        if sink_failure is not None:
            raise sink_failure
        return attempt

    def finalize_delivered(self, capture_record_ref: str) -> ModelCallAttempt:
        """capture 持久化成功后落账 delivered attempt（两阶段第二步）。"""

        if self._finalized is not None:
            raise ValueError(f"{self.draft.attempt_id} 已 finalize 过（幂等违规）。")
        attempt = ModelCallAttempt(
            logical_turn_id=self.draft.scoped_turn_id,
            model_call_attempt_id=self.draft.attempt_id,
            attempt_number=self.draft.attempt_number,
            delivery_status="delivered",
            capture_record_ref=capture_record_ref,
            weight_version=self.draft.weight_version,
            physical_attempt_id=self.draft.physical_attempt_id,
        )
        self._finalized = attempt
        with self._proxy._ledger_lock:
            self._proxy.attempts_ledger.append(attempt)
            self._proxy._pending_drafts.discard(self.draft.attempt_id)
        return attempt


def _response_is_abort(response: Mapping[str, Any]) -> bool:
    """SGLang 以**正常 JSON**返回 abort 的形态（不只网络异常）。"""

    meta = response.get("meta_info")
    if not isinstance(meta, Mapping):
        return False
    finish = meta.get("finish_reason")
    if isinstance(finish, Mapping):
        return finish.get("type") == "abort"
    return finish == "abort"


def _version_int(version: str) -> int:
    return int(version, 10)


def canonical_artifact_bytes(payload: Any) -> bytes:
    """artifact digest 的**单一字节口径**（codex 轮次 12 一般 3）：内存
    record 与外部 sink 必须用同一序列化，否则同一 payload 两个 digest。"""

    try:
        text = json.dumps(payload, ensure_ascii=False, default=repr, sort_keys=True)
    except (TypeError, ValueError):
        text = repr(payload)
    return text.encode("utf-8", "replace")


def _artifact_record(payload: Any) -> dict[str, Any]:
    """digest-only 有界留痕：digest + 截断预览（**刻意不存完整 payload**——
    最小化私有内容落内存；外部 sink 同一契约，见 glue sink docstring）。"""

    text = canonical_artifact_bytes(payload).decode("utf-8", "replace")
    return {
        "sha256": hashlib.sha256(text.encode("utf-8", "replace")).hexdigest(),
        "preview": text[:256],
        "bytes": len(text),
    }


class ModelCallProxy:
    """D-FA-3：更新窗口 abort 的 proxy 内部重生成（CC 全程无感知）。

    守卫三条件（缺一按不可归因故障）：

    1. **重叠**：失败时刻窗口 phase != ACTIVE，或 update_epoch 相对发起
       时刻前进（窗口在调用期间开启过）；
    2. **未交付**：结构性保证（本方法未返回即未交付）；
    3. **恢复达标**（轮次 6 严重 6 修正）：phase==ACTIVE 且
       同 epoch → active_version == abort 窗口 target_version；
       更晚 epoch → active_version >= target_version（epoch 单调即新窗口
       凭据）。只"版本变大"不够——必须至少到达把我们 abort 的那次更新的
       目标版本，否则中间态版本会被误放行。

    身份（轮次 6 严重 4）：attempt id = `{execution_scope}/{turn}_a{n}`——
    并发 rollout 的同名 turn 不再冲突。半截输出经 `_artifact_record` 有界
    留痕（digest+预览；完整体交 `artifact_sink`），超过 `max_audit_artifacts`
    时按 FIFO 淘汰并计数（`audit_evictions`，长训练内存有界）。
    """

    def __init__(
        self,
        coordinator: CoordinatorView,
        *,
        max_regenerations: int = 3,
        wait_poll_seconds: float = 0.02,
        wait_timeout_seconds: float = 60.0,
        attempt_timeout_seconds: float | None = None,
        limits: ResourceLimits | None = None,
        artifact_sink: Callable[[str, Any], str] | None = None,
        sink_required: bool = False,
        max_audit_artifacts: int = 256,
        sleeper: Callable[[float], Awaitable[None]] = asyncio.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if max_regenerations < 1:
            raise ValueError("max_regenerations 必须 >= 1。")
        if max_audit_artifacts < 1:
            raise ValueError("max_audit_artifacts 必须 >= 1。")
        self._coordinator = coordinator
        self._max_regenerations = max_regenerations
        self._wait_poll = wait_poll_seconds
        self._wait_timeout = wait_timeout_seconds
        self._attempt_timeout = attempt_timeout_seconds
        self._limits = limits
        self._artifact_sink = artifact_sink
        self._sink_required = sink_required
        import threading

        # 轮次 13 P0-3：ledger/_pending_drafts 跨线程共享（adapter 线程写、
        # AsyncLoop 线程读/drain）——短临界区锁
        self._ledger_lock = threading.Lock()
        self._max_artifacts = max_audit_artifacts
        self._sleeper = sleeper
        self._clock = clock
        self.attempts_ledger: list[ModelCallAttempt] = []
        self.audit_artifacts: dict[str, Any] = {}
        self.audit_evictions = 0
        self.tombstones_dropped = 0
        self._pending_drafts: set[str] = set()

    def snapshot_attempts(self, execution_scope: str) -> list[ModelCallAttempt]:
        """锁内复制该 execution 的 attempt（**不移除**）——审计事务第一步
        （codex 轮次 14 仍需修正 2：先持久化成功、再 ack 移除，写失败时
        内存证据不丢）。"""

        prefix = f"{execution_scope}/"
        with self._ledger_lock:
            return [a for a in self.attempts_ledger if a.logical_turn_id.startswith(prefix)]

    def ack_attempts(self, execution_scope: str) -> int:
        """审计事务第二步：持久化成功后从热内存移除，返回移除数。"""

        prefix = f"{execution_scope}/"
        with self._ledger_lock:
            before = len(self.attempts_ledger)
            self.attempts_ledger = [
                a for a in self.attempts_ledger if not a.logical_turn_id.startswith(prefix)
            ]
            return before - len(self.attempts_ledger)

    def drain_attempts(self, execution_scope: str) -> list[ModelCallAttempt]:
        """snapshot + ack 的合成（无持久化需求的调用方用；审计路径必须
        分两步走事务）。"""

        drained = self.snapshot_attempts(execution_scope)
        self.ack_attempts(execution_scope)
        return drained

    @property
    def unfinalized_deliveries(self) -> frozenset[str]:
        """已返回草案但未 finalize 的交付（capture 事务未闭合的对账面）。"""

        return frozenset(self._pending_drafts)

    def _store_artifact(self, attempt_id: str, payload: Any) -> str:
        """留痕并返回 evidence 引用。

        悬空修复（codex 轮次 7）：artifact_sink 成功时**直接返回持久外部
        引用**（内存条目只是缓存，可淘汰）；无 sink 时内存条目淘汰后留
        digest tombstone——`audit:` 引用永远可解析（tombstone 只含 sha256，
        体积 ~100B；长训练必须配 artifact_sink，见 docstring）。"""

        record = _artifact_record(payload)
        external: str | None = None
        if self._artifact_sink is not None:
            try:
                external = self._artifact_sink(attempt_id, payload)
                record["external_ref"] = external
            except Exception as exc:  # noqa: BLE001 —— 分链路处置（轮次 11 P0-2）
                if self._sink_required:
                    # 正式链：evidence 持久化失败 = fail-closed（吞掉会让
                    # 训练带着悬空引用继续跑）
                    raise ArtifactSinkWriteError(
                        f"{attempt_id}: sink 写失败 {type(exc).__name__}: {exc}"
                    ) from exc
                record["external_ref_error"] = f"{type(exc).__name__}: {exc}"
        def _live_count() -> int:
            return sum(1 for v in self.audit_artifacts.values() if not v.get("tombstone"))

        # tombstone 也有界（codex 轮次 9）：超过 8x 上限时丢最旧 tombstone，
        # 只留计数——digest 可解析性让位于有界内存（长训练必须配 artifact_sink，
        # 那时引用是外部持久 ref，不受此影响）
        tombstone_cap = self._max_artifacts * 8
        tombstone_keys = [k for k, v in self.audit_artifacts.items() if v.get("tombstone")]
        while len(tombstone_keys) > tombstone_cap:
            dropped = tombstone_keys.pop(0)
            del self.audit_artifacts[dropped]
            self.tombstones_dropped += 1

        while _live_count() >= self._max_artifacts:
            oldest_key = next(
                (k for k, v in self.audit_artifacts.items() if not v.get("tombstone")), None
            )
            if oldest_key is None:  # pragma: no cover - _live_count 保证存在
                break
            evicted = self.audit_artifacts.pop(oldest_key)
            self.audit_artifacts[oldest_key] = {
                "tombstone": True,
                "sha256": evicted["sha256"],
                "external_ref": evicted.get("external_ref"),
            }
            self.audit_evictions += 1
        self.audit_artifacts[attempt_id] = record
        return external if external is not None else f"audit:{attempt_id}"

    def _effective_timeout(self, deadline_monotonic: float | None) -> float | None:
        remaining = self._remaining(deadline_monotonic)
        if remaining is None:
            return self._attempt_timeout
        if self._attempt_timeout is None:
            return max(remaining, 0.0)
        return max(min(self._attempt_timeout, remaining), 0.0)

    async def _send(
        self,
        send_fn: Callable[[int], Awaitable[Mapping[str, Any]]],
        n: int,
        deadline_monotonic: float | None = None,
    ):
        timeout = self._effective_timeout(deadline_monotonic)
        if self._limits is None:
            if timeout is None:
                return await send_fn(n)
            return await asyncio.wait_for(send_fn(n), timeout=timeout)
        async with self._limits.acquire("model_call"):
            if timeout is None:
                return await send_fn(n)
            return await asyncio.wait_for(send_fn(n), timeout=timeout)

    async def _wait_active_before_send(
        self,
        attempts: list[ModelCallAttempt],
        scoped: str,
        attempt_number: int,
        deadline_monotonic: float | None,
        physical_attempt_id: str | None = None,
    ) -> None:
        """发前 ACTIVE 等待：窗口更新中不发注定被 abort 的请求（codex 轮次 7）。"""

        remaining = self._remaining(deadline_monotonic)
        budget = self._wait_timeout if remaining is None else min(self._wait_timeout, remaining)
        deadline = self._clock() + max(budget, 0.0)
        while True:
            window = self._coordinator.current_window()
            if window.phase == "ACTIVE":
                return
            if self._clock() >= deadline:
                self._record_failed(
                    attempts, scoped, f"{scoped}_presend_timeout", attempt_number,
                    physical_attempt_id=physical_attempt_id,
                )
                raise UnattributableModelCallError(
                    "engine_not_active_before_send",
                    f"{scoped}: 发前等待 ACTIVE 超时（budget={budget:.1f}s）。",
                )
            await self._sleeper(self._wait_poll)

    def _poison(self, session_id: str | None, registry: "SessionPoisonRegistry | None", reason: str) -> None:
        if registry is not None and session_id:
            registry.poison(session_id, reason)

    def _remaining(self, deadline_monotonic: float | None) -> float | None:
        if deadline_monotonic is None:
            return None
        return deadline_monotonic - self._clock()

    async def call(
        self,
        execution_scope: str,
        logical_turn_id: str,
        send_fn: Callable[[int], Awaitable[Mapping[str, Any]]],
        *,
        session_id: str | None = None,
        poison_registry: "SessionPoisonRegistry | None" = None,
        deadline_monotonic: float | None = None,
        min_attempt_budget_seconds: float = 5.0,
        physical_attempt_id: str | None = None,
    ) -> ProxyCallResult:
        """一次逻辑轮（codex 轮次 7/8：poison / episode deadline / 发前等待）。

        薄包装：**任何** UnattributableModelCallError 终止都在此统一 poison
        （codex 轮次 8 P0-3——发前等待超时/版本恢复超时/fencing 不符/版本回退
        等分支此前漏 poison）。CC 客户端取消（CancelledError）在内部已落账 +
        poison 后原样传播。
        """

        sid = session_id or execution_scope
        try:
            return await self._call_inner(
                execution_scope,
                logical_turn_id,
                send_fn,
                sid=sid,
                poison_registry=poison_registry,
                deadline_monotonic=deadline_monotonic,
                min_attempt_budget_seconds=min_attempt_budget_seconds,
                physical_attempt_id=physical_attempt_id,
            )
        except UnattributableModelCallError as exc:
            self._poison(sid, poison_registry, exc.reason_code)
            raise

    async def _call_inner(
        self,
        execution_scope: str,
        logical_turn_id: str,
        send_fn: Callable[[int], Awaitable[Mapping[str, Any]]],
        *,
        sid: str,
        poison_registry: "SessionPoisonRegistry | None",
        deadline_monotonic: float | None,
        min_attempt_budget_seconds: float,
        physical_attempt_id: str | None = None,
    ) -> ProxyCallResult:
        if not execution_scope:
            raise ValueError("execution_scope 必填（attempt 全局身份的组成部分）。")
        scoped = f"{execution_scope}/{logical_turn_id}"
        attempts: list[ModelCallAttempt] = []
        attempt_number = 0
        while True:
            attempt_number += 1
            attempt_id = f"{scoped}_a{attempt_number}"
            if poison_registry is not None:
                poison_registry.check(sid)
            remaining = self._remaining(deadline_monotonic)
            if remaining is not None and remaining < min_attempt_budget_seconds:
                self._record_failed(attempts, scoped, attempt_id, attempt_number, physical_attempt_id=physical_attempt_id)
                raise UnattributableModelCallError(
                    "episode_deadline_exhausted",
                    f"{attempt_id}: 剩余预算 {remaining:.1f}s < {min_attempt_budget_seconds}s"
                    "——不再尝试，session 中毒，execution 缺员。",
                )
            await self._wait_active_before_send(
                attempts, scoped, attempt_number, deadline_monotonic,
                physical_attempt_id=physical_attempt_id,
            )
            window_before = self._coordinator.current_window()
            failure: BaseException | None = None
            response: Mapping[str, Any] | None = None
            try:
                response = await self._send(send_fn, attempt_number, deadline_monotonic)
            except asyncio.CancelledError:
                # CC/客户端取消必须原样传播（aiohttp handler_cancellation 链），
                # 但先落账 + poison——取消后 CC 的重试不得复活该 session
                ref = self._store_artifact(attempt_id, "client_cancelled")
                self._record_failed(attempts, scoped, attempt_id, attempt_number, evidence=[ref], physical_attempt_id=physical_attempt_id)
                self._poison(sid, poison_registry, "client_cancelled")  # 取消不走外层统一路径
                raise
            except Exception as exc:  # noqa: BLE001 —— 归因在下方守卫做
                failure = exc

            if response is not None and not _response_is_abort(response):
                meta = response.get("meta_info")
                weight_version = None
                if isinstance(meta, Mapping) and meta.get("weight_version") is not None:
                    weight_version = str(meta["weight_version"])
                if weight_version is None:
                    # delivered 必须携带版本；先留痕再落账（悬空 evidence 修复）
                    ref = self._store_artifact(attempt_id, response)
                    self._record_failed(
                        attempts, scoped, attempt_id, attempt_number, evidence=[ref]
                    , physical_attempt_id=physical_attempt_id)
                    raise UnattributableModelCallError(
                        "delivered_response_missing_weight_version",
                        f"{attempt_id}: 响应缺 meta_info.weight_version，provenance 不完整。",
                    )
                draft = DeliveredDraft(
                    scoped_turn_id=scoped,
                    attempt_id=attempt_id,
                    attempt_number=attempt_number,
                    weight_version=weight_version,
                    physical_attempt_id=physical_attempt_id,
                )
                with self._ledger_lock:
                    self.attempts_ledger.extend(attempts)
                    self._pending_drafts.add(attempt_id)
                return ProxyCallResult(
                    response=response,
                    prior_attempts=tuple(attempts),
                    draft=draft,
                    _proxy=self,
                )

            payload = response if response is not None else repr(failure)
            window_now = self._coordinator.current_window()
            overlapped = (
                window_now.phase != "ACTIVE"
                or window_now.update_epoch > window_before.update_epoch
            )
            ref = self._store_artifact(attempt_id, payload)
            if not overlapped:
                self._record_failed(attempts, scoped, attempt_id, attempt_number, evidence=[ref], physical_attempt_id=physical_attempt_id)
                raise UnattributableModelCallError(
                    "no_overlapping_update_window",
                    f"{attempt_id}: 中断与任何更新窗口不重叠——按缺员处置，不做透明重试。",
                )
            attempts.append(
                ModelCallAttempt(
                    logical_turn_id=scoped,
                    model_call_attempt_id=attempt_id,
                    attempt_number=attempt_number,
                    delivery_status="non_delivered_aborted",
                    abort_update_epoch=window_now.update_epoch,
                    abort_fencing_token=window_now.fencing_token,
                    evidence_refs=[ref],
                    physical_attempt_id=physical_attempt_id,
                )
            )
            if attempt_number > self._max_regenerations:
                self._record_failed(
                    attempts, scoped, f"{attempt_id}_cap", attempt_number, evidence=[ref]
                , physical_attempt_id=physical_attempt_id)
                raise UnattributableModelCallError(
                    "max_regenerations_exceeded",
                    f"{scoped}: 连续 {attempt_number} 次被 abort——超过重生成上限。",
                )
            # codex 轮次 9 P0-1：deadline_monotonic 必须真传进去（轮次 8 的
            # replace 静默失败 + 测试假阳性双重漏网——教训：无 assert 的文本
            # 替换不可信，修复必须配"真进到目标分支"的测试断言）
            await self._wait_version_advance(
                attempts, scoped, attempt_number, window_now, deadline_monotonic,
                physical_attempt_id=physical_attempt_id,
            )

    def _record_failed(
        self,
        attempts: list[ModelCallAttempt],
        scoped: str,
        attempt_id: str,
        attempt_number: int,
        *,
        evidence: list[str] | None = None,
        physical_attempt_id: str | None = None,
    ) -> None:
        attempts.append(
            ModelCallAttempt(
                logical_turn_id=scoped,
                model_call_attempt_id=f"{attempt_id}_failed",
                attempt_number=attempt_number,
                delivery_status="non_delivered_failed",
                evidence_refs=evidence or [],
                physical_attempt_id=physical_attempt_id,
            )
        )
        with self._ledger_lock:
            self.attempts_ledger.extend(attempts)

    async def _wait_version_advance(
        self,
        attempts: list[ModelCallAttempt],
        scoped: str,
        attempt_number: int,
        abort_window: TrainingRuntimeWindow,
        deadline_monotonic: float | None = None,
        physical_attempt_id: str | None = None,
    ) -> None:
        """守卫 3：恢复必须**达到 abort 窗口的 target_version**（轮次 6 严重 6）；
        等待受 episode 绝对 deadline 约束（轮次 8 P0-3：此前用独立固定 60s，
        与 attempt1 生成 + attempt2 生成叠加可远超 episode 预算）。"""

        try:
            target = _version_int(abort_window.target_version)
        except ValueError:
            self._record_failed(attempts, scoped, f"{scoped}_nonnum", attempt_number, physical_attempt_id=physical_attempt_id)
            raise UnattributableModelCallError(
                "non_numeric_version_in_window",
                f"abort 窗口 target_version={abort_window.target_version!r} 非数值。",
            ) from None
        remaining = self._remaining(deadline_monotonic)
        budget = self._wait_timeout if remaining is None else min(self._wait_timeout, remaining)
        deadline = self._clock() + max(budget, 0.0)
        while True:
            window = self._coordinator.current_window()
            if window.phase == "ACTIVE":
                try:
                    active = _version_int(window.active_version)
                except ValueError:
                    self._record_failed(attempts, scoped, f"{scoped}_nonnum", attempt_number, physical_attempt_id=physical_attempt_id)
                    raise UnattributableModelCallError(
                        "non_numeric_version_in_window",
                        f"恢复窗口 active_version={window.active_version!r} 非数值。",
                    ) from None
                if window.update_epoch == abort_window.update_epoch:
                    if window.fencing_token != abort_window.fencing_token:
                        self._record_failed(
                            attempts, scoped, f"{scoped}_fence", attempt_number
                        , physical_attempt_id=physical_attempt_id)
                        raise UnattributableModelCallError(
                            "fencing_token_mismatch",
                            f"{scoped}: 同 epoch 的 ACTIVE 窗口 fencing 与 abort 窗口不一致。",
                        )
                    if active == target:
                        return
                    if active > target:  # 同 epoch 版本超过 target：协议矛盾
                        self._record_failed(
                            attempts, scoped, f"{scoped}_overshoot", attempt_number
                        , physical_attempt_id=physical_attempt_id)
                        raise UnattributableModelCallError(
                            "version_overshoot_same_epoch",
                            f"{scoped}: 同 epoch active({active}) > target({target})——协议矛盾。",
                        )
                elif window.update_epoch > abort_window.update_epoch:
                    if active >= target:
                        return  # 更晚窗口已把版本推到/推过目标（epoch 单调即凭据）
                    # 更晚 epoch 但版本仍低于目标：协议矛盾（版本必须单调）
                    self._record_failed(
                        attempts, scoped, f"{scoped}_regress", attempt_number
                    , physical_attempt_id=physical_attempt_id)
                    raise UnattributableModelCallError(
                        "version_regressed_across_epochs",
                        f"{scoped}: epoch 前进但 active({active}) < abort target({target})。",
                    )
                # window.update_epoch < abort_window.update_epoch：陈旧快照，继续等
            if self._clock() >= deadline:
                self._record_failed(attempts, scoped, f"{scoped}_timeout", attempt_number, physical_attempt_id=physical_attempt_id)
                raise UnattributableModelCallError(
                    "version_did_not_advance",
                    f"{scoped}: 等待 {self._wait_timeout}s 后未达 abort 窗口 target_version。",
                )
            await self._sleeper(self._wait_poll)


# ---------------------------------------------------------------------------
# 持续执行 worker（N1/N2 修复本体 + 轮次 6 生命周期收口）
# ---------------------------------------------------------------------------


class FatalExecutionInfrastructureError(RuntimeError):
    """基建级致命错误（codex 轮次 14 建议 3）：审计存储不可用、账本存储
    不可用等——**不是**单个 execution 的失败，继续 top-up 会持续产出
    无审计依据的 rollout。worker 遇到它按系统故障停机（WorkerHalted），
    恢复语义 = 整个 rollout actor 重启（05 计划已定案）。"""

    def __init__(self, reason_code: str, message: str) -> None:
        super().__init__(f"{reason_code}: {message}")
        self.reason_code = reason_code


class WorkerHalted(RuntimeError):
    """worker 因系统性故障停机（sink 失败/任务源故障）——训练不得继续。"""

    def __init__(self, reason_code: str, message: str) -> None:
        super().__init__(f"{reason_code}: {message}")
        self.reason_code = reason_code


@dataclass(frozen=True)
class ExecutionTaskSpec:
    """一次 RolloutExecution 的调度单元（身份 + 不透明载荷）。"""

    rollout_execution_id: str
    prompt_group_id: str
    member_slot: int
    payload: Any = None
    # F2-1a：物理重放身份——worker 在 **dispatch 时刻**铸造（D2：每次
    # 实际重放都不同；task_source 重供同一逻辑执行 = 新 dispatch = 新值）
    physical_attempt_id: str | None = None
    physical_attempt_seq: int | None = None


@dataclass
class WorkerCounters:
    dispatched: int = 0
    delivered: int = 0
    failed: int = 0
    abandoned: int = 0  # stop 后 drain 超时仍未投出的完成样本（显式记账）
    sink_failures: int = 0
    source_errors: int = 0
    delivery_backpressure: int = 0
    topup_paused_by_backpressure: int = 0


class ContinuousExecutionWorker:
    """持续分派独立 RolloutExecution 的异步 worker（讨论稿 §6 拓扑的 A 节点）。

    账目守恒（任何终态）：``dispatched == delivered + failed + abandoned``。

    生命周期协议（轮次 6 严重 2/3 收口）：

    - **sink 失败**：failure_sink 抛异常 → 失败事实进 worker 内部
      `unrecorded_failures`（durable fallback），置 halt——停止 top-up、
      drain 在途后抛 `WorkerHalted`（账平但无外部记录 = 不可继续训练）；
    - **任务取消**：task.cancelled() 按失败落账（CancelledError 交 sink）；
    - **任务源故障**：task_source 抛异常 → source_errors + halt（在途照常
      收尾，绝不中途弃账）；
    - **worker 自身被取消**：finally 里取消并 await 全部在途 task，逐个
      落账后再传播取消；
    - **stop 后消费者死亡**：`drain_timeout_seconds` 到期 → 未投样本进
      `abandoned` 计数 +（spec, result）留在 `abandoned_deliveries`，退出
      （绝不静默等死）。
    """

    def __init__(
        self,
        *,
        task_source: Callable[[], ExecutionTaskSpec | None],
        execute_fn: Callable[[ExecutionTaskSpec], Awaitable[Any]],
        delivery_queue: BoundedDeliveryQueue,
        failure_sink: Callable[[ExecutionTaskSpec, BaseException], None],
        concurrency: int = 8,
        max_pending_out: int | None = None,
        poll_interval_seconds: float = 0.005,
        drain_timeout_seconds: float | None = None,
        execution_limits: ResourceLimits | None = None,
        execution_resource_class: ResourceClassName = "sandbox",
        sleeper: Callable[[float], Awaitable[None]] = asyncio.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if concurrency < 1:
            raise ValueError("concurrency 必须 >= 1。")
        resolved_pending = max_pending_out if max_pending_out is not None else concurrency
        if resolved_pending < 1:
            raise ValueError(f"max_pending_out={resolved_pending} 必须 >= 1。")
        self._task_source = task_source
        self._execute_fn = execute_fn
        self._queue = delivery_queue
        self._failure_sink = failure_sink
        self._concurrency = concurrency
        self._max_pending_out = resolved_pending
        self._poll = poll_interval_seconds
        self._drain_timeout = drain_timeout_seconds
        self._limits = execution_limits
        self._resource_class = execution_resource_class
        self._sleeper = sleeper
        self._clock = clock
        self.counters = WorkerCounters()
        self.unrecorded_failures: list[tuple[ExecutionTaskSpec, str, str]] = []
        self._attempt_seq: dict[str, int] = {}  # F2-1a：逻辑执行 → 已铸序号
        self.abandoned_deliveries: list[tuple[ExecutionTaskSpec, Any]] = []
        self.halt_reason: str | None = None

    async def _guarded_execute(self, spec: ExecutionTaskSpec) -> Any:
        if self._limits is None:
            return await self._execute_fn(spec)
        async with self._limits.acquire(self._resource_class):
            return await self._execute_fn(spec)

    def _account_failure(self, spec: ExecutionTaskSpec, exc: BaseException) -> None:
        """失败必有账：sink 优先；sink 失败进 durable fallback + halt。
        基建级致命错误（FatalExecutionInfrastructureError）额外触发 halt——
        它不是成员失败，继续 top-up 只会积累无审计依据的 rollout。"""

        if isinstance(exc, FatalExecutionInfrastructureError):
            self.halt_reason = self.halt_reason or f"fatal_infrastructure:{exc.reason_code}"
        self.counters.failed += 1
        try:
            self._failure_sink(spec, exc)
        except Exception as sink_exc:  # noqa: BLE001
            self.counters.sink_failures += 1
            self.unrecorded_failures.append(
                (spec, f"{type(exc).__name__}: {exc}", f"{type(sink_exc).__name__}: {sink_exc}")
            )
            self.halt_reason = self.halt_reason or "failure_sink_failed"

    async def run(self, stop: asyncio.Event) -> None:
        in_flight: dict[asyncio.Task[Any], ExecutionTaskSpec] = {}
        pending_out: list[tuple[ExecutionTaskSpec, Any]] = []
        drain_deadline: float | None = None
        try:
            while True:
                # 1. reap（永不因队列状态停摆；取消也按失败落账）
                for task in [t for t in in_flight if t.done()]:
                    spec = in_flight.pop(task)
                    if task.cancelled():
                        self._account_failure(spec, asyncio.CancelledError("execution cancelled"))
                        continue
                    exc = task.exception()
                    if exc is not None:
                        self._account_failure(spec, exc)
                    else:
                        pending_out.append((spec, task.result()))
                # 2. 非阻塞交付（满 = 反压计数，样本留在待投列表）
                remaining: list[tuple[ExecutionTaskSpec, Any]] = []
                for item in pending_out:
                    if self._queue.try_put(item):
                        self.counters.delivered += 1
                    else:
                        self.counters.delivery_backpressure += 1
                        remaining.append(item)
                pending_out = remaining
                # 3. top-up（halt/stop 停取新；待投积压达上限即暂停并计数）
                halted = self.halt_reason is not None
                if not stop.is_set() and not halted:
                    if len(pending_out) >= self._max_pending_out:
                        self.counters.topup_paused_by_backpressure += 1
                    else:
                        while len(in_flight) < self._concurrency:
                            try:
                                spec = self._task_source()
                            except Exception:  # noqa: BLE001 —— 源故障 = 系统性问题
                                self.counters.source_errors += 1
                                self.halt_reason = self.halt_reason or "task_source_failed"
                                break
                            if spec is None:  # 暂无新任务（持续 worker：下轮再询）
                                break
                            # F2-1a：dispatch 即铸造物理身份（replay 语义：
                            # 同一 rollout_execution_id 再次 dispatch 得新值）
                            seq = self._attempt_seq.get(spec.rollout_execution_id, 0) + 1
                            self._attempt_seq[spec.rollout_execution_id] = seq
                            spec = replace(
                                spec,
                                physical_attempt_id=(
                                    f"{spec.rollout_execution_id}#p{seq}-{uuid.uuid4().hex[:8]}"
                                ),
                                physical_attempt_seq=seq,
                            )
                            task = asyncio.create_task(self._guarded_execute(spec))
                            in_flight[task] = spec
                            self.counters.dispatched += 1
                # 4. 退出协议
                stopping = stop.is_set() or halted
                if stopping and not in_flight and not pending_out:
                    break
                if stopping and self._drain_timeout is not None:
                    if drain_deadline is None:
                        drain_deadline = self._clock() + self._drain_timeout
                    elif self._clock() >= drain_deadline:
                        # drain 超时：在途取消（下轮 reap 落账）；已完成未投样本
                        # 显式弃置记账——绝不静默等死
                        for task in in_flight:
                            task.cancel()
                        if not in_flight:
                            for item in pending_out:
                                self.counters.abandoned += 1
                                self.abandoned_deliveries.append(item)
                            pending_out = []
                            break
                await self._sleeper(self._poll)
        except asyncio.CancelledError:
            # worker 自身被取消：取消并收齐全部在途，逐个落账后再传播
            for task in in_flight:
                task.cancel()
            results = await asyncio.gather(*in_flight, return_exceptions=True)
            for (task, spec), outcome in zip(list(in_flight.items()), results):
                if isinstance(outcome, BaseException):
                    self._account_failure(spec, outcome)
                else:
                    self.counters.abandoned += 1
                    self.abandoned_deliveries.append((spec, outcome))
            for item in pending_out:
                self.counters.abandoned += 1
                self.abandoned_deliveries.append(item)
            raise
        if self.halt_reason is not None:
            raise WorkerHalted(
                self.halt_reason,
                f"worker 停机：{self.halt_reason}（unrecorded={len(self.unrecorded_failures)}, "
                f"source_errors={self.counters.source_errors}）——训练不得继续。",
            )

    def ledger_balanced(self) -> bool:
        """账目守恒的终态检查（N1 验收式，含 abandoned 显式项）。"""

        c = self.counters
        return c.dispatched == c.delivered + c.failed + c.abandoned
