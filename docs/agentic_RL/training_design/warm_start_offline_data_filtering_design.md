# RepoHarness warm-start 与离线数据过滤设计

本文承接 `docs/harness_improve/repo_harness_repositioning_after_polar.md` 中的三档训练资格、`offline_or_sft_candidate`、`TrainingEligibilityReport.offline_filter_report_ref` 和 `TrainTrace.token_penalty_spans`。它讨论 warm-start / SFT / 离线分析数据如何从 rollout artifact 中筛选出来，不改变 formal online RL 的 hard gate。

## 1. 基本边界

RepoHarness 的在线强化学习样本必须先通过 token provenance、logprob、loss mask、reward attribution、artifact visibility、environment validation 和 policy staleness 等硬门槛。没有通过这些门槛的轨迹不能通过“把 loss mask 全部置 0”伪装成在线训练样本。

但是，不能进入 online policy loss 的轨迹仍可能有价值：

```text
1. 可作为 warm-start / SFT 候选。
2. 可作为失败恢复、工具设计和环境质量分析材料。
3. 可作为反作弊、权限拒绝和用户负担的负例。
4. 可作为 evaluator 或 rubric 调试样本。
```

因此需要一个独立的离线过滤层，接收 `offline_or_sft_candidate`，输出更细的使用建议。

## 2. 数据流

建议的离线过滤流程如下：

```text
TrajectoryArtifact
  -> TrainingEligibilityReport
  -> offline_or_sft_candidate
  -> TrajectoryHeuristicAnalyzer
  -> OfflineFilterReport
  -> WarmStartDatasetBuilder
```

`TrajectoryHeuristicAnalyzer` 是训练数据处理工具，不是运行期核心组件。高层架构只要求它的结果通过 `TrainingEligibilityReport.offline_filter_report_ref` 可追溯。

这里需要区分两个生命周期。在线 rollout 结束时生成的原始 `TrainingEligibilityReport` 只负责判断轨迹是否进入 online policy loss，`offline_filter_report_ref` 可以为空。离线数据处理作业随后读取 `offline_or_sft_candidate`，生成 `OfflineFilterReport`。这个后处理结果可以写入 `OfflineDatasetManifest`，也可以生成带有新版本号的补充 `TrainingEligibilityReport`，但不应该静默改写原始在线资格报告。高层文档中的 `offline_filter_report_ref` 表示“离线过滤已经运行之后的可空回链”，不是要求在线资格门在 rollout 当场完成所有 SFT 候选筛选。

## 3. OfflineFilterReport 草案

```python
class OfflineFilterReport:
    report_id: str
    source_artifact_id: str
    source_trace_ids: list[str]
    analyzer_version: str
    decision: Literal[
        "sft_candidate",
        "offline_analysis_candidate",
        "process_negative_candidate",
        "reject",
    ]
    reject_reasons: list[str]
    warning_reasons: list[str]
    heuristic_results: dict[str, str]
    token_penalty_span_refs: list[str]
    evidence_refs: list[str]
```

这个报告不直接改写 `TrainTrace.loss_mask`。如果某些 token 需要过程惩罚，应通过 `token_penalty_spans`、reward components 或后续 advantage 处理表达。

## 4. 第一版启发式目录

第一版可以从以下启发式开始：

```text
valid_submission_action:
  最终是否有明确提交动作或可重放 patch。

disallowed_git_ops:
  是否执行了被禁止的 remote git、checkout future commit、fetch、reset 到未知来源等操作。

edit_test_loop_pattern:
  是否反复编辑测试以迎合当前实现，而不是修复被测代码。

lost_in_exploration:
  是否长期读文件、grep 或运行命令但没有形成有效修改。

malformed_tool_call_rate:
  工具调用格式错误比例是否过高。

debug_artifact_in_patch:
  最终 patch 是否包含临时日志、调试文件、dump、print spam 或本地路径。

edited_but_never_tested:
  修改代码后是否完全没有运行相关测试或验证命令。

test_run_after_edit:
  修改后是否至少运行了与任务相关的 public test、targeted test 或 smoke check。

excessive_churn:
  是否产生大量无关文件修改、格式化整仓、删除无关代码或改动范围明显超出任务。

repeated_denied_action:
  权限被拒绝后是否重复尝试同类越权动作。

timeout_or_max_turns:
  是否因为超时或达到最大轮数终止。

test_tampering:
  是否修改、跳过、monkeypatch 或删除测试来获得通过。
```

这些启发式目录会随着真实数据观察不断变化，不应该冻结进高层架构。新增启发式必须记录 analyzer version，并保留输入 artifact 引用，方便复算。

## 5. SFT 候选规则

一个 rollout 进入 SFT 候选，至少应满足：

```text
1. 轨迹中的模型输出可还原为高质量行为片段。
2. 没有 test tampering、hidden verifier 泄漏、越权访问或明显反作弊违规。
3. 最终 patch 可以 clean replay，或者被明确标记为不依赖 patch 的任务类型。
4. 失败轨迹中的坏行为已被过滤或标为 process_negative_candidate。
5. token provenance 如果不满足 online RL，仍必须能解释文本来源和过滤原因。
```

SFT 候选不等于在线 RL 合格样本。缺少真实 response token ids、logprobs 或 policy version 的轨迹，可以用于人工分析、行为克隆候选或弱监督，但不能自动升级为 online policy loss。

## 6. Process Penalty 与 token_penalty_spans

Nemotron 类实践提醒我们，malformed tool call、非法 reasoning 格式、重复越权动作等坏行为不一定应该简单丢弃。它们可以作为过程负例，但必须有明确 attribution。

建议使用：

```text
token_penalty_spans:
  start
  end
  penalty_type
  penalty_weight
  evidence_ref
```

关键边界：

```text
1. token_penalty_spans 不改变 loss_mask。
2. 未完成轨迹默认不进入 online policy loss。
3. penalty 类型和权重属于 reward / RL 算法设计，不写死在高层架构。
4. 如果 evidence_ref 无法证明 token span 与坏行为相关，该 penalty 只能用于审计。
```

## 7. 指标与复核

warm-start 数据构建至少应该统计：

```text
candidate_count
sft_candidate_rate
offline_analysis_rate
process_negative_rate
reject_rate
top_reject_reasons
test_tampering_rate
disallowed_git_ops_rate
debug_artifact_rate
edited_but_never_tested_rate
```

这些指标用于改进环境生产、工具协议和 rubric，而不是直接作为训练 reward。若某类环境的 reject rate 长期异常高，应回到环境生产流水线检查 task quality、anti-cheat、dependencies 和 grader 稳定性。

## 8. 不进入本文的内容

以下内容属于后续算法设计或数据实验，不在本文冻结：

```text
具体 SFT loss 权重
process penalty 的 advantage 计算方式
不同任务族的接受率阈值
蒸馏 teacher 选择
MOPD / proximal policy 细节
采样温度和 top-p replay 的数值策略
```

这些内容应在 `RL_algorithm_design.md` 或新的实验计划中展开。
