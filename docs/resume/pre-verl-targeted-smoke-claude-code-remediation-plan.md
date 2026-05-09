# Pre-verl Targeted Smoke 暴露的 AgentLoop 深层修复计划

更新时间：2026-05-08

状态：正式二十三题新基线前建议完成的第二轮 Harness 修复计划。本文是对 `docs/resume/pre-verl-agentloop-tool-context-convergence-improvement-plan.md` 的补充和升级，不替代原文中已经完成或已经设计的 provider retry、搜索结果语义、初始上下文绑定和 no-progress 诊断内容。

## 1. 结论

最新 targeted smoke 说明，当前 RepoHarness 的可靠性 hardening 已经明显进步：provider retry、final verifier boundary、模型可见上下文检查、hidden material 防泄漏、失败归因等关键审计链路已经可以支撑继续分析。

但是从“帮助模型完成真实软件工程任务”的角度看，当前 Harness 仍然存在第二层问题：

1. 搜索工具仍可能给出错误事实，尤其是在 Docker execution mode 下，`grep`、`list_files`、`read_file` 和模型可见路径判断可能不完全共享同一个 workspace backend 语义，导致模型相信某个符号不存在。
2. 初始上下文虽然已经绑定了 `repository_context_index` artifact，但模型看到的仍主要是 artifact reference、hash 和空的候选入口列表，不是可以直接行动的源码入口。
3. no-progress 诊断已经能发现“连续只读、重复搜索、临近预算但无补丁”，但诊断结果没有进入模型可见消息，模型不会因此改变策略。
4. RepoHarness 已经有 `ContentReplacementState` 和 deterministic tool result replacement，但当前 replacement 仍不足以阻止 `020 pydicom` 这类长只读轨迹触发 `context_limit`；问题不是“完全没有压缩”，而是现有压缩策略、阈值接线、replacement 预算和诊断还不够。
5. `context_limit` 的停止判断依赖内部字符估算，可能把 provider 实际不会接收的内部 typed 字段、artifact refs、normalized arguments 等也算入预算。后续需要区分内部估算和 provider-ready body 估算。
6. 工具系统已有 `list_files` 的 glob 能力，但工具说明、结果格式、路径恢复和 `grep output_mode` 还没有形成 Claude Code `GlobTool`/`GrepTool` 那样的“先文件发现，再内容搜索，再窄范围读取”的工作流。

因此，不能把 targeted smoke 中的失败简单解释为模型能力不足。更准确的判断是：模型本身在 SWE-Bench-like 任务上的定位和补丁决策能力偏弱，而 Harness 当前没有足够及时地纠偏，放大了模型弱点。

本文建议在下一轮正式二十三题新基线前，先完成一轮“搜索事实可信协议、可行动初始上下文、模型可见收敛提醒、现有 deterministic replacement 增强、provider-ready token estimate 和工具恢复提示”的深层修复。

## 2. 证据范围

本文使用以下本地证据和参考实现：

1. 最新 targeted smoke 目录：`runs/pre-verl-agentloop-targeted-smoke-deepseek-flash-tool-context-convergence-20260508T055743Z`。
2. Targeted smoke 任务集合：
   - `pre_verl_dev_001_sqlfluff__sqlfluff_1625`
   - `pre_verl_dev_014_pylint_dev__astroid_1333`
   - `pre_verl_dev_015_pylint_dev__astroid_1196`
   - `pre_verl_dev_017_pylint_dev__astroid_1268`
   - `pre_verl_dev_020_pydicom__pydicom_1413`
3. RepoHarness 当前实现：
   - `src/repo_harness/agent_loop/loop.py`
   - `src/repo_harness/context/builder.py`
   - `src/repo_harness/context/manager.py`
   - `src/repo_harness/evaluation/runner.py`
   - `src/repo_harness/tools/minimal.py`
   - `src/repo_harness/pre_verl_agentloop.py`
4. Claude Code TypeScript 参考实现：
   - `reference/claude-code-typescript-src/AGENTS.md`
   - `reference/claude-code-typescript-src/query.ts`
   - `reference/claude-code-typescript-src/query/tokenBudget.ts`
   - `reference/claude-code-typescript-src/query/stopHooks.ts`
   - `reference/claude-code-typescript-src/tools/GrepTool/GrepTool.ts`
   - `reference/claude-code-typescript-src/tools/GlobTool/GlobTool.ts`
   - `reference/claude-code-typescript-src/services/tools/toolOrchestration.ts`

注意：Claude Code 是面向真实用户交互的产品。RepoHarness 是面向评测、审计和训练数据导出的 Harness。本文只借鉴 Claude Code 的工程不变量，不照搬产品形态、界面交互、账户能力、记忆系统或完整 hook 生态。

## 3. Targeted smoke 逐题摘要

| 任务 | 结果 | 工具行为 | 首次编辑 | 初步归因 |
| --- | --- | --- | ---: | --- |
| `001 sqlfluff_1625` | `max_turns`，空补丁，final verifier 未执行 | `grep` 28 次，`read_file` 13 次，`list_files` 7 次 | 无 | 模型第 10 轮已读到相关 `L031.py`，但没有进入编辑；Harness 没有模型可见收敛提醒 |
| `014 astroid_1333` | `max_turns`，空补丁，final verifier 未执行 | `read_file` 31 次，`grep` 19 次，`list_files` 2 次 | 无 | 模型长时间在 import 和 modpath 逻辑中游走，没有形成补丁；Harness 只记录无进展，不纠偏 |
| `015 astroid_1196` | `max_turns`，空补丁，final verifier 未执行 | `read_file` 30 次，`grep` 19 次，`list_files` 2 次 | 无 | 模型后期已读到 `Dict.getitem()` 附近关键代码，但仍未编辑 |
| `017 astroid_1268` | 有补丁，但 final verifier rejected | `read_file` 26 次，`grep` 22 次，`edit_file` 1 次 | 第 48 轮 | 模型方向接近，补了 `visit_unknown()`，但返回值错误；编辑发生太晚，没有迭代空间 |
| `020 pydicom_1413` | `context_limit`，空补丁，final verifier 未执行 | `grep` 25 次，`read_file` 24 次，`list_files` 7 次 | 无 | 搜索工具疑似给出 `MultiValue` 假阴性，随后大量读取导致上下文超限 |

这些结果说明，当前失败有三类：

1. 模型策略问题：模型长期只读探索，已经读到相关代码但不敢编辑。
2. Harness 搜索问题：工具可能返回错误的完整无匹配结果。
3. Harness 控制问题：即使系统已经识别无进展或上下文风险，也没有把风险作为模型可见控制信号回流。

## 4. 与原改进计划的关系

原计划 `pre-verl-agentloop-tool-context-convergence-improvement-plan.md` 的方向是正确的，主要覆盖了以下第一层问题：

1. Provider retry 和 baseline 身份冻结。
2. `grep` 结果拆分为 `complete_no_match`、`partial_scan_no_match`、`result_page_truncated` 等状态。
3. 首轮 `prepared_messages` 绑定 `repository_context_index`。
4. no-progress 诊断进入 events 和 metrics。
5. freeze manifest 记录搜索语义、初始上下文、loop progress policy 等版本。

Targeted smoke 之后需要升级的原因是：这些机制多数还停留在“可审计”和“可记录”层面，没有充分进入“可行动”和“可纠偏”层面。

具体差异如下：

| 原计划已经覆盖 | Targeted smoke 后发现仍不足 | 需要补充 |
| --- | --- | --- |
| 搜索结果有 `result_kind` 和 `scan_complete` | `020 pydicom` 出现 `grep MultiValue` 完整无匹配，但源码实际存在命中；`list_files` 和 `_model_visible_path_status()` 也共享同一可见性风险 | 升级为“搜索事实可信协议”，覆盖 `grep`、`list_files`、读取错误、可见性错误和 backend mismatch |
| 首轮上下文包含 `repository_context_index` | 模型看到的是 artifact ref、hash 和空候选列表，不是候选源码入口 | 直接注入安全、确定性、可行动的 candidate source entries |
| no-progress 被记录为事件 | `model_visible_message_injected=false`，模型看不到提醒 | 增加模型可见收敛提醒，第一版不 hard stop |
| 已有 `ContentReplacementState` 和 deterministic replacement | `020 pydicom` 第 46 轮前已经发生大量 replacement，但仍然超过上下文预算 | 增强现有 replacement 策略，而不是从零实现压缩 |
| `token_estimate` 有简单字符估算 | 内部消息对象估算可能高于真实 provider body，导致提前 `context_limit` | 增加 `provider_ready_token_estimate` 和 estimator error diagnostics |
| `list_files` 支持 glob，`grep` 支持 root、glob、mode | 模型仍用 `grep` 做路径发现，且路径错误恢复弱 | 优先强化 `list_files` 文件发现语义，可选增加 `glob_files` 兼容层，并给 `grep` 增加 `output_mode` |

