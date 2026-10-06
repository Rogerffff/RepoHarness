"""第五组本机收尾审查：真实控制流 / 数据源 / 有效引擎参数 / I22。

不运行 Ray、Docker、模型或 GPU。保留 AST 原函数体，替换外部副作用；反例不是完整 CLI 启动。
"""
from __future__ import annotations

import argparse
import ast
import asyncio
from collections import deque
import hashlib
import importlib.util
import json
import logging
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS
from unittest.mock import patch

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "rh2/src/repoharness2").is_dir())
FORK = ROOT / "reference/miles-rh2-integration"
SOURCES = {}


def record(path):
    source = path.read_bytes()
    SOURCES[str(path.relative_to(ROOT))] = hashlib.sha256(source).hexdigest()
    return source


def extract(path, names, namespace):
    tree = ast.parse(record(path))
    nodes = [node for node in tree.body if getattr(node, "name", None) in names]
    assert len(nodes) == len(names)
    unit = ast.Module(body=ast.parse("from __future__ import annotations").body + nodes, type_ignores=[])
    exec(compile(ast.fix_missing_locations(unit), str(path), "exec"), namespace)


def cli_shape():
    """只执行这几个 CLI 选项的真实注册语句；不冒充 Megatron/SGLang 全量参数验证。"""
    wanted = {"--fully-async", "--debug-rollout-only", "--num-rollout", "--skip-eval-before-train",
              "--disable-rollout-global-dataset", "--start-rollout-id"}
    parser = argparse.ArgumentParser()
    path = FORK / "miles/utils/arguments.py"
    found = set()
    for node in ast.walk(ast.parse(record(path))):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument":
            if node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value in wanted:
                unit = ast.Module(body=[ast.Expr(value=node)], type_ignores=[])
                exec(compile(ast.fix_missing_locations(unit), str(path), "exec"), {"parser": parser})
                found.add(node.args[0].value)
    assert found == wanted
    return parser.parse_args(["--debug-rollout-only", "--num-rollout", "0"])


def eval_args(**overrides):
    from repoharness2.adapters.slime.eval_wiring import EVAL_REPORT_HOOK_PATH

    args = NS(eval_interval=1, eval_uses_snapshots=False, custom_eval_rollout_log_function_path=EVAL_REPORT_HOOK_PATH,
              reward_key=None, eval_reward_key=None, ci_metric_checker_key=None, num_rollout=0, debug_rollout_only=True,
              start_rollout_id=0, skip_eval_before_train=False, fully_async=True, hf_checkpoint="/ckpt/hf_step_20",
              eval_datasets=[NS(name="review", path="/prep/eval/prompts.jsonl", custom_generate_function_path=None)])
    vars(args).update(overrides)
    return args


def precheck(args):
    from repoharness2.adapters.slime.eval_wiring import validate_eval_wiring
    return validate_eval_wiring(args, execution_mode="fa_formal", eval_only=True, eval_prepared_dir="/prep/eval",
                                eval_host_grading_path="/private/host.json", eval_host_grading_sha256="sha256:" + "a" * 64).enabled


