"""LLMGateway adapters for existing RepoHarness model clients."""

from __future__ import annotations

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from repo_harness.model_client.protocol import ModelClient
from repo_harness.model_client.schemas import (
    ModelProviderOptions,
    ModelRequestContext,
    ModelResponse,
    ProviderCredentialPolicy,
)
from repo_harness.run_metadata import RunConfigFactsRef
from repo_harness.schema_base import stable_hash
from repo_harness.trajectory import ArtifactRef, RecorderProfile, RunRecorder

from .gateway import LLMGatewayRequest, LLMGatewayResponse
from .visibility import GatewayRoute, validate_route_name


DEFAULT_MODEL_CLIENT_TIMEOUT_SECONDS = 60.0
PROVIDER_DEBUG_TOKEN_SOURCE = "provider_text_retokenized_debug_only"
PROVIDER_UNAVAILABLE_TOKEN_SOURCE = "provider_unavailable"


@dataclass(frozen=True)
class ModelClientLLMGatewayOptions:
    """Runtime-only options for wrapping a synchronous ModelClient."""

    run_dir_root: str | Path
    max_workers: int = 1
    default_model_id: str = "repo-harness-model-client-gateway"
    default_timeout_seconds: float = DEFAULT_MODEL_CLIENT_TIMEOUT_SECONDS

    def __post_init__(self) -> None:
        if self.max_workers < 1:
            raise ValueError("max_workers must be >= 1")
        if self.default_timeout_seconds <= 0:
            raise ValueError("default_timeout_seconds must be > 0")


