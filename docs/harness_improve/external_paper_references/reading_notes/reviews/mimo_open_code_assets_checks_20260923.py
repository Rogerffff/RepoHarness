#!/usr/bin/env python3
"""Offline, narrow checks accompanying the MiMo open-code reading note.

No network, models, containers, Ray, Hydra, or upstream package imports.
`compute_prompt_loss_weights`, `_get`, `_check` are copied function bodies
from XiaomiMiMo/verl@e2b9fc03c6e01247f5d93c44201b068ea320b7de:
  verl/trainer/ppo/core_algos.py
  recipes/code/validate_resolved_config.py
The other checks are explicit examples of inspected selection/mask semantics,
not execution of the complete Uni-Agent framework or proof of training parity.

Copied code copyright 2024/2026 Bytedance Ltd. and/or its affiliates;
copyright 2022 The HuggingFace Team. All rights reserved.;
licensed under Apache-2.0: https://www.apache.org/licenses/LICENSE-2.0
Provided AS IS without warranties or conditions of any kind.
"""
from __future__ import annotations

import json
import os
import subprocess
from collections import defaultdict
from typing import Any

import torch


def compute_prompt_loss_weights(loss_mask: torch.Tensor, prompt_ids) -> torch.Tensor:
    """Return 1 / (active prompt count * prompt action tokens) for every row.

    Compute once over the complete optimizer batch before DP/microbatch splits.
    Zero-token prompts (including synthetic padding) do not enter the average.
    """
    if loss_mask.ndim != 2 or len(prompt_ids) != loss_mask.shape[0]:
        raise ValueError("Prompt IDs must match the rows of a two-dimensional loss mask")
    lengths = loss_mask.to(torch.bool).sum(dim=-1).tolist()
    totals: defaultdict[Any, int] = defaultdict(int)
    for prompt_id, length in zip(prompt_ids, lengths, strict=True):
        totals[prompt_id] += length
    prompt_count = sum(total > 0 for total in totals.values())
    if prompt_count == 0:
        raise ValueError("prompt-mean requires at least one prompt with action tokens")
    return torch.tensor(
        [
            1.0 / (prompt_count * totals[uid]) if length else 0.0
            for uid, length in zip(prompt_ids, lengths, strict=True)
        ],
        dtype=torch.float64,
        device=loss_mask.device,
    )


def _get(config: dict[str, Any], dotted_path: str) -> Any:
    value: Any = config
    for key in dotted_path.split("."):
        if not isinstance(value, dict) or key not in value:
            raise ValueError(f"resolved config is missing {dotted_path}")
        value = value[key]
    return value


def _check(config: dict[str, Any], dotted_path: str, expected: Any) -> None:
    actual = _get(config, dotted_path)
    if actual != expected:
        raise ValueError(f"{dotted_path} must resolve to {expected!r}, got {actual!r}")


def check_launcher_defaults() -> dict:
    # These two parameter expansions are the inspected launcher lines.
    # This does not source or execute run_train.sh.
    snippet = r'''printf '%s\n' "${FILTER_GROUPS_ENABLE:-True}" "$(printf '%s' "${FILTER_GROUPS_ENABLE:-False}" | tr '[:upper:]' '[:lower:]')"'''
    base_env = dict(os.environ)
    base_env.pop("FILTER_GROUPS_ENABLE", None)
    outcomes = {}
    for label, value in (("unset", None), ("explicit_true", "True"), ("explicit_false", "False")):
        env = dict(base_env)
        if value is not None:
            env["FILTER_GROUPS_ENABLE"] = value
        lines = subprocess.check_output(["bash", "-c", snippet], env=env, text=True).splitlines()
        actual, expected = lines[0].lower() == "true", lines[1] == "true"
        config = {"algorithm": {"filter_groups": {"enable": actual}}}
        try:
            _check(config, "algorithm.filter_groups.enable", expected)
            outcomes[label] = {"actual": actual, "expected": expected, "accepted": True}
        except ValueError as exc:
            outcomes[label] = {"actual": actual, "expected": expected, "accepted": False, "message": str(exc)}
    assert outcomes["unset"]["accepted"] is False
    assert outcomes["explicit_true"]["accepted"] is True
    assert outcomes["explicit_false"]["accepted"] is True
    return outcomes


def check_prompt_weights() -> dict:
    mask = torch.tensor([[1, 1, 1, 1], [1, 1, 0, 0], [1, 0, 0, 0], [0, 0, 0, 0]])
    ids = ["A", "A", "B", "PAD"]
    w = compute_prompt_loss_weights(mask, ids)
    mass = w * mask.sum(-1)
    assert torch.allclose(mass.sum(), torch.tensor(1.0, dtype=torch.float64))
    assert abs(float(mass[:2].sum()) - 0.5) < 1e-12
    assert abs(float(mass[2]) - 0.5) < 1e-12
    # Splitting a row preserves the normalized objective only when no token is
    # duplicated/dropped and each token's loss and group assignment stay fixed.
    split_mask = torch.tensor([[1, 1, 0, 0], [1, 1, 0, 0], [1, 1, 0, 0], [1, 0, 0, 0]])
    split_ids = ["A", "A", "A", "B"]
    split_w = compute_prompt_loss_weights(split_mask, split_ids)
    losses = torch.tensor([[1., 2., 3., 4.], [5., 6., 0., 0.], [7., 0., 0., 0.], [0., 0., 0., 0.]])
    split_losses = torch.tensor([[1., 2., 0., 0.], [3., 4., 0., 0.], [5., 6., 0., 0.], [7., 0., 0., 0.]])
    objective = (losses * mask * w[:, None]).sum()
    split_objective = (split_losses * split_mask * split_w[:, None]).sum()
    assert torch.allclose(objective, split_objective)
    try:
        compute_prompt_loss_weights(torch.zeros((2, 3)), ["A", "B"])
    except ValueError:
        all_zero_rejected = True
    else:
        all_zero_rejected = False
    assert all_zero_rejected
    return {"weights": w.tolist(), "prompt_mass_A": float(mass[:2].sum()), "prompt_mass_B": float(mass[2]), "objective": float(objective), "split_objective": float(split_objective), "all_zero_rejected": all_zero_rejected}


def check_selection_example() -> dict:
    # Mirrors the tuple used by _select_session_trajectories, not its full call.
    chains = [
        {"name": "earlier_chain", "mask": [1, 1, 1, 1, 0], "response_length": 5, "turns": 3},
        {"name": "later_final_chain", "mask": [1, 0, 0, 0, 0, 0], "response_length": 6, "turns": 5},
    ]
    idx, chosen = max(enumerate(chains), key=lambda item: (sum(item[1]["mask"]), item[1]["response_length"], item[1]["turns"], item[0]))
    assert idx == 0
    return {"chosen": chosen["name"], "is_latest": idx == len(chains) - 1}


def main() -> None:
    results = {"scope": "CPU function checks and explicit examples; not complete upstream tests or RL reproduction", "launcher": check_launcher_defaults(), "prompt_weights": check_prompt_weights(), "selection_example": check_selection_example()}
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
