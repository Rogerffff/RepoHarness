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
        scaffold_version="repo_harness_simple_react_v1",
        prompt_fragment=(
            "Iterate by requesting tools, reading observations, editing files, "
            "and using the configured test feedback policy. Aim for a durable "
            "repository change that addresses the task. Scratch files or temporary "
            "diagnostic scripts created only for investigation should be removed "
            "before the final diff. After identifying a likely fix, edit the "
            "relevant persistent project files; use glob_files or list_files for "
            "filename/module discovery and symbol_search for Python symbols when "
            "available in allowed_tools, and "
            "use structured file mutation tools such as write_file, apply_patch, "
            "delete_file, move_file, or mkdir only when they are enabled in "
            "allowed_tools and their schema requires the needed hash guard. "
            "use update_working_state briefly when exploration repeats. Use git_diff "
            "to review the final diff and run_tests for configured "
            "feedback."
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
