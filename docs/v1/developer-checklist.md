# RepoHarness V1 Developer Checklist

这份清单用于后续开发时快速检查是否仍然遵守第一版对象边界。它不替代设计文档，优先级仍然以 `docs/v1/implementation-plan.md` 和 `docs/11-object-model-config-and-data-flow.md` 为准。

## 核心边界

- Task Adapter 只读取、校验和规范化任务；不创建 workspace，不运行测试，不生成 `BaselineResult`。
- `BaselineResult` 由 Eval Runner 协调 Workspace Adapter 和 Verifier 生成。
- `ResolvedVerifierPlan` 只在 baseline 质量门控通过后生成。
- Agent Loop 只拥有 `agent_stop_reason` 和 loop state。
- `final_verifier_status`、`run_outcome` 和 `final_verifier_mode` 由 Eval Runner 在 patch 冻结和 formal final verifier 完成后派生。
- final patch 必须先冻结，再在独立 verification workspace 中 strict patch replay。
- feedback verifier 只是模型中间反馈，不能替代 formal final verifier。
- baseline verifier 和 final verifier 默认不进入模型上下文。

## 工具和权限

- 未知工具不进入 Permission System；工具查找阶段必须生成 invalid tool event 和配对 `ToolResult`。
- 已知工具只有通过 schema 校验、输入规范化和语义校验后，才进入 Permission System。
- 所有文件读写和命令执行必须通过 Workspace Adapter 或 Workspace Facade。
- 所有大输出必须写 ArtifactRef，模型上下文只放 preview 和 artifact 引用。
- 权限拒绝、schema 校验失败、工具超时、工具异常和中断都必须生成模型可见的配对 `ToolResult`。

## 数据可见性

- `gold_patch`、隐藏测试、baseline 原始日志、expected outcome、脚本注释和 reward-only 字段不能进入模型上下文。
- ReplayScript 的 expected outcome 和测试用注释属于 evaluator-only 或 test-only 内容，不能进入训练导出。
- 训练导出只能读取已有 run directory，不能重新运行 verifier，不能重写已经记录的事实。
- 强化学习 rollout JSONL 的 reward 必须来自 formal final verifier 和 `reward.json`。
- 导出 JSONL 中的 artifact ref 必须能回到原始 run directory 找到。

## 提交前验证

常用验证命令：

```bash
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest
git diff --check
```

端到端验收命令：

```bash
PATH=.venv/bin:$PATH repo-harness run-batch \
  --config tests/fixtures/run_configs/batch_replay.yaml \
  --output-dir runs/final-acceptance

PATH=.venv/bin:$PATH repo-harness export runs/final-acceptance --format sft_jsonl
PATH=.venv/bin:$PATH repo-harness export runs/final-acceptance --format rl_jsonl
PATH=.venv/bin:$PATH repo-harness inspect-run runs/final-acceptance/stage11_batch_001_task_001
```

## 文档表述

- README、walkthrough、summary 和示例文档不能声称生产级安全沙箱。
- README、walkthrough、summary 和示例文档不能声称已经完成真实模型训练。
- 如果新增能力还只是接口占位，必须明确写成后续扩展，而不是已实现能力。
- 如果设计文档之间出现冲突，记录冲突，优先遵循 `docs/v1/implementation-plan.md` 和 `docs/11-object-model-config-and-data-flow.md`。
