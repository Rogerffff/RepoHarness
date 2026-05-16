"""RepoHarness 强化学习接入的可见性和 route 边界规则。"""

from __future__ import annotations

import re
from typing import Any, Literal, Mapping

from pydantic import Field, model_validator

from repo_harness.schema_base import StrictBaseModel

CONTRACT_VERSION = "repo_harness_verl_shared_contracts_v0"

GatewayRoute = Literal["verl", "openai", "deepseek", "local_vllm", "local_sglang", "replay", "mock"]
InferenceBackend = Literal["sglang", "vllm"]
FlatScalar = str | int | float | bool | None

ALLOWED_ROUTES = {"verl", "openai", "deepseek", "local_vllm", "local_sglang", "replay", "mock"}
PROVIDER_ROUTES = {"openai", "deepseek"}
ALLOWED_INFERENCE_BACKENDS = {"sglang", "vllm"}
OFFLINE_PROVIDER_ALLOWED_USES = {
    "evaluation",
    "teacher_data_generation",
    "sft_export",
    "preference_data",
    "offline_diagnostic_replay",
}
EVALUATOR_ONLY_DENYLIST = {
    "hidden_verifier",
    "gold_patch",
    "accepted_label",
    "complete_reward_metadata",
    "provider_secret",
    "evaluator_only_logs",
    "absolute_run_directory",
    "final_verifier_artifact",
    "reward_metadata_artifact",
    "hidden_test_selector",
    "hidden_test_patch",
}
RAW_PROMPT_FORBIDDEN_TOKENS = {
    "hidden_verifier",
    "gold_patch",
    "accepted_label",
    "provider_secret",
    "evaluator_only_logs",
}
FORBIDDEN_BATCH_EXTRA_FIELD_KEYS = {
    "audit_ref",
    "run_dir",
    "reward_metadata_path",
    "final_verifier_path",
    "gold_patch_path",
}
FORBIDDEN_BATCH_EXTRA_FIELD_ALIASES = {"run_directory"}
FORBIDDEN_FIELD_MARKERS = (
    EVALUATOR_ONLY_DENYLIST | FORBIDDEN_BATCH_EXTRA_FIELD_KEYS | FORBIDDEN_BATCH_EXTRA_FIELD_ALIASES
)


class VisibilityContractError(ValueError):
    """表示字段越过了模型可见或 batch 可传播边界。"""


SAFE_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")


def is_provider_route(route: str) -> bool:
    return route in PROVIDER_ROUTES


def default_invalid_for_online_rl(route: str) -> bool:
    """Only route=verl is eligible for formal online PPO / GRPO by default."""

    validate_route_name(route)
    return route != "verl"


def validate_route_name(route: str) -> str:
    if route not in ALLOWED_ROUTES:
        raise VisibilityContractError(f"unknown llm gateway route: {route}")
    return route


def validate_inference_backend(route: str, inference_backend: str | None) -> None:
    validate_route_name(route)
    if route == "verl" and inference_backend not in ALLOWED_INFERENCE_BACKENDS:
        raise VisibilityContractError("route=verl requires inference_backend=sglang|vllm")
    if inference_backend is not None and inference_backend not in ALLOWED_INFERENCE_BACKENDS:
        raise VisibilityContractError(f"unknown inference_backend: {inference_backend}")


def validate_no_absolute_local_path(value: str, *, field_name: str) -> None:
    if value.startswith("/") or "/Users/" in value or "\\" in value and len(value) > 2 and value[1:3] == ":\\":
        raise VisibilityContractError(f"{field_name} must not contain an absolute local path")


def validate_safe_identifier(value: str, *, field_name: str) -> str:
    validate_no_absolute_local_path(value, field_name=field_name)
    if value in {".", ".."} or "/" in value or "\\" in value:
        raise VisibilityContractError(f"{field_name} must be a safe identifier without path separators")
    if ".." in value:
        raise VisibilityContractError(f"{field_name} must not contain parent directory traversal")
    if not SAFE_IDENTIFIER_PATTERN.fullmatch(value):
        raise VisibilityContractError(f"{field_name} must be a safe identifier")
    return value


def _walk_key_values(value: Any):
    if isinstance(value, Mapping):
        for key, item in value.items():
            yield str(key), item
            yield from _walk_key_values(item)
    elif isinstance(value, list):
        for item in value:
            yield "", item
            yield from _walk_key_values(item)


