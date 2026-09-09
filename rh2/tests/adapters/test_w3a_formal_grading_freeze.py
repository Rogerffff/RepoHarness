"""W3a（决策包 D2-1，owner 2026-09-04 已批）：formal 评分冻结 —— 状态所有权转移 + 生命周期计时。

被测事实（rh2/src/repoharness2/adapters/slime/generate.py）：
- 正式顺序：屏障确认 → post census / 抓取 → FrozenPatchArtifact + baseline 持久化成功 →
  **立即释放 rollout 容器** → 结构 hygiene / 可信投影 → 有界评分队列 → fresh grader 重建 baseline +
  重放 candidate delta + 评分 → receipt → cleanup 追加；
- **验收前提**：grader 拿不到 rollout 容器（容器已不存在、exec 即炸），唯一输入是持久化的
  FrozenPatchArtifact（从 store 本体 JSON 往返重建即可完成评分，与内存对象 digest 相同）；
- 旧 verify_integrity 主链依赖已删除（源码级钉死：_generate_attempt 不引用它，reason code
  snapshot_integrity_mismatch / integrity_recheck_failed 不再由 producer 发出）；
- 释放失败（docker rm 瞬时失败 / docker 通道异常）不阻塞评分，finally 重试或隔离；
- 未建立 artifact 的 attempt（FIFO 等 unsupported 对象）容器仍保留到 receipt 之后；
- 十三段生命周期计时随 attempt 记录（bringup 的 execution audit JSONL 不改即落盘）+ 可按 run 聚合。
"""

from __future__ import annotations

import base64
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "grading"))
from grading_fixtures import FAILING_FAKE_LOG, GOOD_FAKE_LOG, FakeDocker, make_fixture_spec  # noqa: E402
from test_f2_2_capability import _stamp_fa_identity  # noqa: E402
from test_slime_generate import (  # noqa: E402
    BASE_COMMIT,
    SAMPLING_PARAMS,
    TASK_ID_DENSE,
    FakeFinalizationStore,
    FakeRolloutDocker,
    _Args,
    _formal_config,
    build_dense_chain,
    dense_turns,
    make_task,
)

from repoharness2.adapters.slime import generate as generate_mod  # noqa: E402
from repoharness2.adapters.slime.attempt_timing import (  # noqa: E402
    LIFECYCLE_SEGMENTS,
    aggregate_lifecycle_timings,
    extract_lifecycle_timing,
)
from repoharness2.adapters.slime.generate import QuiescenceConfirmed  # noqa: E402
from repoharness2.contracts.baseline_manifest import BaselineWorkspaceManifestV1  # noqa: E402
from repoharness2.contracts.frozen_patch import FrozenPatchArtifactV1, compute_frozen_patch_digest  # noqa: E402
from repoharness2.grading.manager import (  # noqa: E402
    FrozenDeltaSource,
    GradingManagerConfig,
    SWEGradingManager,
)
from repoharness2.grading.queue import GradingQueue, GradingQueueConfig  # noqa: E402
from repoharness2.grading.trusted_projection import build_trusted_scoring_projection  # noqa: E402

PAID = "exec_F22#p1-cafe1234"


# ---------------------------------------------------------------------------
# 替身：带可配置树内容的冻结 workspace / 屏障
# ---------------------------------------------------------------------------


def _b64(data: bytes) -> tuple[str, str]:
    return base64.b64encode(data).decode(), hashlib.sha256(data).hexdigest()


def make_barrier(regular: dict[str, bytes] | None = None, *, unsupported: str | None = None):
    """屏障替身：post census 罐头 = regular 文件（路径 → 内容）；unsupported 非 None 时输出
    UNSUPPORTED 行（FIFO）。verify_integrity 一旦被调用即炸（W3a：正式链不得再调用）。"""

    regular = regular or {}
    census = "".join(
        f"regular\t100644\t{_b64(content)[1]}\t{path}\n" for path, content in sorted(regular.items())
    )
    if unsupported is not None:
        census += f"UNSUPPORTED\tfifo\t{unsupported}\n"

    class _Ws:
        snapshot_ref = "sha256:abc"

        def __init__(self, underlying):
            self._u = underlying

        async def run_bash(self, script):
            if "find ." in script:
                return SimpleNamespace(exit_code=0, stdout=census, stderr="")
            if "base64 <" in script:
                lines = "".join(f"{p}\t{_b64(c)[0]}\n" for p, c in sorted(regular.items()))
                return SimpleNamespace(exit_code=0, stdout=lines, stderr="")
            return await self._u.run_bash(script)

        async def verify_integrity(self):
            raise AssertionError("W3a：正式链不得再调用 FrozenWorkspace.verify_integrity")

    class _Barrier:
        async def establish(self, *, workspace, audit):
            return QuiescenceConfirmed(
                frozen_grading_workspace=_Ws(workspace), snapshot_ref="sha256:abc", evidence_refs=("s",)
            )

    return _Barrier()


