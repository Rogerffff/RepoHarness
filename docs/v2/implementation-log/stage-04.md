# Stage 04: export audit、training eligibility 和 export manifest

## 本阶段目标

本阶段目标是把训练导出从单个 JSONL 文件推进到可审计的规范导出目录。SFT、RL rollout 和 preference export 都必须生成 format-specific export directory，并包含正式数据文件、`export_manifest.json`、`audit_report.json` 和 `audit_report.md`。正式训练 JSONL 默认只能包含 `training_eligibility = trainable` 的样本；`diagnostic_only`、`skipped` 和 `invalid` 样本只能进入审计报告、统计摘要或 skipped 数据 artifact。

## 本阶段实现内容

- 新增 `export/audit.py`：
  - 为导出样本计算强类型 `training_eligibility`。
  - 审计 artifact manifest、artifact ref、tool call/tool result 配对、prepared observation 来源、SFT loss target、formal final verifier、reward metadata、hidden fields、本机路径、hidden test feedback 和 provider raw payload。
  - `oracle_hidden_feedback` 默认映射为 `diagnostic_only`；只有显式 `ExportPolicy.allow_oracle_feedback_training = true` 时才允许进入正式训练数据。
  - quality gate skipped 的 invalid/flaky baseline 映射为 `skipped`，不会因为跳过后缺少 final verifier/reward 而误标成训练 invalid。
  - preference export 会对 chosen/rejected 底层 run 全部执行 source run 审计，并在 audit sample 中记录 `source_run_ids`。
- 新增 `export/manifest.py`：
  - 生成唯一 `export_id`。
  - 写入规范数据文件、manifest、JSON audit 和 Markdown audit。
  - 计算并记录数据文件、audit JSON 和 audit Markdown 的 sha256。
- 新增 `export/inspect.py` 和 CLI `inspect-export`：
  - 检查 manifest、数据文件、audit JSON、audit Markdown、哈希绑定和正式数据文件内容。
  - `--assert-clean` 会在 manifest/audit/data 绑定错误、failed audit report 或 failed audit item 时失败。
  - `--require-trainable-samples` 用于明确要求至少一个正式 trainable 样本。
- 修改 `export/exporter.py`：
  - SFT、RL 和 preference 都写 `exports/<export_id>/`。
  - 继续写第一版 convenience 文件 `exports/sft.jsonl`、`exports/rl.jsonl`、`exports/preference.jsonl` 或 `exports/preference_skipped.json`。
  - convenience 文件保留全部审计后记录，规范 `data.*.jsonl` 只写 trainable 记录。
  - `preference_skipped.json` 也写入规范 export directory，并生成 manifest 和 audit report。
  - export metadata 从 `run_config_facts.json` 和 `run_metadata.json` 读取 provider、model id、scaffold、policy 和 tool schema facts；legacy run 标记为 `legacy_inferred`。
- 修改 `export/schemas.py`：
  - `ExportPolicy` 增加 `allow_oracle_feedback_training`。
  - `ExportAuditSample` 增加 `metadata_source` 和 `source_run_ids`。
- 修改 CLI：
  - `repo-harness export` 增加 `--allow-oracle-feedback-training`。
  - 新增 `repo-harness inspect-export`。

## 修改的主要文件

- `src/repo_harness/export/audit.py`
- `src/repo_harness/export/manifest.py`
- `src/repo_harness/export/inspect.py`
- `src/repo_harness/export/exporter.py`
- `src/repo_harness/export/schemas.py`
- `src/repo_harness/export/__init__.py`
- `src/repo_harness/cli/main.py`
- `tests/unit/test_export.py`
- `tests/integration/test_export_from_run.py`

## 生成的机器可读产物

阶段验收运行生成了：

- `runs/v2-export-audit-20260501T183649Z/exports/sft_*/data.sft.jsonl`
- `runs/v2-export-audit-20260501T183649Z/exports/sft_*/export_manifest.json`
- `runs/v2-export-audit-20260501T183649Z/exports/sft_*/audit_report.json`
- `runs/v2-export-audit-20260501T183649Z/exports/sft_*/audit_report.md`
- `runs/v2-export-audit-20260501T183649Z/exports/rl_*/data.rl.jsonl`
- `runs/v2-export-audit-20260501T183649Z/exports/rl_*/export_manifest.json`
- `runs/v2-export-audit-20260501T183649Z/exports/rl_*/audit_report.json`
- `runs/v2-export-audit-20260501T183649Z/exports/rl_*/audit_report.md`
- `runs/v2-export-audit-20260501T183649Z/exports/preference_*/preference_skipped.json`
- `runs/v2-export-audit-20260501T183649Z/exports/preference_*/export_manifest.json`
- `runs/v2-export-audit-20260501T183649Z/exports/preference_*/audit_report.json`
- `runs/v2-export-audit-20260501T183649Z/exports/preference_*/audit_report.md`

这些运行产物作为本地验收证据保留在 `runs/`，未提交到 Git。

