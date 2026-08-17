"""F2-2b 验收：DockerQuiescenceBarrier（D1a 屏障序列容器面）。

覆盖：① scope 终止有界验证（残留进程 → termination_timeout）；② 双读
指纹（写者注入 → active_writer_detected；读失败 → snapshot_freeze_failed；
会话未排空 → late_model_request_detected）；③ 冻结出具（Confirmed 带
snapshot_ref + FrozenWorkspace）与评分后完整性复核（漂移 →
snapshot_integrity_mismatch，e2e 收口 missing + abort）。
"""

from __future__ import annotations

from types import SimpleNamespace


from repoharness2.adapters.slime.generate import (
    QuiescenceConfirmed,
    QuiescenceRejected,
)
from repoharness2.adapters.slime.quiescence_barrier import (
    DockerQuiescenceBarrier,
    FrozenWorkspace,
)


class _Exec:
    """run_bash 脚本路由假件：按脚本内容分派 ps/pkill/digest 响应。"""

    def __init__(self, *, ps_counts=("0",), digests=("D1", "D1"), digest_exits=None):
        self.ps_counts = list(ps_counts)
        self.digests = list(digests)
        self.digest_exits = list(digest_exits or [0] * len(digests))
        self.scripts: list[str] = []

    async def run_bash(self, script: str):
        self.scripts.append(script)
        if "pkill" in script:
            return SimpleNamespace(exit_code=0, stdout="", stderr="")
        if "ps -o pid=" in script:
            count = self.ps_counts.pop(0) if self.ps_counts else "0"
            return SimpleNamespace(exit_code=0, stdout=count + "\n", stderr="")
        if "git status" in script:
            body = self.digests.pop(0) if self.digests else "D1"
            code = self.digest_exits.pop(0) if self.digest_exits else 0
            return SimpleNamespace(exit_code=code, stdout=body, stderr="")
        return SimpleNamespace(exit_code=0, stdout="", stderr="")


def _audit(drained: bool = True):
    return SimpleNamespace(session_plane_drained=drained)


async def test_confirmed_with_snapshot_and_frozen_workspace():
    ws = _Exec()
    result = await DockerQuiescenceBarrier().establish(workspace=ws, audit=_audit())
    assert isinstance(result, QuiescenceConfirmed)
    assert result.snapshot_ref.startswith("sha256:")
    assert isinstance(result.frozen_grading_workspace, FrozenWorkspace)
    assert result.frozen_grading_workspace.snapshot_ref == result.snapshot_ref
    # 序列证据：kill 先于 ps 验证先于双读
    assert any("pkill" in s for s in ws.scripts)
    assert "agent_processes_zero" in result.evidence_refs


async def test_session_not_drained_rejected():
    result = await DockerQuiescenceBarrier().establish(
        workspace=_Exec(), audit=_audit(drained=False)
    )
    assert isinstance(result, QuiescenceRejected)
    assert result.reason_code == "late_model_request_detected"


async def test_residual_processes_rejected_bounded():
    # 进程数始终为 2 → 有界重试后 termination_timeout（不无限等）
    import repoharness2.adapters.slime.quiescence_barrier as qb

    real_attempts = qb._KILL_VERIFY_ATTEMPTS
    real_interval = qb._KILL_VERIFY_INTERVAL_SECONDS
    qb._KILL_VERIFY_ATTEMPTS = 3
    qb._KILL_VERIFY_INTERVAL_SECONDS = 0.0
    try:
        ws = _Exec(ps_counts=["2", "2", "2"])
        result = await DockerQuiescenceBarrier().establish(workspace=ws, audit=_audit())
    finally:
        qb._KILL_VERIFY_ATTEMPTS = real_attempts
        qb._KILL_VERIFY_INTERVAL_SECONDS = real_interval
    assert isinstance(result, QuiescenceRejected)
    assert result.reason_code == "execution_scope_termination_timeout"
    assert "residual_agent_processes:2" in result.evidence_refs


async def test_active_writer_between_reads_rejected():
    ws = _Exec(digests=["D1", "D2-CHANGED"])
    result = await DockerQuiescenceBarrier().establish(workspace=ws, audit=_audit())
    assert isinstance(result, QuiescenceRejected)
    assert result.reason_code == "active_writer_detected"


