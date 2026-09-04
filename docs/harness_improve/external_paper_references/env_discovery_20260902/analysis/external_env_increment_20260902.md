# 环境生产/资格化/规模化：外部增量调查（截至 2026-09-02）

> 来源：Claude 主线程派出的 general-purpose subagent，实时网络检索，2026-09-02。
> 性质：证据补查，非定案。二手文章仅作线索，核心技术结论附一手 URL。
> 已知覆盖（不再复述）：RLVE、CalibForge、RACES/EvoEnv、Hardening Agent
> Benchmarks、R2E-Gym、SWE-Gym、SWE-rebench V2、PI 365K environments 博客、
> K3 知识图谱、GLM-5.3 环境合成、MAI-Thinking-1 环境工厂、Terminal-Bench 2.1。
> 本文只记这些**之外**的增量。

---

## 1. Prime Intellect Environments Hub —— 有增量（架构换代 + 悬赏式质控）

- **规模**：第三方目录 RL List 记 "2,500+ community RL environments"（https://www.rl-list.com/vendors/prime-intellect ，未标统计日）；官方 7-9 月未公布新总数（Hub 2025-08-27 上线：https://www.primeintellect.ai/blog/environments ）。
- **安装**：`prime env install owner/env@x.y.z` + `uv run vf-eval <env>`；环境按 wheel + pyproject 依赖分发，prime-rl 直接消费。
- **7-9 月版本线**（https://github.com/PrimeIntellect-ai/verifiers/releases ）：
  - v0.2.0（07-10）："v1" 任务中心 API（taskset/harness/runtime 三分、trace 线性增长）
  - v0.2.1（07-20）：Claude Code 等外部 harness、OpenEnv 支持、lazy/infinite taskset
  - v0.3.0（08-07）：多智能体环境、ACP 可续会话、**沙箱网络隔离**
  - v0.3.1（08-24）：请求拦截改写、**训练原生 episode artifacts**，旧 API 移入 `verifiers.legacy`
  - prime-rl v0.8.0（08-07）：proposer-solver Hierarchical GRPO、多智能体 RAE
  - prime-rl v0.9.0（08-25）：**可组合 curricula + task sampling + admission gates**（与本项目资格化设计直接同构）
- **质控**：两档悬赏（开放 $100-500 / 申请制 $1k-5k+，基准类须复现已知模型分数）+ RL residency 人工审查；截至 2025-10-27 收 400+ 环境、80+ 过 review（https://www.primeintellect.ai/blog/scaling-environments-program ）。**没有公开的自动化资格化流水线**——质控本质是"悬赏验收 + 人审"。

> RH2 启示：admission gates 进正式版 → "做一个资格门"的新颖性下降；差异点转向"贯通到训练资格的可审计整链 + 诚实良率数字"。verifiers 升级影响面另见 `verifiers_v031_primerl_v090_impact_20260902.md`。

## 2. SWE 之外的环境家族 —— 有增量（terminal 与办公工具链均有训练结果）

- **Terminal**：Endless Terminals（https://arxiv.org/abs/2601.16443 ，2026-01-23，Gandhi/Goodman/Papailiopoulos 等）程序化生成 3255 个容器化任务（四段管线含可解性过滤），vanilla PPO 训 Qwen2.5-7B dev 10.7%→53.3%；后续数据工程论文（https://arxiv.org/abs/2602.21193 ）再产 6170 任务。社区训练仓：https://github.com/Danau5tin/terminal-bench-rl （GRPO，32×H100）。
- **Terminal-Bench 训练衍生**：仓库并入 harbor-framework 组织；Harbor Hub（https://hub.harborframework.com ）明确定位 "find and share tasks for **training** and evaluation"。
- **办公多工具 DAG**：Toolathlon-Gym（https://github.com/eigent-ai/toolathlon_gym ，503 任务、25 个 PostgreSQL 后端 MCP server）；Surge AI 论文（https://arxiv.org/abs/2608.01604 ，2026-08-03）用 363 个办公任务（零 SWE）RL 训 Qwen3.5-122B-A10B，**SWE-Bench Pro pass@1 +5.8**——最直接的"环境域外迁移"新证据。
- **tau2/BFCL 训练版**：SENTINEL（https://arxiv.org/abs/2606.12908 ，2026-06）failure-driven 闭环（Controller 析失败 → Proposer 定向出题），Qwen3-4B-Thinking，报告 τ²/BFCL-V4 增益（点数未逐一核实，降半级）。
- **CTF**（2025-08，清单未覆盖）：CTF-Dojo（https://arxiv.org/abs/2508.18370 ）：CTF-FORGE 把 pwn.college 资产自动容器化成 658 个可执行挑战，训出模型在 3 个 CTF 基准开源权重 SOTA。
- **OpenEnv**：2026-06 起转入 PyTorch 基金会、9+ 组织指导委员会（Meta/HF/NVIDIA/Prime Intellect/Microsoft 等），环境发布/部署/消费互操作层（HTTP/WS + Docker），TRL/verl/TorchForge/SkyRL 已接入（https://github.com/meta-pytorch/OpenEnv ）——仍自标实验阶段。
- SRE/SQL/科学计算：ITBench（IBM）仍是评测非训练；**未找到有公开训练结果的 SQL/科学计算家族**。

## 3. 环境合成新方法（2026-06 后）—— 有一项直接可用增量

