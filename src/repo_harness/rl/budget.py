"""Stage 8 training budget helpers for RepoHarness episodes."""

from __future__ import annotations

from math import ceil
from typing import Any, Literal

from pydantic import Field, model_validator

from repo_harness.budget import BudgetManager
from repo_harness.config import ContextManagementConfig
from repo_harness.schema_base import StrictBaseModel

from .episode import EpisodeBudgets, RunMode

TRAINING_BUDGET_POLICY_VERSION = "repo_harness_training_budget_policy_v0"
NO_PROGRESS_HARD_STOP_POLICY_VERSION = "repo_harness_no_progress_hard_stop_v0"

NO_PROGRESS_STOP_REASONS = frozenset(
    {
        "no_progress_read_only_loop",
        "no_progress_repeated_tool_input",
        "no_progress_empty_search_loop",
        "no_progress_no_patch_after_budget",
        "no_progress_tool_error_loop",
    }
)
TIMEOUT_STOP_REASONS = frozenset(
    {
        "generation_timeout_loop",
        "max_turns",
        "max_model_calls_exceeded",
        "max_tool_calls",
        "max_test_runs",
    }
)
CONTEXT_BUDGET_STOP_REASONS = frozenset(
    {
        "context_too_large",
        "context_limit",
        "context_limit_preflight_after_autocompact",
        "context_limit_after_reactive_compact",
        "context_limit_reactive_compact_disabled",
        "auto_compact_failed_preflight",
        "reactive_compact_failed",
        "prompt_length_exceeded",
        "response_length_exceeded",
    }
)
BUDGET_HARD_STOP_REASONS = frozenset(
    {
        "max_turns",
        "max_tool_calls",
        "max_test_runs",
        "max_cost",
        "max_model_calls_exceeded",
    }
)

NO_PROGRESS_SIGNAL_TO_REASON: tuple[tuple[str, str], ...] = (
    ("long_read_only_streak", "no_progress_read_only_loop"),
    ("repeated_tool_input", "no_progress_repeated_tool_input"),
    ("empty_search_accumulation", "no_progress_empty_search_loop"),
    ("near_turn_budget_without_patch", "no_progress_no_patch_after_budget"),
    ("tool_error_loop", "no_progress_tool_error_loop"),
)


class NoProgressPolicy(StrictBaseModel):
    schema_version: str = "repo_harness_no_progress_policy_v0"
    policy_version: str = NO_PROGRESS_HARD_STOP_POLICY_VERSION
    hard_stop_enabled: bool = False
    allow_model_visible_nudge: bool = True
    allow_training_sample: bool = False
    read_only_streak_threshold: int = Field(default=10, gt=0)
    repeated_input_threshold: int = Field(default=3, gt=0)
    empty_search_threshold: int = Field(default=4, gt=0)
    near_budget_without_patch_threshold: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_no_progress_policy(self) -> "NoProgressPolicy":
        if self.hard_stop_enabled and self.allow_training_sample:
            raise ValueError("no-progress hard stop samples are not trainable in Stage 8")
        return self


class TrainingBudgetPolicy(StrictBaseModel):
    schema_version: str = "repo_harness_training_budget_policy_v0"
    policy_version: str = TRAINING_BUDGET_POLICY_VERSION
    run_mode: RunMode | None = None
    defaults_source: dict[str, str] = Field(default_factory=dict)
    max_turns: int | None = Field(default=None, gt=0)
    max_model_calls: int | None = Field(default=None, gt=0)
    max_tool_calls: int | None = Field(default=None, ge=0)
    max_wall_seconds: float | None = Field(default=None, gt=0)
    max_model_call_seconds: float | None = Field(default=None, gt=0)
    request_timeout_seconds: float | None = Field(default=None, gt=0)
    generation_timeout_seconds: float | None = Field(default=None, gt=0)
    max_output_tokens: int | None = Field(default=None, gt=0)
    max_prompt_tokens: int | None = Field(default=None, gt=0)
    max_context_tokens: int | None = Field(default=None, gt=0)
    max_tool_output_chars: int | None = Field(default=None, gt=0)
    max_tool_observation_tokens: int | None = Field(default=None, ge=0)
    max_verifier_seconds: float | None = Field(default=None, gt=0)
    max_workspace_materialization_seconds: float | None = Field(default=None, gt=0)
    provider_retry_budget: int | None = Field(default=None, ge=0)
    max_artifact_bytes: int | None = Field(default=None, gt=0)
    no_progress_policy: NoProgressPolicy = Field(default_factory=NoProgressPolicy)


