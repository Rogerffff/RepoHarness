# Stage 12: repo materialization and command environment policy gates

## 本阶段目标

本阶段目标是在扩展任务集之前，先把任务来源、源码快照事实、命令策略门、环境规格 hash 和 verifier parser policy 收口到可审计路径上。Stage 12 不扩展到完整 SWE-Bench 适配，不从网络下载公开仓库，也不实现 Docker backend。

本阶段重点边界：

- Task Adapter 只解析、校验和规范化任务来源 specification，不创建 workspace，不运行 setup，不运行测试。
- 真正的 source materialization 由 `workspace/materialization.py` 和 `WorkspaceAdapter.create_source_checkout()` 完成。
- `SourceCheckout` 是代码里的 materialization 结果对象，`SourceCheckoutFacts` 是序列化事实对象，没有新增含义重叠的别名。
- 正式 agent workspace 来自可审计 source checkout，不直接在用户原始仓库目录运行。
- 命令策略必须区分 setup command、test command 和模型通过 `bash` 请求的命令。
- `test_feedback_policy=disabled` 时，模型不能通过 `bash pytest`、`python -m pytest`、`tox` 或 `nox` 绕过测试反馈策略。

## 本阶段实现内容

- 扩展 task source schema：
  - `FixtureRepositorySource`
  - `LocalArchiveSource`
  - `LocalRepositorySource`
  - `PublicSnapshotSource`
  - `RepoMaterializationResult`
- 扩展 `TaskDefinition` 和 `RunnableTask`：
  - 新增 `repo_source_spec`。
  - 保留旧版 `repo: ../repos/...` fixture path 兼容行为。
  - 对旧 fixture task 自动生成 `FixtureRepositorySource`。
- 新增 source materialization：
  - `workspace/materialization.py`
  - `SourceCheckout`
  - `materialize_source(task, destination)`
  - local archive 支持 `.zip`、`.tar`、`.tar.gz`、`.tgz`，并校验 archive sha256 和 archive member path traversal。
  - local repository 必须是真实 Git repository，必须能读取 HEAD 和 `git status --short`。
  - dirty local repository 默认拒绝，只有 `allow_dirty_snapshot=true` 时允许。
  - `current_commit` 和 `working_tree_clean` 如果在 YAML 中声明，必须和真实 Git HEAD / status 一致，不能用 YAML 声明覆盖真实状态。
  - public snapshot schema 可以校验，但没有预下载 archive 时 materialization 会明确拒绝，不联网下载。
  - materialized checkout 默认剥离 `.git`、`.hg`、`.svn`。
- 新增 source hashing helper：
  - `workspace/source_hash.py`
  - `compute_file_sha256`
  - `compute_source_tree_hash`
  - 避免 workspace materialization 反向依赖 run metadata fingerprint，防止循环导入。
- 扩展 `SourceCheckoutFacts`：
  - `source_type`
  - `current_commit`
  - `working_tree_clean`
  - `dirty_snapshot_allowed`
  - `remotes_stripped`
  - `branches_stripped`
  - `tags_stripped`
  - `materialization_policy_version`
- 扩展 run metadata：
  - `run_config_facts.json` 中继续通过 `environment_fingerprint.workspace_execution.source_checkout` 记录 source facts。
  - 最终 `run_metadata.json` 新增 `source_checkout` 和 `environment_spec_hash`，不只保留 ref。
- 扩展 export metadata：
  - 导出 metadata 新增 `source_type`、`source_tree_hash`、`source_archive_sha256`、`working_tree_clean`、`dirty_snapshot_allowed`。
  - `decontamination_status` 优先来自 materialized source facts，缺失时才回退到 task 层 decontamination。
- 新增 command policy：
  - `SetupCommandPolicy`
  - `TestCommandPolicy`
  - `CommandPolicy`
  - `CommandPolicyDecision`
  - setup command 保持保守 allowlist：`python <repo_script.py>`。
  - local archive / public snapshot 的 setup command 在 Task Adapter 阶段只校验形态，文件存在性在 materialized workspace 中由运行阶段处理。
  - model bash 中的 pytest、`python -m pytest`、tox、nox 和 task test command 都进入测试命令策略门。
