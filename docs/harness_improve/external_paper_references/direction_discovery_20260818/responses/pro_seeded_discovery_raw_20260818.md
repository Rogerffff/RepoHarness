# 第一轮研究方向发现  
**检索截止：2026-08-18**

本轮不选唯一最终方向，也不把某个新算法名当作研究命题。RepoHarness 当前真正有辨识度的基础，是把可执行环境、训练资格、轨迹投影和异步训练版本契约连成一条可审计链；当前正式训练总闸门尚未打开，已有 30B-A3B 八卡结果只是可运行性探针，不是能力结论。 

我的总体判断是：**最值得研究的不是“怎样再提高一次公开 benchmark 分数”，而是哪些任务、轨迹、反馈和异步更新可以被证明具有训练资格，以及这种资格能否带来跨环境、跨接口且可归因的能力提升。**

证据成熟度采用以下标记：

- `I`：仅提出想法；
- `C`：有公开代码、配置或可执行资产；
- `T`：确实更新过目标模型权重；
- `A`：有受控消融或匹配对照；
- `R`：有不同团队的独立复现。

同一作者团队在第二个模型规模上的重复实验不算 `R`。官方技术报告中的旗舰模型训练记为 `T`，但不自动意味着该团队公开框架里的每个算法都被旗舰模型使用。Seed 本身也明确要求这样区分。

---

## 1. 搜索与覆盖说明

### 1.1 检索方法

我先把 seed 当作来源导航，而不是方向目录；这与资料包本身的使用限制一致。 随后分两轮检索：

1. **Seed 核验轮**：回到原论文正文、附录、官方 PDF、模型卡、仓库、固定 commit、release、PR 和 issue，判断各项到底处于 `I/C/T/A/R` 哪一级。
2. **Seed 逃离轮**：不使用 seed 项目名，以“task learnability、trajectory eligibility、verifier hacking、tool failure、context corruption、training provenance、capability regression、release gating、dynamic curation”等问题词检索。

重点补齐了 **2026-07-28 至 2026-08-18**：

- 7 月 31 日：非原子工具失败下的 verified tool calls；
- 8 月 3 日：LongHorizon-Harness；
- 8 月 4 日：Verifiable Memory；
- 8 月 6 日：CalibForge、TRACE；
- 8 月 7–11 日：HarnessSafe、ActBench、REDAgentBench；
- 8 月 12 日：BENCH2ROBUST；
- 8 月 12–18 日：`slime`、`verifiers`、`prime-rl` 中与 fully-async 样本丢弃、样本—reward 错配、resume lineage、重试语义和在线评测权重版本有关的实际修复。 

8 月 13–18 日的非项目名检索没有发现足以取代上述候选的新模型级受控训练结果；这一小窗口新增的承重证据主要来自代码层的 provenance、resume、checkpoint—eval handoff 和正确性修复，而不是新的产品版本号。

### 1.2 覆盖的团队与生态

覆盖了 Microsoft、NVIDIA、Alibaba/Qwen/ROLL/ROCK、Z.ai/THUDM、DeepSeek、Moonshot/Kimi、MiniMax、Cursor、Prime Intellect、Hugging Face，以及 CMU、Nokia Applied Research、SYSU、RUC/AweAI、AMAP、POSTECH/Fewshot 等研究团队。来源不只来自 arXiv：

- 原论文 HTML、PDF 和附录；
- MAI-Thinking-1、Nemotron 等官方技术报告及图表；
- 官方 GitHub 仓库、代码路径、固定 commit 和 issue；
- Hugging Face 数据集、checkpoint 和 rollout；
- 可执行 benchmark、环境和评测实现；
- reward hacking、能力回退、benchmark 失效、工程正确性 bug 等负面证据。

本轮找到的 seed 外一手来源超过 8 个，主要包括 **CalibForge、TRACE、Verifiable Memory、BENCH2ROBUST、Verified Tool Calls、AgentAbstain、Hardening Agent Benchmarks、BenchJack、reward-hacking 负结果、ACM、Proactive Memory Agent、CurateEvo、CoEvolve、CLAP、OpenFinGym、REDAgentBench、HarnessSafe、ActBench、PostTrainBench**。

### 1.3 仍可能遗漏的区域

仍有四类空白：

1. 2026 年 8 月新论文普遍还没有第三方复现；对本轮五个高潜力候选，我没有找到不同团队的完整训练复现。
2. GUI、视觉、机器人和真实互联网执行环境只做了安全与 context 线索检索，没有达到 terminal/tool/API 环境的深度。
3. 很多旗舰模型没有披露完整训练任务、硬件时长、失败 checkpoint 和未成功 recipe；这些数字在下文均保留为 `unknown`。
4. 非 GitHub issue tracker、私有社区复盘及未公开模型卡可能仍有遗漏。

---

## 2. 候选方向全景

我采用的分类不是按生命周期层机械切分，而是按**可信训练闭环中的责任边界**：

1. **资格形成**：什么任务和轨迹有资格进入训练；
2. **语义保持**：什么行为应当跨 harness、context 和故障保持不变；
3. **能力整合**：如何引入新能力而不破坏旧能力；
4. **训练事务**：异步系统是否更新了正确的权重、样本和目标；
5. **因果评测与治理**：提升是否真实、可归因且可回退。

| # | 候选 | 角色 | 初步分类 | 候选来源 |
|---|---|---|---|---|
| 1 | Solver-relative 任务可学习性校准 | 顶层研究命题 | **高潜力** | independently-discovered |
| 2 | 对抗式 verifier hardening 与训练资格门 | 顶层研究命题 | **高潜力** | independently-discovered |
| 3 | 跨 harness / interface 的语义不变性训练 | 顶层研究命题 | **高潜力** | seed-expanded |
| 4 | 可验证 context / memory 状态转换 | 顶层研究命题 | **高潜力** | seed-expanded |
| 5 | 工具故障下的 retry / switch / abstain 策略学习 | 顶层研究命题 | **高潜力** | independently-discovered |
| 6 | 带能力保持与 rollback 契约的模块化能力整合 | 顶层命题，但资源较重 | 需要关键探针 | seed-derived |
| 7 | 可执行安全中的“识别—行动”缺口训练 | 顶层命题 | 需要关键探针 | independently-discovered |
| 8 | Version/staleness/identity-correct 异步训练 | 系统命题；需绑定模型结果 | 需要关键探针 | seed-expanded |
| 9 | Fork/replay 式边界局部反事实信用分配 | 支持机制 | 当前不宜独立立项 | independently-discovered |
| 10 | 动态 protocol-valid held-out 与回退账本 | 治理/评测基础设施 | 当前不宜独立立项 | seed-expanded |
| 11 | 失败驱动、可版本化的数据策展策略演化 | 可成为顶层命题 | 需要关键探针 | independently-discovered |

### 2.1 Solver-relative 任务可学习性校准

