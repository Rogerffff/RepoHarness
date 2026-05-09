# Pre-verl 工具结果 Compact 决策记录

更新时间：2026-05-10

本文单独记录 RepoHarness 后续上下文压缩体系中“工具结果 compact”、紧邻的 MicroCompact（微压缩）借鉴决策，以及在这两层之上的 AutoCompact（自动语义压缩）设计。它是 `docs/resume/pre-verl-context-compaction-claude-code-gap-analysis.md` 的补充文档，但不继续扩展那份总览文档，避免把工具结果入口治理、旧工具结果轻量清理、语义摘要、会话记忆和恢复机制混在同一个设计层里。

本文已经确认的决策包括：单个工具结果过大时立即落盘、当前这一轮工具结果聚合过大时落盘、借鉴 Claude Code time-based MicroCompact 思路做 count / pressure based MicroCompact、不依赖 subagent 的同步 AutoCompact，以及 provider verified Reactive Compact 兜底。本文暂不把 Context Collapse 作为主线实现；Session Memory 留到 AutoCompact 稳定之后再设计。Snip Compact 暂时不作为主线机制实现，最多保留为后续 emergency fallback（紧急兜底）思想。

2026-05-10 复核后补充一个更严格的不变量：**所有会影响训练样本真实性的“模型看过什么”的状态，都必须以真实主模型调用绑定的 provider request 为准，不能以 `prepare_messages()` 的候选结果为准。** 也就是说，`prepare_messages()` 可以生成 candidate prepared messages，但只有某个 candidate 被主模型调用、provider request projection 和后续模型调用事件绑定后，它才可以成为训练导出的模型输入事实。

## 1. 最终决策

RepoHarness 后续工具结果 compact 先保留两层，向 Claude Code 的工具结果治理方式靠拢：

1. **单个工具结果过大时立即落盘。**
   工具执行完成后，如果单个工具结果超过单结果大小阈值，就把完整输出写入当前 run 的不可变 artifact，模型上下文只保留短 preview、artifact 引用、sha256 和安全恢复方式。

2. **当前这一轮工具结果聚合过大时落盘。**
   每次模型调用前，检查上一轮新增工具结果在同一轮模型可见消息中的聚合大小。如果这一轮多个工具结果合计超过阈值，就从最大的 fresh tool result（尚未进入 provider-committed 主模型输入的工具结果）开始落盘替换，直到这一轮新增工具结果回到预算以内。

同时采用 Claude Code 风格的命运冻结规则，但冻结时机必须比初版设计更晚：

```text
某个 tool_result 第一次进入 provider-committed 主模型输入时：
- 如果 provider-committed 输入里是 persisted preview，以后每一轮都复用完全相同的 replacement preview。
- 如果 provider-committed 输入里是完整内容，以后不再由工具结果预算层替换。
```

也就是说，工具结果预算层只处理尚未 provider-committed 的 fresh tool result。已经进入 provider-committed 历史的工具结果，不再由这一层做“老化替换”。

在这两层之后，增加一层独立的 count / pressure based MicroCompact。它不是工具结果预算层，也不改变上面的命运冻结规则；它只在旧 compactable tool result 数量和可见内容量都已经明显偏大时，把更旧工具结果的 `content` 改成固定占位符：

```text
[Old tool result content cleared]
```

MicroCompact 的初始决策如下：

```text
当 compactable tool result 数量 >= 30
并且 compactable tool result 可见内容总量 >= 60,000 字符时，
触发 MicroCompact；
保留最近 15 个 compactable tool result；
更旧 compactable tool result 的 content 设置为 [Old tool result content cleared]。
```

这三项工具结果相关决策分别解决不同问题：

```text
单个工具结果过大时立即落盘：
  防止一次工具调用返回过大的模型可见内容。

当前这一轮工具结果聚合过大时落盘：
  防止同一轮多个工具调用合计过大。

count / pressure based MicroCompact：
  在旧工具结果已经很多、内容量也很大时，用占位符清理旧工具结果内容。
```

在 L0 工具结果 compact 和 L1 MicroCompact 之上，新增 L2 AutoCompact：

```text
AutoCompact：
  当模型可见上下文接近当前模型的有效上下文预算时，
  通过一次独立的 compact LLM 请求生成结构化摘要，
  然后用 compact boundary、compact summary、最近原文尾部和确定性恢复材料重建下一轮主模型输入。
```

## 2. 删除或暂停第三层历史老化压缩

之前讨论过“第三层：历史上下文老化压缩”，也就是当历史中所有工具结果总量过大时，把较旧工具结果后续替换成 preview。这个方向与当前 RepoHarness 已有实现相近，但它会带来一个不理想的行为：某个工具结果第一次完整进入模型上下文后，后续轮次可能突然变成 replacement preview。

这个行为对训练轨迹和长任务连续性都有副作用：

- provider-ready messages 的历史前缀会变化，不利于 prompt cache 稳定。
- 模型上一轮看过完整内容，下一轮同一位置变成 preview，容易产生上下文断裂。
- 训练导出时需要解释“同一个历史工具结果在不同 context revision 中为什么可见形态不同”。
- 后续实现 Claude Code 风格的 Snip Compact、Microcompact、Context Collapse 和 AutoCompact 时，层级职责会变得混乱。

因此，后续主线设计中不再把“历史工具结果老化替换”作为工具结果 compact 的职责。这个策略可以保留为 legacy fallback（旧策略回退）或迁移期兼容选项，但不作为新上下文压缩体系的主线。

新的职责划分是：

```text
工具结果 compact：
  控制 fresh tool result 第一次进入 provider-committed 主模型输入时的大小。

后续上下文 compact：
  控制已经进入历史的旧内容如何被裁剪、清理、折叠、摘要或重建。
```

## 3. 为什么要采用 provider-committed 命运冻结规则

Claude Code 的 `applyToolResultBudget` 有一个非常重要的不变量：某个工具结果的可见形态一旦进入真实模型调用前缀，就不能在后续轮次随意改变。RepoHarness 后续也应采用这个不变量，但不能把“第一次进入 `prepare_messages()`”误认为“模型已经看过”。

原因是当前 RepoHarness 主循环可能在真正调用 provider 之前多次准备上下文。例如第一次 `prepare_messages()` 后发现需要插入 context warning，然后会重新准备一次上下文。第一份 prepared messages 只是 candidate，不一定会进入真实 provider request。如果此时就把工具结果冻结为 full visible 或 persisted preview，训练导出会记录一个模型实际上没有看到的状态。

建议在状态中把工具结果分成三类：

```text
must_reapply:
  之前已经替换过。
  本轮必须复用同一段 replacement preview。

frozen:
  之前已经 provider-committed 进入主模型输入，但当时没有替换。
  本轮不能再由工具结果预算层替换。

fresh:
  尚未出现在 provider-committed 主模型输入中。
  可以根据单结果预算和本轮聚合预算产生 candidate decision。
```

同时把 compact state 和主模型输入边界拆成三个概念：

```text
prepared_candidate:
  某次 prepare_messages 产生的候选决策。
  可以记录 candidate_prepared_messages_ref、candidate_model_input_hash、
  candidate_decisions 和 candidate_state_hash。
  它不能被当作“模型已经看过”的事实。

provider_request_materialized:
  主模型请求体已经由统一 provider request projection 构造器生成，
  并写入 raw provider request / provider request projection artifact。
  这个阶段只能证明“请求准备发送”，不能证明 provider 已经接受或模型已经消费输入。

model_input_accepted / provider_committed:
  provider 返回非 context_limit、非 prompt too long 的结果，
  并且可以认为模型实际消费了该输入。
  只有进入这个阶段，才能把工具结果命运从 fresh 推进为 full_visible 或 persisted_preview。
```

如果 provider 返回的是 `context_limit`、`prompt too long` 或本地 hard preflight 直接停止，则这次 candidate 不能升级为“模型已看过”。即使 provider request 已经 materialized 并写入 artifact，也只能作为失败诊断和 Reactive Compact 的输入边界，不能提交工具结果命运，不能解锁恢复 artifact，也不能生成 trainable `ModelInputSnapshot`。

这个设计带来的收益是：

- 同一段历史前缀更稳定。
- 已替换工具结果的 replacement preview 字节级稳定。
- 已完整进入模型上下文的工具结果不会在后续轮次被这一层改写。
- 训练导出可以直接解释每个 tool result 第一次进入 provider-committed 主模型输入时的可见形态。
- 后续 Snip Compact、Microcompact、Context Collapse 和 AutoCompact 可以明确接管历史压缩，不需要和工具预算层抢职责。