def _normalize_visibility_marker(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _strip_repo_harness_namespace(key: str) -> str:
    return key.removeprefix("repo_harness_")


def _find_forbidden_marker(value: str) -> str | None:
    normalized = _normalize_visibility_marker(value)
    normalized_without_namespace = _strip_repo_harness_namespace(normalized)
    compact = normalized.replace("_", "")
    compact_without_namespace = normalized_without_namespace.replace("_", "")
    for marker in FORBIDDEN_FIELD_MARKERS:
        normalized_marker = _normalize_visibility_marker(marker)
        compact_marker = normalized_marker.replace("_", "")
        if normalized_marker in {normalized, normalized_without_namespace}:
            return marker
        if normalized_marker and normalized_marker in normalized_without_namespace:
            return marker
        if compact_marker and compact_marker in compact_without_namespace:
            return marker
    return None


def _collect_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        parts: list[str] = []
        for key, item in value.items():
            parts.append(str(key))
            parts.append(_collect_text(item))
        return " ".join(parts)
    if isinstance(value, list):
        return " ".join(_collect_text(item) for item in value)
    return ""


def validate_no_forbidden_model_visible_content(
    value: Any,
    *,
    field_name: str,
    forbidden_tokens: set[str] | None = None,
) -> None:
    tokens = forbidden_tokens or RAW_PROMPT_FORBIDDEN_TOKENS
    visible_text = _collect_text(value)
    for token in tokens:
        if token in visible_text:
            raise VisibilityContractError(f"{field_name} contains evaluator-only content: {token}")
    marker = _find_forbidden_marker(visible_text)
    if marker:
        raise VisibilityContractError(f"{field_name} contains evaluator-only content: {marker}")


def validate_opaque_ref(value: str, *, field_name: str) -> None:
    validate_no_absolute_local_path(value, field_name=field_name)
    if not value.startswith("rh://"):
        raise VisibilityContractError(f"{field_name} must be an opaque rh:// reference")


def validate_batch_extra_fields(extra_fields: Mapping[str, Any]) -> dict[str, FlatScalar]:
    """校验未来可进入 AgentLoopOutput.extra_fields 的扁平字段。"""

    validated: dict[str, FlatScalar] = {}
    for key, value in extra_fields.items():
        if not key.startswith("repo_harness_"):
            raise VisibilityContractError(f"batch extra field must be repo_harness_* namespaced: {key}")
        if key.endswith("_audit_ref") or _find_forbidden_marker(key):
            raise VisibilityContractError(f"forbidden batch extra field: {key}")
        if isinstance(value, (dict, list)):
            raise VisibilityContractError(f"batch extra field must be a flat scalar: {key}")
        if not isinstance(value, (str, int, float, bool, type(None))):
            raise VisibilityContractError(f"batch extra field has unsupported scalar type: {key}")
        if isinstance(value, str):
            validate_no_absolute_local_path(value, field_name=key)
            if _find_forbidden_marker(value):
                raise VisibilityContractError(f"forbidden batch extra field value: {key}")
            if key.endswith("_ref"):
                validate_opaque_ref(value, field_name=key)
        validated[key] = value
    return validated


def validate_gateway_extra_fields(extra_fields: Mapping[str, Any]) -> dict[str, Any]:
    """校验 gateway 侧扩展字段。它不是 batch extra_fields，但仍不能携带 evaluator-only 泄漏。"""

    for key, value in _walk_key_values(dict(extra_fields)):
        if _find_forbidden_marker(key):
            raise VisibilityContractError(f"forbidden gateway extra field: {key}")
        if isinstance(value, str):
            validate_no_absolute_local_path(value, field_name=key)
            if _find_forbidden_marker(value):
                raise VisibilityContractError(f"forbidden gateway extra field value: {key}")
    return dict(extra_fields)


class ToolAccessAttempt(StrictBaseModel):
    schema_version: str = "repo_harness_verl_tool_access_attempt_v0"
    tool_name: str
    target_ref: str
    target_kind: str
    expected_status: Literal["denied", "allowed"]
    denied_reason: str | None = None

    @model_validator(mode="after")
    def validate_attempt(self) -> "ToolAccessAttempt":
        validate_opaque_ref(self.target_ref, field_name="target_ref")
        if self.expected_status == "denied" and not self.denied_reason:
            raise ValueError("denied tool access attempt requires denied_reason")
        return self


class RawPromptPolicy(StrictBaseModel):
    schema_version: str = "repo_harness_verl_raw_prompt_policy_v0"
    raw_prompt_model_visible_only: bool
    forbidden_content: list[str] = Field(default_factory=list)


class AuditPathAccessDeniedFixture(StrictBaseModel):
    schema_version: str = "repo_harness_verl_visibility_fixture_v0"
    contract_version: str = CONTRACT_VERSION
    fixture_kind: str | None = None
    episode_id: str
    run_id: str
    visibility_denylist: list[str] = Field(default_factory=list)
    tool_access_attempts: list[ToolAccessAttempt] = Field(default_factory=list)
    allowed_extra_fields: dict[str, FlatScalar] = Field(default_factory=dict)
    forbidden_extra_fields_examples: list[str] = Field(default_factory=list)
    raw_prompt_policy: RawPromptPolicy

    @model_validator(mode="after")
    def validate_visibility_fixture(self) -> "AuditPathAccessDeniedFixture":
        missing = EVALUATOR_ONLY_DENYLIST - set(self.visibility_denylist)
        if missing:
            raise ValueError(f"visibility denylist is missing required entries: {sorted(missing)}")
        validate_batch_extra_fields(self.allowed_extra_fields)
        if not FORBIDDEN_BATCH_EXTRA_FIELD_KEYS.issubset(set(self.forbidden_extra_fields_examples)):
            raise ValueError("visibility fixture must document forbidden batch extra field examples")
        return self
