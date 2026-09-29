"""场景 6 补充：客户端先断开后，dockerd 一侧的 hijack 连接何时释放（残留连接的来源）。

用被测收集器的 time_budget 路径（deadline 1 s，收集器关闭自己的连接、exec 仍在跑），在关闭前从本进程的
docker.sock 连接取到 dockerd 一侧的对端 inode，然后按三种收尾方式各做 5 次：
  A barrier：容器内 kill -9 该 exec 进程（等价既有屏障先杀进程）→ 2 s 后 rm -f 容器
  B rm：不杀进程，直接 rm -f 容器（exec 仍在跑时容器被删）
  C natural：exec 自己在 3 s 后自然退出 → 再 rm -f
每步后核对该 inode 是否仍被 dockerd 持有，并记录 `docker info` 的 NGoroutines 前后值。
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import TMP, env_facts, new_container, rm_container, sh, write_result, ds  # noqa: E402

REPS = 5


def my_docker_peer_inodes() -> set[str]:
    """本进程到 docker.sock 的连接在 dockerd 一侧的 inode（排除事件循环自身的 socketpair）。"""
    rows = [line.split() for line in sh("ss", "-xpH").stdout.splitlines() if f"pid={os.getpid()}," in line]
    mine = {f[5] for f in rows}
    return {f[7] for f in rows if f[7] not in mine and f[7] != "0"}


def dockerd_holds(inode: str) -> bool:
    return any(len(line.split()) > 5 and line.split()[5] == inode and '"dockerd"' in line
               for line in sh("ss", "-xpH").stdout.splitlines())


def goroutines() -> int:
    return int(sh("docker", "info", "--format", "{{.NGoroutines}}").stdout.strip() or -1)


async def one(mode: str, rep: int) -> dict:
    name = new_container(f"s6b{mode}")
    rec: dict = {"mode": mode, "rep": rep, "goroutines_before": goroutines()}
    captured: set[str] = set()
    orig_pump_timeout = None

    # 在 time_budget 关闭连接之前拿到 dockerd 一侧 inode：包装 _FrameSource.next_frame，首帧后记一次
    orig = ds._FrameSource.next_frame

    async def next_frame(src):
        fr = await orig(src)
        if fr is not None and not captured:
            captured.update(my_docker_peer_inodes())
        return fr

    ds._FrameSource.next_frame = next_frame
    try:
        cmd = "echo go; exec sleep 3" if mode == "natural" else "echo go; exec sleep 300"
        run = await ds.run_exec_collected(
            container_name=name, user="root", workdir="/tmp", env={"HOME": "/tmp"}, cmd=cmd,
            stdout_path=TMP / f"s6b_{mode}_{rep}_{name}" / "out", stderr_path=TMP / f"s6b_{mode}_{rep}_{name}" / "err",
            deadline_seconds=1.0,
        )
    finally:
        ds._FrameSource.next_frame = orig
    rec["collector"] = {"exec_state": run.exec_state, "exit_code": run.exit_code, "inspect": run.inspect}
    rec["peer_inodes"] = sorted(captured)
    await asyncio.sleep(0.5)
    rec["held_after_client_close"] = {i: dockerd_holds(i) for i in captured}
    if mode == "barrier":
        sh("docker", "exec", name, "bash", "-c",
           "for p in /proc/[0-9]*; do tr '\\0' ' ' < $p/cmdline 2>/dev/null | grep -q '^sleep 300' && kill -9 ${p#/proc/}; done; true")
        await asyncio.sleep(2.0)
        rec["held_after_process_killed"] = {i: dockerd_holds(i) for i in captured}
    elif mode == "natural":
        await asyncio.sleep(3.5)
        rec["held_after_natural_exit"] = {i: dockerd_holds(i) for i in captured}
    rm_container(name)
    await asyncio.sleep(2.0)
    rec["held_after_rm"] = {i: dockerd_holds(i) for i in captured}
    rec["goroutines_after"] = goroutines()
    return rec


async def main() -> None:
    t0 = time.time()
    g0 = goroutines()
    rows = []
    for mode in ("barrier", "rm", "natural"):
        for rep in range(REPS):
            rows.append(await one(mode, rep))
    summary = {}
    for mode in ("barrier", "rm", "natural"):
        rs = [r for r in rows if r["mode"] == mode]
        summary[mode] = {"leaked_after_rm": sum(any(r["held_after_rm"].values()) for r in rs), "reps": len(rs)}
    write_result("s6b_dockerd_residual", {"env": env_facts(), "goroutines_start": g0, "goroutines_end": goroutines(),
                                         "seconds": round(time.time() - t0, 1), "summary": summary, "rows": rows})


if __name__ == "__main__":
    asyncio.run(main())
