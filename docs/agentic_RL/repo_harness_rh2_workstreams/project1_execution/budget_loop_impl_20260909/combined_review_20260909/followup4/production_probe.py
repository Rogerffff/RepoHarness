"""第四次窄复核：已通知 Fatal 在既有关停宽限结束时的局部对照。

只运行真实编排、LifecycleState 与 close_inflight_executions；外部 Docker、harness、
工件存储用维护夹具。回调只接真实关停的 intake_stop / inflight 两步，不启动整个服务。
物化 digest 矛盾与本轮前已存在的工件持久化 Fatal 共用同一慢 rm，验证是否为 F1 独有回归。
不跑 Docker / Claude Code / 模型服务，不改 helper 的判断或返回值。
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "rh2/pyproject.toml").is_file())
for relative in ("reference/miles-rh2-integration", "rh2/src", "rh2/tests", "rh2/tests/adapters"):
    sys.path.insert(0, str(ROOT / relative))

from test_slime_generate import (  # noqa: E402
    FROZEN_IMG_DIGEST, SAMPLING_PARAMS, TASK_ID_DENSE,
    FakeFinalizationStore, FakeRolloutDocker, _Args, make_task,
)
from test_w1b_termination_facts_producer import _formal_chain  # noqa: E402
from repoharness2.adapters.slime.generate import rh2_custom_generate  # noqa: E402
from repoharness2.shutdown.chain import LifecycleState, close_inflight_executions  # noqa: E402


async def run_case(kind: str) -> dict:
    materialize_case = kind == "materialize_digest"
    task_spec = make_task(
        TASK_ID_DENSE,
        **({"image_manifest_digest": FROZEN_IMG_DIGEST} if materialize_case else {}),
    )
    docker = FakeRolloutDocker(repo_digests=("fake/img@sha256:" + "2" * 64,))
    store = FakeFinalizationStore(fail_put_bodies=not materialize_case)
    chain = _formal_chain(store, docker=docker, task=task_spec)
    state = LifecycleState()
    events: list[str] = []
    close_tasks: list[asyncio.Task] = []
    first_reason: list[str] = []
    at_rm: list[dict] = []
    original_docker = chain.orchestrator._docker

    def resolver(sample):
        state.enter_execution(getattr(sample, "metadata", None), task_id=task_spec.task_id)
        return task_spec

    def on_fatal(exc):
        events.append("fatal")
        first_reason.append(exc.reason_code)
        state.stop_intake()
        events.append("intake_stop")
        close_tasks.append(asyncio.create_task(close_inflight_executions(
            state, grace_seconds=0.05, cancel_wait_seconds=0.5,
        )))

    def sink(audit):
        events.append("audit_sink")
        state.exit_execution()

    async def slow_rm(*args, **kwargs):
        if args[0] == "rm":
            audit = chain.orchestrator.audits[-1]
            events.append("rm_enter")
            at_rm.append({
                "notification_count": len(state.fatal_seen),
                "receipt_dispositions": [r.attempt_disposition for r in store.receipts],
                "receipt_reasons": [r.terminal_reason_code for r in store.receipts],
                "workspace_handle_ready": audit.workspace_handle is not None,
            })
            try:
                await asyncio.sleep(0.2)
            except asyncio.CancelledError:
                events.append("rm_cancelled")
                raise
        return await original_docker(*args, **kwargs)

    chain.orchestrator._task_resolver = resolver
    chain.orchestrator._audit_sink = sink
    chain.orchestrator._docker = slow_rm
    state.on_fatal = on_fatal
    args = _Args()
    args.rh2_orchestrator = chain.orchestrator
    running = asyncio.create_task(rh2_custom_generate(args, chain.base_sample, dict(SAMPLING_PARAMS)))
    try:
        await asyncio.wait_for(running, timeout=3)
        returned = "delivered"
    except asyncio.CancelledError:
        returned = "CancelledError"
    close_facts = await asyncio.wait_for(close_tasks[0], timeout=1)
    audit = chain.orchestrator.audits[-1]
    expected = "rollout_image_digest_mismatch" if materialize_case else "frozen_artifact_persist_failed"
    result = {
        "case": kind,
        "expected_original_reason": expected,
        "events": events,
        "at_first_cleanup": at_rm,
        "run_level_cancel_result": returned,
        "intake_accepting": state.accepting,
        "first_reason": first_reason,
        "fatal_notifications": [e.reason_code for e in state.fatal_seen],
        "receipt_dispositions": [r.attempt_disposition for r in store.receipts],
        "receipt_reasons": [r.terminal_reason_code for r in store.receipts],
        "outcome_v2": audit.outcome_v2,
        "lease_released": audit.lease_released,
        "removed_containers": len(docker.removed),
        "attempt_networks": len(chain.orchestrator._attempt_networks),
        "cleanup_appends": len(store.cleanup_results),
        "cleanup_failures": [f.step for f in audit.cleanup_failures],
        "quarantined_containers": len(chain.orchestrator.cleanup_quarantine),
        "episode_hit_by": audit.episode_deadline["hit_by"],
        "close_inflight_facts": close_facts,
        "production_defaults": {"inflight_grace_seconds": 30, "cleanup_timeout_seconds": 120},
        "probe_scaled_waits": {"inflight_grace_seconds": 0.05, "docker_rm_seconds": 0.2},
    }
    assert result["fatal_notifications"] == [expected]
    assert result["receipt_dispositions"] == ["fatal_run_halt"]
    assert result["receipt_reasons"] == [expected]
    assert result["episode_hit_by"] == "none" and result["outcome_v2"] is None
    assert result["intake_accepting"] is False and returned == "CancelledError"
    assert events.index("fatal") < events.index("rm_enter") < events.index("rm_cancelled")
    assert result["lease_released"] is False and result["cleanup_appends"] == 0
    assert close_facts["cancelled"][0]["finished_after_cancel"] is True
    return result


async def main() -> None:
    results = [await run_case("materialize_digest"), await run_case("existing_artifact_fatal")]
    payload = {
        "scope": "真实编排与既有关停 inflight 步的两案局部对照；非完整 Bringup 关停验收",
        "cases": results,
        "conclusion": "两案均已通知、receipt 保留原 Fatal；run 级宽限取消会中断清理，但没有生成普通 ABORTED。",
    }
    output = Path(__file__).with_name("production_probe.json")
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
