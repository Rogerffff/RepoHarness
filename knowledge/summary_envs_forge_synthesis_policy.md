# 《Envs-FORGE: Frontier-Aware Environment Synthesis for Terminal Agents》阅读摘要

## 论文信息

- arXiv：2608.14312（2026-08 提交批次），DataArcTech；开源工具包 <https://github.com/DataArcTech/DataArc-SynData-Toolkit/>。
- 官方页面：<https://arxiv.org/abs/2608.14312>；本仓库无本地 PDF，本摘要依据 arXiv TeX 源码核实。

## 核心问题

终端 agent 的 RL 训练需要"reward 可靠且难度合适"的可执行环境。固定合成配方（few-shot、Self-Instruct、Evol-Instruct）对每个 seed 套同一套 prompting 策略，不管当前 policy 此刻需要的是更难、更易还是换个花样的任务。Envs-FORGE 把环境合成重新表述为按 seed 的动作选择问题：先用当前 policy 的 verifier 通过率估计每个 seed 的难度，再决定对这个 seed 施加哪种改写动作，让产物落在学习前沿（learning frontier）附近。

## 方法

1. seed 任务是五件套 s_i = (I 指令, D fixtures/数据, S oracle 解, T 测试, E Docker 环境)，组件强耦合：只改指令不同步改解和测试会产出不可判分或语义不一致的任务。
2. 难度估计：用当前 policy 在 seed 上的 verifier reward 均值算通过率 p̂_i；对候选动作用固定 transfer prior 预测改写后通过率 p̃ = clip(p̂ + Δ_a·γ_d, 0, 1)，其中 Δ_increase=−0.25、Δ_reduce=+0.25、Δ_diversify=0，γ_in_depth=1、γ_in_breadth=0.65（论文明确这只是排序先验，不是经验断言）。前沿分数 F = exp(−(p̃−τ)²/2σ²)，τ=0.5、σ=0.2，即目标是把任务推向约五成通过率。
3. 动作空间 6 个 = 投影 {increase, reduce, diversify} × 演化方向 {in_depth, in_breadth}。每个 seed 解一个六候选的 MILP（每 seed 恰选一个动作；技能节点一致性约束；资格/重叠/prompt 长度约束；可选 portfolio 模式加软技能覆盖目标，slack 上限 0.2、惩罚 λ=0.25）。固定配方可表示为同一动作空间上的受限 mask：few-shot ≈ (diversify, in_depth)、Self-Instruct ≈ (diversify, in_breadth)、Evol-Instruct 固定 depth 或 breadth；reduce（把过难 seed 降成 bridge task）是 Envs-FORGE 独有的投影。
4. 同步改写与验证：选中的动作驱动五件套联合改写（禁止 instruction-only 编辑和隐藏测试要求；容器不得打包 oracle 解或隐藏测试）；先过 schema/路径安全/长度/Docker/测试/重叠静态检查，再做 gold verification——oracle 解在生成的测试下必须拿到 reward 1 才能入训练池。
5. 下游训练：接受的环境转成 Terminal-Bench 风格任务做 GRPO；vLLM 异步 rollout，每 prompt 8 样本、temperature 1.0、top-p 0.9、单响应上限 1024 token、至多 50 个 agent 步；测试直接给 reward，无学习型 reward model；35B 训练用 FSDP2 + offload，仅 2×H800 80GB。
6. 训练前 preflight 验证：加载全部归一化任务、重查 train/eval split 与重叠过滤、构建代表性容器并重跑合成期同一条 oracle+测试链，全部通过后才启动 model worker——保证容器或 verifier 故障不会消耗 rollout 预算。prompt 长度用目标 tokenizer + 真实 agent system prompt + 完整 chat template 计算（小模型档阈值 4096、35B 档 8192），超限任务记录在案而不是静默截断。

## 实验结果

- 公平口径：四种合成方法各自持续生成-修复-验证，直到导出恰好 100 个 verified 环境；实际物化 194–210 个任务目录、耗 2.272M–2.881M 合成 token（每个接受环境 22,723–28,811 token、1.90–2.91 次尝试；Envs-FORGE 走 291 次更短的尝试、单次均 9,901 token）。
- Qwen 3.5 35B 主结果（Pass@1）：tb-core Base 40.0 → few-shot 43.2 → Self-Instruct 45.6 → Evol-Instruct 46.8 → Envs-FORGE 49.2（较 Base +9.2，较最强固定配方 +2.4）；tb-2.0 23.0 → 29.4（+6.4，较 Self-Instruct +2.1）；SWE-bench Verified 73.4 → 77.1（+3.7，较最强基线 +1.3）。
- 模型规模消融（tb-core，较各自 Base）：4B +6.8、9B +7.2、27B +8.1、35B +9.2，四档全正。
- 案例数据佐证动作语义：通过率 0.747 的 Bash seed 加深到预测 0.497；饱和 seed（p̂=1.0）加硬到 0.750；两个 p̂=0.0 的过难 seed 用 reduce 降成预测 0.250 的 bridge task；p̂=0.533 的近前沿 seed 用 breadth 换 fixture 保持难度。

## 重要限制

- 论文自述：只评了 per-seed MILP 模式（portfolio 技能配额模式未进对比）；没有 solver-off 消融（选择器 vs 候选池的贡献未拆开）；transfer prior（±0.25/0.65）是未做敏感性分析的固定启发式。
- 难度估计是合成前一次性计算并在优化期间冻结的：这是"按当前 policy 校准"的合成，不是训练过程中持续重估难度的闭环课程。
- 规模很小：每方法 100 个环境、单响应 1024 token、50 步上限、2×H800——与大规模长程 agent RL 设定差距明显；tb-core/tb-2.0 数字与其它论文不可直接互比（评测协议自定）。

## 对 RepoHarness 的意义

- 这是难度控制从"离线难度标签/过滤"升级为"按当前 policy 通过率逐 seed 决定合成动作"的最新参照，直接对位我们 E 方向（环境合成,Wave4）的路线：难度不是任务属性，是任务×policy 的关系量，合成时就应消费 rollout 通过率。
- 与 CalibForge 互补且证据链更贴近我们：Envs-FORGE 是真的用合成环境跑 GRPO（RL 证据），CalibForge 是 SFT 蒸馏证据；两篇合起来支持"solver/policy-relative 难度校准"作为构造期一等公民。
- reduce→bridge task 对我们最实用：0% 通过率的种子不必丢弃，可降解成保留技能链的桥接任务——这与 CalibForge"81% 失配可改写恢复"的结论一致。
- gold verification（oracle 解必须在生成测试下拿 reward 1 才准入）与我们 v2 grader 正链/四门 runner 的资格化思路同构，可互相校对检查清单；DataArc-SynData-Toolkit 已开源，E-Wave4 评估时应先读其实现再决定自研范围。
- 工程细节两处可直接抄：训练前 preflight（容器+oracle+测试全链重跑后才起 model worker，避免环境故障烧 rollout 预算）与全程记录 solver 决策/验证结果的可审计性要求，与我们的账本纪律一致。
