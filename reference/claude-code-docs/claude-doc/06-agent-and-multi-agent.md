# 第 6 篇：Agent 工具与多代理系统

## 目录

1. [概述：多代理系统在 Claude Code 中的地位](#1-概述)
2. [AgentTool 完整设计](#2-agenttool-完整设计)
3. [5 种子代理执行模式详解](#3-5-种子代理执行模式详解)
4. [子代理上下文传播](#4-子代理上下文传播)
5. [Task 系统完整解析](#5-task-系统完整解析)
6. [各 Task 实现详解](#6-各-task-实现详解)
7. [Coordinator 模式](#7-coordinator-模式)
8. [SendMessage 工具：代理间通信](#8-sendmessage-工具代理间通信)
9. [Multi-Agent Swarm](#9-multi-agent-swarm)
10. [设计模式总结](#10-设计模式总结)

---

## 1. 概述

Claude Code 的多代理系统是整个架构中最复杂、也最具创新性的子系统。它允许一个主代理（"协调者"或"父代理"）将复杂任务分解后委托给多个子代理并行或串行执行，从而大幅提升开发效率。

从架构上看，多代理系统横跨以下几个层次：

```
┌───────────────────────────────────────────────────┐
│                   用户交互层                        │
│  REPL / SDK / Headless Entrypoint                 │
├───────────────────────────────────────────────────┤
│                 Coordinator 模式                    │
│  coordinatorMode.ts — 系统提示覆盖、工具限制        │
├───────────────────────────────────────────────────┤
│                  AgentTool 层                       │
│  AgentTool.tsx — 统一入口，5 种执行分支             │
├───────────────────────────────────────────────────┤
│                  Task 注册层                        │
│  Task.ts / tasks.ts — 任务状态机、ID 生成           │
├──────────┬──────────┬──────────┬─────────────────┤
│ Local    │ Local    │ Remote   │ InProcess       │
│ Shell    │ Agent    │ Agent    │ Teammate        │
│ Task     │ Task     │ Task     │ Task            │
├──────────┴──────────┴──────────┴─────────────────┤
│               Swarm 协调层                         │
│  tmux/iTerm2/InProcess Backend + Mailbox 通信      │
└───────────────────────────────────────────────────┘
```

多代理系统的核心设计目标包括：

- **prompt cache 共享**：Fork 子代理继承父代理完整上下文，API 请求前缀保持字节一致，最大化缓存命中率
- **权限隔离**：子代理可以有独立的权限模式（plan/bubble/acceptEdits），不会污染父代理的权限状态
- **生命周期管理**：每个子代理对应一个 TaskState，支持 pending/running/completed/failed/killed 状态流转
- **灵活通信**：通过 SendMessage 工具和 mailbox 文件系统实现代理间消息传递

---

## 2. AgentTool 完整设计

AgentTool 是整个多代理系统的统一入口点。无论是同步子代理、异步后台代理、worktree 隔离代理、远程代理，还是 teammate 多代理集群，都通过这个单一工具触发。

### 2.1 工具注册与元信息

AgentTool 在 `src/tools/AgentTool/AgentTool.tsx` 中通过 `buildTool()` 注册：

```typescript
// src/tools/AgentTool/constants.ts
export const AGENT_TOOL_NAME = 'Agent'
// 向后兼容的旧名称（权限规则、hooks、恢复会话用到）
export const LEGACY_AGENT_TOOL_NAME = 'Task'

// 一次性执行的内置代理 — 父代理不会通过 SendMessage 继续它们
// 跳过 agentId/SendMessage/usage 尾部以节省 token
export const ONE_SHOT_BUILTIN_AGENT_TYPES: ReadonlySet<string> = new Set([
  'Explore',
  'Plan',
])
```

工具名称为 `Agent`，别名为 `Task`（历史兼容）。这意味着模型可以使用 `Agent(...)` 或 `Task(...)` 来调用。

### 2.2 Input Schema 详解

输入 schema 采用分层构建策略，根据 feature flag 动态组装：

```typescript
// 基础输入 schema — 所有模式共享
const baseInputSchema = lazySchema(() => z.object({
  description: z.string().describe('任务的简短描述（3-5 个词）'),
  prompt: z.string().describe('代理要执行的任务'),
  subagent_type: z.string().optional().describe('专用代理类型'),
  model: z.enum(['sonnet', 'opus', 'haiku']).optional()
    .describe('可选模型覆盖'),
  run_in_background: z.boolean().optional()
    .describe('是否在后台运行')
}));

// 完整 schema = 基础 + 多代理参数 + 隔离模式
const fullInputSchema = lazySchema(() => {
  const multiAgentInputSchema = z.object({
    name: z.string().optional()
      .describe('为代理命名，使其可通过 SendMessage 寻址'),
    team_name: z.string().optional()
      .describe('团队名称'),
    mode: permissionModeSchema().optional()
      .describe('权限模式（如 "plan"）')
  });
  return baseInputSchema().merge(multiAgentInputSchema).extend({
    isolation: z.enum(['worktree']).optional()
      .describe('隔离模式：worktree 创建独立 git 工作树'),
    cwd: z.string().optional()
      .describe('工作目录覆盖')
  });
});
```

关键设计点：

1. **`lazySchema()`** — 延迟求值避免模块初始化时循环依赖
2. **条件性 `.omit()`** — 当 feature flag 关闭时，从 schema 中移除不需要的字段，确保模型看不到未启用的功能：

```typescript
export const inputSchema = lazySchema(() => {
  const schema = feature('KAIROS')
    ? fullInputSchema()
    : fullInputSchema().omit({ cwd: true });
  // Fork 模式启用时移除 run_in_background（所有 spawn 强制异步）
  return isForkSubagentEnabled()
    ? schema.omit({ run_in_background: true })
    : schema;
});
```

### 2.3 Output Schema

输出是一个判别联合类型，根据执行模式返回不同结构：

```typescript
export const outputSchema = lazySchema(() => {
  // 同步完成
  const syncOutputSchema = agentToolResultSchema().extend({
    status: z.literal('completed'),
    prompt: z.string()
  });
  // 异步启动
  const asyncOutputSchema = z.object({
    status: z.literal('async_launched'),
    agentId: z.string(),
    description: z.string(),
    prompt: z.string(),
    outputFile: z.string(),  // 磁盘输出文件路径，用于检查进度
    canReadOutputFile: z.boolean().optional()
  });
  return z.union([syncOutputSchema, asyncOutputSchema]);
});
```

此外还有两种内部类型（不暴露给 schema，以实现 dead code elimination）：

- **`TeammateSpawnedOutput`** — teammate 模式返回 tmux pane 信息
- **`RemoteLaunchedOutput`** — 远程代理返回 session URL

### 2.4 权限检查与代理过滤

在 `prompt()` 阶段（构建工具描述时），系统执行两层过滤：

```typescript
async prompt({ agents, tools, getToolPermissionContext, allowedAgentTypes }) {
  // 第一层：过滤掉缺少必需 MCP 服务器的代理
  const agentsWithMcpRequirementsMet =
    filterAgentsByMcpRequirements(agents, mcpServersWithTools);
  // 第二层：过滤掉被权限规则拒绝的代理
  const filteredAgents = filterDeniedAgents(
    agentsWithMcpRequirementsMet,
    toolPermissionContext,
    AGENT_TOOL_NAME
  );
  return await getPrompt(filteredAgents, isCoordinator, allowedAgentTypes);
}
```

权限规则支持 `Agent(AgentName)` 语法来控制哪些代理可以被调用。

### 2.5 call() 方法的执行分支

`call()` 方法是 AgentTool 的核心，包含以下决策树：

```
call() 入口
  │
  ├─ teamName && name? ──→ spawnTeammate() ──→ 返回 teammate_spawned
  │
  ├─ 确定 effectiveType:
  │   ├─ subagent_type 已指定 ──→ 使用该类型
  │   ├─ subagent_type 未指定 + fork 启用 ──→ undefined（fork 路径）
  │   └─ subagent_type 未指定 + fork 未启用 ──→ 默认 general-purpose
  │
  ├─ effectiveType === undefined? ──→ isForkPath = true
  │   ├─ 递归 fork 检测（防止 fork 子代理再次 fork）
  │   └─ selectedAgent = FORK_AGENT
  │
  ├─ isolation === 'remote'? ──→ teleportToRemote() ──→ 返回 remote_launched
  │
  ├─ isolation === 'worktree'? ──→ createAgentWorktree()
  │
  ├─ 构建 systemPrompt + promptMessages
  │   ├─ fork 路径：继承父代理的 system prompt + buildForkedMessages()
  │   └─ 普通路径：agent.getSystemPrompt() + createUserMessage(prompt)
  │
  ├─ shouldRunAsync? ──→ registerAsyncAgent() + runAsyncAgentLifecycle()
  │   └─ 返回 async_launched
  │
  └─ 同步路径 ──→ registerAgentForeground() + runAgent() 迭代
      ├─ 可中途 backgrounded ──→ 转入异步生命周期
      └─ 返回 completed + result
```

---

## 3. 5 种子代理执行模式详解

### 3.1 Sync（同步前台模式）

这是最基本的执行模式。父代理的 `call()` 方法阻塞等待子代理执行完毕。

```typescript
// AgentTool.tsx — 同步执行路径
const agentIterator = runAgent({
  ...runAgentParams,
  override: { ...runAgentParams.override, agentId: syncAgentId }
})[Symbol.asyncIterator]();

while (true) {
  const nextMessagePromise = agentIterator.next();
  // 竞争模式：消息 vs 后台化信号
  const raceResult = backgroundPromise
    ? await Promise.race([
        nextMessagePromise.then(r => ({ type: 'message', result: r })),
        backgroundPromise  // 用户按 Shift+Down 后台化
      ])
    : { type: 'message', result: await nextMessagePromise };

  if (raceResult.type === 'background') {
    // 中途转为后台运行 — 见下文
    wasBackgrounded = true;
    break;
  }

  const { value: msg, done } = raceResult.result;
  if (done) break;

  agentMessages.push(msg);
  // 更新进度跟踪...
}
```

核心特点：
- 父代理的 turn 被阻塞，直到子代理完成
- 使用 `Promise.race()` 在每次消息迭代时检查后台化信号
- 超过 2 秒后显示 `BackgroundHint` UI 组件
- AbortController 与父代理共享（用户按 ESC 时同时取消）

### 3.2 Async（异步后台模式）

当 `run_in_background: true`、agent 定义中 `background: true`、coordinator 模式、fork 模式、或 assistant 模式时触发：

```typescript
// AgentTool.tsx — 异步路径
const shouldRunAsync =
  (run_in_background === true ||
   selectedAgent.background === true ||
   isCoordinator ||
   forceAsync ||
   assistantForceAsync) &&
  !isBackgroundTasksDisabled;

if (shouldRunAsync) {
  // 注册异步代理任务
  const agentBackgroundTask = registerAsyncAgent({
    agentId: asyncAgentId,
    description,
    prompt,
    selectedAgent,
    setAppState: rootSetAppState,
    // 关键：不连接父代理的 AbortController
    // 后台代理在用户按 ESC 时继续运行
    toolUseId: toolUseContext.toolUseId
  });

  // 注册名称 → agentId 映射，供 SendMessage 路由
  if (name) {
    rootSetAppState(prev => {
      const next = new Map(prev.agentNameRegistry);
      next.set(name, asAgentId(asyncAgentId));
      return { ...prev, agentNameRegistry: next };
    });
  }

  // 在后台启动代理生命周期（fire-and-forget）
  void runWithAgentContext(asyncAgentContext, () =>
    wrapWithCwd(() =>
      runAsyncAgentLifecycle({
        taskId: agentBackgroundTask.agentId,
        abortController: agentBackgroundTask.abortController!,
        makeStream: onCacheSafeParams => runAgent({
          ...runAgentParams,
          override: {
            ...runAgentParams.override,
            agentId: asAgentId(agentBackgroundTask.agentId),
            abortController: agentBackgroundTask.abortController!
          },
          onCacheSafeParams
        }),
        // ...
      })
    )
  );

  // 立即返回 — 不阻塞父代理
  return {
    data: {
      status: 'async_launched',
      agentId: agentBackgroundTask.agentId,
      description,
      prompt,
      outputFile: getTaskOutputPath(agentBackgroundTask.agentId),
      canReadOutputFile
    }
  };
}
```

核心特点：
- 父代理立即得到返回值并继续
- 子代理有**独立的 AbortController**，不受父代理 ESC 影响
- 完成时通过 `<task-notification>` XML 通知父代理
- 支持名称注册，可通过 SendMessage 后续交互

### 3.3 Worktree（Git 工作树隔离模式）

当 `isolation: "worktree"` 时，子代理在独立的 git worktree 中执行：

```typescript
// AgentTool.tsx — worktree 创建
if (effectiveIsolation === 'worktree') {
  const slug = `agent-${earlyAgentId.slice(0, 8)}`;
  worktreeInfo = await createAgentWorktree(slug);
}

// Fork + worktree 时注入路径提示
if (isForkPath && worktreeInfo) {
  promptMessages.push(createUserMessage({
    content: buildWorktreeNotice(getCwd(), worktreeInfo.worktreePath)
  }));
}
```

worktree 通知告诉子代理翻译路径：

```typescript
// forkSubagent.ts
export function buildWorktreeNotice(
  parentCwd: string,
  worktreeCwd: string
): string {
  return `You've inherited the conversation context above from a parent agent
working in ${parentCwd}. You are operating in an isolated git worktree at
${worktreeCwd} — same repository, same relative file structure, separate
working copy. Paths in the inherited context refer to the parent's working
directory; translate them to your worktree root. Re-read files before editing
if the parent may have modified them since they appear in the context.
Your changes stay in this worktree and will not affect the parent's files.`
}
```

清理逻辑在代理完成后执行：

```typescript
const cleanupWorktreeIfNeeded = async () => {
  if (!worktreeInfo) return {};
  const { worktreePath, worktreeBranch, headCommit, gitRoot } = worktreeInfo;
  if (headCommit) {
    const changed = await hasWorktreeChanges(worktreePath, headCommit);
    if (!changed) {
      // 没有变更 — 清理 worktree
      await removeAgentWorktree(worktreePath, worktreeBranch, gitRoot);
      return {};
    }
  }
  // 有变更 — 保留 worktree 并返回路径
  return { worktreePath, worktreeBranch };
};
```

### 3.4 Remote（远程 CCR 环境模式）

仅对 Anthropic 内部用户（`ant` 类型）启用，代理在远程 Cloud Code Runner 环境中执行：

```typescript
// AgentTool.tsx — 远程隔离路径（仅 ant 用户）
if ("external" === 'ant' && effectiveIsolation === 'remote') {
  const eligibility = await checkRemoteAgentEligibility();
  if (!eligibility.eligible) {
    const reasons = eligibility.errors
      .map(formatPreconditionError).join('\n');
    throw new Error(`Cannot launch remote agent:\n${reasons}`);
  }

  // 通过 teleport 创建远程会话
  const session = await teleportToRemote({
    initialMessage: prompt,
    description,
    signal: toolUseContext.abortController.signal,
  });

  // 注册远程任务并开始轮询
  const { taskId, sessionId } = registerRemoteAgentTask({
    remoteTaskType: 'remote-agent',
    session: { id: session.id, title: session.title || description },
    command: prompt,
    context: toolUseContext,
    toolUseId: toolUseContext.toolUseId
  });

  return {
    data: {
      status: 'remote_launched',
      taskId,
      sessionUrl: getRemoteTaskSessionUrl(sessionId),
      description,
      prompt,
      outputFile: getTaskOutputPath(taskId)
    }
  };
}
```

远程代理的前置检查包括：登录状态、远程环境可用性、git 仓库、GitHub remote、GitHub App 安装状态、组织策略。

### 3.5 Teammate（队友模式 / Swarm 模式）

当同时提供 `team_name` 和 `name` 参数时触发 teammate 路径。Teammate 是完全独立的 Claude Code 实例，通过 tmux pane 或进程内方式运行：

```typescript
// AgentTool.tsx — teammate 路径
if (teamName && name) {
  const result = await spawnTeammate({
    name,
    prompt,
    description,
    team_name: teamName,
    use_splitpane: true,
    plan_mode_required: spawnMode === 'plan',
    model: model ?? agentDef?.model,
    agent_type: subagent_type,
    invokingRequestId: assistantMessage?.requestId
  }, toolUseContext);

  return {
    data: {
      status: 'teammate_spawned',
      prompt,
      ...result.data
    }
  };
}
```

Teammate 与子代理的核心区别：
- Teammate 是**完整的 Claude Code 实例**，有自己的 REPL 循环
- 通过 **mailbox 文件系统**进行通信，不是函数调用
- 支持 **tmux/iTerm2 pane** 可视化（用户可以看到每个 teammate 的终端）
- Teammate 不能嵌套生成其他 teammate（team roster 是扁平的）

---

## 4. 子代理上下文传播

### 4.1 createSubagentContext

`runAgent()` 中创建子代理上下文是最关键的步骤之一。它决定了子代理能看到什么、能做什么、以及如何与父代理通信。

核心在 `src/utils/forkedAgent.ts` 中的 `createSubagentContext()`：

```typescript
export type CacheSafeParams = {
  systemPrompt: SystemPrompt       // 系统提示 — 必须匹配父代理以获得缓存命中
  userContext: { [k: string]: string }   // 用户上下文
  systemContext: { [k: string]: string } // 系统上下文
  toolUseContext: ToolUseContext    // 包含 tools、model 和其他选项
  forkContextMessages: Message[]   // 父上下文消息，用于缓存共享
};
```

`CacheSafeParams` 的设计理念是确保 fork 子代理与父代理的 API 请求前缀**字节一致**，从而共享 Anthropic API 的 prompt cache。缓存键由以下部分组成：system prompt、tools、model、messages（前缀）、thinking config。

### 4.2 agentId 生成与追踪

每个子代理都有一个唯一的 `agentId`，在 `runAgent()` 中生成：

```typescript
// runAgent.ts
const agentId = override?.agentId
  ? override.agentId
  : createAgentId();

// Perfetto 追踪（性能分析）
if (isPerfettoTracingEnabled()) {
  const parentId = toolUseContext.agentId ?? getSessionId();
  registerPerfettoAgent(agentId, agentDefinition.agentType, parentId);
}
```

`agentId` 用于：
- 日志和分析的父子关系追踪
- Perfetto 性能追踪的层级可视化
- 磁盘上的 transcript 子目录命名
- `agentNameRegistry` 中的名称解析

### 4.3 权限模式隔离

子代理的权限模式通过 `agentGetAppState()` 闭包进行隔离：

```typescript
// runAgent.ts — 权限模式覆盖
const agentGetAppState = () => {
  const state = toolUseContext.getAppState();
  let toolPermissionContext = state.toolPermissionContext;

  // 代理定义的权限模式覆盖（除非父代理是 bypassPermissions 或 acceptEdits）
  if (agentPermissionMode &&
      state.toolPermissionContext.mode !== 'bypassPermissions' &&
      state.toolPermissionContext.mode !== 'acceptEdits') {
    toolPermissionContext = {
      ...toolPermissionContext,
      mode: agentPermissionMode,
    };
  }

  // 异步代理无法显示权限弹窗 — 自动拒绝
  if (shouldAvoidPrompts) {
    toolPermissionContext = {
      ...toolPermissionContext,
      shouldAvoidPermissionPrompts: true,
    };
  }

  // 作用域工具权限：当 allowedTools 提供时，替换所有 session 级别规则
  // 关键：保留 cliArg 规则（来自 SDK 的 --allowedTools），只清除 session 级别
  if (allowedTools !== undefined) {
    toolPermissionContext = {
      ...toolPermissionContext,
      alwaysAllowRules: {
        cliArg: state.toolPermissionContext.alwaysAllowRules.cliArg,
        session: [...allowedTools],
      },
    };
  }

  return { ...state, toolPermissionContext, effortValue };
};
```

### 4.4 拒绝追踪隔离

每个子代理都有独立的 `denialTrackingState`（通过 `createSubagentContext`），确保子代理的权限拒绝记录不会污染父代理的上下文。这在 `createDenialTrackingState()` 中实现。

### 4.5 Fork 路径的上下文继承

Fork 子代理是最特殊的情况 — 它完全继承父代理的上下文：

```typescript
// forkSubagent.ts — FORK_AGENT 定义
export const FORK_AGENT = {
  agentType: FORK_SUBAGENT_TYPE,
  tools: ['*'],           // 通配符 — 继承父代理的完整工具池
  model: 'inherit',       // 继承父代理模型（相同模型才能共享缓存）
  permissionMode: 'bubble', // 权限请求冒泡到父终端
  source: 'built-in',
  getSystemPrompt: () => '',  // 未使用 — fork 路径传递父代理的 system prompt
} satisfies BuiltInAgentDefinition;
```

Fork 消息构建 (`buildForkedMessages`) 精心设计以最大化缓存命中：

```typescript
export function buildForkedMessages(
  directive: string,
  assistantMessage: AssistantMessage,
): MessageType[] {
  // 1. 保留父代理的完整 assistant message（所有 tool_use、thinking、text）
  const fullAssistantMessage = { ...assistantMessage, uuid: randomUUID() };

  // 2. 为每个 tool_use 构建相同占位符的 tool_result
  const toolResultBlocks = toolUseBlocks.map(block => ({
    type: 'tool_result',
    tool_use_id: block.id,
    content: [{ type: 'text', text: FORK_PLACEHOLDER_RESULT }],
  }));

  // 3. 构建单一 user message：所有占位符 + 每个子代理独有的 directive
  // 结果：[...history, assistant(all_tool_uses), user(placeholders..., directive)]
  // 只有最后一个 text block 因子代理不同，最大化缓存命中
  return [fullAssistantMessage, toolResultMessage];
}
```

所有 fork 子代理的消息前缀完全相同（使用相同的 `FORK_PLACEHOLDER_RESULT`），只有尾部的 directive 不同。这确保了 Anthropic API 的 prompt cache 在多个并行 fork 之间共享。

### 4.6 递归 Fork 防护

系统通过双重机制防止 fork 子代理再次 fork：

```typescript
// AgentTool.tsx call() 中
if (isForkPath) {
  // 主检查：querySource（抗 autocompact — 设置在 context.options 上，
  // 不受 autocompact 的消息重写影响）
  if (toolUseContext.options.querySource === `agent:builtin:fork`
      // 后备检查：扫描消息中的 fork boilerplate 标签
      || isInForkChild(toolUseContext.messages)) {
    throw new Error('Fork is not available inside a forked worker.');
  }
}
```

---

## 5. Task 系统完整解析

### 5.1 TaskType 和 TaskStatus

所有后台运行的工作都通过 Task 系统管理，定义在 `src/Task.ts`：

```typescript
// Task 类型枚举
export type TaskType =
  | 'local_bash'           // 本地 shell 命令
  | 'local_agent'          // 本地 AI 代理
  | 'remote_agent'         // 远程 CCR 代理
  | 'in_process_teammate'  // 进程内队友
  | 'local_workflow'       // 本地工作流脚本
  | 'monitor_mcp'          // MCP 监控
  | 'dream'                // Dream 推测性记忆整合

// Task 状态枚举
export type TaskStatus =
  | 'pending'     // 等待执行
  | 'running'     // 执行中
  | 'completed'   // 成功完成
  | 'failed'      // 执行失败
  | 'killed'      // 被手动终止

export function isTerminalTaskStatus(status: TaskStatus): boolean {
  return status === 'completed' || status === 'failed' || status === 'killed';
}
```

### 5.2 Task ID 格式

Task ID 采用 `前缀 + 8位随机字符` 的格式，前缀标识任务类型：

```typescript
const TASK_ID_PREFIXES: Record<string, string> = {
  local_bash: 'b',              // 如 b3x7k9m2
  local_agent: 'a',             // 如 a8f2n4p6
  remote_agent: 'r',            // 如 r1j5q8w3
  in_process_teammate: 't',     // 如 t4d7g0s9
  local_workflow: 'w',          // 如 w6h3m1v5
  monitor_mcp: 'm',             // 如 m2k9p4r7
  dream: 'd',                   // 如 d5n8t1x3
};

// 使用 36^8 ≈ 2.8 万亿组合，足以抵抗暴力符号链接攻击
const TASK_ID_ALPHABET = '0123456789abcdefghijklmnopqrstuvwxyz';

export function generateTaskId(type: TaskType): string {
  const prefix = getTaskIdPrefix(type);
  const bytes = randomBytes(8);
  let id = prefix;
  for (let i = 0; i < 8; i++) {
    id += TASK_ID_ALPHABET[bytes[i]! % TASK_ID_ALPHABET.length];
  }
  return id;
}
```

### 5.3 TaskStateBase — 所有任务的公共状态

```typescript
export type TaskStateBase = {
  id: string           // 任务唯一标识符
  type: TaskType       // 任务类型
  status: TaskStatus   // 当前状态
  description: string  // 人类可读描述
  toolUseId?: string   // 关联的 tool_use ID
  startTime: number    // 开始时间戳
  endTime?: number     // 结束时间戳
  totalPausedMs?: number  // 总暂停时间
  outputFile: string   // 磁盘输出文件路径
  outputOffset: number // 输出文件偏移量
  notified: boolean    // 是否已发送通知
};
```

### 5.4 Task 注册与分发

`src/tasks.ts` 管理所有 Task 的注册：

```typescript
export function getAllTasks(): Task[] {
  const tasks: Task[] = [
    LocalShellTask,
    LocalAgentTask,
    RemoteAgentTask,
    DreamTask,
  ];
  if (LocalWorkflowTask) tasks.push(LocalWorkflowTask);  // feature gated
  if (MonitorMcpTask) tasks.push(MonitorMcpTask);         // feature gated
  return tasks;
}

export function getTaskByType(type: TaskType): Task | undefined {
  return getAllTasks().find(t => t.type === type);
}
```

### 5.5 TaskState 联合类型

`src/tasks/types.ts` 定义了所有具体任务状态的联合：

```typescript
export type TaskState =
  | LocalShellTaskState
  | LocalAgentTaskState
  | RemoteAgentTaskState
  | InProcessTeammateTaskState
  | LocalWorkflowTaskState
  | MonitorMcpTaskState
  | DreamTaskState

// 后台任务判定
export function isBackgroundTask(task: TaskState): task is BackgroundTaskState {
  if (task.status !== 'running' && task.status !== 'pending') return false;
  // 前台任务（isBackgrounded === false）不算后台任务
  if ('isBackgrounded' in task && task.isBackgrounded === false) return false;
  return true;
}
```

---

## 6. 各 Task 实现详解

### 6.1 LocalShellTask — 本地 Shell 命令

**文件**：`src/tasks/LocalShellTask/LocalShellTask.tsx`

LocalShellTask 管理后台运行的 shell 命令（`Bash` 工具的 `run_in_background` 模式）。

```typescript
export type LocalShellTaskState = TaskStateBase & {
  type: 'local_bash'
  command: string
  exitCode?: number
  shellCommand?: ShellCommand
  agentId?: AgentId
  kind?: 'bash' | 'monitor'
};
```

独特的功能 — **Stall Watchdog**（卡顿检测）：

```typescript
// 如果命令输出 45 秒没有变化，且最后一行看起来像交互式提示...
const STALL_THRESHOLD_MS = 45_000;

// 检测交互式提示的模式
const PROMPT_PATTERNS = [
  /\(y\/n\)/i,           // (Y/n), (y/N)
  /\[y\/n\]/i,           // [Y/n]
  /\(yes\/no\)/i,
  /Press (any key|Enter)/i,
  /Continue\?/i,
  /Overwrite\?/i
];
```

当检测到命令可能卡在交互式提示时，系统发送通知建议用户终止并使用管道输入重试。

通知格式使用 XML 标签：

```xml
<task-notification>
  <task-id>{taskId}</task-id>
  <tool-use-id>{toolUseId}</tool-use-id>
  <output-file>{outputPath}</output-file>
  <status>completed|failed|killed</status>
  <summary>Background command "..." completed (exit code 0)</summary>
</task-notification>
```

### 6.2 LocalAgentTask — 本地 AI 代理

**文件**：`src/tasks/LocalAgentTask/LocalAgentTask.tsx`

这是最复杂的 Task 类型，管理异步运行的 AI 子代理的完整生命周期。

```typescript
export type LocalAgentTaskState = TaskStateBase & {
  type: 'local_agent'
  agentId: string
  prompt: string
  selectedAgent?: AgentDefinition
  agentType: string
  model?: string
  abortController?: AbortController
  error?: string
  result?: AgentToolResult
  progress?: AgentProgress           // 进度信息
  retrieved: boolean                  // 结果是否已被父代理读取
  messages?: Message[]               // 对话历史（UI 用）
  isBackgrounded: boolean            // 是否已后台化
  pendingMessages: string[]          // SendMessage 排队的消息
  retain: boolean                    // UI 是否 hold 住这个任务
  diskLoaded: boolean                // 是否已从磁盘加载 transcript
  evictAfter?: number                // 面板可见性截止时间
};
```

**进度追踪**是核心功能：

```typescript
export type AgentProgress = {
  toolUseCount: number       // 工具使用次数
  tokenCount: number         // token 消耗
  lastActivity?: ToolActivity  // 最近的工具活动
  recentActivities?: ToolActivity[]  // 最近 5 个活动
  summary?: string           // 后台总结（周期性生成）
};

export type ProgressTracker = {
  toolUseCount: number
  latestInputTokens: number        // API 的 input_tokens 是累积的
  cumulativeOutputTokens: number   // output_tokens 是逐次的
  recentActivities: ToolActivity[]
};
```

**pendingMessages 队列**允许通过 SendMessage 在代理运行时注入消息：

```typescript
export function queuePendingMessage(
  taskId: string,
  msg: string,
  setAppState: SetAppState
): void {
  updateTaskState<LocalAgentTaskState>(taskId, setAppState, task => ({
    ...task,
    pendingMessages: [...task.pendingMessages, msg]
  }));
}

// 在 tool-round 边界时排空
export function drainPendingMessages(taskId, getAppState, setAppState): string[] {
  const task = getAppState().tasks[taskId];
  if (!isLocalAgentTask(task) || task.pendingMessages.length === 0) return [];
  const drained = task.pendingMessages;
  updateTaskState(taskId, setAppState, t => ({ ...t, pendingMessages: [] }));
  return drained;
}
```

通知格式（比 Shell 更丰富）：

```xml
<task-notification>
  <task-id>{taskId}</task-id>
  <tool-use-id>{toolUseId}</tool-use-id>
  <output-file>{outputPath}</output-file>
  <status>completed|failed|killed</status>
  <summary>Agent "Investigate auth bug" completed</summary>
  <result>{agent 的最终文本响应}</result>
  <usage>
    <total_tokens>N</total_tokens>
    <tool_uses>N</tool_uses>
    <duration_ms>N</duration_ms>
  </usage>
  <worktree>
    <worktree-path>/path/to/worktree</worktree-path>
    <worktree-branch>agent-a1b2c3d4</worktree-branch>
  </worktree>
</task-notification>
```

### 6.3 RemoteAgentTask — 远程 CCR 代理

**文件**：`src/tasks/RemoteAgentTask/RemoteAgentTask.tsx`

远程代理在 Anthropic 的 Cloud Code Runner (CCR) 环境中执行，通过轮询获取结果。

```typescript
export type RemoteAgentTaskState = TaskStateBase & {
  type: 'remote_agent'
  remoteTaskType: RemoteTaskType  // 'remote-agent' | 'ultraplan' | 'ultrareview' | ...
  remoteTaskMetadata?: RemoteTaskMetadata
  sessionId: string           // CCR session ID
  command: string
  title: string
  todoList: TodoList          // 远程代理的 TODO 列表（实时同步）
  log: SDKMessage[]           // 远程代理的消息日志
  isLongRunning?: boolean
  pollStartedAt: number       // 本地轮询起始时间
  isRemoteReview?: boolean    // 是否为远程代码审查
  reviewProgress?: {          // 审查进度
    stage?: 'finding' | 'verifying' | 'synthesizing'
    bugsFound: number
    bugsVerified: number
    bugsRefuted: number
  }
  isUltraplan?: boolean       // 是否为 ultraplan 任务
  ultraplanPhase?: 'needs_input' | 'plan_ready'
};
```

远程任务的前置条件检查：

```typescript
export async function checkRemoteAgentEligibility(): Promise<RemoteAgentPreconditionResult> {
  const errors = await checkBackgroundRemoteSessionEligibility();
  // 检查项：
  // - not_logged_in: 需要登录 claude.ai
  // - no_remote_environment: 需要配置云环境
  // - not_in_git_repo: 需要 git 仓库
  // - no_git_remote: 需要 GitHub remote
  // - github_app_not_installed: 需要安装 Claude GitHub App
  // - policy_blocked: 组织策略禁止
  return errors.length > 0
    ? { eligible: false, errors }
    : { eligible: true };
}
```

远程任务支持 **completion checker** 机制：

```typescript
// 注册自定义完成检测器
const completionCheckers = new Map<RemoteTaskType, RemoteTaskCompletionChecker>();

export function registerCompletionChecker(
  remoteTaskType: RemoteTaskType,
  checker: RemoteTaskCompletionChecker
): void {
  completionCheckers.set(remoteTaskType, checker);
}
```

### 6.4 InProcessTeammateTask — 进程内队友

**文件**：`src/tasks/InProcessTeammateTask/`

进程内 teammate 是最轻量的多代理方式 — 在同一 Node.js 进程中通过 AsyncLocalStorage 隔离运行。

```typescript
// types.ts
export type TeammateIdentity = {
  agentId: string        // 如 "researcher@my-team"
  agentName: string      // 如 "researcher"
  teamName: string
  color?: string
  planModeRequired: boolean
  parentSessionId: string  // Leader 的 session ID
};

export type InProcessTeammateTaskState = TaskStateBase & {
  type: 'in_process_teammate'
  identity: TeammateIdentity
  prompt: string
  model?: string
  selectedAgent?: AgentDefinition
  abortController?: AbortController       // 终止整个 teammate
  currentWorkAbortController?: AbortController  // 仅终止当前 turn
  awaitingPlanApproval: boolean
  permissionMode: PermissionMode
  error?: string
  result?: AgentToolResult
  progress?: AgentProgress
  messages?: Message[]
  inProgressToolUseIDs?: Set<string>   // 动画用
  pendingUserMessages: string[]
  isIdle: boolean
  shutdownRequested: boolean
  onIdleCallbacks?: Array<() => void>  // idle 时的通知回调
};
```

关键设计限制：

```typescript
// UI 消息上限 — 防止内存膨胀
export const TEAMMATE_MESSAGES_UI_CAP = 50;

// 原因：BQ 分析显示 ~20MB RSS/agent@500+turns
// 极端案例：一个会话在 2 分钟内启动 292 个代理，达到 36.8GB
export function appendCappedMessage<T>(
  prev: readonly T[] | undefined,
  item: T
): T[] {
  if (prev === undefined || prev.length === 0) return [item];
  if (prev.length >= TEAMMATE_MESSAGES_UI_CAP) {
    const next = prev.slice(-(TEAMMATE_MESSAGES_UI_CAP - 1));
    next.push(item);
    return next;
  }
  return [...prev, item];
}
```

### 6.5 DreamTask — 推测性记忆整合

**文件**：`src/tasks/DreamTask/DreamTask.ts`

DreamTask 是一种特殊的后台任务，用于自动记忆整合（auto-dream）。它在后台运行一个子代理来分析历史会话并更新记忆文件。

```typescript
export type DreamPhase = 'starting' | 'updating';

export type DreamTaskState = TaskStateBase & {
  type: 'dream'
  phase: DreamPhase
  sessionsReviewing: number    // 正在审查的会话数
  filesTouched: string[]       // 被修改的文件（不完整反映）
  turns: DreamTurn[]           // 代理的 turns（最多 30 个）
  abortController?: AbortController
  priorMtime: number           // 用于 kill 时回滚锁
};

export type DreamTurn = {
  text: string
  toolUseCount: number
};
```

DreamTask 的特殊之处：
- **没有模型通知路径** — 纯 UI 展示，`notified: true` 在完成时立即设置
- **Phase 检测简化** — 只有 `starting` 和 `updating` 两个阶段
- **Kill 时回滚锁** — 通过 `rollbackConsolidationLock(priorMtime)` 确保下次会话可以重试

```typescript
// kill 实现
async kill(taskId, setAppState) {
  let priorMtime: number | undefined;
  updateTaskState<DreamTaskState>(taskId, setAppState, task => {
    if (task.status !== 'running') return task;
    task.abortController?.abort();
    priorMtime = task.priorMtime;
    return {
      ...task,
      status: 'killed',
      endTime: Date.now(),
      notified: true,
      abortController: undefined,
    };
  });
  // 回滚锁的 mtime，使下一个会话可以重试
  if (priorMtime !== undefined) {
    await rollbackConsolidationLock(priorMtime);
  }
}
```

---

## 7. Coordinator 模式

Coordinator 模式是一种特殊的运行模式，将主代理转变为一个纯粹的**任务协调者**，不直接操作文件系统，而是通过 Worker 代理完成所有实际工作。

### 7.1 模式激活

```typescript
// src/coordinator/coordinatorMode.ts
export function isCoordinatorMode(): boolean {
  if (feature('COORDINATOR_MODE')) {
    return isEnvTruthy(process.env.CLAUDE_CODE_COORDINATOR_MODE);
  }
  return false;
}
```

通过环境变量 `CLAUDE_CODE_COORDINATOR_MODE=1` 激活。

### 7.2 Coordinator 的工具限制

Coordinator 只能使用三个核心工具：

```typescript
// coordinatorMode.ts
const INTERNAL_WORKER_TOOLS = new Set([
  TEAM_CREATE_TOOL_NAME,     // TeamCreate
  TEAM_DELETE_TOOL_NAME,     // TeamDelete
  SEND_MESSAGE_TOOL_NAME,   // SendMessage
  SYNTHETIC_OUTPUT_TOOL_NAME // SyntheticOutput
]);
```

Coordinator 的可用工具：
- **Agent** — 启动新 Worker
- **SendMessage** — 向运行中的 Worker 发送后续指令
- **TaskStop** — 停止运行中的 Worker
- **subscribe_pr_activity / unsubscribe_pr_activity**（如果可用）

### 7.3 Worker 上下文注入

Coordinator 通过 `getCoordinatorUserContext()` 向 Worker 传递其可用工具信息：

```typescript
export function getCoordinatorUserContext(
  mcpClients: ReadonlyArray<{ name: string }>,
  scratchpadDir?: string
): { [k: string]: string } {
  if (!isCoordinatorMode()) return {};

  // Worker 可用的工具列表
  const workerTools = Array.from(ASYNC_AGENT_ALLOWED_TOOLS)
    .filter(name => !INTERNAL_WORKER_TOOLS.has(name))
    .sort().join(', ');

  let content = `Workers spawned via the Agent tool have access to these tools: ${workerTools}`;

  // MCP 服务器信息
  if (mcpClients.length > 0) {
    content += `\n\nWorkers also have access to MCP tools from connected MCP servers: ${serverNames}`;
  }

  // Scratchpad 目录 — Worker 可以在此无需权限提示地读写
  if (scratchpadDir && isScratchpadGateEnabled()) {
    content += `\n\nScratchpad directory: ${scratchpadDir}
Workers can read and write here without permission prompts.
Use this for durable cross-worker knowledge.`;
  }

  return { workerToolsContext: content };
}
```

### 7.4 Coordinator 系统提示

Coordinator 模式完全覆盖默认的系统提示，提供详细的工作流指导：

```typescript
export function getCoordinatorSystemPrompt(): string {
  return `You are Claude Code, an AI assistant that orchestrates software
engineering tasks across multiple workers.

## 1. Your Role
You are a **coordinator**. Your job is to:
- Help the user achieve their goal
- Direct workers to research, implement and verify code changes
- Synthesize results and communicate with the user
- Answer questions directly when possible

## 2. Your Tools
- **Agent** - Spawn a new worker
- **SendMessage** - Continue an existing worker
- **TaskStop** - Stop a running worker

## 3. Workers
Workers execute tasks autonomously — research, implementation, or verification.

## 4. Task Workflow
| Phase | Who | Purpose |
|-------|-----|---------|
| Research | Workers (parallel) | Investigate codebase |
| Synthesis | **You** (coordinator) | Read findings, craft specs |
| Implementation | Workers | Make targeted changes |
| Verification | Workers | Test changes work |

## 5. Writing Worker Prompts
**Workers can't see your conversation.** Every prompt must be self-contained.
...`
}
```

核心原则：
- **永远不要委托理解** — Coordinator 必须综合研究结果后再下达具体指令
- **并行是超能力** — 尽可能并行启动独立的 Worker
- **Continue vs Spawn** — 根据上下文重叠程度决定是继续已有 Worker 还是新建

### 7.5 通知格式与流程

Worker 完成后通过 `<task-notification>` XML 通知 Coordinator：

```
Coordinator → Agent({ description: "Investigate auth bug", prompt: "..." })
           → 立即返回 { status: "async_launched", agentId: "a3x7k9m2" }
           → 继续处理其他任务或回复用户

[Worker 完成后]

<task-notification>
  <task-id>a3x7k9m2</task-id>
  <status>completed</status>
  <summary>Agent "Investigate auth bug" completed</summary>
  <result>Found null pointer in src/auth/validate.ts:42...</result>
</task-notification>

Coordinator → 综合结果 → SendMessage({ to: "a3x7k9m2", message: "Fix the null pointer..." })
```

---

## 8. SendMessage 工具：代理间通信

### 8.1 工具定义

`SendMessage` 工具定义在 `src/tools/SendMessageTool/SendMessageTool.ts`，仅在 Agent Swarms 启用时可用：

```typescript
export const SendMessageTool = buildTool({
  name: SEND_MESSAGE_TOOL_NAME,  // "SendMessage"
  searchHint: 'send messages to agent teammates (swarm protocol)',

  isEnabled() {
    return isAgentSwarmsEnabled();
  },

  // 纯文本消息是只读操作
  isReadOnly(input) {
    return typeof input.message === 'string';
  },
  // ...
});
```

### 8.2 Input Schema

```typescript
const inputSchema = lazySchema(() => z.object({
  to: z.string().describe(
    'Recipient: teammate name, "*" for broadcast, ' +
    '"uds:<socket-path>" for local peer, ' +
    '"bridge:<session-id>" for Remote Control peer'
  ),
  summary: z.string().optional()
    .describe('5-10 word preview summary'),
  message: z.union([
    z.string().describe('Plain text message'),
    StructuredMessage()  // shutdown_request/response, plan_approval_response
  ])
}));
```

### 8.3 消息路由逻辑

`call()` 方法的路由决策树：

```
SendMessage({ to, message })
  │
  ├─ to = "bridge:session_..." ──→ postInterClaudeMessage() 跨机器通信
  │
  ├─ to = "uds:/path/to.sock" ──→ sendToUdsSocket() 本地 IPC
  │
  ├─ to 匹配 agentNameRegistry 或 agentId 格式？
  │   ├─ task 状态 = running ──→ queuePendingMessage() 排队
  │   ├─ task 状态 = completed/failed/killed ──→ resumeAgentBackground() 自动恢复
  │   └─ task 不存在 ──→ 尝试从磁盘 transcript 恢复
  │
  ├─ to = "*" ──→ handleBroadcast() 广播给所有队友
  │
  ├─ to = 普通名称（文本消息）──→ handleMessage() 写入 mailbox
  │
  └─ 结构化消息分发：
      ├─ shutdown_request ──→ handleShutdownRequest()
      ├─ shutdown_response (approve) ──→ handleShutdownApproval()
      ├─ shutdown_response (reject) ──→ handleShutdownRejection()
      ├─ plan_approval_response (approve) ──→ handlePlanApproval()
      └─ plan_approval_response (reject) ──→ handlePlanRejection()
```

### 8.4 关键路由：子代理消息注入

对于本地子代理（Coordinator 模式的 Worker），SendMessage 通过两个机制将消息注入运行中的代理：

**1. pendingMessages 队列（运行中的代理）**：

```typescript
if (isLocalAgentTask(task) && task.status === 'running') {
  queuePendingMessage(
    agentId,
    input.message,
    context.setAppStateForTasks ?? context.setAppState
  );
  return { data: { success: true, message: 'Message queued for delivery...' } };
}
```

消息在代理的 tool-round 边界被排空（`drainPendingMessages`），作为用户消息注入代理的对话。

**2. 自动恢复（已停止的代理）**：

```typescript
// task 存在但已停止 — 自动恢复
try {
  const result = await resumeAgentBackground({
    agentId,
    prompt: input.message,
    toolUseContext: context,
    canUseTool,
    invokingRequestId: assistantMessage?.requestId,
  });
  return { data: { success: true, message: `Agent "${input.to}" was stopped; resumed...` } };
} catch (e) {
  // ...
}
```

### 8.5 Mailbox 通信（Teammate 间）

对于 Teammate 之间的通信，消息写入文件系统 mailbox：

```typescript
async function handleMessage(recipientName, content, summary, context) {
  const teamName = getTeamName(appState.teamContext);
  const senderName = getAgentName() || TEAM_LEAD_NAME;

  await writeToMailbox(recipientName, {
    from: senderName,
    text: content,
    summary,
    timestamp: new Date().toISOString(),
    color: senderColor,
  }, teamName);

  return { data: { success: true, message: `Message sent to ${recipientName}'s inbox` } };
}
```

### 8.6 广播机制

广播 (`to: "*"`) 向团队中除自己以外的所有成员发送消息：

```typescript
async function handleBroadcast(content, summary, context) {
  const teamFile = await readTeamFileAsync(teamName);
  const recipients = teamFile.members
    .filter(m => m.name.toLowerCase() !== senderName.toLowerCase())
    .map(m => m.name);

  for (const recipientName of recipients) {
    await writeToMailbox(recipientName, {
      from: senderName,
      text: content,
      summary,
      timestamp: new Date().toISOString(),
    }, teamName);
  }

  return { data: { success: true, recipients, ... } };
}
```

---

## 9. Multi-Agent Swarm

Swarm 系统是 Claude Code 中最完整的多代理协调框架，支持通过 tmux、iTerm2 或进程内方式运行多个独立的 Claude Code 实例。

### 9.1 Swarm 架构

```
┌─────────────────────────────────────────────┐
│                Team Lead                      │
│  （主 Claude Code 实例，运行在用户终端）       │
├─────────────────────────────────────────────┤
│           Backend Registry                    │
│  ┌──────────┬──────────┬──────────────────┐  │
│  │  Tmux    │  iTerm2  │  InProcess       │  │
│  │  Backend │  Backend │  Backend         │  │
│  └──────────┴──────────┴──────────────────┘  │
├─────────────────────────────────────────────┤
│           Mailbox 通信层                      │
│  ~/.claude/teams/{teamName}/mailbox/          │
├─────────────────────────────────────────────┤
│           Permission Sync 层                  │
│  ~/.claude/teams/{teamName}/permissions/      │
└─────────────────────────────────────────────┘
```

### 9.2 Backend 系统

三种 backend 实现（`src/utils/swarm/backends/`）：

**TmuxBackend** — 通过 tmux 管理 pane：

```typescript
// backends/TmuxBackend.ts
class TmuxBackend implements PaneBackend {
  // 在 tmux 内时：分割当前窗口（leader 30%, teammates 70%）
  // 在 tmux 外时：创建独立的 swarm session
  async createPane(config: TeammateSpawnConfig): Promise<CreatePaneResult> {
    const release = await acquirePaneCreationLock();  // 顺序创建防止竞态
    try {
      // 创建 pane、设置颜色、发送启动命令
      await waitForPaneShellReady();  // 200ms 等待 shell 初始化
      // ...
    } finally {
      release();
    }
  }
}
```

**InProcessBackend** — 进程内执行：

```typescript
// backends/InProcessBackend.ts
class InProcessBackend implements TeammateExecutor {
  private context: ToolUseContext | null = null;

  setContext(context: ToolUseContext): void {
    this.context = context;
  }

  async spawn(config: TeammateSpawnConfig): Promise<TeammateSpawnResult> {
    // 1. createTeammateContext() — AsyncLocalStorage 隔离
    // 2. 独立的 AbortController
    // 3. 注册到 AppState.tasks
    // 4. startInProcessTeammate() 启动执行循环
    const result = await spawnInProcessTeammate({
      name: config.name,
      teamName: config.teamName,
      prompt: config.prompt,
      color: config.color,
      planModeRequired: config.planModeRequired ?? false,
    }, this.context);
    return result;
  }
}
```

### 9.3 环境变量传播

Teammate 进程需要继承 leader 的关键环境变量和 CLI 标志：

```typescript
// spawnUtils.ts — CLI 标志继承
export function buildInheritedCliFlags(options?: {
  planModeRequired?: boolean;
  permissionMode?: PermissionMode;
}): string {
  const flags: string[] = [];
  // 传播权限模式（plan 模式优先于 bypass）
  if (planModeRequired) { /* 不继承 bypass */ }
  else if (permissionMode === 'bypassPermissions') {
    flags.push('--dangerously-skip-permissions');
  }
  // 传播 model、settings、plugin-dir、teammate-mode、chrome 标志
  return flags.join(' ');
}

// 需要显式转发的环境变量
const TEAMMATE_ENV_VARS = [
  'CLAUDE_CODE_USE_BEDROCK',    // API provider
  'CLAUDE_CODE_USE_VERTEX',
  'ANTHROPIC_BASE_URL',         // 自定义端点
  'CLAUDE_CONFIG_DIR',          // 配置目录
  'CLAUDE_CODE_REMOTE',         // CCR 标记
  'HTTPS_PROXY', 'HTTP_PROXY',  // 代理设置
  'SSL_CERT_FILE',              // TLS 证书
  // ...
];
```

### 9.4 Permission Sync — 权限同步

Swarm 中最关键的安全机制是权限同步。当 Worker 需要权限审批时，请求会路由到 Team Lead 的 UI：

```typescript
// permissionSync.ts — 权限请求流程
//
// 1. Worker 遇到需要权限的工具使用
// 2. Worker 发送 permission_request 到 Leader 的 mailbox
// 3. Leader 轮询 mailbox，检测权限请求
// 4. 用户通过 Leader 的 UI 批准/拒绝
// 5. Leader 发送 permission_response 到 Worker 的 mailbox
// 6. Worker 轮询 mailbox 获取响应并继续执行

export type SwarmPermissionRequest = {
  id: string              // 唯一请求 ID
  workerId: string        // Worker 的 CLAUDE_CODE_AGENT_ID
  workerName: string      // Worker 的名称
  workerColor?: string    // Worker 颜色标识
  teamName: string        // 团队名称
  toolName: string        // 需要权限的工具名称
  toolUseId: string       // tool_use ID
  description: string     // 操作描述
  input: Record<string, unknown>  // 工具输入
  permissionSuggestions: unknown[]  // 建议的权限规则
  status: 'pending' | 'approved' | 'rejected'
  resolvedBy?: 'worker' | 'leader'
  createdAt: number
};
```

权限文件存储在 `~/.claude/teams/{teamName}/permissions/` 下：
- `pending/` — 等待处理的请求
- `resolved/` — 已处理的请求

文件级锁（通过 `lockfile.lock()`）确保原子性：

```typescript
export async function writePermissionRequest(
  request: SwarmPermissionRequest
): Promise<SwarmPermissionRequest> {
  await ensurePermissionDirsAsync(request.teamName);
  const pendingPath = getPendingRequestPath(request.teamName, request.id);
  const lockFilePath = join(getPendingDir(request.teamName), '.lock');

  let release: (() => Promise<void>) | undefined;
  try {
    release = await lockfile.lock(lockFilePath);
    await writeFile(pendingPath, jsonStringify(request, null, 2), 'utf-8');
    return request;
  } finally {
    if (release) await release();
  }
}
```

### 9.5 Leader Permission Bridge

对于进程内 teammate，权限请求通过 `leaderPermissionBridge` 直接路由到 Leader 的 React UI：

```typescript
// leaderPermissionBridge.ts
let registeredSetter: SetToolUseConfirmQueueFn | null = null;
let registeredPermissionContextSetter: SetToolPermissionContextFn | null = null;

// REPL 启动时注册
export function registerLeaderToolUseConfirmQueue(
  setter: SetToolUseConfirmQueueFn
): void {
  registeredSetter = setter;
}

// 进程内 teammate 使用
export function getLeaderToolUseConfirmQueue(): SetToolUseConfirmQueueFn | null {
  return registeredSetter;
}
```

这允许进程内 teammate 的权限弹窗直接出现在 Leader 的终端 UI 中，无需通过文件系统 mailbox。

### 9.6 Scratchpad — 跨 Worker 共享知识

Coordinator 模式下提供 scratchpad 目录，Worker 可以在此无需权限提示地读写文件：

```typescript
if (scratchpadDir && isScratchpadGateEnabled()) {
  content += `\n\nScratchpad directory: ${scratchpadDir}
Workers can read and write here without permission prompts.
Use this for durable cross-worker knowledge — structure files however fits the work.`
}
```

这解决了 Worker 之间信息共享的问题 — Worker 可以将调研结果写入 scratchpad，其他 Worker 可以直接读取。

### 9.7 Tmux Session 管理

Swarm 的 tmux session 使用 PID 隔离以避免多个 Claude 实例冲突：

```typescript
// constants.ts
export const SWARM_SESSION_NAME = 'claude-swarm';
export const HIDDEN_SESSION_NAME = 'claude-hidden';

export function getSwarmSocketName(): string {
  return `claude-swarm-${process.pid}`;  // PID 隔离
}

export const TEAMMATE_COMMAND_ENV_VAR = 'CLAUDE_CODE_TEAMMATE_COMMAND';
export const TEAMMATE_COLOR_ENV_VAR = 'CLAUDE_CODE_AGENT_COLOR';
export const PLAN_MODE_REQUIRED_ENV_VAR = 'CLAUDE_CODE_PLAN_MODE_REQUIRED';
```

---

## 10. 设计模式总结

### 10.1 统一入口 + 分支路由

AgentTool 的 `call()` 方法是一个大型的决策路由器，根据参数组合将请求路由到 5 种完全不同的执行路径。这种设计将复杂性集中在一个点上，使得模型只需学习一个工具接口。

### 10.2 Lazy Schema 与 Dead Code Elimination

通过 `lazySchema()` 延迟求值 + `feature()` 编译时常量 + `.omit()` 动态裁剪，系统实现了：
- 避免循环依赖（模块加载时不求值 schema）
- 编译时消除不需要的代码路径（`feature()` 在 Bun 编译时求值）
- 运行时根据 feature flag 和用户类型动态调整 API schema

### 10.3 CacheSafeParams 与 Prompt Cache 共享

Fork 子代理的核心优化：所有 fork 共享相同的 API 请求前缀（system prompt + tools + messages prefix），只有尾部的 directive 不同。这通过以下机制实现：

- `FORK_PLACEHOLDER_RESULT` — 所有 fork 使用相同的占位符 tool_result
- `useExactTools: true` — 直接使用父代理的工具池，不重新计算
- `model: 'inherit'` — 使用相同模型以保持 cache key 一致
- `override.systemPrompt` — 直接传递父代理渲染好的 system prompt 字节

### 10.4 渐进式后台化

同步代理可以中途转为后台运行。这通过 `Promise.race()` 在每次消息迭代时检测后台化信号实现：

```
开始 (前台) → [2秒后显示 BackgroundHint]
  → [用户按 Shift+Down]
  → Promise.race 检测到 background 信号
  → 停止前台迭代器
  → 重新以异步模式启动 runAgent
  → 返回 async_launched
```

### 10.5 Mailbox + File Lock 通信

Teammate 间通信使用文件系统作为消息队列，配合 lockfile 实现原子性。这种设计的优势：
- 跨进程通信无需 IPC 机制
- 天然持久化（适合 tmux 断连重连）
- 易于调试（直接查看 mailbox 文件）

### 10.6 双层权限：bubble + sync

子代理的权限模式分两种策略：
- **`bubble`** — 权限请求冒泡到父终端显示（fork 子代理使用）
- **`shouldAvoidPermissionPrompts: true`** — 自动拒绝所有权限请求（后台异步代理）
- **Permission Sync** — 通过文件系统 mailbox 将 Worker 的权限请求路由到 Leader（Swarm 模式）

### 10.7 Agent Definition 的多来源加载

代理定义可以来自多个来源：
- **Built-in** — 代码中定义（general-purpose、Explore、Plan、verification 等）
- **User** — 用户在 `.claude/agents/` 目录中的 markdown/JSON 文件
- **Plugin** — 通过插件系统加载
- **policySettings** — 组织策略设置

每种来源有不同的信任级别，影响 hooks 注册、MCP 服务器加载等安全敏感操作。

### 10.8 幂等通知机制

所有 Task 类型都使用原子性的 "check-and-set notified flag" 模式防止重复通知：

```typescript
let shouldEnqueue = false;
updateTaskState(taskId, setAppState, task => {
  if (task.notified) return task;  // 已通知 — 跳过
  shouldEnqueue = true;
  return { ...task, notified: true };
});
if (!shouldEnqueue) return;
// 发送通知...
```

这确保了即使在并发场景下（如 TaskStopTool 和自然完成同时触发），每个任务只会发送一次通知。

---

以上是 Claude Code 多代理系统的完整解析。这个系统的设计充分体现了实际工程中的权衡艺术：在 prompt cache 效率、安全隔离、用户体验和系统复杂度之间找到了精妙的平衡点。从简单的同步子代理到完整的 tmux swarm 集群，五种执行模式通过统一的 `Agent` 工具接口暴露给模型，实现了"简单的接口，复杂的内部"这一经典设计原则。