## 4. 当前 RepoHarness 机制与新决策的差异

当前 RepoHarness 的 `ContextManager` 主要做的是 deterministic preview replacement（确定性预览替换）。它会扫描当前消息历史中的工具结果，当历史工具结果聚合大小超过预算时，优先替换较旧且未受保护的工具结果。

当前机制的优点是：

- 可审计。
- 可复盘。
- replacement preview 稳定。
- 完整工具输出仍保留在 artifact 中。
- 能在没有语义 compact 的情况下缓解长工具输出带来的上下文压力。

但与新决策相比，它的问题是：

- 它会对已经进入历史的旧工具结果做后续替换。
- 它检查的是历史工具结果聚合压力，而不是 Claude Code 风格的“单个工具结果”和“同一轮新增工具结果聚合压力”。
- 它的 `recovery_call` 多数情况下是建议模型重新执行 `read_file`、`grep`、`list_files`、`git_diff` 等工具，而不是读取当时那次工具调用的不可变原始输出。
- 重新执行工具不一定能恢复旧输出，因为文件内容、工作区状态、测试结果或搜索结果可能已经变化。

因此，新设计不是在当前策略上继续加复杂逻辑，而是把工具结果 compact 的职责前移到“工具结果第一次进入 provider-committed 主模型输入之前”。

## 5. 安全恢复方式

当前 replacement 文本中的 `recovery_call` 不应继续作为唯一恢复方式。它可以作为“重新执行工具”的提示保留，但不能被视为安全、精确、可复现的上下文恢复机制。

后续建议新增一个只读工具，例如：

```text
read_tool_result_artifact(artifact_id, offset=0, limit=8000)
```

这个工具的职责是读取当前 run 中已经通过正向登记、可见性检查和污染扫描，并且允许模型恢复的工具结果 artifact。它读取的是当时那次工具调用的不可变输出，而不是重新运行工具。

这里的 `artifact_id` 必须是 `ToolResultArtifactIndex` 发放的恢复能力标识，不是文件系统路径，不是普通 `ArtifactRef`，也不是 artifact manifest 中任意条目的 id。

`ToolResultArtifactIndex` 必须把“可发布候选”和“已解锁可恢复”拆开：

```text
publishable_after_visibility_scan:
  工具结果 artifact 已通过可见性检查和污染扫描，
  没有 evaluator-only、secret、redacted-only 或 hidden material 风险。
  这只表示它未来可以被 preview 发布，不表示模型已经获得恢复权限。

recovery_unlocked_after_provider_commit:
  包含该 artifact_id 的 preview 或可见索引已经进入 model_input_accepted /
  provider_committed 主模型输入。
  只有这个字段为 true，read_tool_result_artifact 才能读取。
```

必须满足以下边界：

- 只能读取当前 run directory 中被 `ToolResultArtifactIndex` 正向登记的工具结果 artifact。
- 只能读取 `publishable_after_visibility_scan = true` 且 `recovery_unlocked_after_provider_commit = true` 的条目。`model_visible_recoverable = true` 可以作为二者同时满足后的派生字段，不能在 prepared candidate 阶段提前置为 true。
- 不能读取 artifact manifest 中任意 artifact，也不能接受 raw `ArtifactRef`、绝对路径、相对路径或 `../`。
- `ArtifactRef` 的 contamination scan 如果是 `not_scanned`，不能自动视为可恢复。必须由 `ToolResultArtifactIndex` 明确记录该工具结果 artifact 的可见性、污染扫描状态和恢复权限。
- 只能读取已经进入过 model_input_accepted / provider-committed 模型可见上下文，或已经被 provider-committed 模型可见 preview 引用的 artifact。
- 不能读取 hidden test patch、gold patch、final verifier 原始输出、reward、accepted outcome、evaluator-only selector 或任何 evaluator-only artifact。
- 不能读取 provider raw request、provider raw response、secret、redacted-only artifact 或普通审计 artifact。
- 每次读取都必须分页，并记录 `artifact_id`、`offset`、`limit`、返回内容 sha256 和 context revision。
- 如果 artifact 被标记为 redacted、secret 或 evaluator-only，只能返回拒绝信息，不能返回内容。

推荐的模型可见 replacement preview 在可恢复时采用如下形态：

```text
[tool result persisted]
tool_result_id: ...
tool_name: ...
artifact_id: ...
original_size_chars: ...
sha256: ...
reason: single_tool_result_too_large | per_turn_tool_result_budget_exceeded
preview:
...
recovery_call: read_tool_result_artifact(artifact_id="...", offset=0, limit=8000)
```

如果 artifact 不可恢复，preview 不能包含真实 `artifact_id`、内容 sha256 或 `read_tool_result_artifact` 调用，只能包含不可恢复原因。

这样模型恢复的是不可变旧输出，而不是重新执行工具后得到的当前状态输出。

## 6. 建议配置字段

建议后续实现时新增或替换为如下配置。字段名可以在实现阶段微调，但语义应保持稳定。

```yaml
context_management:
  context_policy_snapshot_version: "repo_harness_context_policy_snapshot_v1"
  tool_result_compact_policy: "claude_code_fresh_only_v1"
  freeze_tool_result_budget_decisions: true
  freeze_tool_result_decisions_at: "provider_committed"
  max_single_tool_result_chars: 50000
  max_tool_results_per_turn_chars: 200000
  tool_result_recovery_tool: "read_tool_result_artifact"
  legacy_history_tool_result_replacement: false
```

其中：

- `max_single_tool_result_chars` 对应单个工具结果过大时立即落盘。
- `max_tool_results_per_turn_chars` 对应本轮新增工具结果聚合过大时落盘。
- `freeze_tool_result_budget_decisions` 表示工具结果可见形态需要冻结。
- `freeze_tool_result_decisions_at` 必须是 `provider_committed`，表示只有真实主模型调用绑定 provider request 后，才把 candidate decision 提交为模型已看过的事实。
- `legacy_history_tool_result_replacement` 默认为 `false`，表示不再由工具结果 compact 层做历史老化替换。
- `context_policy_snapshot_version` 表示本次 run 必须生成完整上下文策略快照。该快照应进入 run config facts、模型调用事件、训练导出 compare scope 和 preference pair 可比较性检查。

## 7. 建议状态结构

建议替换或扩展当前 `ContentReplacementState`，使它不仅记录 replaced，也记录 seen-but-unreplaced。

```text
ToolResultCompactState:
  schema_version
  policy_version
  provider_committed_tool_result_ids
  pending_candidate_decisions_by_prepared_messages_ref
  materialized_request_decisions_by_provider_request_projection_hash
  replacements_by_tool_result_id
  frozen_unreplaced_tool_result_ids
  records
  state_hash
  last_context_revision

ToolResultCompactRecord:
  tool_result_id
  tool_call_id
  tool_name
  candidate_prepared_messages_ref
  candidate_model_input_hash
  candidate_context_revision
  provider_request_materialized_ref
  provider_request_materialized_projection_hash
  provider_committed_prepared_messages_ref
  provider_request_projection_hash
  provider_committed_model_call_id
  provider_committed_context_revision
  decision: persisted_preview | full_visible
  decision_reason
  source_artifact_ref
  replacement_artifact_ref
  replacement_text_hash
  original_content_sha256
  model_visible_preview_sha256
```

实现上的关键不变量：

- `replacements_by_tool_result_id` 中的 replacement preview 后续必须字节级复用。
- `frozen_unreplaced_tool_result_ids` 中的工具结果不能再被工具结果预算层替换。
- 只有 provider-committed 的主模型输入才能推进 `provider_committed_tool_result_ids`、`replacements_by_tool_result_id` 和 `frozen_unreplaced_tool_result_ids`。
- 如果某个工具结果只进入过 prepared candidate，但该 candidate 后来被 context warning、AutoCompact、本地 hard preflight stop 或 provider context_limit 替代，则不能把它记录为模型已看过。
- 如果 persistence（落盘）失败，且原始结果已经进入 provider-committed 主模型输入，应把该工具结果记录为 `full_visible`，后续工具结果预算层不能再改写。
- 如果 artifact visibility 不允许模型读取，replacement preview 不能包含恢复读取调用，只能包含 redacted 状态和拒绝原因。

## 8. MicroCompact 借鉴决策

