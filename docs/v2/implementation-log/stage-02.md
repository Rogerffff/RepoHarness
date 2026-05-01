# Stage 02: run_config_facts、run_metadata、环境指纹和 tool schema snapshot

## 本阶段目标

本阶段目标是让第二版新 run 拥有稳定事实来源。`run_config_facts.json` 必须在 Agent Loop 前写入，作为不可变配置事实；`run_metadata.json` 必须在 run 完成或被 quality gate 跳过后写入，作为最终运行事实。本阶段不实现 inspect-run 第二版展示，不实现 export audit，不引入新 scaffold，也不接入真实模型供应商。

## 本阶段实现内容

- 新增 `run_metadata/fingerprint.py`：
  - 计算 source checkout 的稳定 source tree hash。
  - 排除 `.git/`、缓存目录和构建产物目录。
  - 写入 local process backend 的 `WorkspaceBackendFacts`、`WorkspaceExecutionFacts` 和 `SourceCheckoutFacts`。
  - 记录 dependency state artifact ref 和 setup artifact hash；没有 setup 时明确写 `none`。
- 新增 `run_metadata/tool_snapshot.py`：
  - 根据当前工具注册表生成 `ToolSchemaSnapshot`。
  - 记录工具顺序、工具版本、模型可见描述、输入输出 schema、权限属性和输出限制。
  - 通过 `RunRecorder.write_json_artifact` 写入 artifact manifest。
- 新增 `run_metadata/writer.py`：
  - 原子写入根目录 `run_config_facts.json`。
  - 在 run finished 和 `run_status.json = FINALIZED` 后原子写入根目录 `run_metadata.json`。
  - 生成 `RunConfigFactsRef` 和 `RunMetadataRef`，二者不是普通 `ArtifactRef`。
- 修改 `evaluation/runner.py`：
  - 在正式 Agent Loop 前写入 tool schema snapshot artifact、dependency state artifact、environment fingerprint 和 `run_config_facts.json`。
  - 成功、失败和 quality gate skipped 路径都会写最终 `run_metadata.json`。
  - summary 中记录 `run_config_facts.json` 和 `run_metadata.json` 的路径。
- 修改 `agent_loop/loop.py`：
  - `model_call_started` 和 `model_call_completed` 事件引用 `run_config_facts_ref`。
  - Agent Loop 期间不引用 `RunMetadataRef`。
- 增加 Stage 02 单元测试和集成测试覆盖。

## 修改的主要文件

- `src/repo_harness/run_metadata/fingerprint.py`
- `src/repo_harness/run_metadata/tool_snapshot.py`
- `src/repo_harness/run_metadata/writer.py`
- `src/repo_harness/run_metadata/__init__.py`
- `src/repo_harness/run_metadata/schemas.py`
- `src/repo_harness/evaluation/runner.py`
- `src/repo_harness/agent_loop/loop.py`
- `tests/unit/test_run_metadata.py`
- `tests/unit/test_tool_schema_snapshot.py`
- `tests/unit/test_v2_schemas.py`
- `tests/integration/test_minimal_vertical_slice.py`
- `tests/integration/test_eval_runner_quality_gate.py`

## 生成的机器可读产物

通过集成测试生成的 run directory 中会出现：

- `run_config_facts.json`
- `run_metadata.json`
- `artifacts.json` 中的 `tool_schema_snapshot` artifact
- `artifacts.json` 中的 `dependency_state` artifact

这些产物由测试临时目录生成，没有提交到 Git。