def _grading_task():
    """任务面：评分 spec 用 tests/grading 的 fixture spec（真官方 parser），身份对齐 rollout 侧。"""

    task = make_task(TASK_ID_DENSE)
    spec = make_fixture_spec(
        BASE_COMMIT, "fake-image:v1", checkout_mode="image_embedded", task_id=TASK_ID_DENSE,
    )
    import dataclasses

    return dataclasses.replace(task, grading_spec=spec)


def _formal_chain(*, barrier, docker=None, store=None, task=None, **kwargs):
    turns = dense_turns()
    for t in turns:
        t.response["meta_info"]["weight_version"] = "5"
    chain = build_dense_chain(
        config=_formal_config(policy_version="5", execution_mode="fa_formal"),
        runtime_quiescence_barrier=barrier, turns=turns,
        finalization_store=store or FakeFinalizationStore(),
        docker=docker if docker is not None else FakeRolloutDocker(exec_after_rm_raises=True),
        task=task if task is not None else _grading_task(), **kwargs,
    )
    _stamp_fa_identity(chain.base_sample)
    return chain


def _steps(audit) -> list[str]:
    return [e.step for e in audit.timeline]


class _RealGrader:
    """真实 SWEGradingManager + 有界队列（评分侧 FakeDocker），评分 submit 形状 = bringup._grading_submit。"""

    def __init__(self, *, eval_log: str = GOOD_FAKE_LOG, concurrency: int = 1, queue_size: int = 1):
        self.docker = FakeDocker(base_commit=BASE_COMMIT, eval_log=eval_log)
        self.manager = SWEGradingManager(GradingManagerConfig(), docker=self.docker)
        self.queue = GradingQueue(self.manager, GradingQueueConfig(concurrency=concurrency, queue_size=queue_size))
        self.calls: list[dict] = []

    async def submit(self, *, trajectory_id, workspace, spec, frozen_delta=None, **kwargs):
        self.calls.append({"trajectory_id": trajectory_id, "workspace": workspace, "frozen_delta": frozen_delta, **kwargs})
        return await self.queue.submit(
            trajectory_id=trajectory_id, workspace=workspace, spec=spec, frozen_delta=frozen_delta,
            **kwargs,
        )


# ---------------------------------------------------------------------------
# D2-1：状态所有权转移
# ---------------------------------------------------------------------------


async def test_rollout_container_released_before_grading_and_grader_never_reaches_it():
    """验收前提：评分提交时 rollout 容器已被 docker rm；评分侧 docker 调用面从未出现该容器名；
    释放后任何对它的 exec 都会炸（替身 exec_after_rm_raises）——整条链无一次触碰。"""

    grader = _RealGrader()
    chain = _formal_chain(barrier=make_barrier({"src/fix.py": b"print('fixed')\n"}))
    removed_at_submit: list[list[str]] = []
    real_submit = grader.submit

    async def submit(**kw):
        removed_at_submit.append(list(chain.docker.removed))
        return await real_submit(**kw)

    chain.orchestrator._grading_submit = submit
    chain.orchestrator._grader_phase_timing_source = grader.manager.take_grader_phase_timing
    async with grader.queue:
        delivered = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]

    rollout_container = audit.lease.container_id
    assert removed_at_submit == [[rollout_container]]  # 提交评分时容器已不存在
    assert grader.calls[0]["workspace"] is None
    assert not any(rollout_container in " ".join(c) for c in grader.docker.calls)
    assert audit.rollout_container_released_before_grading is True and audit.lease_released is True
    assert audit.finalized.grading_report.outcome == "resolved"
    assert audit.outcome_v2["completion_class"] == "present_complete"
    assert delivered and all(leaf.remove_sample is False for leaf in delivered)
    steps = _steps(audit)
    assert steps.index("artifact_bodies_persisted") < steps.index("rollout_container_released") < steps.index(
        "grading_started"
    )
    (receipt,) = chain.finalization.receipts
    assert receipt.attempt_disposition == "delivery_prepared" and receipt.artifact_bodies_persisted is True


