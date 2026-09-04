# Claude 方向综合与首训阶段重定位（2026-09-02）

> 性质：**讨论材料，非 owner 定案，非实施计划**。本文补记两件只存在于对话、
> 尚未落盘的东西：① Claude 对方向发现（Blind/Seeded Pro + codex 综合）的独立
> 核验与建议；② 首训阶段是否保留为独立阶段的分析。讨论阶段不套开发期协作手册。
> 与 codex 的 `codex_evidence_review_and_direction_synthesis_20260819.md` 并列，
> 不改写它。

## 一、对三份材料的独立核验（改变决策的事实点）

**✅ 确认 3 项**：
1. MOPD 同源约束（2606.30406 §4.4.2）：同源 teacher 初始 per-token KL≈0.04，
   跨源 Qwen3-235B≈0.19（5 倍），更强的跨源 teacher 反而让 student 性能下降，
   top-k 版本约 18 步发散；MiMo-V2-Flash 上 IFBench −2.2 / SWE −0.8。→ 否定"拿
   现成强开源模型蒸进自己模型"的捷径，同时匹配"首训产 SWE 专家→分叉更多专家→
   整合"的自然路径。
   **【2026-09-03 增补：三角验证升级为四源收敛】** 新入库的 Intern-S2-Preview
   （E10：同源双 expert〔reasoning/agentic〕+ 只传 sampled-token logprob 的
   reverse-KL OPD，明确以成本理由否决细粒度多 teacher）与 Nemotron-Cascade 2
   （E11：30B-A3B，teacher 全部取自自家 checkpoint 池、同源同词表、sampled-token
   reverse-KL + [0.5,2.0] 截断 IS，且 MOPD 放管线中段做"回退修复"而非终局整合）
   与 K3、MOPD 论文完全收敛到同一配方形态。C 线"同源、sampled-token、单/少
   teacher"现有四个独立来源；Cascade 2 还提供了"MOPD 作为中段回退修复"这一
   不同放置位的设计选项。精读见 knowledge/summary_intern_s2_preview.md、
   summary_nemotron_cascade2.md。
2. Prime Intellect 多智能体 = 只有代码发布（verifiers 0.3.0 / prime-rl 0.8.0），
   无训练曲线，C 级证据。codex"远期"定位正确。
3. Harness Interplay（2606.25447）边界：只有 ALFWorld、约 1800 H200-hours，证明
   "harness 影响训练"而非"多 harness 随机化必然学出接口不变性"。

**❌ 修正 codex 一处**：`Nemotron-SFT-SWE-v3.5` 官方数据卡**确实存在**（5115 条、
2026-06-20、v1.0、CC BY 4.0），codex"尚未核验到官方数据卡"不成立。可作 warm-start
候选数据登记。

**➕ 三方都没充分挖掘的一点**：本地 pin 的 slime（现已迁 miles）不只是"有 OPD
接口"，而是有完整可跑的 8 卡配方模板（1 卡起 SGLang teacher + 其余训 student，
OPD = advantage 上的加性 reverse-KL）。miles 更保留并扩展了 OPD（含 multi-teacher
脚本 + 模块化 `loss_hub/opd.py`）。OPD proof/kill 启动成本比三份材料估计的都低。

## 二、方向建议（同意 codex 主干 A/B/C，四点修正）

主干（codex）：A 可验证环境生产与训练资格（第一优先）/ B 多 harness 跨接口泛化
/ C OPD 条件线 / 底座（fully-async+DIS+治理）不另立项 / 多智能体远期。四点修正：

**3.1 分层交付兜底（最重要，codex 没讲透）**：研究命题可能失败（多 harness 可能
无增益、或被 parser/prompt 信息量解释掉），所以项目组织必须**命题可失败、交付不
可失败**：

| 交付层 | 即使命题失败也成立的产物 | 对标物 |
|---|---|---|
| infra | fully-async 正确性证据链 | verl/slime/DORA 系统贡献 |
| 环境 | 资格流水线 + 版本化环境资产 + exploit 语料 | PI 365K 环境、CalibForge |
| 评测 | checkpoint × harness 交叉矩阵 + frozen held-out 治理 | Harness-Bench |
| 模型 | 因果矩阵结果（正或负）+ 30B 确认实验 | Harness Interplay、MOPD |

负结果在 2026 行业语境有价值（K3 公开 top-k 无优势、DeepSeek 公开 PRM/MCTS 失败
都被反复引用）。

**3.2 OPD 升格半档**：codex 把完整 MOPD 降级正确（同源约束 + 资源账支持），但把
单 teacher OPD 也压到"先对拍接口"过于保守。理由：① 启动成本已证实很低（miles 有
现成实现 + 8 卡拓扑）；② 同源约束与我们路径天然契合（首训产 SWE 专家 = 与 base
同源）；③ 这是 8 卡内最便宜的"独立复现"机会（三份 Pro 承认本轮所有候选无一达 R
级）。建议：C 线不等 B 出结果，小模型上与 B 并行 proof/kill；完整多专家 MOPD 仍
作条件式 capstone。