## 5. Claude Code 参考设计中值得借鉴的不变量

### 5.1 搜索工具基于统一工作目录和成熟搜索引擎

Claude Code 的 `GrepTool` 使用 ripgrep，在同一个工作目录下执行搜索。它支持 `path`、`glob`、`output_mode`、`head_limit`、`offset`、`type`、`context` 等参数。搜索超时或失败会作为工具错误反馈给模型，而不是伪装成完整无匹配。

RepoHarness 当前 `read_file` 通过 workspace adapter 读取文件，而 `grep` 的 `_read_model_visible_text_for_grep` 直接用本地 `Path(...).read_text()` 读取路径。与此同时，`_model_visible_path_status()` 中也包含 host path 上的符号链接判断，`list_files` 和 `grep` 都依赖这个可见性判断。对于 local execution mode 这通常没有问题，但 Docker execution mode 下可能出现工具可见路径、host symlink 状态和真实容器工作区不一致，导致搜索结果错误。

可借鉴的不变量：所有模型可见文件发现、路径可见性判断和文件读取工具必须共享同一个 workspace backend 语义。`grep`、`read_file`、`list_files` 不能各自绕过 workspace adapter 读不同的文件视图，也不能把 backend mismatch、read error 或 visibility error 伪装成完整无匹配。

### 5.2 文件发现和内容搜索是两个不同工具职责

Claude Code 有 `GlobTool` 专门按文件名模式找文件，有 `GrepTool` 专门按内容搜索。`GrepTool` 默认可以只返回 files-with-matches，避免一开始就把大量匹配内容塞进上下文。

RepoHarness 当前主要依赖 `list_files` 和 `grep`。需要注意的是，`list_files` 已经支持 `glob` 和 `pattern`，所以短期问题不是“没有文件发现能力”，而是工具名、提示词、结果格式和恢复建议没有把模型稳定引导到“先用 `list_files` 做文件发现，再用 `grep` 做内容搜索”的流程。模型经常用 `grep` 承担文件发现职责，这会导致宽泛搜索、空结果、分页、上下文膨胀混在一起。

可借鉴的不变量：先用文件发现缩小候选范围，再用内容搜索定位符号，最后用 `read_file` 读取小范围上下文。

### 5.3 预算和继续策略必须变成模型可见控制信号

Claude Code 在 query loop 中会检查 token budget。如果还可以继续但接近预算，会构造一个 meta user message，把预算状态和继续建议放回下一轮输入。它还支持 stop hooks 在继续前阻断或追加上下文。

RepoHarness 当前已经能检测 no-progress，但 `model_visible_message_injected` 固定为 `false`。这说明 Harness 知道模型在无效探索，但模型不知道 Harness 知道。

可借鉴的不变量：当系统判断模型正在消耗预算但没有产生进展时，应该给模型一个可见、可审计、非 oracle 的控制消息。

### 5.4 现有 deterministic replacement 需要成为真实预算治理，而不是只做后验替换

Claude Code 在调用模型前会执行多层上下文治理，包括 tool result budget、snip、micro compact、context collapse 和 auto compact。RepoHarness 不需要完整复刻，而且 RepoHarness 已经有 `ContentReplacementState` 和 deterministic preview replacement。当前真正的问题是：已有 replacement 没有充分接入 `compact_threshold_ratio`、上下文临界 warning、provider-ready token estimate、重复空搜索优先替换、大文件读取保护和“压缩后仍不足”的诊断。

可借鉴的不变量：上下文治理应该发生在撞上 hard context limit 之前，并且要保留任务、最近对话、补丁状态、文件 hash 和可恢复调用建议。如果已经执行过 replacement 但仍然超限，final diagnostics 必须明确记录“压缩已执行但不足”，而不是只写普通 `context_limit`。

## 6. 问题一：搜索事实可信协议不足

### 6.1 当前问题

在 `pre_verl_dev_020_pydicom__pydicom_1413` 中，模型第 1、4、5、6 轮多次搜索 `MultiValue`。工具返回类似：

```text
No matches found after scanning all 312 model-visible files under root='pydicom'.
```

但同一 run 的后续 `read_file` 结果中存在：

```python
from pydicom.multival import MultiValue
```

本地只读搜索也能在以下文件中找到 `MultiValue`：

1. `pydicom/filewriter.py`
2. `pydicom/dataelem.py`
3. `pydicom/valuerep.py`
4. `pydicom/multival.py`
5. `pydicom/tests/test_multival.py`

这说明模型看到的搜索结果很可能是错误事实。错误事实比“不够详细的提示”更严重，因为模型会基于错误事实排除正确方向。

这个问题不能只理解为“把 `grep` 的读取函数从 `Path(...).read_text()` 换成 workspace adapter”。当前风险至少有三层：

1. `grep` 枚举文件使用 `workspace_adapter.list_files()`，但读取内容走本地 host path。
2. `grep` 和 `list_files` 都调用 `_model_visible_path_status()`，而该函数中包含 host path 的符号链接判断；Docker execution mode 下 host path 的 symlink 状态不一定等价于容器内真实工作区。
3. `list_files` 当前会把非 symlink 的可见性失败混入 `skipped_hidden_count`，模型和 inspect 很难区分“真实被隐藏策略排除”和“workspace backend 或路径可见性判断异常”。

因此，下一轮修复应升级为“搜索事实可信协议”：任何模型可见搜索或文件发现结果，都必须说明它的事实来源、backend、扫描完整性、读取错误、可见性错误和不完整原因。

### 6.2 影响模型的方式

模型看到“完整扫描后无匹配”后，会合理地相信：

1. `MultiValue` 不在源码中。
2. 问题可能不在 value conversion 或 filewriter 相关逻辑。
3. 需要继续搜索 `OL`、`add_new`、`bytes-like object` 或其他线索。

这会直接造成定位发散。`020 pydicom` 最终 46 轮上下文超限，和早期错误搜索反馈高度相关。

### 6.3 修复计划

第一步：统一搜索、文件发现和可见性判断的 workspace backend。

当前 `_read_model_visible_text_for_grep` 应改为通过 `context.workspace_adapter.read_text(...)` 读取，而不是直接 `Path(...).read_text()`。

建议改造前：

```python
workspace = Path(context.run_workspace.workspace_path).resolve()
candidate = (workspace / rel_path).resolve()
return candidate.read_text(encoding="utf-8")
```

建议改造后：

```python
return context.workspace_adapter.read_text(
    context.run_workspace.workspace_path,
    rel_path,
)
```

同时，`_model_visible_path_status()` 也要尽量走 workspace adapter 提供的路径解析和 symlink 策略；如果必须使用 host path 辅助判断，必须把这个事实写入 typed result，例如 `visibility_backend="host_path_plus_workspace_adapter"`，不能默默混用。

第二步：在 `grep` 和 `list_files` typed result 中记录搜索事实可信字段。

建议新增字段：

```json
{
  "root": "pydicom",
  "search_backend": "workspace_adapter",
  "workspace_execution_mode": "docker",
  "read_error_count": 0,
  "read_error_samples": [],
  "visibility_error_count": 0,
  "visibility_error_samples": [],
  "scan_complete_reason": "all_candidates_scanned_and_readable",
  "backend_mismatch_detected": false,
  "search_fact_policy_version": "repo_harness_search_fact_trust_v1"
}
```

第三步：任何读取失败、可见性判断失败或 backend mismatch 都不能返回 `complete_no_match`。

例如扫描了 312 个候选文件，其中 20 个读取失败，即使剩余 292 个文件无匹配，也应该返回：

```json
{
  "result_kind": "incomplete_scan_no_match",
  "scan_complete": false,
  "read_error_count": 20,
  "visibility_error_count": 0,
  "scan_complete_reason": "read_errors_prevent_complete_search_fact"
}
```

模型可见文本应写成：

```text
No matches were found in the readable subset, but 20 candidate files could not be read through the workspace backend. Do not conclude the query is absent.
```

