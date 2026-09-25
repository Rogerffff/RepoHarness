"""R2E 来源语义在 manager 里的两处接缝（R2E 接线 R-b，A 线复核 R2；无 docker）。

1. `execution_failure_trigger` 的"参考全缺席"对 R2E 按**键在场关系**判，不借用恒空的 F2P/P2P 桶。
2. `GradingEnvSpec.grading_semantics` 在 spec 构造时确定，本次评分的每一份报告都带它——正常结论、P-A 候选归因、
   提前 infra、补丁应用失败、parser 链路错误。A 线探针（r2e_grading_wiring_review_20260920/probe_plan_seams.py）
   当时的反例是后三类回落到 `swe_f2p_p2p`；这里把同一组形态改成正向断言，verdict 由真实 `parse_eval_log_r2e` 产出。
"""

from __future__ import annotations

import hashlib
import json
from unittest.mock import AsyncMock

import pytest
from grading_fixtures import (
    GOOD_PATCH,
    TAMPER_SEGMENT,
    FakeDocker,
    FakeWorkspace,
    make_fixture_spec,
)

from repoharness2.envpack import scoring
from repoharness2.envpack.bundles_v2 import (
    PrivateGradingBundleR2E,
    R2EHiddenTestFile,
    r2e_hidden_tests_tree_digest,
)
from repoharness2.envpack.r2e_parsers import R2E_DATASET_REVISION, R2E_GRADER_VERSION_TAG
from repoharness2.grading.manager import (
    GradingEnvSpec,
    GradingManagerConfig,
    SWEGradingManager,
    execution_failure_trigger,
)

BASE = "a" * 40
START, END = scoring.R2E_EVAL_START_MARKER, scoring.R2E_EVAL_END_MARKER


def _sha(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _bundle(expected: dict[str, str]) -> PrivateGradingBundleR2E:
    text, entry = json.dumps(expected), ".venv/bin/python -W ignore -m pytest -rA r2e_tests"
    files = [R2EHiddenTestFile(path="test_1.py", sha256=_sha("x"))]
    return PrivateGradingBundleR2E(
        instance_id="demo__" + "f" * 40, repo="demo", repo_key_lower="demo", base_commit=BASE,
        source_commit_hash="f" * 40, expected_output_json=text, expected_output_json_sha256=_sha(text),
        run_tests_sh=entry, run_tests_sh_sha256=_sha(entry), hidden_test_files=files,
        hidden_tests_tree_sha256=r2e_hidden_tests_tree_digest((f.path, f.sha256) for f in files),
        source_revision=R2E_DATASET_REVISION,
    )


def _log(*summary_lines: str, rc: int = 0) -> str:
    body = "\n".join(summary_lines)
    return f"{START}\n==== short test summary info ====\n{body}\n==== done ====\n{END}\nRH2_TEST_RC={rc}\n"


EXPECTED = {"T.a": "PASSED", "T.b": "PASSED"}


def _verdict(*summary_lines: str) -> scoring.EvalVerdict:
    return scoring.parse_eval_log_r2e(_bundle(EXPECTED), _log(*summary_lines))


# ---------------------------------------------------------------------------
# 1. "参考全缺席"的键在场判据（计划 §5.1 R-b 的四例）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("lines", "trigger", "why"),
    [
        (("FAILED r2e_tests/t.py::T::a - boom", "FAILED r2e_tests/t.py::T::b - boom"), None,
         "状态全错但键全在：测试正常跑完的 tests_failed"),
        (("FAILED r2e_tests/t.py::T::a - boom",), None,
         "部分缺键（A 线反例：旧实现借空桶会误判成全缺席）"),
        (("PASSED r2e_tests/t.py::Other::zzz",), "reference_all_missing", "解析到了测试，但期望键一个都不在场"),
        ((), "zero_parsed", "零解析"),
    ],
)
def test_r2e_reference_presence_trigger(lines, trigger, why):
    verdict = _verdict(*lines)
    assert verdict.grading_semantics == "r2e_expected_map"
    assert execution_failure_trigger(verdict) == trigger, why


