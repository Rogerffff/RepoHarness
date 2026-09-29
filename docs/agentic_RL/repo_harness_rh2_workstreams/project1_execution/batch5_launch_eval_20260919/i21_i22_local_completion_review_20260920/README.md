# 第五组剩余本机部分审查（2026-09-20，Codex A 分叉）

**结论：I22 正编号配对窄修接受；I21 独立评测的本机收尾还需 LR1/P1、LR2/P2 两项修正。** 上一轮 IR1–IR3 维持核销。本轮发现的是新启动形态的配置接缝与模型来源证明不足，不需要重新决定独立/共享评测方案，也不需要为修复新增 T0。第六、七组讨论可以继续。

对象：主仓库 `bac7659ea70cc07a3a8c872a29e7659a894afc5a` 上的未提交增量；miles fork `275e31eb21ecceeb27cb0d1a522c6a59f348dc2e`。本轮只写审查文档、探针和导航，未修改生产代码、维护测试、配置或 fork，未提交、push 或通知其它任务。未跑 Docker/GPU/远端作业。

## 1. LR1 / P1：独立评测形态仍缺启动条件，现有本机测试绕过了两个真实接缝

### 当前行为与反例

交接将 `--debug-rollout-only --num-rollout 0 --eval-interval N --hf-checkpoint ...` 描述为只评测的驱动形态，并允许不配置训练题包。但真实控制流还受两项配置支配：

1. **`--fully-async`。** 真实 CLI 默认是 False。`train_async.train:120–122` 在非 fully-async 分支先提交 `generate(start_rollout_id)`，然后才进入零轮循环，因此 `num_rollout=0` 并不阻止这一预取。新测试把 `fully_async=True` 固定在夹具里，RH2 预检也未检查它。独立探针中，预检返回 True，事件为 `update_weights_call_noop → eval(0) → training_generate(0) → dispose`。这违反“没有训练派发”的承诺；真实 Ray 的 `.remote()` 一经调用即提交，不等随后 await。
2. **miles 的训练数据源。** `rollout_global_dataset` 默认 True；RolloutManager 先构造默认 `RolloutDataSourceWithBuffer`，它立即读 `args.prompt_data`，之后才构造 rollout/eval 函数。独立作业只提供评测文件、`prompt_data=None` 时，真实 Dataset 抛 `TypeError: expected string or bytes-like object, got 'NoneType'`，还没进入 RH2 评测入口。加入 `--disable-rollout-global-dataset` 的正控成功，数据源为 None。已有“不配置训练题包能启动”用例只执行 BringupService，没有覆盖这个更早的 miles 数据源构造。

这不是要求现在写完八卡所有模型参数，而是两项无需 GPU 就能确定、且改变“能否只做评测”的必要条件。一般训练命令已带 `--fully-async` 不构成独立作业自然拥有它的证据；应将条件写进该形态并由测试消费同一配置。

另一个边界是 `--skip-eval-before-train`：文档已禁止它，但现有 RH2 预检仍接受，零轮作业随后没有任何 eval。把禁止项作为运行命令约束可以，但不能说现有预检已覆盖它。`BringupService` 是首次 generate 时才创建；若想提前拒绝“完全不派发评测”的配置，不能只把检查加进首次样本才会调用的函数。

### 建议、锚点和验收

**本轮修正：** 继续复用现成驱动。首版明确选择 fully-async、关闭未使用的全局训练数据源；启动配置核对和 CPU 用例保持一致，不必另建评测驱动或增加无关守卫。正形态至少包含：

```text
--fully-async
--debug-rollout-only
--num-rollout 0
--disable-rollout-global-dataset
--eval-interval N
--hf-checkpoint <被评 HF 导出>
```

这仍是形态片段，不是完整启动命令；评测文件、采样、RH2 环境与模型参数沿既定方案补齐。`skip_eval_before_train=False`、零起点继续保留。

**锚点：** RH2 `rh2/src/repoharness2/adapters/slime/eval_wiring.py:68–92`；夹具 `rh2/tests/adapters_miles/test_i21_eval_only_driver.py:94–99`；fork `train_async.py:120–123`、`miles/ray/rollout/rollout_manager.py:78–79`、`miles/rollout/data_source.py:60–74`。真实 CLI 选项注册在 `miles/utils/arguments.py:495,1034`，默认分别为 False、True。

