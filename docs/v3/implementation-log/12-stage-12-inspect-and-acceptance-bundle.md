# V3 Stage 12 Implementation Log: Inspect Commands And Acceptance Bundle

## Goal

实现第三版最终验收前的显式输入绑定、只读检查命令和 acceptance bundle 构建能力。阶段 12 不生成最终第十三阶段验收结论，不编写 `docs/v3/final-acceptance.md` 或 `docs/v3/walkthrough.md`，也不允许从 latest run、当前目录或未声明的 experiment directory 推断输入。

## Implementation Summary

- 扩展 `src/repo_harness/v3_acceptance.py`，从 schema 骨架扩展为完整的 Stage 12 acceptance 输入、报告和 bundle 构建检查模块。
- 新增 `inspect-trajectory-store RUN_DIR --assert-readable`，检查 `transcript.jsonl`、`events.jsonl`、`artifacts.json`、`run_config_facts.json`、ArtifactRef sha256/size、模型可见 transcript 污染和 terminal run metadata。
- 新增 `inspect-tool-contract RUN_DIR --assert-frozen`，检查 tool schema snapshot、tool protocol、permission/context/policy facts，并把缺省 hook/MCP 状态明确解释为 V3 core disabled/inferred facts。
- 新增 `build-v3-run-selection-manifest`，只接受显式 `--run-ref role=...,path=...`，记录 typed run refs、路径哈希、role、provider、workspace backend、source hash、状态和 evidence refs。
- 新增 `build-v3-acceptance-inputs`，显式绑定 run selection manifest、export root、V2 report、pre-acceptance 文档、pre-acceptance documentation manifest、command log 和 test evidence。
- 新增 `build-v3-acceptance-report`，要求 `ACCEPTANCE_DIR` 是不存在的新目录，复制并绑定 acceptance inputs、run selection manifest、contamination scan 和 `acceptance_command_log.jsonl`，生成 `v3_acceptance_report.json`。
- 新增 `inspect-v3-acceptance REPORT --assert-complete`，重新读取 report、input manifest、run selection manifest、command log 和 contamination scan refs，复算 sha256，不信任 summary。
- 新增 `build-v3-acceptance-bundle` 和 `inspect-acceptance-bundle --assert-immutable`，绑定 post-acceptance documentation refs，并复算 report、inputs、command log 和文档 sha256。
- `inspect-v3-acceptance --assert-complete` 现在会调用 V2 acceptance report 复查逻辑，不能只绑定伪造的 `{"status":"passed"}` 文件。
- `CommandLogEntry` 增加 `self_referential_output_paths` 和 `self_referential_output_reason`。由于 `v3_acceptance_report.json` 引用 `acceptance_command_log.jsonl`，同一 command log 无法同时存储 report 文件 sha256 而不形成哈希循环；因此自引用输出路径和原因被结构化记录，最终 report 文件由 inspect 和 bundle refs 复查。
- run selection success gate 不只信 manifest 字段。它会从 `path_ref` 和所有 `evidence_refs` 绑定的 JSON 文件中回读真实 `status`、`run_outcome`、`final_verifier_status`、`task_success` 等状态；绑定 evidence 出现 failed/error/timeout/rejected 等失败状态时，`accepted=true` 不能覆盖失败。
- credential-gated real provider role 不只信 manifest 顶层 provider 字段。它会从 `path_ref` 和所有 `evidence_refs` 的 JSON 文件中回读 `provider`、`actual_provider` 和 `requested_provider`，并拒绝 replay/mock evidence 混入真实 provider 或 structured skip role。

## Main Files

- `src/repo_harness/v3_acceptance.py`
- `src/repo_harness/cli/main.py`
- `tests/integration/test_v3_acceptance_stage12.py`

## Machine Artifacts

Primary Stage 12 validation artifact directory:

- `runs/v3-stage-12-acceptance-inspect-20260503T031753Z/`

Key files:

