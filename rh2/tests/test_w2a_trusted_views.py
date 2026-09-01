"""W2a trusted controller + training-only typed view 测试。

覆盖（06 计划 §3 W2a 行验收项）：
- 正向消费链：合成夹具 IngestResult → controller → 两侧视图 + digest 贯穿；
- 泄漏边界正反例：private/golden 内容绝不进 rollout（模型侧）视图，
  ValidationOnlyBundle 从 controller 对象图不可达；
- fail-closed 三例：unknown task / 漏包 / digest mismatch；
- 真实 216 题资产的 from_repo_root 集成。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from repoharness2.envpack.bundles import (
    PRIVATE_ONLY_FIELD_NAMES,
    PublicTaskBundle,
    sha256_of_text,
)
from repoharness2.envpack.bundles_v2 import GOLDEN_FIELD_NAMES, ValidationOnlyBundle
from repoharness2.envpack.ingest_swegym_lite import IngestResult, build_task
from repoharness2.envpack.training_view import (
    HostGradingView,
    RolloutTaskView,
    TrustedTaskController,
    TrustedViewError,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
IMG_DIG = "sha256:" + "b" * 64
D = "sha256:" + "a" * 64


# ---------------------------------------------------------------------------
# 合成夹具（与 tests/envpack/test_ingest_swegym_lite.py 同形）
# ---------------------------------------------------------------------------

def make_row(iid: str = "getmoto__moto-1", statement: str = "Resolve the moto bug.") -> dict:
    return {
        "instance_id": iid,
        "repo": "getmoto/moto",
        "base_commit": "0" * 40,
        "version": "4.1",
        "created_at": "2023-01-01T00:00:00Z",
        "problem_statement": statement,
        "hints_text": "maintainer said: apply this diff ...",
        "patch": f"diff --git a/m.py b/m.py\n-bug\n+goldfix({iid})\n",
        "test_patch": f"diff --git a/t.py b/t.py\n+judge({iid})\n",
        "FAIL_TO_PASS": [f"t.py::judge_{iid[-1]}"],
        "PASS_TO_PASS": ["t.py::test_ok"],
    }


def make_image_entry(iid: str) -> dict:
    return {
        "instance_id": iid,
        "source_image_ref": f"xingyaoww/sweb.eval.x86_64.{iid.replace('__', '_s_').lower()}:latest",
        "resolved_manifest_digest": IMG_DIG,
    }


def make_result(iids: tuple[str, ...] = ("getmoto__moto-1", "getmoto__moto-2")) -> IngestResult:
    result = IngestResult()
    for iid in iids:
        row = make_row(iid=iid, statement=f"Resolve the moto bug ({iid}).")
        public, grading, validation, package = build_task(
            row, make_image_entry(iid),
            raw_archive_sha256=D, image_manifest_keyed_sha256=D,
        )
        result.public_bundles.append(public)
        result.grading_bundles.append(grading)
        result.validation_bundles.append(validation)
        result.packages.append(package)
    return result


@pytest.fixture()
def controller() -> TrustedTaskController:
    return TrustedTaskController.build_for_tests_from_ingest_result(make_result())


TID = "swe_gym_lite::getmoto__moto-1"
GOLDEN_CONTENT = "goldfix(getmoto__moto-1)"       # 只存在于 golden patch
TEST_PATCH_CONTENT = "judge(getmoto__moto-1)"     # 只存在于 test_patch / F2P


# ---------------------------------------------------------------------------
# 正向消费链 + digest 贯穿
# ---------------------------------------------------------------------------

def test_rollout_view_shape_and_digest_threading(controller):
    assert controller.task_ids() == ("swe_gym_lite::getmoto__moto-1",
                                     "swe_gym_lite::getmoto__moto-2")
    view = controller.rollout_view(TID)
    assert isinstance(view, RolloutTaskView)
    assert view.instance_id == "getmoto__moto-1"
    assert view.public.problem_statement.startswith("Resolve the moto bug")
    # digest 锚 = 对应 EnvironmentPackageV1.digest()（不是 bundle digest 冒充）
    pkg = next(p for p in make_result().packages if p.task_id == TID)
    assert view.environment_package_digest == pkg.digest()
    # grading join 必须交回同一 digest 才放行，且两侧锚一致
    gv = controller.grading_view(TID, environment_package_digest=view.environment_package_digest)
    assert isinstance(gv, HostGradingView)
    assert gv.environment_package_digest == view.environment_package_digest
    # host 侧密封评分面材料齐全（"private 内容进 host grader"的正例半区）
    assert TEST_PATCH_CONTENT in gv.grading.test_patch
    assert gv.grading.eval_cmd
    assert gv.grading.fail_to_pass
    # join 消费方的锚核对口
    controller.verify_environment_package_digest(TID, view.environment_package_digest)


# ---------------------------------------------------------------------------
# 泄漏边界（正反例）
# ---------------------------------------------------------------------------

def test_rollout_view_field_names_disjoint_from_private_and_golden():
    forbidden = PRIVATE_ONLY_FIELD_NAMES | GOLDEN_FIELD_NAMES
    assert not set(RolloutTaskView.model_fields) & forbidden
    assert "grading" not in RolloutTaskView.model_fields
    assert "validation" not in RolloutTaskView.model_fields
    assert not set(HostGradingView.model_fields) & GOLDEN_FIELD_NAMES


def test_private_content_never_in_model_side_dump(controller):
    """"private 内容绝不进模型侧"的反例半区：rollout 视图整树序列化后，
    golden/test_patch/F2P/eval_cmd/version 的**内容**一概不存在。"""
    view = controller.rollout_view(TID)
    dumped = json.dumps(view.model_dump(mode="json"), ensure_ascii=False)
    assert GOLDEN_CONTENT not in dumped
    assert TEST_PATCH_CONTENT not in dumped
    assert "eval_cmd" not in dumped
    assert '"4.1"' not in dumped  # version 归评分侧（bundles.py A6 名单）


def test_rollout_view_leak_scan_rejects_marker_content():
    """泄漏正例（防线真会红）：题面里混入私有 marker → 视图构造即炸。"""
    statement = "please apply the test_patch shown below"
    public = PublicTaskBundle(
        instance_id="getmoto__moto-1",
        repo="getmoto/moto",
        base_commit="0" * 40,
        image="xingyaoww/sweb.eval.x86_64.getmoto_s_moto-1:latest",
        image_manifest_digest=IMG_DIG,
        problem_statement=statement,
        problem_statement_sha256=sha256_of_text(statement),
    )
    with pytest.raises(ValidationError, match="泄漏扫描"):
        RolloutTaskView(
            task_id="swe_gym_lite::getmoto__moto-1",
            source="swe_gym_lite",
            instance_id="getmoto__moto-1",
            environment_package_digest=D,
            public=public,
        )


def test_rollout_view_rejects_smuggled_extra_field(controller):
    """extra=forbid：想给 rollout 视图塞 grading/golden 字段，构造即拒。"""
    view = controller.rollout_view(TID)
    payload = view.model_dump(mode="json")
    for smuggled in ("test_patch", "golden_patch", "grading", "validation"):
        with pytest.raises(ValidationError):
            RolloutTaskView.model_validate({**payload, smuggled: "x"})


def test_host_grading_view_rejects_golden_field(controller):
    gv = controller.grading_view(
        TID,
        environment_package_digest=controller.rollout_view(TID).environment_package_digest,
    )
    payload = gv.model_dump(mode="json")
    with pytest.raises(ValidationError):
        HostGradingView.model_validate({**payload, "golden_patch": "diff --git ..."})


def _walk_object_graph(root):
    """无 gc 依赖的对象图遍历：dict/list/tuple/set/pydantic 模型/带 __dict__ 的对象。"""
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


def test_validation_bundle_unreachable_from_controller(controller):
    """"validation bundle 不可达 rollout 视图"的强化版：从 controller 根出发
    遍历整个对象图——没有任何 ValidationOnlyBundle 实例，也没有任何字符串
    携带 golden patch 内容。"""
    for obj in _walk_object_graph(controller):
        assert not isinstance(obj, ValidationOnlyBundle), "controller 持有了 golden 面对象"
        if isinstance(obj, str):
            assert GOLDEN_CONTENT not in obj, "controller 对象图里出现 golden patch 内容"


def test_test_patch_content_unreachable_from_rollout_views(controller):
    """test_patch 内容只许在 host grading 视图；rollout 视图对象图 0 出现。"""
    for tid in controller.task_ids():
        for obj in _walk_object_graph(controller.rollout_view(tid)):
            if isinstance(obj, str):
                assert "judge(" not in obj


# ---------------------------------------------------------------------------
# fail-closed：unknown task / 漏包 / digest mismatch
# ---------------------------------------------------------------------------

def test_unknown_task_fail_closed(controller):
    with pytest.raises(TrustedViewError, match="unknown task_id"):
        controller.rollout_view("swe_gym_lite::no__such-task")
    with pytest.raises(TrustedViewError, match="unknown task_id"):
        controller.grading_view("swe_gym_lite::no__such-task", environment_package_digest=D)
    with pytest.raises(TrustedViewError, match="unknown task_id"):
        controller.verify_environment_package_digest("swe_gym_lite::no__such-task", D)


def test_missing_face_fail_closed():
    result = make_result()
    result.grading_bundles.pop(0)  # 漏 grading 面一包
    with pytest.raises(TrustedViewError, match="漏包"):
        TrustedTaskController.build_for_tests_from_ingest_result(result)
    result2 = make_result()
    result2.validation_bundles.pop(1)  # 漏 validation 面同样拒绝（关系检查不可省）
    with pytest.raises(TrustedViewError, match="漏包"):
        TrustedTaskController.build_for_tests_from_ingest_result(result2)


def test_package_digest_mismatch_fail_closed():
    """包记录被篡改（grading digest 指向别的内容）→ 构建期四面关系检查拒绝。"""
    result = make_result()
    tampered = result.packages[0].model_copy(
        update={"grading_bundle_digest": "sha256:" + "e" * 64})
    result.packages[0] = tampered
    with pytest.raises(TrustedViewError, match="四面关系检查失败"):
        TrustedTaskController.build_for_tests_from_ingest_result(result)


def test_identity_mismatch_fail_closed():
    """public 面身份被换（repo 漂移）→ 同样在构建期 fail-closed。"""
    result = make_result()
    bad_public = result.public_bundles[0].model_copy(update={"repo": "other/repo"})
    result.public_bundles[0] = bad_public
    with pytest.raises(TrustedViewError, match="四面关系检查失败"):
        TrustedTaskController.build_for_tests_from_ingest_result(result)


def test_grading_join_digest_mismatch_fail_closed(controller):
    with pytest.raises(TrustedViewError, match="digest 不符"):
        controller.grading_view(TID, environment_package_digest="sha256:" + "f" * 64)
    with pytest.raises(TrustedViewError, match="digest 不符"):
        controller.verify_environment_package_digest(TID, "sha256:" + "f" * 64)


# ---------------------------------------------------------------------------
# 真实 216 题资产集成（正式入口 from_repo_root）
# ---------------------------------------------------------------------------

def test_from_repo_root_real_assets_end_to_end():
    controller = TrustedTaskController.from_repo_root(REPO_ROOT)
    tids = controller.task_ids()
    assert len(tids) == 216
    view = controller.rollout_view(tids[0])
    # 真题的 rollout 视图同样零 marker（validator 已内建，此处走一次消费面）
    gv = controller.grading_view(tids[0],
                                 environment_package_digest=view.environment_package_digest)
    assert gv.grading.test_patch
    with pytest.raises(TrustedViewError, match="digest 不符"):
        controller.grading_view(tids[0], environment_package_digest="sha256:" + "9" * 64)


# ---------------------------------------------------------------------------
# Wave1 复核 F3/F4：构造后污染与 Controller 配对旁路（对抗性反例）
# ---------------------------------------------------------------------------


def test_f4_direct_constructor_cross_key_rejected(controller):
    """F4 codex 复现：map key 是任务 A、value 是任务 B —— 直接构造也必须拒绝。"""

    tids = controller.task_ids()
    a, b = tids[0], tids[1]
    rv_b = controller.rollout_view(b)
    gv_b = controller.grading_view(b, environment_package_digest=rv_b.environment_package_digest)
    with pytest.raises(TrustedViewError, match="task_id"):
        TrustedTaskController(rollout_views={a: rv_b}, grading_views={a: gv_b})


def test_f4_key_set_mismatch_rejected(controller):
    tids = controller.task_ids()
    a, b = tids[0], tids[1]
    rv_a = controller.rollout_view(a)
    gv_b = controller.grading_view(
        b, environment_package_digest=controller.rollout_view(b).environment_package_digest
    )
    with pytest.raises(TrustedViewError, match="集合不一致"):
        TrustedTaskController(rollout_views={a: rv_a}, grading_views={b: gv_b})


def test_f4_cross_pairing_identity_mismatch_rejected(controller):
    """两侧 key 都对但把 A 的 rollout 视图和 B 的 grading 视图硬配对——身份/
    digest 逐任务比对必须拒绝（key 单独一致不足以证明配对正确）。"""

    tids = controller.task_ids()
    a, b = tids[0], tids[1]
    rv_a, rv_b = controller.rollout_view(a), controller.rollout_view(b)
    gv_a = controller.grading_view(a, environment_package_digest=rv_a.environment_package_digest)
    gv_b = controller.grading_view(b, environment_package_digest=rv_b.environment_package_digest)
    forged_gv = gv_b.model_copy(update={"task_id": a, "instance_id": gv_a.instance_id})
    with pytest.raises(TrustedViewError):
        TrustedTaskController(rollout_views={a: rv_a, b: rv_b},
                              grading_views={a: forged_gv, b: gv_b})


def test_f3_consumer_mutation_is_isolated(controller):
    """F3：取数口返回深拷贝隔离副本——一个消费者篡改嵌套 list 不污染
    controller 权威份与后续消费者。"""

    dirty = controller.rollout_view(TID)
    dirty.public.allowed_tools.append("golden_patch")  # codex 复现载荷
    fresh = controller.rollout_view(TID)
    assert "golden_patch" not in fresh.public.allowed_tools
    dirty_gv = controller.grading_view(TID, environment_package_digest=fresh.environment_package_digest)
    dirty_gv.grading.fail_to_pass.append("forged::test")
    fresh_gv = controller.grading_view(TID, environment_package_digest=fresh.environment_package_digest)
    assert "forged::test" not in fresh_gv.grading.fail_to_pass


def test_f3_dirty_rollout_copy_fails_revalidation(controller):
    """F3：被污染的副本在消费时刻 revalidated() 被泄漏扫描拒绝；干净副本
    round-trip 等值通过。"""

    clean = controller.rollout_view(TID)
    assert clean.revalidated() == clean
    dirty = controller.rollout_view(TID)
    dirty.public.allowed_tools.append("golden_patch")
    with pytest.raises(ValueError, match="泄漏扫描|golden"):
        dirty.revalidated()


def test_f3_dirty_grading_copy_fails_revalidation(controller):
    epd = controller.rollout_view(TID).environment_package_digest
    clean = controller.grading_view(TID, environment_package_digest=epd)
    assert clean.revalidated() == clean
    dirty = controller.grading_view(TID, environment_package_digest=epd)
    dirty.grading.fail_to_pass.append("forged::test")
    with pytest.raises(ValueError, match="digest 不符"):
        dirty.revalidated()
