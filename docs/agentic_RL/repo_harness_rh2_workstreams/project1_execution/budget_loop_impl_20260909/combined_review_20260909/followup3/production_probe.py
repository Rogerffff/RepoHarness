"""第三次窄复核：六项 fatal 的来源、通知时序与物化取消接缝；不调用 Docker。

复用维护夹具的外部接口替身，generate、真实物化、期限、receipt 与清理路径均不替换。
结论记录实际行为；已知反例断言也按实测现状冻结，不能当作业务应有行为的测试 oracle。
"""

from __future__ import annotations

import asyncio
import dataclasses
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "rh2/pyproject.toml").is_file())
for relative in ("reference/miles-rh2-integration", "rh2/src", "rh2/tests", "rh2/tests/adapters"):
    sys.path.insert(0, str(ROOT / relative))

from test_slime_generate import (  # noqa: E402
    FROZEN_IMG_DIGEST, SAMPLING_PARAMS, TASK_ID_DENSE, FakeFinalizationStore,
    FakeRolloutDocker, _Args, build_dense_chain, make_task,
)
from test_w1b_termination_facts_producer import _formal_chain  # noqa: E402
from repoharness2.adapters.slime.async_worker import FatalExecutionInfrastructureError  # noqa: E402
from repoharness2.shutdown.chain import LifecycleState  # noqa: E402


