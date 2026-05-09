# 工业级 Agent Harness 设计审查

## 审查范围

本次审查目标是判断 RepoHarness 在正式实现前是否具备足够完整、可实现、可扩展的 agent harness 设计，尤其是它是否能够支撑真实或半真实软件工程任务中的 agent 运行、轨迹采集、验证器评测、奖励元数据生成，以及后续监督微调和强化学习数据导出。

本次审查阅读了以下材料：

- `docs/00-reading-guide.md` 到 `docs/12-resume-narrative-and-demo-artifacts.md`。
- `docs/review/01-architecture-review.md` 到 `docs/review/06-external-review-followup.md`。
- `reference/claude-code-typescript-src/AGENT.md`。
- `reference/claude-code-typescript-src/Tool.ts`、`query.ts`、`QueryEngine.ts`、`tools.ts`、`services/tools/toolExecution.ts`、`services/tools/toolOrchestration.ts`、`utils/permissions/permissions.ts`、`tools/BashTool/bashPermissions.ts`、`tools/BashTool/bashSecurity.ts` 等关键源码。
- `reference/claude-code-docs/claude-doc/06-agent-and-multi-agent.md`、`07-hooks-system.md`、`08-mcp-integration.md`、`10-context-memory-session.md` 等参考文档。
- 公开技术趋势抽样，包括 Cursor Composer 2、Qwen3-Coder、Qwen3-Coder-Next、GLM-4.5、KAT-Coder-V2 等报告或官方说明，用来校验“可执行环境、工具轨迹、验证器奖励、训练评测一致性”这些方向是否仍然是当前主线。

## 总体结论

RepoHarness 当前设计不是玩具级设计。它已经抓住了工业级 agent harness 最核心的不变量：统一 agent loop、结构化工具契约、工具结果回流、权限和执行边界分离、baseline / feedback / final verifier 分离、transcript 和 events 分离、final verifier 驱动评测与奖励元数据、可替换 scaffold、运行产物和训练导出。

如果项目定位是“面向训练和评测的第一版软件工程 agent harness”，当前 00 到 12 号文档的架构方向是成立的，也没有发现会导致未来根本执行不起来的根本性设计矛盾。它比普通 demo 更接近一个可以逐步工程化的基础设施设计。

但是，如果目标是在正式实现后承接更真实、更长轨迹的软件工程任务，目前仍有若干关键契约需要在编码前补齐。主要风险不是“方向错了”，而是一些目前写成原则的模块还没有变成足够确定的实现接口。最需要补的是 Model Client、Context Builder、Verifier Parser、Trajectory Recorder、Artifact Manifest、工具调用配对规则、命令与网络安全策略、训练导出损失掩码和 schema versioning（数据结构版本管理）。

建议结论是：可以开始实现准备和非核心骨架，例如数据对象、配置读取和只读工具原型；但不建议在关键契约未补齐时直接写长轨迹 agent loop、批量训练导出和真实仓库任务运行。下文的高优先级问题可以分成两类：Model Client、Context Builder、工作区生命周期、BaselineResult 所有权、Recorder 所有权、tool call / tool result 配对规则，属于最小运行时前就应补齐的契约；artifact manifest、训练导出损失掩码、数据脱敏、复杂命令策略和网络审计，属于进入真实仓库、批量评测和训练导出前必须补齐的契约。

## 与工业级参考实现的对照

