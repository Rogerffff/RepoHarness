# 第 8 篇：MCP（Model Context Protocol）集成

## 1. 概述：MCP 协议与 Claude Code 的关系

MCP（Model Context Protocol）是 Anthropic 推出的开放协议，旨在为大语言模型提供标准化的外部工具和资源访问能力。Claude Code 作为 Anthropic 官方 CLI 工具，对 MCP 提供了深度集成——用户可以通过配置文件声明 MCP 服务器，Claude Code 会自动连接这些服务器、发现其提供的工具（Tools）、资源（Resources）和提示模板（Prompts），并将它们无缝融合到 Claude 的对话能力中。

从架构角度看，MCP 集成涉及以下核心模块：

```
src/services/mcp/          ← MCP 服务层：客户端、配置、认证、传输
src/tools/MCPTool/         ← MCP 工具包装器（将远程工具适配为内置 Tool 接口）
src/tools/McpAuthTool/     ← OAuth 认证伪工具
src/tools/ReadMcpResourceTool/  ← 资源读取工具
src/tools/ListMcpResourcesTool/ ← 资源列表工具
src/utils/mcp/             ← 辅助函数（日期解析、elicitation 验证等）
```

MCP 集成的设计哲学是"对模型透明"：无论是内置工具（如 `Read`、`Write`）还是来自 MCP 服务器的工具（如 `mcp__slack__send_message`），它们在 Claude 的视角中共享相同的工具调用接口，区别仅在于名称前缀和权限策略。

---

## 2. MCP 客户端架构

### 2.1 传输方式总览

Claude Code 支持丰富的传输方式来连接 MCP 服务器。每种传输方式对应一种 `type` 值，定义在 `src/services/mcp/types.ts` 的 `TransportSchema` 中：

| 传输类型 | type 值 | 典型场景 | 底层实现 |
|---------|---------|---------|---------|
| **Stdio** | `stdio`（或省略） | 本地进程通信 | `StdioClientTransport` |
| **SSE** | `sse` | 远程服务器（旧版） | `SSEClientTransport` |
| **StreamableHTTP** | `http` | 远程服务器（推荐） | `StreamableHTTPClientTransport` |
| **WebSocket** | `ws` | 远程服务器（双向通信） | `WebSocketTransport` |
| **SSE-IDE** | `sse-ide` | IDE 扩展（内部） | `SSEClientTransport` |
| **WS-IDE** | `ws-ide` | IDE 扩展（WebSocket） | `WebSocketTransport` |
| **SDK Control** | `sdk` | SDK 内嵌传输 | `SdkControlClientTransport` |
| **Claude.ai Proxy** | `claudeai-proxy` | Claude.ai 连接器 | `StreamableHTTPClientTransport` |
| **InProcess** | （内部使用） | Chrome MCP 等内置服务 | `InProcessTransport` |

各传输类型的配置 schema 使用 Zod 严格校验。以下是两种最常见的配置形式：

```typescript
// Stdio 传输（本地进程）
// 对应 McpStdioServerConfigSchema
{
  type: "stdio",          // 可省略，默认就是 stdio
  command: "npx",         // 启动命令
  args: ["-y", "@modelcontextprotocol/server-filesystem"],
  env: { "HOME": "/tmp" } // 可选：注入环境变量
}

// HTTP 传输（远程 Streamable HTTP）
// 对应 McpHTTPServerConfigSchema
{
  type: "http",
  url: "https://mcp.example.com/api",
  headers: { "X-Api-Key": "${API_KEY}" }, // 支持环境变量展开
  oauth: {                                // 可选：OAuth 配置
    clientId: "my-client",
    callbackPort: 9876
  }
}
```

### 2.2 连接流程

所有连接逻辑集中在 `src/services/mcp/client.ts` 的 `connectToServer()` 函数中。该函数使用 `lodash/memoize` 做缓存，避免重复连接同一服务器：

