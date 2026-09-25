"""R2E 判定规则移植的回归（R2E 接线 R-b，2026-09-20）。

三层证据，由强到弱：

1. **与固定上游函数对拍**：按 AST 从 vendored 原文件（`s2_r2e/vendor/prime_envs_r2e_gym_taskset_c4d04dfe.py`，
   sha256 钉死）取出 `parse_log_pytest / _decolor / calculate_reward / extract_gold_patch` 四个纯函数，与
   `envpack.r2e_parsers` 的移植在真实日志上逐份比较（解析映射、去色、reward）。原文件依赖 `verifiers.v1`，
   所以不 import，只取函数体执行。
2. 入库子集 `tests/envpack/data/r2e_parser_corpus/`（8 份真实日志，覆盖纯 pytest / 期望键带 ANSI / 自定义 unittest
   runner / 期望含 ERROR 键 / xvfb / 两个来源缺陷的 gold=0 / noop）；本机有完整 336 份语料时再跑全量。
3. 计划 §3.2 的五条固定样本 + 标记段纪律 + 与上游 `calculate_reward` 的那一处有意差别。
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path

import pytest

from repoharness2.envpack import r2e_parsers as port
from repoharness2.envpack import scoring
from repoharness2.envpack.bundles_v2 import (
    PrivateGradingBundleR2E,
    R2EHiddenTestFile,
    r2e_hidden_tests_tree_digest,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
VENDORED = REPO_ROOT / port.R2E_RULE_SOURCE_VENDOR_RELPATH
CURATED = Path(__file__).parent / "data" / "r2e_parser_corpus"
# parser 与上游逐函数对拍用**来源版**期望（修订前的产物原件）：这里验证的是"我们的实现 == 上游规则"，
# 与用户 09-24 批准的材料修订无关。修订后的效果另有测试（test_revised_expected_resolves_the_source_defect_logs）。
INGEST_GRADING = REPO_ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/ingest_history/source_v0_20260923/grading_bundles_r2e_v0.jsonl"
INGEST_GRADING_CURRENT = REPO_ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/ingest/grading_bundles_r2e_v0.jsonl"

START, END = scoring.R2E_EVAL_START_MARKER, scoring.R2E_EVAL_END_MARKER


def _sha(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _upstream() -> dict:
    """vendored 原文件里的四个纯函数（AST 取函数体，隔离命名空间执行）。"""

    names = {"parse_log_pytest", "_decolor", "calculate_reward", "extract_gold_patch"}
    tree = ast.parse(VENDORED.read_text(encoding="utf-8"))
    body = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert {n.name for n in body} == names
    ns: dict = {"re": re, "json": json}
    exec(compile(ast.Module(body=body, type_ignores=[]), str(VENDORED), "exec"), ns)  # noqa: S102 固定摘要的 vendored 纯函数
    return ns


def _real_bundles() -> dict[str, PrivateGradingBundleR2E]:
    out = {}
    for line in INGEST_GRADING.read_text(encoding="utf-8").splitlines():
        b = PrivateGradingBundleR2E.model_validate(json.loads(line))
        out[b.source_commit_hash[:12]] = b
    return out


def _bundle(expected: dict[str, str]) -> PrivateGradingBundleR2E:
    text = json.dumps(expected)
    entry = ".venv/bin/python -W ignore -m pytest -rA r2e_tests"
    files = [R2EHiddenTestFile(path="test_1.py", sha256=_sha("x"))]
    return PrivateGradingBundleR2E(
        instance_id="demo__" + "a" * 40, repo="demo", repo_key_lower="demo", base_commit="b" * 40,
        source_commit_hash="a" * 40, expected_output_json=text, expected_output_json_sha256=_sha(text),
        run_tests_sh=entry, run_tests_sh_sha256=_sha(entry), hidden_test_files=files,
        hidden_tests_tree_sha256=r2e_hidden_tests_tree_digest((f.path, f.sha256) for f in files),
        source_revision=port.R2E_DATASET_REVISION,
    )


def _wrap(test_output: str, *, rc: int = 0) -> str:
    return f"RH2_INSTALL_SKIPPED=1\n{START}\n{test_output}\n{END}\nRH2_TEST_RC={rc}\n"


def _summary(*lines: str) -> str:
    return "collected\n=========== short test summary info ===========\n" + "\n".join(lines) + "\n===== done in 0.1s =====\n"


# ---------------------------------------------------------------------------
# 来源固定
# ---------------------------------------------------------------------------


def test_vendored_rule_source_is_byte_pinned_and_decolor_regex_contains_a_raw_escape_byte():
    raw = VENDORED.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == port.R2E_RULE_SOURCE_SHA256
    assert port.r2e_rule_source_pin("prime_envs_c4d04dfe").sha256 == port.R2E_RULE_SOURCE_SHA256
    with pytest.raises(ValueError):
        port.r2e_rule_source_pin("prime_envs_latest")
    # 两次误读的根源：上游把 ESC 写成原始字节。模式是 \x1b\[\d+m，不是 \[\d+m。
    line, = [ln for ln in raw.split(b"\n") if b"re.sub(" in ln and b"\\d+m" in ln]
    assert b'r"\x1b\\[\\d+m"' in line
    assert port._DECOLOR_RE.pattern == "\\x1b\\[\\d+m"
    assert port.decolor_keys({"\x1b[1mT.test\x1b[0m": "PASSED", "plain[1m]": "FAILED"}) == {"T.test": "PASSED", "plain[1m]": "FAILED"}


# ---------------------------------------------------------------------------
# 与上游函数对拍
# ---------------------------------------------------------------------------


def _replay(paths: list[Path]) -> tuple[dict[float, int], list[str]]:
    up, bundles = _upstream(), _real_bundles()
    rewards: dict[float, int] = {0.0: 0, 1.0: 0}
    problems: list[str] = []
    for path in sorted(paths):
        prefix, = {part.split(".")[0] for part in path.parts if part.split(".")[0] in bundles}
        b = bundles[prefix]
        text = path.read_text(encoding="utf-8", errors="replace")
        expected = json.loads(b.expected_output_json)
        reward = up["calculate_reward"](text, b.expected_output_json)
        rewards[reward] += 1
        if up["parse_log_pytest"](text) != port.parse_log_pytest(text):
            problems.append(f"{path.name}: 解析映射与上游不同")
        if up["_decolor"](expected) != port.decolor_keys(expected):
            problems.append(f"{path.name}: 期望侧去色与上游不同")
        if port.prime_calculate_reward(text, b.expected_output_json) != reward:
            problems.append(f"{path.name}: reward 与上游不同")
        verdict = scoring.parse_eval_log_r2e(b, _wrap(text))
        if float(verdict.resolved) != reward:
            # 并集口径比上游严一处（空观测键）；真实语料上不应触发，触发就单列出来看
            problems.append(f"{path.name}: RH2 判定 {verdict.resolved} 与上游 reward {reward} 不同")
    return rewards, problems


def test_curated_corpus_matches_pinned_upstream_functions():
    paths = sorted(CURATED.glob("*.txt"))
    assert len(paths) == 8
    rewards, problems = _replay(paths)
    assert problems == []
    assert rewards == {0.0: 4, 1.0: 4}


@pytest.mark.parametrize(
    ("name", "resolved", "note"),
    [
        ("4bc6483564ae.gold.txt", True, "期望 24 键全带 \\x1b[1m…\\x1b[0m，两侧对称去色"),
        ("3ac9396e8c99.gold.txt", True, "自定义 unittest runner 自己打印同形摘要段"),
        ("19c5eea5db00.gold.txt", True, "期望里有 ERROR 键且观测同为 ERROR——不能套'失败即不过'"),
        ("22e98f8f4ccc.gold.txt", True, "orange3：xvfb-run 入口"),
        ("016af5f6352d.gold.txt", False, "来源缺陷：期望 FAILED、环境里 PASSED"),
        ("58ba5165234c.gold.txt", False, "来源缺陷：隐藏测试 import 了被 gold 排除的测试文件"),
        ("4bc6483564ae.noop.txt", False, "noop"),
        ("3ac9396e8c99.noop.txt", False, "noop"),
    ],
)
def test_curated_corpus_expected_verdicts(name: str, resolved: bool, note: str):
    b = _real_bundles()[name.split(".")[0]]
    verdict = scoring.parse_eval_log_r2e(b, _wrap((CURATED / name).read_text(encoding="utf-8", errors="replace")))
    assert verdict.apply_ok and verdict.grading_semantics == "r2e_expected_map", note
    assert verdict.resolved is resolved, note
    assert verdict.num_parsed_tests > 0, note
    fields = scoring.grading_outcome_fields(verdict)
    assert fields["reward"] == (1.0 if resolved else 0.0)
    assert fields["expected_total_count"] >= verdict.expected_match.expected_count


def test_curated_pillow_expected_keys_really_carry_ansi_and_errors_are_expected_for_pandas():
    bundles = _real_bundles()
    pillow = bundles["4bc6483564ae"].expected_map()
    assert len(pillow) == 24 and all("\x1b[" in k for k in pillow)
    assert not any("\x1b" in k for k in port.normalize_status_map(pillow))
    assert "ERROR" in set(bundles["19c5eea5db00"].expected_map().values())


def test_full_local_corpus_if_available():
    m3 = REPO_ROOT / "runs/env_overnight_20260916/M3"
    old = REPO_ROOT / "runs/env_probe_20260909_codex_backup/ledger/logs_r2e"
    if not m3.is_dir() or not old.is_dir():
        pytest.skip("本机没有 336 份 R2E 真实日志语料（runs/ 是 git-ignore 的本地证据）")
    paths = list((m3 / "gold_ledger/logs_r2e").glob("*/*/gold/a*/test_output.txt"))
    paths += list((m3 / "facts").glob("*/noop_x2/out*.txt"))
    paths += list(old.glob("*/*/*/a*/test_output.txt"))
    assert len(paths) == 336
    rewards, problems = _replay(paths)
    assert problems == []
    assert rewards == {0.0: 172, 1.0: 164}


# ---------------------------------------------------------------------------
# 计划 §3.2 的固定样本
# ---------------------------------------------------------------------------


def test_sample_ansi_expected_keys_resolve_against_plain_log_lines():
    expected = {f"\x1b[1mTestTiff.test_{i}\x1b[0m": "PASSED" for i in range(24)}
    log = _summary(*[f"PASSED r2e_tests/test_1.py::TestTiff::test_{i}" for i in range(24)])
    v = scoring.parse_eval_log_r2e(_bundle(expected), _wrap(log))
    assert v.resolved and (v.expected_match.match_count, v.expected_match.total_count) == (24, 24)
    assert port.prime_calculate_reward(log, json.dumps(expected)) == 1.0


def test_sample_no_summary_section_is_zero_parsed_not_an_exception():
    v = scoring.parse_eval_log_r2e(_bundle({"a": "PASSED"}), _wrap("ImportError: cannot import name 'x'\n", rc=2))
    assert v.apply_ok and not v.resolved and v.num_parsed_tests == 0
    assert v.expected_match.expected_present_count == 0 and v.reference_missing == ["a"]
    fields = scoring.grading_outcome_fields(v)
    assert (fields["failure_category"], fields["expected_match_count"], fields["expected_total_count"]) == ("tests_failed", 0, 1)


def test_sample_one_extra_observed_key_is_tests_failed():
    v = scoring.parse_eval_log_r2e(
        _bundle({"T.a": "PASSED"}), _wrap(_summary("PASSED r2e_tests/t.py::T::a", "PASSED r2e_tests/t.py::T::new")),
    )
    assert not v.resolved and v.expected_match.unexpected == ["T.new"]
    assert (v.expected_match.match_count, v.expected_match.total_count) == (1, 2)
    assert scoring.grading_outcome_fields(v)["failure_category"] == "tests_failed"


def test_sample_partially_present_expected_keys_are_not_all_missing():
    v = scoring.parse_eval_log_r2e(
        _bundle({"a": "PASSED", "b": "PASSED"}), _wrap(_summary("FAILED r2e_tests/t.py::a - AssertionError: no"), rc=1),
    )
    assert not v.resolved and v.expected_match.missing == ["b"] and v.expected_match.mismatched == ["a"]
    assert v.expected_match.expected_present_count == 1  # 部分在场：不是"参考全缺席"


def test_sample_expected_error_key_observed_as_error_resolves_even_with_nonzero_rc():
    expected = {"T.ok": "PASSED", "T.needs_fixture": "ERROR"}
    log = _summary("PASSED r2e_tests/t.py::T::ok", "ERROR r2e_tests/t.py::T::needs_fixture - fixture 'x' not found")
    v = scoring.parse_eval_log_r2e(_bundle(expected), _wrap(log, rc=1))
    assert v.resolved and scoring.grading_outcome_fields(v)["reward"] == 1.0


# ---------------------------------------------------------------------------
# 标记段纪律与边界
# ---------------------------------------------------------------------------


def test_only_the_marker_segment_is_a_status_source():
    b = _bundle({"a": "PASSED"})
    forged = _summary("PASSED r2e_tests/t.py::a")
    outside = forged + _wrap("nothing parsed here\n")
    v = scoring.parse_eval_log_r2e(b, outside)
    assert v.apply_ok and not v.resolved and v.num_parsed_tests == 0 and v.num_parsed_outside_segment == 1


def test_missing_markers_are_apply_not_ok_and_end_before_start_is_an_empty_segment():
    b = _bundle({"a": "PASSED"})
    v = scoring.parse_eval_log_r2e(b, _summary("PASSED r2e_tests/t.py::a"))
    assert not v.apply_ok and not v.resolved
    fields = scoring.grading_outcome_fields(v)
    assert fields["failure_category"] == "patch_apply_failed" and fields["expected_match_count"] is None
    assert fields["grading_semantics"] == "r2e_expected_map"
    v2 = scoring.parse_eval_log_r2e(b, f"{END}\n{START}\n" + _summary("PASSED r2e_tests/t.py::a"))
    assert v2.apply_ok and v2.num_parsed_tests == 0


def test_swebench_bad_code_strings_are_not_special_for_r2e():
    b = _bundle({"a": "PASSED"})
    v = scoring.parse_eval_log_r2e(b, _wrap(">>>>> Tests Errored\n" + _summary("PASSED r2e_tests/t.py::a")))
    assert v.apply_ok and v.resolved


def test_union_rule_is_stricter_than_upstream_on_empty_observed_key():
    expected = {"a": "PASSED", "b": "PASSED"}
    log = _summary("PASSED", "PASSED r2e_tests/t.py::a")  # 第一行没有 "::" → 上游产出空键并在比较时跳过
    assert _upstream()["calculate_reward"](log, json.dumps(expected)) == 1.0
    assert port.prime_calculate_reward(log, json.dumps(expected)) == 1.0
    v = scoring.parse_eval_log_r2e(_bundle(expected), _wrap(log))
    assert not v.resolved and v.expected_match.missing == ["b"] and v.expected_match.unexpected == [""]


def test_entry_rejects_a_non_r2e_bundle_and_verdict_shape_is_enforced():
    class _V2:
        schema_id = "rh2.private_grading_bundle.v2"
        instance_id = "x"

    with pytest.raises(ValueError, match="只服务"):
        scoring.parse_eval_log_r2e(_V2(), "")
    base = dict(
        instance_id="x", apply_ok=True, resolution="RESOLVED_NO", resolved=False, f2p_rate=0.0, p2p_rate=0.0,
        f2p_success=[], f2p_failure=[], p2p_success=[], p2p_failure=[], num_parsed_tests=1,
    )
    with pytest.raises(ValueError, match="expected_match 必填"):
        scoring.EvalVerdict(**base, grading_semantics="r2e_expected_map")
    match = scoring.expected_map_matches({"a": "PASSED"}, {"a": "PASSED"})
    with pytest.raises(ValueError, match="不得携带 expected_match"):
        scoring.EvalVerdict(**base, expected_match=match)
    with pytest.raises(ValueError, match="矛盾"):
        scoring.EvalVerdict(**base, grading_semantics="r2e_expected_map", expected_match=match)  # match 说 resolved


def test_swe_verdict_defaults_are_unchanged():
    v = scoring.EvalVerdict(
        instance_id="x", apply_ok=True, resolution="RESOLVED_NO", resolved=False, f2p_rate=0.0, p2p_rate=1.0,
        f2p_success=[], f2p_failure=["t"], p2p_success=["p"], p2p_failure=[], num_parsed_tests=2,
    )
    assert v.grading_semantics == "swe_f2p_p2p" and v.expected_match is None
    assert "grading_semantics" not in scoring.grading_outcome_fields(v)


def test_revised_expected_resolves_the_source_defect_logs():
    """r2e-mr-001（用户 09-24 批准 T0-1）：coveragepy `016af5f6` 的期望单键改 PASSED 之后，同一份 gold 日志由 0 变 1，
    noop 日志仍是 0（只剩目标键不符）。来源版期望下的结论不变（上面的对拍用例）。"""

    current = {}
    for line in INGEST_GRADING_CURRENT.read_text(encoding="utf-8").splitlines():
        b = PrivateGradingBundleR2E.model_validate(json.loads(line))
        current[b.source_commit_hash[:12]] = b
    revised = current["016af5f6352d"]
    assert revised.material_revisions == ["r2e-mr-001"]
    gold = scoring.parse_eval_log_r2e(revised, _wrap((CURATED / "016af5f6352d.gold.txt").read_text(encoding="utf-8", errors="replace")))
    assert gold.resolved is True
    assert _real_bundles()["016af5f6352d"].material_revisions == []  # 来源版

