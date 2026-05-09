# 第 3 章 Claude Code Tooling Lessons：命令工具和基础工具设计取舍

## 本章解决什么问题

你在第 2 章已经理解了命令工具的基础概念：`bash`、`run_tests`、setup command、final verifier、`stdout`、`stderr`、`exit_code`、timeout、进程树和输出落盘。

本章进一步回答一个更工程化的问题：**Claude Code 的命令工具和其他内置工具做到了什么程度？这些实现对 RepoHarness 有什么借鉴意义？RepoHarness 第一版应该参考哪些设计，哪些暂缓实现，理由是什么？**

结论先放在前面：

- RepoHarness 第一版不应该复制 Claude Code 的完整交互式产品能力，例如终端界面、用户审批弹窗、MCP 市场、技能系统、自动安全分类器、远程代理和后台长期任务。
- RepoHarness 第一版必须学习 Claude Code 的工具契约、工具结果配对、schema 校验、权限判定顺序、只读工具并发、写工具串行、路径边界、命令 timeout、进程树清理、输出 artifact、读后再写防并发覆盖这些基础设施。
- 命令工具不能只是 `subprocess.run(command, shell=True)`。在训练和评测场景中，命令工具同时影响安全、可复现性、轨迹质量、reward 可信度和失败诊断。
- RepoHarness 的 `run_tests` / final verifier 应该是独立于普通 `bash` 的结构化评测入口。Claude Code 没有这个训练评测特化入口，所以这里需要你自己的设计，而不是照搬 Claude Code。

---

## 1. 本次阅读的 Claude Code 源码范围

本章主要参考这些实现：

| 源码位置 | 关注点 |
| --- | --- |
| `reference/claude-code-typescript-src/Tool.ts` | 工具统一接口、工具上下文、默认 fail-closed 行为。 |
| `reference/claude-code-typescript-src/tools.ts` | 内置工具注册、工具过滤、内置工具和 MCP 工具合并、稳定排序。 |
| `reference/claude-code-typescript-src/services/tools/toolExecution.ts` | 单次工具调用生命周期：查找工具、schema 校验、输入校验、hook、权限、执行、结果映射、输出持久化、错误 tool_result。 |
| `reference/claude-code-typescript-src/services/tools/toolOrchestration.ts` | 工具并发编排：只读并发，非只读串行。 |
| `reference/claude-code-typescript-src/tools/BashTool/BashTool.tsx` | Bash 工具 schema、命令执行、进度、timeout、后台任务、大输出落盘、exit code 语义。 |
| `reference/claude-code-typescript-src/tools/BashTool/bashPermissions.ts` | Bash 权限主流程、命令解析、安全检查、deny / ask / allow 规则顺序。 |
| `reference/claude-code-typescript-src/tools/BashTool/readOnlyValidation.ts` | 只读命令判定、命令 allowlist、危险 git 场景和命令注入保护。 |
| `reference/claude-code-typescript-src/tools/BashTool/pathValidation.ts` | 命令参数中的路径提取、危险删除路径、读写路径边界。 |
| `reference/claude-code-typescript-src/utils/Shell.ts` | shell 选择、命令 spawn、工作目录更新、沙箱包装、输出文件描述符。 |
| `reference/claude-code-typescript-src/utils/ShellCommand.ts` | timeout、kill、后台化、输出大小 watchdog、进程树清理。 |
| `reference/claude-code-typescript-src/utils/task/TaskOutput.ts` | 命令输出的单一事实来源、文件模式输出、进度 tail、内存溢出落盘。 |
| `reference/claude-code-typescript-src/tools/FileReadTool/FileReadTool.ts` | 读文件工具、文件大小限制、token 限制、行范围、读缓存、设备文件阻断。 |
| `reference/claude-code-typescript-src/tools/FileEditTool/FileEditTool.ts` | 精确替换编辑、必须先读再改、mtime 防并发覆盖、结构化 patch。 |
| `reference/claude-code-typescript-src/tools/FileWriteTool/FileWriteTool.ts` | 新建和覆盖文件、必须先读再覆盖、防止外部修改被覆盖。 |
| `reference/claude-code-typescript-src/tools/GrepTool/GrepTool.ts` | ripgrep 包装、结果分页、默认上限、相对路径输出、只读并发。 |
| `reference/claude-code-typescript-src/tools/GlobTool/GlobTool.ts` | glob 文件发现、结果数量上限、只读并发。 |
| `reference/claude-code-typescript-src/tools/AgentTool/AgentTool.tsx` | 子代理工具、工作树隔离、异步代理、代理工具池。 |
| `reference/claude-code-typescript-src/tools/MCPTool/MCPTool.ts` | MCP 工具统一包装思路。 |
| `reference/claude-code-typescript-src/tools/ToolSearchTool/ToolSearchTool.ts` | 工具延迟发现，降低工具 schema 对上下文的占用。 |

