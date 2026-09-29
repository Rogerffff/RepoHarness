"""场景 1：exec 流式收集期间 daemon 重启 / 崩溃（live-restore 关 / 开两种）。

每例：新容器，收集器起 `echo started; echo e >&2; exec sleep 60`（deadline 120），3 s 后在旁路执行动作：
  restart = `systemctl restart docker`；kill9 = `kill -9 $(pidof dockerd)`（systemd Restart=always，2 s 后拉起）。
记录收集器返回 / 抛出的形态（exec_state / exit_code / stream_error / inspect / 每次 inspect 的时刻与结果），
动作耗时，daemon 恢复后容器状态、同一 exec 的 inspect、容器内 sleep 60 是否仍在。
合格线（任务要求）：绝不能返回 exec_state == "exited" 带退出码。

live-restore 开：临时写 /etc/docker/daemon.json {"live-restore": true} 并 reload；结束后删除该文件（原本不存在）并恢复。
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (TMP, InspectLog, collect, container_state, env_facts, exec_inspect_raw, file_info,  # noqa: E402
                     new_container, now, procs, rm_container, sh, wait_daemon, write_result)

DAEMON_JSON = Path("/etc/docker/daemon.json")


def live_restore() -> str:
    return sh("docker", "info", "--format", "{{.LiveRestoreEnabled}}").stdout.strip()


def set_live_restore(on: bool) -> str:
    if on:
        DAEMON_JSON.write_text(json.dumps({"live-restore": True}))
    elif DAEMON_JSON.exists():
        DAEMON_JSON.unlink()
    sh("systemctl", "reload", "docker")
    time.sleep(1.0)
    got = live_restore()
    if got != ("true" if on else "false"):  # reload 不生效就重启（此刻本批没有在跑的容器）
        sh("systemctl", "reset-failed", "docker.service")
        sh("systemctl", "restart", "docker", timeout=300)
        wait_daemon()
        got = live_restore()
    return got


async def one(case: str, action: list[str], live: bool) -> dict:
    sh("systemctl", "reset-failed", "docker.service")
    name = new_container(f"s1{case}")
    outdir = TMP / f"s1_{case}_{name}"
    rec: dict = {"case": case, "action": action, "live_restore_before": live_restore(), "container": name}
    ilog = InspectLog().install()
    progress: dict = {}
    try:
        task = asyncio.create_task(collect(name, outdir, "echo started; echo e >&2; exec sleep 60", deadline=120,
                                           progress=progress))
        await asyncio.sleep(3.0)
        rec["progress_before_action"] = {k: progress.get(k) for k in ("exec_state", "exec_id", "stdout_bytes")}
        ilog.t0 = now()
        t = now()
        proc = await asyncio.create_subprocess_exec(*action, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        coll = await task
        rec["collector_returned_s_after_action"] = round(now() - t, 3)
        _o, err = await proc.communicate()
        rec["action_rc"], rec["action_s"], rec["action_stderr"] = proc.returncode, round(now() - t, 3), err.decode()[-300:]
    finally:
        ilog.uninstall()
    rec["inspect_calls_rel_to_action"] = ilog.calls
    res = coll.get("result") or {}
    rec["collector"] = {k: res.get(k) for k in ("exec_state", "exit_code", "inspect", "stream_error", "log_complete",
                                                  "log_partial_reason", "stdout_bytes", "stderr_bytes")}
    rec["collector"]["raised"] = coll.get("raised")
    rec["collector"]["wall"] = coll.get("wall")
    rec["daemon_back_s"] = wait_daemon()
    await asyncio.sleep(2.0)
    rec["live_restore_after"] = live_restore()
    rec["container_state_after"] = container_state(name)
    rec["exec_inspect_after_restart"] = await exec_inspect_raw(res.get("exec_id") or rec["progress_before_action"].get("exec_id"))
    rec["sleep60_in_container_after"] = [p for p in procs(name).splitlines() if "sleep 60" in p] \
        if container_state(name).startswith("running") else "container not running"
    rec["host_out"] = file_info(outdir / "out")["head"]
    rec["forbidden_exited_with_code"] = res.get("exec_state") == "exited" and res.get("exit_code") is not None
    rm_container(name)
    return rec


async def main() -> None:
    restart = ["systemctl", "restart", "docker"]
    kill9 = ["bash", "-c", "kill -9 $(pidof dockerd)"]
    rows = []
    env0 = env_facts()
    try:
        rows.append(await one("restart_liveoff", restart, False))
        await asyncio.sleep(5)
        rows.append(await one("kill9_liveoff", kill9, False))
        await asyncio.sleep(5)
        rows.append({"set_live_restore_on": set_live_restore(True)})
        rows.append(await one("restart_liveon", restart, True))
        await asyncio.sleep(5)
        rows.append(await one("kill9_liveon", kill9, True))
    finally:
        restored = set_live_restore(False)
        sh("systemctl", "reset-failed", "docker.service")
    write_result("s1_daemon_restart", {"env_before": env0, "live_restore_restored_to": restored,
                                       "daemon_json_exists_after": DAEMON_JSON.exists(), "rows": rows})


if __name__ == "__main__":
    asyncio.run(main())
