# 第 5 篇：权限模型与安全机制

> Claude Code 源码深度教学系列 — 核心重点篇

---

## 1. 概述：为什么需要如此复杂的权限系统

Claude Code 是一个直接在用户机器上执行代码的 AI 工具。它可以运行 Shell 命令、编辑文件、发起网络请求 —— 这些操作如果不加控制，可能造成不可逆的损害：删除关键文件、泄露敏感数据、执行恶意代码。

与传统的基于角色的访问控制不同，Claude Code 面临的威胁模型非常独特：

1. **模型可能被 prompt injection 操纵**：恶意仓库中的 README 或注释可能诱导模型执行危险操作
2. **命令的语义是动态的**：`rm -rf /` 显然危险，但 `python3 script.py` 是否安全取决于脚本内容
3. **用户信任是分层的**：对 `git status` 的信任远高于 `curl | bash`
4. **操作上下文至关重要**：在项目目录内编辑文件通常安全，编辑 `~/.bashrc` 则需要格外小心

为此，Claude Code 构建了一套**多层纵深防御**（defense in depth）的权限系统：

```
用户请求 → Hook 预检 → 规则匹配 → 工具自检 → 模式判断 → 分类器评估 → 交互确认
```

每一层都可以独立做出 allow/deny/ask 决策，任一层的 deny 都不可被后续层覆盖。这种设计确保即使某一层被绕过，其他层仍能提供保护。

核心源码位于以下目录：

| 目录/文件 | 职责 |
|---|---|
| `src/utils/permissions/permissions.ts` | 权限决策主流水线 |
| `src/utils/permissions/PermissionMode.ts` | 权限模式定义 |
| `src/utils/permissions/PermissionRule.ts` | 规则类型定义 |
| `src/utils/permissions/shellRuleMatching.ts` | Shell 命令规则匹配 |
| `src/utils/permissions/yoloClassifier.ts` | Auto Mode 分类器 |
| `src/utils/permissions/denialTracking.ts` | 拒绝追踪机制 |
| `src/tools/BashTool/bashPermissions.ts` | Bash 工具权限逻辑 |
| `src/tools/BashTool/bashSecurity.ts` | Bash 安全检查 |
| `src/utils/sandbox/sandbox-adapter.ts` | 沙箱适配层 |
| `src/services/tools/toolHooks.ts` | 工具 Hook 执行 |

---

## 2. ToolPermissionContext 结构详解

`ToolPermissionContext` 是权限系统的核心数据结构，承载了当前会话中所有的权限状态。它定义在 `src/Tool.ts` 中：

```typescript
// src/Tool.ts
export type ToolPermissionContext = DeepImmutable<{
  // 当前权限模式
  mode: PermissionMode
  // 额外允许的工作目录（通过 --add-dir 等方式添加）
  additionalWorkingDirectories: Map<string, AdditionalWorkingDirectory>
  // 三类规则，按来源分层存储
  alwaysAllowRules: ToolPermissionRulesBySource
  alwaysDenyRules: ToolPermissionRulesBySource
  alwaysAskRules: ToolPermissionRulesBySource
  // bypassPermissions 模式是否可用
  isBypassPermissionsModeAvailable: boolean
  // auto 模式是否可用
  isAutoModeAvailable?: boolean
  // 被剥离的危险规则（进入 auto 模式时移除的过于宽泛的规则）
  strippedDangerousRules?: ToolPermissionRulesBySource
  // 当 true 时，权限提示会被自动拒绝（后台代理场景）
  shouldAvoidPermissionPrompts?: boolean
  // 当 true 时，在显示权限对话框前等待自动化检查（分类器、hooks）
  awaitAutomatedChecksBeforeDialog?: boolean
  // 模型发起 plan 模式前的原始模式，用于退出时恢复
  prePlanMode?: PermissionMode
}>
```

注意 `DeepImmutable` 包装 —— 这是一个类型级别的不可变约束，确保权限上下文不会被意外修改。所有状态变更必须通过 `applyPermissionUpdate` 生成新对象。

### 2.1 五种权限模式 (PermissionMode)

权限模式定义在 `src/types/permissions.ts` 中：

```typescript
// src/types/permissions.ts
export const EXTERNAL_PERMISSION_MODES = [
  'acceptEdits',
  'bypassPermissions',
  'default',
  'dontAsk',
  'plan',
] as const

// 内部模式在外部模式基础上增加 'auto' 和 'bubble'
export type InternalPermissionMode = ExternalPermissionMode | 'auto' | 'bubble'
export type PermissionMode = InternalPermissionMode
```

各模式的语义如下：

#### default 模式
标准交互模式。Claude 执行任何有副作用的操作都需要用户确认。读取文件、搜索等只读操作自动通过，但写入文件、执行命令等需要用户在终端中批准。这是最安全的模式。

#### plan 模式
规划模式。Claude 只能读取和分析代码，不能执行任何写操作。当用户希望先看到完整方案再执行时使用。模型可以主动进入 plan 模式（通过 EnterPlanModeTool），退出时恢复之前的模式（`prePlanMode` 字段的用途）。

#### acceptEdits 模式
自动接受文件编辑。在工作目录内的文件编辑不需要确认，但 Shell 命令仍需要审批。这是一种折中 —— 文件编辑有 git 保护（可以 revert），但命令执行不可逆。

#### bypassPermissions 模式
跳过所有权限检查。**但仍受以下约束**：
- 工具级 deny 规则（步骤 1a）
- 工具级 ask 规则（步骤 1b）
- 内容级 ask 规则（步骤 1f，如 `Bash(npm publish:*)`）
- 安全检查（步骤 1g，如 `.git/`、`.claude/` 等敏感路径）
- `requiresUserInteraction` 的工具（如 AskUserQuestion）

这意味着即使在 bypass 模式下，deny 规则和安全检查仍然生效，提供了底线保护。

#### dontAsk 模式
不询问模式。所有本来需要 ask 用户的操作会被自动拒绝（deny）。适用于 CI/CD 等非交互环境，确保不会因等待用户输入而挂起。

#### auto 模式（内部模式，需 TRANSCRIPT_CLASSIFIER feature flag）
AI 分类器自动决策模式。不提示用户，而是使用一个独立的 AI 分类器来判断操作是否安全。这是最高级的自动化模式，在后续章节详细展开。

### 2.2 规则三元组：allow / deny / ask

每种规则都按来源（source）分层存储在 `ToolPermissionRulesBySource` 中：

```typescript
// 规则按来源分层
type ToolPermissionRulesBySource = {
  [source in PermissionRuleSource]?: string[]
}
```

三类规则的语义：

- **alwaysAllowRules**：匹配时自动允许，跳过用户确认
- **alwaysDenyRules**：匹配时直接拒绝，不可覆盖
- **alwaysAskRules**：匹配时强制弹出确认对话框，即使在 bypass 模式下

优先级顺序：**deny > ask > allow > 默认行为**。这是一个关键设计原则 —— deny 永远优先，确保安全底线不被突破。

### 2.3 SettingSource 分层

规则来源决定了规则的优先级和可编辑性：

```typescript
// src/utils/settings/constants.ts
export const SETTING_SOURCES = [
  'userSettings',     // ~/.claude/settings.json — 全局用户设置
  'projectSettings',  // .claude/settings.json — 项目级共享设置
  'localSettings',    // .claude/settings.local.json — 本地设置（gitignored）
  'flagSettings',     // --settings CLI 参数指定的设置文件
  'policySettings',   // 管理员托管策略（managed-settings.json 或远程 API）
] as const
```

除此之外，权限规则还有两个额外来源：
- **cliArg**：通过 `--allowedTools` / `--disallowedTools` 命令行参数传入
- **session**：会话内临时规则（用户在权限对话框中选择 "Always allow" 时产生）

加载规则时，系统会遍历所有来源，将它们合并到 `ToolPermissionContext` 中：

