# Task, Dataset, And Environment Adapters

## 设计目标

Task Adapter 把不同来源的软件工程任务统一成 RepoHarness 可执行任务。它不负责模型调用，不负责工具执行，也不负责 reward 计算。

## 第一版任务格式

第一版未来实现计划支持 YAML 或 JSON。推荐 YAML 示例：

```yaml
id: repo_task_001
task_version: repo_task_001_v0
dataset_name: repo_harness_micro
source_kind: micro_repo_fixture
dataset_split: dev
created_at: "2026-04-30"
repo: ./fixtures/repos/buggy_calculator
base_commit: main
issue: "Fix division by zero handling in calculator.divide"
setup_command: "python -m pip install -e ."
test_command: "pytest -q"
timeouts:
  setup_timeout_sec: 300
  test_timeout_sec: 120
  agent_timeout_sec: 900
  final_verifier_timeout_sec: 180
environment:
  execution_image: python:3.12-slim
  python_version: "3.12"
  node_version: null
  package_manager: pip
  lockfile_hashes:
    - path: pyproject.toml
      sha256: "<sha256>"
  setup_cache_key_inputs:
    - pyproject.toml
  required_system_packages: []
  setup_network_policy: allow_public_package_indexes
expected_files:
  - calculator.py
visibility:
  issue: model_visible
  expected_files: model_visible
  fail_to_pass_tests: verifier_only
  pass_to_pass_tests: verifier_only
  gold_patch: hidden_reference
decontamination:
  status: manual_checked
  known_public_solution: false
  source_url: null
  overlap_check_notes: "hand-written fixture"
  notes: null
declared_setup_mutations: []
generated_files: []
```

最低字段：

- `id`
- `task_version`
- `dataset_name`
- `source_kind`
- `created_at`
- `repo`
- `issue`
- `test_command`
- `timeouts`
- `environment`
- `visibility`

可选字段：

- `expected_files`
- `setup_command`
- `fail_to_pass_tests`
- `pass_to_pass_tests`
- `base_commit`
- `source_archive_sha256`
- `gold_patch`
- `tags`
- `dataset_split`
- `decontamination`
- `declared_setup_mutations`
- `generated_files`

`timeout_sec` 可以作为 micro fixture 的兼容简写，但 TaskAdapter 应在规范化阶段展开为 `setup_timeout_sec`、`test_timeout_sec`、`agent_timeout_sec` 和 `final_verifier_timeout_sec`。不要让一个字段同时承担 setup、测试、agent run 和 final verifier 四个阶段的含义。

`environment` 描述任务环境身份，而不是当前机器的偶然状态。第一版至少应支持：

- `execution_image`：Docker execution mode 使用的镜像或本地 fixture 的环境标签。
- `python_version`、`node_version` 或其他语言运行时版本。
- `package_manager`：例如 `pip`、`uv`、`poetry`、`npm`、`pnpm`。
- `lockfile_hashes`：锁文件或依赖声明文件的路径和 hash。
- `setup_cache_key_inputs`：影响 dependency_state cache key 的文件列表。
- `required_system_packages`：需要的系统包。
- `setup_network_policy`：setup 阶段是否允许访问公开包索引或指定域名。

`declared_setup_mutations` 和 `generated_files` 应是结构化列表，而不是自由文本。每一项至少包含：

- `path_pattern`
- `allowed_stage`：例如 `setup`、`agent_run`、`final_verifier`。
- `include_in_final_patch`
- `reason`
- `artifact_policy`

当 `allowed_stage = "final_verifier"` 时，`include_in_final_patch` 必须为 `false`。final verifier 发生在 `final.patch` / `final.diff` 冻结之后，它产生的文件只能作为 verifier artifact、日志或诊断材料保存，不能回流进 agent 的最终 patch。需要长期保存的 final verifier 产物应通过 `artifact_policy` 写入 `artifacts.json`，而不是通过 `generated_files` 进入训练 patch。

