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

from repoharness2.adapters.slime.generate import GenerationCaptureHook


@dataclasses.dataclass
class PendingTurn:
    prompt_ids: list[int]
    capture_params: dict[str, Any]
    raw_response: dict[str, Any]
    weight_version: str | None


class CaptureRegistry:
    """sid -> (hook, 暂存轮, 按轮 weight_version) 的进程级登记表。"""

    def __init__(self) -> None:
        self.hooks: dict[str, GenerationCaptureHook] = {}
        self.pending: dict[str, PendingTurn] = {}
        self.weight_versions: dict[str, list[str]] = {}
        self.stats = {"staged": 0, "committed": 0, "dropped_uncommitted": 0}

    def register(self, sid: str, hook: GenerationCaptureHook) -> None:
        self.hooks[sid] = hook
        self.weight_versions[sid] = []

    def unregister(self, sid: str) -> None:
        self.hooks.pop(sid, None)
        if self.pending.pop(sid, None) is not None:
            self.stats["dropped_uncommitted"] += 1

    def stage(self, sid: str | None, turn: PendingTurn) -> None:
        if sid is None or sid not in self.hooks:
            return  # 非 rh2 会话（探针等）不捕获
        if self.pending.pop(sid, None) is not None:
            self.stats["dropped_uncommitted"] += 1  # 上一轮 flush 失败未入树
        self.pending[sid] = turn
        self.stats["staged"] += 1

    def commit(self, sid: str) -> None:
        hook = self.hooks.get(sid)
        turn = self.pending.pop(sid, None)
        if hook is None or turn is None:
            return
        hook.on_generate_response(
            prompt_token_ids=turn.prompt_ids,
            sampling_params=turn.capture_params,
            response=turn.raw_response,
        )
        if turn.weight_version is not None:
            self.weight_versions[sid].append(turn.weight_version)
        self.stats["committed"] += 1


def install_capture_wire(registry: CaptureRegistry) -> None:
    """安装两处接线：模块级 call_sglang_generate 替换 + record_turn 包装。

    幂等：重复调用只装一次（Ray actor 进程内单例）。
    """

    from slime.agent.adapters import common as slime_common
    from slime.agent.trajectory import TrajectoryManager

    if getattr(slime_common, "_rh2_capture_wire_installed", False):
        return

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

        payload: dict[str, Any] = {
            "rid": uuid.uuid4().hex,
            "input_ids": list(prompt_ids),
            "sampling_params": sp,
            "return_logprob": True,
        }
        if want_routing:
            payload["return_routed_experts"] = True
        headers = (
            {"X-SMG-Routing-Key": session_id} if session_id and session_id != "default" else None
        )
        timeout = aiohttp.ClientTimeout(total=None, sock_read=900)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as sess, sess.post(
                f"{adapter.sglang_url}/generate", json=payload, headers=headers
            ) as r:
                if r.status >= 400:
                    text = await r.text()
                    raise RuntimeError(f"sglang upstream {r.status}: {text[:400]}")
                data = await r.json(content_type=None)
        except (asyncio.CancelledError, aiohttp.ClientError, asyncio.TimeoutError):
            try:  # stock 同款：eager abort，释放引擎槽位
                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as s2:
                    await s2.post(f"{adapter.sglang_url}/abort_request", json={"rid": payload["rid"]})
            except Exception:
                pass
            raise

        meta = data.get("meta_info") or {}
        pairs = meta.get("output_token_logprobs") or []
        output_ids = [x[1] for x in pairs]
        output_log_probs = [float(x[0]) for x in pairs]
        finish = (meta.get("finish_reason") or {}).get("type", "stop") or "stop"

        # 暂存捕获（record_turn 时提交）。capture 参数记录**生效值**：
        # temperature/top_p 若请求未带则为引擎默认 1.0（SGLang SamplingParams 默认）。
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
