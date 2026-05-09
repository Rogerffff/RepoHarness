# Pre-verl 上下文压缩实施计划

编写日期：2026-05-10

本文件是 `docs/resume/pre-verl-tool-result-compact-decision.md` 的实施文档。决策文档负责说明“为什么这样设计”，本文件负责说明“应该怎样落地、改哪些模块、每一步怎样验证”。

本文档中的“上下文压缩”指的是 RepoHarness 在调用模型之前，对模型可见消息、工具结果和必要的恢复索引进行受控改写，使软件工程智能体在长任务中仍然能够继续工作，同时保证轨迹可审计、可导出、可训练。

## 1. 实施目标

本轮改造需要落地四层能力：

1. 第零层工具结果压缩：单个工具结果过大时立即落盘，当前轮多个新工具结果聚合过大时按预算落盘，并在工具结果进入 provider-committed 主模型输入之后冻结它的可见命运。
2. 第一层 MicroCompact：当可清理的工具结果数量和可见字符总量都超过阈值时，把较旧的可清理工具结果内容替换成固定占位符，保留最近的可清理工具结果。
3. 第二层 AutoCompact：当准备发送给模型的上下文接近有效上下文预算时，用一次独立的 compact-only 模型调用生成结构化摘要，并用“压缩边界消息、摘要消息、近期原文尾部、恢复索引消息”重建后续上下文。
4. 第三层 Reactive Compact：只有当真实模型服务返回上下文超限错误时，执行 provider verified recovery。优先复用 AutoCompact 的紧急模式；如果 compact-only 输入本身超限或紧急压缩不可用，则使用按 API round 分组的 PTL fallback，保持工具调用和工具结果配对，插入 synthetic user marker，并最多重试一次主模型调用。

## 2. 不在本轮实施的内容

本轮不要实现以下能力：

1. 不实现 Claude Code 内部实验路径中的 Snip Compact。它主要是消息级裁剪思路的参考，不作为当前 RepoHarness 的主线能力。
2. 不实现依赖 Anthropic 私有能力的 cached MicroCompact。
3. 不实现依赖 Anthropic 私有能力的 API context management。
4. 不实现独立的 Context Collapse。当前 RepoHarness 没有子智能体体系，这条机制的收益不高。
5. 不实现跨任务长期 Session Memory。它可以在本轮 AutoCompact 和 Reactive Compact 稳定后再设计。
6. 不继续沿用当前“历史工具结果老化替换”为主线压缩机制。历史工具结果老化替换会破坏工具结果第一次被模型看到后的稳定性，不利于 prompt cache 和轨迹审计。

## 3. 当前代码基线

实施前需要明确当前代码的真实状态：

1. 配置入口在 `src/repo_harness/config/schemas.py` 的 `ContextManagementConfig`。当前主要字段是 `max_context_tokens = 120000`、`tool_result_aggregate_budget_chars = 40000`、`keep_recent_turns = 6`、`keep_recent_test_results = 2`、`compact_strategy = "deterministic_preview_replacement"` 和 `compact_threshold_ratio = 0.85`。
2. 当前压缩实现集中在 `src/repo_harness/context/manager.py`。`ContextManager.prepare_messages()` 每轮生成 `prepared_messages` artifact 和 `context_prepared` event。`ContextManager._reduce_messages()` 会扫描历史工具消息，并按历史工具结果聚合预算替换较旧工具结果。
3. 当前状态结构在 `src/repo_harness/context/schemas.py`。`ContentReplacementState` 和 `ContentReplacementRecord` 已经记录 seen tool result 和 replacement record，但当前语义还不是 Claude Code 风格的“第一次命运冻结”。
4. 工具定义、工具执行和工具结果构造在 `src/repo_harness/tools/minimal.py`。统一构造函数是 `_tool_result()`，工具结果 schema 是 `src/repo_harness/tools/schemas.py` 的 `ToolResult`。
5. 主循环在 `src/repo_harness/agent_loop/loop.py`。目前每轮先调用 `ContextManager.prepare_messages()`，如果 `prepared.token_estimate > budget_manager.max_context_tokens` 就直接停止并记录 `budget_exhausted`。
6. 模型请求 schema 在 `src/repo_harness/model_client/schemas.py`。真实 provider 的 HTTP 错误分类在 `src/repo_harness/model_client/providers/common.py`，当前已经能把 HTTP 413 和常见上下文超限文本归类为 `context_limit`。
7. pre-verl 运行检查主要在 `src/repo_harness/pre_verl_agentloop.py`，其中已经有 prepared messages 绑定检查和隐藏材料扫描。
8. 训练导出相关逻辑主要在 `src/repo_harness/export/exporter.py`、`src/repo_harness/export/audit.py` 和 `src/repo_harness/export/inspect.py`。
9. 失败诊断在 `src/repo_harness/run_metadata/writer.py` 和 `src/repo_harness/run_metadata/schemas.py`，当前已经识别 `context_limit` 和 `compaction_applied_but_insufficient_context_limit`。

## 4. 总体落地顺序

建议按以下顺序实施：

1. 扩展配置和 schema，但先保持旧行为可回退。
2. 增加工具结果 artifact 存储和安全恢复工具。
3. 改造单个工具结果过大时立即落盘。
4. 改造当前轮新工具结果聚合预算，并实现命运冻结。
5. 增加 MicroCompact。
6. 增加有效上下文预算计算。
7. 增加 AutoCompactRunner、compact-only 模型请求和摘要 schema。
8. 增加压缩后消息重建和恢复索引。
9. 把 AutoCompact 接入 `AgentLoop` 的模型调用前流程。
10. 把 Reactive Compact 接入真实 provider 上下文超限错误后的重试流程。
11. 更新 inspect、export audit、failure diagnostics 和验收脚本。
12. 用单元测试、集成测试、模拟长上下文运行和真实 targeted smoke 分层验证。

这个顺序的核心原因是：先保证工具结果层稳定，再让更高层的 AutoCompact 基于稳定的 model-visible prepared messages 工作。

## 5. 第一步：扩展配置和 schema

### 5.1 实施内容

修改 `src/repo_harness/config/schemas.py` 的 `ContextManagementConfig`，增加新的配置字段。建议保留旧字段一段时间，但把旧字段映射到新字段，避免已有测试和已有运行配置马上失效。

建议新增字段：

```python
class ContextManagementConfig(StrictBaseModel):
    schema_version: str = "repo_harness_context_management_config_v1"
    context_policy_snapshot_version: str = "repo_harness_context_policy_snapshot_v1"

    context_budget_policy: str = "model_window_with_optional_cap"
    model_context_window_tokens: int | Literal["auto"] = "auto"
    harness_context_cap_tokens: int | None = None
    main_output_reserve_tokens: int = 32000
    estimator_safety_margin_ratio: float = 0.03
    estimator_safety_margin_min_tokens: int = 20000

    tool_result_compact_policy: str = "claude_code_fresh_only_v1"
    freeze_tool_result_budget_decisions: bool = True
    freeze_tool_result_decisions_at: str = "provider_committed"
    max_single_tool_result_chars: int = 50000
    max_tool_results_per_turn_chars: int = 200000
    tool_result_recovery_tool: str = "read_tool_result_artifact"
    legacy_history_tool_result_replacement: bool = False

    microcompact_enabled: bool = True
    microcompact_policy: str = "count_based_tool_result_clear_v1"
    microcompact_trigger_compactable_tool_result_count: int = 30
    microcompact_trigger_compactable_tool_result_chars: int = 60000
    microcompact_keep_recent_compactable_tool_results: int = 15
    microcompact_cleared_message: str = "[Old tool result content cleared]"

    auto_compact_enabled: bool = True
    auto_compact_trigger_ratio: float = 0.85
    hard_context_limit_ratio: float = 0.97
    post_compact_target_ratio: float = 0.60
    post_compact_target_max_tokens: int = 300000
    auto_compact_max_consecutive_failures: int = 3
    auto_compact_summary_max_output_tokens: int = 16000
    preserve_recent_turns_after_compact: int = 6
    preserve_recent_tail_token_budget: int = 80000

    reactive_compact_enabled: bool = True
    local_context_limit_policy: str = "strict_local_preflight"
    reactive_compact_policy: str = "provider_verified_reactive"
    ptl_retry_policy: str = "auto_compact_then_round_truncate"
    reactive_compact_retry_limit: int = 1
```

需要同时更新 `src/repo_harness/context/schemas.py`：

1. 把 `ContentReplacementRecord` 的语义改成工具结果命运记录。建议新增 `replacement_decision` 字段，取值至少包括 `prepared_candidate`、`provider_committed_full_visible`、`provider_committed_persisted_preview`、`microcompact_cleared`。
2. 新增 `ToolResultCompactRecord` 或者把现有 `ContentReplacementRecord` 升级到等价能力。为了减少误解，建议新增 `ToolResultCompactRecord`，再让旧 `ContentReplacementRecord` 在过渡期保留。
3. 新增 `ToolResultArtifactRecord`，记录 `artifact_id`、`tool_result_id`、`tool_call_id`、`tool_name`、`content_sha256`、`size_chars`、`artifact_ref`、`publishable_after_visibility_scan`、`recovery_unlocked_after_provider_commit` 和派生的 `model_visible_recoverable`。
4. 新增 `MicroCompactRecord`，记录触发前后的数量、字符数、被清理的工具结果标识、保留的工具结果标识和占位符 hash。
5. 新增 `AutoCompactState` 和 `AutoCompactRecord`，记录触发原因、压缩前后 token 估算、summary artifact、source prepared messages、compact model call、是否高于压缩目标、连续失败次数。
6. 新增 `CompactSummary` schema，用于校验 compact-only 模型输出。
7. 新增 `ContextPolicySnapshot`，冻结并比较所有压缩策略字段：工具结果单项预算、每轮聚合预算、MicroCompact 白名单和阈值、AutoCompact 阈值、Reactive Compact 策略、recovery tool policy、模型窗口来源、harness cap、输出预留和安全余量。
8. 新增 `ModelInputSnapshot` 或 `ModelCallTrainingSample`，为每一次主模型调用记录 exact `prepared_messages_ref`、`model_input_hash`、`provider_request_projection_hash`、context compact state、context policy snapshot、trainable flag 和 provider request artifact。

