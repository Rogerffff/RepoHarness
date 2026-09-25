# Brief：E5 诊断 / 效率两份配置与 GPU 测量入口（I24、I27、I28、I30）——设计稿

2026-09-24 / Claude（A 线）。**状态：设计稿；全部结论来自源码阅读（fork HEAD `275e31eb2`），没有任何测量；待 Codex 审查后实施无 GPU 部分。** 依据：[第六组 README §2 E5](README.md)（不要只加 `--skip-actor-forward-only` 就声称等价；列出实际 logprob / 优势 / loss / 路由消费者；配置只改额外 forward 与诊断能力；测量复用 I20）、[README §8.1 第 3 条](README.md)。只读梳理由 sub-agent 完成（本地 `runs/decision_package_20260924/e5_survey/e5_survey_20260924.md`，git-ignore），以下关键行已由我对照源码核过：`validate_skip_actor_forward_only`、actor 的 forward 条件、`launch.sh` 的批大小与白名单、faithful DIS 的 behavior 来源、`run_report` 与 G1 judge 的缺事件处理。

## 1. 两份配置到底是什么

| | 内容 | 依据 |
| --- | --- | --- |
| 诊断配置 | **就是当前 `launch.sh`**：三个开关都不设（`--use-rollout-logprobs` / `--get-mismatch-metrics` / `--skip-actor-forward-only` 缺省关），`custom_config.yaml` 白名单也不放行它们 | `miles/utils/arguments.py` 缺省；`launch.sh` P 段白名单 awk |
| 效率配置 | 当前配方 **只加一个开关 `--use-rollout-logprobs`**，actor 的额外 logprob forward 条件 `not skip_actor_forward_only and (not use_rollout_logprobs or get_mismatch_metrics)` 变为假 | `miles/backends/megatron_utils/actor.py` `_switch_model` 之后 |
| 不可用 | `--skip-actor-forward-only`：校验要求 `loss_type == "policy_loss"` 且每轮恰一个 optimizer step；本配方是 `custom_loss`（faithful DIS）且 64 样本 / global batch 32 = 每轮 2 步 → 启动即 assert | `validate_skip_actor_forward_only` |
| 不采用 | `--use-rollout-logprobs --get-mismatch-metrics` 保留 forward：还要 `--custom-tis-function-path`，TIS / mismatch 指标只在 `policy_loss_function` 内产生，本配方不调用它 → 无消费者（违反 06 A8） | 同上 |

README 警告的"未用 rollout logprob 时改用 detached training logprob 作 old baseline"只存在于 `policy_loss_function`；本配方走 faithful DIS，不经过那段。`j4_full_step.sh` 是旧 slime 配方（PPO + `--use-kl-loss`），不是 E5 的基线。

## 2. 效率配置下什么不变、什么消失

- **不变（源码层面）**：faithful DIS 的公式、执行分母 `rollout_mask_sums`、每步 `num_rollouts`——behavior logprob 一直取 `batch["rollout_log_probs"]`，当前 logprob 在训练 forward 内重算，从不消费诊断 forward 的 `batch["log_probs"]`；更新边界（微批切分、2 步、零信号跳过、发布门控）；I18 路由来源——训练 forward/backward 仍回放路由 tape，`replay_fill` / `replay_consume{train_step}` / `replay_exhausted` 照发。优势张量只是从 `rollout_log_probs` 取形状，`kl_coef=0` 下逐 token 优势 = 样本 reward，数值不变（**待等价探针复跑证实**，见 §4）。
- **消失**：rh2 事件 `logprob_compare` 与 `replay_consume{phase=logprob_forward}`；miles 指标 `rollout/log_probs`、`perf/log_probs_time`、`perf/log_probs_tflops`。两份配置都不产生 miles 的 mismatch / TIS 指标，本配方唯一的同版本对拍就是 `logprob_compare`。
- **消费者现在会误报**：G1 judge 把 logprob 检查记 MISSING，并以"无 logprob_forward 消费事件"判路由链失败（`experiments/miles_gpu_spike/g1_acceptance.py`）；`run_report` 记 `no_logprob_compare_events`。两者都要加第三态 **"按配置不可用"**，与"证据丢失"和"零"分开。
- **副作用**：非末级 PP stage 会算没人用的优势（无害，CPU 探针须覆盖）；`--log-correct-samples` 会 KeyError；learner 更快 → 更早发布 → staleness 与 drop 的分布变化，两份配置比较看分布而不是逐曲线。

## 3. I20 测量覆盖（已有 producer 与缺口）

