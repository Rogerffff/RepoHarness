# Codex 与 Claude Code 的 Harness 设计对照，以及对 RepoHarness 的启发

本文面向 RepoHarness + verl fully async RL 训练链路的后续设计。它不是 OpenAI Codex 或 Claude Code 的产品介绍，也不是要求 RepoHarness 复制某一家产品的源码，而是回答一个更具体的问题：

```text
如果 RepoHarness 想训练接近真实软件工程智能体的能力，
Codex 和 Claude Code 这两类成熟开发代理运行时，能给 RepoHarness 的工具面、权限边界、轨迹 schema 和训练门禁带来什么设计约束？
```

本文结论来自本地参考源码和现有 Stage 16G 文档。路径全部使用仓库相对路径，避免把本机绝对路径写入公开文档。

## 1. 一句话结论

Codex 和 Claude Code 在核心 harness 设计上高度一致：它们都不是“模型一次性输出补丁”的简单壳，而是把模型放进一个真实开发代理运行时中，让模型在工具、权限、沙箱、事件流、上下文和扩展系统共同构成的环境里完成任务。

两者的共同原则可以概括为：

```text
给足真实软件工程需要的核心能力，
再用 sandbox、approval、hook、事件审计、输出截断和权限恢复管理风险，
而不是通过过度削弱工具能力来制造安全感。
```

这对 RepoHarness 的含义很直接：

```text
现有极窄 execute_bash、diagnostic_shell 诊断特例、无参数 run_tests 和 exact replace 编辑能力，
不能长期作为主 SWE 强化学习默认工具面。

RepoHarness 应继续推进 Stage 16G.2 到 Stage 16G.4：
结构化文件和 patch 工具、公开命令工具、项目测试路由、scratch reproduction、受控诊断 shell、
结构化权限拒绝、TrainingView 投影和训练资格门禁。
```

## 2. 参考材料

### 2.1 Codex 参考源码

主要参考：

```text
reference/codex/AGENTS.md
reference/codex/codex-rs/core/src/session/turn.rs
reference/codex/codex-rs/core/src/session/session.rs
reference/codex/codex-rs/core/src/client.rs
reference/codex/codex-rs/core/src/tools/spec_plan.rs
reference/codex/codex-rs/core/src/tools/router.rs
reference/codex/codex-rs/core/src/tools/registry.rs
reference/codex/codex-rs/core/src/tools/orchestrator.rs
reference/codex/codex-rs/core/src/tools/sandboxing.rs
reference/codex/codex-rs/core/src/tools/handlers/shell_spec.rs
reference/codex/codex-rs/core/src/tools/handlers/shell.rs
reference/codex/codex-rs/core/src/tools/handlers/unified_exec.rs
reference/codex/codex-rs/core/src/tools/handlers/apply_patch_spec.rs
reference/codex/codex-rs/core/src/tools/handlers/apply_patch.rs
reference/codex/codex-rs/core/src/tools/runtimes/apply_patch.rs
reference/codex/codex-rs/core/src/exec.rs
reference/codex/codex-rs/protocol/src/protocol.rs
reference/codex/codex-rs/protocol/src/models.rs
reference/codex/codex-rs/protocol/src/permissions.rs
reference/codex/codex-rs/protocol/src/approvals.rs
reference/codex/codex-rs/core/src/config/permissions.rs
reference/codex/codex-rs/app-server/README.md
reference/codex/codex-rs/rollout-trace/README.md
```

Codex 参考仓库当前本地 commit：

```text
61cbf3574eca870df6fa7f49648ec7e001901b5a
```

### 2.2 Claude Code 参考材料

主要参考：

```text
reference/claude-code-typescript-src/AGENTS.md
reference/claude-code-typescript-src/Tool.ts
reference/claude-code-typescript-src/tools.ts
reference/claude-code-typescript-src/services/tools/
reference/claude-code-typescript-src/tools/
reference/claude-code-typescript-src/utils/permissions/
reference/claude-code-typescript-src/hooks/
reference/claude-code-typescript-src/plugins/
reference/claude-code-typescript-src/skills/
```

### 2.3 RepoHarness 和 Stage 16G 材料

主要参考：

```text
docs/harness_improve/gpt_advice.md
docs/agentic_RL/repo_harness_verl_workstreams/49-stage-16g-0-execution-plan.md
docs/agentic_RL/repo_harness_verl_workstreams/50-stage-16g-0-follow-up-baseline-contract-execution-plan.md
docs/agentic_RL/repo_harness_verl_workstreams/51-stage-16g-1-to-16g-6-execution-plan.md
docs/agentic_RL/repo_harness_verl_workstreams/52-stage-16g-1-execution-plan.md
docs/agentic_RL/repo_harness_verl_workstreams/53-stage-16g-2-execution-plan.md
docs/agentic_RL/repo_harness_verl_workstreams/54-stage-16g-2b-preflight-design-correction.md
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_0/
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_1/
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_2/
```

