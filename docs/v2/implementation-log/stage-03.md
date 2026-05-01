# Stage 03: inspect-run 第二版展示和 legacy metadata 兼容

## 本阶段目标

本阶段目标是让 `repo-harness inspect-run <run_dir>` 能区分第一版 legacy run、第二版完整 metadata run 和第二版中断或损坏的 metadata run。inspect-run 必须只读展示状态，不能回填或改写 run directory。本阶段不实现 export audit，不实现 preference pair，不引入实验运行器、scaffold registry 或 provider adapter。

## 本阶段实现内容

- 新增 `run_metadata/reader.py`：
  - 只读读取 `run_config_facts.json` 和 `run_metadata.json`。
  - 对第一版历史 run 返回 `Run metadata: legacy_missing` 和 `Metadata source: legacy_inferred`。
  - 对已写入 `run_config_facts.json` 但缺少最终 `run_metadata.json` 的第二版 run 返回 `Run metadata: missing`，不伪装成 legacy。
  - 对损坏的 `run_config_facts.json` 或 `run_metadata.json` 返回 `invalid` 状态并输出 metadata diagnostics。
  - 校验 `run_metadata.json` 中的 `run_config_facts_ref.sha256`。
  - 校验 tool schema snapshot 的 artifact ref、artifact manifest sha、artifact 文件 sha，以及 `tool_protocol.tool_schema_snapshot_sha256` 和 snapshot 文件内 `snapshot_sha256` 的一致性。
  - 检测 export audit 是否已经生成。
  - 提取 provider、model id、scaffold id、scaffold version 和 failure diagnostics。
- 修改 `trajectory/inspect.py`：
  - 在原有 status、events、artifacts、metrics、baseline、final verifier、reward 和 summary 输出基础上新增第二版 metadata 展示。
  - 保留旧 run directory 的只读可检查行为。
- 修改 `run_metadata/__init__.py`：
  - 保留 Stage 01 和 Stage 02 对外导出。
  - 对依赖 workspace 或 writer 的辅助函数使用懒加载，避免 inspect-run 只读路径触发循环导入。
- 新增 `tests/unit/test_inspect_run.py`：
  - 覆盖 legacy 缺失 metadata。
  - 覆盖第二版缺失最终 metadata。
  - 覆盖第二版 metadata 和 tool schema snapshot 正例。
  - 覆盖损坏配置、损坏最终 metadata、`run_config_facts_ref` 哈希不匹配、tool schema snapshot 协议哈希不匹配和 artifact 缺失负例。

## 修改的主要文件

- `src/repo_harness/run_metadata/reader.py`
- `src/repo_harness/run_metadata/__init__.py`
- `src/repo_harness/trajectory/inspect.py`
- `tests/unit/test_inspect_run.py`

## 生成的机器可读产物

本阶段不新增持久机器可读运行产物。新增 reader 和 inspect-run 输出会读取以下既有或后续阶段产物：

- `run_config_facts.json`
- `run_metadata.json`
- `artifacts.json`
- `exports/**/audit_report.json`
- tool schema snapshot artifact

测试中的 run directory 均位于 pytest 临时目录，没有提交到 Git。