这份文档只讨论对 RepoHarness 第一版有价值的工程设计，不尝试完整讲解 Claude Code 的交互式用户体验实现。

---

## 2. Claude Code 工具系统的总体设计

Claude Code 的工具不是“函数表”，而是带完整生命周期元数据的对象。`Tool.ts` 中的核心字段包括：

- `name`：工具唯一名称。
- `description()` / `prompt()`：给模型看的工具说明。
- `inputSchema`：使用 Zod 做结构化输入校验。
- `outputSchema`：工具输出结构。
- `call()`：真正执行工具。
- `validateInput()`：工具自己的输入值校验，例如文件是否已经读过、路径是否存在、参数是否冲突。
- `checkPermissions()`：工具自己的权限逻辑。
- `isReadOnly()`：是否只读。
- `isConcurrencySafe()`：是否可以和其他工具并发。
- `isDestructive()`：是否具有破坏性。
- `maxResultSizeChars`：结果过大时是否持久化到磁盘。
- `mapToolResultToToolResultBlockParam()`：把工具内部输出映射为模型可见的 `tool_result`。

Claude Code 通过 `buildTool()` 给工具补默认值。最重要的是两个默认值：

- `isReadOnly` 默认是 `false`。
- `isConcurrencySafe` 默认是 `false`。

这就是 fail-closed：新工具如果没有明确声明自己只读、并发安全，就会被当成可能写入、不能并发的工具。

**对 RepoHarness 的借鉴意义：**

RepoHarness 第一版也应该有统一的 `Tool` 契约，不能每个工具各跑各的执行逻辑。你至少需要这些字段：

```text
Tool
  name
  description
  input_schema
  output_schema
  is_read_only
  is_concurrency_safe
  is_destructive
  check_permissions(input, context)
  validate_input(input, context)
  call(input, context)
  map_result_to_observation(output)
  max_result_preview_bytes
```

其中 `map_result_to_observation` 对训练和评测尤其重要，因为模型看到的 observation、事件里记录的结构化输出、落盘的 artifact 不能混在一起。模型可以看到简短摘要，训练导出和失败诊断可以引用完整 artifact。

---

## 3. 工具执行生命周期应该怎么学

Claude Code 的单次工具调用不是直接 `tool.call(input)`，而是经过固定管线：

```text
查找工具
  -> input_schema 校验
  -> validateInput
  -> PreToolUse hooks
  -> checkPermissions / canUseTool
  -> tool.call
  -> mapToolResultToToolResultBlockParam
  -> 大输出持久化
  -> PostToolUse hooks
  -> 生成 tool_result
```

其中几个细节对 RepoHarness 很重要：

1. **未知工具也会生成 tool_result。**  
   如果模型调用了不存在的工具，Claude Code 会返回一个 error tool_result，而不是直接中断消息流。这样可以维持 tool_use / tool_result 配对。

2. **schema 错误也会生成 tool_result。**  
   模型传错参数类型时，工具执行层返回结构化错误，让模型下一轮有机会修正。

3. **权限拒绝也会生成 tool_result。**  
   权限拒绝不是系统崩溃，而是一次环境反馈。

4. **工具异常也会生成 tool_result。**  
   工具抛出的异常会被包装为 error tool_result。

5. **结果过大会落盘并给模型 preview。**  
   Claude Code 的 `toolResultStorage.ts` 会把大输出写到 `tool-results` 目录，再给模型一个 `<persisted-output>` 摘要。

**RepoHarness 第一版应该参考：**

RepoHarness 的工具执行层必须保证：**每一个 assistant tool call 都有一个对应 ToolResult**。状态可以是：

```text
ok
error
denied
timeout
interrupted
```

无论是未知工具、schema 错误、路径拒绝、命令超时、用户中断、进程崩溃，都不能漏掉 ToolResult。否则模型协议会断，trajectory 也会不可训练。

RepoHarness 可以暂缓 hooks，因为你的第一版不是面向用户定制自动化。但是执行管线里应该保留 hook 插槽或 middleware 插槽，未来可以用于：

