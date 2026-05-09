# Stage 02: Core Schemas And Config Loading

## Scope

本阶段实现了：

- `RunConfig` 及其 YAML 读取、默认值和批量评测 `permission_mode=ask` 拒绝逻辑。
- `TaskDefinition`、`RunnableTask`、静态 `VerifierConfig`、任务 timeout 简写展开和 visibility 校验。
- `BaselineResult` 和 `ResolvedVerifierPlan`，并明确 `BaselineResult.status != valid` 时不能进入正式 agent run。
- `DependencyState`、`RunWorkspace`、`ExecutionResult`。
- `VerifierParser`、`TestCaseResult`、`VerifierResult`。
- `RewardMetadata`、`MetricsRecord`、`RunSummary`。
- `ArtifactRef`、`TranscriptRecord`、`TrajectoryEvent`。
- `ToolCall`、`ToolResult`、`PermissionDecision`。
- `ModelMessage`、`ModelResponse`、`ModelCallEvent`、`ProviderCredentialPolicy`、`ToolCallParseResult`。
- `ContextBuilderConfig`、`PreparedMessages`、`ContextReductionRecord`、`ContentReplacementState`、`ContentReplacementRecord`。
- `BudgetManager`、`BudgetState`、`AgentLoopState`、`ToolPairingState`。
- `ExportPolicy`、`ExportRecord`。
- `ReplayScript` 和 `ReplayStep`，并提供只返回模型可见 replay 内容的方法，避免 `expected_outcome`、注释和测试专用 metadata 进入模型上下文。
- 统一 schema 和策略版本常量。

本阶段明确不实现：

- 不实现 Task Adapter 的路径规范化和 fixture 加载。
- 不创建 workspace，不运行 setup，不运行 baseline verifier。
- 不实现 RunRecorder、artifact manifest、tool execution、permission rules、agent loop 或 training export。
- 不生成 `BaselineResult` 或 `ResolvedVerifierPlan` 的运行时业务逻辑，只定义 schema 和基本校验能力。

## Design References

- `docs/v1/implementation-plan.md`
- `docs/11-object-model-config-and-data-flow.md`
- `docs/06-task-dataset-and-environment-adapters.md`
- `docs/03-agent-loop-and-message-protocol.md`
- `docs/04-tool-system-and-orchestration.md`
- `docs/07-verifier-reward-and-evaluation.md`
- `docs/08-trajectory-store-and-training-export.md`

## Files Changed

- `src/repo_harness/schema_base.py`
- `src/repo_harness/schema_versions.py`
- `src/repo_harness/config/schemas.py`
- `src/repo_harness/config/loader.py`
- `src/repo_harness/tasks/schemas.py`
- `src/repo_harness/evaluation/schemas.py`
- `src/repo_harness/workspace/schemas.py`
- `src/repo_harness/verifier/schemas.py`
- `src/repo_harness/reward/schemas.py`
- `src/repo_harness/context/schemas.py`
- `src/repo_harness/tools/schemas.py`
- `src/repo_harness/permissions/schemas.py`
- `src/repo_harness/model_client/schemas.py`
- `src/repo_harness/agent_loop/schemas.py`
- `src/repo_harness/budget/schemas.py`
- `src/repo_harness/export/schemas.py`
- 各模块 `__init__.py`
- `tests/unit/test_config_schema.py`
- `tests/unit/test_task_schema.py`
- `tests/unit/test_core_schemas.py`
- `tests/unit/test_replay_script_schema.py`

## Verification

运行的命令：

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_config_schema.py tests/unit/test_task_schema.py tests/unit/test_core_schemas.py tests/unit/test_replay_script_schema.py
PATH=.venv/bin:$PATH python -m compileall src
```

结果：

- 通过。
- schema 单元测试收集并通过 20 个测试。
- `compileall` 通过。

## Review

审查方式：

- 主实现 agent 自查。
- sub agent 只读审查。

关键审查意见：

- 部分嵌套 Pydantic schema 缺少 `schema_version`，不利于后续持久化和兼容迁移。
- `ExportRecord.payload` 和 `ExportRecord.metadata` 是开放 dict，需要在 schema 层先建立隐藏字段和本机绝对路径的红线。
- `RunnableTask` 携带 `decontamination_metadata`，后续 Context Builder 容易误用，建议提供模型可见投影并增加测试。
- 测试缺口包括：系统性断言所有 schema 都有 `schema_version`，覆盖 `BaselineResult.status = invalid/flaky`，覆盖 `pass_to_pass_tests` 模型可见负例，以及导出和 RunnableTask 投影的隐藏信息隔离。

处理结果：

- 采纳：为所有 `StrictBaseModel` 子类补充或确认 `schema_version`，并增加系统性测试。
- 采纳：`ExportRecord` 增加隐藏字段和本机绝对路径校验，测试覆盖 `gold_patch` 和 `/Users/...` 路径拒绝。
- 采纳：`RunnableTask.agent_visible_view()` 只返回 Context Builder 可以使用的公开投影，测试确认不包含 `gold_patch`、fail/pass 测试列表、decontamination 私有说明。
- 采纳：新增 `BaselineResult` invalid、flaky 和 valid 的 `can_enter_agent_run` 测试。
- 采纳：新增 `pass_to_pass_tests` 不能标记为 `model_visible` 的负例测试。

## Known Limitations

- 当前 schema 只覆盖第一版对象边界和基础校验，不代表运行时功能已经完成。
- `TaskDefinition` 目前不做路径存在性、repo 边界或 fixture 根目录校验，这些属于阶段四 Task Adapter。
- `VerifierResult` 暂不解析 pytest 输出，pytest parser 属于阶段六。
- `RunConfig` 的 `ask` 拒绝通过 `load_run_config(..., for_batch=True)` 和 `RunConfig.ensure_batch_safe()` 表达；单任务交互模式仍允许 `ask`。
- `ContentReplacementState` 只定义数据结构和 round-trip 校验，实际稳定替换策略属于阶段九。

## Commit

- Commit: `stage 02: add core schemas and config validation`
- Commit message: `stage 02: add core schemas and config validation`
