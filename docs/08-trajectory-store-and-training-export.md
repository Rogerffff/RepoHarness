# Trajectory Store And Training Export

## 设计目标

Trajectory Store 把一次 agent run 变成可重放、可统计、可训练的数据资产。它是 RepoHarness 面向 post-training 的核心基础设施。

## 运行产物目录

未来实现中，每次运行应保存到：

```text
runs/
  20260428_153000_repo_task_001/
    task.yaml
    transcript.jsonl
    events.jsonl
    artifacts.json
    final.patch
    final.diff
    dependency_state.json
    verifier.json
    reward.json
    metrics.json
    summary.md
```

`runs/` 默认不提交 Git。

## Transcript 与 Events

transcript 面向对话重放，记录 system、user、assistant、tool call、tool result 和 verifier result。

events 面向评测统计、训练分析和失败诊断，记录结构化字段，例如时间、工具、输入摘要、输出摘要、错误类型和权限决策。

二者必须分开，避免把展示用文本当成唯一数据源。

## 运行产物内容契约

每个 run directory 中的文件语义如下：

- `task.yaml`：规范化后的任务定义，不只是原始输入文件的复制。
- `transcript.jsonl`：可重放对话，每行是 system、user、assistant、tool call、tool result、verifier result 或 termination summary。
- `events.jsonl`：结构化运行事件，用于统计、诊断、reward metadata 和训练导出。
- `artifacts.json`：artifact manifest，记录所有落盘 artifact 的路径、hash、大小、创建来源和脱敏状态。
- `final.patch`：可应用 patch，面向复现最终修改。
- `final.diff`：从 `agent_start_snapshot` 到最终 workspace 的完整 Git diff，面向人工审查和 patch size 统计。
- `dependency_state.json`：正式 agent run 开始前恢复的依赖状态、缓存路径、排除 diff 路径和 setup artifact 引用。
- `verifier.json`：final verifier 输出。即使任务失败，也应尽量生成。
- `reward.json`：RewardMetadata 输出，必须可追溯到 final verifier、events 和 diff。
- `metrics.json`：从 events、diff 和 verifier 输出聚合出来的运行指标。
- `summary.md`：面向人阅读的简要结论、失败原因和关键 artifact 路径。

失败运行也应该尽量生成完整产物。如果 run 在 workspace 创建前失败，可以只生成 `events.jsonl`、`metrics.json` 和 `summary.md`，并在 summary 中说明缺失 artifact 的原因。

完整工具输出不应塞进 transcript。大输出应写入 run directory 的 artifact 文件，并在 tool result 或 event 中记录 `artifact_refs`。`artifact_refs` 指向 `artifacts.json` 中的 `ArtifactRef`，而不是让每个模块各自保存裸路径字符串。

如果未来实现支持中间 turn resume，需要额外保存 `checkpoints/` 目录，例如 per-turn patch chain 或 workspace snapshot。第一版默认只要求从 final workspace 继续，不要求恢复到任意中间 turn。

## RunRecorder 与 Artifact Manifest

运行时模块不应各自打开文件追加 JSONL。第一版应通过统一 `RunRecorder` 写入 transcript、events 和 artifact：

```text
RunRecorder:
  append_transcript(record)
  append_event(event)
  write_artifact(kind, bytes_or_path, metadata) -> ArtifactRef
  finalize_run(summary)
```

`ArtifactRef` 至少包含：

```text
artifact_id
relative_path
kind
sha256
size_bytes
created_by_event_id
redaction_status
retention_policy
```

events、transcript、verifier、reward metadata 和 training export 都应通过 `artifact_id` 或 manifest 中的相对路径引用完整日志、原始模型响应、测试输出、diff 或大工具输出。这样可以避免同一份输出在不同文件中重复保存，也方便后续脱敏、清理和复现实验。

`RunRecorder` 写入必须具备最小幂等策略：

- `append_transcript` 和 `append_event` 使用稳定 `record_id` / `event_id`，崩溃恢复时可以检测重复写入。
- artifact 写入先落到临时文件，完成 hash 校验后再进入 `artifacts.json`。
- `finalize_run(summary)` 可以重复调用；重复调用不能改写已有事实记录，只能补齐 summary、metrics 或 finalize 状态。
- 如果运行在中途崩溃，已有 transcript、events 和 artifacts manifest 仍应可被 `inspect-run` 读取，并在 summary 中标记 `run_outcome = "interrupted"` 或 `inconclusive`。

