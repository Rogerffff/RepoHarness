# 正式 smoke 和二十三题 pre-verl 测评前修复实施计划

本文档用于回答一个具体问题：在已经完成第一轮 AgentLoop hardening 之后，正式 smoke 和正式二十三题 pre-verl 测评开始前，还需要完成哪些修复、冻结哪些限制、跑哪些验收检查。

结论是：`docs/resume/pre-verl-claude-code-harness-gap-analysis.md` 中的 `6.1 正式 pre-verl 测评前建议完成或冻结` 应该作为本轮 readiness backlog 使用，但不需要把其中每一项都做成 Claude Code 级别的完整产品能力。正确边界是：

1. 会直接污染模型可见上下文、provider 输入、final verifier 归因、accepted rate 或训练导出判断的内容，必须在正式 smoke 前修复。
2. 暂时不实现但会影响解释口径的能力，必须在正式 smoke 前写入 freeze manifest、run metadata 或正式报告的 known limitations，不能让评测读者误以为它已经具备。
3. 只提升产品体验、并发效率、交互能力或长期扩展能力的内容，不阻塞本轮二十三题测评。

## 1. 本计划的输入依据

本计划基于以下已有文档和本轮 review finding：

1. `docs/resume/pre-verl-agentloop-harness-hardening-implementation-plan.md`
2. `docs/resume/pre-verl-claude-code-harness-gap-analysis.md`
3. `docs/resume/pre-verl-verifier-agent-evaluation-plan.md`
4. 本轮代码审查识别出的四个剩余 hardening 问题：
   - `inspect-model-visible-context` 对真实 AgentLoop run 的 `prepared_messages_ref` 绑定误报。
   - task timeout 到达 final verifier 前时，没有强制传递给 pre-verl final verifier。
   - evaluator-only 或敏感 artifact 的 context replacement 仍把原始 `sha256` 暴露给模型。
   - `context_integrity_error` 导致的空补丁会被归因为 `model_no_patch_generated`。

## 2. 测评前阻塞范围

正式 smoke 前必须收口的内容分为三类。

第一类是本轮 review finding 的修复。它们不是 Claude Code gap 文档中的长期增强，而是当前 hardening 修复本身的正确性问题。只要这些问题未修复，新的 inspect 和 final verifier boundary 就不能作为正式 readiness gate 使用。

第二类是 gap 文档 `6.1` 中的最小可执行闭环。这里的目标不是补齐完整产品能力，而是避免真实 provider 测评时因为 provider 失败、输出截断、工具调用格式错误、权限策略漂移、预算记录不清、入口不一致或初始上下文缺失，把 Harness 问题误判为模型能力不足。

第三类是正式测评口径冻结。凡是本轮不做的能力，都必须在 `run_config_facts`、readiness report 或正式测评报告里明示，不能被默认解释成已经支持。

这里需要特别区分两个门槛：

1. `进入 smoke 的门槛`：要求本轮 hardening 证据本身可信，mock / fake 异常路径可验证，真实 `run-task` 产物能通过模型可见上下文检查。
2. `把二十三题结果标记为正式结果的门槛`：除了 smoke 通过，还要求二十三题 TaskDefinition、final verifier boundary index、accepted rate 分母、failure taxonomy、command lineage、public-safe scan 和 export readiness 全部通过。

## 3. Stage A：先修复当前四个 review finding

### A1. 修复 `inspect-model-visible-context` 对真实 run 的误报

问题：真实 AgentLoop 的 `model_call_started` 事件把 `prepared_messages_ref` 放在 `artifact_refs`，但 `inspect_model_visible_context(..., assert_prepared_messages_bound=True)` 只查 `event.data.prepared_messages_ref`。

实施要求：

1. 在 `model_call_started.data` 中显式写入 `prepared_messages_ref`，或者让 inspect 同时支持从 `event.artifact_refs` 中识别 `kind=prepared_messages` 的 artifact。
2. 建议优先同时做两件事：AgentLoop 显式写入 `data.prepared_messages_ref`，inspect 兼容历史 run 的 `artifact_refs`。
3. 新增真实 `repo-harness run-task` 集成测试，不能只用手写事件 fixture。

验收检查：

