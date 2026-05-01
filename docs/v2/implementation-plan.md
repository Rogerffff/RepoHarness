# RepoHarness V2 Detailed Implementation Plan

## 0. 文档定位

本文把 `docs/v2/scope-and-roadmap.md` 中的第二版范围，转化为可以逐阶段执行、逐阶段验收、逐阶段审查的工程实施计划。

第二版建立在第一版已经完成的 replay-only 最小闭环之上。第一版已经能够在本地 micro-repo task 上完成任务加载、工作区准备、工具调用、Agent Loop、strict patch replay final verifier、reward metadata、metrics、运行轨迹和训练导出。第二版不推翻这些边界，而是在同一套对象模型上增强五个方向：

1. 更强的 run metadata、导出质量和审计。
2. 多 rollout 与多 scaffold 对比。
3. mock provider 和至少一个真实模型 provider 接入。
4. 20 到 50 个中小型 repository-level 或 repository-style task。
5. 为 Docker-based executable repository environment 提供可验收的扩展路径。

本文不是第二版已经完成的声明，也不是训练算法设计文档。本文只定义工程实现顺序、模块改动范围、测试要求和验收口径。

## 1. 实施原则

第二版实现必须保留第一版已经验证过的不变量：

- `gold_patch`、隐藏测试、ReplayScript expected outcome、reward-only 字段和本地敏感路径不能进入 `PreparedMessages`、模型可见 transcript 或训练导出 prompt。
- hidden fail-to-pass 和 pass-to-pass suite 不能通过 `run_tests` 的模型可见输出泄漏给模型，除非当前 run 明确标记为 `test_feedback_policy = "oracle_hidden_feedback"`，并且该 run 不被标记为 SWE-Bench-like final-only 评测。
- feedback verifier 只是模型中间反馈；formal final verifier 仍然是正式 reward、run outcome 和训练奖励来源。
- final patch 必须先冻结，再在独立 verification workspace 中 strict patch replay。
- 每个已解析 `ToolCall` 都必须有终态 `ToolResult`。未知工具、schema 校验失败、权限拒绝、工具异常、工具超时和中断都不能产生孤立 tool call。
- 导出器只读取已有 run directory，不重新运行 verifier，不改写已经记录的 reward、metrics、transcript 或 events。
- Docker execution mode 只能称为 Docker-based executable repository environment，不能写成生产级安全沙箱。
- 真实模型运行只能表述为真实 provider 驱动的评测运行，不能表述为已经训练出了 coding agent。

第二版每个阶段都应满足四个完成条件：

1. 旧 replay 路径仍然通过对应回归测试。
2. 新增 schema 有单元测试，并且字段缺失、兼容降级和非法组合都有测试。
3. 新增运行产物有 `inspect-run` 或导出审计可读取的证据。
4. 文档、summary 和 README 不夸大能力。

第二版明确不做以下事项：

- 不实现生产级安全沙箱、多租户隔离平台、沙箱逃逸防护证明或操作系统级强制断网能力。
- 不实现完整插件市场、企业权限平台、远程 worker 平台或大规模异步 rollout 集群。
- 不复现完整 SWE-Bench、公开榜单基础设施或某家公司的内部 post-training stack。
- 不实现新的强化学习算法、训练调度器、参数更新流程或 token 级训练日志系统。
- 不默认记录、导出或训练 provider 隐藏思考内容；provider 原始响应只能作为受控 artifact 保存，并默认不得成为训练目标。
- 不实现 hooks、Model Context Protocol（模型上下文协议）服务器、插件系统或技能系统；第二版最多预留字段，不能把这些能力写成已交付。

每个阶段的审查记录应使用固定结构，避免只留下“测试通过”的自由文本结论。阶段审查至少记录：

- 必需产物。
- 正例证据。
- 负例证据。
- 机器阈值或验收命令。
- 允许降级项。
- 禁止降级项。
- 通过判定。
- 不通过判定。

## 2. 代码和文档落点

第二版优先沿用当前目录，不做大规模重命名。建议新增或重点修改的模块如下：

```text
src/repo_harness/
  run_metadata/      # 新增：run_config_facts.json、run_metadata.json、环境指纹、tool schema snapshot
  export/            # 增强：training_eligibility、export manifest、audit report、pairing policy
  scaffolds/         # 增强：registry、single_shot_patch、planner_coder_verifier
  model_client/      # 增强：ModelClient protocol、factory、mock provider、真实 provider
  evaluation/        # 增强：experiment runner、多 rollout、aggregate report
  tasks/             # 增强：repo materialization 和 task source metadata
  workspace/         # 增强：Workspace Adapter 协议，为 Docker 后端留出接口
  trajectory/        # 增强：inspect-run 展示 V2 metadata 和 audit 状态
```

建议新增文档目录：

```text
docs/v2/
  implementation-plan.md
  implementation-log/
  review/implementation/
  final-acceptance.md
  walkthrough.md
```

如果第二版按 commit 推进，建议每个阶段至少对应一个 commit。阶段内可以拆成更小 commit，但不要跨阶段混合。例如不要在导出审计阶段顺手实现真实 provider，也不要在 scaffold 阶段顺手扩展任务集。

本文验收命令中的 `runs/v2-*` 目录是示例路径。实际执行时必须使用 fresh output directory；建议每个阶段先设置唯一目录变量，例如 `RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)` 和 `OUT_DIR=runs/v2-export-audit-$RUN_ID`。如果复用固定目录，必须先用项目允许的清理流程移走旧产物，不能让已存在目录导致验收命令偶发失败。导出检查不得依赖 shell glob 展开来选择某一个 export directory；应优先使用 manifest 查询式参数，例如 `inspect-export "$OUT_DIR/exports" --all --format sft_jsonl --require-trainable-samples`。

## 3. 阶段总览

建议第二版分为十五个阶段：

1. 第二版 schema、版本常量和基础测试。
2. `run_config_facts.json`、最终 `run_metadata.json`、本地环境指纹和 tool schema snapshot。
3. `inspect-run` 第二版展示和 legacy metadata 兼容。
4. 导出 `training_eligibility`、`export_manifest.json`、`audit_report.json` 和 `audit_report.md`。
5. preference pair 硬门控和 compare scope。
6. ExperimentConfig 最小多 rollout 运行器和实验报告。
7. 最小 `ModelClient` 协议、factory、replay/fake 兼容层和 Scaffold registry。
8. `single_shot_patch` scaffold。
9. `planner_coder_verifier` scaffold 计划内增强。
10. mock provider、provider artifact 和 provider 错误分类。
11. 真实 provider 最小接入、provider 错误路径和 smoke report。
12. repo materialization 和任务来源扩展。
13. 任务集扩展到 20 到 50 个 repository-level 或 repository-style task。
14. Workspace Adapter 协议收口和 Docker execution mode 扩展路径。
15. 第二版最终验收、文档、示例和审查收口。

前十三个阶段覆盖第二版核心能力和计划内增强。其中阶段九 `planner_coder_verifier` 是计划内增强，不计入最小完成定义；如果延期，最终验收必须明确标记为 deferred enhancement，不能把它的缺失写成已通过。第十四阶段是条件成熟后的扩展阶段：第二版最小完成只要求 Docker 状态可审计，也就是继续拒绝并保留接口计划，或者实现最小 Docker 后端并通过独立端到端验收；它不要求必须交付 Docker 后端。

## 4. 里程碑验收门

十五个阶段用于提交管理，里程碑验收门用于判断能否进入更高风险工作。建议按五个里程碑推进。

### 4.1 里程碑一：metadata 与导出质量

覆盖阶段一到阶段五。

必须产出：

- `run_config_facts.json`
- 最终 `run_metadata.json`
- tool schema snapshot artifact
- format-specific export directory
- `export_manifest.json`
- `audit_report.json`
- `audit_report.md`
- preference pair blocked reasons 或合格 pair

必须通过：

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v2_schemas.py
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_run_metadata.py tests/unit/test_tool_schema_snapshot.py
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_export.py
PATH=.venv/bin:$PATH python -m pytest tests/integration/test_export_from_run.py
```

允许降级：

- legacy run 可以使用 `metadata_source = "legacy_inferred"`。
- 缺失第二版 metadata 的 legacy run 可以进入 `diagnostic_only`，但不能被伪造成 `trainable`。

不允许降级：

- 不允许多个导出格式覆盖同一个 audit report。
- 不允许 artifact manifest invalid 的样本进入正式训练数据。

### 4.2 里程碑二：实验与 scaffold

覆盖阶段六到阶段九。

必须产出：

- `experiment_manifest.json`
- `aggregate_metrics.json`
- 最小 `ModelClient` 协议和 replay/fake 兼容层。
- 至少两个 scaffold 的 run metadata。
- scaffold phase 或 policy 证据。
- 每个里程碑阶段的审查记录，至少包含命令、产物路径、失败负例、降级项和遗留风险。

必须通过：

```bash
SCAFFOLD_EXP_DIR="${SCAFFOLD_EXP_DIR:?set to the generated scaffold comparison experiment directory}"

PATH=.venv/bin:$PATH python -m pytest tests/integration/test_experiment_runner.py
PATH=.venv/bin:$PATH python -m pytest tests/integration/test_single_shot_patch.py
PATH=.venv/bin:$PATH repo-harness inspect-experiment "$SCAFFOLD_EXP_DIR" \
  --assert-minimums tests/fixtures/run_configs/v2/scaffold_comparison_thresholds.yaml
```

如果 `planner_coder_verifier` 被纳入当前第二版交付范围，还必须额外通过：

```bash
PATH=.venv/bin:$PATH python -m pytest tests/integration/test_planner_coder_verifier.py
```

允许降级：

- 第二版最小完成必须至少有 `simple_react` 和 `single_shot_patch` 两种可运行 scaffold。`planner_coder_verifier` 是计划内增强目标：如果范围需要收紧，可以在最终验收中明确标记为 deferred enhancement，但不能把它的测试缺失伪装成已通过。

不允许降级：

- 不允许只记录 `scaffold_id`，但实际 prompt、allowed tools、phase 或 stop policy 不生效。

### 4.3 里程碑三：模型 provider

覆盖阶段十到阶段十一。

必须产出：

- mock provider 成功和失败样例。
- raw provider request/response artifact。
- provider error taxonomy。
- `real_provider_smoke_report.json`。
- 真实 provider 无凭证 skip 或有凭证 accepted 记录。

必须通过：

```bash
REAL_PROVIDER_REPORT="${REAL_PROVIDER_REPORT:?set to the generated real_provider_smoke_report.json path}"

PATH=.venv/bin:$PATH python -m pytest tests/unit/test_model_client_factory.py tests/unit/test_mock_provider.py
PATH=.venv/bin:$PATH python -m pytest tests/integration/test_real_provider_smoke.py
PATH=.venv/bin:$PATH repo-harness inspect-real-provider-smoke \
  --report "$REAL_PROVIDER_REPORT" \
  --allow-skip-without-credentials \
  --require-accepted-with-credentials
```

允许降级：

- 无凭证环境中真实 provider smoke test 可以 skip。

不允许降级：

- 不允许把无凭证 skip 记成真实 provider 成功。
- 不允许 provider 原始响应直接成为训练目标。

### 4.4 里程碑四：任务集

覆盖阶段十二到阶段十三。

必须产出：

- V2 task fixtures。
- repo materialization metadata。
- source hash、base commit 和 environment spec hash。
- experiment aggregate metrics。
- 机器可执行的 V2 最低阈值检查。

必须通过：

```bash
TASK_SET_DIR="${TASK_SET_DIR:?set to the generated V2 task-set experiment directory}"

PATH=.venv/bin:$PATH repo-harness inspect-experiment \
  "$TASK_SET_DIR" \
  --assert-minimums tests/fixtures/run_configs/v2/task_set_thresholds.yaml