### 5.2 不变量

1. 旧运行配置仍然能加载。加载后如果没有新字段，应使用新字段默认值。
2. 新字段必须能被写入 run config facts，便于后续审计。
3. schema 版本升级后，不应该导致已有 artifact inspect 读旧 artifact 失败。inspect 逻辑需要兼容旧版本。
4. 新增 context policy snapshot 后，preference pair compare scope 必须能比较关键压缩策略；不同策略或关键阈值的 run 不能被配成偏好对。

### 5.3 验证方式

增加或更新以下测试：

1. `tests/unit/test_context_manager.py`：验证默认 `ContextManagementConfig` 能构造，旧字段仍能被读取。
2. `tests/unit/test_pre_verl_cli.py`：验证已有 pre-verl run config 可以解析。
3. `tests/unit/test_run_metadata.py`：验证 run metadata 中的新配置 facts 不破坏旧 failure summary。

执行命令：

```bash
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_context_manager.py tests/unit/test_pre_verl_cli.py tests/unit/test_run_metadata.py
PATH=.venv/bin:$PATH python -m compileall src
```

## 6. 第二步：增加工具结果 artifact 存储和恢复工具

### 6.1 实施内容

新增模块 `src/repo_harness/context/tool_result_artifacts.py`，集中处理工具结果原文落盘和分页恢复。

建议提供以下能力：

1. `persist_tool_result_content(...)`：把工具结果原文写入 run artifact，返回 `ToolResultArtifactRecord`。
2. `build_persisted_tool_result_preview(...)`：生成模型可见的预览文本。只有当 artifact 已经 `publishable_after_visibility_scan = true` 时，preview 才能作为 candidate 包含即将发布的 `artifact_id`、内容 sha256、恢复工具调用示例和前若干字符预览。但是恢复权限不能在 prepared candidate 阶段解锁，必须等包含该 preview 的输入进入 model input accepted / provider-committed 后，才能把 `recovery_unlocked_after_provider_commit` 置为 true。如果工具结果内容被判定为 secret、redacted、evaluator-only 或其他不可恢复内容，preview 只能说明拒绝恢复原因，不能暴露真实 `artifact_id`、内容 sha256 或 `read_tool_result_artifact` 调用示例。
3. `read_tool_result_artifact(...)`：按 `artifact_id`、`offset`、`limit` 分页读取模型已经获准恢复的工具结果原文。
4. `ToolResultArtifactIndex`：当前 run 内的工具结果 artifact 恢复索引，拆分“可发布候选”和“已解锁可恢复”。它只允许恢复本 run、已记录、未隐藏、未标记 evaluator-only，并且已经进入 model input accepted / provider-committed 可见上下文的工具结果。

把恢复工具注册到 `src/repo_harness/tools/minimal.py`：

1. 在 `DEFAULT_TOOL_ORDER` 中加入 `read_tool_result_artifact`，位置建议在 `read_file` 之后。
2. 在 `default_tool_registry()` 注册工具定义，明确它只读取当前 run 中已经模型可见的工具结果 artifact，不读取工作区文件。
3. 在 `ToolExecutionContext` 中增加 `tool_result_artifact_index` 或者通过 `RunRecorder` 读取已登记 artifact 索引。
4. 更新 `ToolExecutor.execute()` 的分发分支，实际执行 `read_tool_result_artifact`。
5. 更新 `normalize()`，对 `artifact_id`、`offset`、`limit` 做规范化。`artifact_id` 必须保持为普通标识符，不能被解析为工作区路径。
6. 更新 `_schema_issue()`，校验 `artifact_id` 必填、`offset >= 0`、`limit` 在允许范围内。
7. 更新 scaffold allowed tools。`simple_react` 继承 `DEFAULT_TOOL_ORDER` 后会自动包含新工具，但 `patch_focused_react` 和 `planner_coder_verifier` 有手写工具列表和 phase tools，需要显式加入 `read_tool_result_artifact`，否则模型即使看到恢复指令也会被 scaffold 拒绝调用。

恢复工具必须拒绝以下内容：

1. evaluator-only artifact。
2. hidden test patch、gold patch、final verifier raw output。
3. provider raw request 和 raw response。
4. secret 或已经 redacted 的内容。
5. 非当前 run 的 artifact。
6. 没有同时满足 `publishable_after_visibility_scan = true` 和 `recovery_unlocked_after_provider_commit = true` 的 artifact。
7. 普通 artifact manifest 中存在、但没有进入 `ToolResultArtifactIndex` 正向登记的 artifact。
8. contamination scan 状态为 `not_scanned` 且没有额外可见性证明的 artifact。
9. 只在 prepared candidate preview 中出现、但对应 provider request 后来被 context warning、AutoCompact、本地 hard preflight stop、provider context_limit 或 prompt too long 替代的 artifact。

### 6.2 不变量

1. 模型只能读取它本来已经在 model input accepted / provider-committed 输入中看过预览、且被标记为可恢复的工具结果原文。
2. `artifact_id` 是 `ToolResultArtifactIndex` 发放的恢复能力标识，不是文件系统路径、普通 `ArtifactRef` 或 artifact manifest id。恢复工具不能让模型通过路径穿越读取任意文件。
3. 每次分页读取都要记录普通工具调用和工具结果，形成可训练、可审计轨迹。
4. 恢复工具返回的内容也要受 `max_tool_output_chars` 或单次 `limit` 限制，避免恢复工具本身变成新的超大工具结果来源。
5. `model_visible_recoverable = true` 只能作为 `publishable_after_visibility_scan = true` 且 `recovery_unlocked_after_provider_commit = true` 的派生状态，不能在 candidate 阶段提前设置。

### 6.3 验证方式

新增 `tests/unit/test_tool_result_artifacts.py`：

1. 大内容落盘后，preview 中包含 `artifact_id`、sha256、大小和恢复工具调用示例。
2. `read_tool_result_artifact(artifact_id, offset=0, limit=8000)` 能返回第一页和 `next_offset`。
3. offset 越界时返回清晰错误。
4. 非当前 run artifact 被拒绝。
5. evaluator-only artifact 被拒绝。
6. 随机路径、绝对路径、`../` 路径不能被当成 artifact_id 读取。
7. `publishable_after_visibility_scan = false` 的 artifact preview 不包含真实 `artifact_id`、内容 sha256 或恢复调用示例。
8. candidate preview 出现过、但没有进入 provider-committed 输入的 artifact 不能被 `read_tool_result_artifact` 读取。
9. 包含 preview 的 provider request 被 context_limit 拒绝时，artifact 不解锁恢复。

更新 `tests/unit/test_tools.py`：

1. 工具 schema snapshot 包含 `read_tool_result_artifact`。
2. 恢复工具是只读工具。
3. 恢复工具不会要求读取工作区路径权限。
4. `patch_focused_react` 和 `planner_coder_verifier` 的 allowed tools / phase allowed tools 都允许恢复工具。

执行命令：

```bash
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_tool_result_artifacts.py tests/unit/test_tools.py tests/unit/test_tool_schema_snapshot.py
PATH=.venv/bin:$PATH python -m compileall src
```

## 7. 第三步：实现单个工具结果过大时立即落盘

### 7.1 实施内容

单个工具结果预算应在 `AgentLoop` 记录工具结果前统一后处理，而不是只放在 `ToolExecutor.execute()` 或 `_tool_result()` 内部。原因是当前不只有正常工具执行会产生工具结果，未知工具、权限拒绝、schema 校验失败、scaffold 禁用、预算中断等路径也会直接进入 `_record_tool_result()`。如果只改正常工具执行出口，会漏掉这些异常路径的大输出。

建议新增统一后处理函数：

```python
def apply_single_tool_result_budget(
    result: ToolResult,
    *,
    context: ToolExecutionContext,
    context_config: ContextManagementConfig,
) -> ToolResult:
    ...
```

这个函数应在所有调用 `_record_tool_result(...)` 之前运行，或者直接把 `_record_tool_result(...)` 扩展为先执行该后处理。它必须覆盖以下来源：

1. 正常 `ToolExecutor.execute()` 返回的工具结果。
2. `invalid_tool_result`。
3. `disallowed_tool_result`。
4. `validate_input` 返回的 schema 错误结果。
5. permission denied 结果。
6. disabled test feedback 结果。
7. interrupted tool result。
8. 未知工具或 scaffold 不允许工具产生的错误结果。

后处理规则：

1. 如果 `len(result.content_preview) <= max_single_tool_result_chars`，保持原样。
2. 如果超过 `max_single_tool_result_chars`，把原文写入工具结果 artifact。
3. 把 `result.content_preview` 替换成固定格式 preview。
4. 在 `result.typed` 中加入 `tool_result_compaction` 信息，例如 `persisted_due_to_single_result_budget`、`artifact_id`、`content_sha256`、`original_size_chars`、`preview_size_chars`。
5. 在 `result.artifact_refs` 中追加对应 artifact ref。
6. 在事件中记录 `tool_result_persisted`，说明这是单个工具结果预算触发，不是后续上下文预算触发。

需要注意：有些工具本身已经有分页和输出限制，例如 `read_file`、`grep`、`list_files`。这一步不是替代工具自身分页，而是防止任何工具在异常情况下返回超大结果。

### 7.2 不变量

1. 单个工具结果一旦被立即落盘，后续 `ContextManager` 不能再把它当成 fresh full result 处理。
2. 立即落盘后的 preview 要稳定。同一个工具结果在后续轮次中应该复用完全相同的 preview 字符串。
3. preview 必须告诉模型如何恢复，而不是只说“内容过大”。
4. 对失败工具结果也适用。如果失败输出特别大，也应落盘。

