"""constants.py 的单测：A6 名单齐全 + 归一化/紧凑匹配语义 + 树扫描。"""

from contract_samples import valid_trajectory_projection

from repoharness2.contracts import (
    FORBIDDEN_PUBLIC_MARKERS,
    find_forbidden_marker,
    scan_for_forbidden_markers,
)

A6_REQUIRED_MARKERS = {
    "golden_patch",
    "test_patch",
    "fail_to_pass",
    "pass_to_pass",
    "hidden_verifier",
    "grader_only",
}


def test_a6_markers_all_present():
    assert A6_REQUIRED_MARKERS <= FORBIDDEN_PUBLIC_MARKERS


def test_legacy_l4_markers_inherited():
    for marker in ("gold_patch", "provider_secret", "hidden_test_patch", "run_dir"):
        assert marker in FORBIDDEN_PUBLIC_MARKERS


def test_normalization_variants_caught():
    # 大写 + 下划线原文
    assert find_forbidden_marker("FAIL_TO_PASS") == "fail_to_pass"
    # 连字符变体
    assert find_forbidden_marker("golden-patch") == "golden_patch"
    # 空格变体
    assert find_forbidden_marker("Pass To Pass results") == "pass_to_pass"
    # camelCase（紧凑匹配）
    assert find_forbidden_marker("swe TestPatch path") == "test_patch"
    # 嵌进长 key
    assert find_forbidden_marker("bundle_hidden_verifier_config") == "hidden_verifier"


def test_clean_text_passes():
    assert find_forbidden_marker("django__django-11099 problem statement") is None
    assert find_forbidden_marker("prompt_token_count") is None


def test_scan_walks_nested_keys_and_values():
    tree = {
        "meta": {"FAIL_TO_PASS": ["test_a"]},  # 命中 key
        "notes": ["see golden_patch for answer"],  # 命中 list 内 value
        "count": 3,  # 非字符串标量不检查
    }
    hits = scan_for_forbidden_markers(tree)
    assert {(hit.marker, hit.kind) for hit in hits} == {
        ("fail_to_pass", "key"),
        ("golden_patch", "value"),
    }
    paths = {hit.path for hit in hits}
    assert "$.meta.FAIL_TO_PASS" in paths
    assert "$.notes[0]" in paths


def test_valid_projection_sample_is_marker_clean():
    """合法投影样例本身必须干净——public 侧契约对象不允许天然携带 marker。"""

    assert scan_for_forbidden_markers(valid_trajectory_projection()) == []


def test_compact_matching_is_fail_closed_by_design():
    """紧凑匹配的已知误报形态（fail-closed 取舍的回归锚点）：
    "latest_patches" 去下划线后包含 "testpatch"，按设计应命中而非放行。"""

    assert find_forbidden_marker("latest_patches") == "test_patch"


def test_multi_marker_hit_is_deterministic():
    """S1-1b：命中多个 marker 的文本（此例同时含 hidden_test / hidden_test_patch /
    test_patch 三个）按字典序返回第一个——跨进程（不同 PYTHONHASHSEED 下
    frozenset 迭代序不同）结果一致，evidence 才能逐字节复现比对。"""

    assert find_forbidden_marker("swe_hidden_test_patch_path") == "hidden_test"