另一个评测工作树的差距分析作为背景输入，但本文不写真实本机路径。

## 3. Codex 的 Harness 形态

Codex 的核心是 `codex-rs/core/`。它不是单一命令执行器，而是一个多入口共享的 agent runtime：

```text
TUI / codex exec / app-server / SDK
-> Session / Thread / Turn
-> ModelClient / Responses API
-> ToolRouter / ToolRegistry / ToolOrchestrator
-> shell、unified exec、apply_patch、MCP、计划、目标、子代理、动态工具
-> ResponseInputItem / EventMsg / TurnItem / Rollout / optional RolloutTrace
```

### 3.1 Agent loop

`codex-rs/core/src/session/turn.rs` 的 `run_turn(...)` 是最重要的入口。它实现的循环是：

```text
构建模型输入
-> 调用模型流式响应
-> 收集 assistant message 和 tool call
-> 工具调用进入 ToolCallRuntime
-> 工具结果变成 ResponseInputItem
-> 写回历史
-> 必要时继续下一轮模型请求
```

这和 Claude Code `query.ts` 中的核心思想一致：模型不是只生成最终答案，而是在多轮工具调用和结果反馈中完成任务。

### 3.2 工具系统

Codex 的工具系统由几层组成：

```text
codex-rs/tools/
  定义 Responses API 工具规格、工具 schema、工具 payload、工具发现和工具输出抽象。

codex-rs/core/src/tools/spec_plan.rs
  根据 turn context、模型元信息、功能开关、MCP、dynamic tools 和 extension tools 构造本轮工具池。

codex-rs/core/src/tools/router.rs
  把模型返回的 ResponseItem 转成内部 ToolCall。

codex-rs/core/src/tools/registry.rs
  统一执行工具，接入 hook、telemetry、tool lifecycle 和结果包装。

codex-rs/core/src/tools/orchestrator.rs
  统一处理 approval、sandbox 选择、sandbox denial、network approval 和升级重试。
```

Codex 工具面和 Claude Code 工具面有重要差异。Claude Code 在源码中显式有 `Read`、`Grep`、`Glob`、`Edit`、`Write`、`Bash`、`TodoWrite` 等结构化工具。Codex 当前核心模型可见工具更集中在：

```text
shell_command 或 exec_command / write_stdin
apply_patch
update_plan
goal tools
request_permissions
request_user_input
MCP tools
tool_search
dynamic tools
extension tools
multi-agent tools
code mode execute / wait
hosted web search / image generation
```

这些工具不是在所有会话里默认同时可见。Codex 会根据模型能力、provider capability、feature flag、namespace tools、鉴权状态、code mode 和运行环境选择工具；Claude Code 的部分工具也会根据嵌入式搜索等能力做条件暴露。因此，分析工具面时要区分“源码里存在的工具定义”“当前 profile 暴露给模型的工具 schema”和“executor registry 实际能执行的工具”。

因此不能把 Codex 简化成“只有 Bash”，也不能说它和 Claude Code 的文件工具分层完全相同。更准确的描述是：

```text
Claude Code 更显式地把读、搜、改、写拆成结构化模型工具；
Codex 更强调通过 shell / unified exec 完成读、搜、测试和诊断，通过 apply_patch 完成受控文件修改。
```

### 3.3 Shell 和真实命令能力

Codex 的 shell-like 能力是正式工具面，不是诊断侧通道。具体暴露 `shell_command` 还是 `exec_command` / `write_stdin`，取决于模型元信息、功能开关和配置。

相关路径：

```text
reference/codex/codex-rs/core/src/tools/handlers/shell_spec.rs
reference/codex/codex-rs/core/src/tools/handlers/shell.rs
reference/codex/codex-rs/core/src/tools/runtimes/shell.rs
reference/codex/codex-rs/core/src/tools/handlers/unified_exec.rs
reference/codex/codex-rs/core/src/unified_exec/
reference/codex/codex-rs/core/src/exec.rs
```

Codex 的 `exec_command` schema 支持：

```text
cmd
workdir
shell
tty
yield_time_ms
max_output_tokens
sandbox_permissions
additional_permissions
justification
prefix_rule
```

`write_stdin` 支持向仍在运行的统一执行 session 写入输入并轮询输出。这说明真实产品态开发代理需要：

```text
运行项目命令
运行测试
运行复现脚本
检查运行时行为
处理长输出和截断
处理交互式或长运行命令
在需要时请求额外权限
```

