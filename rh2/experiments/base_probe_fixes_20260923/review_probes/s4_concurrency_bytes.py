"""场景 4：并发与字节精确。

6 个并发 run_exec_collected（2 个容器 × 3 个 exec，同一事件循环），各自由容器内生成器输出不同的
3 MiB stdout + 3 MiB stderr：随机大小写入交错两路，内容含 >64 KiB 的单行、0x00–0xff 全字节、随机二进制。
生成器在容器内边写边算 sha256，写到 /tmp/ir1gen_<seed>.json（不经过被测流）；宿主文件 sha256 与之逐一核对，
同时核对字节数、退出码（seed 决定，防串扰）、exec_state/log_complete。跑 3 轮不同种子。
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (FrameStats, TMP, collect, env_facts, new_container, rm_container, sh, sha256_file,  # noqa: E402
                     write_result)

GEN = r'''
import hashlib, json, os, random, sys
import time
seed, n_out, n_err = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
pace = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0
rng = random.Random(seed)
left = {1: n_out, 2: n_err}
h = {1: hashlib.sha256(), 2: hashlib.sha256()}
longest = {1: 0, 2: 0}
def chunk(n):
    kind = rng.choice(["bin", "all256", "longline", "json"])
    if kind == "bin":
        return rng.randbytes(n)
    if kind == "all256":
        return (bytes(range(256)) * (n // 256 + 1))[:n]
    if kind == "longline":
        body = bytes(rng.choice(b"abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(min(n, 4096)))
        body = (body * (n // max(len(body), 1) + 1))[: max(n - 1, 0)]
        return body + b"\n"
    lines = b"".join(b'{"seed":%d,"i":%d}\n' % (seed, rng.randrange(1 << 30)) for _ in range(n // 20 + 1))
    return lines[:n]
writes = 0
while left[1] or left[2]:
    fd = 1 if rng.random() < left[1] / (left[1] + left[2]) else 2
    size = min(left[fd], rng.choice([1, 7, 255, 4096, 65535, 65537, 70000, 131072, 200000, rng.randrange(1, 300000)]))
    data = chunk(size)
    view = memoryview(data)
    while len(view):
        k = os.write(fd, view)
        view = view[k:]
    h[fd].update(data)
    left[fd] -= len(data)
    writes += 1
    if pace:
        time.sleep(pace)
    # 最长无换行段（证明含 >64 KiB 单行）
    seg = max((len(s) for s in data.split(b"\n")), default=0)
    longest[fd] = max(longest[fd], seg)
json.dump({"seed": seed, "out_sha256": h[1].hexdigest(), "err_sha256": h[2].hexdigest(), "n_out": n_out,
           "n_err": n_err, "writes": writes, "longest_segment": longest}, open("/tmp/ir1gen_%d.json" % seed, "w"))
sys.exit(seed % 50 + 3)
'''

RUN = uuid.uuid4().hex[:6]
N_OUT = 3 * 1024 * 1024
N_ERR = 3 * 1024 * 1024


async def timed(coro):
    t0 = time.time()
    rec = await coro
    rec["t_start"], rec["t_end"] = round(t0, 3), round(time.time(), 3)
    return rec


async def one_round(round_no: int, containers: list[str], pace: float = 0.0) -> dict:
    seeds = [1000 * (round_no + 1) + i for i in range(6)]
    jobs = []
    for i, seed in enumerate(seeds):
        c = containers[i % len(containers)]
        outdir = TMP / f"s4_{RUN}_r{round_no}_{seed}"  # 每次运行唯一：收集器以追加模式打开宿主文件
        cmd = f"exec /opt/miniconda3/bin/python /tmp/ir1gen.py {seed} {N_OUT} {N_ERR} {pace}"
        jobs.append((seed, c, outdir, timed(collect(c, outdir, cmd, user="nobody", deadline=300, progress={}))))
    stats = FrameStats().install()
    try:
        results = await asyncio.gather(*(j[3] for j in jobs))
    finally:
        stats.uninstall()
    checks = []
    for (seed, c, outdir, _), rec in zip(jobs, results):
        gen = json.loads(sh("docker", "exec", c, "cat", f"/tmp/ir1gen_{seed}.json").stdout or "{}")
        res = rec.get("result") or {}
        host_out, host_err = sha256_file(outdir / "out"), sha256_file(outdir / "err")
        ok = (res.get("exec_state") == "exited" and res.get("exit_code") == seed % 50 + 3 and res.get("log_complete") is True
              and host_out == gen.get("out_sha256") and host_err == gen.get("err_sha256")
              and res.get("stdout_bytes") == N_OUT == (outdir / "out").stat().st_size
              and res.get("stderr_bytes") == N_ERR == (outdir / "err").stat().st_size)
        checks.append({"seed": seed, "container": c, "ok": ok, "exec_state": res.get("exec_state"),
                       "exit_code": res.get("exit_code"), "expected_exit": seed % 50 + 3,
                       "log_complete": res.get("log_complete"), "stdout_bytes": res.get("stdout_bytes"),
                       "stderr_bytes": res.get("stderr_bytes"), "host_out_sha256": host_out, "gen_out_sha256": gen.get("out_sha256"),
                       "host_err_sha256": host_err, "gen_err_sha256": gen.get("err_sha256"), "gen_writes": gen.get("writes"),
                       "gen_longest_segment": gen.get("longest_segment"), "wall": rec.get("wall"), "raised": rec.get("raised"),
                       "stderr_tail_len": len(res.get("stderr_tail") or ""), "t_start": rec.get("t_start"),
                       "t_end": rec.get("t_end")})
    overlap = min(c["t_end"] for c in checks) - max(c["t_start"] for c in checks)
    return {"round": round_no, "pace": pace, "all_ok": all(c["ok"] for c in checks), "all_six_overlap_s": round(overlap, 3),
            "checks": checks, "frame_stats": stats.summary()}


async def main() -> None:
    containers = [new_container("s4a"), new_container("s4b")]
    try:
        for c in containers:
            sh("docker", "exec", "-i", c, "bash", "-c", "cat > /tmp/ir1gen.py", input=GEN, check=True)
        rounds = [await one_round(r, containers) for r in range(3)]
        rounds.append(await one_round(3, containers, pace=0.01))  # 每次写后停 10 ms：6 路在时间上确实重叠
    finally:
        for c in containers:
            rm_container(c)
    write_result("s4_concurrency_bytes", {"env": env_facts(), "n_out": N_OUT, "n_err": N_ERR,
                                          "all_ok": all(r["all_ok"] for r in rounds), "rounds": rounds})


if __name__ == "__main__":
    asyncio.run(main())