### 7.3 验证方式

新增 `tests/unit/test_tool_result_compact.py`：

1. 构造超过 50000 字符的工具结果，验证原文被写入 artifact，模型可见 content 变成 preview。
2. 构造 49999 字符工具结果，验证不落盘。
3. 验证失败状态工具结果超过阈值时也落盘。
4. 验证 preview hash 在重复 prepare 时不变化。
5. 验证 `read_tool_result_artifact` 可以恢复被单结果预算落盘的内容。
6. 覆盖 invalid tool、disallowed tool、schema validation failure、permission denied、interrupted tool result 等非正常执行路径的大输出。
7. 模拟 artifact 写入失败，验证工具结果不会静默丢失原文，并记录明确的 `tool_result_persist_failed` 或等价失败事件。

更新 `tests/integration/test_tool_execution.py`：

1. 用一个产生大输出的工具调用验证 transcript、events 和 artifact manifest 都包含对应记录。

执行命令：

```bash
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_tool_result_compact.py tests/integration/test_tool_execution.py
PATH=.venv/bin:$PATH python -m compileall src
```

## 8. 第四步：实现当前轮工具结果聚合预算和命运冻结

### 8.1 实施内容

改造 `src/repo_harness/context/manager.py`，把当前 `_reduce_messages()` 中的历史老化替换逻辑替换为 fresh-only 聚合预算逻辑，并把“候选决策”和“provider-committed 决策”拆开。

建议新增 `src/repo_harness/context/tool_result_compact.py`，把选择逻辑从 `ContextManager` 中拆出来，便于单独测试。

核心流程：

1. 按模型 API 层面的消息分组计算工具结果聚合大小。RepoHarness 当前消息格式不是 Claude Code 的 content block 格式，但也要按“同一轮工具结果集合”处理，避免把历史工具结果拿来重新决策。
2. 找出 fresh tool result：尚未出现在 provider-committed 主模型输入中，且没有已有 provider-committed `ToolResultCompactRecord` 的工具结果。第一次进入 `prepare_messages()` 只能产生 candidate decision，不能冻结命运。
3. 找出 must reapply：之前已经在 provider-committed 主模型输入中被替换为 persisted preview 的工具结果，这次必须重放同一 preview。
4. 找出 frozen full visible：之前已经以完整内容进入过 provider-committed 主模型输入的工具结果，这次不能被第零层再替换。
5. 对 fresh tool result 计算当前轮聚合字符数。如果总量超过 `max_tool_results_per_turn_chars`，按大小降序选择若干 fresh result 落盘，直到当前轮 fresh 可见工具结果总量低于预算。
6. 对被选择的 fresh result 写入 artifact 并在 prepared candidate 中替换成 preview。
7. 对未被选择的 fresh result 在 prepared candidate 中暂时保留 full content。
8. `ContextManager.prepare_messages()` 写出 candidate decisions 和 `candidate_prepared_messages_ref`，但不把这些结果写入 provider-committed state。
9. 当 `AgentLoop` 构造真实主模型请求，并且该请求有 provider request projection hash、model call id 和 provider request artifact 绑定后，调用 `commit_tool_result_compact_decisions(...)`。只有这一步才能把 candidate decision 提交为 `provider_committed_full_visible` 或 `provider_committed_persisted_preview`。
10. 如果本地 context warning 导致重新 prepare、本地 hard preflight stop、AutoCompact 替代该 candidate，或 provider 返回 `context_limit` / `prompt too long` 拒绝该请求，则该 candidate 不能升级为“模型已看过”的事实。

这一步需要删除或停用当前 `_replacement_candidates()` 中“扫描所有历史工具消息、保护最近 N 轮、替换较旧结果”的主线行为。可以保留旧函数，但只能在 `legacy_history_tool_result_replacement = True` 时启用，用于短期回滚和旧测试对照。

### 8.2 不变量

1. 第零层只对尚未 provider-committed 的 fresh tool result 做新 candidate decision。
2. 一个工具结果第一次进入 provider-committed 主模型输入时如果是完整内容，后续不能被第零层改成 preview。
3. 一个工具结果第一次进入 provider-committed 主模型输入时如果是 preview，后续必须重放同一个 preview，不重新读 artifact、不重新生成 preview。
4. 聚合预算只看模型可见文本字符数，不看 token 数。
5. 已经由单个工具结果预算落盘的结果，不应被聚合预算再次落盘。
6. 工具调用和工具结果配对必须保持完整，不能删除 tool message。
7. prepared candidate state 可以被丢弃；provider-committed state 才能进入训练样本输入事实和 preference compare scope。

### 8.3 验证方式

新增或更新 `tests/unit/test_context_manager.py` 和 `tests/unit/test_tool_result_compact.py`：

1. 同一轮 10 个工具结果，每个 40000 字符，总量 400000 字符，验证会从最大的 fresh result 开始落盘，直到低于 200000 字符。
2. 工具结果只进入过 prepared candidate、但没有绑定主模型 provider request 时，后续仍然可以重新做 candidate decision，不应被记录为 frozen。
3. 历史工具结果曾 provider-committed 完整可见，即使后续总上下文变大，也不会被第零层改成 preview。
4. 历史工具结果曾 provider-committed 为 preview，后续重复 prepare 时 preview 完全一致。
5. context warning 触发第二次 prepare 时，第一次 candidate 不会冻结命运。
6. 已经由单个工具结果预算落盘的结果不会重复写 artifact。
7. `content_replacement_state` 或新的 `tool_result_compact_state` 中区分 candidate decision 和 provider-committed decision。
8. prepared messages 的 `model_input_hash` 在相同输入和相同 provider-committed 状态下稳定。
9. `_validate_tool_pairing()` 仍然通过。

执行命令：

```bash
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_context_manager.py tests/unit/test_tool_result_compact.py
PATH=.venv/bin:$PATH python -m compileall src
```

## 9. 第五步：实现 MicroCompact

### 9.1 实施内容

新增 `src/repo_harness/context/microcompact.py`。MicroCompact 在第零层工具结果预算之后运行。

触发条件：

```text
compactable tool result 数量 >= 30
并且 compactable tool result 当前可见内容总量 >= 60000 字符
```

执行策略：

1. 只处理白名单工具的工具结果。白名单包括 `read_file`、`grep`、`list_files`、`glob_files`、`symbol_search`、`git_diff`、`edit_file`、`create_file`、`bash`、`run_tests`。
2. 不处理 `update_working_state`、`context_warning`、`semantic_summary`、`session_memory` 等状态类或摘要类消息。
3. 保留最近 15 个 compactable tool result 的原始可见内容。
4. 把更旧的 compactable tool result 的 `content` 替换为固定字符串 `[Old tool result content cleared]`。
5. 被清理的消息要保留 role、tool_call_id、tool_result_id、tool_name、status、typed metadata 和 artifact refs。
6. 如果一个工具结果已经是 persisted preview，不应该被 MicroCompact 清成占位符，除非明确记录 `recovery_status = artifact_recoverable` 且产品上接受二次清理。为了降低恢复复杂度，第一版建议不清理 persisted preview。
7. MicroCompact 必须是幂等的。已经是 `[Old tool result content cleared]` 的内容不能重复产生新记录或改变 hash。
8. MicroCompact 只能改变 provider-prepared projection，不能销毁原始工具结果事实。原始内容必须继续保存在 raw trajectory、工具结果 artifact 或审计 artifact 中；训练导出使用模型当轮实际看到的 compacted view。

### 9.2 不变量

1. MicroCompact 可以改变历史 full visible 工具结果的可见内容，但这是第一层明确机制，不属于第零层预算的命运改写。
2. MicroCompact 不提供精确恢复保证。被清理且没有 artifact 的旧工具结果只能显示 `cleared_without_recoverable_artifact`。
3. MicroCompact 不删除消息，不破坏 tool call 和 tool result 配对。
4. MicroCompact 不应该清理工作状态更新类消息，因为这些消息更接近 agent memory。
5. MicroCompact 的审计记录必须能说明“原始事实在哪里保留”和“当轮模型实际看到的是占位符还是原文”。

这里需要特别区分第零层的命运冻结和第一层的 MicroCompact：某个工具结果一旦以完整内容进入过 provider-committed 主模型输入，第零层工具结果预算后续不能再把它改成 persisted preview；但是这不阻止第一层 MicroCompact 在更晚的 provider-prepared projection 中把它替换为 `[Old tool result content cleared]`。这不是修改历史事实，而是生成新的后续模型输入视图。训练导出必须以每一次主模型调用的 `ModelInputSnapshot` 为准，因此同一个工具结果可以在早期训练样本中是完整内容，在后期训练样本中是 MicroCompact 占位符。

### 9.3 验证方式

新增 `tests/unit/test_microcompact.py`：

1. 29 个 compactable tool result，即使字符数超过 60000，也不触发。
2. 30 个 compactable tool result，但字符数低于 60000，也不触发。
3. 30 个 compactable tool result 且字符数超过 60000，保留最近 15 个，其余替换为固定占位符。
4. `update_working_state` 不被清理。
5. persisted preview 不被清理。
6. 重复运行 MicroCompact，第二次没有新增清理记录，prepared messages hash 稳定。
7. tool pairing validation 通过。

更新 `tests/unit/test_context_manager.py`：

1. 验证 `ContextManager.prepare_messages()` 的 `context_reduction` 中包含 `microcompact_applied`、`microcompact_cleared_count`、`microcompact_kept_recent_count`。

执行命令：

```bash
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_microcompact.py tests/unit/test_context_manager.py
PATH=.venv/bin:$PATH python -m compileall src
```

## 10. 第六步：实现有效上下文预算计算

### 10.1 实施内容

新增 `src/repo_harness/context/budget.py` 或 `src/repo_harness/context/model_context.py`，集中计算有效上下文预算。

计算公式：

```text
effective_context_budget_tokens =
  min(model_context_window_tokens, harness_context_cap_tokens if explicitly set)
  - main_output_reserve_tokens
  - estimator_safety_margin_tokens
```