这恰好击中 RepoHarness Stage 16G 当前担心的问题：如果主训练工具面连公开测试、公开项目命令和 scratch reproduction 都不能稳定表达，那么强化学习会优化错误的工作流。

### 3.4 Apply Patch 和文件修改

Codex 的 `apply_patch` 是非常值得 RepoHarness 学习的结构化文件修改入口。

相关路径：

```text
reference/codex/codex-rs/core/src/tools/handlers/apply_patch_spec.rs
reference/codex/codex-rs/core/src/tools/handlers/apply_patch.lark
reference/codex/codex-rs/core/src/tools/handlers/apply_patch.rs
reference/codex/codex-rs/core/src/tools/runtimes/apply_patch.rs
reference/codex/codex-rs/core/src/apply_patch.rs
reference/codex/codex-rs/core/src/safety.rs
reference/codex/codex-rs/apply-patch/src/parser.rs
reference/codex/codex-rs/apply-patch/src/lib.rs
```

Codex 的 `apply_patch` 有几个关键点：

1. 它是模型可见的专用 patch 工具，不要求模型通过 shell 重定向或 Python 脚本改源码。
2. 它有语法约束，支持新增、删除、更新和移动文件。
3. 它在执行前验证 patch 和路径。
4. 它进入 approval / sandbox / event lifecycle。
5. 它会产生 file change event 和 patch status。
6. 它支持 streamed argument diff，用于 UI 看到 patch 生成进度。

RepoHarness Stage 16G.2 的方向与此高度一致：`write_file` 保持整文件写入语义，`apply_patch` 作为批量文件操作入口，删除、移动、目录创建优先通过结构化 `apply_patch.operations` 表达。这比只依赖 `edit_file(old_text, new_text)` 更适合真实 SWE 任务。

### 3.5 Permission、Approval 和 Sandbox

Codex 把权限和审批拆成多层：

```text
PermissionProfile
  文件系统和网络能力边界。

AskForApproval
  什么时候需要审批。

ToolOrchestrator
  approval -> sandbox attempt -> sandbox denied -> optional retry approval -> retry without sandbox。

Guardian
  自动审查高风险工具动作。

Hooks
  PreToolUse、PermissionRequest、PostToolUse 等生命周期拦截点。
```

相关路径：

```text
reference/codex/codex-rs/protocol/src/permissions.rs
reference/codex/codex-rs/protocol/src/approvals.rs
reference/codex/codex-rs/core/src/config/permissions.rs
reference/codex/codex-rs/core/src/tools/orchestrator.rs
reference/codex/codex-rs/core/src/tools/sandboxing.rs
reference/codex/codex-rs/core/src/exec_policy.rs
reference/codex/codex-rs/core/src/guardian/
reference/codex/codex-rs/hooks/src/lib.rs
```

Codex 的默认 `workspace` permission profile 不是无约束全盘访问。它允许工作区写入，但保护 `.git`、`.codex`、`.agents` 等元数据，网络默认受限。它还支持 read-only 和 danger-full-access 这类 profile，但这些是明确配置，不是混在一个模糊的 shell allowlist 里。

这对 RepoHarness 的重要启发是：

```text
安全设计应依赖确定性边界和可审计审批，
不应主要依赖把工具能力压缩到无法完成真实工程闭环。
```

RepoHarness 的边界比产品态 Codex 更严格，因为它存在 hidden verifier、gold patch、test patch、runtime-private artifact、official selector 和训练数据污染风险。但这不意味着必须放弃真实开发动作空间。正确方向是：

```text
公开工作区和公开诊断能力足够强；
私有 evaluator-only 信息绝对隔离；
所有拒绝和越界行为结构化记录；
可疑行为进入 quarantine 或 monitor。
```

### 3.6 App Server、SDK 和非交互模式

Codex 的同一 core 同时服务：

```text
交互式 TUI
codex exec 非交互模式
app-server JSON-RPC
TypeScript SDK
Python SDK
IDE / 桌面端
```

相关路径：

```text
reference/codex/codex-rs/exec/src/lib.rs
reference/codex/codex-rs/app-server/README.md
reference/codex/codex-rs/app-server/src/message_processor.rs
reference/codex/codex-rs/app-server-protocol/src/protocol/v1.rs
reference/codex/codex-rs/app-server-protocol/src/protocol/v2/
reference/codex/sdk/typescript/src/thread.ts
reference/codex/sdk/python/src/openai_codex/client.py
```

这对 RepoHarness 的启发是：`run_episode(real_episode)` 应当成为训练、评测、导出和 smoke 的统一入口。Stage 16F 已经完成了从 legacy `run_task(...)` 到 `run_episode(...)` 的方向收敛，Stage 16G 的工具新增也必须继续绑定这个统一入口，而不能在旧路径或局部工具单测中形成另一套行为事实。

