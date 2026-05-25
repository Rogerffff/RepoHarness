# Stage 16F 统一基线交接说明：给测评工作树 Agent

创建时间：2026-05-25

状态：供 `evaluation_worktree` agent 审查和执行 Stage 16.5 之前对齐使用。

## 1. 一句话结论

当前 `training_worktree` 已经完成 Stage 16F.6，可以作为两个工作树后续协作的共同 Harness 基线。

建议从现在开始采用下面的协作方式：

```text
以 training_worktree 当前 Stage 16F.6 后的提交作为 canonical Harness baseline
-> evaluation_worktree 对齐到这个 baseline
-> evaluation_worktree 继续负责强模型真实任务测评和 Harness 能力缺口诊断
-> training_worktree 继续负责训练链路、数据准备、reward、verl 和正式训练基础设施
-> 所有确认过的 Harness 修复都回流到共同 baseline，而不是长期停留在某一个工作树里
```

当前共同基线建议使用：

```text
canonical_baseline_commit = ab394780 feat: add stage16f6 real model smoke
```

这个提交应理解为 Stage 16F.6 的临时共同基线：它证明统一入口可以跑真实模型，但是还不足以支撑 Stage 16.5 的 20 到 30 题分数差距归因。正式开始 Stage 16.5 之前，`training_worktree` 需要先补一个很小的 Stage 16F.7 / Stage 16.5-prebaseline 加固版本，至少让 `run-episode-task` 能显式选择 `full_audit` 诊断模式，并写出 provider failure accounting、official prediction eligibility 和 per-case artifact inventory。完成后应把新的提交记录为：

```text
stage16_5_diagnostic_baseline_commit = <Stage 16F.7 后的新提交>
```

如果另一个工作树已经在这个提交之后有新的本地修复，请不要直接覆盖当前基线。应先生成差异清单，说明每项修复是否仍然适用于 Stage 16F 之后的统一入口。

这里的“对齐到共同基线”不是要求直接丢弃 `evaluation_worktree` 里已经完成的测评修复。正确做法是先把 `training_worktree` 的 `ab394780` 作为新的 Harness 语义基准，然后逐项判断 `evaluation_worktree` 中已有修复是否还需要回流。例如测评工作树里已经确认有效的 provider 失败记账、patch sidecar 过滤、official prediction hygiene、score gap variant contract、真实任务诊断脚本等，不应该被无差别覆盖；它们应该进入 Stage 16.5 的对齐清单，标注为“已经被 Stage 16F 覆盖”“仍需移植到共同基线”或“只保留在测评工作树作为实验工具”。

## 2. 当前背景

在 Stage 16F 之前，两个工作树的职责和代码入口已经开始分叉：

```text
training_worktree:
  主要推进 run_episode(real_episode)、verl fully async、训练样本 gate、reward、formal online RL、训练数据准备。

evaluation_worktree:
  主要推进 SWE-Bench Verified 分数差距排查、强模型测评、工具能力诊断、official harness 和真实任务表现分析。
```

这个分工本身是合理的，但旧状态有一个关键问题：

```text
测评主要走旧 run_task(...)
训练主要走 run_episode(real_episode)
```

这会导致测评和训练看到的 Harness 不完全相同。例如首轮 prompt、工具集合、公开环境提示、测试反馈策略、verifier plan、patch hygiene 和训练资格事实都可能不一致。这样会让后续训练实验难以归因：

```text
如果模型在测评中失败，不清楚是模型能力问题，还是旧测评入口和训练入口不一致。
如果模型在训练中学不到某种行为，不清楚是数据问题，还是测评 worktree 中的 Harness 修复没有同步。
```

因此 Stage 16F 的核心目标是：把测评和训练重新收敛到同一个 canonical Harness 执行入口。

## 3. Stage 16F 已经完成的关键状态

### 3.1 统一入口的最终方向

Stage 16F 后的新方向是：

```text
repo-harness run-episode-task
-> EpisodeExecutionSpec
-> RepoHarnessRuntime.run_episode(real_episode)
-> RepoHarnessEpisodeResult
-> compat_projection / TrainingView / verifier / reward / export
```

也就是说：

```text
测评入口和训练入口共享同一次 episode 执行过程。
测评和训练只是在 episode 结束后的消费方式不同。
```

