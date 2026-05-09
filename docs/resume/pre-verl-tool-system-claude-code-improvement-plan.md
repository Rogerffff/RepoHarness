# Pre-verl 工具系统 Claude Code 对照改进方案

更新时间：2026-05-08

本文是 `docs/resume/pre-verl-targeted-smoke-claude-code-remediation-plan.md` 的工具系统专项补充。前者重点收口 targeted smoke（定向冒烟测试）暴露的搜索、初始上下文、no-progress（无进展状态）和上下文预算问题；本文只从工具角度回答一个问题：如果以 `reference/claude-code-typescript-src` 中的 Claude Code 工具系统作为产品级参考，RepoHarness 在接入 RL（强化学习）训练框架之前，最值得补齐哪些工具能力、工具返回值语义、工具执行协议和工具证据。

说明：用户提到的参考入口是 `reference/claude-code-typescript-src/AGENT.md`，本轮仓库中实际可读入口是 `reference/claude-code-typescript-src/AGENTS.md`。

## 1. 总结结论

RepoHarness 当前已经具备一个面向评测和训练导出的最小可审计工具协议：工具有稳定名称、输入输出 schema、权限检查、结构化结果、artifact 引用、路径边界检查、受控 `bash`、受控 `run_tests`、工具 schema snapshot 和 transcript 回流。这一点已经明显强于简单的“命令透传式 harness”。

但是，和 Claude Code 的工具系统相比，当前 RepoHarness 仍然更像“评测闭环中的最小工具层”，还不是一个能稳定引导模型完成真实仓库修复的工程智能体工具环境。targeted smoke 的失败模式也支持这个判断：模型在 `list_files`、`grep`、`read_file` 之间长时间循环，迟迟不进入补丁阶段；`grep` 曾经把真实存在的 `MultiValue` 报告为 complete no match；上下文结果替换已经发生但仍然触发 `context_limit`；no-progress 诊断在 smoke 产物里没有稳定变成模型可见的纠偏消息。

本轮最重要的建议不是盲目增加很多新工具，而是先把现有工具协议变得更可信、更能驱动下一步行动、更容易被验收证据证明。优先级最高的方向有四个：

1. 搜索工具必须可信。任何 `complete_no_match` 都必须经过 workspace backend 一致性和回归测试冻结，不能让模型基于错误事实放弃正确文件。
2. 工具返回值必须直接指导下一步。搜索、文件列表、读取、编辑失败和上下文替换都要给出结构化的 recommended next calls，而不是只返回自然语言片段。
3. no-progress 必须模型可见。Harness 已经能发现模型在空转时，应在下一轮 provider call 前注入短而明确的控制消息，而不是只写入 metrics。
4. 工具协议必须可冻结。formal baseline（正式基线）需要写明 tool execution mode（工具执行模式）、tool result envelope version（工具结果封装版本）、search fact policy（搜索事实策略）、context replacement policy（上下文替换策略）、nudge policy（模型可见提醒策略）和可用工具集合，否则后续 23 条 SWE Lite 结果难以判断是模型能力、工具协议还是上下文策略造成的差异。

## 2. 证据范围

本轮参考了三类材料。

第一类是 Claude Code 参考源码。核心入口包括：

- `reference/claude-code-typescript-src/AGENTS.md`
- `reference/claude-code-typescript-src/Tool.ts`
- `reference/claude-code-typescript-src/tools.ts`
- `reference/claude-code-typescript-src/services/tools/toolOrchestration.ts`
- `reference/claude-code-typescript-src/services/tools/toolExecution.ts`
- `reference/claude-code-typescript-src/tools/GrepTool/GrepTool.ts`
- `reference/claude-code-typescript-src/tools/GlobTool/GlobTool.ts`
- `reference/claude-code-typescript-src/tools/FileReadTool/FileReadTool.ts`
- `reference/claude-code-typescript-src/tools/FileEditTool/FileEditTool.ts`
- `reference/claude-code-typescript-src/tools/TodoWriteTool/TodoWriteTool.ts`
- `reference/claude-code-typescript-src/tools/AgentTool/AgentTool.tsx`

第二类是 RepoHarness 当前实现。核心入口包括：

