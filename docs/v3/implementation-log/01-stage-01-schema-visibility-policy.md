# V3 Stage 01 Schema And Visibility Policy

## 目标

阶段 1 的目标是在阶段 0 已冻结输入的基础上，建立第三版后续阶段共用的 schema、版本常量和模型可见性边界。本阶段只实现 schema 骨架、配置扩展、contamination denylist 和对应单元测试，不实现 Docker backend、task adapter、source materialization、Agent Loop、Experiment Runner 或 acceptance builder。

## 实现内容

新增 V3 版本常量，覆盖 V3 schema、visibility policy、contamination denylist、Docker runtime config、SWE-Bench-like config、Docker backend facts、container execution facts、real repository source facts、SWE-Bench-like task facts、task adapter facts、environment spec、verifier plan、core failure diagnostics、context compaction facts、experiment resume manifest、checkpoint、trajectory store facts、tool contract snapshot、policy snapshots、command log entry 和 V3 acceptance report。

扩展 `RunConfig` 和 `ExperimentConfig`，允许 `runtime.execution_mode=docker` 进入配置层，并新增 `docker_backend` 与 `swebench_like` 配置。`RunConfig.swebench_like.effective_max_workers` 默认跟随 `evaluation.concurrency`，显式配置时取 `swebench_like.max_workers` 和 `evaluation.concurrency` 中更保守的较小值。`ExperimentConfig` 在第一阶段仍保持串行默认，避免后续 Docker 阶段前误开并发。

新增 V3 facts 和 policy schema：

- Docker backend facts 和 container execution facts。
- 真实仓库 source facts。
- SWE-Bench-like task facts、task adapter facts 和 environment spec。
- SWE-Bench-like verifier plan。
- Run checkpoint 和 experiment resume manifest。
- Context compaction facts。
- Core failure diagnostics。
- ToolContractSnapshot、PermissionPolicySnapshot、HookPolicySnapshot 和 MCPPolicySnapshot。
- TrajectoryStoreFacts。
- CommandLogEntry 和 V3AcceptanceReport。

新增 `V3VisibilityPolicy` 和 `V3ContaminationDenylist`。denylist 覆盖 prompt、prepared messages、tool observation、transcript、checkpoint、context compaction report、SFT export、RL export、preference export 和 acceptance input 等 surface。它会阻断 `gold_patch`、`test_patch`、`FAIL_TO_PASS`、`PASS_TO_PASS`、official harness/report/status、provider raw、reasoning summary raw、Authorization/API key/credential detail、本机绝对路径、final verifier hidden result、reward metadata 和 run outcome 等污染内容。

根据审查反馈，denylist 没有把普通公开软件工程词汇 `patch` 作为污染词，也不会因为普通公开句子中的 `resolved` 或 `unresolved` 误判污染；只有 official status key、status value 或明确 evaluator-only term 会被拒绝。

## 主要修改文件

- `src/repo_harness/schema_versions.py`
- `src/repo_harness/v3_visibility.py`
- `src/repo_harness/v3_acceptance.py`
- `src/repo_harness/config/schemas.py`
- `src/repo_harness/evaluation/schemas.py`
- `src/repo_harness/workspace/schemas.py`
- `src/repo_harness/tasks/schemas.py`
- `src/repo_harness/verifier/schemas.py`
- `src/repo_harness/context/schemas.py`
- `src/repo_harness/reward/schemas.py`
- `src/repo_harness/run_metadata/schemas.py`
- `src/repo_harness/trajectory/schemas.py`
- 对应 package `__init__.py` exports
- `src/repo_harness/evaluation/experiment.py`
- `tests/unit/test_v3_visibility_policy.py`
- `tests/unit/test_v3_schemas.py`
- `tests/unit/test_config_schema.py`
- `tests/unit/test_experiment_config.py`
- `tests/fixtures/run_configs/v3/docker_experiment_smoke.yaml`
- `docs/v3/implementation-log/01-stage-01-schema-visibility-policy.md`
- `docs/v3/review/implementation/stage-01-review.md`

## 机器产物

本阶段是 schema 和 policy 阶段，没有启动正式 run，也没有生成 `RUN_DIR`。本阶段产生的可复用机器输入是：

- `tests/fixtures/run_configs/v3/docker_experiment_smoke.yaml`

阶段 0 冻结机器输入继续保持有效：

- `tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/v3_feasibility_input_manifest.json`
- `docs/v3/evidence/swebench-lite-fixed/evaluator_only/evaluator_evidence_manifest.json`

## 验证命令和结果

- `PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v3_visibility_policy.py tests/unit/test_v3_schemas.py tests/unit/test_config_schema.py tests/unit/test_experiment_config.py tests/unit/test_core_schemas.py -q`：`33 passed`。
- `PATH=.venv/bin:$PATH python -m compileall src`：通过。
- `PATH=.venv/bin:$PATH python -m pytest -q`：`397 passed in 148.21s`。
- `PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete`：通过，返回 `v2_acceptance=passed`，`task_count=20`。
- `PATH=.venv/bin:$PATH repo-harness inspect-v3-swebench-fixture --fixture-dir tests/fixtures/v3/swebench_lite_fixed --evidence-dir docs/v3/evidence/swebench-lite-fixed --manifest tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/v3_feasibility_input_manifest.json --assert-frozen`：通过，返回 `v3_swebench_fixture=frozen`，`task_count=3`。

## 正例证据