## 运行的验证命令

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_inspect_run.py tests/integration/test_export_from_run.py tests/unit/test_run_recorder.py
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v2_schemas.py tests/unit/test_run_metadata.py tests/unit/test_tool_schema_snapshot.py tests/integration/test_minimal_vertical_slice.py tests/integration/test_eval_runner_quality_gate.py
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_inspect_run.py
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_inspect_run.py tests/integration/test_export_from_run.py tests/unit/test_run_recorder.py tests/unit/test_v2_schemas.py tests/unit/test_run_metadata.py tests/unit/test_tool_schema_snapshot.py tests/integration/test_minimal_vertical_slice.py tests/integration/test_eval_runner_quality_gate.py
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q
```

## 验证结果

- 初始 Stage 03 定向测试在收集阶段暴露循环导入，已通过 `run_metadata.__init__` 懒加载修复。
- 修复循环导入后，inspect、export 和 recorder 定向测试通过，19 个测试通过。
- Stage 01 到 Stage 03 相关回归测试通过，37 个测试通过。
- 修复 sub agent 初审 P2 后，`tests/unit/test_inspect_run.py` 通过，8 个测试通过。
- 修复 sub agent 初审 P2 后，综合针对性测试通过，61 个测试通过。
- `python -m compileall src` 通过。
- 全量测试通过，223 个测试通过。

## 正例证据

- legacy run 缺失 `run_config_facts.json` 和 `run_metadata.json` 时，inspect-run 显示 `Run config facts: missing`、`Run metadata: legacy_missing` 和 `Metadata source: legacy_inferred`。
- 第二版 partial run 已有 `run_config_facts.json` 但缺失最终 `run_metadata.json` 时，inspect-run 显示 `Run config facts: ok`、`Run metadata: missing` 和 `Metadata source: missing`。
- 第二版完整 run 可以显示 provider、model id、scaffold、tool schema snapshot 状态、export audit 状态和 failure diagnostics。
- tool schema snapshot 正例必须同时满足 artifact manifest 文件哈希和 protocol snapshot 哈希。

## 负例证据

- 损坏的 `run_config_facts.json` 显示为 `Run config facts: invalid`，不会被当成缺失的 legacy facts。
- 损坏的 `run_metadata.json` 显示为 `Run metadata: invalid` 和 `Metadata source: invalid`，不会被当成第一版 legacy run。
- `run_metadata.json` 中的 `run_config_facts_ref.sha256` 不匹配时，`Run metadata` 标记为 `invalid` 并输出 metadata diagnostics。
- tool schema snapshot artifact 缺失或 `tool_protocol.tool_schema_snapshot_sha256` 与 snapshot 文件内 `snapshot_sha256` 不一致时，`Tool schema snapshot` 标记为 `invalid`。

## 允许降级项

- legacy run 只做只读推断，不回填第二版 metadata。
- export audit 还没有生成时显示 `Export audit: not_generated`，这是 Stage 04 前的正常状态。
- provider、model 和 scaffold 信息只在 `run_config_facts.json` 或可读 metadata 中存在时展示；legacy run 可能缺少这些字段。

## 禁止降级项

- 第二版 partial run 不能伪装成第一版 legacy run。
- 损坏 metadata 不能显示为正常缺失或正常 legacy 状态。
- inspect-run 不能修改 run directory。
- inspect-run 不能绕过或重写 RunRecorder 产物。
- tool schema snapshot 不能只校验 artifact 文件存在，还必须校验协议哈希一致性。

## 已知限制

- export audit 仍未实现，只能显示是否存在，这是 Stage 04 范围。
- legacy metadata 的更完整导出推断仍属于 Stage 04 及后续审计范围。
- provider artifact 和 provider 错误分类尚未实现，这是 Stage 10 和 Stage 11 范围。

## 是否偏离设计文档

未发现必须记录的设计冲突。本阶段严格保持只读 inspection 边界，没有改写 run directory，没有让 export 重新运行 verifier，也没有将最终 verifier、reward 或 run outcome 引入 Agent Loop。

## sub agent 审查结论

已安排只读 sub agent 审查。初审未发现 P1，发现两个 P2：

- 损坏的 metadata 文件会被误判为缺失或 legacy。
- Tool schema snapshot 状态没有校验协议 hash。

两个 P2 均已修复，并补充负例测试。初审提出的 P3 是负例覆盖不足，已通过新增 inspect-run 单元测试处理。复审未发现新的 P1 或 P2，结论是可以提交 Stage 03。审查记录保存到 `docs/v2/review/implementation/stage-03-review.md`。

## 是否可以进入下一阶段

可以进入 Stage 04。进入下一阶段前，Stage 03 commit 必须只包含当前阶段相关代码、测试、阶段日志和审查记录。
