# Pre-verl 工具能力改进执行文档

更新时间：2026-05-08

本文是 `docs/resume/pre-verl-tool-system-claude-code-improvement-plan.md` 的后续执行文档，目标是在新的 Docker targeted smoke 已经证明 Stage A 到 Stage D 主链路可用之后，一次性实现剩余五个直接影响模型解题能力的工具改进，避免后续正式二十三题评测前遗漏。

本轮不再把主要精力放在搜索事实可信、`repository_action_index`、convergence nudge 和 context replacement recovery 这些旧阻塞项上。它们已经在本次 targeted smoke 中通过了模型可见上下文检查和最终边界检查。本文聚焦下面五项新能力：

1. `edit_file` 编辑前读文件和 `expected_content_hash` 强化。
2. `list_files` 的 Glob-like 文件发现入口，以及可选 `glob_files` 兼容工具。
3. 统一关键工具的 ToolResult envelope，让模型稳定理解“结果是否可信、是否完整、下一步如何恢复”。
4. 新增 `update_working_state` 轻量任务状态工具。
5. 新增轻量符号级代码导航工具。

## 1. 当前基线判断

本轮新的 Docker targeted smoke 目录是：

`runs/pre-verl-agentloop-targeted-smoke-deepseek-flash-tool-context-convergence-actionindex-20260508T105300Z/`

已经确认的事实：

- 五个 run 的 `inspect-model-visible-context` 检查通过，包括 `--assert-no-hidden-test-material`、`--assert-prepared-messages-bound`、`--assert-provider-body-equivalent`、`--assert-tool-results-recoverable` 和 `--assert-no-over-redaction`。
- `inspect-pre-verl-agentloop-boundary-index` 检查通过。
- 五个任务首轮 `repository_action_index` 都是非空，且目标实现文件进入候选列表。
- `017 astroid` 和 `020 pydicom` 已经 accepted。
- `001 sqlfluff` 和 `015 astroid` 进入了补丁阶段，但 final verifier 拒绝，失败更像补丁质量问题。
- `014 astroid` 仍然 `max_turns`，并且 `first_edit=None`，说明模型仍可能在读文件和搜索之间空转。

因此，接下来应该从“修复 Harness 阻塞问题”切换到“提高模型定位、决策和补丁质量的工具能力”。

## 2. 总体实施顺序

虽然五项能力建议在同一轮实现，但不要同时改完再一起验证。推荐按下面顺序推进，每完成一步都运行对应单元测试，最后再统一跑 targeted smoke。

| 顺序 | 能力项 | 先做原因 | 主要文件 |
| --- | --- | --- | --- |
| 第 1 步 | ToolResult envelope | 后续四项工具都要复用统一返回语义，先建立底座 | `src/repo_harness/tools/schemas.py`、`src/repo_harness/tools/minimal.py` |
| 第 2 步 | `edit_file` 编辑前读文件和 hash 强化 | 直接提升补丁质量，针对 `001`、`015` 这类已编辑但错误的任务 | `src/repo_harness/tools/minimal.py`、`src/repo_harness/agent_loop/loop.py` |
| 第 3 步 | Glob-like 文件发现和 `glob_files` | 减少模型用 `grep` 做路径发现，降低 `014` 继续空转概率 | `src/repo_harness/tools/minimal.py`、`src/repo_harness/permissions/system.py` |
| 第 4 步 | `update_working_state` | 让 nudge 之后的模型能显式收敛假设和下一步动作 | `src/repo_harness/tools/minimal.py`、`src/repo_harness/agent_loop/schemas.py`、`src/repo_harness/agent_loop/loop.py` |
| 第 5 步 | 符号级导航工具 | 给 astroid 这类结构化 Python 仓库提供比纯 grep 更强的代码入口 | 新增 `src/repo_harness/tools/symbol_index.py`，并接入 `minimal.py` |

这样排序的理由是：先统一工具结果语义，再提高编辑安全，然后改文件发现，最后补状态管理和符号导航。这个顺序可以让每一步都有明确收益，也能减少后续重写。

## 3. 第 1 步：统一 ToolResult envelope

### 3.1 要解决的问题

当前 `ToolResult` 顶层字段较少，关键语义主要散落在 `typed` 中。`grep`、`list_files`、`read_file` 和 `edit_file` 各自已经有不少结构化字段，但模型和评测代码没有一套统一约定来理解：

