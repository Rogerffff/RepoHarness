"""批 B 主审 CPU 探针：期限覆盖、真实驱动引导取消、取消时致命异常的传播。"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "rh2/pyproject.toml").is_file())
sys.path.insert(0, str(ROOT / "rh2/src"))
sys.path.insert(0, str(ROOT / "rh2/tests/adapters"))

from test_w1b_termination_facts_producer import _formal_chain
from test_slime_generate import _Args, SAMPLING_PARAMS
from repoharness2.adapters.slime import baseline_census
from repoharness2.adapters.slime import bringup, docker_sandbox
from repoharness2.adapters.slime.bringup import ClaudeCodeDriver
from repoharness2.adapters.slime.async_worker import FatalExecutionInfrastructureError
from repoharness2.adapters.slime.generate import HARNESS_LAUNCH_FACTS


def short_chain():
    chain = _formal_chain()
    chain.orchestrator._task_resolver = replace(
        chain.orchestrator._task_resolver, time_budget_seconds=1
    )
    return chain


async def baseline_wait():
    chain = short_chain()
    entered = asyncio.Event()
    cancelled = asyncio.Event()

    async def census(*args, **kwargs):
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    with patch.object(baseline_census, "generate_baseline_manifest", census):
        running = asyncio.create_task(chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS)))
        await asyncio.wait_for(entered.wait(), timeout=2)
        audit = chain.orchestrator.audits[-1]
        await asyncio.sleep(max(0, audit.episode_deadline_monotonic - time.monotonic()) + 0.05)
        result = {
            "case": "baseline_wait_after_episode_deadline",
            "over_deadline": time.monotonic() > audit.episode_deadline_monotonic,
            "execution_pending": not running.done(),
            "census_cancelled_by_deadline": cancelled.is_set(),
            "removed_before_owner_cancel": len(chain.docker.removed),
            "hit_by": audit.episode_deadline["hit_by"],
        }
        running.cancel()
        try:
            await asyncio.wait_for(running, timeout=2)
        except asyncio.CancelledError:
            pass
        result["removed_after_owner_cancel"] = len(chain.docker.removed)
    assert result["over_deadline"] and result["execution_pending"]
    assert not result["census_cancelled_by_deadline"]
    return result


async def bootstrap_cancel(*, fatal_during_cancel=False):
    chain = short_chain()
    chain.orchestrator._harness_driver = ClaudeCodeDriver()
    notices = []
    chain.orchestrator._notify_fatal_halt = notices.append
    entered = asyncio.Event()
    drain_calls = []
    original_drain = chain.orchestrator._session_drain_owner

    async def drain(sid):
        drain_calls.append(sid)
        return await original_drain(sid)

    chain.orchestrator._session_drain_owner = drain

    async def install(self, sb, **kwargs):
        entered.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            if fatal_during_cancel:
                raise FatalExecutionInfrastructureError("probe_cancel_cleanup_fatal", "取消时的明确致命错误")
            raise

    with patch.object(ClaudeCodeDriver, "_install_native_cli", install):
        try:
            delivered = await asyncio.wait_for(
                chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS)), timeout=3
            )
            outcome = {"returned": True, "sample_status": [str(x.status) for x in delivered]}
        except Exception as exc:
            outcome = {"raised": type(exc).__name__, "raised_reason": getattr(exc, "reason_code", None)}
    audit = chain.orchestrator.audits[-1]
    result = {
        "case": "bootstrap_fatal_during_cancel" if fatal_during_cancel else "bootstrap_outer_cancel",
        "install_entered": entered.is_set(),
        "harness_launched": audit.episode_deadline["harness_launched"],
        "hit_by": audit.episode_deadline["hit_by"],
        "drain_calls": len(drain_calls),
        "finish_session_calls": len(chain.adapter_ref["adapter"].finished),
        "outcome_reason": (audit.outcome_v2 or {}).get("reason_code"),
        "termination_kind": (audit.outcome_v2 or {}).get("termination_kind"),
        "notifications": [n.reason_code for n in notices],
        "failure_records": [{"type": x.error_type, "detail": x.detail[:150]} for x in audit.failure_records],
        "removed": len(chain.docker.removed),
        **outcome,
    }
    assert result["install_entered"]
    return result


async def main():
    print(json.dumps(await baseline_wait(), ensure_ascii=False))
    print(json.dumps(await bootstrap_cancel(), ensure_ascii=False))
    print(json.dumps(await bootstrap_cancel(fatal_during_cancel=True), ensure_ascii=False))
    print(json.dumps(await rounded_bootstrap_timeout(), ensure_ascii=False))


async def rounded_bootstrap_timeout():
    now = [0.0]
    seen = []

    async def install(self, sb, **kwargs):
        now[0] += 0.3

    async def run(*args, timeout=None, **kwargs):
        seen.append(timeout)
        now[0] += timeout
        return 124, "", "按收到的 timeout 到点"

    facts = {}
    token = HARNESS_LAUNCH_FACTS.set(facts)
    try:
        with (
            patch.object(bringup, "time", SimpleNamespace(monotonic=lambda: now[0])),
            patch.object(ClaudeCodeDriver, "_install_native_cli", install),
            patch.object(docker_sandbox, "_run", run),
        ):
            try:
                code = await ClaudeCodeDriver().run(
                    SimpleNamespace(container_name="cpu"), workdir="/testbed", session_id="s", adapter_url="http://cpu",
                    time_budget_sec=600, prompt="p",
                )
                outcome = {"return_code": code}
            except Exception as exc:
                outcome = {"raised_reason": getattr(exc, "reason_code", None)}
    finally:
        HARNESS_LAUNCH_FACTS.reset(token)
    return {"case": "rounded_bootstrap_timeout", "exec_timeout": seen, "remaining": round(600-now[0], 3), "facts": facts, **outcome}


if __name__ == "__main__":
    asyncio.run(main())
