# Stage 13: expand replay task set

## 本阶段目标

本阶段目标是在 Stage 12 的 repo materialization、命令策略、环境规格和 parser policy 质量门已经通过后，把 replay task set 扩展到至少 20 个 repository-level 或 repository-style task，并用 experiment manifest、aggregate metrics、export audit 和 threshold inspection 证明任务集可运行、可审计、可导出。

本阶段不做：

- 不追求公开榜单分数。
- 不实现 SWE-Bench Lite 适配。
- 不混入 mock provider、真实 provider、Docker stage 或 Stage 15 全局验收。
- 不把 20 个任务描述成完整 benchmark。

## 本阶段实现内容

- 新增 V2 replay task set：
  - 18 个 `repository_style_fixture` calculator 任务。
  - 2 个 dependency/setup failed invalid task。
  - 总计 20 个任务可被 ExperimentConfig 加载和静态校验。
- 新增 task set experiment config：
  - `tests/fixtures/run_configs/v2/replay_experiment.yaml`
  - 使用 `model_provider=replay`。
  - 使用 `scaffold_id=simple_react`。
  - 使用 `test_feedback_policy=public_only`，避免 oracle hidden feedback 进入正式训练样本。
- 新增 task set threshold config：
  - `tests/fixtures/run_configs/v2/task_set_thresholds.yaml`
  - 阈值覆盖任务数量、进入 Agent Loop 数量、formal final verifier 数量、success 数量、结构化 skipped/invalid reason 和 export audit clean。
- 扩展 `ExperimentConfig`：
  - 新增 `test_feedback_policy`。
  - 新增 `feedback_tests_passed_policy`。
  - 让 experiment runner 可以为 Stage 13 replay task set 显式使用 public-only 测试反馈策略。
- 扩展 `ExperimentMinimums` 和 `inspect-experiment`：
  - `min_task_count`
  - `min_agent_loop_runs`
  - `min_formal_final_verifier_runs`
  - `min_success_count`
  - `min_structured_skipped_runs`
  - `require_export_audit_clean`
- 扩展 aggregate metrics：
  - `task_success_rate`
  - fail-to-pass pass rate
  - pass-to-pass keep rate
  - average turn count
  - average tool call count
  - average test run count
  - final verifier status distribution
  - run outcome distribution
  - permission denial rate
  - invalid tool call rate
  - timeout rate
  - patch size summary
  - environment failure distribution
- 收紧 `inspect-experiment --assert-minimums`：
  - `require_export_audit_clean=true` 时复用 `inspect_export(..., assert_clean=True)` 的完整检查，而不是只读取 audit status 字段。
- 新增 task set 单元测试：
  - 至少 20 个 task。
  - task id 唯一。
  - evaluator-only 字段不在 agent visible view。
  - threshold YAML 覆盖 Stage 13 最小门槛。

## 修改的主要文件

- `src/repo_harness/evaluation/schemas.py`
- `src/repo_harness/evaluation/experiment.py`
- `tests/fixtures/tasks/v2/calc_zero_001.yaml`
- `tests/fixtures/tasks/v2/calc_zero_002.yaml`
- `tests/fixtures/tasks/v2/calc_zero_003.yaml`
- `tests/fixtures/tasks/v2/calc_zero_004.yaml`
- `tests/fixtures/tasks/v2/calc_zero_005.yaml`
- `tests/fixtures/tasks/v2/calc_zero_006.yaml`
- `tests/fixtures/tasks/v2/calc_zero_007.yaml`
- `tests/fixtures/tasks/v2/calc_zero_008.yaml`
- `tests/fixtures/tasks/v2/calc_zero_009.yaml`
- `tests/fixtures/tasks/v2/calc_zero_010.yaml`
- `tests/fixtures/tasks/v2/calc_zero_011.yaml`
- `tests/fixtures/tasks/v2/calc_zero_012.yaml`
- `tests/fixtures/tasks/v2/calc_zero_013.yaml`
- `tests/fixtures/tasks/v2/calc_zero_014.yaml`
- `tests/fixtures/tasks/v2/calc_zero_015.yaml`
- `tests/fixtures/tasks/v2/calc_zero_016.yaml`
- `tests/fixtures/tasks/v2/calc_zero_017.yaml`
- `tests/fixtures/tasks/v2/calc_zero_018.yaml`
- `tests/fixtures/run_configs/v2/replay_experiment.yaml`
- `tests/fixtures/run_configs/v2/task_set_thresholds.yaml`
- `tests/unit/test_v2_task_set.py`

