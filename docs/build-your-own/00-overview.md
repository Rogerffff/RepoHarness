# 第 0 章 Overview：从 Claude Code 到你的 RepoHarness

## 本章解决什么问题

读完本章你会拿到三样东西：

1. **一张能挂概念的"心智图"**：Claude Code 的核心是 4 层抽象——模型循环 / 工具面 / 权限边界 / 生态扩展面。后面 11 章每一章都对应这张图上的某一块。
2. **一段教学用的最小 agent 骨架**：用 `anthropic` SDK + 一个简化版 `read_file` 工具，把"用户输入 → 模型 → 工具 → 模型 → 完成"完整地走一遍。**这是教学玩具，不是 RepoHarness 实现起点**——它的边界、错误处理、元数据都被简化掉了，仅用来体感 agent loop。
3. **一份 RepoHarness 与 Claude Code 的差异地图**：你的 RepoHarness 项目不是 Claude Code 的复刻——它是个**训练数据生产线**，多了三件事（verifier / trajectory / docker workspace），少了三件事（用户审批式权限交互 / MCP marketplace / 富 UI）。本章末尾会把这张差异地图画清楚。

如果你只能读一章就开工，读这章已经够开始**搭原型**。后面 11 章是把"够搭原型"变成"能写到可运行、可评测、可展示的 RepoHarness v1"。

---

## 核心概念（背 4 个就够）

| 术语 | 一句话定义 |
|---|---|
| **Agent Loop（agentic loop）** | `while(模型还在调用工具) { 调模型 → 跑工具 → 把结果回灌进上下文 }`。这就是"agent"的全部本质。 |
| **Tool**（工具） | 一个有 `name / description / input_schema / 执行函数` 四件套的能力契约。模型通过 `tool_use` 块"请求"调用它。 |
| **Tool Use / Tool Result** | 两种**方向相反**的结构化消息块：`tool_use` 是模型 assistant 输出里的"请帮我跑这个工具"请求；`tool_result` 是 Harness 执行工具后**以 user role 回填**给模型的观察结果。两者必须在消息历史里以 `tool_use_id` 配对出现。 |
| **System Prompt** | 喂给模型的"身份说明书"——告诉它是谁、能用哪些工具、要遵守什么规则、当前在什么环境。质量决定 agent 决策质量。 |

剩下那些（compaction / sub-agent / MCP / verifier / trajectory）后面章节再讲，现在记住这 4 个就行。

---

## 整体心智模型（一张图）

