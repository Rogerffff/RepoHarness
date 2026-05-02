# RepoHarness V3 Implementation Plan

## 0. 文档定位

本文把 `docs/v3/scope-and-roadmap.md` 中的第三版范围，转化为可以逐阶段实现、逐阶段验收、逐阶段审查的工程实施计划。

本文不是第三版已经完成的声明，也不是 SWE-Bench Lite 榜单复现计划。第三版的目标是让 RepoHarness 自己具备可审计的 repository-level evaluation harness 能力：由 RepoHarness 自己完成 task adapter、Docker workspace backend、仓库 materialization、test patch / verifier patch 应用、fail-to-pass / pass-to-pass 测试、container execution facts、final verifier evidence、训练导出审计和最终 `v3_acceptance_report.json`。

官方 SWE-Bench harness 只作为进入 V3 前的可实现性证明工具。V3 最终验收不能只复用官方 SWE-Bench 报告，也不能把官方 harness 当作 RepoHarness 的最终产品能力。

## 1. 第零阶段输入：SWE 任务可实现性实验

第三版实施前已经完成小规模本机可实现性实验，结果记录在：

```text
docs/v3/review/swe-task-feasibility-results.md
runs/v3-swe-feasibility-20260502T083722Z/
```

`runs/v3-swe-feasibility-20260502T083722Z/` 是第零阶段来源证明，不是 V3 后续实现阶段的默认输入路径。阶段 0 必须先把最小固定输入迁入受版本控制的工程输入目录，建议路径为：

```text
tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/
docs/v3/evidence/swebench-lite-fixed/evaluator_only/
```

后续 task adapter、inspect 命令和最终验收默认读取 `tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/`。这个目录只能包含 adapter 可见或 adapter 可安全读取的任务输入，例如 sanitized task JSONL、task input manifest、source hashes 和 verifier evidence refs。它不能包含 `gold_patch_predictions.jsonl`、数据集 `patch` 字段、raw `test_patch`、raw `FAIL_TO_PASS` / `PASS_TO_PASS`、official harness report、resolved status 或任何 gold patch 内容。

`docs/v3/evidence/swebench-lite-fixed/evaluator_only/` 只能保存 evaluator-only 或 audit-only 证据引用，例如 gold patch feasibility report 的 sha256、official harness report ref、gold patch prediction 文件 ref 和 raw fixed dataset ref。RepoHarness task adapter 默认不得读取这个目录；只有 verifier / evaluator / audit / acceptance inspect 可以读取，并且所有读取都必须进入 evidence refs。

如果执行者在干净检出环境中缺少这些固定输入，必须先运行明确的预取和校验命令，并显式传入 `--feasibility-root runs/v3-swe-feasibility-20260502T083722Z` 或等价来源目录；不能让任何核心阶段隐式读取未跟踪 `runs/` 目录。

关键输入事实：

- SWE-Bench commit：`f7bbbb2ccdf479001d6467c9e34af59e44a840f9`
- 数据集：`princeton-nlp/SWE-bench_Lite`
- 数据集 revision：`6ec7bb89b9342f664a54a6e0a6ea6501d3437cc2`
- 数据集 split：`test`
- 实验目录：`runs/v3-swe-feasibility-20260502T083722Z`
- 第零阶段来源数据快照：`runs/v3-swe-feasibility-20260502T083722Z/dataset/level2_dataset.jsonl`
- V3 默认 adapter 输入目录：`tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/`
- V3 evaluator-only evidence 目录：`docs/v3/evidence/swebench-lite-fixed/evaluator_only/`
- 实验最终状态：`green_ready_for_v3_implementation_plan`
- 已接受任务：
  - `pytest-dev__pytest-7220`
  - `pytest-dev__pytest-8365`
  - `sympy__sympy-24909`

这些任务可以进入 V3 最小完成定义，保守表述为：

```text
本机固定 revision SWE-Bench-like 小子集已通过 gold patch 可实现性实验。
```

禁止表述为：

- 完整 SWE-Bench Lite 复现。
- 公开 SWE-Bench 榜单可比结果。
- 官方 SWE-Bench 评测环境复现。
- 已经训练或评测出了 coding agent。

第零阶段的任务不是继续运行官方 harness，而是把这些实验事实冻结为 V3 实施输入。若后续需要重新生成数据快照，必须固定同一个 dataset revision，重新记录 manifest sha256，并证明任务字段与本次实验一致。冻结完成后，V3 默认输入不能再指向 `runs/` 目录，也不能把 gold patch prediction 文件放进 adapter 默认输入根目录。

## 2. V3 实施原则

第三版必须保留第二版已经验证过的不变量，并新增以下硬边界。

### 2.1 统一污染字段 denylist 和可见性边界

V3 必须定义一套统一的 `V3ContaminationDenylist`，同一套规则扫描 prompt、prepared messages、tool observation、transcript 中的模型可见记录、checkpoint、context compaction report、SFT export、RL rollout export、preference export、audit report 输入和 acceptance bundle 输入。

以下字段和产物只能作为 verifier / evaluator / audit 侧事实，不能进入模型可见 prompt、模型可见 tool observation、训练 target、SFT assistant 内容、RL action / observation payload 或 preference target：

- 数据集 `patch` 字段，也就是 gold patch。
- `test_patch` 或任何 verifier patch。
- `FAIL_TO_PASS`。
- `PASS_TO_PASS`。
- 官方 SWE-Bench report。
- official harness 的 resolved / unresolved status。
- final verifier hidden stdout / stderr 中会泄漏隐藏测试名称或 gold patch 线索的内容。
- provider raw response。
- reasoning summary 或任何未脱敏推理内容。
- Authorization marker、API key、token、credential path 或 provider credential status detail。
- 本机绝对路径。
- 完整 decontamination metadata；训练 payload 只能包含通过审计允许的摘要或 hash。
- final verifier result、reward metadata、run outcome、failure diagnostics 中会反馈 hidden verifier 结果的字段。

模型可见内容只能来自允许的 issue statement、仓库文件、工具结果和公开反馈策略。默认 SWE-Bench-like task 使用 final-only verifier policy。若某个任务允许 public feedback，必须显式标记为 `public_only` 或 `structured_public_feedback`，并且 hidden fail-to-pass / pass-to-pass suite 仍不能进入模型上下文。

### 2.2 Docker 环境硬前置

V3 实施和验收前必须满足：

- Docker Desktop Linux 虚拟机内存至少 `16 GiB`，建议 `24 GiB`。
- `max_parallel_runs = 1` 和现有 `evaluation.concurrency = 1` 起步。若新增 `swebench_like.max_workers` 字段，它必须默认等于 `evaluation.concurrency`，并且在冲突时以更保守的较小值为准；inspect 必须记录两个字段的来源和最终 effective workers。
- 每个 Docker run 记录 `docker_context`、Docker server platform、server architecture、requested container platform、container `uname -m`、image id、image platform、build mode、cross architecture emulation facts、network policy、mount policy、timeout、cleanup policy 和 cleanup status。
- 禁止无边界清理 Docker 资源。不能执行不带边界的 `docker system prune -a`。只能清理本次 run id、image tag 或实验 namespace 明确创建的资源。

### 2.3 官方 harness 边界

官方 SWE-Bench harness 只用于第零阶段可实现性证明。V3 不能把官方报告当作最终验收。第三版必须由 RepoHarness 自己生成：

- `v3_feasibility_input_manifest.json`
- `source_checkout_facts.json`
- `task_adapter_facts.json`
- `real_repository_task_manifest.json`
- `swebench_like_task_facts.json`
- `swebench_like_environment_specs.json`
- `swebench_like_verifier_plan.json`
- `container_execution_facts/manifest.json`
- `docker_phase_coverage_matrix.json`
- `final_verifier_result.json`
- `failure_diagnostics_core_report.json`
- `failure_distribution_report.json`
- `v3_acceptance_report.json`

官方 harness 的结果可以作为设计参考和第零阶段输入，但不能成为 `final_verifier_result` 的替代品。

### 2.4 验收路径约定

每次阶段验收和最终验收都必须写入新的唯一 run directory 或 acceptance directory，不能复用已有输出目录。若旧目录存在，只能通过项目已有归档流程移动或标记，不能覆盖旧 evidence。

文档中的 `RUN_DIR` 表示某次实际 run 的唯一目录。已有 `inspect-workspace-backend` 命令应保留 `--status-file` 兼容入口；如果 V3 新增 `RUN_DIR` 位置参数，也必须同时保留 `--status-file` 的旧接口测试。

每个 inspect 命令都必须显式接收输入路径，不能读取当前目录、默认 latest run 或环境变量来猜测输入。command log 和 acceptance bundle 必须记录每个输入路径和 sha256。

V3 必须定义 `CommandLogEntry` 或等价 schema。阶段运行期间至少生成 `RUN_DIR/command_log.jsonl` 或 `EXPERIMENT_DIR/command_log.jsonl`；最终验收期间必须生成 `ACCEPTANCE_DIR/acceptance_command_log.jsonl`。每条记录至少包含 command name、argv、cwd、输入路径、输入 sha256、输出路径、输出 sha256、exit code、tool / CLI version、started_at、finished_at 和 structured skip / failure reason。`inspect-v3-acceptance` 和 `inspect-acceptance-bundle` 必须校验 command log 完整性、sha256、输入 manifest 一致性和篡改负例。

### 2.5 Agent Loop、verifier 和 reward 单向边界

Agent Loop 结束并冻结 final patch 之后，才允许启动 final verifier。final verifier result、hidden verifier stdout / stderr、reward metadata、run outcome、failure diagnostics 和 acceptance summary 只能写入 evaluator / audit / export filtering facts，不能被同一次 Agent Loop 读取。

Resume 或 continuation run 不能把上一轮 final verifier hidden result、reward、run outcome 或 failure diagnostics 反馈给同一 agent 继续尝试。若要继续任务，必须创建新的 continuation run，并在 metadata 中标记它只继承允许的公开上下文、源码状态和非泄漏摘要。

