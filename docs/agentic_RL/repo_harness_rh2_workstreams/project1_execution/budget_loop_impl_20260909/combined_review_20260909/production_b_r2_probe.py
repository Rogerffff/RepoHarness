"""批 B 旧 R2 针对性复核；只替换底层子进程与 Docker IO。"""

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
from repoharness2.adapters.slime import bringup, generate
from repoharness2.grading import manager


async def runner_cancel():
    class Proc:
        returncode = None
        kills = 0
        waits = 0
        entered = asyncio.Event()

        async def communicate(self, input=None):
            self.entered.set()
            await asyncio.Event().wait()

        def kill(self):
            self.kills += 1
            self.returncode = -9

        async def wait(self):
            self.waits += 1
            return self.returncode

    proc = Proc()

    async def spawn(*args, **kwargs):
        return proc

    assert generate.run_docker is manager.run_docker
    assert bringup._sandbox_docker() is manager.run_docker
    with patch.object(asyncio, "create_subprocess_exec", spawn):
        running = asyncio.create_task(manager.run_docker("image", "inspect", "review"))
        await proc.entered.wait()
        running.cancel()
        try:
            await running
        except asyncio.CancelledError:
            pass
    assert proc.kills == proc.waits == 1 and running.cancelled()
    return {"case": "real_default_runner_cancel", "kill": proc.kills, "wait": proc.waits}


async def resource_cancel(stage, *, cleanup_fails=False):
    chain = _formal_chain()
    orch = chain.orchestrator
    docker = orch._docker
    entered = asyncio.Event()
    if cleanup_fails:
        chain.docker.profile_fake.network_rm_fail_for = ("*",)

    async def blocked(*args, input_bytes=None):
        result = await docker(*args, input_bytes=input_bytes)
        matches = args[0] == "run" if stage == "run" else args[:2] == ("network", stage)
        if matches:
            entered.set()
            await asyncio.Event().wait()
        return result

    orch._docker = blocked
    clock_values = iter((0.0, 899.95))
    orch._clock = lambda: next(clock_values, 1000.0)
    delivered = await asyncio.wait_for(
        orch.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS)), timeout=2,
    )
    audit = orch.audits[-1]
    result = {
        "case": f"cancel_{stage}" + ("_cleanup_failed" if cleanup_fails else ""),
        "entered": entered.is_set(),
        "networks_remaining": len(chain.docker.profile_fake.networks),
        "registered_networks_remaining": len(orch._attempt_networks),
        "pool_slots_remaining": len(orch._egress_pool._in_use),
        "rollout_containers_removed": len(chain.docker.removed),
        "cleanup_failure_steps": [f.step for f in audit.cleanup_failures],
        "reason_code": audit.outcome_v2["reason_code"],
        "all_aborted": all(s.remove_sample for s in delivered),
    }
    assert result["entered"] and result["all_aborted"]
    if cleanup_fails:
        assert result["networks_remaining"] == result["pool_slots_remaining"] == 1
        assert "remove_egress_network" in result["cleanup_failure_steps"]
    else:
        assert result["networks_remaining"] == result["pool_slots_remaining"] == result["registered_networks_remaining"] == 0
        assert not result["cleanup_failure_steps"]
    return result


async def main():
    results = [await runner_cancel()]
    results += [await resource_cancel(stage) for stage in ("create", "connect", "run")]
    results.append(await resource_cancel("create", cleanup_fails=True))
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
