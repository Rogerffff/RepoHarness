"""W1b 第二段：复合 group admission filter 经**真实 miles `DefaultDataBuffer` / `call_dynamic_filter`**
路径的验收——挡板以下真实 fa_formal 生产链，**经过 prepared registry**（复核修复 #6c 起全部用例改走
prepared 链，不再用 legacy v1 任务面）。

链路（全部生产代码，替身只在 W1a/W1b 切片一文档化的注入点）::

    trusted-prep 产物（合成 controller + 外部 manifest SHA）→ stock miles Dataset + RolloutDataSource.get_samples
      → 2 个 prompt 成员（group_index=0，n=2，metadata 五键）
      → Rh2MilesGenerateFn（接线守卫 → W1a 铸造 → F4 registry.bind（prep manifest 核对分派三元组））
      → 真实 RolloutOrchestrator（fa_formal；task/评分材料只经 attempt 绑定；三终态交付面：真实样本 + rh2_admission）
      → 真实 canonicalize + 六字段/分派三元组/termination 事实盖章 → registry.release
      → DefaultDataBuffer.put()（miles stock）→ rh2_group_admission_filter（唯一 dynamic filter）
      → keep=True 进 buffer → get() → postprocess_rollout_data → convert_samples_to_train_data（真实转换）

验收要点（06 计划 §3 W1b 行 + 复核 #4/#6）：全员 KEEP_FULL 才进 conversion；任一不合格整组零样本进 conversion
（keep=False 固定丢弃、不进 unused handler）；zero-variance；prompt_group↔group 对账错位拒绝；结构矛盾 raise
而不是 keep=False；disposition 未注入 fail-fast + 双注入中立；接线守卫；叶版本事实与 Outcome 版本事实绑定；
Outcome 内部身份与六字段对账；分派三键必填；present_truncated 与 miles TRUNCATED 合法不同。
"""

from __future__ import annotations

import copy
import dataclasses
import sys
from argparse import Namespace
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))
from test_w1a_formal_chain import (  # noqa: E402
    POLICY_VERSION,
    SAMPLING_PARAMS,
    SHA_TEMPLATE,
    TS,
    _Barrier,
    _dense_turns,
    _FakeFinalizationStore,
    _mk_leaf,
    _MockSessionAdapter,
)
from test_w1b_prepared_chain import (  # noqa: E402
    _dispatch_groups,
    _load_face_and_registry,
    _PreparedDocker,
)
from w1b_synthetic_tasks import TID1, prepare_synthetic  # noqa: E402

N = 2
GROUP_INDEX = 0


# ---------------------------------------------------------------------------
# 替身/装配
# ---------------------------------------------------------------------------


class _LeafPerCallAdapter(_MockSessionAdapter):
    """每次 finish_session 由工厂按当前派发样本产新叶（同一 chain 服务多个成员）。"""

    def __init__(self, hook, session_defaults, turns, leaf_factory):
        super().__init__(hook, session_defaults, turns, [])
        self._leaf_factory = leaf_factory

    async def finish_session(self, sid, *, base_sample, reward=0.0, extra_metadata=None, wait_timeout=5.0):
        return list(self._leaf_factory(base_sample))


class _SequencedExitDriver:
    """按调用顺序返回 harness exit code（-1 = slime EXIT_TIME_BUDGET_EXCEEDED → hard_wall_timeout）。"""

    name = "mock_harness"

    def __init__(self, adapter_ref, exit_codes):
        self.adapter_ref = adapter_ref
        self._exit_codes = list(exit_codes)

    async def run(self, sandbox, *, workdir, session_id, adapter_url, time_budget_sec, prompt):
        await self.adapter_ref["adapter"].run_all_turns()
        return self._exit_codes.pop(0) if self._exit_codes else 0


def _grading_report(trajectory_id: str, task_id: str, *, kind: str):
    from repoharness2.contracts import GradingReport

    base = {
        "report_id": f"rpt_{trajectory_id}", "trajectory_id": trajectory_id, "task_id": task_id,
        "grader_name": "swebench_official_parser", "grader_version": "swebench-4.1.0",
        "graded_at_utc": TS,
    }
    hygiene = {
        "cleaned_patch_digest": "sha256:" + "d" * 64, "replayed_on_clean_checkout": True,
        "test_files_modified": False, "forbidden_path_touched": False, "forbidden_paths": [], "verdict": "clean",
    }
    if kind == "resolved":
        base.update(outcome="resolved", failure_category=None, reward=1.0, f2p_pass_count=1, f2p_total_count=1,
                    p2p_fail_count=0, p2p_total_count=1, patch_hygiene=hygiene)
    elif kind == "unresolved":
        base.update(outcome="unresolved", failure_category="tests_failed", reward=0.0, f2p_pass_count=0,
                    f2p_total_count=1, p2p_fail_count=0, p2p_total_count=1, patch_hygiene=hygiene)
    elif kind == "infra":
        base.update(outcome="failed_to_grade", failure_category="infra_failure", reward=None,
                    infra_failure_detail="grading_container_killed_oom")
    else:
        raise AssertionError(kind)
    return GradingReport.model_validate(base)