### 2.6 轨迹存储基础不变量

V3 的核心目标是产生可执行、可审计、可导出的训练轨迹，因此 trajectory store 本身必须成为硬验收，而不是附带产物。除纯计划性 `skipped` run 外，每个实际启动过的 run 至少必须生成：

- `transcript.jsonl`
- `events.jsonl`
- `artifacts.json`
- `run_config_facts.json`

`completed` 或已进入终态并被 acceptance 接受的 run 必须额外生成 `run_metadata.json`，以及 final patch artifact 或结构化 no-patch fact。`interrupted`、`crashed` 或进程外部终止导致没有进入最终 metadata 写入点的 run，不要求生成最终 `run_metadata.json`，但必须生成结构化 interrupted / crash facts，并保留可读的 `run_config_facts.json`、transcript、events 和 artifacts。

`ArtifactRef` 必须可解析，并且每个 artifact 都必须校验 `sha256`、`size_bytes`、relative path、kind、created_at 或等价时间字段。`RunRecorder` 在 provider error、Docker error、verifier error、用户中断或进程崩溃后产生的部分轨迹仍必须能被 inspect 读取；inspect 可以标记 run incomplete，但不能因为缺少最终 metadata 就失去已记录 transcript、events 和 artifacts 的可审计性。

模型可见 transcript 与 evaluator-only artifact/event 必须区分。denylists 不能简单禁止 evaluator-only transcript/event 保存 hidden facts；它们应禁止这些 hidden facts 出现在模型可见 transcript、prepared messages 和训练 payload，同时允许 evaluator-only event/artifact 为复盘保留受标记证据。

### 2.7 工具契约和策略快照不变量

V3 每个 run 必须冻结模型当时实际可见的工具协议和策略事实。至少包括：

- `ToolContractSnapshot`：工具名称、schema、description、tool result pairing 规则、large-output artifact policy、tool call id 规则和 tool protocol version。
- `PermissionPolicySnapshot`：命令、文件、网络、Docker、source materialization 和 verifier 相关 permission policy 引用与 sha256。
- `HookPolicySnapshot` 或 hook disabled facts：即使 V3 核心没有启用 hook，也必须明确记录 hooks disabled、无 hook-generated observation 进入模型上下文。
- `MCPPolicySnapshot` 或 MCP disabled/frozen facts：V3 不实现完整 MCP，但必须记录 MCP disabled 或 frozen external tool surface，避免后续误把外部动态工具混入同一 compare scope。
- scaffold、context policy、feedback policy、workspace backend policy 和 export policy snapshot refs。

这些快照必须进入 `run_config_facts.json`。对于 completed 或 terminal accepted run，它们还必须进入 `run_metadata.json`、preference compare scope 和 acceptance bundle；对于 interrupted / crashed run，它们必须保留在可读的 run config facts、events 或 structured interrupted / crash facts 中。缺少快照或快照 sha256 不匹配时，正式训练 export 和 preference pair 必须被阻断。

### 2.8 Export observation 和 PreparedMessages 绑定

V3 export audit 不能只证明没有污染，还必须证明训练导出的 observation 就是模型当时看到的 observation。每个导出样本必须绑定：

- `prepared_messages_ref`
- `prepared_messages_sha256`
- `model_input_hash`
- `context_revision`
- `content_replacement_state`
- `tool_observation_ref`
- `observation_source_event_ref`
- `observation_matches_prepared_messages`
- `context_compaction_facts_ref`，如果触发 compaction

如果发生 context compaction，导出样本必须记录 compaction 前后 observation 的替换关系和 prepared messages hash。`observation_matches_prepared_messages = false`、缺少 `prepared_messages_ref`、`context_revision` 漂移、或 export observation 与历史 prepared messages 不一致时，样本必须 `diagnostic_only` 或被 export audit 阻断。

## 3. 代码和文档落点

建议沿用现有模块边界，避免大规模重命名。

```text
src/repo_harness/
  schema_versions.py                 # 新增 V3 schema/version 常量
  config/
    schemas.py                       # RunConfig / RuntimeConfig 的 Docker backend 扩展
  workspace/
    protocol.py                      # 扩展 backend 协议实际调用面
    adapter.py                       # 保留 local backend
    docker_adapter.py                # 新增 DockerWorkspaceAdapter
    backend_factory.py               # 新增 workspace backend factory
    schemas.py                       # DockerBackendFacts、ContainerExecutionFacts
  tasks/
    schemas.py                       # RealRepositorySourceFacts、SweBenchLikeTaskFacts、TaskAdapterFacts
    adapter.py                       # 固定 JSONL / task adapter，输出现有 TaskDefinition 兼容对象
    real_repository.py               # 新增真实 repository-level task adapter
    swebench_like.py                 # 新增 SWE-Bench-like adapter
  verifier/
    runner.py                        # final verifier strict replay 扩展
    swebench_like.py                 # fail-to-pass / pass-to-pass verifier
    schemas.py                       # final_verifier_result、environment spec、verifier plan 扩展
  evaluation/
    runner.py                        # backend factory、resume 接入
    experiment.py                    # resumable experiment runner
    schemas.py                       # ExperimentConfig docker、ExperimentResumeManifest、RunCheckpoint
  context/
    manager.py                       # context compaction 和 diagnostics
    schemas.py                       # ContextCompactionFacts
  reward/
    schemas.py                       # CoreFailureDiagnostics
    calculator.py                    # failure/reward metadata
  export/
    audit.py                         # V3 contamination checks
    exporter.py                      # V3 metadata export
  run_metadata/
    schemas.py                       # V3 run metadata refs、ToolContractSnapshot、policy snapshots
  trajectory/
    inspector.py                     # transcript/events/artifacts 基础不变量检查
  cli/
    main.py                          # inspect-v3-* 命令
  v3_acceptance.py                   # V3 acceptance report builder / inspector
```

建议新增测试和文档：

```text
tests/unit/test_docker_workspace_backend.py
tests/unit/test_real_repository_task_adapter.py
tests/unit/test_swebench_like_task_adapter.py
tests/unit/test_swebench_like_verifier_plan.py
tests/unit/test_v3_visibility_policy.py
tests/unit/test_v3_tool_contract_snapshot.py
tests/unit/test_v3_failure_diagnostics.py
tests/integration/test_docker_backend_e2e.py
tests/integration/test_real_repository_task_set_v3.py
tests/integration/test_swebench_like_adapter_to_run_task_v3.py
tests/integration/test_swebench_like_gold_patch_replay.py
tests/integration/test_experiment_resume_v3.py
tests/integration/test_context_compaction_v3.py
tests/integration/test_v3_trajectory_store.py
tests/integration/test_v3_export_audit.py
tests/integration/test_v3_acceptance.py

docs/v3/implementation-log/
docs/v3/review/implementation/
docs/v3/final-acceptance.md
docs/v3/walkthrough.md
```

## 4. 阶段总览

建议 V3 分为十四个实施阶段：

0. 第零阶段输入冻结：SWE 可实现性实验产物、固定 dataset snapshot 和 Docker 前置门槛。
1. V3 schema、版本常量、acceptance skeleton 和 visibility policy。
2. Docker workspace backend factory 和 container execution facts。
3. Docker backend 端到端命令、文件、patch 和 verification workspace 支持。
4. 真实 repository-level task adapter、SWE-Bench-like task adapter 和固定数据快照读取。
5. Source materialization、固定本地 mirror / archive、test patch / verifier patch 应用和 final-only verifier policy。
6. SWE-Bench-like environment spec、verifier plan 和 RepoHarness 自有 fail-to-pass / pass-to-pass final verifier。
7. Agent Loop 与真实 repository-level / SWE-Bench-like 任务集成、污染检查和工具协议不变量。
8. 可恢复 experiment runner、checkpoint 和 retry policy。
9. Context compaction 和 long rollout diagnostics。
10. Core failure diagnostics 和 reward metadata。
11. V3 export audit、训练 payload 污染扫描和 preference baseline。
12. V3 inspect 命令和 acceptance bundle。
13. V3 最终验收、文档、walkthrough 和审查收口。

每个阶段完成后都必须写入 `docs/v3/implementation-log/` 和 `docs/v3/review/implementation/`。阶段审查必须记录：实现范围、测试命令、产物路径、正例证据、负例证据、允许降级项、禁止降级项、残余风险和是否允许进入下一阶段。

## 5. 里程碑验收门

### 5.1 里程碑一：V3 schema 和 Docker backend 可执行

覆盖阶段 0 到阶段 3。

必须产出：

- `DockerBackendFacts`
- `ContainerExecutionFacts`
- `ToolContractSnapshot`
- `PermissionPolicySnapshot`
- `HookPolicySnapshot` 或 hook disabled facts
- `MCPPolicySnapshot` 或 MCP disabled/frozen facts
- `docker_stage_status.json` 兼容输入或 `docker_backend_status.json` V3 扩展输入
- `container_execution_facts/manifest.json`
- `container_execution_facts/*.json`
- `docker_phase_coverage_matrix.json`
- `inspect-workspace-backend --status-file RUN_DIR/docker_backend_status.json --assert-docker-backend`
- `inspect-workspace-backend --status-file RUN_DIR/docker_stage_status.json --assert-docker-backend`

必须证明：

