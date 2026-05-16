"""最小 LLMGateway contract 和 fake gateway。"""

from __future__ import annotations

from collections import deque
from typing import Any, Protocol, runtime_checkable

from pydantic import Field, model_validator

from repo_harness.schema_base import StrictBaseModel

from .visibility import (
    CONTRACT_VERSION,
    GatewayRoute,
    InferenceBackend,
    validate_gateway_extra_fields,
    validate_inference_backend,
    validate_no_forbidden_model_visible_content,
    validate_safe_identifier,
    validate_opaque_ref,
)


class LLMGatewayRequest(StrictBaseModel):
    schema_version: str = "repo_harness_verl_llm_gateway_request_v0"
    contract_version: str = CONTRACT_VERSION
    fixture_kind: str | None = None
    route: GatewayRoute
    inference_backend: InferenceBackend | None = None
    run_id: str
    task_id: str
    episode_id: str
    model_call_id: str
    turn: int = Field(ge=0)
    context_revision: int = Field(ge=0)
    messages: list[dict[str, Any]]
    tools: list[dict[str, Any]] = Field(default_factory=list)
    sampling_params: dict[str, Any] = Field(default_factory=dict)
    provider_options: dict[str, Any] = Field(default_factory=dict)
    tokenizer_policy: dict[str, Any] = Field(default_factory=dict)
    sticky_session_id: str | None = None
    timeout_seconds: float | None = Field(default=None, gt=0)
    budget_state: dict[str, Any] = Field(default_factory=dict)
    recorder_policy: dict[str, Any] = Field(default_factory=dict)
    visibility_policy: dict[str, Any] = Field(default_factory=dict)
    tracing: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_gateway_request(self) -> "LLMGatewayRequest":
        validate_safe_identifier(self.run_id, field_name="run_id")
        validate_safe_identifier(self.task_id, field_name="task_id")
        validate_safe_identifier(self.episode_id, field_name="episode_id")
        validate_safe_identifier(self.model_call_id, field_name="model_call_id")
        validate_inference_backend(self.route, self.inference_backend)
        validate_no_forbidden_model_visible_content(self.messages, field_name="messages")
        validate_no_forbidden_model_visible_content(self.tools, field_name="tools")
        return self


class GenerationRecord(StrictBaseModel):
    schema_version: str = "repo_harness_verl_generation_record_v0"
    turn: int = Field(ge=0)
    model_call_id: str
    context_revision: int = Field(ge=0)
    prompt_ids: list[int]
    output_token_ids: list[int]
    output_logprobs: list[float] | None = None
    stop_reason: str | None = None
    gateway_route: GatewayRoute
    inference_backend: InferenceBackend | None = None
    policy_version: dict[str, Any] = Field(default_factory=dict)
    global_steps: int | None = Field(default=None, ge=0)
    min_global_steps: int | None = Field(default=None, ge=0)
    max_global_steps: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_generation_record(self) -> "GenerationRecord":
        validate_inference_backend(self.gateway_route, self.inference_backend)
        if self.output_logprobs is not None and len(self.output_logprobs) != len(self.output_token_ids):
            raise ValueError("output_logprobs must align with output_token_ids")
        if self.global_steps is not None and self.min_global_steps is not None and self.max_global_steps is not None:
            if not (self.min_global_steps <= self.global_steps <= self.max_global_steps):
                raise ValueError("global_steps must be within min/max bounds")
        return self


class LLMGatewayResponse(StrictBaseModel):
    schema_version: str = "repo_harness_verl_llm_gateway_response_v0"
    contract_version: str = CONTRACT_VERSION
    fixture_kind: str | None = None
    route: GatewayRoute
    inference_backend: InferenceBackend | None = None
    model_call_id: str
    assistant_message: dict[str, Any]
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    prompt_ids: list[int]
    output_token_ids: list[int]
    output_logprobs: list[float] | None = None
    response_mask: list[int]
    stop_reason: str | None = None
    token_source: str | None = None
    policy_version: dict[str, Any] = Field(default_factory=dict)
    global_steps: int | None = Field(default=None, ge=0)
    min_global_steps: int | None = Field(default=None, ge=0)
    max_global_steps: int | None = Field(default=None, ge=0)
    routed_experts: list[Any] = Field(default_factory=list)
    usage: dict[str, int] = Field(default_factory=dict)
    provider_request_id: str | None = None
    raw_request_ref: str | None = None
    raw_response_ref: str | None = None
    model_call_event_ref: str | None = None
    duration_ms: int | None = Field(default=None, ge=0)
    error: dict[str, Any] | str | None = None
    extra_fields: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_gateway_response(self) -> "LLMGatewayResponse":
        validate_inference_backend(self.route, self.inference_backend)
        if len(self.output_token_ids) != len(self.response_mask):
            raise ValueError("output_token_ids and response_mask must have equal length")
        if any(mask != 1 for mask in self.response_mask):
            raise ValueError("LLMGatewayResponse.response_mask must be all 1 for model-generated tokens")
        if self.output_logprobs is not None and len(self.output_logprobs) != len(self.output_token_ids):
            raise ValueError("output_logprobs must align with output_token_ids")
        if self.global_steps is not None and self.min_global_steps is not None and self.max_global_steps is not None:
            if not (self.min_global_steps <= self.global_steps <= self.max_global_steps):
                raise ValueError("global_steps must be within min/max bounds")
        for field_name in ["raw_request_ref", "raw_response_ref", "model_call_event_ref"]:
            value = getattr(self, field_name)
            if value:
                validate_opaque_ref(value, field_name=field_name)
        validate_gateway_extra_fields(self.extra_fields)
        return self

    def to_generation_record(self, *, turn: int, context_revision: int) -> GenerationRecord:
        return GenerationRecord(
            turn=turn,
            model_call_id=self.model_call_id,
            context_revision=context_revision,
            prompt_ids=self.prompt_ids,
            output_token_ids=self.output_token_ids,
            output_logprobs=self.output_logprobs,
            stop_reason=self.stop_reason,
            gateway_route=self.route,
            inference_backend=self.inference_backend,
            policy_version=self.policy_version,
            global_steps=self.global_steps,
            min_global_steps=self.min_global_steps,
            max_global_steps=self.max_global_steps,
        )


@runtime_checkable
class LLMGateway(Protocol):
    async def generate_turn(self, request: LLMGatewayRequest) -> LLMGatewayResponse:
        """生成一轮 assistant 输出，并返回 token 级事实。"""


class FakeLLMGateway:
    """供 Stage 2 runtime facade 测试复用的确定性 fake gateway。"""

    def __init__(self, responses: list[LLMGatewayResponse | dict[str, Any]] | None = None) -> None:
        self._responses: deque[LLMGatewayResponse] = deque(
            response if isinstance(response, LLMGatewayResponse) else LLMGatewayResponse.model_validate(response)
            for response in (responses or [])
        )
        self.requests: list[LLMGatewayRequest] = []

    async def generate_turn(self, request: LLMGatewayRequest) -> LLMGatewayResponse:
        self.requests.append(request)
        if self._responses:
            return self._responses.popleft()
        token_id = 200 + request.turn
        return LLMGatewayResponse(
            route=request.route,
            inference_backend=request.inference_backend,
            model_call_id=request.model_call_id,
            assistant_message={"role": "assistant", "content": f"fake response turn {request.turn}"},
            tool_calls=[],
            prompt_ids=[],
            output_token_ids=[token_id],
            output_logprobs=[-0.01],
            response_mask=[1],
            stop_reason="stop",
            token_source="mock_gateway",
            policy_version={},
            duration_ms=0,
            extra_fields={},
        )
