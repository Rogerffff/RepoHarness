# RepoHarness 中 GRPO、DIS、PPO、SAO 与 CompactionRL 的选择分析

> 状态：算法演进讨论稿。本文已经记录 version-aware fully async + faithful DIS 的当前定案，但不表示该链路、SAO 或 CompactionRL 已经在 RepoHarness 或 slime 中完成实现。
>
> 日期：2026-07-12。

## 1. 结论先行

我的结论不是“现在应该把 GRPO 推翻，立即改成 SAO”，而是：

1. **当前首训仍应保留 GRPO，但正式链直接采用 version-aware fully async + faithful DIS。** RepoHarness 已经围绕 GRPO 完成 S0、S1 和 P3 的大量真实验证；目前最紧迫的问题是独立 FA 工作流中的 prompt group、fan-out、batch admission、loss denominator、真实 weight version 和 DIS 正确性。此时直接切换 critic-PPO，会把尚未关闭的 adapter 问题与 value model、GAE、critic 调度问题叠在一起。
2. **DIS 已从“GRPO 之后的算法增量”上升为正式 fully async GRPO 的正确性组件。** 新论文不仅报告 SAO 优于 GRPO，也报告 GRPO+DIS 明显优于并稳定于标准 GRPO。DIS 不要求 critic，且 RepoHarness 已经保存 rollout token logprobs，改动面远小于 SAO。但当前 slime 的 TIS/IcePop 插件只是近似接入点；正式链需要 faithful custom loss 和逐 token 数值对拍。
3. **PPO/SAO 非常值得做，但更适合作为第二阶段算法实验，而不是首个训练闭环。** 这既符合论文证据，也能形成更有价值的项目叙事：同一套 token-faithful agentic RL 基础设施，依次验证 GRPO、GRPO+DIS、标准 PPO、SAO 增量。
4. **现有 8×RTX PRO 6000 机器有机会完成 30B-A3B PPO/SAO 的短程 bring-up，但不能据此承诺可经济地完成正式 SAO 训练。** GPU 显存可能通过 actor/critic 顺序驻留和 CPU offload 解决；更大的风险是第二份 30B critic 的 host memory、optimizer state、PCIe 交换时间、两次 critic update，以及尚未准备的 value pretraining。
5. **slime 提供了实现 SAO 所需的大部分基础积木，但截至当前远端主分支没有完整 SAO 实现。** 它有 PPO、critic、GAE、自定义 advantage、自定义 loss、自定义 TIS、参数冻结和 fully-async rollout；它没有开箱即用的 DIS 语义、Skip-Observation GAE、每次 policy 更新两次 critic 更新、SAO value pretraining 配方和经过验证的 30B-A3B 八卡 SAO 脚本。
6. **CompactionRL 进一步证明，真正开启 compaction 后不能只把 branches 当作普通 fan-out。** summary 是影响后续执行状态的策略动作；长期训练还需要 summary token provenance、execution/summary segment 类型、全局 token-level loss 选项和跨 segment credit assignment。但这不改变近期结论：32k、30～50 步的首次 GRPO 基线仍应明确关闭 compaction。

因此建议的顺序是：

```text
独立 FA 工作流先关闭 fully async GRPO 数据与运行时语义
  -> version-aware GRPO n=8 + faithful DIS（明确禁用 compaction）
  -> IcePop-style 近似只作实现对照，不替代正式目标
  -> PPO 资源与 critic 正确性短程预实验
  -> SAO-lite：single rollout + DIS + Skip-Observation GAE（仍关闭 compaction）
  -> CompactionRL：summary joint training + token-level loss + cross-trajectory GAE
  -> 只有 value model、summary provenance 和吞吐验证通过后，才开启正式压缩训练
```

> **2026-07-12 fully async-first 定案**：P3 已测得 `wait_time_ratio=0.82`、尾部空闲 26%～28%，超过 fully async 升级阈值。项目直接选择 version-aware fully async + faithful DIS，不再考虑 session-pinned policy 或 bounded async/update barrier。bring-up 与正式预算运行同一条协调和算法路径，只缩小模型、任务数、并发和 optimizer step；faithful DIS 与 slime IcePop-style 近似仍必须分开命名。

## 2. 四份材料实际说明了什么

### 2.1 GLM-5：异步 GRPO 仍然可以工作，但需要补偿机制

GLM-5 技术报告采用异步 group-wise GRPO，并使用与 IcePop 接近的双边 token 过滤。它记录每次模型响应涉及的 policy weight versions，丢弃过度陈旧样本和环境故障样本。

对于过滤后不完整的 GRPO 组，GLM-5 采用了一个很工程化的策略：有效成员超过组大小一半时重复有效样本补齐，否则丢弃整组。这说明大规模团队也遇到了我们正在讨论的 prompt group 缺员问题。

