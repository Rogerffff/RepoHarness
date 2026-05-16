"""verl kwargs 到 RepoHarnessEpisodeRequest 的安全映射。"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from repo_harness.rl import EpisodeBudgets, EpisodeTaskRef, RepoHarnessEpisodeRequest
from repo_harness.rl.visibility import (
    ALLOWED_INFERENCE_BACKENDS,
    VisibilityContractError,
    validate_no_absolute_local_path,
    validate_no_forbidden_model_visible_content,
    validate_safe_identifier,
)

from .errors import RepoHarnessVerlRequestMappingError
from .visibility import TRANSFER_QUEUE_RESERVED_KWARGS, VerlVisibilityError, validate_transfer_queue_kwargs

REQUEST_CONSTRUCTION_KWARGS = frozenset(
    {
        "raw_prompt",
        "agent_name",
        "task_id",
        "repo_harness_task_id",
        "repo_harness_task_ref",
        "repo_harness_run_config_ref",
        "repo_harness_budget_ref",
        "repo_harness_agent_policy_ref",
        "repo_harness_episode_seed",
        "repo_harness_run_mode",
        "repo_harness_dataset_name",
        "repo_harness_dataset_split",
        "repo_harness_dataset_revision",
    }
)

VERL_CONTROL_KWARGS = frozenset({"index", "uid", "session_id", "global_steps"})
REPO_HARNESS_VERL_ALLOWED_KWARGS = REQUEST_CONSTRUCTION_KWARGS | VERL_CONTROL_KWARGS
RUN_MODES = {"full_audit", "training_fast", "training_debug"}
_SAFE_IDENTIFIER_REPLACEMENTS = re.compile(r"[^A-Za-z0-9_.:-]+")


@dataclass(frozen=True)
class RepoHarnessVerlIdentifiers:
    task_id: str
    episode_id: str
    run_id: str


def validate_repo_harness_verl_kwargs(kwargs: Mapping[str, Any]) -> dict[str, Any]:
    """校验 verl 传入的 kwargs，并返回浅拷贝。

    这一步只允许 Stage 11 明确支持的 request 构造字段和 verl 控制字段。
    """

    try:
        validate_transfer_queue_kwargs(dict(kwargs), allowed_keys=set(REPO_HARNESS_VERL_ALLOWED_KWARGS))
    except VerlVisibilityError as exc:
        raise RepoHarnessVerlRequestMappingError(str(exc)) from exc

    for key in kwargs:
        if key in TRANSFER_QUEUE_RESERVED_KWARGS:
            raise RepoHarnessVerlRequestMappingError(f"reserved_verl_training_field: {key}")
        if key not in REPO_HARNESS_VERL_ALLOWED_KWARGS:
            raise RepoHarnessVerlRequestMappingError(f"repo_harness_verl_kwargs_not_allowlisted: {key}")

    raw_prompt = kwargs.get("raw_prompt")
    if raw_prompt is None:
        raise RepoHarnessVerlRequestMappingError("missing_raw_prompt")
    try:
        validate_no_forbidden_model_visible_content(raw_prompt, field_name="raw_prompt")
    except VisibilityContractError as exc:
        raise RepoHarnessVerlRequestMappingError(str(exc)) from exc

    _coerce_optional_int(kwargs.get("index"), field_name="index")
    _coerce_optional_int(kwargs.get("session_id"), field_name="session_id")
    _coerce_optional_int(kwargs.get("global_steps"), field_name="global_steps", minimum=0)
    if "uid" in kwargs and kwargs["uid"] is not None:
        _normalize_safe_identifier(kwargs["uid"], field_name="uid")
    return dict(kwargs)


def build_safe_episode_identifiers(kwargs: Mapping[str, Any]) -> RepoHarnessVerlIdentifiers:
    task_id_source = kwargs.get("repo_harness_task_id") or kwargs.get("task_id") or "repo_harness_task"
    task_id = _normalize_safe_identifier(task_id_source, field_name="task_id")

    uid = _normalize_safe_identifier(kwargs.get("uid", task_id), field_name="uid")
    index = _coerce_optional_int(kwargs.get("index"), field_name="index")
    session_id = _coerce_optional_int(kwargs.get("session_id"), field_name="session_id")
    global_steps = _coerce_optional_int(kwargs.get("global_steps"), field_name="global_steps", minimum=0)

    parts = [task_id, uid]
    if session_id is not None:
        parts.append(f"s{session_id}")
    if index is not None:
        parts.append(f"i{index}")
    if global_steps is not None:
        parts.append(f"g{global_steps}")
    episode_id = _normalize_safe_identifier("-".join(parts), field_name="episode_id")
    run_id = _normalize_safe_identifier(f"rh-verl-{episode_id}", field_name="run_id")
    return RepoHarnessVerlIdentifiers(task_id=task_id, episode_id=episode_id, run_id=run_id)


def build_episode_request_from_verl_kwargs(
    kwargs: Mapping[str, Any],
    *,
    sampling_params: Mapping[str, Any] | None = None,
    trainer_config: Any = None,
    rollout_config: Any = None,
    inference_backend: str | None = None,
) -> RepoHarnessEpisodeRequest:
    """把 verl AgentLoop kwargs 映射为 RepoHarnessEpisodeRequest。"""

    validated = validate_repo_harness_verl_kwargs(kwargs)
    backend = inference_backend or _infer_backend(rollout_config) or _infer_backend(trainer_config)
    if backend not in ALLOWED_INFERENCE_BACKENDS:
        raise RepoHarnessVerlRequestMappingError("route=verl requires explicit inference_backend=sglang|vllm")

    identifiers = build_safe_episode_identifiers(validated)
    task_ref = _build_task_ref(validated, identifiers.task_id)
    run_mode = str(validated.get("repo_harness_run_mode") or "training_fast")
    if run_mode not in RUN_MODES:
        raise RepoHarnessVerlRequestMappingError(f"unsupported_repo_harness_run_mode: {run_mode}")

    return RepoHarnessEpisodeRequest(
        episode_id=identifiers.episode_id,
        run_id=identifiers.run_id,
        task_id=identifiers.task_id,
        llm_gateway_route="verl",
        inference_backend=backend,  # type: ignore[arg-type]
        raw_prompt=_coerce_raw_prompt(validated["raw_prompt"]),
        task_ref=task_ref,
        agent_policy_ref=_optional_safe_ref(validated.get("repo_harness_agent_policy_ref"), "agent_policy_ref"),
        budget_ref=_optional_safe_ref(validated.get("repo_harness_budget_ref"), "budget_ref"),
        run_config_ref=_optional_safe_ref(validated.get("repo_harness_run_config_ref"), "run_config_ref"),
        episode_seed=_coerce_optional_int(validated.get("repo_harness_episode_seed"), field_name="episode_seed"),
        run_mode=run_mode,  # type: ignore[arg-type]
        budgets=_build_budgets(validated, sampling_params or {}, rollout_config),
    )


def _build_task_ref(kwargs: Mapping[str, Any], task_id: str) -> EpisodeTaskRef:
    raw_task_ref = kwargs.get("repo_harness_task_ref")
    if isinstance(raw_task_ref, Mapping):
        payload = dict(raw_task_ref)
    elif raw_task_ref is None:
        payload = {}
    else:
        payload = {"task_ref": str(raw_task_ref)}

    if "task_path" in payload and payload["task_path"] is not None:
        try:
            validate_no_absolute_local_path(str(payload["task_path"]), field_name="repo_harness_task_ref.task_path")
        except VisibilityContractError as exc:
            raise RepoHarnessVerlRequestMappingError(str(exc)) from exc
    payload.setdefault("task_id", task_id)
    if "dataset_name" not in payload and kwargs.get("repo_harness_dataset_name") is not None:
        payload["dataset_name"] = str(kwargs["repo_harness_dataset_name"])
    if "dataset_split" not in payload and kwargs.get("repo_harness_dataset_split") is not None:
        payload["dataset_split"] = str(kwargs["repo_harness_dataset_split"])
    if "dataset_revision" not in payload and kwargs.get("repo_harness_dataset_revision") is not None:
        payload["dataset_revision"] = str(kwargs["repo_harness_dataset_revision"])
    return EpisodeTaskRef.model_validate(payload)


def _build_budgets(
    kwargs: Mapping[str, Any],
    sampling_params: Mapping[str, Any],
    rollout_config: Any,
) -> EpisodeBudgets:
    max_output_tokens = _min_positive_int(
        sampling_params.get("max_output_tokens"),
        sampling_params.get("max_new_tokens"),
        sampling_params.get("max_tokens"),
        sampling_params.get("response_length"),
        _get_nested(rollout_config, "response_length"),
    )
    max_prompt_tokens = _min_positive_int(
        sampling_params.get("prompt_length"),
        _get_nested(rollout_config, "prompt_length"),
    )
    return EpisodeBudgets(
        max_output_tokens=max_output_tokens,
        max_prompt_tokens=max_prompt_tokens,
        reasoning_effort=_optional_string(sampling_params.get("reasoning_effort")),
        thinking_mode=_optional_string(sampling_params.get("thinking_mode")),
    )


def _coerce_raw_prompt(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise RepoHarnessVerlRequestMappingError("raw_prompt must be a list of model-visible messages")
    messages: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise RepoHarnessVerlRequestMappingError("raw_prompt items must be message mappings")
        messages.append(dict(item))
    return messages


def _infer_backend(config: Any) -> str | None:
    candidates = [
        _get_nested(config, "name"),
        _get_nested(config, "rollout.name"),
        _get_nested(config, "actor_rollout_ref.rollout.name"),
        _get_nested(config, "config.actor_rollout_ref.rollout.name"),
    ]
    for candidate in candidates:
        if candidate in ALLOWED_INFERENCE_BACKENDS:
            return str(candidate)
    return None


def _get_nested(value: Any, dotted_path: str) -> Any:
    current = value
    for part in dotted_path.split("."):
        if current is None:
            return None
        if isinstance(current, Mapping):
            current = current.get(part)
        else:
            current = getattr(current, part, None)
    return current


def _coerce_optional_int(value: Any, *, field_name: str, minimum: int | None = None) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise RepoHarnessVerlRequestMappingError(f"{field_name} must be an integer scalar")
    if isinstance(value, float) and not value.is_integer():
        raise RepoHarnessVerlRequestMappingError(f"{field_name} must be an integer scalar")
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise RepoHarnessVerlRequestMappingError(f"{field_name} must be an integer scalar") from exc
    if minimum is not None and result < minimum:
        raise RepoHarnessVerlRequestMappingError(f"{field_name} must be >= {minimum}")
    return result


def _min_positive_int(*values: Any) -> int | None:
    candidates: list[int] = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, bool):
            raise RepoHarnessVerlRequestMappingError("budget token limits must be integer scalars")
        if isinstance(value, float) and not value.is_integer():
            raise RepoHarnessVerlRequestMappingError("budget token limits must be integer scalars")
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise RepoHarnessVerlRequestMappingError("budget token limits must be integer scalars") from exc
        if parsed > 0:
            candidates.append(parsed)
    return min(candidates) if candidates else None


def _optional_string(value: Any) -> str | None:
    return None if value is None else str(value)


def _optional_safe_ref(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    text = str(value)
    try:
        validate_no_absolute_local_path(text, field_name=field_name)
    except VisibilityContractError as exc:
        raise RepoHarnessVerlRequestMappingError(str(exc)) from exc
    return text


def _normalize_safe_identifier(value: Any, *, field_name: str) -> str:
    if isinstance(value, (Mapping, list, tuple, set)):
        raise RepoHarnessVerlRequestMappingError(f"{field_name} must be a flat scalar identifier")
    text = str(value).strip()
    text = _SAFE_IDENTIFIER_REPLACEMENTS.sub("-", text).strip("-")
    if not text:
        text = "unknown"
    try:
        return validate_safe_identifier(text, field_name=field_name)
    except VisibilityContractError as exc:
        raise RepoHarnessVerlRequestMappingError(str(exc)) from exc
