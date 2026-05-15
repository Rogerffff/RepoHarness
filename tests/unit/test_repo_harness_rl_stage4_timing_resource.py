import asyncio
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from repo_harness.rl import (
    FakeLLMGateway,
    LLMGatewayRequest,
    LLMGatewayResponse,
    RepoHarnessEpisodeRequest,
    RepoHarnessRuntime,
    RepoHarnessRuntimeOptions,
)
from repo_harness.rl.timing import (
    ResourceSummary,
    TimingSummary,
    build_timing_summary,
    summarize_timing_from_run_dir,
)
from repo_harness.trajectory import RunRecorder, TrajectoryEvent


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
    route: str = "verl",
    inference_backend: str | None = "sglang",
    model_call_id: str = "stage4-episode-success-turn-0",
    output_token_ids: list[int] | None = None,
    output_logprobs: list[float] | None | object = DEFAULT_LOGPROBS,
    duration_ms: int = 3000,
) -> LLMGatewayResponse:
    tokens = [801, 802] if output_token_ids is None else output_token_ids
    if output_logprobs is DEFAULT_LOGPROBS and tokens:
        logprobs: list[float] | None = [-0.1 for _ in tokens]
    else:
        logprobs = output_logprobs  # type: ignore[assignment]
    return LLMGatewayResponse(
        route=route,  # type: ignore[arg-type]
        inference_backend=inference_backend,  # type: ignore[arg-type]
        model_call_id=model_call_id,
        assistant_message={"role": "assistant", "content": "stage4 patched"},
        prompt_ids=[101, 102],
        output_token_ids=tokens,
        output_logprobs=logprobs,
        response_mask=[1 for _ in tokens],
        stop_reason="stop",
        duration_ms=duration_ms,
        usage={"input_tokens": 2, "output_tokens": len(tokens)},
    )


class ErrorGateway:
    async def generate_turn(self, request: LLMGatewayRequest) -> LLMGatewayResponse:
        raise RuntimeError(f"gateway failed for {request.model_call_id}")


class SlowGateway:
    async def generate_turn(self, request: LLMGatewayRequest) -> LLMGatewayResponse:
        await asyncio.sleep(60)
        return _gateway_response()


def _assert_budget_matches_timing(result: Any) -> None:
    assert result.timing_summary is not None
    assert result.resource_summary is not None
    assert result.budget_consumption is not None
    assert result.budget_consumption.used_wall_seconds == result.timing_summary.rollout_wall_seconds
    assert result.budget_consumption.used_model_call_seconds == result.timing_summary.model_call_seconds
    assert result.budget_consumption.used_artifact_bytes == result.timing_summary.artifact_bytes_written


def test_stage4_timing_summary_uses_exclusive_buckets_without_provider_double_counting() -> None:
    summary = build_timing_summary(
        rollout_wall_seconds=10.0,
        model_call_seconds=3.0,
        tool_seconds=2.0,
        context_prepare_seconds=1.0,
        agent_loop_seconds=1.0,
        cleanup_seconds=1.0,
        provider_reported_model_call_seconds=30.0,
    )

    assert summary.timing_bucket_policy == "exclusive_runtime_facade_v1"
    assert summary.provider_reported_model_call_seconds == 30.0
    assert summary.timing_explained_ratio == pytest.approx(0.8)
    assert summary.timing_unattributed_seconds == pytest.approx(2.0)
    assert any("unattributed" in item for item in summary.timing_diagnostics)


def test_stage4_timing_summary_schema_requires_diagnostics_for_low_explained_ratio() -> None:
    with pytest.raises(ValidationError, match="timing_unattributed_seconds"):
        TimingSummary(
            rollout_wall_seconds=10.0,
            model_call_seconds=1.0,
            timing_explained_ratio=0.1,
        )

    with pytest.raises(ValidationError, match="timing_diagnostics"):
        TimingSummary(
            rollout_wall_seconds=10.0,
            model_call_seconds=1.0,
            timing_explained_ratio=0.1,
            timing_unattributed_seconds=9.0,
        )

    parsed = TimingSummary(
        rollout_wall_seconds=10.0,
        model_call_seconds=1.0,
        timing_explained_ratio=0.1,
        timing_unattributed_seconds=9.0,
        timing_diagnostics=["timing_unattributed_seconds=9.000000 left unexplained"],
    )

    assert parsed.timing_explained_ratio == 0.1


def test_stage4_runtime_success_writes_budget_consistent_timing_and_opaque_refs() -> None:
    request = _episode_request()
    gateway = FakeLLMGateway([_gateway_response(duration_ms=3000)])
    runtime = RepoHarnessRuntime()

    result = asyncio.run(runtime.run_episode(request, llm_gateway=gateway))

    assert result.status == "succeeded"
    _assert_budget_matches_timing(result)
    assert result.timing_summary is not None
    assert result.timing_summary.timing_explained_ratio is not None
    assert result.timing_summary.timing_explained_ratio >= 0.95
    assert result.timing_summary.provider_reported_model_call_seconds == 3.0
    assert result.timing_summary.model_call_seconds < 1.0
    assert result.training_view.extra_fields["repo_harness_timing_summary_ref"] == (
        f"rh://audit/{request.episode_id}/timing-summary"
    )
    assert result.training_view.extra_fields["repo_harness_resource_summary_ref"] == (
        f"rh://audit/{request.episode_id}/resource-summary"
    )
    assert result.audit_ref.important_artifact_refs["timing_summary"] == (
        f"rh://audit/{request.episode_id}/timing-summary"
    )
    assert result.audit_ref.important_artifact_refs["resource_summary"] == (
        f"rh://audit/{request.episode_id}/resource-summary"
    )
    assert result.audit_ref.timing_summary_path is None
    assert result.audit_ref.resource_summary_path is None
    serialized_extra = json.dumps(result.training_view.extra_fields, sort_keys=True)
    assert "/Users/" not in serialized_extra


