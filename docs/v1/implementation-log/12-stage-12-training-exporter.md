# Stage 12: Training Exporter

## Scope

本阶段实现了：

- `ExportPolicy` 和 `ExportRecord` 继续作为导出策略和导出记录 schema。
- Training Exporter 只读取已有 run directory：
  - `transcript.jsonl`
  - `events.jsonl`
  - `artifacts.json`
  - `metrics.json`
  - `reward.json`
  - `verifier.json`
  - `final.patch`
  - `summary.md`
- SFT JSONL 导出：
  - system、user、assistant、tool observation messages。
  - assistant 消息 loss mask。
  - tool observation mask。
  - final patch 和 termination summary。
  - final verifier ref 和 reward metadata ref。
- RL rollout JSONL 导出：
  - prompt 来自已有 `prepared_messages` artifact。
  - trajectory action 来自 `tool_requested` events。
  - observation 来自对应 tool result events。
  - final reward 来自 `reward.json`。
  - reward metadata ref 和 final verifier ref。
- Preference pair JSONL 导出：
  - 同一 task 下至少两个 run 时，根据 final reward 和 run outcome 生成 chosen/rejected。
  - 不足两个可配对 run 时，稳定写出 `preference_skipped.json`。
- `repo-harness export` CLI：
  - `--format sft_jsonl`
  - `--format rl_jsonl`
  - `--format preference_jsonl`
- 导出前做基础脱敏：
  - 本机绝对路径替换为 `<REDACTED_LOCAL_PATH>`。
  - 常见 provider credential、Authorization header、token、password 和 secret 形态替换为 `<REDACTED_CREDENTIAL>`。
  - `ExportRecord` schema 阻止隐藏字段、baseline 原始日志字段、reward-only 字段和本机绝对路径进入 payload/metadata。
- Tool observation 优先来自已有 `prepared_messages` artifact 中模型实际看到的内容；若最后一次工具结果没有后续 model turn，会显式标记 fallback 来源。

本阶段明确不实现：

- 不重新运行 verifier。
- 不修改原始 run directory 中已有事实文件。
- 不生成 parquet。
- 不实现真实 secret scanner；第一版只做保守字段过滤和本机路径脱敏。

## Design References

- `docs/v1/implementation-plan.md`
- `docs/08-trajectory-store-and-training-export.md`
- `docs/11-object-model-config-and-data-flow.md`

## Files Changed

- `src/repo_harness/cli/main.py`
- `src/repo_harness/export/__init__.py`
- `src/repo_harness/export/exporter.py`
- `tests/unit/test_export.py`
- `tests/integration/test_export_from_run.py`
- `docs/v1/review/implementation/12-stage-12-review.md`

## Verification

运行的命令：

```bash
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_export.py tests/integration/test_export_from_run.py -q
PATH=.venv/bin:$PATH repo-harness export runs/test-stage-11-final/stage11-success --format sft_jsonl
PATH=.venv/bin:$PATH repo-harness export runs/test-stage-11-final/stage11-success --format rl_jsonl
PATH=.venv/bin:$PATH repo-harness export runs/test-stage-11-final --format preference_jsonl
PATH=.venv/bin:$PATH python -m pytest
git diff --check
```

结果：

- 通过。
- Exporter 目标测试通过 8 个测试。
- 全量测试收集并通过 158 个测试。
- CLI 导出命令生成：
  - `runs/test-stage-11-final/stage11-success/exports/sft.jsonl`
  - `runs/test-stage-11-final/stage11-success/exports/rl.jsonl`
  - `runs/test-stage-11-final/exports/preference_skipped.json`
- 对 SFT 和 RL JSONL 字符串扫描未发现 `gold_patch`、`fail_to_pass_tests`、`pass_to_pass_tests`、`expected_outcome`、baseline 原始日志字段或本机绝对路径。
- `git diff --check` 未发现空白错误。

## Review

审查方式：

- 主实现 agent 自查。
- sub agent 只读审查，审查记录保存到 `docs/v1/review/implementation/12-stage-12-review.md`。

关键审查意见：

- 导出脱敏需要覆盖 provider credential。
- Observation 需要优先来自 `PreparedMessages` 中模型实际看到的内容。
- RL reward 需要校验 formal final verifier 来源。
- 未跟踪 `docs/build-your-own/` 不属于 Stage 12 提交范围。
- Preference pair 不能在 reward 相等但 outcome 不同时直接跳过。

处理结果：

- 增加 credential 脱敏规则和测试。
- SFT / RL observation 优先使用 `prepared_messages` 中的 tool observation，并保留 prepared/context replacement refs。
- formal final verifier 校验不通过时，导出样本标记为 `invalid_for_training=true` 并记录原因。
- `docs/build-your-own/` 和旧审查材料继续保持未暂存。
- preference ranking 改为 `(final_reward, outcome_rank)`，并新增 reward 相等 outcome 不同的 pair 测试。

## Known Limitations

- 第一版导出使用 JSONL，不提供 parquet。
- 本阶段只做基础正则脱敏和隐藏字段阻断；真实仓库导出前仍需要更完整的 secret scanning。
- 最后一次工具结果如果没有后续 model turn，就不存在对应 `prepared_messages` observation；Exporter 会显式记录 fallback 来源。
- SFT messages 从 transcript preview 恢复，assistant tool call 可以结构化导出，但不是 provider 原生消息格式的完整复刻。
- Preference pair 只实现同 task run 的最小 reward ranking。

## Commit

- Commit: `stage 12: implement training exporter`
- Commit message: `stage 12: implement training exporter`