但这个策略不应直接照搬。重复有效成员会改变样本权重，并可能重复放大少数成功或失败轨迹。RepoHarness 首版已经定案不做同 prompt 成员补采，也不复制已有成员：只把完整、合格且版本相容的 PromptGroup 放入 ready queue；残缺组到期后拒绝在线 GRPO，但保留其中可信 artifact 用于审计和离线研究。只有未来实测确认残组浪费显著，并另行完成偏差消融后，才重新评估成员补采或重复成员策略。

### 2.2 GLM-5.2 博客：从 group-wise 转向 critic-PPO 的直接触发点

博客给出的触发点不是“coding agent 天生不能用 GRPO”，而是以下因素同时出现：

- rollout 极长；
- compaction 把一次执行切成数量不等的 trainable sub-traces；
- 同一 prompt 的不同 rollout 产生不同数量和长度的 sub-traces；
- 训练希望保留所有 sub-traces，并做 token-level credit assignment；
- group-wise 等待与相对比较在全异步大集群里放大长尾和 policy lag。

critic-PPO 不要求每个 prompt 产生固定数量的同题 rollout，可以为单个 rollout 内不同 action token 估计 advantage，因此在这种条件下更自然。

### 2.3 SAO 论文：不是“普通 PPO 改成 n=1”

SAO 至少包含四个互相依赖的部分：

1. group size 1，取消同题组等待；
2. DIS 直接比较当前策略与 rollout 行为策略的 token logprobs；
3. 每次 policy update 对 critic 更新两次，并冻结 critic attention；
4. Skip-Observation token-level GAE，只在模型 action token 之间传播 advantage。

论文还强调 value model 需要预训练。把 slime 的 `--advantage-estimator ppo` 打开，只能称为“标准 PPO bring-up”，不能称为 SAO 复现。

论文在 SWE-Bench Verified 上报告：基座 23.0、GRPO+DIS 27.0、SAO 29.8。更值得注意的是，SAO 与 GRPO+DIS 在训练早期接近，约 400 步后才明显拉开。RepoHarness 当前首训只计划 30~50 步，因此 SAO 的最终优势未必能在第一轮短实验中显现。

### 2.4 CompactionRL：压缩不是数据预处理，而是可训练策略的一部分

《CompactionRL: Reinforcement Learning with Context Compaction for Long-Horizon Agents》与 SAO 来自同一批作者，补上了 GLM-5.2 博客中“如何训练 compacted sub-traces”的细节。它的关键判断是：summary 决定压缩后策略能看到什么，因此 summary generation 本身也是 action，不能只把它当成 harness 在推理时做的无损预处理。

它采用以下流程：

1. 当剩余 context budget 小于阈值时，向同一个 trainable policy 追加固定 summary instruction；
2. summary 需要保留原始目标、已完成操作、重要 observation、未解决错误、当前状态和下一步；
3. 重建上下文为 system prompt + 包含 summary 的 resume user message + 最近两个完整 assistant-observation steps；
4. 完整 rollout 划分为 execution segments 和 summary segments，两者共享最终任务 reward；
5. 原始 summary generation tokens 参与 policy loss，但重建上下文中复制的 summary、最近历史和 observation 必须全部 mask 为 0；
6. 使用 token-level loss normalization 处理 segment 数量与长度不一致；
7. 使用 cross-trajectory GAE 修正早期 segment 到最终 reward 的时间距离。

cross-trajectory GAE 的具体做法是：先在每个 segment 内计算 local GAE，再把第 `s` 个 segment 的 advantage 乘以 `(gamma * lambda) ^ N_after`，其中 `N_after` 是同一 rollout 后续全部 segment 的 trainable token 数。这样不会因为切段而把最终 reward 错误地放到每个 segment 的“近处”。论文明确承认它仍是 full-trajectory GAE 的近似，不会精确恢复跨 segment 的 value bootstrap。

这篇论文还提供了两个很强的实验证据：

- 固定 execution agent，只更换 summary agent，SWE-bench Verified 可从 49.0 变化到 55.5，说明 summary quality 本身足以显著改变任务结果；
- 在 GLM-4.5-Air 上，完整 CompactionRL 为 66.8/24.5；去掉 token-level loss 降到 60.0/21.3，去掉 cross-trajectory GAE 降到 63.0/22.5。segment weighting 的影响甚至大于 cross-segment GAE。

但它不是无条件提升。30B 模型在关闭 compaction 的 single-window SWE 评测中，CompactionRL 为 43.7，低于基座 47.5 和普通 PPO 50.0；优势主要出现在训练与评测都开启 compaction 时。这要求我们的实验必须分开报告 single-window 与 compacted 两个评测面。

还要注意，CompactionRL 论文写的是标准 PPO `current policy / old policy` ratio，没有引入 SAO 的 direct rollout ratio 或 DIS。两篇论文虽然作者与生产背景高度重合，但公开材料没有给出完整组合目标；不能因为它们都用于 GLM-5.2 就宣称“CompactionRL 已经等于 SAO + compaction”。

## 3. “一次 rollout 产生多个 Sample”是否说明 GRPO 不适用

