# Verifier, Reward, And Evaluation

## 设计目标

Verifier 是 RepoHarness 区别于普通 coding agent demo 的关键。它把仓库修改和测试执行结果转成可复核的评测指标与 reward metadata。训练奖励和离线评测必须共用同一套 verifier，避免 reward 和 evaluation 口径漂移。

## Verifier 输出格式

第一版 verifier 输出：

```json
{
  "parser_id": "pytest",
  "parser_version": "pytest_parser_v0",
  "parser_confidence": 0.92,
  "command": "pytest -q",
  "test_cases": [
    {"test_id": "tests/test_calculator.py::test_divide_zero", "status": "failed", "duration_ms": 430}
  ],
  "accepted": false,
  "pass_ratio": 0.62,
  "fail_to_pass": {"passed": 3, "total": 5},
  "pass_to_pass": {"passed": 20, "total": 21},
  "exit_code": 1,
  "timeout": false,
  "error_type": "assertion_failure",
  "acceptance_policy_version": "repo_harness_acceptance_policy_v0",
  "accepted_fallback_reason": null
}
```

字段含义：

- `parser_id`：使用的测试输出解析器标识，例如 `pytest`。
- `parser_version`：解析器版本，保证历史 verifier 结果可以解释。
- `parser_confidence`：解析器对测试用例级结果的可信度。
- `command`：实际执行的 verifier 命令。
- `test_cases`：测试用例级结果列表，用于计算 fail-to-pass、pass-to-pass 和 regression。
- `accepted`：任务是否通过最终验收。
- `pass_ratio`：测试或验证项整体通过比例。
- `fail_to_pass`：目标失败测试中被修复为通过的数量。
- `pass_to_pass`：原本通过的测试中仍然通过的数量。
- `exit_code`：验证命令退出码。
- `timeout`：验证是否超时。
- `error_type`：失败分类。
- `acceptance_policy_version`：`accepted` 字段的确定性派生规则版本。
- `accepted_fallback_reason`：没有声明 fail-to-pass 和 pass-to-pass 时，记录是否退化为整体 exit code 判定。

## Verifier Parser 与 TestCaseResult

第一版可以只实现 `pytest` parser，但文档和对象模型必须预留跨语言 verifier parser。Verifier 不应只保存整体 exit code，还应尽量保存测试用例级结果：

`VerifierParser` 是 verifier 内部的解析组件。Verifier 负责决定在哪里运行验证命令、调用 Workspace Adapter 执行命令、拿到 stdout、stderr、exit code 和 timeout；`VerifierParser` 负责把这些原始输出转换成结构化测试结果。它不安装依赖，不创建 workspace，也不决定 reward。

例如 `pytest -q` 的原始输出可能是：

```text
FAILED tests/test_calculator.py::test_divide_zero - AssertionError
1 failed, 8 passed in 0.43s
```

`pytest` parser 应把它解析成：

```json
{
  "parser_id": "pytest",
  "parser_version": "pytest_parser_v0",
  "parser_confidence": 0.92,
  "test_cases": [
    {
      "test_id": "tests/test_calculator.py::test_divide_zero",
      "status": "failed",
      "duration_ms": null,
      "failure_preview": "AssertionError",
      "raw_output_ref": {
        "artifact_id": "artifact_verifier_pytest_004",
        "relative_path": "artifacts/verifier/turn_004_pytest.txt"
      }
    }
  ]
}
```

有了测试用例级结果，RepoHarness 才能可靠计算 fail-to-pass、pass-to-pass、flaky tests、regression 和 reward metadata。如果 parser 只能确定整体命令失败，但无法识别具体测试用例，就必须降低 `parser_confidence`，并避免伪造精细统计。

```text
TestCaseResult:
  test_id
  status: passed | failed | skipped | error | timeout | unknown
  duration_ms
  failure_preview
  raw_output_ref

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
  accepted_fallback_reason
  error_type
  acceptance_policy_version
```

规则：

- `parser_confidence` 表示解析器对测试用例级结果的可信度。无法稳定解析测试用例时，不能伪造 fail-to-pass 或 pass-to-pass 统计。
- `raw_output_ref` 必须引用 `artifacts.json` 中的 `ArtifactRef`，而不是裸路径字符串。这样 verifier 原始输出可以统一参与 hash 校验、脱敏、保留策略和训练导出审计。
- 测试命令本身无法启动、依赖缺失或测试框架崩溃，应标记为 `test_command_error`、`dependency_error` 或 `parser_error`，不能混成普通 `assertion_failure`。
- baseline 可以配置重复运行次数，用于发现 flaky tests。重复运行结果不一致时，任务应标记为 `flaky`，默认不进入训练轨迹。
- feedback verifier、baseline verifier 和 final verifier 必须共用同一套 parser 和结果 schema，只通过 `verifier_stage` 区分用途。

## Accepted 判定规则

`VerifierResult.accepted` 必须由确定性规则派生，不能由不同 parser 自由解释。第一版建议 `repo_harness_acceptance_policy_v0`：