```
┌─────────────────────────────────────────────────────────────────┐
│  用户输入                                                          │
│    │                                                              │
│    ▼                                                              │
│  ┌──────────────────┐    ┌──────────────────┐                    │
│  │  上下文组装        │───▶│  System Prompt    │                    │
│  │  (cwd, git,       │    │  + 工具列表        │                    │
│  │   CLAUDE.md)     │    └──────────────────┘                    │
│  └──────────────────┘                                             │
│    │                                                              │
│    ▼                                                              │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │              ╔═══════════════════════════╗                │    │
│  │              ║      Agent Loop           ║                │    │
│  │              ║                           ║                │    │
│  │              ║   ┌──────────────────┐    ║                │    │
│  │              ║   │  调用 LLM         │    ║                │    │
│  │              ║   │  (流式 / 缓存)     │    ║                │    │
│  │              ║   └────────┬─────────┘    ║                │    │
│  │              ║            │              ║                │    │
│  │              ║   ┌────────▼─────────┐    ║                │    │
│  │              ║   │ 解析 tool_use     │    ║                │    │
│  │              ║   │ blocks           │    ║                │    │
│  │              ║   └────────┬─────────┘    ║                │    │
│  │              ║   有？        否          ║                │    │
│  │              ║   │           └──▶ 完成   ║                │    │
│  │              ║   ▼                       ║                │    │
│  │              ║   ┌──────────────────┐    ║                │    │
│  │              ║   │ 权限检查          │    ║                │    │
│  │              ║   └────────┬─────────┘    ║                │    │
│  │              ║            │              ║                │    │
│  │              ║   ┌────────▼─────────┐    ║                │    │
│  │              ║   │ 执行工具          │    ║                │    │
│  │              ║   │ (并行 / 流式)     │    ║                │    │
│  │              ║   └────────┬─────────┘    ║                │    │
│  │              ║            │              ║                │    │
│  │              ║   ┌────────▼─────────┐    ║                │    │
│  │              ║   │ tool_result      │────╫────┐          │    │
│  │              ║   │ 灌回 messages     │    ║    │          │    │
│  │              ║   └──────────────────┘    ║    │          │    │
│  │              ║                           ║    │          │    │
│  │              ║   (回到顶部继续下一轮)      ║◀───┘          │    │
│  │              ║                           ║                │    │
│  │              ╚═══════════════════════════╝                │    │
│  └──────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

记住这张图。后面每一章你都会指着它的某个方框说："这一章在讲这一块"。

---

## Claude Code 是怎么做的（4 层抽象）

Claude Code 是个几十万行级别的 TypeScript 工程，但它的灵魂只有 4 层：

### 第 1 层：模型循环（Model Loop）

入口在 `reference/claude-code-typescript-src/QueryEngine.ts` 的 `submitMessage()`，主循环在 `reference/claude-code-typescript-src/query.ts` 的 `queryLoop()`（行 307 起的 `while(true)`）。这个 1700 行的文件**核心思想只有 30 行**：

```typescript
// 极度简化的 query.ts:queryLoop() 伪代码
while (true) {
  compactIfNeeded(messages);                    // ① 上下文压缩（第 5 章）
  const response = streamCallLLM(messages);     // ② 流式调用模型（第 1 章）
  const toolUses = parseToolUseBlocks(response);
  if (toolUses.length === 0) {
    runStopHooks();                              // ③ 停止钩子（第 4 章）
    return Terminal('completed');                // 没有工具调用 → agent 完成
  }
  const toolResults = await executeTools(toolUses);  // ④ 工具执行（第 2 章）
  messages.push(...toolResults);                // ⑤ 回灌（第 1 章核心）
  turnCount++;
}
```

剩下的代码处理**生产级 agent 真实会遇到的工程问题**：流式输出、错误恢复（行 1085-1166 的 collapse drain / reactive compact / max-output retry）、流式工具执行（行 563-568 的 `StreamingToolExecutor`，让工具在模型流出 token 时同步开始执行）、上下文压缩、权限引擎、工具并发与排序、取消机制（`AbortController` + 弱引用）、token 预算追踪、prompt cache 边界管理。

**学习这套源码的关键技巧**：先抓上面那 30 行核心循环，再分主题理解外围。我们 11 章里会一块一块挖。

### 第 2 层：工具面（Tool Surface）

工具接口定义在 `reference/claude-code-typescript-src/Tool.ts`（行 362-461）。下面只列**最常用的核心字段**——真实接口还包含 `aliases` / `searchHint` / `outputSchema` / `isOpenWorld` / `requiresUserInteraction` / `shouldDefer` / `mcpInfo` 等更多字段，在后续 Ch2 / Ch7 会按需展开：

```typescript
// 简化视图：只保留学习入门最常用的字段
type Tool<Input, Output, P> = {
  // 核心 4 件套
  name: string                                   // 唯一标识符
  description(...): Promise<string>              // 给模型看的说明
  inputSchema: Zod<Input>                        // 输入校验
  call(input, context, onProgress): ToolResult   // 执行
  
  // 安全 / 权限相关（生产级必需）
  isReadOnly(input): boolean                     // 是否只读（决定能否并发）
  isDestructive?(input): boolean                 // 是否不可逆
  isConcurrencySafe(input): boolean              // 能否与其他工具并行
  checkPermissions(input, context): PermissionResult  // 工具自己的权限逻辑
  validateInput?(input, context): ValidationResult    // 额外校验
  
  // UI / 可视化
  userFacingName?(input): string                 // 在 UI 里怎么显示
  maxResultSizeChars: number                     // 结果太大时持久化到磁盘
  
  // ...其余字段（aliases / outputSchema / mcpInfo / shouldDefer / ...）见源码
}
```

工具注册表在 `reference/claude-code-typescript-src/tools.ts`（`getAllBaseTools()`，行 179-250）。Claude Code 内置约 30 个工具，最核心的是：**Read / Edit / Write / Bash / Grep / Glob / Task（子 agent）/ WebFetch / WebSearch**。

**关键设计决策**：所有工具都通过 `buildTool()`（`Tool.ts` 行 757-792）注入 fail-closed 的默认值——`isReadOnly` 默认 false（假设会写）、`isConcurrencySafe` 默认 false（假设不能并发）。这样新工具**默认是最严格的**，必须显式声明才能放宽。

> **RepoHarness 的工具也要保留这套元数据**：`isReadOnly` / `isConcurrencySafe` / `isDestructive` 不是只为"宿主机安全"服务，它们驱动 agent loop 的并发调度（只读工具可并发、写工具与测试默认串行）、训练数据标注（破坏性动作要可识别）、轨迹解释（哪一步污染了 workspace）和失败诊断。Docker workspace 只是降低了"宿主机风险"，不替代工具元数据。

### 第 3 层：权限边界（Permission Boundary）

`reference/claude-code-typescript-src/utils/permissions/permissions.ts` 定义了一个**多模式**的权限引擎（实际模式不止 4 个）：

- **default**：每次工具调用都问用户（allow / deny / always allow / always deny）
- **acceptEdits**：自动允许文件编辑工具，其他仍按 default 询问
- **bypassPermissions**：完全信任所有工具（危险，仅在沙箱环境用）
- **dontAsk**：旧式严格模式，未明确 allow 的就拒绝
- **plan**：计划模式——**偏只读、偏规划**，限制写操作与命令执行（**不是**简单的"全部拒绝"，更像"只能读和想，不能改"）
- 此外还有内部用的 `auto`（基于分类器决策）/ `bubble`（向上层冒泡询问）等模式

权限决策有两层：
1. **规则层**：`alwaysAllow` / `alwaysDeny` / `ask` 三组规则匹配（如 `Bash(git push *)` 模式）
2. **工具层**：每个工具自己实现 `checkPermissions()`（如 `BashTool` 会拦截 `rm -rf /` 这类高危命令）

外加一个 **Hook 系统**（`reference/claude-code-typescript-src/utils/hooks.ts`）：用户写的 shell 脚本在 PreToolUse / PostToolUse / SessionStart 等事件触发，可以修改输入、改写决策、注入上下文。

### 第 4 层：生态扩展（Ecosystem）

把 agent 做成"平台"的三个杠杆：

- **MCP**（Model Context Protocol）：工具是远程 RPC 服务（stdio / SSE / HTTP）。第三方写 MCP server，自动接入工具列表。
- **Skills**：YAML frontmatter + markdown body 的"提示词包"——用配置声明一组工具的特定用法。
- **Plugins**：skills + hooks + MCP servers 的组合分发单元。

**对 RepoHarness 来说，这一层基本不需要**——你的 agent 是研究用的，不需要插件市场。所以我们第 7 章只讲思想、不复刻代码。

---

## 教学最小骨架：90 行 Python 跑通一个 agent

> **⚠️ 这是教学用最小模型，不是 RepoHarness 实现模板。**
> 
> 它的目的只是让你**亲眼看到 agent loop 转起来**。它故意省略了：工具安全元数据（`isReadOnly` / `isConcurrencySafe` / `isDestructive`）、权限引擎、并发调度、错误诊断、轨迹记录、token 预算、流式输出、prompt 缓存。代码里加了一个最简的 `WORKSPACE_ROOT` 边界检查，**只够防止误读 `~/.ssh/`，不是真正的 sandbox**。
>
> RepoHarness 的真实起点在第 9-11 章（task / workspace / verifier / trajectory）。这段代码与 RepoHarness 的关系是："你能从它看清 agent loop 的 5 个步骤" —— 仅此而已。

```python
"""
最小 agent loop（教学玩具）—— 大约 90 行 Python。

依赖：pip install anthropic
环境变量：ANTHROPIC_API_KEY
"""
from pathlib import Path
from anthropic import Anthropic