字段可见性必须显式标注。建议使用：

- `model_visible`：可以进入模型上下文，例如 issue statement、允许公开的 expected files。
- `verifier_only`：只能给 Verifier 使用，例如隐藏测试、fail-to-pass 和 pass-to-pass 测试集合。
- `reward_only`：只用于 reward metadata 或统计，不进入模型上下文。
- `hidden_reference`：只用于离线分析或构造 preference pair，例如 `gold_patch`。

`gold_patch` 必须是 `hidden_reference`。隐藏测试、reward metadata 和 baseline 质量门控细节不得进入 ContextBuilder。`expected_files` 是否给模型看也应由 `visibility` 显式决定，不能靠字段名默认泄漏。

`task_version`、`dataset_name`、`source_kind`、`dataset_split`、`created_at` 和 `decontamination` 用于后续实验复现和数据污染分析。第一版 micro-repo task 也应填写这些字段，避免以后把训练集、验证集、测试集或公开来源混在一起。`decontamination` 不进入模型上下文，默认只进入 task metadata、metrics 和 export metadata。

## TaskAdapter 职责

TaskAdapter 必须提供：

- 读取任务定义。
- 验证任务 schema。
- 解析并规范化 `repo`、`base_commit`、`source_archive_sha256` 或本地 fixture 引用。
- 提供 issue statement。
- 提供 setup command。
- 提供 test command。
- 提供 verifier 配置。
- 提供 task metadata。

TaskAdapter 不应该 checkout 仓库、复制仓库、安装依赖、运行测试、知道模型类型、工具执行细节或 reward 公式。

`BaselineResult` 不由 TaskAdapter 单独生成。TaskAdapter 只负责输出 `RunnableTask` 和 `VerifierConfig`；Eval Runner 负责协调 Workspace Adapter 和 Verifier，在 setup workspace 中执行 dependency setup、baseline verifier 和质量门控，最终生成 `BaselineResult`。

`VerifierConfig` 是 Task Adapter 从任务定义中得到的静态配置；baseline 运行后得到的实际 fail-to-pass、pass-to-pass、flaky tests 和 parser confidence 不应反向写回 `VerifierConfig`，而应由 Eval Runner 汇总成 `ResolvedVerifierPlan`。

所有权应保持：

- Task Adapter：读取、校验、规范化任务定义，解析仓库来源、基准提交、环境身份、字段可见性、issue statement、setup command、test command 和 verifier 配置。
- Workspace Adapter：创建 source checkout、setup workspace、agent run workspace，执行命令并保存 workspace artifact。
- Verifier：运行 baseline、feedback 和 final verifier，解析测试结果。
- Eval Runner：根据 `BaselineResult.status` 决定是否进入正式 agent run。
- Trajectory Store：保存 baseline artifact 和 summary，但 baseline 日志不进入正式 agent action-observation 轨迹。

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

1. Eval Runner 把 `RunnableTask` 交给 Workspace Adapter。
2. Workspace Adapter 根据规范化 repo source 创建 source checkout 和 setup workspace。
3. Workspace Adapter 执行 dependency setup，并捕获 dependency_state、setup artifact 和 setup mutation。
4. Eval Runner 调用 Verifier baseline path，Verifier 通过 Workspace Adapter 运行 baseline tests 并解析结果。
5. 确认测试命令可执行。
6. 记录初始失败测试、通过测试、parser confidence 和 baseline artifact 引用。
7. 生成 task summary。

如果 setup 或 baseline tests 不稳定，任务应标记为 invalid 或 flaky，而不是进入正式 agent run。

环境准备阶段不属于正式 agent trajectory。它产生的是任务可执行性证据和依赖状态，不应该把 setup 日志、setup 期间的文件写入或 baseline 测试输出混入 agent 的 action-observation 训练轨迹。

## DependencyState 策略