```bash
PATH=.venv/bin:$PATH repo-harness run-task tests/fixtures/tasks/task_001.yaml --config tests/fixtures/run_configs/replay_success.yaml --output-dir /tmp/repo-harness-readiness-runs --run-id readiness-model-visible-bind
PATH=.venv/bin:$PATH repo-harness inspect-model-visible-context /tmp/repo-harness-readiness-runs/readiness-model-visible-bind --assert-prepared-messages-bound
```

### A2. 修复 final verifier 前 task timeout 的归因边界

问题：`evaluation/runner.py` 已经发现 `task_timeout_expired=true` 时，仍可能把 `loop_state.agent_stop_reason` 原样传给 pre-verl final verifier。如果这个 stop reason 是 `final_answer`、`max_turns` 或其他非 timeout 值，final verifier 会继续执行隐藏测试链路。

实施要求：

1. 当 `task_timeout_expired=true` 且使用 pre-verl runtime plan 时，传给 `run_pre_verl_swebench_dev_final_verifier` 的原因必须强制为 `task_timeout`，或者新增独立参数 `task_timeout_expired=True`。
2. boundary 必须记录：
   - `failure_category=task_timeout_before_final_verifier`
   - `failure_owner=budget_or_timeout`
   - `final_verifier_status=not_executed`
   - `final_verifier_ran=false`
3. 这种 run 不能应用 hidden test patch，也不能运行 fail-to-pass 或 pass-to-pass selector。

验收检查：

1. 构造 agent 已经给出 final answer，但 final verifier 前 wall-clock timeout 已过期的 pre-verl run。
2. 检查 `final_verifier_boundary.json` 的 `observed_command_order` 不包含 hidden test patch apply、fail-to-pass 和 pass-to-pass。
3. 检查 metrics 的 `run_outcome=inconclusive`，不能是 `failed` 或 `success`。

### A3. 隐藏或敏感 artifact 的 replacement 不得暴露原始 sha256

问题：context replacement 已经隐藏 `artifact_id` 和 `kind`，但仍把 evaluator-only、secret、credential 或 provider_raw artifact 的原始 `sha256` 写进模型可见文本。

实施要求：

1. 当 `safe_artifact_data.redacted=true` 时，模型可见 replacement 中不能包含原始 `sha256`。
2. 可以使用固定占位值，例如 `sha256: redacted_sensitive_artifact_sha256`，也可以完全省略 `sha256` 行。
3. replacement artifact 中也不能保留敏感 artifact 的原始 sha256，除非该 artifact 明确是 evaluator-only 审计 payload 且不会进入模型可见 prepared messages。为了降低误用风险，建议 replacement artifact 也使用占位值。
4. `inspect-model-visible-context --assert-no-hidden-test-material` 应覆盖此类泄漏，至少检查 evaluator-only artifact ref 的 sha256 不出现在 prepared messages、transcript model-visible fields 和 raw provider request messages 中。

验收检查：

1. 对 evaluator-only artifact 构造 context replacement。
2. prepared messages 中应该出现 `preview_redacted`，不应该出现原始 artifact id、kind、path、hidden selector 内容或原始 sha256。
3. `inspect-model-visible-context --assert-no-hidden-test-material --assert-tool-results-recoverable` 通过。

### A4. `context_integrity_error` 空补丁不能归因为模型没有生成补丁

问题：工具配对检查在 provider 调用前失败时，AgentLoop 会停止为 `context_integrity_error`。如果此时 final patch 为空，当前 pre-verl final verifier 的空补丁分支可能归因为 `empty_final_patch` 和 `model_no_patch_generated`。

实施要求：

1. `context_integrity_error`、`model_error`、`provider_protocol_error`、`tool_call_parse_failure_unrecovered` 这类 Harness 或 provider 协议失败导致的空补丁，不能归为 `model_no_patch_generated`。
2. 建议新增或复用独立 failure category：
   - `context_integrity_error_before_final_patch`
   - `provider_protocol_error_before_final_patch`
   - `tool_call_parse_failure_unrecovered`
3. 如果为了保持 schema 简单，也可以使用统一类别 `harness_or_provider_protocol_error_before_final_patch`，但 `failure_owner` 必须是 `harness_or_provider`、`harness_or_protocol` 或更精确字段，不能是 `model_wrong_fix` 或 `model_no_patch_generated`。
4. aggregation、training export readiness 和 failure taxonomy 必须把这些类别排除在 trainable accepted sample 之外。

验收检查：