如果是可见性判断异常，应返回：

```json
{
  "result_kind": "incomplete_scan_no_match",
  "scan_complete": false,
  "visibility_error_count": 3,
  "scan_complete_reason": "visibility_errors_prevent_complete_search_fact"
}
```

第四步：`list_files` 也纳入搜索事实可信协议。

`list_files` 的 typed result 需要区分：

1. `hidden_path_count`：被模型可见性策略明确排除。
2. `symlink_outside_workspace_count`：符号链接越界。
3. `workspace_boundary_or_missing_count`：路径不存在、路径越界或 workspace backend 无法解析。
4. `visibility_error_count`：可见性判断异常或 host/backend 不一致。
5. `scan_complete_reason`：例如 `all_entries_classified`、`visibility_errors_present`、`page_truncated`。

验收标准中必须明确：被模型可见性策略确定排除的 hidden path 不等于 scan incomplete。只有 read error、backend mismatch、未分类路径或 visibility error 才会阻止 `complete_no_match` 成为可信事实。换句话说，如果所有候选路径都被成功分类，其中一部分被策略明确排除，剩余可见路径也都成功读取，那么可以返回可信的完整扫描结果；如果任何路径无法分类或读取失败，就必须降级为 incomplete。

模型可见文本不能把这些都写成“hidden/skipped”。例如：

```text
Returned 100 model-visible files, but 3 candidate paths could not be classified by the workspace backend. Do not treat this listing as a complete repository fact.
```

第五步：优先使用 ripgrep 或后端原生搜索能力。

短期可以继续 Python fallback，但必须保证后端一致。中期可以增加 `grep_engine="ripgrep_v1"`，在 local 和 Docker backend 中都通过同一 workspace adapter 执行受控搜索。

### 6.4 验证方式

新增单元测试：

1. `tests/unit/test_tools.py`：构造 fake workspace adapter，确保 `grep` 调用 adapter 的 `read_text`，而不是直接读本地路径。
2. `tests/unit/test_tools.py`：当部分文件读取失败时，断言 `scan_complete=false`，不能返回 `complete_no_match`。
3. `tests/unit/test_tools.py`：`pattern` alias 和 `query` 在 Docker-like fake adapter 中行为一致。
4. `tests/unit/test_tools.py`：当 `_model_visible_path_status()` 无法通过 workspace adapter 确认路径可见性时，`grep` 和 `list_files` 都必须记录 `visibility_error_count`，不能把它混入普通 `skipped_hidden_count`。
5. `tests/unit/test_tools.py`：`list_files` 返回 `scan_complete_reason`，并区分 hidden、symlink、missing、visibility error。

新增集成或 targeted regression：

首选方式是新增一条专门的 Docker integration test，而不是只依赖人工 run 目录检查。建议测试名：

```text
tests/integration/test_pre_verl_search_fact_trust.py::test_pydicom_multivalue_grep_uses_docker_workspace_backend
```

该测试应创建或复用 `pre_verl_dev_020_pydicom__pydicom_1413` 的 Docker workspace，并用 replay 或 mock provider 发出以下工具调用：

```json
{"tool_name": "grep", "arguments": {"pattern": "MultiValue", "path": "pydicom"}}
```

断言工具结果必须包含 `pydicom/multival.py`、`pydicom/filewriter.py`、`pydicom/dataelem.py` 或 `pydicom/valuerep.py` 中至少一个。

如果用 CLI 做人工 targeted regression，必须使用当前 `repo-harness run-task` 的真实参数形态：任务 YAML 是位置参数，run config 通过 `--config` 传入。命令形态如下：

```bash
PATH=.venv/bin:$PATH repo-harness run-task \
  runs/pre-verl-agentloop-targeted-smoke-deepseek-flash-tool-context-convergence-20260508T055743Z/task_definitions/pre_verl_dev_020_pydicom__pydicom_1413.yaml \
  --config /tmp/pre_verl_pydicom_multivalue_grep_replay_run_config.yaml \
  --output-dir /tmp/repo-harness-pydicom-grep-backend-regression \
  --run-id pre_verl_pydicom_multivalue_grep_backend_regression
```

其中 `/tmp/pre_verl_pydicom_multivalue_grep_replay_run_config.yaml` 必须是显式配置 Docker execution mode 和 replay 或 mock provider 的 run config，不能临时改用真实 provider 作为这个搜索事实可信回归的唯一证据。

新增 inspect 断言：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-model-visible-context RUN_DIR \
  --assert-tool-results-recoverable \
  --assert-search-facts-trustworthy
```

如果暂时不新增命令参数，也要在 targeted smoke 后用脚本检查所有 `grep_results.json`：

1. `search_backend` 或 `search_fact_policy_version` 存在且不为 `unknown`。
2. `scan_complete=true` 时 `read_error_count=0`。
3. `scan_complete=true` 时 `visibility_error_count=0`。
4. `complete_no_match` 不能与后续同一 workspace 中的 `read_file` 明显矛盾。
5. 所有 `list_files` result 都能解释 `skipped_hidden_count`、`skipped_symlink_count`、`workspace_boundary_or_missing_count` 和 `visibility_error_count`。

## 7. 问题二：初始上下文绑定了 artifact，但没有给模型可行动入口

### 7.1 当前问题

当前首轮 `prepared_messages` 中已经包含 `repository_context_index`，但内容主要是：

```json
{
  "candidate_source_entries": [],
  "candidate_source_entry_count": 0,
  "repo_context_index_ref": {
    "relative_path": "artifacts/...repo_context_index.json",
    "sha256": "..."
  },
  "usage_hint": "Use repository_context, expected_files, candidate_source_entries, list_files, grep, and read_file..."
}
```

这对审计者有价值，但对模型帮助有限。模型不能通过普通工具读取 artifact ref，也不能直接从空的 `candidate_source_entries` 得到候选源码入口。

### 7.2 影响模型的方式

在 `001 sqlfluff`、`014 astroid`、`015 astroid`、`020 pydicom` 中，模型大量消耗轮次做定位。部分任务后期已经读到关键代码，但太晚才到达，或者到达后仍没有决策。

如果首轮上下文直接给出安全的候选入口，例如：

1. `src/sqlfluff/rules/L031.py`
2. `astroid/nodes/node_classes.py`
3. `astroid/nodes/as_string.py`
4. `pydicom/dataelem.py`
5. `pydicom/filewriter.py`

模型不一定能解决问题，但能显著减少前 10 到 20 轮的低效搜索。

### 7.3 修复计划

第一步：区分 artifact-level index 和 model-visible action index，并让每个候选入口证据化。

建议保留当前 `repo_context_index_ref`，但新增一个直接模型可见的 compact field：

```json
{
  "repository_action_index": {
    "schema_version": "repo_harness_repository_action_index_v1",
    "source": "public_issue_and_model_visible_source_index",
    "top_level_directories": ["pydicom", "tests", "doc"],
    "key_config_files": ["setup.cfg", "pyproject.toml"],
    "candidate_source_entries": [
      {
        "path": "pydicom/dataelem.py",
        "evidence_source": "model_visible_issue_text",
        "matched_terms": ["OL", "MultiValue", "add_new"],
        "source_text_span_hash": "sha256-of-public-issue-span",
        "ranking_reason": "issue mentions OL and MultiValue; file shallow index contains DataElement conversion code",
        "policy_version": "repo_harness_repository_action_index_v1"
      },
      {
        "path": "pydicom/filewriter.py",
        "evidence_source": "model_visible_source_shallow_index",
        "matched_terms": ["bytes-like object", "OL"],
        "source_text_span_hash": "sha256-of-public-issue-span",
        "ranking_reason": "issue reports bytes-like object error while saving OL value; file shallow index contains writer functions",
        "policy_version": "repo_harness_repository_action_index_v1"
      },
      {
        "path": "pydicom/multival.py",
        "evidence_source": "model_visible_issue_text",
        "matched_terms": ["MultiValue"],
        "source_text_span_hash": "sha256-of-public-issue-span",
        "ranking_reason": "issue explicitly names MultiValue; path and shallow index match the symbol",
        "policy_version": "repo_harness_repository_action_index_v1"
      }
    ],
    "selection_limit": {
      "max_candidate_entries": 12,
      "max_sample_paths": 40
    },
    "hidden_evaluator_material_excluded": true
  }
}
```

第二步：候选入口只能来自模型可见材料。

允许来源：

1. 公开 issue statement 中直接出现的相对路径。
2. 公开 issue statement 中出现的类名、函数名、错误名、配置键、模块名。
3. 模型可见源码索引中的路径和浅层内容索引。
4. 公开 task metadata 中明确 model-visible 的 `expected_files`。

禁止来源：

1. hidden test patch。
2. fail-to-pass selector。
3. pass-to-pass selector。
4. gold patch。
5. final verifier 原始输出。
6. evaluator-only artifact id 或 sha256。
7. targeted smoke 后验轨迹、人工分析结论或 previous run 中模型读过的文件。即使这些路径看起来合理，也不能用于正式 baseline 的 action index 排名。

第三步：增加确定性 ranking。

建议排序规则：

1. issue 文本中出现完整相对路径的文件排最前。
2. 文件名、类名、函数名或模块名与 issue token 匹配的源码文件次之。
3. 错误堆栈、异常名、VR 名称、规则编号等关键 token 匹配的源码文件再次之。
4. 测试文件可以作为辅助入口，但源码文件优先。
5. 排名必须稳定，不依赖当前文件系统遍历顺序。
6. 每个候选入口必须记录 `evidence_source`、`matched_terms`、`source_text_span_hash`、`ranking_reason`、`policy_version`。如果某个候选入口没有证据字段，inspect 应判定该 action index 不完整。
7. `source_text_span_hash` 只能哈希模型可见 issue span 或模型可见源码浅层索引片段，不能哈希 hidden selector、hidden patch、gold patch 或 final verifier 输出。

第四步：把 `AGENTS.md` 和仓库指令边界继续保留。

当前 `ContextBuilder` 已经支持 `AGENTS.md`。后续要确保：

1. `AGENTS.md` 是不可信仓库上下文，不能覆盖系统安全规则。
2. `AGENTS.md` 预览长度受限。
3. `AGENTS.md` hash 写入 artifact，便于审计。

### 7.4 验证方式

新增测试：

1. `tests/unit/test_context_builder.py`：首轮 messages 包含 `repository_action_index`。
2. `tests/unit/test_context_builder.py`：`candidate_source_entries` 只来自公开 issue 和模型可见源码索引。
3. `tests/unit/test_context_builder.py`：同一 source tree、同一 issue、同一 policy version 下 action index hash 稳定。
4. `tests/unit/test_pre_verl_agentloop.py`：hidden selector、hidden patch、gold patch 中的路径不会进入 `repository_action_index`。
5. `tests/unit/test_context_builder.py`：每个 candidate entry 都有 `evidence_source`、`matched_terms`、`source_text_span_hash`、`ranking_reason` 和 `policy_version`。
6. `tests/unit/test_context_builder.py`：用 targeted smoke 后验轨迹中的已读路径作为输入时，action index builder 不得把后验路径作为候选来源。

Targeted smoke 检查：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-model-visible-context RUN_DIR \
  --assert-no-hidden-test-material \
  --assert-prepared-messages-bound \
  --assert-provider-body-equivalent \
  --assert-initial-action-index-visible
```