@dataclass
class _Chain:
    orchestrator: Any
    store: _FakeFinalizationStore
    face: Any
    registry: Any
    fx: Any
    grading_calls: list = field(default_factory=list)
    verify_dispatch_calls: list = field(default_factory=list)


def _build_chain(world, tmp_path, *, grading_kinds: dict[str, str],
                 exit_codes: tuple[int, ...] = (0, 0), truncated_slots: tuple[int, ...] = ()) -> _Chain:
    """一条 fa_formal 编排本体服务整组（经 prepared face + registry）：评分结果按 trajectory id 查表。"""

    from repoharness2.adapters.slime import RolloutOrchestrator, SlimeBindingConfig
    from repoharness2.adapters.slime.capture_wire import SessionPlaneDrainResult

    fx = prepare_synthetic(tmp_path)
    face, registry = _load_face_and_registry(fx)
    verify_calls: list = []
    real_verify = registry._verify_dispatch

    def _spy_verify(assignment):
        verify_calls.append(assignment.dispatch_triple())
        return real_verify(assignment)

    registry._verify_dispatch = _spy_verify

    config = SlimeBindingConfig(
        model_name="Qwen/Qwen3-4B", backend_version="0.5.9", renderer_cls_name="Qwen3Renderer",
        expected_renderer_cls_name="Qwen3Renderer", tokenizer_name="Qwen/Qwen3-4B", template_hash=SHA_TEMPLATE,
        adapter_url="http://10.0.0.1:18001", harness_name="mock_harness", expect_moe_routing=False,
        execution_mode="fa_formal", policy_version=POLICY_VERSION, require_real_weight_versions=True,
        reject_context_shrink=True, reject_on_nonzero_harness_exit=True,
        staleness_threshold=4,  # 前置清理批（B-1）起只是 consume-time 阈值的记录用镜像，filter 不读它
    )
    adapter_ref: dict[str, Any] = {}

    def leaf_factory(base_sample):
        leaf = _mk_leaf(world, index=base_sample.index, group_index=base_sample.group_index)
        if (base_sample.index - base_sample.group_index * N) in truncated_slots:
            leaf.metadata = {"truncated": True}  # vendor 的 length/stop 截断事实 → canonicalize 升 TRUNCATED
        return [leaf]

    def adapter_factory(hook, session_defaults):
        adapter = _LeafPerCallAdapter(hook, session_defaults, _dense_turns(), leaf_factory)
        adapter_ref["adapter"] = adapter
        return adapter

    grading_calls: list[str] = []

    async def grading_submit(*, trajectory_id, workspace, spec, **kw):
        grading_calls.append(trajectory_id)
        return _grading_report(trajectory_id, spec.task_id, kind=grading_kinds[trajectory_id])

    async def fake_drain_owner(sid: str):
        return SessionPlaneDrainResult(
            physical_attempt_id=sid.removeprefix("s-"), revoke_enforced=True, inflight_at_drain_start=0,
            inflight_zero_confirmed=True, pending_turns=0, unfinalized_drafts=0, poison_clean=True,
            late_requests_rejected_after_revoke=0, turn_seq_high_water=2,
            weight_versions_seen=[POLICY_VERSION], drain_owner="fake_adapter_loop",
        )

    store = _FakeFinalizationStore()
    orchestrator = RolloutOrchestrator(
        config=config,
        # F4/F6 生产接线形状（bringup._resolve_task / _resolve_grading_spec 同形）
        task_resolver=lambda s: face.rollout_spec(registry.resolve_for_sample(s.metadata).task_id),
        grading_spec_resolver=lambda s: face.grading_spec(registry.resolve_for_sample(s.metadata)),
        adapter_factory=adapter_factory,
        harness_driver=_SequencedExitDriver(adapter_ref, exit_codes), grading_submit=grading_submit,
        docker=_PreparedDocker(), runtime_quiescence_barrier=_Barrier(), finalization_store=store,
        session_drain_owner=fake_drain_owner,
    )
    return _Chain(orchestrator, store, face, registry, fx, grading_calls, verify_calls)