### 3.7 Rollout Trace 和事件审计

Codex 的 `rollout-trace` 是一个非常重要的参考。它明确区分：

```text
模型可见 conversation
runtime tool dispatch
terminal operation
code-mode runtime
MCP call
multi-agent edge
raw payload reference
offline reduced semantic graph
```

相关路径：

```text
reference/codex/codex-rs/rollout-trace/README.md
reference/codex/codex-rs/rollout-trace/src/lib.rs
reference/codex/codex-rs/rollout-trace/src/raw_event.rs
reference/codex/codex-rs/rollout-trace/src/tool_dispatch.rs
reference/codex/codex-rs/rollout-trace/src/reducer/
```

它的核心原则是：

```text
先观察，后解释。
```

这对 RepoHarness 的训练轨迹尤其重要。RepoHarness 不能把所有东西都塞进一个 transcript。至少要区分：

```text
模型真实看见的 observation
工具原始输入
规范化后的工具输入
权限决策
运行时 stdout / stderr 原始 artifact
模型可见截断摘要
final.patch / final.diff
patch hygiene 过滤事实
hidden verifier 私有结果
reward-only metadata
TrainingView 中可训练 token 和不可训练 token
```

否则后续 reward builder、policy loss、SFT export 和偏好数据都会混淆“模型学到了什么”和“评测系统知道什么”。

## 4. Claude Code 的 Harness 形态

Claude Code 参考源码呈现出另一种真实产品态开发代理设计：

```text
用户输入
-> processUserInput
-> query.ts
-> model streaming
-> services/tools/toolOrchestration.ts
-> services/tools/toolExecution.ts
-> Tool.call
-> tool_result
-> query.ts 下一轮
```

Claude Code 的优势在于显式工具分层：

```text
Read / FileReadTool
Grep / Glob
Edit / FileEditTool
Write / FileWriteTool
Bash
TodoWrite
AgentTool
MCPTool
ToolSearchTool
hooks
plugins
skills
LSP diagnostics
context compaction
```

与 Codex 不同，Claude Code 明确建议模型不要用 Bash 完成所有事情。例如读文件用 Read，搜索用 Grep / Glob，编辑用 Edit / Write，项目命令和诊断用 Bash。这种分层非常适合训练 harness，因为模型 action space 更可解释，权限和审计也更精细。

RepoHarness 当前结构化工具路线更接近 Claude Code 的显式分层，但动态诊断能力弱于 Codex 和 mini-SWE-agent 风格 shell-first 环境。Stage 16G 的正确方向不是放弃结构化工具，而是把结构化工具和公开命令能力结合起来。

## 5. 高度一致的设计

### 5.1 多轮 agent loop，而不是一次性 patch 生成

Codex 的 `run_turn(...)` 和 Claude Code 的 `query.ts` 都把任务解决建模为多轮循环：

```text
模型生成思路或工具调用
-> harness 执行工具
-> 工具结果进入上下文
-> 模型继续推理和行动
-> 最终回答或停止
```

RepoHarness 已经有 agent loop 和 `run_episode(real_episode)`，但 Stage 16G 后要继续保证工具新增都进入这个统一 loop，而不是作为 evaluator 旁路。

### 5.2 Shell / Bash 是正式能力

两者都把命令执行作为正式开发能力：

- Claude Code 的 Bash 负责测试、构建、项目命令、复杂诊断和后台任务。
- Codex 的 `shell_command` / `exec_command` / `write_stdin` 负责命令执行、工作目录、PTY、长输出、stdin 续写和权限请求。

这说明：

```text
真实 SWE agent 不能只靠静态读文件和 exact replace。
它必须能够运行公开测试、公开诊断命令和复现脚本。
```

RepoHarness 可以不开放无约束 Bash，但必须提供等价的 `run_public_command`、`run_project_test` 和 `scratch_python`。

### 5.3 编辑必须进入结构化审计

Claude Code 有 Edit / Write，Codex 有 `apply_patch`。两者都避免把文件修改完全交给任意 shell side effect。

RepoHarness Stage 16G.2 的核心工作正是补齐：

```text
write_file
apply_patch
delete / move / mkdir 语义
patch hygiene
final.patch / final.diff
TrainingView 投影
训练资格门禁
```

16G.2A 已经完成 schema、profile 和 scaffold 暴露；16G.2B 已经把 `write_file` 和 `apply_patch` 的默认工具行为启用，并完成基础验收。但 16G.2B 的 acceptance summary 仍明确标记新工具不能进入 policy loss，下一步必须由 16G.2C 补齐 patch hygiene、final patch、TrainingView 和 export linkage。因此不能把 16G.2B 误读成“文件工具已经训练可用”。

### 5.4 权限拒绝不是普通错误字符串