手工或脚本检查 5 个 targeted smoke 任务：

1. `001 sqlfluff` 首轮上下文应出现 `L031` 相关候选入口，或至少出现 `src/sqlfluff/rules`。
2. `014 astroid` 首轮上下文应出现 `astroid/modutils.py` 或 import/modpath 相关入口。
3. `015 astroid` 首轮上下文应出现 `astroid/nodes/node_classes.py`。
4. `017 astroid` 首轮上下文应出现 `astroid/nodes/as_string.py`。
5. `020 pydicom` 首轮上下文应出现 `pydicom/dataelem.py`、`pydicom/filewriter.py` 或 `pydicom/multival.py`。

验收目标不是强制模型 accepted，而是确认首轮定位成本下降：

1. 首次读取候选源码文件的轮数下降。
2. 宽泛 `grep root="."` 的次数下降。
3. 空搜索次数下降。
4. 首次编辑轮数提前，或者模型更早给出明确无补丁原因。

## 8. 问题三：no-progress 诊断没有变成模型可见收敛控制

### 8.1 当前问题

`src/repo_harness/agent_loop/loop.py` 已经能构建 no-progress summary，包括：

1. `long_read_only_streak`
2. `repeated_tool_input`
3. `empty_search_accumulation`
4. `near_turn_budget_without_patch`

但是 summary 中固定记录：

```json
{
  "hard_stop_enabled": false,
  "model_visible_message_injected": false
}
```

也就是说，这些诊断只进入 events 和 metrics，不进入下一轮模型输入。

### 8.2 影响模型的方式

在 targeted smoke 中，多个 run 很早就触发了 no-progress 信号：

1. `001 sqlfluff` 第 42 轮时剩余 6 轮，仍然没有补丁。
2. `014 astroid` 第 7 轮已经有 long read-only streak，最后仍然没有补丁。
3. `015 astroid` 第 43 和第 48 轮已经接近关键代码，但没有编辑。
4. `020 pydicom` 第 42 轮时已有 50 多次只读工具调用，仍没有补丁。

如果这些信号只写日志，模型不会知道自己应该切换策略。最终表现就是“工具还没耗尽，但模型调用轮数耗尽”。

### 8.3 修复计划

第一步：新增 `ConvergenceNudgeController`。

建议新增轻量控制器，接收 `_build_loop_progress_summary(...)` 的输出，并决定是否追加模型可见消息。

策略版本：

```text
repo_harness_convergence_nudge_v1
```

建议触发条件：

1. 连续只读工具调用数大于等于 10，且没有成功编辑。
2. 空搜索次数大于等于 4，且最近没有读到新候选文件。
3. 剩余轮数小于等于 6，且 `patch_tool_call_count == 0`。
4. 上下文 token estimate 大于 max context tokens 的 80%，且最近 5 轮主要是 `read_file` 或 `grep`。

第二步：明确插入位置，保证不破坏 tool_use / tool_result 配对。

nudge 必须插入在“一轮所有 `tool_result` 都已经追加完成之后、下一轮 `prepare_messages()` 之前”。不能插入在 assistant tool call 和 tool result 中间，否则会破坏 provider 消息协议中的工具配对，也会污染已经实现的 pre-provider pairing check。

建议主循环顺序：

```text
assistant tool calls -> execute all tool calls -> append all tool results -> record loop_progress_diagnostic -> maybe append convergence nudge user message -> next turn prepare_messages()
```

如果某一轮没有 tool call，而是模型直接 final answer，也不应补插 nudge；nudge 只用于“模型还在探索但没有进展”的下一轮纠偏。

第三步：第一版只注入提醒，不 hard stop。

建议第一版配置：

```json
{
  "convergence_nudge_enabled": true,
  "no_progress_hard_stop_enabled": false,
  "max_nudges_per_run": 2,
  "min_turn_gap_between_nudges": 6
}
```

第四步：提醒内容只描述 loop 行为，不描述隐藏测试。

示例提醒：

```text
Loop progress diagnostic: the last 10 tool actions were read-only and no patch has been created.
Before calling another broad search, summarize the current hypothesis, name the most likely file,
and either make the smallest plausible edit or explain the concrete blocker.
```

临近预算提醒：

```text
Loop budget diagnostic: only 6 turns remain and no patch has been created.
Stop broad repository search. Choose the smallest plausible source change, inspect only the necessary lines,
then use edit_file or explain why no safe patch can be made.
```

上下文临界提醒：

```text
Context budget diagnostic: the conversation is close to the context limit.
Avoid reading large files from the beginning. Use narrow line ranges, summarize your current hypothesis,
and proceed toward a minimal patch.
```

第五步：把提醒写入 messages、events 和 prepared messages artifact，transcript 落地要尊重当前 schema。

建议新增 event：

```json
{
  "event_type": "convergence_nudge_injected",
  "severity": "warning",
  "data": {
    "policy_version": "repo_harness_convergence_nudge_v1",
    "trigger_signal_keys": ["long_read_only_streak"],
    "model_visible": true,
    "contains_evaluator_only_material": false,
    "nudge_message_hash": "..."
  }
}
```

当前 `TranscriptRecord` 是严格 schema，没有 `message_source` 字段。因此第一版不能直接在 transcript record 顶层写：

```json
{"message_source": "harness_convergence_nudge"}
```

有两种安全落地方式：

