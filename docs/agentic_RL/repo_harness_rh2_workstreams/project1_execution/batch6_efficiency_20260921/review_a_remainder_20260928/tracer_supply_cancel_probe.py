"""有界 CPU 探针：真实 manager + 真实 gateway.release；Docker 用作者已有替身。

不启服务、不连接上游、不调用 Docker。唯一人工边界是把一条在途 task 放进
gateway 的实际 inflight 集合，并在它被撤销后暂缓完成，以确定性命中 release
的真实 asyncio.wait。此处只核 manager 的 owner 运输；HTTP 请求行为由主审另验。
输出只写本文件所在目录的 tracer_* 文件。
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = next(p for p in HERE.parents if (p / "rh2/src/repoharness2/grading/manager.py").is_file())
sys.path[:0] = [str(REPO / "rh2/src"), str(REPO / "rh2/tests/grading"), str(REPO / "rh2/tests")]

from repoharness2.adapters.slime.pkg_index_gateway import PackageIndexGateway
from test_supply_two_stage_manager import SupplyDocker, _grade, _manager, _two_stage_spec


class ObservedGateway(PackageIndexGateway):
    def __init__(self, *, hold_inflight: bool):
        super().__init__(upstream_simple_url="http://127.0.0.1:1/simple/")
        self.hold_inflight = hold_inflight
        self.release_entered = asyncio.Event()
        self.allow_inflight_finish = asyncio.Event()
        self.owned_tasks = []
        self.release_calls = 0

    def issue(self, grant):
        token = super().issue(grant)
        state = self._tokens[token]
        if self.hold_inflight:
            async def held_inflight():
                try:
                    try:
                        await asyncio.Event().wait()
                    except asyncio.CancelledError:
                        await self.allow_inflight_finish.wait()
                finally:
                    state.inflight.discard(asyncio.current_task())

            task = asyncio.create_task(held_inflight())
            state.inflight.add(task)
            self.owned_tasks.append(task)
        return token

    async def release(self, token, *, timeout=10.0):
        self.release_calls += 1
        self.release_entered.set()
        return await super().release(token, timeout=timeout)


async def run_case(name: str, *, install_timeout: bool, cancel_release: bool):
    gateway = ObservedGateway(hold_inflight=cancel_release)
    docker = SupplyDocker(install_delay=0.1 if install_timeout else 0.0)
    logs = HERE / f"tracer_supply_cancel_{name}_logs"
    manager = _manager(docker, gateway, logs)
    spec = _two_stage_spec(test_timeout_seconds=0.01 if install_timeout else 10.0)
    task = asyncio.create_task(_grade(manager, spec=spec, traj=f"tracer-{name}"))
    try:
        if cancel_release:
            await asyncio.wait_for(gateway.release_entered.wait(), timeout=2.0)
            assert any(s.releasing and s.inflight for s in gateway._tokens.values())
            task.cancel()  # 每案只有一次外部取消；timeout 案已进入普通失败后的 finally。
        try:
            report = await asyncio.wait_for(task, timeout=3.0)
            outcome = {"returned": report.outcome, "reward": report.reward,
                       "infra": report.infra_failure_detail}
        except asyncio.CancelledError:
            outcome = {"raised": "CancelledError"}
        record = manager.container_records[-1]

        def snapshot():
            return {
                "container_removed": record.removed,
                "supply_released": record.supply_released,
                "manager_has_token_handle": record.supply_token is not None,
                "gateway_tokens": gateway.active_token_count(),
                "gateway_states": [{"state": s.state, "releasing": s.releasing,
                                    "inflight": len(s.inflight)} for s in gateway._tokens.values()],
                "release_calls": gateway.release_calls,
                "network_count": len(docker.profile_fake.networks),
                "subnet_slots": len(manager.config.supply.subnet_pool._in_use),
                "cleanup_failures": list(manager.cleanup_failures),
                "supply_fact_keys": sorted(record.supply),
                "test_started": "test_exec" in docker.order,
            }

        before_close = snapshot()
        closed = await manager.close()
        after_close = snapshot()
        return {"case": name, "outcome": outcome, "before_close": before_close,
                "after_close": after_close, "close_report": closed, "order": docker.order}
    finally:
        gateway.allow_inflight_finish.set()
        await asyncio.gather(*gateway.owned_tasks, return_exceptions=True)


async def main():
    cases = []
    for name, timed_out, cancelled in (
        ("normal_control", False, False),
        ("cancel_normal_release", False, True),
        ("timeout_control", True, False),
        ("cancel_timeout_cleanup_release", True, True),
    ):
        cases.append(await run_case(name, install_timeout=timed_out, cancel_release=cancelled))
    result = {"scope": "real manager/real gateway release; fake Docker; one artificial inflight drain delay; no network",
              "cases": cases}
    output = HERE / "tracer_supply_cancel_probe.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
