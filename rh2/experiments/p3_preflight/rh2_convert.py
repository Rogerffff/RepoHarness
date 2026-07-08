"""P3-only slime conversion shim for RepoHarness governed samples.

This module is intentionally narrow: it is used by the eight GPU preflight
run to keep governance-rejected samples out of the training batch before slime
materializes tensors. The actual tensor conversion is still slime's stock
``RolloutRayActor._convert_samples_to_train_data`` implementation.
"""

from __future__ import annotations

import itertools
from typing import Any

import torch


def _flatten_samples(samples: list[Any] | list[list[Any]]) -> list[Any]:
    data = samples
    while data and isinstance(data[0], list):
        data = list(itertools.chain.from_iterable(data))
    return list(data)


def _normalize_routing_tape(args: Any, sample: Any) -> None:
    raw = getattr(sample, "rollout_routed_experts", None)
    if raw is None:
        return

    num_layers = getattr(args, "num_layers", None)
    router_topk = getattr(args, "moe_router_topk", None)
    if num_layers is None or router_topk is None:
        raise RuntimeError(
            "rh2_routing_shape_config_missing: "
            "use_rollout_routing_replay=True requires args.num_layers and args.moe_router_topk"
        )

    expected_rows = len(getattr(sample, "tokens", []) or []) - 1
    expected_shape = (expected_rows, int(num_layers), int(router_topk))
    tensor = torch.as_tensor(raw, dtype=torch.int32)
    if tensor.ndim == 1:
        expected_numel = expected_rows * int(num_layers) * int(router_topk)
        if int(tensor.numel()) != expected_numel:
            raise RuntimeError(
                "rh2_routing_tape_numel_mismatch_before_train_data: "
                f"sample={getattr(sample, 'index', None)} got={int(tensor.numel())} "
                f"expected={expected_numel} shape={expected_shape}"
            )
        tensor = tensor.reshape(expected_shape)
    elif tensor.ndim == 3:
        if tuple(int(v) for v in tensor.shape) != expected_shape:
            raise RuntimeError(
                "rh2_routing_tape_shape_mismatch_before_train_data: "
                f"sample={getattr(sample, 'index', None)} got={tuple(int(v) for v in tensor.shape)} "
                f"expected={expected_shape}"
            )
    else:
        raise RuntimeError(
            "rh2_routing_tape_rank_mismatch_before_train_data: "
            f"sample={getattr(sample, 'index', None)} rank={tensor.ndim} expected rank 1 or 3"
        )
    sample.rollout_routed_experts = tensor


def convert_samples_to_train_data(args: Any, samples: list[Any] | list[list[Any]]) -> dict[str, Any]:
    """Drop ``remove_sample=True`` entries, then delegate to slime's converter.

    RepoHarness uses ``remove_sample=True`` for trajectories that failed
    projection or eligibility. Those samples must not decide whether a batch
    carries MoE routing replay tensors, because slime's stock converter keys
    optional fields from the first sample. If every sample is removed, fail
    loudly at the adapter boundary instead of letting the trainer raise a
    misleading missing-field error.
    """

    flat = _flatten_samples(samples)
    kept = [sample for sample in flat if not bool(getattr(sample, "remove_sample", False))]
    if not kept:
        raise RuntimeError(
            "rh2_no_trainable_samples_after_governance_filter: "
            "all samples were marked remove_sample=True before train-data conversion"
        )

    if getattr(args, "use_rollout_routing_replay", False):
        missing = [
            getattr(sample, "index", pos)
            for pos, sample in enumerate(kept)
            if getattr(sample, "rollout_routed_experts", None) is None
        ]
        if missing:
            raise RuntimeError(
                "rh2_routing_tape_missing_after_governance_filter: "
                f"{len(missing)} kept samples lack rollout_routed_experts; "
                f"first_indices={missing[:8]}"
            )
        for sample in kept:
            _normalize_routing_tape(args, sample)

    from slime.ray.rollout import RolloutManager

    class _Proxy:
        custom_convert_samples_to_train_data_func = None
        custom_reward_post_process_func = None

        def __init__(self, args: Any) -> None:
            self.args = args

        def _post_process_rewards(self, samples: list[Any]) -> tuple[list[Any], list[Any]]:
            raw_rewards = [sample.get_reward_value(self.args) for sample in samples]
            normalize_rewards = (
                self.args.advantage_estimator in ["grpo", "gspo", "cispo", "reinforce_plus_plus_baseline"]
                and self.args.rewards_normalization
            )
            if not normalize_rewards:
                return raw_rewards, raw_rewards

            rewards = torch.tensor(raw_rewards, dtype=torch.float)
            expected_group = self.args.n_samples_per_prompt * self.args.rollout_batch_size
            if rewards.shape[-1] == expected_group:
                rewards = rewards.reshape(-1, self.args.n_samples_per_prompt)
            else:
                rewards = rewards.view(-1, rewards.shape[-1])
            rewards = rewards - rewards.mean(dim=-1, keepdim=True)

            if self.args.advantage_estimator in ["grpo", "gspo", "cispo"] and self.args.grpo_std_normalization:
                rewards = rewards / (rewards.std(dim=-1, keepdim=True) + 1e-6)

            return raw_rewards, rewards.flatten().tolist()

    default_convert = RolloutManager._convert_samples_to_train_data.__wrapped__
    return default_convert(_Proxy(args), kept)
