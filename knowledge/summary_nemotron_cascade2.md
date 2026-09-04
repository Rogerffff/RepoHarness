# 《Nemotron-Cascade 2: Post-Training LLMs with Cascade RL and Multi-Domain On-Policy Distillation》阅读摘要

## 论文信息

- arXiv：2603.19220（v1 2026-03-19，v2 2026-03-22），NVIDIA
- 本地论文：`docs/harness_improve/external_paper_references/pdfs/E11_nemotron_cascade2_2603.19220.pdf`
- 官方页面：<https://arxiv.org/abs/2603.19220>；开源：HF 权重 `nvidia/Nemotron-Cascade-2-30B-A3B`（base 为 Nemotron-3-Nano-30B-A3B-Base）+ SFT 数据集 + RL 数据集；训练框架 NeMo-RL
- 来源类型与证据等级：官方技术报告的 arXiv TeX 源码（一手材料）。披露完整度：配方级——SFT 数据构成到条数、各 RL 阶段超参与步数、MOPD 目标函数全公开且训练数据开源；GPU 预算与墙钟时间未披露。

## 核心问题

多域 RL 混训会互相干扰、reward 异构导致不稳。Cascade RL = 按域顺序分段做 RL：抗 catastrophic forgetting、每域单独调超参与课程、域内响应长度与验证耗时均匀从而省算力。本代新增问题：环境数量增大后仍有能力漂移（某些 RLVR 压低熵、缩短推理链而伤数学，RLHF 伤指令遵循），因此在管线中引入 MOPD（multi-domain on-policy distillation）把回退修回来。

## Cascade RL + MOPD 的方法

- SFT：单阶段、256K token packing、约 1.5 epoch（batch 64、33,000 步、lr 5e-5 到 5e-6 cosine）。数据配方到条数：数学 1.8M tool-calling + 2.6M 非 tool（response 由 DeepSeek-V3.2 / V3.2-Speciale / GPT-OSS-120B 生成）+ 816K 证明生成/验证；竞赛代码 1.9M Python + 1.0M C++ + 1.3M Python tool（teacher 为 GPT-OSS-120B，带测试的 prompt 做 correctness filtering）；科学代码 1.1M；SWE 为 125K agentic 轨迹（Qwen3-Coder-480B-A35B 在 OpenHands/SWE-Agent/Mini-SWE-Agent 等 scaffold 生成，任务源 SWE-Gym/SWE-rebench/R2E）+ 389K agentless（定位/修复/测试生成三任务），agentic 数据用 non-thinking mode、agentless 用 thinking mode 训练，混入 agentless 使 OpenHands 上 SWE-bench Verified Pass@1 48.9→49.9、Pass@4 62.8→65.2；terminal 490K（Terminal-Task-Gen 方法，DeepSeek-V3.2 在 Docker 执行反馈循环里生成轨迹，scaffold 为 Terminus 2）。
- Cascade RL 顺序（本代重排）：IF-RL（180 步）→ 多域 RL（70 步；55% STEM MCQA + 30% agentic tool calling + 15% structured output，合并理由是互不干扰且响应长度/验证耗时接近）→ MOPD（52 步）→ RLHF（生成式 reward model 为 Qwen3-235B-A22B-Thinking，pairwise 比较，25~30 步）→ 长上下文 RL（30 步，LLM judge）→ Code RL（22 步；只留 GPT-OSS-120B 8/8 做不全对的 3.5K 高难 prompt，response 上限 118K，严格二值 reward）→ SWE RL。排序原则：最小化域间负干扰，最高优先域（code/SWE）放最后。
- "严格 on-policy"的含义：全程 GRPO，每次迭代从当前 policy 采 G=16 个 rollout 后只做一次 gradient update，因此 IS ratio 恒等于 1；去掉 KL 项后等价于组归一 advantage（减均值除标准差）+ token-level loss 的 REINFORCE；配 DAPO dynamic filtering（全对/全错组剔除）。各 RL 阶段 batch 128、lr 3e-6、temperature/top-p 1.0。与异步的关系：策略更新完全同步，只把 reward 验证放到异步服务器（384 CPU cores，每 batch 2,048 次代码执行 427.2 秒）。
- SWE RL 两段：agentless RL（无 Docker 的实例用 GPT-OSS-120B 当 reward model，全组 reward 不超过 0.5 的 prompt 掩掉 loss，40-50 步收敛；纯 agentless 训练也能迁移到 agentic scaffold，OpenHands avg@4 49.8→50.8）；execution-based agentic RL（OpenHands scaffold 端到端，16 prompts × 64 rollouts = 1024 batch，256K context，最多 200 turns，temperature 0.8，数据 SWE-Gym + R2E-Subset，预筛：16 rollout 全过的实例删除、全不过的随机丢弃 90%）。
- MOPD：teacher 直接取自 Cascade RL 自己的 checkpoint 池，按 benchmark 挑最强者——math teacher = 初始 SFT checkpoint、RLHF teacher = 从 SFT 另训的 RLHF checkpoint、multi-domain teacher = IF-RL+多域 RL 之后的 checkpoint——全部同源（同一 SFT 初始化、同 tokenizer/词表，无外部模型家族）。目标：token 级 advantage = log πteacher(y_t|s_t) − log πtrain(y_t|s_t)（reverse-KL 视角，只算 sampled token，不传全词表）；训推引擎失配用截断 IS：r_t = πtrain/πinf，带外（<0.5 或 >2.0）整 token 置零、带内 stop-gradient。超参：rollout 4 × 128 prompts（512 responses，512 prompts × rollout 1 更稳）、lr 2e-6 且前 30 步自 2e-7 线性 warmup（附录表记 3e-6，两处不一致）、40-50 步收敛；prompt 采自各域 RL 数据池 + AceReason-Math。

