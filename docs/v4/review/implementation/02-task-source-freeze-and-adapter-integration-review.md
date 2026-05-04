# V4 Stage 2 Review: Task Source Freeze And Adapter Integration

## 审查方式

本阶段优先使用只读 subagent 审查。由于审查过程中发现 P1/P2 问题，阶段 2 共进行了三轮只读审查与修复。

## 第一轮审查结论

结论：不允许进入阶段 3。

发现：

- P1：accepted 计数缺少硬门槛。绑定报告中 baseline、post-patch、environment stability、dependency cache、license / use-boundary 等报告只做浅层 schema 检查。
- P1：final acceptance inputs 递归复核 task freeze / task validity 时仍走 Stage 1 skeleton，绕过阶段 2 专用 inspect。
- P2：evaluator-only manifest 未检查 provider raw response、raw patch、raw test patch 等原始内容不复制门槛。
- P2：accepted task row 缺少 baseline evidence ref。

修复：

- 增加绑定报告的通过状态和 raw output 禁止复制检查。
- `inspect_v4_inputs(..., assert_complete=True)` 对 task freeze 和 task validity 调用阶段 2 专用 inspect。
- evaluator-only manifest 检查 `provider_raw_response_copied=false`、`raw_patch_copied=false`、`raw_test_patch_copied=false`、`raw_verifier_output_copied=false`。
- accepted task row 增加 `baseline_verifier_evidence_ref`。

## 第二轮审查结论

结论：不允许进入阶段 3。

发现：

- P1：accepted rows 没有和绑定报告逐 task 强绑定。
- P2：`inspect-v4-task-freeze` 未递归复核 `task_validity_report.json`。
- P2：accepted count 只检查下限，没有校验顶层计数等于实际 accepted 行数和 PR / issue accepted 行数。
- P3：负例没有覆盖全部 evaluator-only 不复制门槛和 evidence 绑定门槛。

修复：

- `inspect_v4_task_validity` 建立 accepted row 与 source materialization、baseline verifier、post-patch verifier、flaky detection、environment stability、dependency cache、license / provenance review 和 use-boundary review 报告的逐 task 强绑定。
- `inspect_v4_task_freeze` 递归调用 `inspect_v4_task_validity(..., assert_complete=True)`。
- 校验 accepted count 等于实际 accepted 行数，PR / issue accepted count 等于实际 PR / issue 行数。
- 补充 evaluator-only raw test patch / raw verifier output 泄漏、task validity 递归失败、count 膨胀、evidence ref 不一致、绑定报告缺少 accepted task identity 等负例。

## 最终复审结论

最终复审结论：允许进入阶段 3。

确认事项：

- 8 个 accepted rows 与 baseline、post-patch、flaky、source materialization、environment、dependency、license 和 use-boundary 报告均通过同一组 `task_id + candidate_id` 强绑定。
- `inspect-v4-task-freeze` 会递归复核 `task_validity_report.json`。
- 顶层 accepted count 等于实际 accepted 行数。
- evaluator-only 泄漏门槛覆盖 `model_visible=false`、`trainable=false`、`raw_content_copied=false`、`raw_verifier_output_copied=false`、`raw_patch_copied=false`、`raw_test_patch_copied=false`、`provider_raw_response_copied=false`。
- 当前没有 P1、P2 或 P3 阻塞项。

## 允许进入下一阶段

允许进入阶段 3。
