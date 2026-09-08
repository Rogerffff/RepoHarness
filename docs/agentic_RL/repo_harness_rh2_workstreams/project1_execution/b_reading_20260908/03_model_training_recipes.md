# B 线阅读整合：模型团队训练配方

阅读日期：2026-09-08。依据固定快照 `rh2_b_reading_20260908_ac0e2e64`，版本 `ac0e2e64163fbe49411540e901df439aea16b6b0`。本轮完整阅读七份**精读笔记**及其审查记录，没有重新逐页核验原论文、下载训练资产或运行模型。下文“报告披露”均指笔记所记录的原文事实；“作者解释”不等于受控因果实验；“B 线候选”不构成项目定案。

当前 B 线只做阅读整合。最终任务范围、taskset、规模和训练阶段尚未批准；216 题 SWE-Gym Lite 是现有候选材料，不能写成已验收的首训题单。

## 1. 全文覆盖记录

七篇共 3,087 行，均按连续区间分块读完，包括非 coding 内容、附录摘要、负结果、成本和来源缺口；没有只读 SWE 小节。

| 笔记及本轮完整范围 | 同时覆盖的非 SWE 内容 | 审查状态 |
| --- | --- | --- |
| [R1 MAI][R1]，1–499 行、§1–12 | STEM、偏好、安全、诚实、风格、工具服务、长上下文、红队与集群 | [独立审查][V1]三项补充已修，原文缺口保留 |
| [R2 Ultra][R2]，1–391 行、§1–12 | 十余种教师、办公、搜索、CUDA/RTL、证明、多语言、量化与 MTP | [独立审查][V2]修订已落；完整配方仍不可恢复 |
| [R3 Coder-Next][R3]，1–503 行、§1–12 | 中训、WebDev、UX、九类单轮编码、数学、安全、packing | [独立审查][V3]三项已修；PrimeVul 原表问题未解 |
| [R13 K3][R13]，1–375 行、§1–12 | 视觉、专业工作、长期助理、kernel、GRM、QAT、draft、六类案例 | [独立审查][V13]三项已修；跨版本状态与成本未知 |
| [N01 KAT][N01]，1–372 行、§1–12 | KwaiClawEnv、五域专家、PPO/critic、GRM、文末奖励表 | [独立审查][VN01]措辞修订已落；无模型规模披露 |
| [E11 Cascade 2][E11]，1–618 行、§1–14 | 十域 SFT、IF/RLHF、长上下文、证明工件、竞赛扩展和接口 | 只有[作者自查][VE11]；独立复查与 Table 11/12 原图核验未完成 |
| [R4 MiniMax][R4]，1–329 行、§1–10 | AppDev、搜索、办公/金融/表格/幻灯片、角色扮演、自演化 | [R4/N10 独立审查][V4]三项已关闭；本轮未另全文阅读 N10 |

## 2. 逐篇事实与对 B 线的意义

### R1：MAI 的可学习问题生产，远大于“环境能启动”

**报告披露。** 从 962B 总参数、34.7B 激活的 mid-trained base 开始，最初没有先用外部 reasoning traces 冷启动；STEM、agentic、helpfulness/safety 三支 RL 专家并行发展，再以轨迹 SFT 合并，最后轻量 RL。中途自蒸馏也回到 mid-trained checkpoint 做 SFT，既用于能力承接，也用于数值失败恢复。最终合并并非 OPD。

任务包括数学/科学、160K 竞赛代码、SWE，以及 150 多个模拟工具环境中的 130K 任务；工具任务还包含“有工具但不需调用”。SWE 从 1.02 亿 PR 筛到约 487 万候选，环境/评分验证后剩 265,617 个问题、94,044 个仓库，**其后质量过滤与题意重写的最终数量未给**。构建成功、可区分正确/错误解、题意充分是不同条件。隐藏测试在评分时应用；bash/editor 使用严格追加历史，评分仍在 agent 用过的同一容器。作者承认重置测试无法挡住所有 monkey-patching，需监测和人工复核。

