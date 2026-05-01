"""Single-shot patch scaffold metadata."""

from __future__ import annotations

from repo_harness.evaluation.schemas import FeedbackTestsPassedPolicy, TestFeedbackPolicy
from repo_harness.scaffolds.schemas import ScaffoldDefinition


class SingleShotPatchScaffold(ScaffoldDefinition):
    pass


def build_single_shot_patch_scaffold() -> SingleShotPatchScaffold:
    return SingleShotPatchScaffold(
        scaffold_id="single_shot_patch",
        scaffold_version="repo_harness_single_shot_patch_v0",
        prompt_fragment=(
            "Return exactly one unified diff patch for the repository. Do not request tools "
            "or intermediate test feedback."
        ),
        allowed_tools_policy="repo_harness_single_shot_patch_no_model_tools_v0",
        phase_transition_policy="repo_harness_single_shot_patch_single_phase_v0",
        default_stop_policy="repo_harness_single_shot_patch_apply_once_v0",
        default_test_feedback_policy=TestFeedbackPolicy.disabled,
        default_feedback_tests_passed_policy=FeedbackTestsPassedPolicy.stop_immediately,
        allows_final_answer_without_tool=False,
        allows_feedback_verifier_repair=False,
        allowed_tools=[],
        initial_phase="patch",
    )