**可证伪命题。** 在任务数、轨迹数、作者模型、求解预算和训练 token 匹配时，经过多求解器分歧或“强模型通过、弱模型失败”校准并允许修改 instruction、environment 与 verifier 的任务，比“可执行即可”“单求解器反馈”产生更高的 held-out 增益/训练 token，并能转移到未参与校准的接口或任务族。

**能力与瓶颈。** 目标能力是更高效地习得新工具、工作流和可执行推理。真实瓶颈不是缺少另一个 terminal 数据集，而是“有效”不等于“对当前 policy 可学习”：任务可能全员通过、全员失败、靠提示泄漏通过，或 verifier 本身定义了错误能力区间。

**链路与产物。** 创新主位于任务生产、环境验证、难度校准和训练资格；harness、轨迹投影和后端可以复用现有链。可复用产物包括 solver profile、task revision history、learnability frontier、资格 reason code、污染记录和任务冻结 manifest。

CalibForge 报告了 5,431 个校准任务；在匹配的 1,300 任务实验中，Terminal-Bench 2.0 从 no-solver 的 22.47 提升到 single-solver 的 24.34、multi-solver 的 29.21 和 contrastive 的 31.09。论文还披露两只 30B/35B-A3B 模型的全参数、多轮 SFT、10 epochs、131k context 和 64×H20。

**反证与未知。** 这可能学到求解器风格而非一般能力；校准过程也可能变相把解决线索写回 prompt。公开仓库目前主要提供数据、模型和最小 eval recipe，我没有找到完整的任务生成、solver calibration 与训练编排代码；没有独立复现。

**低成本探针。** 先取 50–100 个现有环境，用两个 API 求解器和一个较弱本地模型建立首次通过率、分歧和 revision 前后轨迹；不训练也能检验“有效任务中有多少其实不在可学习区间”。

---

### 2.2 对抗式 verifier hardening 与训练资格门

**可证伪命题。** 相比只使用终局标量 reward，把隐藏状态、外部 side-effect receipt、artifact provenance、攻击性 solver/fixer 检查和 fail-closed reason code 纳入训练资格，会降低模型对 verifier exploit 的学习和迁移，同时保持诚实任务通过率。

**能力与瓶颈。** 目标不是让模型更会“过测试”，而是让它学到真实目标完成。瓶颈横跨环境、reward、轨迹筛选和评测：一个可 hack 的 verifier 会同时污染 task validity、训练信号和最终分数。

**链路与产物。** 主创新位于 verifier、评分隔离和训练资格；模型优化可以复用普通 SFT/RL。产物包括 exploit corpus、hacker/fixer patch history、dual-evidence verifier、资格 reason taxonomy、攻击回归集和隐藏 oracle。

Hardening Agent Benchmarks 在 5 个 benchmark、1,968 个任务上找到 323 个可攻击任务；其重要负结果是，朴素 hacker-fixer loop 可以把攻击率降到 0%，同时把良性 solver 通过率也降到 0%，说明 hardening 必须约束 verifier 完整性而非只封攻击。 另一项实际 RL 研究发现，直接优化可见 reward 会扩大可见奖励与隐藏目标之间的差距；更细信用分配、探索提示和熵正则都未解决问题。

**反证与未知。** 过严资格门可能只降低数据量、制造假阴性；攻击模型和 fixer 也可能共享盲区。现有 hardening 工作主要证明 verifier 改造，不直接证明训练后的开放权重模型更诚实。

**低成本探针。** 选 20–50 个环境，构造访问隐藏测试、输出路径替换、状态污染、缓存复用和 scorer monkey-patch 等攻击，让 API agent、静态分析和独立 verifier 交叉审核。先测资格门的 precision/recall，再决定是否训练。

---

### 2.3 跨 harness / interface 的语义不变性训练

**可证伪命题。** 对语义等价但 schema、tool grouping、参数名称、权限提示、上下文协议和错误表示不同的 harness 进行训练时随机化或一致性约束，能够提高对**完全未见接口组合**的迁移，并保持原生接口能力；提升不能仅来自一个更强、更提示友好的 harness。

**能力与瓶颈。** 目标能力是“理解工具和状态语义”，而非记住某个 JSON schema。现实瓶颈是训练后的 agent 往往把能力绑定到 action format、tool decomposition、权限和 observation wording。

**链路与产物。** 创新主位在 harness/trajectory 层和训练数据分配；任务语义、verifier 和后端尽量固定。产物包括 canonical action/state representation、语义等价 harness mutation suite、适配器 conformance test 和跨接口 held-out。

Harness-aware post-training 在 ALFWorld 的 3 个 harness、2 个模型和 2 个 RL 算法上做了 24 组训练配置；3B 模型配高信息 harness 可比 7B 配低信息 harness 高 14.1 点，训练时使用 harness 比训练后再套用高 20.7–22.5 点。论文同时承认只覆盖一个环境，总代价约 1,800 H200 GPU-hours。 Polar 则证明不同黑盒 coding harness 的轨迹可通过代理和 token reconstruction 接入训练，但它证明的是适配能力，不是接口不变性。 Qwen3-Coder-Next 的 template diversity 对照也支持接口多样化的训练价值，同时显示跨 scaffold transfer 仍有限。

**反证与未知。** 多接口训练可能只是格式正则化；canonical adapter 还可能泄漏语义标签，使所谓跨接口迁移变成统一接口训练。没有跨 terminal、API、web 三类环境的独立复现。

**低成本探针。** 在同一小环境中实现三种语义等价协议：细粒度工具、聚合工具和权限受限工具。先用 API/小模型做 zero-shot paired evaluation；若失败模式显著，再做小模型 SFT/RL。

---

### 2.4 可验证 context / memory 状态转换

**可证伪命题。** 在固定 token、步骤和工具预算下，使用环境 snapshot/fork 的局部反事实验证，加上终局 verifier 共同训练或选择 context/memory 操作，能够降低压缩后不可逆错误、重复获取和静默状态丢失，并在无 compaction 情形下不回退。

**能力与瓶颈。** 目标是长期保持约束、环境事实、未完成子目标、失败诊断和证据，并在需要时恢复。瓶颈不是单纯 context window 太短，而是摘要或 memory write 本身是不可观测的状态转换错误。

**链路与产物。** 环境层要能重建 compaction boundary；harness 显式记录 memory operation；训练信号同时有局部 transition verifier 和全局终局反馈。产物包括 boundary cohort、PRE/POST paired rollout、memory operation schema、silent-corruption tests 和 pass² 评测。

TRACE 从同一 pre-compaction 状态分别运行原始历史与摘要续跑，用环境返回的 blocked/refetch 作为 trajectory-relative 指标；仓库公开 verifier、590 个冻结边界、policy optimizer 和可重放测试，但不训练模型权重。  Verifiable Memory 则实际提出七种 memory operation、SFT+三阶段 RL 和 local/global verifier credit；代码公开了 `00_verifiers/` 到 `04_training/`，但明确移除了任务数据、checkpoint 和算力配置。 

