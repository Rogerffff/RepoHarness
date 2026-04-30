# RepoHarness

RepoHarness 是一个面向 agentic training / post-training 的轻量级软件工程智能体 Harness。第一版已经可以在微型仓库任务上跑通下面这条闭环：

```text
task -> executable workspace -> tools -> agent loop -> trajectory -> verifier -> reward/eval/export
```

它的目标是让真实或半真实仓库任务产生可执行、可审计、可导出的训练轨迹，而不是复刻 Claude Code、Cursor、OpenHands 或 SWE-Bench。第一版使用本地微型仓库、脚本回放模型和模拟模型来验证协议，不接入真实模型供应商。

## 第一版已经实现

- Task Adapter：读取、校验和规范化任务定义；不创建 workspace，不运行测试，不生成 baseline。
- Workspace Adapter：创建 source/setup/agent/verification workspace，通过本地进程执行命令，捕获 `final.patch` 和 `final.diff`。
- Verifier：基于 pytest 的 baseline、feedback 和 final verifier，共用 `VerifierResult` schema 和 accepted policy。
- Tool System：`list_files`、`read_file`、`grep`、`edit_file`、`create_file`、受限 `bash`、`run_tests`、`git_diff`。
- Permission System：工具 schema 校验后才进入权限决策；未知工具在工具查找阶段生成 invalid tool event 和配对 ToolResult。
- Context Builder / Context Manager：构建模型可见上下文，记录 `PreparedMessages`、context event 和 content replacement state。
- Fake Model / Replay Model：模拟模型和脚本回放模型，用于验证 tool call / tool result 协议、权限拒绝、上下文事件和 final verifier。
- Agent Loop：多轮 action-observation 循环，支持 final answer、feedback tests passed、预算停止和中断 tool result 配对。
- Eval Runner 和 CLI：`validate-task`、`run-task`、`run-batch`、`inspect-run`。
- Training Exporter：监督微调 JSONL（`sft_jsonl`）、强化学习 rollout JSONL（`rl_jsonl`）和最小 preference pair JSONL 导出，只读取已有 run directory。

## 明确没有实现

- 没有生产级安全沙箱；第一版只是本地执行边界和路径/权限约束。
- 没有接入真实模型供应商；第一版使用 replay/fake model 验证协议。
- 没有声称完成强化学习训练；这里只导出可供后续训练使用的数据。
- 没有完整 SWE-Bench 复现。
- 没有完整 secret scanner；导出阶段只做基础字段过滤、本机路径脱敏和常见凭据正则脱敏。

## 快速运行

安装开发依赖后，可以直接运行：

```bash
python -m pip install -e '.[dev]'
```

然后校验任务、运行单个 replay agent，并检查运行产物：

```bash
repo-harness validate-task tests/fixtures/tasks/task_001.yaml

repo-harness run-task \
  tests/fixtures/tasks/task_001.yaml \
  --config tests/fixtures/run_configs/replay_success.yaml \
  --output-dir runs/demo \
  --run-id demo-success

repo-harness inspect-run runs/demo/demo-success
```

批量运行和导出：

```bash
repo-harness run-batch \
  --config tests/fixtures/run_configs/batch_replay.yaml \
  --output-dir runs/demo-batch

repo-harness export runs/demo-batch --format sft_jsonl
repo-harness export runs/demo-batch --format rl_jsonl
repo-harness export runs/demo-batch --format preference_jsonl
```

## 运行产物

每个 run directory 至少包含这些可复盘文件中的一部分：

- `events.jsonl`：结构化轨迹事件。
- `transcript.jsonl`：模型可见和训练相关消息记录。
- `artifacts.json`：artifact manifest。
- `baseline.json`：baseline quality gate 结果。
- `resolved_verifier_plan.json`：只有 baseline 通过后才生成。
- `final.patch` / `final.diff`：Agent Loop 停止后冻结的最终补丁。
- `verifier.json`：formal final verifier 结果。
- `reward.json`：来自 formal final verifier 的 reward metadata。
- `metrics.json`：运行结果、停止原因、权限拒绝、工具调用等指标。
- `summary.md`：面向人的运行摘要。

## 推荐阅读

- `docs/14-v1-implementation-plan.md`：第一版阶段计划和验收标准。
- `docs/11-object-model-config-and-data-flow.md`：对象模型、配置和数据流。
- `docs/v1-walkthrough.md`：第一版端到端使用说明。
- `docs/v1-final-acceptance.md`：第一版最终验收记录。
- `docs/developer-checklist.md`：后续开发检查清单。

## 边界提醒

RepoHarness 的第一版适合用于协议验证、微型仓库任务评测、轨迹审计和训练数据导出实验。进入真实仓库、真实模型供应商或大规模训练前，需要补齐更强的隔离、secret scanning、并发控制、成本控制和真实模型错误恢复策略。