- 这个结果是否是完整事实；
- 模型可见文本是否被截断；
- 是否有更多结果页；
- 是否可以通过 artifact 或 recovery call 恢复；
- 下一步最合理的工具调用是什么。

这会导致模型在不同工具之间处理失败、截断和恢复提示时不够稳定。

### 3.2 具体实现

第一版不要破坏现有 `ToolResult` schema，不要删除现有 `typed` 字段。建议采用兼容做法：在每个关键工具的 `typed` 中新增统一子对象 `result_envelope`。

建议字段：

```json
{
  "schema_version": "repo_harness_tool_result_envelope_v1",
  "result_kind": "complete_with_matches",
  "semantic_complete": true,
  "model_visible_text_truncated": false,
  "result_limit_reached": false,
  "artifact_backed_full_result": true,
  "recommended_next_calls": [],
  "recovery_call": null,
  "recovery_hint": null,
  "context_effects": []
}
```

字段含义：

- `result_kind`：复用每个工具已经有的结果类型，例如 `complete_with_matches`、`complete_no_match`、`partial_scan_no_match`、`file_read`、`edit_applied`、`stale_file_state`。
- `semantic_complete`：表示这个结果能否作为完整事实使用。对于 `grep` 来说，只有没有读取错误、没有可见性错误、没有 backend mismatch 时才是 `true`。
- `model_visible_text_truncated`：只描述给模型看的文本是否被截断，不描述搜索是否完整。
- `result_limit_reached`：表示结果分页或命中数量达到上限。
- `artifact_backed_full_result`：表示完整内容是否能从 artifact 恢复。
- `recommended_next_calls`：复用现有字段，但统一放入 envelope。
- `recovery_call`：给出一条可恢复调用，例如 `read_file(path="x.py", start_line=20, limit=120)`。
- `context_effects`：第一版只允许枚举值，不允许工具直接注入任意消息。

需要新增一个小 helper，避免每个工具手写不同结构。建议放在 `src/repo_harness/tools/minimal.py`，后续如果文件继续膨胀，再迁移到 `src/repo_harness/tools/result_envelope.py`。

建议 helper：

```python
def _result_envelope(
    *,
    result_kind: str,
    semantic_complete: bool,
    model_visible_text_truncated: bool = False,
    result_limit_reached: bool = False,
    artifact_backed_full_result: bool = False,
    recommended_next_calls: list[dict[str, Any]] | None = None,
    recovery_call: str | None = None,
    recovery_hint: str | None = None,
    context_effects: list[str] | None = None,
) -> dict[str, Any]:
    ...
```

第一批覆盖工具：

- `list_files`
- `grep`
- `read_file`
- `edit_file`
- `git_diff`

暂时不要求 `bash` 和 `run_tests` 使用复杂 envelope，因为当前 formal pre-verl final-only 评测中 `run_tests` 被禁用，`bash` 也不是主要解题工具。

### 3.3 验证方式

新增或更新测试：

- `tests/unit/test_tools.py::test_tool_result_envelope_present_for_core_tools`
- `tests/unit/test_tools.py::test_grep_envelope_marks_partial_scan_as_not_semantically_complete`
- `tests/unit/test_tools.py::test_read_file_envelope_has_recovery_call_when_truncated`
- `tests/unit/test_context_manager.py::test_replacement_preserves_result_envelope_recovery`

运行命令：

```bash
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_tools.py tests/unit/test_context_manager.py
```

验收标准：

- 关键工具的 `typed.result_envelope.schema_version` 都是 `repo_harness_tool_result_envelope_v1`。
- `grep` 的 `partial_scan_no_match` 必须对应 `semantic_complete=false`。
- `read_file` 被截断时 envelope 中必须有 recovery call。
- replacement summary 不能丢失 recovery call 和 envelope 关键字段。

## 4. 第 2 步：强化 `edit_file` 编辑前读文件和 hash

### 4.1 要解决的问题

当前 `edit_file` 已经支持 `expected_content_hash`，hash 不匹配会拒绝编辑。但是它仍然是推荐字段，不是 formal 模式的强约束。模型可以在没有读过文件、没有携带当前文件 hash 的情况下尝试编辑。

这会导致两个问题：