ACM 公开了 student rollout、teacher annotation、resume、teacher logprob cache、KD train 和 held-out eval 的端到端代码、rollout 与 checkpoint，但作者也明确指出缓存 teacher logprob 后 student 已更新，因此实际实现严格说是 off-policy。 CompactionRL 提供了真实训练和消融，但 30B 模型在不开 compaction 的 SWE setting 中得到 43.7，低于基座 47.5；在 compacted setting 才达到 56.0，说明它不是无条件的“通用长上下文能力提升”。

**反证与未知。** TRACE 的 blocked/refetch 会漏掉静默状态污染；VerMem 的任务间 memory state 独立，不能支持终身跨会话记忆主张；多数工作没有跨环境复现。

**低成本探针。** 无需训练，先在 20–50 个长轨迹任务上冻结若干真实 compaction boundary，比较 raw-history、静态 summary、ACM-style external store 和 TRACE-optimized policy 的 PRE/POST 差异。

---

### 2.5 工具故障下的 retry / switch / abstain 策略学习

**可证伪命题。** 在训练中显式区分暂时故障、路径永久故障、全局不可解和静默副作用，并提供 transaction receipt、postcondition 与替代工具图，可以让模型在无 inference-time memory 提示时仍学到 retry、switch 和 calibrated stop，并转移到未见工具和故障类型。

**能力与瓶颈。** 目标是故障恢复和正确停止。真实部署中的工具失败不是原子事件：一次 timeout 可能已产生副作用；盲目 retry 会重复付款、发送或写入。

**链路与产物。** 主创新横跨 fault-injected environment、harness transaction protocol、partial reward 与 held-out fault generalization。产物包括 fault compiler、fallback equivalence graph、idempotency/receipt schema、故障可解性标签和 abstention benchmark。

BENCH2ROBUST 把无故障 benchmark 转成需要 retry、switch 或停止的随机环境；在 held-out Retail 上，BTM 无训练可带来最高 16.8 点，RL 在不使用 BTM 时仍有补充收益，二者结合在 injection 下达到 40.8–45.5%，并保持 clean performance。 但论文没有建立真正的 learned abstention：S3 不可解任务缺少正向 completion credit，因此“abstain”更多是环境要求而非被充分奖励和校准的能力。Verified Tool Calls 的 postcondition、verify-before-retry 与 idempotency key 提供了重要系统机制，但没有权重训练。 AgentAbstain 则显示，17 个模型、4 个 harness 在 263 对 act/abstain 任务上的最佳 paired accuracy 也只有 59.5%，而 abstention 与任务能力相关性弱。

**反证与未知。** BTM 可能比训练本身更有效；故障注入器可能过于可识别；silent failure 的 oracle 很难建立。BENCH2ROBUST 没有公开训练代码，硬件、时长和费用为 `unknown`。

**低成本探针。** 在现有工具协议前加 fault proxy，生成约 100 个 S1/S2/S3 episode；先测模型在无训练和带结构化 runtime state 下的 retry/switch/stop confusion matrix。

---

### 2.6 带能力保持与 rollback 契约的模块化能力整合

**可证伪命题。** 在训练 token 和 teacher 调用预算匹配时，分领域专家训练、on-policy student sampling、teacher provenance 与能力保留 gate 的组合，能比混合数据 SFT 或串行 RL 更好地整合 coding、research、instruction/safety 等能力，且在任何关键 held-out 上不超过预先设定的回退阈值。

**产物。** 能力 ledger、teacher-origin 标签、每能力 retention set、rollback checkpoint、训练顺序记录和跨能力冲突矩阵。

MOPD 实际训练 Qwen3-30B-A3B，并报告模块化 teacher 后的整合收益；但 Table 3 同时出现 IFBench -2.2、SWE-bench Verified -0.8 等回退，跨来源 teacher 还能导致 collapse。 MAI-Thinking-1 使用 SWE/agentic、STEM、helpfulness/safety specialist，再做 trace consolidation 与最终 RL，并用 self-distillation 恢复数值能力 collapse；这是旗舰级官方证据，但资源达到数千 GB 系列 GPU，远超本项目。

**反证。** “RL 天然不遗忘”并不稳定成立；2026 年的 continual policy optimization 研究仍观察到显著多模态 forgetting。

**低成本探针。** 先用 3–8B 模型、两个差异较大的任务族和一个固定 retention set，比较 mixed、cascade、modular distillation 三种方式。

---

### 2.7 可执行安全中的“识别—行动”缺口训练

**可证伪命题。** 对“模型已经识别到约束，但后续工具行动仍违反约束”的轨迹进行状态级训练，比仅增加拒答或安全 reminder 更能降低真实 side-effect violation，并能跨 harness 和 persistent carrier 泛化而不过度拒绝。

REDAgentBench 提供 1,661 个可执行案例、多个服务 surface 和最终状态 receipt；其分析显示约五分之一违规发生在模型已识别约束之后，说明知识与执行之间存在独立缺口。 HarnessSafe 进一步把风险载体扩展到 memory、skills、tools 和 artifact；ActBench 则用 600 个案例、48 个 API 和双重日志/轨迹证据覆盖更广的行动风险。

这是可承担最终项目的能力命题，但引入新安全边界、服务模拟和 over-refusal 评测，成本高于纯 terminal 任务。低成本探针可先做 30–50 个“识别相同、行动不同”的 paired episode。

---

### 2.8 Version/staleness/identity-correct 异步训练

**可证伪命题。** 在完全异步训练中，显式记录 policy version、rollout identity、reward provenance、group completeness、resume lineage 和 checkpoint/eval handoff，会降低 silent sample corruption，并改善“有效模型增益/GPU-hour”，而非只改善系统吞吐。

这是重要系统命题，但**只有绑定到模型结果才足以独立立项**。可复用产物包括 deterministic replay、version graph、fault injector、resume manifest、sample/reward join invariant 和 async-vs-sync parity suite。

近期 `slime` 的真实修复说明问题不是理论上的：一个 fully-async collector 会在达到目标后多 pop 已完成 group 并丢弃；另一个 bug 会把 reward 日志与错误的 DP-local sample 配对。  `verifiers` 新增 resume lineage、config hash 和 changed-config rejection；另一个 commit 专门处理压缩后合法相同请求与 stale retry 不能靠 request-body 相等区分的问题。  `prime-rl` 的在线评测实现也必须处理 stable checkpoint、过早清理、resume 后 future trace 混合和 policy version 标记。

低成本探针主要是 CPU 和小模型：故障注入、重复运行、sync/async 梯度与样本 identity 对账，不必先消耗 30B 八卡资源。

---

### 2.9 Fork/replay 式边界局部反事实信用分配