`dependency_state` 必须是可实现的恢复策略，而不是抽象占位符。第一版建议支持这些策略中的一个或多个：

```text
DependencyState:
  strategy: none | rerun_setup | copy_declared_paths | docker_image_layer
  cache_key
  artifact_ref
  restored_paths
  excluded_diff_paths
  created_after_setup_command
  excludes_baseline_side_effects
```

策略含义：

- `none`：任务不需要依赖恢复，agent run workspace 直接从 source checkout 开始。
- `rerun_setup`：正式 agent run workspace 和 verification workspace 中重新运行 setup command。实现简单，但会消耗时间，并且必须保证 setup mutation 规则可控。
- `copy_declared_paths`：setup command 结束后复制声明过的依赖路径，例如 `.venv/` 或 `node_modules/`，并在正式工作区恢复。必须通过 `declared_setup_mutations`、`excluded_diff_paths` 和 artifact manifest 记录来源。
- `docker_image_layer`：把依赖状态固化为容器层或镜像缓存。它适合后续扩展，第一版不强制实现。

无论使用哪种策略，`dependency_state` 都必须在 setup command 结束后、baseline verifier 之前捕获。baseline verifier 产生的测试缓存、日志、覆盖率文件和快照更新只能作为 baseline artifact 保存，不能进入 `dependency_state`。

## BaselineResult

环境准备阶段必须生成 `BaselineResult`，作为正式运行前的质量门控：

```json
{
  "task_id": "repo_task_001",
  "status": "valid",
  "setup_exit_code": 0,
  "baseline_exit_code": 1,
  "baseline_verifier_result_ref": {
    "artifact_id": "artifact_baseline_verifier_001",
    "relative_path": "verifier/baseline_001.json"
  },
  "setup_artifact_refs": [
    {"artifact_id": "artifact_setup_stdout_001", "relative_path": "artifacts/setup/stdout.txt"}
  ],
  "baseline_artifact_refs": [
    {"artifact_id": "artifact_baseline_stdout_001", "relative_path": "artifacts/baseline/stdout.txt"}
  ],
  "parser_confidence": 0.95,
  "baseline_rerun_count": 2,
  "flaky_policy_version": "repo_harness_flaky_policy_v0",
  "initial_fail_to_pass_tests": ["tests/test_calculator.py::test_divide_zero"],
  "initial_pass_to_pass_tests": ["tests/test_calculator.py::test_add"],
  "flaky_tests": [],
  "dependency_error": null,
  "dependency_state": {
    "strategy": "copy_declared_paths",
    "cache_key": "repo_task_001_py312_lockhash",
    "artifact_ref": {
      "artifact_id": "artifact_dependency_state_001",
      "relative_path": "artifacts/dependency_state/repo_task_001"
    },
    "restored_paths": [".venv/"],
    "excluded_diff_paths": [".venv/", "node_modules/", ".pytest_cache/"],
    "created_after_setup_command": true,
    "excludes_baseline_side_effects": true
  },
  "setup_workspace_snapshot": "snapshots/repo_task_001_baseline",
  "agent_run_start_policy": {
    "create_from": "source_checkout",
    "restore_dependency_state": true,
    "diff_base_policy": "create_agent_start_snapshot_after_dependency_restore"
  }
}
```

`status` 可以是：

- `valid`：测试命令可执行，baseline 状态和任务目标一致，可以进入正式 agent run。
- `invalid`：依赖安装失败、测试命令不可运行、任务字段缺失或仓库无法准备，不产生训练轨迹。
- `flaky`：同一 baseline 多次运行结果不一致，不产生默认训练轨迹，但可以进入诊断集合。

baseline 中确认的 fail-to-pass、pass-to-pass、flaky tests 和 parser confidence 必须进入运行时 `ResolvedVerifierPlan`，不能反向污染 Task Adapter 输出的静态 `VerifierConfig`。

