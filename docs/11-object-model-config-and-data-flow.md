# Object Model, Config, And Data Flow

## 设计目标

这篇文档把 RepoHarness 的核心对象、配置字段、后续源代码目录和端到端数据流集中定义。它不包含具体实现代码，而是给下一阶段工程实现提供统一命名和边界，避免每个模块重复定义相似的数据结构。

## 源代码目录

本文最初用于规划第一版实现的模块边界。第一版完成后，代码已经按下面的目录结构落地；其中真实模型供应商接入、Docker 执行模式和更复杂 scaffold 仍然属于后续扩展，不属于第一版已实现能力。

```text
src/repo_harness/
  agent_loop/        # agent loop state, turn execution, termination handling
  cli/               # command line entrypoints and config loading
  context/           # context builder, prompt templates, context budget policy
  evaluation/        # batch evaluation runner and aggregate metrics
  export/            # SFT, reinforcement learning rollout, preference pair export
  model_client/      # provider adapters, model response normalization, tool call parsing
  permissions/       # permission modes, rules, decisions
  reward/            # verifier-aligned reward calculation and reward metadata
  scaffolds/         # single-shot, simple ReAct, planner-coder-verifier
  tasks/             # task adapters and task validation
  tools/             # tool definitions and tool orchestration
  trajectory/        # transcript, events, artifacts index
  verifier/          # baseline, feedback, final verifier paths
  workspace/         # local process and Docker-based executable repository environment
```

这些目录用于维持对象所有权和模块边界。当前已实现范围以根目录 `README.md`、`docs/v1-walkthrough.md` 和 `docs/v1-final-acceptance.md` 为准。

## RunConfig

`RunConfig` 是一次单任务运行或批量评测的配置对象。推荐 YAML 形态：

```yaml
run_id_prefix: local_eval
tasks:
  - tasks/repo_task_001.yaml
model:
  provider: openai
  model_id: example-model
  temperature: 0.2
  max_output_tokens: 4096
  retry_policy: conservative
  credential_policy: env_only
  provider_request_logging: redact_secrets
runtime:
  scaffold_id: simple_react
  execution_mode: local_process
  permission_mode: auto
  max_turns: 20
  max_tool_calls: 80
  max_test_runs: 6
  no_progress_patience: 3
  task_timeout_sec: 900
  seed: 42
workspace:
  output_dir: runs
  keep_workspace: true
  default_command_timeout_sec: 120
  max_tool_output_chars: 12000
  network_policy: deny_agent_run
context_management:
  max_context_tokens: 120000
  tool_result_aggregate_budget_chars: 40000
  keep_recent_turns: 6
  keep_recent_test_results: 2
  summarize_old_test_outputs: true
  compact_strategy: deterministic_preview_replacement
  compact_threshold_ratio: 0.85
  context_policy_version: repo_harness_context_policy_v0
  token_estimator: char4_token_estimator_v0
evaluation:
  concurrency: 1
  rerun_final_verifier: true
  final_verifier_mode: strict_patch_replay
  fail_on_invalid_task: false
versions:
  schema_version: repo_harness_run_v0
  prompt_template_version: repo_harness_prompt_v0
  context_builder_version: repo_harness_context_v0
  tool_policy_version: repo_harness_tools_v0
  permission_policy_version: repo_harness_permissions_v0
  export_policy_version: repo_harness_export_policy_v0
logging:
  level: info
  write_transcript: true
  write_events: true
```

批量评测默认应使用 `auto` 或 `deny` 模式，不应默认使用需要人工确认的 `ask` 模式。

### RunConfig 字段说明

`RunConfig` 应作为一次运行的可复现实验配置。字段含义如下：

