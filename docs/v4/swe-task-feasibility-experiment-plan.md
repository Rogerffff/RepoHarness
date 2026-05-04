# RepoHarness V4 SWE / PR Task Feasibility Experiment Plan

## 0. 文档定位

本文定义进入 RepoHarness V4 implementation plan 前建议完成的任务预选、Docker 可运行性、patch 可行性和冻结准备实验。它是 V4 scope 和 V4 implementation plan 之间的前置设计文档，不实现 V4 代码，不修改 V3 acceptance 产物，也不把任何候选任务直接宣称为最终 accepted task。

V4 scope 已经把最小任务目标写成：

- 至少 8 个 accepted / auditable task definitions。
- 其中至少 4 个必须是通过 V4 PR / issue 构造流程新增的任务。
- diagnostic-only、quarantined 和 rejected 不计入 accepted / auditable 最低数量。

因此，V4 implementation plan 编写前有必要先设计并执行一个任务可行性实验。否则 implementation plan 会把最大不确定性留到实现中后期：任务镜像是否能在本机运行、依赖是否可安装、baseline verifier 是否稳定、patch 是否可应用、失败是否是任务问题而不是 agent 能力问题。

本实验回答的问题是：

> 在当前本机 Docker 资源较充足的条件下，V4 准备使用的较复杂、更多样的 SWE-Bench-like / PR / issue 任务，是否可以被固定、构建、运行 baseline verifier、隔离 evaluator-only evidence，并形成可审计的任务冻结候选？

## 1. 当前资源假设

本设计采用以下用户提供的本机资源作为计划输入：

- Apple M5 Pro。
- 64GB 内存。
- Docker Desktop 已分配约 30GB 内存。
- 本机硬件资源足以尝试比 V3 更复杂的任务和更多样的技术栈。

这些资源只说明“可以提高任务复杂度和候选池规模”，不等价于任务一定可接受。V4 仍然必须通过实际 Docker build、依赖安装、baseline verifier、flaky 检测和 source materialization repeat check 来判定任务状态。

## 2. 为什么 V4 前需要提前确定任务候选

V4 的任务集比 V3 更关键，原因有五点：

1. P0-2 已经把“至少 8 个 accepted / auditable task definitions，其中至少 4 个 V4 新构造任务”写成机器可检查门槛。任务不可用会直接阻塞 V4 acceptance。
2. P0-1 的 rollout queue、run leasing、retry policy、resource usage facts 都依赖稳定任务集；如果任务本身不稳定，rollout 编排结果会被环境问题污染。
3. P0-3 的 trajectory packing、failure dataset、preference pair trainability 和 patch quality audit 需要成功、失败、部分成功样本都有可比较基础。
4. V4 希望任务复杂度高于 V3，并覆盖更多技术栈；这会显著增加 Docker image、依赖缓存、测试时间、平台兼容和 flaky 风险。
5. evaluator-only evidence、official harness report、gold patch、hidden selector、credential marker 等边界必须从任务构造阶段就建立，不能等导出阶段再补救。

结论：V4 implementation plan 前应至少完成任务预选设计，并建议完成一轮独立的 feasibility run。implementation plan 可以把 feasibility run 的产物作为 P0 task source freeze / construction preflight 的输入。

## 3. 实验原则

本实验必须遵守以下原则：

- 先验证任务和环境，不评测 agent 能力。
- 先固定 source archive、fixed revision、任务 manifest、baseline verifier 和 evaluator-only evidence 分区，再进入批量 rollout。
- 不把公开 SWE-Bench Lite / SWE-Bench Verified 榜单复现作为目标。
- 不默认联网构造正式任务；联网读取或下载只允许发生在 feasibility 阶段，并且必须转化为固定 source archive 和可审计 manifest。
- 不使用浮动默认分支作为正式任务来源。
- 不把 gold patch、official harness report、official report、hidden selector、Authorization marker、provider credential marker、raw provider response 放进模型可见上下文或正式训练 payload。
- 对 public SWE-Bench-like 任务，可以使用官方 gold patch 或官方 evaluator evidence 做 evaluator-only feasibility；这些证据不能进入 adapter-visible task input。
- 对 V4 新构造 PR / issue 任务，可以使用人工 patch 或基线修复 patch 做 evaluator-only feasibility；这些证据同样不能进入训练 target。
- 所有失败必须结构化分类，不能只写“失败”。
- 质量优先于数量。候选任务失败时应降级为 diagnostic-only、quarantined 或 rejected，而不是强行计入 accepted / auditable。