| 项 | 已有 | 缺口 | 最小补法 |
| --- | --- | --- | --- |
| 合格组 / 有效评分（含可信 0） | 组事件、bringup 评分块、可信 0 规则 | 无每小时 / 每 GPU 小时速率 | 只在 `run_report` 聚合 |
| 模型 / 环境 / 评分等待 | limiter 等待、19 段生命周期、`bootstrap_seconds` | 逐轮 SGLang `server_timing` 有存无聚合；`ModelCallAttempt` 区间字段只有 schema | `run_report` 聚合；区间字段按需再填 |
| prefill / decode / cache | SGLang `/metrics` 常开但没人抓 | 无引擎级数据；miles `rollout/prefix_cache_hit_rate` 在 rh2 路径恒 0 | 作业级抓取器；标记该指标无效 |
| 发布与重算 | `weight_update`、发布时 flush | 重算量 | 从事件时间戳重建 learner 时间线（不加 producer） |
| 训练显存 | dmon 5 s、各 GPU 混成一个峰值 | 无逐 GPU、逐阶段峰值 | dmon 按 GPU 1 s；**一处** fork patch 记逐阶段峰值 |
| 分行重复输入 | `turn_coverage`、`seq_lens` | 真实共享前缀 token | 用现有 rollout dump 离线算 |
| CPU / RAM / I/O | 关停时一次峰值 RSS | adapter / owner 事件循环延迟（E3 交接）、宿主时间序列 | bringup 心跳；vmstat / iostat / docker stats 采样 |

两条测量提醒：`train_wait` 量的是两次 train 之间的一切（drain、发布、保存、摘要），不是纯等数据；省下的 forward 只有在 learner 处于关键路径时才变成每小时更多合格组，rollout-bound 时只会变成更长的 drain 等待。

## 4. 交付与验收

**交付**：本 Brief；`launch.sh` 显式 profile 开关（`diagnostic` | `efficiency`，**无默认值**，效率档只多那一个开关）；rh2 检查函数（照 `eval_wiring.py` 的样子）把 profile 写进启动证据，效率档拒绝 PPO / OPD / KL / TIS / keep-old-actor 等不支持开关；`run_report` 三态 + 速率 + learner 时间线；G1 judge 只接受诊断档；bringup 事件循环心跳；逐阶段训练显存的单个 fork patch（唯一 fork 改动，按 patch 存档约定）；作业级采样器与 GPU 清单条目。

**无 GPU 即可验收**：在当前 fork HEAD 复跑并扩展 2026-09-06 的等价探针（覆盖非末级 PP、2 步、调用 / 事件序列）；解析器反例（`--skip-actor-forward-only` 必须失败）；launch dry-run 证明两份参数表恰差一个开关；报告 / judge 的三态测试；心跳与 fork 事件形状测试。

**放进既定 GPU 作业**：首次完整运行用诊断档收齐整张清单并过 G1 parity（≤ 0.05）；同配置同题的一小段效率档（可与冷恢复 R1 合并）；效率档正式启用的输入先写进 Brief，数值阈值进作业计划。

## 5. 风险与待确认

- 仅源码：数值等价（旧探针跑在旧 fork）、cache-hit 指标恒 0、非末级 stage 的多余优势。
- 要真实作业或本地没有的代码：forward-only 是否改 MoE router 状态（本地无 Megatron 源）；计时器不与 GPU 同步，`perf/log_probs_time` 可能偏低；pinned SGLang 实际返回哪些 `meta_info` 键与 `/metrics` 名（本地运行记录里没有 `server_timing`）；forward 实际成本、逐阶段显存、循环延迟。
- 流程：消费者改动落地前跑效率档会得到假 MISSING / FAIL；`launch.sh` 是草稿，profile 要写成未来正式启动器能复用的形态；rollout debug dump 两次运行要一致；不建议 `--save-debug-event-data`（有 checkpoint 副作用）；`bringup.py` / `generate.py` 与 B 共享，按 B 当前工作顺序落地。

## 6. 不做的事

不新建调度 / 观测平台；不改 faithful DIS、组分母、更新边界、I18 来源；不把效率档设为默认；不在无测量数据时宣称收益。无新增用户决策；效率档何时正式启用以作业计划里的实测数字为依据。

## 7. Codex 设计复核（2026-09-25）

**可实施。** 对照当前 fork 后，效率档只加 `--use-rollout-logprobs` 的结论成立。原样复跑既有 CPU 探针，受测优势 / loss / 梯度等价，额外 forward 与对拍消失、训练仍走 replay backward；这不是两步、多 PP 或 GPU 路由状态的完整验收。结果及具体约束见[复核报告 §4](review_next_slices_20260924/README.md)。