| 参考实现中的关键设计 | RepoHarness 当前覆盖情况 | 审查判断 |
| --- | --- | --- |
| 统一查询循环，模型输出工具调用，工具结果回流下一轮 | `docs/03` 已覆盖 | 方向正确，需要补充 tool call 和 tool result 配对不变量的异常处理规则。 |
| QueryEngine 或无界面宿主与 turn-level loop 分离 | `docs/02`、`docs/03`、`docs/11` 提到 CLI（命令行接口）/ Eval Runner 与 Agent Loop | 概念覆盖，但缺少 Model Client 和无界面输出契约。 |
| Tool 是能力契约，不是普通函数列表 | `docs/04` 已覆盖 | 覆盖较好，建议补 `ToolExecutionContext` 和稳定工具排序。 |
| 工具执行管线包含 schema 校验、工具级校验、权限、执行、结果映射、输出持久化、事件记录 | `docs/04` 已覆盖主链路 | 方向正确，需要明确 Recorder 由谁写入、artifact 如何引用、异常和中断如何生成 tool result。 |
| 并发只允许明确安全的工具 | `docs/02`、`docs/04` 已覆盖 | 覆盖较好。 |
| 权限系统与 sandbox 分离 | `docs/05` 已覆盖 | 覆盖较好，但权限判定优先级、命令解析、网络策略和非交互 ask 模式还需要更具体。 |
| Bash 安全需要命令解析、重定向处理、危险模式识别和工作区路径约束 | `docs/05` 只写了规则列表 | 第一版可以比 Claude Code 简化，但不能只靠字符串包含判断。需要设计最小命令策略。 |
| 工作区生命周期、diff 捕获、setup 与 agent 修改隔离 | `docs/06` 和 `docs/11` 已覆盖三阶段；`docs/05` 仍较旧 | 存在局部文档不一致，应修订。 |
| 上下文管理和工具输出预算 | `docs/10` 已覆盖简单策略 | 第一版可接受，但建议把 token budget、preview 和 artifact 的关系写成配置对象。 |
| 会话恢复 | `docs/10` 已保守降级为从 final workspace 继续 | 设计正确，不夸大能力。 |
| 子代理复用同一套 loop | `docs/09` 已覆盖为原则 | 第一版不做后台多代理是合理边界。 |
| MCP（Model Context Protocol，模型上下文协议）、插件、技能、hooks、远程会话、终端界面 | 当前明确不做 | 对训练和评测 harness 第一版可以不做，但建议保留内部生命周期回调或事件总线，不需要产品级插件系统。 |
| 轨迹、事件、运行产物、评测指标 | `docs/08` 已覆盖 | 方向正确，需要补 artifact manifest、schema version、event id、幂等写入和数据脱敏。 |
| 验证器和奖励元数据 | `docs/07` 已覆盖 | 核心思想正确，但 verifier parser 和测试用例级结果 schema 还不够具体。 |
| 训练导出 | `docs/08` 已覆盖三类 JSONL | 方向正确，但缺少监督微调损失掩码、完整 reward metadata 引用、schema version 和多 rollout 配置。 |

## 已经设计得比较好的部分

### 1. 项目定位清楚，没有过度声称

文档明确说第一阶段是设计文档和 Python 骨架，不声称已经实现可运行的 agent loop、生产级安全沙箱、完整强化学习训练、完整 SWE-Bench 复现或 Claude Code 复刻。这一点非常重要，因为它让项目叙事可信，也避免后续实现被迫承担过大的范围。

### 2. 训练和评测一致性是主线

`docs/07` 明确要求训练奖励元数据和离线评测共用 final verifier，这符合当前 agentic coding 训练报告中的主线：模型必须在可执行环境中行动，最终结果必须由同一套环境反馈和验证器来评估。

### 3. transcript 和 events 分离是正确的数据设计

transcript 用于对话重放，events 用于统计、诊断、奖励元数据和训练导出。这个分离避免了把展示文本当成唯一事实来源，是从 demo 走向可训练数据资产的关键一步。

### 4. 工作区、setup、baseline 和 agent 修改已经有三阶段意识

`docs/06` 和 `docs/11` 已经把 source checkout、setup workspace、agent run workspace 区分开，并要求 final diff 只统计 agent 从 `agent_start_snapshot` 之后的改动。这是非常关键的训练数据卫生设计。

### 5. scaffold 的边界克制

