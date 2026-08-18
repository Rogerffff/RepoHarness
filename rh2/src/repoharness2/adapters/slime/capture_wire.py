"""A4 捕获接线：替换 slime `call_sglang_generate` + 包装 `record_turn`。

差异假设 1 的真实落地（S1-6 mock 假设 -> S1-7a 实机）：

1. **替换而非包装**：stock `call_sglang_generate`（slime/agent/adapters/
   common.py:442）把原始响应 meta_info 消费后丢弃（TurnRecord 只留
   prompt_ids/output_ids/logprobs/finish_reason），且请求体只带
   `return_logprob=True`——top-p tape / routing tape 的请求 flag 根本不在
   stock 请求里。所以必须整函数替换（该函数刻意做成模块级可 monkeypatch，
   `BaseAdapter._run_turn` 按名字在模块命名空间解析）。
2. **tape flag 的确切 wire 位置（假设 1/9 的实测结论）**：
   - top-p tape：`sampling_params.custom_params = {"return_top_p_token_ids": True}`
     （slime GenerateState 对 rollout_top_p != 1.0 的自有注入同一位置，
     sglang_rollout.py:107-108；S1-0 探针实测同形）
   - routing tape：请求体顶层 `"return_routed_experts": true`（S1-0 探针）
   两个 rh2 会话默认键 `return_top_p_token_ids` / `return_routed_experts`
   在发送前从 sampling_params **弹出**并翻译成上述 wire 形态（stock SGLang
   的 SamplingParams 不认识这两个键，直传会被静默忽略或报错）。
3. **capture 提交时点 = record_turn（响应 flush 之后）**：_run_turn 先 flush
   响应再 record_turn；客户端断连时 record_turn 不执行、该轮不进轨迹树。
   捕获若在 /generate 返回时就提交，会出现"capture 有这轮、轨迹没有"的
   错位（backfill 的 mask 段 fail-closed 会当场炸）。所以 /generate 返回时
   只 **暂存**（stage），record_turn 真正发生时才提交（commit）给 hook。
4. **weight_version（假设 4 实测）**：slime patch 引擎每次 /generate 的
   meta_info 自带 `weight_version`；按轮收集进 registry 作 handshake /
   staleness 的事实源证据。
"""

from __future__ import annotations

import asyncio
import dataclasses
import uuid
from typing import Any

import aiohttp
from aiohttp import web as aiohttp_web

from repoharness2.adapters.slime.async_worker import (
    ModelCallProxy,
    SessionPoisonRegistry,
)
from repoharness2.adapters.slime.generate import GenerationCaptureHook


@dataclasses.dataclass
class PendingTurn:
    prompt_ids: list[int]
    capture_params: dict[str, Any]
    raw_response: dict[str, Any]
    weight_version: str | None
    request_id: str  # SGLang rid（本轮请求身份，P0-6 去覆盖的键）
    proxy_result: Any = None  # ProxyCallResult：commit 成功才 finalize（P0-1）


@dataclasses.dataclass(frozen=True)
class SessionPlaneDrainResult:
    """F2-3 批 2a：单 owner drain 的 typed 内部交接对象（持久形态是
    SessionDrainReceiptV1；本对象是 owner→orchestrator 的进程内契约）。

    orchestrator 消费规则（codex 批 2 首验收）：owner 缺失/异常/返回非本
    类型/paid 矛盾 = **内部契约损坏 → Fatal → WorkerHalted**；类型正确但
    事实不干净（inflight 未归零/pending 残留/poison）= 单 execution 的
    drain 失败（成员级收口），不冒充干净。"""

    physical_attempt_id: str | None
    revoke_enforced: bool
    inflight_at_drain_start: int
    inflight_zero_confirmed: bool
    pending_turns: int
    unfinalized_drafts: int
    poison_clean: bool
    late_requests_rejected_after_revoke: int
    turn_seq_high_water: int
    weight_versions_seen: list[str]
    drain_owner: str


def make_threadsafe_session_drain_owner(
    registry: "CaptureRegistry", loop: "asyncio.AbstractEventLoop"
):
    """把 registry.drain_session_plane 绑定到 **adapter event loop** 上执行
    （run_coroutine_threadsafe），返回 orchestrator loop 可 await 的 owner
    callable。bringup 用 app_handle.loop 构造。"""

    async def owner(sid: str) -> SessionPlaneDrainResult:
        cfut = asyncio.run_coroutine_threadsafe(
            registry.drain_session_plane(sid), loop
        )
        return await asyncio.wrap_future(cfut)

    return owner



class CaptureWireOwnershipError(RuntimeError):
    """capture wire 进程级单代所有权违反（勘误 4：不同 registry 重绑）。"""

class UnknownSessionError(RuntimeError):
    """未知/未注册 SID 的模型调用（codex 轮次 13 P0-1）：此前直连 SGLang
    ——绕过 proxy/poison/版本/deadline/限额/capture 的未登记推理旁路，
    正式服务一律 fail-closed（探针会话走显式注册，不复用旁路）。"""

    def __init__(self, session_id) -> None:
        super().__init__(
            f"unknown_session: {session_id!r} 不在 active registry——"
            "未注册会话不得触达推理引擎（fail-closed）。"
        )
        self.session_id = session_id


