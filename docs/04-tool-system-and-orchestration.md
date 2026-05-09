# Tool System And Orchestration

## 设计目标

RepoHarness 的工具系统必须像能力契约，而不是普通函数列表。每个工具要清楚描述自己的输入、输出、安全属性、权限逻辑、并发能力和结果格式。

Tool System 的职责是把模型请求转换成受控的工具调用。它不应该直接绕过 workspace boundary 写文件或执行进程。所有文件写入、patch 应用、shell 命令和测试命令最终都必须通过 Workspace / Sandbox Adapter。

## Tool 契约

未来实现中的 `Tool` 至少包含：

- `name`
- `tool_version`
- `model_visible_description`
- `model_visible_prompt`
- `input_schema`
- `output_schema`
- `normalize_input`
- `validate_input`
- `check_permissions`
- `call`
- `map_result_to_model_observation`
- `is_read_only`
- `is_concurrency_safe`
- `is_destructive`
- `max_result_size`

默认策略应保守：没有明确声明并发安全的工具不并发；没有明确声明只读的工具按可能写入处理。

`model_visible_description` 和 `model_visible_prompt` 是会进入模型工具说明的文本，必须稳定版本化。`normalize_input` 负责把模型原始参数转换成规范化参数，例如路径解析、默认 cwd、默认 timeout 和布尔字段补齐；`map_result_to_model_observation` 负责把完整执行结果映射成模型可见 observation preview。完整 stdout、stderr、大文件内容和原始 verifier 输出必须通过 ArtifactRef 保存，不能直接塞进模型上下文。

## ToolExecutionContext

工具执行时不应该拿全局对象，也不应该直接打开 workspace 或 run directory。第一版应定义受限的 `ToolExecutionContext`：

```text
ToolExecutionContext:
  run_id
  task_id
  workspace_facade
  artifact_writer
  permission_context
  verifier_feedback_facade
  abort_signal
  output_limits
  tool_policy
  budget_manager
  file_state_cache
```

普通文件和命令工具只能通过 `workspace_facade` 和 `artifact_writer` 操作工作区与 artifact。只有 `run_tests` 这类验证器入口工具可以使用 `verifier_feedback_facade`。`budget_manager` 负责工具调用次数、测试次数、输出大小和 timeout 等预算扣减；`file_state_cache` 记录最近一次 `read_file` 看到的 `content_hash`、mtime 或等价状态，用于读后再写保护。这样可以防止工具绕过 Workspace Adapter、Verifier 和 Trajectory Store 的边界。

## 第一版工具清单

下面列出第一版需要实现或预留的工具能力。第一版真实暴露给 ReAct 类 scaffold 的模型可见工具集以下方冻结列表为准，内部能力或后续可选工具不能悄悄进入模型工具 schema。

- `list_files`：列出或匹配任务工作区内文件，默认只读、可并发。`glob` 可以作为 `list_files` 的参数模式或内部 helper，不作为第一版单独模型可见工具。
- `read_file`：读取文件片段，默认只读、可并发。
- `grep`：调用 ripgrep 或等价文本搜索，默认只读、可并发。
- `edit_file`：基于 `old_text` / `new_text` 的局部替换，默认不并发、需要权限检查和陈旧读取保护。
- `create_file`：新建文件，若目标已存在默认失败，默认不并发、需要权限检查。
- `write_file`：整文件覆盖写入。覆盖已有文件时必须提供 `expected_content_hash`，默认不并发、需要权限检查。第一版 ReAct 类 scaffold 默认不把它作为模型可见工具；如果实现阶段保留，只应作为内部能力、测试 helper 或后续扩展工具。
- `apply_patch`：应用 unified diff。第一版 ReAct 类 scaffold 默认不把它作为通用 model-facing 工具；它主要作为 Workspace Adapter 内部能力，或用于 single-shot patch scaffold 处理模型一次性输出的 patch。
- `bash`：执行命令，默认不并发、需要权限检查和 timeout。
- `run_tests`：运行任务定义中的测试命令，默认不并发。
- `git_diff`：输出当前 patch，默认只读、可并发。

第一版模型可见工具集应冻结，避免编辑动作过多导致训练协议分散：