```typescript
// 连接缓存键 = 服务器名 + 配置序列化
export function getServerCacheKey(
  name: string,
  serverRef: ScopedMcpServerConfig,
): string {
  return `${name}-${jsonStringify(serverRef)}`
}

// memoize 确保相同配置只连接一次
export const connectToServer = memoize(
  async (name, serverRef, serverStats?) => {
    // ... 根据 type 创建对应 transport，然后调用 client.connect(transport)
  },
  getServerCacheKey,
)
```

连接的核心步骤：

1. **创建 Transport**：根据 `serverRef.type` 分发到对应的传输构造逻辑
2. **创建 MCP Client**：使用 `@modelcontextprotocol/sdk` 的 `Client` 类，声明 `roots` 和 `elicitation` 能力
3. **连接与超时**：`Promise.race([connectPromise, timeoutPromise])`，默认 30 秒超时（`MCP_TIMEOUT` 环境变量可调）
4. **错误分类**：401 → `needs-auth`；超时/网络错误 → `failed`；正常 → `connected`

### 2.3 连接状态机

每个 MCP 服务器连接有五种状态（定义在 `types.ts`）：

```
┌─────────┐     连接成功     ┌───────────┐
│ pending ├────────────────►│ connected │
└────┬────┘                 └─────┬─────┘
     │                            │
     │ 连接失败/超时              │ onclose/onerror
     ▼                            ▼
┌─────────┐                 ┌─────────┐
│ failed  │                 │（重新连接）│
└─────────┘                 └─────────┘
     
┌───────────┐               ┌──────────┐
│ needs-auth│               │ disabled │
└───────────┘               └──────────┘
```

- **connected**：持有活跃的 `Client` 实例，可以调用工具
- **failed**：连接失败，携带错误信息
- **needs-auth**：HTTP 401，需要用户完成 OAuth 流程
- **pending**：正在连接中
- **disabled**：用户主动禁用

### 2.4 断线重连

`connectToServer` 在返回 `ConnectedMCPServer` 后，会安装 `onerror` 和 `onclose` 处理器。当连接断开时，`onclose` 清除 memoize 缓存，下次工具调用时 `ensureConnectedClient()` 会自动触发重连：

```typescript
// onclose 清除所有缓存，触发重连
client.onclose = () => {
  const key = getServerCacheKey(name, serverRef)
  // 清除连接缓存和工具/资源缓存
  fetchToolsForClient.cache.delete(name)
  fetchResourcesForClient.cache.delete(name)
  connectToServer.cache.delete(key)
}
```

对于远程传输（SSE/HTTP），还有额外的错误计数器：连续 3 次终端性错误（ECONNRESET、ETIMEDOUT 等）后主动关闭连接以触发重连。

### 2.5 批量连接调度

启动时需要同时连接多个 MCP 服务器。Claude Code 将服务器分为本地（stdio/sdk）和远程两组，分别以不同的并发度连接：

```typescript
// 本地服务器：受进程派生限制，低并发（默认 3）
const localBatchSize = getMcpServerConnectionBatchSize() // 默认 3
// 远程服务器：仅网络 I/O，高并发（默认 20）
const remoteBatchSize = getRemoteMcpServerConnectionBatchSize() // 默认 20
```

底层使用 `p-map` 实现流式调度——一个槽位空出立即填入下一个，而非等待整批完成。

---

## 3. 服务器配置与发现

### 3.1 配置文件：.mcp.json

