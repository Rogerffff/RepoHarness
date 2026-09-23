# MiMo-V2.6 RL 直播：首次完整巡检与理解记录

调查日期：2026-09-17。主数值快照从 **02:24:38 UTC / 10:24:38 新加坡、北京时间**开始采集；浏览器巡检从约 10:21 开始。作者：Codex。性质：公开事实整理、机制推断与研究建议，不是项目训练配方定案。

**最重要的判断：这次公开最有价值的，是把大规模 agentic RL 的学习、采样、评分、版本陈旧、数据消费和恢复放在同一个观察窗口。当前证据支持“混合任务、多 harness、组内评分、异步采样、带裁剪的策略梯度训练”；还不足以确认具体采用 GRPO、RLOO 或可训练价值网络，也没有公开这些选择的受控消融。**

“首次有模型团队公开大规模 RL 全过程”是一个历史优先性判断，本次调查没有核实。可以确认其公开程度罕见而有用；不能把公开面板等同于全部内部指标、完整算法或完整可复现训练过程。

阅读入口：

- [本次全部 2,067 个公开标签与末步数值](metric_catalog.md)
- [25 个匿名数据源、23 个 harness 标签的完整对照](source_and_harness.md)
- [逐步训练、离线评测与重启事件](step_history.md)
- [全部逐步数值：Pro](snapshots/20260917T022438Z/pro_series_merged.json)、[Flash](snapshots/20260917T022438Z/flash_series_merged.json)
- [每条指标的首末值、范围、有效点数](metrics_summary.json)、[采集来源与 SHA-256](snapshots/20260917T022438Z/manifest.json)、[核验结果](verification.json)
- [Computer use 覆盖与读数规则](browser_audit.md)

## 1. 覆盖范围和证据层级

