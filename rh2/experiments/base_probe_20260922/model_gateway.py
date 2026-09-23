#!/usr/bin/env python3
"""基座探针（2026-09-22，B 线）：宿主侧模型网关。

**这不是 rh2 训练链的 adapter**：正式链里 rollout 容器经 egress relay 到宿主侧的 slime Anthropic adapter
（token 进 / token 出，带训练捕获）。探针只需要"求解"，所以这里放一个只做转发与留证的反向代理：

  rollout 容器（isolated internal 网络）→ rh2-egress-relay:18001（TCP 转发）→ 本网关（明文 HTTP）→ 上游

上游两种形态：
  - 外部 Anthropic 兼容端点（DeepSeek / 其它供应商）：本网关换上真实密钥后走 HTTPS；**密钥只在宿主，不进容器**；
  - 本机的 slime Anthropic adapter（→ SGLang /generate）：明文直转。

做的事：① 按 bearer token（= attempt 的 session_id）分目录落盘完整请求体与响应（SSE 原文）；② 固定真实模型名
（`force_model`：主模型与 CC 的辅助调用都改写成同一个 id，原值留在日志里）；③ 每个 session 的请求数上限（超限回
429 + `x-should-retry: false`，不回 404——CC 2.1.205 对流式创建阶段的 404 会绕过禁用开关再发一次非流式请求）；
④ 首字节下发之前的上游失败（连接错误 / 429 / 5xx）由本网关有界重试——容器内 CC 保持训练守卫
`CLAUDE_CODE_MAX_RETRIES=0`，重试 owner 在宿主；⑤ 汇总每个 session 的 usage。

不做的事：不改消息内容、不加系统提示、不过滤工具；工具清单由 CC 启动参数决定，服务端搜索是否关闭要看
落盘的请求体里有没有对应工具。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import aiohttp
from aiohttp import web

_SID_RE = re.compile(r"^[A-Za-z0-9_.-]{6,96}$")
_HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers",
    "transfer-encoding", "upgrade", "host", "content-length", "accept-encoding",
    "authorization", "x-api-key",
}
_RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504, 529}


def _now() -> float:
    return time.time()


class Gateway:
    def __init__(self, cfg: dict[str, Any], log_dir: Path) -> None:
        self.cfg = cfg
        self.log_dir = log_dir
        self.upstream_base = str(cfg["upstream_base"]).rstrip("/")
        key_file = cfg.get("api_key_file")
        self.api_key = Path(key_file).read_text(encoding="utf-8").strip() if key_file else None
        self.auth_style = cfg.get("auth_style", "bearer")  # bearer | x-api-key | both | passthrough | none
        self.force_model = cfg.get("force_model")
        self.max_requests = int(cfg.get("max_requests_per_session", 300))
        self.retry_attempts = int(cfg.get("upstream_retry_attempts", 4))
        self.retry_base = float(cfg.get("upstream_retry_base_seconds", 2.0))
        self.first_byte_timeout = float(cfg.get("first_byte_timeout_seconds", 900.0))
        self.extra_headers = dict(cfg.get("extra_upstream_headers") or {})
        self.body_overrides = dict(cfg.get("body_overrides") or {})  # 例如 {"temperature": 0.7}；逐项记入日志
        self.body_drop_keys = list(cfg.get("body_drop_keys") or [])
        self._counts: dict[str, int] = {}
        self._usage: dict[str, dict[str, int]] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._client: aiohttp.ClientSession | None = None

    async def client(self) -> aiohttp.ClientSession:
        if self._client is None:
            timeout = aiohttp.ClientTimeout(total=None, sock_connect=30, sock_read=self.first_byte_timeout)
            self._client = aiohttp.ClientSession(timeout=timeout, auto_decompress=True)
        return self._client

    # ------------------------------------------------------------------ 会话与落盘
    @staticmethod
    def _sid(request: web.Request) -> str | None:
        auth = request.headers.get("Authorization", "")
        token = auth[7:].strip() if auth.lower().startswith("bearer ") else request.headers.get("x-api-key", "").strip()
        return token if _SID_RE.match(token or "") else None

    def _dir(self, sid: str) -> Path:
        d = self.log_dir / sid
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _append(self, sid: str, name: str, row: dict[str, Any]) -> None:
        with open(self._dir(sid) / name, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def _add_usage(self, sid: str, usage: dict[str, Any] | None) -> None:
        if not isinstance(usage, dict):
            return
        acc = self._usage.setdefault(sid, {})
        for k, v in usage.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                acc[k] = acc.get(k, 0) + int(v)
        (self._dir(sid) / "usage.json").write_text(
            json.dumps({"requests": self._counts.get(sid, 0), "usage_sum": acc}, ensure_ascii=False, indent=1),
            encoding="utf-8",
        )

    def _upstream_headers(self, request: web.Request) -> dict[str, str]:
        headers = {k: v for k, v in request.headers.items() if k.lower() not in _HOP_BY_HOP}
        if self.auth_style == "passthrough":  # 上游是本机 slime adapter：它按 bearer 取 session_id
            for k in ("Authorization", "x-api-key"):
                if k in request.headers:
                    headers[k] = request.headers[k]
        if self.api_key and self.auth_style in ("bearer", "both"):
            headers["Authorization"] = f"Bearer {self.api_key}"
        if self.api_key and self.auth_style in ("x-api-key", "both"):
            headers["x-api-key"] = self.api_key
        headers.update(self.extra_headers)
        return headers

    # ------------------------------------------------------------------ 主处理
    async def handle(self, request: web.Request) -> web.StreamResponse:
        sid = self._sid(request)
        if sid is None:
            return web.json_response({"type": "error", "error": {"type": "authentication_error",
                                      "message": "probe gateway: missing/invalid session token"}}, status=401)
        raw = await request.read()
        is_messages = request.method == "POST" and request.path.rstrip("/").endswith("/v1/messages")
        seq = None
        body_obj: Any = None
        rewritten = raw
        meta: dict[str, Any] = {"ts": _now(), "method": request.method, "path": request.path_qs}
        if raw:
            try:
                body_obj = json.loads(raw)
            except Exception:  # noqa: BLE001
                body_obj = None
        if is_messages:
            self._counts[sid] = self._counts.get(sid, 0) + 1
            seq = self._counts[sid]
            meta["seq"] = seq
            if seq > self.max_requests:
                self._append(sid, "requests.jsonl", {**meta, "rejected": "session_request_cap", "cap": self.max_requests})
                return web.json_response(
                    {"type": "error", "error": {"type": "rate_limit_error",
                                                "message": f"probe gateway: session request cap {self.max_requests} reached"}},
                    status=429, headers={"x-should-retry": "false"},
                )
        if isinstance(body_obj, dict):
            meta["model_requested"] = body_obj.get("model")
            meta["stream"] = bool(body_obj.get("stream"))
            changed = False
            if self.force_model and "model" in body_obj and body_obj["model"] != self.force_model:
                body_obj["model"] = self.force_model
                changed = True
            for k, v in self.body_overrides.items():
                if body_obj.get(k) != v:
                    body_obj[k] = v
                    changed = True
            for k in self.body_drop_keys:
                if k in body_obj:
                    body_obj.pop(k)
                    changed = True
            meta["model_sent"] = body_obj.get("model")
            if changed:
                rewritten = json.dumps(body_obj, ensure_ascii=False).encode("utf-8")
        hdr_keep = {k: v for k, v in request.headers.items()
                    if k.lower() in ("anthropic-version", "anthropic-beta", "user-agent", "x-app", "content-type")}
        self._append(sid, "requests.jsonl", {**meta, "headers": hdr_keep, "body": body_obj if body_obj is not None
                                             else raw.decode("utf-8", "replace")[:2000]})

        url = self.upstream_base + request.path_qs
        headers = self._upstream_headers(request)
        client = await self.client()
        attempt = 0
        last_err = ""
        while True:
            attempt += 1
            t0 = _now()
            try:
                up = await client.request(request.method, url, data=rewritten if raw else None, headers=headers)
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                last_err = f"{type(exc).__name__}: {exc}"[:300]
                self._append(sid, "responses.jsonl", {"seq": seq, "attempt": attempt, "error": last_err, "seconds": round(_now() - t0, 3)})
                if attempt <= self.retry_attempts:
                    await asyncio.sleep(min(60.0, self.retry_base * (2 ** (attempt - 1))))
                    continue
                return web.json_response(
                    {"type": "error", "error": {"type": "api_error", "message": f"probe gateway upstream failure: {last_err}"}},
                    status=502, headers={"x-should-retry": "false"},
                )
            if up.status in _RETRYABLE_STATUS and attempt <= self.retry_attempts:
                text = (await up.text())[:1000]
                retry_after = up.headers.get("retry-after")
                up.release()
                self._append(sid, "responses.jsonl", {"seq": seq, "attempt": attempt, "status": up.status,
                                                      "retried": True, "body_head": text, "retry_after": retry_after})
                delay = self.retry_base * (2 ** (attempt - 1))
                try:
                    if retry_after:
                        delay = max(delay, float(retry_after))
                except ValueError:
                    pass
                await asyncio.sleep(min(90.0, delay))
                continue
            break

        status = 502 if up.status == 404 else up.status  # 任何错误路径不回 404（见模块说明）
        out_headers = {k: v for k, v in up.headers.items()
                       if k.lower() not in ("content-length", "content-encoding", "transfer-encoding", "connection")}
        if up.status == 404:
            out_headers["x-should-retry"] = "false"
        resp = web.StreamResponse(status=status, headers=out_headers)
        await resp.prepare(request)
        chunks: list[bytes] = []
        first_byte_at: float | None = None
        try:
            async for chunk in up.content.iter_any():
                if first_byte_at is None:
                    first_byte_at = _now()
                chunks.append(chunk)
                await resp.write(chunk)
            await resp.write_eof()
            stream_error = None
        except (aiohttp.ClientError, asyncio.TimeoutError, ConnectionResetError) as exc:
            stream_error = f"{type(exc).__name__}: {exc}"[:300]
        finally:
            up.release()
        payload = b"".join(chunks)
        ctype = up.headers.get("content-type", "")
        record: dict[str, Any] = {
            "seq": seq, "attempt": attempt, "status": up.status, "content_type": ctype,
            "seconds_total": round(_now() - t0, 3),
            "seconds_to_first_byte": round(first_byte_at - t0, 3) if first_byte_at else None,
            "bytes": len(payload), "stream_error": stream_error,
        }
        usage: dict[str, Any] | None = None
        if "text/event-stream" in ctype:
            name = f"resp_{seq if seq is not None else int(t0 * 1000)}.sse"
            (self._dir(sid) / name).write_bytes(payload)
            record["sse_file"] = name
            usage, stop_reason, model_seen = _usage_from_sse(payload)
            record["stop_reason"] = stop_reason
            record["model_reported"] = model_seen
        else:
            text = payload.decode("utf-8", "replace")
            try:
                obj = json.loads(text)
                record["body"] = obj
                if isinstance(obj, dict):
                    usage = obj.get("usage")
                    record["stop_reason"] = obj.get("stop_reason")
                    record["model_reported"] = obj.get("model")
            except Exception:  # noqa: BLE001
                record["body_head"] = text[:4000]
        record["usage"] = usage
        self._append(sid, "responses.jsonl", record)
        if is_messages and up.status == 200:
            self._add_usage(sid, usage)
        if stream_error:
            # 首字节之后上游中断：不能对下游正常收尾——CC 2.1.205 会把缺 message_stop 的流当成完整消息，
            # 会话以 success 结束并交出空补丁（09-22 DVC6954/DeepSeek a1 实例）。这里直接中止下游连接，让 CC 显式失败。
            try:
                if request.transport is not None:
                    request.transport.abort()
            except Exception:  # noqa: BLE001
                pass
        return resp

    async def health(self, _request: web.Request) -> web.Response:
        return web.json_response({"ok": True, "upstream": self.upstream_base, "force_model": self.force_model,
                                  "sessions": len(self._counts)})

    async def close(self, _app: web.Application) -> None:
        if self._client is not None:
            await self._client.close()


def _usage_from_sse(payload: bytes) -> tuple[dict[str, Any] | None, str | None, str | None]:
    """从 Anthropic SSE 原文里取 usage（message_start 的输入侧 + message_delta 的输出侧，后者覆盖同名键）。"""

    usage: dict[str, Any] = {}
    stop_reason = None
    model = None
    for line in payload.decode("utf-8", "replace").splitlines():
        if not line.startswith("data:"):
            continue
        try:
            ev = json.loads(line[5:].strip())
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(ev, dict):
            continue
        if ev.get("type") == "message_start":
            msg = ev.get("message") or {}
            model = msg.get("model") or model
            if isinstance(msg.get("usage"), dict):
                usage.update(msg["usage"])
        elif ev.get("type") == "message_delta":
            if isinstance(ev.get("usage"), dict):
                usage.update(ev["usage"])
            stop_reason = (ev.get("delta") or {}).get("stop_reason") or stop_reason
    flat = {k: v for k, v in usage.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
    return (flat or None), stop_reason, model


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="基座探针宿主侧模型网关")
    ap.add_argument("--config", required=True, help="JSON：upstream_base / api_key_file / auth_style / force_model / …")
    ap.add_argument("--listen-host", required=True, help="relay 能到达的宿主地址（通常是 docker0 网关 172.17.0.1）")
    ap.add_argument("--listen-port", type=int, required=True)
    ap.add_argument("--log-dir", required=True)
    ns = ap.parse_args(argv)
    cfg = json.loads(Path(ns.config).read_text(encoding="utf-8"))
    log_dir = Path(ns.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    gw = Gateway(cfg, log_dir)
    safe_cfg = {k: v for k, v in cfg.items() if k != "api_key_file"}
    (log_dir / "gateway_config.json").write_text(json.dumps(
        {"config": safe_cfg, "api_key_present": gw.api_key is not None, "started_at": _now(),
         "listen": f"{ns.listen_host}:{ns.listen_port}"}, ensure_ascii=False, indent=1), encoding="utf-8")
    app = web.Application(client_max_size=256 * 1024 * 1024)
    app.router.add_get("/__probe_gateway_health", gw.health)
    app.router.add_route("*", "/{tail:.*}", gw.handle)
    app.on_cleanup.append(gw.close)
    print(json.dumps({"probe_gateway": "starting", "listen": f"{ns.listen_host}:{ns.listen_port}",
                      "upstream": gw.upstream_base, "force_model": gw.force_model}), flush=True)
    web.run_app(app, host=ns.listen_host, port=ns.listen_port, print=None, access_log=None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
