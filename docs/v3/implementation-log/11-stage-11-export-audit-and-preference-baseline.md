# V3 Stage 11 Implementation Log: Export Audit And Preference Baseline

## Goal

证明第三版训练导出仍然安全、可审计，并且继续继承第二版导出契约。阶段 11 不实现 acceptance bundle，不代替阶段 12/13 的最终验收扫描，也不把失败的 SWE-Bench-like run 伪装成可训练样本。

## Implementation Summary

- 新增 `build-v3-export-audit`，只接收显式 `--run-dir` 和可选 `--preference-runs-dir`，构建阶段 11 export audit 聚合目录。
- 新增 `inspect-v3-export-audit RUN_DIR --manifest RUN_DIR/export_manifest.json --audit-report RUN_DIR/audit_report.json --assert-clean`。
- 继续复用第二版 SFT、RL rollout 和 preference export，实现 format-specific export directories、`export_manifest.json`、`audit_report.json`、`audit_report.md`、样本级 audit items、training eligibility、skipped manifest 和数据文件 sha256。
- 保持第二版 `STRICT_COMPARE_FIELDS` 不变。V3 额外 compare scope 字段通过阶段 11 显式 `v3_preference_compare_scope.json` 绑定，不改变普通第二版 preference export 默认契约。
- 扩展 preference compare facts，新增 Docker backend、source tree hash、ToolContractSnapshot、permission policy snapshot、hook/MCP state、context revision、source materialization ref 和 verifier plan ref。
- 扩展 SFT/RL 正式训练样本，使每个 tool observation 绑定 `prepared_messages_ref`、`prepared_messages_sha256`、`model_input_hash`、`context_revision`、`content_replacement_state_ref`、`tool_observation_ref`、`observation_source_event_ref` 和 `observation_matches_prepared_messages`。
- 导出审计现在会反查 `prepared_messages_ref`，重新计算 sha256，核对 tool_call_id、tool observation 内容、terminal tool event 和 prepared messages artifact 的一致性。
- 初始 prompt 中的 `workspace_root` 改为 `<REDACTED_LOCAL_PATH>`，避免本机绝对路径进入模型可见 transcript 或 prepared messages。
- 新增 V3 污染扫描聚合：扫描模型可见 transcript、prepared messages、SFT/RL/preference 正式训练 payload 的安全投影、format export manifest 和 audit report 的安全投影。
- 新增 run artifact redaction/content audit，覆盖 `events.jsonl`、`artifacts.json`、`transcript.jsonl`、`run_metadata.json`、`run_config_facts.json`、prepared messages、raw replay request/response 和 raw provider artifact。
- 新增同条件 preference baseline replay 配置，生成一组可训练 chosen/rejected preference pair。
- `inspect-v3-export-audit` 绑定命令行传入的 `audit_report` 与 manifest 中 `audit_report_ref`，防止使用不一致的干净报告绕过检查。

## Main Files

- `src/repo_harness/v3_export_audit.py`
- `src/repo_harness/cli/main.py`
- `src/repo_harness/export/audit.py`
- `src/repo_harness/export/exporter.py`
- `src/repo_harness/export/pairing.py`
- `src/repo_harness/export/schemas.py`
- `src/repo_harness/context/builder.py`
- `tests/integration/test_v3_export_audit.py`
- `tests/unit/test_context_builder.py`
- `tests/fixtures/run_configs/v3/export_audit_success.yaml`
- `tests/fixtures/run_configs/v3/export_audit_failure.yaml`

## Machine Artifacts

Primary Stage 11 artifact directory:

- `runs/v3-stage-11-export-audit-20260503T030000Z/`

Key files:

- `runs/v3-stage-11-export-audit-20260503T030000Z/export_manifest.json`
- `runs/v3-stage-11-export-audit-20260503T030000Z/audit_report.json`
- `runs/v3-stage-11-export-audit-20260503T030000Z/audit_report.md`
- `runs/v3-stage-11-export-audit-20260503T030000Z/preference_pair_baseline_report.json`
- `runs/v3-stage-11-export-audit-20260503T030000Z/v3_preference_compare_scope.json`
- `runs/v3-stage-11-export-audit-20260503T030000Z/command_log.jsonl`
- `runs/v3-stage-11-export-audit-20260503T030000Z/input_runs/format_exports/`
- `runs/v3-stage-11-export-audit-20260503T030000Z/input_runs/preference/`