### 3.1 先统一三个对象

当前讨论里最容易混淆的是：

```text
PromptGroup
  = 同一个 prompt 独立运行 n 次得到的一组 rollout executions

RolloutExecution
  = 一次完整环境执行，有一个最终任务 reward

Branch / slime Sample
  = 同一次 execution 因消息图分叉、历史重写、compaction 或子 agent
    形成的一段可训练 token 叶链
```

一个 `RolloutExecution` 产生多个 `Sample`，不等于 GRPO 的 group size 变大，也不等于这些 `Sample` 是独立同题 rollout。它们共享同一次环境结果，不能被错误地当作多个独立 reward observation。

### 3.2 GRPO 在 fan-out 下仍然可以保持正确

只要遵守以下顺序，GRPO 在多 branch 下仍然有清晰语义：

1. 先以独立 `RolloutExecution` 为单位收集同 prompt 的 n 个 reward；
2. 在这 n 个 execution 之间计算 group-relative advantage；
3. 把某个 execution 的 advantage 广播给它自己的全部 branches；
4. 同一 execution 的所有 trainable token 共用一个 rollout-level loss denominator；
5. branch 数增加不得放大这个 execution 在 policy loss 中的总权重。

这正是 S2-0b 当前设计的方向。因此，“P3 发现 fan-out”首先证明 adapter 必须修，而不是直接证明 GRPO 算法不能用。

需要补充一个边界：上述“rollout-level denominator”是近期 GRPO 兼容方案，它让每个独立 execution 无论有多少 branches 都只贡献一个 rollout mean。CompactionRL 使用的是另一种经过实验验证的目标：全局 trainable-token mean，较长 rollout 会按 token 数贡献更多，但不会因为被切成更多 segments 而额外增加权重。两者都能消除“每个 segment 独立平均”造成的 segment-count bias，却不是同一个优化目标。未来压缩训练应把 reducer 作为算法配置做消融，治理层只负责准确提供两种分母，不替训练算法定案。

### 3.3 但 compaction 会让 PPO/SAO 更自然

即使上述 GRPO 语义可以做对，compaction 仍会带来三个现实问题：

- 同题组必须等待最慢的 execution，长轨迹和重试使组完成延迟变大；
- 不同 execution 的 branch 数与 token 数差异很大，group advantage 虽然可广播，但只能提供粗粒度的整轨迹 credit；
- fully-async 下，先完成成员等待整组期间会进一步变旧，DIS 只能过滤或修正一部分 off-policy，不能消除等待本身。

SAO 的 value model 能给不同 action token 不同 advantage，并且 n=1 不需要同题组完成，因此长期方向更匹配“自动 compaction + subagent + 128k 上下文 + fully async”。

这也直接化解了当前“缺员 prompt group”问题中最棘手的一部分：在 SAO 中，某条 rollout 因基础设施故障被拒绝，只损失这一条 rollout，训练缓冲区可以从其他 prompt 的已完成 rollout 补足 batch；不需要为了保住 GRPO 组统计去等待同题补采，也不会因为一个永久失败成员丢掉七条有效兄弟轨迹。不过，SAO 只是取消了“同题组完整性”约束，环境内幂等重试、失败归因、staleness gate 和全局 batch admission 仍然需要保留。

SAO 与 CompactionRL 不是互斥替代关系。SAO 主要解决异步 single-rollout、direct importance sampling 和 observation token 跨越；CompactionRL 主要解决 summary joint training、segment weighting 与 compaction boundary credit assignment。论文没有公开证明“SAO + CompactionRL”的完整组合，但从契约上看，Skip-Observation GAE 与 cross-trajectory correction 可以组成两层 credit assignment：segment 内跨 observation，segment 间按 lineage 与后续 token 距离修正。组合前必须用手算轨迹做数值验证，不能把两个公式机械相乘后直接训练。

## 4. P3 到底有没有发生 Claude Code compaction

P3 的真实事件记录表明，同一次 session 确实可能返回 2、3、4、8 个 trainable samples。例如 formal J4 中 `index=22 / group_index=5` 返回了 8 个 samples。

但是这些证据只记录了叶链数量，没有记录分叉原因。现有多叶链还可能来自：

- Claude Code 在后续请求中剥离旧 thinking block；
- message history 被重写或重新渲染；
- TrajectoryManager 在 token identity 不一致处做 REALIGN/FORK；
- 真正的自动 compaction；
- subagent 或其他内部会话分叉。

因此不能把 `returned_samples > 1` 直接解释为 `compaction=true`。当前 `rh2/src/repoharness2/contracts/trajectory.py` 已经有唯一权威对象 `CompactedSubTraceLineage`，不能再新建第二套 lineage schema；应该扩展该对象并让编排层真实填充。建议在现有 `compaction_kind` 的基础上补足以下事实：

