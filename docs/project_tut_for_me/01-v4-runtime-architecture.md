# V4 当前运行架构

## 一句话版本

当前 V4 可以理解为：把经过冻结的真实软件工程任务放进 Docker-based executable repository environment 中，让真实 provider 驱动的 agent 通过受控工具修改代码，随后在干净验证工作区中重放 final patch，用 verifier、reward、trajectory export 和 acceptance evidence 判断这条轨迹是否可用于评测或训练。

主链路仍然由 `src/repo_harness/evaluation/runner.py` 中的 `run_task` 编排，但是现在你应该把它理解为真实运行控制器，而不是早期 demo 编排器。

## run-task 的入口

命令行入口来自 `pyproject.toml`：

```text
repo-harness = repo_harness.cli.main:main
```

CLI 解析参数后，`run-task` 会调用：

```text
src/repo_harness/evaluation/runner.py::run_task
```

`run_task` 接收三个关键输入：

- `task_path`：任务定义 YAML。
- `config_path`：运行配置 YAML。
- `output_dir` / `run_id`：本次运行产物放在哪里。

运行配置中最关键的字段是：

```yaml
model:
  provider: deepseek
runtime:
  execution_mode: docker
  permission_mode: auto
workspace:
  output_dir: runs/...
evaluation:
  final_verifier_mode: strict_patch_replay
```

`run_task` 明确限制 provider：

- `deepseek` 是当前真实 provider 主路径。
- `openai` 只允许作为 DeepSeek fallback smoke run，不能作为 primary provider。
- `replay`、`fake`、`mock` 仍存在于代码里，但不应该作为你理解当前成熟链路的中心。

`final_verifier_mode` 当前正式评测只接受 `strict_patch_replay`。这意味着最终判断不是在 agent 改过的工作区里直接测，而是捕获 patch 后，在干净验证工作区中重放。

## run_task 的主对象流

一次运行可以按下面的对象流理解：

```text
RunConfig
  -> LoadedTask(TaskDefinition + RunnableTask + VerifierConfig)
  -> WorkspaceAdapter(DockerWorkspaceAdapter)
  -> SourceCheckout
  -> setup workspace
  -> DependencyState
  -> BaselineResult
  -> RunConfigFacts + tool schema snapshot
  -> RunWorkspace(agent workspace)
  -> initial messages
  -> ModelClient
  -> AgentLoopState
  -> FinalPatchCapture
  -> VerifierResult(final)
  -> RewardMetadata
  -> MetricsRecord
  -> RunMetadata
```

这些对象分别解决不同问题：

- `RunConfig` 决定使用哪个 provider、哪个执行后端、哪些预算和权限策略。
- `TaskDefinition` 保留任务定义的完整 schema，包括 evaluator-only 字段。
- `RunnableTask` 是运行时使用的规范化任务对象。
- `WorkspaceAdapter` 把“文件读写、命令执行、patch 捕获”隐藏在统一接口后面。
- `DependencyState` 记录 setup 之后如何恢复依赖状态，当前 Docker 路径主要是 `none` 或 `rerun_setup`。
- `BaselineResult` 决定任务是否可以进入 agent run。
- `RunConfigFacts` 固化本次运行配置和环境指纹。
- `AgentLoopState` 记录 turn、tool call、预算、上下文压缩、反馈测试等状态。
- `VerifierResult` 是 verifier 的结构化输出，包含 `accepted`、测试统计、错误类型、parser confidence。
- `RewardMetadata` 把 final verifier 结果、patch stats 和事件计数转成训练或评测可用的 reward 信息。

## 一次运行的控制流程

下面是 `run_task` 的核心步骤：

```text
1. load_run_config
2. load_task
3. build_scaffold / resolve_allowed_tools / resolve_feedback_policy
4. create_workspace_adapter
5. create_source_checkout
6. create_setup_workspace
7. run setup command
8. capture_dependency_state
9. run baseline verifier 或读取 SWE-Bench-like frozen baseline
10. write tool schema snapshot
11. write run config facts 和 environment fingerprint
12. create_agent_workspace
13. build initial model messages
14. create_model_client
15. AgentLoop.run
16. capture_final_patch
17. final verifier strict patch replay
18. compute reward
19. build metrics
20. write run metadata
21. cleanup 或保留 workspace
```

关键点是：每个阶段不是只在内存中继续向下传递，还会写入 run directory 中的 artifact、event、metadata。这是 RepoHarness 作为 harness，而不是普通 agent demo 的核心差异。

## 运行目录结构

一次 run-task 产物通常长这样：

```text
runs/<run_group>/<run_id>/
  task.yaml
  baseline.json
  dependency_state.json
  resolved_verifier_plan.json
  run_config_facts.json
  run_metadata.json
  metrics.json
  artifacts.json
  events.jsonl
  transcript.jsonl
  artifacts/
  workspaces/
  container_execution_facts/
  docker_backend_facts.json
  docker_backend_status.json
  docker_stage_status.json
```

如果是 Docker backend，还会有：

- `docker_backend_facts.json`：Docker CLI、server、image、platform、network policy、mount policy 等事实。
- `container_execution_facts/*.json`：每条容器命令的 command、workdir、exit code、timeout、duration、cleanup status。
- `container_execution_facts/manifest.json`：容器命令索引。
- `container_execution_facts/docker_phase_coverage_matrix.json`：Docker 阶段覆盖矩阵。

## V4 不只是 run_task

`run_task` 是单任务执行主链路，但 V4 的完整基础设施还包括这些阶段：

- `v4_implementation_inputs.py`：冻结 V4 implementation inputs，把 PR / issue feasibility 和 public SWE-Bench-like feasibility 绑定成后续阶段输入。
- `v4_task_freeze.py`：生成 V4 task freeze evidence，包括 adapter-visible manifest 和 evaluator-only evidence。
- `v4_rollout.py`：单机 rollout queue、lease、retry、resource lock、checkpoint、resume。
- `v4_tool_lifecycle.py`：工具 contract、权限 policy、hook policy、MCP policy 的审计快照。
- `v4_agent_run.py`：检查 completed / interrupted / crashed run，prepared messages binding，final verifier boundary，trajectory store integrity。
- `v4_export_quality.py`：检查 export sample、failure dataset、packing、reward audit、preference pair trainability。
- `v4_cards.py`：生成 dataset card、run card、export card、provenance summary、contamination scan。
- `v4_acceptance.py`：把各阶段 evidence 绑定为 acceptance inputs、acceptance report 和 acceptance bundle。

所以你面试时可以这样区分：

```text
run_task 是单条任务轨迹的执行引擎。
V4 pipeline 是围绕这些轨迹建立的任务冻结、批量调度、工具生命周期审计、训练导出质量审计和最终验收系统。
```

## 当前 V4 状态

目前最准确的状态是：

- V4 implementation 阶段已经实现完成。
- 历史 V4 acceptance report 和 acceptance bundle 存在。
- 当前复核发现旧 acceptance inputs / report / bundle 已经不完全满足最新 inspect 逻辑。
- 特别是 V4 final acceptance 现在需要独立的 `real_repository_regression` 和 `swebench_like_regression` evidence，不能复用 task freeze 或 task validity evidence。

因此学习时可以信任当前源码链路的结构，但如果要对外声称“最终验收通过”，必须以重新生成后的 evidence 和 acceptance bundle 为准。