1. 构造缺失 tool result 的上下文，确认 provider request 没有写出。
2. run 结束后 final patch 为空，但 boundary failure owner 不是模型。
3. export quality audit 不把该 run 放入训练样本。

## 4. Stage B：处理 gap 文档 `6.1` 的正式测评前项目

### B1. G1：Provider retry、backoff 和 attempt artifact

正式测评使用真实 provider 时，这一项应当实现最小闭环，不能只写 known limitation。

实施要求：

1. 对 DeepSeek 和 OpenAI provider 统一 retry policy：
   - retryable error：`rate_limited`、`provider_timeout`、`provider_error` 且 provider payload 标记为 retryable。
   - non-retryable error：认证错误、请求参数错误、tool schema 不合法、普通 `invalid_response`。
2. 默认最多 3 次 attempt，包含首次请求和最多 2 次重试。
3. 使用确定性、可审计的 backoff 字段。测试中应允许关闭真实 sleep 或注入 fake sleeper。
4. 每次 attempt 都必须有独立 request / response artifact 或独立 attempt metadata，至少包含：
   - `attempt_index`
   - `model_call_id`
   - `provider`
   - `retryable`
   - `error_type`
   - `delay_ms`
   - `request_ref`
   - `response_ref`
5. 最终 `model_call_completed` 事件必须记录 `attempt_count`、`retry_count`、`terminal_error_type` 和 `retry_policy_ref`。
6. fallback provider 的成功不能计入 primary provider accepted rate。若暂时没有 fallback provider，本轮应写明 `fallback_provider.enabled=false`。

验收检查：

1. fake provider 第一次返回 429，第二次成功，最终 run 成功并记录 `retry_count=1`。
2. fake provider 连续 timeout，最终 terminal reason 为 provider timeout，而不是模型失败。
3. non-retryable auth error 不重试。

### B2. G2：输出 token 上限必须有独立 terminal reason

正式测评前可以不实现 continuation，但必须把输出 token 上限和输入 context limit 区分开。

建议本轮采用的冻结策略：

1. `continuation.enabled=false`。
2. `finish_reason=length` 归因为 `output_token_limit_reached` 或 `max_output_tokens_exhausted`。
3. 该状态不能继续沿用 `context_limit`，因为它不是模型输入上下文过长，而是模型输出预算耗尽。
4. metrics、run metadata、failure taxonomy 和正式报告必须能统计输出截断次数。
5. 如果后续启用一次 continuation，必须生成新的 baseline id，不能与本轮正式二十三题结果混算。

验收检查：

1. fake provider 返回 `finish_reason=length`。
2. run 的 `agent_stop_reason` 或 `model_error_type` 能体现 `output_token_limit_reached`。
3. final verifier 前如果没有有效 final patch，归因为输出预算或 provider output limit，不归为模型错误修复。

### B3. G3：Malformed tool call 至少支持一次模型可见修复回合

正式真实 provider 测评中，provider 返回 malformed tool call 是常见协议风险。如果直接 terminal `model_error`，会把可恢复的协议问题误计为模型能力不足。

实施要求：

1. 当 provider response 中工具调用 JSON 无法解析、缺少 function name、arguments 不是 JSON object、tool call id 缺失或重复时，AgentLoop 不应立即进入普通 `model_error`。
2. 增加一次模型可见 repair turn，内容必须明确：
   - 哪个字段错误。
   - 原始错误类别。
   - 需要重新输出合法 tool call 或 final answer。
   - 不暴露 provider raw artifact 的敏感内容。
3. repair turn 需要写入 transcript、prepared messages 和 raw provider request / response artifact。
4. 如果第二次仍失败，terminal reason 必须是 `tool_call_parse_failure_unrecovered`。
5. 修复回合次数必须冻结为 `malformed_tool_call_repair.max_attempts=1`。

验收检查：

1. fake provider 第一次返回 malformed tool call，第二次返回合法 `read_file` 调用，AgentLoop 能继续执行工具。
2. fake provider 连续两次 malformed，run 归因为 `tool_call_parse_failure_unrecovered`，不进入 trainable accepted sample。

### B4. G4：轻量 permission policy manifest

这一项可以不实现完整 Claude Code 权限系统，但必须冻结当前权限裁决顺序和禁用能力。

实施要求：