第一版只做 single-shot、simple ReAct、planner-coder-verifier 三类 scaffold，并把 planner-coder-verifier 定义为顺序式多角色策略，而不是复杂后台多代理系统。这个边界是健康的，能避免第一版被远程代理、mailbox、worktree 分叉拖垮。

## 高优先级问题和建议修改

### P0-1：缺少独立的 Model Client 和工具调用协议适配层

当前 `docs/02` 和 `docs/11` 已经把 Model Client 当作模块关系提到，但还没有把它定义为独立接口。`docs/03` 用 `call_model(messages, tools)` 表示模型调用，`docs/11` 只有 `ModelMessage`，没有 `ModelClient`、`ModelResponse`、`ToolCallParser`、`TokenUsage`、模型错误、重试、限流、fallback、流式与非流式输出等契约。

这会在实现时造成一个直接问题：Agent Loop 很容易被某个模型供应商的消息格式绑住。后续如果要导出监督微调或者强化学习轨迹，也会不清楚哪些字段是模型原始输出，哪些字段是 harness 标准化后的动作。

建议补充一个最小接口：

```text
ModelClient.generate(messages, tools, model_config) -> ModelResponse

ModelResponse:
  assistant_message
  tool_calls
  raw_provider_response_path
  token_usage
  finish_reason
  model_error_type
  provider_request_id
```

同时定义：

- `ToolCallParser`：把不同供应商或不同工具调用格式标准化为 `ToolCall`。
- `ModelErrorType`：例如 `rate_limited`、`auth_error`、`context_limit`、`invalid_response`、`provider_error`。
- `ModelCallEvent`：记录模型、输入 token、输出 token、耗时、错误类型、重试次数。
- 原始响应可以落盘，但训练导出默认使用标准化后的 message 和 tool call。

### P0-2：缺少 Context Builder，也就是初始上下文构造契约

工业级 coding agent 不只是把 issue 直接塞给模型。参考实现会构造系统提示词、用户上下文、当前日期、工作目录、Git 状态、项目指令文件、工具规则和权限模式。RepoHarness 文档目前有 context/session 章节，但缺少一个明确的 Context Builder。

建议在 `docs/03` 或 `docs/11` 中增加 `ContextBuilder`：

```text
ContextBuilder.build_initial_messages(task, workspace, run_config, scaffold)
```

它至少负责：

- 注入 task issue statement。
- 注入仓库根目录、语言、测试命令和允许工具。
- 可选注入 `README`、`AGENT.md`、`CLAUDE.md`、`CONTRIBUTING.md` 等项目说明文件的摘要或路径。
- 注入当前日期、执行模式、权限模式和预算。
- 记录 `prompt_template_version`、`context_builder_version` 和上下文截断策略。
- 明确区分 `agent_visible_context` 和 `evaluator_only_metadata`。`gold_patch`、隐藏测试、评测答案、奖励元数据、baseline 原始验证细节默认不能进入模型上下文，也不能通过普通工具输出泄漏给模型。

这样可以避免不同 scaffold 各自拼 prompt，导致评测和训练数据不可比较。

### P0-3：工作区生命周期在不同文档中仍有轻微不一致

`docs/06` 和 `docs/11` 已经采用 source checkout、setup workspace、agent run workspace 三阶段设计；但 `docs/05` 的 workspace 生命周期仍然像单一工作区流程，容易让实现者把依赖安装、baseline verifier 和 agent 修改混在一起。

建议把所有文档统一成以下口径：

```text
source checkout
  -> setup workspace
      -> setup command
      -> baseline verifier
      -> dependency_state
  -> agent run workspace
      -> restore dependency_state
      -> agent_start_snapshot
      -> agent loop
      -> final verifier
      -> final.diff from agent_start_snapshot
```

同时明确 `BaselineResult` 的所有权：

