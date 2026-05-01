# Stage 05: preference pair hard gates and compare scope

## 本阶段目标

本阶段目标是防止仅凭相同 task id 就把不同环境、不同工具协议、不同 verifier、不同 scaffold、不同模型参数或不同预算的 run 配成正式 preference training pair。Stage 05 只处理已有 run 的 preference 导出配对，不实现多 rollout runner，不实现实验运行器。

## 本阶段实现内容

- 新增 `export/pairing.py`：
  - 从 `run_config_facts.json`、`metrics.json`、`reward.json`、`verifier.json` 和 artifact manifest 中提取 `PairCandidate`。
  - 使用 `PairingPolicy` 和 `CompareScope` 进行 strict compare scope 硬门控。
  - 默认 canonical key 覆盖 task/source/environment/verifier/reward/tool/context/prompt/scaffold/model/budget 字段。
  - `seed` 和 `rollout_index` 不进入 canonical key，默认只作为受控采样变量。
  - 生成枚举化 `blocked_reasons`，包括 `compare_key_mismatch`、`tool_schema_snapshot_mismatch`、`context_policy_mismatch`、`budget_mismatch`、`missing_reward`、`reward_tie`、`missing_formal_final_verifier`、`non_formal_reward_source` 和 `artifact_manifest_invalid`。
- 修改 `export/exporter.py`：
  - preference export 改为先通过 pairing layer 获取 pair decision。
  - 只有 `PairDecision.allowed = true` 的 pair 才会构建正式 preference record。
  - skipped manifest 增加 candidate run count、blocked pair count、blocked reason distribution、pairing policy version 和 compare scope。
  - preference record metadata 记录 pairing policy、compare scope、chosen/rejected run metadata summary、source run ids 和 verifier artifact refs。
  - CLI 支持 `--compare-scope` 传入 CompareScope 或 PairingPolicy JSON 文件。
- 修改 `export/audit.py`：
  - preference audit 增加 `preference_pairing_policy_satisfied` audit item。
  - 如果 preference record 缺少 pairing metadata、存在 blocked reasons 或缺少 chosen/rejected 比较证据，audit item 会失败。
- 扩展导出测试：
  - 同 task、同条件、不同 reward 可以配对。
  - 同 reward 即使 outcome 不同也会被 `reward_tie` 阻断。
  - 不同 base commit 阻断。
  - 不同 tool schema snapshot 阻断。
  - 不同 scaffold 默认阻断，显式 compare scope experimental variables 可以放开。
  - 不同 seed、相同 canonical compare key 可以配对。
  - reward 缺失和非 formal final verifier 产生枚举化 blocked reason。

## 修改的主要文件

- `src/repo_harness/export/pairing.py`
- `src/repo_harness/export/exporter.py`
- `src/repo_harness/export/audit.py`
- `src/repo_harness/export/__init__.py`
- `src/repo_harness/cli/main.py`
- `tests/unit/test_export.py`
- `tests/integration/test_export_from_run.py`

## 生成的机器可读产物

Stage 05 本身不新增新的 run 产物类型。preference export 会在既有 Stage 04 规范导出目录中新增或强化这些机器可读字段：

- `exports/<export_id>/export_manifest.json` 中的 `command_args.pairing_policy_version`
- `exports/<export_id>/export_manifest.json` 中的 `command_args.compare_scope`
- `exports/<export_id>/export_manifest.json` 中的 `command_args.blocked_reason_distribution`
- `exports/<export_id>/preference_skipped.json` 中的 candidate 和 blocked reason 统计
- `exports/<export_id>/audit_report.json` 中的 `preference_pairing_policy_satisfied` audit item

测试中的 export directory 均位于 pytest 临时目录，没有提交到 Git。

## 运行的验证命令

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_export.py tests/integration/test_export_from_run.py
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_export.py tests/integration/test_export_from_run.py tests/unit/test_v2_schemas.py tests/unit/test_inspect_run.py tests/integration/test_minimal_vertical_slice.py tests/integration/test_eval_runner_quality_gate.py
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q
```

## 验证结果

- Stage 05 导出和 preference pairing 定向测试通过，20 个测试通过。
- Stage 01 到 Stage 05 综合相关回归通过，59 个测试通过。
- `python -m compileall src` 通过。
- 全量测试通过，233 个测试通过。

## 正例证据

- 同 task、同 strict compare key、不同 reward 的两个 run 可以生成 preference pair。
- 不同 seed、同 strict compare key 的两个 run 可以生成 preference pair。
- 显式 compare scope 将 `scaffold_id` 和 `scaffold_version` 标为 experimental variables 且 `training_export_allowed=true` 时，可以放开跨 scaffold 配对。
- preference pair 的 audit report 中包含 `preference_pairing_policy_satisfied = passed`。

## 负例证据

- 同 reward 的两个 run 即使 outcome 不同，也会被 `reward_tie` 阻断。
- 不同 base commit 被 `compare_key_mismatch` 阻断。
- 不同 tool schema snapshot 被 `tool_schema_snapshot_mismatch` 阻断。
- 不同 scaffold 默认被 `compare_key_mismatch` 阻断。
- reward 缺失被 `missing_reward` 阻断。
- 缺失 final verifier 被 `missing_formal_final_verifier` 阻断。
- 非 final verifier source 被 `non_formal_reward_source` 阻断。
- 被阻断时写稳定 `preference_skipped.json`，不写正式 trainable preference 样本。

## 允许降级项

- 没有 `ExperimentConfig` 时使用内置 strict compare scope，这是阶段五最低要求。
- `--compare-scope` 先支持 JSON 文件入口；Stage 06 后 `ExperimentConfig.compare_scope` 会成为推荐入口。
- legacy 或缺失关键 facts 的 run 默认无法满足 strict compare scope，只能进入 skipped/diagnostic 审计路径。

## 禁止降级项

- 不允许 reward tie 进入正式 preference training pair。
- 不允许缺失 reward 或非 formal final verifier 的 run 进入正式 preference pair。
- 不允许不同工具协议、不同 source checkout、不同 verifier、不同 scaffold、不同模型或不同预算在默认 strict compare scope 下配对。
- 不允许 preference pair 缺少可审计 pairing policy evidence。

## 已知限制

- Stage 05 未实现多 rollout runner；这是 Stage 06 范围。
- Stage 05 未把 compare scope 接入 ExperimentConfig；这是 Stage 06 范围。
- 目前 compare scope 文件入口只支持 JSON；后续可以按需要增加 YAML 加载。

## 是否偏离设计文档

未发现必须记录的设计冲突。本阶段严格停留在 preference export pair gating，没有新增实验运行器或 provider 能力。

## sub agent 审查结论

已安排只读 sub agent 审查。初审发现一个 P1 和两个 P2：

- P1：reward 相同但 outcome 不同时仍可能进入 formal preference pair。
- P2：pair metadata 没有记录足够的 verifier、reward、预算、模型和 scaffold 条件。
- P2：audit report 没有显式记录 pairing policy satisfaction。

上述问题均已修复。复审未发现新的 P1 或 P2，结论是 Stage 05 可以提交。审查记录保存到 `docs/v2/review/implementation/stage-05-review.md`。

## 是否可以进入下一阶段

可以进入 Stage 06。进入下一阶段前，Stage 05 commit 必须只包含当前阶段相关代码、测试、阶段日志和审查记录。