- 三态由有效 flags 与真实 producer 给出：诊断缺事件仍是缺证据；效率档关闭才是按配置不可用，不借此宣称 G1 parity 已通过，训练 replay 的核对仍保留。
- 训练 reward 列已做组内归一化，不能将公式说明读成原始二值分数直接广播。本文两步与非末级 PP 验收继续保留。
- 不新增强制 profile 闸门或第二套配置事实来源；旧 launch 脚本不替代未来八卡作业方案。先交付配置 / 报告 / 清单，额外 producer 按缺口分片，未知量不由时间戳猜出。

## 7. 实施记录（2026-09-25；sub-agent 实施、Claude 审阅与接线；Codex 复核 §4 四条收紧已落实）

- **已实施**（本地 `runs/decision_package_20260924/e5_impl/README.md` 有 file:line 全表）：
  - `rh2/src/repoharness2/adapters/miles/forward_profile.py`（新，纯标准库）：从**最终 args** 推导（token 流 `derive_from_tokens` / 进程内 `derive_from_namespace`）`profile`（diagnostic / efficiency / unsupported）、`extra_logprob_forward`、三个开关值、`unavailable_observations`、`unsupported_reasons`；效率档 18 条 fail-closed 守卫（PPO / OPD / KL / TIS / keep-old-actor / 读额外 forward 输出的开关）；`--skip-actor-forward-only` 与 `--get-mismatch-metrics` 两档都 unsupported；扫描 custom config YAML（文件或 `base64:` 内联）是否改写追踪键；消费者用 `interpret_recorded` 按同一函数重算核对。
  - `launch.sh`：旋钮 `RH2_TRAIN_FORWARD_PROFILE` **非强制、缺省 diagnostic**（与 §4 "无默认值"的偏离，按 Codex 收紧 3），efficiency 只追加 `--use-rollout-logprobs`；P12 闸对提交给 `train_async.py` 的同一组 token 推导并与旋钮比对，不符或 unsupported 在 Ray 前红；`run_manifest.json` 写推导块，旋钮字符串不进证据。
  - `bringup.py`（Claude 接线）：`derive_from_namespace(args)` 的结果进 `startup_evidence.json`（`forward_profile` 键），**只记录不拒绝**（P12 已在前面挡）。`repoharness2.adapters.miles` 包的 `__init__` 导入时拉 `miles`，没有 miles 的 CPU 进程（启动期测试）按文件路径加载同一纯模块（与 judge / launch 同法）；真实启动纵切测试断言该块落盘且可按同一函数重算。
  - `run_report.py`：logprob 相关三态 present / unavailable_by_configuration / missing + 矛盾态 contradicts_configuration（只有配置已知且额外 forward 确认关闭、且确实无事件才记"按配置不可用"；诊断档缺事件仍是 `no_logprob_compare_events`，该面仍 partial）；每小时 / 每 GPU 小时速率（合格组、applied step、有效评分含可信 0 分）；learner 时间线（drain / train / step / update / publish）；重算 token 数、cache 命中、逐阶段显存明确 `not_collected`。
  - `g1_acceptance.py`：新检查 `forward_profile_evidence`（块缺失 MISSING、无效或 unsupported FAIL）；效率档 logprob 两项 NOT_APPLICABLE（detail 以 `unavailable_by_configuration` 开头）；R3 链仍逐 rank 要求 fill / 每步 train_step 消费 / exhausted，只免 logprob_forward 一环；效率档出现 logprob 事件即 FAIL；效率档总判定最多 NOT_APPLICABLE、verdict 新增 `g1_parity`，judge 退出码非零。
  - 测试：`tests/adapters_miles/test_e5_{forward_profile,run_report,g1_profile}.py`（61 双 lane + 3 integration_base）；`integration_base_manifest.json` 计数同步。
- **CPU 等价探针**（`runs/decision_package_20260924/e5_impl/e5_cpu_equivalence_probe.*`，`all_checks_pass=true`）：09-06 探针在当前 fork 复跑一致；训练 reward 列是组内归一化后的 ±0.935（不是原始 0/1）；两步 + 末级 / 非末级 PP 的真实控制流（AST 提取的 `train_actor` 等）下两档每步 loss / 梯度 / 参数逐位相同，事件序列恰差 `replay_consume{logprob_forward}` 与 `logprob_compare` 两项；诊断档额外 forward 输出全换 NaN 训练量不变；负对照能检出差别；launch dry-run 两份参数表恰差一个 token。替身边界：GPU 数值、Megatron forward-only 对 MoE router 状态、真实时长与显存、CP/TP>1。
- **偏离与已知行为**：旋钮有缺省（见上）；效率档会让 launch 整体非零退出（judge NOT_APPLICABLE 非零，post-run 打印原因）——是否给 NOT_APPLICABLE 独立退出码留后续；E5 之前的旧证据目录重跑 judge 得 INCOMPLETE（缺 `forward_profile` 块），历史证据不回写；不做 argparse 缩写检测（依赖 Megatron 解析器 `allow_abbrev=False`，本机无 Megatron 源码，间接证据）。
- **未做**：逐阶段显存 fork patch、bringup 心跳、作业级采样器、`server_timing` 汇总（按 Codex 收紧 4 分别按缺口落地）。GPU 核验清单 F1–F8 已并入 [batch5 GPU 核验清单 §6](../batch5_launch_eval_20260919/gpu_verification_checklist_20260920.md)。

