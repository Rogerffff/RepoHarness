# Stage 05 只读审查记录

## 审查方式

本阶段安排了只读 sub agent 审查。审查 agent 没有修改文件。审查分为初审和修复后复审。

## 审查重点

- 是否严格限于 Stage 05 preference pair hard gates 和 compare scope。
- 是否没有提前实现 Stage 06 实验运行器。
- 默认 strict compare scope 是否覆盖 task/source/environment/verifier/reward/tool/context/prompt/scaffold/model/budget 字段。
- `seed` 和 `rollout_index` 是否默认不是 canonical key。
- 不同 base commit、不同 tool schema、不同 scaffold 是否默认阻断。
- 显式 compare scope experimental variables 是否可以放开对应字段，并记录在 manifest/metadata。
- reward tie、missing reward、非 formal final verifier 是否产生枚举化 blocked reason。
- preference skipped manifest 是否包含 candidate count、blocked pair count 和 blocked reason distribution。
- Stage 04 export audit 和正式 JSONL 只含 trainable 样本的约束是否保留。

## 初审发现

### P1

1. Reward 相等但 outcome 不同时仍可能进入 formal preference pair。处理方式：只要两个候选 run 的 `final_reward` 相同，就追加 `reward_tie` 并阻断。

### P2

1. Pair metadata 没有记录足够的比较证据。处理方式：`PairCandidate.metadata_summary` 补齐 verifier、reward formula、final verifier mode、tool protocol、context/prompt policy、model provider/id/temperature/max output tokens、scaffold、allowed tools、phase policy 和 turn/tool/test/task timeout budget。
2. Audit report 没有显式审计 pairing policy satisfaction。处理方式：preference audit 增加 `preference_pairing_policy_satisfied` audit item，缺少 pairing metadata、存在 blocked reasons 或缺少 chosen/rejected metadata summary 时失败。

## 复审结果

复审未发现新的 P1 或 P2。复审确认：

- `reward_tie` 已按 final reward 相等硬阻断。
- pair metadata 已补齐可审计比较条件。
- audit report 会记录 `preference_pairing_policy_satisfied`。
- 未发现 Stage 06 实验运行器或命令入口被提前引入。

## 审查验证

sub agent 运行：

```bash
PYTHONDONTWRITEBYTECODE=1 PATH=.venv/bin:$PATH python -m pytest -p no:cacheprovider tests/unit/test_export.py tests/integration/test_export_from_run.py
```

验证结果：

- 导出和 preference pairing 测试通过，20 个测试通过。

## 主流程补充验证

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_export.py tests/integration/test_export_from_run.py
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_export.py tests/integration/test_export_from_run.py tests/unit/test_v2_schemas.py tests/unit/test_inspect_run.py tests/integration/test_minimal_vertical_slice.py tests/integration/test_eval_runner_quality_gate.py
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q
```

验证结果：

- Stage 05 定向测试通过，20 个测试通过。
- Stage 01 到 Stage 05 综合相关回归通过，59 个测试通过。
- 编译通过。
- 全量测试通过，233 个测试通过。

## 结论

初审 P1 和 P2 已修复，复审未发现新的 P1 或 P2。Stage 05 可以提交，并可以进入 Stage 06。
