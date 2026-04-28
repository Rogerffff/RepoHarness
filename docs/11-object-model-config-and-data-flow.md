# Object Model, Config, And Data Flow

## 设计目标

这篇文档把 RepoHarness 的核心对象、配置字段、后续源代码目录和端到端数据流集中定义。它不包含具体实现代码，而是给下一阶段工程实现提供统一命名和边界，避免每个模块重复定义相似的数据结构。

## 后续源代码目录规划

第一阶段只保留 Python 骨架，不创建完整运行时实现。未来实现可以按以下目录演进：

```text
src/repo_harness/
  agent_loop/        # agent loop state, turn execution, termination handling
  cli/               # command line entrypoints and config loading
  evaluation/        # batch evaluation runner and aggregate metrics
  export/            # SFT, reinforcement learning rollout, preference pair export
  permissions/       # permission modes, rules, decisions
  scaffolds/         # single-shot, simple ReAct, planner-coder-verifier
  tasks/             # task adapters and task validation
  tools/             # tool definitions and tool orchestration
  trajectory/        # transcript, events, artifacts index
  verifier/          # baseline, feedback, final verifier paths
  workspace/         # local process and Docker-based executable repository environment
```

这些目录是实现计划，不表示当前仓库已经具备对应功能。

## RunConfig

`RunConfig` 是一次单任务运行或批量评测的配置对象。推荐 YAML 形态：

```yaml
run_id_prefix: local_eval
tasks:
  - tasks/repo_task_001.yaml
model:
  provider: openai
  model_id: example-model
  temperature: 0.2
  max_output_tokens: 4096
runtime:
  scaffold_id: simple_react
  execution_mode: local_process
  permission_mode: auto
  max_turns: 20
  max_tool_calls: 80
  timeout_sec: 900
  seed: 42
workspace:
  output_dir: runs
  keep_workspace: true
  default_command_timeout_sec: 120
  max_tool_output_chars: 12000
evaluation:
  concurrency: 1
  rerun_final_verifier: true
  fail_on_invalid_task: false
logging:
  level: info
  write_transcript: true
  write_events: true
```

批量评测默认应使用 `auto` 或 `deny` 模式，不应默认使用需要人工确认的 `ask` 模式。

## 核心对象清单

| 对象 | 主要字段 | 来源模块 | 消费模块 |
| --- | --- | --- | --- |
| `TaskDefinition` | `id`、`repo`、`issue`、`test_command`、`timeout_sec`、`tags` | Task Adapter | Task Adapter、Trajectory Store |
| `RunnableTask` | `task_id`、`issue_statement`、`repo_source`、`setup_command`、`verifier_config`、`metadata` | Task Adapter | Agent Loop、Workspace Adapter、Verifier |
| `BaselineResult` | `status`、`initial_fail_to_pass_tests`、`initial_pass_to_pass_tests`、`flaky_tests`、`dependency_state`、`agent_start_snapshot`、`agent_diff_base` | Workspace Adapter、Verifier | Eval Runner、Verifier、Trajectory Store |
| `RunWorkspace` | `run_id`、`workspace_path`、`repo_base_commit`、`execution_mode`、`artifact_dir` | Workspace Adapter | Tool System、Verifier、Trajectory Store |
| `AgentLoopState` | `messages`、`turn_count`、`tool_call_count`、`last_verifier_result`、`agent_stop_reason`、`final_verifier_status`、`run_outcome` | Agent Loop | Agent Loop、Trajectory Store |
| `ModelMessage` | `role`、`content`、`tool_calls`、`metadata` | Agent Loop、Model Client | Agent Loop、Transcript Export |
| `ToolCall` | `tool_call_id`、`tool_name`、`arguments`、`turn` | Model Client、Agent Loop | Tool System、Permission System |
| `PermissionDecision` | `decision`、`mode`、`matched_rule`、`reason`、`requires_user_input` | Permission System | Tool System、Trajectory Store |
| `ExecutionResult` | `exit_code`、`stdout_preview`、`stderr_preview`、`output_path`、`duration_ms`、`timeout` | Workspace Adapter | Tool System、Verifier |
| `ToolResult` | `tool_call_id`、`tool_name`、`status`、`content_preview`、`error_type`、`truncated`、`artifact_paths`、typed extension fields | Tool System | Agent Loop、Trajectory Store |
| `VerifierConfig` | `test_command`、`timeout_sec`、`fail_to_pass_tests`、`pass_to_pass_tests`、`parser` | Task Adapter | Verifier |
| `VerifierResult` | `accepted`、`pass_ratio`、`fail_to_pass`、`pass_to_pass`、`exit_code`、`timeout`、`error_type` | Verifier | Eval Runner、Reward、Trajectory Store |
| `RewardMetadata` | `reward_version`、`final_reward`、`components`、`sources`、`invalid_for_training` | Reward module | Training Exporter、Metrics |
| `TrajectoryEvent` | `timestamp`、`run_id`、`task_id`、`event_type`、typed extension fields | All runtime modules | Metrics、Diagnostics、Exporter |
| `ExportRecord` | `sample_id`、`task_id`、`source_run_id`、`payload`、`metadata`、`filter_status` | Training Exporter | Training pipelines |

