# RepoHarness V1 Final Acceptance

本文档记录 RepoHarness 第一版最终验收结果。它不是运行产物的替代品，真实产物仍然保存在 `runs/` 下；本文档只记录验收命令、关键输出和可复盘样例。

## 验收范围

本次验收覆盖：

- 全量 Python 测试。
- 三个 micro-repo task 的顺序批量 replay 运行。
- 成功运行、invalid task、flaky task、final verifier failed、权限拒绝和无效工具调用样例。
- 监督微调 JSONL（`sft_jsonl`）导出。
- 强化学习 rollout JSONL（`rl_jsonl`）导出。
- `inspect-run` 对实际 run directory 的检查。

## 验收命令

成功执行的命令如下：

```bash
rm -rf runs/final-acceptance runs/final-acceptance-extras
PATH=.venv/bin:$PATH python -m pytest
PATH=.venv/bin:$PATH repo-harness run-batch \
  --config tests/fixtures/run_configs/batch_replay.yaml \
  --output-dir runs/final-acceptance
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
```

额外边界样例命令如下：

```bash
PATH=.venv/bin:$PATH repo-harness run-task tests/fixtures/tasks/task_001.yaml \
  --config tests/fixtures/run_configs/replay_failure_minimal.yaml \
  --output-dir runs/final-acceptance-extras \
  --run-id final-failed

PATH=.venv/bin:$PATH repo-harness run-task tests/fixtures/tasks/task_security_probe.yaml \
  --config tests/fixtures/run_configs/replay_security_negative_minimal.yaml \
  --output-dir runs/final-acceptance-extras \
  --run-id final-permission-denied

PATH=.venv/bin:$PATH repo-harness run-task tests/fixtures/tasks/task_001.yaml \
  --config tests/fixtures/run_configs/replay_unknown_tool.yaml \
  --output-dir runs/final-acceptance-extras \
  --run-id final-unknown-tool
```

## 验证结果

- `PATH=.venv/bin:$PATH python -m pytest` 通过，收集并通过 160 个测试。
- `run-batch` 生成 `runs/final-acceptance/batch_manifest.json`。
- `repo-harness export runs/final-acceptance --format sft_jsonl` 生成 `runs/final-acceptance/exports/sft.jsonl`。
- `repo-harness export runs/final-acceptance --format rl_jsonl` 生成 `runs/final-acceptance/exports/rl.jsonl`。
- `inspect-run` 可以读取实际成功 run，并确认 artifacts manifest、baseline、final verifier、reward、metrics 和 summary。

## 样例清单

| Run directory | Task | Baseline status | Run outcome | Final verifier status | Agent stop reason | 权限拒绝数量 | 无效工具调用数量 |
| --- | --- | --- | --- | --- | --- | ---: | ---: |
| `runs/final-acceptance/stage11_batch_001_task_001` | `task_001` | `valid` | `success` | `accepted` | `feedback_tests_passed` | 0 | 0 |
| `runs/final-acceptance/stage11_batch_002_task_invalid` | `task_invalid` | `invalid` | `invalid_task` | `skipped` | `skipped_invalid_baseline` | 0 | 0 |
| `runs/final-acceptance/stage11_batch_003_task_flaky` | `task_flaky` | `flaky` | `flaky_task` | `skipped` | `skipped_flaky_baseline` | 0 | 0 |
| `runs/final-acceptance-extras/final-failed` | `task_001` | `valid` | `failed` | `failed` | `final_answer` | 0 | 0 |
| `runs/final-acceptance-extras/final-permission-denied` | `task_security_probe` | `valid` | `success` | `accepted` | `final_answer` | 4 | 0 |
| `runs/final-acceptance-extras/final-unknown-tool` | `task_001` | `valid` | `failed` | `failed` | `final_answer` | 0 | 1 |

所有上表中的有效 run 都生成可复盘的 `events.jsonl`、`transcript.jsonl`、`artifacts.json`、`metrics.json` 和 `summary.md`。成功、失败、权限拒绝和无效工具调用样例还包含 `final.patch`、`final.diff`、`verifier.json` 和 `reward.json`。

## `inspect-run` 输出摘要

对成功 run 执行 `inspect-run` 的关键输出如下：

```text
Run directory: runs/final-acceptance/stage11_batch_001_task_001
Status: FINALIZED
Events: 22
Artifacts: 46
Task id: task_001
Artifacts manifest: ok
Run outcome: success
Agent stop reason: feedback_tests_passed
Final verifier status: accepted
Baseline status: valid
Final verifier accepted: True
Reward: 0.996
Summary: present
Last event: run_finished
```

## 验收覆盖说明

- 成功 run、final verifier failed run、权限拒绝 run 和无效工具调用 run 均有实际 run directory。
- invalid task 和 flaky task 纳入默认批量运行，并且不会进入正式 Agent Loop。
- strict patch replay 失败不纳入默认批量运行；它由独立集成测试 `tests/integration/test_eval_runner_quality_gate.py::test_strict_patch_replay_failure_derives_inconclusive_outcome` 覆盖。该测试通过真实 `run_task` 路径构造 workspace-specific setup state，使冻结后的 `final.patch` 无法应用到独立 verification workspace，并断言 `final_verifier_status = error`、`run_outcome = inconclusive`。
- parser 低置信不纳入默认批量运行；它由独立集成测试 `tests/integration/test_eval_runner_quality_gate.py::test_low_parser_confidence_blocks_agent_run` 覆盖。该测试通过真实 `run_task` 路径触发 baseline parser confidence 低于阈值，并断言任务被 quality gate 标记为 `invalid_task`，不会进入 Agent Loop。
- 导出器只读取已有 run directory，不重新运行 verifier，不改写 reward 或 metrics 事实。

## 已知限制

- 第一版使用 replay model 和 fake model，不调用真实模型供应商。
- 第一版使用本地进程执行边界和权限规则，不提供生产级安全沙箱。
- 导出阶段只有基础字段过滤、本机路径脱敏和常见凭据正则脱敏，不等同于完整 secret scanner。
