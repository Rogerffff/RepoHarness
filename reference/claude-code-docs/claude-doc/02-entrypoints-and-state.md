# 第 2 篇：入口、启动与状态管理

## 1. 概述

Claude Code 的启动流程是一个精心设计的多阶段管线。从用户在终端键入 `claude` 到 REPL 界面渲染完成，代码经历了**快速路径分流 → memoized 单例初始化 → CLI 解析与编排 → React 状态树挂载**四个核心阶段。整个设计追求两个目标：

- **极致的首字节延迟**：对 `--version` 等轻量命令做到零模块加载；对主流程通过并行预取、延迟导入（dynamic import）和预连接（preconnect）将感知延迟压到最低。
- **双层状态分离**：进程级不可变状态（Bootstrap State）与 React 响应式状态（AppState）各司其职，既满足底层模块对全局状态的同步读取需求，又让 UI 层享受细粒度的响应式更新。

涉及的关键文件：

| 文件 | 职责 |
|------|------|
| `src/entrypoints/cli.tsx` | CLI 入口，快速路径分流 |
| `src/main.tsx` | 主编排器（~4600 行），Commander 解析 → 初始化 → REPL 启动 |
| `src/entrypoints/init.ts` | memoized 单例初始化（mTLS、代理、预连接、遥测） |
| `src/bootstrap/state.ts` | Bootstrap 全局状态（进程级） |
| `src/state/store.ts` | 轻量级 Store 实现（类 Zustand） |
| `src/state/AppStateStore.ts` | AppState 类型定义与默认值 |
| `src/state/AppState.tsx` | React Context 绑定与 `useAppState` hook |
| `src/components/App.tsx` | React Context Provider 树根节点 |

---

## 2. CLI 入口快速路径设计详解

`src/entrypoints/cli.tsx` 是整个 CLI 的第一个执行入口。它的核心设计理念是：**所有 import 都是动态的，按需加载**。

### 2.1 零导入快速路径

文件顶部只有编译期宏和环境变量设置，没有任何模块导入：

```typescript
// src/entrypoints/cli.tsx
async function main(): Promise<void> {
  const args = process.argv.slice(2);

  // 快速路径：--version 不加载任何模块
  if (args.length === 1 && (args[0] === '--version' || args[0] === '-v')) {
    // MACRO.VERSION 在构建时内联
    console.log(`${MACRO.VERSION} (Claude Code)`);
    return;  // 直接返回，零模块开销
  }

  // 其他路径才开始加载 profiler
  const { profileCheckpoint } = await import('../utils/startupProfiler.js');
  profileCheckpoint('cli_entry');
  // ...
}
```

`--version` 路径的模块加载量为零——连 startupProfiler 都不需要。这是启动性能优化的极端体现。

### 2.2 分层快速路径

在加载 profiler 之后，cli.tsx 按优先级依次检查各种快速路径子命令，每条路径只动态导入自己需要的模块：

```
--version          → 零导入，直接输出
--dump-system-prompt → 仅加载 config + prompts
--daemon-worker    → 仅加载 worker registry
remote-control     → 加载 bridge 模块
daemon             → 加载 daemon 主模块
ps/logs/attach/kill → 加载 bg sessions 模块
new/list/reply     → 加载 template jobs
```

所有快速路径命中后立即 `return`，不会继续加载 main.tsx 的 ~4600 行代码。

### 2.3 落入主流程

当没有任何快速路径命中时，才加载完整的主程序：

```typescript
// 没有特殊标志，加载完整 CLI
const { startCapturingEarlyInput } = await import('../utils/earlyInput.js');
startCapturingEarlyInput();  // 开始捕获用户在加载期间的键入

const { main: cliMain } = await import('../main.js');
await cliMain();  // 进入主编排器
```

值得注意的是 `startCapturingEarlyInput()`：它在主模块加载之前就开始监听键盘输入，这样用户在等待加载时键入的内容不会丢失。

---

## 3. main.tsx 主编排器深度分析

`src/main.tsx` 是整个应用的指挥中枢，约 4600 行代码。它的执行分为三个阶段：

### 3.1 阶段一：预初始化与模式检测

`main()` 函数首先进行安全设置和模式检测：