- 新增 environment spec hash helper：
  - `compute_environment_spec_hash`
  - hash 输入包含 environment spec、source checkout facts、dependency state strategy、execution mode 和 setup artifact hash。
- 新增 verifier parser policy：
  - `VerifierParserPolicy`
  - `ParserPolicyDecision`
  - `evaluate_verifier_output`
  - 覆盖 pytest output、generic exit-code text output 和低置信 parser 阻断。
  - baseline quality gate 实际调用 parser policy，不只是孤立 helper。

## 修改的主要文件

- `src/repo_harness/tasks/schemas.py`
- `src/repo_harness/tasks/adapter.py`
- `src/repo_harness/tasks/__init__.py`
- `src/repo_harness/tasks/command_policy.py`
- `src/repo_harness/tasks/environment.py`
- `src/repo_harness/workspace/materialization.py`
- `src/repo_harness/workspace/source_hash.py`
- `src/repo_harness/workspace/adapter.py`
- `src/repo_harness/workspace/__init__.py`
- `src/repo_harness/run_metadata/schemas.py`
- `src/repo_harness/run_metadata/fingerprint.py`
- `src/repo_harness/run_metadata/writer.py`
- `src/repo_harness/export/exporter.py`
- `src/repo_harness/export/pairing.py`
- `src/repo_harness/tools/minimal.py`
- `src/repo_harness/evaluation/runner.py`
- `src/repo_harness/verifier/parser_policy.py`
- `src/repo_harness/verifier/__init__.py`
- `tests/unit/test_repo_materialization.py`
- `tests/unit/test_command_policy.py`
- `tests/unit/test_environment_spec.py`
- `tests/unit/test_verifier_parser_policy.py`
- `tests/integration/test_repo_materialization_smoke.py`
- `tests/integration/test_command_environment_policy_gate.py`

## 生成的机器可读产物

稳定 materialization smoke run：

- `runs/v2-repo-materialization-smoke-20260501T225500Z/inputs/archive_task.yaml`
- `runs/v2-repo-materialization-smoke-20260501T225500Z/inputs/materialization_input_facts.json`
- `runs/v2-repo-materialization-smoke-20260501T225500Z/inputs/replay_public_only.yaml`
- `runs/v2-repo-materialization-smoke-20260501T225500Z/stage12-archive-materialization-smoke/run_config_facts.json`
- `runs/v2-repo-materialization-smoke-20260501T225500Z/stage12-archive-materialization-smoke/run_metadata.json`
- `runs/v2-repo-materialization-smoke-20260501T225500Z/stage12-archive-materialization-smoke/baseline.json`
- `runs/v2-repo-materialization-smoke-20260501T225500Z/stage12-archive-materialization-smoke/final.patch`
- `runs/v2-repo-materialization-smoke-20260501T225500Z/stage12-archive-materialization-smoke/verifier.json`
- `runs/v2-repo-materialization-smoke-20260501T225500Z/stage12-archive-materialization-smoke/reward.json`
- `runs/v2-repo-materialization-smoke-20260501T225500Z/stage12-archive-materialization-smoke/metrics.json`
- `runs/v2-repo-materialization-smoke-20260501T225500Z/stage12-archive-materialization-smoke/exports/sft.jsonl`
- `runs/v2-repo-materialization-smoke-20260501T225500Z/stage12-archive-materialization-smoke/exports/sft_20260501T215323Z_f1425bf40a/export_manifest.json`
- `runs/v2-repo-materialization-smoke-20260501T225500Z/stage12-archive-materialization-smoke/exports/sft_20260501T215323Z_f1425bf40a/audit_report.json`
- `runs/v2-repo-materialization-smoke-20260501T225500Z/stage12-archive-materialization-smoke/exports/sft_20260501T215323Z_f1425bf40a/audit_report.md`

该 run 关键事实：

- `source_type=local_archive`
- `source_archive_sha256=f9548314e7146a38d737c68f1ca2a73c67120f718fb5f7fd54b5964c606fecac`
- `source_tree_hash=5dc1bb255a425bf6f1cb58ca979bfbfc5df0da02b551f6da160730047898b068`
- `environment_spec_hash=c871663a362564b8c4b7f7a60dbb583a813ab2d998bdaffbbf5b0d45a686870e`
- `decontamination_status=source_checked`
- `final_verifier_status=accepted`
- `run_outcome=success`
- `training_eligibility=trainable`