client = Anthropic()
# 教学示例用别名；RepoHarness 实现时务必锁定到带日期的版本 ID（如
# "claude-sonnet-4-6-YYYYMMDD"）以保证可复现实验。模型 ID 列表见
# https://docs.anthropic.com/en/docs/about-claude/models/overview
MODEL = "claude-sonnet-4-6"

# 把当前进程目录视作 workspace 边界。RepoHarness 真实实现里，
# 这是 Docker container 的 /workspace 挂载点。
WORKSPACE_ROOT = Path.cwd().resolve()

# ────────────────────────────────────────────────────────────
# 工具定义（核心 4 件套：name / description / input_schema / 执行函数）
# ────────────────────────────────────────────────────────────
def tool_read_file(input: dict) -> str:
    """读取 workspace 内的文本文件（截断到 4000 字符）。"""
    raw = Path(input["path"]).expanduser()
    try:
        # 解析后的绝对路径必须在 WORKSPACE_ROOT 之下
        abs_path = raw.resolve()
        abs_path.relative_to(WORKSPACE_ROOT)
    except ValueError:
        return f"ERROR: path '{raw}' is outside workspace boundary {WORKSPACE_ROOT}"
    if not abs_path.is_file():
        return f"ERROR: not a file: {abs_path}"
    text = abs_path.read_text(errors="replace")
    return text[:4000] + ("\n...[truncated]" if len(text) > 4000 else "")