测评消费：

```text
RepoHarnessEpisodeResult
-> compat_projection
-> final.patch
-> final verifier summary
-> reward / metrics
-> official prediction
-> evaluation report
```

训练消费：

```text
RepoHarnessEpisodeResult
-> TrainingView
-> GenerationRecord
-> AgentLoopOutput
-> SFT / preference / reward / formal online RL gate
```

### 3.2 Stage 16F 各子阶段已经完成的事情

当前 `training_worktree` 已经完成下面这些提交：

```text
c2da6fea docs: add stage16f sync inventory plan
997d434d feat: sync stage16f diagnostic shell semantics
c6b6faca feat: add stage16f2 episode execution spec
fce58d83 feat: add stage16f3 run episode task entry
11118db4 feat: add stage16f4 run episode parity audit
d167d203 feat: add stage16f5 entrypoint policy
ab394780 feat: add stage16f6 real model smoke
```

这些阶段的实际含义如下：

```text
Stage 16F.0:
  完成跨工作树同步前 inventory，不做代码同步。

Stage 16F.1:
  同步关键 Harness 语义，尤其是 diagnostic shell 的 bash -lc 语义、run directory 隔离和 patch hygiene 相关边界。

Stage 16F.2:
  新增 EpisodeExecutionSpec，把任务、首轮上下文、工具集合、预算、权限、反馈策略和 verifier plan 固定成共享规格。

Stage 16F.3:
  新增 run-episode-task，让 CLI 可以直接通过 run_episode(real_episode) 跑任务，并生成兼容旧评测读取的 projection。

Stage 16F.4:
  做小规模 run_task(...) 与 run-episode-task parity audit，验证关键公开投影语义对齐。

Stage 16F.5:
  把旧 run_task(...) 降级为 legacy 兼容入口，明确新测评和训练数据准备默认使用 run-episode-task。

Stage 16F.6:
  使用真实 DeepSeek provider 跑 run-episode-task 小规模 smoke，证明新 canonical 入口可以承载真实外部 API 模型测评。
```

### 3.3 Stage 16F.6 的真实模型 smoke 结论

Stage 16F.6 已经使用真实 DeepSeek provider 跑过 3 个 `run-episode-task` case。

关键结论：

```text
real_model_case_count = 3
completed_real_model_episode_count = 3
projection_complete_count = 3
legacy_run_task_invocation_count = 0
policy_loss_candidate_count = 0
external_provider_case_count = 3
public_feedback_observed_case_count = 1
```

这里最重要的语义是：

```text
DeepSeek / OpenAI 这类外部 API provider 的轨迹可以用于测评、诊断、SFT 或偏好数据候选。
但它们默认不能进入 formal online RL / policy loss。
```

原因是外部 API provider 通常缺少当前 `verl` 训练路径需要的可靠 token id、response span、generation record 和 log probability provenance。当前 Stage 16F.6 验收器要求这些样本明确记录：

```text
formal_online_rl_eligible = false
policy_loss_candidate = false
reason_not_policy_loss_candidate = external_provider_missing_verl_token_provenance
```

请不要把 Stage 16F.6 的真实 DeepSeek 轨迹解释成“已经可以直接进入强化学习 policy loss”。它证明的是：真实强模型可以走统一 Harness 入口，且不会被误标成正式在线强化学习样本。

另外，即使外部 API provider 轨迹未来作为 SFT 或 preference data 的候选，也不能直接进入导出。它还必须经过 provider 使用条款检查、脱敏检查、patch hygiene、verifier / reward 审计、public / private evidence 分层检查和 offline data gate。Stage 16F.6 只证明统一入口和测评 smoke 可用，不等于这些轨迹已经是合格离线训练数据。

## 4. 当前两个工作树应该如何分工

### 4.1 training_worktree 的职责

`training_worktree` 后续主要负责：

```text
1. 维护 canonical run_episode(real_episode) 入口。
2. 维护 EpisodeExecutionSpec、TrainingView、GenerationRecord、AgentLoopOutput、formal gate。
3. 维护 verl fully async、DataProto、policy loss、reward、SFT / preference / online RL 导出链路。
4. 维护 patch hygiene、reward boundary、visibility、token provenance、public/private evidence 分层。
5. 在 Stage 17 之后准备 R2E-Gym、SWE-Gym 和内部微型任务池的数据 registry。
```

