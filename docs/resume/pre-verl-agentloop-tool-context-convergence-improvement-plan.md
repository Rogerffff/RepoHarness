# Pre-verl AgentLoop 工具效率、搜索语义和初始上下文改进计划

更新时间：2026-05-08

状态：正式二十三题测评前后均可实施的专项改进计划。本文聚焦当前探索性正式测评已经暴露的 harness 工具问题、上下文问题和收敛控制问题，并补充正式 baseline 前必须先通过的 Stage 0 硬门槛。已经在 `docs/resume/pre-verl-agentloop-harness-hardening-implementation-plan.md` 和 `docs/resume/pre-verl-smoke-and-23-eval-readiness-implementation-plan.md` 中完成的隐藏材料泄漏检查、run readiness manifest 等内容不再重复展开；但 provider retry 冻结、`run_metadata.failure_diagnostics` 归因和环境回归证明会在本文 Stage 0 中作为正式 baseline 前置条件明确收口。

## 1. 结论

当前 RepoHarness 的主要问题不是单纯的模型能力不足，而是 AgentLoop 给模型提供的“状态反馈”还不够像一个成熟软件工程智能体 harness：

1. 工具调用虽然有预算上限，但没有持续判断“这些工具调用是否还在产生新信息”。探索性正式测评里有 6 个 run 以 `max_turns` 结束并产出空补丁，这些 run 不是工具调用额度耗尽，而是 48 轮模型调用耗尽。很多 run 还剩大量工具调用额度，却长期停留在只读搜索、读取文件和重复定位阶段。
2. `grep` 的模型可见反馈会把“完整扫描后无匹配”和“只扫描了部分候选文件所以暂时无匹配”混在一起。模型看到 `No matches.` 之后容易相信目标不存在，即使同一个结果后面又提示扫描达到上限。
3. 初始模型可见上下文偏薄。当前首轮 prompt 主要包含 issue、预算、允许工具、README 和 CONTRIBUTING 预览；`source_snapshot` 和 `repo_context_index` 虽然已经作为 run facts 写入 artifact，但没有进入首轮 `prepared_messages`。对于需要快速定位源码入口的任务，这会显著增加无效探索轮数。

参考 Claude Code 的生产级实现，应该借鉴的是三个设计不变量：第一，工具结果必须显式表达“完整性”和“下一步建议”；第二，AgentLoop 必须把“是否有进展”建模成可审计状态，而不是只靠最大轮数兜底；第三，初始上下文应当分层、可截断、可追溯，并包含足够的仓库入口信息，同时严格排除 evaluator-only 材料。

## 2. 证据范围

本计划使用以下本地证据和参考实现：

1. 探索性正式测评目录：`runs/pre-verl-agentloop-formal-deepseek-pro-23-preparedstatefix-20260508T041000Z`。
2. 最新 smoke 目录：`runs/pre-verl-agentloop-smoke-deepseek-flash-stagec-budget8192-context180k-20260507T205500Z`。
3. RepoHarness 当前实现：`src/repo_harness/agent_loop/loop.py`、`src/repo_harness/tools/minimal.py`、`src/repo_harness/context/builder.py`、`src/repo_harness/pre_verl_run_facts.py`、`src/repo_harness/evaluation/runner.py`、`scripts/pre_verl/run_agentloop_evaluation.py`。
4. Claude Code TypeScript 参考实现：`reference/claude-code-typescript-src/query.ts`、`reference/claude-code-typescript-src/query/tokenBudget.ts`、`reference/claude-code-typescript-src/query/stopHooks.ts`、`reference/claude-code-typescript-src/services/tools/toolOrchestration.ts`、`reference/claude-code-typescript-src/tools/GrepTool/GrepTool.ts`、`reference/claude-code-typescript-src/tools/GlobTool/GlobTool.ts`、`reference/claude-code-typescript-src/context.ts`。

探索性正式测评的 run matrix 显示：23 个任务中，4 个被 quality gate 阻止，19 个进入正式 final verifier boundary；进入正式 boundary 的 19 个任务中，6 个 accepted，7 个 final verifier rejected，6 个 `max_turns` 且空补丁。

6 个空补丁任务的工具行为如下：

| 任务 | 模型调用轮数 | 工具调用数 | 工具分布 | 结论 |
| --- | ---: | ---: | --- | --- |
| `pre_verl_dev_001_sqlfluff__sqlfluff_1625` | 48 | 50 | `grep` 33, `list_files` 8, `read_file` 8, `git_diff` 1 | 长时间搜索和列目录，无编辑 |
| `pre_verl_dev_003_sqlfluff__sqlfluff_1733` | 48 | 49 | `grep` 21, `read_file` 22, `list_files` 6 | 长时间定位，无有效补丁 |
| `pre_verl_dev_014_pylint_dev__astroid_1333` | 48 | 51 | `read_file` 27, `grep` 21, `list_files` 2, `git_diff` 1 | 读取量高但未收敛 |
| `pre_verl_dev_015_pylint_dev__astroid_1196` | 48 | 48 | `grep` 23, `read_file` 23, `list_files` 2 | 只读探索耗尽轮数 |
| `pre_verl_dev_017_pylint_dev__astroid_1268` | 48 | 55 | `grep` 31, `read_file` 22, `list_files` 2 | 搜索和读取循环 |
| `pre_verl_dev_020_pydicom__pydicom_1413` | 48 | 52 | `read_file` 32, `grep` 16, `list_files` 4 | 大量读取但无编辑 |

其中 `pre_verl_dev_001_sqlfluff__sqlfluff_1625` 首次 `grep(query="L031")` 的模型可见结果是：