def test_swe_trigger_is_unchanged_for_bucketed_verdicts():
    def _swe(**kw) -> scoring.EvalVerdict:
        base = dict(
            instance_id="x", apply_ok=True, resolution="RESOLVED_NO", resolved=False, f2p_rate=0.0, p2p_rate=0.0,
            f2p_success=[], f2p_failure=["f"], p2p_success=[], p2p_failure=["p"], num_parsed_tests=3,
        )
        base.update(kw)
        return scoring.EvalVerdict(**base)

    assert execution_failure_trigger(_swe(reference_missing=["f", "p"])) == "reference_all_missing"
    assert execution_failure_trigger(_swe(reference_missing=["f"])) is None
    assert execution_failure_trigger(_swe(num_parsed_tests=0)) == "zero_parsed"


# ---------------------------------------------------------------------------
# 2. 来源语义进所有报告分支
# ---------------------------------------------------------------------------


def _r2e_spec(**overrides) -> GradingEnvSpec:
    bundle = _bundle(EXPECTED)
    kwargs = dict(
        checkout_mode="image_embedded",
        task_id="r2e_gym_subset::" + bundle.instance_id,
        parse_log=lambda text: scoring.parse_eval_log_r2e(bundle, text),
        grader_version=R2E_GRADER_VERSION_TAG,
        grading_semantics="r2e_expected_map",
    )
    kwargs.update(overrides)
    return make_fixture_spec(BASE, "fake", **kwargs)


async def _grade(tmp_path, fake: FakeDocker, *, spec: GradingEnvSpec | None = None, patch: str = GOOD_PATCH,
                 decide=None):
    manager = SWEGradingManager(GradingManagerConfig(eval_log_dir=tmp_path / "logs"), docker=fake)
    if decide is not None:
        manager._decide_execution_failure = AsyncMock(return_value=decide)
    return await manager.grade(trajectory_id="traj_r2e", workspace=FakeWorkspace(patch), spec=spec or _r2e_spec())


async def test_resolved_and_tests_failed_reports_carry_expected_counts(tmp_path):
    ok = await _grade(tmp_path, FakeDocker(base_commit=BASE, eval_log=_log(
        "PASSED r2e_tests/t.py::T::a", "PASSED r2e_tests/t.py::T::b")))
    assert (ok.outcome, ok.reward, ok.grading_semantics) == ("resolved", 1.0, "r2e_expected_map")
    assert (ok.expected_match_count, ok.expected_total_count, ok.f2p_total_count) == (2, 2, None)
    assert ok.grader_version == R2E_GRADER_VERSION_TAG

    bad = await _grade(tmp_path, FakeDocker(base_commit=BASE, eval_log=_log(
        "PASSED r2e_tests/t.py::T::a", "FAILED r2e_tests/t.py::T::b - boom", rc=1)))
    assert (bad.outcome, bad.failure_category, bad.reward) == ("unresolved", "tests_failed", 0.0)
    assert (bad.grading_semantics, bad.expected_match_count, bad.expected_total_count) == ("r2e_expected_map", 1, 2)


async def test_partially_missing_expected_key_stays_a_source_rule_zero_without_entering_pa(tmp_path):
    decide = AsyncMock()
    manager = SWEGradingManager(GradingManagerConfig(eval_log_dir=tmp_path / "logs"),
                                docker=FakeDocker(base_commit=BASE, eval_log=_log("PASSED r2e_tests/t.py::T::a")))
    manager._decide_execution_failure = decide
    report = await manager.grade(trajectory_id="traj_partial", workspace=FakeWorkspace(GOOD_PATCH), spec=_r2e_spec())
    assert (report.failure_category, report.reward) == ("tests_failed", 0.0)
    assert (report.expected_match_count, report.expected_total_count) == (1, 2)
    decide.assert_not_called()


async def test_candidate_attribution_branch_keeps_r2e_semantics_and_no_counts(tmp_path):
    report = await _grade(
        tmp_path, FakeDocker(base_commit=BASE, eval_log=_log()),
        decide={"kind": "candidate", "stage": "test_collection", "evidence": ["SyntaxError at pkg/core.py:3"]},
    )
    assert (report.outcome, report.failure_category, report.reward) == ("unresolved", "candidate_execution_failed", 0.0)
    assert report.grading_semantics == "r2e_expected_map"
    assert report.expected_match_count is None and report.expected_total_count is None


