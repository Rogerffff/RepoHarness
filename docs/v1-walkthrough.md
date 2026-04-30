# RepoHarness V1 Walkthrough

本文档演示第一版 RepoHarness 的端到端流程。所有命令都使用 replay model，不会调用真实模型供应商。

## 1. 校验任务

```bash
repo-harness validate-task tests/fixtures/tasks/task_001.yaml
```

这个命令只读取和校验任务定义。它不会创建 workspace，不会运行测试，也不会生成 `BaselineResult`。

## 2. 运行单个 replay agent

```bash
repo-harness run-task \
  tests/fixtures/tasks/task_001.yaml \
  --config tests/fixtures/run_configs/replay_success.yaml \
  --output-dir runs/walkthrough \
  --run-id walkthrough-success
```

`run-task` 会按顺序执行：

1. 加载任务和配置。
2. 创建 source checkout 和 setup workspace。
3. 运行 baseline verifier 并生成 `baseline.json`。
4. baseline 通过后生成 `resolved_verifier_plan.json`。
5. 创建 agent workspace。
6. 运行 replay model 驱动的 Agent Loop。
7. 冻结 `final.patch` 和 `final.diff`。
8. 在独立 verification workspace 中执行 strict patch replay final verifier。
9. 写出 `verifier.json`、`reward.json`、`metrics.json` 和 `summary.md`。

## 3. 检查运行产物

```bash
repo-harness inspect-run runs/walkthrough/walkthrough-success
```

你会看到 task id、run outcome、agent stop reason、final verifier status、baseline status、reward 和关键 artifact 列表。

常用文件：

- `events.jsonl`：按时间排序的结构化事件。
- `transcript.jsonl`：system、user、assistant 和 tool observation 记录。
- `artifacts.json`：所有 artifact 的相对路径、sha256 和类型。
- `final.patch`：formal final verifier 使用的冻结补丁。
- `verifier.json`：formal final verifier 结果。
- `reward.json`：final reward 和 reward metadata。

## 4. 批量运行

```bash
repo-harness run-batch \
  --config tests/fixtures/run_configs/batch_replay.yaml \
  --output-dir runs/walkthrough-batch
```

第一版 batch runner 顺序运行任务，默认并发为 1。`batch_manifest.json` 会记录每个任务的 run directory、run id、状态、失败原因和关键 artifact。

invalid 和 flaky task 会被 quality gate 阻断，不会创建正式 agent workspace，不会生成正式 `ResolvedVerifierPlan`，也不会进入 Agent Loop。

## 5. 导出训练数据

单个 run：

```bash
repo-harness export runs/walkthrough/walkthrough-success --format sft_jsonl
repo-harness export runs/walkthrough/walkthrough-success --format rl_jsonl
```

批量 runs 根目录：

```bash
repo-harness export runs/walkthrough-batch --format sft_jsonl
repo-harness export runs/walkthrough-batch --format rl_jsonl
repo-harness export runs/walkthrough-batch --format preference_jsonl
```

导出器只读取已有 run directory，不重新运行 verifier，也不改写原始轨迹事实。SFT 导出中 assistant action 是训练目标，tool observation 不是 loss target。RL rollout 的 final reward 来自 `reward.json`，并且导出器会校验它来自 strict patch replay 的 formal final verifier。

## 6. 失败样例

下面这些配置可以生成可复盘失败或边界样例：

```bash
repo-harness run-task tests/fixtures/tasks/task_001.yaml \
  --config tests/fixtures/run_configs/replay_failure_minimal.yaml \
  --output-dir runs/walkthrough-extras \
  --run-id final-verifier-failed

repo-harness run-task tests/fixtures/tasks/task_security_probe.yaml \
  --config tests/fixtures/run_configs/replay_security_negative_minimal.yaml \
  --output-dir runs/walkthrough-extras \
  --run-id permission-denied

repo-harness run-task tests/fixtures/tasks/task_001.yaml \
  --config tests/fixtures/run_configs/replay_unknown_tool.yaml \
  --output-dir runs/walkthrough-extras \
  --run-id unknown-tool
```

这些样例分别覆盖 final verifier failed、permission denied 和 invalid tool call 路径。
