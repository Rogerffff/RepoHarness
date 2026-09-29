"""#3 上游流中断（基座探针交接包 §3；Codex §14.2 收窄）：**正式传输链**上的复现事实表。

装配（只有引擎与 tokenizer 是替身，其余全是正式实现）：
  真实 CC 2.1.205（容器，正式 profile / relay / 可信初始化，经正式 ClaudeCodeDriver）
    → relay 容器（RH2 sandbox_profile 的 TCP 转发器）
    → 宿主侧**故障代理**（本文件；四种流形态在这里制造）
    → 真实 vendored AnthropicAdapter app（run_app_in_thread，与生产同一入口；session guard 中间件）
    → 真实 capture wire（install_capture_wire）→ 进程内假引擎（/generate 应答按剧本）
  编排：真实 RolloutOrchestrator（fa_formal）+ make_per_rollout_adapter + threadsafe drain owner + registry poison / cap。

两个边界（Codex §14.2）：
  B：adapter 已写完 SSE 并 record_turn（commit）→ 下游未完整接收：由故障代理在 relay→CC 段制造
       S1 中途 RST；S2 chunked 正常结束但缺 message_stop（HTTP 完整、SSE 不完整）；S3 中途 FIN 无 chunk 结束标记；
       S4 只缺 message_stop 的 FIN（message_delta 之后断）。
  A：adapter SSE 写出中途失败（未 commit）：A1 进程内注入——目标轮的第 K 次 StreamResponse.write 抛 ConnectionResetError
       （vendored _run_turn 的 except 路径 → 499、不 record_turn）。
  S0 完整流作正控。切断都落在第 2 个请求（一个 tool_use 轮）：被 commit 的末轮含 CC 未执行的工具调用，正是交接包担心的形态。

事实（每场景）：CC 退出码与 result 事件、CC 是否重试（adapter 收到的 /v1/messages 数）、被切轮的工具是否执行、
adapter 是否 commit（capture 记录数）、是否 poison、是否装配 / 交付（delivered / remove_sample / completion_class /
termination_kind）、评分调用数、代理观察到的响应与切点。

    SLIME_AGENT_CC_PLATFORM_TARBALL=/work/probe/cc/claude-code-linux-x64-2.1.205.tgz \
    .venv/bin/python experiments/base_probe_fixes_20260923/stream3_formal_chain.py \
        --prepared-summary /work/probe/replay/prepared_a1/replay_summary.json --task conan-io__conan-15422 \
        --scenario S1 --out-dir /work/probe/runs/s3_S1 --run-id s3s1a
"""

from __future__ import annotations

import argparse
import dataclasses
import asyncio
import hashlib
import json
import os
import re
import socket
import struct
import sys
import time
import uuid
import zlib
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
RH2 = HERE.parents[1]
sys.path[:0] = [str(RH2 / "src"), str(RH2 / "tests"), str(RH2 / "tests" / "adapters")]

MARK = "RH2S3T"
GEN_PROMPT_TOKEN = 2  # 假 tokenizer 的"生成提示"token（assistant 渲染以它开头，add_generation_prompt 也追加它）


# ---------------------------------------------------------------------------
# 剧本：按"请求里 tool 消息数"选轮（重试同一轮会拿到同一应答）
# ---------------------------------------------------------------------------


def bash_call(cmd: str) -> str:
    return f"<tool_call><function=Bash><parameter=command>{cmd}</parameter></function></tool_call>"


TURNS = [
    {"text": bash_call(f"echo {MARK}0"), "kind": "tool_use"},
    {"text": bash_call(f"echo {MARK}1 > /tmp/rh2s3_t1_ran; echo {MARK}1"), "kind": "tool_use"},  # 被切的轮
    {"text": bash_call(f"echo {MARK}2; cat /tmp/rh2s3_t1_ran 2>&1"), "kind": "tool_use"},  # 切后若继续：这一轮能看见上一轮是否执行
    {"text": "All done.", "kind": "text"},
]
OUTPUT_LEN = 6


def turn_output_ids(k: int) -> list[int]:
    return [7000 + 100 * k + i for i in range(OUTPUT_LEN)]


class ScriptState:
    """假 tokenizer 与假引擎共享：最近一次渲染看到的 tool 消息数 → 下一应答的轮号；压缩请求标记。"""

    def __init__(self) -> None:
        self.last_tool_msgs = 0
        self.renders: list[dict] = []
        self.engine_calls: list[dict] = []
        self.compaction_request = False
        self.compactions = 0
        self.post_compaction_done = False
        self.summary_ids = lambda: [7900 + i for i in range(OUTPUT_LEN)]


class RealTokenizerScript:
    """真实 tokenizer（HF 目录）：渲染 / decode / count 都是真的；只有引擎"采样"是剧本——输出 id = 剧本文本的真实编码。"""

    def __init__(self, state: ScriptState, tokenizer_dir: str) -> None:
        from transformers import AutoTokenizer

        self.state = state
        self.tok = AutoTokenizer.from_pretrained(tokenizer_dir)
        self.chat_template = self.tok.chat_template
        # 输出 id 末尾带 EOS（no_stop_trim 的真实形态；#5 parse wire 会剥掉可见字面量）→ 与模板渲染的 assistant 段逐 token 一致
        self._ids_by_turn = {k: self.tok.encode(t["text"], add_special_tokens=False) + [self.tok.eos_token_id] for k, t in enumerate(TURNS)}

    def turn_output_ids(self, k: int) -> list[int]:
        return list(self._ids_by_turn[k])

    @staticmethod
    def _xml_assistant(m: dict) -> dict:
        """CC 回放的 assistant（text + tool_calls）→ 引擎当初发出的 XML 文本形态（无 sglang 解析器的 CPU 夹具用 XML 回退格式；
        生产用模板原生格式 + sglang 解析器，同样是"渲染 = 采样文本"的闭环）。这样 prompt(k+1) 的 assistant 段 token 与
        引擎输出 id 一致，漂移只来自 CC 对参数的改写（#4 要测的东西）。"""
        if m.get("role") != "assistant" or not m.get("tool_calls"):
            return m
        parts = [m.get("content") or ""]
        for tc in m["tool_calls"]:
            fn = tc.get("function", {})
            args = fn.get("arguments") or {}
            params = "".join(f"<parameter={k}>{v}</parameter>" for k, v in args.items())
            parts.append(f"<tool_call><function={fn.get('name')}>{params}</function></tool_call>")
        return {"role": "assistant", "content": "".join(parts)}

    def apply_chat_template(self, messages, tools=None, tokenize=True, add_generation_prompt=True, **kw):
        messages = [self._xml_assistant(m) for m in messages]
        tool_msgs = sum(1 for m in messages if m.get("role") == "tool")
        self.state.last_tool_msgs = tool_msgs
        self.state.compaction_request = any(m.get("role") == "user" and COMPACTION_MARKER in json.dumps(m.get("content", "")) for m in messages)
        self.state.summary_ids = lambda: self.tok.encode(SUMMARY_TEXT, add_special_tokens=False) + [self.tok.eos_token_id]
        enc = self.tok.apply_chat_template(messages, tools=tools, tokenize=tokenize, add_generation_prompt=add_generation_prompt, **kw)
        ids = enc["input_ids"] if hasattr(enc, "__getitem__") and "input_ids" in enc else enc
        self.state.renders.append({"n_messages": len(messages), "tool_msgs": tool_msgs, "prompt_len": len(ids), "roles": [m.get("role") for m in messages]})
        return ids

    def decode(self, ids, skip_special_tokens=False, **kw):
        return self.tok.decode(ids, skip_special_tokens=skip_special_tokens, **kw)

    def encode(self, text, **kw):
        return self.tok.encode(text, **kw)

    def ids_for_turn(self, k):
        return self.turn_output_ids(k)