- **Envs-FORGE**（https://arxiv.org/abs/2608.14312 ，2026-08-14）：把 verifier 通过率转成**逐 seed 合成动作策略**——估 seed pass rate、在学习前沿附近评 6 个方向动作、MILP 选动作，**同步改写 instruction/fixtures/oracle 解/tests/Docker 五件套**；产 100 个 verified 环境（2.27-2.88M 合成 token），训 Qwen3.5-35B：tb-core 49.2%（+9.2）、SWE-bench Verified 77.1%；开源（DataArc-SynData-Toolkit）。与 CalibForge 同讲 solver-relative，但把难度控制做成了训练中的在线策略。
- SENTINEL（见上）：失败驱动定向出题是另一条在线难度控制路线。
- 方法地图：Agentic Environment Engineering 综述（https://arxiv.org/abs/2606.12191 ，2026-06）。窗口边缘指路：EnvFactory（2605.18703）、Agent-World（2604.18292，真实环境主题挖掘+可控难度）、SWE-Hub（2603.00575，SWE 任务生产系统化）。

## 4. 环境质量/资格化工程 —— 有增量（Nebius 两份材料 + SWE-smith 确证）

- **SWE-rebench 经验谈**（演讲纪要，2026-06-08：https://www.sean-weldon.com/blog/2026-06-08-swe-rebench-lessons-from-evaluating-coding-agents-ibragim-badertdinov-nebius ）：人工核验约 **1 人日/任务**；实录 reward hacking——模型经 git 历史/GitHub 网页/curl 直接抓答案，对策是剥离未来 git history；缓存换 4x 降本；pass@5 与 pass-all-5 双指标区分"偶然对/稳定对"；时间切分被认定为唯一可靠去污染；V2 称 30,000+ RL 环境、20 种语言。
- **Nebius 基建博客**（2025-11-07：https://nebius.com/blog/posts/infrastructure-behind-swe-rebench ）：21TB GH Archive → 32K repos → **153K 候选 → 约 21K 过执行验证（≈14% 存活率）**；LLM 抽取安装/测试配方，buildah 构建后按历史 F2P/P2P 一致性校验；自建后端 18 分钟跑完 SWE-bench Verified 500 题。
- **SWE-smith 真实存在**：https://arxiv.org/abs/2504.21798 （NeurIPS 2025 D&B Spotlight，John Yang 等，挂 SWE-bench 组织：https://github.com/SWE-bench/SWE-smith ）：对任意 Python 仓自动注入 breaking 任务，50,137 实例/128 仓/125 镜像（295GB），训 SWE-agent-LM-32B 得 40.2% SWE-bench Verified；附带 SWE-bench Multilingual（300 实例/9 语言）。2026 年未见重大新版本。
- OpenHands/All-Hands：2026 只有 SDK 论文与产品迭代，无环境资格化新披露。

> RH2 启示：14% 执行验证存活率与 1 人日/任务是我们四门存活率与自产线良率的**外部对标锚**；git 抓答案的 reward hacking 实录与 W3b 正向能力事实清单完全对上。

## 5. 中国团队 8-9 月披露 —— 增量有限，两个例外

- **蚂蚁 AEnvironment**（https://github.com/inclusionAI/AEnvironment ，Apache-2.0）："Everything as Environment"——扩展 MCP 的统一环境接口，与 AReaL 深度集成，内置 TAU2/Mini Terminal/TerminalBench，K8s 部署；配套：Ling 3.0 Flash（2026-07-23）自称用 **10,000+ 交互式训练环境**。Medium 精确日期未能确认（直接访问 403），时间归属留有不确定。
- **字节 Seed + 清华 AIR CUDA Agent**（https://arxiv.org/abs/2602.24286 ，2026-02 首发，08-17 随开源发布被广泛报道；https://github.com/BytedTsinghua-SIA/CUDA-Agent ）：开源**训练数据 + 专家 SKILL.md + CUDA 开发环境整套**，RL 训练在 KernelBench 超 torch.compile 2.11×——"环境+技能包整体开源"的生产范式可参考。
- **降级项**：Qwen3.8-Max/27B（08-12/14）无技术报告，环境仅一句"million-agent environments"；DeepSeek V4-Pro-0813（08-12/13 API 上线）无官方环境材料，仅第三方分析（agentic mid-training + 领域专家两阶段 + on-policy 蒸馏合并）；Kimi K3 在 8/1 后无环境新披露；GLM-5.4/5.5 仅传闻——均无实质。
- **窗口外但清单未含**：MiniMax M2.1 后训练博客（2026-01-22：https://www.minimax.io/news/post-training-experience-and-insights-for-agent-models ）有硬数字——按 PR 建 Docker 环境、10+ 语言、**10,000+ runnable PRs、140,000+ 任务**、F2P/P2P 校验、应用开发三层 reward（执行/交互/视觉）。

---

## 承重来源速查

verifiers releases / prime-rl releases（GitHub）、Envs-FORGE(2608.14312)、Surge(2608.01604)、Endless Terminals(2601.16443)、SWE-rebench 纪要(sean-weldon.com)、Nebius 基建(nebius.com)、SWE-smith(2504.21798)、AEnvironment(inclusionAI)、CUDA-Agent(BytedTsinghua-SIA)、OpenEnv(meta-pytorch)、Harbor Hub(harborframework.com)、MiniMax M2.1 博客(minimax.io)、CTF-Dojo(2508.18370)、SENTINEL(2606.12908)、Toolathlon-Gym(eigent-ai)。