Claude Code 的 time-based MicroCompact 有三条路径相关能力：

- time-based MicroCompact：白名单工具、时间阈值、保留最近若干工具结果、更旧工具结果替换为 `[Old tool result content cleared]`。
- cached MicroCompact：依赖 provider cache edit 这类 Anthropic 内部能力。
- API context management：依赖 Anthropic provider 侧上下文管理能力。

RepoHarness 只借鉴第一条路径中的通用思想，不借鉴 cached MicroCompact 和 API context management。原因是后两者依赖 Anthropic 私有能力，不适合作为 RepoHarness 的通用、可复现、可导出的 Harness 能力。

Claude Code 的 time-based MicroCompact 默认 `keepRecent = 5`，并且它的触发前提是“距离上一条主线程 assistant message 的时间超过阈值，服务端 prompt cache 大概率已经过期”。RepoHarness 当前不围绕 Anthropic prompt cache 过期时间设计，因此不采用时间阈值作为主触发条件。

RepoHarness 的 MicroCompact 应改为 count / pressure based：

```yaml
microcompact:
  enabled: true
  policy: "count_based_tool_result_clear_v1"
  trigger_compactable_tool_result_count: 30
  trigger_compactable_tool_result_chars: 60000
  keep_recent_compactable_tool_results: 15
  cleared_message: "[Old tool result content cleared]"
```

### 8.1 白名单

初始 compactable tool result 白名单建议为：

```text
read_file
grep
list_files
glob_files
symbol_search
git_diff
edit_file
create_file
bash
run_tests
```

初始不清理以下类型：

```text
update_working_state
context_warning
semantic_summary
session_memory
```

其中 `update_working_state` 是模型主动维护的任务工作状态，后续如果引入 Session Memory，它也应归入工作记忆层，而不是当作普通工具噪声清掉。

MicroCompact 只能改变 provider-prepared projection，不能销毁原始工具结果事实。原始工具结果仍必须保留在 raw trajectory、工具结果 artifact 或审计 artifact 中；训练导出则必须使用对应主模型调用当轮真实看到的 compacted view。换句话说，MicroCompact 清理的是“后续模型输入视图”，不是“历史事实本身”。

这也意味着，L0 的 frozen full visible 规则不阻止 L1 MicroCompact 在后续 provider-prepared projection 中生成占位符。L0 的不变量是“工具结果预算层不能改写一个 provider-committed 工具结果的 persisted preview / full visible 命运”；L1 MicroCompact 的不变量是“在新的后续模型输入视图中清理旧工具结果，同时保留原始事实和每次主模型调用实际看到的 `ModelInputSnapshot`”。因此，同一个工具结果可以在较早的训练样本中保持完整内容，在较晚的训练样本中显示为 `[Old tool result content cleared]`，只要两次样本都绑定各自真实的模型输入快照。

### 8.2 为什么 keepRecent 选择 15

本轮用最新 targeted smoke 产物做了轻量模拟，统计 compactable tool result 的模型可见 `content_preview` 长度，并把更旧结果替换成 `[Old tool result content cleared]`。

最新 targeted smoke 路径：

`runs/pre-verl-agentloop-targeted-smoke-deepseek-flash-tool-capability-guidance-20260508T133407Z/`

关键结果如下：

| 任务 | compactable tool result 数量 | 原可见内容字符数 | keepRecent = 15 后约剩余字符数 | 约节省比例 |
| --- | ---: | ---: | ---: | ---: |
| `001_sqlfluff_1625` | 22 | 36,194 | 17,357 | 52.0% |
| `014_astroid_1333` | 58 | 204,620 | 37,600 | 81.6% |
| `015_astroid_1196` | 29 | 26,073 | 11,371 | 56.4% |
| `017_astroid_1268` | 11 | 46,651 | 46,651 | 0.0% |
| `020_pydicom_1413` | 53 | 153,315 | 25,772 | 83.2% |

这个模拟说明：

- `keepRecent = 15` 对 `014_astroid_1333` 和 `020_pydicom_1413` 这种长任务有明显压缩效果，能节省约 80% 以上旧工具结果可见内容。
- `017_astroid_1268` 只有 11 个 compactable tool result，`keepRecent = 15` 不会清理任何内容，避免误伤短任务。
- `keepRecent = 10` 或 `12` 压缩更强，但对 SWE Lite 修复任务偏激进，可能过早清理最近一段仍有用的源代码读取、编辑结果和 `git_diff`。
- `keepRecent = 20` 更保守，但在长任务中保留内容偏多，压缩收益下降。

因此，`keepRecent = 15` 是一个更平衡的初始值。它不会像 Claude Code 默认 `5` 那样激进，也不会像 `20` 那样保留过多旧工具结果。

### 8.3 为什么触发条件需要同时看数量和字符数

MicroCompact 不应只按数量触发。如果只要工具结果数量超过 15 或 20 就清理，可能会误伤很多短小搜索、短小编辑确认或短小 diff。

初始触发条件建议同时满足：

```text
compactable tool result 数量 >= 30
compactable tool result 可见内容总量 >= 60,000 字符
```

这组阈值在当前 targeted smoke 上的行为比较合理：

- `014_astroid_1333` 会触发，应该触发。
- `020_pydicom_1413` 会触发，应该触发。
- `017_astroid_1268` 不会触发，因为数量只有 11。
- `015_astroid_1196` 不会触发，因为总字符数只有约 26,073。
- `001_sqlfluff_1625` 最新 smoke 不会触发，因为总字符数只有约 36,194。

### 8.4 MicroCompact 不变量

MicroCompact 只能改旧 tool result 的 `content`，不能删除消息，也不能破坏工具调用和工具结果配对。

必须保留：

```text
tool_result_id
tool_call_id
role = tool
artifact_refs
turn
tool_name
status
typed metadata
```

必须记录事件，例如：

```text
event_type: microcompact_applied
policy_version: count_based_tool_result_clear_v1
cleared_message: "[Old tool result content cleared]"
cleared_tool_result_ids: [...]
kept_tool_result_ids: [...]
chars_before
chars_after
estimated_tokens_saved
```

MicroCompact 必须幂等：

- 如果某条旧工具结果的 `content` 已经是 `[Old tool result content cleared]`，再次执行不能重复计算节省，也不能再次改变内容。
- 同一个 context revision 中不能重复触发并生成多份冲突事件。
- 训练导出必须能通过 `prepared_messages_ref` 复原每一轮模型实际看到的是原始内容还是 cleared placeholder。

## 9. AutoCompact 设计决策

AutoCompact 是 L0 工具结果 compact 和 L1 MicroCompact 之后的语义压缩层。它解决的问题不是“某个工具结果太长”，而是“旧对话、旧工具观察、旧尝试路径和当前补丁状态已经太多，模型需要一份可继续工作的结构化任务记忆”。

Claude Code 的 AutoCompact 有两条值得区分的路径：

- 产品内部优先尝试 Session Memory compaction。它依赖后台 post-sampling hook、forked agent、独立 session memory 文件和 prompt cache sharing。
- 当 Session Memory 不可用时，回退到 `compactConversation`。这条路径会发起一次独立 compact 模型请求，生成摘要，再用 compact boundary、summary、recent messages 和 attachments 重建后续上下文。

RepoHarness 当前没有 subagent，也不需要为了 AutoCompact 先实现 streaming 主循环。因此 RepoHarness 初始版本只借鉴第二条路径的核心不变量：

```text
一次独立 compact LLM 请求
  -> 生成结构化摘要
  -> 插入 compact boundary
  -> 保留最近原文尾部
  -> 注入确定性恢复材料
  -> 重新 prepare_messages 并校验工具调用 / 工具结果配对
  -> 再继续主模型调用
```

### 9.1 AutoCompact 与当前 `ContextManager` 的落点

当前 `ContextManager.prepare_messages()` 已经负责每轮主模型调用前的上下文准备、工具结果替换、`prepared_messages` artifact、`context_revision`、`model_input_hash` 和工具调用 / 工具结果配对校验。AutoCompact 应接在这个流程旁边，而不是完全塞进 `ContextManager` 内部。

推荐执行顺序是：

