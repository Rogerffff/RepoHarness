"""W1b 第二段：复合 group admission filter 经**真实 miles `DefaultDataBuffer` / `call_dynamic_filter`**
路径的验收（挡板以下真实 fa_formal 生产链产出交付样本）。

链路（全部生产代码，替身只在 W1a 文档化的注入点）::

    2 个 prompt 成员（group_index=0，n=2）→ Rh2MilesGenerateFn（W1a 铸造 + generate_fn 接线守卫）
      → 真实 RolloutOrchestrator（fa_formal，三终态交付面：真实样本 + rh2_admission 载荷）
      → 真实 canonicalize + 六字段/分派/termination 盖章
      → DefaultDataBuffer.put()（miles stock）→ rh2_group_admission_filter（唯一 dynamic filter）
      → keep=True 进 buffer → postprocess_rollout_data → convert_samples_to_train_data（真实转换）

验收要点（06 计划 §3 W1b 行）：全员 KEEP_FULL 才进 conversion；任一不合格整组零样本进 conversion
（keep=False 固定丢弃、不进 unused handler）；zero-variance 过滤；prompt_group↔group 对账错位拒绝；
结构矛盾 raise 而不是 keep=False；disposition 未注入 fail-fast + 双注入中立；接线守卫。
"""

from __future__ import annotations

import copy
import sys
from argparse import Namespace
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
from test_w1a_formal_chain import (  # noqa: E402
    POLICY_VERSION,
    SAMPLING_PARAMS,
    SHA_TEMPLATE,
    TS,
    _Barrier,
    _dense_turns,
    _FakeFinalizationStore,
    _make_fake_docker,
    _make_task,
    _mk_leaf,
    _MockSessionAdapter,
)

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


def _capability_facts_provider(audit):
    from repoharness2.contracts.eligibility import EligibilityReport  # noqa: F401 - 同包
    from repoharness2.governance import REQUIRED_SANDBOX_CAPABILITIES, SandboxCapabilityFacts
    from repoharness2.adapters.slime.generate import _now_utc

    return SandboxCapabilityFacts(
        trajectory_id=audit.trajectory_id,
        lease_id=audit.lease.lease_id if audit.lease is not None else "lease_test",
        verified_capabilities=list(REQUIRED_SANDBOX_CAPABILITIES),
        violations=[], evidence_refs=["sandbox_probe_test"], verified_at_utc=_now_utc(),
    )


@dataclass
class _Chain:
    orchestrator: Any
    store: _FakeFinalizationStore
    grading_calls: list = field(default_factory=list)


def _build_chain(world, *, grading_kinds: dict[str, str], capability_facts: bool = True,
                 exit_codes: tuple[int, ...] = (0, 0)) -> _Chain:
    """一条 fa_formal 编排本体服务整组：评分结果按 trajectory id（miles_g0_m<slot>）查表。"""

    from repoharness2.adapters.slime import RolloutOrchestrator, SlimeBindingConfig
    from repoharness2.adapters.slime.capture_wire import SessionPlaneDrainResult

    config = SlimeBindingConfig(
        model_name="Qwen/Qwen3-4B", backend_version="0.5.9", renderer_cls_name="Qwen3Renderer",
        expected_renderer_cls_name="Qwen3Renderer", tokenizer_name="Qwen/Qwen3-4B", template_hash=SHA_TEMPLATE,
        adapter_url="http://10.0.0.1:18001", harness_name="mock_harness", expect_moe_routing=False,
        execution_mode="fa_formal", policy_version=POLICY_VERSION, require_real_weight_versions=True,
        reject_context_shrink=True, reject_on_nonzero_harness_exit=True,
        staleness_threshold=4,  # 显式传入（数值归 B）
    )
    adapter_ref: dict[str, Any] = {}

    def leaf_factory(base_sample):
        return [_mk_leaf(world, index=base_sample.index, group_index=base_sample.group_index)]

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
        config=config, task_resolver=_make_task(), adapter_factory=adapter_factory,
        harness_driver=_SequencedExitDriver(adapter_ref, exit_codes), grading_submit=grading_submit,
        docker=_make_fake_docker(), runtime_quiescence_barrier=_Barrier(), finalization_store=store,
        session_drain_owner=fake_drain_owner,
        sandbox_capability_facts_provider=_capability_facts_provider if capability_facts else None,
    )
    return _Chain(orchestrator, store, grading_calls)


