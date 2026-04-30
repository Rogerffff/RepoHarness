"""Verifier parser 和 verifier result schema。"""

from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field

from repo_harness.schema_base import StrictBaseModel
from repo_harness.schema_versions import ACCEPTANCE_POLICY_VERSION, PYTEST_PARSER_VERSION
from repo_harness.trajectory import ArtifactRef


class VerifierParser(StrictBaseModel):
    schema_version: str = "repo_harness_verifier_parser_v0"
    parser_id: str = "pytest"
    parser_version: str = PYTEST_PARSER_VERSION
    supported_frameworks: list[str] = Field(default_factory=lambda: ["pytest"])
    parse_strategy: str = "pytest_text_v0"
    low_confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class TestCaseResult(StrictBaseModel):
    __test__: ClassVar[bool] = False

    schema_version: str = "repo_harness_test_case_result_v0"
    test_id: str
    status: Literal["passed", "failed", "skipped", "error", "timeout", "unknown"]
    duration_ms: int | None = Field(default=None, ge=0)
    failure_preview: str | None = None
    raw_output_ref: ArtifactRef | None = None


class VerifierResult(StrictBaseModel):
    schema_version: str = "repo_harness_verifier_result_v0"
    verifier_stage: Literal["baseline", "feedback", "final"] | None = None
    parser_id: str = "pytest"
    parser_version: str = PYTEST_PARSER_VERSION
    parser_confidence: float = Field(ge=0.0, le=1.0)
    command: str
    raw_output_ref: ArtifactRef | None = None
    test_cases: list[TestCaseResult] = Field(default_factory=list)
    accepted: bool
    acceptance_policy_version: str = ACCEPTANCE_POLICY_VERSION
    accepted_fallback_reason: str | None = None
    pass_ratio: float = Field(ge=0.0, le=1.0)
    fail_to_pass: dict[str, int] = Field(default_factory=lambda: {"passed": 0, "total": 0})
    pass_to_pass: dict[str, int] = Field(default_factory=lambda: {"passed": 0, "total": 0})
    exit_code: int | None = None
    timeout: bool = False
    error_type: str | None = None