```text
1. AgentLoop 收集当前原始 messages。
2. ContextManager 执行 L0 工具结果 compact 和 L1 MicroCompact，生成 prepared_messages 和 token estimate。
3. AgentLoop 根据真实 provider request projection 的 token estimate 判断是否达到 AutoCompact 触发线。
4. 如果未触发，继续正常主模型调用。
5. 如果触发，AgentLoop 调用 AutoCompactRunner。
6. AutoCompactRunner 用现有 ModelClient 发起一次 compact-only 模型请求。
7. compact 请求成功后，AutoCompactRunner 重建后续 canonical run messages：
   compact boundary + compact summary + preserved recent tail + rehydration messages。
8. AgentLoop 再次调用 ContextManager.prepare_messages。
9. 再次校验工具调用 / 工具结果配对和 token estimate。
10. 如果仍在硬限制以内，继续主模型调用。
11. 如果仍超过硬限制，按 `strict_local_preflight` 停止为 context_limit_preflight_after_autocompact；只有在策略显式允许时才进入非 provider-failure 的 hard preflight recovery。
```

这样设计的原因是：`ContextManager` 本身不持有 `ModelClient`，而 AutoCompact 需要一次额外模型调用。把触发判断和消息重建放在 AgentLoop / AutoCompactRunner 侧，更符合当前 RepoHarness 的模块边界。

这里的“重建”不是从未过滤的 raw messages 中回填信息。AutoCompact 的输入和重建来源必须限定为：

- 已经进入模型可见上下文的 `prepared_messages`。
- `prepared_messages` 中已经模型可见的 artifact 引用。
- 压缩前已经由模型可见 read-state、diff-state 或 test-state 记录过的公开工作现场事实，例如当前候选补丁 diff、公开文件内容片段、公开测试输出摘要。
- 当前 run 中已经通过 visibility policy 标记为 model-visible 的上下文管理 artifact。

不能从 evaluator-only metadata、hidden verifier 原始输出、reward、accepted outcome、gold patch、hidden test patch 或未经过可见性过滤的 raw trajectory 数据中回填。

如果确实需要读取实时工作区文件作为 rehydration 来源，不能静默读取后塞进摘要。必须生成单独的 `rehydration_source_read` artifact，记录路径、内容 hash、读取时机、可见性检查结果和污染扫描结果；该内容进入后续主模型输入时，也必须作为模型可见事实和训练样本输入的一部分被审计。

### 9.2 有效上下文预算不应固定为 `max_context_tokens = 120000`

当前 `max_context_tokens = 120000` 是早期评测时的人工预算，不应继续被当作所有模型的真实上下文长度。DeepSeek V4、GPT-5.5 API 等新模型可能有更大的上下文窗口。AutoCompact 的默认阈值应基于当前 provider / model 的有效上下文预算，而不是固定使用 Harness 旧默认值。

建议把预算拆成三个概念：

```text
model_context_window_tokens:
  当前模型或 provider 实际声明的上下文窗口。
  例如 400,000 或 1,000,000。

harness_context_cap_tokens:
  Harness 为公平评测、成本控制、压力测试或消融实验显式设置的人为上限。
  默认可以为 null，表示不主动压低模型窗口。

effective_context_budget_tokens:
  本次 run 实际用于 AutoCompact 判断的有效预算。
```

推荐计算方式：

```text
effective_context_budget_tokens =
  min(model_context_window_tokens, harness_context_cap_tokens 如果显式设置)
  - main_output_reserve_tokens
  - estimator_safety_margin_tokens
```

其中：

- `main_output_reserve_tokens` 是留给主模型回答、工具调用 JSON、补丁说明和最终回答的空间。
- `estimator_safety_margin_tokens` 是留给 token 估算误差、工具 schema、provider 包装开销和不同 provider 计数差异的空间。
- 如果 `harness_context_cap_tokens` 显式设置为 `120000`，则该 run 是固定预算实验；如果为 `null`，则默认使用模型实际窗口。

估算对象不能只包含 messages 文本。必须覆盖真实 provider request projection，至少拆分记录：

```text
provider_request_projection_hash
message_token_estimate
tool_schema_token_estimate
tool_choice_token_estimate
provider_wrapper_token_estimate
main_output_reserve_tokens
estimator_safety_margin_tokens
effective_context_budget_tokens
```

其中 `provider_request_projection_hash` 应对应 provider 适配器实际发送或准备发送的请求投影，包括 messages、工具 schema、`tool_choice`、provider 包装字段和 generation config 中会进入请求体的部分。否则 AutoCompact 触发线和 hard stop 仍可能低估真实请求长度。

这个 projection 必须由同一个纯构造器生成，例如 `build_provider_request_projection(...)`。AutoCompact 触发、context warning、hard preflight、raw provider request 写入、provider body equivalence inspect 和 hash 复算都必须使用这个构造器的结果。不要维护一套“估算用请求体”和另一套“真实发送请求体”，否则预算判断和训练样本输入会漂移。

### 9.3 简化后的阈值配置

RepoHarness 不是面向终端用户的交互式产品，因此不需要完整复制 Claude Code 的 warning、critical、blocking 多档用户体验。初始设计只保留一个主动触发线和一个硬保护线。

建议配置如下：

```yaml
context_management:
  context_budget_policy: "model_window_with_optional_cap"
  model_context_window_tokens: "auto"
  harness_context_cap_tokens: null

  main_output_reserve_tokens: 32000
  estimator_safety_margin_ratio: 0.03
  estimator_safety_margin_min_tokens: 20000

  auto_compact_trigger_ratio: 0.85
  hard_context_limit_ratio: 0.97

  post_compact_target_ratio: 0.60
  post_compact_target_max_tokens: 300000

  auto_compact_max_consecutive_failures: 3
  auto_compact_summary_max_output_tokens: 16000
  preserve_recent_turns_after_compact: 6
  preserve_recent_tail_token_budget: 80000
```

这些字段的含义如下：

- `context_budget_policy`：说明本次 run 的预算来源。默认应为“模型窗口加可选 Harness 上限”，而不是固定 `120000`。
- `model_context_window_tokens`：可以由 provider / model registry 自动解析。解析不到时必须显式降级为保守值，并在 run config facts 中记录来源。
- `harness_context_cap_tokens`：只有在需要公平比较、成本控制或压力测试时才设置。设置后，AutoCompact 以这个 cap 为准。
- `main_output_reserve_tokens`：为主模型下一次输出保留空间。它不是 compact summary 的输出预算。
- `estimator_safety_margin_ratio` 和 `estimator_safety_margin_min_tokens`：为 provider token 估算误差和消息包装开销保留安全余量。
- `auto_compact_trigger_ratio`：唯一的主动 AutoCompact 触发线。例如有效预算为 1,000,000 token 时，0.85 表示约 850,000 token 触发。
- `hard_context_limit_ratio`：硬保护线。达到这条线时不应继续普通主模型调用，必须先 compact；compact 后仍超过这条线，默认应按 `strict_local_preflight` 停止为 `context_limit_preflight_after_autocompact`，只有在策略显式允许时才进入非 provider-failure 的 hard preflight recovery。
- `post_compact_target_ratio`：压缩质量目标，不是循环触发条件。它告诉 AutoCompact 这一次压缩应尽量压到多小。
- `post_compact_target_max_tokens`：压缩后目标的绝对上限。它避免 1,000,000 token 模型下 `0.60` 对应的 600,000 token 仍然过大。
- `auto_compact_max_consecutive_failures`：连续压缩失败熔断次数，避免每一轮都重复烧失败的 compact 请求。
- `auto_compact_summary_max_output_tokens`：compact LLM 生成摘要的最大输出长度。它不是主模型回答长度。
- `preserve_recent_turns_after_compact`：压缩后完整保留最近多少轮原文交互。
- `preserve_recent_tail_token_budget`：最近原文尾部的 token 预算，避免最近 6 轮中存在超大工具结果时直接撑爆上下文。

### 9.4 `post_compact_target` 不是重复压缩条件

`post_compact_target_ratio` 和 `post_compact_target_max_tokens` 的作用是选择压缩边界、摘要详细度和 rehydration 预算，不是要求压缩后如果仍高于目标就立刻再次压缩。

推荐计算：

```text
post_compact_target_tokens =
  min(
    effective_context_budget_tokens * post_compact_target_ratio,
    post_compact_target_max_tokens
  )
```

举例一：小预算固定 cap 实验。

```text
model_context_window_tokens = 1,000,000
harness_context_cap_tokens = 120,000
main_output_reserve_tokens = 32,000
estimator_safety_margin_tokens = max(120,000 * 0.03, 20,000) = 20,000

effective_context_budget_tokens =
  120,000 - 32,000 - 20,000 = 68,000

auto_compact_trigger_tokens =
  68,000 * 0.85 = 57,800

hard_context_limit_tokens =
  68,000 * 0.97 = 65,960

post_compact_target_tokens =
  min(68,000 * 0.60, 300,000) = 40,800
```

