# 第 9 篇：插件与技能系统

## 1. 概述

Claude Code 的可扩展性建立在两套互补的机制之上：**插件系统 (Plugins)** 和 **技能系统 (Skills)**。插件是外部可安装的扩展包，能提供斜杠命令、hooks、MCP 服务器等多种组件；技能则是轻量化的"能力单元"，本质上是一段 Markdown prompt，让模型在对话中获得特定领域的专业知识。

两者最终都统一为 `Command` 类型，通过 `SkillTool` 暴露给模型调用——这是理解整套架构的关键。

**核心源码入口**：

| 目录/文件 | 职责 |
|---|---|
| `src/plugins/builtinPlugins.ts` | Built-in 插件注册表 |
| `src/plugins/bundled/` | Built-in 插件初始化 |
| `src/utils/plugins/pluginLoader.ts` | 外部插件发现与加载 |
| `src/skills/bundledSkills.ts` | Bundled 技能注册与文件提取 |
| `src/skills/loadSkillsDir.ts` | 磁盘技能加载（`~/.claude/skills/`） |
| `src/commands.ts` | 命令聚合与分发 |
| `src/tools/SkillTool/` | 模型侧技能调用工具 |

---

## 2. 双层插件模型：Built-in vs External

Claude Code 将插件分为两个层次：

### 2.1 Built-in Plugins（内置插件）

内置插件编译进 CLI 二进制文件，用户可通过 `/plugin` UI 开启或关闭。其 ID 格式为 `{name}@builtin`。

```typescript
// src/plugins/builtinPlugins.ts
const BUILTIN_PLUGINS: Map<string, BuiltinPluginDefinition> = new Map()

// 注册入口，在启动时由 initBuiltinPlugins() 调用
export function registerBuiltinPlugin(
  definition: BuiltinPluginDefinition,
): void {
  BUILTIN_PLUGINS.set(definition.name, definition)
}
```

`BuiltinPluginDefinition` 是一个全能容器，一个插件可同时提供 skills、hooks 和 MCP servers：

```typescript
// src/types/plugin.ts
export type BuiltinPluginDefinition = {
  name: string
  description: string
  version?: string
  skills?: BundledSkillDefinition[]    // 技能列表
  hooks?: HooksSettings                // Hook 配置
  mcpServers?: Record<string, McpServerConfig>  // MCP 服务器
  isAvailable?: () => boolean          // 运行时可用性检查
  defaultEnabled?: boolean             // 默认启用状态
}
```

启用状态的决策链：**用户偏好 > 插件默认值 > true**。

### 2.2 External Plugins（外部插件）

外部插件通过 Marketplace 安装，存储在 `~/.claude/plugins/cache/{marketplace}/{plugin}/{version}/` 下。它们拥有标准的目录结构：

```
my-plugin/
├── plugin.json          # 元数据清单
├── commands/            # 斜杠命令（Markdown）
├── skills/              # 技能文件
├── agents/              # Agent 定义
└── hooks/               # Hook 配置
    └── hooks.json
```

外部插件的加载由 `src/utils/plugins/pluginLoader.ts` 负责，支持 Git 仓库、NPM 包和 ZIP 缓存三种来源。

---

## 3. 插件加载流程

整个加载流程可以拆为四个阶段：

```
注册 → 技能提取 → Hook 注册 → MCP 连接
```

### 阶段一：注册

启动时，`initBundledSkills()` 和 `initBuiltinPlugins()` 分别注册编译期内置的技能和插件：

```typescript
// src/skills/bundled/index.ts — 注册所有 bundled skills
export function initBundledSkills(): void {
  registerUpdateConfigSkill()
  registerKeybindingsSkill()
  registerVerifySkill()
  registerSimplifySkill()
  // ... 十余个内置技能
}
```

外部插件则由 `pluginLoader.ts` 在启动时扫描 `~/.claude/plugins/` 目录，读取 `plugin.json` 清单，验证后加入 `LoadedPlugin` 列表。

### 阶段二：技能提取

每个插件的 `skills/` 和 `commands/` 子目录被扫描，Markdown 文件被解析为 `Command` 对象。`loadPluginCommands.ts` 中的 `walkPluginMarkdown()` 遍历插件目录，`parseFrontmatter()` 提取 YAML 头部的元数据（description、whenToUse、allowedTools 等）。

