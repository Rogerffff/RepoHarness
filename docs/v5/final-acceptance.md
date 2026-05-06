# V5 Final Acceptance

## 结论

截至 2026-05-06 本轮 accepted-run follow-up，V5 已经恢复并通过 `core_acceptance`。当前最新 V5 验收目录为：

```text
runs/v5-final-acceptance-accepted-20260506T130655Z/
```

本轮新增的关键变化是：在已经冻结的 `v5_task_008` 上执行了一条真实 DeepSeek V4 Pro provider run。该 run 使用 `single_shot_patch` scaffold 生成补丁，RepoHarness 从冻结源码重新创建 verification workspace，应用 provider final patch，再应用 evaluator-only 测试补丁，并执行 strict final verifier。最终 `accepted=true`、`final_verifier_status=accepted`、`exit_code=0`、`timed_out=false`，因此 Stage 4 可以生成真实 provider trainable SFT 样本和 reinforcement learning rollout 样本。

`resume_ready_acceptance` 仍然是 `blocked`，不是失败误报。阻断原因已经收窄为：scaffold comparison 尚未执行，budget comparison 尚未执行，真实可比较 preference pair 尚未通过 compare scope gate。OpenAI / DeepSeek 在 2 个任务上的 provider-axis proof 已经作为补充证据存在，但它不等价于完整 resume-ready 多维比较。

## 关键机器产物

```text
runs/v5-accepted-provider-formal-deepseek-pro-single-shot-context-20260506T120930Z/v5_run_matrix_manifest_executed.json
runs/v5-stage4-export-pack-accepted-20260506T121016Z/v5_export_result_pack_manifest.json
runs/v5-stage5-demo-artifacts-accepted-followup-20260506T122627Z/v5_resume_artifact_index.json
runs/v5-stage5-demo-artifacts-accepted-followup-20260506T122627Z/v5_interview_result_pack_manifest.json
runs/v5-openai-provider-comparison-20260505T194739Z/comparison_reports_gpt55_final_v3/v5_provider_comparison_report.json
runs/v5-final-acceptance-accepted-20260506T130655Z/v5_acceptance_inputs.json
runs/v5-final-acceptance-accepted-20260506T130655Z/v5_acceptance_report.json
runs/v5-final-acceptance-accepted-20260506T130655Z/v5_acceptance_report_reference_integrity_report.json
runs/v5-final-acceptance-accepted-20260506T130655Z/v5_acceptance_bundle_manifest.json
runs/v5-final-acceptance-accepted-20260506T130655Z/v5_final_acceptance_command_log.jsonl
```

历史目录 `runs/v5-final-acceptance-hardening-followup3-20260506T100500Z/` 只能作为“没有 accepted trainable record 时 core 正确失败”的 hardening 证据理解，不能再作为最新 V5 final baseline。

## 验收状态

- `core_acceptance.status=passed`。
- `resume_ready_acceptance.status=blocked`。
- 任务库存：12 个 accepted / auditable task definitions，其中 8 个来自 PR / issue flow，4 个来自 SWE-Bench-like anchors。
- 真实 provider run：7 条 DeepSeek provider run metadata，其中 1 条通过 strict final verifier。
- 训练导出：`real_provider_trainable_records=2`，对应 1 条 SFT 样本和 1 条 reinforcement learning rollout 样本。
- 非训练分区：`diagnostic_records=1`，`blocked_records=1`，`mock_or_replay_records=0`，`synthetic_safe_stress_records=0`。
- Provider-axis 补充证据：OpenAI / DeepSeek 在 2 个任务上有受控变量一致的 provider-axis proof。
- V5 acceptance report reference integrity：通过，未绑定关键证据数量为 `0`。
- V5 public-safe demo bundle：通过 share-safe inspect。
- V5 acceptance bundle：通过 immutable inspect，并要求 final command log 的 build entry 和 inspect entry 都指向当前最终 bundle。

## 关键验证结果

本轮 fresh pretest 结果：

```text
784 passed in 545.89s (0:09:05)
```

本轮已验证的关键命令：

```bash
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q
PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json --assert-immutable
PATH=.venv/bin:$PATH repo-harness inspect-v5-run-matrix runs/v5-accepted-provider-formal-deepseek-pro-single-shot-context-20260506T120930Z/v5_run_matrix_manifest_executed.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-export-pack runs/v5-stage4-export-pack-accepted-20260506T121016Z/v5_export_result_pack_manifest.json --assert-clean
PATH=.venv/bin:$PATH repo-harness inspect-v5-demo-artifacts runs/v5-stage5-demo-artifacts-accepted-followup-20260506T122627Z/v5_resume_artifact_index.json --assert-share-safe
PATH=.venv/bin:$PATH repo-harness inspect-v5-inputs runs/v5-final-acceptance-accepted-20260506T130655Z/v5_acceptance_inputs.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-acceptance runs/v5-final-acceptance-accepted-20260506T130655Z/v5_acceptance_report.json --assert-core-complete
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v5-final-acceptance-accepted-20260506T130655Z/v5_acceptance_bundle_manifest.json --final-command-log runs/v5-final-acceptance-accepted-20260506T130655Z/v5_final_acceptance_command_log.jsonl --assert-immutable
```

以下命令仍然必须失败，并且这个失败是正确边界：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-v5-acceptance runs/v5-final-acceptance-accepted-20260506T130655Z/v5_acceptance_report.json --assert-resume-ready
```

失败原因不是 provider-axis 完全缺失，而是 resume-ready 还需要 scaffold comparison、budget comparison 和真实可比较 preference pair。

## V4 Baseline 说明

V4 closure baseline 仍然只由 Stage 0 的以下产物绑定：

```text
runs/v5-stage0-preimplementation-20260505T143530Z/v5_baseline_check_report.json
runs/v5-stage0-preimplementation-20260505T143530Z/v5_preflight_input_binding.json
runs/v5-stage0-preimplementation-20260505T143530Z/v5_preimplementation_command_log.jsonl
```

本轮没有在已经包含 V5 源码变更的当前工作区重新把旧 V4 doc-sync bundle immutable inspect 当作阶段门。旧 V4 doc-sync bundle 绑定的是 V4 验收当时的文件字节，V5 源码变更后不应把它作为当前工作区的当前阶段门。

## 可使用表述

可以表述为：

```text
RepoHarness V5 已经通过 core acceptance：它冻结了 12 个可审计任务定义，执行了真实 DeepSeek provider accepted run，使用 strict final verifier 复放补丁，生成了真实 provider SFT 和 reinforcement learning rollout trainable 样本，并用 acceptance inputs、reference integrity report、final command log 和 immutable acceptance bundle 绑定了完整证据链。OpenAI / DeepSeek provider-axis proof 作为补充证据存在，但 resume-ready 仍因 scaffold comparison、budget comparison 和真实可比较 preference pair 缺口而被 claim gate 阻断。
```

不得表述为完整 resume-ready acceptance 已通过、preference export 已完成、完整 SWE-Bench 榜单复现、生产级安全沙箱、分布式强化学习 rollout 集群、完整 Claude Code / Codex 产品复刻，或者已经训练出 coding agent。
