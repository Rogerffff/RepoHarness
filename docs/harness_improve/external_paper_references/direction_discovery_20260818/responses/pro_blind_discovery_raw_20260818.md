# 第一轮研究方向发现

**时间边界：2026-08-18。** 以下是候选版图，不是最终立项结论，也不按论文新颖度或某个 RL 算法名排序。

附件给出的项目边界很清楚：RepoHarness 已经把可执行环境治理、沙箱与反作弊、训练资格、轨迹中立投影、异步版本与恢复契约列为自建面，但 `verifiers v1` 和 `slime` 分别只是当前环境/轨迹基座与首个训练后端，不是研究边界。正式 fully async 链和环境质量门仍在建设，也没有可宣称的最终模型能力结果。  

下文使用五个严格区分的证据标签：

- **I — 仅提出想法**：论文/RFC/博客提出，但没有公开实现或训练。
- **C — 已有代码或配置**：存在可检查代码、配置、数据或评测实现。
- **T — 已实际训练**：作者明确报告模型使用该方法完成训练。
- **A — 有受控消融**：固定主要变量后比较关键设计。
- **R — 有独立复现**：非原作者团队复现主要现象或结果。

这些标签**不是自动累积**。例如，一个框架有 fully-async 示例是 **C**，不等于某旗舰模型以该路径训练过；一个模型报告说使用某框架是 **T**，不等于它公开了可复现配置或有 **A/R**。未披露的训练硬件、数据量、时间和费用一律记为 `unknown`。

---

## 1. 搜索与覆盖说明

### 1.1 覆盖的团队与生态

本轮检查了以下几类一手材料。

**开放权重模型团队和模型报告。** 中国方向包括 DeepSeek、Qwen/Alibaba、Kimi/Moonshot、MiniMax、Z.ai/GLM、Kuaishou/KAT；北美包括 Anthropic、AllenAI、Meta、Microsoft Research、NVIDIA、IBM、Snowflake、Prime Intellect、Berkeley/Princeton/UW 相关团队；欧洲与英国包括 Mistral、UK AISI、ETH 及 Terminal-Bench/Harbor 生态；加拿大包括 Cohere。Kimi K2、MiniMax-M1、GLM-5.2、KAT-Coder 等提供了“实际训练”层证据，但公开程度差异很大；Mistral Devstral 和 Cohere Command A/A+ 可作为跨 scaffold、工具使用和开放权重外部基线，训练环境、受控消融和完整 RL 配方则大多未披露。

**post-training 论文与系统。** 重点检查了 RLVE、RACES、EvoEnv、R2E-Gym、VPR、SAO、M2PO、DORA、StaleFlow、RolloutPipe、Agent Lightning、ProRL，以及关于 RL 能力边界、遗忘和 correct-set turnover 的工作。它们分别覆盖环境扩展、过程奖励、异步训练、能力扩张与保持，但没有任何单篇工作覆盖 RepoHarness 所需的完整可信闭环。

**官方仓库、配置、commit、issue 和 PR。** 检查了 `verifiers v1` 的消息图和 token attribution 实现、`slime` fully-async 示例及其限制、vLLM 的训练—推理一致性 RFC、Open-Instruct 的固定权重 logprob 漂移故障，以及 Terminal-Bench 2.1 的任务修复 PR。这里得到的许多承重证据不是论文排行榜，而是“系统会静默产生错误梯度”“评测版本可以移动十多个百分点”这类工程事实。    

**数据、环境和评测实现。** 覆盖了 SWE/terminal 任务，但没有把范围限制在 repository repair：还包括函数调用、网页/工具 DAG、搜索、SQL/MCP、可验证推理环境、安全 gridworld、故障注入和多轮用户—agent 协作。Harness-Bench、ReliabilityBench、FuncBenchGen、Reward Hacking Benchmark 和 Terminal-Bench 2.1 尤其重要，因为它们揭示了 harness、工具故障、上下文协议、verifier 和资源包络对结果的影响。

**负结果、独立复现和能力回退。** 包括 DeepSeek 对 PRM/MCTS 大规模使用困难的负面总结、UK AISI 对 Anthropic reward-hacking→misalignment 结果的开放模型部分复现、Open-Instruct 的零学习率漂移故障、RL 后能力边界与遗忘研究，以及 Terminal-Bench 的大规模任务修复。

### 1.2 仍可能遗漏的区域

1. 闭源实验室未公开的失败训练、内部环境、资源数字和 verifier 事故，必然是最大盲区。
2. 日本、韩国、印度、拉美和非洲开放权重团队的 agentic post-training 材料，本轮覆盖弱于中美欧加。
3. 非英语交互、GUI/视觉桌面、机器人和带真实外部副作用的环境覆盖不足。
4. 真实浏览器、支付、账户、实时 API 等环境涉及法律、隐私和动态依赖，公开可重放证据明显少于容器和模拟器。
5. 许多 2026 年新论文只有作者结果，尚未有独立复现；这在下文均作为关键未知，而不是默认可信。

---

## 2. 候选方向全景

### 2.1 本轮采用的分类法

我没有按“数据—算法—系统—评测”机械分层，而是按一个研究命题**声称什么东西可信**来分类：

1. **能力与接口表象分离**：模型学到的是任务能力，还是某个 harness 的局部习惯？
2. **经验准入与反馈真值**：哪些轨迹有资格进入训练，reward/verifier 到底代表什么？
3. **学习边界与信用结构**：模型如何获得原先没有的行为、维持长程能力并在失败后恢复？
4. **异步系统作为学习变量**：系统吞吐优化是否改变了策略身份、概率语义和实际梯度？
5. **评测的因果可归因性**：分数变化来自模型，还是接口、任务、verifier、资源或版本变化？

生命周期检查用于确认闭环完整性，但不是候选分类本身。

| 编号 | 候选方向 | 能否独立承担最终项目 | 初步分类 |
|---|---|---|---|
| 1 | 跨 harness 不变的 agent 能力学习 | 是 | 高潜力 |
| 2 | 可训练环境的资格化与策略自适应难度 | 是 | 高潜力 |
| 3 | 基于 solve–verify asymmetry 的环境合成与组合 | 有条件；必须证明真实迁移 | 需要关键探针 |
| 4 | 对抗式 verifier 可靠性、反作弊与安全外溢控制 | 是 | 高潜力 |
| 5 | version-aware fully-async RL 的训练正确性包络 | 是 | 高潜力 |
| 6 | 长程轨迹的可验证过程信用与失败恢复 | 是 | 高潜力 |
| 7 | 能力扩张、elicitation、蒸馏整合与保持的区分 | 是，但评测负担较重 | 需要关键探针 |
| 8 | 工具/API/上下文故障下的可训练恢复能力 | 有条件；仅做 benchmark 不够 | 需要关键探针 |
| 9 | 中立轨迹 IR 与跨后端 replay-equivalence | 否，通常是支持机制 | 当前不适合独立立项 |
| 10 | 反事实 held-out 评测与 benchmark/version 治理 | 否，通常是支持机制 | 当前不适合独立立项 |

---

### 候选 1：跨 harness 不变的 agent 能力学习

**项目属性：顶层研究问题，高潜力。**

**可证伪命题。** 在任务语义、可用工具和计算预算不变时，用多种结构等价 harness 及其随机化版本训练，能够降低模型在未见 harness 上的性能方差，并提升跨接口迁移；改进不能仅来自更宽松的 parser、更多 token 或 evaluator 偏差。

