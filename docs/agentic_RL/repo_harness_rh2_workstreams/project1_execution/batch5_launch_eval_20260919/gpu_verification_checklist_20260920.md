# 第五组：留到真实八卡核验的清单（I21 / I22 / I36）

2026-09-20 / Claude（A 线分叉）。用途：第五组本机部分已收口（[Brief §11–§15](i21_eval_brief_20260919.md)），下面是**只有真实引擎 / 真实 CLI / 真实并发才能确认**的事项。每项给出：看什么、判据、本机证据到哪里为止。真实八卡试运行时逐项勾核，结果回写本页"核验记录"列；不通过的项按所属接缝回到 A 线修。

不在本页：实验矩阵、预算、并发与数值参数（随八卡作业方案定）；I18 路由语义（单独决定，试运行只补证据）；反作弊（流水线与基座探针阶段定）；题目与统计协议（B 线）。

## 0. 启动配置核对（写八卡启动命令时对照）

| 形态 | miles 参数 | RH2 环境 |
| --- | --- | --- |
| 训练中评测（共享引擎） | `--eval-interval N`；恰好一个评测数据集，文件就是评测题包的 `prompts.jsonl`，`--input-key` / `--label-key` / `--metadata-key metadata` 与训练一致；`--custom-eval-rollout-log-function-path repoharness2.adapters.miles.eval_report.log_eval_rollout_data`；`--eval-num-gpus 0`；不配 `reward_key` / `eval_reward_key` / `ci_metric_checker_key`；`--eval-max-prompt-len` 建议不设（设了会让加载器丢长题，被丢的题会如实列为缺失、评测点不完整） | 训练题包四项 + `RH2_EVAL_PREPARED_TASKS_DIR`、`RH2_EVAL_PREPARED_TASKS_MANIFEST_SHA256`、`RH2_EVAL_HOST_GRADING_ARTIFACT_PATH`、`RH2_EVAL_HOST_GRADING_ARTIFACT_SHA256`；`RH2_EXECUTION_MODE=fa_formal`；`MILES_RH2_EVENT_DIR` 已设（否则没有 `eval_point` / `eval_window` 事件） |
| 独立固定 checkpoint 评测 | 上一行全部，外加 `--fully-async`、`--debug-rollout-only`、`--num-rollout 0`、`--disable-rollout-global-dataset`（没有训练文件时必须）、`--hf-checkpoint <被评的 HF 导出目录>`；**不得**带 `--skip-eval-before-train`、`--start-rollout-id`、`--sglang-load-format dummy`；首版不使用 engine group 的 `model_path` 覆盖 | 评测题包四项 + `RH2_EVAL_ONLY=1`；训练题包可不配；**不得**设 `MILES_SGLANG_DUMMY_LOAD=1` |
| 冷恢复 | `--load <checkpoint 目录>`，**不传** `--start-rollout-id` | 同训练 |

旧 `rh2/experiments/miles_gpu_spike/launch.sh` 钉的是 `s1_compat` 与 stock filter，不能直接沿用。

**RH2 预检实际在哪里运行：** `BringupService` 在首条样本到达 `Rh2MilesGenerateFn` 时才启动，预检随它执行。配置错误可能在此前就使作业失败，例如没关全局训练数据源又没有 `--prompt-data`，miles 构造数据源时即 `TypeError`；也可能让作业根本没有样本，例如零轮时跳过首次 eval、使用非零起点，或评测题全部被加载器过滤。这些情况下不能声称 RH2 预检已执行。非 fully-async、非零轮、未开 rollout-only、dummy 加载等错误，也只有在样本确实进入 RH2 时才会被这里拒绝。当前先靠本表约束启动命令；同一纯函数 `validate_eval_wiring` 可由后续 launcher 在分配 GPU 前直接调用，但当前没有这一前置接线。

## 1. I21 共享引擎形态（训练中评测）

