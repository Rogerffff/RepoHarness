import asyncio
import json
import threading
from pathlib import Path
from typing import Any

import pytest

from repo_harness.model_client.schemas import ModelCallEvent, ModelMessage, ModelRequestContext, ModelResponse
from repo_harness.rl import (
    LLMGatewayRequest,
    ModelClientLLMGateway,
    RepoHarnessEpisodeRequest,
    RepoHarnessRuntime,
)
from repo_harness.schema_base import stable_hash
from repo_harness.trajectory import RunRecorder


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "repo_harness_verl"


def _load_json(name: str) -> dict[str, Any]:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def _episode_request(**updates: Any) -> RepoHarnessEpisodeRequest:
    payload = _load_json("canonical_episode_request.json")
    payload["llm_gateway_route"] = "openai"
    payload["inference_backend"] = None
    for key, value in updates.items():
        payload[key] = value
    return RepoHarnessEpisodeRequest.model_validate(payload)


def _gateway_request(*, model_call_id: str = "stage5-provider-call-0") -> LLMGatewayRequest:
    return LLMGatewayRequest(
        route="openai",
        inference_backend=None,
        run_id="stage5-provider-run",
        task_id="stage5-provider-task",
        episode_id="stage5-provider-episode",
        model_call_id=model_call_id,
        turn=0,
        context_revision=0,
        messages=[{"role": "user", "content": "please patch the bug"}],
        tools=[{"name": "edit_file", "description": "edit a file"}],
        sampling_params={"temperature": 0.0, "max_output_tokens": 32},
        provider_options={"provider": "openai", "model_id": "stage5-provider-model"},
        tokenizer_policy={"provider_request_token_estimate": 4},
        budget_state={"max_turns": 1},
        recorder_policy={"mode": "training_fast"},
        visibility_policy={"provider_message_format": "stage5_test_chat"},
        tracing={"scaffold_id": "stage5", "scaffold_phase": "provider_gateway"},
    )


class KeywordOnlySpyModelClient:
    def __init__(
        self,
        *,
        content: str = "provider text only response",
        model_error_type: str | None = None,
    ) -> None:
        self.content = content
        self.model_error_type = model_error_type
        self.requests: list[ModelRequestContext] = []
        self.thread_names: list[str] = []

    def generate(self, *, request: ModelRequestContext, recorder: RunRecorder) -> ModelResponse:
        self.requests.append(request)
        self.thread_names.append(threading.current_thread().name)
        raw_request_ref = recorder.write_json_artifact(
            "raw_openai_provider_request",
            {"model_call_id": request.model_call_id, "messages": request.prepared_messages},
            {"redaction_status": "redacted", "retention_policy": "provider_raw_redacted"},
        )
        raw_response_ref = recorder.write_json_artifact(
            "raw_openai_provider_response",
            {"content": self.content, "authorization": "<redacted>"},
            {"redaction_status": "redacted", "retention_policy": "provider_raw_redacted"},
        )
        event = ModelCallEvent(
            model_call_id=request.model_call_id,
            provider=request.provider_options.provider,
            model_id=request.provider_options.model_id,
            provider_request_id="provider-request-1",
            context_revision=request.context_revision,
            prepared_messages_ref=request.prepared_messages_ref,
            model_input_hash=request.model_input_hash,
            provider_message_format=request.provider_message_format,
            tool_schema_hash=stable_hash(request.allowed_tool_definitions),
            input_tokens=4,
            output_tokens=6,
            duration_ms=7,
            request_timeout_seconds=request.request_timeout_seconds,
            request_timeout_policy_facts=request.request_timeout_policy_facts,
            model_error_type=self.model_error_type,
        )
        return ModelResponse(
            assistant_message=ModelMessage(role="assistant", content=self.content),
            raw_provider_request_ref=raw_request_ref,
            raw_provider_response_ref=raw_response_ref,
            token_usage={"input_tokens": 4, "output_tokens": 6},
            finish_reason="error" if self.model_error_type else "stop",
            model_error_type=self.model_error_type,
            provider_request_id="provider-request-1",
            model_call_event=event,
        )


def test_stage5_model_client_gateway_uses_keyword_call_and_marks_provider_tokens_offline(
    tmp_path: Path,
) -> None:
    client = KeywordOnlySpyModelClient()
    gateway = ModelClientLLMGateway(
        model_client=client,
        run_dir_root=tmp_path,
        max_workers=1,
    )

    response = asyncio.run(gateway.generate_turn(_gateway_request()))

    assert client.requests
    assert client.requests[0].model_call_id == "stage5-provider-call-0"
    assert client.thread_names
    assert client.thread_names[0] != threading.current_thread().name
    assert response.route == "openai"
    assert response.output_token_ids
    assert response.output_logprobs is None
    assert response.response_mask == [1 for _ in response.output_token_ids]
    assert response.token_source == "provider_text_retokenized_debug_only"
    assert response.raw_request_ref and response.raw_request_ref.startswith("rh://")
    assert response.raw_response_ref and response.raw_response_ref.startswith("rh://")
    assert response.model_call_event_ref and response.model_call_event_ref.startswith("rh://")
    assert response.extra_fields["repo_harness_model_client_bridge"] == "legacy_model_client"

    run_dir = tmp_path / "stage5-provider-run" / "stage5-provider-call-0"
    manifest = json.loads((run_dir / "artifacts.json").read_text(encoding="utf-8"))
    projection_payloads = [
        json.loads((run_dir / item["relative_path"]).read_text(encoding="utf-8"))
        for item in manifest["artifacts"]
        if item["kind"] == "artifact_projection_facts"
    ]
    assert any(
        payload["target_kind"] == "raw_openai_provider_response"
        and payload["raw_payload_persisted"] is False
        for payload in projection_payloads
    )
    assert "provider text only response" not in json.dumps(projection_payloads)