```

不允许降级：

- 不允许把全部 skipped 的 20 个任务记成第二版任务集验收通过。

### 4.5 里程碑五：Docker 扩展路径

覆盖阶段十四。

必须二选一：

- 接口保留模式：继续拒绝 Docker execution mode，并通过拒绝逻辑测试。
- Docker 后端模式：实现最小 Docker backend，并通过 Docker 端到端测试。

不允许降级：

- 不允许把配置能加载写成 Docker execution mode 已实现。

## 阶段一：第二版 schema、版本常量和基础测试

目标：先定义第二版新增对象的机器可校验形状，避免后续阶段用散乱字典传递核心事实。

建议改动：

- 在 `src/repo_harness/schema_versions.py` 中增加第二版需要的版本常量：
  - `RUN_METADATA_SCHEMA_VERSION`
  - `ENVIRONMENT_FINGERPRINT_VERSION`
  - `TOOL_SCHEMA_SNAPSHOT_VERSION`
  - `EXPORT_AUDIT_SCHEMA_VERSION`
  - `EXPORT_MANIFEST_SCHEMA_VERSION`
  - `PAIRING_POLICY_VERSION`
  - `EXPERIMENT_SCHEMA_VERSION`
  - `SCAFFOLD_REGISTRY_VERSION`
  - `MODEL_CLIENT_PROTOCOL_VERSION`
- 新增 `src/repo_harness/run_metadata/`：
  - `schemas.py`
  - `__init__.py`
- 在 `run_metadata/schemas.py` 中定义：
  - `RunConfigFacts`
  - `RunConfigFactsRef`
  - `RunMetadata`
  - `RunMetadataRef`
  - `EnvironmentFingerprint`
  - `ExecutionModeFacts`
  - `WorkspaceBackendFacts`
  - `WorkspaceExecutionFacts`
  - `SourceCheckoutFacts`
  - `FailureDiagnostics`
  - `ToolSchemaSnapshot`
  - `ToolProtocolFacts`
  - `RunMetadataSource`
- 新增 `src/repo_harness/workspace/protocol.py`：
  - `WorkspaceBackend`
  - `WorkspaceAdapter`
  - `WorkspacePaths`
  - `WorkspaceCommandResult`
  - `WorkspaceBackendError`
- 在 `src/repo_harness/export/schemas.py` 中扩展或新增：
  - `TrainingEligibility`
  - `ExportRecordQuality`
  - `ExportManifest`
  - `ExportAuditReport`
  - `ExportAuditItem`
  - `ExportAuditSample`
  - `PairingPolicy`
  - `CompareScope`
- 在 `src/repo_harness/evaluation/schemas.py` 或新模块中定义 `ExperimentConfig` 和 `ExperimentRunSpec`。
- 在 evaluation 或 runtime schema 中定义：
  - `TestFeedbackPolicy`
  - `FeedbackTestsPassedPolicy`
  - `ResolvedFeedbackPolicyFacts`
- 在 `src/repo_harness/model_client/schemas.py` 中预定义第二版模型调用上下文对象：
  - `ModelRequestContext`
  - `ModelGenerationRequest`
  - `ModelProviderOptions`
  - 扩展现有 `ProviderCredentialPolicy`

字段要求：

- `TrainingEligibility` 枚举必须包含 `trainable`、`diagnostic_only`、`skipped`、`invalid`。
- `ExportRecord.training_eligibility` 必须是顶层强类型字段，或者放入顶层强类型 `quality.training_eligibility` 子对象。它不能放在自由 `metadata` 字典中。
- `ExportRecord.filter_status`、`invalid_for_training`、`invalid_reason` 和 `quality.training_eligibility` 保留兼容关系，校验器必须拒绝互相冲突的组合。例如 `training_eligibility = invalid` 时不能出现 `invalid_for_training = false`。
- `RunMetadata` 中不能把 provider、model id、scaffold、预算、权限模式、工具策略等关键字段藏在自由文本 metadata 中。
- `WorkspaceBackendFacts`、`WorkspaceExecutionFacts` 和 `SourceCheckoutFacts` 必须在阶段一先定义最小字段。阶段二只能写 local process backend 的事实；阶段十二再扩展 repo materialization，不允许后续 Docker、任务来源和 run metadata 各自发明不兼容字段。
- `WorkspaceBackend` 和 `WorkspaceAdapter` 的最小协议必须在阶段一先落地。阶段十四只做 Docker execution mode 的拒绝逻辑或最小 Docker 后端，不再第一次抽象 workspace protocol。
- `RunConfigFacts` 是 Agent Loop 前写入的不可变配置事实，包含 provider、model、scaffold、工具策略、上下文策略、权限策略、预算、test feedback policy 和 execution facts。`RunConfigFactsRef` 最小形状为 `{relative_path, sha256, schema_version}`。
- `RunMetadata` 是 run 完成后写入的最终运行事实，包含 outcome、metrics summary、failure diagnostics、final verifier、reward、export readiness 等最终事实。`RunMetadataRef` 最小形状为 `{relative_path, sha256, schema_version}`。
- Agent Loop 期间的 events、model calls 和 provider requests 只能引用不可变 `RunConfigFactsRef`、tool schema snapshot ref 和 context refs；不能引用尚未最终写入的 `RunMetadataRef`。
- `run_metadata.json` 必须采用两阶段原子写入：先写临时文件，完成最终字段和 sha256 后再 rename 到根目录。最终 `RunMetadataRef` 只在 summary、manifest、export audit 或后置 inspection 中引用。
- `FailureDiagnostics` 用于统一分类模型失败、环境失败、provider 失败、工具协议失败、权限拒绝、任务质量失败和未知失败，至少包含 `failure_category`、`failure_type`、`recoverable`、`source_component`、`message`、`artifact_refs`。`failure_type` 至少包含 `malformed_tool_call`、`tool_timeout`、`tool_schema_invalid`、`permission_denied_unrecovered`、`no_patch_generated`、`provider_auth_error`、`provider_rate_limit`、`provider_timeout`、`context_limit`、`environment_setup_failed`、`baseline_quality_failed`、`final_verifier_failed`、`reward_hacking_suspected`、`unknown_failure`。
- `ExportAuditItem.status` 建议限制为 `passed`、`failed`、`warning`、`skipped`。
- `ModelRequestContext` 至少包含 `run_id`、`task_id`、`turn`、`model_call_id`、`prepared_messages`、`prepared_messages_ref`、`model_input_hash`、`context_revision`、`provider_message_format`、`context_truncation_facts`、`omitted_context_facts`、`generation_config`、`provider_model_settings`、`allowed_tool_definitions`、`tool_choice`、`tool_schema_snapshot_ref`、`provider_options`、`scaffold_id`、`scaffold_phase`、`run_config_facts_ref`、`budget_state`、`request_timeout_seconds`、`raw_request_logging_policy`、`credential_policy` 和 `retry_policy`。不要使用字段名 `model_config`，避免和 Pydantic 配置命名产生歧义。
- 凭证策略统一扩展当前代码已有的 `ProviderCredentialPolicy`。不要新增并行的 `ModelCredentialPolicy`，避免 provider factory、artifact 脱敏和 smoke skip 逻辑出现两套凭证策略。
- `TestFeedbackPolicy` 枚举必须包含 `disabled`、`public_only`、`structured_public_feedback`、`oracle_hidden_feedback`。
- `ResolvedFeedbackPolicyFacts` 至少记录 scaffold default、runtime override、resolved test feedback policy、resolved feedback-tests-passed policy、`hidden_feedback_visible_to_model`、`swe_bench_like_final_only`。
- `CompareScope` 在阶段一必须先有严格默认值。阶段五可以先用默认严格 compare scope 和命令行显式传入的 compare scope 做硬门控；阶段六再由 `ExperimentConfig` 统一生成 compare scope。换句话说，preference pair 的最低实现不能依赖尚未完成的 experiment runner。
- 所有 schema 都必须保持 strict 模式，避免未知字段悄悄进入训练导出。

测试要求：

- 新增 `tests/unit/test_v2_schemas.py`。
- 覆盖合法 `RunMetadata`、合法 `ExportManifest`、合法 `ExportAuditReport`、合法 `PairingPolicy`。
- 覆盖非法 `training_eligibility`、非法 audit status、缺失关键 compare scope 字段。
- 覆盖合法 `ModelRequestContext`，并断言缺失 tool schema snapshot、generation config、model call id、prepared messages ref、model input hash、上下文截断事实、预算状态或 scaffold phase 时 schema 校验失败。
- 覆盖 `RunConfigFactsRef` 和最终 `RunMetadataRef` 的 sha256 校验、相对路径校验和不可混用约束。
- 覆盖 `FailureDiagnostics` 的枚举分类和未知失败兜底分类。
- 覆盖 `TestFeedbackPolicy` 合法值、非法值和 `oracle_hidden_feedback` 与 `swe_bench_like_final_only = true` 的非法组合。
- 覆盖 `feedback_tests_passed_policy = "not_applicable"` 作为用户输入时 schema 校验失败；`not_applicable` 只能由解析后的 `ResolvedFeedbackPolicyFacts` 产生。
- 覆盖第一版 `ExportRecord` 仍然可以被当前导出器构造。

验收命令：

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v2_schemas.py tests/unit/test_export.py
PATH=.venv/bin:$PATH python -m compileall src
```

本阶段不做的事情：

- 不写真实 provider。
- 不改变 Agent Loop 行为。
- 不改变第一版 export 命令的兼容输出行为；规范 export directory 的引入放到阶段四处理。

## 阶段二：`run_config_facts.json`、最终 `run_metadata.json`、本地环境指纹和 tool schema snapshot

目标：第二版新 run 必须有稳定事实来源，导出器和实验比较不能继续从 prompt、metrics 或第一条 model event 中反推关键配置。

建议改动：

- 新增 `src/repo_harness/run_metadata/writer.py`。
- 新增 `src/repo_harness/run_metadata/fingerprint.py`。
- 新增 `src/repo_harness/run_metadata/tool_snapshot.py`。
- 在 `src/repo_harness/evaluation/runner.py` 中，在 run directory 创建后、正式 Agent Loop 开始前，写入不可变 `run_config_facts.json`。
- 在 run 完成、skipped 或 failed 后，原子写入最终 `run_metadata.json`。
- 在 RunRecorder 中继续管理 artifact，不让 run metadata writer 自己绕开 artifact manifest 写重要二进制或大文件。
- `run_config_facts.json` 和 `run_metadata.json` 都是 run directory 根目录事实文件。其他事件或 provider request 在 Agent Loop 期间只能引用 `RunConfigFactsRef`；最终 export、summary 和 inspect 可以引用 `RunMetadataRef`。二者都不是普通 `ArtifactRef`。如果后续需要 artifact manifest 统一校验，可以额外写入 manifest-backed artifact 副本，但不能改变根目录事实文件的地位。

`run_config_facts.json` 至少记录：

- run id、task id、task version、dataset name、source kind、base commit、source archive hash。
- provider、model id、temperature、seed、max output tokens、retry policy、credential policy、provider request logging policy。
- scaffold id、scaffold version、allowed tools policy、phase policy、stop policy。
- test feedback policy、feedback tests passed policy、hidden feedback visible to model、SWE-Bench-like final-only 标记。
- tool schema snapshot ref、tool order、tool parser version、tool result format version、tool policy version。
- context builder version、context policy version、prompt template version、token estimator version。
- permission mode、permission policy version、network policy、shell command policy version。
- verifier name、verifier version、final verifier mode、reward formula version、outcome policy version。
- max turns、max tool calls、max test runs、task timeout、command timeout、context budget、artifact budget。
- execution mode facts：Python 版本、操作系统、包管理器版本、关键锁文件 hash、setup artifact hash、dependency state ref、environment spec hash、source checkout hash、workspace adapter version。

最终 `run_metadata.json` 至少记录：

- `run_config_facts_ref`。
- final run status、agent stop reason、run outcome、reward status、final verifier status。
- metrics summary、tool call summary、model call summary、artifact manifest status。
- failure diagnostics 初始状态和最终状态。如果 run 失败或 skipped，必须通过 `FailureDiagnostics` 写出模型失败、环境失败、provider 失败、工具协议失败、权限拒绝、任务质量失败或未知失败的结构化分类。
- export readiness：是否具备 final patch、formal final verifier、reward metadata、clean transcript、clean artifact manifest。
tool schema snapshot 要求：

- 记录模型当时可见工具的稳定顺序。
- 记录每个工具的 name、tool version、model visible description、input schema、output schema 或结果格式版本、read-only 标记、destructive 标记、permission 需求、最大输出限制。
- 记录 snapshot sha256。
- 写入 artifact，并在 `run_metadata.json` 中引用 `tool_schema_snapshot_ref`。

环境指纹要求：

- 对 local process mode 记录事实，不声称隔离能力。
- 阶段二必须使用阶段一的 `WorkspaceBackendFacts`、`WorkspaceExecutionFacts` 和 `SourceCheckoutFacts` 写入 local process backend 事实，不能只写自由文本环境说明。
- 记录 Python 版本、平台、包管理器标识、锁文件 hash。
- 对当前任务 workspace 记录 source checkout hash。hash 规则必须排除 `.git/`、缓存目录和运行产物目录。
- 如果 setup 没有运行，setup artifact hash 写为 `none`，不能伪造。
- 如果某个字段无法获取，使用 `unknown` 或 `missing`，并在后续 audit 中形成 warning。

测试要求：

- 新增 `tests/unit/test_run_metadata.py`。
- 新增 `tests/unit/test_tool_schema_snapshot.py`。
- 新增或扩展集成测试，断言成功 replay run 先产生 `run_config_facts.json`，run 完成后产生最终 `run_metadata.json`。
- 断言 `tool_schema_snapshot_ref` 指向 artifacts manifest 中存在的 artifact。
- 断言 `RunConfigFactsRef` 和最终 `RunMetadataRef` 使用相对路径和 sha256 引用根目录事实文件，不会被误识别成普通 artifact manifest entry。
- 断言 Agent Loop 期间写出的 model call event 只能引用已写入的 `RunConfigFactsRef`，不能引用尚未最终写入的 `RunMetadataRef`。
- 断言本机绝对路径不会进入训练导出字段；run metadata 可以保留运行事实，但导出时仍需脱敏。

验收命令：

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_run_metadata.py tests/unit/test_tool_schema_snapshot.py
PATH=.venv/bin:$PATH python -m pytest tests/integration/test_minimal_vertical_slice.py
```

本阶段不做的事情：

- 不实现 export audit。
- 不实现新 scaffold。
- 不改变第一版旧 run directory。

## 阶段三：`inspect-run` 第二版展示和 legacy metadata 兼容

目标：让人和工具都能快速判断一个 run 是第一版 legacy run，还是第二版带完整 metadata 的 run。

建议改动：

- 修改 `src/repo_harness/trajectory/inspect.py`。
- 新增 `src/repo_harness/run_metadata/reader.py`。
- 对缺失 `run_metadata.json` 的第一版历史 run，返回结构化 metadata 状态：
  - `metadata_status = "legacy_missing"`
  - `metadata_source = "legacy_inferred"`
  - 不要改写原 run directory。
- 对第二版 run，展示：
  - provider
  - model id
  - scaffold id 和 scaffold version
  - run config facts 状态
  - run metadata 状态
  - tool schema snapshot 状态
  - artifact manifest quality status
  - export audit status
  - baseline、final verifier、reward、metrics 和 summary 状态
  - failure diagnostics 分类和可恢复状态

命令行输出要求：

- `repo-harness inspect-run <run_dir>` 在没有 `run_metadata.json` 时不能报错退出，除非原有 run directory 本身损坏。
- 输出中要明确写出 `Run config facts: missing`、`Run config facts: ok`、`Run metadata: legacy_missing`、`Run metadata: missing` 或 `Run metadata: ok`。
- 如果第二版 run 已写入 `run_config_facts.json` 但因为中断、崩溃或人工停止缺失最终 `run_metadata.json`，`inspect-run` 必须保留可审计输出并把 metadata 状态标记为 `missing`，不能伪装成 legacy run。
- 如果 export audit 不存在，显示 `Export audit: not_generated`。

测试要求：

- 扩展 `tests/unit` 中 inspect 相关测试，或新增 `tests/unit/test_inspect_run.py`。
- 用第一版 fixture run 或临时构造 run 验证 legacy 缺失 metadata 的输出。
- 用第二版新 run 验证 run config facts、metadata、tool schema snapshot 和 audit 状态输出。

验收命令：

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_inspect_run.py
PATH=.venv/bin:$PATH python -m pytest tests/integration/test_export_from_run.py
```