1. 模型可能基于旧上下文或猜测内容编辑，浪费工具调用。
2. 模型可能错误替换相似文本，产生 final verifier 拒绝的补丁。

这项能力直接针对本轮 smoke 中的 `001 sqlfluff` 和 `015 astroid`：它们已经进入补丁阶段，但补丁质量不够。

### 4.2 具体实现

利用当前已经存在的 `ToolExecutionContext.file_state_cache`。`read_file` 已经把 `content_hash` 写入 `context.file_state_cache[path]`，`edit_file` 成功后也会更新该缓存。

第一版 formal 规则：

```text
编辑已有文件时，必须满足以下条件之一：
1. `expected_content_hash` 等于当前文件 hash；
2. 当前 path 存在于 `file_state_cache`，并且缓存 hash 等于当前文件 hash。
```

如果两个条件都不满足，`edit_file` 返回 `status="error"`，`error_type="read_before_edit_required"`。

模型可见错误文本建议：

```text
edit_file requires a fresh read_file observation for this path in formal mode.
Call read_file(path="...") and retry edit_file with expected_content_hash from the read_file result.
```

typed 字段建议：

```json
{
  "path": "astroid/modutils.py",
  "error_type": "read_before_edit_required",
  "current_content_hash": "...",
  "cached_content_hash": null,
  "expected_content_hash": null,
  "recovery_call": "read_file(path='astroid/modutils.py', start_line=1, limit=160)",
  "result_envelope": {
    "result_kind": "read_before_edit_required",
    "semantic_complete": true,
    "recovery_call": "read_file(path='astroid/modutils.py', start_line=1, limit=160)"
  }
}
```

需要注意：

- `create_file` 不需要先读，因为它创建新文件，但如果目标文件已存在，应继续拒绝或要求改用 `edit_file`。
- 如果 `expected_content_hash` 存在但不匹配，继续使用当前的 `stale_file_state` 错误。
- 如果 `file_state_cache` 中有 hash 但当前文件 hash 已变化，应返回 `stale_file_state`，要求重新读取。
- 必须把强约束做成显式工具策略开关，例如新增 `ToolPolicy.require_read_before_edit=True`，并且只在 pre-verl formal 配置中开启。不要默认全局开启，因为这会改变非 pre-verl、replay 和旧评测的工具行为。

### 4.3 需要修改的文件

- `src/repo_harness/tools/minimal.py`
  - 在 `_edit_file()` 中增加 read-before-edit 检查。
  - 在 `_edit_file()` 失败结果中写入 `result_envelope`。
  - 在 `edit_file` prompt 中把 “Prefer passing expected_content_hash” 改成 formal 模式更强的要求。
  - 新增或消费 `ToolPolicy.require_read_before_edit`，避免影响未开启该策略的旧链路。
- `src/repo_harness/agent_loop/loop.py`
  - 确认同一个 run 中 `ToolExecutionContext.file_state_cache` 跨工具调用复用，而不是每次创建新空字典。如果现在已经复用，只加测试固定。
- `src/repo_harness/tools/schemas.py` 或当前工具策略 schema 所在文件
  - 给 `ToolPolicy` 增加 `require_read_before_edit: bool = False`。
- `src/repo_harness/run_metadata/tool_snapshot.py` 和 `tests/unit/test_run_metadata.py`
  - 记录该策略是否启用，避免正式基线和旧基线混淆。
- `tests/unit/test_tools.py`
  - 增加无 read、无 hash 时拒绝编辑。
  - 增加先 `read_file` 后 `edit_file` 成功。
  - 增加 hash 过期时拒绝编辑。
- `tests/unit/test_agent_loop_protocol.py`
  - 增加 agent loop 场景：模型先读再改成功；模型直接改被工具结果提醒恢复。

### 4.4 验证方式

运行命令：

```bash
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_tools.py tests/unit/test_agent_loop_protocol.py
```

针对 smoke 的验收标准：

- `001`、`015`、`017`、`020` 中所有成功 `edit_file` 之前，同一路径必须有 `read_file` 或正确 `expected_content_hash`。
- 如果模型尝试直接编辑，run 不应崩溃，而应得到模型可见的 recovery call。
- 成功编辑的 `typed` 中应包含 `previous_content_hash`、`content_hash` 和 `result_envelope.result_kind="edit_applied"`。

