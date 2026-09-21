"""I21（第五组）：评测公共入口的真实运输——`Rh2MilesGenerateFn(evaluation=True)` → 真实
`RolloutOrchestrator`（fa_formal）→ 交付叶 / audit 行。

链路与 `test_w1b_prepared_chain.py` 同一套注入点（替身只在 W1a 已文档化的位置）；评测样本形状照
miles `inference_rollout_eval.eval_rollout_single_dataset`：deepcopy 数据集样本、扁平 `index`、
`group_index=None`，宿主派发事实由集成分支 patch 0018 盖章（这里在样本上直接给出同一形状；真实 fork
函数的盖章见 `test_i21_eval_fork_seams.py`，lane B）。

验收面：评了分 / 评不了分 / 没跑成三类分开（不记 0 分）；评测不要求组准入 filter、不产训练
admission 载荷；两个平面各绑各的题包（同一份题包可以同时配给两个平面，代码不设互斥）；audit 行的
`evaluation` 块与交付叶载荷出自同一份事实；训练派发不受影响。
"""

from __future__ import annotations

import copy
import json
import sys
from argparse import Namespace
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
    _Barrier,
    _dense_turns,
    _FakeFinalizationStore,
    _make_grading_report,
    _mk_leaf,
)
from test_w1b_prepared_chain import (  # noqa: E402
    _LeafFactoryAdapter,
    _NoDocker,
    _PreparedDocker,
    _RecordingDriver,
    _dispatch_groups,
)
from sandbox_test_support import formal_sandbox_kwargs  # noqa: E402
from w1b_synthetic_tasks import IIDS, TID1, TID2, prepare_synthetic  # noqa: E402

POINT = "0123abcd4567"


def _report(kind: str, trajectory_id: str, task_id: str):
    from repoharness2.contracts import GradingReport

    body = _make_grading_report(trajectory_id, task_id).model_dump(mode="json")
    if kind == "unresolved":
        body.update(outcome="unresolved", failure_category="tests_failed", reward=0.0, f2p_pass_count=0)
    elif kind == "failed_to_grade":
        body.update(outcome="failed_to_grade", failure_category="infra_failure", reward=None,
                    infra_failure_detail="grading_container_killed", patch_hygiene=None,
                    f2p_pass_count=None, f2p_total_count=None, p2p_fail_count=None, p2p_total_count=None)
    return GradingReport.model_validate(body)


def _load_face(fx, *, prompts: bool = True):
    from repoharness2.adapters.slime.prepared_task_face import PreparedTaskFace

    return PreparedTaskFace.load(
        prepared_dir=fx.prepared_dir, manifest_sha256=fx.manifest_sha256, host_grading_path=fx.host_path,
        host_grading_sha256=fx.manifest.host_grading_artifact_sha256, time_budget_seconds=600,
        prompt_data_path=fx.prompts_path if prompts else None,
    )


def _registry(train_face, eval_face):
    """bringup `_verify_dispatch_by_plane` 同形：评测 attempt 只认评测题包、训练 attempt 只认训练题包。"""

    from repoharness2.adapters.miles.attempt_assignment import AttemptAssignmentRegistry

    def face_for(assignment):
        face = eval_face if assignment.evaluation else train_face
        if face is None:
            raise RuntimeError("该平面没有配置题包")
        return face

    return AttemptAssignmentRegistry(verify_dispatch=lambda a: face_for(a).verify_dispatch(a)), face_for