class ModelClientLLMGateway:
    """Wrap an existing synchronous ModelClient behind the async LLMGateway contract."""

    def __init__(
        self,
        *,
        model_client: ModelClient,
        run_dir_root: str | Path,
        max_workers: int = 1,
        default_model_id: str = "repo-harness-model-client-gateway",
        default_timeout_seconds: float = DEFAULT_MODEL_CLIENT_TIMEOUT_SECONDS,
    ) -> None:
        self.model_client = model_client
        self.options = ModelClientLLMGatewayOptions(
            run_dir_root=run_dir_root,
            max_workers=max_workers,
            default_model_id=default_model_id,
            default_timeout_seconds=default_timeout_seconds,
        )
        self._semaphore = asyncio.Semaphore(max_workers)
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="repo-harness-llm-gateway",
        )
        self._closed = False

    @property
    def is_closed(self) -> bool:
        return self._closed

    def close(self) -> None:
        if not self._closed:
            self._executor.shutdown(wait=True, cancel_futures=True)
            self._closed = True

    async def aclose(self) -> None:
        self.close()

    def __enter__(self) -> "ModelClientLLMGateway":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    async def generate_turn(self, request: LLMGatewayRequest) -> LLMGatewayResponse:
        if self._closed:
            raise RuntimeError("ModelClientLLMGateway is closed")
        parsed_request = LLMGatewayRequest.model_validate(request)
        async with self._semaphore:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(self._executor, self._generate_turn_sync, parsed_request)

    def _generate_turn_sync(self, request: LLMGatewayRequest) -> LLMGatewayResponse:
        run_dir = Path(self.options.run_dir_root) / request.run_id / request.model_call_id
        recorder_profile = _recorder_profile_from_policy(request.recorder_policy)
        with RunRecorder(
            request.run_id,
            run_dir,
            task_id=request.task_id,
            recorder_profile=recorder_profile,
        ) as recorder:
            model_request = self.to_model_request_context(request, recorder=recorder)
            model_response = self.model_client.generate(request=model_request, recorder=recorder)
            return self.to_gateway_response(request, model_response, recorder=recorder)

    def to_model_request_context(
        self,
        request: LLMGatewayRequest,
        *,
        recorder: RunRecorder,
    ) -> ModelRequestContext:
        prepared_messages_ref = recorder.write_json_artifact(
            "prepared_messages",
            {"messages": request.messages},
            {"redaction_status": "not_needed", "retention_policy": "keep"},
        )
        tool_schema_snapshot_ref = recorder.write_json_artifact(
            "tool_schema_snapshot",
            {"tools": request.tools},
            {"redaction_status": "not_needed", "retention_policy": "keep"},
        )
        provider_options = _provider_options_from_request(
            request,
            default_model_id=self.options.default_model_id,
        )
        request_timeout_seconds = request.timeout_seconds or self.options.default_timeout_seconds
        model_input_hash = stable_hash(request.messages)
        return ModelRequestContext(
            run_id=request.run_id,
            task_id=request.task_id,
            turn=request.turn,
            model_call_id=request.model_call_id,
            prepared_messages=request.messages,
            prepared_messages_ref=prepared_messages_ref,
            model_input_hash=model_input_hash,
            context_revision=request.context_revision,
            provider_message_format=str(
                request.visibility_policy.get("provider_message_format", "llm_gateway_model_client_v1")
            ),
            context_truncation_facts=dict(request.visibility_policy.get("context_truncation_facts", {})),
            omitted_context_facts=dict(request.visibility_policy.get("omitted_context_facts", {})),
            generation_config=dict(request.sampling_params),
            provider_model_settings=dict(request.provider_options.get("provider_model_settings", {})),
            allowed_tool_definitions=list(request.tools),
            tool_choice=request.provider_options.get("tool_choice"),
            tool_schema_snapshot_ref=tool_schema_snapshot_ref,
            provider_options=provider_options,
            scaffold_id=str(request.tracing.get("scaffold_id", "llm_gateway")),
            scaffold_phase=str(request.tracing.get("scaffold_phase", "generate_turn")),
            run_config_facts_ref=RunConfigFactsRef(
                sha256=stable_hash(
                    {
                        "route": request.route,
                        "inference_backend": request.inference_backend,
                        "provider_options": provider_options.model_dump(mode="json"),
                        "sampling_params": request.sampling_params,
                    }
                )
            ),
            budget_state=dict(request.budget_state),
            request_timeout_seconds=request_timeout_seconds,
            request_timeout_policy_facts=dict(request.budget_state.get("request_timeout_policy_facts", {})),
            raw_request_logging_policy=str(request.recorder_policy.get("raw_request_logging_policy", "redacted")),
            credential_policy=provider_options.credential_policy,
            retry_policy=str(request.recorder_policy.get("retry_policy", "none")),
            provider_request_projection_hash=stable_hash(
                {
                    "messages": request.messages,
                    "tools": request.tools,
                    "provider_options": provider_options.model_dump(mode="json"),
                }
            ),
            provider_request_token_estimate=int(
                request.tokenizer_policy.get("provider_request_token_estimate", 0) or 0
            ),
            provider_request_token_estimate_breakdown=dict(
                request.tokenizer_policy.get("provider_request_token_estimate_breakdown", {})
            ),
            context_budget_facts=dict(request.tokenizer_policy.get("context_budget_facts", {})),
        )

    def to_gateway_response(
        self,
        request: LLMGatewayRequest,
        response: ModelResponse,
        *,
        recorder: RunRecorder,
    ) -> LLMGatewayResponse:
        assistant_message = response.assistant_message.model_dump(mode="json")
        tool_calls = [call.model_dump(mode="json") for call in response.tool_calls]
        output_text = _assistant_debug_text(assistant_message, tool_calls)
        output_token_ids = _debug_token_ids(output_text)
        token_source = PROVIDER_DEBUG_TOKEN_SOURCE if output_token_ids else PROVIDER_UNAVAILABLE_TOKEN_SOURCE
        model_call_event_ref = None
        duration_ms = None
        if response.model_call_event is not None:
            event_ref = recorder.write_json_artifact(
                "model_call_event",
                response.model_call_event.model_dump(mode="json"),
                {"redaction_status": "not_needed", "retention_policy": "keep"},
            )
            model_call_event_ref = _opaque_artifact_ref(request, event_ref)
            duration_ms = response.model_call_event.duration_ms
        return LLMGatewayResponse(
            route=request.route,
            inference_backend=request.inference_backend,
            model_call_id=request.model_call_id,
            assistant_message=assistant_message,
            tool_calls=tool_calls,
            prompt_ids=_debug_token_ids(json.dumps(request.messages, sort_keys=True, ensure_ascii=False)),
            output_token_ids=output_token_ids,
            output_logprobs=None,
            response_mask=[1 for _ in output_token_ids],
            stop_reason=response.finish_reason,
            token_source=token_source,
            usage=dict(response.token_usage),
            provider_request_id=response.provider_request_id,
            raw_request_ref=_optional_opaque_artifact_ref(request, response.raw_provider_request_ref),
            raw_response_ref=_optional_opaque_artifact_ref(request, response.raw_provider_response_ref),
            model_call_event_ref=model_call_event_ref,
            duration_ms=duration_ms,
            error=(
                {"model_error_type": response.model_error_type}
                if response.model_error_type is not None
                else None
            ),
            extra_fields={
                "repo_harness_model_client_bridge": "legacy_model_client",
                "token_provenance": token_source,
                "formal_online_rl_eligible": False,
            },
        )


