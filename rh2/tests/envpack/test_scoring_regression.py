"""scoring 库层对 S0-7 真实 eval 日志的回归（S1-2 验收：解析结果与 S0-7 记录一致）。

数据源（S0-7 远程执行时落盘、随 docs 入库的证据文件，共 428KB）：

    docs/.../s0/swe_smoke_dumps/eval_logs/<instance_id>.eval.log   官方 eval 合并流原始日志
    docs/.../s0/swe_smoke_dumps/<instance_id>.json                 逐题 trace dump（含当时的
                                                                   解析结论 summary/metrics/swe_eval）

覆盖三类官方 parser：django unittest verbose（11099/11133/16139）、sympy bin/test
（14711/15349）、pytest -rA（requests 1142/2931 + astropy 14995，astropy 带 ANSI 色码）。
对照字段：resolution / apply_ok / reward / f2p_rate / p2p_rate / f2p_success /
f2p_failure / p2p_failure——全部要求与 S0-7 落盘记录一致。

本测试也是 A7 接口的验收点：grading_outcome_fields(verdict) 的输出必须能直接
构造出通过 contracts.GradingReport fail-closed 校验的报告。
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from repoharness2.contracts import GradingReport, PatchHygieneResult
from repoharness2.envpack.bundles import load_bundle_pairs
from repoharness2.envpack.scoring import (
    GRADER_NAME,
    EvalVerdict,
    grading_outcome_fields,
    parse_eval_log,
    swebench_version,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DUMPS_DIR = REPO_ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/s0/swe_smoke_dumps"
EVAL_LOG_DIR = DUMPS_DIR / "eval_logs"

INSTANCE_IDS = [
    "django__django-11099",
    "django__django-11133",
    "django__django-16139",
    "sympy__sympy-14711",
    "sympy__sympy-15349",
    "psf__requests-1142",
    "psf__requests-2931",
    "astropy__astropy-14995",
]

pytestmark = pytest.mark.skipif(
    not EVAL_LOG_DIR.is_dir(),
    reason=f"S0-7 证据目录不存在（{EVAL_LOG_DIR}）——回归数据随 docs 入库，正常检出不应缺失",
)


def load_pair(instance_id: str):
    return load_bundle_pairs(subset=[instance_id])[0]


@pytest.fixture(scope="module")
def s0_records() -> dict[str, dict]:
    records = {}
    for iid in INSTANCE_IDS:
        dump = json.loads((DUMPS_DIR / f"{iid}.json").read_text())
        records[iid] = {
            "summary": dump["summary"],
            "swe_eval": dump["trace"]["info"]["swe_eval"],
        }
    return records


@pytest.mark.parametrize("instance_id", INSTANCE_IDS)
def test_parse_matches_s0_record(instance_id: str, s0_records):
    pair = load_pair(instance_id)
    log_text = (EVAL_LOG_DIR / f"{instance_id}.eval.log").read_text()
    verdict = parse_eval_log(pair.private, log_text)

    expected = s0_records[instance_id]
    summary, swe_eval = expected["summary"], expected["swe_eval"]

    assert verdict.resolution == summary["resolution"]
    assert verdict.apply_ok == swe_eval["apply_ok"]
    assert verdict.reward == summary["reward"]
    assert verdict.f2p_rate == pytest.approx(summary["metrics"]["f2p_rate"])
    assert verdict.p2p_rate == pytest.approx(summary["metrics"]["p2p_rate"])
    assert verdict.f2p_success == swe_eval["f2p_success"]
    assert verdict.f2p_failure == swe_eval["f2p_failure"]
    # dump 里 p2p_failure 截断到 20 条；8 题实际最多 1 条，直接等值比较
    assert verdict.p2p_failure == swe_eval["p2p_failure"]
    assert len(verdict.p2p_success) + len(verdict.p2p_failure) == swe_eval["p2p_total"]
    assert verdict.num_parsed_tests > 0


def test_ansi_colored_pytest_log_really_covered():
    """astropy 日志确实带 ANSI 色码（官方 parser 自行处理，本层不剥色的证据）。"""
    log_text = (EVAL_LOG_DIR / "astropy__astropy-14995.eval.log").read_text()
    assert "\x1b[" in log_text
    verdict = parse_eval_log(load_pair("astropy__astropy-14995").private, log_text)
    assert verdict.resolved and len(verdict.p2p_success) == 179


def test_unresolved_case_is_p2p_regression():
    """psf__requests-2931：F2P 全过但 P2P 回归 1 条 → RESOLVED_NO、reward=0（判据活案例）。"""
    log_text = (EVAL_LOG_DIR / "psf__requests-2931.eval.log").read_text()
    verdict = parse_eval_log(load_pair("psf__requests-2931").private, log_text)
    assert verdict.f2p_rate == 1.0 and verdict.p2p_rate < 1.0
    assert verdict.p2p_failure == ["test_requests.py::TestRequests::test_params_bytes_are_encoded"]
    assert verdict.reward == 0.0


def test_apply_fail_bad_code_maps_to_patch_apply_failed():
    """日志含官方坏码（>>>>> Patch Apply Failed）→ apply_ok=False → patch_apply_failed。"""
    pair = load_pair("django__django-11099")
    verdict = parse_eval_log(pair.private, ">>>>> Patch Apply Failed\nsome traceback\n")
    assert not verdict.apply_ok and not verdict.resolved
    fields = grading_outcome_fields(verdict)
    assert fields["outcome"] == "unresolved"
    assert fields["failure_category"] == "patch_apply_failed"
    assert fields["reward"] == 0.0
    assert fields["f2p_pass_count"] is None  # 测试未可信运行，不携带计数


# ---------------------------------------------------------------------------
# A7 接口验收：verdict -> GradingReport 字段组必须过 contracts 的 fail-closed 校验
# ---------------------------------------------------------------------------


def build_report(verdict: EvalVerdict) -> GradingReport:
    return GradingReport(
        report_id=f"gr-{verdict.instance_id}",
        trajectory_id=f"traj-{verdict.instance_id}",
        task_id=verdict.instance_id,
        grader_name=GRADER_NAME,
        grader_version=f"swebench=={swebench_version()}",
        patch_hygiene=PatchHygieneResult(
            cleaned_patch_digest="sha256:" + "0" * 64,
            replayed_on_clean_checkout=False,  # S0-7 同容器评分形态（S1-4 升级为 True）
            test_files_modified=False,
            forbidden_path_touched=False,
            verdict="clean",
        ),
        graded_at_utc=datetime(2026, 7, 7, tzinfo=timezone.utc),
        **grading_outcome_fields(verdict),
    )


def test_resolved_verdict_builds_valid_grading_report():
    log_text = (EVAL_LOG_DIR / "django__django-11099.eval.log").read_text()
    verdict = parse_eval_log(load_pair("django__django-11099").private, log_text)
    report = build_report(verdict)
    assert report.outcome == "resolved" and report.reward == 1.0
    assert report.f2p_pass_count == report.f2p_total_count == 3
    assert report.p2p_fail_count == 0 and report.p2p_total_count == 19


def test_tests_failed_verdict_builds_valid_grading_report():
    log_text = (EVAL_LOG_DIR / "psf__requests-2931.eval.log").read_text()
    verdict = parse_eval_log(load_pair("psf__requests-2931").private, log_text)
    report = build_report(verdict)
    assert report.outcome == "unresolved" and report.failure_category == "tests_failed"
    assert report.reward == 0.0
    assert report.p2p_fail_count == 1 and report.p2p_total_count == 84


def test_apply_failed_verdict_builds_valid_grading_report():
    verdict = parse_eval_log(load_pair("django__django-11099").private, ">>>>> Patch Apply Failed\n")
    report = build_report(verdict)
    assert report.failure_category == "patch_apply_failed"
    assert report.f2p_pass_count is None and report.p2p_total_count is None


def test_grading_outcome_fields_never_emits_infra_failure():
    """parser 层只见日志，infra_failure 归 S1-4 manager——库层输出永远不含它。"""
    for iid in INSTANCE_IDS:
        log_text = (EVAL_LOG_DIR / f"{iid}.eval.log").read_text()
        fields = grading_outcome_fields(parse_eval_log(load_pair(iid).private, log_text))
        assert fields["failure_category"] != "infra_failure"
        assert fields["reward"] is not None  # 评出结果就必有 reward（0/1），绝无 None
