"""有界关停链（W5a，06 计划 §3 W5a 行 / 就绪稿 §2.6）。

本模块是**通用的关停执行器**，不认识任何具体组件：组件（评分队列、capture
wire、adapter HTTP 线程、容器、evidence sink）由持有者（`adapters/slime/bringup.py`
的 `BringupService.close()`）按顺序装配成 `ShutdownStep` 列表交给
`run_shutdown_chain` 执行。执行器只保证四条纪律：

1. **有界**：每一步都套 `asyncio.wait_for(step, timeout)`，超时记 `timeout`
   状态后继续下一步——关停永远不会因为某个组件挂死而无限等待；
2. **首因保留**：触发关停的异常（run-fatal / 取消）或第一个失败步是
   `first_cause`，之后的失败一律记为 `secondary_failures`，不覆盖首因；
3. **不中途放弃**：任何一步失败/超时都不会跳过后面的步骤（普通 evidence
   写失败尤其不能阻止容器清理，就绪稿 §2.6 / 06 W5a 行）；
4. **不抛异常**：`run_shutdown_chain` 永远返回 `ShutdownReport`（调用方通常在
   `finally` 里调它，抛异常会顶掉真正的首因）。幂等由持有者负责（bringup 缓存
   首次关停的 task/report）。

另外两个小件放在这里而不是 bringup 里，是为了让它们在没有 vendor slime 的普通
测试 lane 也能单测：

- `LifecycleState`：任务面的"关闭后禁 submit"状态 + 在飞执行登记（用
  `asyncio.current_task()` 拿到执行所在的 task 句柄，关停时按有界超时等待 /
  取消）+ run-fatal 通道接线（复用 `async_worker.fatal_halt_notifier` 这个
  既有的 task-local 通知位，不改 generate.py）；
- `close_inflight_executions`：在飞执行的"先等后取消再等"步骤，取消的执行只记
  事实（`termination_kind=owner_cancelled`，`completion_class=missing`），不做任何
  disposition（A5 归决策包 C）。

零 miles / slime import。
"""

from __future__ import annotations

import asyncio
import signal
import time
import traceback
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from repoharness2.adapters.slime.async_worker import fatal_halt_notifier
from repoharness2.contracts.fa_runtime import TERMINATION_KINDS_CONTROL

__all__ = [
    "CANCELLED_EXECUTION_TERMINATION_KIND",
    "CancelledExecutionFact",
    "InFlightExecutionFact",
    "LifecycleState",
    "ServiceClosedError",
    "ShutdownReport",
    "ShutdownStep",
    "ShutdownStepResult",
    "ShutdownTimeouts",
    "Skipped",
    "close_inflight_executions",
    "describe_exception",
    "install_signal_shutdown",
    "run_shutdown_chain",
]

# 取消的在飞执行记的 termination_kind：必须是 contracts 里已有的控制面族成员
# （fa_runtime.TERMINATION_KINDS_CONTROL = {"owner_cancelled"}）。这里只引用词汇，
# 不产 Outcome v2、不改 contracts；导入期核对一次，词汇漂移当场炸。
CANCELLED_EXECUTION_TERMINATION_KIND = "owner_cancelled"
assert CANCELLED_EXECUTION_TERMINATION_KIND in TERMINATION_KINDS_CONTROL, (
    "owner_cancelled 不在 TERMINATION_KINDS_CONTROL 里——contracts 词汇变了，关停事实需要重新对齐"
)


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ServiceClosedError(RuntimeError):
    """关闭后仍有人向任务面提交/解析 = typed 拒绝（不是 abort 形状、不是 Fatal）。

    `face` 标记被拒的是哪一面（task_resolve / grading_submit / bringup_get /
    custom_generate …），`reason_code` 供审计 grep。它是异常而不是"缺员样本"：
    关停后不该再有任何新执行形成对象，所以也不给它编 Outcome/disposition。
    """

    def __init__(self, face: str, message: str | None = None) -> None:
        self.face = face
        self.reason_code = f"{face}_rejected_service_closed"
        super().__init__(
            f"{self.reason_code}: {message or '服务已进入关停，拒绝新的 ' + face}"
        )


