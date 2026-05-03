# RepoHarness 第三版（V3）验收 Walkthrough

本文是第三版（V3）验收报告生成之后编写的 post-acceptance walkthrough。它说明如何复查当前最终验收证据。本文不是 `v3_acceptance_report.json` 的输入，只由验收包在报告生成之后绑定。

## 1. 基线和固定输入

先确认第三版正式实现基线仍在当前历史中：

```bash
git merge-base --is-ancestor dd8f4d3 HEAD
```

阶段 0 固定了 SWE-Bench-like 输入：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-v3-swebench-fixture \
  --fixture-dir tests/fixtures/v3/swebench_lite_fixed \
  --evidence-dir docs/v3/evidence/swebench-lite-fixed \
  --manifest tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/v3_feasibility_input_manifest.json \
  --assert-frozen
```

adapter-visible 输入位于：

- `tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/`

evaluator-only 或 audit-only 证据位于：

- `docs/v3/evidence/swebench-lite-fixed/evaluator_only/`

## 2. 核心阶段检查

任务、source materialization 和 SWE-Bench-like verifier：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-v3-task-set runs/v3-stage-04-task-adapter-20260502T170000Z --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v3-source-materialization runs/v3-stage-05-source-materialization-20260502T181500Z --report runs/v3-stage-05-source-materialization-20260502T181500Z/source_materialization_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-swebench-like runs/v3-stage-06-swebench-like-20260502T191500Z --manifest runs/v3-stage-06-swebench-like-20260502T191500Z/swebench_like_task_manifest.json --assert-complete
```

Resume、context、long rollout 和 reward diagnostics：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-experiment-resume runs/v3-stage-08-experiment-resume-20260502T214500Z --manifest runs/v3-stage-08-experiment-resume-20260502T214500Z/experiment_resume_manifest.json --assert-resumable
PATH=.venv/bin:$PATH repo-harness inspect-context-report runs/v3-stage-09-context-diagnostics-20260503T-stage9-subagent-fix --report runs/v3-stage-09-context-diagnostics-20260503T-stage9-subagent-fix/context_compaction_report.json --assert-consistent
PATH=.venv/bin:$PATH repo-harness inspect-long-rollout-diagnostics runs/v3-stage-09-context-diagnostics-20260503T-stage9-subagent-fix --report runs/v3-stage-09-context-diagnostics-20260503T-stage9-subagent-fix/long_rollout_diagnostics.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-reward-diagnostics runs/v3-stage-10-failure-diagnostics-20260503T-stage9-subagent-fix --core-report runs/v3-stage-10-failure-diagnostics-20260503T-stage9-subagent-fix/failure_diagnostics_core_report.json --distribution-report runs/v3-stage-10-failure-diagnostics-20260503T-stage9-subagent-fix/failure_distribution_report.json --assert-core-complete
```

## 3. 当前核心 Agent Loop run

真实 repository-level run：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-workspace-backend \
  --status-file runs/v3-core-realrepo-deepseek-20260504T000000Z/agent_loop_runs/v3_core_realrepo_local_buggy_calculator_deepseek_docker_v2/docker_backend_status.json \
  --assert-docker-backend
PATH=.venv/bin:$PATH repo-harness inspect-trajectory-store runs/v3-core-realrepo-deepseek-20260504T000000Z/agent_loop_runs/v3_core_realrepo_local_buggy_calculator_deepseek_docker_v2 --assert-readable
PATH=.venv/bin:$PATH repo-harness inspect-tool-contract runs/v3-core-realrepo-deepseek-20260504T000000Z/agent_loop_runs/v3_core_realrepo_local_buggy_calculator_deepseek_docker_v2 --assert-frozen
```

SWE-Bench-like run：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-workspace-backend \
  --status-file runs/v3-core-swebench-deepseek-20260504T000000Z/agent_loop_runs/v3_core_pytest_dev__pytest_8365_deepseek_docker_patch_focused_amd64_final_only_v7/docker_backend_status.json \
  --assert-docker-backend
PATH=.venv/bin:$PATH repo-harness inspect-trajectory-store runs/v3-core-swebench-deepseek-20260504T000000Z/agent_loop_runs/v3_core_pytest_dev__pytest_8365_deepseek_docker_patch_focused_amd64_final_only_v7 --assert-readable
PATH=.venv/bin:$PATH repo-harness inspect-tool-contract runs/v3-core-swebench-deepseek-20260504T000000Z/agent_loop_runs/v3_core_pytest_dev__pytest_8365_deepseek_docker_patch_focused_amd64_final_only_v7 --assert-frozen
```

The SWE-Bench-like final verifier result is evaluator-only, but the public summary is:

- final verifier accepted
- fail-to-pass：`1/1`
- pass-to-pass：`32/32`
- hidden feedback visible to model：`false`

## 4. Export audit

当前 export audit 目录：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-v3-export-audit \
  runs/v3-export-audit-rerun-20260504T003000Z \
  --manifest runs/v3-export-audit-rerun-20260504T003000Z/export_manifest.json \
  --audit-report runs/v3-export-audit-rerun-20260504T003000Z/audit_report.json \
  --assert-clean
```