| 字段 | 含义 |
| --- | --- |
| `run_id_prefix` | run id 的前缀，用于区分本地调试、批量评测或不同实验批次。最终 run id 仍应包含任务 id、时间戳或唯一后缀。 |
| `tasks` | 本次运行要加载的任务定义文件列表。每个文件会先进入 Task Adapter，转换成 `RunnableTask` 和 `VerifierConfig`。 |
| `model.provider` | 模型供应商标识，例如 `openai`、`anthropic`、`deepseek`。Agent Loop 不直接依赖它，而是交给 Model Client 适配。 |
| `model.model_id` | 具体模型名称。它必须进入 run metadata，保证后续评测和训练样本可追溯。 |
| `model.temperature` | 模型采样温度。批量评测通常使用较低温度；多 rollout 数据采集可以提高温度以增加多样性。 |
| `model.max_output_tokens` | 单次模型响应最多输出多少 token。它不是整条轨迹预算，整条轨迹预算由 runtime 和 Budget Manager 管。 |
| `model.retry_policy` | 模型调用失败时的重试策略。例如 `conservative` 可以表示只对 429、5xx、临时网络错误做有限重试，不重试鉴权错误、协议错误或无效响应。每次重试必须写入 `ModelCallEvent`。 |
| `model.credential_policy` | 模型供应商凭据读取策略。第一版建议 `env_only`，即只从环境变量读取 API key，不把密钥写入 task、RunConfig、transcript、events 或 artifact。 |
| `model.provider_request_logging` | provider request / response artifact 的记录和脱敏策略。第一版建议保存可复盘 artifact，但默认脱敏密钥、认证 header 和用户本地绝对路径。 |
| `runtime.scaffold_id` | 本次运行使用的 scaffold，例如 `single_shot_patch`、`simple_react` 或 `planner_coder_verifier`。 |
| `runtime.execution_mode` | 工作区执行模式，例如 `local_process` 或 Docker-based executable repository environment。它描述命令在哪个边界内执行，不等同于 permission。 |
| `runtime.permission_mode` | 权限模式，例如 `plan`、`ask`、`auto`、`deny`。批量评测默认不应使用 `ask`。 |
| `runtime.max_turns` | Agent Loop 最多允许多少轮模型调用。耗尽后记录 `agent_stop_reason = "max_turns"`。 |
| `runtime.max_tool_calls` | 单次 run 最多允许多少次工具调用。用于防止工具滥用和长轨迹失控。 |
| `runtime.max_test_runs` | agent run 期间最多允许多少次 `run_tests` feedback verifier。它不包含 baseline verifier 和 final verifier。 |
| `runtime.no_progress_patience` | 连续多少次无测试改善、无有效 diff 变化或重复工具失败后触发 `no_progress` 诊断。是否终止由 scaffold 和 BudgetManager 决定。 |
| `runtime.task_timeout_sec` | 单任务全局超时时间，映射到 `BudgetManager.task_timeout_sec`。到达后应中断 agent loop，补齐未完成 tool result，并记录 timeout 事件。 |
| `runtime.seed` | 随机种子，用于任务抽样、rollout 排序或未来可控采样。模型供应商不一定完全保证同 seed 可复现，但仍应记录。 |
| `workspace.output_dir` | run artifacts 的根目录，例如 `runs/`。每次运行会在其下创建独立 run directory，保存 transcript、events、artifacts、diff、verifier、metrics 和 summary。 |
| `workspace.keep_workspace` | 是否保留正式 agent run workspace。`true` 适合本地调试，方便人工检查最终文件；批量评测可以设为 `false`，只保留可复现 artifacts。无论是否保留 workspace，都必须保存 `final.patch`、`final.diff` 和必要 artifact。 |
| `workspace.default_command_timeout_sec` | 普通命令默认 timeout。工具、测试和 verifier 可以有更具体的 timeout 覆盖。 |
| `workspace.max_tool_output_chars` | 回填给模型上下文的工具输出 preview 最大字符数。完整输出应作为 artifact 保存。 |
| `workspace.network_policy` | 网络访问策略。第一版建议 `deny_agent_run`：setup 阶段可按任务配置允许网络，正式 agent run 阶段默认拒绝或强限制网络。 |
| `context_management.max_context_tokens` | 单次模型调用允许的最大上下文 token 预算。超过预算时先执行确定性 context reduction，仍超出时停止为 `context_limit`。 |
| `context_management.tool_result_aggregate_budget_chars` | 一轮模型输入中所有 tool result preview 的总字符预算，用于避免长日志和重复文件读取挤占任务上下文。 |
| `context_management.keep_recent_turns` | 压缩时完整保留最近多少轮消息，较旧轮次可以替换为 ArtifactRef preview 或摘要。 |
| `context_management.keep_recent_test_results` | 完整保留最近多少次 feedback verifier 结果，较旧测试输出应替换为结构化摘要。 |
| `context_management.summarize_old_test_outputs` | 是否把旧测试输出替换为失败测试 id、错误类型、关键片段和 artifact 引用。 |
| `context_management.compact_strategy` | 上下文裁剪策略。第一版建议确定性 preview replacement，不要求 LLM 自动 compact。 |
| `context_management.compact_threshold_ratio` | 达到上下文预算多少比例时开始执行 context reduction。 |
| `context_management.context_policy_version` | 上下文策略版本，必须写入 context event 和训练导出 metadata。 |
| `context_management.token_estimator` | token 估算器版本。不同估算器会影响裁剪决策，必须可追溯。 |
| `evaluation.concurrency` | 批量评测并发数。第一版默认为 1，未来提高并发时必须处理 run directory lock、唯一 run id 和 recorder 幂等性。 |
| `evaluation.rerun_final_verifier` | agent 停止后是否强制重新运行 final verifier。正式评测和训练导出应为 `true`。 |
| `evaluation.final_verifier_mode` | final verifier 模式。`strict_patch_replay` 表示从干净 verification workspace 恢复合法依赖、应用 `final.patch` 后再验收；快速调试可以使用 agent run workspace 直接验收，但必须记录模式。 |
| `evaluation.fail_on_invalid_task` | 遇到 invalid 或 flaky task 时是否让整个批量运行失败。`false` 表示跳过无效任务并记录 `invalid_task` 或 `flaky_task`；`true` 适合 CI 或任务集质量门控。 |
| `versions.*` | 所有关键 schema、prompt、context、tool、permission 和 export 策略版本。版本字段保证历史 runs 和训练样本在设计演进后仍然可解释。 |
| `logging.level` | 运行时日志级别。它控制 operational telemetry，不应改变 transcript、events 和 verifier 的事实数据。 |
| `logging.write_transcript` | 是否写 `transcript.jsonl`。正式训练数据采集应开启。 |
| `logging.write_events` | 是否写 `events.jsonl`。正式评测、诊断和 reward metadata 生成应开启。 |

