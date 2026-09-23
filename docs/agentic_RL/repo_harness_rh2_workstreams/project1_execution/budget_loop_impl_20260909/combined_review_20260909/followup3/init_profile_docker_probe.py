"""第三次窄复核：实际 rollout profile 参数、真实分离启动与停止确认。

只用已有 node 镜像，临时内部网络、无宿主挂载，无 CC / 外部 API。
正常与强停两案；保留生产参数构造器，最终只清理本探针自己的容器和网络。
"""
from __future__ import annotations

import asyncio
import copy
import dataclasses
import hashlib
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
from repoharness2.adapters.slime.execution_scope import terminate_agent_processes
from repoharness2.adapters.slime.sandbox_profile import (
    RolloutSandboxProfile, check_rollout_inspect, rollout_trusted_init_script,
)

HERE = Path(__file__).resolve().parent
IMAGE = "node:22-bookworm"
LABEL = "rh2.review=budget-followup3"


async def docker(*args, check=True):
    proc = await asyncio.create_subprocess_exec(
        "docker", *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), 15)
    except BaseException:
        if proc.returncode is None:
            proc.kill()
            await proc.wait()
        raise
    result = SimpleNamespace(exit_code=proc.returncode, stdout=out.decode(), stderr=err.decode())
    if check and result.exit_code:
        raise RuntimeError(f"docker {args[0]} failed: {result.stderr[:500]}")
    return result


async def one_case(forced: bool):
    uid = uuid.uuid4().hex[:10]
    name, network = f"rh2-review-init-{uid}", f"rh2-review-init-net-{uid}"
    profile = RolloutSandboxProfile(
        model_proxy_upstream_host="host.docker.internal", model_proxy_upstream_port=18000,
        pids_limit=64, cpus=0.5, memory_bytes=256 * 1024**2,
        tmp_tmpfs_bytes=32 * 1024**2, home_tmpfs_bytes=16 * 1024**2,
    )
    record = {"case": "forced" if forced else "natural", "container": name, "network": network}
    running = None
    try:
        await docker("network", "create", "--internal", "--label", LABEL, network)
        args = profile.docker_run_args(name=name, network=network, image=IMAGE, labels=("--label", LABEL))
        # 验证用镜像必须本机已有；其余参数保持生产构造器结果。
        await docker(args[0], "--pull=never", *args[1:])
        await docker("exec", name, "mkdir", "-p", profile.workdir)
        await docker("exec", name, "bash", "-c", rollout_trusted_init_script(profile))
        inspected = json.loads((await docker("inspect", name)).stdout)[0]
        record["inspect_violations"] = check_rollout_inspect(inspected, profile, expected_network=network)
        assert record["inspect_violations"] == []
        record["profile_parameters"] = profile.to_parameters()
        record["profile_digest"] = profile.digest()
        record["host_config_init"] = inspected["HostConfig"]["Init"]
        record["pid1"] = (await docker("exec", name, "ps", "-o", "pid=,ppid=,stat=,comm=", "-p", "1")).stdout.strip()
        record["profile_run_args"] = args
        assert record["host_config_init"] is True and record["pid1"].endswith("docker-init")
        assert record["profile_parameters"]["init"] is True and "--init" in args
        old_parameters = dict(record["profile_parameters"])
        old_parameters.pop("init")
        legacy_digest = "sha256:" + hashlib.sha256(json.dumps(old_parameters, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
        record["same_parameters_without_init_digest"] = legacy_digest
        assert legacy_digest != record["profile_digest"]
        # 只改本地 inspect 副本：证明新增启动核对真的读取该事实。
        absent_init = copy.deepcopy(inspected)
        absent_init["HostConfig"]["Init"] = False
        failures = check_rollout_inspect(absent_init, profile, expected_network=network)
        assert len(failures) == 1 and "HostConfig.Init" in failures[0]
        record["negative_init_inspect_violations"] = failures

        sb = DockerSandbox(name)
        record["agent_uid"] = (await sb.exec("id -u", user="agent", check=True))[1].strip()
        assert record["agent_uid"] == str(profile.agent_uid)
        running = asyncio.create_task(exec_and_wait(
            sb, cmd="sleep 60 & wait" if forced else "true", user="agent",
            workdir=profile.workdir, time_budget_sec=15, tag="initreview", want_output=False,
        ))
        if forced:
            start = time.monotonic()
            while True:
                rows = (await docker("exec", name, "ps", "-o", "stat=", "-u", "agent", check=False)).stdout.split()
                if len(rows) >= 2:
                    break
                if time.monotonic() - start > 4:
                    raise AssertionError("分离进程未启动")
                await asyncio.sleep(0.05)
            record["agent_states_before_stop"] = rows
        else:
            code, _ = await asyncio.wait_for(running, 9)
            record["natural_exit_code"] = code
            assert code == 0
            record["agent_rows_before_stop"] = (await docker("exec", name, "ps", "-o", "pid=,ppid=,stat=,comm=", "-u", "agent", check=False)).stdout.strip()

        class Workspace:
            async def run_bash(self, script):
                return await docker("exec", name, "bash", "-c", f"cd {profile.workdir} && {script}", check=False)

        stop = await terminate_agent_processes(Workspace(), total_timeout=3)
        record["stop"] = dataclasses.asdict(stop)
        assert stop.verified and not stop.timed_out
        record["agent_rows_after_stop"] = (await docker("exec", name, "ps", "-o", "pid=,ppid=,stat=,comm=", "-u", "agent", check=False)).stdout.strip()
        assert not record["agent_rows_after_stop"]
    finally:
        if running is not None and not running.done():
            running.cancel()
            await asyncio.gather(running, return_exceptions=True)
        # 即使创建调用已发出但未返回，也按本探针预选名字清理，不操作其它资源。
        await docker("rm", "--force", name, check=False)
        await docker("network", "rm", network, check=False)
        record["container_removed"] = not (await docker("ps", "--all", "--quiet", "--filter", f"name=^/{name}$")).stdout.strip()
        record["network_removed"] = (await docker("network", "inspect", network, check=False)).exit_code != 0
        assert record["container_removed"] and record["network_removed"]
    return record


async def main():
    server = json.loads((await docker("version", "--format", "{{json .Server}}")).stdout)
    image = json.loads((await docker("image", "inspect", IMAGE)).stdout)[0]
    result = {"docker_version": server["Version"], "arch": server["Arch"], "image_id": image["Id"], "cases": []}
    for forced in (False, True):
        result["cases"].append(await one_case(forced))
        (HERE / "init_profile_docker_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
