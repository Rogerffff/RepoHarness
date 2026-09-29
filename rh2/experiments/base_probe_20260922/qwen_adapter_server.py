#!/usr/bin/env python3
"""基座探针：把项目自带的 slime Anthropic adapter 单独立起来（→ 本机 SGLang `/generate`）。

用它而不用推理框架自带的 Anthropic/OpenAI 兼容端点，是为了让探针里 Qwen 的 chat template 渲染与工具调用解析
走训练链同一份代码（`slime/agent/adapters/anthropic.py` + `slime/agent/parsing.py` → SGLang 的
FunctionCallParser / ReasoningParser）。

09-25 接线（A→B 交接 b_wiring_handoff_20260924 §2）：按 `bringup.py` 生产构造点的同一顺序装配 RH2 包装——
count_tokens 路由（#8 真实计数）→ parse wire（#5 EOS 字面量按采样事实剥、悬空 <tool_call> 置 ill_formed）
→ 探针专用的 turn 终局事实发布器（生产由 capture wire 发布）→ RH2 子类（#6(a) 提醒并入 tool_result）
→ count_tokens 绑定到本实例。实际装上哪些写进 adapter_config.json 的 `rh2_wrappers`。
**与正式链的差异**：没有 capture / turn 预算闸门 / 会话治理 / 训练行归属；溢出 400 在 capture wire 里，
09-25 起用 A 线抽出的 `prompt_overflow.install_overflow_400_wire()`（交接 §2 第 2c 行）补上。
会话按首次请求自动建立，采样缺省值与上下文上限由本脚本统一给定并落盘。

本进程需要能 import `sglang`（解析器）与 `transformers`（tokenizer）：在 SGLang 的运行环境里启动它。
探针网关（model_gateway.py，auth_style=passthrough）放在它前面做留证与请求上限。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

RH2_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RH2_ROOT / "src"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sglang-url", required=True)
    ap.add_argument("--tokenizer", required=True, help="HF 模型目录 / 名称（与 SGLang 加载的同一份）")
    ap.add_argument("--tool-parser", required=True, help="SGLang FunctionCallParser 名称（按所装 SGLang 版本核对）")
    ap.add_argument("--reasoning-parser", default=None)
    ap.add_argument("--sampling-defaults", default="{}", help='JSON，例如 {"temperature":0.7,"top_p":0.8,"top_k":20,"max_new_tokens":8192}')
    ap.add_argument("--max-context-tokens", type=int, required=True)
    ap.add_argument("--fork-threshold-tokens", type=int, default=0, help="与 bringup.FORK_THRESHOLD_TOKENS 一致（I01 B 路线）")
    ap.add_argument("--listen-host", default="127.0.0.1")
    ap.add_argument("--listen-port", type=int, required=True)
    ap.add_argument("--log-dir", required=True)
    ap.add_argument("--idle-drop-seconds", type=int, default=2400)
    ns = ap.parse_args(argv)

    from aiohttp import web
    from transformers import AutoTokenizer

    from slime.agent.adapters.common import Session

    from repoharness2.adapters.slime.count_tokens_wire import bind_count_tokens_adapter, install_count_tokens_wire
    from repoharness2.adapters.slime.parse_wire import (
        assert_parse_wire_installed, install_parse_wire, install_turn_terminal_publisher, parse_wire_stats,
    )
    from repoharness2.adapters.slime.prompt_overflow import install_overflow_400_wire, overflow_400_wire_installed
    from repoharness2.adapters.slime.rh2_anthropic_adapter import rh2_anthropic_adapter_cls

    log_dir = Path(ns.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    tokenizer = AutoTokenizer.from_pretrained(ns.tokenizer, trust_remote_code=True)
    defaults = json.loads(ns.sampling_defaults)
    last_seen: dict[str, float] = {}

    def debug_callback(sid, translated, tools_schema, manager_message, turn) -> None:
        last_seen[sid] = time.time()
        try:
            raw_text = tokenizer.decode(turn.output_ids, skip_special_tokens=False)
        except Exception as exc:  # noqa: BLE001
            raw_text = f"<decode failed: {exc}>"
        row = {"ts": time.time(), "sid": sid, "prompt_tokens": len(turn.prompt_ids), "output_tokens": len(turn.output_ids),
               "finish_reason": getattr(turn, "finish_reason", None), "n_messages": len(translated),
               "n_tools": len(tools_schema or []), "raw_output": raw_text, "parsed": manager_message}
        with open(log_dir / f"{sid}.turns.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")

    # 顺序同 bringup.py 生产构造点：路由在 vendored 构造器里登记，所以包装必须先装、后构造
    install_count_tokens_wire()                                            # 1) #8 count_tokens 路由
    install_parse_wire(eos_token=getattr(tokenizer, "eos_token", None),    # 2) #5 按采样事实剥 EOS 字面量
                       eos_token_id=getattr(tokenizer, "eos_token_id", None))
    install_turn_terminal_publisher()                                      # 2b) 探针没有 capture wire：自己发布 EOS 事实
    install_overflow_400_wire()                                            # 2c) 溢出时回 Anthropic 形状的 400（与 capture wire 同一构造）
    assert_parse_wire_installed()
    adapter = rh2_anthropic_adapter_cls()(tokenizer=tokenizer, sglang_url=ns.sglang_url, tool_parser=ns.tool_parser or None,  # 3) #6(a)
                                          reasoning_parser=ns.reasoning_parser or None, fork_threshold_tokens=ns.fork_threshold_tokens,
                                          debug_callback=debug_callback)
    bind_count_tokens_adapter(adapter)                                     # 4) count_tokens 绑到本实例

    class _Store(dict):  # 首次请求自动建会话时带上统一的采样缺省值与上下文上限
        def setdefault(self, key, default=None):  # noqa: ARG002
            if key not in self:
                self[key] = Session(sampling_defaults=dict(defaults), max_context_tokens=int(ns.max_context_tokens))
                last_seen[key] = time.time()
            return self[key]

    adapter.store = _Store()

    async def reaper(_app):
        async def loop():
            while True:
                await asyncio.sleep(120)
                now = time.time()
                for sid, seen in list(last_seen.items()):
                    if now - seen > ns.idle_drop_seconds:
                        last_seen.pop(sid, None)
                        try:
                            await adapter.drop_session(sid)
                        except Exception as exc:  # noqa: BLE001
                            print(f"[qwen_adapter] drop_session({sid}) failed: {exc}", flush=True)
        task = asyncio.create_task(loop())
        yield
        task.cancel()

    async def probe_stats(_request):  # 运行中回读 #5 计数（eos_fact_missing / 剥离 / 悬空）
        return web.json_response({"parse_wire_stats": parse_wire_stats(), "sessions": len(adapter.store)})

    adapter.app.router.add_get("/__probe_stats", probe_stats)
    adapter.app.cleanup_ctx.append(reaper)
    (log_dir / "adapter_config.json").write_text(json.dumps({
        "sglang_url": ns.sglang_url, "tokenizer": ns.tokenizer, "tool_parser": ns.tool_parser,
        "reasoning_parser": ns.reasoning_parser, "sampling_defaults": defaults,
        "max_context_tokens": ns.max_context_tokens, "fork_threshold_tokens": ns.fork_threshold_tokens,
        "adapter_class": f"{type(adapter).__module__}.{type(adapter).__qualname__}",
        "rh2_wrappers": {"count_tokens": True, "parse_wire": True, "turn_terminal_publisher": True,
                         "rh2_subclass": True, "overflow_400": overflow_400_wire_installed()},
        "parse_wire_stats_at_start": parse_wire_stats(),
        "started_at": time.time(),
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"qwen_adapter": "starting", "listen": f"{ns.listen_host}:{ns.listen_port}"}), flush=True)
    web.run_app(adapter.app, host=ns.listen_host, port=ns.listen_port, print=None, access_log=None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