## 核心对象清单

| 对象 | 主要字段 | 来源模块 | 消费模块 |
| --- | --- | --- | --- |
| `TaskDefinition` | `id`、`task_version`、`dataset_name`、`source_kind`、`dataset_split`、`created_at`、`repo`、`base_commit`、`source_archive_sha256`、`issue`、`setup_command`、`test_command`、`timeouts`、`environment`、`expected_files`、`fail_to_pass_tests`、`pass_to_pass_tests`、`gold_patch`、`decontamination`、`declared_setup_mutations`、`generated_files`、`visibility`、`tags` | Task Adapter | Task Adapter、Trajectory Store |
| `RunnableTask` | `task_id`、`task_version`、`dataset_name`、`issue_statement`、`repo_source`、`base_commit`、`environment`、`setup_command`、`timeouts`、`verifier_config`、`expected_files`、`mutation_policy`、`generated_files_policy`、`visibility_policy`、`decontamination_metadata`、`metadata` | Task Adapter | Agent Loop、Workspace Adapter、Verifier |
| `BaselineResult` | `status`、`setup_exit_code`、`baseline_exit_code`、`baseline_verifier_result_ref`、`setup_artifact_refs`、`baseline_artifact_refs`、`parser_confidence`、`baseline_rerun_count`、`flaky_policy_version`、`initial_fail_to_pass_tests`、`initial_pass_to_pass_tests`、`flaky_tests`、`dependency_error`、`dependency_state`、`setup_workspace_snapshot`、`agent_run_start_policy` | Workspace Adapter、Verifier | Eval Runner、Verifier、Trajectory Store |
| `DependencyState` | `strategy`、`cache_key`、`artifact_ref`、`restored_paths`、`excluded_diff_paths`、`created_after_setup_command`、`excludes_baseline_side_effects` | Workspace Adapter | Eval Runner、RunWorkspace、Verifier |
| `RunWorkspace` | `run_id`、`workspace_path`、`repo_base_commit`、`execution_mode`、`artifact_dir`、`dependency_state`、`dependency_state_ref`、`agent_start_snapshot`、`agent_diff_base` | Workspace Adapter | Tool System、Verifier、Trajectory Store |
| `AgentLoopState` | `messages`、`turn_count`、`tool_call_count`、`last_verifier_result`、`budget_state`、`tool_pairing_state`、`context_revision`、`last_model_error`、`last_tool_parse_error`、`agent_stop_reason` | Agent Loop | Agent Loop、Trajectory Store |
| `ContextBuilder` | `context_builder_version`、`prompt_template_version`、`visible_context_policy`、`hidden_metadata_policy` | Context module | Agent Loop、Scaffold、Trajectory Store |
| `ContextManager` | `context_revision`、`context_policy_version`、`truncation_policy`、`compaction_event`、`tokens_before`、`tokens_after`、`token_estimator_version`、`tool_pairing_validation`、`content_replacement_state` | Context module | Agent Loop、RunRecorder、Training Exporter |
| `PreparedMessages` | `messages`、`prepared_messages_ref`、`model_input_hash`、`context_revision`、`context_event`、`content_replacement_state`、`token_estimate` | ContextManager | Model Client、RunRecorder、Training Exporter |
| `ContextReductionRecord` | `context_revision`、`source_message_ids`、`kept_message_ids`、`dropped_message_ids`、`replaced_tool_result_ids`、`replacement_artifact_refs`、`replacement_preview_hash`、`summary_artifact_ref`、`model_visible` | Context module | RunRecorder、Training Exporter、Diagnostics |
| `ContentReplacementState` | `context_policy_version`、`seen_tool_result_ids`、`records`、`state_hash`、`last_context_revision` | Context module | ContextManager、Training Exporter、Session Resume |
| `ContentReplacementRecord` | `tool_call_id`、`original_tool_result_id`、`replaced`、`first_visible_form`、`first_visible_content_hash`、`replacement_allowed_after_first_seen`、`replacement_text_hash`、`replacement_artifact_refs`、`replacement_preview_hash`、`first_replaced_at_context_revision`、`first_seen_at_context_revision` | Context module | ContentReplacementState、Training Exporter、Diagnostics |
| `ModelMessage` | `role`、`content`、`tool_calls`、`metadata` | Agent Loop、Model Client | Agent Loop、Transcript Export |
| `ModelClient` | `provider`、`model_id`、`retry_policy`、`streaming_mode`、`tool_call_parser` | Model Client module | Agent Loop |
| `ProviderCredentialPolicy` | `credential_source`、`required_env_vars`、`redact_request_headers`、`redact_provider_response`、`secret_scan_policy` | CLI / Model Client | Model Client、RunRecorder |
| `ToolCallParser` | `parser_id`、`provider`、`tool_call_format`、`validation_policy` | Model Client module | ModelClient、Agent Loop |
| `ModelResponse` | `assistant_message`、`tool_calls`、`raw_provider_request_ref`、`raw_provider_response_ref`、`token_usage`、`finish_reason`、`model_error_type`、`provider_request_id`、`model_call_event` | Model Client | Agent Loop、Trajectory Store |
| `ModelCallEvent` | `model_id`、`provider_request_id`、`context_revision`、`prepared_messages_ref`、`model_input_hash`、`provider_message_format`、`tool_schema_hash`、`input_tokens`、`output_tokens`、`cached_tokens`、`duration_ms`、`retry_count`、`model_error_type` | Model Client | RunRecorder、Metrics |
| `ToolCall` | `tool_call_id`、`tool_name`、`arguments`、`turn` | Model Client、Agent Loop | Tool System、Permission System |
| `ToolExecutionContext` | `run_id`、`task_id`、`workspace_facade`、`artifact_writer`、`permission_context`、`verifier_feedback_facade`、`abort_signal`、`output_limits`、`tool_policy`、`budget_manager`、`file_state_cache` | Tool System | Tool implementations |
| `PermissionDecision` | `decision_id`、`tool_call_id`、`tool_name`、`requested_tool_name`、`effective_tool_name`、`decision`、`mode`、`matched_rule`、`policy_version`、`rule_source`、`reason`、`normalized_input_hash`、`resolved_paths`、`command_category`、`network_policy`、`requested_cwd`、`effective_cwd`、`non_interactive_resolution`、`requires_user_input` | Permission System | Tool System、Trajectory Store |
| `ExecutionResult` | `exit_code`、`stdout_preview`、`stderr_preview`、`output_artifact_ref`、`duration_ms`、`timeout`、`command_semantics`、`exit_code_interpretation` | Workspace Adapter | Tool System、Verifier |
| `ToolResult` | `tool_call_id`、`tool_name`、`requested_tool_name`、`effective_tool_name`、`requested_arguments`、`normalized_arguments`、`effective_arguments`、`normalization_policy_version`、`normalized_input_hash`、`route_reason`、`route_policy_version`、`status`、`content_preview`、`error_type`、`truncated`、`artifact_refs`、typed extension fields | Tool System | Agent Loop、Trajectory Store |
| `VerifierConfig` | `test_command`、`test_timeout_sec`、`final_verifier_timeout_sec`、`fail_to_pass_tests`、`pass_to_pass_tests`、`parser`、`visibility_policy` | Task Adapter | Verifier |
| `ResolvedVerifierPlan` | `verifier_config`、`initial_fail_to_pass_tests`、`initial_pass_to_pass_tests`、`flaky_tests`、`parser_confidence`、`acceptance_policy_version`、`resolved_verifier_plan_id` | Eval Runner | Verifier、Reward module、Training Exporter |
| `VerifierParser` | `parser_id`、`parser_version`、`supported_frameworks`、`parse_strategy` | Verifier | Verifier |
| `TestCaseResult` | `test_id`、`status`、`duration_ms`、`failure_preview`、`raw_output_ref` | Verifier Parser | VerifierResult、Metrics |
| `VerifierResult` | `parser_id`、`parser_version`、`parser_confidence`、`command`、`test_cases`、`accepted`、`acceptance_policy_version`、`accepted_fallback_reason`、`pass_ratio`、`fail_to_pass`、`pass_to_pass`、`exit_code`、`timeout`、`error_type` | Verifier | Eval Runner、Reward、Trajectory Store |
| `RewardMetadata` | `reward_version`、`final_reward`、`formula`、`components`、`sources`、`invalid_for_training`、`invalid_reason`、`acceptance_policy_version`、`reward_clip_range` | Reward module | Training Exporter、Metrics |
| `RunRecorder` | `run_id`、`transcript_writer`、`event_writer`、`artifact_manifest`、`schema_version` | Trajectory Store | All runtime modules |
| `ArtifactRef` | `artifact_id`、`relative_path`、`kind`、`sha256`、`size_bytes`、`created_by_event_id`、`redaction_status`、`retention_policy` | Trajectory Store | Events、Transcript、Exporter |
| `TranscriptRecord` | `schema_version`、`record_id`、`run_id`、`task_id`、`message_id`、`parent_message_id`、`turn`、`role`、`model_call_id`、`tool_call_id`、`tool_result_id`、`context_revision`、`content_preview`、`content_artifact_refs`、`model_visible`、`trainable`、`created_at` | RunRecorder | Replay、Training Exporter、Diagnostics |
| `TrajectoryEvent` | `schema_version`、`event_id`、`timestamp`、`run_id`、`task_id`、`turn`、`event_type`、`severity`、`duration_ms`、`error_type`、`artifact_refs`、typed extension fields | All runtime modules | Metrics、Diagnostics、Exporter |
| `BudgetManager` | `max_turns`、`max_tool_calls`、`max_test_runs`、`task_timeout_sec`、`command_timeout_sec`、`verifier_timeout_sec`、`max_tool_output_chars`、`max_context_tokens`、`max_output_tokens`、`max_cost`、`max_artifact_bytes`、`max_concurrent_tasks` | Runtime | Agent Loop、Tool System、Verifier、Eval Runner |
| `RunSummary` | `run_id`、`task_id`、`agent_stop_reason`、`final_verifier_status`、`run_outcome`、`key_artifact_refs`、`failure_diagnostics`、`human_summary` | Trajectory Store | CLI、Inspect、README demo artifacts |
| `MetricsRecord` | `task_success`、`final_verifier_status`、`run_outcome`、`turn_count`、`tool_call_count`、`test_run_count`、`timeout`、`patch_stats`、`permission_denial_count`、`invalid_tool_call_count`、`cost_estimate`、`code_quality_checks`、`interaction_efficiency`、`patch_locality` | Evaluation | Metrics、Training Exporter、Reports |
| `ExportPolicy` | `export_policy_version`、`loss_mask_policy`、`observation_mask_policy`、`filter_rules`、`redaction_policy` | Training Exporter | Exporter、Metrics |
| `ExportRecord` | `schema_version`、`sample_id`、`task_id`、`source_run_id`、`payload`、`metadata`、`filter_status`、`invalid_for_training`、`invalid_reason` | Training Exporter | Training pipelines |

