"""AR2/O1 有界独立复核：沿上一轮实际 manager 的网络收尾取消窗口复跑。

从仓库根运行：
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=rh2/src:rh2/tests:rh2/tests/grading \
  rh2/.venv/bin/python <本文件>

真实 manager、真实 gateway.release；Docker 是既有 CPU 替身。清理超时采用
维护测试的 0.3 s 配置，不改生产代码，不启动 Docker/HTTP。
"""

from __future__ import annotations

import asyncio
import json
import tempfile
import time
from pathlib import Path

from test_supply_cleanup_ownership import HeldGateway, _manager, _sidecar_supply
from test_supply_two_stage_manager import RELAY, SupplyDocker, _grade


class PauseAtTeardown(SupplyDocker):
    def __init__(self) -> None:
        super().__init__()
        self.entered = asyncio.Event()
        self.resume = asyncio.Event()
        self.teardown_calls = 0

    async def __call__(self, *args: str, input_bytes: bytes | None = None):
        if args[:2] == ("network", "disconnect") and args[-1] == RELAY.container_name:
            self.teardown_calls += 1
            self.entered.set()
            await self.resume.wait()
        return await super().__call__(*args, input_bytes=input_bytes)


def snapshot(manager, docker, gateway, logs: Path) -> dict:
    record = manager.container_records[-1]
    supply = _sidecar_supply(logs, record)
    return {
        "container_removed": record.removed,
        "supply_released": record.supply_released,
        "tokens": gateway.active_token_count(),
        "networks": len(docker.profile_fake.networks),
        "slots": len(manager.config.supply.subnet_pool._in_use),
        "cleanup_tasks_running": sum(not t.done() for t in manager._supply_cleanup_tasks),
        "teardown_calls": docker.teardown_calls,
        "sidecar": {k: supply.get(k) for k in ("token_release", "network_teardown", "cleanup")},
    }


async def close_and_record(manager) -> dict:
    started = time.monotonic()
    closed = await asyncio.wait_for(manager.close(), timeout=5)
    return {
        "seconds": round(time.monotonic() - started, 4),
        "supply_open_count": len(closed["supply_open"]),
        "containers_open_count": len(closed["containers_open"]),
        "cleanup_failure_kinds": sorted({s.split(":", 1)[0] for s in closed["cleanup_failures"]}),
    }


async def run_case(logs: Path, mode: str) -> dict:
    docker, gateway = PauseAtTeardown(), HeldGateway(hold=False)
    manager = _manager(docker, gateway, logs)
    owner = asyncio.create_task(_grade(manager))
    await asyncio.wait_for(docker.entered.wait(), timeout=5)
    record = manager.container_records[-1]
    paused_task = record.supply_cleanup
    if mode == "normal":
        docker.resume.set()
        report = await owner
        outcome = report.outcome
    else:
        owner.cancel()
        try:
            await owner
        except asyncio.CancelledError:
            outcome = "CancelledError"
        else:
            raise AssertionError("取消未传给 grade 调用方")
        assert not paused_task.done(), "grade 取消不应取消独立清理 task"
        assert record.supply_cleanup is paused_task
        if mode == "cancel_then_resume":
            docker.resume.set()
        else:
            docker.profile_fake.network_rm_fail_for = ("*",)

    first_close = await close_and_record(manager)
    first_state = snapshot(manager, docker, gateway, logs)
    second_close = await close_and_record(manager)
    second_state = snapshot(manager, docker, gateway, logs)

    if mode == "cancel_then_timeout":
        assert first_close["supply_open_count"] == second_close["supply_open_count"] == 1
        assert first_state["sidecar"]["cleanup"] == second_state["sidecar"]["cleanup"] == "incomplete"
        assert second_state["networks"] == second_state["slots"] == 1
        assert "supply_resources_open_at_close" in second_close["cleanup_failure_kinds"]
        docker.profile_fake.network_rm_fail_for = ()
        docker.resume.set()
        final_close = await close_and_record(manager)
    else:
        assert first_close["supply_open_count"] == second_close["supply_open_count"] == 0
        assert second_state["teardown_calls"] == 1, "重复 close 不应重新拆已释放网络"
        final_close = second_close
    final_state = snapshot(manager, docker, gateway, logs)
    assert final_state["tokens"] == final_state["networks"] == final_state["slots"] == 0
    assert final_state["cleanup_tasks_running"] == 0
    assert final_state["supply_released"] and final_state["sidecar"]["cleanup"] == "done"
    assert gateway.summary()["totals"]["tokens_released"] == 1
    return {
        "mode": mode,
        "grade_result": outcome,
        "first_close": first_close,
        "first_state": first_state,
        "second_close": second_close,
        "second_state": second_state,
        "final_close": final_close,
        "final_state": final_state,
        "gateway_tokens_released": gateway.summary()["totals"]["tokens_released"],
    }


async def main() -> None:
    here = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix="main_replay_logs_", dir=here) as tmp:
        evidence = {
            "head": "a31cdcd0",
            "scope": "CPU actual manager + real gateway.release + existing Docker fixture",
            "cases": [
                await run_case(Path(tmp) / mode, mode)
                for mode in ("normal", "cancel_then_resume", "cancel_then_timeout")
            ],
        }
    output = json.dumps(evidence, ensure_ascii=False, indent=2) + "\n"
    here.joinpath("main_replay_cleanup.json").write_text(output)
    print(output, end="")


if __name__ == "__main__":
    asyncio.run(main())