- Docker mode 不能静默回退到 `local_process`。
- Docker Desktop Linux 虚拟机内存低于 `16 GiB` 时，Docker SWE-Bench-like 验收必须结构化失败。
- `evaluation.concurrency` 和 effective SWE workers 必须为 `1`。
- Docker facts 必须分字段记录 `docker_context`、server platform、server architecture、requested container platform、container `uname -m`、image platform、cross architecture emulation used、cleanup policy 和 cleanup status。
- `run_config_facts.json` 必须冻结 tool contract、permission policy、hook disabled/frozen state、MCP disabled/frozen state、scaffold policy、context policy、feedback policy、workspace backend policy 和 export policy refs。
- replay task 能在 Docker backend 下跑通。
- mock provider task 能在 Docker backend 下跑通。
- 有真实 provider 凭证时，至少一个真实 provider smoke 必须在 Docker backend 下通过 formal final verifier；无凭证时只能结构化 skip，不能把 skip 记为 accepted run。
- source checkout、setup、agent tool、`run_tests`、final patch capture、verification workspace、verifier patch / test patch apply、model final patch apply、fail-to-pass test execution、pass-to-pass test execution 和 final verifier 都有 container execution facts。

建议测试：

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_docker_workspace_backend.py
PATH=.venv/bin:$PATH python -m pytest tests/integration/test_docker_backend_e2e.py
PATH=.venv/bin:$PATH repo-harness inspect-workspace-backend --status-file RUN_DIR/docker_backend_status.json --assert-docker-backend
PATH=.venv/bin:$PATH repo-harness inspect-workspace-backend --status-file RUN_DIR/docker_stage_status.json --assert-docker-backend
```

禁止降级：

- Docker 不可用时不能伪装通过。
- Docker backend implemented 不能只写 summary 字段，必须有逐 phase evidence refs。
- 不能用官方 SWE-Bench harness 的 Docker 行为替代 RepoHarness 自己的 Docker backend。
- 不能破坏 V2 `docker_stage_status.json`、`workspace-backend-status`、`repo_harness_docker_stage_status_v2_v0` schema 和 `DOCKER_BACKEND_IMPLEMENTED` 兼容面。V3 可以新增字段或 alias，但旧 `--status-file` 入口和旧测试必须继续能复查 V2 acceptance 引用。
- 缺少 `ToolContractSnapshot` 或 policy snapshot 时，Docker smoke 不能被标记为正式可训练 run。

### 5.2 里程碑二：真实仓库任务、SWE-Bench-like adapter 和 RepoHarness 自有 verifier

覆盖阶段 4 到阶段 6。

必须产出：

- `task_adapter_facts.json`
- `real_repository_task_manifest.json`
- `swebench_like_task_facts.json`
- `source_checkout_facts.json`
- `source_materialization_report.json`
- `swebench_like_environment_specs.json`
- `swebench_like_verifier_plan.json`
- `final_verifier_result.json`
- `swebench_like_task_manifest.json`

真实 repository-level task 要求：

- 接入至少 3 个真实 repository-level task。
- 至少 1 个任务必须来自公开仓库固定 commit 或预下载公开归档，并记录 remote URL、base commit、archive sha256、source tree hash、dataset/source revision 和本地 materialization ref。
- 其余真实仓库任务可以来自本地受控 Git 仓库快照或本地归档，但不能只是同一个本地 fixture 的复制。
- 至少 1 个真实 repository-level task 必须在 Docker backend 下端到端完成 source checkout、setup、agent tools、final patch freeze、verification workspace strict patch replay 和 final verifier。

必须使用第零阶段 accepted 的固定任务：

- `pytest-dev__pytest-7220`
- `pytest-dev__pytest-8365`
- `sympy__sympy-24909`

任务数据来源要求：

- 阶段 0 之后默认读取 `tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/swebench_like_tasks.jsonl` 和同目录 manifest / sha256 文件。
- `runs/v3-swe-feasibility-20260502T083722Z/dataset/level2_dataset.jsonl` 只能作为生成受版本控制固定输入的来源证明，不能作为阶段 4 之后的默认读取路径。
- 如果重新生成数据，必须显式传入 `--feasibility-root` 或固定 dataset revision 来源，并使用 `princeton-nlp/SWE-bench_Lite` revision `6ec7bb89b9342f664a54a6e0a6ea6501d3437cc2`。
- 必须记录本地 JSONL sha256、candidate manifest sha256、selected task manifest sha256 和每个任务字段 sha256。
- 不能从 Hugging Face 浮动默认分支读取任务。
- 每个 SWE-Bench-like task 必须生成 resolved `SweBenchLikeEnvironmentSpec` 和 `SweBenchLikeVerifierPlan`。计划至少包含 setup command、base test command、fail-to-pass command、pass-to-pass command、test selector 转换规则、timeout、parser policy、Docker image 或 build source、network policy 和 expected artifact refs。

必须证明：

- RepoHarness 能读取真实 repository-level task adapter 数据并生成 task facts。
- RepoHarness 能读取 SWE-Bench-like task adapter 数据，并生成现有 `TaskDefinition` 兼容 YAML 或等价 `LoadedTask` / `RunnableTask` 对象。
- SWE-Bench-like adapter 输出必须能通过现有 `run_task` 入口进入常规 Agent Loop，或者实施计划明确扩展 `run_task` 接收 adapter 生成的任务对象；不能只生成 facts 或 manifest 后绕开 Agent Loop。
- RepoHarness 能从固定本地 source archive 或固定本地 mirror materialize 仓库到 Docker workspace。
- RepoHarness 能在 verifier workspace 应用 `test_patch` 或等价 verifier patch。
- RepoHarness 能运行 fail-to-pass / pass-to-pass 测试并生成 final verifier evidence。
- `patch`、`test_patch`、`FAIL_TO_PASS`、`PASS_TO_PASS`、官方 report 和 resolved status 不进入模型上下文或训练 target。

建议测试：

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_real_repository_task_adapter.py
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_swebench_like_task_adapter.py
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_swebench_like_verifier_plan.py
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v3_visibility_policy.py
PATH=.venv/bin:$PATH python -m pytest tests/integration/test_real_repository_task_set_v3.py
PATH=.venv/bin:$PATH python -m pytest tests/integration/test_swebench_like_adapter_to_run_task_v3.py
PATH=.venv/bin:$PATH python -m pytest tests/integration/test_swebench_like_gold_patch_replay.py
PATH=.venv/bin:$PATH repo-harness inspect-v3-task-set RUN_DIR --assert-complete
```

禁止降级：

- 不能用官方 `gold_patch_feasibility_probe` report 直接作为 RepoHarness final verifier result。
- 不能把 gold patch apply 成 agent output 后宣称模型成功。
- 不能把 test patch 或 FAIL_TO_PASS / PASS_TO_PASS 名称放进 prompt。
- 不能用 3 个本地新建 fixture 替代真实 repository-level task 集合。
- 不能用 1 个公开任务加 2 个重复本地 fixture 通过验收。3 个真实 repository-level task 必须有独立 source facts、task hash 和 verifier evidence；本地任务不能共享同一个复制 fixture 或只改 task id。
- 不能在 V3 核心验收中从浮动网络 clone 或浮动默认分支读取源码。

### 5.3 里程碑三：Agent Loop、resume、context 和 diagnostics

覆盖阶段 7 到阶段 10。

必须产出：

- `ExperimentResumeManifest`
- `RunCheckpoint`
- `experiment_resume_manifest.json`
- `run_checkpoint_manifest.json`
- `interrupted_run_diagnostics.json`
- `context_compaction_report.json`
- `long_rollout_diagnostics.json`
- `failure_diagnostics_core_report.json`
- `failure_distribution_report.json`

必须证明：

- 至少一个 SWE-Bench-like task 能进入完整 Agent Loop，而不是只跑 gold patch replay。
- 至少一个真实 repository-level task 能进入完整 Agent Loop，并在 Docker backend 下完成 final verifier。
- run-level checkpoint 可以从 interrupted 状态恢复或明确判定不可恢复。
- resume 会跳过 completed runs，继续 pending / interrupted runs。
- 中断注入至少覆盖 `baseline`、`agent_loop` 和 `final_verifier` 三个固定位置之一；每个 checkpoint 必须声明 run state、resume action、已完成 phase sha256、下一步 phase 和 run directory lock。
- 至少一个真实长工具输出触发 context compaction。
- 至少一个样例产生 no progress、repeated tool call 或 context limit diagnostics。
- core failure diagnostics 至少覆盖 invalid tool call、unfinished trajectory、regression、environment failure、parser low confidence、no patch、context limit 和 no progress。
- failure distribution 至少统计 provider、Docker backend、environment setup、verifier、permission、tool protocol、context limit、task quality 和 deterministic verifier failure。

建议测试：

```bash
PATH=.venv/bin:$PATH python -m pytest tests/integration/test_experiment_resume_v3.py
PATH=.venv/bin:$PATH python -m pytest tests/integration/test_context_compaction_v3.py
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v3_failure_diagnostics.py
PATH=.venv/bin:$PATH repo-harness inspect-experiment-resume RUN_DIR --manifest RUN_DIR/experiment_resume_manifest.json --assert-resumable
PATH=.venv/bin:$PATH repo-harness inspect-context-report RUN_DIR --report RUN_DIR/context_compaction_report.json --assert-consistent
PATH=.venv/bin:$PATH repo-harness inspect-reward-diagnostics RUN_DIR --core-report RUN_DIR/failure_diagnostics_core_report.json --distribution-report RUN_DIR/failure_distribution_report.json --assert-core-complete
```

禁止降级：

- 不能把 continuation run 写成任意 turn resume。
- 不能用 long rollout diagnostics 替代 context compaction。
- 不能让 context compaction 破坏 tool call / tool result pairing。

### 5.4 里程碑四：export audit、acceptance bundle 和最终验收

覆盖阶段 11 到阶段 13。

必须产出：