class ProviderLLMGateway(ModelClientLLMGateway):
    """Provider route wrapper for OpenAI / DeepSeek style ModelClient implementations."""


class ReplayLLMGateway(ModelClientLLMGateway):
    """Replay route wrapper for existing ReplayModelClient implementations."""


class MockLLMGateway:
    """Deterministic route-level mock gateway with token/logprob facts for tests."""

    def __init__(self) -> None:
        self.requests: list[LLMGatewayRequest] = []

    async def generate_turn(self, request: LLMGatewayRequest) -> LLMGatewayResponse:
        parsed_request = LLMGatewayRequest.model_validate(request)
        self.requests.append(parsed_request)
        output_token_ids = [900 + parsed_request.turn, 901 + len(parsed_request.messages)]
        return LLMGatewayResponse(
            route=parsed_request.route,
            inference_backend=parsed_request.inference_backend,
            model_call_id=parsed_request.model_call_id,
            assistant_message={"role": "assistant", "content": f"mock route response {parsed_request.turn}"},
            tool_calls=[],
            prompt_ids=_debug_token_ids(json.dumps(parsed_request.messages, sort_keys=True, ensure_ascii=False)),
            output_token_ids=output_token_ids,
            output_logprobs=[-0.01 for _ in output_token_ids],
            response_mask=[1 for _ in output_token_ids],
            stop_reason="stop",
            token_source="mock_gateway",
            usage={"input_tokens": len(parsed_request.messages), "output_tokens": len(output_token_ids)},
            duration_ms=0,
            extra_fields={"repo_harness_gateway_kind": "mock"},
        )


class UnsupportedRouteLLMGateway:
    """Structured placeholder for routes that are reserved for later stages."""

    def __init__(self, route: str) -> None:
        self.route = validate_route_name(route)
        self.requests: list[LLMGatewayRequest] = []

    async def generate_turn(self, request: LLMGatewayRequest) -> LLMGatewayResponse:
        parsed_request = LLMGatewayRequest.model_validate(request)
        self.requests.append(parsed_request)
        return LLMGatewayResponse(
            route=parsed_request.route,
            inference_backend=parsed_request.inference_backend,
            model_call_id=parsed_request.model_call_id,
            assistant_message={
                "role": "assistant",
                "content": f"route={self.route} is not implemented in Stage 5",
            },
            tool_calls=[],
            prompt_ids=_debug_token_ids(json.dumps(parsed_request.messages, sort_keys=True, ensure_ascii=False)),
            output_token_ids=[],
            output_logprobs=None,
            response_mask=[],
            stop_reason="unsupported_route",
            token_source=PROVIDER_UNAVAILABLE_TOKEN_SOURCE,
            usage={"input_tokens": len(parsed_request.messages), "output_tokens": 0},
            duration_ms=0,
            error={"error_type": "unsupported_route", "route": self.route},
            extra_fields={"repo_harness_gateway_kind": "unsupported_route"},
        )


