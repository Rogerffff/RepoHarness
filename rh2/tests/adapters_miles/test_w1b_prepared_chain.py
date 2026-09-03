"""W1b 第一集成切片验收：miles 路径上 prepared artifact 的真实消费链（挡板以下）。

链路（全部生产代码，替身只在 W1a 已文档化的注入点）::

    trusted-prep（合成 controller）→ prompts.jsonl
      → 真实 miles Dataset（--input-key prompt --label-key label --metadata-key metadata）
      → 真实 RolloutDataSource.get_samples（组/index 装配）→ Sample.metadata 五键
      → Rh2MilesGenerateFn（W1a 六字段铸造 → F4 attempt 绑定，bind 时 prep manifest 核对）
      → 真实 RolloutOrchestrator（fa_formal；task/评分材料解析只经 attempt 绑定；
         PreparedTaskFace 在 actor 内从 v2 safe view 构造 grading spec）
      → sandbox public payload / harness prompt / 评分 spec / 交付 miles Sample.metadata
      → F5 termination 事实载荷随交付面回到 miles 侧

验收面（任务书 F6 清单）：真实形状纵链、actor 未调完整 loader、对象图无 golden、private
不进四个面（adapter 请求 / 模型输入 / sandbox payload / Sample.metadata）+ args 只带 opaque
引用、v2 spec 在 actor 内构造、mismatch fail-closed、formal 不可达 v1；F4 join 反例；F5 retry。
"""

from __future__ import annotations

import json
import sys
from argparse import Namespace
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))
from test_w1a_formal_chain import (  # noqa: E402
    POLICY_VERSION,
    SAMPLING_PARAMS,
    SHA_TEMPLATE,
    _Barrier,
    _dense_turns,
    _FakeFinalizationStore,
    _make_fake_docker,
    _make_grading_report,
    _mk_leaf,
    _MockSessionAdapter,
)
from w1b_synthetic_tasks import (  # noqa: E402
    IIDS,
    IMG_DIG,
    TID1,
    TID2,
    golden_content,
    judge_content,
    prepare_synthetic,
)

PUBLIC_BUNDLE_CONTAINER_PATH = "/rh2/public_task_bundle.json"


# ---------------------------------------------------------------------------
# 替身/装配（形状 = test_w1a_formal_chain 的既有 mock 纪律）
# ---------------------------------------------------------------------------


class _LeafFactoryAdapter(_MockSessionAdapter):
    """每次 finish_session 产**新**叶对象（同一 chain 上多次 generate 不共享叶）。"""

    def __init__(self, hook, session_defaults, turns, leaf_factory):
        super().__init__(hook, session_defaults, turns, [])
        self._leaf_factory = leaf_factory

    async def finish_session(self, sid, *, base_sample, reward=0.0, extra_metadata=None, wait_timeout=5.0):
        return list(self._leaf_factory())


class _RecordingDriver:
    name = "mock_harness"

    def __init__(self, adapter_ref):
        self.adapter_ref = adapter_ref
        self.prompts: list[str] = []

    async def run(self, sandbox, *, workdir, session_id, adapter_url, time_budget_sec, prompt):
        self.prompts.append(prompt)
        await self.adapter_ref["adapter"].run_all_turns()
        return 0


class _NoDocker:
    """CPU 无容器面：materialize 确定性失败（abort 收口路径）。"""

    async def __call__(self, *args, input_bytes=None):
        raise FileNotFoundError("docker disabled in CPU test")


class _PreparedDocker:
    """W1a 的 FakeRolloutDocker + 运行期镜像 RepoDigests 应答：prepared 任务面携带真实
    image_manifest_digest（不走 local_build 豁免），编排层会比对容器实际镜像的 RepoDigests。"""

    def __init__(self):
        from repoharness2.grading.manager import ExecResult

        self._inner = _make_fake_docker()
        self._exec_result = ExecResult

    @property
    def writes(self) -> dict[str, bytes]:
        return self._inner.writes

    async def __call__(self, *args, input_bytes=None):
        if args[:4] == ("image", "inspect", "-f", "{{json .RepoDigests}}"):
            repo = "xingyaoww/sweb.eval.x86_64.getmoto_s_moto-1"
            return self._exec_result(0, json.dumps([f"{repo}@{IMG_DIG}"]) + "\n", "")
        return await self._inner(*args, input_bytes=input_bytes)


