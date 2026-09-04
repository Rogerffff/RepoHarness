# 环境层调研共用 Brief（Pro-Env-1 / Pro-Env-2 / codex 共用）

**日期：2026-09-02。** 本文是本轮环境层调研三个任务书的共用背景。只陈述项目事实与资源边界，不预设结论，不给候选方向清单。

## 1. 项目是什么

代号 RepoHarness / RH2：一个面向交互式软件工程 agent 的**强化学习后训练基础设施**，目标是产出一个对齐前沿基座团队实践的简历级项目。当前基座模型 = **Qwen3-30B-A3B**（MoE，3B activated），训练后端 = **miles**（slime 的 fork，第三方维护了完全异步基础设施），rollout = SGLang，训练 = Megatron，首个算法闭环 = fully-async GRPO + faithful DIS（我们自研的重要性采样修正 loss）。硬件 = **8×RTX PRO 6000 Blackwell**（96GB/卡，PCIe 无 NVLink），单机。

## 2. 环境层现状（事实，非目标）

- **已建成且极硬**：216 道 SWE-Gym Lite 任务的数据身份链（ingestion → 三分 bundle〔public/grading/validation〕→ EnvironmentPackage → 防篡改 trusted loader，四级 digest 链，133 项定向测试）。
- **零实现**：环境质量链——empty/golden/determinism 四门 runner、受控评分入口 `grade_controlled_patch`、EnvValidationReport、TaskQualityEvaluator、anti-cheat git 净化。设计文档齐备，代码零行。
- **未接线**：216 题在训练 runtime 上零消费者，miles 链今天固定吃 8 道 SWE-bench Verified 探针题。
- **held-out**：542 候选一题未冻结，其中 450 题依赖从未发生的 R2E-Gym ingestion（~2.3TiB 镜像）。
- **可复用**：本地 pin 的 `reference/research-environments`（Prime Intellect，73 环境）与 `reference/verifiers`（v1，pin 在 2026-07-03）；miles 官方带 Harbor 集成（`harbor-miles-v0.20.0`）。

## 3. 已有的方向框架（供理解语境，非本轮结论）

分层交付兜底：无论最终实验做 OPD/MOPD、多 harness 泛化还是别的，**infra 层和环境层都是简历项目的基本交付**。已暂定的主线：A（可验证环境生产与训练资格，第一优先）、B（多 harness 跨接口泛化）、C（OPD/MOPD 条件式）。环境层直接服务 A、并为 C 提供第二个 specialist 域、为评测层提供公共可比面。

## 4. 已覆盖的外部资料（不要复述，只找增量）

RLVE、CalibForge(2608.06352)、RACES/EvoEnv、Hardening Agent Benchmarks(2606.08960)、R2E-Gym、SWE-Gym、SWE-rebench V2、Prime Intellect 365K environments 博客、Envs-FORGE(2608.14312)、Endless Terminals(2601.16443)、SWE-smith(2504.21798)、Surge 办公 RL(2608.01604)、Nebius SWE-rebench 基建博客、K3 知识图谱任务生产、GLM-5.3 真实工作模式合成环境、MAI-Thinking-1 环境工厂、Terminal-Bench 2.1 修复事件、prime-rl v0.9.0 admission gates、蚂蚁 AEnvironment、字节 CUDA-Agent、MiniMax M2.1 博客。

## 5. 证据分级要求（三个任务书共用）

对承重结论标注证据成熟度，严格区分：

```text
I — 仅提出想法（论文/博客提出，无公开实现或训练）
C — 已有代码/配置/数据/评测实现
T — 已实际训练（作者报告模型用该方法训练过）
A — 有受控消融（固定主要变量后比较关键设计）
R — 有独立复现（非原作者团队复现主要现象）
```

"框架支持某算法" ≠ "旗舰模型用过该算法"。未披露的硬件/数据量/时长/费用一律记 `unknown`，不用行业印象补齐。二手文章可作线索，核心技术结论必须附一手 URL + 章节/表格/代码路径/commit 中至少一种可复核定位。

## 6. 资源边界（判断"能不能在本项目做"时用）

- GPU：8×RTX PRO 6000（96GB），单机 PCIe 无 NVLink。30B-A3B 一次 4-train+4-rollout 探针实测约 1387 秒/step、rollout wait ratio 约 0.82（rollout-bound）。
- 环境生产可用：本机 Docker、x86 CPU 云实例（四门评分估算 216×8≈1730 次评分，16 核/1TB ~$0.3-0.8/h，1-2 天 ~$15-40）、Codex/Claude 订阅 agent 额度、模型 API。
- 正式 GPU 训练预算未冻结；首训阶段已重定义为"链路完整性短跑"而非独立能力宣称阶段。
