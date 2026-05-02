# V3 Stage 04 Real Repository And Fixed Task Adapter

## 目标

阶段 4 的目标是让 RepoHarness 能读取真实 repository-level task 输入和阶段 0 固定 SWE-Bench-like JSONL 快照，并生成自己的 task facts、manifest 和 `TaskDefinition` 兼容输出。本阶段不执行正式 source materialization，不应用 verifier patch，也不实现 RepoHarness 自有 fail-to-pass / pass-to-pass final verifier；这些属于阶段 5 和阶段 6。

## 实现内容

新增 `build-v3-task-set` 和 `inspect-v3-task-set`：

- `build-v3-task-set` 显式接收真实仓库任务输入、SWE-Bench-like fixture、阶段 0 `task_input_manifest.json`、evaluator-only evidence 根目录和输出目录。
- builder 读取 `tests/fixtures/v3/real_repositories/real_repository_task_inputs.json`，生成 3 个真实 repository-level task。
- 真实任务中包含 1 个公开固定 archive 来源：`pypa/sampleproject` 固定 commit `621e4974ca25ce531773def586ba3ed8e736b3fc` 的本地归档。
- 另外 2 个真实任务来自两个不同的固定本地 mirror：`buggy_calculator` 和 `import_config_bug`，source tree hash 不重复。
- builder 读取阶段 0 adapter-visible 文件 `tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/swebench_like_tasks.jsonl`，生成 3 个 accepted SWE-Bench-like task facts。
- builder 对 SWE-Bench-like evaluator-only evidence 只转录阶段 0 manifest 中的 artifact ref，不读取 raw `test_patch`、raw `FAIL_TO_PASS`、raw `PASS_TO_PASS`、official harness report 或 gold patch prediction。
- `inspect-v3-task-set` 只读检查 `task_adapter_facts.json`、`real_repository_task_manifest.json` 和 `swebench_like_task_facts.json`，并重新读取 artifact refs 校验 sha256 和 size。
- `inspect-v3-task-set` 会打开 `source_facts_ref`，用 source facts 反查 `source_kind`、`source_tree_hash`、`local_materialization_ref` 和 `verifier_evidence_ref`，避免只信 manifest 自述。
- SWE-Bench-like generated task 写入 `swe_bench_like_final_only` / `final_only` tags 和 metadata；`resolve_feedback_policy` 在无显式 runtime override 时把 final-only task 解析为 `disabled`。

新增 schema 字段：

- `SweBenchLikeTaskFacts.environment_setup_commit`
- `SweBenchLikeTaskFacts.problem_statement_sha256`
- `SweBenchLikeTaskFacts.test_patch_sha256`
- `SweBenchLikeTaskFacts.fail_to_pass_selectors_sha256`
- `SweBenchLikeTaskFacts.pass_to_pass_selectors_sha256`
- `SweBenchLikeTaskFacts.fail_to_pass_selector_count`
- `SweBenchLikeTaskFacts.pass_to_pass_selector_count`

## 主要修改文件

- `src/repo_harness/v3_task_set.py`
- `src/repo_harness/cli/main.py`
- `src/repo_harness/tasks/schemas.py`
- `tests/unit/test_v3_task_set.py`
- `tests/unit/test_v3_schemas.py`
- `tests/fixtures/v3/real_repositories/real_repository_task_inputs.json`
- `tests/fixtures/v3/real_repositories/archives/pypa-sampleproject-621e4974ca25ce531773def586ba3ed8e736b3fc.tar.gz`
- `tests/fixtures/v3/real_repositories/verifier_evidence/*.json`

## 机器产物

阶段 4 task adapter 产物目录：

- `runs/v3-stage-04-task-adapter-20260502T170000Z/`

关键机器产物：

- `runs/v3-stage-04-task-adapter-20260502T170000Z/task_adapter_facts.json`
- `runs/v3-stage-04-task-adapter-20260502T170000Z/real_repository_task_manifest.json`
- `runs/v3-stage-04-task-adapter-20260502T170000Z/swebench_like_task_facts.json`
- `runs/v3-stage-04-task-adapter-20260502T170000Z/real_repository_source_facts/*.json`
- `runs/v3-stage-04-task-adapter-20260502T170000Z/swebench_like_task_facts/*.json`
- `runs/v3-stage-04-task-adapter-20260502T170000Z/generated_tasks/real_repository/*.yaml`
- `runs/v3-stage-04-task-adapter-20260502T170000Z/generated_tasks/swebench_like/*.yaml`

## 验证命令和结果