- 注入 secret scanner。
- 注入 trajectory redaction。
- 注入企业策略。
- 注入额外 telemetry。
- 注入课程化或 benchmark 特定限制。

---

## 4. 工具并发：只读并发，写入串行

Claude Code 的 `toolOrchestration.ts` 会把模型同一轮输出的多个工具调用分批执行：

- 连续的并发安全工具可以一起并发。
- 非并发安全工具单独串行执行。
- 工具的 `contextModifier` 不会在并发批次中立即生效，而是等批次结束后按 tool_use 顺序应用。

这个设计解决的是“模型一轮可能同时请求多个工具”的问题。例如模型同时请求读 5 个文件，这些工具可以并发；但如果模型同时请求改文件和跑命令，就不能随便并发。

**RepoHarness 第一版应该参考：**

第一版可以实现一个简单规则：

```text
FileRead / Grep / Glob / ListFiles:
  is_read_only = true
  is_concurrency_safe = true

FileEdit / FileWrite / Bash / RunTests:
  is_read_only = false
  is_concurrency_safe = false
```

这里把普通 `bash` 和 `run_tests` 都先当作不并发，是保守但正确的。测试命令可能产生缓存文件，普通命令也可能改变工作目录或文件系统状态。后续再按命令分类放宽只读诊断命令并发。

---

## 5. BashTool 的真正复杂度

Claude Code 的 BashTool 不是一个简单 shell wrapper。它包含这些能力：

- 输入 schema：`command`、`timeout`、`description`、`run_in_background`、`dangerouslyDisableSandbox`。
- 输出 schema：`stdout`、`stderr`、`interrupted`、`backgroundTaskId`、`returnCodeInterpretation`、`persistedOutputPath` 等。
- 命令只读判断：`ls`、`cat`、`rg`、`grep`、`find`、`git status` 等受限命令可以视为只读。
- 命令语义解释：`grep` 返回 1 表示没有匹配，不一定是错误；`diff` 返回 1 表示有差异，也不一定是执行失败。
- 命令安全解析：处理管道、重定向、环境变量、wrapper 命令、shell 注入、复杂 compound command。
- 路径约束：从命令参数中提取读写路径，检查是否在允许范围内。
- timeout 和进程清理：超时后 kill 进程树。
- 输出处理：stdout/stderr 合并到文件，进度通过 tail 输出文件获取，大输出持久化。
- 后台任务：长命令可以后台运行，并在完成时把通知重新注入模型上下文。
- 沙箱包装：在可用平台上把命令包进 sandbox adapter。

这说明一个关键事实：**只要允许模型执行任意 shell 字符串，复杂度就会迅速逼近一个安全产品。**

**RepoHarness 第一版不应该照搬完整 BashTool。**

你的第一版应该刻意收窄：

```text
bash v1
  只作为诊断命令入口
  默认不允许网络命令
  默认不允许复杂 shell 语法
  默认不允许后台任务
  默认不允许任意写入 home directory
  默认不允许 workspace 外路径
  所有命令必须有 timeout
  所有输出必须有 preview 和 artifact
```

第一版可以支持的命令类别：

| 类别 | 第一版策略 | 理由 |
| --- | --- | --- |
| `pwd`、受限 `ls`、受限 `find` | 允许 | 方便模型理解 workspace，风险低。 |
| `python -m compileall .`、`ruff check .`、`mypy .`、`tsc --noEmit` | 允许或任务配置声明后允许 | 属于诊断，不直接产生 reward。 |
| `pytest`、`npm test`、`pnpm test`、`go test` | 路由到 `run_tests` | 测试语义必须进入 VerifierResult，不能普通化。 |
| `git diff`、`git status` | 允许只读形式 | 对 agent 判断修改状态很有用。 |
| `git clone`、`git fetch`、`git pull`、`git remote add` | 默认拒绝 | 会引入外部状态，破坏可复现性。 |
| `curl`、`wget`、`ssh`、`scp` | agent run 阶段默认拒绝 | 网络访问会污染任务、泄漏信息、引入不可复现依赖。 |
| `rm -rf`、`sudo`、`chmod -R`、`chown -R` | 默认拒绝或需要任务显式配置 | 破坏性强，且训练数据价值低。 |
| 管道、重定向、命令替换、后台进程 | 默认拒绝，后续按需允许 | shell 解析复杂，第一版不值得承担。 |

---

## 6. 命令执行器应该参考哪些实现细节

