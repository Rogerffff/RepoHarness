# Stage 12 只读审查记录

## 审查方式

本阶段安排了只读 sub agent 审查。审查 agent 没有修改文件，也没有运行会写入仓库文件的命令。主流程根据审查结论修复了 P2，并处理了可以在 Stage 12 范围内完成的 P3。

## 审查重点

- 是否严格限于 Stage 12 的 repo materialization、命令环境策略门和任务来源扩展。
- 是否复用 `SourceCheckout`、`SourceCheckoutFacts`、`WorkspaceBackend`、`WorkspaceAdapter` 和 `WorkspacePaths`。
- 是否新增含义重叠的 source facts 别名。
- Task Adapter 是否只解析和校验 task source specification。
- source materialization 是否由 Workspace Adapter 或 `workspace/materialization.py` 完成。
- 正式 agent workspace 是否来自可审计 source checkout。
- local archive、local repository、public snapshot 是否记录必要事实。
- dirty local repository 是否默认拒绝。
- source hash、base commit、decontamination status 是否进入 run metadata 和 export metadata。
- command policy 是否阻断 `test_feedback_policy=disabled` 下的 bash pytest、tox、nox 绕过。
- environment spec hash 是否稳定且进入 compare facts。
- verifier parser policy 是否覆盖 pytest、非 pytest和低置信阻断。
- 第一版 replay、verifier、permission、workspace、trajectory 和 export 是否保持兼容。

## 初审发现

### P1

未发现 P1。

### P2

1. 本地仓库 dirty 状态可以被任务声明绕过。
   - 风险：如果 `LocalRepositorySource.working_tree_clean=true` 被直接信任，dirty repository 可以在 `allow_dirty_snapshot=false` 时进入 source checkout。
   - 处理：materialization 总是读取真实 `git status --short`；如果 YAML 声明和真实状态不一致，拒绝任务来源。`current_commit` 同样必须和真实 HEAD 一致。

2. `SourceCheckoutFacts` 没有写入最终 `run_metadata.json`。
   - 风险：最终 metadata 不能独立报告 Stage 12 source checkout 事实。
   - 处理：`RunMetadata` 新增 `source_checkout` 和 `environment_spec_hash`，writer 从 `run_config_facts.environment_fingerprint.workspace_execution` 中读取并写入。

3. 导出 metadata 使用 task decontamination 而不是 materialized source facts。
   - 风险：local archive、local repository 或 public snapshot 的 source spec decontamination status 与 task 层状态不一致时，export metadata 会记录错误事实。
   - 处理：`_safe_metadata()` 中 `decontamination_status` 优先来自 `source_checkout.decontamination_status`，缺失时才回退到 task 层。

4. `VerifierParserPolicy` 只做孤立 helper，未接入任务质量门。
   - 风险：低置信 parser policy 无法影响 baseline quality gate。
   - 处理：`_derive_baseline_status()` 和 `_baseline_hard_error()` 调用 `_baseline_parser_policy_issue()`，使用 `VerifierParserPolicy` 的阈值和阻断规则。

### P3

1. `decontamination_metadata_ref` 已预留，但本阶段没有生成完整 metadata artifact。
   - 处理：记录为后续项。

2. command policy 决策模块和运行时 ToolExecutor / Permission System 的事实记录还没有完全统一。
   - 处理：记录为后续项；Stage 12 已保证 `test_feedback_policy=disabled` 的 bash pytest 路径被路由到 `run_tests` 并拒绝，tox/nox 被 command policy 识别为测试命令，不作为绕过路径。

3. local repository 如果不是 Git repository，初始实现可能走 fallback。
   - 处理：已收紧为拒绝；local repository 必须有可读取的 Git HEAD 和 status。

## 修复后复审

sub agent 复审确认：

- P1/P2 已关闭。
- local repository 不再信任 YAML 声明的 `working_tree_clean` 和 `current_commit`。
- `SourceCheckoutFacts` 和 `environment_spec_hash` 已写入最终 `run_metadata.json`。
- export metadata 的 `decontamination_status` 优先来自 materialized source facts。
- `VerifierParserPolicy` 已接入 baseline quality gate。
- 剩余内容均为 P3 或后续增强，不阻断 Stage 12 提交。

## 修复后验证

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

验证结果：

- Stage 12 验收测试全部通过。
- 全量测试通过，332 个测试通过。
- local archive materialization smoke 通过。
- SFT 导出 audit passed，包含 1 个 trainable 样本。

## 结论

审查提出的 P2 已修复并通过测试覆盖。P3 中可以在 Stage 12 范围内处理的 local repository fallback 已处理；其余 P3 记录为后续增强。Stage 12 可以提交，并可以进入 Stage 13。