## 8. Codex 实施复核（2026-09-25）

**配置、CPU 等价与 G1 三态主干通过；评分速率 EF1 / P2 待修，本机部分尚未全部收口。** [完整报告、反例与停止条件](review_followup_e5_20260925/README.md)。原作者 CPU 探针在独立输出目录复跑 `all_checks_pass=true`，真实 GPU / router 内部状态仍留 F1–F8。

- 正式 miles 包装直接调用 `rh2_custom_generate`，绕过旧 `bringup.generate` 的评分摘要 writer。新报告把只有 shutdown 行的事件文件当成有评分观测，输出有效评分 0 / 小时。探针中两个 1 / 0 结果均未触发摘要 writer；关停前未知，关停后错误变零。
- 在真实每 execution 审计出口补摘要，并按 attempt 身份和 train/eval 平面聚合；无评分观测保持未知、部分观测说明覆盖量，不按训练行或重评分重复计数。也可暂标未采集，但不能宣称已经提供该速率。沿实际 miles 包装验证成功、可信零分、infra、eval 与仅生命周期行即可，无需 GPU。
- P12 是新增配方兼容预检，应如实记录配置拒绝变化；不是新增训练样本准入规则。效率档 G1 非零退出与未来 launcher 的衔接仍按已声明分期。

## 8. Codex 聚焦复核 EF1 的修订（2026-09-25）：评分摘要走每次 execution 的审计出口

- **问题**（[review_followup_e5 §1](review_followup_e5_20260925/README.md)）：正式 miles 路径（`Rh2MilesGenerateFn` → `rh2_custom_generate`）不经旧 `bringup.record_event`，带 `grading` 块的 `bringup_events` 行只由旧包装写；`_hourly_rates` 只判 `if bringup:`，两条 shutdown 生命周期行就让"有效评分"从未知变成 0 / 小时，且没有缺证据 reason。
- **修法**：`write_execution_audit_record` 新增 `grading` 摘要块（`finalized.grading_report` 的 report_id / outcome / failure_category / reward / timings，与旧 record_event 同形；未 finalize = None）——这是每次 execution 都经过的审计出口。`run_report` 的评分总体（reward facet）、有效评分速率、评分分段耗时改为共用 `_grading_records`：唯一来源 = execution audit 的 grading 块（按 `physical_attempt_id` 去重取最后一条，重评分 / 多训练行不重复计数；评测 attempt 单列不计）；旧 bringup 块只在没有任何带 `grading` 键的 audit 行时作回退（E5 之前的证据）；两者都没有 → `effective_gradings=None` + `no_grading_records`，生命周期行不产生分母；部分 execution 无评分块 → `grading_coverage` 与 `partial_grading_coverage` reason，不把部分观察当总体。交付记录 / eligibility 分布仍只来自 bringup_events（没有就是 None）。
- **验收**（`test_e5_run_report.py` +4，双 lane）：真实 `RolloutOrchestrator` + `write_execution_audit_record`（假 Docker / driver / 模型，评分替身给 resolved 与 infra 两种真实契约形态）→ `load_run_inputs` → 报告：resolved 1、infra 归 reward_unknown、来源 execution_audit、无 bringup 时交付记录为 None；只有 shutdown 两行 + 无 grading 键的旧 audit → 未知（速率、评分总体、分段耗时三处）；评测 / infra / 重复 execution 记录 / 无评分块的 aborted 各自单列，覆盖 3/4 有 reason；audit 与旧 bringup 块同时在场以 audit 为准。既有 `test_run_report` 的"只给 audit = 无法知道"口径同步改为"评分总体来自 audit，交付记录仍未知"。
- **未做 / 提醒**：train / eval 平面按 audit 的 `evaluation` 块分；`startup_evidence.json` 的进程内档位块仍只由 launch 的 `run_manifest.json` 消费（未来正式 launcher 接同一证据）。Codex §4 的复杂度提醒（`save_debug_train_data` 等纯观测不足不宜一概扩成配置拒绝、少堆 YAML 关键词扫描）记为后续收敛项，本轮未改守卫。