- 如果 `final.patch` 无法应用到 verification workspace，`accepted = false`，`error_type = "patch_apply_failed"`。
- 如果测试命令无法启动，`accepted = false`，`error_type = "test_command_error"` 或 `dependency_error`。
- 如果 final verifier 超时，`accepted = false`，`final_verifier_status = "timeout"`。
- 如果存在 fail-to-pass tests，则必须全部通过。
- 如果存在 pass-to-pass tests，则必须全部保持通过。
- 如果没有声明 fail-to-pass 和 pass-to-pass，则可以退化为整体测试命令 exit code 为 0，但必须记录 `acceptance_policy_version` 和 `accepted_fallback_reason`。
- 如果 `parser_confidence` 低于配置阈值，不能生成精细 fail-to-pass / pass-to-pass 成功结论；`repo_harness_acceptance_policy_v0` 应设置 `accepted = false`、`error_type = "low_parser_confidence"`，并由 Eval Runner 派生 `final_verifier_status = "error"`、`run_outcome = "inconclusive"`。

formal final verifier 的 `accepted` 是任务成功率、reward metadata 和训练过滤的默认依据。feedback verifier 可以帮助 agent 停止或继续修复，但不能替代 formal final verifier。

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
  "final_reward": 0.89,
  "formula": "0.7 * fail_to_pass_score + 0.2 * pass_to_pass_score + 0.1 * accepted_bonus - cost_penalty - patch_size_penalty - regression_penalty - timeout_penalty",
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
  "invalid_reason": null,
  "acceptance_policy_version": "repo_harness_acceptance_policy_v0",
  "reward_clip_range": [0.0, 1.0]
}
```

`components` 中的 score 字段是归一化后的原始分量，penalty 字段是已经按当前 reward version 换算后的扣分值。以上示例的计算过程是 `0.7 * 1.0 + 0.2 * 1.0 + 0.1 * 1.0 - 0.08 - 0.03 = 0.89`。如果未来实现改成保存加权后分量，必须在 `reward_version` 和 `formula` 中明确说明，不能让示例值和公式不一致。

字段来源必须可追溯：

- verifier 原始结果来自 final verifier，不来自人工判断。
- `turn_count`、`tool_call_count`、`test_run_count` 和 `duration_ms` 来自 events。
- patch size 来自 `final.diff` 或 Git diff 统计。
- timeout 和 permission denial 来自结构化 events。

V4 以后，RewardMetadata 还必须保留 `version`、`formula`、`components`、`sources`、`invalid_for_training` 和 `invalid_reason` 等字段，并和 export audit 的训练资格判断分离。`reward scalar` 和 `reward label` 只能位于非模型可见、字段路径受 allowlist 约束的 structured reward、RewardMetadata、reward audit report 或 audit-only metadata 中，不能进入 prompt、action、observation、assistant target、SFT target 或 preference target。导出审计不能只检查 `model_visible = false`，还必须校验 allowlist 字段路径。

边界条件必须保守处理：如果 `fail_to_pass.total = 0`，不能把 fail-to-pass score 默认为满分，应把任务标记为不适合该 reward 分量，或使用只依赖 pass-to-pass 和 accepted 的备用公式。flaky 或 invalid task 默认 `invalid_for_training = true`。一旦 final verifier 发现 pass-to-pass regression，应施加强惩罚，即使目标失败测试已经通过。

第一版 `final_reward` 建议裁剪到 `[0.0, 1.0]`，并把裁剪区间写入 `RewardMetadata`。如果 `parser_confidence` 低于阈值、patch replay 失败、final verifier timeout 或 accepted policy 无法给出确定结论，应设置 `invalid_for_training = true` 或在 export filter 中标记为 `inconclusive`，不能把低置信 verifier 结果当作可靠强化学习奖励。

## `run_tests` 与最终验收

`run_tests` 是 agent 可以调用的中间反馈工具。它调用 verifier 的 feedback path，把测试失败摘要返回给模型，帮助模型继续修复。

最终评测必须在 agent 停止后重新运行 final verifier。reward metadata、任务成功率、fail-to-pass、pass-to-pass 和训练导出默认都使用 final verifier 的结果。这样可以避免模型在中间测试通过后继续修改代码导致最终工作区回归。

导出样本不能只声明 `final_verifier_result` 字段，还必须能回指同一 run 的 final verifier boundary evidence。V4 最新复核曾发现 Stage 6 导出样本引用了没有 Stage 5 boundary report 支撑的 final verifier 结果；修复完成前，任何 acceptance 或 export 结论都应显式检查这条证据链。

正式评测模式应支持 strict final verifier：从 source checkout 创建 verification workspace，恢复合法 `dependency_state`，应用 `final.patch`，再运行 final verifier。快速调试模式可以直接在 agent run workspace 上运行 final verifier，但 metrics 和 summary 必须记录所用模式，避免把模型临时安装依赖或运行时副作用误当成可复现 patch 成功。

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
- agent stop reason distribution。
- final verifier status distribution。
- run outcome distribution。

这些指标必须来自 events 和 verifier 输出，而不是人工观察。

可以预留但不阻塞第一版闭环的质量指标：

- code quality check result，例如 lint、type check、format check。
- interaction efficiency，例如重复读取率、无效工具调用率、过度测试率。
- patch locality，例如是否修改了 expected files 之外的大量文件。
- instruction adherence，例如是否修改了任务不允许修改的文件。

这些指标用于后续更接近真实软件工程任务的评测，不应在第一版还没有跑通 verifier 闭环前扩大实现范围。

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