def _miles_args(world, chain: _Chain | None, **over) -> Namespace:
    from repoharness2.adapters.miles.group_admission import GROUP_ADMISSION_FILTER_PATH

    args = world.mk_miles_args(
        n_samples_per_prompt=N, rollout_batch_size=1, global_batch_size=2, rewards_normalization=False,
        dynamic_sampling_filter_path=GROUP_ADMISSION_FILTER_PATH, **over,
    )
    if chain is not None:
        args.rh2_orchestrator = chain.orchestrator
    return args


async def _dispatch_group(world, chain: _Chain):
    """派发 group_index=0 的 n=2 成员（stock 算术 index = 0,1），返回 (prompt_group, group)。"""

    from miles.rollout.base_types import GenerateFnInput

    fn = world.Rh2MilesGenerateFn()
    args = _miles_args(world, chain)
    prompt_group = [world.mk_miles_input(index=i, group_index=GROUP_INDEX) for i in range(N)]
    group = []
    for sample in prompt_group:
        out = await fn(GenerateFnInput(state=SimpleNamespace(args=args), sample=sample,
                                       sampling_params=dict(SAMPLING_PARAMS), evaluation=False))
        group.append(out.samples)  # miles：每个成员 = GenerateFnOutput.samples（list[Sample]）
    return prompt_group, group


def _buffer(world, args):
    from miles.rollout.fully_async_data_buffer import DataBufferConstructorInput, DefaultDataBuffer

    recycled: list = []
    buf = DefaultDataBuffer(DataBufferConstructorInput(args=args, unused_handler_fn=recycled.append))
    return buf, recycled


def _entry(world, prompt_group, group):
    from miles.rollout.fully_async_data_buffer import DataBufferInput

    return DataBufferInput(prompt_group=prompt_group, group=group)


BOTH_OK = {"miles_g0_m0": "resolved", "miles_g0_m1": "unresolved"}


# ---------------------------------------------------------------------------
# 正例：全员 KEEP_FULL 才进 conversion
# ---------------------------------------------------------------------------


async def test_full_chain_keep_full_group_reaches_real_conversion(world):
    world.install_sglang_stub()
    from miles.ray.rollout.rollout_data_conversion import postprocess_rollout_data
    from miles.ray.rollout.train_data_conversion import convert_samples_to_train_data

    chain = _build_chain(world, grading_kinds=BOTH_OK)
    prompt_group, group = await _dispatch_group(world, chain)
    assert chain.grading_calls == ["miles_g0_m0", "miles_g0_m1"]
    for member in group:
        (leaf,) = member
        assert leaf.remove_sample is False and "rh2_admission" in leaf.metadata
        assert leaf.metadata["training_eligibility_class"] == "online_policy_loss_eligible"

    args = _miles_args(world, chain)
    buf, recycled = _buffer(world, args)
    await buf.put(_entry(world, prompt_group, group))
    got = await buf.get(current_version=5)
    assert got.group is group and recycled == []
    metrics = buf.get_metrics()
    assert not any(k.startswith("rollout/dynamic_filter/drop_") for k in metrics)

    data, metadata = postprocess_rollout_data(args, [got.group], train_parallel_config=None)
    td = convert_samples_to_train_data(args, data, metadata, None, None)
    assert td["raw_reward"] == [1.0, 0.0]  # 可信 reward=0 成员完整参与（A6）
    assert all(sum(m) > 0 for m in td["loss_masks"])
    assert td["weight_versions"] == [[POLICY_VERSION, POLICY_VERSION]] * 2


