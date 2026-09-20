"""S1-b（评分接线 2026-09-15）：vendored SWE-Gym parser 的行为回归 + v2 入口的判定小样例。

两层语料：

1. 入库子集 `rh2/tests/envpack/data/swegym_parser_dumps/`（每仓库最小 2 份阶段一日志 + fork parser 产出的
   status_map.json）——无外部依赖，CI 恒跑；
2. 环境变量 `RH2_SWEGYM_PARSER_CORPUS` 指向本机 `runs/env_probe_stage1_20260910/ledger`（441 份）时全量跑。

status_map.json 是当时用 fork 的 `get_logs_eval` 包装（坏码 / "applied patch" 检查 → 取 `Applied Patch (pred)`
之后全部内容 → parser）得到的，所以这里用同一包装喂移植后的 parser——检验的是 parser 函数等价，不是 v2 标记入口。
v2 入口另用合成小样例钉判定语义（B 线 B2、A 线 R5）。
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

from repoharness2.envpack import scoring
from repoharness2.envpack.bundles_v2 import PrivateGradingBundleV2
from repoharness2.envpack.spec_vendor import SPEC_VENDOR_ID_SWEGYM_242429C1, derive_eval_cmd
from repoharness2.envpack.swegym_parsers import (
    MAP_REPO_TO_PARSER_SWEGYM,
    SWEGYM_PARSERS_SOURCE_COMMIT,
    SWEGYM_PARSERS_SOURCE_SHA256,
    TEST_STATUS_VALUES,
    SwegymParserError,
    lookup_parser,
    parse_log_pytest,
    parse_log_pytest_pydantic,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DOCS = REPO_ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams"
CURATED = Path(__file__).resolve().parent / "data" / "swegym_parser_dumps"  # A1：随 rh2 测试树走
VENDORED_SOURCE = DOCS / "s2/vendor/swegym_log_parsers_242429c1.py"

_IID_RE = re.compile(r"^[A-Za-z0-9_.-]+__[A-Za-z0-9_.-]+-\d+$")
START = ">>>>> Start Test Output"
END = ">>>>> End Test Output"
APPLIED = ">>>>> Applied Patch"


def _fork_wrapper(content: str, parser) -> dict[str, str]:
    """fork grading.get_logs_eval 的包装语义（阶段一 status_map.json 的产生方式）。"""
    markers = [">>>>> Patch Apply Failed", ">>>>> Reset Failed", ">>>>> Tests Errored", ">>>>> Tests Timed Out",
               "Failed to reset task environment"]
    if any(m in content for m in markers) or "applied patch" not in content.lower():
        return {}
    return parser(content.split(f"{APPLIED} (pred)")[-1])


def _repo_of(instance_dir: str) -> str:
    return "-".join(instance_dir.replace("__", "/").split("-")[:-1]).lower()


def _corpus_pairs(root: Path):
    for sm in sorted(root.rglob("status_map.json")):
        if "logs_r2e" in sm.parts:
            continue
        log = sm.with_name("test_output.txt")
        if not log.exists():
            continue
        iid_dirs = [p for p in sm.parts if _IID_RE.match(p)]
        if not iid_dirs:
            # 入库子集目录名形如 <iid>__<gate>__<variant>__<attempt>
            name = sm.parent.name
            iid_dirs = [name.split("__gold__")[0].split("__empty__")[0]]
        yield iid_dirs[-1], log, sm


def _run_corpus(root: Path) -> tuple[int, list[str]]:
    n, mismatches = 0, []
    for iid, log, sm in _corpus_pairs(root):
        parser = lookup_parser(_repo_of(iid))
        expected = json.loads(sm.read_text())
        got = _fork_wrapper(log.read_text(errors="replace"), parser)
        n += 1
        if got != expected:
            diff = {k: (expected.get(k), got.get(k)) for k in set(expected) | set(got) if expected.get(k) != got.get(k)}
            mismatches.append(f"{sm}: {len(diff)} 项不同，例如 {list(diff.items())[:2]}")
    return n, mismatches


def test_source_pin_matches_vendored_file():
    import hashlib

    assert hashlib.sha256(VENDORED_SOURCE.read_bytes()).hexdigest() == SWEGYM_PARSERS_SOURCE_SHA256
    assert SWEGYM_PARSERS_SOURCE_COMMIT == "242429c188fcfd06aad13fce9a54d450470bf0ac"
    text = VENDORED_SOURCE.read_text()
    for repo in MAP_REPO_TO_PARSER_SWEGYM:
        # 映射键都来自 fork 新增块（大小写不敏感比对）
        assert repo in text.lower(), repo


def test_status_values_match_installed_swebench():
    constants = pytest.importorskip("swebench.harness.constants")
    assert tuple(t.value for t in constants.TestStatus) == TEST_STATUS_VALUES


def test_curated_corpus_reproduces_fork_status_maps():
    n, mismatches = _run_corpus(CURATED)
    assert n >= 18, f"入库子集应有 ≥ 18 份，实际 {n}"
    assert mismatches == [], "\n".join(mismatches)


def test_full_local_corpus_if_available():
    root = os.environ.get("RH2_SWEGYM_PARSER_CORPUS")
    if not root:
        pytest.skip("未设置 RH2_SWEGYM_PARSER_CORPUS（本机 441 份语料）")
    n, mismatches = _run_corpus(Path(root))
    assert n >= 400, f"语料只找到 {n} 份"
    assert mismatches == [], "\n".join(mismatches)


def test_pydantic_parser_strips_ansi_and_control_chars_and_tolerates_bare_status():
    log = (
        "\x1b[32mPASSED\x1b[0m tests/test_main.py::test_ok\n"
        "FAILED [ 12%] tests/test_main.py::test_bad - AssertionError\n"
        "PASSED\n"  # 上游对此行 IndexError；移植跳过
        "tests/test_old.py::test_legacy PASSED\n"
    )
    assert parse_log_pytest_pydantic(log) == {
        "tests/test_main.py::test_ok": "PASSED",
        "tests/test_main.py::test_bad": "FAILED",
        "tests/test_old.py::test_legacy": "PASSED",
    }
    assert parse_log_pytest("PASSED\nFAILED a::b - x\n") == {"a::b": "FAILED"}


def test_lookup_rejects_unknown_or_uppercase():
    with pytest.raises(SwegymParserError):
        lookup_parser("django/django")
    with pytest.raises(SwegymParserError):
        lookup_parser("Project-MONAI/MONAI")
    assert lookup_parser("project-monai/monai") is parse_log_pytest
    assert lookup_parser("pydantic/pydantic") is parse_log_pytest_pydantic


# ---- v2 入口判定小样例 ---------------------------------------------------------

def _bundle(repo="getmoto/moto", version="5.0", f2p=("tests/t.py::f",), p2p=("tests/t.py::p",)):
    return PrivateGradingBundleV2(
        instance_id="getmoto__moto-0001" if repo == "getmoto/moto" else "pydantic__pydantic-0001",
        repo=repo,
        repo_key_lower=repo.lower(),
        version=version,
        base_commit="a" * 40,
        test_patch="diff --git a/tests/t.py b/tests/t.py\n--- a/tests/t.py\n+++ b/tests/t.py\n+x\n",
        fail_to_pass=list(f2p),
        pass_to_pass=list(p2p),
        eval_cmd=derive_eval_cmd(SPEC_VENDOR_ID_SWEGYM_242429C1, repo.lower(), version),
        python_version=None if repo == "getmoto/moto" else "3.11",
        spec_vendor_id=SPEC_VENDOR_ID_SWEGYM_242429C1,
    )


def _log(inside: str, before: str = "", after: str = "") -> str:
    return f"{before}\n+ : '{START}'\n{inside}\n+ : '{END}'\n{after}\n"


def test_v2_reference_missing_counts_as_failure():
    v = scoring.parse_eval_log_v2(_bundle(), _log("PASSED tests/t.py::p\n"))
    assert v.apply_ok and v.resolution == "RESOLVED_NO" and not v.resolved
    assert v.f2p_failure == ["tests/t.py::f"] and v.reference_missing == ["tests/t.py::f"]
    assert v.parser_source.startswith("swegym_parsers@242429c1")


def test_v2_all_skipped_is_full_but_diagnosed():
    v = scoring.parse_eval_log_v2(_bundle(), _log("SKIPPED tests/t.py::f\nSKIPPED tests/t.py::p\n"))
    assert v.resolution == "RESOLVED_FULL" and v.resolved
    assert v.reference_skipped == ["tests/t.py::f", "tests/t.py::p"]
    assert v.f2p_success == [] and v.f2p_failure == []


def test_v2_zero_parsed_inside_segment_no_fallback_to_outside():
    v = scoring.parse_eval_log_v2(
        _bundle(), _log("==== errors during collection ====\nno tests ran in 0.1s\n", after="PASSED tests/t.py::f\nPASSED tests/t.py::p\n")
    )
    assert v.apply_ok and v.num_parsed_tests == 0  # manager 零解析保护会把它归 infra
    assert v.num_parsed_outside_segment == 2
    assert v.resolution == "RESOLVED_NO"


def test_v2_passed_inside_segment_is_full():
    v = scoring.parse_eval_log_v2(_bundle(), _log("PASSED tests/t.py::f\nPASSED tests/t.py::p\n"))
    assert v.resolved and v.num_parsed_tests == 2 and v.num_parsed_outside_segment == 0
    fields = scoring.grading_outcome_fields(v)
    assert fields["outcome"] == "resolved" and fields["reward"] == 1.0


def test_v2_bad_code_or_missing_markers_means_apply_not_ok():
    v = scoring.parse_eval_log_v2(_bundle(), ">>>>> Patch Apply Failed\n" + _log("PASSED tests/t.py::f\n"))
    assert not v.apply_ok and v.num_parsed_tests == 0
    assert scoring.grading_outcome_fields(v)["failure_category"] == "patch_apply_failed"
    v2 = scoring.parse_eval_log_v2(_bundle(), "PASSED tests/t.py::f\nPASSED tests/t.py::p\n")
    assert not v2.apply_ok


def test_v2_dispatches_pydantic_parser():
    log = _log("\x1b[32mPASSED\x1b[0m tests/t.py::f\nPASSED tests/t.py::p\n")
    v = scoring.parse_eval_log_v2(_bundle(repo="pydantic/pydantic", version="2.04"), log)
    assert v.resolved


def test_v2_rejects_other_vendor():
    b = _bundle()
    class Other:  # 鸭子：spec_vendor_id 不同
        spec_vendor_id = "something_else"
        instance_id = b.instance_id
        repo_key_lower = b.repo_key_lower
        fail_to_pass = b.fail_to_pass
        pass_to_pass = b.pass_to_pass
    with pytest.raises(ValueError):
        scoring.parse_eval_log_v2(Other(), _log("PASSED tests/t.py::f\n"))