- ReAct 类 scaffold：`list_files`、`read_file`、`grep`、`edit_file`、`create_file`、`bash`、`run_tests`、`git_diff`。
- single-shot patch scaffold：模型输出 patch 文本，由 Harness 内部调用 patch apply 能力并把应用结果记录为工具或 verifier 事件。
- 第一版不同时向同一个 ReAct scaffold 暴露 `edit_file` 和通用 `apply_patch`，除非未来版本明确两者优先级、失败反馈、动作类型和训练导出映射。

## 工具执行管线

一次工具调用必须经过：

1. 根据工具名查找 tool definition。
2. 校验输入 schema。
3. 执行工具级 `validate_input`。
4. 调用 Permission System。
5. 如果工具需要读写文件或执行命令，通过 Workspace / Sandbox Adapter 执行。
6. 捕获异常、timeout 和 exit code。exit code 是执行事实，不自动等同于工具错误。
7. 根据 `command_semantics` 或 `exit_code_interpretation` 解释 exit code，例如 `grep` 的 exit code 1 可以表示没有匹配，`run_tests` 的非零退出应进入 `VerifierResult`，普通 `bash` 的非零退出按命令语义转成 observation 或 tool error。
8. 截断模型可见 preview，并把完整 stdout、stderr、验证器原始输出、过大搜索结果和过大文件读取结果写入 run directory artifact。
9. 捕获 workspace diff 或 output `ArtifactRef`。
10. 格式化 tool result。
11. 通过统一 `RunRecorder` 写入 transcript 和 events。

## 工具与 Workspace Adapter 的分工

`list_files`、`read_file` 和 `grep` 仍然需要通过 workspace 路径解析，避免访问任务工作区外的文件。`list_files` 如果支持 glob-style pattern，也必须使用同一套路由和边界检查。

`edit_file`、`create_file`、`write_file` 和内部 patch apply 能力负责校验输入格式和描述写入意图，但实际路径解析、符号链接处理、文件写入、patch 应用和 diff 捕获由 Workspace Adapter 完成。

写工具还应支持陈旧读取保护：

- `expected_content_hash`：模型基于某次 `read_file` 的内容修改文件时，可以声明当时看到的文件 hash。
- `old_text` / `new_text`：`edit_file` 必须声明期望被替换的旧文本和新文本；`old_text` 就是模型认为当前文件中应存在的原始片段。
- `replace_all`：是否替换所有匹配。默认只允许旧文本唯一匹配；多处匹配时必须显式设置并记录。
- patch apply failure 必须返回结构化 `ToolResult(status = "error", error_type = "patch_apply_failed")`，并给出失败 hunk 的简短 preview。
- 新建文件和覆盖文件必须分开记录：`create_file` 在文件已存在时默认失败；`write_file` 覆盖已存在文件时必须检查 `expected_content_hash`。
- 如果未来允许无 hash 强制覆盖，只能来自 `RunConfig` 或人工权限策略，不能作为普通模型参数绕过陈旧读取保护；这类覆盖必须记录 `override_reason`、`permission_decision` 和 `policy_version`。
- 未跟踪文件、二进制文件和符号链接必须有明确处理规则。第一版可以保守拒绝二进制文件写入和跨 workspace 符号链接写入。

`bash` 负责表达命令请求、timeout、环境变量和输出限制，但实际进程启动、工作目录、进程中断、stdout/stderr 落盘和 exit code 捕获由 Workspace Adapter 完成。

`run_tests` 是 verifier 的中间反馈入口。它不应自己解析测试日志，而应调用 verifier 的 feedback path，并返回结构化 `VerifierResult` 摘要给 agent loop。

如果模型通过 `bash` 请求运行任务测试命令或可识别测试命令，Tool System 应默认把它路由到 `run_tests`，除非配置显式允许“普通 bash observation”。普通 bash observation 可以进入模型上下文，但不能进入 success rate、reward metadata、fail-to-pass 或 pass-to-pass 统计。

路由必须记录：

- `requested_tool_name`：模型原始请求的工具名，例如 `bash`。
- `effective_tool_name`：实际执行的工具名，例如 `run_tests`。
- `route_reason`：例如 `recognized_task_test_command`。
- `route_policy_version`：用于说明当前路由规则版本。

这样 transcript 可以保留模型真实动作，events 和 metrics 也能知道实际消耗的是测试次数预算、生成的是结构化 `VerifierResult`。