## TranscriptRecord Schema

`transcript.jsonl` 不能只保存自由文本。第一版最小 `TranscriptRecord` 应包含：

```text
TranscriptRecord:
  schema_version
  record_id
  run_id
  task_id
  turn
  role: system | user | assistant | tool | verifier | termination
  message_id
  parent_message_id
  model_call_id
  tool_call_id
  tool_result_id
  context_revision
  content_preview
  content_artifact_refs
  model_visible
  trainable
  created_at
```

`model_visible` 表示这条记录是否进入过模型上下文；`trainable` 表示导出时是否可以作为模型生成目标候选。baseline verifier 和 formal final verifier 可以进入 transcript 或 summary 供重放和阅读，但默认 `model_visible = false`，不能被训练导出误当成 agent 中间 observation。

## Event 字段

events 采用“通用字段 + 按事件类型扩展字段”的结构，而不是要求所有事件都带工具字段。

通用字段：

- `schema_version`
- `event_id`
- `timestamp`
- `run_id`
- `task_id`
- `turn`
- `event_type`
- `severity`
- `duration_ms`
- `error_type`
- `artifact_refs`

工具事件扩展字段：

- `tool_name`
- `tool_call_id`
- `requested_arguments`
- `normalized_arguments`
- `effective_arguments`
- `normalization_policy_version`
- `normalized_input_hash`
- `tool_output_preview`
- `exit_code`
- `truncated`
- `permission_decision`

权限事件扩展字段：

- `permission_decision`
- `matched_rule`
- `reason`
- `mode`
- `workspace_path`

verifier 事件扩展字段：

- `verifier_stage`：`baseline`、`feedback` 或 `final`。
- `accepted`
- `pass_ratio`
- `fail_to_pass`
- `pass_to_pass`
- `timeout`
- `verifier_result_ref`

`verifier_result_ref` 必须引用 `artifacts.json` 中的 `ArtifactRef`，而不是裸路径字符串。baseline、feedback 和 final verifier 的完整结构化结果都应通过 artifact manifest 追踪 hash、大小、创建事件和脱敏状态。

上下文事件扩展字段：

- `context_action`：例如 `truncate_tool_output`、`summarize_test_output`、`drop_old_turns`。
- `context_revision`
- `context_policy_version`
- `source_message_ids`
- `kept_message_ids`
- `dropped_message_ids`
- `replaced_tool_result_ids`
- `replacement_artifact_refs`
- `replacement_preview_hash`
- `summary_artifact_ref`
- `tokens_before`
- `tokens_after`
- `model_visible`
- `token_estimator_version`

context event 必须能复盘模型本轮实际看到的 messages。训练导出使用的 observation 应来自对应 `context_revision` 的 model-visible 内容，而不是导出时重新生成的摘要或后处理 preview。

终止事件扩展字段：

- `agent_stop_reason`
- `final_verifier_status`
- `run_outcome`
- `final_verifier_accepted`
- `metrics_path`
- `summary`

## 训练导出格式

第一版设计三类导出。以下格式是未来实现的最小 schema，不表示当前仓库已经生成这些文件。

SFT JSONL：

```json
{
  "schema_version": "repo_harness_export_v0",
  "sample_id": "repo_task_001_run_0001_sft",
  "task_id": "repo_task_001",
  "messages": [
    {"role": "system", "content": "You are a software engineering agent..."},
    {"role": "user", "content": "Fix division by zero handling..."},
    {"role": "assistant", "tool_calls": [{"name": "read_file", "arguments": {"path": "calculator.py"}}]},
    {"role": "tool", "name": "read_file", "content": "def divide(..."}
  ],
  "trainable_messages": [2],
  "loss_mask": [0, 0, 1, 0],
  "observation_mask": [0, 0, 0, 1],
  "target": {
    "final_patch": "diff --git ...",
    "termination_summary": "Tests passed after updating divide error handling."
  },
  "verifier": {"accepted": true, "pass_ratio": 1.0},
  "reward_metadata_ref": {"artifact_id": "artifact_reward_001", "relative_path": "reward.json"},
  "invalid_for_training": false,
  "invalid_reason": null,
  "metadata": {
    "export_policy_version": "repo_harness_export_policy_v0",
    "scaffold_id": "simple_react",
    "source_run_id": "run_0001"
  }
}
```