**评测与取舍。** Verified 73.5，SWE Pro 52.8；Terminal 46.0 忽略了预设 timeout，不能与遵守超时的分数同表判优。作者报告 STEM 向 agentic 正迁移、反向未见变化，并发现最终安全/风格 RL 会遗忘复杂推理；这些缺少等预算完整消融。固定 token 预算下，新 prompt 多样性优于同题更多轨迹是自蒸馏经验，不能升为所有阶段定律。

**不可直接迁移。** 最大作业 4,864 GB300，典型组规模 128，另有先 16 再 additional 128 的原文冲突；百万级自蒸馏与万核制题不是八卡配方。B 线可借鉴分层验题与按原因记录流失，不复制其平台、采样阈值或任务规模。定位：笔记 §3–8；原文 §3.1–3.6、App. D/F/H。

### R2：Ultra 的多教师融合不能保证学生获得新推理路径

**报告披露。** 550B/55B 底座经历两阶段全域 SFT、统一多环境 RLVR、轻量 SFT warmup、两轮 MOPD，再冻结主干训练 MTP。能力覆盖办公产物、搜索、终端、会话工具、安全/事实性、数学证明、CUDA、RTL和多语言。SWE SFT 使用多个公开数据源和 harness，过滤提交、工具格式、调试残留等行为；这些是监督数据启发式，不是普遍 RL 准入规则。SWE 教师有多轮端到端 RL，隐藏测试给二元奖励；多数 agentic **MOPD** 因长尾低效改用单轮训练，不能合并成“所有 agentic 都端到端蒸馏”。

**评测与解释。** MOPD 弥合的 teacher gap 在 SWE 为 88.1%，HLE 仅 16.9%；作者解释为学生较容易迁移已有的工具行为偏好，却很少采到教师新学的稀有推理路径。第二轮 LCB 90→89、GDPVal 持平。跨 harness 图中 Ultra Verified 为 60–70 多分的一组结果，在 Codex 上却只有 21.1，直接限制“多 harness 训练已经普遍鲁棒”。ProfBench、PinchBench 只在 final model 后评，是较明确的开发留出协议，但不证明预训练无污染。

**B 线候选。** 无法解决的题先诊断学生是否具备必要技能与动作表达，再讨论 OPD；第二 harness 可先作固定模型评测。完整 SWE 题池、误杀率、GPU-hour 仍缺；3K+ GPU 注册优化、百万级各域 SFT 与 192K 蒸馏不能按 55B 激活直接换算八卡成本。定位：笔记 §3–8、§10；原文 §3、App. A.2 图17。

### R3：Coder-Next 的 3B 激活不代表本项目的训练起点

**报告披露。** Qwen3-Next 的 80B/3B base 经万亿级 NTP/FIM 中训、SFT，分 WebDev、UX、单轮编码 RL、SWE RL 四专家，再蒸馏回 SFT 模型；末段蒸馏算法未给，不能称已知 OPD。天然数据含约 600B 仓库 token。807,693 个真实 PR repository instances 与 851,898 个注入 bug tasks 是两池，不能直接相加成去重 RL 题单。

工程能力覆盖库/API、I/O、多语言、SQL、测试/编辑、复杂指令与安全代码；WebDev 用 Playwright、截图 VLM 和交互状态过滤，UX 学工具定义、调用与返回格式。VLM 作为评审者不证明学生本身支持视觉。SWE 的 SFT/RL prompts 互斥，不等于仓库或派生任务严格互斥；过易与噪声失败会筛除，但阈值和重复数未知。

**评测与负结果。** 固定数据量的模板数 1→8 消融，Verified 约 48→53.8；另一个中训实验跨 OpenHands/SWE-agent 迁移很弱且不对称。二者不能混成同一“多 harness 增益”。最终 Verified 约 71，Terminal 25.8–36.2；FullStack、BIRD-SQL、EvalPlus 有回退。防未来代码措施未强化时出现 84.6 的作弊高分，强化后专家图为 75.1，不能把前者当能力提升。PrimeVul 的 P-C 方向及部分比例分母仍有来源问题。