- SFT / RL rollout / preference export roots。
- `export_manifest.json`
- `audit_report.json`
- `audit_report.md`
- `preference_pair_baseline_report.json`
- `acceptance_bundle_manifest.json`
- `v3_acceptance_report.json`
- `transcript.jsonl`
- `events.jsonl`
- `artifacts.json`
- `run_config_facts.json`
- completed 或 terminal accepted run 的 `run_metadata.json`
- `ToolContractSnapshot`
- `PermissionPolicySnapshot`
- `HookPolicySnapshot` 或 hook disabled facts
- `MCPPolicySnapshot` 或 MCP disabled/frozen facts
- `inspect-v3-acceptance ACCEPTANCE_DIR/v3_acceptance_report.json --assert-complete`
- `inspect-acceptance-bundle ACCEPTANCE_DIR/acceptance_bundle_manifest.json --assert-immutable`

必须证明：

- `V3ContaminationDenylist` 中的 hidden tests、gold patch、test patch、FAIL_TO_PASS、PASS_TO_PASS、official report、resolved status、provider raw response、reasoning summary、Authorization marker、本机绝对路径、完整 decontamination metadata、final verifier hidden result、reward metadata、run outcome 和 hidden failure diagnostics 不进入 prompt、prepared messages、tool observation、transcript 中的模型可见记录、checkpoint、context compaction report 或正式训练 payload。
- diagnostic-only、skipped、invalid 样本不进入正式训练 JSONL。
- 有真实 provider 凭证时，真实 provider Docker smoke 的 export audit 必须纳入全局扫描；无凭证时只能结构化 skip，并记录 skip reason。
- 至少一个同条件多 rollout preference baseline 产生合格 pair，或者输出机器可审计的阻断分布并标记残余风险。
- `acceptance_bundle_manifest.json` 绑定最终报告、命令日志、输入 evidence refs、export roots、文档摘要和 sha256。
- `acceptance_bundle_manifest.json` 引用第二版最终验收报告 `runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json` 或等价 V2 regression report，并记录 sha256。
- V2 不变量继续通过机器检查：`inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete` 或带显式报告路径的 V3 兼容检查必须通过；oracle hidden feedback 默认 diagnostic-only、invalid / skipped 不进正式训练 JSONL、preference pair compare scope 不一致时阻断、provider raw response 和凭证标记不进入正式训练 payload。
- trajectory store、tool contract snapshots、policy snapshots 和 run facts 必须进入 acceptance bundle，并通过 inspect。completed 或 terminal accepted run 必须包含 `run_metadata.json`；interrupted / crashed run 必须包含 `run_config_facts.json`、结构化 interrupted / crash facts 和可读的 transcript / events / artifacts，但不要求最终 `run_metadata.json`。

建议测试：

```bash
PATH=.venv/bin:$PATH python -m pytest tests/integration/test_v3_export_audit.py
PATH=.venv/bin:$PATH python -m pytest tests/integration/test_v3_acceptance.py
PATH=.venv/bin:$PATH repo-harness build-v3-acceptance-inputs --run-selection-manifest RUN_SELECTION_MANIFEST --export-root EXPORT_ROOT --v2-report runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --pre-acceptance-doc docs/v3/implementation-plan.md --pre-acceptance-doc docs/v3/review/implementation-plan-review.md --output ACCEPTANCE_INPUTS
PATH=.venv/bin:$PATH repo-harness build-v3-acceptance-report --acceptance-dir ACCEPTANCE_DIR --input-manifest ACCEPTANCE_INPUTS --output ACCEPTANCE_DIR/v3_acceptance_report.json
PATH=.venv/bin:$PATH repo-harness build-v3-acceptance-bundle --acceptance-dir ACCEPTANCE_DIR --input-manifest ACCEPTANCE_INPUTS --report ACCEPTANCE_DIR/v3_acceptance_report.json --documentation-ref docs/v3/final-acceptance.md --documentation-ref docs/v3/walkthrough.md --output ACCEPTANCE_DIR/acceptance_bundle_manifest.json
PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance ACCEPTANCE_DIR/v3_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle ACCEPTANCE_DIR/acceptance_bundle_manifest.json --assert-immutable
```

禁止降级：

- 不能只检查 summary，不重新读取 evidence refs。
- 不能用 “官方 harness 通过” 代替 RepoHarness V3 acceptance。
- 不能把没有真实 pair 的 preference export 写成成功训练偏好数据。

## 6. 阶段详细计划

### 阶段 0：第零阶段输入冻结

目标：把本次可实现性实验变成 V3 实施的可审计输入。

实现任务：

- 新增 `docs/v3/implementation-log/00-stage-00-feasibility-input.md`。
- 新增 `v3_feasibility_input_manifest.json`，把第零阶段输入冻结为不可变引用。
- 新增写型冻结命令，例如 `prepare-v3-swebench-fixture --feasibility-root runs/v3-swe-feasibility-20260502T083722Z --fixture-dir tests/fixtures/v3/swebench_lite_fixed --evidence-dir docs/v3/evidence/swebench-lite-fixed`。
- 该写型命令读取 `runs/v3-swe-feasibility-20260502T083722Z/feasibility_decision.json`，生成 adapter-visible input 和 evaluator-only evidence 两套受版本控制输入：
  - `tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/swebench_like_tasks.jsonl`
  - `tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/task_input_manifest.json`
  - `tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/*.sha256`
  - `docs/v3/evidence/swebench-lite-fixed/evaluator_only/gold_patch_predictions.jsonl`
  - `docs/v3/evidence/swebench-lite-fixed/evaluator_only/official_harness_reports.json`
  - `docs/v3/evidence/swebench-lite-fixed/evaluator_only/evaluator_evidence_manifest.json`
- 新增只读检查命令，例如 `inspect-v3-swebench-fixture --fixture-dir tests/fixtures/v3/swebench_lite_fixed --evidence-dir docs/v3/evidence/swebench-lite-fixed --manifest tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/v3_feasibility_input_manifest.json --assert-frozen`。该命令只能读取并校验固定输入、evaluator-only evidence 引用和 sha256，不能创建、修改或删除文件。
- `prepare-v3-swebench-fixture` 必须移除 adapter-visible JSONL 中的 `patch` 字段、raw `test_patch`、raw `FAIL_TO_PASS` / `PASS_TO_PASS`、gold patch prediction、official resolved status 和 official harness report，只保留 task id、repo、base commit、problem statement hash、source refs、verifier refs、verifier evidence hashes 和必要的 non-secret metadata。
- 生成 `tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/v3_feasibility_input_manifest.json`，其中只引用 evaluator-only evidence 的 sha256 和 relative path，不内联 gold patch 内容。
- 校验 `current_v3_entry_status = green_ready_for_v3_implementation_plan`。
- 校验三任务 accepted 清单、dataset revision 和 split。
- 重新计算并校验以下文件的 sha256，不能只检查文件存在：
  - `runs/v3-swe-feasibility-20260502T083722Z/dataset/level2_dataset.jsonl`
  - `runs/v3-swe-feasibility-20260502T083722Z/candidate_task_manifest.json`
  - `runs/v3-swe-feasibility-20260502T083722Z/level2/selected_task_manifest.json`
  - `runs/v3-swe-feasibility-20260502T083722Z/level2/gold_patch_predictions.jsonl`
  - `runs/v3-swe-feasibility-20260502T083722Z/level1/gold_patch_prediction.sha256`
  - `runs/v3-swe-feasibility-20260502T083722Z/level2/gold_patch_predictions.sha256`
- 对复制或生成后的以下受版本控制文件重新计算 sha256：
  - `tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/swebench_like_tasks.jsonl`
  - `tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/task_input_manifest.json`
  - `tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/v3_feasibility_input_manifest.json`
  - `docs/v3/evidence/swebench-lite-fixed/evaluator_only/gold_patch_predictions.jsonl`
  - `docs/v3/evidence/swebench-lite-fixed/evaluator_only/official_harness_reports.json`
  - `docs/v3/evidence/swebench-lite-fixed/evaluator_only/evaluator_evidence_manifest.json`
- 记录每个 accepted task 的关键字段哈希：`repo`、`instance_id`、`base_commit`、`problem_statement`、`test_patch`、`FAIL_TO_PASS`、`PASS_TO_PASS` 和 `environment_setup_commit`。

完成标准：

- V3 implementation plan 后续阶段可以通过 manifest 引用固定任务输入。
- 任一冻结文件的重新计算 sha256 与 manifest 不一致时，SWE-Bench-like 阶段必须阻断。
- 如果实验目录缺失或 decision 不是 Green，V3 SWE-Bench-like 阶段必须阻断。
- 阶段 0 完成后，阶段 4 到阶段 13 的默认 adapter 输入必须是 `tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/`，不是 `runs/`。
- `inspect-v3-swebench-fixture --assert-frozen` 必须通过，并证明 adapter-visible input 与 evaluator-only evidence 已拆分。
- `inspect-swebench-like` 必须拒绝 adapter 输入根目录中出现 `gold_patch_predictions.jsonl`、`patch` 字段、raw `test_patch`、raw `FAIL_TO_PASS` / `PASS_TO_PASS`、official harness report 或 resolved status。

### 阶段 1：V3 schema、版本常量和 visibility policy

目标：先把所有新增事实对象和污染边界定义清楚，避免后续实现散落字段。

实现任务：