class BudgetStopDecision(StrictBaseModel):
    schema_version: str = "repo_harness_budget_stop_decision_v0"
    stop_reason: str
    episode_status: Literal["no_progress", "timeout", "invalid", "infrastructure_error"]
    invalid_for_training: bool = True
    invalid_for_online_rl: bool = True
    reward_score_policy: Literal["none"] = "none"
    recorder_event_type: str


class NoProgressDecision(StrictBaseModel):
    schema_version: str = "repo_harness_no_progress_decision_v0"
    hard_stop: bool = False
    stop_reason: str | None = None
    recorder_event_type: str | None = None
    signal_keys: list[str] = Field(default_factory=list)
    thresholds: dict[str, Any] = Field(default_factory=dict)
    policy_version: str = NO_PROGRESS_HARD_STOP_POLICY_VERSION
    allow_model_visible_nudge: bool = True
    trainable: bool = False


class TrainingBudgetProjection(StrictBaseModel):
    schema_version: str = "repo_harness_training_budget_projection_v0"
    policy: TrainingBudgetPolicy
    budget_manager: BudgetManager
    context_config_overrides: dict[str, Any] = Field(default_factory=dict)
    gateway_timeout_seconds: float | None = Field(default=None, gt=0)
    sampling_params: dict[str, Any] = Field(default_factory=dict)


def build_training_budget_policy(
    budgets: EpisodeBudgets | dict[str, Any] | None = None,
    *,
    run_mode: RunMode | None = None,
) -> TrainingBudgetPolicy:
    episode_budgets = EpisodeBudgets.model_validate(budgets or {})
    training_fast = run_mode == "training_fast"
    defaults: dict[str, str] = {}

    def choose(field_name: str, default_value: Any) -> Any:
        value = getattr(episode_budgets, field_name)
        if value is not None:
            defaults[field_name] = "episode_request"
            return value
        if training_fast:
            defaults[field_name] = "training_fast_default"
            return default_value
        defaults[field_name] = "unset"
        return None

    max_turns = choose("max_turns", 12)
    max_model_calls = episode_budgets.max_model_calls
    if max_model_calls is None:
        max_model_calls = max_turns if max_turns is not None else (12 if training_fast else None)
        defaults["max_model_calls"] = (
            "derived_from_max_turns" if max_model_calls is not None else "unset"
        )
    else:
        defaults["max_model_calls"] = "episode_request"

    raw_no_progress = dict(episode_budgets.no_progress_policy)
    raw_no_progress.setdefault("hard_stop_enabled", training_fast)
    raw_no_progress.setdefault("allow_model_visible_nudge", not training_fast)
    raw_no_progress.setdefault("allow_training_sample", False)

    return TrainingBudgetPolicy(
        run_mode=run_mode,
        defaults_source=defaults,
        max_turns=max_turns,
        max_model_calls=max_model_calls,
        max_tool_calls=choose("max_tool_calls", 80),
        max_wall_seconds=episode_budgets.max_wall_seconds,
        max_model_call_seconds=episode_budgets.max_model_call_seconds,
        request_timeout_seconds=episode_budgets.request_timeout_seconds,
        generation_timeout_seconds=episode_budgets.generation_timeout_seconds,
        max_output_tokens=choose("max_output_tokens", 2048),
        max_prompt_tokens=episode_budgets.max_prompt_tokens,
        max_context_tokens=choose("max_context_tokens", 32000),
        max_tool_output_chars=(
            episode_budgets.max_tool_observation_tokens
            if episode_budgets.max_tool_observation_tokens is not None
            else (12000 if training_fast else None)
        ),
        max_tool_observation_tokens=episode_budgets.max_tool_observation_tokens,
        max_verifier_seconds=episode_budgets.max_verifier_seconds,
        max_workspace_materialization_seconds=episode_budgets.max_workspace_materialization_seconds,
        provider_retry_budget=episode_budgets.provider_retry_budget,
        max_artifact_bytes=episode_budgets.max_artifact_bytes,
        no_progress_policy=NoProgressPolicy.model_validate(raw_no_progress),
    )


