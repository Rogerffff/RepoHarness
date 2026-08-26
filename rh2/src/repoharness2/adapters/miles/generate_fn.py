"""miles 新签名 generate 函数：Rh2MilesGenerateFn（miles 迁移 C0）。

miles 加载方式（reference/miles/miles/rollout/inference_rollout/
compatibility.py `load_generate_function`）：

    --custom-generate-function-path repoharness2.adapters.miles.generate_fn.Rh2MilesGenerateFn

路径指向类时 miles 直接 `fn()` 实例化并以新签名调用
`await fn(GenerateFnInput(...))`——**不经过** LegacyGenerateFnAdapter。
本类内部仍复用 rh2 现有的 legacy 入口 `rh2_custom_generate`（slime 冻结
回退面，签名 `(args, sample, sampling_params, evaluation=...)`），再把输出
经 canonicalize_group 转成 miles Sample（B1 崩溃链的正式修复位）。

import 面说明（sglang 卡点，spike 已知）：`miles.rollout.base_types` 模块级
import `miles.rollout.data_source`，后者经 chat_template_utils 拉 sglang——
CPU 环境（本机测试）没有 sglang 时该链会在 import 时炸。因此本模块**模块级
不 import 任何 miles.rollout.***，`GenerateFnOutput` 延迟到 `__call__` 内
import（miles 真实运行环境里 miles 自身早已加载，函数内 import 零成本；
CPU 测试环境按需先装 sglang 最小 stub）。`repoharness2.adapters.slime.generate`
模块级零 slime import（P0-1 已核实），放在模块级安全。
"""

from __future__ import annotations

from typing import Any

from repoharness2.adapters.miles.canonicalize import canonicalize_group
from repoharness2.adapters.slime.generate import rh2_custom_generate


class Rh2MilesGenerateFn:
    """miles 新签名类形态 generate 函数：legacy rh2 链 + canonicalize 边界。

    职责刻意最小（C0）：不做治理、不碰 buffer——只保证"凡返回 miles 的样本
    必为 miles Sample"这一条类型边界不变量。治理件（ledger/governed buffer）
    在 C3/C7 单独接线。
    """

    async def __call__(self, input: Any) -> Any:  # input: miles GenerateFnInput
        # 延迟 import：见模块 docstring 的 sglang 卡点说明。
        from miles.rollout.base_types import GenerateFnOutput

        # B1 最小 bootstrap（R6-ext）：miles 只配置
        # --custom-generate-function-path 时没有任何生产代码构造
        # args.rh2_orchestrator——首个样本会在 canonicalize 前因
        # orchestrator_not_configured 失败。这里**复用既有** bringup 单例
        # （ensure_fa_started：BringupService.get 幂等 + 挂 rh2_orchestrator/
        # rh2_sampling_params），不新建任何 backend 抽象。每个 rollout actor
        # 进程首次调用构造一次；后续调用（包括并发首调用，单例内有锁）拿同
        # 一实例。启动失败按 BringupService 的 sticky FAILED 语义传播（同进
        # 程不静默重试第二代）。
        #
        # 关闭 hook 说明（有意留给进程退出路径）：BringupService 持有的
        # adapter HTTP 线程 / 评分队列没有 per-rollout 的 close 面，miles
        # stock FullyAsyncRolloutFn 也没有 dispose 回调（spike R5-ext B5 已
        # 登记）；CPU/首轮 GPU spike 按 run-fatal + 进程退出回收处理，正式
        # 关停语义归硬件段的 close/dispose seam。
        if getattr(input.args, "rh2_orchestrator", None) is None:
            from repoharness2.adapters.slime.bringup import ensure_fa_started

            await ensure_fa_started(input.args)

        # rh2 legacy 入口自己会从 args.rh2_orchestrator 取编排本体并 fail-closed
        # 校验；GenerateFnInput.args 即 state.args（miles base_types 的 property）。
        raw = await rh2_custom_generate(
            input.args,
            input.sample,
            input.sampling_params,
            evaluation=input.evaluation,
        )
        # C1′-b mask 闸透传：miles 配置 rollout_top_p<1.0 即开 sampling-support
        # replay（上游严格开关），此时 slime->miles 构造分支必须带装配 mask，
        # 缺失由 canonicalize fail-closed 拒绝。args 无该属性（老测试面/非
        # miles args）时传 None，闸不生效。
        samples = canonicalize_group(
            raw,
            miles_input_sample=input.sample,
            rollout_top_p=getattr(input.args, "rollout_top_p", None),
        )
        return GenerateFnOutput(samples=samples)