## 5. 第 3 步：强化 Glob-like 文件发现和 `glob_files`

### 5.1 要解决的问题

当前 `list_files` 已经支持 `glob`，也已经有 `recommended_next_calls`。但是从模型心智看，它仍然不像 Claude Code 的 `Glob` 那样明确承担“路径模式发现”职责。模型仍可能用 `grep` 做路径发现，尤其是在 `014 astroid` 这类任务中，它会长时间围绕同一文件读和搜。

### 5.2 具体实现

建议分两层实现。

第一层：强化现有 `list_files`。

在 `list_files` typed result 中增加：

```json
{
  "tool_family": "glob_like_file_discovery",
  "path_discovery_mode": "glob",
  "recommended_workflow": [
    "Use list_files/glob_files to narrow candidate files.",
    "Use grep(output_mode='files_with_matches') only after root or glob is narrow.",
    "Use read_file on the top candidate paths before edit_file."
  ]
}
```

第二层：新增 `glob_files` 兼容工具。

`glob_files` 不要实现第二套文件枚举逻辑。它应该是 `list_files` 的薄包装，最终走同一个 `_list_files()`、同一个 workspace adapter、同一个可见性策略、同一个 search fact policy。

建议 schema：

```json
{
  "pattern": "string",
  "path": "string, optional",
  "offset": "integer, optional",
  "max_entries": "integer, optional"
}
```

归一化规则：

```text
glob_files(pattern="**/*mod*.py", path="astroid")
等价于
list_files(path="astroid", glob="**/*mod*.py")
```

`ToolResult` 中：

- `requested_tool_name="glob_files"`
- `effective_tool_name="list_files"` 或 `effective_tool_name="glob_files"` 二选一需要固定。
- 推荐选择 `effective_tool_name="list_files"`，`route_reason="glob_files_alias_to_list_files"`，这样后续只有一套文件发现语义。

### 5.3 需要修改的文件

- `src/repo_harness/tools/minimal.py`
  - 在 `DEFAULT_TOOL_ORDER` 中加入 `glob_files`，建议放在 `list_files` 后面、`read_file` 前面。
  - 在 `normalize_request()` 中支持 `glob_files` 到 `list_files` 的路由。
  - 在 `_schema_issue()` 中加入 `glob_files.pattern`、`glob_files.path`、`glob_files.offset`、`glob_files.max_entries`。
  - 在 `build_tool()` 中新增 `glob_files` ToolDefinition。
  - 在 `_list_files_recommended_next_calls()` 中优先推荐更窄的 `glob_files` 或 `list_files`，但要保持不要无限推荐自身。
- `src/repo_harness/permissions/system.py`
  - 把 `glob_files` 加入路径参数检查，复用 `list_files` 的 path/root 规则。
- `src/repo_harness/scaffolds/patch_focused_react.py`
  - 把 `glob_files` 加入 allowed tools，并在 prompt 中明确它是文件路径发现工具。
- `src/repo_harness/run_metadata/tool_snapshot.py` 和 `tests/unit/test_run_metadata.py`
  - 固定新增工具顺序、工具 schema、output schema 和 alias route policy，确保后续 preference/export 比较能绑定到准确工具集合。
- `tests/unit/test_tools.py`
  - 增加 `glob_files` 与等价 `list_files(glob=...)` 返回同一文件集合。
  - 增加 `glob_files` 不绕过 hidden path、symlink、workspace boundary。
- `tests/unit/test_permissions.py`
  - 增加 `glob_files` 路径权限测试。

### 5.4 验证方式

运行命令：

```bash
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_tools.py tests/unit/test_permissions.py tests/unit/test_scaffold_patch_focused_react.py
```

targeted smoke 验收标准：

- prepared tool definitions 中出现 `glob_files`。
- `014 astroid` 的前几轮更倾向于使用 `glob_files` 或 `list_files(glob=...)` 定位候选文件。
- `grep` 用作内容搜索，而不是主要路径发现。
- hidden material 检查仍然通过。

## 6. 第 4 步：新增 `update_working_state`

### 6.1 要解决的问题

Convergence nudge 已经能提醒模型“不要继续空转”，但它不能替模型维护长期工作状态。`014 astroid` 本轮已经出现 nudge，但仍然 48 轮没有编辑。这说明单纯提醒不一定足够，模型需要一个轻量工具来显式记录：

