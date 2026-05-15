import asyncio
import json
from math import ceil
from pathlib import Path
from time import perf_counter
from typing import Any

import pytest
from pydantic import ValidationError

from repo_harness.model_client.schemas import (
    ModelProviderOptions,
    ModelRequestContext,
    ProviderCredentialPolicy,
)
from repo_harness.rl import (
    FakeLLMGateway,
    LLMGatewayModelClientAdapter,
    LLMGatewayResponse,
    RepoHarnessEpisodeRequest,
    RepoHarnessRuntime,
)
from repo_harness.run_metadata import RunConfigFactsRef
from repo_harness.trajectory import (
    ArtifactRef,
    RecorderProfile,
    RunRecorder,
    read_jsonl,
    verify_artifact_manifest,
)


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
    model_call_id: str = "stage3-episode-success-turn-0",
    output_token_ids: list[int] | None = None,
    output_logprobs: list[float] | None | object = DEFAULT_LOGPROBS,
    duration_ms: int = 3,
) -> LLMGatewayResponse:
    tokens = [701, 702] if output_token_ids is None else output_token_ids
    if output_logprobs is DEFAULT_LOGPROBS and tokens:
        logprobs: list[float] | None = [-0.1 for _ in tokens]
    else:
        logprobs = output_logprobs  # type: ignore[assignment]
    return LLMGatewayResponse(
        route="verl",
        inference_backend="sglang",
        model_call_id=model_call_id,
        assistant_message={"role": "assistant", "content": "stage3 patched"},
        prompt_ids=[101, 102],
        output_token_ids=tokens,
        output_logprobs=logprobs,
        response_mask=[1 for _ in tokens],
        stop_reason="stop",
        duration_ms=duration_ms,
        usage={"input_tokens": 2, "output_tokens": len(tokens)},
    )


def test_stage3_recorder_profile_defaults_are_stable() -> None:
    full = RecorderProfile.for_run_mode("full_audit")
    fast = RecorderProfile.for_run_mode("training_fast")
    debug = RecorderProfile.for_run_mode("training_debug")

    assert full.mode == "full_audit"
    assert full.save_raw_provider_request is True
    assert full.save_raw_provider_response is True
    assert full.save_reasoning_trace is True
    assert fast.mode == "training_fast"
    assert fast.save_raw_provider_request is False
    assert fast.save_raw_provider_response is False
    assert fast.save_reasoning_trace is False
    assert fast.prepared_messages_retention == "keep_export_audit_compat"
    assert fast.raw_artifact_preview_chars == 0
    assert debug.mode == "training_debug"
    assert debug.raw_artifact_preview_chars > fast.raw_artifact_preview_chars

    assert RecorderProfile.model_validate(fast.model_dump(mode="json")) == fast