- `runs/v3-stage-12-acceptance-inspect-20260503T031753Z/run_selection_manifest.json`
- `runs/v3-stage-12-acceptance-inspect-20260503T031753Z/v3_acceptance_inputs.json`
- `runs/v3-stage-12-acceptance-inspect-20260503T031753Z/pre_acceptance_command_log.jsonl`
- `runs/v3-stage-12-acceptance-inspect-20260503T031753Z/pre_acceptance_documentation_manifest.json`
- `runs/v3-stage-12-acceptance-inspect-20260503T031753Z/pre_acceptance_evidence/stage12_focused_tests.json`
- `runs/v3-stage-12-acceptance-inspect-20260503T031753Z/acceptance/v3_acceptance_report.json`
- `runs/v3-stage-12-acceptance-inspect-20260503T031753Z/acceptance/acceptance_command_log.jsonl`
- `runs/v3-stage-12-acceptance-inspect-20260503T031753Z/acceptance/acceptance_inputs_manifest.json`
- `runs/v3-stage-12-acceptance-inspect-20260503T031753Z/acceptance/run_selection_manifest.json`
- `runs/v3-stage-12-acceptance-inspect-20260503T031753Z/acceptance/contamination_scan_results.json`
- `runs/v3-stage-12-acceptance-inspect-20260503T031753Z/acceptance/acceptance_bundle_manifest.json`

The Stage 12 bundle uses placeholder post-acceptance docs under `runs/v3-stage-12-acceptance-inspect-20260503T031753Z/post_acceptance_docs/` only to exercise the builder. Stage 13 must create the real `docs/v3/final-acceptance.md` and `docs/v3/walkthrough.md`.

## Validation Commands

- `PATH=.venv/bin:$PATH python -m compileall src`
- `PATH=.venv/bin:$PATH python -m pytest tests/integration/test_v3_acceptance_stage12.py -q`
- `PATH=.venv/bin:$PATH python -m pytest tests/integration/test_v3_acceptance_stage12.py tests/integration/test_v3_export_audit.py tests/unit/test_v3_schemas.py -q`
- `PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete`
- `PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-stage-12-acceptance-inspect-20260503T031753Z/acceptance/v3_acceptance_report.json --assert-complete`
- `PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-stage-12-acceptance-inspect-20260503T031753Z/acceptance/acceptance_bundle_manifest.json --assert-immutable`
- `PATH=.venv/bin:$PATH python -m pytest -q`

## Validation Results

- `compileall src` passed.
- Stage 12 focused tests passed: `10 passed in 1.77s`.
- Stage 12 plus adjacent export/schema regression tests passed: `24 passed in 21.43s`.
- `inspect-v2-acceptance --assert-complete` passed for `runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json`.
- `inspect-v3-acceptance --assert-complete` passed for `runs/v3-stage-12-acceptance-inspect-20260503T031753Z/acceptance/v3_acceptance_report.json`.
- `inspect-acceptance-bundle --assert-immutable` passed for `runs/v3-stage-12-acceptance-inspect-20260503T031753Z/acceptance/acceptance_bundle_manifest.json`.
- Final full repository tests after all Stage 12 fixes passed: `447 passed in 198.71s`.

## Positive Evidence

- `v3_acceptance_report.json` status is `passed`, failures are empty, and checks include explicit acceptance input binding, fresh acceptance directory enforcement, run selection manifest binding, command log binding and contamination scans.
- `acceptance_command_log.jsonl` records the build command, input manifest ref and the self-referential report output path with a structured reason.
- `run_selection_manifest.json` binds `credential_gated_real_provider` to accepted DeepSeek evidence, `mock_provider` to mock provider evidence, and `swebench_like` to a successful accepted run for Stage 12 validation.
- `inspect-v3-acceptance --assert-complete` re-runs V2 report inspection and rejects fake V2 reports.
- `inspect-acceptance-bundle --assert-immutable` detects post-acceptance documentation changes by sha256.

## Negative Evidence And Fixes

