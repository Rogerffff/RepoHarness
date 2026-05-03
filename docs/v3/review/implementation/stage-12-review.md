# V3 Stage 12 Read-Only Review: Inspect Commands And Acceptance Bundle

## Review Method

Stage 12 used multiple read-only subagent reviews because acceptance inspection is the gate that later prevents false final acceptance.

Subagents used:

- Helmholtz reviewed the initial Stage 12 implementation and machine artifact.
- Goodall reviewed the first fix set.
- Rawls reviewed the second fix set.
- Darwin reviewed the third fix set.
- Locke reviewed the final fix set.

No subagent modified files.

## Initial Findings From Helmholtz

### P1: credential-gated real provider could be replaced by replay evidence

Helmholtz found that `credential_gated_real_provider` only rejected a skip that was also marked accepted. A replay run could occupy the role with `run_state=success` and no skip reason.

Fix:

- `inspect-v3-acceptance --assert-complete` now requires `credential_gated_real_provider` to be either real provider evidence (`deepseek` or `openai`) with accepted/success status, or a structured skip without accepted/success state.
- Added provider role checks for mock and replay roles.
- Regenerated Stage 12 machine artifact with DeepSeek accepted-with-credentials evidence for the credential-gated role.

Status: fixed.

### P1: required run roles did not require success

Helmholtz found that a failed SWE-Bench-like run could still pass Stage 12 acceptance because the inspector only checked trajectory readability and tool contract freezing.

Fix:

- Added success gates for replay, mock provider, credential-gated real provider, real repository and SWE-Bench-like roles.
- Added negative tests for failed success-required roles.

Status: fixed.

### P2: V2 report was only hash-bound

Helmholtz found that a fake `{"status":"passed"}` V2 report could be accepted because Stage 12 only checked file sha256.

Fix:

- `inspect-v3-acceptance --assert-complete` now calls `inspect_v2_acceptance(..., assert_complete=True)` for the bound V2 report.
- Added a fake V2 report negative test.

Status: fixed.

### P2: acceptance command log did not record the main report output

Helmholtz found that the command log listed copied inputs and contamination scan output, but not `v3_acceptance_report.json`.

Fix:

- Added `self_referential_output_paths` and `self_referential_output_reason` to `CommandLogEntry`.
- `build-v3-acceptance-report` records the report output path as self-referential and explains the hash cycle.
- `inspect-v3-acceptance` requires a self-referential output path for the report build entry.

Status: fixed.

## Follow-Up Findings From Goodall

### P1: accepted=true could override failed status

Goodall found that `_entry_is_success()` initially returned true for `accepted=true` even when manifest status fields said failed.

Fix:

- `_entry_is_success()` now rejects explicit failure states before considering accepted/success states.
- Added a negative test with `accepted=true` plus failed manifest fields.

Status: fixed.

### P2: credential-gated skip could still carry replay provider fields

Goodall found that structured skip could include replay provider fields and still pass.

Fix:

- Structured credential-gated skip now rejects replay/mock provider identity.
- Added a negative test for replay identity on credential-gated skip.

Status: fixed.

## Follow-Up Findings From Rawls

### P1: credential-gated skip could hide replay evidence by deleting provider fields

Rawls found that manifest provider fields could be deleted while `path_ref` and `evidence_refs` still pointed at replay evidence.

Fix:

- Provider identity is now read from the bound `path_ref` target and evidence refs, not only from top-level manifest fields.
- `_provider_values_from_path()` reads `run_config_facts.json`, `run_metadata.json`, provider smoke reports and report JSON.
- Added a negative test that copies replay `path_ref` and `evidence_refs` into credential-gated skip while removing provider fields.

Status: fixed.

## Follow-Up Findings From Darwin

### P1: manifest could disguise a bound failed run as accepted

Darwin found that success checks still trusted manifest status fields and did not re-read bound run files for status.

Fix:

- `_entry_is_success()` now calls `_bound_status_values()` and reads status from `path_ref` and every evidence ref.
- Bound `failed`, `error`, `timeout`, `rejected`, `invalid_task`, `flaky_task` or `inconclusive` evidence blocks success even if the manifest claims `accepted=true`.
- Added a negative test where the manifest claims a bound real provider run succeeded while the bound files show failure.

Status: fixed.

### P2: neutral evidence ref keys could hide provider identity

Darwin found that provider identity extraction depended on evidence ref key names containing `run_config_facts` or `provider`.

Fix:

- Provider identity is now extracted from every JSON evidence ref value, independent of key name.
- Added a negative test where replay `run_config_facts.json` is hidden under a neutral key named `smoke_report`.

Status: fixed.

## Final Review From Locke

Locke reviewed the final implementation and tests.

### P1

No P1 findings.

### P2

No P2 findings.

### P3

No P3 findings.

Locke confirmed:

- `_entry_is_success()` reads `path_ref` and all `evidence_refs` binding files, and failed bound evidence cannot be hidden behind manifest `accepted/success`.
- Provider identity checks iterate through all `evidence_refs` values, so replay/mock identity cannot be hidden under neutral key names.
- `tests/integration/test_v3_acceptance_stage12.py` contains regression tests for both bypasses.

## Verification Evidence

- `PATH=.venv/bin:$PATH python -m compileall src`: passed.
- `PATH=.venv/bin:$PATH python -m pytest tests/integration/test_v3_acceptance_stage12.py -q`: `10 passed in 1.77s`.
- `PATH=.venv/bin:$PATH python -m pytest tests/integration/test_v3_acceptance_stage12.py tests/integration/test_v3_export_audit.py tests/unit/test_v3_schemas.py -q`: `24 passed in 21.43s`.
- `PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete`: passed.
- `PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-stage-12-acceptance-inspect-20260503T031753Z/acceptance/v3_acceptance_report.json --assert-complete`: passed.
- `PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-stage-12-acceptance-inspect-20260503T031753Z/acceptance/acceptance_bundle_manifest.json --assert-immutable`: passed.
- `PATH=.venv/bin:$PATH python -m pytest -q`: `447 passed in 198.71s`.

## Boundary Checks

- CLI builders require explicit paths and do not scan latest runs.
- `ACCEPTANCE_DIR` reuse is rejected.
- V2 acceptance is machine-rechecked, not just hash-bound.
- Pre-acceptance command logs and acceptance command logs are schema-checked as `CommandLogEntry`.
- Bundle inspection recomputes post-acceptance documentation sha256.
- Prompt, official harness report, checkpoint and context report pollution are rejected in negative tests.
- `ArtifactRef` sha256 drift and missing trajectory/tool contract evidence are rejected in negative tests.

## Residual Risk

- Stage 12 validation artifacts are not the final Stage 13 acceptance bundle. Stage 13 must rebuild final acceptance inputs from final pre-acceptance evidence and final selected runs.
- The self-referential report output path is intentionally not hashed inside the same command log to avoid a hash cycle; it is verified by report and bundle refs.

## Decision

No remaining P1, P2 or P3 findings after final Locke review. Stage 12 may proceed to Stage 13.