```text
compaction_kind:
  context_compaction
  subagent_fork
  retokenization_drift_fork
  history_rewrite_fork
  unknown_fork

lineage_evidence_source: harness_event | prefix_transition | inferred | unknown
pre_compaction_context_tokens
post_compaction_context_tokens
```

现有 `compaction_event_id / parent_trajectory_id / parent_branch_id / fork_point_token_index` 继续作为权威字段，不重复维护。若黑盒 harness 不提供明确事件，最多写 `inferred` 或 `unknown`，不能伪装成已知事实。

CompactionRL 还要求 `compaction_event_id` 必须能解析到一个 canonical compaction event artifact，而不是只有一个没有内容的标识符。该 event artifact 只保存事件级事实：

```text
trigger_context_token_count
remaining_context_tokens
compaction_threshold_tokens
summary_capture_record_refs
summary_token_span
retained_atomic_step_refs
resume_template_version
reconstructed_context_digest
```

segment 自身的训练位置事实继续归 branch/segment 权威对象，不复制进 event：

```text
segment_index / segment_count
segment_type: execution | summary
subsequent_trainable_token_count
```

其中 `subsequent_trainable_token_count` 应由排序后的同 rollout segments 和各自 loss mask 推导并互检，不能由调用方随意申报；现有 `RewardFacts.segment_count / rollout_loss_denominator` 应复用或收敛，而不是为 CompactionRL 再建一套同义账目。

其中 assistant tool call 与对应 observation 必须视为原子步骤，compaction 只能发生在 observation 返回之后，不能把工具调用和工具结果拆到两个上下文窗口。summary 的原始采样 token 可以训练一次；resume prompt 里复制的 summary 和保留的最近步骤必须通过现有 `replay_prefix_loss_masked` 证明全部为 mask=0。

对白盒 harness，这些事实可以直接由 runtime 产生。对 Claude Code 等黑盒 harness，model proxy 虽然通常能捕获内部 summary API 请求和响应，但还必须可靠识别“这是 compaction summary”，并重建它与后续请求的 lineage；做不到时可以继续用于评测或审计，不能进入 CompactionRL policy loss。

## 5. Claude Code 的 compaction 能否关闭

可以控制，而且当前 slime 已经给了传递入口：

- `reference/slime/slime/agent/harness/claude_code.py` 会把 `SLIME_AGENT_CC_EXTRA_ENVS` 的 JSON 合并进 Claude Code 子进程环境；
- Claude Code 参考实现支持：
  - `DISABLE_COMPACT=1`：禁用自动和手动 compaction；
  - `DISABLE_AUTO_COMPACT=1`：只禁用自动 compaction，保留手动 `/compact`。

当前 P3 脚本没有设置这两个变量。因此现有实验设计中“关闭 compaction”的文字定案尚未变成运行时硬事实。

GRPO 首训建议使用：

```bash
export SLIME_AGENT_CC_EXTRA_ENVS='{"DISABLE_COMPACT":"1"}'
```

同时必须做三件事：

1. 启动 inspector 验证环境变量确实进入 harness 进程；
2. 捕获到明确 compaction 或无法解释的上下文收缩时，轨迹不得进入 GRPO 基线；
3. 32k 上下文耗尽时按 `unfinished / context_limit` 结束并屏蔽 policy loss，不允许静默压缩后继续。

需要注意：关闭 compaction 不会自动消除所有多 branch。thinking 剥离和 token identity REALIGN 仍可能造成分叉，所以 S2-0b 的 rollout/branch 账目仍然必须实现。

## 6. DIS 为什么是当前最值得先做的算法增量

### 6.1 DIS 可以同时用于 GRPO 和 PPO

DIS 解决的是“当前训练策略与实际生成 token 的 rollout 策略不一致”，与 advantage 来自 GRPO 组比较还是 critic 无关。因此可以先做：

```text
GRPO advantage + DIS token mask
```

后续再做：

```text
critic/GAE advantage + DIS token mask
```

这让我们可以把“off-policy 稳定性收益”和“critic credit assignment 收益”分开消融。

### 6.2 slime 的 TIS/IcePop 与论文 DIS 不是完全同一件事

slime 最新主分支提供：

- `--use-tis`；
- `--custom-tis-function-path`；
- `vanilla_tis_function`：把 ratio clamp 到上下界后继续加权；
- `icepop_function`：ratio 超出双边范围时权重归零；
- `--custom-loss-function-path`：可替换整个 loss；
- `--custom-advantage-function-path`：可替换 advantage/return 计算。

`icepop_function` 在“超界 token 归零”上最接近 DIS，但 slime 默认 TIS 使用的是 clamp，不是 hard mask。更重要的是，标准 slime policy loss 仍可能同时保留 PPO old-policy ratio，而论文 SAO 明确把目标简化为 current policy 与 rollout policy 的直接 ratio。

因此分两档实现：