其中：

```text
estimator_safety_margin_tokens =
  max(
    int(base_window * estimator_safety_margin_ratio),
    estimator_safety_margin_min_tokens
  )
```

`model_context_window_tokens` 的来源：

1. 如果配置显式填写整数，直接使用。
2. 如果配置为 `"auto"`，从 provider 和 model_id 的本地 registry 解析。
3. 如果 registry 不认识该 model_id，应使用保守默认值，并在 `context_prepared` event 中写入 `model_context_window_resolution = "unknown_model_uses_default"`。

建议新增本地 registry，例如：

```python
MODEL_CONTEXT_WINDOW_REGISTRY = {
    ("deepseek", "deepseek-v4"): 1_000_000,
    ("openai", "gpt-5.5"): 1_000_000,
}
```

真实 model_id 可能有版本后缀，registry 需要支持精确匹配和 provider 级默认值。不要联网查询上下文长度，运行时应保持可复现。

预算估算对象必须是 provider request projection，而不只是 messages 文本。新增的预算记录至少需要拆分以下字段：

```text
provider_request_projection_hash
message_token_estimate
tool_schema_token_estimate
tool_choice_token_estimate
provider_wrapper_token_estimate
generation_config_token_estimate
main_output_reserve_tokens
estimator_safety_margin_tokens
effective_context_budget_tokens
hard_context_limit_tokens
```

其中 `provider_request_projection_hash` 必须对应 provider 适配器实际发送或准备发送的请求投影，包括 messages、工具 schema、`tool_choice`、provider 包装字段和会进入请求体的 generation config。AutoCompact 触发线、context warning 和 hard preflight stop 都应使用这个 projection 的估算结果。

provider request projection 必须由一个统一的纯构造器生成，例如 `build_provider_request_projection(...)`。AutoCompact 触发、context warning、hard preflight、真实 provider request、raw request artifact、provider body equivalence inspect 和 hash 复算都必须使用同一个构造器的输出。不要分别维护“估算用请求体”和“真实发送请求体”，否则预算判断、provider request hash 和训练样本输入会发生漂移。

实现有效上下文预算后，必须同步替换所有仍然使用旧 `max_context_tokens` 作为硬限制的入口：

1. 更新 `src/repo_harness/budget/schemas.py` 的 `BudgetManager.from_run_config()`，让 `budget_manager.max_context_tokens` 或新增的 `budget_manager.effective_context_budget_tokens` 来自有效上下文预算，而不是固定来自 `context_management.max_context_tokens`。
2. 更新 `src/repo_harness/agent_loop/loop.py` 中的 context warning 计算，让 80% 和 90% 警告基于有效上下文预算。
3. 更新 `src/repo_harness/agent_loop/loop.py` 中模型调用前的 preflight hard stop，让它基于 `hard_context_limit_tokens = effective_context_budget_tokens * hard_context_limit_ratio`。
4. 更新 `src/repo_harness/pre_verl_run_facts.py` 和 `src/repo_harness/run_metadata/writer.py`，把 `context_budget_tokens`、模型上下文窗口来源、harness cap、输出预留和估算安全余量写入 run config facts。
5. 更新 `ContextManager.prepare_messages()` 的调用接口。当前它只有 `provider_name`，不知道具体 `model_id`。如果 `context_prepared` event 要记录 `model_context_window_resolution` 和 `effective_context_budget_tokens`，应由 `AgentLoop` 先根据 `provider_options.provider` 和 `provider_options.model_id` 解析预算，再把预算事实传给 `ContextManager`。

### 10.2 不变量

1. AutoCompact 阈值和 hard context limit 都基于有效上下文预算，而不是旧的固定 `max_context_tokens = 120000`。
2. 如果用户显式设置 `harness_context_cap_tokens`，harness cap 可以低于模型真实上下文窗口。
3. 如果模型上下文窗口是 1,000,000 token，压缩阈值应该自然变大，不应该被旧默认 120,000 限制。
4. `post_compact_target_tokens = min(effective_budget * post_compact_target_ratio, post_compact_target_max_tokens)`。
5. `post_compact_target_tokens` 是压缩质量目标，不是立即循环压缩条件。
6. 任何进入主模型调用的训练样本，都必须保存当轮 `provider_request_projection_hash`，用于证明导出的输入和真实请求一致。

### 10.3 验证方式

新增 `tests/unit/test_context_budget.py`：

1. model window 1,000,000，reserve 32,000，safety margin 至少 30,000，验证 effective budget 约为 938,000。
2. 设置 `harness_context_cap_tokens = 120000`，验证 effective budget 基于 120,000 而不是 1,000,000。
3. unknown model 使用保守默认值，并写入 resolution reason。
4. `post_compact_target_ratio = 0.60` 且 max 为 300,000 时，1M 模型目标被上限截断到 300,000。
5. 小上下文模型不会产生负数预算，配置错误时给出清晰异常。
6. `BudgetManager.from_run_config()`、context warning、preflight hard stop、run config facts 和 `context_prepared` event 使用同一个预算事实。
7. messages 很短但工具 schema 很大时，`tool_schema_token_estimate` 会让总 projection estimate 增大，并能触发 AutoCompact 或 warning。
8. `provider_request_projection_hash` 在 provider body 等价检查中可复算。
9. 同一组 prepared messages、工具 schema、`tool_choice` 和 provider options 通过统一 projection 构造器生成稳定 hash；如果真实 provider request 与 projection 不等价，inspect 必须失败。

执行命令：

```bash
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_context_budget.py tests/unit/test_context_manager.py
PATH=.venv/bin:$PATH python -m compileall src
```

## 11. 第七步：实现 AutoCompactRunner 和 compact-only 模型请求

### 11.1 实施内容

新增 `src/repo_harness/context/auto_compact.py`，实现 `AutoCompactRunner`。

`AutoCompactRunner` 不应该隐藏在 `ContextManager` 内部。原因是 `ContextManager` 只负责确定性准备消息，而 AutoCompact 需要发起一次独立模型调用。它应该由 `AgentLoop` 持有并调用。

建议接口：

```python
class AutoCompactRunner:
    def run(
        self,
        *,
        mode: Literal["proactive", "emergency"],
        trigger_reason: str,
        source_prepared: PreparedMessages,
        recorder: RunRecorder,
        task_id: str,
        turn: int,
        context_config: ContextManagementConfig,
        provider_options: ProviderOptions,
        model_client: ModelClient,
        tool_schema_snapshot_ref: ArtifactRef,
        run_config_facts_ref: RunConfigFactsRef,
    ) -> AutoCompactResult:
        ...
```

`AutoCompactRunner` 的 compact-only prompt 和 rehydration 输入只能由 `source_prepared.messages` 的模型可见投影构造，不能从 raw trajectory、未过滤的 canonical messages、provider raw request、provider raw response 或 evaluator-only metadata 中补材料。如果实现为了保留 message id、system/task 边界或 append 压缩后的 canonical messages 而需要接触原始 `messages`，也只能把它们作为结构性输出目标使用，不能把未经过 visibility 过滤的内容送入 compact-only prompt 或 summary 重建。

`AutoCompactRunner` 在调用 compact-only 模型之前，必须先构造 `compact_source_projection` 并估算其真实 provider request projection。如果 compact-only 请求本身超过 compact 模型的硬限制：

1. proactive AutoCompact 不能生成伪摘要，应记录 `auto_compact_source_too_large`。
2. 如果当前主模型请求已经超过本地 hard preflight，应停止为 `context_limit_preflight_after_autocompact`，除非显式配置允许 hard preflight recovery。
3. provider verified Reactive Compact 场景下，可以进入 PTL fallback，由 round truncation 产生可重试请求。
4. 摘要不能声称理解没有送入 compact-only 请求的历史；被省略历史必须通过 omission marker 和审计 artifact 说明。

compact-only 模型请求要求：

1. 使用独立 `model_call_id`，例如 `{run_id}_compact_call_{turn:04d}_{attempt:02d}`。
2. `scaffold_phase = "compact"`。
3. `allowed_tool_definitions = []`。
4. `tool_choice = "none"` 或等价配置。
5. 不写入普通 assistant action。
6. 不计入主循环 tool-call budget。
7. 不作为 trainable action 导出。
8. 原始 provider request 和 response 仍然写 artifact，但要在导出时标记为 compact metadata，不作为模型训练样本。

compact-only prompt 应明确要求模型只基于可见上下文写摘要，不得编造测试结果、不得引入隐藏 verifier 或 gold patch 信息。摘要输出建议强制为 JSON，字段至少包括：

```json
{
  "task_intent": "...",
  "repository_facts": ["..."],
  "actions_taken": ["..."],
  "patch_state": {
    "changed_files": ["..."],
    "important_diffs": ["..."]
  },
  "test_state": {
    "commands_run": ["..."],
    "passing": ["..."],
    "failing": ["..."],
    "unknown": ["..."]
  },
  "tool_recovery_index": [
    {
      "tool_result_id": "...",
      "tool_name": "...",
      "artifact_id": "...",
      "recovery_status": "artifact_recoverable"
    }
  ],
  "open_questions": ["..."],
  "next_step": "...",
  "visibility_policy": "model_visible_only"
}
```

### 11.2 不变量

1. compact-only 模型请求只能看到 `source_prepared.messages` 中已经模型可见的内容，以及显式允许的模型可见 artifact 索引。
2. compact-only 输出必须通过 schema 校验。校验失败时不能进入正式上下文。
3. compact-only 输出不得包含隐藏材料标记，例如 hidden test patch、gold patch、final verifier raw output。
4. compact-only 失败时，只记录失败事件，不得把失败文本塞进普通消息历史。

### 11.3 验证方式

新增 `tests/unit/test_auto_compact.py`：

