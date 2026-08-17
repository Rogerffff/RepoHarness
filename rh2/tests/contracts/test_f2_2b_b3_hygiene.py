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


def _art(entries, pathset_changed=False):
    return FrozenPatchArtifactV1(
        task_id="t1", rollout_execution_id="exec_1",
        physical_attempt_id="exec_1#p1-aaaa",
        baseline_manifest_digest="sha256:" + "b" * 64,
        public_bundle_digest="sha256:" + "e" * 64,
        runtime_image_digest="sha256:" + "1" * 64,
        materialized_head="a" * 40,
        entries=tuple(entries), excluded_pathset_changed=pathset_changed,
    )


def _classify(art):
    return classify_frozen_patch(
        art, excluded_namespaces=_NS, frozen_patch_digest="sha256:" + "f" * 64)


def test_projectable_projection_is_reference_only():
    report, proj = _classify(_art([_link_entry("l", b"src/a.py"), _reg_entry("src/a.py")]))
    assert report.verdict == "projectable"
    assert proj.included_entry_paths == ("l", "src/a.py")
    # 引用不复制：projection 无任何内容字段
    assert "content" not in str(sorted(ScoringProjectionArtifactV1.model_fields))


def test_symlink_escape_unsafe_no_projection():
    for target in [b"/etc/passwd", b"../outside", b"a/../../x"]:
        report, proj = _classify(_art([_link_entry("l", target)]))
        assert report.verdict == "unsafe_artifact" and proj is None
        assert any("unsafe_symlink_escape" in r for r in report.reason_codes)
    # 相对不逃逸合法
    report, proj = _classify(_art([_link_entry("l", b"sub/dir/file")]))
    assert report.verdict == "projectable"


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