class DuplicateActiveSessionError(RuntimeError):
    """健康 SID 并发重复注册（codex 轮次 12）：稳定 SID（task+index+group）
    在完全异步下并发出现会静默覆盖 hook/pending/weight_versions/artifact
    ——临时守卫直接拒绝；FA-2 第一项用 execution 唯一身份根治。"""

    def __init__(self, session_id: str) -> None:
        super().__init__(
            f"duplicate_active_session: {session_id} 已有活跃注册——并发同 SID "
            "execution 在唯一身份落地前不可安全共存。"
        )
        self.session_id = session_id


class CapturePendingOverlapError(RuntimeError):
    """同 session 并发暂存重叠（codex 轮次 9 P0-2）：slime 把同 session 请求
    作为独立 asyncio task 并发执行（common.py inflight，无 per-session 串行
    锁），record_turn 按**完成序**到达——FIFO 弹最旧会把请求 A 的 token/
    logprob/weight_version 记到请求 B 名下（结构合法但内容串账的训练轨迹，
    比丢数据更危险，codex 探针确定性复现）。request 级归属（record_turn 传
    request_id，需改 slime 签名）是 FA-2 第一验收项；落地前 overlap 一律
    fail-closed：poison session + 本请求失败 + execution 缺员。"""

    def __init__(self, session_id: str) -> None:
        super().__init__(
            f"capture_pending_overlap: session {session_id} 已有未 commit 的暂存轮"
            "——request 级归属落地前，并发同 session 模型调用不可安全捕获。"
        )
        self.session_id = session_id