1. **GRPO + IcePop-style direct-rollout masking 近似档**：使用自定义 TIS hard mask，严格验证 ratio 来自训练时策略 logprob 与 rollout logprob；这是最小改动，但不能把结果直接标成论文忠实的 `GRPO+DIS`。当前 slime 是先算 PPO-style clipped policy loss，再把 TIS ratio 乘到已有 `pg_loss` 上，目标并不等同于论文公式。
2. **GRPO + faithful DIS**：使用 GRPO advantage，但用自定义 loss 直接实现论文的 `f(current/rollout ratio) * advantage * log π_current`，区间内保留 ratio 权重、区间外置零，并做逐 token 手算对拍。这才是论文 Table 2 中 `GRPO (w/ DIS)` 的合理复现目标。
3. **SAO 忠实档**：在 faithful DIS 之上换成 critic/Skip-Observation GAE advantage，再补齐 K=2 critic update、frozen-attention critic 和 value pretraining。不能只靠 `--use-tis` 或 `--advantage-estimator ppo` 宣称实现 SAO。

### 6.3 DIS 的算法掩码不得改写轨迹 loss mask

必须区分两种完全不同的 token 选择事实：

```text
provenance_loss_mask
  回答 token 是否由模型真实采样、角色是否允许进入 policy loss；
  属于 TrajectoryProjection 的不可变历史事实。

algorithmic_importance_mask / importance_weight
  回答本次 trainer step 中 current/rollout ratio 是否处于 DIS 信任区间；
  属于训练后端针对某个 policy step 的算法决定。
```

同一条轨迹在不同 trainer step 上会得到不同的 current-policy logprob 和 DIS ratio，因此算法掩码不能反向覆盖 `LossMaskSpan`。正确实现应保留原始 mask，额外产生 step-local 的 `dis_mask` 或 `importance_weight`，并记录：上下界拒绝比例、有效 token 数、全零梯度 rollout/microbatch 数、不同轨迹长度上的拒绝率和 ratio 分布。

当前 slime 的 TIS 路径会用修改后的 response mask 把超界 token 的分子贡献清零，但 `rollout_mask_sums` 仍来自原始 provenance mask。换句话说，被拒 token 仍留在原始 denominator 中而梯度贡献为零。该语义与“只对被接受 token 重新归一化”不同，正式 DIS 实现必须预注册 denominator 语义并用小张量手算对拍，不能在接插件时无意改变。

## 7. slime 最新代码到底支持了多少 SAO

### 7.1 远端状态

检查时：

```text
local HEAD  = e848052a
origin/main = 680824dd
本地落后 8 commits
```

这 8 个提交主要是 disaggregated rollout 权重拉取、Docker 修复、`--release-train` 等，没有 SAO、DIS、Skip-Observation GAE 或 frozen-attention critic 的完整提交。由于 `reference/slime` 有本地未跟踪导览文件，本次只 fetch 检查，没有破坏性更新工作树。

### 7.2 已有能力

slime 已有：

- `--advantage-estimator ppo`；
- actor 与 critic 两套 Megatron role；
- value loss 和标准 token-level GAE；
- `--num-critic-only-steps`；
- actor/critic 分角色 YAML 配置；
- `--only-train-params-name-list` 和 `--freeze-params-name-list`；
- 自定义 advantage、TIS 和完整 loss；
- PPO 的 4B、8 卡 colocate 与 4 训练卡 + 4 rollout 卡测试；
- fully-async rollout worker；
- compact/subagent fan-out 的嵌套输出检查、共享 `rollout_id` 和 per-rollout denominator；
- `--calculate-per-token-loss` 对应的全局 token-level reducer。

代码层还有一个必须提前登记的文档漂移：`TrajectoryManager.get_trajectory` 当前给每个 emitted Sample 写入完整 trajectory reward，而 coding-agent README 仍声称按 `reward / K` 拆分。当前源码与 RepoHarness 的 full raw reward 语义更接近 CompactionRL；后续实现必须以结构化 reward facts 和代码测试为权威，不能根据 README 再做一次除法。

这些能力足以让我们不从零写训练框架。

但“契约和基础积木已经存在”不等于在线实现已经完备。当前成熟度应拆开表达：

- token ids、逐 token rollout logprobs、provenance loss mask、top-p/routing replay 已有 S1/P3 实证；
- policy version 契约已存在，但 RH2 默认路径仍由静态 `SlimeBindingConfig.policy_version="step_0"` 回填，并默认构造 `staleness_steps=0`；fully async 前必须接入真实 SGLang `meta_info.weight_version`；
- `TokenSpan` 已区分 sampled assistant 与 tool/user/system context，可作为 action/observation 的基础，但还没有稳定的 `turn_id / action_id / observation_id` 与下一 action linkage，不能直接声称 Skip-Observation GAE 输入已经完整；
- `RewardFacts.segment_count` 能记录 branch 数，但当前多 branch 投影的 `segment_index=None`，尚缺 CompactionRL 所需的 branch 级 execution/summary 顺序和跨 segment token 距离。

### 7.3 尚缺能力

slime 当前标准 PPO 路径仍有以下差距：