MCP 服务器配置的主要入口是项目根目录的 `.mcp.json` 文件，遵循 `McpJsonConfigSchema`：

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    },
    "github": {
      "type": "http",
      "url": "https://mcp.github.com",
      "oauth": { "clientId": "xxx" }
    }
  }
}
```

### 3.2 多作用域合并

Claude Code 从多个来源加载 MCP 配置，按优先级从低到高合并：

```
plugin < claude.ai < user < project < local < dynamic
```

配置发现由 `getClaudeCodeMcpConfigs()` 和 `getAllMcpConfigs()` 实现（`config.ts`）：

| 作用域 | 来源 | ConfigScope |
|-------|------|-------------|
| **enterprise** | `managed-mcp.json`（由企业管理） | `'enterprise'` |
| **user** | `~/.claude/settings.json` 中的 `mcpServers` | `'user'` |
| **project** | 从 CWD 向上搜索 `.mcp.json` 文件（越近优先级越高） | `'project'` |
| **local** | 当前项目 `.claude/settings.local.json` | `'local'` |
| **dynamic** | 运行时通过 `--mcp-config` 或 SDK 注入 | `'dynamic'` |
| **plugin** | 已安装插件提供的 MCP 服务器 | —（`pluginSource`标记） |
| **claude.ai** | Claude.ai 网页端配置的连接器 | `'claudeai'` |

项目级 `.mcp.json` 的搜索特别有趣——它从 CWD 向上遍历到根目录，每层的 `.mcp.json` 都会被解析，靠近 CWD 的配置覆盖上层：

```typescript
// config.ts getMcpConfigsByScope('project')
let currentDir = getCwd()
while (currentDir !== parse(currentDir).root) {
  dirs.push(currentDir)
  currentDir = dirname(currentDir)
}
// 从根目录到 CWD 的顺序处理，后面的覆盖前面的
for (const dir of dirs.reverse()) {
  const mcpJsonPath = join(dir, '.mcp.json')
  // 解析并合并 ...
}
```

### 3.3 环境变量展开

配置中的字符串值支持 `${VAR}` 和 `${VAR:-default}` 语法的环境变量展开，实现在 `envExpansion.ts`：

```typescript
// 展开 ${VAR} 和 ${VAR:-default} 语法
export function expandEnvVarsInString(value: string): {
  expanded: string
  missingVars: string[]  // 记录缺失的变量，用于警告
} {
  const expanded = value.replace(/\$\{([^}]+)\}/g, (match, varContent) => {
    const [varName, defaultValue] = varContent.split(':-', 2)
    const envValue = process.env[varName]
    if (envValue !== undefined) return envValue
    if (defaultValue !== undefined) return defaultValue
    missingVars.push(varName)
    return match // 保留原文便于调试
  })
  return { expanded, missingVars }
}
```

展开在 `expandEnvVars()` 中按传输类型精确应用：stdio 展开 command/args/env，远程展开 url/headers，IDE 和 SDK 类型不展开。

### 3.4 去重机制

当多个来源提供相同的 MCP 服务器时，Claude Code 使用基于"签名"的去重：

```typescript
// 签名计算：stdio 用命令数组，远程用 URL
export function getMcpServerSignature(config: McpServerConfig): string | null {
  const cmd = getServerCommandArray(config)
  if (cmd) return `stdio:${jsonStringify(cmd)}`
  const url = getServerUrl(config)
  if (url) return `url:${unwrapCcrProxyUrl(url)}`
  return null
}
```

去重规则：
- **插件 vs 手动配置**：手动配置优先，`dedupPluginMcpServers()` 抑制重复的插件服务器
- **Claude.ai vs 手动配置**：手动配置优先，`dedupClaudeAiMcpServers()` 抑制重复的连接器
- **禁用的服务器**不参与去重目标（避免两边都不运行）

### 3.5 企业策略过滤

企业管理员可以通过 `allowedMcpServers` / `deniedMcpServers` 控制可用服务器。策略支持按名称、命令数组、URL 通配符三种匹配方式，且 denylist 绝对优先于 allowlist：

```typescript
function isMcpServerAllowedByPolicy(serverName, config): boolean {
  // Denylist 绝对优先
  if (isMcpServerDenied(serverName, config)) return false
  // 无 allowlist 则全部允许
  if (!settings.allowedMcpServers) return true
  // 空 allowlist 表示阻止所有
  if (settings.allowedMcpServers.length === 0) return false
  // 按类型匹配：名称 / 命令数组 / URL 通配符
  // ...
}
```

---

## 4. 工具集成流程

### 4.1 工具发现：list_tools → Tool 包装

当 MCP 服务器连接成功后，`fetchToolsForClient()` 调用 `tools/list` 获取工具列表，然后将每个 MCP 工具包装为 Claude Code 内部的 `Tool` 接口：

```typescript
export const fetchToolsForClient = memoizeWithLRU(
  async (client: MCPServerConnection): Promise<Tool[]> => {
    const result = await client.client.request(
      { method: 'tools/list' },
      ListToolsResultSchema,
    )
    // 对原始工具数据进行 Unicode 净化
    const toolsToProcess = recursivelySanitizeUnicode(result.tools)

    return toolsToProcess.map((tool): Tool => {
      // 构造全限定名：mcp__<server>__<tool>
      const fullyQualifiedName = buildMcpToolName(client.name, tool.name)
      return {
        ...MCPTool,  // 继承 MCPTool 的基础属性（渲染、权限检查等）
        name: fullyQualifiedName,
        mcpInfo: { serverName: client.name, toolName: tool.name },
        isMcp: true,
        // annotations 映射到 Claude Code 的工具属性
        isConcurrencySafe: () => tool.annotations?.readOnlyHint ?? false,
        isReadOnly: () => tool.annotations?.readOnlyHint ?? false,
        isDestructive: () => tool.annotations?.destructiveHint ?? false,
        isOpenWorld: () => tool.annotations?.openWorldHint ?? false,
        // 工具调用委托到 callMCPToolWithUrlElicitationRetry
        async call(args, context, _canUseTool, parentMessage, onProgress) {
          // ... 详见下文
        },
      }
    })
  },
  (client) => client.name,  // LRU 缓存键：服务器名
  MCP_FETCH_CACHE_SIZE,      // 缓存上限：20
)
```

### 4.2 名称规范化

MCP 工具名称遵循 `mcp__<server>__<tool>` 格式，通过 `mcpStringUtils.ts` 管理：

```typescript
// 规范化：替换非法字符为下划线
export function normalizeNameForMCP(name: string): string {
  let normalized = name.replace(/[^a-zA-Z0-9_-]/g, '_')
  // claude.ai 服务器还要合并连续下划线、去首尾下划线
  if (name.startsWith('claude.ai ')) {
    normalized = normalized.replace(/_+/g, '_').replace(/^_|_$/g, '')
  }
  return normalized
}

