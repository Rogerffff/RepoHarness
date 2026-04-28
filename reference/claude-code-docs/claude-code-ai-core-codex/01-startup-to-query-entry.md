# 从启动入口到 Query 入口

## 这篇解决什么问题

这篇只回答一个问题：Claude Code 是如何从进程入口一路走到真正的模型执行入口的。

这里最重要的不是 UI，而是“谁在什么时候决定了这次会话的模型、工具、权限、MCP、session 状态，以及最后到底是进入 `query()` 还是进入 `QueryEngine`”。

## 核心类型与职责

本篇重点关注 4 个对象：

| 名称 | 作用 |
| --- | --- |
| `Command` | 用于描述 slash command/技能/本地命令的统一结构 |
| `ToolPermissionContext` | 启动阶段整理好的权限模式、规则和额外工作目录 |
| `ToolUseContext` | 进入 query 前为工具系统准备好的运行时上下文 |
| `QueryEngineConfig` | headless/SDK 模式下长期保留的会话配置 |

从文件职责看，启动主链大致分成 5 层：

| 文件 | 角色 |
| --- | --- |
| `src/entrypoints/cli.tsx` | 极薄入口，优先拦截 fast path |
| `src/main.tsx` | 真正的装配中心 |
| `src/entrypoints/init.ts` | 安全初始化与全局环境准备 |
| `src/setup.ts` | 会话级 setup，补全 cwd/worktree/hooks/background state |
| `src/query.ts` / `src/QueryEngine.ts` | 模型执行入口 |

## 关键源码

- `src/entrypoints/cli.tsx`
- `src/main.tsx`
- `src/entrypoints/init.ts`
- `src/setup.ts`
- `src/query.ts`
- `src/QueryEngine.ts`
- `src/utils/queryContext.ts`

## 控制流分步讲解

### 1. `cli.tsx` 先把“无需完整启动”的路径拦掉

`src/entrypoints/cli.tsx` 的思路很明确：入口必须尽量薄。

它先做几件极早期动作：

- 修正 `COREPACK_ENABLE_AUTO_PIN`
- 在 remote 场景下注入 `NODE_OPTIONS`
- 根据 feature flag 设置某些环境变量

然后它先判断一批 fast path：

- `--version`
- `--dump-system-prompt`
- 若干 MCP server 模式
- daemon / bridge / background session / templates / self-hosted runner

这些路径的共同点是：

- 不需要完整的 REPL 与 query 运行时
- 不应该支付 `main.tsx` 的整套装配成本

如果命中这些 fast path，程序会直接退出，不会进入主 query 链。

### 2. `main.tsx` 是真正的装配中心

未命中 fast path 时，`cli.tsx` 才会加载 `src/main.tsx`。

`main.tsx` 负责做三类高价值工作：

1. 标准化命令行输入
2. 决定这次会话属于哪一种运行模式
3. 在进入 query 前把模型宿主所需的一切都拼好

它会处理的事情包括：

- 解析 `--print`、`--resume`、`--sdk-url`、`--permission-mode`
- 识别 interactive 还是 non-interactive
- 初始化 settings、policy、auth、remote flags
- 提前准备 commands、tools、agents、MCP config
- 决定是走本地交互 REPL、headless/SDK、remote、SSH 还是 direct connect

这里有一个关键理解：

`main.tsx` 并不直接“运行模型”，它负责把模型运行所需的宿主环境拼好。

### 3. `init.ts` 解决的是“安全初始化”，不是“业务初始化”

`src/entrypoints/init.ts` 的职责是 process 级初始化。

它做的事情偏底层，但它们会直接影响后续模型执行是否正确：

- 启用配置系统
- 在 trust 建立前仅应用 safe env vars
- 提前设置 CA 证书
- 注册 graceful shutdown
- 初始化代理、mTLS、预连接
- 启动 remote settings / policy limits 的加载 promise

从 AI 交互视角，最重要的设计点有两个：

1. trust 是一个独立边界
2. safe env 与 full env 分阶段应用