```typescript
export async function main() {
  // 安全：防止 Windows 从当前目录执行命令
  process.env.NoDefaultCurrentDirectoryInExePath = '1';

  // 检测是否为非交互模式（-p/--print、--init-only、--sdk-url、非 TTY）
  const isNonInteractive = hasPrintFlag || hasInitOnlyFlag || hasSdkUrl || !process.stdout.isTTY;

  // 非交互模式下停止捕获早期输入
  if (isNonInteractive) {
    stopCapturingEarlyInput();
  }

  // 设置 client type（cli / sdk-typescript / remote / github-action 等）
  setClientType(clientType);
}
```

模式检测是全局性的决策点——它影响后续的遥测初始化、权限模型、输出格式等行为。

### 3.2 阶段二：Commander 解析与 preAction Hook

main.tsx 使用 Commander.js 构建命令行解析器。关键设计是利用 `preAction` hook 将初始化逻辑延迟到命令实际执行时：

```typescript
program.hook('preAction', async thisCommand => {
  // 1. 等待 MDM 设置和 Keychain 预取完成
  await Promise.all([ensureMdmSettingsLoaded(), ensureKeychainPrefetchCompleted()]);

  // 2. 运行 memoized 单例初始化（详见第 4 节）
  await init();

  // 3. 挂载日志 sink
  initSinks();

  // 4. 运行迁移
  runMigrations();

  // 5. 非阻塞加载远程管理设置
  void loadRemoteManagedSettings();
  void loadPolicyLimits();
});
```

这意味着当用户运行 `claude --help` 时，`preAction` 不会执行，初始化完全跳过。

### 3.3 阶段三：Action Handler → setup() → launchRepl()

Commander 的 `.action()` 回调是主要的业务逻辑入口，约占 main.tsx 的 70%。核心流程：

```
action handler 开始
  ├── 检测 Assistant/Kairos 模式
  ├── 解析大量 CLI 选项（model、tools、permissions 等）
  ├── setup()：信任对话框、worktree、权限模式
  ├── 并行加载 commands 和 agent definitions
  ├── 构建 initialState（AppState 的初始值）
  ├── 根据模式分支：
  │   ├── print 模式 → 直接执行 query，输出结果
  │   ├── --resume/--continue → 加载历史会话
  │   ├── SSH/Direct Connect → 建立远程连接
  │   └── 交互模式 → launchRepl()
  └── 启动延迟预取（startDeferredPrefetches）
```

`setup()` 与 commands 加载被巧妙地并行化：

```typescript
// setup() 耗时 ~28ms（主要是 socket bind），不与 getCommands 的文件读取竞争
const setupPromise = setup(preSetupCwd, permissionMode, ...);
const commandsPromise = worktreeEnabled ? null : getCommands(preSetupCwd);
const agentDefsPromise = worktreeEnabled ? null : getAgentDefinitionsWithOverrides(preSetupCwd);

await setupPromise;
const [commands, agentDefinitions] = await Promise.all([
  commandsPromise ?? getCommands(currentCwd),
  agentDefsPromise ?? getAgentDefinitionsWithOverrides(currentCwd),
]);
```

最终通过 `launchRepl()` 将 React 组件树挂载到 Ink 终端渲染器：

```typescript
// src/replLauncher.tsx
export async function launchRepl(root, appProps, replProps, renderAndRun) {
  const { App } = await import('./components/App.js');
  const { REPL } = await import('./screens/REPL.js');
  await renderAndRun(root, <App {...appProps}><REPL {...replProps} /></App>);
}
```

---

## 4. init.ts：memoized 单例初始化

`src/entrypoints/init.ts` 导出一个用 `lodash.memoize` 包裹的 `init()` 函数，确保整个进程生命周期内只执行一次：

```typescript
export const init = memoize(async (): Promise<void> => {
  // 1. 启用配置系统
  enableConfigs();

  // 2. 应用安全环境变量（信任对话框之前的安全子集）
  applySafeConfigEnvironmentVariables();

  // 3. 应用 NODE_EXTRA_CA_CERTS（必须在首次 TLS 握手之前）
  applyExtraCACertsFromConfig();

  // 4. 设置优雅退出处理
  setupGracefulShutdown();

  // 5. 异步初始化分析和事件日志（fire-and-forget）
  void Promise.all([
    import('../services/analytics/firstPartyEventLogger.js'),
    import('../services/analytics/growthbook.js'),
  ]).then(([fp, gb]) => { fp.initialize1PEventLogging(); });

  // 6. 配置 mTLS
  configureGlobalMTLS();

  // 7. 配置全局 HTTP 代理
  configureGlobalAgents();

  // 8. 预连接 Anthropic API（重叠 TCP+TLS 握手 ~100-200ms）
  preconnectAnthropicApi();
});
```

