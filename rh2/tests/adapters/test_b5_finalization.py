"""B5 验收（05 计划 5a 节）：
① receipt 前 cleanup 不发生（正序 + persist 失败 run-halt；**批 A I12（06 A4，2026-09-09）**：
   persist 失败后 cleanup 照常执行，容器只在清理失败时进隔离队列，不再"保留现场"）——**W3a（决策包 D2-1）
   修订**：rollout 容器在 artifact 本体持久化成功后**立即释放**（早于评分、早于 receipt），
   "receipt 之后才 cleanup"对容器移除只在**未冻结/未持久化**的 attempt 上仍成立；session drop /
   poison release / cleanup 追加记录仍在 receipt 之后。两种形态各有测试。
② cleanup failure 追加、不覆盖首因（独立记录，receipt 不改写）；
③ F2-4 可复用 receipt 字段（outcome_v2 typed / delivery_prepared 定界 / digest 引用）；
另：artifact 本体持久化失败 = T0 失败表第 1 行（missing 收口）；
S1 无 store 行为逐字不变；FileFinalizationStore 原子写单元测试。
"""

from __future__ import annotations

import base64
import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_f2_2_capability import _stamp_fa_identity  # noqa: E402
from test_slime_generate import (  # noqa: E402
    SAMPLING_PARAMS,
    FakeFinalizationStore,
    _Args,
    _formal_config,
    build_dense_chain,
    dense_turns,
)

from repoharness2.adapters.slime import generate as generate_mod  # noqa: E402
from repoharness2.adapters.slime.async_worker import (  # noqa: E402
    FatalExecutionInfrastructureError,
)
from repoharness2.adapters.slime.generate import QuiescenceConfirmed, SlimeBindingError  # noqa: E402
from repoharness2.envpack.termination_facts import TerminationFactsError  # noqa: E402


class _FrozenWs:
    def __init__(self, underlying):
        self._u = underlying

    async def run_bash(self, script):
        return await self._u.run_bash(script)


class _Barrier:
    async def establish(self, *, workspace, audit):
        return QuiescenceConfirmed(
            frozen_grading_workspace=_FrozenWs(workspace),
            snapshot_ref="sha256:abc", evidence_refs=("s",))


def _formal_chain(store: FakeFinalizationStore | None = None, **kwargs):
    turns = dense_turns()
    for t in turns:
        t.response["meta_info"]["weight_version"] = "5"
    chain = build_dense_chain(
        config=_formal_config(policy_version="5", execution_mode="fa_formal"),
        runtime_quiescence_barrier=_Barrier(), turns=turns,
        finalization_store=store, **kwargs)
    _stamp_fa_identity(chain.base_sample)
    return chain


def _log_docker_rm(chain):
    """把 docker rm 调用插进 store.call_order（跨对象排序证据）。"""

    orig = chain.orchestrator._docker

    async def logging_docker(*args, **kw):
        if args and args[0] == "rm":
            chain.finalization.call_order.append("docker_rm")
        return await orig(*args, **kw)

    chain.orchestrator._docker = logging_docker


# ------------------------------------------- ① 持久化 → 释放容器 → 评分 → receipt → 追加
async def test_artifact_persist_then_release_then_grading_then_receipt_then_append():
    """W3a（D2-1，T1 oracle 改动，原 test_receipt_persists_before_any_cleanup 断言
    persist_receipt < docker_rm）：正式顺序 = put_artifact_bodies < docker_rm（释放 rollout
    容器）< grading_submit < persist_receipt < append_cleanup_result。"""

    chain = _formal_chain()
    _log_docker_rm(chain)
    orig_submit = chain.orchestrator._grading_submit

    async def logging_submit(**kw):
        chain.finalization.call_order.append("grading_submit")
        return await orig_submit(**kw)

    chain.orchestrator._grading_submit = logging_submit
    await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    order = chain.finalization.call_order
    assert order == [
        "put_artifact_bodies", "docker_rm", "grading_submit", "persist_receipt", "append_cleanup_result",
    ]
    audit = chain.orchestrator.audits[0]
    assert audit.rollout_container_released_before_grading is True and audit.lease_released is True
    assert len(chain.docker.removed) == 1  # finally 的 cleanup 幂等，不再 rm 第二次


