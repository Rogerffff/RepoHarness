"""真实本机 Docker：供应 relay 创建后、readiness await 中取消。

只延迟 readiness DockerRunner 调用；镜像、run 参数、Docker daemon 为真实。
不拉镜像、不接入题目网络，finally 只清理本探针的随机命名容器。
"""
from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path

from repoharness2.adapters.slime import sandbox_profile as sp

HERE = Path(__file__).resolve().parent


async def main():
    image = await sp.default_docker_runner("image", "inspect", sp.RELAY_IMAGE_DEFAULT)
    assert image.exit_code == 0, "本机须已有镜像，不自动拉取"
    run_id = f"codex-supply-cancel-{uuid.uuid4().hex[:8]}"
    name = f"rh2-supply-relay-{run_id}"
    entered = asyncio.Event()
    calls = []

    async def docker(*args, **kwargs):
        calls.append(args[0])
        if args[0] == "exec":
            entered.set()
            await asyncio.Event().wait()
        return await sp.default_docker_runner(*args, **kwargs)

    task = asyncio.create_task(sp.start_supply_relay(
        docker, sp.RolloutSandboxProfile(model_proxy_upstream_host="127.0.0.1", model_proxy_upstream_port=1234),
        gateway_host="127.0.0.1", gateway_port=1234, run_id=run_id,
        labels=("--label", f"rh2.run_id={run_id}"),
    ))
    try:
        await asyncio.wait_for(entered.wait(), 15)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            cancellation_propagated = True
        inspect = await sp.default_docker_runner("inspect", "-f", "{{.State.Running}}", name)
        facts = {
            "scope": __doc__, "cancellation_propagated": cancellation_propagated,
            "helper_commands": list(calls), "running_after_cancel": inspect.stdout.strip(),
            "inspect_exit": inspect.exit_code,
        }
        assert calls == ["run", "exec"] and inspect.exit_code == 0 and inspect.stdout.strip() == "true"
    finally:
        if not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        removed = await sp.default_docker_runner("rm", "-f", name)
        check = await sp.default_docker_runner("ps", "-aq", "--filter", f"label=rh2.run_id={run_id}")
        assert removed.exit_code == 0 and check.exit_code == 0 and not check.stdout.strip()
    facts["probe_cleanup_confirmed"] = True
    (HERE / "main_relay_cancel_docker.json").write_text(json.dumps(facts, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(facts, ensure_ascii=False))


asyncio.run(main())