举例二：不设置 Harness cap，使用 1,000,000 token 模型窗口。

```text
model_context_window_tokens = 1,000,000
harness_context_cap_tokens = null
main_output_reserve_tokens = 32,000
estimator_safety_margin_tokens = max(1,000,000 * 0.03, 20,000) = 30,000

effective_context_budget_tokens =
  1,000,000 - 32,000 - 30,000 = 938,000

auto_compact_trigger_tokens =
  938,000 * 0.85 = 797,300

hard_context_limit_tokens =
  938,000 * 0.97 = 909,860

post_compact_target_tokens =
  min(938,000 * 0.60, 300,000) = 300,000
```

压缩后处理规则：

```text
如果 tokens_after <= post_compact_target_tokens：
  记录 auto_compact_succeeded，继续主模型调用。

如果 tokens_after > post_compact_target_tokens
并且 tokens_after <= effective_context_budget_tokens * hard_context_limit_ratio：
  记录 post_compact_above_target = true，继续主模型调用。
  不要立刻重复 AutoCompact。

如果 tokens_after > effective_context_budget_tokens * hard_context_limit_ratio：
  不继续普通主模型调用。
  默认按 strict_local_preflight 停止为 context_limit_preflight_after_autocompact；
  只有在策略显式允许时进入非 provider-failure 的 hard preflight recovery。
```

不建议在同一轮中自动连续 AutoCompact。原因是第二次压缩通常是在总结第一次 summary 和少量尾部消息，容易丢失细节，而且成本更高。`post_compact_target` 是质量目标；`hard_context_limit_ratio` 才是能不能继续的硬门槛。

这条规则只限制“同一轮中不要因为高于 target 就立刻连续压缩”。后续轮次如果上下文再次达到 `auto_compact_trigger_ratio`，仍然可以触发新的 AutoCompact，但必须生成新的 `compact_id`、新的事件和新的 source prepared messages 绑定。

### 9.4.1 preserved recent tail 预算也必须动态收缩

`preserve_recent_tail_token_budget` 不能作为固定硬值直接使用。比如小预算固定 cap 实验中，扣除输出预留和估算余量后，`effective_context_budget_tokens` 可能只有 68,000；如果最近尾部固定允许 80,000 token，就已经超过有效预算。

推荐计算：

```text
effective_preserve_recent_tail_token_budget =
  min(
    preserve_recent_tail_token_budget,
    post_compact_target_tokens * 0.50,
    effective_context_budget_tokens * 0.35
  )
```

含义是：最近原文尾部要足够保真，但不能挤占 compact summary 和 rehydration messages 的空间。对大上下文模型，80,000 token 可以作为上限；对小预算实验，它会自动收缩。

### 9.5 compact-only 模型请求

RepoHarness 初始 AutoCompact 不依赖 subagent，也不依赖 streaming。它应通过现有 `ModelClient.generate()` 发起一个 compact-only 请求。

compact-only 请求建议满足：

```text
provider_message_format: repo_harness_compact_summary_request_v0
scaffold_phase: compact
allowed_tools: []
tool_choice: none
generation_config.max_output_tokens: auto_compact_summary_max_output_tokens
trainable: false
visibility: model_visible_context_management
```

compact-only 请求必须满足以下硬性不变量：

- 使用独立 `model_call_id`，例如 `run_id_compact_0001`，不能复用主任务模型调用编号。
- `scaffold_phase` 必须是 `compact`。
- `allowed_tool_definitions` 必须是空列表。
- `tool_choice` 必须是 `none`。
- compact response 不能作为普通 assistant action 进入主任务 transcript。
- compact response 不能计入主任务 tool-call budget。
- compact response 不能作为 trainable trajectory sample，只能作为 context-management artifact。

必须约束 compact LLM：

- 只能输出文本摘要，不能调用工具。
- 只能使用当前模型已经可见的上下文、公开任务说明、公开工具结果 preview、模型可见 artifact 引用、当前工作区公开状态和公开 budget 状态。
- 不能读取或推断 hidden test、gold patch、final verifier 原始输出、reward、accepted outcome、evaluator-only selector 或任何 evaluator-only artifact。
- 不允许把压缩请求的输出当成主任务动作；它只是上下文管理产物。
- compact 请求的 raw provider request / response、summary artifact、source message hashes 和审计事件都必须保留。

compact-only 请求自身也可能超过上下文限制，因此 AutoCompactRunner 在调用 compact LLM 之前必须先构造并估算 `compact_source_projection`。如果 `compact_source_projection` 超过 compact 模型的硬限制：

```text
proactive AutoCompact:
  记录 auto_compact_source_too_large。
  不生成伪摘要。
  如果当前主模型请求也超过 hard preflight，则停止为 context_limit_preflight_after_autocompact。

provider verified Reactive Compact:
  可以进入 truncate_head_for_ptl_retry 类兜底。
  该兜底必须按 API round 分组、保持 tool call / tool result 配对、
  插入 synthetic user marker，并记录被丢弃 round 的审计 artifact。
```

也就是说，AutoCompact 不能在 compact-only 输入本身过长时“假装总结了所有历史”。如果没有把某段历史送入 compact LLM，就不能让摘要声称掌握了那段历史，只能通过 omission marker 和审计事件说明被省略。

如果 compact-only 请求失败、返回空摘要、返回 provider 错误或输出不满足 schema，本次 AutoCompact 视为失败，并增加 `consecutive_failures`。连续失败达到 `auto_compact_max_consecutive_failures` 后，本次 run 不再主动 AutoCompact；只有当后续真实 provider 主模型调用返回 `context_limit` 时，才允许进入 Reactive Compact 兜底。

### 9.6 压缩后消息结构

AutoCompact 成功后，下一次主模型看到的消息不应是“随意删掉旧消息后附一段摘要”，而应按固定结构重建：

```text
1. 基础上下文
   system prompt、任务说明、工具协议、可见性规则、scaffold 阶段提示。

2. compact_boundary message
   记录这里发生过一次上下文压缩。
   它应包含 compact_id、trigger_reason、context_revision_before、
   summarized_message_count、preserved_message_count、summary artifact 引用等元信息。

3. compact_summary message
   compact LLM 生成的结构化历史摘要。
   它覆盖被摘要的较早消息。

4. preserved recent tail messages
   最近若干轮原始消息，完整保留。
   不能切断 assistant tool call 和对应 tool result。

5. post-compact rehydration messages
   确定性恢复的当前工作现场材料。
   例如当前 diff 摘要、修改文件列表、最近测试结果、最近关键文件片段和工具结果恢复索引。
```

这个结构借鉴 Claude Code 的 `buildPostCompactMessages` 思路：`boundaryMarker -> summaryMessages -> messagesToKeep -> attachments -> hookResults`。区别是 Claude Code 的 attachments 和 hook results 来自产品运行时，例如最近读取文件、plan、skills、deferred tools、MCP instructions 和 session start hooks；RepoHarness 更适合把这些恢复材料显式写成 run artifact 和模型可见 message，保证训练导出时可以复原模型到底看到了什么。

### 9.7 摘要结构

摘要结构指 compact LLM 必须输出的内容结构。它不是 `ContextManager` 自己写的固定模板，而是 compact-only 模型请求的输出。为了训练轨迹可审计，RepoHarness 不应让 compact LLM 随意写自然语言总结，而应要求它输出严格结构化 Markdown 或 JSON。

建议初始字段如下：

```text
task_intent:
  用户原始任务、当前目标、显式约束和最近用户指令。

repository_facts:
  已确认的仓库事实、关键文件、关键函数、重要配置和已经排除的方向。

actions_taken:
  已经读取、搜索、编辑、运行测试、检查 diff 的动作摘要。

patch_state:
  当前修改过哪些文件，修改意图是什么，哪些修改已经验证，哪些修改仍有风险。

test_state:
  最近公开测试、命令、失败摘要、通过摘要和仍需运行的验证。

tool_recovery_index:
  被 L0 落盘或 L1 清理的关键工具结果如何恢复。
  记录 tool_result_id、tool_name、artifact_id、sha256 和 read_tool_result_artifact 调用方式。

open_questions:
  当前仍不确定的问题、可能的下一步调查方向。

next_step:
  与最近任务直接一致的下一步最小行动。

visibility_policy:
  明确说明摘要只来自模型可见上下文，不包含隐藏评测、奖励、gold patch 或最终验收事实。
```