## 运行的验证命令

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_run_metadata.py tests/unit/test_tool_schema_snapshot.py tests/integration/test_minimal_vertical_slice.py
PATH=.venv/bin:$PATH python -m pytest tests/integration/test_export_from_run.py tests/unit/test_export.py
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v2_schemas.py tests/unit/test_run_metadata.py tests/unit/test_tool_schema_snapshot.py tests/integration/test_minimal_vertical_slice.py tests/integration/test_eval_runner_quality_gate.py
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q
```

## 验证结果

- Stage 02 针对性 run metadata、tool schema snapshot 和 minimal vertical slice 测试通过，10 个测试通过。
- 导出回归测试通过，10 个测试通过。
- 修复审查意见后的综合针对性测试通过，37 个测试通过。
- `python -m compileall src` 通过。
- 全量测试通过，215 个测试通过。

## 正例证据

- 成功 replay run 会生成 `run_config_facts.json` 和 `run_metadata.json`。
- `run_config_facts.json` 中记录 provider、model id、scaffold、预算、权限、上下文、verifier、reward、execution facts 和 tool protocol。
- `run_metadata.json` 中记录 `run_config_facts_ref`、`tool_protocol`、final verifier status、run outcome、metrics summary、artifact manifest status、failure diagnostics 和 export readiness。
- tool schema snapshot 通过 RunRecorder 写入 artifact，且 artifact manifest 可解析。
- model call events 包含 `run_config_facts_ref`，且不包含 `run_metadata_ref`。
- quality gate skipped run 也会生成最终 `run_metadata.json`，并记录 export readiness 阻断原因。

## 负例证据

- `run_config_facts.json` 和 `run_metadata.json` 不会作为普通 artifact 写入 `artifacts.json`。
- `run_config_facts.json` 已存在时，writer 会拒绝覆盖，保持不可变配置事实。
- source tree hash 会排除 `.git/` 和 `__pycache__/`。
- quality gate skipped run 的 `export_readiness.training_export_ready = false`，不会伪装成可训练样本。

## 允许降级项

- local process mode 只记录事实，不声称生产级隔离能力。
- 当前默认记录第一版 replay 行为实际暴露了 oracle hidden feedback，因为第一版 `run_tests` 模型可见输出包含 fail-to-pass 和 pass-to-pass 结构化信息。Stage 07 会引入正式 `test_feedback_policy` 运行时约束。
- `dependency_state.json` 继续作为第一版根目录兼容文件保留，同时新增 artifact-backed dependency state ref。

## 禁止降级项

- 不能把 `run_config_facts.json` 或 `run_metadata.json` 当作普通 `ArtifactRef`。
- Agent Loop 期间不能引用尚未最终写入的 `RunMetadataRef`。
- tool schema snapshot 必须通过 RunRecorder 写 artifact，不能绕过 artifact manifest。
- run metadata 必须在最终状态事实齐全后写入。

## 已知限制

- `inspect-run` 尚未展示第二版 metadata 状态；这是 Stage 03。
- export audit 尚未消费 `run_metadata.json`；这是 Stage 04。
- feedback policy 运行时约束尚未生效；这是 Stage 07。
- Docker backend 仍未实现；这是 Stage 14 的范围。

## 是否偏离设计文档

未发现必须记录的设计冲突。本阶段保持 Task Adapter、Workspace Adapter、RunRecorder、Agent Loop 和 Eval Runner 的既有边界：Task Adapter 不创建 workspace，tool schema snapshot 通过 RunRecorder 记录，最终 run metadata 由 Eval Runner 在 run 完成后写出。

## sub agent 审查结论

已安排只读 sub agent 审查。审查未发现 P1 问题。审查提出的 P2 问题已经处理：

- Stage 02 commit 必须排除既有无关文档重组：提交时只暂存本阶段相关文件。
- `run_metadata.json` 写入早于 `run_finished` 和 finalize：已调整为先写 `run_finished` 事件并 `finalize_run`，再写最终 `run_metadata.json`。
- `run_metadata.json` 缺少直接 tool schema snapshot 引用：已在 `RunMetadata.tool_protocol` 中记录。
- 环境指纹缺少 dependency state ref 和 setup artifact hash：已补充字段传入与测试。

审查提出的 P3 已处理：

- 新增本阶段日志。
- 增加 root fact 文件不进入 artifact manifest 的负例测试。
- 增加 quality gate skipped 路径的 metadata 覆盖。

审查记录保存到 `docs/v2/review/implementation/stage-02-review.md`。

## 是否可以进入下一阶段

可以进入 Stage 03。进入下一阶段前，Stage 02 commit 必须只包含当前阶段相关代码、测试、阶段日志和审查记录。
