"""bundle 拆分（A6）单测：三道防线逐一验证 + 冻结 8 题真实数据全量过检。"""

import pydantic
import pytest

from repoharness2.contracts import scan_for_forbidden_markers
from repoharness2.envpack.bundles import (
    PRIVATE_ONLY_FIELD_NAMES,
    PUBLIC_SYSTEM_HINTS,
    BundleLeakError,
    BundlePair,
    PrivateGradingBundle,
    PublicTaskBundle,
    load_bundle_pairs,
    load_task_entries,
    render_user_prompt,
    sha256_of_text,
    split_frozen_entry,
)

BASE = "d26b2424437dabeeca94d7900b37d2df4410da0c"
IMG_DIGEST = "sha256:" + "0" * 64


def make_public(**overrides) -> PublicTaskBundle:
    statement = overrides.pop("problem_statement", "UsernameValidator allows trailing newline.")
    fields = dict(
        instance_id="django__django-11099",
        repo="django/django",
        base_commit=BASE,
        image="swebench/sweb.eval.x86_64.django_1776_django-11099:latest",
        image_manifest_digest=IMG_DIGEST,
        problem_statement=statement,
        problem_statement_sha256=sha256_of_text(statement),
    )
    fields.update(overrides)
    return PublicTaskBundle(**fields)


# ---------------------------------------------------------------------------
# 防线 1：schema 白名单（extra="forbid"）
# ---------------------------------------------------------------------------


def test_public_bundle_rejects_private_extra_fields():
    """往 public bundle 塞任何私有字段，构造期就拒绝——走不到扫描那一步。"""
    for private_field in ("test_patch", "fail_to_pass", "golden_patch", "eval_script"):
        with pytest.raises(pydantic.ValidationError):
            make_public(**{private_field: "leak"})


def test_public_field_names_disjoint_from_private_names():
    """防线 2：字段名静态互斥（含 forbidden marker 名单本身）。"""
    public_fields = set(PublicTaskBundle.model_fields)
    assert not public_fields & PRIVATE_ONLY_FIELD_NAMES
    # 字段名树本身也过一遍 marker 扫描（key 命中即视为拆分被破坏）
    assert not scan_for_forbidden_markers({name: "" for name in public_fields})


def test_statement_digest_self_check():
    with pytest.raises(pydantic.ValidationError, match="自证失败"):
        PublicTaskBundle(
            instance_id="x__y-1",
            repo="x/y",
            base_commit=BASE,
            image="img:latest",
            image_manifest_digest=IMG_DIGEST,
            problem_statement="real statement",
            problem_statement_sha256=sha256_of_text("different statement"),
        )


# ---------------------------------------------------------------------------
# 防线 3：内容泄漏扫描（split_frozen_entry 出厂检查）
# ---------------------------------------------------------------------------


def leaky_entry(statement: str) -> dict:
    return {
        "instance": {
            "instance_id": "evil__evil-1",
            "repo": "evil/evil",
            "version": "1.0",
            "base_commit": BASE,
            "patch": "diff --git a/f.py b/f.py",
            "test_patch": "diff --git a/test_f.py b/test_f.py",
            "problem_statement": statement,
            "environment_setup_commit": None,
        },
        "image": "evil:latest",
        "image_manifest_digest": IMG_DIGEST,
        "eval_script": "#!/bin/bash\ntrue",
        "test_cmd": "pytest",
        "fail_to_pass": ["test_a"],
        "pass_to_pass": [],
    }


def test_split_rejects_statement_leaking_private_field_names():
    """私有字段名出现在 public 可见文本里 → BundleLeakError（A6 验收用例）。"""
    for poison in (
        "apply the golden test_patch to reproduce",  # test_patch
        "see FAIL_TO_PASS list below",  # fail_to_pass（归一化命中）
        "the hidden TestPatch works",  # 紧凑匹配抓 camelCase
        "grader_only assets: ...",  # grader_only
    ):
        with pytest.raises(BundleLeakError, match="泄漏扫描命中"):
            split_frozen_entry(leaky_entry(poison))


def test_scan_reports_hit_path():
    with pytest.raises(BundleLeakError, match=r"problem_statement"):
        split_frozen_entry(leaky_entry("答案在 PASS_TO_PASS 清单里"))


# ---------------------------------------------------------------------------
# 冻结 8 题真实数据：拆分、digest、扫描全量过检
# ---------------------------------------------------------------------------


def test_frozen_eight_tasks_split_clean():
    """8 题真实题面 + 公开提示过扫描 0 命中（S1-1 遗留的误报率问题就此关闭）。"""
    pairs = load_bundle_pairs()  # split_frozen_entry 内嵌扫描，能加载完成即 0 命中
    assert len(pairs) == 8
    for pair in pairs:
        assert scan_for_forbidden_markers(pair.public.model_dump(mode="json")) == []


def test_digests_stable_and_distinct():
    pairs = load_bundle_pairs()
    by_id = {pair.instance_id: pair for pair in pairs}
    pair = by_id["django__django-11099"]
    # 同一内容重复计算恒等（规范化 JSON digest）
    assert pair.public.digest() == pair.public.digest()
    reload_pair = load_bundle_pairs(subset=["django__django-11099"])[0]
    assert reload_pair.public.digest() == pair.public.digest()
    assert reload_pair.private.digest() == pair.private.digest()
    # public 与 private、题与题之间 digest 互不相同
    digests = [p.public.digest() for p in pairs] + [p.private.digest() for p in pairs]
    assert len(set(digests)) == 16


def test_private_bundle_carries_grading_material():
    entries = load_task_entries()
    pair = split_frozen_entry(entries["psf__requests-2931"])
    private = pair.private
    assert private.version and private.eval_script.startswith("#!/bin/bash")
    assert private.fail_to_pass and len(private.pass_to_pass) == 84
    assert private.test_patch.startswith("diff --git")
    assert private.golden_patch.startswith("diff --git")
    # public 侧 dump 全文里不得出现 golden patch / eval 脚本内容片段
    public_text = pair.public.model_dump_json()
    assert private.test_patch[:60] not in public_text
    assert private.eval_script[:60] not in public_text


def test_pairing_key_mismatch_rejected():
    entries = load_task_entries()
    a = split_frozen_entry(entries["django__django-11099"])
    b = split_frozen_entry(entries["django__django-11133"])
    with pytest.raises(pydantic.ValidationError, match="配对键不一致"):
        BundlePair(public=a.public, private=b.private)


# ---------------------------------------------------------------------------
# prompt 渲染（薄壳回归锚点：文本形态与 S0-7 逐字一致）
# ---------------------------------------------------------------------------


def test_render_user_prompt_matches_s0_format():
    pair = load_bundle_pairs(subset=["django__django-11099"])[0]
    prompt = render_user_prompt(pair.public)
    assert prompt.startswith(
        "Fix the following issue from the `django/django` repository "
        f"(checked out at /testbed, commit {BASE[:12]}):\n\n"
    )
    assert prompt.endswith(pair.public.problem_statement)
    assert "Do NOT modify test files" in PUBLIC_SYSTEM_HINTS


def test_subset_unknown_instance_rejected():
    with pytest.raises(ValueError, match="不在冻结题单里"):
        load_bundle_pairs(subset=["django__django-99999"])
