from repo_harness.evaluation import build_metrics_record
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


def test_metrics_record_derives_final_status():
    metrics = build_metrics_record(
        final_verifier=verifier_result(accepted=False, timeout=True, error_type="test_timeout"),
        run_outcome="inconclusive",
        agent_stop_reason="final_answer",
        patch_stats={"added_lines": 1},
    )

    assert metrics.final_verifier_status == "timeout"
    assert metrics.run_outcome == "inconclusive"
    assert metrics.patch_stats == {"added_lines": 1}


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