`training_worktree` 不应该单独承担所有真实任务测评和工具能力探索，否则会和 `evaluation_worktree` 的职责重叠。

### 4.2 evaluation_worktree 的职责

`evaluation_worktree` 后续主要负责：

```text
1. 基于当前 canonical baseline 做 Stage 16.5 代表性 Harness 诊断。
2. 使用强模型，例如 DeepSeek V4，跑 20 到 30 个代表性任务。
3. 记录真实任务中模型需要但当前 Harness 不支持的工具能力。
4. 记录 public feedback、diagnostic shell、run_tests、project test command、patch hygiene、verifier 和 official harness 的实际问题。
5. 输出可复现的最小失败样例和建议修复清单。
```

从 Stage 16F.6 以后，`evaluation_worktree` 的新测评默认应该使用：

```text
repo-harness run-episode-task
```

旧 `run_task(...)` 只应保留下面用途：

```text
1. 读取历史 evidence。
2. 做 legacy compatibility regression。
3. 对照旧入口行为，帮助定位迁移差异。
```

它不应该继续作为新测评、新训练数据准备或 Stage 17 数据事实的主入口。

### 4.3 evaluation_worktree 开始 Stage 16.5 前的对齐前置检查

在 `evaluation_worktree` 开始新的 20 到 30 题强模型诊断之前，建议先生成一个很小的对齐报告，避免两个工作树刚刚统一入口又重新分叉。报告可以命名为：

```text
stage16_5_baseline_alignment_report.json
```

这个报告至少记录：

```text
canonical_baseline_commit = ab394780
evaluation_worktree_head_before_alignment
training_worktree_head = ab394780
evaluation_only_commits_after_last_sync
commits_or_changes_ported_from_training_worktree
evaluation_fixes_retained_as_experimental_only
evaluation_fixes_recommended_for_canonical_backflow
entrypoint_for_new_cases = run_episode_task
legacy_run_task_allowed_only_for_regression = true
```

其中 `evaluation_only_commits_after_last_sync` 很重要。当前测评工作树此前已经围绕 SWE-Bench Verified 分数差距做过多项修复和诊断，例如 provider 响应异常重试、patch sidecar artifact 过滤、provider-only rerun、score gap variant contract 等。这些内容不能在对齐时静默消失；如果其中某项仍然适用于 `run-episode-task`，就应该变成共同基线候选修复。如果某项只适用于旧 `run_task(...)` 或一次性诊断脚本，就应该明确留在测评工作树，不作为训练链路依赖。

## 5. 建议的 Stage 16.5 执行方式

这里的 `Stage 16.5` 指的是 Stage 16F 统一入口完成之后的“20 到 30 题代表性 Harness 诊断扩展阶段”。它不是 `Stage 16F.5 entrypoint policy`。`Stage 16F.5` 已经完成，作用是把旧 `run_task(...)` 降级为 legacy 兼容入口；这里讨论的 `Stage 16.5` 是下一步用强模型诊断统一入口下的 Harness 能力缺口。

### 5.1 Stage 16.5 的目标

Stage 16.5 不应该重新设计训练链路，也不应该直接准备正式训练数据。它的目标是：

```text
用统一后的 run-episode-task，在 20 到 30 个代表性任务上诊断当前 Harness 是否足够稳定和真实。
```

Stage 16.5 诊断不建议直接使用 `ab394780` 作为最终基线。`ab394780` 适合作为“统一入口已经跑通”的临时基线；正式诊断应使用 Stage 16F.7 / Stage 16.5-prebaseline 之后的新提交。这个新提交需要保持训练默认路径仍然是 `training_fast`，同时允许测评显式传入：

```bash
repo-harness run-episode-task <task> --config <config> --run-mode full_audit
```

`full_audit` 只用于诊断运行，不表示该样本可以进入正式在线强化学习训练。外部 provider 轨迹仍然必须保持 `policy_loss_candidate=false`。

Stage 16F.7 之后，`run-episode-task` 可以在所有运行模式下写出三份 Stage 16.5 预基线摘要报告：

```text
stage16_5_provider_failure_accounting.json
stage16_5_official_prediction_eligibility.json
stage16_5_case_artifact_inventory.json
```

