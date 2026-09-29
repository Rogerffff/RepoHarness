"""默认 egress 入口的同名启动反例；仅使用已有本机 Docker 镜像与随机专属容器名。"""

from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path

from repoharness2.adapters.slime import sandbox_profile as sp


async def main():
    docker = sp.default_docker_runner
    image = await docker("image", "inspect", sp.RELAY_IMAGE_DEFAULT)
    assert image.exit_code == 0, "需已有本机镜像；本探针不下载"
    run_id = f"codex-egress-{uuid.uuid4().hex[:8]}"
    name = f"rh2-egress-relay-{run_id}"
    profile = sp.RolloutSandboxProfile(
        model_proxy_upstream_host="127.0.0.1", model_proxy_upstream_port=1234,
    )
    labels = ("--label", f"rh2.run_id={run_id}")
    try:
        first = await sp.start_egress_relay(docker, profile, run_id=run_id, labels=labels)
        before = await docker("inspect", "-f", "{{.State.Running}}", first.container_name)
        assert before.exit_code == 0 and before.stdout.strip() == "true"
        try:
            await sp.start_egress_relay(docker, profile, run_id=run_id, labels=labels)
        except sp.SandboxNetworkError as exc:
            error = {"reason": exc.reason_code, "name_conflict": "already in use" in str(exc)}
        after = await docker("inspect", "-f", "{{.State.Running}}", first.container_name)
        assert error["name_conflict"] and after.exit_code != 0
        facts = {
            "head": "23f5586d", "entry": "start_egress_relay", "second_start": error,
            "first_running_before": True, "first_inspect_exit_after": after.exit_code,
            "first_stderr_after": after.stderr.strip(),
        }
    finally:
        await docker("rm", "-f", name)
        left = await docker("ps", "-aq", "--filter", f"label=rh2.run_id={run_id}")
        assert left.exit_code == 0 and not left.stdout.strip()
    result = json.dumps(facts, ensure_ascii=False, indent=2) + "\n"
    Path(__file__).with_suffix(".json").write_text(result)
    print(result, end="")


if __name__ == "__main__":
    asyncio.run(main())