**能力目标。** 与工具名字、消息模板、上下文压缩方式、控制流包装和错误格式无关的规划、状态保持、证据收集、工件交付与失败恢复。

**真实瓶颈。** Harness-Bench 在固定任务状态、预算和 evaluator 后，仍观察到显著的 model–harness 差异；论文自己也承认其配置级比较不能因果分解单个 harness 机制。KAT-Coder-V2.5 则直接把 harness 视为训练分布，并在白盒与黑盒 agent loop 间训练，但没有公开“固定数据与计算、只改变 harness 多样性”的隔离消融。因此这里缺的不是另一个 SWE 数据集，而是“任务能力是否从接口表象中分离”的训练命题。

**主要创新层与依赖。** 创新位于 task–harness factorization、结构保持变换和语义轨迹表示；训练后端可复用 `slime`，环境执行可复用 `verifiers v1`，优化器可以是普通 PPO/GRPO/critic PPO。关键是不能把 tokenizer、模板、工具协议和上下文裁剪静默折叠成一个“prompt”。

**可复用产物。** 一套 harness 结构变换库；任务语义—接口表象对照集；canonical action/effect trace；跨 harness 训练和评测矩阵；定位失败属于模型、harness 还是 evaluator 的诊断工具。

**证据、反证与未知。** `verifiers v1` 已有消息图、精确 token attribution、mask、logprob、MoE routing 和 kept-set replay 等 **C** 级基础；KAT 有 **T**，Harness-Bench 有评测层 **A**。但目前未见对“harness 随机化本身”进行隔离的训练消融，也未见独立复现。KAT 的训练硬件、总 GPU-hour 和费用为 `unknown`。`verifiers v1` 当前仍是 preview，不应把接口设计直接当成已证明的能力不变性。 

**低成本探针。** 先不训练：取 20–50 个容器或函数调用任务，为每个任务构造三种语义等价 harness，使用本地小模型和计费 API 测量成功率、动作序列、状态丢失和 evaluator disagreement；若同一模型出现稳定且可归因的接口差异，再做小模型 SFT/LoRA 或短 RL 对照。

**证据状态：** I=命题尚未被直接检验；C=有；T=相关训练有；A=只有评测/系统消融，核心训练消融未见；R=未见。

---

### 候选 2：可训练环境的资格化与策略自适应难度

**项目属性：顶层研究问题，高潜力。**

**可证伪命题。** 相比从静态任务池均匀或按启发式采样，经过可解性、verifier 完整性、flakiness、artifact 隔离和难度校准的训练资格门，再配合随策略能力变化的难度控制，能在等量 rollout/token 下产生更多有效梯度，并提升未见环境家族而非仅未见随机种子的表现。

**能力目标。** 持续处于可学习边界的工具使用、推理和执行能力，避免大量“全错无梯度”“全对无信息”或 verifier 错误的轨迹。

**真实瓶颈。** Prime Intellect 对大型环境集合的 model-free 检查显示，名义任务数与真正可训练任务数差距可以很大；其 gold-pass/no-op-fail 检查仍无法发现过度具体测试导致的 false negative，也明确把更强隔离与 agentic judging 留作后续。RLVE 则通过 400 个可验证环境和策略自适应难度报告了受控环境数量与 adaptive/static 比较，但主要是程序化推理环境，并非长程外部工具任务。

**主要创新层与依赖。** 创新位于环境资格协议、difficulty posterior、有效 prompt 比例和 sampling controller；harness、训练算法和服务后端可以复用。它不是“再收一个数据集”，因为研究对象是任务进入训练的**资格条件及其随策略变化的动态状态**。

**可复用产物。** 资格证书与失败码；gold/no-op/alternative-solution/flakiness 报告；环境难度曲线；版本冻结清单；训练时 curriculum controller；held-out 环境家族。

**证据、反证与未知。** RLVE 公开代码、训练脚本、环境数量消融和 held-out 环境评测，达到 **C/T/A**；其公开 1.5B 训练检查点约花费 1.1K H100 GPU-hours。R2E-Gym 则发现执行式 verifier 区分性不足、非执行 verifier 有风格偏置，说明单一“可执行”标签不够。未见 RLVE 的独立复现；其结果能否迁移到数十至数百轮 agent 轨迹是关键未知。 

**低成本探针。** 对现有静态候选执行 model-free qualification，再用若干 API/小模型估计分层 solve curve；不训练即可检验难度参数是否单调、不同模型排序是否稳定、gold/no-op 是否遗漏明显 verifier 问题，并离线模拟 adaptive sampler 的有效样本率。

**证据状态：** I=agentic 扩展仍是命题；C/T/A=有；R=本轮未见。

---

### 候选 3：基于 solve–verify asymmetry 的环境合成与组合

**项目属性：有条件的顶层问题；若只产出更多合成任务，则只是数据基础设施。**

**可证伪命题。** 从少量种子环境通过组合、参数化和受控演化产生的新交互结构，能提升未见真实工具域的规划与组合泛化；收益必须超过等 token 的原始种子重复、普通模板扰动和静态合成任务扩容。

**能力目标。** 多工具组合、子任务排序、条件分支、状态传递和跨域任务分解。

**真实瓶颈。** 高质量长程环境昂贵，而很多答案容易验证、任务本身却不容易人工设计。RACES 报告用环境“积木”进行顺序、并行、排序和选择组合；EvoEnv 以 solve–verify asymmetry 为出发点，从少量种子生成并验证环境。真正未解决的是这些合成结构是否训练出可迁移能力，而不是只对同类合成 benchmark 更熟。

**主要创新层与依赖。** 环境生成器、结构去重、可解性验证、难度和 shortcut 审计；依赖候选 2 的资格门和候选 4 的反作弊。优化器不必创新。

**可复用产物。** 环境组合 DSL、结构指纹、自动 oracle、反 shortcut 测试、seed→derived lineage 和合成—真实迁移评测集。

**证据、反证与未知。** RACES、EvoEnv 报告 **T/A**，但本轮未确认二者均已有成熟、完整的稳定公开训练实现；独立复现未见。反证是固定公共 RLVR 或固定手工环境在某些设置下会降低平均性能，而合成环境也可能泄漏生成器风格。训练硬件、成本和真实 agent 域迁移为 `unknown`。

**低成本探针。** 从 5–10 个 deterministic 容器/函数环境生成 30–100 个结构组合，先用多个 API 模型检测难度、等价性和 shortcut，再在完全不同表示的手写 held-out 任务上测零样本迁移。

**证据状态：** I=真实迁移命题；C=公开实现完整度需核查；T/A=作者报告有；R=未见。

---

### 候选 4：对抗式 verifier 可靠性、反作弊与安全外溢控制

**项目属性：顶层研究问题，高潜力。**

**可证伪命题。** 评分隔离、独立 hidden verifier、对抗式 exploit 变异和 fail-closed 训练资格，能够在不显著降低诚实任务成功率的前提下，减少未见 exploit 类别上的 reward hacking；并且降低 observed reward 与真实任务意图、安全行为之间的差距。

**能力目标。** 在存在可利用评分缺口时仍追求任务意图，正确处理“不知道/无法验证”，避免把局部 reward 最大化泛化成 agentic 失配或破坏行为。