```typescript
// src/utils/permissions/permissions.ts
export function getAllowRules(
  context: ToolPermissionContext,
): PermissionRule[] {
  // 遍历所有来源，将字符串规则解析为结构化的 PermissionRule
  return PERMISSION_RULE_SOURCES.flatMap(source =>
    (context.alwaysAllowRules[source] || []).map(ruleString => ({
      source,
      ruleBehavior: 'allow',
      ruleValue: permissionRuleValueFromString(ruleString),
    })),
  )
}
```

**托管策略优先级**：当 `policySettings` 中设置了 `allowManagedPermissionRulesOnly: true` 时，只有来自 policySettings 的规则会被尊重，其他来源的规则全部被清空。这是企业管理场景下的强制策略。

---

## 3. 权限决策完整流水线

权限决策的入口是 `hasPermissionsToUseTool` 函数，内部委托给 `hasPermissionsToUseToolInner`。整个流水线分为多个步骤，每一步都可以终止流程并返回最终决策。

### 整体调用流程

```
hasPermissionsToUseTool(tool, input, context)
  │
  ├─► hasPermissionsToUseToolInner(tool, input, context)
  │     │
  │     ├─ Step 1a: 检查工具级 deny 规则
  │     ├─ Step 1b: 检查工具级 ask 规则
  │     ├─ Step 1c: 调用 tool.checkPermissions()
  │     ├─ Step 1d: 工具实现返回 deny
  │     ├─ Step 1e: 工具需要用户交互
  │     ├─ Step 1f: 内容级 ask 规则
  │     ├─ Step 1g: 安全检查（bypass-immune）
  │     ├─ Step 2a: 模式检查（bypass 模式跳过）
  │     ├─ Step 2b: 工具级 allow 规则
  │     └─ Step 3:  passthrough → ask 转换
  │
  ├─► 后处理：denial tracking 更新
  ├─► dontAsk 模式：ask → deny 转换
  ├─► auto 模式：AI 分类器评估
  └─► 无头代理：自动 deny + hook 机会
```

### Step 1a: 工具级 deny 规则检查

这是权限检查的第一道防线 —— 直接检查整个工具是否被禁止：

```typescript
// src/utils/permissions/permissions.ts — hasPermissionsToUseToolInner()
// 1. Check if the tool is denied
// 1a. Entire tool is denied
const denyRule = getDenyRuleForTool(appState.toolPermissionContext, tool)
if (denyRule) {
  return {
    behavior: 'deny',
    decisionReason: {
      type: 'rule',
      rule: denyRule,  // 记录是哪条规则触发了拒绝
    },
    message: `Permission to use ${tool.name} has been denied.`,
  }
}
```

`getDenyRuleForTool` 的匹配逻辑支持精确匹配和 MCP 服务器级匹配：

```typescript
// src/utils/permissions/permissions.ts
function toolMatchesRule(
  tool: Pick<Tool, 'name' | 'mcpInfo'>,
  rule: PermissionRule,
): boolean {
  // 规则不能有 ruleContent —— 这是工具级匹配，不是内容级
  if (rule.ruleValue.ruleContent !== undefined) {
    return false
  }

  const nameForRuleMatch = getToolNameForPermissionCheck(tool)

  // 直接工具名匹配：规则 "Bash" 匹配工具 "Bash"
  if (rule.ruleValue.toolName === nameForRuleMatch) {
    return true
  }

  // MCP 服务器级匹配：规则 "mcp__server1" 匹配 "mcp__server1__tool1"
  const ruleInfo = mcpInfoFromString(rule.ruleValue.toolName)
  const toolInfo = mcpInfoFromString(nameForRuleMatch)

  return (
    ruleInfo !== null &&
    toolInfo !== null &&
    (ruleInfo.toolName === undefined || ruleInfo.toolName === '*') &&
    ruleInfo.serverName === toolInfo.serverName
  )
}
```

### Step 1b: 工具级 ask 规则检查

如果工具不在 deny 列表中，接下来检查是否需要强制询问：

```typescript
// 1b. Check if the entire tool should always ask for permission
const askRule = getAskRuleForTool(appState.toolPermissionContext, tool)
if (askRule) {
  // 特殊情况：如果沙箱启用且配置了 autoAllowBashIfSandboxed，
  // 则沙箱内的 Bash 命令可以跳过 ask 规则
  const canSandboxAutoAllow =
    tool.name === BASH_TOOL_NAME &&
    SandboxManager.isSandboxingEnabled() &&
    SandboxManager.isAutoAllowBashIfSandboxedEnabled() &&
    shouldUseSandbox(input)

  if (!canSandboxAutoAllow) {
    return {
      behavior: 'ask',
      decisionReason: { type: 'rule', rule: askRule },
      message: createPermissionRequestMessage(tool.name),
    }
  }
  // 沙箱可以自动允许 → 继续到 tool.checkPermissions 处理命令级规则
}
```

这里有一个重要的沙箱优化：当沙箱开启并配置了 `autoAllowBashIfSandboxed` 时，即使有工具级 ask 规则，沙箱内的命令也可以自动通过。这是因为沙箱本身提供了 OS 级别的安全隔离。

### Step 1c: 工具特定权限检查 — tool.checkPermissions()

每个工具可以实现自己的 `checkPermissions` 方法来做细粒度的权限控制。这是最复杂的步骤，因为不同工具有不同的安全关注点。

```typescript
// 1c. Ask the tool implementation for a permission result
let toolPermissionResult: PermissionResult = {
  behavior: 'passthrough',  // 默认值：让后续步骤决定
  message: createPermissionRequestMessage(tool.name),
}
try {
  const parsedInput = tool.inputSchema.parse(input)
  toolPermissionResult = await tool.checkPermissions(parsedInput, context)
} catch (e) {
  if (e instanceof AbortError || e instanceof APIUserAbortError) {
    throw e  // 中止错误直接传播
  }
  logError(e)  // 其他错误记录但不阻塞
}
```

对于 **BashTool**，`checkPermissions` 会：
1. 解析命令为子命令列表（处理 `&&`、`||`、`;`、管道等）
2. 对每个子命令检查 allow/deny/ask 规则
3. 运行安全模式检测（命令替换、重定向等危险模式）
4. 生成建议的权限更新（如 "Always allow `git commit:*`"）

对于 **FileEditTool**，`checkPermissions` 会：
1. 检查目标路径是否在允许的工作目录内
2. 检查路径是否匹配 allow/deny 规则
3. 检查敏感路径保护（`.git/`、`.bashrc` 等）
4. 在 `acceptEdits` 模式下，工作目录内的编辑自动允许

### Step 1d-1g: 工具返回结果处理

```typescript
// 1d. 工具实现直接 deny → 立即返回
if (toolPermissionResult?.behavior === 'deny') {
  return toolPermissionResult
}

// 1e. 工具需要用户交互（如 AskUserQuestion）→ 即使 bypass 模式也必须 ask
if (
  tool.requiresUserInteraction?.() &&
  toolPermissionResult?.behavior === 'ask'
) {
  return toolPermissionResult
}

// 1f. 内容级 ask 规则（如 Bash(npm publish:*)）→ bypass-immune
// 用户明确配置的 ask 规则必须被尊重
if (
  toolPermissionResult?.behavior === 'ask' &&
  toolPermissionResult.decisionReason?.type === 'rule' &&
  toolPermissionResult.decisionReason.rule.ruleBehavior === 'ask'
) {
  return toolPermissionResult
}

// 1g. 安全检查不可绕过（sensitive paths: .git/, .claude/, .vscode/, shell configs）
// 即使在 bypassPermissions 模式下也必须提示
if (
  toolPermissionResult?.behavior === 'ask' &&
  toolPermissionResult.decisionReason?.type === 'safetyCheck'
) {
  return toolPermissionResult
}
```

步骤 1f 和 1g 的关键意义在于：它们定义了**即使在最高权限模式下也不可绕过的安全边界**。

### Step 2a: 模式检查 — bypassPermissions

通过了步骤 1 的所有检查后，才进入模式判断：

