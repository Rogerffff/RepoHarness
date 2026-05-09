"""Context budget and provider request projection helpers."""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import Field

from repo_harness.config import ContextManagementConfig
from repo_harness.schema_base import StrictBaseModel, stable_hash

PROVIDER_REQUEST_PROJECTION_VERSION = "repo_harness_provider_request_projection_v1"
PROVIDER_REQUEST_TOKEN_ESTIMATOR_VERSION = "provider_request_char4_token_estimator_v1"

MODEL_CONTEXT_WINDOW_REGISTRY: dict[tuple[str, str], int] = {
    ("deepseek", "deepseek-v4"): 1_000_000,
    ("deepseek", "deepseek-chat"): 1_000_000,
    ("openai", "gpt-5.5"): 1_000_000,
    ("openai", "gpt-5.4"): 1_000_000,
    ("openai", "gpt-5"): 1_000_000,
}

PROVIDER_CONTEXT_WINDOW_DEFAULTS: dict[str, int] = {
    "deepseek": 1_000_000,
    "openai": 1_000_000,
}


class ContextBudgetFacts(StrictBaseModel):
    schema_version: str = "repo_harness_context_budget_facts_v1"
    provider: str
    model_id: str
    model_context_window_tokens: int = Field(gt=0)
    model_context_window_resolution: str
    harness_context_cap_tokens: int | None = Field(default=None, gt=0)
    budget_base_window_tokens: int = Field(gt=0)
    main_output_reserve_tokens: int = Field(ge=0)
    estimator_safety_margin_tokens: int = Field(ge=0)
    estimator_safety_margin_ratio: float = Field(ge=0.0)
    estimator_safety_margin_min_tokens: int = Field(ge=0)
    effective_context_budget_tokens: int = Field(gt=0)
    hard_context_limit_tokens: int = Field(gt=0)
    hard_context_limit_ratio: float = Field(gt=0.0)
    post_compact_target_tokens: int = Field(gt=0)
    post_compact_target_ratio: float = Field(gt=0.0)
    post_compact_target_max_tokens: int = Field(gt=0)
    legacy_max_context_tokens: int = Field(gt=0)


class ProviderRequestProjectionEstimate(StrictBaseModel):
    schema_version: str = "repo_harness_provider_request_projection_estimate_v1"
    provider_request_projection_hash: str
    provider_request_projection_version: str = PROVIDER_REQUEST_PROJECTION_VERSION
    token_estimator_version: str = PROVIDER_REQUEST_TOKEN_ESTIMATOR_VERSION
    provider_request_token_estimate: int = Field(ge=0)
    message_token_estimate: int = Field(ge=0)
    tool_schema_token_estimate: int = Field(ge=0)
    tool_choice_token_estimate: int = Field(ge=0)
    provider_wrapper_token_estimate: int = Field(ge=0)
    generation_config_token_estimate: int = Field(ge=0)
    main_output_reserve_tokens: int = Field(ge=0)
    estimator_safety_margin_tokens: int = Field(ge=0)
    effective_context_budget_tokens: int = Field(gt=0)
    hard_context_limit_tokens: int = Field(gt=0)
    post_compact_target_tokens: int = Field(gt=0)