Claude Code 的 `Shell.ts` 和 `ShellCommand.ts` 对 RepoHarness 很有启发：

1. **每个命令都有 timeout。**
2. **不要只杀 shell 进程，要清理进程树。**
3. **命令输出要有单一事实来源。**
4. **大输出不能无限塞进模型上下文。**
5. **命令执行必须记录 `cwd`。**
6. **命令执行时的环境变量不能直接继承宿主机完整环境。**
7. **命令结束后要区分正常失败和 harness 错误。**

RepoHarness 第一版的 `CommandExecutor` 建议接口：

```text
CommandExecutor.run(command_request) -> CommandResult

CommandRequest
  argv_or_command
  cwd
  env
  timeout_ms
  stdin_policy
  network_policy
  workspace_root
  output_artifact_dir

CommandResult
  exit_code
  status: ok | failed | timeout | interrupted | spawn_error
  stdout_preview
  stderr_preview
  stdout_artifact_ref
  stderr_artifact_ref
  duration_ms
  timed_out
  interrupted
  cwd
  command_hash
```

第一版最好优先使用参数数组执行确定命令，例如：

```text
["python", "-m", "pytest", "-q"]
["git", "status", "--short"]
```

只有 `bash` 诊断工具才接收 shell 字符串，并且 shell 字符串经过分类器或 allowlist。这样你可以把大部分核心路径保持为可验证、可复现、低风险的 argv 执行。

---

## 7. 文件读写工具的关键借鉴

Claude Code 的 Read / Edit / Write 工具非常值得学习，因为它们不是简单文件系统 API，而是解决了 agent 编辑真实代码时最常见的失败模式。

### 7.1 Read 工具

Claude Code 的 FileReadTool 有这些关键设计：

- 读文件支持 `offset` 和 `limit`，避免大文件一次性塞满上下文。
- 对文件大小和 token 数做限制。
- 阻止读取会阻塞或无限输出的设备文件，例如 `/dev/zero`、`/dev/random`、`/dev/stdin`。
- 读取后把内容、mtime、offset、limit 存到 `readFileState`。
- 同一范围重复读取且文件没变时，可以返回“文件未变化”的 stub，减少上下文浪费。
- 图片、PDF、Notebook 是特殊类型，不和普通文本混在一起。

RepoHarness 第一版应该实现：

- `read_file(path, offset?, limit?)`
- 路径必须在 workspace 内。
- 默认最大字节数和最大行数。
- 输出包含 `start_line`、`end_line`、`total_lines`、`truncated`。
- read state 记录 `content_hash`、`mtime`、`offset`、`limit`。

RepoHarness 第一版可以暂缓：

- 图片读取。
- PDF 读取。
- Notebook 专用读取。
- 基于模型 token 计数的精确限制。
- 重复读取去重 stub。

理由是第一版主要面向 coding agent 训练和评测，文本源码读取是核心，复杂多模态读取不是第一优先级。

### 7.2 Edit 工具

Claude Code 的 FileEditTool 有几个非常重要的约束：

- 编辑前必须已经读过目标文件。
- 如果文件在读取后被外部修改，拒绝写入，要求重新读取。
- `old_string` 必须唯一匹配；如果有多个匹配，要求提供更多上下文或显式 replace all。
- 生成结构化 patch。
- 写入后更新 read state，避免下一步基于旧内容编辑。

这套设计对 RepoHarness 很重要，因为训练轨迹里最糟糕的一类数据是“模型在没有看清文件状态时乱改”，或者“工具悄悄覆盖了并发修改”。第一版应该直接参考这个策略。

RepoHarness 第一版应该实现：

```text
edit_file(path, old_string, new_string, replace_all=false)

要求：
  path 在 workspace 内
  文件必须先被 read_file 完整读取
  old_string 必须存在
  replace_all=false 时 old_string 必须唯一
  文件 mtime 或 content_hash 自读取后不能变化
  返回 structured_patch 和 diff preview
```

### 7.3 Write 工具

Claude Code 的 FileWriteTool 用于创建或覆盖文件，但覆盖已有文件时也要求先读过文件，并检查 mtime。

RepoHarness 第一版可以有两个工具：

- `create_file(path, content)`：只允许创建不存在的文件。
- `write_file(path, content)`：覆盖已有文件前必须先读过完整文件。

比单一 `write_file` 更清晰，因为训练分析时可以区分“创建文件”和“覆盖文件”。如果想简化，也可以保留一个 `write_file`，但输出里必须有 `type = create | update`。

