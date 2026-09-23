# MiMo-V2.6 RL：09-19 现场巡检与两次快照对照

本次最有价值的变化不只是评测涨分，而是：**训练中的轨迹负载继续增长；数据源、并行策略和运行状态发生改变；一些总均值的改善实际上伴随分组指标恶化。** 这使公开面板成为研究长程 agent RL 的系统与统计问题的案例，但它仍不是控制变量实验。

## 观测范围与时间基准

- 官方页面：[overview](https://mimo.xiaomi.com/rl/#overview)、[metrics](https://mimo.xiaomi.com/rl/#metrics)、[about](https://mimo.xiaomi.com/rl/#about)。本轮实际使用 computer use 阅读图像、切换面板、检查来源与 harness 组成，再以页面公开接口的冻结数据核对数值。
- 旧完整快照：2026-09-17 02:24:38 UTC，即北京时间/新加坡时间 10:24:38，Pro s12、Flash s15。它早于用户后来提供的 Pro s14 / Flash s17 截图。
- 新完整快照：2026-09-19 05:11 UTC，即 13:11，Pro s23、Flash s30。两次机器快照相隔约 **50.8 小时**。浏览器巡检至 13:30，完成 step 未变，Pro 正在训练 s24；费用时钟继续运行。
- 已归档 **2,077 个不同 tag、100,494 个非空数值点**；Pro 2,029 tags、Flash 2,062 tags。两次快照共同覆盖的历史训练指标未发现数值改写。新增主要是 lag 分桶细分字段，不是新算法说明。
- 图像检查覆盖关键趋势与异常点，并不声称逐张看完 2,077 张图。全部数值对照、UI 路径与缺失处理分别见 [指标全表](metric_changes.md)、[浏览器巡检记录](browser_audit.md)、[核验结果](verification.json)。

## 1. 当前状态：Flash 已停止，Pro 继续运行

| 项目 | Pro | Flash |
| --- | ---: | ---: |
| 完成 step：旧 → 新 | 12 → 23 | 15 → 30 |
| 当前状态 | 继续运行 | stopped，未公布原因 |
| 累计训练 tokens | 25.08B → 52.99B | 35.20B → 81.40B |
| 累计页面费用 | $819,612 → $1,863,299 | $361,128 → $854,045 |
| 累计重启次数 | 5 → 11 | 2 → 5 |
| 每步训练条数 | 25,088 | 25,088 |

新快照合计费用约 **271.7 万美元**，比旧快照增加约 **153.7 万美元**。页面按 Pro $5.71/s、Flash $2.855/s 的固定费率和运行时长计算，不能当作逐项审计的 GPU、环境、grader 账单。

Flash 的 run end 时间为 09-19 10:22:09（UTC+8）。最后完成的是 s30，停止前 feed 还显示 s31 rollout。**stopped 不等于正常收敛、训练失败或预算耗尽**；公开公告未说明停止原因。停止后的 env/active 等卡片仍是末个训练 step 的记录，不代表现在仍有同数量环境运行。

## 2. 评测确有提升，但要对齐 checkpoint 与回填时间

新增 In-house Coding Bench 与 AutomationBench。三组曲线均标注 avg@3；DeepSWE 使用 mini-swe-agent。页面没有给出足以检查统计显著性与训练集重叠的题级结果、置信区间等信息。

| 离线评测 | Pro：旧训练末步现已回填 → 最新已评测 | Flash：旧训练末步现已回填 → 最新已评测 |
| --- | --- | --- |
| DeepSWE v1.1 | s12 65.97 → s18 67.46，+1.49 分 | s15 60.77 → s25 64.90，+4.13 分 |
| In-house Coding | s12 61.64 → s18 63.67，+2.03 分 | s15 58.96 → s25 61.93，+2.97 分 |
| AutomationBench v1.0.6 | s12 48.90 → s16 49.80，+0.90 分 | s15 49.90 → s25 51.60，+1.70 分 |

![已公布离线评测](figures/benchmarks.png)

需要区分两种增量：旧页面当时最新的 Pro DeepSWE 是 s10=63.72，今天显示 s18=67.46，差 3.74 分；但旧快照的模型已训练到 s12，后来回填的 s12 是 65.97。因此不能把整个 3.74 分都算成旧快照之后训练带来的提升。

Flash DeepSWE 的 s16–25 序列为 63.86、58.11、64.01、61.65、63.72、59.59、64.01、61.36、65.78、64.90。局部上下波动很大。s24→25 三项评测同时小幅下降：65.78→64.90、62.28→61.93、52.30→51.60；这值得继续核对，但一个 checkpoint 的下降不足以宣布训练崩溃或饱和。

**可吸收的经验：** 把“训练已经走到哪里”“哪些 checkpoint 已完成评测”“结果何时公开”当作三条时间线。固定任务、harness、推理预算与采样协议后，再解释趋势；既看多个评测，也看完整曲线，不能只选最好的一点。当前缺少 Pro s19–23、Flash s26–30 的离线评测，尤其不能用 s25 的成绩评价 Flash s30 的异常。

## 3. 固定 batch 不等于固定工作量：轨迹在普遍变长

| 指标 | Pro s12 → s23 | Flash s15 → s30 |
| --- | ---: | ---: |
| 每轨迹平均 response tokens | 88,991 → 101,375（+13.9%） | 103,314 → 143,385（+38.8%） |
| 每轨迹平均 prompt+response tokens | 93,077 → 105,501 | 107,496 → 147,751 |
| 每步训练 tokens | 2.328B → 2.639B（+13.4%） | 2.686B → 3.696B（+37.6%） |
| 平均 agent turns | 55.04 → 42.45 | 57.02 → 68.52 |
| trainer wall time / step | 60.4 → 111.7 分钟 | 63.6 → 95.6 分钟 |
| rollout wall time / step | 87.5 → 120.3 分钟 | 58.5 → 107.2 分钟 |
| whole step wall time | 151.1 → 236.3 分钟 | 125.9 → 207.2 分钟 |

![负载、时间与采样组变化](figures/workload_and_system.png)

Flash **25/25 个可比较匿名数据源**的平均 response 长度都高于旧快照；Pro 为 **21/24**。因此，整体变长不能只归因于大类来源权重变化。但来源内部题目也会变，仍不能据此证明同一道题一定写得更长、或模型学会了更好的搜索。

Flash s30 中 code/dataset-yfch 的平均 response 已达 524,848 tokens，cyber 为 342,206；总体平均会遮住这些极长任务。response 最大值一度超过百万，不能直接解释成单次模型请求的 context window；这里记录的是轨迹长度，分段与多轮处理细节未公开。

关于此前讨论的 token/step：官方配置明确把 `perf/total_num_tokens` 描述为 **“tokens trained on this step”**，overview 的 token/step 对应该字段。因此大类口径是该步训练 tokens，不能直接叫该步所有 rollout 的输出总量。更细的 loss mask、prompt/tool token、去重、packing、staleness 过滤前后计数公式仍未公开；不能从字段解释再推出这些细节。

**可吸收的经验：** agent RL 的负载分布会随训练演化。用起跑时的长度和耗时估计总预算可能明显偏低；应同时按 tokens、wall-clock、采样轨迹和环境占用看增长。只比较“训练了多少步”会把后期更昂贵的步骤当成等价工作量。

## 4. 公告揭示三类不同干预，不能合成一条纯学习曲线

以下为 UTC+8 公告时间，不等于底层故障的精确起止时间。

| 公告时间 | 官方披露 | 研究含义 |
| --- | --- | --- |
| 09-17 10:27 | Flash 从 s15 重启；某数据集约 3 小时内的基础设施错误未被正确识别 | 错误分类会影响训练样本；重跑与丢弃成本不能从成功 step 数读出 |
| 09-17 20:20 | Pro 训练集群与 grader 网络连接异常并重启；因 rollout 日志中不良模式，移除 cyber 数据源 | grader 是训练依赖；轨迹审计会触发数据干预，后续分布不再相同 |
| 09-18 11:49 | Pro s17 因 MoE expert 负载不均衡 OOM；调整训练并行策略 | 参数量与总 tokens 相同也不保证显存/吞吐稳定；路由分布和并行方案可能决定可运行性 |

Pro cyber 的来源序列在 s14 后不再报告，数据源构成图从 s15 起为 0。Flash 仍包含 cyber，最新约占 4.08%。不能把不良模式直接翻译成已证实 reward hacking；官方没有公开轨迹例子。

Pro s16→17，tokens 从 2.353B 略降至 2.296B，trainer 时间却从 63.7 增到 105.9 分钟，时间上与并行策略调整相邻。它说明“tokens 没多、训练为何变慢”有系统层解释候选，**不是**该调整造成全部变慢的因果证明。

Pro s22→23 的 env/active 又从 23,419 跃至 37,888，约 +61.8%；同区间有两次重启。不要把后续吞吐与 lag 变化只归于策略本身。

## 5. 最值得学的统计陷阱：总 KL 降了，各 lag 桶内 KL 却都升了

Pro s22→23：

| 指标 | s22 | s23 |
| --- | ---: | ---: |
| 平均 policy lag | 1.29452 | 0.129428 |
| 总 inference/trainer KL | 0.00911571 | 0.00382564 |
| lag 0 桶占比 | 19.8654% | 94.7190% |
| lag 0 桶内 KL | 0.00262771 | 0.00291956 |
| lag 1 桶内 KL | 0.00660189 | 0.01422960 |
| lag 2 桶内 KL | 0.01469670 | 0.01992730 |

`partial/k/frac` 在末步可由该桶 `n_tokens / 各桶 n_tokens 总和` 复核，因此此处是日志的 token 桶权重，不冒充轨迹数量占比。

**直观解释：** s23 绝大多数权重落到原本 KL 更低的 lag 0 桶，即使 lag 0、1、2 各自变差，总均值仍能下降。这是类似 Simpson 悖论的组成效应。它与该区间重启和环境规模变化相容，不能只凭总 KL 下降 58% 就宣布训练/推理数值一致性改善。

![lag 条件指标与 penalty](figures/lag_and_penalty.png)

Flash s30 的 lag 0/1/2 占比分别为 15.59% / 49.63% / 34.77%，各桶 KL 为 0.00337 / 0.00838 / 0.01692；较旧桶的偏差明显更大，但桶内任务组成不同，不能当作控制其他因素后的 lag 因果效应。

同版本 lag 0 的 KL 也不是 0，说明总差异不能全用 policy lag 解释；数值精度、引擎计算路径及统计定义都是待核查因素。公开资料未给出足以做精确分解的 mask 与归一化公式。

**可吸收的经验：** 看异步 RL 时，至少联看 lag 的分布、各桶 KL、同版本 KL、重启位置、任务长度和吞吐。平均 lag 低不自动等于成本效率高；队列刚重建时可能暂时变“新”，随后又积累长尾。

## 6. Flash 最后一步是异常组合，不能被平均 reward 掩盖

| Flash 指标 | s29 | s30 |
| --- | ---: | ---: |
| 平均 response tokens | 126,834 | 143,385 |
| 训练 tokens | 3.269B | 3.696B |
| clipped policy-gradient objective | 0.0117151 | 0.0261328 |
| inference/trainer KL | 0.00603871 | 0.0105611 |
| signed/neg_hit_tokens | 2,277,100 | 25,829,000 |
| signed/neg_mass_added | 1,086,330 | 28,902,700 |
| signed/neg_scale | 0.995011 | 0.895555 |
| context clip ratio | 0.0561% | 0.2239% |
| dynsam/avg@n | 0.662291 | 0.643526 |
| 进入训练轨迹的 mean reward | 0.597833 | 0.600520 |
| clip 前全局 grad norm | 0.00780057 | 0.00628155 |

负侧命中 tokens 约增 **11.3 倍**，新增负向 mass 约增 **26.6 倍**；同时 pg_loss、KL、长度和截断比例上升。这是一组应查看轨迹、按来源拆解和复核 loss 的信号。它不是“训练 reward 略涨，所以一切正常”。

但同一步 grad norm 下降，update_successful=1，skip 字段仍为 0；`select_hack_attempt_rate` 还从 0.503920 略降到 0.498541。不能把 token 命中数暴涨直接解释成“十倍数量的轨迹发生作弊”，也不能把一次 pg_loss 变大当作监督学习 loss 发散。轨迹更长、命中严重程度、处理权重与来源组成均可能参与，字段定义不足以确定原因。

`adv_neg_sum_pre_penalty` / `post_penalty` 在同一步仍相同；正侧也如此（公开数值精度下）。这与局部改权后恢复累计量相容，但无法从聚合指标还原精确算法，更不能证明具体动作级定位。Flash s30 的离线评测及停止原因均未披露，因此**不把最后一步异常写成停止原因**。

## 7. Grader：均值约 9 分钟，长尾可接近 2 小时

末步 `stage_credit_group/time_total_sec_mean`：Pro 512.5 秒，Flash 580.9 秒。多个步骤的 `time_total_sec_max` 聚集在约 7,236–7,258 秒，即约 2 小时。重复平台形状提示可能存在超时上限加收尾时间，但 timeout 配置未公开，不能确认。

末步 end2end_success_rate 为 Pro 96.26%、Flash 96.77%；Pro s14 曾降至 **76.62%**，随后恢复。结合训练集群与 grader 的网络异常公告，说明评分链路的可用性本身是训练变量。该指标是评分管线完成情况，不能当作任务成功率。

最新 groups_attempted / groups_judged 分别为 Pro 1,017 / 979、Flash 991 / 959。此类组处理和等待计数应与具体统计窗口一起读，不能拿 live pending、完成 step 的均值和 batch 目标混成严格账本。

Flash `select_renorm_capped_rate` 从旧快照 0.02415 升到 0.07036，`select_renorm_k_mean` 从 1.17504 升到 1.21668；基础 lr 和 clip 参数没变，不代表实际训练信号处理强度不变。`select_hack_attempt_rate` 约 0.50 是自定义判定计数，定义及分母不充分，不能宣称一半训练轨迹已被证实作弊。

**可吸收的经验：** judge 能减少 value critic 的训练接线工作，但长轨迹输入、补充测试、组等待、重试与长尾会带来实际代价。均值延迟不能说明尾部是否阻塞批次，也不能换算 GPU 花费。比较 judge 与 critic 时，应纳入总时间和成本，而不预设 judge 一定便宜。

## 8. 固定 16 rollouts 的信息效率，可能随训练阶段变化

Flash s15→30：全部成功组占比从 **23.46% → 29.07%**，全部失败组从 **15.08% → 15.64%**；一组内既有成功又有失败的比例从 **61.46% → 55.28%**。Pro s23 的混合组比例为 62.72%。

在仅有二元终局 reward、采用组内相对 advantage 的简化算法里，全成功/全失败组缺少组内回报差异。但 MiMo 有动态采样和额外 grader 信号，这些采样统计不是训练后 ADV 的直接统计。不能将 44.72% 的 Flash 非混合组直接称为“无效训练量”，也不能因 `dropped_zero_adv=0` 就断言每组都提供有效梯度。

**可吸收的经验：** 16 个 rollout 不是天然最优常数。模型变强后，某些题可能已容易到无需 16 次尝试，另一些题仍需要更多探索或更好的评分。这提出 prompts / rollouts / grader compute 的分配问题；本次只有一条主要配方曲线，无法给出哪种分配更优的因果答案。

## 9. 样本流转、计费和图表口径：几个会直接改变结论的陷阱

**采样成功率与训练 reward 不同。** 官方定义 `dynsam/avg@n` 为该步采样 prompt 的 n 次尝试成功比例再对 prompt 平均；`critic/rewards/mean` 是该步进入训练的轨迹 reward 均值。题目选择、动态筛选、异步 carryover 与非二元奖励均可使二者走势不同。Flash s30 已有一个下降、另一个上升的具体例子。

**accepted 超过 1,568 不代表所有训练条件满足。** 停止前 Flash s31 feed 显示 accepted 2,704/1,568、judged 2,559，而某来源 target 仍差 1 个。来源配额、评分和组完成均可能约束准备情况；仅凭总数不能断言调度器空转或判定卡在哪里。

**不要把 carried/rejected 全叫过期。** Pro 末步 carried=18,354、rejected=20,608、expired=144；Flash 为 25,722、25,536、0。只有 expired 明确使用过期标签，其余原因和分母未完整披露。它们也不能和 live prompt 计数直接相减。

**完整运行时间不等于成功 step 时间之和。** Pro s16→17 的完成时间间隔，扣除 s17 报告的 step duration 后仍差约 5.88 小时；Flash s15→16 差约 5.63 小时。其间存在重启/回滚，但差额可能包括失败尝试、初始化、重跑等，不能全部命名为闲置时间。详细逐步时刻见 [step_history.md](step_history.md)。对成本效率应保留这些时间，而不是只计算成功更新的吞吐。

**部分卡片会显示历史最后值。** Pro cyber 的 response 卡片仍显示约 243k，但那是 s14，s15–23 为缺失。更具体地，overview 的 Pro s23 harness 表仍列 harness-R=1,022，实际是 s14 的最后值；表格总数 22,744 包含它，当前 s23 非空 harness rollouts 的和则为 21,722。前端 [app.js](sources/js/app.js) 的 `lastOf`、`renderMetricComposition` 可复核这一差异：表格取每条序列最后非空值，柱图把各步空值当 0。不要把表格当作同一 step 的完整组成证据。

**其他分母也不能擅自统一。** 当前非空 harness rollouts 求和，Pro 21,722、Flash 22,421，均不等于 train/verdicts/trained=25,088；rollout_share 与原始 counts 也有聚合口径差异，不能自动算成丢弃率。数据源组成本身是由 accepted/held/carryover 推导，Pro s23 还使用重启后的比例近似，网页明确标注 ≈。详见 [来源与 harness 对照](source_and_harness_changes.md)。

## 10. 算法线索的更新与边界

- 当前公开的是 Pro、Flash 两条多任务训练运行。多个数据源、harness 和指标页面不等于多组独立算法消融；没有固定总预算的 prompts / rollouts / grader 配额对照。
- About 本次仍只有直播与即将发布的简短说明，没有算法公式或正式名称。
- lr=3e-6、clip_low=0.20、clip_high=0.27 在已公开步骤中保持不变；组大小仍为 16，stage_credit、signed penalty、异步 policy lag 仍存在。
- `actor/ppo_kl` 与 `pg_clipfrac` 均为 0，而 train/infer KL 非零、update_successful 为 1。这些字段不能跨实现等同解释；PPO 命名与 0 值均不足以判定实际 loss 公式或“没有更新”。
- 对公开同名对应序列逐项检查，`critic/returns/*` 与 `critic/advantages/*` 完全相同，`critic/rewards/*` 与 `critic/score/*` 完全相同；仍没有可据此确认 learned value critic 的证据。
- policy entropy 由旧快照 Pro 0.392→0.442、Flash 0.432→0.471，当前不呈现全局熵塌缩。但分布、长度和统计 mask 会影响均值，熵增不能单独证明探索质量提高。
- Pro s19 grad norm 有一次 0.03351 的突出峰值，随后回落，更新未跳过；孤立 spike 应结合后续和任务组成看，不能机械称作训练崩溃。

公开数据仍无法确定：完整 ADV 公式、过程 credit 粒度、judge 使用何种模型、实际 staleness 阈值/修正公式、所有 penalty 的定义、硬件资源数与真实成本分项、数据划分和 eval 统计不确定性。不能据这些曲线确认“16 最优”“judge 比 critic 便宜”“credit 是涨分主因”或“大规模 RL 已到极限”。

## 作为外部研究者，后续怎样读这种直播

1. 每次先固定快照、step、wall time、公告和评测覆盖；保留回填与缺失。
2. 用多组离线评测确认能力趋势，再读训练成功率；不把动态题目上的 avg@n 当作固定考试。
3. 在整体均值外看任务来源、harness、轨迹长度与 policy lag 分桶，尤其检查均值与分组走势是否相反。
4. 把轨迹 token/turn 增长当作系统预算变化，记录平均值、尾部、截断与 trainer 时间。
5. 对异常联看 reward、ADV/penalty、KL、梯度、更新是否成功及真实轨迹；一个指标不承担全部诊断。
6. 把 grader、环境、筛选和队列计入学习闭环；保留失败尝试与重启时间。
7. 把当前观察转成可证伪的问题，例如“同预算增加题目覆盖还是增强评分更好”，而不是把单条生产运行曲线当成消融答案。

本次已按用户要求另行记录 [后续 credit 实验候选](../../../../agentic_RL/repo_harness_rh2_workstreams/project1_execution/credit_assignment_ideas_20260919.md)，连接 SWE-RM、SWE-TRACE、Agentic Rubrics、DRACO、IAPO 等既有精读。它是后续研究备忘，不是训练配方或实施授权。

## 复查入口

- [原始快照与采集版本](snapshots/20260919T051100Z/summary.json)、[原始文件清单与 SHA-256](snapshots/20260919T051100Z/manifest.json)
- [全部指标对照](metric_changes.md)、[机器可读比较](metrics_comparison.json)、[逐步时间与评测](step_history.md)
- [来源/harness 对照](source_and_harness_changes.md)、[数据源构成复算](composition_derived.json)
- [公告原文](snapshots/20260919T051100Z/notices.json)、[评测原始数据](snapshots/20260919T051100Z/benchmarks.json)、[官方简短指标定义](snapshots/20260919T051100Z/runs.json)
- [UI 巡检范围](browser_audit.md)、[自查说明](verification_notes.md)、[数据核验](verification.json)
- [冻结数据分析与作图脚本](analyze_changes.py)；仅读取本地快照，不平滑、不把缺失评测填成已测结果。