Codex 有 `ExecApprovalRequestEvent`、`ApplyPatchApprovalRequestEvent`、`GuardianAssessmentEvent`、network policy amendment 和 execpolicy amendment。Claude Code 有 deny / ask / allow / bypass / content-level safety check / hook 的多层决策。

RepoHarness 需要把拒绝变成结构化、可学习、可审计的事件：

```json
{
  "denied_reason_code": "network_disabled",
  "policy_version": "stage16g3.public_command.v1",
  "retryable": true,
  "safe_alternative_tool": "run_project_test",
  "safe_rewrite_example": "pytest tests/test_example.py::test_case -q"
}
```

否则强化学习会学到“少调用工具更安全”，而不是学到“如何把失败命令改写成安全公开命令”。

### 5.5 Sandbox 是技术边界，不是提示词装饰

Codex 有 macOS、Linux、Windows 各自的 sandbox 后端和 permission profile 编译。Claude Code 也强调 sandbox、allowlist、denylist、用户审批和 hook。

RepoHarness 的边界必须至少覆盖：

```text
hidden verifier 不可读
gold patch 不可读
test patch 不可读
official selector 不可读
runtime-private 路径不可读写
宿主绝对路径不可逃逸
共享依赖环境只读
默认无网络
临时脚本和 cache 不进入 final patch
```

这和给模型公开命令能力并不矛盾。真正的目标是“强能力在强边界内运行”。

### 5.6 外部工具和扩展系统是未来能力位

Claude Code 有 MCP、插件、技能、工具搜索和子代理。Codex 也有 MCP、dynamic tools、extension tools、plugins、skills、multi-agent 和 hosted tools。

RepoHarness 短期可以不实现完整插件市场，但 trajectory schema 和 tool registry 不能假设“永远只有固定单代理小工具集”。建议至少预留：

```text
tool_source
tool_namespace
tool_exposure
deferred_loading
authorization_outcome
sidechain_transcript_ref
subagent_thread_id
external_tool_public_projection
```

### 5.7 事件流和轨迹是产品能力的一部分

Codex 的 app-server、exec JSONL、rollout 和 rollout trace，以及 Claude Code 的 transcript、tool_result pairing、hooks 和 sidechain transcript，都说明事件不是日志附属品，而是运行时契约。

RepoHarness 的 TrainingView、GenerationRecord、formal online RL gate 和 export inspector 应继续沿着这个方向加强。

## 6. 主要差异

### 6.1 Claude Code 更显式结构化，Codex 更 shell / patch 中心

Claude Code 的工具分层更接近：

```text
Read / Grep / Glob / Edit / Write / Bash
```

Codex 的模型可见核心更接近：

```text
exec_command / write_stdin / apply_patch / plan / goal / MCP / dynamic tools
```

这意味着 RepoHarness 不必照搬 Codex 的 shell-first 风格。RepoHarness 可以保留结构化 `read_file`、`grep`、`glob_files`、`symbol_search`、`edit_file`，同时引入 Codex 风格的 `apply_patch` 和受控 public command。

### 6.2 Claude Code 有更完整的内置文件导航工具

Claude Code 源码中有独立 FileRead、Glob、Grep、FileEdit、FileWrite。Codex 的核心模型工具没有同等显式的 Read / Grep / Glob 工具；很多导航动作由 shell 承担。

对 RepoHarness 来说，结构化文件导航仍然应该保留，因为训练 harness 更需要清晰的 action attribution、权限边界和 reward attribution。不能因为 Codex shell 能读文件，就让 RepoHarness 也鼓励模型用 shell `cat`、`sed`、`awk` 完成所有源码操作。

### 6.3 Codex 的 app-server API 不等同于模型工具

Codex app-server 提供 `fs/readFile`、`fs/writeFile`、`command/exec`、`process/spawn` 等外部客户端 API。但这些是客户端控制 Codex 或环境的 API，不是模型普通可见工具。

RepoHarness 做能力对齐时必须区分：

```text
模型动作空间
客户端控制面
评测 harness 内部能力
verifier / reward-only 能力
```

Stage 16G 的所有工具面结论都应以模型可见工具和可训练轨迹为准。

还需要特别区分 app-server 不同 API 的安全语义：

| app-server API | 安全语义 | 对 RepoHarness 的含义 |
| --- | --- | --- |
| `command/exec` | 客户端请求 app-server 在 server sandbox 下运行单个命令，不启动模型 turn。 | 可参考命令执行结果结构和流式输出，但不能直接等同于模型动作。 |
| `thread/shellCommand` | 用户发起的 `!` shell command，文档明确写成不继承 thread sandbox policy。 | 只能作为产品控制面参考，不能作为训练工具面默认语义。 |
| `process/spawn` | 实验性宿主进程能力，文档明确说明不经过 Codex sandbox。 | 对 RepoHarness 主训练工具面风险过高，只能作为“不要误用”的边界案例。 |
| `fs/readFile` / `fs/writeFile` 等 `fs/*` | 操作宿主绝对路径的客户端文件系统 API。 | 不能映射成模型可见文件工具；RepoHarness 文件工具必须使用任务工作区相对路径和隐藏路径隔离。 |

