# Stage 06: ExperimentConfig minimal rollout runner

## 本阶段目标

本阶段目标是实现最小 `ExperimentConfig` 多 rollout 运行器和实验检查命令。Stage 06 只承诺 replay provider 和 `simple_react` scaffold，按顺序调用已有 Eval Runner；不实现并发调度器，不实现 Stage 07 的 ModelClient protocol、factory 或 scaffold registry。

## 本阶段实现内容

- 新增 `evaluation/experiment.py`：
  - 加载 `ExperimentConfig`。
  - 顺序生成每个 task 和 rollout 的 run config。
  - 通过现有 `run_task(...)` 执行每个 run，保持 Eval Runner、RunRecorder、Workspace Adapter 和 verifier 边界。
  - 单个 run 失败时继续写 `experiment_manifest.json`，并在 run record 中记录 `status = error` 和结构化 `failure_reason`。
  - 写出 `experiment_manifest.json`、`aggregate_metrics.json`、`experiment_summary.md` 和 `compare_scope.json`。
  - 可选调用 Stage 05 preference export，并传入实验 compare scope 文件。
- 扩展 `ExperimentConfig`：
  - 表达 task 列表、rollout count、replay provider config、单一 `simple_react` scaffold、预算、permission mode、output dir、run id naming policy、compare scope、aggregate report 和 preference export 开关。
  - Stage 06 明确拒绝非 replay provider、非 `simple_react` scaffold 和 `permission_mode=ask`。
  - 强制 `run_id_template` 包含 task id、model alias、scaffold id 和 rollout index。
- 新增 `ExperimentMinimums` 和 `inspect-experiment`：
  - 检查 manifest、aggregate metrics、total/recorded runs、failure records 和 all-skipped 情况。
  - `require_failure_records=true` 时逐个检查 error run 必须有 `failure_reason`。
- 修改 CLI：
  - 新增 `run-experiment --config ... --output-dir ...`。
  - 新增 `inspect-experiment <dir> --assert-minimums ...`。
- 新增测试 fixture：
  - `tests/fixtures/run_configs/v2/experiment_smoke.yaml`
  - `tests/fixtures/run_configs/v2/experiment_smoke_thresholds.yaml`

## 修改的主要文件

- `src/repo_harness/evaluation/experiment.py`
- `src/repo_harness/evaluation/schemas.py`
- `src/repo_harness/evaluation/__init__.py`
- `src/repo_harness/cli/main.py`
- `tests/fixtures/run_configs/v2/experiment_smoke.yaml`
- `tests/fixtures/run_configs/v2/experiment_smoke_thresholds.yaml`
- `tests/unit/test_experiment_config.py`
- `tests/integration/test_experiment_runner.py`

## 生成的机器可读产物

阶段验收运行生成了：

- `runs/v2-experiment-smoke-20260501T190444Z/experiment_manifest.json`
- `runs/v2-experiment-smoke-20260501T190444Z/aggregate_metrics.json`
- `runs/v2-experiment-smoke-20260501T190444Z/compare_scope.json`
- `runs/v2-experiment-smoke-20260501T190444Z/exports/preference_*/export_manifest.json`
- 每个成功 run 的独立 run directory、`run_config_facts.json`、`run_metadata.json` 和 trajectory artifacts

这些运行产物作为本地验收证据保留在 `runs/`，未提交到 Git。

