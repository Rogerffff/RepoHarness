# 《Intern-S2-Preview: Scientific Agentic Foundation Model》阅读摘要

## 论文信息

- arXiv：2608.13505v1，2026-08-13 提交；Intern-S2-Preview Team, Shanghai AI Laboratory
- 本地论文：`docs/harness_improve/external_paper_references/pdfs/E10_intern_s2_preview_2608.13505.pdf`
- 官方页面：<https://arxiv.org/abs/2608.13505>；权重：<https://huggingface.co/internlm/Intern-S2-Preview>；agentic RL 框架随 XTuner 仓库开源
- 来源类型与证据等级：官方技术报告的 arXiv TeX 源码（一手材料）。披露完整度：算法目标函数与训练基础设施为配方级；SFT/RL 数据混合比例、关键超参数值（IS clip 区间、GEPO 阈值、length-reg 的 τ/α/γ）与算力预算未披露，属主张级。

## 核心问题

科学发现类任务要求模型同时具备多模态科学理解、可验证的工具交互与长 horizon 执行。主评测模型 Intern-S2-Preview-397B 为 MoE（训练细节提到 MoE router 与 Gated DeltaNet；按命名总参 397B，激活参数量未能核实），另有 35B 变体但只出现在 length regularization ablation 中。后训练要解决的核心问题：把同一个 SFT checkpoint 分别训成 reasoning 与 agentic 两个 expert 策略，再合并回单一发布模型。

## Intern-S2-Preview 的后训练方法

管线实际结构：SFT → 多任务 RL 与黑白盒 agentic RL 从同一 SFT checkpoint 并行训出两个 expert → OPD 合并；并非严格串行四段。

1. SFT：多模态大混合（通用对话、代码、工具使用、科学任务、长 horizon agentic 轨迹）；CoT 用上一代 Intern-S1-Pro 与其他开源模型做 rejection sampling，再经模型与人工专家校验。数据量未披露。
2. 可扩展多任务 RL（RLVR）：leave-one-out REINFORCE（RLOO advantage）+ DAPO 式 dynamic sampling（组内 reward 全同则剔除重采）。advantage 两次 shaping：先 GEPO（低熵组衰减正 advantage、高熵组衰减负 advantage，系数不对称），再 adaptive length regularization（只作用正样本、组内 pass rate 超过阈值才激活，近似保持正 advantage 总质量）。系统侧：XTuner+LMDeploy 的 co-located partial rollout（pause-resume 保留已生成前缀），逐 token 记录 behavior policy 版本与 logprob，clipped IS ratio 作为 detached 权重（clip 权重而非 PPO 式 clip objective），trajectory 陈旧超过 3 个 policy update 即丢弃；MoE 训推一致用 R3 routing replay + expert 层 FP8/其余 BF16/敏感算子 FP32 + 双向 binary KL token mask。online speculative decoding（hybrid LK loss，K=4，η=3）带来 rollout 约 2 倍、端到端 1.7 倍加速。Muon optimizer lr 1e-6，每 batch 8,192 条完成 response、8 次 mini-batch 更新，最大生成 65,536 token。
3. 黑盒/白盒 agentic RL：核心是 harness × task 抽象。白盒 = 控制循环可直接编排的自研 loop；黑盒 = 保留原生消息与工具循环的现成 runtime（OpenClaw、Claude Code、OpenCode、OpenHands、Mini-SWE），经其 CLI/SDK/模型 API 接入，只需写薄 adapter。模型服务是 token-in-token-out（TITO）：对 harness 表现为普通 OpenAI/Anthropic 协议服务，同时透明捕获 token id、rollout logprob 与 MoE router experts；PrefixTree Trace Store 保存 token 级证据，与语义 Replay Buffer（动作-观察轨迹 + verifier 反馈）按 session/segment join。任务两来源：公开可执行任务集（SWE-smith 59,136、SWE-rebench-V2 32,100、Scale-SWE 20,200、Nemotron-Terminal-Synthetic-Tasks 80,000、R2E-Gym-V1 7,480、SWE-Gym 2,438、ClawGym-Task 13,500）统一归一成"初始环境 + 自然语言目标 + 自动 verifier"契约；加 skill2task 自演化合成（社区 skill 过滤 → skill-state graph 组合成不同 horizon 的能力路径 → 环境/任务/verifier 分阶段生成且每阶段配可执行 validator → 执行失败统计反哺采样权重与合成组件）。沙箱由 Shared Sandbox Provider 抽象，支持 local/remote/custom 后端。训练：整个 session 一个 outcome reward，按 GRPO 范式算组相对 advantage 并广播给该 session 全部可训 policy 段；process annotator 对确定性过程错误（格式错、无效工具调用、重复失败、超限终止等）打 adv_penalty，权重 w∈[-1,1] 只作用于正 advantage，保留失败轨迹的负信号；verifier 防泄漏：gold patch/held-out test 只进评分侧，git 历史压成单 baseline commit，评分时恢复 canonical 测试并叠加 gold test patch，SWE 任务用 all-correct 语义，infra 失败与任务失败分开记账。
4. OPD：只设两个 teacher——reasoning expert 与 agentic expert，均源自同一 SFT checkpoint（同源）；明确否决 fine-grained 多 teacher 路线（独立训多个域 teacher 的 RL 与基础设施成本高、增益有限）。先用两个 teacher 的轨迹对 SFT 模型做轻量 warmup（引 Nemotron 3 Ultra 做法），再做 fully on-policy reverse KL：student 采样、按 query 域选对应 teacher 打分。只传输 sampled token 的 teacher logprob（payload 从 O(HV)/O(Hk) 降到 O(H)），advantage = sg[log πT − log πprox]，套入与 RL 完全同形的 clipped-IS REINFORCE（同 R3、同 BKL mask），最大序列 256K。

