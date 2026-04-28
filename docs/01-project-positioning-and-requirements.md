# Project Positioning And Requirements

## 项目背景

当前 agentic training 正在从单轮答案优化转向可执行环境中的长轨迹训练。大厂报告反复强调 executable environments、tool-use rollout、environment feedback、sandbox、verifier、trajectory diagnostics 和 training-evaluation harness consistency。

RepoHarness 的定位是把这些趋势落到一个轻量、训练友好、可评测的软件工程 agent harness 设计中。

## 与已有项目的互补关系

CaRR DeepSearch 项目提供了长轨迹搜索智能体强化学习和异步 rollout 基础设施的经验基础。它覆盖 search/open/find 工具、多轮浏览器环境、reward history、C-GRPO 和长轨迹诊断，但不覆盖真实仓库修改、测试反馈和软件工程任务。

Coding GRPO 项目提供了 verifier-based coding post-training 的经验基础。它覆盖 `verl + vLLM + SandboxFusion`、shared verifier、代码执行反馈、稠密可验证奖励和 checkpoint 评测，但主要面向算法题代码生成，不是多轮软件工程 agent harness。

RepoHarness 补齐第三块：真实或半真实仓库、多文件编辑、终端命令、测试执行、patch diff、trajectory collection、verifier-aligned reward metadata 和训练评测一致性。

## 第一版目标

第一阶段是设计和骨架，不写实际功能代码。最终设计必须足够清楚，让后续实现者可以直接进入实现。

第一版未来实现目标包括：

- 计划支持真实或半真实 repository-level software engineering tasks。
- 计划支持 `read / search / edit / bash / test` 工具族。
- 计划支持多轮 action-observation agent loop。
- 计划使用同一套 verifier 生成离线评测结果和训练 reward metadata。
- 计划记录 JSONL transcript 和 events。
- 计划支持批量 evaluation runner。
- 计划支持导出 SFT JSONL、reinforcement learning rollout JSONL 和 preference pair JSONL。

## 非目标

第一版不做：

- 生产级安全沙箱。
- 完整企业权限系统。
- 完整插件市场。
- 完整远程多代理平台。
- 新强化学习算法。
- 完整 SWE-Bench 复现。
- 大规模异步 rollout 集群。
- 完整 GitHub Issue 到 Pull Request 自动闭环。

## 成功标准

设计阶段成功标准：

- 核心设计文档覆盖 agent loop、工具系统、workspace/sandbox、task adapter、verifier、trajectory、export、scaffold 和 diagnostics。
- 每篇模块文档都有目标、接口、数据流、参考 Claude Code 模块、边界和测试点。
- 文档明确哪些能力第一版实现，哪些只预留扩展。
- 多子代理审查后形成修订记录。

未来实现阶段成功标准：

- 能在 20 到 50 个软件工程任务上运行。
- 每个任务都有 patch、测试结果、trajectory、verifier 输出和 metrics。
- 能比较 single-shot patch、simple ReAct 和 planner-coder-verifier scaffold。
- 能导出训练可用轨迹数据。

## 简历叙事

推荐标题：

> Training-Aware Software Engineering Agent Harness with Verifier-Aligned Trajectory Collection

推荐核心表述：

> 在设计文档和 Python 骨架中规划面向真实仓库软件工程任务的轻量级 agent harness，统一设计工具执行、Docker-based executable repository environments、轨迹记录、verifier-aligned reward metadata、离线评测和训练数据导出。

这条表述适合设计阶段简历。进入实现阶段后，应根据实际完成的功能把“规划”“设计”逐步替换为“实现”“评测”“导出”，避免把尚未完成的运行时能力说成已经交付。
