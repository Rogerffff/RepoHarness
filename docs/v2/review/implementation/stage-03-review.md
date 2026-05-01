# Stage 03 只读审查记录

## 审查方式

本阶段安排了只读 sub agent 审查。审查 agent 没有修改文件。初审发现两个 P2 后，主 agent 进行了修复，并补充了负例测试。

## 审查重点

- 是否严格限于 Stage 03 范围。
- inspect-run 是否只读展示第二版 metadata 状态和 legacy metadata 兼容状态。
- 第一版 legacy run 缺失 `run_config_facts.json` 和 `run_metadata.json` 时是否仍可读取。
- 第二版 partial run 是否不会被伪装成 legacy run。
- 是否没有回填 run directory，没有绕过 RunRecorder。
- 是否没有破坏第一版 replay 和 export 路径。
- 是否展示 provider、model id、scaffold、tool schema snapshot、export audit 和 failure diagnostics。
- 是否存在循环导入或对象所有权混乱。
- 是否缺少阶段验收测试。

## 初审发现

### P1

未发现 P1 问题。

### P2

1. 损坏的 metadata 文件会被误判为缺失或 legacy。处理方式：`inspect_run_metadata` 现在基于文件是否存在和解析错误分别判断 `missing`、`legacy_missing` 和 `invalid`。损坏的 `run_config_facts.json` 显示为 `Run config facts: invalid`；损坏的 `run_metadata.json` 显示为 `Run metadata: invalid` 和 `Metadata source: invalid`。
2. Tool schema snapshot 状态没有校验协议 hash。处理方式：`_tool_schema_snapshot_status` 现在同时校验 artifact ref sha、artifact manifest sha、artifact 文件 sha，以及 `tool_protocol.tool_schema_snapshot_sha256` 与 snapshot 文件内 `snapshot_sha256` 的一致性。

### P3

阶段验收测试缺少负例覆盖。处理方式：新增损坏配置、损坏最终 metadata、`run_config_facts_ref.sha256` 不匹配、tool snapshot 协议哈希不匹配和 artifact 缺失测试。

## 审查后修改

- 修复 metadata 状态判断，避免 corrupt 文件被降级成 legacy 或 missing。
- 强化 tool schema snapshot 状态检查。
- 修复 `run_metadata.__init__` 的 eager import 循环问题，使用懒加载保留对外导出。
- 补充 inspect-run 正例和负例单元测试。

## 审查后验证

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_inspect_run.py
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_inspect_run.py tests/integration/test_export_from_run.py tests/unit/test_run_recorder.py tests/unit/test_v2_schemas.py tests/unit/test_run_metadata.py tests/unit/test_tool_schema_snapshot.py tests/integration/test_minimal_vertical_slice.py tests/integration/test_eval_runner_quality_gate.py
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q
```

验证结果：

- inspect-run 单元测试通过，8 个测试通过。
- 综合针对性测试通过，61 个测试通过。
- 编译通过。
- 全量测试通过，223 个测试通过。

## 结论

初审 P2 已修复，P3 已补齐。复审未发现新的 P1 或 P2，并确认 inspect-run 单元测试、export 回归和定向导入检查通过。Stage 03 可以提交，并可以进入 Stage 04。