// 构造全限定名
export function buildMcpToolName(serverName: string, toolName: string): string {
  return `mcp__${normalizeNameForMCP(serverName)}__${normalizeNameForMCP(toolName)}`
}
```

解析时使用 `__` 作为分隔符（已知限制：如果服务器名本身包含 `__` 会解析错误）。

### 4.3 工具调用与大结果处理

工具调用通过 `callMCPTool()` 发送 JSON-RPC 请求，配合超时机制（默认约 27.8 小时，可通过 `MCP_TOOL_TIMEOUT` 调整）：

```typescript
async function callMCPTool({ client, tool, args, meta, signal, onProgress }) {
  const result = await Promise.race([
    client.callTool(
      { name: tool, arguments: args, _meta: meta },
      CallToolResultSchema,
      { signal, timeout: timeoutMs, onprogress: /* SDK 进度回调 */ },
    ),
    timeoutPromise,
  ])

  // isError 检查
  if (result.isError) {
    throw new McpToolCallError(...)
  }

  // 处理大结果：截断或持久化到文件
  return processMCPResult(result, tool, name)
}
```

大结果处理策略（`processMCPResult`）：

1. 如果结果未超过 token 限制 → 直接返回
2. 如果包含图片 → 截断（保留图片可查看性）
3. 如果可以持久化 → 保存到临时文件，返回文件路径和读取指引
4. 持久化失败 → 回退到截断

### 4.4 进度流式

MCP 工具支持进度报告。Claude Code 在工具调用的三个阶段发出进度事件：

```typescript
// 开始
onProgress({ type: 'mcp_progress', status: 'started', serverName, toolName })