- Task Adapter 负责读取、校验、规范化任务定义，并解析仓库来源、基准提交、issue statement、setup command、test command 和 verifier 配置，输出 `RunnableTask` 和 `VerifierConfig`。
- Eval Runner 调用 Workspace Adapter 和 Verifier 生成 `BaselineResult`。
- Eval Runner 根据 `BaselineResult.status` 决定是否进入正式 agent run。
- Trajectory Store 保存 baseline artifact，但 baseline 日志不进入正式 agent action-observation 轨迹。

### P0-4：Verifier Parser 还不够具体

当前 `VerifierResult` 是正确的高层结构，但还不足以支撑 fail-to-pass、pass-to-pass、flaky 检测和跨语言任务。只保存整体 `exit_code` 和 `pass_ratio` 会让后续 reward 和 metrics 失去可审计基础。

建议新增 `TestCaseResult` 和 `VerifierParser` 契约：

```text
TestCaseResult:
  test_id
  status: passed | failed | skipped | error | timeout | unknown
  duration_ms
  failure_preview
  raw_output_path

VerifierResult:
  parser_id
  parser_version
  parser_confidence
  command
  exit_code
  timeout
  test_cases
  fail_to_pass
  pass_to_pass
  accepted
  error_type
```

第一版可以只实现 `pytest` parser，但文档应说明：

- 无法解析测试用例时，`parser_confidence` 降低，不能伪造 fail-to-pass 统计。
- 测试命令本身崩溃属于 `test_command_error` 或 `dependency_error`，不是普通断言失败。
- baseline 可以配置重复运行次数，用于发现 flaky。
- final verifier 是 reward metadata 和 export 的默认来源。

### P0-5：Trajectory Store 需要统一 Recorder 接口和 artifact manifest

目前文档中有时说 Tool System 写 transcript 和 events，有时说 Trajectory Store 保存 transcript 和 events。实现时应避免每个模块自己打开文件追加 JSONL。

建议定义统一的 `RunRecorder` 或 `TrajectoryStore`：

```text
recorder.append_transcript(record)
recorder.append_event(event)
recorder.write_artifact(kind, bytes_or_path, metadata) -> ArtifactRef
recorder.finalize_run(summary)
```

同时给每个 run directory 增加 `manifest.json` 或 `artifacts.json`：

```text
ArtifactRef:
  artifact_id
  relative_path
  kind
  sha256
  size_bytes
  created_by_event_id
  redaction_status
  retention_policy
```

这样 events、transcript、verifier、training export 都可以引用同一份 artifact，而不是散落路径字符串。对于训练数据，这一点尤其重要，因为后续需要知道某条 observation 的完整日志、diff 或 verifier 原始输出来自哪里。

### P0-6：需要明确 tool call 和 tool result 配对不变量

参考实现中一个非常重要的不变量是：每个 assistant tool_use 都必须有对应的 user tool_result。中断、流式失败、fallback、未知工具和 schema 错误都要生成合成 tool_result，否则下一轮模型请求、会话恢复和训练重放都会出问题。

RepoHarness 文档已经说工具结果必须回流，但还没有把异常配对规则写清楚。

建议补充：

- 未知工具名也要生成 `ToolResult(status = "error", error_type = "unknown_tool")`。
- schema 校验失败也要生成 `ToolResult(status = "error", error_type = "schema_validation_failed")`。
- 权限拒绝也要生成 `ToolResult(status = "denied")`。
- 工具超时也要生成 `ToolResult(status = "timeout")`。
- agent 被中断时，已经发出的 tool call 必须补齐 `interrupted` 或 `cancelled` tool result。
- transcript 中不得出现孤立 tool call。

### P0-7：命令安全、测试路由和网络策略需要从规则列表升级为最小策略

`docs/05` 已列出 `rm -rf`、`sudo`、`ssh`、`scp`、`curl | sh` 等默认拒绝项，但真实 agent 任务中最容易出问题的不是这几个字符串，而是组合命令、重定向、子命令、网络访问、包安装和 benchmark 泄漏。

建议第一版定义一个保守命令策略：