- 增加 V3 schema version 常量。
- 定义 Docker facts、真实 repository-level facts、SWE-Bench-like facts、TaskAdapterFacts、`SweBenchLikeEnvironmentSpec`、`SweBenchLikeVerifierPlan`、CoreFailureDiagnostics、ContextCompactionFacts、ExperimentResumeManifest、trajectory store facts、`ToolContractSnapshot`、policy snapshots 和 acceptance report schema。
- 更新 `RunConfig`、`RuntimeConfig`、`ExperimentConfig` 和 run config fixture，使 experiment runner 能显式接受 Docker backend，并在 resume manifest 中保留 Docker backend facts。
- 并发配置优先复用现有 `evaluation.concurrency`。若新增 `swebench_like.max_workers`，必须定义它与 `evaluation.concurrency` 的关系、优先级和 inspect 检查规则，避免两个并发字段各自生效。
- 定义 `VisibilityPolicy` 或等价可见性检查规则。
- 定义统一 `V3ContaminationDenylist`，至少包含 `patch`、`test_patch`、`FAIL_TO_PASS`、`PASS_TO_PASS`、official report、resolved status、provider raw response、reasoning summary、Authorization marker、本机绝对路径、完整 decontamination metadata、final verifier hidden result、reward metadata、run outcome 和 hidden failure diagnostics。
- 明确 V3 当前代码迁移门：
  - 当前 `run_task` 仍硬拒绝 Docker；阶段 1/2 必须把 Docker rejection 改成 backend factory 结构化选择和结构化 unavailable failure，不能继续早期硬拒绝。
  - 当前 `run_task` 只接收 `task_path` 并通过 `load_task` 产生任务；阶段 1/2 必须提供 adapter 生成 `TaskDefinition` YAML 的路径，或扩展 `run_task` 接收 `LoadedTask` / `RunnableTask` 的显式入口。
  - SWE-Bench-like final-only task 必须在 schema 和 policy 层阻断 `oracle_hidden_feedback`，并覆盖 scaffold 默认反馈策略，默认只能使用 `disabled`。
  - `ContextBuilder` 当前可能暴露 workspace root 绝对路径和 `test_command`；阶段 1/2 必须加入 prompt path redaction 和 verifier command redaction，模型可见 context 不得包含 host absolute path、hidden verifier command、FAIL_TO_PASS/PASS_TO_PASS 或 final-only test command。
  - `run_config_facts.json` 必须在 Agent Loop 前写入；completed 或 terminal accepted run 的 `run_metadata.json` 必须在最终终态后原子写入；interrupted / crashed run 如果没有到达最终 metadata 写入点，必须写入结构化 interrupted / crash facts；阶段 1/2 必须保留 V2 legacy inspect 兼容。

完成标准：

- schema 单元测试覆盖必填字段、非法组合、legacy 兼容和污染字段拒绝。
- `gold_patch` / `test_patch` 字段只能被 verifier facts 引用，不能被 prompt builder 引用。
- `ExperimentConfig accepts docker backend and resume runner preserves docker backend facts` 必须有单元测试或集成测试覆盖。
- denylist 单元测试必须覆盖 prompt、prepared messages、tool observation、transcript、checkpoint、context compaction report、SFT / RL / preference export。
- migration gate 单元测试必须证明 Docker 不再被无条件硬拒绝、adapter 任务可以进入 `run_task`、SWE-Bench-like final-only 拒绝 `oracle_hidden_feedback`、ContextBuilder 不泄漏 host absolute path 或 hidden test command。

### 阶段 2：Docker backend factory 和基础 facts

目标：引入 backend factory，保留 local backend，新增 Docker backend 的生命周期和事实记录。

实现任务：

- 新增 `DockerWorkspaceAdapter`。
- 新增 backend factory，替代 runner 中硬编码 `LocalWorkspaceAdapter` 的路径。
- 扩展 `WorkspaceAdapter` 协议，覆盖当前实际调用面，并使用现有方法名作为兼容基线：`run_command`、`read_text`、`write_text`、`resolve_workspace_path`、`apply_patch`、`capture_final_patch`、`create_source_checkout`、`create_setup_workspace`、`capture_dependency_state`、`create_agent_workspace`、`create_verification_workspace`、`restore_dependency_state` 和 `cleanup_workspaces`。如果 V3 新增别名，必须同步迁移所有调用点并保留兼容测试。
- `evaluation.runner`、`ToolExecutionContext`、minimal tools、setup helper、`PytestVerifier`、SWE-Bench-like verifier 和 `ContextBuilder` 不能依赖 `LocalWorkspaceAdapter` 具体类型，必须依赖扩展后的 workspace backend 协议或 facade。
- `ContextBuilder` 在 Docker mode 下不能使用裸 `Path(workspace.workspace_path).read_text()` 读取仓库文件。它必须通过 workspace facade 的 `read_text` / listing API 读取 repo context，或者读取由 backend 生成并带 sha256 的 repository context artifact ref；验收测试必须证明 Docker mode 下 repo context 读取不会绕过 workspace backend。
- 记录 Docker availability、server version、Docker Desktop Linux 虚拟机内存、docker context、server platform、server architecture、requested container platform、container `uname -m`、image ref、image id、image platform、network policy、mount policy、workdir、cross architecture emulation facts 和 cleanup policy。
- Docker 不可用时输出结构化 failure，不允许静默回退。

完成标准：

- replay smoke 在 Docker backend 下能完成基础 workspace lifecycle。
- `inspect-workspace-backend --status-file RUN_DIR/docker_backend_status.json --assert-docker-backend` 会在内存低于 `16 GiB`、`evaluation.concurrency != 1`、effective SWE workers != 1、container architecture 缺失或 cleanup status 缺失时失败。
- 类型和集成测试证明 runner、tools、verifier、setup 和 context builder 不再需要 `LocalWorkspaceAdapter` 具体类型。
- Docker mode context builder 测试证明 repo context 读取通过 workspace facade 或 backend artifact，不使用裸宿主机 `Path.read_text` 读取 container path。
- Docker mode rejected 的 V2 测试要更新为 V3 语义：如果 backend implemented，则不再期待拒绝；如果 Docker unavailable，则期待结构化失败。

### 阶段 3：Docker command、file、patch 和 verifier workspace

目标：补齐实际调用面，而不是只实现协议生命周期方法。

实现任务：

- Docker backend 支持 run command、resolve path、read text、write text、apply patch、capture final patch。
- Docker backend 支持 cleanup workspaces，并且 cleanup 只能作用于本次 run id、image tag 或实验 namespace。
- verification workspace strict patch replay 在 Docker backend 下执行。
- 每个 phase 生成 `ContainerExecutionFacts`。
- 生成 `docker_phase_coverage_matrix.json`。

完成标准：

- phase coverage 包含 source checkout、setup、agent tool、run_tests、final patch capture、verification workspace creation、verifier patch / test patch apply、model final patch apply、fail-to-pass test execution、pass-to-pass test execution 和 final verifier。
- 每个 phase 都必须引用 `container_execution_facts/manifest.json` 中的逐命令 facts 文件和输出 artifact sha256。
- inspect 命令拒绝 phase 缺失。

### 阶段 4：真实仓库和固定数据快照 task adapter

目标：RepoHarness 读取真实 repository-level task 清单和第零阶段固定 JSONL 快照，生成自己的 task facts。

实现任务：

- 新增真实 repository-level task adapter。
- 新增 `real_repository_task_manifest.json`。
- 至少登记 3 个真实 repository-level task，其中至少 1 个来自公开仓库固定 commit 或预下载公开归档。
- 对公开来源任务记录 remote URL、base commit、archive sha256 或 mirror sha256、source tree hash、dataset/source revision、local materialization ref 和 decontamination status。
- 新增 SWE-Bench-like fixed JSONL adapter。
- 读取 `tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/swebench_like_tasks.jsonl`。
- 记录 dataset name、revision、split、instance id、repo、base commit、environment setup commit、test patch hash、F2P/P2P hash。
- 生成 `task_adapter_facts.json` 和 `swebench_like_task_facts.json`。

完成标准：

- 3 个真实 repository-level task 都能被 adapter 读取。
- `inspect-v3-task-set RUN_DIR --assert-complete` 拒绝 3 个真实仓库任务全部来自本地新建 fixture，或拒绝 1 个公开任务加 2 个重复本地 fixture 的组合。
- 3 个 accepted task 都能被 adapter 读取。
- adapter 拒绝字段为空的 task。
- adapter 拒绝 dataset revision 不匹配或 sha256 不匹配的 snapshot。

### 阶段 5：source materialization、固定源码输入和 verifier patch

目标：RepoHarness 自己 materialize 仓库并准备 verifier workspace。

实现任务：

- 阶段 5 的 V3 核心路径只允许从固定本地 source archive 或固定本地 mirror materialize，不从浮动网络 clone，也不从浮动默认分支读取源码。
- 对每个 task checkout 或 extract 到 base commit。
- 记录 source type、remote URL 或 mirror source、base commit、resolved commit、archive sha256 或 mirror sha256、source tree hash、remotes / branches / tags stripped 状态、checkout path redaction status 和 materialization command facts。
- 如果实现允许联网创建 mirror 或 archive，该步骤只能作为受控预取阶段，必须记录命令、缓存位置、resolved commit、sha256、失败状态和验收证据；正式 V3 run 仍只能读取固定本地输入。
- 在 verifier workspace 应用 test patch 或 verifier patch。
- 保证 agent workspace 不包含 test patch / verifier patch。

完成标准：

- `source_checkout_facts.json` 和 `source_materialization_report.json` 完整。
- agent workspace 和 verifier workspace 有明确隔离。
- 污染检查证明 test patch 不在模型可见 workspace diff、prompt 或 transcript 中。
- source provenance 缺失、浮动网络 clone 或 source hash 不匹配时，inspect 必须失败。

### 阶段 6：SWE-Bench-like verifier plan 和 RepoHarness 自有 F2P/P2P final verifier

目标：实现 RepoHarness 自己的 SWE-Bench-like final verifier。

实现任务：

- 为每个 accepted task 生成 resolved `SweBenchLikeEnvironmentSpec` 和 `SweBenchLikeVerifierPlan`。
- `SweBenchLikeEnvironmentSpec` 至少包含 Docker image 或 build source、Python / dependency setup command、environment setup commit、setup timeout、network policy、mount policy 和 expected parser。
- `SweBenchLikeVerifierPlan` 至少包含 base test command、fail-to-pass command、pass-to-pass command、test selector 转换规则、selector source、selector cache、selector failure strategy、per-command timeout、parser policy、expected artifact refs 和 hidden visibility policy。
- 解析 `FAIL_TO_PASS` 和 `PASS_TO_PASS`，并通过 verifier plan 转换成明确命令。
- selector 转换必须覆盖带文件路径的 pytest node id 和裸函数名两类情况。`sympy__sympy-24909` 必须作为裸函数名 selector 的单元测试和集成测试样例，不能只覆盖 `pytest-dev` 这类带路径 selector。
- 在 verification workspace 中应用模型 final patch。
- 运行 F2P/P2P 测试命令。
- 生成 `final_verifier_result.json`。
- 记录 parser confidence 和 low confidence failure。