### 3.1 执行资源边界

V4 的本机资源比 V3 更充足，但 feasibility run 仍必须默认保守执行，避免把任务探针变成开放式批量实验。

默认执行边界：

- `max_workers = 1`。除非单个阶段已经稳定通过，否则不并发执行 verifier 或 official harness。
- 最大并发 Docker image build 数为 `1`。镜像预热可以排队，不并发抢占磁盘和内存。
- 单候选 image build 默认 timeout 为 `45` 分钟；超过后标记为 `image_build_timeout`，不能直接重试到耗尽资源。
- 单候选 dependency install 默认 timeout 为 `30` 分钟；超过后标记为 `dependency_timeout`。
- 单次 baseline verifier 默认 timeout 为 `20` 分钟；public SWE-Bench-like official harness 可以继承 V3 的 `1800` 秒上限，但必须在 manifest 中显式记录。
- 单次 post-patch verifier 默认 timeout 为 `20` 分钟；超过后标记为 `post_patch_timeout`。
- Level 2 到 Level 4 每个候选最多 `2` 次尝试：一次 primary attempt，一次 retry attempt。retry 必须写明 `retry_reason`，不能无界重试。
- Docker disk 可用空间低于 `120GB` 时不启动新的 image build；低于 `80GB` 时暂停实验并记录 `docker_disk_below_minimum`。
- 单候选镜像预算默认不超过 `15GB`；超过 `20GB` 的候选必须降级为 `tier_3_high_risk` 或 `quarantined`，除非有明确人工例外记录。
- 允许清理本次 run 目录下创建的临时容器、临时 image tag、build cache label 和临时 worktree。
- 禁止自动删除 V3 acceptance 产物、V3 source archives、用户已有工作区文件、未标记为本次 feasibility run 创建的 Docker image 或 volume。

默认 run directory layout：

```text
runs/v4-swe-task-feasibility-YYYYMMDDTHHMMSSZ/
  setup/
  inventory/
  docker/
  baseline/
  patch/
  freeze/
  logs/
  manifests/
```

所有机器产物必须记录自身 `sha256`，或由上层 manifest 记录 `path`、`kind`、`sha256`、`size_bytes` 和生成命令。

## 4. 非目标

本实验明确不做：

- 不跑完整 SWE-Bench Lite 或 SWE-Bench Verified。
- 不声称本机结果可与公开 leaderboard 比较。
- 不训练模型。
- 不调优 prompt。
- 不实现 V4 rollout queue、export audit 或 task adapter 代码。
- 不建设大规模 PR mining。
- 不把 Docker backend 宣称为生产级安全沙箱。
- 不把非 Python 技术栈任务强行纳入 P0，如果它们不能在本机稳定运行。

## 5. 候选任务组成建议

V4 不应只复用 V3 的 pytest / sympy 轻量任务。建议采用“两条轨道”的候选池：

### 5.1 轨道 A：public SWE-Bench-like Python 任务

用途：

- 继承 V3 的 SWE-Bench-like 能力。
- 使用公开仓库、固定 revision、官方或等价 verifier。
- 为 V4 提供复杂 Python 项目任务。

建议优先覆盖的项目家族：

- 测试框架或开发工具：pytest、pylint、sphinx。
- Web 框架：django。
- 科学计算或数据栈：sympy、scikit-learn、matplotlib、astropy、seaborn。

候选选择规则：

- V3 已 accepted 的任务可以作为回归锚点，但不能替代 V4 新构造任务。
- V4 新 public SWE-Bench-like 候选应优先选择比 V3 更复杂的任务，例如测试面更宽、patch 涉及多个语义区域、依赖更重或仓库规模更大。
- 不在未完成 dataset scan 和 Docker probe 前硬写最终 instance id。最终 instance id 必须来自 `candidate_task_inventory.jsonl` 和 `v4_task_selection_manifest.json`。

### 5.2 轨道 B：V4 人工可审计 PR / issue 任务

用途：

