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

环境准备阶段不属于正式 agent trajectory。它产生的是任务可执行性证据和依赖状态，不应该把 setup 日志、setup 期间的文件写入或 baseline 测试输出混入 agent 的 action-observation 训练轨迹。

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
  "dependency_state": {
    "cache_key": "repo_task_001_py312_lockhash",
    "artifact_path": "artifacts/dependency_state/repo_task_001",
    "excluded_diff_paths": [".venv/", "node_modules/", ".pytest_cache/"]
  },
  "workspace_snapshot": "snapshots/repo_task_001_baseline",
  "agent_start_snapshot": "snapshots/repo_task_001_agent_start",
  "agent_diff_base": "agent_start_snapshot"
}
```

`status` 可以是：

- `valid`：测试命令可执行，baseline 状态和任务目标一致，可以进入正式 agent run。
- `invalid`：依赖安装失败、测试命令不可运行、任务字段缺失或仓库无法准备，不产生训练轨迹。
- `flaky`：同一 baseline 多次运行结果不一致，不产生默认训练轨迹，但可以进入诊断集合。

baseline 中发现的 fail-to-pass 和 pass-to-pass 信息必须进入 `VerifierConfig`。

## 正式运行 Workspace 边界

正式 agent run 的起点不能含糊。未来实现应区分三个状态：

1. source checkout：从任务 `base_commit` 或 fixture source 得到的干净源码树。
2. setup workspace：执行 dependency setup 和 baseline verifier 的准备工作区。
3. agent run workspace：模型真正开始调用工具的正式工作区。

推荐策略是：先在 setup workspace 中完成依赖安装和 baseline 检查，再把可复用依赖状态保存成 `dependency_state`，最后从 source checkout 创建 agent run workspace，并在 agent 开始前恢复依赖状态。agent trajectory 从 agent run workspace 创建完成之后才开始记录。

`dependency_state` 可以包含虚拟环境、包管理器缓存、容器层、构建缓存或测试缓存，但这些路径必须记录在 `excluded_diff_paths` 中，默认不进入 `final.diff`、`final.patch` 或训练样本。常见排除路径包括 `.venv/`、`node_modules/`、`.pytest_cache/`、`.mypy_cache/`、`dist/`、`build/` 和语言包管理器缓存目录。

如果 setup 修改了被 Git 跟踪的源码文件，默认应把任务标记为 `invalid`，除非任务 schema 显式声明这些 setup mutation 是合法的，并把它们保存为单独的 `setup.patch`。即使存在 `setup.patch`，最终 agent diff 也必须以 `agent_start_snapshot` 为基线，而不是以原始 source checkout 为基线，避免把 setup 副作用记成模型贡献。

正式运行的 diff 规则：

- `final.diff` 和 `final.patch` 只描述 agent 从 `agent_start_snapshot` 到最终 workspace 的改动。
- dependency setup 产物、baseline 测试缓存和未声明的构建产物默认排除。
- 如果 dependency setup 失败、baseline flaky 或 setup mutation 未声明，不进入正式 agent run，也不产生训练轨迹。
- `summary.md` 应同时记录 source checkout、setup workspace、dependency_state、agent_start_snapshot 和 final workspace 的路径或 artifact id。

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
