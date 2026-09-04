# Pro-Env-1：环境资格化与合成配方深挖

先读 `common_env_brief.md`。你是一名独立的开放权重模型 post-training 研究员，本轮只做**证据审计与配方提炼**，不做立项、不写代码、不给完整执行计划。检索截止：请覆盖到 2026-09-02，重点补 2026-06 之后窗口。

## 任务

围绕一个具体问题做深度证据审计：

> **在 216 道 SWE 任务量级、8×GPU 单机、可用 CPU 云+订阅 agent+API 的资源下，"任务资格化（learnability 校准 + verifier 可信度）与难度控制"的哪一种配方性价比最高，且能贯通到训练资格与真实训练增益？**

这不是让你找一个更新的算法名，也不是把流行组件列清单。核心是把"资格化/合成"这一族工作**拆到可执行的配方级**，并诚实标注每一步的成本与证据成熟度。

### 必须覆盖的锚点（核验它们实际支持什么、不支持什么）

- **CalibForge**（2608.06352）：solver-relative 校准的 single/multi-solver/contrastive 四档，5431 任务，匹配 1300 任务的 Terminal-Bench 消融，64×H20 全参数 SFT（注意：不是在线 RL）。核验：公开了多少训练/生产代码？solver-style leakage 是否被独立排除？
- **Envs-FORGE**（2608.14312）：verifier 通过率→逐 seed 合成动作策略、6 方向动作+MILP、同步改写五件套、DataArc-SynData-Toolkit 开源完整度。
- **prime-rl v0.9.0 admission gates + composable curricula + task sampling**（GitHub release，2026-08-25）：读实现代码，它的 gate 判什么、在训练循环哪里生效、与"训练资格治理"是不是一回事。
- **RLVE**（2511.07317）：adaptive difficulty 的真实训练消融、1.1K H100 GPU-hour 披露、能否迁移到 agent 长轨迹。
- **Hardening Agent Benchmarks**（2606.08960）：hacker-fixer loop 的负结果（攻击率→0 同时良性通过率→0），verifier 完整性约束。
- **Nebius / SWE-rebench**：14% 执行验证存活率、1 人日/任务人工核验、reward hacking 实录（git 抓答案）。

### 主动逃离锚点

用不含上述项目名的问题词继续搜：task learnability、curriculum for agentic RL、verifier reliability、solver-relative difficulty、synthetic environment acceptance rate、reward hacking in coding RL、oracle-free difficulty estimation、negative results in environment curation。目标找到 5+ 个锚点外的一手来源。

## 期望输出

### 1. 搜索与覆盖说明
检查了哪些团队/论文/仓库/数据集，哪些是锚点外发现，哪些区域仍可能遗漏。

### 2. 配方拆解（本轮核心）
把"资格化 + 难度控制 + 合成"拆成 4~6 个**可独立评估的机制**（例如：solver-relative pass-rate 分桶、verifier 对抗加固、oracle-free 难度估计、失败驱动定向合成、在线合成动作策略、difficulty-adaptive sampling）。每个机制：
- 它判定/生产什么，输入输出是什么；
- 最强一手证据（含证据等级 I/C/T/A/R）与主要负证据；
- 在 216 题量级下的**成本估算**（API solver 调用次数、CPU-hour、GPU-hour、人工核验量——能引用披露就引用，不能就标 unknown 并给数量级推断）；
- 是否有低成本探针（不训练即可证伪）。

### 3. 性价比排序
对上述机制给"高性价比 / 需关键探针 / 当前不划算"三档，并说明本项目资源下的理由。重点回答共用问题：solver-relative 校准在 216 题上需要多少 API/GPU 预算？

### 4. 贯通性判断
哪些机制只停在"任务采样层"（像 prime-rl admission gates），哪些能真正贯通到"训练资格 + 轨迹事实 + 真实增益归因"？这个区别对本项目的研究差异点很关键。

### 5. 证据附录
按机制列承重来源：直接 URL + 日期 + 版本 + 定位（章节/表格/代码路径/commit）+ 证据等级 + discovery origin（provided_anchor / independent_search）。

本轮给"高潜力 / 需关键探针 / 当前不适合"初步分类，不选唯一最终配方。
