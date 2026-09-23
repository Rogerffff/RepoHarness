"""E3 单轮微基准（只调用生产入口，旧新树都能跑）：一轮 /generate 响应在 adapter 内的同步处理成本。

    PYTHONPATH=<tree>/rh2/src .venv/bin/python baseline_bench.py

分项：json.loads（响应体）、hook.on_generate_response（逐轮）、canonical_json_digest（逐轮的 meta 摘要，
E3b 对象）、backfill_leaf_sample（每叶张量化）、_build_routing（每叶投影）。ru_maxrss 是整个基准进程的
累计峰值，不是生产单轮内存的归因证据。
"""

from __future__ import annotations

import base64
import gc
import json
import os
import random
import resource
import sys
import time
from types import SimpleNamespace

from repoharness2.adapters.slime import generate as G
from repoharness2.adapters.slime import projection as P
from repoharness2.contracts._base import canonical_json_digest

LAYERS, TOPK = 48, 8
GEN = 256
SP = {"temperature": 1.0, "top_p": 1.0, "max_new_tokens": 4096, "return_top_p_token_ids": False,
      "return_routed_experts": True}


def make_response(rows: int, gen_ids: list[int], rnd: random.Random):
    payload = rnd.randbytes(rows * LAYERS * TOPK * 4)
    meta = {"id": f"rid-{rows}", "weight_version": "1", "finish_reason": {"type": "stop"},
            "output_token_logprobs": [[-0.1, t, None] for t in gen_ids],
            "routed_experts": base64.b64encode(payload).decode("ascii")}
    return {"text": "x", "meta_info": meta}


def timed(fn):
    started = time.perf_counter()
    out = fn()
    return out, (time.perf_counter() - started) * 1e3


def run_rows(rows: int, rnd: random.Random) -> str:
    prompt_ids = list(range(rows + 1 - GEN))
    gen_ids = list(range(10_000, 10_000 + GEN))
    resp = make_response(rows, gen_ids, rnd)
    body = json.dumps(resp)
    _, t_json = timed(lambda: json.loads(body))
    hook = G.GenerationCaptureHook(trajectory_id="bench", model_name="m", backend_name="sglang", backend_version="v",
                                   renderer_cls_name="r", tokenizer_name="t", template_hash="sha256:" + "0" * 64)
    gc.collect()
    _, t_hook = timed(lambda: hook.on_generate_response(prompt_token_ids=prompt_ids, sampling_params=SP, response=resp))
    _, t_digest = timed(lambda: canonical_json_digest(dict(resp["meta_info"])))
    leaf = SimpleNamespace(tokens=prompt_ids + gen_ids, loss_mask=[1] * GEN, response_length=GEN,
                           rollout_log_probs=[-0.1] * GEN, metadata={}, weight_versions=[],
                           rollout_top_p_token_ids=None, rollout_top_p_token_offsets=None, rollout_routed_experts=None)
    _, t_backfill = timed(lambda: G.backfill_leaf_sample(leaf, hook.tapes, moe_num_layers=LAYERS, moe_router_topk=TOPK))
    store: dict = {}
    ref, t_proj = timed(lambda: P._build_routing(
        SimpleNamespace(rollout_routed_experts=leaf.rollout_routed_experts), branch_id="b0", trajectory_id="bench",
        prompt_len=len(prompt_ids), response_len=GEN, engine_name="sglang", tape_requested=True,
        moe_num_layers=LAYERS, moe_router_topk=TOPK, store=store))
    assert ref.tensor_ref.sha256 == hook.records[-1].routed_experts_ref.sha256  # 逐轮工件与分支工件同一字节
    return (f"rows={rows:6d} raw={rows * LAYERS * TOPK * 4 / 2**20:6.1f}MiB | json.loads {t_json:7.1f} ms | "
            f"hook.on_generate_response {t_hook:8.1f} ms (其中 meta digest 约 {t_digest:6.1f}) | "
            f"backfill {t_backfill:8.1f} ms | projection {t_proj:8.1f} ms")


def main() -> None:
    rnd = random.Random(20260922)
    print(f"python {sys.version.split()[0]}  pid {os.getpid()}  tree {os.environ.get('PYTHONPATH', '')}")
    for rows in (8192, 16384, 32768):
        print(run_rows(rows, rnd))
        gc.collect()
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print("ru_maxrss MiB:", round(rss / 2**20 if sys.platform == "darwin" else rss / 2**10, 1), "(整个基准进程的累计峰值)")


main()