1. 扩展 `TranscriptRecord` schema，新增 `message_source` 或 `source_type` 字段，并同步更新所有 transcript 读写测试。
2. 不扩展 transcript schema，把来源写入 `convergence_nudge_injected` event 和 nudge artifact metadata；transcript record 只保留当前 schema 允许的字段，并确保 `role="user"`、`model_visible=true`、`trainable=false`、`content_artifact_refs` 指向 nudge artifact。

如果选择不扩展 schema，transcript record 应保持如下形态：

```json
{
  "role": "user",
  "model_visible": true,
  "trainable": false,
  "content_artifact_refs": [
    {
      "kind": "convergence_nudge",
      "relative_path": "artifacts/..._convergence_nudge.json"
    }
  ]
}
```

nudge artifact metadata 中记录：

```json
{
  "kind": "convergence_nudge",
  "policy_version": "repo_harness_convergence_nudge_v1",
  "trigger_signal_keys": ["long_read_only_streak"],
  "dedupe_scope": "analysis_window_after_latest_patch",
  "model_visible": true,
  "trainable": false,
  "contains_evaluator_only_material": false
}
```

### 8.4 验证方式

新增单元测试：

1. 连续 10 次只读工具后，下一轮 `prepared_messages` 中出现 convergence nudge。
2. 已经成功 `edit_file` 后，no-progress 窗口重置，不应继续注入旧提醒。
3. 同一 run 最多注入两次提醒，避免每轮刷屏。
4. 提醒文本不包含 hidden selector、hidden patch、gold patch、final verifier 输出。
5. `loop_diagnostics_summary` 中记录 `convergence_nudge_count`、`last_nudge_turn`、`nudge_policy_version`。
6. 构造 assistant 同时发出多个 tool call 的场景，断言 nudge 只出现在所有 tool result 之后、下一轮 provider request 之前，且 tool_use / tool_result pairing validation 仍然通过。
7. 如果不扩展 `TranscriptRecord` schema，断言 transcript 顶层不写未知字段，来源信息只写在 event 或 artifact metadata 中。

新增集成测试：

1. fake provider 连续重复 `grep`，断言第一个 nudge 注入。
2. fake provider 在 nudge 后调用 `edit_file`，断言 nudge 之后模型可以继续，不触发 hard stop。
3. fake provider 在临近预算时仍无补丁，断言临近预算 nudge 注入。

Targeted smoke 验收：

1. 凡是触发 `long_read_only_streak`、`empty_search_accumulation` 或 `near_turn_budget_without_patch`，且当前 analysis window 中还没有成功 `edit_file` 或 `create_file` 的 run，下一轮 `prepared_messages` 必须出现一条 model-visible、`trainable=false`、来源为 harness 的 convergence nudge。
2. 每个 run 的 nudge 数量必须受 `max_nudges_per_run` 限制；默认最多 2 条，不能每轮重复刷屏。
3. 如果最终仍为空补丁，failure diagnostics 中应能区分：
   - 没有触发 no-progress。
   - 触发 no-progress 但模型没有响应。
   - 模型响应了提醒但补丁仍失败。
4. 首次编辑轮数应作为关键指标记录。`017 astroid` 原来第 48 轮才编辑，修复后目标是明显提前，而不是保证 accepted。

## 9. 问题四：现有 deterministic replacement 不足，且 context_limit 决策源过粗

### 9.1 当前问题

当前主循环在 provider 调用前检查 `prepared.token_estimate > max_context_tokens`。如果超限，直接设置：

```text
agent_stop_reason = context_limit
```

这能保证不会向 provider 发送明显超预算请求，但有两个问题：

1. RepoHarness 并不是完全没有上下文压缩。`ContextManager` 已经有 `ContentReplacementState`、`ContentReplacementRecord` 和 deterministic preview replacement，会把旧 tool result 替换成可恢复摘要。
2. 当前 `token_estimate` 使用 `len(str(prepared_messages)) // 4` 估算，包含内部 dict 表示、typed payload、artifact refs、normalized arguments 等 provider 未必按同样形式接收的内容。这个值被主循环直接用于 `context_limit` hard stop，可能发生内部估算过高导致的提前停止。

`020 pydicom` 是典型例子。第 46 轮前已经替换了大量 tool result，但仍然触发 `context_limit`。运行事件中可以看到 `tokens_after=184098`、`max_context_tokens=180000`，并且 replacement 已经发生。这说明问题不是“从零实现压缩”，而是现有 deterministic replacement 的预算策略、replacement preview 自身大小、阈值接线、重复内容优先级和停止决策源都需要增强。

### 9.2 影响模型的方式

如果现有 replacement 不足，模型会受到三方面影响：

1. 越到后期，provider 输入越长，模型越难从大量旧工具结果中提炼当前假设。
2. replacement 虽然发生了，但如果 replacement 文本本身过长、重复、没有优先替换空搜索或大文件读取，仍然会把上下文推到上限。
3. 一旦内部估算触发 `context_limit`，run 直接停止，模型没有机会利用最后几轮做最小补丁；如果 provider-ready body 实际远小于内部估算，这种停止会误伤模型。

这类失败不能完全归因给模型，因为 Harness 已经知道上下文正在膨胀，却没有把 `compact_threshold_ratio`、provider-ready token estimate、replacement 效果和压缩不足原因形成明确 runtime 决策。

### 9.3 修复计划

第一步：接线现有 `ContextManagementConfig.compact_threshold_ratio`。

配置里已经存在：

```json
{
  "compact_threshold_ratio": 0.85,
  "compact_strategy": "deterministic_preview_replacement"
}
```

后续必须二选一：

1. 真正让 `compact_threshold_ratio` 驱动 context warning、replacement 强度或 critical replacement。
2. 如果短期不接线，就在 manifest 中明确记录 `compact_threshold_ratio_runtime_effect="not_connected"`，不能让正式报告冻结一个看起来有效但实际不参与 runtime decision 的字段。

建议接线方式：

```json
{
  "context_warning_threshold_ratio": 0.8,
  "context_compact_threshold_ratio": 0.85,
  "context_critical_threshold_ratio": 0.9,
  "compact_threshold_runtime_decision_source": "ContextManagementConfig.compact_threshold_ratio"
}
```

第二步：增强现有 deterministic replacement，而不是新增一套平行压缩系统。

增强方向：

1. replacement preview 自身要有最大字符预算，例如每条最多 600 到 1000 字符。
2. 重复空搜索、重复 `complete_no_match`、重复读取同一文件同一行段，应优先进入 replacement。
3. 大文件读取需要保护策略：如果同一文件被从头多次读取，后续 replacement 应保留路径、行段、hash、恢复调用，而不是保留大段 preview。
4. replacement 需要去重：相同 `effective_tool_name + normalized_arguments_sha256 + result_kind` 的旧结果只保留一条代表摘要。
5. replacement 需要冷却时间：刚产生的最近若干轮 tool result 仍然保留，避免模型失去最新上下文。
6. replacement 效果必须记录 `tokens_before`、`tokens_after`、`replacement_count`、`replacement_preview_total_chars` 和 `replacement_effective`。

第三步：增加 context budget warning。

在每轮 `prepare_messages` 后，如果 token estimate 达到阈值但还没有超过硬上限，则注入模型可见提醒。注入提醒后，必须重新执行一次 `prepare_messages()` 或等价的 provider body projection，并重新计算 `provider_ready_token_estimate`、`provider_body_char_estimate` 和 `threshold_decision_source`。不能在已经生成 provider request 之后才把 warning 追加到 canonical messages；否则当前轮模型实际上看不到 warning，审计记录却会误以为 warning 已经生效。

建议阈值：

```json
{
  "context_warning_threshold_ratio": 0.8,
  "context_critical_threshold_ratio": 0.9
}
```

第四步：增加 provider-ready token estimate，避免内部字符估算误杀。

建议 `ContextManager.prepare_messages()` 或 provider request 准备路径同时输出：

```json
{
  "internal_char_estimate": 184098,
  "provider_body_char_estimate": 97321,
  "provider_ready_token_estimate": 24330,
  "provider_returned_prompt_tokens": 25102,
  "estimator_error_ratio": 0.0317,
  "threshold_decision_source": "provider_ready_token_estimate",
  "provider_usage_metadata_status": "available"
}
```

字段含义：