```typescript
// 2a. Check if mode allows the tool to run
appState = context.getAppState()  // 重新获取最新状态

const shouldBypassPermissions =
  appState.toolPermissionContext.mode === 'bypassPermissions' ||
  // plan 模式 + 原始模式是 bypass → 仍然允许
  (appState.toolPermissionContext.mode === 'plan' &&
    appState.toolPermissionContext.isBypassPermissionsModeAvailable)

if (shouldBypassPermissions) {
  return {
    behavior: 'allow',
    updatedInput: getUpdatedInputOrFallback(toolPermissionResult, input),
    decisionReason: { type: 'mode', mode: appState.toolPermissionContext.mode },
  }
}
```

### Step 2b: 工具级 allow 规则

如果不在 bypass 模式，检查是否有工具级 allow 规则：

```typescript
// 2b. Entire tool is allowed
const alwaysAllowedRule = toolAlwaysAllowedRule(
  appState.toolPermissionContext,
  tool,
)
if (alwaysAllowedRule) {
  return {
    behavior: 'allow',
    updatedInput: getUpdatedInputOrFallback(toolPermissionResult, input),
    decisionReason: { type: 'rule', rule: alwaysAllowedRule },
  }
}
```

### Step 3: passthrough 转换为 ask

如果到这一步还没有决策，将 `passthrough` 转换为 `ask`：

```typescript
// 3. Convert "passthrough" to "ask"
const result: PermissionDecision =
  toolPermissionResult.behavior === 'passthrough'
    ? {
        ...toolPermissionResult,
        behavior: 'ask' as const,
        message: createPermissionRequestMessage(
          tool.name,
          toolPermissionResult.decisionReason,
        ),
      }
    : toolPermissionResult

return result
```

### 后处理：Auto Mode / dontAsk / 无头代理

`hasPermissionsToUseTool` 在拿到 `hasPermissionsToUseToolInner` 的结果后，进行模式级别的后处理：

```typescript
// 后处理逻辑（在 hasPermissionsToUseTool 中）

// 允许的工具重置连续拒绝计数
if (result.behavior === 'allow') {
  // ... 更新 denial tracking
  return result
}

// dontAsk 模式：ask → deny
if (result.behavior === 'ask') {
  if (appState.toolPermissionContext.mode === 'dontAsk') {
    return {
      behavior: 'deny',
      decisionReason: { type: 'mode', mode: 'dontAsk' },
      message: DONT_ASK_REJECT_MESSAGE(tool.name),
    }
  }

  // auto 模式：调用 AI 分类器
  if (feature('TRANSCRIPT_CLASSIFIER') &&
      appState.toolPermissionContext.mode === 'auto') {
    // ... 分类器评估流程（详见第 5 节）
  }

  // 无头代理：给 hooks 一次机会，否则 auto-deny
  if (appState.toolPermissionContext.shouldAvoidPermissionPrompts) {
    const hookDecision = await runPermissionRequestHooksForHeadlessAgent(...)
    if (hookDecision) return hookDecision
    return {
      behavior: 'deny',
      message: AUTO_REJECT_MESSAGE(tool.name),
    }
  }
}
```

---

## 4. 规则匹配语法详解

权限规则的字符串格式为 `ToolName` 或 `ToolName(ruleContent)`。解析由 `permissionRuleValueFromString` 完成：

```typescript
// src/utils/permissions/permissionRuleParser.ts
export function permissionRuleValueFromString(
  ruleString: string,
): PermissionRuleValue {
  // 找到第一个未转义的 '('
  const openParenIndex = findFirstUnescapedChar(ruleString, '(')
  if (openParenIndex === -1) {
    // 没有括号 → 纯工具名规则
    return { toolName: normalizeLegacyToolName(ruleString) }
  }

  // 找到最后一个未转义的 ')'
  const closeParenIndex = findLastUnescapedChar(ruleString, ')')
  // ... 提取 toolName 和 ruleContent

  // 空内容或通配符 "Bash()" / "Bash(*)" → 等同于工具级规则
  if (rawContent === '' || rawContent === '*') {
    return { toolName: normalizeLegacyToolName(toolName) }
  }

  // 反转义内容中的括号
  const ruleContent = unescapeRuleContent(rawContent)
  return { toolName: normalizeLegacyToolName(toolName), ruleContent }
}
```

### 4.1 Shell 命令规则 — Bash(...)

Shell 命令规则是最复杂的，因为要匹配各种命令格式。规则解析在 `shellRuleMatching.ts` 中：

```typescript
// src/utils/permissions/shellRuleMatching.ts
export type ShellPermissionRule =
  | { type: 'exact'; command: string }     // 精确匹配
  | { type: 'prefix'; prefix: string }     // 前缀匹配（遗留语法）
  | { type: 'wildcard'; pattern: string }  // 通配符匹配
```

#### 精确匹配

```
Bash(npm install)
```

只匹配命令 `npm install`，不匹配 `npm install lodash`。

#### 前缀匹配（遗留 `:*` 语法）

```
Bash(git:*)
```

匹配所有以 `git` 开头的命令：`git status`、`git commit -m "fix"`、甚至单独的 `git`。

```typescript
// 前缀提取
export function permissionRuleExtractPrefix(
  permissionRule: string,
): string | null {
  const match = permissionRule.match(/^(.+):\*$/)
  return match?.[1] ?? null
}
```

#### 通配符匹配（新语法，使用 `*`）

```
Bash(git *)       — 等同于 git:*，但更直观
Bash(npm run *)   — 匹配 npm run build、npm run test 等
Bash(docker * -it *) — 匹配 docker run -it ubuntu 等
```

通配符匹配的关键实现：

```typescript
// src/utils/permissions/shellRuleMatching.ts
export function matchWildcardPattern(
  pattern: string,
  command: string,
  caseInsensitive = false,
): boolean {
  const trimmedPattern = pattern.trim()

  // 处理转义序列：\* → 字面星号，\\ → 字面反斜杠
  let processed = ''
  let i = 0
  while (i < trimmedPattern.length) {
    const char = trimmedPattern[i]
    if (char === '\\' && i + 1 < trimmedPattern.length) {
      const nextChar = trimmedPattern[i + 1]
      if (nextChar === '*') {
        processed += ESCAPED_STAR_PLACEHOLDER  // 保护字面星号
        i += 2
        continue
      }
      // ...
    }
    processed += char
    i++
  }

  // 将 * 转换为 .* 的正则表达式
  const escaped = processed.replace(/[.+?^${}()|[\]\\'"]/g, '\\$&')
  const withWildcards = escaped.replace(/\*/g, '.*')

  // 特殊处理：单通配符 "git *" 也匹配裸 "git"
  // 使尾部的 " .*" 变成可选的 "( .*)?"
  const unescapedStarCount = (processed.match(/\*/g) || []).length
  if (regexPattern.endsWith(' .*') && unescapedStarCount === 1) {
    regexPattern = regexPattern.slice(0, -3) + '( .*)?'
  }

  // dotAll 模式：. 匹配换行符，支持 heredoc 内容
  const flags = 's' + (caseInsensitive ? 'i' : '')
  const regex = new RegExp(`^${regexPattern}$`, flags)
  return regex.test(command)
}
```

注意 `git *` 的特殊处理：当模式以 ` *` 结尾且只有一个通配符时，会让尾部变为可选，使得 `git *` 既匹配 `git add` 也匹配裸 `git`。这和前缀语法 `git:*` 的行为一致。

### 4.2 文件路径规则 — Edit(...)、Read(...)

```
Edit(/src/**)       — 允许编辑 /src/ 下的所有文件（相对于设置文件目录）
Edit(//etc/config)  — 允许编辑绝对路径 /etc/config（// 前缀 = 文件系统根目录）
Read(~/.ssh/**)     — 允许读取 ~/.ssh/ 下的所有文件
```

路径规则使用 glob 语法，由工具的 `checkPermissions` 实现匹配。路径的解析有特殊的约定：

```typescript
// src/utils/sandbox/sandbox-adapter.ts
export function resolvePathPatternForSandbox(
  pattern: string,
  source: SettingSource,
): string {
  // // 前缀 → 绝对路径（"//.aws/**" → "/.aws/**"）
  if (pattern.startsWith('//')) {
    return pattern.slice(1)
  }

  // / 前缀 → 相对于设置文件目录
  if (pattern.startsWith('/') && !pattern.startsWith('//')) {
    const root = getSettingsRootPathForSource(source)
    return resolve(root, pattern.slice(1))
  }

  // 其他模式（~/path、./path）→ 直接传递
  return pattern
}
```