`TaskDefinition` 中的 `expected_files`、`fail_to_pass_tests`、`pass_to_pass_tests`、`gold_patch`、`declared_setup_mutations` 和 `generated_files` 都必须受 `visibility` / `visibility_policy` 约束。`gold_patch` 必须保持 `hidden_reference`；隐藏测试、reward-only 字段和 baseline 质量门控细节不得进入 ContextBuilder；`declared_setup_mutations` 和 `generated_files` 只用于 workspace 准备、patch 过滤、artifact 归因和训练样本边界控制。

`RunWorkspace.dependency_state` 表示运行时可直接交给 Workspace Adapter 或 final verifier 使用的依赖状态对象；`RunWorkspace.dependency_state_ref` 表示同一状态写入 run directory 后在 `artifacts.json` 或 `dependency_state.json` 中的引用。实现可以按需懒加载，但文档中的 final verifier 伪代码使用的是运行时对象语义，不能让 verification workspace 从未记录的本地路径隐式恢复依赖。

## 端到端数据流

1. Eval Runner 读取 `RunConfig` 和任务路径列表。
2. Task Adapter 读取 `TaskDefinition`，校验字段，并生成 `RunnableTask` 和静态 `VerifierConfig`。
3. Eval Runner 调用 Workspace Adapter 创建 setup workspace，并由 Workspace Adapter 执行 setup command；setup command 结束后、baseline verifier 运行前捕获 `dependency_state`。
4. Eval Runner 调用 Verifier baseline path 运行验证命令并解析 baseline verifier 结果。baseline verifier 产生的测试缓存、日志和覆盖率文件只作为 baseline artifact 或 excluded diff 处理，不进入可恢复到 agent run workspace 的 `dependency_state`。
5. Eval Runner 汇总 Workspace Adapter 和 Verifier 输出，生成 `BaselineResult`，包括 `dependency_state`、`setup_workspace_snapshot` 和 `agent_run_start_policy`。如果任务是 `invalid` 或 `flaky`，默认不进入正式 agent run。
6. Eval Runner 基于静态 `VerifierConfig` 和 `BaselineResult` 生成运行时 `ResolvedVerifierPlan`。baseline 发现的信息进入这个运行时计划，不反向修改任务定义或 Task Adapter 输出。
7. Eval Runner 为有效任务从 source checkout 创建正式 `RunWorkspace`，恢复 `dependency_state`，在正式运行起点生成 `agent_start_snapshot`，并以该 snapshot 作为 agent diff 基线。
8. Context Builder 根据 scaffold、`RunnableTask`、`RunWorkspace`、`RunConfig` 和 `ResolvedVerifierPlan` 构造初始 system message 与 user task message，并记录 prompt/context 版本。
9. 每轮模型调用前，Context Manager 根据 `context_management`、`budget_state` 和 `tool_pairing_state` 生成 provider-ready messages，并记录 `PreparedMessages`、`ContextReductionRecord` 与 `ContentReplacementState`。
10. Agent Loop 把完整 `PreparedMessages` 交给 Model Client；Model Client 把供应商原始响应标准化为 `ModelResponse` 和 `ToolCall`，并写入 `ModelCallEvent`、`raw_provider_request_ref` 和 `raw_provider_response_ref`。
11. Tool System 进行工具查找、schema 校验和工具级输入校验，构造 `ToolExecutionContext`。
12. Permission System 返回 `PermissionDecision`。
13. Tool System 把允许执行的文件或命令操作交给 Workspace Adapter。
14. Workspace Adapter 返回 `ExecutionResult`，Tool System 转换为 `ToolResult`。所有 tool call 必须配对 tool result，包括未知工具、`schema_validation_failed`、权限拒绝、timeout 和 interrupted。
15. Agent Loop 把 `ToolResult` 写回 messages，RunRecorder 写入 transcript、events 和 artifact manifest。
16. `run_tests` 调用 verifier feedback path，并把结构化结果作为中间反馈回流模型上下文。
17. Agent Loop 因 final answer、feedback tests passed、预算耗尽、timeout、no_progress 或错误停止，并记录 `agent_stop_reason`。
18. Trajectory Store 先从 `agent_start_snapshot` 捕获 `final.patch` 和 `final.diff`，冻结 agent 的最终贡献。
19. Final verifier 正式评测模式通过 strict patch replay 在 verification workspace 中应用 `final.patch` 后运行；快速调试模式可以在 agent run workspace 上验收，但必须记录 `final_verifier_mode`。
20. Eval Runner 根据 final verifier、`ResolvedVerifierPlan` 和 accepted policy 生成 `final_verifier_status` 和 `run_outcome`。
21. Reward module 根据 final verifier、events、diff 和 `ResolvedVerifierPlan` 生成 `RewardMetadata`。
22. Trajectory Store 写出 `artifacts.json`、`dependency_state.json`、`final.patch`、`final.diff`、`verifier.json`、`reward.json`、`metrics.json` 和 `summary.md`，并保证 `final.patch` / `final.diff` 已在 final verifier 前冻结。
23. Training Exporter 根据 `ExportPolicy` 从完整 run artifacts 生成 SFT、reinforcement learning rollout 或 preference pair `ExportRecord`。

