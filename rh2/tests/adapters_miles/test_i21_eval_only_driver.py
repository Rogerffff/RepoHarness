"""I21（第五组）：不训练的独立评测作业——启动形态的本机证据（Codex I21 审查 R4 / 本机收尾审查 LR1、LR2）。

**一份**启动形态（`EVAL_ONLY_SHAPE`）同时喂给三个真实消费者，避免各测各的、互相绕过：

1. miles 的训练数据源构造（真实 `RolloutDataSourceWithBuffer`，RolloutManager 构造时最先执行）；
2. 训练驱动（fork `train_async.train` 原函数体；remote 替身按 Ray 语义**调用即提交**，不等 await——
   否则非 fully-async 分支那次"提交了但从未 await"的训练预取会被替身吞掉）；
3. rh2 预检（`validate_eval_wiring`）。

形态片段（不是完整启动命令；评测文件、采样、模型与 RH2 环境按既定方案另给）::

    --fully-async --debug-rollout-only --num-rollout 0 --disable-rollout-global-dataset
    --eval-interval N --hf-checkpoint <被评的 HF 导出>
    （不带 --skip-eval-before-train、--start-rollout-id；不用 dummy 权重加载）

本机到此为止：完整 miles CLI 参数校验、引擎是否真的从该路径载入权重、评测端到端，留真实八卡核验
（`batch5_launch_eval_20260919/gpu_verification_checklist_20260920.md` A1–A6）。integration_base：读集成树源码。
"""

from __future__ import annotations

import ast
import asyncio
import logging
import os
import sys
from collections import deque
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

pytestmark = pytest.mark.integration_base

HF_EXPORT = "/ckpt/hf_step_20"
# 独立评测作业的启动形态（miles args 视角）。三个消费者用同一份；反例只改其中一项。
EVAL_ONLY_SHAPE = dict(
    fully_async=True, debug_rollout_only=True, num_rollout=0, rollout_global_dataset=False, prompt_data=None,
    skip_eval_before_train=False, start_rollout_id=0, eval_interval=1, hf_checkpoint=HF_EXPORT, sglang_load_format="auto",
)


def _fork_root() -> Path:
    import miles

    return Path(miles.__file__).resolve().parents[1]


def _load(path: Path, names: tuple[str, ...], namespace: dict) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name in names]
    assert {n.name for n in nodes} == set(names), f"{path.name}: 缺 {set(names) - {n.name for n in nodes}}"
    unit = ast.Module(body=ast.parse("from __future__ import annotations").body + nodes, type_ignores=[])
    exec(compile(ast.fix_missing_locations(unit), str(path), "exec"), namespace)  # noqa: S102 —— 只执行仓库内指定定义


def _shape(**over) -> NS:
    return NS(**{**EVAL_ONLY_SHAPE, **over})


async def _drive(shape: NS) -> list[str]:
    """真实 `train_async.train` 函数体下，驱动向 RolloutManager 提交了什么（按提交顺序）。"""

    submitted: list[str] = []

    class _Remote:
        def __init__(self, op: str) -> None:
            self._op = op

        def remote(self, *args, **kwargs):  # Ray 语义：调用即提交
            submitted.append(self._op)
            future = asyncio.get_running_loop().create_future()
            future.set_result({"ok": True} if self._op == "dispose" else None)
            return future

    manager = NS(eval=_Remote("eval"), generate=_Remote("training_generate"), dispose=_Remote("dispose"))

    async def update_weights(**kwargs):  # rollout-only 下真实 actor.update_weights 直接返回
        submitted.append("update_weights_call")

    async def train_model(rollout_id, data):  # 只有保留训练轮数的反例会走到这里
        submitted.append("train_call")
        return [NS(weights_dirty=True)]

    async def models(*a):
        return NS(update_weights=update_weights, train=train_model), None

    noop = lambda *a, **k: None  # noqa: E731
    namespace = {
        "asyncio": asyncio, "logging": logging, "logger": logging.getLogger("i21-driver"), "os": os, "sys": sys, "deque": deque,
        "rh2_event_log": NS(assert_and_emit_identity=noop, emit=noop), "validate_async_off_policy_correction": noop,
        "configure_logger": noop, "MainProcessIdentity": lambda: None, "maybe_start_periodic_pyspy_dump": noop,
        "create_placement_groups": lambda args: {"rollout": None}, "object_store": NS(init_instance=noop), "init_tracking": noop,
        "create_rollout_manager": lambda *a: (manager, None), "create_training_models": models,
        "maybe_start_mini_ft_controller": noop, "remove_rollout_data_refs": noop, "raise_if_shutdown_failed": noop,
        "serialize_driver_cause": lambda exc: str(exc),
    }
    root = _fork_root()
    _load(root / "miles/utils/misc.py", ("should_run_periodic_action",), namespace)
    _load(root / "miles/ray/rollout/eval_dispatch.py", ("EvalDispatcher",), namespace)
    _load(root / "train_async.py", ("_any_weights_dirty", "train"), namespace)
    args = NS(**vars(shape), colocate=False, control_server_port=None, check_weight_update_equal=False, use_critic=False,
              save_trigger_sentinel=None, save_interval=None, update_weights_interval=1, debug_exit_after_rollout=None,
              eval_uses_snapshots=False)
    await namespace["train"](args)
    return submitted


