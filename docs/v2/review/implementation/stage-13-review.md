# Stage 13 只读审查记录

## 审查方式

本阶段安排了只读 sub agent 审查。审查 agent 没有修改文件。主流程根据审查结论修复了可以在 Stage 13 范围内完成的 P3 项，并重新运行相关检查。

## 审查重点

- 是否至少 20 个任务通过静态校验。
- 是否至少 15 个任务进入 Agent Loop。
- 是否至少 15 个任务产生 formal final verifier。
- 是否至少 3 个任务 accepted。
- 是否包含 invalid、flaky、dependency failed 或等价环境失败样例，并且有结构化 skipped reason。
- 是否没有把 mock provider、真实 provider、Docker 或 Stage 15 全局验收混入 Stage 13。
- 隐藏测试、gold patch 和 reward-only 字段是否没有进入模型上下文或训练导出。
- `ExperimentMinimums` 和 `inspect-experiment` 是否真的检查 Stage 13 阈值。
- export audit 是否 clean。
- 是否破坏第一版 replay、export 或 scaffold 行为。

## 审查发现

### P1

未发现 P1。

### P2

未发现 P2。

### P3

1. Stage 13 task set 数量满足门槛，但任务较同质。
   - 现状：18 个成功任务使用同一个 `buggy_calculator` 仓库、同一个 divide-by-zero 修复和同一组 fail/pass tests 的 wording variants。
   - 处理：记录为后续增强。当前实现满足 Stage 13 最低验收口径，但后续应补充更多 import/config/CLI/terminal-style repository tasks。

2. `inspect-experiment` export audit check 初始实现弱于 `inspect-export`。
   - 风险：如果只运行 `inspect-experiment --assert-minimums`，它不能单独证明 manifest 绑定、data sha、正式 JSONL 只含 trainable、hidden/local path 检查等导出完整性。
   - 处理：已修复。`require_export_audit_clean=true` 时复用 `inspect_export(..., all_exports=True, assert_clean=True)`。

## 审查正例证据

- `total_runs=20`
- `task_count=20`
- `recorded_runs=20`
- `agent_loop_runs=18`
- `formal_final_verifier_runs=18`
- `success_count=18`
- `structured_skipped_runs=2`
- `environment_failure_distribution={"setup_failed": 2}`
- SFT、RL 和 preference 三种 export 均有 manifest 和 audit report。
- SFT 和 RL 导出通过 `--require-trainable-samples`。
- Preference export 因 pair 不足而 skipped，没有伪造 pair。

## 审查负例证据

- 没有 mock provider、真实 provider、Docker 或 Stage 15 全局验收混入 replay task set 阈值。
- 没有 SWE-Bench-like final-only 声明被滥用。
- 没有发现 hidden tests、gold patch 或 reward-only 字段进入 agent visible view。

## 修复后验证

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v2_task_set.py tests/integration/test_experiment_runner.py -q
PATH=.venv/bin:$PATH repo-harness inspect-experiment runs/v2-task-set-20260501T231000Z --assert-minimums tests/fixtures/run_configs/v2/task_set_thresholds.yaml
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q
```

验证结果：

- Stage 13 相关测试通过。
- `inspect-experiment --assert-minimums` 通过。
- 全量测试通过，335 个测试通过。

## 结论

Stage 13 没有剩余 P1/P2。一个任务多样性 P3 记录为后续增强，不阻断当前阶段提交。Stage 13 可以进入 Stage 14。