这样设计的原因是 SWE 类型任务最容易丢失的不是闲聊，而是“看过哪些文件、为什么做这个判断、改了什么、测试失败在哪里、下一步本来要做什么”。Claude Code 的 compact prompt 也强调用户意图、技术概念、文件和代码、错误修复、待办、当前工作和下一步；RepoHarness 的区别是需要更强的结构化字段、source hashes 和 visibility policy，服务于训练导出、审计和失败归因。

### 9.8 上下文记忆恢复和压缩后消息结构的关系

上下文记忆恢复不是另一个独立压缩机制，而是“压缩后消息结构”中第 5 部分的生成过程。

可以这样理解：

```text
压缩后消息结构：
  规定 AutoCompact 成功后，下一轮主模型输入由哪些消息组成、顺序是什么。

上下文记忆恢复：
  负责为这个结构准备“当前工作现场”材料。
```

举例：

```text
compact_summary 可能写：
  已定位到 src/parser.py 的 parse_error 分支，
  已修改错误格式化逻辑，
  最近 tests/test_parser.py 仍有一个断言失败。

rehydration messages 进一步提供：
  当前 git diff 摘要；
  当前被修改文件列表；
  最近一次公开测试失败摘要；
  src/parser.py 相关片段；
  被替换工具结果的 artifact_id 和恢复方式。
```

也就是说：

```text
compact_summary 负责记住“较早历史发生过什么”。
preserved recent tail 负责保留“刚刚发生的精确交互”。
rehydration messages 负责恢复“现在工作区是什么状态，下一步需要哪些精确信息”。
```

RepoHarness 初始 rehydration 可以先做确定性恢复，不需要 subagent：

- 压缩前已经由模型可见 diff-state 记录过的 `git diff --stat` 和修改文件列表。
- 压缩前已经由模型可见 `git_diff` 工具结果记录过的摘要。
- 压缩前已经由模型可见 `run_tests` / `bash` 工具结果记录过的公开测试摘要。
- 压缩前已经由模型可见 `read_file` 或等价 read-state 记录过的相关文件片段。
- 当前 `update_working_state` 或等价工作状态消息。
- L0 replacement 和 L1 MicroCompact 涉及的关键 artifact recovery index。

这些恢复材料必须全部来自模型可见信息、模型可恢复 artifact，或者压缩前已经记录为模型可见的公开工作现场材料。不能借 rehydration 注入 evaluator-only 信息，也不能静默读取模型之前没有看过的新文件内容。

如果实现确实需要读取实时工作区文件、clean source checkout 或实时 diff 作为 rehydration 来源，必须生成独立的 `rehydration_source_read` artifact，并记录路径、读取命令、内容 hash、可见性检查、污染扫描结果和引入原因。clean source checkout 只能用于复核已经模型可见的公开片段，不能静默补入模型之前没有看过的新文件内容。该 artifact 进入后续主模型输入时，也必须进入训练样本的 `ModelInputSnapshot`，不能作为隐形上下文存在。

建议给 rehydration source 增加正向 allowlist：

```text
allowed_rehydration_sources:
  - prepared_messages 中的模型可见消息
  - prepared_messages 引用的模型可见 artifact
  - ToolResultArtifactIndex 中 publishable_after_visibility_scan=true 且 recovery_unlocked_after_provider_commit=true 的 artifact
  - 压缩前模型可见 read-state 中的公开文件片段
  - 压缩前模型可见 diff-state 中的当前候选补丁 diff 和 diff --stat
  - 公开工具结果 preview
  - 已经由 visibility policy 标记为 model-visible 的 verifier_result_preview
  - 当前 run 的 model-visible context management artifact
  - 显式记录并通过可见性检查的 rehydration_source_read artifact
```

明确禁止：

```text
forbidden_rehydration_sources:
  - hidden_feedback_ran 原始内容
  - final verifier 原始输出
  - reward / accepted outcome
  - gold patch
  - hidden test patch
  - evaluator-only selector
  - evaluator-only artifact
  - 未经过 visibility policy 过滤的 raw trajectory metadata
```

`tool_recovery_index` 只能索引模型可见或模型可恢复的 artifact。对于 L1 MicroCompact 清理掉的旧工具结果，如果原始内容没有安全 artifact，摘要不能承诺可以用 `read_tool_result_artifact` 恢复，只能记录：

```text
recovery_status: cleared_without_recoverable_artifact
```

更稳妥的实现策略是：MicroCompact 在清理旧工具结果之前，先确保该工具结果原文已经进入安全、model-visible 的 tool result artifact；如果不能安全落盘，就只能清理为不可恢复原文，而不能生成恢复调用。

### 9.9 AutoCompact 状态与事件

建议新增 `AutoCompactState`：

```text
AutoCompactState:
  schema_version
  policy_version
  compact_count
  last_compact_id
  last_compact_context_revision_before
  last_compact_context_revision_after
  turns_since_last_compact
  consecutive_failures
  disabled_reason
```

每次尝试 AutoCompact 都应记录事件：

```text
event_type: auto_compact_requested | auto_compact_succeeded | auto_compact_failed
policy_version
compact_id
trigger_reason
context_budget_policy
model_context_window_tokens
harness_context_cap_tokens
effective_context_budget_tokens
auto_compact_trigger_ratio
hard_context_limit_ratio
post_compact_target_tokens
tokens_before
tokens_after
post_compact_above_target
summary_artifact_ref
compact_model_call_ref
source_message_hashes
source_prepared_messages_ref
compact_source_messages_ref
summarized_message_ids
preserved_message_ids
rehydration_artifact_refs
tool_pairing_validation_before
tool_pairing_validation_after
hidden_metadata_excluded: true
consecutive_failures
```

训练导出必须能通过这些事件回答：

- 哪一轮触发了 AutoCompact。
- 压缩前模型可见内容是什么。
- compact LLM 看到的源内容是什么。
- compact summary 是什么。
- 压缩后主模型实际看到了什么。
- 哪些旧工具结果只能通过 artifact recovery 恢复。
- 是否存在压缩后仍高于目标但低于硬限制的情况。

### 9.10 Reactive Compact 兜底

AutoCompact 是主动压缩，Reactive Compact 是 provider 已经返回 `context_limit`、`prompt too long` 或类似错误后的兜底。复核后，Reactive Compact 不能只写成“emergency AutoCompact”。原因是 provider 已经拒绝的请求可能大到连 compact-only 请求本身也无法安全构造；如果仍然只调用 compact LLM，可能得到一个没有完整输入依据的摘要。

核心决策是：

```text
Reactive Compact = provider verified recovery pipeline。

优先路径：
  provider context_limit 后的一次 emergency AutoCompact + 一次主模型重试。

兜底路径：
  如果 emergency AutoCompact 输入本身无法放入 compact-only provider request，
  或 provider 错误显示 token gap 需要立即裁剪请求头部，
  则使用 truncate_head_for_ptl_retry 类机制：
    按 API round 分组；
    从最旧 round 开始丢弃；
    保持 tool call 和 tool result 配对；
    保留 system / task / compact summary / 最近完整 rounds；
    插入 synthetic user marker；
    最多重试一次主模型调用。
```

也就是说，Reactive Compact 的优先路径不拥有自己的摘要 prompt、不拥有自己的 summary schema、不拥有自己的 rehydration 规则，也不拥有自己的消息重建格式。它必须复用 AutoCompact 的以下能力：

- compact-only 模型请求。
- compact summary 结构。
- compact boundary message。
- preserved recent tail 选择规则。
- rehydration allowlist 和 forbidden sources。
- source prepared messages 绑定。
- 工具调用 / 工具结果配对校验。
- context-management artifact 和事件审计。

但 Reactive Compact 还必须拥有一个确定性的 PTL fallback（prompt too long fallback）。该 fallback 不产生语义摘要，不假装理解被丢弃历史，只负责把 provider 已拒绝的请求裁剪到可以重试的形态，并通过 synthetic marker 明确告诉模型“较早 round 已因 provider context limit 被省略，请依赖剩余上下文和已有 compact summary 继续”。

#### 9.10.1 触发条件

Reactive Compact 只在 provider 已经拒绝当前主模型请求时触发。初始触发条件建议为：

