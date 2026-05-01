# Stage 01: 第二版 schema、版本常量和基础测试

## 本阶段目标

本阶段目标是先定义第二版新增对象的机器可校验形状，避免后续阶段使用散乱字典传递关键运行事实。本阶段不改变第一版 replay-only 最小闭环，不改变 Agent Loop 行为，不接入真实模型供应商，不生成第二版 run metadata 运行产物。

## 本阶段实现内容

- 在 `schema_versions.py` 中新增第二版版本常量，包括 run metadata、环境指纹、tool schema snapshot、export audit、export manifest、pairing policy、experiment、scaffold registry 和 model client protocol。
- 新增 `repo_harness.run_metadata` 模块，定义：
  - `RunConfigFacts` 和 `RunConfigFactsRef`。
  - `RunMetadata` 和 `RunMetadataRef`。
  - `EnvironmentFingerprint`、`ExecutionModeFacts`、`WorkspaceBackendFacts`、`WorkspaceExecutionFacts` 和 `SourceCheckoutFacts`。
  - `FailureDiagnostics`、`ToolSchemaSnapshot`、`ToolProtocolFacts` 和 `RunMetadataSource`。
- 新增 `workspace.protocol`，定义 `WorkspaceBackend`、`WorkspaceAdapter`、`WorkspacePaths`、`WorkspaceCommandResult` 和 `WorkspaceBackendError`。
- 扩展导出 schema，新增 `ExportRecordQuality`、`ExportManifest`、`ExportAuditReport`、`ExportAuditItem`、`ExportAuditSample`、`PairingPolicy` 和 `CompareScope`。
- 扩展 `ExportRecord`，新增强类型 `quality.training_eligibility`，并保持第一版 `filter_status`、`invalid_for_training` 和 `invalid_reason` 的兼容构造方式。
- 扩展评测 schema，新增 `TestFeedbackPolicy`、`FeedbackTestsPassedPolicy`、`ResolvedFeedbackPolicyFacts`、`ExperimentConfig` 和 `ExperimentRunSpec`。
- 扩展模型客户端 schema，新增 `ModelRequestContext`、`ModelGenerationRequest` 和 `ModelProviderOptions`，并继续复用既有 `ProviderCredentialPolicy`。
- 为 `LocalWorkspaceAdapter` 增加 `backend = WorkspaceBackend.local_process`，只让它满足协议事实，不改变本地执行行为。
- 新增 `tests/unit/test_v2_schemas.py`，覆盖第二版 schema 的正例和负例。

## 修改的主要文件

- `src/repo_harness/schema_versions.py`
- `src/repo_harness/run_metadata/__init__.py`
- `src/repo_harness/run_metadata/schemas.py`
- `src/repo_harness/workspace/protocol.py`
- `src/repo_harness/workspace/adapter.py`
- `src/repo_harness/workspace/__init__.py`
- `src/repo_harness/export/schemas.py`
- `src/repo_harness/export/__init__.py`
- `src/repo_harness/evaluation/schemas.py`
- `src/repo_harness/evaluation/__init__.py`
- `src/repo_harness/model_client/schemas.py`
- `src/repo_harness/model_client/__init__.py`
- `tests/unit/test_v2_schemas.py`

## 生成的机器可读产物

本阶段没有生成 run directory 或 export directory。新增的机器可读产物是第二版 Pydantic schema 和对应单元测试，用于后续阶段写入 `run_config_facts.json`、`run_metadata.json`、`export_manifest.json` 和 `audit_report.json` 时复用。

## 运行的验证命令

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v2_schemas.py tests/unit/test_export.py
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_core_schemas.py
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v2_schemas.py tests/unit/test_export.py tests/unit/test_core_schemas.py
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q
```

## 验证结果

- `tests/unit/test_v2_schemas.py tests/unit/test_export.py` 通过，16 个测试通过。
- `tests/unit/test_core_schemas.py` 通过，5 个测试通过。
- 合并后的 schema、导出和核心 schema 测试通过，22 个测试通过。
- `python -m compileall src` 通过。
- 全量测试通过，209 个测试通过。

## 正例证据

- 合法 `RunConfigFacts`、`RunMetadata` 和 `ToolSchemaSnapshot` 可以 round trip。
- 合法 `ExportManifest`、`ExportAuditReport`、`PairingPolicy` 和 `ExperimentConfig` 可以 round trip。
- 合法 `ModelRequestContext` 必须包含 model call id、prepared messages ref、model input hash、tool schema snapshot ref、generation config、预算状态和 scaffold phase。
- 第一版 `ExportRecord` 仍然可以按旧方式构造；旧字段会推导出 `quality.training_eligibility`。

## 负例证据

- 非法 `training_eligibility` 会被拒绝。
- `training_eligibility = invalid` 且 `invalid_for_training = false` 会被拒绝。
- 非法 audit status 会被拒绝。
- 缺少硬门控字段的 `CompareScope` 会被拒绝。
- `RunConfigFactsRef` 和 `RunMetadataRef` 的路径、sha256、schema_version 混用会被拒绝。
- `feedback_tests_passed_policy = not_applicable` 作为用户配置会被拒绝。
- `test_feedback_policy = disabled` 但解析后不是 `not_applicable` 会被拒绝。
- `oracle_hidden_feedback` 与 SWE-Bench-like final-only 组合会被拒绝。

## 允许降级项

- 本阶段只定义 schema，不要求写入真实 `run_config_facts.json` 或 `run_metadata.json`。
- 本阶段只定义 export manifest 和 audit report schema，不要求导出器生成 format-specific export directory。
- 本阶段只定义 workspace backend 协议，不实现 Docker backend。

## 禁止降级项

- 不能改变第一版 replay、workspace、verifier、trajectory 或 export 的既有行为。
- 不能让第二版 `RunConfigFactsRef` 和 `RunMetadataRef` 混用。
- 不能把 provider、model、scaffold、预算、权限模式和工具策略藏进自由文本 metadata。
- 不能新增第二套 credential policy 名称。

## 已知限制

- `RunConfigFacts` 和 `RunMetadata` 尚未由运行器写入；这属于 Stage 02。
- `inspect-run` 尚未展示第二版 metadata；这属于 Stage 03。
- 导出 manifest、audit report 和 preference pair 硬门控尚未实际接入导出器；这属于 Stage 04 和 Stage 05。
- `ModelClient` 协议目前只有请求上下文 schema，运行器和 Agent Loop 尚未切换到通用协议；这属于 Stage 07。

## 是否偏离设计文档

未发现必须记录的设计冲突。本阶段按 `docs/v2/implementation-plan.md` 的 Stage 01 范围推进，并保留第一版 replay-only 行为。

## sub agent 审查结论

已安排只读 sub agent 审查。审查未发现 P1 问题。审查提出三个需要处理的重点：

- 不要把既有文档重组混入 Stage 01 commit：本阶段会只暂存 Stage 01 相关代码、测试、阶段日志和审查记录。
- 补充 Stage 01 implementation log：已补充本文件。
- `RunConfigFacts` 需要强校验反馈策略组合：已修复并补充测试。

审查提出的 P3 也已在阶段范围内处理：

- `RunConfigFactsRef` 和 `RunMetadataRef` 的 `schema_version` 改为固定值，并补充混用负例。
- `LocalWorkspaceAdapter` 增加 `backend` 属性以满足新协议。

审查记录保存到 `docs/v2/review/implementation/stage-01-review.md`。

## 是否可以进入下一阶段

可以进入 Stage 02。进入下一阶段前，Stage 01 commit 必须只包含当前阶段相关文件，不能包含既有无关文档移动、删除或未跟踪目录。