def test_stage3_training_fast_projects_raw_artifacts_and_keeps_manifest_valid(tmp_path: Path) -> None:
    full_dir = tmp_path / "full"
    fast_dir = tmp_path / "fast"

    full_refs = _write_retention_scenario(full_dir, "full_audit")
    fast_refs = _write_retention_scenario(fast_dir, "training_fast")

    full_bytes = _artifact_bytes(full_dir)
    fast_bytes = _artifact_bytes(fast_dir)

    assert verify_artifact_manifest(full_dir) == []
    assert verify_artifact_manifest(fast_dir) == []
    assert fast_bytes <= full_bytes * 0.5

    assert full_refs["raw_request"].kind == "raw_mock_provider_request"
    raw_request_payload = _read_artifact(fast_dir, fast_refs["raw_request"])
    assert fast_refs["raw_request"].kind == "artifact_projection_facts"
    assert raw_request_payload["schema_version"] == "repo_harness_artifact_retention_facts_v0"
    assert raw_request_payload["target_kind"] == "raw_mock_provider_request"
    assert raw_request_payload["run_mode"] == "training_fast"
    assert raw_request_payload["raw_payload_persisted"] is False
    assert raw_request_payload["projection_only"] is True
    assert raw_request_payload["original_size_bytes"] > 0
    assert len(raw_request_payload["original_sha256"]) == 64
    assert "RAW_PROVIDER_BODY_SHOULD_NOT_BE_PERSISTED" not in json.dumps(raw_request_payload)

    raw_response_payload = _read_artifact(fast_dir, fast_refs["raw_response"])
    assert fast_refs["raw_response"].kind == "artifact_projection_facts"
    assert raw_response_payload["schema_version"] == "repo_harness_artifact_retention_facts_v0"
    assert raw_response_payload["target_kind"] == "raw_mock_provider_response"
    assert raw_response_payload["run_mode"] == "training_fast"
    assert raw_response_payload["raw_payload_persisted"] is False
    assert raw_response_payload["projection_only"] is True
    assert raw_response_payload["original_size_bytes"] > raw_response_payload["preview_size_bytes"]
    assert "RAW_PROVIDER_BODY_SHOULD_NOT_BE_PERSISTED" not in json.dumps(raw_response_payload)

    reasoning_payload = _read_artifact(fast_dir, fast_refs["reasoning_trace"])
    assert fast_refs["reasoning_trace"].kind == "artifact_retention_facts"
    assert reasoning_payload["hash_only"] is True
    assert reasoning_payload["raw_payload_persisted"] is False
    assert "PRIVATE_REASONING_TRACE_SHOULD_NOT_BE_PERSISTED" not in json.dumps(reasoning_payload)

    prepared_payload = _read_artifact(fast_dir, fast_refs["prepared_messages"])
    assert prepared_payload["messages"][0]["content"].startswith("prepared message kept complete")
    assert prepared_payload["model_input_hash"] == "a" * 64

    events = read_jsonl(fast_dir / "events.jsonl")
    retention_events = [
        event for event in events if event["event_type"] == "artifact_retention_policy_applied"
    ]
    assert any(
        event["data"]["retention_policy"] == "training_fast_raw_artifact_projection"
        and event["data"]["target_kind"] == "raw_mock_provider_response"
        for event in retention_events
    )
    assert any(
        event["data"]["retention_policy"] == "training_fast_reasoning_trace_hash_only"
        and event["data"]["target_kind"] == "deepseek_provider_reasoning_trace"
        for event in retention_events
    )
    assert any(
        event["data"]["retention_policy"] == "training_fast_keep_export_audit_compat"
        and event["data"]["target_kind"] == "prepared_messages"
        and event["data"]["raw_payload_persisted"] is True
        for event in retention_events
    )


def test_stage3_training_fast_mapping_profile_uses_safe_defaults(tmp_path: Path) -> None:
    run_dir = tmp_path / "dict_profile_fast"
    with RunRecorder("dict_profile_fast", run_dir, recorder_profile={"mode": "training_fast"}) as recorder:
        ref = recorder.write_json_artifact(
            "raw_openai_provider_response",
            {"body": "DICT_PROFILE_RAW_PAYLOAD_SHOULD_NOT_PERSIST" + ("x" * 10_000)},
            {"redaction_status": "redacted", "retention_policy": "provider_raw_redacted"},
        )

    payload = _read_artifact(run_dir, ref)

    assert ref.kind == "artifact_projection_facts"
    assert payload["run_mode"] == "training_fast"
    assert payload["target_kind"] == "raw_openai_provider_response"
    assert payload["raw_payload_persisted"] is False
    assert payload["projection_only"] is True
    assert "DICT_PROFILE_RAW_PAYLOAD_SHOULD_NOT_PERSIST" not in json.dumps(payload)


def test_stage3_training_fast_rejects_conflicting_plaintext_profile(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="training_fast recorder profile must not save full raw"):
        RunRecorder(
            "unsafe_dict_profile_fast",
            tmp_path / "unsafe_dict_profile_fast",
            recorder_profile={"mode": "training_fast", "save_raw_provider_request": True},
        )


def test_stage3_training_debug_keeps_projection_preview_without_full_raw_payload(tmp_path: Path) -> None:
    debug_dir = tmp_path / "debug"
    with RunRecorder("debug", debug_dir, recorder_profile="training_debug") as recorder:
        ref = recorder.write_json_artifact(
            "raw_openai_provider_response",
            {"body": "DEBUG_PREVIEW_VISIBLE" + ("x" * 20_000)},
            {"redaction_status": "redacted", "retention_policy": "provider_raw_redacted"},
        )

    payload = _read_artifact(debug_dir, ref)

    assert ref.kind == "artifact_projection_facts"
    assert payload["run_mode"] == "training_debug"
    assert payload["raw_payload_persisted"] is False
    assert "DEBUG_PREVIEW_VISIBLE" in payload["preview"]
    assert len(payload["preview"]) < payload["original_size_bytes"]
    assert verify_artifact_manifest(debug_dir) == []


