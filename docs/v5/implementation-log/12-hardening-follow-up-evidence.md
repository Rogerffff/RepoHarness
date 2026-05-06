# V5 Hardening Follow-up Evidence 实施日志

## 目标

本次 follow-up 修复 hardening 后剩余的证据同步问题：递归 evidence ref 校验已经进入代码，但公开展示生成物和历史阶段文档仍可能让读者误以为 V5 已经产生 trainable SFT / reinforcement learning rollout 样本，或者误以为首次 Stage 6 的 `core_acceptance.status=passed` 仍是当前结论。

## 实现内容

- 使用修复后的 Stage 5 builder 重新生成 public-safe demo artifact 和 interview result pack。
- 将首次 Stage 4 和 Stage 6 的 implementation log / review 标记为历史记录，明确说明其中的 trainable export 和 core acceptance 通过表述已经被 hardening 撤回。
- 更新最终验收文档和 walkthrough，指向新的 Stage 5 follow-up 目录，并补充 OpenAI / DeepSeek provider-axis 证明的边界。
- 明确当前仍不能声明 V5 core acceptance 通过，因为没有通过 final verifier 的真实 provider trainable record。

## 主要产物

```text
runs/v5-stage5-demo-artifacts-hardening-followup2-20260506T062200Z/v5_resume_artifact_index.json
runs/v5-stage5-demo-artifacts-hardening-followup2-20260506T062200Z/v5_interview_result_pack_manifest.json
runs/v5-stage5-demo-artifacts-hardening-followup2-20260506T062200Z/v5_canonical_demo_walkthrough.md
runs/v5-stage5-demo-artifacts-hardening-followup2-20260506T062200Z/v5_resume_bullets.md
runs/v5-openai-provider-comparison-20260505T194739Z/comparison_reports_gpt55_final_v3/v5_provider_comparison_report.json
```

## 验证命令

```bash
PATH=.venv/bin:$PATH repo-harness build-v5-demo-artifacts --task-set-manifest runs/v5-stage2b-merged-task-set-20260505T152756Z/v5_task_set_manifest.json --executed-run-matrix-manifest runs/v5-stage3b-run-matrix-20260505T164640Z/execution/v5_run_matrix_manifest_executed.json --export-pack-manifest runs/v5-stage4-export-pack-hardening-20260505T184706Z/v5_export_result_pack_manifest.json --stage4-claim-gate-report runs/v5-stage4-export-pack-hardening-20260505T184706Z/v5_resume_claim_gate_report.json --output-dir runs/v5-stage5-demo-artifacts-hardening-followup2-20260506T062200Z --fail-if-output-exists
PATH=.venv/bin:$PATH repo-harness build-v5-interview-result-pack --resume-artifact-index runs/v5-stage5-demo-artifacts-hardening-followup2-20260506T062200Z/v5_resume_artifact_index.json --stage5-claim-gate-report runs/v5-stage5-demo-artifacts-hardening-followup2-20260506T062200Z/v5_resume_claim_gate_report.json --docs12-path docs/12-resume-narrative-and-demo-artifacts.md --output-dir runs/v5-stage5-demo-artifacts-hardening-followup2-20260506T062200Z --fail-if-output-exists
PATH=.venv/bin:$PATH repo-harness inspect-v5-demo-artifacts runs/v5-stage5-demo-artifacts-hardening-followup2-20260506T062200Z/v5_resume_artifact_index.json --assert-share-safe
rg -n "sanitized SFT|rollout 格式样本|分区训练导出|core 方向" runs/v5-stage5-demo-artifacts-hardening-followup2-20260506T062200Z
```

## 验证结果

- `inspect-v5-demo-artifacts --assert-share-safe` 通过。
- 关键词扫描没有在新的 Stage 5 follow-up 目录中发现 `sanitized SFT`、`rollout 格式样本` 或 `分区训练导出`。
- 新的 `v5_result_summary_table.json` 继续记录 `accepted_count=0` 和 `real_provider_trainable_records=0`。

## 允许降级项

允许把当前 V5 表述为 evidence chain hardened、public-safe demo artifacts generated、OpenAI / DeepSeek provider-axis proof available。

## 禁止降级项

不能把当前 V5 表述为 core acceptance passed、trainable export completed、preference export completed、resume-ready provider comparison completed、scaffold comparison completed 或 budget comparison completed。

## 已知限制

本次 follow-up 没有生成通过 final verifier 的真实 provider trainable record，因此不会把 `core_acceptance.status` 改成 passed。要真正关闭这个阻塞，必须实现并执行带仓库工作区修改、patch capture 和 final verifier strict replay 的真实 provider run。