- 当前修复假设是什么；
- 已经排除过哪些方向；
- 当前候选文件有哪些；
- 下一步唯一动作是什么；
- 是否还缺一个具体信息。

### 6.2 工具定义

新增工具名：`update_working_state`。

工具定位：

- 不修改仓库文件；
- 不读取 hidden material；
- 不调用 verifier；
- 不算 patch progress；
- 但可以算作 planning progress，帮助 no-progress 诊断判断模型是否在收敛。

建议 input schema：

```json
{
  "current_hypothesis": "string",
  "candidate_files": ["string"],
  "next_action": "string",
  "completed_steps": ["string"],
  "blocking_question": "string or null"
}
```

字段约束：

- `candidate_files` 最多 8 个路径，全部必须是 workspace-relative path。
- `completed_steps` 最多 12 条，每条最多 240 字符。
- `current_hypothesis` 和 `next_action` 必填，最多 1000 字符。
- `blocking_question` 可为空；如果不为空，必须是模型可通过现有工具解决的问题，不能请求 hidden tests 或 gold patch。

返回内容建议：

```text
working_state updated.
Current hypothesis: ...
Candidate files: ...
Next action: ...
```

typed 字段建议：

```json
{
  "result_kind": "working_state_updated",
  "current_hypothesis": "...",
  "candidate_files": ["astroid/modutils.py"],
  "next_action": "read astroid/modutils.py around file_from_module_name",
  "completed_step_count": 3,
  "blocking_question": null,
  "result_envelope": {
    "result_kind": "working_state_updated",
    "semantic_complete": true,
    "context_effects": ["working_state_updated"]
  }
}
```

### 6.3 AgentLoop 集成

只把工具结果写进 transcript 还不够，因为长上下文 replacement 后，最新工作状态可能被压缩掉。建议在 agent loop state 中保留一份最新 `working_state_summary`。

建议实现：

1. 在 `src/repo_harness/agent_loop/schemas.py` 中给 `AgentLoopState` 增加：

```python
working_state_summary: dict[str, Any] | None = None
working_state_update_count: int = 0
last_working_state_turn: int | None = None
```

2. 在 `_record_tool_result()` 或工具执行后，如果 `effective_tool_name=="update_working_state"` 且结果 ok，把 typed 中的工作状态写入 state。

3. 在下一轮 prepared messages 前，将最新工作状态以简短模型可见信息注入。不要作为系统消息，建议作为普通 user-side harness context，且标记不可训练：

```text
Current working state from the model's previous update:
- hypothesis: ...
- candidate files: ...
- next action: ...
```

如果当前 message schema 不适合新增单独 control message，第一版也可以只依赖 tool result 留在历史中，但必须确保 context replacement 不会删除最新一次 working state。

4. Convergence nudge 文本中增加建议：如果还没有足够信心编辑，先调用 `update_working_state` 固定当前假设和唯一下一步工具调用。

### 6.4 需要修改的文件

- `src/repo_harness/tools/minimal.py`
  - 新增 `update_working_state` ToolDefinition。
  - 新增 `_update_working_state()`。
  - 把它加入 `DEFAULT_TOOL_ORDER`，建议放在 `grep` 后、`edit_file` 前。
- `src/repo_harness/agent_loop/schemas.py`
  - 增加工作状态字段。
- `src/repo_harness/agent_loop/loop.py`
  - 在工具结果后更新 state。
  - 在 nudge 文本中引导使用该工具。
  - 在 context replacement 中保护最新 working state。
- `src/repo_harness/context/manager.py`
  - 如果 working state 作为 tool result 存在，确保最新一次不被替换；旧的可以替换为摘要。
- `src/repo_harness/export/exporter.py`
  - 明确 working state 的导出边界。如果 working state 是模型主动调用工具写出的内容，可以保留为模型行为轨迹；如果后续又把最新 working state 作为 harness control message 注入，则该注入消息必须标记 `trainable=false` 并从默认监督微调导出中排除。
- `src/repo_harness/run_metadata/tool_snapshot.py` 和 `tests/unit/test_run_metadata.py`
  - 固定 `update_working_state` 的工具 schema 和策略版本。
