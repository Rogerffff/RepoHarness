# V5 Walkthrough

## 阅读路径

V5 walkthrough 的目标是让面试官沿着一条代表任务理解证据链，同时清楚看到当前 hardening 后的降级边界。推荐顺序如下：

1. 查看任务库存：`runs/v5-stage2b-merged-task-set-20260505T152756Z/v5_task_set_manifest.json`。
2. 查看真实 provider 运行矩阵：`runs/v5-stage3b-run-matrix-20260505T164640Z/execution/v5_run_matrix_manifest_executed.json`。
3. 查看比较范围：`runs/v5-stage3c-comparison-reports-20260505T171500Z/v5_matrix_compare_scope_report.json`。
4. 查看 hardening 后的导出分区：`runs/v5-stage4-export-pack-hardening-20260505T184706Z/v5_export_result_pack_manifest.json`。
5. 查看 hardening follow-up 后的 public-safe 展示包：`runs/v5-stage5-demo-artifacts-hardening-followup2-20260506T062200Z/v5_resume_artifact_index.json`。
6. 查看 hardening follow-up 后的最终验收报告：`runs/v5-final-acceptance-hardening-followup-20260506T062200Z/v5_acceptance_report.json`。
7. 如果要展示新增 provider-axis 证据，再查看 OpenAI / DeepSeek 2 任务补充比较报告：`runs/v5-openai-provider-comparison-20260505T194739Z/comparison_reports_gpt55_final_v3/v5_provider_comparison_report.json`。

## 代表任务

Canonical demo 绑定任务：

```text
task_id: v5_task_003
candidate_id: pallets/click#3208
repository: pallets/click
task_family: cli_error_formatting
```

模型可见任务描述是：命令错误输出应该只在相关 help option 实际可用时展示帮助提示，包括子命令 option shadow 父命令 option 的情况。

这个任务适合展示 V5 的原因是：它来自真实 PR / issue flow，任务故事清楚，源码和 verifier 计划已经冻结，并且 Stage 3B 有真实 provider run metadata。

## 证据链

Stage 2 固定了任务定义、adapter-visible input、源码哈希、visibility scan 和 evaluator-only evidence 边界。

Stage 3B 使用 `deepseek` provider family 执行最小真实 provider loop。该 loop 受限于 `stage3b_constrained_one_turn_no_tool_calls` budget，因此不能讲成完成修复的 accepted patch。它的价值是证明 provider credential gate、模型可见输入、trajectory ref、final verifier boundary ref 和 command log 能被绑定。

Stage 3C 原始验收链证明四个任务进入 comparison proof，但 comparison validity 是 diagnostic-only。也就是说，它能证明受控变量被记录，不能证明 provider、scaffold 或 budget 的胜负结论。后续 OpenAI 扩展另外生成了 `v5_task_005` 和 `v5_pr_issue_click_3364` 两个任务上的 DeepSeek / OpenAI provider-axis proof；这只能作为补充比较证据，不能把当前 V5 改写成 resume-ready，因为 scaffold comparison、budget comparison、preference pair 和 trainable export 仍然阻断。

Stage 4 hardening 后重新生成分区导出包。由于当前真实 provider run 的 `final_verifier_status=not_executed_stage3b_minimal_provider_loop`，SFT 和 reinforcement learning rollout trainable 分区为空，`real_provider_trainable_records=0`。这些运行只进入 failure、diagnostic-only 或 blocked 证据，不再被计入 trainable payload。

Stage 5 hardening follow-up 后重新生成 public-safe demo card、canonical walkthrough、redacted transcript excerpt、result summary 和 interview result pack。所有公开 artifact 都只引用脱敏摘要，不引用 provider 私有载荷、evaluator-only 原始证据、隐藏测试、credential marker 或 reward 数值；新的 walkthrough 和简历 bullet 明确说明 trainable SFT / reinforcement learning rollout 分区为空。

Stage 6 hardening 后生成 acceptance inputs、acceptance report、reference integrity report、acceptance bundle 和 final command log。当前 core acceptance 正确失败，resume-ready acceptance 继续阻断。这个结果比上一轮“core passed”的结论更保守，也更符合 final verifier 权威边界。

## 现场演示命令

```bash
PATH=.venv/bin:$PATH repo-harness inspect-v5-inputs runs/v5-final-acceptance-hardening-followup-20260506T062200Z/v5_acceptance_inputs.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-demo-artifacts runs/v5-stage5-demo-artifacts-hardening-followup2-20260506T062200Z/v5_resume_artifact_index.json --assert-share-safe
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v5-final-acceptance-hardening-followup-20260506T062200Z/v5_acceptance_bundle_manifest.json --final-command-log runs/v5-final-acceptance-hardening-followup-20260506T062200Z/v5_final_acceptance_command_log.jsonl --assert-immutable
```

如果面试官追问为什么不能使用更强表述，可以展示：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-v5-acceptance runs/v5-final-acceptance-hardening-followup-20260506T062200Z/v5_acceptance_report.json --assert-core-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-acceptance runs/v5-final-acceptance-hardening-followup-20260506T062200Z/v5_acceptance_report.json --assert-resume-ready
```

第一条命令会失败，因为当前没有任何通过 final verifier 的真实 provider trainable record。第二条命令会失败，因为当前没有满足 resume-ready 的多真实 provider、真实 preference pair、scaffold comparison 和 budget comparison 门槛。这两个失败都是 claim gate 和 final verifier boundary 的预期保护行为。

## 现场负例

如果 acceptance inputs 中任意 evidence ref 的 `path`、`sha256` 或 `size_bytes` 被篡改，`inspect-v5-inputs --assert-complete` 应失败。

如果 acceptance report 引用 acceptance inputs 之外的关键证据，`inspect-v5-acceptance --assert-core-complete` 应失败，并在 `v5_acceptance_report_reference_integrity_report.json` 中记录未绑定证据。

如果 acceptance bundle 的文档、report、post-report inspect output、pre-bundle command log 或 final command log 发生 sha256 漂移，`inspect-acceptance-bundle --assert-immutable` 应失败。

如果 public demo bundle 混入 provider 私有载荷、evaluator-only 内容、模型可见泄漏，或者 copy-safe 简历 bullet 使用被 claim gate 阻断的强表述，`inspect-v5-demo-artifacts --assert-share-safe` 应失败。

## 降级讲法

当前项目可以讲成 V5 hardening 已形成可复核证据链：固定任务、固定源码、固定 verifier 计划、固定工具策略、真实 provider run metadata、trajectory、分区导出审计、public-safe demo 和 immutable acceptance bundle。

当前项目不能讲成 V5 core acceptance 已通过，也不能讲成简历完成级强结果。缺口非常具体：需要至少一个通过 final verifier 的真实 trainable record；如果要恢复 resume-ready，还需要第二个真实 provider family、真实可比较 preference pair、scaffold 对比和 budget 对比。
