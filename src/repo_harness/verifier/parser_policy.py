"""Verifier parser policy checks used before expanding the task set."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from repo_harness.schema_base import StrictBaseModel
from repo_harness.schema_versions import PYTEST_PARSER_VERSION
from repo_harness.verifier.pytest_parser import PytestTextParser

VERIFIER_PARSER_POLICY_VERSION = "repo_harness_verifier_parser_policy_v0"


class VerifierParserPolicy(StrictBaseModel):
    schema_version: str = "repo_harness_verifier_parser_policy_v0"
    policy_version: str = VERIFIER_PARSER_POLICY_VERSION
    parser_id: Literal["pytest", "generic_exit_code"] = "pytest"
    parser_version: str = PYTEST_PARSER_VERSION
    supported_output_formats: list[str] = Field(default_factory=lambda: ["pytest_text"])
    low_confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    block_low_confidence: bool = True
    low_confidence_failure_type: str = "environment_setup_failed"


class ParserPolicyDecision(StrictBaseModel):
    schema_version: str = "repo_harness_parser_policy_decision_v0"
    policy_version: str = VERIFIER_PARSER_POLICY_VERSION
    parser_id: str
    parser_version: str
    parser_confidence: float = Field(ge=0.0, le=1.0)
    error_type: str | None = None
    quality_gate_blocked: bool
    failure_type: str | None = None
    reason: str


def evaluate_verifier_output(
    *,
    stdout: str,
    stderr: str,
    exit_code: int | None,
    timeout: bool = False,
    policy: VerifierParserPolicy | None = None,
) -> ParserPolicyDecision:
    resolved_policy = policy or VerifierParserPolicy()
    if resolved_policy.parser_id == "pytest":
        parser = PytestTextParser()
        confidence = parser.parser_confidence(stdout, stderr, exit_code)
        error_type = parser.error_type(stdout, stderr, exit_code, timeout)
        parser_version = parser.parser_version
    elif resolved_policy.parser_id == "generic_exit_code":
        confidence = _generic_confidence(stdout, stderr, exit_code)
        error_type = _generic_error_type(exit_code, timeout)
        parser_version = resolved_policy.parser_version
    else:
        confidence = 0.0
        error_type = "unsupported_parser"
        parser_version = resolved_policy.parser_version

    blocked = bool(
        resolved_policy.block_low_confidence
        and confidence < resolved_policy.low_confidence_threshold
    )
    return ParserPolicyDecision(
        parser_id=resolved_policy.parser_id,
        parser_version=parser_version,
        parser_confidence=confidence,
        error_type=error_type,
        quality_gate_blocked=blocked,
        failure_type=resolved_policy.low_confidence_failure_type if blocked else None,
        reason=(
            "parser confidence is below quality gate threshold"
            if blocked
            else "parser confidence satisfies quality gate threshold"
        ),
    )


def _generic_confidence(stdout: str, stderr: str, exit_code: int | None) -> float:
    combined = f"{stdout}\n{stderr}".lower()
    if "pass" in combined or "fail" in combined or "error" in combined:
        return 0.75
    if exit_code in {0, 1}:
        return 0.6
    if exit_code is None:
        return 0.2
    return 0.4


def _generic_error_type(exit_code: int | None, timeout: bool) -> str | None:
    if timeout:
        return "test_timeout"
    if exit_code == 0:
        return None
    if exit_code is None:
        return "test_command_error"
    return "assertion_failure" if exit_code == 1 else "test_command_error"
