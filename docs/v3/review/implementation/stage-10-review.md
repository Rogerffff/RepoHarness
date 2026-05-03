# V3 Stage 10 Read-Only Review: Core Failure Diagnostics And Reward Metadata

## Review Method

The requested subagent review was attempted, but the environment returned `agent thread limit reached`. I performed an equivalent independent read-only self-review.

Review dimensions:

- Whether Stage 10 stays inside `docs/v3/implementation-plan.md` scope and does not implement a new reward model.
- Whether `build-v3-reward-diagnostics` uses explicit input paths and does not guess latest runs.
- Whether `inspect-reward-diagnostics` reads both reports from explicit paths and validates `ArtifactRef` relative path, sha256 and size.
- Whether the core report includes all required fields.
- Whether the distribution report includes provider, Docker backend, environment setup, verifier, permission, tool protocol, context limit, task quality, parser confidence and deterministic verifier failure.
- Whether audit-only diagnostics avoid model-visible leakage and formal training payload leakage.
- Whether negative tests cover evidence drift.

## Findings

### P1

No P1 findings.

### P2: Source evidence refs were named inconsistently

The first Stage 10 builder run failed before writing a complete report because `_source_file_refs()` produced keys derived from filenames, while diagnostic construction expected `metrics_file_ref` and `verifier_file_ref`.

Fix:

- Replaced filename-derived keys with explicit `metrics_file_ref`, `verifier_file_ref`, `baseline_file_ref`, `events_file_ref` and `final_patch_file_ref`.
- Re-ran the builder and `inspect-reward-diagnostics --assert-core-complete`.

Status: fixed.

### P2: Raw diagnostic dumps exposed forbidden key names for later acceptance scanning

Raw `CoreFailureDiagnostics.model_dump()` included internal guard fields named `reward_metadata_visible_to_model` and `run_outcome_visible_to_model`. Those fields were false and audit-only, but their literal key names could create avoidable risk when Stage 12 scans acceptance inputs.

Fix:

- Excluded the internal guard fields from `diagnostic_records` in the report payload.
- Kept `CoreFailureDiagnostics` schema validation in inspect; missing guard fields validate with safe defaults.
- Ran an `rg` scan against the final Stage 10 core and distribution reports for forbidden markers, including `reward_metadata`, `run_outcome`, `final_reward`, host paths, gold/test patch terms, official report terms and credential markers. The scan returned no matches.

Status: fixed.

### P3: Stage 10 sample is local diagnostic evidence, not Docker failure coverage

The Stage 10 sample reuses the Stage 9 long-output diagnostic run, so Docker-specific categories are present with zero counts rather than exercised by a Docker failure sample.

Status: acceptable within Stage 10 scope. Docker backend and Docker phase coverage are owned by earlier Docker stages and will be bound again during final acceptance.

## Verification Evidence

- `PATH=.venv/bin:$PATH python -m compileall src`: passed.
- `PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v3_failure_diagnostics.py tests/unit/test_v3_schemas.py tests/unit/test_reward.py -q`: `15 passed`.
- `PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v3_failure_diagnostics.py -q`: `3 passed` after the report-key redaction adjustment.
- `PATH=.venv/bin:$PATH repo-harness build-v3-reward-diagnostics --run-dir runs/v3-stage-09-context-diagnostics-20260502T223000Z/context_runs/v3_stage_09_context_long_output --context-report runs/v3-stage-09-context-diagnostics-20260502T223000Z/context_compaction_report.json --long-rollout-report runs/v3-stage-09-context-diagnostics-20260502T223000Z/long_rollout_diagnostics.json --output-dir runs/v3-stage-10-failure-diagnostics-20260502T234500Z`: passed.
- `PATH=.venv/bin:$PATH repo-harness inspect-reward-diagnostics runs/v3-stage-10-failure-diagnostics-20260502T234500Z --core-report runs/v3-stage-10-failure-diagnostics-20260502T234500Z/failure_diagnostics_core_report.json --distribution-report runs/v3-stage-10-failure-diagnostics-20260502T234500Z/failure_distribution_report.json --assert-core-complete`: passed.
- Denylist-oriented `rg` scan on Stage 10 reports returned no matches.
- `PATH=.venv/bin:$PATH python -m pytest -q`: `430 passed in 174.57s` after the final report-key redaction adjustment.
- `PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete`: passed, report status `passed`.

## Boundary Checks

- `inspect-reward-diagnostics` requires explicit `run_dir`, `--core-report` and `--distribution-report`.
- The inspect command rejects absolute paths or `..` segments in report ArtifactRefs.
- The inspect command recomputes sha256 for referenced files and source directory trees.
- The inspect command checks all required core fields and all required distribution categories.
- The builder writes `command_log.jsonl` with input and output refs, sha256, exit code and CLI version.
- Reports are filtering evidence only and are not inserted into prompt, transcript, prepared messages or export payloads by Stage 10.

## Residual Risk

- Stage 11 still needs to connect these diagnostics to export audit and skipped manifest decisions.
- Stage 12 still needs to bind Stage 10 reports into the final acceptance input mechanism and re-check immutability.
- Enhanced penalty weights and deep reward hacking analysis remain deferred enhancements.

## Decision

No remaining P1 or P2 findings. The P3 limitation is documented and within phase scope. Full-test and V2 regression verification passed, so Stage 10 may proceed to Stage 11.