## 实验设置与结果

- 竞赛级：IMO 2025 金牌 35/42（人类 IMO 金牌得主评分）、IOI 2025 金牌 439.28/600、ICPC World Finals 2025 10/12（官方测试用例判题）；是继 DeepSeek-V3.2-Speciale-671B-A37B 之后第二个达成三金的开源权重模型，参数少 20 倍。
- 推理面：LiveCodeBench v6 87.2（TIR 88.4）、AIME 2025 92.4（TIR 98.6）、HMMT Feb25 94.6、IFBench 82.9、ArenaHard v2 83.5——超过 Qwen3.5-35B-A3B 与更大的 Nemotron-3-Super-120B-A12B。
- MOPD 效率：AIME25 上 math-only 训练 GRPO 25 步 89.9→91.0，MOPD 30 步内到 92.0 并追平 teacher（92.08）；ArenaHard v2 Hard Prompt 上 MOPD 52 步 71.5→85.5，RLHF 160 步才到 80.7。
- agentic 弱项（作者自认）：SWE-bench Verified（OpenHands）50.2、Terminal-Bench 2.0 21.1、τ²-Bench 58.9、BFCL v4 52.9，全面落后 Qwen3.5-35B-A3B（对应 69.2 / 40.5 / 81.2 / 67.3）。

## 重要限制

- agentic 与知识面短板明确，作者归因于预训练与 agentic RL 投入不足；execution-based SWE RL 数据只有 SWE-Gym + R2E-Subset、每步仅 16 个 prompt，规模很小。
- 严格 on-policy 单步更新的吞吐/算力代价未量化；GPU 预算与训练时长未披露。
- 报告内有小不一致（RLHF 步数正文 30 vs 附录 25；MOPD lr 正文 2e-6 vs 附录 3e-6）。
- IMO 评分部分依赖人工与 LLM grader（P2 用 ProofBench 的 LLM grader）。

## 对 RepoHarness 的意义（规模/算法/蒸馏逐点对照）

- 规模：与我们同为 30B-A3B MoE（我们是 Qwen3-30B-A3B）。它 SWE-bench Verified 50.2（OpenHands、执行 RL 后）与 Terminal-Bench 2.0 21.1 是"强 SFT + 顺序 RL"路线在同规模上的真实水位，可作我们 A/B 线的外部锚点。
- 算法：它对"严格 on-policy GRPO"的操作性定义是采样后单次更新（IS≡1）+ 无 KL + token-level loss，用吞吐换稳定，与我们 fully-async GRPO + faithful DIS 是两极。注意它即便严格 on-policy 也要处理训推引擎失配（MOPD 用 [0.5,2.0] 截断 IS、带外置零）——训推一致问题在任何设置下都存在，印证 faithful DIS 的必要性；其带外整 token 置零的语义可与我们 DIS 的处理逐条比对。
- 蒸馏：同源 teacher（同 SFT 初始化）、sampled-token reverse-KL、密集 token advantage 带来数倍步效率，是我们 C 线"同源单 teacher OPD proof"最接近的正面参照，并给出可抄超参（rollout 4、lr 2e-6 + 30 步 warmup、40-50 步收敛、IS 带 [0.5,2.0]）。定位差异要记：它的 MOPD 是管线中段的"回退修复"手段，teacher 是过程 checkpoint 而非终态强模型；我们把 OPD 当能力转移主线时不能直接照搬其结论。
- 数据/预算：SFT 与 RL 数据全部开源，可抽查其 SWE/terminal 数据作我们环境与准入设计的对照样本；其难度预筛规则（全对实例删除、全错实例丢 90%、agentless 全组低 reward 掩 loss）与我们 DIS/样本准入语义可逐条比对。