- `tests/unit/test_tools.py`
  - 测试 schema、字段长度、候选路径可见性、返回内容。
- `tests/unit/test_agent_loop_protocol.py`
  - 测试 working state 更新后下一轮模型可见。
  - 测试 nudge 后模型可以调用 working state，不被误判为 patch progress。
- `tests/unit/test_context_manager.py`
  - 测试最新 working state replacement 保护。
- `tests/unit/test_export.py`
  - 测试模型主动 `update_working_state` 工具调用的导出行为，以及 harness 注入的 working state context 不会作为可训练目标泄漏。

### 6.5 验证方式

运行命令：

```bash
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_tools.py tests/unit/test_agent_loop_protocol.py tests/unit/test_context_manager.py
```

targeted smoke 验收标准：

- `014 astroid` 如果仍然没有编辑，至少应该出现 `update_working_state`，并且状态中包含候选文件和下一步动作。
- 如果出现 nudge 后模型调用 `update_working_state`，后续应该减少重复搜索同一问题。
- `update_working_state` 不能让 hidden material 进入 prepared messages。
- export 中如果把 working state 作为训练轨迹保留，需要明确它是模型主动写出的状态，不是 harness 注入的隐藏答案。

## 7. 第 5 步：新增轻量符号级导航工具

### 7.1 要解决的问题

`grep` 和 `read_file` 可以完成很多定位任务，但对 Python 仓库来说，模型经常需要知道：

- 某个类或函数在哪里定义；
- 某个方法有哪些引用；
- 某个文件里有哪些 class 和 def；
- 某个符号附近的行号范围是什么。

在 `astroid` 这类任务中，纯文本搜索容易造成大量来回读取。轻量符号导航可以显著缩短定位路径。

### 7.2 工具范围

不要第一版就接入完整语言服务器。建议新增一个基于 Python `ast` 的轻量工具：`symbol_search`。

第一版只支持 Python 源码文件，覆盖 SWE Lite 中最常见的 Python 仓库任务。

建议 input schema：

```json
{
  "query": "string",
  "root": "string, optional",
  "symbol_kind": "class | function | method | any",
  "include_references": "boolean, default false",
  "max_results": "integer, default 20"
}
```

行为：

1. 使用 workspace adapter 枚举模型可见 `.py` 文件。
2. 对每个可见 Python 文件读取文本。
3. 使用 `ast.parse()` 提取：
   - `ClassDef`
   - `FunctionDef`
   - `AsyncFunctionDef`
   - class 内方法
4. 用 `query` 做精确匹配和大小写不敏感包含匹配。
5. 如果 `include_references=true`，再用 AST `Name`、`Attribute` 和简单文本行扫描提供引用候选。引用结果只作为候选，不声明完整调用图。
6. 返回路径、行号、列号、符号类型、父类或父 class、签名摘要、上下文读取建议。

输出示例：

```json
{
  "result_kind": "symbols_found",
  "query": "MultiValue",
  "definitions": [
    {
      "path": "pydicom/multival.py",
      "line": 17,
      "kind": "class",
      "name": "MultiValue",
      "read_call": "read_file(path='pydicom/multival.py', start_line=1, limit=120)"
    }
  ],
  "references": [
    {
      "path": "pydicom/dataelem.py",
      "line": 21,
      "kind": "import_or_reference"
    }
  ],
  "result_envelope": {
    "result_kind": "symbols_found",
    "semantic_complete": true,
    "recommended_next_calls": [
      {
        "tool": "read_file",
        "arguments": {"path": "pydicom/multival.py", "start_line": 1, "limit": 120}
      }
    ]
  }
}
```

### 7.3 不要过度承诺

第一版符号工具只能描述为“AST-based Python symbol navigation”，不能描述成完整语言服务器或完整静态分析。它不保证动态引用完整，不解析运行时 monkey patch，也不读取 hidden tests。

如果某个文件 AST parse 失败：

- 不应让整个工具失败；
- 应记录 `parse_error_count`；
- 如果存在 parse error，则 `semantic_complete=false`；
- 返回 `partial_symbol_results`。

### 7.4 需要修改的文件

- 新增 `src/repo_harness/tools/symbol_index.py`
  - 放 AST 扫描、定义提取、引用候选提取、结果排序。