- `RuntimeConfig` 和 `ExperimentConfig` 可以解析 `execution_mode=docker`，不会继续在配置层硬拒绝 Docker。
- `RunConfig.swebench_like.effective_max_workers` 在 `evaluation.concurrency=2`、`swebench_like.max_workers=4` 时解析为 `2`。
- 未设置 `swebench_like.max_workers` 时，`RunConfig` 使用 `evaluation.concurrency` 作为有效 worker 数。
- `DockerBackendFacts` 记录 docker context、client/server version、server platform、server architecture、requested container platform、image id、image platform、build mode、cross architecture emulation、network policy、mount policy、timeout、cleanup policy 和 cleanup status。
- `ContainerExecutionFacts` 记录 command、container id、requested platform、container `uname -m`、exit code、duration、network policy、mount policy 和 cleanup status。
- `RealRepositorySourceFacts` 要求固定 source hash、materialization ref 和 verifier evidence ref。
- `SweBenchLikeTaskFacts` 默认 final-only，并阻断模型可见 hidden material。
- `SweBenchLikeVerifierPlan` 阻断 oracle hidden feedback 和模型可见 fail-to-pass / pass-to-pass 命令。
- `RunCheckpoint` 阻断 interrupted/crashed checkpoint 提前引用最终 `run_metadata_ref`。
- `ExperimentResumeManifest` 校验 completed、pending 和 interrupted run ids 与 checkpoint 状态一致。
- `ContextCompactionFacts` 要求 context revision 前进，且 compaction 后 token 数不能增加。
- `CoreFailureDiagnostics` 阻断 reward metadata、run outcome 和 hidden failure diagnostics 进入模型可见面。
- Hook disabled 时不能产生 model-visible hook observation；MCP dynamic tool discovery 被拒绝。
- `V3AcceptanceReport(status="passed")` 必须有 checks、contamination scan refs，并覆盖全部 V3 visibility surfaces。
- `V3ContaminationDenylist` 阻断 `goldPatch`、`testPatch`、`failToPass`、`passToPass`、`provider_raw_response`、Authorization marker、本机绝对路径、reward metadata 和 official status；普通公开 `patch` 和公开 `resolved` 句子通过。

## 负例证据

单元测试覆盖以下拒绝场景：

- Visibility policy 把 evaluator-only 或 audit-only category 放入 model-visible categories 时失败。
- `gold_patch`、`testPatch`、`FAIL_TO_PASS`、`provider_raw_response`、`resolvedStatus`、final verifier hidden result、Authorization marker、reward metadata 和本机绝对路径进入受保护 surface 时失败。
- Real repository source facts 缺少 archive sha 或 mirror sha 时失败。
- SWE-Bench-like task facts 标记 hidden material model-visible 时失败。
- SWE-Bench-like verifier plan 允许 oracle hidden feedback 时失败。
- Run checkpoint 在 interrupted 状态引用 final metadata 时失败。
- Experiment resume manifest 的 pending run ids 与 checkpoint 不一致时失败。
- Context compaction 后 token 增加时失败。
- Core failure diagnostics 把 reward metadata 暴露给模型时失败。
- Completed trajectory store facts 缺少 run metadata ref 时失败。
- Disabled hook 产生 model-visible observation 时失败。
- Dynamic MCP tool discovery 被启用时失败。
- Finished command log entry 缺少 exit code 或 structured skip reason 时失败。
- Passed V3 acceptance report 缺少 contamination scan evidence 或 scan surface coverage 时失败。
- Failed/blocked V3 acceptance report 缺少 failures 时失败。

## 允许降级项

本阶段没有降级执行项。Docker backend 还没有实现，不能被标记为通过；`execution_mode=docker` 仅在 schema 和配置层被接受，实际 backend 能力留给阶段 2 和阶段 3。

## 禁止降级项

- 不允许把 V2 Stage 14 `interface_only` Docker 口径当作 V3 Docker backend 通过。
- 不允许把 generic `patch` 误作为 hidden contamination，从而阻断合法公开任务内容。
- 不允许把 `gold_patch`、`test_patch`、`FAIL_TO_PASS`、`PASS_TO_PASS`、official status、provider raw、credential、本机路径、hidden verifier result、reward metadata 或 run outcome 放进模型可见内容或正式训练 payload。
- 不允许让 passed acceptance report 在缺少 contamination scan evidence 或 surface coverage 时通过 schema。
- 不允许因为工作树中存在无关既有改动而将这些改动混入 Stage 1 commit。

## 已知限制

本阶段只定义 schema 和策略，不读取污染扫描 artifact 的内容，也不校验每个 surface 与单个 clean scan result 的一一映射。该内容属于阶段 12 inspect 和 acceptance builder 的实现范围，后续必须在读取 evidence refs 和 sha256 时补齐。

本阶段没有生成正式 trajectory store、Docker backend status、task set manifest、export audit 或 acceptance bundle。这些均属于后续阶段。

## 设计偏离

没有偏离 V3 实施计划。对 `ExperimentConfig` 的 Docker 接受仍保持第一阶段串行默认，避免在 Docker backend 实现前产生并发执行含义。

## 审查结论

第一轮只读子代理审查发现 2 个代码层面 P2、1 个工作树范围 P2 和 1 个 P3。代码层面 P2 已修复：`V3AcceptanceReport` 已要求 passed 状态绑定 contamination scan evidence 和 surface coverage；denylist 已移除普通 `patch` 与裸 `resolved` / `unresolved` 的误拦。P3 已修复：`ExperimentResumeManifest` 现在校验 completed、pending 和 interrupted 三类 run id。

第二轮只读子代理复核结论：P1 未发现；代码层面 P2 已修复；条件允许进入阶段 2，条件是 Stage 1 commit 必须显式排除无关 V1 文档迁移、`.vscode`、`docs/build-your-own`、`docs/resume`、`docs/v1`、`uv.lock` 等非 Stage 1 范围文件。本阶段提交将只 stage Stage 1 相关文件。
