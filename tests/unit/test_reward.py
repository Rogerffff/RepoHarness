from repo_harness.evaluation import build_metrics_record
from repo_harness.rl.reward_boundary import build_stage7_reward_boundary
from repo_harness.reward import compute_reward_metadata
from repo_harness.verifier import VerifierResult


def verifier_result(**updates):
    payload = {
        "parser_confidence": 0.9,
        "command": "pytest -q",
        "test_cases": [],
        "accepted": True,
        "pass_ratio": 1.0,
        "fail_to_pass": {"passed": 1, "total": 1},
        "pass_to_pass": {"passed": 1, "total": 1},
        "exit_code": 0,
        "timeout": False,
        "error_type": None,
    }
    payload.update(updates)
    return VerifierResult.model_validate(payload)


def test_reward_metadata_uses_final_verifier_and_patch_stats():
    reward = compute_reward_metadata(
        verifier_result(),
        patch_stats={"added_lines": 5, "removed_lines": 1},
        event_counts={"turn_count": 3, "tool_call_count": 4, "test_run_count": 1},
    )

    assert 0.0 <= reward.final_reward <= 1.0
    assert reward.invalid_for_training is False
    assert reward.sources["patch_added_lines"] == 5


def test_patch_hygiene_only_filtered_patch_is_invalid_for_training():
    reward = compute_reward_metadata(
        verifier_result(),
        patch_stats={
            "added_lines": 0,
            "removed_lines": 0,
            "patch_hygiene": {
                "status": "filtered_changes",
                "only_filtered_changes": True,
            },
        },
    )

    assert reward.invalid_for_training is True
    assert reward.invalid_reason == "patch_hygiene_only_filtered_changes"
    assert reward.final_reward == 0.0


def test_stage7_boundary_preserves_patch_hygiene_invalid_authority():
    boundary = build_stage7_reward_boundary(
        final_verifier=verifier_result(),
        reward_metadata_ref="rh://reward/unit",
        final_verifier_ref="rh://verifier/unit",
        patch_stats={
            "added_lines": 0,
            "removed_lines": 0,
            "patch_hygiene": {
                "status": "filtered_changes",
                "only_filtered_changes": True,
            },
        },
    )

    assert boundary.invalid_for_training is True
    assert boundary.status == "invalid"
    assert boundary.status_reason == "patch_hygiene_only_filtered_changes"


def test_reward_does_not_treat_missing_fail_to_pass_as_full_score():
    reward = compute_reward_metadata(
        verifier_result(fail_to_pass={"passed": 0, "total": 0}, accepted=True),
    )

    assert reward.components["fail_to_pass_score"] == 0.0
    assert reward.formula.startswith("0.6 * accepted_bonus")
    assert reward.final_reward <= 1.0


def test_reward_marks_timeout_invalid_for_training():
    reward = compute_reward_metadata(
        verifier_result(accepted=False, timeout=True, error_type="test_timeout"),
    )

    assert reward.invalid_for_training is True
    assert reward.invalid_reason == "test_timeout"
    assert reward.final_reward == 0.0
    assert reward.components["diagnostic_reward_before_invalid_clip"] > 0.0


def test_reward_marks_final_verifier_environment_error_invalid_for_training():
    reward = compute_reward_metadata(
        verifier_result(
            accepted=False,
            parser_confidence=0.95,
            fail_to_pass={"passed": 0, "total": 1},
            pass_to_pass={"passed": 1, "total": 1},
            error_type="final_verifier_environment_error",
        ),
    )

    assert reward.invalid_for_training is True
    assert reward.invalid_reason == "final_verifier_environment_error"
    assert reward.final_reward == 0.0


def test_reward_clips_not_executed_final_verifier_samples_to_zero():
    reward = compute_reward_metadata(
        verifier_result(
            accepted=False,
            parser_confidence=0.0,
            fail_to_pass={"passed": 0, "total": 0},
            pass_to_pass={"passed": 0, "total": 0},
            error_type="task_timeout_before_final_verifier",
        ),
    )

    assert reward.invalid_for_training is True
    assert reward.invalid_reason == "task_timeout_before_final_verifier"
    assert reward.final_reward == 0.0


def test_metrics_record_derives_final_status():
    metrics = build_metrics_record(
        final_verifier=verifier_result(accepted=False, timeout=True, error_type="test_timeout"),
        run_outcome="inconclusive",
        agent_stop_reason="final_answer",
        patch_stats={"added_lines": 1},
        loop_diagnostics_summary={"diagnostic_status": "no_progress_suspected"},
        loop_diagnostic_count=2,
    )

    assert metrics.final_verifier_status == "timeout"
    assert metrics.run_outcome == "inconclusive"
    assert metrics.patch_stats == {"added_lines": 1}
    assert metrics.interaction_efficiency["loop_diagnostics_summary"] == {
        "diagnostic_status": "no_progress_suspected"
    }
    assert metrics.interaction_efficiency["loop_diagnostic_count"] == 2


def test_metrics_record_can_mark_task_timeout_when_final_verifier_did_not_run():
    metrics = build_metrics_record(
        final_verifier=verifier_result(
            accepted=False,
            parser_confidence=0.0,
            error_type="task_timeout_before_final_verifier",
        ),
        run_outcome="inconclusive",
        final_verifier_status="not_executed",
        agent_stop_reason="task_timeout",
        timeout=True,
    )

    assert metrics.final_verifier_status == "not_executed"
    assert metrics.timeout is True
    assert metrics.interaction_efficiency["agent_stop_reason"] == "task_timeout"


def test_patch_apply_failure_is_counted_as_inconclusive_run_outcome():
    metrics = build_metrics_record(
        final_verifier=verifier_result(
            accepted=False,
            error_type="patch_apply_failed",
            parser_confidence=1.0,
        ),
        run_outcome="inconclusive",
        agent_stop_reason="final_answer",
    )

    assert metrics.final_verifier_status == "error"
    assert metrics.run_outcome == "inconclusive"