预期结果：

- `Inspect V3 export audit: clean`
- `Inspect V3 export audit: passed`
- audit status：`passed_with_warnings`
- warning：`preference_pair_baseline_blocked`
- blocked reason：`no_trainable_preference_pair`

## 5. 预验收测试

预验收 evidence 位于：

- `runs/v3-final-rerun-20260504T010000Z/pre_acceptance_evidence`
- `runs/v3-final-rerun-20260504T010000Z/pre_acceptance_command_log.jsonl`

全量测试命令：

```bash
PATH=.venv/bin:$PATH python -m pytest
```

记录结果：

- `488 passed in 220.34s`

第二版回归命令：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete
```

记录结果：

- `status=passed`
- `task_count=20`
- real provider：`accepted_with_credentials`

## 6. 最终验收报告

最终验收从显式 run selection manifest 开始：

```bash
PATH=.venv/bin:$PATH repo-harness build-v3-run-selection-manifest \
  --run-ref role=replay,path=runs/v3-stage-11-preference-inputs-20260503T023000Z/v3_stage_11_pref_success_public \
  --run-ref role=mock_provider,path=runs/v2-final-mock-provider-20260501T223447Z/mock_provider_smoke_report.json \
  --run-ref role=credential_gated_real_provider,path=runs/v3-independent-real-provider-smoke-20260503T-audit/real_provider_smoke_report.json \
  --run-ref role=real_repository,path=runs/v3-core-realrepo-deepseek-20260504T000000Z/agent_loop_runs/v3_core_realrepo_local_buggy_calculator_deepseek_docker_v2 \
  --run-ref role=swebench_like,path=runs/v3-core-swebench-deepseek-20260504T000000Z/agent_loop_runs/v3_core_pytest_dev__pytest_8365_deepseek_docker_patch_focused_amd64_final_only_v7 \
  --run-ref role=resume,path=runs/v3-stage-08-experiment-resume-20260502T214500Z \
  --run-ref role=context,path=runs/v3-stage-09-context-diagnostics-20260503T-stage9-subagent-fix \
  --run-ref role=long_rollout,path=runs/v3-stage-09-context-diagnostics-20260503T-stage9-subagent-fix \
  --run-ref role=failure_diagnostics,path=runs/v3-stage-10-failure-diagnostics-20260503T-stage9-subagent-fix \
  --output runs/v3-final-rerun-20260504T010000Z/run_selection_manifest.json
```

然后构建 acceptance inputs：

```bash
PATH=.venv/bin:$PATH repo-harness build-v3-acceptance-inputs \
  --run-selection-manifest runs/v3-final-rerun-20260504T010000Z/run_selection_manifest.json \
  --export-root runs/v3-export-audit-rerun-20260504T003000Z \
  --v2-report runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json \
  --pre-acceptance-doc docs/v3/scope-and-roadmap.md \
  --pre-acceptance-doc docs/v3/implementation-plan.md \
  --pre-acceptance-doc docs/v3/review/scope-review.md \
  --pre-acceptance-doc docs/v3/review/implementation-plan-review.md \
  --pre-acceptance-doc docs/v3/review/swe-task-feasibility-results.md \
  --pre-acceptance-doc docs/v3/swe-task-feasibility-experiment-plan.md \
  --documentation-manifest runs/v3-final-rerun-20260504T010000Z/pre_acceptance_documentation_manifest.json \
  --command-log runs/v3-final-rerun-20260504T010000Z/pre_acceptance_command_log.jsonl \
  --test-evidence runs/v3-final-rerun-20260504T010000Z/pre_acceptance_evidence \
  --output runs/v3-final-rerun-20260504T010000Z/v3_acceptance_inputs.json
```

最后生成并检查新的 acceptance report：

```bash
PATH=.venv/bin:$PATH repo-harness build-v3-acceptance-report \
  --acceptance-dir runs/v3-final-rerun-20260504T010000Z/acceptance \
  --input-manifest runs/v3-final-rerun-20260504T010000Z/v3_acceptance_inputs.json \
  --output runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json
PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json --assert-complete
```

预期结果：

- `Report status: passed`
- `Inspect V3 acceptance: complete`
- `Inspect V3 acceptance: passed`

## 7. 验收包

验收报告生成之后，再绑定 post-acceptance 文档：

```bash
PATH=.venv/bin:$PATH repo-harness build-v3-acceptance-bundle \
  --acceptance-dir runs/v3-final-rerun-20260504T010000Z/acceptance \
  --input-manifest runs/v3-final-rerun-20260504T010000Z/v3_acceptance_inputs.json \
  --report runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json \
  --documentation-ref docs/v3/final-acceptance.md \
  --documentation-ref docs/v3/walkthrough.md \
  --output runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json
```

验收包检查：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json --assert-immutable
```

验收包证明最终报告、报告输入、验收命令日志和 post-acceptance 文档在报告生成之后被显式绑定，并且重新计算 sha256 后仍然一致。