@dataclass
class _PreparedChain:
    orchestrator: Any
    grading_calls: list
    store: Any
    docker: Any
    driver: _RecordingDriver
    adapter_ref: dict


def _build_prepared_chain(world, *, face, registry, leaf_factory, docker=None) -> _PreparedChain:
    from repoharness2.adapters.slime import RolloutOrchestrator, SlimeBindingConfig
    from repoharness2.adapters.slime.capture_wire import SessionPlaneDrainResult

    config = SlimeBindingConfig(
        model_name="Qwen/Qwen3-4B", backend_version="0.5.9", renderer_cls_name="Qwen3Renderer",
        expected_renderer_cls_name="Qwen3Renderer", tokenizer_name="Qwen/Qwen3-4B",
        template_hash=SHA_TEMPLATE, adapter_url="http://10.0.0.1:18001", harness_name="mock_harness",
        expect_moe_routing=False, execution_mode="fa_formal", policy_version=POLICY_VERSION,
        require_real_weight_versions=True, reject_context_shrink=True, reject_on_nonzero_harness_exit=True,
        staleness_threshold=4,  # 前置清理批（B-1）起只是 consume-time 阈值的记录用镜像，不是资格门
    )
    adapter_ref: dict[str, Any] = {}

    def adapter_factory(hook, session_defaults):
        adapter = _LeafFactoryAdapter(hook, session_defaults, _dense_turns(), leaf_factory)
        adapter_ref["adapter"] = adapter
        return adapter

    grading_calls: list[dict] = []

    async def grading_submit(*, trajectory_id, workspace, spec, **kw):
        grading_calls.append({"trajectory_id": trajectory_id, "spec": spec, "workspace": workspace})
        return _make_grading_report(trajectory_id, spec.task_id)

    async def fake_drain_owner(sid: str):
        return SessionPlaneDrainResult(
            physical_attempt_id=sid.removeprefix("s-"), revoke_enforced=True, inflight_at_drain_start=0,
            inflight_zero_confirmed=True, pending_turns=0, unfinalized_drafts=0, poison_clean=True,
            late_requests_rejected_after_revoke=0, turn_seq_high_water=2,
            weight_versions_seen=[POLICY_VERSION], drain_owner="fake_adapter_loop",
        )

    store = _FakeFinalizationStore()
    docker = docker if docker is not None else _PreparedDocker()
    driver = _RecordingDriver(adapter_ref)
    orchestrator = RolloutOrchestrator(
        config=config,
        # F4/F6 生产接线形状（bringup._resolve_task / _resolve_grading_spec 同形）
        task_resolver=lambda s: face.rollout_spec(registry.resolve_for_sample(s.metadata).task_id),
        grading_spec_resolver=lambda s: face.grading_spec(registry.resolve_for_sample(s.metadata)),
        adapter_factory=adapter_factory,
        harness_driver=driver,
        grading_submit=grading_submit,
        docker=docker,
        runtime_quiescence_barrier=_Barrier(),
        finalization_store=store,
        session_drain_owner=fake_drain_owner,
    )
    return _PreparedChain(orchestrator, grading_calls, store, docker, driver, adapter_ref)


def _load_face_and_registry(fx):
    from repoharness2.adapters.miles.attempt_assignment import AttemptAssignmentRegistry
    from repoharness2.adapters.slime.prepared_task_face import PreparedTaskFace

    face = PreparedTaskFace.load(
        prepared_dir=fx.prepared_dir, manifest_sha256=fx.manifest_sha256, host_grading_path=fx.host_path,
        host_grading_sha256=fx.manifest.host_grading_artifact_sha256,
        time_budget_seconds=600, prompt_data_path=fx.prompts_path,
    )
    return face, AttemptAssignmentRegistry(verify_dispatch=face.verify_dispatch)