完成标准：

- 3 个 accepted task 都有 resolved verifier plan，且 inspect 重新读取并执行这些命令，而不是只检查字段存在。
- 每个 accepted task 都必须记录 base workspace 的 fail-to-pass failing evidence、pass-to-pass baseline evidence、gold patch passing evidence，以及模型 final patch 的独立 verifier result。
- 如果 FAIL_TO_PASS 在 baseline 已经通过、PASS_TO_PASS 在 baseline 未通过、PASS_TO_PASS 解析为空、selector 转换为空、测试集合为空或 parser confidence 低于阈值，inspect 必须失败或把任务标记为不可验收。
- 对第零阶段 3 个 accepted task，gold patch replay 在 RepoHarness verifier 下通过。
- public / hidden visibility policy 清晰：测试名称和 hidden evidence 不进入模型可见上下文。

### 阶段 7：Agent Loop 集成和污染检查

目标：让真实 repository-level task 和 SWE-Bench-like task 进入常规 RepoHarness agent loop。

实现任务：

- prompt builder 只提供 issue statement 和允许的仓库上下文。
- tool execution 使用 Docker backend。
- final patch 冻结后进入 independent verification workspace。
- Agent Loop 结束并冻结 final patch 后才允许启动 final verifier。
- final verifier result、hidden verifier stdout / stderr、reward metadata、run outcome 和 failure diagnostics 不能被同一次 Agent Loop 或 resume 后的同一 agent 读取。
- 增加训练 payload 污染检查。

完成标准：

- 至少一个 SWE-Bench-like task 进入常规 Agent Loop，并由 RepoHarness 自己完成 final patch freeze、verification workspace strict replay 和 final verifier。
- 至少一个真实 repository-level task 进入常规 Agent Loop，并在 Docker backend 下完成 final verifier。
- mock provider 或 replay-driven run 只能作为附加 smoke，不能替代上述两个任务类别。
- 每个 tool call 有终态 tool result。
- export audit 扫描确认 `V3ContaminationDenylist` 未进入 prompt、prepared messages、tool observation、transcript 中的模型可见记录、checkpoint、context compaction report 或 training target。

### 阶段 8：可恢复 Experiment Runner

目标：把真实任务运行变成可恢复实验，而不是一次性脚本。

实现任务：

- 新增 run states：pending、running、completed、failed、skipped、interrupted。
- 新增 checkpoint manifest。
- resume 跳过 completed，继续 pending / interrupted。
- 增加固定中断注入场景：`--inject-interrupt-after baseline`、`--inject-interrupt-after agent_loop`、`--inject-interrupt-after final_verifier`。实现形式可以是测试专用参数或测试 fixture，但必须写入 command log。
- 区分 provider transient、Docker infrastructure、environment setup、deterministic verifier 和 task quality failure。
- `RunCheckpoint` 只能在对应事实文件已经存在时引用它们。`run_metadata_ref` 只能出现在最终 metadata 已经原子写入后的 checkpoint；final metadata 生成前的 checkpoint 只能引用 `run_config_facts_ref`、events offsets、transcript offsets 和 artifact manifest refs。
- continuation run 必须生成新的 run id，并记录 parent run refs、允许继承字段和禁止继承的 evaluator-only facts；不能覆盖原 run，也不能把 hidden verifier / reward / outcome 注入继续运行上下文。

完成标准：

- 构造中断实验并恢复，至少覆盖上述中断点之一。
- 不可恢复状态必须有明确判定标准，例如缺失必需 checkpoint、sha256 不匹配、run directory lock 冲突或 final verifier evidence 不完整。
- 恢复后不覆盖原 evidence。
- run directory lock 防止两个 worker 写同一目录。
- checkpoint inspect 必须拒绝 final metadata 写入前出现 `run_metadata_ref` 的 checkpoint。

### 阶段 9：Context compaction 和 long rollout diagnostics

目标：证明长输出任务可压缩、可诊断。

实现任务：

- 实现 deterministic tool observation compaction。
- 记录 tokens before/after、kept ids、dropped ids、replaced tool result ids、prepared messages ref、prepared messages hash、model input hash、context revision、content replacement state 和 observation source event ref。
- 实现 repeated tool call、no progress、context limit diagnostics。

完成标准：

- 至少一个真实长工具输出触发 compaction。
- 至少一个 long rollout diagnostics 样例产生结构化诊断。
- compaction 后 tool pairing 仍完整。
- `context_compaction_report.json` 必须证明 `observation_matches_prepared_messages = true`，或把不匹配样本标记为 diagnostic-only。
- `long_rollout_diagnostics.json` 必须有独立 inspect 命令，不能只隐含在 context inspect 中。

### 阶段 10：Core failure diagnostics 和 reward metadata

目标：提升训练数据过滤价值，但不实现新的 reward model。

实现任务：

- 生成 `failure_diagnostics_core_report.json`。
- 生成 `failure_distribution_report.json`。
- 记录 patch size、files changed、tool call count、test run count、invalid tool call count、unfinished trajectory、permission violation、regression detected、environment failure category、parser low confidence、no patch、provider transient、deterministic verifier failure、context limit、no progress。
- 统计 provider、Docker backend、environment setup、verifier、permission、tool protocol、context limit、task quality、parser confidence 和 deterministic verifier failure 的失败分布。
- 仅把这些作为 metadata / filtering evidence。

完成标准：

- `inspect-reward-diagnostics RUN_DIR --core-report RUN_DIR/failure_diagnostics_core_report.json --distribution-report RUN_DIR/failure_distribution_report.json --assert-core-complete` 同时检查 `failure_diagnostics_core_report.json` 和 `failure_distribution_report.json`。
- penalty 权重和 reward hacking 深度分析仍是计划内增强，不是核心验收必需。

### 阶段 11：Export audit 和 preference baseline

目标：证明 V3 训练导出仍然安全可审计。

实现任务：

- 扩展 SFT / RL / preference export metadata。
- 扫描 `V3ContaminationDenylist`。
- 继承 V2 export 契约：format-specific export directory、样本级 audit items、training eligibility、skipped manifest、数据文件 sha256、`export_manifest.json`、`audit_report.json`、`audit_report.md`。
- 继承或扩展 V2 严格 `CompareScope` 默认值，preference compare scope 不能少于 V2 字段；新增 Docker backend、source hash、ToolContractSnapshot、policy snapshots、context revision 和 verifier plan refs。
- 对 run artifact 级别执行 redaction audit，覆盖 `events.jsonl`、`artifacts.json`、raw provider artifact、container facts、source facts、run metadata 和正式训练 JSONL。acceptance bundle 是阶段 12/13 产物，它的 redaction / denylist 审计由 `inspect-acceptance-bundle` 执行。
- 对新增真实仓库和 SWE-Bench-like Agent Loop run 执行 export 闭环；如果某个 run 不可训练，必须由样本级 audit 明确标记 `diagnostic_only`、`skipped` 或 `invalid`，并写入 skipped manifest。
- 每个 export sample 必须绑定 `prepared_messages_ref`、`prepared_messages_sha256`、`model_input_hash`、`context_revision`、`content_replacement_state`、`tool_observation_ref`、`observation_source_event_ref` 和 `observation_matches_prepared_messages`。
- 对至少一个任务做同条件多 rollout preference baseline。
- 如果没有合格 pair，输出 blocked distribution 并标记残余风险。

完成标准：

- export audit 证明 `V3ContaminationDenylist` 未进入 prompt、prepared messages、tool observation、transcript 中的模型可见记录、checkpoint、context compaction report 或正式训练 payload。
- diagnostic-only、skipped、invalid 不进入正式 JSONL。
- preference pair compare scope 包含 source hash、verifier、tool protocol、ToolContractSnapshot、permission policy、hook/MCP disabled facts、context policy、context revision、scaffold、模型、预算、Docker backend、source materialization 和 verifier plan。
- `observation_matches_prepared_messages = false`、缺少 prepared messages ref、context revision 漂移或 observation 与历史 prepared messages 不一致时，样本不得进入正式训练 JSONL。

### 阶段 12：Inspect 命令和 acceptance bundle

目标：所有 V3 evidence 可以被机器复查。

实现任务：

