# V3 Stage 10 Implementation Log: Core Failure Diagnostics And Reward Metadata

## Goal

生成第三版最小完成定义要求的核心失败诊断和失败分布报告，用于训练样本过滤和审计。阶段 10 不实现新的 reward model，不实现 penalty 权重调参，不实现 reward hacking 深度分析。

## Implementation Summary

- 新增 `build-v3-reward-diagnostics`，从一个已有 RepoHarness run 只读聚合 `metrics.json`、`verifier.json`、`baseline.json`、`events.jsonl`、`final.patch`，并可绑定 `context_compaction_report.json` 和 `long_rollout_diagnostics.json`。
- 新增 `failure_diagnostics_core_report.json`，记录 patch size、changed files、tool call count、test run count、invalid tool call count、unfinished trajectory、permission violation count、regression detected、environment failure category、parser low confidence、no patch、provider transient、deterministic verifier failure、context limit 和 no progress。
- 新增 `failure_distribution_report.json`，覆盖 provider、Docker backend、environment setup、verifier、permission、tool protocol、context limit、task quality、parser confidence 和 deterministic verifier failure 十个核心类别。
- 新增 `inspect-reward-diagnostics RUN_DIR --core-report RUN_DIR/failure_diagnostics_core_report.json --distribution-report RUN_DIR/failure_distribution_report.json --assert-core-complete`。
- 扩展 `CoreFailureDiagnostics` schema，使核心过滤字段有类型化默认值。
- 新增 `command_log.jsonl`，记录 Stage 10 builder 的输入路径、输出路径、sha256、exit code 和 CLI version。
- 报告层排除了内部可见性保护字段的字面键，避免 `reward_metadata`、`run_outcome` 等禁止项进入后续验收输入扫描面；schema 仍在 inspect 时用默认值重新校验。

## Main Files

- `src/repo_harness/v3_failure_diagnostics.py`
- `src/repo_harness/cli/main.py`
- `src/repo_harness/reward/schemas.py`
- `tests/unit/test_v3_failure_diagnostics.py`

## Machine Artifacts

Primary Stage 10 artifact directory:

- `runs/v3-stage-10-failure-diagnostics-20260502T234500Z/`

Key files:

- `runs/v3-stage-10-failure-diagnostics-20260502T234500Z/failure_diagnostics_core_report.json`
- `runs/v3-stage-10-failure-diagnostics-20260502T234500Z/failure_distribution_report.json`
- `runs/v3-stage-10-failure-diagnostics-20260502T234500Z/v3_failure_diagnostics_report.json`
- `runs/v3-stage-10-failure-diagnostics-20260502T234500Z/command_log.jsonl`
- `runs/v3-stage-10-failure-diagnostics-20260502T234500Z/input_run/`
- `runs/v3-stage-10-failure-diagnostics-20260502T234500Z/supporting_inputs/context_compaction_report.json`
- `runs/v3-stage-10-failure-diagnostics-20260502T234500Z/supporting_inputs/long_rollout_diagnostics.json`

## Validation Commands

- `PATH=.venv/bin:$PATH python -m compileall src`
- `PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v3_failure_diagnostics.py tests/unit/test_v3_schemas.py tests/unit/test_reward.py -q`
- `PATH=.venv/bin:$PATH repo-harness build-v3-reward-diagnostics --run-dir runs/v3-stage-09-context-diagnostics-20260502T223000Z/context_runs/v3_stage_09_context_long_output --context-report runs/v3-stage-09-context-diagnostics-20260502T223000Z/context_compaction_report.json --long-rollout-report runs/v3-stage-09-context-diagnostics-20260502T223000Z/long_rollout_diagnostics.json --output-dir runs/v3-stage-10-failure-diagnostics-20260502T234500Z`
- `PATH=.venv/bin:$PATH repo-harness inspect-reward-diagnostics runs/v3-stage-10-failure-diagnostics-20260502T234500Z --core-report runs/v3-stage-10-failure-diagnostics-20260502T234500Z/failure_diagnostics_core_report.json --distribution-report runs/v3-stage-10-failure-diagnostics-20260502T234500Z/failure_distribution_report.json --assert-core-complete`
- `rg -n "reward_metadata|run_outcome|final_reward|hidden_failure_diagnostics|/Users/|/private/|gold_patch|test_patch|FAIL_TO_PASS|PASS_TO_PASS|official_report|official_harness|Authorization|api_key" runs/v3-stage-10-failure-diagnostics-20260502T234500Z/failure_diagnostics_core_report.json runs/v3-stage-10-failure-diagnostics-20260502T234500Z/failure_distribution_report.json`
- `PATH=.venv/bin:$PATH python -m pytest -q`
- `PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete`

