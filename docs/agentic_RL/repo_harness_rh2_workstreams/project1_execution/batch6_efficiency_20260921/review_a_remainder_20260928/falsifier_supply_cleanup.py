"""只跑 CPU：完整 manager 流程中，首次取消发生在容器删除后的网络收尾。

复跑（仓库根）：
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=rh2/src:rh2/tests:rh2/tests/grading \
  rh2/.venv/bin/python <本文件>

DockerRunner 和 gateway 使用已有窄测试替身；实际 manager、网络 helper、
记录退役及 close 均不替换。替身只在 teardown 的一次 Docker await 上挂起。
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path

from test_supply_two_stage_manager import (
    RELAY,
    FakeGateway,
    SupplyDocker,
    _grade,
    _manager,
)


class PauseTeardownDocker(SupplyDocker):
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


async def run_case(*, cancel_owner: bool, logs: Path) -> dict:
    docker, gateway = PauseTeardownDocker(), FakeGateway()
    manager = _manager(docker, gateway, logs)
    owner = asyncio.create_task(_grade(manager))
    await asyncio.wait_for(docker.entered.wait(), timeout=5)
    record = manager.container_records[-1]
    at_pause = {
        "container_removed": record.removed,
        "retired_seq": record.retired_seq,
        "supply_released": record.supply_released,
        "networks_remaining": len(docker.profile_fake.networks),
        "pool_in_use": len(manager.config.supply.subnet_pool._in_use),
        "test_started": "test_exec" in docker.order,
        "gateway_released_count": len(gateway.released),
    }
    if cancel_owner:
        owner.cancel()
    else:
        docker.resume.set()
    try:
        report = await owner
        result = {"owner": "returned", "outcome": report.outcome, "reward": report.reward}
    except asyncio.CancelledError:
        result = {"owner": "CancelledError"}

    close_report = await manager.close()
    result.update({
        "cancel_owner": cancel_owner,
        "at_teardown_pause": at_pause,
        "after_close": {
            "container_removed": record.removed,
            "supply_released": record.supply_released,
            "networks_remaining": len(docker.profile_fake.networks),
            "pool_in_use": len(manager.config.supply.subnet_pool._in_use),
            "teardown_calls": docker.teardown_calls,
            "network_teardown_fact": record.supply.get("network_teardown_failures"),
            "containers_open": close_report["containers_open"],
            "cleanup_failures": close_report["cleanup_failures"],
            "created_total": close_report["containers_created_total"],
            "removed_total": close_report["containers_removed_total"],
        },
    })
    return result


async def main() -> None:
    here = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix="falsifier_cleanup_logs_", dir=here) as tmp:
        evidence = {
            "head": "23f5586d",
            "mechanism": "actual manager + existing CPU Docker/gateway fixtures",
            "reachability": "conditional_future: GradingManagerConfig.supply 尚未正式启用",
            "cases": [
                await run_case(cancel_owner=False, logs=Path(tmp) / "control"),
                await run_case(cancel_owner=True, logs=Path(tmp) / "cancel"),
            ],
        }
    control, cancelled = evidence["cases"]
    assert control["outcome"] == "resolved" and control["reward"] == 1.0
    assert control["after_close"]["networks_remaining"] == 0
    assert cancelled["owner"] == "CancelledError"
    assert cancelled["after_close"]["networks_remaining"] == 1
    assert cancelled["after_close"]["pool_in_use"] == 1
    assert cancelled["after_close"]["teardown_calls"] == 1
    assert cancelled["after_close"]["cleanup_failures"] == []
    output = json.dumps(evidence, ensure_ascii=False, indent=2) + "\n"
    here.joinpath("falsifier_supply_cleanup.json").write_text(output)
    print(output, end="")


if __name__ == "__main__":
    asyncio.run(main())
