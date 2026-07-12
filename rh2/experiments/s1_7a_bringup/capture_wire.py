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

    def register(self, sid: str, hook: GenerationCaptureHook) -> None:
        # 轮次 11 身份兜底：中毒 SID（含归档）不得复用注册——稳定 ID
        # （task+index+group）跨补采/epoch 复用时先 fail-fast，不让 harness
        # 带毒起跑。execution 唯一身份是 FA-2 第一验收项。
        self.poison.check(sid)
        if sid in self.hooks:
            raise DuplicateActiveSessionError(sid)  # 轮次 12：不静默覆盖
        self.hooks[sid] = hook
        self.weight_versions[sid] = []
        self.pending.setdefault(sid, [])

    def assert_session_clean(self, sid: str) -> None:
        """评分/Gate 前边界断言（codex 轮次 12 P0 层 1）：该 SID 不得残留
        pending 暂存轮或 unfinalized delivered draft——任一在场说明交付账
        不完整（flush 失败/abandon 未闭合），先 poison 再抛，execution 缺员。"""

        problems: list[str] = []
        if self.pending.get(sid):
            problems.append(f"pending_turns={len(self.pending[sid])}")
        proxy = self.model_call_proxy
        if proxy is not None:
            stale = [a for a in proxy.unfinalized_deliveries if a.startswith(f"{sid}/")]
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

        queue = self.pending.get(sid)
        if not queue:
            raise RuntimeError(
                f"session {sid} 无暂存轮——capture wire 未接上（A4）或已被 commit。"
            )
        if len(queue) != 1:
            raise RuntimeError(
                f"session {sid} 暂存轮数量异常：{len(queue)}（期望恰好 1）。"
            )
        return queue[0]

    def session_deadline(self, sid: str | None) -> float | None:
        """会话 deadline（episode 预算传播）。首次调用即按默认预算起表——
        第一次模型调用 ≈ harness 启动后数秒，余量记入 notes。"""

        if sid is None:
            return None
        if sid not in self.session_deadlines:
            if self.default_session_budget_seconds is None:
                return None
            import time as _time

            self.session_deadlines[sid] = (
                _time.monotonic() + self.default_session_budget_seconds
            )
        return self.session_deadlines[sid]

    def next_turn_seq(self, sid: str | None) -> int:
        key = sid or "default"
        self._turn_seq[key] = self._turn_seq.get(key, 0) + 1
        return self._turn_seq[key]

    def unregister(self, sid: str) -> None:
        self.hooks.pop(sid, None)
        # P0-1（codex 轮次 8）：会话销毁时，暂存但未 commit 的轮 = 未真正交付
        # 给 CC（HTTP flush 前断连/失败）——显式 abandon delivered draft，
        # 消除"delivered 但 CC 没收到"的虚假交付。
        leftover = self.pending.pop(sid, None) or []
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
        self.session_deadlines.pop(sid, None)
        self._turn_seq.pop(sid, None)
        # 有界内存（codex 轮次 9 一般 4）：weight_versions 随会话清理——
        # provider 的 registry 交叉检查从此只覆盖**存活会话**（权威来源是
        # engine /get_weight_version，交叉检查弱化可接受、如实记录）。
        self.weight_versions.pop(sid, None)
        # 轮次 11 身份 4：unregister 只是 **adapter 会话关闭**，不是完整
        # execution 清理 ACK（容器清理在 orchestrator finally 更晚发生）——
        # poison 的归档（release）由 orchestrator 在 sandbox 清理完成后触发
        #（glue 注入 session_poison_release），此处不再提前释放。

    def stage(self, sid: str | None, turn: PendingTurn) -> None:
        if sid is None or sid not in self.hooks:
            return  # 非 rh2 会话（探针等）不捕获
        queue = self.pending.setdefault(sid, [])
        if queue:
            # P0-2（codex 轮次 9）：overlap = 并发同 session 请求在飞——FIFO
            # 猜测会串账（A 的 token 记到 B 名下），fail-closed：本请求失败 +
            # session 中毒 + 旧暂存 abandon（两轮都不可信：完成序未知）。
            self.stats["concurrent_overlap_seen"] += 1
            self.poison.poison(sid, "capture_pending_overlap")
            stale = queue.pop(0)
            self.stats["dropped_uncommitted"] += 1
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
        hook = self.hooks.get(sid)
        queue = self.pending.get(sid)
        if hook is None or not queue:
            return
        turn = queue.pop(0)  # 不变量 len<=1：弹出即本轮（无 FIFO 猜测面）
        hook.on_generate_response(
            prompt_token_ids=turn.prompt_ids,
            sampling_params=turn.capture_params,
            response=turn.raw_response,
        )
        if turn.weight_version is not None:
            self.weight_versions[sid].append(turn.weight_version)
        # P0-1：commit 成功（该轮已确定进入轨迹树、CC 已收到响应）才 finalize
        # delivered——capture ref 用真实 request_id（不再是复用的 staged:sid:tN）
        if turn.proxy_result is not None:
            try:
                turn.proxy_result.finalize_delivered(f"capture:{sid}:{turn.request_id}")
            except ValueError:
                pass  # 已 finalize（幂等，防重复 commit）
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
        return

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
        if proxy is None or session_id is None or session_id not in registry.hooks:
            # 未装配 proxy / 非 rh2 会话（探针）：原直连路径逐字保留
            data = await _send_once(1)
            request_id = last_rid.get("rid", uuid.uuid4().hex)
        else:
            # D-FA-3 生产接线（codex 轮次 7/8）：poison 快速拒绝 + deadline
            # 传播 + 发前 ACTIVE 等待 + 更新窗口 abort 内部重生成，全在 proxy 内
            registry.poison.check(session_id)
            turn_seq = registry.next_turn_seq(session_id)
            proxy_result = await proxy.call(
                session_id,
                f"t{turn_seq}",
                _send_once,
                session_id=session_id,
                poison_registry=registry.poison,
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
