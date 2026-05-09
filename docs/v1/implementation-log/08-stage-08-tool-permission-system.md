# Stage 08: Tool And Permission System

## Scope

本阶段实现了：

- 第一版模型可见工具顺序：
  - `list_files`
  - `read_file`
  - `grep`
  - `edit_file`
  - `create_file`
  - `bash`
  - `run_tests`
  - `git_diff`
- `ToolDefinition`、`ToolRegistry`、`ToolExecutionContext`、`ToolOutputLimits` 和 `ToolPolicy`。
- `PermissionContext` 和 `PermissionSystem`：
  - schema / normalization 之后才进入权限判断。
  - workspace boundary 和敏感路径拒绝优先于权限模式 fallback。
  - `plan`、`ask`、`deny` 对非只读工具保守拒绝。
  - `ask` 在当前非交互 run-task 中降级为 deny，并记录 `requires_user_input` 和 `non_interactive_resolution`。
  - `bash` 命令解析拒绝 `curl`、`git fetch`、管道、重定向、环境变量前缀、后台任务等风险入口。
- 工具执行管线：
  - 未知工具写 `invalid_tool` event，并生成配对 `ToolResult`，不进入 Permission System。
  - schema 校验失败写 `tool_validation_failed` event 和模型可见 `ToolResult(error_type=schema_validation_failed)`，不进入 Permission System。
  - 已知且校验通过的工具写 `permission_decision` event 后再执行。
  - permission deny 写 `tool_denied` event 和配对 `ToolResult(status=denied)`。
  - 普通成功写 `tool_completed` event；错误、timeout、interrupted 使用独立 event type。
- `bash` 请求 `pytest -q` 或任务测试命令时路由到 `run_tests`，并在 `ToolResult` 中记录 `requested_tool_name`、`effective_tool_name` 和 `route_reason`。
- 新增 replay fixture：
  - create file 成功 replay。
  - bash pytest 路由 replay。
  - schema error replay。
  - unknown tool replay。
- 单元测试和集成测试覆盖工具注册、schema 错误、权限模式、bash 安全拒绝、grep 无匹配、create_file、bash 路由、权限拒绝和 tool call / tool result 配对。

本阶段明确不实现：

- 不开启工具并发执行；第一版仍串行提交 tool result。
- 不把 `write_file` 或 `apply_patch` 暴露给 ReAct 类模型。
- 不实现生产级操作系统隔离或真实网络断开，只实现命令层保守拒绝。
- 不实现完整交互式 ask；当前 run-task 是非交互执行，ask 对风险操作降级为 deny。

## Design References

- `docs/v1/implementation-plan.md`
- `docs/04-tool-system-and-orchestration.md`
- `docs/05-workspace-sandbox-and-permissions.md`
- `docs/11-object-model-config-and-data-flow.md`
- `docs/03-agent-loop-and-message-protocol.md`

## Files Changed

- `src/repo_harness/agent_loop/loop.py`
- `src/repo_harness/evaluation/__init__.py`
- `src/repo_harness/evaluation/runner.py`
- `src/repo_harness/model_client/replay.py`
- `src/repo_harness/permissions/__init__.py`
- `src/repo_harness/permissions/system.py`
- `src/repo_harness/tools/__init__.py`
- `src/repo_harness/tools/minimal.py`
- `tests/fixtures/replays/task_001_bash_pytest.yaml`
- `tests/fixtures/replays/task_001_schema_error.yaml`
- `tests/fixtures/replays/task_001_unknown_tool.yaml`
- `tests/fixtures/replays/task_003_create_file_success.yaml`
- `tests/fixtures/run_configs/replay_bash_pytest.yaml`
- `tests/fixtures/run_configs/replay_create_file.yaml`
- `tests/fixtures/run_configs/replay_schema_error.yaml`
- `tests/fixtures/run_configs/replay_unknown_tool.yaml`
- `tests/integration/test_minimal_vertical_slice.py`
- `tests/integration/test_tool_execution.py`
- `tests/unit/test_permissions.py`
- `tests/unit/test_task_adapter.py`
- `tests/unit/test_tools.py`

## Verification

运行的命令：

```bash
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_permissions.py tests/unit/test_tools.py tests/integration/test_tool_execution.py
PATH=.venv/bin:$PATH python -m pytest
```

结果：

- 通过。
- 阶段八指定测试收集并通过 28 个测试。
- 全量测试收集并通过 111 个测试。

调试记录：

- 初次运行阶段八测试时发现 `evaluation.__init__` 重新导出 `run_task`，导致工具模块导入 evaluation schema 时拉入 runner、agent loop、model client 和 tools，形成循环导入。
- 处理方式：`evaluation.__init__` 不再重新导出 runner；调用方直接从 `repo_harness.evaluation.runner` 导入 `run_task`。

## Review

审查方式：

- 主实现 agent 自查。
- sub agent 只读审查。

关键审查意见：

- `bash` allowlist 按命令名允许 `ls` 和 `find`，但没有解析路径参数，可能通过 `ls /`、`ls $HOME`、`find /` 读取 workspace 外信息。
- pytest 路由先于 shell 安全拒绝，`pytest -q | tee out.txt`、重定向和后台任务可能被误路由为 `run_tests`。
- `bash.cwd` 在 normalize 阶段解析，越界异常会绕过 Permission System，导致缺少配对 ToolResult。
- `grep` Python fallback 直接读取文件，可能绕过 Workspace Adapter 的敏感路径和符号链接检查。
- Workspace Adapter 子进程环境继承完整宿主环境变量。
- summary 缺少权限拒绝原因，测试覆盖不完整。

处理结果：

- 采纳：`bash` 安全检查拒绝 `$`、`~` 和后台任务等 shell 语法，并对 `ls`、`find` 路径参数调用 Workspace Adapter 解析；新增 `ls /`、`ls $HOME`、`find /` 测试。
- 采纳：pytest 路由先检查危险 shell 语法，再用 `shlex.split` 判断测试命令；新增真实 Agent Loop 的危险 pytest shell 语法拒绝测试。
- 采纳：normalize 不再解析 `bash.cwd`；cwd 解析交给 Permission System；新增 cwd 越界仍生成 deny decision 和配对 ToolResult 的端到端测试。
- 采纳：`grep` Python fallback 对每个候选文件调用 Workspace Adapter `read_text()`；新增 `.env` 内容不进入 grep 结果测试。
- 采纳：命令环境改为最小 allowlist，只保留 PATH、临时目录和 locale 等必要字段，并设置 Python 编码变量。
- 采纳：AgentLoopState 记录权限拒绝原因，summary 写出 `permission_denial_count` 和去重原因；安全负例测试覆盖 summary。
- 采纳：审查报告保存到 `docs/v1/review/implementation/08-stage-08-review.md`。

## Known Limitations

- `bash` allowlist 只覆盖第一版需要的诊断命令和只读 Git 子命令；复杂 shell 语法默认拒绝。
- `grep` 优先使用 `rg`，不可用时使用 Python fallback；当前 parser 不尝试解释正则错误之外的复杂搜索语义。
- 文件陈旧读取保护支持 `expected_content_hash`，但第一版不强制所有 `edit_file` 都提供该字段。
- `PermissionSystem` 是命令层和路径层策略，不声称提供操作系统级沙箱或网络隔离。

## Commit

- Commit: `stage 08: implement tools and permissions`
- Commit message: `stage 08: implement tools and permissions`