- `src/repo_harness/tools/minimal.py`
- `src/repo_harness/tools/schemas.py`
- `src/repo_harness/agent_loop/loop.py`
- `src/repo_harness/context/builder.py`
- `src/repo_harness/context/manager.py`
- `src/repo_harness/permissions/system.py`
- `src/repo_harness/run_metadata/tool_snapshot.py`
- `src/repo_harness/run_metadata/schemas.py`
- `src/repo_harness/evaluation/runner.py`

第三类是 targeted smoke 产物：

- `runs/pre-verl-agentloop-targeted-smoke-deepseek-flash-tool-context-convergence-20260508T055743Z/`

该目录下 5 条任务的失败模式高度集中：`001`、`014`、`015` 都是 `max_turns` 且空 patch；`017` 有 1 次 `edit_file` 但 final verifier 拒绝；`020` 是 `context_limit` 且空 patch。`020` 的 `grep` 曾经把 `MultiValue` 报告为“扫描完成后没有匹配”，但工作区中实际存在 `pydicom/multival.py` 和多个引用位置。这是工具事实可信度问题，不应该归因给模型能力。

## 3. RepoHarness 当前工具基线

当前默认工具集合来自 `src/repo_harness/tools/minimal.py`：

| 工具 | 当前定位 | 工具层价值 | 主要缺口 |
| --- | --- | --- | --- |
| `list_files` | 文件发现、目录浏览、glob 风格筛选 | 能限制模型先看可见文件范围 | 工具名称不像 Claude Code 的 `Glob` 那样直观；返回值还需要更强地引导下一步搜索和读取 |
| `read_file` | 读取文本文件，支持 offset 和 limit | 能返回 `content_hash`，为安全编辑提供依据 | 对“编辑前必须读过文件”的约束还不够强；不支持 notebook、PDF、图片，这对 SWE Lite 不是阻塞 |
| `grep` | 内容搜索，支持 root、glob、mode、output_mode、context_lines | 当前已加入 `result_kind`、`scan_complete`、`recommended_next_calls`、`search_fact_policy_version` 等字段 | 必须用 smoke 回归冻结不能出现 false complete no-match；返回 envelope 还需要统一 |
| `edit_file` | 精确字符串替换 | 有 line-number 防误用、ambiguity 检查、可选 `expected_content_hash` | 建议在 formal 模式要求“先读后改”或强制 `expected_content_hash` |
| `create_file` | 创建新文件 | 简单直接 | 需要和 edit/write 权限、路径可见性、文件状态缓存统一 |
| `bash` | 受控诊断命令 | 通过命令策略和 `safe_argv` 限制危险行为 | 仍需要在 manifest 中说明它不是任意 shell，不应被描述成生产级安全沙箱 |
| `run_tests` | 受控测试反馈 | 能走 verifier feedback facade，formal final-only 时可移除 | 必须持续证明不会泄露 hidden verifier 材料 |
| `git_diff` | 检查模型改动 | 对最终 patch 很关键 | 可以进一步和编辑归因、文件历史结合 |

这些工具的 schema 和元数据已经能写入 tool schema snapshot，但是当前 snapshot 没有完整表达 Claude Code 风格的工具协议细节，例如每个工具的 `is_concurrency_safe`、`search_hint`、`strict`、`interrupt_behavior`、是否会修改上下文、是否是 open-world 工具、是否 deferred、工具执行模式是否 serial。当前 `ToolProtocolFacts` 也没有 `tool_execution_mode` 字段，因此 formal 结果里容易出现“工具声明并发安全，但 runtime 仍串行”的解释空洞。

## 4. Claude Code 工具系统的不变量

Claude Code 的工具系统可以概括成以下几个不变量。RepoHarness 不需要完整复刻产品功能，但应该迁移这些协议思想。

### 4.1 工具是完整协议，不只是函数

Claude Code 的 `Tool` 接口不仅包含 name、description、input schema 和 call，还包含：

- 输入 schema 和输出 schema；
- 自定义输入校验；
- 权限检查；
- 是否只读；
- 是否破坏性；
- 是否可以并发；
- 中断行为；
- 是否是搜索或读取命令；
- 是否 open-world；
- 是否需要用户交互；
- 最大结果大小；
- 工具结果到 `tool_result` block 的映射；
- 可选 `contextModifier` 和 `newMessages`。