1. 用 fake model client 返回合法 JSON 摘要，验证 `AutoCompactRunner` 生成 `AutoCompactResult`。
2. fake model client 返回非 JSON，验证失败事件和失败计数。
3. fake model client 返回包含禁止字段的摘要，验证被污染扫描拒绝。
4. 验证 compact-only request 的 allowed tools 为空。
5. 验证 compact-only request 的 `scaffold_phase` 是 `compact`。
6. 验证 compact-only request 不生成普通 assistant transcript action。
7. 验证 compact-only provider request 和 response 仍有 artifact ref，便于审计。
8. compact-only source projection 超限时，记录 `auto_compact_source_too_large`，不产生 summary artifact。
9. compact-only source projection 的 provider request hash 可复算。

执行命令：

```bash
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_auto_compact.py tests/unit/test_agent_loop_protocol.py
PATH=.venv/bin:$PATH python -m compileall src
```

## 12. 第八步：实现压缩后消息重建和上下文恢复索引

### 12.1 实施内容

在 `src/repo_harness/context/auto_compact.py` 或单独模块 `src/repo_harness/context/compact_rebuild.py` 中实现压缩后消息重建。

压缩后的 canonical messages 建议结构：

1. 原始系统消息和任务消息。
2. 一条模型可见的 compact boundary user message，说明“之前较长历史已经被 AutoCompact 压缩为摘要”。
3. 一条模型可见的 compact summary message，内容来自 `CompactSummary`。
4. 最近原文尾部消息，按 `preserve_recent_turns_after_compact` 和动态 tail token budget 保留。
5. 一条恢复索引消息，列出可以通过 `read_tool_result_artifact` 恢复的 artifact。

动态近期尾部预算：

```text
effective_preserve_recent_tail_token_budget =
  min(
    preserve_recent_tail_token_budget,
    post_compact_target_tokens * 0.50,
    effective_context_budget_tokens * 0.35
  )
```

重建逻辑必须从以下来源提取信息：

1. `source_prepared.messages` 中模型已经可见的消息。
2. 模型可见并且可恢复的工具结果 artifact。
3. 压缩前已经由模型可见 read-state 记录过的 allowlisted workspace 文件片段。这里的 workspace 只能是 agent 当前公开工作区中允许模型读取的路径；clean source checkout 只能用于复核已经模型可见的公开片段，不能静默补入模型之前没有看过的新文件内容。所有路径都必须复用工具系统中的模型隐藏路径规则，例如 `_is_model_hidden_tool_path` 或等价逻辑。
4. 压缩前已经由模型可见 diff-state 或 `git_diff` 工具结果记录过的当前 candidate diff 和 diff stat。
5. 已经标记为模型可见的 verifier result preview。
6. 模型可见 context management artifacts。

如果必须读取实时工作区文件、clean source checkout 或实时 diff，不能静默读取后塞进 rehydration。必须生成 `rehydration_source_read` artifact，记录路径、读取命令、内容 hash、读取时机、可见性检查、污染扫描结果和引入原因。clean source checkout 的读取只能用于验证或重取模型已经看过的公开片段；如果引入了新片段，它必须作为新的模型可见事实进入后续 prepared messages 和训练样本的 `ModelInputSnapshot`。

禁止来源：

1. raw hidden feedback。
2. final verifier raw output。
3. reward 和 outcome。
4. gold patch。
5. hidden test patch。
6. evaluator-only selector 和 evaluator-only artifacts。
7. 没经过 visibility 过滤的 raw trajectory metadata。
8. `evaluator_only_inputs` 目录。
9. `pre_verl_final_verification_workspace` 目录。
10. hidden patch、selector、final verifier 输出所在的任何 run artifact 或临时目录。
11. 没有经过 `rehydration_source_read` 记录和污染扫描的实时工作区读取结果。

### 12.2 不变量

1. 压缩后上下文仍然是普通 canonical messages，后续 `ContextManager.prepare_messages()` 可以继续处理。
2. 压缩后必须重新运行第零层和第一层压缩，保证 prepared messages 没有超过 hard limit。
3. 工具调用和工具结果配对不能被破坏。近期尾部如果保留了 assistant tool call，就必须保留对应 tool result；如果无法完整保留，应从安全边界处截断。
4. `tool_recovery_index` 只能包含模型可见且可恢复 artifact。
5. 被 MicroCompact 清理且没有 artifact 的旧结果只能标记 `cleared_without_recoverable_artifact`，不能假装可恢复。
6. rehydration 不能注入模型压缩前没有看过的新信息，除非该信息通过 `rehydration_source_read` 明确进入模型可见输入和审计链。

### 12.3 验证方式

新增 `tests/unit/test_compact_rebuild.py`：

1. 给定一段包含多轮工具调用的历史，重建后保留系统消息、任务消息、boundary、summary、近期尾部和恢复索引。
2. 如果近期尾部从 assistant tool call 中间截断，验证重建器会回退到完整配对边界。
3. recovery index 只包含同时满足 `publishable_after_visibility_scan = true` 和 `recovery_unlocked_after_provider_commit = true` 的 artifact。
4. 输入中包含 evaluator-only artifact，重建后不能出现。
5. 输入中包含 hidden/gold/final verifier raw marker，污染扫描失败。
6. 重建后再次调用 `ContextManager.prepare_messages()`，tool pairing validation 通过。
7. 实时读取工作区文件作为 rehydration 来源时，必须存在 `rehydration_source_read` artifact，且该 artifact 进入 post-compact prepared messages 引用链。
8. 未经记录的实时文件内容出现在 rehydration 中时，测试失败。

执行命令：

```bash
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_compact_rebuild.py tests/unit/test_auto_compact.py tests/unit/test_context_manager.py
PATH=.venv/bin:$PATH python -m compileall src
```

## 13. 第九步：把 AutoCompact 接入 AgentLoop

### 13.1 实施内容

修改 `src/repo_harness/agent_loop/loop.py` 的模型调用前流程。

当前流程是：

```text
canonical messages
-> ContextManager.prepare_messages()
-> context warning
-> 如果超过 max_context_tokens，直接 context_limit 停止
-> model_client.generate()
```

目标流程是：

```text
canonical messages
-> ContextManager.prepare_messages()
-> 计算 effective_context_budget_tokens
-> 如果达到 auto_compact_trigger_ratio，调用 AutoCompactRunner(mode="proactive")
-> 用压缩后的 canonical messages 再次 ContextManager.prepare_messages()
-> 如果仍然高于 post_compact_target 但低于 hard limit，继续并记录 post_compact_above_target
-> 如果压缩后仍超过 hard_context_limit_tokens，停止为 context_limit_preflight_after_autocompact
-> model_client.generate()
```

注意：本轮不建议在本地 preflight 超过 hard limit 时直接调用 Reactive Compact。Reactive Compact 的定义是“真实 provider 返回 context_limit 后的兜底”。如果压缩后仍超过 `hard_context_limit_tokens`，应停止为 `context_limit_preflight_after_autocompact`，并记录 `source_prepared_messages_ref`、`summary_artifact_ref`、`tokens_before`、`tokens_after` 和 `effective_context_budget_tokens`；不要发送主模型请求，也不要把本地 preflight 超限标记为 Reactive Compact。

需要新增事件：

1. `auto_compact_triggered`
2. `auto_compact_model_call_started`
3. `auto_compact_model_call_completed`
4. `auto_compact_applied`
5. `auto_compact_failed`
6. `context_post_compact_prepared`

需要在 `AgentState` 或等价状态中记录：

1. `auto_compact_consecutive_failures`
2. `last_auto_compact_revision`
3. `last_auto_compact_summary_ref`
4. `post_compact_above_target`

还需要同步更新 `src/repo_harness/agent_loop/schemas.py`：

1. 为 `AgentLoopState` 增加 AutoCompact 和 Reactive Compact 的运行字段。
2. 扩展 `AgentStopReason`。至少增加 `context_limit_preflight_after_autocompact`、`auto_compact_failed_preflight`、`reactive_compact_failed`、`context_limit_after_reactive_compact`、`context_limit_reactive_compact_disabled`。
3. 更新任何根据 stop reason 做严格枚举校验的 inspect、run metadata 和 export 逻辑。

还需要在 `AgentLoop` 中新增 provider request materialized 与 model input accepted 边界：

1. `ContextManager.prepare_messages()` 只产生 candidate prepared messages 和 candidate compact decisions。
2. 主模型请求构造完成后，provider adapter 生成 provider request projection、`provider_request_projection_hash` 和 raw provider request artifact，并写出 `provider_request_materialized` 事件。这个事件只表示请求体已经构造并准备发送，不能冻结工具结果命运，不能解锁 tool result artifact，也不能生成 trainable `ModelInputSnapshot`。
3. provider 返回非 `context_limit`、非 `prompt too long` 的结果，并且可以认为模型实际消费了该输入后，`AgentLoop` 或 provider adapter 才写出 `model_input_accepted` 事件。如果实现继续使用 `model_input_committed` 这个名字，它必须等价于 `model_input_accepted`，不能表示“请求体已构造”。
4. `model_input_accepted` 绑定 `model_call_id`、`prepared_messages_ref`、`model_input_hash`、`provider_request_projection_hash`、provider request artifact、provider response artifact 和 `context_policy_snapshot_ref`。
5. 只有 `model_input_accepted` 成功后，才调用 `commit_tool_result_compact_decisions(...)`，把 candidate decisions 推进为 provider-committed state，并解锁 provider-committed preview 引用的 tool result artifact。
6. 如果这次调用被本地 hard preflight 拦截，或者 provider 返回 `context_limit` / `prompt too long` 拒绝请求，则不能提交为“模型已看过”，不能解锁恢复 artifact，也不能生成 trainable `ModelInputSnapshot`。

### 13.2 不变量

