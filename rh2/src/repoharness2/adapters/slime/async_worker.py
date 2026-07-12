"""FA-1：持续 RolloutExecution worker、有界交付队列、资源分类限额、
model proxy 边界（D-FA-3 内部重生成）、局部幂等重试白名单。

出处：05 计划 FA-1；机制论证见 `fully_async_rollout_pipeline_design_discussion.md`
§3.2/§4/§6 与 D-FA-3（proxy 内部重生成，codex 轮次 3 #1/#2 修正后的形态）。

与 slime 的绑定边界：本模块 **零 slime import**——所有运行时组件可注入
（task_source / execute_fn / coordinator / send_fn），本地故障注入测试
即 FA-1 验收；slime 侧 `--rollout-function-path` 的薄壳入口在 FA-5 短租
的 glue 层落地（slime 模块在本机不可 import，诚实分界与 FA-0 同款）。

对 stock fully_async 三缺陷的修复对应（表面契约测试 pin 的三处）：

- **N1 task 异常静默泄漏**（done_cb 只 log 后 return）→ 本 worker 把每个
  异常执行交给注入的 failure_sink（RolloutAttemptOutcome 的生产点），
  dispatched == delivered + failed 恒等式在测试里逐例断言；
- **N2 阻塞式 put 停摆 reap/top-up** → 交付走非阻塞 try_put + 待投列表，
  队列满只计数反压、暂停 top-up（反压传导到生产侧），reap 与循环本体
  永不停摆；
- **ABORTED 整组回队**（add_samples 组长断言对 fan-out 也会炸）→ 我方
  abort 处置整体在 proxy 层（内部重生成），worker 面不存在 ABORTED 样本，
  自然不依赖 stock 回队。
"""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from repoharness2.contracts.fa_runtime import (
    ModelCallAttempt,
    TrainingRuntimeWindow,
)

__all__ = [
    "BoundedDeliveryQueue",
    "ContinuousExecutionWorker",
    "DEFAULT_RETRY_WHITELIST",
    "ExecutionTaskSpec",
    "ModelCallProxy",
    "ProxyCallResult",
    "ResourceClassName",
    "ResourceLimits",
    "RetryAttemptRecord",
    "RetrySpec",
    "UnattributableModelCallError",
    "retry_local_operation",
]


# ---------------------------------------------------------------------------
# 资源分类限额（codex 轮次 3 #9：各类独立限额，不共用全局池）
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
    """按资源类分离的并发限额：一类打满只反压自己的上游，不饿死其他类。"""

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


@dataclass(frozen=True)
class RetrySpec:
    max_attempts: int  # 含首次
    base_delay_seconds: float = 0.5
    max_delay_seconds: float = 8.0


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
) -> Any:
    """白名单式局部重试（full-jitter 指数退避）。

    不在白名单的操作**只执行一次**（失败原样抛出）——"默认不重试"是
    讨论稿 §4 的硬规则；重试记录追加进 ledger（RolloutAudit 时间线的
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
        except Exception as exc:  # noqa: BLE001 —— 分类交给白名单与调用方
            is_final = attempt >= max_attempts
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


class CoordinatorView(Protocol):
    """TrainingRuntimeCoordinator 协议的消费端形状（FA-0 3b）。"""

    def current_window(self) -> TrainingRuntimeWindow: ...


class UnattributableModelCallError(RuntimeError):
    """不可归因中断：走缺员分支（RolloutAttemptOutcome missing_after_local_retry）。"""

    def __init__(self, reason_code: str, message: str) -> None:
        super().__init__(f"{reason_code}: {message}")
        self.reason_code = reason_code


@dataclass(frozen=True)
class ProxyCallResult:
    """一次逻辑轮的最终交付：只含 delivered attempt 的响应。"""

    response: Mapping[str, Any]
    attempts: tuple[ModelCallAttempt, ...]
    delivered_attempt_number: int


def _response_is_abort(response: Mapping[str, Any]) -> bool:
    """SGLang 以**正常 JSON**返回 abort 的形态（codex 轮次 3 #1：不只网络异常）。"""

    meta = response.get("meta_info")
    if not isinstance(meta, Mapping):
        return False
    finish = meta.get("finish_reason")
    if isinstance(finish, Mapping):
        return finish.get("type") == "abort"
    return finish == "abort"


