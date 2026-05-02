# V3 Stage 9 Read-Only Review: Context Compaction And Long Rollout Diagnostics

## Review Method

The requested subagent review was attempted, but the environment returned `agent thread limit reached`. I performed an equivalent independent read-only self-review.

Review dimensions:

- Whether compaction is triggered by a real Agent Loop tool observation rather than a hand-written report.
- Whether `context_compaction_report.json` rebinds `prepared_messages_ref`, sha256, `model_input_hash`, `context_revision`, content replacement state and observation source events.
- Whether `observation_matches_prepared_messages=true` is proven by re-reading prepared messages artifacts.
- Whether tool call / tool result pairing stays complete after replacement.
- Whether long rollout diagnostics are independent and contain repeated tool call, no progress or context limit evidence.
- Whether reports avoid V3 denylist terms and host absolute paths.
- Whether negative tests detect sha256 drift.

## Findings

### P1

No P1 findings.

### P2: Long output did not execute because bash here-doc was denied

Initial Stage 9 tests produced no compaction events. Root cause investigation showed the replay used a bash here-doc, and the permission layer denied the `<` shell fragment before any long output was produced.

Fix:

- Removed the here-doc path.
- Re-ran the focused Stage 9 tests.

Status: fixed, but this led to the next P2.

### P2: `python -c` through bash was outside the bash allowlist

After removing here-doc syntax, the run still produced only short denied tool results. Root cause investigation showed model-visible bash only permits a restricted diagnostic allowlist and rejects `python` as a bash command.

Fix:

- Generate a repository-local `long_context.txt` file inside a generated local repository source.
- Use normal `read_file` tool calls to produce long observations.
- Keep the generated task source as `repo_source_spec.source_type=local_repository`, so it does not depend on fixture-only task path resolution.

Status: fixed.

### P3: Diagnostic run final verifier fails

The Stage 9 run intentionally reads a long file twice and does not patch `calculator.py`; final verifier therefore fails. This is acceptable for Stage 9 because the stage proves context compaction and long rollout diagnostics, not task solving.

Status: accepted within phase scope.

## Verification Evidence

- `PATH=.venv/bin:$PATH python -m compileall src`: passed.
- `PATH=.venv/bin:$PATH python -m pytest tests/integration/test_context_compaction_v3.py -q`: `3 passed`.
- `PATH=.venv/bin:$PATH python -m pytest tests/integration/test_context_compaction_v3.py tests/unit/test_context_manager.py tests/unit/test_agent_loop_protocol.py tests/unit/test_v3_visibility_policy.py -q`: `27 passed`.
- `PATH=.venv/bin:$PATH repo-harness build-v3-context-diagnostics --output-dir runs/v3-stage-09-context-diagnostics-20260502T223000Z`: passed.
- `PATH=.venv/bin:$PATH repo-harness inspect-context-report runs/v3-stage-09-context-diagnostics-20260502T223000Z --report runs/v3-stage-09-context-diagnostics-20260502T223000Z/context_compaction_report.json --assert-consistent`: passed.
- `PATH=.venv/bin:$PATH repo-harness inspect-long-rollout-diagnostics runs/v3-stage-09-context-diagnostics-20260502T223000Z --report runs/v3-stage-09-context-diagnostics-20260502T223000Z/long_rollout_diagnostics.json --assert-complete`: passed.
- `PATH=.venv/bin:$PATH repo-harness inspect-run runs/v3-stage-09-context-diagnostics-20260502T223000Z/context_runs/v3_stage_09_context_long_output`: passed as a readable failed diagnostic run.
- `PATH=.venv/bin:$PATH python -m pytest -q`: `427 passed in 178.60s`.
- `PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete`: passed, report status `passed`.

## Boundary Checks

- Report scan found no `/Users/`, `/private/`, `gold_patch`, `test_patch`, `FAIL_TO_PASS`, `PASS_TO_PASS`, provider raw, credential, reward metadata, run outcome or hidden verifier result markers in Stage 9 reports.
- The prepared messages sha256, model input hash and context revision were independently re-read from artifact files and matched report values.
- `tool_pairing_validation.ok=true` for context revisions that performed replacement.
- `long_rollout_diagnostics.json` reports `repeated_tool_call` and `no_progress`; it is not used as substitute evidence for compaction.
- Negative test mutates `prepared_messages_sha256` and inspect rejects the report.

## Residual Risk

- Stage 9 does not yet enforce export eligibility for compaction-aware training samples. Stage 11 owns export audit.
- Stage 9 does not produce the core failure diagnostics taxonomy. Stage 10 owns that scope.
- Stage 9 does not implement semantic summarization or arbitrary session memory.

## Decision

No remaining P1 or P2 findings. P3 is documented and within phase scope. Full-test and V2 regression verification passed, so Stage 9 may proceed to Stage 10.
