"""Stage 2 async episode runtime facade."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Literal

from repo_harness.model_client.schemas import ModelCallEvent, ModelMessage, ModelRequestContext, ModelResponse
from repo_harness.schema_base import stable_hash
from repo_harness.tools.schemas import ToolCall

from .episode import (
    AuditDiagnostic,
    BudgetConsumption,
    RepoHarnessEpisodeRequest,
    RepoHarnessEpisodeResult,
    VerifierSummary,
)
from .gateway import LLMGateway, LLMGatewayRequest, LLMGatewayResponse
from .timing import ResourceSummary, TimingSummary
from .training_view import AuditRef, ResponseSpan, RolloutLimits, TrainingView
from .visibility import PROVIDER_ROUTES, VisibilityContractError, validate_no_absolute_local_path

CleanupCallback = Callable[[], None | Awaitable[None]]
TaskPathResolver = Callable[[RepoHarnessEpisodeRequest], str | Path | None]
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
    if invalid_task or run_outcome in {"invalid_task", "flaky_task"} or baseline_status in {"invalid", "flaky"}:
        return "invalid_task"
    if infrastructure_error or final_verifier_status == "error" or provider_error_type:
        return "infrastructure_error"
    if agent_stop_reason in {"no_progress", "stalled", "max_no_progress"}:
        return "no_progress"
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
        gateway_request = self.to_gateway_request(request)
        response = _run_gateway_turn_blocking(self.llm_gateway, gateway_request)
        return self.to_model_response(request, response)

    def to_gateway_request(self, request: ModelRequestContext) -> LLMGatewayRequest:
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
            recorder_policy={
                "raw_request_logging_policy": request.raw_request_logging_policy,
                "retry_policy": request.retry_policy,
            },
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

        try:
            self.resolve_runner_inputs(parsed_request)
            timeout_seconds = self._episode_timeout_seconds(parsed_request)
            if timeout_seconds is None:
                response = await self._generate_minimal_turn(parsed_request, llm_gateway)
            else:
                response = await asyncio.wait_for(
                    self._generate_minimal_turn(parsed_request, llm_gateway),
                    timeout=timeout_seconds,
                )
            status = self._status_from_minimal_verifier()
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
        except Exception as exc:  # pragma: no cover - exercised by tests through concrete failures.
            status = "infrastructure_error"
            status_reason = "infrastructure_error"
            diagnostics.append(AuditDiagnostic(code=exc.__class__.__name__, message=str(exc)))

        cleanup_started = perf_counter()
        cleanup_status, cleanup_diagnostic = await self._cleanup()
        cleanup_seconds = perf_counter() - cleanup_started
        if cleanup_diagnostic is not None:
            diagnostics.append(cleanup_diagnostic)

        elapsed = perf_counter() - started
        if response is not None:
            return self._result_from_gateway_response(
                parsed_request,
                response,
                status=status,
                status_reason=status_reason,
                diagnostics=diagnostics,
                elapsed_seconds=elapsed,
                cleanup_seconds=cleanup_seconds,
                cleanup_status=cleanup_status,
            )
        return self._terminal_result(
            parsed_request,
            status=status,
            status_reason=status_reason or status,
            diagnostics=diagnostics,
            elapsed_seconds=elapsed,
            cleanup_seconds=cleanup_seconds,
            cleanup_status=cleanup_status,
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
            recorder_policy={"run_mode": request.run_mode or "full_audit"},
            visibility_policy=request.visibility_policy.model_dump(mode="json"),
            tracing={"runtime_mode": self.options.execution_mode},
        )
        return await llm_gateway.generate_turn(gateway_request)

    def _result_from_gateway_response(
        self,
        request: RepoHarnessEpisodeRequest,
        response: LLMGatewayResponse,
        *,
        status: EpisodeStatusName,
        status_reason: str | None,
        diagnostics: list[AuditDiagnostic],
        elapsed_seconds: float,
        cleanup_seconds: float,
        cleanup_status: str,
    ) -> RepoHarnessEpisodeResult:
        invalid_reason = self._response_invalid_reason(request, response)
        if invalid_reason in {"gateway_route_mismatch", "gateway_inference_backend_mismatch"}:
            status = "infrastructure_error"
            status_reason = invalid_reason
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

        diagnostics.extend(self._diagnostics_for_invalid_reason(request, response, status_reason))
        budget_consumption = self._budget_consumption(request, response, stop_reason=status_reason)
        reward_score = self._reward_score(status, invalid_for_training, invalid_for_online_rl)
        training_view = self._training_view_from_response(
            request,
            response,
            status=status,
            reward_score=reward_score,
            invalid_for_training=invalid_for_training,
            invalid_for_online_rl=invalid_for_online_rl,
            invalid_reason=status_reason,
        )
        generation_records = [response.to_generation_record(turn=0, context_revision=0)]
        timing_summary = self._timing_summary(
            elapsed_seconds=elapsed_seconds,
            cleanup_seconds=cleanup_seconds,
            response=response,
        )
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
            audit_ref=self._audit_ref(request),
            audit_diagnostics=diagnostics,
            verifier_summary=self._verifier_summary(status),
            generation_records=generation_records,
            timing_summary=timing_summary,
            resource_summary=self._resource_summary(cleanup_status=cleanup_status),
        )

    def _terminal_result(
        self,
        request: RepoHarnessEpisodeRequest,
        *,
        status: EpisodeStatusName,
        status_reason: str,
        diagnostics: list[AuditDiagnostic],
        elapsed_seconds: float,
        cleanup_seconds: float,
        cleanup_status: str,
    ) -> RepoHarnessEpisodeResult:
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
                used_wall_seconds=elapsed_seconds,
                max_model_call_seconds=request.budgets.generation_timeout_seconds
                or request.budgets.max_model_call_seconds,
                used_model_call_seconds=0.0,
                max_tool_calls=request.budgets.max_tool_calls,
                used_tool_calls=0,
                max_artifact_bytes=request.budgets.max_artifact_bytes,
                used_artifact_bytes=0,
                stop_reason=status_reason,
                rollout_response_length=request.budgets.max_output_tokens,
                actual_response_length=0,
            ),
            training_view=training_view,
            audit_ref=self._audit_ref(request),
            audit_diagnostics=diagnostics,
            timing_summary=self._timing_summary(
                elapsed_seconds=elapsed_seconds,
                cleanup_seconds=cleanup_seconds,
                response=None,
            ),
            resource_summary=self._resource_summary(cleanup_status=cleanup_status),
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
                status=status,
                invalid_for_training=invalid_for_training,
                invalid_for_online_rl=invalid_for_online_rl,
                invalid_reason=invalid_reason,
            ),
        )

    def _response_invalid_reason(self, request: RepoHarnessEpisodeRequest, response: LLMGatewayResponse) -> str | None:
        if response.route != request.llm_gateway_route:
            return "gateway_route_mismatch"
        if response.inference_backend != request.inference_backend:
            return "gateway_inference_backend_mismatch"
        if not response.output_token_ids:
            return "empty_response"
        if request.budgets.max_prompt_tokens is not None and len(response.prompt_ids) > request.budgets.max_prompt_tokens:
            return "prompt_length_exceeded"
        if request.budgets.max_output_tokens is not None and len(response.output_token_ids) > request.budgets.max_output_tokens:
            return "response_length_exceeded"
        if request.llm_gateway_route in PROVIDER_ROUTES or response.route in PROVIDER_ROUTES:
            return "provider_route_invalid_for_online_rl"
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
    ) -> BudgetConsumption:
        return BudgetConsumption(
            max_turns=request.budgets.max_turns,
            used_turns=1,
            max_wall_seconds=request.budgets.max_wall_seconds,
            max_model_call_seconds=request.budgets.generation_timeout_seconds
            or request.budgets.max_model_call_seconds,
            max_tool_calls=request.budgets.max_tool_calls,
            used_tool_calls=0,
            max_artifact_bytes=request.budgets.max_artifact_bytes,
            used_artifact_bytes=0,
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
        return []

    def _status_from_minimal_verifier(self) -> EpisodeStatusName:
        if self.options.minimal_final_verifier_status == "accepted":
            return "succeeded"
        return "failed"

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
            return "not_required", None
        try:
            result = callback()
            if isinstance(result, Awaitable):
                await asyncio.shield(result)
            return "ok", None
        except Exception as exc:
            return "failed", AuditDiagnostic(code="cleanup_failed", message=str(exc))

    def _timing_summary(
        self,
        *,
        elapsed_seconds: float,
        cleanup_seconds: float,
        response: LLMGatewayResponse | None,
    ) -> TimingSummary:
        return TimingSummary(
            rollout_wall_seconds=elapsed_seconds,
            agent_loop_seconds=elapsed_seconds,
            model_call_seconds=(response.duration_ms or 0) / 1000 if response is not None else 0.0,
            cleanup_seconds=cleanup_seconds,
            model_call_count=1 if response is not None else 0,
        )

    def _resource_summary(self, *, cleanup_status: str) -> ResourceSummary:
        return ResourceSummary(
            execution_mode=self.options.execution_mode,
            cleanup_status=cleanup_status,
        )

    def _audit_ref(self, request: RepoHarnessEpisodeRequest) -> AuditRef:
        return AuditRef(
            run_id=request.run_id,
            episode_id=request.episode_id,
            task_id=request.task_id,
            run_dir=f"runs/{request.run_id}",
            important_artifact_refs={
                "runtime_result": f"rh://audit/{request.episode_id}/runtime-result",
            },
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
        status: str,
        invalid_for_training: bool,
        invalid_for_online_rl: bool,
        invalid_reason: str | None,
    ) -> dict[str, str | int | float | bool | None]:
        return {
            "repo_harness_episode_id": request.episode_id,
            "repo_harness_run_id": request.run_id,
            "repo_harness_task_id": request.task_id,
            "repo_harness_status": status,
            "repo_harness_invalid_for_training": invalid_for_training,
            "repo_harness_invalid_for_online_rl": invalid_for_online_rl,
            "repo_harness_invalid_reason": invalid_reason,
        }


def _status_invalid_for_training(status: EpisodeStatusName) -> bool:
    return status in {"cancelled", "timeout", "invalid", "invalid_task", "infrastructure_error", "no_progress"}


def _status_invalid_for_online_rl(status: EpisodeStatusName) -> bool:
    return status in {"cancelled", "timeout", "invalid", "invalid_task", "infrastructure_error", "no_progress"}


def _is_timeout_reason(value: str | None) -> bool:
    if not value:
        return False
    normalized = value.lower()
    return any(marker in normalized for marker in TIMEOUT_REASON_MARKERS)


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
