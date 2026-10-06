"""本机既有 Python 镜像：只杀本探针的 docker exec 客户端，记录生产收集器结果。

不拉镜像，不运行 CC/模型，不碰用户容器或 Docker daemon；finally 删除本次随机名容器。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import signal
import sys
import tempfile
import uuid
from pathlib import Path

REPO = next(p for p in Path(__file__).resolve().parents if (p / "rh2/src").is_dir())
sys.path.insert(0, str(REPO / "rh2/src"))

import pytest
from repoharness2.adapters.slime import docker_sandbox as ds


async def docker(*args):
    proc = await asyncio.create_subprocess_exec("docker", *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        out, err = await asyncio.wait_for(proc.communicate(), 20)
    except BaseException:
        if proc.returncode is None:
            proc.kill()
        await proc.communicate()
        raise
    if proc.returncode:
        raise RuntimeError(f"docker {args[0]}: {err.decode(errors='replace')}")
    return out.decode().strip()


async def main():
    image = os.environ.get("RH2_REVIEW_IMAGE", "python:3.12-slim")
    image_id = await docker("image", "inspect", image, "--format", "{{.Id}}")
    name = "rh2-review-host-signals-" + uuid.uuid4().hex[:10]
    rows = []
    removed = False
    try:
        await docker("run", "--detach", "--pull=never", "--name", name, "--network=none", "--read-only",
                     "--memory=128m", "--cpus=0.5", "--pids-limit=64", "--cap-drop=ALL",
                     "--security-opt=no-new-privileges", image, "sleep", "300")
        with tempfile.TemporaryDirectory(prefix="rh2-review-docker-signals-") as directory:
            for rc in (0, 3, 130):
                root = Path(directory) / f"control-{rc}"
                run = await ds.run_host_collected(
                    ["docker", "exec", "-u", "65534", name, "python", "-c", f"import sys; sys.exit({rc})"],
                    stdout_path=root / "stdout", stderr_path=root / "stderr", deadline_seconds=10,
                )
                rows.append({"control_container_exit": rc, "exit_code": run.exit_code,
                             "client_exit_kind": run.client_exit_kind, "log_complete": run.log_complete})
            for signal_name in ("SIGHUP", "SIGINT", "SIGTERM", "SIGKILL"):
                root = Path(directory) / signal_name
                ready = asyncio.Event()
                client = None
                original_spawn = asyncio.create_subprocess_exec

                async def spawn(*args, _spawn=original_spawn, _ready=ready, **kwargs):
                    nonlocal client
                    client = await _spawn(*args, **kwargs)
                    _ready.set()
                    return client

                with pytest.MonkeyPatch.context() as mp:
                    mp.setattr(asyncio, "create_subprocess_exec", spawn)
                    task = asyncio.create_task(ds.run_host_collected(
                        ["docker", "exec", "-u", "65534", name, "python", "-u", "-c",
                         "import os,time; print(os.getpid(), flush=True); time.sleep(30)"],
                        stdout_path=root / "stdout", stderr_path=root / "stderr", deadline_seconds=10,
                    ))
                    try:
                        await asyncio.wait_for(ready.wait(), 3)
                        for _ in range(400):
                            if (root / "stdout").exists() and (root / "stdout").stat().st_size:
                                break
                            if task.done():
                                await task
                            await asyncio.sleep(0.01)
                        assert (root / "stdout").stat().st_size > 0
                        os.kill(client.pid, getattr(signal, signal_name))
                        run = await asyncio.wait_for(task, 5)
                        pid = int((root / "stdout").read_text().strip())
                        # 独立连接只读核查同一个容器内 PID；不借用收集器的退出推断。
                        inner_state = await docker(
                            "exec", name, "python", "-c",
                            f"from pathlib import Path; p=Path('/proc/{pid}/cmdline'); print(p.read_bytes().decode().replace(chr(0), ' ') if p.exists() else 'MISSING')",
                        )
                        rows.append({"signal": signal_name, "exit_code": run.exit_code,
                                     "client_exit_code": run.client_exit_code, "client_exit_kind": run.client_exit_kind,
                                     "log_complete": run.log_complete, "stdout": (root / "stdout").read_text(),
                                     "stderr_tail": run.stderr_tail,
                                     "container_process_alive_after_client_exit": "time.sleep(30)" in inner_state})
                    finally:
                        if not task.done():
                            task.cancel()
                            await asyncio.gather(task, return_exceptions=True)
    finally:
        await docker("rm", "-f", name)
        removed = True
    result = {"client_version": await docker("version", "--format", "{{.Client.Version}}"),
              "server_version": await docker("version", "--format", "{{.Server.Version}}"),
              "collector_source_sha256": hashlib.sha256(Path(ds.__file__).read_bytes()).hexdigest(),
              "image_id": image_id, "signals": rows, "owned_container_removed": removed,
              "remaining_owned_names": await docker("ps", "-a", "--filter", f"name={name}", "--format", "{{.Names}}")}
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if __file__ != "<stdin>":
        Path(__file__).with_name(Path(__file__).stem + "_with_pid.json").write_text(output)
    print(output, end="")


if __name__ == "__main__":
    asyncio.run(main())