```text
No matches.
[truncated] Search reached the scanned-file limit; narrow root, glob, or query instead of paginating.
```

这条结果同时表达“无匹配”和“扫描不完整”，会误导模型把“当前扫描范围未找到”理解成“仓库中不存在”。同一事件里，顶层 `ToolResult.truncated` 当前并没有被 `_tool_result` 可靠维护，实际经常保持 schema 默认值 `false`；而 `typed.truncated` 表示搜索扫描达到限制，因此是 `true`。这说明当前 schema 缺少可靠的 `output_truncated` 事实字段，并且把“搜索结果分页或扫描不完整”都压进了含义过宽的 `typed.truncated`。

同一任务首轮 `prepared_messages` 的 user content 只有以下顶层字段：`allowed_tools`、`budget`、`context_metadata`、`execution_mode`、`language`、`network_policy`、`permission_mode`、`repository_context`、`task`、`test_command`、`test_command_visibility`、`workspace_root`。`repository_context` 只包含 `README.md` 和 `CONTRIBUTING.md` 预览，没有 `repo_context_index`、`source_snapshot`、候选源码路径或 `AGENTS.md`。

## 3. Claude Code 参考实现中可借鉴的不变量

Claude Code 是面向用户交互的产品，RepoHarness 是面向评测、审计和训练数据导出的 harness，不能照搬产品 UI、个人记忆、托管账户、MCP 发现、Plan Mode 审批等特性。但它有一些非常适合 RepoHarness 借鉴的工程不变量。

### 3.1 工具结果必须表达完整性

Claude Code 的 `GrepTool` 和 `GlobTool` 会明确区分：

1. 完整扫描后确实没有匹配。
2. 有匹配但结果分页或结果数量达到上限。
3. 搜索超时、缓冲区溢出或扫描不完整。
4. 当前模式可能写错，例如把正则当成字面量。
5. 下一步应该缩小 `path`、`glob`、`type`，还是继续分页。

RepoHarness 当前 `grep` 已经有 `scanned_file_count`、`skipped_hidden_path_count`、`truncated`、`next_offset` 和 `recovery_hint`，但模型可见文本和 typed schema 没有把完整性讲清楚。正式训练轨迹中，模型不应该从工具文本里猜测搜索是否完整。

### 3.2 主循环必须把“继续、停止、收敛、恢复”显式建模

Claude Code 的 query loop 不是只靠最大轮数停止。它有 token budget、输出 token 超限恢复上限、stop hook、继续提示、工具 hook 和压缩策略。RepoHarness 不需要复制这些产品能力，但需要保留对应的 harness 不变量：

1. 接近预算时，模型应该收到明确的收敛提示。
2. 连续多轮只读且没有补丁时，系统应该记录诊断事件，并要求模型总结当前假设、候选文件和下一步最小补丁。
3. 重复同一搜索、重复读取同一范围、连续工具失败等情况应该进入可审计的 loop diagnostics。
4. 如果最终仍然没有补丁，failure taxonomy 应该能区分 `model_no_patch_generated`、`budget_exhausted_empty_patch`、`no_progress_empty_patch` 和 harness/provider 错误。

### 3.3 初始上下文应当分层、可追溯、可截断

Claude Code 会把系统指令、项目指令、用户上下文、Git 状态、当前日期、压缩摘要、文件索引和工具能力分别管理。RepoHarness 不需要把完整文件索引塞进 prompt，但应该给模型一个稳定、简洁、可审计的仓库入口摘要：

1. 当前仓库有哪些顶层目录和关键配置文件。
2. 当前任务 issue 文本中显式提到了哪些文件、类名、函数名或模块名。
3. 根据模型可见源码索引，哪些文件是候选入口。
4. 哪些上下文来自不可信仓库文件，不能覆盖系统规则。
5. 哪些上下文因为 evaluator-only 或隐藏测试策略被明确排除。

## 4. 当前 RepoHarness 的具体差距

### 4.1 `AgentStopReason` 有 `no_progress`，但主循环没有使用

`src/repo_harness/agent_loop/schemas.py` 已经在 `AgentStopReason` 中定义了 `no_progress`，但 `src/repo_harness/agent_loop/loop.py` 的主循环只在超时、费用、上下文、工具调用数、测试次数、provider/model 错误等场景停止。连续只读无编辑、重复搜索、重复读取、临近轮数耗尽都没有对应的事件、模型可见提示或 metrics 字段。

当前 `metrics.json` 的 `interaction_efficiency` 主要记录 `agent_stop_reason`、反馈测试策略、final verifier mode、baseline status 等字段，没有记录：

1. 连续只读轮数。
2. 重复工具调用次数。
3. 空搜索次数。
4. 临近预算提示次数。
5. 是否曾经形成候选补丁。
6. 最后一次有效进展发生在哪一轮。

### 4.2 工具执行仍然是串行，`is_concurrency_safe` 没有带来执行收益

`ToolDefinition` 已经有 `is_read_only` 和 `is_concurrency_safe` 这类字段，但当前 AgentLoop 对一个 assistant response 中的多个 tool calls 逐个执行。对于正式 baseline 可以继续保持串行以降低变量；但在分析工具效率时，需要至少记录 `tool_execution_mode="serial"`，并在后续版本实现只读工具批量执行的可选策略。否则工具 schema 中的并发安全信息只是声明，没有 runtime 收益。

### 4.3 `grep` 的状态语义混淆

`src/repo_harness/tools/minimal.py` 当前把 `preview` 写成：

1. 有匹配：展示匹配行。
2. 无匹配：展示 `No matches.`。
3. 如果 `payload.truncated` 且 `next_offset` 为 `None`：再追加扫描上限提示。