```text
response.terminal_error_type == "context_limit"
或者 response.model_error_type == "context_limit"
或者 provider 错误分类为：
  - context_length
  - maximum context
  - context limit
  - too many tokens
  - prompt too long
  - HTTP 413
```

provider adapter 必须把归一化后的错误类型写入 `model_call_completed` 事件，例如 `terminal_error_type` 和 `model_error_type`。AgentLoop 判断 Reactive Compact 时应使用归一化字段，而不是只依赖 provider 原始错误字符串。

如果本地 preflight 阶段已经发现 `prepared.token_estimate > hard_context_limit_tokens`，那仍属于主动 AutoCompact 或 hard preflight stop 的范围，不应伪造成 Reactive Compact。Reactive Compact 的语义必须保持清楚：它是“真实 provider 返回上下文限制错误之后”的恢复路径。

#### 9.10.2 执行流程

推荐流程如下：

```text
1. AgentLoop 正常准备 messages，并调用主模型。
2. provider 返回 context_limit / prompt too long。
3. AgentLoop 记录原始失败的 model_call_completed 事件和 provider error artifact。
4. 解析 provider 错误中的 token gap / prompt too long 分类；如果 provider 没有给出精确 gap，也要记录 gap_unknown。
5. 如果本次主模型调用还没有执行过 reactive compact：
   调用 AutoCompactRunner.run(mode="emergency", trigger_reason="provider_context_limit_retry")。
6. AutoCompactRunner 使用触发失败前的 source_prepared_messages_ref / compact_source_messages_ref 作为 compact 输入边界。
7. 如果 compact-only 请求可以构造并通过预算，生成 compact boundary、compact summary、preserved recent tail 和 rehydration messages。
8. 如果 compact-only 请求本身超限，或 emergency compact 失败但策略允许 PTL fallback，则执行 truncate_head_for_ptl_retry。
9. truncate_head_for_ptl_retry 按 API round 分组，从最旧完整 round 开始丢弃，保持 tool call / tool result 配对，插入 synthetic user marker，并记录 omitted_rounds artifact。
10. AgentLoop 重新调用 ContextManager.prepare_messages。
11. 重新校验工具调用 / 工具结果配对。
12. 以新的 prepared_messages 重试同一个主模型调用一次。
13. 如果重试成功，继续正常 loop。
14. 如果重试仍是 context_limit，停止为 context_limit_after_reactive_compact。
15. 如果 emergency compact 和 PTL fallback 都失败，停止为 reactive_compact_failed。
```

原始 provider `context_limit` 失败必须作为审计事件和 artifact 保留，但不能作为普通 assistant message 追加进 retry 的 canonical messages，也不能成为 trainable transcript action。未来实现时需要特别处理当前 AgentLoop 对 model error 的 transcript 写入和 `messages.append(assistant_message)` 行为：Reactive Compact retry 的输入应该来自失败前的 source prepared messages 加上 emergency AutoCompact 产物，而不是包含 provider 错误文本的普通对话历史。

这一流程必须保留两次主模型调用之间的因果链：

```text
original_model_call_id
original_provider_error_ref
reactive_compact_id
reactive_compact_summary_ref
ptl_truncation_ref
synthetic_marker_message_id
retry_model_call_id
```

这样后续失败分析可以区分：

- 主动 AutoCompact 没有触发导致 provider 拒绝。
- 主动 AutoCompact 已触发但 provider 仍拒绝。
- 本地 token 估算低于阈值但 provider 实际拒绝。
- Reactive Compact 成功救回。
- Reactive Compact 后仍然失败。
- Reactive Compact 走了语义 emergency compact 还是确定性 PTL truncation。

#### 9.10.3 一次性限制

Reactive Compact 不能循环执行。

```text
同一次 provider context_limit 错误：
  最多执行一次 emergency AutoCompact；
  最多重试一次主模型调用。
```

如果重试后再次返回 `context_limit`，不能继续 emergency compact 第二次。原因是第二次 emergency compact 很可能是在压缩刚生成的 summary 和很短的尾部上下文，信息损失风险高，且会把失败原因变得不清楚。

推荐停止原因如下：

```text
reactive_compact_failed:
  emergency AutoCompact 请求失败、返回空摘要、schema 校验失败、可见性检查失败，
  且 PTL fallback 不可用或也失败。

context_limit_after_reactive_compact:
  emergency AutoCompact 成功，重试主模型仍返回 context_limit。

context_limit_reactive_compact_disabled:
  provider 返回 context_limit，但策略或熔断状态禁止 reactive compact。
```

PTL fallback 必须满足：

- 只按 API round 删除旧内容，不删除半个 tool call / tool result 配对。
- 不删除 system message、任务原始说明、最新用户指令、已有 compact summary 和最近完整 rounds，除非已经无法构造任何合法请求。
- 插入 synthetic user marker，说明较早 rounds 因 provider context limit 被省略。
- synthetic marker 是模型可见事实，但不是用户真实输入，也不是 assistant action。
- 记录 `ptl_truncation_ref`，包含被省略 round 的 message ids、hash、token 估算、删除原因和保留边界。
- 训练导出必须能复原 retry 主模型实际看到的是“裁剪后的请求 + synthetic marker”，不能把被省略 round 拼回训练样本输入。

#### 9.10.4 与 AutoCompact 状态的关系

Reactive Compact 复用 AutoCompactRunner，但事件和状态必须区分主动压缩和兜底压缩。

建议字段：

```text
auto_compact_mode: proactive | emergency
trigger_reason: proactive_threshold | hard_preflight | provider_context_limit_retry
reactive_attempt_count: 0 | 1
original_model_call_id
original_provider_error_type
original_provider_error_ref
retry_model_call_id
retry_after_reactive_compact: true | false
```

`auto_compact_max_consecutive_failures` 仍然适用于 emergency 模式，但不能因为 proactive AutoCompact 熔断就完全禁止最后一次 Reactive Compact。建议区分：

```text
proactive_auto_compact_consecutive_failures:
  主动 AutoCompact 连续失败计数。

reactive_auto_compact_attempted_for_model_call_id:
  当前主模型调用是否已经使用过 Reactive Compact。
```

也就是说，主动 AutoCompact 可以因为连续失败停止自动尝试，但 provider 真正返回 `context_limit` 时，仍然允许一次 Reactive Compact，除非 compact-only 请求本身已经被全局策略禁用。

#### 9.10.5 预算和训练导出边界

Reactive Compact 产生的 compact-only response 仍然是 context-management artifact，不是主任务 assistant action。

必须满足：

- 不计入主任务 tool-call budget。
- 不计入主任务 assistant action count。
- 不作为 trainable trajectory sample。
- 不隐藏原始 provider context_limit 错误。
- 不覆盖第一次失败的 raw provider request / response。
- 重试的主模型调用必须引用新的 `prepared_messages_ref` 和 `model_input_hash`。

训练导出时可以选择保留 Reactive Compact 相关事件作为诊断信息，但不能把 compact-only response 当作模型解决任务的一步动作。可训练样本应绑定重试后的主模型输入和输出，并通过事件链说明它是在 Reactive Compact 之后产生的。

#### 9.10.6 最小验收行为

Reactive Compact 的最小可接受行为是：

```text
如果 provider 返回 context_limit：
  记录原始失败；
  优先执行一次 emergency AutoCompact；
  如果 compact-only source 超限或 emergency compact 不可用，
  按策略执行一次 PTL round truncation fallback；
  成功后重试一次；
  重试成功则继续；
  重试失败则停止；
  所有中间 artifact 可审计。
```

它不是日常上下文控制主力，也不是替代主动 AutoCompact 的机制。它只负责兜住本地估算和 provider 实际限制不一致造成的最后一类失败。

## 10. 与后续压缩机制的关系

本决策有意把前两层工具结果 compact 限定为 L0 层，把 count / pressure based MicroCompact 作为 L1 轻量清理层。

推荐后续层次如下：