### 阶段三：Hook 注册

`loadPluginHooks.ts` 将插件的 hooks 配置转化为 `PluginHookMatcher[]`，注册到全局 hook 系统。支持的 Hook 事件非常丰富：

```typescript
// src/utils/plugins/loadPluginHooks.ts — 支持的 Hook 事件类型
const pluginMatchers: Record<HookEvent, PluginHookMatcher[]> = {
  PreToolUse: [],
  PostToolUse: [],
  Notification: [],
  SessionStart: [],
  SessionEnd: [],
  Stop: [],
  SubagentStart: [],
  FileChanged: [],
  // ... 共 20+ 种事件
}
```

### 阶段四：MCP 连接

`mcpPluginIntegration.ts` 处理插件声明的 MCP 服务器。它支持标准的 `mcp.json` 配置和 `.mcpb` 打包格式（DXT manifest），后者需要下载、解压并进行用户配置后才能连接。

---

## 4. 插件作用域：managed > user > project > local

技能文件可以存放在四个层级的目录中，优先级从高到低：

| 作用域 | 路径 | 说明 |
|---|---|---|
| `policySettings` (managed) | `{managed}/.claude/skills/` | 企业管理员统一下发 |
| `userSettings` | `~/.claude/skills/` | 用户全局自定义 |
| `projectSettings` | `.claude/skills/` | 项目级别共享 |
| `localSettings` | `.claude/skills/`（gitignored） | 本地开发者私有 |

```typescript
// src/skills/loadSkillsDir.ts — 根据 source 返回技能目录路径
export function getSkillsPath(
  source: SettingSource | 'plugin',
  dir: 'skills' | 'commands',
): string {
  switch (source) {
    case 'policySettings':
      return join(getManagedFilePath(), '.claude', dir)
    case 'userSettings':
      return join(getClaudeConfigHomeDir(), dir)
    case 'projectSettings':
      return `.claude/${dir}`
    // ...
  }
}
```

加载时，`getSkillDirCommands()` 并行扫描所有层级，用 `realpath` 解析符号链接来去重（避免同一文件通过不同路径被加载两次）。低优先级的同名技能会被高优先级覆盖。

---

## 5. Bundled Skills 注册表

Bundled skills 是编译进二进制的"官方"技能，注册中心位于 `src/skills/bundledSkills.ts`。

### BundledSkillDefinition 结构

```typescript
// src/skills/bundledSkills.ts
export type BundledSkillDefinition = {
  name: string
  description: string
  aliases?: string[]
  whenToUse?: string           // 模型判断何时调用的提示
  argumentHint?: string        // 参数提示
  allowedTools?: string[]      // 该技能可以使用的工具白名单
  model?: string               // 模型覆盖
  disableModelInvocation?: boolean  // 禁止模型主动调用
  userInvocable?: boolean      // 用户是否可以通过 /name 调用
  hooks?: HooksSettings        // 技能自带的 hooks
  context?: 'inline' | 'fork'  // 执行模式
  agent?: string               // fork 模式下的 Agent 类型
  files?: Record<string, string>  // 附带的参考文件（懒提取到磁盘）
  getPromptForCommand: (       // 核心：生成 prompt 的函数
    args: string,
    context: ToolUseContext,
  ) => Promise<ContentBlockParam[]>
}
```

一个典型的 bundled skill 示例——`simplify`：

