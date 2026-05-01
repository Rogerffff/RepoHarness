# Stage 04 只读审查记录

## 审查方式

本阶段是高风险阶段，安排了只读 sub agent 审查。审查 agent 没有修改文件。审查分为初审、修复后复审和 preference artifact ref 复审。

## 审查重点

- 是否严格限于 Stage 04 范围。
- SFT、RL rollout 和 preference export 是否都有规范 export directory、manifest、JSON audit 和 Markdown audit。
- 正式训练 JSONL 是否默认只包含 trainable 样本。
- `diagnostic_only`、`skipped` 和 `invalid` 样本是否进入 audit 或 skipped artifact。
- `oracle_hidden_feedback` 默认是否为 diagnostic_only。
- provider raw response、raw request body、reasoning summary、hidden metadata 和本机路径是否有审计。
- preference export 是否审计 chosen/rejected 底层 run。
- `inspect-export --assert-clean` 是否覆盖 manifest、data sha、audit JSON、audit Markdown 和 failed audit。
- 是否没有提前实现 Stage 05 preference compare scope 硬门控。

## 初审发现

### P1

1. Preference export 使用合成 `source_run_id`，导致底层 source run 审计被跳过。处理方式：preference record 在 metadata 中记录 `source_run_ids`，audit 会针对 chosen/rejected 两个底层 run 执行 artifact manifest、artifact ref、tool pairing、formal final verifier、reward metadata 和 metadata source 检查。

### P2

1. Export metadata 没有读取 `run_config_facts.json` 和 `run_metadata.json`。处理方式：`_safe_metadata` 改为优先读取第二版 facts，并记录 provider、model、scaffold version、tool policy、permission policy、context policy、prompt template、reward formula、final verifier mode 和 tool schema snapshot hash。
2. Legacy metadata source 没有机器可读记录。处理方式：`ExportAuditSample` 增加 `metadata_source` 和 `source_run_ids`。
3. `inspect-export --assert-clean` 不会因为 failed audit report 或 failed audit item 失败。处理方式：inspect-export 现在会检查 audit status 和 failed audit items。

### P3

未发现越界实现 Stage 05 compare scope。当前 preference 仍是第一版同 task reward 排序，Stage 05 会实现硬门控。

## 复审发现

### P1

未发现新的 P1。

### P2

1. Preference artifact refs 没有绑定具体 source run，导致 rejected run 的 artifact ref 可能在 chosen run directory 下解析。处理方式：chosen/rejected 的 verifier artifact ref 通过 `source_run_id` 标注来源；artifact ref 解析时按 `source_run_id` 选择对应 run directory。

## 审查后验证

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_export.py tests/integration/test_export_from_run.py
PATH=.venv/bin:$PATH python -m pytest tests/integration/test_eval_runner_quality_gate.py tests/unit/test_run_metadata.py tests/unit/test_tool_schema_snapshot.py
```

sub agent 复审结果：

- 导出单元和集成测试通过，14 个测试通过。
- eval runner quality gate、run metadata 和 tool schema snapshot 测试通过，21 个测试通过。
- 最终复审未发现新的 P1 或 P2。

## 主流程补充验证

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_export.py tests/integration/test_export_from_run.py
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_export.py tests/integration/test_export_from_run.py tests/unit/test_v2_schemas.py tests/unit/test_inspect_run.py tests/integration/test_minimal_vertical_slice.py tests/integration/test_eval_runner_quality_gate.py
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q
```

验证结果：

- 导出测试通过，14 个测试通过。
- Stage 01 到 Stage 04 相关综合回归通过，53 个测试通过。
- 编译通过。
- 全量测试通过，227 个测试通过。

## 结论

初审和复审提出的 P1/P2 均已修复。Stage 04 可以提交，并可以进入 Stage 05。
