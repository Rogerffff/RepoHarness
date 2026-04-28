# Tool System And Orchestration

## 设计目标

RepoHarness 的工具系统必须像能力契约，而不是普通函数列表。每个工具要清楚描述自己的输入、输出、安全属性、权限逻辑、并发能力和结果格式。

Tool System 的职责是把模型请求转换成受控的工具调用。它不应该直接绕过 workspace boundary 写文件或执行进程。所有文件写入、patch 应用、shell 命令和测试命令最终都必须通过 Workspace / Sandbox Adapter。

## Tool 契约

未来实现中的 `Tool` 至少包含：

- `name`
- `description`
- `input_schema`
- `output_schema`
- `validate_input`
- `check_permissions`
- `call`
- `is_read_only`
- `is_concurrency_safe`
- `is_destructive`
- `max_result_size`

默认策略应保守：没有明确声明并发安全的工具不并发；没有明确声明只读的工具按可能写入处理。

## 第一版工具清单

- `list_files`：列出任务工作区内文件，默认只读、可并发。
- `read_file`：读取文件片段，默认只读、可并发。
- `search`：调用 ripgrep 或等价搜索，默认只读、可并发。
- `write_file`：写入文件，默认不并发、需要权限检查。
- `apply_patch`：应用 patch，默认不并发、需要权限检查。
- `bash`：执行命令，默认不并发、需要权限检查和 timeout。
- `run_tests`：运行任务定义中的测试命令，默认不并发。
- `git_diff`：输出当前 patch，默认只读、可并发。

## 工具执行管线

一次工具调用必须经过：

1. 根据工具名查找 tool definition。
2. 校验输入 schema。
3. 执行工具级 `validate_input`。
4. 调用 Permission System。
5. 如果工具需要读写文件或执行命令，通过 Workspace / Sandbox Adapter 执行。
6. 捕获异常、timeout 和非零 exit code。
7. 截断或保存超大输出。
8. 捕获 workspace diff 或 output artifact 引用。
9. 格式化 tool result。
10. 写入 transcript 和 events。

## 工具与 Workspace Adapter 的分工

`list_files`、`read_file` 和 `search` 仍然需要通过 workspace 路径解析，避免访问任务工作区外的文件。

`write_file` 和 `apply_patch` 负责校验输入格式和描述写入意图，但实际路径解析、符号链接处理、文件写入、patch 应用和 diff 捕获由 Workspace Adapter 完成。

`bash` 负责表达命令请求、timeout、环境变量和输出限制，但实际进程启动、工作目录、进程中断、stdout/stderr 落盘和 exit code 捕获由 Workspace Adapter 完成。

`run_tests` 是 verifier 的中间反馈入口。它不应自己解析测试日志，而应调用 verifier 的 feedback path，并返回结构化 `VerifierResult` 摘要给 agent loop。

如果模型通过 `bash` 请求运行任务测试命令或可识别测试命令，Tool System 应默认把它路由到 `run_tests`，除非配置显式允许“普通 bash observation”。普通 bash observation 可以进入模型上下文，但不能进入 success rate、reward metadata、fail-to-pass 或 pass-to-pass 统计。

## 并发编排

连续的并发安全工具可以并发执行，例如多个 `read_file` 或 `search`。写文件、应用 patch、运行 bash、运行测试必须串行，因为它们会改变 workspace state 或依赖当前文件系统状态。

如果一批工具中存在不确定状态，编排器必须回到串行执行。该策略借鉴 Claude Code 的保守默认值。

## 工具输出规范

ToolResult 应采用“通用字段 + 按工具类型扩展字段”的结构，避免让只读工具伪造命令执行字段。

通用字段至少包含：

- `tool_name`
- `tool_call_id`
- `tool_input`
- `status`：`ok`、`error`、`denied` 或 `timeout`。
- `content_preview`
- `duration_ms`
- `error_type`
- `truncated`
- `artifact_paths`
- `permission_decision`

命令类工具扩展字段：

- `stdout_preview`
- `stderr_preview`
- `exit_code`
- `output_path`

文件读取类工具扩展字段：

- `path`
- `start_line`
- `end_line`
- `content_hash`

搜索类工具扩展字段：

- `query`
- `match_count`
- `result_preview`

diff 类工具扩展字段：

- `diff_preview`
- `patch_stats`

stdout、stderr、文件内容和搜索结果都必须限制长度；完整输出可以在未来实现中保存到 run directory。

`run_tests` 的 tool result 还应包含 `verifier_result_preview` 和 `verifier_result_path`，让模型看到关键失败信息，同时让评测和训练导出能够读取完整结构化结果。

## Claude Code 参考

参考模块：

- `reference/claude-code-docs/claude-doc/04-tool-system.md`
- `reference/claude-code-docs/claude-code-ai-core-codex/03-tools-permissions-and-plan-mode.md`
- `reference/claude-code-typescript-src/Tool.ts`
- `reference/claude-code-typescript-src/services/tools/toolExecution.ts`
- `reference/claude-code-typescript-src/services/tools/toolOrchestration.ts`

RepoHarness 只借鉴接口思想和执行顺序，不照搬产品遥测、UI、MCP、多平台兼容和复杂 hooks。
