# Stage 07: Minimal Vertical Slice

## Scope

本阶段实现了：

- 最小 `ContextBuilder`，注入系统规则、任务可见投影、工作区根目录、测试命令、允许工具和运行预算。
- 最小 `ContextManager`，每轮生成 `PreparedMessages`、`context_revision`、`model_input_hash`、`prepared_messages_ref` 和 `context_prepared` event。
- 最小 `ReplayModelClient`，从 replay script 产生 `read_file`、`edit_file`、`run_tests`、`git_diff` 和 final answer，并写入 model call event。
- Stage 07 最小工具接口和 `build_tool()` 工厂，四个工具的只读、并发和破坏性默认值保持保守。
- Stage 07 最小 Permission System shim：
  - 已知工具先做输入校验，再做权限决策。
  - `read_file` 和 `edit_file` 复用 Workspace Adapter 的路径解析、workspace boundary 和敏感路径拒绝。
  - 允许或拒绝都会写 `permission_decision` event。
  - 未知工具不进入权限系统，会写 `invalid_tool` event，并生成配对 `ToolResult`。
- 最小 `AgentLoop`：
  - 维护 message state。
  - 每轮调用 Context Manager 和 ReplayModelClient。
  - 写 `model_call_started`、`model_call_completed`、`tool_requested`、`permission_decision`、`tool_completed` 或 `tool_failed` event。
  - 为每个 tool call 回填一个 tool result transcript record。
- 只支持 replay 的最小 `run-task` 编排器：
  - 调用 Task Adapter、Workspace Adapter、baseline verifier、ResolvedVerifierPlan、Agent Loop、final patch capture、strict patch replay final verifier、reward、metrics 和 summary。
  - baseline 未通过质量门控时不生成 `ResolvedVerifierPlan`，并以 `invalid_task` 结束。
  - `final_verifier_status` 和 `run_outcome` 只在 Eval Runner 内派生，不进入 Agent Loop。
- Stage 07 成功 replay、失败 replay 和安全负例 replay 的 RunConfig fixture。
- 集成测试覆盖成功闭环、失败 artifact、权限拒绝、未知工具、tool call / tool result 配对、prepared messages artifact 和工具工厂默认值。

本阶段明确不实现：

- 不接真实模型供应商。
- 不实现完整第一版 ReAct 工具集；阶段七只暴露 `read_file`、`edit_file`、`run_tests` 和 `git_diff`。
- 不实现完整 Permission System 策略矩阵；这里只保留后续阶段可扩展的最小 shim。
- 不实现复杂 context replacement、token budget 压缩或 fake model client。
- 不实现 batch Eval Runner 或 Training Exporter。

## Design References

- `docs/14-v1-implementation-plan.md`
- `docs/11-object-model-config-and-data-flow.md`
- `docs/03-agent-loop-and-message-protocol.md`
- `docs/04-tool-system-and-orchestration.md`
- `docs/05-workspace-sandbox-and-permissions.md`
- `docs/07-verifier-reward-and-evaluation.md`
- `docs/08-trajectory-store-and-training-export.md`

## Files Changed

- `src/repo_harness/agent_loop/loop.py`
- `src/repo_harness/agent_loop/schemas.py`
- `src/repo_harness/agent_loop/__init__.py`
- `src/repo_harness/cli/main.py`
- `src/repo_harness/config/schemas.py`
- `src/repo_harness/context/builder.py`
- `src/repo_harness/context/manager.py`
- `src/repo_harness/context/__init__.py`
- `src/repo_harness/evaluation/metrics.py`
- `src/repo_harness/evaluation/runner.py`
- `src/repo_harness/evaluation/__init__.py`
- `src/repo_harness/model_client/replay.py`
- `src/repo_harness/model_client/schemas.py`
- `src/repo_harness/model_client/__init__.py`
- `src/repo_harness/tools/minimal.py`
- `src/repo_harness/tools/__init__.py`
- `tests/fixtures/run_configs/replay_success_minimal.yaml`
- `tests/fixtures/run_configs/replay_failure_minimal.yaml`
- `tests/fixtures/run_configs/replay_security_negative_minimal.yaml`
- `tests/integration/test_minimal_vertical_slice.py`