def test_stage4_runtime_failed_result_keeps_timing_budget_consistency() -> None:
    request = _episode_request()
    gateway = FakeLLMGateway([_gateway_response()])
    runtime = RepoHarnessRuntime(
        RepoHarnessRuntimeOptions(minimal_final_verifier_status="rejected")
    )

    result = asyncio.run(runtime.run_episode(request, llm_gateway=gateway))

    assert result.status == "failed"
    _assert_budget_matches_timing(result)
    assert result.training_view.extra_fields["repo_harness_status"] == "failed"


def test_stage4_terminal_statuses_keep_timing_and_resource_summaries() -> None:
    invalid_request = _episode_request()
    invalid_runtime = RepoHarnessRuntime(RepoHarnessRuntimeOptions(require_resolved_task_path=True))
    invalid_result = asyncio.run(
        invalid_runtime.run_episode(invalid_request, llm_gateway=FakeLLMGateway([_gateway_response()]))
    )

    error_result = asyncio.run(
        RepoHarnessRuntime().run_episode(_episode_request(), llm_gateway=ErrorGateway())
    )

    timeout_request = _episode_request(
        budgets={**_load_json("canonical_episode_request.json")["budgets"], "max_wall_seconds": 0.01}
    )
    timeout_result = asyncio.run(
        RepoHarnessRuntime().run_episode(timeout_request, llm_gateway=SlowGateway())
    )

    assert invalid_result.status == "invalid_task"
    assert error_result.status == "infrastructure_error"
    assert timeout_result.status == "timeout"
    for result in [invalid_result, error_result, timeout_result]:
        _assert_budget_matches_timing(result)
        assert result.timing_summary is not None
        assert result.timing_summary.timing_explained_ratio is not None
        assert result.timing_summary.timing_explained_ratio >= 0.95
        assert result.resource_summary is not None
        assert result.resource_summary.cleanup_status in {"not_required", "ok", "failed"}


def test_stage4_resource_summary_rejects_absolute_runtime_paths() -> None:
    with pytest.raises(ValidationError, match="run_dir"):
        ResourceSummary(run_dir="/Users/roger/private/run")

    with pytest.raises(ValidationError, match="workspace_path"):
        ResourceSummary(workspace_path="/Users/roger/private/workspace")


def test_stage4_run_directory_summarizer_reads_events_and_artifact_manifest(tmp_path: Path) -> None:
    run_dir = tmp_path / "stage4_run"
    with RunRecorder("stage4_run", run_dir, task_id="task_stage4") as recorder:
        recorder.append_event(
            TrajectoryEvent(
                event_id=recorder.next_event_id("model"),
                timestamp="2026-05-15T00:00:00Z",
                run_id="stage4_run",
                task_id="task_stage4",
                event_type="model_call_completed",
                duration_ms=1200,
            )
        )
        recorder.append_event(
            TrajectoryEvent(
                event_id=recorder.next_event_id("context"),
                timestamp="2026-05-15T00:00:01Z",
                run_id="stage4_run",
                task_id="task_stage4",
                event_type="context_prepare_completed",
                duration_ms=300,
            )
        )
        recorder.append_event(
            TrajectoryEvent(
                event_id=recorder.next_event_id("tool"),
                timestamp="2026-05-15T00:00:02Z",
                run_id="stage4_run",
                task_id="task_stage4",
                event_type="tool_call_completed",
                duration_ms=400,
            )
        )
        recorder.append_event(
            TrajectoryEvent(
                event_id=recorder.next_event_id("verifier"),
                timestamp="2026-05-15T00:00:03Z",
                run_id="stage4_run",
                task_id="task_stage4",
                event_type="final_verifier_completed",
                duration_ms=500,
            )
        )
        recorder.write_json_artifact("timing_fixture", {"ok": True})

    summary = summarize_timing_from_run_dir(run_dir, rollout_wall_seconds=3.0)

    assert summary.model_call_seconds == pytest.approx(1.2)
    assert summary.context_prepare_seconds == pytest.approx(0.3)
    assert summary.tool_seconds == pytest.approx(0.4)
    assert summary.final_verifier_seconds == pytest.approx(0.5)
    assert summary.model_call_count == 1
    assert summary.tool_call_count == 1
    assert summary.verifier_call_count == 1
    assert summary.artifact_count == 1
    assert summary.artifact_bytes_written > 0
    assert summary.timing_explained_ratio == pytest.approx(0.8)