- 权限判定顺序必须确定，建议至少包含：显式 deny 规则、显式 ask 规则、工具自身 `check_permissions`、不可绕过的内容级安全检查、权限模式、整工具 allow 规则、最终 ask 或 deny。
- `run_tests` 只执行任务定义中的测试命令，或者由配置允许的测试子集命令。
- `bash` 只能执行诊断命令和受限只读命令，不能把可识别测试结果计入 reward。
- setup 阶段可以按任务配置允许网络，agent run 阶段默认关闭或强限制网络。
- 默认拒绝 `git clone`、`git fetch`、`git pull`、`git remote add`、`curl`、`wget`、`ssh`、`scp`、`sudo`、写 home directory、访问 workspace 外路径。
- 如果未来允许网络，必须记录 `network_policy`、允许域名、命令、时间和输出。
- 命令解析至少要处理工作目录、环境变量、重定向和 shell compound command；第一版可以保守地把复杂命令直接拒绝或要求显式 allowlist。

这不是为了声称生产级安全，而是为了保证训练评测可复现，并降低 reward hacking 和未来 commit 泄漏风险。

### P0-8：训练导出需要损失掩码、完整奖励元数据和数据结构版本

当前 `docs/08` 的导出样例已经覆盖监督微调、强化学习 rollout 和 preference pair，但它还不够训练工程化。监督微调时并不是所有消息都应该作为 label；强化学习 rollout 也需要区分 prompt、action、observation、final reward、invalid sample 原因。

建议增加：

- `schema_version`：例如 `repo_harness_export_v0`。
- `export_policy_version`：说明过滤规则和消息选择规则。
- `loss_mask` 或 `trainable_messages`：标明哪些 assistant 消息参与监督微调损失。
- `observation_mask`：标明 tool result 是环境观察，不作为模型生成目标。
- `reward_metadata` 必须完整内嵌，或提供 `reward_metadata_path` 和 sha256。
- `invalid_for_training` 和 `invalid_reason` 必须进入 export record。
- preference pair 需要记录 `pairing_policy`、同任务多 rollout 来源、chosen / rejected 的 verifier 依据。

如果后续接入强化学习框架，这些字段比最终 patch 文本更重要。

## 中优先级建议

### P1-1：补充确定性的 run outcome 派生表

目前三层结论已经拆开：`agent_stop_reason`、`final_verifier_status`、`run_outcome`。建议再加一张机器可读派生表。例如：

| 条件 | run_outcome |
| --- | --- |
| baseline invalid | `invalid_task` |
| baseline flaky | `flaky_task` |
| final verifier accepted | `success` |
| final verifier failed | `failed` |
| final verifier timeout 且无可解析测试结果 | `inconclusive` 或 `failed`，需要项目明确 |
| agent timeout 但 final verifier accepted | `success`，并保留 stop reason 为 `timeout` |
| permission denied 后无进一步行动且 final verifier failed | `failed` |

这张表会直接影响 metrics 和训练过滤，建议放在 `docs/03` 或 `docs/10`。

### P1-2：补充 Scaffold 接口

`docs/09` 对 scaffold 的描述是正确的，但还没有实现者可以直接照着写的接口。建议定义：

```text
Scaffold:
  scaffold_id
  build_system_prompt(task, run_config)
  build_initial_messages(task, workspace_context)
  allowed_tools(turn_state)
  handle_tool_result(tool_result, state)
  handle_verifier_feedback(verifier_result, state)
  should_stop(state)
```

这样 single-shot、simple ReAct、planner-coder-verifier 可以复用同一套 Agent Loop。

### P1-3：补充 ToolExecutionContext

参考实现的 `ToolUseContext` 很丰富。RepoHarness 不需要复制产品状态，但需要最小上下文对象：

```text
ToolExecutionContext:
  run_id
  task_id
  workspace_facade
  artifact_writer
  permission_context
  verifier_feedback_facade
  abort_signal
  output_limits
  tool_policy
```