TOOLS = [{
    "name": "read_file",
    "description": (
        "Read a text file from the workspace. The path must be within the current "
        "working directory; absolute paths outside it will be rejected."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"path": {"type": "string", "description": "relative or absolute path within workspace"}},
        "required": ["path"],
    },
}]

TOOL_HANDLERS = {"read_file": tool_read_file}

# ────────────────────────────────────────────────────────────
# Agent Loop —— 整套核心
# ────────────────────────────────────────────────────────────
def agent_loop(user_msg: str, max_turns: int = 10) -> str:
    messages = [{"role": "user", "content": user_msg}]
    system = (
        f"You are a helpful coding assistant. Workspace root is {WORKSPACE_ROOT}. "
        "Use the read_file tool when you need to inspect file contents."
    )

    for turn in range(max_turns):
        # ① 调模型
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=system,
            tools=TOOLS,
            messages=messages,
        )

        # ② 把模型整段输出原样追加进历史（含 text + tool_use）
        messages.append({"role": "assistant", "content": response.content})

        # ③ 判断有没有 tool_use 块
        tool_uses = [b for b in response.content if b.type == "tool_use"]
        if not tool_uses:
            # 没有工具调用 → 模型说完了 → 提取文本回答返回
            text_blocks = [b.text for b in response.content if b.type == "text"]
            return "\n".join(text_blocks)

        # ④ 跑工具，构造 tool_result blocks
        tool_results = []
        for tu in tool_uses:
            handler = TOOL_HANDLERS.get(tu.name)
            if handler is None:
                output = f"ERROR: unknown tool {tu.name}"
            else:
                try:
                    output = handler(tu.input)
                except Exception as e:
                    output = f"ERROR: {type(e).__name__}: {e}"
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": output,
            })

        # ⑤ tool_result 必须以 user role 灌回（Anthropic API 协议）
        messages.append({"role": "user", "content": tool_results})

    return "[max turns reached]"

# ────────────────────────────────────────────────────────────
# 跑一下（在 RepoHarness 仓库根目录执行）
# ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    answer = agent_loop("请读取 docs/00-reading-guide.md 的开头，告诉我这是什么项目。")
    print(answer)
