"""I21 设计审查窄探针：执行原函数体，替换 Ray/设备/日志依赖，不修改生产代码。"""

from __future__ import annotations

import ast
import asyncio
import hashlib
import json
import logging
import os
from pathlib import Path
import sys
from collections import deque
from types import SimpleNamespace as NS
from typing import Any


ROOT = next(p for p in Path(__file__).resolve().parents if (p / "rh2/src/repoharness2").is_dir())
MILES = ROOT / "reference/miles-rh2-integration"
SOURCES: dict[str, str] = {}


def load_nodes(relative: str, names: tuple[str, ...], namespace: dict) -> None:
    path = MILES / relative
    source = path.read_bytes()
    SOURCES[relative] = hashlib.sha256(source).hexdigest()
    tree = ast.parse(source, filename=str(path))
    selected = [n for n in tree.body if getattr(n, "name", None) in names]
    assert len(selected) == len(names), (relative, names)
    future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
    body = ast.fix_missing_locations(ast.Module(body=[future, *selected], type_ignores=[]))
    exec(compile(body, str(path), "exec"), namespace)


class FloatWithItem(float):
    def item(self):
        return float(self)


def metric_probe(rewards, *, samples=True, suppress_default=False):
    logged = []
    env = {
        "logger": logging.getLogger("metric_probe"),
        "load_function": lambda _: lambda *a: suppress_default,
        "compute_rollout_step": lambda *a: 0,
        "tracking": NS(log=lambda *a, **k: logged.append(a[1])),
        "dict_add_prefix": lambda values, prefix: {prefix + k: v for k, v in values.items()},
        "compute_statistics": lambda _: {},
        "has_repetition": lambda _: False,
        "np": NS(mean=lambda values: FloatWithItem(sum(values) / len(values))),
        "Sample": NS(Status=NS(TRUNCATED="truncated")),
    }
    for name in ("_compute_zero_std_metrics", "_compute_spec_metrics", "_compute_prefix_cache_metrics", "_compute_reward_cat_metrics"):
        env[name] = lambda *a: {}
    load_nodes("miles/ray/rollout/metrics.py", ("log_eval_rollout_data", "_compute_metrics_from_samples", "_compute_training_sample_metrics"), env)
    # get_reward_value 与当前 Sample 的无 reward_key 分支一致；不改指标函数的 None 处理。
    rows = [NS(reward=r, metadata={}, index=i, group_index=None, rollout_id=None,
               effective_response_length=0, response="", status="aborted" if r is None else "completed",
               oldest_weight_version=None, weight_versions=[], get_reward_value=lambda args, r=r: r)
            for i, r in enumerate(rewards)]
    data = {"swe_dev": {"rewards": rewards, **({"samples": rows} if samples else {})}}
    args = NS(custom_eval_rollout_log_function_path="review.fixture", reward_key=None, log_passrate=False)
    try:
        result = env["log_eval_rollout_data"](0, args, data)
        return {"error": None, "result": result, "logged": logged}
    except Exception as exc:
        return {"error": type(exc).__name__, "message": str(exc), "logged": logged}


class Remote:
    def __init__(self, fn):
        self.fn = fn

    async def remote(self, *args, **kwargs):
        return self.fn(*args, **kwargs)


async def driver_probe(*, debug_rollout_only=False, num_rollout=1):
    events = []
    version = 0

    async def update_weights(**kwargs):
        nonlocal version
        if not debug_rollout_only:
            version += 1
        events.append({"op": "publish_call", "version": version})

    async def train_model(rollout_id, data):
        events.append({"op": "train_call", "rollout_id": rollout_id})
        return [NS(weights_dirty=True)]

    actor = NS(update_weights=update_weights, train=train_model)
    manager = NS(
        eval=Remote(lambda rid: events.append({"op": "eval", "rollout_id": rid, "version": version})),
        generate=Remote(lambda rid: events.append({"op": "training_generate", "rollout_id": rid})),
        dispose=Remote(lambda **kwargs: {"ok": True}),
    )

    async def models(*args):
        return actor, None

    noop = lambda *args, **kwargs: None
    env = {
        "asyncio": asyncio, "logging": logging, "logger": logging.getLogger("driver_probe"),
        "os": os, "sys": sys, "deque": deque,
        "rh2_event_log": NS(assert_and_emit_identity=noop, emit=noop),
        "validate_async_off_policy_correction": noop, "configure_logger": noop,
        "MainProcessIdentity": lambda: None, "maybe_start_periodic_pyspy_dump": noop,
        "create_placement_groups": lambda args: {"rollout": None},
        "object_store": NS(init_instance=noop), "init_tracking": noop,
        "create_rollout_manager": lambda *args: (manager, None),
        "create_training_models": models, "maybe_start_mini_ft_controller": noop,
        "remove_rollout_data_refs": noop, "raise_if_shutdown_failed": noop,
        "serialize_driver_cause": lambda exc: str(exc),
    }
    load_nodes("miles/utils/misc.py", ("should_run_periodic_action",), env)
    load_nodes("miles/ray/rollout/eval_dispatch.py", ("EvalDispatcher",), env)
    load_nodes("train_async.py", ("_any_weights_dirty", "train"), env)
    args = NS(colocate=False, control_server_port=None, check_weight_update_equal=False,
              eval_interval=1, start_rollout_id=0, skip_eval_before_train=False,
              hf_checkpoint="fixture://immutable-model", fully_async=True, num_rollout=num_rollout,
              use_critic=False, save_trigger_sentinel=None, save_interval=None,
              update_weights_interval=1, debug_exit_after_rollout=None,
              eval_uses_snapshots=False, debug_rollout_only=debug_rollout_only)
    await env["train"](args)
    return events


def main():
    output = {
        "scope": "原函数体；Ray/模型/日志等依赖使用替身；没有真实 GPU/完整 CLI 解析/模型加载",
        "metrics_none_with_samples": metric_probe([1.0, None]),
        "metrics_numeric_control": metric_probe([1.0, 0.0]),
        "metrics_none_without_samples": metric_probe([1.0, None], samples=False),
        "metrics_custom_suppresses_default": metric_probe([1.0, None], suppress_default=True),
        "driver_before_after_zero": asyncio.run(driver_probe()),
        "debug_rollout_only_one_iteration": asyncio.run(driver_probe(debug_rollout_only=True)),
        "zero_iteration_candidate": asyncio.run(driver_probe(debug_rollout_only=True, num_rollout=0)),
    }
    env = {"Any": Any}
    load_nodes("miles/utils/rh2_recovery.py", ("resolve_restore_rollout_id",), env)
    output["recovery_explicit_zero_loaded_ten"] = env["resolve_restore_rollout_id"](NS(start_rollout_id=0), 10)
    assert output["metrics_none_with_samples"]["error"] == "TypeError"
    assert output["metrics_numeric_control"]["result"]["eval/swe_dev"] == 0.5
    assert output["metrics_none_without_samples"]["result"]["eval/swe_dev"] == 0.5
    points = [e for e in output["driver_before_after_zero"] if e["op"] == "eval"]
    assert [(e["rollout_id"], e["version"]) for e in points] == [(0, 1), (0, 2)]
    assert any(e["op"] == "training_generate" for e in output["debug_rollout_only_one_iteration"])
    assert not any(e["op"] == "training_generate" for e in output["zero_iteration_candidate"])
    assert output["recovery_explicit_zero_loaded_ten"] == -1
    output["source_sha256"] = SOURCES
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