---

## 8. 搜索工具应该作为专用工具，而不是全靠 Bash

Claude Code 有 `GrepTool` 和 `GlobTool`，虽然 Bash 也能跑 `rg`、`find`、`ls`。这不是重复，而是为了：

- 给模型更清晰的工具语义。
- 避免模型构造复杂 shell。
- 统一路径权限检查。
- 控制结果数量，减少上下文污染。
- 让只读工具可以并发。
- 让输出结构更适合训练和诊断。

RepoHarness 第一版应该实现：

```text
list_files(path?, pattern?)
grep(pattern, path?, glob?, mode?, limit?, offset?)
read_file(path, offset?, limit?)
```

其中 `grep` 可以内部调用 ripgrep，但对模型暴露结构化参数，不暴露任意 shell 字符串。

第一版应该有默认上限：

- glob / list_files 默认最多返回 100 或 200 个路径。
- grep 默认最多返回 200 或 250 行。
- 如果结果被截断，ToolResult 必须标注 `truncated = true`，并提示模型缩小搜索范围或使用 offset 分页。

---

## 9. 权限设计：学顺序，不学完整产品形态

Claude Code 的权限系统很复杂，因为它要服务交互式用户：

- 用户可以一次性批准。
- 用户可以永久批准。
- 用户可以永久拒绝。
- 权限规则来自用户设置、项目设置、命令行参数、session。
- 权限拒绝可以触发用户界面。
- auto mode 可以调用分类器判断是否允许。
- hooks 可以改写输入或权限决策。

RepoHarness 第一版不是交互式产品，所以不应该复制这些复杂体验。但是你应该学习它的**判定顺序**：

```text
1. 工具是否被整体 deny。
2. 工具是否被整体 ask。
3. 工具自己的 check_permissions。
4. 工具内部 deny 立即生效。
5. 内容级安全检查不可绕过。
6. 当前权限模式是否允许。
7. 工具 allowlist 是否允许。
8. passthrough 在非交互批量评测中变成 deny。
```

RepoHarness 第一版建议：

```text
PermissionDecision
  decision: allow | deny
  reason
  rule_id?
  mode
  tool_name
  input_summary
```

不要在第一版实现交互式 `ask`，而是在配置校验阶段禁止批量评测使用需要人工确认的模式。也就是说：

- 单任务开发模式可以把 `ask` 显示为终端确认。
- 批量 evaluation runner 中，`ask` 必须提前转成 `deny` 或配置错误。

---

## 10. 沙箱设计：学边界分层，不承诺生产级安全

Claude Code 把 permission 和 sandbox 分开：

- permission 决定工具调用是否允许。
- sandbox 决定允许执行后进程在什么边界内运行。

这与 `docs/05-workspace-sandbox-and-permissions.md` 当前口径一致。RepoHarness 必须保持这个区分。

第一版应该实现的不是“安全沙箱产品”，而是“可复现执行边界”：

```text
Workspace boundary
  路径解析
  symlink 处理
  cwd 限制
  diff 基线
  excluded_diff_paths

Command boundary
  timeout
  env whitelist
  network policy
  process tree cleanup
  stdout/stderr artifact

Docker execution mode
  用于可复现评测
  不宣称多租户安全
  不宣称生产级逃逸防护
```

Claude Code 的 Bash sandbox 有很多平台和产品细节，第一版不需要复制。RepoHarness 更应该把精力放在：

- source checkout / setup workspace / agent run workspace 三阶段隔离。
- final verifier strict patch replay。
- artifact 和 reward metadata 的可信记录。

---

## 11. `run_tests` 和 verifier 是 RepoHarness 自己必须新增的能力

Claude Code 的 BashTool 可以运行 `pytest` 或 `npm test`，但它不会把测试结果变成训练评测所需的结构化对象。RepoHarness 的定位不同，所以必须有专用工具：

```text
run_tests(input) -> VerifierResult
```

`run_tests` 不是普通命令工具。它应该：

- 只能执行任务配置中的 feedback verifier 命令，或经过任务配置声明的测试命令。
- 由 Workspace Adapter 执行命令。
- 由 VerifierParser 解析输出。
- 返回 `VerifierResult`，包括 `parser_id`、`parser_version`、`parser_confidence`、`test_cases`、`fail_to_pass`、`pass_to_pass`、`timeout`、`exit_code`。
- 写入 events 和 artifacts。
- 可以给模型作为中间反馈。
- 不能直接替代 final verifier。

