"""TrainingView 到 verl AgentLoopOutput 的转换。"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from repo_harness.rl import AuditRef, GenerationRecord, RepoHarnessEpisodeResult, TrainingView
from repo_harness.rl.training_view import validate_training_view_for_online_rl
from repo_harness.rl.visibility import FlatScalar, validate_batch_extra_fields

from .visibility import validate_agent_loop_output_extra_fields


class VerlConversionError(ValueError):
    """表示 RepoHarness training view 无法安全转换为 verl 输出。"""


VERL_AGENT_LOOP_METRIC_KEYS = frozenset(
    {
        "generate_sequences",
        "tool_calls",
        "compute_score",
        "num_preempted",
    }
)

REPO_HARNESS_AGENT_LOOP_EXTRA_FIELDS = frozenset(
    {
        "repo_harness_episode_id",
        "repo_harness_run_id",
        "repo_harness_task_id",
        "repo_harness_audit_manifest_ref",
        "repo_harness_reward_metadata_ref",
        "repo_harness_final_verifier_ref",
        "repo_harness_patch_ref",
        "repo_harness_timing_summary_ref",
        "repo_harness_resource_summary_ref",
        "repo_harness_metrics_ref",
        "repo_harness_verifier_worker_pool_id",
        "repo_harness_verifier_worker_id",
        "repo_harness_verifier_queue_wait_seconds",
        "repo_harness_status",
        "repo_harness_invalid_for_training",
        "repo_harness_invalid_reason",
        "repo_harness_invalid_for_online_rl",
        "repo_harness_llm_gateway_route",
    }
)

_AUDIT_REF_EXTRA_FIELD_MAP = {
    "manifest": "repo_harness_audit_manifest_ref",
    "artifacts_manifest": "repo_harness_audit_manifest_ref",
    "audit_manifest": "repo_harness_audit_manifest_ref",
    "reward_metadata": "repo_harness_reward_metadata_ref",
    "final_verifier": "repo_harness_final_verifier_ref",
    "patch": "repo_harness_patch_ref",
    "timing_summary": "repo_harness_timing_summary_ref",
    "resource_summary": "repo_harness_resource_summary_ref",
    "metrics": "repo_harness_metrics_ref",
}


def _load_verl_agent_loop_types() -> tuple[type[Any], type[Any]]:
    """延迟导入 verl 类型，避免 RepoHarness core 强制依赖 verl。"""

    try:
        from verl.experimental.agent_loop.agent_loop import AgentLoopMetrics, AgentLoopOutput
    except Exception as exc:  # pragma: no cover - exercised by integration environment.
        raise VerlConversionError(
            "failed_to_import_verl_agent_loop_types; install or expose reference/verl dependencies first"
        ) from exc
    return AgentLoopOutput, AgentLoopMetrics


def build_agent_loop_metrics(verl_metrics: Mapping[str, int | float] | None) -> Any:
    """把 TrainingView.verl_metrics 转成真实 verl AgentLoopMetrics。"""

    _, agent_loop_metrics_cls = _load_verl_agent_loop_types()
    metrics = dict(verl_metrics or {})
    unsupported = sorted(set(metrics) - VERL_AGENT_LOOP_METRIC_KEYS)
    if unsupported:
        raise VerlConversionError(f"unsupported_verl_agent_loop_metrics: {unsupported}")
    return agent_loop_metrics_cls(**metrics)


def project_audit_refs_for_extra_fields(
    audit_ref: AuditRef | None,
    *,
    base_extra_fields: Mapping[str, FlatScalar] | None = None,
) -> dict[str, FlatScalar]:
    """把结构化 AuditRef 投影成 batch 可传播的 opaque refs。"""

    extra_fields: dict[str, FlatScalar] = dict(base_extra_fields or {})
    if audit_ref is None:
        return validate_agent_loop_output_extra_fields(extra_fields)

    extra_fields.setdefault("repo_harness_episode_id", audit_ref.episode_id)
    extra_fields.setdefault("repo_harness_run_id", audit_ref.run_id)
    extra_fields.setdefault("repo_harness_task_id", audit_ref.task_id)
    for audit_key, extra_key in _AUDIT_REF_EXTRA_FIELD_MAP.items():
        ref = audit_ref.important_artifact_refs.get(audit_key)
        if ref is not None:
            extra_fields.setdefault(extra_key, ref)

    return validate_agent_loop_output_extra_fields(extra_fields)


def project_generation_records_route(generation_records: Iterable[GenerationRecord | Mapping[str, Any]]) -> str:
    """从 generation_records 投影 route，并要求所有 generation record 都是 route=verl。"""

    records = [
        record if isinstance(record, GenerationRecord) else GenerationRecord.model_validate(record)
        for record in generation_records
    ]
    if not records:
        raise VerlConversionError("missing_generation_records_for_route_projection")
    routes = {record.gateway_route for record in records}
    if routes != {"verl"}:
        raise VerlConversionError("generation_records_route_must_all_be_verl")
    return "verl"


def training_view_with_projected_route(
    training_view: TrainingView | Mapping[str, Any],
    generation_records: Iterable[GenerationRecord | Mapping[str, Any]],
) -> TrainingView:
    """如果 TrainingView 缺少 route，则从全量 generation_records 安全投影 route。"""

    view = training_view if isinstance(training_view, TrainingView) else TrainingView.model_validate(training_view)
    route = project_generation_records_route(generation_records)
    existing_route = view.extra_fields.get("repo_harness_llm_gateway_route")
    if existing_route is not None and existing_route != route:
        raise VerlConversionError("training_view_route_mismatch_generation_records")
    return view.model_copy(update={"extra_fields": {**view.extra_fields, "repo_harness_llm_gateway_route": route}})


def _validate_rollout_lengths(
    view: TrainingView,
    *,
    rollout_prompt_length: int | None,
    rollout_response_length: int | None,
) -> None:
    prompt_limit = rollout_prompt_length or view.rollout_limits.prompt_length
    response_limit = rollout_response_length or view.rollout_limits.response_length
    if len(view.prompt_ids) > prompt_limit:
        raise VerlConversionError("prompt_length_exceeded")
    if len(view.response_ids) > response_limit:
        raise VerlConversionError("response_length_exceeded")


def _validate_extra_field_allowlist(extra_fields: Mapping[str, Any]) -> None:
    unknown = sorted(set(extra_fields) - REPO_HARNESS_AGENT_LOOP_EXTRA_FIELDS)
    if unknown:
        raise VerlConversionError(f"unsupported_agent_loop_extra_fields: {unknown}")


def training_view_to_agent_loop_output(
    training_view: TrainingView | Mapping[str, Any],
    *,
    audit_ref: AuditRef | None = None,
    formal_online_rl: bool = True,
    rollout_prompt_length: int | None = None,
    rollout_response_length: int | None = None,
) -> Any:
    """把 RepoHarness TrainingView 转换成真实 verl AgentLoopOutput。"""

    view = training_view if isinstance(training_view, TrainingView) else TrainingView.model_validate(training_view)
    if formal_online_rl:
        try:
            view = validate_training_view_for_online_rl(view, require_explicit_eligibility=True)
        except ValueError as exc:
            raise VerlConversionError(str(exc)) from exc
    _validate_rollout_lengths(
        view,
        rollout_prompt_length=rollout_prompt_length,
        rollout_response_length=rollout_response_length,
    )

    extra_fields = project_audit_refs_for_extra_fields(audit_ref, base_extra_fields=view.extra_fields)
    _validate_extra_field_allowlist(extra_fields)
    validate_batch_extra_fields(extra_fields)

    agent_loop_output_cls, _ = _load_verl_agent_loop_types()
    return agent_loop_output_cls(
        prompt_ids=list(view.prompt_ids),
        response_ids=list(view.response_ids),
        response_mask=list(view.response_mask),
        response_logprobs=list(view.response_logprobs) if view.response_logprobs is not None else None,
        reward_score=view.reward_score,
        num_turns=view.num_turns or 0,
        metrics=build_agent_loop_metrics(view.verl_metrics),
        extra_fields=extra_fields,
    )


def episode_result_to_agent_loop_output(
    episode_result: RepoHarnessEpisodeResult | Mapping[str, Any],
    *,
    formal_online_rl: bool = True,
    rollout_prompt_length: int | None = None,
    rollout_response_length: int | None = None,
) -> Any:
    """把 RepoHarnessEpisodeResult 的 training_view 转换成真实 verl AgentLoopOutput。"""

    result = (
        episode_result
        if isinstance(episode_result, RepoHarnessEpisodeResult)
        else RepoHarnessEpisodeResult.model_validate(episode_result)
    )
    view = result.training_view
    if "repo_harness_llm_gateway_route" not in view.extra_fields:
        view = training_view_with_projected_route(view, result.generation_records)
    elif result.generation_records:
        project_generation_records_route(result.generation_records)
    return training_view_to_agent_loop_output(
        view,
        audit_ref=result.audit_ref,
        formal_online_rl=formal_online_rl,
        rollout_prompt_length=rollout_prompt_length,
        rollout_response_length=rollout_response_length,
    )
