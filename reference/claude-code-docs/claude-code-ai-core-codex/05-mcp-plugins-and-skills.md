# MCP、Plugins 与 Skills

## 这篇解决什么问题

如果只看 `query()`、`Tool` 和 `AgentTool`，你会觉得 Claude Code 的能力边界是静态的。

但真正让它变成“可扩展 AI 宿主”的，是这三套扩展面：

1. MCP
2. plugins
3. skills

这篇要讲清：

- Claude Code 如何把外部 server 接成统一工具面
- 插件如何向系统注入 commands、hooks、agents、MCP servers
- skills 为什么最终被做成 `Command` 的一种
- 为什么 provenance、dedup、policy 会成为这一层的关键词

## 核心类型与职责

本篇最关键的类型如下：

| 类型 | 作用 |
| --- | --- |
| `ScopedMcpServerConfig` | 一个 MCP server 配置加上其来源标签 |
| `MCPServerConnection` | MCP client 连接的运行时表示 |
| `Command` | 扩展生态最终汇入的统一 command 结构 |
| `Tool` | MCP tools 与 built-in tools 统一后的执行抽象 |
| `LoadedPlugin` | plugin loader 归一化后的插件对象 |

从职责分层上看：

| 层 | 作用 |
| --- | --- |
| MCP | 提供 live tools / commands / resources |
| plugins | 扩展本地产品表面与运行时配置 |
| skills | 扩展 prompt 级能力与工作流入口 |

## 关键源码

- `src/services/mcp/config.ts`
- `src/services/mcp/client.ts`
- `src/services/mcp/types.ts`
- `src/services/mcp/useManageMCPConnections.ts`
- `src/utils/plugins/pluginLoader.ts`
- `src/utils/plugins/loadPluginCommands.ts`
- `src/utils/plugins/loadPluginHooks.ts`
- `src/plugins/builtinPlugins.ts`
- `src/skills/loadSkillsDir.ts`
- `src/skills/bundledSkills.ts`
- `src/tools/SkillTool/SkillTool.ts`
- `src/commands.ts`

## MCP：把外部 server 变成 Claude Code 运行时的一部分

从系统视角看，MCP 做的事情不是“调用一个外部 API”，而是：

把一个外部 server 的 capabilities 归一化成 Claude Code 自己的 runtime object。

### MCP 配置是多来源汇总的

`src/services/mcp/config.ts` 会把多个来源的配置汇总起来，例如：

- enterprise-managed
- user / local settings
- 项目级 `.mcp.json`
- plugin 提供的 MCP servers
- Claude.ai connector

这里最重要的不是配置字段本身，而是 `ScopedMcpServerConfig`。

它给每个 server 附上来源信息，例如：

- scope
- optional pluginSource

这一步非常重要，因为后面很多逻辑都依赖 provenance：

- dedup
- policy filter
- stale plugin cleanup

### MCP client 运行时的中心在 `client.ts`

`src/services/mcp/client.ts` 是 MCP 宿主中心。

它支持多种 transport：

- `stdio`
- `sse`
- `streamable http`
- `ws`
- IDE 特殊 transport
- in-process transport

对 Claude Code 来说，关键不是 transport 多样性本身，而是：

无论 transport 是什么，最后都要被归一化成：

- tools
- commands/prompts
- resources

### MCP server 接入后的统一产物

连接建立后，Claude Code 会把 server 能力拆成三类：

1. tools
2. commands/prompts
3. resources

其中：

- MCP tools 最终会变成 `Tool`
- MCP prompts/commands 最终会变成 `Command`
- MCP resources 会进入统一的 resource 列表，并通过通用资源工具访问

这意味着 Claude Code 不是把 MCP 当旁路系统，而是把它并入了自己的核心抽象层。

## MCP 为什么强调命名规范化与去重

一个直接问题是：如果外部 server 也有叫 `search` 的工具怎么办？

Claude Code 的做法是：

- 通过 `mcpStringUtils.ts` 构造带 server 前缀的规范名称
- 通过 signature 和 config 内容做 dedup，而不是只看显示名称

换句话说：

MCP 进入 Claude Code 之后，首先不是“可调用”，而是“先归一化，再命名，再并入统一注册表”。

## `useManageMCPConnections()` 是动态接入的关键

如果说 `config.ts` 决定“应该连谁”，那么 `useManageMCPConnections()` 决定“怎么把它们接进运行时”。

这层主要做几件事：

1. 计算待连接 server 集合
2. 分阶段连接
3. 订阅 tools/commands/resources 变更
4. 将结果写入 `AppState.mcp`

所以从运行时视角看，MCP 不是一次性静态加载，而是：

一个可持续变化的 live capability surface。

## 控制流分步讲解

把扩展层压成一条统一主链，可以这样理解：

1. 配置层先发现 MCP servers、plugins、skills 的来源。
2. MCP 连接层把外部 server 归一化成 tools / commands / resources。
3. plugin loader 把插件归一化成 `LoadedPlugin`，再拆出 commands、hooks、agents、MCP servers。
4. skills loader 把多来源 skill 统一成 `Command`。
5. `commands.ts` 与 `tools.ts` 把这些能力合流进统一宿主。
6. 最终模型只看到统一后的 command/tool/resource 表面，而不需要知道底层来源。

## Plugins：扩展本地产品表面

plugin 的角色和 MCP 不同。

MCP 更像“接入外部 server”。
plugin 更像“向本地产品注入新模块”。

