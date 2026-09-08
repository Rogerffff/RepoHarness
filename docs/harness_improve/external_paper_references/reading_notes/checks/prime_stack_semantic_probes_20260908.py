#!/usr/bin/env python3
"""Reader-authored CPU reference probes, NOT the Prime upstream test suite.

These small models expose consequences of selected code semantics at the pinned
commits. They do not import prime_rl/verifiers/renderers and do not validate GPU,
RPC, tokenizers, environment safety, or training convergence. See the companion
Chinese reading note for source paths and the distinction between code facts and
reader inference. Requires Python >=3.10 and PyTorch; no network or GPU is used.

Run: python prime_stack_semantic_probes_20260908.py --output results.json
"""
from __future__ import annotations
import argparse
import json
import math
import platform
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import torch

PINS = {
    "prime-rl": "04a61d3b75c3c99f263b2c133e822f998909adf7",
    "verifiers": "828488fffe31aa3332b9d1bd4bd9ee320e375cf1",
    "renderers": "f91c3e7061ce50ea405cdf54fd419a45cb51a152",
    "prime-envs": "1f1e050ab0cd273bca39eed5c3e5315e6a8ae9d1",
}


def close(actual: float, expected: float, tol: float = 1e-10) -> None:
    assert math.isclose(actual, expected, rel_tol=tol, abs_tol=tol), (actual, expected)


def centered(rewards: list[float]) -> list[float]:
    assert rewards
    mean = sum(rewards) / len(rewards)
    return [r - mean for r in rewards]


@dataclass
class Sample:
    mask: list[bool]
    advantages: list[float] | None
    rl: list[float] | None = None
    ce: list[float] | None = None
    ref: list[float] | None = None


def prune_reference(s: Sample) -> bool:
    """Reference model of TrainSink's zero-advantage RL pruning."""
    if s.advantages is None:
        return True
    assert len(s.mask) == len(s.advantages)
    if s.rl is None:
        s.rl = [float(m) for m in s.mask]
    changed = False
    for i, a in enumerate(s.advantages):
        if a == 0 and s.rl[i] != 0:
            s.rl[i] = 0.0
            changed = True
    return not (changed and not any(s.rl) and not any(s.ce or []) and not any(s.ref or []))


def advantage_gate_reference(advantages: list[float], lo: float = 0, hi: float = 0) -> bool:
    return not advantages or not all(lo <= a <= hi for a in advantages)


def per_component_nll(logps: list[float], weights: list[float]) -> float:
    assert len(logps) == len(weights)
    return -sum(p * w for p, w in zip(logps, weights)) / max(sum(w != 0 for w in weights), 1)


def error_is_not_zero_reward() -> dict:
    survivors = centered([1.0, 0.0])
    injected = centered([1.0, 0.0, 0.0])
    assert survivors == [0.5, -0.5]
    close(injected[0], 2 / 3)
    assert survivors[0] != injected[0]
    return {"valid_trace_advantages": survivors, "with_invented_failure_reward": injected}


def all_pass_can_have_efficiency_credit() -> dict:
    lengths, rewards = [1, 2], [1.0, 1.0]
    mean = sum(rewards) / len(rewards)
    shaped = [r - mean * 0.25 * length / max(lengths) for r, length in zip(rewards, lengths)]
    adv = centered(shaped)
    assert adv == [0.0625, -0.0625]
    assert centered([0.0, 0.0]) == [0.0, 0.0]
    return {"raw_rewards": rewards, "shaped_rewards": shaped, "advantages": adv}


def maxrl_singleton_is_zero() -> dict:
    r = [1.0]
    mean = sum(r) / len(r)
    adv = [(x - mean) / mean for x in r]
    assert adv == [0.0]
    return {"reward": r, "max_rl_advantage": adv, "not_reinforce_reward": r}


def rae_is_order_sensitive() -> dict:
    def run(rs: list[float]) -> list[tuple[float, float]]:
        baseline, out = 0.0, []
        for r in rs:
            out.append((r, r - baseline))
            baseline = 0.5 * baseline + 0.5 * r
        return out
    left, right = run([0.0, 1.0]), run([1.0, 0.0])
    assert left == [(0.0, 0.0), (1.0, 1.0)]
    assert right == [(1.0, 1.0), (0.0, -0.5)]
    return {"order_01": left, "order_10": right, "illustrative_decay": 0.5}