1. AutoCompact 成功后，后续主模型调用必须绑定新的 prepared messages ref。
2. AutoCompact 失败不应该把 compact-only 模型输出写入普通 messages。
3. 连续失败达到 `auto_compact_max_consecutive_failures` 后，本轮不再继续 proactive AutoCompact，避免死循环。
4. 压缩后如果仍高于 `post_compact_target_tokens` 但低于 hard limit，不立即重复压缩，只记录 `post_compact_above_target=true`。
5. 压缩后如果仍超过 hard limit，应停止并记录清楚原因，不能继续发一个明显会失败的请求。

### 13.3 验证方式

更新 `tests/unit/test_agent_loop_protocol.py`：

1. 构造 fake prepared token estimate 达到触发阈值，验证 AutoCompact 被调用一次。
2. AutoCompact 成功后，主模型调用使用压缩后的 prepared messages ref。
3. AutoCompact 成功但高于 post target、低于 hard limit，验证继续主模型调用，并记录 `post_compact_above_target=true`。
4. AutoCompact 成功但仍超过 hard limit，验证停止为明确原因。
5. AutoCompact 连续失败达到上限，验证不会无限循环。
6. 新增 stop reason 能通过 `AgentLoopState` schema 校验。
7. 本地 preflight 超过 hard limit 时不会发送主模型请求，也不会触发 Reactive Compact。
8. context warning 触发 re-prepare 时，第一次 candidate prepared messages 不会生成 `model_input_accepted`，也不会冻结工具结果命运。
9. 只有带有 `model_input_accepted` 事件的主模型调用才生成 trainable `ModelInputSnapshot`；provider request materialized 但随后 context_limit 的调用不能生成 trainable snapshot。

更新 `tests/unit/test_run_metadata.py`：

1. 验证 AutoCompact 成功后不会被错误分类为普通 context_limit failure。
2. 验证 AutoCompact 后仍不足导致停止时，分类为 `compaction_applied_but_insufficient_context_limit` 或新的更精确 failure type。

执行命令：

```bash
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_agent_loop_protocol.py tests/unit/test_auto_compact.py tests/unit/test_run_metadata.py
PATH=.venv/bin:$PATH python -m compileall src
```

## 14. 第十步：实现 Reactive Compact

### 14.1 实施内容

Reactive Compact 只在真实 provider 返回上下文超限错误后触发。它不是简单的 “emergency AutoCompact”，而是 provider verified recovery pipeline：

1. 优先路径是 `AutoCompactRunner.run(mode="emergency", trigger_reason="provider_context_limit_retry")`。
2. 如果 emergency AutoCompact 的 compact-only 输入本身超限，或者 provider 错误显示必须立即裁剪请求头部，则进入 `truncate_head_for_ptl_retry` fallback。
3. `truncate_head_for_ptl_retry` 必须按 API round 分组，从最旧完整 round 开始丢弃，保持 tool call 和 tool result 配对，保留 system / task / compact summary / 最近完整 rounds，并插入 synthetic user marker。
4. synthetic user marker 必须说明较早 rounds 因 provider context limit 被省略。它是模型可见上下文管理标记，不是用户真实输入，也不是 assistant action。

触发判断应覆盖：

1. `response.terminal_error_type == "context_limit"`。
2. `response.model_error_type == "context_limit"`。
3. provider adapter 标准化出的 HTTP 413 或上下文超限文本。

需要更新 `src/repo_harness/model_client/providers/common.py` 的 `classify_http_status()`，把 `"prompt too long"`、`"context length"`、`"maximum context"`、`"context limit"`、`"too many tokens"` 和 HTTP 413 等 provider 常见表达统一归一化为 `context_limit`。`AgentLoop` 中的 Reactive Compact 触发逻辑只依赖归一化后的 `terminal_error_type` 或 `model_error_type`，不要在主循环里直接解析原始错误全文。

修改 `src/repo_harness/agent_loop/loop.py` 的模型响应处理：

1. 如果主模型调用返回 `context_limit`，先记录原始失败事件和 artifact。
2. 不要把这次失败 response 作为普通 assistant message 加入可继续重试的 canonical messages。
3. 解析 provider 错误中的 token gap / prompt too long 分类；如果 provider 没有给出精确 gap，也要记录 `token_gap_status = "unknown"`。
4. 优先调用 `AutoCompactRunner.run(mode="emergency", trigger_reason="provider_context_limit_retry")`。
5. 如果 emergency compact 可构造并成功，用 emergency compact 产生的 canonical messages 重新 prepare。
6. 如果 emergency compact source projection 超限或 emergency compact 失败，并且 `ptl_retry_policy` 允许 fallback，则调用 `truncate_head_for_ptl_retry` 生成裁剪后的 retry messages。
7. `truncate_head_for_ptl_retry` 必须写出 `ptl_truncation_ref`，记录被省略 round 的 message ids、hash、token 估算、删除原因、保留边界和 synthetic marker id。
8. 最多重试一次主模型调用。
9. 如果重试成功，继续正常循环。
10. 如果重试仍然 `context_limit`，停止为 `context_limit_after_reactive_compact`。
11. 如果 emergency compact 和 PTL fallback 都失败，停止为 `reactive_compact_failed`。

当前 `AgentLoop` 会在模型响应后立即写 assistant artifact、assistant transcript，并把 assistant message append 到 `messages`。这对 Reactive Compact 有风险。需要把响应处理拆成两个阶段：

1. 先分类响应是否为可 reactive 的 provider context limit。
2. 如果是，不写普通 assistant message，不写 trainable assistant transcript，只写 provider failure event 和 reactive compact event。
3. 如果不是，再走原来的 assistant message 写入逻辑。

### 14.2 不变量

1. Reactive Compact 的语义摘要路径不维护自己的摘要 schema，必须复用 AutoCompact。
2. Reactive Compact 不因本地估算超限触发，只因真实 provider context limit 触发。
3. 每个主模型调用最多触发一次 Reactive Compact 重试。
4. 原始 provider context_limit 错误必须可审计，但不能进入普通可训练消息历史。
5. Proactive AutoCompact 的连续失败不应完全阻止一次 Reactive Compact，除非 compact-only 能力被配置关闭或全局不可用。
6. PTL fallback 不生成语义摘要，不假装理解被丢弃历史，只通过 synthetic marker 和审计 artifact 说明省略。
7. PTL fallback 不能删除半个 tool call / tool result 配对。

### 14.3 验证方式

新增或更新 `tests/unit/test_reactive_compact.py` 和 `tests/unit/test_agent_loop_protocol.py`：

1. fake model client 第一次返回 `context_limit`，Reactive Compact 成功，第二次主调用成功，验证 agent loop 继续。
2. 第一次返回 `context_limit` 时，失败 response 没有作为普通 assistant message 加入 retry messages。
3. Reactive Compact 的 compact-only request 使用 `mode="emergency"` 和 `trigger_reason="provider_context_limit_retry"`。
4. 第二次主调用仍返回 `context_limit`，验证停止为 `context_limit_after_reactive_compact`。
5. emergency compact 失败且 PTL fallback 禁用或失败，验证停止为 `reactive_compact_failed`。
6. 非 context_limit 的 provider error 不触发 Reactive Compact。
7. Reactive Compact 不超过一次重试限制。
8. `"prompt too long"` 和 `"context length"` 等 provider 文本会被归一化为 `context_limit`。
9. compact-only source projection 超限时，PTL fallback 按 API round 丢弃旧消息，保留 tool call / tool result 配对，并插入 synthetic user marker。
10. PTL fallback 的 retry 训练样本只包含裁剪后的输入和 synthetic marker，不能把被省略 round 拼回去。

执行命令：

```bash
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_reactive_compact.py tests/unit/test_agent_loop_protocol.py tests/unit/test_model_client_factory.py
PATH=.venv/bin:$PATH python -m compileall src
```

## 15. 第十一步：更新 inspect、export audit 和 failure diagnostics

### 15.1 实施内容

更新 `src/repo_harness/pre_verl_agentloop.py`：

1. prepared messages 检查需要识别 persisted tool result preview、MicroCompact 占位符、AutoCompact boundary、AutoCompact summary 和 recovery index。
2. 增加检查：`publishable_after_visibility_scan = true` 且 `recovery_unlocked_after_provider_commit = true` 的 persisted preview 必须包含恢复指令；派生的 `model_visible_recoverable = true` 只能在这两个条件同时满足后出现。不可恢复 preview 不能包含真实 `artifact_id`、内容 sha256 或恢复调用示例。
3. 增加检查：recovery index 不能引用 evaluator-only artifact。
4. 增加检查：compact summary 不能包含隐藏材料 marker。
5. 增加检查：compact-only model call 不作为普通 trainable assistant turn。
6. 增加检查：Reactive Compact 原始 context_limit provider error 没有进入 retry prepared messages。
7. 增加 compact-only 调用检查：`scaffold_phase = "compact"`、`allowed_tools = []`、`tool_choice = "none"` 或等价字段、`trainable = false`、没有普通 assistant transcript action。
8. 增加哈希链检查：`auto_compact_source_messages`、`auto_compact_summary`、`auto_compact_rebuilt_messages` 三类 artifact 必须互相引用，并且事件中的 hash 与 artifact 实际内容一致。

更新 `src/repo_harness/export/exporter.py` 和 `src/repo_harness/export/audit.py`：

1. compact-only model call 可以作为审计 metadata 导出，但不能作为普通训练样本 action。
2. `sft_jsonl` 和 `rl_jsonl` 必须按“每一次主模型调用”构建样本，并绑定该次主模型调用真实使用的 `prepared_messages_ref`。不能再用整条 transcript、第一份 prepared messages 或第一次工具观察反推出训练输入，否则 AutoCompact 或 MicroCompact 之后会把模型当时没有看到的旧内容写进训练样本，或者漏掉压缩后的真实输入。
3. `read_tool_result_artifact` 的调用是普通模型行为，可以作为训练轨迹的一部分，因为它是模型显式发起的恢复动作。
4. persisted 原文 artifact 是否导出给训练数据，需要按 visibility 控制。默认不直接进入训练样本，只通过模型可见 preview 和模型主动恢复的分页内容进入训练上下文。
5. export audit 的 hidden marker 和 blocked key 检查需要显式覆盖 `final_verifier_raw_output`、`accepted outcome`、`reward scalar`、`reward label`、hidden test、gold patch、selector 和 evaluator-only artifact。
6. preference pair 的 compare scope 需要纳入新的上下文压缩策略。`tool_result_compact_policy`、MicroCompact 策略、AutoCompact 策略、Reactive Compact 策略、模型上下文预算来源和关键阈值必须写入 run config facts，并进入偏好对可比较性检查。不同压缩策略或关键阈值不同的 run 不能被配成偏好对。
7. 新增 `ModelInputSnapshot` 或 `ModelCallTrainingSample`，每条主模型调用训练样本至少包含：

