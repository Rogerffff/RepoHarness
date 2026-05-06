# V5 Walkthrough

## 阅读路径

V5 walkthrough 的目标是让面试官沿着一条真实 accepted run 理解证据链，同时清楚看到当前仍然不能越过的 resume-ready 边界。推荐顺序如下：

1. 查看任务库存：`runs/v5-stage2b-merged-task-set-20260505T152756Z/v5_task_set_manifest.json`。
2. 查看 accepted provider run 矩阵：`runs/v5-accepted-provider-formal-deepseek-pro-single-shot-context-20260506T120930Z/v5_run_matrix_manifest_executed.json`。
3. 查看 accepted 后的导出分区：`runs/v5-stage4-export-pack-accepted-20260506T121016Z/v5_export_result_pack_manifest.json`。
4. 查看 public-safe 展示包：`runs/v5-stage5-demo-artifacts-accepted-followup-20260506T122627Z/v5_resume_artifact_index.json`。
5. 查看最终验收报告：`runs/v5-final-acceptance-accepted-20260506T130655Z/v5_acceptance_report.json`。
6. 查看 OpenAI / DeepSeek 2 任务 provider-axis 补充比较报告：`runs/v5-openai-provider-comparison-20260505T194739Z/comparison_reports_gpt55_final_v3/v5_provider_comparison_report.json`。

## 代表任务

Canonical demo 绑定任务：

```text
task_id: v5_task_008
candidate_id: pelletier/go-toml#1041
repository: pelletier/go-toml
task_family: parser_error_location
provider: deepseek
model_id: deepseek-v4-pro
scaffold_id: single_shot_patch
budget_policy_id: v5_accepted_single_shot_patch_budget
```

模型可见任务描述只包含脱敏后的修复目标和公开源码上下文。它不包含 evaluator-only 测试补丁、gold patch、隐藏测试 selector、final verifier 输出、reward 数值、provider raw request / response 或 credential marker。

## 证据链

Stage 2 固定了任务定义、adapter-visible input、源码哈希、visibility scan 和 evaluator-only evidence 边界。

Stage 3B 本轮追加了一条窄范围 accepted provider run。DeepSeek V4 Pro 生成了一个非空 unified diff，修改 `unstable/parser.go` 中 parser error location 的输入片段选择逻辑。RepoHarness 随后从冻结源码重新创建 verification workspace，先应用 provider final patch，再应用 evaluator-only 测试补丁，最后执行 strict final verifier。最终结果是：

```text
accepted=true
final_verifier_ran=true
final_verifier_status=accepted
final_verifier_mode=strict_patch_replay
exit_code=0
timed_out=false
actual_provider_call_count=1
```

同一个 executed run matrix 还保留之前 6 条真实 DeepSeek provider run metadata，因此当前 result summary 的真实 provider run 分母是 7，accepted 数量是 1。

Stage 4 使用严格 accepted predicate 重新生成 export pack。只有同时满足 `accepted=true`、`final_verifier_ran=true`、`final_verifier_status=accepted`、`final_verifier_mode=strict_patch_replay`、final patch 非空、hidden test patch apply 成功、final verifier result 完整的 run 才能进入 trainable payload。本轮导出结果为：

```text
real_provider_trainable_records=2
diagnostic_records=1
blocked_records=1
mock_or_replay_records=0
synthetic_safe_stress_records=0
```

这 2 条 trainable records 分别对应 1 条 SFT 样本和 1 条 reinforcement learning rollout 样本。未通过 final verifier 的 provider run 仍然只进入 failure、diagnostic-only 或 blocked 证据，不会混入 trainable payload。

Stage 5 重新生成 public-safe demo card、canonical walkthrough、redacted transcript excerpt、result summary 和 interview result pack。当前 demo card 可以展示任务冻结、真实 provider accepted run evidence、trainable 分区导出、provider-axis 补充证据和 public-safe demo artifact；它仍然明确阻断 resume-ready 多维比较、preference export completed 和 export stress test completed。

