"""Scaffold definition schemas."""

from __future__ import annotations

from dataclasses import dataclass, field

from repo_harness.evaluation.schemas import FeedbackTestsPassedPolicy, TestFeedbackPolicy
from repo_harness.tools import DEFAULT_TOOL_ORDER


@dataclass(frozen=True)
class ScaffoldDefinition:
    scaffold_id: str
    scaffold_version: str
    prompt_fragment: str
    allowed_tools_policy: str
    phase_transition_policy: str
    default_stop_policy: str
    default_test_feedback_policy: TestFeedbackPolicy
    default_feedback_tests_passed_policy: FeedbackTestsPassedPolicy
    allows_final_answer_without_tool: bool
    allows_feedback_verifier_repair: bool
    allowed_tools: list[str] = field(default_factory=lambda: list(DEFAULT_TOOL_ORDER))
    initial_phase: str = "act"
    phase_sequence: list[str] = field(default_factory=list)
    phase_allowed_tools: dict[str, list[str]] = field(default_factory=dict)
    phase_prompt_fragments: dict[str, str] = field(default_factory=dict)

    def phases(self) -> list[str]:
        return list(self.phase_sequence or [self.initial_phase])

    def allowed_tools_for_phase(self, phase: str) -> list[str]:
        return list(self.phase_allowed_tools.get(phase, self.allowed_tools))

    def prompt_fragment_for_phase(self, phase: str) -> str | None:
        return self.phase_prompt_fragments.get(phase)

    def is_valid_final_answer(self, content: str | None, finish_reason: str | None) -> bool:
        if not self.allows_final_answer_without_tool or finish_reason != "stop":
            return False
        if content is None:
            return False
        normalized = content.strip()
        if not normalized:
            return False
        lowered = normalized.lower()
        if lowered.startswith(("{", "[", "```json")):
            return False
        invalid_markers = [
            "i cannot",
            "i can't",
            "cannot comply",
            "i am unable",
            "i'm unable",
            "context restored",
            "continue from previous",
            "please retry",
            "function_call",
            "tool_call",
        ]
        if any(marker in lowered for marker in invalid_markers):
            return False
        if normalized.count("{") > normalized.count("}") or normalized.count("[") > normalized.count("]"):
            return False
        return True