### 6.4 Codex 没有内置 SWE-Bench verifier / reward

Codex 是产品态编码代理运行时，不是 SWE-Bench 训练 harness。它有 rollout、trace、review、patch、shell、approval、sandbox，但没有 RepoHarness 需要的：

```text
task dataset
hidden verifier
gold patch / test patch 隔离
official prediction
reward builder
policy loss eligibility
verl fully async queue
TrainingView
```

因此 Codex 只能指导工具环境和运行时设计，不能替代 RepoHarness 的训练数据治理和 verifier 边界。

### 6.5 Codex approval 可以有人参与，RepoHarness RL rollout 通常无人参与

产品态 Codex 可以向用户请求批准，或者使用 guardian 自动审查。RepoHarness 强化学习 rollout 通常不能依赖真人逐条确认。

因此 RepoHarness 需要把 Codex / Claude Code 的 approval 思想转成训练环境中的 deterministic policy：

```text
公开安全动作自动允许
明确越界动作确定性拒绝
可恢复拒绝返回结构化替代建议
可疑动作进入 quarantine
LLM judge 只做辅助 monitor，不做唯一安全边界
```

## 7. 对 RepoHarness 的具体设计建议

### 7.1 工具 profile 应继续沿 Stage 16G 规划推进

Stage 16G.1 已经提出 profile taxonomy：

```text
safe_structured_only
swe_public_core
swe_public_extended
redteam_restricted
```

结合 Codex 和 Claude Code，建议含义如下：

| profile | 目标 | 建议能力 |
| --- | --- | --- |
| `safe_structured_only` | 最保守结构化文件工具 profile。 | `read_file`、`grep`、`glob_files`、`symbol_search`、`edit_file`、`create_file`、`write_file`、`apply_patch`、`git_diff`。 |
| `swe_public_core` | 主 SWE 强化学习默认工具面。 | 结构化文件工具、`apply_patch`、`run_public_command`、`run_project_test`、`scratch_python`、`git_diff`、artifact 回读、任务状态。 |
| `swe_public_extended` | 更接近真实产品态的扩展工具面。 | core 能力加 persistent diagnostic shell、长会话命令、更多 project command、可能的子代理或 MCP schema 预留。 |
| `redteam_restricted` | 安全验证和拒绝恢复训练。 | 故意触发 hidden access、路径逃逸、测试篡改、依赖污染和网络请求的拒绝路径。 |

Codex 的 `exec_command` 和 Claude Code 的 Bash 说明 `swe_public_core` 不能没有公开命令能力。Claude Code 的结构化工具说明 `swe_public_core` 也不能退化成纯 shell。

### 7.2 Stage 16G.2 文件工具必须完成行为闭环

Stage 16G.2A 和 16G.2B 合在一起给出的当前状态是：

```text
write_file、apply_patch、delete_file、move_file、mkdir 已完成 schema 和 profile 暴露；
write_file 和 apply_patch 进入默认工具面；
独立 delete_file / move_file / mkdir 暂不进入 swe_public_core 默认 scaffold；
16G.2B 已经启用 write_file 和 apply_patch 的默认行为；
新文件修改工具仍不能进入 policy loss；
patch hygiene、final patch、TrainingView 投影和 export linkage 留给 16G.2C。
```

Codex `apply_patch` 给出的参考很明确：patch 工具必须进入权限、沙箱、事件和 file change lifecycle。RepoHarness 16G.2B 已经证明 `write_file` 和 `apply_patch` 的基础行为可以运行；后续 16G.2C 和相关验收还要确保这些行为稳定投影成结构化 operation facts：

```text
operation_id
op
path / source_path / target_path
expected hash
result hash
reason 或 denied_reason_code
retryable
partial_failure
rollback_status
training_projection_policy
```

16G.2C 必须继续证明：

```text
工具修改 -> git diff -> final.patch/final.diff -> patch hygiene -> official prediction manifest -> TrainingView / export metadata
```

这条链路不通，工具实现就不能算训练可用。

### 7.3 Stage 16G.3 应成为动态诊断能力的关键阶段

Codex 和 Claude Code 都说明真实 SWE agent 必须能动态验证假设。RepoHarness Stage 16G.3 应优先实现：

```text
run_public_command
run_project_test
scratch_python
```

