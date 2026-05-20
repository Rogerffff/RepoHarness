"""RepoHarness AgentLoop adapter for verl."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
from collections.abc import Mapping
from pathlib import Path
from time import time
from typing import Any

from repo_harness.rl import RepoHarnessRuntime, RepoHarnessRuntimeOptions
from repo_harness.rl.partial_checkpoint import (
    compute_partial_checkpoint_visibility_digest,
    validate_partial_checkpoint_not_trainable,
    validate_partial_checkpoint_roundtrip,
)
from repo_harness.verifier import VerifierResult
import yaml

from .conversion import VerlConversionError, episode_result_to_agent_loop_output
from .errors import RepoHarnessVerlAdapterError, RepoHarnessVerlRequestMappingError
from .gateway import VerlLLMGateway
from .partial_rollout import DEFAULT_STAGE15_VISIBILITY_DIGEST
from .request_mapping import build_episode_request_from_verl_kwargs, validate_repo_harness_verl_kwargs

try:
    from verl.experimental.agent_loop.agent_loop import AgentLoopBase, register
except Exception as exc:  # pragma: no cover - exercised by environment preflight.
    raise RepoHarnessVerlAdapterError(
        "failed_to_import_verl_agent_loop_base; expose reference/verl and its dependencies before importing "
        "repo_harness_verl.agent_loop"
    ) from exc


@register("repo_harness")
class RepoHarnessVerlAgentLoop(AgentLoopBase):
    """通过 verl AgentLoopBase 调用 RepoHarnessRuntime.run_episode(...)。"""

    def __init__(
        self,
        *args: Any,
        runtime: RepoHarnessRuntime | None = None,
        runtime_options: RepoHarnessRuntimeOptions | None = None,
        inference_backend: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        if runtime_options is None:
            runtime_options = _runtime_options_from_environment()
        elif not isinstance(runtime_options, RepoHarnessRuntimeOptions):
            runtime_options = RepoHarnessRuntimeOptions(**dict(runtime_options))  # type: ignore[arg-type]
        self.runtime = runtime or RepoHarnessRuntime(options=runtime_options)
        self.repo_harness_inference_backend = inference_backend

    async def run(self, sampling_params: dict[str, Any], **kwargs: Any) -> Any:
        """从 verl 样本字段构造 RepoHarness episode，并返回真实 AgentLoopOutput。"""

        try:
            validated_kwargs = validate_repo_harness_verl_kwargs(kwargs)
            request = build_episode_request_from_verl_kwargs(
                validated_kwargs,
                sampling_params=sampling_params,
                trainer_config=self.config,
                rollout_config=self.rollout_config,
                inference_backend=self.repo_harness_inference_backend,
            )
            gateway = VerlLLMGateway(
                server_manager=self.server_manager,
                tokenizer=self.tokenizer,
                processor=self.processor,
                inference_backend=request.inference_backend,
                sampling_params=sampling_params,
                prompt_ids_builder=self._build_prompt_ids_for_gateway_request,
            )
            partial_control = _coerce_partial_rollout_control(
                validated_kwargs.get("repo_harness_partial_rollout_control")
            )
            if partial_control["enabled"]:
                runtime_mode = self.runtime.options.runtime_execution_mode or self.runtime.options.execution_mode
                requested_mode = validated_kwargs.get("repo_harness_runtime_execution_mode")
                if requested_mode is not None and str(requested_mode) != "real_episode":
                    raise RepoHarnessVerlAdapterError(
                        "partial_rollout_control_requires_repo_harness_runtime_execution_mode_real_episode"
                    )
                if runtime_mode != "real_episode":
                    raise RepoHarnessVerlAdapterError(
                        "partial_rollout_control_requires_runtime_execution_mode_real_episode"
                    )
                result = await self._run_controlled_partial_rollout_episode(
                    request,
                    gateway=gateway,
                    partial_control=partial_control,
                )
            else:
                result = await self.runtime.run_episode(request, llm_gateway=gateway)
            try:
                return episode_result_to_agent_loop_output(
                    result,
                    formal_online_rl=True,
                    rollout_prompt_length=_optional_int_config(self.rollout_config, "prompt_length"),
                    rollout_response_length=_optional_int_config(self.rollout_config, "response_length"),
                )
            except VerlConversionError as exc:
                diagnostics = [
                    f"{diagnostic.code}: {diagnostic.message}"
                    for diagnostic in result.audit_diagnostics[:5]
                ]
                raise RepoHarnessVerlAdapterError(
                    "episode_result_not_formal_online_rl: "
                    f"episode_id={result.episode_id} "
                    f"run_id={result.run_id} "
                    f"status={result.status} "
                    f"status_reason={result.status_reason} "
                    f"diagnostics={diagnostics}: {exc}"
                ) from exc
        except RepoHarnessVerlRequestMappingError:
            raise

    async def _run_controlled_partial_rollout_episode(
        self,
        request: Any,
        *,
        gateway: VerlLLMGateway,
        partial_control: dict[str, Any],
    ) -> Any:
        """在同进程内执行一次 partial checkpoint / resume。

        partial checkpoint 本身只作为 runtime-private evidence；能够进入
        policy-loss 路径的仍然只能是恢复后的完整终态 episode result。
        """

        handle = await self.runtime.start_episode(request, llm_gateway=gateway)
        checkpoint = None
        resume_attempt_id: str | None = None
        try:
            pause_outcome = await handle.request_pause_at_next_turn_boundary(
                reason="stage15_2_controlled_partial_rollout_requested",
                timeout=float(partial_control["pause_wait_timeout_seconds"]),
            )
            if pause_outcome.status != "paused" or pause_outcome.checkpoint is None:
                await self._cancel_partial_handle(
                    handle,
                    reason=f"stage15_2_pause_not_created:{pause_outcome.status}",
                    wait_timeout_seconds=float(partial_control["pause_cancel_wait_timeout_seconds"]),
                )
                _emit_stage15_partial_event(
                    "partial_checkpoint_not_created",
                    {
                        "episode_id": request.episode_id,
                        "run_id": request.run_id,
                        "pause_status": pause_outcome.status,
                    },
                )
                raise RepoHarnessVerlAdapterError(
                    f"partial_checkpoint_not_created:{pause_outcome.status}"
                )

            checkpoint = validate_partial_checkpoint_roundtrip(pause_outcome.checkpoint)
            validate_partial_checkpoint_not_trainable(checkpoint)
            visibility_digest = compute_partial_checkpoint_visibility_digest(checkpoint)
            _emit_stage15_partial_event(
                "partial_checkpoint_generated",
                {
                    "episode_id": checkpoint.episode_id,
                    "run_id": checkpoint.run_id,
                    "task_id": checkpoint.task_id,
                    "checkpoint_id": checkpoint.checkpoint_id,
                    "checkpoint_status": checkpoint.checkpoint_status,
                    "content_digest": checkpoint.content_digest,
                    "trajectory_digest": checkpoint.token_provenance.trajectory_digest,
                    "generation_record_digest": checkpoint.token_provenance.generation_record_digest,
                    "visibility_digest": visibility_digest,
                    "policy_loss_consumed": False,
                    "native_partial_rollout_enabled": bool(partial_control["native_partial_rollout_enabled"]),
                    "native_abort_signal_visible_to_repo_harness": False,
                    "controlled_turn_boundary_trigger_used": True,
                    "repo_harness_checkpoint_generated_by_controlled_trigger": True,
                },
            )

            resume_attempt_id = f"{checkpoint.checkpoint_id}:resume-0"
            resume_outcome = await handle.resume(checkpoint)
            _emit_stage15_partial_event(
                "resume_attempted",
                {
                    "episode_id": checkpoint.episode_id,
                    "run_id": checkpoint.run_id,
                    "checkpoint_id": checkpoint.checkpoint_id,
                    "resume_attempt_id": resume_attempt_id,
                    "resume_status": resume_outcome.status,
                },
            )
            if resume_outcome.status != "resumed":
                await self._cancel_partial_handle(
                    handle,
                    reason=f"stage15_2_resume_not_accepted:{resume_outcome.status}",
                    wait_timeout_seconds=float(partial_control["resume_cancel_wait_timeout_seconds"]),
                )
                raise RepoHarnessVerlAdapterError(f"partial_resume_not_accepted:{resume_outcome.status}")

            try:
                result = await handle.wait_result(timeout=float(partial_control["resume_wait_timeout_seconds"]))
            except asyncio.TimeoutError as exc:
                await self._cancel_partial_handle(
                    handle,
                    reason="stage15_2_resume_wait_timeout",
                    wait_timeout_seconds=float(partial_control["resume_cancel_wait_timeout_seconds"]),
                )
                _emit_stage15_partial_event(
                    "resume_timeout",
                    {
                        "episode_id": checkpoint.episode_id,
                        "run_id": checkpoint.run_id,
                        "checkpoint_id": checkpoint.checkpoint_id,
                        "resume_attempt_id": resume_attempt_id,
                    },
                )
                raise RepoHarnessVerlAdapterError("partial_resume_wait_timeout") from exc

            result = _annotate_resumed_episode_result(
                result,
                resume_attempt_id=resume_attempt_id,
                native_partial_rollout_enabled=bool(partial_control["native_partial_rollout_enabled"]),
            )
            _emit_stage15_partial_event(
                "resumed_terminal_result",
                {
                    "episode_id": result.episode_id,
                    "run_id": result.run_id,
                    "task_id": result.task_id,
                    "status": result.status,
                    "status_reason": result.status_reason,
                    "checkpoint_id": checkpoint.checkpoint_id,
                    "resume_attempt_id": resume_attempt_id,
                    "invalid_for_training": result.invalid_for_training,
                    "invalid_for_online_rl": result.invalid_for_online_rl,
                    "reward_score": result.training_view.reward_score,
                    "policy_loss_candidate": not result.invalid_for_training and not result.invalid_for_online_rl,
                },
            )
            return result
        except Exception:
            if checkpoint is not None:
                _emit_stage15_partial_event(
                    "partial_resume_failed",
                    {
                        "episode_id": checkpoint.episode_id,
                        "run_id": checkpoint.run_id,
                        "checkpoint_id": checkpoint.checkpoint_id,
                        "resume_attempt_id": resume_attempt_id,
                    },
                )
            raise

    async def _cancel_partial_handle(
        self,
        handle: Any,
        *,
        reason: str,
        wait_timeout_seconds: float,
    ) -> None:
        try:
            await handle.cancel(reason)
            await handle.wait_result(timeout=wait_timeout_seconds)
        except asyncio.TimeoutError:
            _emit_stage15_partial_event(
                "partial_handle_cancel_wait_timeout",
                {"reason": reason, "run_id": handle.snapshot().run_id},
            )

    async def _build_prompt_ids_for_gateway_request(self, request: Any) -> list[int]:
        from verl.utils.chat_template import apply_chat_template
        from verl.utils.tokenizer import normalize_token_ids

        loop = asyncio.get_running_loop()
        tools = list(request.tools) if request.tools else None
        if self.processor is not None:
            raw_prompt = await loop.run_in_executor(
                None,
                lambda: apply_chat_template(
                    self.processor,
                    list(request.messages),
                    tools=tools,
                    add_generation_prompt=True,
                    tokenize=False,
                    **self.apply_chat_template_kwargs,
                ),
            )
            model_inputs = self.processor(
                text=[raw_prompt],
                images=None,
                videos=None,
                video_metadata=None,
                return_tensors="pt",
                do_sample_frames=False,
            )
            return list(normalize_token_ids(model_inputs.pop("input_ids")))
        tokenized_prompt = await loop.run_in_executor(
            None,
            lambda: apply_chat_template(
                self.tokenizer,
                list(request.messages),
                tools=tools,
                add_generation_prompt=True,
                tokenize=True,
                **self.apply_chat_template_kwargs,
            ),
        )
        return list(normalize_token_ids(tokenized_prompt))


def _optional_int_config(config: Any, key: str) -> int | None:
    if config is None:
        return None
    value = config.get(key) if isinstance(config, dict) else getattr(config, key, None)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _runtime_options_from_environment() -> RepoHarnessRuntimeOptions | None:
    runtime_execution_mode = os.environ.get("REPO_HARNESS_RUNTIME_EXECUTION_MODE")
    output_dir = os.environ.get("REPO_HARNESS_OUTPUT_DIR")
    if not runtime_execution_mode and not output_dir:
        return None
    return RepoHarnessRuntimeOptions(
        runtime_execution_mode=runtime_execution_mode or None,  # type: ignore[arg-type]
        output_dir=output_dir or None,
        real_episode_final_verifier_factory=(
            _task_yaml_final_verifier_factory
            if os.environ.get("REPO_HARNESS_REAL_EPISODE_TASK_VERIFIER") == "1"
            else None
        ),
    )


def _coerce_partial_rollout_control(value: Any) -> dict[str, Any]:
    if value is None:
        return {
            "enabled": False,
            "pause_wait_timeout_seconds": 5.0,
            "pause_cancel_wait_timeout_seconds": 2.0,
            "resume_wait_timeout_seconds": 30.0,
            "resume_cancel_wait_timeout_seconds": 2.0,
            "visibility_scan_status": "passed",
            "visibility_scan_digest": DEFAULT_STAGE15_VISIBILITY_DIGEST,
            "native_partial_rollout_enabled": False,
        }
    if not isinstance(value, Mapping):
        raise RepoHarnessVerlAdapterError("repo_harness_partial_rollout_control_must_be_mapping")
    payload = dict(value)
    return {
        "enabled": bool(payload.get("enabled", False)),
        "pause_wait_timeout_seconds": _positive_float(
            payload.get("pause_wait_timeout_seconds", 5.0),
            field_name="pause_wait_timeout_seconds",
        ),
        "pause_cancel_wait_timeout_seconds": _positive_float(
            payload.get("pause_cancel_wait_timeout_seconds", 2.0),
            field_name="pause_cancel_wait_timeout_seconds",
        ),
        "resume_wait_timeout_seconds": _positive_float(
            payload.get("resume_wait_timeout_seconds", 30.0),
            field_name="resume_wait_timeout_seconds",
        ),
        "resume_cancel_wait_timeout_seconds": _positive_float(
            payload.get("resume_cancel_wait_timeout_seconds", 2.0),
            field_name="resume_cancel_wait_timeout_seconds",
        ),
        "visibility_scan_status": str(payload.get("visibility_scan_status", "passed")),
        "visibility_scan_digest": str(payload.get("visibility_scan_digest", DEFAULT_STAGE15_VISIBILITY_DIGEST)),
        "native_partial_rollout_enabled": bool(payload.get("native_partial_rollout_enabled", False)),
    }


def _positive_float(value: Any, *, field_name: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise RepoHarnessVerlAdapterError(f"{field_name}_must_be_positive_float") from exc
    if parsed <= 0:
        raise RepoHarnessVerlAdapterError(f"{field_name}_must_be_positive_float")
    return parsed


def _annotate_resumed_episode_result(
    result: Any,
    *,
    resume_attempt_id: str,
    native_partial_rollout_enabled: bool,
) -> Any:
    view = result.training_view
    extra_fields = dict(view.extra_fields)
    extra_fields.update(
        {
            "repo_harness_partial_rollout_supported": True,
            "repo_harness_partial_rollout_status": "complete",
            "repo_harness_resume_attempt_id": resume_attempt_id,
            "repo_harness_stage15_controlled_turn_boundary_trigger_used": True,
            "repo_harness_stage15_native_partial_rollout_enabled": native_partial_rollout_enabled,
            "repo_harness_stage15_native_abort_signal_visible_to_repo_harness": False,
        }
    )
    return result.model_copy(
        update={
            "training_view": view.model_copy(update={"extra_fields": extra_fields}),
        }
    )


def _emit_stage15_partial_event(event_type: str, payload: Mapping[str, Any]) -> None:
    event_dir = os.environ.get("REPO_HARNESS_STAGE15_EVENT_DIR")
    if not event_dir:
        return
    path = Path(event_dir) / "stage15_partial_events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "schema_version": "repo_harness_verl_stage15_partial_event_v0",
        "event_type": event_type,
        "event_time_unix_seconds": time(),
        **dict(payload),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")


def _task_yaml_final_verifier_factory(context: Any):
    task_path = context.request.task_ref.task_path
    if not task_path:
        raise RepoHarnessVerlAdapterError("task_yaml_final_verifier_requires_task_ref_task_path")
    payload = yaml.safe_load(Path(task_path).read_text(encoding="utf-8")) or {}
    command = payload.get("test_command")
    if not command:
        raise RepoHarnessVerlAdapterError("task_yaml_final_verifier_requires_test_command")
    timeout_sec = float((payload.get("timeouts") or {}).get("timeout_sec") or 60)

    def verify() -> VerifierResult:
        completed = subprocess.run(
            str(command),
            cwd=context.workspace_path,
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_sec,
            check=False,
        )
        accepted = completed.returncode == 0
        return VerifierResult(
            verifier_stage="final",
            parser_confidence=1.0,
            command=str(command),
            accepted=accepted,
            pass_ratio=1.0 if accepted else 0.0,
            fail_to_pass={"passed": 1 if accepted else 0, "total": 1},
            pass_to_pass={"passed": 1 if accepted else 0, "total": 1},
            exit_code=completed.returncode,
        )

    return verify
