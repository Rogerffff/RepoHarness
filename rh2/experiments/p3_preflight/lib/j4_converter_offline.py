"""Offline checker for the P3 J4 rollout-dump to slime train-data boundary.

This script is intentionally cheap: it reuses an existing ``rollout_*.pt`` dump,
reconstructs slime ``Sample`` objects, calls the exact RepoHarness P3 conversion
shim, and validates the tensors/fields that Megatron later consumes. It lets us
catch Python binding errors, governance filtering mistakes, and replay-tape
shape mismatches without paying for another full black-box rollout.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any


def _bootstrap_paths() -> None:
    here = Path(__file__).resolve()
    experiments_dir = here.parents[2]
    candidates = [experiments_dir]
    if os.environ.get("P3_SLIME"):
        candidates.append(Path(os.environ["P3_SLIME"]))
    if os.environ.get("P3_RH2"):
        candidates.append(Path(os.environ["P3_RH2"]) / "src")
    for candidate in candidates:
        if candidate.exists():
            sys.path.insert(0, str(candidate))


def _flatten(value: Any) -> list[Any]:
    if isinstance(value, list):
        out: list[Any] = []
        for item in value:
            out.extend(_flatten(item))
        return out
    return [value]


def _tensor_len(value: Any) -> int:
    try:
        import torch

        if torch.is_tensor(value):
            return int(value.detach().cpu().reshape(-1).numel())
    except Exception:  # noqa: BLE001 - best-effort helper for diagnostics
        pass
    return len(value)


def _seq_len(value: Any) -> int:
    try:
        import torch

        if torch.is_tensor(value):
            return int(value.shape[0])
    except Exception:  # noqa: BLE001 - best-effort helper for diagnostics
        pass
    return len(value)


def _tensor_shape(value: Any) -> tuple[int, ...]:
    try:
        import torch

        tensor = value if torch.is_tensor(value) else torch.as_tensor(value)
        return tuple(int(v) for v in tensor.shape)
    except Exception:  # noqa: BLE001 - fallback for plain nested lists
        if isinstance(value, (list, tuple)):
            if not value:
                return (0,)
            if isinstance(value[0], (list, tuple)):
                if value[0] and isinstance(value[0][0], (list, tuple)):
                    return (len(value), len(value[0]), len(value[0][0]))
                return (len(value), len(value[0]))
            return (len(value),)
        return ()


def _tensor_last_int(value: Any) -> int:
    try:
        import torch

        if torch.is_tensor(value):
            flat = value.detach().cpu().reshape(-1)
            return int(flat[-1].item())
    except Exception:  # noqa: BLE001 - best-effort helper for diagnostics
        pass
    return int(value[-1])


def _load_samples(path: Path) -> list[Any]:
    import torch
    from slime.utils.types import Sample

    blob = torch.load(path, weights_only=False)
    raw = blob.get("samples", blob) if isinstance(blob, dict) else blob
    samples = []
    for item in _flatten(raw):
        samples.append(Sample.from_dict(item) if isinstance(item, dict) else item)
    return samples


def _make_args(args: argparse.Namespace) -> SimpleNamespace:
    return SimpleNamespace(
        reward_key=None,
        advantage_estimator="grpo",
        rewards_normalization=args.rewards_normalization,
        grpo_std_normalization=False,
        n_samples_per_prompt=args.n_samples_per_prompt,
        rollout_batch_size=args.rollout_batch_size,
        rollout_top_p=args.rollout_top_p,
        use_rollout_routing_replay=args.expect_routing,
        num_layers=args.num_layers,
        moe_router_topk=args.moe_router_topk,
    )


def _validate_train_data(
    *,
    train_data: dict[str, Any],
    expected_trainable: int,
    expect_routing: bool,
    rollout_top_p: float,
    num_layers: int,
    moe_router_topk: int,
) -> tuple[bool, list[str], dict[str, Any]]:
    errors: list[str] = []
    summary: dict[str, Any] = {}
    required = [
        "tokens",
        "response_lengths",
        "loss_masks",
        "rewards",
        "raw_reward",
        "sample_indices",
        "rollout_ids",
        "rollout_mask_sums",
    ]
    for key in required:
        if key not in train_data:
            errors.append(f"missing train_data[{key!r}]")

    n = len(train_data.get("tokens", []))
    summary["num_train_data_samples"] = n
    if n != expected_trainable:
        errors.append(f"train_data sample count {n} != trainable sample count {expected_trainable}")

    response_lengths = train_data.get("response_lengths", [])
    loss_masks = train_data.get("loss_masks", [])
    if len(response_lengths) != n or len(loss_masks) != n:
        errors.append("response_lengths/loss_masks length does not match sample count")
    else:
        bad_loss = [
            i
            for i, (response_length, loss_mask) in enumerate(zip(response_lengths, loss_masks, strict=True))
            if len(loss_mask) != int(response_length)
        ]
        if bad_loss:
            errors.append(f"loss mask length mismatch at indices {bad_loss[:8]}")
        positive_masks = sum(1 for loss_mask in loss_masks if sum(loss_mask) > 0)
        summary["samples_with_positive_loss_mask"] = positive_masks
        if positive_masks == 0:
            errors.append("all train_data samples have zero loss mask")

    rollout_mask_sums = train_data.get("rollout_mask_sums", [])
    if len(rollout_mask_sums) == n:
        summary["rollout_mask_sums_min"] = min(rollout_mask_sums) if rollout_mask_sums else None
        summary["rollout_mask_sums_max"] = max(rollout_mask_sums) if rollout_mask_sums else None

    if rollout_top_p != 1.0:
        ids_list = train_data.get("rollout_top_p_token_ids")
        offsets_list = train_data.get("rollout_top_p_token_offsets")
        if ids_list is None or offsets_list is None:
            errors.append("top-p replay fields missing from train_data")
        elif len(ids_list) != n or len(offsets_list) != n:
            errors.append("top-p replay field length does not match sample count")
        else:
            bad_top_p = []
            for i, (ids, offsets, response_length) in enumerate(
                zip(ids_list, offsets_list, response_lengths, strict=True)
            ):
                if _tensor_len(offsets) != int(response_length) + 1:
                    bad_top_p.append((i, "offset_len", _tensor_len(offsets), int(response_length) + 1))
                    continue
                if _tensor_last_int(offsets) != _tensor_len(ids):
                    bad_top_p.append((i, "offset_end", _tensor_last_int(offsets), _tensor_len(ids)))
            if bad_top_p:
                errors.append(f"top-p replay shape mismatch: {bad_top_p[:4]}")
            summary["top_p_replay_present"] = True

    if expect_routing:
        routed = train_data.get("rollout_routed_experts")
        tokens = train_data.get("tokens", [])
        if routed is None:
            errors.append("routing replay field missing from train_data")
        elif len(routed) != n:
            errors.append("routing replay field length does not match sample count")
        else:
            summary["routing_replay_present"] = True
            bad_routing = []
            shapes = []
            for i, (experts, token_ids) in enumerate(zip(routed, tokens, strict=True)):
                shape = _tensor_shape(experts)
                shapes.append(shape)
                expected_shape = (_seq_len(token_ids) - 1, num_layers, moe_router_topk)
                if shape != expected_shape:
                    bad_routing.append((i, shape, expected_shape))
            summary["routing_first_shape"] = list(shapes[0]) if shapes else []
            summary["routing_first_numel"] = _tensor_len(routed[0]) if routed else 0
            if bad_routing:
                errors.append(f"routing replay shape mismatch: {bad_routing[:4]}")

    return not errors, errors, summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dump", action="append", default=[], help="Specific rollout_*.pt file")
    parser.add_argument("--dumps-dir", help="Directory containing rollout_*.pt files")
    parser.add_argument("--expect-routing", action="store_true")
    parser.add_argument("--rollout-top-p", type=float, default=0.95)
    parser.add_argument("--rollout-batch-size", type=int, default=8)
    parser.add_argument("--n-samples-per-prompt", type=int, default=4)
    parser.add_argument("--num-layers", type=int, default=48)
    parser.add_argument("--moe-router-topk", type=int, default=8)
    parser.add_argument("--rewards-normalization", action="store_true")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    _bootstrap_paths()
    from p3_preflight.rh2_convert import convert_samples_to_train_data

    dump_paths = [Path(p) for p in args.dump]
    if args.dumps_dir:
        dump_paths.extend(sorted(Path(args.dumps_dir).glob("rollout_*.pt")))
    dump_paths = sorted(set(dump_paths))
    if not dump_paths:
        raise SystemExit("No rollout dump files were provided.")

    all_samples: list[Any] = []
    per_dump: list[dict[str, Any]] = []
    for path in dump_paths:
        samples = _load_samples(path)
        trainable = [s for s in samples if not bool(getattr(s, "remove_sample", False))]
        per_dump.append(
            {
                "path": str(path),
                "num_samples": len(samples),
                "num_trainable_samples": len(trainable),
                "num_removed_samples": len(samples) - len(trainable),
            }
        )
        all_samples.extend(samples)

    expected_trainable = sum(
        1 for sample in all_samples if not bool(getattr(sample, "remove_sample", False))
    )
    try:
        train_data = convert_samples_to_train_data(_make_args(args), all_samples)
        ok, errors, train_summary = _validate_train_data(
            train_data=train_data,
            expected_trainable=expected_trainable,
            expect_routing=args.expect_routing,
            rollout_top_p=args.rollout_top_p,
            num_layers=args.num_layers,
            moe_router_topk=args.moe_router_topk,
        )
    except Exception as exc:  # noqa: BLE001 - this is the failure we want cheaply
        ok = False
        errors = [f"{type(exc).__name__}: {exc}"]
        train_summary = {}

    report = {
        "status": "PASS" if ok else "FAIL",
        "num_dumps": len(dump_paths),
        "num_input_samples": len(all_samples),
        "num_trainable_samples": expected_trainable,
        "per_dump": per_dump,
        "train_data": train_summary,
        "errors": errors,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[j4_converter_offline] {report['status']} -> {out}")
    for error in errors[:8]:
        print(f"[j4_converter_offline] error: {error}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