- `PATH=.venv/bin:$PATH python -m compileall src`：通过。
- `PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v3_task_set.py tests/unit/test_v3_schemas.py tests/unit/test_task_adapter.py tests/unit/test_task_schema.py tests/unit/test_scaffold_planner_coder_verifier.py tests/unit/test_scaffold_single_shot_patch.py -q`：`62 passed`。
- `PATH=.venv/bin:$PATH python -m pytest -q`：`409 passed`。
- `PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-v3-swebench-fixture --fixture-dir tests/fixtures/v3/swebench_lite_fixed --evidence-dir docs/v3/evidence/swebench-lite-fixed --manifest tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/v3_feasibility_input_manifest.json --assert-frozen`：通过。
- `PATH=.venv/bin:$PATH repo-harness build-v3-task-set --real-repository-inputs tests/fixtures/v3/real_repositories/real_repository_task_inputs.json --swebench-fixture-dir tests/fixtures/v3/swebench_lite_fixed --swebench-manifest tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/task_input_manifest.json --swebench-evidence-dir docs/v3/evidence/swebench-lite-fixed --output-dir runs/v3-stage-04-task-adapter-20260502T170000Z`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-v3-task-set runs/v3-stage-04-task-adapter-20260502T170000Z --assert-complete`：通过。
- `PATH=.venv/bin:$PATH repo-harness validate-task runs/v3-stage-04-task-adapter-20260502T170000Z/generated_tasks/real_repository/realrepo_public_sampleproject_add_two.yaml`：通过。
- `PATH=.venv/bin:$PATH repo-harness validate-task runs/v3-stage-04-task-adapter-20260502T170000Z/generated_tasks/real_repository/realrepo_local_buggy_calculator.yaml`：通过。
- `PATH=.venv/bin:$PATH repo-harness validate-task runs/v3-stage-04-task-adapter-20260502T170000Z/generated_tasks/real_repository/realrepo_local_import_config_bug.yaml`：通过。

## 正例证据

- `real_repository_task_manifest.json` 记录 `task_count=3`、`public_archive_count=1` 和 `unique_source_tree_hash_count=3`。
- 公开 archive 记录 remote URL、base commit、archive sha256、source tree hash、本地 archive ref、decontamination status 和 verifier evidence ref。
- 3 个 SWE-Bench-like accepted task 都记录 dataset name、revision、split、instance id、repo、base commit、environment setup commit、test patch sha256、fail-to-pass selector hash/count 和 pass-to-pass selector hash/count。
- 3 个真实仓库生成任务可以通过现有 `validate-task` 进入 TaskAdapter。
- 公开 archive source facts 记录 `dataset_source_revision=repo_harness_v3_real_repository_tasks_20260502`。
- SWE-Bench-like final-only generated task 在 policy resolution 中默认得到 `test_feedback_policy=disabled`。

## 负例证据

单元测试覆盖：

- 真实仓库任务字段为空时 builder 拒绝。
- SWE-Bench-like dataset revision 漂移时 builder 拒绝。
- SWE-Bench-like JSONL sha256 漂移时 builder 拒绝。
- SWE-Bench-like 行级 dataset revision 漂移时 builder 拒绝，即使 JSONL sha 和 manifest task hash 同步更新。
- `inspect-v3-task-set` 拒绝 3 个真实仓库任务全部来自本地 fixture。
- `inspect-v3-task-set` 拒绝 1 个公开任务加 2 个重复本地 fixture source hash 的组合。
- `inspect-v3-task-set` 拒绝 manifest source hash 与 source facts 不一致的篡改。

## 允许降级项

阶段 4 只生成 adapter facts 和任务定义，不执行 source checkout、正式 Docker run、verifier patch apply 或 final verifier。SWE-Bench-like generated task YAML 暂不包含 raw fail-to-pass / pass-to-pass selector；它只绑定阶段 0 固定输入中的 selector hash 和 evaluator-only evidence ref。raw selector 和 raw test patch 的解析属于阶段 6。

## 禁止降级项

- 不允许从 `runs/` 下的可行性实验目录作为默认 adapter 输入。
- 不允许从 Hugging Face 浮动默认分支读取 SWE-Bench-like task。
- 不允许 adapter 读取 raw `test_patch`、raw `FAIL_TO_PASS`、raw `PASS_TO_PASS`、gold patch prediction 或 official harness report。
- 不允许用 3 个重复本地 fixture 冒充真实 repository-level task set。
- 不允许把当前 task adapter 产物表述为完整 SWE-Bench Lite 复现、公开榜单结果或已完成 final verifier。

## 已知限制

公开 `pypa/sampleproject` 任务在阶段 4 仅作为固定 archive 来源和 task adapter 证据；它没有在本阶段运行 Docker final verifier。正式 source materialization、verifier patch 隔离和 final verifier evidence 必须在阶段 5 和阶段 6 完成。

## 设计偏离

没有偏离阶段 4 范围。builder 为了校验公开 archive 的 source tree hash 会在临时目录中安全解包归档并计算 hash，但不会把该临时目录作为正式 source materialization，也不会生成 `source_checkout_facts.json` 或 `source_materialization_report.json`。

## 审查结论

只读子代理第一轮发现 3 个 P2 和 1 个 P3：行级 SWE-Bench-like revision 漂移未拒绝、generated task 缺少可运行 final-only 标记、inspect 重复 source 检查依赖 manifest 自述、公开 archive source facts 缺少 dataset/source revision。全部修复后，子代理复核未发现新的 P1、P2 或 P3，并明确允许进入阶段 5。
