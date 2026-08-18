"""B5 验收（05 计划 5a 节）：
① receipt 前 cleanup 不发生（正序 + persist 失败保留现场 run-halt）；
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

from repoharness2.adapters.slime.async_worker import (  # noqa: E402
    FatalExecutionInfrastructureError,
)
from repoharness2.adapters.slime.generate import QuiescenceConfirmed  # noqa: E402


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


# ------------------------------------------- ① receipt 前 cleanup 不发生
async def test_receipt_persists_before_any_cleanup():
    chain = _formal_chain()
    _log_docker_rm(chain)
    await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    order = chain.finalization.call_order
    assert "persist_receipt" in order and "docker_rm" in order
    assert order.index("persist_receipt") < order.index("docker_rm")
    assert order.index("docker_rm") < order.index("append_cleanup_result")
    # 本体持久化发生在 receipt 之前（组装时刻）
    assert order.index("put_artifact_bodies") < order.index("persist_receipt")


async def test_receipt_persist_failure_retains_workspace_and_run_halts():
    """T0 失败表第 2 行：durable handoff 失败 → 不清理（容器保留 + 隔离
    队列）+ run halt；cleanup 追加记录也不发生。"""

    store = FakeFinalizationStore(fail_persist_receipt=True)
    chain = _formal_chain(store)
    _log_docker_rm(chain)
    with pytest.raises(FatalExecutionInfrastructureError,
                       match="finalization_receipt_write_failed"):
        await chain.orchestrator.generate(
            _Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    assert "docker_rm" not in store.call_order  # 容器未清理（现场保留）
    assert store.cleanup_results == []  # 无 receipt 就无追加
    assert chain.orchestrator.cleanup_quarantine  # 容器入隔离队列
    audit = chain.orchestrator.audits[0]
    assert any(f.error_type == "finalization_receipt_write_failed"
               for f in audit.failure_records)


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


async def test_abort_path_still_gets_receipt():
    """abort 路径同样出 receipt（disposition=aborted + outcome_v2 归因），
    cleanup 仍在 receipt 之后。"""

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
    await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    store = chain.finalization
    receipt = store.receipts[0]
    assert receipt.attempt_disposition == "aborted"  # 软失败收口
    assert receipt.terminal_reason_code == "unsafe_artifact_permanent_rejection"
    # B5 复核 P1-2（T0 第 9 条 retention）：unsafe 拒绝也保留 artifact 本体
    assert store.bodies, "unsafe 分支必须先持久化本体再返回"
    assert receipt.artifact_bodies_persisted is True
    assert receipt.outcome_v2.reason_code == "unsafe_artifact_permanent_rejection"
    assert store.call_order.index("persist_receipt") < store.call_order.index("docker_rm")


async def test_artifact_body_persist_failure_is_missing_abort():
    """T0 失败表第 1 行：本体持久化失败 = 无法建立可信 artifact →
    abort（样本剔除），不评分；receipt 记 aborted + bodies 未持久化。"""

    store = FakeFinalizationStore(fail_put_bodies=True)
    chain = _formal_chain(store)
    delivered = await chain.orchestrator.generate(
        _Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    assert all(getattr(x, "remove_sample", False) for x in delivered)
    assert chain.grading.calls == []  # 不评分
    receipt = store.receipts[0]
    assert receipt.attempt_disposition == "aborted"
    assert receipt.artifact_bodies_persisted is False
    assert receipt.terminal_reason_code == "frozen_artifact_persist_failed"
    assert receipt.outcome_v2.reward_unavailable is True


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

    def receipt(disposition):
        return FinalizationReceiptV1(
            receipt_id="rcpt_e1_p1-aaaa", task_id="t", trajectory_id="traj",
            physical_attempt_id="e1#p1-aaaa", attempt_disposition=disposition,
            started_epoch_seconds=1.0,
            finalized_at_utc=datetime(2026, 8, 18, tzinfo=timezone.utc),
        )

    store.persist_receipt(receipt("aborted"))
    store.persist_receipt(receipt("aborted"))  # 同内容幂等
    with pytest.raises(FinalizationStoreConflict):  # aborted 改 delivery_prepared：拒绝
        store.persist_receipt(receipt("delivery_prepared"))
    rfile = adir / "receipt.json"
    assert json.loads(rfile.read_text())["attempt_disposition"] == "aborted"  # 未被覆盖

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
    不写 cleanup_started/cleanup_completed 假事件，标 cleanup_skipped。"""

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
    assert "cleanup_skipped_receipt_failure" in steps
    assert "cleanup_started" not in steps  # 跳过就不写假事件
    assert "cleanup_completed" not in steps
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
    assert all(getattr(x, "remove_sample", False) for x in delivered)
    receipt = chain.finalization.receipts[0]
    assert receipt.attempt_disposition == "aborted"
    assert receipt.rejection_evidence is not None
    assert receipt.rejection_evidence.reason_code == "unsupported_object_in_patch"
    assert receipt.rejection_evidence.object_path == "evil_pipe"
    assert receipt.rejection_evidence.object_type == "fifo"
    assert receipt.frozen_patch_digest is None  # artifact 未建立，证据仍在
    assert "object:evil_pipe:fifo" in receipt.outcome_v2.evidence_refs