def _build_training_data_source(world, shape: NS):
    """真实 `RolloutDataSourceWithBuffer`（RolloutManager 构造时第一件事）；只替换 tokenizer / processor 加载。"""

    world.install_sglang_stub()
    from miles.rollout import data_source as ds

    args = NS(rollout_global_dataset=shape.rollout_global_dataset, prompt_data=shape.prompt_data, hf_checkpoint=shape.hf_checkpoint,
              chat_template_path=None, dump_details=None, rollout_max_prompt_len=None, input_key="prompt", multimodal_keys=None,
              label_key="label", metadata_key="metadata", tool_key=None, apply_chat_template=False, apply_chat_template_kwargs={},
              rollout_seed=1, rollout_shuffle=False, buffer_filter_path=None)
    originals = (ds.load_tokenizer, ds.load_processor)
    ds.load_tokenizer, ds.load_processor = (lambda *a, **k: NS()), (lambda *a, **k: None)
    try:
        return ds.RolloutDataSourceWithBuffer(args)
    finally:
        ds.load_tokenizer, ds.load_processor = originals


def _precheck(shape: NS, *, environ=None):
    from repoharness2.adapters.slime.eval_wiring import EVAL_REPORT_HOOK_PATH, validate_eval_wiring

    args = NS(**vars(shape), eval_uses_snapshots=False, custom_eval_rollout_log_function_path=EVAL_REPORT_HOOK_PATH,
              reward_key=None, eval_reward_key=None, ci_metric_checker_key=None,
              eval_datasets=[NS(name="swe_dev", path="/prep/eval/prompts.jsonl", custom_generate_function_path=None)])
    return validate_eval_wiring(args, execution_mode="fa_formal", eval_only=True, eval_prepared_dir="/prep/eval",
                                eval_host_grading_path="/private/host.json", eval_host_grading_sha256="sha256:" + "a" * 64,
                                environ={} if environ is None else environ)


async def test_one_eval_only_shape_passes_data_source_construction_driver_and_precheck(world):
    shape = _shape()
    assert _build_training_data_source(world, shape).dataset is None  # 没有训练文件也能构造（全局训练数据源已关）
    assert await _drive(shape) == ["update_weights_call", "eval", "dispose"]  # 恰好一次 eval，零训练提交
    wiring = _precheck(shape)
    assert wiring.enabled and wiring.eval_only


async def test_without_fully_async_a_training_rollout_is_submitted_even_with_zero_iterations(world):
    """Codex LR1：非 fully-async 分支在进入零轮循环之前就预取 `generate(start_rollout_id)`。"""

    from repoharness2.adapters.slime.eval_wiring import EvalWiringError

    shape = _shape(fully_async=False)
    submitted = await _drive(shape)
    assert "training_generate" in submitted and submitted.index("training_generate") > submitted.index("eval")
    with pytest.raises(EvalWiringError, match="eval_only_requires_fully_async_driver"):
        _precheck(shape)


async def test_keeping_training_iterations_dispatches_training_after_the_eval(world):
    from repoharness2.adapters.slime.eval_wiring import EvalWiringError

    shape = _shape(num_rollout=1)  # 只加 --debug-rollout-only 而保留轮数
    submitted = await _drive(shape)
    assert submitted[:2] == ["update_weights_call", "eval"] and "training_generate" in submitted
    with pytest.raises(EvalWiringError, match="eval_only_requires_zero_training_iterations"):
        _precheck(shape)


def test_default_global_training_data_source_without_a_training_file_crashes_before_any_eval(world):
    """Codex LR1：独立评测作业只给评测文件时，miles 默认的全局训练数据源在 RolloutManager 构造时读 `prompt_data=None`。

    这发生在 rh2 预检之前（BringupService 在首条样本时才启动），真实作业里靠启动命令核对清单约束；同一条件也写在
    预检纯函数里，供 launcher 在分配 GPU 前直接调用。"""

    from repoharness2.adapters.slime.eval_wiring import EvalWiringError

    shape = _shape(rollout_global_dataset=True)
    with pytest.raises(TypeError):
        _build_training_data_source(world, shape)
    with pytest.raises(EvalWiringError, match="eval_only_global_dataset_without_prompt_data"):
        _precheck(shape)


@pytest.mark.parametrize(("over", "code"), [
    ({"skip_eval_before_train": True}, "eval_only_initial_eval_skipped"),
    ({"start_rollout_id": 3, "num_rollout": 3}, None),
])
async def test_zero_iteration_job_evaluates_nothing_when_the_initial_eval_is_disabled(world, over, code):
    """这类配置根本不派发评测——真实作业里没有任何样本会触发 rh2 预检，只能由启动命令核对清单排除；
    预检纯函数里的同名检查在 launcher 直接调用时才生效。"""

    from repoharness2.adapters.slime.eval_wiring import EvalWiringError

    shape = _shape(**over)
    assert "eval" not in await _drive(shape)
    with pytest.raises(EvalWiringError) as err:
        _precheck(shape)
    assert code is None or err.value.reason_code == code