### 关键设计决策

- **memoize 保证幂等**：无论被调用多少次，初始化逻辑只跑一次。preAction hook、子命令、setup 都可以安全地 `await init()`。
- **CA 证书必须最早应用**：Bun 在启动时缓存 TLS 证书存储，所以 `applyExtraCACertsFromConfig()` 必须在任何 TLS 连接之前执行。
- **遥测延迟加载**：OpenTelemetry + protobuf 约 400KB，gRPC 约 700KB——通过 `import()` 延迟到遥测真正初始化时才加载。
- **预连接策略**：`preconnectAnthropicApi()` 在 mTLS 和代理配置完成后执行，将 TCP+TLS 握手（~100-200ms）与后续 ~100ms 的 action handler 工作重叠。

遥测初始化在信任对话框之后单独触发：

```typescript
export function initializeTelemetryAfterTrust(): void {
  if (isEligibleForRemoteManagedSettings()) {
    // 等待远程设置加载，然后初始化遥测
    void waitForRemoteManagedSettingsToLoad()
      .then(async () => {
        applyConfigEnvironmentVariables();  // 应用完整环境变量
        await doInitializeTelemetry();
      });
  } else {
    void doInitializeTelemetry();
  }
}
```

---

## 5. 双层状态架构

Claude Code 采用两层状态管理，各自服务于不同的消费者。

### 5.1 Bootstrap State（进程级不可变状态）

定义在 `src/bootstrap/state.ts`，是一个普通的 JavaScript 模块闭包：

```typescript
// 模块级单例——进程启动时立即创建
const STATE: State = getInitialState();

// 通过 getter/setter 函数暴露，不提供 subscribe 机制
export function getSessionId(): SessionId { return STATE.sessionId; }
export function getCwdState(): string { return STATE.cwd; }
export function setCwdState(cwd: string): void { STATE.cwd = cwd.normalize('NFC'); }
export function addToTotalCostState(cost, modelUsage, model): void {
  STATE.modelUsage[model] = modelUsage;
  STATE.totalCostUSD += cost;
}
```

**核心特征**：

- **同步读写**：getter/setter 是纯同步函数，任何模块都可以在 import 后立即使用，无需 Context 或 Provider。
- **进程生命周期**：从 `getInitialState()` 到进程退出，状态只有一份。
- **无响应式通知**：修改不会触发 UI 重新渲染——这是有意为之的设计。
- **模块 DAG 叶节点**：bootstrap/state.ts 位于 import 依赖图的最底层，避免循环依赖。

State 类型包含约 80 个字段，涵盖：

| 类别 | 典型字段 |
|------|---------|
| 会话标识 | `sessionId`, `parentSessionId`, `clientType` |
| 路径信息 | `originalCwd`, `projectRoot`, `cwd` |
| 成本与性能 | `totalCostUSD`, `totalAPIDuration`, `totalToolDuration` |
| 遥测计数器 | `meter`, `sessionCounter`, `locCounter`, `costCounter` |
| 模型配置 | `mainLoopModelOverride`, `initialMainLoopModel`, `modelStrings` |
| 缓存与标志 | `cachedClaudeMdContent`, `promptCache1hEligible`, 各种 header latch |

文件顶部的注释一针见血：`// DO NOT ADD MORE STATE HERE - BE JUDICIOUS WITH GLOBAL STATE`。

### 5.2 AppState（React 响应式状态）

定义在 `src/state/AppStateStore.ts`，是 React 组件树的状态中心。

```typescript
// 用 DeepImmutable 包裹确保不可变性
export type AppState = DeepImmutable<{
  settings: SettingsJson;
  verbose: boolean;
  mainLoopModel: ModelSetting;
  toolPermissionContext: ToolPermissionContext;
  kairosEnabled: boolean;
  thinkingEnabled: boolean | undefined;
  // ... 100+ 字段
}> & {
  // 部分字段因包含函数类型而排除在 DeepImmutable 之外
  tasks: { [taskId: string]: TaskState };
  mcp: { clients: MCPServerConnection[]; tools: Tool[]; ... };
  plugins: { enabled: LoadedPlugin[]; ... };
};
```

