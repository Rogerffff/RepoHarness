from __future__ import annotations

from pathlib import Path

import pytest

from repo_harness.evaluation import ResolvedVerifierPlan
from repo_harness.tasks import load_task
from repo_harness.tasks.public_environment import (
    PublicEnvironmentVisibilityError,
    build_public_environment_context,
    project_public_environment_for_batch,
    validate_public_environment_model_visible_payload,
    write_public_environment_context_artifacts,
)
from repo_harness.trajectory import RunRecorder


ROOT = Path(__file__).resolve().parents[2]


def test_stage16c_batch_projection_excludes_full_prompt_block() -> None:
    context = _build_context()

    projection = project_public_environment_for_batch(context)

    assert set(projection) == {
        "repo_harness_public_environment_context_digest",
        "repo_harness_public_test_entry_status",
        "repo_harness_public_test_tool_strategy",
    }
    assert projection["repo_harness_public_environment_context_digest"] == context.context_digest
    assert "model_visible_prompt_block" not in projection


def test_stage16c_visibility_rejects_forbidden_public_environment_payload() -> None:
    with pytest.raises(PublicEnvironmentVisibilityError):
        validate_public_environment_model_visible_payload(
            {"model_visible_prompt_block": "Try FAIL_TO_PASS selector."}
        )

    with pytest.raises(PublicEnvironmentVisibilityError):
        validate_public_environment_model_visible_payload(
            {"model_visible_prompt_block": "Open /Users/roger/private.txt"}
        )


def test_stage16c_model_visible_payload_excludes_oracle_feedback_name() -> None:
    context = _build_context(test_feedback_policy="oracle_hidden_feedback")
    payload = context.model_visible_payload()

    assert payload["public_test_entry"]["feedback_policy"] == "non_public_feedback_configured"
    assert "oracle_hidden_feedback" not in str(payload)


def test_stage16c_recorder_artifacts_are_public_and_digest_bound(tmp_path: Path) -> None:
    context = _build_context()
    recorder = RunRecorder(run_id="stage16c", task_id="task", run_dir=tmp_path / "run")

    context_ref, prompt_ref = write_public_environment_context_artifacts(
        recorder=recorder,
        context=context,
    )

    context_text = (recorder.run_dir / context_ref.relative_path).read_text(encoding="utf-8")
    prompt_text = (recorder.run_dir / prompt_ref.relative_path).read_text(encoding="utf-8")
    assert context_ref.kind == "public_environment_context"
    assert prompt_ref.kind == "public_environment_prompt_block"
    assert context.context_digest in context_text
    assert context.model_visible_prompt_block == prompt_text
    for forbidden in ("FAIL_TO_PASS", "PASS_TO_PASS", "hidden_verifier", "/Users/"):
        assert forbidden not in context_text
        assert forbidden not in prompt_text


def _build_context(*, test_feedback_policy: str = "structured_public_feedback"):
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
        allowed_tools=["read_file", "grep", "edit_file", "run_tests", "git_diff"],
    )