**可证伪命题。** 从相同环境 snapshot 分叉两个候选行动或 context 操作，并比较短期真实后果，可以比启发式 turn reward 更准确地识别导致终局失败的决策边界，并提高后续训练样本效率。

这是**支持机制**，自身不足以成为顶层项目；它需要服务于 context/memory、工具故障或 verifier 资格命题。TRACE 的 PRE/POST continuation 和 Verified Tool Calls 的 postcondition 检查是最直接的证据，但目前尚缺“局部反事实标签确实改善模型训练”的独立结果。

---

### 2.10 动态 protocol-valid held-out 与回退账本

**可证伪命题。** 使用版本化、污染检查、protocol-valid、跨接口且包含能力保留项的动态 held-out，会改变模型选择和发布决策，并比单一静态 leaderboard 更好预测真实回退。

这是治理和归因基础设施，而不是单独的能力训练方向。产物包括 eval manifest、task provenance、接口版本 digest、污染记录、逐能力最低门槛、model lineage 和 rollback decision record。

2026 年 2 月，OpenAI 报告其审计的 138 个 SWE-bench Verified 难例中有 59.4% 存在实质性测试或描述问题；7 月对 SWE-Bench Pro 的数据分析标记 200/731 个问题，人工审核标记 249/731，即 34.1%。 这说明 held-out 本身也必须经过资格审查，而不能只做 train/test ID 分割。

---

### 2.11 失败驱动、可版本化的数据策展策略演化

**可证伪命题。** 把数据筛选、augmentation、refinement、SFT/RL 分流和 memory construction 表示为可执行、可版本化策略，并仅使用冻结 dev failure taxonomy 更新策略，能够在匹配 retained turns 与 teacher 调用预算时优于固定策展规则，且迁移到第二任务族。

**与候选 1 的区别。** 候选 1 校准单个任务是否处于可学习区；本候选优化的是**整个训练过程中数据分布如何随 policy 失败而演化**。

CurateEvo 用 failed trajectories 重写策展代码，并把固定 raw corpus 转成 SFT、RL 和 inference memory 数据；其摘要报告在 ACEBench-Agent、BFCL-V4 和 τ²-Bench 上有 3.2/2.7 点平均增益。 CoEvolve 则实际在 AppWorld/BFCL 和 Qwen2.5-7B、Qwen3-4B、Qwen3-30B-A3B 上训练，报告 15.58–19.43 点增益，但当前公开仓库只有极少文件，不能算可复现训练实现。

CLAP 提供有价值的负证据：五个业务 batch 中只有三个改善，且全部 GRPO batch 虽通过静态 admission，却在训练中出现极端 KL 风险；因此动态策展必须绑定 release gate，不能让 dev failure loop 无限制过拟合。

**关键未知。** 使用 dev 失败不断改数据策略非常容易把 held-out 变成隐性训练集。本轮没有找到 CurateEvo 的官方公开实现。初始分类为“需要关键探针”。

---

## 3. 值得继续讨论的五个候选

## 3.1 Solver-relative 任务可学习性校准

**能力命题 → 数据/环境与反馈。** 模型不是缺更多“有效任务”，而是缺位于当前能力边缘、既可解又不会被统一解决的任务。任务先过结构验证和 oracle/self-solving，再由多个 solver 或强弱 solver pair 产生可验证轨迹；反馈可以修改 instruction、initial state、artifact contract 和 verifier，而不是只过滤。

**Harness / 轨迹。** 每次 solver 尝试必须固定 environment digest、harness version、模型版本、sampling config 和 verifier revision。任务修改前后的轨迹需要绑定同一 task lineage，避免把“改了任务”误当成模型学习。

**训练信号、算法与系统。** 这一候选不需要发明新 RL 算法。最先可复用 multi-turn SFT 或现有 online RL；创新是 training admission：哪些任务、哪些 solver profile、哪些 revision 有资格进入训练。异步后端只消费冻结后的资格样本。

**Held-out 与归因。** 至少要有：未参与校准的 solver、未见任务族、未见 harness 组合、污染检查，以及按 accepted task、trajectory、token 和生成成本归一化的增益。

**一手与负面证据。** CalibForge 的匹配任务数消融是当前最强正证据；但它的核心生产代码未完整开放，使用 64×H20 的全参数训练，且 solver-style leakage 未被独立排除。

**最小本机/API 探针。** 50–100 个任务；两个 API solver、一个弱本地模型；比较 validity-only、single-solver、multi-solver disagreement、strong-pass/weak-fail 四类任务的首次 solver 分布、revision 次数和后续轨迹质量。可先不训练。

**进入八卡实验最小需证明。** 在 3–8B POC 或 30B 小规模训练中，匹配任务数和训练 token 后，solver-calibrated 数据提高未见任务 held-out；不能只提升参与校准的 Terminal-Bench 类任务。

**推翻条件。**

- 匹配轨迹数后增益消失；
- 未见 solver/harness 上不转移；
- 任务 revision 主要是把答案线索写入 prompt；
- 污染或 verifier 修改解释了主要增益；
- 单纯 difficulty filtering 达到相同结果。

**资源。** 来源披露：64×H20、10 epochs、131,072 context、全参数 SFT。wall time、API solver 总费用、任务生产人工成本：`unknown`。本项目已知 30B-A3B 一次 4 trainer+4 rollout 探针约 1,387 秒/step、rollout wait ratio 约 0.82，因此正式 30B 对照应在低成本资格探针之后。

---

## 3.2 对抗式 verifier hardening 与训练资格门

**能力命题 → 数据/环境与反馈。** 训练模型完成隐藏目标，而不是优化可见评分漏洞。每个任务至少区分真实目标、可见评分、side effects 和禁止路径；hacker 轨迹用于发现漏洞，fixer 改 verifier，独立合法 solver 检查修复是否误杀。

**Harness / 轨迹。** Scorer 与 policy 环境隔离；hidden tests、reference artifact 和评分凭据对 agent 不可见。轨迹记录文件访问、网络、进程、外部调用和最终 state receipt。任何缺少 provenance 或 scorer 隔离证明的 rollout 不进入正式训练。

**训练信号、算法与系统。** 对比三种信号：raw reward、hardened reward、hardened reward + eligibility mask/reason。资格门应能表达“honest pass”“exploit pass”“verifier ambiguous”“environment corrupt”，不能强行把所有情况压成 0/1。

**Held-out 与归因。** 使用未见 exploit family、不同 hacker 模型、不同 verifier 实现和隐藏目标评测；同时报告诚实通过率、攻击成功率、假阴性、任务存活率和训练数据损失率。

**一手与负面证据。** Hardening 工作证明自动攻击—修复是可行的，也明确证明只追求攻击率会毁掉 benchmark。Reward-hacking RL 的负结果则说明“模型训练后自然变诚实”不成立。

