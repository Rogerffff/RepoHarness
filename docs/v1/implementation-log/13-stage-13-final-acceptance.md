# Stage 13: Final Acceptance

## Scope

本阶段实现了：

- 将根目录 `README.md` 从“设计阶段骨架”更新为“第一版实现范围”。
- 更新 `docs/00-reading-guide.md` 和 `src/repo_harness/README.md`，避免继续声称当前仓库只是未来实现占位。
- 更新 `docs/11-object-model-config-and-data-flow.md` 的阶段状态说明，保留对象边界，同时明确第一版已实现最小闭环，真实模型供应商、Docker 执行模式和复杂 scaffold 仍是后续扩展。
- 新增 `docs/v1/walkthrough.md`，说明如何运行任务校验、replay agent、run artifact 检查、批量运行和训练数据导出。
- 新增 `docs/v1/final-acceptance.md`，记录最终验收命令、结果和可复盘样例。
- 新增 `docs/v1/examples/stage13-success-summary.md`，保存来自真实成功 run 的 `summary.md` 示例。
- 新增 `docs/v1/developer-checklist.md`，总结后续开发必须遵守的第一版边界。
- 补强 `repo-harness export <runs_dir> --format sft_jsonl|rl_jsonl`，让 Stage 13 验收命令可以直接对 runs 根目录导出监督微调 JSONL 和强化学习 rollout JSONL。
- 新增两个 Stage 13 验收补充集成测试，覆盖 strict patch replay failure 和低 parser confidence quality gate。

本阶段明确不实现：

- 不接入真实模型供应商。
- 不实现生产级安全沙箱。
- 不新增训练算法。
- 不提交 `runs/` 运行产物。

## Design References

- `docs/v1/implementation-plan.md`
- `docs/11-object-model-config-and-data-flow.md`
- `docs/08-trajectory-store-and-training-export.md`

## Files Changed

- `README.md`
- `docs/00-reading-guide.md`
- `docs/11-object-model-config-and-data-flow.md`
- `src/repo_harness/README.md`
- `docs/v1/walkthrough.md`
- `docs/v1/final-acceptance.md`
- `docs/v1/examples/stage13-success-summary.md`
- `docs/v1/developer-checklist.md`
- `docs/v1/implementation-log/13-stage-13-final-acceptance.md`
- `docs/v1/review/implementation/13-stage-13-review.md`
- `src/repo_harness/export/exporter.py`
- `tests/integration/test_export_from_run.py`
- `tests/integration/test_eval_runner_quality_gate.py`

## Verification

运行的命令：

```bash
rm -rf runs/final-acceptance runs/final-acceptance-extras
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest
git diff --check
PATH=.venv/bin:$PATH repo-harness run-batch --config tests/fixtures/run_configs/batch_replay.yaml --output-dir runs/final-acceptance
PATH=.venv/bin:$PATH repo-harness export runs/final-acceptance --format sft_jsonl
PATH=.venv/bin:$PATH repo-harness export runs/final-acceptance --format rl_jsonl
PATH=.venv/bin:$PATH python - <<'PY'
import json
import subprocess
from pathlib import Path

manifest = json.loads(Path("runs/final-acceptance/batch_manifest.json").read_text())
first_run_dir = manifest["runs"][0]["run_dir"]
subprocess.run(["repo-harness", "inspect-run", first_run_dir], check=True)
PY
PATH=.venv/bin:$PATH repo-harness run-task tests/fixtures/tasks/task_001.yaml --config tests/fixtures/run_configs/replay_failure_minimal.yaml --output-dir runs/final-acceptance-extras --run-id final-failed
PATH=.venv/bin:$PATH repo-harness run-task tests/fixtures/tasks/task_security_probe.yaml --config tests/fixtures/run_configs/replay_security_negative_minimal.yaml --output-dir runs/final-acceptance-extras --run-id final-permission-denied
PATH=.venv/bin:$PATH repo-harness run-task tests/fixtures/tasks/task_001.yaml --config tests/fixtures/run_configs/replay_unknown_tool.yaml --output-dir runs/final-acceptance-extras --run-id final-unknown-tool
PATH=.venv/bin:$PATH python -m pytest tests/integration/test_eval_runner_quality_gate.py -q
```

结果：

- `python -m compileall src` 通过。
- 全量测试通过，收集并通过 160 个测试。
- `git diff --check` 未发现空白错误。
- 批量 replay 生成 3 个 run：
  - `task_001` 成功，`run_outcome = success`。
  - `task_invalid` 被 baseline quality gate 标记为 `invalid_task`。
  - `task_flaky` 被 baseline quality gate 标记为 `flaky_task`。
- 额外样例覆盖：
  - final verifier failed。
  - permission denied。
  - invalid tool call。
- 监督微调 JSONL 导出到 `runs/final-acceptance/exports/sft.jsonl`。
- 强化学习 rollout JSONL 导出到 `runs/final-acceptance/exports/rl.jsonl`。
- `inspect-run` 可以读取成功 run，并确认 artifacts manifest、baseline、final verifier、reward、metrics 和 summary。
- `tests/integration/test_eval_runner_quality_gate.py` 通过 10 个测试，其中新增测试覆盖 strict patch replay failure 和低 parser confidence。

说明：

- 初次执行最终验收命令中的内联 Python 片段时，子进程没有继承包含 `.venv/bin` 的 `PATH`，导致找不到 `repo-harness` 可执行文件。随后使用 `PATH=.venv/bin:$PATH python - <<'PY' ...` 重新执行并通过。这是命令环境问题，不是 RepoHarness 运行逻辑失败。

## Review

审查方式：

- 主实现 agent 自查。
- sub agent 只读审查，审查记录保存到 `docs/v1/review/implementation/13-stage-13-review.md`。

关键审查意见：

- P2：最终验收文档只引用了 strict patch replay failure 和低 parser confidence 的单元测试，弱于阶段十三“可复盘样例或独立集成测试覆盖”的标准。
- P3：Stage 13 审查记录仍是占位，缺少 `docs/v1/review/implementation/13-stage-13-review.md`。

处理结果：

- 采纳 P2：新增 `test_strict_patch_replay_failure_derives_inconclusive_outcome` 和 `test_low_parser_confidence_blocks_agent_run` 两个集成测试，并更新 `docs/v1/final-acceptance.md`。
- 采纳 P3：新增 `docs/v1/review/implementation/13-stage-13-review.md`，并更新本日志 Review 小节。

## Known Limitations

- 第一版仍然只使用 fake model 和 replay model。
- 第一版仍然只提供本地进程执行边界，不提供生产级安全沙箱。
- 导出脱敏是基础防护，不是完整 secret scanner。
- Preference pair 导出保持最小实现；默认验收重点是监督微调 JSONL 和强化学习 rollout JSONL。

## Commit

- Commit: `stage 13: finalize acceptance docs`
- Commit message: `stage 13: finalize acceptance docs`
