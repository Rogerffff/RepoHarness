from __future__ import annotations

import pytest

from repo_harness.evaluation.stage16d_healthcheck import (
    CANONICAL_EMPTY_PATCH_REF,
    DISPOSITION_DIAGNOSTIC,
    DISPOSITION_DIAGNOSTIC_UNTIL_REVIEWED,
    DISPOSITION_ENV_OR_ORACLE_INVALID,
    DISPOSITION_TRAINABLE,
    GOLD_FAILED,
    GOLD_PASSED,
    NOOP_EXPECTED_UNRESOLVED,
    NOOP_UNEXPECTEDLY_RESOLVED,
    Stage16DHealthcheckInputResult,
    Stage16DProxyResult,
    Stage16DSeedRecord,
    classify_stage16d_seed,
)


def test_stage16d_concrete_gold_pass_noop_unresolved_is_trainable_with_locked_image() -> None:
    record = classify_stage16d_seed(
        _seed(),
        gold_result=_result("task-1", "gold_patch", True),
        noop_result=_result("task-1", "noop_patch", False),
    )

    assert record.gold_healthcheck_status == GOLD_PASSED
    assert record.noop_healthcheck_status == NOOP_EXPECTED_UNRESOLVED
    assert record.noop_patch_ref == CANONICAL_EMPTY_PATCH_REF
    assert record.noop_patch_ref_status == "generated_canonical_empty_patch"
    assert record.healthcheck_training_disposition == DISPOSITION_TRAINABLE
    assert record.invalid_for_training is False
    assert record.invalid_for_online_rl is False


def test_stage16d_gold_failure_invalidates_environment_or_oracle() -> None:
    record = classify_stage16d_seed(
        _seed(),
        gold_result=_result("task-1", "gold_patch", False),
        noop_result=_result("task-1", "noop_patch", False),
    )

    assert record.gold_healthcheck_status == GOLD_FAILED
    assert record.healthcheck_training_disposition == DISPOSITION_ENV_OR_ORACLE_INVALID
    assert record.invalid_for_training is True


def test_stage16d_noop_resolved_invalidates_environment_or_oracle() -> None:
    record = classify_stage16d_seed(
        _seed(),
        gold_result=_result("task-1", "gold_patch", True),
        noop_result=_result("task-1", "noop_patch", True),
    )

    assert record.noop_healthcheck_status == NOOP_UNEXPECTEDLY_RESOLVED
    assert record.healthcheck_training_disposition == DISPOSITION_ENV_OR_ORACLE_INVALID


def test_stage16d_proxy_official_disagreement_is_diagnostic_until_reviewed() -> None:
    record = classify_stage16d_seed(
        _seed(),
        gold_result=_result("task-1", "gold_patch", True),
        noop_result=_result("task-1", "noop_patch", False),
        proxy_result=Stage16DProxyResult(
            instance_id="task-1",
            internal_final_verifier_status="accepted",
            official_verifier_status="rejected",
            final_verifier_boundary_ref="runtime-private:final-verifier:" + "a" * 64,
            final_verifier_boundary_available=True,
            internal_final_verifier_reran=True,
        ),
    )

    assert record.proxy_official_disagreement is True
    assert record.healthcheck_training_disposition == DISPOSITION_DIAGNOSTIC_UNTIL_REVIEWED
    assert record.invalid_for_training is True


def test_stage16d_aggregate_seed_is_never_trainable() -> None:
    record = classify_stage16d_seed(
        Stage16DSeedRecord(
            instance_id="repr20-gold-smoke-aggregate",
            seed_role="gold_patch_smoke_pass_candidate",
            source_dataset="swebench_verified",
            candidate_instance_status="aggregate_not_directly_runnable",
        )
    )

    assert record.seed_resolution_status == "aggregate_not_directly_runnable"
    assert record.healthcheck_training_disposition == DISPOSITION_DIAGNOSTIC
    assert record.not_run_reason == "aggregate_seed_not_directly_runnable"


def test_stage16d_rejects_non_opaque_runtime_private_ref() -> None:
    with pytest.raises(ValueError, match="runtime-private"):
        Stage16DProxyResult(
            instance_id="task-1",
            final_verifier_boundary_ref="/tmp/raw-final-verifier.json",
        )


def _seed() -> Stage16DSeedRecord:
    return Stage16DSeedRecord(
        instance_id="task-1",
        seed_role="positive_path_official_resolved",
        source_dataset="swebench_verified",
        candidate_instance_status="concrete_not_healthchecked_in_stage16d_0",
        gold_patch_source="dataset_gold_patch_or_not_available",
        noop_patch_source="not_available",
    )


def _result(instance_id: str, check_kind: str, resolved: bool) -> Stage16DHealthcheckInputResult:
    return Stage16DHealthcheckInputResult(
        instance_id=instance_id,
        check_kind=check_kind,  # type: ignore[arg-type]
        official_resolved=resolved,
        official_harness_execution_status="executed",
        official_image_source="swebench:latest",
        official_image_digest="sha256:" + "1" * 64,
        official_image_digest_locked=True,
        official_result_ref="runtime-private:official-result:" + "2" * 64,
        official_result_sha256="2" * 64,
    )