本阶段不做的事情：

- 不生成 audit report。
- 不 backfill 旧 run。

## 阶段四：导出 `training_eligibility`、`export_manifest.json`、`audit_report.json` 和 `audit_report.md`

目标：把训练导出从“生成 JSONL 文件”推进到“有机器可校验的导出清单和样本审计”。

建议改动：

- 新增 `src/repo_harness/export/audit.py`。
- 新增 `src/repo_harness/export/manifest.py`。
- 修改 `src/repo_harness/export/exporter.py`：
  - SFT、RL rollout、preference export 都写独立的 format-specific export directory。
  - 每次导出使用唯一 `export_id`，建议格式为 `<format>_<utc_timestamp>_<short_hash>`；测试中可以使用固定时间和固定 hash 让路径稳定。
  - 规范输出目录为 `exports/<export_id>/`，目录内写入训练数据文件、`export_manifest.json`、`audit_report.json` 和 `audit_report.md`。
  - SFT、RL rollout、preference export 都写 `export_manifest.json`。
  - SFT、RL rollout、preference export 都写 `audit_report.json`。
  - SFT、RL rollout、preference export 都写 `audit_report.md`。这个 Markdown 文件是面向人工复盘的摘要，必须由 `audit_report.json` 派生，不作为训练事实来源。
  - `ExportRecord` 顶层增加 `training_eligibility`，或者增加强类型 `quality` 子对象并把 `training_eligibility` 放入 `quality.training_eligibility`。
  - `quality` 子对象建议包含 `quality_reasons`、`artifact_manifest_status`、`tool_pairing_status`、`redaction_status`、`reward_source`、`failure_diagnostics_ref`。
  - 自由 `metadata` 只保留非判定性补充信息，不能承载训练资格主状态。

导出文件命名要求：

- SFT 的规范数据文件建议为 `exports/<export_id>/data.sft.jsonl`。
- RL rollout 的规范数据文件建议为 `exports/<export_id>/data.rl.jsonl`。
- preference 的规范数据文件建议为 `exports/<export_id>/data.preference.jsonl`。
- 默认情况下，`data.sft.jsonl`、`data.rl.jsonl` 和 `data.preference.jsonl` 只能包含 `training_eligibility = "trainable"` 的样本。`diagnostic_only`、`skipped` 和 `invalid` 样本进入 `audit_report.json`、统计摘要或显式 diagnostic export；除非命令行明确传入类似 `--include-diagnostic` 的诊断导出开关，否则不能写入正式训练 JSONL。
- 如果 preference export 因 pair 不足或硬门控阻断而跳过，规范数据文件建议为 `exports/<export_id>/preference_skipped.json`。这个文件是该次导出的数据 artifact，不替代 `export_manifest.json` 和 `audit_report.json`。
- 为兼容第一版命令，可以继续写 `exports/sft.jsonl`、`exports/rl.jsonl`、`exports/preference.jsonl` 或 `exports/preference_skipped.json` 作为 latest convenience file，但这些文件不能作为审计事实来源，也不能覆盖规范 export directory 的 manifest 和 audit report。
- `export_manifest.json` 必须记录 `export_id`、format、schema version、export policy version、source run directories、导出命令参数、数据文件路径、数据文件 sha256、样本数量、included 数量、filtered 数量、skipped 数量、invalid 数量、diagnostic-only 数量、生成时间、exporter version、`audit_report_path`、`audit_report_sha256`、`audit_report_md_path`、`audit_report_md_sha256`，确保连续导出三种格式不会互相覆盖审计报告，也能证明导出命令、策略版本、输出文件和审计报告之间的绑定关系。
- `audit_report.md` 必须包含本次导出的样本数量、`training_eligibility` 分布、失败审计项分布、主要 skipped reason、主要 invalid reason、数据文件路径和 JSON audit report 路径。

阶段四建议拆成两个内部验收门，降低一次性实现风险：

- 阶段四 A：不可降级的训练数据安全最小闭环。必须交付 format-specific export directory、`export_manifest.json`、`audit_report.json`、`audit_report.md`、artifact manifest 校验、formal final verifier 来源校验、`training_eligibility` 强类型映射、hidden field 检查、本机绝对路径检查、loss target 检查、provider raw response 不作为训练目标检查和 `inspect-export --assert-clean`。
- 阶段四 B：增强审计项。继续补齐更深的 secret scanner、legacy metadata 只读推断、preference audit 细项、更完整的人工 Markdown 摘要和统计分布。
- 阶段四 A 未通过时不能进入阶段五。阶段四 B 可以在不改变阶段四 A 安全口径的前提下分 commit 完成。

审计项至少包括：

- `artifact_manifest_valid`：artifact manifest 可解析，所有引用文件存在，sha256 和 size 匹配。
- `artifact_refs_resolve`：导出样本中的 artifact ref 能回到原 run directory。
- `tool_call_pairing_valid`：每个工具调用有终态工具结果。
- `prepared_observation_source_valid`：tool observation 来自当时真实 `PreparedMessages`。
- `loss_targets_valid`：SFT 的 loss target 只覆盖 assistant action，不覆盖 tool observation、system instruction 或 evaluator-only metadata。
- `formal_final_verifier_source_valid`：RL reward 来自 strict patch replay formal final verifier。
- `reward_metadata_present`：正式训练样本必须有 `reward.json` 或对应 manifest-backed reward artifact。
- `hidden_fields_absent`：隐藏字段没有进入导出 payload。
- `hidden_test_feedback_not_visible`：除非 `test_feedback_policy = "oracle_hidden_feedback"`，hidden fail-to-pass 和 pass-to-pass suite 的 accepted、通过比例、通过数量、失败数量和测试名称都没有进入模型可见 transcript、训练 prompt 或训练 target。
- `oracle_feedback_labeled`：如果使用 `oracle_hidden_feedback`，run metadata、metrics、export manifest 和 audit report 必须显式记录 `hidden_feedback_visible_to_model = true`，且该 run 不能被标记为 SWE-Bench-like final-only。
- `oracle_feedback_training_allowed`：`oracle_hidden_feedback` 默认只能导出为 `diagnostic_only`。只有 export policy 显式允许 oracle feedback training，且 oracle 标记完整、审计通过时，样本才可以进入 `trainable`。
- `local_paths_redacted`：导出 payload 中没有本机绝对路径。
- `provider_raw_response_not_target`：provider 原始响应、raw request body 和 reasoning summary 默认不作为任何训练 payload 的内容，包括 SFT loss target、RL rollout payload、trajectory、metadata、preference export、skipped manifest 和训练 prompt 中的 evaluator-only metadata。

`audit_report.json` 契约：

- 顶层字段至少包含 `schema_version`、`export_id`、`format`、`status`、`source_run_dirs`、`data_files`、`generated_at`、`exporter_version`、`summary`、`samples`。
- `status` 建议限制为 `passed`、`passed_with_warnings`、`failed`、`skipped`。
- `summary` 至少包含样本总数、trainable 数量、diagnostic-only 数量、skipped 数量、invalid 数量、审计项失败分布、主要 quality reasons。
- `samples` 中每个样本至少包含 `sample_id`、`data_file`、`line_number`、`run_id`、`task_id`、`training_eligibility`、`filter_status`、`invalid_for_training`、`invalid_reason`、`quality_reasons`、`audit_items`、`artifact_refs`。
- 每个 `audit_items` entry 至少包含 `name`、`status`、`severity`、`reason`、`evidence_ref`。任何 `failed` 必须能映射到 `training_eligibility`、`invalid_reason` 或 `quality_reasons`。
- 对 skipped manifest，例如 `preference_skipped.json`，仍然必须生成 audit report，且 samples 可以为空，但 summary 必须解释 skipped 原因和候选 pair 阻断分布。

训练资格映射规则必须有固定优先级，不能由多个布尔值临时拼接：

| 优先级 | 条件 | `training_eligibility` |
| --- | --- | --- |
| 1 | hidden field 泄漏、hidden test feedback 在非 oracle 模式下进入模型可见内容或训练 payload、本机绝对路径泄漏到训练 payload、artifact manifest invalid、final verifier 缺失、reward 来源非法、formal final verifier 不是 strict patch replay、loss target 覆盖了 tool observation 或 evaluator-only metadata | `invalid` |
| 2 | 任务被 quality gate 跳过、baseline 不合格、dependency failed、flaky baseline、未恢复且导致 run 停止的权限拒绝、策略违规、timeout、preference pair 不足或 compare scope 硬门控阻断 | `skipped` |
| 3 | legacy metadata 不完整、tool schema snapshot 缺失但可审计、provider 或 scaffold 信息只能只读推断、`oracle_hidden_feedback` 未被 export policy 显式允许进入训练、仅适合诊断统计而不适合正式训练 | `diagnostic_only` |
| 4 | 所有核心审计项 `passed`，final verifier 来源合法，artifact ref 可解析，redaction 通过，loss target 合法 | `trainable` |

兼容要求：

- `filter_status` 和 `invalid_for_training` 必须和 `training_eligibility` 保持兼容映射，不能出现 `training_eligibility = invalid` 但 `invalid_for_training = false`。
- warning 不能覆盖 failed check。只要出现优先级 1 条件，样本必须是 `invalid`。
- `diagnostic_only` 可以进入分析报告和统计摘要，但不能进入正式训练 JSONL。
- 权限拒绝不能一律映射为 `skipped`。如果权限拒绝产生终态 `ToolResult`，Agent Loop 继续运行，最终 formal final verifier accepted，且导出审计干净，该轨迹可以保持 `trainable`；未恢复的权限违规、导致停止的权限拒绝或策略违规才进入 `skipped` 或 `diagnostic_only`。
- `oracle_hidden_feedback` 默认不能进入正式训练 JSONL。若 export policy 没有显式设置 `allow_oracle_feedback_training = true`，这类样本必须是 `diagnostic_only`；如果显式允许，则 manifest、audit report 和 export metadata 必须记录该策略版本和理由。

legacy 兼容要求：

- 第一版 run 没有 `run_metadata.json`，导出器可以只读推断已有字段。
- `audit_report.json` 必须记录 `metadata_source = "legacy_inferred"`。
- 无法推断字段写入 `quality_reasons`，不能伪造 provider、scaffold version 或 tool schema snapshot。

测试要求：

- 扩展 `tests/unit/test_export.py`。
- 扩展 `tests/integration/test_export_from_run.py`。
- 增加 artifact manifest 损坏、tool pairing 损坏、hidden field 泄漏、本地路径泄漏、缺失 final verifier 的负例。
- 增加 provider raw response 被误设为 SFT target、RL rollout payload、trajectory、metadata、preference export 或 skipped manifest 内容的负例；同时增加 loss target 覆盖 tool observation、权限拒绝后恢复并 accepted、权限拒绝导致 run 停止的负例和正例。
- 增加基于静态导出 fixture 的污染检查：非 oracle 模式下如果 transcript、training prompt 或 training target 中出现 hidden accepted、fail-to-pass 或 pass-to-pass 反馈，audit 必须失败。运行时策略行为放到阶段七验收，阶段四不要求 Agent Loop 已实现 `test_feedback_policy`。
- 增加连续导出 SFT、RL rollout 和 preference 的测试，断言三次导出的 `exports/<export_id>/export_manifest.json` 和 `exports/<export_id>/audit_report.json` 不会互相覆盖。
- 增加 `preference_skipped.json` 测试，断言 skipped 数据 artifact、manifest 和 audit report 同时存在，并且 manifest 可以解释 skipped 原因。
- 断言导出目录中同时存在目标数据文件、`export_manifest.json`、`audit_report.json` 和 `audit_report.md`。
- 新增或扩展导出检查命令，例如：

```text
repo-harness inspect-export <export_dir> --assert-clean
repo-harness inspect-export <exports_dir> --all --assert-clean
repo-harness inspect-export <export_dir> --require-trainable-samples
```

这个命令至少断言 manifest 可解析、数据文件存在、sha256 匹配、audit report 可解析、Markdown 摘要存在且引用同一个 JSON audit report、没有 `invalid` 样本进入正式训练文件、没有本机绝对路径或 hidden field 出现在训练 payload 中。`--all` 模式用于检查某个 run 或 experiment 下所有规范 export directory。`--require-trainable-samples` 用于声明某次导出必须包含至少一个 `trainable` 样本，避免 skipped manifest 干净但被误判为训练数据成功。

验收命令：

```bash
RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)
OUT_DIR="runs/v2-export-audit-$RUN_ID"

PATH=.venv/bin:$PATH repo-harness run-batch \
  --config tests/fixtures/run_configs/batch_replay.yaml \
  --output-dir "$OUT_DIR"

PATH=.venv/bin:$PATH repo-harness export "$OUT_DIR" --format sft_jsonl
PATH=.venv/bin:$PATH repo-harness export "$OUT_DIR" --format rl_jsonl
PATH=.venv/bin:$PATH repo-harness export "$OUT_DIR" --format preference_jsonl

PATH=.venv/bin:$PATH python -m pytest tests/unit/test_export.py
PATH=.venv/bin:$PATH python -m pytest tests/integration/test_export_from_run.py
PATH=.venv/bin:$PATH repo-harness inspect-export "$OUT_DIR/exports" --all --assert-clean
PATH=.venv/bin:$PATH repo-harness inspect-export "$OUT_DIR/exports" --all --format sft_jsonl --require-trainable-samples
```