## 运行的验证命令

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_export.py tests/integration/test_export_from_run.py
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_export.py tests/integration/test_export_from_run.py tests/unit/test_v2_schemas.py
PATH=.venv/bin:$PATH repo-harness run-batch --config tests/fixtures/run_configs/batch_replay.yaml --output-dir runs/v2-export-audit-20260501T183649Z
PATH=.venv/bin:$PATH repo-harness export runs/v2-export-audit-20260501T183649Z --format sft_jsonl
PATH=.venv/bin:$PATH repo-harness export runs/v2-export-audit-20260501T183649Z --format rl_jsonl
PATH=.venv/bin:$PATH repo-harness export runs/v2-export-audit-20260501T183649Z --format preference_jsonl
PATH=.venv/bin:$PATH repo-harness inspect-export runs/v2-export-audit-20260501T183649Z/exports --all --assert-clean
PATH=.venv/bin:$PATH repo-harness export runs/v2-export-audit-20260501T183649Z --format sft_jsonl --allow-oracle-feedback-training
PATH=.venv/bin:$PATH repo-harness inspect-export runs/v2-export-audit-20260501T183649Z/exports --all --format sft_jsonl --require-trainable-samples --assert-clean
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_export.py tests/integration/test_export_from_run.py tests/unit/test_v2_schemas.py tests/unit/test_inspect_run.py tests/integration/test_minimal_vertical_slice.py tests/integration/test_eval_runner_quality_gate.py
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q
```

## 验证结果

- 导出单元测试和集成测试通过，14 个测试通过。
- 导出 schema 回归通过，23 个测试通过。
- Stage 01 到 Stage 04 相关综合回归通过，53 个测试通过。
- Stage 04 批量 replay 验收路径通过：三种格式都生成规范 export directory、manifest、audit JSON 和 audit Markdown，`inspect-export --all --assert-clean` 通过。
- 显式允许 oracle feedback training 的 SFT 导出通过 `--require-trainable-samples`。
- `python -m compileall src` 通过。
- 全量测试通过，227 个测试通过。

## 正例证据

- SFT 和 RL 导出默认只把 trainable 样本写入 `data.sft.jsonl` 和 `data.rl.jsonl`。
- 默认 `oracle_hidden_feedback` 样本进入 `diagnostic_only`，不进入正式训练 JSONL。
- 显式 `--allow-oracle-feedback-training` 时，oracle 样本可在完整审计通过后进入 trainable。
- invalid/flaky baseline run 进入 `skipped`，并保留在 audit report 中。
- preference skipped 导出会同时生成 `preference_skipped.json`、manifest、audit JSON 和 audit Markdown。
- preference pair 的 chosen/rejected artifact refs 带有 `source_run_id`，审计会解析到正确底层 run。
- `inspect-export --assert-clean` 会检查 manifest、数据文件哈希、audit JSON、audit Markdown 和正式数据文件污染。

## 负例证据

- artifact manifest path escape 会被导出审计标记为 invalid，且不会进入正式训练 JSONL。
- provider raw response marker 出现在训练 payload 时，audit report 标记 failed，`inspect-export --assert-clean` 失败。
- 缺失 formal final verifier 的非 skipped run 会被标记为 invalid。
- preference 底层 rejected run 缺失 formal final verifier 时，preference 样本被标记 invalid，`data.preference.jsonl` 为空。
- `inspect-export --require-trainable-samples` 会在没有 trainable 样本时失败。

## 允许降级项

- 第一版 convenience 文件继续存在，作为兼容入口；规范事实来源是 `exports/<export_id>/export_manifest.json` 和 `audit_report.json`。
- legacy metadata 只读推断，不回填旧 run directory。
- Stage 04 不实现 Stage 05 的 preference compare scope 硬门控；当前 preference 仍沿用第一版同 task reward 排序，Stage 05 会收紧 compare scope。
- secret scanner 和 provider raw marker 检查是保守最小实现，后续 provider 阶段会继续扩展脱敏和 provider artifact 检查。

## 禁止降级项

- 正式训练 JSONL 默认不能包含 diagnostic_only、skipped 或 invalid 样本。
- `oracle_hidden_feedback` 默认不能进入正式训练 JSONL。
- hidden fields、provider raw response、raw request body、reasoning summary、本机绝对路径不能进入正式训练 payload。
- Training Exporter 只能读取已有 run directory，不能重新运行 verifier 或改写运行事实。
- preference 样本不能绕过 chosen/rejected 底层 run 的审计。

## 已知限制

- preference compare scope 硬门控尚未实现，这是 Stage 05 范围。
- audit Markdown 是由 JSON audit 派生的摘要，不作为训练事实来源。
- 更深层 secret scanner、跨 provider pairing 规则和 provider artifact 审计将在后续 provider 阶段继续增强。

## 是否偏离设计文档

未发现必须记录的设计冲突。为了同时满足批量验收和审计清晰性，本阶段将 quality gate skipped run 的缺失 final verifier/reward 映射为 `skipped` 审计项，而不是 `invalid`；这是对“任务被 quality gate 跳过”优先进入 skipped 的实现化处理。非 skipped run 缺失 formal final verifier 仍然是 invalid。

## sub agent 审查结论

Stage 04 是高风险阶段，已安排只读 sub agent 审查。初审发现一个 P1 和三个 P2：

- P1：preference export 使用合成 `source_run_id`，导致底层 run 审计被跳过。
- P2：export metadata 没有读取第二版 run metadata facts。
- P2：audit report 没有机器可读记录 legacy `metadata_source`。
- P2：`inspect-export --assert-clean` 没有对 failed audit report 失败。

修复后复审又发现一个 P2：

- preference artifact refs 没有绑定具体 source run，导致 rejected run 的 artifact ref 可能在 chosen run 下解析。

上述 P1/P2 均已修复。最终复审未发现新的 P1 或 P2，结论是可以提交 Stage 04。审查记录保存到 `docs/v2/review/implementation/stage-04-review.md`。

## 是否可以进入下一阶段

可以进入 Stage 05。进入下一阶段前，Stage 04 commit 必须只包含当前阶段相关代码、测试、阶段日志和审查记录。