这些报告只是哈希、相对路径、大小、redaction / retention 状态和不透明引用索引。默认 `training_fast` 可以生成这些摘要报告，但不会保存完整 provider 原始请求和原始响应。只有显式 `--run-mode full_audit` 时，底层 recorder 才会尽量保留 runtime-private provider 诊断证据；公开报告仍然只能引用哈希和不透明引用，不能公开 provider 原文、私有 reasoning、真实本机路径或密钥。

`stage16_5_provider_failure_accounting.json` 需要同时记录两类事实：

```text
1. 最终 model call 是否失败，例如 provider timeout、invalid response、retry exhausted。
2. 中间 provider_attempt 是否发生过可重试失败，即使最终调用成功也要能看出曾经重试。
```

因此报告里应包含 `provider_attempt_count`、`retryable_attempt_count`、`terminal_attempt_count`、`provider_attempt_error_types`、`retry_count_from_model_call_event`，以及 `training_fast` 下的 `provider_request_projection_fact_count`、`provider_response_projection_fact_count` 和 `raw_payload_persisted`。这样后续 Stage 16.5 诊断可以区分“模型语义失败”“provider 最终失败”“provider 中间失败但重试成功”三类情况。

需要重点回答：

```text
1. 模型是否能看懂当前 public environment prompt。
2. 当前工具集合是否足够完成真实 SWE 修复任务。
3. execute_bash 的安全最小工具面是否过于限制。
4. diagnostic_shell 是否在需要时提供了足够真实的持久诊断能力。
5. run_tests / public feedback 是否能给模型提供有用、非 oracle 的反馈。
6. final.patch 是否干净，是否会残留诊断脚本、缓存、依赖目录或测试文件改动。
7. final verifier / official harness 失败时，是否能区分模型语义失败、Harness 基础设施失败和 provider 失败。
8. 强模型没有解决任务时，是因为模型能力不足，还是 Harness 工具和上下文还不够真实。
```

### 5.2 Stage 16.5 推荐任务池

Stage 16.5 可以优先使用小规模、可审计的任务池，而不是直接进入大规模 SWE-Bench。

建议覆盖：

```text
1. 内部微型任务：
   用来验证 edit_file、read_file、run_tests、public feedback、patch hygiene 和 verifier 基本闭环。

2. SWE-Bench-like 小任务：
   用来验证真实仓库布局、测试命令、patch capture、official prediction hygiene。

3. 带依赖或测试环境敏感任务：
   用来验证 diagnostic_shell、dependency policy、Docker backend 或 future allowed project command routing。

4. verifier rejected 的可信负样本：
   用来验证 final verifier rejected 是否被正确归类为可训练负样本候选，而不是基础设施失败。

5. 工具能力压力样本：
   用来观察模型是否需要更多 shell 能力、项目测试入口、文件搜索入口或结构化诊断工具。
```

### 5.3 Stage 16.5 应该输出的报告

`evaluation_worktree` 建议至少输出下面这些报告，供 `training_worktree` 消费：

```text
stage16_5_case_manifest.json
stage16_5_run_episode_task_report.json
stage16_5_tool_gap_report.json
stage16_5_public_feedback_report.json
stage16_5_patch_hygiene_report.json
stage16_5_verifier_failure_classification_report.json
stage16_5_provider_failure_accounting_report.json
stage16_5_recommended_harness_fixes.json
stage16_5_acceptance_summary.json
```

这些报告不能只写人工摘要。为了便于 `training_worktree` 后续自动复核，建议每个 Stage 16.5 公开报告至少包含下面这些机器可校验字段：

```text
baseline_commit
evaluation_worktree_commit
case_count
run_episode_task_invocation_count
legacy_run_task_invocation_count
per_case.entrypoint
per_case.provider_route
per_case.formal_online_rl_eligible
per_case.policy_loss_candidate
per_case.projection_complete
per_case.assert_projection_complete_passed
per_case.compat_projection_digest
per_case.final_patch_sha256
per_case.final_patch_hygiene_status
per_case.public_feedback_observed
per_case.verifier_status
per_case.reward_score
public_evidence_manifest_sha256
runtime_private_manifest_sha256_or_opaque_ref
blocking_reason_count
```

最低要求是：

