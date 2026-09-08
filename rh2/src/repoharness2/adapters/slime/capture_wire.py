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
import contextvars
import dataclasses
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

# F2-3 批 2b：per-HTTP-request 捕获归属键（guard middleware 进入时铸造，
# stage/commit 在同一请求 task 内读取——并行 subagent 请求各持独立键）
_capture_request_key: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "rh2_capture_request_key", default=None
)

import aiohttp
from aiohttp import web as aiohttp_web

from repoharness2.adapters.slime.async_worker import (
    ModelCallProxy,
    SessionPoisonRegistry,
)
from repoharness2.adapters.slime.engine_router_client import AbortDeliveryUnprovenError
from repoharness2.adapters.slime.generate import (
    GenerationCaptureHook,
    parse_weight_version_spans,
)


@dataclasses.dataclass
class PendingTurn:
    prompt_ids: list[int]
    capture_params: dict[str, Any]
    raw_response: dict[str, Any]
    weight_version: str | None
    request_id: str  # SGLang rid（本轮请求身份，P0-6 去覆盖的键）
    proxy_result: Any = None  # ProxyCallResult：commit 成功才 finalize（P0-1）
    # B2（R6-ext）：本轮已解析校验的采样支持集（miles TurnSupport；
    # return_sampling_mask 会话才非 None）。此前 wire 解析出 _turn_support
    # 后即丢弃——mask 事实到不了 commit 之后的装配层。现在随暂存结构走到
    # commit，由 hook 落进 TurnTape.sampling_supports（叶链装配的事实源）。
    turn_support: Any = None
    # V2（vendor refresh 第二批）：本轮已解析校验的 per-token 权重版本区间
    # （generate.parse_weight_version_spans 产物，tuple[WeightVersionSpan,...]）。
    # None = 引擎未报 meta_info.weight_versions（旧引擎，回退单数
    # weight_version，provenance=single_version_only）；引擎报了但非法在
    # wire 解析处已抛（fail-closed，走 F5 统一 guard poison+abandon），
    # 不会以坏值到达这里。commit 时随 hook kwarg 落 TurnTape，且区间的
    # **全部**版本并入 registry.weight_versions[sid]（drain receipt /
    # handshake 的 weight_versions_seen 事实源）。
    weight_version_spans: Any = None


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
    registry: "CaptureRegistry",
    loop: "asyncio.AbstractEventLoop",
    *,
    timeout_seconds: float = 45.0,
):
    """把 registry.drain_session_plane 绑定到 **adapter event loop** 上执行
    （run_coroutine_threadsafe），返回 orchestrator loop 可 await 的 owner
    callable。bringup 用 app_handle.loop 构造。"""

    async def owner(sid: str) -> SessionPlaneDrainResult:
        # 窄 T0 共同必修 + 联合终核 P1-2：bridge 层有界 deadline，超时
        # **先落准入闩（expired）再尽力 cancel**——run_coroutine_threadsafe
        # 在 loop 恢复时先建 Task 后传播 cancel，裸 cancel 挡不住
        # drain_session_plane 开头的同步 revoke 迟到生效；闩在 owner loop
        # 上的任何状态变更之前检查，过期命令零副作用。上层转 Fatal →
        # WorkerHalted，绝不永久 in-flight 或伪装缺员。
        latch: dict = {}  # PENDING→ADMITTED|EXPIRED，registry._lock 保护

        async def _admitted():
            if not registry.try_admit_drain(sid, latch):
                raise RuntimeError("session_drain_command_expired")
            return await registry.drain_session_plane(sid)

        cfut = asyncio.run_coroutine_threadsafe(_admitted(), loop)
        try:
            return await asyncio.wait_for(
                asyncio.wrap_future(cfut), timeout=timeout_seconds
            )
        except (TimeoutError, asyncio.TimeoutError) as exc:
            verdict = registry.expire_drain(latch)  # 与准入同锁排他定局
            cfut.cancel()
            raise RuntimeError(
                f"session_drain_owner_bridge_timeout:{verdict}: adapter loop "
                f"未在 {timeout_seconds}s 内完成 drain——"
                + ("命令已过期，零副作用。" if verdict == "expired"
                   else "owner 已抢先准入（revoke 已生效），如实上报。")
            ) from exc

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
    比丢数据更危险，codex 探针确定性复现）。**F2-3 批 2b 已落地 request 级
    归属**（ContextVar 请求键）：不同请求键并行暂存合法共存；本异常现在
    只在两种真异常时抛——同键二次 stage、多条在场且无请求键的歧义
    commit（都 fail-closed：poison + abandon，绝不猜测归属）。"""

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

        # 所有权模型定案（2026-08-24 窄 T0 方案 A，混合模型）：
        # **owner 独占域** = revoke/inflight/drain 生命周期临界段（批 2a，
        # 必须在 adapter loop 上执行）+ request 级归属键（批 2b）；
        # **锁域** = 其余短态 map（hooks/pending/versions/stats 等），由
        # 本显式锁保护（5000 轮竞态压测实证）。批 2c 命令桥已撤回。
        # 纪律：新增状态必须声明所属域，禁跨域混用；poison 为独立线程
        # 安全对象。全量单 owner 若未来需要须带证据重新提案（T0）。
        self._lock = threading.Lock()
        self.hooks: dict[str, GenerationCaptureHook] = {}
        # F2-3 批 2b：request 级归属——sid → {request_key → PendingTurn}。
        # 并行不同请求各占独立键（overlap 误杀解除）；同键二次 stage 或
        # 无键歧义 commit 仍 fail-closed（CapturePendingOverlapError）。
        self.pending: dict[str, dict[str, PendingTurn]] = {}
        self.weight_versions: dict[str, list[str]] = {}
        self.stats = {
            "staged": 0,
            "committed": 0,
            "dropped_uncommitted": 0,
            "concurrent_overlap_seen": 0,
        }
        # FA-1 follow-up（codex 轮次 7/8）：proxy 接入真实 HTTP 链的挂点。
        self.model_call_proxy: ModelCallProxy | None = None
        # W10（决策包 B-5b）：rid 级 abort 的投递函数。bringup 接线 =
        # `MilesRouterWorkerClient.broadcast_abort`（router `/list_workers` 实时列表 ∪ 启动核对
        # 集合，绕过 router 逐 worker 直发同一 rid：持有者终止、其余忽略）。返回
        # `AbortBroadcastResult`，outcome ∈ delivered / partial / undeliverable；**只有 delivered
        # 算到达**，其余两种由 wire 经 `bringup.notify_run_fatal` 升级为 typed run-fatal
        # （codex Wave3 F3 P1：不得把部分投递当成功、不得静默吞掉未投递事实）。
        # None = 未接线（S1 mock 链 / 无 bringup 的测试面）：wire 退回 stock 形状经 router 单发
        # ——MilesRouter 逐请求最小负载选 worker，单发只在**单 worker 池**下语义正确；该退化
        # 只可能出现在没有 bringup 的测试面，正式 profile 由 `abort_router_single_send == 0` 判据钉死。
        self.engine_abort: Callable[[str], Awaitable[Any]] | None = None
        # 最近的 abort 投递事实（有界环，锁域；bringup 关停/审计可读）
        self.abort_results: list[dict[str, Any]] = []
        self.stats.update(
            {
                "abort_requested": 0,  # wire 走到 abort 分支的次数（cancel/超时/连接错误）
                "abort_broadcast": 0,  # 经 engine_abort 广播的次数（含 partial/undeliverable）
                "abort_router_single_send": 0,  # 未接线 → 经 router 单发（正式 profile 必须为 0）
                "abort_delivery_failed": 0,  # outcome ≠ delivered 的次数（正式 profile 必须为 0）
                "abort_unproven_fatal": 0,  # 升级为 run-fatal 的次数（notify_run_fatal 已调用）
                # 升级时通知**没送到** owner loop：本进程无 BringupService，或 owner loop
                # 已关闭/不再接受回调（codex Wave3 §9.4）。只留账 + 打印，不当成已通知。
                "abort_unproven_unnotified": 0,
            }
        )
        self.poison = SessionPoisonRegistry()
        self.session_deadlines: dict[str, float] = {}
        self.default_session_budget_seconds: float | None = None
        self._turn_seq: dict[str, int] = {}
        # F2-1a：sid → physical_attempt_id 映射（orchestrator 经注入点登记；
        # wire 读出后随每条 ModelCallAttempt 落账；unregister 清理）
        self._physical_attempt_ids: dict[str, str] = {}
        # F1 身份制（finding §3）：sid → {树 turn_index → capture record_id}。
        # rh2_record_turn 包装在 commit 成功且树确实新增 turn 时写入——
        # capture 身份从此正向流动到树侧（vendor 树只读，绑定账存这里）；
        # 叶侧 span 导出（bringup finish_session 树走查）按 turn_index 解析
        # 回 capture_record_id。unregister 一并清理。
        self._turn_bindings: dict[str, dict[int, str]] = {}
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
        # 批 C（I02）：turn 预算事实（vendored _check_turn_cap 的包装写入；guard 读"已达 N"；
        # 编排订阅命中事件）。锁域；unregister 一并清理。
        self._turn_budget: dict[str, dict[str, Any]] = {}
        self._turn_budget_subscribers: dict[str, Callable[[str], None]] = {}
        # F2-2 复核 P0-3：capability token 只做**认证**——guard 验证后把
        # Authorization 重写为非秘密 internal sid，slime 的 store/closed/
        # turn-count/日志/routing key/异常消息全部只见 internal sid。
        # token→internal 映射与 hook 同事务绑定/清理。
        self._capability_tokens: dict[str, str] = {}
        # 绑定了 token 的 internal sid 集合：这些会话**只能**经 token 认证
        # 进入——internal sid 非秘密（进日志/审计），直接当 bearer 必须拒
        self._capability_required: set[str] = set()
        # W5a 关停：整表关闭标志。close() 后 register 抛 typed ServiceClosedError，
        # guard 对任何请求 403（rh2_service_closed）——"关闭后禁 submit"的 HTTP 面。
        self.closed = False

    def close(self) -> int:
        """关停链调用：置 closed（幂等）。返回此刻仍注册的 hook 数（应为 0；非 0 = 残留）。"""

        with self._lock:
            self.closed = True
            return len(self.hooks)

    def register(
        self,
        sid: str,
        hook: GenerationCaptureHook,
        physical_attempt_id: str | None = None,
        capability_token: str | None = None,
        deadline_monotonic: float | None = None,
    ) -> None:
        """会话注册（F2-1a 熔断后所有权收敛版）：hook 与 paid **单锁原子
        绑定**，同生命周期——重复 SID 在任何状态修改前拒绝；绑定发生在
        open_session 事务内（materialize 之后），underlying open 失败走
        既有 rollback unregister 连带清 paid。**不存在预登记**，所以
        materialize 失败不可能残留映射（codex F2-1a 二审 P0 的根因修）。"""

        # 轮次 11 身份兜底：中毒 SID（含归档）不得复用注册
        self.poison.check(sid)
        with self._lock:
            if self.closed:
                from repoharness2.shutdown.chain import ServiceClosedError

                raise ServiceClosedError("capture_register", f"registry 已关闭，拒绝注册 session {sid}")
            if sid in self.hooks:
                raise DuplicateActiveSessionError(sid)  # 任何状态修改前拒绝
            self.hooks[sid] = hook
            self.weight_versions[sid] = []
            self.pending.setdefault(sid, {})
            if physical_attempt_id is not None:
                self._physical_attempt_ids[sid] = physical_attempt_id
            if capability_token is not None:
                self._capability_tokens[capability_token] = sid
                self._capability_required.add(sid)
            if deadline_monotonic is not None:
                # 批 B（I03）：episode 期限由编排在资源占用时刻算好、随注册显式下传——proxy 的
                # deadline_monotonic 从此读它，不再在首次模型调用时才懒起表。
                self.session_deadlines[sid] = float(deadline_monotonic)

    def assert_session_clean(self, sid: str) -> None:
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
            queue = list((self.pending.get(sid) or {}).values())
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
        """会话 deadline（episode 预算传播）。批 B（I03）起正式链由 register(deadline_monotonic=…)
        显式设定（编排在资源占用时刻算好的绝对期限）；未显式设定且配置了
        default_session_budget_seconds 时保留旧的首调懒起表（兼容 / 探针），两者都没有 → None。"""

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

    def bind_turn_identity(
        self, sid: str, turn_index: int, capture_record_id: str
    ) -> None:
        """F1 身份制：commit 时刻登记 capture_id↔树 turn 绑定。

        同 (sid, turn_index) 重复绑定 = 身份账损坏（turn_index 由
        TrajectoryManager._turn_count 单调派发，正常不可能重复）——
        poison + 抛错 fail-closed，绝不静默覆盖。"""

        with self._lock:
            slot = self._turn_bindings.setdefault(sid, {})
            existing = slot.get(turn_index)
            if existing is None:
                slot[turn_index] = capture_record_id
                return
        self.poison.poison(sid, "turn_identity_binding_conflict")
        raise RuntimeError(
            f"turn_identity_binding_conflict: session {sid} turn {turn_index} 已绑定 "
            f"{existing!r}，拒绝改绑 {capture_record_id!r}——身份账不可变。"
        )

    def turn_capture_binding(self, sid: str, turn_index: int) -> str | None:
        """按树 turn_index 解析 capture record_id（无绑定返回 None）。"""

        with self._lock:
            return (self._turn_bindings.get(sid) or {}).get(turn_index)

    def turn_identity_bindings(self, sid: str) -> dict[int, str]:
        """锁内复制该会话全部 turn 身份绑定（测试/审计用）。"""

        with self._lock:
            return dict(self._turn_bindings.get(sid) or {})

    def resolve_capability(self, token: str | None) -> str | None:
        """认证：token → internal sid（未知 token → None，guard 拒绝）。"""

        if token is None:
            return None
        with self._lock:
            return self._capability_tokens.get(token)

    def try_admit_drain(self, sid: str, latch: dict) -> bool:
        """联合终核二轮 P1-1：drain 命令准入——PENDING→ADMITTED 与**首次
        revoke 在同一 _lock 临界区**完成（真线性化：超时方与准入方在同一
        锁上排他，谁先拿到锁谁定局）。已过期返回 False（命令零副作用）。"""

        with self._lock:
            if latch.get("expired"):
                return False
            latch["admitted"] = True
            self._revoked.add(sid)  # 准入即撤销（同临界区，不可再迟到）
            return True

    def expire_drain(self, latch: dict) -> str:
        """超时方转移：PENDING→EXPIRED（同一锁）。若 owner 已抢先准入，
        如实返回 admitted_but_timed_out——不再声称"过期且零副作用"。"""

        with self._lock:
            if latch.get("admitted"):
                return "admitted_but_timed_out"
            latch["expired"] = True
            return "expired"

    def revoke(self, sid: str) -> None:
        with self._lock:
            self._revoked.add(sid)

    def is_revoked(self, sid: str) -> bool:
        with self._lock:
            return sid in self._revoked

    def note_abort_result(self, result: Any) -> None:
        """W10：记一次 rid abort 的投递事实（锁域）。``result`` 为
        `AbortBroadcastResult`（有 to_dict）或 dict（legacy 单发路径）；环上限 256 条。"""

        record = result.to_dict() if hasattr(result, "to_dict") else dict(result)
        with self._lock:
            if record.get("outcome") == "router_single_send":
                self.stats["abort_router_single_send"] += 1
            else:
                self.stats["abort_broadcast"] += 1
            if record.get("outcome") != "delivered" or record.get("failed"):
                self.stats["abort_delivery_failed"] += 1
            self.abort_results.append(record)
            if len(self.abort_results) > 256:
                del self.abort_results[: len(self.abort_results) - 256]

    def note_abort_unproven(self, exc: AbortDeliveryUnprovenError, *, notified: bool) -> None:
        """W10（F3 P1）：一次"不能证明 abort 到达"的升级事实（锁域）。"""

        with self._lock:
            self.stats["abort_unproven_fatal"] += 1
            if not notified:
                self.stats["abort_unproven_unnotified"] += 1
            self.abort_results.append(
                {
                    "rid": exc.result.rid,
                    "outcome": "run_fatal",
                    "reason_code": exc.reason_code,
                    "notified": notified,
                    "detail": str(exc)[:400],
                }
            )
            if len(self.abort_results) > 256:
                del self.abort_results[: len(self.abort_results) - 256]

    def note_revoked_rejection(self, sid: str) -> None:
        """guard 在 revoked 分支计一笔迟到请求（F2-3 drain receipt 证据）。"""

        with self._lock:
            self.revoked_rejections[sid] = self.revoked_rejections.get(sid, 0) + 1

    # ---- F2-3 批 2a：adapter event-loop 单 owner drain -------------------
    # inflight 追踪在 guard middleware（授权通过与计入之间无 await——同
    # loop 原子），drain owner 在 adapter loop 上执行 revoke→等 inflight
    # 归零→账目读取，返回 typed 结果。消灭"多锁快照看不到真实 HTTP
    # inflight"的假阳性窗口（批 1 复核 P1-1 根修）。

    # ---- 批 C（I02）：turn 预算事实 -------------------------------------------------

    def _turn_budget_state(self, sid: str) -> dict[str, Any]:
        return self._turn_budget.setdefault(
            sid,
            {"cap": None, "accepted": 0, "exhausted": False, "refused_count": 0, "refused_at_monotonic": None},
        )

    def note_turn_admitted(self, sid: str, *, accepted: int, cap: int | None) -> None:
        """vendored _check_turn_cap 放行一次请求（accepted = 放行后的累计接纳数）。"""

        with self._lock:
            state = self._turn_budget_state(sid)
            state["cap"] = cap
            state["accepted"] = int(accepted)

    def note_turn_budget_refused(self, sid: str, *, cap: int | None, accepted: int) -> None:
        """vendored _check_turn_cap 拒绝了第 N+1 次请求：记预算事实并通知订阅者（锁外回调，
        回调须线程安全——编排用 call_soon_threadsafe）。"""

        with self._lock:
            state = self._turn_budget_state(sid)
            state["cap"] = cap
            state["accepted"] = int(accepted)
            state["exhausted"] = True
            state["refused_count"] += 1
            if state["refused_at_monotonic"] is None:
                state["refused_at_monotonic"] = time.monotonic()
            callback = self._turn_budget_subscribers.get(sid)
        if callback is not None:
            try:
                callback(sid)
            except Exception:  # noqa: BLE001 —— 通知失败只计数，不影响拒绝响应
                with self._lock:
                    self.stats["turn_budget_notify_failures"] = (
                        self.stats.get("turn_budget_notify_failures", 0) + 1
                    )

    def turn_budget_snapshot(self, sid: str) -> dict[str, Any] | None:
        with self._lock:
            state = self._turn_budget.get(sid)
            return dict(state) if state is not None else None

    def turn_budget_reached(self, sid: str) -> bool:
        """计数已达 N（下一次 /v1/messages 会被拒）——guard 据此先等在飞请求归零。"""

        with self._lock:
            state = self._turn_budget.get(sid)
            return bool(state and state["cap"] is not None and state["accepted"] >= state["cap"])

    def subscribe_turn_budget(self, sid: str, callback: Callable[[str], None]) -> None:
        with self._lock:
            self._turn_budget_subscribers[sid] = callback
            already = bool(self._turn_budget.get(sid, {}).get("exhausted"))
        if already:
            callback(sid)  # 订阅前已命中：立即回调（与 poison.subscribe 同一竞态收口）

    def unsubscribe_turn_budget(self, sid: str) -> None:
        with self._lock:
            self._turn_budget_subscribers.pop(sid, None)

    async def wait_inflight_zero(self, sid: str, *, timeout: float, poll: float = 0.02) -> bool:
        """等该 sid 的 guard 级在飞计数归零（有界轮询；须在 adapter loop 上调用）。"""

        import asyncio as _asyncio

        deadline = time.monotonic() + max(timeout, 0.0)
        while True:
            with self._lock:
                n = self._inflight.get(sid, 0)
            if n <= 0:
                return True
            if time.monotonic() >= deadline:
                return False
            await _asyncio.sleep(poll)

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
            leftover_locked = list((self.pending.pop(sid, None) or {}).values())
            self.session_deadlines.pop(sid, None)
            self._turn_seq.pop(sid, None)
            self.weight_versions.pop(sid, None)
            self._physical_attempt_ids.pop(sid, None)
            self._turn_bindings.pop(sid, None)
            self._turn_budget.pop(sid, None)
            self._turn_budget_subscribers.pop(sid, None)
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

    def stage(self, sid: str | None, turn: PendingTurn) -> bool:
        """暂存一条捕获轮。返回值 = 所有权接管事实（F5 guard 的判据）：

        - True：registry 已接管 turn（含其 proxy_result draft 的生命周期——
          此后 commit finalize / unregister abandon 二选一，调用方不得再碰）；
        - False：**未**接管（sid None 的非 rh2 会话，或 stage 时会话已被并发
          unregister 摘除）——draft 生命周期仍归调用方，泄漏责任在调用方兜底；
        - 抛 CapturePendingOverlapError：同请求键二次 stage，poison + 双方
          draft 都已在本方法内 abandon（调用方**不得**再 abandon，见 F5 guard
          的幂等豁免）。"""

        if sid is None:
            return False  # 非 rh2 会话不捕获（未知 SID 的拒绝在 wire 入口，轮次 13 P0-1）
        key = _capture_request_key.get() or turn.request_id
        stale = None
        with self._lock:
            if sid not in self.hooks:
                return False
            slot = self.pending.setdefault(sid, {})
            if key in slot:
                # 同一请求键二次 stage = 真异常（非并行误杀），fail-closed
                stale = slot.pop(key)
                self.stats["concurrent_overlap_seen"] += 1
                self.stats["dropped_uncommitted"] += 1
            else:
                slot[key] = turn
                self.stats["staged"] += 1
        if stale is None:
            return True
        self.poison.poison(sid, "capture_pending_overlap")
        for t in (stale, turn):
            if t.proxy_result is not None:
                try:
                    t.proxy_result.abandon_delivered("capture_pending_overlap")
                except ValueError:
                    pass  # 已定案（幂等）
        raise CapturePendingOverlapError(sid)

    def commit(self, sid: str) -> str | None:
        """PENDING -> COMMITTING -> COMMITTED/ABANDONED（轮次 13 P0-3 事务化）。

        锁内只摘取所有权；hook（capture store/tape 构造）在锁外执行——
        中点异常不再留永久悬挂 draft（turn 持有 proxy_result，事务化
        abandon 先关账再传播）；hook 后复检会话仍在（unregister 竞态时
        弃置本轮，不给已销毁会话追加版本——KeyError 竞态的根修）。

        返回值（F1 身份制）：commit 成功产出的 capture record_id；未发生
        commit（无 hook/无暂存/no-stage/unregister 竞态弃置）返回 None——
        rh2_record_turn 包装据此建立 capture_id↔turn 绑定。"""

        key = _capture_request_key.get()
        ambiguous = False
        with self._lock:
            hook = self.hooks.get(sid)
            slot = self.pending.get(sid)
            if hook is None:
                return None
            if key is not None:
                if slot and key in slot:
                    turn = slot.pop(key)  # COMMITTING：按请求键精确取own（批 2b）
                else:
                    # 批 2b 收口 P0：本请求从未 stage（如 max-context 短路
                    # 轮直接 record_turn）——**绝不触碰其他请求的暂存**。
                    # 旧写法落进 len==1 分支会把别人的轮偷走并 finalize
                    #（静默串账）。落账后返回。
                    # slot 为空或键未命中都计（收口二轮非阻塞项：空 slot
                    # 的 no-stage commit 此前漏计，只影响遥测）
                    self.stats["commit_without_stage"] = (
                        self.stats.get("commit_without_stage", 0) + 1
                    )
                    return None
            elif not slot:
                return None
            elif len(slot) == 1:
                turn = slot.pop(next(iter(slot)))  # 无键上下文且无歧义（探针直调）
            else:
                ambiguous = True
                turn = None
        if ambiguous:
            # 多条在场且无请求键 = 归属不可判——猜测会串账，fail-closed
            self.poison.poison(sid, "capture_pending_overlap")
            raise CapturePendingOverlapError(sid)
        assert turn is not None
        capture_ref = None
        try:
            # B2（R6-ext）：wire 已解析校验的逐轮支持集随 commit 交给 hook
            # （TurnTape.sampling_supports）。仅在场时传 kwarg——探针/回归里
            # 的最小 hook 替身没有该参数，非 mask 会话不动既有签名调用形状。
            # V2：weight_version_spans 同一模式（仅在场才传；未报 spans 的
            # 旧引擎轮不动调用形状，hook 直调路径自行解析同一函数）。
            extra: dict[str, Any] = {}
            if turn.turn_support is not None:
                extra["turn_support"] = turn.turn_support
            if turn.weight_version_spans is not None:
                extra["weight_version_spans"] = turn.weight_version_spans
            record = hook.on_generate_response(
                prompt_token_ids=turn.prompt_ids,
                sampling_params=turn.capture_params,
                response=turn.raw_response,
                **extra,
            )
            # 收口二轮 P1：capture provenance 不许 fail-open——record_id
            # 缺失/为空与 hook 抛异常同罪（poison + abandon + 抛错，绝不
            # 用合成引用 finalize 出不可解析的 delivered attempt）。
            capture_ref = getattr(record, "record_id", None)
            if not capture_ref:
                raise RuntimeError(
                    f"capture_hook_returned_no_record_id: {type(record).__name__}"
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
            if still_registered:
                # V2：spans 在场时把区间的**全部**版本依序并入（一轮可跨多次
                # 权重更新；spans[-1].version == 单数 weight_version 已在解析
                # 时校验，序列尾部仍是 finalize 时刻值——weight_versions_seen
                # 的 FA-0 权威序列语义）。未报 spans 保持旧口径 append 单数。
                if turn.weight_version_spans:
                    self.weight_versions[sid].extend(
                        span.version for span in turn.weight_version_spans
                    )
                elif turn.weight_version is not None:
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
            return None
        # COMMITTED：finalize（重复 finalize = 契约违规，poison 不静默吞）
        if turn.proxy_result is not None:
            # 批 2b 收口 P1：finalize 引用 = hook 返回的**真实**
            # GenerationCaptureRecord.record_id（cap_{traj}_t{n}），上方
            # 已强制非空——无 fallback（合成引用是 provenance 旁路）。
            try:
                turn.proxy_result.finalize_delivered(capture_ref)
            except ValueError:
                self.poison.poison(sid, "duplicate_finalize_contract_violation")
                self.stats["duplicate_finalize_violations"] = (
                    self.stats.get("duplicate_finalize_violations", 0) + 1
                )
        self.stats["committed"] += 1
        return capture_ref


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
        if registry.closed:
            # W5a：关停链已把 registry 关闭——任何模型调用都拒绝（不分已知/未知
            # 会话），且明确告诉 CC 不要重试。
            return aiohttp_web.json_response(
                {"error": {"type": "rh2_service_closed", "message": "service is shutting down"}},
                status=403,
                headers={"x-should-retry": "false"},
            )
        auth = request.headers.get("Authorization", "")
        token = auth.removeprefix("Bearer ").strip() if auth.startswith("Bearer ") else None
        # F2-2 复核 P0-3：capability token 只做认证。命中 token 映射 →
        # 解析出 internal sid 并**重写 Authorization**，下游（slime
        # _session_id/store/closed/turn-count/日志/X-SMG-Routing-Key/异常
        # 消息）只见非秘密 internal sid；token 不进入任何持久面。
        # 兼容路径：sid 直接注册（启动探针等非秘密 id）→ 原样放行。
        internal = registry.resolve_capability(token) if token else None
        effective = internal if internal is not None else token
        if effective and request.path == "/v1/messages" and registry.turn_budget_reached(effective):
            # 批 C（I02；Codex 计划审查 R3 的并发接缝）：计数已达 N 时，第 N+1 次不抢在第 N 次交付
            # 之前被拒——先等该 sid 的在飞请求归零（受 session 期限约束），再进入下方授权判定与
            # _run_turn（那里 vendored _check_turn_cap 的包装会拒绝并记录预算事实）。否则 CC 收到
            # 拒绝立刻退出，会把在飞的第 N 轮断连成 client_cancelled poison。授权判定与 inflight
            # 计入之间仍无 await（在下方）。
            deadline = registry.session_deadline(effective)
            budget = 30.0 if deadline is None else max(0.0, deadline - time.monotonic())
            await registry.wait_inflight_zero(effective, timeout=min(budget, 600.0))
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
        token = _capture_request_key.set(uuid.uuid4().hex)  # 批 2b：请求归属键
        try:
            return await handler(request)
        finally:
            _capture_request_key.reset(token)
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


def escalate_abort_unproven(registry: CaptureRegistry, exc: AbortDeliveryUnprovenError) -> bool:
    """W10（codex Wave3 F3 P1）：把"不能证明 abort 到达持有者"升级为进程级 run-fatal。

    通道 = `bringup.notify_run_fatal`（与 `adapters/miles/group_admission.py` 的 GroupAdmissionFatal
    同一入口：未在关停 → 调度关停链，首因 = exc；关停进行中 → 吸收进报告；已定稿 → 只留 fatal_seen）。

    本函数几乎总是跑在 **adapter 的 aiohttp 线程/loop** 上（HTTP handler → `_send_once` → abort），
    而 BringupService 属于 miles 共享后台 loop；`notify_run_fatal` 负责把记账与关停调度整体派回
    owner loop（codex Wave3 §9.4）。它返回 False 的三种情形——本进程没有 BringupService、
    owner loop 已关闭、派回失败——都**不算通知成功**：记 `abort_unproven_unnotified` + 打印，
    事实无论如何都进 `registry.abort_results`。bringup 在模块级 import 本模块，所以这里延迟 import。
    永不抛（升级路径自身出错也只能留账，不能反过来吞掉调用方正在传播的原异常）。
    """

    notified = False
    try:
        from repoharness2.adapters.slime import bringup as bringup_mod

        notified = bool(bringup_mod.notify_run_fatal(exc))
    except Exception as notify_exc:  # noqa: BLE001
        print(f"[rh2-capture] abort run-fatal 通知失败（{type(notify_exc).__name__}: {notify_exc}）：{exc}")
    registry.note_abort_unproven(exc, notified=notified)
    if not notified:
        print(
            "[rh2-capture] abort 不能证明到达，且 run-fatal 未通知到 owner loop"
            f"（无 BringupService / owner loop 已关闭 / 派回失败），只留账：{exc}"
        )
    return notified


def install_turn_budget_wire(registry: CaptureRegistry) -> None:
    """批 C（I02）：包装 vendored `BaseAdapter._check_turn_cap`。

    计数与前置条件（读 body、预处理、closed 检查之后才计；`count_tokens` 不经 _run_turn 不计）
    **仍由 vendored 完成**，`MAX_TURNS_PER_SID` 经 vendored 构造参数传入（唯一来源不变；不复制第三份
    解析）。包装只做两件事：把每次接纳 / 拒绝写进 registry（预算事实，编排据此产出真实
    `max_turns_exhausted`，不伪造 end_turn），并把拒绝响应从 429（Anthropic SDK 视为可重试）换成
    403 + `x-should-retry: false`（与守卫拒绝同形状）。真实 CC 二进制对该响应怎样退出由 B 的真实
    探针确认，编排不依赖它——宽限后强制停止。幂等、单 registry 归属（与 capture wire 同纪律）。
    """

    from slime.agent.adapters import common as slime_common

    bound = getattr(slime_common, "_rh2_turn_budget_wire_registry", None)
    if bound is registry:
        return
    if bound is not None:
        raise CaptureWireOwnershipError(
            "turn budget wire 已绑定另一 registry——进程级单代所有权被违反。"
        )
    original_check = slime_common.BaseAdapter._check_turn_cap

    def rh2_check_turn_cap(self, sid):
        cap = self.max_turns_per_sid
        refused = original_check(self, sid)  # vendored 计数 + 前置条件不变
        accepted = int(self._sid_turn_count.get(sid, 0))
        if refused is None:
            if cap is not None:
                registry.note_turn_admitted(sid, accepted=accepted, cap=cap)
            return None
        registry.note_turn_budget_refused(sid, cap=cap, accepted=accepted)
        return aiohttp_web.json_response(
            {
                "error": {
                    "type": "rh2_turn_budget_exhausted",
                    "message": (
                        f"turn budget ({cap} accepted model requests) exhausted for this session; "
                        "the run is being stopped"
                    ),
                }
            },
            status=403,
            headers={"x-should-retry": "false"},
        )

    slime_common.BaseAdapter._check_turn_cap = rh2_check_turn_cap
    slime_common._rh2_turn_budget_wire_registry = registry


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
    install_turn_budget_wire(registry)  # 批 C（I02）：turn 预算事实 + 不可重试的拒绝形状

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

        # C1′-b（miles 迁移）：sampling-support mask 捕获。会话默认键
        # `return_sampling_mask` 翻译成**请求体顶层旗标**（sglang-miles 约定，
        # 对照 miles/rollout/sglang_rollout.py:181-189 的 payload 注入）。
        # 与上面 custom_params 里的 `return_top_p_token_ids` 是**双约定并存期**：
        # vendor slime patch 引擎只认 custom_params 键、对顶层旗标无感；
        # sglang-miles 只认顶层旗标、custom_params 约定对它无效。用哪个由
        # 编排层按目标引擎在会话默认键里二选一，本函数不猜引擎型号。
        want_sampling_mask = bool(sp.pop("return_sampling_mask", False))
        if want_sampling_mask:
            # 前置校验 fail-closed（对照上游 should_return_sampling_mask：
            # top_k 有限、温度与会话配置一致、penalties/logit_bias 拒绝——
            # 不可忠实 replay 的请求不发出去）。lazy import：
            # repoharness2.adapters.miles 包 __init__ 依赖 miles checkout，
            # 现有 321 测试面（无 miles 环境）不得因 import 本文件被迫加载。
            from repoharness2.adapters.miles.sampling_mask_assembly import (
                validate_sampling_mask_request,
            )

            defaults = session.sampling_defaults or {}
            configured_top_k = defaults.get("top_k")
            validate_sampling_mask_request(
                sp,
                expected_temperature=float(defaults.get("temperature", 1.0)),
                # 上游 request_top_k <= configured_top_k 的会话侧等价物：请求
                # body 不得静默放大会话配置的支持集硬上界（未配置则不设上界,
                # T0-A 兼容）
                configured_top_k=(int(configured_top_k) if configured_top_k is not None else None),
            )

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
        if want_sampling_mask:
            # C1′-b：顶层旗标（sglang-miles wire 形态，见上方双约定注释）
            base_payload["return_sampling_mask"] = True
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
                # stock 同款：eager abort **本 attempt 的 rid**，释放引擎槽位。
                # W10（B-5b）：投递方式改为 registry.engine_abort（bringup 接线的 rid 级广播：
                # router `/list_workers` 全部 worker 各发一次同一 rid，持有者终止、其余忽略）；
                # 未接线时退回 stock 形状经 router 单发（只在单 worker 池下语义正确）。
                # 投递失败只记账不上抛（与 stock 一致：abort 是尽力释放，不改变本次失败的归因）。
                with registry._lock:
                    registry.stats["abort_requested"] += 1
                try:
                    await _abort_rid(rid)
                except Exception as abort_exc:  # noqa: BLE001 —— abort 机制自身异常 = 同样不能证明到达
                    # codex Wave3 F3 P1：不再静默吞掉。按 undeliverable 走同一 run-fatal 通道；
                    # 本 attempt 的失败归因仍是下面 raise 出去的原异常（cancel/连接错误/超时）。
                    escalate_abort_unproven(registry, AbortDeliveryUnprovenError.from_exception(rid, abort_exc))
                raise

        async def _abort_rid(rid: str) -> None:
            abort_fn = registry.engine_abort
            if abort_fn is not None:
                result = await abort_fn(rid)
                registry.note_abort_result(result)
                if not getattr(result, "proven", False):
                    # partial / undeliverable：router 不告诉我们谁持有 rid，SGLang 的 200 也不区分
                    # 持有/忽略——只要有一个目标没收到，就不能证明持有者收到；被放弃的生成可能
                    # 继续占 engine 槽位。升级为 typed run-fatal（与 group filter fatal 同一通道），
                    # 不 raise：本 attempt 的失败归因不变。
                    escalate_abort_unproven(registry, AbortDeliveryUnprovenError(result))
                return
            # 未接线（S1 mock 链 / 无 bringup 的测试面）：stock 形状经 router 单发。
            # 只在单 worker 池下语义正确；如实记账为 router_single_send，正式 profile 判据 == 0。
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as s2:
                async with s2.post(f"{adapter.sglang_url}/abort_request", json={"rid": rid}) as r:
                    registry.note_abort_result(
                        {
                            "rid": rid,
                            "outcome": "router_single_send",
                            "targets_source": "router",
                            "targets": [adapter.sglang_url],
                            "delivered": [adapter.sglang_url] if r.status < 400 else [],
                            "failed": ({} if r.status < 400 else {adapter.sglang_url: f"HTTP {r.status}"}),
                            "list_error": "engine_abort_not_wired",
                            "proven": None,
                        }
                    )

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

        # F5 统一 ownership guard：proxy.call 成功返回的瞬间，delivered draft
        # 已挂在 proxy._pending_drafts；直到 registry.stage **真正接管**之前，
        # draft 生命周期归本函数。此区间内任何解析异常（含 mask 解析失败）或
        # 并发 unregister（stage 返回 False）都必须 poison + abandon，否则
        # draft 永远留在 unfinalized_deliveries（drain 永不干净、生命周期账
        # 无终态——finding §7）。stage 接管成功（True）或 overlap 路径（stage
        # 内部已 poison + abandon 双方 draft）后不得 double-abandon。
        staged = False
        try:
            meta = data.get("meta_info") or {}
            pairs = meta.get("output_token_logprobs") or []
            output_ids = [x[1] for x in pairs]
            output_log_probs = [float(x[0]) for x in pairs]
            finish = (meta.get("finish_reason") or {}).get("type", "stop") or "stop"

            # V2：per-token 权重版本区间（sglang-miles meta_info.weight_versions，
            # 键名/形态/边界合同以 sglang 4e230c3d weight_versions.py 为准）。
            # **引擎报了就必须合法**：解析失败在这里抛 SlimeBindingError →
            # 下方 F5 统一 guard poison + abandon（fail-closed，绝不把坏
            # spans 静默降级成单数记账）。未报（None）= 旧引擎回退单数，
            # provenance 由 TurnTape.weight_version_provenance 显式记
            # single_version_only。
            weight_version_spans = parse_weight_version_spans(
                meta, generated=len(output_ids)
            )

            turn_support = None
            if want_sampling_mask:
                # C1′-b 响应侧：解析并校验 output_token_sampling_mask/_logprobs
                # （逐 token sampled∈support、长度对齐；abort 且零输出豁免——语义
                # 对照上游 append_sampling_metadata，rh2 侧实现不 import 上游），
                # 并把 TurnRecord 的 logprob 列**切换为 support-normalized 值**
                # （对照 miles/rollout/sglang_rollout.py:255-256 的同款替换；T0-B：
                # 该列经 vendor 叶链落 Sample.rollout_log_probs = DIS/TIS 正式分母，
                # provenance=behavior_support_normalized）。全词表 logprob 原样留在
                # raw_response（output_token_logprobs -> capture store），只作诊断列。
                # B2（R6-ext）：解析产物不再丢弃——挂进 PendingTurn.turn_support，
                # commit 时交 hook 落 TurnTape（装配层的逐轮支持集事实源）。
                from repoharness2.adapters.miles.sampling_mask_assembly import (
                    parse_turn_sampling_support,
                )

                turn_support, output_log_probs = parse_turn_sampling_support(output_ids, meta)

            # 暂存捕获（record_turn 时提交）。capture 参数记录**生效值**：
            # temperature/top_p 若请求未带则为引擎默认 1.0（SGLang SamplingParams 默认）。
            # P0-1（codex 轮次 8）：proxy_result 挂进 PendingTurn，**finalize 移到
            # commit**——stage 只是本进程暂存，CC 的 SSE flush 发生在 slime
            # _respond()（本函数返回之后）。在 flush 前 finalize 会造成"delivered
            # 但 CC 没收到"的虚假交付；改到 record_turn/commit 成功（该轮确定进入
            # 轨迹树、CC 已收到）才 finalize，会话销毁时未 commit 的 draft 由
            # unregister abandon。
            staged = registry.stage(
                session_id,
                PendingTurn(
                    prompt_ids=list(prompt_ids),
                    capture_params={
                        "temperature": float(sp.get("temperature", 1.0)),
                        "top_p": top_p,
                        "max_new_tokens": int(sp.get("max_new_tokens", 4096)),
                        "return_top_p_token_ids": want_top_p_tape,
                        "return_routed_experts": want_routing,
                        # C1′-b 生效值补记：top_k 是支持集硬上界（T0-A；mask 开启时
                        # 已被前置校验强制为有限正整数），return_sampling_mask 记录
                        # 引擎实际收到的顶层旗标。
                        "top_k": (int(sp["top_k"]) if sp.get("top_k") is not None else None),
                        "return_sampling_mask": want_sampling_mask,
                    },
                    raw_response=data,
                    weight_version=(
                        str(meta["weight_version"]) if meta.get("weight_version") is not None else None
                    ),
                    request_id=request_id,
                    proxy_result=proxy_result,
                    turn_support=turn_support,
                    weight_version_spans=weight_version_spans,
                ),
            )
            if proxy_result is not None and not staged:
                # 并发 unregister：会话在 proxy 交付后、stage 前被摘除——
                # unregister 的 leftover 扫尾看不到这条 draft（从未进 pending），
                # 只能在这里 fail-closed（进下方统一 guard 关账）。
                raise CaptureWireOwnershipError(
                    f"sid={session_id} 在 proxy 交付后、stage 接管前被 unregister"
                    "——delivered draft 无人接管，fail-closed。"
                )
        except CapturePendingOverlapError:
            raise  # stage 内已 poison + abandon（含本轮 draft），再关会 double-abandon
        except Exception as exc:
            if proxy_result is not None and not staged:
                registry.poison.poison(session_id, "delivered_draft_orphaned_before_stage")
                try:
                    proxy_result.abandon_delivered(
                        f"pre_stage_failure:{type(exc).__name__}: {exc}"
                    )
                except ValueError:
                    pass  # 已 finalize/abandon（幂等，不 double-abandon）
                except Exception:  # noqa: BLE001 - abandon 已先关账（事务化）
                    registry.stats["abandon_evidence_failures"] = (
                        registry.stats.get("abandon_evidence_failures", 0) + 1
                    )
            raise
        return slime_common.TurnRecord(
            prompt_ids=list(prompt_ids),
            output_ids=output_ids,
            finish_reason=finish,
            output_log_probs=output_log_probs,
        )

    slime_common.call_sglang_generate = rh2_call_sglang_generate

    original_record_turn = TrajectoryManager.record_turn

    def rh2_record_turn(self, sid, *args, **kwargs):
        turns_before = self.turn_count(sid)
        result = original_record_turn(self, sid, *args, **kwargs)
        capture_ref = registry.commit(sid)  # 该轮已确定进入轨迹树（flush 成功之后才会走到这）
        # F1 身份制（commit 时刻绑定）：本次调用真的给树追加了 assistant
        # leaf（turn_count 增长；新 leaf 的 turn_index 恰为增长后的计数，
        # _attach_assistant_leaf 的 `_turn_count+1` 语义）且 commit 产出了
        # capture 记录 → 登记 capture_id↔turn 绑定。不绑定的两类情形都
        # 有兜底：record_turn 因空 prompt_messages 跳过附着（after==before，
        # capture 成孤儿、不被任何叶 span 引用）；max-context 短路轮无
        # stage（commit 返回 None，该轮 output_ids 为空、不产 trained span，
        # 若未来出现"有输出却无 capture"的轮，叶侧 span 导出会因解析不到
        # 绑定而 fail-closed）。
        turns_after = self.turn_count(sid)
        if turns_after > turns_before and capture_ref is not None:
            registry.bind_turn_identity(sid, turns_after, capture_ref)
        return result

    TrajectoryManager.record_turn = rh2_record_turn
    slime_common._rh2_capture_wire_installed = True
    slime_common._rh2_capture_wire_registry = registry
