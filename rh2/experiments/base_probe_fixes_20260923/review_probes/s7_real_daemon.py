"""场景 7（真实 daemon 上的疑点复现）。

R1 exec 启动失败（用户不存在 / 工作目录不存在 / PATH 里找不到 bash / 容器已停止）：收集器给出什么形态？daemon 的错误
   文本落到哪一路文件？帧类型？
R2 进程先关掉 stdout/stderr 再继续跑（15 s / 5 s）：流 EOF 时 exec 仍在跑 → 多久、什么状态？
R3 后台子进程继承 stdout、主进程先退出：流何时结束？终态？后台子进程后续输出去哪了？
R4 进程退出时消费者（收集器）恰好停顿 5 s（异步停顿 / 阻塞事件循环两种）：daemon 在退出后只等流 ~2 s——尾部字节会不会
   丢，而收集器仍报 exited + log_complete=True？
R5 宿主盘真实写满（1 MiB tmpfs）：按实际写入计数、标 partial、退出码仍可信？
"""

from __future__ import annotations

import asyncio
import hashlib
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (TMP, FrameStats, collect, container_state, ds, env_facts, exec_inspect_raw, file_info,  # noqa: E402
                     new_container, procs, rm_container, sh, sha256_file, write_result)


async def r1_start_failures(c: str) -> list[dict]:
    rows = []
    cases = [
        ("user_missing", dict(user="nosuchuser"), "echo hi"),
        ("workdir_missing", dict(workdir="/nonexistent/dir"), "echo hi"),
        ("bash_not_in_path", dict(env={"PATH": "/nonexistent"}), "echo hi"),
    ]
    for tag, kw, cmd in cases:
        stats = FrameStats().install()
        try:
            rec = await collect(c, TMP / f"s7r1_{tag}_{c}", cmd, progress={}, **kw)
        finally:
            stats.uninstall()
        res = rec.get("result") or {}
        rows.append({"case": tag, "exec_state": res.get("exec_state"), "exit_code": res.get("exit_code"), "inspect": res.get("inspect"),
                     "log_complete": res.get("log_complete"), "stdout_file": file_info(TMP / f"s7r1_{tag}_{c}" / "out")["head"]
                     if (TMP / f"s7r1_{tag}_{c}" / "out").exists() else None,
                     "stderr_file": file_info(TMP / f"s7r1_{tag}_{c}" / "err").get("head"),
                     "frame_types": stats.summary()["types"], "raised": rec.get("raised")})
    # 容器已停止：exec create 应被 daemon 拒绝
    stopped = new_container("s7r1stopped")
    sh("docker", "stop", "-t", "0", stopped)
    rec = await collect(stopped, TMP / f"s7r1_stopped_{stopped}", "echo hi", progress={})
    rows.append({"case": "container_stopped", "raised": rec.get("raised"), "raised_type": rec.get("raised_type"),
                 "progress_state": (rec.get("progress") or {}).get("exec_state")})
    rm_container(stopped)
    return rows


async def r2_outputs_closed_early(c: str) -> list[dict]:
    rows = []
    for secs in (15, 5):
        rec = await collect(c, TMP / f"s7r2_{secs}_{c}", f"echo before-close; exec 1>&- 2>&-; sleep {secs}; exit 3", progress={})
        res = rec.get("result") or {}
        rows.append({"sleep_after_close": secs, "exec_state": res.get("exec_state"), "exit_code": res.get("exit_code"),
                     "inspect": res.get("inspect"), "wall": rec["wall"], "stdout": file_info(TMP / f"s7r2_{secs}_{c}" / "out")["head"],
                     "exec_inspect_after": await exec_inspect_raw(res.get("exec_id")),
                     "still_running_in_container": [p for p in procs(c).splitlines() if f"sleep {secs}" in p]})
        await asyncio.sleep(secs + 1)
    return rows


async def r3_background_child_holds_stdout(c: str) -> dict:
    cmd = "(for i in 1 2 3 4 5 6; do sleep 1; echo late-$i; done) & echo early; exit 5"
    rec = await collect(c, TMP / f"s7r3_{c}", cmd, progress={})
    res = rec.get("result") or {}
    await asyncio.sleep(7)
    return {"exec_state": res.get("exec_state"), "exit_code": res.get("exit_code"), "wall": rec["wall"],
            "log_complete": res.get("log_complete"), "stdout_file": file_info(TMP / f"s7r3_{c}" / "out")["head"],
            "stdout_bytes": res.get("stdout_bytes")}