def _chain(world, *, registry, face_for, grading_kind: str = "resolved", docker=None, leaf_factory=None):
    from repoharness2.adapters.slime import RolloutOrchestrator, SlimeBindingConfig
    from repoharness2.adapters.slime.capture_wire import SessionPlaneDrainResult

    config = SlimeBindingConfig(
        model_name="Qwen/Qwen3-4B", backend_version="0.5.9", renderer_cls_name="Qwen3Renderer",
        expected_renderer_cls_name="Qwen3Renderer", tokenizer_name="Qwen/Qwen3-4B", template_hash=SHA_TEMPLATE,
        adapter_url="http://10.0.0.1:18001", harness_name="mock_harness", expect_moe_routing=False,
        execution_mode="fa_formal", policy_version=POLICY_VERSION, require_real_weight_versions=True,
        reject_on_nonzero_harness_exit=True, staleness_threshold=4,
    )
    adapter_ref: dict[str, Any] = {}

    def adapter_factory(hook, session_defaults):
        adapter_ref["adapter"] = _LeafFactoryAdapter(
            hook, session_defaults, _dense_turns(), leaf_factory or (lambda: [_mk_leaf(world, index=0, group_index=0)])
        )
        return adapter_ref["adapter"]

    grading_calls: list[dict] = []

    async def grading_submit(*, trajectory_id, workspace, spec, **kw):
        grading_calls.append({"trajectory_id": trajectory_id, "task_id": spec.task_id})
        return _report(grading_kind, trajectory_id, spec.task_id)

    async def drain_owner(sid: str):
        return SessionPlaneDrainResult(
            physical_attempt_id=sid.removeprefix("s-"), revoke_enforced=True, inflight_at_drain_start=0,
            inflight_zero_confirmed=True, pending_turns=0, unfinalized_drafts=0, poison_clean=True,
            late_requests_rejected_after_revoke=0, turn_seq_high_water=2,
            weight_versions_seen=[POLICY_VERSION], drain_owner="fake_adapter_loop",
        )

    store = _FakeFinalizationStore()
    orchestrator = RolloutOrchestrator(
        config=config,
        task_resolver=lambda s: (lambda a: face_for(a).rollout_spec(a.task_id))(registry.resolve_for_sample(s.metadata)),
        grading_spec_resolver=lambda s: (lambda a: face_for(a).grading_spec(a))(registry.resolve_for_sample(s.metadata)),
        adapter_factory=adapter_factory, harness_driver=_RecordingDriver(adapter_ref), grading_submit=grading_submit,
        docker=docker if docker is not None else _PreparedDocker(), runtime_quiescence_barrier=_Barrier(),
        finalization_store=store, session_drain_owner=drain_owner, **formal_sandbox_kwargs(),
    )
    return SimpleNamespace(orchestrator=orchestrator, grading_calls=grading_calls, store=store)


def _eval_samples(fx, *, n: int = 1, point: str = POINT, rollout_id: int | None = 0, target: str | None = POLICY_VERSION):
    """miles eval 样本形状 + patch 0018 的宿主派发事实。"""

    from miles.utils.data import Dataset

    ds = Dataset(str(fx.prompts_path), tokenizer=None, processor=None, max_length=None,
                 prompt_key="prompt", label_key="label", metadata_key="metadata")
    out, index = [], 0
    for pi, prompt_sample in enumerate(ds.samples):
        for slot in range(n):
            sample = copy.deepcopy(prompt_sample)
            sample.index = index
            index += 1
            sample.metadata = {**(sample.metadata or {}), "rh2_eval_dispatch": {
                "eval_point_id": point, "eval_rollout_id": rollout_id, "target_weight_version": target, "hf_dir": None,
                "dataset": "swe_dev", "dataset_index": 0, "prompt_index": pi, "sample_slot": slot,
                "n_samples_per_eval_prompt": n, "num_prompts": len(ds.samples),
            }}
            out.append(sample)
    return out


def _gi(args, sample, *, evaluation: bool):
    from miles.rollout.base_types import GenerateFnInput

    return GenerateFnInput(state=SimpleNamespace(args=args), sample=sample, sampling_params=dict(SAMPLING_PARAMS), evaluation=evaluation)


@pytest.fixture
def host_stamp(world, monkeypatch):
    """lane A（stock pin 树）没有 patch 0018 的模块标记；这些用例验证的是 RH2 侧运输，标记能力单独测。"""

    world.install_sglang_stub()
    from repoharness2.adapters.miles import generate_fn as gf

    monkeypatch.setattr(gf, "_eval_host_stamp_supported", lambda: True)
    return gf