**复现：** [probe.py](probe.py) 的 `cli_shape`、`drive`、`data_source_case`；结果见 [results.json](results.json) 中 `selected_cli_defaults`、`non_fully_async` 和 `default_data_source_without_training_file`。Ray/模型被替换，驱动原函数体、DataSource 与 Dataset 保持真实。探针的 remote 替身在调用时记录提交，避免用 async 替身把未 await 的预取误当成没有提交。

**验收：** 用统一的一份独立作业配置连过默认数据源构造与驱动控制流：无训练文件也可构造；恰好一次 eval，零训练提交；非 fully-async、默认全局数据源但无训练文件、跳过首次 eval 三个反例明确拒绝或明确排除在该启动形态之外。说明实际预检在哪里运行，不能把首条样本上的检查写成“无样本时也会执行”。完整 miles CLI 及设备启动仍可留部署环境验证。

## 2. LR2 / P2：路径字段只能证明配置来源，当前 A3 判据会漏掉 dummy 加载

**当前行为：** `generate.py:2725–2727` 把 `args.hf_checkpoint` 写为 `engine_model_path`。作为用户配置的来源记录，这个值有用；但新测试只搜索三段源码，就推断 rollout-only 引擎实际服务该导出的权重，清单 A3 又主要核对引擎的 `model_path` 与这一字段相等。

真实 `_compute_server_args` 在初始字典之后还会应用环境变量、CLI 字段与 engine group overrides：

| 配置 | RH2 预检 | 记录的 HF 路径 | 有效引擎路径 / load_format |
| --- | --- | --- | --- |
| 普通配置 | 通过 | `/ckpt/hf_step_20` | 同路径 / auto |
| `MILES_SGLANG_DUMMY_LOAD=1` | 通过 | `/ckpt/hf_step_20` | **同路径 / dummy** |
| `--sglang-load-format dummy` | 通过 | `/ckpt/hf_step_20` | **同路径 / dummy** |
| engine group 覆盖 model_path | 通过 | `/ckpt/hf_step_20` | `/ckpt/other` / auto |

因此，“路径相等 + 没有权重发布”不足以证明载入了目标 HF 权重：dummy 形态保留同一模型路径，而 rollout-only 又不会用 trainer 权重覆盖它。上表证明的是有效参数，不冒充 GPU 上已发生了错误加载。模型路径覆盖在现有 A3 路径对照中应能被发现；它也说明 audit 字段并不是无条件的“引擎实测路径”。

**影响：** 独立基座/固定 checkpoint 评测可能把错误初始化归因于被评模型；按当前 A3 仅看路径的判据仍可能误验收。`binding=unverified` 保留得正确，应继续保留，不能用路径相等将它口头升级为模型已验证。

**本轮建议：** 明确字段是配置来源（可以改成更准确的名字，也可以保留兼容字段并明确说明）；首版形态排除 dummy 加载，明确 group model override 的支持范围。用真实 `_compute_server_args` 的有效值替代三个源码字符串断言作为配置证据；GPU 清单再核对实际加载方式/启动加载日志、有效模型路径与 HF 导出对应。无需逐请求模型哈希或新的绑定平台。

**锚点：** `rh2/src/repoharness2/adapters/slime/generate.py:2725–2727`；`rh2/tests/adapters_miles/test_i21_eval_only_driver.py:127–138`；fork `miles/backends/sglang_utils/sglang_engine.py:794,821–822,877–888`，group overrides 的生产传入点为 `miles/ray/rollout/rollout_server.py:54,72`；[GPU 清单 A3](../gpu_verification_checklist_20260920.md) 第 39 行。

**复现与验收：** [probe.py](probe.py) 的 `engine_config_case` 执行真实组装函数，只替换 GPU 定位、LoRA 分支与 ServerArgs 字段集合；结果 `engine_configs`。修后普通 auto 正控成立；env/CLI 两个 dummy 反例被启动形态排除，或明确阻止其被当作目标 checkpoint 评测；若支持覆盖则记录有效来源。清单不得只凭路径相等验收权重加载。

## 3. I22 窄修接受及清单补充

I22 的正编号配对检查位于 `restore_updater_weight_version → resolve_restore_rollout_id`，先于 sidecar 读取，也先于首次 publish。八组独立对照：四个正编号错配均 `RecoveryStartMismatch`，状态文件读取次数为零；`(5,4)` 和 `(None,4)` 读状态 4；`(0,9)`、`(5,None)` 保留原语义。维护测试还覆盖真实状态文件，未改变 B-3 的 p / p+1 规则。oracle 从 `(5,2)→4` 改为拒绝符合用户“不开放手工重编号、允许简单匹配修复”的既有授权，不需要新 T0。