@dataclass(frozen=True)
class InFlightExecutionFact:
    """一次在飞执行的身份摘要（进入任务面时从样本 metadata 读，只读事实）。"""

    trajectory_id: str | None
    physical_attempt_id: str | None
    rollout_execution_id: str | None
    task_id: str | None
    entered_monotonic: float

    @classmethod
    def from_metadata(cls, metadata: Mapping[str, Any] | None, *, task_id: str | None = None,
                      clock: Callable[[], float] = time.monotonic) -> "InFlightExecutionFact":
        meta = metadata if isinstance(metadata, Mapping) else {}

        def _s(key: str) -> str | None:
            value = meta.get(key)
            return str(value) if value not in (None, "") else None

        return cls(
            trajectory_id=_s("rh2_rollout_execution_id") or _s("trajectory_id"),
            physical_attempt_id=_s("rh2_physical_attempt_id"),
            rollout_execution_id=_s("rh2_rollout_execution_id"),
            task_id=task_id if task_id is not None else (_s("rh2_task_id") or _s("instance_id")),
            entered_monotonic=clock(),
        )


@dataclass(frozen=True)
class CancelledExecutionFact:
    """关停取消了一次在飞执行——**只记事实**：

    - `termination_kind` 固定为控制面族的 `owner_cancelled`；
    - `completion_class` 固定为 `missing`（对象没有形成完整交付）；
    - `finished_after_cancel`：取消后该 task 是否在有界等待内跑完了自己的
      finally（receipt→cleanup 的 B5 顺序由 generate.py 自己保证；False 表示
      到等待截止时它还没跑完——属于残留，H9 判失败）。

    这里没有 disposition 字段：取消的 attempt 该怎么处置（drop/…）归 A5/决策包 C。
    """

    trajectory_id: str | None
    physical_attempt_id: str | None
    rollout_execution_id: str | None
    task_id: str | None
    in_flight_seconds: float
    finished_after_cancel: bool
    termination_kind: str = CANCELLED_EXECUTION_TERMINATION_KIND
    completion_class: str = "missing"

    def to_dict(self) -> dict[str, Any]:
        return {
            "trajectory_id": self.trajectory_id,
            "physical_attempt_id": self.physical_attempt_id,
            "rollout_execution_id": self.rollout_execution_id,
            "task_id": self.task_id,
            "in_flight_seconds": round(self.in_flight_seconds, 3),
            "finished_after_cancel": self.finished_after_cancel,
            "termination_kind": self.termination_kind,
            "completion_class": self.completion_class,
        }


