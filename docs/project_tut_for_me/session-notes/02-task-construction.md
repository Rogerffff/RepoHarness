# 第 2 章：任务构造，SWE-Bench-like 和 GitHub PR / issue

## 本章链路图

```text
PR / issue feasibility run
-> adapter-visible task input
-> evaluator-only evidence
-> v4_task_freeze
-> task_freeze_manifest.json
-> generated_task_definition.jsonl

SWE-Bench-like dataset input
-> fixed source materialization
-> hidden verifier input
-> selector cache
-> verifier plan
-> swebench_like_task_manifest.json
```

## 本章实际运行或查看的命令

```bash
jq '{accepted_auditable_task_definition_count, accepted_task_refs}' \
  docs/v4/evidence/task-source-freeze/task_freeze_manifest.json

jq '{model_visible_source_count, records: [.records[] | {task_id, candidate_id, task_source_tag, trainable_candidate_source, visibility_scan_clean, path}][0:8]}' \
  docs/v4/evidence/task-source-freeze/adapter_visible_task_input_manifest.json

jq '{schema_version, task_count, accepted_task_ids, official_harness_report_used_as_final_verifier, entries: [.entries[] | {task_id, repo, final_verifier_accepted, hidden_visibility_policy, verifier_plan_ref, selector_cache_ref}][0:3]}' \
  runs/v3-stage-06-swebench-like-20260502T191500Z/swebench_like_task_manifest.json
```

真实产物结论：

- V4 PR / issue accepted auditable task definition 数量为 `8`。
- 8 个 adapter-visible task input 都是 `trainable_candidate_source=true`，且 `visibility_scan_clean=true`。
- SWE-Bench-like 固定任务数量为 `3`：`pytest-dev__pytest-7220`、`pytest-dev__pytest-8365`、`sympy__sympy-24909`。
- SWE-Bench-like manifest 明确记录 `official_harness_report_used_as_final_verifier=false`。
- SWE-Bench-like verifier plan 和 selector cache 都是 `evaluator_only`。

## 源码入口和对象流

关键入口：

- `src/repo_harness/tasks/schemas.py:281`：`TaskDefinition`
- `src/repo_harness/tasks/schemas.py:342`：`RunnableTask`
- `src/repo_harness/tasks/schemas.py:366`：`RunnableTask.from_definition`
- `src/repo_harness/tasks/schemas.py:394`：`agent_visible_view`
- `src/repo_harness/tasks/adapter.py:47`：加载和规范化任务
- `src/repo_harness/workspace/materialization.py:36`：源码物化
- `src/repo_harness/v3_swebench_like.py:35`：构造 SWE-Bench-like verifier plan 和 evidence
- `src/repo_harness/v4_task_freeze.py:95`：构造 V4 task freeze evidence

关键理解：

- `TaskDefinition` 是完整任务定义，包含 verifier-only、reward-only、hidden-reference 等字段。
- `RunnableTask` 是运行时对象，`agent_visible_view()` 决定模型可见投影。
- PR / issue 任务冻结的核心是把真实 issue / PR provenance、base commit、source archive、baseline verifier、post-patch verifier、flaky probe、license 和 use boundary evidence 绑定起来。
- SWE-Bench-like 任务冻结的核心是把 hidden test patch、fail-to-pass selectors、pass-to-pass selectors、selector cache 和 verifier plan 留在 evaluator-only 侧。

## 面试追问与推荐回答

问：任务为什么不能只是一个 prompt？

答：软件工程训练任务必须绑定源码、base commit、环境、验证器、可见性策略和证据边界。否则模型轨迹无法复现，也无法判断是否泄漏隐藏测试或参考答案。

问：PR / issue 任务怎样避免把答案泄漏给模型？

答：模型只看到 adapter-visible task input，例如问题陈述、公开行为提示和仓库文件。PR patch、hidden verifier、audit-only provenance 和 evaluator-only material 不进入 `agent_visible_view()`，并由 task visibility scan 和 contamination scan 复核。

问：SWE-Bench-like 和官方 SWE-Bench harness 有什么区别？

答：这里是固定子集和 RepoHarness-owned evidence 链路，目标是训练轨迹和内部评测审计，不是公开榜单复现。它保留 fail-to-pass / pass-to-pass 语义，但不把 official harness report 当作 final verifier。