```typescript
// src/skills/bundled/simplify.ts
export function registerSimplifySkill(): void {
  registerBundledSkill({
    name: 'simplify',
    description: 'Review changed code for reuse, quality, and efficiency...',
    userInvocable: true,
    async getPromptForCommand(args) {
      let prompt = SIMPLIFY_PROMPT  // 详细的多阶段代码审查指令
      if (args) {
        prompt += `\n\n## Additional Focus\n\n${args}`
      }
      return [{ type: 'text', text: prompt }]
    },
  })
}
```

注册后，`registerBundledSkill()` 将 definition 转化为 `Command` 对象（`source: 'bundled'`, `loadedFrom: 'bundled'`），存入内部数组。

---

## 6. 技能懒提取与安全写入

部分 bundled skill 携带参考文件（通过 `files` 字段声明）。这些文件不会在启动时写入磁盘，而是在首次调用该技能时**懒提取**：

```typescript
// src/skills/bundledSkills.ts — 懒提取机制
if (files && Object.keys(files).length > 0) {
  skillRoot = getBundledSkillExtractDir(definition.name)
  // 闭包中缓存 Promise，保证并发调用只写一次
  let extractionPromise: Promise<string | null> | undefined
  const inner = definition.getPromptForCommand
  getPromptForCommand = async (args, ctx) => {
    extractionPromise ??= extractBundledSkillFiles(definition.name, files)
    const extractedDir = await extractionPromise
    const blocks = await inner(args, ctx)
    if (extractedDir === null) return blocks
    return prependBaseDir(blocks, extractedDir)  // 在 prompt 前插入基目录路径
  }
}
```

写入过程有严格的安全防护：

1. **Per-process nonce 目录**：提取目录包含进程级随机数，防止符号链接攻击
2. **O_NOFOLLOW | O_EXCL**：不跟踪符号链接，文件已存在则不覆盖
3. **0o700/0o600 权限**：目录和文件仅对 owner 可读写
4. **路径遍历检查**：`resolveSkillFilePath()` 拒绝包含 `..` 的路径

---

## 7. 斜杠命令系统

### 命令规模

`src/commands.ts` 汇聚了所有命令来源，通过 `getCommands()` 返回完整列表。命令数量在 100+ 级别，由以下来源组成：

- **内置命令 (COMMANDS)**：`/help`、`/clear`、`/compact`、`/config` 等 60+ 个硬编码命令
- **Bundled skills**：`/simplify`、`/verify`、`/update-config` 等
- **Built-in plugin skills**：来自启用的内置插件
- **Skill directory commands**：来自 `~/.claude/skills/` 等目录
- **Plugin commands/skills**：来自已安装的外部插件
- **MCP skills**：来自 MCP 服务器暴露的 prompts
- **Dynamic skills**：运行时通过文件操作发现的技能

### Command 类型

所有命令统一为一个判别联合类型：

```typescript
// src/types/command.ts
export type Command = CommandBase &
  (PromptCommand | LocalCommand | LocalJSXCommand)
```

三种子类型对应不同的执行方式：

| 类型 | 执行方式 | 典型场景 |
|---|---|---|
| `prompt` | 展开为 prompt 发送给模型 | 技能、插件命令 |
| `local` | 直接执行 JS 逻辑，返回文本 | `/compact`、`/cost` |
| `local-jsx` | 渲染 Ink (React) UI | `/config`、`/mcp` |

### 命令聚合与分发

`loadAllCommands()` 并行加载所有来源，按优先级合并：

```typescript
// src/commands.ts — 命令加载顺序（前面的优先）
return [
  ...bundledSkills,         // 编译期内置技能
  ...builtinPluginSkills,   // 内置插件的技能
  ...skillDirCommands,      // 磁盘技能目录
  ...workflowCommands,      // Workflow 脚本
  ...pluginCommands,        // 外部插件命令
  ...pluginSkills,          // 外部插件技能
  ...COMMANDS(),            // 硬编码内置命令
]
```

用户输入 `/foo` 时，`findCommand()` 按 name 和 aliases 查找匹配。返回前还会经过两层过滤：

1. `meetsAvailabilityRequirement()`：基于认证状态过滤（claude-ai / console）
2. `isCommandEnabled()`：基于 feature flag 和运行时条件

---

## 8. SkillTool：模型如何调用技能

`SkillTool` 是暴露给 Claude 模型的工具，让模型能够在对话中主动调用技能。

### 输入 Schema

```typescript
// src/tools/SkillTool/SkillTool.ts
z.object({
  skill: z.string().describe('The skill name. E.g., "commit", "review-pr"'),
  args: z.string().optional().describe('Optional arguments for the skill'),
})
```

### 技能发现

模型通过 system-reminder 消息获取可用技能列表。`prompt.ts` 中的 `formatCommandsWithinBudget()` 将技能列表压缩到上下文窗口的 1% 以内（约 8000 字符），bundled skills 的描述永远不会被截断，其他技能按需缩短：

```typescript
// src/tools/SkillTool/prompt.ts
export const SKILL_BUDGET_CONTEXT_PERCENT = 0.01  // 上下文的 1%
export const MAX_LISTING_DESC_CHARS = 250          // 单条描述上限
```

### 执行路径

调用一个技能时经过三步验证：

1. **validateInput**：检查技能是否存在、是否为 prompt 类型、是否允许模型调用
2. **checkPermissions**：检查权限规则（deny/allow rules）
3. **call**：执行技能

执行时根据 `context` 字段分为两种模式：

- **inline**（默认）：技能的 prompt 展开到当前对话上下文中，模型直接看到并执行
- **fork**：技能在一个独立的 sub-agent 中运行，有独立的 token 预算和工具集

```typescript
// fork 模式的核心：启动子 Agent 运行技能
for await (const message of runAgent({
  agentDefinition,
  promptMessages,
  toolUseContext: { ...context, getAppState: modifiedGetAppState },
  canUseTool,
  isAsync: false,
  querySource: 'agent:custom',
  model: command.model as ModelAlias | undefined,
  availableTools: context.options.tools,
  override: { agentId },
})) {
  agentMessages.push(message)
  // 向父对话报告进度
}
```

### 过滤逻辑

并非所有 `Command` 都会出现在 SkillTool 列表中。`getSkillToolCommands()` 过滤规则：

```typescript
// src/commands.ts — SkillTool 的命令过滤
cmd.type === 'prompt' &&              // 必须是 prompt 类型
!cmd.disableModelInvocation &&        // 未禁止模型调用
cmd.source !== 'builtin' &&           // 排除 /help 等内置命令
(cmd.loadedFrom === 'bundled' ||      // bundled skills 总是包含
 cmd.loadedFrom === 'skills' ||       // 磁盘技能总是包含
 cmd.hasUserSpecifiedDescription ||   // 有明确描述的命令
 cmd.whenToUse)                       // 有使用场景说明的命令