按用户要求，先用 computer use 检查 [Overview](https://mimo.xiaomi.com/rl/#overview)、[Metrics](https://mimo.xiaomi.com/rl/#metrics)、[About](https://mimo.xiaomi.com/rl/#about)，通过页面搜索 `/.*/` 和逐批展开按钮枚举所有标签，再逐类阅读指标与重点子页。About 目前只有直播介绍，没有算法配方。

为避免只记下图上四舍五入的数值，随后保存了页面实际使用的公开 JS 和只读 JSON 接口。端点来自该页面的 `js/app.js`，没有猜测私有 API。两次 run 采集期间版本均稳定：Pro `3-5513.12.6.11`，Flash `3-5513.17.3.16`。

覆盖量为：**Pro 2,019 条序列，Flash 2,050 条序列，并集 2,067 个标签，共 51,702 个非空数值点**。Computer use 展开的完整标签清单与 JSON 并集逐字符摘要一致：长度 94,156，FNV-1a `67ad9a49`。61 份原始文件的 SHA-256 已核对。

本文把证据分为三类：

| 层级 | 含义 | 示例 |
| --- | --- | --- |
| 直接事实 | 官方页面、字段定义、原始数值或前端计算可直接支持 | batch=1,568×16；`actor/lr=3e-6`；费用按固定费率计算 |
| 有依据的推断 | 多条观测相互支持，但实现未公开 | 组相对、近零和的 advantage 处理；`signed` 看起来在保持总量的同时改变局部分配 |
| 尚未确定 | 缺少定义、代码、实验设计或对照 | GRPO/RLOO；critic 架构；grader 模型；真实数据集、harness 名称；各机制净收益 |

用户转述的官方发言作为声明记录：约 2B tokens/step、1,568 prompts×16 rollouts、fully async、多任务多 harness、test-case/rubric rewards 和 agentic in-group credit assignment。尝试打开对应 X 原帖时返回 403，未把搜索聚合站的转述或观众推测当作新增的一手算法证据。

## 2. 到底在做哪些实验

**公开的是两个仍在运行的综合训练 run：MiMo-V2.6-Pro 和 MiMo-V2.6-Flash。** 两者均混合 code、general、cyber、visual、chat 五类来源，并混合多个 harness。公开页面没有“换一种算法、固定其余条件”的实验矩阵。

| 项目 | Pro | Flash |
| --- | ---: | ---: |
| run 起点 UTC | 09-15 10:32:19 | 09-15 15:16:29 |
| 当前主曲线保留的已完成 step | 1–12 | 1–15 |
| 每步目标 prompts × rollouts | 1,568 × 16 | 1,568 × 16 |
| 每步 `train/verdicts/trained` | 25,088 | 25,088 |
| 最新步训练 tokens | 2.3281B | 2.68554B |
| 当前主曲线累计训练 tokens | 25.0827B | 35.2043B |
| 当前主曲线累计训练序列 | 301,056 | 376,320 |
| sampled `avg@n`：step 1 → 末步 | 0.564662 → 0.608784 | 0.513693 → 0.596286 |
| 对应提升 | +4.4122 个百分点 | +8.2593 个百分点 |
| 末步实际训练轨迹 mean reward | 0.581967 | 0.563659 |
| 最新公开 DeepSWE v1.1，mini-swe-agent，avg@3 | 63.72，step 10 | 60.77，step 12 |
| 快照费用显示值，USD | 819,612 | 361,128 |
| restart 事件数 | 5 | 2 |

来源：[Pro 状态快照](snapshots/20260917T022438Z/pro_status_before.json)、[Flash 状态快照](snapshots/20260917T022438Z/flash_status_before.json)、[官方评测数据](https://mimo.xiaomi.com/rl/api/benchmarks)。这些是不同 run、不同完成步数和不同评测 checkpoint，不能当作同预算算法对照。step 1 也不是公开的未训练 step 0 基座。

两条 run 内还可见这些**并存机制**：

- **25 个匿名数据源**，各自有 accepted、target、held、carryover 等记录。
- **23 个匿名 harness 标签**：A–F、H–U，以及 A-pw、D-pw、G-pw。不能据此认定有 23 套完全独立软件，也不能把 `pw` 擅自展开为 Playwright 等名称。
- 组内评分有 `select_v4`、`select_v4_nogold`、`off` 三条路由。它们是同一个 run 内的处理分支；没有证据表明这是随机分组的消融。
- 组内评分按 harness-A/B/C/D 另有细分；其他 harness 没有相同公开切片，不等于没有评分。
- 唯一公开的命名离线 benchmark 是 **DeepSWE v1.1 / mini-swe-agent / avg@3**。当前面板没有 Terminal-Bench、视觉或聊天的独立 held-out 评测曲线。

## 3. 数据混合与 Harness：工程上最直观的一组信息

最新已完成步的页面推导构成如下：

| 类别 | 来源数 | Pro prompts / share | Flash prompts / share |
| --- | ---: | ---: | ---: |
| code | 11 | 1,067 / 67.28% | 1,057 / 67.24% |
| general | 4 | 190 / 11.98% | 194 / 12.34% |
| cyber | 1 | 76 / 4.79% | 65 / 4.13% |
| visual | 6 | 206 / 12.99% | 210 / 13.36% |
| chat | 3 | 47 / 2.96% | 46 / 2.93% |

**约三分之二 prompts 来自 code，但不能把它读成三分之二算力来自 code。** 长度、环境调用和评分成本差异很大；例如 Flash 的 `code/dataset-yfch` 平均 response 长度为 440,762，部分 chat 来源只有约 2,600–4,500。

这里有两个需要保留的统计边界：

1. 页面不是直接公布每条被训练样本的来源清单，而是用 `held(t−1)+accepted(t)−held(t)` 推导 prompts 构成。若总数与目标相差不超过 5%，直接显示该结果；否则采用 carryover 加 fresh accepts 按比例分配。因此 Pro 总数是 **1,586**，Flash 是 **1,572**，并不严格等于 1,568。网页特别提示重启后的构成可能是近似值。公式没有完整消费 expired 信息，不能拿它当精确配比账本。
2. harness 构成图合计 Pro **22,453**、Flash **22,410** rollouts，而 `train/verdicts/trained` 两者均为 **25,088**。原始 `trained_rollout_share` 又与构成图 share 分母不同；算术上它接近按非零 advantage 行数归一。公开资料未解释全部差额，不应先断言样本丢失或自动补齐归属。

以上来源与计算见 [构成表](source_and_harness.md) 和 [网页构成计算](sources/js/app.js)，全部匿名数据源及 harness 名称已保留。

## 4. 能确认什么算法，不能确认什么

### 4.1 已公开的优化信息

| 证据 | 读数 / 定义 | 可支持的结论 |
| --- | --- | --- |
| `actor/pg_loss` | 官方定义为 clipped policy-gradient objective | 使用带裁剪的策略梯度目标 |
| `actor/clip_low`、`clip_high` | 全部公开步均为 0.20、0.27 | 使用了不对称的裁剪相关参数；精确公式仍未公开 |
| `actor/lr` | 全部公开步均为 3e-6 | 本观察窗口内学习率恒定 |
| `training/actor_optimizer_steps`、`actor/updated_iter` | 每步均为 1 | 每个公开 step 记录一次 actor optimizer step；不能反推 microbatch/gradient accumulation 数 |
| `actor/pg_tis_clipfrac` 及正负 advantage × 高低边界切片 | 末步 0.000254096 / 0.000181866 | 有与 TIS 命名一致的重要性采样裁剪诊断；阈值和实现未公开 |
| `actor/pg_clipfrac`、`actor/ppo_kl` | 两 run 全部公开点均为 0 | 这些字段当前没有显示非零值；不能把字段名当成具体 PPO/GRPO 配方证明 |
| `actor/update_successful` | 每步 1；skip 字段每步 0 | 已完成步骤未记录 optimizer skip；不能因此否认 run 中途发生过故障 |

官方字段解释来自 [api/runs](https://mimo.xiaomi.com/rl/api/runs)；冻结副本在 [runs.json](snapshots/20260917T022438Z/runs.json)。TIS 通常指截断重要性采样，用于处理采样分布与训练分布的差异；这里属于名称支持的解释，不能借此补出作者没有公开的目标函数。

### 4.2 `critic/*` 并不证明存在可训练 critic

全部 324 个 `critic/*` 标签仅由四组统计组成：`advantages`、`returns`、`rewards`、`score` 的 min/mean/max，再按全局、agentic、25 个数据源重复。

本次逐点核对发现：

- 在两个 run 的全部公开点、全部数据源上，`returns/*` 与对应 `advantages/*` **完全相同**。
- `rewards/*` 与对应 `score/*` **完全相同**。
- 没有公开 `value_loss`、value predictions、explained variance、critic optimizer、critic learning rate 等价值网络训练诊断。

这更像一个沿用 `critic` 命名空间记录 RL 统计的实现，**仍不是“确定没有 critic”的证据**。训练代码、配置和未公开指标都可能提供额外信息。

组内 `select_adv_group_sum_abs_mean` 约为 1e-16，各 harness 的 `advantage_mean` 多接近 1e-8 或更小，支持存在组中心化/近零和处理。但是 GRPO、RLOO、重排后的组相对 advantage 都可能产生这种现象，无法由这些汇总量区分。

如果只比较未做标准差归一化和额外重写的组均值 baseline 与 RLOO，同一组内 advantage 只差 `n/(n−1)` 的比例；n=16 时为 16/15。需要 baseline 公式或代码才能辨认。**截至本次快照，不应给 MiMo 贴上已经确认的 GRPO、RLOO、PPO+GAE 或 Le Critique 标签。**

### 4.3 最合理的机制描述

将直接证据拼起来，可以描述为：多来源任务配额 → 每题多条 rollout → 多 harness 环境执行 → task reward 与可选组内 judge/selection → advantage 构造、重写及局部修正 → 混合不同策略版本的数据更新 actor。

这是依据观测形成的流程概括，**不是恢复出的源码调用顺序**。尚未公开：reward/advantage 完整公式、token mask、归一化维度、组不完整时怎么办、importance ratio 截断规则、参考策略 KL 正则、entropy 系数，以及每条轨迹的策略版本如何传播。

## 5. `agentic in-group credit assignment`：最值得继续跟进的部分

`penalty` 有 535 个标签，其中 **523 个属于 `stage_credit_group`**。其结构包括全局 78、harness 切片 296、路由 3、`select_v4` 74、`select_v4_nogold` 72。

| 功能面 | 公开标签线索 | 当前可以说什么 |
| --- | --- | --- |
| 组路由 | `routed/off`、`select_v4`、`select_v4_nogold` | 不是每个组都走同一种 judge；gold/no-gold 是名称体现的区分 |
| judge 生命周期 | attempted/judged、failed_pod/select、pending、pool_in_flight、expired_unjudged、judged_after_drop | 评分本身是有队列、失败和迟到结果的异步工作负载 |
| 参考与测试检查 | `select_above_gold_share`、`impl_over_gold_mean`、`pass_new_tests_rate`、`r3_gold_fails`、`regression_flagged` | 至少在记录 gold 对照、新测试、回归检查相关信息；gold 的具体使用方式未公开 |
| 评分与排序 | `score_A/B/E/P/S_mean`、tier H/T1/T2/T3、rank_invalid、rank_score_conflict、tier_mismatch | 不只有终局单一 reward；A/B/E/P/S 的维度定义和 tier 规则未知 |
| 过程/作弊信号 | `hack_attempt`、`hack_attempt_ge_min`、`hack_exposed_not_relied`、`process_severe`、`probe_disagree_rate` | 在区分过程异常或可疑行为；字段不能直接当作人工确认的作弊率 |
| advantage 处理 | `select_tq_adv_rows_rewritten`、`select_adv_group_sum_abs_mean`、`select_factor_mean`、`renorm_k_mean`、`renorm_capped_rate` | 有明确、非零的 advantage 重写记录和重新归一化诊断 |

**它已经超过“每条轨迹只给一个原始测试通过分数”的简单记录方式。** 但面板未公开 judge 输入、prompt、具体评分规则、行与 token 的对应关系，不能直接宣称实现了可靠的逐动作因果归因。

末步的重点数值：

| `penalty/stage_credit_group/` 下的指标 | Pro s12 | Flash s15 |
| --- | ---: | ---: |
| `groups_total` | 1,788 | 1,504 |
| routed off / select_v4 / select_v4_nogold | 872 / 406 / 510 | 706 / 412 / 386 |
| `groups_attempted` / `groups_judged` | 880 / 847 | 686 / 646 |
| `end2end_success_rate` | 96.25% | 94.17% |
| `groups_failed_pod` / `groups_failed_select` | 12 / 21 | 13 / 23 |
| `groups_judged_after_drop` | 0 | 4 |
| `judge_pending` / `judge_pool_in_flight` | 77 / 77 | 113 / 113 |
| `time_total_sec_mean` | 554.024 秒 | 576.642 秒 |
| `time_total_sec_max` | 3,468.81 秒 | 7,243.99 秒 |
| `select_tq_adv_rows_rewritten` | 13,541 | 10,316 |
| `select_adv_group_sum_abs_mean` | 1.27476e-16 | 1.2316e-16 |
| `select_pass_new_tests_rate` | 75.48% | 71.57% |
| `select_probe_disagree_rate` | 62.62% | 59.74% |
| `select_hack_attempt_rate` | 41.15% | 42.66% |
| `select_hack_attempt_ge_min_rate` | 4.53% | 6.12% |
| `select_renorm_k_mean` | 1.19345 | 1.17504 |

来源：[组内评分页面](https://mimo.xiaomi.com/rl/#metrics/penalty/stage_credit_group)、完整序列与 [指标目录](metric_catalog.md)。这里的 success 是 **judge 处理成功率**，不能冒充模型解题成功率。`hack_attempt_rate` 的筛查规则和分母未知，不能写成“40% 的模型轨迹在作弊”；`probe_disagree_rate` 也不能写成“60% 的 reward 是错的”。

几个反直觉细节说明必须核对活跃性：

- 有 pass1/pass2 两套标签，但全部公开点的 **`judge_pass2_attempts=0`、`time_pass2_sec_mean=0`**。同时 `pass2_success_rate=1`。这个 100% 不能证明第二阶段有效；实际观察到的活跃处理在 pass1/select 路径。
- `select_tq_adv_rows_rewritten` 明显非零，但另一个不带 `select_` 的 `tq_adv_rows_rewritten` 及 `tq_adv_set_tokens` 等字段为零。不能把两套路径混为一谈。
- `penalty/action` 的乘数下界为 1，其余计数为 0；该命名空间在窗口内没有显示实际惩罚。
- `penalty/signed` 有非零 positive/negative hit tokens 和质量增减，`pos_scale` 略大于 1、`neg_scale` 略小于 1，而训练前后正、负 advantage 总和分别相等。**这与“修改局部后恢复总量”的做法一致**，但仍需要源码确认归一化发生在哪一步、作用于哪些 token。

因此，对“把 credit 分给整条轨迹、阶段还是动作”的最诚实回答是：**组内比较与 advantage 重写已有实测；带符号的 token 相关调整有实测；阶段/动作如何定位、是否给每个 token 独立 credit，尚无足够公开信息。**

## 6. 异步、长轨迹和策略陈旧度

`partial/avg_staleness` 的官方定义是采样到训练之间相差的策略版本数。`partial` 下共有 375 个标签，包括 lag 0–9 的份额、token 数、entropy，以及按 lag 分解的训练/推理差异；也有 25 个数据源的平均 lag。

| 末步指标 | Pro s12 | Flash s15 |
| --- | ---: | ---: |
| 平均 policy lag | 0.677916 | 1.87435 |
| agentic 子集平均 lag | 0.689095 | 1.94626 |
| lag=0 的 `frac` | 32.2084% | 15.7042% |
| lag=1 的 `frac` | 67.7916% | 52.7276% |
| lag≥2 的已公开非空 `frac` 之和 | 本步无这些 bucket 的点 | 31.5683% |
| lag≥5 的已公开非空 `frac` 之和 | 本步无这些 bucket 的点 | 15.1730% |
| `code/dataset-yfch` 平均 lag | 0.687739 | **5.4749** |
| 该来源平均 response tokens | 262,637 | **440,762** |

用 `partial/k/frac` 重算加权平均可对应 `avg_staleness`，且 frac 与该 bucket `n_tokens` 归一结果一致；因此更接近 **所记录 token 的版本分布**，不宜称为“有 31.6% 的完整轨迹落后至少两版”。具体 mask/计数对象没有公开。

![按 lag 分桶的份额与 KL](figures/lag_and_kl.png)

同一 Flash s15，`train_infer_diff/new_infer/kl` 从 lag0 的 **0.00317817** 增至 lag9 的 **0.0342927**。全局 KL 为 0.00832682。这个分层结果比“整体平均 KL 不大”更有信息：陈旧尾部与明显更大的差异同时出现。

仍需保留三点：

1. 官方定义是同一 token 的 inference-engine 与 trainer log-probs 差异；既可能含版本差异，也可能含实现/数值差异。它不是参考策略 KL，也不应自动等于纯 policy drift。lag0 已有非零差异就是一个提醒。
2. Pro s9/s10 平均 lag 约 1.82/1.79，重启后的 s11 降至 0.44，s12 回到 0.68。这与恢复过程相关，但不能据此宣布某算法消除了陈旧度；需要控制重启/队列状态后再比较。
3. 官方称 fully async，不等于没有组内等待、不等于每完成一条轨迹便立即训练，也不证明 rollout、judge、trainer 的所有计算完全重叠。`carried`、`pending`、迟到和过期记录表明仍有实际调度依赖。

**真正值得迁移的是分来源、分版本的诊断方法。** 仅比较 trajectories/hour 或一个全局 lag 均值，会掩盖长任务的学习信号来自更旧策略这一事实；反过来，简单丢掉慢任务又可能改变训练分布。

## 7. 学习曲线有没有变好，代价是什么

![学习、长度、陈旧度、时长与评分开销](figures/learning_and_system.png)

### 7.1 有正向变化，但离线评测并不单调

Pro sampled `avg@n` 从 56.47% 到 60.88%，Flash 从 51.37% 到 59.63%。这里的定义是：对本步每个 sampled prompt，计算 n 次尝试的成功比例，再对 prompts 平均。**它不是 best-of-n 的 pass@n，也不是 held-out 准确率。** 数据来源、采样、accept/consume 的变化都会影响它。

实际用于训练的 reward 均值为 Pro 0.552211→0.581967，Flash 0.516717→0.563659；它与 sampled `avg@n` 的样本总体、权重、评分含义不同，不能预期两条曲线完全一致。

离线 DeepSWE：Pro step1 的 58.41 到 step10 的 63.72，增加 5.31 个百分点；Flash step1 的 48.67 到 step12 的 60.77，增加 12.10 个百分点。中间有明显波动，例如 Flash s10→s11→s12 为 **60.18→54.13→60.77**。公开资料未给题目级配对结果、方差、置信区间或完整数据隔离说明，不能把单步涨跌都解释成真实能力变化，也不能据此证明未见任务上的稳定 scaling law。

### 7.2 轨迹显著变长

| 指标 | Pro：step1 → 末步 | Flash：step1 → 末步 |
| --- | ---: | ---: |
| 平均 response tokens | 68,078 → 88,991（约 +31%） | 67,463 → 103,314（约 +53%） |
| 平均总 context tokens | 72,178 → 93,077 | 71,634 → 107,496 |
| 平均 agent turns | 47.47 → 55.04 | 47.31 → 57.02 |
| 每步训练 tokens | 1.80052B → 2.32810B | 1.78967B → 2.68554B |

这说明即使固定 1,568×16，**每步计算工作量也不是固定的**。模型可能在进行更多搜索、验证，也可能出现冗长或无效工具循环；仅凭长度与成功率同涨无法区分，必须看轨迹、成功/失败条件长度及等预算评测。

Flash 历史 `ctx_response_length/max` 达 2.23144M，`ctx_total_length/max` 达 2.23643M。这是面板里的轨迹长度统计，**不能反推出模型支持 2.2M 的单次上下文窗口**；多轮拼接、分段、恢复及计数实现都未公开。

末步 `ctx_total_length/clip_ratio` 约 Pro 0.0080%、Flash 0.0520%。只知道该字段很小；长度 cap、分母和截断语义仍需代码，不能据此否认预算截断对少量长任务的影响。

### 7.3 采样总体和训练总体明显不同

末步 sampled prompts 全失败/全成功比例：Pro 15.15%/24.76%，Flash 15.08%/23.46%；合计约 39.9%/38.5%。训练侧 `passrate_0_ratio + passrate_1_ratio` 仅约 14.6%/13.9%。这与筛选、carryover、来源差异或重写后的训练分布一致，但不能仅凭汇总数证明采用了某篇论文的 dynamic sampling 规则。

`train/verdicts/dropped_zero_adv` 全窗口为 0，训练侧全成功/全失败比例又并非 0，尤其不能直接声称“所有零方差组均被删除”。多种 reward、grader 重排与字段统计阶段都可能影响这里的关系。

## 8. 运行效率、成本和恢复

### 8.1 最新步的成本结构线索

| 指标 | Pro s12 | Flash s15 |
| --- | ---: | ---: |
| `timing_s/step` | 9,063.03 秒 / 151.05 分钟 | 7,552.10 秒 / 125.87 分钟 |
| `timing_s/outer_gen` | 5,251.64 秒 / 87.53 分钟 | 3,510.31 秒 / 58.51 分钟 |
| `timing_s/trainer_ops` | 3,624.12 秒 / 60.40 分钟 | 3,818.61 秒 / 63.64 分钟 |
| 训练 tokens / step wall-clock，派生 | 约 256,879 tokens/s | 约 355,602 tokens/s |
| `env/active` | 23,848 | 37,786 |
| infra failure sequence rate | 0.4535% | 0.5108% |
| `env/possible_leak` | 0 | 0 |
| `train/verdicts/carried` | 19,150 | 20,054 |
| `train/verdicts/rejected` | 19,024 | 15,088 |
| `train/verdicts/expired` | 0 | 753 |
| `train/trace/late_finishes` | 0 | 177 |

上述 tokens/s 是**已记录训练 tokens 的吞吐**，不是 GPU decode throughput；也不能拿它推出算力利用率。各类队列、计数的窗口不全相同，不把它们随意相加成拒绝率。`possible_leak=0` 是检测指标，没有检测器覆盖证明，不等于已证明没有泄漏。

评分平均 9 分钟、最大接近 2 小时，但这些任务并发运行；不能把平均耗时×group 数直接视为 run 增加的墙钟时间。是否位于关键路径、占多少 GPU/CPU/token 和实际美元，仍未公开。

`train/spec_accept_length/request_mean` 末步为 Pro 3.53581、Flash 2.81937；token 加权值约 3.44612/2.79267。命名与 speculative decoding 接受长度一致，但 draft 模型、MTP 配置和净加速比未公开。

### 8.2 费用显示是固定费率模型

公开 status 给出 Pro **$5.71/s = $20,556/h**，Flash **$2.855/s = $10,278/h**。前端用费率乘 `now − run.start`，中途持续跳动；当前总额约 $1.181M。源码直接支持这一点，见 [app.js 的 tick/nav-cost 计算](sources/js/app.js) 与 [status 原始字段](snapshots/20260917T022438Z/pro_status_before.json)。

因此现在能比较的是这个公开计价模型下的用时，**不能把显示额称为已审计实际支出，更不能声称已包含或单列 grader、环境、critic、离线评测的真实成本**。GPU 类型/数量、预留资源、利用率和计费构成没有公开。

若只是演示“达到某离线分数所需成本”的读法：首次公开 DeepSWE≥60 的点，Pro 是 s4=60.47，Flash 是 s10=60.18；按公开费率和 checkpoint 完成时间可算费用，原始值在 [逐步表](step_history.md)。但不同基座、架构、初始分数、评测波动和未拆分成本，使其不能成为公平的算法效率结论。

### 8.3 重启会改变我们看到的有效进度

公告明确指出一次 Pro 重启与某节点 VRAM 问题有关。不能把全部 5 次 Pro restart 都归因为该原因。

Flash 在快照前的事件流记录过 s16 和 s17，随后于 **09-17 02:06:43 UTC** 重启；当前主曲线、累计 tokens 和 trained samples 却只覆盖到 s15，页面继续显示下一轮 s16。**这是进度回退/曲线重建的直接观测**；具体 checkpoint 恢复策略、参数是否回滚、数据是否重放，公开内容还不能确定。

这解释了为什么不能只按最高见过的 step 号算“完成了多少训练”。当前主曲线累计 tokens / run 起跑至快照的真实时间，Pro 约 174,744 tokens/s、Flash 约 278,317 tokens/s，低于仅按保留步骤时长计算的约 260,349/358,170 tokens/s。这个差额包含重启、启动、当前未完成步骤和未保留进度等影响；不能全部归为纯故障损耗。

`env/total_setup` 随步骤上升并在某些重启后重置，很像进程生命周期累计计数。状态里的 `sandboxes_cum` 不能未经定义就当成独立新建环境总数，本报告不据它推算环境单价。

## 9. 全部 14 类指标应该怎样读

| 主类 | 标签数 | 主要结构 / 用途 | 本次最重要的解读边界 |
| --- | ---: | --- | --- |
| actor | 257 | 全局优化字段；agentic 和 25 来源的 entropy、pg_loss、clip、TIS、ppo_kl | 参数/统计名不能独立鉴定 GRPO/RLOO；零梯度计数无分母，不能推模型规模或冻结策略 |
| critic | 324 | 4 组×3 统计×27 层次 | return=advantage，reward=score；没有价值网络训练直接证据 |
| ctx_prompt_length | 81 | min/mean/max×27 | prompt 的拼接、重用口径没有完整说明 |
| ctx_response_length | 81 | min/mean/max×27 | 官方定义每轨迹生成 tokens；不能把轨迹极值当单次 context limit |
| ctx_total_length | 108 | min/mean/max/clip_ratio×27 | 固定轨迹数仍有变化的 token 工作量 |
| dynsam | 83 | avg@n、turns、measurable、target、passrate、infra；25 来源 accepted step/held/carryover | sampled 成功率不同于 trained reward 与 held-out 评测 |
| env | 15 | active、possible_leak、error、setup；来源切片 | gauge、累计 counter 与失败率不能混用 |
| partial | 375 | 全局/agentic/来源 lag；0–9 分桶、token/entropy/KL/tail | token 分布不等于完整轨迹分布；尾部与来源差异很大 |
| penalty | 535 | action、signed、stage_credit_group | 有的路径活跃、有的只有字段；pass2=100% 同时 attempts=0 |
| perf | 1 | total_num_tokens | 官方定义是本步训练 tokens；没有 FLOPs/MFU/decode 吞吐 |
| timing_s | 3 | step、outer_gen、trainer_ops | 不足以恢复所有服务重叠关系或 grader 关键路径 |
| train | 191 | 23 harness×6、passrate 28、spec 2、trace 13、verdicts 6、adv sums 4 | 消费侧统计与接受池/公开 harness 切片的口径存在差异 |
| train_infer_diff | 11 | 5 个 F(tau)；绝对差 max/mean/std；KL；两类 NLL | F(tau) 精确公式未给，不硬译成某个阈值超限概率 |
| training | 2 | actor_optimizer_steps、global_step | 标记更新步数，不显示 microbatch 或完整训练拓扑 |

目录和全部原始时间序列均已保存。重复的数据源、harness 和 lag 切片逐项纳入数值盘点；正文聚焦可解释机制和影响结论的异常。

## 10. 对观众提出的问题逐项回应

**更多 prompts、更多 rollouts，还是更好的 feedback？** 面板只能证实 B=1,568、n=16 和评分工作负载，不能证实这个分配最优。固定 B×n 也不等于固定预算：轨迹长度会变，组内 judge 可能有非线性成本。应比较固定总资源约束下，到达相同、固定且隔离的评测目标所需时间和成本，连同 rollout、grader、环境、训练、恢复及评测一起计入。

**组内 credit assignment 是否值得？** 已有活跃的评分路由和 advantage 重写，所以这不是仅仅挂了一个概念标签。缺的是同起点、同任务分布、同总预算下：基础 reward、加 group grader、加局部重写各自带来的收益，以及判别错误和拒绝分布。`select_v4` 与 `nogold` 路由的自然差异不能替代这个消融。

**critic/RLOO 与调度的关系？** 观众的限定是正确的：`critic/*` 名称不足以证明 learned critic。独立 value baseline 可以减少依赖 sibling returns 的机会，但若 advantage 或 grader 仍需组内比较，依赖仍存在；增加价值模型也会增加计算和维护成本。

关联论文 [Le Critique](https://arxiv.org/html/2608.16739v1) 的 TETHER 明确混合 LOO 与 token value；其 grouped 设置仍需要 rollout groups。论文实验主要是 4B 模型，作者说明 group-mean 与 value 方法没有严格等算力匹配。这支持“值得实验的设计问题”，不支持“已经证明它比 MiMo 当前方案更省钱”。本次只定向核对其方法、组依赖和限制，不冒充完成独立全文复现。

**吞吐与 policy lag 是否应一起看？** 应该，而且这里已经有足够数据展示原因：Flash code/yfch 的 lag=5.47、长轨迹和高 lag KL 尾部，说明全局平均会漏掉重要来源。还需补齐 per-source 时延分位数、组等待、拒绝/过期、grader 用量和版本处理规则，才能判断是否系统性偏向短任务。

**time/cost to equal held-out performance 能否现在回答？** 只能做描述性粗算。页面已公开的评测名称、checkpoint 点数、固定费率和事件历史是起点，但还缺可比较的实验控制、误差估计、真实成本构成和数据隔离证据。

## 11. 对我们当前 RH2 闭环的参考价值

这是临时研究任务，以下均为建议，不改变现有训练、评分或安全语义。

1. **优先学统计分层。** 把 sampled、accepted/carried、trained、held-out 四层分清；同样把 task failure、infra error、grader failure 和 expired 分开。已有 I19/I20 报告与版本记录可作为落点，先核对事实覆盖，不因看到 2,067 个标签就另建一套监控平台。
2. **把策略版本和长任务来源放在同一张表。** 对真实 CC 多轮轨迹，组均值/成员版本与 token/turn 版本不是同一件事。先观察长轨迹在何处变旧、何时完成评分，再决定需要怎样的异步调度或校正；不要仅为降低均值丢掉慢样本。
3. **先测 grader 的净价值再扩大 grader compute。** 当前 SWE 评分和环境清理已经有明确任务。可先用真实失败、gold 和合法替代解分析“额外评分是否改变排序、能否识别测试漏洞、错杀多少”，再讨论训练 advantage 重写。小米的未公开规则不是我方 reward 变更授权。
4. **训练效果与效率必须联合评测。** 轨迹增长 31%–53% 提醒我们：成功率提高不一定降低完成任务成本。对固定隔离题集同时报告成功率、成功/失败轨迹成本、墙钟和环境/评分开销。
5. **重启历史需要和 checkpoint 进度并列保留。** 不能用一个 global_step 和当前累计数覆盖掉之前真实执行过的工作；也不能把恢复后的低 lag 误读成算法优化。现有运行产物、消费事实和恢复事件要保持可追溯。

## 12. 后续公开材料最需要补哪些信息

| 优先级 | 等待的信息 | 它会解决的问题 |
| --- | --- | --- |
| 高 | advantage 公式、normalization、importance ratio 与 clipping/mask 代码 | 判定 GRPO/RLOO/自定义目标及 off-policy 校正 |
| 高 | grader 模型、prompt、测试生成/执行、gold 使用和反馈可信边界 | 判定 credit assignment 的粒度、可靠性、泄漏与成本 |
| 高 | 分来源/harness 的真实映射、混合调度、组不完整与过期处理 | 判定是否牺牲长任务、哪些能力真正受益 |
| 高 | B/n/grader budget 的等资源消融与固定 held-out 评测 | 回答最优计算分配，区分新机制与多花算力 |
| 中 | 设备数、类型、并行拓扑、利用率及费用计价依据 | 从“tokens 很多”推进到真实计算效率 |
| 中 | 重启/恢复协议与已训练样本重放规则 | 解释 Flash 主曲线回退和实际训练成本 |
| 中 | 指标字典，尤其 A/B/E/P/S、tiers、r1/r2/r3、F(tau)、share 与计数窗口 | 避免指标名字产生的伪确定性 |
| 中 | 更多任务族和 harness 的隔离评测、题目级结果与置信区间 | 判断综合能力、泛化和跨 harness 鲁棒性 |

## 来源与复核方式

核心一手来源为 [直播页面](https://mimo.xiaomi.com/rl/)、[公开配置和字段说明](https://mimo.xiaomi.com/rl/api/runs)、[离线评测](https://mimo.xiaomi.com/rl/api/benchmarks)、[公告](https://mimo.xiaomi.com/rl/api/notices)，以及页面调用的 status/live/tags/series。精确请求 URL、采集时间和 SHA-256 全部在来源 manifest 中；这些在线地址会继续变化，应优先用本次冻结副本复核数值。

[capture_public_data.py](capture_public_data.py) 归档公开接口；[analyze_snapshot.py](analyze_snapshot.py) 只读取冻结数据，生成目录、表和图。正文属于作者分析，不代表 MiMo 官方解释。未修改训练代码或共享执行决定，未启动训练、评测作业或持续监控。
