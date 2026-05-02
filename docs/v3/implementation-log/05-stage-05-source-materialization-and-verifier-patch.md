# V3 Stage 05 Source Materialization And Verifier Patch

## 目标

阶段 5 的目标是让 RepoHarness 从固定本地 archive 或固定本地 mirror materialize source，并为 verifier workspace 准备 evaluator-only verifier patch / test patch。本阶段不实现阶段 6 的 fail-to-pass / pass-to-pass final verifier，也不把官方 SWE-Bench harness report 当作 final verifier result。

## 实现内容

新增 `build-v3-source-materialization` 和 `inspect-v3-source-materialization`：

- builder 显式接收阶段 4 task set 目录、SWE-Bench-like 固定 source archive manifest、hidden verifier inputs JSONL 和输出目录。
- 正式 materialization 只读取本地固定 archive 或本地固定 mirror，不从浮动网络 clone 或默认分支读取 source。
- 真实 repository-level task 使用阶段 4 generated task 定义和 source facts materialize。
- SWE-Bench-like task 使用新增的受版本控制 source archive manifest materialize。
- 对 SWE-Bench-like verifier workspace 应用 evaluator-only `test_patch`。
- agent workspace 从 base source checkout 复制，不应用 verifier patch / test patch。
- 输出 `source_checkout_facts.json` 和 `source_materialization_report.json`。

新增固定 source archive 输入：

- `tests/fixtures/v3/swebench_lite_fixed/source_archives/source_archive_manifest.json`
- `tests/fixtures/v3/swebench_lite_fixed/source_archives/pytest-dev__pytest-7220-56bf819c2f4eaf8b36bd8c42c06bb59d5a3bfc0f.tar.gz`
- `tests/fixtures/v3/swebench_lite_fixed/source_archives/pytest-dev__pytest-8365-4964b468c83c06971eb743fbc57cc404f760c573.tar.gz`
- `tests/fixtures/v3/swebench_lite_fixed/source_archives/sympy__sympy-24909-d3b4158dea271485e3daa11bf82e69b8dab348ce.tar.gz`

实现细节：

- `v3_source_materialization.py` 生成 per-task `source_checkout_facts.json`，聚合 `source_checkout_facts.json`，以及 `source_materialization_report.json`。
- `source_materialization_report.json` 显式记录 `source_provenance_ref`、`expected_source_tree_hash`、`remote_url`、`resolved_commit`、`archive_sha256` 或 `mirror_sha256`，以及 source materialization command facts。
- `inspect-v3-source-materialization` 重新读取 artifact refs，校验 source tree hash、source provenance、checkout facts、workspace refs、verifier patch visibility 和 agent workspace contamination。
- inspect 不只信任 report 自述；它会读取 evaluator-only verifier patch artifact，过滤 base source 中原本存在的普通代码片段后，扫描 agent workspace 和 task definition 是否包含 verifier patch 内容。
- `git apply` 通过 `GIT_CEILING_DIRECTORIES` 限定在 verifier workspace，避免向上发现 RepoHarness 自身 `.git`。
- `workspace.materialization` 支持没有 `.git` 目录但带固定 `base_commit` 的 `fixed_local_mirror` 目录，并对 tar extraction 使用 `filter="data"`。

## 主要修改文件

- `src/repo_harness/v3_source_materialization.py`
- `src/repo_harness/cli/main.py`
- `src/repo_harness/run_metadata/schemas.py`
- `src/repo_harness/workspace/materialization.py`
- `tests/unit/test_v3_source_materialization.py`
- `tests/fixtures/v3/swebench_lite_fixed/source_archives/source_archive_manifest.json`
- `tests/fixtures/v3/swebench_lite_fixed/source_archives/*.tar.gz`
- `docs/v3/implementation-log/05-stage-05-source-materialization-and-verifier-patch.md`
- `docs/v3/review/implementation/stage-05-review.md`

## 机器产物

阶段 5 source materialization 产物目录：

- `runs/v3-stage-05-source-materialization-20260502T181500Z/`

关键机器产物：

- `runs/v3-stage-05-source-materialization-20260502T181500Z/source_checkout_facts.json`
- `runs/v3-stage-05-source-materialization-20260502T181500Z/source_materialization_report.json`
- `runs/v3-stage-05-source-materialization-20260502T181500Z/tasks/*/source_checkout_facts.json`
- `runs/v3-stage-05-source-materialization-20260502T181500Z/tasks/*/source_provenance.json`
- `runs/v3-stage-05-source-materialization-20260502T181500Z/tasks/*/task_definition.yaml`
- `runs/v3-stage-05-source-materialization-20260502T181500Z/tasks/*/agent_workspace/`
- `runs/v3-stage-05-source-materialization-20260502T181500Z/tasks/*/verifier_workspace/`
- `runs/v3-stage-05-source-materialization-20260502T181500Z/tasks/*/evaluator_only/verifier.patch`

