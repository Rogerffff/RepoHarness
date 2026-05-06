# V5 Final Acceptance

## 结论

截至 2026-05-06 本轮 hardening follow-up 复核后，V5 最终验收状态已经从“核心验收通过”修正为“证据链可复核，但当前不再满足 core acceptance”。当前最新 V5 hardening 验收目录为：

```text
runs/v5-final-acceptance-hardening-followup-20260506T062200Z/
```

这次修正关闭了上一轮复核发现的关键假阳性：acceptance inputs 现在会校验 evidence ref 的 `path`、`sha256` 和 `size_bytes`，并递归校验已经绑定的 V5 JSON / JSONL evidence tree 内部引用；acceptance report 的 core inspect 会在引用完整性失败时失败；acceptance bundle 会把 final command log 作为带哈希的 evidence ref 绑定；Stage 4 不再把未执行 final verifier 的真实 provider run 计入 trainable export。

当前 V5 仍然保留有价值的展示证据：12 个可审计任务定义、8 个 PR / issue flow 任务、4 个 SWE-Bench-like anchor、6 条 DeepSeek 真实 provider run metadata、OpenAI / DeepSeek 在 2 个任务上的 provider-axis 补充比较证据、4 个 diagnostic comparison proof 任务、public-safe demo artifact、result summary 和 immutable evidence bundle。但是这些证据不足以支持“训练导出已经形成真实 trainable 样本”或者“V5 core acceptance 已经通过”的结论。

## 关键机器产物

```text
runs/v5-stage4-export-pack-hardening-20260505T184706Z/v5_export_result_pack_manifest.json
runs/v5-stage5-demo-artifacts-hardening-followup2-20260506T062200Z/v5_resume_artifact_index.json
runs/v5-stage5-demo-artifacts-hardening-followup2-20260506T062200Z/v5_interview_result_pack_manifest.json
runs/v5-openai-provider-comparison-20260505T194739Z/comparison_reports_gpt55_final_v3/v5_provider_comparison_report.json
runs/v5-final-acceptance-hardening-followup-20260506T062200Z/v5_acceptance_inputs.json
runs/v5-final-acceptance-hardening-followup-20260506T062200Z/v5_acceptance_report.json
runs/v5-final-acceptance-hardening-followup-20260506T062200Z/v5_acceptance_report_reference_integrity_report.json
runs/v5-final-acceptance-hardening-followup-20260506T062200Z/v5_acceptance_bundle_manifest.json
runs/v5-final-acceptance-hardening-followup-20260506T062200Z/v5_final_acceptance_command_log.jsonl
```

上一轮目录 `runs/v5-final-acceptance-20260505T191500Z/` 只能作为历史失败基线理解，不能再作为 V5 final accepted baseline。

## 验收状态

- `core_acceptance.status=failed`。
- `resume_ready_acceptance.status=blocked`。
- 失败的 core 原因是当前 export pack 中 `real_provider_trainable_records=0`。Stage 3B 的真实 provider run 只记录了最小 provider loop 和 final verifier boundary，`final_verifier_status=not_executed_stage3b_minimal_provider_loop`，因此不能进入 trainable SFT 或 reinforcement learning rollout 分区。
- V5 acceptance report reference integrity 检查通过，未绑定关键证据数量为 `0`。
- V5 public-safe demo bundle 检查通过。
- V5 acceptance bundle immutable inspect 通过。

## 关键验证结果

本轮 hardening 已验证：

```bash
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_v5_*.py -p no:cacheprovider
PATH=.venv/bin:$PATH repo-harness inspect-v5-export-pack runs/v5-stage4-export-pack-hardening-20260505T184706Z/v5_export_result_pack_manifest.json --assert-clean
PATH=.venv/bin:$PATH repo-harness inspect-v5-demo-artifacts runs/v5-stage5-demo-artifacts-hardening-followup2-20260506T062200Z/v5_resume_artifact_index.json --assert-share-safe
PATH=.venv/bin:$PATH repo-harness inspect-v5-inputs runs/v5-final-acceptance-hardening-followup-20260506T062200Z/v5_acceptance_inputs.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v5-final-acceptance-hardening-followup-20260506T062200Z/v5_acceptance_bundle_manifest.json --final-command-log runs/v5-final-acceptance-hardening-followup-20260506T062200Z/v5_final_acceptance_command_log.jsonl --assert-immutable
```

以下命令现在必须失败，并且这个失败是正确的证据边界：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-v5-acceptance runs/v5-final-acceptance-hardening-followup-20260506T062200Z/v5_acceptance_report.json --assert-core-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-acceptance runs/v5-final-acceptance-hardening-followup-20260506T062200Z/v5_acceptance_report.json --assert-resume-ready
```

## V4 Baseline 说明

V4 closure baseline 仍然只由 Stage 0 的以下产物绑定：

```text
runs/v5-stage0-preimplementation-20260505T143530Z/v5_baseline_check_report.json
runs/v5-stage0-preimplementation-20260505T143530Z/v5_preflight_input_binding.json
runs/v5-stage0-preimplementation-20260505T143530Z/v5_preimplementation_command_log.jsonl
```

本轮 hardening 没有在已经包含 V5 源码变更的当前工作区重新把旧 V4 doc-sync bundle immutable inspect 当作阶段门。旧 V4 doc-sync bundle 绑定的是 V4 验收当时的文件字节，V5 源码变更后不应把它作为当前工作区的当前阶段门。

## 可使用表述

可以保守表述为：

```text
RepoHarness V5 hardening 后形成了一条可审计的本地证据链，覆盖任务冻结、真实 provider run metadata、OpenAI / DeepSeek provider-axis 补充比较证据、受控变量比较范围、分区导出审计、public-safe demo artifact、result summary 和 immutable acceptance bundle；同时用 claim gate 明确阻断 trainable export、core acceptance 和 resume-ready 强表述。
```

不得表述为 V5 core acceptance 已通过、resume-ready multi-provider comparison 已完成、preference export 已完成、完整 SWE-Bench 榜单复现、生产级安全沙箱、分布式强化学习 rollout 集群、完整 Claude Code / Codex 产品复刻，或者已经训练出 coding agent。OpenAI / DeepSeek 的 2 任务 provider-axis proof 只能作为补充比较证据讲解，不能覆盖 trainable export、scaffold comparison、budget comparison 或 resume-ready acceptance 的缺口。
