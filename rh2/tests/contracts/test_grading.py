"""grading.py 的 fail-closed 单测：失败归因三分与 patch hygiene 的互锁。

最关键的一条（执行计划点名）：infra_failure 携带 reward=0 必须拒收。
"""

import pytest
from contract_samples import (
    valid_grading_report,
    valid_infra_grading_report,
    valid_patch_hygiene,
)
from pydantic import ValidationError

from repoharness2.contracts import GradingReport, PatchHygieneResult


def test_infra_failure_with_reward_zero_rejected():
    """点名非法样例：基建故障绝不允许伪装成 reward=0 的负样本。"""

    payload = valid_infra_grading_report()
    payload["reward"] = 0.0
    with pytest.raises(ValidationError, match="reward 必须为 None"):
        GradingReport.model_validate(payload)


def test_infra_failure_valid_shape_passes():
    report = GradingReport.model_validate(valid_infra_grading_report())
    assert report.reward is None
    assert report.failure_category == "infra_failure"


def test_failed_to_grade_requires_infra_category():
    payload = valid_infra_grading_report()
    payload["failure_category"] = "tests_failed"
    with pytest.raises(ValidationError, match="infra_failure"):
        GradingReport.model_validate(payload)


def test_failed_to_grade_requires_detail():
    payload = valid_infra_grading_report()
    payload["infra_failure_detail"] = None
    with pytest.raises(ValidationError, match="infra_failure_detail"):
        GradingReport.model_validate(payload)


def test_unresolved_requires_failure_category():
    payload = valid_grading_report()
    payload["outcome"] = "unresolved"
    payload["failure_category"] = None
    payload["reward"] = 0.0
    with pytest.raises(ValidationError, match="patch_apply_failed 或 tests_failed"):
        GradingReport.model_validate(payload)


def test_unresolved_tests_failed_valid():
    payload = valid_grading_report()
    payload["outcome"] = "unresolved"
    payload["failure_category"] = "tests_failed"
    payload["reward"] = 0.0
    payload["f2p_pass_count"] = 1  # 3 个 F2P 只过 1 个
    report = GradingReport.model_validate(payload)
    assert report.reward == 0.0


def test_resolved_with_failing_p2p_rejected():
    payload = valid_grading_report()
    payload["p2p_fail_count"] = 2
    with pytest.raises(ValidationError, match="p2p_fail_count"):
        GradingReport.model_validate(payload)


def test_resolved_requires_all_f2p_passed():
    payload = valid_grading_report()
    payload["f2p_pass_count"] = 2  # 3 个只过 2 个不算 resolved
    with pytest.raises(ValidationError, match="F2P"):
        GradingReport.model_validate(payload)


def test_f2p_pass_greater_than_total_rejected():
    payload = valid_grading_report()
    payload["outcome"] = "unresolved"
    payload["failure_category"] = "tests_failed"
    payload["reward"] = 0.0
    payload["f2p_pass_count"] = 5
    payload["f2p_total_count"] = 3
    with pytest.raises(ValidationError, match="不得大于"):
        GradingReport.model_validate(payload)


def test_patch_apply_failed_with_test_counts_rejected():
    payload = valid_grading_report()
    payload["outcome"] = "unresolved"
    payload["failure_category"] = "patch_apply_failed"
    payload["reward"] = 0.0
    with pytest.raises(ValidationError, match="不得携带 F2P/P2P"):
        GradingReport.model_validate(payload)


def test_hygiene_rejected_patch_cannot_be_resolved():
    payload = valid_grading_report()
    payload["patch_hygiene"] = {
        "cleaned_patch_digest": valid_patch_hygiene()["cleaned_patch_digest"],
        "replayed_on_clean_checkout": True,
        "test_files_modified": True,
        "forbidden_path_touched": False,
        "forbidden_paths": [],
        "verdict": "rejected_test_tampering",
    }
    with pytest.raises(ValidationError, match="不得给出 resolved"):
        GradingReport.model_validate(payload)


def test_graded_outcome_requires_hygiene_result():
    payload = valid_grading_report()
    payload["patch_hygiene"] = None
    with pytest.raises(ValidationError, match="patch_hygiene"):
        GradingReport.model_validate(payload)


def test_hygiene_clean_verdict_with_tampering_fact_rejected():
    payload = valid_patch_hygiene()
    payload["test_files_modified"] = True  # verdict 仍是 clean -> 矛盾
    with pytest.raises(ValidationError, match="矛盾"):
        PatchHygieneResult.model_validate(payload)


def test_hygiene_forbidden_paths_iff_touched():
    payload = valid_patch_hygiene()
    payload["forbidden_paths"] = ["docs/PROBLEM_STATEMENT.md"]  # touched=False 却有路径
    with pytest.raises(ValidationError, match="forbidden_path_touched"):
        PatchHygieneResult.model_validate(payload)


def test_hygiene_contamination_verdict_valid():
    payload = valid_patch_hygiene()
    payload["forbidden_path_touched"] = True
    payload["forbidden_paths"] = ["docs/PROBLEM_STATEMENT.md"]
    payload["verdict"] = "rejected_forbidden_contamination"
    result = PatchHygieneResult.model_validate(payload)
    assert result.verdict == "rejected_forbidden_contamination"