- `inspect-trajectory-store RUN_DIR --assert-readable`
- `inspect-tool-contract RUN_DIR --assert-frozen`
- `inspect-workspace-backend --status-file RUN_DIR/docker_backend_status.json --assert-docker-backend`
- `inspect-workspace-backend --status-file RUN_DIR/docker_stage_status.json --assert-docker-backend`
- `inspect-v3-task-set RUN_DIR --assert-complete`
- `inspect-v3-swebench-fixture --fixture-dir tests/fixtures/v3/swebench_lite_fixed --evidence-dir docs/v3/evidence/swebench-lite-fixed --manifest tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/v3_feasibility_input_manifest.json --assert-frozen`
- `inspect-swebench-like RUN_DIR --manifest RUN_DIR/swebench_like_task_manifest.json --assert-complete`
- `inspect-experiment-resume RUN_DIR --manifest RUN_DIR/experiment_resume_manifest.json --assert-resumable`
- `inspect-context-report RUN_DIR --report RUN_DIR/context_compaction_report.json --assert-consistent`
- `inspect-long-rollout-diagnostics RUN_DIR --report RUN_DIR/long_rollout_diagnostics.json --assert-complete`
- `inspect-reward-diagnostics RUN_DIR --core-report RUN_DIR/failure_diagnostics_core_report.json --distribution-report RUN_DIR/failure_distribution_report.json --assert-core-complete`
- `inspect-v3-export-audit RUN_DIR --manifest RUN_DIR/export_manifest.json --audit-report RUN_DIR/audit_report.json --assert-clean`
- `build-v3-run-selection-manifest --run-ref role=replay,path=RUN_DIR_REPLAY --run-ref role=mock_provider,path=RUN_DIR_MOCK --run-ref role=credential_gated_real_provider,path=RUN_DIR_REAL_OR_SKIP --run-ref role=real_repository,path=RUN_DIR_REAL_REPO --run-ref role=swebench_like,path=RUN_DIR_SWEBENCH_LIKE --run-ref role=resume,path=RUN_DIR_RESUME --run-ref role=context,path=RUN_DIR_CONTEXT --run-ref role=long_rollout,path=RUN_DIR_LONG_ROLLOUT --run-ref role=failure_diagnostics,path=RUN_DIR_FAILURE --output RUN_SELECTION_MANIFEST`
- `build-v3-acceptance-inputs --run-selection-manifest RUN_SELECTION_MANIFEST --export-root EXPORT_ROOT --v2-report runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --pre-acceptance-doc docs/v3/implementation-plan.md --pre-acceptance-doc docs/v3/review/implementation-plan-review.md --output ACCEPTANCE_INPUTS`
- `build-v3-acceptance-report --acceptance-dir ACCEPTANCE_DIR --input-manifest ACCEPTANCE_INPUTS --output ACCEPTANCE_DIR/v3_acceptance_report.json`
- `build-v3-acceptance-bundle --acceptance-dir ACCEPTANCE_DIR --input-manifest ACCEPTANCE_INPUTS --report ACCEPTANCE_DIR/v3_acceptance_report.json --documentation-ref docs/v3/final-acceptance.md --documentation-ref docs/v3/walkthrough.md --output ACCEPTANCE_DIR/acceptance_bundle_manifest.json`
- `inspect-v3-acceptance ACCEPTANCE_DIR/v3_acceptance_report.json --assert-complete`
- `inspect-acceptance-bundle ACCEPTANCE_DIR/acceptance_bundle_manifest.json --assert-immutable`

完成标准：

- 每个 inspect 命令重新读取 evidence refs 和 sha256。
- summary 与 evidence 漂移时失败。
- 每个 inspect 命令的输入路径必须写入 command log 和 acceptance bundle，不能依赖当前目录、latest run 或环境变量。
- `inspect-trajectory-store` 必须验证 `transcript.jsonl`、`events.jsonl`、`artifacts.json`、ArtifactRef 可解析性、sha256、size_bytes、relative path、events offset、transcript offset、RunRecorder crash-readable 状态。
- `inspect-tool-contract` 必须验证 ToolContractSnapshot、PermissionPolicySnapshot、HookPolicySnapshot 或 hook disabled facts、MCPPolicySnapshot 或 MCP disabled/frozen facts、scaffold/context/feedback/export policy snapshot refs。
- `inspect-workspace-backend` 保留 `--status-file` 兼容入口；如新增 `RUN_DIR` 位置参数，也必须有兼容测试。
- `inspect-v3-task-set` 同时检查真实 repository-level task 和 SWE-Bench-like task，不允许只检查其中一类。
- `inspect-swebench-like` 必须重新计算固定 JSONL、selected manifest、verifier plan 和逐任务字段哈希。
- `inspect-v3-swebench-fixture` 必须证明 adapter-visible input 不含 gold patch prediction、数据集 `patch` 字段、raw `test_patch`、raw `FAIL_TO_PASS` / `PASS_TO_PASS`、official harness report 或 resolved status，并证明 evaluator-only evidence 只能通过 manifest sha256 引用。
- `inspect-acceptance-bundle` 必须对 acceptance bundle 自身执行 redaction / denylist 审计，覆盖最终报告、命令日志、输入 evidence refs、export roots、文档摘要和 sha256 manifest，不能依赖阶段 11 的 export audit 代替。
- `RUN_SELECTION_MANIFEST` 必须是显式 typed run refs，不允许从 `EXPERIMENT_DIR` 隐式扫描、猜测 latest run 或按目录名自动挑选。每个 ref 必须包含 role、path、sha256、run id、run state、expected evidence types 和 structured skip reason。
- `ACCEPTANCE_INPUTS` 必须是显式文件路径，建议为 `RUN_DIR/v3_acceptance_inputs.json` 或 `EXPERIMENT_DIR/v3_acceptance_inputs.json`。它必须列出 `RUN_SELECTION_MANIFEST`、replay、mock provider、credential-gated real provider、真实 repository-level、SWE-Bench-like、trajectory store、tool contract snapshots、resume、context、long rollout、failure diagnostics、source materialization、export roots、V2 report 和 pre-acceptance documentation refs 的路径与 sha256。这里的 documentation refs 只指生成 acceptance report 前已经冻结的范围文档、实施文档、审查文档和 implementation log；`docs/v3/final-acceptance.md` 与 `docs/v3/walkthrough.md` 是 post-acceptance 文档，由 `acceptance_bundle_manifest.json` 在 report 生成后绑定。
- `build-v3-acceptance-report` 必须拒绝已经存在的 `ACCEPTANCE_DIR`，并记录创建时间、`ACCEPTANCE_DIR/acceptance_command_log.jsonl`、输入 manifest sha256、typed run refs、export root sha256 和 acceptance builder version。
- 负例测试必须覆盖：篡改 summary、删除 evidence ref、修改 sha256、替换旧 `RUN_DIR`、注入官方 harness report、污染 prompt 字段、污染 checkpoint、污染 context compaction report、复用旧 acceptance directory、adapter 输入目录出现 gold patch prediction、缺失 transcript/events/artifacts、ArtifactRef sha256 不匹配、ToolContractSnapshot 缺失、export observation 与 prepared messages 不匹配、`ACCEPTANCE_INPUTS` 缺少必需类别、报告引用 `ACCEPTANCE_INPUTS` 外部 evidence、documentation ref 在 bundle 后变化、command log 与输入 manifest 不一致、credential-gated real provider skip 被伪装成 accepted run。

### 阶段 13：最终验收和文档收口

目标：生成完整 V3 acceptance，保守说明能力边界。

实现任务：

- 运行 `build-v3-run-selection-manifest --run-ref ... --output RUN_SELECTION_MANIFEST`，显式冻结每个验收类别对应的 run。
- 运行 `build-v3-acceptance-inputs --run-selection-manifest RUN_SELECTION_MANIFEST --export-root EXPORT_ROOT --v2-report runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --pre-acceptance-doc docs/v3/implementation-plan.md --pre-acceptance-doc docs/v3/review/implementation-plan-review.md --output ACCEPTANCE_INPUTS`。
- 运行 `build-v3-acceptance-report --acceptance-dir ACCEPTANCE_DIR --input-manifest ACCEPTANCE_INPUTS --output ACCEPTANCE_DIR/v3_acceptance_report.json`。
- 生成 `ACCEPTANCE_DIR/v3_acceptance_report.json`。
- 引用并校验 V2 acceptance 或 V2 regression report。
- 编写 `docs/v3/final-acceptance.md`。
- 编写 `docs/v3/walkthrough.md`。
- 运行 `build-v3-acceptance-bundle --acceptance-dir ACCEPTANCE_DIR --input-manifest ACCEPTANCE_INPUTS --report ACCEPTANCE_DIR/v3_acceptance_report.json --documentation-ref docs/v3/final-acceptance.md --documentation-ref docs/v3/walkthrough.md --output ACCEPTANCE_DIR/acceptance_bundle_manifest.json`，生成 `ACCEPTANCE_DIR/acceptance_bundle_manifest.json`。
- 汇总 implementation log 和 review 记录。

完成标准：

- `ACCEPTANCE_DIR` 必须是不存在的新目录；如果目录已存在，acceptance builder 必须失败，不能覆盖旧验收证据。
- `inspect-v3-acceptance ACCEPTANCE_DIR/v3_acceptance_report.json --assert-complete` 必须校验所有 V3 evidence 都来自 `ACCEPTANCE_INPUTS` 明确绑定的 typed run refs、export roots、V2 report、pre-acceptance docs 和 command log。
- 全量 `python -m pytest` 必须通过，或在文档中明确列出只因外部 credential / platform gating 被结构化 skip 的测试。
- V2 regression 必须通过：`inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete`，并且 V2 相关 smoke / unit 测试不得被 V3 改坏。
- 每个 completed 或 terminal accepted V3 run 都必须有 `run_config_facts.json` 和 `run_metadata.json`；skipped / interrupted / crashed run 必须有可读 `run_config_facts.json` 和结构化 skipped / interrupted / crash facts，但不要求最终 `run_metadata.json`。
- V2 验收仍可读取。
- V2 不变量有机器复查证据，不能只在文档中声明。
- V3 acceptance 通过。
- 文档不夸大为生产级沙箱、完整 SWE-Bench、公开榜单、分布式 rollout 或训练框架。

## 7. 最终验收定义

V3 最终验收必须同时满足：