这说明 Claude Code 不把“能否调模型”和“能否无条件信任当前工作区”混在一起。

### 4. `setup.ts` 进入会话级装配

如果说 `init.ts` 面向整个进程，那么 `setup.ts` 面向“当前这次会话”。

`src/setup.ts` 会把 session 相关的状态钉下来，例如：

- 当前 cwd 与 project root
- worktree 模式
- hooks 快照
- background jobs
- sink / analytics / watcher
- 某些缓存与派生状态

这里最重要的是：到 `setup()` 结束时，这次会话的“运行边界”基本确定了。

也就是说，从这里开始：

- 模型要在哪个目录工作
- 工具被允许看到哪些目录
- 当前 session 的 hooks 与 background 机制是什么

这些都已经是稳定状态。

### 5. 进入两条不同的 query 入口

接下来会分成两条主线。

#### 5.1 interactive 路径

interactive 模式最终会进入本地 REPL，随后由 REPL 调用 `query()`。

这里真正重要的不是 REPL UI，而是它作为“活的会话壳”：

- 持有当前消息列表
- 合并本地 tools 与 MCP tools
- 处理 slash commands
- 准备 `ToolUseContext`
- 在用户提交输入后进入 `query()`

也就是说，interactive 模式本质上是：

`UI 壳 + 实时会话状态 + query()`

#### 5.2 headless / SDK 路径

headless 模式则不依赖 REPL，它会构造 `QueryEngine`。

`QueryEngine` 是一个面向长期会话的对象，它把这些状态保留在实例里：

- `mutableMessages`
- `permissionDenials`
- `readFileState`
- `totalUsage`
- 一些 session 级追踪状态

然后在 `submitMessage()` 中：

- 组装 system prompt parts
- 调用 `processUserInput`
- 维护 transcript
- 最终进入 `query()`

所以更准确地说：

- `query()` 是单次 turn 的核心循环
- `QueryEngine` 是 headless/SDK 会话的宿主

## 一张简化主链图

```text
cli.tsx
  -> main.tsx
    -> init()
    -> setup()
    -> interactive ? REPL -> query()
    -> headless    ? QueryEngine.submitMessage() -> query()
```

## 关键设计权衡

### 1. 入口必须薄

`cli.tsx` 尽量只做分流，不做重活。这样可以保证：

- 简单命令足够快
- 某些 server/worker 模式不会被无关模块拖慢
- feature-gated 能力可以通过动态 import 延后加载

### 2. `main.tsx` 统一装配，而不是到处分散初始化

这会带来一个明显好处：所有和模型执行有关的核心状态都在进入 query 前被一次性装配。

代价是 `main.tsx` 会非常大，但收益是控制流清晰。

### 3. `query()` 被设计成共享核心

交互式与 headless 并没有各写一套模型循环，而是共享 `query()`。

这样做的好处是：

- tool_use 处理逻辑统一
- compact、continuation、budget、tool_result 规则统一
- 不同 shell 只需要关心“怎么进来”，不用重写“怎么跑”

## 易错点与误解

### 误解 1：REPL 是系统核心

不是。REPL 是 interactive 宿主壳，真正的模型主循环在 `query()`。

### 误解 2：`init()` 做完就能跑模型

不够。`init()` 只是 process 级安全初始化，真正会话级上下文还要靠 `setup()` 和 `main.tsx` 后续装配。

### 误解 3：`QueryEngine` 替代了 `query()`

不是。`QueryEngine` 包住的是会话管理；`query()` 才是 turn 级对话循环。

### 误解 4：interactive 与 headless 是两套完全独立系统

也不是。它们在入口壳不同，但执行核心共享。

## 继续阅读建议

下一篇看 [02-dialogue-engine-and-context.md](./02-dialogue-engine-and-context.md)。那里会进入真正的 AI 主循环：用户输入怎么变成消息、上下文怎么拼到模型请求里、tool_result 又是怎么回流成下一轮对话的。