class CaptureRegistry:
    """sid -> (hook, 暂存轮, 按轮 weight_version) 的进程级登记表。"""

    def __init__(self) -> None:
        import threading

        # 轮次 13 P0-3：register/assert/unregister 在 AsyncLoopThread，
        # stage/commit 在 aiohttp 线程——共享容器全部走短临界区锁（只移动
        # 所有权，hook/磁盘/回调都在锁外）。单 owner 消息化重构留 FA-2。
        self._lock = threading.Lock()
        self.hooks: dict[str, GenerationCaptureHook] = {}
        # 容器保持 list（FA-2 request 级归属会改成 rid 映射），但 stage 对已有
        # 未 commit 暂存 **fail-closed**（CapturePendingOverlapError）——不做
        # FIFO 猜测。不变量：len(pending[sid]) <= 1。
        self.pending: dict[str, list[PendingTurn]] = {}
        self.weight_versions: dict[str, list[str]] = {}
        self.stats = {
            "staged": 0,
            "committed": 0,
            "dropped_uncommitted": 0,
            "concurrent_overlap_seen": 0,
        }
        # FA-1 follow-up（codex 轮次 7/8）：proxy 接入真实 HTTP 链的挂点。
        self.model_call_proxy: ModelCallProxy | None = None
        self.poison = SessionPoisonRegistry()
        self.session_deadlines: dict[str, float] = {}
        self.default_session_budget_seconds: float | None = None
        self._turn_seq: dict[str, int] = {}
        # F2-1a：sid → physical_attempt_id 映射（orchestrator 经注入点登记；
        # wire 读出后随每条 ModelCallAttempt 落账；unregister 清理）
        self._physical_attempt_ids: dict[str, str] = {}
        # F2-2：quiescence 屏障第一步——已撤销 capability 集合。撤销与
        # unregister 分离：revoke 后 guard 立即拒新请求（HTTP 层），但
        # hook/暂存仍在场供 drain/对账；unregister 时一并清（会话关闭即
        # 失效，之后未知 sid 由 guard 的 unknown 分支兜底）。
        self._revoked: set[str] = set()
        # F2-3 批 1：撤销后被 guard 拒掉的迟到请求计数（撤销真实生效的
        # 运行期证据，进 SessionDrainReceiptV1）。unregister 一并清理。
        self.revoked_rejections: dict[str, int] = {}
        # F2-3 批 2a：guard 层 in-flight 计数（授权通过即计入，finally
        # 退账；drain owner 在 adapter loop 上等它归零）
        self._inflight: dict[str, int] = {}
        self._inflight_zero_events: dict[str, Any] = {}
        # F2-2 复核 P0-3：capability token 只做**认证**——guard 验证后把
        # Authorization 重写为非秘密 internal sid，slime 的 store/closed/
        # turn-count/日志/routing key/异常消息全部只见 internal sid。
        # token→internal 映射与 hook 同事务绑定/清理。
        self._capability_tokens: dict[str, str] = {}
        # 绑定了 token 的 internal sid 集合：这些会话**只能**经 token 认证
        # 进入——internal sid 非秘密（进日志/审计），直接当 bearer 必须拒
        self._capability_required: set[str] = set()

    def register(
        self,
        sid: str,
        hook: GenerationCaptureHook,
        physical_attempt_id: str | None = None,
        capability_token: str | None = None,
    ) -> None:
        """会话注册（F2-1a 熔断后所有权收敛版）：hook 与 paid **单锁原子
        绑定**，同生命周期——重复 SID 在任何状态修改前拒绝；绑定发生在
        open_session 事务内（materialize 之后），underlying open 失败走
        既有 rollback unregister 连带清 paid。**不存在预登记**，所以
        materialize 失败不可能残留映射（codex F2-1a 二审 P0 的根因修）。"""

        # 轮次 11 身份兜底：中毒 SID（含归档）不得复用注册
        self.poison.check(sid)
        with self._lock:
            if sid in self.hooks:
                raise DuplicateActiveSessionError(sid)  # 任何状态修改前拒绝
            self.hooks[sid] = hook
            self.weight_versions[sid] = []
            self.pending.setdefault(sid, [])
            if physical_attempt_id is not None:
                self._physical_attempt_ids[sid] = physical_attempt_id
            if capability_token is not None:
                self._capability_tokens[capability_token] = sid
                self._capability_required.add(sid)

    def assert_session_clean(self, sid: str) -> None:
        """评分/Gate 前边界断言（codex 轮次 12 P0 层 1）：该 SID 不得残留
        pending 暂存轮或 unfinalized delivered draft——任一在场说明交付账
        不完整（flush 失败/abandon 未闭合），先 poison 再抛，execution 缺员。"""

        problems: list[str] = []
        with self._lock:
            pending_count = len(self.pending.get(sid) or [])
            # P0-2：attempt 命名空间 = paid（见 rh2_call_sglang_generate 的
            # execution_scope），boundary 也按 paid 前缀查
            scope = self._physical_attempt_ids.get(sid) or sid
        if pending_count:
            problems.append(f"pending_turns={pending_count}")
        proxy = self.model_call_proxy
        if proxy is not None:
            stale = [a for a in proxy.unfinalized_deliveries if a.startswith(f"{scope}/")]
            if stale:
                problems.append(f"unfinalized_drafts={sorted(stale)}")
        if problems:
            self.poison.poison(sid, "capture_boundary_unclean")
            raise RuntimeError(
                f"capture_boundary_unclean: session {sid} 交付账不完整（{'; '.join(problems)}）"
                "——评分/Gate 前拒绝，execution 缺员。"
            )

    def single_pending_turn(self, sid: str) -> PendingTurn:
        """取恰好一条暂存轮（启动探针/单轮消费的形状权威）。

        codex 轮次 11 P0-1：pending 是 list[PendingTurn]——旧探针代码按单
        对象取 `.raw_response` 会在真实启动时 AttributeError。这里收口形状
        断言：无暂存或多于一条都显式报错。"""

        with self._lock:
            queue = list(self.pending.get(sid) or [])
        if not queue:
            raise RuntimeError(
                f"session {sid} 无暂存轮——capture wire 未接上（A4）或已被 commit。"
            )
        if len(queue) != 1:
            raise RuntimeError(
                f"session {sid} 暂存轮数量异常：{len(queue)}（期望恰好 1）。"
            )
        return queue[0]

    def physical_attempt_id_for(self, sid: str | None) -> str | None:
        if sid is None:
            return None
        with self._lock:
            return self._physical_attempt_ids.get(sid)

    def snapshot_weight_versions(self) -> dict[str, list[str]]:
        """锁内复制全部会话的版本序列（codex 轮次 14 仍需修正 1：provider
        此前无锁遍历 dict.values()，并发 commit/unregister 会
        `dictionary changed size during iteration`——变成未归因 adapter 500
        而不是干净缺员）。"""

        with self._lock:
            return {sid: list(vs) for sid, vs in self.weight_versions.items()}

    def session_deadline(self, sid: str | None) -> float | None:
        """会话 deadline（episode 预算传播）。首次调用即按默认预算起表——
        第一次模型调用 ≈ harness 启动后数秒，余量记入 notes。"""

        if sid is None:
            return None
        import time as _time

        with self._lock:
            if sid not in self.session_deadlines:
                if self.default_session_budget_seconds is None:
                    return None
                self.session_deadlines[sid] = (
                    _time.monotonic() + self.default_session_budget_seconds
                )
            return self.session_deadlines[sid]

    def next_turn_seq(self, sid: str | None) -> int:
        key = sid or "default"
        with self._lock:
            self._turn_seq[key] = self._turn_seq.get(key, 0) + 1
            return self._turn_seq[key]

    def resolve_capability(self, token: str | None) -> str | None:
        """认证：token → internal sid（未知 token → None，guard 拒绝）。"""

        if token is None:
            return None
        with self._lock:
            return self._capability_tokens.get(token)

    def revoke(self, sid: str) -> None:
        """撤销 capability（quiescence 序列第一步：HTTP 层拒新请求）。

        幂等；对未注册 sid 也可调用（撤销一个从未开张的凭证无害）。
        不清任何账目——drain/边界断言仍按原序进行。"""

        with self._lock:
            self._revoked.add(sid)

    def is_revoked(self, sid: str) -> bool:
        with self._lock:
            return sid in self._revoked

    def note_revoked_rejection(self, sid: str) -> None:
        """guard 在 revoked 分支计一笔迟到请求（F2-3 drain receipt 证据）。"""

        with self._lock:
            self.revoked_rejections[sid] = self.revoked_rejections.get(sid, 0) + 1

    # ---- F2-3 批 2a：adapter event-loop 单 owner drain -------------------
    # inflight 追踪在 guard middleware（授权通过与计入之间无 await——同
    # loop 原子），drain owner 在 adapter loop 上执行 revoke→等 inflight
    # 归零→账目读取，返回 typed 结果。消灭"多锁快照看不到真实 HTTP
    # inflight"的假阳性窗口（批 1 复核 P1-1 根修）。

    def _inflight_enter(self, sid: str) -> None:
        with self._lock:
            self._inflight[sid] = self._inflight.get(sid, 0) + 1

    def _inflight_exit(self, sid: str) -> None:
        event: Any = None
        with self._lock:
            n = self._inflight.get(sid, 0) - 1
            if n <= 0:
                self._inflight.pop(sid, None)
                event = self._inflight_zero_events.get(sid)
            else:
                self._inflight[sid] = n
        if event is not None:
            event.set()

    async def drain_session_plane(
        self, sid: str, *, timeout_seconds: float = 30.0
    ) -> "SessionPlaneDrainResult":
        """单 owner drain（**必须在 adapter event loop 上执行**——
        middleware 的 inflight 计数在同一 loop，等待与读数不会撕裂）。

        步骤：revoke（幂等；guard 即拒新）→ 等 rh2 自己观测的 inflight
        归零（超时 = 不干净结果，交调用方按成员级失败收口，不冒充干净）
        → 账目读取 → typed 结果。"""

        import asyncio as _asyncio

        self.revoke(sid)
        with self._lock:
            inflight_start = self._inflight.get(sid, 0)
            event: _asyncio.Event | None = None
            if inflight_start > 0:
                event = self._inflight_zero_events.setdefault(sid, _asyncio.Event())
        zero_confirmed = inflight_start == 0
        if event is not None:
            try:
                await _asyncio.wait_for(event.wait(), timeout=timeout_seconds)
                zero_confirmed = True
            except TimeoutError:
                zero_confirmed = False
            finally:
                with self._lock:
                    self._inflight_zero_events.pop(sid, None)
        snap = self.drain_snapshot(sid)
        return SessionPlaneDrainResult(
            physical_attempt_id=snap["physical_attempt_id"],  # type: ignore[arg-type]
            revoke_enforced=bool(snap["revoke_enforced"]),
            inflight_at_drain_start=inflight_start,
            inflight_zero_confirmed=zero_confirmed,
            pending_turns=int(snap["pending_turns"]),  # type: ignore[arg-type]
            unfinalized_drafts=int(snap["unfinalized_drafts"]),  # type: ignore[arg-type]
            poison_clean=bool(snap["poison_clean"]),
            late_requests_rejected_after_revoke=int(
                snap["late_requests_rejected_after_revoke"]  # type: ignore[arg-type]
            ),
            turn_seq_high_water=int(snap["turn_seq_high_water"]),  # type: ignore[arg-type]
            weight_versions_seen=list(snap["weight_versions_seen"]),  # type: ignore[arg-type]
            drain_owner="adapter_event_loop",
        )

    def drain_snapshot(self, sid: str) -> dict[str, object]:
        """F2-3 批 1：会话面排空账目快照（drain + 边界断言之后读取，供
        SessionDrainReceiptV1 构造）。纯读取，不改任何状态。"""

        with self._lock:
            pending_count = len(self.pending.get(sid) or [])
            scope = self._physical_attempt_ids.get(sid) or sid
            facts: dict[str, object] = {
                "pending_turns": pending_count,
                "revoke_enforced": sid in self._revoked,
                "late_requests_rejected_after_revoke": self.revoked_rejections.get(sid, 0),
                "turn_seq_high_water": self._turn_seq.get(sid, 0),
                "weight_versions_seen": list(self.weight_versions.get(sid) or []),
                "physical_attempt_id": self._physical_attempt_ids.get(sid),
            }
        proxy = self.model_call_proxy
        drafts = 0
        if proxy is not None:
            drafts = sum(
                1 for a in proxy.unfinalized_deliveries if a.startswith(f"{scope}/")
            )
        facts["unfinalized_drafts"] = drafts
        facts["poison_clean"] = not self.poison.is_poisoned(sid)
        return facts

    def unregister(self, sid: str) -> None:
        with self._lock:
            self._revoked.discard(sid)
            self.revoked_rejections.pop(sid, None)
            self._capability_tokens = {
                t: i for t, i in self._capability_tokens.items() if i != sid
            }
            self._capability_required.discard(sid)
            self.hooks.pop(sid, None)
            leftover_locked = self.pending.pop(sid, None) or []
            self.session_deadlines.pop(sid, None)
            self._turn_seq.pop(sid, None)
            self.weight_versions.pop(sid, None)
            self._physical_attempt_ids.pop(sid, None)
        self._finish_unregister(sid, leftover_locked)
        return

    def _finish_unregister(self, sid: str, leftover: list[PendingTurn]) -> None:
        # P0-1（codex 轮次 8）：暂存但未 commit 的轮 = 未真正交付给 CC——
        # 显式 abandon（锁外：涉及 sink 磁盘写）。
        if any(turn.proxy_result is not None for turn in leftover):
            # 轮次 12 P0 层 2：有未 commit 的 delivered draft = 该 execution
            # 的交付账不完整——**先 poison** 再尝试持久化 abandon evidence
            #（sink 再失败也不会出现"训练样本带着 pending draft 继续走"）
            self.poison.poison(sid, "uncommitted_draft_at_unregister")
        for turn in leftover:
            self.stats["dropped_uncommitted"] += 1
            if turn.proxy_result is not None:
                try:
                    turn.proxy_result.abandon_delivered("session_unregistered_before_commit")
                except ValueError:
                    pass  # 已 finalize/abandon（幂等）
                except Exception as exc:  # noqa: BLE001 - abandon 已先关账（事务化）
                    self.stats["abandon_evidence_failures"] = (
                        self.stats.get("abandon_evidence_failures", 0) + 1
                    )
                    print(f"[rh2-capture] abandon evidence 持久化失败 sid={sid}: {exc}")
        # session_deadlines/_turn_seq/weight_versions 已在锁内随会话清理；
        # poison 的归档（release）由 orchestrator 在容器清理后触发（轮次 11）。

    def stage(self, sid: str | None, turn: PendingTurn) -> None:
        if sid is None:
            return  # 非 rh2 会话不捕获（未知 SID 的拒绝在 wire 入口，轮次 13 P0-1）
        with self._lock:
            if sid not in self.hooks:
                return
            queue = self.pending.setdefault(sid, [])
            overlap = bool(queue)
            stale = queue.pop(0) if overlap else None
            if not overlap:
                queue.append(turn)
                self.stats["staged"] += 1
                return
        if overlap:
            # P0-2（codex 轮次 9）：overlap = 并发同 session 请求在飞——FIFO
            # 猜测会串账，fail-closed：poison + 两轮 abandon（锁外：磁盘写；
            # 轮次 14：stats 增量补锁）。
            with self._lock:
                self.stats["concurrent_overlap_seen"] += 1
                self.stats["dropped_uncommitted"] += 1
            self.poison.poison(sid, "capture_pending_overlap")
            if stale.proxy_result is not None:
                try:
                    stale.proxy_result.abandon_delivered("capture_pending_overlap")
                except ValueError:
                    pass  # 已定案（幂等）
            if turn.proxy_result is not None:
                try:
                    turn.proxy_result.abandon_delivered("capture_pending_overlap")
                except ValueError:
                    pass
            raise CapturePendingOverlapError(sid)
        queue.append(turn)
        self.stats["staged"] += 1

    def commit(self, sid: str) -> None:
        """PENDING -> COMMITTING -> COMMITTED/ABANDONED（轮次 13 P0-3 事务化）。

        锁内只摘取所有权；hook（capture store/tape 构造）在锁外执行——
        中点异常不再留永久悬挂 draft（turn 持有 proxy_result，事务化
        abandon 先关账再传播）；hook 后复检会话仍在（unregister 竞态时
        弃置本轮，不给已销毁会话追加版本——KeyError 竞态的根修）。"""

        with self._lock:
            hook = self.hooks.get(sid)
            queue = self.pending.get(sid)
            if hook is None or not queue:
                return
            turn = queue.pop(0)  # COMMITTING：所有权已移出共享容器
        try:
            hook.on_generate_response(
                prompt_token_ids=turn.prompt_ids,
                sampling_params=turn.capture_params,
                response=turn.raw_response,
            )
        except Exception:
            # 中点异常：poison + 关闭 draft（最小 FailureFact），再传播
            self.poison.poison(sid, "capture_commit_hook_failed")
            if turn.proxy_result is not None:
                try:
                    turn.proxy_result.abandon_delivered("capture_commit_hook_failed")
                except Exception:  # noqa: BLE001 - abandon 已事务化（先关账）
                    self.stats["abandon_evidence_failures"] = (
                        self.stats.get("abandon_evidence_failures", 0) + 1
                    )
            raise
        with self._lock:
            still_registered = sid in self.hooks
            if still_registered and turn.weight_version is not None:
                self.weight_versions[sid].append(turn.weight_version)
        if not still_registered:
            # commit 与 unregister 竞态：会话已销毁——本轮不进树后账，
            # poison + abandon（不静默复活已清理的会话容器）
            self.poison.poison(sid, "commit_after_unregister")
            if turn.proxy_result is not None:
                try:
                    turn.proxy_result.abandon_delivered("commit_after_unregister")
                except Exception:  # noqa: BLE001
                    self.stats["abandon_evidence_failures"] = (
                        self.stats.get("abandon_evidence_failures", 0) + 1
                    )
            return
        # COMMITTED：finalize（重复 finalize = 契约违规，poison 不静默吞）
        if turn.proxy_result is not None:
            try:
                turn.proxy_result.finalize_delivered(f"capture:{sid}:{turn.request_id}")
            except ValueError:
                self.poison.poison(sid, "duplicate_finalize_contract_violation")
                self.stats["duplicate_finalize_violations"] = (
                    self.stats.get("duplicate_finalize_violations", 0) + 1
                )
        self.stats["committed"] += 1


