# Final Verifier、Reward、Export 和 V4 Acceptance

## final verifier 的核心原则

RepoHarness 当前正式评测使用：

```text
final_verifier_mode = strict_patch_replay
```

含义是：

```text
agent workspace 只用于模型探索和修改
-> 从 agent workspace 捕获 final patch
-> 在干净 verification workspace 重新应用 patch
-> 在 verification workspace 运行 formal final verifier
```

这避免了一个常见问题：agent workspace 中可能存在临时文件、缓存、测试副作用或未记录环境变化。如果直接在 agent workspace 评分，结果不够可审计。

## final patch 怎样捕获

Docker backend 和 local backend 都实现了：

```text
WorkspaceAdapter.capture_final_patch
```

在 Docker backend 中，agent workspace 会在创建时初始化 git baseline commit。agent 完成后，adapter 会对这个 baseline 执行：

```text
git diff <agent_start_snapshot>
git diff --numstat <agent_start_snapshot>
git diff --summary <agent_start_snapshot>
git diff --name-status <agent_start_snapshot>
```

输出包括：

- `final.patch`
- added lines。
- removed lines。
- changed files。
- added / modified / deleted files。
- renamed files。
- binary files。
- symlink files。
- untracked text files。

patch stats 会参与 reward 和 export quality audit。

## 普通 Pytest final verifier

普通任务的 final verifier 由：

```text
src/repo_harness/verifier/runner.py::PytestVerifier.run_final
```

执行。它会在 verification workspace 中运行 `ResolvedVerifierPlan` 中的 test command，并解析 pytest 输出。

`PytestVerifier` 有几个阶段方法：

- `run_baseline`
- `run_feedback`
- `run_feedback_public`
- `run_final`

这些方法最终都进入 `_run`，并通过 workspace adapter 执行命令。Docker mode 下就是容器执行。

## fail-to-pass 和 pass-to-pass

`VerifierResult` 不是只看 `pytest` 总体退出码。它会根据：

- fail-to-pass tests。
- pass-to-pass tests。
- parser confidence。
- timeout。
- error type。
- test cases。

计算 accepted。

acceptance policy 在：

```text
src/repo_harness/verifier/acceptance.py::apply_acceptance_policy
```

规则可以概括为：

- timeout 一定不 accepted。
- dependency error、test command error、patch apply failed 一定不 accepted。
- parser confidence 低于阈值不 accepted。
- 如果声明了 fail-to-pass / pass-to-pass，则必须全部满足。
- 如果没有声明测试集合，才 fallback 到整体 exit code 为 0。
- pass-to-pass 失败会标记 regression。

所以面试里不要说“pytest 退出码为 0 就算过”。更准确的说法是：`VerifierResult.accepted` 来自结构化 acceptance policy。

## SWE-Bench-like final verifier

SWE-Bench-like final-only 任务不走普通 `PytestVerifier.run_final`。它走：

```text
src/repo_harness/v3_agent_runtime.py::run_swebench_like_final_verifier
```

它使用冻结的 evaluator-only runtime plan：

```text
SweBenchLikeRuntimePlan
  manifest
  entry
  verifier_plan
  selector_cache
  environment_spec
```

执行过程：

```text
复制 manifest 中的 baseline verifier workspace 到 final verifier workspace
-> 应用 agent final patch
-> 使用冻结的 evaluator-only verifier plan 和 selector cache
-> 执行 fail-to-pass command
-> 执行 pass-to-pass command
-> 解析 pytest 输出
-> 写 swebench_like_agent_loop_final_verifier_report.json
-> 返回 VerifierResult
```

这条路径的核心价值是 hidden verifier material 不进入 agent loop。

## reward 怎样计算

reward 计算入口：

```text
src/repo_harness/reward/calculator.py::compute_reward_metadata
```

它的输入包括：

- final verifier result。
- patch stats。
- event counts。

reward 不只是一个 float，还会包含 metadata，例如：

- final verifier accepted。
- failure type。
- patch changed files。
- tool / permission / verifier 相关事件计数。
- reward schema version。

这使得 export audit 可以检查 reward 是否只来自允许字段，而不是从 hidden 或污染字段中偷看答案。

## run metadata 和 metrics

final verifier 后，`run_task` 会继续写：

- `metrics.json`
- `run_metadata.json`
- `events.jsonl`
- `transcript.jsonl`
- `artifacts.json`

`run_metadata` 会绑定：

- run config facts。
- environment fingerprint。
- execution mode facts。
- tool schema snapshot。
- provider options。
- final verifier。
- reward metadata。
- outcome policy。

这一步让后续 export 和 acceptance 可以回答：

```text
这条训练轨迹是在什么配置、什么工具、什么 provider、什么 Docker 环境、什么源码快照下产生的？
```

## trajectory export

训练导出相关模块包括：

```text
src/repo_harness/training_export.py
src/repo_harness/export/exporter.py
src/repo_harness/export/audit.py
src/repo_harness/export/pairing.py
```

导出的核心不是简单把 transcript 转成 JSONL，而是保留：

