<!-- 注意：本文件（2026-09-02，env_discovery_20260902 批次）与 summary_calibforge.md
（2026-08-18）是同一篇论文（2608.06352）的两份摘要。数字一致无冲突。旧文件独有：
"资格状态机"四态映射 + SWE-Bench Pro 审计注记。是否合并/删其一由 owner 定。 -->

# 《CalibForge: Adversarial Solver Calibration》阅读摘要

## 论文信息

- arXiv：2608.06352（2026-08 提交批次），AweAI-Team。
- 官方页面：<https://arxiv.org/abs/2608.06352>；数据集 <https://huggingface.co/datasets/AweAI-Team/CalibForge>；仓库 <https://github.com/AweAI-Team/CalibForge>。本仓库无本地 PDF，本摘要依据 arXiv TeX 源码核实。

## 核心问题

终端任务合成系统已能规模化产出"可执行且可验证"的任务，但 executable validity 不等于难度合适：任务可能对当前模型太浅或实际不可解。论文提出 environment-level behavioral calibration：把任务构造改成受约束的对抗式 author–solver 循环，用 solver 的验证结果（谁过谁不过）和完整轨迹作为构造期反馈，多轮改写任务直到它落进 solver-relative 的"learnable zone"——可解（至少一个 solver 成功）但不被所有 solver 一致解决。

## 方法

1. 构造流水线：从一条 clue 出发，authoring agent（DeepSeek-V4-Pro）先做 web research（官方文档/GitHub issue/Stack Overflow 找版本 bug、依赖冲突等真实工程问题），写任务规格，然后联合产出 instruction、Docker 执行环境和 verification tests；经结构校验（能构建、初始状态所有测试必须失败）+ self-solving（作者自己解一遍验证一致性）双门后进入校准循环。
2. 校准循环（R_max=50 轮，早停于达标，超轮次丢弃）：每轮为每个 solver 从 Dockerfile 起独立 sandbox（单次尝试限 100 步/30 分钟），verifier 判定 pass/fail；反馈包含 pass/fail、步数、完成状态、自评、失败诊断和完整轨迹，作者据此改写任务任意组件后重新校验、重新探测。三种 solver 设定：
   - Single-solver（消融基线）：与作者同模型的 solver 只给 pass/fail 反馈。
   - Multi-solver calibration：K 个异构 solver（DeepSeek-V4-Flash、GLM-5、Kimi K2.5）独立尝试，保留条件 0 < Σy_i < K，即必须出现分歧。
   - Contrastive solver calibration：指定强 solver（DeepSeek-V4-Pro）必须过、弱 solver（DeepSeek-V4-Flash）必须挂（y_s=1 ∧ y_w=0），把任务钉进两档能力的区间里。
3. 训练用途是 SFT 蒸馏而不是 RL：保留任务存成 Harbor 风格实例，用 DeepSeek-V4-Pro（reasoning effort high）在极简 scaffold CalibForge-Eval（只有 bash/file-editing/finish 工具）下每题跑 2 次（200 步/1 小时），保留过测试的轨迹；对 Qwen3-30B-A3B-Instruct 与 Qwen3.5-35B-A3B 做全参数 SFT（10 epochs，lr 1e-5，global batch 128，context 131,072，bf16，64×H20）。

## 实验结果

- 匹配 1,300 任务的校准方式消融（Qwen3-30B-A3B-Instruct，Terminal-Bench 2.0）：No Solver 22.47 → Single Solver 24.34（+1.87）→ Multi Solver 29.21（+6.74）→ Contrast Solver 31.09（+8.62）。且 Multi Solver 的 SFT 轨迹数（2,425）比 No Solver（2,466）还少，收益不能用轨迹量解释。
- 全量 5,431 任务（1,263 multi-solver + 4,168 contrastive）主结果：CalibForge-30B-A3B TB2.0 32.58%（base 7.87，最强基线 TerminalTraj 26.22，+6.36）；CalibForge-35B-A3B 47.57%（base 39.10，最强基线 40.82，+6.75）。OOD 迁移：SWE-bench Pro 30B 30.94 / 35B 44.32，Doc2Repo 30B 35.98 / 35B 48.77，均为同底座各数据源最高。
- 校准动态：全部通过结构校验+self-solving 的候选中，首轮只有 19% 满足 strong-pass/weak-fail（主要失配是双双通过=太浅）；经改写+重探后累计 96% 达标。15% 一次探测即达标，53% 在 5 次内，93% 在 20 次内。
- 数据画像：16 类领域，最大类 SWE 仅 25.5%（对比 SETA-Env 74.6% 集中在 sysadmin）；3,885 个 capability tag，中位每题 5 个，51.6% 的 tag 只出现一次；中位 7 个 verifier 测试函数（P90 15）；轨迹中位 21 步但 thinking tokens 中位 5.3k（CLI-Gym 28 步/4.0k）。
- 已对 TB2.0/SWE-bench Pro/Doc2Repo 做去污染（14-gram 重叠 + 5-shingle Jaccard + 输出路径/测试函数匹配）。

## 重要限制

- 全程是 teacher 蒸馏 + SFT，证明的是"这样造的数据在 SFT 下更有效"，没有任何 RL 训练证据；难度校准对 RL reward/样本准入的价值是外推。
- learnable zone 是 solver-relative 的：难度锚定在 DeepSeek-V4 家族等特定 solver 上，换 student policy 后区间会漂移；为让"弱 solver 必挂"而改写任务也可能把反特定模型的风格痕迹写进任务（solver-style leakage）。
- 公开资产范围（经核实 GitHub README）：5,431 任务数据集和两个训练后模型已放出，CalibForge-Eval 以 AweAgent 的 TB2.0 recipe 形式发布，但 authoring agent + 校准循环的完整流水线代码未开源（附录给了 prompt 模板）。
- SWE-bench Pro 只测一次（TB2.0/Doc2Repo 为三次取均值±SEM）；单次尝试成本高（每轮最多 50 次校准、每次多 solver 各 100 步）。

## 对 RepoHarness 的意义

- 我们 216 题 bundle 的 learnability 探针有了直接参照：CalibForge 把"solver-relative learnable zone"做成了可操作的保留判据（分歧判据 0<Σy<K、对比判据 strong-pass/weak-fail），且用匹配任务数消融证明校准本身贡献 +6.7~+8.6 个点——这正是我们"gold 能过≠当前模型可学"原则的量化证据。
- 首轮仅 19% 达标、改写后 96% 达标说明：探针的价值不只是过滤，更在"改写恢复"——难度失配大多可修，直接丢弃会浪费大量候选。
- 必须警惕 solver-style leakage：若我们用固定探针模型校准而训练另一 policy，难度标签会系统性偏移；对比校准尤其容易把"针对弱 solver 的坑"固化进任务。
- 注意证据边界：该论文支持的是数据构造→SFT 链路；把校准判据搬进 RL 样本准入属于我们自己的外推，需按 T0 决策流程单独论证。
