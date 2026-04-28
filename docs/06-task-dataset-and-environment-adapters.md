# Task, Dataset, And Environment Adapters

## 设计目标

Task Adapter 把不同来源的软件工程任务统一成 RepoHarness 可执行任务。它不负责模型调用，不负责工具执行，也不负责 reward 计算。

## 第一版任务格式

第一版未来实现计划支持 YAML 或 JSON。推荐 YAML 示例：

```yaml
id: repo_task_001
repo: ./fixtures/repos/buggy_calculator
issue: "Fix division by zero handling in calculator.divide"
test_command: "pytest -q"
timeout_sec: 120
expected_files:
  - calculator.py
```

最低字段：

- `id`
- `repo`
- `issue`
- `test_command`
- `timeout_sec`

可选字段：

- `expected_files`
- `setup_command`
- `fail_to_pass_tests`
- `pass_to_pass_tests`
- `base_commit`
- `gold_patch`
- `tags`

## TaskAdapter 职责

TaskAdapter 必须提供：

- 读取任务定义。
- 验证任务 schema。
- 准备初始仓库。
- 提供 issue statement。
- 提供 setup command。
- 提供 test command。
- 提供 verifier 配置。
- 提供 task metadata。

TaskAdapter 不应该知道模型类型、工具执行细节或 reward 公式。

## 任务来源

第一版任务来源：

- 自建 micro-repo tasks。
- issue-style fixture tasks。

后续预留：

- SWE-Bench Lite subset。
- GitHub Issue / Pull Request adapter。
- 从真实 Pull Request 构造 fail-to-pass 和 pass-to-pass tests。

这些后续能力只在接口层预留，不作为第一阶段实现目标，也不应在 README 中声称已经完成。

## 环境准备流程

环境准备应包含：

1. 复制或 checkout 仓库。
2. 执行 dependency setup。
3. 运行 baseline tests。
4. 确认测试命令可执行。
5. 记录初始失败测试和通过测试。
6. 生成 task summary。

如果 setup 或 baseline tests 不稳定，任务应标记为 invalid 或 flaky，而不是进入正式 agent run。

## BaselineResult

环境准备阶段必须生成 `BaselineResult`，作为正式运行前的质量门控：

```json
{
  "task_id": "repo_task_001",
  "status": "valid",
  "setup_exit_code": 0,
  "baseline_exit_code": 1,
  "initial_fail_to_pass_tests": ["tests/test_calculator.py::test_divide_zero"],
  "initial_pass_to_pass_tests": ["tests/test_calculator.py::test_add"],
  "flaky_tests": [],
  "dependency_error": null,
  "workspace_snapshot": "snapshots/repo_task_001_baseline"
}
```

`status` 可以是：

- `valid`：测试命令可执行，baseline 状态和任务目标一致，可以进入正式 agent run。
- `invalid`：依赖安装失败、测试命令不可运行、任务字段缺失或仓库无法准备，不产生训练轨迹。
- `flaky`：同一 baseline 多次运行结果不一致，不产生默认训练轨迹，但可以进入诊断集合。

baseline 中发现的 fail-to-pass 和 pass-to-pass 信息必须进入 `VerifierConfig`。正式 agent run 应从干净 workspace 或明确记录的 baseline snapshot 开始，避免 dependency setup 的副作用污染 agent trajectory。

## 任务质量控制

需要过滤：

- 无法安装依赖的任务。
- 测试命令不可运行的任务。
- 任务描述过于模糊的任务。
- 修复范围过大的任务。
- 环境依赖外部网络且无法复现的任务。
- baseline 状态和任务目标不一致的任务。

## Claude Code 参考

Claude Code 不提供 SWE-style dataset adapter，但可参考它的 cwd、project root、worktree、context construction 设计：

- `reference/claude-code-docs/claude-code-ai-core-codex/01-startup-to-query-entry.md`
- `reference/claude-code-typescript-src/setup.ts`
- `reference/claude-code-typescript-src/context.ts`
