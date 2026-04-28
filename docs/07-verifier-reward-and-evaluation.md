# Verifier, Reward, And Evaluation

## 设计目标

Verifier 是 RepoHarness 区别于普通 coding agent demo 的关键。它把仓库修改和测试执行结果转成可复核的评测指标与 reward metadata。训练奖励和离线评测必须共用同一套 verifier，避免 reward 和 evaluation 口径漂移。

## Verifier 输出格式

第一版 verifier 输出：

```json
{
  "accepted": false,
  "pass_ratio": 0.62,
  "fail_to_pass": {"passed": 3, "total": 5},
  "pass_to_pass": {"passed": 20, "total": 21},
  "exit_code": 1,
  "timeout": false,
  "error_type": "assertion_failure"
}
```

字段含义：

- `accepted`：任务是否通过最终验收。
- `pass_ratio`：测试或验证项整体通过比例。
- `fail_to_pass`：目标失败测试中被修复为通过的数量。
- `pass_to_pass`：原本通过的测试中仍然通过的数量。
- `exit_code`：验证命令退出码。
- `timeout`：验证是否超时。
- `error_type`：失败分类。

## Reward Prototype

第一版 reward 只是 prototype：

```text
reward = 0.7 * fail_to_pass_ratio
       + 0.2 * pass_to_pass_ratio
       + 0.1 * accepted
       - cost_penalty
       - patch_size_penalty
```

这不是新的强化学习算法，也不是论文贡献。它只是 verifier-aligned reward metadata，用于后续 SFT / reinforcement learning 数据导出和实验设计。

## Reward Metadata Schema

未来实现应把 reward 计算结果保存为可审计的 `RewardMetadata`，而不是只保存一个浮点数：

```json
{
  "reward_version": "repo_harness_reward_v0",
  "final_reward": 0.73,
  "verifier": {
    "accepted": true,
    "fail_to_pass": {"passed": 5, "total": 5},
    "pass_to_pass": {"passed": 21, "total": 21},
    "pass_ratio": 1.0
  },
  "components": {
    "fail_to_pass_score": 1.0,
    "pass_to_pass_score": 1.0,
    "accepted_bonus": 1.0,
    "cost_penalty": 0.08,
    "patch_size_penalty": 0.03,
    "regression_penalty": 0.0,
    "timeout_penalty": 0.0
  },
  "sources": {
    "turn_count": 7,
    "tool_call_count": 18,
    "test_run_count": 4,
    "patch_added_lines": 12,
    "patch_removed_lines": 3,
    "duration_ms": 182000
  },
  "invalid_for_training": false,
  "invalid_reason": null
}
```

字段来源必须可追溯：

- verifier 原始结果来自 final verifier，不来自人工判断。
- `turn_count`、`tool_call_count`、`test_run_count` 和 `duration_ms` 来自 events。
- patch size 来自 `final.diff` 或 Git diff 统计。
- timeout 和 permission denial 来自结构化 events。

边界条件必须保守处理：如果 `fail_to_pass.total = 0`，不能把 fail-to-pass score 默认为满分，应把任务标记为不适合该 reward 分量，或使用只依赖 pass-to-pass 和 accepted 的备用公式。flaky 或 invalid task 默认 `invalid_for_training = true`。一旦 final verifier 发现 pass-to-pass regression，应施加强惩罚，即使目标失败测试已经通过。

## `run_tests` 与最终验收

`run_tests` 是 agent 可以调用的中间反馈工具。它调用 verifier 的 feedback path，把测试失败摘要返回给模型，帮助模型继续修复。

最终评测必须在 agent 停止后重新运行 final verifier。reward metadata、任务成功率、fail-to-pass、pass-to-pass 和训练导出默认都使用 final verifier 的结果。这样可以避免模型在中间测试通过后继续修改代码导致最终工作区回归。

## 评测指标

批量评测设计应至少输出：

- task success rate。
- fail-to-pass pass rate。
- pass-to-pass preservation rate。
- mean pass ratio。
- average turns。
- average tool calls。
- average test runs。
- timeout rate。
- invalid tool call rate。
- permission denial rate。
- average patch size。
- termination reason distribution。

这些指标必须来自 events 和 verifier 输出，而不是人工观察。

## 对比实验设计

第一版未来评测建议：

- single-shot patch baseline vs multi-turn harness。
- no test feedback vs test feedback。
- local process vs Docker execution。
- simple ReAct vs planner-coder-verifier。
- sparse accepted reward vs dense pass ratio reward。

每个实验都应记录成本、成功率、测试运行次数和失败模式。

## 失败案例分析

评测报告必须包含失败案例：

- dependency installation failed。
- test command error。
- context insufficient。
- patch too large。
- test timeout。
- tool misuse。
- new test passed but old test regressed。

## Claude Code 参考

Claude Code 没有训练 reward 模块，但其 tool result、termination、transcript 和 task notification 设计可作为结构参考：

- `reference/claude-code-docs/claude-code-ai-core-codex/06-end-to-end-ai-sequences.md`
- `reference/claude-code-typescript-src/query.ts`
- `reference/claude-code-typescript-src/services/tools/toolExecution.ts`