class FakeTokenizer:
    """前缀一致的确定性编码：system/user/tool 按内容 crc 编码；assistant 按剧本轮号 = [G] + 该轮引擎输出 id；
    add_generation_prompt 追加 [G]。decode 按输出 id 的首个 id 找回剧本文本（XML tool_call，vendored 回退解析器认）。"""

    chat_template = "fake-template"

    def __init__(self, state: ScriptState) -> None:
        self.state = state

    def _turn_of(self, message: dict) -> int | None:
        blob = json.dumps(message, ensure_ascii=False, sort_keys=True)
        m = re.search(rf"{MARK}(\d+)", blob)
        if m and message.get("role") == "assistant":
            return int(m.group(1))
        if message.get("role") == "assistant" and message.get("content") == "All done.":
            return len(TURNS) - 1
        return None

    def apply_chat_template(self, messages, tools=None, tokenize=True, add_generation_prompt=True, **_kw):
        ids: list[int] = [1]  # "模板头"
        tool_msgs = 0
        for m in messages:
            role = m.get("role")
            turn = self._turn_of(m) if role == "assistant" else None
            if turn is not None:
                ids += [GEN_PROMPT_TOKEN] + turn_output_ids(turn)
                continue
            if role == "tool":
                tool_msgs += 1
            content = json.dumps(m.get("content", ""), ensure_ascii=False)
            n = 1 + min(len(content) // 64, 40)
            base = 20000 + (zlib.crc32(content.encode()) % 20000)
            ids += [base + i for i in range(n)]
        if add_generation_prompt:
            ids.append(GEN_PROMPT_TOKEN)
        self.state.last_tool_msgs = tool_msgs
        self.state.compaction_request = any(m.get("role") == "user" and COMPACTION_MARKER in json.dumps(m.get("content", "")) for m in messages)
        self.state.renders.append({"n_messages": len(messages), "tool_msgs": tool_msgs, "prompt_len": len(ids),
                                   "roles": [m.get("role") for m in messages]})
        return ids

    def decode(self, ids, skip_special_tokens=False, **_kw):
        ids = list(ids)
        if ids and 7000 <= ids[0] < 7000 + 100 * len(TURNS):
            return TURNS[(ids[0] - 7000) // 100]["text"]
        return ""

    def encode(self, text, **_kw):
        return [1] * (1 + len(text) // 64)


# ---------------------------------------------------------------------------
# 假引擎：替换 capture_wire 的 aiohttp（同 tests/adapters_miles/test_b2_mask_chain 的替身形状）
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, status: int, payload: dict):
        self.status = status
        self._payload = payload

    async def json(self, content_type=None):
        return self._payload

    async def text(self):
        return json.dumps(self._payload)


class _PostCM:
    def __init__(self, resp):
        self._resp = resp

    async def __aenter__(self):
        return self._resp

    async def __aexit__(self, *exc):
        return False


class FakeEngine:
    def __init__(self, state: ScriptState, ids_for_turn=turn_output_ids) -> None:
        self.state = state
        self.ids_for_turn = ids_for_turn

    def respond(self, url: str, payload: dict | None) -> _FakeResponse:
        if url.endswith("/abort_request"):
            self.state.engine_calls.append({"url": url, "abort": True})
            return _FakeResponse(200, {"ok": True})
        if getattr(self.state, "compaction_request", False):
            # CC 的压缩请求（"CRITICAL: Respond with TEXT ONLY…"）：回一段摘要文本；之后的请求按剧本收尾
            self.state.compaction_request = False
            self.state.compactions += 1
            ids = self.state.summary_ids()
            self.state.engine_calls.append({"url": url, "turn": "summary", "prompt_len": len((payload or {}).get("input_ids") or [])})
            return _FakeResponse(200, {"text": SUMMARY_TEXT, "meta_info": {"id": f"rid-sum-{uuid.uuid4().hex[:6]}", "weight_version": "5",
                                                                          "finish_reason": {"type": "stop"}, "output_token_logprobs": [[-0.1, t, None] for t in ids]}})
        if getattr(self.state, "compactions", 0) and getattr(self.state, "post_compaction_done", False) is False and self.state.last_tool_msgs <= 1:
            self.state.post_compaction_done = True
            k = len(TURNS) - 1  # 压缩后历史只剩摘要 + 最后一对工具调用/结果：直接收尾
        else:
            k = min(self.state.last_tool_msgs, len(TURNS) - 1)
        ids = self.ids_for_turn(k)
        self.state.engine_calls.append({"url": url, "turn": k, "prompt_len": len((payload or {}).get("input_ids") or []),
                                        "rid": (payload or {}).get("rid")})
        return _FakeResponse(200, {
            "text": TURNS[k]["text"],
            "meta_info": {"id": f"rid-{k}-{uuid.uuid4().hex[:6]}", "weight_version": "5", "finish_reason": {"type": "stop"},
                          "output_token_logprobs": [[-0.1, t, None] for t in ids]},
        })


class _FakeClientSession:
    def __init__(self, engine: FakeEngine):
        self._engine = engine

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def post(self, url, json=None, headers=None):
        return _PostCM(self._engine.respond(url, json))


class FakeAiohttp:
    class ClientError(Exception):
        pass

    def __init__(self, engine: FakeEngine):
        self._engine = engine

    def ClientTimeout(self, **_kw):  # noqa: N802
        return None

    def ClientSession(self, **_kw):  # noqa: N802
        return _FakeClientSession(self._engine)


# ---------------------------------------------------------------------------
# 故障代理：relay → (proxy) → adapter；按响应序号对 SSE 分块流做手术
# ---------------------------------------------------------------------------


class FaultProxy:
    """HTTP/1.1 感知的 TCP 代理。请求方向原样转发；响应方向解析状态行/头/分块体，按 `plan` 对第 N 个
    /v1/messages 响应动手：rst_after / fin_after（不发终止 chunk）/ drop_message_stop（发终止 chunk）。"""

    def __init__(self, *, listen_host: str, upstream_host: str, upstream_port: int, plan: dict | None, log: list) -> None:
        self.listen_host, self.upstream_host, self.upstream_port = listen_host, upstream_host, upstream_port
        self.plan = plan or {}
        self.log = log
        self.response_index = 0  # 只数 SSE（chunked）响应
        self.port: int | None = None
        self._server = None

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle, host=self.listen_host, port=0)
        self.port = self._server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def _handle(self, cr: asyncio.StreamReader, cw: asyncio.StreamWriter) -> None:
        conn = {"opened": time.time(), "id": uuid.uuid4().hex[:6]}
        try:
            ur, uw = await asyncio.open_connection(self.upstream_host, self.upstream_port)
        except OSError as exc:
            self.log.append({**conn, "event": "upstream_connect_failed", "error": str(exc)})
            cw.close()
            return
        self.log.append({**conn, "event": "conn_open"})
        req_task = asyncio.create_task(self._pipe_requests(cr, uw, conn))
        try:
            await self._pipe_responses(ur, cw, uw, conn)
        finally:
            req_task.cancel()
            for w in (cw, uw):
                try:
                    w.close()
                except Exception:  # noqa: BLE001
                    pass
            self.log.append({**conn, "event": "conn_closed"})

    async def _pipe_requests(self, cr, uw, conn) -> None:
        try:
            while True:
                data = await cr.read(65536)
                if not data:
                    break
                head = data[:200]
                if head.startswith(b"POST ") or head.startswith(b"GET "):
                    self.log.append({**conn, "event": "request", "line": head.split(b"\r\n", 1)[0].decode(errors="replace")})
                uw.write(data)
                await uw.drain()
        except (asyncio.CancelledError, OSError, ConnectionError):
            pass
        finally:
            try:
                uw.write_eof()
            except Exception:  # noqa: BLE001
                pass

    async def _read_head(self, ur) -> tuple[bytes, dict[str, str]] | None:
        raw = bytearray()
        while True:
            line = await ur.readline()
            if not line:
                return None
            raw.extend(line)
            if line in (b"\r\n", b"\n"):
                break
        text = raw.decode(errors="replace")
        headers = {}
        for ln in text.split("\r\n")[1:]:
            if ":" in ln:
                k, _, v = ln.partition(":")
                headers[k.strip().lower()] = v.strip()
        return bytes(raw), headers

    async def _pipe_responses(self, ur, cw, uw, conn) -> None:
        while True:
            head = await self._read_head(ur)
            if head is None:
                return
            raw_head, headers = head
            if (headers.get("transfer-encoding", "").lower() == "chunked" and self.plan.get("mode") == "replace_529"
                    and self.plan.get("target_index") == self.response_index):
                # 把 adapter 的第 N 个 SSE 响应整个换成 529 overloaded（adapter 已 commit；看 CC 是否重试 → 同一轮再 commit）
                idx = self.response_index
                self.response_index += 1
                drained = await self._drain_chunked(ur)
                body = json.dumps({"type": "error", "error": {"type": "overloaded_error", "message": "s3 proxy injected 529"}}).encode()
                cw.write(b"HTTP/1.1 529 Overloaded\r\nContent-Type: application/json\r\nx-should-retry: true\r\nContent-Length: " + str(len(body)).encode() + b"\r\n\r\n" + body)
                await cw.drain()
                self.log.append({**conn, "event": "sse_response", "index": idx, "events": drained, "action": "replaced_with_529", "chunks": len(drained)})
                continue
            cw.write(raw_head)
            await cw.drain()
            if headers.get("transfer-encoding", "").lower() == "chunked":
                idx = self.response_index
                self.response_index += 1
                action = self.plan if self.plan.get("target_index") == idx else None
                rec = {**conn, "event": "sse_response", "index": idx, "chunks": 0, "events": [], "action": None, "bytes_forwarded": 0}
                self.log.append(rec)
                if action and action["mode"] == "replace_529":
                    # 头已经转发了：无法再改状态行——所以 529 替换在写头之前处理（见下方 head 分支）
                    pass
                done = await self._pipe_chunked(ur, cw, uw, action, rec)
                if done == "cut":
                    return
            elif "content-length" in headers:
                try:
                    body = await ur.readexactly(int(headers["content-length"]))
                except asyncio.IncompleteReadError as exc:
                    body = exc.partial
                    self.log.append({**conn, "event": "plain_response_truncated_by_upstream", "got": len(body), "expected": exc.expected})
                    cw.write(body)
                    return
                cw.write(body)
                await cw.drain()
                self.log.append({**conn, "event": "plain_response", "status_line": raw_head.split(b"\r\n", 1)[0].decode(errors="replace"), "bytes": len(body)})
            else:
                data = await ur.read()
                cw.write(data)
                await cw.drain()
                return

    async def _drain_chunked(self, ur) -> list[str]:
        events: list[str] = []
        while True:
            sl = await ur.readline()
            if not sl:
                events.append("<upstream-eof-before-terminator>")
                return events
            sz = int(sl.split(b";")[0].strip() or b"0", 16)
            if sz == 0:
                await ur.readline()
                return events
            d = await ur.readexactly(sz)
            await ur.readline()
            mm = re.search(rb"event: ([a-z_]+)", d)
            events.append((mm.group(1).decode() if mm else "?") + "(drained)")

    async def _pipe_chunked(self, ur, cw, uw, action: dict | None, rec: dict) -> str:
        """返回 'ok' | 'cut'。"""
        cut_pending = False
        truncating = False  # truncate_then_terminate：切点之后不再转发事件，但最后转发终止 chunk（HTTP 完整、SSE 截断）
        while True:
            size_line = await ur.readline()
            if not size_line:
                rec["events"].append("<upstream-eof-before-terminator>")
                return "cut"
            size = int(size_line.split(b";")[0].strip() or b"0", 16)
            if size == 0:
                trailer = await ur.readline()
                if action and action["mode"] == "drop_message_stop":
                    rec["action"] = "terminator_forwarded_after_drop"
                if action and action["mode"] == "truncate_then_terminate" and truncating:
                    rec["action"] = f"truncated_after:{action['after_event']}:terminator_forwarded"
                if action and action["mode"] in ("fin_after", "rst_after") and cut_pending:
                    rec["action"] = f"{action['mode']}:{action['after_event']}:no_terminator"
                    await self._cut(cw, action["mode"], rec)
                    return "cut"
                cw.write(size_line + trailer)
                await cw.drain()
                return "ok"
            data = await ur.readexactly(size)
            await ur.readline()
            rec["chunks"] += 1
            m = re.search(rb"event: ([a-z_]+)", data)
            ev = m.group(1).decode() if m else "?"
            rec["events"].append(ev)
            if action and action["mode"] == "drop_message_stop" and ev == "message_stop":
                rec["events"][-1] = "message_stop(DROPPED)"
                continue
            if truncating:
                rec["events"][-1] = ev + "(DROPPED)"
                continue
            if cut_pending:
                continue  # 已过切点：只排空上游（让 adapter 写完、commit），不再向下游转发
            cw.write(size_line + data + b"\r\n")
            await cw.drain()
            rec["bytes_forwarded"] += len(size_line) + len(data) + 2
            if action and action["mode"] == "truncate_then_terminate" and ev == action["after_event"]:
                truncating = True
                continue
            if action and action["mode"] in ("fin_after", "rst_after") and ev == action["after_event"]:
                cut_pending = True
                if action.get("cut_immediately", True):
                    rec["action"] = f"{action['mode']}:{ev}"
                    await self._cut(cw, action["mode"], rec)
                    # 继续排空上游到终止 chunk（不转发），让 adapter 正常收尾 → commit
                    while True:
                        sl = await ur.readline()
                        if not sl:
                            break
                        sz = int(sl.split(b";")[0].strip() or b"0", 16)
                        if sz == 0:
                            await ur.readline()
                            break
                        d = await ur.readexactly(sz)
                        await ur.readline()
                        mm = re.search(rb"event: ([a-z_]+)", d)
                        rec["events"].append((mm.group(1).decode() if mm else "?") + "(drained)")
                    return "cut"

    async def _cut(self, cw: asyncio.StreamWriter, mode: str, rec: dict) -> None:
        sock = cw.get_extra_info("socket")
        if mode == "rst_after" and sock is not None:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
        rec["cut_at"] = round(time.time(), 3)
        cw.close()


# ---------------------------------------------------------------------------
# 边界 A：进程内注入——目标轮的第 K 次 StreamResponse.write 抛 ConnectionResetError
# ---------------------------------------------------------------------------


class WriteFaultInjector:
    def __init__(self, target_turn: int, fail_at_write: int, log: list) -> None:
        self.target_turn, self.fail_at_write, self.log = target_turn, fail_at_write, log
        self.turn_seen = -1
        self.writes_in_turn = 0
        self.armed = False

    def install(self, state: ScriptState) -> None:
        from aiohttp import web

        original = web.StreamResponse.write
        injector = self

        async def write(resp_self, data):
            if injector.armed:
                injector.writes_in_turn += 1
                injector.log.append({"event": "write", "n": injector.writes_in_turn, "bytes": len(data)})
                if injector.writes_in_turn == injector.fail_at_write:
                    injector.armed = False
                    injector.log.append({"event": "injected_connection_reset", "at_write": injector.writes_in_turn})
                    raise ConnectionResetError("rh2 s3 injected: client connection lost mid-write")
            return await original(resp_self, data)

        web.StreamResponse.write = write  # type: ignore[assignment]
        self._state = state

    def arm_if_target(self, turn: int) -> None:
        if turn == self.target_turn and self.turn_seen != turn:
            self.turn_seen = turn
            self.writes_in_turn = 0
            self.armed = True


# ---------------------------------------------------------------------------
# 运行器
# ---------------------------------------------------------------------------


SCENARIOS = {
    "S0": {"desc": "完整流（正控）", "plan": None},
    "S1": {"desc": "第 2 个 SSE 响应 content_block_start 之后中途 RST（adapter 已 commit）", "plan": {"target_index": 1, "mode": "rst_after", "after_event": "content_block_start"}},
    "S2": {"desc": "第 2 个 SSE 响应缺 message_stop、chunked 正常结束（HTTP 完整 / SSE 不完整；adapter 已 commit）", "plan": {"target_index": 1, "mode": "drop_message_stop"}},
    "S3": {"desc": "第 2 个 SSE 响应 content_block_start 之后中途 FIN、无 chunk 结束标记（adapter 已 commit）", "plan": {"target_index": 1, "mode": "fin_after", "after_event": "content_block_start"}},
    "S4": {"desc": "第 2 个 SSE 响应 message_delta 之后 FIN（只缺 message_stop、无 chunk 结束标记；adapter 已 commit）", "plan": {"target_index": 1, "mode": "fin_after", "after_event": "message_delta"}},
    "A1": {"desc": "边界 A：第 2 轮 adapter 第 3 次 write（content_block_start 之后）抛 ConnectionResetError → 499、不 commit", "plan": None, "inject": {"turn": 1, "fail_at_write": 3}},
    "S5": {"desc": "第 2 个 SSE 响应在 content_block_start 之后截断但 chunked 正常结束（HTTP 完整 / SSE 在消息中途截断 = B 线旧网关 EOF 即 write_eof 的形态；adapter 已 commit）", "plan": {"target_index": 1, "mode": "truncate_then_terminate", "after_event": "content_block_start"}},
    "S6": {"desc": "第 2 个 SSE 响应在 content_block_delta 之后截断但 chunked 正常结束（工具入参已到、无 content_block_stop / message_delta；adapter 已 commit）", "plan": {"target_index": 1, "mode": "truncate_then_terminate", "after_event": "content_block_delta"}},
    "S8": {"desc": "第 2 个响应被整个换成 529 overloaded + x-should-retry:true（adapter 已 commit）：CC 是否重试 → 同一轮再 commit", "plan": {"target_index": 1, "mode": "replace_529"}},
    "R1": {"desc": "#8(i) 真实计数验收：T0 生成 1801 行大文件，T1 用 Read 整文件读 → CC 调 count_tokens（RH2 wire 回真实计数）→ Read 按上限截断", "plan": None, "script": "bigfile"},
    "C1": {"desc": "#8(ii) 反例：窗口 8192 + 输出预留 1024 → 主动压缩阈值为负（CC 13,000 固定预留）→ 每轮都压 → 熔断退出 1", "plan": None, "script": "overflow"},
    "C2": {"desc": "#8(iii) 被动压缩验收：关掉主动压缩（--no-auto-compact），连续大 Bash 输出累积到超过服务上限 → RH2 capture wire 回 400 prompt too long → CC 被动压缩（摘要请求受同一真实上限）→ 继续", "plan": None, "script": "accumulate"},
    "C3": {"desc": "#8(ii) 主动压缩验收：窗口 / 压缩窗口 / 输出预留按测试参数注入，连续大 Bash 输出让 usage 超过阈值 → CC 主动压缩 → 摘要请求受同一上限 → 继续", "plan": None, "script": "accumulate"},
    "W1": {"desc": "#4 表示成本核验（改写组）：cd /testbed && 前缀、Edit 不带 replace_all、Write/Edit 行尾空白——CC 回放时规范化参数，看消息树分支 / 训练行 / 输入 token", "plan": None, "script": "rewrite"},
    "W0": {"desc": "#4 对照组：同样的动作但不含 CC 会规范化的形态（无 cd 前缀、Edit 显式 replace_all、无行尾空白）", "plan": None, "script": "rewrite_control"},
}


def _edit_call(path: str, old: str, new: str, *, replace_all: bool | None) -> str:
    extra = f"<parameter=replace_all>{'true' if replace_all else 'false'}</parameter>" if replace_all is not None else ""
    return f"<tool_call><function=Edit><parameter=file_path>{path}</parameter><parameter=old_string>{old}</parameter><parameter=new_string>{new}</parameter>{extra}</function></tool_call>"


def _write_call(path: str, content: str) -> str:
    return f"<tool_call><function=Write><parameter=file_path>{path}</parameter><parameter=content>{content}</parameter></function></tool_call>"


REWRITE_TURNS = [  # 三类 CC 已知规范化（CCS normalizeToolInput）：去 `cd /testbed && `、补 `replace_all:false`、去行尾空白
    {"text": _write_call("/tmp/rh2_w4.py", "x = 1   \ny = 2\t\n"), "kind": "tool_use"},
    {"text": bash_call(f"cd /testbed && cat /tmp/rh2_w4.py; echo {MARK}1"), "kind": "tool_use"},
    {"text": _edit_call("/tmp/rh2_w4.py", "y = 2", "y = 3   ", replace_all=None), "kind": "tool_use"},
    {"text": bash_call(f"cd /testbed && cat /tmp/rh2_w4.py; echo {MARK}3"), "kind": "tool_use"},
    {"text": "All done.", "kind": "text"},
]
REWRITE_CONTROL_TURNS = [
    {"text": _write_call("/tmp/rh2_w4.py", "x = 1\ny = 2"), "kind": "tool_use"},  # 首轮实测：CC 也会去掉 Write 内容的末尾换行
    {"text": bash_call(f"cat /tmp/rh2_w4.py; echo {MARK}1"), "kind": "tool_use"},
    {"text": _edit_call("/tmp/rh2_w4.py", "y = 2", "y = 3", replace_all=False), "kind": "tool_use"},
    {"text": bash_call(f"cat /tmp/rh2_w4.py; echo {MARK}3"), "kind": "tool_use"},
    {"text": "All done.", "kind": "text"},
]

def _big_bash(i: int) -> dict:
    # 每次约 28K 字符（CC 的 Bash 工具结果截断上限约 30K 字符）≈ 7K token
    return {"text": bash_call(f"python3 -c \"print(' '.join('t{i}x%05d' % j for j in range(3100)))\"; echo {MARK}{i}"), "kind": "tool_use"}

ACCUMULATE_TURNS = [_big_bash(i) for i in range(6)] + [{"text": "All done.", "kind": "text"}]

OVERFLOW_TURNS = [
    {"text": bash_call(f"python3 -c \"print(' '.join('tok%05d' % i for i in range(2600)))\"; echo {MARK}0"), "kind": "tool_use"},  # ≈ 6K token 的工具输出
    {"text": bash_call(f"echo {MARK}1"), "kind": "tool_use"},
    {"text": "All done.", "kind": "text"},
]
COMPACTION_MARKER = "Respond with TEXT ONLY"
SUMMARY_TEXT = "Summary: the previous turns generated a large token list and confirmed the environment; nothing else pending."

BIGFILE_TURNS = [
    {"text": bash_call("python3 -c \"import random; random.seed(7); w=['alpha','beta','gamma','delta','epsilon','zeta','eta','theta']; "
                       "open('/tmp/rh2_big.py','w').write(''.join('# L%04d ' % i + ' '.join(random.choice(w)+str(random.randint(0,9999)) for _ in range(14)) + '\\n' for i in range(1801)))\"; "
                       f"wc -lc /tmp/rh2_big.py; echo {MARK}0"), "kind": "tool_use"},
    {"text": "<tool_call><function=Read><parameter=file_path>/tmp/rh2_big.py</parameter></function></tool_call>", "kind": "tool_use"},
    {"text": "All done.", "kind": "text"},
]


def summarize_stream(text: str) -> dict[str, Any]:
    from collections import Counter

    kinds: Counter[str] = Counter()
    stream_events: Counter[str] = Counter()
    tool_uses: list[str] = []
    tool_results: list[str] = []
    result: dict[str, Any] = {}
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            ev = json.loads(ln)
        except Exception:  # noqa: BLE001
            continue
        kinds[ev.get("type")] += 1
        if ev.get("type") == "stream_event":
            stream_events[(ev.get("event") or {}).get("type", "?")] += 1
        elif ev.get("type") == "assistant":
            for b in (ev.get("message") or {}).get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    tool_uses.append(json.dumps(b.get("input"), ensure_ascii=False)[:160])
        elif ev.get("type") == "user":
            for b in (ev.get("message") or {}).get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    c = b.get("content")
                    tool_results.append((c if isinstance(c, str) else json.dumps(c, ensure_ascii=False)))
        elif ev.get("type") == "result":
            result = {k: ev.get(k) for k in ("subtype", "is_error", "num_turns", "stop_reason", "duration_ms") if k in ev}
    return {"event_kinds": dict(kinds), "stream_events": dict(stream_events), "tool_uses": tool_uses, "tool_results": tool_results,
            "cc_result": result, "message_start_count": stream_events.get("message_start", 0)}


class Runner:
    def __init__(self, ns: argparse.Namespace) -> None:
        self.ns = ns
        self.out = Path(ns.out_dir)
        self.out.mkdir(parents=True, exist_ok=True)
        self.rec: dict[str, Any] = {"scenario": ns.scenario, "desc": SCENARIOS[ns.scenario]["desc"], "run_id": ns.run_id,
                                    "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "stages": {}}
        self.proxy_log: list = []
        self.inject_log: list = []
        self.adapter_requests: list = []

    def save(self) -> None:
        tmp = self.out / ".facts.json.tmp"
        tmp.write_text(json.dumps(self.rec, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        os.replace(tmp, self.out / "facts.json")

    def stage(self, name: str, **facts: Any) -> None:
        self.rec["stages"][name] = {"at": round(time.time(), 3), **facts}
        self.save()

    async def run(self) -> int:
        ns = self.ns
        os.environ["RH2_BRINGUP_ARTIFACT_DIR"] = str(self.out / "bringup_artifacts")
        Path(os.environ["RH2_BRINGUP_ARTIFACT_DIR"]).mkdir(parents=True, exist_ok=True)
        os.environ["SLIME_AGENT_CC_EXTRA_ARGS"] = ns.cc_extra_args
        os.environ.setdefault("SLIME_AGENT_CC_EXTRA_ENVS", "{}")

        from aiohttp import web
        from slime.agent.adapters.anthropic import AnthropicAdapter
        from slime.agent.aiohttp_threaded import run_app_in_thread

        from repoharness2.adapters.slime import capture_wire as cw
        from repoharness2.adapters.slime import sandbox_profile as sp
        from repoharness2.adapters.slime.bringup import ClaudeCodeDriver, FileFinalizationStore, bringup_leaf_facts, make_per_rollout_adapter
        from repoharness2.adapters.slime.generate import RolloutOrchestrator, SlimeBindingConfig
        from repoharness2.adapters.slime.prepared_task_face import build_grading_spec_from_host_view, rollout_spec_from_view
        from repoharness2.adapters.slime.replay_grade import load_context
        from test_slime_generate import SAMPLING_PARAMS, GradingSubmitStub, _Args
        from test_w1b_termination_facts_producer import _Barrier

        scenario = SCENARIOS[ns.scenario]
        if scenario.get("script") == "bigfile":
            TURNS[:] = BIGFILE_TURNS
        elif scenario.get("script") == "overflow":
            TURNS[:] = OVERFLOW_TURNS
        elif scenario.get("script") == "accumulate":
            TURNS[:] = ACCUMULATE_TURNS
        elif scenario.get("script") == "rewrite":
            TURNS[:] = REWRITE_TURNS
        elif scenario.get("script") == "rewrite_control":
            TURNS[:] = REWRITE_CONTROL_TURNS
        if ns.no_auto_compact:
            # 测试条件：只注入服务窗口（MAX_CONTEXT_TOKENS）与 Read 上限，不注入 AUTO_COMPACT_WINDOW / MAX_OUTPUT_TOKENS，
            # 让 CC 不主动压缩，从而跨过服务上限、触发 RH2 的 400 → 被动压缩路径
            from repoharness2.adapters.slime import cc_launch_conditions as _cc
            from repoharness2.adapters.slime import generate as _gen

            def _only_window(*, max_context_len, max_new_tokens, file_read_max_output_tokens):
                env = _cc.cc_context_env(max_context_len=max_context_len, max_new_tokens=max_new_tokens, file_read_max_output_tokens=file_read_max_output_tokens)
                env.pop(_cc.CC_AUTO_COMPACT_WINDOW_ENV, None)
                env.pop(_cc.CC_MAX_OUTPUT_TOKENS_ENV, None)
                return env

            _gen.cc_context_env = _only_window
        state = ScriptState()
        registry = cw.CaptureRegistry()
        cw.install_capture_wire(registry)
        from repoharness2.adapters.slime.count_tokens_wire import bind_count_tokens_adapter, install_count_tokens_wire

        install_count_tokens_wire()  # #8(i)：先安装后构造（与生产 bringup 同序）
        from repoharness2.adapters.slime.parse_wire import install_parse_wire  # #5：与生产同一挂接
        if ns.tokenizer_dir:
            tokenizer = RealTokenizerScript(state, ns.tokenizer_dir)
            engine = FakeEngine(state, ids_for_turn=tokenizer.turn_output_ids)
        else:
            tokenizer = FakeTokenizer(state)
            engine = FakeEngine(state)
        cw.aiohttp = FakeAiohttp(engine)  # 引擎替身：只替换 capture wire 的 HTTP 客户端
        from repoharness2.adapters.slime.rh2_anthropic_adapter import rh2_anthropic_adapter_cls  # #6(a)：与生产同一子类

        from repoharness2.adapters.slime.bringup import FORK_THRESHOLD_TOKENS  # 与生产同一分叉阈值（0 = 改写不合并、成死端叶）

        shared_adapter = rh2_anthropic_adapter_cls()(tokenizer=tokenizer, sglang_url="http://fake-engine", max_turns_per_sid=int(ns.max_turns_per_sid),
                                                     fork_threshold_tokens=FORK_THRESHOLD_TOKENS)
        self.rec["fork_threshold_tokens"] = FORK_THRESHOLD_TOKENS
        del AnthropicAdapter  # 只用生产子类
        bind_count_tokens_adapter(shared_adapter)
        install_parse_wire(
            eos_token=getattr(getattr(tokenizer, "tok", None), "eos_token", None),
            eos_token_id=getattr(getattr(tokenizer, "tok", None), "eos_token_id", None),  # R1：与生产同一对值
        )
        self.rec["tokenizer"] = ns.tokenizer_dir or "fake"
        shared_adapter.app.middlewares.append(cw.build_session_guard_middleware(registry))

        injector = None
        if scenario.get("inject"):
            injector = WriteFaultInjector(scenario["inject"]["turn"], scenario["inject"]["fail_at_write"], self.inject_log)
            injector.install(state)

        requests_seen = self.adapter_requests

        @web.middleware
        async def counting_middleware(request, handler):
            entry = {"at": round(time.time(), 3), "path": request.path, "index": len(requests_seen)}
            requests_seen.append(entry)
            if request.path == "/v1/messages":
                try:
                    body = await request.json()
                    n_tool = sum(1 for m in body.get("messages", []) if isinstance(m.get("content"), list)
                                 and any(isinstance(b, dict) and b.get("type") == "tool_result" for b in m["content"]))
                    entry["tool_results_in_request"] = n_tool
                    entry["n_messages"] = len(body.get("messages", []))
                    if injector is not None:
                        injector.arm_if_target(n_tool)
                except Exception:  # noqa: BLE001
                    pass
            try:
                resp = await handler(request)
            except web.HTTPException as exc:  # 溢出 400 等以异常形式返回：也记状态
                entry["status"] = exc.status
                raise
            entry["status"] = getattr(resp, "status", None)
            if request.path == "/v1/messages/count_tokens":
                try:
                    entry["count_tokens"] = json.loads(resp.text or "{}").get("input_tokens")
                except Exception:  # noqa: BLE001
                    entry["count_tokens"] = None
            return resp

        shared_adapter.app.middlewares.append(counting_middleware)  # 在 session guard 之后：guard 要 clone 未读 body 的请求
        app_handle = run_app_in_thread(shared_adapter.app, host="127.0.0.1", port=0, thread_name="rh2-s3-adapter",
                                       runner_kwargs={"handler_cancellation": True})
        self.rec["adapter_port"] = app_handle.port
        self.stage("adapter_started", port=app_handle.port)

        proxy = FaultProxy(listen_host=ns.proxy_host, upstream_host="127.0.0.1", upstream_port=app_handle.port,
                           plan=scenario["plan"], log=self.proxy_log)
        await proxy.start()
        self.rec["proxy_port"] = proxy.port
        self.stage("proxy_started", port=proxy.port, plan=scenario["plan"])

        profile = sp.rollout_profile_from_env(os.environ, model_proxy_upstream_host=ns.proxy_host, model_proxy_upstream_port=int(proxy.port))
        grader = sp.grader_profile_from_env(os.environ)
        summary = json.loads(Path(ns.prepared_summary).read_text(encoding="utf-8"))
        ctx = load_context(prepared_dir=summary["prepared_dir"], private_dir=summary["private_dir"],
                           manifest_sha256=summary["prepared_manifest_sha256"], rollout_profile=profile, grader_profile=grader,
                           artifacts_dir=self.out / "unused_artifacts", run_id=ns.run_id)
        task_id = ctx.resolve_task_id(ns.task)
        spec = rollout_spec_from_view(ctx.rollout_views[task_id], time_budget_seconds=int(ns.wall_seconds))
        spec = dataclasses.replace(spec, prompt=ns.prompt)  # 短提示：桩剧本不看它
        # 评分材料：与生产同一构造口（prepared 链的 host grading view）；评分执行本身是替身（GradingSubmitStub 回罐头报告）
        grading_spec = build_grading_spec_from_host_view(ctx.grading_views[task_id], image=spec.image, image_manifest_digest=spec.image_manifest_digest)
        self.rec.update({"task_id": task_id, "image": spec.image, "profile_digest": profile.digest()})

        labels = ("--label", f"rh2.run_id={ns.run_id}", "--label", "rh2.s3=1")
        docker = sp.default_docker_runner
        relay = await sp.start_egress_relay(docker, profile, run_id=ns.run_id, labels=labels)
        self.stage("relay_started", relay=relay.container_name, upstream=f"{ns.proxy_host}:{proxy.port}")
        config = SlimeBindingConfig(
            model_name="fake/stub", backend_version="0.5.9", renderer_cls_name="FakeRenderer", expected_renderer_cls_name="FakeRenderer",
            tokenizer_name="fake/stub", template_hash="sha256:" + hashlib.sha256(b"fake-template").hexdigest(),
            adapter_url=profile.harness_adapter_url(), harness_name="claude_code", expect_moe_routing=False,
            policy_version="5", execution_mode="fa_formal", require_real_weight_versions=True, reject_on_nonzero_harness_exit=True,
            staleness_threshold=4, max_context_len=int(ns.max_context_len), cc_file_read_max_output_tokens=ns.read_cap,
        )
        self.rec["test_params"] = {"max_context_len": ns.max_context_len, "read_cap": ns.read_cap, "max_new_tokens": ns.max_new_tokens, "no_auto_compact": ns.no_auto_compact}
        grading = GradingSubmitStub()
        orchestrator = RolloutOrchestrator(
            config=config, task_resolver=spec, grading_spec_resolver=lambda sample: grading_spec,
            adapter_factory=lambda hook, defaults: make_per_rollout_adapter(registry, shared_adapter, hook),
            harness_driver=ClaudeCodeDriver(), grading_submit=grading, docker=docker, runtime_quiescence_barrier=_Barrier(),
            leaf_facts_fn=bringup_leaf_facts,  # 生产的多叶链（压缩 / fan-out）轮次归属提取器
            finalization_store=FileFinalizationStore(self.out / "finalization"),
            session_drain_owner=cw.make_threadsafe_session_drain_owner(registry, app_handle.loop),
            sandbox_profile=profile, egress_relay=relay, runtime_profile_digest=sp.runtime_profile_digest(profile, grader),
            session_poison_check=registry.poison.is_poisoned, session_poison_subscribe=registry.poison.subscribe,
            session_poison_unsubscribe=registry.poison.unsubscribe, session_poison_release=registry.poison.release,
            session_poison_reason=registry.poison.reason, turn_budget_subscribe=registry.subscribe_turn_budget,
            turn_budget_unsubscribe=registry.unsubscribe_turn_budget, turn_budget_snapshot=registry.turn_budget_snapshot,
            capture_boundary_check=registry.assert_session_clean, artifact_dir=self.out / "rollouts",
        )
        from slime.utils.types import Sample  # vendored manager的 to_sample 按真实 Sample 字段复制（group_index / rollout_id / label）

        sample = Sample(index=0, group_index=0, prompt=ns.prompt, metadata={})
        tag = uuid.uuid4().hex[:8]
        sample.metadata.update({
            "rh2_rollout_execution_id": f"s3_{ns.scenario}_{tag}", "rh2_prompt_group_id": f"pg_s3_{tag}", "rh2_group_index": 0,
            "rh2_member_slot": 0, "rh2_physical_attempt_id": f"s3_{ns.scenario}_{tag}#p1-{tag}", "rh2_physical_attempt_seq": 1,
        })
        self.stage("orchestrator_built")
        t = time.monotonic()
        delivered = None
        error = None
        try:
            # top_p=1.0：假引擎不产 top-p tape；tape 不是本复现的对象（top_p<1 会要求引擎回 tape 字段）
            sampling = {**SAMPLING_PARAMS, "top_p": 1.0, "max_new_tokens": int(ns.max_new_tokens)}
            delivered = await asyncio.wait_for(orchestrator.generate(_Args(), sample, sampling), timeout=float(ns.wall_seconds) + 900)
        except Exception as exc:  # noqa: BLE001 - 如实记录（含 run-fatal）
            error = f"{type(exc).__name__}: {exc}"[:1200]
        self.rec["generate_seconds"] = round(time.monotonic() - t, 3)
        self.rec["generate_error"] = error
        audit = orchestrator.audits[-1] if orchestrator.audits else None
        self.collect(audit, delivered, grading, registry, state)
        self.rec["proxy_log"] = self.proxy_log
        self.rec["inject_log"] = self.inject_log
        self.rec["adapter_requests"] = self.adapter_requests
        self.rec["engine_calls"] = state.engine_calls
        self.rec["renders"] = state.renders
        self.save()
        # 收尾
        try:
            await sp.stop_egress_relay(docker, relay)
        finally:
            await proxy.stop()
            app_handle.stop() if hasattr(app_handle, "stop") else None
        left = await sp._call(docker, "ps", "-a", "--filter", f"label=rh2.run_id={ns.run_id}", "--format", "{{.Names}}", timeout=60)
        nets = await sp._call(docker, "network", "ls", "--filter", f"label=rh2.run_id={ns.run_id}", "--format", "{{.Name}}", timeout=60)
        self.rec["cleanup"] = {"labeled_containers_left": left.stdout.split(), "labeled_networks_left": nets.stdout.split()}
        self.rec["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.save()
        return 0

    def collect(self, audit, delivered, grading, registry, state: ScriptState) -> None:
        facts: dict[str, Any] = {}
        if audit is not None:
            hl = audit.harness_log or {}
            traj_text = ""
            if hl.get("stdout_path") and Path(hl["stdout_path"]).exists():
                traj_text = Path(hl["stdout_path"]).read_text(encoding="utf-8", errors="replace")
            ts = summarize_stream(traj_text)
            outcome = audit.outcome_v2 or {}
            cov = getattr(audit, "turn_coverage", None)
            facts["turn_coverage"] = cov if isinstance(cov, dict) else (dataclasses.asdict(cov) if dataclasses.is_dataclass(cov) else cov)
            facts.update({
                "harness_exit_code": audit.harness_exit_code,
                "harness_log": {k: hl.get(k) for k in ("exec_state", "exit_code", "stdout_bytes", "log_complete", "log_partial_reason", "stream_error")},
                "stderr_tail": (Path(hl["stderr_path"]).read_text(errors="replace")[-800:] if hl.get("stderr_path") and Path(hl["stderr_path"]).exists() else ""),
                "cc": ts,
                "cc_executed_cut_turn_tool": any(f"{MARK}1" in u for u in ts["tool_uses"]) and any(f"{MARK}1" in r for r in ts["tool_results"]),
                "cc_saw_cut_turn_tool_use": any(f"{MARK}1" in u for u in ts["tool_uses"]),
                "capture_record_count": audit.capture_record_count,
                "captured_output_tokens": audit.captured_output_tokens,
                "session_plane_drained": audit.session_plane_drained,
                "capture_closed": audit.capture_closed,
                "finalized": audit.finalized is not None,
                "outcome_v2": {k: outcome.get(k) for k in ("termination_kind", "completion_class", "reason_code", "runtime_failure_category")},
                "termination_kind_hint": audit.termination_kind_hint,
                "termination": audit.termination,
                "failure_records": [{"stage": f.stage, "error_type": f.error_type, "detail": f.detail[:300]} for f in audit.failure_records],
                "timeline": [e.step for e in audit.timeline][-25:],
                "grading_calls": len(grading.calls),
                "launch_session_id": getattr(getattr(audit, "launch_spec", None), "session_id", None),
            })
            sid = facts["launch_session_id"]
            if sid:
                facts["poisoned"] = registry.poison.is_poisoned(sid)
                facts["poison_reason"] = registry.poison.reason(sid) if facts["poisoned"] else None
        if delivered is not None:
            facts["delivered"] = [{
                "status": getattr(s, "status", None), "remove_sample": getattr(s, "remove_sample", None),
                "tokens": len(getattr(s, "tokens", []) or []), "response_length": getattr(s, "response_length", None),
                "loss_mask_sum": sum(getattr(s, "loss_mask", []) or []),
                "admission": {k: (((getattr(s, "metadata", {}) or {}).get("rh2_admission") or {}).get(k)) for k in ("eligibility_class", "grading_outcome", "grading_reward", "outcome")}
                if (getattr(s, "metadata", {}) or {}).get("rh2_admission") else None,
            } for s in delivered]
        facts["adapter_messages_requests"] = sum(1 for r in self.adapter_requests if r.get("path") == "/v1/messages")
        facts["script_tool_inputs"] = [t["text"][:200] for t in TURNS if t["kind"] == "tool_use"]  # 引擎侧原样（对照 CC 回放的 tool_uses）
        facts["count_tokens_calls"] = [{"status": r.get("status"), "input_tokens": r.get("count_tokens")} for r in self.adapter_requests if r.get("path") == "/v1/messages/count_tokens"]
        facts["compactions_served"] = state.compactions
        facts["prompt_too_long_400s"] = sum(1 for r in self.adapter_requests if r.get("path") == "/v1/messages" and r.get("status") == 400)
        if audit is not None and getattr(audit, "launch_spec", None) is not None:
            facts["launch_env_injections"] = {k: v for k, v in dict(audit.launch_spec.env_injections).items() if k.startswith("CLAUDE_CODE_")}
        if audit is not None and facts.get("cc"):
            reads = [t for t in facts["cc"]["tool_results"]]
            facts["read_tool_results"] = [{"chars": len(t), "lines": t.count("\n"), "truncated_note": ("[Truncated" in t)} for t in reads]
        facts["adapter_request_statuses"] = [(r.get("tool_results_in_request"), r.get("status")) for r in self.adapter_requests if r.get("path") == "/v1/messages"]
        facts["engine_turns_generated"] = [c.get("turn") for c in state.engine_calls if "turn" in c]
        self.rec["facts"] = facts


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prepared-summary", required=True)
    ap.add_argument("--task", required=True)
    ap.add_argument("--scenario", choices=sorted(SCENARIOS), required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--proxy-host", default="172.17.0.1")
    ap.add_argument("--wall-seconds", type=int, default=300)
    ap.add_argument("--max-turns-per-sid", type=int, default=12)
    ap.add_argument("--cc-extra-args", default="--disallowedTools Task WebFetch WebSearch --max-turns 8")
    ap.add_argument("--prompt", default="S3 acceptance: execute the tool calls you are given, then stop.")
    ap.add_argument("--tokenizer-dir", default=None, help="HF tokenizer 目录：渲染 / decode / count 用真实 tokenizer（引擎仍是剧本）")
    ap.add_argument("--max-context-len", type=int, default=0, help="测试参数：服务上下文上限（0 = 不配置窗口）")
    ap.add_argument("--max-new-tokens", type=int, default=4096, help="测试参数：采样 max_new_tokens（→ CLAUDE_CODE_MAX_OUTPUT_TOKENS）")
    ap.add_argument("--read-cap", type=int, default=None, help="测试参数：cc_file_read_max_output_tokens")
    ap.add_argument("--no-auto-compact", action="store_true", help="测试条件：不注入 AUTO_COMPACT_WINDOW / MAX_OUTPUT_TOKENS（只留服务窗口）")
    ns = ap.parse_args(argv)
    if not os.environ.get("SLIME_AGENT_CC_PLATFORM_TARBALL"):
        ap.error("需要环境变量 SLIME_AGENT_CC_PLATFORM_TARBALL")
    runner = Runner(ns)
    rc = asyncio.run(runner.run())
    f = runner.rec.get("facts", {})
    print(json.dumps({"scenario": ns.scenario, "generate_error": runner.rec.get("generate_error"), "exit": f.get("harness_exit_code"),
                      "cc_result": (f.get("cc") or {}).get("cc_result"), "adapter_messages_requests": f.get("adapter_messages_requests"),
                      "capture_record_count": f.get("capture_record_count"), "outcome": f.get("outcome_v2"),
                      "delivered": f.get("delivered"), "poisoned": f.get("poisoned"), "cut_tool_executed": f.get("cc_executed_cut_turn_tool")},
                     ensure_ascii=False, indent=1, default=str))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