**最小本机/API 探针。** 20–50 个任务、5–8 类 exploit、两种 API hacker、一种独立 solver。先建立 attack survival 与 benign survival Pareto curve。

**进入八卡实验最小需证明。** Raw-reward 与 qualified-reward 两组，在相同有效训练 token 下，后者对未见攻击的 exploit propensity 显著较低，并且 honest held-out 不出现不可接受回退。

**推翻条件。**

- 只让攻击在可见 verifier 上消失，隐藏 oracle 不改善；
- 诚实任务存活率大幅下降；
- 模型仅学会拒绝或不行动；
- 对新的攻击模型没有迁移；
- 资格筛选减少数据后，用随机等量筛选能复现结果。

**资源。** Hardening 主实验披露 8×H200 约 48 小时，agent inference 走 API，总 API 费用约 5,000 美元；GPU 主要运行 KernelBench task execution。 本项目具体 task family、API 费用和八卡训练时长：`unknown`。

---

## 3.3 跨 harness / interface 的语义不变性训练

**能力命题 → 数据/环境与反馈。** 同一个环境语义被投影成不同 action schemas、tool grouping、observation format、错误协议和权限提示。模型要学习“这个动作在环境里意味着什么”，而不是 token 形式。

**Harness / 轨迹。** 需要 canonical semantic event layer，同时保留原始 harness trace；否则无法区分模型失败、adapter 失败和环境失败。训练与评测必须记录 harness hash，并冻结 semantic-equivalence tests。

**训练信号、算法与系统。** 可复用普通 RL/SFT；候选变量是每 episode harness randomization、paired consistency、跨 harness trajectory distillation。不能把全部输入先无损翻译成同一格式，否则研究问题被 adapter 消解。

**Held-out 与归因。** 关键不是看见过的三种模板平均分，而是：未见 schema、未见工具 grouping、未见权限组合，以及原生 harness 能力保持。

**一手与负面证据。** Harness-aware paper 对训练时/训练后 harness 做了受控比较；Polar 和 Qwen3-Coder-Next 支持多 harness 接入及 template diversity，但尚未证明强跨域 semantic invariance。

**最小本机/API 探针。** 在同一个环境生成三个协议，对同一 task seed 做 paired rollout，先测模型失效是否集中在 schema、admissibility、权限或状态追踪。

**进入八卡实验最小需证明。** 用小模型或 30B 小预算训练后，在**完全未见的接口组合**上显著改善，且原生接口不退；仅提高训练接口平均分不够。

**推翻条件。**

- 增益只出现在见过的 template；
- canonical adapter 承担了主要能力；
- 更丰富单一 harness 达到相同结果；
- 跨接口提升伴随任务语义退化；
- 换环境后效果消失。

**资源。** Harness-aware 研究披露约 1,800 H200 GPU-hours，单训练配置使用 4×H200；Polar 的完整训练硬件、时长和费用为 `unknown`。

---

## 3.4 可验证 context / memory 状态转换

**能力命题 → 数据/环境与反馈。** 模型应在有限 context 中保留任务状态，并能在压缩后继续正确行动。训练数据来自真实 compaction boundaries，而不是人工参考摘要；相同环境 snapshot 下分别运行 raw 与 compacted continuation，产生局部反事实标签。

**Harness / 轨迹。** context operation 必须成为一等 action：summarize、store、retrieve、select episode、delete 等均记录输入、输出、版本和可见性。环境需要 snapshot/rebuild，并检查摘要后静默状态损坏。

**训练信号、算法与系统。** 可使用 SFT warmup，再把局部 transition burden 与全局 task reward 组合；训练算法本身可复用 CompactionRL、VerMem 式 credit 或现有后端。TRACE 可先充当无权重训练的 verifier/probe。

**Held-out 与归因。** 同时报告 task pass、pass²、blocked、refetch、silent corruption、token/step、无 compaction 保持和跨 harness/model transfer。固定最大 token 和工具调用，排除“用了更多上下文”解释。

**一手与负面证据。** TRACE 提供强局部因果测量但只覆盖 AppWorld 类环境；VerMem 有训练方法代码但缺数据/checkpoint/compute；ACM 公开完整流水线却有 cached-logprob off-policy 问题；CompactionRL 的 no-compaction 回退表明能力可能条件化于 compaction harness。  

**最小本机/API 探针。** 20–50 个任务、每个抽取 2–5 个真实 boundary；比较 raw、static summary、lossless store、TRACE-style optimized prompt。只需环境重放和 API。

**进入八卡实验最小需证明。** 学到的 memory/context policy 必须超过最优 prompt-only policy，并在第二环境或第二 harness 转移；同时无 compaction 情况不能出现明显能力回退。

**推翻条件。**

- 增益完全由更多 token 或更多工具调用解释；
- local verifier 改善但终局无提升；
- silent corruption 不降；
- 无 compaction 能力退化；
- 只在训练环境有效；
- static summary 或 external memory prompt 达到相同表现。

**资源。** TRACE 不更新模型；其公开数据为 590 个 boundary。ACM README 披露 teacher Qwen3.5-397B-A17B 本地服务需要 8×B200 bf16 或 8×H100 fp8；student 完整训练时长和费用为 `unknown`。  VerMem 和 CompactionRL 的完整训练资源：`unknown`。

---

## 3.5 工具故障下的 retry / switch / abstain

**能力命题 → 数据/环境与反馈。** 同一任务被编译成正常、暂时失败、当前路径永久失败、所有路径不可解和静默成功/失败等版本；每个版本具有明确可解性和最优策略标签。

**Harness / 轨迹。** 每个工具调用具备 transaction ID、postcondition、side-effect receipt 和 idempotency key；替代工具间存在显式 capability/fallback graph。错误消息本身不得直接泄漏 S1/S2/S3 类别。

**训练信号、算法与系统。** 除终局 task reward 外，对正确 retry、及时 switch 和正确 abstain 分别给可辨识信号。若要声称 learned abstention，S3 必须有正向停止奖励，而不能只是耗尽 budget。可复用现有 RL 后端和 KL/能力保持约束。

**Held-out 与归因。** 未见 API、未见故障模式、不同注入概率、clean performance、重复 side effect、retry/switch/stop calibration，以及去掉 runtime BTM 后的能力。

**一手与负面证据。** BENCH2ROBUST 是最接近完整训练证据的工作，但 runtime BTM 本身贡献很强，且没有充分训练 abstention；Verified Tool Calls 证明事务协议可以减少重复副作用，但不涉及模型训练；AgentAbstain 说明正确停止本身仍是弱能力。

**最小本机/API 探针。** 约 100 个 fault-injected episode，在无 BTM、结构化 BTM 和 transaction receipt 三种条件下建立策略 confusion matrix，不必先训练。

**进入八卡实验最小需证明。** 4B/8B 或 30B 小预算训练后，在无 BTM 的未见工具和未见故障上，retry/switch/abstain 均有改善，clean task 不退，且重复 side effect 显著下降。

