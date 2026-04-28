# AgentTool、任务系统与远程执行

## 这篇解决什么问题

这篇要回答的是 Claude Code 最“agentic”的那部分：

1. 主 agent 如何派生子 agent
2. 为什么 `AgentTool` 不等于真正的 agent 执行器
3. 本地、后台、远程、teammate 这几种 agent 到底有什么差别
4. 子 agent 的结果是怎样重新汇回主对话的

如果说前两篇讲的是“Claude Code 怎样和模型对话”，这一篇讲的是“Claude Code 怎样让一个模型驱动多个执行体协作”。

## 核心类型与职责

本篇最重要的类型如下：

| 类型 | 作用 |
| --- | --- |
| `AgentDefinition` | 一个 agent 类型的声明，包括模型、权限模式、frontmatter 能力等 |
| `LocalAgentTaskState` | 本地 agent 在 `AppState.tasks` 里的状态 |
| `RemoteAgentTaskState` | 远程 agent 在本地侧的镜像状态 |
| `ToolUseContext` | 父 agent 传给子 agent 的运行时上下文骨架 |
| `AgentToolResult` | `AgentTool` 对外暴露的结果结构 |

要先建立一个关键分层：

- `AgentTool` 是“启动与编排层”
- `runAgent()` 是“真正的子 agent 执行循环”
- `Task` 系统是“长期状态托管层”

## 关键源码

- `src/tools/AgentTool/AgentTool.tsx`
- `src/tools/AgentTool/runAgent.ts`
- `src/tools/AgentTool/agentToolUtils.ts`
- `src/tools/AgentTool/loadAgentsDir.ts`
- `src/tasks/LocalAgentTask/LocalAgentTask.tsx`
- `src/tasks/RemoteAgentTask/RemoteAgentTask.tsx`
- `src/tasks/InProcessTeammateTask/InProcessTeammateTask.tsx`
- `src/utils/swarm/inProcessRunner.ts`
- `src/utils/teleport.ts`
- `src/tools/SendMessageTool/SendMessageTool.ts`

## `AgentTool` 负责决策，不负责真正执行

最容易误解的一点是把 `AgentTool` 看成“子 agent 本体”。

更准确的理解是：

`AgentTool` 是一个给主模型调用的编排工具。

它做的事情包括：

- 根据 `AgentDefinition` 过滤可用 agent
- 判断当前是 sync 还是 async
- 判断是否走 remote
- 判断是否创建 worktree
- 决定注册哪种 task
- 决定结果是前台返回、后台通知、还是远程 URL

它本身并不实现完整子 agent loop。

真正运行子 agent 的，是 `runAgent()`。

## `runAgent()` 才是子 agent 的执行器

`src/tools/AgentTool/runAgent.ts` 是理解 Claude Code 多 agent 架构的关键文件。

它做的事情可以概括为：

1. 选定最终模型
2. 创建子 agent id
3. 准备初始消息
4. 克隆或新建 read file cache
5. 组装子 agent 的 user/system context
6. 按 agent 定义覆盖权限模式
7. 初始化 agent-specific MCP servers
8. 创建 subagent context
9. 调用 `query()`
10. 把子 agent 产生的消息记录到 transcript / sidechain

因此，`runAgent()` 的本质是：

“在父 agent 的宿主内，再构造一个缩小版但独立的 query 运行时”

## 控制流分步讲解

从主 agent 视角看，一条典型多 agent 主链是：

1. 主模型调用 `AgentTool`。
2. `AgentTool` 选择 sync / async / remote / teammate 路径。
3. 若需要长期托管，先注册 task state。
4. `runAgent()` 组装子 agent 的模型、上下文、权限和工具池。
5. 子 agent 进入同一个 `query()` 主循环。
6. 生命周期管理器把进度、日志、结果写回 task state。
7. 结果通过直接返回或 `task-notification` 回到主线程。

## 为什么子 agent 不是简单复用父上下文

源码显示，子 agent 既继承父上下文，又会主动裁剪或改写某些部分。

典型例子：

- 会克隆 `readFileState`
- 某些只读 agent 会裁掉 `claudeMd`
- Explore/Plan agent 会裁掉 `gitStatus`
- agent 定义可以覆盖 permission mode
- agent frontmatter 还可以附带自己的 MCP servers

这说明 Claude Code 不是把子 agent 当成“同一个 agent 的另一个线程”，而是把它当成：

一个共享部分状态、但拥有自己 prompt 边界与工具边界的独立执行体。

## 本地子 agent 的两种主要形态

### 1. 同步本地 agent

同步本地 agent 的特点是：

- 当前主对话阻塞等待结果
- 生命周期较短
- 结果直接回到当前对话

这个路径通常适合：

- 短时探索
- 单次验证
- 需要立即消费结果的委派任务

### 2. 异步本地 agent

异步路径会注册 `LocalAgentTaskState`，由后台生命周期托管。

这条路的关键动作包括：

- `registerAsyncAgent()`
- `runAsyncAgentLifecycle()`
- 进度更新
- 结束时发出 `task-notification`

异步路径的关键产物不是“一段立刻可见的文本”，而是：

- 一个 task id
- 一个输出文件
- 一条会回流主对话的通知

## `LocalAgentTaskState` 为什么重要

`LocalAgentTaskState` 并不只是 UI 状态。

从 AI 交互视角，它承担这些职责：

- 持有 agent 的长期身份
- 跟踪 prompt 与 selected agent
- 持有 abort controller
- 累积 progress
- 持有 messages 与 pendingMessages
- 决定这个 agent 是 foreground 还是 backgrounded