- GAE 按 response token 顺序计算，不识别 action/observation 边界，没有 Skip-Observation；
- critic 每个 batch 默认只训练一次，没有 SAO 的 `K=2` 更新频率；
- attention freeze 只有通用正则参数选择，没有经过验证的 Qwen3-30B-A3B critic 参数名单；
- 没有 SAO value pretraining 数据和初始化流程；
- 没有公开的 SAO 配置或验收测试；
- 最新 `run-glm5.2-744B-A40B.sh` 实际仍是 GRPO + 默认 TIS clamp，不是 SAO；
- fully-async 示例只验证 GRPO，PPO+critic+n=1+黑盒 coding harness 的组合仍需单独实机验证；
- 没有 CompactionRL 的 summary segment 分类、canonical compaction event 或 cross-trajectory GAE；
- coding-agent 示例能把 auto-compaction 表示成多叶链，但“检测到 token prefix 分叉”不等于已经恢复论文所需的 summary/action 语义。

所以较准确的说法是：**slime 大约提供了实现所需的基础框架，但 RepoHarness 仍要实现和验证 SAO 专用算法插件与数据契约。**

## 8. 8 卡上 PPO/SAO 是否可行

### 8.1 GPU 显存不是唯一问题

slime 当前在 PPO 模式下：

- critic GPU 数强制等于 actor GPU 数；
- critic 与 actor 使用同一个 placement group；
- 两者是不同 Ray actor，在相同物理 GPU 上依靠 wake/sleep 和 CPU offload 顺序运行；
- critic 先训练并返回 CPU values，actor 再计算 advantage 和训练；
- 启用 critic 时强制 `offload_train=True`；
- `--release-train` 当前不支持 critic。

因此在 P3 的 T3 布局上可以尝试：

```text
GPU 0~3：actor 与 critic 顺序复用
GPU 4~7：SGLang rollout
host RAM：保存 actor/critic offload 状态与 optimizer state
```

4×96GB 训练卡大概率能在“某一时刻只唤醒 actor 或 critic”条件下装下 30B-A3B，但这还不是整个可行性结论。

### 8.2 host memory 和 PCIe 更可能成为瓶颈

P3 的 actor-only 30B 训练已经在 optimizer CPU offload 下观测到约 462GB host used。P3 机器有 1716GB host RAM，所以当时余量很大；一般租到的 512GB 节点则很危险。

增加 30B critic 意味着第二份参数、value head、optimizer state 和 offload 交换。即使冻结 attention，Qwen3-30B-A3B 的 MoE experts 仍占大量参数，不能假设 optimizer memory 会缩到很小。经验估算应把 800GB host RAM 视作 30B actor+critic bring-up 的安全起点，正式租机前必须由 inspector 依据实际 trainable parameter count 计算，而不是写死一个数字。

吞吐方面，P3 actor train 约 252 秒，而完整 step 约 1387 秒，82% 时间在等 rollout。理论上 critic 计算的一部分可以被 rollout 长尾掩盖；但 actor/critic 两次唤醒、offload、K=2 critic update 和 PCIe 传输也可能吃掉这部分余量。需要实测，不能从显存能装下推导出训练经济可行。

### 8.3 建议的 PPO/SAO 预实验梯子

不要第一次就跑正式 30B SAO。建议：

1. **PPO-small**：4B dense，n=1，单步；验证 critic value、GAE、actor update、checkpoint 和 fully-async 兼容。
2. **PPO-30B train-only replay**：使用已有或合成 rollout dump，不启动黑盒 harness；在 4 张训练卡上验证 actor+critic 内存峰值、offload 时间、标准 PPO 数值。
3. **PPO-30B online mini**：4 训练卡 + 4 rollout 卡，1~2 步；记录 actor、critic、rollout、offload、weight sync 分段墙钟。
4. **DIS plugin test**：固定 token/logprob 小张量与手算结果逐位对拍，再接真实 rollout。
5. **Skip-Observation GAE test**：用明确的 action/observation token spans 做手算对拍；观察 observation token 必须为 mask=0，且跨 observation 的 bootstrap 指向下一 action。
6. **SAO-lite**：n=1 + DIS + Skip-Observation GAE；先 K=1，再 K=2；最后才验证 frozen-attention critic。
7. **value pretraining**：若 critic explained variance、value loss 或 advantage 分布不健康，先停 policy update，建立 value warmup/pretraining，不允许靠继续在线训练碰运气。
8. **CompactionRL-offline**：用合成的 execution-summary-execution 三段轨迹，对拍 summary mask、全局 token reducer、`N_after` 和 cross-trajectory GAE。
9. **CompactionRL-online mini**：先只允许一次 compaction，再扩到最多三次；分别运行 summary loss 开/关和 local/cross-trajectory GAE 对照。

