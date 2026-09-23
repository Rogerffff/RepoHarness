# 批 A 独立审查：错误来源与传播

日期：2026-09-09。角色：Production Tracer。基线：`297f1f59` 上未提交的 `bringup.py`、`generate.py`、`outcome_producer.py` 差异。先读差异，再核对当前 Brief §3A/§6 和 `infra.md:236–252`。范围仅限批 A 错误分类与 miles 消费，不重审预算 B/C/D；receipt 清理由主审独立核对。

**结论：有一个 P1 窄修项。新编排分流本身有效，CLI 版本与两条 capture 矛盾已接入 fatal；但 `ClaudeCodeDriver.run` 的新 RuntimeError 包装范围过宽，仍能把未知内部异常改名成已归因的引导故障并返回 ABORTED。六项明确保留现状的分支不计作本批违约。**

## R1：驱动把整个 harness 生命周期里的 RuntimeError 都当成局部引导故障

**当前行为与位置。** `rh2/src/repoharness2/adapters/slime/bringup.py:365–392` 的 `try` 包住 `_install_native_cli`、用户初始化、guard 构造以及整个 `ClaudeCodeHarness.run`。`:397–404` 对所有非 `SlimeBindingError` 的 `RuntimeError` 一律包成 `harness_bootstrap_failed`，没有核对它来自 Docker 命令结果还是我方/vendor Python 内部错误。实际 vendor `BaseHarness.run` 在 `rh2/src/slime/agent/harness/common.py:97–104` 依次执行 ensure user、配置和 `launch_and_wait`，最后一段同样落在该包装内。

**不变量。** Brief §3A `README.md:36,42,47` 允许 ABORTED 的是已识别的局部运行/服务/传输故障；未知内部异常仍须 FATAL。这里只改变了错误名称，未完成来源分类。同一位置的错误仅因是 RuntimeError 而非 TypeError 就得到不同终态，违反本批要落实的 06 §2 / 第二组 §2 原则。

**完整调用链与生产可达条件。** 非 `s1_compat` 正式调用 `Rh2MilesGenerateFn.__call__ → rh2_custom_generate → RolloutOrchestrator.generate/_generate_attempt → ClaudeCodeDriver.run → ClaudeCodeHarness.run`。当该已启用路径的安装或运行实现抛出未经归因的 RuntimeError，驱动将其改名；`outcome_producer.py:77` 将新码列入局部故障表，`generate.py:3477–3481,3501–3516` 据此选择 ABORTED；`:3592–3612,5006–5028` 生成 missing Outcome 与 aborted 样本。

随后 `adapters/miles/canonicalize.py:192` 将状态映射为 miles `Sample.Status.ABORTED`，`reference/miles-rh2-integration/miles/rollout/fully_async_data_buffer.py:239–256` 在动态 admission 之前调用 unused handler 并丢组。正式 handler 为 drop，因此后面的严格组准入看不到这类内部错误；若只在部分任务路径出现，后续正常组仍可继续，no-progress 不保证发现它。

**可达性：`production_reachable`，证据为当前正式入口调用链及 CPU 故障注入；不是 `production_observed`。** 本轮未观察到真实 CLI 内部 bug，不主张发生频率，也不把它定成 P0。注入只替换当前路径中的故障来源，不启用新功能。

**最小反例。** [error_routing_probe.py](error_routing_probe.py) 用真实 `ClaudeCodeDriver.run` 与真实 formal 编排，复用现有纯 CPU 容器/评分夹具；仅在安装函数或 `launch_and_wait` 注入单个异常。没有运行 Docker、CLI 或网络模型。执行：

```bash
cd rh2
uv run --no-sync python ../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/budget_loop_impl_20260909/batch_a_review/error_routing_probe.py
```

实际结果：

