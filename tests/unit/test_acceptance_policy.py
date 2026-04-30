from repo_harness.verifier import TestCaseResult, apply_acceptance_policy, build_error_verifier_result


def test_acceptance_policy_requires_fail_to_pass_and_pass_to_pass():
    result = apply_acceptance_policy(
        command="pytest -q",
        exit_code=0,
        timeout=False,
        parser_confidence=0.9,
        test_cases=[
            TestCaseResult(test_id="tests/test_demo.py::test_fix", status="passed"),
            TestCaseResult(test_id="tests/test_demo.py::test_old", status="passed"),
        ],
        fail_to_pass_tests=["tests/test_demo.py::test_fix"],
        pass_to_pass_tests=["tests/test_demo.py::test_old"],
        error_type=None,
    )

    assert result.accepted is True
    assert result.fail_to_pass == {"passed": 1, "total": 1}
    assert result.pass_to_pass == {"passed": 1, "total": 1}


def test_acceptance_policy_detects_regression():
    result = apply_acceptance_policy(
        command="pytest -q",
        exit_code=1,
        timeout=False,
        parser_confidence=0.9,
        test_cases=[
            TestCaseResult(test_id="tests/test_demo.py::test_fix", status="passed"),
            TestCaseResult(test_id="tests/test_demo.py::test_old", status="failed"),
        ],
        fail_to_pass_tests=["tests/test_demo.py::test_fix"],
        pass_to_pass_tests=["tests/test_demo.py::test_old"],
        error_type=None,
    )

    assert result.accepted is False
    assert result.error_type == "regression_detected"


def test_acceptance_policy_low_confidence_is_error():
    result = apply_acceptance_policy(
        command="pytest -q",
        exit_code=0,
        timeout=False,
        parser_confidence=0.2,
        test_cases=[],
        fail_to_pass_tests=[],
        pass_to_pass_tests=[],
        error_type=None,
    )

    assert result.accepted is False
    assert result.error_type == "low_parser_confidence"


def test_acceptance_policy_falls_back_to_exit_code_without_declared_tests():
    result = apply_acceptance_policy(
        command="pytest -q",
        exit_code=0,
        timeout=False,
        parser_confidence=0.8,
        test_cases=[],
        fail_to_pass_tests=[],
        pass_to_pass_tests=[],
        error_type=None,
    )

    assert result.accepted is True
    assert result.accepted_fallback_reason == "overall_exit_code_zero"


def test_acceptance_policy_command_error_blocks_success_even_if_declared_tests_pass():
    result = apply_acceptance_policy(
        command="pytest -q",
        exit_code=2,
        timeout=False,
        parser_confidence=0.9,
        test_cases=[
            TestCaseResult(test_id="tests/test_demo.py::test_fix", status="passed"),
            TestCaseResult(test_id="tests/test_demo.py::test_old", status="passed"),
        ],
        fail_to_pass_tests=["tests/test_demo.py::test_fix"],
        pass_to_pass_tests=["tests/test_demo.py::test_old"],
        error_type="test_command_error",
        verifier_stage="final",
    )

    assert result.accepted is False
    assert result.error_type == "test_command_error"
    assert result.verifier_stage == "final"


def test_patch_apply_failure_builds_structured_verifier_result():
    result = build_error_verifier_result(
        command="git apply final.patch",
        error_type="patch_apply_failed",
        verifier_stage="final",
    )

    assert result.accepted is False
    assert result.error_type == "patch_apply_failed"
    assert result.verifier_stage == "final"
