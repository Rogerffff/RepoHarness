# I21 本机收尾修复复核（2026-09-20，Codex A 分叉）

**LR1（P1）、LR2（P2）均核销，无新增代码阻塞项。第五组本次本机实施与修复审查可以收口，继续第六、七组；真实 CLI、权重加载和 GPU 端到端尚未验收。** I22 维持上一轮接受结论，IR1–IR3 不重开。

对象：[Brief §17](../i21_eval_brief_20260919.md#17-对-codex-本机收尾审查-lr1--lr2-的修复2026-09-20claude已实施本机验证)，相对于[原审查](../i21_i22_local_completion_review_20260920/README.md)的修复。主仓库 HEAD `bac7659ea70cc07a3a8c872a29e7659a894afc5a` 上的未提交工作区；fork 仍为 `275e31eb21ecceeb27cb0d1a522c6a59f348dc2e`，工作树干净。

## 1. LR1：启动形态与反例均符合验收条件

指定形态包含 fully-async、rollout-only、零训练轮、无训练文件时关闭全局训练数据源，并保留首次 eval、零起点。复核继续执行 fork 的驱动原函数体，remote 替身在**调用时**记录提交。

| 场景 | 独立复放结果 |
| --- | --- |
| 同一配置 → 真实 DataSource → 驱动 → RH2 预检 | 无训练文件也能构造，`dataset=None`；恰好一次 eval，无训练提交；预检通过。 |
| 删除 fully-async | 原驱动仍在零轮循环前提交训练预取；预检返回 `eval_only_requires_fully_async_driver`。反例未被异步替身吞掉。 |
| 开全局数据源却不提供训练文件 | 真实 Dataset 在 RH2 之前 `TypeError`；直接调用预检返回 `eval_only_global_dataset_without_prompt_data`。明确从启动形态排除，未声称实际作业已提前执行预检。 |
| 跳过首次 eval | 原驱动没有 eval；直接调用预检返回 `eval_only_initial_eval_skipped`。无样本时仍靠启动命令约束。 |

证据：[probe.py](probe.py)、[results.json](results.json) 前四个场景。维护测试 `rh2/tests/adapters_miles/test_i21_eval_only_driver.py:138` 以同一配置串过三个消费者，反例位于 146、168、187 行；生产检查在 `rh2/src/repoharness2/adapters/slime/eval_wiring.py:100` 起。

**接受范围是指定形态的 CPU 控制流与配置条件。** BringupService 仍在首条样本才创建，新增纯函数检查不自动变成分配 GPU 前的 launcher 检查。原验收条件允许明确启动约束，不要求另造 launcher 才能收口。

## 2. LR2：来源字段准确，有效参数与报告运输通过

`configured_hf_checkpoint` 准确表达 `args.hf_checkpoint` 的配置来源。沿 `generate.py:2729 → eval_result.py:119 → eval_report.py:249 / run_report.py:829–849` 核对，无生产消费者遗留旧字段名。

| 真实 `_compute_server_args` 场景 | 有效参数 / 当前处置 |
| --- | --- |
| 普通 auto | 目标路径 + auto，预检通过；只证明配置组装，未证明加载发生。 |
| env dummy / CLI dummy | 两者均是同一目标路径 + dummy；预检均返回 `eval_only_dummy_weight_load`。 |
| engine group 覆盖路径 | 有效路径变为 `/ckpt/other`，配置来源不变；预检仍可通过。首版不支持该覆盖，GPU 清单 A3 逐引擎核对，没有声称代码已拦截。 |
| 训练中 eval 正控 | 独立评测专用限制未扩到训练面。 |

**实际运输：** 用真实 audit writer、载荷派生、评测聚合和 run 报告处理一个完整且已评分的独立评测点。audit 与交付载荷相同；新字段在报告的 audit 聚合与 `eval_point` 两路都保留；目标发布版本未知时，即使采样版本有值仍为 **`complete=true, binding=unverified`**。配置路径未被升级成加载证明。详见 `model_source_transport`。

真实权重加载仍由 A3 / A4 核验，不新增逐请求模型哈希或绑定机制。

## 3. 清单两处文字澄清（已直接修订）

Claude 对 E7（确认注入命中 eval attempt）、E10（只核评测自身资源）的修订正确。本轮另对[清单](../gpu_verification_checklist_20260920.md)作两处 T2 澄清，不另起代码修复轮次：

1. §0 原文将非零起点等列为一定在首条评测处被拒，但零轮、非零起点可以没有任何 eval。统一为“只有样本实际进入 RH2，惰性预检才执行”；全部题被加载器过滤也可能没有样本。后续 launcher 可复用纯函数，当前未接到分配 GPU 前。
2. A3 删除“与已知基座输出不同”可以替代目标导出对照的推断。错误 checkpoint 或随机权重也可能不同，不能据此证明目标权重。greedy 抽样保留为同一导出的辅助对照；实际加载方式、路径与加载日志仍需核对。

不改变用户决定、不新增闸门或实现阻塞项。

## 4. 本轮独立验证

| 项 | 结果 |
| --- | --- |
| 9 个 I21 测试文件 | **90 passed / 0 skipped**，[日志](focused_tests.log)。 |
| 完整 C5 双 lane | **A 461 passed / 342 skipped；B 803 passed / 0 skipped**。pin、fork 树与干净状态、19 个语义 patch 存档、skip 来源均通过，[日志](integration_lanes.log)。 |
| 相关生产/测试 ruff | 通过，[日志](ruff.log)。 |
| 独立探针 | LR1 三消费者与三个反例；LR2 四种有效配置、训练面正控、完整字段运输，[结果](results.json)。复用原审查的真实函数探针，历史证据未改。 |
| 版本 | [verification.json](verification.json)；探针记录的 14 个相关文件至收尾无摘要漂移。 |
| 未运行 | 完整 CLI、Docker、GPU、远端、全 CPU 套件。作者的 1442 条非 Docker 结果不记成本轮独立验证。 |

从仓库根目录重跑（不要覆盖历史证据）：

```bash
bash rh2/scripts/miles_integration_lanes.sh
cd rh2
RH2_MILES_PATH="$PWD/../reference/miles-rh2-integration" uv run pytest -q tests/adapters/test_i21_eval_{delivery,wiring}.py tests/adapters_miles/test_i21_eval_{bringup_vertical,entry,fork_seams,identity,report,run_report,only_driver}.py
RH2_MILES_PATH="$PWD/../reference/miles-rh2-integration" uv run python ../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/batch5_launch_eval_20260919/i21_local_fix_followup_20260920/probe.py
```

## 5. A–N 适用性与停止条件

| 维度 | 本轮证据与边界 |
| --- | --- |
| A / E / G | 真实 DataSource/Dataset、驱动函数体、立即提交的 remote、有效参数组装及 audit/report 运输；不以替身代替真实进程或设备证据。 |
| B / C / F | 四条新增检查限定独立评测，不改训练 reward、mask、组成员或丢组语义；训练中 eval 正控通过。无新增临时挡板或 T0。 |
| D / H | 配置来源与有效引擎参数分开；预检调用时点明确。交付与 audit 继续共用派生函数。 |
| I / J / K | 补必要启动条件与字段含义，不另造生命周期；清单文字当场澄清，不要求新的实现循环。 |
| L / M | 指定独立形态没有训练预取；来源可见、绑定不伪造。共享资源竞争和性能属 GPU 清单，本轮未测。 |
| N | fork 未变，双 lane 与存档通过；改名覆盖生产消费者，历史工件保留。完整 CLI、实际 SGLang 加载仍待核验。 |

**停止条件已满足：** LR1/LR2 不再阻塞本机切片收口。后续按更新后的清单编写真实作业命令并核验，不把本轮通过扩大为完整八卡验收；第六、七组可继续。本轮未改生产代码、维护测试、配置或 fork，未提交、push 或发送跨任务消息。
