"""场景 6：信号打到运行收集器的 Python 进程自己（SIGINT / SIGTERM / SIGHUP，默认处理与"优雅取消"两种；SIGKILL 对照）。

每例：新容器 → 起子进程（s6_child.py）→ 等它报告流已开始（exec_id）→ 记下子进程持有的 docker.sock 连接及其在 dockerd
一侧的对端 inode → 发信号 → 记录子进程如何结束（返回码 / 最后输出）→ 1 s 后核对：
- 宿主是否有僵尸（全表 ps 的 Z 状态）；子进程的连接是否已消失；dockerd 一侧对端 socket 是否还在（残留连接）；
- 同一 exec 的 inspect（Running?）与容器内 `sleep 120` 是否仍在跑（预期仍在：停止容器内进程是既有屏障的职责）；
- 宿主 out 文件内容。
最后 rm -f 容器，再核对 dockerd 一侧对端 socket 是否随之消失。
"""

from __future__ import annotations

import asyncio
import json
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (HERE, TMP, container_state, env_facts, exec_inspect_raw, file_info, new_container, procs,  # noqa: E402
                     rm_container, sh, write_result)

PY = sys.executable


def unix_socks(pid: int | None = None) -> list[dict]:
    rows = []
    for line in sh("ss", "-xpH").stdout.splitlines():
        f = line.split()
        if len(f) < 9:
            continue
        if pid is not None and f"pid={pid}," not in line:
            continue
        rows.append({"state": f[1], "local": f[4], "inode": f[5], "peer_inode": f[7], "proc": " ".join(f[8:])[:120]})
    return rows


def sock_by_inode(inode: str) -> list[str]:
    return [line for line in sh("ss", "-xpH").stdout.splitlines() if len(line.split()) > 5 and line.split()[5] == inode]


def zombies() -> list[str]:
    out = sh("ps", "-eo", "pid,ppid,stat,comm").stdout.splitlines()[1:]
    return [line.strip() for line in out if line.split()[2].startswith("Z")]


def one(sig: signal.Signals, mode: str) -> dict:
    name = new_container(f"s6{sig.name.lower()}{mode[0]}")
    outdir = TMP / f"s6_{sig.name}_{mode}_{name}"
    outdir.mkdir(parents=True, exist_ok=True)
    rec: dict = {"signal": sig.name, "mode": mode, "container": name, "zombies_before": zombies()}
    child = subprocess.Popen([PY, str(HERE / "s6_child.py"), mode, name, str(outdir)],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        line = child.stdout.readline()
        rec["first_event"] = json.loads(line) if line.strip() else None
        exec_id = (rec["first_event"] or {}).get("exec_id")
        time.sleep(0.5)
        socks = unix_socks(child.pid)
        rec["child_socks_before_signal"] = socks
        peer_inodes = [s["peer_inode"] for s in socks]
        rec["peer_side_before"] = {i: sock_by_inode(i) for i in peer_inodes}
        t = time.monotonic()
        child.send_signal(sig)
        try:
            rc = child.wait(timeout=30)
        except subprocess.TimeoutExpired:
            rc = "timeout"
            child.kill()
            child.wait()
        rec["child_exit_s"] = round(time.monotonic() - t, 3)
        rec["child_returncode"] = rc
        rest_out, rest_err = child.stdout.read(), child.stderr.read()
        rec["child_stdout_after_signal"] = [json.loads(x) for x in rest_out.splitlines() if x.strip().startswith("{")]
        rec["child_stderr_tail"] = rest_err[-600:]
        time.sleep(1.0)
        rec["zombies_after"] = zombies()
        rec["child_socks_after"] = unix_socks(child.pid)
        rec["peer_side_after_1s"] = {i: sock_by_inode(i) for i in peer_inodes}
        rec["exec_inspect_after"] = asyncio.run(exec_inspect_raw(exec_id))
        rec["container_procs_after"] = [p for p in procs(name).splitlines() if "sleep 120" in p]
        rec["host_out"] = file_info(outdir / "out")
        rec["container_state_after"] = container_state(name)
    finally:
        if child.poll() is None:
            child.kill()
            child.wait()
        rm_container(name)
    time.sleep(1.0)
    rec["peer_side_after_container_rm"] = {i: sock_by_inode(i) for i in peer_inodes}
    rec["exec_inspect_after_container_rm"] = asyncio.run(exec_inspect_raw(exec_id))
    return rec


def main() -> None:
    cases = [(signal.SIGINT, "default"), (signal.SIGTERM, "default"), (signal.SIGHUP, "default"),
             (signal.SIGTERM, "graceful"), (signal.SIGHUP, "graceful"), (signal.SIGKILL, "default")]
    rows = [one(sig, mode) for sig, mode in cases]
    write_result("s6_collector_signals", {"env": env_facts(), "rows": rows})


if __name__ == "__main__":
    main()