def resolve_context_budget(
    *,
    config: ContextManagementConfig,
    provider: str,
    model_id: str,
) -> ContextBudgetFacts:
    model_window, resolution = _resolve_model_window(
        config=config,
        provider=provider,
        model_id=model_id,
    )
    base_window = model_window
    if config.harness_context_cap_tokens is not None:
        base_window = min(base_window, config.harness_context_cap_tokens)
    safety_margin = max(
        int(base_window * config.estimator_safety_margin_ratio),
        config.estimator_safety_margin_min_tokens,
    )
    effective = max(1, base_window - config.main_output_reserve_tokens - safety_margin)
    hard_limit = max(1, int(effective * config.hard_context_limit_ratio))
    post_target = max(
        1,
        min(
            int(effective * config.post_compact_target_ratio),
            config.post_compact_target_max_tokens,
        ),
    )
    return ContextBudgetFacts(
        provider=provider,
        model_id=model_id,
        model_context_window_tokens=model_window,
        model_context_window_resolution=resolution,
        harness_context_cap_tokens=config.harness_context_cap_tokens,
        budget_base_window_tokens=base_window,
        main_output_reserve_tokens=config.main_output_reserve_tokens,
        estimator_safety_margin_tokens=safety_margin,
        estimator_safety_margin_ratio=config.estimator_safety_margin_ratio,
        estimator_safety_margin_min_tokens=config.estimator_safety_margin_min_tokens,
        effective_context_budget_tokens=effective,
        hard_context_limit_tokens=hard_limit,
        hard_context_limit_ratio=config.hard_context_limit_ratio,
        post_compact_target_tokens=post_target,
        post_compact_target_ratio=config.post_compact_target_ratio,
        post_compact_target_max_tokens=config.post_compact_target_max_tokens,
        legacy_max_context_tokens=config.max_context_tokens,
    )


def build_provider_request_projection(
    *,
    provider: str,
    model_id: str,
    provider_message_format: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    tool_choice: str | dict[str, Any] | None,
    generation_config: dict[str, Any],
    provider_model_settings: dict[str, Any],
) -> dict[str, Any]:
    projected_messages = _project_messages_for_provider(messages, provider=provider)
    projected_tools = _project_tools_for_provider(tools, provider=provider)
    resolved_tool_choice = _resolved_tool_choice(
        tools=projected_tools,
        requested_tool_choice=tool_choice,
        provider=provider,
    )
    return {
        "schema_version": PROVIDER_REQUEST_PROJECTION_VERSION,
        "provider": provider,
        "model_id": model_id,
        "provider_message_format": provider_message_format,
        "messages": projected_messages,
        "tools": projected_tools,
        "tool_choice": resolved_tool_choice,
        "generation_config": generation_config,
        "provider_model_settings": provider_model_settings,
        "wrapper": {
            "request_kind": "chat_completion_with_tools",
            "projection_scope": "model_visible_request_body",
        },
    }


def estimate_provider_request_projection(
    *,
    projection: dict[str, Any],
    budget_facts: ContextBudgetFacts,
) -> ProviderRequestProjectionEstimate:
    messages = projection.get("messages")
    tools = projection.get("tools")
    tool_choice = projection.get("tool_choice")
    generation_config = {
        "generation_config": projection.get("generation_config"),
        "provider_model_settings": projection.get("provider_model_settings"),
    }
    total = _char4_token_estimate(projection)
    message_tokens = _char4_token_estimate(messages)
    tool_tokens = _char4_token_estimate(tools)
    tool_choice_tokens = _char4_token_estimate(tool_choice)
    generation_tokens = _char4_token_estimate(generation_config)
    wrapper_tokens = max(
        0,
        total - message_tokens - tool_tokens - tool_choice_tokens - generation_tokens,
    )
    return ProviderRequestProjectionEstimate(
        provider_request_projection_hash=stable_hash(projection),
        provider_request_token_estimate=total,
        message_token_estimate=message_tokens,
        tool_schema_token_estimate=tool_tokens,
        tool_choice_token_estimate=tool_choice_tokens,
        provider_wrapper_token_estimate=wrapper_tokens,
        generation_config_token_estimate=generation_tokens,
        main_output_reserve_tokens=budget_facts.main_output_reserve_tokens,
        estimator_safety_margin_tokens=budget_facts.estimator_safety_margin_tokens,
        effective_context_budget_tokens=budget_facts.effective_context_budget_tokens,
        hard_context_limit_tokens=budget_facts.hard_context_limit_tokens,
        post_compact_target_tokens=budget_facts.post_compact_target_tokens,
    )


