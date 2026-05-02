# RepoHarness V3 Implementation Plan Review

## 0. 审查定位

本文记录 `docs/v3/implementation-plan.md` 的多维度只读审查结果。审查目标是确认第三版实施文档是否可以作为进入 V3 实现阶段的工程依据，而不是确认 V3 已经实现。

审查重点包括：

- 第零阶段 SWE 任务可实现性实验是否被正确引用。
- Docker、本机 Apple Silicon 环境、固定数据快照和污染边界是否写成硬前置。
- 真实 repository-level task 和 SWE-Bench-like 小子集是否都进入核心范围。
- 官方 SWE-Bench harness 是否只作为前置可实现性证明，而不是最终产品能力。
- 验收是否从“官方能跑”升级为“RepoHarness 自己能审计地跑”。
- 最终验收是否保留 V2 已建立的 export audit、metadata audit、training eligibility 和 preference hard gate 等不变量。

## 1. 第一轮审查发现

第一轮审查安排了四个视角：

1. 范围一致性与边界审查。
2. 工程可执行性和代码落点审查。
3. SWE-Bench-like 数据、Docker 本机环境和污染边界审查。
4. 验收审计和机器产物审查。

第一轮结论是：实施文档方向正确，但存在必须修订的问题。

### 1.1 已修复的 P1 问题

- 初稿遗漏了 `docs/v3/scope-and-roadmap.md` 中的真实 repository-level task 核心范围。修订后，实施文档明确要求至少接入 3 个真实 repository-level task，其中至少 1 个来自公开仓库固定 commit 或预下载公开归档，并要求至少 1 个真实 repository-level task 在 Docker backend 下端到端完成。
- 初稿的 SWE-Bench-like final verifier 口径不够可执行。修订后，文档新增 `SweBenchLikeEnvironmentSpec` 和 `SweBenchLikeVerifierPlan`，要求每个 accepted task 都有 setup command、base test command、fail-to-pass command、pass-to-pass command、selector 转换规则、timeout、parser policy、Docker image 或 build source。
- 初稿的 source materialization 来源策略不够硬。修订后，V3 核心路径只允许固定本地 source archive 或固定本地 mirror，正式 V3 run 禁止浮动网络 clone 和浮动默认分支。

### 1.2 已修复的 P2 问题

- 阶段 7 初稿允许 mock provider 或 replay-driven run 替代真实 Agent Loop。修订后，mock provider 和 replay-driven run 只能作为附加 smoke，不能替代真实 repository-level task 或 SWE-Bench-like task。
- 初稿没有把 `ExperimentConfig` 的 Docker backend 接入写入 schema 阶段。修订后，阶段 1 明确要求更新 `RunConfig`、`RuntimeConfig`、`ExperimentConfig` 和 run config fixture。
- 初稿的 `inspect-workspace-backend` 命令口径与现有 CLI 不一致。修订后，文档统一使用 `--status-file RUN_DIR/docker_backend_status.json --assert-docker-backend`，并要求保留兼容入口。
- 初稿的 resume 中断注入和不可恢复标准不够明确。修订后，文档要求覆盖 `baseline`、`agent_loop`、`final_verifier` 中断点之一，并定义 checkpoint 缺失、sha256 不匹配、run directory lock 冲突和 final verifier evidence 不完整等不可恢复条件。
- 初稿没有把 V2 不变量绑定到最终机器验收。修订后，最终验收要求 acceptance bundle 引用 V2 acceptance 或等价 V2 regression report，并重新检查 V2 export audit、diagnostic-only、preference compare scope、provider raw response 和凭证标记等边界。
- 初稿的 Docker phase matrix 缺少 patch apply 阶段。修订后，`docker_phase_coverage_matrix.json` 必须覆盖 verifier patch / test patch apply、model final patch apply、fail-to-pass test execution 和 pass-to-pass test execution。
- 初稿只要求输入快照 sha256 存在。修订后，`v3_feasibility_input_manifest.json` 必须重新计算并校验 level2 dataset、candidate manifest、selected manifest、gold patch predictions 和逐任务字段哈希。
- 初稿的 Docker 硬前置没有全部进入最终验收。修订后，最终验收要求检查内存至少 16 GiB、`evaluation.concurrency = 1`、effective SWE workers = 1、server/container architecture、cross architecture emulation facts、image platform、cleanup policy 和 cleanup status。
- 初稿的 Yellow 替代路径过宽。修订后，Yellow 最多允许 1 个公开 issue-style 替代任务，并且至少保留 2 个固定 revision SWE-Bench Lite task。

## 2. 第二轮复审结论

修订后，四个审查视角均给出 `PASS`。

