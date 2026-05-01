# Stage 02 只读审查记录

## 审查方式

本阶段安排了只读 sub agent 审查。审查 agent 没有修改文件。

## 审查重点

- 是否严格限于 Stage 02 范围。
- `run_config_facts.json` 是否在 Agent Loop 前写入，且不是普通 artifact。
- `run_metadata.json` 是否在 run 完成或 skipped 后写入，且不会在 Agent Loop 期间被引用。
- tool schema snapshot 是否通过 RunRecorder 写入 artifact manifest。
- 环境指纹和 source tree hash 是否复用 Stage 01 的 workspace facts。
- 是否破坏第一版 replay、verifier、workspace、trajectory 和 export。
- 测试是否覆盖正例和负例。

## 审查发现

### P1

未发现 P1 问题。

### P2

1. 工作区存在 Stage 02 范围外的既有文档重组和未跟踪文件。处理方式：不回滚、不删除，提交时只暂存 Stage 02 相关文件。
2. `run_metadata.json` 写入早于 `run_finished` 和 `finalize_run`。处理方式：移动写入顺序，先追加 `run_finished`、写 summary 并 finalize，再写最终 `run_metadata.json`。
3. `run_metadata.json` 缺少直接 tool schema snapshot 引用。处理方式：在 `RunMetadata` 中增加 `tool_protocol`，包含 `tool_schema_snapshot_ref` 和 snapshot sha256。
4. 环境指纹固定写 `setup_artifact_hash=none`，且缺少 `dependency_state_ref`。处理方式：新增 dependency state artifact，并把 setup artifact hash 和 dependency state ref 写入 `WorkspaceExecutionFacts`。

### P3

1. 缺少 Stage 02 阶段日志。处理方式：新增 `docs/v2/implementation-log/stage-02.md`。
2. 测试没有断言根目录事实文件不进入 artifact manifest。处理方式：新增 unit 和 integration 断言。

## 审查后修改

- 更新 metadata 写入时序。
- 在 `RunMetadata` 中直接记录 tool protocol。
- 扩展环境指纹输入，记录 dependency state ref 和 setup artifact hash。
- 补充 success path、quality gate skipped path 和 root fact manifest 负例测试。
- 新增本审查记录和 Stage 02 implementation log。

## 审查后验证

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v2_schemas.py tests/unit/test_run_metadata.py tests/unit/test_tool_schema_snapshot.py tests/integration/test_minimal_vertical_slice.py tests/integration/test_eval_runner_quality_gate.py
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q
```

验证结果：

- 综合针对性测试通过，37 个测试通过。
- 编译通过。
- 全量测试通过，215 个测试通过。

## 结论

审查提出的 P2 已修复，P3 已补齐。Stage 02 可以提交，并可以进入 Stage 03。