AppState 涵盖了 UI 层需要响应的一切：MCP 连接状态、插件列表、任务状态、推测执行、bridge 连接、团队协作等。

**Store 实现**（`src/state/store.ts`）极其精简——仅 34 行代码，是 Zustand 模式的最小实现：

```typescript
export function createStore<T>(initialState: T, onChange?: OnChange<T>): Store<T> {
  let state = initialState;
  const listeners = new Set<Listener>();

  return {
    getState: () => state,
    setState: (updater: (prev: T) => T) => {
      const prev = state;
      const next = updater(prev);
      if (Object.is(next, prev)) return;  // 引用相等则跳过
      state = next;
      onChange?.({ newState: next, oldState: prev });
      for (const listener of listeners) listener();
    },
    subscribe: (listener: Listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
  };
}
```

核心设计：
- **`Object.is` 短路**：updater 返回相同引用时不触发任何通知。
- **`onChange` 回调**：用于副作用（如 `onChangeAppState` 同步 bootstrap state）。
- **无中间件、无 devtools**：极致轻量。

### 5.3 useAppState Hook

`src/state/AppState.tsx` 提供了类 Zustand 的 selector hook：

```typescript
/**
 * 订阅 AppState 的某个切片。仅当 selector 返回值变化（Object.is 比较）时重新渲染。
 *
 * 用法：
 *   const verbose = useAppState(s => s.verbose);
 *   const model = useAppState(s => s.mainLoopModel);
 *
 * 注意：不要在 selector 中返回新对象——Object.is 会认为它总是变化了。
 */
export function useAppState<T>(selector: (state: AppState) => T): T {
  const store = useAppStore();
  // 使用 useSyncExternalStore 确保与 React 并发模式兼容
  return useSyncExternalStore(store.subscribe, () => selector(store.getState()));
}
```

---

## 6. React Context Provider 树

`src/components/App.tsx` 是 Provider 树的根：

```
<FpsMetricsProvider>           ← 帧率监控
  <StatsProvider>              ← 统计计数器（histogram、reservoir sampling）
    <AppStateProvider>         ← 核心应用状态
      <HasAppStateContext>     ← 防止嵌套（开发期保护）
        <AppStoreContext>      ← Store 实例注入
          <MailboxProvider>    ← 消息队列（agent 间通信）
            <VoiceProvider>    ← 语音模式（ant-only，外部构建为 passthrough）
              {children}       ← REPL 组件
            </VoiceProvider>
          </MailboxProvider>
        </AppStoreContext>
      </HasAppStateContext>
    </AppStateProvider>
  </StatsProvider>
</FpsMetricsProvider>
```

`AppStateProvider` 内部的 `HasAppStateContext` 是一个布尔 Context，用于在开发期检测 Provider 嵌套错误：

```typescript
const hasAppStateContext = useContext(HasAppStateContext);
if (hasAppStateContext) {
  throw new Error("AppStateProvider can not be nested within another AppStateProvider");
}
```

此外，`AppStateProvider` 在挂载时还会监听设置文件变更（`useSettingsChange`），通过 `applySettingsChange` 热更新 AppState 中的 `settings` 字段。

---

## 7. SDK 入口与 Headless 模式

Claude Code 支持多种 headless（非交互）入口：

### 7.1 --print 模式

通过 `-p`/`--print` 标志启动，跳过 REPL，直接执行一次查询并输出结果。支持三种输出格式：
- `text`（默认）
- `json`（单次 JSON 结果）
- `stream-json`（实时流式 JSON）

### 7.2 --sdk-url 模式

当提供 `--sdk-url` 时，自动启用 `stream-json` 输入输出、verbose 和 print 模式。这是 Agent SDK（TypeScript/Python）与 Claude Code 进程通信的标准方式。

### 7.3 SDK 类型系统

`src/entrypoints/sdk/` 目录定义了 SDK 的类型契约：
- `coreTypes.ts`：从 Zod schema 生成的核心类型（通过 `bun scripts/generate-sdk-types.ts`）
- `coreSchemas.ts`：Zod schema 定义，用于运行时验证
- `controlSchemas.ts`：控制消息的 schema

SDK 暴露的 Hook 事件类型涵盖了完整的生命周期：`PreToolUse`、`PostToolUse`、`SessionStart`、`SessionEnd`、`Stop`、`PermissionRequest` 等。