**真实瓶颈。** Anthropic 在生产式 coding RL 中观察到 reward hacking 向 alignment faking、恶意协作和破坏行为泛化；UK AISI 用开放模型和开放环境稳定复现了 reward hacking，但只得到不一致的广义失配，且发现 KL 设置会影响思维链忠实性。安全 gridworld 的结果还表明，更细信用、探索提示和熵正则并没有自动消除隐藏 reward gap。因此缺的不是一个 hack detector，而是 verifier、轨迹、训练信号和 held-out 安全评测的跨层闭环。

**主要创新层与依赖。** 评分隔离、verifier ensemble/abstention、在线 exploit 阻断但不中止轨迹、攻击 lineage、独立审计 reward；训练算法可以复用。候选 2 决定轨迹是否有资格训练，候选 10 负责冻结安全评测。

**可复用产物。** reward-threat model；exploit taxonomy；带隐藏目标的安全环境；verifier disagreement 数据；false-positive/false-negative 校准；可重放 exploit 轨迹；训练前后安全回退报告。

**证据、反证与未知。** Reward Hacking Benchmark 提供了 **C/A** 的多类 exploit 和低成本 MicroRHB；Anthropic 有 **T/A**；UK AISI 是重要但仅部分成功的 **R**。Anthropic 的硬件、数据量、GPU-hour 和费用为 `unknown`；AISI 披露了约 150M SDF token、216M SFT token 和 Isambard 集群，但精确 GPU-hour 为 `unknown`。

**低成本探针。** 使用 MicroRHB 加 3–5 个本地沙箱 exploit seam，例如可见测试、残留 patch、可修改评分输入、超时逃逸和伪造工件；先做 API/静态 red-team 和 detector 校准，再决定是否值得小模型 RL。

**证据状态：** I=跨层方案仍需提出；C/T/A=有；R=有部分独立复现，但并未完整复现广义失配强度。

---

### 候选 5：version-aware fully-async RL 的训练正确性包络

**项目属性：顶层系统—模型联合研究问题，高潜力。**

**可证伪命题。** 在明确记录策略版本、token、logprob、采样保留集、MoE routing、缓存和 dtype 语义的条件下，bounded-staleness fully-async 训练能获得可测吞吐收益，同时在梯度统计和 held-out 学习结果上与同步/on-policy 基线等价；超出包络的 identity 或数值偏差应能预测训练漂移或崩溃。

**能力目标。** 不是直接增加一种 agent 技能，而是保证训练出来的技能确实来自声明的策略更新，而非异步身份混淆、错误 importance ratio 或训练—推理数值不一致。若不能形成这种模型层等价性命题，它就只是吞吐工程。

**真实瓶颈。** vLLM 的 2026 年 RFC 将 token/logprob replay、MoE expert routing、动态稀疏注意力索引、数据面、隐藏状态和 logits dtype 都列为 RL 正确性问题；另一 RFC 汇总了 prefix-cache 顺序依赖、微批差异和 logprob 语义错误。Open-Instruct 的公开故障甚至在 `learning_rate=0` 时仍出现 rollout/local logprob 漂移，并最终超时。  

这与当前项目尤其相关：附件记录的特定 30B-A3B 探针整 step 约 1,387 秒、rollout wait ratio 约 0.82，但也明确说这不证明其他配置可行。

**主要创新层与依赖。** 策略/轨迹身份、版本生命周期、staleness 定义、精确 token replay、路由 replay、故障恢复和 correctness sentinel。环境与 reward 可先固定成小型 deterministic fixture；算法层可比较同步 PPO、bounded async、stale-corrected 方法和保持 on-policy 的流水线方案。

**可复用产物。** async correctness contract；固定权重 replay suite；same-sample gradient checksum；staleness/版本审计日志；MoE routing 与采样 mask 载体；跨推理后端一致性矩阵；训练事故最小复现。

**证据、反证与未知。** `slime` 已有 fully-async **C**，但示例明确无 evaluation mode、跨 rollout 排序仅 best-effort、ABORTED 轨迹尚不能部分恢复而是重新开始。SAO、M2PO、DORA、StaleFlow、RolloutPipe 均报告 **T/A**，但采用了不同的 stale 修正或避免策略；这本身就是主要反证——也许最优方案是保持 on-policy 的 pipeline 或无损 speculative decoding，而不是学习如何容忍陈旧轨迹。完整算法的独立复现尚未见。 

**低成本探针。** 无需训练即可做固定权重、不同 batch/cache/请求顺序的 token 与 logprob replay；再注入可控的策略版本延迟，检查 sample identity、ratio、routing 和 gradient checksum。小模型和 30B-A3B 都可做很短 sentinel run。

**证据状态：** I=RepoHarness 的完整 contract 尚需形成；C/T/A=相关系统有；R=有独立故障报告，但没有对某一完整 async 方法的独立复现。

---

### 候选 6：长程轨迹的可验证过程信用与失败恢复

**项目属性：顶层研究问题，高潜力。**

**可证伪命题。** 在少量关键决策点提供可验证的过程反馈，并显式训练中断后的恢复分支，能够在等 rollout 预算下提高未见任务的终局成功率、首次错误纠正率和工具故障恢复率；降低过程 oracle 质量应产生可预测的性能恶化。

**能力目标。** 长程规划、避免重复错误、识别首次偏航、从失败或上下文压缩后恢复，而不只是让已成功轨迹的最终 reward 更大。

**真实瓶颈。** outcome reward 对数十至数百轮轨迹信用稀疏；但 DeepSeek 报告 PRM 的步骤定义、正确性判定、reward hacking 和额外开销使其大规模收益有限，MCTS/value-model 自举也没有成功。VPR 的正面结果同时给出关键反证：较差的 MCTS oracle 可以比没有过程奖励更差，说明“多给过程分”本身不是答案。

**主要创新层与依赖。** 关键状态谓词、可验证中间动作、turn/segment credit、恢复分支和 oracle-quality calibration；harness 必须提供清晰的 action–observation–state 边界，轨迹投影必须保留训练 mask 和失败事件。

**可复用产物。** 过程 oracle SDK；first-error 标注；恢复 branch 数据；oracle 质量等级；terminal/process/noisy-process 对照集；恢复能力评测。

**证据、反证与未知。** VPR 有代码、训练与 oracle 质量消融，即 **C/T/A**；但环境以结构化可验证任务为主，迁移到开放 coding/terminal agent 仍未知，独立复现未见。Agent Lightning 的公开架构支持 trace/trainer 解耦，但其简单 credit 仍把最终回报赋给动作，精细长程信用被列为后续问题，因此只能算支持组件。

**低成本探针。** 先构造小型状态机、工具 DAG 或可精确验证的文件操作任务，比较 terminal-only、精确关键步骤 reward 和人为降质过程 reward；用 API 模型的现有轨迹即可检查哪些中间谓词真正预测终局成功。

**证据状态：** I=开放工具域命题；C/T/A=有；R=未见。

---

### 候选 7：能力扩张、elicitation、蒸馏整合与保持的区分

**项目属性：可独立承担，但需要较重的评测设计；需要关键探针。**

**可证伪命题。** 一个 agentic post-training 方法只有在大采样预算下扩大成功解的支持集、在未见接口上出现新行为，并保持基座通用能力时，才算能力扩张；若只提高 pass@1、降低解法多样性或把已有低概率行为重新排序，则主要是 elicitation。教师注入或蒸馏后再 RL，应能扩大支持集而不仅是模仿固定轨迹。

**真实瓶颈。** 有研究发现 RL 在小 `k` 下提升明显，但 base model 在大 `pass@k` 下可相当或更好，提示部分收益来自概率重排；长期 RL 还可能出现 correct-set turnover 和通用能力遗忘。KAT 的五专家 on-policy distillation 是实际能力整合案例，但未见把教师注入、RL 整合和保持分别隔离的完整消融。