1. 每个正式 run 写出 `permission_policy_manifest` artifact。
2. manifest 至少包含：
   - `permission_policy_version`
   - `command_policy_version`
   - `decision_order`
   - `permission_mode`
   - `non_interactive_resolution`
   - `hooks.enabled=false`
   - `mcp.enabled=false`
   - `dynamic_permission_classifier.enabled=false`
   - `bash.shell_execution=false`
   - `bash.safe_argv_required=true`
   - `test_feedback_policy`
   - `feedback_tests_passed_policy`
   - deny rule summary 和 policy hash
3. 每次 tool decision 仍要记录 matched rule、decision、reason、normalized input hash、resolved path 和 recovery hint。

验收检查：

1. readiness inspect 能证明每个正式 run 都有 `permission_policy_manifest_ref`。
2. `bash` disabled 或受限的状态能从 manifest 中直接读出。
3. formal report 中引用该 manifest，说明本轮没有启用 hooks、MCP 和动态权限 classifier。

### B5. G5：统一 `run-task` 和 V5 provider matrix 的 primary provider 入口

这一项要先做明确决策：如果正式二十三题只用一个 primary provider，并且全部通过 `repo-harness run-task` 执行，可以冻结为单 provider 正式测评；如果要做 provider comparison，则必须先统一 runtime。

推荐本轮采用的最小策略：

1. 正式二十三题 accepted rate 只统计通过 `repo-harness run-task` 产生的 run。这是硬门槛，不是可选增强。
2. V5 provider matrix 只作为调度或报告层，不能绕过 `run-task` 生成 accepted rate，不能使用旧 pilot、matrix-only shortcut 或旧 V3 adapter 产物填充正式结果。
3. 如果本轮只用 DeepSeek，则写入 `provider_axis_scope=deepseek_only`，并在报告中说明 OpenAI comparison 不属于本轮正式 accepted rate。
4. 如果本轮要同时跑 DeepSeek 和 OpenAI，则必须先统一 provider registry，使两个 provider 都走同一个 AgentLoop、同一个 final verifier adapter、同一套 provider artifact binding 和 failure taxonomy。

验收检查：

1. CLI help 不再暴露旧 pilot 运行入口。
2. 每个正式 run 的 `run_config_facts` 记录 provider id、provider family、provider message format、tool schema snapshot hash、prompt hash、model id 和 provider options hash。
3. 正式结果聚合只读取 `run-task` run dir，不读取旧 pilot 或 matrix-only shortcut 产物。
4. boundary index inspect 能证明每个正式 run 都有 `run-task` lineage、AgentLoop events、tool schema snapshot 和 final verifier boundary ref。

### B6. G6：per-turn token、cost 和 budget decision trace

本轮不要求真实美元成本完全准确，但必须避免 `cost=0` 看起来像真实低成本。

实施要求：

1. 每轮 provider 调用后写出 budget decision trace，至少包含：
   - `turn`
   - `input_tokens`
   - `output_tokens`
   - `cached_tokens`
   - `token_source`
   - `cost_source`
   - `cost_available`
   - `estimated_cost`
   - `max_cost_enforcement`
   - `remaining_turn_budget`
   - `remaining_tool_call_budget`
   - `remaining_test_run_budget`
   - `decision`
   - `decision_reason`
2. 如果 provider 没返回费用，写 `cost_available=false` 和 `max_cost_enforcement=unavailable` 或 `disabled`。
3. budget stop reason 必须和 AgentLoop terminal reason 对齐。

验收检查：

1. 一个正常 provider run 至少有一条 budget decision trace。
2. 一个 token 或 turn budget 到顶的 run 能从 trace 中解释为什么停止。
3. metrics、run metadata 和 readiness report 的 budget 字段一致。

### B7. G13 轻量部分：初始上下文和 repo context index

这一项不要求复制 Claude Code 的完整层级 instruction resolver，也不应因为没有完整层级项目说明解析而阻塞正式测评。正式测评前的最低要求是记录当前 context policy、注入文件、哈希、截断边界，并把“没有完整层级 instruction resolution”写成 known limitation。

建议实施要求：

1. AgentLoop 初始上下文识别并记录仓库内 `AGENTS.md`。如果不存在，记录 `agents_md_present=false`。
2. 记录简洁 git/source snapshot：
   - base commit 或 source tree hash
   - agent start snapshot
   - 初始 changed / untracked 文件摘要
   - dirty state policy