## 运行的验证命令

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_task_adapter.py tests/unit/test_task_schema.py
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_repo_materialization.py
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_command_policy.py tests/unit/test_environment_spec.py
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_verifier_parser_policy.py
PATH=.venv/bin:$PATH python -m pytest tests/integration/test_workspace_lifecycle.py
PATH=.venv/bin:$PATH python -m pytest tests/integration/test_repo_materialization_smoke.py
PATH=.venv/bin:$PATH python -m pytest tests/integration/test_command_environment_policy_gate.py
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q
PATH=.venv/bin:$PATH repo-harness run-task runs/v2-repo-materialization-smoke-20260501T225500Z/inputs/archive_task.yaml --config runs/v2-repo-materialization-smoke-20260501T225500Z/inputs/replay_public_only.yaml --output-dir runs/v2-repo-materialization-smoke-20260501T225500Z --run-id stage12-archive-materialization-smoke
PATH=.venv/bin:$PATH repo-harness inspect-run runs/v2-repo-materialization-smoke-20260501T225500Z/stage12-archive-materialization-smoke
PATH=.venv/bin:$PATH repo-harness export runs/v2-repo-materialization-smoke-20260501T225500Z/stage12-archive-materialization-smoke --format sft_jsonl
PATH=.venv/bin:$PATH repo-harness inspect-export runs/v2-repo-materialization-smoke-20260501T225500Z/stage12-archive-materialization-smoke/exports --all --assert-clean
PATH=.venv/bin:$PATH repo-harness inspect-export runs/v2-repo-materialization-smoke-20260501T225500Z/stage12-archive-materialization-smoke/exports --all --format sft_jsonl --require-trainable-samples
```

## 验证结果

- Stage 12 分组验收测试全部通过：
  - task adapter / schema：38 个测试通过。
  - repo materialization：8 个测试通过。
  - command policy / environment spec：11 个测试通过。
  - verifier parser policy：4 个测试通过。
  - workspace lifecycle：8 个测试通过。
  - repo materialization smoke：1 个测试通过。
  - command environment policy gate：2 个测试通过。
- 全量测试通过，332 个测试通过。
- 稳定 local archive materialization smoke run 通过 `inspect-run`。
- SFT 导出 audit status 为 `passed`，包含 1 个 trainable 样本。
- 额外 metadata/export 断言通过：最终 `run_metadata.json.source_checkout.source_tree_hash` 与 `run_config_facts.json` 一致，SFT export metadata 中的 `source_type`、`source_tree_hash` 和 `decontamination_status` 与 materialized source facts 一致。

## 正例证据

- 旧 fixture task 仍然可以 load，并保持 `repo` 绝对路径规范化。
- local archive 可以 materialize，archive sha256 和 source tree hash 都进入 run metadata 和 export metadata。
- local repository dirty snapshot 默认拒绝。
- local repository 只有显式 `allow_dirty_snapshot=true` 时允许 dirty snapshot，并在 facts 中记录 `dirty_snapshot_allowed=true`。
- local repository 的 `working_tree_clean` 和 `current_commit` YAML 声明不能覆盖真实 Git 状态。
- public snapshot schema 可以校验；没有预下载 archive 时明确拒绝 materialization，不联网下载。
- `test_feedback_policy=disabled` 下，模型通过 `bash` 请求 pytest 会被路由到 `run_tests` 并被策略拒绝。
- tox 和 nox 被 command policy 识别为测试命令，不能绕过测试反馈策略。
- parser policy 已接入 baseline quality gate，低置信 parser 会阻断任务质量门。
- replay、workspace lifecycle、strict patch replay final verifier 和 export audit 回归测试通过。

## 负例证据

- 本阶段没有扩展任务数量到 20 到 50 个。
- 本阶段没有实现 SWE-Bench 适配。
- 本阶段没有从网络下载公开仓库。
- 本阶段没有实现 Docker backend。
- Task Adapter 没有解包 archive，没有复制 workspace，没有运行 setup 或 test。
- local_repository 不是 Git repository、HEAD 不可读取或 status 不可读取时会被拒绝。
- OpenAI、DeepSeek、mock provider 和 provider artifact 路径没有在本阶段改写。
- provider raw response、hidden feedback、gold patch 和 evaluator-only metadata 没有新增进入模型可见内容或训练 payload 的路径。

## 允许降级项

- public snapshot 只保留 schema 和预下载 archive materialization 路径，不默认联网下载。
- archive/public snapshot 的 setup command 在 Task Adapter 阶段只校验命令形态，文件存在性在 materialized workspace 中由运行阶段处理。
- decontamination metadata ref 只保留字段和状态，不在本阶段生成完整 decontamination metadata artifact。
- command policy 的机器可读决策模块已经存在；运行时仍通过既有 ToolExecutor normalize 和 Agent Loop disabled feedback gate 执行阻断。本阶段没有重写整个 Permission System。

## 禁止降级项

- 不能直接在用户原始仓库目录中运行 agent workspace。
- 不能让 Task Adapter 创建 workspace、运行 setup、运行测试或生成 baseline。
- 不能信任任务 YAML 声明的 local repository clean 状态或 current commit 来覆盖真实 Git 状态。
- 不能在 `test_feedback_policy=disabled` 时让模型通过 bash 运行 pytest、`python -m pytest`、tox、nox 或 task test command。
- 不能把完整 decontamination metadata、隐藏测试反馈、gold patch 或 provider raw payload 放入训练 JSONL。
- 不能把 Docker execution mode 写成已完成能力。

## 已知限制

- public snapshot 不联网下载；必须提供预下载 archive 才能 materialize。
- 本阶段没有新增非 pytest verifier runner，只新增 parser policy helper 和 generic exit-code output policy 测试。实际正式 verifier 仍是现有 pytest runner。
- decontamination metadata ref 尚未生成 artifact；当前只记录 `decontamination_status` 和预留 ref 字段。
- Docker backend、任务集扩展和最终全局验收属于后续阶段。

## 是否偏离设计文档

未发现需要违反设计文档的实现。Stage 12 实现遵循 `docs/v2/implementation-plan.md` 和 `docs/11-object-model-config-and-data-flow.md`：

- `SourceCheckout` 只作为代码内 materialization 结果对象。
- `SourceCheckoutFacts` 作为 run facts 和 metadata facts。
- Task Adapter 不拥有 workspace lifecycle。
- Workspace Adapter 拥有 source checkout materialization。
- Exporter 只读取已有 run directory，不重新运行 verifier 或改写事实。

## sub agent 审查结论

已安排只读 sub agent 审查。初审发现 4 个 P2 和 2 个 P3：

- P2：local repository 的 dirty 状态和 current commit 初始实现可能被 YAML 声明绕过。
- P2：`SourceCheckoutFacts` 初始只在 `run_config_facts.json` 中，不在最终 `run_metadata.json` 中直接呈现。
- P2：export metadata 的 `decontamination_status` 初始来自 task 层，而不是 materialized source facts。
- P2：`VerifierParserPolicy` 初始只是孤立 helper，没有接入实际 baseline quality gate。
- P3：decontamination metadata ref 尚未生成 artifact。
- P3：command policy 决策模块和运行时 ToolExecutor/Permission System 的事实记录还没有完全统一。

处理结果：

- P2 已修复：local repository 总是读取真实 Git HEAD 和 `git status --short`，声明不一致会拒绝。
- P2 已修复：最终 `run_metadata.json` 新增 `source_checkout` 和 `environment_spec_hash`。
- P2 已修复：export metadata 优先使用 materialized source facts 的 decontamination status。
- P2 已修复：baseline quality gate 调用 parser policy issue check。
- P3 部分处理：local_repository 的 Git HEAD/status 不可读取已升级为拒绝。
- P3 记录为后续项：完整 decontamination metadata artifact 和 command policy 运行时决策统一事实记录留到后续增强。

复审确认 P1/P2 已关闭。审查记录保存到 `docs/v2/review/implementation/stage-12-review.md`。

## 是否可以进入下一阶段

可以进入 Stage 13。进入下一阶段前，Stage 12 commit 必须只包含当前阶段相关代码、测试、阶段日志和审查记录。