Stage 6 重新生成 acceptance inputs、acceptance report、reference integrity report、acceptance bundle 和 final command log。`inspect-v5-acceptance --assert-core-complete` 通过；`inspect-v5-acceptance --assert-resume-ready` 仍然失败。这个失败是预期边界，因为当前缺口已经收窄为 scaffold comparison、budget comparison 和真实可比较 preference pair。

## Provider-Axis 说明

OpenAI / DeepSeek provider-axis proof 已经存在，路径是：

```text
runs/v5-openai-provider-comparison-20260505T194739Z/comparison_reports_gpt55_final_v3/v5_provider_comparison_report.json
```

它证明 2 个任务在 provider 轴上有 DeepSeek / OpenAI 真实 provider call evidence，并记录受控变量一致性。它不能单独改写成 resume-ready acceptance，因为 resume-ready 还要求 scaffold comparison、budget comparison 和至少 1 个真实可比较 preference pair。

## 现场演示命令

```bash
PATH=.venv/bin:$PATH repo-harness inspect-v5-run-matrix runs/v5-accepted-provider-formal-deepseek-pro-single-shot-context-20260506T120930Z/v5_run_matrix_manifest_executed.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-export-pack runs/v5-stage4-export-pack-accepted-20260506T121016Z/v5_export_result_pack_manifest.json --assert-clean
PATH=.venv/bin:$PATH repo-harness inspect-v5-demo-artifacts runs/v5-stage5-demo-artifacts-accepted-followup-20260506T122627Z/v5_resume_artifact_index.json --assert-share-safe
PATH=.venv/bin:$PATH repo-harness inspect-v5-inputs runs/v5-final-acceptance-accepted-20260506T130655Z/v5_acceptance_inputs.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-acceptance runs/v5-final-acceptance-accepted-20260506T130655Z/v5_acceptance_report.json --assert-core-complete
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v5-final-acceptance-accepted-20260506T130655Z/v5_acceptance_bundle_manifest.json --final-command-log runs/v5-final-acceptance-accepted-20260506T130655Z/v5_final_acceptance_command_log.jsonl --assert-immutable
```

如果面试官追问为什么不能使用 resume-ready 强表述，可以展示：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-v5-acceptance runs/v5-final-acceptance-accepted-20260506T130655Z/v5_acceptance_report.json --assert-resume-ready
```

这条命令会失败，因为当前没有 scaffold comparison、budget comparison 和真实可比较 preference pair。这个失败不是 core acceptance 失败，也不是 provider-axis 完全缺失，而是 claim gate 对 resume-ready 强表述的正确保护。

## 现场负例

如果 acceptance inputs 中任意 evidence ref 的 `path`、`sha256` 或 `size_bytes` 被篡改，`inspect-v5-inputs --assert-complete` 应失败。

如果 acceptance report 引用 acceptance inputs 之外的关键证据，`inspect-v5-acceptance --assert-core-complete` 应失败，并在 `v5_acceptance_report_reference_integrity_report.json` 中记录未绑定证据。

如果 acceptance bundle 的文档、report、post-report inspect output、pre-bundle command log 或 final command log 发生 sha256 漂移，`inspect-acceptance-bundle --assert-immutable` 应失败。

如果 public demo bundle 混入 provider 私有载荷、evaluator-only 内容、模型可见泄漏，或者 copy-safe 简历 bullet 使用被 claim gate 阻断的强表述，`inspect-v5-demo-artifacts --assert-share-safe` 应失败。

## 降级讲法

当前项目可以讲成 V5 已通过 core acceptance：固定任务、固定源码、固定 verifier 计划、固定工具策略、真实 provider accepted run、strict final verifier、trajectory、分区导出、public-safe demo 和 immutable acceptance bundle 都有可追溯证据。

当前项目不能讲成完整 resume-ready acceptance 已通过。缺口非常具体：还需要 scaffold 对比、budget 对比和真实可比较 preference pair。