- 满足至少 4 个 V4 新构造任务的硬目标。
- 增加技术栈多样性，避免 V4 只停留在 Python SWE-Bench-like 小子集。
- 建立 RepoHarness 自有 PR / issue task construction 流程。

建议优先覆盖的技术栈：

- Python 中大型项目任务：复杂 pytest、django、sphinx、scientific Python。
- TypeScript / JavaScript：Node.js 包、CLI、解析器、工具库，使用 `npm test`、`pnpm test`、`vitest` 或 `jest`。
- Rust：小到中型 crate，使用 `cargo test`。
- Go：小到中型 module，使用 `go test ./...`。

非 Python 技术栈不应直接成为硬性 P0 数量要求。建议先作为 V4 feasibility 候选，如果 Docker build、依赖缓存、baseline verifier 和 patch probe 都稳定，再纳入 accepted / auditable task definitions。

### 5.3 轨道 B 的 auditable 定义和计数规则

V4 PR / issue 构造任务只有满足以下条件，才可以计入“至少 4 个 V4 新构造任务”：

- 有可固定的 source provenance：至少包含 repository URL、fixed revision、source archive candidate ref 和 source archive sha256 或 source tree hash。
- 有可审计的问题来源：issue URL、pull request URL、修复 commit URL、release note / changelog entry，或等价的人工审查记录。只靠一句人工描述构造的任务不能计入 V4 PR / issue 新构造任务。
- 有 patch provenance：上游 PR patch、修复 commit patch、人工基线修复 patch或内部 patch 都必须记录来源、hash、作者/构造者、应用命令和验证结果。
- 有测试证据：baseline verifier、post-patch verifier、测试命令、日志引用和 expected failing / passing behavior。
- issue / pull request / commit 与 patch 的对应关系必须可复查。如果没有公开 issue，必须有修复 commit、测试变更或人工 review note 说明任务意图。
- adapter-visible task input 只能包含公开问题描述、复现症状、允许的 repository context 和执行说明；不能包含上游解法、patch diff、hidden selector、official report 或 evaluator-only evidence。
- evaluator-only evidence 必须单独存放，并通过 manifest 绑定。

V3 accepted SWE-Bench-like 任务可以作为 regression anchors；公开 SWE-Bench-like 新任务可以作为 V4 扩展任务；但它们不能替代“至少 4 个 V4 PR / issue 构造流程新增任务”的计数。

### 5.4 初始候选家族和硬排除规则

建议初始候选家族：

- Public SWE-Bench-like Python：django、sphinx、astropy、scikit-learn、matplotlib、pytest、sympy。
- V4 PR / issue Python：中型 Python CLI、解析器、文档构建工具、测试工具、科学计算工具。
- V4 PR / issue TypeScript / JavaScript：小到中型 CLI、parser、formatter、lint rule、library utility，优先有 deterministic unit tests。
- V4 PR / issue Rust：单 crate 或 workspace 较小的 crate，优先 `cargo test` 可在 20 分钟内完成。
- V4 PR / issue Go：单 module 或小型 multi-package module，优先 `go test ./...` 可在 20 分钟内完成。

硬排除规则：

- 需要 GPU、TPU、专用硬件、macOS GUI、Windows GUI 或浏览器端到端环境的任务。
- 需要云凭据、私有 API key、付费外部服务、数据库服务集群、消息队列集群或长期后台服务的任务。
- 测试必须联网才能通过，或默认会下载超大数据集、模型权重、大二进制资产的任务。
- license / provenance 不能固定或不适合训练数据审计的任务。
- 无法固定 source revision、无法生成 source archive、无法重复 materialization 的任务。
- image build 预计超过 `60` 分钟、镜像预计超过 `20GB`、单次 verifier 预计超过 `30` 分钟的任务。
- 已知长期 flaky、需要人工交互、需要本机绝对路径、依赖不可缓存或依赖不支持本机 Docker 的任务。

## 6. 复杂度目标

V4 任务复杂度应高于 V3，但不能高到不可稳定验证。建议定义 `complexity_tier`：