- `src/repo_harness/tools/minimal.py`
  - 新增 `symbol_search` ToolDefinition。
  - 新增 `_symbol_search()`，调用 `symbol_index.py`。
  - 加入 `DEFAULT_TOOL_ORDER`，建议放在 `grep` 后、`update_working_state` 前。
- `src/repo_harness/permissions/system.py`
  - 增加 `symbol_search.root` 路径检查，复用 `grep.root` 或 `list_files.root` 的规则。
- `src/repo_harness/scaffolds/patch_focused_react.py`
  - 提示模型：当任务涉及 class、function、method、inheritance、call site 时，优先使用 `symbol_search` 缩小定位范围。
- `tests/unit/test_tools.py`
  - 增加定义查找、方法查找、引用候选、parse error 降级、hidden path 不可见测试。
- 可选新增 `tests/unit/test_symbol_index.py`
  - 如果 `symbol_index.py` 逻辑较多，建议单独测试。
- `src/repo_harness/run_metadata/tool_snapshot.py` 和 `tests/unit/test_run_metadata.py`
  - 固定 `symbol_search` 的 input schema、output schema、read-only 标记和可见性策略版本。

### 7.5 验证方式

运行命令：

```bash
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_tools.py tests/unit/test_symbol_index.py
```

targeted smoke 验收标准：

- `014 astroid`、`015 astroid`、`017 astroid` 至少有机会使用 `symbol_search` 定位 class 或 function。
- 如果模型使用 `symbol_search`，后续应更快进入 `read_file` 或 `edit_file`。
- `symbol_search` 不得读取 hidden path，不得把 parse error 伪装成完整结果。

## 8. 统一工具顺序建议

本轮完成后，pre-verl patch-focused tool order 建议为：

```text
list_files
glob_files
read_file
grep
symbol_search
update_working_state
edit_file
git_diff
```

说明：

- `create_file`、`bash`、`run_tests` 仍然由当前 pre-verl policy 控制。formal final-only 模式下，`run_tests` 继续禁用。
- `glob_files` 是 `list_files` 的 alias，不是第二套文件发现系统。
- `symbol_search` 只读、可并发安全，但第一版 agent loop 仍然串行执行工具，避免引入调度变量。
- `update_working_state` 不修改仓库，但会修改会话状态，因此建议 `is_concurrency_safe=False`。
- `edit_file` 继续是非只读、非并发安全工具。

## 9. 本轮总体验证计划

### 9.1 单元测试

每一步完成后运行局部测试，全部完成后运行：

```bash
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_tools.py
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_agent_loop_protocol.py
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_context_manager.py
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_context_builder.py
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_run_metadata.py
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_export.py
```

如果新增 `tests/unit/test_symbol_index.py`：

```bash
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_symbol_index.py
```

### 9.2 targeted smoke

全部五项实现后，重新运行同一组五个 targeted smoke 任务，保持以下变量不变：

- provider；
- model；
- temperature；
- seed；
- max turns；
- max tool calls；
- final verifier mode；
- test feedback policy；
- Docker execution mode。

新的 baseline id 建议包含 `toolcap`，例如：

```text
pre_verl_deepseek_flash_toolcap_v1_targeted_YYYYMMDDTHHMMSSZ
```

### 9.3 targeted smoke 验收指标

必须检查：

1. 五个 run 的 `inspect-model-visible-context` 仍然全部通过。
2. `inspect-pre-verl-agentloop-boundary-index` 仍然通过。
3. 首轮 `repository_action_index` 仍然非空，且不泄漏 hidden material。
4. 成功 `edit_file` 之前必须存在同路径 `read_file` 或正确 `expected_content_hash`。
5. `glob_files` 和 `symbol_search` 不绕过模型可见性策略。
6. `update_working_state` 不把 hidden material 写入 prepared messages。
7. 如果 `014 astroid` 仍然 `max_turns`，必须能看到 working state 或 symbol navigation 是否被模型使用；如果模型完全不用这些工具，应把它归类为模型未采用可用工具，而不是 Harness 没提供能力。
8. `001`、`015` 的失败如果仍是 rejected，应检查补丁是否更早生成、是否更局部、是否因为模型修错逻辑，而不是因为无法定位或无法编辑。

### 9.3.1 自动化 inspect 入口