def _resolve_model_window(
    *,
    config: ContextManagementConfig,
    provider: str,
    model_id: str,
) -> tuple[int, str]:
    if isinstance(config.model_context_window_tokens, int):
        return config.model_context_window_tokens, "explicit_config"
    normalized_provider = provider.lower()
    normalized_model = model_id.lower()
    exact = MODEL_CONTEXT_WINDOW_REGISTRY.get((normalized_provider, normalized_model))
    if exact is not None:
        return exact, "exact_model_registry"
    for (registered_provider, registered_model), window in MODEL_CONTEXT_WINDOW_REGISTRY.items():
        if registered_provider == normalized_provider and normalized_model.startswith(registered_model):
            return window, "prefix_model_registry"
    provider_default = PROVIDER_CONTEXT_WINDOW_DEFAULTS.get(normalized_provider)
    if provider_default is not None:
        return provider_default, "provider_default_registry"
    return _legacy_default_window(config), "unknown_model_uses_legacy_default"


def _legacy_default_window(config: ContextManagementConfig) -> int:
    return (
        config.max_context_tokens
        + config.main_output_reserve_tokens
        + config.estimator_safety_margin_min_tokens
    )


def _char4_token_estimate(value: Any) -> int:
    return max(1, len(json.dumps(value, ensure_ascii=False, sort_keys=True)) // 4)


def _project_messages_for_provider(
    messages: list[dict[str, Any]],
    *,
    provider: str,
) -> list[dict[str, Any]]:
    if provider in {"mock", "replay"}:
        return [dict(message) for message in messages]
    return [_to_chat_message_projection(message) for message in messages]


def _project_tools_for_provider(
    tools: list[dict[str, Any]],
    *,
    provider: str,
) -> list[dict[str, Any]]:
    if provider in {"mock", "replay"}:
        return [dict(tool) for tool in tools]
    return [_to_chat_tool_projection(tool) for tool in tools]


def _resolved_tool_choice(
    *,
    tools: list[dict[str, Any]],
    requested_tool_choice: str | dict[str, Any] | None,
    provider: str,
) -> str | dict[str, Any] | None:
    if provider in {"mock", "replay"}:
        return requested_tool_choice
    if tools:
        return requested_tool_choice or "auto"
    return "none"


def _to_chat_message_projection(message: dict[str, Any]) -> dict[str, Any]:
    role = str(message.get("role") or "user")
    converted: dict[str, Any] = {"role": role}
    if role == "assistant":
        content = _content_to_string(message.get("content"))
        converted["content"] = content
        calls = message.get("tool_calls") or []
        if isinstance(calls, list) and calls:
            converted["tool_calls"] = [_to_provider_tool_call_projection(call) for call in calls]
        return converted
    if role == "tool":
        converted["content"] = _content_to_string(message.get("content"))
        converted["tool_call_id"] = str(message.get("tool_call_id") or message.get("tool_result_id") or "")
        return converted
    converted["content"] = _content_to_string(message.get("content"))
    return converted


def _to_provider_tool_call_projection(call: Any) -> dict[str, Any]:
    if hasattr(call, "model_dump"):
        call = call.model_dump(mode="json")
    if not isinstance(call, dict):
        call = {}
    return {
        "id": str(call.get("tool_call_id") or call.get("id") or ""),
        "type": "function",
        "function": {
            "name": str(call.get("tool_name") or call.get("name") or ""),
            "arguments": json.dumps(call.get("arguments") or {}, ensure_ascii=False, sort_keys=True),
        },
    }


def _to_chat_tool_projection(tool: dict[str, Any]) -> dict[str, Any]:
    parameters = dict(tool.get("input_schema") or {})
    parameters.setdefault("type", "object")
    properties = dict(parameters.get("properties") or {})
    required = list(parameters.get("required") or [])
    for name in required:
        properties.setdefault(name, {"type": "string"})
    parameters["properties"] = properties
    description = str(tool.get("description") or tool.get("model_visible_prompt") or tool.get("name"))
    prompt = tool.get("model_visible_prompt")
    if prompt and str(prompt) not in description:
        description = f"{description}\n{prompt}"
    return {
        "type": "function",
        "function": {
            "name": str(tool.get("name")),
            "description": description,
            "parameters": parameters,
        },
    }


def _content_to_string(content: Any) -> str | None:
    if content is None:
        return None
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False, sort_keys=True)
