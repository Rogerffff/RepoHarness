"""场景 3：exec 流式收集期间容器被 kill / stop / rm -f / restart / pause。

每次新建容器（--init 等同正式 profile），起 `echo a; exec sleep 40`（或 TERM 陷阱变体），1.5 s 后在旁路执行动作，
等收集器返回；记录 exec_state / exit_code / inspect / stream_error、动作耗时、容器终态、事后 exec inspect。
TERM 陷阱变体：exec 进程若收到 SIGTERM 会打印 got-TERM 并以 99 退出——用来区分 docker stop 时 exec 进程
收到的是 TERM（143/99）还是随 PID 命名空间被 SIGKILL（137）。
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (TMP, collect, container_state, env_facts, exec_inspect_raw, file_info, new_container,  # noqa: E402
                     now, rm_container, write_result)

PLAIN = "echo a; exec sleep 40"
TRAP = "trap 'echo got-TERM; exit 99' TERM; echo a; sleep 40 & wait"


async def one(action: str, rep: int, *, cmd: str = PLAIN, init: bool = True, deadline: float = 60.0) -> dict:
    name = new_container(f"s3{action}", init=init)
    outdir = TMP / f"s3_{action}_{rep}_{name}"
    rec: dict = {"action": action, "rep": rep, "cmd": cmd, "init": init, "container": name}
    try:
        task = asyncio.create_task(collect(name, outdir, cmd, deadline=deadline, progress={}))
        await asyncio.sleep(1.5)
        argv = {"kill": ["docker", "kill", "--signal", "KILL", name], "stop": ["docker", "stop", name],
                "rm": ["docker", "rm", "-f", name], "restart": ["docker", "restart", name],
                "pause": ["docker", "pause", name]}[action]
        t = now()
        proc = await asyncio.create_subprocess_exec(*argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        coll = await task
        rec["collector_after_action_s"] = round(now() - t, 3)
        _o, err = await proc.communicate()
        rec["action_rc"], rec["action_s"], rec["action_stderr"] = proc.returncode, round(now() - t, 3), err.decode()[-200:]
        res = coll.get("result") or {}
        rec.update({"exec_state": res.get("exec_state"), "exit_code": res.get("exit_code"), "inspect": res.get("inspect"),
                    "stream_error": res.get("stream_error"), "log_partial_reason": res.get("log_partial_reason"),
                    "raised": coll.get("raised"), "wall": coll.get("wall"), "stdout": file_info(outdir / "out")["head"]
                    if (outdir / "out").exists() else None})
        rec["container_state_after"] = container_state(name)
        rec["exec_inspect_after"] = await exec_inspect_raw(res.get("exec_id") or (coll.get("progress") or {}).get("exec_id"))
        if action == "pause":
            rec["procs_while_paused_after_return"] = "skipped (paused)"
            up = await asyncio.create_subprocess_exec("docker", "unpause", name)
            await up.wait()
            await asyncio.sleep(0.5)
            rec["exec_inspect_after_unpause"] = await exec_inspect_raw(res.get("exec_id"))
    finally:
        rm_container(name)
    return rec


async def main() -> None:
    rows = []
    for rep in range(5):
        rows.append(await one("kill", rep))
    for rep in range(5):
        rows.append(await one("stop", rep))
    for rep in range(3):
        rows.append(await one("stop", rep, cmd=TRAP))
    rows.append(await one("stop", 0, init=False))  # 对照：无 init 时 PID 1 忽略 TERM，10 s 后 SIGKILL
    for rep in range(3):
        rows.append(await one("rm", rep))
    for rep in range(2):
        rows.append(await one("restart", rep))
    rows.append(await one("pause", 0, deadline=4.0))
    bad = [r for r in rows if r["exec_state"] == "exited" and not isinstance(r["exit_code"], int)]
    write_result("s3_container_kill_stop", {"env": env_facts(), "rows": rows, "bad_rows": bad})


if __name__ == "__main__":
    asyncio.run(main())