```text
run_episode_task_invocation_count >= completed_case_count
legacy_run_task_invocation_count = 0
每个新测评 case 的 entrypoint = run_episode_task
每个 case 都必须有 projection binding 结果
如果使用外部 API provider，则 policy_loss_candidate 必须为 false
```

其中 `stage16_5_recommended_harness_fixes.json` 最重要。每个建议修复项应该至少包含：

```text
issue_id
priority = P1 | P2 | P3
observed_case_ids
minimal_reproduction_command
expected_behavior
actual_behavior
affected_module
suggested_fix
whether_blocks_stage17
whether_requires_training_worktree_change
whether_can_remain_evaluation_only
```

## 6. 修复如何在两个工作树之间流动

### 6.1 不建议长期私有修复

如果 `evaluation_worktree` 发现了 Harness 问题，不建议只在测评工作树本地修复然后继续测评。这样会重新制造分叉。

更推荐的流程是：

```text
evaluation_worktree 发现问题
-> 写最小复现和诊断报告
-> 如果修复很小，可以在 evaluation_worktree 做 proof-of-fix
-> 把修复建议和测试带回 canonical baseline
-> training_worktree 或 canonical branch 合入修复
-> 两个工作树重新同步到新的 baseline
```

### 6.2 哪些修复应该回流到共同 baseline

下面这些类型的修复应该回流到共同 baseline：

```text
1. 工具协议或工具权限修复。
2. public environment prompt 修复。
3. diagnostic_shell / Docker backend / workspace projection 修复。
4. final.patch capture 和 patch hygiene 修复。
5. verifier plan、public feedback、official prediction hygiene 修复。
6. provider failure accounting 修复。
7. run-episode-task projection 或 inspector 修复。
8. TrainingView、GenerationRecord、reward boundary、formal gate 相关修复。
```

下面这些内容可以留在 `evaluation_worktree`：

```text
1. 大量原始测评日志。
2. 临时分析 notebook。
3. 未脱敏的 provider 请求和响应。
4. 本地路径、API key、云实例配置。
5. 只用于一次性排查的脚本。
```

如果某个脚本后来成为重复执行的验收工具，就应该重写成可提交、可脱敏、可测试的正式工具。

### 6.3 同步节奏建议

建议采用短周期同步：

```text
每完成 5 到 10 个真实任务诊断
或者发现任意 P1 Harness 问题
或者准备进入 Stage 17 数据冻结前
```

就做一次同步检查。

每次同步至少记录：

```text
baseline_commit_before
evaluation_worktree_head
training_worktree_head
changed_modules
recommended_fixes
accepted_fixes
deferred_fixes
new_baseline_commit_after
```

## 7. 对 evaluation_worktree agent 的具体要求

### 7.1 新测评默认使用 run-episode-task

请优先使用：

```text
repo-harness run-episode-task <task> --config <config>
```

不要继续把旧 `repo-harness run-task` 当作主测评入口。

如果必须使用旧入口，请在报告中明确：

```text
legacy_run_task_used = true
reason
whether_result_can_generalize_to_run_episode
```

### 7.2 外部 provider 不能声明 policy loss 候选

如果使用 DeepSeek、OpenAI 或其他外部 API provider，请把它们当作测评轨迹或离线数据候选，而不是 formal online RL 样本。

必须保持：

```text
formal_online_rl_eligible = false
policy_loss_candidate = false
reason_not_policy_loss_candidate = external_provider_missing_verl_token_provenance
```

如果发现某个报告把外部 provider 样本标成 `policy_loss_candidate=true`，这是阻断问题。

### 7.3 不要绕过 Stage 16A 到 Stage 16F 已建立的安全边界

请不要为了提高强模型得分，直接放宽下面这些边界：

```text
1. Git history 禁止访问。
2. hidden verifier / gold patch / test patch 禁止泄漏。
3. raw run directory 和 runtime-private path 禁止模型可见。
4. shared dependency environment 禁止模型写入。
5. final.patch 禁止包含诊断残留、依赖目录、缓存目录、测试文件改动和敏感 marker。
6. 外部 provider 轨迹禁止进入 formal online RL policy loss。
```

如果某个真实任务确实需要更多 shell 能力，应该记录为工具缺口，而不是直接绕过策略。

### 7.4 优先产出“缺口分类”，不是只追求分数

