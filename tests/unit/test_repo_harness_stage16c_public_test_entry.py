from __future__ import annotations

from repo_harness.tools import build_tool


def test_stage16c_run_tests_description_matches_public_feedback_boundary() -> None:
    tool = build_tool("run_tests")

    assert "public test feedback" in tool.model_visible_description
    assert "takes no arguments" in tool.model_visible_description
    assert "not the final verifier" in tool.model_visible_description
    assert "does not run arbitrary shell commands" in tool.model_visible_prompt
    assert "final scoring evidence" in tool.model_visible_prompt
    assert "FAIL_TO_PASS" not in tool.model_visible_prompt
    assert "PASS_TO_PASS" not in tool.model_visible_prompt
    assert "hidden_verifier" not in tool.model_visible_prompt


def test_stage16c_execute_bash_description_matches_stage16a_minimal_shell_boundary() -> None:
    tool = build_tool("execute_bash")

    text = tool.model_visible_description + " " + tool.model_visible_prompt
    assert "Stage 16A allowlist" in text
    assert "not a general shell" in text
    assert "command composition" in text
    assert "runtime-private paths" in text
    assert "public repository test commands are allowed" not in text
    assert "broader diagnostic tool than bash" not in text
    assert "multi-step public reproduction commands" not in text