Preference input runs:

- `runs/v3-stage-11-preference-inputs-20260503T023000Z/v3_stage_11_pref_success_public/`
- `runs/v3-stage-11-preference-inputs-20260503T023000Z/v3_stage_11_pref_failure_public/`

Format export input runs:

- `runs/v3-stage-07-agent-loop-20260502T203000Z/agent_loop_runs/v3_stage_07_realrepo_local_buggy_calculator/`
- `runs/v3-stage-07-agent-loop-20260502T203000Z/agent_loop_runs/v3_stage_07_pytest-dev__pytest-7220/`

## Validation Commands

- `PATH=.venv/bin:$PATH python -m compileall src`
- `PATH=.venv/bin:$PATH python -m pytest tests/integration/test_v3_export_audit.py tests/integration/test_export_from_run.py tests/unit/test_export.py tests/unit/test_context_builder.py -q`
- `PATH=.venv/bin:$PATH repo-harness run-task tests/fixtures/tasks/task_001.yaml --config tests/fixtures/run_configs/v3/export_audit_success.yaml --output-dir runs/v3-stage-11-preference-inputs-20260503T023000Z --run-id v3_stage_11_pref_success_public`
- `PATH=.venv/bin:$PATH repo-harness run-task tests/fixtures/tasks/task_001.yaml --config tests/fixtures/run_configs/v3/export_audit_failure.yaml --output-dir runs/v3-stage-11-preference-inputs-20260503T023000Z --run-id v3_stage_11_pref_failure_public`
- `PATH=.venv/bin:$PATH repo-harness build-v3-export-audit --run-dir runs/v3-stage-07-agent-loop-20260502T203000Z/agent_loop_runs/v3_stage_07_realrepo_local_buggy_calculator --run-dir runs/v3-stage-07-agent-loop-20260502T203000Z/agent_loop_runs/v3_stage_07_pytest-dev__pytest-7220 --output-dir runs/v3-stage-11-export-audit-20260503T030000Z --preference-runs-dir runs/v3-stage-11-preference-inputs-20260503T023000Z`
- `PATH=.venv/bin:$PATH repo-harness inspect-v3-export-audit runs/v3-stage-11-export-audit-20260503T030000Z --manifest runs/v3-stage-11-export-audit-20260503T030000Z/export_manifest.json --audit-report runs/v3-stage-11-export-audit-20260503T030000Z/audit_report.json --assert-clean`
- `PATH=.venv/bin:$PATH python -m pytest -q`
- `PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete`

## Validation Results

- `compileall src` passed.
- Focused Stage 11 and V2 export regression tests passed: `30 passed in 30.32s`.
- `inspect-v3-export-audit --assert-clean` passed for `runs/v3-stage-11-export-audit-20260503T030000Z`.
- Full repository tests passed: `437 passed in 200.45s`.
- V2 acceptance regression passed: report status `passed`, task count `20`, mock provider `accepted`, real provider `accepted_with_credentials`, export counts `sft_jsonl=6`, `rl_jsonl=6`, `preference_jsonl=5`.

## Positive Evidence

- `export_manifest.json` binds 5 format exports: SFT/RL for the real repository Agent Loop run, SFT/RL for the SWE-Bench-like Agent Loop run, and one preference export baseline.
- `preference_pair_baseline_report.json` records `eligible_pair_count=1`, `blocked_pair_count=0`, `residual_risk=null`, and one trainable pair: `v3_stage_11_pref_success_public` chosen over `v3_stage_11_pref_failure_public`.
- `v3_preference_compare_scope.json` contains all V2 strict fields plus V3 fields: Docker backend, source hash, ToolContractSnapshot, permission policy snapshot, hook/MCP states, context revision, source materialization and verifier plan refs.
- `sample_binding_summary` reports `binding_records_checked=6`, `missing_binding_count=0`, `mismatched_binding_count=0`, `observation_matches_prepared_messages=true`.
- `run_artifact_redaction_audit` reports `run_count=4`, `events_jsonl_covered=4`, `artifacts_json_covered=4`, `run_metadata_covered=4`, `run_config_facts_covered=4`, `content_scan_file_count=56`, `content_scan_failure_count=0`.
- Formal JSONL contains only trainable samples. The failed SWE-Bench-like Agent Loop run produced invalid SFT/RL records in audit reports, but those records are filtered out of formal training data.
- `inspect-v3-export-audit` re-reads ArtifactRefs, validates sha256 and size, rejects paths outside the Stage 11 directory, validates formal JSONL eligibility, checks V3 binding fields, checks preference compare scope coverage and binds `audit_report` to manifest `audit_report_ref`.