## 第一版实现依赖选择

为了降低第一版落地不确定性，建议先固定最小技术选择：

- schema / object validation：优先使用 Pydantic v2；如果希望零运行时依赖，可以先用 `dataclasses` 加显式校验函数，但必须保持同一套字段名。
- task config：YAML 和 JSON 都可支持；若第一版只选一个，推荐先支持 YAML，并在 Task Adapter 中规范化为同一 `TaskDefinition`。
- CLI：第一版可以用标准库 `argparse`，后续再替换为 Typer 或 Click。
- fake / replay model：第一版 agent loop 测试应先支持脚本化 fake model 或 replay model，用来验证 tool call / tool result 配对、context event、permission denial 和 transcript，而不是一开始依赖真实模型供应商。
- Docker：第一版可以先通过本机 `docker` CLI 编排，不需要设计远程容器平台。

这些选择不是项目卖点，但应写入实现文档或 `pyproject.toml`，避免不同模块各自引入不兼容依赖。

## 统一错误与终止口径

错误类型、终止原因和失败诊断之间应保持映射关系：

- `invalid_tool_call` 属于模型或协议错误，预算内可以重试。
- `permission_denied` 属于权限决策结果，是否终止取决于权限模式和工具类型。
- `tool_error` 属于工具执行失败，通常可以把 observation 返回给模型继续修复。
- `test_timeout` 和 `assertion_failure` 属于 verifier feedback，通常不是 runtime crash。
- `dependency_install_failed` 属于 baseline invalid task，默认不产生训练轨迹。
- `context_limit` 属于上下文管理失败，压缩失败后才终止。
- `regression_detected` 属于 final verifier 或 pass-to-pass 检查结果，应进入 reward penalty 和 failure diagnostics。

## 设计边界

这篇文档定义第一版对象流和后续扩展接口。第一版已经实现最小可运行闭环，但本文中的真实模型供应商、Docker execution mode、复杂 scaffold 和更大规模导出能力仍然只是后续扩展方向，不能被 README、summary 或展示材料描述成已交付能力。