## 运行的验证命令

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_experiment_config.py tests/integration/test_experiment_runner.py
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v2_schemas.py tests/unit/test_export.py tests/integration/test_export_from_run.py tests/unit/test_experiment_config.py tests/integration/test_experiment_runner.py
PATH=.venv/bin:$PATH repo-harness run-experiment --config tests/fixtures/run_configs/v2/experiment_smoke.yaml --output-dir runs/v2-experiment-smoke-20260501T190444Z
PATH=.venv/bin:$PATH repo-harness inspect-experiment runs/v2-experiment-smoke-20260501T190444Z --assert-minimums tests/fixtures/run_configs/v2/experiment_smoke_thresholds.yaml
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_experiment_config.py tests/integration/test_experiment_runner.py tests/unit/test_v2_schemas.py tests/unit/test_export.py tests/integration/test_export_from_run.py tests/integration/test_minimal_vertical_slice.py tests/integration/test_eval_runner_quality_gate.py
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q
```

## 验证结果

- ExperimentConfig 和 experiment runner 定向测试通过，9 个测试通过。
- Stage 06 相关综合测试通过，60 个测试通过。
- smoke CLI 验收通过，`inspect-experiment --assert-minimums` 成功。
- `python -m compileall src` 通过。
- 全量测试通过，242 个测试通过。

## 正例证据

- `run-experiment` 可以用 replay provider 和 `simple_react` 对同一任务执行两次 rollout。
- run id 包含 `task_id`、`model_alias`、`scaffold_id` 和 `rollout_index`，例如 `v2_exp_smoke_task_001_replay_simple_react_r000`。
- `experiment_manifest.json` 记录每个 run 的模型、scaffold、rollout index、run outcome 和 error 情况。
- 单个 run 出错时，实验仍写 manifest、aggregate metrics 和 summary。
- `inspect-experiment --assert-minimums` 在阈值满足时通过。

## 负例证据

- 非 replay provider 被 `ExperimentConfig` 拒绝。
- 非 `simple_react` scaffold 被 `ExperimentConfig` 拒绝。
- 缺少必要维度的 `run_id_template` 被拒绝。
- 阈值不足时 `inspect-experiment` 失败。
- error run 缺少 `failure_reason` 时 `inspect-experiment` 失败。

## 允许降级项

- Stage 06 只支持顺序运行，`concurrency` 固定为 1。
- Stage 06 只支持 replay provider；fake/mock/real provider 等到 Stage 07、Stage 10 和 Stage 11。
- Stage 06 只支持 `simple_react`；scaffold registry 和新增 scaffold 等到 Stage 07 到 Stage 09。
- compare scope 文件由实验 runner 写出并交给 Stage 05 exporter 使用，ExperimentConfig 还不是 provider/scaffold 全局编排入口。

## 禁止降级项

- 不能绕过 `run_task`、Eval Runner、RunRecorder、Workspace Adapter 或 verifier。
- 单个 run 失败不能导致实验 manifest 缺失。
- run id 不能缺少 task id、model alias、scaffold id 或 rollout index。
- Stage 06 不能把跨 scaffold、跨模型 pair 当作正式训练数据。

## 已知限制

- 没有并发调度器，没有异步 rollout service，没有远程 worker。
- run id 模板校验基于字符串包含关系，没有使用 `string.Formatter` 做更复杂的模板语义解析；当前 smoke 和负例覆盖足以保护阶段六必需字段。
- preference export 仍由 Stage 05 exporter 决定是否 skipped 或 trainable。

## 是否偏离设计文档

未发现必须记录的设计冲突。本阶段按照文档要求保持 `run_experiment` 对现有 Eval Runner 的调用，不提前引入 Stage 07 ModelClient 或 scaffold registry。

## sub agent 审查结论

已安排只读 sub agent 审查。初审未发现 P1，发现两个 P2 和一个 P3：

- P2：`run_id_template` 未强制包含 task id、model alias、scaffold id 和 rollout index。
- P2：`require_failure_records` 检查过于宽松。
- P3：缺少 run id 命名策略负例测试。

上述问题均已修复，并补充负例测试。复审未发现新的 P1 或 P2，结论是 Stage 06 可以提交。审查记录保存到 `docs/v2/review/implementation/stage-06-review.md`。

## 是否可以进入下一阶段

可以进入 Stage 07。进入下一阶段前，Stage 06 commit 必须只包含当前阶段相关代码、测试、fixture、阶段日志和审查记录。
