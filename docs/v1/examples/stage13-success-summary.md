# Stage 13 Success Run Summary Example

该示例来自实际命令：

```bash
repo-harness run-batch \
  --config tests/fixtures/run_configs/batch_replay.yaml \
  --output-dir runs/final-acceptance
```

对应 run directory：

```text
runs/final-acceptance/stage11_batch_001_task_001
```

实际 `summary.md` 内容：

```markdown
# RepoHarness Run Summary

- run_id: stage11_batch_001_task_001
- task_id: task_001
- baseline_status: valid
- agent_stop_reason: feedback_tests_passed
- final_verifier_status: accepted
- final_verifier_mode: strict_patch_replay
- run_outcome: success
- outcome_policy_version: repo_harness_outcome_policy_v0
- permission_denial_count: 0
- resolved_verifier_plan: resolved_verifier_plan.json
- final.patch: final.patch
- final.diff: final.diff
```

该 run 可以通过下面命令重新生成：

```bash
rm -rf runs/final-acceptance
repo-harness run-batch \
  --config tests/fixtures/run_configs/batch_replay.yaml \
  --output-dir runs/final-acceptance
```