@pytest.mark.parametrize(
    ("kind", "status", "reward", "result_class", "task_outcome"),
    [
        ("resolved", "COMPLETED", 1.0, "graded", "resolved"),
        ("unresolved", "COMPLETED", 0.0, "graded", "unresolved"),
        ("failed_to_grade", "ABORTED", None, "reward_unavailable", None),
    ],
)
async def test_eval_dispatch_delivers_typed_result_and_never_books_missing_reward_as_zero(
    world, host_stamp, tmp_path, kind, status, reward, result_class, task_outcome
):
    from repoharness2.adapters.miles import identity as idm
    from repoharness2.adapters.slime.bringup import write_execution_audit_record
    from repoharness2.adapters.slime.eval_result import EVAL_RESULT_METADATA_KEY
    from repoharness2.governance.admission import ADMISSION_METADATA_KEY

    fx = prepare_synthetic(tmp_path / "eval")
    eval_face = _load_face(fx)
    registry, face_for = _registry(None, eval_face)  # 只配了评测题包（独立评测作业形态）
    chain = _chain(world, registry=registry, face_for=face_for, grading_kind=kind)
    sample = _eval_samples(fx)[1]
    assert sample.group_index is None and sample.label == TID2  # eval 样本没有训练组事实
    # 评测不要求组准入 filter，也不需要 n_samples_per_prompt
    args = Namespace(rh2_orchestrator=chain.orchestrator, rh2_attempt_assignments=registry, hf_checkpoint="/ckpt/hf_step_20")

    (delivered,) = (await world.Rh2MilesGenerateFn()(_gi(args, sample, evaluation=True))).samples

    assert isinstance(delivered, world.MS) and delivered.status is getattr(world.MS.Status, status)
    assert delivered.reward == reward and delivered.remove_sample is True
    payload = delivered.metadata[EVAL_RESULT_METADATA_KEY]
    assert (payload["result_class"], payload["task_outcome"], payload["reward"]) == (result_class, task_outcome, reward)
    assert payload["task_id"] == TID2 and payload["eval"]["eval_point_id"] == POINT and payload["eval"]["prompt_index"] == 1
    assert payload["turn_weight_versions"] and set(payload["turn_weight_versions"]) == {POLICY_VERSION}
    assert payload["model_name"] == "Qwen/Qwen3-4B" and payload["time_budget_seconds"] == 600
    assert payload["configured_hf_checkpoint"] == "/ckpt/hf_step_20"  # 配置来源（args.hf_checkpoint），不是权重已加载的证明
    if kind == "unresolved":
        assert payload["grading_failure_category"] == "tests_failed"  # 修复失败：评分侧类别随载荷，供逐题检查
    if kind == "failed_to_grade":
        assert payload["unavailable_reason"] == "grading:infra_failure" and "grading_container_killed" in payload["unavailable_detail"]
    # 身份 = 评测命名空间，载荷与叶身份一致；分派三元组照常盖章；没有训练 admission 载荷
    assert delivered.metadata[idm.GROUP_ID_KEY] == f"eval-{POINT}-d0-p1"
    assert payload["physical_attempt_id"] == delivered.metadata[idm.ATTEMPT_ID_KEY]
    assert delivered.metadata["task_id"] == TID2 and ADMISSION_METADATA_KEY not in delivered.metadata
    assert len(registry) == 0  # attempt 结束即 release

    audit = chain.orchestrator.audits[0]
    assert audit.evaluation is True and audit.eval_dispatch["eval_point_id"] == POINT
    identity = audit.outcome_v2["identity"]  # 正式链的 Outcome v2 / receipt 按评测命名空间的六字段 join，消费者不用改
    assert identity["rollout_execution_id"] == f"eval-{POINT}-d0-p1_m0" and identity["prompt_group_id"] == f"eval-{POINT}-d0-p1"
    assert chain.store.receipts and chain.store.receipts[0].outcome_v2.identity.rollout_execution_id == identity["rollout_execution_id"]
    # audit 行的 evaluation 块与交付叶载荷出自同一份事实（sink 先于出口盖章执行，也不会分家）
    row_path = tmp_path / "audit.jsonl"
    write_execution_audit_record(None, audit, row_path, model_name="Qwen/Qwen3-4B")
    assert json.loads(row_path.read_text().strip())["evaluation"] == json.loads(json.dumps(payload))


