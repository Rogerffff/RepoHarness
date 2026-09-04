<!-- 注意：本文件（2026-08-18）与 summary_calibforge_solver_calibration.md（2026-09-02，
env_discovery_20260902 批次）是同一篇论文（2608.06352）的两份摘要。数字一致无冲突。
本文独有：末尾"资格状态机"四态映射（all-pass/all-fail/strong-weak/weak-pass-strong-fail）
+ SWE-Bench Pro 被后续审计削弱的注记。新文件独有：标准六段格式 + solver panel/开源范围
细节。是否合并/删其一由 owner 定。 -->

# CalibForge：面向可学习终端任务的对抗式 solver 校准

## 论文与定位

- 论文：<https://arxiv.org/abs/2608.06352>
- 时间：2026-08-06，v1；截至 2026-08-18 尚无独立复现。
- 核心定位：训前的 `solver-relative calibration`。它不进行在线 RL，而是用外部 solver 的执行结果反复修改任务，使任务落入指定能力区间，再蒸馏成功轨迹进行全参数 SFT。

## 方法

任务生产流程：

```text
clue / 外部资料
→ 编写 instruction、Docker 环境、verifier
→ structural validation
→ author self-solving
→ solver panel 执行
→ 根据 verified outcome 与轨迹修改任务
→ 重新验证与执行
→ 满足目标关系后保留
```

两种校准方式：

- Multi-solver：DeepSeek-V4-Flash、GLM-5、Kimi K2.5 中至少一个成功、至少一个失败。
- Contrastive：DeepSeek-V4-Pro 成功且 DeepSeek-V4-Flash 失败。

一次 solver attempt 最多 100 steps、30 分钟；一项任务最多 50 轮校准。

## 核心实验

- 最终产生 5,431 项 Harbor-style terminal tasks：1,263 multi-solver，4,168 contrastive。
- 所有候选已经通过 structural validation 和 self-solving，但第一次 contrastive probe 只有 19% 满足 strong-pass/weak-fail；反复修订后累计接受率为 96%。这说明“环境能运行、已知解能通过”不能替代行为资格检查。
- 在每组 1,300 个任务、相同 teacher 蒸馏与 SFT 配方的消融中：

| 构造方式 | TB 2.0 |
|---|---:|
| 无外部 solver | 22.47% |
| 单 solver feedback | 24.34% |
| Multi-solver | 29.21% |
| Contrastive | 31.09% |

Multi-solver 组的保留 SFT 轨迹并不更多，因此收益不能只用轨迹数量解释。

## 训练与资源

- 成功轨迹由 DeepSeek-V4-Pro 蒸馏。
- 学生：Qwen3-30B-A3B-Instruct、Qwen3.5-35B-A3B。
- 全参数、多轮 SFT；10 epochs；131,072 context；global batch 128；64×H20。
- 论文未公开 author/solver API 总成本与总运行时间。

## 关键局限

- 证据是 SFT，不证明该校准会提高在线 GRPO 的 nonzero-advantage ratio。
- author、自解、strong solver、最终 teacher 都大量依赖 DeepSeek-V4-Pro，可能形成模型与 scaffold 偏好。
- 单次 pass/fail 有采样噪声，论文没有对同一 solver 做重复运行和置信区间。
- 反复修改到 strong-pass/weak-fail 可能产生对固定 solver panel 的过拟合。
- 主评测仍使用 Terminal-Bench 2.0；SWE-Bench Pro 也已被后续审计削弱。
- 最终数据与模型权重已公开，但核心 authoring/calibration/revision 流水线没有公开实现。

## 对 RepoHarness 的意义

可迁移的是资格状态机，而不是 64×H20 SFT：

```text
all-pass        → 检查过易、泄漏、shortcut
all-fail        → 区分过难、歧义、环境坏、verifier 坏
strong/weak 分歧 → 进入目标 learnable-zone 候选
weak-pass/strong-fail → 检查随机性、harness 差异和 verifier 过度规定
```

必须额外记录 solver/model/harness/revision/budget、重复尝试、任务修订 lineage 和置信区间。外部 solver panel 只能做训前筛选；是否对当前训练 checkpoint 真有梯度，仍需目标 policy rollout 验证。