final verifier 也不应该是普通 `bash`。它应该是 Eval Runner 在 agent 停止后执行的评测路径，必要时使用 strict patch replay：

```text
source checkout
  -> verification workspace
  -> restore dependency_state
  -> apply final.patch
  -> run final verifier
  -> parse VerifierResult
  -> derive reward.json
```

这部分是 RepoHarness 相比 Claude Code 的核心差异，不要因为 Claude Code 没有 `run_tests` 专用工具就省略它。

---

## 12. 大输出和 artifact：必须第一版实现

Claude Code 的工具结果持久化设计对 RepoHarness 很重要：

- 工具输出超过阈值时，完整内容写入磁盘。
- 模型只看到 preview 和文件引用。
- 空输出也会被替换成明确提示，避免模型看到空 tool_result 后异常续写。
- transcript 中保留模型实际看到的内容。

RepoHarness 第一版应该实现更训练友好的版本：

```text
ToolResult
  stdout_preview
  stderr_preview
  artifact_refs
  truncated

artifacts/tool_outputs/
  tool_0001.stdout.txt
  tool_0001.stderr.txt
```

注意：模型 observation、events、artifact 三者不能混为一谈。

- observation：模型看见的短内容。
- events：机器可分析的结构化事实。
- artifact：完整原始材料。

这样以后导出 SFT / RL 数据时，可以通过 observation mask 和 artifact metadata 控制哪些内容进训练样本，哪些只用于审计和诊断。

---

## 13. 后台任务：第一版建议不实现

Claude Code 支持后台 Bash 和后台 Agent，因为它是交互式开发工具：

- 长命令可以后台跑。
- 用户可以继续输入。
- 命令完成后把通知注入会话。
- 后台任务可以被停止。
- 如果命令像是在等待交互输入，会提醒用户。

RepoHarness 第一版是训练和评测 harness，不需要这种交互式长期任务体验。后台任务会带来很多复杂性：

- trajectory 的时间顺序更难解释。
- 同一时间多个进程可能修改 workspace。
- final.diff 的归因更难。
- timeout 和任务全局预算更难管理。
- 失败复现更难。

第一版建议：

```text
不支持 run_in_background
不支持后台 shell task
不支持命令完成后异步注入 task_notification
```

所有命令同步执行，受单次 timeout 和全局 run budget 控制。以后如果要支持长时间服务进程，可以单独设计 `service_process` 或 `dev_server` 工具，而不是直接开放后台 Bash。

---

## 14. 子代理工具：先保留 Scaffold 接口，不复制 AgentTool

Claude Code 的 AgentTool 很强：

- 可以选择不同 agent 类型。
- 可以同步或异步运行。
- 可以用 git worktree 隔离。
- 可以继承或重建工具池。
- 可以有独立 MCP。
- 可以有独立权限模式。
- 可以把进度和结果回传主会话。

RepoHarness 的 `docs/09-agent-scaffolds-and-multi-agent.md` 已经设计了 Scaffold 接口，这是正确方向。第一版不建议复制 Claude Code AgentTool 的完整能力。

RepoHarness 第一版应该实现：

```text
Scaffold
  single_shot
  simple_react
  planner_coder_verifier
```

这些 scaffold 复用同一个 Agent Loop 和同一个工具系统，只改变 prompt、预算和阶段策略。这样能支持训练和评测，又不引入异步子代理、工作树清理、代理通信、远程会话等复杂度。

可以暂缓：

- agent 自己调用 AgentTool 生成子代理。
- 异步子代理。
- 代理间消息系统。
- per-agent MCP。
- 自动 worktree isolation。
- 子代理权限冒泡。

理由是第一版的核心目标是收集可控、可复现、可训练的 agentic trajectory。多代理系统会显著增加轨迹解释难度，应该在单代理和 scaffold 跑稳定后再加入。

---

## 15. MCP、ToolSearch、Skills、Web 工具：第一版不做或只留接口

Claude Code 的 MCPTool、ToolSearchTool、SkillTool、WebFetchTool、WebSearchTool 面向通用开发产品，很有价值，但对 RepoHarness 第一版不是核心。

### MCP

暂缓实现。原因：

- MCP 工具来自外部服务，输出和副作用不一定可复现。
- MCP 鉴权、权限、连接生命周期会显著增加复杂度。
- 训练评测场景更需要固定工具面。

可以在对象模型中保留：