这里的关键不是让工具拿到所有内部对象，而是给工具受限 facade。普通文件和命令工具只能通过 `workspace_facade` 和 `artifact_writer` 操作工作区与 artifact；只有 `run_tests` 这类验证器入口工具才应该拿到 `verifier_feedback_facade`。这样工具不会各自拿全局变量，也不会绕过 Workspace Adapter、Verifier 和 Recorder 的边界。

### P1-4：补充 edit / patch 的并发和陈旧读取保护

如果模型先读文件再编辑，文件可能被前一个工具修改。即使第一版没有用户并发编辑，也可能有多工具顺序修改。建议让 `write_file` 和 `apply_patch` 支持：

- `expected_content_hash`。
- `expected_old_text`。
- patch apply failure 的结构化错误。
- 未跟踪文件、二进制文件、符号链接的处理规则。

### P1-5：补充进程清理和 timeout 语义

命令 timeout 不能只返回状态，还要说明如何停止进程树、如何处理后台进程、如何保存 stdout / stderr、容器如何清理、final verifier 是否还能继续运行。

建议新增：

- 工具 timeout。
- 单任务全局 timeout。
- verifier timeout。
- process group kill。
- container cleanup。
- interrupted artifact 记录。

### P1-6：补充数据脱敏和 secret scanning

如果未来使用真实仓库或真实 issue，训练导出必须避免泄露密钥、令牌、私有路径和用户数据。建议在 `docs/08` 增加：

- artifact 写入前或导出前运行 secret scan。
- export record 带 `redaction_status`。
- 被脱敏字段保留占位符和原因。
- 默认不导出 `.env`、证书、私钥、token 文件。

### P1-7：补充 stable tool ordering 和 tool policy version

参考实现中工具排序会影响 prompt cache。RepoHarness 第一版不一定做 prompt cache，但稳定工具顺序仍然有利于复现实验。建议记录：

- `tool_policy_version`。
- `allowed_tools`。
- `tool_order`。
- `permission_policy_version`。

### P1-8：补充批量评测的幂等性和并发安全

当前 evaluation concurrency 默认为 1，这适合作为第一版。但后续一旦并发运行，需要：

- run_id 唯一生成规则。
- 原子写 JSONL 或单 writer recorder。
- run directory lock。
- 重跑同一任务时的覆盖策略。
- 失败半成品如何标记。

### P1-9：补充无界面命令行输出和退出码

RepoHarness 面向训练和评测，不需要交互界面，但需要稳定的无界面命令行接口。建议定义：

- 单任务运行命令的 stdout JSON 或 summary path。
- 批量评测命令的 aggregate metrics path。
- exit code 语义，例如配置错误、无效任务、运行失败、部分任务失败。
- `--json` 或 `--output-dir` 的稳定行为。

### P1-10：为 LSP、语义搜索和诊断工具预留扩展点

第一版只做 `read / search / edit / bash / run_tests` 是合理的。但工业级 coding agent 往往会引入 LSP（Language Server Protocol，语言服务器协议）诊断、符号搜索、语义搜索和代码索引。建议只在工具 registry 中预留工具类别，不必第一版实现。

### P1-11：增加统一 Budget Manager

当前文档分散提到了 `max_turns`、`max_tool_calls`、timeout、最大工具输出字符数和模型 token，但还没有一个统一预算对象。工业级 agent runtime 中，预算不是附属字段，而是控制长轨迹是否可控、是否可复现、是否适合训练导出的核心状态。

建议增加 `BudgetState` 或 `BudgetManager`：

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

每一种预算耗尽都应产生确定的 event，并映射到明确的 `agent_stop_reason` 或 `run_outcome`。例如，工具调用次数耗尽是 `max_tool_calls`，最终验证器超时是 `final_verifier_status = "timeout"`，二者不应该混成同一个普通失败。

### P1-12：区分训练轨迹和运行时遥测