// 运行中（来自 MCP SDK 的 onprogress 回调）
onProgress({
  type: 'mcp_progress', status: 'progress',
  progress: sdkProgress.progress,  // 当前进度
  total: sdkProgress.total,        // 总量
  progressMessage: sdkProgress.message,
})

// 完成/失败
onProgress({ type: 'mcp_progress', status: 'completed', elapsedTimeMs: ... })
```

---

## 5. 资源浏览

MCP 服务器除了工具外，还可以提供资源（Resources）——表示文件、数据库记录等可读内容。Claude Code 通过两个专用工具暴露此能力。

### 5.1 ListMcpResourcesTool

列出可用资源，支持按服务器名过滤：

```typescript
// src/tools/ListMcpResourcesTool/ListMcpResourcesTool.ts
export const ListMcpResourcesTool = buildTool({
  name: 'mcp__list_resources',
  isReadOnly: () => true,
  isConcurrencySafe: () => true,
  shouldDefer: true,  // 延迟加载，减少启动开销

  async call(input, { options: { mcpClients } }) {
    const clientsToProcess = input.server
      ? mcpClients.filter(c => c.name === input.server)
      : mcpClients

    // 对每个已连接的服务器获取资源（有 LRU 缓存）
    const results = await Promise.all(
      clientsToProcess.map(async client => {
        if (client.type !== 'connected') return []
        const fresh = await ensureConnectedClient(client)
        return await fetchResourcesForClient(fresh)
      }),
    )
    return { data: results.flat() }
  },
})
```

### 5.2 ReadMcpResourceTool

按 URI 读取特定资源，支持文本和二进制内容：

```typescript
// src/tools/ReadMcpResourceTool/ReadMcpResourceTool.ts
export const ReadMcpResourceTool = buildTool({
  name: 'ReadMcpResourceTool',
  isReadOnly: () => true,

  async call(input, { options: { mcpClients } }) {
    const client = mcpClients.find(c => c.name === input.server)
    const connectedClient = await ensureConnectedClient(client)

    const result = await connectedClient.client.request(
      { method: 'resources/read', params: { uri: input.uri } },
      ReadResourceResultSchema,
    )

    // 二进制内容（blob）→ 解码写入磁盘，返回文件路径
    // 文本内容 → 直接返回
    const contents = await Promise.all(
      result.contents.map(async (c, i) => {
        if ('text' in c) return { uri: c.uri, text: c.text }
        if ('blob' in c) {
          const persisted = await persistBinaryContent(
            Buffer.from(c.blob, 'base64'), c.mimeType, persistId,
          )
          return { uri: c.uri, blobSavedTo: persisted.filepath }
        }
      }),
    )
    return { data: { contents } }
  },
})
```

这两个资源工具只在至少一个已连接服务器声明了 `resources` 能力时才添加到工具列表中。

---

## 6. OAuth 认证

### 6.1 ClaudeAuthProvider

远程 MCP 服务器（SSE/HTTP）可能需要 OAuth 2.0 认证。Claude Code 实现了完整的 `OAuthClientProvider` 接口（`src/services/mcp/auth.ts`），名为 `ClaudeAuthProvider`：

```typescript
export class ClaudeAuthProvider implements OAuthClientProvider {
  // 凭据存储键 = serverName + config hash（防止同名不同配置混用）
  // 凭据通过 SecureStorage（macOS Keychain / 其他平台加密存储）持久化