```text
ExternalToolProvider
McpToolAdapter
```

但第一版不接入。

### ToolSearch

暂缓实现。原因：

- 第一版工具数量少，不需要延迟发现。
- ToolSearch 主要解决大型工具池占用上下文和模型找工具的问题。
- RepoHarness 第一版更需要工具面固定、可审计、可复现。

### Skills / Plugins

暂缓实现。原因：

- 它们是产品扩展生态，不是评测 harness 必需能力。
- 会引入额外 prompt 来源，不利于第一版训练数据可控。

### WebFetch / WebSearch

agent run 阶段默认不实现。原因：

- 网络会破坏可复现性。
- 网络内容会随时间变化。
- 对 benchmark 可能造成信息泄漏。

如果任务确实需要网络，应该只放在 setup workspace，并写入 `network_policy` 和 artifacts。

---

## 16. RepoHarness 第一版工具清单建议

第一版建议工具面如下：

| 工具 | 是否第一版实现 | 参考 Claude Code | 理由 |
| --- | --- | --- | --- |
| `read_file` | 实现 | FileReadTool | 编码任务必需；支持 offset / limit；记录 read state。 |
| `edit_file` | 实现 | FileEditTool | 精确替换比整文件覆盖更适合训练；可生成 patch。 |
| `write_file` 或 `create_file` | 实现 | FileWriteTool | 支持新增文件和必要覆盖；覆盖前要求已读。 |
| `list_files` / `glob` | 实现 | GlobTool | 文件发现必需；只读并发；限制结果数量。 |
| `grep` | 实现 | GrepTool | 搜索代码必需；不要让模型写复杂 shell。 |
| `bash` | 限制实现 | BashTool | 只做诊断命令；严格 allowlist；默认拒绝复杂 shell。 |
| `run_tests` | 实现 | RepoHarness 自己设计 | 结构化 verifier feedback，不能用普通 Bash 替代。 |
| `final_verifier` | 实现为 Eval Runner 路径 | RepoHarness 自己设计 | 最终 reward 和 success rate 来源。 |
| `git_status` / `git_diff` | 可以实现为专用只读工具 | BashTool 的 git 只读经验 | 比让模型跑任意 git 命令更稳定。 |
| `todo` / `plan` | 可选 | TodoWriteTool | 对模型行为有帮助，但不是评测基础设施必需。 |
| `agent` | 暂缓 | AgentTool | 第一版先做 scaffold，不开放递归子代理。 |
| `mcp` | 暂缓 | MCPTool | 外部工具破坏可复现性，复杂度高。 |
| `tool_search` | 暂缓 | ToolSearchTool | 第一版工具少，不需要延迟发现。 |
| `web_fetch` / `web_search` | 暂缓 | WebFetch / WebSearch | agent run 阶段网络默认关闭。 |
| `background_task` | 暂缓 | LocalShellTask | 异步输出和 workspace 归因复杂。 |
| `lsp` | 暂缓 | LSPTool / diagnostic tracking | 第一版可以用命令行类型检查替代。 |

---

## 17. 第一版实现优先级

建议按这个顺序实现，而不是按 Claude Code 的工具数量横向铺开：

### 第 1 阶段：工具协议和执行器

目标是让工具调用稳定进入 trajectory。

必须完成：

- Tool schema。
- ToolResult schema。
- Unknown tool -> error ToolResult。
- Schema error -> error ToolResult。
- Permission denied -> denied ToolResult。
- Timeout -> timeout ToolResult。
- Interrupted -> interrupted ToolResult。
- 每个 tool_call 都配对 tool_result。
- events.jsonl 记录工具生命周期。

### 第 2 阶段：文件和搜索工具

目标是让 coding agent 能可靠读写代码。

必须完成：

- `read_file`
- `edit_file`
- `write_file` 或 `create_file`
- `grep`
- `list_files`
- workspace boundary
- read-before-write
- mtime / content_hash 防并发覆盖

### 第 3 阶段：命令和测试工具

目标是让 agent 能获得诊断和测试反馈。

必须完成：

- `CommandExecutor`
- 受限 `bash`
- `run_tests`
- VerifierParser
- stdout/stderr artifact
- command timeout
- process tree cleanup
- test command 路由

### 第 4 阶段：final verifier 和训练导出

目标是让运行结果可信、可复现、可训练。

必须完成：

- final verifier。
- strict patch replay。
- `reward.json`
- `verifier.json`
- `final.patch`
- `final.diff`
- transcript / events / artifacts 对齐。
- SFT / RL export 所需 masks 和 metadata。

