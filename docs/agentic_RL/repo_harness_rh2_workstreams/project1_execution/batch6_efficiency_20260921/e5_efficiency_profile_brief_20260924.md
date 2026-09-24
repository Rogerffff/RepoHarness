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
