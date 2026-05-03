"""Patch-focused ReAct scaffold metadata."""

from __future__ import annotations

from repo_harness.evaluation.schemas import FeedbackTestsPassedPolicy, TestFeedbackPolicy
from repo_harness.scaffolds.schemas import ScaffoldDefinition

PATCH_FOCUSED_REACT_TOOL_ORDER = [
    "list_files",
    "read_file",
    "grep",
    "edit_file",
    "run_tests",
    "git_diff",
]


class PatchFocusedReactScaffold(ScaffoldDefinition):
    pass


def build_patch_focused_react_scaffold() -> PatchFocusedReactScaffold:
    return PatchFocusedReactScaffold(
        scaffold_id="patch_focused_react",
        scaffold_version="repo_harness_patch_focused_react_v0",
        prompt_fragment=(
            "Focus on a durable source patch. Use the allowed read, search, edit, "
            "test, and diff tools to inspect the repository and update persistent "
            "project files. Do not rely on shell commands or scratch diagnostic "
            "files for the final change. If temporary investigation was already "
            "performed, keep the final diff limited to the repository files needed "
            "for the task. When available in allowed_tools, use run_tests for "
            "configured feedback and git_diff to review the final diff before "
            "answering."
        ),
        allowed_tools_policy="repo_harness_patch_focused_react_allowed_tools_v0",
        phase_transition_policy="repo_harness_patch_focused_react_single_phase_v0",
        default_stop_policy="repo_harness_patch_focused_react_stop_policy_v0",
        default_test_feedback_policy=TestFeedbackPolicy.structured_public_feedback,
        default_feedback_tests_passed_policy=FeedbackTestsPassedPolicy.require_model_final,
        allows_final_answer_without_tool=True,
        allows_feedback_verifier_repair=True,
        allowed_tools=list(PATCH_FOCUSED_REACT_TOOL_ORDER),
        initial_phase="patch",
    )