### 4.3 MCP 服务器级规则

```
mcp__server1            — 允许/拒绝/询问整个 MCP 服务器的所有工具
mcp__server1__tool1     — 只针对特定工具
mcp__server1__*         — 通配符匹配服务器下所有工具
```

匹配逻辑在 `toolMatchesRule` 中：

```typescript
// MCP 服务器级匹配
const ruleInfo = mcpInfoFromString(rule.ruleValue.toolName)
const toolInfo = mcpInfoFromString(nameForRuleMatch)

return (
  ruleInfo !== null &&
  toolInfo !== null &&
  // 规则没有指定具体工具名，或使用了通配符
  (ruleInfo.toolName === undefined || ruleInfo.toolName === '*') &&
  // 服务器名匹配
  ruleInfo.serverName === toolInfo.serverName
)
```

### 4.4 Agent 类型规则

```
Agent(Explore)    — 拒绝 Explore 类型的子代理
```

这是一种内容级规则，针对 AgentTool 的特定代理类型：

```typescript
// src/utils/permissions/permissions.ts
export function getDenyRuleForAgent(
  context: ToolPermissionContext,
  agentToolName: string,
  agentType: string,
): PermissionRule | null {
  return (
    getDenyRules(context).find(
      rule =>
        rule.ruleValue.toolName === agentToolName &&
        rule.ruleValue.ruleContent === agentType,
    ) || null
  )
}
```

---

## 5. Auto Mode 分类器系统

Auto Mode 是 Claude Code 最前沿的权限自动化功能。它使用一个独立的 AI 分类器来代替用户做出 allow/deny 决策，实现真正的"无人值守"工作流。

### 5.1 整体架构

```
工具请求 (behavior: 'ask')
       │
       ├─► 安全检查豁免？ → safetyCheck 且 !classifierApprovable → 直接 ask
       ├─► acceptEdits 快速路径？ → 模拟 acceptEdits 模式检查 → allow
       ├─► 安全工具白名单？ → SAFE_YOLO_ALLOWLISTED_TOOLS → allow
       └─► 调用 classifyYoloAction() → shouldBlock?
             ├─ false → allow（重置连续拒绝计数）
             └─ true  → deny（更新拒绝追踪）
                         └─ 超限？→ 降级到用户提示
```

### 5.2 安全工具白名单 (SAFE_YOLO_ALLOWLISTED_TOOLS)

在调用昂贵的分类器 API 之前，系统先检查工具是否在安全白名单中：

```typescript
// src/utils/permissions/classifierDecision.ts
const SAFE_YOLO_ALLOWLISTED_TOOLS = new Set([
  // 只读文件操作
  FILE_READ_TOOL_NAME,
  // 搜索/只读
  GREP_TOOL_NAME,
  GLOB_TOOL_NAME,
  LSP_TOOL_NAME,
  TOOL_SEARCH_TOOL_NAME,
  LIST_MCP_RESOURCES_TOOL_NAME,
  // 任务管理（只有元数据）
  TODO_WRITE_TOOL_NAME,
  TASK_CREATE_TOOL_NAME,
  TASK_GET_TOOL_NAME,
  // ... 更多安全工具
  // Plan 模式 / UI
  ASK_USER_QUESTION_TOOL_NAME,
  ENTER_PLAN_MODE_TOOL_NAME,
  // 杂项安全工具
  SLEEP_TOOL_NAME,
])

export function isAutoModeAllowlistedTool(toolName: string): boolean {
  return SAFE_YOLO_ALLOWLISTED_TOOLS.has(toolName)
}
```

白名单中的工具不需要分类器检查，直接允许。注意白名单**不包含**写入/编辑工具 —— 那些由 acceptEdits 快速路径处理。

### 5.3 acceptEdits 快速路径

对于文件编辑等操作，系统模拟 `acceptEdits` 模式来检查：

```typescript
// src/utils/permissions/permissions.ts — auto 模式处理
if (result.behavior === 'ask' &&
    tool.name !== AGENT_TOOL_NAME &&  // Agent 和 REPL 排除
    tool.name !== REPL_TOOL_NAME) {
  try {
    const parsedInput = tool.inputSchema.parse(input)
    // 模拟 acceptEdits 模式
    const acceptEditsResult = await tool.checkPermissions(parsedInput, {
      ...context,
      getAppState: () => {
        const state = context.getAppState()
        return {
          ...state,
          toolPermissionContext: {
            ...state.toolPermissionContext,
            mode: 'acceptEdits' as const,
          },
        }
      },
    })
    if (acceptEditsResult.behavior === 'allow') {
      // acceptEdits 允许 → auto 模式也允许，跳过分类器
      return {
        behavior: 'allow',
        updatedInput: acceptEditsResult.updatedInput ?? input,
        decisionReason: { type: 'mode', mode: 'auto' },
      }
    }
  } catch (e) {
    // 失败则继续到分类器
  }
}
```

为什么排除 Agent 和 REPL？注释中解释了：Agent 和 REPL 的 `checkPermissions` 在 acceptEdits 模式下返回 allow，这会静默绕过分类器。REPL 代码可能包含 VM 逃逸，分类器必须检查。

### 5.4 yoloClassifier — 核心分类器

分类器通过一个独立的 Claude API 调用来评估操作安全性：

```typescript
// src/utils/permissions/yoloClassifier.ts

// 分类器工具定义 — 要求模型输出结构化的分类结果
const YOLO_CLASSIFIER_TOOL_SCHEMA: BetaToolUnion = {
  type: 'custom',
  name: 'classify_result',
  description: 'Report the security classification result for the agent action',
  input_schema: {
    type: 'object',
    properties: {
      thinking: {
        type: 'string',
        description: 'Brief step-by-step reasoning.',
      },
      shouldBlock: {
        type: 'boolean',
        description:
          'Whether the action should be blocked (true) or allowed (false)',
      },
      reason: {
        type: 'string',
        description: 'Brief explanation of the classification decision',
      },
    },
    required: ['thinking', 'shouldBlock', 'reason'],
  },
}
```

分类器构建的 transcript 只包含用户消息和助手的 tool_use 块，**不包含助手的文本内容**：

```typescript
// src/utils/permissions/yoloClassifier.ts
export function buildTranscriptEntries(messages: Message[]): TranscriptEntry[] {
  const transcript: TranscriptEntry[] = []
  for (const msg of messages) {
    // ... 处理用户消息
    } else if (msg.type === 'assistant') {
      const blocks: TranscriptBlock[] = []
      for (const block of msg.message.content) {
        // 只包含 tool_use 块 — 助手文本是模型生成的，
        // 可能被精心构造来影响分类器的决策
        if (block.type === 'tool_use') {
          blocks.push({
            type: 'tool_use',
            name: block.name,
            input: block.input,
          })
        }
      }
      // ...
    }
  }
  return transcript
}
```

这是一个重要的安全设计：排除助手文本可以防止模型通过自己的回复来操纵分类器。

### 5.5 用户可自定义的分类器规则 (AutoModeRules)

用户可以通过 `settings.autoMode` 配置来自定义分类器的行为：

```typescript
// src/utils/permissions/yoloClassifier.ts
export type AutoModeRules = {
  allow: string[]      // 允许的操作描述
  soft_deny: string[]  // 软拒绝的操作描述
  environment: string[] // 环境描述
}
```

这些规则被注入到分类器的 system prompt 中，让用户可以精细控制哪些操作在 auto 模式下被允许或阻止。

### 5.6 bashClassifier — Bash 命令语义分类器

`bashClassifier.ts` 在外部构建中是一个存根（stub），但其接口定义了 Bash 命令级别的语义分类：