## 并发编排

连续的并发安全工具可以并发执行，例如多个 `read_file`、`list_files` 或 `grep`。写文件、应用 patch、运行 bash、运行测试必须串行，因为它们会改变 workspace state 或依赖当前文件系统状态。

如果一批工具中存在不确定状态，编排器必须回到串行执行。该策略借鉴 Claude Code 的保守默认值。

并发工具结果必须确定性提交。即使多个只读工具并发执行，ToolResult 回填到 messages、events 写入顺序、artifact_refs 分配、file_state_cache 更新和 transcript 记录都必须按原始 tool_call 顺序提交。并发只优化执行等待时间，不改变轨迹顺序。这样同一个 `RunConfig` 在相同模型输出下可以得到稳定的 transcript、events 和 training export。

工具注册顺序必须稳定。同一份 `RunConfig` 下应记录 `tool_policy_version`、`allowed_tools`、`tool_order` 和 `permission_policy_version`，避免不同运行中工具提示顺序变化影响模型行为和实验复现。

V4 以后，工具面冻结还必须和 tool lifecycle audit 绑定：`ToolContractSnapshot`、`PermissionPolicySnapshot`、`HookPolicySnapshot` 或 hook disabled facts、`MCPPolicySnapshot` 或 MCP disabled / frozen facts、稳定工具顺序、permission decision trace 和 tool lifecycle trace 都应能被 inspect 命令复核。最新机器证据位于 `docs/v4/evidence/tool-lifecycle/`，实施要求见 `docs/v4/implementation-plan.md`。

## 工具输出规范

ToolResult 应采用“通用字段 + 按工具类型扩展字段”的结构，避免让只读工具伪造命令执行字段。

通用字段至少包含：

- `tool_name`
- `tool_call_id`
- `status`：`ok`、`error`、`denied`、`timeout` 或 `interrupted`。
- `content_preview`
- `duration_ms`
- `error_type`
- `truncated`
- `artifact_refs`
- `permission_decision`
- `requested_tool_name`
- `effective_tool_name`
- `requested_arguments`
- `normalized_arguments`
- `effective_arguments`
- `normalization_policy_version`
- `normalized_input_hash`
- `route_reason`
- `route_policy_version`

`requested_arguments` 是模型原始请求；`normalized_arguments` 是 Tool System 规范化后的参数，例如路径、cwd、默认 timeout 或布尔字段；`effective_arguments` 是实际执行参数，例如 `bash` 被路由到 `run_tests` 后使用的测试命令配置。训练导出默认保留模型原始动作，同时用 normalized / effective 字段解释系统如何规范化和执行该动作。

命令类工具扩展字段：

- `stdout_preview`
- `stderr_preview`
- `exit_code`
- `command_semantics`
- `exit_code_interpretation`
- `output_artifact_ref`

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

stdout、stderr、文件内容、验证器原始输出和搜索结果都必须限制模型可见长度；完整输出第一版就应保存到 run directory，并通过 `ArtifactRef` 引用。`ArtifactRef` 至少应提供 `artifact_id`、`relative_path`、`kind`、`sha256`、`size_bytes`、`created_by_event_id`、`redaction_status` 和 `retention_policy`。ToolResult 只回填 preview 给模型，并记录 `artifact_refs`、`truncated`、hash、大小和脱敏状态，方便 secret scan、失败复盘、奖励审计和训练导出。

`run_tests` 的 tool result 还应包含 `verifier_result_preview` 和 `verifier_result_ref`，让模型看到关键失败信息，同时让评测和训练导出能够通过 artifact manifest 读取完整结构化结果。

## Claude Code 参考

参考模块：

- `reference/claude-code-docs/claude-doc/04-tool-system.md`
- `reference/claude-code-docs/claude-code-ai-core-codex/03-tools-permissions-and-plan-mode.md`
- `reference/claude-code-typescript-src/Tool.ts`
- `reference/claude-code-typescript-src/services/tools/toolExecution.ts`
- `reference/claude-code-typescript-src/services/tools/toolOrchestration.ts`

RepoHarness 只借鉴接口思想和执行顺序，不照搬产品遥测、UI、MCP、多平台兼容和复杂 hooks。