```

---

## 9. 设计模式总结

### 9.1 统一抽象：一切皆 Command

无论来源如何——编译期 bundled、磁盘 Markdown、外部插件、MCP 服务器——所有可执行单元最终都归约为 `Command` 类型。这使得命令查找、权限检查、模型调用等逻辑只需编写一次。

### 9.2 注册表模式 (Registry Pattern)

Bundled skills 和 built-in plugins 都采用模块级注册表（`Map` / 数组），配合 `register*()` 函数在启动时填充。这比 decorator 或配置文件更显式、更易调试。

### 9.3 懒加载与按需提取

- 命令列表通过 `memoize` 缓存，只在首次 `getCommands(cwd)` 时触发磁盘 I/O
- Bundled skill 的参考文件在首次调用时才写入磁盘
- 重量级命令（如 `/insights`，113KB）通过 lazy shim 延迟 `import()`

### 9.4 多层安全屏障

- **作用域隔离**：managed 策略能覆盖用户和项目级配置
- **权限检查**：SkillTool 的 `checkPermissions()` 支持 deny/allow 规则
- **文件写入安全**：O_NOFOLLOW、O_EXCL、nonce 目录、路径遍历检查
- **策略管控**：`isRestrictedToPluginOnly()` 可将用户限制为只能使用指定插件

### 9.5 依赖解环 (mcpSkillBuilders)

MCP 技能发现需要调用 `loadSkillsDir.ts` 中的函数，但直接 import 会形成循环依赖。解决方案是 `mcpSkillBuilders.ts` 作为无依赖的中间层，提供 write-once 注册表：

```typescript
// src/skills/mcpSkillBuilders.ts — 打破循环依赖的桥接模块
let builders: MCPSkillBuilders | null = null

export function registerMCPSkillBuilders(b: MCPSkillBuilders): void {
  builders = b  // loadSkillsDir.ts 在模块初始化时注册
}

export function getMCPSkillBuilders(): MCPSkillBuilders {
  if (!builders) throw new Error('MCP skill builders not registered')
  return builders  // mcpSkills.ts 在需要时获取
}
```

### 9.6 预算感知的提示压缩

技能列表可能很长，但首轮对话的上下文宝贵。`formatCommandsWithinBudget()` 实现了智能压缩：先尝试完整描述，超预算则截断非 bundled 技能的描述，极端情况下退化为仅显示技能名称——bundled skills 的描述始终完整保留。