def shared_prefix_loss_not_compute_dedup() -> dict:
    branches = [["prompt", "a", "tool", "b"], ["prompt", "a", "tool", "c"]]
    sampled = {"a", "b", "c"}
    seen_actions: set[str] = set()
    seen_ce: set[str] = set()
    rl_masks, ce_masks = [], []
    for branch in branches:
        rl_masks.append([node in sampled and node not in seen_actions for node in branch])
        seen_actions.update(node for node in branch if node in sampled)
        ce_masks.append([node == "tool" and node not in seen_ce for node in branch])
        seen_ce.update(node for node in branch if node == "tool")
    assert sum(map(sum, rl_masks)) == 3
    assert sum(map(sum, ce_masks)) == 1
    assert sum(map(len, branches)) == 8  # Both full physical paths are still forward inputs.
    return {"rl_masks": rl_masks, "ce_masks": ce_masks, "forward_positions": 8, "unique_nodes": 5}


def gate_can_remove_echo_before_pruning() -> dict:
    sample = Sample([True, False, True], [0.0, 0.0, 0.0], ce=[0.0, 0.1, 0.0])
    admitted_by_gate = advantage_gate_reference([0.0, 0.0])
    kept_by_builtin = prune_reference(sample)
    assert admitted_by_gate is False and kept_by_builtin is True
    assert advantage_gate_reference([]) is True
    return {"optional_adv_range_gate": admitted_by_gate, "builtin_pruning_without_gate": kept_by_builtin}


def prune_is_component_specific() -> dict:
    rl = Sample([False, True], [0.0, 0.0])
    ce = Sample([False, True], [0.0, 0.0], ce=[0.1, 0.0])
    ref = Sample([False, True], None, rl=[0.0, 0.0], ref=[0.0, 1.0])
    results = [prune_reference(x) for x in (rl, ce, ref)]
    assert results == [False, True, True]
    return {"pure_rl_echo_ref_kept": results}


def alpha_does_not_cancel() -> dict:
    actual = per_component_nll([-2, -4], [0.1, 0.1])
    wrong = -sum(p * w for p, w in zip([-2, -4], [0.1, 0.1])) / 0.2
    close(actual, 0.3)
    close(wrong, 3.0)
    return {"nonzero_count_denominator": actual, "weight_sum_denominator": wrong}


def same_component_mixture_still_changes_mean() -> dict:
    echo_only = per_component_nll([-2, -4], [0.1, 0.1])
    with_unrelated_rl = per_component_nll([-2, -4] + [-10] * 50, [0.1, 0.1] + [0.0] * 50)
    mixed_ce = per_component_nll([-2, -4, -1, -1], [0.1, 0.1, 1.0, 1.0])
    close(echo_only, with_unrelated_rl)
    close(mixed_ce, 0.65)
    return {"echo_ce": echo_only, "extra_rl_only": with_unrelated_rl, "with_sft_ce": mixed_ce}


def ipo_uses_absolute_probability_gap() -> dict:
    mu, pi, eps = 0.001, 0.02, 0.1
    assert abs(pi - mu) <= eps and pi / mu == 20
    mu2, pi2 = 0.5, 0.8
    keep = abs(pi2 - mu2) <= eps
    regularizer = 0.001 * math.log(pi2 / mu2) ** 2
    assert not keep and regularizer > 0
    return {"rare_token_ratio_kept": pi / mu, "outside_trust_region_kl_survives": regularizer}


def ref_signal_detach_changes_gradient() -> dict:
    t = torch.tensor(-1.0, dtype=torch.float64, requires_grad=True)
    i, ref = torch.tensor(-1.1, dtype=torch.float64), torch.tensor(-0.7, dtype=torch.float64)
    ratio = (t - i).exp()
    loss = -(ref - t).detach() * ratio + 0.001 * (t - i).square()
    loss.backward()
    expected = -0.3 * math.exp(0.1) + 0.0002
    close(float(t.grad), expected)
    bad_t = torch.tensor(-1.0, dtype=torch.float64, requires_grad=True)
    bad = -(ref - bad_t) * (bad_t - i).exp() + 0.001 * (bad_t - i).square()
    bad.backward()
    close(float(bad_t.grad) - float(t.grad), math.exp(0.1))
    return {"detached_signal_gradient": float(t.grad), "non_detached_gradient": float(bad_t.grad)}


def sampled_loggap_is_not_nonnegative_kl() -> dict:
    student, teacher = [0.9, 0.1], [0.5, 0.5]
    target_index = 0
    observed_gap = math.log(teacher[target_index]) - math.log(student[target_index])
    exact_reverse_kl = sum(p * math.log(p / q) for p, q in zip(student, teacher))
    assert observed_gap < 0 and exact_reverse_kl > 0
    return {"single_sample_ref_minus_student": observed_gap, "full_distribution_kl_student_teacher": exact_reverse_kl}


def support_mismatch_creates_false_gap() -> dict:
    full_p = 0.2
    truncated_p = full_p / 0.5
    close(math.log(full_p) - math.log(full_p), 0)
    gap = math.log(full_p) - math.log(truncated_p)
    close(gap, -math.log(2))
    return {"equal_raw_models_gap": 0.0, "full_ref_vs_truncated_student_gap": gap}


