# Stage 06 只读审查记录

## 审查方式

本阶段安排了只读 sub agent 审查。审查 agent 没有修改文件。审查分为初审和修复后复审。

## 审查重点

- 是否严格限于 Stage 06 ExperimentConfig 最小多 rollout 运行器和实验检查。
- 是否没有提前实现 Stage 07 ModelClient protocol、factory 或 scaffold registry。
- `run_experiment` 是否通过现有 `run_task` 执行每个 run。
- 是否没有绕过 Eval Runner、RunRecorder、Workspace Adapter 或 verifier。
- run id 是否包含 task id、model alias、scaffold id 和 rollout index。
- 单个 run 出错时是否仍写 manifest、aggregate 和 summary。
- error run 是否有结构化 `failure_reason`。
- 是否只支持 replay provider 和 `simple_react` scaffold。
- `inspect-experiment --assert-minimums` 是否检查 manifest、aggregate、run 数量、failure records 和 all-skipped 情况。

## 初审发现

### P1

未发现 P1 问题。

### P2

1. `run_id_template` 未强制包含必要维度。处理方式：`ExperimentConfig.validate_stage06_scope` 现在要求模板包含 `task_id`、`model_alias`、`scaffold_id` 和 `rollout_index`。
2. `require_failure_records` 检查过于宽松。处理方式：`inspect_experiment` 现在会逐个检查 `status=error` 的 manifest run record 必须有 `failure_reason`。

### P3

1. 缺少 run id 命名策略负例测试。处理方式：新增 `test_experiment_config_rejects_run_id_template_missing_required_dimensions`。

## 复审结果

复审未发现新的 P1 或 P2。复审确认：

- run id 模板强校验已生效。
- failure records 检查已经覆盖 manifest 级 `failure_reason`。
- `run_experiment` 仍然调用现有 `run_task(...)`。
- 没有提前引入 Stage 07 ModelClient protocol、model client factory 或 scaffold registry。
- Stage 06 仍收紧在 replay provider 和 `simple_react` scaffold。

## 审查验证

sub agent 运行：

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_experiment_config.py tests/integration/test_experiment_runner.py
```

验证结果：

- ExperimentConfig 和 experiment runner 测试通过，9 个测试通过。

## 主流程补充验证

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_experiment_config.py tests/integration/test_experiment_runner.py
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_experiment_config.py tests/integration/test_experiment_runner.py tests/unit/test_v2_schemas.py tests/unit/test_export.py tests/integration/test_export_from_run.py tests/integration/test_minimal_vertical_slice.py tests/integration/test_eval_runner_quality_gate.py
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q
```

验证结果：

- Stage 06 定向测试通过，9 个测试通过。
- Stage 06 综合相关回归通过，60 个测试通过。
- 编译通过。
- 全量测试通过，242 个测试通过。

## 结论

初审 P2 和 P3 已修复，复审未发现新的 P1 或 P2。Stage 06 可以提交，并可以进入 Stage 07。
