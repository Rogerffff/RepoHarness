# Resume Narrative And Demo Artifacts

## 设计目标

这篇文档服务于后续简历、面试和项目展示。它描述 RepoHarness 未来实现完成后应该如何被解释，以及哪些 artifacts 可以作为展示材料。当前内容是设计阶段的 illustrative example，不表示这些 artifacts 已经由仓库运行生成。

## 一句话项目定位

RepoHarness 是一个面向 agentic training 和 post-training 的软件工程智能体 Harness 设计项目，目标是把真实或半真实仓库任务转化为可执行、可验证、可记录、可评测、可导出的训练数据闭环。

## 与已有项目的项目谱系

CaRR DeepSearch 展示了长轨迹搜索智能体、工具反馈、多轮 rollout、reward history 和长轨迹诊断经验。

Coding GRPO 展示了 verifier-based coding post-training、shared verifier、可执行代码反馈、稠密可验证奖励和 checkpoint evaluation 经验。

RepoHarness 计划把这些能力迁移到 repository-level software engineering tasks：模型不再只输出单段代码，而是在工作区里读文件、搜索、修改、多轮运行测试、记录轨迹、生成 patch，并把最终 verifier 结果变成 evaluation metrics 和 training export metadata。

## 面试中可以强调的技术难点

- 如何让工具结果稳定回流到下一轮模型上下文，而不是只作为旁路日志存在。
- 如何让训练 reward 和离线 evaluation 共用同一套 verifier，减少 reward/eval 口径漂移。
- 如何把 transcript 和 events 分开，让同一次运行既能对话重放，又能统计、诊断和导出训练数据。
- 如何区分 permission 和 sandbox：permission 决定是否允许执行，Docker-based executable repository environment 只提供可复现执行边界，不声称生产级安全隔离。
- 如何在同一任务、同一工具、同一 verifier 下比较 single-shot patch、simple ReAct 和 planner-coder-verifier scaffold。
- 如何记录失败类型，例如依赖安装失败、测试超时、无效工具调用、权限拒绝、上下文限制和 pass-to-pass regression。

## 未来展示 Artifact 清单

未来实现完成后，一个最小展示案例可以包含：

- 一个 `task.yaml`，展示 issue-style repository task。
- 一段 `transcript.jsonl`，展示模型如何调用工具、观察结果并继续修复。
- 一段 `events.jsonl`，展示工具事件、权限事件、verifier 事件和终止事件。
- 一个 `final.diff`，展示最终 patch。
- 一个 `verifier.json`，展示 fail-to-pass、pass-to-pass、accepted 和 error type。
- 一个 `metrics.json`，展示任务成功率、工具调用数、测试次数、patch size 和终止原因。
- 一个 reinforcement learning rollout JSONL 样例，展示 action-observation trajectory 和 reward metadata。
- 一个 preference pair JSONL 样例，展示同任务不同 rollout 如何按 final verifier 和 regression 情况排序。

## Illustrative Task

```yaml
id: repo_task_001
repo: ./fixtures/repos/buggy_calculator
issue: "Fix division by zero handling in calculator.divide without regressing existing arithmetic tests."
test_command: "pytest -q"
timeout_sec: 120
fail_to_pass_tests:
  - tests/test_calculator.py::test_divide_by_zero
pass_to_pass_tests:
  - tests/test_calculator.py::test_add
  - tests/test_calculator.py::test_multiply
```

## Illustrative Verifier Result

```json
{
  "accepted": true,
  "pass_ratio": 1.0,
  "fail_to_pass": {"passed": 1, "total": 1},
  "pass_to_pass": {"passed": 2, "total": 2},
  "exit_code": 0,
  "timeout": false,
  "error_type": null
}
```

## Illustrative Metrics Summary

```json
{
  "task_id": "repo_task_001",
  "success": true,
  "turn_count": 6,
  "tool_call_count": 14,
  "test_run_count": 3,
  "invalid_tool_call_count": 0,
  "permission_denial_count": 0,
  "patch_added_lines": 8,
  "patch_removed_lines": 2,
  "agent_stop_reason": "feedback_tests_passed",
  "final_verifier_status": "accepted",
  "run_outcome": "success"
}
```

## Illustrative Training Export Records

Reinforcement learning rollout record:

```json
{
  "sample_id": "repo_task_001_run_0001_rl",
  "task_id": "repo_task_001",
  "trajectory": [
    {
      "turn": 1,
      "action": {"type": "tool_call", "tool_name": "search", "arguments": {"query": "divide"}},
      "observation": {"preview": "calculator.py:12:def divide(a, b):"}
    }
  ],
  "reward": 0.91,
  "reward_metadata": {
    "reward_version": "repo_harness_reward_v0",
    "components": {
      "fail_to_pass_score": 1.0,
      "pass_to_pass_score": 1.0,
      "patch_size_penalty": 0.02
    }
  }
}
```

Preference pair record:

```json
{
  "sample_id": "repo_task_001_pair_0001",
  "task_id": "repo_task_001",
  "chosen": {"source_run_id": "run_success", "reward": 0.91},
  "rejected": {"source_run_id": "run_regression", "reward": 0.18},
  "reason": "chosen_passed_fail_to_pass_and_preserved_pass_to_pass"
}
```

## 简历阶段安全表述

设计阶段可以写：

> Designed a training-aware software engineering agent harness for repository-level tasks, specifying agent loop, tool contracts, permission boundaries, verifier-aligned reward metadata, trajectory logging, evaluation metrics, and training export schemas.

不应该写：

- 已实现生产级安全沙箱。
- 已完整复现 SWE-Bench。
- 已提出新的强化学习算法。
- 已训练出 frontier coding agent。
- 已复刻 Claude Code、Cursor 或 OpenHands。

进入实现阶段后，简历表述应该只根据真实完成的模块更新。例如完成 `run_tests` 和 final verifier 后，可以说“implemented verifier-aligned feedback and final evaluation path”；完成导出器后，可以说“exported SFT and rollout JSONL records from recorded trajectories”。