RepoHarness 的核心数据是 training trajectory，但实现时仍会需要 operational telemetry，也就是调试运行时用的日志、性能计时和错误上下文。两者不应混成一套字段。

建议文档明确：

- transcript 和 events 是训练、评测、诊断的事实数据。
- operational telemetry 可以用于本地调试，但默认不进入训练导出。
- telemetry 需要可关闭，且不能包含未脱敏的密钥、私有路径或大段源码。
- transcript、events、verifier、metrics 和 export records 都应带 `schema_version`。
- event 类型本身也应有版本或兼容策略，避免未来字段变化破坏历史训练数据。

### P1-13：明确测试和诊断命令产生的临时文件如何处理

`run_tests`、lint、type check、coverage 或构建命令可能生成 `.pytest_cache`、`.coverage`、coverage 报告、构建缓存、临时日志和语言包管理器缓存。文档已经要求 dependency setup 产物默认排除，但还应明确正式 agent run 期间这些临时文件的处理规则。

建议补充：

- 测试缓存和诊断缓存默认不进入 `final.diff` 和训练 patch。
- 如果测试命令生成了重要日志，应保存为 artifact，并由 event 引用。
- 如果任务本身要求修改生成文件或快照文件，必须在 task schema 中显式声明。
- `excluded_diff_paths` 应同时适用于 setup 阶段和 agent run 阶段的测试缓存。

## 第一版可以合理不做的能力

以下能力在 Claude Code 等产品级实现中很重要，但对 RepoHarness 第一版训练评测目标不是必需项。文档当前选择不做是合理的：

- 终端交互界面、键盘快捷键、状态栏、消息选择器。
- 完整插件市场、技能系统、MCP 生态和用户命令系统。
- 远程会话、移动端桥接、后台云代理和企业权限回调。
- 复杂自动记忆、跨会话长期记忆和完整自动压缩系统。
- 多代理 swarm、mailbox、远程 teammate、自动 worktree 分叉。
- 生产级安全沙箱、对抗性隔离、多租户 Kubernetes 安全平台。
- 大规模异步 rollout 集群和训练调度系统。

但是，第一版文档最好保留内部扩展点，例如 `ToolRegistry`、`ScaffoldRegistry`、`VerifierRegistry`、`TaskAdapterRegistry` 和 `Recorder`，这样后续扩展不会重写核心 loop。

## 是否存在根本设计矛盾

没有发现根本设计矛盾。当前发现的问题都属于“需要补充契约或统一口径”，不是“架构方向无法实现”。

需要修正的局部矛盾主要有四个：

1. `docs/05` 的 workspace 生命周期仍像单工作区流程，而 `docs/06` 和 `docs/11` 已经是三阶段流程。
2. `BaselineResult` 的生成责任在不同文档中写法不完全一致。
3. `RewardMetadata` 要求完整可审计，但训练导出样例有时只保留了简化字段。
4. Tool System 和 Trajectory Store 的写入责任还需要统一到 Recorder 接口。

这些都很容易通过文档修订解决，不会推翻项目主线。

## 建议的实现前修订清单

建议在正式编码前完成以下文档修改：

1. 在 `docs/03-agent-loop-and-message-protocol.md` 增加 Model Client、ModelResponse、tool call parser、tool call / tool result 配对规则。
2. 在 `docs/03` 或 `docs/11-object-model-config-and-data-flow.md` 增加 Context Builder。
3. 在 `docs/05-workspace-sandbox-and-permissions.md` 统一三阶段 workspace 生命周期，并补网络策略和命令策略。
4. 在 `docs/06-task-dataset-and-environment-adapters.md` 明确 BaselineResult 由 Eval Runner 协调 Workspace Adapter 和 Verifier 生成。
5. 在 `docs/07-verifier-reward-and-evaluation.md` 增加 VerifierParser、TestCaseResult、parser confidence、flaky 重跑策略。
6. 在 `docs/08-trajectory-store-and-training-export.md` 增加 Recorder、artifact manifest、schema version、secret scanning、损失掩码、完整 reward metadata 引用。
7. 在 `docs/09-agent-scaffolds-and-multi-agent.md` 增加 Scaffold 接口。
8. 在 `docs/10-context-session-and-failure-diagnostics.md` 增加 run outcome 派生表、timeout 清理语义和上下文预算配置。
9. 在 `docs/11` 的核心对象表中补 `ModelClient`、`ModelResponse`、`ContextBuilder`、`ToolExecutionContext`、`VerifierParser`、`TestCaseResult`、`ArtifactRef`、`RunRecorder`、`BudgetManager`、`ExportPolicy`。