1. `internal_char_estimate`：当前内部 `str(prepared_messages)` 估算，保留用于调试。
2. `provider_body_char_estimate`：把消息投影成真实 provider request body 后的字符估算。
3. `provider_ready_token_estimate`：基于 provider body projection 的 token 估算。
4. `provider_returned_prompt_tokens`：provider 返回 usage 时记录真实 prompt token。
5. `estimator_error_ratio`：有真实 usage 时计算估算误差。
6. `threshold_decision_source`：本轮 hard stop 到底依据内部估算、provider-ready 估算还是 provider metadata。
7. `provider_usage_metadata_status`：如果 provider 没有返回 usage，必须写 `unavailable_provider_metadata`，不能留空。

第五步：在 replacement 仍不足时写明诊断，而不是只写普通 `context_limit`。

如果 replacement 和 warning 都已经执行，但仍然超限，final diagnostics 应记录：

```json
{
  "context_limit_subtype": "compaction_applied_but_insufficient_context_limit",
  "content_replacement_record_count": 50,
  "context_warning_count": 1,
  "provider_ready_token_estimate": 181500,
  "threshold_decision_source": "provider_ready_token_estimate"
}
```

第六步：让 replacement 可恢复。

每个被替换的工具结果继续保留：

1. 原 artifact ref。
2. 工具名。
3. normalized arguments hash。
4. recovery call 建议。
5. 原始内容 hash，若 artifact 为 sensitive 或 evaluator-only 则不能暴露原始 sha256。

第七步：freeze manifest 记录 replacement 和 estimator policy。

新增字段：

```json
{
  "context_replacement_policy_version": "repo_harness_context_replacement_v1",
  "context_warning_threshold_ratio": 0.8,
  "context_compact_threshold_ratio": 0.85,
  "context_critical_threshold_ratio": 0.9,
  "tool_result_replacement_enabled": true,
  "provider_ready_token_estimator_version": "repo_harness_provider_body_estimator_v1",
  "threshold_decision_source_policy": "provider_ready_first_fallback_internal_v1"
}
```

### 9.4 验证方式

新增单元测试：

1. 构造长 `read_file` 历史，确认 context manager 在阈值后增强 replacement，而不是等到 hard limit。
2. replacement 摘要包含文件路径、行段、content hash 和恢复建议。
3. replacement 摘要不包含 hidden selector、hidden patch、gold patch、final verifier 输出。
4. 成功编辑后的 `edit_file` 和 `git_diff` 不被错误替换掉。
5. `compact_threshold_ratio` 参与 runtime decision；如果未接线，manifest 必须显式记录 `compact_threshold_ratio_runtime_effect="not_connected"`。
6. provider-ready body projection 的估算字段存在，且 hard stop 的 `threshold_decision_source` 可追溯。

新增集成测试：

1. fake provider 连续读取大文件，原本会触发 `context_limit`，修复后应先出现 `context_budget_warning` 或 replacement 增强事件。
2. 如果 replacement 后仍然超限，才允许 `agent_stop_reason=context_limit`，并且 final diagnostics 必须写 `compaction_applied_but_insufficient_context_limit`。
3. `inspect-model-visible-context --assert-tool-results-recoverable` 必须覆盖 replacement summary。
4. 构造内部 `len(str(prepared_messages)) // 4` 很高但 provider body projection 较低的场景，断言不会只因为内部估算过高而 hard stop；必须记录 `internal_char_estimate`、`provider_body_char_estimate` 和 `threshold_decision_source`。

Targeted smoke 验收：

1. `020 pydicom` 不应在无任何提醒或 replacement 增强证据的情况下直接撞上 `context_limit`。
2. 如果仍然 context limit，final diagnostics 必须说明已经触发过 warning 或 replacement，并写明是否属于 `compaction_applied_but_insufficient_context_limit`。
3. prepared messages 最大 provider-ready token estimate 应下降，或者至少不再单调无控制增长。
4. 报告中同时记录 `internal_char_estimate`、`provider_body_char_estimate`、`provider_returned_prompt_tokens`、`estimator_error_ratio` 和 `threshold_decision_source`；如果 provider 没有 usage，记录 `unavailable_provider_metadata`。

## 10. 问题五：文件发现工作流和路径错误恢复不足

### 10.1 当前问题

模型会用 `grep` 做文件发现，也会犯可恢复路径错误，例如：

1. `grep root="/"` 触发 workspace boundary 错误。
2. 路径拼写错误时，工具只告诉路径不存在，缺少候选建议。
3. `list_files` 已经支持 `glob` 和 `pattern`，但工具说明、默认 workflow、结果格式和恢复提示没有让模型像使用 Claude Code `GlobTool` 那样先做文件发现。

### 10.2 影响模型的方式

路径错误和工具职责不清会造成两种浪费：

1. 浪费模型调用轮次，因为模型要从错误中自己猜下一步。
2. 浪费上下文，因为宽泛 `grep` 可能返回大量内容或大量空结果。

### 10.3 修复计划

第一步：优先强化现有 `list_files`，可选提供 `glob_files` 兼容层。

短期建议不要把新增 `glob_files` 作为唯一方案，因为 RepoHarness 当前 `list_files` 已经支持 glob 过滤。更稳妥的路径是：

1. 在 `list_files` tool description 中明确写出“用于文件发现，优先在 `grep` 前使用”。
2. 在 `list_files` typed result 中加入 `result_kind`、`scan_complete_reason`、`recommended_next_calls`、路径 typo 建议和 workspace boundary 恢复建议。
3. 在模型可见提示中强调：如果你只知道文件名、模块名或通配符，应先用 `list_files(glob=...)`，再用 `grep(output_mode="files_with_matches")`。
4. 如果为了兼容 Claude Code 心智模型新增 `glob_files`，它应作为 `list_files` 的薄包装或 alias，不能成为另一套独立文件发现实现，避免产生第二套可见性和 backend 语义。

可选 `glob_files` schema：

建议工具 schema：

```json
{
  "name": "glob_files",
  "arguments": {
    "pattern": "**/*dataelem*.py",
    "root": ".",
    "max_entries": 100,
    "offset": 0
  }
}
```

模型可见结果：

```text
Found 3 files matching pattern='**/*dataelem*.py' under root='.'.
pydicom/dataelem.py
pydicom/tests/test_dataelem.py
pydicom/doc/reference/elem.dataelem.rst
```

第二步：给 `grep` 增加 `output_mode`。

建议支持：

1. `files_with_matches`
2. `content`
3. `count`

默认可以考虑 `files_with_matches`，或者在 tool description 中强烈建议模型先用 `files_with_matches` 缩小范围，再用 `read_file`。

第三步：增加路径建议。

对于 workspace boundary：

```text
Path "/" is outside the workspace. Use root="." for repository root, or a repository-relative path such as "src", "pydicom", or "tests".
```

对于拼写错误：

```text
Path "astrid" does not exist. Did you mean "astroid"?
```

路径建议只能来自模型可见文件索引，不能从隐藏材料或 evaluator-only artifact 中派生。

### 10.4 验证方式

新增单元测试：

1. `list_files(glob="**/*dataelem*.py")` 返回稳定、分页、模型可见的文件列表，并带 `result_kind`、`scan_complete_reason` 和 `recommended_next_calls`。
2. 如果实现 `glob_files` 兼容层，`glob_files(pattern="**/*dataelem*.py")` 必须和等价 `list_files(glob="**/*dataelem*.py")` 共享同一 backend 和可见性策略。
3. `grep(output_mode="files_with_matches")` 只返回文件路径，不返回大段内容。
4. `grep root="/"` 返回 workspace boundary 错误和可执行恢复建议。
5. 路径 typo 返回候选建议，建议来源只包含模型可见路径。

Targeted smoke 观察指标：

1. 宽泛 `grep root="."` 次数下降。
2. `list_files(glob=...)` 或兼容 `glob_files` 的使用更集中在前几轮。
3. `read_file` 平均读取行数下降。
4. 路径错误恢复后，模型下一轮能使用建议路径。

## 11. 问题六：failure taxonomy 还需要表达搜索、收敛、压缩和 final-only 子类

### 11.1 当前问题

当前空补丁常被归为：

```text
budget_exhausted_empty_patch
```

这个分类对最终结果是正确的，但粒度不足。它无法区分：

1. 模型完全没有看到任何收敛提醒。
2. Harness 已经提示收敛，但模型继续空搜。
3. 模型响应了提醒并编辑，但补丁错误。
4. Harness 工具给了错误事实，导致模型走偏。
5. 现有 replacement 已经执行但仍不足以避免 `context_limit`。
6. final-only 评测没有中间可见反馈，模型最后一轮才编辑，导致没有迭代空间。

