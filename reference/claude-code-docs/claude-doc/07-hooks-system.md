# 第 7 篇：Hooks 系统

## 1. 概述：Hooks 在 Claude Code 中的角色

Hooks 是 Claude Code 提供的**生命周期扩展点**。它们允许用户在 CLI 运行的各个关键节点插入自定义逻辑——从会话启动、工具调用前后、到用户提交 prompt 的瞬间，再到 compaction 和会话结束。

与 Git hooks 类似，Claude Code Hooks 的核心设计理念是**约定大于配置**：用户在 `settings.json` 中声明 matcher 和 command，系统在对应事件触发时自动执行。但 Claude Code 的 Hooks 远比 Git hooks 复杂——它们支持 5 种 Hook 来源类型（命令、Prompt、HTTP、Agent、函数），拥有精密的 JSON 输出协议，与权限系统深度交互，并且支持异步后台执行和 asyncRewake 唤醒模型。

### 核心源码文件

| 文件 | 职责 |
|------|------|
| `src/utils/hooks.ts` | Hooks 核心引擎（~5000 行），包含所有 execute* 函数 |
| `src/services/tools/toolHooks.ts` | 工具级 Hook 执行与权限决策解析 |
| `src/types/hooks.ts` | Hook JSON 输出的 Zod schema 定义 |
| `src/entrypoints/sdk/coreTypes.ts` | HookEvent 枚举定义 |
| `src/utils/hooks/execPromptHook.ts` | Prompt Hook 执行器 |
| `src/utils/hooks/execAgentHook.ts` | Agent Hook 执行器 |
| `src/utils/hooks/execHttpHook.ts` | HTTP Hook 执行器 |
| `src/utils/hooks/sessionHooks.ts` | 会话级 Hook 存储（FunctionHook） |
| `src/utils/hooks/AsyncHookRegistry.ts` | 异步 Hook 注册表 |
| `src/hooks/toolPermission/` | 工具权限处理（交互式/协调者/Swarm） |

---

## 2. Hook 事件类型详解

Claude Code 定义了 **27 种** Hook 事件，在 `src/entrypoints/sdk/coreTypes.ts` 中通过 `HOOK_EVENTS` 常量数组声明：

```typescript
// src/entrypoints/sdk/coreTypes.ts
export const HOOK_EVENTS = [
  'PreToolUse', 'PostToolUse', 'PostToolUseFailure',
  'Notification', 'UserPromptSubmit',
  'SessionStart', 'SessionEnd',
  'Stop', 'StopFailure',
  'SubagentStart', 'SubagentStop',
  'PreCompact', 'PostCompact',
  'PermissionRequest', 'PermissionDenied',
  'Setup', 'TeammateIdle',
  'TaskCreated', 'TaskCompleted',
  'Elicitation', 'ElicitationResult',
  'ConfigChange',
  'WorktreeCreate', 'WorktreeRemove',
  'InstructionsLoaded',
  'CwdChanged', 'FileChanged',
] as const
```

以下是各事件的详细说明：

### 2.1 工具生命周期 Hooks

| 事件 | 触发时机 | 是否阻塞 | 用途 |
|------|----------|----------|------|
| **PreToolUse** | 工具执行**前** | 是（可通过 exit code 2 或 JSON `decision: "block"` 阻塞） | 审计、输入校验、权限决策（allow/deny/ask）、输入修改（updatedInput） |
| **PostToolUse** | 工具执行**成功后** | 是（可阻塞并阻止后续 continuation） | 输出审计、附加上下文注入、MCP 工具输出替换（updatedMCPToolOutput） |
| **PostToolUseFailure** | 工具执行**失败后** | 是 | 失败分析、附加上下文注入、错误恢复提示 |

PreToolUse 是最核心的 Hook 事件。它的 matcher 按 tool name 匹配（如 `Write`、`Bash`、`Edit`），支持正则表达式和 pipe 分隔多值。其输入包含 `tool_name`、`tool_input`、`tool_use_id`，hooks 可以返回 `permissionDecision`（allow/deny/ask）来影响权限流。

### 2.2 会话生命周期 Hooks