def _dispatch_groups(fx, *, n: int):
    """真实 miles Dataset + 真实 RolloutDataSource.get_samples（stock 组/index 装配算术）。"""

    from miles.rollout.data_source import RolloutDataSource
    from miles.utils.data import Dataset

    ds = Dataset(
        str(fx.prompts_path), tokenizer=None, processor=None, max_length=None,
        prompt_key="prompt", label_key="label", metadata_key="metadata",
    )
    src = object.__new__(RolloutDataSource)
    src.args = Namespace(n_samples_per_prompt=n, rollout_shuffle=False)
    src.dataset = ds
    src.epoch_id = 0
    src.sample_group_index = 0
    src.sample_index = 0
    src.sample_offset = 0
    src.metadata = {}
    return src.get_samples(len(ds))


def _args(chain, registry) -> Namespace:
    """miles args 替身：W1b 第二段起非 s1 模式派发要求复合 group filter 已接线。"""

    from repoharness2.adapters.miles.group_admission import GROUP_ADMISSION_FILTER_PATH

    return Namespace(
        rh2_orchestrator=chain.orchestrator, n_samples_per_prompt=2, rh2_attempt_assignments=registry,
        dynamic_sampling_filter_path=GROUP_ADMISSION_FILTER_PATH,
    )


def _gi(world, args, sample):
    from miles.rollout.base_types import GenerateFnInput

    return GenerateFnInput(state=SimpleNamespace(args=args), sample=sample,
                          sampling_params=dict(SAMPLING_PARAMS), evaluation=False)


def _walk(root):
    seen: set[int] = set()
    stack = [root]
    while stack:
        obj = stack.pop()
        if id(obj) in seen:
            continue
        seen.add(id(obj))
        yield obj
        if isinstance(obj, dict):
            stack.extend(obj.keys())
            stack.extend(obj.values())
        elif isinstance(obj, (list, tuple, set, frozenset)):
            stack.extend(obj)
        elif isinstance(obj, BaseModel):
            stack.extend(getattr(obj, name) for name in type(obj).model_fields)
        elif hasattr(obj, "__dict__"):
            stack.extend(vars(obj).values())


# ---------------------------------------------------------------------------
# F6 主验收：真实形状纵链
# ---------------------------------------------------------------------------