def _miles_args(world, chain: _Chain | None, **over) -> Namespace:
    from repoharness2.adapters.miles.group_admission import GROUP_ADMISSION_FILTER_PATH

    args = world.mk_miles_args(
        n_samples_per_prompt=N, rollout_batch_size=1, global_batch_size=2, rewards_normalization=False,
        dynamic_sampling_filter_path=GROUP_ADMISSION_FILTER_PATH, **over,
    )
    if chain is not None:
        args.rh2_orchestrator = chain.orchestrator
        args.rh2_attempt_assignments = chain.registry
    return args


async def _dispatch_group(world, chain: _Chain):
    """真实 miles Dataset + RolloutDataSource 派发 group_index=0 的 n=2 成员（TID1），返回 (prompt_group, group)。"""

    from miles.rollout.base_types import GenerateFnInput

    fn = world.Rh2MilesGenerateFn()
    args = _miles_args(world, chain)
    prompt_group = _dispatch_groups(chain.fx, n=N)[0]
    assert [s.group_index for s in prompt_group] == [GROUP_INDEX] * N and [s.index for s in prompt_group] == [0, 1]
    group = []
    for sample in prompt_group:
        out = await fn(GenerateFnInput(state=SimpleNamespace(args=args), sample=sample,
                                       sampling_params=dict(SAMPLING_PARAMS), evaluation=False))
        group.append(out.samples)  # miles：每个成员 = GenerateFnOutput.samples（list[Sample]）
    assert len(chain.registry) == 0  # attempt 结束即 release，不延长 registry 生命周期
    return prompt_group, group


def _buffer(world, args):
    from miles.rollout.fully_async_data_buffer import DataBufferConstructorInput, DefaultDataBuffer

    recycled: list = []
    buf = DefaultDataBuffer(DataBufferConstructorInput(args=args, unused_handler_fn=recycled.append))
    return buf, recycled


def _entry(world, prompt_group, group):
    from miles.rollout.fully_async_data_buffer import DataBufferInput

    return DataBufferInput(prompt_group=prompt_group, group=group)


def _convert(world, args, got_group):
    from miles.ray.rollout.rollout_data_conversion import postprocess_rollout_data
    from miles.ray.rollout.train_data_conversion import convert_samples_to_train_data

    data, metadata = postprocess_rollout_data(args, [got_group], train_parallel_config=None)
    return convert_samples_to_train_data(args, data, metadata, None, None)


BOTH_OK = {"miles_g0_m0": "resolved", "miles_g0_m1": "unresolved"}


# ---------------------------------------------------------------------------
# 复核 #6c：真正经过 prepared registry 的生产链 e2e
# ---------------------------------------------------------------------------


async def test_w1b_e2e_prepared_registry_group_admission_to_conversion(world, tmp_path):
    """经过的真实组件：trusted-prep 产物 + 外部 manifest SHA（PreparedTaskFace.load）→ stock miles Dataset /
    RolloutDataSource.get_samples → Rh2MilesGenerateFn（守卫/铸造/registry.bind 经 face.verify_dispatch 核对
    prep manifest）→ RolloutOrchestrator(fa_formal) → canonicalize → registry.release → DefaultDataBuffer.put()
    （复合 filter）→ get() → postprocess_rollout_data → convert_samples_to_train_data。"""

    world.install_sglang_stub()
    chain = _build_chain(world, tmp_path, grading_kinds=BOTH_OK)
    prompt_group, group = await _dispatch_group(world, chain)
    # registry 真的核对过两次分派（每成员一次），三元组 = prep manifest 的 TID1 记录
    rec = chain.fx.manifest.record(TID1)
    assert chain.verify_dispatch_calls == [
        {"task_id": TID1, "environment_package_digest": rec.environment_package_digest,
         "public_bundle_digest": rec.public_bundle_digest}
    ] * 2
    assert chain.grading_calls == ["miles_g0_m0", "miles_g0_m1"]
    for member in group:
        (leaf,) = member
        assert leaf.metadata["task_id"] == TID1 and leaf.metadata["environment_package_digest"] == rec.environment_package_digest
        assert leaf.remove_sample is False and "rh2_admission" in leaf.metadata

    args = _miles_args(world, chain)
    buf, recycled = _buffer(world, args)
    await buf.put(_entry(world, prompt_group, group))
    got = await buf.get(current_version=5)
    assert got.group is group and recycled == []
    td = _convert(world, args, got.group)
    assert td["raw_reward"] == [1.0, 0.0] and all(sum(m) > 0 for m in td["loss_masks"])

    # 同一条链，一名成员 failed_to_grade → 整组零样本进 conversion
    chain2 = _build_chain(world, tmp_path / "second", grading_kinds={"miles_g0_m0": "resolved", "miles_g0_m1": "infra"})
    pg2, g2 = await _dispatch_group(world, chain2)
    buf2, recycled2 = _buffer(world, _miles_args(world, chain2))
    await buf2.put(_entry(world, pg2, g2))
    assert buf2._buffer == [] and recycled2 == []
    assert buf2.get_metrics()["rollout/dynamic_filter/drop_admission_reward_scope_none"] == 1


