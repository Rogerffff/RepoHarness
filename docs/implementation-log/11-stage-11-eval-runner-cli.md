# Stage 11: Eval Runner And CLI End-To-End Flow

## Scope

本阶段实现了：

- `validate-task` 命令继续只执行任务 schema、可见性和静态配置校验，不创建 workspace，不运行测试。
- `run-task` 端到端编排：
  - 加载任务和 RunConfig。
  - 创建 source checkout 和 setup workspace。
  - 执行 setup command，并把 setup 失败作为 baseline quality gate 失败。
  - 运行 baseline verifier。
  - 生成并写出 `baseline.json` 和 baseline verifier artifact。
  - baseline 为 `invalid` 或 `flaky` 时阻断正式 agent run，不创建 agent workspace，不生成正式 `ResolvedVerifierPlan`，不进入 Agent Loop。
  - baseline 通过后才生成 `resolved_verifier_plan.json`。
  - Agent Loop 停止后冻结 `final.patch` 和 `final.diff`。
  - 在独立 verification workspace 中执行 strict patch replay final verifier。
  - 由 Eval Runner 派生 `final_verifier_status`、`run_outcome`、reward、metrics 和 summary。
- 新增 `evaluation/outcome_policy.py`，把 `derive_run_outcome()` 放在 evaluation 边界内，而不是 Agent Loop 内。
- `run-batch` 命令：
  - 顺序读取 `RunConfig.tasks`。
  - 第一版固定按配置中的 `concurrency=1` 语义运行。
  - 为每个任务写出 run directory。
  - 写出 `batch_manifest.json`，包含 task id、run id、run directory、状态、失败原因和关键 artifact 路径。
- `inspect-run` 增强：
  - 输出 task id、run outcome、agent stop reason、final verifier status、baseline status、reward 和关键 artifact。
- `fail_on_invalid_task` 返回码策略：
  - `run-task` 遇到 invalid 或 flaky quality gate 且配置为 true 时返回非零。
  - `run-batch` 在 manifest 中记录 `should_fail_command`，CLI 根据该字段返回非零。
- 阶段十一 fixture：
  - `tests/fixtures/run_configs/replay_success.yaml`
  - `tests/fixtures/run_configs/batch_replay.yaml`
  - `tests/fixtures/tasks/task_invalid.yaml`

本阶段明确不实现：

- 不实现并发 batch runner；第一版 batch 仍然顺序运行。
- 不实现真实模型供应商。
- 不实现 Training Exporter；导出命令仍留到 Stage 12。

## Design References

- `docs/14-v1-implementation-plan.md`
- `docs/11-object-model-config-and-data-flow.md`
- `docs/07-verifier-reward-and-evaluation.md`

## Files Changed

- `src/repo_harness/cli/main.py`
- `src/repo_harness/evaluation/__init__.py`
- `src/repo_harness/evaluation/metrics.py`
- `src/repo_harness/evaluation/outcome_policy.py`
- `src/repo_harness/evaluation/runner.py`
- `src/repo_harness/schema_versions.py`
- `src/repo_harness/trajectory/inspect.py`
- `src/repo_harness/verifier/acceptance.py`
- `tests/fixtures/run_configs/batch_replay.yaml`
- `tests/fixtures/run_configs/replay_success.yaml`
- `tests/fixtures/tasks/task_invalid.yaml`
- `tests/integration/test_eval_runner_quality_gate.py`
- `tests/unit/test_outcome_policy.py`
- `docs/review/v1-implementation/11-stage-11-review.md`

## Verification

运行的命令：

```bash
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_outcome_policy.py tests/integration/test_eval_runner_quality_gate.py tests/integration/test_tool_execution.py::test_create_file_replay_succeeds -q
PATH=.venv/bin:$PATH repo-harness validate-task tests/fixtures/tasks/task_001.yaml
PATH=.venv/bin:$PATH repo-harness run-task tests/fixtures/tasks/task_001.yaml --config tests/fixtures/run_configs/replay_success.yaml --output-dir runs/test-stage-11 --run-id stage11-success
PATH=.venv/bin:$PATH repo-harness inspect-run runs/test-stage-11/stage11-success
PATH=.venv/bin:$PATH repo-harness run-task tests/fixtures/tasks/task_invalid.yaml --config tests/fixtures/run_configs/replay_success.yaml --output-dir runs/test-stage-11 --run-id stage11-invalid
PATH=.venv/bin:$PATH repo-harness run-task tests/fixtures/tasks/task_flaky.yaml --config tests/fixtures/run_configs/replay_success.yaml --output-dir runs/test-stage-11 --run-id stage11-flaky
PATH=.venv/bin:$PATH repo-harness run-batch --config tests/fixtures/run_configs/batch_replay.yaml --output-dir runs/test-stage-11-batch
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_reward.py tests/unit/test_outcome_policy.py tests/integration/test_eval_runner_quality_gate.py -q
PATH=.venv/bin:$PATH python -m pytest
git diff --check
```

结果：

- 通过。
- Stage 11 目标测试通过 13 个测试。
- 审查修复相关测试通过 17 个测试。
- 全量测试收集并通过 150 个测试。
- CLI 验证命令完成，`inspect-run` 能读取成功 run，invalid 和 flaky fixture 都被 quality gate 阻断。
- `git diff --check` 未发现空白错误。

## Review

审查方式：

- 主实现 agent 自查。
- sub agent 只读审查，审查记录保存到 `docs/review/v1-implementation/11-stage-11-review.md`。

关键审查意见：

- `test_command_error` 不能绕过 baseline quality gate。
- strict patch replay 失败不能归类为普通 final failed。
- `run-batch` 任务级 schema/config 错误不能导致 CLI 返回 0。
- `inspect-run` 必须输出 task id。
- 未跟踪的 `docs/build-your-own/` 不属于 Stage 11 提交范围。

处理结果：

- `test_command_error` 默认标记 baseline invalid；仅对显式声明 `generated_files` 的缺失文件类 fixture 保留受限例外，并新增负例测试。
- `patch_apply_failed` 和 `verification_workspace_error` 现在派生为 `final_verifier_status = "error"`，最终 outcome 为 `inconclusive`。
- `batch_manifest.json` 在任一任务 `status = "error"` 时设置 `should_fail_command = true`，CLI 返回非零。
- `inspect-run` 现在输出 `Task id`，测试已覆盖。
- `docs/build-your-own/` 和旧审查材料继续保持未暂存。

## Known Limitations

- Batch runner 第一版是顺序执行；不会并发运行任务。
- `flaky` fixture 通过显式 fixture tag 触发 deterministic flaky quality gate，用于第一版验收；真实 flaky 统计和多次 rerun 策略留到后续版本。
- `generated_files` 对 baseline `test_command_error` 的受限例外用于支持缺失文件类 micro-repo fixture；后续版本应由更精确的 parser 或单测试分类替代。
- `run-task` 默认在任务失败时仍返回 0，除非配置 `fail_on_invalid_task=true` 且任务被 invalid 或 flaky quality gate 阻断。
- Training export 尚未实现，保留到 Stage 12。

## Commit

- Commit: `stage 11: wire eval runner cli`
- Commit message: `stage 11: wire eval runner cli`