@aiohttp_web.middleware
async def rh2_no_404_middleware(request: "aiohttp_web.Request", handler):
    """adapter 永不返回 404（codex 轮次 8/9：CC 2.1.205 对流式创建阶段的 404
    会绕过 CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK 再发一次非流式请求，
    claude.ts:2607 分支不检查禁用变量）。

    未知路由/内部 404 一律转 503 + `x-should-retry: false`（实测该头对
    external build 的 5xx 生效、单请求收束）。这是 HTTP 面的兜底；主防线
    仍是 session poison + execution 主动终止。"""

    try:
        response = await handler(request)
    except aiohttp_web.HTTPNotFound:
        return aiohttp_web.json_response(
            {"error": {"type": "rh2_route_unavailable", "message": "not found is never exposed"}},
            status=503,
            headers={"x-should-retry": "false"},
        )
    if getattr(response, "status", None) == 404:
        return aiohttp_web.json_response(
            {"error": {"type": "rh2_route_unavailable", "message": "not found is never exposed"}},
            status=503,
            headers={"x-should-retry": "false"},
        )
    return response


def build_session_guard_middleware(registry: "CaptureRegistry"):
    """adapter 入口的会话能力预检（codex 轮次 13 P0-1 建议 3）：进入
    _run_turn 前验证 bearer（= 当前 SID）在 active registry 且未中毒——
    未知/已关闭/中毒会话在 HTTP 层就拒绝（403 + x-should-retry:false，
    绝不 404），根本不产生 SGLang 请求。/healthz 与 /v1/models 放行。"""

    @aiohttp_web.middleware
    async def session_guard(request: "aiohttp_web.Request", handler):
        if request.path in ("/healthz", "/v1/models"):
            return await handler(request)
        auth = request.headers.get("Authorization", "")
        token = auth.removeprefix("Bearer ").strip() if auth.startswith("Bearer ") else None
        # F2-2 复核 P0-3：capability token 只做认证。命中 token 映射 →
        # 解析出 internal sid 并**重写 Authorization**，下游（slime
        # _session_id/store/closed/turn-count/日志/X-SMG-Routing-Key/异常
        # 消息）只见非秘密 internal sid；token 不进入任何持久面。
        # 兼容路径：sid 直接注册（启动探针等非秘密 id）→ 原样放行。
        internal = registry.resolve_capability(token) if token else None
        effective = internal if internal is not None else token
        if effective:
            with registry._lock:
                known = effective in registry.hooks
                # internal sid 非秘密：token 绑定的会话不许拿 internal 直接进门
                if internal is None and effective in registry._capability_required:
                    known = False
                revoked = effective in registry._revoked
            poisoned = registry.poison.is_poisoned(effective)
        else:
            known, poisoned, revoked = False, False, False
        if effective is None or not known or poisoned or revoked:
            # F2-2 quiescence：revoked = 撤销后迟到请求（drain 窗口内 hook
            # 仍注册，但 HTTP 层已拒新——排在 unknown 之前判，审计可区分）
            if poisoned:
                reason = "session_poisoned"
            elif revoked:
                reason = "session_revoked"
                # F2-3 批 1：迟到请求计数（drain receipt 的撤销生效证据；
                # revoked=True 蕴含 effective 非空——None 分支恒 False）
                if effective:
                    registry.note_revoked_rejection(effective)
            else:
                reason = "unknown_or_closed_session"
            return aiohttp_web.json_response(
                {"error": {"type": f"rh2_{reason}", "message": "session not authorized"}},
                status=403,
                headers={"x-should-retry": "false"},
            )
        if internal is not None:
            request = request.clone(
                headers={**request.headers, "Authorization": f"Bearer {internal}"}
            )
        # F2-3 批 2a：授权判定与 inflight 计入之间**无 await**（同 loop
        # 原子）——drain owner 在本 loop 上 revoke 后读到的 inflight 必然
        # 包含所有已过闸请求，不存在"过了闸还没计入就被 drain 越过"的
        # 交错（批 1 复核 Falsifier 复现的窗口）。
        registry._inflight_enter(effective)
        try:
            return await handler(request)
        finally:
            registry._inflight_exit(effective)

    return session_guard


