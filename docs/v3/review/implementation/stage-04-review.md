# V3 Stage 04 Implementation Review

## 审查范围

本审查覆盖阶段 4 的真实 repository-level task adapter、SWE-Bench-like fixed JSONL adapter、task facts 生成和 `inspect-v3-task-set`。

不覆盖阶段 5 source materialization、阶段 6 verifier patch / fail-to-pass / pass-to-pass final verifier，也不把本阶段构建的 task set 视为完整 SWE-Bench-like evaluation。

## 本地自审

本地自审检查了以下维度：

- 阶段 4 是否只生成 adapter facts、manifest 和 TaskDefinition 兼容输出。
- 真实 repository-level task 是否至少 3 个，且至少 1 个来自公开固定 archive。
- 真实 repository-level task 是否避免 3 个全本地 fixture 或重复 source hash。
- SWE-Bench-like adapter 是否默认读取阶段 0 adapter-visible input，而不是 `runs/` 目录。
- SWE-Bench-like adapter 是否没有读取 raw `test_patch`、raw `FAIL_TO_PASS`、raw `PASS_TO_PASS`、gold patch prediction 或 official harness report。
- `inspect-v3-task-set` 是否重新读取 artifact refs 并验证 sha256 / size。

## 自审和子代理发现

### P2：builder 读取 evaluator-only manifest 进行 sha256 校验

初版 builder 会读取 `docs/v3/evidence/swebench-lite-fixed/evaluator_only/evaluator_evidence_manifest.json` 计算 sha256。虽然没有读取 raw hidden verifier material，但 adapter 默认不应读取 evaluator-only 目录。

修复：builder 改为只转录阶段 0 `task_input_manifest.json` 中的 evaluator evidence ref。`inspect-v3-task-set` 作为只读检查命令继续负责读取和校验该 ArtifactRef。

### P2：SWE-Bench-like 行级 revision 漂移未被拒绝

子代理指出，初版只校验 manifest 顶层 dataset revision 和整份 JSONL sha256，没有逐行校验 `dataset_name`、`dataset_revision`、`dataset_split`、`problem_statement_sha256` 和 `model_visible_field_sha256`。

修复：新增 `_assert_swebench_row_matches_manifest`，逐行校验固定 dataset 字段、problem statement hash、model-visible field hash 和 hidden evidence hash。新增负例测试证明即使 JSONL sha 和 manifest task hash 同步更新，行级 revision 漂移仍会被拒绝。

### P2：SWE-Bench-like generated task 缺少可运行 final-only 标记

子代理指出，`TaskAdapterFacts.final_only_policy` 不是 `resolve_feedback_policy` 的运行时输入；generated `TaskDefinition` 自身必须带 `swe_bench_like_final_only` 或 `final_only` 标记。

修复：SWE-Bench-like generated task 写入 `swe_bench_like_final_only` / `final_only` tags 和 metadata。`resolve_feedback_policy` 在没有显式 runtime override 时，对 final-only task 默认解析为 `disabled`，避免 scaffold 默认 hidden feedback 回流。

### P2：inspect 对重复 source 的拒绝依赖 manifest 自述

子代理指出，初版 `inspect-v3-task-set` 只用 `real_repository_task_manifest.json` 中的 source hash 判断重复，没有打开 source facts 反查。

修复：inspect 会读取 `source_facts_ref`，验证 `RealRepositorySourceFacts`，反查 `source_kind`、`source_tree_hash`、`local_materialization_ref` 和 `verifier_evidence_ref`，并基于 source facts 计算公开 archive 数量和重复 source hash。

### P3：公开 archive source facts 丢失 dataset/source revision

子代理指出，公开任务的 `RealRepositorySourceFacts.dataset_source_revision` 没有继承真实任务输入 manifest 顶层 revision。

修复：builder 将顶层 `dataset_source_revision` 注入每个真实仓库 task record，source facts 自身记录该 revision。

### P3：绝对 fixture 路径调用下 adapter input path 比较过窄

初版使用字符串比较 `adapter_visible_input_ref.path` 和 `tasks_path.as_posix()`。当调用方传入绝对 fixture 路径时会误报 path mismatch。

修复：改为解析后的路径比较，并补充单元测试覆盖。

## 负例覆盖

已有单元测试覆盖：

- 空字段拒绝。
- SWE-Bench-like dataset revision 漂移拒绝。
- SWE-Bench-like JSONL sha256 漂移拒绝。
- SWE-Bench-like 行级 dataset revision 漂移拒绝。
- 全本地真实仓库 task set 拒绝。
- 重复本地 source hash 拒绝。
- manifest source hash 与 source facts 不一致拒绝。

## 子代理审查

只读子代理 `Meitner` 第一轮发现 3 个 P2 和 1 个 P3，均已修复。复核结论：

- P1：无。
- P2：无。
- P3：无。
- 阶段边界：没有提前实现阶段 5 的 `source_checkout_facts.json`、`source_materialization_report.json`，也没有提前实现阶段 6 的 `swebench_like_verifier_plan.json`、`final_verifier_result.json` 或 F2P/P2P final verifier。
- 污染边界：SWE-Bench-like adapter 没有读取 evaluator-only raw `test_patch`、raw `FAIL_TO_PASS`、raw `PASS_TO_PASS`；hidden verifier material 仅以 hash/count 形式进入 facts/metadata，且 metadata 不进入 `agent_visible_view`。
- 结论：允许进入阶段 5。

## 结论

阶段 4 当前实现未发现 P1、P2 或 P3 阻断项，可以进入阶段 5。