本阶段不做的事情：

- 不实现 preference pair 硬门控。
- 不改写旧 run directory。

## 阶段五：preference pair 硬门控和 compare scope

目标：防止同一 task id 但不同环境、不同工具协议、不同 verifier、不同 scaffold、不同模型参数的 run 被误配成偏好训练样本。

建议改动：

- 新增 `src/repo_harness/export/pairing.py`。
- 在 `export_preference_jsonl` 中使用 `PairingPolicy` 和 `CompareScope`。
- 对每个候选 pair 记录：
  - `pairing_policy_version`
  - `compare_scope`
  - `blocked_reasons`
  - chosen/rejected 的 run metadata 摘要
  - chosen/rejected 的 verifier、reward、预算、模型和 scaffold 条件

默认阻断配对的字段：

- task id、task version、base commit、source archive hash。
- environment spec hash、dependency state policy、execution mode。
- verifier name、verifier version、reward formula version、final verifier mode。
- tool schema snapshot hash、tool order、tool parser version、tool result format version。
- context policy version、prompt template version、export policy version。
- scaffold id、scaffold version、allowed tools policy、phase policy。
- model provider、model id、temperature、max output tokens。
- turn budget、tool budget、test budget、task timeout。

canonical compare key 要求：

- 默认 canonical compare key 应包含 task id、task version、base commit、source archive hash、environment spec hash、verifier、reward formula、tool schema snapshot、context policy、prompt template、export policy、scaffold、model provider、model id、temperature、max output tokens 和预算。
- `rollout_index` 不进入 canonical compare key，只用于标识同一条件下的第几次采样。
- `seed` 默认作为受控采样变量处理。只要 provider、model、temperature、工具协议、预算和 verifier 等 canonical 字段一致，不同 seed 的 rollout 可以进入同条件候选池。只有在实验配置把 seed 标记为必须一致时，seed 才进入 canonical compare key。
- compare scope 必须把哪些字段属于 canonical key、哪些字段属于 controlled sampling variables、哪些字段属于 experimental variables 写入 manifest。

最低实现顺序：

- 阶段五必须可以在没有 `ExperimentConfig` 的情况下工作。此时使用内置 strict compare scope，只有所有硬门控字段一致时才允许配对。
- 命令行或导出配置可以显式传入 compare scope 文件，用于提前测试跨 scaffold 对比，但该文件必须记录在 `export_manifest.json` 中。
- 阶段六完成后，`ExperimentConfig.compare_scope` 成为推荐入口，并且 experiment manifest 必须记录每个实验变量如何影响 preference pair。

允许的跨条件对比：

- 只有 `ExperimentConfig` 或导出配置显式声明某个字段是实验变量时，才允许跨该字段配对。
- preference pair 必须区分两种用途：
  - 训练数据配对：默认使用 strict compare scope。model provider、model id、temperature、scaffold、预算、工具协议、verifier 和 source checkout 都必须一致。`seed` 和 `rollout_index` 默认是受控采样变量，除非 compare scope 显式要求一致。
  - 实验分析配对：可以显式允许跨 scaffold、跨模型或跨采样参数对比，但 manifest 必须标记 `training_export_allowed = false` 或等价状态，除非对应 experimental variable 已通过训练数据审计。
- 例如比较 `simple_react` 和 `single_shot_patch` 时，`scaffold id` 可以进入 `compare_scope.experimental_variables`，但 verifier、task version、base commit、工具协议和预算仍应一致。默认情况下这类 pair 先用于实验分析，不直接进入正式偏好训练数据。

输出要求：

- 如果没有可配对 run，继续输出稳定的 skipped manifest。
- skipped manifest 应包含候选 run 数量、被阻断 pair 数量和主要阻断原因分布。
- `audit_report.json` 中应记录 preference pair 是否满足 pairing policy。

blocked reason 必须使用枚举值，至少包含：

- `compare_key_mismatch`
- `missing_reward`
- `reward_tie`
- `missing_formal_final_verifier`
- `non_formal_reward_source`
- `artifact_manifest_invalid`
- `tool_schema_snapshot_mismatch`
- `context_policy_mismatch`
- `budget_mismatch`
- `experimental_variable_not_training_approved`

测试要求：

- 同一 task、同一条件、不同 reward 的两个 run 可以配对。
- 同一 task、不同 base commit 阻断。
- 同一 task、不同 tool schema snapshot 阻断。
- 同一 task、不同 scaffold 默认阻断，除非 compare scope 显式允许。
- 不同 seed、相同 canonical compare key 的同任务多 rollout 可以进入候选池。
- reward 相等、reward 缺失、final verifier 非正式来源时必须产生枚举化 blocked reason。
- legacy run 缺失关键字段时默认不进入正式 preference pair，可以进入 diagnostic report。

验收命令：

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_export.py
PATH=.venv/bin:$PATH python -m pytest tests/integration/test_export_from_run.py
```

本阶段不做的事情：

- 不实现多 rollout runner。
- 不生成新的 run，只处理已有 run 的导出配对。

## 阶段六：ExperimentConfig 最小多 rollout 运行器和实验报告

目标：先让 RepoHarness 可以用一个实验配置描述同一任务的多次 rollout，并生成可复盘实验 manifest。阶段六只要求 `simple_react` 单 scaffold 的最小实验运行器；跨 scaffold 对比必须等阶段七的 scaffold registry 和阶段八、阶段九的新增 scaffold 完成后再放开。

建议改动：

- 新增或扩展 `src/repo_harness/evaluation/experiment.py`。
- 新增 `ExperimentConfig` 加载入口。
- 新增命令：

```text
repo-harness run-experiment --config <experiment_config> [--output-dir <dir>]
repo-harness inspect-experiment <experiment_dir> [--assert-minimums <threshold_config>]
```

如果希望减少命令数量，也可以让 `run-batch` 识别 `kind: experiment` 配置。但是实施计划建议使用 `run-experiment`，避免把第一版 `RunConfig.tasks` 的顺序批量语义变复杂。

ExperimentConfig 在阶段六至少表达：

- task 列表。
- rollout count。
- replay provider config。
- 单一 `simple_react` scaffold config。
- budgets。
- permission mode。
- output dir。
- run id naming policy。
- compare scope。
- 是否生成 aggregate report。
- 是否自动尝试 preference export。

阶段六的明确限制：

- 阶段六只承诺 replay provider。fake provider 需要等待阶段七的最小 `ModelClient` protocol 和 replay/fake factory 完成后再接入实验运行器。
- 多 scaffold config 可以先通过 schema 表达，但运行器必须拒绝阶段七之前未注册或未迁移的 scaffold。
- 多模型真实 provider 对比只记录 schema 方向，不在阶段六验收；真实 provider 接入在阶段十一。
- preference export 可以使用阶段五的 strict compare scope 生成或稳定 skipped，但不能把跨 scaffold、跨模型 pair 当成正式训练数据。

运行产物：

- `experiment_manifest.json`
- `experiment_summary.md`
- `aggregate_metrics.json`
- 每个 run 仍然使用独立 run directory。

`inspect-experiment --assert-minimums` 在阶段六先使用 smoke 阈值配置，例如 `tests/fixtures/run_configs/v2/experiment_smoke_thresholds.yaml`：

```yaml
min_total_runs: 2
min_recorded_runs: 2
require_experiment_manifest: true
require_aggregate_metrics: true
require_failure_records: true
require_no_all_skipped_success: true
```

阶段六的 smoke 阈值只验证实验入口、manifest、run id、聚合指标和失败记录逻辑。完整的第二版任务数量阈值必须留到阶段十三和最终验收使用 `tests/fixtures/run_configs/v2/task_set_thresholds.yaml` 检查，不能在阶段六提前要求 20 个任务。

运行策略：

- 第二版先保持顺序运行，`concurrency` 继续默认为 1。
- 每个 run 必须继续通过现有 `run_task` 或等价内部函数，不能绕过 Eval Runner。
- run id 必须包含 task id、model alias、scaffold id、rollout index，避免同名覆盖。
- 单个 run 失败不能破坏整个实验 manifest 写出；失败记录必须结构化。

测试要求：

- 增加 CLI parser 测试，覆盖 `run-experiment` 和 `inspect-experiment --assert-minimums`。
- 使用 replay provider 和 `simple_react` 跑同一任务两次，生成两个 run directory 和一个 `experiment_manifest.json`。
- 断言 run id 稳定。
- 断言 experiment manifest 记录模型、scaffold、rollout index 和 run outcome。
- 断言某个 run 抛出 RepoHarnessError 时，实验 manifest 仍记录 error。
- 断言阈值不足时 `inspect-experiment --assert-minimums` 失败，阈值满足时成功。

验收命令：

```bash
RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)
EXP_DIR="runs/v2-experiment-smoke-$RUN_ID"

PATH=.venv/bin:$PATH repo-harness run-experiment \
  --config tests/fixtures/run_configs/v2/experiment_smoke.yaml \
  --output-dir "$EXP_DIR"

PATH=.venv/bin:$PATH python -m pytest tests/unit/test_experiment_config.py
PATH=.venv/bin:$PATH python -m pytest tests/integration/test_experiment_runner.py
PATH=.venv/bin:$PATH repo-harness inspect-experiment "$EXP_DIR" \
  --assert-minimums tests/fixtures/run_configs/v2/experiment_smoke_thresholds.yaml