## Validation Results

- `compileall src` passed.
- Stage 10 focused tests plus schema and reward regression tests passed: `15 passed`.
- Stage 10 unit tests passed after the report-key redaction adjustment: `3 passed`.
- `inspect-reward-diagnostics --assert-core-complete` passed.
- Denylist-oriented `rg` scan returned no matches for the Stage 10 core and distribution reports.
- Full repository tests passed after the final report-key redaction adjustment: `430 passed in 174.57s`.
- V2 acceptance regression passed: report status `passed`, task count `20`, mock provider `accepted`, real provider `accepted_with_credentials`.

## Positive Evidence

- `failure_diagnostics_core_report.json` recorded `patch_size=0`, `files_changed=[]`, `tool_call_count=2`, `test_run_count=0`, `invalid_tool_call_count=0`, `no_patch_generated=true`, `deterministic_verifier_failure=true` and `no_progress_detected=true` for the Stage 9 diagnostic run.
- `failure_distribution_report.json` contains all ten required core categories and counts verifier and deterministic verifier failure as `1`.
- Inspect re-reads ArtifactRefs, rejects paths that leave the Stage 10 directory, and validates sha256 and size.
- The negative unit test mutates a source `ArtifactRef.sha256`; inspect rejects it.
- `command_log.jsonl` binds the Stage 9 input run, context report, long rollout report and Stage 10 outputs with sha256.

## Negative Evidence

- Initial builder attempt failed because source report refs used inconsistent keys for `metrics.json` and `verifier.json`. Fixed by using explicit `metrics_file_ref`, `verifier_file_ref`, `baseline_file_ref`, `events_file_ref` and `final_patch_file_ref`.
- Self-review found that raw `CoreFailureDiagnostics.model_dump()` would write internal protection keys containing `reward_metadata` and `run_outcome`. Fixed by excluding those fields from the report payload while keeping schema validation defaults in inspect.

## Allowed Degradations

- Penalty weights, reward hacking deep analysis and complex distribution statistics remain deferred enhancements.
- The Stage 10 machine artifact uses the Stage 9 diagnostic run as input. That run is allowed to fail the final verifier because Stage 10 is auditing failure taxonomy, not proving task success.

## Prohibited Degradations

- Summary-only inspection is not allowed; ArtifactRefs must be re-read and sha256-checked.
- Failure distribution must include all required categories even when a category count is zero.
- Reports must not be used as model-visible context or formal training payload.
- Report generation must not read a default latest run or environment variable; inputs are explicit paths.

## Known Limits

- Stage 10 does not yet connect these reports to export audit eligibility. Stage 11 owns that integration.
- Stage 10 does not compute penalty weights or reward hacking suspicion beyond documenting them as deferred enhancements.
- Docker-specific failure categories are present and counted, but the Stage 10 sample run itself is the Stage 9 local diagnostic run.

## Design Deviation

No intentional deviation from `docs/v3/implementation-plan.md`. The build command name uses `reward-diagnostics` to match the required inspect command terminology, but the implementation is limited to core failure diagnostics and filtering evidence.

## Review Conclusion

Subagent review was attempted but failed with `agent thread limit reached`. An equivalent independent read-only self-review is saved in `docs/v3/review/implementation/stage-10-review.md`.

Stage 10 is allowed to proceed to Stage 11 after full-test and V2 regression verification pass.
