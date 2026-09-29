"""探针网关的 CPU 窄验收：受控上游三种形态 → 经 model_gateway.py → 客户端看到什么。
  normal        完整 SSE（含 message_stop）→ 客户端读完整流
  eof_no_stop   发到 message_delta 后上游**干净结束** HTTP（无 message_stop）→ 期望网关中止下游（客户端读流报错）
  abort         发 content_block_start 后上游直接断连 → 期望网关中止下游
同时回读网关 responses.jsonl 的 stream_error。用法：gateway_check.py --out DIR
"""
import argparse, asyncio, json, subprocess, sys, tempfile
from pathlib import Path
from aiohttp import ClientSession, web

HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True)
ap.add_argument("--up-port", type=int, default=18321); ap.add_argument("--gw-port", type=int, default=18322)
ns = ap.parse_args(); out = Path(ns.out); out.mkdir(parents=True, exist_ok=True)
MODE = {"m": "normal"}

def ev(name, data):
    return f"event: {name}\ndata: {json.dumps(data)}\n\n".encode()

async def messages(request):
    await request.read()
    r = web.StreamResponse(status=200, headers={"Content-Type": "text/event-stream"})
    await r.prepare(request)
    await r.write(ev("message_start", {"type": "message_start", "message": {"id": "m1", "type": "message", "role": "assistant", "model": "slime-actor", "content": [], "stop_reason": None, "usage": {"input_tokens": 5, "output_tokens": 0}}}))
    await r.write(ev("content_block_start", {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}}))
    if MODE["m"] == "abort":
        request.transport.abort(); return r
    await r.write(ev("content_block_delta", {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "hi"}}))
    await r.write(ev("content_block_stop", {"type": "content_block_stop", "index": 0}))
    await r.write(ev("message_delta", {"type": "message_delta", "delta": {"stop_reason": "end_turn"}, "usage": {"output_tokens": 1}}))
    if MODE["m"] == "normal":
        await r.write(ev("message_stop", {"type": "message_stop"}))
    await r.write_eof(); return r

async def main():
    app = web.Application(); app.router.add_post("/v1/messages", messages)
    runner = web.AppRunner(app); await runner.setup(); await web.TCPSite(runner, "127.0.0.1", ns.up_port).start()
    cfg = out / "gw.json"; cfg.write_text(json.dumps({"upstream_base": f"http://127.0.0.1:{ns.up_port}", "auth_style": "passthrough"}))
    gw = subprocess.Popen([sys.executable, str(HERE.parent / "base_probe_20260922" / "model_gateway.py"), "--config", str(cfg),
                           "--listen-host", "127.0.0.1", "--listen-port", str(ns.gw_port), "--log-dir", str(out / "gwlog")],
                          stdout=open(out / "gw_stdout.log", "wb"), stderr=subprocess.STDOUT)
    await asyncio.sleep(3)
    res = {}
    try:
        async with ClientSession() as s:
            for m in ("normal", "eof_no_stop", "abort"):
                MODE["m"] = m
                try:
                    async with s.post(f"http://127.0.0.1:{ns.gw_port}/v1/messages", json={"model": "slime-actor", "stream": True, "messages": []},
                                      headers={"Authorization": f"Bearer gwcheck{m.replace('_','')}01"}) as r:
                        body = await r.read()
                        res[m] = {"client": "read_complete", "status": r.status, "has_message_stop": b"message_stop" in body, "bytes": len(body)}
                except Exception as exc:  # noqa: BLE001
                    res[m] = {"client": f"error:{type(exc).__name__}"}
    finally:
        gw.terminate(); gw.wait(timeout=10); await runner.cleanup()
    for f in (out / "gwlog").rglob("responses.jsonl"):
        for line in f.read_text().splitlines():
            d = json.loads(line); res.setdefault("gateway_records", []).append({k: d.get(k) for k in ("status", "stream_error", "stop_reason", "bytes")})
    (out / "gateway_check.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps(res, ensure_ascii=False, indent=1))

asyncio.run(main())