一个 plugin 可以带来：

- commands
- skills
- hooks
- agents
- MCP servers
- LSP servers
- output styles
- 受限 settings

这说明 plugin 不是单一能力包，而是“局部产品扩展单元”。

## `pluginLoader.ts` 的关键设计

`src/utils/plugins/pluginLoader.ts` 的设计非常值得注意。

它明确区分了三层：

1. intent
2. materialization
3. activation

### intent

用户或配置表达“想启用什么插件”。

### materialization

插件是否已经在本地安装、缓存、可读取。

### activation

这些插件当前是否真的被装配进：

- command registry
- hook registry
- MCP config
- agent definitions

这三层拆开后，Claude Code 才能同时支持：

- cache-only startup
- 后台安装
- 显式 refresh
- resume 后恢复

## 为什么有 `loadAllPlugins()` 和 `loadAllPluginsCacheOnly()`

这是 plugin 层很有代表性的一个权衡。

### `loadAllPlugins()`

用于显式刷新路径，允许做更完整的加载工作。

### `loadAllPluginsCacheOnly()`

用于 startup 或不想阻塞交互的路径。

它只读本地缓存，不主动做网络安装。

这个分叉很重要，因为 Claude Code 不希望：

“为了决定 turn 1 能不能看到某个 plugin command，把整个启动过程卡在网络安装上”

所以 plugin 系统从设计上就支持：

- 快速启动
- 后续再做一致性修复

## Skills：为什么最终被做成 `Command`

skills 在 Claude Code 里最有意思的一点是：

它不是单独一套完全不同的对象模型，而是最终落成 `Command`。

来源可以很多：

- filesystem skills
- bundled skills
- plugin skills
- MCP skills
- 甚至 legacy commands

它们都会在 `src/commands.ts` 里汇总，再被 `getCommands()` 过滤。

这意味着 Claude Code 对 skills 的看法是：

skill 首先是“可被选择、可被解释、可被注入对话”的 command；
然后才是在某些场景下可由 `SkillTool` 调用的能力。

## `SkillTool` 的位置

`SkillTool` 非常关键，因为它连接了两种世界：

- command/skill 注册世界
- model tool-calling 世界

它会把可运行 skill 暴露给模型，并在需要时：

- 内联 skill 内容
- 或 fork 到 subagent

这就是为什么 skills 虽然在注册层长得像 command，但在执行层仍然能像 tool 一样被模型调用。

## skills 的来源与信任边界

`src/skills/loadSkillsDir.ts` 展示了 Claude Code 对 skill 来源的细粒度区分：

- `skills`
- `plugin`
- `managed`
- `bundled`
- `mcp`
- `commands_DEPRECATED`

这种来源标记不是装饰信息，而是安全与行为差异的基础。

一个很好的例子是：

对 `loadedFrom === 'mcp'` 的 skill，系统会更谨慎地对待内联 shell 等能力。

这说明 Claude Code 对扩展能力的总体态度是：

来源不同，信任边界也不同。

## 最终汇流：commands、tools、resources 进入统一宿主

从系统整体看，三条扩展面最后会分别汇入：

### commands 面

- built-in commands
- plugin commands
- filesystem skills
- bundled skills
- MCP prompts/commands

都被整合成 `Command`

### tools 面

- built-in tools
- MCP tools

都被整合成统一工具池

### resources 面

- MCP resources

通过通用 resource tools 暴露给模型或宿主

因此 Claude Code 的扩展设计并不是“三套平行系统”，而是：

“多来源能力进入统一抽象，再进入统一执行面”

## 关键设计权衡

### 1. provenance 比简洁更重要

这套系统大量给对象打来源标签，会让类型和流程都更重。

但收益是：

- policy 可控
- dedup 可控
- 安全边界可控
- debug 时更容易追溯

### 2. plugin 和 MCP 故意分层

plugin 偏本地产品扩展。
MCP 偏外部 live capability 接入。

两者虽然都能带来工具面扩展，但治理方式不同。

### 3. skills 选择复用 command 体系

这样做避免再维护一套完全独立的技能注册机制。

代价是需要在 `Command` 语义和 skill 语义之间做桥接。

### 4. 启动时倾向 cache-only，显式刷新时才求最新

这是交互式产品很实用的工程取舍。

## 易错点与误解

### 误解 1：MCP 只是“更多工具”

不对。MCP 还会带来 commands/prompts/resources，而且这些对象都进入统一 runtime。

### 误解 2：plugin 只是 marketplace 扩展

也不对。plugin 是本地产品表面的组合式扩展单元。

### 误解 3：skill 就是一段 prompt 文本

不准确。skill 先被组织成 command，再通过 `SkillTool` 接到模型执行链。

### 误解 4：扩展层没有强治理

不对。来源标签、dedup、policy、cache 分层都说明 Claude Code 对扩展治理非常重。

## 快照缺口说明

本篇有一个需要明确记下的缺口：

- `src/services/mcp/client.ts` 中可见对 `src/skills/mcpSkills.ts` 的动态引用，但当前快照中未找到该文件。因此可以确认 MCP skills 的接线存在，但不能完整确认其实现细节。

## 继续阅读建议

最后一篇看 [06-end-to-end-ai-sequences.md](./06-end-to-end-ai-sequences.md)。那篇不会再按模块拆，而是把整套系统压成 4 条完整时序，让你把前面五篇的内容在真正执行链上串起来。