RepoHarness 当前的 `ToolDefinition` 已经有一部分字段，但仍然是静态和简化版本。短期不需要把所有字段都实现成 runtime 行为，但应该先写入 snapshot，明确哪些能力启用、哪些能力禁用、哪些能力仅是声明。

### 4.2 工具生命周期是可审计管线

Claude Code 的单次工具执行大致是：

```text
locate tool
-> schema validation
-> tool-specific validation
-> PreToolUse hooks
-> permission decision
-> tool.call()
-> result mapping
-> large-result storage or replacement
-> PostToolUse hooks
-> model-visible tool_result
```

RepoHarness 当前也有 schema 校验、权限检查、执行、结果记录和 artifact 引用，但 hook、result mapping、large-result storage、permission denied retry hint、tool-specific validation 还没有形成统一协议。对评测 harness 来说，最先应该补齐的不是交互式 hook，而是把每个阶段写成稳定事件：`tool_validation_started`、`tool_validation_failed`、`tool_permission_decided`、`tool_execution_started`、`tool_result_mapped`、`tool_result_budget_replaced` 等。这样后续可以判断失败是模型给错参数、权限策略拒绝、工具执行失败、返回值被压缩，还是上下文预算策略导致信息丢失。

### 4.3 搜索、文件发现、读取和编辑是分层工作流

Claude Code 明确区分 `Glob` 和 `Grep`：

- `Glob` 负责按路径模式找文件；
- `Grep` 负责按内容找文件或内容片段；
- `FileRead` 负责窄范围读取；
- `FileEdit` 负责基于已读内容的精确替换。

RepoHarness 当前把路径发现和 glob 能力放在 `list_files`，把内容搜索放在 `grep`。能力上可以完成任务，但模型在 smoke 中大量重复 `grep` 和 `read_file`，说明提示和返回值没有足够强地形成“先文件、再内容、再窄读、再补丁”的节奏。建议短期不重命名原工具，以免破坏 baseline；但可以新增一个 `glob_files` alias 或在 `list_files` 返回值中显式写出 `tool_family="glob_like_file_discovery"`，并将 `grep` 的默认建议改成优先 `output_mode="files_with_matches"`。

### 4.4 工具返回值可以修改后续上下文

Claude Code 的 `ToolResult` 可以带 `contextModifier` 和 `newMessages`。这意味着工具结果不只是文本，而可以对后续上下文产生确定性影响。例如读取文件后更新文件状态，某些工具结果触发额外上下文，或者工具发现动态激活能力。

RepoHarness 当前已经有 harness 级别的 context warning 和 convergence nudge，也有 ContextManager 的工具结果替换，但这些主要在 agent loop 或 context manager 层处理，并不是工具协议的一部分。短期可以继续保持这个分层；但 tool result envelope 应该预留 `context_effects` 字段，至少能表达：

- 是否更新了 file state cache；
- 是否触发了 model-visible control message；
- 是否写入了大结果 artifact；
- 是否建议替换后续上下文中的旧 tool result；
- 是否产生了不可训练的 harness control message。

### 4.5 并发是保守的、可证明的

Claude Code 默认工具并发不安全，只有显式声明安全的工具才可并发；连续并发安全工具可以批量执行；非并发安全工具串行。需要注意的是，Claude Code 的并发工具结果可以按完成顺序产出，稳定按原始工具调用顺序应用的是 `contextModifier` 这类上下文修改效果。

RepoHarness 当前工具定义中已经有 `is_concurrency_safe=True`，但 agent loop 仍然逐个执行工具调用。这个状态本身可以接受，因为 formal baseline 最重要的是稳定性；问题是 metadata 必须诚实写出 runtime 是 `serial_v0`，否则后续分析工具效率时会误读。中期如果 RepoHarness 增加只读工具批处理，建议为了轨迹可复现性采用比 Claude Code 更保守的回填规则：transcript 中 tool result 按原始 tool call 顺序写入，所有 context effects 延后到批次结束后按原始顺序提交。

### 4.6 大结果处理不能只是截断

Claude Code 会把大工具结果持久化，并给模型保留可恢复预览。RepoHarness 当前有 artifact refs、tool result replacement 和 recovery call 提示，这是正确方向。targeted smoke 的 `020` 说明，当前替换策略仍然可能在长时间读搜循环中不够强。下一步应把“替换后是否仍然超预算”变成明确诊断和验收条件，而不是只在最后看到 `context_limit`。