这会产生语义冲突：`No matches.` 看起来像完整结论，但后续提示又说明扫描没有完成。除此之外，`truncated` 字段同时承担了至少三种不同含义：

1. 模型可见工具输出字符串是否被 `max_tool_output_chars` 截断。
2. 搜索结果页是否还有更多匹配。
3. 搜索候选文件扫描是否达到文件数量上限。

这三种含义应该拆开，否则模型、inspect 命令和后续训练样本消费者都会误读。

### 4.4 初始上下文只读取固定文件，且漏掉 `AGENTS.md`

`src/repo_harness/context/builder.py` 的 `REPO_CONTEXT_FILES` 当前是 `["AGENT.md", "README.md", "CLAUDE.md", "CONTRIBUTING.md"]`。但本仓库和很多现代 agent 工程使用的是 `AGENTS.md` 复数。`src/repo_harness/pre_verl_run_facts.py` 已经检查 root `AGENTS.md` 是否存在，却没有把它注入初始上下文。这会让模型缺少仓库内最重要的 agent 指令。

### 4.5 `source_snapshot` 和 `repo_context_index` 只写入 artifact，没有进入模型首轮上下文

`src/repo_harness/pre_verl_run_facts.py` 已经生成：

1. `source_snapshot`：包含 `source_tree_hash`、`base_commit`、`agents_md_present` 等。
2. `repo_context_index`：包含文件数量、前 200 个 sample paths、`expected_files`、敏感路径过滤策略和已知限制。

`src/repo_harness/evaluation/runner.py` 会把这些 artifact ref 写入 `run_config_facts`，但 `ContextBuilder.build_initial_messages` 没有接收这些引用或摘要。因此模型不能利用这些安全上下文，只有审计者能看到这些产物。

### 4.6 pre-verl task definition 的 `expected_files` 仍然为空

`scripts/pre_verl/run_agentloop_evaluation.py` 当前把 `expected_files` 写成空列表，同时标注 `expected_files` 是 model-visible。也就是说 schema 允许给模型源码入口，但正式 pre-verl 任务生成没有填充。对于 SWE-Bench-like 任务，不能从隐藏 selector 或 gold patch 派生 `expected_files`，但可以从公开 issue 文本、公开仓库索引和模型可见文件路径中派生候选入口。

## 5. 实施阶段

建议先完成 Stage 0 正式 baseline 前硬门槛，再分三阶段实施工具和上下文改进。Stage 1 修搜索工具反馈，风险最低且能立即减少误导；Stage 2 把安全的仓库索引真正注入首轮上下文；Stage 3 加入 no-progress 诊断和收敛提示。只读工具并发执行作为后续可选优化，不建议阻塞下一轮正式 baseline。

### Stage 0：正式 baseline 前硬门槛

目标：在改变工具语义和初始上下文之前，先确保正式 baseline 的运行环境、provider retry、失败归因和 freeze manifest 都是可审计、可复现、不会污染 accepted rate 的状态。否则后续即使模型表现改善，也无法证明改善来自工具和上下文修复，而不是 provider 临时错误、环境材料化失败或 manifest 身份混乱。

必须修复或确认的内容：

1. Provider retry 冻结：正式 DeepSeek/OpenAI run config 不能继续写死 `retry_policy: none`。正式 baseline 应默认使用 `provider_retry_v0`，冻结 `max_attempts=3`、`backoff_delays_ms=[0, 250, 1000]`、`sleep_enabled=true` 和 retryable error types。failure injection 和单元测试可以继续使用 `provider_retry_no_sleep_v0`。
2. Provider retry 产物绑定：每个真实 provider model call 都应有 `provider_retry_policy` artifact、attempt artifact refs、`attempt_count`、`retry_count`，并在 `model_call_completed`、`run_config_facts.json`、run config manifest 和 formal freeze manifest 中可追溯。
3. `run_metadata.failure_diagnostics` 归因修正：当 `final_verifier_boundary.json` 明确记录 `final_verifier_status="rejected"`、`failure_category="model_patch_rejected_by_final_verifier"`、`failure_owner="model_wrong_fix"` 时，`run_metadata.json` 不能再把该 run 归为 `environment_failure/final_verifier_failed`。当前 `FailureDiagnostics.failure_category` 是宽类别枚举，没有 `model_patch_rejected_by_final_verifier` 这种 pre-verl 细分类，也没有单独的 `failure_owner` 字段；因此第一版修复应把 rejected boundary 映射为 `FailureCategory.model_failure`，并把原始 `final_verifier_boundary.failure_category`、`final_verifier_boundary.failure_owner`、`final_verifier_boundary.final_verifier_status` 放入 `details`。除非同步扩展 `src/repo_harness/run_metadata/schemas.py`，否则不要把 pre-verl 细分类直接写进枚举字段。
4. 环境材料化回归证明：当前工作区已经修复 `pvlib`、`pyvista`、Docker image platform 检查和 symlink 复制问题。新的正式 baseline 前必须保留定向回归证据，确认旧探索性 run 中 4 个 `invalid_task` 不再代表当前 HEAD 状态。这 4 个任务是 `pre_verl_dev_008_pvlib__pvlib_python_1707`、`pre_verl_dev_010_pvlib__pvlib_python_1606`、`pre_verl_dev_011_pvlib__pvlib_python_1854`、`pre_verl_dev_018_pyvista__pyvista_4315`。如果为了节约 provider 成本只做代表性证明，必须明确代表性规则：同一 repo、同一环境修复原因、同一 `environment_id` 或同一 setup/platform 失败模式可以用一个 run 代表，但正式 baseline 前仍建议四个旧 blocked task 全部重新证明。
5. Baseline 身份冻结：启用本文 Stage 0 到 Stage 3 的任何改动后，都必须生成新的 `baseline_id` 和 `baseline_lineage`，并把旧的 `preparedstatefix` formal run 标记为 exploratory/provisional parent，不能与新 baseline 合并计算 accepted rate。