| 事件 | 触发时机 | 是否阻塞 | 用途 |
|------|----------|----------|------|
| **SessionStart** | 会话开始（startup/resume/clear/compact） | 否（fire-and-forget 式） | 环境初始化、设置 CLAUDE_ENV_FILE 环境变量、返回 watchPaths |
| **SessionEnd** | 会话结束 | 否（超时 1.5 秒） | 清理资源、持久化状态。超时极短以避免阻塞退出 |
| **Setup** | 初始化（init/maintenance） | 否 | 一次性设置任务（安装依赖、配置环境） |

SessionEnd 有专门的超时常量：

```typescript
// src/utils/hooks.ts
const SESSION_END_HOOK_TIMEOUT_MS_DEFAULT = 1500
// 可通过 CLAUDE_CODE_SESSIONEND_HOOKS_TIMEOUT_MS 环境变量覆盖
```

### 2.3 停止与反馈 Hooks

| 事件 | 触发时机 | 是否阻塞 | 用途 |
|------|----------|----------|------|
| **Stop** | 模型即将停止回复时 | 是（exit code 2 可以给模型反馈，阻止其停止） | 验证输出质量、强制模型继续工作 |
| **StopFailure** | 模型因 API 错误等原因停止 | 否 | 错误处理、通知 |

Stop Hook 是一个强大的质量保障工具。当 Hook 以 exit code 2 返回时，其 stderr 内容会作为反馈消息注入模型上下文，迫使模型重新审视并继续工作。

### 2.4 子 Agent 生命周期 Hooks

| 事件 | 触发时机 | 是否阻塞 | 用途 |
|------|----------|----------|------|
| **SubagentStart** | 子 agent 启动 | 否 | 注入额外上下文（additionalContext） |
| **SubagentStop** | 子 agent 完成 | 是 | 验证子 agent 产出质量 |

### 2.5 用户交互 Hooks

| 事件 | 触发时机 | 是否阻塞 | 用途 |
|------|----------|----------|------|
| **UserPromptSubmit** | 用户提交 prompt 后、发送给模型**前** | 是（exit code 2 阻塞提交） | 注入上下文（additionalContext）、过滤不当请求 |
| **PermissionRequest** | 即将弹出权限对话框时 | 是 | 自动化权限决策（headless 模式关键） |
| **PermissionDenied** | 权限被拒绝后 | 否 | 审计日志、retry 触发 |

### 2.6 Compaction Hooks

| 事件 | 触发时机 | 是否阻塞 | 用途 |
|------|----------|----------|------|
| **PreCompact** | 上下文压缩**前** | 否 | 自定义压缩指令（返回的 stdout 会替代默认压缩 instructions） |
| **PostCompact** | 上下文压缩**后** | 否 | 记录压缩摘要、触发后续操作 |

### 2.7 团队与任务协作 Hooks

| 事件 | 触发时机 | 是否阻塞 | 用途 |
|------|----------|----------|------|
| **TeammateIdle** | 团队成员即将闲置 | 是 | 分配新任务，阻止闲置 |
| **TaskCreated** | 任务创建时 | 是 | 审核任务、阻止不合规任务 |
| **TaskCompleted** | 任务完成时 | 是 | 验证任务质量 |

### 2.8 MCP 交互 Hooks

| 事件 | 触发时机 | 是否阻塞 | 用途 |
|------|----------|----------|------|
| **Elicitation** | MCP 服务器发起表单/URL 请求时 | 是 | 自动填表、拒绝请求 |
| **ElicitationResult** | 用户对 Elicitation 回应后 | 是 | 拦截或修改回应 |

### 2.9 配置与环境 Hooks

| 事件 | 触发时机 | 是否阻塞 | 用途 |
|------|----------|----------|------|
| **ConfigChange** | 配置文件变更时 | 否（policy_settings 源强制不阻塞） | 审计日志、安全监控 |
| **InstructionsLoaded** | CLAUDE.md 或规则文件加载时 | 否（observability only） | 审计哪些指令被加载 |
| **CwdChanged** | 工作目录变更时 | 否 | 环境变量刷新、返回新 watchPaths |
| **FileChanged** | 被监视文件变化时 | 否 | 触发环境重载 |
| **Notification** | 系统发出通知时 | 否 | 自定义通知渠道（Slack、邮件等） |