  get clientMetadata(): OAuthClientMetadata {
    return {
      client_name: `Claude Code (${this.serverName})`,
      redirect_uris: [this.redirectUri],
      grant_types: ['authorization_code', 'refresh_token'],
      token_endpoint_auth_method: 'none',  // 公客户端
    }
  }

  // 凭据查找优先级：
  // 1. SecureStorage 中存储的 DCR 凭据
  // 2. 配置文件中预设的 clientId
  async clientInformation(): Promise<OAuthClientInformation | undefined> { ... }

  // Token 获取（每个请求都会调用）
  async tokens(): Promise<OAuthTokens | undefined> {
    // 特殊路径：XAA（Cross-App Access）可用缓存的 id_token 静默换取 access_token
    // 正常路径：从 SecureStorage 读取存储的 tokens
  }
}
```

### 6.2 Token 刷新

Token 刷新通过 `refreshTokens()` 方法实现，包含严谨的重试策略：

- **瞬态错误**（5xx、429、超时）：最多重试 3 次，指数退避
- **invalid_grant**：Token 被撤销，清除凭据，将服务器标记为 `needs-auth`
- **Slack 兼容**：某些服务器（如 Slack）用 HTTP 200 返回错误体，`normalizeOAuthErrorBody()` 将其标准化为 400

```typescript
// auth.ts - normalizeOAuthErrorBody
// Slack 返回 200 + {"error":"invalid_refresh_token"}
// 标准化为 400 + {"error":"invalid_grant"} 以便 SDK 正确处理
const NONSTANDARD_INVALID_GRANT_ALIASES = new Set([
  'invalid_refresh_token',
  'expired_refresh_token',
  'token_expired',
])
```

### 6.3 Step-up 认证

当 MCP 服务器返回 `403 insufficient_scope` 时，需要"权限升级"（Step-up）。`wrapFetchWithStepUpDetection` 在每个请求的 fetch 层拦截此响应：

```typescript
export function wrapFetchWithStepUpDetection(
  baseFetch: FetchLike,
  provider: ClaudeAuthProvider,
): FetchLike {
  return async (url, init) => {
    const response = await baseFetch(url, init)
    if (response.status === 403) {
      const wwwAuth = response.headers.get('WWW-Authenticate')
      if (wwwAuth?.includes('insufficient_scope')) {
        // 解析需要的 scope，标记 provider 进入 step-up 流程
        const match = wwwAuth.match(/scope=(?:"([^"]+)"|([^\s,]+))/)
        const scope = match?.[1] ?? match?.[2]
        if (scope) provider.markStepUpPending(scope)
      }
    }
    return response
  }
}
```

标记 step-up 后，`tokens()` 会省略 `refresh_token`，迫使 SDK 发起新的授权流程（因为 RFC 6749 禁止通过刷新提升 scope）。

### 6.4 McpAuthTool：模型驱动的认证

当 MCP 服务器处于 `needs-auth` 状态时，Claude Code 不是隐藏它，而是创建一个认证伪工具（`McpAuthTool`），让模型知道服务器存在并可以主动发起认证：

```typescript
// src/tools/McpAuthTool/McpAuthTool.ts
export function createMcpAuthTool(serverName, config): Tool {
  return {
    name: buildMcpToolName(serverName, 'authenticate'),
    description: `The ${serverName} MCP server is installed but requires authentication...`,

    async call(_input, context) {
      // 启动 OAuth 流程（后台），获取授权 URL
      const oauthPromise = performMCPOAuthFlow(
        serverName, config, onAuthorizationUrl, signal,
        { skipBrowserOpen: true },
      )
      const authUrl = await authUrlPromise
      // 返回 URL 让模型展示给用户
      return {
        data: {
          status: 'auth_url',
          authUrl,
          message: `Ask the user to open this URL...`,
        },
      }
      // 后台：OAuth 完成后自动重连，用前缀替换机制移除伪工具，换上真实工具
    },
  }
}
```

---

## 7. Elicitation 处理

### 7.1 什么是 Elicitation

Elicitation 是 MCP 协议的一种交互机制，允许服务器在工具调用过程中向用户请求额外输入（如表单填写或打开浏览器链接确认）。

### 7.2 Elicitation 注册

在 `connectToServer` 成功后，`registerElicitationHandler`（`elicitationHandler.ts`）为每个连接注册请求处理器：

```typescript
export function registerElicitationHandler(
  client: Client,
  serverName: string,
  setAppState: (f: (prev: AppState) => AppState) => void,
): void {
  client.setRequestHandler(ElicitRequestSchema, async (request, extra) => {
    // 1. 先尝试 hook 处理（可编程响应）
    const hookResponse = await runElicitationHooks(serverName, request.params, extra.signal)
    if (hookResponse) return hookResponse

    // 2. 加入 UI 队列，等待用户交互
    return new Promise<ElicitResult>(resolve => {
      setAppState(prev => ({
        ...prev,
        elicitation: {
          queue: [...prev.elicitation.queue, {
            serverName,
            params: request.params,
            respond: resolve,  // 用户操作后调用此函数
          }],
        },
      }))
    })
  })

  // 注册完成通知（URL 模式）
  client.setNotificationHandler(
    ElicitationCompleteNotificationSchema,
    notification => {
      // 找到匹配的队列项，标记 completed: true
    },
  )
}
```

### 7.3 错误码 -32042 重试

MCP 协议定义了特殊的错误码 `ErrorCode.UrlElicitationRequired`（-32042），表示工具调用需要用户先完成 URL 确认。`callMCPToolWithUrlElicitationRetry` 实现了自动重试：

```typescript
export async function callMCPToolWithUrlElicitationRetry({
  client, tool, args, signal, setAppState, handleElicitation, ...
}) {
  const MAX_URL_ELICITATION_RETRIES = 3
  for (let attempt = 0; ; attempt++) {
    try {
      return await callToolFn({ client, tool, args, signal })
    } catch (error) {
      // 只处理 -32042 错误
      if (!(error instanceof McpError) ||
          error.code !== ErrorCode.UrlElicitationRequired) {
        throw error
      }
      if (attempt >= MAX_URL_ELICITATION_RETRIES) throw error

      // 从错误数据中提取 elicitation 请求
      const elicitations = error.data.elicitations.filter(
        e => e.mode === 'url' && e.url && e.elicitationId && e.message
      )

      // 展示 URL 给用户，等待确认完成
      for (const elicitation of elicitations) {
        await handleElicitation(serverName, elicitation, signal)
      }
      // 循环回去重试工具调用
    }
  }
}
```

流程概览：

```
Claude 调用 MCP 工具
        │
        ▼
  服务器返回 -32042
  （附带 URL elicitation 列表）
        │
        ▼
  Claude Code 向用户展示 URL
  用户在浏览器完成操作
        │
        ▼
  服务器发送完成通知
        │
        ▼
  自动重试工具调用（最多 3 次）
