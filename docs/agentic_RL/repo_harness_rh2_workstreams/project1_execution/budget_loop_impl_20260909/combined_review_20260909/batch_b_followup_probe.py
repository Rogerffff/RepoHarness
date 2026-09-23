"""B 针对性复核；复用历史探针的操作，保留原探针和原反例输出不动。

新的 baseline 用例独立检查不经 owner 取消即收口；旧函数的引导、浮点 timeout、
排队与跨 loop 操作直接复用，断言修后行为。无 Docker / CC / 推理服务调用。
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "batch_b_review"))

import orchestrator_probe as previous
import queue_deadline_probe as queue_previous


async def baseline_without_owner_cancel():
    chain = previous.short_chain()
    entered, cancelled = asyncio.Event(), asyncio.Event()

    async def census(*args, **kwargs):
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    started = time.monotonic()
    with patch.object(previous.baseline_census, "generate_baseline_manifest", census):
        leaves = await asyncio.wait_for(
            chain.orchestrator.generate(previous._Args(), chain.base_sample, dict(previous.SAMPLING_PARAMS)), timeout=3
        )
    audit = chain.orchestrator.audits[-1]
    result = {
        "case": "baseline_without_owner_cancel",
        "entered": entered.is_set(),
        "cancelled_by_episode_deadline": cancelled.is_set(),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "removed": len(chain.docker.removed),
        "networks_remaining": len(chain.docker.profile_fake.networks),
        "harness_calls": len(chain.driver.calls),
        "hit_by": audit.episode_deadline["hit_by"],
        "termination_kind": audit.outcome_v2["termination_kind"],
        "outcome_reason": audit.outcome_v2["reason_code"],
        "remove_sample": [x.remove_sample for x in leaves],
    }
    assert result["entered"] and result["cancelled_by_episode_deadline"]
    assert result["removed"] == 1 and result["networks_remaining"] == 0 and result["harness_calls"] == 0
    assert result["termination_kind"] == "hard_wall_timeout" and all(result["remove_sample"])
    return result


async def main():
    results = [await baseline_without_owner_cancel()]
    boot = await previous.bootstrap_cancel()
    assert boot["harness_launched"] is False and boot["hit_by"] == "bootstrap"
    assert boot["drain_calls"] == 0 and boot["finish_session_calls"] == 0 and boot["removed"] == 1
    assert boot["outcome_reason"] == "episode_deadline_in_bootstrap"
    results.append(boot)
    fatal = await previous.bootstrap_cancel(fatal_during_cancel=True)
    assert fatal["raised_reason"] == "probe_cancel_cleanup_fatal"
    assert fatal["notifications"] == ["probe_cancel_cleanup_fatal"] and fatal["removed"] == 1
    results.append(fatal)
    fractional = await previous.rounded_bootstrap_timeout()
    assert fractional["exec_timeout"] == [599.7] and fractional["return_code"] == -1
    results.append(fractional)
    for mode in ("deadline", "cancel"):
        queued = await queue_previous.queue_case(mode)
        assert queued["queue_wait"] > 0 and queued["capacity_restored"]
        results.append({"case": "queue_" + mode, **queued})
    results.append({"case": "cancel_acquire_races", **await queue_previous.cancel_acquire_races()})
    results.append({"case": "cross_loop_same_deadline", **await queue_previous.cross_loop_case()})
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