async def test_w1b_prepared_chain_real_shape_prompt_to_sandbox_and_delivery(world, tmp_path):
    world.install_sglang_stub()
    from miles.rollout.base_types import GenerateFnOutput
    from repoharness2.adapters.miles import identity as idm
    from repoharness2.contracts import scan_for_forbidden_markers
    from repoharness2.envpack.bundles import PrivateGradingBundle, render_user_prompt
    from repoharness2.envpack.bundles_v2 import PrivateGradingBundleV2, ValidationOnlyBundle
    from repoharness2.envpack.termination_facts import assert_payload_dereferences, resolve_termination_facts

    fx = prepare_synthetic(tmp_path)
    face, registry = _load_face_and_registry(fx)
    groups = _dispatch_groups(fx, n=2)
    assert [[s.group_index for s in g] for g in groups] == [[0, 0], [1, 1]]
    assert [[s.index for s in g] for g in groups] == [[0, 1], [2, 3]]

    # DataSource → Sample.metadata：正是 prompt 行 metadata 五键（miles data.py 直传 + deepcopy）
    sample = groups[1][1]  # TID2，group 1，slot 1
    record = fx.manifest.record(TID2)
    assert sample.metadata == record.model_dump(mode="json")
    assert sample.label == TID2 and sample.status is world.MS.Status.PENDING

    chain = _build_prepared_chain(world, face=face, registry=registry,
                                  leaf_factory=lambda: [_mk_leaf(world, index=3, group_index=1)])
    args = _args(chain, registry)
    out = await world.Rh2MilesGenerateFn()(_gi(world, args, sample))

    # ① resolver 只走 attempt 绑定：任务 = host 分派（TID2），source-qualified id 贯穿 audit/评分
    audit = chain.orchestrator.audits[0]
    assert audit.task_id == TID2 and audit.failure_records == [] and audit.steps[-1] == "step9_samples_delivered"
    assert sample.metadata[idm.EXECUTION_ID_KEY] == "miles_g1_m1"

    # ② sandbox public payload = public bundle 全量 JSON；零私有内容
    view = fx.controller.rollout_view(TID2)
    payload = chain.docker.writes[PUBLIC_BUNDLE_CONTAINER_PATH]
    assert payload == view.public.model_dump_json(indent=2).encode("utf-8")
    assert json.loads(payload)["instance_id"] == IIDS[1]
    for iid in IIDS:
        assert judge_content(iid) not in payload.decode() and golden_content(iid) not in payload.decode()
    # 模型输入（harness prompt）= public bundle 渲染 = prompts.jsonl 的 prompt 字段
    assert chain.driver.prompts == [render_user_prompt(view.public)] == [sample.prompt]
    # adapter 请求面（会话采样默认值）无私有内容
    assert judge_content(IIDS[1]) not in json.dumps(chain.adapter_ref["adapter"].session_defaults)

    # ③ 评分 spec 在 actor 内由 v2 safe view 构造：闭包只捕获 PrivateGradingBundleV2
    (call,) = chain.grading_calls
    spec = call["spec"]
    assert call["trajectory_id"] == "miles_g1_m1" and spec.task_id == TID2
    cells = [c.cell_contents for c in (spec.parse_log.__closure__ or ())]
    assert any(isinstance(c, PrivateGradingBundleV2) for c in cells)
    assert not any(isinstance(c, (PrivateGradingBundle, ValidationOnlyBundle)) for c in cells)
    assert judge_content(IIDS[1]) in spec.eval_script and golden_content(IIDS[1]) not in spec.eval_script

    # ④ 交付 miles 样本：六字段 + 分派三元组 + termination 事实；无私有内容、marker 零命中
    assert isinstance(out, GenerateFnOutput)
    (d,) = out.samples
    assert isinstance(d, world.MS) and d.status is world.MS.Status.COMPLETED and d.reward == 1.0
    for key in idm.IDENTITY_KEYS:
        assert d.metadata[key] == sample.metadata[key], key
    assert d.metadata["task_id"] == TID2
    assert d.metadata["environment_package_digest"] == view.environment_package_digest
    assert d.metadata["public_bundle_digest"] == view.public_bundle_digest
    facts = resolve_termination_facts(d.metadata)
    assert facts.physical_attempt_id == sample.metadata[idm.ATTEMPT_ID_KEY]
    assert facts.rollout_execution_id == "miles_g1_m1" and facts.task_id == TID2
    assert facts.termination_kind == "completed" and facts.fresh_grading_complete
    assert facts.eligibility_report_id == audit.finalized.eligibility_report.report_id
    (receipt,) = chain.store.receipts
    assert_payload_dereferences(facts, receipt)
    meta_json = json.loads(json.dumps(d.metadata, default=str))
    assert scan_for_forbidden_markers(meta_json) == []
    for iid in IIDS:
        assert judge_content(iid) not in json.dumps(meta_json) and golden_content(iid) not in json.dumps(meta_json)

    # ⑤ args 只带 opaque 引用；attempt 结束即 release（旧 attempt id 失效）
    assert len(registry) == 0 and registry.active_attempt_ids() == ()
    assert judge_content(IIDS[1]) not in repr(vars(args))