建议把三者放在共享 public command substrate 上：

```text
统一 cwd 解析
统一 timeout
统一 stdout / stderr / exit code 结构
统一输出截断和 artifact visibility
统一路径脱敏
统一 hidden access detector
统一 permission denial envelope
统一 TrainingView projection
```

`run_project_test` 应支持定向公开测试，而不只是无参数 `run_tests`：

```text
pytest tests/test_file.py::test_case -q
Django test label
Sphinx 或项目自定义 smoke command
轻量 import smoke test
task-declared public command template
```

`scratch_python` 应允许模型写小复现，但默认在临时目录或 public scratch artifact 中运行，不进入 final patch。

### 7.4 diagnostic_shell 应从诊断特例升级为 extended profile 能力

Codex 的 `exec_command` 和 Claude Code 的 Bash 都是正式工具生命周期中的能力。RepoHarness 当前把 `diagnostic_shell` 作为诊断 profile 和侧通道，会带来训练分布问题：

```text
最像真实软件工程的调试行为，被排除在主训练工具面之外；
模型在主训练中学不到如何运行、复现、验证和修复；
训练数据更容易强化静态猜 patch。
```

建议：

1. Stage 16G.3 先实现无持久 session 的 `run_public_command`、`run_project_test`、`scratch_python`。
2. Stage 16G.4 再把 persistent diagnostic shell 纳入 `swe_public_extended`。
3. `swe_public_core` 默认不必包含 persistent shell，但必须覆盖等价 public diagnostic/action capability。

### 7.5 权限拒绝要进入训练数据，而不是被过滤掉

Codex 的 approval event 和 guardian event 说明，高风险动作的允许、拒绝、审查来源和风险理由都是重要事实。

RepoHarness 应记录：

```text
invalid tool call
permission denied
patch apply failure
bad command
unknown file path
hidden access attempt
test tampering attempt
network request attempt
permission denial recovery quality
```

这些不应全部过滤掉。建议分类：

| 行为 | 处理方式 |
| --- | --- |
| 合理公开命令被误拒 | harness bug，修 public command policy。 |
| 不合理命令被拒 | 可作为负样本或局部反馈。 |
| hidden verifier / gold patch 访问 | deterministic hard fail，episode quarantine。 |
| 权限拒绝后改用安全替代路径 | 正向过程信号。 |
| 伪造测试通过、跳过验证、污染依赖 | monitor / quarantine / negative reward candidate。 |

### 7.6 轨迹 schema 应借鉴 Codex rollout trace 的分层

建议 RepoHarness 后续 trajectory 至少分开：

```text
model_visible_input
model_visible_tool_schema
assistant_raw_output
tool_call_raw_arguments
tool_call_normalized_arguments
permission_decision
sandbox_attempt
runtime_raw_output_ref
model_visible_observation
artifact_public_projection
artifact_private_ref
patch_operation_fact
final_patch_fact
verifier_private_fact
reward_public_fact
training_eligibility_fact
```

这样才能回答强化学习中最关键的问题：

```text
模型到底基于什么信息采取了动作？
哪些信息只属于 evaluator / reward？
哪些 token 可以进入 policy loss？
哪些轨迹应该进入 SFT / preference / quarantine？
```

### 7.7 LLM-as-judge 应定位为 reviewer / monitor / quarantine

Codex guardian 的定位对 RepoHarness 有参考价值：它审查 approval request，但不是底层 sandbox。RepoHarness 如果引入 LLM-as-judge，应避免把它当成唯一安全边界。

更合适的位置是：

```text
审批审查辅助
reward hacking monitor
权限拒绝恢复质量评分
final answer 声明和 tool event 一致性检查
quarantine reason 生成
偏好数据辅助标签
```

确定性安全边界仍然应该由 path policy、network policy、runtime-private isolation、patch hygiene 和 verifier boundary 承担。

### 7.8 训练环境和部署环境要保持高保真

`docs/harness_improve/gpt_advice.md` 已经指出 Cursor、Claude Code、Codex、SWE-agent、OpenHands、SWE-Gym、DeepSWE 都共同指向一个原则：

```text
SWE RL 的 harness 必须足够真实，否则 RL 优化的是错误环境。
```

Codex 进一步说明真实产品态至少包含：

```text
正式命令执行工具
正式 patch 工具
权限和沙箱体系
工具事件流
非交互自动化入口
SDK / app-server 协议
扩展工具和 MCP
本地轨迹与诊断
```

RepoHarness 不需要复制所有产品能力，但主 SWE 强化学习默认工具面不能弱到连 mini-SWE-agent 的稳定 Bash 闭环都覆盖不了。

## 8. 对当前 Stage 16G 路线的评价

### 8.1 Stage 16G.0 的方向是合理的

