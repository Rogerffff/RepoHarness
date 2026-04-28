# Claude Code AI Core 阅读导引

## 这篇解决什么问题

这组文档只回答一个问题：如果把 Claude Code 当成一个“会调用模型、会调用工具、会派生子 agent、会接入 MCP 的 AI 执行宿主”，它的核心设计到底是什么。

这里不讲 UI 渲染细节，不讲 Ink 组件树，也不讲性能 profiling。我们只关心下面这条主链：

`用户输入 -> 上下文组装 -> 模型请求 -> tool_use -> 权限判定 -> 工具执行 -> tool_result -> 多轮继续 -> Agent/MCP 扩展`

## 先说明仓库现实状态

当前仓库有一个必须先说清的现实差异：

- `README.md` 仍把仓库描述成 2026-03-31 之后的 Python-first porting workspace。
- 但当前工作树里的 `src/` 实际上是一整套未跟踪的 TypeScript Claude Code 源码快照。
- `src_current/` 里反而是 Python 版本的小型 port。

因此，这组文档的唯一分析对象是 `src/` 里的 TypeScript 快照，而不是 `README.md` 所描述的 Python 主线。

## 这套系统到底是什么

最容易误解的一点，是把 Claude Code 看成“一个 CLI 程序”。更准确的说法是：

Claude Code 是一个以模型循环为核心、以工具系统为执行面、以权限系统为安全边界、以 AgentTool 为多 agent 扩展面、以 MCP/skills/plugins 为生态扩展面的宿主平台。

从 AI 核心视角看，它大致由 6 层组成：

1. 启动与会话装配层
2. 对话与查询引擎层
3. 工具与权限层
4. Agent 与任务层
5. MCP / skills / plugins 扩展层
6. 远程执行与桥接层

## 核心类型与职责

虽然这是导引篇，但你一开始就应该先认住后文最常出现的核心类型：

| 类型 | 作用 |
| --- | --- |
| `QueryParams` | `query()` 这一轮对话循环的输入包 |
| `QueryEngineConfig` | headless / SDK 模式下的长期会话配置 |
| `Tool` | 模型可调用能力的统一抽象 |
| `ToolUseContext` | 工具调用时可见的运行时上下文 |
| `ToolPermissionContext` | 工具权限状态与规则集合 |
| `Command` | slash command / skill / 本地命令的统一抽象 |
| `AgentDefinition` | 一个 agent 类型的声明式定义 |
| `LocalAgentTaskState` | 本地 agent 任务在 `AppState` 里的状态 |
| `RemoteAgentTaskState` | 远程 agent 任务在本地侧的镜像状态 |
| `ScopedMcpServerConfig` | MCP server 配置与来源标签 |

## AI 核心源码主地图

下面这份索引是本次阅读的“主战场”。如果一个目录不在这里，它大概率不属于这组文档的重点。

| 主题 | 关键文件 |
| --- | --- |
| 启动入口 | `src/entrypoints/cli.tsx`, `src/main.tsx`, `src/entrypoints/init.ts`, `src/setup.ts` |
| 对话引擎 | `src/query.ts`, `src/QueryEngine.ts`, `src/query/config.ts`, `src/query/deps.ts` |
| 上下文与 prompt | `src/utils/queryContext.ts`, `src/context.ts`, `src/constants/prompts.ts`, `src/utils/messages/*` |
| 用户输入处理 | `src/utils/processUserInput/processUserInput.ts`, `src/utils/processUserInput/processSlashCommand.tsx`, `src/utils/processUserInput/processTextPrompt.ts` |
| 工具抽象 | `src/Tool.ts`, `src/tools.ts`, `src/services/tools/toolExecution.ts`, `src/services/tools/toolOrchestration.ts`, `src/services/tools/StreamingToolExecutor.ts` |
| 权限与沙箱 | `src/utils/permissions/permissions.ts`, `src/utils/permissions/permissionSetup.ts`, `src/utils/permissions/filesystem.ts`, `src/utils/sandbox/sandbox-adapter.ts` |
| Agent | `src/tools/AgentTool/AgentTool.tsx`, `src/tools/AgentTool/runAgent.ts`, `src/tools/AgentTool/agentToolUtils.ts`, `src/tools/AgentTool/loadAgentsDir.ts` |
| 任务系统 | `src/Task.ts`, `src/tasks.ts`, `src/tasks/LocalAgentTask/LocalAgentTask.tsx`, `src/tasks/RemoteAgentTask/RemoteAgentTask.tsx` |
| MCP | `src/services/mcp/client.ts`, `src/services/mcp/config.ts`, `src/services/mcp/types.ts`, `src/services/mcp/useManageMCPConnections.ts` |
| skills / commands | `src/commands.ts`, `src/types/command.ts`, `src/skills/loadSkillsDir.ts`, `src/tools/SkillTool/SkillTool.ts` |
| plugins | `src/utils/plugins/pluginLoader.ts`, `src/utils/plugins/loadPluginCommands.ts`, `src/utils/plugins/loadPluginHooks.ts` |
| 远程与桥接 | `src/remote/*`, `src/server/*`, `src/bridge/*`, `src/utils/teleport.ts` |