def _version_int(version: str) -> int:
    return int(version, 10)


class ModelCallProxy:
    """D-FA-3：更新窗口 abort 的 proxy 内部重生成（CC 全程无感知）。

    守卫三条件（缺一按不可归因故障，05 计划 D-FA-3）：

    1. **失败与已知更新窗口重叠**：以协调器协议为唯一事实源——失败时刻
       窗口 phase != ACTIVE，或 update_epoch 相对发起时刻前进了（窗口在
       调用期间开启过）；
    2. **响应未交付**：结构性保证（本方法未返回即未交付；adapter 完整
       缓冲语义是物理依据）；
    3. **恢复后版本前进**：等到 phase==ACTIVE 且 active_version 数值大于
       发起时刻版本，且 fencing_token 与观测到的 abort 窗口一致。

    非 abort 的异常/超出重生成上限/等待超时 → UnattributableModelCallError
    （调用方按缺员处置）。半截输出只进 audit_artifacts，**绝不**进交付面
    （旧 token 悬挂负测试的断言点）。
    """

    def __init__(
        self,
        coordinator: CoordinatorView,
        *,
        max_regenerations: int = 3,
        wait_poll_seconds: float = 0.02,
        wait_timeout_seconds: float = 60.0,
        sleeper: Callable[[float], Awaitable[None]] = asyncio.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if max_regenerations < 1:
            raise ValueError("max_regenerations 必须 >= 1。")
        self._coordinator = coordinator
        self._max_regenerations = max_regenerations
        self._wait_poll = wait_poll_seconds
        self._wait_timeout = wait_timeout_seconds
        self._sleeper = sleeper
        self._clock = clock
        self.attempts_ledger: list[ModelCallAttempt] = []
        # 半截输出的审计存放点：attempt_id -> 原始响应/异常描述（不进交付面）
        self.audit_artifacts: dict[str, Any] = {}

    async def call(
        self,
        logical_turn_id: str,
        send_fn: Callable[[int], Awaitable[Mapping[str, Any]]],
        *,
        capture_record_ref: Callable[[int], str],
    ) -> ProxyCallResult:
        attempts: list[ModelCallAttempt] = []
        attempt_number = 0
        while True:
            attempt_number += 1
            attempt_id = f"{logical_turn_id}_a{attempt_number}"
            window_before = self._coordinator.current_window()
            failure: BaseException | None = None
            response: Mapping[str, Any] | None = None
            try:
                response = await send_fn(attempt_number)
            except Exception as exc:  # noqa: BLE001 —— 归因在下方守卫做
                failure = exc

            if response is not None and not _response_is_abort(response):
                meta = response.get("meta_info")
                weight_version = None
                if isinstance(meta, Mapping) and meta.get("weight_version") is not None:
                    weight_version = str(meta["weight_version"])
                if weight_version is None:
                    # delivered 必须携带版本（契约强制）；缺失按不可归因处置
                    self._record_failed(attempts, logical_turn_id, attempt_id, attempt_number)
                    raise UnattributableModelCallError(
                        "delivered_response_missing_weight_version",
                        f"{attempt_id}: 响应缺 meta_info.weight_version，provenance 不完整。",
                    )
                attempt = ModelCallAttempt(
                    logical_turn_id=logical_turn_id,
                    model_call_attempt_id=attempt_id,
                    attempt_number=attempt_number,
                    delivery_status="delivered",
                    capture_record_ref=capture_record_ref(attempt_number),
                    weight_version=weight_version,
                )
                attempts.append(attempt)
                self.attempts_ledger.extend(attempts)
                return ProxyCallResult(
                    response=response,
                    attempts=tuple(attempts),
                    delivered_attempt_number=attempt_number,
                )

            # 未交付：先按协议判定窗口重叠（守卫 1）
            window_now = self._coordinator.current_window()
            overlapped = (
                window_now.phase != "ACTIVE"
                or window_now.update_epoch > window_before.update_epoch
            )
            if not overlapped:
                self.audit_artifacts[attempt_id] = response if response is not None else repr(failure)
                self._record_failed(attempts, logical_turn_id, attempt_id, attempt_number)
                raise UnattributableModelCallError(
                    "no_overlapping_update_window",
                    f"{attempt_id}: 中断与任何更新窗口不重叠（协议 phase=ACTIVE 且 "
                    "epoch 未前进）——按缺员处置，不做透明重试。",
                )
            # abort 归因成立：记 non_delivered_aborted（窗口双凭据）
            self.audit_artifacts[attempt_id] = response if response is not None else repr(failure)
            attempts.append(
                ModelCallAttempt(
                    logical_turn_id=logical_turn_id,
                    model_call_attempt_id=attempt_id,
                    attempt_number=attempt_number,
                    delivery_status="non_delivered_aborted",
                    abort_update_epoch=window_now.update_epoch,
                    abort_fencing_token=window_now.fencing_token,
                    evidence_refs=[f"audit:{attempt_id}"],
                )
            )
            if attempt_number > self._max_regenerations:
                self._record_failed(attempts, logical_turn_id, f"{attempt_id}_cap", attempt_number)
                raise UnattributableModelCallError(
                    "max_regenerations_exceeded",
                    f"{logical_turn_id}: 连续 {attempt_number} 次被 abort——超过重生成上限，"
                    "按不可归因故障缺员（可能是更新风暴或窗口协议异常）。",
                )
            # 守卫 3：等 ACTIVE + 版本前进 + fencing 一致
            await self._wait_version_advance(
                attempts, logical_turn_id, attempt_number, window_before, window_now
            )

    def _record_failed(
        self,
        attempts: list[ModelCallAttempt],
        logical_turn_id: str,
        attempt_id: str,
        attempt_number: int,
    ) -> None:
        attempts.append(
            ModelCallAttempt(
                logical_turn_id=logical_turn_id,
                model_call_attempt_id=f"{attempt_id}_failed",
                attempt_number=attempt_number,
                delivery_status="non_delivered_failed",
                evidence_refs=[f"audit:{attempt_id}"],
            )
        )
        self.attempts_ledger.extend(attempts)

    async def _wait_version_advance(
        self,
        attempts: list[ModelCallAttempt],
        logical_turn_id: str,
        attempt_number: int,
        window_before: TrainingRuntimeWindow,
        abort_window: TrainingRuntimeWindow,
    ) -> None:
        try:
            version_floor = _version_int(window_before.active_version)
        except ValueError as exc:
            self._record_failed(
                attempts, logical_turn_id, f"{logical_turn_id}_nonnum", attempt_number
            )
            raise UnattributableModelCallError(
                "non_numeric_version_in_window", f"协议版本非数值：{exc}"
            ) from None
        deadline = self._clock() + self._wait_timeout
        while True:
            window = self._coordinator.current_window()
            if window.phase == "ACTIVE":
                advanced = _version_int(window.active_version) > version_floor
                fencing_consistent = (
                    window.update_epoch > abort_window.update_epoch
                    or window.fencing_token == abort_window.fencing_token
                )
                if advanced and fencing_consistent:
                    return
                if advanced and not fencing_consistent:
                    self._record_failed(
                        attempts, logical_turn_id, f"{logical_turn_id}_fence", attempt_number
                    )
                    raise UnattributableModelCallError(
                        "fencing_token_mismatch",
                        f"{logical_turn_id}: ACTIVE 窗口 fencing 与观测 abort 窗口不一致"
                        "（陈旧窗口误归因防线）。",
                    )
            if self._clock() >= deadline:
                self._record_failed(
                    attempts, logical_turn_id, f"{logical_turn_id}_timeout", attempt_number
                )
                raise UnattributableModelCallError(
                    "version_did_not_advance",
                    f"{logical_turn_id}: 等待 {self._wait_timeout}s 后版本未前进/未回 ACTIVE。",
                )
            await self._sleeper(self._wait_poll)


# ---------------------------------------------------------------------------
# 持续执行 worker（N1/N2 修复本体）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExecutionTaskSpec:
    """一次 RolloutExecution 的调度单元（身份 + 不透明载荷）。"""

    rollout_execution_id: str
    prompt_group_id: str
    member_slot: int
    payload: Any = None


@dataclass
class WorkerCounters:
    dispatched: int = 0
    delivered: int = 0
    failed: int = 0
    delivery_backpressure: int = 0
    topup_paused_by_backpressure: int = 0


class ContinuousExecutionWorker:
    """持续分派独立 RolloutExecution 的异步 worker（讨论稿 §6 拓扑的 A 节点）。

    不变量（测试逐条断言）：

    - **账目守恒**：dispatched == delivered + failed + in_flight + pending_out
      （任何时刻）；结束时 dispatched == delivered + failed——异常执行经
      failure_sink 落账（N1 修复），绝无静默消失。
    - **反压不停摆**：交付队列满时 reap 照常、循环照常，只暂停 top-up 并
      计数（N2 修复）；队列腾出后待投样本继续交付。
    - worker 不感知 PromptGroup 完整性（那是 FA-2 assembler 的职责）——
      它只保证"每次执行要么交付、要么显式失败落账"。
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
        sleeper: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        if concurrency < 1:
            raise ValueError("concurrency 必须 >= 1。")
        self._task_source = task_source
        self._execute_fn = execute_fn
        self._queue = delivery_queue
        self._failure_sink = failure_sink
        self._concurrency = concurrency
        self._max_pending_out = max_pending_out if max_pending_out is not None else concurrency
        self._poll = poll_interval_seconds
        self._sleeper = sleeper
        self.counters = WorkerCounters()

    async def run(self, stop: asyncio.Event) -> None:
        in_flight: dict[asyncio.Task[Any], ExecutionTaskSpec] = {}
        pending_out: list[tuple[ExecutionTaskSpec, Any]] = []
        while True:
            # 1. reap（永不因队列状态停摆）
            for task in [t for t in in_flight if t.done()]:
                spec = in_flight.pop(task)
                exc = task.exception()
                if exc is not None:
                    self.counters.failed += 1
                    try:
                        self._failure_sink(spec, exc)
                    except Exception:  # noqa: BLE001 —— sink 自身异常不允许炸 worker
                        pass
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
            # 3. top-up（反压传导：待投积压超限即暂停取新任务）
            if not stop.is_set():
                if len(pending_out) > self._max_pending_out:
                    self.counters.topup_paused_by_backpressure += 1
                else:
                    while len(in_flight) < self._concurrency:
                        spec = self._task_source()
                        if spec is None:  # 暂无新任务（持续 worker：下轮再询，不退出）
                            break
                        task = asyncio.create_task(self._execute_fn(spec))
                        in_flight[task] = spec
                        self.counters.dispatched += 1
            # 4. 退出条件：显式停止且账目清零（在途收完、待投投完）
            if stop.is_set() and not in_flight and not pending_out:
                return
            await self._sleeper(self._poll)

    def ledger_balanced(self) -> bool:
        """账目守恒的终态检查（N1 验收式）。"""

        return self.counters.dispatched == self.counters.delivered + self.counters.failed