### 2.1 范围一致性与边界审查

结论：`PASS`。

确认结果：

- 已补齐真实 repository-level task 核心范围。
- 已要求至少 3 个真实 repository-level task，且至少 1 个来自公开仓库固定 commit 或预下载公开归档。
- 已要求至少 1 个真实 repository-level task 和至少 1 个 SWE-Bench-like task 在 Docker backend 下端到端完成。
- 阶段 7 已明确 mock provider 或 replay-driven run 只能作为附加 smoke。
- 已补齐数据集 split：`test`。

### 2.2 工程可执行性和代码落点审查

结论：`PASS`。

确认结果：

- `SweBenchLikeEnvironmentSpec` 和 `SweBenchLikeVerifierPlan` 已经覆盖 setup command、base test command、fail-to-pass command、pass-to-pass command、selector 转换规则、timeout、parser policy 和 Docker image / build source。
- source materialization 已明确只允许固定本地 source archive 或固定本地 mirror，正式 V3 run 禁止浮动网络 clone。
- `RunConfig`、`RuntimeConfig` 和 `ExperimentConfig` 的 Docker backend 接入已写入阶段 1。
- `inspect-workspace-backend` 已统一为 `--status-file` 入口，并要求保留兼容测试。
- resume 已补充固定中断注入点和不可恢复标准。
- 最终验收已继承真实 repository-level task 范围。

### 2.3 SWE-Bench-like 数据、Docker 环境和污染边界审查

结论：`PASS`。

确认结果：

- `v3_feasibility_input_manifest.json` 已要求重新计算并校验 `level2_dataset.jsonl`、candidate manifest、selected manifest、gold patch predictions 和逐任务字段哈希。
- Docker 内存、`evaluation.concurrency = 1`、effective SWE workers = 1、server/container architecture、cross architecture emulation 和 cleanup facts 已进入阶段验收和最终验收。
- Yellow 路径已限制为最多 1 个公开 issue-style 替代任务，并且至少保留 2 个固定 revision SWE-Bench Lite task。
- `patch`、`test_patch`、`FAIL_TO_PASS`、`PASS_TO_PASS`、官方 report 和 resolved status 的模型可见性边界保持清晰。

### 2.4 验收审计和机器产物审查

结论：`PASS`。

确认结果：

- V2 不变量已绑定到最终机器验收和 `acceptance_bundle_manifest.json`。
- `docker_phase_coverage_matrix.json` 已加入 verifier patch / test patch apply、model final patch apply、fail-to-pass execution 和 pass-to-pass execution。
- source materialization 已明确禁止浮动网络 clone，并要求固定本地 archive / mirror、provenance、sha256 和 inspect 失败条件。
- `container_execution_facts/manifest.json` 与逐命令 facts 文件命名已经清晰。

## 3. 追加审查和最终修订

第二轮通过后，外部复查又提出一组会影响可复现实施和最终验收可信度的问题。实施文档随后继续修订，并再次交给四个审查视角做短复审。

### 3.1 已修复的新增 P1 问题

- 固定输入不再默认依赖未跟踪 `runs/` 目录。文档现在要求阶段 0 通过 `--feasibility-root` 把最小 JSONL、manifest 和 sha256 文件迁入 `tests/fixtures/v3/swebench_lite_fixed/` 和 `docs/v3/evidence/swebench-lite-fixed/`，后续阶段默认读取受版本控制的固定输入。
- SWE-Bench-like adapter 必须生成现有 `TaskDefinition` 兼容 YAML 或等价 `LoadedTask` / `RunnableTask` 对象，并通过 `run_task` 或明确扩展后的等价入口进入常规 Agent Loop。
- 所有 inspect 命令都要求显式输入路径，不能读取当前目录、默认 latest run 或环境变量。
- 最终验收新增 `build-v3-acceptance-inputs` 和 `ACCEPTANCE_INPUTS` 输入 manifest，`build-v3-acceptance-report` 必须拒绝复用旧 `ACCEPTANCE_DIR`。
- 最终验收逐项列出 `experiment_resume_manifest.json`、`context_compaction_report.json`、`long_rollout_diagnostics.json`、`failure_diagnostics_core_report.json`、`failure_distribution_report.json`、`export_manifest.json`、`audit_report.json`、`preference_pair_baseline_report.json` 和 `acceptance_bundle_manifest.json`。
- `V3ContaminationDenylist` 已统一覆盖 prompt、prepared messages、tool observation、transcript、checkpoint、context compaction report、SFT / RL / preference export、audit 输入和 acceptance bundle 输入。
- Agent Loop 与 final verifier、reward、run outcome、hidden diagnostics 的单向边界已写成硬性不变量，resume 不能把这些 evaluator 侧事实反馈给同一 agent 继续尝试。