# ---------------------------------------------------------------------------
# 正例：全员 KEEP_FULL 才进 conversion
# ---------------------------------------------------------------------------


async def test_full_chain_keep_full_group_reaches_real_conversion(world, tmp_path):
    world.install_sglang_stub()
    chain = _build_chain(world, tmp_path, grading_kinds=BOTH_OK)
    prompt_group, group = await _dispatch_group(world, chain)
    for member in group:
        (leaf,) = member
        assert leaf.metadata["training_eligibility_class"] == "online_policy_loss_eligible"
    args = _miles_args(world, chain)
    buf, recycled = _buffer(world, args)
    await buf.put(_entry(world, prompt_group, group))
    got = await buf.get(current_version=5)
    assert got.group is group and recycled == []
    assert not any(k.startswith("rollout/dynamic_filter/drop_") for k in buf.get_metrics())
    td = _convert(world, args, got.group)
    assert td["raw_reward"] == [1.0, 0.0]  # 可信 reward=0 成员完整参与（A6）
    assert td["weight_versions"] == [[POLICY_VERSION, POLICY_VERSION]] * 2


async def test_degraded_member_drops_whole_group_and_nothing_reaches_conversion(world, tmp_path):
    """A2 全员合取：一名成员 failed_to_grade（present、DROP）→ keep=False，固定丢弃（不进
    unused handler、不 retry）；miles 记 drop 指标；零样本进 conversion。"""

    world.install_sglang_stub()
    chain = _build_chain(world, tmp_path, grading_kinds={"miles_g0_m0": "resolved", "miles_g0_m1": "infra"})
    prompt_group, group = await _dispatch_group(world, chain)
    (infra_leaf,) = group[1]
    assert infra_leaf.status is not world.MS.Status.ABORTED and infra_leaf.remove_sample is False
    buf, recycled = _buffer(world, _miles_args(world, chain))
    await buf.put(_entry(world, prompt_group, group))
    assert buf._buffer == [] and recycled == []  # 固定丢弃：不进 buffer、不回收
    metrics = buf.get_metrics()
    assert metrics["rollout/dynamic_filter/drop_admission_reward_scope_none"] == 1
    assert metrics["rollout/fully_async/aborted_groups_filtered"] == 0


async def test_group_without_any_sandbox_sidecar_is_admitted(world, tmp_path):
    """D2-2（取代 W1b 的 `test_missing_capability_facts_drops_group_by_a3`）：整条 fa_formal 链没有
    任何 sandbox 能力事实 provider，合格组照常 keep=True 进 buffer——载荷里的报告 security 维
    通过、evidence 为空，没有 `sandbox_capability_*` 理由码；W1b 的
    `drop_admission_sandbox_capability_facts_missing` 指标不再可达。"""

    world.install_sglang_stub()
    chain = _build_chain(world, tmp_path, grading_kinds=BOTH_OK)
    prompt_group, group = await _dispatch_group(world, chain)
    for member in group:
        (leaf,) = member
        report = leaf.metadata["rh2_admission"]["eligibility_report"]
        security = report["facts"]["security_and_leakage"]
        assert security["ok"] is True and security["evidence_refs"] == []
        assert not any(c.startswith("sandbox_capability") for c in report["reason_codes"])
        assert report["eligibility_class"] == "online_policy_loss_eligible"
    buf, recycled = _buffer(world, _miles_args(world, chain))
    await buf.put(_entry(world, prompt_group, group))
    assert len(buf._buffer) == 1 and recycled == []
    assert not any("sandbox_capability" in k for k in buf.get_metrics())