建议修改位置：

1. `scripts/pre_verl/run_agentloop_evaluation.py`：把正式 run config 默认 retry policy 改为 `provider_retry_v0`，并把 retry policy、provider axis、baseline id 和 policy versions 写入 configuration manifest、run config manifest、formal budget freeze manifest 和 run matrix。
2. `src/repo_harness/run_metadata/writer.py`：读取 pre-verl `final_verifier_boundary.json`，优先使用其中的 `failure_category` 和 `failure_owner` 生成 `failure_diagnostics`。
3. `tests/unit/test_pre_verl_agentloop_scheduler.py`：断言正式 run config、configuration manifest、run config manifest 和 budget freeze manifest 都冻结 provider retry。
4. `tests/unit/test_run_metadata.py`：新增 rejected boundary 的归因测试，确保模型错误补丁不会被写成 environment failure。
5. `tests/unit/test_docker_adapter_image_platform.py`、`tests/unit/test_pre_verl_agentloop_scheduler.py`：保留当前环境修复的定向证明。

验收要求：

1. `PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_pre_verl_agentloop_scheduler.py tests/unit/test_run_metadata.py tests/unit/test_docker_adapter_image_platform.py tests/unit/test_pre_verl_failure_injection.py`
2. Provider retry 事件链测试必须覆盖 `model_call_completed.retry_policy_ref`、`provider_attempt_refs`、`attempt_count` 和 `retry_count`，证明不仅 run config 冻结了 retry policy，真实 provider call 事件也绑定了 retry artifact。
3. 定向环境回归目录中 4 个旧 blocked task 的 `baseline.status` 必须为 `valid`，并且全部进入 `executed_formal_boundary`。如果只运行代表性任务，必须在报告中写明代表性规则和未覆盖任务列表。
4. `pyvista` 的 `docker_backend_facts.json` 必须记录 `requested_container_platform="linux/amd64"` 且 `image_platform="linux/amd64"`。
5. 针对环境回归 run 执行 `inspect-model-visible-context --assert-no-hidden-test-material --assert-prepared-messages-bound --assert-provider-body-equivalent --assert-tool-results-recoverable` 必须通过。
6. 新生成的正式 smoke/formal manifest 必须冻结 `baseline_id`、`baseline_lineage`、`provider_retry_policy_version`、`retry_max_attempts`、`retry_backoff_policy`、`provider_axis_scope` 和 `code_commit_hash` 或 dirty worktree policy。
7. 旧正式探索 run 中的 4 个 `invalid_task` 只能作为历史探索性证据，不能再作为当前 HEAD 的环境状态依据。

### Stage 1：搜索结果语义修复

目标：任何模型可见搜索结果都必须让模型知道“本次搜索是否完整、是否有更多结果、下一步应该怎么缩小范围”。

修改位置：

1. `src/repo_harness/tools/minimal.py`
2. `tests/unit/test_tools.py`
3. `docs/04-tool-system-and-orchestration.md`
4. `docs/10-context-session-and-failure-diagnostics.md`
5. `repo-harness inspect-model-visible-context` 相关检查逻辑，如果已有检查覆盖工具结果可恢复性，需要同步扩展。

建议新增或调整的 typed 字段：

```json
{
  "result_kind": "complete_with_matches | complete_no_match | partial_scan_with_matches | partial_scan_no_match | result_page_truncated | page_empty_out_of_range | invalid_query",
  "scan_complete": true,
  "scan_limit_reached": false,
  "result_limit_reached": false,
  "output_truncated": false,
  "candidate_file_count": 1234,
  "scanned_file_count": 1234,
  "scanned_file_limit": 2000,
  "unscanned_file_count": 0,
  "next_offset": null,
  "recommended_next_calls": [
    {
      "tool": "grep",
      "arguments": {
        "query": "symbol_name",
        "root": "src",
        "glob": "*.py",
        "mode": "literal"
      },
      "reason": "当前仓库范围过大，建议缩小到源码目录"
    }
  ]
}
```

模型可见文本建议按状态拆分：

1. 完整无匹配：`No matches found after scanning all 317 model-visible files under root='src'.`
2. 部分扫描无匹配：`No matches found in the scanned subset, but the search stopped after 2000 candidate files. Do not conclude the symbol is absent. Narrow root or glob and retry.`
3. 有匹配且还有更多结果：展示当前页匹配，并提示 `More matches are available. Call grep(..., offset=next_offset) to continue.`
4. 正则疑似误用：保留当前已有的 `mode='literal'` 到 `mode='regex'` 恢复提示，但把它放入 `recommended_next_calls`。
5. 输出字符串被截断：用 `output_truncated=true` 表达，不复用搜索扫描状态。

实现要点：

1. `_grep_python` 需要返回 `candidate_file_count` 和 `scan_limit_reached`。如果由于隐藏路径过滤导致候选文件减少，也要区分“候选文件被安全策略排除”和“候选文件尚未扫描”。
2. `_grep` 需要根据 `matches`、`next_offset`、`scan_limit_reached`、`candidate_file_count` 生成 `result_kind`。
3. 顶层 `ToolResult.truncated` 要么被真正维护为“模型可见工具输出被截断”，要么新增明确的 `output_truncated` 字段并让 inspect 以该字段为准；搜索扫描状态只放在 typed 字段中，不能继续依赖含义含混的 `typed.truncated`。
4. 对 `list_files` 也建议新增 `result_kind`：`files_returned`、`complete_empty`、`page_truncated`、`page_empty_out_of_range`。这不是第一优先级，但可以顺手补齐。