---

## 18. 需要避免的三个设计陷阱

### 18.1 把 Bash 当成万能工具

如果所有事情都通过 Bash 做，短期实现很快，但会带来问题：

- 训练轨迹里看不清模型到底是在读文件、搜文件、跑测试还是写文件。
- 权限和路径检查只能靠脆弱字符串解析。
- 测试结果无法稳定转成 VerifierResult。
- 大输出和分页难统一。
- future RL reward 难归因。

所以第一版应该专用工具优先，Bash 只作为诊断兜底。

### 18.2 把测试命令当普通命令

测试命令必须走 `run_tests` 或 final verifier。普通 Bash 里的测试结果可以作为模型观察，但不能作为 success rate 或 reward 依据。

否则模型可以只跑容易通过的测试，或者跑了错误目录下的测试，而 harness 却误以为任务成功。

### 18.3 只记录模型看见的文本，不记录执行事实

训练和评测 harness 必须记录机器可分析事实：

- 命令实际 argv 或 command。
- cwd。
- timeout。
- exit code。
- stdout/stderr artifact。
- parser confidence。
- test case 级结果。
- permission decision。
- workspace snapshot。
- diff 基线。

模型看到的 observation 只是事实的一种摘要，不能替代 events 和 artifacts。

---

## 19. 和当前设计文档的对齐建议

结合 `docs/05-workspace-sandbox-and-permissions.md` 和本次 Claude Code 阅读，当前 RepoHarness 设计方向是正确的。重点需要继续坚持这些口径：

- permission 和 sandbox 分开。
- Task Adapter 不执行 baseline。
- Eval Runner 协调 Workspace Adapter 和 Verifier 生成 BaselineResult。
- BaselineResult 不持有正式 `agent_start_snapshot`。
- `run_tests` 和 final verifier 生成结构化 `VerifierResult`。
- ToolResult 配对不变量必须覆盖所有错误路径。
- command output 必须 artifact 化。
- agent run 阶段默认拒绝网络命令。
- Docker execution mode 只表述为可复现执行环境，不表述为生产级安全沙箱。

额外建议补进实现计划：

```text
CommandExecutor 是 Workspace Adapter 的一部分，不是 BashTool 自己私有实现。

BashTool / RunTests / FinalVerifier 都调用同一个 CommandExecutor。

Tool execution layer 负责 tool_call -> ToolResult 配对。

Workspace Adapter 负责 cwd、env、timeout、进程树、输出 artifact。

Verifier 负责命令输出解析和 VerifierResult，不负责依赖安装。
```

这能避免未来出现三套命令执行路径：Bash 一套、测试一套、final verifier 一套。三套执行路径会直接破坏可复现性和诊断一致性。

---

## 20. 最小可用但不玩具的第一版边界

RepoHarness 第一版如果实现下面这些，就已经不是 toy project：

```text
统一 Tool 接口
统一 ToolExecutor 生命周期
严格 tool_use / tool_result 配对
只读工具并发、写工具串行
read_file / edit_file / write_file / grep / glob
受限 bash
专用 run_tests
final verifier
CommandExecutor
workspace boundary
timeout 和进程树清理
stdout/stderr artifact
read-before-write 防覆盖
三阶段 workspace 生命周期
strict patch replay
VerifierResult + TestCaseResult
reward.json
trajectory export masks
```

第一版可以明确不实现：

```text
交互式权限弹窗
自动安全分类器
后台 Bash 任务
递归子代理工具
MCP 工具市场
Skills / Plugins
WebSearch / WebFetch
LSP 常驻诊断
远程 agent
终端 UI
```

这个取舍是合理的：你保留了工业级 agent infra 的核心骨架，但删掉了交互产品、插件生态和远程协作能力。对于训练和评测型 harness，这是更清晰、更可控、更可复现的第一版。

---

## 21. 最后一句话

Claude Code 给 RepoHarness 的最大启发不是“工具越多越工业级”，而是：**工具调用必须被当成可审计、可回放、可权限判定、可结构化记录的状态转移。**

只要第一版把工具契约、执行事实、权限决策、workspace 边界、测试解析和 trajectory 存储打牢，即使工具数量很少，也已经是工业级基础设施的正确起点。反过来，如果只是给模型一个任意 Bash，即使用了 Docker，也仍然更像一个难以诊断的实验脚本，而不是面向训练和评测的 agent harness。