- `tier_0_regression_anchor`：V3 已 accepted 或等价轻量任务，只作为回归锚点。
- `tier_1_moderate`：单仓库、依赖可缓存、测试范围有限，预期 patch 为 1 到 2 个文件。
- `tier_2_complex`：中大型仓库、依赖较重、测试范围较宽，预期 patch 可能涉及 2 到 4 个文件或多个语义点。
- `tier_3_high_risk`：依赖重、构建慢、跨语言、测试耗时长或容易 flaky。只能先作为 diagnostic-only candidate，不能直接计入 V4 最小 accepted 数量。

建议分档阈值：

- `tier_1_moderate`：image build <= `20` 分钟，dependency install <= `15` 分钟，baseline verifier <= `10` 分钟，post-patch verifier <= `10` 分钟，镜像 <= `8GB`，patch <= `2` 个文件且 <= `100` 行非测试改动。
- `tier_2_complex`：image build <= `45` 分钟，dependency install <= `30` 分钟，baseline verifier <= `20` 分钟，post-patch verifier <= `20` 分钟，镜像 <= `15GB`，patch <= `4` 个文件且 <= `250` 行非测试改动。
- `tier_3_high_risk`：超过上述任一 `tier_2_complex` 阈值，或需要外部服务、跨架构 native dependency、超大数据下载、复杂服务编排、长期 flaky 重跑，默认只能 diagnostic-only 或 quarantined。

Flaky 判定默认使用 `3` 次重复 verifier probe：三次结果一致才算 stable；若出现 1 次非预期失败，标记 `flaky_suspected` 并追加到最多 `5` 次。5 次中仍有非预期失败则不能 accepted / auditable，只能 quarantined 或 diagnostic-only。

非 Python 多样性按 package ecosystem 和 primary verifier command 计算。也就是说，`npm test` / `pnpm test` / `vitest` / `jest` 计入 JavaScript / TypeScript，`cargo test` 计入 Rust，`go test` 计入 Go。若仓库主语言和修改文件语言不同，以 primary verifier command 为主，并在 manifest 中记录 `mixed_language=true`。

建议 V4 feasibility 目标：

- 至少扫描 30 到 45 个候选任务。
- 至少完整 probe 18 到 24 个候选任务。
- 至少形成 8 个 accepted / auditable task definitions 的候选清单。
- 至少 4 个 accepted / auditable 候选来自 V4 PR / issue 构造流程。
- accepted 候选中至少包含 4 个不同项目家族。
- 如果非 Python 技术栈稳定通过，优先纳入 1 到 2 个作为 V4 多样性样本；如果不稳定，保留为 diagnostic-only，不阻塞 P0。

## 7. 实验分层

### Level 0：本机 Docker 和资源确认

目标：确认本机资源和 Docker 配置可以支持 V4 任务 feasibility。

建议记录：

- `host_hardware_profile.json`
- `docker_environment.json`
- `docker_system_df_before.txt`
- `docker_buildkit_status.txt`
- `platform_emulation_probe.txt`

建议检查项：

- Docker server platform。
- Docker Desktop memory limit，预期约 30GB。
- Docker CPU limit。
- Docker disk image limit 和剩余空间。
- `linux/amd64` 仿真是否可运行。
- native `linux/arm64` 是否可运行。
- BuildKit 是否启用。

通过标准：

- Docker 可用。
- Docker memory >= 24GB，理想为 30GB。
- 宿主机磁盘空间足以存放多项目镜像和 dependency cache。
- `linux/amd64` 和 native `linux/arm64` 基础容器至少能完成 `uname -m` probe。

### Level 1：候选来源和任务 inventory scan

目标：不运行 agent，只扫描候选来源，形成可审查候选池。

建议产物：

- `candidate_source_registry.json`
- `candidate_task_inventory.jsonl`
- `candidate_metadata_schema.json`
- `candidate_complexity_score_report.json`
- `candidate_visibility_risk_report.json`

每个候选任务至少记录：