async def test_grader_completes_from_persisted_artifact_alone():
    """唯一输入 = 持久化产物：评分 submit 无视内存里的 frozen_delta，只从 store 本体 JSON 往返
    重建 artifact/baseline，并用 spec.hygiene 重算投影——digest 与内存对象相同，评分正常完成。"""

    grader = _RealGrader(eval_log=FAILING_FAKE_LOG)
    store = FakeFinalizationStore()
    chain = _formal_chain(barrier=make_barrier({"src/fix.py": b"print('half')\n"}), store=store)
    rebuilt_digests: list[str] = []

    async def submit(*, trajectory_id, workspace, spec, frozen_delta=None, **kwargs):
        assert workspace is None
        body = store.bodies[-1]
        art = FrozenPatchArtifactV1.model_validate(json.loads(body["frozen_patch"].model_dump_json()))
        base = BaselineWorkspaceManifestV1.model_validate(json.loads(body["baseline_manifest"].model_dump_json()))
        projection, _split = build_trusted_scoring_projection(art, spec.hygiene)
        rebuilt = FrozenDeltaSource(
            frozen_patch=art, baseline_manifest=base, projection=projection,
            frozen_patch_digest=compute_frozen_patch_digest(art),
        )
        rebuilt_digests.append(rebuilt.frozen_patch_digest)
        assert rebuilt.frozen_patch_digest == frozen_delta.frozen_patch_digest
        return await grader.manager.grade(trajectory_id=trajectory_id, workspace=None, spec=spec, frozen_delta=rebuilt)

    chain.orchestrator._grading_submit = submit
    await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert rebuilt_digests == [audit.frozen_patch_digest]
    report = audit.finalized.grading_report
    assert report.outcome == "unresolved" and report.failure_category == "tests_failed" and report.reward == 0.0
    assert report.patch_hygiene.verdict == "clean" and report.patch_hygiene.replayed_on_clean_checkout is True
    assert audit.outcome_v2["task_outcome"] == "unresolved" and audit.outcome_v2["reward_unavailable"] is False


def test_verify_integrity_no_longer_referenced_by_the_formal_chain():
    """源码级钉死：_generate_attempt 不再引用 verify_integrity / snapshot_ref，也不再产出
    snapshot_integrity_mismatch / integrity_recheck_failed（reason code 仍在 contracts 封闭集）。"""

    code = generate_mod.RolloutOrchestrator._generate_attempt.__code__
    names = set(code.co_names)
    consts = {c for c in code.co_consts if isinstance(c, str)}
    assert "verify_integrity" not in names  # snapshot_ref 仍作屏障证据引用，合法
    assert "snapshot_integrity_mismatch" not in consts
    assert "integrity_recheck_failed" not in consts
    assert "_release_rollout_container" in names


async def test_release_rm_failure_is_recorded_retried_in_finally_and_does_not_block_grading():
    """docker rm 在释放时刻瞬时失败：评分照常（artifact 已是权威），失败进 cleanup_failures，
    finally 重试成功 → lease_released，hold 段在 finally 才闭合；释放旗标如实为 False。"""

    grader = _RealGrader()
    docker = FakeRolloutDocker(rm_fail_times=1)
    chain = _formal_chain(barrier=make_barrier({"src/fix.py": b"x\n"}), docker=docker)
    chain.orchestrator._grading_submit = grader.submit
    async with grader.queue:
        await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert audit.finalized is not None and audit.finalized.grading_report.outcome == "resolved"
    assert audit.rollout_container_released_before_grading is False
    assert audit.lease_released is True and docker.rm_attempts == 2 and len(docker.removed) == 1
    assert [f.step for f in audit.cleanup_failures] == ["remove_container"]
    steps = _steps(audit)
    assert "rollout_container_release_failed" in steps and "cleanup_completed" in steps
    hold = audit.lifecycle_timing.get("rollout_container_hold_after_freeze")
    assert hold is not None and hold >= 0.0
    assert chain.orchestrator.cleanup_quarantine == []