### 11.2 修复计划

在不改变 final verifier 接受标准的前提下，增加诊断字段：

```json
{
  "failure_diagnostics": {
    "failure_category": "model_failure",
    "failure_type": "budget_exhausted_empty_patch",
    "loop_progress_subtype": "nudge_ignored_empty_patch",
    "convergence_nudge_count": 2,
    "model_acted_after_last_nudge": false,
    "search_backend_anomaly_detected": true,
    "context_replacement_applied": true,
    "context_limit_subtype": "compaction_applied_but_insufficient_context_limit",
    "final_only_feedback_subtype": "final_only_no_intermediate_feedback"
  }
}
```

注意：这不是降低 verifier 标准，也不是把模型失败改成 Harness 成功。它只是让后续训练样本分析更清楚。

建议补充的诊断子类：

1. `search_backend_false_fact_suspected`：只能由可审计异常触发，例如 backend mismatch、read error、visibility error，或者公开源码复核命中；不能靠 hidden tests、gold patch 或人工后验答案触发。
2. `no_nudge_empty_patch`：没有触发 convergence nudge，最终空补丁。
3. `nudge_ignored_empty_patch`：触发 nudge 后模型仍继续只读或空搜，最终空补丁。
4. `compaction_applied_but_insufficient_context_limit`：ContentReplacementState 已经执行 replacement，但 provider-ready 或内部阈值仍然超限。
5. `final_only_no_intermediate_feedback`：正式 final-only 模式没有可见测试反馈，模型补丁无法迭代。
6. `model_wrong_fix_after_late_edit`：模型很晚才首次编辑，final verifier rejected；例如 `017 astroid` 第 48 轮才编辑且补丁语义错误。

### 11.3 验证方式

新增测试：

1. 空补丁且没有 nudge：`loop_progress_subtype=no_nudge_empty_patch`。
2. 空补丁且 nudge 后继续只读：`loop_progress_subtype=nudge_ignored_empty_patch`。
3. nudge 后有编辑但 verifier rejected：仍然是 `model_wrong_fix`，并记录 `nudge_before_first_edit=true`。
4. 搜索后端异常时，run metadata 和 final boundary details 记录 `search_backend_anomaly_detected=true` 和 `loop_progress_subtype=search_backend_false_fact_suspected`，但不直接把 accepted/rejected 改写。
5. replacement 已执行但仍 context limit：记录 `context_limit_subtype=compaction_applied_but_insufficient_context_limit`。
6. final-only 且无 public feedback：记录 `final_only_feedback_subtype=final_only_no_intermediate_feedback`。
7. late edit rejected：记录 `model_wrong_fix_after_late_edit`，但仍保持 final verifier 的 `failure_owner=model_wrong_fix`。

## 12. 推荐实施顺序

### Stage F0：最小前置冻结和 inspect 门槛

目标：任何会改变模型输入、工具反馈、loop 控制或上下文估算的修复，在进入 targeted smoke 或正式新基线前，都必须先有最小可追溯身份。这个阶段不能过重，否则会阻塞最紧急的 `grep` 搜索假阴性修复；完整 export audit 和 run matrix 扩展放到 Stage F。

必须完成：

1. 新 targeted smoke 必须生成新的 `baseline_id`，旧探索性 run 只能写入 `baseline_lineage`，不能进入指标分母或分子。
2. configuration manifest、run config facts 或等价最小 freeze 文件必须写入以下字段：
   - `search_fact_policy_version`
   - `tool_schema_snapshot_hash`
   - `model_visible_initial_context_hash`
   - `context_estimator_policy_version`
   - `provider_ready_token_estimator_version`
   - `run_config_hash`
   - `code_commit_hash` 或 dirty worktree policy
3. 如果某个后续 Stage 尚未启用，也要明确写 `disabled` 或 `not_connected`，例如：
   - `repository_action_index_policy_version="disabled"`
   - `convergence_nudge_policy_version="disabled"`
   - `context_replacement_policy_version="repo_harness_context_policy_v0"`
   - `compact_threshold_ratio_runtime_effect="not_connected"` 或实际接线版本
4. `inspect-model-visible-context` 或最小脚本必须能检查新增模型可见字段没有 hidden selector、hidden patch、gold patch、final verifier 原始输出或 evaluator-only artifact hash。

验收要求：

```bash
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_pre_verl_agentloop_scheduler.py tests/unit/test_pre_verl_agentloop.py
PATH=.venv/bin:$PATH repo-harness inspect-model-visible-context RUN_DIR \
  --assert-no-hidden-test-material \
  --assert-prepared-messages-bound \
  --assert-provider-body-equivalent \
  --assert-tool-results-recoverable
```

如果 `RUN_DIR` 尚未产生，可以先用 mock run 目录验证 inspect gate 的字段检查逻辑。Stage A 到 Stage D 的任何真实 targeted smoke 都必须在 Stage F0 完成后运行。

### Stage A：先修搜索事实可信协议

目标：消除 `grep` 和 `list_files` 给模型错误事实的风险。

必须完成：

1. `grep` 使用 workspace adapter 或同一 Docker workspace backend 读取文件。
2. Docker execution mode 下补 `MultiValue` 搜索回归。
3. `complete_no_match` 必须保证所有候选文件都成功读取，或者明确记录不可读文件导致扫描不完整。
4. 所有 `grep_results.json` 记录 `root`、`search_backend`、`workspace_execution_mode`、`read_error_count`、`read_error_samples`、`visibility_error_count`、`visibility_error_samples`、`scan_complete_reason`。
5. `list_files` 也记录同一组搜索事实可信字段，至少包含 `scan_complete_reason`、`visibility_error_count` 和区分后的 skip counters。

验收命令：

```bash
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_tools.py
PATH=.venv/bin:$PATH python -m pytest -q tests/integration/test_pre_verl_agentloop_runtime.py
PATH=.venv/bin:$PATH python -m pytest -q tests/integration/test_pre_verl_search_fact_trust.py
```

### Stage B：增强可行动初始上下文

目标：让模型首轮就看到安全、确定性、可行动的候选源码入口。

必须完成：

1. 新增 `repository_action_index`。
2. `candidate_source_entries` 来自公开 issue 和模型可见源码索引。
3. 5 个 targeted smoke 任务的首轮上下文都能给出合理候选入口。
4. inspect 检查新增字段没有 hidden material 泄漏。
5. 每个 candidate entry 都带 `evidence_source`、`matched_terms`、`source_text_span_hash`、`ranking_reason`、`policy_version`，并禁止 targeted smoke 后验轨迹来源。

验收命令：

```bash
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_context_builder.py tests/unit/test_pre_verl_agentloop.py
```

### Stage C：启用模型可见收敛提醒

目标：把 no-progress 从“审计日志”升级为“可见纠偏信号”。

必须完成：

1. 新增 convergence nudge policy。
2. 第一版不 hard stop。
3. nudge 只能插入在一轮所有 tool results 追加完成之后、下一轮 `prepare_messages()` 之前。
4. nudge 写入 messages、events、prepared messages artifact；如果不扩展 `TranscriptRecord` schema，来源只能写在 event 或 artifact metadata，不能写 transcript 顶层未知字段。
5. freeze manifest 记录 `convergence_nudge_policy_version`。

验收命令：

```bash
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_agent_loop_protocol.py tests/integration/test_pre_verl_agentloop_runtime.py
```

### Stage D：增强现有 deterministic replacement 和 provider-ready context 估算

目标：避免长只读轨迹在已有 replacement 仍不足的情况下无解释地撞上 `context_limit`，并避免内部字符估算误杀。

必须完成：

1. `compact_threshold_ratio` 要么接入 runtime decision，要么在 manifest 中明确 `not_connected`。
2. 80% 上下文阈值模型可见 warning。
3. 90% 上下文阈值触发更强 replacement 或 critical warning。
4. replacement 摘要可恢复、可审计、不泄漏 hidden material。
5. 记录 `internal_char_estimate`、`provider_body_char_estimate`、`provider_ready_token_estimate`、`provider_returned_prompt_tokens`、`estimator_error_ratio`、`threshold_decision_source`。
6. `020 pydicom` targeted smoke 不应无提醒、无 replacement 诊断、无 provider-ready estimate 证据地直接 context limit。

验收命令：