```

本阶段不做的事情：

- 不引入并发调度器。
- 不实现异步 rollout service。
- 不实现远程 worker。

## 阶段七：最小 `ModelClient` 协议、factory、replay/fake 兼容层和 Scaffold registry

目标：先把模型调用接口和第一版唯一 scaffold 一起迁移到稳定协议上，避免阶段八和阶段九新增 scaffold 后再反向重写模型调用路径。

建议改动：

- 新增 `src/repo_harness/model_client/protocol.py`：
  - 定义 `ModelClient` Protocol 或抽象基类。
  - `generate(request: ModelRequestContext, recorder: RunRecorder) -> ModelResponse`。
- 新增 `src/repo_harness/model_client/factory.py`：
  - 根据 `RunConfig.model.provider` 创建 replay 或 fake provider client。
  - mock provider 和真实 provider 暂不在本阶段实现。
- 修改 `AgentLoop` 类型依赖：
  - 从 `ReplayModelClient` 改为通用 `ModelClient`。
- 修改模型调用组装逻辑：
  - Agent Loop 负责把当前 `PreparedMessages`、turn index、scaffold phase、allowed tool definitions、tool schema snapshot ref、`run_config_facts_ref`、预算状态和请求超时组装成 `ModelRequestContext`。
  - replay/fake client 必须通过 `ModelRequestContext` 工作，不能继续依赖旧的裸 messages 调用路径。
- 重构 `src/repo_harness/scaffolds/`：
  - `schemas.py`
  - `registry.py`
  - `simple_react.py`
  - `policies.py`
- 定义 `ScaffoldDefinition` 或等价协议：
  - `scaffold_id`
  - `scaffold_version`
  - `prompt_fragment`
  - `allowed_tools_policy`
  - `phase_transition_policy`
  - `default_stop_policy`
  - `default_test_feedback_policy`
  - `default_feedback_tests_passed_policy`
  - `allows_final_answer_without_tool`
  - `allows_feedback_verifier_repair`
- 扩展 `RuntimeConfig`：
  - 新增 `test_feedback_policy`。
  - 取值为 `disabled`、`public_only`、`structured_public_feedback`、`oracle_hidden_feedback`。
  - 新增 `feedback_tests_passed_policy`。
  - 取值为 `stop_immediately`、`require_model_final`、`continue`。
  - scaffold 只提供默认值；runtime config 可以显式覆盖 scaffold default。
- `test_feedback_policy` 的最终生效顺序为：`RunConfig.runtime.test_feedback_policy` 显式值优先，其次是 `ScaffoldDefinition.default_test_feedback_policy`，最后才使用 task style 默认值。SWE-Bench-like task 默认 `disabled`，普通 repository-style task 可以默认 `public_only`。
- `feedback_tests_passed_policy` 的最终生效顺序为：`RunConfig.runtime.feedback_tests_passed_policy` 显式值优先，其次是 `ScaffoldDefinition.default_feedback_tests_passed_policy`，最后才使用 provider kind 默认值。
  - 如果 resolved `test_feedback_policy = "disabled"`，resolved `feedback_tests_passed_policy` 必须记录为 `not_applicable` 或等价状态，不能触发 Agent Loop 停止行为。
  - `not_applicable` 是解析后的事实状态，不是用户可配置枚举值；用户在 run config 中直接写 `feedback_tests_passed_policy = "not_applicable"` 必须 schema validation fail。
  - replay 默认保留 `stop_immediately`，用于第一版回归和低成本确定性评测。
  - 真实 provider 推荐默认值为 `require_model_final`，让模型在 feedback verifier accepted 后至少获得一轮机会输出 final answer、检查 `git_diff` 或进行收尾判断。
- 修改 `ContextBuilder`：
  - system prompt 不再写死 `simple_react agent`。
  - scaffold 只提供 prompt fragment 和策略信息。
  - Context Builder 仍然负责最终初始 messages、可见性隔离和版本记录。
- 修改 `AgentLoop`：
  - 构造函数接受通用 scaffold definition。
  - final answer 判断、allowed tools、phase transition 和 stop policy 通过 scaffold policy 生效。
  - 不再硬编码 `run_tests accepted` 后必停。
  - `agent_stop_reason = "feedback_tests_passed"` 只允许在 `feedback_tests_passed_policy = "stop_immediately"` 时出现。
  - `require_model_final` 下，feedback verifier accepted 后必须把结果作为下一轮模型可见反馈回流，并消费 replay script 中的 final answer 或真实 provider 的下一次响应。
  - `continue` 下，feedback verifier accepted 只是一条普通 tool observation，停止由模型、预算、超时和 scaffold stop policy 决定。
  - `test_feedback_policy = "disabled"` 时，`run_tests` 不能出现在模型可见 allowed tools 中；formal final verifier 仍然必须在 agent 停止后运行。
  - `test_feedback_policy = "disabled"` 时，模型也不能通过 `bash` 绕过测试反馈策略运行 `pytest`、`python -m pytest`、`tox`、`nox` 或任务 test command。此类命令必须按现有工具设计路由到 `run_tests` 策略检查，或者被 shell command policy 拒绝并生成终态 `ToolResult`。
  - `test_feedback_policy = "disabled"` 时，不会产生模型可见的 feedback verifier accepted event，`agent_stop_reason = "feedback_tests_passed"` 必须被 schema 或运行时断言拒绝。
  - `public_only` 和 `structured_public_feedback` 只能运行公开测试或任务显式声明为 model-visible 的 smoke tests，不能运行 hidden fail-to-pass 或 pass-to-pass suite。
  - `oracle_hidden_feedback` 才允许 `run_tests` 运行 evaluator-only 测试并返回 accepted、fail-to-pass、pass-to-pass 等结构化隐藏反馈。
- 修改 `Eval Runner`：
  - 根据 `run_config.runtime.scaffold_id` 从 registry 获取 scaffold。
  - 把 scaffold 传给 Context Builder 和 Agent Loop。
  - 在 run metadata 中记录 scaffold default、runtime override、resolved `test_feedback_policy` 和 resolved `feedback_tests_passed_policy`。
  - 把 scaffold facts 写入 `run_metadata.json`。

行为要求：

- `simple_react` 行为与第一版兼容。
- 不支持的 scaffold id 必须在配置加载或 run 开始前报清晰错误。
- allowed tools policy 必须真实限制工具集合，而不仅记录 metadata。
- ReplayModelClient 和 FakeModelClient 的外部行为与第一版兼容，但内部通过新的 `ModelClient` protocol 被调用。
- metrics 增加 `feedback_verifier_accepted`、`first_feedback_accept_turn`、`first_feedback_accept_ref` 和 `feedback_tests_passed_policy`。
- metrics 增加 `test_feedback_policy`、`hidden_feedback_visible_to_model`、`public_tests_ran`、`hidden_feedback_ran`。
- SFT 导出必须能保留 `require_model_final` 下测试通过后的 final answer；RL rollout 必须保留 `continue` 下测试通过后继续修改导致回归的负样本轨迹。

测试要求：

- ReplayModelClient 和 FakeModelClient 现有测试继续通过。
- `ModelClient` factory 可以构造 replay 和 fake client。
- Agent Loop 通过 `ModelRequestContext` 调用模型，并记录 `model_call_id`、turn、scaffold phase 和 budget state。
- 当前 replay 成功、失败、权限拒绝、未知工具、schema 错误测试继续通过。
- 覆盖三种 `feedback_tests_passed_policy`：
  - `stop_immediately`：保持第一版 replay 行为，`run_tests accepted` 后停止。
  - `require_model_final`：`run_tests accepted` 后继续一轮并消费 replay script 中的 final answer。
  - `continue`：`run_tests accepted` 作为普通反馈，后续修改如果导致 final verifier 失败，RL rollout 中保留负样本轨迹。
- 覆盖四种 `test_feedback_policy`：
  - `disabled`：`run_tests` 不在 allowed tools 中，agent 停止后仍运行 formal final verifier。
  - `disabled` 与 `stop_immediately` 或 `require_model_final` 组合时，resolved feedback-tests-passed policy 为 not applicable，不能触发 `feedback_tests_passed` stop reason。
  - `disabled` 下模型通过 `bash` 请求测试命令时，不能绕过策略获得测试反馈。
  - `public_only`：`run_tests` 只运行公开测试，模型可见输出不含 hidden accepted、fail-to-pass 或 pass-to-pass 计数。
  - `structured_public_feedback`：返回结构化公开测试摘要，但不含 hidden suite 统计。
  - `oracle_hidden_feedback`：允许隐藏反馈，但 run metadata 和 export metadata 必须标记 oracle feedback。
- `ContextBuilder` 的 system prompt 不再含有固定 `simple_react agent` 语义。
- `run_metadata.json` 中有 `scaffold_id` 和 `scaffold_version`。
- 构造一个测试 scaffold 限制工具集合，验证被禁止工具不能执行。

验收命令：

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_replay_model.py tests/unit/test_fake_model.py
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_model_client_factory.py
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_context_builder.py tests/unit/test_agent_loop_protocol.py
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_feedback_tests_passed_policy.py
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_test_feedback_policy.py
PATH=.venv/bin:$PATH python -m pytest tests/integration/test_agent_loop_replay.py
```

本阶段不做的事情：

- 不实现 `single_shot_patch`。
- 不实现 planner-coder-verifier。
- 不实现 mock provider 或真实外部 provider。

## 阶段八：`single_shot_patch` scaffold

目标：实现低成本 baseline，使同一任务可以比较“一次性补丁输出”和多轮工具使用的差异。

建议实现方式：

- 新增 `src/repo_harness/scaffolds/single_shot_patch.py`。
- 新增 patch action parser，例如 `src/repo_harness/scaffolds/patch_action.py`。
- 扩展 replay script schema，允许 replay model 提供 patch action 或 assistant content 中的 fenced diff。
- Harness 内部应用 patch，生成结构化 patch apply result。
- `single_shot_patch` 不允许中间 `run_tests` 反馈。
- `single_shot_patch` 的 effective `test_feedback_policy` 必须为 `disabled`。如果 runtime config 显式请求其他值，默认必须 schema validation fail；第二版不做自动降级，避免同一实验配置产生不可比轨迹。
- 应用补丁后仍然由 Eval Runner 冻结 `final.patch`，并执行 strict patch replay final verifier。

关键边界：

- 不把 `apply_patch` 作为所有 scaffold 的普通模型可见工具。
- patch 应用是 `single_shot_patch` scaffold 的内部能力或等价结构化 action。
- patch apply 失败必须生成模型可见失败结果或 run 失败事件，不能静默失败。
- single-shot 运行仍然写 transcript、events、artifacts、metrics、summary 和 run metadata。

事件建议：

- `patch_action_parsed`
- `patch_action_parse_failed`
- `patch_apply_started`
- `patch_apply_completed`
- `patch_apply_failed`

测试要求：

- 单个 replay patch action 可以修复一个 fixture task。
- patch apply 失败产生结构化 failure。
- `single_shot_patch` 中模型请求 `run_tests` 时被 scaffold policy 阻断或标记为 invalid action。
- 导出 metadata 能证明 `single_shot_patch` 没有中间 `run_tests` feedback。

验收命令：

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_scaffold_single_shot_patch.py
PATH=.venv/bin:$PATH python -m pytest tests/integration/test_single_shot_patch.py
```

本阶段不做的事情：

- 不实现复杂 patch 纠错循环。
- 不实现 tree search 或多候选 patch 排序。

## 阶段九：`planner_coder_verifier` scaffold 计划内增强

目标：实现顺序式多阶段 scaffold，用于比较更结构化的 planning、coding 和 verifier-feedback 使用方式。本阶段是第二版计划内增强目标，不作为第二版最小完成的必需条件；如果延期，必须在最终验收中明确标记为 deferred enhancement，并说明未进入最小完成统计。这里的 planner、coder、verifier 是同一个 Agent Loop 内的阶段化策略角色，不是后台多智能体系统。

建议改动：

- 新增 `src/repo_harness/scaffolds/planner_coder_verifier.py`。
- 在 scaffold policy 中定义 phases：
  - `planner`
  - `coder`
  - `verifier`
  - `repair`
  - `final`
- Agent Loop 记录 phase transition event。
- Context Manager 或 Agent Loop 在每轮模型调用时把当前 phase metadata 放入 provider-ready messages。
- allowed tools policy 按 phase 生效：
  - planner：默认只允许 `list_files`、`read_file`、`grep`、`git_diff`。
  - coder：允许编辑类工具和必要诊断工具。
  - verifier：允许 `run_tests`，读取反馈并决定是否进入 repair。
  - repair：允许编辑类工具和 `run_tests`，但仍受 test budget 限制。
- verifier 和 repair phase 是否真的暴露 `run_tests`，以及 `run_tests` 返回公开测试摘要还是 oracle hidden feedback，仍然由 resolved `test_feedback_policy` 控制。

关键边界：

- verifier role 是模型策略角色，不等于系统 Verifier 模块。
- 不启动后台子代理。
- 不创建 agent-to-agent mailbox。
- 不创建额外 worktree。
- 所有 phase 共享同一个 Agent Loop、Tool System、Workspace Adapter、Verifier 和 RunRecorder。

测试要求：

- replay script 可以按 planner -> coder -> verifier -> final 路径完成任务。
- phase transition 写入 events。
- planner phase 试图调用 `edit_file` 时被 scaffold policy 阻断。
- verifier phase 的 `run_tests` 仍然只是 feedback verifier，不改变 final verifier 的正式地位。
- run metadata 和 export metadata 记录 scaffold id、scaffold version 和 phase policy。

验收命令：

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_scaffold_planner_coder_verifier.py
PATH=.venv/bin:$PATH python -m pytest tests/integration/test_planner_coder_verifier.py
```

本阶段不做的事情：

- 不实现后台多代理。
- 不实现远程代理。
- 不实现复杂团队协作。

## 阶段十：mock provider、provider artifact 和 provider 错误分类

目标：在阶段七已经完成最小 `ModelClient` 协议、factory 和 replay/fake 兼容层之后，用 mock provider 覆盖真实 provider 接入前的协议风险。

建议改动：

- 在 `src/repo_harness/model_client/schemas.py` 中补充 `provider` 字段到 `ModelCallEvent`。
- 修改 `Eval Runner`：
  - 通过阶段七的 factory 创建 mock provider client。
  - 保留 replay 和 fake provider 的旧行为和错误提示。
- 新增 mock provider：
  - 可以是 `MockProviderClient`，也可以是本地 mock HTTP server。
  - 测试 provider request 构造、response 解析、tool call parser、错误分类、原始请求响应 artifact、脱敏策略。

mock provider 必须覆盖：

- 成功 assistant tool call。
- final answer。
- malformed tool call。
- invalid response。
- context limit。
- provider timeout。
- rate limit。
- auth error。

artifact 要求：

- raw provider request 和 response 必须写 artifact。
- artifact metadata 记录 redaction status 和 retention policy。
- 凭证和 authorization header 不能进入 artifact 明文。
- 新增 `mock_provider_smoke_report.json`，至少记录 `status`、`provider`、`run_dir`、`final_verifier_status`、`model_error_type`、`export_audit_status`、`checked_at` 和 raw artifact redaction 检查结果，供阶段十五全局 V2 acceptance report 引用。

测试要求：

- ReplayModelClient 所有现有测试继续通过。
- mock provider 单元测试覆盖 request/response。
- mock provider 集成测试至少跑通一个端到端 task。
- provider error 不应被记成普通模型任务失败，而应有 `model_error_type`。
- 单元测试必须断言 provider adapter 从 `ModelRequestContext` 中读取 tool schema snapshot、generation config、scaffold phase、provider options、tool choice、request timeout 和 raw request logging policy，而不是重新从全局状态或 prompt 文本中反推。

验收命令：

```bash
RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)
MOCK_DIR="runs/v2-mock-provider-smoke-$RUN_ID"

PATH=.venv/bin:$PATH repo-harness run-task \
  tests/fixtures/tasks/task_001.yaml \
  --config tests/fixtures/run_configs/v2/mock_provider_smoke.yaml \
  --output-dir "$MOCK_DIR"

PATH=.venv/bin:$PATH repo-harness export "$MOCK_DIR" --format sft_jsonl
PATH=.venv/bin:$PATH repo-harness export "$MOCK_DIR" --format rl_jsonl
PATH=.venv/bin:$PATH repo-harness inspect-export "$MOCK_DIR/exports" --all --assert-clean
PATH=.venv/bin:$PATH repo-harness inspect-export "$MOCK_DIR/exports" --all --format sft_jsonl --require-trainable-samples
PATH=.venv/bin:$PATH repo-harness inspect-export "$MOCK_DIR/exports" --all --format rl_jsonl --require-trainable-samples
PATH=.venv/bin:$PATH repo-harness inspect-mock-provider-smoke \
  --run-dir "$MOCK_DIR" \
  --output "$MOCK_DIR/mock_provider_smoke_report.json" \
  --assert-accepted \
  --assert-export-clean

PATH=.venv/bin:$PATH python -m pytest tests/unit/test_model_client_factory.py tests/unit/test_mock_provider.py
PATH=.venv/bin:$PATH python -m pytest tests/integration/test_mock_provider_e2e.py
```

本阶段不做的事情：

- 不调用真实外部 provider。
- 不引入复杂重试调度器。

## 阶段十一：真实 provider 最小接入、provider 错误路径和 smoke report

目标：接入至少一个真实模型 provider，以验证非脚本化模型响应下 harness 是否稳定。

实现前置要求：

- 当前阶段开始前必须已经完成最小 ModelClient protocol、factory、mock provider、provider error taxonomy 和 raw request/response artifact。
- 选择具体 provider 时，必须查阅该 provider 的官方文档，不能把第三方博客或过时记忆作为请求格式依据。
- 实施日志必须记录 provider 名称、使用的 API 或兼容接口版本、官方文档 URL、检查日期、请求格式关键约束和错误码映射依据。
- 默认优先使用 Python 标准库或项目已有 HTTP 客户端实现最小 adapter，避免为了一个 smoke test 引入大依赖。如果决定引入官方 SDK，必须在 implementation log 中说明原因、版本约束、锁文件变化和替代方案。

