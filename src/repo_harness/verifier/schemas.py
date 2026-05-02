"""Verifier parser 和 verifier result schema。"""

from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field, model_validator

from repo_harness.schema_base import StrictBaseModel
from repo_harness.schema_versions import (
    ACCEPTANCE_POLICY_VERSION,
    PYTEST_PARSER_VERSION,
    SWEBENCH_LIKE_VERIFIER_PLAN_VERSION,
)
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


class SweBenchLikeVerifierPlan(StrictBaseModel):
    schema_version: str = SWEBENCH_LIKE_VERIFIER_PLAN_VERSION
    instance_id: str
    base_test_command: str
    fail_to_pass_command: str
    pass_to_pass_command: str
    selector_conversion_rule: str = "path_node_id_passthrough_or_bare_function_to_patch_file"
    selector_source: Literal["evaluator_only_manifest_ref"]
    selector_cache_ref: ArtifactRef
    fail_to_pass_selector_count: int = Field(default=1, ge=1)
    pass_to_pass_selector_count: int = Field(default=1, ge=1)
    selector_failure_strategy: str = "fail_closed_on_empty_or_unresolved_selector"
    verifier_patch_ref: ArtifactRef
    per_command_timeout_sec: int = Field(gt=0)
    parser_policy_version: str = PYTEST_PARSER_VERSION
    expected_artifact_refs: list[ArtifactRef] = Field(default_factory=list)
    hidden_visibility_policy: str = "evaluator_only"
    oracle_hidden_feedback_allowed: bool = False
    model_visible_test_command: str | None = None

    @model_validator(mode="after")
    def final_only_plan_does_not_expose_hidden_feedback(self) -> "SweBenchLikeVerifierPlan":
        if self.oracle_hidden_feedback_allowed:
            raise ValueError("SWE-Bench-like final-only verifier plan 不能允许 oracle_hidden_feedback。")
        if self.model_visible_test_command in {self.fail_to_pass_command, self.pass_to_pass_command}:
            raise ValueError("fail-to-pass / pass-to-pass command 不能进入模型可见上下文。")
        return self