## Verification

运行的命令：

```bash
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest tests/integration/test_minimal_vertical_slice.py
PATH=.venv/bin:$PATH repo-harness run-task tests/fixtures/tasks/task_001.yaml --config tests/fixtures/run_configs/replay_success_minimal.yaml --output-dir runs/test-stage-07 --run-id stage07-success
PATH=.venv/bin:$PATH repo-harness inspect-run runs/test-stage-07/stage07-success
test -f runs/test-stage-07/stage07-success/dependency_state.json
test -f runs/test-stage-07/stage07-success/final.diff
test -f runs/test-stage-07/stage07-success/verifier.json
PATH=.venv/bin:$PATH python -m pytest tests/integration/test_minimal_vertical_slice.py
PATH=.venv/bin:$PATH python -m pytest
```

结果：

- 通过。
- `repo-harness inspect-run runs/test-stage-07/stage07-success` 显示 `Status: FINALIZED`、artifact manifest 正常、`Run outcome: success`、最后事件为 `run_finished`。
- 集成测试收集并通过 5 个测试。
- 全量测试收集并通过 79 个测试。

调试记录：

- 初次运行集成测试时发现 `ContextBuilder` 通过包级 `repo_harness.evaluation` 导入 `ResolvedVerifierPlan`，与 `evaluation.runner` 形成循环导入。
- 处理方式：改为从 `repo_harness.evaluation.schemas` 直接导入 schema，保持运行时依赖方向清楚。

## Review

审查方式：

- 主实现 agent 自查。
- sub agent 只读审查。

关键审查意见：

- `patch_apply_failed` 不应派生为 `final_verifier_status = "error"` 和 `run_outcome = "inconclusive"`；strict patch replay 失败应计为 formal final verifier failed。
- `run_task` 不应在打开 `RunRecorder` 前删除已有 run directory，否则会绕过 finalized-run 和 lock 保护。
- Stage 07 permission shim 不应让 `plan` 和 `ask` 模式继续执行非只读工具。
- `agent_visible_view()` 不应把原始 `repo_source` 路径放进模型可见 prepared messages。

处理结果：

- 采纳：`patch_apply_failed` 现在派生为 `final_verifier_status = "failed"`；对应 `run_outcome = "failed"`，并新增测试。
- 采纳：已有 run directory 现在会让 `run_task` 抛出配置错误，要求使用新的 run id 或手动归档，不再自动删除。
- 采纳：`plan`、`ask`、`deny` 模式只允许只读工具；`ask` 对非只读工具记录 `requires_user_input = true` 和 `non_interactive_resolution = "deny"`。
- 采纳：模型可见任务投影移除 `repo_source`，ContextBuilder 只单独提供 agent workspace 根目录。
- 采纳：审查报告保存到 `docs/review/v1-implementation/07-stage-07-review.md`。

## Known Limitations

- Stage 07 的 Permission System 是 shim，只覆盖四个最小工具和 workspace 路径边界；完整命令策略、网络策略、敏感命令策略留到阶段八。
- Stage 07 的 Context Manager 不做复杂 replacement，只保证每轮模型可见输入都有 artifact、hash 和 revision 可追踪。
- Stage 07 的 Agent Loop 只处理 replay model 已解析出的结构化 tool call，不实现真实模型输出解析恢复。
- 失败 replay 会生成完整 run artifact、metrics 和 summary，但 batch invalid/flaky 策略和更完整 outcome policy 留到阶段十一扩展。

## Commit

- Commit: `stage 07: complete replay vertical slice`
- Commit message: `stage 07: complete replay vertical slice`
