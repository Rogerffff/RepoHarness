"""bundle v2 三分体系契约测试（S2-1 T2-b）。

覆盖执行计划 §3.0 的关键不变量：golden 面与 grading 面静态互斥、
大小写投影钉死、digest 自证与包记录联动、身份一致性断言。
"""

from __future__ import annotations

import hashlib

import pytest
from pydantic import ValidationError

from repoharness2.envpack.bundles import PublicTaskBundle
from repoharness2.envpack.bundles_v2 import (
    GOLDEN_FIELD_NAMES,
    EnvironmentPackageV1,
    PrivateGradingBundleV2,
    ValidationOnlyBundle,
    build_environment_package,
    task_id_for,
)

DIG = "sha256:" + "a" * 64
IMG_DIG = "sha256:" + "b" * 64
SHA = "0" * 40


def _sha(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def make_public(iid: str = "getmoto__moto-1") -> PublicTaskBundle:
    stmt = "Fix the bug in moto."
    return PublicTaskBundle(
        instance_id=iid,
        repo="getmoto/moto",
        base_commit=SHA,
        image="xingyaoww/sweb.eval.x86_64.getmoto_s_moto-1:latest",
        image_manifest_digest=IMG_DIG,
        problem_statement=stmt,
        problem_statement_sha256=_sha(stmt),
    )


def make_grading(iid: str = "getmoto__moto-1", repo: str = "getmoto/moto") -> PrivateGradingBundleV2:
    return PrivateGradingBundleV2(
        instance_id=iid,
        repo=repo,
        repo_key_lower=repo.lower(),
        version="4.1",
        base_commit=SHA,
        test_patch="diff --git a/tests/x.py b/tests/x.py\n+assert True\n",
        fail_to_pass=["tests/x.py::test_a"],
        pass_to_pass=["tests/x.py::test_b"],
        eval_cmd="pytest -n0 -rA",
        python_version="3.12",  # 必须等于 vendor 派生值（轮次 15 起消费期互检）
        spec_vendor_id="swegym_constants_242429c1",
    )


def make_validation(iid: str = "getmoto__moto-1") -> ValidationOnlyBundle:
    patch = "diff --git a/moto/core.py b/moto/core.py\n-bug\n+fix\n"
    return ValidationOnlyBundle(
        instance_id=iid, golden_patch=patch, golden_patch_sha256=_sha(patch)
    )


# ---- golden 面与 grading 面静态互斥（防线：字段名交集为空） -------------------

def test_grading_v2_has_no_golden_fields():
    assert not set(PrivateGradingBundleV2.model_fields) & GOLDEN_FIELD_NAMES


def test_package_has_no_golden_or_content_fields():
    assert not set(EnvironmentPackageV1.model_fields) & GOLDEN_FIELD_NAMES
    # 包记录零内容字段：不携带题面/补丁/测试文本
    for banned in ("problem_statement", "test_patch", "eval_cmd"):
        assert banned not in EnvironmentPackageV1.model_fields


def test_grading_v2_rejects_extra_golden_field():
    with pytest.raises(ValidationError):
        PrivateGradingBundleV2(**{**make_grading().model_dump(), "golden_patch": "x"})


# ---- 大小写投影与自证 digest --------------------------------------------------

def test_repo_case_projection_pinned():
    g = make_grading(repo="Project-MONAI/MONAI")
    assert g.repo_key_lower == "project-monai/monai"
    with pytest.raises(ValidationError, match="小写投影"):
        PrivateGradingBundleV2(**{**make_grading().model_dump(), "repo_key_lower": "WRONG/case"})


def test_validation_bundle_patch_digest_selfcheck():
    with pytest.raises(ValidationError, match="不符"):
        ValidationOnlyBundle(
            instance_id="getmoto__moto-1",
            golden_patch="real patch",
            golden_patch_sha256=_sha("tampered"),
        )


# ---- 包记录：digest 联动与身份一致性 ------------------------------------------

def _build_pkg():
    return build_environment_package(
        public=make_public(),
        grading=make_grading(),
        validation=make_validation(),
        raw_archive_sha256=DIG,
        image_manifest_keyed_sha256=DIG,
    )


def test_package_digests_recomputed_from_bundles():
    pkg = _build_pkg()
    assert pkg.public_bundle_digest == make_public().digest()
    assert pkg.grading_bundle_digest == make_grading().digest()
    assert pkg.validation_bundle_digest == make_validation().digest()
    assert pkg.task_id == task_id_for("swe_gym_lite", "getmoto__moto-1")
    from repoharness2.envpack.spec_vendor import vendor_pin
    assert pkg.spec_vendor_json_sha256 == "sha256:" + vendor_pin("swegym_constants_242429c1").json_sha256


def test_package_rejects_mismatched_instance_ids():
    with pytest.raises(ValueError, match="instance_id 不一致"):
        build_environment_package(
            public=make_public(),
            grading=make_grading(iid="getmoto__moto-2"),
            validation=make_validation(),
            raw_archive_sha256=DIG,
            image_manifest_keyed_sha256=DIG,
        )


def test_package_task_id_validator():
    pkg = _build_pkg()
    with pytest.raises(ValidationError, match="不一致"):
        EnvironmentPackageV1(**{**pkg.model_dump(), "task_id": "swe_gym_lite::other"})


def test_environment_identity_documented_pairs_coexist():
    # 环境身份（repo+base_commit）相同、任务不同 —— 两包合法共存且 digest 不同
    p1 = _build_pkg()
    pub2 = make_public(iid="getmoto__moto-2")
    g2 = make_grading(iid="getmoto__moto-2")
    v2 = make_validation(iid="getmoto__moto-2")
    p2 = build_environment_package(
        public=pub2, grading=g2, validation=v2,
        raw_archive_sha256=DIG, image_manifest_keyed_sha256=DIG,
    )
    assert (p1.repo, p1.base_commit) == (p2.repo, p2.base_commit)
    assert p1.task_id != p2.task_id and p1.digest() != p2.digest()


# ---- 轮次 12 严重 1：public↔grading 任务身份交叉核对 --------------------------

def test_package_rejects_repo_mismatch():
    pub = make_public()
    g = make_grading(repo="evil/other")
    with pytest.raises(ValueError, match="repo.*不一致"):
        build_environment_package(
            public=pub, grading=g, validation=make_validation(),
            raw_archive_sha256=DIG, image_manifest_keyed_sha256=DIG,
        )


def test_package_rejects_base_commit_mismatch():
    pub = make_public()
    g = make_grading()
    g = PrivateGradingBundleV2(**{**g.model_dump(), "base_commit": "1" * 40})
    with pytest.raises(ValueError, match="base_commit.*不一致"):
        build_environment_package(
            public=pub, grading=g, validation=make_validation(),
            raw_archive_sha256=DIG, image_manifest_keyed_sha256=DIG,
        )


# ---- 轮次 12 严重 2：vendor 路径注入封死 + eval_cmd 互检 ----------------------

def test_spec_vendor_id_rejects_arbitrary_path():
    with pytest.raises(ValidationError):
        PrivateGradingBundleV2(**{**make_grading().model_dump(),
                                  "spec_vendor_id": "/tmp/attacker.py"})


def test_eval_cmd_cross_check_against_registry():
    from repoharness2.envpack.spec_vendor import VendorSpecError, verify_grading_eval_cmd
    good = make_grading()  # getmoto/moto 4.1 的真实 test_cmd = pytest -n0 -rA
    verify_grading_eval_cmd(good)  # 不抛 = 互检通过
    bad = PrivateGradingBundleV2(**{**good.model_dump(), "eval_cmd": "rm -rf / #"})
    with pytest.raises(VendorSpecError, match="不作权威"):
        verify_grading_eval_cmd(bad)


# ---- 轮次 13 严重 1：恶意 eval_cmd 不能进入正式包（builder 强制互检） ---------

def test_malicious_eval_cmd_cannot_package():
    from repoharness2.envpack.spec_vendor import VendorSpecError
    bad = PrivateGradingBundleV2(**{**make_grading().model_dump(), "eval_cmd": "rm -rf / #"})
    with pytest.raises(VendorSpecError, match="不作权威"):
        build_environment_package(
            public=make_public(), grading=bad, validation=make_validation(),
            raw_archive_sha256=DIG, image_manifest_keyed_sha256=DIG,
        )


def test_build_private_grading_bundle_derives_from_registry():
    from repoharness2.envpack.bundles_v2 import build_private_grading_bundle
    from repoharness2.envpack.spec_vendor import VendorSpecError
    g = build_private_grading_bundle(
        instance_id="getmoto__moto-1", repo="getmoto/moto", version="4.1",
        base_commit=SHA, test_patch="diff --git a/t b/t\n+x\n",
        fail_to_pass=["t::a"], pass_to_pass=[],
    )
    assert g.eval_cmd == "pytest -n0 -rA"      # 注册表派生，非调用方填写
    assert g.python_version is not None
    with pytest.raises(VendorSpecError, match="无 .* 的 spec"):
        build_private_grading_bundle(
            instance_id="getmoto__moto-1", repo="getmoto/moto", version="99.99",
            base_commit=SHA, test_patch="d", fail_to_pass=["t::a"], pass_to_pass=[],
        )