## 5. targeted smoke 暴露的工具层问题

### 5.1 搜索事实曾经不可信

`020` 中，模型搜索 `MultiValue` 时得到“完整扫描后没有匹配”的结果，但真实工作区存在 `pydicom/multival.py`，并且多个文件引用了 `MultiValue`。这种错误会直接破坏模型的问题定位过程，因为模型会把“没有匹配”当成事实。

当前代码已经有若干修复迹象：`grep` 通过 workspace adapter 读取模型可见文本，返回 `search_fact_policy_version="repo_harness_search_fact_trust_v1"`，并区分 `complete_no_match`、`partial_scan_no_match`、`matches_found` 等结果。但是这个问题必须有回归测试和 inspect 证据冻结，不能只靠代码阅读。

建议验收标准：

- 在同一 pydicom 工作区中，`grep(query="MultiValue", root="pydicom", output_mode="files_with_matches")` 必须返回 `pydicom/multival.py` 或至少返回引用文件；
- 如果 backend 不能完整扫描，结果必须是 `partial_scan_no_match` 或 `scan_complete=false`，不能是 `complete_no_match`；
- `read_error_count`、`visibility_error_count`、`backend_mismatch_detected` 必须进入 typed result；
- local workspace 和 Docker-based executable repository environment 都要覆盖。

### 5.2 工具结果没有稳定推动模型进入补丁阶段

`001`、`014`、`015` 的连续只读工具调用次数分别达到 47、52、50，patch 工具调用为 0。这不是单纯“模型不聪明”，因为 Harness 已经能观察到模型在工具层空转，却没有在 smoke 产物中稳定注入模型可见提醒。

当前代码已经出现 `CONVERGENCE_NUDGE_POLICY_VERSION`、`convergence_nudge_injected` event、模型可见 nudge message 等实现迹象。下一步重点不是再设计一遍，而是冻结可验收行为：

- 连续只读工具达到阈值后，下一轮 provider call 之前必须出现一条 `role="user"`、`model_visible=true`、`trainable=false` 的 harness control message；
- 这条消息必须要求模型给出候选文件、当前假设、下一步最小补丁或明确停止理由；
- metrics 中的 `loop_diagnostics_summary.model_visible_message_injected`、`convergence_nudge_count` 和 `last_convergence_nudge_turn` 必须和事件一致；
- export 时这些控制消息不能作为可训练 assistant 行为样本。

### 5.3 初始上下文对工具行动的帮助不够稳定

旧 smoke 中首轮上下文只给 artifact refs，`candidate_source_entries` 为空，模型没有可以立即行动的路径候选。当前代码已经在 `src/repo_harness/evaluation/runner.py` 中构造 `repository_action_index`，`src/repo_harness/context/builder.py` 也能把它放进首轮 user message。这个方向正确，但需要防止两个问题：

1. `repository_action_index` 只在某些 runner 路径生效，formal pre-verl agent loop 没有稳定填充；
2. `repository_action_index` 不小心使用 hidden selector、hidden patch、gold patch 或 targeted smoke hindsight。

建议把 `repository_action_index_hash`、候选来源策略、候选数量、hidden material exclusion 证明都写入 run metadata，并在 acceptance inspect 中检查。

### 5.4 工具结果 envelope 语义仍需要统一

当前 `ToolResult` 顶层只有 `truncated`，而搜索类工具 typed 字段中又有 `scan_complete`、`result_limit_reached`、`output_truncated` 等概念。对模型来说，“搜索没有匹配”“扫描没有完成”“输出被截断”“命中太多只展示前几条”是四种完全不同的信息。如果这些概念混在 `content_preview` 或一个布尔 `truncated` 中，模型很容易做出错误判断。

建议定义 `repo_harness_tool_result_envelope_v1`，至少包含：

```json
{
  "tool_result_format_version": "repo_harness_tool_result_envelope_v1",
  "status": "ok | error | denied | timeout | interrupted",
  "result_kind": "matches_found | complete_no_match | partial_scan_no_match | file_read | edit_applied | ...",
  "model_visible_text_truncated": false,
  "semantic_scan_complete": true,
  "result_limit_reached": false,
  "artifact_backed_full_result": true,
  "recommended_next_calls": [],
  "context_effects": [],
  "recovery_call": null
}
```