def test_stage5_model_client_gateway_replaces_runtime_placeholder_model_id(
    tmp_path: Path,
) -> None:
    client = KeywordOnlySpyModelClient()
    gateway = ModelClientLLMGateway(
        model_client=client,
        run_dir_root=tmp_path,
        max_workers=1,
        default_model_id="stage5-default-model",
    )
    request = _gateway_request()
    request = request.model_copy(
        update={
            "provider_options": {
                "provider": "openai",
                "model_id": "repo-harness-llm-gateway",
            }
        }
    )

    asyncio.run(gateway.generate_turn(request))

    assert client.requests[0].provider_options.model_id == "stage5-default-model"


def test_stage5_model_client_gateway_merges_default_provider_specific_options(
    tmp_path: Path,
) -> None:
    client = KeywordOnlySpyModelClient()
    gateway = ModelClientLLMGateway(
        model_client=client,
        run_dir_root=tmp_path,
        max_workers=1,
        default_provider_specific_options={"mock_scenario": "public_feedback"},
    )
    request = _gateway_request()
    request = request.model_copy(
        update={
            "provider_options": {
                "provider": "openai",
                "model_id": "stage5-provider-model",
                "provider_specific_options": {"temperature_probe": "kept"},
            }
        }
    )

    asyncio.run(gateway.generate_turn(request))

    assert client.requests[0].provider_options.provider_specific_options == {
        "mock_scenario": "public_feedback",
        "temperature_probe": "kept",
    }


def test_stage5_provider_gateway_response_stays_invalid_for_online_rl_in_runtime(
    tmp_path: Path,
) -> None:
    client = KeywordOnlySpyModelClient()
    gateway = ModelClientLLMGateway(
        model_client=client,
        run_dir_root=tmp_path,
        max_workers=1,
    )
    request = _episode_request()
    runtime = RepoHarnessRuntime()

    result = asyncio.run(runtime.run_episode(request, llm_gateway=gateway))

    assert result.status == "succeeded"
    assert result.invalid_for_training is False
    assert result.invalid_for_online_rl is True
    assert result.status_reason == "provider_route_invalid_for_online_rl"
    assert result.training_view.response_ids
    assert result.training_view.response_logprobs is None
    assert result.generation_records[0].gateway_route == "openai"


def test_stage5_gateway_error_maps_to_timeout_status(tmp_path: Path) -> None:
    client = KeywordOnlySpyModelClient(model_error_type="provider_timeout")
    gateway = ModelClientLLMGateway(
        model_client=client,
        run_dir_root=tmp_path,
        max_workers=1,
    )
    request = _episode_request()
    runtime = RepoHarnessRuntime()

    result = asyncio.run(runtime.run_episode(request, llm_gateway=gateway))

    assert result.status == "timeout"
    assert result.status_reason == "provider_timeout"
    assert result.invalid_for_training is True
    assert result.invalid_for_online_rl is True
    assert result.training_view.reward_score is None


def test_stage5_gateway_error_maps_to_infrastructure_error(tmp_path: Path) -> None:
    client = KeywordOnlySpyModelClient(model_error_type="replay_alignment_error")
    gateway = ModelClientLLMGateway(
        model_client=client,
        run_dir_root=tmp_path,
        max_workers=1,
    )
    request = _episode_request()
    runtime = RepoHarnessRuntime()

    result = asyncio.run(runtime.run_episode(request, llm_gateway=gateway))

    assert result.status == "infrastructure_error"
    assert result.status_reason == "replay_alignment_error"
    assert result.invalid_for_training is True
    assert result.invalid_for_online_rl is True


def test_stage5_model_client_gateway_can_be_closed(tmp_path: Path) -> None:
    client = KeywordOnlySpyModelClient()
    gateway = ModelClientLLMGateway(
        model_client=client,
        run_dir_root=tmp_path,
        max_workers=1,
    )

    gateway.close()

    assert gateway.is_closed is True


def test_stage5_model_client_gateway_rejects_generate_after_close(tmp_path: Path) -> None:
    client = KeywordOnlySpyModelClient()
    gateway = ModelClientLLMGateway(
        model_client=client,
        run_dir_root=tmp_path,
        max_workers=1,
    )

    gateway.close()

    with pytest.raises(RuntimeError, match="ModelClientLLMGateway is closed"):
        asyncio.run(gateway.generate_turn(_gateway_request()))


def test_stage5_model_client_gateway_aclose_marks_gateway_closed(tmp_path: Path) -> None:
    client = KeywordOnlySpyModelClient()
    gateway = ModelClientLLMGateway(
        model_client=client,
        run_dir_root=tmp_path,
        max_workers=1,
    )

    asyncio.run(gateway.aclose())

    assert gateway.is_closed is True
