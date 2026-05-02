# V3 Stage 8 Read-Only Review: Experiment Runner Resume

## Review Method

The requested subagent review was attempted, but the environment returned `agent thread limit reached`. I therefore performed an equivalent independent read-only self-review.

Review dimensions:

- `RunCheckpoint.run_metadata_ref` timing and interrupted run metadata boundary.
- Resume semantics for completed, pending and interrupted runs.
- Continuation run id behavior and original evidence preservation.
- Checkpoint and manifest ArtifactRef sha256 verification.
- V3 contamination denylist scan on checkpoint-visible surfaces.
- Command log evidence coverage.
- Run directory lock behavior.
- V2 experiment runner compatibility.

Reviewed files:

- `src/repo_harness/evaluation/schemas.py`
- `src/repo_harness/evaluation/runner.py`
- `src/repo_harness/v3_experiment_resume.py`
- `src/repo_harness/cli/main.py`
- `tests/integration/test_experiment_resume_v3.py`
- `tests/fixtures/run_configs/v3/experiment_resume_smoke.yaml`
- `runs/v3-stage-08-experiment-resume-20260502T214500Z/`

## Findings

### P1

No P1 findings.

### P2: Absolute host path in checkpoint-scanned manifest

Initial Stage 8 targeted tests failed because `ExperimentResumeRunEntry.run_dir` serialized absolute temporary paths such as `/private/...` into `experiment_resume_manifest.json`. Since Stage 8 inspect scans checkpoint-related payloads with `V3ContaminationDenylist`, this was correctly rejected as host-path contamination.

Fix:

- Store `run_dir` relative to the experiment root with `_relative_path`.
- Keep ArtifactRefs relative to the experiment root where possible.
- Re-run Stage 8 tests and regenerate the formal Stage 8 artifact directory.

Status: fixed.

### P2: Misleading `run-experiment --resume` placeholder

An intermediate CLI patch added a `run-experiment --resume` parser argument only to make command log argv look parseable. That would overstate generic `run-experiment` resume support and could confuse acceptance reviewers.

Fix:

- Removed the placeholder parser argument.
- Kept the actual Stage 8 support in `build-v3-experiment-resume` and `inspect-experiment-resume`.
- Changed the skip command log argv to a structured Stage 8 operation under `build-v3-experiment-resume`.

Status: fixed.

### P3: Stage artifact uses baseline interruption only

The code supports all required injection points: `baseline`, `agent_loop` and `final_verifier`. The formal Stage 8 artifact uses `baseline` because the implementation plan only requires at least one fixed injection point for phase completion.

Status: accepted as within phase scope.

## Verification Evidence

- `PATH=.venv/bin:$PATH python -m compileall src`: passed.
- `PATH=.venv/bin:$PATH python -m pytest tests/integration/test_experiment_resume_v3.py tests/unit/test_v3_schemas.py -q`: `10 passed`.
- `PATH=.venv/bin:$PATH python -m pytest tests/integration/test_experiment_runner.py tests/integration/test_experiment_resume_v3.py tests/unit/test_experiment_config.py tests/unit/test_v3_schemas.py -q`: `25 passed`.
- `PATH=.venv/bin:$PATH repo-harness build-v3-experiment-resume --config tests/fixtures/run_configs/v3/experiment_resume_smoke.yaml --output-dir runs/v3-stage-08-experiment-resume-20260502T214500Z --inject-interrupt-after baseline`: passed.
- `PATH=.venv/bin:$PATH repo-harness inspect-experiment-resume runs/v3-stage-08-experiment-resume-20260502T214500Z --manifest runs/v3-stage-08-experiment-resume-20260502T214500Z/experiment_resume_manifest.json --assert-resumable`: passed.
- `PATH=.venv/bin:$PATH repo-harness inspect-run` on completed, interrupted, continuation and resumed-pending runs: passed.
- `PATH=.venv/bin:$PATH python -m pytest -q`: `424 passed in 209.10s`.
- `PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete`: passed, report status `passed`.

## Boundary Checks

- Completed checkpoints include `run_metadata_ref`.
- Interrupted checkpoint does not include `run_metadata_ref` and points to `interrupted_run_facts.json`.
- Pending checkpoint does not misuse `run_config_facts_ref`; pending config is recorded outside `RunCheckpoint` as `pending_run_config_ref`.
- `inspect-experiment-resume` re-reads checkpoint refs and validates sha256 and size.
- Tampering an interrupted checkpoint to include `run_metadata_ref` is rejected by test.
- Checkpoint contamination scan on `experiment_resume_manifest.json`, `run_checkpoint_manifest.json` and `interrupted_run_diagnostics.json` is clean.
- Command log includes `run-task`, injected interrupt argv and completed skip evidence.
- Run directory lock probe records a conflict without unbounded cleanup.

## Residual Risk

- Stage 8 does not implement arbitrary turn resume or provider continuation. This is an explicit V3 boundary, not a defect.
- Stage 8 failure distribution is intentionally narrow. Stage 10 owns expanded failure diagnostics.
- The generic V2 `run-experiment` command remains a sequential runner. V3 resume evidence is produced by the dedicated Stage 8 builder and inspect command.

## Decision

No remaining P1 or P2 findings. P3 is documented and within phase scope. Full-test and V2 regression verification passed, so Stage 8 may proceed to Stage 9.