async def test_release_docker_exception_is_quarantined_grading_still_runs():
    """docker 通道在 rm 时抛 OSError：释放异常结构化落账 + 隔离队列（去重），评分照常。"""

    grader = _RealGrader()
    docker = FakeRolloutDocker()
    orig_call = docker.__call__

    async def flaky(*args, input_bytes=None):
        if args and args[0] == "rm":
            raise OSError("docker socket gone")
        return await orig_call(*args, input_bytes=input_bytes)

    chain = _formal_chain(barrier=make_barrier({"src/fix.py": b"x\n"}), docker=docker)
    chain.orchestrator._docker = flaky
    chain.orchestrator._grading_submit = grader.submit
    async with grader.queue:
        await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert audit.finalized is not None
    assert audit.rollout_container_released_before_grading is False and audit.lease_released is False
    assert [f.step for f in audit.cleanup_failures] == ["container_release_exception", "container_cleanup_exception"]
    assert chain.orchestrator.cleanup_quarantine == [audit.lease.container_id]
    assert audit.lifecycle_timing.get("rollout_container_hold_after_freeze") is None  # 从未确认移除


async def test_unsupported_object_keeps_container_until_receipt():
    """无 artifact 本体（FIFO → unsupported_object_in_patch）：容器是唯一证据，仍按 B5 保留到
    receipt 之后再清理；release 旗标 False。"""

    store = FakeFinalizationStore()
    chain = _formal_chain(barrier=make_barrier(unsupported="evil_pipe"), store=store, docker=FakeRolloutDocker())
    orig = chain.orchestrator._docker

    async def logging_docker(*args, **kw):
        if args and args[0] == "rm":
            store.call_order.append("docker_rm")
        return await orig(*args, **kw)

    chain.orchestrator._docker = logging_docker
    await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert audit.rollout_container_released_before_grading is False
    assert store.call_order.index("persist_receipt") < store.call_order.index("docker_rm")
    assert store.receipts[0].rejection_evidence.object_path == "evil_pipe"
    assert audit.lifecycle_timing.get("post_census") is not None  # 失败前完成的段仍记录
    assert audit.lifecycle_timing.get("artifact_capture") is None


async def test_structural_unsafe_artifact_released_after_persist_without_grading():
    """结构不安全 artifact（symlink 逃逸）：本体持久化 → 释放容器 → unsafe 永久拒绝（不评分）。"""

    target = b"../../etc/passwd"
    tb64 = base64.b64encode(target).decode()
    tsha = hashlib.sha256(target).hexdigest()

    class _Ws:
        snapshot_ref = "sha256:abc"

        def __init__(self, underlying):
            self._u = underlying

        async def run_bash(self, script):
            if "find ." in script:
                return SimpleNamespace(exit_code=0, stdout=f"symlink\t120000\t{tsha}\tsrc/escape\n", stderr="")
            if "readlink" in script:
                return SimpleNamespace(exit_code=0, stdout=f"src/escape\t{tb64}\n", stderr="")
            return await self._u.run_bash(script)

    class _Barrier:
        async def establish(self, *, workspace, audit):
            return QuiescenceConfirmed(frozen_grading_workspace=_Ws(workspace), snapshot_ref="sha256:abc", evidence_refs=("s",))

    chain = _formal_chain(barrier=_Barrier())
    delivered = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert chain.grading.calls == [] and audit.finalized is None
    assert audit.unsafe_artifact_reasons == ["unsafe_symlink_escape:src/escape"]
    assert audit.outcome_v2["reason_code"] == "unsafe_artifact_permanent_rejection"
    assert audit.rollout_container_released_before_grading is True
    assert audit.trusted_projection is None  # 不进投影
    (leaf,) = delivered
    assert leaf.remove_sample is False and "rh2_admission" in leaf.metadata


# ---------------------------------------------------------------------------
# 生命周期计时（W3a 验收项）
# ---------------------------------------------------------------------------