新论文再次确认 value warmup 不是可选小项：两个实验模型都从同模型 checkpoint 初始化 critic，并先做 50 steps value pretraining；在线训练仍采用每 batch 两次 value update、一次 policy update。RepoHarness 不应直接照搬“50”这个数字，但 PPO/SAO/CompactionRL 计划必须为 value-only warmup、critic checkpoint 和 explained variance 验收留出独立阶段。

## 9. 对当前实验设计的具体修改建议

现有 `repoharness_validation_experiment_design.md` 的 GRPO 首训结论可以保留，但需要修正四处表述。

### 9.1 修正“关 compaction 已成立”

应改成：

```text
GRPO 首训要求在运行期传入 DISABLE_COMPACT=1，并由 inspector 验证。
发现 compaction 或未知上下文收缩时，该轨迹退出 GRPO 基线。
```

### 9.2 把 fan-out 与 compaction 分开

应明确：fan-out 已在 P3 真实发生，S2-0b 必须处理；但是否为 compaction 未知。即使禁用 compaction，GRPO adapter 仍需 rollout-level advantage 和 denominator。

### 9.3 新增 GRPO+DIS 对照

建议第一轮算法矩阵至少包含：

| 实验 | group | compaction | off-policy 处理 | 目的 |
| --- | ---: | --- | --- | --- |
| A | n=8 | 强制关闭 | faithful DIS | 正式 version-aware fully async GRPO 基线 |
| B | n=8 | 强制关闭 | IcePop-style 近似 | 只比较接插件近似与论文忠实目标的差异 |
| C | n=1 | 强制关闭 | 标准 PPO | 验证 critic 基础链路 |
| D | n=1 | 强制关闭 | SAO-lite | 隔离 DIS、Skip-Observation GAE 与 critic 更新设计 |
| E | n=1 | 可控开启 | CompactionRL | 验证 summary joint training 与跨 segment credit |

A 是近期正式实验；B 是小规模实现对照，不应占用完整正式预算；C/D/E 是后续预实验和算法扩展，不应同时塞进第一次正式训练。尤其不能把 D 与 E 合并，否则无法判断变化来自 single-rollout、DIS、critic、summary training 还是 compaction。

### 9.4 新增算法切换触发条件

以下指标用于触发“从 GRPO 为主升级到 PPO/SAO 为主”的优先级评审：

- compaction 需要开启，且真实 rollout 中 compaction 比例超过 10%；
- 每个 execution 的 branch count 变异系数持续较高，并明显影响 batch packing；
- GRPO 同题组 p95 完成时间与中位数之比超过 2；
- 组等待造成的额外 staleness 超过一个 policy version，或 DIS reject ratio 持续过高；
- 残缺组拒绝造成的可信生成 token 浪费超过 15%；
- 轨迹级广播 advantage 无法区分明显不同质量的行动阶段；
- 训练预算扩展到 64k/128k、100+ turns 或 400+ policy steps。

这些阈值应先作为预注册观察指标，不应实现成“满足任意两项就自动切换算法”的硬闸门。不同指标可能有完全不同的根因：例如 branch count 变异可能只是 adapter packing 问题，DIS reject ratio 高也可能是推理/训练 logprob 对齐错误；反过来，如果 compaction 已成为任务完成的必要能力，单独一项也可能足以启动 PPO/SAO 评审。最终判断应同时看算法正确性、统计效率和系统墙钟成本。

### 9.5 为 CompactionRL 预留独立实验协议

当算法切换触发条件满足、决定正式开启 compaction 时，建议预注册三个互相匹配的评测面：

```text
Single-window：关闭 compaction，只允许一个 peak context window
Compacted：训练和评测均允许同样次数的 compaction
Long-context reference：关闭 compaction，但提供近似相同的有效总 token budget
```

首轮 compaction 实验至少做四个对照：普通 PPO 无压缩、压缩但 summary mask=0、压缩且 summary 参训、完整 CompactionRL 加 cross-trajectory GAE。应新增的运行指标包括：

- compaction trigger rate、每条 rollout compaction 次数和触发 token 位置；
- execution/summary segment 数量、长度和 trainable token 比例；
- summary token 数、summary 后重复搜索/重复工具调用数量；
- `P(success | compaction triggered)`，不能只看全量任务平均；
- single-window 与 compacted 的能力差，监控 train-test mismatch；
- local GAE 与 cross-trajectory GAE 的 advantage 分布、critic explained variance；
- per-rollout mean 与 global token mean 两种 reducer 的有效权重分布。

论文使用 64k/80k peak context、10,240 token response headroom、最多三次 compaction 和最多 250 turns。对 RepoHarness 来说这些只能作为上界参考；在 32k、600 秒任务里如果 compaction trigger rate 很低，CompactionRL 没有足够训练信号，应继续保持关闭，而不是为了复现论文人为频繁压缩。

## 10. 最终建议

### 近期：version-aware fully async GRPO + faithful DIS

先完成独立 FA 工作流，并补上 `DISABLE_COMPACT=1` 的运行时验收。GRPO 的价值是让现有基础设施在不引入 critic 的条件下闭环，而不是因为它一定是长期最优算法。正式链直接使用 faithful DIS，不提供无 DIS 或静态 policy version 旁路。