## 验证命令和结果

- `PATH=.venv/bin:$PATH python -m compileall src`：通过。
- `PATH=.venv/bin:$PATH repo-harness build-v3-source-materialization --task-set-dir runs/v3-stage-04-task-adapter-20260502T170000Z --swebench-source-manifest tests/fixtures/v3/swebench_lite_fixed/source_archives/source_archive_manifest.json --hidden-verifier-inputs docs/v3/evidence/swebench-lite-fixed/evaluator_only/hidden_verifier_inputs.jsonl --output-dir runs/v3-stage-05-source-materialization-20260502T181500Z`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-v3-source-materialization runs/v3-stage-05-source-materialization-20260502T181500Z --report runs/v3-stage-05-source-materialization-20260502T181500Z/source_materialization_report.json --assert-complete`：通过。
- `PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v3_source_materialization.py tests/unit/test_repo_materialization.py tests/integration/test_repo_materialization_smoke.py -q`：`13 passed`。
- `PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v3_source_materialization.py tests/unit/test_v3_task_set.py tests/unit/test_repo_materialization.py tests/integration/test_repo_materialization_smoke.py -q`：`24 passed`。
- `PATH=.venv/bin:$PATH python -m pytest -q`：`416 passed`。
- `PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-v3-swebench-fixture --fixture-dir tests/fixtures/v3/swebench_lite_fixed --evidence-dir docs/v3/evidence/swebench-lite-fixed --manifest tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/v3_feasibility_input_manifest.json --assert-frozen`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-v3-task-set runs/v3-stage-04-task-adapter-20260502T170000Z --assert-complete`：通过。

## 正例证据

- `source_materialization_report.json` 记录 `task_count=6`。
- 3 个真实 repository-level task materialize 成 base source、agent workspace 和 verifier workspace。
- 3 个 SWE-Bench-like task 从固定本地 source archive materialize，并在 verifier workspace 应用 evaluator-only `test_patch`。
- 6 个 task 的 `expected_source_tree_hash` 与 materialized `source_tree_hash` 一致，并由 per-task `source_provenance.json` 绑定到阶段 4 source facts 或 SWE-Bench-like source archive manifest。
- `source_checkout_facts.json` 记录 source type、remote URL 或 mirror source、base commit、resolved commit、archive sha256 或 mirror sha256、stripped 状态、checkout path redaction status 和 materialization command facts。
- 3 个 SWE-Bench-like task 的 `agent_workspace_ref.sha256` 等于 base `source_tree_hash`。
- 3 个 SWE-Bench-like task 的 `verifier_workspace_ref.sha256` 不等于 base `source_tree_hash`，证明 verifier workspace 包含 test patch 变更。
- `agent_workspace_contains_verifier_patch=false`。

## 负例证据

单元测试覆盖：

- source archive manifest 允许浮动网络 source 时 builder 拒绝。
- source archive sha256 漂移时 builder 拒绝。
- source archive manifest `source_tree_hash` 漂移时 builder 拒绝。
- 真实仓库 source facts `source_tree_hash` 漂移时 builder 拒绝。
- report 声称 agent workspace 包含 verifier patch 时 inspect 拒绝。
- agent workspace 中真实写入 verifier patch 片段时 inspect 拒绝。
- inspect 会拒绝 verifier workspace 未体现 verifier patch 变更。

## 允许降级项

阶段 5 只准备 verifier workspace 和 source facts，不运行 fail-to-pass / pass-to-pass tests，不生成 final verifier result。真实 repository-level task 当前没有 verifier patch，所以 verifier patch 状态为 `not_applicable`。

## 禁止降级项

- 不允许正式 materialization 从浮动网络 clone 或浮动默认分支读取 source。
- 不允许把官方 SWE-Bench harness report 当作 RepoHarness final verifier。
- 不允许把 raw `test_patch`、raw `FAIL_TO_PASS`、raw `PASS_TO_PASS` 写入 generated task、prompt 或 agent workspace。
- 不允许只根据 `git apply` exit code 声称 patch 已应用；verifier workspace hash 必须不同于 base source hash。

## 已知限制

阶段 5 的 source materialization report 是独立阶段产物，尚未被 Agent Loop run metadata、export audit 或 final acceptance inputs 绑定；这些属于后续阶段。

## 设计偏离

没有偏离阶段 5 范围。SWE-Bench-like source archive 是受控预取产生的本地固定 archive；正式 builder 只读取这些本地文件。

## 审查结论

只读子代理 `Franklin` 首轮审查发现 1 个 P1 和 2 个 P2，均已修复并重新验证。最终复审结论记录在 `docs/v3/review/implementation/stage-05-review.md`；若复审未发现新的 P1/P2，则阶段 5 可以进入阶段 6。