async def test_degraded_member_drops_whole_group_and_nothing_reaches_conversion(world):
    """A2 全员合取：一名成员 failed_to_grade（present、DROP）→ keep=False，固定丢弃（不进
    unused handler、不 retry）；miles 记 drop 指标；零样本进 conversion。"""

    world.install_sglang_stub()
    chain = _build_chain(world, grading_kinds={"miles_g0_m0": "resolved", "miles_g0_m1": "infra"})
    prompt_group, group = await _dispatch_group(world, chain)
    (infra_leaf,) = group[1]
    assert infra_leaf.status is not world.MS.Status.ABORTED and infra_leaf.remove_sample is False

    args = _miles_args(world, chain)
    buf, recycled = _buffer(world, args)
    await buf.put(_entry(world, prompt_group, group))
    assert buf._buffer == [] and recycled == []  # 固定丢弃：不进 buffer、不回收
    metrics = buf.get_metrics()
    assert metrics["rollout/dynamic_filter/drop_admission_reward_scope_none"] == 1
    assert metrics["rollout/fully_async/aborted_groups_filtered"] == 0


async def test_missing_capability_facts_drops_group_by_a3(world):
    world.install_sglang_stub()
    chain = _build_chain(world, grading_kinds=BOTH_OK, capability_facts=False)
    prompt_group, group = await _dispatch_group(world, chain)
    args = _miles_args(world, chain)
    buf, recycled = _buffer(world, args)
    await buf.put(_entry(world, prompt_group, group))
    assert buf._buffer == [] and recycled == []
    assert buf.get_metrics()["rollout/dynamic_filter/drop_admission_sandbox_capability_facts_missing"] == 1


async def test_zero_variance_group_dropped_by_composite_filter(world):
    world.install_sglang_stub()
    chain = _build_chain(world, grading_kinds={"miles_g0_m0": "resolved", "miles_g0_m1": "resolved"})
    prompt_group, group = await _dispatch_group(world, chain)
    args = _miles_args(world, chain)
    buf, recycled = _buffer(world, args)
    await buf.put(_entry(world, prompt_group, group))
    assert buf._buffer == [] and recycled == []
    assert buf.get_metrics()["rollout/dynamic_filter/drop_zero_std_1.0"] == 1


# ---------------------------------------------------------------------------
# A5：截断成员未注入 fail-fast + 双注入中立（经真实 buffer）
# ---------------------------------------------------------------------------


async def test_truncated_member_fail_fast_without_injection_and_neutral_with(world):
    world.install_sglang_stub()
    from repoharness2.governance.admission import DispositionNotInjectedError, DispositionPolicy

    async def _group():
        chain = _build_chain(world, grading_kinds=BOTH_OK, exit_codes=(0, -1))  # 成员 1 hard wall
        prompt_group, group = await _dispatch_group(world, chain)
        (leaf,) = group[1]
        payload = leaf.metadata["rh2_admission"]
        assert payload["outcome"]["completion_class"] == "present_truncated"
        assert payload["outcome"]["termination_kind"] == "hard_wall_timeout"
        return chain, prompt_group, group

    chain, pg, group = await _group()
    buf, _ = _buffer(world, _miles_args(world, chain))
    with pytest.raises(DispositionNotInjectedError, match="hard_wall_truncation"):
        await buf.put(_entry(world, pg, group))

    chain, pg, group = await _group()
    buf, recycled = _buffer(world, _miles_args(world, chain, rh2_disposition_policy=DispositionPolicy(hard_wall_truncation="KEEP_FULL")))
    await buf.put(_entry(world, pg, group))
    assert len(buf._buffer) == 1 and recycled == []

    chain, pg, group = await _group()
    buf, recycled = _buffer(world, _miles_args(world, chain, rh2_disposition_policy=DispositionPolicy(hard_wall_truncation="DROP_GROUP")))
    await buf.put(_entry(world, pg, group))
    assert buf._buffer == [] and recycled == []
    assert buf.get_metrics()["rollout/dynamic_filter/drop_admission_truncation_hard_wall_excluded"] == 1