def dummy_requires_clearing_component_weights() -> dict:
    sampled_mask = [False, False]
    ce = [0.0, 0.1]
    assert not any(sampled_mask) and sum(w != 0 for w in ce) == 1
    clear = [0.0, 0.0]
    assert not any(clear)
    return {"zero_action_mask_ce_members": 1, "after_clearing_ce": 0}


def pool_weights_are_per_task() -> dict:
    easy_count, normal_count = 9, 1
    easy_weight, normal_weight = 0.2, 1.0
    mass = easy_count * easy_weight / (easy_count * easy_weight + normal_count * normal_weight)
    close(mass, 9 / 14)
    assert mass > 0.5
    return {"easy_pool_probability": mass, "not_fixed_pool_probability": 0.2 / 1.2}


def stale_boundary_uses_batch_input_version() -> dict:
    step, start, end, bound = 10, 7, 8, 2
    minimum = (step - 1) - bound
    total = max(0, step - 1 - start)
    in_flight = min(total, max(0, end - start))
    assert start >= minimum and total == 2 and in_flight == 1
    assert start < ((step + 1) - 1 - bound)
    return {"batch": step, "input_policy": step - 1, "age": total, "in_flight": in_flight, "queued": total - in_flight}


def retokenized_history_must_fork() -> dict:
    stored_nodes = [[10, 11], [20, 21]]
    prompt = [10, 11, 20, 99, 30]
    off, kept = 0, 0
    for node in stored_nodes:
        if prompt[off:off + len(node)] != node:
            break
        kept += 1
        off += len(node)
    assert kept == 1 and off == 2
    return {"same_message_identity_not_sufficient": True, "whole_prefix_nodes_reused": kept}


def post_admission_truncation_can_remove_all_loss() -> dict:
    token_ids, mask = [1, 2, 3, 4], [False, False, True, True]
    assert any(mask) and not any(mask[:2])
    t = torch.tensor([-0.2, -0.3], dtype=torch.float64, requires_grad=True)
    anchor = t.sum() * 0.0
    anchor.backward()
    assert t.grad is not None and torch.equal(t.grad, torch.zeros_like(t))
    return {"before_sampled_tokens": sum(mask), "after_sampled_tokens": sum(mask[:2]), "backward_zero_gradient": t.grad.tolist()}


def global_token_denominator_needs_rank_compensation() -> dict:
    # Simple DP arithmetic only; this does NOT simulate CP/FSDP communication.
    counts, local_gradient_sums = [1, 9], [1.0, 18.0]
    total = sum(counts)
    expected = sum(local_gradient_sums) / total
    local_means_then_rank_average = sum(g / n for g, n in zip(local_gradient_sums, counts)) / 2
    global_scaled_then_rank_average = sum(g / total for g in local_gradient_sums) / 2
    compensated = global_scaled_then_rank_average * 2
    close(expected, 1.9)
    close(local_means_then_rank_average, 1.5)
    close(compensated, expected)
    return {"token_mean": expected, "wrong_rank_mean": local_means_then_rank_average,
            "global_denominator_plus_rank_compensation": compensated}


PROBES: list[Callable[[], dict[str, Any]]] = [
    error_is_not_zero_reward, all_pass_can_have_efficiency_credit, maxrl_singleton_is_zero,
    rae_is_order_sensitive, shared_prefix_loss_not_compute_dedup, gate_can_remove_echo_before_pruning,
    prune_is_component_specific, alpha_does_not_cancel, same_component_mixture_still_changes_mean,
    ipo_uses_absolute_probability_gap, ref_signal_detach_changes_gradient,
    sampled_loggap_is_not_nonnegative_kl, support_mismatch_creates_false_gap,
    dummy_requires_clearing_component_weights, pool_weights_are_per_task,
    stale_boundary_uses_batch_input_version, retokenized_history_must_fork,
    post_admission_truncation_can_remove_all_loss, global_token_denominator_needs_rank_compensation,
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    records: list[dict[str, Any]] = []
    for probe in PROBES:
        try:
            details = probe()
            records.append({"name": probe.__name__, "status": "passed", "details": details})
        except Exception as exc:
            records.append({"name": probe.__name__, "status": "failed", "error": f"{type(exc).__name__}: {exc}"})
    report = {
        "scope": "reader-authored semantic reference probes; NOT upstream tests or end-to-end validation",
        "source_pins": PINS,
        "python": platform.python_version(), "torch": torch.__version__, "device": "cpu",
        "passed": sum(r["status"] == "passed" for r in records), "total": len(records), "probes": records,
    }
    text = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text)
    if report["passed"] != report["total"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
