"""grading.py 的 fail-closed 单测：失败归因与 patch hygiene 的互锁。

最关键的一条（执行计划点名）：infra_failure 携带 reward=0 必须拒收。
S1-1b 追加 R1~R4 回归：二值锁（unresolved<=>0.0、resolved<=>1.0）、
NaN reward 拒收、tests_failed 四计数齐全、test_log_parse_failed 归 infra 族。
"""

import pytest
from contract_samples import (
    valid_grading_report,
    valid_infra_grading_report,
    valid_patch_hygiene,
)
from pydantic import ValidationError

from repoharness2.contracts import GradingReport, PatchHygieneResult


def valid_tests_failed_report() -> dict:
    """unresolved + tests_failed 的合法形态（四计数齐全，reward 恰为 0.0）。"""

    payload = valid_grading_report()
    payload["outcome"] = "unresolved"
    payload["failure_category"] = "tests_failed"
    payload["reward"] = 0.0
    payload["f2p_pass_count"] = 1  # 3 个 F2P 只过 1 个
    return payload


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
    report = GradingReport.model_validate(valid_tests_failed_report())
    assert report.reward == 0.0


# ---------------------------------------------------------------------------
# S1-1b 回归：R1~R4（修复前这些反例都能通过，修复后必须拒收）
# ---------------------------------------------------------------------------


def test_r1_unresolved_with_full_reward_rejected():
    """R1：unresolved + reward=1.0——二值锁要求 unresolved 恰为 0.0。"""

    payload = valid_tests_failed_report()
    payload["reward"] = 1.0
    with pytest.raises(ValidationError, match="恰为 0.0"):
        GradingReport.model_validate(payload)


def test_r2_resolved_with_nan_reward_rejected():
    """R2：reward=NaN 穿过数值比较（NaN 与任何数比较都是 False），基类必须拦。"""

    payload = valid_grading_report()
    payload["reward"] = float("nan")
    with pytest.raises(ValidationError):
        GradingReport.model_validate(payload)


def test_r3_resolved_with_partial_reward_rejected():
    """R3：resolved + reward=0.5——binary_v1 语义下 resolved 恰为 1.0，中间值拒收。"""

    payload = valid_grading_report()
    payload["reward"] = 0.5
    with pytest.raises(ValidationError, match="恰为 1.0"):
        GradingReport.model_validate(payload)


def test_r4_tests_failed_without_counts_rejected():
    """R4：tests_failed 却四计数全空——解析不出计数应归因 test_log_parse_failed。"""

    payload = valid_tests_failed_report()
    for key in ("f2p_pass_count", "f2p_total_count", "p2p_fail_count", "p2p_total_count"):
        payload[key] = None
    with pytest.raises(ValidationError, match="四个计数必须齐全"):
        GradingReport.model_validate(payload)


def test_reward_scale_version_cannot_be_silently_bumped():
    """连续 reward 必须显式升版：binary_v1 之外的取值在本版契约下不可表示。"""

    payload = valid_grading_report()
    payload["reward_scale_version"] = "continuous_v2"
    with pytest.raises(ValidationError, match="reward_scale_version"):
        GradingReport.model_validate(payload)


# ---------------------------------------------------------------------------
# test_log_parse_failed：infra 族的第二个成员（S1-1b 新增）
# ---------------------------------------------------------------------------


def test_log_parse_failed_valid_shape_passes():
    """测试跑了但日志解析不出：合法形态与 infra_failure 同构（无 reward、无计数）。"""

    payload = valid_infra_grading_report()
    payload["failure_category"] = "test_log_parse_failed"
    payload["infra_failure_detail"] = "test_output_markers_missing"
    report = GradingReport.model_validate(payload)
    assert report.reward is None


def test_log_parse_failed_with_zero_reward_rejected():
    """infra 族互锁：日志解析失败同样绝不允许伪装成 reward=0 的负样本。"""

    payload = valid_infra_grading_report()
    payload["failure_category"] = "test_log_parse_failed"
    payload["reward"] = 0.0
    with pytest.raises(ValidationError, match="reward 必须为 None"):
        GradingReport.model_validate(payload)


def test_log_parse_failed_not_allowed_under_unresolved():
    """test_log_parse_failed 是基建归因，只许配 failed_to_grade，不许混进 unresolved。"""

    payload = valid_tests_failed_report()
    payload["failure_category"] = "test_log_parse_failed"
    with pytest.raises(ValidationError, match="patch_apply_failed 或 tests_failed"):
        GradingReport.model_validate(payload)


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