- `candidate_id`
- `source_track`: `public_swebench_like` 或 `auditable_pr_issue`
- `repo`
- `repository_url`
- `license`
- `source_provenance`
- `issue_url`
- `pull_request_url`
- `fix_commit_url`
- `task_statement_sha256`
- `fixed_revision`
- `source_archive_candidate_ref`
- `source_archive_sha256`
- `source_tree_hash`
- `task_statement_source`
- `technology_stack`
- `repository_primary_language`
- `patch_primary_language`
- `mixed_language`
- `test_command_family`
- `expected_verifier_type`
- `expected_verifier_command`
- `max_test_budget_sec`
- `estimated_dependency_weight`
- `estimated_dependency_download_bytes`
- `estimated_test_runtime_class`
- `estimated_image_size_class`
- `patch_file_count`
- `patch_line_count`
- `requires_network_at_test_time`
- `requires_external_service`
- `requires_linux_amd64_emulation`
- `large_binary_or_model_data_risk`
- `local_docker_fit`
- `complexity_tier`
- `visibility_risk_flags`
- `evaluator_only_evidence_available`
- `adapter_visible_input_available`
- `adapter_visible_input_hash`
- `evaluator_only_evidence_manifest_hash`
- `candidate_status`

候选状态：

- `inventory_only`
- `ready_for_image_probe`
- `visibility_blocked`
- `source_blocked`
- `out_of_scope`

### Level 2：Docker image prewarm 和 dependency probe

目标：提前安装或构建候选任务需要的镜像和依赖，判断本机是否能稳定运行任务环境。

建议产物：

- `docker_image_prewarm_plan.json`
- `docker_image_prewarm_report.json`
- `dependency_cache_report.json`
- `platform_compatibility_report.json`
- `image_size_report.json`
- `build_failure_report.jsonl`

每个候选至少记录：

- `candidate_id`
- `requested_platform`
- `actual_container_arch`
- `base_image`
- `image_tag`
- `image_digest`
- `build_duration_sec`
- `image_size_bytes`
- `dependency_cache_key`
- `dependency_install_exit_code`
- `dependency_install_log_ref`
- `dependency_install_duration_sec`
- `dependency_download_bytes`
- `source_archive_sha256`
- `source_tree_hash`
- `manifest_sha256`
- `attempt`
- `retry_reason`
- `exit_code`
- `stdout_log_ref`
- `stderr_log_ref`
- `actual_report_paths`
- `platform_failure_category`
- `prewarm_status`

通过标准：

- 候选可以构建或拉取固定镜像。
- 依赖安装成功，或失败原因结构化可诊断。
- 镜像大小、构建时间和缓存策略可接受。
- 对失败候选明确标记 `dependency_blocked`、`platform_blocked`、`timeout_blocked` 或 `resource_blocked`。

### Level 3：baseline verifier 和 flaky probe

目标：确认任务的 baseline 状态、预期失败、通过用例、环境健康和重复运行稳定性。

建议产物：

- `baseline_verifier_probe_report.json`
- `flaky_probe_report.json`
- `environment_stability_score_report.json`
- `source_materialization_repeat_report.json`

每个候选至少记录：

- `candidate_id`
- `source_archive_sha256`
- `source_tree_hash`
- `verifier_command`
- `verifier_definition_hash`
- `timeout_sec`
- `attempt`
- `retry_reason`
- `exit_code`
- `stdout_log_ref`
- `stderr_log_ref`
- `actual_report_paths`
- `adapter_visible_input_hash`
- `evaluator_only_evidence_manifest_hash`
- `baseline_expected_failure_observed`
- `pass_to_pass_regression`
- `flaky_probe_attempt_count`
- `flaky_probe_pass_count`

通过标准：

- bug-fix task 的 `fail_to_pass` 初始失败被视为有效任务信号，不能误判为 invalid。
- `pass_to_pass`、setup、依赖安装、环境健康检查和 broad regression failure 用于判断 unstable、quarantined 或 rejected。
- 同一 source archive 和 fixed revision 重复 materialization 的 hash 一致。
- 重复 verifier 运行结果稳定，或者 flaky 原因被结构化记录。

### Level 4：patch feasibility probe

目标：确认任务确实可 patch，而不是只有失败测试。该阶段不评测 agent。

对 public SWE-Bench-like 任务：

- 可以使用官方 gold patch 作为 evaluator-only feasibility probe。
- official harness report、official resolved status、gold patch、test_patch、FAIL_TO_PASS / PASS_TO_PASS 原始 selector 必须保留在 evaluator-only 分区。

对 V4 PR / issue 任务：

- 可以使用人工 patch、上游 PR patch 或内部基线修复 patch 做 evaluator-only feasibility probe。
- patch 来源、hash、应用命令、验证结果必须记录。