### 2.10 工作树 Hooks

| 事件 | 触发时机 | 是否阻塞 | 用途 |
|------|----------|----------|------|
| **WorktreeCreate** | Git worktree 创建时 | 是 | 自定义 worktree 路径 |
| **WorktreeRemove** | Git worktree 删除时 | 否 | 清理资源 |

---

## 3. Hook 来源类型

Claude Code 支持 **6 种** Hook 实现方式，每种有不同的适用场景：

### 3.1 Command Hook（命令 Hook）

最基本的 Hook 类型。在 `settings.json` 中配置一个 shell 命令，系统通过 `spawn()` 执行：

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash",
      "hooks": [{
        "type": "command",
        "command": "python3 /path/to/validator.py",
        "timeout": 30,
        "shell": "bash"
      }]
    }]
  }
}
```

执行流程（`execCommandHook` 函数）：
1. 解析 shell 类型（bash 或 powershell）
2. 替换 `${CLAUDE_PLUGIN_ROOT}`、`${user_config.X}` 等变量
3. 构建环境变量（`CLAUDE_PROJECT_DIR`、`CLAUDE_ENV_FILE` 等）
4. 通过 `spawn()` 启动子进程
5. 将 Hook 输入 JSON 写入 stdin
6. 收集 stdout/stderr，解析输出

**关键约定**：
- Exit code 0 = 成功
- Exit code 2 = 阻塞（stderr 作为反馈消息）
- 其他非零 = 非阻塞错误
- stdout 以 `{` 开头则尝试 JSON 解析

### 3.2 Prompt Hook

使用 LLM（小模型 Haiku）来执行 Hook 逻辑。适合需要语义理解的场景：

```json
{
  "type": "prompt",
  "prompt": "检查以下工具调用是否安全：$ARGUMENTS"
}
```

`execPromptHook` 将 `$ARGUMENTS` 替换为序列化的 Hook 输入 JSON，然后调用小型模型（getSmallFastModel）。Prompt Hook 不会触发 UserPromptSubmit Hook（避免无限递归）。

### 3.3 HTTP Hook

通过 HTTP POST 请求调用外部服务。适合集成现有 API 或 webhook：

```json
{
  "type": "http",
  "url": "https://audit.company.com/hook",
  "timeout": 10
}
```

特殊行为：
- HTTP hooks **不支持** SessionStart 和 Setup 事件（headless 模式死锁风险）
- 内置 SSRF 防护（`ssrfGuardedLookup`）
- 支持 `allowedHttpHookUrls` 白名单策略
- 请求头值会被清理以防止 CRLF 注入
- 必须返回 JSON（空 body 视为空对象 `{}`）

### 3.4 Agent Hook

启动一个完整的子 agent 来执行 Hook。适合需要多轮对话和工具调用的复杂逻辑：

```json
{
  "type": "agent",
  "prompt": "验证代码变更是否符合规范：$ARGUMENTS"
}
```

Agent Hook 会创建独立的 agent 上下文，拥有自己的 transcript，可以使用工具（但排除危险工具），最终通过结构化输出返回 Hook 结果。

### 3.5 Callback Hook（回调 Hook）

内部使用的 SDK 级 Hook，通过 `registerHookCallbacks()` 注册 TypeScript 函数。不需要序列化，直接在进程内执行：

```typescript
// 内部使用示例
hook.callback(hookInput, toolUseID, signal, hookIndex, context)
```

Callback hooks 分为 `internal`（系统内部如文件访问跟踪）和非 internal（插件注册）两种。当一批 hooks 全部是 internal callback 时，系统走快速路径，跳过 span/progress/abort 等开销。

### 3.6 Function Hook（函数 Hook）

会话级别的内存 Hook，不可持久化。通过 `addFunctionHook()` 注册，典型用途是结构化输出强制（schema enforcement）：

```typescript
// src/utils/hooks/sessionHooks.ts
export type FunctionHook = {
  type: 'function'
  id?: string
  timeout?: number
  callback: FunctionHookCallback  // (messages, signal?) => boolean
  errorMessage: string
  statusMessage?: string
}
```

当 callback 返回 `false`，hook 产生阻塞错误（blockingError），使用 `errorMessage` 作为反馈。

---

## 4. Hook 执行模型

### 4.1 核心执行引擎

所有 Hook 的执行最终汇聚到两个内部函数：

- **`executeHooks()`** — REPL 内执行，返回 `AsyncGenerator<AggregatedHookResult>`，结果以消息形式注入模型上下文
- **`executeHooksOutsideREPL()`** — REPL 外执行（通知、会话结束等），返回 `Promise<HookOutsideReplResult[]>`

```typescript
// executeHooks 的简化调用链
async function* executeHooks({ hookInput, toolUseID, ... }) {
  // 1. 安全检查
  if (shouldDisableAllHooksIncludingManaged()) return
  if (shouldSkipHookDueToTrust()) return

  // 2. 匹配 hooks
  const matchingHooks = await getMatchingHooks(appState, sessionId, hookEvent, hookInput)

  // 3. 快速路径：全是内部 callback，跳过重量级基础设施
  if (allInternalCallbacks) {
    for (const hook of matchingHooks) await hook.callback(...)
    return
  }

  // 4. 并行执行所有 hooks
  for await (const result of all(hookPromises)) {
    // 5. 聚合结果：权限决策优先级 deny > ask > allow
    // 6. yield 各种结果（message, blockingError, additionalContext, updatedInput...）
  }
}
```

### 4.2 超时机制

每个 Hook 有独立的超时控制：

```typescript
const TOOL_HOOK_EXECUTION_TIMEOUT_MS = 10 * 60 * 1000  // 默认 10 分钟

// 每个 hook 可以通过 timeout 字段覆盖（单位：秒）
const hookTimeoutMs = hook.timeout ? hook.timeout * 1000 : TOOL_HOOK_EXECUTION_TIMEOUT_MS
```

超时通过 `createCombinedAbortSignal()` 实现——它将父 AbortSignal（取消请求时触发）和超时信号合并为一个组合信号。

特殊超时：
- SessionEnd hooks: 默认 1.5 秒（`SESSION_END_HOOK_TIMEOUT_MS_DEFAULT`）
- StatusLine hooks: 5 秒
- Prompt hooks: 30 秒

### 4.3 环境变量传递

Command Hook 执行时，系统注入丰富的环境变量：

```typescript
// src/utils/hooks.ts - execCommandHook
const envVars = {
  ...subprocessEnv(),                        // 基础环境
  CLAUDE_PROJECT_DIR: toHookPath(projectDir), // 项目根目录
  CLAUDE_PLUGIN_ROOT: pluginRoot,             // 插件根目录（如有）
  CLAUDE_PLUGIN_DATA: pluginDataDir,          // 插件数据目录（如有）
  CLAUDE_PLUGIN_OPTION_*: pluginOptions,      // 插件配置选项
  CLAUDE_ENV_FILE: envFilePath,               // 环境文件路径（SessionStart/Setup/CwdChanged/FileChanged）
}
```

Hook 的输入通过 **stdin** 传递（JSON 格式），而非命令行参数。每个输入都包含通用字段：

```typescript
// createBaseHookInput 生成的基础输入
{
  session_id: string,
  transcript_path: string,  // 当前会话的 transcript 文件路径
  cwd: string,              // 当前工作目录
  permission_mode?: string, // 权限模式
  agent_id?: string,        // 子 agent ID（如有）
  agent_type?: string,      // agent 类型
}
```

### 4.4 JSON 输出 Schema

Hook 的 stdout 输出如果以 `{` 开头，系统会尝试按 `hookJSONOutputSchema` 验证。该 schema 定义了两种响应格式：

**异步响应**（使 Hook 进入后台执行）：
```json
{"async": true, "asyncTimeout": 15000}
```

**同步响应**（立即返回结果）：
```typescript
// src/types/hooks.ts - syncHookResponseSchema
{
  continue?: boolean,       // false 时阻止模型继续
  suppressOutput?: boolean, // 隐藏 stdout
  stopReason?: string,      // continue=false 时的停止原因
  decision?: "approve" | "block",  // 顶层权限决策
  reason?: string,          // 决策原因
  systemMessage?: string,   // 显示给用户的警告消息
  hookSpecificOutput?: {    // 事件特定输出
    hookEventName: "PreToolUse" | "PostToolUse" | "UserPromptSubmit" | ...
    // 不同事件有不同的额外字段
    permissionDecision?: "allow" | "deny" | "ask",  // PreToolUse
    updatedInput?: Record<string, unknown>,           // PreToolUse
    additionalContext?: string,                       // 多种事件
    updatedMCPToolOutput?: unknown,                   // PostToolUse
    retry?: boolean,                                  // PermissionDenied
    // ...更多
  }
}
```

验证失败时，系统会生成详细的错误消息，包含期望的 schema 结构，帮助 Hook 开发者调试。

### 4.5 错误处理

Hook 的错误处理遵循**容错优先**原则：

1. **Exit code 0** — 成功，stdout 作为内容显示
2. **Exit code 2** — 阻塞错误（blocking error），stderr 作为反馈注入模型上下文
3. **其他非零** — 非阻塞错误（non-blocking error），仅记录日志，不影响流程
4. **JSON 验证失败** — 非阻塞错误，返回完整的验证错误和期望 schema
5. **EPIPE** — stdin 写入失败（Hook 进程提前退出），记录日志并继续
6. **超时/取消** — 生成 `hook_cancelled` 消息

```typescript
// 核心错误处理逻辑（简化）
if (result.status === 0) {
  // 成功
} else if (result.status === 2) {
  // 阻塞错误 — 反馈给模型
  yield { blockingError: { blockingError: stderr, command } }
} else {
  // 非阻塞错误 — 仅记录
  yield { message: createAttachmentMessage({ type: 'hook_non_blocking_error', ... }) }
}
```

---

## 5. Hook 与权限系统的交互

### 5.1 关键不变量：Hook allow 不绕过 deny 规则

这是 Hooks 系统最重要的安全设计之一。即使 PreToolUse Hook 返回 `permissionDecision: "allow"`，`settings.json` 中的 deny 规则仍然生效。这个不变量在 `resolveHookPermissionDecision()` 函数中实现：

```typescript
// src/services/tools/toolHooks.ts
export async function resolveHookPermissionDecision(
  hookPermissionResult, tool, input, toolUseContext, canUseTool, assistantMessage, toolUseID
) {
  if (hookPermissionResult?.behavior === 'allow') {
    const hookInput = hookPermissionResult.updatedInput ?? input

    // Hook allow 跳过交互式提示，但 deny/ask 规则仍然适用
    const ruleCheck = await checkRuleBasedPermissions(tool, hookInput, toolUseContext)

    if (ruleCheck === null) {
      // 没有匹配的规则 → Hook 的 allow 生效
      return { decision: hookPermissionResult, input: hookInput }
    }
    if (ruleCheck.behavior === 'deny') {
      // deny 规则覆盖 Hook 的 allow！
      logForDebugging(`Hook approved but deny rule overrides: ${ruleCheck.message}`)
      return { decision: ruleCheck, input: hookInput }
    }
    if (ruleCheck.behavior === 'ask') {
      // ask 规则要求用户确认，即使 Hook 已 approve
      return { decision: await canUseTool(...), input: hookInput }
    }
  }

  if (hookPermissionResult?.behavior === 'deny') {
    return { decision: hookPermissionResult, input }
  }

  // 无 Hook 决策或 'ask' → 正常权限流程
  return { decision: await canUseTool(...), input }
}
```

### 5.2 权限决策的优先级

当多个 Hook 并行返回不同的权限决策时，聚合逻辑遵循严格的优先级：

```typescript
// src/utils/hooks.ts - executeHooks 内部
// deny > ask > allow > passthrough
switch (result.permissionBehavior) {
  case 'deny':
    permissionBehavior = 'deny'      // deny 永远优先
    break
  case 'ask':
    if (permissionBehavior !== 'deny')
      permissionBehavior = 'ask'     // ask 仅当没有 deny 时生效
    break
  case 'allow':
    if (!permissionBehavior)
      permissionBehavior = 'allow'   // allow 仅当没有其他决策时生效
    break
  case 'passthrough':
    break                            // passthrough 不设置任何决策
}
```

### 5.3 PermissionRequest Hook

这是实现**无人值守自动化**的关键 Hook。当系统即将弹出权限对话框时，PermissionRequest Hook 被触发。它可以：

- 返回 `behavior: "allow"` 自动批准（可携带 `updatedInput` 和 `updatedPermissions`）
- 返回 `behavior: "deny"` 自动拒绝
- 不返回决策，让对话框正常弹出

这使得 CI/CD 环境和 headless 模式可以完全自动化权限管理。

---

## 6. Pre/Post Tool Hook 详解

### 6.1 PreToolUse Hook

PreToolUse 是最功能丰富的 Hook 事件，通过 `runPreToolUseHooks()` 在 `toolHooks.ts` 中编排：

```typescript
// src/services/tools/toolHooks.ts
export async function* runPreToolUseHooks(toolUseContext, tool, processedInput, ...) {
  for await (const result of executePreToolHooks(tool.name, toolUseID, processedInput, ...)) {
    // 处理各种结果类型
    if (result.blockingError) {
      // → 生成 deny 权限决策
      yield { type: 'hookPermissionResult', hookPermissionResult: { behavior: 'deny', message } }
    }
    if (result.permissionBehavior !== undefined) {
      // → 传递权限决策（allow/deny/ask）
      yield { type: 'hookPermissionResult', hookPermissionResult: { behavior, updatedInput } }
    }
    if (result.updatedInput && result.permissionBehavior === undefined) {
      // → 仅修改输入，不影响权限（passthrough 模式）
      yield { type: 'hookUpdatedInput', updatedInput: result.updatedInput }
    }
    if (result.additionalContexts) {
      // → 注入额外上下文供模型参考
      yield { type: 'additionalContext', message: ... }
    }
    if (result.preventContinuation) {
      // → 阻止模型后续响应
      yield { type: 'preventContinuation', shouldPreventContinuation: true }
    }
  }
}
```

**输入转换**能力：Hook 可以通过 `updatedInput` 修改工具输入。例如，一个 PreToolUse Hook 可以自动为 Bash 命令添加 `--dry-run` 标志。

### 6.2 PostToolUse Hook

PostToolUse Hook 在工具成功执行后触发，核心编排在 `runPostToolUseHooks()`：

```typescript
// src/services/tools/toolHooks.ts
export async function* runPostToolUseHooks(toolUseContext, tool, ..., toolResponse) {
  let toolOutput = toolResponse
  for await (const result of executePostToolHooks(tool.name, ..., toolOutput, ...)) {
    // 阻塞错误
    if (result.blockingError) {
      yield { message: createAttachmentMessage({ type: 'hook_blocking_error', ... }) }
    }
    // 阻止后续继续
    if (result.preventContinuation) {
      yield { message: createAttachmentMessage({ type: 'hook_stopped_continuation', ... }) }
      return  // 立即终止
    }
    // 附加上下文
    if (result.additionalContexts) {
      yield { message: createAttachmentMessage({ type: 'hook_additional_context', ... }) }
    }
    // MCP 工具输出替换（仅对 MCP 工具有效）
    if (result.updatedMCPToolOutput && isMcpTool(tool)) {
      toolOutput = result.updatedMCPToolOutput
      yield { updatedMCPToolOutput: toolOutput }
    }
  }
}
```

**输出转换**能力：`updatedMCPToolOutput` 允许 Hook 完全替换 MCP 工具的输出。这对数据脱敏、输出过滤等场景非常有用。

### 6.3 PostToolUseFailure Hook

当工具调用失败时触发，结构与 PostToolUse 类似但不支持输出替换（因为没有成功的输出）。额外输入包含 `error` 字符串和 `is_interrupt` 标志。

---

## 7. asyncRewake Hook

asyncRewake 是一种特殊的异步 Hook 模式，它允许 Hook 在后台运行，**完成后唤醒模型**。这与普通异步 Hook（仅后台静默执行）有本质区别。

```typescript
// src/utils/hooks.ts - executeInBackground
if (asyncRewake) {
  // asyncRewake hooks 绕过注册表。完成后：
  // - 如果 exit code 2（阻塞错误），将消息作为 task-notification 入队
  // - useQueueProcessor（空闲时）或 queued_command attachments（忙碌时）
  //   会将该消息注入模型上下文，从而"唤醒"模型
  void shellCommand.result.then(async result => {
    await new Promise(resolve => setImmediate(resolve))  // 等待 I/O 排空
    const stdout = await shellCommand.taskOutput.getStdout()
    const stderr = shellCommand.taskOutput.getStderr()

    if (result.code === 2) {
      enqueuePendingNotification({
        value: wrapInSystemReminder(
          `Stop hook blocking error from command "${hookName}": ${stderr || stdout}`,
        ),
        mode: 'task-notification',  // 唤醒模型
      })
    }
  })
  return true
}
```

配置方式：

```json
{
  "hooks": {
    "Stop": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "python3 /path/to/long-running-check.py",
        "asyncRewake": true
      }]
    }]
  }
}
```

典型用例：Stop Hook 启动一个耗时的测试验证脚本。脚本在后台运行，如果发现问题（exit code 2），其反馈会被注入模型上下文，模型被"唤醒"继续修复问题。

**关键设计决策**：asyncRewake hooks 不调用 `shellCommand.background()`——这会导致 `spillToDisk()` 破坏内存中的 stdout/stderr 捕获。StreamWrappers 保持挂载状态，将数据管道到内存 TaskOutput 缓冲区中。

---

## 8. UserPromptSubmit Hook

UserPromptSubmit 在用户提交 prompt 后、发送给模型**前**触发，是拦截和增强用户输入的关键扩展点。

### 8.1 执行流程

```typescript
// src/utils/hooks.ts
export async function* executeUserPromptSubmitHooks(
  prompt: string,
  permissionMode: string,
  toolUseContext: ToolUseContext,
) {
  const hookInput: UserPromptSubmitHookInput = {
    ...createBaseHookInput(permissionMode),
    hook_event_name: 'UserPromptSubmit',
    prompt,  // 用户的原始 prompt
  }
  yield* executeHooks({ hookInput, toolUseID: randomUUID(), ... })
}
```

### 8.2 能力

1. **注入上下文**：Hook 通过 `hookSpecificOutput.additionalContext` 返回额外上下文，作为 system message 附加到对话中
2. **阻塞提交**：Exit code 2 阻止 prompt 发送给模型
3. **停止继续**：`continue: false` 配合 `stopReason` 可以中止响应

### 8.3 用例

```bash
#!/bin/bash
# 读取 stdin 中的 JSON 输入
read -r input
prompt=$(echo "$input" | jq -r '.prompt')