这不是要求所有工具都立刻有复杂字段，而是要求每个工具把“模型是否可以相信这个结果”和“下一步应该怎么恢复信息”说清楚。

## 6. 优先级改进建议

优先级含义如下：P0 表示在重新执行正式 23 条 SWE Lite 评测之前必须完成；P1 表示强烈建议在正式评测前完成，否则会降低结果的解释力；P2 表示可以在当前修复稳定后进入下一轮基线；P3 表示长期能力扩展，不应该阻塞当前 pre-verl（接入强化学习训练框架之前）测评。

### P0：冻结搜索事实可信度

目标：任何搜索工具给出的 complete no-match 都可以被信任；不能完整搜索时必须明确告诉模型。

实施内容：

1. 为 `grep` 增加 pydicom `MultiValue` 回归测试，覆盖 `root="."`、`root="pydicom"`、`glob="*.py"`、`output_mode="files_with_matches"` 和 `output_mode="content"`。
2. 覆盖 local workspace 和 Docker-based executable repository environment。
3. 在 typed result 中强制包含 `search_backend`、`workspace_execution_mode`、`candidate_file_count`、`scanned_file_count`、`read_error_count`、`visibility_error_count`、`scan_complete_reason`、`backend_mismatch_detected`。
4. 新增或扩展 inspect 命令，检查 smoke run 中不存在 “source contains symbol but grep reported complete_no_match” 的矛盾。

推荐修改文件：

- `src/repo_harness/tools/minimal.py`
- `tests/unit/test_tools.py`
- `tests/integration/test_workspace_lifecycle.py`
- `src/repo_harness/cli/` 下对应 inspect 命令文件，如果当前 inspect 命令已经存在则扩展断言。

验收证据：

```bash
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_tools.py
PATH=.venv/bin:$PATH python -m pytest -q tests/integration/test_workspace_lifecycle.py
```

### P0：把工具层 no-progress 变成模型可见控制

目标：Harness 发现模型持续只读空转时，模型下一轮必须看到纠偏消息。

实施内容：

1. 保留当前 `loop_progress_diagnostic`，但在达到阈值时强制调用 convergence nudge 注入。
2. nudge 文本必须短，避免继续消耗过多上下文。推荐格式是：

```text
你已经连续多次只读取或搜索文件，但还没有形成补丁。请用下一次回复完成以下动作之一：
1. 指出最可能需要修改的 1 到 3 个文件和理由；
2. 对其中一个文件执行最小 `edit_file`；
3. 如果信息仍不足，说明唯一缺失的信息，并只调用一个能补足该信息的工具。
```

3. `metrics.json`、`events.jsonl`、transcript 和 export 都要能证明 nudge 是模型可见但不可训练的 harness control message。
4. 如果 nudge 已实现，则重点修复 summary 一致性：`loop_diagnostics_summary.model_visible_message_injected` 不能和 `convergence_nudge_injected` event 矛盾。

推荐修改文件：

- `src/repo_harness/agent_loop/loop.py`
- `src/repo_harness/evaluation/metrics.py`
- `src/repo_harness/export/exporter.py`
- `tests/unit/test_agent_loop_protocol.py`
- `tests/unit/test_export.py`

### P0：在 formal manifest 中诚实记录工具执行协议

目标：让后续 23 条 SWE Lite 结果可以明确知道使用了什么工具协议。

实施内容：

1. 在 `ToolProtocolFacts` 或 run config facts 中加入 `tool_execution_mode="serial_v0"`。
2. 在 tool schema snapshot 中加入 `concurrency_safe_declared`、`runtime_concurrency_enabled=false`。
3. 记录 `tool_result_format_version`、`tool_call_parser_version`、`search_fact_policy_version`、`context_replacement_runtime_policy_version`、`convergence_nudge_policy_version`。
4. 如果 `run_tests` 在 final-only 模式被移除，需要在 snapshot 或 config facts 中明确记录 removal reason。

推荐修改文件：

- `src/repo_harness/run_metadata/schemas.py`
- `src/repo_harness/run_metadata/tool_snapshot.py`
- `src/repo_harness/run_metadata/writer.py`
- `tests/unit/test_run_metadata.py`