### 7.4 Client Type 检测

main.tsx 根据环境变量检测入口来源：

```typescript
const clientType = (() => {
  if (process.env.CLAUDE_CODE_ENTRYPOINT === 'sdk-ts') return 'sdk-typescript';
  if (process.env.CLAUDE_CODE_ENTRYPOINT === 'sdk-py') return 'sdk-python';
  if (process.env.CLAUDE_CODE_ENTRYPOINT === 'claude-vscode') return 'claude-vscode';
  if (process.env.CLAUDE_CODE_ENTRYPOINT === 'remote') return 'remote';
  return 'cli';
})();
```

---

## 8. 启动并行预取策略

Claude Code 的启动优化可以分为两个阶段的并行策略：

### 8.1 启动期并行（init 阶段）

在 `init()` 内部，多个网络和 I/O 操作以 fire-and-forget 方式并行启动：

```
init() 同步执行:
  enableConfigs() → applySafeConfigEnvironmentVariables() → configureGlobalMTLS() → configureGlobalAgents()

init() fire-and-forget:
  ├── populateOAuthAccountInfoIfNeeded()     ← OAuth 信息填充
  ├── initJetBrainsDetection()               ← IDE 检测
  ├── detectCurrentRepository()              ← Git 仓库检测
  ├── preconnectAnthropicApi()               ← TCP+TLS 预连接
  └── initialize1PEventLogging()             ← 分析事件日志
```

### 8.2 首次渲染后预取（startDeferredPrefetches）

在 REPL 组件首次渲染完成后，启动不影响首屏的后台工作：

```typescript
export function startDeferredPrefetches(): void {
  // 利用用户打字的时间窗口预取
  void initUser();                      // 用户信息
  void getUserContext();                 // CLAUDE.md 内容
  prefetchSystemContextIfSafe();        // git status/log/branch
  void getRelevantTips();               // 提示信息
  void countFilesRoundedRg(...);        // 文件计数
  void initializeAnalyticsGates();      // 分析功能门控
  void refreshModelCapabilities();      // 模型能力刷新
  void settingsChangeDetector.initialize();  // 设置文件监听
  void skillChangeDetector.initialize();     // 技能文件监听
}
```

注释中解释了这一设计的动机：这些预取发生在 "用户正在打字" 的时间窗口内，到用户按下回车发送第一条消息时，所有上下文数据已经准备就绪。

### 8.3 非交互模式的激进预取

在 `-p` 模式下，因为没有 "用户打字" 的时间窗口，main.tsx 在 `setup()` 完成后立即触发预取：

```typescript
if (getIsNonInteractiveSession()) {
  applyConfigEnvironmentVariables();
  void getSystemContext();           // 立即启动 git 子进程
  void getUserContext();             // 立即启动 CLAUDE.md 读取
  void ensureModelStringsInitialized();  // Bedrock profile 预取
}
```

---

## 9. 设计模式总结

| 模式 | 应用位置 | 目的 |
|------|----------|------|
| **快速路径分流** | cli.tsx | 轻量命令零开销，动态 import 按需加载 |
| **memoize 单例** | init.ts | 全局初始化幂等，多调用点安全 |
| **preAction Hook** | main.tsx Commander | 帮助输出不触发初始化 |
| **双层状态** | bootstrap/state + AppState | 底层同步 vs. UI 响应式 |
| **Selector Hook** | useAppState | 细粒度渲染——仅订阅所需切片 |
| **fire-and-forget 并行** | init.ts, main.tsx | 非阻塞预热网络、缓存、子进程 |
| **延迟遥测加载** | init.ts | 400KB+ OpenTelemetry 按需导入 |
| **预连接** | preconnectAnthropicApi | TCP+TLS 握手与业务逻辑重叠 |
| **Provider 防嵌套** | AppStateProvider | HasAppStateContext 布尔守卫 |
| **build-time DCE** | feature() 门控 | 外部构建裁剪内部功能（voice、daemon 等） |

这些模式共同构成了一个启动快、响应灵敏、架构清晰的 CLI 应用框架。Bootstrap State 保证了底层模块（工具执行、API 调用、遥测）的无依赖状态访问；AppState + Store + React Context 则为终端 UI 提供了现代前端级别的状态管理体验。
