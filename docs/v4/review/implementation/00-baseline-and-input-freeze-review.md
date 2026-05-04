# V4 阶段 0 只读审查记录：基线确认和实施输入冻结

## 审查范围

本次审查覆盖 V4 阶段 0 的实现、测试、机器产物和 V3 acceptance 兼容修复。审查对象包括：

- `src/repo_harness/schema_versions.py`
- `src/repo_harness/v4_visibility.py`
- `src/repo_harness/v4_implementation_inputs.py`
- `src/repo_harness/cli/main.py`
- `src/repo_harness/v3_acceptance.py`
- `tests/unit/test_v4_implementation_inputs.py`
- `tests/integration/test_v3_acceptance_stage12.py`
- `docs/v4/evidence/implementation-inputs/`
- `docs/v4/implementation-log/00-baseline-and-input-freeze.md`

## 初审结论

subagent 初审未发现 P1 问题，但发现 3 个 P2 问题，因此初审时不允许进入阶段 1。

### P2-1：V3 command log immutable check 例外过宽

初审认为，`src` 和 `tests` 目录 input ref 的 sha256 漂移例外过宽，缺少对历史 pre-acceptance 命令、特定 command name 和具体 input ref 场景的限制。

修复结果：

- 只在复核 V3 `pre_acceptance_command_log` 时开启历史 repo input drift 例外。
- V3 `acceptance_command_log.jsonl` 仍保持严格 sha256 复核。
- 例外只适用于 `input_refs`，不适用于 `output_refs`。
- 例外只适用于 `python-m-pytest` 和 `inspect-v2-acceptance` 两个历史命令。
- 例外只适用于 `src` 和 `tests` 两个目录。
- 新增反向测试，证明没有历史命令身份的 `src` / `tests` 哈希漂移仍然失败。

### P2-2：V4 denylist binding 缺少 denylist sha256

初审认为，Stage 0 manifest、binding 和 audit report 只记录 denylist version，没有记录统一 denylist 规则集的稳定 sha256，后续阶段难以证明扫描规则没有漂移。

修复结果：

- 新增 `v4_contamination_denylist_sha256()`，对当前 `V4ContaminationDenylist` 的 schema version、visibility policy version、allowlist policy version、forbidden terms 和 adapter-visible regexes 生成稳定 sha256。
- `v4_implementation_input_manifest.json`、`v4_feasibility_input_binding.json` 和 `v4_implementation_input_audit_report.json` 均绑定相同 denylist sha256。
- `inspect-v4-implementation-inputs` 会重新计算 denylist sha256 并复核三份 Stage 0 产物。
- 当前 denylist sha256 为 `cd22eb930ffa308f1f17127fd33135354f835e13c947d1a9d96edb598ed67e6e`。

### P2-3：Stage 0 negative tests 未覆盖全部要求的污染场景

初审认为，原测试只覆盖 PR URL、`gold_patch` 和 40 位 fix commit hash，缺少 issue URL、PR 编号、issue 编号、hidden selector marker、AI session URL、PR body、PR diff、provider raw response、verifier raw output 等硬要求中的负例。

修复结果：

- 增加 issue URL 污染负例。
- 增加 PR 编号和 issue 编号污染负例。
- 增加 hidden selector marker 污染负例。
- 增加 AI session URL 污染负例。
- 增加 PR body 和 PR diff marker 污染负例。
- 增加 provider raw response marker 污染负例。
- 增加 verifier raw output marker 污染负例。
- 增加 denylist sha256 不匹配负例。

## P3 一并修复项

初审另提出两项 P3：

- baseline report 复核过于依赖 `baseline_status=passed`。
- AI session marker 覆盖偏枚举式。

修复结果：

- `inspect-v4-implementation-inputs` 现在要求 `v4_baseline_check_report.json` 的 `live_checks_run=true`。
- `inspect-v4-implementation-inputs` 会复核 `required_commands` 覆盖完整 baseline 命令集合。
- `inspect-v4-implementation-inputs` 会复核 `command_results` 覆盖完整 baseline 命令集合。
- denylist 和测试增加了更明确的 AI session URL marker。

## 复审结论

subagent 复审结论如下：

- 未发现 P1 问题。
- 未发现 P2 问题。
- 未发现 P3 问题。
- 之前 3 个 P2 均已解决。
- Stage 0 当前仍限定在 baseline confirmation 与 input freeze，没有越界到 adapter integration、task validity、run selection、final V4 acceptance 等后续阶段。
- 可以进入下一阶段。

复审还只读运行了：

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/repo-harness inspect-v4-implementation-inputs docs/v4/evidence/implementation-inputs/v4_implementation_input_manifest.json --assert-complete
```

结果通过，输出包含 `Inspect V4 implementation inputs: complete` 和 `Inspect V4 implementation inputs: passed`。

## 阶段准入结论

阶段 0 审查通过。没有 P1 / P2 / P3 阻塞问题。完成提交前验证后，可以进入阶段 1。
