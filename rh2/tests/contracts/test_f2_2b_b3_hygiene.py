"""B3 验收：hygiene 分类 + 引用式 ScoringProjection + 失败表行为。

计划验收项：unsafe → present_* + permanent_rejection 不跑 grader；
runtime 私有文件 = 记录事实而非 tamper。
"""

from __future__ import annotations

import base64
import hashlib

import pytest

from repoharness2.contracts.frozen_patch import FrozenPatchArtifactV1, PatchEntry
from repoharness2.contracts.scoring_projection import (
    HygieneReport,
    ScoringProjectionArtifactV1,
    classify_frozen_patch,
)

_NS = (".git/", ".harness/")

from repoharness2.contracts.baseline_manifest import (  # noqa: E402
    BASELINE_MANIFEST_POLICY_V1,
    BaselineWorkspaceManifestV1,
    compute_baseline_manifest_digest,
    compute_policy_digest,
)

_BASELINE = BaselineWorkspaceManifestV1(
    task_id="t1", workdir="/testbed",
    public_bundle_digest="sha256:" + "e" * 64,
    runtime_image_digest="sha256:" + "1" * 64,
    materialized_head="a" * 40, task_base_commit="b" * 40,
    policy=BASELINE_MANIFEST_POLICY_V1,
    policy_digest=compute_policy_digest(BASELINE_MANIFEST_POLICY_V1),
    entries=(),
)
_BASELINE_DIGEST = compute_baseline_manifest_digest(_BASELINE)


def _b64(data: bytes):
    return (base64.b64encode(data).decode(),
            "sha256:" + hashlib.sha256(data).hexdigest())


def _reg_entry(path, data=b"x"):
    b64, dg = _b64(data)
    return PatchEntry(path=path, operation="add", object_type="regular",
                      mode="100644", content_b64=b64, content_digest=dg)


def _link_entry(path, target: bytes):
    b64, dg = _b64(target)
    return PatchEntry(path=path, operation="add", object_type="symlink",
                      mode="120000", content_b64=b64, content_digest=dg)


def _art(entries, pathset_changed=False, **over):
    base = dict(
        task_id="t1", rollout_execution_id="exec_1",
        physical_attempt_id="exec_1#p1-aaaa",
        baseline_manifest_digest=_BASELINE_DIGEST,  # 真锚（classifier 互检）
        public_bundle_digest="sha256:" + "e" * 64,
        runtime_image_digest="sha256:" + "1" * 64,
        materialized_head="a" * 40,
        entries=tuple(entries), excluded_pathset_changed=pathset_changed,
    )
    base.update(over)
    return FrozenPatchArtifactV1(**base)


def _classify(art):
    return classify_frozen_patch(art, _BASELINE)


def test_projectable_projection_is_reference_only():
    report, proj = _classify(_art([_link_entry("l", b"src/a.py"), _reg_entry("src/a.py")]))
    assert report.verdict == "projectable"
    assert proj.included_entry_paths == ("l", "src/a.py")
    # 引用不复制：projection 无任何内容字段
    assert "content" not in str(sorted(ScoringProjectionArtifactV1.model_fields))


def test_symlink_lexical_resolution_three_codex_cases():
    """阻塞 1 三判例：跨入排除区拒；仓库内父目录相对链接放行；逃根拒。"""

    # repo_config_link -> .git/config：解析落排除区 → 拒（修复前误放行）
    report, proj = _classify(_art([_link_entry("repo_config_link", b".git/config")]))
    assert report.verdict == "unsafe_artifact" and proj is None
    assert any("into_excluded_namespace" in r for r in report.reason_codes)
    # pkg/link -> ../shared/file：解析 = shared/file 仍在根内 → 放行（修复前误拒）
    report, proj = _classify(_art([_link_entry("pkg/link", b"../shared/file")]))
    assert report.verdict == "projectable"
    # pkg/link -> ../../outside：逃出根 → 拒
    report, proj = _classify(_art([_link_entry("pkg/link", b"../../outside")]))
    assert report.verdict == "unsafe_artifact"
    assert any("unsafe_symlink_escape" in r for r in report.reason_codes)
    # 绝对路径仍拒；根级 ../ 拒
    for path, target in [("l", b"/etc/passwd"), ("l", b"../x")]:
        report, _ = _classify(_art([_link_entry(path, target)]))
        assert report.verdict == "unsafe_artifact"
    # docs/latest -> ../README.md（codex 误拒反例）→ 放行
    report, _ = _classify(_art([_link_entry("docs/latest", b"../README.md")]))
    assert report.verdict == "projectable"