3. 写出 `repo_context_index` artifact：
   - model-visible 文件索引摘要
   - 文件数量
   - 截断策略
   - 敏感路径过滤策略
   - index hash
4. 不要把 evaluator-only、hidden patch、hidden selector 或 provider raw artifact 放入初始上下文。
5. 如果本轮来不及实现 `repo_context_index`，至少必须在 freeze manifest 中记录 `repo_context_index.enabled=false`、`agents_md_resolution=not_implemented_or_root_only` 和对应 known limitation；不能让正式报告暗示已经具备完整项目记忆。

验收检查：

1. 正式 run 的 initial prepared messages 或 run facts 能证明是否读取了 `AGENTS.md`。
2. `repo_context_index` 可以复算或至少绑定 source snapshot hash。
3. 没有隐藏测试材料进入模型可见上下文。

### B8. G23：Provider failure injection smoke

这项必须在正式 smoke 前完成，因为它验证 B1、B2、B3 的异常路径是否真的可用。

实施要求：

1. 使用 fake 或 mock provider 构造以下场景：
   - retryable 429
   - provider timeout
   - 五百类 provider error
   - non-retryable auth error
   - `finish_reason=length`
   - malformed tool call JSON
   - missing function name
   - arguments 不是 JSON object
   - invalid response body
2. 每个场景都要验证：
   - terminal reason
   - attempt artifact
   - retry count
   - model-visible repair message 是否存在
   - raw provider request / response 是否绑定
   - redaction report 是否存在
   - 该 run 是否被排除出 trainable accepted sample
3. 该 smoke 是 non-formal readiness evidence，不计入正式 accepted rate。

验收检查：

```bash
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_provider_artifact_binding.py tests/unit/test_provider_client.py
PATH=.venv/bin:$PATH repo-harness run-provider-failure-injection-smoke --scenario retryable_429,timeout,length,malformed_tool_call
```

如果暂时不新增 CLI，也可以用 pytest 集合实现同等覆盖，但 readiness report 必须列出每个 scenario 的通过结果和 artifact 路径。

## 5. Stage C：正式 smoke gate

完成 Stage A 和 Stage B 后，必须重新跑 smoke。旧 smoke 只能作为历史参考，不能作为本轮 readiness evidence。

建议 smoke gate：

1. 编译检查：

```bash
PATH=.venv/bin:$PATH python -m compileall src
```

2. hardening 相关单元测试：

```bash
PATH=.venv/bin:$PATH python -m pytest -q \
  tests/unit/test_tools.py \
  tests/unit/test_command_policy.py \
  tests/unit/test_permissions.py \
  tests/unit/test_agent_loop_protocol.py \
  tests/unit/test_context_manager.py \
  tests/unit/test_provider_artifact_binding.py \
  tests/unit/test_provider_client.py \
  tests/unit/test_pre_verl_agentloop.py
```

3. 真实 `run-task` model-visible context inspect：

```bash
PATH=.venv/bin:$PATH repo-harness run-task tests/fixtures/tasks/task_001.yaml --config tests/fixtures/run_configs/replay_success.yaml --output-dir /tmp/repo-harness-readiness-runs --run-id readiness-replay-context
PATH=.venv/bin:$PATH repo-harness inspect-model-visible-context /tmp/repo-harness-readiness-runs/readiness-replay-context --assert-no-hidden-test-material --assert-prepared-messages-bound --assert-provider-body-equivalent --assert-tool-results-recoverable --assert-no-over-redaction
```

4. 非 formal bash hardening smoke：
   - `bash pytest` 在 `test_feedback_policy=disabled` 时必须保持为 bash 并被拒绝。
   - `bash pytest` 在 public feedback enabled 时才允许路由到 `run_tests`。
   - `bash` 不允许 shell composition、管道、重定向、环境变量前缀、任意 `python -c`、网络命令、破坏性命令。

5. provider failure injection smoke：
   - 覆盖 retry、output length、malformed tool call 和 non-retryable provider error。

6. mock provider tool schema smoke：
   - provider tool schema 必须暴露 `grep.mode`、`grep.offset`、`grep.max_matches`、`read_file.start_line`、`read_file.end_line`、`edit_file.expected_content_hash`、`edit_file.replace_all`、`list_files.offset`、`list_files.max_entries`。
   - schema snapshot hash 必须写入 provider request binding。