**B 线候选。** 对目标 checkpoint 先测格式、工具调用和真实任务三个层次。不能只因激活参数同为 3B，推断 Qwen3-30B-A3B 具备相同仓库知识、长上下文与训练适应性。定位：笔记 §3–7、§9；原文 §2–5、App. A。

### R13：K3 拓宽工程能力定义，但没有给 SWE 供给闭环

**报告披露。** 2.78T/104.2B 原生视觉底座，SFT 后按通用任务、通用 agent、coding 三域训练 low/high/max 九个 RL policy，再 MOPD；各域先训 max，再退火预算。涉及 kernel、网站/游戏、专业工作、多日助理和自主执行，后者区分公开诊断接口与隐藏场景验证。1,505,678 images、51,219,741 sandbox creations 含训练和评测重复启动，均非题目数。

白盒可组合 harness 支持不同工具、上下文管理、skills、subagent；同步迭代中达到完成比例后暂停，未完轨迹下轮续跑，同题 K 条完整才优化。它不同于 miles 连续 fully async。预算超限覆盖 reward 为 −1，也不同于丢弃样本。K3 不能为本项目重新设计 scheduler 提供直接授权。

**评测与边界。** Terminal 2.1 的 88.3 是跨 harness 取最好；内部 benchmark 持续参与开发，不是最终未触碰留出。无 compaction 的 1M BrowseComp 为 90.4，300K 压缩为 91.2，未匹配总计算。研究级推理、agent 行为纪律仍有短板；top-k 蒸馏无明确优势。几百 GPU 的长程共置实验、微虚拟机和百万上下文不可平移；SWE 题单漏斗、污染、实际成本未披露。B 线可借其“最终产物/状态验证”的任务定义，不能据旗舰任务跨度要求首训全覆盖。定位：笔记 §3–9；原文 §4、§5.3、§6、App. F。

### N01：KAT 最有用的证据是环境错反馈曾被误判为算法问题

**报告披露。** 基座规模和初始化未给。五域专家为 SWE、Claw、terminal、web coding、general knowledge，使用 PPO/GAE、训练期可读事后信息的 critic、规则与 GRM 奖励，之后教师轨迹 SFT 冷启动加 MOPD。critic 无偏性、复杂 reward 的单项收益并未证明。

AutoBuilder 用结构化测试输出和跨次一致性，要求收集超过 90% **预期测试**，不是 90% 通过；构建成功率 16.5→57.2%，产出十万多环境，但缺候选分母。过程提示可使原零通过任务约 20% 通过；随后必须固定已验证 patch，从原始无提示上下文重新生成，并再次查执行、泄漏与一致性，20% 不是最终监督数据留存率。KwaiClawEnv 另做服务/任务/执行三层一致性，覆盖写作、数据分析和业务工具链。

白盒与真实黑盒 harness 均参与 RL。约 200-turn 实验中 40% 是发生重分词漂移的 **sample 比例**。早期抽审约 16% 轨迹含 sandbox 故障，修复后反馈错误低于 2%；曾发生几十步空 observation 与 verifier 读错配置。先调 RL 超参没有解决这些问题。

**B 线候选。** 区分模型失败与环境错误，再研究近成功轨迹是否值得恢复。SWE Pro 65.2 不能遮盖 Terminal 2.1 为五个对照最低的 60.7；内部 Code Bench 用于数据选择和增广，留出独立性不足。无硬件/预算/teacher规模，不能直接采用 PPO、critic、十项 reward 或五教师作为八卡要求。定位：笔记 §3–8；原文 §2–6、文末表1–3。

### E11：相近参数规模的强例子，同样依赖重 SFT 与强教师