建议产物：

- `patch_feasibility_report.json`
- `evaluator_only_patch_probe_manifest.json`
- `patch_apply_log.jsonl`
- `post_patch_verifier_report.json`

每个候选至少记录：

- `candidate_id`
- `patch_provenance`
- `patch_sha256`
- `patch_apply_command`
- `patch_apply_exit_code`
- `patch_apply_log_ref`
- `post_patch_verifier_command`
- `post_patch_verifier_definition_hash`
- `timeout_sec`
- `attempt`
- `retry_reason`
- `exit_code`
- `stdout_log_ref`
- `stderr_log_ref`
- `actual_report_paths`
- `adapter_visible_input_hash`
- `evaluator_only_evidence_manifest_hash`

通过标准：

- patch 可以干净应用到 fixed revision。
- post-patch verifier 达到预期。
- patch evidence 不进入 adapter-visible task input。

冲突原因可诊断只表示失败原因可审计，不能等同于 patch feasibility 通过。若 patch 不能干净应用到 fixed revision，即使冲突原因清楚，也只能进入 `quarantined`、`diagnostic-only` 或 `rejected`，不能计入 accepted / auditable。

### Level 5：任务冻结 readiness decision

目标：从候选池中形成 V4 implementation plan 可引用的任务冻结候选。

建议产物：

- `v4_task_selection_manifest.json`
- `v4_task_freeze_readiness_report.json`
- `accepted_auditable_task_candidates.jsonl`
- `diagnostic_only_task_candidates.jsonl`
- `quarantined_task_candidates.jsonl`
- `rejected_task_candidates.jsonl`
- `evaluator_only_evidence_partition_report.json`

accepted / auditable 候选必须满足：

- source archive / fixed revision 已固定。
- source archive sha256 或 source tree hash 已记录。
- manifest 文件自身 sha256 已由上层 manifest 绑定。
- repository URL、dataset revision 或 harness revision 已记录。
- baseline verifier 可运行。
- flaky probe 通过或风险可接受。
- source materialization repeat check 通过。
- patch feasibility probe 通过。
- verifier command、verifier definition hash、timeout、attempt、exit code、stdout/stderr/log refs 和 actual report paths 已记录。
- evaluator-only evidence 分区完整。
- adapter-visible input 不含 gold patch、raw test patch、FAIL_TO_PASS / PASS_TO_PASS 原始 selector、hidden selector、official harness report、official report、official resolved status、Authorization marker、provider credential marker 或 provider raw response。
- Docker resource facts 和 platform facts 已记录。

每个候选最终状态必须写入：

- `final_status`
- `stage`
- `primary_failure_category`
- `secondary_failure_category`
- `evidence_ref`
- `retryable`

## 8. 候选选择和降级规则

### 8.1 统一 failure taxonomy

所有失败候选必须使用统一 failure taxonomy。每条最终记录必须包含 `final_status`、`stage`、`primary_failure_category`、`secondary_failure_category`、`evidence_ref` 和 `retryable`。

允许的 `primary_failure_category`：

- `dataset_or_source_unavailable`
- `source_not_freezable`
- `source_materialization_mismatch`
- `visibility_or_contamination_blocked`
- `image_build_failed`
- `dependency_install_failed`
- `test_patch_apply_failed`
- `baseline_invalid`
- `pass_to_pass_regression`
- `environment_health_failed`
- `flaky`
- `patch_apply_failed`
- `post_patch_unresolved`
- `timeout`
- `docker_disk_limit`
- `docker_memory_limit`
- `architecture_incompatible`
- `official_harness_error`
- `credential_or_external_service_required`
- `license_or_provenance_blocked`
- `out_of_scope`

`secondary_failure_category` 可以记录更细原因，例如 `network_required_at_test_time`、`large_binary_download`、`native_dependency_arm64_failed`、`amd64_emulation_timeout`、`missing_issue_patch_link`、`gold_patch_leakage_risk`、`official_report_leakage_risk`。

`stage` 必须来自：

- `inventory`
- `image_prewarm`
- `dependency_probe`
- `baseline_probe`
- `flaky_probe`
- `patch_probe`
- `freeze_decision`

accepted / auditable：