## 这组文档的阅读顺序

建议严格按顺序读：

1. `00-reading-guide.md`
2. `01-startup-to-query-entry.md`
3. `02-dialogue-engine-and-context.md`
4. `03-tools-permissions-and-plan-mode.md`
5. `04-agenttool-tasks-and-remote-execution.md`
6. `05-mcp-plugins-and-skills.md`
7. `06-end-to-end-ai-sequences.md`

这个顺序背后的原因是：

- 先知道系统怎么启动，才知道 query 从哪里来。
- 先知道 query 和上下文怎么工作，才知道工具为什么以这种方式被调用。
- 先知道工具和权限，才知道 agent 为什么要分同步、异步、本地、远程。
- 先知道 agent 主链，才容易看懂 MCP、skills、plugins 如何接到这条链上。

## 控制流分步讲解

如果你现在只想先记住 Claude Code AI 主链的最粗轮廓，可以先抓这一条：

1. `cli.tsx` / `main.tsx` 负责装配会话。
2. `processUserInput()` 把用户输入转成内部消息。
3. `fetchSystemPromptParts()` 构造稳定上下文前缀。
4. `query()` 调模型，得到 text 或 `tool_use`。
5. 工具系统与权限系统处理 `tool_use`。
6. `tool_result` 回流成下一轮消息。
7. 如果调用 `AgentTool`，同一套 query loop 会在子上下文里再次运行。
8. 如果接入 MCP，外部能力会先归一化为内部 tool/command/resource，再进入同一执行面。

## 建议带着什么问题读

每一篇都建议带着这几个问题去看：

1. 这一步是在“装配上下文”，还是在“执行模型循环”，还是在“执行外部动作”？
2. 数据是存在消息里，还是存在 `ToolUseContext` 里，还是存在 `AppState` 里？
3. 这一层是在做能力注册，还是在做权限裁剪，还是在做真正执行？
4. 这个 abstraction 是给主线程用的，还是给子 agent 用的，还是给 headless/SDK 用的？

## 本次阅读的范围边界

明确不展开的内容：

- `src/screens/REPL.tsx` 的 UI 细节
- `src/components/*` 的渲染组件
- `src/ink/*` 的终端渲染机制
- 页面/弹窗/菜单的视觉逻辑
- 启动性能优化、懒加载、profile 指标本身

这些内容可能会在源码里被提到，但这里只在它们影响模型执行链路时顺带解释。

## 关键设计权衡

这组文档刻意采用“从模型主链反推系统”的读法，而不是“从目录树平铺模块”的读法。

原因是：

- Claude Code 的真正复杂度在于跨模块闭环，而不在于目录数量本身。
- 先抓 `query -> tools -> permissions -> agents -> MCP` 的执行链，更容易建立系统感。
- UI、Ink、组件树虽然也重要，但它们不是这次学习 Claude Code AI 本体的最快路径。

## 易错点与误解

### 误解 1：只要把 `main.tsx` 看懂就算看懂系统

不够。`main.tsx` 只是装配中心，真正的 AI 主循环在 `query()`。

### 误解 2：MCP、skills、plugins 是三块彼此独立的能力

不是。它们最后都会被统一吸收到 command/tool/resource 宿主里。

### 误解 3：多 agent 只是“额外功能”

也不对。`AgentTool` 是 Claude Code 把单 agent loop 扩展成协作系统的关键支点。

## 快照缺口与验证边界

本次分析过程中，至少发现了两个要明确记录的缺口：

- `src/services/mcp/client.ts` 动态引用了 `src/skills/mcpSkills.ts`，但快照中没有这个文件，因此 MCP skills 的某些细节只能确认“有接线”，不能确认完整实现。
- `SendMessageTool` 相关路径会动态引用 `src/bridge/peerSessions.js`，但这份快照里没有看到对应源码，因此跨 session bridge 发送的某些细节只能标为缺口。

文档里凡是碰到这种情况，都会显式写成“快照缺口说明”，不会猜测实现。

## 如何使用这组文档

推荐一种高效用法：

1. 先读每篇前两节，建立概念图。
2. 再按文中的“关键源码”打开对应文件。
3. 只追主链函数，不要一开始就把所有 helper 全读完。
4. 读完 `06-end-to-end-ai-sequences.md` 后，再回到前面的章节做二刷。

如果你后面还想继续扩展，最自然的下一步会是：

- 补一组 UI/REPL 交互文档
- 补一组远程桥接与 direct-connect 文档
- 补一组 compact / memory / prompt-cache 细化文档

## 继续阅读建议

下一篇先看 [01-startup-to-query-entry.md](./01-startup-to-query-entry.md)。它会把“Claude Code 如何从 CLI 入口走到模型查询入口”完整串起来，为后面的 query / tools / agents 打底。
