import asyncio
import json
import time
from pathlib import Path
from typing import Any

from repo_harness.rl import (
    FakeLLMGateway,
    LLMGatewayResponse,
    RepoHarnessEpisodeRequest,
    RepoHarnessRuntime,
    RepoHarnessRuntimeOptions,
    build_stage7_reward_boundary,
    map_stage7_verifier_status,
    validate_training_view_for_online_rl,
)
from repo_harness.reward import RewardMetadata, compute_reward_metadata
import repo_harness.rl.reward_boundary as reward_boundary_module
from repo_harness.verifier import VerifierJob, VerifierPoolOptions, VerifierResult, VerifierWorkerPool


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "repo_harness_verl"
DEFAULT_LOGPROBS = object()


def _load_json(name: str) -> dict[str, Any]:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def _episode_request(**updates: Any) -> RepoHarnessEpisodeRequest:
    payload = _load_json("canonical_episode_request.json")
    for key, value in updates.items():
        payload[key] = value
    return RepoHarnessEpisodeRequest.model_validate(payload)


def _gateway_response(
    *,
    output_token_ids: list[int] | None = None,
    output_logprobs: list[float] | None | object = DEFAULT_LOGPROBS,
) -> LLMGatewayResponse:
    tokens = [901, 902] if output_token_ids is None else output_token_ids
    if output_logprobs is DEFAULT_LOGPROBS and tokens:
        logprobs: list[float] | None = [-0.1 for _ in tokens]
    else:
        logprobs = output_logprobs  # type: ignore[assignment]
    return LLMGatewayResponse(
        route="verl",
        inference_backend="sglang",
        model_call_id="stage7-episode-success-turn-0",
        assistant_message={"role": "assistant", "content": "stage7 patched"},
        prompt_ids=[101, 102],
        output_token_ids=tokens,
        output_logprobs=logprobs,
        response_mask=[1 for _ in tokens],
        stop_reason="stop",
        duration_ms=5,
        usage={"input_tokens": 2, "output_tokens": len(tokens)},
    )