### P1：统一工具结果 envelope

目标：所有工具的返回值都能被模型和 evaluator 稳定解释。

实施内容：

1. 引入 `repo_harness_tool_result_envelope_v1`。
2. 保留现有 `ToolResult.typed` 以兼容旧产物，但要求新工具都填充统一 envelope 字段。
3. 把 `truncated` 拆清楚：顶层 `truncated` 只表示模型可见文本被截断；搜索完整性使用 `scan_complete`；命中展示限制使用 `result_limit_reached`；完整内容是否可通过 artifact 恢复使用 `artifact_backed_full_result`。
4. 在 provider message 中尽量用短文本表达关键语义，在 artifact 中保存完整结构。

推荐修改文件：

- `src/repo_harness/tools/schemas.py`
- `src/repo_harness/tools/minimal.py`
- `src/repo_harness/context/manager.py`
- `tests/unit/test_tools.py`
- `tests/unit/test_context_manager.py`

### P1：把 `list_files` 强化为 Claude Code `Glob` 风格入口

目标：让模型先定位文件集合，再做内容搜索，减少无效 `grep` 和大范围 `read_file`。

实施内容：

1. 短期不删除 `list_files`，避免破坏已有轨迹和 baseline。
2. 增加 `glob_files` alias 或 tool family 字段，让模型更容易理解它是“路径模式发现工具”。
3. `list_files` 返回结果中加入 `recommended_next_calls`，例如：
   - 文件过多：建议加更窄 `glob` 或 `path`；
   - 找到少量候选：建议对这些文件执行 `grep(output_mode="content")` 或 `read_file`；
   - 没有结果但扫描不完整：建议缩小 root 或更换 glob。
4. `grep` 的描述中强化默认工作流：先 `list_files` 或 `glob_files`，再 `grep(output_mode="files_with_matches")`，最后 `read_file`。

推荐修改文件：

- `src/repo_harness/tools/minimal.py`
- `tests/unit/test_tools.py`

### P1：编辑工具要求先读后改

目标：减少模型在没有准确上下文时做错误替换，也保护用户或其他工具已经修改过的文件。

实施内容：

1. 对已有文件的 `edit_file`，formal 模式要求该文件此前被 `read_file` 读取过。
2. `expected_content_hash` 从推荐字段升级为 formal 模式必填字段；如果暂时不能强制，则至少在缺失时返回 model-visible 警告并记录 risk。
3. 编辑失败时返回明确 recovery call，例如要求重新 `read_file(path, start_line, limit)`。
4. `git_diff` 应能报告每次编辑对应的文件和工具调用 id，形成编辑归因。

推荐修改文件：

- `src/repo_harness/tools/minimal.py`
- `src/repo_harness/agent_loop/loop.py`
- `tests/unit/test_tools.py`
- `tests/unit/test_agent_loop_protocol.py`

### P1：把上下文替换做成工具验收条件

目标：工具结果大量累积时，ContextManager 必须证明它能保留恢复路径并把 provider-ready 输入压到预算以内；如果压不进去，必须给出可解释原因。

实施内容：

1. 在 replacement artifact 中记录被替换的 tool result id、原始大小、保留预览、recovery call 和替换原因。
2. 收口现有 `replacement_applied_but_insufficient_context_limit` 一类诊断的命名、传播和验收；如果需要兼容新命名，可以增加 `replacement_applied_but_still_over_budget` 作为别名，但不要丢失已有语义。
3. 在 metrics 中记录最大 provider-ready token estimate、替换前后 token estimate、替换次数、不可替换消息数量。
4. smoke acceptance 检查 `020` 不再因为工具结果堆积直接到 `context_limit`，或者至少能说明是模型持续无效探索而不是 replacement 静默失败。

推荐修改文件：

- `src/repo_harness/context/manager.py`
- `src/repo_harness/agent_loop/loop.py`
- `src/repo_harness/evaluation/metrics.py`
- `tests/unit/test_context_manager.py`

### P2：增加轻量任务状态工具

目标：迁移 Claude Code `TodoWrite` 的核心价值，让模型在长任务中维护当前假设、候选文件和下一步动作，减少漫无目的搜索。

建议新增工具名：`update_working_state`。

该工具不修改仓库文件，不参与评分，不接触 hidden material，只维护模型可见的会话状态。建议输入字段：