async def test_zero_variance_group_dropped_by_composite_filter(world, tmp_path):
    world.install_sglang_stub()
    chain = _build_chain(world, tmp_path, grading_kinds={"miles_g0_m0": "resolved", "miles_g0_m1": "resolved"})
    prompt_group, group = await _dispatch_group(world, chain)
    buf, recycled = _buffer(world, _miles_args(world, chain))
    await buf.put(_entry(world, prompt_group, group))
    assert buf._buffer == [] and recycled == []
    assert buf.get_metrics()["rollout/dynamic_filter/drop_zero_std_1.0"] == 1


# ---------------------------------------------------------------------------
# A5：截断成员未注入 fail-fast + 双注入中立（经真实 buffer）
# ---------------------------------------------------------------------------


async def test_truncated_member_fail_fast_without_injection_and_neutral_with(world, tmp_path):
    world.install_sglang_stub()
    from repoharness2.governance.admission import DispositionNotInjectedError, DispositionPolicy

    async def _group(sub):
        chain = _build_chain(world, tmp_path / sub, grading_kinds=BOTH_OK, exit_codes=(0, -1))  # 成员 1 hard wall
        prompt_group, group = await _dispatch_group(world, chain)
        (leaf,) = group[1]
        payload = leaf.metadata["rh2_admission"]
        assert payload["outcome"]["completion_class"] == "present_truncated"
        assert payload["outcome"]["termination_kind"] == "hard_wall_timeout"
        return chain, prompt_group, group

    chain, pg, group = await _group("a")
    buf, _ = _buffer(world, _miles_args(world, chain))
    with pytest.raises(DispositionNotInjectedError, match="hard_wall_truncation"):
        await buf.put(_entry(world, pg, group))

    chain, pg, group = await _group("b")
    buf, recycled = _buffer(world, _miles_args(world, chain, rh2_disposition_policy=DispositionPolicy(hard_wall_truncation="KEEP_FULL")))
    await buf.put(_entry(world, pg, group))
    assert len(buf._buffer) == 1 and recycled == []

    chain, pg, group = await _group("c")
    buf, recycled = _buffer(world, _miles_args(world, chain, rh2_disposition_policy=DispositionPolicy(hard_wall_truncation="DROP_GROUP")))
    await buf.put(_entry(world, pg, group))
    assert buf._buffer == [] and recycled == []
    assert buf.get_metrics()["rollout/dynamic_filter/drop_admission_truncation_hard_wall_excluded"] == 1


async def test_present_truncated_and_miles_truncated_status_are_legally_distinct(world, tmp_path):
    """RH2 的 present_truncated（policy horizon / hard wall / owner control 终止）与 miles
    `Sample.Status.TRUNCATED`（生成请求的 length/stop finish reason）是两个不同事实，可以合法不同：
    - hard wall 成员：Outcome present_truncated，叶 status COMPLETED（生成本身没被截断）；
    - 生成被 length 截断的成员：叶 status TRUNCATED，Outcome present_complete（termination=completed）。
    两者都能通过组准入（前者需显式注入 hard_wall 处置）；filter **不**要求二者相等。"""

    world.install_sglang_stub()
    from repoharness2.governance.admission import DispositionPolicy

    chain = _build_chain(world, tmp_path, grading_kinds=BOTH_OK, exit_codes=(-1, 0), truncated_slots=(1,))
    prompt_group, group = await _dispatch_group(world, chain)
    (hard_wall_leaf,) = group[0]
    (length_truncated_leaf,) = group[1]
    assert hard_wall_leaf.status is world.MS.Status.COMPLETED
    assert hard_wall_leaf.metadata["rh2_admission"]["outcome"]["completion_class"] == "present_truncated"
    assert length_truncated_leaf.status is world.MS.Status.TRUNCATED
    assert length_truncated_leaf.metadata["rh2_admission"]["outcome"]["completion_class"] == "present_complete"
    assert length_truncated_leaf.metadata["rh2_admission"]["outcome"]["termination_kind"] == "completed"
    args = _miles_args(world, chain, rh2_disposition_policy=DispositionPolicy(hard_wall_truncation="KEEP_FULL"))
    buf, recycled = _buffer(world, args)
    await buf.put(_entry(world, prompt_group, group))
    got = await buf.get(current_version=5)
    assert got.group is group and recycled == []
    td = _convert(world, args, got.group)
    assert td["truncated"] == [0, 1]  # miles 训练面看到的是生成截断事实，不是 RH2 的终止族


# ---------------------------------------------------------------------------
# 结构矛盾：raise（不是 keep=False）
# ---------------------------------------------------------------------------