async def test_digest_read_failure_rejected():
    ws = _Exec(digests=["boom", "x"], digest_exits=[1, 0])
    result = await DockerQuiescenceBarrier().establish(workspace=ws, audit=_audit())
    assert isinstance(result, QuiescenceRejected)
    assert result.reason_code == "snapshot_freeze_failed"


async def test_frozen_workspace_integrity_recheck():
    ws = _Exec(digests=["D1", "D1", "D1"])  # 第三读 = 评分后复核，一致
    confirmed = await DockerQuiescenceBarrier().establish(workspace=ws, audit=_audit())
    frozen = confirmed.frozen_grading_workspace
    assert await frozen.verify_integrity() is True
    ws2 = _Exec(digests=["D1", "D1", "DRIFTED"])
    confirmed2 = await DockerQuiescenceBarrier().establish(workspace=ws2, audit=_audit())
    assert await confirmed2.frozen_grading_workspace.verify_integrity() is False


async def test_e2e_integrity_drift_after_grading_closes_as_missing():
    """③ e2e：屏障确认 → 评分正常 → 评分后指纹漂移 → 评分结果作废，
    outcome = missing + snapshot_integrity_mismatch + abort 形状。"""

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

    class _DriftingFrozen:
        snapshot_ref = "sha256:frozen0"

        def __init__(self, underlying):
            self._u = underlying

        async def run_bash(self, script):
            return await self._u.run_bash(script)

        async def verify_integrity(self):
            return False  # 评分后复核：漂移

    class _Barrier:
        async def establish(self, *, workspace, audit):
            return QuiescenceConfirmed(
                frozen_grading_workspace=_DriftingFrozen(workspace),
                snapshot_ref="sha256:frozen0",
                evidence_refs=("e",),
            )

    turns = dense_turns()
    for t in turns:
        t.response["meta_info"]["weight_version"] = "5"
    chain = build_dense_chain(
        config=_formal_config(policy_version="5", execution_mode="fa_formal"),
        runtime_quiescence_barrier=_Barrier(),
        turns=turns,
    )
    _stamp_fa_identity(chain.base_sample)
    delivered = await chain.orchestrator.generate(
        _Args(), chain.base_sample, dict(SAMPLING_PARAMS)
    )
    audit = chain.orchestrator.audits[0]
    assert chain.grading.calls  # 评分发生过（漂移在评分后才发现）
    assert all(getattr(x, "remove_sample", False) for x in delivered)  # 作废
    ov2 = audit.outcome_v2
    assert ov2["completion_class"] == "missing"
    assert ov2["failure_category"] == "runtime_quiescence_failure"
    assert ov2["reason_code"] == "snapshot_integrity_mismatch"
    assert "snapshot:sha256:frozen0" in ov2["evidence_refs"]


async def test_e2e_real_barrier_class_confirms_and_grades_frozen():
    """真实 DockerQuiescenceBarrier 接入正式链（mock 容器 exec）：评分
    收到 FrozenWorkspace（同一性），outcome present_complete。"""

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

    turns = dense_turns()
    for t in turns:
        t.response["meta_info"]["weight_version"] = "5"
    chain = build_dense_chain(
        config=_formal_config(policy_version="5", execution_mode="fa_formal"),
        runtime_quiescence_barrier=DockerQuiescenceBarrier(),
        turns=turns,
    )
    _stamp_fa_identity(chain.base_sample)

    # 把 workspace 的 run_bash 换成脚本路由假件（真实容器归 FA-5）
    stub = _Exec(digests=["D1", "D1", "D1"])
    real_materialize = chain.orchestrator._materialize_rollout_sandbox

    async def patched_materialize(task, trajectory_id, audit):
        sandbox = await real_materialize(task, trajectory_id, audit)
        # workspace 为 frozen dataclass——测试注入走 object.__setattr__
        object.__setattr__(sandbox.workspace, "run_bash", stub.run_bash)
        return sandbox

    chain.orchestrator._materialize_rollout_sandbox = patched_materialize
    delivered = await chain.orchestrator.generate(
        _Args(), chain.base_sample, dict(SAMPLING_PARAMS)
    )
    audit = chain.orchestrator.audits[0]
    assert isinstance(chain.grading.calls[0]["workspace"], FrozenWorkspace)
    assert audit.runtime_quiescence_confirmed is True
    assert audit.outcome_v2["completion_class"] == "present_complete"
    assert any(not getattr(x, "remove_sample", False) for x in delivered)