async def test_lifecycle_timing_all_thirteen_segments_recorded_and_persisted(tmp_path):
    """十三段全部记录（grader 六段来自 manager 分段记录）；随 bringup execution audit JSONL 落盘
    （不改 bringup）；sidecar attempt_lifecycle_timing.json 落 artifact_dir；可按 run 聚合 p50/p95。"""

    from repoharness2.adapters.slime.bringup import write_execution_audit_record

    grader = _RealGrader()
    chain = _formal_chain(barrier=make_barrier({"src/fix.py": b"x\n"}), artifact_dir=tmp_path / "rollouts")
    chain.orchestrator._grading_submit = grader.submit
    chain.orchestrator._grader_phase_timing_source = grader.manager.take_grader_phase_timing
    async with grader.queue:
        await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    timing = audit.lifecycle_timing
    missing = [name for name in LIFECYCLE_SEGMENTS if timing.get(name) is None]
    assert missing == [], f"未记录的分段：{missing}"
    assert all(timing.get(name) >= 0.0 for name in LIFECYCLE_SEGMENTS)
    assert timing.grader_segment_source == "manager"
    assert timing.grading_backpressure_triggered is False and timing.grading_queue_depth_at_enqueue == 0
    assert "grader_phase_timing_unavailable" not in _steps(audit)
    # manager 侧记录被取走（不留无界暂存）
    assert grader.manager.take_grader_phase_timing(audit.finalized.grading_report.timings.record_id) is None
    # 与冻结契约 GradingTimingRecord 的 test 段口径一致
    assert timing.get("test") == pytest.approx(audit.finalized.grading_report.timings.test_seconds, abs=1e-3)

    # 落盘 1：bringup execution audit（读取口 = timing_summary，本批未改 bringup）
    jsonl = tmp_path / "audit.jsonl"
    write_execution_audit_record(None, audit, jsonl)
    record = json.loads(jsonl.read_text().strip())
    persisted = extract_lifecycle_timing(record)
    assert persisted is not None and persisted["segments_seconds"] == timing.to_dict()["segments_seconds"]
    assert record["timing_summary"]["rollout_container_released_before_grading"] is True
    # 落盘 2：交付路径 sidecar
    sidecar = tmp_path / "rollouts" / audit.trajectory_id / "attempt_lifecycle_timing.json"
    assert json.loads(sidecar.read_text())["segments_seconds"] == persisted["segments_seconds"]
    projection_sidecar = tmp_path / "rollouts" / audit.trajectory_id / "trusted_scoring_projection.json"
    assert json.loads(projection_sidecar.read_text())["candidate_solution_paths"] == ["src/fix.py"]
    # 聚合（两条同 attempt 记录只为验证形状）
    agg = aggregate_lifecycle_timings([persisted, persisted])
    assert agg["attempts"] == 2 and agg["attempts_with_backpressure"] == 0
    assert agg["segments"]["test"]["count"] == 2 and agg["segments"]["test"]["p95"] == timing.get("test")
    assert agg["grader_segment_source_counts"] == {"manager": 2}


async def test_lifecycle_timing_without_phase_source_falls_back_to_report_only():
    """未注入 grader_phase_timing_source（bringup 尚未接线的形态）：grader 六段只填 test（来自
    GradingTimingRecord），其余 None，时间线留痕 grader_phase_timing_unavailable。"""

    grader = _RealGrader()
    chain = _formal_chain(barrier=make_barrier({"src/fix.py": b"x\n"}))
    chain.orchestrator._grading_submit = grader.submit
    async with grader.queue:
        await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    timing = audit.lifecycle_timing
    assert timing.grader_segment_source == "report_only"
    assert timing.get("test") is not None and timing.get("grading_queue_wait") is not None
    assert all(timing.get(n) is None for n in ("grader_start_and_verify", "grader_baseline_rebuild",
                                               "delta_apply", "parser_and_report", "grader_cleanup"))
    assert "grader_phase_timing_unavailable" in _steps(audit)
    # 非 grader 段照常
    for name in ("runtime_quiescence", "baseline_census", "post_census", "artifact_capture",
                 "artifact_persist", "rollout_container_hold_after_freeze"):
        assert timing.get(name) is not None


async def test_queue_backpressure_is_counted_per_run_and_per_attempt():
    """评分队列打满次数：GradingQueue.backpressure_count（run 级）+ attempt 记录的
    grading_backpressure_triggered（聚合为 attempts_with_backpressure）。"""

    import asyncio

    grader = _RealGrader(concurrency=1, queue_size=1)
    grader.docker.eval_delay = 0.05
    chains = [_formal_chain(barrier=make_barrier({"src/fix.py": b"x\n"})) for _ in range(3)]
    for i, chain in enumerate(chains):
        chain.base_sample.metadata["rh2_physical_attempt_id"] = f"{PAID}-{i}"
        chain.orchestrator._grading_submit = grader.submit
        chain.orchestrator._grader_phase_timing_source = grader.manager.take_grader_phase_timing
    async with grader.queue:
        await asyncio.gather(*(
            chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS)) for chain in chains
        ))
    records = [chain.orchestrator.audits[0].lifecycle_timing.to_dict() for chain in chains]
    agg = aggregate_lifecycle_timings(records)
    assert agg["attempts"] == 3
    assert agg["attempts_with_backpressure"] == grader.queue.backpressure_count
    assert agg["segments"]["grading_queue_wait"]["count"] == 3
    assert agg["segments"]["grading_queue_wait"]["p95"] >= agg["segments"]["grading_queue_wait"]["p50"]