class LifecycleState:
    """任务面的关停状态（BringupService 持有一份；无 vendor 依赖，可单测）。

    三个门 + 一张在飞表：

    - `accepting`：`stop_intake()` 后为 False，`require_accepting(face)` 抛
      `ServiceClosedError`——这是"关闭后禁 submit/resolve"的唯一判定点；
    - `grading_open`：`close_grading()` 后为 False——评分面单独关，是因为在飞
      执行在宽限期内还要把评分提交完，不能在停收新执行的同一刻把评分也拒掉；
    - `closed`：整条关停链跑完后置位（sticky，同进程不再有第二代）；
    - 在飞表：`enter_execution()` 把当前 asyncio task 登记进来（关停时按此表
      等待/取消），`exit_execution()` 注销；同时把 run-fatal 通知器挂到该 task
      的 context 上（`fatal_halt_notifier`），generate.py 的 `_notify_fatal_halt`
      会在进入异步 cleanup 之前同步调它——run-fatal 由此触发关停链。
    """

    def __init__(self, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self.accepting = True
        self.grading_open = True
        self.closed = False
        self._inflight: dict[asyncio.Task[Any], InFlightExecutionFact] = {}
        self.rejected_after_close: dict[str, int] = {}
        self.fatal_seen: list[BaseException] = []
        self.on_fatal: Callable[[BaseException], None] | None = None

    # ---- 门 ---------------------------------------------------------------
    def stop_intake(self) -> None:
        self.accepting = False

    def close_grading(self) -> None:
        self.grading_open = False

    def mark_closed(self) -> None:
        self.accepting = False
        self.grading_open = False
        self.closed = True

    def require_accepting(self, face: str) -> None:
        if not self.accepting:
            self.rejected_after_close[face] = self.rejected_after_close.get(face, 0) + 1
            raise ServiceClosedError(face)

    def require_grading_open(self, face: str = "grading_submit") -> None:
        if not self.grading_open:
            self.rejected_after_close[face] = self.rejected_after_close.get(face, 0) + 1
            raise ServiceClosedError(face)

    # ---- 在飞表 -----------------------------------------------------------
    def enter_execution(
        self, metadata: Mapping[str, Any] | None, *, task_id: str | None = None
    ) -> InFlightExecutionFact:
        """任务面解析入口调用：先过门，再登记当前 task，再挂 fatal 通知器。"""

        self.require_accepting("task_resolve")
        fact = InFlightExecutionFact.from_metadata(metadata, task_id=task_id, clock=self._clock)
        try:
            task = asyncio.current_task()
        except RuntimeError:  # 无运行中的 loop（同步测试面）：不登记
            task = None
        if task is not None:
            self._inflight[task] = fact
            self._install_fatal_notifier()
        return fact

    def exit_execution(self) -> InFlightExecutionFact | None:
        try:
            task = asyncio.current_task()
        except RuntimeError:
            return None
        if task is None:
            return None
        return self._inflight.pop(task, None)

    def inflight_snapshot(self) -> list[tuple[asyncio.Task[Any], InFlightExecutionFact]]:
        """未完成的在飞执行快照（已完成的顺手清掉——audit sink 没走到的异常
        路径不会让表无限长）。"""

        done = [t for t in self._inflight if t.done()]
        for t in done:
            self._inflight.pop(t, None)
        return list(self._inflight.items())

    @property
    def inflight_count(self) -> int:
        return len(self.inflight_snapshot())

    # ---- run-fatal 通道 ---------------------------------------------------
    def _install_fatal_notifier(self) -> None:
        previous = fatal_halt_notifier.get()
        if getattr(previous, "_rh2_lifecycle_owner", None) is self:
            return  # 同一 task 顺序跑多次执行：不叠加链

        state = self

        def _notify(exc: BaseException) -> None:
            state.fatal_seen.append(exc)
            if previous is not None:
                try:
                    previous(exc)
                except Exception:  # noqa: BLE001 —— 既有通知器的异常不掩盖 fatal 本身
                    pass
            if state.on_fatal is not None:
                state.on_fatal(exc)

        _notify._rh2_lifecycle_owner = state  # type: ignore[attr-defined]
        fatal_halt_notifier.set(_notify)


# ---------------------------------------------------------------------------
# 在飞执行：先等、后取消、再等（有界）
# ---------------------------------------------------------------------------


async def close_inflight_executions(
    state: LifecycleState,
    *,
    grace_seconds: float,
    cancel_wait_seconds: float,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    """返回事实字典：`cancelled`（CancelledExecutionFact 列表，含取消后是否跑完）、
    `finished_in_grace`（宽限内自己跑完的执行数）、`unfinished_after_cancel_wait`
    （取消后仍未结束的执行——残留）。

    取消发生在执行 task 上：generate.py 的 `except asyncio.CancelledError: raise`
    → finally 先持久化 receipt（disposition=cancelled）再清理容器（B5 顺序不变），
    这里不介入那条链，只等它跑完并记账。
    """

    snapshot = state.inflight_snapshot()
    tasks = [t for t, _ in snapshot]
    facts = dict(snapshot)
    if tasks and grace_seconds > 0:
        await asyncio.wait(tasks, timeout=grace_seconds)
    finished_in_grace = [t for t in tasks if t.done()]
    remaining = [t for t in tasks if not t.done()]
    for task in remaining:
        task.cancel()
    if remaining and cancel_wait_seconds > 0:
        await asyncio.wait(remaining, timeout=cancel_wait_seconds)
    now = clock()
    cancelled: list[CancelledExecutionFact] = []
    for task in remaining:
        fact = facts[task]
        cancelled.append(
            CancelledExecutionFact(
                trajectory_id=fact.trajectory_id,
                physical_attempt_id=fact.physical_attempt_id,
                rollout_execution_id=fact.rollout_execution_id,
                task_id=fact.task_id,
                in_flight_seconds=max(now - fact.entered_monotonic, 0.0),
                finished_after_cancel=task.done(),
            )
        )
    return {
        "inflight_at_shutdown": len(tasks),
        "finished_in_grace": len(finished_in_grace),
        "cancelled": [c.to_dict() for c in cancelled],
        "unfinished_after_cancel_wait": [c.to_dict() for c in cancelled if not c.finished_after_cancel],
    }


# ---------------------------------------------------------------------------
# 关停链
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ShutdownTimeouts:
    """每一步的上界（秒）。bringup 从 `RH2_SHUTDOWN_*_SEC` 环境变量读，缺省如下。

    数值口径：`inflight_cancel_wait` 必须容纳 generate.py 的 cleanup 超时
    （`SlimeBindingConfig.cleanup_timeout_seconds` 默认 120s）+ drop_session 5s，
    否则取消后的 finally 还没跑完就被记成残留（假红）。`inflight_grace` 刻意远小于
    agent 时间预算（600s）：关停时不等一整条 rollout 自然结束。
    """

    inflight_grace: float = 30.0
    inflight_cancel_wait: float = 150.0
    grading_drain: float = 60.0
    grading_manager: float = 60.0
    capture_sessions: float = 20.0
    adapter_http: float = 20.0
    container_residue: float = 10.0
    resource_closure: float = 15.0
    evidence: float = 10.0

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "ShutdownTimeouts":
        values: dict[str, float] = {}
        for name in cls.__dataclass_fields__:
            raw = env.get(f"RH2_SHUTDOWN_{name.upper()}_SEC")
            if raw is None or raw == "":
                continue
            try:
                value = float(raw)
            except ValueError as exc:
                raise ValueError(f"RH2_SHUTDOWN_{name.upper()}_SEC={raw!r} 不是数字") from exc
            if value < 0:
                raise ValueError(f"RH2_SHUTDOWN_{name.upper()}_SEC={raw!r} 不能为负")
            values[name] = value
        return cls(**values)


class Skipped:
    """步骤自己判定无事可做时返回它（例如评分队列从未启动）。"""

    def __init__(self, reason: str) -> None:
        self.reason = reason


StepKind = Literal["control", "cleanup", "evidence"]


@dataclass(frozen=True)
class ShutdownStep:
    """一步关停动作。`run` 返回 dict（事实，并入报告）/ `Skipped` / None。

    `kind`：`cleanup` 步失败 = 残留风险（报告 ok=False）；`evidence` 步失败 =
    普通证据写失败（记录、ok=False，但**绝不阻止**后续 cleanup）；`control`
    步（停收新任务）失败视同 cleanup 失败。三类在执行器里的处理完全一样
    ——都继续；区别只在报告归类，供 judge 区分"没清干净"与"没记下来"。
    """

    name: str
    run: Callable[[], Awaitable[Any]]
    timeout_seconds: float
    kind: StepKind = "cleanup"


@dataclass
class ShutdownStepResult:
    name: str
    kind: StepKind
    status: Literal["ok", "failed", "timeout", "skipped"]
    seconds: float
    detail: str | None = None
    facts: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "status": self.status,
            "seconds": round(self.seconds, 3),
            "detail": self.detail,
            "facts": self.facts,
        }


@dataclass
class ShutdownReport:
    reason: str
    trigger: str  # owner_close | run_fatal | signal | startup_rollback …
    started_at_utc: str = field(default_factory=_now_utc_iso)
    completed_at_utc: str | None = None
    first_cause: str | None = None
    first_cause_origin: str | None = None  # "trigger" | "step:<name>"
    secondary_failures: list[str] = field(default_factory=list)
    steps: list[ShutdownStepResult] = field(default_factory=list)
    evidence_failures: list[str] = field(default_factory=list)
    residue: dict[str, Any] = field(default_factory=dict)
    rejected_after_close: dict[str, int] = field(default_factory=dict)
    # patch 0013：关停开始之后（进行中或已完成）后到的原因/残留的并入记录——
    # 报告所有权在此，不建旁路 marker；每次并入一条 {phase, trigger, first_cause, ...}
    late_merges: list[dict[str, Any]] = field(default_factory=list)
    # I13（第 2 组 §3，owner 2026-09-09 已批）：rh2 负责的执行 / 资源 / 必要记录的完成事实（bringup 在
    # residue 装配之后填；`complete` 是它们的合取）。miles 侧"等待超时后来清完"的改判由 miles owner loop
    # 复查任务状态后调用 bringup.resolve_external_wait_residue 完成——本报告自己的 `ok` 口径不变。
    execution_closure: dict[str, Any] = field(default_factory=dict)
    # I13：复查通过后从 residue 移出的等待类快照（保留为历史诊断；不再计入 residue_free）
    resolved_wait_timeouts: list[dict[str, Any]] = field(default_factory=list)
    schema_id: str = "rh2.shutdown_report.v1"

    # ---- 记账口 -------------------------------------------------------------
    def note_failure(self, origin: str, detail: str) -> None:
        """首因只落一次；其后全部是次生。"""

        if self.first_cause is None:
            self.first_cause = detail
            self.first_cause_origin = origin
        else:
            self.secondary_failures.append(f"{origin}: {detail}")

    def note_evidence_failure(self, origin: str, detail: str) -> None:
        self.evidence_failures.append(f"{origin}: {detail}")
        self.note_failure(origin, detail)

    def step(self, name: str) -> ShutdownStepResult | None:
        for result in self.steps:
            if result.name == name:
                return result
        return None

    @property
    def cleanup_clean(self) -> bool:
        return all(
            r.status in ("ok", "skipped") for r in self.steps if r.kind in ("cleanup", "control")
        )

    @property
    def residue_free(self) -> bool:
        return not any(bool(v) for v in self.residue.values())

    @property
    def residue_free_excluding_external_wait(self) -> bool:
        """I13：不计 miles 侧等待类快照（`unfinished_executions` 里 source=miles_rollout_fn 的行与
        `rollout_fn_shutdown_failure` 对象）时，其余残留是否为空。rh2 自己的未完成执行仍算残留。"""

        for key, value in self.residue.items():
            if key == "rollout_fn_shutdown_failure":
                continue
            if key == "unfinished_executions":
                if any((row or {}).get("source") != "miles_rollout_fn" for row in value or []):
                    return False
                continue
            if value:
                return False
        return True

    @property
    def ok_if_wait_residue_resolved(self) -> bool:
        """I13：若 miles 侧等待类残留已由其 owner 复查确认消失，本报告其余部分是否允许成功退出——
        清理步全绿、除等待快照外无残留、证据全部写成功、无首因、且 execution_closure 完整。"""

        return (
            self.cleanup_clean
            and self.residue_free_excluding_external_wait
            and not self.evidence_failures
            and self.first_cause is None
            and bool(self.execution_closure.get("complete"))
        )

    @property
    def ok(self) -> bool:
        """H9 口径：清理步全绿 + 无残留 + 证据全部写成功 + 触发不是故障。"""

        return (
            self.cleanup_clean
            and self.residue_free
            and not self.evidence_failures
            and self.first_cause is None
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "reason": self.reason,
            "trigger": self.trigger,
            "started_at_utc": self.started_at_utc,
            "completed_at_utc": self.completed_at_utc,
            "ok": self.ok,
            "cleanup_clean": self.cleanup_clean,
            "residue_free": self.residue_free,
            "first_cause": self.first_cause,
            "first_cause_origin": self.first_cause_origin,
            "secondary_failures": list(self.secondary_failures),
            "evidence_failures": list(self.evidence_failures),
            "residue": dict(self.residue),
            "execution_closure": dict(self.execution_closure),
            "ok_if_wait_residue_resolved": self.ok_if_wait_residue_resolved,
            "resolved_wait_timeouts": [dict(r) for r in self.resolved_wait_timeouts],
            "rejected_after_close": dict(self.rejected_after_close),
            "late_merges": [dict(m) for m in self.late_merges],
            "steps": [s.to_dict() for s in self.steps],
        }


def describe_exception(exc: BaseException) -> str:
    """异常 → 报告用的一行描述（类型 + reason_code + 前 300 字）。"""

    code = getattr(exc, "reason_code", None)
    head = f"{type(exc).__name__}({code})" if code else type(exc).__name__
    return f"{head}: {str(exc)[:300]}"


async def run_shutdown_chain(
    steps: list[ShutdownStep],
    *,
    reason: str,
    trigger: str,
    first_cause: BaseException | None = None,
    clock: Callable[[], float] = time.monotonic,
    report: ShutdownReport | None = None,
) -> ShutdownReport:
    """按序执行全部步骤（见模块 docstring 四条纪律）。永不抛异常。"""

    report = report if report is not None else ShutdownReport(reason=reason, trigger=trigger)
    if first_cause is not None:
        report.note_failure("trigger", describe_exception(first_cause))
    for step in steps:
        started = clock()
        try:
            outcome = await asyncio.wait_for(step.run(), timeout=step.timeout_seconds)
        except asyncio.CancelledError:
            # 关停链自己被取消（进程退出路径）：先把这一步记成 timeout 再传播，
            # 让已经写出去的报告/调用方拿到的部分报告仍然如实。
            report.steps.append(
                ShutdownStepResult(step.name, step.kind, "timeout", clock() - started,
                                   detail="shutdown chain cancelled while running this step")
            )
            raise
        except (TimeoutError, asyncio.TimeoutError):
            elapsed = clock() - started
            detail = f"step timed out after {step.timeout_seconds}s"
            report.steps.append(ShutdownStepResult(step.name, step.kind, "timeout", elapsed, detail=detail))
            if step.kind == "evidence":
                report.note_evidence_failure(f"step:{step.name}", detail)
            else:
                report.note_failure(f"step:{step.name}", detail)
            continue
        except Exception as exc:  # noqa: BLE001 —— 关停链收集而不扩散
            elapsed = clock() - started
            detail = describe_exception(exc) + " | " + traceback.format_exc(limit=3).strip().splitlines()[-1][:200]
            report.steps.append(ShutdownStepResult(step.name, step.kind, "failed", elapsed, detail=detail))
            if step.kind == "evidence":
                report.note_evidence_failure(f"step:{step.name}", detail)
            else:
                report.note_failure(f"step:{step.name}", detail)
            continue
        elapsed = clock() - started
        if isinstance(outcome, Skipped):
            report.steps.append(
                ShutdownStepResult(step.name, step.kind, "skipped", elapsed, detail=outcome.reason)
            )
        else:
            facts = dict(outcome) if isinstance(outcome, Mapping) else None
            report.steps.append(ShutdownStepResult(step.name, step.kind, "ok", elapsed, facts=facts))
    report.completed_at_utc = _now_utc_iso()
    return report


# ---------------------------------------------------------------------------
# 信号触发（SIGTERM → 关停链）
# ---------------------------------------------------------------------------


def install_signal_shutdown(
    loop: asyncio.AbstractEventLoop,
    on_signal: Callable[[str], Awaitable[Any]],
    *,
    signals: tuple[int, ...] = (signal.SIGTERM,),
) -> Callable[[], None]:
    """把信号接到关停链上：收到信号即在 loop 上调度 `on_signal("SIGTERM")`。

    返回一个撤销函数（恢复默认处置）。只在 loop 所在线程（主线程）可用，这是
    `loop.add_signal_handler` 的既有限制。是否默认安装由持有者决定（bringup 里
    是 opt-in：Ray worker 自带 SIGTERM 处置，无条件覆盖属于改变运行边界）。
    """

    scheduled: dict[int, asyncio.Task[Any]] = {}

    def _make(signum: int):
        name = signal.Signals(signum).name

        def _handler() -> None:
            if signum in scheduled and not scheduled[signum].done():
                return  # 重复信号：不重复调度
            scheduled[signum] = loop.create_task(on_signal(name))

        return _handler

    for signum in signals:
        loop.add_signal_handler(signum, _make(signum))

    def _uninstall() -> None:
        for signum in signals:
            try:
                loop.remove_signal_handler(signum)
            except Exception:  # noqa: BLE001 —— loop 已关等情况：尽力恢复
                pass
            signal.signal(signum, signal.SIG_DFL)

    return _uninstall