def test_classifier_recomputes_digest_and_rejects_mismatch():
    """阻塞 2：digest/lineage 由 classifier 内部重算互检——假锚/错 lineage 拒。"""

    from repoharness2.contracts.frozen_patch import compute_frozen_patch_digest
    from repoharness2.contracts.scoring_projection import ProjectionContractError

    art = _art([_reg_entry("a.py")])
    report, proj = _classify(art)
    assert proj.frozen_patch_digest == compute_frozen_patch_digest(art)  # 真重算
    with pytest.raises(ProjectionContractError, match="baseline_digest_mismatch"):
        _classify(_art([_reg_entry("a.py")],
                       baseline_manifest_digest="sha256:" + "0" * 64))
    with pytest.raises(ProjectionContractError, match="lineage_mismatch"):
        _classify(_art([_reg_entry("a.py")], task_id="t-other"))


def test_entry_in_excluded_namespace_unsafe():
    report, proj = _classify(_art([_reg_entry(".harness/x")]))
    assert report.verdict == "unsafe_artifact" and proj is None
    assert any("entry_in_excluded_namespace" in r for r in report.reason_codes)


def test_runtime_private_pathset_fact_not_tamper():
    report, proj = _classify(_art([_reg_entry("a.py")], pathset_changed=True))
    assert report.verdict == "projectable"  # 变化 ≠ tamper（A-prime 6）
    assert report.runtime_private_pathset_changed is True
    assert proj is not None


def test_hygiene_report_consistency():
    with pytest.raises(ValueError, match="必须携带 reason_codes"):
        HygieneReport(verdict="unsafe_artifact", runtime_private_pathset_changed=False)
    with pytest.raises(ValueError, match="不得携带"):
        HygieneReport(verdict="projectable", reason_codes=("x",),
                      runtime_private_pathset_changed=False)