```text
model_call_id
turn
trainable
prepared_messages_ref
model_input_hash
provider_request_projection_hash
provider_request_ref
context_revision
context_policy_snapshot_ref
tool_result_compact_state_ref
microcompact_state_ref
auto_compact_state_ref
reactive_compact_state_ref
synthetic_marker_refs
source_event_ids
```

这个 snapshot 是训练样本的输入真相来源。`sft_jsonl`、`rl_jsonl` 和 preference export 都必须从它构造输入，不能从最终 transcript 反推。

更新 `src/repo_harness/run_metadata/writer.py`：

1. 新增或细化 failure type：`reactive_compact_failed`、`context_limit_after_reactive_compact`、`auto_compact_failed_preflight`。
2. 把 AutoCompact 成功但仍无法降到 hard limit 的情况归到压缩后仍不足，而不是普通 context_limit。
3. 在 failure details 中包含 `source_prepared_messages_ref`、`summary_artifact_ref`、`tokens_before`、`tokens_after`、`effective_context_budget_tokens`。
4. 把本地 hard preflight stop 和真实 provider Reactive Compact 分成两种策略写入 run metadata：`local_context_limit_policy = "strict_local_preflight"` 和 `reactive_compact_policy = "provider_verified_reactive"`。
5. 如果使用 PTL fallback，failure details 和 success diagnostics 都要包含 `ptl_truncation_ref`、synthetic marker id、omitted rounds 数量和 retry model call id。

### 15.2 不变量

1. 所有 inspect 失败信息必须直接指出 artifact 或事件路径，便于复核。
2. 训练导出不能泄漏 hidden test、gold patch、reward outcome、final verifier raw output。
3. compact-only 调用可以审计，但不能污染 trainable action 序列。
4. 模型主动调用 `read_tool_result_artifact` 的恢复内容属于模型可见轨迹，可以出现在后续 prepared messages。
5. 每个训练样本的输入必须能追溯到同一个主模型调用事件上的 `prepared_messages_ref`，不能跨轮次拼接或回填压缩前历史。
6. provider 返回 context_limit 的失败调用不能生成 trainable sample；Reactive Compact 重试成功后的样本必须绑定 retry 主模型调用的真实 input snapshot。

### 15.3 验证方式

更新以下测试：

1. `tests/unit/test_pre_verl_agentloop.py`
2. `tests/unit/test_export.py`
3. `tests/integration/test_export_from_run.py`
4. `tests/unit/test_run_metadata.py`

新增场景：

1. 运行中包含 persisted preview，inspect 通过。
2. 运行中 compact summary 含 hidden marker，inspect 失败。
3. 运行中 recovery index 指向 evaluator-only artifact，inspect 失败。
4. export audit 验证 compact-only model call 不进入 trainable samples。
5. export audit 验证模型主动恢复工具结果后的分页内容可以进入后续 observation。
6. `sft_jsonl` 和 `rl_jsonl` 中每个样本都绑定当轮真实 `prepared_messages_ref`。
7. preference export 拒绝把不同 context compact policy 或不同关键阈值的 run 配成偏好对。
8. export audit 发现 `final_verifier_raw_output`、reward scalar、reward label、accepted outcome 等隐藏信息时失败。
9. provider context_limit 失败调用没有 trainable sample；Reactive Compact retry 成功时，trainable sample 绑定 retry 的 `ModelInputSnapshot`。
10. exporter 不再使用第一份 prepared messages 或整条 transcript 推导样本输入。

执行命令：

```bash
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_pre_verl_agentloop.py tests/unit/test_export.py tests/unit/test_run_metadata.py tests/integration/test_export_from_run.py
PATH=.venv/bin:$PATH python -m compileall src
```

## 16. 第十二步：端到端压力验证和 targeted smoke 验证

### 16.1 分层集成验证

在端到端总管线测试之前，需要先增加分层集成测试，避免后续压缩层掩盖前一层缺陷。建议新增 `tests/integration/test_context_compaction_layers.py`，或者把 `tests/integration/test_context_compaction_pipeline.py` 参数化为多组场景。

至少覆盖以下场景：

1. 只触发单个工具结果过大落盘：验证 `tool_result_persisted`、preview、artifact manifest、恢复工具和 export audit。
2. 只触发当前轮工具结果聚合预算：验证 fresh-only candidate 选择、provider-committed 命运冻结、provider request projection 绑定和 inspect。
3. 只触发 MicroCompact：验证阈值双条件、白名单、保留最近 15 个、非白名单不被清理、幂等和 export audit。
4. 只触发 AutoCompact：验证 compact-only 模型调用、summary schema、压缩后 prepared messages、主模型调用绑定新 prepared messages。
5. 只触发 Reactive Compact：验证真实 provider context_limit 后 emergency compact 或 PTL fallback、一次重试、原始 provider error 不进入 retry prepared messages。

执行命令：

```bash
PATH=.venv/bin:$PATH python -m pytest -q tests/integration/test_context_compaction_layers.py
PATH=.venv/bin:$PATH python -m compileall src
```

### 16.2 本地合成压力验证

新增一个合成长上下文测试，建议放在 `tests/integration/test_context_compaction_v3.py` 或新增 `tests/integration/test_context_compaction_pipeline.py`。

测试任务应构造：

1. 多轮工具调用。
2. 多个 40,000 字符左右的工具结果，触发当前轮聚合预算。
3. 超过 30 个可清理工具结果，触发 MicroCompact。
4. 总 token 估算超过 AutoCompact 阈值，触发 AutoCompact。
5. fake provider 第一次返回 `context_limit`，触发 Reactive Compact。

验证：

1. `context_prepared` event 数量合理。
2. `tool_result_persisted` event 存在。
3. `microcompact_applied` event 存在。
4. `auto_compact_applied` event 存在。
5. `reactive_compact_triggered` event 存在。
6. 最终主模型调用绑定的是压缩后的 prepared messages。
7. inspect 通过。
8. export audit 通过。

执行命令：

```bash
PATH=.venv/bin:$PATH python -m pytest -q tests/integration/test_context_compaction_pipeline.py
PATH=.venv/bin:$PATH python -m compileall src
```

### 16.3 targeted smoke 验证

在单元测试和合成集成测试通过后，再恢复 targeted smoke。不要在四层压缩没有全部完成前继续用真实模型跑 23 条任务，否则容易把 harness 压缩缺陷误判为模型能力问题。

建议 smoke 阶段分三批：

1. 先跑 2 条高工具输出任务，验证工具结果恢复和 MicroCompact。
2. 再跑 5 条长上下文任务，验证 AutoCompact 是否减少 context_limit。
3. 最后再跑完整 targeted smoke，和 `runs/pre-verl-agentloop-targeted-smoke-deepseek-flash-tool-capability-guidance-20260508T133407Z` 的结果对比。

每批都要检查：

1. `repo-harness inspect-model-visible-context <run_dir> --assert-prepared-messages-bound --assert-provider-body-equivalent --assert-tool-results-recoverable --assert-no-hidden-test-material`
2. `repo-harness inspect-pre-verl-agent-runtime-audit <runtime_report.json> --assert-runtime-invariants-clean`
3. `repo-harness inspect-pre-verl-export-audit <export_audit_manifest.json> --assert-export-clean`
4. `repo-harness inspect-export <export_dir> --all --assert-clean --require-trainable-samples`
5. `repo-harness inspect-pre-verl-agent-evaluation <agent_evaluation_report.json> --assert-agent-evaluation-readiness-complete`
6. 是否存在 hidden material marker。
7. context_limit 数量是否下降。
8. 模型是否能通过 `read_tool_result_artifact` 恢复需要的旧内容。

具体命令需要根据当时生成的 run manifest 路径填写，不能使用“latest run”隐式路径。

## 17. 事件和 artifact 命名建议

建议新增或标准化以下事件类型：

1. `tool_result_persisted`
2. `tool_result_budget_applied`
3. `microcompact_applied`
4. `auto_compact_triggered`
5. `auto_compact_model_call_started`
6. `auto_compact_model_call_completed`
7. `auto_compact_applied`
8. `auto_compact_failed`
9. `reactive_compact_triggered`
10. `reactive_compact_retry_started`
11. `reactive_compact_retry_completed`
12. `reactive_compact_failed`
13. `context_limit_after_reactive_compact`
14. `provider_request_materialized`
15. `model_input_accepted`
16. `ptl_truncation_applied`

建议新增或标准化以下 artifact kind：

1. `tool_result_original_content`
2. `tool_result_compact_state`
3. `microcompact_record`
4. `auto_compact_source_messages`
5. `auto_compact_summary`
6. `auto_compact_rebuilt_messages`
7. `auto_compact_state`
8. `reactive_compact_failure`
9. `context_policy_snapshot`
10. `model_input_snapshot`
11. `provider_request_projection`
12. `ptl_truncation_record`
13. `rehydration_source_read`

这些命名要进入 inspect allowlist，避免 artifact manifest 检查把新 artifact 当成未知产物。

## 18. 分层验收矩阵

每一层压缩都必须同时具备单元测试、分层集成测试、inspect/export 验证和失败路径验证。不能只依赖最后的端到端压力测试。