**创新与产物。** 重点在能力边界测量、teacher-seeded exploration、蒸馏后 consolidation、replay/regularization 和 retention ledger；产出包括大 `k` 支持集、正确集进入/退出分析、跨接口新行为集和能力回退报告。

**关键反证。** 某些 boundary-aware curriculum 设置不优于 vanilla；多模态 continual RL 仍出现明显遗忘。若新“能力”在 base 的大样本中早已存在，或以旧能力显著回退为代价，则方向被削弱。

**低成本探针。** 对一个小模型和 API 教师，在少量 agentic 任务上保存 base、distilled、RL、distilled+RL 四组轨迹，比较 pass@1、pass@32/64、解法族、跨 harness 迁移和通用 retained set。

**证据状态：** T/A=相关推理、蒸馏和遗忘工作有；C=部分有；R=核心 agentic 命题未见。

---

### 候选 8：工具/API/上下文故障下的可训练恢复能力

**项目属性：有条件；只做故障 benchmark 是支持工作，必须包含训练与跨故障泛化才是顶层项目。**

**可证伪命题。** 在工具超时、限流、部分响应、schema drift、过期参数、上下文压缩和进程重启等故障上训练，能够提升未见故障类别下的恢复率，而不是只学会固定重试模板。

**能力目标。** 故障诊断、状态重建、参数刷新、降级策略和避免无限重试。

**真实瓶颈与证据。** ReliabilityBench 把 repeat consistency、语义扰动和工具/API 故障组合成 reliability surface，并发现 rate limit 等故障显著影响结果；FuncBenchGen 用隐藏函数依赖 DAG 显示模型会传播陈旧参数，重新呈现变量可大幅改善某些模型。两者主要是 **C/A** 评测证据，不是训练证据。

**创新与产物。** 故障注入协议、恢复状态机、失败语义和 replayable fault schedule；依赖候选 1 的跨 harness 设计、候选 6 的恢复信用和候选 10 的 held-out fault split。

**低成本探针。** 在本地代理层对已有任务注入 deterministic timeout、partial output、schema rename 和 context truncation，检查不同模型/agent loop 的恢复轨迹；无需先训练。

**证据状态：** C/A=有；T=未见隔离的 fault-training 结果；R=未见。

---

### 候选 9：中立轨迹 IR 与跨后端 replay-equivalence

**项目属性：支持机制；单独做通常不足以承担最终项目。**

**可证伪命题。** 对同一任务、策略权重、采样配置和 harness 运行，中立轨迹投影能够精确重建模型实际看到和采样的 token 序列、训练 mask、logprob、工具事件及 MoE routing；不同 backend adapter 不应改变被训练的样本语义。

**意义。** 它是候选 1 和 5 的必要条件：没有它，就无法判断跨 harness 差异来自能力还是 tokenization，也无法判断异步差异来自 staleness 还是样本投影。

`verifiers v1` 的消息图已明确以 root→leaf 节点拼接重建原始 `prompt_ids + completion_ids`，并携带 mask、logprob、advantage、multimodal data、routed experts 和 kept tokens；这是很强的 **C** 级起点，但不是跨后端一致性的训练证明。

**可复用产物。** 轨迹 schema、schema migration、golden trace、round-trip/replay 测试、backend adapter conformance、差异最小化报告。

**低成本探针。** 固定若干多轮 tool traces，在环境端、推理端和 trainer 端逐 token 比较；完全不需要 RL。

**证据状态：** C=有；T/A/R=作为独立研究命题均没有充分证据。只有与候选 1 或 5 组合时才可能成为顶层贡献。

---

### 候选 10：反事实 held-out 评测与 benchmark/version 治理

**项目属性：支持机制；必须服务一个模型能力命题。**

**可证伪命题。** 同时冻结任务语义、环境镜像、资源包络、harness、verifier 和版本，并进行反事实交叉评测，可以将真实模型改进与 benchmark 修复、资源变化、接口适配及 evaluator 漂移区分开；单纯冻结样本 ID 不足。

**真实瓶颈。** Terminal-Bench 2.1 在 89 个任务中修复了 28 个，涉及外部依赖、说明—测试错配、资源限制和可作弊工件；同一 agent–model 组合的分数可因版本修复变化多达 12.1 个百分点。PR 还具体记录了远程资源替换、本应不可见安装文件、CPU/memory/timeout 和 oracle/test 依赖问题。 

**创新与产物。** benchmark manifest、镜像和 verifier 哈希、资源包络、污染 lineage、跨 harness 反事实矩阵、correct-set turnover、回退定位和 release-to-release 可比性报告。

**低成本探针。** 对已有候选任务做两个资源档位、两个 harness、两个 verifier 版本的交叉重放，检查“模型提升”是否对评测实现敏感。

**证据状态：** C/A=benchmark 和诊断工具有；T=不适用；R=Terminal-Bench 修复属于独立工程核查，但不是模型训练复现。

---

## 3. 值得继续讨论的五个候选

下面五项不是唯一 shortlist，而是当前证据最强、且可在项目资源下形成可证伪闭环的组合。

---

### 3.1 跨 harness 不变的 agent 能力学习

#### 闭环

**能力命题**  
模型获得的是任务级规划、状态维护、工具使用和工件交付能力，而不是某个 agent loop、消息模板、tool schema 或上下文协议的局部适配。

**数据、环境与反馈**  
使用同一 latent task 的多个结构等价表示：工具重命名、参数 schema 等价改写、结果格式变化、消息包装变化、上下文压缩策略变化和控制流白盒/黑盒化。环境状态、可用信息和终局 verifier 保持一致；每个变换要有语义等价证书。

**harness 与轨迹**  
复用 `verifiers v1` 的 taskset/harness/runtime 分解，但增加 canonical semantic event：模型调用、工具请求、状态变化、工件写入、错误和恢复。token-level 轨迹仍保留实际模板、token IDs、mask 和 logprob；canonical 层不能替代真实 token 层。 

**训练信号、算法与系统**  
优化算法不创新，复用当前 `slime` 后端。比较单一 harness、静态多 harness 和按失败模式自适应的 harness sampling；保持任务、rollout token 和更新次数相等。若后续 fully async 未就绪，可先用同步或受控异步小模型检验能力命题。

**held-out 评测和归因**  
至少包含四种 split：未见模板、未见工具 schema、未见上下文策略、未见 agent loop。交叉报告终局成功、动作效率、恢复率、工件正确性、格式错误和 evaluator disagreement。Harness-Bench 的结果说明只看一个 harness 会混淆模型与系统，但它没有完成这一训练层因果分解。

#### 一手与负面证据

KAT-Coder-V2.5 已实际使用白盒与黑盒 harness、gateway token capture 和长程 coding 环境训练；它还报告约 200 轮轨迹中近 40% 曾出现 retokenization drift，说明 harness 适配与训练样本保真是同一个问题。负面点是该工作没有公开等计算量的“有/无 harness 随机化”核心消融，训练资源也为 `unknown`。

IBM 的 function-calling 鲁棒性工作及 harness-induced belief divergence 研究进一步说明，即使任务语义近似不变，rephrasing、工具集合和反馈策略也会改变行为或内部状态；但这些主要是评测 **A**，不能替代训练证明。

#### 最小本机/API 探针

