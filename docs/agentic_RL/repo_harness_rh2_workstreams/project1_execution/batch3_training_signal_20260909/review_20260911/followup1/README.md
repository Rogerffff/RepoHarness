# I20 R1–R5 修后针对性复核（2026-09-11）

**结论：R1 / R2 / R3 通过；R5 按明确的 TP 支持范围收口；R4 尚有一处原 P2 余项，另发现本次修复新增的一项 P2 直接回归 R6。** 两项均只影响报告，不改变训练 reward、loss、准入或路由。I19 已通过结论保持，注释余项也已清理。无新 T0。

范围：`76ede7f4` → `bc2cfa711c188c71d5e110ee8bb9875b9456c298`，修复提交 `c8bf6bd4`、计数 `1bc2dfb7`、说明 `bc2cfa71`。只复核 [上一轮报告](../README.md) R1–R5 及直接回归，不重开 I19 表示验收、N1–N4、I18 或第四组。此轮为纯消费者 / schema 与注释修正，按审查标准 §10.4 / §10.5 由主审完成窄复核，不重复安排上一轮双角色。

## 1. 已闭合内容

| 项 | 主审实测 | 结论 |
|---|---|---|
| R1 生命周期 | 真实 audit writer 的 `test=40 秒`、`sandbox_container_start=3.5 秒` 正确进入分段；队列深度 7 进入计数，未进入秒数桶。 | 通过。 |
| R2 评分来源 | 真实 bringup writer 写出的已评分记录被统计为 graded=1、无评分记录=0；不提供 bringup 记录时为未知。维护测试另覆盖 reward=0 与已知无评分块。 | 通过。 |
| R3 FORK 成员 reward | 真实 rollout emitter 的 `[10,10,10,11]` 归并为 2 个成员、4 行，reward 均值 0.5，优势符号正 1 / 负 1。已标明 delivered 总体与过滤前未知；矛盾成员单列。 | 原问题通过。 |
| R4 两个 run 均有事件的正控 | 默认子报告分别给 r1=16、r2=40 accepted token；指定 r2 后只含其 1 条 audit、1 条 bringup。一个 bundle 内确有两个 run 时，audit 归属未知，不强行并入。 | 这些路径通过；第 2 节还有余项。 |
| R5 TP 副本 | 真实 emitter 的 CPU 基数模拟中，可比动作数从 32 还原为 16，保留不同 DP 的真实叶；DIS 的无完整身份事件明确注明 TP>1 不支持。 | 按上轮允许的缩小支持范围方案收口，未实现 TP>1 的 DIS 安全去重。 |
| I19 文字 | `generate.py` 四处旧注释改为纯观测；Brief 收窄参考版本与目标 CC 的区别。 | 通过，不重开实现审查。 |

R5 的边界应保留：`sample_dis_accounting.accepted_tokens_sum` 等仍是原始事件累计值，TP2 模拟仍含重复；`tp_copies` 字段已明确不支持。不能对外改述为“所有 TP 指标都已去重”或“本机验证了分布式 GPU 路径”。

## 2. R4 余项 / P2：另一个 bundle 缺事件时，仍被强行归给唯一可见 run

**位置**：`rh2/src/repoharness2/adapters/miles/run_report.py:774–788`，尤其 `:776–777、784–785`；默认单 run 输出 `:815–817` 也需要与修正一致。

**当前行为与不变量**：`_attribute_run()` 无法从本 bundle 得到归属后，只要所有输入中恰好出现一个 run_id，就把该 bundle 的 audit / bringup 归到它。它把“只看见一个有事件的 run”当成了“全部输入只来自这个 run”，仍违反 R4 的未知不强行关联，也与 Brief 所称“bundle 内恰有一个 run 才归属，否则只计数”不一致。

**生产可达性**：production_reachable。事件是可选采集，I20 本来就支持没有 `MILES_RH2_EVENT_DIR` 的输入和若干目录；不需要异常 schema、文件篡改或未规划的训练模式。

**主审反例**：两个独立输入目录 A、B，各由真实 writer 写 1 条 audit 和 1 条 bringup。仅 A 有 run_id=r1 的事件，B 没有事件文件。调用真实 loader / report 并指定 r1：

```text
实际：r1.audit_rows = 2，bringup_rows = 2，unattributed_audit_rows = 0
      r1 的按 task 评分分布同时出现 task-s-1 和 task-s-2
应为：r1 仅 1 条 audit、1 条 bringup；B 的两类记录归属未知、分别计数
```

为 B 补上 r2 的事件后，其它输入不变，报告马上恢复 r1 / r2 各 1 条。说明不是 writer 或 session 字段形状的问题，而是缺事件触发的归属兜底。

