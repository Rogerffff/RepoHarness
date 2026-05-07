"""Scaffold and runtime policy resolution."""

from __future__ import annotations

from repo_harness.config import RunConfig
from repo_harness.errors import ConfigError
from repo_harness.evaluation.schemas import (
    FeedbackTestsPassedPolicy,
    ResolvedFeedbackPolicyFacts,
    TestFeedbackPolicy,
)
from repo_harness.scaffolds.schemas import ScaffoldDefinition
from repo_harness.tasks import RunnableTask, TaskDefinition
from repo_harness.tools import ToolRegistry, build_tool


def resolve_feedback_policy(
    *,
    run_config: RunConfig,
    scaffold: ScaffoldDefinition,
    task: RunnableTask | TaskDefinition | None = None,
) -> ResolvedFeedbackPolicyFacts:
    runtime_test_policy = (
        TestFeedbackPolicy(run_config.runtime.test_feedback_policy)
        if run_config.runtime.test_feedback_policy is not None
        else None
    )
    runtime_passed_policy = (
        FeedbackTestsPassedPolicy(run_config.runtime.feedback_tests_passed_policy)
        if run_config.runtime.feedback_tests_passed_policy is not None
        else None
    )
    if (
        scaffold.scaffold_id == "single_shot_patch"
        and runtime_test_policy is not None
        and runtime_test_policy != TestFeedbackPolicy.disabled
    ):
        raise ConfigError(
            "single_shot_patch scaffold requires test_feedback_policy=disabled; "
            f"received {runtime_test_policy.value!r}."
        )
    swe_bench_like_final_only = _is_swe_bench_like_final_only(task)
    if (
        swe_bench_like_final_only
        and runtime_test_policy is not None
        and runtime_test_policy != TestFeedbackPolicy.disabled
    ):
        raise ConfigError(
            "SWE-Bench-like final-only task requires test_feedback_policy=disabled; "
            f"received {runtime_test_policy.value!r}."
        )
    if runtime_test_policy is None and swe_bench_like_final_only:
        resolved_test_policy = TestFeedbackPolicy.disabled
    else:
        resolved_test_policy = (
            runtime_test_policy
            or scaffold.default_test_feedback_policy
            or _default_test_feedback_policy_for_task(task)
        )
    if resolved_test_policy == TestFeedbackPolicy.disabled:
        resolved_passed_policy = "not_applicable"
    else:
        passed_policy = (
            runtime_passed_policy
            or scaffold.default_feedback_tests_passed_policy
            or _default_feedback_tests_passed_policy_for_provider(run_config.model.provider)
        )
        resolved_passed_policy = passed_policy.value
    return ResolvedFeedbackPolicyFacts(
        scaffold_default_test_feedback_policy=scaffold.default_test_feedback_policy,
        scaffold_default_feedback_tests_passed_policy=scaffold.default_feedback_tests_passed_policy,
        runtime_test_feedback_policy=runtime_test_policy,
        runtime_feedback_tests_passed_policy=runtime_passed_policy,
        resolved_test_feedback_policy=resolved_test_policy,
        resolved_feedback_tests_passed_policy=resolved_passed_policy,
        hidden_feedback_visible_to_model=resolved_test_policy == TestFeedbackPolicy.oracle_hidden_feedback,
        swe_bench_like_final_only=swe_bench_like_final_only,
    )


def resolve_allowed_tools(
    *,
    scaffold: ScaffoldDefinition,
    feedback_policy: ResolvedFeedbackPolicyFacts,
) -> list[str]:
    allowed = list(scaffold.allowed_tools)
    if feedback_policy.resolved_test_feedback_policy == TestFeedbackPolicy.disabled:
        allowed = [name for name in allowed if name != "run_tests"]
    return allowed


def resolve_allowed_tools_for_phase(
    *,
    scaffold: ScaffoldDefinition,
    feedback_policy: ResolvedFeedbackPolicyFacts,
    phase: str,
) -> list[str]:
    allowed = resolve_allowed_tools(scaffold=scaffold, feedback_policy=feedback_policy)
    phase_allowed = scaffold.allowed_tools_for_phase(phase)
    return [name for name in phase_allowed if name in allowed]


def tool_registry_for_allowed_tools(allowed_tools: list[str]) -> ToolRegistry:
    return ToolRegistry([build_tool(name) for name in allowed_tools])


def _default_test_feedback_policy_for_task(
    task: RunnableTask | TaskDefinition | None,
) -> TestFeedbackPolicy:
    if _is_swe_bench_like_final_only(task):
        return TestFeedbackPolicy.disabled
    return TestFeedbackPolicy.public_only


def _default_feedback_tests_passed_policy_for_provider(provider: str) -> FeedbackTestsPassedPolicy:
    if provider in {"replay", "fake"}:
        return FeedbackTestsPassedPolicy.stop_immediately
    return FeedbackTestsPassedPolicy.require_model_final


def _is_swe_bench_like_final_only(task: RunnableTask | TaskDefinition | None) -> bool:
    if task is None:
        return False
    metadata = getattr(task, "metadata", {}) or {}
    tags = getattr(task, "tags", []) or []
    return bool(
        metadata.get("swe_bench_like_final_only")
        or metadata.get("final_only")
        or "swe_bench_like_final_only" in tags
        or "final_only" in tags
    )