def _effective_server_args(shape: NS, *, environ: dict, overrides: dict | None = None) -> dict:
    """真实 `_compute_server_args` 组装出的引擎有效参数（只替换 GPU 定位、LoRA 分支与 ServerArgs 字段集合）。"""

    path = _fork_root() / "miles/backends/sglang_utils/sglang_engine.py"
    func = next(n for n in ast.parse(path.read_text(encoding="utf-8")).body if isinstance(n, ast.FunctionDef) and n.name == "_compute_server_args")
    keys = {k.value for node in ast.walk(func) if isinstance(node, ast.Dict) for k in node.keys if isinstance(k, ast.Constant) and isinstance(k.value, str)}
    keys.update(("load_format", "dtype"))
    namespace = {
        "os": NS(environ=environ), "logger": logging.getLogger("i21-driver"), "ServerArgs": object,
        "dataclasses": NS(fields=lambda _: [NS(name=k) for k in sorted(keys)]), "_to_local_gpu_id": lambda n: n,
        "get_base_gpu_id": lambda *a: 0, "is_multi_lora_enabled": lambda _: False, "lora_rollout_enabled": lambda _: False,
        "_EXTERNAL_ENGINE_SKIP_CHECK_FIELDS": [],
    }
    _load(path, ("_compute_server_args",), namespace)
    args = NS(**vars(shape), rollout_num_gpus_per_engine=1, num_gpus_per_node=1, seed=1, offload_rollout=False, sglang_dp_size=1,
              sglang_pp_size=1, sglang_ep_size=1, use_rollout_routing_replay=False, use_rollout_indexer_replay=False, fp16=False)
    kwargs, _ = namespace["_compute_server_args"](args, 0, "127.0.0.1:9999", 9998, "127.0.0.1", 9997, sglang_overrides=overrides)
    return kwargs


def test_configured_checkpoint_is_not_proof_of_loaded_weights(world):
    """Codex LR2：路径相等不足以证明目标权重已载入——rollout-only 又不会有权重发布去覆盖引擎初始权重。"""

    from repoharness2.adapters.slime.eval_wiring import EvalWiringError

    shape = _shape()
    normal = _effective_server_args(shape, environ={})
    assert normal["model_path"] == HF_EXPORT and normal["load_format"] == "auto"  # 正控：有效参数就是被评导出、真实加载
    assert _precheck(shape, environ={}).eval_only

    # dummy 加载（环境变量或 CLI）：model_path 不变，权重却是随机初始化——预检把它排除在独立评测形态之外
    by_env = _effective_server_args(shape, environ={"MILES_SGLANG_DUMMY_LOAD": "1"})
    by_cli = _effective_server_args(_shape(sglang_load_format="dummy"), environ={})
    assert (by_env["model_path"], by_env["load_format"]) == (HF_EXPORT, "dummy")
    assert (by_cli["model_path"], by_cli["load_format"]) == (HF_EXPORT, "dummy")
    with pytest.raises(EvalWiringError, match="eval_only_dummy_weight_load"):
        _precheck(shape, environ={"MILES_SGLANG_DUMMY_LOAD": "1"})
    with pytest.raises(EvalWiringError, match="eval_only_dummy_weight_load"):
        _precheck(_shape(sglang_load_format="dummy"), environ={})

    # engine group 覆盖 model_path：有效路径 ≠ 配置来源，而 rh2 记录的 configured_hf_checkpoint 不变。
    # 覆盖来自 miles 的引擎拓扑配置（不在 args 上），rh2 预检看不到——首版独立评测不支持它，由 GPU 清单 A3
    # 逐引擎核对有效 model_path 与 load_format。
    overridden = _effective_server_args(shape, environ={}, overrides={"model_path": "/ckpt/other"})
    assert overridden["model_path"] == "/ckpt/other" and shape.hf_checkpoint == HF_EXPORT


def test_rollout_only_driver_never_publishes_trainer_weights_source_facts(world):
    """源码事实（CPU 上无法执行 Megatron actor）：rollout-only 下 actor 在加载模型之前返回、`update_weights` 是空操作
    ——所以引擎里只有它自己启动时载入的权重。真实作业用"全程没有 publish 事件"核验（GPU 清单 A3）。"""

    actor = (_fork_root() / "miles/backends/megatron_utils/actor.py").read_text(encoding="utf-8")
    assert actor.index("        if self.args.debug_rollout_only:\n            return 0") < actor.index("initialize_model_and_optimizer(")
    update = actor[actor.index("    def update_weights(self, info:"):]
    assert "if self.args.debug_train_only or self.args.debug_rollout_only:\n            return" in update[:400]