## 生成的机器可读产物

Stage 13 验收运行目录：

- `runs/v2-task-set-20260501T231000Z/experiment_manifest.json`
- `runs/v2-task-set-20260501T231000Z/aggregate_metrics.json`
- `runs/v2-task-set-20260501T231000Z/experiment_summary.md`
- `runs/v2-task-set-20260501T231000Z/compare_scope.json`
- `runs/v2-task-set-20260501T231000Z/exports/sft.jsonl`
- `runs/v2-task-set-20260501T231000Z/exports/rl.jsonl`
- `runs/v2-task-set-20260501T231000Z/exports/preference_skipped.json`
- `runs/v2-task-set-20260501T231000Z/exports/sft_20260501T220424Z_9977afefb6/export_manifest.json`
- `runs/v2-task-set-20260501T231000Z/exports/sft_20260501T220424Z_9977afefb6/audit_report.json`
- `runs/v2-task-set-20260501T231000Z/exports/rl_20260501T220424Z_e00dd2dbdd/export_manifest.json`
- `runs/v2-task-set-20260501T231000Z/exports/rl_20260501T220424Z_e00dd2dbdd/audit_report.json`
- `runs/v2-task-set-20260501T231000Z/exports/preference_20260501T220425Z_c2aeca99db/export_manifest.json`
- `runs/v2-task-set-20260501T231000Z/exports/preference_20260501T220425Z_c2aeca99db/audit_report.json`

关键 aggregate metrics：

- `total_runs=20`
- `task_count=20`
- `recorded_runs=20`
- `agent_loop_runs=18`
- `formal_final_verifier_runs=18`
- `success_count=18`
- `structured_skipped_runs=2`
- `task_success_rate=0.9`
- `status_distribution={"invalid_task": 2, "success": 18}`
- `quality_gate_reason_distribution={"setup_failed": 2}`
- `fail_to_pass_pass_rate=1.0`
- `pass_to_pass_keep_rate=1.0`

## 运行的验证命令

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v2_task_set.py tests/unit/test_experiment_config.py tests/integration/test_experiment_runner.py -q
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q

