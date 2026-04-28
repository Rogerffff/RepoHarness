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
    final.patch
    final.diff
    verifier.json
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
- `final.patch`：可应用 patch，面向复现最终修改。
- `final.diff`：完整 Git diff，面向人工审查和 patch size 统计。
- `verifier.json`：final verifier 输出。即使任务失败，也应尽量生成。
- `metrics.json`：从 events、diff 和 verifier 输出聚合出来的运行指标。
- `summary.md`：面向人阅读的简要结论、失败原因和关键 artifact 路径。

失败运行也应该尽量生成完整产物。如果 run 在 workspace 创建前失败，可以只生成 `events.jsonl`、`metrics.json` 和 `summary.md`，并在 summary 中说明缺失 artifact 的原因。

完整工具输出不应塞进 transcript。大输出应写入 run directory 的 artifact 文件，并在 tool result 或 event 中记录 `output_path`。

## Event 字段

events 采用“通用字段 + 按事件类型扩展字段”的结构，而不是要求所有事件都带工具字段。

通用字段：

- `timestamp`
- `run_id`
- `task_id`
- `turn`
- `event_type`
- `severity`
- `duration_ms`
- `error_type`
- `artifact_paths`

工具事件扩展字段：

- `tool_name`
- `tool_call_id`
- `tool_input`
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
- `verifier_result_path`

上下文事件扩展字段：

- `context_action`：例如 `truncate_tool_output`、`summarize_test_output`、`drop_old_turns`。
- `tokens_before`
- `tokens_after`
- `summary_path`

终止事件扩展字段：

- `termination_reason`
- `final_verifier_accepted`
- `metrics_path`
- `summary`

## 训练导出格式

第一版设计三类导出。以下格式是未来实现的最小 schema，不表示当前仓库已经生成这些文件。

SFT JSONL：

```json
{
  "sample_id": "repo_task_001_run_0001_sft",
  "task_id": "repo_task_001",
  "messages": [
    {"role": "system", "content": "You are a software engineering agent..."},
    {"role": "user", "content": "Fix division by zero handling..."},
    {"role": "assistant", "tool_calls": [{"name": "read_file", "arguments": {"path": "calculator.py"}}]},
    {"role": "tool", "name": "read_file", "content": "def divide(..."}
  ],
  "target": {
    "final_patch": "diff --git ...",
    "termination_summary": "Tests passed after updating divide error handling."
  },
  "verifier": {"accepted": true, "pass_ratio": 1.0},
  "metadata": {"scaffold_id": "simple_react", "source_run_id": "run_0001"}
}
```

Reinforcement learning rollout JSONL：

```json
{
  "sample_id": "repo_task_001_run_0001_rl",
  "task_id": "repo_task_001",
  "prompt": "Issue statement and repository context...",
  "trajectory": [
    {
      "turn": 1,
      "action": {"type": "tool_call", "tool_name": "search", "arguments": {"query": "divide"}},
      "observation": {"preview": "calculator.py:12:def divide", "truncated": false}
    }
  ],
  "reward": 0.73,
  "reward_metadata": {"reward_version": "repo_harness_reward_v0"},
  "metadata": {"source_run_id": "run_0001", "verifier_result_path": "verifier.json"}
}
```

Preference pair JSONL：

```json
{
  "sample_id": "repo_task_001_pair_0001",
  "task_id": "repo_task_001",
  "chosen": {"source_run_id": "run_success", "reward": 0.91, "final_patch": "diff --git ..."},
  "rejected": {"source_run_id": "run_failed", "reward": 0.22, "final_patch": "diff --git ..."},
  "reason": "higher_final_verifier_score_and_no_regression",
  "metadata": {"pairing_method": "same_task_rollout_ranking"}
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

## 可复现实验字段

每条 export record 至少应保留这些 metadata，方便复现实验和解释训练数据来源：

- `model_id`
- `scaffold_id`
- `task_version`
- `repo_base_commit`
- `docker_image`
- `test_command`
- `timeout_sec`
- `seed`
- `temperature`
- `max_turns`
- `max_tool_calls`
- `tool_policy`
- `permission_mode`
- `execution_mode`

## Claude Code 参考

参考模块：

- `reference/claude-code-docs/claude-doc/10-context-memory-session.md`
- `reference/claude-code-typescript-src/query.ts`
- `reference/claude-code-typescript-src/services/compact/`
- `reference/claude-code-typescript-src/services/SessionMemory/`

RepoHarness 借鉴 transcript 和 session 思想，但记录格式面向训练和评测，而不是产品 UI。
