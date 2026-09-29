"""E3 实施复核：隔离旧新源码差分，分离计时与内存跟踪，核实路由值分布的影响。

运行于 rh2 venv；只向本目录写审查证据，不修改作者脚本、生产代码或维护测试。
较小的四案仅用于区分 tracemalloc 与随机 int32 的影响；代表规模的计时关闭跟踪。
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tarfile
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "rh2" / "pyproject.toml").is_file())
EXPERIMENT = ROOT / "rh2/experiments/batch6_e3_20260922"
REVISIONS = {"old": "110bbd91", "e3": "45c67de3", "e3b": "d4a11940"}


def child(args):
    spec = importlib.util.spec_from_file_location("author_bench", EXPERIMENT / "lifecycle_bench.py")
    bench = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bench)

    if args.distribution == "experts128":
        # 索引数值取 0..127；每个 token/layer 的 8 个值均不同。表示成本不依赖真实路由频率。
        def make_response(rid, prompt_len, gen, layers, topk, rnd):
            rows = prompt_len - 1 + len(gen)
            count = rows * layers * topk
            values = struct.pack("<128i", *[(i * 13 + 7) % 128 for i in range(128)])
            payload = values * (count // 128) + values[: (count % 128) * 4]
            return {"text": "x", "meta_info": {
                "id": rid, "weight_version": "1", "finish_reason": {"type": "stop"},
                "output_token_logprobs": [[-0.1, t, None] for t in gen],
                "routed_experts": bench.base64.b64encode(payload).decode("ascii"),
            }}

        bench.make_response = make_response

    if not args.trace:
        bench.tracemalloc = bench.SimpleNamespace(
            start=lambda: None, stop=lambda: None, get_traced_memory=lambda: (0, 0),
        )

    class SettledHeartbeat(bench.Heartbeat):
        async def measure(self, fn):
            # 先让合成 response 的同步构造所造成的延迟结算，不算进被测生产函数。
            await asyncio.sleep(self.interval * 2)
            return await super().measure(fn)

    bench.Heartbeat = SettledHeartbeat
    result = asyncio.run(bench.run(args))
    result["distribution"] = args.distribution
    result["tracemalloc_enabled"] = args.trace
    result["heartbeat_note"] = "fixture 构造后先结算两个心跳周期；计时仍只包生产入口"
    if not args.trace:
        for key in ("phase_a_capture", "phase_b_leaves"):
            for metric in ("tracemalloc_current_mib", "tracemalloc_peak_mib"):
                result[key][metric] = None
    print(json.dumps(result, ensure_ascii=False, indent=2))


def run_one(command, env, filename):
    result = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True, check=True)
    (HERE / filename).write_text(result.stdout)
    if result.stderr:
        (HERE / filename.replace(".json", ".stderr.txt")).write_text(result.stderr)
    value = json.loads(result.stdout)
    print(filename, flush=True)
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--trace", action="store_true")
    parser.add_argument("--distribution", choices=["random32", "experts128"], default="experts128")
    parser.add_argument("--turns", type=int, default=8)
    parser.add_argument("--rows-max", type=int, default=8192)
    parser.add_argument("--leaves", type=int, default=2)
    parser.add_argument("--layers", type=int, default=48)
    parser.add_argument("--topk", type=int, default=8)
    parser.add_argument("--heartbeat-ms", type=float, default=10.0)
    args = parser.parse_args()
    if args.child:
        child(args)
        return

    summary = {"revisions": REVISIONS, "script_sha256": {}, "differential": {}, "measurements": {}}
    for name in ("differential_probe.py", "lifecycle_bench.py"):
        summary["script_sha256"][name] = hashlib.sha256((EXPERIMENT / name).read_bytes()).hexdigest()

    with tempfile.TemporaryDirectory(prefix="rh2-e3-review-") as temporary:
        trees = {}
        for name, revision in REVISIONS.items():
            tree = Path(temporary) / name
            tree.mkdir()
            archive = Path(temporary) / (name + ".tar")
            subprocess.run(["git", "archive", "--format=tar", "--output", str(archive), revision, "rh2/src"],
                           cwd=ROOT, check=True)
            with tarfile.open(archive) as stream:
                stream.extractall(tree, filter="data")
            trees[name] = tree

        def environment(name):
            env = dict(os.environ)
            env["PYTHONPATH"] = str(trees[name] / "rh2/src")
            env["RH2_MILES_PATH"] = str(ROOT / "reference/miles-rh2-integration")
            return env

        diffs = {}
        for name in REVISIONS:
            data = run_one([sys.executable, str(EXPERIMENT / "differential_probe.py")],
                           environment(name), f"differential_{name}.json")
            data.pop("tree")
            diffs[name] = data
        assert diffs["old"] == diffs["e3"] == diffs["e3b"]
        assert all(isinstance(v, dict) for v in diffs["old"]["canonicalize"].values())
        summary["differential"] = {"all_equal_except_tree": True, "canonicalize_ran": True}

        # 一个小型 2×2 对照，四个独立进程：跟踪开关 × 路由取值。
        cases = [("old", dist, trace, 8, 8192)
                 for dist in ("random32", "experts128") for trace in (False, True)]
        # 代表规模只计时，不让 tracemalloc 的额外成本进入结果；三个版本均保留全部轮次和两叶。
        cases += [(name, "experts128", False, 25, 32768) for name in REVISIONS]
        # 同规模内存单独跑；这些运行的时间不能代替上面的时间。
        cases += [(name, "experts128", True, 25, 32768) for name in ("old", "e3b")]
        for name, dist, trace, turns, rows in cases:
            key = f"{name}_{dist}_{'traced' if trace else 'untraced'}_{turns}x{rows}"
            command = [sys.executable, str(Path(__file__).resolve()), "--child", "--distribution", dist,
                       "--turns", str(turns), "--rows-max", str(rows)]
            if trace:
                command.append("--trace")
            data = run_one(command, environment(name), f"measurement_{key}.json")
            capture, leaves = data["phase_a_capture"], data["phase_b_leaves"]
            summary["measurements"][key] = {
                "capture_ms": capture["total_ms"],
                "last_turn_ms": capture["per_turn"][-1]["ms"],
                "capture_heartbeat_ms": capture["heartbeat_max_delay_ms"],
                "capture_traced_current_mib": capture["tracemalloc_current_mib"],
                "capture_traced_peak_mib": capture["tracemalloc_peak_mib"],
                "maxrss_mib": leaves["maxrss_mib"],
                "backfill_ms": [v["backfill_ms"] for v in leaves["per_leaf"]],
                "projection_ms": [v["projection_ms"] for v in leaves["per_leaf"]],
            }
            (HERE / "probe_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
        print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
