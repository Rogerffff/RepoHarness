# RepoHarness 第三版（V3）验收 Walkthrough

本文是第三版（V3）验收报告生成之后编写的 post-acceptance walkthrough。它描述如何从冻结输入、阶段产物、预验收证据、最终验收报告和验收包逐步复查第三版能力。

## 1. 基线和输入冻结

第三版正式实现基线为：

```bash
git merge-base --is-ancestor dd8f4d3 HEAD
```

阶段 0 通过写型冻结命令和只读检查命令固定了 SWE-Bench-like 输入：

```bash
PATH=.venv/bin:$PATH repo-harness prepare-v3-swebench-fixture --feasibility-root runs/v3-swe-feasibility-20260502T083722Z --fixture-dir tests/fixtures/v3/swebench_lite_fixed --evidence-dir docs/v3/evidence/swebench-lite-fixed
PATH=.venv/bin:$PATH repo-harness inspect-v3-swebench-fixture --fixture-dir tests/fixtures/v3/swebench_lite_fixed --evidence-dir docs/v3/evidence/swebench-lite-fixed --manifest tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/v3_feasibility_input_manifest.json --assert-frozen
```

adapter-visible 输入位于：

- `tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/`

evaluator-only 或 audit-only 证据位于：

- `docs/v3/evidence/swebench-lite-fixed/evaluator_only/`

阶段 4 到阶段 13 默认读取受版本控制的 adapter input，不从浮动网络分支或未跟踪 `runs/` 目录读取正式任务输入。

## 2. 关键阶段产物

任务和 source materialization：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-v3-task-set runs/v3-stage-04-task-adapter-20260502T170000Z --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v3-source-materialization runs/v3-stage-05-source-materialization-20260502T181500Z --report runs/v3-stage-05-source-materialization-20260502T181500Z/source_materialization_report.json --assert-complete
```

SWE-Bench-like verifier：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-swebench-like runs/v3-stage-06-swebench-like-20260502T191500Z --manifest runs/v3-stage-06-swebench-like-20260502T191500Z/swebench_like_task_manifest.json --assert-complete
```

Agent Loop、resume、context、failure diagnostics 和 export audit：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-v3-agent-loop-integration runs/v3-stage-07-agent-loop-20260502T203000Z --report runs/v3-stage-07-agent-loop-20260502T203000Z/v3_agent_loop_integration_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-experiment-resume runs/v3-stage-08-experiment-resume-20260502T214500Z --manifest runs/v3-stage-08-experiment-resume-20260502T214500Z/experiment_resume_manifest.json --assert-resumable
PATH=.venv/bin:$PATH repo-harness inspect-context-report runs/v3-stage-09-context-diagnostics-20260503T-stage9-subagent-fix --report runs/v3-stage-09-context-diagnostics-20260503T-stage9-subagent-fix/context_compaction_report.json --assert-consistent
PATH=.venv/bin:$PATH repo-harness inspect-long-rollout-diagnostics runs/v3-stage-09-context-diagnostics-20260503T-stage9-subagent-fix --report runs/v3-stage-09-context-diagnostics-20260503T-stage9-subagent-fix/long_rollout_diagnostics.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-reward-diagnostics runs/v3-stage-10-failure-diagnostics-20260503T-stage9-subagent-fix --core-report runs/v3-stage-10-failure-diagnostics-20260503T-stage9-subagent-fix/failure_diagnostics_core_report.json --distribution-report runs/v3-stage-10-failure-diagnostics-20260503T-stage9-subagent-fix/failure_distribution_report.json --assert-core-complete
PATH=.venv/bin:$PATH repo-harness inspect-v3-export-audit runs/v3-stage-11-export-audit-20260503T030000Z --manifest runs/v3-stage-11-export-audit-20260503T030000Z/export_manifest.json --audit-report runs/v3-stage-11-export-audit-20260503T030000Z/audit_report.json --assert-clean
```

阶段 7 至阶段 10 的原始审查曾因为子代理智能体线程未清理而退回自审。追溯补审记录位于：

- `docs/v3/review/implementation/stage-07-to-10-retrospective-subagent-review.md`
- `docs/v3/implementation-log/post-acceptance-stage-07-to-10-subagent-review-and-stage-09-fix.md`

追溯补审后，阶段 9 使用修复后的 context diagnostics 产物，阶段 10 使用重新绑定修复后阶段 9 evidence 的 failure diagnostics 产物。

## 3. 最终预验收

最终验收前先运行并记录全量测试和第二版回归。输出写入独立预验收证据目录：

- `runs/v3-final-pre-acceptance-20260503T043025Z/evidence/`

全量测试：

```bash
PATH=.venv/bin:$PATH python -m pytest -q
```

记录结果：

- `449 passed in 236.72s`

第二版回归：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete
```

记录结果：

- `status=passed`
- `task_count=20`
- mock provider：`accepted`
- real provider：`accepted_with_credentials`

预验收命令日志：

- `runs/v3-final-pre-acceptance-20260503T043025Z/pre_acceptance_command_log.jsonl`

预验收文档清单：

