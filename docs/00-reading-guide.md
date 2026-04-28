# RepoHarness Reading Guide

## 一句话定义

RepoHarness 是一个面向 agentic training 和 post-training 的轻量级软件工程智能体 Harness 设计项目。它的目标是让未来实现能够在真实或半真实仓库任务中执行工具调用、收集轨迹、运行 verifier、生成 reward metadata，并导出监督微调或强化学习可用的数据。

核心闭环是：

```text
task -> executable workspace -> tools -> agent loop -> trajectory -> verifier -> reward/eval/export
```

## 阅读路径

快速了解项目定位：

1. `01-project-positioning-and-requirements.md`
2. `02-system-architecture.md`
3. `07-verifier-reward-and-evaluation.md`

准备实现核心 runtime：

1. `03-agent-loop-and-message-protocol.md`
2. `04-tool-system-and-orchestration.md`
3. `05-workspace-sandbox-and-permissions.md`
4. `06-task-dataset-and-environment-adapters.md`
5. `11-object-model-config-and-data-flow.md`

准备训练数据、评测和实验：

1. `07-verifier-reward-and-evaluation.md`
2. `08-trajectory-store-and-training-export.md`
3. `10-context-session-and-failure-diagnostics.md`
4. `12-resume-narrative-and-demo-artifacts.md`

准备扩展脚手架和多角色 agent：

1. `09-agent-scaffolds-and-multi-agent.md`
2. `10-context-session-and-failure-diagnostics.md`

准备面试快速阅读：

1. `01-project-positioning-and-requirements.md`
2. `02-system-architecture.md`
3. `07-verifier-reward-and-evaluation.md`
4. `12-resume-narrative-and-demo-artifacts.md`

## 项目边界

RepoHarness 第一阶段只交付设计文档和 Python 骨架，不实现具体功能代码。

它不是 Claude Code、Cursor、OpenHands 或 SWE-agent 的复刻。它借鉴产品级 agent 系统的关键架构不变量：统一 agent loop、工具能力契约、权限判断、工具结果回流、轨迹存储和失败诊断。

它也不是生产级安全沙箱。文档中使用 Docker-based executable repository environment 表述执行环境，不声称具备完整网络隔离、逃逸防护、审计、资源配额或企业权限能力。

## 核心术语

- agent loop：模型输出、工具调用、工具结果回填、继续推理的循环。
- tool call：模型请求 Harness 执行某个具体工具的结构化动作。
- tool result：工具执行后的结构化观察结果，会进入下一轮模型上下文。
- trajectory：一次任务运行中的消息、工具调用、观察、测试结果和终止信息。
- verifier：将代码修改结果转成可评测信号的组件，例如测试执行器和日志解析器。
- reward metadata：由 verifier 和成本信息生成的训练奖励候选字段，不等于新的强化学习算法。
- sandbox：任务执行边界。第一版只设计 local process 和 Docker execution mode。
- task adapter：把任务数据集转换为 RepoHarness 可执行任务格式的适配层。
- scaffold：控制模型如何规划、调用工具和利用反馈的策略层，例如 simple ReAct 或 planner-coder-verifier。
- run config：一次批量评测或单任务运行的配置对象，包含模型、权限模式、执行模式、预算、输出目录和可复现实验字段。
- baseline result：正式 agent 运行前的任务可执行性检查结果，用来判断任务是否有效、是否稳定、哪些测试属于 fail-to-pass 或 pass-to-pass。

## Claude Code 参考材料

本仓库保留两类本地参考：

- `reference/claude-code-docs/`：Claude Code 架构分析文档。
- `reference/claude-code-typescript-src/`：Claude Code TypeScript 参考源码，默认不提交到 Git。

这些材料只用于设计参考，不进入 RepoHarness 主实现。