async def test_contract_mismatch_goes_fatal_not_missing():
    """P1-1 反例：baseline 互检失败 → Fatal 逃逸（worker run-halt），
    不收口为缺员继续训练；audit 落结构化归因。"""

    import sys
    from pathlib import Path as _P

    sys.path.insert(0, str(_P(__file__).resolve().parents[1] / "adapters"))
    from test_f2_2_capability import _stamp_fa_identity
    from test_slime_generate import (
        SAMPLING_PARAMS,
        _Args,
        _formal_config,
        build_dense_chain,
        dense_turns,
    )

    from repoharness2.adapters.slime.async_worker import (
        FatalExecutionInfrastructureError,
    )
    from repoharness2.adapters.slime.generate import QuiescenceConfirmed
    import repoharness2.adapters.slime.patch_exporter as pe

    class _FrozenWs:
        def __init__(self, u):
            self._u = u

        async def run_bash(self, script):
            return await self._u.run_bash(script)

    class _Barrier:
        async def establish(self, *, workspace, audit):
            return QuiescenceConfirmed(
                frozen_grading_workspace=_FrozenWs(workspace),
                snapshot_ref="sha256:abc", evidence_refs=("s",))

    # 注入：exporter 产出带错误 baseline 锚的 artifact（两份事实分家）
    real_export = pe.export_frozen_patch

    async def poisoned_export(workspace, baseline, **kw):
        art = await real_export(workspace, baseline, **kw)
        return art.model_copy(update={
            "baseline_manifest_digest": "sha256:" + "0" * 64})

    turns = dense_turns()
    for t in turns:
        t.response["meta_info"]["weight_version"] = "5"
    chain = build_dense_chain(
        config=_formal_config(policy_version="5", execution_mode="fa_formal"),
        runtime_quiescence_barrier=_Barrier(), turns=turns)
    _stamp_fa_identity(chain.base_sample)
    pe.export_frozen_patch = poisoned_export
    try:
        with pytest.raises(FatalExecutionInfrastructureError,
                           match="baseline_digest_mismatch"):
            await chain.orchestrator.generate(
                _Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    finally:
        pe.export_frozen_patch = real_export
    audit = chain.orchestrator.audits[0]
    assert any(f.error_type == "baseline_digest_mismatch"
               for f in audit.failure_records)
    assert chain.grading.calls == []  # 互检失败不评分


def test_exemption_requires_reward_unavailable():
    """P1-2 反例：resolved + reward 可得 + unsafe reason + 无 eligibility
    = 矛盾形状，构造即拒。"""

    from repoharness2.contracts.fa_runtime import (
        ExecutionIdentity,
        RolloutAttemptOutcomeV2,
    )

    with pytest.raises(ValueError, match="完整形状"):
        RolloutAttemptOutcomeV2(
            outcome_id="o", identity=ExecutionIdentity(
                prompt_group_id="g", group_index=0, rollout_execution_id="e",
                physical_attempt_id="e#p1-x", physical_attempt_seq=1),
            member_slot=0, attempt_number=1,
            completion_class="present_complete", termination_kind="completed",
            reason_code="unsafe_artifact_permanent_rejection",
            failed_component="patch_hygiene",
            task_outcome="resolved", reward_unavailable=False,  # 矛盾核
            recovery_scope="none", turn_weight_versions=["1"],
            intra_execution_version_span=0, current_version_at_finalize="1",
            eligibility_report_id=None,
        )


def test_permanent_rejected_disposition_requires_present_fact():
    """P1-3 反例：completion=missing + unsafe reason → disposition 不得
    派生 permanent_rejected（reason 字符串不足）。"""

    import json as _json
    import tempfile
    import types
    from pathlib import Path as _P

    from repoharness2.adapters.slime.bringup import write_execution_audit_record

    audit = types.SimpleNamespace(
        trajectory_id="t", task_id="k", session_id="s-x",
        physical_attempt_id=None,
        started_epoch_seconds=1000.0, started_monotonic=500.0,
        non_chargeable_intervals=[], steps=[], harness_exit_code=None,
        delivered_sample_count=0, lease_released=False,
        repair_signal_forwarded=False, failure_records=[], cleanup_failures=[],
        context_shrink_reasons=[], finalized=None, audit_only=False,
        session_plane_drained=False, runtime_quiescence_confirmed=False,
        capture_closed=False, baseline_manifest_digest=None,
        baseline_entry_count=0, frozen_patch_digest=None, patch_entry_count=0,
        excluded_pathset_changed=False, runtime_private_pathset_changed=False,
        unsafe_artifact_reasons=[], scoring_projection_entry_count=0,
        timeline_dicts=lambda: [], timing_summary=lambda: {},
        outcome_v2={"reason_code": "unsafe_artifact_permanent_rejection",
                    "completion_class": "missing"},
    )
    with tempfile.TemporaryDirectory() as td:
        jsonl = _P(td) / "a.jsonl"
        write_execution_audit_record(None, audit, jsonl)
        rec = _json.loads(jsonl.read_text().strip())
    assert rec["disposition"] != "permanent_rejected"  # missing 不派生拒绝


def test_unsafe_rejection_shape_table_driven():
    """B3 终核：七字段全量谓词——合法组合通过；逐字段翻转全部拒绝
    （schema/producer/disposition 三处共用同一谓词）。"""

    from repoharness2.contracts.fa_runtime import (
        ExecutionIdentity,
        RolloutAttemptOutcomeV2,
        outcome_dict_is_unsafe_rejection,
    )

    valid = dict(
        outcome_id="o", identity=ExecutionIdentity(
            prompt_group_id="g", group_index=0, rollout_execution_id="e",
            physical_attempt_id="e#p1-x", physical_attempt_seq=1),
        member_slot=0, attempt_number=1,
        completion_class="present_complete", termination_kind="completed",
        failure_category=None,
        reason_code="unsafe_artifact_permanent_rejection",
        failed_component="patch_hygiene",
        task_outcome="unknown", reward_unavailable=True,
        recovery_scope="none", turn_weight_versions=["1"],
        intra_execution_version_span=0, current_version_at_finalize="1",
        eligibility_report_id=None,
    )
    rec = RolloutAttemptOutcomeV2(**valid)  # 合法形状通过
    assert outcome_dict_is_unsafe_rejection(rec.model_dump(mode="json"))

    mutations = [
        {"failure_category": "grading_infra_failure"},   # codex 反例 2
        {"task_outcome": "resolved", "reward_unavailable": False,
         "eligibility_report_id": "elig"},               # codex 反例 1
        {"failed_component": "other_component"},
        {"eligibility_report_id": "elig"},
        {"reward_unavailable": False},
    ]
    for mut in mutations:
        with pytest.raises(ValueError):
            RolloutAttemptOutcomeV2(**{**valid, **mut})
    # missing + 该 reason：schema 拒（present_* 要求）；dict 谓词同样 False
    assert not outcome_dict_is_unsafe_rejection(
        {**rec.model_dump(mode="json"), "completion_class": "missing"})


async def test_e2e_unsupported_object_present_rejected_no_grader():
    """oracle 1：模型产出不支持对象（FIFO 等）→ present + 永久拒绝、
    不跑 grader、remove_sample（旧 fallback 表 missing 行已删，防退回）。"""

    import sys
    from pathlib import Path as _P

    sys.path.insert(0, str(_P(__file__).resolve().parents[1] / "adapters"))
    from test_f2_2_capability import _stamp_fa_identity
    from test_slime_generate import (
        SAMPLING_PARAMS,
        _Args,
        _formal_config,
        build_dense_chain,
        dense_turns,
    )

    from repoharness2.adapters.slime.generate import QuiescenceConfirmed

    class _FrozenWs:
        def __init__(self, underlying):
            self._u = underlying

        async def run_bash(self, script):
            if "find ." in script:
                from types import SimpleNamespace

                return SimpleNamespace(exit_code=0,
                                       stdout="UNSUPPORTED\tfifo\tweird_fifo\n",
                                       stderr="")
            return await self._u.run_bash(script)

    class _Barrier:
        async def establish(self, *, workspace, audit):
            return QuiescenceConfirmed(
                frozen_grading_workspace=_FrozenWs(workspace),
                snapshot_ref="sha256:abc", evidence_refs=("s",))

    turns = dense_turns()
    for t in turns:
        t.response["meta_info"]["weight_version"] = "5"
    chain = build_dense_chain(
        config=_formal_config(policy_version="5", execution_mode="fa_formal"),
        runtime_quiescence_barrier=_Barrier(), turns=turns)
    _stamp_fa_identity(chain.base_sample)
    delivered = await chain.orchestrator.generate(
        _Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert chain.grading.calls == []
    assert all(getattr(x, "remove_sample", False) for x in delivered)
    assert audit.outcome_v2["completion_class"] == "present_complete"
    assert audit.outcome_v2["reason_code"] == "unsafe_artifact_permanent_rejection"
    # oracle 2 一并：真实 generate → JSONL 的 disposition 回归（阻塞 4）
    import json as _json
    import tempfile

    from repoharness2.adapters.slime.bringup import write_execution_audit_record

    with tempfile.TemporaryDirectory() as td:
        jsonl = _P(td) / "a.jsonl"
        write_execution_audit_record(None, audit, jsonl)
        rec = _json.loads(jsonl.read_text().strip())
    assert rec["disposition"] == "permanent_rejected"  # 不再 unknown_terminal
    assert rec["unsafe_artifact_reasons"] == [
        "unsupported_object_in_patch:weird_fifo:fifo"
    ]
    # B5 复核三轮 P1-1：路径/类型作为 typed 证据挂 audit（receipt 内嵌面）
    assert audit.rejection_evidence.object_path == "weird_fifo"
    assert audit.rejection_evidence.object_type == "fifo"
    assert "runtime_private_pathset_changed" in rec
    assert "scoring_projection_entry_count" in rec


async def test_e2e_unsafe_artifact_present_rejected_no_grader(tmp_path):
    """失败表 unsafe 行：present_complete + 永久拒绝 reason、不跑 grader、
    abort 形状；audit 落 unsafe reasons。"""

    import sys
    from pathlib import Path as _P

    sys.path.insert(0, str(_P(__file__).resolve().parents[1] / "adapters"))
    from test_f2_2_capability import _stamp_fa_identity
    from test_slime_generate import (
        SAMPLING_PARAMS,
        _Args,
        _formal_config,
        build_dense_chain,
        dense_turns,
    )

    from repoharness2.adapters.slime.generate import QuiescenceConfirmed

    class _FrozenWs:
        """post census 注入一条逃逸 symlink（模型产物）。"""

        def __init__(self, underlying):
            self._u = underlying

        async def run_bash(self, script):
            if "find ." in script:
                from types import SimpleNamespace

                sha = hashlib.sha256(b"/etc/passwd").hexdigest()
                return SimpleNamespace(exit_code=0, stdout=(
                    f"symlink\t120000\t{sha}\tevil_link\n"), stderr="")
            if "readlink" in script and "printf" in script:
                from types import SimpleNamespace

                b64 = base64.b64encode(b"/etc/passwd").decode()
                return SimpleNamespace(exit_code=0,
                                       stdout=f"evil_link\t{b64}\n", stderr="")
            return await self._u.run_bash(script)

    class _Barrier:
        async def establish(self, *, workspace, audit):
            return QuiescenceConfirmed(
                frozen_grading_workspace=_FrozenWs(workspace),
                snapshot_ref="sha256:abc", evidence_refs=("s",))

    turns = dense_turns()
    for t in turns:
        t.response["meta_info"]["weight_version"] = "5"
    chain = build_dense_chain(
        config=_formal_config(policy_version="5", execution_mode="fa_formal"),
        runtime_quiescence_barrier=_Barrier(), turns=turns)
    _stamp_fa_identity(chain.base_sample)
    delivered = await chain.orchestrator.generate(
        _Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert chain.grading.calls == []  # unsafe 不运行 grader
    assert all(getattr(x, "remove_sample", False) for x in delivered)  # 剔除
    ov2 = audit.outcome_v2
    assert ov2["completion_class"] == "present_complete"  # 事实完整，禁止训练
    assert ov2["reason_code"] == "unsafe_artifact_permanent_rejection"
    assert ov2["reward_unavailable"] is True
    assert any("unsafe_symlink_escape" in r for r in audit.unsafe_artifact_reasons)


def test_non_utf8_symlink_target_rejected_fail_closed():
    """B4 修正 c：非 UTF-8 symlink target 不再半支持穿过 B3——typed
    fail-closed（unsafe 家族独立 reason code），B4 应用层不可能再遇到
    裸 UnicodeDecodeError。"""

    bad = b"\xff\xfe-target"
    entry = PatchEntry(
        path="src/badlink", operation="add", object_type="symlink",
        mode="120000",
        content_b64=base64.b64encode(bad).decode(),
        content_digest="sha256:" + hashlib.sha256(bad).hexdigest(),
    )
    report, proj = _classify(_art([entry]))
    assert report.verdict == "unsafe_artifact"
    assert proj is None
    assert any(
        r == "unsupported_symlink_target_encoding:src/badlink"
        for r in report.reason_codes
    )


async def test_baseline_integrity_error_goes_fatal_not_member_loss():
    """B4 P0-1 run-halt e2e：grader 侧 exact-baseline 校验失败（穿队列
    上抛 BaselineIntegrityError）→ generate 转 Fatal（worker run-halt），
    audit 落 grading_baseline_verify 归因；不许转 failed_to_grade 当成员
    损耗继续训练。"""

    import sys
    from pathlib import Path as _P

    sys.path.insert(0, str(_P(__file__).resolve().parents[1] / "adapters"))
    from test_f2_2_capability import _stamp_fa_identity
    from test_slime_generate import (
        SAMPLING_PARAMS,
        _Args,
        _formal_config,
        build_dense_chain,
        dense_turns,
    )

    from repoharness2.adapters.slime.async_worker import (
        FatalExecutionInfrastructureError,
    )
    from repoharness2.adapters.slime.generate import QuiescenceConfirmed
    from repoharness2.grading.manager import BaselineIntegrityError

    class _FrozenWs:
        def __init__(self, u):
            self._u = u

        async def run_bash(self, script):
            return await self._u.run_bash(script)

    class _Barrier:
        async def establish(self, *, workspace, audit):
            return QuiescenceConfirmed(
                frozen_grading_workspace=_FrozenWs(workspace),
                snapshot_ref="sha256:abc", evidence_refs=("s",))

    turns = dense_turns()
    for t in turns:
        t.response["meta_info"]["weight_version"] = "5"
    chain = build_dense_chain(
        config=_formal_config(policy_version="5", execution_mode="fa_formal"),
        runtime_quiescence_barrier=_Barrier(), turns=turns)
    _stamp_fa_identity(chain.base_sample)

    async def _raising_submit(**kw):
        raise BaselineIntegrityError(
            "baseline_digest_mismatch", "fresh checkout 树漂移（测试注入）")

    chain.orchestrator._grading_submit = _raising_submit
    with pytest.raises(FatalExecutionInfrastructureError,
                       match="baseline_digest_mismatch"):
        await chain.orchestrator.generate(
            _Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert any(
        f.stage == "grading_baseline_verify"
        and f.error_type == "baseline_digest_mismatch"
        for f in audit.failure_records
    )
    assert any(
        e.step == "grading_baseline_integrity_mismatch" for e in audit.timeline
    )


async def test_e2e_test_tampering_is_permanent_rejection_no_grader(tmp_path):
    """codex B4 复核 P1-1（T0 失败表 unsafe 行）：修改测试文件的 delta 在
    generate 侧永久拒绝——不运行 grader、reward 不可得、audit 落
    test_file_modified 归因；绝不"剥掉违规文件评剩余 patch"。"""

    import dataclasses
    import sys
    from pathlib import Path as _P

    sys.path.insert(0, str(_P(__file__).resolve().parents[1] / "adapters"))
    from test_f2_2_capability import _stamp_fa_identity
    from test_slime_generate import (
        SAMPLING_PARAMS,
        TASK_ID_DENSE,
        _Args,
        _formal_config,
        build_dense_chain,
        dense_turns,
        make_task,
    )

    from repoharness2.adapters.slime.generate import QuiescenceConfirmed
    from repoharness2.grading.manager import HygieneRules

    content = b"def test_evil():\n    assert True\n"
    sha = hashlib.sha256(content).hexdigest()
    b64 = base64.b64encode(content).decode()

    class _FrozenWs:
        """post census 注入一个被修改的测试文件（模型产物）。"""

        def __init__(self, underlying):
            self._u = underlying

        async def run_bash(self, script):
            from types import SimpleNamespace

            if "find ." in script:
                return SimpleNamespace(exit_code=0, stdout=(
                    f"regular\t100644\t{sha}\ttests/test_evil.py\n"), stderr="")
            if "base64 <" in script:
                return SimpleNamespace(exit_code=0,
                                       stdout=f"tests/test_evil.py\t{b64}\n",
                                       stderr="")
            return await self._u.run_bash(script)

    class _Barrier:
        async def establish(self, *, workspace, audit):
            return QuiescenceConfirmed(
                frozen_grading_workspace=_FrozenWs(workspace),
                snapshot_ref="sha256:abc", evidence_refs=("s",))

    base_task = make_task(TASK_ID_DENSE)
    task = dataclasses.replace(
        base_task,
        grading_spec=dataclasses.replace(
            base_task.grading_spec,
            hygiene=HygieneRules(test_globs=("tests/*",)),
        ),
    )
    turns = dense_turns()
    for t in turns:
        t.response["meta_info"]["weight_version"] = "5"
    chain = build_dense_chain(
        config=_formal_config(policy_version="5", execution_mode="fa_formal"),
        runtime_quiescence_barrier=_Barrier(), turns=turns, task=task)
    _stamp_fa_identity(chain.base_sample)
    delivered = await chain.orchestrator.generate(
        _Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert chain.grading.calls == []  # 不运行 grader
    assert all(getattr(x, "remove_sample", False) for x in delivered)  # 剔除
    ov2 = audit.outcome_v2
    assert ov2["completion_class"] == "present_complete"
    assert ov2["reason_code"] == "unsafe_artifact_permanent_rejection"
    assert ov2["reward_unavailable"] is True
    assert ov2["task_outcome"] == "unknown"  # 没评分，不许伪装成 unresolved
    assert any(r == "test_file_modified:tests/test_evil.py"
               for r in audit.unsafe_artifact_reasons)