async def test_eval_attempt_that_never_ran_is_execution_missing_not_zero(world, host_stamp, tmp_path):
    from repoharness2.adapters.slime.eval_result import EVAL_RESULT_METADATA_KEY

    fx = prepare_synthetic(tmp_path / "eval")
    registry, face_for = _registry(None, _load_face(fx))
    chain = _chain(world, registry=registry, face_for=face_for, docker=_NoDocker())  # materialize 确定性失败
    args = Namespace(rh2_orchestrator=chain.orchestrator, rh2_attempt_assignments=registry)

    (delivered,) = (await world.Rh2MilesGenerateFn()(_gi(args, _eval_samples(fx)[0], evaluation=True))).samples

    assert delivered.status is world.MS.Status.ABORTED and delivered.reward is None  # 不是 _abort_result 的 0.0
    payload = delivered.metadata[EVAL_RESULT_METADATA_KEY]
    assert payload["result_class"] == "execution_missing" and payload["completion_class"] == "missing"
    assert payload["unavailable_reason"] and payload["reward"] is None and chain.grading_calls == []


async def test_planes_bind_to_their_own_package_and_may_share_tasks(world, host_stamp, tmp_path):
    from repoharness2.adapters.miles.attempt_assignment import AttemptAssignmentError
    from repoharness2.adapters.miles.group_admission import GROUP_ADMISSION_FILTER_PATH
    from repoharness2.adapters.slime.eval_result import EVAL_RESULT_METADATA_KEY

    train_fx = prepare_synthetic(tmp_path / "train", iids=(IIDS[0],))   # 训练题包只有 TID1
    eval_fx = prepare_synthetic(tmp_path / "eval")                      # 评测题包 TID1 + TID2（与训练有交集：不设互斥）
    registry, face_for = _registry(_load_face(train_fx), _load_face(eval_fx))
    chain = _chain(world, registry=registry, face_for=face_for)
    fn = world.Rh2MilesGenerateFn()
    args = Namespace(rh2_orchestrator=chain.orchestrator, rh2_attempt_assignments=registry,
                     n_samples_per_prompt=1, dynamic_sampling_filter_path=GROUP_ADMISSION_FILTER_PATH)

    # 同一道 TID1：评测派发走评测题包、训练派发走训练题包，互不影响
    eval_tid1 = _eval_samples(eval_fx)[0]
    (evaluated,) = (await fn(_gi(args, eval_tid1, evaluation=True))).samples
    assert evaluated.metadata[EVAL_RESULT_METADATA_KEY]["task_id"] == TID1
    ((train_tid1,),) = _dispatch_groups(train_fx, n=1)
    (trained,) = (await fn(_gi(args, train_tid1, evaluation=False))).samples
    assert EVAL_RESULT_METADATA_KEY not in trained.metadata and trained.metadata["rh2_prompt_group_id"] == "miles_g0"

    # 训练派发一道只在评测题包里的题（TID2）→ 绑定时按训练 manifest 核对，拒绝；评测 attempt 同理反向
    groups = _dispatch_groups(eval_fx, n=1)
    train_tid2 = groups[1][0]
    assert train_tid2.label == TID2
    with pytest.raises(AttemptAssignmentError, match="dispatch_not_authoritative"):
        await fn(_gi(args, train_tid2, evaluation=False))
    only_train_registry, only_train_face_for = _registry(_load_face(train_fx), _load_face(train_fx, prompts=False))
    chain2 = _chain(world, registry=only_train_registry, face_for=only_train_face_for)
    args2 = Namespace(rh2_orchestrator=chain2.orchestrator, rh2_attempt_assignments=only_train_registry)
    with pytest.raises(AttemptAssignmentError, match="dispatch_not_authoritative"):
        await fn(_gi(args2, _eval_samples(eval_fx)[1], evaluation=True))  # 评测题包里没有 TID2
    assert len(registry) == 0 and len(only_train_registry) == 0