1. Docker backend 端到端跑通 replay task、mock provider task、至少一个真实 repository-level task 和至少一个 SWE-Bench-like task。有真实 provider 凭证时，还必须跑通 credential-gated real provider Docker smoke；无凭证时只能结构化 skip。
2. Docker 硬前置通过机器检查：Linux 虚拟机内存至少 `16 GiB`、`evaluation.concurrency = 1`、effective SWE workers = 1、Docker server platform、server architecture、requested container platform、container architecture、cross architecture emulation facts、image platform、cleanup policy 和 cleanup status 都进入 facts。
3. 接入至少 3 个真实 repository-level task，其中至少 1 个来自公开仓库固定 commit 或预下载公开归档，并记录 remote URL、base commit、archive sha256 或 mirror sha256、source tree hash、dataset/source revision、本地 materialization ref 和 verifier evidence。3 个任务必须有独立 source facts、task hash 和 verifier evidence。
4. 第零阶段 3 个 accepted SWE-Bench-like task 被 RepoHarness 自己的 task adapter 读取，并在 RepoHarness 自己的 Docker backend、environment spec、verifier plan 和 final verifier 下生成 evidence。adapter 必须生成现有 `TaskDefinition` 兼容文件或等价 `LoadedTask` / `RunnableTask` 对象，并通过 `run_task` 或明确扩展后的等价入口进入 Agent Loop。
5. 至少一个真实 repository-level task 和至少一个 SWE-Bench-like task 进入 agent loop，并由 RepoHarness 自己完成 final patch freeze、verification workspace strict replay 和 final verifier。final verifier result、reward metadata、run outcome 和 hidden diagnostics 不得反馈给同一次或恢复后的 Agent Loop。
6. `v3_feasibility_input_manifest.json`、受版本控制的 `tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/` 输入、`docs/v3/evidence/swebench-lite-fixed/evaluator_only/` evidence、`source_checkout_facts.json`、`source_materialization_report.json`、`task_adapter_facts.json`、`real_repository_task_manifest.json`、`swebench_like_task_facts.json`、`swebench_like_environment_specs.json`、`swebench_like_verifier_plan.json`、`container_execution_facts/manifest.json`、`docker_phase_coverage_matrix.json`、`final_verifier_result.json` 和 `v3_acceptance_report.json` 均存在且通过 inspect。adapter input inspect 必须拒绝 gold patch prediction、`patch` 字段、raw `test_patch`、raw `FAIL_TO_PASS` / `PASS_TO_PASS`、official report 和 resolved status。
7. `transcript.jsonl`、`events.jsonl`、`artifacts.json`、ArtifactRef 可解析性、sha256、size_bytes、relative path、RunRecorder crash-readable 状态和 `run_config_facts.json` 均通过 `inspect-trajectory-store RUN_DIR --assert-readable`。completed 或 terminal accepted run 必须额外校验 `run_metadata.json`；interrupted / crashed run 必须额外校验结构化 interrupted / crash facts，并明确不要求最终 `run_metadata.json`。
8. `ToolContractSnapshot`、`PermissionPolicySnapshot`、`HookPolicySnapshot` 或 hook disabled facts、`MCPPolicySnapshot` 或 MCP disabled/frozen facts、scaffold/context/feedback/export policy snapshot refs 均通过 `inspect-tool-contract RUN_DIR --assert-frozen`，并进入 preference compare scope。
9. `docker_phase_coverage_matrix.json` 覆盖 source checkout、setup、agent tool、run_tests、final patch capture、verification workspace creation、verifier patch / test patch apply、model final patch apply、fail-to-pass test execution、pass-to-pass test execution 和 final verifier。
10. `experiment_resume_manifest.json`、`run_checkpoint_manifest.json` 和 `interrupted_run_diagnostics.json` 均存在，sha256 进入 acceptance bundle，并通过 `inspect-experiment-resume RUN_DIR --manifest RUN_DIR/experiment_resume_manifest.json --assert-resumable`。checkpoint 中的 `run_metadata_ref` 只能在最终 metadata 已存在时出现。
11. `context_compaction_report.json` 和 `long_rollout_diagnostics.json` 均存在，sha256 进入 acceptance bundle，并分别通过 `inspect-context-report RUN_DIR --report RUN_DIR/context_compaction_report.json --assert-consistent` 和 `inspect-long-rollout-diagnostics RUN_DIR --report RUN_DIR/long_rollout_diagnostics.json --assert-complete`。
12. `failure_diagnostics_core_report.json` 和 `failure_distribution_report.json` 均存在，sha256 进入 acceptance bundle，并通过 `inspect-reward-diagnostics RUN_DIR --core-report RUN_DIR/failure_diagnostics_core_report.json --distribution-report RUN_DIR/failure_distribution_report.json --assert-core-complete`。
13. `export_manifest.json`、`audit_report.json`、`audit_report.md`、format-specific export directories、skipped manifest、样本级 audit items、training eligibility、数据文件 sha256 和 `preference_pair_baseline_report.json` 均存在，sha256 进入 acceptance bundle，并通过 `inspect-v3-export-audit RUN_DIR --manifest RUN_DIR/export_manifest.json --audit-report RUN_DIR/audit_report.json --assert-clean`。
14. Export audit 证明 `V3ContaminationDenylist` 不进入 prompt、prepared messages、tool observation、模型可见 transcript、checkpoint、context compaction report 或正式训练 payload；同时 redaction audit 覆盖 evaluator-only events/artifacts、raw provider artifact、container facts、source facts 和 run metadata。
15. Export audit 证明每个正式训练样本的 `prepared_messages_ref`、`prepared_messages_sha256`、`model_input_hash`、`context_revision`、`content_replacement_state`、`tool_observation_ref`、`observation_source_event_ref` 和 `observation_matches_prepared_messages` 一致。新增真实仓库和 SWE-Bench-like Agent Loop run 必须进入 export 闭环，或被样本级 audit 标记为 `diagnostic_only`、`skipped` 或 `invalid`。
16. `RUN_SELECTION_MANIFEST` 和 `ACCEPTANCE_INPUTS` 是显式输入 manifest，列出 replay、mock provider、credential-gated real provider、真实 repository-level、SWE-Bench-like、trajectory store、tool contract snapshots、resume、context、long rollout、failure diagnostics、source materialization、export roots、V2 report 和 pre-acceptance documentation refs 的路径与 sha256。最终 `docs/v3/final-acceptance.md` 和 `docs/v3/walkthrough.md` 不作为 acceptance report 的输入，只在 report 生成后由 `acceptance_bundle_manifest.json` 绑定。
17. `ACCEPTANCE_DIR` 是 fresh directory，`build-v3-acceptance-report --input-manifest ACCEPTANCE_INPUTS` 拒绝复用旧目录；`inspect-v3-acceptance ACCEPTANCE_DIR/v3_acceptance_report.json --assert-complete` 校验所有 evidence 都来自 `ACCEPTANCE_INPUTS` 明确绑定的输入路径、typed run refs 和 command log。
18. 全量 `python -m pytest`、V2 regression 和 `inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete` 通过，除非外部 credential / platform gated 测试被结构化 skip。
19. V2 不变量继续通过机器检查，`acceptance_bundle_manifest.json` 引用 `runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json` 或等价 V2 regression report，并记录 sha256。
20. `acceptance_bundle_manifest.json` 绑定最终报告、`ACCEPTANCE_DIR/acceptance_command_log.jsonl`、输入 evidence refs、export roots、`docs/v3/final-acceptance.md`、`docs/v3/walkthrough.md`、文档摘要和 sha256，并通过 `inspect-acceptance-bundle ACCEPTANCE_DIR/acceptance_bundle_manifest.json --assert-immutable`。该 inspect 必须对 acceptance bundle 自身执行 redaction / denylist 审计，不能由阶段 11 export audit 代替。

## 8. 降风险路径

当前主线是 Green 路径，默认使用 3 个 accepted task。Yellow 路径不需要启用。

如果后续本机 Docker、依赖或数据漂移导致 accepted task 失效，必须按以下规则处理：

- 优先使用同一固定 dataset revision 中已经字段完整的候选任务，例如 `sympy__sympy-22005` 或 `sympy__sympy-15678`。
- 替代任务必须先跑第零阶段同等 gold patch 可实现性实验。
- 如果替代任务仍来自固定 revision SWE-Bench Lite 候选，必须记录 dataset revision、snapshot sha256、test patch hash、F2P/P2P、Docker logs 和 official harness report。
- Yellow 路径最多允许 1 个公开 issue-style 替代任务，并且至少保留 2 个固定 revision SWE-Bench Lite task。
- 若使用公开 issue-style 替代任务，不要求 SWE-Bench official harness report，但必须来自公开仓库固定 commit 或预下载公开归档，并提供 verifier patch、baseline failing evidence、gold patch passing evidence、fail-to-pass / pass-to-pass 或等价测试命令、Docker logs 和 RepoHarness 自有 verifier evidence。
- 如果少于 2 个固定 revision SWE-Bench Lite task 可用，必须进入 Red 状态，或者降低并重写 V3 SWE-Bench-like 最小完成定义；不能继续宣称同一 SWE-Bench-like 小子集目标已经完成。
- 本地 fixture 不能替代 SWE-Bench-like 小子集任务。

任何替代都必须更新 `docs/v3/review/swe-task-feasibility-results.md` 和 `docs/v3/scope-and-roadmap.md`，不能只改 implementation plan。

## 9. 非目标

V3 实施计划明确不做：

- 不实现生产级安全沙箱。
- 不实现完整 SWE-Bench Lite 或 Verified 榜单。
- 不声称结果可与公开榜单比较。
- 不实现大规模分布式 rollout 集群。
- 不实现新的强化学习算法或训练调度器。
- 不实现完整 MCP、插件市场、LSP 或后台多代理 swarm。
- 不训练 coding agent。
- 不把官方 SWE-Bench harness 包装成 RepoHarness 最终能力。

## 10. 实施完成后的推荐表述

如果 V3 按本文完成，可以写：

```text
RepoHarness V3 是一个面向软件工程智能体训练轨迹的轻量级 repository-level evaluation harness。它支持 Docker-based executable repository environment、真实 repository-level task、固定 revision SWE-Bench-like 小子集 task adapter、RepoHarness 自有 final verifier、可恢复多 rollout、上下文压缩诊断、core failure diagnostics 和可审计训练数据导出。
```

不能写：

```text
RepoHarness 复现了 SWE-Bench Lite 榜单。
RepoHarness 提供生产级安全沙箱。
RepoHarness 训练出了 coding agent。
RepoHarness 实现了工业级分布式 rollout service。
```
