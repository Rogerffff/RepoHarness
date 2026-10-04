from __future__ import annotations

import asyncio
import contextlib
import io
import json
import logging
import math
import os
import random
import time
from dataclasses import dataclass, field, replace
from functools import partial
from pathlib import Path
from typing import Protocol
from uuid import uuid4

import numpy as np
import ray
import torch
from omegaconf import OmegaConf
from tensordict import TensorDict
from tensordict.tensorclass import NonTensorData, NonTensorStack

from uni_agent.gateway.session import SessionHandle, Trajectory
from uni_agent.logging import LogContext, sample_logging
from verl.tools.tool_registry import initialize_tools_from_config
from verl.utils import tensordict_utils as tu
from verl.utils.import_utils import load_class_from_fqn
from verl.utils.model import compute_position_id_with_mask
from verl.utils.transferqueue_utils import tq

from .base import AgentFramework
from .multi_modal_postprocess import compute_multi_modal_inputs, compute_position_ids

logger = logging.getLogger(__name__)


class AgentRunner(Protocol):
    """Callable contract for OpenAI-compatible agent runners."""

    async def __call__(
        self,
        *,
        session: SessionHandle,
        raw_prompt: object,
        sample_index: int,
        **sample_runner_kwargs: object,
    ) -> object: ...


@dataclass
class _RunnerConfig:
    runner_fqn: str
    runner_kwargs: dict[str, object]
    dispatch_mode: str
    max_concurrent_sessions: int
    trajectory_selection: str = "all"
    session_timeout_seconds: float | None = None
    agent_request_idle_timeout_seconds: float | None = None
    trajectory_timeout_by_dataset: dict[str, float | None] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.runner_fqn:
            raise ValueError("runner_fqn is required")
        if self.dispatch_mode not in {"inline_async", "ray_task"}:
            raise ValueError(f"Unknown dispatch mode: {self.dispatch_mode}")
        if self.max_concurrent_sessions < 0:
            raise ValueError(f"max_concurrent_sessions must be non-negative, got {self.max_concurrent_sessions}")
        if self.trajectory_selection not in {"all", "longest"}:
            raise ValueError(f"Unknown trajectory selection: {self.trajectory_selection}. Expected 'all' or 'longest'")
        if self.session_timeout_seconds is not None and self.session_timeout_seconds <= 0:
            raise ValueError(f"session_timeout_seconds must be positive, got {self.session_timeout_seconds}")
        if self.agent_request_idle_timeout_seconds is not None and self.agent_request_idle_timeout_seconds <= 0:
            raise ValueError(
                "agent_request_idle_timeout_seconds must be positive, "
                f"got {self.agent_request_idle_timeout_seconds}"
            )

    @classmethod
    def from_config(cls, runner_name: object, runner_cfg) -> _RunnerConfig:
        runner_fqn = runner_cfg.get("runner_fqn")
        runner_kwargs = dict(
            OmegaConf.to_container(OmegaConf.create(runner_cfg.get("runner_kwargs", {})), resolve=True) or {}
        )
        tool_config_path = runner_cfg.get("tool_config_path")
        if tool_config_path:
            tool_config = initialize_tools_from_config(str(tool_config_path))
            if not tool_config:
                raise ValueError(
                    f"agent_runners.{runner_name}.tool_config_path did not initialize any tools: {tool_config_path}"
                )
            runner_kwargs["tool_config"] = tool_config
        dispatch_mode = str(runner_cfg.get("dispatch_mode", "inline_async"))
        max_concurrent_sessions = int(runner_cfg.get("max_concurrent_sessions", 0) or 0)
        trajectory_selection = str(runner_cfg.get("trajectory_selection", "all"))
        raw_timeout = runner_cfg.get("session_timeout_seconds")
        session_timeout_seconds = None if raw_timeout is None else float(raw_timeout)
        raw_idle_timeout = runner_cfg.get("agent_request_idle_timeout_seconds")
        agent_request_idle_timeout_seconds = None if raw_idle_timeout is None else float(raw_idle_timeout)
        raw_dataset_timeouts = runner_cfg.get("trajectory_timeout_by_dataset") or {}
        trajectory_timeout_by_dataset = {
            str(dataset_type): (float(timeout) if float(timeout) > 0 else None)
            for dataset_type, timeout in dict(raw_dataset_timeouts).items()
        }
        try:
            return cls(
                runner_fqn="" if runner_fqn is None else str(runner_fqn),
                runner_kwargs=runner_kwargs,
                dispatch_mode=dispatch_mode,
                max_concurrent_sessions=max_concurrent_sessions,
                trajectory_selection=trajectory_selection,
                session_timeout_seconds=session_timeout_seconds,
                agent_request_idle_timeout_seconds=agent_request_idle_timeout_seconds,
                trajectory_timeout_by_dataset=trajectory_timeout_by_dataset,
            )
        except ValueError as exc:
            raise ValueError(f"agent_runners.{runner_name}: {exc}") from exc


def _materialize_runner(runner_fqn: str, runner_kwargs: dict[str, object]):
    runner = load_class_from_fqn(runner_fqn, description="agent runner")
    if isinstance(runner, type):
        return runner(**runner_kwargs)
    if runner_kwargs:
        return partial(runner, **runner_kwargs)
    return runner


def _session_timeout_for_sample(
    runner_config: _RunnerConfig,
    sample_fields: dict[str, object],
) -> float | None:
    """Select the runner wall timeout, allowing mixed validation datasets."""
    if not runner_config.trajectory_timeout_by_dataset:
        return runner_config.session_timeout_seconds

    extra_info = sample_fields.get("extra_info")
    dataset_type = extra_info.get("dataset_type") if isinstance(extra_info, dict) else None
    if dataset_type is None:
        tools_kwargs = sample_fields.get("tools_kwargs")
        if isinstance(tools_kwargs, dict):
            dataset_type = tools_kwargs.get("dataset_type")
    return runner_config.trajectory_timeout_by_dataset.get(
        str(dataset_type), runner_config.session_timeout_seconds
    )


def _log_scope(log_context: LogContext | None):
    if log_context is None:
        return contextlib.nullcontext()
    return sample_logging.from_context(log_context)


def _runner_task_num_cpus() -> float:
    """Return the Ray scheduling token reserved for one agent runner task."""
    raw_value = os.environ.get("UNI_AGENT_RUNNER_TASK_NUM_CPUS", "1")
    try:
        num_cpus = float(raw_value)
    except ValueError as exc:
        raise ValueError(
            "UNI_AGENT_RUNNER_TASK_NUM_CPUS must be a positive number, "
            f"got {raw_value!r}"
        ) from exc
    if not math.isfinite(num_cpus) or num_cpus <= 0:
        raise ValueError(
            "UNI_AGENT_RUNNER_TASK_NUM_CPUS must be a positive number, "
            f"got {raw_value!r}"
        )
    return num_cpus


_RUNNER_TASK_NUM_CPUS = _runner_task_num_cpus()


@ray.remote(num_cpus=_RUNNER_TASK_NUM_CPUS)
def _run_agent_runner_ray_task(
    *,
    runner_fqn: str,
    runner_kwargs: dict[str, object],
    raw_prompt,
    session: SessionHandle,
    sample_index: int,
    tools_kwargs: object | None,
    log_context: LogContext | None,
) -> None:
    """Run only the user runner in Ray; parent owns session lifecycle outputs."""
    runner = _materialize_runner(runner_fqn, runner_kwargs)
    with _log_scope(log_context):
        asyncio.run(
            runner(
                raw_prompt=raw_prompt,
                session=session,
                sample_index=sample_index,
                **({"tools_kwargs": tools_kwargs} if tools_kwargs is not None else {}),
            )
        )


def _short_failure_reason(error: BaseException) -> str:
    message = str(error)
    if not message:
        message = error.__class__.__name__
    return f"{error.__class__.__name__}:{message}"[:512]


class AgentRequestTimeout(asyncio.TimeoutError):
    """The external agent stopped sending requests after a model tool call."""

    def __init__(self, *, idle_seconds: float, pending_tool_call_ids: list[str]):
        self.idle_seconds = idle_seconds
        self.pending_tool_call_ids = list(pending_tool_call_ids)
        super().__init__(
            f"agent sent no follow-up request for {idle_seconds:.1f}s after tool calls "
            f"{self.pending_tool_call_ids}"
        )