def _admission(leaf) -> dict:
    return leaf.metadata["rh2_admission"]


def _set_outcome_versions(leaf, versions: list[str]):
    """改写载荷 Outcome 的逐轮版本（含派生跨度，保持 Outcome 自身契约合法）。"""

    from repoharness2.contracts.trajectory import derive_weight_version_max_lag

    oc = _admission(leaf)["outcome"]
    oc["turn_weight_versions"] = versions
    oc["intra_execution_version_span"] = derive_weight_version_max_lag(versions)


@pytest.mark.parametrize(
    ("mutate", "reason_code"),
    [
        (lambda g: setattr(g[1][0], "remove_sample", True), "remove_sample_on_delivered_member"),
        (lambda g: g[1][0].metadata.__setitem__("rh2_rollout_execution_id", "miles_g0_m0"), "identity_execution_mismatch"),
        (lambda g: g[1][0].metadata.__setitem__("rh2_physical_attempt_id", "miles_g0_m1#p9-ffffffff"), "identity_attempt_mismatch"),
        (lambda g: g[1][0].metadata.__setitem__("training_eligibility_class", "offline_or_sft_candidate"), "derived_view_mismatch"),
        (lambda g: g[1][0].metadata.__setitem__("environment_package_digest", "sha256:" + "c" * 64), "admission_environment_mismatch"),
        (lambda g: g[1][0].metadata.__setitem__("task_id", "swe_gym_lite::other"), "admission_task_mismatch"),
        # 复核 #6a：分派三键必须在场
        (lambda g: g[1][0].metadata.pop("task_id"), "admission_dispatch_identity_missing"),
        (lambda g: g[1][0].metadata.pop("environment_package_digest"), "admission_dispatch_identity_missing"),
        (lambda g: g[1][0].metadata.pop("public_bundle_digest"), "admission_dispatch_identity_missing"),
        (lambda g: g[1][0].metadata.pop("rh2_admission"), "admission_payload_missing"),
        (lambda g: g[1][0].metadata.pop("rh2_termination_facts"), "termination_facts_unresolvable"),
        (lambda g: setattr(g[1][0], "reward", 0.5), "reward_mismatch_on_delivery"),
        (lambda g: setattr(g[0][0], "loss_mask", [0] * len(g[0][0].loss_mask)), "online_claim_without_trainable_provenance"),
        (lambda g: setattr(g[1][0], "index", 5), "prompt_group_index_mismatch"),
        (lambda g: setattr(g[1][0], "group_index", 7), "prompt_group_index_mismatch"),
        (lambda g: g[1][0].metadata.__setitem__("rh2_member_slot", 0), "identity_execution_mismatch"),
        # 复核 #6b：Outcome 内部身份与六字段对账
        (lambda g: _admission(g[1][0])["outcome"].__setitem__("member_slot", 0), "outcome_identity_mismatch"),
        (lambda g: _admission(g[1][0])["outcome"]["identity"].__setitem__("group_index", 3), "outcome_identity_mismatch"),
        (lambda g: _admission(g[1][0])["outcome"]["identity"].__setitem__("physical_attempt_seq", 2), "outcome_identity_mismatch"),
        # 复核 #4：叶版本事实与 Outcome 版本事实绑定（codex 反例：叶改成未来版本 999，Outcome 仍为 5）
        (lambda g: setattr(g[1][0], "weight_versions", ["999", "999"]), "leaf_version_not_in_outcome"),
        (lambda g: (_set_outcome_versions(g[1][0], ["5", "9"]), setattr(g[1][0], "weight_versions", ["9"])), "leaf_version_ahead_of_finalize"),
        (lambda g: setattr(g[1][0], "weight_versions", []), "version_facts_presence_mismatch"),
        (lambda g: setattr(g[1][0], "weight_versions", ["v5", "v5"]), "version_not_numeric"),
    ],
)
async def test_structural_contradictions_raise_from_real_buffer_put(world, tmp_path, mutate, reason_code):
    world.install_sglang_stub()
    from repoharness2.adapters.miles.group_admission import GroupAdmissionFatal

    chain = _build_chain(world, tmp_path, grading_kinds=BOTH_OK)
    prompt_group, group = await _dispatch_group(world, chain)
    mutate(group)
    buf, recycled = _buffer(world, _miles_args(world, chain))
    with pytest.raises(GroupAdmissionFatal) as info:
        await buf.put(_entry(world, prompt_group, group))
    assert info.value.reason_code == reason_code, info.value
    assert buf._buffer == [] and recycled == []


