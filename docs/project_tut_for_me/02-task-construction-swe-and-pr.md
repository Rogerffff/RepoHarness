# 任务构造：SWE-Bench-like 和 GitHub PR / issue

## 任务不是 prompt，而是 frozen execution contract

RepoHarness 中的任务不是单纯的自然语言 issue。一个可运行任务至少包含：

- 模型可见的 issue statement。
- 固定的源码来源，例如本地 archive、public snapshot archive、固定本地镜像。
- base commit 或 synthetic base identity。
- setup command 和 test command。
- fail-to-pass tests 与 pass-to-pass tests。
- 可见性策略，决定哪些字段模型可见、哪些字段只属于 verifier。
- decontamination 和 provenance metadata。
- 环境描述，例如 Python 版本、依赖状态策略、source archive sha256。

这些字段由 `src/repo_harness/tasks/schemas.py` 定义，磁盘上的 YAML 先进入 `TaskDefinition`，随后被转换成 `RunnableTask`。

## TaskDefinition 到 RunnableTask

任务加载入口是：

```text
src/repo_harness/tasks/adapter.py::load_task
```

流程如下：

```text
读取 YAML
-> TaskDefinition.model_validate
-> normalize repo_source_spec
-> validate setup_command / test_command
-> to_verifier_config
-> RunnableTask.from_definition
```

`TaskDefinition` 保留完整定义，包括 evaluator-only 或 hidden reference 字段。`RunnableTask` 是运行时对象，提供 `agent_visible_view()`，只把允许模型看到的内容交给 `ContextBuilder`。

一个容易忽略的点：`agent_visible_view()` 当前会包含 `setup_command`、`test_command`、`environment` 等字段；但如果是 SWE-Bench-like final-only 任务，`ContextBuilder` 会把 test command 隐去，返回 `test_command=None` 和 `test_command_visibility=redacted_final_only`。

## repo_source_spec 的几种来源

源码物化由：

```text
src/repo_harness/workspace/materialization.py::materialize_source
```

支持的 source spec 包括：

- `FixtureRepositorySource`：测试 fixture 中的小仓库。
- `LocalRepositorySource`：固定本地仓库或本地镜像，可以检查 `current_commit` 和 dirty working tree。
- `LocalArchiveSource`：本地 archive，必须记录 `archive_sha256`、`expected_root_directory`、base identity。
- `PublicSnapshotSource`：公开仓库快照，但正式运行要求已经有预下载 archive，不在 formal run 中从网络实时下载。

V4 和 SWE-Bench-like 任务应优先理解为 archive / fixed snapshot，而不是运行时 `git clone`。这样才能保证同一个 task 在不同时间仍然指向同一份源码。

## SWE-Bench-like 任务构造

SWE-Bench-like 相关实现主要在：

```text
src/repo_harness/v3_swebench_like.py
src/repo_harness/v3_agent_runtime.py
```

虽然文件名保留 `v3`，但这部分能力仍然是当前 V4 链路的重要基础。V4 没有丢弃它，而是把它纳入更完整的 evidence 和 acceptance 体系。

构造输入通常包括：

- SWE dataset instance，例如 `instance_id`、`repo`、`base_commit`、problem statement。
- 固定 source archive。
- hidden `test_patch`。
- hidden `FAIL_TO_PASS` selectors。
- hidden `PASS_TO_PASS` selectors。
- gold patch 或 reference model patch，用于构造 evaluator evidence。

构造输出包括：

- adapter-visible task YAML。
- evaluator-only evidence manifest。
- selector cache。
- verifier patch ref。
- environment spec。
- baseline / gold / model_final verifier result。
- task manifest。

## SWE-Bench-like 的隐藏边界

SWE-Bench-like 的关键不是“能跑 pytest”，而是隐藏边界：

- 模型看到 issue statement 和源码。
- 模型不能看到 hidden test patch。
- 模型不能看到 fail-to-pass / pass-to-pass 的原始隐藏选择器。
- 模型通常不能在中间过程中运行 formal hidden verifier。
- final verifier 使用 evaluator-only verifier plan。

这由几个 schema 和 manifest 共同表达：

- `SweBenchLikeTaskFacts`
- `SweBenchLikeEnvironmentSpec`
- `SweBenchLikeVerifierPlan`
- selector cache
- evaluator-only evidence manifest

`SweBenchLikeTaskFacts` 里有两个非常关键的约束：

```text
final_only = True
model_visible_contains_hidden_material = False
```

这意味着这种任务不是 public leaderboard comparable 的官方 SWE-Bench 复刻，而是“固定子集、可审计、final-only”的 SWE-Bench-like 训练和评测素材。

## selector expansion

SWE 数据里可能给的是函数名或较粗的 selector。RepoHarness 会尝试把 selector 展开成 pytest node id。这一步由 `expand_swebench_selectors` 相关逻辑完成。

作用是：

- 把 evaluator-only selector 固定下来。
- 避免 final verifier 每次解析得到不同集合。
- 让 fail-to-pass / pass-to-pass 的数量和哈希进入 evidence。