def test_stage3_training_debug_omits_preview_when_source_is_not_redacted(tmp_path: Path) -> None:
    debug_dir = tmp_path / "debug_unredacted"
    with RunRecorder("debug_unredacted", debug_dir, recorder_profile="training_debug") as recorder:
        ref = recorder.write_json_artifact(
            "raw_openai_provider_request",
            {"body": "UNREDACTED_SECRET_SHOULD_NOT_APPEAR" + ("x" * 20_000)},
            {"redaction_status": "not_scanned", "retention_policy": "provider_raw_unredacted"},
        )

    payload = _read_artifact(debug_dir, ref)

    assert ref.kind == "artifact_projection_facts"
    assert payload["preview"] is None
    assert payload["preview_chars"] == 0
    assert payload["preview_omitted_reason"] == "source_not_redacted"
    assert "UNREDACTED_SECRET_SHOULD_NOT_APPEAR" not in json.dumps(payload)
    assert verify_artifact_manifest(debug_dir) == []


def test_stage3_runtime_passes_recorder_profile_and_sets_timing_ratio() -> None:
    request = _episode_request(run_mode="training_fast")
    gateway = FakeLLMGateway([_gateway_response(duration_ms=3_000)])
    runtime = RepoHarnessRuntime()

    result = asyncio.run(runtime.run_episode(request, llm_gateway=gateway))

    assert gateway.requests
    policy = gateway.requests[0].recorder_policy
    assert policy["mode"] == "training_fast"
    assert policy["save_raw_provider_request"] is False
    assert policy["save_raw_provider_response"] is False
    assert policy["save_reasoning_trace"] is False
    timing = result.timing_summary
    assert timing is not None
    assert timing.timing_explained_ratio is not None
    assert timing.timing_explained_ratio >= 0.95
    assert timing.model_call_seconds < 1.0
    assert timing.model_call_seconds <= timing.rollout_wall_seconds
    explained = timing.agent_loop_seconds + timing.model_call_seconds + timing.cleanup_seconds
    expected_ratio = 1.0 if timing.rollout_wall_seconds <= 0 else min(1.0, explained / timing.rollout_wall_seconds)
    assert timing.timing_explained_ratio == expected_ratio


def test_stage3_gateway_model_client_adapter_passes_recorder_profile(tmp_path: Path) -> None:
    gateway = FakeLLMGateway(
        [
            _gateway_response(
                model_call_id="model-call-adapter",
                duration_ms=0,
            )
        ]
    )
    adapter = LLMGatewayModelClientAdapter(
        llm_gateway=gateway,
        episode_id="episode-adapter",
        route="mock",
    )
    with RunRecorder("adapter", tmp_path / "adapter", recorder_profile={"mode": "training_fast"}) as recorder:
        gateway_request = adapter.to_gateway_request(_model_request_context(), recorder=recorder)

    policy = gateway_request.recorder_policy

    assert policy["mode"] == "training_fast"
    assert policy["save_raw_provider_request"] is False
    assert policy["save_raw_provider_response"] is False
    assert policy["save_reasoning_trace"] is False
    assert policy["raw_artifact_retention"] == "projection"
    assert policy["raw_request_logging_policy"] == "disabled"
    assert policy["retry_policy"] == "none"


def test_stage3_fake_gateway_minimal_episode_smoke_p95_under_default_threshold() -> None:
    durations: list[float] = []

    async def run_one(index: int):
        request = _episode_request(
            episode_id=f"stage3-smoke-episode-{index}",
            run_id=f"stage3-smoke-run-{index}",
            run_mode="training_fast",
        )
        gateway = FakeLLMGateway([_gateway_response(model_call_id=f"stage3-smoke-call-{index}")])
        runtime = RepoHarnessRuntime()
        started = perf_counter()
        result = await runtime.run_episode(request, llm_gateway=gateway)
        durations.append(perf_counter() - started)
        return result

    async def run_all():
        return await asyncio.gather(*(run_one(index) for index in range(8)))

    results = asyncio.run(run_all())
    p95 = sorted(durations)[ceil(len(durations) * 0.95) - 1]

    assert p95 < 180.0
    assert all(result.status == "succeeded" for result in results)
    assert all(
        result.timing_summary is not None
        and result.timing_summary.timing_explained_ratio is not None
        and result.timing_summary.timing_explained_ratio >= 0.95
        for result in results
    )


