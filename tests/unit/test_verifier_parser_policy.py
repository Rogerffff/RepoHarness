from repo_harness.verifier.parser_policy import (
    VerifierParserPolicy,
    evaluate_verifier_output,
)
from repo_harness.evaluation.runner import _derive_baseline_status
from repo_harness.verifier.schemas import VerifierResult


def test_pytest_output_parser_policy_accepts_confident_output():
    decision = evaluate_verifier_output(
        stdout="1 passed in 0.01s",
        stderr="",
        exit_code=0,
        policy=VerifierParserPolicy(parser_id="pytest"),
    )

    assert decision.quality_gate_blocked is False
    assert decision.parser_confidence >= 0.5


def test_generic_exit_code_parser_handles_non_pytest_output():
    decision = evaluate_verifier_output(
        stdout="PASS: command line smoke",
        stderr="",
        exit_code=0,
        policy=VerifierParserPolicy(
            parser_id="generic_exit_code",
            parser_version="generic_exit_code_v0",
            supported_output_formats=["plain_text_exit_code"],
        ),
    )

    assert decision.quality_gate_blocked is False
    assert decision.error_type is None


def test_low_confidence_parser_blocks_quality_gate():
    decision = evaluate_verifier_output(
        stdout="",
        stderr="unexpected runner crash",
        exit_code=2,
        policy=VerifierParserPolicy(parser_id="pytest", low_confidence_threshold=0.9),
    )

    assert decision.quality_gate_blocked is True
    assert decision.failure_type == "environment_setup_failed"


def test_verifier_parser_policy_is_used_by_baseline_quality_gate():
    result = VerifierResult(
        verifier_stage="baseline",
        parser_id="pytest",
        parser_version="pytest_parser_v0",
        parser_confidence=0.2,
        command="pytest -q",
        test_cases=[],
        accepted=False,
        pass_ratio=0.0,
        exit_code=2,
        error_type=None,
    )

    status, reason = _derive_baseline_status(
        generated_file_count=0,
        verifier_results=[result, result],
        setup_result=None,
    )

    assert status == "invalid"
    assert reason == "low_parser_confidence"