```

---

## 8. MCP 工具权限

### 8.1 与内置工具共享权限体系

MCP 工具使用全限定名（如 `mcp__github__create_issue`）参与 Claude Code 的统一权限系统。用户可以在 settings.json 中对 MCP 工具设置 `allow` / `deny` 规则，语法与内置工具完全一致：

```json
{
  "permissions": {
    "deny": ["mcp__github__delete_repo"],
    "allow": ["mcp__github__*"]
  }
}
```

### 8.2 权限检查名称

`getToolNameForPermissionCheck()` 确保权限匹配使用全限定名，避免内置工具和 MCP 工具的名称冲突：

```typescript
// mcpStringUtils.ts
export function getToolNameForPermissionCheck(tool: {
  name: string
  mcpInfo?: { serverName: string; toolName: string }
}): string {
  // MCP 工具：用 mcp__server__tool 格式
  // 内置工具：直接用 tool.name
  return tool.mcpInfo
    ? buildMcpToolName(tool.mcpInfo.serverName, tool.mcpInfo.toolName)
    : tool.name
}
```

这意味着一个名为 `Write` 的 MCP 工具不会被针对内置 `Write` 工具的 deny 规则误伤——它的权限名是 `mcp__myserver__Write`。

### 8.3 首次使用授权

MCP 工具默认需要用户确认（`passthrough` 行为）。`checkPermissions()` 返回的建议会引导用户添加永久规则：

```typescript
async checkPermissions() {
  return {
    behavior: 'passthrough',
    message: 'MCPTool requires permission.',
    suggestions: [{
      type: 'addRules',
      rules: [{ toolName: fullyQualifiedName, ruleContent: undefined }],
      behavior: 'allow',
      destination: 'localSettings',
    }],
  }
}
```

### 8.4 服务器级 Allowlist/Denylist

除了工具级权限，服务器本身也受 `allowedMcpServers` / `deniedMcpServers` 策略约束（见 3.5 节）。被阻止的服务器在配置加载阶段就被过滤掉，其工具永远不会出现在 Claude 的可用工具列表中。

---

## 9. 设计模式总结

通过对 MCP 集成子系统的深入分析，可以提炼出以下核心设计模式：

### 9.1 Memoize + Cache Invalidation

连接（`connectToServer`）和工具/资源拉取（`fetchToolsForClient` 等）都使用 memoize/LRU 缓存。缓存键精心设计——连接用"名称+配置 JSON"，fetch 用"服务器名称"——在断线时通过 `onclose` 批量清除，实现自动重连。

### 9.2 Adapter Pattern（适配器模式）

`MCPTool` 是一个"空壳"工具定义，`fetchToolsForClient` 中通过对象展开（`{ ...MCPTool, name, call, ... }`）将每个 MCP 工具适配为 Claude Code 的内部 `Tool` 接口。这让 MCP 工具可以无缝参与权限检查、结果渲染、折叠分类等内部流程。

### 9.3 多层 Fetch 包装

远程连接的 fetch 函数经过多层包装，每层解决一个关注点：

```
globalThis.fetch
  → createFetchWithInit()          // MCP SDK 的 init 注入
    → wrapFetchWithStepUpDetection() // 403 scope 升级检测
      → wrapFetchWithTimeout()       // 60 秒超时（GET 除外）