**3.3 探针槽位选 tool-fault（非 context/memory）**：tool-fault 与 A 线协同（故障
家族 = 环境族生成的一个维度），runtime-only vs RL-only vs runtime+RL 对照清晰；
context/memory 有三重不利（与首训 compaction-off 定案冲突、CompactionRL 有
no-compaction 回退、TRACE 不训权重），保留为 B 线 offline boundary replay。

**3.4 对三个原始问题的回答**：对齐前沿？是（A+B+C 映射 2026 主流四层结构前两层
+评测层）。高价值？是且按 3.1 分层后不依赖单一命题成立。8 卡可行？是（A 吃 CPU/
API；B 因果矩阵在 3-8B 做，30B 只确认；C 有现成 1-teacher-GPU 拓扑；多智能体/
User-Sim 不进近期）。

统一叙事（面试版）：**"建一条可信 agentic RL 训练链 → 证明环境资格与 harness 分布
对能力的因果影响 → 用 OPD 把专家能力整合进部署模型并保持"**。

## 三、首训阶段是否保留为独立阶段（2026-09-01 讨论）

**用户提问**：完整首训（SWE + GRPO）对最终简历项目无增量，只测链路可靠性；是否
可以 GPU spike 测好 infra 后直接进正式项目训练，不单独设首训阶段？

**Claude 结论**：前提一半成立。首训的**能力宣称装置**（E5 的 Δ≥8pp 预注册判据、
功效分析、满血 frozen held-out T≥50×n8 双 checkpoint、数据扩容档）对最终项目确实
无增量，应删。但"spike 就够了"不成立——**spike 验证不了训练信号的语义正确性**。

建议：**取消"首训"作为独立阶段，但在已并入的 GPU 资格 campaign 尾部保留一段
20~50 步的"训练完整性短跑"（integrity run），验收从能力判据全面降格为完整性判据。**
（这是对 plan-06 §2 条 7 的小改动——它已把 FA-5 吸收进 GPU 资格作业 H1~H10，等于
加一个 H11。）

**为什么 spike 替代不了几十步真实训练**：
1. 这类"不崩溃、不报错、只默默毁掉或偏置学习"的缺陷在本项目是现行犯——A6（GRPO
   组内可信 reward=0 成员负 advantage 不得清零）、A5（timeout 长度偏置）都是不会让
   spike 变红但会砍掉训练信号的例子。
2. 有些错误需要步数才显形（Open-Instruct #1473：lr=0 下 logprob 漂移到 ~step450
   才爆；熵坍缩、KL 漂移、staleness 累积同理）。
3. 后端刚换 slime→miles，旧验证证据大面积失效，且"30B-A3B × fully_async ×
   faithful DIS × 真实多步"这个组合从未存在过（P3 时 fully_async 用 0.6B 替代、
   DIS 未上、30B 跑 train_async 双缓冲）。迁移 spike 全绿只说明"接上了"不说明"学
   对了"。
4. 正式项目 C 包数值（timeout 四分类、staleness、H1~H10 预算）需要一次 formal
   profile 真实短跑标定，否则拍脑袋，中途返工期望成本高于短跑。

**对"首训无帮助"前提的三点修正**：① 数据线工作（四门/216/held-out）就是简历项目
A 线本体，不是首训沉没成本；② 完整性短跑产物直接被最终项目消费（配置模板/遥测预
算/甚至 checkpoint 作 C 线 teacher 种子）；③ 不做完整性验证的隐性代价出现在最坏位
置——第一次真实学习循环若发生在正式项目首个实验里，静默 bug 会同时烧 GPU + 污染
研究结论（分不清"多 harness 没增益"和"训练本来就坏"）。

**落到 plan-06**：保留 W0~W8 + 界外数据线（改挂 A 线）；降格 held-out→小切片冒烟
eval、E8 能力证据→完整性证据、W7 thresholds→完整性判据；移入最终项目 Δ≥8pp 判据
+功效+满血 held-out+扩容档+R2E。00-status 的 S4 语义"正式训练实验"→"最终项目训练"。
**当前仅讨论，未拍板**（见 `../../../agentic_RL/repo_harness_rh2_workstreams/tmp/
doc_drift_backlog_20260902.md` 第 6 条）。

## 四、外部资源定位（用户给的三个链接 + 后续）

- Prime Intellect multi-agent（2026-08-07）：Agent/Env 两抽象 + 四类环境（含
  User-Sim）+ Hierarchical GRPO + RAE，随 verifiers 0.3.0/prime-rl 0.8.0，仅代码。
  本地 pin 早于此版本，需拉新（已在 env 阶段做了 v0.3.1 影响面评估）。
- HF delta-weight-sync（2026-05-27）：RL 下 bf16 相邻步 ~99% 位不变→稀疏同步
  30-130x。P3 实测权重同步仅占 step ~0.8%（瓶颈是 rollout），当前非瓶颈，登记备查。
- Nemotron-SFT-SWE-v3.5（2026-06-20，5115 条 OpenCode harness 轨迹，CC BY 4.0）：
  warm-start/SFT 候选，且本身是"另一个 harness 的轨迹"，与多 harness 方向有交集。