### 3.2 已修复的新增 P2 问题

- `WorkspaceAdapter` 实际调用面已经写成现有方法名，包括 `create_source_checkout`、`create_setup_workspace`、`capture_dependency_state`、`create_agent_workspace` 和 `create_verification_workspace`；如果新增别名，必须同步迁移调用点并保留兼容测试。
- `ContextBuilder` 在 Docker mode 下不能使用裸 `Path.read_text` 读取仓库文件，必须通过 workspace facade 或 backend 生成的 repository context artifact。
- 有真实 provider 凭证时，credential-gated real provider Docker smoke 必须进入 Docker backend 和 export audit；无凭证时只能结构化 skip。
- SWE-Bench-like verifier 必须记录 fail-to-pass baseline failing evidence、pass-to-pass baseline evidence、gold patch passing evidence 和模型 final patch 独立 verifier result。
- 真实 repository-level task 不能用 1 个公开任务加 2 个重复本地 fixture 通过；3 个任务必须有独立 source facts、task hash 和 verifier evidence。
- `failure_distribution_report.json` 已进入阶段 10 和最终验收。
- 并发配置优先复用现有 `evaluation.concurrency`，若新增 `swebench_like.max_workers`，必须定义它和 `evaluation.concurrency` 的关系。
- V2 `docker_stage_status.json`、`workspace-backend-status`、`repo_harness_docker_stage_status_v2_v0` schema 和旧 `--status-file` 入口必须保持兼容。
- `sympy__sympy-24909` 已被列为裸函数名 selector 转换的单元测试和集成测试样例。
- 负例测试清单已覆盖 summary 篡改、evidence ref 删除、sha256 修改、旧 `RUN_DIR` 替换、官方 harness report 注入、prompt/checkpoint/context compaction 污染和旧 acceptance directory 复用。

### 3.3 最终短复审

四个审查视角均给出 `PASS`：

- 范围一致性和边界审查：`PASS`。
- 工程可执行性和代码落点审查：`PASS`。
- SWE-Bench-like 数据、Docker 环境和污染边界审查：`PASS`。
- 验收审计和机器产物审查：`PASS`。

该轮短复审当时没有剩余 P1、P2 或 P3 问题；后续复查又提出的新增问题记录在下面的 3.4 和 3.5。

### 3.4 Yellow 路径 P3 文案修订

后续复查指出 Yellow 替代任务的 official harness report 口径需要拆分。实施文档已修订：

- 固定 revision SWE-Bench Lite 候选替代任务必须记录 official harness report。
- 公开 issue-style 替代任务不要求 SWE-Bench official harness report，但必须提供固定公开来源、baseline failing evidence、gold patch passing evidence、fail-to-pass / pass-to-pass 或等价测试命令、Docker logs 和 RepoHarness 自有 verifier evidence。

该修订不改变 Green 主线，也不改变阶段 0 的进入条件，只是避免后续执行 agent 把 SWE-Bench 官方 harness report 错误套用到公开 issue-style 替代任务上。

### 3.5 轨迹、工具契约和导出绑定修订

后续复查又指出一组会影响“可执行、可审计、可导出训练轨迹”核心目标的问题。实施文档已继续修订：

- 阶段 0 输入拆成 adapter-visible task input 和 evaluator-only evidence。`tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/` 不得出现 `gold_patch_predictions.jsonl`、数据集 `patch` 字段、raw `test_patch`、raw `FAIL_TO_PASS` / `PASS_TO_PASS`、official harness report 或 resolved status；这些只能作为 evaluator-only evidence refs 存在于 `docs/v3/evidence/swebench-lite-fixed/evaluator_only/`。
- trajectory store 成为硬验收：`transcript.jsonl`、`events.jsonl`、`artifacts.json`、ArtifactRef 可解析性、sha256、size_bytes、`run_config_facts.json` 和 RunRecorder 崩溃后可读性都进入 `inspect-trajectory-store` 和最终验收。completed 或 terminal accepted run 必须有 `run_metadata.json`；interrupted / crashed run 必须有结构化 interrupted / crash facts，但不要求最终 `run_metadata.json`。
- 工具契约和策略快照成为硬验收：`ToolContractSnapshot`、`PermissionPolicySnapshot`、hook disabled facts、MCP disabled/frozen facts、scaffold/context/feedback/export policy snapshot refs 进入 run facts、preference compare scope 和 acceptance bundle。
- export observation 与历史 PreparedMessages 建立硬绑定：`prepared_messages_ref`、`prepared_messages_sha256`、`model_input_hash`、`context_revision`、`content_replacement_state`、`tool_observation_ref`、`observation_source_event_ref` 和 `observation_matches_prepared_messages` 成为 export audit 门禁。
- 当前 V2 代码迁移门被写入阶段 1/2：Docker 不能继续硬拒绝，adapter 必须进入 `run_task` 或明确扩展后的等价入口，SWE-Bench-like final-only 必须拒绝 `oracle_hidden_feedback`，`ContextBuilder` 不得泄漏 host absolute path 或 hidden verifier command。
- V2 export 契约被显式继承：format-specific export directory、样本级 audit items、training eligibility、skipped manifest、数据文件 sha256、严格 `CompareScope` 默认值和 run artifact 级 redaction audit 都进入阶段 11 和最终验收。
- `long_rollout_diagnostics.json` 增加独立 inspect；全量 `python -m pytest`、V2 regression、`run_config_facts.json` 和 `run_metadata.json` 也进入最终验收门禁。
- `RunCheckpoint.run_metadata_ref` 只能在最终 metadata 已存在的 checkpoint 中出现，新增真实仓库和 SWE-Bench-like Agent Loop run 必须进入 export 闭环，或者被样本级 audit 标记为不可训练。