@pytest.mark.parametrize("kind", ["resource", "unattributed"])
async def test_pa_infra_branches_keep_r2e_semantics_and_no_reward(tmp_path, kind):
    decision = {"kind": kind, "resource_detail": "oom_kill=1", "missing": ["env_qualification"]}
    report = await _grade(tmp_path, FakeDocker(base_commit=BASE, eval_log=_log()), decide=decision)
    assert (report.outcome, report.reward, report.grading_semantics) == ("failed_to_grade", None, "r2e_expected_map")
    assert report.expected_match_count is None


async def test_infra_before_parser_and_patch_apply_failed_keep_r2e_semantics(tmp_path):
    early = await _grade(tmp_path, FakeDocker(base_commit=BASE, pull_fail=True, image_present=False))
    assert (early.outcome, early.reward, early.grading_semantics) == ("failed_to_grade", None, "r2e_expected_map")

    no_apply = await _grade(tmp_path, FakeDocker(base_commit=BASE, apply_exit_code=1))
    assert (no_apply.failure_category, no_apply.reward) == ("patch_apply_failed", 0.0)
    assert no_apply.grading_semantics == "r2e_expected_map" and no_apply.expected_total_count is None


async def test_missing_markers_become_infra_with_r2e_semantics(tmp_path):
    report = await _grade(tmp_path, FakeDocker(base_commit=BASE, eval_log="crashed before markers\n"))
    assert (report.outcome, report.failure_category, report.reward) == ("failed_to_grade", "test_log_parse_failed", None)
    assert report.grading_semantics == "r2e_expected_map"


async def test_parser_verdict_semantics_must_match_the_spec(tmp_path):
    swe_verdict = scoring.EvalVerdict(
        instance_id="x", apply_ok=True, resolution="RESOLVED_FULL", resolved=True, f2p_rate=1.0, p2p_rate=1.0,
        f2p_success=["f"], f2p_failure=[], p2p_success=["p"], p2p_failure=[], num_parsed_tests=2,
    )
    report = await _grade(tmp_path, FakeDocker(base_commit=BASE), spec=_r2e_spec(parse_log=lambda _: swe_verdict))
    assert (report.outcome, report.failure_category, report.reward) == ("failed_to_grade", "test_log_parse_failed", None)
    assert "parser_semantics_mismatch:spec=r2e_expected_map:verdict=swe_f2p_p2p" in report.infra_failure_detail
    assert report.grading_semantics == "r2e_expected_map"


async def test_legacy_diff_path_hygiene_downgrade_is_infra_not_a_contract_crash(tmp_path):
    report = await _grade(
        tmp_path,
        FakeDocker(base_commit=BASE, eval_log=_log("PASSED r2e_tests/t.py::T::a", "PASSED r2e_tests/t.py::T::b")),
        patch=GOOD_PATCH + TAMPER_SEGMENT,
    )
    assert (report.outcome, report.reward, report.grading_semantics) == ("failed_to_grade", None, "r2e_expected_map")
    assert report.infra_failure_detail == "hygiene_downgrade_unsupported_for_r2e_expected_map"


async def test_swe_reports_still_default_to_swe_semantics(tmp_path):
    manager = SWEGradingManager(GradingManagerConfig(eval_log_dir=tmp_path / "logs"), docker=FakeDocker(base_commit=BASE))
    report = await manager.grade(
        trajectory_id="traj_swe", workspace=FakeWorkspace(GOOD_PATCH),
        spec=make_fixture_spec(BASE, "fake", checkout_mode="image_embedded"),
    )
    assert (report.outcome, report.grading_semantics, report.expected_total_count) == ("resolved", "swe_f2p_p2p", None)


def test_spec_rejects_an_unknown_semantics_value():
    with pytest.raises(ValueError, match="grading_semantics"):
        _r2e_spec(grading_semantics="custom")