async def test_w1b_prepared_chain_never_calls_full_loader_and_graph_has_no_golden(world, tmp_path, monkeypatch):
    world.install_sglang_stub()
    import repoharness2.envpack.bundles as bundles_mod
    import repoharness2.envpack.ingest_swegym_lite as ingest
    import repoharness2.envpack.training_view as tv
    from repoharness2.envpack.bundles import PrivateGradingBundle
    from repoharness2.envpack.bundles_v2 import ValidationOnlyBundle

    fx = prepare_synthetic(tmp_path)  # prep 在 actor 侧封锁之前完成（host 进程）

    def _boom(*a, **k):
        raise AssertionError("actor 进程不得调用完整 loader / v1 八题 / controller 构造")

    monkeypatch.setattr(ingest, "load_trusted_ingest_outputs", _boom)
    monkeypatch.setattr(ingest, "load_ingest_outputs", _boom)
    monkeypatch.setattr(tv, "load_trusted_ingest_outputs", _boom)
    monkeypatch.setattr(tv.TrustedTaskController, "_build", classmethod(lambda cls, *a, **k: _boom()))
    monkeypatch.setattr(bundles_mod, "load_bundle_pairs", _boom)

    face, registry = _load_face_and_registry(fx)
    sample = _dispatch_groups(fx, n=2)[0][0]
    chain = _build_prepared_chain(world, face=face, registry=registry,
                                  leaf_factory=lambda: [_mk_leaf(world, index=0, group_index=0)])
    args = _args(chain, registry)
    out = await world.Rh2MilesGenerateFn()(_gi(world, args, sample))
    assert chain.orchestrator.audits[0].steps[-1] == "step9_samples_delivered"

    (call,) = chain.grading_calls
    for obj in _walk((face, registry, chain.orchestrator, call["spec"], args, out.samples)):
        assert not isinstance(obj, (ValidationOnlyBundle, PrivateGradingBundle)), type(obj)
        if isinstance(obj, str):
            for iid in IIDS:
                assert golden_content(iid) not in obj


# ---------------------------------------------------------------------------
# F4：mismatch fail-closed / join 反例
# ---------------------------------------------------------------------------


async def test_w1b_dispatch_pair_swap_and_missing_keys_rejected_at_bind(world, tmp_path):
    world.install_sglang_stub()
    from repoharness2.adapters.miles.attempt_assignment import AttemptAssignmentError

    fx = prepare_synthetic(tmp_path)
    face, registry = _load_face_and_registry(fx)
    fn = world.Rh2MilesGenerateFn()

    # 合法 package A 的 task_id + 合法 package B 的 environment digest：自洽但不是 host 分派
    sample = _dispatch_groups(fx, n=2)[0][0]
    sample.metadata["environment_package_digest"] = fx.manifest.record(TID2).environment_package_digest
    chain = _build_prepared_chain(world, face=face, registry=registry, leaf_factory=list)
    args = _args(chain, registry)
    with pytest.raises(AttemptAssignmentError, match="dispatch_not_authoritative"):
        await fn(_gi(world, args, sample))
    assert chain.orchestrator.audits == [] and len(registry) == 0  # 从未进入生产链、无残留绑定

    # 反向替换：B 的 task_id 配 A 的 digest 对
    sample2 = _dispatch_groups(fx, n=2)[0][1]
    sample2.metadata["task_id"] = TID2
    with pytest.raises(AttemptAssignmentError, match="dispatch_not_authoritative"):
        await fn(_gi(world, args, sample2))

    # legacy 形状（只有 instance_id）的样本进 prepared 链：缺分派键
    sample3 = world.mk_miles_input(index=2, group_index=1)
    sample3.metadata["instance_id"] = IIDS[0]
    with pytest.raises(AttemptAssignmentError, match="dispatch_metadata_missing"):
        await fn(_gi(world, args, sample3))
    assert len(registry) == 0