| 来源 | 注入异常 | 当前输出 | fatal 通知 | cleanup |
|---|---|---|---:|---|
| Docker exec 已识别失败 | RuntimeError，exit=124 | ABORTED；`harness_bootstrap_failed` | 0 | 完成 |
| 安装函数内部不变量 | 未归因 RuntimeError | **ABORTED；`harness_bootstrap_failed`** | **0** | 完成 |
| 完成引导后的运行函数内部不变量 | 未归因 RuntimeError | **ABORTED；`harness_bootstrap_failed`** | **0** | 完成 |
| 同一运行位置 | 未归因 TypeError | `pre_finalize_failure_unclassified` FATAL；无 Outcome | 1 | 完成 |
| CLI 版本错误 | typed `cc_version_mismatch` | `pre_finalize_failure_unclassified` FATAL；无 Outcome | 1 | 完成 |

**影响与分期。** 本批 I05 的未知错误关闭路径尚未完整落实；建议批 A 提交前窄修。不是新的训练策略或 T0，也不要求推翻六项待确认范围。

**窄修验收。** 在能够证明来源的 Docker/引导边界产生局部故障类型，驱动只转换该类型或等价的明确结果；不能用包住整个生命周期的 `except RuntimeError` 或错误文本匹配代替归因。安装和运行内部裸 RuntimeError 均须保持未归因并由编排 FATAL，保留原始 cause、通知停止、不返回 ABORTED，清理继续；明确的局部命令失败仍 ABORTED，CLI typed 配置错误继续 FATAL。不要为此新增通用错误分类平台，也不反向把所有 Docker 非零退出都认定为内部损坏。

## 本轮未发现新增问题的部分

- **编排通用分流。** `generate.py:3469–3516` 对非兼容模式且未 finalize 的异常只接受表内 `SlimeBindingError`；其余进入 `_structural_contract_fatal`，记录 failure、同步通知后抛出。独立探针已验证 TypeError 与未映射的 CLI 版本码都不产 Outcome、不返回 ABORTED。
- **两条 capture 矛盾。** 实际抛出点 `generate.py:2896–2912` 未改；`leaf_facts_length_mismatch` / `capture_record_unknown_in_backfill` 已从映射表移除（`outcome_producer.py:108–115` 仅保留文档集合），因此经真实 except 路径会进入 FATAL。不是仅新增一个未被消费的集合；判定仍来自同一张映射表。维护测试的定向重跑由主审执行，本报告不把作者全量结果冒充本轮验证。
- **fatal 生产接线。** `BringupService._resolve_task`（`bringup.py:1573–1579`）在编排前登记执行并安装通知器；`shutdown/chain.py:243–261` 将 fatal 交给 lifecycle，`bringup.py:2256–2285` 调度关停。异常也经 `Rh2MilesGenerateFn` 原样上抛，miles `inference_rollout_common.py:167–175` 取消并收齐同组兄弟任务；`fully_async_rollout.py:241,375–381` 由 worker/消费端继续抛出。没有发现此批把已经形成的 FATAL 重新变成样本丢弃。
- **明确保留的六项。** 身份缺失、finalize 前 ValidationError、artifact 持久化失败、装配 mask 缺失、image digest 与 testbed lineage 两码，当前分别仍在表中或专门 ValidationError 分支中（`outcome_producer.py:81,90–96`；`generate.py:3456–3468`），符合本次任务指定的实施范围。即使此前建议改 fatal，也不据此把未批准切换误记为本批漏实现。
- **兼容与已完成对象。** `_pre_finalize_exception_is_attributed` 对 `s1_compat` 和已 finalize 对象返回旧入口；后者仍由 `generate.py:3573–3589` 走既有 `post_finalize_failure_unclassified`，不会重新生产 missing Outcome。取消仍有独立 `CancelledError` 原样传播分支。

本轮产物仅本报告与独立探针；未改业务源码、维护测试或主 Brief，未提交。停止条件：R1 的当前错误来源、真实编排结果与 miles 后果均已定位，其余本批必要分流已核对；不扩展到预算 B/C/D 或全仓异常审计。