async def test_plane_mixups_and_unsupported_trees_fail_closed_before_any_execution(world, tmp_path, monkeypatch):
    world.install_sglang_stub()
    from repoharness2.adapters.miles import generate_fn as gf
    from repoharness2.adapters.miles import identity as idm
    from repoharness2.adapters.miles.group_admission import GROUP_ADMISSION_FILTER_PATH

    fx = prepare_synthetic(tmp_path / "pkg")
    face = _load_face(fx)
    registry, face_for = _registry(face, face)
    chain = _chain(world, registry=registry, face_for=face_for)
    fn = world.Rh2MilesGenerateFn()
    args = Namespace(rh2_orchestrator=chain.orchestrator, rh2_attempt_assignments=registry,
                     n_samples_per_prompt=1, dynamic_sampling_filter_path=GROUP_ADMISSION_FILTER_PATH)

    # 当前树没有宿主盖章标记（stock pin / 旧 fork）→ formal 评测直接拒绝，不信数据集自带的派发事实
    monkeypatch.setattr(gf, "_eval_host_stamp_supported", lambda: False)
    with pytest.raises(idm.MilesIdentityError, match="eval_host_stamp_unsupported"):
        await fn(_gi(args, _eval_samples(fx)[0], evaluation=True))
    monkeypatch.setattr(gf, "_eval_host_stamp_supported", lambda: True)

    # 训练派发带评测派发事实 → 拒绝；独立评测作业收到训练派发 → 拒绝
    ((train_sample,), _) = _dispatch_groups(fx, n=1)
    train_sample.metadata["rh2_eval_dispatch"] = {"eval_point_id": POINT}
    with pytest.raises(idm.MilesIdentityError, match="eval_facts_on_training_sample"):
        await fn(_gi(args, train_sample, evaluation=False))
    ((clean_train,), _) = _dispatch_groups(fx, n=1)
    eval_only_args = Namespace(**{**vars(args), "rh2_eval_only": True})
    with pytest.raises(idm.MilesIdentityError, match="training_dispatch_in_eval_only_mode"):
        await fn(_gi(eval_only_args, clean_train, evaluation=False))
    assert chain.orchestrator.audits == [] and len(registry) == 0  # 全部在进入编排之前拒绝


@pytest.mark.parametrize(
    ("train_top_p", "unsafe", "status", "reward", "result_class"),
    [
        (1.0, True, "ABORTED", None, "reward_unavailable"),
        (0.95, True, "ABORTED", None, "reward_unavailable"),   # 修复前：CanonicalizationError(sampling_mask_required) → 停训练驱动
        (0.95, False, "COMPLETED", 1.0, "graded"),
    ],
)
async def test_eval_result_never_trips_the_training_sampling_mask_requirement(
    world, host_stamp, tmp_path, monkeypatch, train_top_p, unsafe, status, reward, result_class
):
    """Codex I21 实施复核 IR1：训练 top_p=0.95、评测 top_p=1.0（评测不采集 top-p 支持集），模型产出 unsafe artifact
    （FIFO）。它按既有规则不评分，应交付一条"评不了分"的评测结果；结果载体是输入样本（不进训练），不向它要训练用
    sampling mask。"""

    import repoharness2.adapters.slime.patch_exporter as exporter
    from repoharness2.adapters.slime.eval_result import EVAL_RESULT_METADATA_KEY
    from repoharness2.governance.admission import ADMISSION_METADATA_KEY

    fx = prepare_synthetic(tmp_path / "eval")
    registry, face_for = _registry(None, _load_face(fx))
    sample = _eval_samples(fx)[1]
    # vendor 叶的 index / group_index 由真实 to_sample 从输入样本复制（不是夹具里固定的 0）
    chain = _chain(world, registry=registry, face_for=face_for,
                   leaf_factory=lambda: [_mk_leaf(world, index=sample.index, group_index=sample.group_index)])
    if unsafe:
        async def _unsupported(*a, **k):
            raise exporter.PatchExportError("unsupported_object_in_patch", "fifo in scoreable tree", object_path="src/pipe", object_type="fifo")

        monkeypatch.setattr(exporter, "export_frozen_patch", _unsupported)
    args = Namespace(rh2_orchestrator=chain.orchestrator, rh2_attempt_assignments=registry,
                     rollout_top_p=train_top_p, rh2_engine_sampling_mask=True)  # 训练配置；评测请求自己的 top_p=1.0
    assert SAMPLING_PARAMS["top_p"] == 1.0

    (delivered,) = (await world.Rh2MilesGenerateFn()(_gi(args, sample, evaluation=True))).samples

    assert delivered is sample  # 结果载体 = 输入样本（miles 直通分支），不是 vendor 叶
    assert delivered.status is getattr(world.MS.Status, status) and delivered.reward == reward
    payload = delivered.metadata[EVAL_RESULT_METADATA_KEY]
    assert payload["result_class"] == result_class and ADMISSION_METADATA_KEY not in delivered.metadata
    if unsafe:
        assert payload["unavailable_reason"] == "unsafe_artifact" and "src/pipe" in payload["unavailable_detail"]
        assert chain.grading_calls == [] and delivered.tokens == [0, 0] and delivered.loss_mask == [0]  # 占位形状，没有可训练 token
        assert "rh2_termination_facts" in delivered.metadata  # 终止事实照常盖在载体上
    assert len(registry) == 0