def _framework_failure_metadata(error: BaseException) -> dict[str, object]:
    """Describe a hard framework failure without changing its grading policy."""
    extra: dict[str, object] = {}
    if isinstance(error, AgentRequestTimeout):
        status = "timeout"
        termination_kind = "agent_request_timeout"
        extra = {
            "agent_status": "agent_timeout",
            "idle_seconds": error.idle_seconds,
            "pending_tool_call_ids": error.pending_tool_call_ids,
        }
    elif isinstance(error, asyncio.TimeoutError):
        status = "timeout"
        termination_kind = "framework_timeout"
    elif isinstance(error, asyncio.CancelledError):
        status = "cancelled"
        termination_kind = "framework_cancelled"
    else:
        status = "failed"
        termination_kind = "framework_error"
    return {
        "status": status,
        "termination_kind": termination_kind,
        "agent_status": "runner_error",
        "agent_completed": False,
        "finished": False,
        "gradable": False,
        "error_type": error.__class__.__name__,
        "error_message": str(error)[:2000],
        "result": _short_failure_reason(error),
        **extra,
    }


def _select_session_trajectories(
    session_id: str,
    trajectories: list[Trajectory],
    selection: str,
) -> list[Trajectory]:
    """Apply the runner's trajectory-retention policy before scoring and TQ writes."""
    if selection == "all" or len(trajectories) <= 1:
        return trajectories

    index, trajectory = max(
        enumerate(trajectories),
        key=lambda item: (
            sum(item[1].response_mask),
            len(item[1].response_ids),
            item[1].num_turns,
            item[0],
        ),
    )
    logger.info(
        "session %s: selected longest trajectory index=%s model_tokens=%s response_tokens=%s turns=%s candidates=%s",
        session_id,
        index,
        sum(trajectory.response_mask),
        len(trajectory.response_ids),
        trajectory.num_turns,
        len(trajectories),
    )
    return [trajectory]


_TQ_NESTED_SEQUENCE_FIELDS = {
    "prompts",
    "responses",
    "response_mask",
    "loss_mask",
    "input_ids",
    "attention_mask",
    "position_ids",
    "rollout_log_probs",
    "routed_experts",
    "rm_scores",
    "tool_call_error_mask",
    "repetition_mask",
    "turn_index",
    "teacher_logprobs",
    "teacher_ids",
}


def _json_default(obj: object) -> object:
    """Best-effort JSON coercion for reward/extra fields (numpy scalars, tensors, sets)."""
    if isinstance(obj, set | frozenset):
        return list(obj)
    for attr in ("item", "tolist"):  # numpy scalar / 0-d tensor, then ndarray / tensor
        fn = getattr(obj, attr, None)
        if callable(fn):
            try:
                return fn()
            except Exception:
                pass
    return str(obj)


def _align_routed_experts(source: object, seq_len: int) -> torch.Tensor | None:
    """Return R3 routing as ``[seq_len, layers, topk]`` aligned to input_ids."""
    experts = torch.as_tensor(source, device="cpu")
    if experts.dim() != 3:
        return None
    out = torch.zeros((seq_len, experts.shape[1], experts.shape[2]), dtype=experts.dtype)
    covered = min(experts.shape[0], seq_len)
    if covered > 0:
        out[:covered] = experts[:covered]
    return out



_REPETITION_HASH_BASE = np.uint64(1099511628211)  # FNV-1a 64-bit prime, odd so invertible mod 2**64
_REPETITION_HASH_BASE_INV = np.uint64(pow(int(_REPETITION_HASH_BASE), -1, 1 << 64))
_REPETITION_DETECT_DEFAULTS: dict[str, object] = {
    "enable": False,
    "ngram_size": 300,
    "window_size": 8300,
    "min_content_length": 16384,
    "min_repeat": 15,
    "zero_reward": False,
}


def _normalize_repetition_detect_config(raw: object) -> dict[str, object]:
    """Validate ``agent_framework.repetition_detect`` and fill the reference defaults."""
    if raw is None:
        raw = {}
    if OmegaConf.is_config(raw):
        raw = OmegaConf.to_container(raw, resolve=True)
    if not isinstance(raw, dict):
        raise ValueError("actor_rollout_ref.rollout.custom.agent_framework.repetition_detect must be a mapping")
    unknown = set(raw) - set(_REPETITION_DETECT_DEFAULTS)
    if unknown:
        raise ValueError(f"repetition_detect has unknown keys: {sorted(unknown)}")
    cfg = dict(_REPETITION_DETECT_DEFAULTS)
    cfg.update(raw)
    for key in ("enable", "zero_reward"):
        if type(cfg[key]) is not bool:
            raise ValueError(f"repetition_detect.{key} must be a bool")
    for key in ("ngram_size", "window_size", "min_repeat"):
        value = cfg[key]
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"repetition_detect.{key} must be a positive int")
    gate = cfg["min_content_length"]
    if isinstance(gate, bool) or not isinstance(gate, int) or gate < 0:
        raise ValueError("repetition_detect.min_content_length must be a non-negative int")
    if cfg["window_size"] < cfg["ngram_size"]:
        raise ValueError("repetition_detect.window_size must be >= ngram_size")
    return cfg


def _rolling_ngram_hashes(token_ids: np.ndarray, ngram_size: int) -> np.ndarray:
    """64-bit polynomial hash of every ``ngram_size``-token window, wrapping mod 2**64.

    H[i] = sum_{j<n} (t[i+j]+1) * B**(n-1-j). Computed as
    B**(i+n-1) * (S[i+n] - S[i]) with S the prefix sum of (t[j]+1) * B**(-j); B is odd so
    its inverse modulo 2**64 exists and every product wraps consistently in uint64.
    """
    n = int(ngram_size)
    tokens = np.asarray(token_ids, dtype=np.uint64) + np.uint64(1)
    count = tokens.shape[0] - n + 1
    if count <= 0:
        return np.empty(0, dtype=np.uint64)
    with np.errstate(over="ignore"):
        inv_powers = np.cumprod(np.full(tokens.shape[0], _REPETITION_HASH_BASE_INV, dtype=np.uint64))
        inv_powers = np.concatenate([np.ones(1, dtype=np.uint64), inv_powers[:-1]])  # B**(-j)
        prefix = np.concatenate([np.zeros(1, dtype=np.uint64), np.cumsum(tokens * inv_powers, dtype=np.uint64)])
        powers = np.cumprod(np.full(tokens.shape[0], _REPETITION_HASH_BASE, dtype=np.uint64))  # B**(i+1)
        scale = powers[n - 2 : n - 2 + count] if n >= 2 else np.ones(count, dtype=np.uint64)
        return (prefix[n : n + count] - prefix[:count]) * scale


def repetition_first_hit(
    token_ids,
    *,
    ngram_size: int = 300,
    window_size: int = 8300,
    min_content_length: int = 16384,
    min_repeat: int = 15,
) -> int:
    """Token offset (exclusive end of the repeated n-gram) of the first repetition hit, or -1.

    Same predicate as the reference ``_check_repetition_tokens``: at position ``i`` the window
    holds the n-grams starting in ``[i + ngram_size - window_size, i]``; a hit is the first
    ``i`` whose n-gram occurs at least ``min_repeat`` times in that window.
    """
    seq_len = len(token_ids)
    if seq_len < min_content_length or seq_len < ngram_size:
        return -1
    if min_repeat <= 1:
        return ngram_size
    hashes = _rolling_ngram_hashes(token_ids, ngram_size)
    order = np.argsort(hashes, kind="stable")  # groups equal hashes, positions ascending within a group
    sorted_hashes = hashes[order]
    positions = order.astype(np.int64)
    lag = min_repeat - 1
    if positions.shape[0] <= lag:
        return -1
    same = sorted_hashes[lag:] == sorted_hashes[:-lag]
    within = (positions[lag:] - positions[:-lag]) <= (window_size - ngram_size)
    candidates = positions[lag:][same & within]
    if candidates.size == 0:
        return -1
    return int(candidates.min()) + ngram_size


def _repetition_hit_segments(trajectory: Trajectory, cfg: dict[str, object]) -> list[int]:
    """Indices of generation spans whose tokens trip ``repetition_first_hit``."""
    hits: list[int] = []
    response_ids = np.asarray(trajectory.response_ids, dtype=np.int64)
    for index, span in enumerate(trajectory.generation_spans):
        if not isinstance(span, (list, tuple)) or len(span) != 2:
            continue
        start, end = int(span[0]), int(span[1])
        if start < 0 or end <= start or end > response_ids.shape[0]:
            continue
        offset = repetition_first_hit(
            response_ids[start:end],
            ngram_size=int(cfg["ngram_size"]),
            window_size=int(cfg["window_size"]),
            min_content_length=int(cfg["min_content_length"]),
            min_repeat=int(cfg["min_repeat"]),
        )
        if offset >= 0:
            hits.append(index)
    return hits