- `runs/v3-final-pre-acceptance-20260503T043025Z/manifests/pre_acceptance_documentation_manifest.json`

## 4. 最终验收报告

最终验收从显式 run selection manifest 开始，不扫描 latest run：

```bash
PATH=.venv/bin:$PATH repo-harness build-v3-run-selection-manifest \
  --run-ref role=replay,path=runs/v3-stage-11-preference-inputs-20260503T023000Z/v3_stage_11_pref_success_public \
  --run-ref role=mock_provider,path=runs/v2-final-mock-provider-20260501T223447Z/mock_provider_smoke_report.json \
  --run-ref role=credential_gated_real_provider,path=runs/v2-real-provider-smoke-20260502T091000Z/real_provider_smoke_report.json \
  --run-ref role=real_repository,path=runs/v3-stage-07-agent-loop-20260502T203000Z/agent_loop_runs/v3_stage_07_realrepo_local_buggy_calculator \
  --run-ref role=swebench_like,path=runs/v3-final-swebench-agent-loop-20260503T035615Z/agent_loop_runs/v3_stage_13_sympy__sympy-24909_public_issue_patch_v3 \
  --run-ref role=resume,path=runs/v3-stage-08-experiment-resume-20260502T214500Z \
  --run-ref role=context,path=runs/v3-stage-09-context-diagnostics-20260503T-stage9-subagent-fix \
  --run-ref role=long_rollout,path=runs/v3-stage-09-context-diagnostics-20260503T-stage9-subagent-fix \
  --run-ref role=failure_diagnostics,path=runs/v3-stage-10-failure-diagnostics-20260503T-stage9-subagent-fix \
  --output runs/v3-final-acceptance-20260503T043025Z/run_selection_manifest.json
```

然后显式绑定 acceptance inputs：

```bash
PATH=.venv/bin:$PATH repo-harness build-v3-acceptance-inputs \
  --run-selection-manifest runs/v3-final-acceptance-20260503T043025Z/run_selection_manifest.json \
  --export-root runs/v3-stage-11-export-audit-20260503T030000Z \
  --v2-report runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json \
  --pre-acceptance-doc docs/v3/scope-and-roadmap.md \
  --pre-acceptance-doc docs/v3/implementation-plan.md \
  --pre-acceptance-doc docs/v3/review/scope-review.md \
  --pre-acceptance-doc docs/v3/review/implementation-plan-review.md \
  --pre-acceptance-doc docs/v3/review/swe-task-feasibility-results.md \
  --pre-acceptance-doc docs/v3/swe-task-feasibility-experiment-plan.md \
  --documentation-manifest runs/v3-final-pre-acceptance-20260503T043025Z/manifests/pre_acceptance_documentation_manifest.json \
  --command-log runs/v3-final-pre-acceptance-20260503T043025Z/pre_acceptance_command_log.jsonl \
  --test-evidence runs/v3-final-pre-acceptance-20260503T043025Z/evidence \
  --output runs/v3-final-acceptance-20260503T043025Z/v3_acceptance_inputs.json
```

最后构建并检查新验收目录：

```bash
PATH=.venv/bin:$PATH repo-harness build-v3-acceptance-report --acceptance-dir runs/v3-final-acceptance-20260503T043025Z/acceptance --input-manifest runs/v3-final-acceptance-20260503T043025Z/v3_acceptance_inputs.json --output runs/v3-final-acceptance-20260503T043025Z/acceptance/v3_acceptance_report.json
PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-final-acceptance-20260503T043025Z/acceptance/v3_acceptance_report.json --assert-complete
```

最终结果：

- `Report status: passed`
- `Inspect V3 acceptance: complete`
- `Inspect V3 acceptance: passed`

## 5. 验收包

验收报告生成之后，再绑定 post-acceptance 文档：

```bash
PATH=.venv/bin:$PATH repo-harness build-v3-acceptance-bundle \
  --acceptance-dir runs/v3-final-acceptance-20260503T043025Z/acceptance \
  --input-manifest runs/v3-final-acceptance-20260503T043025Z/v3_acceptance_inputs.json \
  --report runs/v3-final-acceptance-20260503T043025Z/acceptance/v3_acceptance_report.json \
  --documentation-ref docs/v3/final-acceptance.md \
  --documentation-ref docs/v3/walkthrough.md \
  --documentation-ref docs/v3/implementation-log/13-stage-13-final-acceptance-and-docs.md \
  --documentation-ref docs/v3/review/implementation/stage-13-review.md \
  --documentation-ref docs/v3/implementation-log/post-acceptance-stage-07-to-10-subagent-review-and-stage-09-fix.md \
  --documentation-ref docs/v3/review/implementation/stage-07-to-10-retrospective-subagent-review.md \
  --output runs/v3-final-acceptance-20260503T043025Z/acceptance/acceptance_bundle_manifest.json
```

验收包检查：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-final-acceptance-20260503T043025Z/acceptance/acceptance_bundle_manifest.json --assert-immutable
```

验收包的用途是证明最终报告、报告输入、验收命令日志和 post-acceptance 文档在报告生成之后被显式绑定，并且重新计算 sha256 后仍然一致。