验证要求：

1. 单元测试覆盖完整扫描无匹配：`result_kind=complete_no_match`、`scan_complete=true`，模型可见文本不能出现扫描上限提示。
2. 单元测试覆盖扫描上限无匹配：`result_kind=partial_scan_no_match`、`scan_complete=false`、`scan_limit_reached=true`，模型可见文本不能只写 `No matches.`。
3. 单元测试覆盖有匹配但结果分页：`result_kind=result_page_truncated` 或 `partial_scan_with_matches`，`next_offset` 必须存在。
4. 回归测试覆盖 `pre_verl_dev_001_sqlfluff__sqlfluff_1625` 的第一类场景，确保不会再产生 `No matches.` 加扫描上限提示的混合文本。
5. `inspect-model-visible-context --assert-tool-results-recoverable` 应能识别新的 `recommended_next_calls`。

### Stage 2：安全初始上下文增强

目标：把已经生成的 `source_snapshot` 和 `repo_context_index` 转化为安全、简洁、模型可见的首轮上下文，让模型更快找到候选源码入口，同时保证不会泄漏 hidden patch、hidden selector、gold patch、final verifier 原始输出或 evaluator-only artifact 哈希。

修改位置：

1. `src/repo_harness/context/builder.py`
2. `src/repo_harness/pre_verl_run_facts.py`
3. `src/repo_harness/evaluation/runner.py`
4. `scripts/pre_verl/run_agentloop_evaluation.py`
5. `src/repo_harness/pre_verl_agentloop.py`
6. `tests/unit/test_context_builder.py` 或现有上下文相关测试文件
7. `tests/unit/test_pre_verl_agentloop.py`

建议实现方式：

1. 在 `ContextBuilder.build_initial_messages` 增加一个可选参数，例如 `model_visible_repo_context` 或 `initial_context_bundle`。
2. `EvaluationRunner` 在调用 `write_source_snapshot_and_context_index` 后，把一个安全摘要传给 `ContextBuilder`。不要让 `ContextBuilder` 自己读取 run facts JSON，以免模块边界变得混乱。
3. `pre_verl_run_facts.py` 中的文件索引过滤规则要与工具可见路径规则对齐，排除 `.git`、`.venv`、`.pre_verl_venv`、缓存目录、provider raw artifacts、hidden evaluator materials、凭据路径和软链接越界路径。
4. `REPO_CONTEXT_FILES` 应该兼容 `AGENTS.md` 和 `AGENT.md`，优先级建议是 `AGENTS.md`、`CLAUDE.md`、`README.md`、`CONTRIBUTING.md`、`AGENT.md`。每条记录都保留 `path`、`source`、`sha256`、`truncated`、`preview_char_count` 和 instruction boundary。
5. `scripts/pre_verl/run_agentloop_evaluation.py` 可以从公开 issue 文本和模型可见文件索引中派生 `candidate_source_entries`，但不要把它命名成确定性的 `expected_files`，除非来源本来就是 dataset 中模型可见的 `expected_files`。这样可以避免把候选入口误写成 oracle。

建议首轮 user content 新增字段：

```json
{
  "repository_context_index": {
    "schema_version": "repo_harness_model_visible_repo_context_index_v0",
    "source_snapshot_ref": {
      "kind": "source_snapshot",
      "sha256": "只允许 not_sensitive source_snapshot 的 sha256"
    },
    "source_tree_hash": "公开源码树哈希",
    "base_commit": "公开 base commit",
    "agents_md_present": true,
    "top_level_directories": ["src", "tests", "docs"],
    "key_config_files": ["pyproject.toml", "setup.cfg"],
    "model_visible_file_count": 317,
    "sample_paths": ["src/package/module.py"],
    "candidate_source_entries": [
      {
        "path": "src/package/module.py",
        "reason": "issue_text_token_match",
        "matched_terms": ["module", "ClassName"]
      }
    ],
    "context_selection_policy_version": "repo_harness_initial_context_selection_v0",
    "evaluator_only_material_excluded": true,
    "selection_limit": {
      "max_paths": 40,
      "max_preview_chars": 6000
    }
  }
}
```

候选入口选择策略必须是确定性的，建议按以下顺序：

1. dataset 显式提供且模型可见的 `expected_files`。
2. issue 文本中直接出现的相对路径，例如 `src/foo/bar.py`。
3. issue 文本中的类名、函数名、配置键、错误名和模块名，与模型可见文件路径或文件内容浅层索引匹配。
4. 语言和项目配置推断出的常见入口，例如 Python 项目的 `src/`、包名目录、`tests/`、`pyproject.toml`、`setup.cfg`。
5. 最近修改时间或文件大小不应作为正式 baseline 的主要排序依据，除非这些信息来自公开源码状态并已冻结。

不建议在正式 baseline 中使用额外 side model 来选择相关文件。Claude Code 可以用独立模型做记忆筛选，但 RepoHarness 的正式评测需要可复现、可审计、可冻结。若未来引入 side model selector，必须单独记录 selector 模型、输入、输出、hash、成本和失败策略，并与主模型评测隔离。

验证要求：