```bash
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_context_manager.py tests/unit/test_agent_loop_protocol.py
```

### Stage E：补文件发现工具和路径恢复

目标：减少宽泛搜索和可恢复路径错误。

必须完成：

1. 优先强化 `list_files` 的工具说明、结果格式、路径建议和 glob workflow。
2. `grep` 支持 `output_mode`。
3. 路径越界和路径 typo 提供模型可见恢复建议。
4. `glob_files` 只作为可选兼容层，必须复用 `list_files` backend 和可见性策略。

验收命令：

```bash
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_tools.py
```

### Stage F：补齐训练导出字段和最终冻结检查

目标：在 Stage F0 已经保证运行前冻结和 inspect gate 的基础上，补齐训练导出字段和最终 freeze 一致性检查。Stage F 不能作为 targeted smoke 之后才想起来补的审计材料；它只能补导出和最终汇总，不能替代 Stage F0。

必须完成：

1. export 样本包含 tool result `result_kind`、搜索事实可信字段、nudge record、context replacement summary 和 provider-ready estimate fields。
2. export audit 检查新增模型可见控制消息是否标记为 harness-generated、model-visible，并校验正式基线和默认训练导出中的 harness-generated convergence nudge 必须 `trainable=false`。只有显式消融实验可以通过单独 policy 覆盖这个默认值，并且 export 中必须记录最终 resolved trainable 值，避免后续训练样本消费方误读。
3. final freeze inspect 重新计算并校验 configuration manifest、run config manifest、formal budget freeze manifest 和 run matrix manifest 的 hash。
4. 新 baseline 的所有 run 都绑定同一组 policy versions。
5. provider retry、`output_token_limit_reached`、malformed tool call repair 等已经部分实现的 hardening 项作为回归验证项保留，不再写成未实现阻塞项。

验收命令：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-model-visible-context RUN_DIR \
  --assert-no-hidden-test-material \
  --assert-prepared-messages-bound \
  --assert-provider-body-equivalent \
  --assert-tool-results-recoverable
```

如果新增 inspect 命令，建议形态为：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-agentloop-convergence RUN_DIR \
  --assert-search-facts-trustworthy \
  --assert-action-index-visible \
  --assert-convergence-nudges-bound \
  --assert-context-replacement-recoverable
```

## 13. Targeted smoke 重新运行方案

完成 Stage F0 和 Stage A 到 Stage D 后，建议重新运行同一组 5 个任务，保持模型、provider、温度、seed、预算和 provider retry policy 不变。不能在 Stage F0 未完成时启动新的 targeted smoke，因为那会让新 run 的 policy version、prepared messages 绑定、convergence nudge、deterministic replacement 增强、provider-ready context estimate 和搜索事实可信协议的 inspect 证据不完整。

建议 baseline id：

```text
pre_verl_deepseek_flash_targeted_tool_context_convergence_v2_20260508
```

建议冻结字段：

1. `search_fact_policy_version`
2. `repository_action_index_policy_version`
3. `convergence_nudge_policy_version`
4. `context_replacement_policy_version`
5. `no_progress_hard_stop_enabled=false`
6. `tool_execution_mode=serial_v0`
7. `provider_retry_policy_version=provider_retry_v0`
8. `model_visible_initial_context_hash`
9. `repository_action_index_hash`
10. `context_estimator_policy_version`
11. `provider_ready_token_estimator_version`
12. `inspect_model_visible_context_report_hash`

观察指标：

1. `grep` 假阴性数量必须为 0。
2. `grep` 和 `list_files` 的 `complete_no_match` 都有可信的 `scan_complete_reason`，且没有 read error、visibility error 或 backend mismatch。
3. 首次候选源码文件读取轮数下降。
4. 首次编辑轮数提前。
5. 空补丁数量下降，或者空补丁原因变得更可解释。
6. `context_limit` 不能在没有 warning、replacement 诊断和 provider-ready estimate 的情况下发生。
7. convergence nudge 后模型是否改变行为，例如从 broad search 转为 read candidate file 或 edit file。

成功标准不是 5 题全部 accepted。更合理的成功标准是：

1. Harness 不再给模型明显错误的搜索事实。
2. 模型首轮能看到可行动候选入口。
3. 无进展时模型能收到明确、可审计、不含隐藏材料的提醒。
4. 上下文超限前有可追溯的 warning、replacement 诊断和 provider-ready estimate。
5. 如果模型仍失败，失败轨迹能区分模型能力不足、模型未响应提醒、搜索工具异常、replacement 已执行但不足、provider-ready 估算不足和普通预算耗尽。

## 14. 正式二十三题新基线前的硬门槛

在进入正式二十三题新基线前，必须满足：

1. Stage F0 已经在任何新 targeted smoke 或正式新基线启动前完成，并且 freeze manifest、run config facts、inspect gate 都能记录新增 policy versions。
2. Stage A 搜索事实可信协议通过 targeted regression，特别是 Docker execution mode 下 `pydicom MultiValue` 搜索不能再返回错误的完整无匹配。
3. Stage B 初始 action index 通过 hidden material 防泄漏检查。
4. Stage C convergence nudge 在 fake provider 和 targeted smoke 中均有证据；凡是触发 no-progress 且尚无成功编辑的 run，都必须能在下一轮 prepared messages 中看到 nudge。
5. Stage D context warning、replacement 增强和 provider-ready estimate 不仅在模拟长上下文场景中通过，还必须在 `020 pydicom` targeted run 中留下真实证据；如果该 run 仍然 `context_limit`，final diagnostics 必须明确记录已经触发过 warning、replacement 和 `threshold_decision_source`。
6. freeze manifest 完整记录所有新 policy versions。
7. 旧探索性 run 只能作为 parent lineage，不能和新结果合并计算 accepted rate。
8. 如果工作区 dirty，必须冻结 dirty diff hash；正式简历展示基线建议使用 clean commit。

## 15. 风险控制

### 15.1 防止 oracle 泄漏

所有新上下文、新提醒和新摘要都不能包含：

1. hidden test patch。
2. fail-to-pass selector。
3. pass-to-pass selector。
4. gold patch。
5. final verifier 原始输出。
6. evaluator-only artifact id。
7. evaluator-only artifact sha256。

### 15.2 防止 baseline 不可比

启用本计划任何一项会改变模型输入或工具反馈的修复后，都必须生成新 baseline id。

不能把以下结果混算：

1. 原 `preparedstatefix` 探索性正式 run。
2. Stage B hardening 后的 targeted smoke。
3. 启用 convergence nudge 后的新 targeted smoke。
4. 启用 context replacement 增强或 provider-ready token estimate 后的新正式二十三题基线。

### 15.3 防止过度控制模型

第一版 convergence nudge 不应强制 hard stop，也不应强制模型必须编辑。提醒应要求模型选择以下之一：

1. 编辑最小候选补丁。
2. 读取一个明确候选文件的小范围行段。
3. 解释具体阻塞原因并给出 final answer。

只有在后续消融证明 hard stop 能提升样本质量且不污染归因后，才考虑启用 `agent_stop_reason=no_progress`。

## 16. 完成定义

本轮深层修复完成后，应能用本地 artifact 直接回答以下问题：

1. `grep` 是否和 `read_file` 使用同一个 workspace backend 语义？
2. `list_files` 和 `_model_visible_path_status()` 是否也遵守同一套搜索事实可信协议？
3. Docker execution mode 下搜索 `MultiValue` 这类已存在符号是否不再返回完整无匹配？
4. 模型首轮是否看到有证据来源、匹配词、span hash 和 ranking reason 的候选源码入口，而不是只有 artifact ref？
5. 连续只读、重复搜索、临近预算无补丁时，模型是否收到可见收敛提醒，并且提醒插入位置不破坏 tool pairing？
6. 上下文接近上限时，Harness 是否先 warning、增强 replacement、记录 provider-ready estimate，而不是只靠内部字符估算直接 hard stop？
7. 路径错误是否给出模型可执行的恢复建议？
8. 如果最终仍失败，run metadata、final verifier boundary 和 metrics 是否能解释失败是模型未响应、模型错误补丁、搜索事实异常、replacement 已执行但不足、provider-ready token estimate 不足、final-only 无中间反馈还是普通预算耗尽？

只有这些问题都能被测试、inspect 命令和 targeted smoke artifact 证明，才建议进入下一轮正式二十三题新基线，并将结果作为简历展示和 RL 训练前可靠性证据。