**报告披露。** Nemotron-Nano-30B-A3B-Base 经十域 SFT（33K steps、batch 64、packing 上限 256K、约1.5 epochs），再 IF→多域→MOPD→RLHF→长上下文→竞赛代码→SWE。MOPD 使用同源历史 checkpoint 恢复能力，数学教师甚至是初始 SFT；这不等于无外部蒸馏成本，SFT 和 GenRM 大量使用强外部模型。正式执行 SWE 用 OpenHands，16 prompts×64 rollouts、256K/200 turns；中间模型每题16次预筛，保留10%的全失败题。

Agentless RL 用模型评分且可提供 gold 定位；其 OpenHands avg@4 从49.8→50.8，最终模型50.2，不能由两张表隔离真实执行 RL 增益。Terminal 2.0 为21.1，LCB 为87.2；强竞赛推理没有自动转成强交互工程。BFCL、翻译回退，NIAH 99也不能代替复杂长文或长期执行能力。HLE boxed 格式约带来6–7个百分点，历史 reasoning 保留使 τ² 改变约3–5个百分点，显示协议本身能显著改分。

**B 线候选。** 在同一目标模型、任务和预算下比较初始化与后续学习，并监测保留能力。公开 SWE 3,612 条是发布记录，不保证历史全量消费；发布 SFT 数量与论文也不一致。严格 on-policy、每题64条及重 SFT 均不匹配当前八卡 n=8 配置，GPU总账仍未知。本篇尚只有作者自查，不能借其他六篇的独立审查状态替它背书。定位：笔记 §2–12；原文 Fig.2、§3–4、Table 4/10、App. A–E。

### R4：MiniMax 的实际工程范围包括新增功能、写测试和应用交付

**报告披露。** 229.9B/9.8B base 经 interleaved-thinking SFT 和分阶段四域混合 CISPO RL；没有多领域 policy 专家再 MOPD 的已披露链。SWE 分 bug fix、feature、性能优化、bug injection/合并、SWE-Test、code review，验证规则须随产物变化：新增功能不能机械套 F2P，代码审查甚至无需可运行环境。AppDev 要通过构建、交互和视觉验证；Terminal-Gym 从 Stack Overflow 重建可执行任务并削减 hints。搜索、办公、金融表格、幻灯片、对话和角色扮演各有不同评分链。

一次真实 completion 是动作，实际呈给模型的 context 是状态，信用分配仍可跨 episode；这支持正确理解上下文重写，不能直接补齐其 token mask。Windowed FIFO 限制消费乱序，前缀树只复用计算；最高40×是缺 workload/硬件分母的局部训练声明。

**评测与边界。** M2.7 的 MMLU-Pro 比 M2.5 低3.4点，限制“混训消除遗忘”的解释。Terminal 57.0 使用2h预算；SWE 默认 Claude Code但 GPT 用 Codex。GDPval 同时用于训练种子和评测，拆分缺口不等于已证污染，却使独立性不能默认成立。自演化和 MLE 是固定模型执行/修改工程的工作流，不是持续更新 policy。B 线可借产物对应 verifier 的思路；完整题量、SFT/RL预算、reward、共享前缀计权和评分隔离均缺，不能据此造 Forge 或复制速度奖励。定位：笔记 §2–8；原文 §4–8。

## 3. 跨篇不能“取多数票”的冲突