| # | 核验什么 | 怎么看 / 判据 | 本机证据止于 | 核验记录 |
| --- | --- | --- | --- | --- |
| E1 | 真实 CLI 接受上表参数组合，RH2 预检通过 | 作业启动；`startup_evidence.json` 的 `eval_wiring.enabled=true`、`eval_task_count` 等于题包题数、`eval_max_prompt_len` 为预期值 | 预检纯函数与真实 `BringupService` 启动用例（替身引擎）；未跑 miles 全量参数解析 | |
| E2 | 评测钩子在真实 RolloutManager 进程里被加载并接管 | 每次评测有一条 `eval_point` 事件；tracking 出现 `eval/<数据集>/planned` 等键；没有 miles 默认 `eval/<数据集>` 均值；评不了分的样本不引发日志异常 | 钩子与 miles 日志原函数体的 CPU 运输 | |
| E3 | 宿主盖章在真实进程生效，评测点可区分 | eval attempt 的 audit 行 `evaluation.eval.eval_point_id` 在场；`--eval-interval 1` 时训练前与第 0 步之后两次评测的 `eval_rollout_id` 都是 0 而 `eval_point_id` 不同 | fork 原函数体（AST）盖章；真实进程未跑 | |
| E4 | **模型绑定**：评的就是刚发布的权重 | `eval_point.target_weight_version` 等于该时刻 RolloutManager 已发布版本；`observed_weight_versions` 只有这一个值；`binding=verified`。至少核两个不同版本的评测点（训练前、若干步之后） | 目标版本透传与 `verified / mismatch / unverified` 判定逻辑；真实引擎回报版本未验 | |
| E5 | 评测期间不发生权重发布 | `eval_window` 的 start / end 时间戳之间没有 publish / `set_weight_version` 事件 | 驱动 `await dispatch` 的源码事实与 AST 控制流 | |
| E6 | **重叠代价**（首版不排空在飞组） | `eval_window.active_groups`（start / end）；对比评测窗口内外：训练 episode 的 `episode_deadline.hit_by` 硬墙截断率、评分反压次数 / 排队时长、单点评测墙钟。代价明显时再决定排空或限流（需用户决定，首版未做） | 只证明"暂停新组提交、不排空"这一行为；代价无本机数字 | |
| E7 | 单题基础设施失败不伤训练、不记 0 分 | 评测中让一道题的评分失败，并**确认命中的是评测 attempt**：`RH2_INJECT_INFRA_INSTANCE` 只按 `spec.task_id` 匹配、用全局一次性 marker，不区分训练与评测——题目与训练重合且有在飞训练时，故障可能先落在训练 attempt。选一道评测专属的题，或注入后回读该 attempt 的 audit 行确有 `evaluation` 块（或直接杀该评测 attempt 的评分容器）。命中后：该 attempt `result_class=reward_unavailable`、`reward=None`；`eval_point.complete=false`、`reward_unavailable=1`；训练继续、驱动不退出 | 真实 orchestrator + 真实 `SWEGradingManager`（FakeDocker） | |
| E8 | 既定题单与实际评测一致 | `planned_source=eval_package`、`prompts_not_loaded=0`、`missing_members=[]`；若刻意设 `--eval-max-prompt-len`，被过滤的题逐条出现在 `missing_members` | 真实 `Dataset` 过滤 + 假 tokenizer；真实 tokenizer 下的长度未验 | |
| E9 | 评测不混进训练统计 | 对真实 run 目录跑 `python -m repoharness2.adapters.miles.run_report <run_dir>`：`eval_audit_rows>0`；训练各 facet 的 attempt 数与 `rollout_group` 成员数对得上；`costs.evaluation.snapshots` 等于评测 attempt 数；评测重评分只出现在 `evaluation.grading_regrades` | 真实 writer 的 CPU 用例 | |
| E10 | 评测 attempt 自己的资源已关闭 | 按评测 attempt 核对：每个带 `evaluation` 块的 audit 行 `lease_released=true`、无 `cleanup_failures`，其容器 / 私网已删除。共享形态下评测结束时仍有合法的在飞训练容器，**不能用"总容器数为零"作判据**；整 run 的 `rh2.run_id` 标签清零与最终关停 verdict 放到作业结束时核 | 既有清理链用例（与训练 attempt 同一条链） | |
| E11 | 评测结果 tracking 与题包分母的双口径 | 面板同时有 `resolved_rate_graded` 与 `resolved_rate_planned`；全缺失的点 `resolved_rate_graded` 缺省而不是 0 | 指标函数用例 | |

## 2. I21 独立固定 checkpoint 评测作业

