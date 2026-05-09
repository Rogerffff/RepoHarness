# RepoHarness 项目学习资料

这个目录用于帮助你系统学习 RepoHarness 的项目定位、运行链路、源码实现、证据产物、版本演进和面试表达。

新的主入口是：

```text
docs/project_tut_for_me/00-learning-plan.md
```

它会按照完整项目链路来安排学习顺序，而不是只围绕 V4 或某一次 `run-task` 实录展开。

RepoHarness 的核心闭环是：

```text
task -> executable workspace -> tools -> agent loop -> trajectory -> verifier -> reward/eval/export
```

学习时最重要的是理解每个箭头在代码里由哪些模块实现、写出哪些运行产物、哪些内容模型可见、哪些内容只属于 evaluator-only evidence 或 audit-only evidence。

## 推荐阅读顺序

1. `00-learning-plan.md`
   - 这是当前最重要的学习路线。
   - 先从项目定位、系统架构、对象流和 `run_task()` 主链路讲起，再逐步进入任务、Docker、工具、provider、verifier、export、V4 evidence 和 V5 result pack。

2. `session-notes/01-run-task-architecture.md`
   - 这是你已经读过的一次真实 `run-task` 纵向追踪。
   - 它适合作为实战记录，不再作为完整项目学习的唯一主线。

3. `session-notes/06-task-schema-adapter-input-boundary-summary.md`
   - 这是当前源码讲解第一轮的回顾笔记。
   - 它整理了任务 schema、`TaskAdapter.load()`、`agent_visible_view()`、SWE-Bench-like 输入、GitHub PR / issue-like 输入和 Docker 工作区关系。

4. `00-v4-deep-dive-plan.md`
   - 这是 V4 深挖计划。
   - 它适合在你完成全局学习路线之后，用来专门复盘 V4 已完成能力。

5. `01-v4-runtime-architecture.md` 到 `05-final-verifier-reward-export-acceptance.md`
   - 这是 V4 主讲义。
   - 主题分别是运行架构、任务构造、Docker 命令执行、provider / agent loop / tools、final verifier / reward / export / acceptance。

6. `代码阅读QA.md`
   - 这是局部概念问答。
   - 适合在阅读源码时查具体概念，不适合作为主线连续阅读。

7. `99-next-questions.md`
   - 这是后续追问清单。
   - 问题偏实现审查和面试深挖。

## 当前学习路线的代码依据

核心代码入口：

- `src/repo_harness/evaluation/runner.py`
- `src/repo_harness/workspace/docker_adapter.py`
- `src/repo_harness/workspace/materialization.py`
- `src/repo_harness/tasks/schemas.py`
- `src/repo_harness/tasks/adapter.py`
- `src/repo_harness/tasks/command_policy.py`
- `src/repo_harness/model_client/factory.py`
- `src/repo_harness/model_client/providers/common.py`
- `src/repo_harness/model_client/providers/deepseek.py`
- `src/repo_harness/model_client/providers/openai.py`
- `src/repo_harness/agent_loop/loop.py`
- `src/repo_harness/context/builder.py`
- `src/repo_harness/tools/minimal.py`
- `src/repo_harness/permissions/system.py`
- `src/repo_harness/verifier/runner.py`
- `src/repo_harness/v3_swebench_like.py`
- `src/repo_harness/v3_agent_runtime.py`
- `src/repo_harness/v4_implementation_inputs.py`
- `src/repo_harness/v4_task_freeze.py`
- `src/repo_harness/v4_rollout.py`
- `src/repo_harness/v4_agent_run.py`
- `src/repo_harness/v4_export_quality.py`
- `src/repo_harness/v4_cards.py`
- `src/repo_harness/v4_acceptance.py`
- `src/repo_harness/v5_evidence.py`
- `src/repo_harness/v5_task_set.py`
- `src/repo_harness/v5_provider_gate.py`
- `src/repo_harness/v5_run_matrix.py`
- `src/repo_harness/v5_export_pack.py`

关键产物入口：

- `docs/v4/evidence/task-source-freeze/`
- `docs/v4/evidence/tool-lifecycle/`
- `docs/v4/evidence/agent-run-integration/`
- `docs/v4/evidence/export-quality/`
- `docs/v4/evidence/regression/`
- `runs/v3-core-realrepo-deepseek-20260504T000000Z/`
- `runs/v3-final-swebench-agent-loop-20260503T035615Z/`
- `runs/v3-final-rerun-20260504T010000Z/`
- `runs/v4-final-rerun-20260504T194758Z/`

## 一个需要牢记的状态说明

截至 2026-05-05，V4 implementation 已经完成，之前复核发现的检查器和 evidence 绑定缺口已经修复，并重新生成了修复后的 acceptance evidence。最新 V4 closure commit 是 `e0da89c test: refresh V4 acceptance evidence after hardening`，最新验收目录是 `runs/v4-final-rerun-20260504T194758Z/`，完整测试结果是 `712 passed`。

**V4 实现链路已经通过修复后最终验收；后续学习和引用 V4 状态时，应优先使用 `runs/v4-final-rerun-20260504T194758Z/` 下的 acceptance inputs、acceptance report、文档同步后的 acceptance bundle 和 final acceptance command log。**

V5 当前正在实施。学习 V5 时应该把它描述为“正在基于 V4 构建面试级结果包”，不能提前说成已经通过最终验收。V5 是否允许使用多 provider、preference export completed、完整 interview-grade evaluation pack 等强表述，要以 V5 的 claim gate 和最终 acceptance 结果为准。
