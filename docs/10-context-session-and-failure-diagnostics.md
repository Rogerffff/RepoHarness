# Context, Session, And Failure Diagnostics

## 设计目标

软件工程 agent 的长轨迹会快速膨胀上下文：文件内容、搜索结果、测试输出、错误日志和多轮 patch 都可能占用大量 token。RepoHarness 必须从设计阶段就规划上下文和失败诊断。

当前实现状态需要和历史 V1 设计区分：V3 已经实现 context compaction 和 long rollout diagnostics；V4 增加 batch resume、checkpoint state、resource lock 和 rollout resume 审计。这些能力用于单机 experiment / batch resume 和轨迹审计，不等同于 P1-3 session continuation、跨会话长期记忆、任意中间 turn 恢复，也不能继承 hidden verifier、reward 或 outcome facts。

## 上下文增长问题

主要来源：

- 多次读取大文件。
- 搜索结果过多。
- 测试输出过长。
- 失败重试反复产生类似日志。
- verifier 输出和 patch diff 叠加。

如果不控制，上下文限制会变成主要失败原因。

## 第一版上下文策略

第一版不需要复制 Claude Code 的完整 LLM auto compact、session memory compact 或 context collapse，但不能把上下文压缩完全后置。RepoHarness 至少需要一个确定性的 `ContextManager`，在每次模型调用前执行可复现的 context reduction policy：

- 工具完整输出全部写入 run directory，并通过 `ArtifactRef` 进入 `artifacts.json`。
- 模型上下文只放 `content_preview`、关键失败片段、结构化摘要和 artifact 引用说明，不直接塞入完整 stdout、stderr、大文件内容或大搜索结果。
- 超出 `tool_result_aggregate_budget_chars` 时，按稳定顺序替换较旧的 tool result，而不是随机丢弃消息。
- 保留最近 `keep_recent_turns` 轮的消息和最近 `keep_recent_test_results` 次 feedback verifier 结果。
- 较旧测试输出变成结构化摘要，例如失败测试 id、错误类型、关键 traceback 首尾片段和 `summary_artifact_ref`。
- 重复 `read_file`、`grep` 和测试日志应优先替换为 ArtifactRef preview，避免同一内容多次消耗上下文。
- 压缩或替换后必须重新校验 tool call / tool result 配对。
- 如果确定性裁剪后仍超过 `max_context_tokens`，应停止为 `agent_stop_reason = "context_limit"`，而不是继续提交可能被 provider 拒绝的请求。

`ContextManager` 的第一版目标是“可实现、可复盘、可导出训练数据”，不是语义记忆。复杂自动 compact、跨 session memory、向量检索式记忆和 LLM 生成长摘要都可以作为后续扩展。

## ContextManager 最小契约

第一版 `ContextManager` 应提供：

```text
ContextManager.prepare_messages(messages, budget_state, tool_pairing_state) -> PreparedMessages
```

`PreparedMessages` 至少包含：

- `messages`：本轮真实发送给模型的 provider-ready messages。
- `prepared_messages_ref`：本轮 provider-ready messages 落盘后的 `ArtifactRef`。
- `model_input_hash`：本轮 provider-ready messages、工具 schema 和关键 provider formatting 字段的稳定 hash。
- `context_revision`：本次上下文版本。
- `context_event`：写入 events 的上下文变化记录。
- `content_replacement_state`：稳定的替换决策状态。
- `token_estimate`：本轮输入 token 估计。

为了保证 transcript、实际模型输入和训练导出一致，替换决策必须稳定。第一版应维护两层结构：`ContentReplacementState` 表示跨轮次、session resume 和训练导出的状态集合；`ContentReplacementRecord` 表示某一个 tool result 的替换记录。

```text
ContentReplacementState:
  context_policy_version
  seen_tool_result_ids
  records: map[tool_result_id, ContentReplacementRecord]
  state_hash
  last_context_revision

ContentReplacementRecord:
  tool_call_id
  original_tool_result_id
  replaced: true | false
  first_visible_form: full | preview | replacement
  first_visible_content_hash
  replacement_allowed_after_first_seen: true | false
  replacement_text_hash
  replacement_artifact_refs
  replacement_preview_hash
  first_replaced_at_context_revision
  first_seen_at_context_revision
```