```typescript
// src/utils/permissions/bashClassifier.ts（外部构建存根）
export type ClassifierResult = {
  matches: boolean           // 是否匹配描述
  matchedDescription?: string // 匹配到的描述
  confidence: 'high' | 'medium' | 'low'
  reason: string
}

export type ClassifierBehavior = 'deny' | 'ask' | 'allow'

// 分类单个 Bash 命令
export async function classifyBashCommand(
  command: string,
  cwd: string,
  descriptions: string[],  // 用户定义的语义描述
  behavior: ClassifierBehavior,
  signal: AbortSignal,
  isNonInteractiveSession: boolean,
): Promise<ClassifierResult> {
  // 内部实现使用 AI 来判断命令是否匹配给定的语义描述
  return {
    matches: false,
    confidence: 'high',
    reason: 'This feature is disabled',
  }
}
```

bashClassifier 使用 `prompt:` 前缀语法让用户定义语义级别的规则。例如 `Bash(prompt: installing new npm packages)` 会使用 AI 来判断一个 Bash 命令是否在"安装新的 npm 包"。

### 5.7 denialTracking — 拒绝追踪与降级机制

当分类器连续拒绝操作时，系统会降级到交互式提示，防止无限循环：

```typescript
// src/utils/permissions/denialTracking.ts
export type DenialTrackingState = {
  consecutiveDenials: number  // 连续拒绝次数
  totalDenials: number        // 总拒绝次数
}

export const DENIAL_LIMITS = {
  maxConsecutive: 3,   // 连续 3 次拒绝 → 降级
  maxTotal: 20,        // 总共 20 次拒绝 → 降级
} as const

export function shouldFallbackToPrompting(state: DenialTrackingState): boolean {
  return (
    state.consecutiveDenials >= DENIAL_LIMITS.maxConsecutive ||
    state.totalDenials >= DENIAL_LIMITS.maxTotal
  )
}

// 记录拒绝
export function recordDenial(state: DenialTrackingState): DenialTrackingState {
  return {
    ...state,
    consecutiveDenials: state.consecutiveDenials + 1,
    totalDenials: state.totalDenials + 1,
  }
}

// 记录成功（重置连续计数，保留总数）
export function recordSuccess(state: DenialTrackingState): DenialTrackingState {
  if (state.consecutiveDenials === 0) return state  // 无变化时返回同一引用
  return {
    ...state,
    consecutiveDenials: 0,
  }
}
```

降级处理的完整逻辑：

```typescript
// src/utils/permissions/permissions.ts
function handleDenialLimitExceeded(
  denialState, appState, classifierReason, assistantMessage, tool, result, context
): PermissionDecision | null {
  if (!shouldFallbackToPrompting(denialState)) {
    return null  // 未超限，不降级
  }

  const hitTotalLimit = denialState.totalDenials >= DENIAL_LIMITS.maxTotal
  const isHeadless = appState.toolPermissionContext.shouldAvoidPermissionPrompts

  if (isHeadless) {
    // 无头模式下超限 → 直接中止代理
    throw new AbortError(
      'Agent aborted: too many classifier denials in headless mode',
    )
  }

  // 交互模式下超限 → 显示警告并降级到手动审批
  // 如果是总数超限，重置计数器（给用户一次审查后继续的机会）
  if (hitTotalLimit) {
    persistDenialState(context, {
      ...denialState,
      totalDenials: 0,
      consecutiveDenials: 0,
    })
  }

  return {
    ...result,
    behavior: 'ask',
    message: `${warning}\n\n${classifierReason}`,
    // 保留原始分类器信息用于分析
  }
}
```

### 5.8 铁门机制 (Iron Gate)

当分类器 API 不可用时，系统根据 `tengu_iron_gate_closed` feature gate 决定行为：

- **Gate 关闭**（铁门关闭）：fail closed，拒绝操作并提供重试指导
- **Gate 开放**：fail open，降级到正常的权限提示流程

```typescript
if (classifierResult.unavailable) {
  if (getFeatureValue_CACHED_WITH_REFRESH(
    'tengu_iron_gate_closed',
    true,   // 默认关闭 → 安全优先
    CLASSIFIER_FAIL_CLOSED_REFRESH_MS,  // 30 分钟刷新
  )) {
    // Fail closed: 拒绝 + 重试指导
    return {
      behavior: 'deny',
      message: buildClassifierUnavailableMessage(tool.name, classifierResult.model),
    }
  }
  // Fail open: 降级到正常权限处理
  return result
}
```

---

## 6. 沙箱系统

Claude Code 的沙箱通过 `@anthropic-ai/sandbox-runtime` 包提供 OS 级别的进程隔离，确保即使权限系统被绕过，Bash 命令的破坏也被限制在一个受控范围内。

### 6.1 沙箱适配层

`src/utils/sandbox/sandbox-adapter.ts` 是连接 sandbox-runtime 和 Claude Code 设置系统的桥梁：

```typescript
// src/utils/sandbox/sandbox-adapter.ts
import {
  SandboxManager as BaseSandboxManager,
  SandboxRuntimeConfigSchema,
  SandboxViolationStore,
} from '@anthropic-ai/sandbox-runtime'
```

沙箱配置通过 `convertToSandboxRuntimeConfig` 从 Claude Code 设置转换为 sandbox-runtime 格式：

```typescript
export function convertToSandboxRuntimeConfig(
  settings: SettingsJson,
): SandboxRuntimeConfig {
  const permissions = settings.permissions || {}

  // 从 WebFetch 规则提取允许的网络域名
  const allowedDomains: string[] = []
  const deniedDomains: string[] = []

  for (const ruleString of permissions.allow || []) {
    const rule = permissionRuleValueFromString(ruleString)
    if (rule.toolName === WEB_FETCH_TOOL_NAME &&
        rule.ruleContent?.startsWith('domain:')) {
      allowedDomains.push(rule.ruleContent.substring('domain:'.length))
    }
  }

  // 文件系统写入：始终允许当前目录和临时目录
  const allowWrite: string[] = ['.', getClaudeTempDir()]
  const denyWrite: string[] = []

  // 安全关键：始终禁止写入 settings.json 文件（防止沙箱逃逸）
  const settingsPaths = SETTING_SOURCES.map(source =>
    getSettingsFilePathForSource(source),
  ).filter((p): p is string => p !== undefined)
  denyWrite.push(...settingsPaths)

  // 禁止写入 .claude/skills（与 .claude/commands 同等特权级别）
  denyWrite.push(resolve(originalCwd, '.claude', 'skills'))

  // 防止裸 git 仓库攻击：禁止写入 HEAD、objects/、refs/ 等文件
  // 攻击者可以伪造这些文件让 git 认为 cwd 是裸仓库，
  // 然后通过 core.fsmonitor 执行任意代码
  const bareGitRepoFiles = ['HEAD', 'objects', 'refs', 'hooks', 'config']
  for (const gitFile of bareGitRepoFiles) {
    const p = resolve(dir, gitFile)
    try {
      statSync(p)
      denyWrite.push(p)  // 文件存在 → 禁止写入（只读绑定）
    } catch {
      bareGitRepoScrubPaths.push(p)  // 文件不存在 → 命令后清理
    }
  }

  return {
    network: {
      allowedDomains,
      deniedDomains,
      allowUnixSockets: settings.sandbox?.network?.allowUnixSockets,
      allowLocalBinding: settings.sandbox?.network?.allowLocalBinding,
      // ...
    },
    filesystem: {
      denyRead,
      allowRead,
      allowWrite,
      denyWrite,
    },
    // ...
  }
}
```

### 6.2 网络限制

沙箱对网络访问实施域名级白名单控制：

- 默认阻止所有出站网络连接
- 只允许访问 `allowedDomains` 中的域名
- `deniedDomains` 可以覆盖允许的域名
- Unix socket 和本地绑定需要单独配置

网络域名从两个地方收集：
1. `settings.sandbox.network.allowedDomains` — 直接配置
2. `permissions.allow` 中的 `WebFetch(domain:example.com)` 规则 — 从权限规则推导

### 6.3 文件系统限制

文件系统限制分为读和写两个维度：

