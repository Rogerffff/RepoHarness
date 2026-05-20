from __future__ import annotations

from repo_harness_verl.stage15_inventory import (
    build_stage15_partial_rollout_interface_inventory,
    build_stage15_partial_rollout_patch_plan,
    build_stage15_partial_rollout_risk_matrix,
)


def test_stage15_0_patch_plan_rejects_no_patch_claim_when_abort_is_invisible() -> None:
    inventory = build_stage15_partial_rollout_interface_inventory()

    plan = build_stage15_partial_rollout_patch_plan(inventory)

    assert plan.reference_verl_patch_or_wrapper_required is True
    assert plan.no_patch_required_claim_allowed is False
    assert plan.recommended_patch_id in plan.recommended_patch_ids
    assert "stage15_fully_async_rollouter_source_gate_wrapper" in plan.recommended_patch_ids
    assert "abort_aborted_not_visible_to_repo_harness_agent_loop" in plan.no_patch_rejection_reasons
    assert "fully_async_trainer_does_not_filter_repo_harness_diagnostic_samples" in (
        plan.no_patch_rejection_reasons
    )


def test_stage15_0_patch_plan_lists_required_candidate_boundaries() -> None:
    inventory = build_stage15_partial_rollout_interface_inventory()

    plan = build_stage15_partial_rollout_patch_plan(inventory)
    candidates = {candidate.patch_id: candidate for candidate in plan.candidates}

    assert plan.recommended_patch_id == "stage15_agent_loop_owned_partial_side_channel"
    assert "stage15_no_checkpoint_engine_abort_boundary_wrapper" in candidates
    assert "stage15_agent_loop_owned_partial_side_channel" in candidates
    assert "stage15_fully_async_rollouter_source_gate_wrapper" in candidates
    assert "stage15_fully_llm_client_stop_reason_probe" in candidates
    assert (
        candidates["stage15_no_checkpoint_engine_abort_boundary_wrapper"].kind
        == "no_patch_required"
    )
    assert candidates["stage15_fully_async_rollouter_source_gate_wrapper"].patch_manifest_required is True
    assert candidates["stage15_agent_loop_owned_partial_side_channel"].patch_manifest_required is False
    assert "valid_completed_sample_queue" in candidates[
        "stage15_fully_async_rollouter_source_gate_wrapper"
    ].enables


def test_stage15_0_risk_matrix_covers_partial_rollout_acceptance_risks() -> None:
    matrix = build_stage15_partial_rollout_risk_matrix()
    risk_ids = {risk.risk_id for risk in matrix.risks}

    expected = {
        "stage15_risk_invisible_abort",
        "stage15_risk_checkpoint_engine_abort_not_repo_boundary",
        "stage15_risk_trainer_required_samples_polluted",
        "stage15_risk_cross_actor_resume",
        "stage15_risk_duplicate_resume_consumption",
        "stage15_risk_stale_resumed_sample",
        "stage15_risk_visibility_or_path_leak",
        "stage15_risk_reference_verl_patch_drift",
    }
    assert expected.issubset(risk_ids)
    assert all(risk.severity in {"P1", "P2"} for risk in matrix.risks)
