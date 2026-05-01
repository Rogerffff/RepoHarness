# Stage 01 只读审查记录

## 审查方式

本阶段安排了只读 sub agent 审查。审查对象是 Stage 01 的未提交改动，审查 agent 不修改文件。

## 审查重点

- 是否严格限于 `docs/v2/implementation-plan.md` 的 Stage 01 范围。
- 是否和 `docs/v2/scope-and-roadmap.md`、`docs/11-object-model-config-and-data-flow.md` 一致。
- 是否破坏第一版 replay 或 export 兼容。
- 新增 schema 是否保持 strict，是否都有 `schema_version`。
- `RunConfigFactsRef` 与 `RunMetadataRef` 是否能防止混用。
- `ExportRecord` 的 `quality.training_eligibility` 与旧字段是否兼容。
- `ModelRequestContext` 是否包含 Stage 01 要求的核心字段，且没有使用 `model_config` 字段名。
- Workspace Adapter protocol 是否只是接口骨架，没有提前实现 Docker 或改变 LocalWorkspaceAdapter 行为。
- `tests/unit/test_v2_schemas.py` 是否覆盖阶段要求中的主要正负例。

## 审查发现

### P1

未发现 P1 问题。

### P2

1. 当前工作区存在 Stage 01 范围外的既有文档重组、删除和未跟踪文件。处理方式：不回滚、不删除，也不纳入 Stage 01 commit；本阶段只暂存当前阶段相关文件。
2. 缺少 Stage 01 的 `docs/v2/implementation-log/` 阶段日志。处理方式：新增 `docs/v2/implementation-log/stage-01.md`。
3. `RunConfigFacts` 对 `test_feedback_policy` 和 `feedback_tests_passed_policy` 的组合校验不足。处理方式：改为枚举化字段，并增加 disabled、not_applicable、oracle hidden feedback 与 final-only 组合的负例测试。

### P3

1. `RunConfigFactsRef` 和 `RunMetadataRef` 的 `schema_version` 未固定。处理方式：改为 `Literal` 固定值，并增加 schema_version 混用负例。
2. `WorkspaceAdapter` 协议要求 `backend` 属性，但 `LocalWorkspaceAdapter` 尚未暴露。处理方式：增加 `backend = WorkspaceBackend.local_process`，不改变执行行为。

## 审查后修改

- 更新 `src/repo_harness/run_metadata/schemas.py`，补充 feedback policy 组合校验和 fact ref 固定 schema version。
- 更新 `src/repo_harness/workspace/adapter.py`，让本地 adapter 暴露 backend 属性。
- 更新 `tests/unit/test_v2_schemas.py`，补充策略组合和 fact ref schema version 负例。
- 新增阶段日志和本审查记录。

## 审查后验证

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v2_schemas.py tests/unit/test_export.py tests/unit/test_core_schemas.py
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q
```

验证结果：

- 针对性 schema、导出兼容和核心 schema 测试通过，22 个测试通过。
- 编译通过。
- 全量测试通过，209 个测试通过。

## 结论

审查发现的 P2 问题已经修复或通过只暂存当前阶段相关文件来规避。P3 问题已经在不扩大阶段范围的前提下修复。Stage 01 可以提交，并可以进入 Stage 02。