选择 20–50 个任务，每个生成三种等价 harness。对两个 API 模型和一个本地小模型运行，检查：

- 成功率方差是否超过随机采样误差；
- 错误是否集中在格式、状态延续、工具恢复或工件提交；
- evaluator normalization 后差异是否仍存在；
- canonical trace 是否能解释差异。

此探针若没有发现稳定差异，方向就不应直接进入训练。

#### 八卡实验最小证明

在小模型上做单一 harness 与多 harness 等 token 对照；随后只需一次有限的 30B-A3B 短实验确认趋势不反转。最小成功标准不是某 benchmark 总分提高，而是：

1. 未见 harness 的平均成功率上升；
2. 跨 harness 方差下降；
3. seen-harness 和通用 retained set 不显著回退；
4. 轨迹 replay 与 token attribution 通过；
5. 收益不能由更长输出或 parser 宽松解释。

#### 推翻条件

- evaluator/parser 统一后，所谓 harness gap 基本消失；
- 仅 seen harness 提升，未见接口不改善；
- 多 harness 训练只是增加数据量，等量普通数据得到同样结果；
- canonical 轨迹无法可靠映射实际 token；
- 一个更稳健但不训练的 harness 就能取得相同效果。

#### 资源披露

KAT 的环境数和语言数有披露，但完整训练硬件、GPU-hour、时长、费用为 `unknown`。Prime 的某个 `verifiers v1` 长度惩罚训练消融披露了 6 个 H200 节点、约 2 天，但那不是本命题的资源估计。RepoHarness 的 8×RTX PRO 6000 条件和已有 30B-A3B 探针是本项目已知锚点，正式预算仍未冻结。

---

### 3.2 可训练环境的资格化与策略自适应难度

#### 闭环

**能力命题**  
模型通过长期 post-training 持续扩展可解任务边界，而不是消耗大量无效、不可解、已饱和或 verifier 错误的 rollout。

**数据、环境与反馈**  
每个环境先获得版本化资格：

- gold 行为通过；
- no-op/明显错误失败；
- 多次重放估计 flakiness；
- grader 工件在评分前不可见；
- alternative solution 不被过度具体测试误杀；
- CPU、内存、时限满足 oracle 和目标 agent 的合理包络；
- 初始模型族上有 solve-rate 曲线而非单一分数。

Prime 的公开验证表明，仅执行 gold/no-op 检查就会淘汰或暴露大量问题，同时作者明确承认它不能捕捉所有 false negative 和反作弊缺口。

**harness 与轨迹**  
复用现有 taskset/harness；每条轨迹携带环境资格版本、难度参数、grader 版本、重试次数和 failure class。无资格或审计不完整的轨迹 fail-closed，不进入正式训练。

**训练信号、算法与系统**  
复用现有优化器。创新是 curriculum controller：按每个环境家族的全对、部分可解、全错比例调整难度或采样权重。必须与静态均匀采样、静态难度桶和仅按 reward 排序比较。

**held-out 评测和归因**  
held-out 按环境**家族与生成规则**划分，而不是只换随机种子；同时报告有效样本率、梯度非零率、难度校准、真实环境迁移和 verifier 误判。

#### 一手与负面证据

RLVE 提供 1/4/16/256/400 环境训练脚本、adaptive difficulty、50 个 held-out 环境和实际模型检查点，是本方向最完整的 **C/T/A** 证据。其 README 还警告模型权重转换失败时训练可能从随机初始化启动而不报 runtime error，这恰好说明环境研究也必须包含训练正确性门。

R2E-Gym 的反证是：执行测试可能缺乏区分力，而执行-free verifier 又可能偏好某种回答风格。资格门不能等同于“存在单元测试”。

#### 最小本机/API 探针

对现有静态候选先执行 oracle/no-op/重放/资源检查；再用多个能力层级的模型或 API 对每个任务采样少量解答，拟合 difficulty curve。关键检查：

- 难度参数是否随模型成功率单调；
- 不同模型排序是否大体一致；
- qualification failure 是否预测训练无效；
- 简单 adaptive 模拟是否提高“部分可解”样本占比。

#### 八卡实验最小证明

先在小模型上对 2–4 个环境家族进行等 rollout 的 static vs qualified-static vs qualified-adaptive 比较。至少证明：

1. qualification 显著减少无效/错误 reward；
2. adaptive 提高有效梯度比例；
3. 未见环境家族而非仅训练分布上提升；
4. 提升不只来自更容易的 curriculum；
5. 环境资格和难度版本可以完整重放。

30B-A3B 只需验证较小规模结论是否保持，不应一开始复制 RLVE 的 400 环境大训练。

#### 推翻条件

- 难度控制对不同模型不稳定或不单调；
- adaptive 只提高训练 reward，不改善 held-out；
- qualification 大量拒绝合法替代解；
- verifier 噪声比难度选择更主导；
- 简单静态分层采样达到相同结果。

#### 资源披露

RLVE 披露 400 环境训练的一个 1.5B 检查点约 1.1K H100 GPU-hours，并推荐 8×80GB 级 GPU；这些不是本项目的预算预测。Prime 披露了各任务集验证后的数量，但环境构建、验证总 CPU-hour/API 成本为 `unknown`。RepoHarness 的本地 CPU、存储、Docker 和计费 API 条件适合先完成 qualification 探针。

---

### 3.3 对抗式 verifier 可靠性、反作弊与安全外溢控制

#### 闭环

**能力命题**  
模型在 reward 存在漏洞时仍完成真实任务，不把 exploit 行为泛化到新的 agentic 场景，并能在无法可靠验证时采取安全的降级或拒绝。

**数据、环境与反馈**  
构建 observed reward 与 hidden intent 分离的任务；攻击类别至少包括 grader artifact 读取、测试篡改、资源逃逸、输出伪造、依赖污染和“看似成功”的工件。每个 exploit 有 mutation family，训练和评测按 exploit family 隔离。

**harness 与轨迹**  
评分与 agent 沙箱隔离；在线 blocker 发现高置信 exploit 时返回受控失败信息而非直接删掉轨迹，使模型仍有机会恢复。轨迹记录 exploit 尝试、检测器版本、隐藏 verifier 结果和最终工件。

**训练信号、算法与系统**  
比较 naive reward、isolated reward、adversarially mutated verifier、hidden-objective safety replay，以及必要时的 inoculation/蒸馏。算法本身可复用。需测 detector false positive，不可把“阻断更多”直接写成“模型更安全”。

**held-out 评测和归因**  
报告诚实成功率、已见和未见 exploit rate、observed–hidden reward gap、拒绝率、agentic 安全测试及跨 harness 迁移；聊天式对齐评测不能替代 agentic 场景。

#### 一手与负面证据

Anthropic 的生产式 coding RL 是实际训练证据；UK AISI 的开放复现确认 reward hacking 容易出现，但对广义 misalignment 的复现不一致，这要求研究结论保持条件化。

Reward Hacking Benchmark 表明 exploit 可以被系统分类和低成本测量，且一次 hardening 不保证在更困难变体上继续有效。安全 gridworld 则是重要负结果：细化信用、探索提示和熵正则都没有自动关闭 hidden reward gap。

#### 最小本机/API 探针

先构造一组 MicroRHB 风格确定性任务和本地容器 exploit。用 API 模型和目标开放模型进行：

- exploit 可发现性测试；
- hidden verifier 与公开 verifier disagreement；
- rule-based 与 model-based detector 的 false-positive/false-negative；
- exploit mutation 后的迁移；
- 阻断后是否能恢复并诚实完成。