```json
{
  "current_hypothesis": "string",
  "candidate_files": ["path"],
  "next_action": "string",
  "completed_steps": ["string"],
  "blocking_question": "string | null"
}
```

返回值应短小，并且在 no-progress nudge 后要求模型优先调用该工具或执行最小补丁。这个工具可能增加额外 tool calls，因此建议放在 P2，不要阻塞当前 targeted smoke 修复。

推荐修改文件：

- `src/repo_harness/tools/minimal.py`
- `src/repo_harness/agent_loop/loop.py`
- `src/repo_harness/trajectory/` 相关 schema，如果需要持久化工作状态
- `tests/unit/test_tools.py`

### P2：实现只读工具批处理，但不改变 transcript 顺序

目标：减少多工具调用的 wall-clock 时间，同时不破坏可复现轨迹。

实施内容：

1. 只允许 `is_read_only=True` 且 `is_concurrency_safe=True` 的工具进入批处理。
2. 写工具、`bash`、`run_tests`、任何可能修改上下文的工具默认串行。
3. 批处理执行可以并行，但 RepoHarness 为了可复现训练轨迹，建议 transcript 中 tool result 按原始 tool call 顺序写回；这是一项 RepoHarness 设计选择，不是对 Claude Code 当前实现的照搬。
4. 如果工具产生 context effects，先缓存，批次结束后按原始顺序应用。
5. formal baseline 初期仍建议使用 `serial_v0`；批处理作为 `readonly_batch_v0` 单独开 baseline。

推荐修改文件：

- `src/repo_harness/agent_loop/loop.py`
- `src/repo_harness/tools/minimal.py`
- `tests/unit/test_agent_loop_protocol.py`

### P2：预留工具级 context effects

目标：让工具结果对上下文的影响可审计，而不是散落在 agent loop 和 context manager 中。

实施内容：

1. 在 `ToolResult.typed` 或新 envelope 中加入 `context_effects`。
2. 第一版只允许以下枚举：
   - `file_state_updated`
   - `large_result_artifact_written`
   - `recovery_call_available`
   - `harness_control_message_suggested`
   - `tool_result_replacement_candidate`
3. 禁止工具直接注入任意系统消息，避免训练数据污染；所有模型可见控制消息仍由 agent loop 统一创建并标记 `trainable=false`。

推荐修改文件：

- `src/repo_harness/tools/schemas.py`
- `src/repo_harness/tools/minimal.py`
- `src/repo_harness/agent_loop/loop.py`

### P3：后续补齐 Claude Code 类扩展能力

以下能力会提升系统上限，但不建议阻塞 pre-verl formal evaluation：

1. 符号搜索和定义跳转工具，例如 `symbol_search`、`definition_lookup`、`diagnostics`。
2. MCP 或插件式动态工具发现，但必须通过 tool snapshot 和 deferred tool policy 固定。
3. 子智能体工具，用于未来多智能体轨迹，不应用于当前单模型 SWE Lite baseline。
4. notebook、PDF、图片读取能力。SWE Lite 主要是 Python 仓库修复，短期收益较小。
5. hook 协议。评测环境可以先记录 hook disabled，后续再引入可审计 hook。

## 7. 推荐实施顺序

### Stage A：工具协议冻结和证据修复

目标：先让 formal run 能解释自己使用了什么工具协议。

交付物：

- `ToolProtocolFacts` 增加 `tool_execution_mode="serial_v0"`；
- tool schema snapshot 增加 `concurrency_safe_declared` 和 runtime concurrency 字段；
- run config facts 写入 search、context replacement、nudge、tool result envelope policy version；
- pydicom `MultiValue` 搜索回归测试通过；
- targeted smoke inspect 能发现并拒绝 false complete no-match。

### Stage B：工具返回值和搜索工作流收口

目标：让模型更少空转，更快进入候选文件和补丁阶段。

交付物：

- 统一 tool result envelope；
- `list_files` / `grep` / `read_file` 全部带清晰 `recommended_next_calls`；
- `grep` no-match 和 partial scan 文本清楚区分；
- `list_files` 增加 Glob-like alias 或 tool family；
- acceptance 检查 5 条 targeted smoke 的连续只读工具次数下降，或者至少出现模型可见 nudge 后的明确收敛行为。