```

**这段代码做了什么 / 没做什么**（重点看右列——那是后续章节会逐章补上的内容，也是把它和 RepoHarness 实现拉开距离的关键）：

| ✅ 做了 | ❌ 没做（后续章节加） |
|---|---|
| 完整的 agentic loop（5 步） | 流式输出 / 流式工具执行（Ch1）|
| 工具定义 + 调度（核心 4 件套） | 工具安全元数据 isReadOnly / isConcurrencySafe（Ch2）|
| 最简 workspace 边界检查（防止误读 `~`） | 多工具并行 + 排序（Ch2）|
| `tool_use` / `tool_result` 配对（Anthropic 协议） | 真实 Read/Edit/Write/Bash/Grep 工具集（Ch2）|
| 错误隔离（工具异常不会炸整个循环） | 系统提示词的动态组装 / 缓存（Ch3）|
| 最大轮数保护 | 权限引擎 + Hooks（Ch4）|
| | 上下文压缩（Ch5）|
| | 子 agent / scaffold（Ch6）|
| | MCP / Skills（Ch7）|
| | Task / Docker workspace 生命周期（Ch9）|
| | Verifier / 测试反馈 / Reward（Ch10）|
| | Trajectory 记录 / 训练导出（Ch11）|

后面 11 章每一章我都会回到这段代码，告诉你"在哪一行加什么"——但**不要把它当 RepoHarness 起点**。RepoHarness 的真正骨架要等第 9 章。

---

## → RepoHarness 对照（解码 docs/00 + docs/02）

> 接下来你要读 `docs/00-reading-guide.md` 和 `docs/02-system-architecture.md`。下面是把它们和上面学到的内容对应起来的"翻译表"。

### RepoHarness 与 Claude Code 是什么关系？

**Claude Code = 给人用的产品级编程助手**：UI 重要、用户体验重要、要能接 MCP marketplace、要支持 plugins。

**RepoHarness = 给训练用的研究 harness**：UI 不重要（基本无 UI）、可复现性最重要、要能批量跑 50 个任务、每个任务要产出训练数据（trajectory）。

它们**共享核心**（agent loop / tool system / permissions），**RepoHarness 多三件**（verifier / trajectory store / Docker workspace），**RepoHarness 少三件**（UI / MCP / 用户审批式权限）。

### docs/00 的核心闭环（你的项目灵魂）

```
task -> executable workspace -> tools -> agent loop -> trajectory -> verifier -> reward/eval/export
```

把这个闭环和上面那张"心智图"对照看：

| RepoHarness 闭环步骤 | 心智图位置 | 哪一章讲 |
|---|---|---|
| `task` | 顶部"用户输入"位置，但来自数据集而非交互 | Ch9 |
| `executable workspace` | 整个执行环境（Docker） | Ch9 |
| `tools` | 中部"执行工具"方框 | Ch2 |
| `agent loop` | 中部整个粗框（核心） | Ch1 |
| `verifier` | "tool_result 灌回"之后多一步：跑测试评估 | Ch10 |
| `trajectory` | 整套消息流 + 事件流的持久化 | Ch11 |
| `reward / eval / export` | trajectory 的下游消费 | Ch10 + Ch11 |

### docs/02 的"三平面"架构

RepoHarness 设计文档把系统分成三个平面：

```
Control Plane     ←→ "怎么编排一次实验"   (CLI, Eval Runner, Task Adapter, Scaffold)
Execution Plane   ←→ "一次任务怎么跑完"   (Agent Loop, Tools, Permissions, Workspace, Verifier)
Data Plane        ←→ "怎么记录与导出"     (Trajectory Store, Training Exporter)
```

Claude Code 没有按"三平面"显式分层——它有 transcript / session / diagnostics / telemetry 等记录机制（可以视为"事实数据平面"），但**没有面向训练数据导出的数据平面**：没有 SFT/RL JSONL 导出器、没有 reward metadata、不需要"任务批量执行 + 同 verifier 重放评测"这类硬约束。RepoHarness 加这两层正是为了满足这些训练场景的需求。

### 关键不变量（docs/02 末尾列了 8 条，我挑 4 条最关键的）

1. **工具结果必须作为 `tool_result` 回流到下一轮模型上下文**——这是 agent loop 的灵魂，Claude Code 和 RepoHarness 都遵守。
2. **所有写操作必须限制在任务工作区内**——Claude Code 以**当前项目目录 + 权限系统**为主要操作上下文（不是严格安全 sandbox），RepoHarness 以 **Docker workspace 边界**为操作上下文（也不是严格安全 sandbox，但物理隔离更强）。
3. **训练奖励和离线评测必须共用同一套 verifier**——RepoHarness 特有，避免训练评测不一致（这是大厂强调的 "training-evaluation harness consistency"）。
4. **轨迹记录不能依赖终端界面或人工观察**——RepoHarness 特有，因为训练时没人在看。Claude Code 的事件记录是为了 telemetry / 调试，RepoHarness 的事件记录是为了**生产训练数据**。

### 你应该在脑子里画的对比表

| 维度 | Claude Code | RepoHarness |
|---|---|---|
| 谁来用 | 人 | 训练 / 评测 pipeline |
| 入口 | REPL 交互 | CLI 跑 task list |
| 操作上下文 | 当前项目目录 + 权限系统 | 每任务一个 workspace（local process 或 Docker） |
| 权限 | 完整四模式 + 用户审批 | 同样四模式（plan/ask/auto/deny），批量评测默认不开 ask |
| 终止条件 | 用户满意 / Ctrl+C | feedback_tests_passed / 轮数耗尽 / 预算耗尽（与 final verifier 评测分开） |
| 输出 | 屏幕上的回答 + 文件改动 | Trajectory 目录（transcript + events + diff + verifier） |
| 衡量成功 | 用户满不满意 | `final_verifier_status` + `run_outcome` 综合判定 |

---

## 常见坑与扩展方向

**坑 1：不理解 `tool_use` / `tool_result` 必须配对**

Anthropic API 的硬约束：assistant 消息里出现的每一个 `tool_use` 块，下一条 user 消息里**必须**有对应 `tool_use_id` 的 `tool_result`，不然下次调用模型直接 400。这是 80 行代码里第 ⑤ 步的关键——所有 tool_results 必须打包进**一条** user 消息。

**坑 2：忘了把 assistant 的整段 content 原样追加**

很多人只追加 `text`，结果 `tool_use` 丢了，下一轮模型对不上号。第 ② 步的写法 `messages.append({"role": "assistant", "content": response.content})`——**整段 content 数组**原样追加。

**坑 3：没有 `max_turns` 保护**

模型可能进死循环（比如反复调一个失败的工具）。生产级 agent 必须有轮数上限 + token 预算上限 + 无限循环检测。第 5 章会讲 RepoHarness 的"failure diagnostics"分类。

**扩展方向（这章就能尝试）**：
- 加一个 `bash` 工具：`subprocess.run(args_list, shell=False, cwd=WORKSPACE_ROOT, capture_output=True, timeout=30)`。**不要**用 `shell=True`（命令注入）、**要**指定 `cwd=WORKSPACE_ROOT`、**要**加 timeout——这些边界设计在 Ch4（权限）和 Ch9（workspace）里会展开讲。这里只是预览。
- 把消息历史持久化到 JSONL：每收到一条消息就 append 到 `messages.jsonl`——你已经在做 trajectory 记录的雏形了（Ch11 会重做这一块）。
- 把 `system` 字符串换成读取 `CLAUDE.md` / 任务 issue statement 的内容——你已经在做上下文组装的雏形了（Ch3 会重做这一块）。

---

## 下一章预告

**第 1 章 Agentic Loop**：把 `query.ts` 的核心循环精读到能默写。重点：
- 流式 vs 阻塞——为什么 Claude Code 要在模型流出 token 时**同步**开始工具执行？
- 错误恢复的三层退路：`collapse drain` / `reactive compact` / `max-output retry`——它们分别在哪些场景救你？
- AbortController + 弱引用——怎么让用户按 Ctrl+C 时所有正在跑的工具立刻停？
- RepoHarness 对照（docs/03）：你的 agent loop 与 Claude Code 的差异分两部分讲清楚——
  - **运行控制（停止 agent）**：多了一个停止条件 `feedback_tests_passed`（中间一次 `run_tests` 通过就直接停 agent loop，避免浪费 token）；同时把交互式恢复**换成**了诊断式失败记录（没人在看，错了就分类记录 + 继续下一个任务）
  - **最终评测（agent 停止之后）**：在 agent stop 之后再跑一次 **final verifier**——它**不是另一个停止条件**，而是独立的"最终评测路径"。RepoHarness 把 `agent_stop_reason` / `final_verifier_status` / `run_outcome` 拆成三个不同字段，让"agent 自己以为做完了"和"verifier 在最终 workspace 上确认做完了"分开记录，避免训练数据里出现"agent 看到的旧测试结果"和"最终 workspace 上的真实测试结果"被混淆