# 自动检测并注入项目上下文
if echo "$prompt" | grep -q "deployment"; then
  echo '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"当前部署环境: staging, 最近一次部署: 2024-01-15"}}'
fi
```

---

## 9. Hook 信任检查

Hooks 执行任意 shell 命令，因此安全性至关重要。系统通过多层机制确保安全：

### 9.1 工作区信任检查

所有 Hook 都需要工作区信任（trust dialog accepted）。这在 `shouldSkipHookDueToTrust()` 中集中检查：

```typescript
// src/utils/hooks.ts
export function shouldSkipHookDueToTrust(): boolean {
  // SDK（非交互模式）隐式信任
  const isInteractive = !getIsNonInteractiveSession()
  if (!isInteractive) return false

  // 交互模式下，所有 Hook 必须通过信任检查
  const hasTrust = checkHasTrustDialogAccepted()
  return !hasTrust
}
```

历史漏洞（促成此设计）：
- SessionEnd hooks 在用户拒绝信任对话框时仍然执行
- SubagentStop hooks 在子 agent 完成后、信任建立前执行

### 9.2 Managed Hooks 策略

企业管理员可以通过 `policySettings` 控制 Hook 行为：

```typescript
// src/utils/hooks/hooksConfigSnapshot.ts
function getHooksFromAllowedSources(): HooksSettings {
  const policySettings = getSettingsForSource('policySettings')

  // 管理员可以禁用所有 Hook（包括自己的）
  if (policySettings?.disableAllHooks === true) return {}

  // 管理员可以仅允许自己管理的 Hook
  if (policySettings?.allowManagedHooksOnly === true) {
    return policySettings.hooks ?? {}
  }

  // strictPluginOnlyCustomization: 阻止用户/项目/本地 settings 的 hooks
  if (isRestrictedToPluginOnly('hooks')) {
    return policySettings?.hooks ?? {}
  }

  // 默认：合并所有来源
  return mergedSettings.hooks ?? {}
}
```

### 9.3 CLAUDE_CODE_SIMPLE 模式

设置 `CLAUDE_CODE_SIMPLE=true` 环境变量会完全禁用所有 Hooks，这是一个"极简模式"安全逃生门。

### 9.4 Snapshot 冻结

Hooks 配置在会话启动时通过 `captureHooksConfigSnapshot()` 冻结。会话期间配置文件的变更不会影响已加载的 Hook 定义，防止运行时注入攻击。

---

## 10. 设计模式总结

### 10.1 AsyncGenerator 流式结果

核心执行函数使用 `AsyncGenerator<AggregatedHookResult>` 模式，允许调用者逐个处理 Hook 结果，而非等待所有 Hook 完成。这在多个 Hook 并行运行时特别重要——一个 Hook 的阻塞决策可以立即生效，无需等待其他 Hook。

### 10.2 并行执行 + 优先级聚合

所有匹配的 Hooks 并行执行（`Promise.all` + `all()` 流式合并），但权限决策按 **deny > ask > allow** 优先级聚合。这确保了安全性（deny 不会被 allow 覆盖）和性能（不需要串行执行）。

### 10.3 双路径执行

REPL 内（`executeHooks`）和 REPL 外（`executeHooksOutsideREPL`）使用不同的执行路径。前者通过 AsyncGenerator yield 消息到模型上下文，后者返回简单的结果数组。两者共享匹配和执行逻辑，但结果处理方式完全不同。

### 10.4 Dedup 与 If 条件

Hook 配置可能来自多个 settings 源（user、project、local、policy），系统通过 `hookDedupKey()` 去重——同源下相同命令只执行一次。`if` 条件允许精细过滤：

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash",
      "hooks": [{
        "type": "command",
        "command": "check-git.sh",
        "if": "Bash(git *)"
      }]
    }]
  }
}
```

