"""VerlLLMGateway adapter for verl-managed LLMServerClient."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable, Mapping
from time import perf_counter
from typing import Any

from repo_harness.rl import LLMGatewayRequest, LLMGatewayResponse

from .errors import RepoHarnessVerlGatewayError
from .visibility import VerlVisibilityError, validate_token_output_extra_fields

PromptIdsBuilder = Callable[[LLMGatewayRequest], Awaitable[list[int]] | list[int]]


class VerlLLMGateway:
    """把 RepoHarness LLMGatewayRequest 转成 verl LLMServerClient.generate(...) 调用。"""

    def __init__(
        self,
        *,
        server_manager: Any,
        tokenizer: Any,
        processor: Any = None,
        inference_backend: str,
        sampling_params: Mapping[str, Any] | None = None,
        prompt_ids_builder: PromptIdsBuilder | None = None,
    ) -> None:
        self.server_manager = server_manager
        self.tokenizer = tokenizer
        self.processor = processor
        self.inference_backend = inference_backend
        self.sampling_params = dict(sampling_params or {})
        self.prompt_ids_builder = prompt_ids_builder

    async def generate_turn(self, request: LLMGatewayRequest) -> LLMGatewayResponse:
        parsed_request = LLMGatewayRequest.model_validate(request)
        if parsed_request.route != "verl":
            raise RepoHarnessVerlGatewayError("VerlLLMGateway only accepts route=verl requests")
        if parsed_request.inference_backend != self.inference_backend:
            raise RepoHarnessVerlGatewayError("gateway inference_backend does not match request")

        prompt_ids = await self._build_prompt_ids(parsed_request)
        sampling_params = self._merged_sampling_params(parsed_request)
        started = perf_counter()
        token_output = await self.server_manager.generate(
            parsed_request.sticky_session_id or parsed_request.episode_id,
            prompt_ids=prompt_ids,
            sampling_params=sampling_params,
            image_data=None,
            video_data=None,
        )
        duration_ms = int((perf_counter() - started) * 1000)
        return token_output_to_llm_gateway_response(
            token_output,
            request=parsed_request,
            prompt_ids=prompt_ids,
            tokenizer=self.tokenizer,
            inference_backend=self.inference_backend,
            duration_ms=duration_ms,
        )

    async def _build_prompt_ids(self, request: LLMGatewayRequest) -> list[int]:
        if self.prompt_ids_builder is not None:
            maybe_prompt_ids = self.prompt_ids_builder(request)
            prompt_ids = await maybe_prompt_ids if inspect.isawaitable(maybe_prompt_ids) else maybe_prompt_ids
            return _coerce_int_list(prompt_ids, field_name="prompt_ids")

        if hasattr(self.tokenizer, "apply_chat_template"):
            tokenized = self.tokenizer.apply_chat_template(
                request.messages,
                tools=request.tools or None,
                add_generation_prompt=True,
                tokenize=True,
            )
            return _coerce_int_list(tokenized, field_name="prompt_ids")
        raise RepoHarnessVerlGatewayError("missing_prompt_ids_builder")

    def _merged_sampling_params(self, request: LLMGatewayRequest) -> dict[str, Any]:
        merged = {key: value for key, value in self.sampling_params.items() if value is not None}
        merged.update({key: value for key, value in request.sampling_params.items() if value is not None})
        return merged


def token_output_to_llm_gateway_response(
    token_output: Any,
    *,
    request: LLMGatewayRequest,
    prompt_ids: list[int],
    tokenizer: Any,
    inference_backend: str,
    duration_ms: int,
) -> LLMGatewayResponse:
    """把 verl TokenOutput 映射为 RepoHarness LLMGatewayResponse。"""

    output_token_ids = _coerce_int_list(_get_attr(token_output, "token_ids", []), field_name="token_ids")
    output_logprobs = _coerce_optional_float_list(_get_attr(token_output, "log_probs", None), field_name="log_probs")
    extra_fields = dict(_get_attr(token_output, "extra_fields", {}) or {})
    num_preempted = _get_attr(token_output, "num_preempted", None)
    if num_preempted is not None:
        extra_fields.setdefault("num_preempted", int(num_preempted))
    _validate_token_output_extra_fields(extra_fields)

    global_steps = _coerce_optional_int(extra_fields.get("global_steps"), field_name="global_steps")
    min_global_steps = _coerce_optional_int(extra_fields.get("min_global_steps"), field_name="min_global_steps")
    max_global_steps = _coerce_optional_int(extra_fields.get("max_global_steps"), field_name="max_global_steps")

    return LLMGatewayResponse(
        route="verl",
        inference_backend=inference_backend,  # type: ignore[arg-type]
        model_call_id=request.model_call_id,
        assistant_message={"role": "assistant", "content": _decode_output(tokenizer, output_token_ids)},
        tool_calls=[],
        prompt_ids=list(prompt_ids),
        output_token_ids=output_token_ids,
        output_logprobs=output_logprobs,
        response_mask=[1] * len(output_token_ids),
        stop_reason=_optional_string(_get_attr(token_output, "stop_reason", None)),
        token_source="verl_llm_server_client",
        policy_version={"token_source": "verl_llm_server_client"},
        global_steps=global_steps,
        min_global_steps=min_global_steps,
        max_global_steps=max_global_steps,
        routed_experts=_coerce_routed_experts(_get_attr(token_output, "routed_experts", None)),
        usage={"input_tokens": len(prompt_ids), "output_tokens": len(output_token_ids)},
        duration_ms=duration_ms,
        error=None if output_logprobs is not None else {"type": "missing_response_logprobs"},
        extra_fields=extra_fields,
    )


def _validate_token_output_extra_fields(extra_fields: Mapping[str, Any]) -> None:
    try:
        validate_token_output_extra_fields(dict(extra_fields))
    except VerlVisibilityError as exc:
        raise RepoHarnessVerlGatewayError(f"forbidden_token_output_extra_fields: {exc}") from exc


def _decode_output(tokenizer: Any, token_ids: list[int]) -> str:
    if hasattr(tokenizer, "decode"):
        return str(tokenizer.decode(token_ids, skip_special_tokens=True))
    return " ".join(str(token_id) for token_id in token_ids)


def _get_attr(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _coerce_int_list(value: Any, *, field_name: str) -> list[int]:
    try:
        return [int(item) for item in _as_list(value)]
    except (TypeError, ValueError) as exc:
        raise RepoHarnessVerlGatewayError(f"{field_name} must be a list of integers") from exc


def _coerce_optional_float_list(value: Any, *, field_name: str) -> list[float] | None:
    if value is None:
        return None
    try:
        return [float(item) for item in _as_list(value)]
    except (TypeError, ValueError) as exc:
        raise RepoHarnessVerlGatewayError(f"{field_name} must be a list of floats") from exc


def _coerce_optional_int(value: Any, *, field_name: str) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise RepoHarnessVerlGatewayError(f"{field_name} must be an integer") from exc


def _coerce_routed_experts(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if hasattr(value, "tolist"):
        return value.tolist()
    return [value]


def _optional_string(value: Any) -> str | None:
    return None if value is None else str(value)


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if hasattr(value, "tolist"):
        maybe_list = value.tolist()
        return maybe_list if isinstance(maybe_list, list) else [maybe_list]
    return list(value)