## Negative Evidence And Fixes

- Initial Stage 11 tests failed because `tool_observation_ref` was missing for event-only tool results. Fixed by using event-backed refs for tool observations without file artifacts.
- Initial RL export missed `context_revision` on trajectory observations. Fixed by propagating context revision from prepared messages.
- Initial V3 compare scope was added directly to `STRICT_COMPARE_FIELDS`, which would have broken V2 compare scope compatibility. Fixed by restoring V2 strict fields and writing explicit Stage 11 `v3_preference_compare_scope.json`.
- Initial observation binding audit only checked field presence. Fixed by re-reading prepared messages artifacts, recomputing sha256, and comparing tool_call_id, content, event and observation refs.
- Initial contamination scan did not cover preference metadata and audit evidence projections strongly enough. Fixed by scanning SFT/RL/preference payloads separately and scanning safe projections of metadata, quality, manifests and audit reports.
- Initial inspect could be called with a different clean `audit_report` than the one named in manifest. Fixed by requiring the command-line report path to match `audit_report_ref.relative_path`; a negative test covers this.
- Attempting to copy a SWE-Bench-like run with `.v3_verifier_venv` failed because the verifier virtual environment contained fragile symlinks. Fixed by excluding `.v3_verifier_venv` from Stage 11 copied audit inputs; verifier evidence remains referenced by the original stage evidence and is not needed for export construction.

## Allowed Degradations

- The root Stage 11 audit status is `passed_with_warnings` because `v3_stage_07_pytest-dev__pytest-7220` is a failed SWE-Bench-like Agent Loop run. Its SFT/RL records are invalid and filtered, which is allowed because Stage 11 requires non-trainable runs to be explicitly marked rather than silently exported.
- Acceptance bundle redaction and immutability scanning remain deferred to Stage 12/13, as required by the implementation plan.

## Prohibited Degradations

- V3 must not mutate the V2 default `STRICT_COMPARE_FIELDS`.
- Diagnostic-only, skipped or invalid samples must not enter formal training JSONL.
- Preference pairs must not be generated from mismatched compare scope fields.
- Raw provider/replay artifacts, credentials, host paths, reward metadata, run outcome and hidden verifier information must not enter model-visible context or formal training payload.
- `inspect-v3-export-audit` must not accept default/latest run directories or an audit report path that differs from manifest.

## Known Limits

- Stage 11 scans run artifacts and exports, but final acceptance report inputs and acceptance bundle are produced later and must be scanned again by Stage 12/13.
- Real provider export closure remains represented by V2 acceptance evidence at this stage; Stage 13 must bind provider-gated evidence into final acceptance inputs.
- `source_fact_count=0` in the Stage 11 run artifact audit because copied Agent Loop run directories do not store source facts as root `source*.json` files. Source materialization evidence is bound in earlier V3 stages and must be included again in final acceptance inputs.

## Design Deviation

No intentional deviation from `docs/v3/implementation-plan.md`. The root audit status allows `passed_with_warnings` when non-trainable records are explicitly filtered and formal JSONL remains clean; `inspect-v3-export-audit --assert-clean` still rejects structural failures, contamination failures, ArtifactRef drift, binding mismatches and unbound audit reports.

## Review Conclusion

Initial subagent review by Nash found two P1 issues and three P2 issues. All were fixed before final verification. A follow-up read-only subagent review by Carver found no P1, P2 or P3 findings and allowed proceeding to Stage 12.

Stage 11 is allowed to proceed to Stage 12 after full-test and V2 regression verification pass.
