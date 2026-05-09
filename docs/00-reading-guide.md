# RepoHarness Reading Guide

## 一句话定义

RepoHarness 是一个面向 agentic training 和 post-training 的轻量级软件工程智能体 Harness。它的目标是把真实或半真实仓库任务转化为可执行、可审计、可导出的训练轨迹。第一版已经实现本地微型仓库最小闭环；第二版扩展 provider、run metadata、导出审计和多 rollout；第三版交付 Docker-based executable repository environment、真实 repository-level task、固定 SWE-Bench-like 小子集和 acceptance bundle；第四版继续补强任务冻结、单机 rollout orchestration、工具生命周期审计、agent run integration、trajectory store、export quality、cards 和 final acceptance machinery。

截至 2026-05-05，V4 已完成复核问题修复并重新生成验收证据。最新 V4 closure commit 为 `e0da89c test: refresh V4 acceptance evidence after hardening`，完整测试结果为 `712 passed`，修复后最终验收目录为 `runs/v4-final-rerun-20260504T194758Z/`。本轮文档同步后，当前文档哈希可复核的 bundle 是 `runs/v4-final-rerun-20260504T194758Z/acceptance/acceptance_bundle_manifest_doc_sync_20260505T075410Z.json`。阅读和引用 V4 结论时，应使用该目录下的 acceptance inputs、acceptance report、文档同步后的 acceptance bundle 和 final acceptance command log。

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

理解历史 V1 最小闭环：

1. `01-project-positioning-and-requirements.md` 中的“第一版最小可运行闭环”。
2. `02-system-architecture.md` 中的“第一版 CLI / Eval Runner 操作面”。
3. `11-object-model-config-and-data-flow.md` 中的 `RunConfig`、核心对象清单和端到端数据流。
4. `08-trajectory-store-and-training-export.md` 中的 `RunRecorder`、`TranscriptRecord` 和 artifact manifest。

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

准备对照工业界 agentic training 技术报告：

1. `13-agentic-technical-report-reading-map.md`

准备接手当前 V4 状态或 V5 范围设计：

1. `docs/v4/scope-and-roadmap.md`
2. `docs/v4/implementation-plan.md`
3. `docs/v4/review/implementation-plan-review.md`
4. `docs/v4/final-acceptance.md`
5. `docs/v4/walkthrough.md`
6. `docs/v4/review/implementation/08-final-acceptance-review.md`
7. `runs/v4-final-rerun-20260504T194758Z/` 下的最新修复后 acceptance evidence。
8. `docs/v5/scope-and-roadmap.md`
9. `docs/v5/review/scope-review.md`

## 项目边界

RepoHarness 的历史第一版不是完整产品，而是在少量 micro-repo task 上跑通一条可复盘闭环：任务加载、workspace 准备、fake model 或 replay model 工具调用、工具结果回流、final patch 冻结、strict final verifier、reward metadata、metrics 和训练导出样例。当前代码已经推进到 V4，但仍保持单机优先和训练轨迹生产链路定位。

它不是 Claude Code、Cursor、OpenHands 或 SWE-agent 的复刻。它借鉴产品级 agent 系统的关键架构不变量：统一 agent loop、工具能力契约、权限判断、工具结果回流、轨迹存储和失败诊断。

它也不是生产级安全沙箱。第一版使用本地进程执行边界和保守权限规则；第三版开始交付真实 Docker-based executable repository environment；第四版增加 resource lock、checkpoint state 和更多审计事实。即便如此，Docker execution mode 仍只表示可复现执行边界，不声称具备完整网络隔离、逃逸防护、多租户安全或企业权限能力。

## 核心术语

- agent loop：模型输出、工具调用、工具结果回填、继续推理的循环。
- tool call：模型请求 Harness 执行某个具体工具的结构化动作。
- tool result：工具执行后的结构化观察结果，会进入下一轮模型上下文。
- trajectory：一次任务运行中的消息、工具调用、观察、测试结果和终止信息。
- verifier：将代码修改结果转成可评测信号的组件，例如测试执行器和日志解析器。
- reward metadata：由 verifier 和成本信息生成的训练奖励候选字段，不等于新的强化学习算法。
- sandbox：任务执行边界。RepoHarness 支持 local process 和 Docker-based executable repository environment，但 Docker 不等同于生产级安全沙箱。
- task adapter：把任务数据集转换为 RepoHarness 可执行任务格式的适配层。
- scaffold：控制模型如何规划、调用工具和利用反馈的策略层，例如 simple ReAct 或 planner-coder-verifier。
- run config：一次批量评测或单任务运行的配置对象，包含模型、权限模式、执行模式、预算、输出目录和可复现实验字段。
- baseline result：正式 agent 运行前的任务可执行性检查结果，用来判断任务是否有效、是否稳定、哪些测试属于 fail-to-pass 或 pass-to-pass。

## Claude Code 参考材料

本仓库保留两类本地参考：

- `reference/claude-code-docs/`：Claude Code 架构分析文档。
- `reference/claude-code-typescript-src/`：Claude Code TypeScript 参考源码，默认不提交到 Git。

这些材料只用于设计参考，不进入 RepoHarness 主实现。
