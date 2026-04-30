"""Simple ReAct scaffold metadata."""

from __future__ import annotations

from dataclasses import dataclass, field

from repo_harness.tools import DEFAULT_TOOL_ORDER


@dataclass(frozen=True)
class SimpleReactScaffold:
    scaffold_id: str = "simple_react"
    scaffold_version: str = "repo_harness_simple_react_v0"
    allowed_tools: list[str] = field(default_factory=lambda: list(DEFAULT_TOOL_ORDER))
    prompt_fragment: str = (
        "Iterate by requesting tools, reading observations, editing files, and verifying with run_tests."
    )
    allows_final_answer_without_tool: bool = True

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


def build_scaffold(scaffold_id: str) -> SimpleReactScaffold:
    if scaffold_id != "simple_react":
        raise ValueError(f"Unsupported scaffold for v1: {scaffold_id}")
    return SimpleReactScaffold()