def _write_retention_scenario(run_dir: Path, run_mode: str) -> dict[str, ArtifactRef]:
    profile = RecorderProfile.for_run_mode(run_mode)
    raw_body = "RAW_PROVIDER_BODY_SHOULD_NOT_BE_PERSISTED" + ("x" * 150_000)
    reasoning = "PRIVATE_REASONING_TRACE_SHOULD_NOT_BE_PERSISTED" + ("y" * 20_000)
    prepared = "prepared message kept complete for export audit compatibility"
    with RunRecorder(run_mode, run_dir, recorder_profile=profile) as recorder:
        prepared_ref = recorder.write_json_artifact(
            "prepared_messages",
            {
                "messages": [{"role": "user", "content": prepared}],
                "context_revision": 1,
                "model_input_hash": "a" * 64,
            },
            {"budget_policy": "preserve_json"},
        )
        request_ref = recorder.write_json_artifact(
            "raw_mock_provider_request",
            {
                "provider": "mock",
                "messages": [{"role": "user", "content": raw_body}],
                "authorization": "<REDACTED_CREDENTIAL>",
            },
            {"redaction_status": "redacted", "retention_policy": "provider_raw_redacted"},
        )
        response_ref = recorder.write_json_artifact(
            "raw_mock_provider_response",
            {
                "provider": "mock",
                "status": "ok",
                "assistant_message": {"role": "assistant", "content": raw_body},
            },
            {"redaction_status": "redacted", "retention_policy": "provider_raw_redacted"},
        )
        reasoning_ref = recorder.write_json_artifact(
            "deepseek_provider_reasoning_trace",
            {
                "provider": "deepseek",
                "reasoning_content": reasoning,
                "reasoning_trace_training_allowed": True,
            },
            {
                "redaction_status": "not_redacted_explicit_reasoning_trace_opt_in",
                "retention_policy": "provider_reasoning_trace_training_opt_in",
            },
        )
    return {
        "prepared_messages": prepared_ref,
        "raw_request": request_ref,
        "raw_response": response_ref,
        "reasoning_trace": reasoning_ref,
    }


def _artifact_bytes(run_dir: Path) -> int:
    manifest = json.loads((run_dir / "artifacts.json").read_text(encoding="utf-8"))
    return sum(int(ref["size_bytes"]) for ref in manifest["artifacts"])


def _read_artifact(run_dir: Path, ref: ArtifactRef) -> dict[str, Any]:
    return json.loads((run_dir / ref.relative_path).read_text(encoding="utf-8"))


def _artifact_ref(kind: str) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=kind,
        relative_path=f"artifacts/{kind}.json",
        kind=kind,
        sha256="0" * 64,
        size_bytes=0,
    )


def _model_request_context() -> ModelRequestContext:
    return ModelRequestContext(
        run_id="adapter-run",
        task_id="adapter-task",
        turn=0,
        model_call_id="model-call-adapter",
        prepared_messages=[{"role": "user", "content": "fix it"}],
        prepared_messages_ref=_artifact_ref("prepared_messages"),
        model_input_hash="a" * 64,
        context_revision=0,
        provider_message_format="chat",
        context_truncation_facts={},
        omitted_context_facts={},
        generation_config={"temperature": 0.0},
        provider_model_settings={},
        allowed_tool_definitions=[],
        tool_schema_snapshot_ref=_artifact_ref("tool_schema"),
        provider_options=ModelProviderOptions(provider="mock", model_id="mock-model"),
        scaffold_id="default",
        scaffold_phase="agent_loop",
        run_config_facts_ref=RunConfigFactsRef(sha256="b" * 64),
        budget_state={},
        request_timeout_seconds=30,
        raw_request_logging_policy="disabled",
        credential_policy=ProviderCredentialPolicy(),
        retry_policy="none",
    )
