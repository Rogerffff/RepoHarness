"""场景 2：dockerd 被 SIGSTOP 一段时间再 SIGCONT。

子场景（每个都有线程定时 CONT + finally CONT 双保险；STOP 期间不调用 docker CLI）：
 a_lines  流中途 STOP 5 s：进程每 20 ms 打一行共 300 行后 exit 5 —— 流只是停顿？行序 / 行数完整？终态 exited 5？
 a_bulk   流中途 STOP 5 s：进程快速写 20 MiB 后 exit 0 —— sha256 与容器内一致？
 b_deadline  STOP 横跨期限：deadline 3 s，t=1 s STOP，t=13 s CONT —— 收集器何时返回？time_budget 后那次
             "有界 inspect"（_TIME_BUDGET_INSPECT_SECONDS）真实耗时？CONT 后 exec 是否仍在跑？
 c_ghost  在 exec create 之后、exec start 之前 STOP（包装 engine_hijack 注入），40 s 后 CONT：收集器在 hijack 30 s
          超时后抛什么？CONT 后 daemon 会不会仍把这次 start 执行掉（"幽灵启动"：命令会 touch 标记文件）？
 d_create 在 exec create 之前 STOP，40 s 后 CONT：收集器多久失败、抛什么？CONT 后容器里是否留下已建未启动的 exec？
 e_settle 流 EOF 之后、终态轮询期间 STOP（包装 _await_exec_terminal 注入）5 s / 15 s：前者应拿到终态，后者应
          inspect_failed 而不是编造退出码；记录墙钟。
"""

from __future__ import annotations

import asyncio
import os
import signal
import sys
import threading
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (TMP, InspectLog, collect, container_state, dockerd_pid, ds, env_facts, exec_inspect_raw,  # noqa: E402
                     file_info, new_container, now, procs, rm_container, sh, sha256_file, wait_daemon, write_result)

PID = dockerd_pid()


def stop() -> float:
    os.kill(PID, signal.SIGSTOP)
    return now()


def cont() -> float:
    try:
        os.kill(PID, signal.SIGCONT)
    except ProcessLookupError:
        pass
    return now()


def cont_after(seconds: float) -> threading.Timer:
    t = threading.Timer(seconds, cont)
    t.daemon = True
    t.start()
    return t


def dockerd_state() -> str:
    try:
        return Path(f"/proc/{PID}/stat").read_text().split()[2]
    except OSError as exc:
        return f"?{exc}"


async def a_lines() -> dict:
    name = new_container("s2a")
    outdir = TMP / f"s2_a_lines_{name}"
    try:
        task = asyncio.create_task(collect(name, outdir, "for i in $(seq 1 300); do echo line-$i; sleep 0.02; done; exit 5",
                                           deadline=120, progress={}))
        await asyncio.sleep(1.5)
        t_stop = stop()
        cont_after(5.0)
        await asyncio.sleep(5.3)
        rec = await task
    finally:
        cont()
        rm_container(name)
    lines = (outdir / "out").read_text().splitlines() if (outdir / "out").exists() else []
    res = rec.get("result") or {}
    return {"case": "a_lines", "exec_state": res.get("exec_state"), "exit_code": res.get("exit_code"), "wall": rec["wall"],
            "lines": len(lines), "in_order": lines == [f"line-{i}" for i in range(1, 301)], "log_complete": res.get("log_complete"),
            "stream_error": res.get("stream_error"), "raised": rec.get("raised"), "stop_len_s": 5.0}


async def a_bulk() -> dict:
    name = new_container("s2a2")
    outdir = TMP / f"s2_a_bulk_{name}"
    # 1 MiB 一块、块间 0.1 s，约 2 s 写完 20 MiB；t=1.6 s STOP 必落在流中途
    cmd = ("head -c 20971520 /dev/urandom > /tmp/blob && sha256sum /tmp/blob > /tmp/blob.sha && sleep 1 && "
           "exec /opt/miniconda3/bin/python -c \"import sys,time\nd=open('/tmp/blob','rb').read()\n"
           "for i in range(0,len(d),1048576):\n sys.stdout.buffer.write(d[i:i+1048576]); sys.stdout.buffer.flush(); time.sleep(0.1)\"")
    try:
        task = asyncio.create_task(collect(name, outdir, cmd, deadline=120, progress={}))
        await asyncio.sleep(1.6)
        stop()
        cont_after(5.0)
        rec = await task
    finally:
        cont()
    try:
        want = sh("docker", "exec", name, "cat", "/tmp/blob.sha").stdout.split()[0]
    finally:
        rm_container(name)
    res = rec.get("result") or {}
    got = sha256_file(outdir / "out")
    return {"case": "a_bulk", "exec_state": res.get("exec_state"), "exit_code": res.get("exit_code"), "wall": rec["wall"],
            "stdout_bytes": res.get("stdout_bytes"), "sha_match": got == want, "log_complete": res.get("log_complete"),
            "raised": rec.get("raised")}