```typescript
filesystem: {
  allowWrite: ['.', getClaudeTempDir()],  // 允许写入当前目录和临时目录
  denyWrite: [...settingsPaths, ...skillsPaths, ...bareGitFiles],
  denyRead: [...],   // 禁止读取的路径
  allowRead: [...],  // 允许读取的路径
}
```

关键的写入保护：
- **设置文件**：所有 settings.json 文件都禁止写入，防止沙箱内的命令修改权限配置
- **技能目录**：`.claude/skills` 禁止写入，因为技能与命令具有相同的特权级别
- **裸 git 仓库文件**：防止攻击者通过伪造 git 仓库结构来执行代码

### 6.4 shouldUseSandbox 决策

并非所有 Bash 命令都在沙箱中运行：

```typescript
// src/tools/BashTool/shouldUseSandbox.ts
export function shouldUseSandbox(input: Partial<SandboxInput>): boolean {
  // 沙箱未启用 → 不使用
  if (!SandboxManager.isSandboxingEnabled()) return false

  // 显式禁用且策略允许 → 不使用
  if (input.dangerouslyDisableSandbox &&
      SandboxManager.areUnsandboxedCommandsAllowed()) {
    return false
  }

  // 无命令 → 不使用
  if (!input.command) return false

  // 命令匹配用户配置的排除列表 → 不使用
  if (containsExcludedCommand(input.command)) return false

  return true
}
```

`dangerouslyDisableSandbox` 是工具输入的一个参数，允许模型请求在沙箱外运行命令。但这不是无条件的：

1. 必须 `areUnsandboxedCommandsAllowed()` 返回 true（策略允许）
2. 如果策略不允许，`dangerouslyDisableSandbox` 被忽略，命令仍在沙箱中运行
3. 在沙箱外运行通常需要额外的用户确认（通过权限系统的 `sandboxOverride` 决策原因）

### 6.5 排除命令

用户可以配置某些命令不在沙箱中运行：

```typescript
function containsExcludedCommand(command: string): boolean {
  const settings = getSettings_DEPRECATED()
  const userExcludedCommands = settings.sandbox?.excludedCommands ?? []

  // 将复合命令拆分为子命令，逐一检查
  let subcommands: string[]
  try {
    subcommands = splitCommand_DEPRECATED(command)
  } catch {
    subcommands = [command]
  }

  for (const subcommand of subcommands) {
    // 对每个子命令：
    // 1. 原始命令
    // 2. 去除安全环境变量前缀后的命令
    // 3. 去除安全包装命令后的命令
    // 迭代应用直到不产生新候选（固定点）
    const candidates = [trimmed]
    // ... 固定点迭代逻辑

    for (const pattern of userExcludedCommands) {
      const rule = bashPermissionRule(pattern)
      for (const cand of candidates) {
        // 使用与权限规则相同的匹配逻辑
        // ...
      }
    }
  }
  return false
}
```

**重要提示**：排除命令不是安全边界。注释中明确指出：

> NOTE: excludedCommands is a user-facing convenience feature, not a security boundary. It is not a security bug to be able to bypass excludedCommands — the sandbox permission system (which prompts users) is the actual security control.

---

## 7. 工作区信任机制

Claude Code 的文件操作安全基于"工作目录信任"概念：在当前工作目录内的操作被认为是预期的，而工作目录外的操作需要额外审查。

### 7.1 敏感文件和目录保护

`src/utils/permissions/filesystem.ts` 定义了需要特殊保护的文件和目录：

```typescript
// src/utils/permissions/filesystem.ts
export const DANGEROUS_FILES = [
  '.gitconfig',
  '.gitmodules',
  '.bashrc',
  '.bash_profile',
  '.zshrc',
  '.zprofile',
  '.profile',
  '.ripgreprc',
  '.mcp.json',
  '.claude.json',
] as const

export const DANGEROUS_DIRECTORIES = [
  '.git',
  '.vscode',
  '.idea',
  '.claude',
] as const
```

即使在 `bypassPermissions` 模式下，对这些文件和目录的编辑也会触发 `safetyCheck` 类型的 ask 决策，强制用户确认。这个检查在步骤 1g 中实现：

```typescript
// 1g. Safety checks — bypass-immune
if (
  toolPermissionResult?.behavior === 'ask' &&
  toolPermissionResult.decisionReason?.type === 'safetyCheck'
) {
  return toolPermissionResult  // 即使 bypass 模式也不跳过
}
```

在 auto 模式下，`safetyCheck` 的处理更加细腻：

```typescript
// safetyCheck 在 auto 模式下的处理
if (result.decisionReason?.type === 'safetyCheck' &&
    !result.decisionReason.classifierApprovable) {
  // 不可被分类器批准的安全检查 → 必须人工确认
  // 例如：Windows 路径绕过尝试、跨机器桥接消息
  return result
}
// classifierApprovable 的安全检查（如敏感文件编辑）→ 交给分类器评估
```

`classifierApprovable` 标志区分了两类安全检查：
- 敏感文件路径编辑（`.claude/`、`.git/`、shell 配置文件）→ 分类器可以根据上下文判断
- 路径绕过攻击（Windows UNC 路径等）→ 必须人工确认

### 7.2 路径验证

文件工具通过 `pathInAllowedWorkingPath` 检查路径是否在允许的工作范围内：

- 当前工作目录（`cwd`）
- 通过 `--add-dir` 添加的额外目录
- 设置中配置的 `additionalDirectories`

超出这些范围的路径操作需要匹配明确的 allow 规则，或者获得用户批准。

### 7.3 托管策略 (policySettings)

企业环境中，管理员可以通过 `policySettings` 强制执行安全策略：

```typescript
// src/utils/permissions/permissionsLoader.ts
export function shouldAllowManagedPermissionRulesOnly(): boolean {
  return (
    getSettingsForSource('policySettings')?.allowManagedPermissionRulesOnly ===
    true
  )
}
```

当此选项开启时：
1. 所有非 policy 来源的规则被清空
2. 权限提示中不显示 "Always allow" 选项
3. 用户无法自行添加持久化的 allow 规则
4. 只有管理员配置的规则生效

---

## 8. PermissionResult 类型系统

权限系统的类型设计体现了 TypeScript 类型系统在安全关键代码中的应用。

### 8.1 决策类型

```typescript
// src/types/permissions.ts

// 允许 — 操作可以执行
export type PermissionAllowDecision<Input = { [key: string]: unknown }> = {
  behavior: 'allow'
  updatedInput?: Input       // 工具输入可能被 hook 或用户修改
  userModified?: boolean     // 用户是否修改了输入
  decisionReason?: PermissionDecisionReason
  acceptFeedback?: string    // 用户批准时附带的反馈
  contentBlocks?: ContentBlockParam[]
}

// 询问 — 需要用户确认
export type PermissionAskDecision<Input = { [key: string]: unknown }> = {
  behavior: 'ask'
  message: string             // 显示给用户的消息
  updatedInput?: Input
  decisionReason?: PermissionDecisionReason
  suggestions?: PermissionUpdate[]  // 建议的 "Always allow" 规则
  blockedPath?: string        // 被阻止的路径（用于 UI 展示）
  pendingClassifierCheck?: PendingClassifierCheck  // 异步分类器检查
}

// 拒绝 — 操作被禁止
export type PermissionDenyDecision = {
  behavior: 'deny'
  message: string
  decisionReason: PermissionDecisionReason  // 注意：deny 必须有原因
}

// 三选一联合类型
export type PermissionDecision<Input = { [key: string]: unknown }> =
  | PermissionAllowDecision<Input>
  | PermissionAskDecision<Input>
  | PermissionDenyDecision
```

### 8.2 passthrough 特殊行为

`PermissionResult` 在 `PermissionDecision` 基础上增加了 `passthrough`：

```typescript
export type PermissionResult<Input = { [key: string]: unknown }> =
  | PermissionDecision<Input>
  | {
      behavior: 'passthrough'  // 工具不关心，让框架决定
      message: string
      decisionReason?: PermissionDecision<Input>['decisionReason']
      suggestions?: PermissionUpdate[]
      blockedPath?: string
      pendingClassifierCheck?: PendingClassifierCheck
    }
```