def _repetition_mask(trajectory: Trajectory) -> tuple[torch.Tensor, str, int]:
    """Expand ``reward_info.repetition_hit_segments`` onto response-token offsets.

    Mirrors ``_tool_call_error_mask``: the framework decided the hits at scoring time
    (``_annotate_repetition``); here they are only projected through ``generation_spans``.
    Fail closed on any inconsistency so a bad span cannot mask unrelated tokens.
    """
    mask = torch.zeros(len(trajectory.response_ids), dtype=torch.float32)
    reward_info = trajectory.reward_info if isinstance(trajectory.reward_info, dict) else {}
    hits = reward_info.get("repetition_hit_segments")
    if hits is None:
        return mask, "not_detected", 0
    if not isinstance(hits, (list, tuple)):
        return mask, "invalid_hits", 0
    spans = trajectory.generation_spans
    marked = 0
    for index in hits:
        if not isinstance(index, int) or isinstance(index, bool) or index < 0 or index >= len(spans):
            return torch.zeros_like(mask), "invalid_hit_index", 0
        span = spans[index]
        if not isinstance(span, (list, tuple)) or len(span) != 2:
            return torch.zeros_like(mask), "invalid_span", 0
        try:
            start, end = int(span[0]), int(span[1])
        except (TypeError, ValueError, OverflowError):
            return torch.zeros_like(mask), "invalid_span", 0
        if start < 0 or end < start or end > len(mask):
            return torch.zeros_like(mask), "invalid_span", 0
        mask[start:end] = 1.0
        marked += 1
    return mask, "ok", marked


def _turn_index(trajectory: Trajectory) -> tuple[torch.Tensor, str]:
    """Per-response-token generation-turn index projected through ``generation_spans``.

    Tokens inside span ``i`` get value ``i``; tokens outside every span (observations,
    tool results) get ``-1``. Consumed by the trainer's experimental
    ``algorithm.deep_failure_mask`` channel. Fails closed (all ``-1``) on any span
    inconsistency so a bad span can never mark unrelated tokens.
    """
    n = len(trajectory.response_ids)
    index = torch.full((n,), -1, dtype=torch.long)
    spans = trajectory.generation_spans
    if not isinstance(spans, (list, tuple)):
        return index, "invalid_spans"
    prev_end = 0
    for i, span in enumerate(spans):
        if not isinstance(span, (list, tuple)) or len(span) != 2:
            return torch.full((n,), -1, dtype=torch.long), "invalid_span"
        try:
            start, end = int(span[0]), int(span[1])
        except (TypeError, ValueError, OverflowError):
            return torch.full((n,), -1, dtype=torch.long), "invalid_span"
        if start < prev_end or end < start or end > n:
            return torch.full((n,), -1, dtype=torch.long), "invalid_span"
        index[start:end] = i
        prev_end = end
    return index, "ok"


def _tool_call_error_mask(trajectory: Trajectory) -> tuple[torch.Tensor, str, int]:
    """Expand per-generation tool errors onto response-token offsets.

    The runner owns error classification while the gateway owns token spans.
    Refuse to guess when their lengths disagree: a zero mask plus an explicit
    alignment status is safer than penalizing the wrong assistant turn.
    """
    mask = torch.zeros(len(trajectory.response_ids), dtype=torch.float32)
    reward_info = trajectory.reward_info if isinstance(trajectory.reward_info, dict) else {}
    flags = reward_info.get("tool_call_error_flags")
    spans = trajectory.generation_spans
    if flags is None:
        return mask, "missing_flags", 0
    if not isinstance(flags, (list, tuple)):
        return mask, "invalid_flags", 0
    if len(flags) != len(spans):
        return mask, "length_mismatch", 0

    marked = 0
    for flag, span in zip(flags, spans):
        if not flag:
            continue
        if not isinstance(span, (list, tuple)) or len(span) != 2:
            return torch.zeros_like(mask), "invalid_span", 0
        try:
            start, end = int(span[0]), int(span[1])
        except (TypeError, ValueError, OverflowError):
            return torch.zeros_like(mask), "invalid_span", 0
        if start < 0 or end < start or end > len(mask):
            return torch.zeros_like(mask), "invalid_span", 0
        mask[start:end] = 1.0
        marked += 1
    return mask, "ok", marked


def _list_of_tq_fields_to_tensordict(fields: list[dict[str, object]]) -> TensorDict:
    # Optional per-sample fields (e.g. routed_experts) can be missing on degenerate
    # trajectories; drop any column not present on every sample so the stacker never
    # KeyErrors on a partially-present key (list_of_dict_to_tensordict keys off row 0).
    if fields:
        shared_keys = set(fields[0]).intersection(*(set(f) for f in fields[1:]))
        for f in fields:
            for key in list(f):
                if key not in shared_keys:
                    f.pop(key, None)
    td = tu.list_of_dict_to_tensordict(fields)
    for key in _TQ_NESTED_SEQUENCE_FIELDS:
        if key not in fields[0]:
            continue
        values = [field[key] for field in fields]
        if not all(isinstance(value, torch.Tensor) for value in values):
            continue
        if key == "routed_experts":
            ragged_idx = 1  # [seq, layers, topk]: ragged on the sequence dim
        elif key == "position_ids" and values[0].dim() == 2:
            ragged_idx = 2
        else:
            ragged_idx = None
        td[key] = tu.nested_tensor_from_tensor_list(values, ragged_idx=ragged_idx)
    return td


def _trajectory_to_reward_dataproto(trajectory, sample_fields):
    """Build a single-sample DataProto for RewardLoopWorker.compute_score.

    Field shape matches AgentLoopWorker._compute_score
    (verl/experimental/agent_loop/agent_loop.py:753-772). Only fields actually
    consumed by NaiveRewardManager.run_single / RewardLoopWorker dispatch are
    populated; ``__num_turns__`` rides in non_tensor_batch for parity.
    """
    from verl.protocol import DataProto

    prompt_ids = torch.tensor(trajectory.prompt_ids, dtype=torch.long).unsqueeze(0)
    response_ids = torch.tensor(trajectory.response_ids, dtype=torch.long).unsqueeze(0)
    input_ids = torch.cat([prompt_ids, response_ids], dim=1)
    attention_mask = torch.ones_like(input_ids, dtype=torch.long)

    batch = TensorDict(
        {
            "prompts": prompt_ids,
            "responses": response_ids,
            "input_ids": input_ids,
            "attention_mask": attention_mask,
        },
        batch_size=1,
    )

    non_tensor_batch: dict[str, object] = {}
    for key in (
        "raw_prompt",
        "data_source",
        "reward_model",
        "extra_info",
        "tools_kwargs",
        "agent_name",
    ):
        if key in sample_fields:
            non_tensor_batch[key] = np.array([sample_fields[key]], dtype=object)
    non_tensor_batch["__num_turns__"] = np.array([trajectory.num_turns])

    return DataProto(batch=batch, non_tensor_batch=non_tensor_batch)


