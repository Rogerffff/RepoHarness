# RepoHarness 环境生产与质量流水线设计

本文承接 `repo_harness_repositioning_after_polar.md` 中的 `EnvironmentPackageSpec`、`EnvironmentValidationReport`、`task_quality_report_ref`、`AntiCheatSpec` 和 `SWEEnvPackageProfile`。它讨论的是训练前的数据处理与环境包生产流程，不是 rollout 运行期协议。

## 1. 文档定位

高层架构文档只应该定义运行期必须依赖的契约：

```text
冻结的环境包
  + 可复现 digest
  + EnvironmentValidationReport
  + task_quality_report_ref
  + anti_cheat_spec_ref
  + 可选领域 profile
```

至于任务如何从 PR、issue、fixture 或 synthetic task 进入候选池，如何过滤、改写、构建镜像、验证确定性，这些都属于环境生产流水线。它们会随着数据源、模型能力和成本预算快速演化，不应该写死在高层架构中。

## 2. 总体流水线

建议把环境生产理解成下面的离线流水线：

```text
Source Intake
  -> Repository Snapshot
  -> Diff / Test Split
  -> Task Draft
  -> Dependency And Image Build
  -> Anti-cheat Preparation
  -> Validation Runs
  -> Task Quality Evaluation
  -> EnvironmentPackage Freeze
```

每一步都应该产出可追溯报告，而不是只在日志里留下自然语言说明。最终进入训练采样池的不是原始任务，而是冻结后的 `EnvironmentPackageSpec` 和对应 validation / quality / anti-cheat 报告引用。

## 3. EnvironmentBuilder / TaskIngestionPipeline

`EnvironmentBuilder` 或 `TaskIngestionPipeline` 是生产流程名称，不是运行期核心组件。它的职责包括：

```text
1. 接收 PR、issue、人工 fixture、合成任务或已有 benchmark item。
2. 固定 repo snapshot、base commit、依赖锁文件和公开输入。
3. 拆分 code diff、test diff、隐藏评分资源和公开 scaffold。
4. 生成任务 prompt、公开约束和隐藏约束。
5. 构建或选择 sandbox image、scoring image 和 dependency cache。
6. 执行 anti-cheat 准备，例如 git 历史净化、future refs 删除、remote refs 删除。
7. 运行 empty patch、golden patch、重复执行确定性检查和训练 runtime 复验。
8. 调用 TaskQualityEvaluator 生成任务质量报告。
9. 冻结 EnvironmentPackageSpec、TaskPackSpec、EnvConfig 和相关 digest。
```

这个流水线可以借鉴 MAI-Thinking-1 报告中从大规模 PR 池逐步筛到可训练 SWE 环境的思路，但 RepoHarness 第一版不需要追求相同规模。关键是保留相同的质量门槛：环境必须可复现、可评分、可防泄漏、可解释为什么进入或不进入训练池。

## 4. TaskQualityEvaluator

`TaskQualityEvaluator` 属于离线数据处理，不属于 rollout runtime。它的输出通过 `EnvironmentValidationReport.task_quality_report_ref` 挂到环境包上。

建议第一版质量报告包含：

```text
task_quality_report:
  specification_clarity: pass | warn | fail
  test_alignment: pass | warn | fail
  leakage_risk: pass | warn | fail
  feasibility: pass | warn | fail
  underspecification_flags: list[str]
  overspecification_flags: list[str]
  hidden_test_fairness_notes: list[str]
  rewrite_suggestion_ref: str | None
  evaluator_version: str
  evidence_refs: list[str]
```

质量报告不应该直接替代 rubric，也不应该在 rollout 期间影响模型可见上下文。它只决定环境包是否进入训练采样池、是否需要人工复核、是否只能作为离线分析样本。

## 5. 验证门槛

典型 SWE patch 型任务进入训练采样池前，至少要满足：

```text
empty_patch_must_fail = passed
golden_patch_must_pass = passed
determinism_check = passed
verified_in_training_runtime = true
task_quality_report_ref != None
anti_cheat_spec_ref != None
```

非 patch 型任务可以声明 `patch_validation_applicability="not_applicable"`，但必须写明原因，并提供等价的任务质量验证。例如只做代码解释的任务，可能不需要 empty patch / golden patch，但仍需要检查 prompt 是否清晰、答案是否可验证、评分是否不会泄漏隐藏信息。

## 6. Anti-cheat 准备

环境生产阶段应生成 anti-cheat 报告，至少覆盖：

```text
git_sanitizer_report:
  future_refs_removed: bool
  reflog_removed: bool
  remote_refs_removed: bool
  unreachable_future_objects_checked: bool
  sanitizer_version: str

command_filter_policy:
  block_remote_git: bool
  block_github_http: bool
  allowlisted_domains: list[str]
  denied_command_patterns: list[str]
  audit_policy_ref: str
```

这些报告的细节可以演进，但最终必须回写到 `AntiCheatSpec` 和环境包 digest 中。不能只在环境构建脚本中隐式完成。

## 7. 输出物

环境生产流水线最终应该输出：

```text
EnvironmentPackageSpec
TaskPackSpec
EnvConfig
EnvironmentValidationReport
TaskQualityReport
AntiCheatSpec
SWEEnvPackageProfile | None
benchmark_card_ref
source_digest_manifest
```

其中只有冻结后的规格和报告引用进入运行期；原始 PR、改写中间稿、LLM 质量评估长文本、构建日志和调试数据应留在 runtime-private 或 data-private artifact 中。

## 8. 不进入高层架构的内容

以下内容不应该写入重定位主文档，只在本子文档或后续数据处理计划中演进：

```text
PR 选择启发式
issue / PR 匹配规则
LLM rewrite prompt
质量评估 rubric 细则
dependency build retry 策略
人工复核队列规则
具体通过率阈值
环境生产成本统计
```

这样可以保持高层设计文档稳定，同时让环境生产流程按照真实数据质量不断迭代。