| 议题 | 真实差异 | 对 B 线的限定 |
| --- | --- | --- |
| SFT 是否必做冷启动 | MAI 初始 reasoning RL 直接从 mid-trained base 开始；其余多数先做较重 SFT，且初始化各异 | 先诊断当前 checkpoint；不把“必须先 SFT”或“RL 可凭空学会”定为规则 |
| 能力如何合并 | MAI 轨迹 SFT；Ultra/K3/KAT MOPD；Next 未披露；Cascade 中途恢复；MiniMax 分阶段混训 | 这些解决的问题不同，不能以旗舰采用次数决定本项目新增教师 |
| 超长/未完成 | Ultra SWE mask loss；Next惩罚reward；K3覆盖为−1；Cascade按阶段零reward、过滤或mask | reward、组统计、梯度、补采是四件事，不从论文拼成统一处置 |
| 题目难度筛选 | MAI有两级pass-rate区间；Cascade保留部分全失败题；KAT尝试提示恢复；Next未给阈值 | “全失败”不能直接等于不可训练，更不能由强teacher通过率代表本模型难度 |
| 多样性与遗忘 | MAI某自蒸馏实验偏新prompt；MiniMax称同题多解有OOD价值；Cascade报告部分域混训有害 | 阶段、预算、能力和评测不同；作为待比较假设，不能互相覆盖 |
| harness 与吞吐 | MAI简单追加；KAT真实黑盒；K3可组合；Ultra仍有跨harness大降分 | 第二harness先诊断；格式正确、任务完成、泛化三种指标分开 |

八卡约30B-A3B的可用推论是**诊断顺序**，而非各家的规模配方：未来先固定 checkpoint/模式与工具接口，确认环境/评分及题意有效，再观察本模型无提示执行的成功、近成功、零进展和系统故障；之后才比较直接 RL、有限完整轨迹 SFT 或数据恢复。训练范围可按修复、功能/API、测试、终端和交付分层讨论，同时分开开发集与最终留出、保留能力与迁移指标。这些只是后续实验候选，本轮不选题、不定阈值、不冻结比例。

## 4. 后续回原文的优先缺口

七篇普遍缺少“最终独立任务→实际消费组/轨迹/token”的全链数量、完整失败语义、评分误差率、可审计的污染/派生关系切分和全部教师/CPU/GPU费用。没有这些，不能把环境数量、激活参数、optimizer steps、每题API价格或局部加速合成总成本优势。

真正准备引用具体机制前，按最短入口补证：R1 核 early/full 128 vs16+128和质量过滤终点；R2核未完成loss mask之外的组处置、teacher实际RL题池及71.7/70.7评测差异；R3核完整RL/蒸馏目标与PrimeVul预测/分母；R13核跨权重缓存/概率和SWE供给；N01核base、hindsight critic和无提示重建的留存/独立收益；E11优先独立核公式、正文/附录配置冲突、Table11/12原图及数据卡差异；R4核MLE图文口径、thinking stripping歧义、GDPval拆分及真实计权。上述缺口没有因笔记已修订而消失，本轮也没有把它们伪装成已重验结论。

[R1]: ../../../../harness_improve/external_paper_references/reading_notes/R1_mai_thinking_1.md
[R2]: ../../../../harness_improve/external_paper_references/reading_notes/R2_nemotron_3_ultra.md
[R3]: ../../../../harness_improve/external_paper_references/reading_notes/R3_qwen3_coder_next.md
[R13]: ../../../../harness_improve/external_paper_references/reading_notes/R13_kimi_k3.md
[N01]: ../../../../harness_improve/external_paper_references/reading_notes/N01_kat_coder_v2_5.md
[E11]: ../../../../harness_improve/external_paper_references/reading_notes/E11_nemotron_cascade2.md
[R4]: ../../../../harness_improve/external_paper_references/reading_notes/R4_minimax_m2_series.md
[V1]: ../../../../harness_improve/external_paper_references/reading_notes/reviews/01_R1_review.md
[V2]: ../../../../harness_improve/external_paper_references/reading_notes/reviews/07_R2_review.md
[V3]: ../../../../harness_improve/external_paper_references/reading_notes/reviews/02_R3_review.md
[V13]: ../../../../harness_improve/external_paper_references/reading_notes/reviews/08_R13_review.md
[VN01]: ../../../../harness_improve/external_paper_references/reading_notes/reviews/03_N01_review.md
[VE11]: ../../../../harness_improve/external_paper_references/reading_notes/reviews/E11_nemotron_cascade2_self_check_20260907.md
[V4]: ../../../../harness_improve/external_paper_references/reading_notes/reviews/09_R4_N10_review.md
