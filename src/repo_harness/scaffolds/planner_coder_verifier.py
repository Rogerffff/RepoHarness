"""Planner/coder/verifier scaffold metadata."""

from __future__ import annotations

from repo_harness.evaluation.schemas import FeedbackTestsPassedPolicy, TestFeedbackPolicy
from repo_harness.scaffolds.schemas import ScaffoldDefinition
from repo_harness.tools import DEFAULT_TOOL_ORDER


class PlannerCoderVerifierScaffold(ScaffoldDefinition):
    pass


PHASE_SEQUENCE = ["planner", "coder", "verifier", "repair", "final"]

PHASE_ALLOWED_TOOLS = {
    "planner": ["list_files", "read_file", "grep", "git_diff"],
    "coder": ["list_files", "read_file", "grep", "edit_file", "create_file", "bash", "git_diff"],
    "verifier": ["read_file", "grep", "run_tests", "git_diff"],
    "repair": [
        "list_files",
        "read_file",
        "grep",
        "edit_file",
        "create_file",
        "bash",
        "run_tests",
        "git_diff",
    ],
    "final": [],
}

PHASE_PROMPTS = {
    "planner": "Plan the repository change. Inspect files as needed, but do not edit code.",
    "coder": "Apply the planned code change using editing tools and lightweight diagnostics.",
    "verifier": "Use configured test feedback if available. Treat it as feedback only, not final judgment.",
    "repair": "Repair issues found by feedback while respecting the same tool and test budgets.",
    "final": "Provide the final answer without requesting tools.",
}


def build_planner_coder_verifier_scaffold() -> PlannerCoderVerifierScaffold:
    return PlannerCoderVerifierScaffold(
        scaffold_id="planner_coder_verifier",
        scaffold_version="repo_harness_planner_coder_verifier_v0",
        prompt_fragment=(
            "Follow sequential phases inside one Agent Loop: planner, coder, verifier, repair, "
            "then final. These are strategy phases, not separate agents."
        ),
        allowed_tools_policy="repo_harness_planner_coder_verifier_phase_tools_v0",
        phase_transition_policy="repo_harness_planner_coder_verifier_linear_v0",
        default_stop_policy="repo_harness_planner_coder_verifier_require_final_v0",
        default_test_feedback_policy=TestFeedbackPolicy.oracle_hidden_feedback,
        default_feedback_tests_passed_policy=FeedbackTestsPassedPolicy.require_model_final,
        allows_final_answer_without_tool=True,
        allows_feedback_verifier_repair=True,
        allowed_tools=list(DEFAULT_TOOL_ORDER),
        initial_phase="planner",
        phase_sequence=list(PHASE_SEQUENCE),
        phase_allowed_tools={phase: list(tools) for phase, tools in PHASE_ALLOWED_TOOLS.items()},
        phase_prompt_fragments=dict(PHASE_PROMPTS),
    )