- 可进入 V4 implementation plan 的 P0 任务清单。
- 可计入至少 8 个 accepted / auditable task definitions。
- 若属于 V4 PR / issue 构造流程新增任务，可计入至少 4 个 V4 新构造任务。

diagnostic-only：

- 可用于 failure diagnostics、platform diagnostics、prompt injection diagnostics 或 tool lifecycle diagnostics。
- 不计入 accepted / auditable 最低数量。
- 不进入正式训练 payload。

quarantined：

- 任务有价值，但当前存在 flaky、依赖、平台、运行时间或 source materialization 风险。
- 后续可以重新 probe。
- 不计入 accepted / auditable 最低数量。

rejected：

- source 不可固定、evaluator-only evidence 不可隔离、baseline verifier 不稳定、patch 不可应用、依赖不可安装，或任务超出 V4 范围。
- 不进入 V4 implementation plan 的任务主线。

## 9. 建议候选池规模和最终构成

建议 feasibility 阶段先准备：

- 8 到 12 个 public SWE-Bench-like Python 候选。
- 14 到 18 个 V4 PR / issue 构造候选。
- 4 到 6 个非 Python 技术栈候选作为多样性 probe。
- 2 到 3 个 V3 accepted 或等价轻量任务作为 regression anchors。

这些类别可以有少量重叠。例如，一个 V4 PR / issue 构造候选也可以是非 Python 技术栈候选；V3 regression anchors 不计入 V4 PR / issue 新构造任务数量。

建议最终 V4 implementation plan 输入：

- 至少 8 个 accepted / auditable task definitions。
- 至少 4 个 V4 PR / issue 新构造任务。
- 至少 4 个不同项目家族。
- 优先包含至少 2 个 `tier_2_complex` 任务，但这是 stretch / preference，不是 V4 acceptance 硬门。若 feasibility 结果不足，应记录为 staged enhancement。
- 至少 1 个非 Python 技术栈任务如果 feasibility 稳定；如果不稳定，明确降级为 diagnostic-only，不阻塞 P0。
- 保留 V3 accepted SWE-Bench-like / real_repository 任务作为 regression anchors。

## 10. 与 V4 implementation plan 的关系

V4 implementation plan 不应在任务未知的情况下直接展开 rollout queue 和 export quality 实现。建议顺序是：

1. 先执行本文定义的 Level 0 到 Level 2，确认 Docker 和候选环境。
2. 对候选任务执行 Level 3 到 Level 4，得到 baseline、flaky、patch feasibility 和 evidence partition。
3. 产出 Level 5 的 `v4_task_selection_manifest.json` 和 `v4_task_freeze_readiness_report.json`。
4. implementation plan 使用这两个产物作为 P0 task source freeze / construction preflight 的输入。
5. 如果 Level 5 不能给出至少 8 个 accepted / auditable 候选，implementation plan 必须先缩小任务目标或保留 staged acceptance，而不是继续假设任务集已经准备好。

## 11. 风险和降级路径

### 风险：复杂任务构建耗时过长

降级路径：保留任务为 `quarantined`，优先选择依赖可缓存、测试范围可控的 `tier_1_moderate` 或 `tier_2_complex` 任务。

### 风险：非 Python 技术栈不稳定

降级路径：非 Python 候选先作为 diagnostic-only；只有 Docker build、baseline verifier 和 patch probe 都稳定后，才计入 accepted / auditable。

### 风险：官方 SWE-Bench-like 任务平台不兼容

降级路径：记录 `platform_blocked` 或 `official_harness_platform_blocker`，不要把失败归因于 agent。可以转向 V4 PR / issue 构造任务。

### 风险：任务复杂度过高导致 verifier 运行成本不可控

降级路径：限制 task timeout、test budget 和 dependency cache；把高风险任务保留为 `tier_3_high_risk` diagnostic-only。

### 风险：任务选择过程引入污染

降级路径：所有 official report、gold patch、hidden selector、credential marker、provider raw response 都保留在 evaluator-only evidence 分区，并对 adapter-visible input 和 export payload 做污染扫描。

## 12. 建议下一步

建议在 V4 implementation plan 前新增一个独立执行步骤：

```text
V4 SWE / PR task feasibility and freeze preparation
```

这个步骤的完成定义不是“所有任务都 accepted”，而是产出：