## 建议的第一版实现顺序

修订完成后，建议按以下顺序实现，风险最低：

1. 数据对象和 schema：`RunConfig`、`TaskDefinition`、`RunnableTask`、`RunWorkspace`、`ToolCall`、`ToolResult`、`TrajectoryEvent`、`VerifierResult`。
2. `RunRecorder`：先能稳定写 transcript、events、artifact manifest、summary。
3. Workspace Adapter：只做 local process mode、路径边界、输出落盘、diff 捕获。
4. Task Adapter：只支持 micro-repo YAML tasks。
5. Verifier：只支持 `pytest` parser，跑 baseline、feedback、final 三条路径。
6. 只读工具：`list_files`、`read_file`、`search`、`git_diff`。
7. 写工具：`apply_patch`，先不要急着做全量 `write_file`。
8. `run_tests` 工具：只路由到 Verifier feedback path。
9. Model Client：先接一个供应商，内部立刻标准化为 `ModelResponse`。
10. simple ReAct scaffold：先跑 3 到 5 个 micro-repo tasks。
11. metrics 和 export：先生成监督微调 JSONL 与强化学习 rollout JSONL。
12. 再加入 single-shot baseline 和 planner-coder-verifier scaffold 做对比。

## 最终判断

当前 RepoHarness 设计可以被评价为“训练和评测导向的工业级 agent harness 初版设计”，但还不能评价为“已经决策完整到可以直接大规模实现的工业级运行时规格”。它的核心方向是正确的，架构边界也是健康的；需要补的是实现契约、数据血缘、验证器解析和训练导出细节。

只要在正式实现前补齐上述 P0 项，RepoHarness 就具备清晰的演进路径：第一版先跑通单机 micro-repo 闭环，第二版扩展任务集和 Docker execution mode，第三版再接入更多 scaffold、更多 verifier、更强数据导出和更真实的 repository-level tasks。

## 外部趋势参考

以下链接只作为当前技术趋势的外部佐证，不作为 RepoHarness 本地设计正确性的唯一依据。访问日期为 2026-04-29。

- Cursor Composer 2 技术报告说明其训练强调真实 Cursor harness、一致工具结构、真实问题环境和大规模强化学习，这与 RepoHarness 的训练评测一致性目标相符：https://cursor.com/blog/composer-2-technical-report
- Composer 2 arXiv 摘要强调同一 harness 用于训练和部署，以及长程真实软件工程问题：https://arxiv.org/abs/2603.24477
- Qwen3-Coder 官方说明强调 execution-driven code reinforcement learning、long-horizon agent reinforcement learning 和大规模独立环境：https://qwenlm.github.io/blog/qwen3-coder/
- Qwen3-Coder-Next arXiv 摘要强调可验证 coding tasks、executable environments 和 environment feedback：https://arxiv.org/abs/2603.00729
- GLM-4.5 arXiv 摘要强调 agentic、reasoning、coding 综合能力和强化学习后训练：https://arxiv.org/abs/2508.06471
- KAT-Coder-V2 arXiv 摘要强调 KwaiEnv、sandbox、scaffold generalization 和大规模轨迹训练：https://arxiv.org/abs/2603.27703
