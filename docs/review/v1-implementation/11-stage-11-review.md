# Stage 11 Read-Only Review

## Scope

本次审查针对 Stage 11: Eval Runner And CLI End-To-End Flow 的当前实现，重点对照：

- `docs/14-v1-implementation-plan.md`
- `docs/11-object-model-config-and-data-flow.md`
- `docs/07-verifier-reward-and-evaluation.md`

审查方式为 sub agent 只读审查；sub agent 没有直接修改仓库文件。

## Findings

### P1: `test_command_error` 可能绕过 baseline 质量门控

审查指出：baseline verifier 如果产生 `test_command_error`，但 parser confidence 没低于阈值且 fail-to-pass 测试仍未通过，可能被误判为 `valid`，从而生成正式 `ResolvedVerifierPlan` 并进入 Agent Loop。

处理结果：

- 已修复。
- `test_command_error` 现在默认会把 baseline 标记为 `invalid` 并阻断正式 agent run。
- 对第一版已有的 create-file fixture 保留一个受限例外：如果任务显式声明了 `generated_files`，缺失待生成文件导致的 baseline collection/import error 可以继续进入 agent run；这与 Stage 08 的新增文件工具 fixture 保持兼容。
- 新增测试覆盖未声明 `generated_files` 时 `test_command_error` 必须阻断 agent run。

### P2: patch replay 失败不应归类为普通 final failed

审查指出：strict patch replay 失败构造 `error_type="patch_apply_failed"` 后，`derive_final_verifier_status()` 会把它落到 `failed`，从而混淆 patch replay / verification workspace 错误和真实测试失败。

处理结果：

- 已修复。
- `patch_apply_failed` 和 `verification_workspace_error` 现在派生为 `final_verifier_status = "error"`。
- 对应 `run_outcome` 通过 outcome policy 派生为 `inconclusive`。
- 新增单元测试覆盖 patch replay failure 的状态派生。

### P2: `run-batch` 任务级 schema/config 错误不能返回成功

审查指出：`run_batch()` 捕获任务级 `RepoHarnessError` 后只写 `status="error"`，但 CLI 返回码只看 invalid/flaky gate，因此任务加载或 schema 错误可能导致 batch 命令返回 0。

处理结果：

- 已修复。
- `batch_manifest.json` 的 `should_fail_command` 现在在任何任务 `status="error"` 时为 true。
- CLI `run-batch` 根据 `should_fail_command` 返回非零。
- 新增测试覆盖 batch 任务加载错误时 CLI 返回非零。

### P3: `inspect-run` 摘要缺少 task id

审查指出：Stage 11 要求 `inspect-run` 输出 task id，但当前摘要没有显示。

处理结果：

- 已修复。
- `inspect-run` 现在从 events 或 baseline 中提取并输出 `Task id`。
- CLI 集成测试已断言成功 run 的 inspect 输出包含 `Task id: task_001`。

### P3: 未跟踪 `docs/build-your-own/` 超出 Stage 11 范围

审查指出：如果把未跟踪的 `docs/build-your-own/` 纳入 Stage 11 提交，会超出本阶段 Eval Runner/CLI 范围，并可能涉及真实模型调用示例。

处理结果：

- 不提交。
- 当前阶段暂存范围会继续排除 `docs/build-your-own/` 和旧审查材料。

## Residual Risk

- 第一版 flaky fixture 使用 deterministic tag 触发 quality gate，真实多次 rerun 统计留到后续版本。
- `generated_files` 对 baseline `test_command_error` 的受限例外是为了支持缺失文件类 micro-repo fixture；后续版本应通过更精确的 parser / 单测试结果分类替代。