| 压缩层 | 单元测试 | 分层集成测试 | inspect/export 验证 | 失败路径验证 |
|---|---|---|---|---|
| L0A 单个工具结果落盘 | 大输出、小输出、失败工具大输出、preview 稳定性、恢复工具分页 | 只触发单个大工具结果，验证 transcript、events、artifact manifest | `inspect-model-visible-context --assert-tool-results-recoverable`；`inspect-export --assert-clean` 验证原文 artifact 不直接进入训练样本 | artifact 写入失败；不可恢复内容不暴露 sha256 和恢复调用；非法 artifact_id 被拒绝 |
| L0B 当前轮聚合预算和 provider-committed 命运冻结 | fresh candidate 选择、provider-committed full visible 冻结、persisted preview 字节级复用、旧历史不被第零层改写 | 只触发同一轮多工具结果聚合超限，验证最大 fresh result 优先落盘；context warning re-prepare 不冻结第一次 candidate | prepared messages 绑定检查；provider request projection hash；content state hash；export 样本绑定当轮真实 `ModelInputSnapshot` | state hash 漂移；重复 prepare 产生不同 preview；未 provider-committed candidate 被错误冻结；已 frozen full result 被错误替换 |
| L1 MicroCompact | 阈值双条件、白名单、保留最近 15 个、幂等、tool pairing、原始事实保留 | 只触发 MicroCompact，验证非白名单不被清理，状态类消息保留 | inspect 验证占位符合法；export audit 验证每轮真实 prepared messages 绑定；raw trajectory 保留原始工具结果事实 | 非白名单工具被清理；MicroCompact record 数量不匹配；重复清理导致 hash 漂移；原始事实被销毁 |
| L2 AutoCompact | compact-only 无工具、summary schema、污染扫描、provider request projection、post target 逻辑 | 只触发 AutoCompact，验证 source、summary、rebuilt messages 的 artifact 引用和哈希链；compact-only source 超限时不生成伪摘要 | compact-only 不进入 trainable sample；主模型调用绑定压缩后 `ModelInputSnapshot`；rehydration_source_read 可审计 | 非 JSON summary；hidden marker；compact-only request artifact 缺失；source prepared hash 不匹配；compact-only source 超限；压缩后仍超 hard limit |
| L3 Reactive Compact | 真实 provider context_limit 触发、最多一次重试、非 context_limit 不触发、PTL fallback | fake provider 第一次 context_limit、emergency compact 后重试成功或失败；compact-only source 超限时 round truncation retry | 原始 provider error 可审计但不进 retry prepared messages；compact-only 不进 trainable sample；PTL synthetic marker 进入 retry input snapshot | emergency compact 失败；PTL fallback 失败；二次 context_limit；原始 provider error 进入 retry history；Reactive Compact 被本地 preflight 误触发；tool pair 被截断 |

## 19. 分阶段验收标准

第一阶段验收：工具结果层。

1. 单个工具结果超过 50000 字符会立即落盘。
2. 当前轮 fresh 工具结果聚合超过 200000 字符会落盘最大的 fresh 结果。
3. full visible 和 persisted preview 的命运冻结只在 provider-committed 主模型输入之后发生。
4. `read_tool_result_artifact` 可以安全分页恢复。
5. 旧历史老化替换默认关闭。

第二阶段验收：MicroCompact。

1. 触发条件为数量和字符数同时满足。
2. 保留最近 15 个可清理工具结果。
3. 不清理状态类消息。
4. 幂等检查通过。
5. tool pairing validation 通过。

第三阶段验收：AutoCompact。

1. 有效上下文预算基于模型上下文窗口和可选 harness cap。
2. 达到 0.85 触发比例时，会基于 provider request projection 发起 compact-only 模型调用。
3. compact-only 调用没有工具、不是普通 assistant action、不是 trainable sample。
4. 压缩后消息结构包含 boundary、summary、近期尾部和恢复索引。
5. 压缩后如果高于目标但低于 hard limit，不立即重复压缩。
6. 压缩后主模型调用绑定新的 prepared messages。

第四阶段验收：Reactive Compact。

1. 只有真实 provider context_limit 触发。
2. 原始失败可审计但不进入 retry canonical messages。
3. 优先复用 AutoCompact emergency 模式。
4. 最多重试一次。
5. compact-only 输入本身超限或 emergency compact 不可用时，可以进入 PTL fallback。
6. PTL fallback 按 API round 裁剪，保持 tool call / tool result 配对，并插入 synthetic user marker。
7. 二次 context_limit、emergency compact 失败或 PTL fallback 失败时，停止原因清晰。

第五阶段验收：训练导出和简历展示。

1. inspect 全部通过。
2. export audit 全部通过。
3. hidden/gold/final verifier raw material 不出现在 prepared messages 或训练样本中。
4. 每条训练样本都来自对应主模型调用的 `ModelInputSnapshot`，包含 exact `prepared_messages_ref`、`provider_request_projection_hash` 和 context policy snapshot。
5. 新增压缩事件和 artifact 能支撑简历展示：可以解释每次压缩发生的原因、输入、输出、摘要、恢复路径和 PTL 截断边界。

## 20. 推荐提交拆分

建议按以下提交拆分实现，便于 review 和回滚：

1. `feat: add context compact config and schemas`
2. `feat: add tool result artifact recovery`
3. `feat: persist oversized tool results`
4. `feat: apply fresh tool result budget with provider-committed decisions`
5. `feat: add tool result microcompact`
6. `feat: add effective context budget calculation`
7. `feat: add auto compact runner`
8. `feat: rebuild messages after auto compact`
9. `feat: integrate proactive auto compact into agent loop`
10. `feat: add provider verified reactive compact retry`
11. `test: add context compact pipeline coverage`
12. `docs: bind context compact implementation evidence`

## 21. 主要风险和缓解方式

风险一：恢复工具泄漏 evaluator-only artifact。

缓解方式：恢复工具只能读取 `ToolResultArtifactIndex` 中同时满足 `publishable_after_visibility_scan = true` 和 `recovery_unlocked_after_provider_commit = true` 的 artifact。`model_visible_recoverable = true` 只能作为这两个条件同时满足后的派生字段。恢复工具不能接收路径，不能读取任意 artifact ref，也不能读取 prepared candidate 阶段生成但后来没有进入 provider-committed 可见上下文的 artifact。

风险二：AutoCompact 摘要引入隐藏信息。

缓解方式：compact-only 输入只来自 `source_prepared.messages`，摘要输出通过污染扫描，inspect 再做二次检查。

风险三：Reactive Compact 把 provider context_limit 错误作为普通 assistant message 写入 retry 历史。

缓解方式：拆分模型响应处理流程，在写 assistant transcript 和 append messages 前先处理 reactive trigger。

风险四：压缩后破坏 tool call 和 tool result 配对。

缓解方式：所有消息重建和 MicroCompact 都只能在完整配对边界上操作，每次 prepare 后强制运行 `_validate_tool_pairing()`。

风险五：token 估算偏差导致仍然触发 provider context_limit。

缓解方式：保留 `estimator_safety_margin_ratio` 和 `estimator_safety_margin_min_tokens`，并用 Reactive Compact 作为真实 provider 错误兜底。

风险六：compact-only 调用污染训练导出。

缓解方式：事件和 transcript 明确标记 `scaffold_phase = "compact"`、`trainable = false`，export audit 增加检查。

## 22. 完整验证命令集合

完成所有改造后，至少执行：

```bash
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_context_manager.py
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_tool_result_artifacts.py tests/unit/test_tool_result_compact.py tests/unit/test_microcompact.py
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_context_budget.py tests/unit/test_auto_compact.py tests/unit/test_compact_rebuild.py tests/unit/test_reactive_compact.py
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_agent_loop_protocol.py tests/unit/test_pre_verl_agentloop.py tests/unit/test_export.py tests/unit/test_run_metadata.py tests/unit/test_model_input_snapshot.py
PATH=.venv/bin:$PATH python -m pytest -q tests/integration/test_tool_execution.py tests/integration/test_export_from_run.py tests/integration/test_context_compaction_layers.py tests/integration/test_context_compaction_pipeline.py
PATH=.venv/bin:$PATH python -m pytest -q
```

如果某些新增测试文件尚未创建，对应命令应在实现该阶段时创建测试文件后执行。最终合并前必须执行完整 `python -m pytest -q`。

针对实际生成的 run artifact，还必须显式执行以下 inspect/export 命令。命令中的路径必须替换为该次运行真实生成的路径，不能使用 latest run 或隐式目录：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-model-visible-context <run_dir> --assert-prepared-messages-bound --assert-provider-body-equivalent --assert-tool-results-recoverable --assert-no-hidden-test-material
PATH=.venv/bin:$PATH repo-harness inspect-pre-verl-agent-runtime-audit <runtime_report.json> --assert-runtime-invariants-clean
PATH=.venv/bin:$PATH repo-harness inspect-pre-verl-export-audit <export_audit_manifest.json> --assert-export-clean
PATH=.venv/bin:$PATH repo-harness inspect-export <export_dir> --all --assert-clean --require-trainable-samples
PATH=.venv/bin:$PATH repo-harness inspect-pre-verl-agent-evaluation <agent_evaluation_report.json> --assert-agent-evaluation-readiness-complete
```

## 23. 最终结论

当前 RepoHarness 的压缩机制应从“历史工具结果老化替换”升级为“工具结果稳定落盘、provider-committed 命运冻结、MicroCompact 控制旧工具结果膨胀、AutoCompact 进行语义摘要、Reactive Compact 处理真实 provider 超限并具备 PTL fallback”的多层管线。

实施时最重要的约束不是尽可能压缩得多，而是保证四件事：

1. 模型看到的内容来源清晰。
2. 工具结果可以安全恢复。
3. hidden/evaluator-only/reward/gold/final verifier raw 信息不会泄漏。
4. 每一次主模型训练样本都绑定真实 `ModelInputSnapshot`，不能从最终 transcript 反推。
5. 每次压缩都有事件、artifact 和 inspect 证据，能够支撑训练导出和简历展示。
