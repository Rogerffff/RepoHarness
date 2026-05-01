# Stage 15 只读审查记录

## 审查方式

本阶段安排了只读 sub agent 审查。审查 agent 没有修改文件。主流程根据审查结论修复了 P1 和 P2 问题，并重新运行相关验证。

## 审查重点

- 全局 `v2_acceptance_report.json` 是否与 Stage 13 task-set 阈值检查分离。
- `build-v2-acceptance-report` 是否只汇总既有机器产物，不重新运行 verifier，不改写 run facts。
- `inspect-v2-acceptance --assert-complete` 是否拒绝关键伪装路径。
- 是否引用 task set manifest、mock provider report、real provider report、Docker status、三种导出格式 audit 和 feedback policy report。
- feedback policy coverage 是否覆盖四种 `test_feedback_policy` 和三种 `feedback_tests_passed_policy`。
- 文档是否避免声称生产级安全沙箱、完整 SWE-Bench 或已经训练出 coding agent。

## 审查发现

### P1

1. `inspect-v2-acceptance --assert-complete` 没有强制必需 evidence refs 存在。
   - 风险：删除 `task_set_manifest` 等关键引用后，初始检查器仍可能通过。
   - 处理：已修复。检查器现在要求 `v1_batch_manifest`、`task_set_manifest`、`task_set_aggregate_metrics`、`mock_provider_report`、`real_provider_report`、`feedback_policy_report` 和 `docker_stage_status` 全部存在，并校验 sha256。

2. 无凭证 accepted 伪装没有被拒绝。
   - 风险：`accepted_with_credentials` 可以和 `credential_status=missing_all`、`credential_source=none` 同时出现。
   - 处理：已修复。DeepSeek accepted 和 OpenAI fallback success 都必须有 `credential_status=present`、redacted credential source、accepted final verifier 和 success run outcome。

3. Docker backend 伪装没有被拒绝。
   - 风险：acceptance report 摘要可声称 `docker_backend`，但引用的 status file 仍是 `interface_only`。
   - 处理：已修复。检查器会重新读取 `docker_stage_status.json`，并要求 report 摘要和 status file 的 mode、status、docker_backend_implemented、execution behavior 和 production sandbox claim 逐字段一致。

### P2

1. `inspect-v2-acceptance` 初始实现过度信任 report 内部摘要。
   - 处理：已修复。inspect 会重新读取 referenced source artifacts，重新计算 V1 regression、task set、mock provider、real provider、Docker stage、feedback policy 和 export audit summary，并和 report 摘要比对。

2. provider raw marker 和非 trainable 样本的拒绝主要是 build-time snapshot。
   - 处理：已修复。inspect 阶段会重新扫描 export roots，并重新调用 export audit 检查。

### P3

1. Stage 15 单元测试负例不足。
   - 处理：已修复。`tests/unit/test_v2_acceptance.py` 从 4 个测试扩展到 8 个测试，新增 missing evidence ref、accepted without credentials、Docker summary mismatch、inspect-time provider raw marker 和 non-trainable formal JSONL 负例。

## 审查正例证据

- `build-v2-acceptance-report` 只读取既有 report、manifest、audit 和 status 文件。
- `v2_acceptance_report.json` 引用所有关键输入并记录 sha256。
- feedback policy coverage 覆盖 `disabled`、`public_only`、`structured_public_feedback`、`oracle_hidden_feedback`。
- feedback-tests-passed policy coverage 覆盖 `stop_immediately`、`require_model_final`、`continue`。
- 文档明确 Docker 当前是 `interface_only`，不是生产级安全沙箱。

## 审查负例证据

- 缺失关键 evidence ref 会被拒绝。
- 无凭证 accepted 伪装会被拒绝。
- Docker summary 和 status file 不一致会被拒绝。
- provider raw marker 进入正式训练 JSONL 会被拒绝。
- 非 trainable 样本进入正式训练 JSONL 会被拒绝。

## 修复后验证

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v2_acceptance.py -q
PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-feedback-policy-coverage --experiment-dir runs/v2-final-task-set-20260501T223447Z --output /tmp/repo-harness-feedback-policy-review.json --assert-complete
```

验证结果：

- Stage 15 acceptance 单元测试通过，8 个测试通过。
- `inspect-v2-acceptance --assert-complete` 通过。
- `inspect-feedback-policy-coverage --assert-complete` 通过。

## 结论

Stage 15 审查发现的 P1 和 P2 已修复。Stage 15 可以进入全量回归和提交前检查。
