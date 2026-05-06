# V5 Hardening Follow-up Evidence 自审记录

## 审查范围

本记录覆盖 2026-05-06 hardening follow-up 修复：

- 递归 evidence ref 校验后的文档和 bundle 重新绑定风险。
- Stage 4、Stage 5、Stage 6 历史日志中旧 trainable export 和 core acceptance passed 表述。
- OpenAI / DeepSeek provider-axis proof 的机器字段边界。
- 新的 public-safe Stage 5 follow-up 生成物。

## sub agent 发现和处理

只读 sub agent `Pascal` 在提交前审查中发现 1 个 P1、3 个 P2 和 1 个 P3：

- P1：旧 hardening bundle 已经因为文档更新失去 immutable 绑定。
- P2：Stage 6 历史日志正文仍保留 `core_acceptance.status=passed` 结论。
- P2：Stage 4 历史日志仍把旧 trainable 样本写成可用降级项。
- P2：OpenAI / DeepSeek provider-axis proof 的 `counts_toward_resume_ready_acceptance=true` 和 `resume_ready_provider_comparison_satisfied=true` 字段边界过强。
- P3：canonical walkthrough 中“core 方向已具备证据链”的说法偏模糊。

处理结果：

- Stage 4、Stage 5、Stage 6 历史日志和审查记录均增加历史假阳性说明，并把当前可信状态改为 `real_provider_trainable_records=0` 和 `core_acceptance.status=failed`。
- `src/repo_harness/v5_run_matrix.py` 已把 provider-axis proof 改为 `provider_axis_comparison_satisfied=true`，同时明确 `resume_ready_provider_comparison_satisfied=false`、`counts_toward_resume_ready_acceptance=false`。
- 已重新生成 OpenAI / DeepSeek provider-axis comparison report：`runs/v5-openai-provider-comparison-20260505T194739Z/comparison_reports_gpt55_final_v3/`。
- `src/repo_harness/v5_demo_artifacts.py` 已把 canonical walkthrough 降级讲法改成“具备可复核证据链，但 core acceptance 仍失败”。
- 已重新生成 Stage 5 follow-up public-safe artifacts：`runs/v5-stage5-demo-artifacts-hardening-followup2-20260506T062200Z/`。

## 验证结果

已通过：

```bash
PATH=.venv/bin:$PATH python -m compileall src/repo_harness/v5_run_matrix.py src/repo_harness/v5_demo_artifacts.py
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_v5_run_matrix.py tests/unit/test_v5_demo_artifacts.py
PATH=.venv/bin:$PATH repo-harness inspect-v5-run-matrix runs/v5-openai-provider-comparison-20260505T194739Z/comparison_reports_gpt55_final_v3/v5_matrix_compare_scope_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-demo-artifacts runs/v5-stage5-demo-artifacts-hardening-followup2-20260506T062200Z/v5_resume_artifact_index.json --assert-share-safe
```

结果：

```text
8 passed
V5 provider-axis comparison scope inspect passed
V5 Stage 5 follow-up demo artifacts inspect passed
```

## 允许降级项

- 可以声明 OpenAI / DeepSeek provider-axis supplemental comparison proof available。
- 可以声明 evidence chain hardened、public-safe demo artifacts generated 和 immutable bundle passed，前提是新的 Stage 6 follow-up bundle 重新生成并通过 immutable inspect。

## 禁止降级项

- 不允许声明 V5 core acceptance passed。
- 不允许声明 trainable export completed。
- 不允许声明 resume-ready multi-provider comparison completed。
- 不允许声明 scaffold comparison、budget comparison 或 preference export completed。

## 审查结论

当前代码和文档修复方向正确。提交前仍必须重新生成 Stage 6 follow-up acceptance inputs、acceptance report、acceptance bundle 和 final command log，并用当前文档字节通过 immutable inspect；旧 `runs/v5-final-acceptance-hardening-20260505T190928Z/` bundle 不能继续作为当前提交后的最终 immutable 证据。
