"""Simple ReAct scaffold metadata."""

from __future__ import annotations

from repo_harness.evaluation.schemas import FeedbackTestsPassedPolicy, TestFeedbackPolicy
from repo_harness.scaffolds.schemas import ScaffoldDefinition
from repo_harness.tools import DEFAULT_TOOL_ORDER


class SimpleReactScaffold(ScaffoldDefinition):
    pass


def build_simple_react_scaffold() -> SimpleReactScaffold:
    return SimpleReactScaffold(
        scaffold_id="simple_react",
        scaffold_version="repo_harness_simple_react_v0",
        prompt_fragment=(
            "Iterate by requesting tools, reading observations, editing files, "
            "and using the configured test feedback policy."
        ),
        allowed_tools_policy="repo_harness_simple_react_allowed_tools_v0",
        phase_transition_policy="repo_harness_simple_react_single_phase_v0",
        default_stop_policy="repo_harness_simple_react_stop_policy_v0",
        default_test_feedback_policy=TestFeedbackPolicy.oracle_hidden_feedback,
        default_feedback_tests_passed_policy=FeedbackTestsPassedPolicy.stop_immediately,
        allows_final_answer_without_tool=True,
        allows_feedback_verifier_repair=True,
        allowed_tools=list(DEFAULT_TOOL_ORDER),
        initial_phase="act",
    )


def build_scaffold(scaffold_id: str) -> ScaffoldDefinition:
    if scaffold_id != "simple_react":
        from repo_harness.errors import ConfigError

        raise ConfigError(f"Unsupported scaffold_id={scaffold_id!r}. Supported scaffolds: simple_react.")
    return build_simple_react_scaffold()