`records` 必须覆盖所有已经进入过模型可见上下文的 tool result，包括已经替换的、尚未替换的、以及第一次出现时就是 preview / replacement 的结果。`seen_tool_result_ids` 可以作为快速索引，但不能替代 `records`。这样可以区分两种情况：某个结果曾经被模型完整看过，后来因为预算压力被替换；另一个结果从第一次进入上下文起就是 replacement preview。训练导出时必须按对应 `context_revision` 使用当时模型实际看到的版本，而不是统一使用最终压缩后的版本。

同一个 tool result 第一次被替换后，后续轮次、session resume 和训练导出都应复用同一段 replacement preview，不能每次重新生成不同摘要。`state_hash` 用于检测 resume 或导出阶段是否复用了同一份替换状态。这样才能回答“模型这一轮到底看到了什么”，也能保证 observation mask 对应的是当时实际可见内容。

## Budget Manager

第一版应把分散预算收敛成统一 `BudgetManager` 或 `BudgetState`，避免长轨迹运行不可控：

```text
BudgetManager:
  max_turns
  max_tool_calls
  max_test_runs
  task_timeout_sec
  command_timeout_sec
  verifier_timeout_sec
  max_tool_output_chars
  max_context_tokens
  max_output_tokens
  max_cost
  max_artifact_bytes
  max_concurrent_tasks
```

每一种预算耗尽都必须产生结构化 event，并映射到明确字段：

- `max_turns` 和 `max_tool_calls` 映射到 `agent_stop_reason`。
- `command_timeout_sec` 映射到工具级 timeout tool result。
- `verifier_timeout_sec` 映射到 `VerifierResult(timeout = true)` 和 `final_verifier_status = "timeout"` 或 feedback verifier event。
- `max_context_tokens` 映射到 context truncation、compaction 或最终 `context_limit`。
- `max_artifact_bytes` 映射到 artifact 写入失败或截断事件，不能无声丢弃完整日志。

## Session Resume

第一版 session resume 不承诺恢复到任意中间 turn。没有 per-turn workspace checkpoint 或 patch chain 时，仅凭 `final.diff`、`transcript.jsonl` 和 `events.jsonl` 不能可靠恢复到“最后一个稳定 turn”。

V3/V4 的 experiment resume、batch resume、checkpoint state 和 resource lock 审计，是运行队列和批量实验层面的可恢复性；它们不是长期 session continuation，也不是允许模型在恢复后看到隐藏验证结果、reward 结果或最终 outcome 事实的机制。

第一版应把 resume 降级为“从 final workspace 继续”：

- 读取 `transcript.jsonl`。
- 读取 `events.jsonl`。
- 读取 `final.diff`。
- 用任务 source checkout、`dependency_state` 和 `final.patch` 重建 final workspace。
- 重新运行 verifier。
- 以新的 `run_id` 继续，记录 `parent_run_id` 和 `resume_from = "final_workspace"`。

resume 不要求恢复每个未完成工具进程。未完成工具必须标记为 interrupted 或 timeout。

如果未来希望恢复到中间 turn，必须额外设计至少一种可恢复依据：

- `checkpoints/turn_0007.patch` 形式的 per-turn patch chain。
- `checkpoints/turn_0007_workspace/` 形式的 workspace snapshot。
- `events.jsonl` 中可重放且确定性的文件写入事件序列。

在没有这些 artifact 之前，文档和实现都不应声称可以恢复到任意中间稳定 turn。

## Timeout、进程清理与 Interrupted Artifact

timeout 不是单一错误类型，必须区分来源：

- 工具 timeout：当前工具调用结束，生成 timeout tool result，模型可以在预算内继续。
- 命令 timeout：Workspace Adapter 负责终止进程树，保存 stdout/stderr preview 和完整 artifact。
- verifier timeout：生成结构化 `VerifierResult(timeout = true)`，final verifier timeout 进入最终评测状态。
- 单任务全局 timeout：终止 agent loop，未完成 tool call 补齐 interrupted tool result。

local process mode 应使用 process group 或等价机制清理子进程。Docker execution mode 应记录容器停止、清理和 artifact 保存状态。任何被中断的命令都应尽量保存 interrupted artifact，方便失败诊断。

