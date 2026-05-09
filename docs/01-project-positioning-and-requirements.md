# Project Positioning And Requirements

## 项目背景

当前 agentic training 正在从单轮答案优化转向可执行环境中的长轨迹训练。大厂报告反复强调 executable environments、tool-use rollout、environment feedback、sandbox、verifier、trajectory diagnostics 和 training-evaluation harness consistency。

RepoHarness 的定位是把这些趋势落到一个轻量、训练友好、可评测的软件工程 agent harness 设计中。

## 与已有项目的互补关系

CaRR DeepSearch 项目提供了长轨迹搜索智能体强化学习和异步 rollout 基础设施的经验基础。它覆盖 search/open/find 工具、多轮浏览器环境、reward history、C-GRPO 和长轨迹诊断，但不覆盖真实仓库修改、测试反馈和软件工程任务。

Coding GRPO 项目提供了 verifier-based coding post-training 的经验基础。它覆盖 `verl + vLLM + SandboxFusion`、shared verifier、代码执行反馈、稠密可验证奖励和 checkpoint 评测，但主要面向算法题代码生成，不是多轮软件工程 agent harness。

RepoHarness 补齐第三块：真实或半真实仓库、多文件编辑、终端命令、测试执行、patch diff、trajectory collection、verifier-aligned reward metadata 和训练评测一致性。

## 当前实现状态

本文最初是基础设计和第一版实施前的定位文档。当前仓库已经经历 V1 到 V4 的连续实现：

- V1 已经跑通本地 micro-repo task 的最小闭环。
- V2 已经扩展 run metadata、导出审计、多 rollout、scaffold、真实 provider 路径和 V2 final acceptance。
- V3 已经交付 Docker-based executable repository environment、repository-level task、固定 SWE-Bench-like 小子集、source materialization、context compaction、resume、export audit 和 acceptance bundle。
- V4 已经完成 implementation，并增加 task source freeze、rollout orchestration、resource lock、checkpoint state、tool lifecycle audit、agent run integration、trajectory store 字段级检查、export quality、reward / preference pair 审计和 cards。

截至 2026-05-05，V4 已完成复核问题修复并通过修复后最终验收。最新 V4 closure commit 为 `e0da89c test: refresh V4 acceptance evidence after hardening`，完整测试结果为 `712 passed`，修复后最终验收目录为 `runs/v4-final-rerun-20260504T194758Z/`。因此，下面关于“第一版目标”和“未来实现阶段成功标准”的内容应作为历史设计边界理解，不应覆盖 `docs/v4/` 中的最新范围、审查记录、修复后 acceptance evidence 和 `docs/v5/` 中的下一阶段范围设计。

## 第一版目标

第一阶段是设计和骨架，不写实际功能代码。最终设计必须足够清楚，让后续实现者可以直接进入实现。

第一版未来实现目标包括：

- 计划支持真实或半真实 repository-level software engineering tasks。
- 计划支持 `read / grep-style search / edit / bash / test` 工具族。
- 计划支持多轮 action-observation agent loop。
- 计划使用同一套 verifier 生成离线评测结果和训练 reward metadata。
- 计划记录 JSONL transcript 和 events。
- 计划支持批量 evaluation runner。
- 计划支持导出 SFT JSONL、reinforcement learning rollout JSONL 和 preference pair JSONL。

## 第一版最小可运行闭环

正式开始实现时，第一版最小闭环应先收敛到一个可验收、可调试、可复盘的范围，而不是一开始追求完整真实模型评测平台。

第一版最小闭环验收标准：

- 能加载 3 到 5 个自建 micro-repo task。
- 能创建 source checkout、setup workspace、agent run workspace 和 verification workspace。
- 能运行 baseline verifier 和 strict patch replay final verifier。
- 能用 fake model 或 replay model 跑通 tool call 到 tool result 的协议，不要求第一步就接入真实模型供应商。
- 能实现 `list_files`、`read_file`、`grep`、`edit_file`、`create_file`、`bash`、`run_tests` 和 `git_diff` 的最小版本。
- 能生成 `transcript.jsonl`、`events.jsonl`、`artifacts.json`、`dependency_state.json`、`final.patch`、`final.diff`、`verifier.json`、`reward.json`、`metrics.json` 和 `summary.md`。
- 能导出至少一条监督微调 JSONL 和一条 reinforcement learning rollout JSONL。

第一版之后的早期规划曾设想继续扩展真实模型长轨迹、多 scaffold 对比、20 到 50 个任务、preference pair 批量生成和 Docker execution mode 的完整覆盖。这个规划用于解释路线演进，不是当前 V4 硬门；当前 V4 门槛以 `docs/v4/` 和最新复核记录为准。

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

历史未来实现阶段成功标准：

- 第一版最小闭环先在 3 到 5 个 micro-repo task 上稳定运行。
- 历史愿景曾设想扩展到 20 到 50 个软件工程任务，但这不是当前 V4 硬门。
- 每个任务都有 patch、测试结果、trajectory、verifier 输出和 metrics。
- 能比较 single-shot patch、simple ReAct 和 planner-coder-verifier scaffold。
- 能导出训练可用轨迹数据。

当前 V4 不把“20 到 50 个任务”作为硬门。V2 曾扩展任务级 fixture；V3/V4 的当前验收重点是可审计任务定义、真实仓库 / SWE-Bench-like 证据链、accepted / auditable task gate、trajectory production、export audit 和 acceptance bundle。具体数量和门槛以对应版本的 scope、implementation plan、final acceptance 和最新复核记录为准。

## 简历叙事

推荐标题：

> Training-Aware Software Engineering Agent Harness with Verifier-Aligned Trajectory Collection

推荐核心表述：

> 在设计文档和 Python 骨架中规划面向真实仓库软件工程任务的轻量级 agent harness，统一设计工具执行、Docker-based executable repository environments、轨迹记录、verifier-aligned reward metadata、离线评测和训练数据导出。

这条表述适合设计阶段简历。进入实现阶段后，应根据实际完成的功能把“规划”“设计”逐步替换为“实现”“评测”“导出”，避免把尚未完成的运行时能力说成已经交付。