7. 五题 Docker SWE-Bench Lite development smoke：
   - 全部通过正式 `repo-harness run-task` 入口。
   - 至少 4 个任务有真实 provider terminal outcome。
   - 0 个 `provider_protocol_error`。
   - 0 个 `context_integrity_error`。
   - 0 个 raw provider request over-redaction。
   - 所有真实 provider terminal outcome 都必须绑定 `final_verifier_boundary.json`。
   - 至少 3 个 smoke task 必须进入 strict final verifier adapter，或者完成 `model final patch -> evaluator-only hidden test patch -> selector` 的边界链路。
   - 至少 1 个 smoke task 必须产生可应用的非空模型补丁，用来证明 smoke 不只是空补丁、blocked run 或 provider error 的集合。
   - 如果有 blocked 任务，必须证明是单任务已知问题，不是 Docker execution mode、TaskDefinition、provider adapter、final verifier 或隐藏测试补丁的系统性问题。

## 6. Stage D：正式二十三题测评前 freeze manifest

正式二十三题开始前必须冻结以下字段，并把 freeze manifest 与每个 run 绑定：

1. 代码提交 hash。
2. task set manifest hash。
3. run config hash。
4. provider id、provider family、model id、base url policy 和 provider options hash。
5. prompt hash 和 scaffold id。
6. tool schema snapshot hash。
7. permission policy manifest hash。
8. command policy hash。
9. budget policy hash。
10. redaction policy hash。
11. context replacement policy hash。
12. final verifier adapter id 和 verifier plan hash。
13. baseline id。
14. smoke readiness report hash。
15. `provider_retry_policy_version`、`retry_max_attempts` 和 `retry_backoff_policy`。
16. `output_token_recovery_policy`，本轮如果不启用 continuation，应写 `continuation.enabled=false`。
17. `tool_call_repair_policy`，包括 `malformed_tool_call_repair.max_attempts`。
18. `provider_protocol_family` 和 provider message serializer version。
19. `usage_metadata_source`，包括 token usage 来源和 cost 是否可用。
20. `hooks.enabled=false`、`mcp.enabled=false`、`plugin_tools.enabled=false`、`skill_tools.enabled=false`。
21. `provider_axis_scope`，例如 `deepseek_only` 或 `multi_provider_run_task_unified`。
22. 运行预算字段必须明文冻结，不能只藏在 `run_config_hash` 中：
    - `max_turns`
    - `max_tool_calls`
    - `max_test_runs`
    - `task_timeout_sec`
    - `command_timeout_sec`
    - `final_verifier_timeout_sec`
23. provider 生成参数必须明文冻结：
    - `max_output_tokens`
    - `temperature`
    - `seed` 或 `seed_unavailable`
    - `request_timeout_seconds`
24. 工具可见性和工具输出预算必须明文冻结：
    - `resolved_tool_list`
    - `test_feedback_policy`
    - `feedback_tests_passed_policy`
    - `bash.enabled`
    - `bash.shell_execution`
    - `bash.safe_argv_required`
    - 每个工具的 `resolved_max_output_chars`
25. 如果 formal final-only baseline 不开放 `bash`，必须写 `bash.enabled=false`，并证明 provider tool schema snapshot 中没有 `bash`。如果任何 scaffold comparison 开放 `bash`，必须生成新的 baseline id，不能与 final-only baseline 混算。

只要以上任意字段在正式测评前发生变化，就必须生成新的 baseline id，重新跑 smoke，不能把旧 smoke 或旧 accepted rate 与新运行混算。

## 7. Stage E：正式结果标记和公开叙事前的额外门槛

以下检查不一定阻塞“开始跑任务”，但必须阻塞“把结果标记为正式结果、写入简历展示或公开叙事”：

1. 二十三题 TaskDefinition 全部通过冻结和 hidden material 可见性检查。
2. final verifier boundary index 全部通过，特别是 patch application order、command order、clean source origin 和 run-task lineage。
3. accepted rate 分母字段精确，能区分 accepted、rejected、provider error、budget / timeout、empty patch、context integrity error、environment setup failed 和 structured skip。
4. Docker phase coverage matrix 完整，能证明 setup、model patch apply、hidden patch apply、fail-to-pass、pass-to-pass 的阶段覆盖。
5. bundle command lineage 完整，正式报告中的每个关键 artifact 都能追溯到命令、输入 hash 和输出 hash。
6. public-safe scan 通过，正式展示包不包含 evaluator-only hidden patch、selector、gold patch、final verifier raw output、provider raw body 或 provider private reasoning。
7. training export readiness 通过，默认训练导出不包含失败污染样本、evaluator-only artifact 或 provider raw artifact。