def test_w1b_registry_join_negatives(world, tmp_path):
    from repoharness2.adapters.miles import identity as idm
    from repoharness2.adapters.miles.attempt_assignment import (
        AttemptAssignmentError,
        AttemptAssignmentRegistry,
        assignment_from_dispatch,
    )

    fx = prepare_synthetic(tmp_path)
    face, registry = _load_face_and_registry(fx)
    rec1 = fx.manifest.record(TID1).model_dump(mode="json")

    def minted(slot: int, seq: int, uid: str) -> dict:
        return {
            idm.GROUP_ID_KEY: "miles_g0", idm.GROUP_INDEX_KEY: 0, idm.EXECUTION_ID_KEY: f"miles_g0_m{slot}",
            idm.MEMBER_SLOT_KEY: slot, idm.ATTEMPT_ID_KEY: f"miles_g0_m{slot}#p{seq}-{uid}", idm.ATTEMPT_SEQ_KEY: seq,
        }

    x = assignment_from_dispatch(rec1, minted(0, 1, "aaaaaaaa"))
    y = assignment_from_dispatch(rec1, minted(1, 1, "bbbbbbbb"))  # 并发同题的另一 member
    registry.bind(x)
    registry.bind(y)
    assert len(registry) == 2

    meta_x = {**rec1, **minted(0, 1, "aaaaaaaa")}
    assert registry.resolve_for_sample(meta_x) == x
    # 并发同题错接：携带 X 的 attempt id、却回显 Y 的 execution/slot
    with pytest.raises(AttemptAssignmentError, match="assignment_echo_mismatch"):
        registry.resolve_for_sample({**meta_x, idm.EXECUTION_ID_KEY: "miles_g0_m1", idm.MEMBER_SLOT_KEY: 1})
    # 回显别的 (task_id, digest) 二元组（合法 package B）
    rec2 = fx.manifest.record(TID2).model_dump(mode="json")
    with pytest.raises(AttemptAssignmentError, match="assignment_echo_mismatch"):
        registry.resolve_for_sample({**meta_x, "task_id": TID2, "environment_package_digest": rec2["environment_package_digest"]})
    # 重复派发同一 attempt
    with pytest.raises(AttemptAssignmentError, match="attempt_already_bound"):
        registry.bind(x)
    # 旧 retry attempt：release 后 id 失效
    assert registry.release(x.physical_attempt_id) is True
    with pytest.raises(AttemptAssignmentError, match="attempt_not_bound"):
        registry.resolve_for_sample(meta_x)
    with pytest.raises(AttemptAssignmentError, match="attempt_not_bound"):
        registry.lookup(x.physical_attempt_id)
    with pytest.raises(AttemptAssignmentError, match="attempt_id_missing"):
        registry.resolve_for_sample({**rec1})
    # 评分材料查找必须经绑定（未绑定的 attempt 拿不到 spec）
    with pytest.raises(AttemptAssignmentError):
        face.grading_spec(registry.resolve_for_sample(meta_x))
    # bind 时 manifest 核对：A 的 task_id + B 的 digest 拒
    swapped = assignment_from_dispatch({**rec1, "public_bundle_digest": rec2["public_bundle_digest"]}, minted(0, 2, "cccccccc"))
    with pytest.raises(AttemptAssignmentError, match="dispatch_not_authoritative"):
        registry.bind(swapped)
    # 有界：容量触顶即拒（不静默增长）
    tiny = AttemptAssignmentRegistry(verify_dispatch=face.verify_dispatch, capacity=1)
    tiny.bind(assignment_from_dispatch(rec1, minted(0, 1, "dddddddd")))
    with pytest.raises(AttemptAssignmentError, match="registry_capacity_exceeded"):
        tiny.bind(assignment_from_dispatch(rec1, minted(1, 1, "eeeeeeee")))


# ---------------------------------------------------------------------------
# F5：retry 换 attempt，事实载荷随之更换；旧事实不可 join
# ---------------------------------------------------------------------------


