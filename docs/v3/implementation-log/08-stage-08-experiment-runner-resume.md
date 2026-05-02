# V3 Stage 8 Implementation Log: Experiment Runner Resume

## Goal

把真实任务运行推进为 run-level 可恢复实验，而不是一次性脚本。阶段 8 只实现可恢复 experiment runner、checkpoint manifest、中断注入和 resume inspect，不进入阶段 9 的 context compaction，也不进入阶段 10 到阶段 12 的 export audit、failure diagnostics 或 acceptance bundle。

## Implementation Summary

- 扩展 `RunCheckpoint`，新增 checkpoint id、checkpoint type、created at、workspace / final patch refs 和 resume eligibility，并继续强制 `run_metadata_ref` 只能在 `completed` 或 `failed` checkpoint 中出现。
- 新增 `ExperimentResumeRunEntry`，让 `ExperimentResumeManifest` 记录 run state、attempt、last checkpoint ref、failure category、retryable、resume action、parent run id 和 continuation reason。
- 在 `run_task` 增加测试专用中断注入点：`baseline`、`agent_loop`、`final_verifier`。中断会写入 `interrupted_run_facts.json`，把 recorder 标记为 `INTERRUPTED`，并且不会写最终 `run_metadata.json`。
- 新增 `build-v3-experiment-resume`，构造一次 completed、interrupted、pending 的实验状态，然后执行 resume：跳过 completed，使用新 run id 继续 interrupted，继续 pending。
- 新增 `inspect-experiment-resume RUN_DIR --manifest RUN_DIR/experiment_resume_manifest.json --assert-resumable`，重新读取 manifest、checkpoint refs、sha256、interrupted diagnostics、command log 和 checkpoint 污染扫描。
- 新增 command log evidence：`RUN_DIR/command_log.jsonl`，记录 `run-task`、中断注入和 completed skip。
- 新增 run directory lock probe，证明同一个 run directory 不能被两个 recorder 同时写入。

## Main Files

- `src/repo_harness/evaluation/schemas.py`
- `src/repo_harness/evaluation/runner.py`
- `src/repo_harness/evaluation/__init__.py`
- `src/repo_harness/v3_experiment_resume.py`
- `src/repo_harness/cli/main.py`
- `tests/fixtures/run_configs/v3/experiment_resume_smoke.yaml`
- `tests/integration/test_experiment_resume_v3.py`

## Machine Artifacts

Primary Stage 8 artifact directory:

- `runs/v3-stage-08-experiment-resume-20260502T214500Z/`

Key files:

- `runs/v3-stage-08-experiment-resume-20260502T214500Z/experiment_resume_manifest.json`
- `runs/v3-stage-08-experiment-resume-20260502T214500Z/run_checkpoint_manifest.json`
- `runs/v3-stage-08-experiment-resume-20260502T214500Z/interrupted_run_diagnostics.json`
- `runs/v3-stage-08-experiment-resume-20260502T214500Z/failure_distribution_report.json`
- `runs/v3-stage-08-experiment-resume-20260502T214500Z/command_log.jsonl`
- `runs/v3-stage-08-experiment-resume-20260502T214500Z/run_directory_lock_diagnostic.json`

Run evidence:

- Completed before resume: `v3_resume_smoke_task_001_replay_simple_react_r000`
- Interrupted before resume: `v3_resume_smoke_task_001_replay_simple_react_r001`
- Continuation for interrupted run: `v3_resume_smoke_task_001_replay_simple_react_r001__resume001`
- Pending run completed during resume: `v3_resume_smoke_task_001_replay_simple_react_r002`

## Validation Commands