### 3.6 运行状态、阶段时序和命令类型修订

后续复查指出三处文档一致性问题。实施文档已继续修订：

- `run_metadata.json` 的要求按运行状态拆分：completed 或 terminal accepted run 必须生成最终 `run_metadata.json`；interrupted / crashed run 必须保留 `run_config_facts.json`、transcript、events、artifacts 和结构化 interrupted / crash facts，但不要求最终 `run_metadata.json`。
- 阶段 11 只审计 run artifacts、exports 和当时已经存在的 facts，不再要求审计阶段 12/13 才生成的 acceptance bundle。acceptance bundle 自身的 redaction / denylist 审计改由 `inspect-acceptance-bundle` 在阶段 12/13 执行。
- 阶段 0 明确拆分写型冻结命令和只读检查命令：`prepare-v3-swebench-fixture` 负责生成 adapter-visible input 和 evaluator-only evidence，`inspect-v3-swebench-fixture --assert-frozen` 只负责读取、校验和拒绝污染布局。

### 3.7 最终验收输入和 command log 修订

工程可执行性复审又指出最终验收输入选择、文档引用顺序和 command log 机器产物存在可收紧空间。实施文档已继续修订：

- `RUN_SELECTION_MANIFEST` 被写成显式 typed run refs，禁止 `build-v3-acceptance-inputs` 从 experiment directory 隐式扫描或猜测 latest run。每个验收类别必须有 role、path、sha256、run id、run state、expected evidence types 和 structured skip reason。
- `ACCEPTANCE_INPUTS` 改为引用 `RUN_SELECTION_MANIFEST`、export roots、V2 report 和 pre-acceptance documentation refs。`docs/v3/final-acceptance.md` 与 `docs/v3/walkthrough.md` 被明确为 post-acceptance 文档，不作为 acceptance report 输入，而是在 report 生成后由 `acceptance_bundle_manifest.json` 绑定。
- 增加 `CommandLogEntry` schema 要求，阶段运行生成 `RUN_DIR/command_log.jsonl` 或 `EXPERIMENT_DIR/command_log.jsonl`，最终验收生成 `ACCEPTANCE_DIR/acceptance_command_log.jsonl`，并由 `inspect-v3-acceptance` 和 `inspect-acceptance-bundle` 检查完整性、sha256 和输入 manifest 一致性。
- 里程碑摘要中的 inspect 命令补成带显式 report、manifest 或 status-file 的完整形式。
- `source_materialization_report.json` 已进入最终机器产物、`ACCEPTANCE_INPUTS` 和 acceptance bundle 要求。
- 负例测试补充 `ACCEPTANCE_INPUTS` 缺少必需类别、报告引用外部 evidence、documentation ref 在 bundle 后变化、command log 与输入 manifest 不一致、credential-gated real provider skip 被伪装成 accepted run 等场景。

## 4. 最终审查结论

`docs/v3/implementation-plan.md` 已通过前序四个维度的复审，并已继续吸收后续复查提出的 P1、P2 和 P3 文档修订点。当前文档可以进入 V3 阶段 0/1 的准备，但阶段 0 仍必须先冻结 adapter-visible 输入和 evaluator-only evidence，不能跳过阶段 0 直接实现后续 Docker backend、task adapter 或 Agent Loop 代码。

该实施文档可以作为 V3 实现阶段的工程输入，但它本身不代表 V3 已经完成。进入实现阶段后，每个阶段仍需要独立 implementation log、独立 review、测试命令、机器产物和 inspect 证据。
