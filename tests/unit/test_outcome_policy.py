from repo_harness.evaluation.outcome_policy import derive_run_outcome
from repo_harness.evaluation.metrics import derive_final_verifier_status
from repo_harness.verifier import build_error_verifier_result


def test_outcome_policy_prioritizes_baseline_gate():
    assert (
        derive_run_outcome(
            baseline_status="invalid",
            final_verifier_status="accepted",
            final_verifier_ran=False,
        )
        == "invalid_task"
    )
    assert (
        derive_run_outcome(
            baseline_status="flaky",
            final_verifier_status="accepted",
            final_verifier_ran=False,
        )
        == "flaky_task"
    )


def test_outcome_policy_maps_final_verifier_status():
    assert derive_run_outcome(final_verifier_status="accepted") == "success"
    assert derive_run_outcome(final_verifier_status="failed") == "failed"
    assert derive_run_outcome(final_verifier_status="rejected") == "failed"
    assert derive_run_outcome(final_verifier_status="not_executed") == "inconclusive"
    assert derive_run_outcome(final_verifier_status="timeout") == "inconclusive"
    assert derive_run_outcome(final_verifier_status="error") == "inconclusive"


def test_outcome_policy_manual_stop_without_final_verifier_is_interrupted():
    assert (
        derive_run_outcome(agent_stop_reason="manual_stop", final_verifier_ran=False)
        == "interrupted"
    )


def test_patch_replay_failure_is_final_verifier_error():
    verifier = build_error_verifier_result(
        command="strict_patch_replay",
        error_type="patch_apply_failed",
        verifier_stage="final",
    )

    assert derive_final_verifier_status(verifier) == "error"
    assert derive_run_outcome(final_verifier_status="error") == "inconclusive"