接受范围是 **I22 本次正编号窄修**，不是完整恢复正确性。`0`、加载点未知、目标加载方式、真实多 rank 退出仍按清单核验；继续“指定 checkpoint、不手填编号”。

GPU 清单另有两处建议在开跑前澄清，属于文档口径，不要求现在改生产机制：

- **E7：故障注入归属。** `_grading_submit` 只匹配 `spec.task_id`，用全局一次性 marker 竞争，不区分训练与评测。在允许 train/eval 题目重合、且存在在飞训练的条件下，故障可能先落在训练 attempt。测试时选择评测专属题，或按明确的 eval attempt 注入并回读归属；不要仅凭“配置了评测题 ID”认定已命中评测。也不必为此恢复全局 train/eval 互斥。
- **E10：残留资源的范围。** 共享形态保留在飞训练，eval 结束后还会恢复 producer。应核对该次 eval attempt 的资源是否关闭；同 run 的合法训练容器/私网不能算评测残留。整 run 标签清零与最终 shutdown verdict 放到作业结束核验，不能在评测窗口结束时用总容器数为零作判据。

## 4. 本轮验证

| 项 | 独立结果 |
| --- | --- |
| 9 个 I21 文件 + W5b 冷恢复文件 | **120 passed / 0 skipped**，见 [focused_tests.log](focused_tests.log)。 |
| 完整双 lane | **A 461 passed / 340 skipped；B 801 passed / 0 skipped**。A 的 skip 来源、fork 工作树与树摘要、19 个语义 patch 存档摘要、pin 均通过，见 [integration_lanes.log](integration_lanes.log)。 |
| 相关生产/测试文件与 fork rh2_recovery 的 ruff | 通过；fork 原配置有 lint 字段迁移提醒，非代码告警，见 [ruff.log](ruff.log)。 |
| 独立探针 | 3 个驱动形态、2 个真实数据源、4 个有效引擎参数、8 个恢复对照，以及目标 CLI 选项的真实注册默认值；见 [results.json](results.json)。 |
| 版本 | [verification.json](verification.json)；13 个相关源文件在验证结束后无摘要漂移，fork 工作树干净。 |
| 未跑 | 完整 miles CLI、Docker、GPU、远端、全 CPU 套件。不将这些窄探针说成真实模型加载或端到端执行。 |

从仓库根目录重跑：

```bash
bash rh2/scripts/miles_integration_lanes.sh
cd rh2
RH2_MILES_PATH="$PWD/../reference/miles-rh2-integration" uv run pytest -q tests/adapters/test_i21_eval_{delivery,wiring}.py tests/adapters_miles/test_i21_eval_{bringup_vertical,entry,fork_seams,identity,report,run_report,only_driver}.py tests/adapters_miles/test_w5b_cold_recovery.py
RH2_MILES_PATH="$PWD/../reference/miles-rh2-integration" uv run python ../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/batch5_launch_eval_20260919/i21_i22_local_completion_review_20260920/probe.py
```

## 5. A–N 适用性与下一轮边界

| 维度 | 本轮证据与结论 |
| --- | --- |
| A / E / G | 真实驱动函数、立即提交的 remote 语义、真实 DataSource/Dataset、有效参数组装、恢复调用链。LR1 暴露了仅验证内部循环而绕过启动消费者的缺口；LR2 暴露了字符串断言不能证明最终配置。 |
| B / C / F | 不改训练/评分分布与已批准语义。I22 正编号 oracle 翻转可接受；未增加临时挡板或恢复手工重编号。IR1–IR3 不重开。 |
| D / H | 配置来源与引擎实际加载事实应分清，见 LR2；题包和数据源是两个消费者，见 LR1。恢复仍以 trainer 返回迭代为配对依据。 |
| I / J / K | 修正启动形态与配置测试即可，不建议为独立评测另造生命周期；本机可确定项先补，真实 CLI/加载/并发仍按部署条件核验。 |
| L / M | 单独评测不应意外启动训练；共享评测保留重叠代价观测。模型来源字段可留，但不是已加载权重的证明；GPU 清单的注入归属与清理范围应明确。 |
| N | 0020 存档、manifest 与实际 fork 一致，两条 lane 通过。实际 Megatron/SGLang 参数解析及多 rank 行为未验证，不据 CPU 替身扩张结论。 |

下一轮只核 LR1、LR2 的反例/正控及清单澄清。无需等待八卡才能修这两项，也无需阻塞第六、七组讨论；不扩为新的全仓审计。