`passthrough` 的设计意图是：工具的 `checkPermissions` 返回 "我没有特别的意见"，让权限框架根据模式和规则来决定。在主流水线的步骤 3 中，`passthrough` 被转换为 `ask`。

### 8.3 决策原因 (PermissionDecisionReason)

每个权限决策都携带原因，用于日志、分析和用户展示：

```typescript
export type PermissionDecisionReason =
  | { type: 'rule'; rule: PermissionRule }               // 规则匹配
  | { type: 'mode'; mode: PermissionMode }                // 模式决定
  | { type: 'subcommandResults'; reasons: Map<string, PermissionResult> }  // 复合命令
  | { type: 'permissionPromptTool'; permissionPromptToolName: string }     // 权限提示工具
  | { type: 'hook'; hookName: string; hookSource?: string; reason?: string }  // Hook 决定
  | { type: 'asyncAgent'; reason: string }                // 异步代理
  | { type: 'sandboxOverride'; reason: string }           // 沙箱覆盖
  | { type: 'classifier'; classifier: string; reason: string }  // 分类器决定
  | { type: 'workingDir'; reason: string }                // 工作目录问题
  | { type: 'safetyCheck'; reason: string; classifierApprovable: boolean }  // 安全检查
  | { type: 'other'; reason: string }                     // 其他
```

这种详细的原因追踪使得：
1. 用户在权限对话框中能看到清晰的解释
2. 分析系统能追踪每个决策的来源
3. Hook 系统能根据原因做出进一步判断

---

## 9. Hook 系统与权限集成

### 9.1 PreToolUse Hooks

`src/services/tools/toolHooks.ts` 中的 `runPreToolUseHooks` 在工具执行前运行用户配置的 hooks：

```typescript
// src/services/tools/toolHooks.ts
export async function* runPreToolUseHooks(
  toolUseContext, tool, processedInput, toolUseID, messageId, ...
): AsyncGenerator<
  | { type: 'hookPermissionResult'; hookPermissionResult: PermissionResult }
  | { type: 'hookUpdatedInput'; updatedInput: Record<string, unknown> }
  | { type: 'preventContinuation'; shouldPreventContinuation: boolean }
  | { type: 'stop' }
  // ...
> {
  for await (const result of executePreToolHooks(...)) {
    // Hook 返回 blockingError → deny
    if (result.blockingError) {
      yield {
        type: 'hookPermissionResult',
        hookPermissionResult: {
          behavior: 'deny',
          message: denialMessage,
          decisionReason: {
            type: 'hook',
            hookName: `PreToolUse:${tool.name}`,
            reason: denialMessage,
          },
        },
      }
    }

    // Hook 返回 permissionBehavior → 按行为分发
    if (result.permissionBehavior === 'allow') {
      yield {
        type: 'hookPermissionResult',
        hookPermissionResult: {
          behavior: 'allow',
          updatedInput: result.updatedInput,
          decisionReason: { type: 'hook', hookName: `PreToolUse:${tool.name}` },
        },
      }
    }
    // ... deny、ask 类似处理
  }
}
```

### 9.2 Hook allow 不绕过 deny/ask 规则

这是一个关键的安全设计：`resolveHookPermissionDecision` 确保 hook 的 allow 不能覆盖设置中的 deny/ask 规则：

```typescript
// src/services/tools/toolHooks.ts
export async function resolveHookPermissionDecision(
  hookPermissionResult, tool, input, toolUseContext, canUseTool, ...
): Promise<{ decision: PermissionDecision; input: Record<string, unknown> }> {

  if (hookPermissionResult?.behavior === 'allow') {
    const hookInput = hookPermissionResult.updatedInput ?? input

    // Hook allow 跳过交互式提示，但 deny/ask 规则仍然适用
    const ruleCheck = await checkRuleBasedPermissions(tool, hookInput, toolUseContext)

    if (ruleCheck === null) {
      // 没有规则阻止 → hook allow 生效
      return { decision: hookPermissionResult, input: hookInput }
    }

    if (ruleCheck.behavior === 'deny') {
      // deny 规则覆盖 hook allow
      return { decision: ruleCheck, input: hookInput }
    }

    // ask 规则 → 即使 hook 批准也要显示对话框
    return {
      decision: await canUseTool(tool, hookInput, ...),
      input: hookInput,
    }
  }

  // ...
}
```

这个设计确保了：
- Hook 不能静默绕过管理员配置的 deny 规则
- Hook 不能跳过安全关键的 ask 规则
- Hook 可以修改工具输入（`updatedInput`），但最终还是要通过规则检查

### 9.3 PermissionRequest Hooks

除了 PreToolUse hooks，还有 PermissionRequest hooks，在权限对话框显示时触发：

```typescript
// src/hooks/toolPermission/PermissionContext.ts
async runHooks(
  permissionMode, suggestions, updatedInput?, permissionPromptStartTimeMs?
): Promise<PermissionDecision | null> {
  for await (const hookResult of executePermissionRequestHooks(
    tool.name, toolUseID, input, toolUseContext, ...
  )) {
    if (hookResult.permissionRequestResult) {
      const decision = hookResult.permissionRequestResult
      if (decision.behavior === 'allow') {
        return await this.handleHookAllow(
          finalInput, decision.updatedPermissions ?? [], ...
        )
      } else if (decision.behavior === 'deny') {
        return this.buildDeny(
          decision.message || 'Permission denied by hook',
          { type: 'hook', hookName: 'PermissionRequest', reason: decision.message },
        )
      }
    }
  }
  return null  // 没有 hook 做出决策
}
```

PermissionRequest hooks 特别适用于：
- 自动化审批系统（如 CI/CD 中的自动批准 hook）
- 自定义权限 UI（替换默认的终端对话框）
- 无头代理的权限管理

---

## 10. Bash 安全检查深度解析

`src/tools/BashTool/bashSecurity.ts` 实现了 Bash 命令的深度安全检查，防止通过命令注入、替换和混淆来绕过权限系统。

### 10.1 危险模式检测

系统检测以下类别的危险命令模式：

```typescript
// src/tools/BashTool/bashSecurity.ts
const COMMAND_SUBSTITUTION_PATTERNS = [
  { pattern: /<\(/, message: 'process substitution <()' },
  { pattern: />\(/, message: 'process substitution >()' },
  { pattern: /=\(/, message: 'Zsh process substitution =()' },
  // Zsh EQUALS 扩展：=cmd 在单词开头扩展为 $(which cmd)
  // `=curl evil.com` → `/usr/bin/curl evil.com`，绕过 Bash(curl:*) deny 规则
  { pattern: /(?:^|[\s;&|])=[a-zA-Z_]/, message: 'Zsh equals expansion (=cmd)' },
  { pattern: /\$\(/, message: '$() command substitution' },
  { pattern: /\$\{/, message: '${} parameter substitution' },
  { pattern: /\$\[/, message: '$[] legacy arithmetic expansion' },
  // ...
]
```

### 10.2 Zsh 特有的危险命令

```typescript
const ZSH_DANGEROUS_COMMANDS = new Set([
  'zmodload',    // 加载模块 → zsh/mapfile（文件IO）、zsh/zpty（执行命令）等
  'emulate',     // emulate -c 是 eval 等价物
  'sysopen',     // 文件描述符操作
  'sysread',
  'syswrite',
  'sysseek',
  'zpty',        // 伪终端命令执行
  'ztcp',        // TCP 连接（数据外泄）
  'zsocket',     // Unix/TCP 套接字
  'mapfile',     // 通过数组赋值的文件 IO
  'zf_rm',       // zsh/files 模块的内置命令
  'zf_mv',
  'zf_ln',
  'zf_chmod',
  // ...
])
```

这些 Zsh 特有的攻击向量特别隐蔽 —— 它们不调用外部程序，而是使用 Zsh 的内置模块来绕过安全检查。

### 10.3 安全环境变量白名单

BashTool 维护了一个安全环境变量白名单，用于命令匹配前的规范化：