1. 首轮 `prepared_messages` 必须包含 `repository_context_index` 或等价字段。
2. 对 `pre_verl_dev_001_sqlfluff__sqlfluff_1625` 这类任务，首轮上下文至少应暴露模型可见候选入口或明确告诉模型如何用 `grep`/`list_files` 缩小到源码目录。
3. `AGENTS.md` 存在时必须进入 `repository_context`，并带有不可信上下文边界说明。
4. `inspect-model-visible-context --assert-no-hidden-test-material` 必须覆盖新增字段，检查 hidden patch 内容、selector 内容、evaluator-only artifact id、evaluator-only artifact sha256 都不在 `prepared_messages`、transcript、provider raw request 中出现。
5. 新增稳定性测试：同一个 source tree、同一个 issue、同一个 policy version 下，`repository_context_index` hash 必须稳定。
6. 新增 budget 测试：初始上下文增强不能超过配置的 `max_context_tokens`，超出时必须按 policy 截断并记录 `truncated=true`。

### Stage 3：无进展检测和收敛控制

目标：在不污染模型评测结论的前提下，让 AgentLoop 识别“模型还在使用工具，但没有向补丁收敛”的场景，并在合适时机给出模型可见的结构化提醒。

修改位置：

1. `src/repo_harness/agent_loop/loop.py`
2. `src/repo_harness/agent_loop/schemas.py`
3. `src/repo_harness/evaluation/metrics.py`
4. `src/repo_harness/pre_verl_agentloop.py`
5. `tests/unit/test_agent_loop_protocol.py`
6. `tests/integration/test_pre_verl_agentloop_runtime.py`

建议新增 `LoopProgressController` 或 `NoProgressMonitor`，维护以下状态：

```json
{
  "schema_version": "repo_harness_loop_progress_v0",
  "last_progress_turn": 12,
  "consecutive_read_only_turns": 8,
  "consecutive_no_edit_turns": 20,
  "edit_count": 0,
  "diff_hash": null,
  "git_diff_seen_after_edit": false,
  "repeated_tool_call_count": 6,
  "empty_search_count": 11,
  "partial_scan_no_match_count": 5,
  "candidate_files_seen": ["src/package/module.py"],
  "near_budget_warning_count": 1,
  "convergence_nudge_count": 1,
  "no_progress_suspected": true
}
```

哪些行为算作“有进展”：

1. `edit_file` 成功修改文件。
2. `git_diff` 在编辑后返回非空 diff。
3. 新的 `grep` 或 `read_file` 命中了之前没有出现过的候选文件。
4. 模型提出 final answer 且有非空 patch。
5. 公开测试工具成功运行并产生新的可见结果。

哪些行为增加 no-progress 风险：

1. 连续多轮只使用 `grep`、`list_files`、`read_file`、`git_diff`，且没有编辑。
2. 重复相同 `effective_tool_name + normalized_input_hash`。
3. 多次 `complete_no_match` 或 `partial_scan_no_match` 后仍然使用同一 root/query 策略。
4. 多次读取同一文件同一行段。
5. 剩余轮数很少但仍继续 broad search。

模型可见提醒建议分为两个等级：

1. 诊断提醒，不改变停止原因。触发条件示例：连续 10 个只读工具调用或连续 8 轮无编辑。提醒内容应要求模型输出当前假设、已排除路径、下一步最小行动，并优先选择一个候选文件编辑或明确说明阻塞原因。
2. 临近预算收敛提醒，不立即停止。触发条件示例：剩余轮数小于等于 6 且没有成功编辑，或剩余工具调用数小于等于 10。提醒内容应要求模型停止 broad search，选择最小补丁、运行可见验证或给出没有补丁的最终原因。

示例模型可见提醒：

```text
Loop progress diagnostic: the last 10 tool actions were read-only and no patch has been created.
Before calling another broad search, summarize the current hypothesis, name the most likely file,
and either make the smallest plausible edit or explain the concrete blocker.
```

注意：该提醒是 harness 生成的控制消息，不是 evaluator-only 信息。它不能包含 hidden tests、final verifier 结果、gold patch、selector 名称或任何 evaluator-only artifact hash。

是否启用硬停止需要分阶段：

1. 第一版只记录 `loop_diagnostic` 事件和 metrics，并注入最多 1 到 2 次模型可见收敛提醒，不把 stop reason 改成 `no_progress`。
2. 第二版可以在严格阈值下启用 `agent_stop_reason="no_progress"`，例如连续 20 轮无编辑且重复工具调用比例超过 60%，并且已经发出过收敛提醒。
3. 一旦启用硬停止，pre-verl final verifier 归因必须新增或确认 `no_progress_empty_patch`，避免把 harness 识别出的无进展场景误归因为普通 `model_no_patch_generated`。

验证要求：

1. 使用 fake provider 构造连续重复 `grep` 的 replay，断言事件流出现 `loop_diagnostic`。
2. 使用 fake provider 构造 48 轮只读无编辑，断言在阈值轮次前后 `prepared_messages` 出现模型可见收敛提醒。
3. 构造已经成功编辑的场景，确保 no-progress 计数被重置或降级。
4. 构造临近预算场景，断言最多注入一次或两次提醒，不能每轮重复刷屏。
5. `metrics.json` 的 `interaction_efficiency.loop_diagnostics_summary` 必须记录 no-progress、near-budget、convergence nudge 和最终是否有 patch。
6. `pre_verl_agentloop` 的 final verifier boundary 必须记录 `no_progress_suspected`，并在硬停止启用后记录 `agent_stop_reason="no_progress"`。

### Stage 4：只读工具批量执行，可选但不阻塞正式 baseline

Claude Code 会把连续的并发安全工具调用批量执行，并按原始 tool call 顺序回填结果。RepoHarness 已有 `is_concurrency_safe` 声明，但 runtime 仍串行执行。

这项优化可以降低真实 provider 等待成本，但会改变事件时序、duration、并发错误处理和 artifact 写入顺序，因此不建议在下一轮正式 baseline 前仓促启用。建议先做两件事：