async def test_negative_consume_time_staleness_reproduction_is_closed_at_filter(world, tmp_path):
    """codex 反例复现：叶 weight_versions=999、Outcome 仍为 5 时，miles get() 的 staleness =
    current − oldest 会算成负数（5 − 999），max_weight_staleness=0 也"满足"。本轮在 filter 侧
    （finalize 事实层）关闭：put() 即 FATAL，组根本进不了 buffer。consume-time 的负 lag 拒绝归 W4。"""

    world.install_sglang_stub()
    from miles.rollout.fully_async_data_buffer import DefaultDataBuffer
    from repoharness2.adapters.miles.group_admission import GroupAdmissionFatal

    chain = _build_chain(world, tmp_path, grading_kinds=BOTH_OK)
    prompt_group, group = await _dispatch_group(world, chain)
    for member in group:
        member[0].weight_versions = ["999", "999"]
    assert DefaultDataBuffer._staleness(group, 5) == 5 - 999  # miles 侧事实：oldest=min(叶 weight_versions) → 负 staleness
    buf, _ = _buffer(world, _miles_args(world, chain, max_weight_staleness=0))
    with pytest.raises(GroupAdmissionFatal, match="leaf_version_not_in_outcome"):
        await buf.put(_entry(world, prompt_group, group))


async def test_facts_digest_tampering_inside_payload_is_fatal(world, tmp_path):
    world.install_sglang_stub()
    from repoharness2.adapters.miles.group_admission import GroupAdmissionFatal

    chain = _build_chain(world, tmp_path, grading_kinds=BOTH_OK)
    prompt_group, group = await _dispatch_group(world, chain)
    payload = _admission(group[1][0])
    payload["eligibility_report"]["facts"]["logprob_alignment"] = {"ok": False, "reason_codes": ["logprob_missing"], "evidence_refs": []}
    buf, _ = _buffer(world, _miles_args(world, chain))
    with pytest.raises(GroupAdmissionFatal, match="admission_payload_invalid"):
        await buf.put(_entry(world, prompt_group, group))


async def test_prompt_group_reconciliation_rejects_wrong_size_and_duplicate_member(world, tmp_path):
    world.install_sglang_stub()
    from repoharness2.adapters.miles.group_admission import GroupAdmissionFatal

    chain = _build_chain(world, tmp_path, grading_kinds=BOTH_OK)
    prompt_group, group = await _dispatch_group(world, chain)
    buf, _ = _buffer(world, _miles_args(world, chain))
    with pytest.raises(GroupAdmissionFatal, match="group_shape_mismatch"):
        await buf.put(_entry(world, prompt_group[:1], group[:1]))  # n=2 却只有 1 个成员
    with pytest.raises(GroupAdmissionFatal, match="member_slot_duplicated"):
        await buf.put(_entry(world, prompt_group, [group[0], group[0]]))  # 同一成员重复交付


async def test_fan_out_leaves_share_identity_subset_versions_ok_but_forged_leaf_is_fatal(world, tmp_path):
    world.install_sglang_stub()
    from repoharness2.adapters.miles.group_admission import GroupAdmissionFatal

    chain = _build_chain(world, tmp_path, grading_kinds=BOTH_OK)
    prompt_group, group = await _dispatch_group(world, chain)
    twin = copy.deepcopy(group[1][0])
    twin.rollout_id = group[1][0].rollout_id
    twin.weight_versions = [POLICY_VERSION]  # 复核 #4：fan-out 叶只回链自己的入训轮——子集合法，不要求集合相等
    group[1].append(twin)
    buf, recycled = _buffer(world, _miles_args(world, chain))
    await buf.put(_entry(world, prompt_group, group))
    assert len(buf._buffer) == 1
    forged = copy.deepcopy(group[1][0])
    forged.metadata["rh2_physical_attempt_id"] = "miles_g0_m1#p2-deadbeef"
    forged.metadata["rh2_physical_attempt_seq"] = 2
    group[1].append(forged)
    buf2, _ = _buffer(world, _miles_args(world, chain))
    with pytest.raises(GroupAdmissionFatal, match="fan_out_leaf_identity_forgery"):
        await buf2.put(_entry(world, prompt_group, group))