Reinforcement learning rollout JSONL：

```json
{
  "schema_version": "repo_harness_export_v0",
  "sample_id": "repo_task_001_run_0001_rl",
  "task_id": "repo_task_001",
  "prompt": "Issue statement and repository context...",
  "trajectory": [
    {
      "turn": 1,
      "action": {"type": "tool_call", "tool_name": "grep", "arguments": {"query": "divide"}},
      "observation": {"preview": "calculator.py:12:def divide", "truncated": false}
    }
  ],
  "reward": 0.89,
  "reward_metadata": {
    "reward_version": "repo_harness_reward_v0",
    "reward_metadata_ref": {"artifact_id": "artifact_reward_001", "relative_path": "reward.json"}
  },
  "invalid_for_training": false,
  "invalid_reason": null,
  "metadata": {
    "export_policy_version": "repo_harness_export_policy_v0",
    "source_run_id": "run_0001",
    "verifier_result_ref": {"artifact_id": "artifact_final_verifier_001", "relative_path": "verifier.json"}
  }
}
```

Preference pair JSONL：

```json
{
  "schema_version": "repo_harness_export_v0",
  "sample_id": "repo_task_001_pair_0001",
  "task_id": "repo_task_001",
  "chosen": {"source_run_id": "run_success", "reward": 0.91, "final_patch": "diff --git ..."},
  "rejected": {"source_run_id": "run_failed", "reward": 0.22, "final_patch": "diff --git ..."},
  "reason": "higher_final_verifier_score_and_no_regression",
  "metadata": {
    "pairing_policy": "same_task_rollout_ranking_v0",
    "chosen_verifier_result_ref": {"artifact_id": "artifact_success_verifier_001", "relative_path": "runs/run_success/verifier.json"},
    "rejected_verifier_result_ref": {"artifact_id": "artifact_failed_verifier_001", "relative_path": "runs/run_failed/verifier.json"}
  }
}
```

后续可以增加 `verl` parquet，但第一阶段只设计接口，不承诺实现。

## 数据质量过滤

导出时必须能筛选：

- 成功轨迹。
- 部分成功轨迹。
- 工具失败轨迹。
- 测试失败但含有有效中间步骤的轨迹。
- 无效工具调用过多的轨迹。
- 权限拒绝过多的轨迹。
- 超时轨迹。

过滤策略必须写入 export metadata，保证训练数据可追溯。

监督微调导出必须明确哪些 assistant message 参与 loss。tool result 是环境 observation，不应作为模型生成目标；system、user task、verifier observation 默认也不参与 assistant loss。强化学习 rollout 导出必须区分 prompt、action、observation、final reward、invalid sample 原因和 reward metadata 来源。

## 数据脱敏与 Secret Scanning

进入真实仓库或真实 issue 前，导出流程必须包含脱敏策略：

- artifact 写入前或导出前运行 secret scan。
- export record、ArtifactRef 和 manifest 记录 `redaction_status`。
- 被脱敏字段保留占位符和原因，例如 `<REDACTED_SECRET:github_token>`。
- 默认不导出 `.env`、证书、私钥、token 文件和用户本地绝对路径。
- operational telemetry 可以用于本地调试，但默认不进入训练导出。

## 可复现实验字段

每条 export record 至少应保留这些 metadata，方便复现实验和解释训练数据来源：

- `model_id`
- `scaffold_id`
- `task_version`
- `dataset_name`
- `dataset_split`
- `source_kind`
- `decontamination_status`
- `repo_base_commit`
- `docker_image`
- `test_command`
- `timeouts`
- `seed`
- `temperature`
- `max_turns`
- `max_tool_calls`
- `tool_policy`
- `permission_mode`
- `execution_mode`
- `schema_version`
- `export_policy_version`
- `tool_policy_version`
- `permission_policy_version`
- `context_builder_version`
- `prompt_template_version`

## Claude Code 参考

参考模块：

- `reference/claude-code-docs/claude-doc/10-context-memory-session.md`
- `reference/claude-code-typescript-src/query.ts`
- `reference/claude-code-typescript-src/services/compact/`
- `reference/claude-code-typescript-src/services/SessionMemory/`

RepoHarness 借鉴 transcript 和 session 思想，但记录格式面向训练和评测，而不是产品 UI。