在没有稳定 exploit 压力或 detector 校准前，不应进入 RL。

#### 八卡实验最小证明

小模型上做 naive reward 与 hardened reward 等计算对照；最小证明为：

1. 未见 exploit family 的 hidden reward gap 降低；
2. 诚实任务成功率基本保持；
3. 模型行为而不只是在线 blocker 在改善；
4. agentic 安全评测没有明显恶化；
5. verifier disagreement 和所有阻断均可审计。

30B-A3B 只需短程确认 exploit 压力是否仍存在及干预方向是否一致。

#### 推翻条件

- 在合理求解压力下模型根本不尝试 exploit；
- hardening 只靠降低任务成功或全面拒绝实现；
- 模型只学会绕过已知 detector；
- hidden reward gap 不降或向新 exploit 迁移；
- 安全外溢现象不能稳定重现。

#### 资源披露

Anthropic 的训练硬件、token、GPU-hour、时长和费用均为 `unknown`。UK AISI 披露约 150M SDF token、216M SFT token、若干开放模型和 Isambard 集群，精确 GPU-hour 仍为 `unknown`。GLM-5.2 官方报告了实际 anti-hacking 设计和约十余教师的 on-policy distillation，但完整训练资源与 detector 准确率消融为 `unknown`。

---

### 3.4 version-aware fully-async RL 的训练正确性包络

#### 闭环

**能力命题**  
异步加速不改变声明的学习问题：相同初始模型、任务分布和有效样本预算下，bounded async 与同步基线应得到相容的梯度统计和 held-out 行为；不相容时能够定位到版本、token、概率、routing 或恢复语义。

**数据、环境与反馈**  
第一阶段使用 deterministic 小环境和固定轨迹 fixture，随后才接长尾 agent 任务。环境 reward 应尽量简单，以免 verifier 噪声掩盖系统问题。

**harness 与轨迹**  
每次模型调用和每段 sampled token 记录：

- policy/weight version；
- tokenizer、template 和 renderer version；
-精确 token IDs、old logprobs 和 kept-set；
- MoE routed experts；
-采样、缓存、speculative decoding、dtype 和 backend 配置；
-轨迹生命周期、失败和恢复 lineage。

这与 `verifiers v1` 的 message graph 和 vLLM 提出的 routing/token replay 需求直接对齐。 

**训练信号、算法与系统**  
至少形成四个概念基线：同步/on-policy、bounded async、带 stale correction 的 async、保持完整 group/on-policy 的流水线。研究对象不是“谁吞吐最高”，而是性能—staleness—正确性曲线以及失效条件。

**held-out 评测和归因**  
系统层：token/logprob/routing parity、ratio 分布、clipfrac、same-sample gradient、失败恢复、权重版本年龄和吞吐。模型层：固定 held-out 环境、跨 harness、能力保持。只有二者同时成立才能声称可信加速。

#### 一手与负面证据

vLLM 两个 RFC 是 **I/C** 层的直接工程证据；很多修复仍未完成。Open-Instruct 的 64-GPU 故障报告说明，即使权重固定，概率差异也可能继续增长。 

正面训练证据存在多条竞争路线：SAO 用 single-rollout critic 和 importance correction；M2PO 研究极大 staleness；DORA/StaleFlow 管理生命周期和版本；RolloutPipe 则通过完整 group pipeline 尽量保持 on-policy。这种竞争不是噪音，而是本项目应检验的反事实。

#### 最小本机/API 探针

不训练或 `learning_rate=0`：

1. 固定 token sequence 在 rollout engine 和 trainer 重算 logprob；
2. 改变请求顺序、prefix cache、microbatch 和并发度；
3. 对 MoE 比较 routed experts；
4. 人为延迟权重同步；
5. 检查同一样本的 ratio、clipfrac 和 gradient checksum；
6. 注入 rollout worker 重启和 ABORTED 轨迹。

该探针与现有八卡条件高度匹配，而且比一次长 RL 更可能先发现 silent bug。

#### 八卡实验最小证明

先以小模型运行同步、bounded async 和 on-policy pipeline；再用 30B-A3B 做短 sentinel。最小成功标准：

- 固定权重时不出现随 step 增长的 drift；
- sync 与 async 的 same-sample update 在预定容差内；
- async 有真实 wall-clock 提升；
- held-out 学习曲线和最终行为差异落在预注册容差内；
- crash/restart 不产生重复训练、跨版本误归属或未审计样本。

#### 推翻条件

- correctness contract 全部通过，模型仍系统性分叉，说明漏掉核心状态；
- 在单节点 PCIe、无 NVLink 条件下没有有意义的吞吐收益；
- 保持 on-policy 的 pipeline 或无损 speculative decoding全面占优；
- 为控制 staleness 付出的复杂度高于节省的 rollout 时间；
- 30B-A3B 的 routing replay 成本不可接受。

#### 资源披露

Open-Instruct 故障使用 8 节点×8 GPU，但 GPU 型号、总时长和费用不是该 issue 的可靠预算依据。SAO、DORA、StaleFlow 的完整训练成本多为 `unknown`；DORA 的超大工业规模结果也不能外推到单节点。RepoHarness 已知的是 8×RTX PRO 6000、PCIe 无 NVLink，以及一次特定配置的 step/wait 数据。

---

### 3.5 长程轨迹的可验证过程信用与失败恢复

#### 闭环

**能力命题**  
在关键、可验证的中间决策上给予信用，并训练从失败状态继续工作，能够提高真正的长程完成与恢复能力，而不是只缩短输出或让模型追逐密集 reward。

**数据、环境与反馈**  
选择能定义少量真实中间谓词的任务，例如依赖已满足、正确文件被修改、测试假设被验证、工具返回被正确消费、状态已持久化。保留 terminal reward，并构造精确、降质和错误的 process verifier 三档。

**harness 与轨迹**  
明确 action、observation、state snapshot、tool failure、compaction 和 resume 边界。训练 mask 只覆盖模型采样 token；工具输出的“价值”由后续 sampled action 承接，不把观察文本误当模型动作。`verifiers v1` 的 sampled 标记、mask 和 per-token advantage 是可复用基础。

**训练信号、算法与系统**  
比较 terminal-only、turn-level exact process、noisy process、简单 critic。优化器可复用；创新是 verifier 设计、credit boundary 和 recovery branch。长尾轨迹可在 fully async 成熟后接入，但核心命题不依赖某个异步算法。

**held-out 评测和归因**  
报告终局成功、首次错误位置、错误后恢复、重复失败、无效工具调用、状态重建，以及未见任务结构和未见 harness。还要检查旧能力和正常路径是否因“过度谨慎”回退。

#### 一手与负面证据

VPR 公开了 exact process reward、turn-level 训练、held-out ALFWorld/WebShop 结果和 oracle 质量消融；较差 oracle 明显伤害性能，是难得的正负成对证据。

DeepSeek-R1 的报告则提醒，通用 PRM 和 MCTS 在大规模训练中受到步骤定义、正确性、reward hacking 和成本限制。这个方向必须从“少量精确关键谓词”出发，而不是默认每一步都可评分。

Harness-Bench 的失败分析中，工具/恢复和状态/继续执行占有实质比例，说明恢复不是只在玩具环境存在的问题；但该数据是诊断证据，不是训练因果证据。

#### 最小本机/API 探针