async def b_deadline() -> dict:
    name = new_container("s2b")
    outdir = TMP / f"s2_b_{name}"
    ilog = InspectLog().install()
    progress: dict = {}
    try:
        task = asyncio.create_task(collect(name, outdir, "echo started; exec sleep 30", deadline=3.0, progress=progress))
        await asyncio.sleep(1.0)
        t_stop = stop()
        cont_after(12.0)
        rec = await task
        returned_at = now() - t_stop
        state_at_return = dockerd_state()
        await asyncio.sleep(max(0.0, 12.5 - (now() - t_stop)))
    finally:
        ilog.uninstall()
        cont()
    wait_daemon()
    res = rec.get("result") or {}
    out = {"case": "b_deadline", "exec_state": res.get("exec_state"), "exit_code": res.get("exit_code"), "inspect": res.get("inspect"),
           "wall": rec["wall"], "returned_s_after_stop": round(returned_at, 3), "dockerd_state_at_return": state_at_return,
           "inspect_calls": ilog.calls, "raised": rec.get("raised"), "host_out": file_info(outdir / "out")["head"],
           "exec_inspect_after_cont": await exec_inspect_raw(res.get("exec_id")),
           "sleep_alive_after_cont": [p for p in procs(name).splitlines() if "sleep 30" in p]}
    rm_container(name)
    return out


async def c_ghost() -> dict:
    name = new_container("s2c")
    tag = uuid.uuid4().hex[:8]
    outdir = TMP / f"s2_c_{name}"
    orig = ds.engine_hijack
    marks: dict = {}

    async def hijack_with_stop(*a, **kw):
        marks["stop_at"] = stop()
        cont_after(40.0)
        return await orig(*a, **kw)

    ds.engine_hijack = hijack_with_stop
    progress: dict = {}
    try:
        rec = await collect(name, outdir, f"touch /tmp/ghost_{tag}; echo ghost; exec sleep 60", deadline=5.0, progress=progress)
    finally:
        ds.engine_hijack = orig
    raised_after = round(now() - marks["stop_at"], 3)
    await asyncio.sleep(max(0.0, 45.0 - (now() - marks["stop_at"])))
    cont()
    wait_daemon()
    await asyncio.sleep(2.0)
    exec_id = progress.get("exec_id")
    marker = sh("docker", "exec", name, "bash", "-c", f"ls -la /tmp/ghost_{tag} 2>&1; echo rc=$?").stdout.strip()
    out = {"case": "c_ghost", "raised": rec.get("raised"), "raised_type": rec.get("raised_type"), "wall": rec["wall"],
           "raised_s_after_stop": raised_after, "progress": rec.get("progress"),
           "marker_file_after_cont": marker, "ghost_started": "No such file" not in marker,
           "exec_inspect_after_cont": await exec_inspect_raw(exec_id), "container_state": container_state(name),
           "sleep_alive": [p for p in procs(name).splitlines() if "sleep 60" in p], "host_out": file_info(outdir / "out")}
    rm_container(name)
    return out


async def d_create() -> dict:
    name = new_container("s2d")
    outdir = TMP / f"s2_d_{name}"
    t_stop = stop()
    cont_after(40.0)
    try:
        rec = await collect(name, outdir, "echo x; exec sleep 5", deadline=3.0, progress={})
        raised_after = round(now() - t_stop, 3)
    finally:
        pass
    await asyncio.sleep(max(0.0, 45.0 - (now() - t_stop)))
    cont()
    wait_daemon()
    await asyncio.sleep(1.0)
    out = {"case": "d_create", "raised": rec.get("raised"), "raised_type": rec.get("raised_type"), "wall": rec["wall"],
           "raised_s_after_stop": raised_after, "progress": rec.get("progress"),
           "container_state_after_cont": container_state(name)}
    rm_container(name)
    return out


async def e_settle(stop_len: float) -> dict:
    name = new_container("s2e")
    outdir = TMP / f"s2_e_{int(stop_len)}_{name}"
    orig = ds._await_exec_terminal
    marks: dict = {}

    async def settle_with_stop(*a, **kw):
        marks["stop_at"] = stop()
        cont_after(stop_len)
        return await orig(*a, **kw)

    ds._await_exec_terminal = settle_with_stop
    ilog = InspectLog().install()
    try:
        rec = await collect(name, outdir, "echo e; exit 6", deadline=30.0, progress={})
        returned_after = round(now() - marks["stop_at"], 3)
    finally:
        ds._await_exec_terminal = orig
        ilog.uninstall()
    await asyncio.sleep(max(0.0, stop_len + 0.5 - (now() - marks["stop_at"])))
    cont()
    wait_daemon()
    res = rec.get("result") or {}
    out = {"case": f"e_settle_{int(stop_len)}s", "exec_state": res.get("exec_state"), "exit_code": res.get("exit_code"),
           "inspect": res.get("inspect"), "wall": rec["wall"], "returned_s_after_stop": returned_after,
           "inspect_calls": ilog.calls, "raised": rec.get("raised"),
           "exec_inspect_after_cont": await exec_inspect_raw(res.get("exec_id"))}
    rm_container(name)
    return out


async def main() -> None:
    rows = []
    try:
        for fn in (a_lines, a_bulk, b_deadline, c_ghost, d_create):
            rows.append(await fn())
            wait_daemon()
        rows.append(await e_settle(5.0))
        rows.append(await e_settle(15.0))
    finally:
        cont()
    write_result("s2_daemon_pause", {"env": env_facts(), "dockerd_pid": PID, "rows": rows})


if __name__ == "__main__":
    asyncio.run(main())