async def test_w1b_retry_replaces_stale_termination_facts_on_passthrough_sample(world, tmp_path):
    world.install_sglang_stub()
    from repoharness2.adapters.miles import identity as idm
    from repoharness2.envpack.termination_facts import (
        TERMINATION_FACTS_METADATA_KEY,
        TerminationFactsError,
        resolve_termination_facts,
    )

    fx = prepare_synthetic(tmp_path)
    face, registry = _load_face_and_registry(fx)
    sample = _dispatch_groups(fx, n=2)[0][0]
    fn = world.Rh2MilesGenerateFn()

    chain1 = _build_prepared_chain(world, face=face, registry=registry, leaf_factory=list, docker=_NoDocker())
    args1 = _args(chain1, registry)
    (aborted1,) = (await fn(_gi(world, args1, sample))).samples
    assert aborted1 is sample and aborted1.status is world.MS.Status.ABORTED
    paid1 = sample.metadata[idm.ATTEMPT_ID_KEY]
    facts1 = resolve_termination_facts(sample.metadata)
    assert facts1.physical_attempt_id == paid1 and facts1.termination_kind == "sandbox_failure"
    assert facts1.fresh_grading_complete is False
    stale_payload = dict(sample.metadata[TERMINATION_FACTS_METADATA_KEY])
    assert len(registry) == 0

    # miles 真实回收路径：reset_for_retry 保留 metadata（旧事实 + 旧身份在场）→ 重派发
    sample.reset_for_retry()
    chain2 = _build_prepared_chain(world, face=face, registry=registry, leaf_factory=list, docker=_NoDocker())
    args2 = _args(chain2, registry)
    (aborted2,) = (await fn(_gi(world, args2, sample))).samples
    paid2 = sample.metadata[idm.ATTEMPT_ID_KEY]
    assert paid2 != paid1 and sample.metadata[idm.ATTEMPT_SEQ_KEY] == 2
    facts2 = resolve_termination_facts(aborted2.metadata)
    assert facts2.physical_attempt_id == paid2 and facts2.receipt_id != facts1.receipt_id
    # 旧 attempt 的事实放到新 attempt 身份上 → 不可 join
    with pytest.raises(TerminationFactsError, match="attempt"):
        resolve_termination_facts({**aborted2.metadata, TERMINATION_FACTS_METADATA_KEY: stale_payload})
    assert len(registry) == 0


# ---------------------------------------------------------------------------
# F6：formal 不可达 v1（任务面选择）+ bringup 真实装配 prepared 面
# ---------------------------------------------------------------------------


def test_w1b_select_task_face_mode_matrix(world):
    import repoharness2.adapters.slime.bringup as bringup

    assert bringup.select_task_face_mode("fa_audit_only", "/x/prepared") == "prepared"
    assert bringup.select_task_face_mode("fa_formal", "/x/prepared") == "prepared"
    assert bringup.select_task_face_mode("s1_compat", None) == "legacy_v1"
    assert bringup.select_task_face_mode("fa_audit_only", None) == "legacy_v1"
    with pytest.raises(RuntimeError, match="不得静默回退 v1"):
        bringup.select_task_face_mode("fa_formal", None)
    with pytest.raises(RuntimeError, match="s1_compat"):
        bringup.select_task_face_mode("s1_compat", "/x/prepared")


def _strip_reference_slime_paths():
    removed = [p for p in sys.path if "reference/slime" in p]
    for p in removed:
        sys.path.remove(p)
    return removed