Stage 16G.0 先做能力矩阵、风险报告和 probe，而不是直接改工具，这是合理的。原因是工具面一旦进入训练轨迹，就会影响 policy loss 和数据分布。先建立 baseline contract 可以避免后续“凭感觉放开 shell”或“凭感觉继续收紧”。

### 8.2 Stage 16G.1 的 profile registry 是必要前置

Codex 和 Claude Code 都说明工具是否存在不等于模型是否能学会使用。必须同时知道：

```text
工具 schema
模型是否可见
profile 是否暴露
权限语义
拒绝语义
artifact visibility
TrainingView 投影
是否可进入 policy loss
```

Stage 16G.1 的 tool registry、profile taxonomy 和 training eligibility gate 正好是在补这个缺口。

### 8.3 Stage 16G.2B 已经启用行为，但还不是训练可用终点

Stage 16G.2A 已经完成 schema 和 scaffold 暴露，当时的 `stage16g2a_tool_surface_delta.json` 明确写着：

```text
schema_profile_and_scaffold_exposure_complete_behavior_pending_16G2B
schema_only_denial_until_16G2B
```

当前工作树已经推进到 16G.2B：`stage16g2b_acceptance_summary.json` 显示 `stage16g2b_complete: true`，默认行为启用工具是 `write_file` 和 `apply_patch`，但 `policy_loss_candidate_for_new_tools: false`，并且 `next_required_stage_for_policy_loss` 是 `16G.2C`。因此，16G.2B 应理解为“文件修改行为已打通”，不是“可以直接进入 policy loss”。真正关键的下一步是 16G.2C 的 patch capture、verifier linkage、reward linkage、TrainingView 投影和 export linkage。

### 8.4 Stage 16G.3 和 16G.4 是是否能训练 SWE agent 的分水岭

如果 16G.2 完成后仍没有公开命令、项目测试、scratch Python 和受控诊断 shell，那么 RepoHarness 仍然可能训练出静态猜 patch 的模型。

Codex 和 Claude Code 共同说明：

```text
运行、复现、验证、修复，是软件工程智能体能力的核心。
```

因此 Stage 16G.3 / 16G.4 不应被视为锦上添花，而应视为进入 Stage 20 warm-start 和 Stage 21 formal RL 之前的主门槛。

## 9. 建议的近期硬门槛

在进入真实数据冻结、warm-start 数据生产或 formal RL 前，建议至少满足：

1. `apply_patch` 和 `write_file` 已有真实行为，并且补齐路径边界、hash 检查、失败恢复、patch hygiene、final patch 和 TrainingView 投影。
2. `run_public_command` 能运行公开诊断命令，并返回 stdout、stderr、exit code、timeout、truncation 和 artifact projection。
3. `run_project_test` 能运行参数化公开测试，而不是只有无参数 `run_tests`。
4. `scratch_python` 能运行临时复现脚本，并保证临时脚本不进入 final patch。
5. 权限拒绝有结构化 envelope，并能作为训练负样本、局部反馈或 quarantine 信号保留。
6. hidden verifier、gold patch、test patch、official selector、runtime-private 路径和宿主路径逃逸都有 deterministic hard fail。
7. 模型可见工具 schema、scaffold 暴露、executor registry、public environment 提示和 TrainingView 投影一致。
8. `run_episode(real_episode)` 是所有新工具能力的验收入口。
9. 轨迹 schema 区分模型可见 observation 和 reward-only / evaluator-only 事实。
10. 至少有 Codex-like、Claude-Code-like 和 mini-SWE-agent-like 能力 probe，证明 RepoHarness 的主工具面不再弱于稳定 Bash baseline。

## 10. 最终建议

Codex 不是 RepoHarness 的替代品，因为它没有 SWE-Bench dataset、hidden verifier、reward builder 和 verl fully async policy loss 链路。Claude Code 也不是 RepoHarness 应该复制的源码模板，因为产品态交互和训练态安全边界不同。

但二者共同给出的设计约束非常清楚：

```text
主训练 harness 必须像真实开发代理一样让模型完成定位、复现、修改、验证和收口；
安全边界必须由 sandbox、权限、路径隔离、artifact hygiene 和审计实现；
训练轨迹必须精确区分模型看见的内容、工具实际做的事情和 evaluator 私有事实；
不能为了安全把动作空间压到失真。
```

因此，RepoHarness 近期最重要的工作不是直接进入 Stage 17A 数据 registry，而是在 16G.2B 已完成行为启用的基础上，继续完成 Stage 16G.2C、16G.3 和 16G.4。只有在这些工具能力、权限边界和训练投影稳定后，Stage 17 之后的数据治理、Stage 20 warm-start 和 Stage 21 formal RL 才有足够可信的训练环境基础。