## 端到端数据流

1. Eval Runner 读取 `RunConfig` 和任务路径列表。
2. Task Adapter 读取 `TaskDefinition`，校验字段，并生成 `RunnableTask`。
3. Workspace Adapter 创建 setup workspace，执行 dependency setup 和 baseline verifier。
4. Baseline verifier 生成 `BaselineResult`，包括 `dependency_state` 和 `agent_start_snapshot` 计划。如果任务是 `invalid` 或 `flaky`，默认不进入正式 agent run。
5. Eval Runner 为有效任务从 source checkout 创建正式 `RunWorkspace`，恢复 `dependency_state`，并以 `agent_start_snapshot` 作为 agent diff 基线。
6. Agent Loop 根据 scaffold、`RunnableTask` 和 `RunConfig` 构造 system message 与 user task message。
7. 模型输出 `ToolCall`，Tool System 进行工具查找、schema 校验和工具级输入校验。
8. Permission System 返回 `PermissionDecision`。
9. Tool System 把允许执行的文件或命令操作交给 Workspace Adapter。
10. Workspace Adapter 返回 `ExecutionResult`，Tool System 转换为 `ToolResult`。
11. Agent Loop 把 `ToolResult` 写回 messages，Trajectory Store 写入 transcript 和 events。
12. `run_tests` 调用 verifier feedback path，并把结构化结果作为中间反馈回流模型上下文。
13. Agent Loop 因 final answer、feedback tests passed、预算耗尽、timeout 或错误停止，并记录 `agent_stop_reason`。
14. Final verifier 基于最终工作区重新运行，生成最终 `VerifierResult`。
15. Eval Runner 根据 final verifier 生成 `final_verifier_status` 和 `run_outcome`。
16. Reward module 根据 final verifier、events 和 diff 生成 `RewardMetadata`。
17. Trajectory Store 写出 `final.patch`、`final.diff`、`verifier.json`、`metrics.json` 和 `summary.md`。
18. Training Exporter 从完整 run artifacts 生成 SFT、reinforcement learning rollout 或 preference pair `ExportRecord`。

## 统一错误与终止口径

错误类型、终止原因和失败诊断之间应保持映射关系：

- `invalid_tool_call` 属于模型或协议错误，预算内可以重试。
- `permission_denied` 属于权限决策结果，是否终止取决于权限模式和工具类型。
- `tool_error` 属于工具执行失败，通常可以把 observation 返回给模型继续修复。
- `test_timeout` 和 `assertion_failure` 属于 verifier feedback，通常不是 runtime crash。
- `dependency_install_failed` 属于 baseline invalid task，默认不产生训练轨迹。
- `context_limit` 属于上下文管理失败，压缩失败后才终止。
- `regression_detected` 属于 final verifier 或 pass-to-pass 检查结果，应进入 reward penalty 和 failure diagnostics。

## 设计边界

这篇文档只定义未来实现接口和对象流。它不要求第一阶段创建这些 Python 类，也不声称当前仓库已经能够运行评测、执行工具或导出训练数据。