- `PATH=.venv/bin:$PATH python -m compileall src`
- `PATH=.venv/bin:$PATH python -m pytest tests/integration/test_experiment_resume_v3.py tests/unit/test_v3_schemas.py -q`
- `PATH=.venv/bin:$PATH python -m pytest tests/integration/test_experiment_runner.py tests/integration/test_experiment_resume_v3.py tests/unit/test_experiment_config.py tests/unit/test_v3_schemas.py -q`
- `PATH=.venv/bin:$PATH repo-harness build-v3-experiment-resume --config tests/fixtures/run_configs/v3/experiment_resume_smoke.yaml --output-dir runs/v3-stage-08-experiment-resume-20260502T214500Z --inject-interrupt-after baseline`
- `PATH=.venv/bin:$PATH repo-harness inspect-experiment-resume runs/v3-stage-08-experiment-resume-20260502T214500Z --manifest runs/v3-stage-08-experiment-resume-20260502T214500Z/experiment_resume_manifest.json --assert-resumable`
- `PATH=.venv/bin:$PATH repo-harness inspect-run runs/v3-stage-08-experiment-resume-20260502T214500Z/v3_resume_smoke_task_001_replay_simple_react_r000`
- `PATH=.venv/bin:$PATH repo-harness inspect-run runs/v3-stage-08-experiment-resume-20260502T214500Z/v3_resume_smoke_task_001_replay_simple_react_r001`
- `PATH=.venv/bin:$PATH repo-harness inspect-run runs/v3-stage-08-experiment-resume-20260502T214500Z/v3_resume_smoke_task_001_replay_simple_react_r001__resume001`
- `PATH=.venv/bin:$PATH repo-harness inspect-run runs/v3-stage-08-experiment-resume-20260502T214500Z/v3_resume_smoke_task_001_replay_simple_react_r002`
- `PATH=.venv/bin:$PATH python -m pytest -q`
- `PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete`

## Validation Results

- Compileall passed.
- Stage 8 and schema targeted tests passed: `10 passed`.
- Experiment runner regression and Stage 8 targeted set passed: `25 passed`.
- Full repository tests passed: `424 passed in 209.10s`.
- V2 acceptance regression passed: report status `passed`, task count `20`, mock provider `accepted`, real provider `accepted_with_credentials`.
- `inspect-experiment-resume --assert-resumable` passed with 5 command log entries.
- Completed runs have `run_metadata.json`.
- Interrupted run has `run_status.json` status `INTERRUPTED`, readable transcript/events/artifacts/run_config facts, no final `run_metadata.json`, and last event `run_interrupted`.
- Continuation run uses a new run id with `__resume001`.

## Positive Evidence

- Resume manifest records `skip_completed`, `continue_interrupted_as_new_run`, and `continue_pending`.
- Checkpoint manifest records five checkpoints: completed, interrupted, pending, continuation completed, pending completed.
- `interrupted_run_diagnostics.json` records original evidence preservation and lock diagnostic ref.
- Checkpoint contamination scan rejects host absolute paths and V3 denylist terms; the generated Stage 8 checkpoint surfaces are clean.

## Negative Evidence

- `tests/integration/test_experiment_resume_v3.py::test_inspect_experiment_resume_rejects_premature_run_metadata_ref` tampers an interrupted checkpoint to add `run_metadata_ref`; inspect rejects it.
- The first Stage 8 targeted run exposed a host absolute path in `ExperimentResumeRunEntry.run_dir`; the root cause was absolute tmp path serialization in checkpoint-scanned manifest payload. The fix stores run dirs relative to the experiment root.
- The run directory lock probe creates a deliberate lock conflict and records structured lock diagnostic evidence.

## Allowed Degradations

- `max_parallel_runs` remains `1`, matching the V3 conservative startup requirement.
- The formal Stage 8 artifact injects interruption after `baseline`. Code and CLI also support `agent_loop` and `final_verifier`, but the phase completion criterion only requires at least one fixed injection point.
- This is run-level and experiment-level resume only. It does not claim provider KV-cache resume, arbitrary turn resume, token-level write-ahead logging or live tool process continuation.

## Prohibited Degradations

- No overwrite of existing `RUN_DIR`; the builder refuses an existing output directory.
- No `run_metadata_ref` before final metadata exists.
- No final `run_metadata.json` requirement for interrupted runs.
- No hidden verifier result, scoring artifact, terminal result fact or evaluator-only failure detail is injected back into the same agent continuation context.
- No Docker fallback behavior is added or changed in this stage.

## Known Limits

- The Stage 8 builder is a deterministic local replay smoke for resume mechanics. Docker-backed V3 task runs remain covered by stages 2 to 7 and later acceptance selection.
- Failure distribution is intentionally minimal in Stage 8 and only records explicit resume categories needed here. Stage 10 expands core failure diagnostics and reward metadata.
- Preference pair baseline is not implemented in this stage; it belongs to Stage 11.

## Design Deviation

No intentional deviation from `docs/v3/implementation-plan.md`. The implementation keeps the scope to run-level resume and checkpoint-aware experiment resume, as required by the roadmap.

## Review Conclusion

Subagent review was attempted, but the environment reported `agent thread limit reached`. An equivalent independent read-only self-review was performed and saved in `docs/v3/review/implementation/stage-08-review.md`. The review found and fixed the absolute-path checkpoint contamination issue before this log was finalized.

Stage 8 is allowed to proceed to Stage 9 after final full-test and V2 regression verification pass.
