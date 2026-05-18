"""Stage 2 async episode runtime facade."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from functools import partial
from pathlib import Path
from time import perf_counter
from typing import Any, Literal, TypeVar

from repo_harness.agent_loop import AgentLoop
from repo_harness.agent_loop.schemas import AgentLoopState
from repo_harness.config import ContextManagementConfig
from repo_harness.context import ToolResultArtifactIndex
from repo_harness.model_client.schemas import ModelProviderOptions
from repo_harness.model_client.schemas import ModelCallEvent, ModelMessage, ModelRequestContext, ModelResponse
from repo_harness.permissions import PermissionContext
from repo_harness.schema_base import stable_hash
from repo_harness.tools import ToolExecutionContext, ToolExecutor, ToolOutputLimits, ToolPolicy
from repo_harness.tools.schemas import ToolCall
from repo_harness.trajectory import RecorderProfile, RunRecorder, load_artifact_manifest
from repo_harness.verifier import VerifierJob, VerifierJobResult, VerifierResult, VerifierWorkerPool
from repo_harness.workspace import (
    DependencyEnvironmentHandle,
    DependencyEnvironmentManager,
    DependencyEnvironmentSpec,
    DependencyState,
    LocalWorkspaceAdapter,
    RunWorkspace,
    WorkspaceLeaseHandle,
    WorkspaceSnapshotManager,
    WorkspaceSnapshotResult,
    build_command_environment,
    build_workspace_snapshot_key,
)

from .episode import (
    AuditDiagnostic,
    BudgetConsumption,
    RepoHarnessEpisodeRequest,
    RepoHarnessEpisodeResult,
    VerifierSummary,
)
from .budget import (
    CONTEXT_BUDGET_STOP_REASONS,
    NO_PROGRESS_STOP_REASONS,
    budget_manager_from_training_policy,
    build_training_budget_policy,
    context_config_from_training_policy,
)
from .async_contracts import AsyncEpisodeHandleRef
from .async_runtime import AsyncEpisodeHandle, AsyncEpisodeStartError, AsyncEpisodeState
from .gateway import GenerationRecord, LLMGateway, LLMGatewayRequest, LLMGatewayResponse
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
RuntimeExecutionMode = Literal["minimal_gateway", "real_episode"]
RealEpisodeSourceResolver = Callable[[RepoHarnessEpisodeRequest], str | Path | None]
DependencyEnvironmentSpecResolver = Callable[
    [RepoHarnessEpisodeRequest, Path],
    DependencyEnvironmentSpec | None,
]
ToolObservationTokenProjector = Callable[[str], list[int]]
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


@dataclass(frozen=True)
class RealEpisodeContext:
    """Runtime-only context for real episode factories.

    It may contain local paths and must never be nested into TrainingView or
    future trainer batch payloads.
    """

    request: RepoHarnessEpisodeRequest
    run_dir: Path
    workspace_path: Path
    run_workspace: RunWorkspace
    snapshot: WorkspaceSnapshotResult | None
    workspace_lease: WorkspaceLeaseHandle | None
    agent_state: AgentLoopState | None = None


RealEpisodeFinalVerifierFactory = Callable[[RealEpisodeContext], FinalVerifierCallable]


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
    runtime_execution_mode: RuntimeExecutionMode | None = None
    execution_mode: str = "minimal_gateway"
    real_episode_source_resolver: RealEpisodeSourceResolver | None = None
    real_episode_final_verifier_factory: RealEpisodeFinalVerifierFactory | None = None
    workspace_snapshot_manager: WorkspaceSnapshotManager | None = None
    dependency_environment_manager: DependencyEnvironmentManager | None = None
    dependency_environment_spec_resolver: DependencyEnvironmentSpecResolver | None = None
    tool_observation_token_projector: ToolObservationTokenProjector | None = None

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


@dataclass(frozen=True)
class CollectedGenerationRecord:
    request: LLMGatewayRequest
    response: LLMGatewayResponse
    generation_record: GenerationRecord


@dataclass
class GenerationRecordCollector:
    """Runtime-only collector for token facts lost by legacy ModelResponse."""

    records: list[CollectedGenerationRecord]

    def __init__(self) -> None:
        self.records = []

    def collect(self, request: LLMGatewayRequest, response: LLMGatewayResponse) -> None:
        self.records.append(
            CollectedGenerationRecord(
                request=request,
                response=response,
                generation_record=response.to_generation_record(
                    turn=request.turn,
                    context_revision=request.context_revision,
                ),
            )
        )

    @property
    def generation_records(self) -> list[GenerationRecord]:
        return [record.generation_record for record in self.records]


@dataclass(frozen=True)
class RealEpisodeWorkspace:
    run_dir: Path
    adapter: LocalWorkspaceAdapter
    snapshot_manager: WorkspaceSnapshotManager
    snapshot: WorkspaceSnapshotResult
    lease_handle: WorkspaceLeaseHandle
    dependency_environment: DependencyEnvironmentHandle | None = None


@dataclass(frozen=True)
class RealEpisodeRun:
    agent_state: AgentLoopState
    collector: GenerationRecordCollector
    run_dir: Path
    run_workspace: RunWorkspace
    workspace: RealEpisodeWorkspace
    final_verifier_callable: FinalVerifierCallable
    agent_loop_seconds: float
    artifact_count: int
    artifact_bytes_written: int


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
        generation_record_collector: GenerationRecordCollector | None = None,
        gateway_accounting: GatewayCallAccounting | None = None,
        resource_lease_manager: ResourceLeaseManager | None = None,
        resource_handle: ResourceLeaseHandle | None = None,
        runtime_loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        self.llm_gateway = llm_gateway
        self.episode_id = episode_id
        self.route = route
        self.inference_backend = inference_backend
        self.generation_record_collector = generation_record_collector
        self.gateway_accounting = gateway_accounting
        self.resource_lease_manager = resource_lease_manager
        self.resource_handle = resource_handle
        self.runtime_loop = runtime_loop

    def generate(self, request: ModelRequestContext, recorder: Any) -> ModelResponse:
        gateway_request = self.to_gateway_request(request, recorder=recorder)
        call_started = perf_counter()
        if self.gateway_accounting is not None:
            self.gateway_accounting.request_submitted = True
        try:
            response = _run_gateway_turn_blocking(
                self.llm_gateway,
                gateway_request,
                resource_lease_manager=self.resource_lease_manager,
                resource_handle=self.resource_handle,
                runtime_loop=self.runtime_loop,
            )
        finally:
            if self.gateway_accounting is not None:
                self.gateway_accounting.model_call_seconds += perf_counter() - call_started
        if self.generation_record_collector is not None:
            self.generation_record_collector.collect(gateway_request, response)
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
        self._real_episode_executor: ThreadPoolExecutor | None = None
        self._async_episode_counter_by_episode_id: dict[str, int] = {}
        self._async_handles_by_ref: dict[str, AsyncEpisodeHandle] = {}
        self._async_handles_by_run_id: dict[str, AsyncEpisodeHandle] = {}
        self._async_registry_lock = asyncio.Lock()
        self._close_requested = False
        if self.resource_lease_manager is None and self.options.resource_concurrency_policy is not None:
            self.resource_lease_manager = ResourceLeaseManager(self.options.resource_concurrency_policy)

    def close(self) -> None:
        """Release runtime-owned worker resources."""

        self._close_requested = True
        for handle in list(self._async_handles_by_ref.values()):
            state = handle._state
            task = state.task
            if task is not None and not task.done():
                state.mark_cancel_requested("runtime_closed")
                if state.started:
                    task.cancel()
        if not self._has_active_async_episode_handles():
            self._shutdown_real_episode_executor()

    async def aclose(self) -> None:
        self.close()

    def _has_active_async_episode_handles(self) -> bool:
        return any(not handle._state.is_terminal() for handle in self._async_handles_by_ref.values())

    def _shutdown_real_episode_executor(self) -> None:
        if self._real_episode_executor is not None:
            self._real_episode_executor.shutdown(wait=False, cancel_futures=True)
            self._real_episode_executor = None

    async def start_episode(
        self,
        request: RepoHarnessEpisodeRequest,
        *,
        llm_gateway: LLMGateway,
    ) -> AsyncEpisodeHandle:
        """Start an episode in the background and return a runtime-only handle."""

        started = perf_counter()
        parsed_request = RepoHarnessEpisodeRequest.model_validate(request)
        async with self._async_registry_lock:
            existing = self._async_handles_by_run_id.get(parsed_request.run_id)
            if existing is not None and not existing._state.is_terminal():
                raise AsyncEpisodeStartError(f"run_id already has an active async episode: {parsed_request.run_id}")
            attempt_index = self._async_episode_counter_by_episode_id.get(parsed_request.episode_id, 0)
            self._async_episode_counter_by_episode_id[parsed_request.episode_id] = attempt_index + 1
            sample_attempt_id = f"{parsed_request.episode_id}:attempt-{attempt_index}"
            handle_ref = AsyncEpisodeHandleRef(
                episode_id=parsed_request.episode_id,
                run_id=parsed_request.run_id,
                sample_attempt_id=sample_attempt_id,
                handle_ref=f"rh://async/{parsed_request.episode_id}/{sample_attempt_id}",
            )

            def cancel_result_factory() -> RepoHarnessEpisodeResult:
                return self._terminal_result(
                    parsed_request,
                    status="cancelled",
                    status_reason="runtime_cancelled",
                    diagnostics=[
                        AuditDiagnostic(
                            code="runtime_cancelled",
                            message="async episode was cancelled before the runner started",
                        )
                    ],
                    elapsed_seconds=perf_counter() - started,
                    model_call_seconds=0.0,
                    cleanup_seconds=0.0,
                    cleanup_status="skipped",
                )

            state = AsyncEpisodeState(
                request=parsed_request,
                sample_attempt_id=sample_attempt_id,
                handle_ref=handle_ref,
                runtime_mode=self._runtime_execution_mode(),
                cancel_result_factory=cancel_result_factory,
            )
            handle = AsyncEpisodeHandle(state, unregister=self._unregister_async_episode_handle)
            self._async_handles_by_ref[handle_ref.handle_ref] = handle
            self._async_handles_by_run_id[parsed_request.run_id] = handle

        async def runner() -> RepoHarnessEpisodeResult:
            return await self.run_episode(parsed_request, llm_gateway=llm_gateway)

        task = asyncio.create_task(
            handle._run_and_record(runner),
            name=f"repo-harness-async-episode:{parsed_request.episode_id}:{sample_attempt_id}",
        )
        handle.attach_task(task)
        return handle

    async def _unregister_async_episode_handle(self, handle: AsyncEpisodeHandle) -> None:
        async with self._async_registry_lock:
            self._async_handles_by_ref.pop(handle.handle_ref.handle_ref, None)
            if self._async_handles_by_run_id.get(handle.handle_ref.run_id) is handle:
                self._async_handles_by_run_id.pop(handle.handle_ref.run_id, None)
            if self._close_requested and not self._has_active_async_episode_handles():
                self._shutdown_real_episode_executor()

    async def run_episode(
        self,
        request: RepoHarnessEpisodeRequest,
        *,
        llm_gateway: LLMGateway,
    ) -> RepoHarnessEpisodeResult:
        started = perf_counter()
        parsed_request = RepoHarnessEpisodeRequest.model_validate(request)
        runtime_mode = self._runtime_execution_mode()
        if runtime_mode == "real_episode":
            return await self._run_real_episode_entry(
                parsed_request,
                llm_gateway=llm_gateway,
                started=started,
            )
        if runtime_mode != "minimal_gateway":
            return self._terminal_result(
                parsed_request,
                status="infrastructure_error",
                status_reason="unsupported_runtime_execution_mode",
                diagnostics=[
                    AuditDiagnostic(
                        code="unsupported_runtime_execution_mode",
                        message=f"unsupported runtime_execution_mode: {runtime_mode}",
                    )
                ],
                elapsed_seconds=perf_counter() - started,
                model_call_seconds=0.0,
                cleanup_seconds=0.0,
                cleanup_status="skipped",
            )
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

    def _runtime_execution_mode(self) -> str:
        return self.options.runtime_execution_mode or self.options.execution_mode

    async def _run_real_episode_entry(
        self,
        request: RepoHarnessEpisodeRequest,
        *,
        llm_gateway: LLMGateway,
        started: float,
    ) -> RepoHarnessEpisodeResult:
        status: EpisodeStatusName = "infrastructure_error"
        status_reason: str | None = None
        diagnostics: list[AuditDiagnostic] = []
        gateway_accounting = GatewayCallAccounting()
        resource_handle: ResourceLeaseHandle | None = None
        real_workspace: RealEpisodeWorkspace | None = None
        real_run: RealEpisodeRun | None = None
        reward_boundary: Stage7RewardBoundaryResult | None = None
        runtime_loop = asyncio.get_running_loop()
        executor = self._get_real_episode_executor()

        try:
            resolved_inputs = self.resolve_runner_inputs(request)
            resource_handle = await self._acquire_episode_resources(request)
            real_workspace = await self._run_in_real_episode_executor(
                executor,
                self._prepare_real_episode_workspace,
                request,
                resolved_inputs,
            )
            timeout_seconds = self._episode_timeout_seconds(request)
            real_episode_task = asyncio.create_task(
                self._run_in_real_episode_executor(
                    executor,
                    self._run_real_episode_sync,
                    request,
                    llm_gateway,
                    real_workspace,
                    gateway_accounting,
                    resource_handle,
                    runtime_loop,
                )
            )
            if timeout_seconds is None:
                real_run = await asyncio.shield(real_episode_task)
            else:
                real_run = await asyncio.wait_for(asyncio.shield(real_episode_task), timeout=timeout_seconds)
            reward_boundary = await self._stage7_reward_boundary_for_callable(
                request,
                real_run.final_verifier_callable,
            )
            status = reward_boundary.status
            status_reason = reward_boundary.status_reason
        except asyncio.CancelledError:
            status = "cancelled"
            status_reason = "runtime_cancelled"
            diagnostics.append(AuditDiagnostic(code="runtime_cancelled", message="episode coroutine was cancelled"))
            if "real_episode_task" in locals():
                real_run, wait_diagnostics = await _wait_for_real_episode_task_after_stop(
                    real_episode_task,
                    stop_kind="cancelled",
                )
                diagnostics.extend(wait_diagnostics)
        except TimeoutError:
            status = "timeout"
            status_reason = "episode_timeout"
            diagnostics.append(AuditDiagnostic(code="episode_timeout", message="episode timeout expired"))
            if "real_episode_task" in locals():
                real_run, wait_diagnostics = await _wait_for_real_episode_task_after_stop(
                    real_episode_task,
                    stop_kind="timeout",
                )
                diagnostics.extend(wait_diagnostics)
        except InvalidTaskError as exc:
            status = "invalid_task"
            status_reason = "invalid_task"
            diagnostics.append(AuditDiagnostic(code="invalid_task", message=str(exc)))
        except ResourceLeaseError as exc:
            status = exc.episode_status
            status_reason = exc.status_reason
            diagnostics.append(AuditDiagnostic(code=exc.status_reason, message=str(exc)))
        except Exception as exc:  # pragma: no cover - exercised through concrete failures.
            status = "infrastructure_error"
            status_reason = "infrastructure_error"
            diagnostics.append(AuditDiagnostic(code=exc.__class__.__name__, message=str(exc)))

        cleanup_started = perf_counter()
        cleanup_status, cleanup_diagnostic = await self._cleanup_protected()
        if cleanup_diagnostic is not None and cleanup_diagnostic.code == "cleanup_cancelled":
            status = "cancelled"
            status_reason = "runtime_cancelled"
        workspace_cleanup_status, workspace_cleanup_diagnostics = await self._release_real_workspace_protected(
            real_workspace,
            executor=executor,
        )
        resource_cleanup_status, resource_cleanup_diagnostics = await self._release_episode_resources_protected(
            resource_handle
        )
        cleanup_status = combine_cleanup_status(cleanup_status, workspace_cleanup_status)
        cleanup_status = combine_cleanup_status(cleanup_status, resource_cleanup_status)
        cleanup_seconds = perf_counter() - cleanup_started
        if cleanup_diagnostic is not None:
            diagnostics.append(cleanup_diagnostic)
        diagnostics.extend(workspace_cleanup_diagnostics)
        diagnostics.extend(resource_cleanup_diagnostics)

        elapsed = perf_counter() - started
        if real_run is None:
            return self._terminal_result(
                request,
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
        return self._result_from_real_episode_run(
            request,
            real_run,
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

    def _get_real_episode_executor(self) -> ThreadPoolExecutor:
        if self._real_episode_executor is None:
            self._real_episode_executor = ThreadPoolExecutor(
                max_workers=self.options.executor_max_workers,
                thread_name_prefix="repo-harness-real-episode",
            )
        return self._real_episode_executor

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

    def _prepare_real_episode_workspace(
        self,
        request: RepoHarnessEpisodeRequest,
        resolved_inputs: RuntimeResolvedInputs,
    ) -> RealEpisodeWorkspace:
        source_path = self._real_episode_source_path(request, resolved_inputs)
        if source_path is None:
            raise InvalidTaskError("real_episode requires a resolved source workspace path")
        run_dir = self._run_dir_for_request(request)
        dependency_environment = self._prepare_dependency_environment(request, source_path)
        snapshot_manager = self.options.workspace_snapshot_manager or WorkspaceSnapshotManager(
            run_dir / "workspaces" / "snapshot_cache",
            creator_id=f"repo-harness-{request.run_id}",
        )
        snapshot_key = build_workspace_snapshot_key(
            repo_ref=request.task_id,
            environment_id=(
                dependency_environment.dependency_cache_key
                if dependency_environment is not None
                else "local_process"
            ),
            dependency_lock_hash=(
                dependency_environment.dependency_cache_key
                if dependency_environment is not None
                else None
            ),
            harness_version="repo_harness_stage11_5_v0",
            diagnostics=["stage11_5_real_episode_runtime_bridge"],
        )
        snapshot = snapshot_manager.create_or_get_snapshot(snapshot_key, source_path=source_path)
        lease = snapshot_manager.acquire_workspace(
            snapshot,
            lease_id=request.episode_id,
            dependency_restore_seconds=(
                0.0 if dependency_environment is None else dependency_environment.dependency_restore_seconds
            ),
        )
        adapter = LocalWorkspaceAdapter(
            run_id=request.run_id,
            run_dir=run_dir,
            allowed_workspace_roots=[snapshot_manager.leases_dir],
            command_env_provider=(
                None
                if dependency_environment is None
                else lambda workspace_path: build_command_environment(
                    dependency_environment,
                    workspace_path=workspace_path,
                )
            ),
            block_shared_environment_writes=dependency_environment is not None,
        )
        return RealEpisodeWorkspace(
            run_dir=run_dir,
            adapter=adapter,
            snapshot_manager=snapshot_manager,
            snapshot=snapshot,
            lease_handle=lease,
            dependency_environment=dependency_environment,
        )

    def _prepare_dependency_environment(
        self,
        request: RepoHarnessEpisodeRequest,
        source_path: Path,
    ) -> DependencyEnvironmentHandle | None:
        if (
            self.options.dependency_environment_manager is None
            or self.options.dependency_environment_spec_resolver is None
        ):
            return None
        spec = self.options.dependency_environment_spec_resolver(request, source_path)
        if spec is None:
            return None
        return self.options.dependency_environment_manager.prepare_environment(spec)

    def _real_episode_source_path(
        self,
        request: RepoHarnessEpisodeRequest,
        resolved_inputs: RuntimeResolvedInputs,
    ) -> Path | None:
        if self.options.real_episode_source_resolver is not None:
            resolved = self.options.real_episode_source_resolver(request)
            return None if resolved is None else Path(resolved)
        if resolved_inputs.task_path:
            return Path(resolved_inputs.task_path)
        return None

    def _run_dir_for_request(self, request: RepoHarnessEpisodeRequest) -> Path:
        output_dir = Path(self.options.output_dir) if self.options.output_dir is not None else Path("runs")
        return output_dir / request.run_id

    def _run_real_episode_sync(
        self,
        request: RepoHarnessEpisodeRequest,
        llm_gateway: LLMGateway,
        workspace: RealEpisodeWorkspace,
        gateway_accounting: GatewayCallAccounting,
        resource_handle: ResourceLeaseHandle | None,
        runtime_loop: asyncio.AbstractEventLoop,
    ) -> RealEpisodeRun:
        collector = GenerationRecordCollector()
        recorder_profile = RecorderProfile.for_run_mode(request.run_mode)
        with RunRecorder(
            request.run_id,
            workspace.run_dir,
            task_id=request.task_id,
            max_artifact_bytes=request.budgets.max_artifact_bytes,
            recorder_profile=recorder_profile,
        ) as recorder:
            dependency_state = DependencyState()
            agent_start_snapshot = workspace.adapter.create_agent_start_snapshot(
                workspace.lease_handle.workspace_path,
                dependency_state.excluded_diff_paths,
                recorder,
            )
            run_workspace = RunWorkspace(
                run_id=request.run_id,
                workspace_path=workspace.lease_handle.workspace_path.as_posix(),
                repo_base_commit=workspace.snapshot.facts.base_commit,
                execution_mode="local_process",
                artifact_dir=(workspace.run_dir / "artifacts").as_posix(),
                dependency_state=dependency_state,
                agent_start_snapshot=agent_start_snapshot,
                agent_diff_base=agent_start_snapshot,
            )
            tool_context = ToolExecutionContext(
                run_id=request.run_id,
                task_id=request.task_id,
                workspace_facade=workspace.adapter,
                run_workspace=run_workspace,
                artifact_writer=recorder,
                permission_context=PermissionContext(mode="auto"),
                verifier_feedback_facade=None,  # type: ignore[arg-type]
                resolved_verifier_plan=None,  # type: ignore[arg-type]
                output_limits=ToolOutputLimits(
                    max_tool_output_chars=request.budgets.max_tool_observation_tokens or 12000
                ),
                tool_policy=ToolPolicy(),
                test_feedback_policy="disabled",
                feedback_tests_passed_policy="not_applicable",
                tool_result_artifact_index=ToolResultArtifactIndex(run_dir=workspace.run_dir),
            )
            adapter = LLMGatewayModelClientAdapter(
                llm_gateway=llm_gateway,
                episode_id=request.episode_id,
                route=request.llm_gateway_route,
                inference_backend=request.inference_backend,
                generation_record_collector=collector,
                gateway_accounting=gateway_accounting,
                resource_lease_manager=self.resource_lease_manager,
                resource_handle=resource_handle,
                runtime_loop=runtime_loop,
            )
            budget_policy = build_training_budget_policy(request.budgets, run_mode=request.run_mode)
            budget_manager = budget_manager_from_training_policy(budget_policy)
            context_config = context_config_from_training_policy(
                budget_policy,
                base_config=ContextManagementConfig(),
            )
            agent_loop_started = perf_counter()
            agent_state = AgentLoop(
                model_client=adapter,
                tool_executor=ToolExecutor(),
            ).run(
                run_id=request.run_id,
                task_id=request.task_id,
                initial_messages=[dict(message) for message in request.raw_prompt],
                tool_context=tool_context,
                recorder=recorder,
                max_turns=budget_manager.max_turns,
                context_config=context_config,
                budget_manager=budget_manager,
                training_budget_policy=budget_policy,
                provider_options=ModelProviderOptions(
                    provider=request.llm_gateway_route,
                    model_id="repo-harness-llm-gateway",
                ),
                generation_config={
                    "max_output_tokens": request.budgets.max_output_tokens,
                    "reasoning_effort": request.budgets.reasoning_effort,
                    "thinking_mode": request.budgets.thinking_mode,
                },
                request_timeout_seconds=(
                    request.budgets.generation_timeout_seconds
                    or request.budgets.request_timeout_seconds
                    or 60.0
                ),
            )
            agent_loop_seconds = perf_counter() - agent_loop_started
            workspace.adapter.capture_final_patch(run_workspace, recorder=recorder)
            manifest = load_artifact_manifest(workspace.run_dir)
            artifacts = list(manifest.get("artifacts", []))
            final_verifier_callable = self._real_episode_final_verifier_callable(
                request,
                workspace=workspace,
                run_workspace=run_workspace,
                agent_state=agent_state,
            )
            return RealEpisodeRun(
                agent_state=agent_state,
                collector=collector,
                run_dir=workspace.run_dir,
                run_workspace=run_workspace,
                workspace=workspace,
                final_verifier_callable=final_verifier_callable,
                agent_loop_seconds=agent_loop_seconds,
                artifact_count=len(artifacts),
                artifact_bytes_written=sum(int(artifact.get("size_bytes", 0)) for artifact in artifacts),
            )

    def _real_episode_final_verifier_callable(
        self,
        request: RepoHarnessEpisodeRequest,
        *,
        workspace: RealEpisodeWorkspace,
        run_workspace: RunWorkspace,
        agent_state: AgentLoopState,
    ) -> FinalVerifierCallable:
        context = RealEpisodeContext(
            request=request,
            run_dir=workspace.run_dir,
            workspace_path=workspace.lease_handle.workspace_path,
            run_workspace=run_workspace,
            snapshot=workspace.snapshot,
            workspace_lease=workspace.lease_handle,
            agent_state=agent_state,
        )
        if self.options.real_episode_final_verifier_factory is not None:
            return self.options.real_episode_final_verifier_factory(context)
        if self.options.final_verifier_callable is not None:
            return self.options.final_verifier_callable
        raise InvalidTaskError("real_episode requires final_verifier_callable or real_episode_final_verifier_factory")

    async def _release_real_workspace_protected(
        self,
        workspace: RealEpisodeWorkspace | None,
        *,
        executor: ThreadPoolExecutor | None = None,
    ) -> tuple[str | None, list[AuditDiagnostic]]:
        if workspace is None:
            return None, []
        try:
            if executor is None:
                released = await asyncio.to_thread(
                    workspace.snapshot_manager.release_workspace,
                    workspace.lease_handle,
                )
            else:
                released = await self._run_in_real_episode_executor(
                    executor,
                    workspace.snapshot_manager.release_workspace,
                    workspace.lease_handle,
                )
        except Exception as exc:
            return "failed", [AuditDiagnostic(code="workspace_lease_release_failed", message=str(exc))]
        diagnostics = [
            AuditDiagnostic(code="workspace_lease_diagnostic", message=diagnostic)
            for diagnostic in released.lease.diagnostics
        ]
        return released.lease.cleanup_status, diagnostics

    async def _run_in_real_episode_executor(
        self,
        executor: ThreadPoolExecutor,
        func: Callable[..., T],
        *args: object,
    ) -> T:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(executor, partial(func, *args))

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
            tracing={"runtime_mode": self._runtime_execution_mode()},
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

    def _result_from_real_episode_run(
        self,
        request: RepoHarnessEpisodeRequest,
        real_run: RealEpisodeRun,
        *,
        status: EpisodeStatusName,
        status_reason: str | None,
        diagnostics: list[AuditDiagnostic],
        elapsed_seconds: float,
        model_call_seconds: float,
        cleanup_seconds: float,
        cleanup_status: str,
        reward_boundary: Stage7RewardBoundaryResult | None,
        resource_handle: ResourceLeaseHandle | None = None,
    ) -> RepoHarnessEpisodeResult:
        generation_records = real_run.collector.generation_records
        invalid_reason = self._real_episode_invalid_reason(request, real_run)
        invalid_for_training = _status_invalid_for_training(status)
        invalid_for_online_rl = _status_invalid_for_online_rl(status) or invalid_reason is not None
        if invalid_reason == "missing_generation_records":
            status = "invalid"
            status_reason = invalid_reason
            invalid_for_training = True
            invalid_for_online_rl = True
        elif invalid_reason in {"gateway_route_mismatch", "gateway_inference_backend_mismatch"}:
            status = "infrastructure_error"
            status_reason = invalid_reason
            invalid_for_training = True
            invalid_for_online_rl = True
        elif invalid_reason in {
            "empty_response",
            "prompt_length_exceeded",
            "response_length_exceeded",
            "response_logprobs_length_mismatch",
        }:
            status = "invalid"
            status_reason = invalid_reason
            invalid_for_training = True
            invalid_for_online_rl = True
        elif invalid_reason not in {
            None,
            "missing_response_logprobs",
            "provider_route_invalid_for_online_rl",
            "non_verl_route_invalid_for_online_rl",
            "tool_observation_tokenizer_unavailable",
        }:
            status = "timeout" if _is_timeout_reason(invalid_reason) else "infrastructure_error"
            status_reason = invalid_reason
            invalid_for_training = True
            invalid_for_online_rl = True
        else:
            status_reason = status_reason or invalid_reason or real_run.agent_state.agent_stop_reason

        if reward_boundary is not None:
            invalid_for_training = reward_boundary.invalid_for_training or invalid_for_training
            invalid_for_online_rl = reward_boundary.invalid_for_online_rl or invalid_for_online_rl
            if invalid_reason in {
                None,
                "missing_response_logprobs",
                "provider_route_invalid_for_online_rl",
                "non_verl_route_invalid_for_online_rl",
                "tool_observation_tokenizer_unavailable",
            }:
                status = reward_boundary.status
                status_reason = reward_boundary.status_reason or status_reason

        diagnostics.extend(self._write_real_episode_audit_evidence(request, real_run, reward_boundary))
        diagnostics.extend(
            self._finalize_real_episode_audit(
                request,
                real_run,
                status=status,
                status_reason=status_reason,
                reward_boundary=reward_boundary,
            )
        )
        real_run = self._refresh_real_episode_artifact_stats(real_run)
        diagnostics.extend(self._real_episode_diagnostics_for_invalid_reason(invalid_reason))
        timing_summary = self._real_episode_timing_summary(
            elapsed_seconds=elapsed_seconds,
            model_call_seconds=model_call_seconds,
            cleanup_seconds=cleanup_seconds,
            real_run=real_run,
            reward_boundary=reward_boundary,
            resource_handle=resource_handle,
        )
        budget_consumption = self._real_episode_budget_consumption(
            request,
            real_run,
            stop_reason=status_reason,
            timing_summary=timing_summary,
        )
        reward_score = None
        if reward_boundary is not None and not invalid_for_training:
            reward_score = reward_boundary.reward_score
        training_view = self._training_view_from_real_episode(
            request,
            real_run,
            status=status,
            reward_score=reward_score,
            invalid_for_training=invalid_for_training,
            invalid_for_online_rl=invalid_for_online_rl,
            invalid_reason=status_reason,
            gateway_route=_generation_route_projection(generation_records),
            stage7_extra_fields=None if reward_boundary is None else reward_boundary.extra_fields,
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
            audit_ref=self._audit_ref(request, reward_boundary=reward_boundary),
            audit_diagnostics=diagnostics,
            reward=None if reward_boundary is None else reward_boundary.reward_summary,
            verifier_summary=(
                self._verifier_summary(status) if reward_boundary is None else reward_boundary.verifier_summary
            ),
            generation_records=generation_records,
            timing_summary=timing_summary,
            resource_summary=self._real_episode_resource_summary(
                request,
                real_run=real_run,
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
        gateway_route: str | None = None,
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

    def _training_view_from_real_episode(
        self,
        request: RepoHarnessEpisodeRequest,
        real_run: RealEpisodeRun,
        *,
        status: EpisodeStatusName,
        reward_score: float | None,
        invalid_for_training: bool,
        invalid_for_online_rl: bool,
        invalid_reason: str | None,
        gateway_route: str | None = None,
        stage7_extra_fields: dict[str, str | int | float | bool | None] | None = None,
    ) -> TrainingView:
        response_ids: list[int] = []
        response_mask: list[Literal[0, 1]] = []
        response_logprobs: list[float] = []
        missing_logprobs = False
        spans: list[ResponseSpan] = []
        tool_messages_by_call_id: dict[str, dict[str, Any]] = {}
        for message in real_run.agent_state.messages:
            if message.get("role") != "tool":
                continue
            tool_call_id = message.get("tool_call_id")
            if tool_call_id:
                tool_messages_by_call_id[str(tool_call_id)] = dict(message)

        consumed_tool_call_ids: set[str] = set()
        for collected in real_run.collector.records:
            record = collected.generation_record
            start = len(response_ids)
            response_ids.extend(record.output_token_ids)
            response_mask.extend([1] * len(record.output_token_ids))
            if record.output_logprobs is None:
                missing_logprobs = True
            else:
                response_logprobs.extend(record.output_logprobs)
            end = len(response_ids)
            if end > start:
                spans.append(
                    ResponseSpan(
                        start=start,
                        end=end,
                        source_type="assistant_generation",
                        model_call_id=record.model_call_id,
                        artifact_ref=f"rh://model-call/{record.model_call_id}/assistant-output",
                        response_mask_value=1,
                        logprob_policy=(
                            "gateway_output_logprobs"
                            if record.output_logprobs is not None
                            else "missing_logprobs_invalid_for_online_rl"
                        ),
                        policy_version=record.policy_version,
                        global_steps=record.global_steps or 0,
                        min_global_steps=record.min_global_steps or record.global_steps or 0,
                        max_global_steps=record.max_global_steps or record.global_steps or 0,
                    )
                )
            for tool_call in collected.response.tool_calls:
                tool_call_id = str(tool_call.get("tool_call_id") or "")
                if not tool_call_id:
                    continue
                tool_message = tool_messages_by_call_id.get(tool_call_id)
                if tool_message is None:
                    continue
                consumed_tool_call_ids.add(tool_call_id)
                tool_tokens = self._project_tool_observation_tokens(str(tool_message.get("content", "")))
                if not tool_tokens:
                    continue
                tool_start = len(response_ids)
                response_ids.extend(tool_tokens)
                response_mask.extend([0] * len(tool_tokens))
                if not missing_logprobs:
                    response_logprobs.extend([0.0] * len(tool_tokens))
                tool_end = len(response_ids)
                spans.append(
                    ResponseSpan(
                        start=tool_start,
                        end=tool_end,
                        source_type="tool_observation",
                        tool_call_id=str(tool_message.get("tool_call_id") or "unknown_tool_call"),
                        artifact_ref=f"rh://tool-observation/{tool_message.get('tool_result_id') or tool_start}",
                        response_mask_value=0,
                        logprob_policy="tool_observation_zero_logprob",
                        policy_version={},
                        global_steps=record.global_steps or 0,
                        min_global_steps=record.min_global_steps or record.global_steps or 0,
                        max_global_steps=record.max_global_steps or record.global_steps or 0,
                    )
                )
        for tool_call_id, tool_message in tool_messages_by_call_id.items():
            if tool_call_id in consumed_tool_call_ids:
                continue
            tool_tokens = self._project_tool_observation_tokens(str(tool_message.get("content", "")))
            if not tool_tokens:
                continue
            tool_start = len(response_ids)
            response_ids.extend(tool_tokens)
            response_mask.extend([0] * len(tool_tokens))
            if not missing_logprobs:
                response_logprobs.extend([0.0] * len(tool_tokens))
            tool_end = len(response_ids)
            spans.append(
                ResponseSpan(
                    start=tool_start,
                    end=tool_end,
                    source_type="tool_observation",
                    tool_call_id=tool_call_id,
                    artifact_ref=f"rh://tool-observation/{tool_message.get('tool_result_id') or tool_start}",
                    response_mask_value=0,
                    logprob_policy="tool_observation_zero_logprob",
                    policy_version={},
                    global_steps=0,
                    min_global_steps=0,
                    max_global_steps=0,
                )
            )
        prompt_ids = real_run.collector.records[0].generation_record.prompt_ids if real_run.collector.records else []
        return TrainingView(
            online_rl_eligible=not invalid_for_training and not invalid_for_online_rl,
            rollout_limits=RolloutLimits(
                prompt_length=max(request.budgets.max_prompt_tokens or 10**9, len(prompt_ids)),
                response_length=request.budgets.max_output_tokens or max(len(response_ids), 1),
            ),
            prompt_ids=list(prompt_ids),
            response_ids=response_ids,
            response_mask=response_mask,
            response_logprobs=None if missing_logprobs else response_logprobs,
            response_spans=spans,
            reward_score=reward_score,
            num_turns=real_run.agent_state.turn_count,
            extra_fields=self._extra_fields(
                request,
                gateway_route=gateway_route,
                status=status,
                invalid_for_training=invalid_for_training,
                invalid_for_online_rl=invalid_for_online_rl,
                invalid_reason=invalid_reason,
                extra_fields=stage7_extra_fields,
            ),
        )

    def _project_tool_observation_tokens(self, content: str) -> list[int]:
        if self.options.tool_observation_token_projector is not None:
            return list(self.options.tool_observation_token_projector(content))
        if not content:
            return []
        return [10_000 + byte for byte in content.encode("utf-8")[:256]]

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

    def _real_episode_invalid_reason(
        self,
        request: RepoHarnessEpisodeRequest,
        real_run: RealEpisodeRun,
    ) -> str | None:
        records = real_run.collector.records
        if not records:
            return "missing_generation_records"
        for collected in records:
            response_error_reason = _response_error_reason(collected.response)
            if response_error_reason is not None:
                return response_error_reason
            record = collected.generation_record
            if record.gateway_route != request.llm_gateway_route:
                return "gateway_route_mismatch"
            if record.inference_backend != request.inference_backend:
                return "gateway_inference_backend_mismatch"
            if not record.output_token_ids:
                return "empty_response"
            if (
                request.budgets.max_prompt_tokens is not None
                and len(record.prompt_ids) > request.budgets.max_prompt_tokens
            ):
                return "prompt_length_exceeded"
            if record.output_logprobs is None:
                return "missing_response_logprobs"
            if len(record.output_logprobs) != len(record.output_token_ids):
                return "response_logprobs_length_mismatch"
        if (
            request.budgets.max_output_tokens is not None
            and self._real_episode_response_token_count(real_run) > request.budgets.max_output_tokens
        ):
            return "response_length_exceeded"
        if any(collected.generation_record.gateway_route in PROVIDER_ROUTES for collected in records):
            return "provider_route_invalid_for_online_rl"
        if request.llm_gateway_route != "verl" or any(
            collected.generation_record.gateway_route != "verl" for collected in records
        ):
            return "non_verl_route_invalid_for_online_rl"
        if self.options.tool_observation_token_projector is None and self._real_episode_has_tool_observations(real_run):
            return "tool_observation_tokenizer_unavailable"
        return None

    def _real_episode_response_token_count(self, real_run: RealEpisodeRun) -> int:
        total = sum(len(collected.generation_record.output_token_ids) for collected in real_run.collector.records)
        for message in real_run.agent_state.messages:
            if message.get("role") == "tool":
                total += len(self._project_tool_observation_tokens(str(message.get("content", ""))))
        return total

    def _real_episode_has_tool_observations(self, real_run: RealEpisodeRun) -> bool:
        return any(message.get("role") == "tool" for message in real_run.agent_state.messages)

    def _real_episode_diagnostics_for_invalid_reason(self, invalid_reason: str | None) -> list[AuditDiagnostic]:
        if invalid_reason is None:
            return []
        return [
            AuditDiagnostic(
                code=invalid_reason,
                message=f"real_episode token provenance marked sample invalid: {invalid_reason}",
            )
        ]

    def _write_real_episode_audit_evidence(
        self,
        request: RepoHarnessEpisodeRequest,
        real_run: RealEpisodeRun,
        reward_boundary: Stage7RewardBoundaryResult | None,
    ) -> list[AuditDiagnostic]:
        if reward_boundary is None:
            return []
        try:
            recorder_profile = RecorderProfile.for_run_mode(request.run_mode)
            with RunRecorder(
                request.run_id,
                real_run.run_dir,
                task_id=request.task_id,
                max_artifact_bytes=request.budgets.max_artifact_bytes,
                recorder_profile=recorder_profile,
            ) as recorder:
                recorder.write_json_artifact(
                    "final_verifier",
                    reward_boundary.verifier_summary.model_dump(mode="json"),
                    {
                        "redaction_status": "not_sensitive",
                        "retention_policy": "keep",
                        "budget_policy": "preserve_json",
                    },
                )
                recorder.write_json_artifact(
                    "reward_metadata",
                    (
                        reward_boundary.reward_metadata.model_dump(mode="json")
                        if reward_boundary.reward_metadata is not None
                        else reward_boundary.reward_summary.model_dump(mode="json")
                    ),
                    {
                        "redaction_status": "not_sensitive",
                        "retention_policy": "keep",
                        "budget_policy": "preserve_json",
                    },
                )
        except Exception as exc:
            return [
                AuditDiagnostic(
                    code="real_episode_audit_evidence_write_failed",
                    message=str(exc),
                )
            ]
        return []

    def _finalize_real_episode_audit(
        self,
        request: RepoHarnessEpisodeRequest,
        real_run: RealEpisodeRun,
        *,
        status: EpisodeStatusName,
        status_reason: str | None,
        reward_boundary: Stage7RewardBoundaryResult | None,
    ) -> list[AuditDiagnostic]:
        try:
            recorder_profile = RecorderProfile.for_run_mode(request.run_mode)
            with RunRecorder(
                request.run_id,
                real_run.run_dir,
                task_id=request.task_id,
                max_artifact_bytes=request.budgets.max_artifact_bytes,
                recorder_profile=recorder_profile,
            ) as recorder:
                recorder.finalize_run(
                    _real_episode_run_summary(
                        request,
                        real_run,
                        status=status,
                        status_reason=status_reason,
                        reward_boundary=reward_boundary,
                    )
                )
        except Exception as exc:
            return [
                AuditDiagnostic(
                    code="real_episode_audit_finalize_failed",
                    message=str(exc),
                )
            ]
        return []

    def _refresh_real_episode_artifact_stats(self, real_run: RealEpisodeRun) -> RealEpisodeRun:
        manifest = load_artifact_manifest(real_run.run_dir)
        artifacts = list(manifest.get("artifacts", []))
        return replace(
            real_run,
            artifact_count=len(artifacts),
            artifact_bytes_written=sum(int(artifact.get("size_bytes", 0)) for artifact in artifacts),
        )

    def _real_episode_timing_summary(
        self,
        *,
        elapsed_seconds: float,
        model_call_seconds: float,
        cleanup_seconds: float,
        real_run: RealEpisodeRun,
        reward_boundary: Stage7RewardBoundaryResult | None,
        resource_handle: ResourceLeaseHandle | None = None,
    ) -> TimingSummary:
        resource_queue_wait_seconds = 0.0
        if resource_handle is not None:
            resource_queue_wait_seconds = sum(
                resource_handle.lease.queue_wait_seconds_by_resource.values()
            )
        verifier_queue_wait_seconds = 0.0 if reward_boundary is None else reward_boundary.verifier_queue_wait_seconds
        total_queue_wait_seconds = resource_queue_wait_seconds + verifier_queue_wait_seconds
        tool_seconds = _tool_seconds_from_run_dir(real_run.run_dir, real_run.agent_state)
        final_verifier_seconds = 0.0 if reward_boundary is None else reward_boundary.final_verifier_seconds
        reward_compute_seconds = 0.0 if reward_boundary is None else reward_boundary.reward_compute_seconds
        workspace_seconds = real_run.workspace.lease_handle.workspace_materialization_seconds
        dependency_seconds = real_run.workspace.lease_handle.dependency_restore_seconds
        agent_loop_overhead_seconds = max(
            0.0,
            real_run.agent_loop_seconds - model_call_seconds - tool_seconds,
        )
        return build_timing_summary(
            rollout_wall_seconds=elapsed_seconds,
            queue_wait_seconds=total_queue_wait_seconds,
            workspace_materialization_seconds=workspace_seconds,
            dependency_restore_seconds=dependency_seconds,
            agent_loop_seconds=agent_loop_overhead_seconds,
            model_call_seconds=model_call_seconds,
            tool_seconds=tool_seconds,
            final_verifier_seconds=final_verifier_seconds,
            reward_compute_seconds=reward_compute_seconds,
            cleanup_seconds=cleanup_seconds,
            model_call_count=len(real_run.collector.records),
            tool_call_count=real_run.agent_state.tool_call_count,
            verifier_call_count=0 if reward_boundary is None else 1,
            artifact_count=real_run.artifact_count,
            artifact_bytes_written=real_run.artifact_bytes_written,
        )

    def _real_episode_budget_consumption(
        self,
        request: RepoHarnessEpisodeRequest,
        real_run: RealEpisodeRun,
        *,
        stop_reason: str | None,
        timing_summary: TimingSummary,
    ) -> BudgetConsumption:
        return BudgetConsumption(
            max_turns=request.budgets.max_turns,
            used_turns=real_run.agent_state.turn_count,
            max_wall_seconds=request.budgets.max_wall_seconds,
            used_wall_seconds=timing_summary.rollout_wall_seconds,
            max_model_calls=request.budgets.max_model_calls,
            used_model_calls=real_run.agent_state.budget_state.model_call_count,
            max_model_call_seconds=request.budgets.generation_timeout_seconds
            or request.budgets.max_model_call_seconds,
            used_model_call_seconds=timing_summary.model_call_seconds,
            max_tool_calls=request.budgets.max_tool_calls,
            used_tool_calls=real_run.agent_state.tool_call_count,
            max_artifact_bytes=request.budgets.max_artifact_bytes,
            used_artifact_bytes=timing_summary.artifact_bytes_written,
            stop_reason=stop_reason,
            rollout_response_length=request.budgets.max_output_tokens,
            actual_response_length=self._real_episode_response_token_count(real_run),
        )

    def _real_episode_resource_summary(
        self,
        request: RepoHarnessEpisodeRequest,
        *,
        real_run: RealEpisodeRun,
        cleanup_status: str,
        reward_boundary: Stage7RewardBoundaryResult | None,
        resource_handle: ResourceLeaseHandle | None = None,
    ) -> ResourceSummary:
        base = self._resource_summary(
            request,
            cleanup_status=cleanup_status,
            reward_boundary=reward_boundary,
            resource_handle=resource_handle,
        )
        fields = real_run.workspace.snapshot_manager.resource_summary_fields(
            snapshot=real_run.workspace.snapshot,
            lease=real_run.workspace.lease_handle.lease,
            workspace_backend="local_process",
            dependency_cache_key=(
                real_run.workspace.dependency_environment.dependency_cache_key
                if real_run.workspace.dependency_environment is not None
                else real_run.run_workspace.dependency_state.cache_key
            ),
            dependency_cache_hit=(
                None
                if real_run.workspace.dependency_environment is None
                else real_run.workspace.dependency_environment.cache_hit
            ),
            run_dir=f"runs/{request.run_id}",
        )
        return base.model_copy(
            update={
                **fields,
                "execution_mode": self._runtime_execution_mode(),
                "workspace_backend": "local_process",
                "inference_route": request.llm_gateway_route,
                "inference_backend": request.inference_backend,
                "repo_harness_environment_ref": (
                    None
                    if real_run.workspace.dependency_environment is None
                    else real_run.workspace.dependency_environment.environment_ref
                ),
                "cleanup_status": cleanup_status,
            }
        )

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
        return await self._stage7_reward_boundary_for_callable(request, final_verifier_callable)

    async def _stage7_reward_boundary_for_callable(
        self,
        request: RepoHarnessEpisodeRequest,
        final_verifier_callable: FinalVerifierCallable,
    ) -> Stage7RewardBoundaryResult:
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
            timed_out_at = perf_counter()
            await _wait_for_cancelled_asyncio_future(future)
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
                diagnostics=[
                    "direct verifier timeout elapsed at "
                    f"{timed_out_at - started_at:.6f}s; waited for callable completion before resource release"
                ],
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
            execution_mode=self._runtime_execution_mode(),
            workspace_backend=self._runtime_execution_mode(),
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


def _generation_route_projection(records: list[GenerationRecord]) -> str | None:
    routes = {record.gateway_route for record in records}
    if len(routes) == 1:
        return next(iter(routes))
    if len(routes) > 1:
        return "mixed"
    return None


def _batch_safe_invalid_reason(value: str | None) -> str | None:
    if value == "run_directory_lock_conflict":
        return "run_lock_conflict"
    if value == "run_directory_already_finalized":
        return "run_already_finalized"
    return value


def _tool_seconds_from_agent_state(state: AgentLoopState) -> float:
    # AgentLoop stores exact tool durations in trajectory events, but the state
    # only carries aggregate counts. Stage 11.5 keeps this bucket conservative
    # until a shared event summarizer owns cross-recorder timing extraction.
    if state.tool_call_count <= 0:
        return 0.0
    return 0.0


def _tool_seconds_from_run_dir(run_dir: Path, state: AgentLoopState) -> float:
    event_path = run_dir / "events.jsonl"
    if not event_path.exists():
        return _tool_seconds_from_agent_state(state)
    total = 0.0
    for line in event_path.read_text(encoding="utf-8").splitlines():
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        event_type = str(payload.get("event_type", ""))
        if not any(marker in event_type for marker in ("tool_call", "tool_execution", "workspace_command")):
            continue
        duration_ms = payload.get("duration_ms")
        if isinstance(duration_ms, int | float):
            total += max(0.0, float(duration_ms) / 1000.0)
    if total > 0.0:
        return total
    return _tool_seconds_from_agent_state(state)


def _real_episode_run_summary(
    request: RepoHarnessEpisodeRequest,
    real_run: RealEpisodeRun,
    *,
    status: EpisodeStatusName,
    status_reason: str | None,
    reward_boundary: Stage7RewardBoundaryResult | None,
) -> str:
    verifier_status = None if reward_boundary is None else reward_boundary.verifier_summary.status
    reward_score = None if reward_boundary is None else reward_boundary.reward_score
    return (
        "# RepoHarness real episode summary\n\n"
        f"- episode_id: {request.episode_id}\n"
        f"- run_id: {request.run_id}\n"
        f"- task_id: {request.task_id}\n"
        f"- runtime_execution_mode: real_episode\n"
        f"- status: {status}\n"
        f"- status_reason: {status_reason or status}\n"
        f"- agent_stop_reason: {real_run.agent_state.agent_stop_reason}\n"
        f"- turn_count: {real_run.agent_state.turn_count}\n"
        f"- model_call_count: {real_run.agent_state.budget_state.model_call_count}\n"
        f"- tool_call_count: {real_run.agent_state.tool_call_count}\n"
        f"- generation_record_count: {len(real_run.collector.records)}\n"
        f"- final_verifier_status: {verifier_status}\n"
        f"- reward_score: {reward_score}\n"
    )


async def _wait_for_real_episode_task_after_stop(
    task: asyncio.Task[RealEpisodeRun],
    *,
    stop_kind: Literal["cancelled", "timeout"],
) -> tuple[RealEpisodeRun | None, list[AuditDiagnostic]]:
    diagnostics = [
        AuditDiagnostic(
            code=f"real_episode_thread_wait_after_{stop_kind}",
            message=(
                "real_episode uses a synchronous legacy AgentLoop in a worker thread; "
                "workspace and resource leases are held until that thread finishes"
            ),
        )
    ]
    while not task.done():
        try:
            result = await asyncio.shield(task)
            return result, diagnostics
        except asyncio.CancelledError:
            continue
        except Exception as exc:
            diagnostics.append(
                AuditDiagnostic(
                    code="real_episode_thread_failed_after_stop",
                    message=str(exc),
                )
            )
            return None, diagnostics
    try:
        return task.result(), diagnostics
    except asyncio.CancelledError:
        diagnostics.append(
            AuditDiagnostic(
                code="real_episode_thread_cancelled_after_stop",
                message="real_episode worker task ended with cancellation",
            )
        )
    except Exception as exc:
        diagnostics.append(
            AuditDiagnostic(
                code="real_episode_thread_failed_after_stop",
                message=str(exc),
            )
        )
    return None, diagnostics


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


async def _generate_gateway_turn(
    gateway: LLMGateway,
    request: LLMGatewayRequest,
    *,
    resource_lease_manager: ResourceLeaseManager | None = None,
    resource_handle: ResourceLeaseHandle | None = None,
) -> LLMGatewayResponse:
    if resource_lease_manager is None or resource_handle is None:
        return await gateway.generate_turn(request)
    async with resource_lease_manager.route_call(handle=resource_handle, route=request.route):
        return await gateway.generate_turn(request)


def _run_gateway_turn_blocking(
    gateway: LLMGateway,
    request: LLMGatewayRequest,
    *,
    resource_lease_manager: ResourceLeaseManager | None = None,
    resource_handle: ResourceLeaseHandle | None = None,
    runtime_loop: asyncio.AbstractEventLoop | None = None,
) -> LLMGatewayResponse:
    if runtime_loop is not None:
        future = asyncio.run_coroutine_threadsafe(
            _generate_gateway_turn(
                gateway,
                request,
                resource_lease_manager=resource_lease_manager,
                resource_handle=resource_handle,
            ),
            runtime_loop,
        )
        return future.result()
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(
            _generate_gateway_turn(
                gateway,
                request,
                resource_lease_manager=resource_lease_manager,
                resource_handle=resource_handle,
            )
        )
    raise RuntimeError("LLMGatewayModelClientAdapter.generate must run outside an active event loop")