## Failure Diagnostics

标准失败类型：

- `dependency_install_failed`
- `test_timeout`
- `assertion_failure`
- `permission_denied`
- `invalid_tool_call`
- `context_limit`
- `patch_apply_failed`
- `no_progress`
- `regression_detected`

每次失败必须能关联到 task、turn、tool、workspace state 和 verifier result。

## 失败类型、终止原因和重试策略

终止原因、verifier error type 和 failure diagnostics 需要统一口径。未来实现应维护一张机器可读分类表，至少包含：

| failure type | 典型来源 | 是否允许模型重试 | 是否直接终止运行 |
| --- | --- | --- | --- |
| `dependency_install_failed` | baseline setup | 否 | 是，任务标记为 invalid |
| `test_timeout` | feedback verifier 或 final verifier | 可以，预算内允许修复 | 否，除非超过全局 timeout |
| `assertion_failure` | verifier parser | 可以 | 否 |
| `permission_denied` | permission event | 可以，模型可换低风险方案 | 视权限模式而定 |
| `invalid_tool_call` | tool schema validation | 可以 | 否，除非超过无效调用预算 |
| `context_limit` | context manager | 通常否 | 是，除非压缩后可恢复 |
| `patch_apply_failed` | workspace adapter | 可以 | 否 |
| `no_progress` | repeated failure heuristic | 否 | 由 scaffold 和 BudgetManager 策略决定 |
| `regression_detected` | final verifier | 可以，若仍有预算 | 否，最终无预算时失败 |

这些分类应进入 events、metrics 和 summary。训练导出可以根据这些字段过滤无效轨迹，或者保留有诊断价值的失败轨迹作为偏好数据。

`run_outcome` 的确定性派生表定义在 `03-agent-loop-and-message-protocol.md`。Failure diagnostics 只解释失败来源和重试策略，不应覆盖最终评测口径。

## No Progress 检测

`no_progress` 不应在第一版里变成随意的人工判断。第一版可以采用保守启发式，或者把它只作为诊断标签而非默认终止原因。

建议第一版最小规则：

- 连续 N 次 feedback verifier 的 fail-to-pass、pass-to-pass 和 error type 完全没有改善。
- 连续 N 次编辑后 `final.diff` 的有效源码改动没有变化，或者反复恢复同一段 patch。
- 连续 N 次工具调用都因为同一 schema 错误、权限拒绝或不存在路径失败。
- N 的默认值写入 `RunConfig` 或 `BudgetManager`，例如 `no_progress_patience = 3`。

触发时应记录 `no_progress_event`，包含最近 verifier 摘要、diff hash、失败工具类型和策略版本。是否终止由 scaffold 和 BudgetManager 决定；批量评测第一版可以把它映射为 `agent_stop_reason = "no_progress"`，本地调试也可以只记录诊断并继续。

## Operational Telemetry 边界

RepoHarness 的事实数据是 transcript、events、verifier、metrics 和 artifact manifest。实现时可以额外生成 operational telemetry，用于本地调试性能、调用栈和内部错误，但它默认不进入训练导出。

telemetry 要求：

- 可以关闭。
- 不包含未脱敏密钥、私有路径或大段源码。
- 不作为 reward 或 success rate 的唯一依据。
- 若被保存，应带 `schema_version`，并和训练 trajectory 数据分开。

## 面试案例

准备三个面试案例：

1. 权限和 sandbox 边界：解释 permission 决定是否执行，Docker execution mode 决定执行边界，但不声称生产级安全沙箱。
2. verifier reward 与评测一致性：解释为什么 shared verifier 能减少 reward/eval 口径漂移。
3. 长轨迹失败诊断：展示一次任务因为上下文、测试超时或 patch 回归失败，如何从 events 追踪原因。

## Claude Code 参考

参考模块：

- `reference/claude-code-docs/claude-doc/10-context-memory-session.md`
- `reference/claude-code-typescript-src/services/compact/autoCompact.ts`
- `reference/claude-code-typescript-src/services/compact/microCompact.ts`
- `reference/claude-code-typescript-src/services/SessionMemory/`

RepoHarness 只借鉴上下文治理思想，第一版不实现完整自动 compact 系统。