- `candidate_task_inventory.jsonl`
- `docker_image_prewarm_report.json`
- `baseline_verifier_probe_report.json`
- `flaky_probe_report.json`
- `patch_feasibility_report.json`
- `v4_task_selection_manifest.json`
- `v4_task_freeze_readiness_report.json`

这些产物可以直接成为 V4 implementation plan 第一阶段的输入。

## 13. 当前初始执行记录（2026-05-04）

本节记录在编写本文后立即启动的一轮初始 public SWE-Bench-like 数据选择和本机可行性 probe。它用于降低 V4 implementation plan 的任务不确定性，不是 V4 最终 acceptance，也不能替代后续 RepoHarness 自有 verifier、source archive freeze、flaky probe 或 V4 PR / issue 任务构造。

执行目录：

```text
runs/v4-swe-task-feasibility-20260504T044301Z/
```

已完成 Level 0 / Level 1 证据：

- Docker Desktop 可用，`linux/amd64` 和 `linux/arm64` 基础容器 probe 均通过。
- Docker 运行时记录显示内存配置为 `32768 MiB`，符合本设计中 Docker memory >= `24GB` 的要求。
- 宿主机工作区所在磁盘可用空间约 `681GB`，高于新增 image build 的暂停阈值。
- Hugging Face Dataset Viewer 读取 `princeton-nlp/SWE-bench_Lite`，dataset revision 为 `6ec7bb89b9342f664a54a6e0a6ea6501d3437cc2`。
- `candidate_task_inventory.jsonl` 覆盖 test split 的 `300` 条任务。
- `selected_public_swebench_like_candidates.jsonl` 选择 `18` 条候选，使用 `family_quota_then_score_v1` 策略，覆盖 Django、Astropy、Matplotlib、Scikit-learn、Sphinx、Sympy、Pytest、Pylint 和 Flask 等项目家族。

初始 public SWE-Bench-like probe 选择了 `5` 个 `tier_2_complex` 候选：

- `django__django-11283`
- `astropy__astropy-14182`
- `sphinx-doc__sphinx-7686`
- `matplotlib__matplotlib-18869`
- `scikit-learn__scikit-learn-10297`

这些候选覆盖 Web framework、天文科学计算、文档构建、绘图库和机器学习库，复杂度和技术栈广度均高于 V3 最终固定的轻量 SWE-Bench-like 小子集。

本机官方 harness gold patch probe 结果：

- 命令记录：`runs/v4-swe-task-feasibility-20260504T044301Z/baseline/official_harness_initial_public_swe_probe_command.txt`
- 安全摘要：`runs/v4-swe-task-feasibility-20260504T044301Z/baseline/public_swebench_initial_probe_result.json`
- freeze readiness 摘要：`runs/v4-swe-task-feasibility-20260504T044301Z/freeze/public_swebench_initial_freeze_readiness_report.json`
- 结果 manifest：`runs/v4-swe-task-feasibility-20260504T044301Z/manifests/public_swebench_initial_probe_result_manifest.json`
- 结果：`5 / 5` gold patch probe resolved，`error_count = 0`。
- 观测总耗时：`2033` 秒，约 `33` 分 `53` 秒。
- Docker probe 后 `docker system df` 回到约 `1.946GB` image 占用，说明 `--clean True` 没有留下大型候选任务镜像。

边界说明：

- 原始 dataset rows、gold patch predictions、official harness report、patch diff、test output 和 hidden selector 明细均位于 evaluator-only 或官方 harness 日志目录中。
- `public_swebench_initial_probe_result.json` 只保留 resolved、patch applied、success / failure 计数、哈希和 report ref，不包含 patch 文本、test patch 文本或 selector 名称。
- 这 `5` 个任务可以作为 V4 public SWE-Bench-like freeze candidates，但还不能直接计入 V4 最终 accepted / auditable task definitions。后续至少还需要 source archive materialization、repeat materialization hash、RepoHarness 自有 verifier probe、flaky probe、adapter-visible input freeze 和 evaluator-only evidence manifest。
- 这轮 public SWE-Bench-like 成功不能替代至少 `4` 个 V4 PR / issue 构造流程新增任务。PR / issue 任务仍需要单独执行 auditable construction、baseline verifier、patch provenance 和 evidence partition。