# ---------------------------------------------------------------------------
# 结构矛盾：raise（不是 keep=False）
# ---------------------------------------------------------------------------


def _admission(leaf) -> dict:
    return leaf.metadata["rh2_admission"]


@pytest.mark.parametrize(
    ("mutate", "reason_code"),
    [
        (lambda g: setattr(g[1][0], "remove_sample", True), "remove_sample_on_delivered_member"),
        (lambda g: g[1][0].metadata.__setitem__("rh2_rollout_execution_id", "miles_g0_m0"), "identity_execution_mismatch"),
        (lambda g: g[1][0].metadata.__setitem__("rh2_physical_attempt_id", "miles_g0_m1#p9-ffffffff"), "identity_attempt_mismatch"),
        (lambda g: g[1][0].metadata.__setitem__("training_eligibility_class", "offline_or_sft_candidate"), "derived_view_mismatch"),
        (lambda g: g[1][0].metadata.__setitem__("environment_package_digest", "sha256:" + "c" * 64), "admission_environment_mismatch"),
        (lambda g: g[1][0].metadata.__setitem__("task_id", "swe_gym_lite::other"), "admission_task_mismatch"),
        (lambda g: g[1][0].metadata.pop("rh2_admission"), "admission_payload_missing"),
        (lambda g: g[1][0].metadata.pop("rh2_termination_facts"), "termination_facts_unresolvable"),
        (lambda g: setattr(g[1][0], "reward", 0.5), "reward_mismatch_on_delivery"),
        (lambda g: setattr(g[0][0], "loss_mask", [0] * len(g[0][0].loss_mask)), "online_claim_without_trainable_provenance"),
        (lambda g: setattr(g[1][0], "index", 5), "prompt_group_index_mismatch"),
        (lambda g: setattr(g[1][0], "group_index", 7), "prompt_group_index_mismatch"),
        (lambda g: g[1][0].metadata.__setitem__("rh2_member_slot", 0), "identity_execution_mismatch"),
    ],
)
async def test_structural_contradictions_raise_from_real_buffer_put(world, mutate, reason_code):
    world.install_sglang_stub()
    from repoharness2.adapters.miles.group_admission import GroupAdmissionFatal

    chain = _build_chain(world, grading_kinds=BOTH_OK)
    prompt_group, group = await _dispatch_group(world, chain)
    mutate(group)
    buf, recycled = _buffer(world, _miles_args(world, chain))
    with pytest.raises(GroupAdmissionFatal) as info:
        await buf.put(_entry(world, prompt_group, group))
    assert info.value.reason_code == reason_code, info.value
    assert buf._buffer == [] and recycled == []


async def test_facts_digest_tampering_inside_payload_is_fatal(world):
    world.install_sglang_stub()
    from repoharness2.adapters.miles.group_admission import GroupAdmissionFatal

    chain = _build_chain(world, grading_kinds=BOTH_OK)
    prompt_group, group = await _dispatch_group(world, chain)
    payload = _admission(group[1][0])
    payload["eligibility_report"]["facts"]["logprob_alignment"] = {"ok": False, "reason_codes": ["logprob_missing"], "evidence_refs": []}
    buf, _ = _buffer(world, _miles_args(world, chain))
    with pytest.raises(GroupAdmissionFatal, match="admission_payload_invalid"):
        await buf.put(_entry(world, prompt_group, group))


async def test_prompt_group_reconciliation_rejects_wrong_size_and_duplicate_member(world):
    world.install_sglang_stub()
    from repoharness2.adapters.miles.group_admission import GroupAdmissionFatal

    chain = _build_chain(world, grading_kinds=BOTH_OK)
    prompt_group, group = await _dispatch_group(world, chain)
    buf, _ = _buffer(world, _miles_args(world, chain))
    with pytest.raises(GroupAdmissionFatal, match="group_shape_mismatch"):
        await buf.put(_entry(world, prompt_group[:1], group[:1]))  # n=2 却只有 1 个成员
    with pytest.raises(GroupAdmissionFatal, match="member_slot_duplicated"):
        await buf.put(_entry(world, prompt_group, [group[0], group[0]]))  # 同一成员重复交付


