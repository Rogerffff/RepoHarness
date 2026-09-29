"""AR2/O1 窄复核：真实 manager/gateway，作者旧 SupplyDocker 替身。

不运行 Docker/HTTP 服务。人工 held-inflight 仅定位真实 gateway.release 的等待；
暂停 relay disconnect 仅定位 cleanup task 的拆网等待。输出保存在本目录。
"""
from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = next(p for p in HERE.parents if (p / "rh2/src/repoharness2/grading/manager.py").is_file())
sys.path[:0] = [str(REPO / "rh2/src"), str(REPO / "rh2/tests/grading"), str(REPO / "rh2/tests")]

from repoharness2.adapters.slime.pkg_index_gateway import PackageIndexGateway
from repoharness2.grading.manager import SWEGradingManager
from test_supply_two_stage_manager import RELAY, SupplyDocker, _grade, _manager, _two_stage_spec


class Gateway(PackageIndexGateway):
    def __init__(self, hold):
        super().__init__(upstream_simple_url="http://127.0.0.1:1/simple/")
        self.hold = hold
        self.entered = asyncio.Event()
        self.finish = asyncio.Event()
        self.work = []
        self.release_calls = 0

    def issue(self, grant):
        token = super().issue(grant)
        state = self._tokens[token]
        if self.hold:
            async def pending():
                try:
                    try:
                        await asyncio.Event().wait()
                    except asyncio.CancelledError:
                        await self.finish.wait()
                finally:
                    state.inflight.discard(asyncio.current_task())
            task = asyncio.create_task(pending())
            self.work.append(task)
            state.inflight.add(task)
        return token

    async def release(self, token, *, timeout=10):
        self.release_calls += 1
        self.entered.set()
        return await super().release(token, timeout=timeout)


class Docker(SupplyDocker):
    def __init__(self, *, pause_teardown=False, **kw):
        super().__init__(**kw)
        self.pause_teardown = pause_teardown
        self.teardown_entered = asyncio.Event()
        self.resume = asyncio.Event()
        self.teardown_calls = 0

    async def __call__(self, *args, input_bytes=None):
        if args[:2] == ("network", "disconnect") and args[-1] == RELAY.container_name:
            self.teardown_calls += 1
            self.teardown_entered.set()
            if self.pause_teardown:
                await self.resume.wait()
        return await super().__call__(*args, input_bytes=input_bytes)


def build(docker, gateway, name, limit=256):
    template = _manager(docker, gateway, HERE / f"tracer_{name}_logs")
    config = replace(template.config, container_history_limit=limit,
                     supply=replace(template.config.supply, release_timeout_seconds=0.05,
                                    teardown_timeout_seconds=0.05))
    return SWEGradingManager(config, docker=docker)


def snapshot(manager, docker, gateway):
    records = manager.container_records
    record = records[-1]
    ref = record.persisted_eval_log_ref or record.cancelled_eval_log_ref
    side = None
    if ref:
        path = manager.config.eval_log_dir / f"{ref.ref_id}.diagnostics.json"
        side = json.loads(path.read_text())["supply"]
    return {
        "tokens": gateway.active_token_count(), "networks": len(docker.profile_fake.networks),
        "slots": len(manager.config.supply.subnet_pool._in_use),
        "active_cleanup_tasks": sum(not t.done() for t in manager._supply_cleanup_tasks),
        "release_calls": gateway.release_calls, "teardown_calls": docker.teardown_calls,
        "record_count": len(records), "container_removed": record.removed,
        "cleanup_done": record.supply_cleanup is not None and record.supply_cleanup.done(),
        "supply_released": record.supply_released,
        "token_handle": record.supply_token is not None, "network_handle": record.supply_network is not None,
        "cleanup_failures": manager.cleanup_failures.copy(),
        "facts": dict(record.supply), "sidecar_supply": side,
    }


async def case(name, *, timeout=False, cancel=None, before_token=False):
    gateway = Gateway(hold=cancel in ("normal_release", "cleanup_release"))
    docker = Docker(pause_teardown=cancel == "teardown", install_delay=0.1 if timeout else 0,
                    **({"setup_exit_code": 3, "setup_attest": None} if before_token else {}))
    manager = build(docker, gateway, name)
    grade = asyncio.create_task(_grade(manager, spec=_two_stage_spec(test_timeout_seconds=0.01 if timeout else 5), traj=name))
    try:
        if cancel:
            entered = docker.teardown_entered if cancel == "teardown" else gateway.entered
            await asyncio.wait_for(entered.wait(), 2)
            grade.cancel()
        try:
            report = await asyncio.wait_for(grade, 2)
            outcome = {"returned": report.outcome, "reward": report.reward}
        except asyncio.CancelledError:
            outcome = {"raised": "CancelledError"}
        immediately = snapshot(manager, docker, gateway)
        docker.resume.set()
        closed = await asyncio.wait_for(manager.close(), 2)
        settled = snapshot(manager, docker, gateway)
        assert (settled["tokens"], settled["networks"], settled["slots"], settled["active_cleanup_tasks"]) == (0, 0, 0, 0)
        assert settled["supply_released"] and settled["sidecar_supply"] == settled["facts"]
        assert settled["facts"]["cleanup"] == "done" and closed["supply_open"] == []
        assert settled["release_calls"] == (0 if before_token else 1)
        assert settled["teardown_calls"] == 1
        return {"name": name, "outcome": outcome, "immediately": immediately, "after_close": settled,
                "close_supply_open": closed["supply_open"]}
    finally:
        docker.resume.set()
        gateway.finish.set()
        await asyncio.gather(*gateway.work, return_exceptions=True)


async def main():
    rows = []
    for name, kw in (
        ("normal", {}), ("install_timeout", {"timeout": True}),
        ("before_token", {"before_token": True}),
        ("cancel_normal_release", {"cancel": "normal_release"}),
        ("cancel_cleanup_release", {"timeout": True, "cancel": "cleanup_release"}),
        ("cancel_teardown", {"cancel": "teardown"}),
    ):
        rows.append(await case(name, **kw))
    output = HERE / "tracer_cleanup_owner_probe.json"
    output.write_text(json.dumps({"head": "a31cdcd0", "cases": rows}, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"cases": [{"name": r["name"], "outcome": r["outcome"],
                                 "resources_after_close": [r["after_close"][k] for k in ("tokens", "networks", "slots")],
                                 "cleanup_tasks_immediate": r["immediately"]["active_cleanup_tasks"],
                                 "token_release": r["after_close"]["facts"]["token_release"],
                                 "sidecar_equals_final_facts": r["after_close"]["sidecar_supply"] == r["after_close"]["facts"]}
                                for r in rows]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
