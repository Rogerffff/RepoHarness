"""用本机已有 Linux 镜像验证分离启动后的僵尸：真实 DockerSandbox / exec_and_wait / 停止 helper。

仅创建本脚本自己的临时容器，--pull=never、无网络、无宿主挂载，finally 删除；不启动 CC 或模型。
四个对照：自然完成 / 强停，分别不带和带 --init。不是完整 SWE 或 GPU 验收。
"""
from __future__ import annotations

import asyncio
import dataclasses
import json
import sys
import time
import uuid
from pathlib import Path
from types import SimpleNamespace

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "rh2/pyproject.toml").is_file())
sys.path.insert(0, str(ROOT / "rh2/src"))

from slime.agent.sandbox import exec_and_wait
from repoharness2.adapters.slime.docker_sandbox import DockerSandbox
from repoharness2.adapters.slime.execution_scope import COUNT_SCRIPT, terminate_agent_processes

HERE = Path(__file__).resolve().parent
IMAGE = "node:22-bookworm"


async def docker(*args, check=True):
    proc = await asyncio.create_subprocess_exec("docker", *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), 12)
    except BaseException:
        if proc.returncode is None:
            proc.kill()
            await proc.wait()
        raise
    result = SimpleNamespace(exit_code=proc.returncode, stdout=stdout.decode(), stderr=stderr.decode())
    if check and result.exit_code:
        raise RuntimeError(f"docker {args[0]} failed: {result.stderr[:500]}")
    return result


async def one_case(*, with_init: bool, forced: bool):
    name = "rh2-review-stop-" + uuid.uuid4().hex[:10]
    record = {"case": f"{'init' if with_init else 'sleep_pid1'}_{'forced' if forced else 'natural'}", "container_name": name}
    running = None
    created = False
    try:
        args = ["run", "--detach", "--pull=never", "--network", "none", "--cpus", "0.5", "--memory", "256m", "--pids-limit", "64", "--cap-drop", "ALL"]
        for cap in ("CHOWN", "DAC_OVERRIDE", "DAC_READ_SEARCH", "FOWNER", "KILL"):
            args += ["--cap-add", cap]
        args += ["--security-opt", "no-new-privileges", "--label", "rh2.review=budget-stop-followup2", "--name", name]
        if with_init:
            args += ["--init"]
        args += [IMAGE, "sleep", "infinity"]
        await docker(*args)
        created = True
        await docker("exec", name, "bash", "-c", "command -v ps && command -v pkill && useradd -m -u 20123 agent && mkdir /testbed && chown agent:agent /testbed")
        record["pid1"] = (await docker("exec", name, "ps", "-o", "pid=,ppid=,stat=,comm=", "-p", "1")).stdout.strip()
        sb = DockerSandbox(name)
        running = asyncio.create_task(exec_and_wait(sb, cmd="sleep 60 & wait" if forced else "true", user="agent", workdir="/testbed", time_budget_sec=15, tag="probe", want_output=False))
        if forced:
            start = time.monotonic()
            while True:
                p = await docker("exec", name, "ps", "-o", "stat=", "-u", "agent", check=False)
                if len(p.stdout.splitlines()) >= 2:
                    break
                if time.monotonic() - start > 4:
                    raise AssertionError("detached launcher did not start")
                await asyncio.sleep(0.05)
            record["before_stop_states"] = p.stdout.split()
        else:
            record["natural_exit_code"], _ = await asyncio.wait_for(running, 9)
            assert record["natural_exit_code"] == 0

        class Workspace:
            async def run_bash(self, script):
                return await docker("exec", name, "bash", "-c", f"cd /testbed && {script}", check=False)

        # 真实 helper，短观察窗口；目的是状态分类，不模拟 episode 时间。
        stop = await terminate_agent_processes(Workspace(), attempts=3, interval=0.1, total_timeout=2)
        record["stop"] = dataclasses.asdict(stop)
        record["helper_verified"] = stop.verified
        record["processes_after_stop"] = (await docker("exec", name, "ps", "-o", "pid=,ppid=,stat=,comm=", "-u", "agent", check=False)).stdout.strip()
        record["current_count"] = int((await Workspace().run_bash(COUNT_SCRIPT)).stdout.strip())
        filtered = "ps -o stat= -u agent | awk '$1 !~ /^Z/ {n++} END {print n+0}'"
        record["count_excluding_zombies"] = int((await Workspace().run_bash(filtered)).stdout.strip())
        if with_init:
            assert record["current_count"] == 0 and record["helper_verified"]
        else:
            assert record["current_count"] > 0 and not record["helper_verified"]
            assert record["count_excluding_zombies"] == 0
            assert all(line.split()[2].startswith("Z") for line in record["processes_after_stop"].splitlines())
    finally:
        if running is not None and not running.done():
            running.cancel()
            await asyncio.gather(running, return_exceptions=True)
        # 仅按本探针唯一名字清理；不扫描或操作其它容器。
        if created:
            await docker("rm", "--force", name)
            check = await docker("ps", "--all", "--quiet", "--filter", f"name=^/{name}$")
            record["container_removed"] = check.stdout.strip() == ""
            assert record["container_removed"]
    return record


async def main():
    server = json.loads((await docker("version", "--format", "{{json .Server}}")).stdout)
    image = json.loads((await docker("image", "inspect", IMAGE)).stdout)[0]
    record = {"docker_version": server["Version"], "kernel": next(x["Details"]["KernelVersion"] for x in server["Components"] if x["Name"] == "Engine"), "docker_arch": server["Arch"], "image_id": image["Id"], "image_arch": image["Architecture"], "cases": []}
    for forced, with_init in ((False, False), (True, False), (False, True), (True, True)):
        record["cases"].append(await one_case(with_init=with_init, forced=forced))
        (HERE / "zombie_docker_result.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