def budget_manager_from_training_policy(
    policy: TrainingBudgetPolicy,
    *,
    base_manager: BudgetManager | None = None,
) -> BudgetManager:
    base = base_manager or BudgetManager(
        max_turns=policy.max_turns or 1000,
        max_tool_calls=policy.max_tool_calls if policy.max_tool_calls is not None else 1000,
        max_test_runs=1000,
        task_timeout_sec=_positive_budget_seconds(policy.max_wall_seconds, default=3600),
        command_timeout_sec=120,
        verifier_timeout_sec=_positive_budget_seconds(
            policy.max_verifier_seconds
            if policy.max_verifier_seconds is not None
            else policy.max_wall_seconds,
            default=120,
        ),
        max_tool_output_chars=policy.max_tool_output_chars or 12000,
        max_context_tokens=policy.max_context_tokens or 120000,
        max_output_tokens=policy.max_output_tokens or 4096,
        max_artifact_bytes=policy.max_artifact_bytes,
        max_model_calls=policy.max_model_calls,
    )
    updates: dict[str, Any] = {}
    for policy_field, manager_field in [
        ("max_turns", "max_turns"),
        ("max_model_calls", "max_model_calls"),
        ("max_tool_calls", "max_tool_calls"),
        ("max_output_tokens", "max_output_tokens"),
        ("max_context_tokens", "max_context_tokens"),
        ("max_tool_output_chars", "max_tool_output_chars"),
        ("max_artifact_bytes", "max_artifact_bytes"),
    ]:
        value = getattr(policy, policy_field)
        if value is not None:
            updates[manager_field] = value
    if policy.max_wall_seconds is not None:
        updates["task_timeout_sec"] = _positive_budget_seconds(policy.max_wall_seconds)
    if policy.max_verifier_seconds is not None:
        updates["verifier_timeout_sec"] = _positive_budget_seconds(policy.max_verifier_seconds)
    return base.model_copy(update=updates)


def _positive_budget_seconds(value: float | None, *, default: float | None = None) -> int:
    resolved = default if value is None else value
    if resolved is None:
        raise ValueError("positive budget seconds requires value or default")
    return max(1, int(ceil(resolved)))


def context_config_overrides_from_training_policy(policy: TrainingBudgetPolicy) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    if policy.max_context_tokens is not None:
        overrides["max_context_tokens"] = policy.max_context_tokens
    if policy.max_tool_output_chars is not None:
        overrides["max_single_tool_result_chars"] = policy.max_tool_output_chars
        overrides["max_tool_results_per_turn_chars"] = policy.max_tool_output_chars
    return overrides


def context_config_from_training_policy(
    policy: TrainingBudgetPolicy,
    *,
    base_config: ContextManagementConfig | None = None,
) -> ContextManagementConfig:
    config = base_config or ContextManagementConfig()
    overrides = context_config_overrides_from_training_policy(policy)
    if not overrides:
        return config
    return config.model_copy(update=overrides)