上述 targeted smoke 验收不能只靠人工读日志。建议新增一个专用 inspect 命令，或者扩展现有 `inspect-model-visible-context`。

推荐新增命令：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-pre-verl-tool-capabilities RUN_DIR \
  --assert-edit-read-before-write \
  --assert-new-tools-model-visible \
  --assert-tool-capability-results-recoverable \
  --assert-working-state-no-hidden-material \
  --assert-symbol-search-visible-only
```

命令应检查：

- 每个成功 `edit_file` 之前，同一路径存在 `read_file` 或正确 `expected_content_hash`。
- `glob_files`、`update_working_state`、`symbol_search` 出现在 prepared tool definitions 中。
- `glob_files` 和 `symbol_search` 结果不包含 hidden path、selector 文件、gold patch 或 hidden test 名称。
- `update_working_state` 的模型可见内容不包含 hidden material。
- 新增工具结果包含 `result_envelope`，且 recovery call 可以被 `inspect-model-visible-context --assert-tool-results-recoverable` 识别。

对应测试：

```bash
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_pre_verl_agentloop.py
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_run_metadata.py
```

### 9.4 建议记录的对比指标

和 `20260508T105300Z` targeted smoke 对比：

| 指标 | 期望变化 |
| --- | --- |
| `014 first_edit` | 从 `None` 变成具体轮次，或者至少出现 `update_working_state` 后更明确的候选文件 |
| `001 first_edit` | 尽量早于第 24 轮 |
| `015 first_edit` | 尽量早于第 14 轮 |
| `017 accepted` | 不应回退 |
| `020 accepted` | 不应回退 |
| 成功 edit 前 read/hash 覆盖率 | 100% |
| 重复 grep / read_file 次数 | 下降 |
| `symbol_search` 使用后到 `read_file` 的距离 | 尽量小于 2 轮 |

## 10. 风险和回滚边界

### 10.1 最大风险

一次性加入五项能力会改变模型工具选择分布。即使每个工具本身正确，模型也可能因为工具更多而多探索，导致回合预算增加。

缓解方式：

- patch-focused scaffold prompt 必须明确工具使用顺序；
- `update_working_state` 不应鼓励长篇计划；
- `symbol_search` 输出必须短，默认 `max_results=20`；
- `glob_files` 只是 alias，不增加新的文件发现语义；
- `edit_file` 的拒绝信息必须直接给 recovery call，避免模型被拒绝后不知道下一步。

### 10.2 不建议本轮同时做的事情

本轮不要同时实现只读工具并发执行。原因是并发会改变工具结果时序，让本轮很难判断行为变化来自新工具能力还是调度模式。当前仍建议保持 `serial_v0`。

本轮也不要接入完整语言服务器。第一版符号导航只做 Python AST-based 工具，避免把工程范围扩大到多语言索引、依赖环境和缓存失效。

### 10.3 回滚边界

如果 targeted smoke 明显变差，按以下顺序排查和回滚：

1. 先检查 scaffold prompt 是否让模型过度使用 `update_working_state`。
2. 再检查 `symbol_search` 是否返回太多结果或误导候选路径。
3. 再检查 `edit_file` 强约束是否导致模型被拒绝后没有恢复。
4. 最后才考虑关闭 `glob_files` alias，因为它只是 `list_files` 包装，风险最低。

建议每个新能力都有单独 policy version 或 feature flag，便于只关闭某一项，而不是整批回滚。

## 11. 完成定义

本轮五项能力可以认为完成，需要同时满足：

1. 新工具和新返回语义全部有单元测试。
2. 核心单元测试和 `compileall` 通过。
3. 五题 targeted smoke 可以正常 prepared and executed。
4. 五个 run 的模型可见上下文 inspect 全部通过。
5. 成功编辑都满足 read-before-edit 或 hash 约束。
6. `glob_files`、`update_working_state`、`symbol_search` 至少在 fake provider 或 targeted smoke 中各有一条真实工具调用证据。
7. `017` 和 `020` 不应因为新工具能力回退到 Harness 错误；如果模型结果回退，必须能从轨迹解释是模型工具选择或补丁逻辑问题。

完成后，再决定是否启动正式二十三题评测。不要在五项能力只完成一部分时启动正式评测，否则新的 baseline 会混合“旧工具链”和“新工具链”，不利于简历展示和可靠性归因。