1. 在 run config facts 和 freeze manifest 中记录 `tool_execution_mode="serial_v0"`。
2. 另开实验分支实现 `read_only_batch_v0`，只允许 `list_files`、`read_file`、`grep` 这类只读工具并发执行，且必须按 tool call 原顺序写入 transcript 和 messages。

验证要求：

1. 并发执行和串行执行在同一 mock workspace 上产生相同 messages 顺序和相同 artifact 内容 hash。
2. 任一工具失败时，只影响该工具结果，不改变同一批次其他工具的结果回流。
3. 写入类工具、权限交互工具、测试工具不能进入并发批次。

## 6. Freeze manifest 和训练导出要求

这些改动会改变模型输入和工具反馈，因此一旦启用，就必须生成新的 baseline id，不能与之前的探索性 formal run 混为同一条基线。

正式 manifest 至少应冻结以下字段：

1. `baseline_id`，例如 `pre_verl_deepseek_pro_23_tool_context_convergence_v1_20260508T000000Z`。启用本文任何会改变模型输入、工具反馈或 loop 控制的改动后，都不能沿用旧 baseline id。
2. `baseline_lineage`，至少包含 `parent_baseline_id`、`parent_run_dir`、`parent_status`、`change_summary`。当前已经完成的 `preparedstatefix` 正式 run 应标记为 `exploratory` 或 `provisional_parent`，不能和新 baseline 合并计算 accepted rate。
3. `code_commit_hash` 和 `working_tree_policy`。正式 baseline 应优先要求 clean worktree；如果允许 dirty worktree，必须把 dirty diff hash 和 dirty file 列表写入 manifest。
4. `task_set_manifest_hash`、`task_definition_manifest_hash`、`run_config_manifest_hash`、`configuration_manifest_hash`、`formal_budget_freeze_manifest_hash` 和 `run_matrix_manifest_hash`。
5. `search_result_semantics_version`，例如 `repo_harness_search_result_semantics_v1`。
6. `initial_context_selection_policy_version`，例如 `repo_harness_initial_context_selection_v1`。
7. `loop_progress_policy_version`，例如 `repo_harness_loop_progress_diagnostic_v1`。
8. `convergence_nudge_policy_version`，如果只记录诊断不注入提醒，应明确为 `disabled`。
9. `no_progress_hard_stop_enabled`，布尔值。
10. `tool_execution_mode`，例如 `serial_v0`。
11. `provider_axis_scope`、`provider_retry_policy_version`、`retry_max_attempts` 和 `retry_backoff_policy`，防止工具和上下文改动与 provider runtime 变更混在一起。
12. `repo_context_index_hash`。
13. `source_snapshot_hash`。
14. `model_visible_initial_context_hash`。
15. `inspect_model_visible_context_report_hash`。

必须更新并检查以下正式运行 manifest：

1. `pre_verl_agentloop_configuration_manifest.json`：写入 `baseline_id`、`baseline_lineage`、`code_commit_hash`、provider axis、三类新 policy version、`tool_execution_mode` 和 manifest schema version。
2. `formal_budget_freeze_manifest.json`：除了预算、模型、温度和 seed，还要写入 `max_context_tokens`、`search_result_semantics_version`、`initial_context_selection_policy_version`、`loop_progress_policy_version`、`convergence_nudge_policy_version` 和 `no_progress_hard_stop_enabled`。
3. `pre_verl_agentloop_run_config_manifest.json`：每个 run config entry 都要绑定同一 `baseline_id`，并记录 run config 文件 hash、policy version、provider retry policy、permission policy manifest hash 和模型可见初始上下文策略。
4. `pre_verl_agentloop_formal_run_matrix_manifest.json`：matrix 顶层和每个 entry 都要绑定 `baseline_id`，并记录 `run_config_ref`、`run_config_facts_ref`、`final_verifier_boundary_ref`、`inspect_model_visible_context_report_ref`。旧探索性 run 只能作为 lineage evidence，不能混入新 baseline 指标。
5. 每个 run 的 `run_config_facts.json`：必须能追溯到 `source_snapshot_ref`、`repo_context_index_ref`、`model_visible_initial_context_hash`、`tool_schema_snapshot_ref` 和 policy versions。

验收断言不能只检查文件存在，还要检查上述字段跨 manifest 一致。例如 run matrix 的 `baseline_id` 必须等于 configuration manifest 的 `baseline_id`；每个 run config hash 必须出现在 run config manifest；每个 run 的 `model_call_started.prepared_messages_ref` 必须能追溯到对应的模型可见初始上下文策略。

训练导出时应增加或确认以下字段：

1. 每个 tool result 的 `result_kind`、`scan_complete`、`recommended_next_calls`。
2. 每个 run 的 `loop_diagnostics_summary`。
3. 每个模型可见收敛提醒的 transcript record，并标记为 harness-generated、model-visible、trainable policy 可配置。
4. `no_progress_suspected` 和 `near_budget_warning_count`，用于后续分析模型失败和 harness 失败边界。

## 7. 推荐实施顺序

1. 先实施 Stage 1 搜索结果语义修复。这一阶段主要改变工具结果文本和 typed result，风险最低，且可以直接修复 `No matches.` 与扫描上限混用的问题。
2. 然后实施 Stage 2 安全初始上下文增强。这一阶段会改变首轮 prompt，应单独运行 smoke，并用 inspect 命令确认没有隐藏材料泄漏。
3. 再实施 Stage 3 诊断型 no-progress 记录。第一版只记录事件和 metrics，不启用硬停止，降低对 baseline 分布的冲击。
4. 在一轮 smoke 和小规模正式重跑后，再决定是否启用模型可见收敛提醒。
5. 最后才考虑 Stage 4 只读工具批量执行。这个优化对运行效率有价值，但对评测可比性的影响更大，应该与正式 baseline 分开冻结。