def ensure_no_404_middleware(app: "aiohttp_web.Application") -> bool:
    """给**已构造**的 adapter app 挂 404 守卫（幂等）。

    codex 轮次 10 P0-2：生产顺序是先 `AnthropicAdapter(...)` 再
    `install_capture_wire()`——构造器 monkeypatch 只影响之后创建的 adapter，
    对首个（唯一的）生产 adapter 无效。glue 必须对已存在的 app 直接 append，
    并在 run_app_in_thread 前断言在场。返回 True = 本次新挂上。"""

    if rh2_no_404_middleware in app.middlewares:
        return False
    app.middlewares.append(rh2_no_404_middleware)
    return True


def assert_no_404_guard_installed(app: "aiohttp_web.Application") -> None:
    if rh2_no_404_middleware not in app.middlewares:
        raise RuntimeError(
            "rh2_no_404_middleware 不在 adapter app 上——404 会绕过 CC 的 "
            "nonstreaming fallback 开关（轮次 10 P0-2），启动中止。"
        )


def install_capture_wire(registry: CaptureRegistry) -> None:
    """安装两处接线：模块级 call_sglang_generate 替换 + record_turn 包装。

    幂等：重复调用只装一次（Ray actor 进程内单例）。
    """

    from slime.agent.adapters import common as slime_common
    from slime.agent.trajectory import TrajectoryManager

    if getattr(slime_common, "_rh2_capture_wire_installed", False):
        bound = getattr(slime_common, "_rh2_capture_wire_registry", None)
        if bound is registry:
            return  # 同 registry 幂等
        if bound is None:
            # 终核条件项 3：flag 在而 ref 缺 = 旧版本 wire 的 monkeypatch
            # 闭包可能仍持旧 registry——改模块属性重绑不了闭包，"收养"是
            # 假迁移。A′ 不支持进程内旧版迁移，typed fatal。
            raise CaptureWireOwnershipError(
                "capture wire 已安装但无 registry 归属记录（旧版本 wire）——"
                "单代语义不支持进程内迁移，重启进程。"
            )
        # 勘误 4 ⑤：不同 registry 重绑 = 所有权错误，typed fatal 暴露
        # （不是帮系统带病续跑——单代语义下这不该发生）
        raise CaptureWireOwnershipError(
            "capture wire 已绑定另一 registry——进程级单代所有权被违反"
            "（第二代 BringupService/registry 不允许存在，勘误 4）。"
        )

    # 404 -> 503 middleware（codex 轮次 9 一般 1：helper 必须真接线）——
    # BaseAdapter.__init__ 构造 app 后追加；aiohttp 允许 runner 起动前 append
    original_adapter_init = slime_common.BaseAdapter.__init__

    def rh2_adapter_init(self, *args, **kwargs):
        original_adapter_init(self, *args, **kwargs)
        ensure_no_404_middleware(self.app)

    slime_common.BaseAdapter.__init__ = rh2_adapter_init

    async def rh2_call_sglang_generate(
        prompt_ids: list[int],
        session: Any,
        body: dict,
        *,
        adapter: Any,
        session_id: str | None = None,
    ):
        """stock 实现的镜像（clamp/路由头/abort 语义逐行对照）+ tape 注入 + 暂存。"""

        logger = adapter.logger
        sp = slime_common._sampling_params(
            session, body, max_token_keys=adapter.max_token_keys, stop_keys=adapter.stop_keys
        )
        # rh2 会话默认键 -> wire 形态翻译（见模块 docstring 第 2 条）
        want_top_p_tape = bool(sp.pop("return_top_p_token_ids", False))
        want_routing = bool(sp.pop("return_routed_experts", False))
        top_p = float(sp.get("top_p", 1.0))
        if want_top_p_tape and top_p < 1.0:
            custom = dict(sp.get("custom_params") or {})
            custom["return_top_p_token_ids"] = True
            sp["custom_params"] = custom

        if session.max_context_tokens > 0:
            remaining = session.max_context_tokens - len(prompt_ids)
            if remaining <= 0:
                logger.warning(
                    "[rh2-capture] sid=%s prompt exceeds max_context_tokens (%d >= %d)",
                    session_id,
                    len(prompt_ids),
                    session.max_context_tokens,
                )
                return slime_common.TurnRecord(
                    prompt_ids=list(prompt_ids), output_ids=[], finish_reason="length"
                )
            sp["max_new_tokens"] = min(int(sp.get("max_new_tokens", remaining)), remaining)

        base_payload: dict[str, Any] = {
            "input_ids": list(prompt_ids),
            "sampling_params": sp,
            "return_logprob": True,
        }
        if want_routing:
            base_payload["return_routed_experts"] = True
        headers = (
            {"X-SMG-Routing-Key": session_id} if session_id and session_id != "default" else None
        )
        timeout = aiohttp.ClientTimeout(total=None, sock_read=900)
        last_rid: dict[str, str] = {}

        async def _send_once(attempt_number: int) -> dict:
            # P0-4（codex 轮次 8）：**每个 attempt 独立 rid**——proxy 内部重生成
            # 的 attempt1/attempt2 不再共用同一 SGLang rid（否则 /abort_request
            # 无法精确指向被 abort 的那次）。
            rid = uuid.uuid4().hex
            last_rid["rid"] = rid
            payload = {"rid": rid, **base_payload}
            try:
                async with aiohttp.ClientSession(timeout=timeout) as sess, sess.post(
                    f"{adapter.sglang_url}/generate", json=payload, headers=headers
                ) as r:
                    if r.status >= 400:
                        text = await r.text()
                        raise RuntimeError(f"sglang upstream {r.status}: {text[:400]}")
                    return await r.json(content_type=None)
            except (asyncio.CancelledError, aiohttp.ClientError, asyncio.TimeoutError):
                try:  # stock 同款：eager abort **本 attempt 的 rid**，释放引擎槽位
                    async with aiohttp.ClientSession(
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as s2:
                        await s2.post(f"{adapter.sglang_url}/abort_request", json={"rid": rid})
                except Exception:
                    pass
                raise

        proxy = registry.model_call_proxy
        proxy_result = None
        with registry._lock:
            session_known = session_id is not None and session_id in registry.hooks
        if not session_known:
            # 轮次 13 P0-1：未知 SID **fail-closed**——旧行为是直连 SGLang
            #（未登记推理旁路：绕过 proxy/poison/版本/deadline/限额/capture）。
            # 启动探针的会话是显式 register 过的，不受影响。
            raise UnknownSessionError(session_id)
        if proxy is None:
            # 未装配 proxy（纯 S1 mock 链）：已注册会话按原直连路径
            data = await _send_once(1)
            request_id = last_rid.get("rid", uuid.uuid4().hex)
        else:
            # D-FA-3 生产接线（codex 轮次 7/8）：poison 快速拒绝 + deadline
            # 传播 + 发前 ACTIVE 等待 + 更新窗口 abort 内部重生成，全在 proxy 内
            assert session_id is not None  # session_known 已保证
            registry.poison.check(session_id)
            turn_seq = registry.next_turn_seq(session_id)
            # P0-2：execution_scope = paid（每次物理重放唯一）→ attempt id
            # `{paid}/t{n}_a{k}` 不再随 replay 的 turn 序号重置而碰撞；
            # session_id 仍传给 poison/认证（sid 只负责认证与路由）
            paid = registry.physical_attempt_id_for(session_id)
            proxy_result = await proxy.call(
                paid or session_id,
                f"t{turn_seq}",
                _send_once,
                session_id=session_id,
                poison_registry=registry.poison,
                physical_attempt_id=paid,
                deadline_monotonic=registry.session_deadline(session_id),
            )
            data = dict(proxy_result.response)
            request_id = last_rid.get("rid", f"t{turn_seq}")

        meta = data.get("meta_info") or {}
        pairs = meta.get("output_token_logprobs") or []
        output_ids = [x[1] for x in pairs]
        output_log_probs = [float(x[0]) for x in pairs]
        finish = (meta.get("finish_reason") or {}).get("type", "stop") or "stop"

        # 暂存捕获（record_turn 时提交）。capture 参数记录**生效值**：
        # temperature/top_p 若请求未带则为引擎默认 1.0（SGLang SamplingParams 默认）。
        # P0-1（codex 轮次 8）：proxy_result 挂进 PendingTurn，**finalize 移到
        # commit**——stage 只是本进程暂存，CC 的 SSE flush 发生在 slime
        # _respond()（本函数返回之后）。在 flush 前 finalize 会造成"delivered
        # 但 CC 没收到"的虚假交付；改到 record_turn/commit 成功（该轮确定进入
        # 轨迹树、CC 已收到）才 finalize，会话销毁时未 commit 的 draft 由
        # unregister abandon。
        registry.stage(
            session_id,
            PendingTurn(
                prompt_ids=list(prompt_ids),
                capture_params={
                    "temperature": float(sp.get("temperature", 1.0)),
                    "top_p": top_p,
                    "max_new_tokens": int(sp.get("max_new_tokens", 4096)),
                    "return_top_p_token_ids": want_top_p_tape,
                    "return_routed_experts": want_routing,
                },
                raw_response=data,
                weight_version=(
                    str(meta["weight_version"]) if meta.get("weight_version") is not None else None
                ),
                request_id=request_id,
                proxy_result=proxy_result,
            ),
        )
        return slime_common.TurnRecord(
            prompt_ids=list(prompt_ids),
            output_ids=output_ids,
            finish_reason=finish,
            output_log_probs=output_log_probs,
        )

    slime_common.call_sglang_generate = rh2_call_sglang_generate

    original_record_turn = TrajectoryManager.record_turn

    def rh2_record_turn(self, sid, *args, **kwargs):
        result = original_record_turn(self, sid, *args, **kwargs)
        registry.commit(sid)  # 该轮已确定进入轨迹树（flush 成功之后才会走到这）
        return result

    TrajectoryManager.record_turn = rh2_record_turn
    slime_common._rh2_capture_wire_installed = True
    slime_common._rh2_capture_wire_registry = registry