这里有一项会直接影响首次正式 GRPO 运行：P3 启动脚本没有设置 `DISABLE_COMPACT`，所以“关闭 compaction”尚未成为运行事实。正式基线必须通过 `SLIME_AGENT_CC_EXTRA_ENVS` 注入该变量，并由 inspector 证明 Claude Code 子进程真实收到；发现明确 compaction 或无法解释的上下文收缩时，该轨迹退出 GRPO 基线。关闭 compaction 仍不会消除 thinking 剥离或 retokenization fork，因此 S2-0b 的 fan-out 账目不能省略。

### 实现对照：IcePop-style 近似不是正式目标

RepoHarness 已经具备 token-faithful rollout logprobs、loss mask 和 top-p/routing replay，policy version 与 action/observation 边界则是“契约已预留、fully async/SAO 前仍须完成真实接线”。faithful DIS 利用这些资产并保障异步链路的 off-policy 正确性；slime IcePop-style TIS 只用于小规模数值与性能对照。

不过，30～50 step 的首次短实验不应把“DIS 必须显著提升最终能力”写成成功条件。论文中 SAO 与 GRPO+DIS 的长期差异约在数百步后才展开；短实验更适合验证 ratio 分布、有效 token 比例、梯度稳定性、长度相关拒绝偏差和后半程是否避免崩溃。

### 中期：把 SAO 做成一个明确的算法工作流

这对项目和个人学习都很有价值，但应诚实分阶段：

```text
标准 PPO bring-up
  -> direct rollout ratio + hard-mask DIS
  -> action/observation span + Skip-Observation GAE
  -> K=2 critic update
  -> frozen-attention critic
  -> value pretraining / warmup
  -> fully-async single-rollout coding agent（无 compaction）
  -> canonical compaction event + summary provenance
  -> token-level reducer + cross-trajectory GAE
  -> CompactionRL online ablation
```

每一步都有独立数值测试和消融，最终项目叙事会比“把配置从 GRPO 改成 PPO”更强，也更可信。

### 长期架构：保持算法中立

RepoHarness 不应把 PromptGroup、critic 或 SAO 写死进环境核心。中立投影应继续提供：

- `rollout_execution_id / prompt_group_id / branch_id`；
- action/observation token spans；
- rollout token ids、logprobs、loss masks；
- policy version 序列和 staleness；
- compaction/subagent lineage；
- execution/summary segment 类型、顺序和跨 segment token 距离；
- rollout-level reward facts 与 token-level penalty spans。

GRPO adapter 消费 prompt group；PPO/SAO adapter 消费 critic values 和 action spans；CompactionRL adapter 额外消费 canonical compaction events 与 segment lineage；DIS 是这些算法可共享的训练侧策略。这样无论最后选择 slime、verl，还是新的训练后端，RepoHarness 的环境与治理层都不需要重写。

## 11. 关键代码与资料路径

### 论文和博客

- `docs/harness_improve/external_paper_references/pdfs/2607.07508v1.pdf`
- `docs/harness_improve/external_paper_references/pdfs/2607.05378v1.pdf`
- `docs/harness_improve/external_paper_references/pdfs/R5_glm5_agentic_engineering_2602.15763.pdf`
- `docs/harness_improve/external_paper_references/pdfs/R5b_glm5_2_blog_zai.pdf`
- `docs/harness_improve/external_paper_references/pdfs/glm5.2_blog_RL.md`

### RepoHarness

- `docs/agentic_RL/training_design/repoharness_validation_experiment_design.md`
- `docs/agentic_RL/repo_harness_rh2_workstreams/04-s2-execution-plan.md`
- `docs/agentic_RL/repo_harness_rh2_workstreams/preflight/preflight_report.md`
- `rh2/src/repoharness2/adapters/slime/projection.py`
- `rh2/src/repoharness2/adapters/slime/generate.py`

### slime

- `reference/slime/slime/utils/arguments.py`
- `reference/slime/slime/backends/megatron_utils/loss.py`
- `reference/slime/slime/utils/ppo_utils.py`
- `reference/slime/slime/backends/megatron_utils/actor.py`
- `reference/slime/slime/backends/megatron_utils/cp_utils.py`
- `reference/slime/slime/ray/placement_group.py`
- `reference/slime/slime/ray/rollout.py`
- `reference/slime/train.py`
- `reference/slime/train_async.py`
- `reference/slime/slime/rollout/fully_async_rollout.py`
- `reference/slime/tests/test_qwen3_4B_ppo.py`
- `reference/slime/tests/test_qwen3_4B_ppo_disaggregate.py`
- `reference/slime/scripts/run-glm5.2-744B-A40B.sh`
- `reference/slime/slime/agent/harness/claude_code.py`

### Claude Code compaction

- `reference/claude-code-docs/claude-doc/16-autocompact-detail.md`