## 实验设置与结果

- Agentic（各基准 harness 均注明）：SWE-Bench Pro 61.56（Mini-SWE-Agent，并修改官方镜像防止 agent 从 git log 拿 ground truth）、SWE-bench Multilingual 81.67（Mini-SWE-Agent）、Terminal-Bench 2.1 67.42（Terminus 2）、SkillsBench 50.03（OpenClaw 2026.5.7）、WildClawBench 44.68。对比模型含 Qwen3.5-397B-A17B、DeepSeek-V4-pro、Kimi-K2.7-Code、GLM-5.2、GPT-5.5、Gemini-3.1-Pro、Claude-Opus-4.8。
- 通用：MMLU-Pro 89.75、SimpleQA-Verified 69.90、HMMT-2026 91.57、MMMU-Pro 80.46、ChartQAPro 69.65（多为开源第一）。
- 科学：Biology-Instructions 56.92（外挂 Intern-MemDec-4B 后 60.32）、Mol-Instructions 52.37、SciReasoner 63.97、MP20 67.88 等多项全场第一。

## 重要限制

- 数据混合比例、RL 任务配比、关键超参数值与 GPU 预算未披露；35B 变体无独立评测表。
- agentic 面仍落后 GLM-5.2 与 Claude-Opus-4.8（Terminal-Bench 2.1 为 67.42 vs 77.90/84.60；SWE-Bench Pro 61.56 vs 62.10/69.20）。
- agentic credit assignment 仍是 outcome-level 加过程降权，无独立 step reward；reward 曲线只展示 160 步代表性示例，且论文自注不同 harness 的绝对 reward 不可比。

## 对 RepoHarness 的意义

- B 线（多 harness 泛化）最直接的同类系统证据：黑盒 harness（含 Claude Code、Mini-SWE）不改内部逻辑、仅靠 TITO serving + 薄 adapter 即可进 RL；其 PrefixTree + 语义/token 双视图 join 与我们 miles+SGLang 的 token 账本、faithful DIS 需求同构，可作设计对照。
- C 线 OPD：两 expert 同源、只传 sampled-token logprob、先 warmup 的轻量 OPD 支持我们"同源优先、单 teacher proof"取向；其对 fine-grained 多 teacher 的成本否决与我们"MOPD 仅作条件式 capstone"的定位一致。
- A 线环境资格：其 verifier 防泄漏清单（git 历史 sanitize、评分时恢复测试、all-correct 语义、infra 错误单独记账）与公开任务源清单（SWE-smith、SWE-rebench-V2、Scale-SWE 等）可直接进入我们的环境资格标准与数据源候选。
- 算法对照：它选 co-located partial rollout 而非 fully-async，异步性靠逐 token behavior 版本 + clip IS 兜底，staleness 硬上限 3 个 policy update——是我们 fully-async GRPO 陈旧度预算的外部参考点。
