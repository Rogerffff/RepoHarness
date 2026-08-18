"""B5 验收（05 计划 5a 节）：
① receipt 前 cleanup 不发生（正序 + persist 失败保留现场 run-halt）；
② cleanup failure 追加、不覆盖首因（独立记录，receipt 不改写）；
③ F2-4 可复用 receipt 字段（outcome_v2 verbatim / handed_off / digest 引用）；
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
    assert receipt.attempt_disposition == "delivered"  # 首因事实完好
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
    assert receipt.attempt_disposition == "delivered"
    assert receipt.handed_off is True  # HANDED_OFF → F2-4 uncertain_trained 判据
    assert receipt.outcome_v2 == audit.outcome_v2  # 事实层 verbatim
    assert receipt.physical_attempt_id == audit.physical_attempt_id
    assert receipt.frozen_patch_digest == audit.frozen_patch_digest
    assert receipt.baseline_manifest_digest == audit.baseline_manifest_digest
    assert receipt.artifact_bodies_persisted is True
    assert receipt.grading_report_id == audit.finalized.grading_report.report_id
    assert receipt.eligibility_report_id == audit.finalized.eligibility_report.report_id
    assert receipt.drain_receipt_ref is None  # F2-3 落地前恒 None
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
    assert receipt.handed_off is False
    assert receipt.abort_reason == "unsafe_artifact_permanent_rejection"
    assert receipt.outcome_v2["reason_code"] == "unsafe_artifact_permanent_rejection"
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
    assert receipt.handed_off is False
    assert receipt.artifact_bodies_persisted is False
    assert receipt.abort_reason == "frozen_artifact_persist_failed"
    assert receipt.outcome_v2["reward_unavailable"] is True


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


def test_file_finalization_store_atomic_and_append_only(tmp_path):
    """文件实现：原子写（无 .tmp 残留）、content-addressed 去重、cleanup
    独立文件（receipt 本体不改写）。"""

    import json
    from datetime import datetime, timezone

    from repoharness2.adapters.slime.bringup import FileFinalizationStore
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
    from repoharness2.contracts.frozen_patch import (
        FrozenPatchArtifactV1,
        compute_frozen_patch_digest,
    )

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
    store.put_artifact_bodies(frozen_patch=art, baseline_manifest=baseline)  # 幂等
    fp_dir = tmp_path / "fin" / "artifacts" / "frozen_patch"
    assert len(list(fp_dir.glob("*.json"))) == 1
    fp_file = next(fp_dir.glob("*.json"))
    assert fp_file.stem == compute_frozen_patch_digest(art).removeprefix("sha256:")
    assert not list((tmp_path / "fin").rglob("*.tmp"))  # 原子写无残留

    receipt = FinalizationReceiptV1(
        receipt_id="rcpt_e1_p1-aaaa", task_id="t", trajectory_id="traj",
        physical_attempt_id="e1#p1-aaaa", attempt_disposition="delivered",
        started_epoch_seconds=1.0,
        finalized_at_utc=datetime.now(timezone.utc),
    )
    store.persist_receipt(receipt)
    rfile = tmp_path / "fin" / "receipts" / "rcpt_e1_p1-aaaa.receipt.json"
    before = rfile.read_bytes()
    store.append_cleanup_result(CleanupResultAppendV1(
        receipt_id=receipt.receipt_id,
        completed_at_utc=datetime.now(timezone.utc),
    ))
    cfile = tmp_path / "fin" / "receipts" / "rcpt_e1_p1-aaaa.cleanup.json"
    assert cfile.exists()  # 独立追加文件
    assert rfile.read_bytes() == before  # receipt 本体逐字未动
    assert json.loads(rfile.read_text())["attempt_disposition"] == "delivered"