```text
L0A single_tool_result_persistence:
  单个工具结果过大时立即落盘。

L0B per_turn_tool_result_budget:
  当前这一轮新增工具结果聚合过大时落盘。

L1 Count / Pressure Based MicroCompact:
  当 compactable tool result 数量和可见内容量都明显偏大时，
  清理旧 compactable tool result 的 content。

L2 AutoCompact:
  用结构化语义摘要、最近原文尾部和确定性恢复材料重建当前工作状态。

L3 Reactive Compact:
  provider 返回 context_limit 后，只允许一次 provider verified recovery。
  优先使用 emergency AutoCompact；
  compact-only 输入本身超限或失败时，使用按 API round 裁剪的 PTL fallback。

L4 Session Memory:
  在 AutoCompact 稳定之后，再考虑单个 run 内的持续工作记忆。

后续可选 Context Collapse:
  把历史上下文投影成更紧凑的结构化上下文。
  当前不作为 RepoHarness 初始主线。

后续可选 Emergency Message Prune:
  借鉴 Snip Compact 的消息级裁剪思想，但暂时不作为主线机制。
```

因此，历史内容膨胀不再由 L0 工具结果 compact 解决。L0 只保证工具结果第一次进入上下文时不会造成明显爆量。旧工具结果内容膨胀先由 L1 MicroCompact 做轻量清理；更复杂的历史语义保留和任务状态重建，由 L2 AutoCompact 解决。Session Memory 和 Context Collapse 都可以作为后续增强，但不应阻塞当前 AutoCompact 落地。

## 11. 验收标准

因为当前阶段只是设计记录，并且计划在完整上下文压缩体系实现后再继续 smoke，所以本文不要求立即复跑 targeted smoke。

后续实现工具结果 compact、MicroCompact、AutoCompact 和 Reactive Compact 时，至少需要以下测试和检查：

1. 单个工具结果超过阈值时，模型可见内容变成 persisted preview，完整内容进入当前 run artifact。
2. 同一轮多个 fresh tool result 聚合超过阈值时，从最大的 fresh 结果开始替换，直到这一轮聚合大小回到预算以内。
3. prepared candidate 阶段不能冻结工具结果命运；只有 provider-committed 主模型输入才能提交 full_visible 或 persisted_preview。
4. 已替换的 provider-committed 工具结果后续轮次必须复用完全相同的 replacement preview。
5. 已 provider-committed 但未替换的工具结果，后续不能再被工具结果预算层替换。
6. `read_tool_result_artifact` 只能读取 `ToolResultArtifactIndex` 中正向登记、`publishable_after_visibility_scan = true` 且 `recovery_unlocked_after_provider_commit = true` 的工具结果 artifact，不能读取 prepared candidate 提前生成但未解锁的 artifact，也不能读取普通 artifact manifest、raw `ArtifactRef`、路径或 evaluator-only 内容。
7. 如果工具结果 artifact 被 redacted，恢复读取必须拒绝。
8. 训练导出必须绑定每一次主模型调用真实的 `prepared_messages_ref`、`provider_request_projection_hash` 和 `model_input_hash`，不能用最终 compact 状态覆盖历史。
9. 旧的历史工具结果老化替换如果保留，只能作为 legacy 策略显式启用，不能和 `claude_code_fresh_only_v1` 混用。
10. 当 compactable tool result 数量不足 30，或可见内容总量不足 60,000 字符时，MicroCompact 不应触发。
11. 当 MicroCompact 触发时，只能保留最近 15 个 compactable tool result，并把更旧 compactable tool result 的 provider-prepared `content` 设置为 `[Old tool result content cleared]`。
12. MicroCompact 不能删除消息，不能删除 tool result id，不能破坏 tool call / tool result 配对，也不能销毁原始工具结果事实。
13. MicroCompact 必须幂等，重复执行不能重复计算节省，也不能产生冲突事件。
14. AutoCompact 触发阈值必须基于真实 provider request projection 的 `effective_context_budget_tokens`，不能默认固定使用 `120000`。
15. 当 `harness_context_cap_tokens` 显式设置时，AutoCompact 必须按该 cap 计算阈值，并在事件中记录预算来源。
16. AutoCompact compact-only 请求不能携带工具，不能读取 evaluator-only 信息，不能产生训练样本中的主任务动作。
17. AutoCompact compact-only 请求自身如果超限，不能生成伪摘要，必须记录 `auto_compact_source_too_large`，必要时交给 Reactive Compact 的 PTL fallback。
18. AutoCompact 成功后必须插入 compact boundary 和 compact summary，并保留最近原文尾部。
19. AutoCompact 不能切断 assistant tool call 和对应 tool result。
20. AutoCompact 后必须再次执行 `prepare_messages` 和工具调用 / 工具结果配对校验。
21. 如果压缩后高于 `post_compact_target_tokens` 但低于硬限制，应继续运行并记录 `post_compact_above_target = true`，不能在同一轮自动反复压缩。
22. 如果压缩后仍高于 `hard_context_limit_ratio`，必须按 `strict_local_preflight` 停止，或按显式策略进入 hard preflight recovery；不能把本地 preflight 超限记为 Reactive Compact。
23. Reactive Compact 对同一次 provider context_limit 错误最多重试一次。
24. Reactive Compact 优先复用 AutoCompactRunner 的 emergency 模式，但必须有按 API round 分组的 `truncate_head_for_ptl_retry` fallback。
25. PTL fallback 必须保持 tool call / tool result 配对，并插入 synthetic user marker。
26. 训练导出必须能复原 AutoCompact 前的源消息、compact summary、压缩后主模型实际看到的 messages、rehydration artifact 和 PTL synthetic marker。
27. `source_prepared_messages_ref`、`compact_source_messages_ref`、`provider_request_projection_hash` 必须可复核，不能只依赖 source message hash 列表。
28. Reactive Compact 必须记录原始 provider context_limit 失败的 `original_model_call_id`、`original_provider_error_ref`、`ptl_truncation_ref` 和重试的 `retry_model_call_id`。
29. Reactive Compact 的 compact-only response 不能计入主任务 assistant action、tool-call budget 或 trainable trajectory sample。
30. 如果 emergency AutoCompact 或 PTL fallback 成功但重试后仍然 provider context_limit，停止原因必须是 `context_limit_after_reactive_compact`。
31. 如果 emergency AutoCompact 和 PTL fallback 都失败，停止原因必须是 `reactive_compact_failed`。
32. 必须生成 `context_policy_snapshot`，冻结工具结果预算、MicroCompact、AutoCompact、Reactive Compact、recovery tool、模型窗口来源、harness cap、输出预留和安全余量等所有会影响输入视图的策略字段。

## 12. 当前结论

后续主线设计应采用：

```text
上下文压缩主线 =
  单结果落盘
  + 本轮聚合预算
  + 命运冻结
  + 安全 artifact 恢复
  + count / pressure based MicroCompact
  + 同步 AutoCompact
  + provider verified Reactive Compact
  + 必要时按 API round 裁剪的 PTL fallback。
```

不再采用：

```text
工具结果 compact = 历史所有工具结果聚合后，持续替换旧工具结果。
```

当前保留的核心决策是合理的：

1. 单个工具结果过大时立即落盘，解决单次工具输出过大的问题。
2. 当前这一轮工具结果聚合过大时落盘，解决同一轮多个工具结果合计过大的问题。
3. 当 compactable tool result 数量大于等于 30 且可见内容总量大于等于 60,000 字符时触发 MicroCompact，保留最近 15 个 compactable tool result，解决旧工具结果内容在长任务中持续膨胀的问题。
4. AutoCompact 默认基于当前模型的有效上下文预算触发，而不是固定使用 `max_context_tokens = 120000`。
5. RepoHarness 初始 AutoCompact 不依赖 subagent 和 streaming，而是使用一次同步 compact-only 模型请求生成结构化摘要。
6. `post_compact_target_ratio` 和 `post_compact_target_max_tokens` 是压缩质量目标，不是同一轮反复压缩的循环条件。
7. 压缩后必须通过 compact boundary、compact summary、最近原文尾部和确定性 rehydration messages 重建主模型可见上下文。
8. Reactive Compact 只在 provider 真实返回 `context_limit` / `prompt too long` 后触发，并且只允许一次 provider verified recovery 和一次主模型重试。优先使用 emergency AutoCompact；如果 compact-only 输入本身超限或 emergency compact 失败且策略允许，则使用按 API round 分组、保持工具配对并插入 synthetic marker 的 PTL fallback。

这个决策让 RepoHarness 的工具结果治理和语义压缩主线更接近 Claude Code 的关键不变量，但避免依赖 Claude Code 的内部 subagent、私有 cache 能力和产品级 streaming 复杂度。Snip Compact 和 Context Collapse 暂时不作为主线机制；完整上下文压缩体系实现之前，不继续把 targeted smoke 结果作为上下文压缩能力的最终判断依据。