建议改动：

- 新增一个 provider adapter，例如：
  - `src/repo_harness/model_client/providers/openai_compatible.py`
  - 或 `src/repo_harness/model_client/providers/<provider_name>.py`
- 扩展现有 `ProviderCredentialPolicy`，不新增第二套 credential policy 名称：
  - 默认只从环境变量读取密钥。
  - 缺少凭证时返回结构化 skip 或测试跳过，不产生假成功。
  - 不把认证 header、token 或本地密钥路径写入导出样本。
- provider adapter 只负责：
  - RepoHarness messages -> provider request。
  - provider response -> `ModelResponse`。
  - provider error -> `model_error_type`。
  - provider token usage -> `ModelCallEvent`。
  - raw request/response 脱敏 artifact。
- provider artifact 导出审计：
  - mock provider 和真实 provider run 生成 raw request/response artifact 后，必须再运行 export 和 `inspect-export --all --assert-clean`。
  - 审计必须证明 provider 原始响应、reasoning summary 和 raw request body 没有进入 SFT loss target，也没有进入 RL rollout payload、trajectory、metadata、preference export、skipped manifest 或训练 prompt 中的 evaluator-only metadata。
- 新增 `real_provider_smoke_report.json`：
  - `status`：`skipped_no_credentials`、`accepted_with_credentials`、`failed_with_credentials`、`provider_error`。
  - `provider`。
  - `credential_state`。
  - `skip_reason`。
  - `run_dir`。
  - `final_verifier_status`。
  - `model_error_type`。
  - `checked_at`。
  - `docs_ref`。

真实 provider 验收分三层：

1. 无密钥环境：
   - mock provider 测试必须稳定通过。
   - 真实 provider smoke test 可以 skip，但必须写 `real_provider_smoke_report.json`，并记录结构化 skip reason。
2. 有密钥环境：
   - 至少一个固定小任务完成端到端 `run-task`。
   - final verifier 必须 accepted。
   - 如果凭证存在但 smoke test skip，不能算通过。
3. 错误路径：
   - auth error、rate limit、invalid response、tool call parse failure、context limit、provider timeout、provider error 都通过 mock 或可控测试覆盖。

reasoning 内容策略：

- 如果 provider 只返回 reasoning token usage，只记录用量。
- 如果 provider 返回 reasoning summary，默认保存为非训练目标 artifact，并标记 `export_allowed = false`，除非后续策略明确允许。
- 隐藏思考内容默认不进入训练导出。

测试要求：

- `tests/unit/test_provider_client.py`
- `tests/integration/test_real_provider_smoke.py`
- 真实 provider smoke test 必须在没有凭证时 skip，不能失败。
- 有凭证时至少跑一个小任务并 accepted。
- 断言 `real_provider_smoke_report.json` 在无凭证、有凭证 accepted 和 provider error 路径下都符合 schema。
- 无凭证路径也必须产生固定路径的 `real_provider_smoke_report.json`，不能只依赖 pytest skip 结果。
- provider 文档记录测试或静态检查应确认 implementation log 中存在 provider、文档 URL 和检查日期，避免真实 provider 接入依据不可追溯。

新增或扩展机器检查命令：

```text
repo-harness inspect-real-provider-smoke --report <real_provider_smoke_report.json> --allow-skip-without-credentials --require-accepted-with-credentials
```

该命令必须读取报告中的 `credential_state` 和 `status`。如果没有凭证，允许 `status = "skipped_no_credentials"`，但报告文件必须存在且 skip reason 结构化；如果存在凭证，`status = "skipped_no_credentials"` 不能通过，必须是 accepted 或清晰失败。

验收命令：

```bash
RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)
REAL_PROVIDER_DIR="runs/v2-real-provider-smoke-$RUN_ID"
REAL_PROVIDER_REPORT="$REAL_PROVIDER_DIR/real_provider_smoke_report.json"

PATH=.venv/bin:$PATH python -m pytest tests/unit/test_provider_client.py
REAL_PROVIDER_SMOKE_DIR="$REAL_PROVIDER_DIR" \
REAL_PROVIDER_SMOKE_REPORT="$REAL_PROVIDER_REPORT" \
  PATH=.venv/bin:$PATH python -m pytest tests/integration/test_real_provider_smoke.py
PATH=.venv/bin:$PATH repo-harness inspect-real-provider-smoke \
  --report "$REAL_PROVIDER_REPORT" \
  --allow-skip-without-credentials \
  --require-accepted-with-credentials
```

如果 `real_provider_smoke_report.json` 的 `status = "accepted_with_credentials"`，还必须对报告中的 `run_dir` 运行导出审计：

```bash
PATH=.venv/bin:$PATH repo-harness export <real_provider_run_dir> --format sft_jsonl
PATH=.venv/bin:$PATH repo-harness export <real_provider_run_dir> --format rl_jsonl
PATH=.venv/bin:$PATH repo-harness inspect-export <real_provider_run_dir>/exports --all --assert-clean
PATH=.venv/bin:$PATH repo-harness inspect-export <real_provider_run_dir>/exports --all --format sft_jsonl --require-trainable-samples
PATH=.venv/bin:$PATH repo-harness inspect-export <real_provider_run_dir>/exports --all --format rl_jsonl --require-trainable-samples
```

本阶段不做的事情：

- 不实现 provider 多路 fallback。
- 不实现成本优化调度。
- 不声称已经验证工业级长轨迹智能体能力。

## 阶段十二：repo materialization、命令环境策略门和任务来源扩展

目标：让任务来源不再只局限于 fixture repository，同时在任务集扩展前先收紧 setup/test command、environment spec 和 verifier parser 策略，保持 source checkout 可审计、可哈希、可复现。

建议改动：

- 在开始 repo materialization 前，复用并扩展阶段一已经定义的最小 workspace facts，避免任务来源逻辑直接绑定 local process：
  - `SourceCheckout`
  - `SourceCheckoutFacts`
  - `WorkspaceBackend`
  - `WorkspaceAdapter`
  - `WorkspacePaths`
  - `WorkspaceExecutionFacts`
- 命名必须统一：`SourceCheckout` 是代码里的 materialization 结果对象，`SourceCheckoutFacts` 是写入 `run_config_facts.json`、最终 `run_metadata.json` 和 export metadata 的序列化事实对象。后续阶段不能再新增含义重叠的 `SourceCheckoutInfo`、`SourceFacts` 等别名。
- `SourceCheckout` / `SourceCheckoutFacts` 只描述已经 materialize 完成的源码快照事实，包括 checkout root、source tree hash、base commit 或 synthetic base id、source kind、decontamination status、decontamination metadata ref 和 archive hash。
- 阶段十二应复用阶段一已经定义的 `WorkspaceBackend` 和 `WorkspaceAdapter`，只扩展 materialization 需要的新字段。不能在本阶段重新定义一套不兼容的 workspace protocol。
- 扩展 `src/repo_harness/tasks/schemas.py`：
  - `RepoSource`
  - `LocalArchiveSource`
  - `LocalRepositorySource`
  - `PublicSnapshotSource`
  - `RepoMaterializationResult`
- 扩展 `src/repo_harness/tasks/adapter.py`：
  - 支持旧版 `repo: ../repos/...` fixture path。
  - 支持本地归档。
  - 支持受控本地仓库副本。
  - 为公开仓库快照保留 schema，但第二版可以先要求预下载 archive，不主动联网抓取。
- 新增 `src/repo_harness/workspace/materialization.py` 或在 Workspace Adapter 中增加清晰接口：
  - `materialize_source(task) -> SourceCheckout`
- Task Adapter 只负责解析和校验 task source specification，不直接创建 agent workspace、不执行 setup、不绕过 Workspace Adapter。真正的 source materialization 必须由 `workspace/materialization.py` 或 `WorkspaceAdapter` 完成，并返回阶段一已经定义的 `SourceCheckoutFacts`。

三类来源必填字段：

- 本地归档：
  - archive path
  - archive sha256
  - 解包后 source tree hash
  - expected root directory
  - base commit 或 synthetic base id
- 本地仓库副本：
  - source path
  - 当前 commit
  - working tree clean 状态
  - source tree hash
  - 是否允许未提交文件进入任务快照
- 公开仓库快照：
  - remote URL
  - commit sha
  - 下载或镜像来源
  - archive sha256
  - decontamination status
  - decontamination metadata ref
  - 是否移除了 remotes、branches、tags

边界要求：

- 正式 agent workspace 必须来自可审计 source checkout，不能直接在用户原始仓库目录中运行。
- 默认移除或屏蔽 Git remotes、branches、tags，防止模型通过 Git 历史或远程泄漏答案。
- source hash、base commit、decontamination status 必须进入 run metadata 和 export metadata。
- 完整 decontamination metadata 只能进入 run metadata、audit report 的非训练事实区，或作为受控 artifact 被引用。训练 JSONL payload 只能包含 `decontamination_status` 或脱敏摘要，不能直接嵌入完整 decontamination metadata。

任务集扩展前置策略门：

- 新增或扩展 `CommandPolicy`，把 setup command、test command 和模型通过 `bash` 请求的命令分开校验。
- `SetupCommandPolicy` 至少记录 allowlist、是否允许网络、超时、工作目录、环境变量白名单和依赖安装策略。
- `TestCommandPolicy` 至少记录公开测试命令、隐藏 formal verifier 命令、是否允许模型可见执行、以及和 `test_feedback_policy` 的映射关系。模型通过 `bash` 请求 `pytest`、`python -m pytest`、`tox`、`nox` 或任务 test command 时，必须先经过这个策略，不能绕过阶段七的测试反馈可见性规则。
- 新增或扩展 `EnvironmentSpec`，记录 Python 版本、包管理器、锁文件 hash、setup artifact hash、source archive hash、dependency state ref、environment spec hash 和是否允许 dirty dependency state。
- 新增或扩展 `VerifierParserPolicy`，记录 parser id、parser version、支持的输出格式、置信度、失败映射和低置信阻断策略。
- 阶段十三开始前必须有独立验收证明：命令策略能拒绝未授权 setup/test command，环境规格 hash 稳定，pytest 输出和至少一种非 pytest 输出可以被解析，低置信 parser 会阻断任务质量门。

测试要求：

- 旧 fixture task 仍然可用。
- 本地归档可以 materialize 并验证 hash。
- 本地仓库副本在 dirty 且未允许 dirty snapshot 时被拒绝。
- 公开仓库快照 schema 可以校验，但不默认联网下载。
- 增加 materialization smoke：本地归档或本地仓库副本 materialize 后运行一个 replay task，并断言 source facts 进入 `run_metadata.json` 和 export metadata。
- 增加命令策略负例：setup command 不在 allowlist、模型通过 `bash` 直接请求隐藏 test command、`test_feedback_policy = "disabled"` 下请求 pytest，都必须被拒绝或路由到受控 `run_tests` 策略。
- 增加环境策略测试：相同 source checkout 和依赖状态产生稳定 `environment_spec_hash`，依赖状态变化会进入 run metadata 和 compare scope。
- 增加 verifier parser 策略测试：pytest 解析、非 pytest 解析、低置信 parser 阻断、parser failure 进入 `FailureDiagnostics.failure_type = "environment_setup_failed"` 或更精确枚举。

验收命令：

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_task_adapter.py tests/unit/test_task_schema.py
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_repo_materialization.py
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_command_policy.py tests/unit/test_environment_spec.py
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_verifier_parser_policy.py
PATH=.venv/bin:$PATH python -m pytest tests/integration/test_workspace_lifecycle.py
PATH=.venv/bin:$PATH python -m pytest tests/integration/test_repo_materialization_smoke.py
PATH=.venv/bin:$PATH python -m pytest tests/integration/test_command_environment_policy_gate.py
```

本阶段不做的事情：

- 不实现完整 SWE-Bench 适配。
- 不默认从网络下载公开仓库。

## 阶段十三：任务集扩展到 20 到 50 个 repository-level 或 repository-style task

目标：用更多中小型任务验证 harness 质量，而不是追求公开榜单复现。

任务构成建议：

- 继续保留第一版 micro-repo fixture。
- 增加 Python 小型 repository-level task。
- 增加 terminal-style task，例如命令行脚本、配置错误、导入错误、测试失败。
- 增加 issue-style fixture task，把 issue statement、仓库状态、测试命令和 verifier config 统一成 `TaskDefinition`。
- 暂不承诺完整 SWE-Bench Lite 子集。

最低验收口径：

- 至少 20 个任务通过静态校验。
- 至少 15 个任务通过 setup 和 baseline quality gate，并进入正式 Agent Loop。
- 至少 15 个任务产生 formal final verifier。
- 至少 3 个任务产生 accepted 成功样例。
- invalid、flaky、dependency failed、permission denied、timeout 等类别可以存在，但必须有结构化分布报告。

建议新增：

- `tests/fixtures/tasks/v2/`
- `tests/fixtures/repos/v2/`
- `tests/fixtures/run_configs/v2/`
- `tests/fixtures/replays/v2/`
- `tests/fixtures/run_configs/v2/task_set_thresholds.yaml`

质量门控要求：

- pass-to-pass 初始失败必须阻断。
- dependency install failed 必须阻断。
- parser 低置信必须阻断。
- flaky baseline 必须阻断。
- fail-to-pass 初始全部通过通常说明任务无效，不能作为修复任务训练数据。
- 隐藏测试、gold patch 和 reward-only 字段不能进入模型上下文或训练导出。
- SWE-Bench-like task 的默认 `test_feedback_policy` 必须是 `disabled`。如果任务选择 `public_only`，必须证明运行的是仓库公开测试或 model-visible smoke tests；hidden fail-to-pass 和 pass-to-pass suite 只能用于 baseline quality gate、formal final verifier、reward metadata 和 training eligibility。

评测报告要求：

- `task_success_rate`
- fail-to-pass 测试通过率。
- pass-to-pass 测试保持率。
- 平均 turn 数。
- 平均工具调用数。
- 平均测试次数。
- final verifier status 分布。
- run outcome 分布。
- permission denial rate。
- invalid tool call rate。
- timeout rate。
- patch size 分布。
- environment failure 分布。

测试要求：

- 批量运行 V2 任务集时生成 batch 或 experiment manifest。
- 任务分布报告可以区分模型失败和环境失败。
- 至少一个 invalid task、一个 flaky task、一个 dependency failed 或等价环境失败样例有结构化 skipped reason。
- `inspect-experiment --assert-minimums tests/fixtures/run_configs/v2/task_set_thresholds.yaml` 只检查任务集事实：任务数量、进入 Agent Loop 数量、formal final verifier 数量、accepted 数量、结构化 skipped reason 和本任务集的 export audit 状态。
- 阶段十三不能把 mock provider、真实 provider、Docker stage 或全部第二版能力覆盖混入 replay task-set 阈值；这些跨来源事实由阶段十五的全局 V2 acceptance report 汇总和检查。

验收命令：

```bash
RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)
TASK_SET_DIR="runs/v2-task-set-$RUN_ID"

