"""批 B 独立 CPU 探针：真实子进程通道取消与物化私网所有权。

仅替换 subprocess / Docker IO，不启动真实 Docker、容器或模型。
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "rh2/pyproject.toml").is_file())
sys.path.insert(0, str(ROOT / "rh2/src"))
sys.path.insert(0, str(ROOT / "rh2/tests/adapters"))

from test_slime_generate import SAMPLING_PARAMS, _Args
from test_w1b_termination_facts_producer import _formal_chain

from repoharness2.adapters.slime import bringup, docker_sandbox, generate
from repoharness2.grading import manager
from repoharness2.shutdown.chain import ShutdownTimeouts


class _BlockedProcess:
    def __init__(self):
        self.entered = asyncio.Event()
        self.returncode = None
        self.kill_calls = 0
        self.wait_calls = 0

    async def communicate(self, input=None):
        self.entered.set()
        await asyncio.Event().wait()

    def kill(self):
        self.kill_calls += 1
        self.returncode = -9

    async def wait(self):
        self.wait_calls += 1
        return self.returncode


async def process_cancel(runner, name):
    proc = _BlockedProcess()

    async def spawn(*args, **kwargs):
        assert args[0] == "docker"
        return proc

    with patch.object(asyncio, "create_subprocess_exec", spawn):
        pending = asyncio.create_task(runner("image", "inspect", "review-image"))
        await asyncio.wait_for(proc.entered.wait(), timeout=1)
        pending.cancel()
        try:
            await asyncio.wait_for(pending, timeout=1)
        except asyncio.CancelledError:
            pass
    return {
        "case": name,
        "cancelled": pending.cancelled(),
        "kill_calls": proc.kill_calls,
        "wait_calls": proc.wait_calls,
    }


def _short_remaining_clock():
    values = iter((0.0, 899.95))
    return lambda: next(values, 1000.0)


async def network_cancel(stage):
    chain = _formal_chain()
    orch = chain.orchestrator
    original_docker = orch._docker
    entered = asyncio.Event()

    async def block_after_effect(*args, input_bytes=None):
        # 模拟 daemon 已完成创建/接入，而 CLI 仍等待响应；其余 IO 为既有 CPU 替身。
        result = await original_docker(*args, input_bytes=input_bytes)
        if args[:2] == ("network", stage):
            entered.set()
            await asyncio.Event().wait()
        return result

    orch._docker = block_after_effect
    orch._clock = _short_remaining_clock()
    delivered = await asyncio.wait_for(
        orch.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS)), timeout=2
    )
    audit = orch.audits[-1]
    result = {
        "case": f"episode_deadline_during_network_{stage}",
        "stage_entered": entered.is_set(),
        "reason_code": audit.outcome_v2["reason_code"],
        "termination_kind": audit.outcome_v2["termination_kind"],
        "aborted": all(sample.remove_sample for sample in delivered),
        "daemon_networks_before_shutdown": len(chain.docker.profile_fake.networks),
        "registered_networks_before_shutdown": len(orch._attempt_networks),
        "pool_slots_before_shutdown": len(orch._egress_pool._in_use),
        "removed_networks_before_shutdown": len(chain.docker.profile_fake.removed_networks),
        "container_run_calls": sum(args[0] == "run" for args in chain.docker.calls),
        "cleanup_completed": "cleanup_completed" in [event.step for event in audit.timeline],
        "cleanup_failures": len(audit.cleanup_failures),
        "quarantine": list(orch.cleanup_quarantine),
    }

    # 直接执行真实 shutdown 的 egress_runtime 一步，验证 label 兜底的实际边界。
    service = bringup.BringupService.__new__(bringup.BringupService)
    service.shutdown_timeouts = ShutdownTimeouts()
    service.egress_relay = orch._egress_relay
    with patch.object(bringup, "_sandbox_docker", lambda: original_docker):
        step = next(step for step in service._build_shutdown_steps() if step.name == "egress_runtime")
        shutdown_facts = await step.run()
    result.update(
        shutdown_networks_removed=len(shutdown_facts["networks_removed"]),
        shutdown_failures=shutdown_facts["failures"],
        daemon_networks_after_shutdown=len(chain.docker.profile_fake.networks),
        registered_networks_after_shutdown=len(orch._attempt_networks),
        pool_slots_after_shutdown=len(orch._egress_pool._in_use),
    )
    assert result["stage_entered"] and result["aborted"]
    assert result["reason_code"] == "episode_deadline_in_materialize"
    assert result["daemon_networks_before_shutdown"] == 1
    assert result["removed_networks_before_shutdown"] == 0
    assert result["pool_slots_before_shutdown"] == 1
    assert result["daemon_networks_after_shutdown"] == 0
    assert result["pool_slots_after_shutdown"] == 1
    return result


async def main():
    assert generate.run_docker is manager.run_docker
    assert bringup._sandbox_docker() is manager.run_docker
    process_results = [
        await process_cancel(manager.run_docker, "materialize_default_run_docker"),
        await process_cancel(docker_sandbox._run, "driver_docker_sandbox_run"),
    ]
    assert process_results[0]["kill_calls"] == process_results[0]["wait_calls"] == 0
    assert process_results[1]["kill_calls"] == process_results[1]["wait_calls"] == 1
    network_results = [await network_cancel("create"), await network_cancel("connect")]
    print(json.dumps({"process_cancel": process_results, "network_cancel": network_results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