```typescript
// src/tools/BashTool/bashPermissions.ts
const SAFE_ENV_VARS = new Set([
  // 绝对不能添加到白名单的变量：
  // PATH, LD_PRELOAD, LD_LIBRARY_PATH, DYLD_* — 执行/库加载
  // PYTHONPATH, NODE_PATH, CLASSPATH — 模块加载
  // GOFLAGS, RUSTFLAGS, NODE_OPTIONS — 可包含代码执行标志
  // HOME, TMPDIR, SHELL, BASH_ENV — 影响系统行为

  // Go - 构建/运行时设置
  'GOEXPERIMENT', 'GOOS', 'GOARCH', 'CGO_ENABLED', 'GO111MODULE',
  // Rust - 日志/调试
  'RUST_BACKTRACE', 'RUST_LOG',
  // Node - 仅环境名称（不包括 NODE_OPTIONS！）
  'NODE_ENV',
  // Python - 行为标志（不包括 PYTHONPATH！）
  'PYTHONUNBUFFERED', 'PYTHONDONTWRITEBYTECODE',
  // 终端和显示
  'TERM', 'COLORTERM', 'NO_COLOR', 'FORCE_COLOR', 'TZ',
  // ...
])
```

白名单中的环境变量在匹配权限规则前会被去除，使得 `NODE_ENV=production npm run build` 可以匹配 `Bash(npm run:*)` 规则。注释中详细说明了哪些变量**绝对不能**被白名单化，因为它们可以用于代码注入。

### 10.4 危险前缀检测

为了防止过于宽泛的 allow 规则，系统定义了一组危险的命令前缀：

```typescript
// src/utils/permissions/dangerousPatterns.ts
export const DANGEROUS_BASH_PATTERNS: readonly string[] = [
  // 跨平台代码执行入口
  'python', 'python3', 'python2',
  'node', 'deno', 'tsx',
  'ruby', 'perl', 'php', 'lua',
  // 包运行器
  'npx', 'bunx',
  'npm run', 'yarn run', 'pnpm run', 'bun run',
  // Shell
  'bash', 'sh', 'zsh', 'fish',
  // eval/exec
  'eval', 'exec', 'env', 'xargs',
  // 特权提升
  'sudo',
  // 远程命令
  'ssh',
]
```

例如 `Bash(python:*)` 是一个危险的 allow 规则，因为它允许执行任意 Python 代码。进入 auto 模式时，这类规则会被自动剥离：

```typescript
// 进入 auto 模式时，危险的 allow 规则被移除
// 原始规则保存在 strippedDangerousRules 中，退出 auto 模式时恢复
```

---

## 11. 安全设计原则总结

Claude Code 的权限系统体现了多项安全工程最佳实践：

### 11.1 纵深防御 (Defense in Depth)

每一层都独立提供保护：
- **规则层**：deny/ask/allow 三元组，deny 优先
- **工具层**：每个工具的 `checkPermissions` 做上下文相关的检查
- **模式层**：全局模式控制（bypass/acceptEdits/default/dontAsk/auto）
- **分类器层**：AI 驱动的语义级安全评估
- **沙箱层**：OS 级进程隔离
- **Hook 层**：可扩展的策略执行点

### 11.2 失败安全 (Fail-Safe Defaults)

- 默认模式是 `default`（需要确认）
- 未知工具的 `checkPermissions` 返回 `passthrough` → 转为 `ask`
- 分类器不可用时默认 fail-closed（铁门机制）
- 安全检查不可被任何模式绕过（bypass-immune）

### 11.3 最小权限 (Least Privilege)

- 只读工具（Grep、Glob、Read）不需要权限
- 文件编辑限制在工作目录内
- Shell 命令需要逐个审批（或匹配明确的规则）
- MCP 工具默认需要确认

### 11.4 不可变性与审计

- `ToolPermissionContext` 使用 `DeepImmutable` 包装
- 所有状态变更通过 `applyPermissionUpdate` 产生新对象
- 每个决策携带 `PermissionDecisionReason`，支持完整审计
- 分析事件 (`logEvent`) 记录每次权限决策

### 11.5 分离信任域

- 用户文本和助手 tool_use 是分类器的输入，但助手的自由文本被排除（防止自我操纵）
- Hook allow 不能覆盖 deny/ask 规则（Hook 不是上帝）
- 沙箱配置独立于权限规则（双重保护）
- policySettings 可以覆盖所有其他来源（管理员权威）

### 11.6 可恢复性

- `prePlanMode` 允许从 plan 模式恢复到之前的模式
- `strippedDangerousRules` 允许退出 auto 模式时恢复规则
- denial tracking 的连续计数器在成功后重置
- 总拒绝计数器在用户审查后重置

### 11.7 防御性编程

- 权限检查中的错误被捕获并记录，不会阻塞操作（但 AbortError 除外）
- 复合命令有子命令数量上限（`MAX_SUBCOMMANDS_FOR_SECURITY_CHECK = 50`）
- 规则解析处理各种边界情况（转义括号、遗留格式、空内容）
- 裸 git 仓库攻击防御（命令后清理伪造的 git 文件）

---

## 附录：核心文件速查表

| 文件路径 | 核心导出 | 用途 |
|---|---|---|
| `src/types/permissions.ts` | `PermissionMode`, `PermissionDecision`, `PermissionResult`, `PermissionDecisionReason` | 所有权限类型定义 |
| `src/Tool.ts` | `ToolPermissionContext`, `getEmptyToolPermissionContext` | 权限上下文结构 |
| `src/utils/permissions/permissions.ts` | `hasPermissionsToUseTool`, `checkRuleBasedPermissions`, `getAllowRules`, `getDenyRules` | 权限决策主流水线 |
| `src/utils/permissions/PermissionMode.ts` | `permissionModeTitle`, `isDefaultMode`, `getModeColor` | 模式工具函数 |
| `src/utils/permissions/permissionRuleParser.ts` | `permissionRuleValueFromString`, `permissionRuleValueToString` | 规则字符串解析 |
| `src/utils/permissions/shellRuleMatching.ts` | `matchWildcardPattern`, `parsePermissionRule`, `ShellPermissionRule` | Shell 命令规则匹配 |
| `src/utils/permissions/yoloClassifier.ts` | `classifyYoloAction`, `buildTranscriptEntries`, `AutoModeRules` | Auto Mode 分类器 |
| `src/utils/permissions/classifierDecision.ts` | `isAutoModeAllowlistedTool` | 安全工具白名单 |
| `src/utils/permissions/denialTracking.ts` | `DenialTrackingState`, `DENIAL_LIMITS`, `shouldFallbackToPrompting` | 拒绝追踪 |
| `src/utils/permissions/filesystem.ts` | `DANGEROUS_FILES`, `DANGEROUS_DIRECTORIES`, `pathInAllowedWorkingPath` | 文件系统安全 |
| `src/utils/permissions/dangerousPatterns.ts` | `DANGEROUS_BASH_PATTERNS`, `CROSS_PLATFORM_CODE_EXEC` | 危险命令模式 |
| `src/tools/BashTool/bashPermissions.ts` | `bashPermissionRule`, `matchWildcardPattern`, `SAFE_ENV_VARS` | Bash 权限规则匹配 |
| `src/tools/BashTool/bashSecurity.ts` | `bashCommandIsSafeAsync_DEPRECATED` | Bash 安全检查 |
| `src/tools/BashTool/shouldUseSandbox.ts` | `shouldUseSandbox` | 沙箱使用决策 |
| `src/utils/sandbox/sandbox-adapter.ts` | `SandboxManager`, `convertToSandboxRuntimeConfig` | 沙箱适配层 |
| `src/services/tools/toolHooks.ts` | `runPreToolUseHooks`, `resolveHookPermissionDecision` | Hook 与权限集成 |
| `src/hooks/toolPermission/PermissionContext.ts` | `createPermissionContext`, `PermissionContext` | 权限交互上下文 |
| `src/utils/permissions/bypassPermissionsKillswitch.ts` | `checkAndDisableBypassPermissionsIfNeeded` | Bypass 模式熔断 |
| `src/utils/permissions/permissionsLoader.ts` | `shouldAllowManagedPermissionRulesOnly` | 托管策略加载 |