PATH=.venv/bin:$PATH repo-harness run-experiment \
  --config tests/fixtures/run_configs/v2/replay_experiment.yaml \
  --output-dir "$TASK_SET_DIR"

PATH=.venv/bin:$PATH repo-harness export "$TASK_SET_DIR" --format sft_jsonl
PATH=.venv/bin:$PATH repo-harness export "$TASK_SET_DIR" --format rl_jsonl
PATH=.venv/bin:$PATH repo-harness export "$TASK_SET_DIR" --format preference_jsonl
PATH=.venv/bin:$PATH repo-harness inspect-export "$TASK_SET_DIR/exports" --all --assert-clean
PATH=.venv/bin:$PATH repo-harness inspect-export "$TASK_SET_DIR/exports" --all --format sft_jsonl --require-trainable-samples
PATH=.venv/bin:$PATH repo-harness inspect-export "$TASK_SET_DIR/exports" --all --format rl_jsonl --require-trainable-samples

PATH=.venv/bin:$PATH repo-harness inspect-experiment "$TASK_SET_DIR" \
  --assert-minimums tests/fixtures/run_configs/v2/task_set_thresholds.yaml
```

本阶段不做的事情：

- 不追求公开榜单分数。
- 不把 20 个任务描述为完整 benchmark。

## 阶段十四：Workspace Adapter 协议收口和 Docker execution mode 扩展路径

目标：在前面已经落地的 workspace facts、source materialization 和 local process backend 之上，把执行后端接口收口清楚，并在条件允许时实现 Docker-based executable repository environment 的最小端到端路径。

本阶段可以有两种完成方式。

无论选择哪种方式，本阶段都必须写 `docker_stage_status.json`，建议字段包括：

- `mode`：`interface_only` 或 `docker_backend`。
- `status`：`passed`、`failed` 或 `skipped`。
- `docker_available`。
- `reason`。
- `workspace_backend_version`。
- `local_backend_tests`。
- `docker_rejection_tests`。
- `docker_backend_tests`。
- `generated_at`。

新增机器检查命令：

```text
repo-harness workspace-backend-status --output <docker_stage_status.json> --mode interface-only
repo-harness workspace-backend-status --output <docker_stage_status.json> --mode docker-backend
repo-harness inspect-workspace-backend --status-file <docker_stage_status.json> --assert-interface-only
repo-harness inspect-workspace-backend --status-file <docker_stage_status.json> --assert-docker-backend
repo-harness inspect-workspace-backend --status-file <docker_stage_status.json> --assert-stage-complete
```

CLI 参数与 JSON 枚举的映射必须固定：

| CLI `--mode` | `docker_stage_status.json.mode` |
| --- | --- |
| `interface-only` | `interface_only` |
| `docker-backend` | `docker_backend` |

`--assert-stage-complete` 用于最终验收。它必须接受 `mode = "interface_only"` 且接口保留模式测试通过的状态，也必须接受 `mode = "docker_backend"` 且 Docker 最小端到端测试通过的状态；任何 `status = "failed"`、缺失关键字段、Docker 后端声明但 Docker 不可用被 skip 的情况都必须失败。

### 仅完成接口和拒绝逻辑保留

如果当前时间或运行环境不适合实现 Docker 后端，则本阶段至少要完成：

- 复核阶段一已经定义的 Workspace Adapter 接口或 backend protocol。
- 确认 `LocalWorkspaceAdapter` 明确实现该接口。
- 保留 `runtime.execution_mode = "docker"` 的清晰拒绝错误。
- 保留或新增测试，确认 Docker 未实现时不会静默退回 local process。
- 在文档中说明 Docker execution mode 的最小验收路径。

接口保留模式验收命令：

```bash
RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)
DOCKER_STATUS_DIR="runs/v2-docker-stage-$RUN_ID"
DOCKER_STATUS_FILE="$DOCKER_STATUS_DIR/docker_stage_status.json"

PATH=.venv/bin:$PATH python -m pytest tests/unit/test_workspace_backend.py
PATH=.venv/bin:$PATH python -m pytest tests/integration/test_docker_mode_rejected.py
PATH=.venv/bin:$PATH python -m pytest tests/integration/test_workspace_lifecycle.py
PATH=.venv/bin:$PATH repo-harness workspace-backend-status \
  --output "$DOCKER_STATUS_FILE" \
  --mode interface-only
PATH=.venv/bin:$PATH repo-harness inspect-workspace-backend \
  --status-file "$DOCKER_STATUS_FILE" \
  --assert-interface-only
```

### 实现 Docker 最小后端

如果实现 Docker 后端，必须满足：

- 新增 `DockerWorkspaceAdapter` 或独立 backend。
- setup、agent run、formal final verifier 三个阶段都记录 execution mode、image id、network policy、mount policy、command timeout、container path 和 host artifact path。
- agent run 和 formal final verifier 默认无网络或受控网络；如果 setup 需要网络，必须由任务配置显式声明。
- 容器内路径不能直接泄漏成本机绝对路径进入模型上下文或训练导出。
- Docker 模式下仍然必须先冻结 `final.patch`，再在独立 verification workspace 中 strict patch replay。
- Docker 模式不能声称生产级安全沙箱、沙箱逃逸防护或完整网络隔离。

Docker 最小验收：

- source checkout。
- setup workspace。
- agent workspace。
- 工具执行。
- `run_tests`。
- `final.patch`。
- verification workspace。
- final verifier。

Docker 后端最小定义：

- 必须真实创建并使用 container execution context，不能只是把 `execution_mode = docker` 记录到 metadata 后继续在 host local process 中运行。
- setup、agent run 和 verification 必须分别记录 container id 或等价 execution id、image ref、mount policy、network policy、command timeout、container workdir、host artifact path 和 container artifact path。
- 至少一个 replay task 在 Docker 后端中完成 source checkout、setup、工具执行、`run_tests`、冻结 `final.patch`、独立 verification workspace 和 formal final verifier。

测试要求：

- Docker 不可用时，只有接口保留模式可以通过；如果声明 `mode = docker_backend`，Docker 不可用必须失败，不能被 skip 当作通过。
- Docker 可用时跑通一个最小 replay task。
- local process mode 回归测试继续通过。

验收命令：

```bash
RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)
DOCKER_STATUS_DIR="runs/v2-docker-stage-$RUN_ID"
DOCKER_STATUS_FILE="$DOCKER_STATUS_DIR/docker_stage_status.json"

PATH=.venv/bin:$PATH python -m pytest tests/unit/test_workspace_backend.py
PATH=.venv/bin:$PATH python -m pytest tests/integration/test_docker_workspace.py
PATH=.venv/bin:$PATH python -m pytest tests/integration/test_workspace_lifecycle.py
PATH=.venv/bin:$PATH repo-harness workspace-backend-status \
  --output "$DOCKER_STATUS_FILE" \
  --mode docker-backend
PATH=.venv/bin:$PATH repo-harness inspect-workspace-backend \
  --status-file "$DOCKER_STATUS_FILE" \
  --assert-docker-backend
```

本阶段不做的事情：

- 不实现远程容器平台。
- 不实现多租户安全平台。
- 不实现操作系统级沙箱证明。

## 阶段十五：第二版最终验收、文档、示例和审查收口

目标：把第二版实现从“功能散落完成”收束成可复盘、可展示、可继续维护的版本。

必须新增或更新：

- `docs/v2/final-acceptance.md`
- `docs/v2/walkthrough.md`
- `docs/v2/developer-checklist.md`
- `docs/v2/implementation-log/`
- `docs/v2/review/implementation/`
- `docs/v2/review/implementation/template.md`
- README 中的第二版能力边界。
- `runs/<v2-acceptance>/v2_acceptance_report.json` 或等价最终验收报告。

阶段审查记录模板至少包含：

- 阶段编号和提交范围。
- 修改的模块和文档。
- 实际运行的验收命令和结果。
- 关键产物路径，例如 run metadata、export manifest、audit report、experiment manifest。
- 至少一个正例和相关负例的证据。
- 降级项、未完成风险和下一阶段阻断项。
- 审查结论：通过、带条件通过或不通过。

全局 V2 acceptance report 必须和阶段十三的 replay task-set 阈值检查分开：

- 阶段十三的 `inspect-experiment --assert-minimums` 只证明任务集本身达到数量和质量阈值。
- `v2_acceptance_report.json` 才汇总跨来源事实，至少引用 task-set experiment manifest、mock provider smoke report、real provider smoke report、Docker stage status、三种导出格式的 audit report、feedback policy 覆盖结果和最终文档检查结果。
- 新增或扩展 `repo-harness build-v2-acceptance-report` 和 `repo-harness inspect-v2-acceptance`，前者只汇总既有机器产物，后者断言所有必需引用存在、sha256 匹配、状态满足第二版最小完成定义。
- `build-v2-acceptance-report` 必须有稳定证据输入：`--feedback-policy-report` 显式传入策略覆盖报告，`--export-audit-root` 可以重复传入一个或多个 exports 根目录。若实现选择从 experiment manifest 自动发现 export audit，也必须在 `v2_acceptance_report.json` 中记录发现来源、manifest path 和 sha256，不能让 `inspect-v2-acceptance` 依赖隐式目录扫描。

最终验收命令建议：

```bash
RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)
V1_DIR="runs/v2-v1-regression-$RUN_ID"
MOCK_DIR="runs/v2-final-mock-provider-$RUN_ID"
TASK_SET_DIR="runs/v2-final-task-set-$RUN_ID"
REAL_PROVIDER_DIR="runs/v2-final-real-provider-$RUN_ID"
REAL_PROVIDER_REPORT="$REAL_PROVIDER_DIR/real_provider_smoke_report.json"
FEEDBACK_POLICY_REPORT="$TASK_SET_DIR/feedback_policy_report.json"
DOCKER_STATUS_FILE="${DOCKER_STATUS_FILE:?set to the phase fourteen docker_stage_status.json path}"
ACCEPTANCE_DIR="runs/v2-final-acceptance-$RUN_ID"
ACCEPTANCE_REPORT="$ACCEPTANCE_DIR/v2_acceptance_report.json"

PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest

PATH=.venv/bin:$PATH repo-harness run-batch \
  --config tests/fixtures/run_configs/batch_replay.yaml \
  --output-dir "$V1_DIR"

PATH=.venv/bin:$PATH repo-harness export "$V1_DIR" --format sft_jsonl
PATH=.venv/bin:$PATH repo-harness export "$V1_DIR" --format rl_jsonl
PATH=.venv/bin:$PATH repo-harness export "$V1_DIR" --format preference_jsonl
PATH=.venv/bin:$PATH repo-harness inspect-export "$V1_DIR/exports" --all --assert-clean
PATH=.venv/bin:$PATH repo-harness inspect-export "$V1_DIR/exports" --all --format sft_jsonl --require-trainable-samples
PATH=.venv/bin:$PATH repo-harness inspect-export "$V1_DIR/exports" --all --format rl_jsonl --require-trainable-samples

PATH=.venv/bin:$PATH repo-harness run-task \
  tests/fixtures/tasks/task_001.yaml \
  --config tests/fixtures/run_configs/v2/mock_provider_smoke.yaml \
  --output-dir "$MOCK_DIR"
PATH=.venv/bin:$PATH repo-harness export "$MOCK_DIR" --format sft_jsonl
PATH=.venv/bin:$PATH repo-harness export "$MOCK_DIR" --format rl_jsonl
PATH=.venv/bin:$PATH repo-harness inspect-export "$MOCK_DIR/exports" --all --assert-clean
PATH=.venv/bin:$PATH repo-harness inspect-mock-provider-smoke \
  --run-dir "$MOCK_DIR" \
  --output "$MOCK_DIR/mock_provider_smoke_report.json" \
  --assert-accepted \
  --assert-export-clean

PATH=.venv/bin:$PATH repo-harness run-experiment \
  --config tests/fixtures/run_configs/v2/replay_experiment.yaml \
  --output-dir "$TASK_SET_DIR"

