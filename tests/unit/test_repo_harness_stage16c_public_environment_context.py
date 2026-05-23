from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from repo_harness.evaluation import ResolvedVerifierPlan
from repo_harness.tasks import load_task
from repo_harness.tasks.public_environment import (
    PublicTestEntry,
    build_public_environment_context,
)


ROOT = Path(__file__).resolve().parents[2]


def test_stage16c_public_environment_context_public_feedback_is_available() -> None:
    context = _build_context(test_feedback_policy="structured_public_feedback")

    assert context.public_test_entry.status == "available"
    assert context.public_test_entry.tool_name == "run_tests"
    assert context.public_test_entry.command_template_label == "structured_public_feedback"
    assert context.context_digest
    assert context.model_visible_payload()["public_test_entry"]["feedback_policy"] == (
        "structured_public_feedback"
    )


def test_stage16c_public_environment_context_disabled_fails_closed() -> None:
    context = _build_context(test_feedback_policy="disabled", allowed_tools=["read_file", "git_diff"])

    assert context.public_test_entry.status == "disabled"
    assert context.public_test_entry.tool_name is None
    assert context.public_test_entry.unavailable_reason == "test_feedback_policy_disabled"


def test_stage16c_public_environment_context_oracle_feedback_is_not_public() -> None:
    context = _build_context(test_feedback_policy="oracle_hidden_feedback")

    payload = context.model_visible_payload()
    serialized = json.dumps(payload, ensure_ascii=False)
    assert context.public_test_entry.status == "unavailable"
    assert context.public_test_entry.tool_name is None
    assert payload["public_test_entry"]["feedback_policy"] == "non_public_feedback_configured"
    assert "oracle_hidden_feedback" not in serialized
    assert "FAIL_TO_PASS" not in serialized
    assert "PASS_TO_PASS" not in serialized


def test_stage16c_public_environment_context_rejects_unsafe_command_template_label() -> None:
    with pytest.raises(ValidationError):
        PublicTestEntry(
            status="available",
            tool_name="run_tests",
            feedback_policy="structured_public_feedback",
            model_visible_summary="Use public feedback.",
            command_template_label="pytest -k FAIL_TO_PASS",
        )


def test_stage16c_public_environment_context_digest_is_stable() -> None:
    first = _build_context(test_feedback_policy="public_only")
    second = _build_context(test_feedback_policy="public_only")

    assert first.context_digest == second.context_digest


def _build_context(
    *,
    test_feedback_policy: str,
    allowed_tools: list[str] | None = None,
):
    loaded = load_task(ROOT / "tests/fixtures/tasks/task_001.yaml")
    plan = ResolvedVerifierPlan(
        verifier_config=loaded.verifier_config,
        initial_fail_to_pass_tests=[],
        initial_pass_to_pass_tests=[],
        flaky_tests=[],
        parser_confidence=1.0,
        resolved_verifier_plan_id="stage16c-plan",
    )
    return build_public_environment_context(
        task=loaded.runnable_task,
        resolved_verifier_plan=plan,
        test_feedback_policy=test_feedback_policy,
        allowed_tools=allowed_tools or ["read_file", "grep", "edit_file", "run_tests", "git_diff"],
    )