- message / tool call / tool result 顺序。
- model-visible 和 trainable 标记。
- artifact refs。
- verifier refs。
- reward metadata。
- run metadata binding。
- hidden / evaluator-only 内容的排除策略。
- export policy version。

V4 export quality 进一步检查：

- sample tier。
- failure dataset。
- packing manifest。
- patch quality。
- reward audit。
- test overfitting risk。
- reward hacking risk。
- preference pair trainability。

## preference pair 为什么要审

preference pair 不是随便找一个成功样本和一个失败样本配对。V4 复核中特别指出：只靠固定 sample id 可能绕过可训练性要求。

正确方向是检查它们是否具有可比较性，例如：

- 同一个任务。
- 同一个源码快照。
- 同一个 verifier plan。
- 同一类或可比较的策略设置。
- final verifier boundary 都有 evidence 支撑。

否则 pair 看似是 preferred / dispreferred，实际上可能比较的是不同环境或不同任务，训练信号会变脏。

## V4 acceptance 的结构

V4 acceptance 由：

```text
src/repo_harness/v4_acceptance.py
```

实现，主要步骤：

```text
build_v4_acceptance_inputs
-> build_v4_acceptance_report
-> build_v4_acceptance_bundle
-> inspect_v4_acceptance
-> inspect_acceptance_bundle
```

acceptance inputs 会绑定各阶段 evidence，例如：

- implementation inputs。
- task freeze。
- rollout orchestration。
- tool lifecycle。
- agent run integration。
- export quality。
- cards。
- real repository regression。
- SWE-Bench-like regression。

acceptance report 再检查这些 evidence 是否满足 V4 final acceptance 条件。

acceptance bundle 会把 acceptance report、关键 evidence 和命令日志打包成可审计 bundle。

## 当前 V4 evidence 状态

修复后最新产物包括：

```text
runs/v4-final-rerun-20260504T194758Z/v4_acceptance_inputs.json
runs/v4-final-rerun-20260504T194758Z/acceptance/v4_acceptance_report.json
runs/v4-final-rerun-20260504T194758Z/acceptance/acceptance_bundle_manifest_doc_sync_20260505T075410Z.json
```

`runs/v4-final-rerun-20260504T162105Z/` 是早期最终验收目录。后续复核发现过以下问题：

- 旧 acceptance inputs 缺少独立 `real_repository_regression` 和 `swebench_like_regression` evidence。
- 旧 acceptance report 曾把 regression role 绑定到 task freeze / task validity evidence，这现在不再允许。
- 部分 src、tests、evidence hash 与旧 pre-acceptance command log 不一致。
- 旧 bundle 缺少最新要求的 final acceptance command log ref。
- Stage 6、preference pair、reward allowlist、implementation log index 等也有过复核问题。

这些问题已经在后续修复中收口。当前学习和复述 V4 状态时，应以 `runs/v4-final-rerun-20260504T194758Z/` 下的修复后 evidence、`712 passed` 的完整测试结果，以及文档同步后的 acceptance bundle inspect 结果为准。

同时，仓库中已经有新的 regression evidence 文件：

```text
docs/v4/evidence/regression/real_repository_regression_report.json
docs/v4/evidence/regression/swebench_like_regression_report.json
```

这说明修复方向已经进入代码和 evidence 层，并已经通过重新生成的 V4 acceptance inputs、acceptance report 和文档同步后的 acceptance bundle 完成收口。

## 你需要能复述的完整闭环

可以把一次成熟运行讲成：

```text
任务在 V4 task freeze 阶段被固定为 adapter-visible task 和 evaluator-only evidence。
run-task 读取 task YAML 和 run config，创建 DockerWorkspaceAdapter。
adapter 从固定 archive 或固定本地镜像 materialize source，创建 setup workspace 并运行 setup。
baseline verifier 判断任务是否能进入 agent run。
ContextBuilder 只把模型可见任务投影、仓库上下文预览、工具列表、预算和执行模式交给 provider。
AgentLoop 每轮调用真实 provider，解析 tool call，经过 schema 校验、scaffold phase 检查、permission decision 和 workspace boundary 检查后执行工具。
工具中的文件读写和 bash 诊断命令都通过 WorkspaceAdapter；Docker mode 下每条命令都是 docker run，并写 container execution facts。
agent loop 结束后，从 agent workspace 捕获 final patch。
final verifier 在干净 verification workspace 中重放 final patch；SWE-Bench-like 任务会使用冻结的 evaluator-only verifier workspace、verifier patch reference 和 selector plan，而不是把隐藏验证材料暴露给模型。
VerifierResult 经过 acceptance policy 得出 accepted、failure type 和测试统计。
RewardMetadata、metrics、run metadata、transcript、events 和 artifacts 共同构成训练轨迹。
V4 export quality 和 acceptance 再检查这些轨迹能否安全导出、能否构成可训练 preference pair、能否被 evidence 完整支撑。
```

这段话基本覆盖了“跑一个真实 SWE / GitHub issue 任务”的完整实现链路。