async def drive(args):
    events = []

    class Remote:
        def __init__(self, op):
            self.op = op

        def remote(self, *args, **kw):
            # Ray .remote 的提交在调用时就发生，不等 await；用普通函数避免 async 替身吞掉 prefetch。
            events.append({"op": self.op, "args": args})
            future = asyncio.get_running_loop().create_future()
            future.set_result({"ok": True} if self.op == "dispose" else None)
            return future

    manager = NS(eval=Remote("eval"), generate=Remote("training_generate"), dispose=Remote("dispose"))

    async def update_weights(**kw):
        events.append({"op": "update_weights_call_noop"})

    async def models(*a):
        return NS(update_weights=update_weights), None

    noop = lambda *a, **kw: None
    env = dict(asyncio=asyncio, logging=logging, logger=logging.getLogger("i21-local-review"), os=os, sys=sys, deque=deque,
               rh2_event_log=NS(assert_and_emit_identity=noop, emit=noop), validate_async_off_policy_correction=noop,
               configure_logger=noop, MainProcessIdentity=lambda: None, maybe_start_periodic_pyspy_dump=noop,
               create_placement_groups=lambda _: {"rollout": None}, object_store=NS(init_instance=noop), init_tracking=noop,
               create_rollout_manager=lambda *a: (manager, None), create_training_models=models,
               maybe_start_mini_ft_controller=noop, remove_rollout_data_refs=noop, raise_if_shutdown_failed=noop,
               serialize_driver_cause=lambda exc: str(exc))
    extract(FORK / "miles/ray/rollout/eval_dispatch.py", ("EvalDispatcher",), env)
    extract(FORK / "miles/utils/misc.py", ("should_run_periodic_action",), env)
    extract(FORK / "train_async.py", ("_any_weights_dirty", "train"), env)
    vars(args).update(colocate=False, control_server_port=None, check_weight_update_equal=False, use_critic=False,
                      save_trigger_sentinel=None, save_interval=None, update_weights_interval=1, debug_exit_after_rollout=None)
    await env["train"](args)
    return events


def data_source_case(global_dataset):
    from miles.rollout import data_source as ds
    from miles.utils.data import Dataset

    args = NS(rollout_global_dataset=global_dataset, prompt_data=None, hf_checkpoint="fixture", chat_template_path=None,
              dump_details=None, rollout_max_prompt_len=None, input_key="prompt", multimodal_keys=None,
              label_key="label", metadata_key="metadata", tool_key=None, apply_chat_template=False,
              apply_chat_template_kwargs={}, rollout_seed=1, rollout_shuffle=False, buffer_filter_path=None)
    assert ds.Dataset is Dataset  # 替换 tokenizer/processor，不替换文件加载器与 Dataset。
    with patch.object(ds, "load_tokenizer", lambda *a, **kw: NS()), patch.object(ds, "load_processor", lambda *a, **kw: None):
        try:
            source = ds.RolloutDataSourceWithBuffer(args)
            return {"rollout_global_dataset": global_dataset, "error": None, "dataset_is_none": source.dataset is None}
        except Exception as exc:
            return {"rollout_global_dataset": global_dataset, "error": type(exc).__name__, "message": str(exc)}


def engine_config_case(*, dummy_env=False, dummy_cli=False, override_path=None):
    path = FORK / "miles/backends/sglang_utils/sglang_engine.py"
    tree = ast.parse(record(path))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_compute_server_args")
    # 这里只模拟 ServerArgs 可接受字段集合，避免导入设备依赖；关注的 model_path/load_format 都是既有真实字段。
    keys = {key.value for node in ast.walk(func) if isinstance(node, ast.Dict)
            for key in node.keys if isinstance(key, ast.Constant) and isinstance(key.value, str)}
    keys.update(("load_format", "dtype"))
    env = dict(os=os, logger=logging.getLogger("i21-local-review"), ServerArgs=object,
               dataclasses=NS(fields=lambda _: [NS(name=k) for k in sorted(keys)]),
               _to_local_gpu_id=lambda n: n, get_base_gpu_id=lambda *a: 0,
               is_multi_lora_enabled=lambda _: False, lora_rollout_enabled=lambda _: False,
               _EXTERNAL_ENGINE_SKIP_CHECK_FIELDS=[])
    extract(path, ("_compute_server_args",), env)
    args = eval_args(rollout_num_gpus_per_engine=1, num_gpus_per_node=1, seed=1, offload_rollout=False,
                     sglang_dp_size=1, sglang_pp_size=1, sglang_ep_size=1, use_rollout_routing_replay=False,
                     use_rollout_indexer_replay=False, fp16=False, sglang_load_format="dummy" if dummy_cli else "auto")
    with patch.dict(os.environ, {"MILES_SGLANG_DUMMY_LOAD": "1" if dummy_env else "0"}):
        ok = precheck(args)
        kwargs, _ = env["_compute_server_args"](args, 0, "127.0.0.1:9999", 9998, "127.0.0.1", 9997,
                                                sglang_overrides={"model_path": override_path} if override_path else None)
    return {"precheck": ok, "configured_checkpoint": args.hf_checkpoint, "engine_model_path": kwargs["model_path"],
            "effective_load_format": kwargs["load_format"], "dummy_env": dummy_env, "dummy_cli": dummy_cli}


