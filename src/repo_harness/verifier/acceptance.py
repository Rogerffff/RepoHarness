"""Verifier accepted 判定策略。"""

from __future__ import annotations

from repo_harness.schema_versions import ACCEPTANCE_POLICY_VERSION
from repo_harness.verifier.schemas import TestCaseResult, VerifierResult

LOW_CONFIDENCE_THRESHOLD = 0.5


def apply_acceptance_policy(
    *,
    command: str,
    exit_code: int | None,
    timeout: bool,
    parser_confidence: float,
    test_cases: list[TestCaseResult],
    fail_to_pass_tests: list[str],
    pass_to_pass_tests: list[str],
    error_type: str | None,
    verifier_stage: str | None = None,
    raw_output_ref: object | None = None,
) -> VerifierResult:
    case_by_id = {case.test_id: case for case in test_cases}
    fail_passed = sum(1 for test_id in fail_to_pass_tests if _case_passed(case_by_id.get(test_id)))
    pass_passed = sum(1 for test_id in pass_to_pass_tests if _case_passed(case_by_id.get(test_id)))
    declared_total = len(fail_to_pass_tests) + len(pass_to_pass_tests)
    total_cases = len(test_cases)
    pass_count = sum(1 for case in test_cases if case.status == "passed")
    pass_ratio = pass_count / total_cases if total_cases else (1.0 if exit_code == 0 else 0.0)

    accepted = False
    accepted_fallback_reason = None
    effective_error = error_type
    if timeout:
        accepted = False
        effective_error = "test_timeout"
    elif effective_error in {"test_command_error", "dependency_error", "patch_apply_failed"}:
        accepted = False
    elif parser_confidence < LOW_CONFIDENCE_THRESHOLD:
        accepted = False
        effective_error = "low_parser_confidence"
    elif fail_to_pass_tests or pass_to_pass_tests:
        accepted = fail_passed == len(fail_to_pass_tests) and pass_passed == len(pass_to_pass_tests)
        if not accepted and effective_error is None:
            if pass_passed < len(pass_to_pass_tests):
                effective_error = "regression_detected"
            else:
                effective_error = "assertion_failure"
        elif not accepted and pass_passed < len(pass_to_pass_tests):
            effective_error = "regression_detected"
    else:
        accepted = exit_code == 0
        accepted_fallback_reason = "overall_exit_code_zero"
        if not accepted and effective_error is None:
            effective_error = "assertion_failure"

    return VerifierResult(
        verifier_stage=verifier_stage,  # type: ignore[arg-type]
        parser_confidence=parser_confidence,
        command=command,
        raw_output_ref=raw_output_ref,  # type: ignore[arg-type]
        test_cases=test_cases,
        accepted=accepted,
        acceptance_policy_version=ACCEPTANCE_POLICY_VERSION,
        accepted_fallback_reason=accepted_fallback_reason,
        pass_ratio=pass_ratio,
        fail_to_pass={"passed": fail_passed, "total": len(fail_to_pass_tests)},
        pass_to_pass={"passed": pass_passed, "total": len(pass_to_pass_tests)},
        exit_code=exit_code,
        timeout=timeout,
        error_type=effective_error,
    )


def _case_passed(case: TestCaseResult | None) -> bool:
    return case is not None and case.status == "passed"


def build_error_verifier_result(
    *,
    command: str,
    error_type: str,
    verifier_stage: str | None = None,
    timeout: bool = False,
    raw_output_ref: object | None = None,
) -> VerifierResult:
    return apply_acceptance_policy(
        command=command,
        exit_code=None,
        timeout=timeout,
        parser_confidence=1.0,
        test_cases=[],
        fail_to_pass_tests=[],
        pass_to_pass_tests=[],
        error_type=error_type,
        verifier_stage=verifier_stage,
        raw_output_ref=raw_output_ref,
    )