async def r4_tail_loss_on_consumer_stall(c: str) -> list[dict]:
    n = 2 * 1024 * 1024
    sh("docker", "exec", c, "bash", "-c", f"head -c {n} /dev/urandom > /tmp/r4.bin", check=True)
    want = sh("docker", "exec", c, "sha256sum", "/tmp/r4.bin").stdout.split()[0]
    rows = []
    for mode in ("async_stall", "loop_block"):
        for remain_kib in (16, 64, 128, 256, 384, 512, 1024):
            for rep in range(3):
                threshold = n - remain_kib * 1024
                orig = ds._FrameSource.next_frame
                state = {"got": 0, "stalled": False, "stall_at": None}

                async def next_frame(src, _orig=orig, _state=state, _threshold=threshold, _mode=mode):
                    fr = await _orig(src)
                    if fr is not None and fr[0] == 1:
                        _state["got"] += len(fr[1])
                        if not _state["stalled"] and _state["got"] >= _threshold:
                            _state["stalled"], _state["stall_at"] = True, _state["got"]
                            if _mode == "async_stall":
                                await asyncio.sleep(5.0)
                            else:
                                time.sleep(5.0)  # 模拟编排事件循环被同步工作占住
                    return fr

                ds._FrameSource.next_frame = next_frame
                outdir = TMP / f"s7r4_{mode}_{remain_kib}_{rep}_{c}"
                try:
                    rec = await collect(c, outdir, "exec cat /tmp/r4.bin", deadline=60, progress={})
                finally:
                    ds._FrameSource.next_frame = orig
                res = rec.get("result") or {}
                size = (outdir / "out").stat().st_size if (outdir / "out").exists() else None
                rows.append({"mode": mode, "remain_kib_at_stall": remain_kib, "rep": rep, "stall_at": state["stall_at"],
                             "exec_state": res.get("exec_state"), "exit_code": res.get("exit_code"),
                             "log_complete": res.get("log_complete"), "stdout_bytes": res.get("stdout_bytes"), "file_size": size,
                             "lost_bytes": (n - size) if size is not None else None,
                             "sha_match": sha256_file(outdir / "out") == want, "wall": rec["wall"]})
    return rows


async def r5_real_enospc(c: str) -> dict:
    mnt = TMP / "tinyfs"
    mnt.mkdir(exist_ok=True)
    sh("mount", "-t", "tmpfs", "-o", "size=1m", "tmpfs", str(mnt), check=True)
    try:
        run = await ds.run_exec_collected(
            container_name=c, user="root", workdir="/tmp", env={}, cmd="head -c 3145728 /dev/zero; echo e >&2; exit 0",
            stdout_path=mnt / "out", stderr_path=TMP / f"s7r5_err_{c}", deadline_seconds=60,
        )
        size = (mnt / "out").stat().st_size
        df = sh("df", "-B1", str(mnt)).stdout.strip().splitlines()[-1]
    finally:
        sh("umount", str(mnt))
    f = run.facts()
    return {"exec_state": f["exec_state"], "exit_code": f["exit_code"], "stdout_bytes": f["stdout_bytes"], "file_size": size,
            "counts_match_disk": f["stdout_bytes"] == size, "log_complete": f["log_complete"],
            "log_partial_reason": f["log_partial_reason"], "stderr_bytes": f["stderr_bytes"], "df": df}


async def main() -> None:
    c = new_container("s7real")
    out: dict = {"env": env_facts(),
                 "unix_sock_buffers": sh("sysctl", "net.core.wmem_default", "net.core.rmem_default").stdout.strip(),
                 "pipe_max": sh("cat", "/proc/sys/fs/pipe-max-size").stdout.strip()}
    try:
        out["r1_start_failures"] = await r1_start_failures(c)
        print("[ir1] r1 done", file=sys.stderr)
        out["r2_outputs_closed_early"] = await r2_outputs_closed_early(c)
        print("[ir1] r2 done", file=sys.stderr)
        out["r3_background_child"] = await r3_background_child_holds_stdout(c)
        print("[ir1] r3 done", file=sys.stderr)
        out["r4_tail_loss"] = await r4_tail_loss_on_consumer_stall(c)
        print("[ir1] r4 done", file=sys.stderr)
        out["r5_enospc"] = await r5_real_enospc(c)
        out["container_state_end"] = container_state(c)
    finally:
        rm_container(c)
    write_result("s7_real_daemon", out)


if __name__ == "__main__":
    asyncio.run(main())