def build_training_budget_projection(
    budgets: EpisodeBudgets | dict[str, Any] | None = None,
    *,
    run_mode: RunMode | None = None,
    base_budget_manager: BudgetManager | None = None,
) -> TrainingBudgetProjection:
    policy = build_training_budget_policy(budgets, run_mode=run_mode)
    timeout_candidates = [
        value
        for value in [
            policy.generation_timeout_seconds,
            policy.request_timeout_seconds,
            policy.max_model_call_seconds,
        ]
        if value is not None
    ]
    sampling_params: dict[str, Any] = {}
    if policy.max_output_tokens is not None:
        sampling_params["max_output_tokens"] = policy.max_output_tokens
    return TrainingBudgetProjection(
        policy=policy,
        budget_manager=budget_manager_from_training_policy(
            policy,
            base_manager=base_budget_manager,
        ),
        context_config_overrides=context_config_overrides_from_training_policy(policy),
        gateway_timeout_seconds=min(timeout_candidates) if timeout_candidates else None,
        sampling_params=sampling_params,
    )


def map_budget_stop_to_episode_status(stop_reason: str) -> BudgetStopDecision:
    if stop_reason in NO_PROGRESS_STOP_REASONS or stop_reason == "no_progress":
        return BudgetStopDecision(
            stop_reason=stop_reason,
            episode_status="no_progress",
            recorder_event_type="no_progress_hard_stop",
        )
    if stop_reason in TIMEOUT_STOP_REASONS or "timeout" in stop_reason:
        return BudgetStopDecision(
            stop_reason=stop_reason,
            episode_status="timeout",
            recorder_event_type=recorder_event_type_for_stop_reason(stop_reason),
        )
    if stop_reason in CONTEXT_BUDGET_STOP_REASONS:
        return BudgetStopDecision(
            stop_reason=stop_reason,
            episode_status="invalid",
            recorder_event_type="context_budget_hard_stop",
        )
    return BudgetStopDecision(
        stop_reason=stop_reason,
        episode_status="infrastructure_error",
        recorder_event_type=recorder_event_type_for_stop_reason(stop_reason),
    )


def recorder_event_type_for_stop_reason(stop_reason: str) -> str:
    if stop_reason in NO_PROGRESS_STOP_REASONS or stop_reason == "no_progress":
        return "no_progress_hard_stop"
    if stop_reason == "generation_timeout_loop":
        return "generation_timeout"
    if stop_reason in CONTEXT_BUDGET_STOP_REASONS:
        return "context_budget_hard_stop"
    if stop_reason in BUDGET_HARD_STOP_REASONS:
        return "budget_hard_stop"
    return "budget_exhausted"


def decide_no_progress_hard_stop(
    summary: dict[str, Any],
    policy: NoProgressPolicy,
) -> NoProgressDecision:
    signal_keys = [
        str(signal.get("signal_key"))
        for signal in summary.get("signals", [])
        if isinstance(signal, dict) and signal.get("signal_key")
    ]
    if not policy.hard_stop_enabled or summary.get("diagnostic_status") != "no_progress_suspected":
        return NoProgressDecision(
            hard_stop=False,
            signal_keys=signal_keys,
            allow_model_visible_nudge=policy.allow_model_visible_nudge,
        )
    stop_reason = None
    for signal_key, mapped_reason in NO_PROGRESS_SIGNAL_TO_REASON:
        if signal_key in signal_keys:
            stop_reason = mapped_reason
            break
    if stop_reason is None:
        return NoProgressDecision(
            hard_stop=False,
            signal_keys=signal_keys,
            allow_model_visible_nudge=policy.allow_model_visible_nudge,
        )
    thresholds = {
        "read_only_streak_threshold": policy.read_only_streak_threshold,
        "repeated_input_threshold": policy.repeated_input_threshold,
        "empty_search_threshold": policy.empty_search_threshold,
        "near_budget_without_patch_threshold": policy.near_budget_without_patch_threshold,
    }
    return NoProgressDecision(
        hard_stop=True,
        stop_reason=stop_reason,
        recorder_event_type=recorder_event_type_for_stop_reason(stop_reason),
        signal_keys=signal_keys,
        thresholds=thresholds,
        allow_model_visible_nudge=False,
        trainable=False,
    )