Stage 16.5 的主要价值不是立刻提高 resolved rate，而是分类当前 Harness 为什么不够真实。

建议把每个失败 case 分类为：

```text
model_semantic_failure:
  模型推理或修改本身失败。

tool_surface_gap:
  当前工具能力不足，例如不能运行必要测试、不能进行合理文件检查、不能执行项目脚本。

public_context_gap:
  初始提示没有告诉模型必要环境信息、测试入口或依赖策略。

feedback_gap:
  模型没有得到公开测试反馈，或者反馈不可理解。

verifier_or_reward_gap:
  verifier、reward 或 final status 分类不准确。

patch_hygiene_gap:
  final.patch 捕获不干净，包含诊断残留或不该进入训练目标的文件。

provider_or_infrastructure_failure:
  API、超时、环境、Docker、依赖、网络或 workspace 基础设施问题。
```

这种分类比单一分数更有价值，因为它会直接决定 Stage 17 之前要修哪些 Harness 能力。

## 8. 给 training_worktree 的后续动作

`training_worktree` 在收到 Stage 16.5 诊断结果后，应按下面顺序处理：

```text
1. 先处理 P1 Harness 安全或事实一致性问题。
2. 再处理会阻塞 Stage 17 数据冻结的 P2 问题。
3. 对工具能力扩展做最小可控设计，不要一次性开放完整无约束 shell。
4. 更新 run-episode-task / EpisodeExecutionSpec / projection / TrainingView / export / reward 的对应测试。
5. 修复后重新生成共同 baseline commit。
6. 通知 evaluation_worktree 重新对齐。
```

如果 Stage 16.5 发现大量任务都需要更真实的项目测试入口，建议优先设计 harness-owned 结构化入口，例如：

```text
run_public_tests
run_project_test
allowed_project_command
safe_search
safe_read_file
diagnostic_shell with Docker backend
```

而不是直接把 `execute_bash` 扩展成无限制 shell。原因不是“不允许模型使用 shell”，而是正式训练需要可审计、可归因、可防泄漏的工具边界。

## 9. 当前不应该做的事情

请避免下面几类做法：

```text
1. 在 evaluation_worktree 继续大规模使用旧 run_task 产生新结论。
2. 把旧 run_task 的高分或低分直接外推到 run_episode 训练入口。
3. 把外部 API provider 轨迹标成 online RL policy loss 候选。
4. 为了临时通过任务而关闭 patch hygiene、hidden path guard 或 official prediction hygiene。
5. 把另一个工作树的未脱敏 runs、API key、HTML 报告或本机路径提交到共同 baseline。
6. 在没有最小复现和测试的情况下，把大块测评 worktree 修改直接合入 training worktree。
```

## 10. 推荐交接格式

如果 `evaluation_worktree` agent 要向 `training_worktree` 回传 Stage 16.5 结果，建议使用下面格式：

```text
baseline_commit:
evaluation_worktree_commit:
model_provider:
model_id:
case_count:
completed_case_count:
resolved_or_accepted_count:
model_semantic_failure_count:
tool_surface_gap_count:
public_context_gap_count:
feedback_gap_count:
verifier_or_reward_gap_count:
patch_hygiene_gap_count:
provider_or_infrastructure_failure_count:

blocking_p1_items:
  - issue_id:
    affected_cases:
    minimal_reproduction:
    expected_behavior:
    actual_behavior:
    proposed_fix:
    suggested_tests:

recommended_p2_items:
  - issue_id:
    affected_cases:
    reason:
    whether_blocks_stage17:

deferred_items:
  - issue_id:
    reason:
```

这样 `training_worktree` 可以直接把结果转成后续 Stage 16.5 follow-up 或 Stage 17 前置修复计划。

## 11. 总结

当前最重要的共识是：

```text
training_worktree 当前 Stage 16F.6 后的提交可以作为两个工作树的共同 Harness baseline。

后续新测评默认使用 run-episode-task。

evaluation_worktree 继续负责强模型真实任务诊断，但诊断结果必须回流到共同 baseline。

training_worktree 继续负责训练基础设施和数据准备，但不应该在没有真实测评反馈的情况下闭门完善 Harness。
```

这套协作方式可以避免两个工作树再次分叉，同时让强模型测评和强化学习训练共享同一套 Harness 事实。