async def test_receipt_persist_failure_before_release_cleans_up_and_run_halts():
    """T0 失败表第 2 行（未冻结形态）：harness 引导失败 → 容器从未释放 → receipt 写失败 →
    仍 run halt，**但 cleanup 照常**（批 A I12 / 06 A4 T1 oracle 改动：此前"不清理 + 容器入
    隔离队列保留现场"）：docker rm 在 persist_receipt 之后发生、隔离队列为空、poison 不释放；
    cleanup 追加记录仍不发生（无 receipt 就无追加对象）。"""

    store = FakeFinalizationStore(fail_persist_receipt=True)
    chain = _formal_chain(
        store, crash=SlimeBindingError("harness_bootstrap_failed", "docker exec failed (exit=1)")
    )
    _log_docker_rm(chain)
    with pytest.raises(FatalExecutionInfrastructureError,
                       match="finalization_receipt_write_failed"):
        await chain.orchestrator.generate(
            _Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    order = store.call_order
    assert order.index("persist_receipt") < order.index("docker_rm")  # receipt 失败后仍清理
    assert store.cleanup_results == []  # 无 receipt 就无追加
    assert chain.orchestrator.cleanup_quarantine == []  # 容器已清，无需隔离
    audit = chain.orchestrator.audits[0]
    assert audit.rollout_container_released_before_grading is False
    assert audit.lease_released is True and len(chain.docker.removed) == 1
    steps = [e.step for e in audit.timeline]
    assert "cleanup_started" in steps and "cleanup_completed" in steps
    assert "cleanup_skipped_receipt_failure" not in steps
    assert any(f.error_type == "finalization_receipt_write_failed"
               for f in audit.failure_records)


async def test_receipt_persist_failure_with_container_rm_failure_quarantines_and_still_halts():
    """批 A I12：receipt 写失败且清理本身也失败（docker rm 非零）→ 首因仍是
    finalization_receipt_write_failed；容器**此时才**进隔离队列，cleanup_failures 留痕。"""

    store = FakeFinalizationStore(fail_persist_receipt=True)
    chain = _formal_chain(
        store, crash=SlimeBindingError("harness_bootstrap_failed", "docker exec failed (exit=1)"),
        rm_fail=True,
    )
    with pytest.raises(FatalExecutionInfrastructureError,
                       match="finalization_receipt_write_failed"):
        await chain.orchestrator.generate(
            _Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert audit.lease_released is False
    steps = [f.step for f in audit.cleanup_failures]
    assert steps == ["finalization_receipt_write_failed", "remove_container"]  # 首因在前，rm 失败留痕
    assert chain.orchestrator.cleanup_quarantine == [audit.lease.container_id]


async def test_receipt_persist_failure_after_release_run_halts_without_quarantine():
    """W3a（D2-1）：artifact 已 durable 且容器已释放后 receipt 写失败——仍 run halt、仍无
    cleanup 追加；容器早已不存在（隔离队列为空），证据 = 已持久化的本体。批 A I12：cleanup
    段照常执行（幂等，不再 rm 第二次）。"""

    store = FakeFinalizationStore(fail_persist_receipt=True)
    chain = _formal_chain(store)
    _log_docker_rm(chain)
    with pytest.raises(FatalExecutionInfrastructureError,
                       match="finalization_receipt_write_failed"):
        await chain.orchestrator.generate(
            _Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    order = store.call_order
    assert order.index("put_artifact_bodies") < order.index("docker_rm") < order.index("persist_receipt")
    assert store.bodies and store.cleanup_results == []
    assert chain.orchestrator.cleanup_quarantine == []  # 容器已不存在，无现场可隔离
    audit = chain.orchestrator.audits[0]
    assert audit.rollout_container_released_before_grading is True
    steps = [e.step for e in audit.timeline]
    assert "cleanup_completed" in steps and "cleanup_skipped_receipt_failure" not in steps
    assert len(chain.docker.removed) == 1  # 幂等：已释放的容器不再 rm
    assert any(f.error_type == "finalization_receipt_write_failed"
               for f in audit.failure_records)


def _pause_drop_session(chain):
    """把 per-rollout adapter 的 drop_session（finally 段第一个清理 await）换成可暂停版本：
    返回 (entered, release) 两个 Event——entered 在进入 drop_session 时置位，release 由测试
    置位后才继续真正 drop。用于观察"清理等待期间"的状态（Codex 批 A 审查 R2 的探针形状）。"""

    import asyncio

    entered, release = asyncio.Event(), asyncio.Event()
    original_factory = chain.orchestrator._adapter_factory

    def factory(hook, defaults):
        adapter = original_factory(hook, defaults)
        original_drop = adapter.drop_session

        async def paused_drop(sid, *, wait_timeout=5.0):
            entered.set()
            await release.wait()
            return await original_drop(sid, wait_timeout=wait_timeout)

        adapter.drop_session = paused_drop
        return adapter

    chain.orchestrator._adapter_factory = factory
    return entered, release


def _record_halt_notifications(chain) -> list:
    notified: list = []
    chain.orchestrator._notify_fatal_halt = notified.append
    return notified


async def test_receipt_only_failure_notifies_halt_before_cleanup_wait():
    """批 A I12（Codex 批 A 审查 R2）：receipt 写失败是本 attempt **唯一**的 fatal 时，必须在
    进入 drop_session / 容器 rm 等清理 await **之前**就经 `_notify_fatal_halt` 通知停机——否则
    清理窗口内 worker 仍接新执行。放开清理后：cleanup 照常完成，最终抛出的就是已通知的同一个
    fatal 对象（首因不变、不二次构造）。"""

    import asyncio

    store = FakeFinalizationStore(fail_persist_receipt=True)
    chain = _formal_chain(
        store, crash=SlimeBindingError("harness_bootstrap_failed", "docker exec failed (exit=1)")
    )
    entered, release = _pause_drop_session(chain)
    notified = _record_halt_notifications(chain)
    task = asyncio.create_task(
        chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    )
    await asyncio.wait_for(entered.wait(), 2.0)
    # 检查点：清理尚未发生（容器还在、drop 未返回），但停机通知已经发出
    audit = chain.orchestrator.audits[0]
    assert [n.reason_code for n in notified] == ["finalization_receipt_write_failed"]
    assert chain.docker.removed == [] and audit.lease_released is False
    assert any(f.error_type == "finalization_receipt_write_failed" for f in audit.failure_records)
    release.set()
    with pytest.raises(FatalExecutionInfrastructureError, match="finalization_receipt_write_failed") as ei:
        await asyncio.wait_for(task, 2.0)
    assert ei.value is notified[0]  # 尾部抛的是已通知的同一对象
    assert len(notified) == 1
    steps = [e.step for e in audit.timeline]
    assert "cleanup_started" in steps and "cleanup_completed" in steps
    assert len(chain.docker.removed) == 1 and audit.lease_released is True
    assert store.cleanup_results == [] and chain.orchestrator.cleanup_quarantine == []


async def test_primary_fatal_with_receipt_failure_keeps_first_cause_single_notification():
    """对照：已有在途 fatal（harness 内基建级致命错误）时 receipt 也失败 → 只通知首因一次，
    receipt 失败只作 secondary 事实，尾部不再抛/不再通知 receipt fatal；清理照常。"""

    import asyncio

    store = FakeFinalizationStore(fail_persist_receipt=True)
    chain = _formal_chain(
        store, crash=FatalExecutionInfrastructureError("probe_primary_fatal", "harness 内首因")
    )
    entered, release = _pause_drop_session(chain)
    notified = _record_halt_notifications(chain)
    task = asyncio.create_task(
        chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    )
    await asyncio.wait_for(entered.wait(), 2.0)
    assert [n.reason_code for n in notified] == ["probe_primary_fatal"]
    release.set()
    with pytest.raises(FatalExecutionInfrastructureError, match="probe_primary_fatal"):
        await asyncio.wait_for(task, 2.0)
    assert [n.reason_code for n in notified] == ["probe_primary_fatal"]
    audit = chain.orchestrator.audits[0]
    assert any(f.error_type == "finalization_receipt_write_failed" for f in audit.failure_records)
    assert "cleanup_completed" in [e.step for e in audit.timeline]
    assert len(chain.docker.removed) == 1


async def test_underivable_facts_notifies_halt_before_cleanup_wait(monkeypatch):
    """同一接缝的另一条尾部 fatal：termination 事实不可派生（receipt 已 durable）也在清理 await
    之前通知，尾部抛同一对象。"""

    import asyncio

    store = FakeFinalizationStore()
    chain = _formal_chain(store)

    def _boom(receipt):
        raise TerminationFactsError("forced contradiction")

    monkeypatch.setattr(generate_mod, "termination_facts_payload", _boom)
    entered, release = _pause_drop_session(chain)
    notified = _record_halt_notifications(chain)
    task = asyncio.create_task(
        chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    )
    await asyncio.wait_for(entered.wait(), 2.0)
    assert [n.reason_code for n in notified] == ["termination_facts_underivable"]
    assert store.receipts  # receipt 先 durable
    release.set()
    with pytest.raises(FatalExecutionInfrastructureError, match="termination_facts_underivable") as ei:
        await asyncio.wait_for(task, 2.0)
    assert ei.value is notified[0] and len(notified) == 1
    assert "cleanup_completed" in [e.step for e in chain.orchestrator.audits[0].timeline]


# ------------------------------------------- ② cleanup 失败追加不覆盖首因
async def test_cleanup_failure_appended_receipt_untouched():
    chain = _formal_chain(rm_fail=True)  # 容器 rm 失败
    await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    store = chain.finalization
    assert len(store.receipts) == 1  # receipt 恰好持久化一次，从未改写
    assert store.call_order.count("persist_receipt") == 1
    receipt = store.receipts[0]
    assert receipt.attempt_disposition == "delivery_prepared"  # 首因事实完好
    assert len(store.cleanup_results) == 1
    append = store.cleanup_results[0]
    assert append.receipt_id == receipt.receipt_id
    assert append.cleanup_failures  # 清理失败进追加记录
    assert append.poison_released is False  # 清理未确认 → poison 不释放


# ------------------------------------------- ③ F2-4 字段复用
async def test_receipt_fields_reusable_by_f2_4():
    chain = _formal_chain()
    await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    receipt = chain.finalization.receipts[0]
    assert receipt.attempt_disposition == "delivery_prepared"
    # B5 复核 P0：receipt 不承载 trainer handoff 语义（HANDED_OFF 归 F2-5/6）
    assert not hasattr(receipt, "handed_off")
    # typed 嵌入 = 同一事实（构造期已复跑 Outcome v2 不变量）
    from repoharness2.contracts.fa_runtime import RolloutAttemptOutcomeV2

    assert receipt.outcome_v2 == RolloutAttemptOutcomeV2.model_validate(audit.outcome_v2)
    assert receipt.physical_attempt_id == audit.physical_attempt_id
    assert receipt.frozen_patch_digest == audit.frozen_patch_digest
    assert receipt.baseline_manifest_digest == audit.baseline_manifest_digest
    assert receipt.artifact_bodies_persisted is True
    assert receipt.grading_report_id == audit.finalized.grading_report.report_id
    assert receipt.eligibility_report_id == audit.finalized.eligibility_report.report_id
    # F2-3 批 1：drain receipt 内嵌 + ref 一致
    assert receipt.drain_receipt is not None
    assert receipt.drain_receipt_ref == receipt.drain_receipt.receipt_id
    # 本体确实可解引用（digest 匹配）
    from repoharness2.contracts.frozen_patch import compute_frozen_patch_digest

    body = chain.finalization.bodies[0]["frozen_patch"]
    assert compute_frozen_patch_digest(body) == receipt.frozen_patch_digest


async def test_test_only_change_is_graded_normally_not_unsafe():
    """W3a（D2-3，T1 oracle 改动，原 test_abort_path_still_gets_receipt：测试文件改动 →
    unsafe 永久拒绝、不评分）：只改测试文件的 artifact 现在**正常评分**——控制面 entry 拆进
    ignored_validation_delta（不重放、只记录），grader 收到的投影 candidate 集为空；真实交付 +
    EligibilityReport；receipt=delivery_prepared；顺序 put_artifact_bodies < docker_rm <
    persist_receipt。"""

    content = b"def test_x():\n    pass\n"
    sha = hashlib.sha256(content).hexdigest()
    b64 = base64.b64encode(content).decode()

    class _TamperWs(_FrozenWs):
        async def run_bash(self, script):
            from types import SimpleNamespace

            if "find ." in script:
                return SimpleNamespace(exit_code=0, stdout=(
                    f"regular\t100644\t{sha}\ttests/test_x.py\n"), stderr="")
            if "base64 <" in script:
                return SimpleNamespace(exit_code=0,
                                       stdout=f"tests/test_x.py\t{b64}\n",
                                       stderr="")
            return await self._u.run_bash(script)

    class _TamperBarrier:
        async def establish(self, *, workspace, audit):
            return QuiescenceConfirmed(
                frozen_grading_workspace=_TamperWs(workspace),
                snapshot_ref="sha256:abc", evidence_refs=("s",))

    import dataclasses

    from test_slime_generate import TASK_ID_DENSE, make_task

    from repoharness2.grading.manager import HygieneRules

    base_task = make_task(TASK_ID_DENSE)
    task = dataclasses.replace(
        base_task,
        grading_spec=dataclasses.replace(
            base_task.grading_spec, hygiene=HygieneRules(test_globs=("tests/*",))),
    )
    turns = dense_turns()
    for t in turns:
        t.response["meta_info"]["weight_version"] = "5"
    chain = build_dense_chain(
        config=_formal_config(policy_version="5", execution_mode="fa_formal"),
        runtime_quiescence_barrier=_TamperBarrier(), turns=turns, task=task)
    _stamp_fa_identity(chain.base_sample)
    _log_docker_rm(chain)
    delivered = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    store = chain.finalization
    receipt = store.receipts[0]
    audit = chain.orchestrator.audits[0]
    assert receipt.attempt_disposition == "delivery_prepared"
    assert all(getattr(x, "remove_sample", True) is False for x in delivered)
    assert all("rh2_admission" in x.metadata for x in delivered)
    # 完整 artifact（含测试文件改动）先持久化供审计
    assert store.bodies and receipt.artifact_bodies_persisted is True
    # D2-3：评分发生了，投影 candidate 集为空、ignored 记录了测试路径
    (call,) = chain.grading.calls
    assert call["workspace"] is None
    assert call["frozen_delta"].projection.included_entry_paths == ()
    assert audit.trusted_projection["ignored_validation_entries"] == [
        {"path": "tests/test_x.py", "operation": "add", "object_type": "regular",
         "control_plane_class": "test_glob"},
    ]
    assert audit.unsafe_artifact_reasons == []
    assert receipt.outcome_v2.reason_code is None
    assert receipt.outcome_v2.task_outcome in ("resolved", "unresolved")  # 由 grader 决定
    assert receipt.eligibility_report_id is not None
    assert "ignored_validation_delta:test_glob:add:tests/test_x.py" in receipt.outcome_v2.evidence_refs
    order = store.call_order
    assert order.index("put_artifact_bodies") < order.index("docker_rm") < order.index("persist_receipt")


async def test_artifact_body_persist_failure_is_run_fatal():
    """Brief §6（owner 2026-09-09 确认，原 oracle = ABORTED）：本体持久化失败 = A4"核心记录持久化失败"→
    typed run-fatal（不评分不交付、通知停 run、继续清理）；receipt 记 fatal_run_halt + bodies 未持久化。"""

    from repoharness2.adapters.slime.async_worker import FatalExecutionInfrastructureError

    store = FakeFinalizationStore(fail_put_bodies=True)
    chain = _formal_chain(store)
    with pytest.raises(FatalExecutionInfrastructureError, match="frozen_artifact_persist_failed"):
        await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    assert chain.grading.calls == []  # 不评分
    receipt = store.receipts[0]
    assert receipt.attempt_disposition == "fatal_run_halt"
    assert receipt.artifact_bodies_persisted is False
    assert receipt.terminal_reason_code == "frozen_artifact_persist_failed"
    audit = chain.orchestrator.audits[0]
    assert any("frozen_artifact_persist_failed" in f.detail and f.stage == "finalize" for f in audit.failure_records)
    assert "cleanup_completed" in [e.step for e in audit.timeline]


# ------------------------------------------- S1 回归 + 文件实现
async def test_s1_without_store_unchanged():
    chain = build_dense_chain()  # 默认 s1 配置：不自动配 store
    assert chain.finalization is None
    delivered = await chain.orchestrator.generate(
        _Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    assert delivered  # 正常交付，无 receipt 依赖


def test_fa_formal_requires_store():
    from test_slime_generate import TASK_ID_DENSE, GradingSubmitStub, make_task

    from repoharness2.adapters.slime.generate import (
        RolloutOrchestrator,
        SlimeBindingError,
    )

    with pytest.raises(SlimeBindingError, match="finalization_store_required"):
        RolloutOrchestrator(
            config=_formal_config(policy_version="5", execution_mode="fa_formal"),
            task_resolver=make_task(TASK_ID_DENSE),
            adapter_factory=lambda hook, defaults: None,
            harness_driver=object(),
            grading_submit=GradingSubmitStub(),
            runtime_quiescence_barrier=_Barrier(),
        )


def test_file_finalization_store_per_attempt_immutable(tmp_path):
    """T0 第 9 条：per-execution immutable 目录、无全局 CAS；write-once
    （同内容幂等 / 不同内容 typed 冲突）；cleanup 独立文件不改写 receipt。"""

    import json
    from datetime import datetime, timezone

    from repoharness2.adapters.slime.bringup import (
        FileFinalizationStore,
        FinalizationStoreConflict,
    )
    from repoharness2.contracts.baseline_manifest import (
        BASELINE_MANIFEST_POLICY_V1,
        BaselineWorkspaceManifestV1,
        compute_baseline_manifest_digest,
        compute_policy_digest,
    )
    from repoharness2.contracts.finalization import (
        CleanupResultAppendV1,
        FinalizationReceiptV1,
    )
    from repoharness2.contracts.frozen_patch import FrozenPatchArtifactV1

    store = FileFinalizationStore(tmp_path / "fin")
    baseline = BaselineWorkspaceManifestV1(
        task_id="t", workdir="/testbed",
        public_bundle_digest="sha256:" + "e" * 64,
        runtime_image_digest="sha256:" + "1" * 64,
        materialized_head="a" * 40, task_base_commit="a" * 40,
        policy=BASELINE_MANIFEST_POLICY_V1,
        policy_digest=compute_policy_digest(BASELINE_MANIFEST_POLICY_V1),
        entries=(),
    )
    art = FrozenPatchArtifactV1(
        task_id="t", rollout_execution_id="e1",
        physical_attempt_id="e1#p1-aaaa",
        baseline_manifest_digest=compute_baseline_manifest_digest(baseline),
        public_bundle_digest=baseline.public_bundle_digest,
        runtime_image_digest=baseline.runtime_image_digest,
        materialized_head=baseline.materialized_head,
        entries=(), excluded_pathset_changed=False,
    )
    store.put_artifact_bodies(frozen_patch=art, baseline_manifest=baseline)
    store.put_artifact_bodies(frozen_patch=art, baseline_manifest=baseline)  # 同内容幂等
    adir = tmp_path / "fin" / "attempts" / "e1_p1-aaaa"
    assert (adir / "frozen_patch.json").exists()
    assert (adir / "baseline_manifest.json").exists()  # per-attempt，无共享 CAS 目录
    assert not (tmp_path / "fin" / "artifacts").exists()
    assert not list((tmp_path / "fin").rglob("*.tmp"))  # 原子写无残留

    def receipt(reason):
        # 复核二轮 P1-2 后 delivery_prepared 需带 drain 证明；本测试只关心
        # 存储不可变性，用 aborted + 不同归因构造"同 ID 不同内容"对
        return FinalizationReceiptV1(
            receipt_id="rcpt_e1_p1-aaaa", task_id="t", trajectory_id="traj",
            physical_attempt_id="e1#p1-aaaa", attempt_disposition="aborted",
            terminal_reason_code=reason,
            started_epoch_seconds=1.0,
            finalized_at_utc=datetime(2026, 8, 18, tzinfo=timezone.utc),
        )

    store.persist_receipt(receipt("reason_a"))
    store.persist_receipt(receipt("reason_a"))  # 同内容幂等
    with pytest.raises(FinalizationStoreConflict):  # 同 ID 改归因：拒绝
        store.persist_receipt(receipt("reason_b"))
    rfile = adir / "receipt.json"
    assert json.loads(rfile.read_text())["terminal_reason_code"] == "reason_a"  # 未被覆盖

    def cleanup(failures):
        return CleanupResultAppendV1(
            receipt_id="rcpt_e1_p1-aaaa",
            cleanup_failures=failures,
            completed_at_utc=datetime(2026, 8, 18, 0, 0, 5, tzinfo=timezone.utc),
        )

    from repoharness2.contracts.finalization import CleanupFailureFact

    first = cleanup([CleanupFailureFact(lease_id="l", step="rm", detail="rm failed")])
    store.append_cleanup_result(first)
    before = rfile.read_bytes()
    with pytest.raises(FinalizationStoreConflict):  # 第二次写抹掉失败事实：拒绝
        store.append_cleanup_result(cleanup([]))
    assert rfile.read_bytes() == before  # receipt 本体始终未动
    stored = json.loads((adir / "cleanup.json").read_text())
    assert stored["cleanup_failures"][0]["step"] == "rm"  # 首次失败事实保留


# ------------------------------------------- P0 / P1-4 复核负测试
async def test_receipt_then_audit_sink_failure_never_claims_handoff():
    """B5 复核 P0 场景：receipt 成功后 audit sink 失败 → generate 抛
    Fatal，样本从未离开 orchestrator——receipt 只说 delivery_prepared，
    没有任何 trainer handoff 字段可被 F2-4 误读成 uncertain_trained。"""

    chain = _formal_chain()

    def _failing_sink(audit):
        raise OSError("audit store down")

    chain.orchestrator._audit_sink = _failing_sink
    with pytest.raises(FatalExecutionInfrastructureError,
                       match="execution_audit_write_failed"):
        await chain.orchestrator.generate(
            _Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    receipt = chain.finalization.receipts[0]
    assert receipt.attempt_disposition == "delivery_prepared"
    assert not hasattr(receipt, "handed_off")  # trainer handoff 语义不存在


async def test_double_store_failure_first_cause_wins():
    """B5 复核 P1-4：receipt 失败 + audit sink 也失败 → 最终抛的是
    finalization_receipt_write_failed（最早首因），sink 失败记 secondary；
    批 A I12：cleanup 照常执行（cleanup_started/cleanup_completed 是真事件）。"""

    store = FakeFinalizationStore(fail_persist_receipt=True)
    chain = _formal_chain(store)

    def _failing_sink(audit):
        raise OSError("audit store down")

    chain.orchestrator._audit_sink = _failing_sink
    with pytest.raises(FatalExecutionInfrastructureError,
                       match="finalization_receipt_write_failed"):
        await chain.orchestrator.generate(
            _Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    steps = [e.step for e in audit.timeline]
    assert "cleanup_skipped_receipt_failure" not in steps
    assert "cleanup_started" in steps and "cleanup_completed" in steps
    assert any(f.error_type == "audit_sink_failed_secondary"
               for f in audit.failure_records)
    assert any(f.error_type == "finalization_receipt_write_failed"
               for f in audit.failure_records)


# ------------------------------------------- B5 复核三轮（P1-1/2/3）
async def test_barrier_fatal_plus_sink_failure_first_cause_wins():
    """三轮 P1-2：在途 Fatal（barrier 炸）+ audit sink 失败 → 传播的仍是
    首因 Fatal（不被 execution_audit_write_failed 顶替）；receipt 记
    fatal_run_halt + terminal_reason_code=首因；sink 失败记 secondary。"""

    class _FatalBarrier:
        async def establish(self, *, workspace, audit):
            raise FatalExecutionInfrastructureError(
                "primary_barrier_fatal", "barrier 基建炸（测试注入）")

    turns = dense_turns()
    for t in turns:
        t.response["meta_info"]["weight_version"] = "5"
    chain = build_dense_chain(
        config=_formal_config(policy_version="5", execution_mode="fa_formal"),
        runtime_quiescence_barrier=_FatalBarrier(), turns=turns)
    _stamp_fa_identity(chain.base_sample)

    def _failing_sink(audit):
        raise OSError("audit store down")

    chain.orchestrator._audit_sink = _failing_sink
    with pytest.raises(FatalExecutionInfrastructureError,
                       match="primary_barrier_fatal") as exc_info:
        await chain.orchestrator.generate(
            _Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    # 首因未被 sink 错误顶替（既有屏障包装层转 runtime_barrier_exception，
    # 消息链保留原始 primary_barrier_fatal）
    assert exc_info.value.reason_code == "runtime_barrier_exception"
    receipt = chain.finalization.receipts[0]
    assert receipt.attempt_disposition == "fatal_run_halt"
    # receipt 记录实际在途传播的 Fatal 归因（可恢复）
    assert receipt.terminal_reason_code == "runtime_barrier_exception"
    audit = chain.orchestrator.audits[0]
    assert any(f.error_type == "audit_sink_failed_secondary"
               for f in audit.failure_records)


async def test_store_conflict_is_run_halt_not_member_loss():
    """三轮 P1-3：immutable 违约（同 attempt 不同内容）→ Fatal run-halt，
    绝不 remove_sample 缺员继续训练。"""

    store = FakeFinalizationStore(conflict_put_bodies=True)
    chain = _formal_chain(store)
    with pytest.raises(FatalExecutionInfrastructureError,
                       match="finalization_store_conflict"):
        await chain.orchestrator.generate(
            _Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    # receipt 仍产出（fatal 在途），归因可恢复
    receipt = store.receipts[0]
    assert receipt.attempt_disposition == "fatal_run_halt"
    assert receipt.terminal_reason_code == "finalization_store_conflict"


async def test_unsupported_object_rejection_evidence_survives_in_receipt():
    """三轮 P1-1：FIFO 等不支持对象在 artifact 建立前触发永久拒绝——
    对象路径/类型经 typed 证据内嵌 receipt，workspace 清理后不消失。"""

    class _FifoWs(_FrozenWs):
        async def run_bash(self, script):
            from types import SimpleNamespace

            if "find ." in script:
                return SimpleNamespace(
                    exit_code=0, stdout="UNSUPPORTED\tfifo\tevil_pipe\n", stderr="")
            return await self._u.run_bash(script)

    class _FifoBarrier:
        async def establish(self, *, workspace, audit):
            return QuiescenceConfirmed(
                frozen_grading_workspace=_FifoWs(workspace),
                snapshot_ref="sha256:abc", evidence_refs=("s",))

    turns = dense_turns()
    for t in turns:
        t.response["meta_info"]["weight_version"] = "5"
    chain = build_dense_chain(
        config=_formal_config(policy_version="5", execution_mode="fa_formal"),
        runtime_quiescence_barrier=_FifoBarrier(), turns=turns)
    _stamp_fa_identity(chain.base_sample)
    delivered = await chain.orchestrator.generate(
        _Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    # W1b 第二段（三终态 ③，T1 oracle 改动）：unsupported 对象 = present + 永久拒绝，真实交付
    # + 载荷（无报告）而不是 ABORTED；receipt=delivery_prepared，拒绝证据照旧内嵌。
    assert all(getattr(x, "remove_sample", True) is False for x in delivered)
    assert all("rh2_admission" in x.metadata for x in delivered)
    receipt = chain.finalization.receipts[0]
    assert receipt.attempt_disposition == "delivery_prepared"
    assert receipt.rejection_evidence is not None
    assert receipt.rejection_evidence.reason_code == "unsupported_object_in_patch"
    assert receipt.rejection_evidence.object_path == "evil_pipe"
    assert receipt.rejection_evidence.object_type == "fifo"
    assert receipt.frozen_patch_digest is None  # artifact 未建立，证据仍在
    assert "object:evil_pipe:fifo" in receipt.outcome_v2.evidence_refs