async def test_fan_out_leaves_share_identity_but_forged_leaf_is_fatal(world):
    world.install_sglang_stub()
    from repoharness2.adapters.miles.group_admission import GroupAdmissionFatal

    chain = _build_chain(world, grading_kinds=BOTH_OK)
    prompt_group, group = await _dispatch_group(world, chain)
    twin = copy.deepcopy(group[1][0])
    twin.rollout_id = group[1][0].rollout_id
    group[1].append(twin)  # 合法 fan-out：同身份、同载荷
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


async def test_aborted_group_never_reaches_filter_and_filter_rejects_aborted_if_reached(world):
    world.install_sglang_stub()
    from repoharness2.adapters.miles.group_admission import GroupAdmissionFatal, admit_group
    from repoharness2.governance.admission import DispositionPolicy

    chain = _build_chain(world, grading_kinds=BOTH_OK)
    prompt_group, group = await _dispatch_group(world, chain)
    (leaf,) = group[1]
    leaf.status = world.MS.Status.ABORTED
    buf, recycled = _buffer(world, _miles_args(world, chain))
    await buf.put(_entry(world, prompt_group, group))  # miles put() 先交 unused handler，filter 不被调用
    assert recycled == [prompt_group] and buf.get_metrics()["rollout/fully_async/aborted_groups_filtered"] == 1
    with pytest.raises(GroupAdmissionFatal, match="aborted_member_reached_filter"):
        admit_group(group, n_samples_per_prompt=N, disposition_policy=DispositionPolicy(),
                    finalize_staleness_threshold=4, reward_of=lambda s: s.reward)


# ---------------------------------------------------------------------------
# 接线守卫 / 阈值权威
# ---------------------------------------------------------------------------


async def test_generate_fn_refuses_dispatch_without_admission_filter_wired(world):
    world.install_sglang_stub()
    from miles.rollout.base_types import GenerateFnInput
    from repoharness2.adapters.miles.group_admission import AdmissionWiringError

    chain = _build_chain(world, grading_kinds=BOTH_OK)
    sample = world.mk_miles_input(index=0, group_index=0)
    for bad in ({}, {"dynamic_sampling_filter_path": None},
                {"dynamic_sampling_filter_path": "miles.rollout.filter_hub.dynamic_sampling_filters.check_reward_nonzero_std"}):
        args = Namespace(rh2_orchestrator=chain.orchestrator, n_samples_per_prompt=N, **bad)
        with pytest.raises(AdmissionWiringError, match="group_admission_filter_not_wired"):
            await world.Rh2MilesGenerateFn()(GenerateFnInput(state=SimpleNamespace(args=args), sample=sample,
                                                             sampling_params=dict(SAMPLING_PARAMS), evaluation=False))
    assert chain.orchestrator.audits == []  # 守卫先于任何生成


async def test_threshold_authority_must_be_reachable_and_consistent(world):
    world.install_sglang_stub()
    import dataclasses

    from repoharness2.adapters.miles.group_admission import GroupAdmissionFatal

    chain = _build_chain(world, grading_kinds=BOTH_OK)
    prompt_group, group = await _dispatch_group(world, chain)
    buf, _ = _buffer(world, _miles_args(world, None))  # args 上无 rh2_orchestrator
    with pytest.raises(GroupAdmissionFatal, match="staleness_threshold_authority_unreachable"):
        await buf.put(_entry(world, prompt_group, group))
    chain.orchestrator.config = dataclasses.replace(chain.orchestrator.config, staleness_threshold=8)
    buf2, _ = _buffer(world, _miles_args(world, chain))
    with pytest.raises(GroupAdmissionFatal, match="staleness_threshold_authority_mismatch"):
        await buf2.put(_entry(world, prompt_group, group))