def build_llm_gateway_for_route(
    route: str,
    *,
    model_client: ModelClient | None = None,
    run_dir_root: str | Path | None = None,
    max_workers: int = 1,
) -> MockLLMGateway | ModelClientLLMGateway | UnsupportedRouteLLMGateway:
    validate_route_name(route)
    if route in {"verl", "local_vllm", "local_sglang"}:
        return UnsupportedRouteLLMGateway(route)
    if route == "mock" and model_client is None:
        return MockLLMGateway()
    if model_client is None or run_dir_root is None:
        return UnsupportedRouteLLMGateway(route)
    if route == "replay":
        return ReplayLLMGateway(model_client=model_client, run_dir_root=run_dir_root, max_workers=max_workers)
    if route in {"openai", "deepseek"}:
        return ProviderLLMGateway(model_client=model_client, run_dir_root=run_dir_root, max_workers=max_workers)
    return ModelClientLLMGateway(model_client=model_client, run_dir_root=run_dir_root, max_workers=max_workers)


def _provider_options_from_request(
    request: LLMGatewayRequest,
    *,
    default_model_id: str,
) -> ModelProviderOptions:
    raw_options = dict(request.provider_options)
    credential_policy = raw_options.get("credential_policy")
    parsed_credential_policy = (
        ProviderCredentialPolicy.model_validate(credential_policy)
        if isinstance(credential_policy, dict)
        else ProviderCredentialPolicy()
    )
    provider_specific_options = raw_options.get("provider_specific_options")
    if not isinstance(provider_specific_options, dict):
        provider_specific_options = {
            key: value
            for key, value in raw_options.items()
            if key
            not in {
                "provider",
                "model_id",
                "model",
                "credential_policy",
                "provider_model_settings",
                "tool_choice",
            }
        }
    return ModelProviderOptions(
        provider=str(raw_options.get("provider") or request.route),
        model_id=str(raw_options.get("model_id") or raw_options.get("model") or default_model_id),
        credential_policy=parsed_credential_policy,
        provider_specific_options=dict(provider_specific_options),
    )


def _recorder_profile_from_policy(policy: dict[str, Any]) -> RecorderProfile:
    if not policy:
        return RecorderProfile.for_run_mode("training_fast")
    if "mode" in policy:
        base = RecorderProfile.for_run_mode(str(policy["mode"])).model_dump(mode="json")
        return RecorderProfile.model_validate({**base, **policy})
    return RecorderProfile.for_run_mode("training_fast")


def _assistant_debug_text(assistant_message: dict[str, Any], tool_calls: list[dict[str, Any]]) -> str:
    content = assistant_message.get("content")
    if isinstance(content, str) and content:
        return content
    payload = {"assistant_message": assistant_message, "tool_calls": tool_calls}
    text = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return text if text != "{}" else ""


def _debug_token_ids(text: str) -> list[int]:
    if not text:
        return []
    return [byte + 1 for byte in text.encode("utf-8")]


def _optional_opaque_artifact_ref(
    request: LLMGatewayRequest,
    artifact_ref: ArtifactRef | None,
) -> str | None:
    if artifact_ref is None:
        return None
    return _opaque_artifact_ref(request, artifact_ref)


def _opaque_artifact_ref(request: LLMGatewayRequest, artifact_ref: ArtifactRef) -> str:
    return f"rh://artifact/{request.run_id}/{request.model_call_id}/{artifact_ref.artifact_id}"