这种 selector cache 不应该进入模型上下文，只应该被 final verifier 使用。

## SWE-Bench-like final verifier 怎样运行

agent loop 运行结束后，`run_task` 会检查：

```text
load_swebench_like_runtime_plan(loaded.runnable_task)
```

如果任务 metadata 显示它是 `swebench_like_fixed`，final verifier 不走普通的 `PytestVerifier.run_final`，而是走：

```text
src/repo_harness/v3_agent_runtime.py::run_swebench_like_final_verifier
```

核心过程：

```text
创建独立 final verifier workspace
-> 从 manifest 中的 baseline verifier workspace 复制源码
-> 应用 agent final patch
-> 使用冻结的 evaluator-only verifier plan 和 selector cache
-> 运行 fail-to-pass commands
-> 运行 pass-to-pass commands
-> 解析 pytest 输出
-> 写 swebench_like_agent_loop_final_verifier_report.json
-> 返回 VerifierResult
```

所以模型在 agent loop 中看到的是普通仓库任务，最终评分时才使用隐藏 verifier material。

## GitHub PR / issue 任务构造

V4 新增的更成熟任务来源是 auditable PR / issue task。相关设计文档是：

```text
docs/v4/pr-issue-task-source-plan.md
```

相关实现是：

```text
src/repo_harness/v4_implementation_inputs.py
src/repo_harness/v4_task_freeze.py
```

PR / issue 任务的构造目标是：从真实 GitHub issue 和修复 PR 中抽取一个可以让模型尝试修复的任务，但不能把 PR patch、隐藏测试意图或泄漏性材料直接给模型。

候选任务需要记录：

- repository，例如 `pallets/click`、`pytest-dev/pluggy`、`spf13/cobra`。
- issue URL 和 PR URL。
- base commit。
- merge commit 或 fix commit。
- fix patch sha256。
- upstream test patch sha256。
- adapter-visible source。
- visibility risk。
- environment lock strategy。
- baseline verifier evidence。
- post-patch verifier evidence。
- flaky probe evidence。
- source archive manifest。
- license provenance review。
- use boundary review。

## V4 task freeze 做了什么

`build_v4_task_freeze` 从两个来源读取输入：

- `v4_pr_issue_feasibility`
- `v4_public_swebench_like_feasibility`

对 PR / issue 任务，它读取类似这些文件：

```text
manifests/pr_issue_task_freeze_readiness_report.json
manifests/adapter_visible_task_freeze_manifest.json
manifests/docker_feasibility_summary_report.json
manifests/flaky_probe_report.json
manifests/training_export_boundary_report.json
manifests/adapter_visible_denylist_scan_report.json
manifests/source_archive_manifest.json
```

随后写出：

```text
docs/v4/evidence/task-source-freeze/task_freeze_manifest.json
docs/v4/evidence/task-source-freeze/adapter_visible_task_input_manifest.json
docs/v4/evidence/task-source-freeze/evaluator_only_evidence_manifest.json
docs/v4/evidence/task-source-freeze/pr_task_construction_manifest.json
docs/v4/evidence/task-source-freeze/source_materialization_report.json
docs/v4/evidence/task-source-freeze/baseline_verifier_report.json
docs/v4/evidence/task-source-freeze/post_patch_verifier_report.json
docs/v4/evidence/task-source-freeze/flaky_detection_report.json
docs/v4/evidence/task-source-freeze/environment_stability_report.json
docs/v4/evidence/task-source-freeze/dependency_cache_report.json
docs/v4/evidence/task-source-freeze/license_provenance_review_report.json
docs/v4/evidence/task-source-freeze/use_boundary_review_report.json
docs/v4/evidence/task-source-freeze/task_validity_report.json
```

这一步的本质是把“网上有一个 PR 修复了一个 issue”变成“我有一个固定源码、固定任务文本、固定验证器证据、固定可见性边界的训练任务”。

## 面试里容易被问的点

如果被问“你怎么避免模型看到答案”，应答重点是：

- PR body、fix patch、gold patch、hidden verifier selectors 都不进入 adapter-visible task。
- `VisibilityPolicy` 标记字段可见性。
- `ContextBuilder` 使用 `RunnableTask.agent_visible_view()`，不直接把完整 `TaskDefinition` 塞给模型。
- V4 task freeze 生成 adapter-visible manifest 和 evaluator-only evidence manifest。
- export quality audit 和 contamination scan 会检查泄漏风险。

如果被问“SWE-Bench-like 和官方 SWE-Bench harness 的区别”，应答重点是：

- RepoHarness 当前不是官方 leaderboard harness。
- 它使用固定 source archive 和 evaluator-only verifier material 构造可审计任务。
- 目标是训练轨迹和内部评测，不是声明与官方榜单完全可比。
- final verifier 使用 fail-to-pass / pass-to-pass 语义，但 evidence、task freeze 和 export audit 是 RepoHarness 自己的基础设施。