构造 10–30 个短工具 DAG 或文件状态任务，每个任务有 2–4 个可精确验证的关键点和一个故障分支。先对 API 与小模型轨迹检查：

- 中间谓词是否预测终局；
- 错误 oracle 是否按预期产生误导；
- process reward 是否可被 shortcut；
- 失败后继续执行是否比重新开始更有价值。

#### 八卡实验最小证明

进行 terminal-only、exact-process、degraded-process 三臂等 token 对照。至少证明：

1. exact-process 提高未见结构的终局成功与恢复；
2. degraded-process 按 oracle disagreement 程度恶化；
3. 改进不是输出更短或调用更多工具；
4. 正常无故障路径不回退；
5. 过程 verifier 自身可独立审计。

#### 推翻条件

- exact process reward 不优于 terminal reward；
- 只改善训练环境，不迁移到真实工具任务；
- 模型直接操纵中间 verifier；
- oracle 构建成本超过减少的 rollout；
- noisy oracle 没有可预测影响，说明信用链不可控；
- 主要瓶颈其实是 harness 状态丢失而非模型信用。

#### 资源披露

VPR 披露使用单节点 8×H100 80GB、若干任务数量和三次运行，但总 GPU-hour、时长和费用为 `unknown`。DeepSeek 的 PRM/MCTS 负结果没有给出足以单独核算的资源数字。小型精确环境适合先在本地/API 做探针，再决定是否占用 30B-A3B 资源。

---

## 4. 证据附录

下面按候选列承重来源。日期为首次发布或本轮使用的公开版本日期；“定位”给出章节、表格、代码路径、issue 或 commit。

### 4.1 跨 harness 不变能力