def _verifier_result(**updates: Any) -> VerifierResult:
    payload = {
        "verifier_stage": "final",
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


def test_stage7_reward_boundary_does_not_trust_old_reward_invalid_coverage() -> None:
    for error_type, expected_status in [
        ("test_command_error", "invalid_task"),
        ("dependency_error", "infrastructure_error"),
        ("verification_workspace_error", "infrastructure_error"),
    ]:
        verifier = _verifier_result(
            accepted=False,
            fail_to_pass={"passed": 0, "total": 1},
            error_type=error_type,
        )

        reward = compute_reward_metadata(verifier)
        status, reason = map_stage7_verifier_status(verifier)
        boundary = build_stage7_reward_boundary(
            final_verifier=verifier,
            reward_metadata_ref="rh://reward/stage7/metadata",
            final_verifier_ref="rh://verifier/stage7/final",
        )

        assert reward.invalid_for_training is True
        assert reward.invalid_reason == error_type
        assert status == expected_status
        assert reason == error_type
        assert boundary.invalid_for_training is True
        assert boundary.reward_score is None
        assert boundary.reward_summary.invalid_for_training is True


def test_stage7_reward_boundary_keeps_trusted_rejection_as_model_failure() -> None:
    verifier = _verifier_result(
        accepted=False,
        fail_to_pass={"passed": 0, "total": 1},
        pass_to_pass={"passed": 1, "total": 1},
        error_type="assertion_failure",
    )

    boundary = build_stage7_reward_boundary(
        final_verifier=verifier,
        reward_metadata_ref="rh://reward/stage7/metadata",
        final_verifier_ref="rh://verifier/stage7/final",
    )

    assert boundary.status == "failed"
    assert boundary.invalid_for_training is False
    assert boundary.reward_score is not None
    assert boundary.verifier_summary.status == "rejected"


def test_stage7_reward_boundary_owns_invalid_classification(monkeypatch) -> None:
    def legacy_invalid_reward(*args: Any, **kwargs: Any) -> RewardMetadata:
        return RewardMetadata(
            final_reward=0.0,
            formula="legacy invalid diagnostic",
            components={"diagnostic_reward_before_invalid_clip": 0.4},
            sources={},
            invalid_for_training=True,
            invalid_reason="legacy_invalid_reason",
        )

    monkeypatch.setattr(reward_boundary_module, "compute_reward_metadata", legacy_invalid_reward)
    verifier = _verifier_result(
        accepted=False,
        fail_to_pass={"passed": 0, "total": 1},
        pass_to_pass={"passed": 1, "total": 1},
        error_type="assertion_failure",
    )

    boundary = reward_boundary_module.build_stage7_reward_boundary(
        final_verifier=verifier,
        reward_metadata_ref="rh://reward/stage7/metadata",
        final_verifier_ref="rh://verifier/stage7/final",
    )

    assert boundary.status == "failed"
    assert boundary.status_reason == "assertion_failure"
    assert boundary.invalid_for_training is False
    assert boundary.reward_score == 0.4
    assert boundary.reward_metadata is not None
    assert boundary.reward_metadata.invalid_for_training is False
    assert boundary.reward_metadata.invalid_reason is None
    assert boundary.reward_metadata.sources["legacy_reward_invalid_reason"] == "legacy_invalid_reason"


def test_stage7_runtime_returns_reward_before_episode_result_and_records_pool_facts() -> None:
    request = _episode_request()
    pool = VerifierWorkerPool(VerifierPoolOptions(max_workers=1, max_pending_jobs=0))
    runtime = RepoHarnessRuntime(
        RepoHarnessRuntimeOptions(
            final_verifier_callable=_verifier_result,
            verifier_worker_pool=pool,
        )
    )
    try:
        result = asyncio.run(runtime.run_episode(request, llm_gateway=FakeLLMGateway([_gateway_response()])))
    finally:
        pool.close()

    assert result.status == "succeeded"
    assert result.reward is not None
    assert result.reward.score is not None
    assert result.training_view.reward_score == result.reward.score
    assert result.verifier_summary is not None
    assert result.verifier_summary.status == "accepted"
    assert result.timing_summary is not None
    assert result.timing_summary.verifier_call_count == 1
    assert result.timing_summary.final_verifier_seconds >= 0.0
    assert result.timing_summary.verifier_seconds == 0.0
    assert result.timing_summary.reward_compute_seconds >= 0.0
    assert result.resource_summary is not None
    assert result.resource_summary.verifier_worker_pool_id == "verifier-pool-local-v1"
    assert result.resource_summary.verifier_worker_id == "verifier-worker-0"
    assert "verifier_worker" in result.resource_summary.queue_wait_seconds_by_resource
    assert result.training_view.extra_fields["repo_harness_reward_metadata_ref"].startswith("rh://")
    assert result.training_view.extra_fields["repo_harness_final_verifier_ref"].startswith("rh://")
    validate_training_view_for_online_rl(result.training_view)


def test_stage7_runtime_maps_test_command_error_to_invalid_task() -> None:
    request = _episode_request()
    runtime = RepoHarnessRuntime(
        RepoHarnessRuntimeOptions(
            final_verifier_callable=lambda: _verifier_result(accepted=False, error_type="test_command_error"),
        )
    )

    result = asyncio.run(runtime.run_episode(request, llm_gateway=FakeLLMGateway([_gateway_response()])))

    assert result.status == "invalid_task"
    assert result.status_reason == "test_command_error"
    assert result.invalid_for_training is True
    assert result.invalid_for_online_rl is True
    assert result.training_view.reward_score is None
    assert result.reward is not None
    assert result.reward.invalid_for_training is True


def test_stage7_runtime_maps_workspace_and_dependency_errors_to_infrastructure_error() -> None:
    for error_type in ["dependency_error", "verification_workspace_error"]:
        request = _episode_request()
        runtime = RepoHarnessRuntime(
            RepoHarnessRuntimeOptions(
                final_verifier_callable=lambda error_type=error_type: _verifier_result(
                    accepted=False,
                    error_type=error_type,
                ),
            )
        )

        result = asyncio.run(runtime.run_episode(request, llm_gateway=FakeLLMGateway([_gateway_response()])))

        assert result.status == "infrastructure_error"
        assert result.status_reason == error_type
        assert result.invalid_for_training is True
        assert result.training_view.reward_score is None


def test_stage7_runtime_queue_timeout_is_structured_and_not_unbounded() -> None:
    request = _episode_request()
    pool = VerifierWorkerPool(
        VerifierPoolOptions(max_workers=1, max_pending_jobs=0, queue_timeout_seconds=0.01)
    )
    second_callable_count = 0

    def second_callable() -> VerifierResult:
        nonlocal second_callable_count
        second_callable_count += 1
        return _verifier_result()

    async def scenario():
        blocking_job = VerifierJob(
            job_id="blocking",
            run_id="stage7-run",
            episode_id="stage7-blocking",
            task_id="stage7-task",
            verifier_stage="final",
            callable=lambda: (time.sleep(0.08), _verifier_result())[1],
        )
        first = asyncio.create_task(pool.run(blocking_job))
        await asyncio.sleep(0.01)
        runtime = RepoHarnessRuntime(
            RepoHarnessRuntimeOptions(
                final_verifier_callable=second_callable,
                verifier_worker_pool=pool,
            )
        )
        result = await runtime.run_episode(request, llm_gateway=FakeLLMGateway([_gateway_response()]))
        await first
        return result

    try:
        result = asyncio.run(scenario())
    finally:
        pool.close()

    assert result.status == "timeout"
    assert result.status_reason == "queue_timeout"
    assert result.invalid_for_training is True
    assert result.training_view.reward_score is None
    assert result.resource_summary is not None
    assert result.resource_summary.verifier_worker_pool_id == "verifier-pool-local-v1"
    assert second_callable_count == 0


def test_stage7_runtime_visibility_excludes_hidden_reward_and_verifier_details() -> None:
    request = _episode_request()
    runtime = RepoHarnessRuntime(
        RepoHarnessRuntimeOptions(final_verifier_callable=_verifier_result)
    )

    result = asyncio.run(runtime.run_episode(request, llm_gateway=FakeLLMGateway([_gateway_response()])))

    serialized_extra = json.dumps(result.training_view.extra_fields, sort_keys=True)
    assert "components" not in serialized_extra
    assert "accepted_label" not in serialized_extra
    assert "fail_to_pass" not in serialized_extra
    assert "/Users/" not in serialized_extra
