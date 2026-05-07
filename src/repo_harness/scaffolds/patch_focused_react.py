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
        scaffold_version="repo_harness_patch_focused_react_v8",
        prompt_fragment=(
            "Focus on a durable, minimal source patch. Use the allowed read, "
            "search, edit, test, and diff tools to understand the reported "
            "behavior, inspect only relevant code, update persistent project "
            "files, and review the final diff. Prefer the smallest change that "
            "follows existing local patterns and preserves surrounding behavior. "
            "Do not assume a task category or solution pattern before reading "
            "the code. Do not rely on shell commands or scratch diagnostic files "
            "for the final change; if temporary investigation was already "
            "performed, keep it out of the final diff. When available in "
            "allowed_tools, use run_tests only through the configured feedback "
            "policy and use git_diff before the final answer. If tests are "
            "disabled, rely on source inspection and remember that the final "
            "strict verifier will judge the patch after the agent stops."
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
