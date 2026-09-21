"""I21（第五组）：评测接线预检（纯函数）。

为什么要在启动期检查：共享引擎形态下 miles 直接 ``await rollout_manager.eval``，评测里的接线错误
会原样上抛并**停掉训练驱动**（只有快照形态才降级成 skip）。所以"第 k 步 eval 才发现配置不对"
等于训到一半崩——能在启动时发现的都放这里。

调用方与**实际运行时点**：``BringupService.__init__``（任何 RH2 资源型副作用之前）。注意 BringupService 是
在**首条样本**（训练或评测）到达 ``Rh2MilesGenerateFn`` 时才惰性启动的，所以真实作业里本预检到不了两类配置：
(a) miles 自己在更早处就崩溃的（独立评测作业默认的全局训练数据源 + 没有 ``--prompt-data``，RolloutManager
构造数据源时即 TypeError）；(b) 根本不派发任何评测的（``--skip-eval-before-train``）。这两类同样写在本函数里
（launcher 在分配 GPU 之前直接调用时才生效），在真实作业里则由启动命令核对清单约束——不要把它们说成
"预检已覆盖"。本函数只读 args 与个别环境变量，不触碰文件内容（题包 digest 绑定由 ``PreparedTaskFace.load`` 做）。

首版支持边界（明确写成边界，不是评测数学要求）：恰好一个评测数据集；共享引擎形态（含不训练的
独立作业）；快照 / 作业内专用 eval 引擎组形态拒绝——RH2 的模型代理在 bringup 时绑定训练 router，
专用引擎组上的评测请求仍会打到训练引擎（Brief §4.3 后置项）。
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

EVAL_REPORT_HOOK_PATH = "repoharness2.adapters.miles.eval_report.log_eval_rollout_data"


class EvalWiringError(RuntimeError):
    """评测接线配置错误（reason_code 机器可读；bringup 转成 StartupCheckError）。"""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"[{reason_code}] {message}")


@dataclass(frozen=True)
class EvalWiring:
    """预检结论。``enabled=False`` = 本次运行不走 RH2 formal 评测面（未开 eval，或 s1_compat 冻结路径）。"""

    enabled: bool
    eval_only: bool = False
    dataset_name: str | None = None
    dataset_path: str | None = None


def validate_eval_wiring(
    args: Any,
    *,
    execution_mode: str,
    eval_only: bool,
    eval_prepared_dir: str | None,
    eval_host_grading_path: str | None,
    eval_host_grading_sha256: str | None,
    environ: Mapping[str, str] | None = None,
) -> EvalWiring:
    environ = os.environ if environ is None else environ
    eval_interval = getattr(args, "eval_interval", None)
    requested = bool(eval_only) or eval_interval is not None
    if execution_mode == "s1_compat":
        if eval_only or eval_prepared_dir:
            raise EvalWiringError(
                "eval_requires_identity_mode",
                "RH2_EVAL_ONLY / RH2_EVAL_PREPARED_TASKS_DIR 已设但 RH2_EXECUTION_MODE=s1_compat："
                "评测题包按 attempt 绑定解析，依赖 s1_compat 不铸造的身份——改 fa_audit_only / fa_formal。",
            )
        return EvalWiring(enabled=False)  # 冻结路径：eval 走既有占位形状，不经本批接线
    if not requested:
        return EvalWiring(enabled=False)
    if eval_only and eval_interval is None:
        raise EvalWiringError(
            "eval_only_without_eval_interval",
            "RH2_EVAL_ONLY=1 但 miles 的 --eval-interval 未设——训练驱动根本不会派发评测。",
        )
    if eval_only:
        # 独立评测作业的驱动形态（miles `train_async.train` 的真实控制流，见 test_i21_eval_only_driver.py）：
        # - `--num-rollout 0`：训练循环零轮，只发生训练前那一次 eval（rollout 0）。只加 `--debug-rollout-only`
        #   不够——它不跳过 rollout 循环，eval 之后仍会派发训练 rollout（本作业没有训练题包，会被拒绝，而且要等
        #   整场评测跑完才暴露）；
        # - `--debug-rollout-only`：actor 在加载模型之前返回、权重发布是空操作，引擎服务的就是 `--hf-checkpoint`
        #   指向的固定 HF 导出。不加它时驱动会把训练侧加载的权重发布给引擎，记录里的模型来源就不再是被评对象。
        if getattr(args, "num_rollout", None) != 0:
            raise EvalWiringError(
                "eval_only_requires_zero_training_iterations",
                f"RH2_EVAL_ONLY=1 要求 --num-rollout 0（实际 {getattr(args, 'num_rollout', None)!r}）："
                "否则训练驱动在评测之后仍会派发训练 rollout。",
            )
        if not getattr(args, "debug_rollout_only", False):
            raise EvalWiringError(
                "eval_only_requires_rollout_only_driver",
                "RH2_EVAL_ONLY=1 要求 --debug-rollout-only：引擎直接服务 --hf-checkpoint 的固定导出，"
                "训练侧不加载模型、不向引擎发布权重。",
            )
        if getattr(args, "start_rollout_id", None) not in (None, 0):
            raise EvalWiringError(
                "eval_only_requires_fresh_start",
                f"RH2_EVAL_ONLY=1 要求不传 --start-rollout-id（实际 {getattr(args, 'start_rollout_id', None)!r}）："
                "训练前 eval 只在 start_rollout_id == 0 时派发。",
            )
        # Codex 第五组本机收尾审查 LR1：零轮只在 fully-async 分支才没有训练提交——非 fully-async 分支在进入
        # 循环之前就预取 `generate(start_rollout_id)`（Ray `.remote()` 一经调用即提交，不等 await）。
        if not getattr(args, "fully_async", False):
            raise EvalWiringError(
                "eval_only_requires_fully_async_driver",
                "RH2_EVAL_ONLY=1 要求 --fully-async：非 fully-async 的驱动在零轮循环之前就预取一次训练 rollout。",
            )
        # 下面两条在真实作业里到不了本预检（见模块说明），供 launcher 直接调用时使用。
        if getattr(args, "skip_eval_before_train", False):
            raise EvalWiringError(
                "eval_only_initial_eval_skipped",
                "RH2_EVAL_ONLY=1 不得带 --skip-eval-before-train：零轮作业只有训练前那一次 eval，跳过它就什么都不评。",
            )
        if getattr(args, "rollout_global_dataset", True) and not getattr(args, "prompt_data", None):
            raise EvalWiringError(
                "eval_only_global_dataset_without_prompt_data",
                "独立评测作业没有训练文件时必须带 --disable-rollout-global-dataset：miles 默认的全局训练数据源会在"
                "RolloutManager 构造时读取 --prompt-data（None → TypeError），作业在进入评测之前就崩。",
            )
        # LR2：rollout-only 不会有任何权重发布去覆盖引擎初始权重，所以引擎必须真的从 --hf-checkpoint 载入。
        # dummy 加载下 model_path 不变而权重是随机初始化——评出来的不是目标 checkpoint。
        if environ.get("MILES_SGLANG_DUMMY_LOAD") == "1" or getattr(args, "sglang_load_format", None) == "dummy":
            raise EvalWiringError(
                "eval_only_dummy_weight_load",
                "RH2_EVAL_ONLY=1 不得使用 dummy 权重加载（MILES_SGLANG_DUMMY_LOAD=1 / --sglang-load-format dummy）："
                "rollout-only 作业不发布权重，引擎里就是随机初始化，评测结果不属于 --hf-checkpoint。",
            )
    if not eval_prepared_dir or not eval_host_grading_path or not eval_host_grading_sha256:
        raise EvalWiringError(
            "eval_prepared_tasks_missing",
            "已开启评测（--eval-interval / RH2_EVAL_ONLY）但缺评测题包：需要 RH2_EVAL_PREPARED_TASKS_DIR、"
            "RH2_EVAL_HOST_GRADING_ARTIFACT_PATH、RH2_EVAL_HOST_GRADING_ARTIFACT_SHA256"
            "（同一份题包可以同时配给训练与评测，代码不强制两者互斥）。",
        )
    if getattr(args, "eval_uses_snapshots", False):
        raise EvalWiringError(
            "eval_snapshot_mode_unsupported",
            "快照 / 专用 eval 引擎组形态（--eval-num-gpus > 0 或 checkpoint eval fn）首版不支持："
            "RH2 模型代理启动时绑定训练 router，专用引擎组上的评测请求仍会打到训练引擎。",
        )
    datasets = list(getattr(args, "eval_datasets", None) or [])
    if len(datasets) != 1:
        raise EvalWiringError(
            "eval_dataset_count_unsupported",
            f"首版只支持恰好一个评测数据集（得到 {len(datasets)} 个）——评测题包的 prompts.jsonl 与它按内容 digest 绑定。",
        )
    dataset = datasets[0]
    path = getattr(dataset, "path", None)
    if not isinstance(path, str) or not path:
        raise EvalWiringError("eval_dataset_path_missing", f"评测数据集没有可用的 path：{path!r}。")
    if getattr(dataset, "custom_generate_function_path", None):
        raise EvalWiringError(
            "eval_dataset_generate_fn_override",
            "评测数据集配置了自己的 custom_generate_function_path——样本会绕过 Rh2MilesGenerateFn"
            "（身份、任务绑定、评分与结果载荷全部落空）。",
        )
    configured_hook = getattr(args, "custom_eval_rollout_log_function_path", None)
    if configured_hook != EVAL_REPORT_HOOK_PATH:
        raise EvalWiringError(
            "eval_report_hook_not_wired",
            f"--custom-eval-rollout-log-function-path 必须是 {EVAL_REPORT_HOOK_PATH!r}（实际 {configured_hook!r}）："
            "评不了分的评测样本交付 reward=None，miles 默认聚合会在样本指标里对 None 求和而崩，并把缺失计成 0 分。",
        )
    for key in ("reward_key", "eval_reward_key"):
        if getattr(args, key, None):
            raise EvalWiringError(
                "eval_reward_key_unsupported",
                f"args.{key}={getattr(args, key)!r}：RH2 评测交付标量 reward（不可得为 None），按键取值会崩。",
            )
    if getattr(args, "ci_metric_checker_key", None):
        raise EvalWiringError(
            "eval_metric_checker_unsupported",
            "配置了 ci_metric_checker_key：接管 eval 日志后 miles 的指标返回值为 None，MetricChecker 会在取值处崩。",
        )
    return EvalWiring(
        enabled=True, eval_only=bool(eval_only), dataset_name=str(getattr(dataset, "name", "")) or None, dataset_path=path,
    )


__all__ = ["EVAL_REPORT_HOOK_PATH", "EvalWiring", "EvalWiringError", "validate_eval_wiring"]
