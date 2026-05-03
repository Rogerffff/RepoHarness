# V3 Stage 11 Read-Only Review: Export Audit And Preference Baseline

## Review Method

Two read-only subagent reviews were used.

The first review was performed by Nash after the initial implementation. Nash was asked to check V2 export compatibility, V3 contamination scanning, preference compare scope, observation binding, run artifact redaction audit, inspect bypass risks and negative coverage.

The second review was performed by Carver after fixes. Carver was asked to re-check the exact earlier findings and the final machine artifact `runs/v3-stage-11-export-audit-20260503T030000Z`.

Neither subagent modified files.

## Initial Findings

### P1: V3 fields were added to the V2 strict compare scope

Nash found that `docker_backend`, `source_tree_hash`, `verifier_plan_ref` and other V3 fields were directly added to `STRICT_COMPARE_FIELDS`, which would change the second version preference export contract.

Fix:

- Restored `STRICT_COMPARE_FIELDS` to the V2 field set.
- Added V3 fields as `V3_COMPARE_SCOPE_FIELDS` in `src/repo_harness/v3_export_audit.py`.
- Wrote a Stage 11 explicit `v3_preference_compare_scope.json` and passed it to `export_preference_jsonl`.
- Added a regression test proving `CompareScope(canonical_key_fields=list(STRICT_COMPARE_FIELDS))` remains valid without V3 fields.

Status: fixed.

### P1: Observation binding audit only checked field presence

Nash found that the first version of `_v3_binding_error` only checked required fields and trusted `observation_matches_prepared_messages=true`.

Fix:

- `audit_export_records` now passes source run paths into the prepared observation audit.
- The audit re-reads `prepared_messages_ref`, recomputes sha256, validates `prepared_messages_sha256`, compares `model_input_hash`, `context_revision`, `content_replacement_state_ref`, `tool_call_id`, observation content, `tool_observation_ref`, and terminal `observation_source_event_ref`.
- Added a negative test that tampers `prepared_messages_sha256` and verifies the sample becomes invalid.

Status: fixed.

### P2: V3 contamination scan boundaries were too narrow

Nash found that preference metadata, quality, compare scope and audit evidence were not sufficiently scanned, and formal payloads were all reported as `rl_export`.

Fix:

- Split formal training payload scans by surface: `sft_export`, `rl_export`, and `preference_export`.
- Added safe projections for metadata and quality.
- Added safe projections for format export manifests and audit reports under `acceptance_input`.
- Kept audit-only reward/outcome fields out of training projections while still allowing structural metadata to be scanned.

Status: fixed.

### P2: Run artifact redaction audit only looked at artifact manifest labels

Nash found that the initial redaction audit mostly counted raw provider artifact refs and did not scan file contents.

Fix:

- Added content scanning for `events.jsonl`, `artifacts.json`, `transcript.jsonl`, `run_metadata.json`, `run_config_facts.json`, prepared messages, raw replay request/response and raw provider artifacts.
- The final Stage 11 artifact reports `content_scan_file_count=56` and `content_scan_failure_count=0`.

Status: fixed.

### P2: Inspect could use an audit report not bound by the manifest

Nash found that `inspect-v3-export-audit` validated `audit_report_ref` but read the command-line report path separately.

Fix:

- Added `_inspect_manifest_bound_audit_report` to require the command-line `--audit-report` path to equal manifest `audit_report_ref.relative_path`.
- Added a negative test with `alternate_audit_report.json`.

Status: fixed.

## Final Review Findings

Carver re-reviewed the fixed implementation and final Stage 11 artifact.

### P1

No P1 findings.

### P2

No P2 findings.

### P3

No P3 findings.

## Verification Evidence

- `PATH=.venv/bin:$PATH python -m compileall src`: passed.
- `PATH=.venv/bin:$PATH python -m pytest tests/integration/test_v3_export_audit.py tests/integration/test_export_from_run.py tests/unit/test_export.py tests/unit/test_context_builder.py -q`: `30 passed in 30.32s`.
- `PATH=.venv/bin:$PATH repo-harness inspect-v3-export-audit runs/v3-stage-11-export-audit-20260503T030000Z --manifest runs/v3-stage-11-export-audit-20260503T030000Z/export_manifest.json --audit-report runs/v3-stage-11-export-audit-20260503T030000Z/audit_report.json --assert-clean`: passed.
- `PATH=.venv/bin:$PATH python -m pytest -q`: `437 passed in 200.45s`.
- `PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete`: passed.

Carver additionally ran a read-only inspect using `uv run repo-harness inspect-v3-export-audit ... --assert-clean`; it passed.

## Boundary Checks

- V2 `STRICT_COMPARE_FIELDS` remains independent from V3 fields.
- Stage 11 V3 preference compare scope is manifest-bound by `v3_preference_compare_scope_ref`.
- Formal JSONL is checked so non-trainable, skipped or invalid samples cannot appear in data files.
- `prepared_messages_ref` and `prepared_messages_sha256` are not trusted without recomputation.
- Manifest, audit report, preference baseline report and format export data files are bound by ArtifactRefs and sha256.
- Run artifact content scanning covers raw replay artifacts as well as raw provider artifact labels.
- Acceptance bundle redaction remains Stage 12/13 responsibility and is not replaced by Stage 11 export audit.

## Residual Risk

- The final Stage 11 root report is `passed_with_warnings` rather than plain `passed` because the failed SWE-Bench-like Agent Loop run produced invalid SFT/RL records. This is not a blocker because those records are filtered out of formal JSONL and explicitly counted as invalid.
- Stage 12 still needs to bind this Stage 11 evidence into acceptance inputs and re-check immutability.

## Decision

No remaining P1, P2 or P3 findings. Stage 11 may proceed to Stage 12.