TASK_SET_DIR=runs/v2-task-set-20260501T231000Z
PATH=.venv/bin:$PATH repo-harness run-experiment --config tests/fixtures/run_configs/v2/replay_experiment.yaml --output-dir "$TASK_SET_DIR"
PATH=.venv/bin:$PATH repo-harness export "$TASK_SET_DIR" --format sft_jsonl
PATH=.venv/bin:$PATH repo-harness export "$TASK_SET_DIR" --format rl_jsonl
PATH=.venv/bin:$PATH repo-harness export "$TASK_SET_DIR" --format preference_jsonl
PATH=.venv/bin:$PATH repo-harness inspect-export "$TASK_SET_DIR/exports" --all --assert-clean
PATH=.venv/bin:$PATH repo-harness inspect-export "$TASK_SET_DIR/exports" --all --format sft_jsonl --require-trainable-samples
PATH=.venv/bin:$PATH repo-harness inspect-export "$TASK_SET_DIR/exports" --all --format rl_jsonl --require-trainable-samples
PATH=.venv/bin:$PATH repo-harness inspect-experiment "$TASK_SET_DIR" --assert-minimums tests/fixtures/run_configs/v2/task_set_thresholds.yaml
```

## 验证结果

- Stage 13 定向测试通过，17 个测试通过。
- `python -m compileall src` 通过。
- 全量测试通过，335 个测试通过。
- `run-experiment` 生成 20 个 recorded runs。
- `inspect-experiment --assert-minimums` 通过。
- SFT export audit clean，包含 18 个 trainable 样本。
- RL export audit clean，包含 18 个 trainable 样本。
- Preference export 因同任务 pair 不足生成 skipped artifact、manifest 和 audit report，未伪造 preference pair。

## 正例证据

- 至少 20 个 task 静态校验通过。
- 至少 15 个 task 进入正式 Agent Loop；实际为 18 个。
- 至少 15 个 task 产生 formal final verifier；实际为 18 个。
- 至少 3 个 task accepted；实际 success 为 18 个。
- 至少 1 个结构化 invalid/dependency failure；实际为 2 个 `setup_failed` invalid task。
- `test_feedback_policy=public_only`，正式训练样本没有依赖 oracle hidden feedback。
- SFT 和 RL 正式 JSONL 只包含 trainable 样本。
- Preference pair 不足时稳定生成 skipped manifest，不伪造 pair。
- export audit 由 `inspect-export --assert-clean` 检查。
- `inspect-experiment --assert-minimums` 检查 Stage 13 task set 事实，不混入 mock provider、真实 provider、Docker stage 或 Stage 15 全局验收事实。

## 负例证据

- 本阶段没有新增 mock provider、DeepSeek provider、OpenAI fallback 或 Docker backend 能力。
- 本阶段没有声称完整 benchmark 或公开榜单能力。
- 本阶段没有实现 SWE-Bench Lite 适配。
- 本阶段没有把 hidden tests、gold patch 或 reward-only 字段放入 agent visible view。
- Preference export 没有在 pair 不足时伪造训练 pair。

## 允许降级项

- 当前 20 个任务满足最低数量门槛，但任务多样性仍然有限，作为 P3 后续增强记录。
- Preference export 在单 rollout task set 下 skipped 是允许行为，因为同一任务没有两个可比较 run。
- Invalid/dependency failure 样例用于结构化 skipped reason 和质量门覆盖，不进入正式训练 JSONL。

## 禁止降级项

- 不能用扩大任务数量掩盖 Stage 12 命令策略、环境规格或 parser policy 失败。
- 不能把 invalid/dependency failed run 标记为 trainable。
- 不能把 oracle hidden feedback 样本默认放入正式训练 JSONL。
- 不能把 mock provider、真实 provider、Docker 或最终全局验收结果混入 replay task set 阈值。
- 不能把 task set 说成完整 benchmark。

## 已知限制

- 18 个成功任务使用同一个 `buggy_calculator` repository-style fixture 和同一个 divide-by-zero 修复模式，任务多样性较弱。后续应补充更多 import/config/CLI/terminal-style repository tasks。
- 本阶段没有新增按任务选择不同 replay script 的 experiment 配置；当前 task set 使用单一 replay script 验证 replay task-set 阈值和导出质量。
- 本阶段没有增加真实模型在 20 个任务上的运行结果；真实 provider 属于 Stage 11 smoke 和 Stage 15 汇总。

## 是否偏离设计文档

未发现需要记录的设计冲突。本阶段严格限定为 replay task set 扩展、experiment threshold 和 aggregate report 增强，没有提前实现 Stage 14 Docker 或 Stage 15 全局验收。

## sub agent 审查结论

已安排只读 sub agent 审查。审查未发现 P1 或 P2，发现 2 个 P3：

- P3：task set 数量满足门槛，但 18 个成功任务同质性较高，后续应增加更多不同仓库形态和 terminal/config/import-failure 类任务。
- P3：`inspect-experiment` 的 export audit check 初始实现弱于 `inspect-export --assert-clean`。

处理结果：

- 第二个 P3 已修复：`require_export_audit_clean=true` 时复用 `inspect_export(..., assert_clean=True)`。
- 第一个 P3 记录为后续增强，不阻断 Stage 13，因为当前 task set 满足本阶段最低验收口径。

审查记录保存到 `docs/v2/review/implementation/stage-13-review.md`。

## 是否可以进入下一阶段

可以进入 Stage 14。进入下一阶段前，Stage 13 commit 必须只包含当前阶段相关代码、测试、fixture、阶段日志和审查记录。