- Summary/report tampering is covered by sha256 mismatch tests.
- Evidence ref deletion and missing transcript/events/artifacts are covered by trajectory store negative tests.
- ArtifactRef sha256 mismatch is covered by mutating a tool schema snapshot artifact.
- ToolContractSnapshot/tool schema snapshot missing is covered by deleting `tool_schema_snapshot_ref`.
- Official harness report injection and prompt pollution are covered by acceptance input contamination tests.
- Checkpoint/context compaction report pollution is covered by injecting `reward_metadata` and `final_verifier_hidden_result`.
- Reusing an existing `ACCEPTANCE_DIR` is rejected by `build-v3-acceptance-report`.
- `ACCEPTANCE_INPUTS` missing required categories is rejected by `inspect-v3-acceptance --assert-complete`.
- Command log mismatch is rejected when `acceptance_command_log.jsonl` changes after report generation.
- Documentation ref changes after bundle generation are rejected by `inspect-acceptance-bundle --assert-immutable`.
- Credential-gated real provider skip disguised as accepted is rejected.
- Credential-gated real provider role cannot be replaced by replay/mock evidence, including when replay/mock provider identity is hidden inside `path_ref` or inside an `evidence_refs` value with a neutral key.
- Required success roles cannot use failed runs, and `accepted=true` cannot override failed status from manifest fields or from bound run/report evidence.
- Fake V2 acceptance reports are rejected because Stage 12 inspect calls V2 acceptance inspection in assert-complete mode.

## Allowed Degradations

- Stage 12 machine artifacts use placeholder post-acceptance documentation for bundle-builder validation only. This is allowed because real final acceptance documentation is a Stage 13 post-report artifact.
- The Stage 12 validation `swebench_like` role uses an accepted replay run from Stage 11 preference inputs as a command-level acceptance inspector fixture. Stage 13 must select the final acceptance run set explicitly according to the implementation plan and cannot reuse this as final SWE-Bench-like acceptance evidence unless it meets Stage 13 run-selection requirements.

## Prohibited Degradations

- Acceptance builders and inspectors must not read latest run directories or infer inputs from the current working directory.
- `ACCEPTANCE_DIR` must be fresh and must not overwrite old evidence.
- V2 acceptance evidence must be machine-rechecked, not merely sha256-bound.
- Command logs must be schema-checked and must bind command inputs/outputs or explicitly explain self-referential output paths.
- Real provider role cannot be satisfied by replay/mock evidence.
- Failed run evidence cannot be hidden behind a manifest that claims success.
- Post-acceptance documentation cannot drift after bundle generation.

## Known Limits

- Stage 12 implements the acceptance machinery and tests it with a validation artifact. Stage 13 must run final pre-acceptance tests, build the final run selection manifest, final acceptance inputs, final report, final documentation and final bundle.
- The Stage 12 validation artifact is under ignored `runs/` and is not version-controlled; the implementation and tests are version-controlled. Stage 13 must bind final evidence into the final acceptance bundle.
- The self-referential report output cannot be represented as a normal `output_ref` in the same command log without a hash cycle. It is represented by `self_referential_output_paths` and verified through report and bundle ArtifactRefs.

## Design Deviation

No intentional deviation from `docs/v3/implementation-plan.md`. Stage 12 deliberately stops before final Stage 13 acceptance documentation and final acceptance run selection.

## Review Conclusion

Stage 12 required several read-only review rounds because the acceptance inspector is a high-leverage gate. Helmholtz, Goodall, Rawls and Darwin found P1/P2 bypasses in early implementations. Each P1/P2 was fixed before proceeding.

The final read-only review by Locke found no P1, P2 or P3 findings. Locke specifically confirmed that bound failed run evidence cannot be disguised as accepted/success in the manifest, and replay/mock provider identity cannot be hidden under neutral `evidence_refs` keys.

Stage 12 is allowed to proceed to Stage 13 after focused tests, full repository tests, V2 regression, V3 acceptance inspect and acceptance bundle inspect all passed.