| # | 核验什么 | 怎么看 / 判据 | 本机证据止于 | 核验记录 |
| --- | --- | --- | --- | --- |
| A1 | 真实 CLI 接受 §0 的独立评测形态（`--fully-async --debug-rollout-only --num-rollout 0 --disable-rollout-global-dataset --eval-interval 1 …`，含 miles 对 `num_rollout` / `num_epoch` / 调度相关参数的校验） | 作业能起；若 miles 参数校验拒绝零轮，记录报错原文并回 A 线定替代形态 | 同一份形态连过真实训练数据源构造、`train_async.train` 原函数体（调用即提交的 remote 替身）与 RH2 预检：恰好一次 eval、零训练提交；未跑真实参数解析 | |
| A2 | 只发生评测、没有训练派发 | 事件里恰好一组 `eval_point` / `eval_smoke`（rollout 0）；没有 `rollout_group`、`group_consumed`、`train_step`；RH2 没有出现 `training_dispatch_in_eval_only_mode` | 同上 + RH2 预检要求零轮与 rollout-only | |
| A3 | **引擎里载入的确实是被评 HF 导出的权重**（路径相等不够：dummy 加载时 `model_path` 相同而权重随机；engine group 覆盖时有效路径不同） | 逐引擎核对：① 有效启动参数 `load_format` 不是 `dummy`、有效 `model_path` 等于 `--hf-checkpoint`（引擎启动日志 / ServerArgs 转储）；② 引擎启动日志有从该目录载入权重的记录（分片数、耗时），没有 dummy / 随机初始化字样；③ SGLang `/get_model_info` 的 `model_path` 一致；④ 全程没有 publish / `set_weight_version` 事件；⑤ 抽几条固定 prompt 做 greedy 生成，与同一导出在独立 SGLang 上的输出对照，作为辅助证据；若不同，记录推理配置与数值差异并调查。仅仅"与已知基座输出不同"既不能证明加载的是目标 checkpoint，也不能排除随机权重。评测记录里的 `configured_hf_checkpoint(s)` 只是配置来源，`binding=unverified` 在此形态是预期，不能据路径相等或少量抽样口头升级为"模型已验证" | 真实 `_compute_server_args` 的有效参数（正常 / dummy 环境变量 / dummy CLI / group 覆盖）与"rollout-only 不发布权重"的两处源码事实；预检已把 env / CLI 的 dummy 加载排除在本形态之外，拓扑覆盖仍靠逐引擎核对；真实加载未验 | |
| A4 | HF 导出与训练 checkpoint 的对应关系可追溯 | 记录导出方式（训练时 `--save-hf` 或离线转换）、对应的 rollout id / 迭代、导出目录；同一 checkpoint 导出两次的评测结果在抽样噪声内一致 | 无 | |
| A5 | 没有训练题包也能启动 | `startup_evidence.json` 的 `eval_wiring.eval_only=true`、`train_task_count=0`；sandbox profile 核对用的是评测题包镜像 | 真实 `BringupService` 启动用例（替身引擎） | |
| A6 | 基座诊断（I36 第一类）可直接用本形态 | 对基座 HF 目录跑一次小批评测：逐题结果三类分开、失败题带评分侧类别，供 B 线 agent 逐题检查 | 结果载荷与聚合用例 | |

## 3. I22 冷恢复

| # | 核验什么 | 怎么看 / 判据 | 本机证据止于 | 核验记录 |
| --- | --- | --- | --- | --- |
| R1 | 按操作约束的真实恢复 | 训练到 checkpoint k 后杀作业，用同一 `--load`、不传 `--start-rollout-id` 重启：出现 `run_restarted`（含旧 run_id、恢复 rollout id、已发布版本 p）；bootstrap 发布标 p、首次真实更新标 p+1；无 `RecoveryVersionMismatch` / `RecoveryStateMissing`；旧 buffer 与在飞组不出现在新 run | W5b CPU 用例（真实 data source + AST 的 RolloutManager.save/load） | |
| R2 | 手填编号错配被拒 | 同一 checkpoint，故意传错的 `--start-rollout-id`：所有 trainer rank 在 actor 初始化阶段抛 `RecoveryStartMismatch`，作业在任何 publish 之前非零退出，没有写出新的状态文件 | `resolve_restore_rollout_id` / `restore_updater_weight_version` 用例；多 rank 真实失败路径未验 | |
| R3 | 实际加载方式下 `loaded_rollout_id` 的取值 | 记录目标配置（bridge 或非 bridge）下：全新 run（框架自置 `start_rollout_id=0`）不被 R2 的检查误拒；finetune / 参考权重加载报告的迭代值 | 既有用例只固定了"`0` 不算恢复"的语义 | |
| R4 | 保存频率与可接受重算窗口 | 按作业方案的 `--save-interval` 实测单次保存耗时与恢复耗时 | 无 | |

## 4. I36 完整八卡验收里与 A 线已交付件相关的核验（指针）

本页不重复这些条目的细节，只列出处，试运行时一并核：

| 范围 | 出处 |
| --- | --- |
| CP>1 / 多 engine 真机资格、`normalize_advantages=false`、单 rank 失败的 watchdog 行为、no-progress 停止数值、staleness / 成本阈值 | [06 执行计划 §3 决策包 C](../../06-first-training-local-execution-plan.md) |
| 真实 Claude Code 对预算拒绝（403）的退出行为、强停后的残留进程、目标 GPU 上 abort 广播到达率（用 `termination.stop`、`harness_exit_code` 字段证明） | [预算闭环 README "不宣称"段](../budget_loop_impl_20260909/README.md) |
| 评分期限 / 追加评分 / 退出改判在真实 Docker 与真实关停下的表现 | [第 2 组剩余实施 README](../failures_remainder_impl_20260909/README.md) |
| 压缩恢复后真实 CC 请求面与 B 表示的分叉行为 | [I19 Brief](../batch3_training_signal_20260909/i19_impl_brief_20260910.md) |
| run 报告在真实 run 目录上的可用性；TP>1 下逐叶 DIS 统计的限制 | [I20 Brief](../batch3_training_signal_20260909/i20_run_report_brief_20260910.md) |
| MoE 路由重放：试运行只补证据，正式语义单独决定 | [第三组决定](../batch3_training_signal_20260909/) |

## 5. 记录方式

每项核验后在"核验记录"列写：日期、run_id、结论（通过 / 不通过 / 不适用）与证据路径（事件文件、`startup_evidence.json`、run 报告输出）。不通过项另在 `infra.md` 记一条，指明接缝与复现条件。运行产物放 `runs/` 下的明确路径，不回写历史证据。