```

对 claude.ai 代理连接还有额外的 `createClaudeAiProxyFetch()`：注入 Bearer token、401 自动刷新重试。

### 9.4 渐进式降级

MCP 系统在多处体现了"尽力而为"的容错哲学：

- 连接超时/失败 → 标记为 `failed`，不影响其他服务器
- Token 刷新失败 → 降级为 `needs-auth`，创建认证伪工具
- 大结果持久化失败 → 回退到截断
- 认证缓存写入失败 → 静默忽略（best-effort cache）
- 单个服务器资源获取失败 → 不影响 ListMcpResourcesTool 整体返回

### 9.5 安全边界

MCP 集成严守安全边界：

- **项目级 .mcp.json** 需要用户批准（`getProjectMcpServerStatus() === 'approved'`）
- **OAuth 参数**（state、code、nonce）在日志中统一脱敏
- **企业策略** 可以完全接管 MCP 服务器列表（enterprise 模式下忽略所有其他来源）
- **全限定名** 防止 MCP 工具伪装内置工具绕过 deny 规则
- **描述长度限制** 防止恶意服务器通过超长描述注入上下文（`MAX_MCP_DESCRIPTION_LENGTH = 2048`）

---

以上就是 Claude Code MCP 集成子系统的完整架构解读。这个子系统是 Claude Code 最复杂的模块之一——它将一个开放协议的灵活性与生产级工具的可靠性、安全性需求巧妙地融合在一起，值得反复研读。