## 8. 最小验收命令

实现 Stage 1 到 Stage 3 后，至少运行：

```bash
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_tools.py
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_context_manager.py tests/unit/test_pre_verl_agentloop.py
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_agent_loop_protocol.py tests/integration/test_pre_verl_agentloop_runtime.py
PATH=.venv/bin:$PATH python -m pytest -q
```

对 smoke 或正式 run 目录运行：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-model-visible-context RUN_DIR \
  --assert-no-hidden-test-material \
  --assert-prepared-messages-bound \
  --assert-provider-body-equivalent \
  --assert-tool-results-recoverable
```

新增一条专项检查命令或扩展现有 inspect：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-agentloop-progress RUN_DIR \
  --assert-search-status-unambiguous \
  --assert-initial-context-index-visible \
  --assert-loop-diagnostics-bound
```

如果暂时不新增命令，也必须在 `inspect-model-visible-context` 中加入等价断言：

1. `prepared_messages` 中包含冻结后的 `repository_context_index`。
2. 所有 `grep` tool result 都有 `result_kind` 和 `scan_complete`。
3. 不存在 `No matches.` 与扫描上限提示混合的模型可见文本。
4. no-progress 诊断事件的 artifact ref 和 transcript record 能互相追溯。
5. 新增上下文字段没有 hidden selector、hidden patch、gold patch、final verifier 原始输出或 evaluator-only artifact sha256。

还需要新增或扩展正式 freeze 检查。推荐命令形态如下：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-pre-verl-formal-freeze FORMAL_RUN_DIR \
  --assert-baseline-identity-bound \
  --assert-policy-versions-frozen \
  --assert-run-config-hashes-bound \
  --assert-run-matrix-baseline-consistent \
  --assert-exploratory-parent-not-merged
```

如果暂时不新增该命令，也必须用测试或脚本等价检查：

1. `pre_verl_agentloop_configuration_manifest.json`、`formal_budget_freeze_manifest.json`、`pre_verl_agentloop_run_config_manifest.json` 和 `pre_verl_agentloop_formal_run_matrix_manifest.json` 的 `baseline_id` 完全一致。
2. 所有 policy version 字段都存在且不为 `unknown`。
3. 所有 run config hash、task set hash、task definition hash、configuration manifest hash 都能被重新计算并匹配。
4. 旧的探索性 run 目录只出现在 `baseline_lineage`，不能出现在新 baseline 的指标分母或分子中。

## 9. 重新评测建议

Stage 1 和 Stage 2 完成后，建议先重跑以下任务作为 targeted smoke：

1. `pre_verl_dev_001_sqlfluff__sqlfluff_1625`：验证 `grep` 语义和源码入口上下文是否减少错误搜索。
2. `pre_verl_dev_014_pylint_dev__astroid_1333`：验证大量读取但不编辑的场景是否更快收敛。
3. `pre_verl_dev_015_pylint_dev__astroid_1196`：验证候选源码入口是否降低只读轮数。
4. `pre_verl_dev_017_pylint_dev__astroid_1268`：验证重复搜索诊断。
5. `pre_verl_dev_020_pydicom__pydicom_1413`：验证读取循环和临近预算提醒。

目标不是要求这些任务全部 accepted，而是观察：

1. 空补丁 `max_turns` 数量是否下降。
2. 首次编辑发生轮数是否提前。
3. `grep` 的 `partial_scan_no_match` 是否引导模型缩小 root 或 glob。
4. `loop_diagnostic` 是否能解释失败轨迹。
5. `model_visible_initial_context_hash`、`search_result_semantics_version`、`loop_progress_policy_version` 是否都被完整冻结。

完成 targeted smoke 后，再进入新的正式二十三题基线。旧的 `preparedstatefix` formal run 可以继续作为探索性证据，但不应该和启用这些改动后的结果合并计算 accepted rate。

## 10. 风险控制

1. 不要从 hidden selector、hidden patch、gold patch 或 final verifier 结果派生候选文件。候选入口只能来自公开 issue、模型可见源码索引和模型可见 task 字段。
2. 不要让 no-progress 提醒泄漏 verifier 结论。提醒只能描述 loop 行为，例如“连续只读”“重复搜索”“剩余轮数少”，不能描述隐藏测试。
3. 不要在正式 baseline 中临时启用 side model 做上下文选择，除非把 side model 本身也纳入可审计评测配置。
4. 不要把 `no_progress` 硬停止作为第一版默认策略。先记录诊断和 metrics，再根据 targeted smoke 的证据决定是否启用。
5. 不要把 Stage 4 并发优化和 Stage 1 到 Stage 3 混在同一 baseline 中，否则很难判断 accepted rate 变化来自上下文、工具语义还是执行时序。

## 11. 完成定义

这轮专项改进完成后，应能回答以下问题：

1. 模型看到一个搜索无结果时，能否明确知道这是完整无匹配还是部分扫描无匹配？
2. 首轮 prompt 是否给出了安全、可审计、足够有用的仓库入口，而不是只给 README 和 CONTRIBUTING？
3. 当模型连续多轮只读探索但没有补丁时，events、transcript 和 metrics 是否能证明 harness 已经识别并提示收敛？
4. 如果最终仍是空补丁，failure taxonomy 是否能区分模型没产出、预算耗尽、no-progress、provider/model 错误和 harness 错误？
5. 新 baseline 的 manifest 是否冻结了所有会改变模型输入和工具反馈的策略版本？

只有这五个问题都可以用本地 artifact 直接回答，才建议把下一轮正式二十三题结果作为简历展示和 RL 训练前可靠性证据。