def recovery_cases(directory):
    from miles.utils import rh2_recovery as recovery

    result = []
    for explicit, loaded in ((21, 10), (5, 2), (5, -1), (1, 3), (5, 4), (None, 4), (0, 9), (5, None)):
        args = NS(load=str(directory), start_rollout_id=explicit)
        reads = []

        def read(*a, **kw):
            reads.append(a[1])
            return {"published_weight_version": 7}

        with patch.object(recovery, "load_published_weight_version", read):
            try:
                initial = recovery.restore_updater_weight_version(args, loaded)
                row = {"explicit": explicit, "loaded": loaded, "initial_counter": initial, "error": None}
            except Exception as exc:
                row = {"explicit": explicit, "loaded": loaded, "error": type(exc).__name__}
        row["state_read_ids"] = reads
        mismatch = explicit is not None and explicit > 0 and loaded is not None and explicit - 1 != loaded
        assert row["error"] == ("RecoveryStartMismatch" if mismatch else None)
        if mismatch:
            assert reads == []  # 在读取可能属于别的权重的 sidecar 之前拒绝。
        result.append(row)
    return result


def main():
    sys.path[:0] = [str(ROOT / "rh2/tests/adapters_miles"), str(ROOT / "rh2/tests")]
    spec = importlib.util.spec_from_file_location("local_review_fixtures", ROOT / "rh2/tests/adapters_miles/conftest.py")
    fixtures = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixtures)
    fixture = fixtures._vendor_slime_world.__wrapped__()
    next(fixture)
    world = fixtures._World()
    world.install_sglang_stub()
    defaults = cli_shape()
    result = {"scope": "CPU; CLI 指定选项注册 + 真 data source/Dataset + 驱动/参数组装原函数体 + 恢复入口; 非完整 CLI/设备运行",
              "selected_cli_defaults": vars(defaults)}
    for name, over in (("fully_async_positive", {}), ("non_fully_async", {"fully_async": False}),
                       ("skip_initial_eval", {"skip_eval_before_train": True})):
        args = eval_args(**over)
        result[name] = {"precheck": precheck(args), "events": asyncio.run(drive(args))}
    assert "training_generate" not in [r["op"] for r in result["fully_async_positive"]["events"]]
    assert "training_generate" in [r["op"] for r in result["non_fully_async"]["events"]]
    assert "eval" not in [r["op"] for r in result["skip_initial_eval"]["events"]]
    result["default_data_source_without_training_file"] = data_source_case(defaults.rollout_global_dataset)
    result["disabled_data_source_without_training_file"] = data_source_case(False)
    assert result["default_data_source_without_training_file"]["error"] is not None
    assert result["disabled_data_source_without_training_file"]["error"] is None
    result["engine_configs"] = [engine_config_case(), engine_config_case(dummy_env=True), engine_config_case(dummy_cli=True),
                                engine_config_case(override_path="/ckpt/other")]
    with tempfile.TemporaryDirectory(prefix="i22-review-") as directory:
        result["recovery"] = recovery_cases(Path(directory))
    for relative in ("rh2/src/repoharness2/adapters/slime/eval_wiring.py", "rh2/src/repoharness2/adapters/slime/generate.py",
                     "rh2/src/repoharness2/adapters/slime/eval_result.py", "rh2/src/repoharness2/adapters/miles/eval_report.py",
                     "rh2/src/repoharness2/adapters/miles/run_report.py",
                     "reference/miles-rh2-integration/miles/utils/rh2_recovery.py",
                     "reference/miles-rh2-integration/miles/rollout/data_source.py",
                     "reference/miles-rh2-integration/miles/utils/data.py"):
        record(ROOT / relative)
    result["source_sha256"] = SOURCES
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