**推翻条件。**

- 只有 BTM 有效，训练权重没有持久收益；
- 模型从错误文本直接识别注入类别；
- 未见工具无迁移；
- clean performance 明显下降；
- abstain 只是过早拒绝；
- silent/non-atomic failure 仍无法处理。

**资源。** BENCH2ROBUST 的训练硬件、wall time、数据生成成本和 API 费用均为 `unknown`。论文披露 Qwen3-4B 的训练与同团队 8B 规模检查，但后者不算独立复现。

---

## 4. Seed 覆盖与逃离记录

## 4.1 Seed 论文与报告实际支持什么

| Seed 项 | 实际支持 | 不支持或仍缺失 |
|---|---|---|
| **R0 Polar / ProRL-Agent-Server** | `C,T,A`：确实用多个黑盒 coding harness 训练 Qwen3.5-4B，并有 trajectory reconstruction 消融。 | 不证明多 harness 训练得到接口不变性；硬件、费用 `unknown`。 |
| **R1 MAI-Thinking-1** | `T,A`：官方报告明确给出 specialist RL→distillation→final RL、environment builder 和数值能力 collapse 后 self-distillation。 | 闭源数据和系统；资源远超本项目；无独立复现。 |
| **R2 Nemotron 3 Ultra** | `C,T,A`：官方报告、模型/recipe/data release 主张和多 teacher post-training。 | 中间 checkpoint 与完整 flagship pipeline 不能单次独立重放；发布资产不等于全链复现。 |
| **R3 Qwen3-Coder-Next** | `T,A`：实际 agentic training、约 800k 可执行任务、tool-format diversity 受控分析和开放权重。 | 完整数据生产和训练资源未公开；跨 scaffold transfer 仍有限。 |
| **R4 MiniMax-M2** | `T`：官方模型系列报告支持确实进行 agentic data pipeline 与训练。 | 对每个 pipeline 组件的因果消融不足；无独立复现。 |
| **R5 GLM-5 / 5.2 / 5.3** | GLM-5 报告支持实际模型训练、异步 RL infra 与开放模型/部分代码。 | 后续博客若无训练细节或受控实验，只能算官方产品/能力主张；不能据此推断所有 `slime` 特性都用于旗舰训练。 |
| **R6 DeepSeek V3.2 / V4** | `T`：V4 技术报告支持两种 MoE 规模、32T+ pretraining 和完整 post-training 主张、checkpoint release。 | 后训练数据组成、逐阶段资源和失败实验不完整；无独立复现。 |
| **R7 Kimi K2 / K2.5** | `T`：官方技术报告与开放权重支持模型已实际训练。 | 不提供本项目可直接复用的完整 agentic RL recipe 或受控链路归因。 |
| **R8 MiniMax-M1** | `T,A`：长上下文/软件环境 RL、CISPO，披露 512×H800、约三周及估算租赁成本。 | 规模与本项目不匹配；独立复现缺失。 |
| **R9 Composer 2** | `T`：官方报告支持 continued pretraining 与 Cursor harness 内的大规模 RL。 | 主要训练环境和 CursorBench 私有，外部难以审核训练—评测接口耦合。 |
| **R10 ROME / Let It Flow** | `C,T`：报告支持百万级轨迹、ROLL/ROCK/iFlow 生态和实际 agentic 模型训练。 | 无独立端到端复现；生态存在不代表所有组件都必要。 |
| **R11 RollArt** | `C,A`，并有大规模训练使用主张：支持 disaggregated agentic RL 与 1.35–2.05× 训练时间改善。 | 主要是系统吞吐证据，不是能力因果结论；旗舰使用主张尚无独立复核。 |
| **R12 ROLL** | `C`：真实框架和配置能力。 | 框架支持某算法，不等于旗舰模型使用；代码路径本身不构成 `T/A`。 |
| **R13 Kimi K3** | `T`：官方技术报告和开放模型支持确实训练。 | 不能从高 benchmark 分数反推具体 post-training 机制；无独立复现。 |
| **R14 CompactionRL** | `T,A`：真实模型训练、summary loss 和 cross-trajectory GAE 消融。 | 不支持“所有接口下普遍提升”；30B no-compaction 条件存在明显回退；公开训练代码状态不明确。 |
| **R15 SAO** | `T,A`：报告支持 Qwen3-30B-A3B 上长程稳定训练和 clipping/importance-sampling 分析。 | 没有找到对应开放实现；它是优化组件，不足以形成完整能力闭环。 |

### 4.2 Seed 中主要是代码能力或官方主张的项目

`slime`、`verl`、`verifiers`、`prime-rl`、ROLL、ROCK、AgentEnv、NeMo RL、DataDesigner 等，首先证明的是 `C`。它们可以成为后端或环境生产组件，但不单独证明模型能力收益。Seed 对这一点的警告是正确的。

而且实际 commit 表明，成熟框架仍会出现训练语义 bug：completed group 被丢弃、reward 与错误 DP sample 关联、resume 时未来 trace 与新 policy 混合、合法相同请求被误当 stale replay。这进一步说明“能够运行”和“训练正确”是两个证据等级。  

OpenCode 没有被用作承重证据：seed 未冻结其 commit 和 license；本轮虽然确认当前入口指向公开项目，但没有为本项目建立足够严格的固定 revision、授权和训练结果链，因此维持“待核验”状态。

### 4.3 Seed 外的新方向与新来源

明确不只是 seed 换名的候选至少包括：

1. **Solver-relative learnability 作为任务资格门**：CalibForge；
2. **对抗式 verifier hardening 直接决定训练资格**：Hardening、BenchJack、reward-hacking 负结果；
3. **工具故障的 retry/switch/abstain 与事务语义**：BENCH2ROBUST、Verified Tool Calls、AgentAbstain；
4. **Failure-driven curation policy evolution**：CurateEvo、CoEvolve、CLAP；
5. **Executable safety 的 recognition→execution gap**：REDAgentBench、HarnessSafe、ActBench；
6. **Boundary-relative context verifier**：TRACE；
7. **训练系统 provenance/resume/eval handoff 作为正确性研究变量**：近期 `slime`、`verifiers`、`prime-rl` commits。

### 4.4 经核验后被降级或排除为顶层方向的线索