async def test_aborted_group_never_reaches_filter_and_filter_rejects_aborted_if_reached(world, tmp_path):
    world.install_sglang_stub()
    from repoharness2.adapters.miles.group_admission import GroupAdmissionFatal, admit_group
    from repoharness2.governance.admission import DispositionPolicy

    chain = _build_chain(world, tmp_path, grading_kinds=BOTH_OK)
    prompt_group, group = await _dispatch_group(world, chain)
    (leaf,) = group[1]
    leaf.status = world.MS.Status.ABORTED
    buf, recycled = _buffer(world, _miles_args(world, chain))
    await buf.put(_entry(world, prompt_group, group))  # miles put() 先交 unused handler，filter 不被调用
    assert recycled == [prompt_group] and buf.get_metrics()["rollout/fully_async/aborted_groups_filtered"] == 1
    with pytest.raises(GroupAdmissionFatal, match="aborted_member_reached_filter"):
        admit_group(group, n_samples_per_prompt=N, disposition_policy=DispositionPolicy(), reward_of=lambda s: s.reward)


# ---------------------------------------------------------------------------
# 接线守卫 / 阈值权威
# ---------------------------------------------------------------------------


async def test_generate_fn_refuses_dispatch_without_admission_filter_wired(world, tmp_path):
    world.install_sglang_stub()
    from miles.rollout.base_types import GenerateFnInput
    from repoharness2.adapters.miles.group_admission import AdmissionWiringError

    chain = _build_chain(world, tmp_path, grading_kinds=BOTH_OK)
    sample = _dispatch_groups(chain.fx, n=N)[0][0]
    for bad in ({}, {"dynamic_sampling_filter_path": None},
                {"dynamic_sampling_filter_path": "miles.rollout.filter_hub.dynamic_sampling_filters.check_reward_nonzero_std"}):
        args = Namespace(rh2_orchestrator=chain.orchestrator, n_samples_per_prompt=N,
                         rh2_attempt_assignments=chain.registry, **bad)
        with pytest.raises(AdmissionWiringError, match="group_admission_filter_not_wired"):
            await world.Rh2MilesGenerateFn()(GenerateFnInput(state=SimpleNamespace(args=args), sample=sample,
                                                             sampling_params=dict(SAMPLING_PARAMS), evaluation=False))
    assert chain.orchestrator.audits == [] and len(chain.registry) == 0  # 守卫先于铸造、绑定与任何生成


async def test_filter_has_no_threshold_authority_and_ignores_config_threshold(world, tmp_path):
    """B-1（取代 W1b 的 `test_threshold_authority_must_be_reachable_and_consistent`）：filter 不再引用
    `args.rh2_orchestrator.config.staleness_threshold`——args 上没有 orchestrator 也能准入；交付后把
    配置镜像改成 8（曾经 `staleness_threshold_authority_mismatch` FATAL）同样准入。过期组只由 miles
    `get()` 按 --max-weight-staleness 判。"""

    world.install_sglang_stub()
    from repoharness2.adapters.miles import group_admission as ga

    assert not hasattr(ga, "_threshold_from_args")
    chain = _build_chain(world, tmp_path, grading_kinds=BOTH_OK)
    prompt_group, group = await _dispatch_group(world, chain)
    buf, recycled = _buffer(world, _miles_args(world, None))  # args 上无 rh2_orchestrator
    await buf.put(_entry(world, prompt_group, group))
    assert len(buf._buffer) == 1 and recycled == []
    chain.orchestrator.config = dataclasses.replace(chain.orchestrator.config, staleness_threshold=8)
    buf2, recycled2 = _buffer(world, _miles_args(world, chain))
    await buf2.put(_entry(world, prompt_group, group))
    assert len(buf2._buffer) == 1 and recycled2 == []
    assert "finalize_staleness_threshold" not in group[0][0].metadata["rh2_admission"]


def test_filter_fatal_notifies_process_level_run_fatal(world, monkeypatch):
    """W5a 复核 #3 接缝：filter 内的结构 fatal 必须经 bringup.notify_run_fatal 触发
    关停链（filter 在 miles put() 内运行，contextvar 通知器够不到），且首因原样传播。"""

    from repoharness2.adapters.miles import group_admission as ga
    from repoharness2.adapters.slime import bringup

    seen: list[BaseException] = []
    monkeypatch.setattr(bringup, "notify_run_fatal", lambda exc: seen.append(exc) or True)
    args = SimpleNamespace(n_samples_per_prompt=1)
    bad_leaf = world.mk_miles_input(index=0, group_index=0)  # 无六字段身份 → identity_missing
    with pytest.raises(ga.GroupAdmissionFatal) as ei:
        ga.rh2_group_admission_filter(args, [bad_leaf])
    assert seen == [ei.value]