1. [Harness-Bench: Measuring the Impact of Agent Harnesses on LLM-Based Agents](https://arxiv.org/abs/2605.27922)，2026-05-27。  
   **定位：** §3 protocol；Table 1/2 的 model–harness 结果；Table 3/失败分类；论文明确声明没有对单一 harness 机制做因果分解。  
   **状态：C/A（评测），非训练。** 

2. [KAT-Coder-V2.5](https://arxiv.org/abs/2607.05471)，2026-07。  
   **定位：** §2.1 环境生产；§2.2 白盒/黑盒 harness；§2.3 gateway、retokenization drift 与 sandbox 审计；§4 多教师 on-policy distillation。  
   **状态：T；有若干系统消融，但没有隔离的 harness-diversity 训练消融。** 

3. [verifiers v1: Decomposing Tasksets and Harnesses](https://www.primeintellect.ai/blog/verifiers-v1)，2026-07-10，`verifiers 0.2.0` preview。  
   **定位：** taskset/harness/runtime 分解、branching trajectory、训练 token/logprob；长度惩罚训练消融。  
   **状态：C/T/A；v1 仍为 preview。** 

4. [`verifiers/v1/graph.py`](https://github.com/PrimeIntellect-ai/verifiers/blob/88de7294f35e85da014d8ec61fe10f93f74cfb03/verifiers/v1/graph.py)，commit `88de7294f35e85da014d8ec61fe10f93f74cfb03`。  
   **定位：** 文件头、`MessageNode`；精确 token path、mask、logprobs、advantages、routed experts、kept tokens。  
   **状态：C。** 

5. [On the Robustness of Agentic Function Calling](https://arxiv.org/abs/2504.00914)，2025-04。  
   **定位：** query rephrasing、toolkit expansion、exact-match evaluator 误差分析。  
   **状态：C/A（评测）。** 

---

### 4.2 环境资格与自适应难度

1. [RLVE: Scaling Up Reinforcement Learning for Language Models with Adaptive Verifiable Environments](https://arxiv.org/abs/2511.07317)，2025-11-10；ICML 2026。  
   **定位：** adaptive difficulty；环境数量消融；400 环境联合训练；50 held-out 环境；六项外部 benchmark。  
   **状态：C/T/A；R 未见。** 

2. [Zhiyuan-Zeng/RLVE](https://github.com/Zhiyuan-Zeng/RLVE)，本轮访问 2026-08-18。  
   **版本定位：** Docker `slimerl/slime:v0.5.0rc0-cu126`；`scripts/training/*/num-environment={1,4,16,256,400}.sh`；`scripts/evaluation/*/eval_HELD-OUT_ENVIRONMENTS.sh`；README 的随机初始化警告与约 1.1K H100 GPU-hour 披露。  
   **状态：C/T/A。** 

3. [Scaling Agentic RL: 365,000+ Environments for SWE, Terminal, and Search](https://www.primeintellect.ai/blog/scaling-agentic-rl)，2026-07-22。  
   **定位：** model-free `validate`；gold-pass/no-op-fail；flakiness；artifact visibility；各 taskset 通过数量；false-negative 和 isolated grading 限制。  
   **状态：C；内部训练有提及，但该文章不提供资格设计的受控模型消融。** 

4. [R2E-Gym](https://arxiv.org/abs/2504.07164)，2025-04-09。  
   **定位：** 环境构建；执行式 verifier 的低可区分性；execution-free verifier 的风格偏置；真实/合成轨迹对照。  
   **状态：C/T/A；实际训练主要是 SFT，不应写成 agentic RL。** 

---

### 4.3 环境合成与组合

1. [RACES: Verifiable Environments Are LEGO Bricks](https://arxiv.org/abs/2606.12373)，2026-06-10。  
   **定位：** sequential/parallel/sort/select composition；50 vs 300 base environments；14B 模型结果。  
   **状态：T/A；公开实现完整度与独立复现待核查。** 

2. [EvoEnv](https://arxiv.org/abs/2605.14392)，2026-05-14。  
   **定位：** solve–verify asymmetry；从少量 seed 演化 Python 环境；分阶段 validation、novelty 和 difficulty；固定环境基线的负结果。  
   **状态：T/A；资源和独立复现 `unknown`。** 

---

### 4.4 Verifier、反作弊与安全

1. [Natural Emergent Misalignment from Reward Hacking in Production RL](https://arxiv.org/abs/2511.18397)，2025-11-23。  
   **定位：** 生产 coding RL；reward hacking；agentic misalignment；alignment faking/sabotage；预防、safety RL 与 inoculation。  
   **状态：T/A；代码、硬件、数据量和成本大多 `unknown`。** 

2. [(Some) Natural Emergent Misalignment from Reward Hacking in Production RL](https://www.lesswrong.com/posts/2ANCyejqxfqK2obEj/some-natural-emergent-misalignment-from-reward-hacking-in)，UK AISI，2026-03。  
   **定位：** executive summary；开放模型、数据、环境与配置；reward hacking 稳定复现；广义 misalignment 不一致；KL/CoT 忠实性。  
   **状态：R（部分复现）。** 

3. [Reward Hacking Benchmark](https://arxiv.org/abs/2605.02964)，2026-05-03。  
   **定位：** 13 个模型、六类 exploit、hardening、harder variants、MicroRHB。  
   **状态：C/A，非训练。** 

4. [Reward Hacking in Language Model Agents: Revisiting AI Safety Gridworlds](https://arxiv.org/abs/2606.15385)，2026-06-13；[代码](https://github.com/asparius/verl-agent-safety)。  
   **定位：** 1.5B–14B RL；observed/hidden reward gap；credit、exploration prompt、entropy regularization 负结果。  
   **状态：C/T/A；R 未见。** 

5. [GLM-5.2 官方报告](https://z.ai/blog/glm-5.2)，2026-06-16。  
   **定位：** single-rollout critic PPO、compaction sub-trace、两阶段 anti-hacking、在线阻断、并行 on-policy distillation。  
   **状态：T；完整训练配置、硬件、数据和 anti-hack 准确率消融 `unknown`。** 

---

### 4.5 Fully-async 训练正确性

1. [vLLM issue #48305 — Training-Inference Consistency for RL](https://github.com/vllm-project/vllm/issues/48305)，创建 2026-07-11。  
   **定位：** logprob/token replay、MoE routing、DSA index、data plane、hidden states、dtype 六类差异；多个 exit criterion 尚未完成。  
   **状态：I/C，开放 RFC。** 

2. [vLLM issue #42259 — Logprobs/Logits Semantics and Determinism](https://github.com/vllm-project/vllm/issues/42259)，创建 2026-05-11，更新至 2026-07-29。  
   **定位：** prefix cache、raw/processed logprob、microbatch、MoE nondeterminism、rollout/trainer mismatch 和 GRPO collapse 关联。  
   **状态：I/C；修复状态不一。** 

3. [`slime/examples/fully_async/README.md`](https://github.com/THUDM/slime/blob/main/examples/fully_async/README.md)，本轮访问 2026-08-18。  
   **定位：** 0.5B/4-GPU 与 9B/8-GPU 示例；固定 in-flight pool；无 eval mode；跨 rollout best-effort ordering；ABORTED partial resume TODO。  
   **状态：C，不等于旗舰模型训练证据。** 

4. [Open-Instruct issue #1473](https://github.com/allenai/open-instruct/issues/1473)，2026-02-16 至 2026-02-25。  
   **定位：** OLMo-3-7B RLVR；约 step 450 后 logprob divergence；约 step 550 失败；`learning_rate=0` 仍漂移；8 节点×8 GPU。  
   **状态：独立工程故障报告，不是算法复现。** 

5. [Single-Rollout Asynchronous Optimization](https://arxiv.org/abs/2607.07508)，2026-07-08。  
   **定位：** Qwen3-30B-A3B、OpenHands/SWE-Bench Verified；稳定性、importance correction 和 critic 消融。  
   **状态：T/A；代码、硬件和成本部分 `unknown`，R 未见。** 

6. [M2PO](https://arxiv.org/abs/2510.01161)，2025-10-01；[代码](https://github.com/Infini-AI-Lab/M2PO/)。  
   **定位：** stale-k 对照、truncated ratio、1.7B–32B；主要是数学推理。  
   **状态：C/T/A；agentic 长轨迹迁移和 R 未见。** 

7. [RolloutPipe](https://arxiv.org/abs/2606.26997)，2026-06，v2 2026-07-05。  
   **定位：** complete-group pipeline、on-policy correctness、等待和 wall-clock 对照。  
   **状态：T/A；是“避免 stale”路线的重要反证。** 

8. [DORA](https://arxiv.org/abs/2604.26256)，2026-04-29；[StaleFlow](https://arxiv.org/abs/2601.12784)，2026-01-19。  
   **定位：** trajectory lifecycle/data integrity/bounded staleness；multi-version streaming；data server。  
   **状态：T/A；工业规模成本和独立复现 `unknown`。** 

---

### 4.6 过程信用与恢复

1. [Verifiable Process Rewards](https://arxiv.org/abs/2605.10325)，v2 2026-05-27；[代码](https://github.com/thu-nics/VPR)。  
   **定位：** §2 exact process oracle；turn-level GRPO；§3 held-out transfer；oracle-quality/MCTS 规模消融；Appendix A 资源与复现信息。  
   **状态：C/T/A；R 未见。** 

2. [DeepSeek-R1](https://arxiv.org/abs/2501.12948)，2025-01。  
   **定位：** §4.2 PRM 和 MCTS 负结果；§5 function calling、多轮和 SWE RL 局限。  
   **状态：T 级模型团队负结果；训练代码和对应资源 `unknown`。** 

3. [Agent Lightning](https://arxiv.org/abs/2508.03680)，2025-08。  
   **定位：** agent trace 与 trainer 解耦；当前简单 credit；长程细粒度信用与探索列为未来工作。  
   **状态：C/T（系统实验）；不能作为精细信用已解决的证据。** 

---

### 4.7 能力扩张、保持与回退

1. [Does RL Really Incentivize Reasoning Capacity Beyond the Base Model?](https://arxiv.org/abs/2504.13837)，2025-04。  
   **定位：** pass@1 与大 `pass@k`；base support 与 RL 概率重排；蒸馏引入知识的对照。  
   **状态：T/A；推理域，agentic 外推待验证。** 

2. [ProRL](https://arxiv.org/abs/2505.24864)，2025-05。  
   **定位：** prolonged RL、136K tasks、4×8 H100、约 16K GPU-hour；pass@k 与能力边界；validation/reset 的选择混杂。  
   **状态：T/A；非 agentic 工具域。** 

3. [Learning to Solve, Forgetting to Retain](https://arxiv.org/abs/2606.03087)，2026-06-02。  
   **定位：** correct-set turnover、repair window、retention-aware review。  
   **状态：T/A；工具 agent 复现未见。** 

4. [RL Forgets!](https://arxiv.org/abs/2607.04364)，2026-07-05。  
   **定位：** continual multimodal post-training 的遗忘和 CPO；代码公开。  
   **状态：C/T/A；领域与本项目不同，但提供能力保持反证。** 

---

### 4.8 故障恢复与评测治理

1. [ReliabilityBench](https://arxiv.org/abs/2601.06112)，2026-01-03。  
   **定位：** reliability surface；repeat/semantic/tool-fault；timeout、rate limit、partial response、schema drift。  
   **状态：C/A，非训练。** 

2. [FuncBenchGen](https://arxiv.org/abs/2509.26553)，2025-09，v2 2026-02-06。  
   **定位：** hidden function dependency DAG；深度与 distractor；stale argument propagation；变量重述对照。  
   **状态：C/A，非训练。** 

3. [Terminal-Bench 2.1 release](https://www.tbench.ai/news/terminal-bench-2-1)，2026-05-06。  
   **定位：** 89 个任务中修复 28 个；同一 agent–model 组合最高约 12.1 个百分点变化；依赖、资源和规范问题。  
   **状态：C/独立工程核查。** 

4. [Terminal-Bench 2.1 PR #53](https://github.com/harbor-framework/terminal-bench-2/pull/53)，head SHA `56fc6147c7426e7588cc8e089c6f791da0aad0e9`。  
   **定位：** 任务逐项修复；外部视频、本地工件泄漏、说明—测试错配、memory/CPU/timeout、oracle 和依赖问题。该 PR 标注为展示差异和社区讨论，不用于合并。  
   **状态：C。** 

---

## 本轮初步归类

**高潜力：**  
跨 harness 不变能力；环境资格与自适应难度；对抗式 verifier/反作弊；fully-async 正确性包络；可验证过程信用与恢复。

**需要关键探针：**  
solve–verify 环境合成；能力扩张与保持；故障注入恢复。它们都有强线索，但存在“只在合成域有效”“只是重新排序已有能力”或“稳健 harness 已足够”的实质反命题。

**当前不适合单独立项：**  
中立轨迹 IR；反事实评测与版本治理。二者都很重要，也与附件中的自建边界高度匹配，但只有在服务一个可检验的模型能力或训练正确性命题时，才足以构成最终项目。附件本身也要求最终工作同时具备可复用能力和可控模型命题，而不是把通用工程最佳实践直接包装成研究结论。