PATH=.venv/bin:$PATH repo-harness export "$TASK_SET_DIR" --format sft_jsonl
PATH=.venv/bin:$PATH repo-harness export "$TASK_SET_DIR" --format rl_jsonl
PATH=.venv/bin:$PATH repo-harness export "$TASK_SET_DIR" --format preference_jsonl
PATH=.venv/bin:$PATH repo-harness inspect-export "$TASK_SET_DIR/exports" --all --assert-clean
PATH=.venv/bin:$PATH repo-harness inspect-export "$TASK_SET_DIR/exports" --all --format sft_jsonl --require-trainable-samples
PATH=.venv/bin:$PATH repo-harness inspect-export "$TASK_SET_DIR/exports" --all --format rl_jsonl --require-trainable-samples
PATH=.venv/bin:$PATH repo-harness inspect-experiment "$TASK_SET_DIR" \
  --assert-minimums tests/fixtures/run_configs/v2/task_set_thresholds.yaml
PATH=.venv/bin:$PATH repo-harness inspect-feedback-policy-coverage \
  --experiment-dir "$TASK_SET_DIR" \
  --output "$FEEDBACK_POLICY_REPORT" \
  --assert-complete

REAL_PROVIDER_SMOKE_DIR="$REAL_PROVIDER_DIR" \
REAL_PROVIDER_SMOKE_REPORT="$REAL_PROVIDER_REPORT" \
  PATH=.venv/bin:$PATH python -m pytest tests/integration/test_real_provider_smoke.py
PATH=.venv/bin:$PATH repo-harness inspect-real-provider-smoke \
  --report "$REAL_PROVIDER_REPORT" \
  --allow-skip-without-credentials \
  --require-accepted-with-credentials

PATH=.venv/bin:$PATH repo-harness inspect-workspace-backend \
  --status-file "$DOCKER_STATUS_FILE" \
  --assert-stage-complete

PATH=.venv/bin:$PATH repo-harness build-v2-acceptance-report \
  --v1-regression-dir "$V1_DIR" \
  --task-set-manifest "$TASK_SET_DIR/experiment_manifest.json" \
  --mock-provider-report "$MOCK_DIR/mock_provider_smoke_report.json" \
  --real-provider-report "$REAL_PROVIDER_REPORT" \
  --feedback-policy-report "$FEEDBACK_POLICY_REPORT" \
  --export-audit-root "$V1_DIR/exports" \
  --export-audit-root "$MOCK_DIR/exports" \
  --export-audit-root "$TASK_SET_DIR/exports" \
  --docker-status "$DOCKER_STATUS_FILE" \
  --output "$ACCEPTANCE_REPORT"
PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance "$ACCEPTANCE_REPORT" --assert-complete
```

`test_real_provider_smoke.py` 必须在最终验收中始终运行。无凭证时可接受结果是结构化 skip，并记录 skip reason；有凭证时必须至少有一个固定小任务 accepted，不能把无凭证 skip 记成真实 provider 成功。

最终验收必须记录：

- 全量测试结果。
- 第一版 replay 回归结果。
- 第二版 experiment 结果。
- `feedback_tests_passed_policy` 覆盖结果，包括 `stop_immediately`、`require_model_final`、`continue` 三种策略的测试摘要，以及 `feedback_verifier_accepted`、`first_feedback_accept_turn`、`agent_stop_reason` 的样例。
- `test_feedback_policy` 覆盖结果，包括 `disabled`、`public_only`、`structured_public_feedback`、`oracle_hidden_feedback` 四种策略的测试摘要，以及 `hidden_feedback_visible_to_model`、`public_tests_ran`、`hidden_feedback_ran` 的样例。
- `disabled` 与 `feedback_tests_passed_policy` 的组合解析样例，证明 disabled 下 feedback-tests-passed policy 为 not applicable，不能触发 `feedback_tests_passed` stop reason。
- `oracle_hidden_feedback` 的训练资格样例，证明默认 `diagnostic_only`，以及显式允许 oracle feedback training 时的 export policy、manifest 和 audit report 证据。
- 任务数量、进入 Agent Loop 数量、formal final verifier 数量、accepted 数量。
- 按 scaffold、provider kind 和 execution mode 分层的覆盖数量。
- mock provider 结果。
- 真实 provider 无凭证 skip 或有凭证 accepted 结果。
- `real_provider_smoke_report.json` 样例和结论。
- export manifest、audit report JSON 和 audit report Markdown 样例。
- preference pair 生成或被阻断的结构化原因。
- inspect-run 对 replay run 和真实 provider run 的输出摘要。
- Docker stage 的状态：未实现且继续拒绝，或者已实现并通过最小端到端 Docker 验收。
- `docker_stage_status.json` 和 `inspect-workspace-backend` 检查结果。
- `v2_acceptance_report.json` 和 `inspect-v2-acceptance --assert-complete` 检查结果，证明 replay task set、mock provider、real provider、Docker stage 和 export audit 没有被混在单一来源的阈值检查里。

文档表述边界：

- 可以写“支持真实模型驱动的评测运行”。
- 可以写“支持中小规模任务评测、多策略对比和可审计训练数据导出”。
- 可以写“为 Docker-based executable repository environment 提供接口和可验收路径”。
- 不能写“生产级安全沙箱”。
- 不能写“完整 SWE-Bench 复现”。
- 不能写“已经训练出软件工程智能体”。
- 不能写“复现 Claude Code 或某家公司的内部 post-training stack”。

## 第二版测试矩阵

第二版完成后，测试矩阵至少覆盖：

| 能力 | 单元测试 | 集成测试 | 端到端验收 |
| --- | --- | --- | --- |
| run metadata | schema、writer、reader、fingerprint | replay run 写 metadata | inspect-run 展示 |
| tool schema snapshot | snapshot 生成、hash、artifact ref | run metadata 引用 snapshot | export audit 读取 |
| export audit | audit item、eligibility 映射 | SFT/RL/preference 生成 manifest、JSON audit 和 Markdown audit | final acceptance export |
| FailureDiagnostics | failure category、failure type、recoverable | skipped/failed run 写诊断 | acceptance report failure distribution |
| preference pairing | compare scope、阻断原因 | 同任务多 run 配对和阻断 | experiment preference export |
| experiment runner | config 展开、run id 策略 | 多 rollout replay | V2 acceptance experiment |
| scaffold registry | policy、allowed tools、stop policy | simple_react 回归 | scaffold comparison report |
| test feedback policy | disabled/public/oracle schema、allowed tools、output shape | run_tests visibility integration | final acceptance policy report |
| single_shot_patch | patch parser、policy | accepted 和 patch failure | scaffold comparison |
| planner_coder_verifier | phase transition、allowed tools | phase replay | conditional enhancement |
| model client factory | provider selection、错误类型 | mock provider | real provider smoke |
| real provider report | smoke report schema | 无凭证 skip、有凭证 accepted、provider error | final acceptance provider section |
| repo materialization | source schema、hash | archive/local repo materialize | V2 task set |
| Docker backend | backend protocol | Docker skip 或 run | conditional acceptance |
| Docker stage status | status schema | interface-only 或 docker backend 状态 | inspect-workspace-backend |

必须保留的负例矩阵：

| 负例 | 预期结果 |
| --- | --- |
| 训练 payload 中出现本机绝对路径 | export audit failed，样本 `training_eligibility = invalid` |
| hidden field、gold patch 或 reward-only 字段进入 prompt 或导出 | export audit failed，样本 `training_eligibility = invalid` |
| tool call 缺少终态 tool result | run 或 export audit failed，不能进入正式训练数据 |
| formal final verifier 缺失或不是 strict patch replay | 样本 `training_eligibility = invalid` |
| preference pair 的 base commit、tool schema snapshot、verifier 或预算不一致 | pair 被阻断，并写入 blocked reason |
| Docker 不可用 | Docker backend 测试结构化 skip，接口保留模式仍测试拒绝逻辑 |
| 配置 Docker execution mode 但后端未实现 | 清晰拒绝，不能静默回退到 local process |
| 无真实 provider 凭证 | real provider smoke test 结构化 skip，不能记为 accepted |
| provider auth error、rate limit、timeout、invalid response、tool call parse failure、context limit | 记录 `model_error_type`，不能伪装为普通 accepted run |
| 损坏的 `export_manifest.json` 或 `audit_report.json` | `inspect-export --assert-clean` 非零退出 |
| 缺失或不完整 compare scope 文件 | preference pair 阻断，并写入 blocked reason |
| provider raw response 被误设为 SFT target、RL rollout payload、trajectory、metadata、preference export 或 skipped manifest 内容 | export audit failed，样本 `training_eligibility = invalid` |
| hidden test accepted/fail-to-pass/pass-to-pass 在非 oracle 模式下进入模型可见输出 | export audit failed，样本 `training_eligibility = invalid` |
| SWE-Bench-like final-only task 使用 `oracle_hidden_feedback` | schema 校验失败或 quality gate 阻断 |
| `test_feedback_policy = disabled` 但产生 `feedback_tests_passed` stop reason | schema 或运行时断言失败 |
| `single_shot_patch` 显式请求非 disabled `test_feedback_policy` | schema 校验失败 |
| `oracle_hidden_feedback` 未经 export policy 显式允许却进入正式训练 JSONL | export audit failed，样本保持 `diagnostic_only` |
| 导出命令要求 trainable 样本但只有 skipped manifest | `inspect-export --require-trainable-samples` 非零退出 |
| 完整 decontamination metadata 进入训练 JSONL payload | export audit failed，样本 `training_eligibility = invalid` |

## 实施风险和降级策略

风险一：导出审计阶段变得过大。

- 降级策略：先完成阶段四 A，也就是 `export_manifest.json`、`audit_report.json`、`audit_report.md`、artifact manifest 校验、formal final verifier 校验、training eligibility 和 `inspect-export --assert-clean`，再补 redaction、loss target 和 preference audit 的细项。
- 不允许降级成只写自由文本质量报告。

风险二：scaffold registry 改动破坏第一版 replay 路径。

- 降级策略：先只迁移 `simple_react`，保持现有 replay tests 全部通过，再新增 scaffold。
- 不允许在 `single_shot_patch` 未稳定时改动 final verifier 口径。

风险三：真实 provider 不稳定或缺少凭证。

- 降级策略：mock provider 必须成为稳定回归基础；真实 provider 无凭证时结构化 skip。
- 不允许把无凭证 skip 记成真实 provider 通过。

风险四：20 到 50 个任务扩展拖慢核心能力。

- 降级策略：先达到 20 个任务的最低验收，再扩展到 50 个。
- 不允许把全部 skipped 的任务集记成第二版成功。

风险五：Docker 后端占用过多时间。

- 降级策略：完成 Workspace Adapter backend protocol、保留 Docker 拒绝测试和文档化验收路径，把 Docker 端到端作为扩展目标。
- 不允许把配置能加载写成 Docker execution mode 已实现。

高风险阶段还必须提供兼容开关和回滚条件：

- 阶段四导出审计：保留第一版 legacy export 读取能力，但第二版正式训练导出必须默认走 `export_manifest.json` 和 `audit_report.json`。如果新审计器阻断旧 run，只允许降级为 `diagnostic_only`，不能绕开审计直接写训练 JSONL。
- 阶段七模型调用和 scaffold registry：保留 replay provider 的第一版行为回归开关；如果新 `ModelClient` protocol 破坏 replay 确定性，必须先回滚新增 scaffold 接入，恢复 `simple_react` replay 通过后再继续。
- 阶段十和阶段十一 provider：保留 mock provider 作为真实 provider 失败时的回归基线；真实 provider 不稳定时只能结构化 skip 或 failed，不允许让最终验收依赖不可复现的外部调用结果。
- 阶段十二和阶段十三任务扩展：命令策略、环境规格和 parser 策略未通过时，不允许扩大任务集数量来掩盖质量门失败。
- 阶段十四 Docker：Docker 后端未满足机器检查时，回滚到接口保留模式，并由 `docker_stage_status.json` 明确记录 `mode = "interface_only"`。

## 最小完成定义

第二版核心范围的最小完成定义如下：

1. 第一版全量测试继续通过。
2. 新 run 在 Agent Loop 前写入不可变 `run_config_facts.json`，在 run 结束后原子写入最终 `run_metadata.json`，并记录本地执行环境指纹和 tool schema snapshot。
3. `inspect-run` 可以读取第一版 legacy run 和第二版 run，并明确报告 metadata、artifact manifest、export audit、baseline、final verifier、reward、metrics 和 summary 状态。
4. SFT、RL rollout 和 preference export 都生成不会互相覆盖的 format-specific export directory，并且每个目录都有 `export_manifest.json`、`audit_report.json` 和 `audit_report.md`。
5. ExportRecord 有顶层 `training_eligibility` 或强类型 `quality.training_eligibility`，且与 `filter_status`、`invalid_for_training`、`invalid_reason` 兼容。
6. Preference pair 只在 pairing policy 硬门控通过时生成。
7. `run-experiment` 或等价实验入口支持同任务多 rollout，并生成 experiment manifest 和 aggregate metrics。
8. 至少两种 scaffold 可以在同一任务集合上运行，并且新增 scaffold 的行为约束真实生效。
9. ModelClient 已解耦，mock provider 可以无密钥稳定回归。
10. `test_real_provider_smoke.py` 在最终验收中始终运行；至少一个真实 provider 在有凭证时可以让固定小任务通过 formal final verifier，无凭证时结构化 skip。
11. 至少 20 个中小型 repository-level 或 repository-style task 通过静态校验，至少 15 个进入正式 Agent Loop，至少 15 个产生 formal final verifier，至少 3 个 accepted，并且这些阈值由 `inspect-experiment --assert-minimums` 机器检查。
12. Docker stage 明确处于“未实现但继续拒绝并有接口计划”或“已实现最小端到端 Docker backend 并通过条件验收”之一。
13. 第二版最终验收文档、walkthrough、developer checklist 和示例导出产物齐全。

完成这些内容后，RepoHarness 第二版可以被克制地表述为：

> 一个面向软件工程智能体训练轨迹的轻量级研究 Harness，支持真实模型运行、中小规模任务评测、多策略对比、verifier-aligned reward metadata 和可审计训练数据导出，并为 Docker-based executable repository environment 留出可验收的扩展路径。