`if` 条件通过 `prepareIfConditionMatcher` 解析，利用工具的 `preparePermissionMatcher` 进行语义匹配（如 Bash 工具的命令模式匹配），避免为不匹配的调用启动 Hook 进程。

### 10.5 快速路径优化

当所有匹配的 Hooks 都是 internal callback 时（常见于文件访问跟踪、归因等），系统跳过重量级基础设施（span 追踪、进度消息、abort 信号等），直接同步调用 callback。测量显示延迟从 6.01 微秒降至约 1.8 微秒（-70%）。

### 10.6 Prompt 请求协议

Command Hooks 支持**双向通信**：Hook 进程可以通过 stdout 输出 `promptRequestSchema` 格式的 JSON 行来向用户提问，系统通过 stdin 返回用户选择。这使得交互式 Hook 成为可能，同时保持了进程模型的简洁性。

```typescript
// Hook 进程 stdout 输出
{"prompt": "req-1", "message": "选择操作", "options": [{"key": "y", "label": "允许"}]}
// 系统通过 stdin 回传
{"prompt_response": "req-1", "selected": "y"}
```

### 10.7 防御性编程

整个 Hooks 系统充满防御性编程实践：
- 每个外部调用都有超时保护
- Windows 路径自动转换为 POSIX 格式（Git Bash 兼容）
- 失去的 cwd（worktree 删除后）回退到 originalCwd
- EPIPE 错误被优雅处理（Hook 进程提前退出）
- 缺失的插件目录在 spawn 前检测（而非让 exit code 2 误报阻塞）

---

*本文基于 Claude Code 源码 `src/utils/hooks.ts`（~5000 行）及相关文件分析。Hooks 系统是 Claude Code 可扩展性的核心支柱，理解它对于开发插件、自动化工作流和企业级定制至关重要。*