**影响、分期与最小修复**：保留原 P2，建议本轮修。取消“依据其它 bundle 的唯一 run 自动认领”这两处分支，让未知状态不依赖当前看见几个 run。audit-only 单目录仍可给未绑定 run 的本地摘要；多个文件需要关联时，首版可以要求输入同一 run 根目录，无需发明新 registry。不同 bundle、无法关联的记录不进入具名 run 的统计。

**验收条件**：保留已有双 run 正控；增加上面“一处有事件、一处无事件，指定 / 不指定 run”的真实 loader 反例，确认陌生 task 不混入，未知计数正确。再保留 audit-only 单目录可读的正控。探针键：`R4_remaining_eventless_bundle` 与 `R4_positive_controls`。

## 3. R6 / P2：新增成员级版本统计只取首叶，遗漏后续版本

**位置**：`rh2/src/repoharness2/adapters/miles/run_report.py:538–553`。本次修复把逐训练行版本统计改为 `behavior_versions_per_member`，但遇到同一成员第二条叶就 `continue`，没有合并它的版本。

**不变量与生产证据**：一个 execution 可在 v5 生成早期动作，更新后在 v6 继续；若上下文改写触发 B 分行，两条训练行可以各携带不同版本。`generate.py:1399–1434、1539–1557` 的 `backfill_leaf_sample()` 按该叶实际入训轮回填版本；`canonicalize.py:417` 逐叶复制；miles `rollout_manager.py:235–329` 的真实 emitter 再逐叶输出 `behavior_versions`。它们没有保证同成员每条叶都带整个 execution 的版本全集。

**生产可达性**：production_reachable，属于现有异步权重更新 + I01 B 分行路径。这里只核对统计消费，不需要决定 I18 的 MoE 路由方案。

**主审反例与影响**：同一成员两条叶分别带 `['5']`、`['6']`，真实 emitter 到报告得到 `single_version=1、multi_version=0`，应为 `single_version=0、multi_version=1`。另一个正反例是 `['5']` 与 `['5','6']`：交换叶顺序后，报告会从单版本变成多版本，而成员经历的版本没有变化。它会低估跨版本执行比例，干扰后续训推对齐诊断，但不会改变训练本身的 staleness 判定。

**分期与最小修复**：这是本次修复新增的直接回归，按 §10.5.6 可在当前窄修里处理，不扩大到其它算法。先按成员收集所有叶的版本，再求已知版本集合；缺版本的部分保留未知事实。更小的替代是保留原先逐训练行统计并标清单位，暂不声称已有成员级版本统计。无需改 producer、loss 或路由。

**验收条件**：`[['5'],['6']]` 判多版本；`[['5'],['5']]` 判单版本；交换同成员叶顺序不改变结果；缺版本不被当成“已确认单版本”。探针键：`R6_member_version_regression`。原 R3 的 reward 去重结果保持不变。

## 4. 验证与复现

- 主审相关维护测试 **71 passed / 0 failed，5.92 秒**，输出 [focused_tests.txt](focused_tests.txt)。覆盖 report 两文件、I19 两案、consume-time staleness、既有丢组 / 成本汇总、masked logprob compare。
- 本轮复用上一轮真实 writer / emitter 生成函数，保留原探针不动，另写 [followup_probe.py](followup_probe.py)；[结果](followup_probe_result.json)同时记录已闭合案例和上面两项余项，不能只看脚本退出 0 就说所有问题已修复。
- 相关源码 / 测试 / 探针 ruff 通过，lanes 仅独立执行 `--checks-only`。未重跑作者 2264 全量或完整双 lane，未运行真实 CC / Docker / API / GPU。R5 为 CPU 发射基数模拟，没有声称验证 GPU collective。
- 基线见 [source_snapshot.json](source_snapshot.json)，收尾核验见 [verification.json](verification.json)。生产源码、维护测试、配置与提交未被本审查修改；I19 动作 / 摘要语义、I18 未定状态保持。

从仓库根目录复跑：

```bash
rh2/.venv/bin/python docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/batch3_training_signal_20260909/review_20260911/followup1/followup_probe.py
```

相关维护测试（`rh2/` 内）：

```bash
RH2_MILES_PATH="$PWD/../reference/miles-rh2-integration" .venv/bin/python -m pytest -q \
  tests/adapters_miles/test_run_report.py \
  tests/adapters_miles/test_run_report_real_emitters.py \
  tests/adapters_miles/test_i19_compaction_representation.py \
  tests/adapters_miles/test_w4_consume_time_staleness.py \
  tests/adapters_miles/test_w4_drop_event_summary.py \
  tests/adapters_miles/test_logprob_compare_masked.py
```

## 5. 停止条件

已闭合 R1 / R2 / R3 / R5 不重开。后续只核对 R4 归属兜底与 R6 成员版本统计这两处窄修的正反例及直接回归；也可删除 / 明确不支持无法可靠给出的对应统计。不补新的采集平台或训练门，不把全面指标完整性、真实 CC 或 GPU 实验加成本次验收条件。