class OpenAICompatibleAgentFramework(AgentFramework):
    """Reference AgentFramework implementation for OpenAI-compatible agent loops.

    Each sample in the batch is run as an independent session: the agent
    communicates with the Gateway via standard ``/v1/chat/completions``
    requests, and the Gateway collects token-level trajectories.  After
    finalization, scoring prefers the reward the runner posted to the session
    (``_score_from_reward_info``); otherwise, if a RewardLoopWorker is configured,
    ``_score_trajectories`` scores the final trajectory and broadcasts the score to all
    trajectories in the session (matching ``AgentLoopWorkerTQ._agent_loop_postprocess``).
    The framework then writes them to the TransferQueue schema consumed by sync training.
    """

    #: Grace period for a timed-out runner Ray task to observe a graceful
    #: ray.cancel (letting its sandbox context manager tear down) before the
    #: framework escalates to a force-kill.
    _RUNNER_CANCEL_GRACE_SECONDS = 30.0
    _RUNNER_ACTIVITY_POLL_SECONDS = 5.0

    def __init__(
        self,
        gateway_manager,  # GatewayManager: framework calls create_session/finalize_session/abort_session
        *,
        runner_registry: dict[str, _RunnerConfig],
        reward_loop_worker_handles=None,
        tokenizer=None,
        processor=None,
        rollout_config=None,
        log_dir: str | None = None,
        mask_unfinished_episode: bool = False,
        repetition_detect: dict[str, object] | None = None,
        ship_turn_index: bool = False,
    ):
        self.gateway_manager = gateway_manager
        self.runner_registry = runner_registry
        # Materialize inline runners at construction since they run in-process and may maintain state;
        # ray_task runners are materialized per-run since they run remotely.
        self._inline_runners = {
            runner_name: _materialize_runner(runner_config.runner_fqn, runner_config.runner_kwargs)
            for runner_name, runner_config in runner_registry.items()
            if runner_config.dispatch_mode == "inline_async"
        }
        self.reward_loop_worker_handles = list(reward_loop_worker_handles) if reward_loop_worker_handles else None
        self._tokenizer = tokenizer
        self._processor = processor
        self._rollout_config = rollout_config
        self._runner_semaphores: dict[str, asyncio.Semaphore] = {}
        self._semaphore_loop: asyncio.AbstractEventLoop | None = None
        self._log_dir = log_dir
        self._mask_unfinished_episode = mask_unfinished_episode
        self._repetition_detect = _normalize_repetition_detect_config(repetition_detect)
        self._ship_turn_index = ship_turn_index

    @classmethod
    def from_config(
        cls,
        *,
        config,
        gateway_manager,
        tokenizer=None,
        processor=None,
        reward_loop_worker_handles=None,
    ) -> OpenAICompatibleAgentFramework:
        # TODO(phase-b): switch this to actor_rollout_ref.rollout.agent_framework.*
        af_cfg = OmegaConf.select(config, "actor_rollout_ref.rollout.custom.agent_framework", default={}) or {}
        runner_registry: dict[str, _RunnerConfig] = {}
        agent_runners_cfg = af_cfg.get("agent_runners")
        if not agent_runners_cfg:
            raise ValueError("actor_rollout_ref.rollout.custom.agent_framework.agent_runners is required")

        for runner_name, runner_cfg in agent_runners_cfg.items():
            runner_registry[str(runner_name)] = _RunnerConfig.from_config(runner_name, runner_cfg)

        if "log_dir" in af_cfg:
            configured_log_dir = af_cfg.get("log_dir")
            log_dir = str(configured_log_dir) if configured_log_dir else None
        else:
            output_root = os.environ.get("VERL_HOME") or os.getcwd()
            log_dir = os.environ.get("UNI_AGENT_LOG_DIR") or str(Path(output_root) / "outputs" / "uni_agent_logs")

        if not bool(af_cfg.get("use_reward_loop_worker", True)):
            reward_loop_worker_handles = None

        mask_unfinished_episode = af_cfg.get("mask_unfinished_episode", False)
        if type(mask_unfinished_episode) is not bool:
            raise ValueError("actor_rollout_ref.rollout.custom.agent_framework.mask_unfinished_episode must be a bool")

        repetition_detect = _normalize_repetition_detect_config(af_cfg.get("repetition_detect"))

        ship_turn_index = af_cfg.get("ship_turn_index", False)
        if type(ship_turn_index) is not bool:
            raise ValueError("actor_rollout_ref.rollout.custom.agent_framework.ship_turn_index must be a bool")

        return cls(
            gateway_manager=gateway_manager,
            runner_registry=runner_registry,
            reward_loop_worker_handles=reward_loop_worker_handles,
            tokenizer=tokenizer,
            processor=processor,
            rollout_config=config.actor_rollout_ref.rollout,
            log_dir=log_dir,
            mask_unfinished_episode=mask_unfinished_episode,
            repetition_detect=repetition_detect,
            ship_turn_index=ship_turn_index,
        )

    def _build_session_sampling_params(
        self,
        *,
        partition_id: str,
        sample_fields: dict[str, object],
    ) -> dict[str, object]:
        """Build trusted per-session sampling defaults using VERL rollout semantics."""
        config = self._rollout_config
        sampling_params: dict[str, object] = {
            "temperature": config.temperature,
            "top_p": config.top_p,
            "top_k": config.top_k,
            "repetition_penalty": 1.0,
            "logprobs": config.calculate_log_probs,
        }
        tokenizer_eos = getattr(self._tokenizer, "eos_token_id", None)
        if isinstance(tokenizer_eos, (list, tuple, set)):
            stop_token_ids = sorted({int(token_id) for token_id in tokenizer_eos})
        elif tokenizer_eos is not None:
            stop_token_ids = [int(tokenizer_eos)]
        else:
            stop_token_ids = []
        if stop_token_ids:
            sampling_params["stop_token_ids"] = stop_token_ids
        if partition_id == "val":
            sampling_params.update(
                temperature=config.val_kwargs.temperature,
                top_p=config.val_kwargs.top_p,
                top_k=config.val_kwargs.top_k,
            )
        elif "__do_sample__" in sample_fields and not bool(sample_fields["__do_sample__"]):
            sampling_params.update(temperature=0, top_p=1.0, top_k=-1)
        return sampling_params

    async def generate_sequences(self, prompts: TensorDict) -> None:
        """Run rollout-manager generation and write outputs into TransferQueue."""
        if self._rollout_config is None:
            raise RuntimeError("OpenAICompatibleAgentFramework requires rollout_config for generate_sequences")

        is_validate = bool(tu.get(prompts, "validate", False))
        partition_id = "val" if is_validate else "train"
        global_steps = tu.get(prompts, "global_steps")
        if global_steps is None and not is_validate:
            raise ValueError("OpenAICompatibleAgentFramework requires prompts['global_steps'] for training")

        if partition_id == "val":
            val_kwargs = self._rollout_config.get("val_kwargs", {})
            num_sessions = int(val_kwargs.get("n"))
        else:
            num_sessions = int(self._rollout_config.get("n"))

        uids = tu.get(prompts, "uid")
        if uids is None:
            raise ValueError("OpenAICompatibleAgentFramework requires prompts['uid'] for TransferQueue output")

        stats = await self._run_batch_to_tq(
            prompts,
            global_steps=global_steps,
            partition_id=partition_id,
            num_sessions=num_sessions,
        )
        logger.info(
            "generate_sequences summary: num_input_prompts=%s num_success_sessions=%s "
            "num_failed_sessions=%s num_success_outputs=%s num_unfinished_episodes=%s "
            "num_failed_uids=%s failure_reasons=%s",
            stats["num_input_prompts"],
            stats["num_success_sessions"],
            stats["num_failed_sessions"],
            stats["num_success_outputs"],
            stats["num_unfinished_episodes"],
            stats["num_failed_uids"],
            stats["failure_reasons"][:3],
        )
        if stats["num_success_outputs"] == 0:
            raise RuntimeError(
                f"All rollouts failed at global_steps={global_steps}. "
                f"failures={stats['num_failed_uids']}/{stats['num_input_prompts']}"
            )
        return None

    async def _run_batch_to_tq(
        self,
        prompts: TensorDict,
        *,
        global_steps: int | None,
        partition_id: str,
        num_sessions: int = 1,
    ) -> dict:
        """Run all prompts in a batch and aggregate prompt/session stats."""
        assert len(prompts) > 0, "generate_sequences requires a non-empty batch"
        if num_sessions <= 0:
            raise ValueError(f"num_sessions must be positive, got {num_sessions}")

        # Batch layer: each sample/prompt owns its own group of rollout.n sessions.
        # Prompt tasks are isolated so one prompt failure does not drop the whole batch.
        tasks = []
        for sample_index in range(len(prompts)):
            tasks.append(
                self._run_prompt_sessions_to_tq(
                    sample_fields=self._extract_sample_fields(prompts=prompts, sample_index=sample_index),
                    sample_index=sample_index,
                    global_steps=global_steps,
                    partition_id=partition_id,
                    num_sessions=num_sessions,
                )
            )
        outcomes = await asyncio.gather(*tasks, return_exceptions=True)

        failure_reasons: list[str] = []
        stats = {
            "num_input_prompts": len(prompts),
            "num_success_sessions": 0,
            "num_failed_sessions": 0,
            "num_success_outputs": 0,
            "num_unfinished_episodes": 0,
            "num_failed_uids": 0,
            "failure_reasons": failure_reasons,
        }
        for outcome in outcomes:
            if isinstance(outcome, Exception):
                stats["num_failed_sessions"] += num_sessions
                stats["num_failed_uids"] += 1
                failure_reasons.append(_short_failure_reason(outcome))
                continue
            # Propagate control-flow exceptions such as CancelledError/SystemExit;
            # only ordinary Exceptions are treated as isolated rollout failures.
            if isinstance(outcome, BaseException):
                raise outcome
            stats["num_success_sessions"] += outcome["num_success_sessions"]
            stats["num_failed_sessions"] += outcome["num_failed_sessions"]
            stats["num_success_outputs"] += outcome["num_success_outputs"]
            stats["num_unfinished_episodes"] += outcome["num_unfinished_episodes"]
            stats["num_failed_uids"] += outcome["num_failed_uids"]
            failure_reasons.extend(outcome["failure_reasons"])
        return stats

    async def _run_prompt_sessions_to_tq(
        self,
        *,
        sample_fields: dict[str, object],
        sample_index: int,
        global_steps: int | None,
        partition_id: str,
        num_sessions: int,
    ) -> dict:
        uid = sample_fields.get("uid")
        if uid is None:
            raise ValueError("OpenAICompatibleAgentFramework requires prompts['uid'] for TransferQueue output")
        uid = str(uid)
        sampling_params = self._build_session_sampling_params(
            partition_id=partition_id,
            sample_fields=sample_fields,
        )

        # Prompt layer: rollout.n sessions race independently for the same uid.
        # Successful sessions are written to TQ; failed sessions only affect this uid's stats.
        tasks = [
            self._run_session_with_concurrency_limit(
                sample_fields=sample_fields,
                sample_index=sample_index,
                session_index=session_index,
                global_steps=global_steps,
                sampling_params=sampling_params,
            )
            for session_index in range(num_sessions)
        ]
        outcomes = await asyncio.gather(*tasks, return_exceptions=True)

        success_sessions = 0
        failed_sessions = 0
        success_outputs = 0
        unfinished_episodes = 0
        failure_reasons: list[str] = []
        for session_index, outcome in enumerate(outcomes):
            if isinstance(outcome, Exception):
                failed_sessions += 1
                failure_reasons.append(_short_failure_reason(outcome))
                continue
            # Propagate control-flow exceptions such as CancelledError/SystemExit;
            # only ordinary Exceptions are treated as isolated rollout failures.
            if isinstance(outcome, BaseException):
                raise outcome

            trajectories, session_sample_fields = outcome
            if not trajectories:
                failed_sessions += 1
                failure_reasons.append(f"empty trajectories for uid={uid} session_index={session_index}")
                continue

            try:
                await self._write_session_trajectories_to_tq(
                    uid=uid,
                    session_index=session_index,
                    trajectories=trajectories,
                    sample_fields=session_sample_fields,
                    global_steps=global_steps,
                    partition_id=partition_id,
                )
            except Exception as e:
                logger.exception(f"TQ write failed for uid={uid} session={session_index}: {e}")
                failed_sessions += 1
                failure_reasons.append(f"TQ write error: {e}")
            else:
                success_sessions += 1
                success_outputs += len(trajectories)
                # One session is one episode; its trajectories all carry the same
                # session-level completion flag, so this counts episodes, not tokens.
                if any(traj.reward_info.get("finished") is False for traj in trajectories):
                    unfinished_episodes += 1

        if success_sessions > 0:
            await tq.async_kv_put(key=uid, partition_id=partition_id, tag={"status": "finished"})
            failed_uids = 0
        else:
            await tq.async_kv_put(key=uid, partition_id=partition_id, tag={"status": "failure"})
            failed_uids = 1

        return {
            "num_success_sessions": success_sessions,
            "num_failed_sessions": failed_sessions,
            "num_success_outputs": success_outputs,
            "num_unfinished_episodes": unfinished_episodes,
            "num_failed_uids": failed_uids,
            "failure_reasons": failure_reasons,
        }

    async def _run_session_with_concurrency_limit(
        self,
        *,
        sample_fields: dict[str, object],
        sample_index: int,
        session_index: int,
        global_steps: int | None,
        sampling_params: dict[str, object],
    ) -> tuple[list[Trajectory], dict[str, object]]:
        # Lazy-init semaphores on first use and rebind if the running loop
        # changed: asyncio.Semaphore binds to the loop at construction, but
        # Ray actors may run sessions on a different loop than __init__.
        loop = asyncio.get_running_loop()
        if self._semaphore_loop is not loop:
            self._runner_semaphores = {}
            self._semaphore_loop = loop

        if len(self.runner_registry) == 1:
            runner_name, runner_config = next(iter(self.runner_registry.items()))
        else:
            agent_name = sample_fields.get("agent_name")
            if agent_name is None:
                raise ValueError("agent_name is required when multiple agent_runners are configured")
            if not isinstance(agent_name, str):
                raise ValueError(f"agent_name must be a string, got {type(agent_name).__name__}")
            try:
                runner_name = agent_name
                runner_config = self.runner_registry[runner_name]
            except KeyError as exc:
                raise ValueError(f"Unknown agent runner: {agent_name}") from exc

        runner_cap = runner_config.max_concurrent_sessions
        if runner_cap <= 0:
            return await self._run_session(
                sample_fields=sample_fields,
                sample_index=sample_index,
                session_index=session_index,
                global_steps=global_steps,
                runner_name=runner_name,
                runner_config=runner_config,
                sampling_params=sampling_params,
            )

        runner_semaphore = self._runner_semaphores.get(runner_name)
        if runner_semaphore is None:
            runner_semaphore = asyncio.Semaphore(runner_cap)
            self._runner_semaphores[runner_name] = runner_semaphore

        async with runner_semaphore:
            return await self._run_session(
                sample_fields=sample_fields,
                sample_index=sample_index,
                session_index=session_index,
                global_steps=global_steps,
                runner_name=runner_name,
                runner_config=runner_config,
                sampling_params=sampling_params,
            )

    async def _run_session(
        self,
        *,
        sample_fields: dict[str, object],
        sample_index: int,
        session_index: int,
        global_steps: int | None,
        runner_name: str,
        runner_config: _RunnerConfig,
        sampling_params: dict[str, object],
    ) -> tuple[list[Trajectory], dict[str, object]]:
        """Run one gateway session lifecycle and return finalized trajectories."""
        session_id = f"session-sample-{sample_index}-rollout-{session_index}-{uuid4().hex}"
        if self._log_dir:
            log_root = Path(self._log_dir)
            run_dir = (log_root if global_steps is None else log_root / f"step_{int(global_steps)}") / session_id
            framework_log = LogContext(session_id, str(run_dir / "framework.log"))
            task_log = LogContext(session_id, str(run_dir / "task.log"))
            parent_log = framework_log if runner_config.dispatch_mode == "ray_task" else task_log
        else:
            run_dir = None
            framework_log = None
            task_log = None
            parent_log = None

        raw_prompt = sample_fields["raw_prompt"]
        tools_kwargs = sample_fields.get("tools_kwargs")
        if isinstance(tools_kwargs, dict):
            tools_kwargs = dict(tools_kwargs)
            tools_kwargs["rollout_index"] = session_index
            if global_steps is not None:
                tools_kwargs["harness_round"] = int(global_steps)
        async with _log_scope(parent_log):
            session = None
            try:
                session = await self.gateway_manager.create_session(
                    session_id,
                    sampling_params=dict(sampling_params),
                )
                logger.info(
                    "session %s start: runner=%s sample_index=%s session_index=%s global_steps=%s stop_token_ids=%s",
                    session_id,
                    runner_name,
                    sample_index,
                    session_index,
                    global_steps,
                    sampling_params.get("stop_token_ids", []),
                )
                if runner_config.dispatch_mode == "ray_task":
                    # Ray workers run only the runner. Gateway token truth,
                    # finalization, reward scoring, and TQ writes stay in parent.
                    object_ref = _run_agent_runner_ray_task.remote(
                        runner_fqn=runner_config.runner_fqn,
                        runner_kwargs=runner_config.runner_kwargs,
                        raw_prompt=raw_prompt,
                        session=session,
                        sample_index=sample_index,
                        tools_kwargs=tools_kwargs,
                        log_context=task_log,
                    )
                    # Guard against runners that hang without raising (e.g. a
                    # remote sandbox that OOM-killed the kernel and never returns).
                    # Without this cap a single stuck session would hold its
                    # concurrency slot forever and stall the whole training batch.
                    # wait_for only bounds the parent's await; the Ray task must
                    # be cancelled explicitly or it (and its sandbox) would keep
                    # running. Graceful cancel first so the runner's asyncio.run
                    # unwinds and its sandbox context manager tears down cleanly;
                    # force-kill only if it ignores the cancel.
                    try:
                        session_timeout = _session_timeout_for_sample(runner_config, sample_fields)
                        await self._wait_for_runner_task(
                            object_ref,
                            session_id=session_id,
                            session_timeout_seconds=session_timeout,
                            request_idle_timeout_seconds=runner_config.agent_request_idle_timeout_seconds,
                        )
                    except (asyncio.TimeoutError, asyncio.CancelledError):
                        await self._cancel_runner_task(object_ref, session_id)
                        raise
                else:
                    runner = self._inline_runners[runner_name]
                    await runner(
                        raw_prompt=raw_prompt,
                        session=session,
                        sample_index=sample_index,
                        **({"tools_kwargs": tools_kwargs} if tools_kwargs is not None else {}),
                    )
                all_session_trajectories = await self.gateway_manager.finalize_session(session_id)
                session_trajectories = _select_session_trajectories(
                    session_id,
                    all_session_trajectories,
                    runner_config.trajectory_selection,
                )
            except Exception as exc:
                logger.exception("session %s failed (runner=%s); aborting session", session_id, runner_name)
                partial_trajectories = []
                if session is not None:
                    try:
                        partial_trajectories = await self.gateway_manager.abort_session(session_id)
                    except Exception:
                        logger.exception("session %s: abort snapshot failed", session_id)
                failure_info = _framework_failure_metadata(exc)
                failed = [replace(traj, reward_info=dict(failure_info)) for traj in partial_trajectories]
                if run_dir is not None:
                    if failed:
                        await asyncio.to_thread(self._dump_trajectories, run_dir, session_id, failed)
                    await asyncio.to_thread(
                        self._dump_session_manifest,
                        run_dir,
                        session_id,
                        sample_fields,
                        sample_index,
                        session_index,
                        runner_name,
                        failed,
                        failure_info,
                    )
                raise

            if not session_trajectories:
                if run_dir is not None:
                    await asyncio.to_thread(
                        self._dump_session_manifest,
                        run_dir,
                        session_id,
                        sample_fields,
                        sample_index,
                        session_index,
                        runner_name,
                        [],
                        {
                            "status": "failed",
                            "termination_kind": "no_trajectory",
                            "agent_status": "runner_empty",
                            "agent_completed": False,
                            "finished": False,
                            "gradable": False,
                            "error_type": "EmptyTrajectory",
                            "error_message": "session finalized without a materialized trajectory",
                        },
                    )
                return session_trajectories, sample_fields

            # Prefer the reward the runner posted to the session (report_reward=True);
            # otherwise defer to the RewardLoopWorker (if any), else rm_scores stays 0.
            annotations = self._score_from_reward_info(session_trajectories)
            reward_source = "reward_info" if annotations is not None else None
            if annotations is None and self.reward_loop_worker_handles:
                annotations = await self._score_trajectories(session_trajectories, sample_fields)
                reward_source = "reward_loop_worker"

            if annotations is None:
                logger.warning("session %s: no reward available; rm_scores=0 for this sample", session_id)
                result_trajectories = session_trajectories
            else:
                logger.info("session %s: scored via %s", session_id, reward_source)
                result_trajectories = [
                    replace(
                        traj,
                        reward_score=score,
                        extra_fields={**traj.extra_fields, "reward_extra_info": extra},
                    )
                    for traj, (score, extra) in zip(session_trajectories, annotations, strict=True)
                ]
            result_trajectories = self._annotate_repetition(session_id, result_trajectories)

            self._log_trajectory_summary(session_id, result_trajectories)
            if run_dir is not None:
                await asyncio.to_thread(self._dump_trajectories, run_dir, session_id, result_trajectories)
                if len(all_session_trajectories) != len(result_trajectories):
                    await asyncio.to_thread(
                        self._dump_semantic_trajectory,
                        run_dir,
                        session_id,
                        all_session_trajectories,
                    )
                await asyncio.to_thread(
                    self._dump_session_manifest,
                    run_dir,
                    session_id,
                    sample_fields,
                    sample_index,
                    session_index,
                    runner_name,
                    result_trajectories,
                    None,
                )
            return result_trajectories, sample_fields

    async def _wait_for_runner_task(
        self,
        object_ref,
        *,
        session_id: str,
        session_timeout_seconds: float | None,
        request_idle_timeout_seconds: float | None,
    ) -> None:
        """Wait for a Ray runner with separate wall and external-request idle budgets."""
        if session_timeout_seconds is None and request_idle_timeout_seconds is None:
            await object_ref
            return

        runner_wait_task = asyncio.ensure_future(asyncio.shield(object_ref))
        started_at = time.monotonic()
        try:
            while not runner_wait_task.done():
                remaining_wall = (
                    session_timeout_seconds - (time.monotonic() - started_at)
                    if session_timeout_seconds is not None
                    else None
                )
                if remaining_wall is not None and remaining_wall <= 0:
                    raise asyncio.TimeoutError(
                        f"session exceeded wall timeout of {session_timeout_seconds:.1f}s"
                    )

                wait_seconds = self._RUNNER_ACTIVITY_POLL_SECONDS
                if remaining_wall is not None:
                    wait_seconds = min(wait_seconds, remaining_wall)
                if request_idle_timeout_seconds is not None:
                    wait_seconds = min(wait_seconds, request_idle_timeout_seconds)
                done, _ = await asyncio.wait({runner_wait_task}, timeout=wait_seconds)
                if done:
                    break

                if request_idle_timeout_seconds is None:
                    continue
                try:
                    state = await self.gateway_manager.get_session_state(session_id)
                except Exception:
                    logger.warning("session %s: failed to inspect request-idle state", session_id, exc_info=True)
                    continue
                if runner_wait_task.done() or int(state.get("in_flight_requests", 0)) > 0:
                    continue
                if state.get("agent_finished"):
                    continue
                idle_seconds = state.get("awaiting_external_followup_seconds")
                if not state.get("awaiting_external_followup") or idle_seconds is None:
                    continue
                idle_seconds = float(idle_seconds)
                if idle_seconds >= request_idle_timeout_seconds:
                    raise AgentRequestTimeout(
                        idle_seconds=idle_seconds,
                        pending_tool_call_ids=[str(value) for value in state.get("pending_tool_call_ids", [])],
                    )

            await runner_wait_task
        finally:
            if not runner_wait_task.done():
                runner_wait_task.cancel()

    async def _cancel_runner_task(self, object_ref, session_id: str) -> None:
        """Cancel a dispatched runner Ray task after its session timed out.

        Graceful cancel (``force=False``) lets the worker's ``asyncio.run`` raise
        ``CancelledError`` and unwind, so runner-side cleanup (e.g. the task's
        sandbox context manager) runs. If the task is still pending after a short
        grace period, force-kill it: correctness of the batch (freeing the worker
        and its resources) beats the risk of skipping graceful teardown.
        """
        try:
            ray.cancel(object_ref)
        except Exception:
            logger.exception("session %s: ray.cancel failed for runner task", session_id)
            return
        try:
            await asyncio.wait_for(object_ref, timeout=self._RUNNER_CANCEL_GRACE_SECONDS)
        except asyncio.TimeoutError:
            logger.warning(
                "session %s: runner task ignored graceful cancel after %ss; force-killing",
                session_id,
                self._RUNNER_CANCEL_GRACE_SECONDS,
            )
            try:
                ray.cancel(object_ref, force=True)
            except Exception:
                logger.exception("session %s: force ray.cancel failed", session_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            # Task terminated while being cancelled (e.g. TaskCancelledError);
            # that is the expected outcome.
            pass

    def _annotate_repetition(self, session_id: str, trajectories: list[Trajectory]) -> list[Trajectory]:
        """Stamp repetition hits on every trajectory of a session.

        Runs after scoring so the verdict sits next to the reward it may override:
        ``reward_info.repetition_hit_segments`` lists the generation spans that trip the
        n-gram rule (projected to ``repetition_mask`` at TQ write time), and with
        ``zero_reward`` any hit forces ``reward_score`` to 0 the way the reference implementation's
        ``early_stop`` skips the verifier. Detection is per trajectory, but the reward
        override is session-wide: the runner posted one reward for the whole session.
        Disabled config leaves the trajectories untouched so old runs stay byte-identical.
        """
        cfg = self._repetition_detect
        if not cfg["enable"]:
            return trajectories
        hits_by_index = [_repetition_hit_segments(traj, cfg) for traj in trajectories]
        session_hit = any(hits_by_index)
        annotated: list[Trajectory] = []
        for traj, hits in zip(trajectories, hits_by_index, strict=True):
            reward_info = {
                **(traj.reward_info if isinstance(traj.reward_info, dict) else {}),
                "repetition_hit_segments": list(hits),
                "repetition_hit": bool(hits),
            }
            reward_score = traj.reward_score
            if session_hit and cfg["zero_reward"]:
                reward_info["repetition_original_reward"] = reward_score
                reward_info["repetition_zeroed_reward"] = True
                reward_score = 0.0
            annotated.append(replace(traj, reward_info=reward_info, reward_score=reward_score))
        if session_hit:
            logger.warning(
                "session %s: repetition detected in generation spans %s (ngram=%d window=%d min_repeat=%d); %s",
                session_id,
                hits_by_index,
                int(cfg["ngram_size"]),
                int(cfg["window_size"]),
                int(cfg["min_repeat"]),
                "reward forced to 0" if cfg["zero_reward"] else "reward kept",
            )
        return annotated

    def _log_trajectory_summary(self, session_id: str, trajectories: list[Trajectory]) -> None:
        """Log a per-session trajectory summary -- the info the task layer can't emit,
        since trajectories exist only after the session finalizes."""
        lines = [f"session {session_id}: {len(trajectories)} trajectory(ies)"]
        for i, traj in enumerate(trajectories):
            model_tokens = sum(traj.response_mask) if traj.response_mask else 0
            finished = traj.reward_info.get("finished")
            reason = (traj.extra_fields or {}).get("materialization_reason")
            lines.append(
                f"  [{i}] turns={traj.num_turns} prompt_tokens={len(traj.prompt_ids)} "
                f"response_tokens={len(traj.response_ids)} model_tokens={model_tokens} "
                f"finished={finished} "
                f"logprobs={'yes' if traj.response_logprobs else 'no'} "
                f"experts={'yes' if traj.routed_experts is not None else 'no'} "
                f"reward_score={traj.reward_score} reward_info={traj.reward_info or {}}"
                + (f" materialization_reason={reason}" if reason else "")
            )
        logger.info("\n".join(lines))

    def _dump_trajectories(self, run_dir: Path, session_id: str, trajectories: list[Trajectory]) -> None:
        """Persist finalized trajectories next to ``task.log``.

        Split by cost: a small human-readable summary (reward, turns, lengths) is written
        to ``trajectory.json``; the bulky per-token arrays (ids / mask / logprobs) go to a
        compressed ``trajectory.npz``. The arrays serialize at C speed and compress well
        (token ids repeat, the mask is runs of 0/1), so this is far smaller and faster than
        the old indented-JSON dump -- which matters most on a network / HDFS log_dir.

        Runs off the event loop (caller wraps this in ``asyncio.to_thread``) and is
        best-effort: an IO / serialization error is logged but never aborts the rollout.
        """
        try:
            run_dir.mkdir(parents=True, exist_ok=True)
            meta = {
                "session_id": session_id,
                "num_trajectories": len(trajectories),
                "trajectories": [self._trajectory_meta(traj) for traj in trajectories],
            }
            (run_dir / "trajectory.json").write_text(
                json.dumps(meta, ensure_ascii=False, separators=(",", ":"), default=_json_default),
                encoding="utf-8",
            )
            arrays: dict[str, np.ndarray] = {}
            for i, traj in enumerate(trajectories):
                arrays[f"traj{i}_prompt_ids"] = np.asarray(traj.prompt_ids, dtype=np.int32)
                arrays[f"traj{i}_response_ids"] = np.asarray(traj.response_ids, dtype=np.int32)
                arrays[f"traj{i}_response_mask"] = np.asarray(traj.response_mask, dtype=np.int8)
                arrays[f"traj{i}_generation_spans"] = np.asarray(
                    traj.generation_spans, dtype=np.int64
                ).reshape((len(traj.generation_spans), 2))
                if traj.response_logprobs is not None:
                    arrays[f"traj{i}_response_logprobs"] = np.asarray(traj.response_logprobs, dtype=np.float32)

            buf = io.BytesIO()
            np.savez_compressed(buf, **arrays)
            (run_dir / "trajectory.npz").write_bytes(buf.getvalue())
            self._dump_semantic_trajectory(run_dir, session_id, trajectories)
        except Exception:
            logger.exception("session %s: failed to write trajectory dump under %s", session_id, run_dir)

    def _dump_semantic_trajectory(
        self, run_dir: Path, session_id: str, trajectories: list[Trajectory]
    ) -> None:
        """Write a human-readable session transcript."""
        trajs: dict[str, dict[str, object]] = {}
        tool_counts: dict[str, int] = {}
        for index, trajectory in enumerate(trajectories):
            messages = getattr(trajectory, "messages", None) or []
            model_messages = getattr(trajectory, "model_messages", None) or messages
            tools = getattr(trajectory, "tools", None)
            model_tools = getattr(trajectory, "model_tools", None)
            key = "main" if index == 0 else f"chain_{index + 1}"
            trajs[key] = {
                "messages": messages,
                "model_messages": model_messages,
                "tools": tools,
                "model_tools": model_tools,
                "num_turns": trajectory.num_turns,
                "reward_info": trajectory.reward_info or {},
                "reward_score": trajectory.reward_score,
            }
            for message in messages:
                for call in message.get("tool_calls", []) if isinstance(message, dict) else []:
                    if not isinstance(call, dict):
                        continue
                    function = call.get("function") or {}
                    name = function.get("name") if isinstance(function, dict) else None
                    if name:
                        tool_counts[str(name)] = tool_counts.get(str(name), 0) + 1

        reward_info = dict(trajectories[-1].reward_info or {}) if trajectories else {}
        status = reward_info.get("agent_status") or reward_info.get("claude_code_status")
        if status is None and "finished" in reward_info:
            status = "Completed" if reward_info["finished"] else "Unfinished"
        payload = {
            "trajectory_format": "mimoagent",
            "info": {
                "session_id": session_id,
                "exit_status": status,
                "result": reward_info.get("result"),
                "reward": reward_info.get("reward"),
                "reward_info": reward_info,
                "tool_calls": tool_counts,
            },
            "trajs": trajs,
        }
        (run_dir / "traj.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default),
            encoding="utf-8",
        )

    def _dump_session_manifest(
        self,
        run_dir: Path,
        session_id: str,
        sample_fields: dict[str, object],
        sample_index: int,
        session_index: int,
        runner_name: str,
        trajectories: list[Trajectory],
        failure_info: dict[str, object] | None,
    ) -> None:
        """Persist one lifecycle record without feeding it back into rollout data."""
        try:
            run_dir.mkdir(parents=True, exist_ok=True)
            reward_info = dict(trajectories[-1].reward_info or {}) if trajectories else {}
            lifecycle = dict(failure_info or {})
            if not lifecycle:
                termination_kind = reward_info.get("termination_kind") or "completed"
                lifecycle = {
                    "status": "truncated" if termination_kind == "truncated" else "completed",
                    "termination_kind": termination_kind,
                    "agent_status": reward_info.get("agent_status"),
                    "agent_completed": reward_info.get("agent_completed"),
                    "finished": reward_info.get("finished"),
                    "gradable": True,
                    "error_type": None,
                    "error_message": None,
                }
            tools_kwargs = sample_fields.get("tools_kwargs")
            dataset_index = tools_kwargs.get("dataset_index") if isinstance(tools_kwargs, dict) else None
            selected_harness = reward_info.get("selected_harness") or reward_info.get("agent_type")
            payload = {
                "session_id": session_id,
                "sample_index": sample_index,
                "session_index": session_index,
                "dataset_index": dataset_index,
                "data_source": sample_fields.get("data_source"),
                "runner_name": runner_name,
                "selected_harness": selected_harness,
                **lifecycle,
                "num_trajectories": len(trajectories),
                "num_turns": max((trajectory.num_turns for trajectory in trajectories), default=0),
                "reward_score": trajectories[-1].reward_score if trajectories else None,
                "has_trajectory": bool(trajectories),
                "trajectory_path": str(run_dir / "traj.json") if trajectories else None,
            }
            target = run_dir / "session.json"
            temporary = run_dir / "session.json.tmp"
            temporary.write_text(
                json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=_json_default),
                encoding="utf-8",
            )
            temporary.replace(target)
        except Exception:
            logger.exception("session %s: failed to write lifecycle manifest under %s", session_id, run_dir)

    def _trajectory_meta(self, traj: Trajectory) -> dict[str, object]:
        """Small, human-readable per-trajectory summary; the token arrays live in the npz."""
        extra = traj.extra_fields or {}
        return {
            "num_turns": traj.num_turns,
            "finished": traj.reward_info.get("finished"),
            "reward_score": traj.reward_score,
            "reward_info": traj.reward_info or {},
            "reward_extra_info": extra.get("reward_extra_info"),
            "materialization_reason": extra.get("materialization_reason"),
            "prompt_len": len(traj.prompt_ids),
            "response_len": len(traj.response_ids),
            "model_token_count": sum(traj.response_mask) if traj.response_mask else 0,
            "generation_spans": [list(span) for span in traj.generation_spans],
            "has_routed_experts": traj.routed_experts is not None,
            "has_logprobs": traj.response_logprobs is not None,
        }

    def _score_from_reward_info(
        self, session_trajectories: list[Trajectory]
    ) -> list[tuple[float, dict[str, object]]] | None:
        """Score from the reward the runner posted to the session, if any.

        reward_score = the posted ``reward``; anything else posted (e.g. ``acc``)
        rides along as reward_extra_info. ``finished`` is dropped instead: the
        framework consumes it directly as a completion fact, so it is not a reward
        metric. See ``task_runner._post_reward_info`` for what's posted.
        """
        reward_info = dict(session_trajectories[-1].reward_info or {})
        reward = reward_info.pop("reward", None)
        reward_info.pop("finished", None)
        if reward is None:
            return None
        # Each trajectory needs its own dict: downstream code merges into it.
        return [(float(reward), dict(reward_info)) for _ in session_trajectories]

    async def _score_trajectories(
        self,
        session_trajectories: list[Trajectory],
        sample_fields: dict[str, object],
    ) -> list[tuple[float, dict[str, object]]]:
        """Score the session's final trajectory and broadcast (score, extra_info) to all.

        Mirrors AgentLoopWorkerTQ._agent_loop_postprocess
        (verl/trainer/main_ppo_sync.py:353-396): only the final trajectory (the
        session's last interaction segment) is dispatched to RewardLoopWorker;
        its score + reward_extra_info are then broadcast to every trajectory in
        the session. Subclasses can override this method to implement custom
        session-to-trajectory scoring policies.
        """
        assert self.reward_loop_worker_handles is not None
        assert session_trajectories, "expected non-empty session_trajectories"

        final_trajectory = session_trajectories[-1]
        scoring_sample_fields = dict(sample_fields)
        if final_trajectory.reward_info:
            scoring_sample_fields["extra_info"] = {
                **dict(sample_fields.get("extra_info") or {}),
                **final_trajectory.reward_info,
            }
        data = _trajectory_to_reward_dataproto(final_trajectory, scoring_sample_fields)
        worker = random.choice(self.reward_loop_worker_handles)
        result = await worker.compute_score.remote(data)

        if not isinstance(result, dict) or "reward_score" not in result:
            raise ValueError(
                f"RewardLoopWorker result missing 'reward_score' key or invalid for uid={sample_fields.get('uid')}"
            )
        score = float(result["reward_score"])
        extra = result.get("reward_extra_info") or {}
        # Each trajectory needs its own dict: downstream code merges into it.
        return [(score, dict(extra)) for _ in session_trajectories]

    def _extract_sample_fields(self, *, prompts: TensorDict, sample_index: int) -> dict[str, object]:
        sample_fields = {}
        for key, value in prompts.items():
            if isinstance(value, torch.Tensor):
                sample_fields[key] = value if value.ndim == 0 else value[sample_index]
            elif isinstance(value, NonTensorStack):
                sample_fields[key] = tu.get(prompts, key)[sample_index]
            else:
                assert isinstance(value, NonTensorData)
                sample_fields[key] = value.data
        return sample_fields

    async def _write_session_trajectories_to_tq(
        self,
        *,
        uid: str,
        session_index: int,
        trajectories: list[Trajectory],
        sample_fields: dict[str, object],
        global_steps: int | None,
        partition_id: str,
    ) -> None:
        keys = []
        fields = []
        tags = []
        for index, trajectory in enumerate(trajectories):
            field, tag = self._trajectory_to_tq_field_and_tag(
                trajectory=trajectory,
                sample_fields=sample_fields,
                session_index=session_index,
                global_steps=global_steps,
                uid=uid,
            )
            keys.append(f"{uid}_{session_index}_{index}")
            fields.append(field)
            tags.append(tag)

        await tq.async_kv_batch_put(
            keys=keys,
            fields=_list_of_tq_fields_to_tensordict(fields),
            tags=tags,
            partition_id=partition_id,
        )

    def _trajectory_to_tq_field_and_tag(
        self,
        *,
        trajectory: Trajectory,
        sample_fields: dict[str, object],
        session_index: int,
        global_steps: int | None,
        uid: str,
    ) -> tuple[dict[str, object], dict[str, object]]:
        prompts = torch.tensor(trajectory.prompt_ids, dtype=torch.long)
        responses = torch.tensor(trajectory.response_ids, dtype=torch.long)
        source_response_mask = torch.tensor(trajectory.response_mask, dtype=torch.long)
        tool_call_error_mask, tool_call_error_alignment, tool_call_error_segments = _tool_call_error_mask(
            trajectory
        )
        repetition_mask, repetition_alignment, repetition_segments = _repetition_mask(trajectory)
        finished = trajectory.reward_info.get("finished")
        if finished is not None and type(finished) is not bool:
            raise ValueError("reward_info.finished must be a bool or null")
        response_mask = (
            torch.zeros_like(source_response_mask)
            if self._mask_unfinished_episode and finished is False
            else source_response_mask
        )
        input_ids = torch.cat([prompts, responses], dim=0)
        attention_mask = torch.ones_like(input_ids, dtype=torch.long)
        multi_modal_inputs = compute_multi_modal_inputs(
            self._processor,
            input_ids.unsqueeze(0),
            trajectory.multi_modal_data,
        )
        if self._processor is None:
            position_ids = compute_position_id_with_mask(attention_mask.unsqueeze(0)).squeeze(0)
        else:
            position_ids = compute_position_ids(
                self._processor,
                input_ids.unsqueeze(0),
                attention_mask.unsqueeze(0),
                multi_modal_inputs,
            ).squeeze(0)

        field: dict[str, object] = {
            "prompts": prompts,
            "responses": responses,
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "position_ids": position_ids,
            "multi_modal_inputs": multi_modal_inputs,
        }
        if trajectory.response_logprobs is not None:
            field["rollout_log_probs"] = torch.tensor(trajectory.response_logprobs, dtype=torch.float32)
        if trajectory.routed_experts is not None:
            aligned_experts = _align_routed_experts(trajectory.routed_experts, input_ids.size(0))
            if aligned_experts is not None:
                field["routed_experts"] = aligned_experts
        rm_scores = torch.zeros_like(responses, dtype=torch.float32)
        if trajectory.reward_score is not None and responses.numel() > 0:
            rm_scores[-1] = float(trajectory.reward_score)
        field["rm_scores"] = rm_scores

        extra_fields = dict(trajectory.extra_fields)
        extra_fields.pop("materialization_reason", None)
        field.update(extra_fields)
        # Framework-owned masks must win over same-named Gateway extra fields.
        field["response_mask"] = response_mask
        field["loss_mask"] = response_mask
        field["tool_call_error_mask"] = tool_call_error_mask
        field["repetition_mask"] = repetition_mask
        if self._ship_turn_index:
            field["turn_index"], _turn_index_status = _turn_index(trajectory)
        field.pop("multi_modal_data", None)
        selected_harness = None
        if isinstance(trajectory.reward_info, dict):
            selected_harness = (
                trajectory.reward_info.get("selected_harness")
                or trajectory.reward_info.get("agent_type")
            )
        for key in (
            "uid",
            "raw_prompt",
            "data_source",
            "reward_model",
            "extra_info",
            "tools_kwargs",
            "agent_name",
        ):
            if key in sample_fields:
                field[key] = sample_fields[key]
        tag_data_source = bool(
            isinstance(trajectory.reward_info, dict)
            and trajectory.reward_info.get("tag_data_source_with_harness")
        )
        if selected_harness and tag_data_source:
            source = str(field.get("data_source") or "")
            if "@" not in source:
                field["data_source"] = f"{source}@{selected_harness}"
        field["session_id"] = session_index
        field["global_steps"] = global_steps
        field["num_turns"] = torch.tensor(int(trajectory.num_turns), dtype=torch.long)

        prompt_len = prompts.size(0)
        response_len = responses.size(0)

        # The gateway reports the weight versions a trajectory spanned. Fall back to
        # the dataloader step only when absent (backends that report no version):
        # the trainer casts these tags with dtype=int, so None must not reach it.
        min_global_steps = trajectory.extra_fields.get("min_global_steps", global_steps)
        max_global_steps = trajectory.extra_fields.get("max_global_steps", global_steps)
        tag = {
            "global_steps": global_steps,
            "min_global_steps": global_steps if min_global_steps is None else min_global_steps,
            "max_global_steps": global_steps if max_global_steps is None else max_global_steps,
            "status": "success",
            "prompt_len": prompt_len,
            "response_len": response_len,
            "seq_len": prompt_len + response_len,
            "uid": uid,
        }
        materialization_reason = trajectory.extra_fields.get("materialization_reason")
        if materialization_reason is not None:
            tag["materialization_reason"] = materialization_reason
        reward_info = trajectory.reward_info if isinstance(trajectory.reward_info, dict) else {}
        agent_type = reward_info.get("agent_type") or reward_info.get("selected_harness")
        tag["agent_type"] = str(agent_type) if agent_type else "unknown"
        tag["tool_call_error_count"] = int(reward_info.get("tool_call_error_count") or 0)
        for error_type in (
            "unknown_tool",
            "invalid_arguments",
            "incompatible_payload",
            "other_tool_error",
        ):
            tag[f"tool_call_error_{error_type}_count"] = int(
                reward_info.get(f"tool_call_error_{error_type}_count") or 0
            )
        tag["codex_transport_error_count"] = int(reward_info.get("codex_transport_error_count") or 0)
        tag["tool_call_error_alignment"] = tool_call_error_alignment
        tag["tool_call_error_segment_count"] = tool_call_error_segments
        tag["repetition_alignment"] = repetition_alignment
        tag["repetition_segment_count"] = repetition_segments
        tag["repetition_hit"] = int(bool(reward_info.get("repetition_hit")))
        tag["repetition_zeroed_reward"] = int(bool(reward_info.get("repetition_zeroed_reward")))
        return field, tag