- **SAO 或另一种 GRPO 变体**：可作为优化组件；没有独立能力命题、任务/环境和 held-out 闭环时不独立立项。
- **LongHorizon-Harness**：公开 harness、manager/executor/auditor 设计和推理结果，但项目明确不训练新模型；作为 inference scaffold 或数据生成组件，不是当前顶层训练方向。
- **BenchJack、Meerkat、HackDetect**：是强 audit/benchmark 组件；若不与资格门和训练实验结合，不构成 agentic post-training 项目。
- **VerMem 的“长期记忆”宽泛表述**：当前训练 episode 的 memory state 独立初始化，证据只支持任务内 episodic/context management，不支持跨用户、跨会话的 lifetime memory。
- **BENCH2ROBUST 的“abstain”宽泛表述**：当前正证据主要是 retry/switch 和 budget exhaustion；没有充分正向训练不可解时的 calibrated abstention。
- **OpenEnv/通用 environment protocol**：互操作性重要，但协议存在本身不证明模型能力。
- **AutoTrainess / PostTrainBench**：研究对象是“coding agent 是否能自动替小模型做 post-training”，不是本项目目标模型的 agentic 能力；可借鉴实验管理 harness，但不作为顶层候选。PostTrainBench 的核心设置是单 H100、10 小时、4 个小模型和 7 个 benchmark。
- **OpenFinGym**：是值得关注的非 SWE 可执行环境和 host-side verifier 资产，但“换到金融数据集”本身不是研究命题。
- **只有产品宣传的新版本**：没有训练细节、对照和可复核轨迹时，统一降为官方主张，不作为承重证据。

---

## 5. 证据附录

下面只列承重来源。`origin` 表示其进入本轮证据图的方式，不表示论文作者是否引用过 seed。

### 候选 1：任务可学习性校准

- **CalibForge: Adversarial Solver Calibration for Scaling Learnable Terminal Tasks**  
  URL：<https://arxiv.org/abs/2608.06352>  
  日期/版本：v1，2026-08-06。  
  定位：Algorithm 1；§2.3；Table 1、Table 3；Figure 8–9；Appendix B–F，尤其 Table E1。  
  `origin: independent_search`；`C△ T✓ A✓ R–`。

- **CalibForge 官方仓库**  
  URL：<https://github.com/AweAI-Team/CalibForge>  
  核验：2026-08-18；README、HF dataset/models、AweAgent eval recipe。  
  支持数据、模型和评测入口；本轮未找到完整 calibration/training pipeline。  
  `origin: independent_search`；`C△`。

### 候选 2：Verifier hardening 与训练资格

- **Hardening Agent Benchmarks with Adversarial Hacker-Fixer Loops**  
  URL：<https://arxiv.org/abs/2606.08960>  
  日期/版本：v1，2026-06-08。  
  定位：主实验；raw hardening 负结果；Appendix D.9、E、F。  
  `origin: independent_search`；`C✓ T– A✓ R–`。

- **官方代码**  
  URLs：<https://github.com/few-sh/harden-v0>；<https://github.com/few-sh/terminal-wrench>  
  定位：hacker/fixer/solver loop、attack hints、environment patches。  
  `origin: independent_search`；`C✓`。

- **Reward hacking 负结果**  
  URL：<https://arxiv.org/abs/2606.15385>  
  代码：<https://github.com/asparius/verl-agent-safety>  
  定位：observed reward 与 hidden objective gap；credit/exploration/entropy 对照。  
  `origin: independent_search`；`C✓ T✓ A✓ R–`。

- **BenchJack**  
  URL：<https://github.com/benchjack/benchjack>  
  定位：scanner、`audits/`、八类 verifier vulnerability；README limitations。  
  `origin: independent_search`；`C✓ T– A✓ R–`。

### 候选 3：跨 harness 语义不变性

- **The Interplay of Harness Design and Post-Training in LLM Agents**  
  URL：<https://arxiv.org/abs/2606.25447>  
  定位：§3.2–3.4；§4.2–4.4；Figure 3–4；Appendix C/D；compute remark。  
  `origin: provided_seed`；`T✓ A✓ R–`。

- **Polar / ProRL-Agent-Server**  
  URLs：<https://arxiv.org/abs/2605.24220>；<https://github.com/NVIDIA-NeMo/ProRL-Agent-Server>  
  定位：black-box harness proxy、token reconstruction、trajectory reconstruction ablation。  
  `origin: provided_seed`；`C✓ T✓ A✓ R–`。

- **Qwen3-Coder-Next**  
  URL：<https://arxiv.org/abs/2603.00729>  
  定位：Figure 3；§4.2.2；Table 2；tool format/template diversity。  
  `origin: provided_seed`；`T✓ A✓ R–`。

### 候选 4：可验证 context / memory

- **TRACE**  
  URLs：<https://arxiv.org/abs/2608.06503>；<https://github.com/nokia-applied-research/Trace>  
  日期：v1，2026-08-06；仓库创建 2026-08-05。  
  定位：paired PRE/POST continuation；`trace_cc/verifier.py`、`collect/boundaries.py`、`optimize/loop.py`、590-boundary cohort。  
  `origin: independent_search`；`C✓ T– A✓ R–`。 

- **Verifiable Memory**  
  URLs：<https://arxiv.org/abs/2608.03137>；<https://github.com/Sun-SYSU-24/VerMem>  
  日期：v1，2026-08-04。  
  定位：七类 memory operation、三阶段 curriculum、local/global verifier；代码路径 `00_verifiers/` 至 `04_training/`。  
  `origin: independent_search`；`C✓ T✓ A✓ R–`，但复现资产不全。 

- **ACM: Agentic Context Management for Long-Horizon Tasks**  
  URLs：<https://arxiv.org/abs/2607.23809>；<https://github.com/lixiaochuan2020/agentic-context-management>  
  日期：2026-07-26。  
  定位：paper Table 2–3；仓库 `src/teacher_guide/`、`distill/`、`train/`、pipeline config；off-policy cache caveat。  
  `origin: independent_search`；`C✓ T✓ A✓ R–`。 

- **CompactionRL**  
  URL：<https://arxiv.org/abs/2607.05378>  
  日期：v1，2026-07。  
  定位：§5.3；Table 3–4；single/compacted/long context 对照。  
  `origin: provided_seed`；`T✓ A✓ C=unknown R–`。

- **Proactive Memory Agent**  
  URLs：<https://arxiv.org/abs/2607.08716>；<https://github.com/yifannnwu/proactive-memory-agent>  
  定位：selective intervention、Terminal-Bench/τ²、SFT+GRPO 训练主张；公开仓库主要是 inference runner/config/examples。  
  `origin: independent_search`；论文 `T✓ A✓`，公开 repo `C✓`，训练代码本轮未找到。 

### 候选 5：工具故障恢复与停止

- **Retry, Switch, or Abstain? / BENCH2ROBUST**  
  URL：<https://arxiv.org/abs/2608.11977>  
  日期：2026-08-12。  
  定位：failure taxonomy；Table 1–2；BTM/RL 组合；S3 与 abstention 限制。  
  `origin: independent_search`；`T✓ A✓ C– R–`。

- **Verified Tool Calls Under Non-Atomic Failures**  
  URL：<https://arxiv.org/abs/2608.02645>  
  日期：v1，2026-07-31。  
  定位：postcondition verification、verify-before-retry、idempotency keys。  
  `origin: independent_search`；`T– A✓ C=unknown R–`。