这意味着 Claude Code 并不是把异步 agent 当“fire and forget job”，而是把它当“可继续对话、可恢复、可查看 transcript 的长期 actor”。

## `task-notification` 是怎样把结果送回主对话的

本地后台 agent 完成后，不是直接把一段自然语言强塞回主上下文。

它更常见的做法是发出结构化的 XML 风格通知，例如：

- `task id`
- `status`
- `summary`
- `output file`
- 可选 usage 与 worktree 信息

主线程收到这条 `task-notification` 后，再把它作为用户侧系统通知消息处理。

这一设计非常关键，因为它把：

- “后台 agent 的内部 transcript”
- “主 agent 需要知道的摘要事件”

明确分开了。

## `SendMessage` 为什么是关键续航点

如果只有 spawn，没有继续通信，多 agent 很快就会退化成一次性函数调用。

`SendMessageTool` 正是 Claude Code 防止这种退化的关键。

它可以做几件事：

- 给运行中的 local agent 追加消息
- 恢复已停下的 agent 并继续后台运行
- 给 teammate mailbox 发送消息
- 给某些 bridge / peer 地址发送消息

所以 `SendMessage` 不是边角工具，而是让 agent 具备“持续协作能力”的基础设施。

## 远程 agent 的本地镜像机制

远程 agent 并不是“发起一个 HTTP 请求然后等结果”这么简单。

其核心模式是：

1. `AgentTool` 选择 remote 路径
2. 通过 `teleportToRemote()` 或相关 remote 启动逻辑创建远端会话
3. 本地注册 `RemoteAgentTaskState`
4. 本地持续轮询远端 session 事件
5. 需要时在 resume 后恢复这个镜像任务

这里的关键理解是：

`RemoteAgentTaskState` 不是远端真实状态本身，而是本地侧对远端 agent 的持久镜像。

这样设计的好处是：

- 主对话仍能把远端工作看成“一个任务”
- 本地可以在重启/resume 后恢复跟踪
- 远端 transcript 与本地消息系统之间可以通过稳定的 task id 对齐

## 为什么 coordinator 只是 prompt contract

`coordinatorMode.ts` 很容易让人误以为系统存在一个复杂的“中央调度器内核”。

但从源码看，更准确的说法是：

coordinator 更像一份 prompt contract。

它告诉主模型：

- 你现在是协调者
- 应该用 `AgentTool` 派发工作
- 应该用 `SendMessage` 追踪与续问
- 会通过 `<task-notification>` 收到子任务回报

真正的调度、状态托管、消息路由，发生在：

- `AgentTool`
- task framework
- mailbox / swarm
- `SendMessageTool`

所以 coordinator mode 更像“角色提示”，而不是“独立 runtime”。

## in-process teammate 与普通 subagent 有什么不同

这是一个很关键的架构分叉。

### 普通 subagent

- 更像一次性委派
- 跑完就结束
- 生命周期围绕一项任务

### in-process teammate

- 是长期存活 worker
- 会 idle、等待新消息、再继续执行
- 有 mailbox 和 task-list 语义
- 适合 swarm / team 协作

因此它不是普通后台 agent 的别名，而是另一种 actor 模型。

## 一条典型“主 agent 启动本地后台 agent”的主链

可以把它概括成：

1. 主模型调用 `AgentTool`
2. `AgentTool` 选择异步本地路径
3. 注册 `LocalAgentTaskState`
4. `runAgent()` 在子上下文里运行
5. 子 agent 内部仍调用同一个 `query()`
6. 生命周期管理器持续更新 progress
7. 结束后发 `task-notification`
8. 主线程把通知当作下一轮可见事件处理

这条链说明：

Claude Code 的多 agent 不是单独重写了一套推理器，而是把同一个 query loop 递归地放进不同宿主上下文中。

## 关键设计权衡

### 1. 把 spawn 与 execution 分离

`AgentTool` 负责“怎么启动”，`runAgent()` 负责“怎么执行”。

这样做让：

- 启动策略可以很多样
- 执行循环仍然统一

### 2. 用 task state 托管长期 agent

后台 agent 只要是长期存在，就必须有稳定状态结构，否则 resume / cancel / progress 都会失控。

### 3. 用结构化通知而不是自然语言直接合流

这样主线程能可靠地区分：

- 任务完成事件
- 普通用户消息
- 子 agent transcript 细节

### 4. 远程 agent 做成本地镜像

这样本地系统不用因为 agent 在云端就另起一套状态模型。

## 易错点与误解

### 误解 1：`AgentTool` 就是子 agent

不是。`AgentTool` 是主模型调用的编排入口。

### 误解 2：子 agent 有独立推理引擎

不准确。子 agent 仍然复用同一套 `query()` 主循环。

### 误解 3：后台 agent 结束时只是输出文本

不是。更关键的是它会发结构化 task notification。

### 误解 4：coordinator 是系统级 scheduler

不对。它主要是 prompt contract，真正调度散在任务系统、mailbox 和工具层。

## 快照缺口说明

本篇相关主链基本都可验证，但有一个要明确记录：

- 某些 bridge / peer 发送路径动态引用了当前快照中未出现的文件，因此跨 session bridge 续发细节只能确认“有接线”，不能确认完整实现。

## 继续阅读建议

下一篇看 [05-mcp-plugins-and-skills.md](./05-mcp-plugins-and-skills.md)。当你已经理解 agent 与任务系统之后，再看 MCP、skills、plugins 就会更自然：

- 为什么 Claude Code 能动态长出新的工具面
- 为什么它把 skills 做成 command 子类型
- 为什么 provenance、dedup、policy 会这么重