## 8. 本轮不阻塞正式测评但必须报告的 known limitations

以下内容来自 gap 分析文档，但不建议阻塞本轮正式二十三题测评：

1. 并发工具执行和只读工具并发调度。
2. streaming 输出和长耗时阶段的实时 liveness 展示。
3. 完整 no-progress detector 和重复失败诊断。
4. 完整 hook lifecycle 执行协议。
5. 任意中断点 durable session resume。
6. 完整层级 instruction resolver。
7. 延迟工具发现、动态工具池和 schema cache 产品化。
8. 文件历史浏览和编辑归因快照增强。
9. LSP、符号级检索和异步 lint 诊断。
10. MCP、plugin、skill runtime tool source。
11. 模型可调用子代理和 sidechain transcript。
12. provider quota、rate limit circuit breaker 的并发批量调度能力。如果本轮顺序执行，应明确写为 sequential evaluation limitation。
13. provider/tool/final verifier 的统一 cancellation propagation。

这些能力可以进入 post-pre-verl backlog，但不能影响本轮 accepted rate 的解释。

## 9. 推荐实施顺序

建议按以下顺序执行，避免后续修复覆盖前面证据：

1. 修复 Stage A 四个 review finding，并补齐真实 run 集成测试。
2. 实现或冻结 B2 output token terminal reason，因为它改动 provider response 归因。
3. 实现 B3 malformed tool call repair，因为它改动 AgentLoop 的 provider error 分支。
4. 实现 B1 provider retry 和 attempt artifact，因为它依赖 provider terminal reason 分类。
5. 实现 B4 permission policy manifest。
6. 明确 B5 provider runtime scope：单 provider freeze 或 provider comparison runtime 统一二选一。
7. 实现 B6 budget decision trace。
8. 实现 B7 AGENTS.md、git/source snapshot 和 repo context index 的轻量上下文。
9. 实现 B8 provider failure injection smoke。
10. 跑 Stage C smoke gate。
11. 生成 Stage D freeze manifest。
12. 只有所有 readiness gate 通过后，启动正式二十三题测评。

## 10. 停止条件

如果出现以下任意情况，应停止进入正式二十三题测评，并生成 blocked report：

1. `inspect-model-visible-context` 不能在真实 `run-task` 产物上通过。
2. 任何正式 smoke 出现 `context_integrity_error`。
3. 任何正式 smoke 出现 raw provider request 与 prepared messages projection 不一致。
4. final verifier boundary 中隐藏测试补丁应用顺序不满足：先 model final patch，再 evaluator-only hidden test patch，再 fail-to-pass，再 pass-to-pass。
5. provider failure injection smoke 不能区分 retryable、non-retryable、output token limit 和 malformed tool call。
6. mock provider tool schema smoke 不能证明正式 provider request 中的 schema snapshot 与工具契约一致。
7. 训练导出 readiness 仍可能包含 empty patch、provider protocol error、context integrity error、hidden verifier material 或 evaluator-only artifact。
8. freeze manifest 缺失关键 hash，或者 smoke 后又改了 tool schema、prompt、provider policy、redaction policy、budget policy 或 final verifier adapter。
9. 正式聚合发现任何 run 来自旧 pilot、matrix-only shortcut、旧 V3 adapter 或非 `repo-harness run-task` 入口。

## 11. 最终回答

正式 smoke 和正式二十三题 pre-verl 测评前，需要做的不是“补齐 Claude Code 的所有产品级能力”，而是把 gap 文档 `6.1` 变成一组可验证的 readiness gate。

其中 Stage A 四个 review finding 必须先修，因为它们会让当前 hardening 证据本身不可信。Stage B 中 G1、G2、G3、G23 应实现最小闭环；G4、G6、G13 应实现轻量冻结和审计；G5 必须在“单 provider 正式评测”和“多 provider runtime 统一”之间做明确选择。完成后重新跑 smoke，生成新的 freeze manifest，再进入正式二十三题测评。