async def test_training_dispatch_still_requires_the_sampling_mask_when_top_p_is_below_one(world, host_stamp, tmp_path):
    """IR1 的修复不放松训练面：训练派发、`rollout_top_p<1`、vendor 叶没有装配 mask → 仍然 fail-closed。"""

    from repoharness2.adapters.miles.canonicalize import CanonicalizationError
    from repoharness2.adapters.miles.group_admission import GROUP_ADMISSION_FILTER_PATH

    fx = prepare_synthetic(tmp_path / "pkg")
    face = _load_face(fx)
    registry, face_for = _registry(face, face)
    ((train_sample,), _) = _dispatch_groups(fx, n=1)
    chain = _chain(world, registry=registry, face_for=face_for,
                   leaf_factory=lambda: [_mk_leaf(world, index=train_sample.index, group_index=train_sample.group_index)])
    args = Namespace(rh2_orchestrator=chain.orchestrator, rh2_attempt_assignments=registry, n_samples_per_prompt=1,
                     dynamic_sampling_filter_path=GROUP_ADMISSION_FILTER_PATH, rollout_top_p=0.95, rh2_engine_sampling_mask=True)
    with pytest.raises(CanonicalizationError, match="sampling_mask_required"):
        await world.Rh2MilesGenerateFn()(_gi(args, train_sample, evaluation=False))
    assert len(registry) == 0


def test_host_stamp_capability_probe_reads_the_loaded_host_module(world, monkeypatch):
    """生产路径里 eval 样本由 `inference_rollout_eval` 产生，该模块必然已加载；探测只读它的标记。CPU 测试环境
    导入不了它的重依赖，这里装一个替身模块，标记取自被测树的真实源码（integration base = True，stock pin = 无）。"""

    import re
    import sys
    import types

    from repoharness2.adapters.miles import generate_fn as gf

    name = "miles.rollout.inference_rollout.inference_rollout_eval"
    monkeypatch.delitem(sys.modules, name, raising=False)
    assert gf._eval_host_stamp_supported() is False  # 宿主模块未加载 = 无从确认，拒绝
    source = (world.miles_root / "miles" / "rollout" / "inference_rollout" / "inference_rollout_eval.py").read_text(encoding="utf-8")
    real_marker = re.search(r"^RH2_EVAL_DISPATCH_HOST_STAMP\s*=\s*True\s*$", source, flags=re.MULTILINE) is not None
    stub = types.ModuleType(name)
    if real_marker:
        stub.RH2_EVAL_DISPATCH_HOST_STAMP = True
    monkeypatch.setitem(sys.modules, name, stub)
    assert gf._eval_host_stamp_supported() is real_marker


async def test_missing_eval_result_payload_is_a_wiring_contradiction(world, host_stamp, tmp_path, monkeypatch):
    """编排出口没盖章（例如有人把出口分支删了）→ 交付面自检拒绝，而不是把没有结果事实的样本交给聚合。"""

    import repoharness2.adapters.slime.eval_result as er
    from repoharness2.adapters.slime.eval_result import EvalResultError

    fx = prepare_synthetic(tmp_path / "eval")
    registry, face_for = _registry(None, _load_face(fx))
    chain = _chain(world, registry=registry, face_for=face_for)
    monkeypatch.setattr(er, "derive_eval_attempt_result", lambda audit, **kw: None)
    args = Namespace(rh2_orchestrator=chain.orchestrator, rh2_attempt_assignments=registry)
    with pytest.raises(EvalResultError, match="eval_result_missing"):
        await world.Rh2MilesGenerateFn()(_gi(args, _eval_samples(fx)[0], evaluation=True))
    assert len(registry) == 0
