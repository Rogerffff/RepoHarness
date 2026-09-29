"""E3 生命周期基准：一段 session 逐轮增长到 rows_max 的 N 轮捕获 + M 叶 backfill / 投影。

分项计时与心跳延迟、内存跟踪**分成不同运行**（Codex E3 实施复核 EP1）：默认关闭 tracemalloc 只计时；
`--trace-memory` 只报内存、时间列不可比。专家编号默认 0..127（目标模型 Qwen3-30B-A3B 为 128 专家）；
`--stress-random-int32` 才用整个 int32 值域，只作字节等价压力条件，不代表该模型的路由内存。
心跳：先让夹具准备阶段的延迟结算（等两个心跳周期）再清零、调同步函数、再等心跳醒来记录。
只调用生产入口，不碰 TurnTape 内部字段。用法（旧新树各自独立进程）：

    PYTHONPATH=<tree>/rh2/src .venv/bin/python lifecycle_bench.py --turns 25 --rows-max 32768 --leaves 2
    PYTHONPATH=<tree>/rh2/src .venv/bin/python lifecycle_bench.py --turns 25 --rows-max 32768 --leaves 2 --trace-memory
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import platform
import resource
import sys
import time
import tracemalloc
from types import SimpleNamespace

from repoharness2.adapters.slime import generate as G
from repoharness2.adapters.slime import projection as P

SP = {"temperature": 1.0, "top_p": 1.0, "max_new_tokens": 4096, "return_top_p_token_ids": False,
      "return_routed_experts": True}


def maxrss_mib() -> float:
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return round(rss / 2**20 if sys.platform == "darwin" else rss / 2**10, 1)  # darwin: bytes；linux: KiB


class Heartbeat:
    def __init__(self, interval: float) -> None:
        self.interval, self.max_delay, self._stop = interval, 0.0, False

    async def _run(self) -> None:
        loop = asyncio.get_running_loop()
        while not self._stop:
            expected = loop.time() + self.interval
            await asyncio.sleep(self.interval)
            self.max_delay = max(self.max_delay, loop.time() - expected)

    def start(self) -> None:
        self._task = asyncio.create_task(self._run())

    async def measure(self, fn):
        """先让之前（夹具准备）的心跳延迟结算 -> 清零 -> 同步调用 -> 让心跳醒来记录；返回 (结果, 秒, 本次最大心跳延迟秒)。"""
        await asyncio.sleep(self.interval * 2)
        self.max_delay = 0.0
        started = time.perf_counter()
        result = fn()
        elapsed = time.perf_counter() - started
        await asyncio.sleep(self.interval * 2)
        return result, elapsed, self.max_delay

    async def stop(self) -> None:
        self._stop = True
        self._task.cancel()
        try:
            await self._task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            pass


def routing_payload(rows: int, layers: int, topk: int, seed: int, *, num_experts: int | None) -> bytes:
    """num_experts=None：整个 int32 值域（压力条件）；否则编号 0..num_experts-1（目标模型形态）。"""
    import numpy

    rng = numpy.random.default_rng(seed)
    n = rows * layers * topk
    if num_experts is None:
        return rng.integers(-(2**31), 2**31, size=n, dtype=numpy.int64).astype("<i4").tobytes()
    return rng.integers(0, num_experts, size=n, dtype="<i4").tobytes()


def make_response(rid: str, prompt_len: int, gen: list[int], layers: int, topk: int, seed: int, num_experts: int | None):
    rows = prompt_len - 1 + len(gen)
    payload = routing_payload(rows, layers, topk, seed, num_experts=num_experts)
    return {"text": "x", "meta_info": {"id": rid, "weight_version": "1", "finish_reason": {"type": "stop"},
            "output_token_logprobs": [[-0.1, t, None] for t in gen],
            "routed_experts": base64.b64encode(payload).decode("ascii")}}


async def run(args) -> dict:
    hook = G.GenerationCaptureHook(trajectory_id="bench", model_name="m", backend_name="sglang", backend_version="v",
                                   renderer_cls_name="r", tokenizer_name="t", template_hash="sha256:" + "0" * 64)
    num_experts = None if args.stress_random_int32 else args.num_experts
    out = {"platform": platform.platform(), "python": sys.version.split()[0], "tree": os.environ.get("PYTHONPATH", ""),
           "turns": args.turns, "rows_max": args.rows_max, "leaves": args.leaves, "layers": args.layers, "topk": args.topk,
           "expert_ids": "random_int32_stress" if num_experts is None else f"0..{num_experts - 1}",
           "mode": "memory_only(tracemalloc on; timings not comparable)" if args.trace_memory else "timing(tracemalloc off)"}
    try:
        import torch

        out["torch"] = torch.__version__
    except Exception:  # noqa: BLE001
        out["torch"] = None
    if args.trace_memory:
        tracemalloc.start()
    hb = Heartbeat(args.heartbeat_ms / 1000)
    hb.start()

    def mem() -> dict:
        if not args.trace_memory:
            return {"maxrss_mib": maxrss_mib()}
        current, peak = tracemalloc.get_traced_memory()
        return {"tracemalloc_current_mib": round(current / 2**20, 1), "tracemalloc_peak_mib": round(peak / 2**20, 1),
                "maxrss_mib": maxrss_mib()}

    # A：逐轮捕获（adapter 循环上的同步成本）。每轮 prompt 增长到 rows_max；response 在 commit 后即丢弃（同生产）。
    gen_len = 256
    per_turn = []
    prompt_ids: list[int] = []
    for i in range(args.turns):
        target_rows = max(gen_len + 1, args.rows_max * (i + 1) // args.turns)
        prompt_ids = list(range(target_rows + 1 - gen_len))
        gen = list(range(10_000, 10_000 + gen_len))
        resp = make_response(f"rid{i}", len(prompt_ids), gen, args.layers, args.topk, 20260922 + i, num_experts)
        _, secs, delay = await hb.measure(lambda: hook.on_generate_response(prompt_token_ids=prompt_ids, sampling_params=SP, response=resp))
        per_turn.append({"rows": len(prompt_ids) - 1 + gen_len, "ms": round(secs * 1e3, 1), "heartbeat_max_delay_ms": round(delay * 1e3, 1)})
        resp = None  # commit 之后响应即丢弃（同生产 PendingTurn 生命周期）
    out["phase_a_capture"] = {"per_turn": per_turn, "total_ms": round(sum(t["ms"] for t in per_turn), 1),
                              "heartbeat_max_delay_ms": max(t["heartbeat_max_delay_ms"] for t in per_turn), **mem()}

    # B：每叶 backfill + 分支投影（owner 循环上的同步成本）；叶与最后一轮对齐、不裁剪。
    tokens = prompt_ids + list(range(10_000, 10_000 + gen_len))
    leaves = []
    kept = []
    for j in range(args.leaves):
        s = SimpleNamespace(tokens=list(tokens), loss_mask=[1] * gen_len, response_length=gen_len,
                            rollout_log_probs=[-0.1] * gen_len, metadata={}, weight_versions=[],
                            rollout_top_p_token_ids=None, rollout_top_p_token_offsets=None, rollout_routed_experts=None)
        _, bf_secs, bf_delay = await hb.measure(lambda: G.backfill_leaf_sample(s, hook.tapes, moe_num_layers=args.layers, moe_router_topk=args.topk))
        store: dict = {}
        _, pj_secs, pj_delay = await hb.measure(lambda: P._build_routing(
            SimpleNamespace(rollout_routed_experts=s.rollout_routed_experts), branch_id=f"b{j}", trajectory_id="bench",
            prompt_len=len(prompt_ids), response_len=gen_len, engine_name="sglang", tape_requested=True,
            moe_num_layers=args.layers, moe_router_topk=args.topk, store=store))
        kept.append((s, store))  # 与生产一致：投影期间叶张量与分支工件同时存活
        leaves.append({"backfill_ms": round(bf_secs * 1e3, 1), "backfill_heartbeat_max_delay_ms": round(bf_delay * 1e3, 1),
                       "projection_ms": round(pj_secs * 1e3, 1), "projection_heartbeat_max_delay_ms": round(pj_delay * 1e3, 1)})
    out["phase_b_leaves"] = {"per_leaf": leaves, **mem()}
    await hb.stop()
    if args.trace_memory:
        tracemalloc.stop()
    out["note"] = ("时间与内存分开运行：--trace-memory 只看 tracemalloc（只计 Python 分配器可见内存，torch 张量存储不在其中），"
                   "其时间列不可比；maxrss 是整个进程累计峰值。保留对象与一个 session 的生产保留一致；不外推到多并发。")
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--turns", type=int, default=25)
    parser.add_argument("--rows-max", type=int, default=32768)
    parser.add_argument("--leaves", type=int, default=2)
    parser.add_argument("--layers", type=int, default=48)
    parser.add_argument("--topk", type=int, default=8)
    parser.add_argument("--num-experts", type=int, default=128, help="专家编号范围 0..N-1（Qwen3-30B-A3B 为 128）")
    parser.add_argument("--stress-random-int32", action="store_true", help="整个 int32 值域：只作字节等价压力条件")
    parser.add_argument("--trace-memory", action="store_true", help="只测内存（tracemalloc 开），时间列不可比")
    parser.add_argument("--heartbeat-ms", type=float, default=10.0)
    print(json.dumps(asyncio.run(run(parser.parse_args())), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
