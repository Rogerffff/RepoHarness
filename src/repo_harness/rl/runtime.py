"""Stage 2 async episode runtime facade."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Literal, TypeVar

from repo_harness.model_client.schemas import ModelCallEvent, ModelMessage, ModelRequestContext, ModelResponse
from repo_harness.schema_base import stable_hash
from repo_harness.tools.schemas import ToolCall
from repo_harness.trajectory import RecorderProfile
from repo_harness.verifier import VerifierJob, VerifierJobResult, VerifierResult, VerifierWorkerPool

from .episode import (
    AuditDiagnostic,
    BudgetConsumption,
    RepoHarnessEpisodeRequest,
    RepoHarnessEpisodeResult,
    VerifierSummary,
)
from .budget import CONTEXT_BUDGET_STOP_REASONS, NO_PROGRESS_STOP_REASONS
from .gateway import LLMGateway, LLMGatewayRequest, LLMGatewayResponse
from .reward_boundary import Stage7RewardBoundaryResult, build_stage7_reward_boundary
from .resources import (
    ResourceConcurrencyPolicy,
    ResourceLeaseError,
    ResourceLeaseHandle,
    ResourceLeaseManager,
    combine_cleanup_status,
)
from .timing import ResourceSummary, TimingSummary, build_timing_summary
from .training_view import AuditRef, ResponseSpan, RolloutLimits, TrainingView
from .visibility import PROVIDER_ROUTES, VisibilityContractError, validate_no_absolute_local_path

CleanupCallback = Callable[[], None | Awaitable[None]]
TaskPathResolver = Callable[[RepoHarnessEpisodeRequest], str | Path | None]
FinalVerifierCallable = Callable[[], VerifierResult]
T = TypeVar("T")
EpisodeStatusName = Literal[
    "succeeded",
    "failed",
    "invalid",
    "invalid_task",
    "infrastructure_error",
    "cancelled",
    "timeout",
    "no_progress",
]


class InvalidTaskError(ValueError):
    """Raised when runtime-only task resolution fails before model generation."""


TIMEOUT_REASON_MARKERS = ("timeout", "timed_out", "deadline_exceeded")


@dataclass(frozen=True)
class RepoHarnessRuntimeOptions:
    """Runtime-only local execution options.

    These fields may contain local paths or callables, so they deliberately stay
    outside RepoHarnessEpisodeRequest, TrainingView, and future trainer batches.
    """

    config_path: str | Path | None = None
    output_dir: str | Path | None = None
    project_root: str | Path | None = None
    task_path_resolver: TaskPathResolver | None = None
    require_resolved_task_path: bool = False
    require_runner_paths: bool = False
    executor_max_workers: int = 1
    episode_timeout_seconds: float | None = None
    cleanup_callback: CleanupCallback | None = None
    default_success_reward: float = 1.0
    default_failure_reward: float = 0.0
    minimal_final_verifier_status: Literal["accepted", "rejected"] = "accepted"
    final_verifier_callable: FinalVerifierCallable | None = None
    verifier_worker_pool: VerifierWorkerPool | None = None
    resource_concurrency_policy: ResourceConcurrencyPolicy | None = None
    resource_lease_manager: ResourceLeaseManager | None = None
    execution_mode: str = "minimal_gateway"

    def __post_init__(self) -> None:
        if self.executor_max_workers < 1:
            raise ValueError("executor_max_workers must be >= 1")
        if self.episode_timeout_seconds is not None and self.episode_timeout_seconds <= 0:
            raise ValueError("episode_timeout_seconds must be > 0")


@dataclass(frozen=True)
class RuntimeResolvedInputs:
    task_path: str | None
    config_path: str | None
    output_dir: str | None


@dataclass
class GatewayCallAccounting:
    request_submitted: bool = False
    model_call_seconds: float = 0.0


def map_episode_status(
    *,
    final_verifier_status: str | None = None,
    baseline_status: str | None = None,
    run_outcome: str | None = None,
    agent_stop_reason: str | None = None,
    provider_error_type: str | None = None,
    infrastructure_error: bool = False,
    invalid_task: bool = False,
    timeout: bool = False,
    cancelled: bool = False,
) -> EpisodeStatusName:
    """Map existing runner facts to the Stage 2 episode result status set."""

    if cancelled:
        return "cancelled"
    if (
        timeout
        or _is_timeout_reason(final_verifier_status)
        or _is_timeout_reason(provider_error_type)
        or _is_timeout_reason(agent_stop_reason)
    ):
        return "timeout"
    if agent_stop_reason in CONTEXT_BUDGET_STOP_REASONS or provider_error_type in CONTEXT_BUDGET_STOP_REASONS:
        return "invalid"
    if invalid_task or run_outcome in {"invalid_task", "flaky_task"} or baseline_status in {"invalid", "flaky"}:
        return "invalid_task"
    if infrastructure_error or final_verifier_status == "error" or provider_error_type:
        return "infrastructure_error"
    if agent_stop_reason in NO_PROGRESS_STOP_REASONS or agent_stop_reason in {"no_progress", "stalled", "max_no_progress"}:
        return "no_progress"
    if agent_stop_reason in {"generation_timeout_loop", "max_turns", "max_model_calls_exceeded", "max_tool_calls", "max_test_runs"}:
        return "timeout"
    if final_verifier_status == "accepted" or run_outcome == "success":
        return "succeeded"
    if final_verifier_status in {"rejected", "failed"} or run_outcome == "failed":
        return "failed"
    return "infrastructure_error"


class LLMGatewayModelClientAdapter:
    """Bridge the legacy synchronous ModelClient protocol to LLMGateway."""

    def __init__(
        self,
        *,
        llm_gateway: LLMGateway,
        episode_id: str,
        route: str,
        inference_backend: str | None = None,
    ) -> None:
        self.llm_gateway = llm_gateway
        self.episode_id = episode_id
        self.route = route
        self.inference_backend = inference_backend

    def generate(self, request: ModelRequestContext, recorder: Any) -> ModelResponse:
        gateway_request = self.to_gateway_request(request, recorder=recorder)
        response = _run_gateway_turn_blocking(self.llm_gateway, gateway_request)
        return self.to_model_response(request, response)

    def to_gateway_request(self, request: ModelRequestContext, *, recorder: Any = None) -> LLMGatewayRequest:
        recorder_policy = {
            "raw_request_logging_policy": request.raw_request_logging_policy,
            "retry_policy": request.retry_policy,
        }
        recorder_profile = getattr(recorder, "recorder_profile", None)
        if recorder_profile is not None:
            recorder_policy = {
                **RecorderProfile.model_validate(recorder_profile).model_dump(mode="json"),
                **recorder_policy,
            }
        return LLMGatewayRequest(
            route=self.route,  # type: ignore[arg-type]
            inference_backend=self.inference_backend,  # type: ignore[arg-type]
            run_id=request.run_id,
            task_id=request.task_id,
            episode_id=self.episode_id,
            model_call_id=request.model_call_id,
            turn=request.turn,
            context_revision=request.context_revision,
            messages=request.prepared_messages,
            tools=request.allowed_tool_definitions,
            sampling_params=request.generation_config,
            provider_options=request.provider_options.model_dump(mode="json"),
            tokenizer_policy={
                "provider_request_token_estimate": request.provider_request_token_estimate,
                "provider_request_token_estimate_breakdown": request.provider_request_token_estimate_breakdown,
                "context_budget_facts": request.context_budget_facts,
            },
            timeout_seconds=request.request_timeout_seconds,
            budget_state=request.budget_state,
            recorder_policy=recorder_policy,
            visibility_policy={
                "provider_message_format": request.provider_message_format,
                "context_truncation_facts": request.context_truncation_facts,
                "omitted_context_facts": request.omitted_context_facts,
            },
            tracing={
                "scaffold_id": request.scaffold_id,
                "scaffold_phase": request.scaffold_phase,
                "model_input_hash": request.model_input_hash,
            },
        )

    def to_model_response(self, request: ModelRequestContext, response: LLMGatewayResponse) -> ModelResponse:
        tool_calls = [_coerce_tool_call(call, turn=request.turn) for call in response.tool_calls]
        assistant_payload = dict(response.assistant_message)
        assistant_payload.setdefault("role", "assistant")
        if tool_calls:
            assistant_payload["tool_calls"] = [call.model_dump(mode="json") for call in tool_calls]
        assistant = ModelMessage.model_validate(assistant_payload)
        usage = dict(response.usage)
        input_tokens = int(usage.get("input_tokens", len(response.prompt_ids)))
        output_tokens = int(usage.get("output_tokens", len(response.output_token_ids)))
        terminal_error_type = None
        if response.error:
            terminal_error_type = "llm_gateway_error"
        event = ModelCallEvent(
            model_call_id=request.model_call_id,
            provider=response.route,
            model_id=request.provider_options.model_id,
            provider_request_id=response.provider_request_id,
            context_revision=request.context_revision,
            prepared_messages_ref=request.prepared_messages_ref,
            model_input_hash=request.model_input_hash,
            provider_message_format=request.provider_message_format,
            tool_schema_hash=stable_hash(request.allowed_tool_definitions),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=int(usage.get("cached_tokens", 0)),
            duration_ms=response.duration_ms or 0,
            request_timeout_seconds=request.request_timeout_seconds,
            request_timeout_policy_facts=request.request_timeout_policy_facts,
            terminal_error_type=terminal_error_type,
            model_error_type=terminal_error_type,
        )
        return ModelResponse(
            assistant_message=assistant,
            tool_calls=tool_calls,
            token_usage={"input_tokens": input_tokens, "output_tokens": output_tokens},
            finish_reason=response.stop_reason,
            model_error_type=terminal_error_type,
            provider_request_id=response.provider_request_id,
            model_call_event=event,
        )


class RepoHarnessRuntime:
    """Reusable async episode runtime facade for Stage 2."""

    def __init__(self, options: RepoHarnessRuntimeOptions | None = None) -> None:
        self.options = options or RepoHarnessRuntimeOptions()
        self.resource_lease_manager = self.options.resource_lease_manager
        if self.resource_lease_manager is None and self.options.resource_concurrency_policy is not None:
            self.resource_lease_manager = ResourceLeaseManager(self.options.resource_concurrency_policy)

    async def run_episode(
        self,
        request: RepoHarnessEpisodeRequest,
        *,
        llm_gateway: LLMGateway,
    ) -> RepoHarnessEpisodeResult:
        started = perf_counter()
        parsed_request = RepoHarnessEpisodeRequest.model_validate(request)
        response: LLMGatewayResponse | None = None
        status: EpisodeStatusName = "infrastructure_error"
        status_reason: str | None = None
        diagnostics: list[AuditDiagnostic] = []
        gateway_accounting = GatewayCallAccounting()
        reward_boundary: Stage7RewardBoundaryResult | None = None
        resource_handle: ResourceLeaseHandle | None = None

        try:
            self.resolve_runner_inputs(parsed_request)
            resource_handle = await self._acquire_episode_resources(parsed_request)
            timeout_seconds = self._episode_timeout_seconds(parsed_request)
            if timeout_seconds is None:
                response = await self._generate_minimal_turn(
                    parsed_request,
                    llm_gateway,
                    resource_handle=resource_handle,
                    gateway_accounting=gateway_accounting,
                )
            else:
                response = await asyncio.wait_for(
                    self._generate_minimal_turn(
                        parsed_request,
                        llm_gateway,
                        resource_handle=resource_handle,
                        gateway_accounting=gateway_accounting,
                    ),
                    timeout=timeout_seconds,
                )
            reward_boundary = await self._stage7_reward_boundary(parsed_request)
            if reward_boundary is None:
                status = self._status_from_minimal_verifier()
            else:
                status = reward_boundary.status
                status_reason = reward_boundary.status_reason
        except asyncio.CancelledError:
            status = "cancelled"
            status_reason = "runtime_cancelled"
            diagnostics.append(AuditDiagnostic(code="runtime_cancelled", message="episode coroutine was cancelled"))
        except TimeoutError:
            status = "timeout"
            status_reason = "episode_timeout"
            diagnostics.append(AuditDiagnostic(code="episode_timeout", message="episode timeout expired"))
        except InvalidTaskError as exc:
            status = "invalid_task"
            status_reason = "invalid_task"
            diagnostics.append(AuditDiagnostic(code="invalid_task", message=str(exc)))
        except ResourceLeaseError as exc:
            status = exc.episode_status
            status_reason = exc.status_reason
            if (
                resource_handle is not None
                and exc.status_reason == "gateway_route_queue_timeout"
                and exc.queue_wait_seconds is not None
            ):
                resource_handle.lease.queue_wait_seconds_by_resource["gateway_route"] = (
                    resource_handle.lease.queue_wait_seconds_by_resource.get("gateway_route", 0.0)
                    + exc.queue_wait_seconds
                )
            diagnostics.append(AuditDiagnostic(code=exc.status_reason, message=str(exc)))
        except Exception as exc:  # pragma: no cover - exercised by tests through concrete failures.
            status = "infrastructure_error"
            status_reason = "infrastructure_error"
            diagnostics.append(AuditDiagnostic(code=exc.__class__.__name__, message=str(exc)))

        cleanup_started = perf_counter()
        cleanup_status, cleanup_diagnostic = await self._cleanup_protected()
        if cleanup_diagnostic is not None and cleanup_diagnostic.code == "cleanup_cancelled":
            status = "cancelled"
            status_reason = "runtime_cancelled"
        resource_cleanup_status, resource_cleanup_diagnostics = await self._release_episode_resources_protected(
            resource_handle
        )
        cleanup_status = combine_cleanup_status(cleanup_status, resource_cleanup_status)
        cleanup_seconds = perf_counter() - cleanup_started
        if cleanup_diagnostic is not None:
            diagnostics.append(cleanup_diagnostic)
        diagnostics.extend(resource_cleanup_diagnostics)

        elapsed = perf_counter() - started
        if response is not None:
            return self._result_from_gateway_response(
                parsed_request,
                response,
                status=status,
                status_reason=status_reason,
                diagnostics=diagnostics,
                elapsed_seconds=elapsed,
                model_call_seconds=gateway_accounting.model_call_seconds,
                cleanup_seconds=cleanup_seconds,
                cleanup_status=cleanup_status,
                reward_boundary=reward_boundary,
                resource_handle=resource_handle,
            )
        return self._terminal_result(
            parsed_request,
            status=status,
            status_reason=status_reason or status,
            diagnostics=diagnostics,
            elapsed_seconds=elapsed,
            model_call_seconds=gateway_accounting.model_call_seconds,
            gateway_request_submitted=gateway_accounting.request_submitted,
            cleanup_seconds=cleanup_seconds,
            cleanup_status=cleanup_status,
            resource_handle=resource_handle,
        )

    def resolve_runner_inputs(self, request: RepoHarnessEpisodeRequest) -> RuntimeResolvedInputs:
        task_path: str | None = request.task_ref.task_path
        if task_path:
            try:
                validate_no_absolute_local_path(task_path, field_name="task_ref.task_path")
            except VisibilityContractError as exc:
                raise InvalidTaskError(str(exc)) from exc
        if task_path is None and self.options.task_path_resolver is not None:
            resolved = self.options.task_path_resolver(request)
            task_path = None if resolved is None else str(resolved)
        config_path = None if self.options.config_path is None else str(self.options.config_path)
        output_dir = None if self.options.output_dir is None else str(self.options.output_dir)
        if self.options.require_resolved_task_path and not task_path:
            raise InvalidTaskError("task_path could not be resolved for Stage 2 runtime")
        if self.options.require_runner_paths and (not config_path or not output_dir):
            raise InvalidTaskError("config_path and output_dir are required for legacy runner bridge")
        return RuntimeResolvedInputs(task_path=task_path, config_path=config_path, output_dir=output_dir)

    async def _generate_minimal_turn(
        self,
        request: RepoHarnessEpisodeRequest,
        llm_gateway: LLMGateway,
        *,
        resource_handle: ResourceLeaseHandle | None = None,
        gateway_accounting: GatewayCallAccounting,
    ) -> LLMGatewayResponse:
        gateway_request = LLMGatewayRequest(
            route=request.llm_gateway_route,
            inference_backend=request.inference_backend,
            run_id=request.run_id,
            task_id=request.task_id,
            episode_id=request.episode_id,
            model_call_id=f"{request.episode_id}-turn-0",
            turn=0,
            context_revision=0,
            messages=request.raw_prompt,
            tools=[],
            sampling_params={
                "max_output_tokens": request.budgets.max_output_tokens,
                "reasoning_effort": request.budgets.reasoning_effort,
                "thinking_mode": request.budgets.thinking_mode,
            },
            provider_options={},
            tokenizer_policy={
                "max_prompt_tokens": request.budgets.max_prompt_tokens,
                "max_total_tokens": request.budgets.max_total_tokens,
                "max_context_tokens": request.budgets.max_context_tokens,
            },
            timeout_seconds=request.budgets.generation_timeout_seconds or request.budgets.request_timeout_seconds,
            budget_state=request.budgets.model_dump(mode="json", exclude_none=True),
            recorder_policy=RecorderProfile.for_run_mode(request.run_mode).model_dump(mode="json"),
            visibility_policy=request.visibility_policy.model_dump(mode="json"),
            tracing={"runtime_mode": self.options.execution_mode},
        )
        if self.resource_lease_manager is None or resource_handle is None:
            call_started = perf_counter()
            gateway_accounting.request_submitted = True
            try:
                return await llm_gateway.generate_turn(gateway_request)
            finally:
                gateway_accounting.model_call_seconds += perf_counter() - call_started
        async with self.resource_lease_manager.route_call(
            handle=resource_handle,
            route=request.llm_gateway_route,
        ):
            call_started = perf_counter()
            gateway_accounting.request_submitted = True
            try:
                return await llm_gateway.generate_turn(gateway_request)
            finally:
                gateway_accounting.model_call_seconds += perf_counter() - call_started

    def _result_from_gateway_response(
        self,
        request: RepoHarnessEpisodeRequest,
        response: LLMGatewayResponse,
        *,
        status: EpisodeStatusName,
        status_reason: str | None,
        diagnostics: list[AuditDiagnostic],
        elapsed_seconds: float,
        model_call_seconds: float,
        cleanup_seconds: float,
        cleanup_status: str,
        reward_boundary: Stage7RewardBoundaryResult | None = None,
        resource_handle: ResourceLeaseHandle | None = None,
    ) -> RepoHarnessEpisodeResult:
        invalid_reason = self._response_invalid_reason(request, response)
        response_error_reason = _response_error_reason(response)
        if invalid_reason in {"gateway_route_mismatch", "gateway_inference_backend_mismatch"}:
            status = "infrastructure_error"
            status_reason = invalid_reason
            invalid_for_training = True
            invalid_for_online_rl = True
        elif response_error_reason is not None:
            status = "timeout" if _is_timeout_reason(response_error_reason) else "infrastructure_error"
            status_reason = response_error_reason
            invalid_for_training = True
            invalid_for_online_rl = True
        elif invalid_reason in {"empty_response", "prompt_length_exceeded", "response_length_exceeded"}:
            status = "invalid"
            status_reason = invalid_reason
            invalid_for_training = True
            invalid_for_online_rl = True
        else:
            invalid_for_training = _status_invalid_for_training(status)
            invalid_for_online_rl = _status_invalid_for_online_rl(status) or invalid_reason is not None
            status_reason = status_reason or invalid_reason

        if reward_boundary is not None and invalid_reason is None and response_error_reason is None:
            invalid_for_training = reward_boundary.invalid_for_training
            invalid_for_online_rl = reward_boundary.invalid_for_online_rl or invalid_for_online_rl
            status = reward_boundary.status
            status_reason = reward_boundary.status_reason or status_reason

        diagnostics.extend(self._diagnostics_for_invalid_reason(request, response, status_reason))
        timing_summary = self._timing_summary(
            elapsed_seconds=elapsed_seconds,
            model_call_seconds=model_call_seconds,
            cleanup_seconds=cleanup_seconds,
            model_call_count=1,
            response=response,
            verifier_queue_wait_seconds=(
                0.0 if reward_boundary is None else reward_boundary.verifier_queue_wait_seconds
            ),
            final_verifier_seconds=0.0 if reward_boundary is None else reward_boundary.final_verifier_seconds,
            reward_compute_seconds=0.0 if reward_boundary is None else reward_boundary.reward_compute_seconds,
            verifier_call_count=0 if reward_boundary is None else 1,
            resource_handle=resource_handle,
        )
        budget_consumption = self._budget_consumption(
            request,
            response,
            stop_reason=status_reason,
            timing_summary=timing_summary,
        )
        if reward_boundary is not None and not invalid_for_training and not invalid_for_online_rl:
            reward_score = reward_boundary.reward_score
        else:
            reward_score = self._reward_score(status, invalid_for_training, invalid_for_online_rl)
        training_view = self._training_view_from_response(
            request,
            response,
            status=status,
            reward_score=reward_score,
            invalid_for_training=invalid_for_training,
            invalid_for_online_rl=invalid_for_online_rl,
            invalid_reason=status_reason,
            stage7_extra_fields=None if reward_boundary is None else reward_boundary.extra_fields,
        )
        generation_records = [response.to_generation_record(turn=0, context_revision=0)]
        return RepoHarnessEpisodeResult(
            episode_id=request.episode_id,
            run_id=request.run_id,
            task_id=request.task_id,
            status=status,
            status_reason=status_reason,
            invalid_for_training=invalid_for_training,
            invalid_for_online_rl=invalid_for_online_rl,
            attempted_reward_score=reward_score,
            budget_consumption=budget_consumption,
            training_view=training_view,
            audit_ref=self._audit_ref(request, reward_boundary=reward_boundary),
            audit_diagnostics=diagnostics,
            reward=None if reward_boundary is None else reward_boundary.reward_summary,
            verifier_summary=(
                self._verifier_summary(status) if reward_boundary is None else reward_boundary.verifier_summary
            ),
            generation_records=generation_records,
            timing_summary=timing_summary,
            resource_summary=self._resource_summary(
                request,
                cleanup_status=cleanup_status,
                reward_boundary=reward_boundary,
                resource_handle=resource_handle,
            ),
        )

    def _terminal_result(
        self,
        request: RepoHarnessEpisodeRequest,
        *,
        status: EpisodeStatusName,
        status_reason: str,
        diagnostics: list[AuditDiagnostic],
        elapsed_seconds: float,
        model_call_seconds: float,
        cleanup_seconds: float,
        cleanup_status: str,
        gateway_request_submitted: bool = False,
        resource_handle: ResourceLeaseHandle | None = None,
    ) -> RepoHarnessEpisodeResult:
        timing_summary = self._timing_summary(
            elapsed_seconds=elapsed_seconds,
            model_call_seconds=model_call_seconds,
            cleanup_seconds=cleanup_seconds,
            model_call_count=1 if gateway_request_submitted else 0,
            resource_handle=resource_handle,
        )
        training_view = TrainingView(
            online_rl_eligible=False,
            prompt_ids=[],
            response_ids=[],
            response_mask=[],
            response_logprobs=[],
            response_spans=[],
            reward_score=None,
            num_turns=0,
            extra_fields=self._extra_fields(
                request,
                status=status,
                invalid_for_training=True,
                invalid_for_online_rl=True,
                invalid_reason=status_reason,
            ),
        )
        return RepoHarnessEpisodeResult(
            episode_id=request.episode_id,
            run_id=request.run_id,
            task_id=request.task_id,
            status=status,
            status_reason=status_reason,
            invalid_for_training=True,
            invalid_for_online_rl=True,
            budget_consumption=BudgetConsumption(
                max_turns=request.budgets.max_turns,
                used_turns=0,
                max_wall_seconds=request.budgets.max_wall_seconds,
                used_wall_seconds=timing_summary.rollout_wall_seconds,
                max_model_calls=request.budgets.max_model_calls,
                used_model_calls=1 if gateway_request_submitted else 0,
                max_model_call_seconds=request.budgets.generation_timeout_seconds
                or request.budgets.max_model_call_seconds,
                used_model_call_seconds=timing_summary.model_call_seconds,
                max_tool_calls=request.budgets.max_tool_calls,
                used_tool_calls=0,
                max_artifact_bytes=request.budgets.max_artifact_bytes,
                used_artifact_bytes=timing_summary.artifact_bytes_written,
                stop_reason=status_reason,
                rollout_response_length=request.budgets.max_output_tokens,
                actual_response_length=0,
            ),
            training_view=training_view,
            audit_ref=self._audit_ref(request, reward_boundary=None),
            audit_diagnostics=diagnostics,
            timing_summary=timing_summary,
            resource_summary=self._resource_summary(
                request,
                cleanup_status=cleanup_status,
                reward_boundary=None,
                resource_handle=resource_handle,
            ),
        )

    def _training_view_from_response(
        self,
        request: RepoHarnessEpisodeRequest,
        response: LLMGatewayResponse,
        *,
        status: EpisodeStatusName,
        reward_score: float | None,
        invalid_for_training: bool,
        invalid_for_online_rl: bool,
        invalid_reason: str | None,
        stage7_extra_fields: dict[str, str | int | float | bool | None] | None = None,
    ) -> TrainingView:
        response_ids = list(response.output_token_ids)
        global_steps = response.global_steps or 0
        min_global_steps = response.min_global_steps if response.min_global_steps is not None else global_steps
        max_global_steps = response.max_global_steps if response.max_global_steps is not None else global_steps
        spans: list[ResponseSpan] = []
        if response_ids:
            spans.append(
                ResponseSpan(
                    start=0,
                    end=len(response_ids),
                    source_type="assistant_generation",
                    model_call_id=response.model_call_id,
                    artifact_ref=f"rh://model-call/{response.model_call_id}/assistant-output",
                    response_mask_value=1,
                    logprob_policy=(
                        "gateway_output_logprobs"
                        if response.output_logprobs is not None
                        else "missing_logprobs_invalid_for_online_rl"
                    ),
                    policy_version=response.policy_version,
                    global_steps=global_steps,
                    min_global_steps=min_global_steps,
                    max_global_steps=max_global_steps,
                )
            )
        return TrainingView(
            online_rl_eligible=not invalid_for_training and not invalid_for_online_rl,
            rollout_limits=RolloutLimits(
                prompt_length=max(request.budgets.max_prompt_tokens or 10**9, len(response.prompt_ids)),
                response_length=request.budgets.max_output_tokens or 10**9,
            ),
            prompt_ids=list(response.prompt_ids),
            response_ids=response_ids,
            response_mask=list(response.response_mask),
            response_logprobs=None if response.output_logprobs is None else list(response.output_logprobs),
            response_spans=spans,
            reward_score=reward_score,
            num_turns=1,
            extra_fields=self._extra_fields(
                request,
                gateway_route=response.route,
                status=status,
                invalid_for_training=invalid_for_training,
                invalid_for_online_rl=invalid_for_online_rl,
                invalid_reason=invalid_reason,
                extra_fields=stage7_extra_fields,
            ),
        )

    def _response_invalid_reason(self, request: RepoHarnessEpisodeRequest, response: LLMGatewayResponse) -> str | None:
        if response.route != request.llm_gateway_route:
            return "gateway_route_mismatch"
        if response.inference_backend != request.inference_backend:
            return "gateway_inference_backend_mismatch"
        error_reason = _response_error_reason(response)
        if error_reason is not None:
            return error_reason
        if not response.output_token_ids:
            return "empty_response"
        if request.budgets.max_prompt_tokens is not None and len(response.prompt_ids) > request.budgets.max_prompt_tokens:
            return "prompt_length_exceeded"
        if request.budgets.max_output_tokens is not None and len(response.output_token_ids) > request.budgets.max_output_tokens:
            return "response_length_exceeded"
        if request.llm_gateway_route in PROVIDER_ROUTES or response.route in PROVIDER_ROUTES:
            return "provider_route_invalid_for_online_rl"
        if request.llm_gateway_route != "verl" or response.route != "verl":
            return "non_verl_route_invalid_for_online_rl"
        if response.output_logprobs is None:
            return "missing_response_logprobs"
        return None

    def _reward_score(
        self,
        status: EpisodeStatusName,
        invalid_for_training: bool,
        invalid_for_online_rl: bool,
    ) -> float | None:
        if invalid_for_training:
            return None
        if invalid_for_online_rl and status == "succeeded":
            return None
        if status == "succeeded":
            return self.options.default_success_reward
        if status == "failed":
            return self.options.default_failure_reward
        return None

    def _budget_consumption(
        self,
        request: RepoHarnessEpisodeRequest,
        response: LLMGatewayResponse,
        *,
        stop_reason: str | None,
        timing_summary: TimingSummary,
    ) -> BudgetConsumption:
        return BudgetConsumption(
            max_turns=request.budgets.max_turns,
            used_turns=1,
            max_wall_seconds=request.budgets.max_wall_seconds,
            used_wall_seconds=timing_summary.rollout_wall_seconds,
            max_model_calls=request.budgets.max_model_calls,
            used_model_calls=1,
            max_model_call_seconds=request.budgets.generation_timeout_seconds
            or request.budgets.max_model_call_seconds,
            used_model_call_seconds=timing_summary.model_call_seconds,
            max_tool_calls=request.budgets.max_tool_calls,
            used_tool_calls=0,
            max_artifact_bytes=request.budgets.max_artifact_bytes,
            used_artifact_bytes=timing_summary.artifact_bytes_written,
            stop_reason=stop_reason,
            rollout_response_length=request.budgets.max_output_tokens,
            actual_response_length=len(response.output_token_ids),
        )

    def _diagnostics_for_invalid_reason(
        self,
        request: RepoHarnessEpisodeRequest,
        response: LLMGatewayResponse,
        invalid_reason: str | None,
    ) -> list[AuditDiagnostic]:
        if invalid_reason == "prompt_length_exceeded":
            return [
                AuditDiagnostic(
                    code="prompt_length_exceeded",
                    message=(
                        "gateway prompt_ids length "
                        f"{len(response.prompt_ids)} exceeded max_prompt_tokens {request.budgets.max_prompt_tokens}"
                    ),
                )
            ]
        if invalid_reason == "response_length_exceeded":
            return [
                AuditDiagnostic(
                    code="response_length_exceeded",
                    message=(
                        "gateway output_token_ids length "
                        f"{len(response.output_token_ids)} exceeded max_output_tokens {request.budgets.max_output_tokens}"
                    ),
                )
            ]
        if response.error is not None and invalid_reason is not None:
            return [
                AuditDiagnostic(
                    code=invalid_reason,
                    message=f"LLMGatewayResponse.error reported: {response.error}",
                )
            ]
        return []

    def _status_from_minimal_verifier(self) -> EpisodeStatusName:
        if self.options.minimal_final_verifier_status == "accepted":
            return "succeeded"
        return "failed"

    async def _stage7_reward_boundary(
        self,
        request: RepoHarnessEpisodeRequest,
    ) -> Stage7RewardBoundaryResult | None:
        final_verifier_callable = self.options.final_verifier_callable
        if final_verifier_callable is None:
            return None
        job = VerifierJob(
            job_id=f"{request.episode_id}-final-verifier",
            run_id=request.run_id,
            episode_id=request.episode_id,
            task_id=request.task_id,
            verifier_stage="final",
            callable=final_verifier_callable,
            timeout_seconds=request.budgets.max_verifier_seconds,
        )
        pool_result = await self._run_stage7_verifier_job(job)
        reward_started = perf_counter()
        boundary = build_stage7_reward_boundary(
            final_verifier=pool_result.verifier_result,
            pool_result=pool_result,
            reward_metadata_ref=f"rh://reward/{request.episode_id}/metadata",
            final_verifier_ref=f"rh://verifier/{request.episode_id}/final",
            source_refs={
                "verifier_pool_id": pool_result.pool_id,
                "verifier_worker_id": pool_result.worker_id,
                "verifier_queue_wait_seconds": pool_result.queue_wait_seconds,
            },
        )
        reward_compute_seconds = perf_counter() - reward_started
        return boundary.model_copy(update={"reward_compute_seconds": reward_compute_seconds})

    async def _run_stage7_verifier_job(self, job: VerifierJob) -> VerifierJobResult:
        verifier_pool = self.options.verifier_worker_pool
        if verifier_pool is not None:
            try:
                return await verifier_pool.run(job)
            except Exception as exc:
                return self._verifier_job_exception_result(job, exc, pool_id="verifier-pool-error")
        return await self._run_direct_verifier_job(job)

    async def _run_direct_verifier_job(self, job: VerifierJob) -> VerifierJobResult:
        submitted_at = perf_counter()
        started_at = submitted_at
        future = asyncio.create_task(asyncio.to_thread(job.callable))
        try:
            if job.timeout_seconds is None:
                verifier_result = await future
            else:
                verifier_result = await asyncio.wait_for(asyncio.shield(future), timeout=job.timeout_seconds)
            finished_at = perf_counter()
            return VerifierJobResult(
                job_id=job.job_id,
                run_id=job.run_id,
                episode_id=job.episode_id,
                task_id=job.task_id,
                verifier_stage=job.verifier_stage,
                pool_id="direct-blocking",
                worker_id="direct",
                queue_wait_seconds=0.0,
                execution_seconds=finished_at - started_at,
                submitted_at_seconds=submitted_at,
                started_at_seconds=started_at,
                finished_at_seconds=finished_at,
                verifier_result=verifier_result,
            )
        except TimeoutError:
            finished_at = perf_counter()
            return VerifierJobResult(
                job_id=job.job_id,
                run_id=job.run_id,
                episode_id=job.episode_id,
                task_id=job.task_id,
                verifier_stage=job.verifier_stage,
                pool_id="direct-blocking",
                worker_id="direct",
                queue_wait_seconds=0.0,
                execution_seconds=finished_at - started_at,
                submitted_at_seconds=submitted_at,
                started_at_seconds=started_at,
                finished_at_seconds=finished_at,
                timeout=True,
                error_type="execution_timeout",
                error_message="direct final verifier execution timeout elapsed",
                diagnostics=["direct verifier timeout does not imply a forced thread stop"],
            )
        except asyncio.CancelledError:
            await _wait_for_cancelled_asyncio_future(future)
            raise
        except Exception as exc:
            return self._verifier_job_exception_result(job, exc, pool_id="direct-blocking")

    def _verifier_job_exception_result(
        self,
        job: VerifierJob,
        exc: Exception,
        *,
        pool_id: str,
    ) -> VerifierJobResult:
        now = perf_counter()
        return VerifierJobResult(
            job_id=job.job_id,
            run_id=job.run_id,
            episode_id=job.episode_id,
            task_id=job.task_id,
            verifier_stage=job.verifier_stage,
            pool_id=pool_id,
            queue_wait_seconds=0.0,
            execution_seconds=0.0,
            submitted_at_seconds=now,
            finished_at_seconds=now,
            error_type="pool_executor_error",
            error_message=str(exc),
            diagnostics=[exc.__class__.__name__],
        )

    def _episode_timeout_seconds(self, request: RepoHarnessEpisodeRequest) -> float | None:
        candidates = [
            value
            for value in [self.options.episode_timeout_seconds, request.budgets.max_wall_seconds]
            if value is not None
        ]
        return min(candidates) if candidates else None

    async def _cleanup(self) -> tuple[str, AuditDiagnostic | None]:
        callback = self.options.cleanup_callback
        if callback is None:
            return "skipped", None
        try:
            result = callback()
            if isinstance(result, Awaitable):
                await asyncio.shield(result)
            return "completed", None
        except Exception as exc:
            return "failed", AuditDiagnostic(code="cleanup_failed", message=str(exc))

    async def _cleanup_protected(self) -> tuple[str, AuditDiagnostic | None]:
        cleanup_task = asyncio.create_task(self._cleanup())
        cancellation_seen = False
        while True:
            try:
                cleanup_status, cleanup_diagnostic = await asyncio.shield(cleanup_task)
                if cancellation_seen:
                    return (
                        cleanup_status,
                        AuditDiagnostic(
                            code="cleanup_cancelled",
                            message=(
                                "episode coroutine was cancelled while cleanup callback was still running; "
                                "resource leases were held until cleanup finished"
                            ),
                        ),
                    )
                return cleanup_status, cleanup_diagnostic
            except asyncio.CancelledError:
                if cleanup_task.done():
                    try:
                        cleanup_status, _cleanup_diagnostic = cleanup_task.result()
                    except asyncio.CancelledError:
                        if cancellation_seen:
                            return (
                                "failed",
                                AuditDiagnostic(
                                    code="cleanup_cancelled",
                                    message=(
                                        "episode coroutine was cancelled while cleanup callback was still running; "
                                        "cleanup callback ended with cancellation"
                                    ),
                                ),
                            )
                        return (
                            "failed",
                            AuditDiagnostic(
                                code="cleanup_callback_cancelled",
                                message="cleanup callback raised asyncio.CancelledError",
                            ),
                        )
                    except Exception as exc:
                        return "failed", AuditDiagnostic(code="cleanup_failed", message=str(exc))
                    return (
                        cleanup_status,
                        AuditDiagnostic(
                            code="cleanup_cancelled",
                            message=(
                                "episode coroutine was cancelled while cleanup callback was still running; "
                                "resource leases were held until cleanup finished"
                            ),
                        ),
                    )
                cancellation_seen = True

    async def _acquire_episode_resources(
        self,
        request: RepoHarnessEpisodeRequest,
    ) -> ResourceLeaseHandle | None:
        if self.resource_lease_manager is None:
            return None
        return await self.resource_lease_manager.acquire_episode(
            episode_id=request.episode_id,
            run_id=request.run_id,
            task_id=request.task_id,
        )

    async def _release_episode_resources(
        self,
        resource_handle: ResourceLeaseHandle | None,
    ) -> tuple[str | None, list[AuditDiagnostic]]:
        if self.resource_lease_manager is None or resource_handle is None:
            return None, []
        released = await self.resource_lease_manager.release_episode(resource_handle)
        diagnostics = [
            AuditDiagnostic(code=diagnostic.code, message=diagnostic.message)
            for diagnostic in released.diagnostics
        ]
        return released.cleanup_status, diagnostics

    async def _release_episode_resources_protected(
        self,
        resource_handle: ResourceLeaseHandle | None,
    ) -> tuple[str | None, list[AuditDiagnostic]]:
        if self.resource_lease_manager is None or resource_handle is None:
            return None, []
        release_task = asyncio.create_task(self._release_episode_resources(resource_handle))
        try:
            return await asyncio.shield(release_task)
        except asyncio.CancelledError:
            try:
                return await release_task
            except Exception as exc:
                return "failed", [
                    AuditDiagnostic(
                        code="resource_release_failed",
                        message=str(exc),
                    )
                ]
        except Exception as exc:
            return "failed", [
                AuditDiagnostic(
                    code="resource_release_failed",
                    message=str(exc),
                )
            ]

    def _timing_summary(
        self,
        *,
        elapsed_seconds: float,
        model_call_seconds: float,
        cleanup_seconds: float,
        model_call_count: int,
        response: LLMGatewayResponse | None = None,
        verifier_queue_wait_seconds: float = 0.0,
        final_verifier_seconds: float = 0.0,
        reward_compute_seconds: float = 0.0,
        verifier_call_count: int = 0,
        resource_handle: ResourceLeaseHandle | None = None,
    ) -> TimingSummary:
        resource_queue_wait_seconds = 0.0
        if resource_handle is not None:
            resource_queue_wait_seconds = sum(
                resource_handle.lease.queue_wait_seconds_by_resource.values()
            )
        total_queue_wait_seconds = verifier_queue_wait_seconds + resource_queue_wait_seconds
        agent_loop_seconds = max(
            0.0,
            elapsed_seconds
            - model_call_seconds
            - cleanup_seconds
            - total_queue_wait_seconds
            - final_verifier_seconds
            - reward_compute_seconds,
        )
        provider_reported_model_call_seconds = (
            0.0 if response is None or response.duration_ms is None else response.duration_ms / 1000.0
        )
        return build_timing_summary(
            rollout_wall_seconds=elapsed_seconds,
            agent_loop_seconds=agent_loop_seconds,
            model_call_seconds=model_call_seconds,
            provider_reported_model_call_seconds=provider_reported_model_call_seconds,
            queue_wait_seconds=total_queue_wait_seconds,
            final_verifier_seconds=final_verifier_seconds,
            verifier_seconds=0.0,
            reward_compute_seconds=reward_compute_seconds,
            cleanup_seconds=cleanup_seconds,
            model_call_count=model_call_count,
            verifier_call_count=verifier_call_count,
        )

    def _resource_summary(
        self,
        request: RepoHarnessEpisodeRequest,
        *,
        cleanup_status: str,
        reward_boundary: Stage7RewardBoundaryResult | None = None,
        resource_handle: ResourceLeaseHandle | None = None,
    ) -> ResourceSummary:
        queue_wait_seconds_by_resource: dict[str, float] = {}
        worker_id = None
        concurrency_group = None
        lease_id = None
        inference_concurrency_slot = None
        if resource_handle is not None:
            queue_wait_seconds_by_resource.update(
                resource_handle.lease.queue_wait_seconds_by_resource
            )
            worker_id = resource_handle.lease.worker_id
            concurrency_group = resource_handle.lease.concurrency_group
            lease_id = resource_handle.lease.lease_id
            inference_concurrency_slot = resource_handle.lease.gateway_route_slot_id
        if reward_boundary is not None:
            queue_wait_seconds_by_resource["verifier_worker"] = reward_boundary.verifier_queue_wait_seconds
        return ResourceSummary(
            execution_mode=self.options.execution_mode,
            workspace_backend=self.options.execution_mode,
            worker_id=worker_id,
            concurrency_group=concurrency_group,
            lease_id=lease_id,
            inference_route=request.llm_gateway_route,
            inference_backend=request.inference_backend,
            inference_concurrency_slot=inference_concurrency_slot,
            verifier_worker_pool_id=None if reward_boundary is None else reward_boundary.verifier_pool_id,
            verifier_worker_id=None if reward_boundary is None else reward_boundary.verifier_worker_id,
            queue_wait_seconds_by_resource=queue_wait_seconds_by_resource,
            run_dir=f"runs/{request.run_id}",
            cleanup_status=cleanup_status,
        )

    def _audit_ref(
        self,
        request: RepoHarnessEpisodeRequest,
        *,
        reward_boundary: Stage7RewardBoundaryResult | None = None,
    ) -> AuditRef:
        important_refs = {
            "runtime_result": f"rh://audit/{request.episode_id}/runtime-result",
            "timing_summary": f"rh://audit/{request.episode_id}/timing-summary",
            "resource_summary": f"rh://audit/{request.episode_id}/resource-summary",
        }
        if reward_boundary is not None:
            important_refs["final_verifier"] = f"rh://verifier/{request.episode_id}/final"
            if reward_boundary.reward_metadata is not None:
                important_refs["reward_metadata"] = f"rh://reward/{request.episode_id}/metadata"
        return AuditRef(
            run_id=request.run_id,
            episode_id=request.episode_id,
            task_id=request.task_id,
            run_dir=f"runs/{request.run_id}",
            important_artifact_refs=important_refs,
        )

    def _verifier_summary(self, status: EpisodeStatusName) -> VerifierSummary | None:
        if status == "succeeded":
            return VerifierSummary(accepted=True, status="accepted", summary_ref="rh://verifier/minimal/accepted")
        if status == "failed":
            return VerifierSummary(accepted=False, status="rejected", summary_ref="rh://verifier/minimal/rejected")
        return None

    def _extra_fields(
        self,
        request: RepoHarnessEpisodeRequest,
        *,
        gateway_route: str | None = None,
        status: str,
        invalid_for_training: bool,
        invalid_for_online_rl: bool,
        invalid_reason: str | None,
        extra_fields: dict[str, str | int | float | bool | None] | None = None,
    ) -> dict[str, str | int | float | bool | None]:
        actual_gateway_route = gateway_route or request.llm_gateway_route
        fields: dict[str, str | int | float | bool | None] = {
            "repo_harness_episode_id": request.episode_id,
            "repo_harness_run_id": request.run_id,
            "repo_harness_task_id": request.task_id,
            "repo_harness_llm_gateway_route": actual_gateway_route,
            "repo_harness_status": status,
            "repo_harness_invalid_for_training": invalid_for_training,
            "repo_harness_invalid_for_online_rl": invalid_for_online_rl,
            "repo_harness_invalid_reason": _batch_safe_invalid_reason(invalid_reason),
            "repo_harness_timing_summary_ref": f"rh://audit/{request.episode_id}/timing-summary",
            "repo_harness_resource_summary_ref": f"rh://audit/{request.episode_id}/resource-summary",
        }
        if extra_fields:
            fields.update(extra_fields)
        if actual_gateway_route != request.llm_gateway_route:
            fields["repo_harness_requested_llm_gateway_route"] = request.llm_gateway_route
        return fields


def _status_invalid_for_training(status: EpisodeStatusName) -> bool:
    return status in {"cancelled", "timeout", "invalid", "invalid_task", "infrastructure_error", "no_progress"}


def _status_invalid_for_online_rl(status: EpisodeStatusName) -> bool:
    return status in {"cancelled", "timeout", "invalid", "invalid_task", "infrastructure_error", "no_progress"}


def _is_timeout_reason(value: str | None) -> bool:
    if not value:
        return False
    normalized = value.lower()
    return any(marker in normalized for marker in TIMEOUT_REASON_MARKERS)


def _response_error_reason(response: LLMGatewayResponse) -> str | None:
    error = response.error
    if error is None:
        return None
    if isinstance(error, str):
        return error or "gateway_response_error"
    if isinstance(error, dict):
        for key in ["model_error_type", "error_type", "type", "code"]:
            value = error.get(key)
            if isinstance(value, str) and value:
                return value
        return "gateway_response_error"
    return "gateway_response_error"


def _batch_safe_invalid_reason(value: str | None) -> str | None:
    if value == "run_directory_lock_conflict":
        return "run_lock_conflict"
    if value == "run_directory_already_finalized":
        return "run_already_finalized"
    return value


async def _wait_for_cancelled_asyncio_future(future: asyncio.Future[T]) -> None:
    while not future.done():
        try:
            await asyncio.shield(future)
        except asyncio.CancelledError:
            continue
        except Exception:
            break
    if future.done():
        try:
            future.result()
        except Exception:
            pass


def _coerce_tool_call(value: dict[str, Any], *, turn: int) -> ToolCall:
    payload = dict(value)
    payload.setdefault("turn", turn)
    return ToolCall.model_validate(payload)


def _run_gateway_turn_blocking(gateway: LLMGateway, request: LLMGatewayRequest) -> LLMGatewayResponse:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(gateway.generate_turn(request))
    raise RuntimeError("LLMGatewayModelClientAdapter.generate must run outside an active event loop")
