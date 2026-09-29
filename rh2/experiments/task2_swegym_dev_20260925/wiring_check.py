"""探针接线的 CPU 窄验收（无 GPU、无 SGLang）：假 SGLang `/generate` + 真实 Qwen tokenizer + 探针 adapter 进程。

覆盖（对应 A→B 交接 §2 的装配）：
  W1 启动：qwen_adapter_server 按生产顺序装配后能起来；adapter_config.json 的 rh2_wrappers / adapter_class 如实；
  W2 count_tokens：POST /v1/messages/count_tokens 返回真实计数（>0，且随消息变长而增加），不再是恒 0；
  W3 #5 EOS：假上游最后一个采样 id 是 EOS 时，可见文本末尾的 `<|im_end|>` 字面量被剥；普通 token 拼出的同名文本
     （最后一个 id 不是 EOS）保留；/__probe_stats 的计数随之变化；
  W4 窗口：prompt 超过 max_context_tokens 时的实际表现（vendored 回 finish_reason=length 空输出 → HTTP 层看到什么），
     对应 overflow_400=false 的已知限制，只记事实。
不覆盖：工具调用 / 推理解析（需要 SGLang 解析器）、#6(a) 提醒并入（A 线已有单测；GPU 冒烟时从真实请求回读）。
用法：wiring_check.py --tokenizer Qwen/Qwen3-Coder-30B-A3B-Instruct --out /work/task2/runs/wiring
"""
import argparse, asyncio, json, os, subprocess, sys, time
from pathlib import Path

from aiohttp import ClientSession, web

HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument("--tokenizer", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--fake-port", type=int, default=18311); ap.add_argument("--adapter-port", type=int, default=18312)
ap.add_argument("--window", type=int, default=3000)
ns = ap.parse_args()
out = Path(ns.out); out.mkdir(parents=True, exist_ok=True)
from transformers import AutoTokenizer  # noqa: E402

tok = AutoTokenizer.from_pretrained(ns.tokenizer)
EOS_ID = tok.eos_token_id
MODE = {"next": "eos"}  # eos | literal_no_eos


async def generate(request):
    body = await request.json()
    txt = "Done." if MODE["next"] == "eos" else "Done.<|im_end|>"
    ids = tok.encode(txt, add_special_tokens=False)
    if MODE["next"] == "eos":
        ids = ids + [EOS_ID]
    else:  # 普通 token 拼出字面量：用字符级编码避开特殊 token
        ids = tok.encode("Done.", add_special_tokens=False) + [i for ch in "<|im_end|>" for i in tok.encode(ch, add_special_tokens=False)]
    return web.json_response({"text": tok.decode(ids), "meta_info": {"finish_reason": {"type": "stop"},
                              "output_token_logprobs": [[-0.1, i, None] for i in ids], "prompt_tokens": len(body["input_ids"])}})


async def main():
    app = web.Application(); app.router.add_post("/generate", generate)
    runner = web.AppRunner(app); await runner.setup(); await web.TCPSite(runner, "127.0.0.1", ns.fake_port).start()
    log_dir = out / "adapter_logs"
    proc = subprocess.Popen([sys.executable, str(HERE.parent / "base_probe_20260922" / "qwen_adapter_server.py"),
                             "--sglang-url", f"http://127.0.0.1:{ns.fake_port}", "--tokenizer", ns.tokenizer, "--tool-parser", "",
                             "--sampling-defaults", json.dumps({"max_new_tokens": 256}), "--max-context-tokens", str(ns.window),
                             "--listen-port", str(ns.adapter_port), "--log-dir", str(log_dir)],
                            stdout=open(out / "adapter_stdout.log", "wb"), stderr=subprocess.STDOUT)
    res = {}
    base = f"http://127.0.0.1:{ns.adapter_port}"
    hdr = {"x-api-key": "wiringcheck01", "anthropic-version": "2023-06-01", "Authorization": "Bearer wiringcheck01"}
    try:
        async with ClientSession() as s:
            for _ in range(120):
                try:
                    async with s.get(f"{base}/__probe_stats") as r:
                        if r.status == 200:
                            break
                except Exception:
                    await asyncio.sleep(1)
            res["W1_config"] = json.loads((log_dir / "adapter_config.json").read_text())
            def msgs(n):
                return {"model": "slime-actor", "max_tokens": 256, "messages": [{"role": "user", "content": "hello " * n}]}
            counts = []
            for n in (5, 200):
                async with s.post(f"{base}/v1/messages/count_tokens", json=msgs(n), headers=hdr) as r:
                    counts.append((r.status, await r.text()))
            res["W2_count_tokens"] = counts
            for mode in ("eos", "literal_no_eos"):
                MODE["next"] = mode
                async with s.post(f"{base}/v1/messages", json={**msgs(3), "stream": False}, headers={**hdr, "x-api-key": f"wiring{mode}01"}) as r:
                    res[f"W3_{mode}"] = {"status": r.status, "body": (await r.text())[:800]}
                async with s.get(f"{base}/__probe_stats") as r:
                    res[f"W3_stats_after_{mode}"] = await r.json()
            async with s.post(f"{base}/v1/messages", json={**msgs(ns.window * 2), "stream": False}, headers={**hdr, "x-api-key": "wiringovf01"}) as r:
                res["W4_overflow"] = {"status": r.status, "body": (await r.text())[:600]}
    finally:
        proc.terminate(); proc.wait(timeout=20); await runner.cleanup()
    (out / "wiring_check.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str))
    print(json.dumps(res, ensure_ascii=False, indent=1, default=str)[:6000])

asyncio.run(main())
