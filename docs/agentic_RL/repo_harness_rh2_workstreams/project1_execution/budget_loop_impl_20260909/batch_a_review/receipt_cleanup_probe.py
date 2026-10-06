"""批 A I12 的独立 CPU 探针：真实编排/会话包装，Docker 与持久化均为替身。"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(REPO / "rh2/tests/adapters"))

from test_b5_finalization import _formal_chain  # noqa: E402
from test_slime_generate import FakeFinalizationStore, SAMPLING_PARAMS, _Args  # noqa: E402

from repoharness2.adapters.slime.async_worker import FatalExecutionInfrastructureError  # noqa: E402
from repoharness2.adapters.slime.bringup import make_per_rollout_adapter  # noqa: E402
from repoharness2.adapters.slime.capture_wire import CaptureRegistry  # noqa: E402
from repoharness2.adapters.slime.generate import SlimeBindingError  # noqa: E402
from repoharness2.shutdown.chain import LifecycleState  # noqa: E402


async def run_case(
    name: str,
    *,
    primary_fatal: bool = False,
    drop_failure: bool = False,
    rm_failure: str | None = None,
    audit_failure: bool = False,
    pause_drop: bool = False,
    after_release: bool = False,
) -> dict:
    store = FakeFinalizationStore(fail_persist_receipt=True)
    crash = None if after_release else (
        FatalExecutionInfrastructureError("probe_primary_fatal", "探针首因")
        if primary_fatal
        else SlimeBindingError("harness_bootstrap_failed", "已归因的引导故障")
    )
    chain = _formal_chain(store, crash=crash, rm_fail=rm_failure == "nonzero")
    lifecycle = LifecycleState()
    events = []
    releases = []
    snapshots = []
    registry = CaptureRegistry()
    drop_entered = asyncio.Event()
    release_drop = asyncio.Event()
    original_task = chain.orchestrator._task_resolver
    original_docker = chain.orchestrator._docker
    original_factory = chain.orchestrator._adapter_factory

    def resolve(sample):
        lifecycle.enter_execution(sample.metadata)
        return original_task

    def notify(exc):
        events.append("notify:" + exc.reason_code)
        lifecycle.stop_intake()

    def audit_sink(audit):
        try:
            events.append("audit_sink")
            snapshots.append({
                "failure_codes": [f.error_type for f in audit.failure_records],
                "cleanup_steps": [f.step for f in audit.cleanup_failures],
                "lease_released": audit.lease_released,
            })
            if audit_failure:
                raise OSError("探针 audit sink 故障")
        finally:
            lifecycle.exit_execution()

    def poison_release(sid):
        releases.append(sid)
        registry.poison.release(sid)

    async def docker(*args, **kwargs):
        if args[0] == "rm":
            events.append("docker_rm")
            if rm_failure == "exception":
                raise OSError("探针 Docker socket 故障")
        return await original_docker(*args, **kwargs)

    async def drop(sid, *, wait_timeout=5.0):
        events.append("drop_enter")
        registry.poison.poison(sid, "probe_existing_poison")
        drop_entered.set()
        if pause_drop:
            await release_drop.wait()
        if drop_failure:
            raise RuntimeError("探针 shared adapter drop 故障")
        events.append("drop_return")

    class SharedAdapter:
        def open_session(self, *args, **kwargs):
            pass

        drop_session = staticmethod(drop)

    def factory(hook, defaults):
        if after_release:
            adapter = original_factory(hook, defaults)
            adapter.drop_session = drop
            return adapter
        return make_per_rollout_adapter(registry, SharedAdapter(), hook)

    lifecycle.on_fatal = notify
    chain.orchestrator._task_resolver = resolve
    chain.orchestrator._adapter_factory = factory
    chain.orchestrator._docker = docker
    chain.orchestrator._audit_sink = audit_sink
    chain.orchestrator._session_poison_release = poison_release
    task = asyncio.create_task(
        chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    )
    checkpoint = None
    if pause_drop:
        await asyncio.wait_for(drop_entered.wait(), 2)
        audit = chain.orchestrator.audits[0]
        checkpoint = {
            "receipt_failure_recorded": any(
                f.error_type == "finalization_receipt_write_failed" for f in audit.failure_records
            ),
            "fatal_notifications": [getattr(exc, "reason_code", type(exc).__name__) for exc in lifecycle.fatal_seen],
            "accepting": lifecycle.accepting,
            "container_removed": bool(chain.docker.removed),
        }
        release_drop.set()
    try:
        await asyncio.wait_for(task, 2)
    except FatalExecutionInfrastructureError as exc:
        final_code = exc.reason_code
    else:
        raise AssertionError("receipt 失败未导致预期 fatal")
    audit = chain.orchestrator.audits[0]
    sid = audit.session_id
    expected_primary = "probe_primary_fatal" if primary_fatal else "finalization_receipt_write_failed"
    assert final_code == expected_primary, (name, final_code)
    assert not store.cleanup_results, name
    assert not releases, name
    assert registry.poison.reason(sid) == "probe_existing_poison", name
    if not after_release:
        assert not registry.hooks, name
        assert not registry._capability_tokens, name
    if rm_failure:
        assert chain.orchestrator.cleanup_quarantine == [audit.lease.container_id], name
        assert not audit.lease_released, name
    else:
        assert not chain.orchestrator.cleanup_quarantine, name
        assert audit.lease_released and len(chain.docker.removed) == 1, name
    assert snapshots, name
    return {
        "name": name,
        "checkpoint": checkpoint,
        "final_code": final_code,
        "notifications": [getattr(exc, "reason_code", type(exc).__name__) for exc in lifecycle.fatal_seen],
        "events": events,
        "failure_codes": [f.error_type for f in audit.failure_records],
        "cleanup_steps": [f.step for f in audit.cleanup_failures],
        "lease_released": audit.lease_released,
        "quarantine_count": len(chain.orchestrator.cleanup_quarantine),
        "poison_release_count": len(releases),
        "registry_unregistered": not registry.hooks,
        "cleanup_append_count": len(store.cleanup_results),
    }


async def main():
    results = []
    for name, kwargs in [
        ("receipt_only_pause", {"pause_drop": True}),
        ("receipt_and_drop_error", {"drop_failure": True}),
        ("receipt_and_rm_nonzero", {"rm_failure": "nonzero"}),
        ("receipt_and_rm_exception", {"rm_failure": "exception"}),
        ("primary_fatal_and_receipt_and_cleanup_errors", {
            "primary_fatal": True, "drop_failure": True,
            "rm_failure": "exception", "audit_failure": True, "pause_drop": True,
        }),
        ("after_early_release", {"after_release": True}),
        ("after_release_and_drop_error", {"after_release": True, "drop_failure": True}),
    ]:
        results.append(await run_case(name, **kwargs))
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
