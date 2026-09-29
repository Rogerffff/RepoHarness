"""桩模型端点（决策包 #8/#9/#10 事实采集版）。

复制自 `experiments/base_probe_fixes_20260923/stub_anthropic_endpoint.py`（原脚本不改），SSE 形状不变；扩展：

  --count-tokens-mode zero|chars4|null
      zero   回 {"input_tokens": 0}（= vendored adapter `_count_tokens` 的现状）
      chars4 回 round(请求内全部文本字符数 / 4)（粗略估计，不是真实 tokenizer；只用来给 CC 一个 >25,000 的数）
      null   回 {"input_tokens": null}（看 CC 是否退回自己的字符估计）
  --usage-start N --usage-step M
      主循环请求在 message_start / message_delta 的 usage.input_tokens 报 N + j*M，
      j = 自启动或上一次压缩以来的主循环请求序号（从 0 起）；不给则恒 100（与原桩相同）
  压缩请求识别：最后一条 user 消息的文本含 "Your task is to create a detailed summary" 或
      "CRITICAL: Respond with TEXT ONLY" → 回一段 <summary> 文本（不消耗剧本步），usage 报 1000，并把 j 归零
  剧本项新增字段：{"kind": "http_error", "status": 400, "body": {...}} 自定义错误体（prompt too long 复现）；
      text 步可带 "stop_reason" / "output_tokens" / "input_tokens"（模拟 adapter 溢出时回的空文本 + stop_reason=max_tokens）

每个请求体原样落盘到 <out>/requests/{messages,count_tokens}_NNN.json（不记 Authorization / x-api-key 头）。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import secrets
import time
from pathlib import Path

from aiohttp import web

COMPACT_MARKERS = ("Your task is to create a detailed summary", "CRITICAL: Respond with TEXT ONLY")
SUMMARY_TEXT = (
    "<analysis>stub analysis</analysis>\n<summary>\n1. Primary Request and Intent: stub acceptance run.\n"
    "2. Key Technical Concepts: none.\n3. Files and Code Sections: none.\n4. Errors and fixes: none.\n"
    "5. Problem Solving: none.\n6. All user messages: the acceptance prompt.\n7. Pending Tasks: continue the scripted tool calls.\n"
    "8. Current Work: scripted Bash calls.\n9. Optional Next Step: continue.\n</summary>"
)


def _texts(obj) -> list[str]:
    """请求内所有文本（字符串内容、text 块、tool_result 内容、system 文本）。"""
    out: list[str] = []
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, list):
        for x in obj:
            out.extend(_texts(x))
    elif isinstance(obj, dict):
        t = obj.get("type")
        if t == "text" and isinstance(obj.get("text"), str):
            out.append(obj["text"])
        elif t == "tool_result":
            out.extend(_texts(obj.get("content")))
        elif t == "tool_use":
            out.append(json.dumps(obj.get("input"), ensure_ascii=False))
        elif "content" in obj:
            out.extend(_texts(obj.get("content")))
    return out


def _last_user_text(parsed: dict) -> str:
    msgs = parsed.get("messages") or []
    for m in reversed(msgs):
        if m.get("role") == "user":
            return "\n".join(_texts(m.get("content")))
    return ""


class Stub:
    def __init__(self, script: list[dict], out: Path, ns: argparse.Namespace) -> None:
        self.script = script
        self.out = out
        self.ns = ns
        (out / "requests").mkdir(parents=True, exist_ok=True)
        self.n_messages = 0
        self.n_count_tokens = 0
        self.step_idx = 0  # 剧本步游标（压缩请求不消耗）
        self.ramp_j = 0
        self.log: list[dict] = []

    def _record(self, kind: str, request: web.Request, body: bytes, extra: dict) -> dict:
        idx = self.n_messages if kind == "messages" else self.n_count_tokens
        entry = {
            "at": round(time.time(), 3), "kind": kind, "index": idx, "path": request.path_qs, "bytes": len(body),
            "headers": {k: v for k, v in request.headers.items() if k.lower() not in ("authorization", "x-api-key")},
            **extra,
        }
        self.log.append(entry)
        (self.out / "requests" / f"{kind}_{idx:03d}.json").write_bytes(body)
        (self.out / "stub_log.json").write_text(json.dumps(self.log, ensure_ascii=False, indent=1), encoding="utf-8")
        return entry

    async def health(self, request: web.Request) -> web.Response:
        return web.json_response({"ok": True, "messages": self.n_messages, "count_tokens": self.n_count_tokens})

    async def count_tokens(self, request: web.Request) -> web.Response:
        body = await request.read()
        mode = self.ns.count_tokens_mode
        facts: dict = {"mode": mode}
        try:
            parsed = json.loads(body)
            texts = _texts(parsed.get("messages")) + _texts(parsed.get("system"))
            chars = sum(len(t) for t in texts)
            tools_chars = len(json.dumps(parsed.get("tools") or [], ensure_ascii=False)) if parsed.get("tools") else 0
            facts.update({"top_keys": sorted(parsed.keys()), "n_messages": len(parsed.get("messages") or []),
                          "n_tools": len(parsed.get("tools") or []), "text_chars": chars, "tools_chars": tools_chars,
                          "chars4_estimate": round((chars + tools_chars) / 4)})
        except Exception as exc:  # noqa: BLE001
            facts["parse_error"] = f"{type(exc).__name__}: {exc}"[:200]
        if mode == "zero":
            value = 0
        elif mode == "chars4":
            value = facts.get("chars4_estimate", 0)
        else:
            value = None
        facts["returned_input_tokens"] = value
        self._record("count_tokens", request, body, facts)
        self.n_count_tokens += 1
        return web.json_response({"input_tokens": value})

    async def messages(self, request: web.Request) -> web.StreamResponse:
        body = await request.read()
        compaction = False
        try:
            parsed = json.loads(body)
            last = (parsed.get("messages") or [{}])[-1]
            content = last.get("content")
            has_tool_result = isinstance(content, list) and any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content)
            tool_result_text = ""
            tool_result_is_error = None
            if has_tool_result:
                for b in content:
                    if isinstance(b, dict) and b.get("type") == "tool_result":
                        c = b.get("content")
                        tool_result_text = c if isinstance(c, str) else json.dumps(c, ensure_ascii=False)
                        tool_result_is_error = b.get("is_error")
            lut = _last_user_text(parsed)
            compaction = any(m in lut for m in COMPACT_MARKERS)
            summary = {"n_messages_in_request": len(parsed.get("messages") or []), "last_role": last.get("role"),
                       "last_has_tool_result": has_tool_result, "last_tool_result_chars": len(tool_result_text),
                       "last_tool_result_is_error": tool_result_is_error, "last_tool_result_text": tool_result_text[:1500],
                       "n_tools": len(parsed.get("tools") or []), "stream": parsed.get("stream"), "model": parsed.get("model"),
                       "max_tokens": parsed.get("max_tokens"), "compaction_request": compaction}
        except Exception as exc:  # noqa: BLE001 - 记录形状即可
            summary = {"parse_error": f"{type(exc).__name__}: {exc}"[:200]}

        if compaction:
            step = {"kind": "text", "text": SUMMARY_TEXT, "_compaction_reply": True}
            in_tok = 1000
        else:
            idx = self.step_idx
            step = self.script[idx] if idx < len(self.script) else {"kind": "text", "text": "done (script exhausted)"}
            self.step_idx += 1
            if self.ns.usage_start is not None:
                in_tok = int(self.ns.usage_start + self.ramp_j * self.ns.usage_step)
            else:
                in_tok = 100
        self._record("messages", request, body, {"step": step, "script_step_index": None if compaction else self.step_idx - 1,
                                                  "usage_input_tokens_reported": in_tok, "ramp_j": None if compaction else self.ramp_j, **summary})
        self.n_messages += 1
        if compaction:
            self.ramp_j = 0
        elif step.get("kind") != "http_error":
            self.ramp_j += 1

        kind = step["kind"]
        if kind == "http_error":
            payload = step.get("body") or {"type": "error", "error": {"type": "overloaded_error", "message": "stub"}}
            return web.json_response(payload, status=int(step.get("status", 529)))
        cut_after = step.get("after") if kind == "cut" else None
        out = web.StreamResponse(status=200, headers={"Content-Type": "text/event-stream", "Cache-Control": "no-cache", "Connection": "keep-alive"})
        await out.prepare(request)
        if cut_after == "headers":
            return await self._cut(request, out)

        async def emit(event: str, data: dict) -> bool:
            await out.write(f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode())
            return cut_after == event

        out_tok = int(step.get("output_tokens", 10))
        if step.get("input_tokens") is not None:
            in_tok = int(step["input_tokens"])
        if await emit("message_start", {"type": "message_start", "message": {
                "id": f"msg_{secrets.token_hex(12)}", "type": "message", "role": "assistant", "model": "slime-actor",
                "content": [], "stop_reason": None, "stop_sequence": None, "usage": {"input_tokens": in_tok, "output_tokens": 0}}}):
            return await self._cut(request, out)
        if kind == "hang":
            await asyncio.sleep(float(step.get("seconds", 600)))
            return await self._cut(request, out)
        if kind == "tool_use":
            start = {"type": "tool_use", "id": f"toolu_{secrets.token_hex(8)}", "name": step["name"], "input": {}}
            delta = {"type": "input_json_delta", "partial_json": json.dumps(step["input"], ensure_ascii=False)}
            stop_reason = "tool_use"
        else:
            start = {"type": "text", "text": ""}
            delta = {"type": "text_delta", "text": step.get("text", "done")}
            stop_reason = step.get("stop_reason", "end_turn")  # 可模拟 adapter 溢出时的空文本 + max_tokens
        if await emit("content_block_start", {"type": "content_block_start", "index": 0, "content_block": start}):
            return await self._cut(request, out)
        if await emit("content_block_delta", {"type": "content_block_delta", "index": 0, "delta": delta}):
            return await self._cut(request, out)
        if await emit("content_block_stop", {"type": "content_block_stop", "index": 0}):
            return await self._cut(request, out)
        if await emit("message_delta", {"type": "message_delta", "delta": {"stop_reason": stop_reason, "stop_sequence": None},
                                        "usage": {"input_tokens": in_tok, "output_tokens": out_tok}}):
            return await self._cut(request, out)
        await emit("message_stop", {"type": "message_stop"})
        await out.write_eof()
        return out

    async def _cut(self, request: web.Request, out: web.StreamResponse) -> web.StreamResponse:
        transport = request.transport
        if transport is not None:
            transport.abort()
        return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--listen-host", default="172.17.0.1")
    ap.add_argument("--listen-port", type=int, default=18100)
    ap.add_argument("--script", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--count-tokens-mode", choices=("zero", "chars4", "null"), default="zero")
    ap.add_argument("--usage-start", type=int, default=None)
    ap.add_argument("--usage-step", type=int, default=0)
    ns = ap.parse_args()
    stub = Stub(json.loads(Path(ns.script).read_text(encoding="utf-8")), Path(ns.out_dir), ns)
    app = web.Application(client_max_size=64 * 1024 * 1024)
    app.router.add_get("/__stub_health", stub.health)
    app.router.add_post("/v1/messages", stub.messages)
    app.router.add_post("/v1/messages/count_tokens", stub.count_tokens)
    web.run_app(app, host=ns.listen_host, port=ns.listen_port, print=None, access_log=None)


if __name__ == "__main__":
    main()