`BaselineResult` 不能保存实际的 `agent_start_snapshot`。baseline 阶段只证明任务有效、保存 setup workspace 状态和 `dependency_state`。正式 `agent_start_snapshot` 必须在创建 agent run workspace、恢复 `dependency_state`、确认正式运行起点后生成，并记录到 `RunWorkspace` 或 agent run start artifact 中。

`BaselineResult` 必须引用完整 baseline `VerifierResult` 和相关 artifact，而不是只保存 exit code 和测试列表摘要。完整 `VerifierResult` 应包含 `parser_id`、`parser_version`、`parser_confidence`、`test_cases`、stdout/stderr artifact 引用和 timeout 信息。这样后续才能审计 flaky task、baseline parser 失败、依赖安装失败和任务质量门控原因。

## VerifierConfig 与 ResolvedVerifierPlan

第一版需要明确区分静态验证器配置和运行时验证计划：

```text
VerifierConfig:
  来源: Task Adapter
  内容: task definition 中声明的 test_command、test_timeout_sec、final_verifier_timeout_sec、parser、visibility policy、可选 fail_to_pass_tests 和 pass_to_pass_tests
  性质: 任务定义的一部分，不应被 baseline 结果原地修改

ResolvedVerifierPlan:
  来源: Eval Runner + Workspace Adapter + Verifier baseline path
  内容: VerifierConfig + BaselineResult 中确认的 initial_fail_to_pass_tests、initial_pass_to_pass_tests、flaky_tests、parser_confidence、acceptance_policy_version
  性质: feedback verifier、formal final verifier、accepted 判定和 reward metadata 使用的运行时计划
```

这样可以保证 Task Adapter 只负责读取和规范化任务，Eval Runner 才负责把 baseline 证据变成正式评测计划。训练导出和 reward evidence chain 应记录使用的 `resolved_verifier_plan_id` 或等价版本字段。

## 正式运行 Workspace 边界

正式 agent run 的起点不能含糊。未来实现应区分三个状态：

1. source checkout：从任务 `base_commit` 或 fixture source 得到的干净源码树。
2. setup workspace：执行 dependency setup、捕获 `dependency_state`，并承载随后 baseline verifier 的准备工作区。
3. agent run workspace：模型真正开始调用工具的正式工作区。

推荐策略是：先在 setup workspace 中完成依赖安装，立刻把可复用依赖状态保存成 `dependency_state`，然后运行 baseline verifier。baseline verifier 产生的测试缓存、日志、覆盖率文件和其他副作用只作为 baseline artifact 或 excluded diff 处理，不应被恢复到正式 agent run workspace。最后从 source checkout 创建 agent run workspace，并在 agent 开始前恢复 `dependency_state`。agent trajectory 从 agent run workspace 创建完成之后才开始记录。

`dependency_state` 可以包含虚拟环境、包管理器缓存、容器层和 setup command 产生的构建缓存，但不应包含 baseline verifier 产生的测试缓存或日志。所有依赖状态路径必须记录在 `excluded_diff_paths` 中，默认不进入 `final.diff`、`final.patch` 或训练样本。常见排除路径包括 `.venv/`、`node_modules/`、`.pytest_cache/`、`.mypy_cache/`、`dist/`、`build/` 和语言包管理器缓存目录。

如果 setup 修改了被 Git 跟踪的源码文件，默认应把任务标记为 `invalid`，除非任务 schema 显式声明这些 setup mutation 是合法的，并把它们保存为单独的 `setup.patch`。即使存在 `setup.patch`，最终 agent diff 也必须以 `agent_start_snapshot` 为基线，而不是以原始 source checkout 为基线，避免把 setup 副作用记成模型贡献。

如果任务需要生成文件或快照文件，必须通过 `generated_files` 或 `declared_setup_mutations` 显式声明。未声明的源码改动、生成文件改动或依赖安装副作用默认不进入正式 agent run。

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