def test_w1b_bringup_builds_prepared_face_without_v1_loader(world, monkeypatch, tmp_path):
    """真实 BringupService.__init__（fa_audit_only + prepared 旋钮）：任务面来自 prepared 产物，
    v1 `load_bundle_pairs` 被封死仍能构造；fa_formal 挡板原样在前。tokenizer 缓存缺失即 skip
    （与 test_bringup_vendor_only 同口径）。"""

    from repoharness2.adapters.miles import identity as idm

    removed = _strip_reference_slime_paths()
    try:
        import repoharness2.adapters.slime.bringup as bringup

        fx = prepare_synthetic(tmp_path)
        monkeypatch.setattr(bringup, "ARTIFACT_DIR", tmp_path / "artifacts")
        monkeypatch.setattr(bringup, "ADAPTER_BIND_HOST", "127.0.0.1")
        monkeypatch.setattr(bringup, "ADAPTER_PORT", 0)
        monkeypatch.setattr(bringup, "EXECUTION_MODE", "fa_audit_only")
        monkeypatch.setattr(bringup, "PREPARED_TASKS_DIR", str(fx.prepared_dir))
        monkeypatch.setattr(bringup, "PREPARED_TASKS_MANIFEST_SHA256", fx.manifest_sha256)
        monkeypatch.setattr(bringup, "HOST_GRADING_ARTIFACT_PATH", str(fx.host_path))
        monkeypatch.setattr(bringup, "HOST_GRADING_ARTIFACT_SHA256", fx.manifest.host_grading_artifact_sha256)
        monkeypatch.setenv("HF_HUB_OFFLINE", "1")

        def _boom(*a, **k):
            raise AssertionError("prepared 链不得触碰 v1 load_bundle_pairs")

        monkeypatch.setattr(bringup.bundles, "load_bundle_pairs", _boom)
        args = Namespace(
            hf_checkpoint="Qwen/Qwen3-8B", sglang_router_ip="127.0.0.1", sglang_router_port=59999,
            rollout_max_context_len=0, sglang_tool_call_parser=None, sglang_reasoning_parser=None,
            prompt_data=str(fx.prompts_path),
        )
        try:
            service = bringup.BringupService(args)
        except OSError as exc:
            pytest.skip(f"本机无 Qwen3-8B tokenizer 缓存且离线，跳过：{exc}")
        try:
            assert service.prepared_face is not None and service.pairs is None
            assert set(service.task_specs) == {TID1, TID2}
            assert all(spec.grading_spec is None for spec in service.task_specs.values())
            registry = service.attempt_assignments
            assert registry is not None and len(registry) == 0
            # 真实 resolver：只认 attempt 绑定；未绑定样本被拒（不回退 instance_id 查表）
            from repoharness2.adapters.miles.attempt_assignment import (
                AttemptAssignmentError,
                assignment_from_dispatch,
            )

            rec = fx.manifest.record(TID1).model_dump(mode="json")
            identity = {
                idm.GROUP_ID_KEY: "miles_g0", idm.GROUP_INDEX_KEY: 0, idm.EXECUTION_ID_KEY: "miles_g0_m0",
                idm.MEMBER_SLOT_KEY: 0, idm.ATTEMPT_ID_KEY: "miles_g0_m0#p1-01234567", idm.ATTEMPT_SEQ_KEY: 1,
            }
            unbound = SimpleNamespace(metadata={**rec, **identity}, label=TID1)
            with pytest.raises(AttemptAssignmentError, match="attempt_not_bound"):
                service._resolve_task(unbound)
            registry.bind(assignment_from_dispatch(rec, identity))
            assert service._resolve_task(unbound).task_id == TID1
            gs = service._resolve_grading_spec(unbound)
            assert gs.task_id == TID1 and judge_content(IIDS[0]) in gs.eval_script
        finally:
            service.app_handle.stop()

        # fa_formal 既有挡板原样在前，不因 prepared 旋钮而放行（capture wire 进程级单代，
        # 同进程不能再构造第二个 BringupService——用源码顺序钉死：挡板文本先于任务面选择）。
        src = Path(bringup.__file__).read_text(encoding="utf-8")
        guard_at = src.index('raise RuntimeError(\n                "fa_formal 暂禁')
        face_at = src.index("select_task_face_mode(EXECUTION_MODE, PREPARED_TASKS_DIR)")
        assert 0 < guard_at < face_at
    finally:
        for p in removed:
            sys.path.append(p)
