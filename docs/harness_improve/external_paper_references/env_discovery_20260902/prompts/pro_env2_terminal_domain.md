# Pro-Env-2：terminal 作为第二可验证域的尽调

先读 `common_env_brief.md`。你是一名独立的开放权重模型 post-training 研究员，本轮只做**证据审计与可行性尽调**，不写代码、不给完整执行计划。检索截止：覆盖到 2026-09-02。

## 背景与任务

本项目计划在 SWE 之外扩展**第二个可验证训练域**，当前倾向 terminal 域（载体 = Harbor 任务格式，本地已有 Prime Intellect 的 terminal_lego ~13.8k / tmax 14.6k / terminal_bench_2 等薄壳环境）。你的任务是审计"terminal 作为 RL 训练域"的完整外部证据，回答：

> **terminal 域作为第二训练域，其任务供给、verifier 可靠性、已知失败模式、以及"训过什么规模模型得到什么增益"的证据链有多硬？它相对 SWE 域的边际价值（尤其对跨域迁移和第二 specialist）是否成立？**

### 必须覆盖的锚点

- **Endless Terminals**（2601.16443）+ 扩展（2602.21193）：程序化生成 3255+6170 任务的四段管线、可解性过滤、vanilla PPO Qwen2.5-7B 10.7%→53.3%。核验：管线可复现度？任务难度分布？与真实 Claude Code SWE 任务的差距。
- **Harbor / Terminal-Bench 生态**：Harbor Hub 训练用例、Terminal-Bench 2.1→3.0 演进、terminal_lego（私有 HF repo `PrimeIntellect/Terminal-Lego-15k`）的**可得性与许可**、tmax 数据来源与质量。这条尽量查清，因为它决定我们能不能真的拿到训练数据。
- **社区训练仓** `Danau5tin/terminal-bench-rl`（GRPO，32×H100）：真实训练配方与结果。
- **跨域迁移证据**：Surge 办公 RL（2608.01604）SWE-Bench Pro +5.8；有没有 terminal→SWE 或 SWE→terminal 的迁移数据？

### 主动逃离锚点

问题词：terminal agent RL training、containerized task generation、shell agent reward、terminal environment reward hacking、CLI agent benchmark contamination、executable task synthesis non-SWE。顺带核这两个环境生产细节（brief 已提及但需深挖）：**蚂蚁 AEnvironment**（内置 Mini Terminal/TerminalBench 的统一环境系统）、**MiniMax M2.1 博客**（10,000+ runnable PRs / 140,000+ 任务 / 三层 reward）。

## 期望输出

### 1. 搜索与覆盖说明

### 2. terminal 域证据审计
- 任务供给：有哪些公开可训练的 terminal 任务源？各自量级、生成方式、许可、可得性（能不能真的下载）。terminal_lego 私有 repo 到底能不能拿到。
- verifier 可靠性：terminal 任务的评分方式（test.sh/状态检查/LLM judge），已知的 reward hacking 与环境缺陷模式（对标 Terminal-Bench 2.1 修复事件）。
- 训练证据：谁用 terminal 环境训过什么规模的模型、什么算法、什么增益（证据等级 I/C/T/A/R）。

### 3. 边际价值判断
terminal 相对 SWE 的边际价值：(a) 能力覆盖差异（terminal 覆盖了 SWE 覆盖不到的什么）；(b) 跨域迁移证据（训 terminal 是否帮 SWE，反之）；(c) 作为 C 线第二 specialist 的适配性。诚实标注哪些是推断哪些有数据。

### 4. 可行性与成本
在 8×GPU + CPU 云 + Harbor 格式的条件下，接入 terminal 域的主要成本项（镜像分发、任务下载、verifier 适配、单位任务评分成本）。哪些是拦路石（如私有数据不可得）。

### 5. 证据附录
按主题列承重来源：URL + 日期 + 版本 + 定位 + 证据等级 + discovery origin。

给"terminal 作为第二域"一个初步判断：值得做 / 需先解决某个关键前置 / 有更好的第二域候选（若有，指出是什么及理由）。