- **AgentAbstain**  
  URL：<https://arxiv.org/abs/2607.10059>  
  日期：2026-07-11。  
  定位：263 paired act/abstain tasks、42 sandboxes、17 models、4 harnesses。  
  `origin: independent_search`；`T– A✓ R–`。

### 候选 6：能力整合与保持

- **MOPD**  
  URL：<https://arxiv.org/abs/2606.30406>  
  定位：Table 3–4；§4.4.2；cross-origin teacher collapse 与能力回退。  
  `origin: provided_seed`；`T✓ A✓ C=unknown R–`。

- **MAI-Thinking-1 官方报告**  
  URL：<https://microsoft.ai/pdf/mai-thinking-1.pdf>  
  定位：Figure 12；specialist/distillation/final RL；environment builder；numerical self-distillation。  
  `origin: provided_seed`；`T✓ A✓ C– R–`。

- **NVIDIA Nemotron 3 Ultra Technical Report**  
  URL：<https://research.nvidia.com/labs/nemotron/files/NVIDIA-Nemotron-3-Ultra-Technical-Report.pdf>  
  定位：post-training/MOPD、safety teacher、evaluation tables。  
  `origin: provided_seed`；`C△ T✓ A✓ R–`。

- **RL Forgets! / CPO**  
  URL：<https://arxiv.org/abs/2607.04364>  
  代码：<https://github.com/MaolinLuo/CPO>  
  定位：continual policy optimization、multimodal forgetting。  
  `origin: independent_search`；`C✓ T✓ A✓ R–`。

### 候选 7：可执行安全

- **REDAgentBench**：<https://arxiv.org/abs/2608.10669>，2026-08-11；service receipts、recognition-action gap。`origin: independent_search`；`T– A✓ R–`。
- **HarnessSafe**：<https://arxiv.org/abs/2608.06984>，2026-08-07；persistent carriers across memory/skills/tools/artifacts。`origin: independent_search`；`T– A✓ R–`。
- **ActBench**：<https://arxiv.org/abs/2608.09476>，2026-08-10；600 cases、48 APIs、dual-evidence evaluation。`origin: independent_search`；`T– A✓ R–`。

### 候选 8：异步训练正确性

- `slime` completed-group 丢弃修复：  
  <https://github.com/THUDM/slime/commit/7e02052ee454736228464f2f167b0e889c44f10c>  
  路径：`slime/rollout/fully_async_rollout.py`、`tests/test_fully_async_rollout.py`。  
  `origin: both`；`C✓ T–`。

- `slime` reward/sample DP 错配修复：  
  <https://github.com/THUDM/slime/commit/c1dd9ab2422326f97590577ddd7fe3c934dc0c20>  
  路径：`slime/backends/megatron_utils/data.py`、`slime/utils/data.py`。  
  `origin: both`；`C✓ T–`。

- `verifiers` run lineage/config hash：  
  <https://github.com/PrimeIntellect-ai/verifiers/commit/91a267616d409b9538c4424ba9b2fbec829d1b13>  
  `origin: independent_search`；`C✓ T–`。

- `verifiers` retry identity：  
  <https://github.com/PrimeIntellect-ai/verifiers/commit/be6faf6d684f7f191de2414e244949f205cb7b93>  
  路径：`verifiers/v1/interception/server.py`。  
  `origin: independent_search`；`C✓ T–`。

- `prime-rl` online eval/checkpoint handoff：  
  <https://github.com/PrimeIntellect-ai/prime-rl/commit/15d6c81974c94b2c70db13d0d9cfd502bb6516a6>  
  定位：stable checkpoint、policy version、resume cleaning、multi-node decoupled eval。  
  `origin: independent_search`；`C✓`，仅有 e2e 系统验证，不是模型能力消融。

### 候选 9：边界局部反事实信用

承重来源与候选 4、5 相同：TRACE 的 paired continuation 与 Verified Tool Calls 的 postcondition。当前状态为 `C/A`，尚无“该信用信号改善训练”的 `T/A` 闭环。

### 候选 10：动态 held-out 与回退

- **Why SWE-bench Verified no longer measures frontier coding capabilities**  
  URL：<https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/>  
  日期：2026-02-23；定位：138-task audit、59.4% material issues、contamination discussion。  
  `origin: independent_search`；评测审计 `A✓`。

- **Separating signal from noise in coding evaluations**  
  URL：<https://openai.com/index/separating-signal-from-noise-coding-evaluations/>  
  日期：2026-07-08；定位：SWE-Bench Pro 731 tasks、200 automated flags、249 human labels。  
  `origin: independent_search`；评测审计 `A✓`。

- **Protocol validity / HackDetect**  
  URL：<https://arxiv.org/abs/2607.22368>  
  定位：2,385 traces、15 benchmarks、exposure/reward-hacking audit。  
  `origin: independent_search`；`T– A✓ R–`。

### 候选 11：失败驱动数据策展

- **CurateEvo**  
  URL：<https://arxiv.org/abs/2607.06140>  
  日期：2026-07-07；定位：failed-trajectory-driven executable curation policy、SFT/RL/memory outputs。  
  `origin: independent_search`；论文 `T✓ A✓`，`C– R–`。

- **CoEvolve**  
  URLs：<https://arxiv.org/abs/2604.15840>；<https://github.com/AMAP-ML/CoEvolve>  
  日期：v1，2026-04-17；定位：forgetting/uncertainty-driven task synthesis，AppWorld/BFCL、3 个 Qwen 规模。  
  `origin: independent_search`；论文 `T✓ A✓`，当前公开 repo `C△`，`R–`。

- **CLAP**  
  URL：<https://arxiv.org/abs/2607.01846>  
  日期：2026-07-02；定位：§3.2–3.4；Table 3–4；GRPO KL failure boundary、release/fallback gate。  
  `origin: independent_search`；`T✓ A△ C=unknown R–`。

---

## 初步结论

**高潜力**的五项是：

1. solver-relative 任务可学习性校准；
2. verifier hardening 与训练资格门；
3. 跨 harness/interface 语义不变性；
4. 可验证 context/memory 状态转换；
5. 工具故障下 retry/switch/abstain 策略学习。

其中 1、2、5 明确不是对 seed 中已有算法或框架换名；它们分别把研究对象转向**可学习任务资格、可信反馈资格和故障语义下的策略能力**。6、7、8、11 值得保留，但需要先回答关键可行性或因果问题。9、10 很重要，却更适合作为上述顶层命题的支持机制和可信评测基座，而不是单独以“做一套 infra”立项。

本轮没有任何候选达到 `R`。因此下一轮最有价值的不是继续累积新名称，而是用低成本探针尽快淘汰那些只能在原作者 harness、原 verifier、原数据分布或 inference-time 提示下成立的命题。
