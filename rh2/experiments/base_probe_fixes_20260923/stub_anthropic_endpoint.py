"""桩模型端点（Anthropic Messages 形状，SSE 与 vendored `slime.agent.adapters.anthropic._render_stream` 同形）。

用途：#2 真实 CC 2.1.205 验收（Brief §4 SR4）与 #3 流中断复现共用的夹具。不是模型：按 `--script` 给出的
逐请求剧本应答，把每个请求体原样落盘（不记 Authorization / x-api-key 头）。

    .venv/bin/python stub_anthropic_endpoint.py --listen-host 172.17.0.1 --listen-port 18090 \
        --script script.json --out-dir /work/probe/runs/<attempt>/stub

剧本：JSON 列表，第 i 个 `/v1/messages` 请求用第 i 项；用尽后一律 `end_turn` 文本。项的形状：
  {"kind": "tool_use", "name": "Bash", "input": {"command": "..."}}      → stop_reason=tool_use
  {"kind": "text", "text": "..."}                                        → stop_reason=end_turn
  {"kind": "hang", "seconds": 600}                                       → 发 message_start 后挂住（期限 / 强停复现）
  {"kind": "cut", "after": "content_block_start"|"message_start"|"message_delta"|"headers"}  → 发到该事件后直接断开（#3）
  {"kind": "http_error", "status": 529}                                  → 非 200（#3）
"""

from __future__ import annotations

import argparse
import asyncio
import json
import secrets
import time
from pathlib import Path

from aiohttp import web

_ORDER = ("headers", "message_start", "content_block_start", "content_block_delta", "content_block_stop", "message_delta", "message_stop")


class Stub:
    def __init__(self, script: list[dict], out: Path) -> None:
        self.script = script
        self.out = out
        (out / "requests").mkdir(parents=True, exist_ok=True)
        self.n_messages = 0
        self.n_count_tokens = 0
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
        self._record("count_tokens", request, body, {})
        self.n_count_tokens += 1
        return web.json_response({"input_tokens": 0})

    async def messages(self, request: web.Request) -> web.StreamResponse:
        body = await request.read()
        idx = self.n_messages
        step = self.script[idx] if idx < len(self.script) else {"kind": "text", "text": "done (script exhausted)"}
        try:
            parsed = json.loads(body)
            last = (parsed.get("messages") or [{}])[-1]
            content = last.get("content")
            has_tool_result = isinstance(content, list) and any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content)
            tool_result_text = ""
            if has_tool_result:
                for b in content:
                    if isinstance(b, dict) and b.get("type") == "tool_result":
                        c = b.get("content")
                        tool_result_text = c if isinstance(c, str) else json.dumps(c, ensure_ascii=False)
            summary = {"n_messages_in_request": len(parsed.get("messages") or []), "last_role": last.get("role"),
                       "last_has_tool_result": has_tool_result, "last_tool_result_text": tool_result_text[:2000],
                       "stream": parsed.get("stream"), "model": parsed.get("model"), "max_tokens": parsed.get("max_tokens")}
        except Exception as exc:  # noqa: BLE001 - 记录形状即可
            summary = {"parse_error": f"{type(exc).__name__}: {exc}"[:200]}
        self._record("messages", request, body, {"step": step, **summary})
        self.n_messages += 1

        kind = step["kind"]
        if kind == "http_error":
            return web.json_response({"type": "error", "error": {"type": "overloaded_error", "message": "stub"}}, status=int(step.get("status", 529)))
        cut_after = step.get("after") if kind == "cut" else None
        out = web.StreamResponse(status=200, headers={"Content-Type": "text/event-stream", "Cache-Control": "no-cache", "Connection": "keep-alive"})
        await out.prepare(request)
        if cut_after == "headers":
            return await self._cut(request, out)

        async def emit(event: str, data: dict) -> bool:
            await out.write(f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode())
            return cut_after == event

        in_tok, out_tok = 100, 10
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
            stop_reason = "end_turn"
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
        """不发终局事件，直接断开底层连接（对端看到 EOF / 连接重置）。"""
        transport = request.transport
        if transport is not None:
            transport.abort()
        return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--listen-host", default="172.17.0.1")
    ap.add_argument("--listen-port", type=int, default=18090)
    ap.add_argument("--script", required=True)
    ap.add_argument("--out-dir", required=True)
    ns = ap.parse_args()
    stub = Stub(json.loads(Path(ns.script).read_text(encoding="utf-8")), Path(ns.out_dir))
    app = web.Application(client_max_size=64 * 1024 * 1024)
    app.router.add_get("/__stub_health", stub.health)
    app.router.add_post("/v1/messages", stub.messages)
    app.router.add_post("/v1/messages/count_tokens", stub.count_tokens)
    web.run_app(app, host=ns.listen_host, port=ns.listen_port, print=None, access_log=None)


if __name__ == "__main__":
    main()