def profile_and_audit_seams() -> dict:
    """仅检查 R3/Z1 的直接生产数据接缝，不重复主审的停止归类或真 Docker 探针。"""
    from sandbox_test_support import make_grader_profile, make_rollout_profile, synthesize_inspect
    from repoharness2.adapters.slime.bringup import _termination_block
    from repoharness2.adapters.slime.sandbox_profile import (
        _facts_from_inspect, check_rollout_inspect, runtime_profile_digest,
    )

    rollout, grader = make_rollout_profile(), make_grader_profile()
    args = rollout.docker_run_args(name="review", network="review-network", image="review-image")
    inspect = synthesize_inspect(tuple(args), name="review")
    assert args.count("--init") == 1 and rollout.to_parameters()["init"] is True
    assert _facts_from_inspect(inspect)["init"] is True
    assert check_rollout_inspect(inspect, rollout, expected_network="review-network") == []
    inspect["HostConfig"]["Init"] = False
    failures = check_rollout_inspect(inspect, rollout, expected_network="review-network")
    assert len(failures) == 1 and "HostConfig.Init" in failures[0]
    record = {
        "schema_id": "rh2.runtime_profile_digest.v1",
        "rollout": rollout.to_parameters(), "grader": grader.to_parameters(),
    }
    record["rollout"].pop("init")
    prior_digest = "sha256:" + hashlib.sha256(
        json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    current_digest = runtime_profile_digest(rollout, grader)
    assert prior_digest != current_digest
    barrier = {"confirmed_at": 899.5, "residual": 0, "observations": []}
    block = _termination_block(SimpleNamespace(
        termination={"barrier_stop": barrier},
        outcome_v2={"termination_kind": "max_turns_exhausted"},
        termination_kind_hint="max_turns_exhausted",
    ))
    assert block["barrier_stop"] == barrier and block["kind"] == "max_turns_exhausted"
    return {
        "profile_has_init": True, "launch_argument_count": 1,
        "init_false_violations": failures,
        "runtime_digest": current_digest, "digest_without_init": prior_digest,
        "barrier_stop_survives_audit_projection": True,
    }


def make_chain(kind: str, *, mode: str = "fa_formal", deadline: float = 900):
    docker_kwargs = {}
    task = make_task(TASK_ID_DENSE)
    if kind.startswith("digest"):
        task = make_task(TASK_ID_DENSE, image_manifest_digest=FROZEN_IMG_DIGEST)
        if kind == "digest_query_failure":
            docker_kwargs["image_inspect_fail"] = True
        elif kind == "digest_match":
            docker_kwargs["repo_digests"] = ("fake/img@" + FROZEN_IMG_DIGEST,)
        else:
            docker_kwargs["repo_digests"] = ("fake/img@sha256:" + "2" * 64,)
    elif kind == "lineage_mismatch":
        docker_kwargs["probe_head"] = "f" * 40
    elif kind == "lineage_query_failure":
        docker_kwargs["probe_fail"] = True
    task = dataclasses.replace(task, time_budget_seconds=deadline)
    docker = FakeRolloutDocker(**docker_kwargs)
    store = FakeFinalizationStore(fail_put_bodies=(kind == "artifact_persist_failure"))
    if mode == "fa_formal":
        chain = _formal_chain(store, docker=docker, task=task)
    else:
        chain = build_dense_chain(docker=docker, task=task, finalization_store=store)
    if kind == "identity_incomplete":
        chain.base_sample.metadata.pop("rh2_member_slot", None)
    elif kind == "workspace_contract_invalid":
        # WorkspaceHandle 的真实 Pydantic 构造点：不注入已造好的 ValidationError。
        chain.orchestrator._mount_planner = lambda task: ["invalid-mount-shape"]
    return chain


async def run_case(kind: str, *, mode="fa_formal", rm_gate="none") -> dict:
    # 仅跨墙反例缩短配置预算；触发与取消仍由真实 asyncio 期限执行。
    deadline = 0.25 if rm_gate == "cross_deadline" else 900
    chain = make_chain(kind, mode=mode, deadline=deadline)
    state = LifecycleState()
    events = []
    entered_rm = asyncio.Event()
    release_rm = asyncio.Event()
    original_docker = chain.orchestrator._docker
    task_spec = chain.orchestrator._task_resolver

    def resolver(sample):
        # BringupService._resolve_task 的同一接缝，复用真实 LifecycleState 通知器。
        state.enter_execution(getattr(sample, "metadata", None))
        return task_spec

    def on_fatal(exc):
        events.append("fatal:" + exc.reason_code)

    def sink(audit):
        events.append("audit_sink")
        state.exit_execution()

    async def docker(*args, **kwargs):
        if args[0] == "rm":
            events.append("rm_enter")
            entered_rm.set()
            if rm_gate != "none":
                try:
                    await release_rm.wait()
                except asyncio.CancelledError:
                    events.append("rm_cancelled")
                    raise
            result = await original_docker(*args, **kwargs)
            events.append("rm_return")
            return result
        if args[:2] == ("network", "rm"):
            events.append("network_rm")
        return await original_docker(*args, **kwargs)

    state.on_fatal = on_fatal
    chain.orchestrator._task_resolver = resolver
    chain.orchestrator._audit_sink = sink
    chain.orchestrator._docker = docker
    args = _Args()
    params = dict(SAMPLING_PARAMS)
    if kind == "mask_missing":
        args.rh2_engine_sampling_mask = True
        params["top_k"] = 32
    generated = asyncio.create_task(chain.orchestrator.generate(args, chain.base_sample, params))
    during_cleanup = None
    if rm_gate != "none":
        await asyncio.wait_for(entered_rm.wait(), timeout=2.0)
        audit = chain.orchestrator.audits[-1]
        during_cleanup = {
            "fatal_notifications": len(state.fatal_seen),
            "receipt_count": len(chain.finalization.receipts),
            "failure_types": [f.error_type for f in audit.failure_records],
            "failure_details": [f.detail for f in audit.failure_records],
            "events": list(events),
        }
        if rm_gate == "release":
            release_rm.set()
    try:
        outputs = await asyncio.wait_for(generated, timeout=3.0)
    except FatalExecutionInfrastructureError as exc:
        terminal = {"result": "fatal", "reason": exc.reason_code}
    else:
        terminal = {
            "result": "returned", "status": str(outputs[0].status),
            "remove_sample": getattr(outputs[0], "remove_sample", None),
        }
    audit = chain.orchestrator.audits[-1]
    receipt = chain.finalization.receipts[0] if chain.finalization.receipts else None
    adapter = chain.adapter_ref.get("adapter")
    result = {
        "case": kind + ":" + mode + ":" + rm_gate,
        **terminal,
        "mode": chain.orchestrator._mode,
        "events": events,
        "during_cleanup": during_cleanup,
        "fatal_notifications": [e.reason_code for e in state.fatal_seen],
        "outcome_reason": (audit.outcome_v2 or {}).get("reason_code"),
        "outcome_completion": (audit.outcome_v2 or {}).get("completion_class"),
        "receipt_disposition": receipt.attempt_disposition if receipt else None,
        "receipt_reason": receipt.terminal_reason_code if receipt else None,
        "receipt_bodies_persisted": receipt.artifact_bodies_persisted if receipt else None,
        "receipt_cleanup_records": len(chain.finalization.cleanup_results),
        "failure_types": [f.error_type for f in audit.failure_records],
        "failure_details": [f.detail for f in audit.failure_records],
        "cleanup_steps": [f.step for f in audit.cleanup_failures],
        "cleanup_completed": any(e.step == "cleanup_completed" for e in audit.timeline),
        "lease_released": audit.lease_released,
        "containers_removed": len(chain.docker.removed),
        "private_networks_registered": len(chain.orchestrator._attempt_networks),
        "quarantine_count": len(chain.orchestrator.cleanup_quarantine),
        "opened_sessions": len(adapter.opened) if adapter else 0,
        "dropped_sessions": len(adapter.dropped) if adapter else 0,
        "grading_calls": len(chain.grading.calls),
        "inflight_after_audit": state.inflight_count,
    }
    assert result["cleanup_completed"] and result["inflight_after_audit"] == 0
    assert result["receipt_cleanup_records"] == 1
    if rm_gate == "cross_deadline":
        # 当前反例：物化异常清理被期限取消，首因 fatal 消失，容器与私网均残留。
        assert result["result"] == "returned" and result["status"] == "aborted", result
        assert result["outcome_reason"] == "episode_deadline_in_materialize", result
        assert result["receipt_disposition"] == "aborted" and not result["fatal_notifications"], result
        assert result["containers_removed"] == 0 and result["private_networks_registered"] == 1, result
    elif kind in {"digest_query_failure", "lineage_query_failure"}:
        expected = "rollout_image_digest_inspect_failed" if kind.startswith("digest") else "rollout_testbed_probe_failed"
        assert result["status"] == "aborted" and result["outcome_reason"] == expected, result
        assert not result["fatal_notifications"] and result["receipt_disposition"] == "aborted", result
    elif kind == "workspace_contract_invalid" and mode == "s1_compat":
        assert result["status"] == "aborted" and not result["fatal_notifications"], result
    elif kind == "digest_match":
        assert result["result"] == "returned" and not result["fatal_notifications"], result
        assert result["grading_calls"] == 1, result
    else:
        expected = {
            "digest_mismatch": "rollout_image_digest_mismatch",
            "lineage_mismatch": "rollout_testbed_lineage_failed",
            "identity_incomplete": "fa_identity_incomplete_in_formal_mode",
            "workspace_contract_invalid": "rh2_contract_validation_failed",
            "artifact_persist_failure": "frozen_artifact_persist_failed",
            "mask_missing": "sampling_mask_tape_missing_in_assembly",
        }[kind]
        assert result["reason"] == expected and result["fatal_notifications"] == [expected], result
        assert result["receipt_disposition"] == "fatal_run_halt" and result["receipt_reason"] == expected, result
        assert result["outcome_reason"] is None and result["grading_calls"] == 0, result
    if rm_gate != "cross_deadline" and kind != "identity_incomplete":
        assert result["containers_removed"] == 1 and result["lease_released"], result
        assert result["private_networks_registered"] == 0, result
    if result["opened_sessions"]:
        assert result["dropped_sessions"] == result["opened_sessions"], result
    print(json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
    return result


async def main():
    results = []
    for kind in ("digest_mismatch", "lineage_mismatch"):
        results.append(await run_case(kind, rm_gate="release"))
        results.append(await run_case(kind, rm_gate="cross_deadline"))
    for kind in (
        "identity_incomplete", "workspace_contract_invalid", "artifact_persist_failure", "mask_missing",
        "digest_query_failure", "lineage_query_failure", "digest_match",
    ):
        results.append(await run_case(kind))
    for kind in ("digest_mismatch", "lineage_mismatch", "mask_missing", "workspace_contract_invalid"):
        results.append(await run_case(kind, mode="s1_compat"))
    seams = profile_and_audit_seams()
    sources = (
        "rh2/src/repoharness2/adapters/slime/generate.py",
        "rh2/src/repoharness2/adapters/slime/outcome_producer.py",
        "rh2/src/repoharness2/shutdown/chain.py",
        "rh2/src/repoharness2/adapters/slime/bringup.py",
        "rh2/src/repoharness2/adapters/slime/quiescence_barrier.py",
        "rh2/src/repoharness2/adapters/slime/sandbox_profile.py",
    )
    payload = {
        "scope": "第三次窄复核的六项 fatal 与直接物化接缝；真实 Docker 不在本脚本范围",
        "cases": results,
        "direct_seams": seams,
        "source_digests": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sources},
        "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    Path(__file__).with_name("production_probe_result.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    asyncio.run(main())