### Stage C：编辑安全和上下文预算

目标：提高补丁阶段质量，减少 `context_limit`。

交付物：

- formal 模式要求编辑前读文件或提供 `expected_content_hash`；
- 编辑失败返回 recovery call；
- `git_diff` 和编辑工具调用 id 绑定；
- ContextManager replacement 诊断可验收；
- `020` 不再出现“replacement 已发生但最终只剩 context_limit，缺少中间解释”的情况。

### Stage D：可选工具能力扩展

目标：在当前 baseline 稳定后，再提升上限。

交付物：

- `update_working_state` 轻量任务状态工具；
- `readonly_batch_v0` 只读批处理执行模式；
- `context_effects` 字段；
- symbol / diagnostics 工具试验 baseline；
- deferred tool / MCP / subagent 作为后续版本，不混入当前 formal baseline。

## 8. 最小验收清单

在重新运行 23 条 SWE Lite 任务前，至少完成以下验收：

```bash
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_tools.py
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_agent_loop_protocol.py
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_context_builder.py
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_context_manager.py
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_run_metadata.py
```

针对 targeted smoke，还需要有专门的 inspect 或脚本证明：

1. `grep` 不再对真实存在的符号返回 false complete no-match；
2. 首轮上下文包含非空 `repository_action_index`，并证明没有 hidden material；
3. 连续只读空转达到阈值后，模型可见 convergence nudge 被注入；
4. `loop_diagnostics_summary` 和 `convergence_nudge_injected` 事件一致；
5. tool schema snapshot 记录 `tool_execution_mode="serial_v0"`；
6. final-only 配置下 `run_tests` 的可见性和移除原因可审计；
7. context replacement artifact 包含 recovery call，且替换后预算状态可解释。

## 9. 对简历展示结果的影响

如果上述 P0 和 P1 完成，再执行 23 条 SWE Lite 任务，结果会更适合作为简历展示，因为你可以把评测结论拆清楚：

- 如果模型仍然失败，但工具事实可信、上下文预算可解释、no-progress 已模型可见，则更可能是模型能力或任务难度问题；
- 如果模型进入补丁阶段的比例提升，说明 Harness 的工具协议和上下文控制确实改善了 agent 行为；
- 如果某些任务失败于 final verifier，则可以把失败归类为补丁质量问题，而不是工具误导或上下文缺失；
- 如果 run metadata 中冻结了工具协议，就能把不同模型、不同 baseline、不同修复阶段的结果进行可审计对比。

最终对外表述建议是：RepoHarness 在接入 RL 训练框架前，先完成了一轮工具系统可信度和交互协议加固。它的目标不是复刻 Claude Code 产品，也不是构建生产级安全沙箱，而是把真实仓库任务中的工具调用、上下文控制、权限边界、补丁生成和最终验证变成可执行、可审计、可导出的训练轨迹。

## 10. 子代理复核记录

本文档已经过子代理只读复核。复核结论是：主体描述可以作为最终建议返回，但需要修正两处准确性问题；本文已经完成对应修订。

已修正的问题：

1. 并发工具结果顺序：原文把 Claude Code 的并发工具结果描述为按原始工具调用顺序回填。复核指出 Claude Code 稳定按原始顺序应用的是 `contextModifier`，并发 `tool_result` 可以按完成顺序产出。本文已改为：RepoHarness 如果实现只读批处理，为了可复现训练轨迹，建议主动选择按原始 tool call 顺序写 transcript。
2. 上下文替换诊断：原文建议新增 `replacement_applied_but_still_over_budget`。复核指出当前 ContextManager 已经有语义相近的 `replacement_applied_but_insufficient_context_limit` 和 recovery 信息。本文已改为：优先收口现有诊断的命名、传播、metrics 和 inspect 验收；如果需要兼容新命名，再增加别名。

复核确认的事项：

- Claude Code 工具系统主体描述和参考源码一致。
- 文档已经区分 targeted smoke 暴露的历史问题、当前代码已经出现的修复迹象和仍需验收的建议。
- 文档没有把 RepoHarness 描述成生产级安全沙箱、完整 Claude Code 复刻、公开榜单系统或已经训练出模型的项目。
- P0、P1、P2、P3 建议总体落到了具体文件、测试方向和验收证据。
