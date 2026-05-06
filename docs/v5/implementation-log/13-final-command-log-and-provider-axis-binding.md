# V5 Hardening Follow-up：最终命令日志闭环和 provider-axis 证据绑定

## 目标

本轮修复 V5 复核中发现的 final command log 闭环和 OpenAI / DeepSeek provider-axis 补充证据绑定问题。修复范围只覆盖 V5 相关实现、测试、机器产物和 V5 文档，不回滚或提交工作区内既有的无关文档改动。

## 实现内容

- `inspect-acceptance-bundle --assert-immutable` 现在要求 final command log 至少包含一条指向当前最终 `v5_acceptance_bundle_manifest.json` 的 `build-v5-acceptance-bundle` entry，以及一条指向当前最终 bundle 的 `inspect-acceptance-bundle --assert-immutable` entry。
- 新增 `plan-v5-acceptance-bundle-build-entry`，用于生成最终 bundle 自引用构建 entry。该 entry 使用 `self_referential_input_paths` 和 `self_referential_output_paths` 表达 final command log 与最终 bundle 之间的哈希循环边界。
- `plan-acceptance-bundle-inspect-entry` 新增 `--self-referential-acceptance-bundle`，用于最终 bundle 自身尚未生成但必须进入 final command log 的场景。
- `inspect-v5-run-matrix` 现在可以检查 `repo_harness_v5_provider_comparison_report_v0`。
- `build-v5-demo-artifacts` 新增可选 `--provider-comparison-report`，用于把 OpenAI / DeepSeek 两任务 provider-axis proof 写入 result summary 和 Stage 5 claim gate，同时保持 resume-ready 强表述 blocked。
- `build-v5-acceptance-inputs` 新增可选 `--v5-provider-comparison-report`，用于把 provider-axis proof 作为 acceptance inputs 的显式 evidence ref 绑定。
- `_resume_failures()` 现在会区分“缺少第二 provider”和“已有 provider-axis 补充证据但整体 resume-ready 仍被其他门阻断”。

## 主要修改文件

- `src/repo_harness/v5_acceptance.py`
- `src/repo_harness/v5_demo_artifacts.py`
- `src/repo_harness/v5_evidence.py`
- `src/repo_harness/v5_run_matrix.py`
- `src/repo_harness/cli/main.py`
- `src/repo_harness/schema_versions.py`
- `tests/unit/test_v5_acceptance.py`
- `tests/unit/test_v5_demo_artifacts.py`
- `tests/unit/test_v5_run_matrix.py`

## 新增或更新的机器产物

- `runs/v5-stage5-demo-artifacts-hardening-followup3-20260506T073000Z/v5_result_summary_table.json`
- `runs/v5-stage5-demo-artifacts-hardening-followup3-20260506T073000Z/v5_resume_claim_gate_report.json`
- `runs/v5-final-acceptance-hardening-followup3-20260506T100500Z/v5_acceptance_inputs.json`
- `runs/v5-final-acceptance-hardening-followup3-20260506T100500Z/v5_acceptance_report.json`
- `runs/v5-final-acceptance-hardening-followup3-20260506T100500Z/v5_final_acceptance_command_log.jsonl`
- `runs/v5-final-acceptance-hardening-followup3-20260506T100500Z/v5_acceptance_bundle_manifest.json`

## 验证口径

- `PATH=.venv/bin:$PATH python -m compileall src`
- `PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v5_acceptance.py tests/unit/test_v5_demo_artifacts.py tests/unit/test_v5_run_matrix.py -q`
- `PATH=.venv/bin:$PATH repo-harness inspect-v5-run-matrix runs/v5-openai-provider-comparison-20260505T194739Z/comparison_reports_gpt55_final_v3/v5_provider_comparison_report.json --assert-complete`
- `PATH=.venv/bin:$PATH repo-harness inspect-v5-demo-artifacts runs/v5-stage5-demo-artifacts-hardening-followup3-20260506T073000Z/v5_resume_artifact_index.json --assert-share-safe`
- 旧的 `runs/v5-final-acceptance-hardening-followup-20260506T062200Z/v5_acceptance_bundle_manifest.json` 在新校验下应失败，因为它的 final command log 只记录了 pre-final bundle 的构建和检查 entry。

## 允许声明

- 可以声明 OpenAI / DeepSeek provider-axis supplemental comparison proof available。
- 可以声明 final command log 对当前最终 bundle 的构建和 inspect entry 已经形成自引用闭环。

## 禁止声明

- 不能声明 V5 core acceptance 已通过，因为当前 trainable SFT 和 reinforcement learning rollout 分区仍然没有通过 final verifier 的真实 provider trainable record。
- 不能声明 resume-ready acceptance 已通过。
- 不能把 provider-axis proof 写成完整的 `multi-provider agent runs`、整体 `controlled multi-provider comparison completed` 或 `preference export completed`。

## 已知限制

本轮没有新增通过 final verifier 的真实 trainable record，因此 V5 仍然是 evidence chain hardened 和 provider-axis proof 补强状态，不是最终通过状态。
