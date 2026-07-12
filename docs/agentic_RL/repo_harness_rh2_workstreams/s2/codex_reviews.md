# codex 复核意见存档（S2 前）

> 背景：codex 的复核意见原先写在 `tmp/codx_adv.md`，但 `tmp/` 被 `.gitignore` 忽略（`.gitignore:16`），新 clone 中不存在、引用不可复现。本文件将两轮意见全文迁入版本控制；S2 计划与状态文档的引用一律指向本文件。原 tmp 文件此后只作草稿箱。

---

## 轮次 1（2026-07-10：P3 收口后全面复核 → 已消化为 S2 计划 G6~G10 + S2-0b）

### 需要纠正的地方

- P3 应称为"训练后端与架构决策完成"，不能称为"严格端到端全部绿灯"。formal J4 最后仍失败于 `num_rollouts (19) < global_batch_size (32)`；J5 gbs16 失败于 23 个 microbatch 无法对齐 24。J5 gbs20 成功证明了根因，但 gbs20 只是诊断对照，不是正式方案。
- 本地没有 P3 的 rollout_0.pt。远程同步时排除了大型 .pt 张量文件，因此不能"直接重放真实 dump"。不过保存了完整的 J4 事件元数据：44 个原始样本、31 个保留样本、19 个有效 rollout，以及每个 rollout 的 fan-out、长度和剔除状态。这足以构造真实形状回归夹具，但不能原样重跑 slime tensor converter。
- S2 计划还没有吸收 batch schedule 准入任务。当前计划仍从 S2-6 导出器起步。P3 之后，batch admission 和 fan-out 规范化才是训练主线第一阻塞项。
- fan-out 目前仍是实验级兼容。RepoHarness 返回的 `list[list[Sample]]` 已经打崩 slime 的 dynamic_filter 和 fully async `_key` 两处。正式方案应在 RepoHarness→slime 交付边界统一展平，同时保留 rollout_id、branch、group 和 reward 分摊语义，不应继续给 slime 各处打零散补丁。
- S2 的资格解封规则存在矛盾。计划一处说本机 S2-7 后可以产生 `online_policy_loss_eligible`，另一处又规定 `rh2_s2_signal_trusted = local AND gpu_verified`。两者必须统一。建议：本机验收只能解除"实现阶段封顶"，黑盒正式在线训练仍必须等待 GPU 侧真实拦截验证通过。
- `--network none` 不能直接作为黑盒 rollout 的最终网络方案。Claude Code 必须访问模型代理，容器里的 localhost 也不是宿主机。合理方案：依赖预装 + 隔离 Docker 网络 + 只允许访问模型代理/必要内部服务 + 公网默认拒绝。`--network none` 适合评分容器、纯本地白盒任务和安全单测。
- 导出器的原验收规模无法从现有本地资产重放。run8/run9 的 60+65 条原始 .pt 不在本地。保存了一条真实的多轮、t0 被剥离、包含完整 token artifact 的 run8 轨迹，正好可以验证锚定式重建。正式验收应改为：一条真实 t0 掉落轨迹 + 多轮/REALIGN/fan-out 合成回归夹具 + 下次短租时采集少量完整真实轨迹复验。
- S1 账本轻微不同步：deferred_risks 已把 S1-7b 改为 closed_by_p3_20260708，但 tasks.S1-7b 仍写 deferred_to_s4_pre_8card。【已修复：commit 0867f64a】
- 数据资产边界：数据冻结包本身可靠（四个 HF revision 固定、24 项 digest 一致、仓库级互斥通过），但 216 题只是静态存活集，还要过 golden/empty/假阳性/确定性四道环境门 + 目标模型 pass-rate 预筛才成为训练题单。

### 建议推进顺序

1. 确认 S1 检查点 2，修正账本状态表述。【已完成】
2. 新增 S2 前置任务：batch admission preflight/repair + fan-out 正规化。【已完成：S2-0b】
3. 使用 P3 真实事件元数据复现 44→31→19 和 23/24 两种失败。
4. 实现分叉感知离线导出器，使用保存的真实 t0 掉落轨迹验收。
5. 并行推进 SWE-Gym ingestion、环境四门和安全 Runtime。
6. 完成 Git sanitizer、CommandFilter、红队环境包和 S2 inspector。
7. 最后短租一次 GPU，合并验证 strict J4、真实在线拦截和少量完整轨迹留存。
8. fully async 暂不作为当前主线改造；首训先用 P3 已定案的 T3 分离 + train_async 双缓冲。

### 用户疑问（随轮次 1 提出）

分叉感知导出器是不是源自 final_review 的"双消费者 parity 证明"？对 SFT/warm-start 来说，同一个 Qwen MoE 模型的拒绝采样/RL 保留轨迹，和强 teacher 生成的轨迹，后续 SFT 输入是否都要 token 级轨迹重新分词？【解答已写入 S2 计划 S2-6 的"依赖关系澄清"：同 tokenizer/renderer 契约的自产轨迹直接用 token ids + loss mask，不重分词；异构 teacher 轨迹必须走结构化语义导出 + 学生 renderer 重渲染分词（SemanticSFT，G9 新缺口）】

### codex 对导出器的两点修正 + SemanticSFT 建议

- 分叉感知重建方向正确（叶链 tokens 为权威、capture records 只锚定 mask=1 区间），但它只阻塞：同策略 thinking rollout 的精确 token 回收、在线/离线 parity、同模型 warm-start/RFT——不阻塞所有 SFT。
- 原验收"60+65 条全部导出"不可执行（.pt 不在本地），改为真实 t0 掉落轨迹 + 合成回归 + 下次短租复验。
- SemanticSFT exporter 是新设计缺口：当前只有 token-faithful 出口，没有结构化消息/tool call/tool result/target/来源模型形态的通用 SFT 导出。建议 S2 至少完成 SemanticSFTRecord 契约和最小导出闭环，批量 teacher 数据生产放 S3，避免架构被 token-only 出口锁死。
- S2 最后应有一次短 GPU 验收（strict J4 + 真实在线拦截 + 代表性轨迹留存），不是重做 P3。

---

## 轮次 2（2026-07-11：对 commit 0867f64a / 53d1403a 的审查 → S2-0b 开工前必须补齐）

### 结论

两个提交整体方向正确，不需要回退。但 S2-0b 尚不能直接开工：存在两个影响 GRPO 算法正确性的严重遗漏，以及几处文档一致性问题。

### 严重问题 1：S2-0b 没有区分三层身份

正确层次：

```text
PromptGroup       同一任务 prompt 的 n 次采样（group_index / parent_rollout_id）
                  —— GRPO reward/advantage 归一化的单位
RolloutExecution  一次独立 harness 执行（Sample.index / rollout_id）
                  —— slime build_dp_schedule 按它计 global_batch_size
Branch            一次执行因 compaction/subagent 产生的叶链
                  —— 多 branch 共享 rollout_id，loss 按 rollout 聚合
```

P3 反例（本地事件元数据可复核）：J4 formal 中 group_index=5 只有一次有效 harness 执行 index=22，却 fan-out 出 8 个 branch——不能把这 8 个 branch 当成 8 次独立 GRPO 采样，也不能用它们凑 global_batch_size。

### 严重问题 2：P3 converter 在治理过滤 + fan-out 后会错误计算 GRPO reward normalization

`rh2/experiments/p3_preflight/rh2_convert.py` 的 `_post_process_rewards`（镜像 slime stock `slime/ray/rollout.py` 的 reshape-by-shape 逻辑）：保留样本数 == `rollout_batch_size × n_samples_per_prompt` 时按组 reshape；否则 `view(-1, total)` 把**全部样本折叠成一个大组**做均值中心化。J5 gbs20 实际保留 36 个样本 ≠ 名义 32，走了第二条路径，且 J5 日志确认 `rewards_normalization=True`。slime 自己的测试辅助文件（`reference/slime/slime/rollout/_fanout_test_helpers.py` 的 `grpo_normalize_by_group_index`）已明确指出该问题并给出 group_index 键控分组的原型。

含义：P3 仍然证明了 30B、top-p/routing replay、反向传播、权重同步能工作；**P3 的有限 loss 不能证明 GRPO 组归一化语义正确**。S2-0b 必须新增问题 E（层次化优势归一化），验收不变量：

1. 同一 prompt group 内，先按唯一 rollout execution 计算 reward/advantage；
2. 一个 rollout 的 fan-out branch 数变化，不得改变其他 rollout 的 advantage；
3. 同一 rollout 的 advantage 可广播给它的 branches；
4. branch 对 loss 的总贡献按 rollout 级分母聚合，不能随 branch 数放大；
5. 缺员 prompt group 首训默认整组补采或整组拒绝，不做隐式可变 n 的 GRPO。

### 一般问题

- **"统一展平为 list[Sample]"边界不精确**：slime rollout 层原生就是 `list[list[Sample]]`（外层 = prompt group），train converter 才消费平铺。过早全局展平丢 prompt group 边界；不处理 branch 列表又成三层嵌套。应明确三个视图：RepoHarness 内部权威结构（PromptGroup → RolloutExecution → Branch）；slime rollout/filter 视图（保留 PromptGroup，组内展开 execution/branch + 显式身份 sidecar）；slime train converter 视图（平铺 + group_index/rollout_id/branch_id 无损回链）。若坚持不改 slime 源码，需要自己的 rollout-function-path 或统一 fan-out adapter——仅改 custom_generate 返回值覆盖不了 stock rollout 的 `len(group)==n_samples_per_prompt` 假设。
- **batch admission 结果不应写进 TrajectoryProjection 或 EligibilityReport**：`backend_rejection_reason` 属于 `BackendHandshake`（`contracts/handshake.py`），且契约注释明言"可训练性唯一权威是 EligibilityReport，accepted 不构成资格背书"。一条轨迹可能语义完全合格、只是当前批次装箱失败，不应因此改 eligibility。建议新增批次级 `BatchAdmissionReport`，各条 BackendHandshake 引用它；rejection reason 扩充：insufficient_rollout_count / microbatch_alignment_failed / prompt_group_incomplete / capacity_backpressure。
- **修复策略顺序要改写**：不能先 fail-closed（先拒绝就没有 repair 了）。正确顺序：预检 → 按配置尝试（延迟聚合 / 同 prompt 补采 / 完整组选择）→ 重新预检 → 仍不合法才 fail-closed。另外组级子集选择不能解决 A 类（19<32）——它只能减样本；A 类只能靠跨波次等待、降到预注册的更小 batch 目标、或补采完整 prompt group。
- **离线测试应加与 slime 真 `build_dp_schedule` 的差分验证**：同一输入同时喂 RepoHarness 预测器和 slime 的真实纯 Python 函数，要求成功/失败类别、step 数、microbatch 数一致。

### 文档问题

- S2-6 正文仍保留不可执行的旧验收（60+65 条），与 G8 冲突——开工版本不应同时保留两套标准。
- S2 计划引用了被 .gitignore 忽略的 `tmp/codx_adv.md`，新 clone 不可复现。【本文件即修复】
- AGENTS.md 阶段一览仍有一处"待检查点 2 确认"；状态文档快照日期未更新；状态文档末尾多空行。

### 验证结果（codex 本机复跑）

```text
inspect-rh2-s1                         PASS
inspect-rh2-s1 --run-contract-tests    303 passed
uv run pytest -q                       647 passed
```


---

## 轮次 3（2026-07-12：对 05-fully-async-execution-plan.md 的开工前审查 → 12 条全部采纳，编号 codex #1~#12）

> 原文全文转录如下（tmp/codex_adv_async.md，gitignore 不入库故迁此）。处置：#1~#4（proxy 内部重生成 / TrainingRuntimeCoordinator 跨进程协议 / DIS 准入分层 / batch lease+ACK）已写回 05 计划 D-FA-3、FA-0 3b/3c、FA-1、FA-3、FA-4；#5~#11（多版本 schema、present+eligibility 引用、DIS 对拍清单+ε 区间、训练进度权威、双 TTL+资源分类限额、训后周期 checkpoint 评测、microcompact 警示）逐条落对应任务；#12 账目残留当轮修复。

**总判定**

整体方向正确，我同意继续采用：

- `version-aware fully async + faithful DIS`
- 首版不做成员补采
- 权重更新 abort 采用 proxy 级 turn 重生成
- 训练期间不评测，只做 before/after
- FA 与 S2 独立并行

但当前计划还不适合不加修改地全面开工。至少有四个正确性问题应先写回 FA-0/FA-1，否则容易实现出“看似完全异步、实际无法可靠恢复或准入”的链路。

**执行前阻塞问题**

1. **Proxy 重生成不应依赖 Claude Code 自己重试**

计划一边规定 proxy 是唯一重试执行点，一边写成“proxy 返回错误 → Claude Code 原生重试”，两者矛盾，见 [05-fully-async-execution-plan.md:17](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/05-fully-async-execution-plan.md:17) 和 [同文档:50](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/05-fully-async-execution-plan.md:50)。

当前 slime adapter 会等待 `/generate` 返回完整 JSON 后，才向 Claude Code 伪装成 SSE 流发送结果，见 [common.py:344](/Users/roger/Desktop/claude-code-verl-stage0h/reference/slime/slime/agent/adapters/common.py:344) 和 [anthropic.py:211](/Users/roger/Desktop/claude-code-verl-stage0h/reference/slime/slime/agent/adapters/anthropic.py:211)。所以 non-delivered 保证来自“完整响应缓冲”，不是“逐 token 捕获”。

建议定为：

```text
同一个 Claude Code HTTP 请求
  -> proxy 发起 model_call_attempt_1
  -> 识别更新窗口 abort，丢弃未交付 attempt
  -> 等待引擎 ACTIVE 且版本前进
  -> proxy 内部发起 model_call_attempt_2
  -> 只把最终成功响应交付 Claude Code
```

这样不依赖黑盒 SDK 重试，也不会重复消耗当前在生成前递增的 turn cap。必须新增 `logical_turn_id / model_call_attempt_id / delivery_status`，并处理 SGLang 以正常 JSON 返回 `finish_reason=abort` 的情况，而不只是网络异常。

2. **`TrainingRuntimeCoordinator` 目前只有名字，没有跨进程协议**

计划说 proxy 与协调器“共享更新窗口开始/结束事件即可”，见 [执行计划:62](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/05-fully-async-execution-plan.md:62)。但权重更新、RolloutManager、proxy 和 trainer 位于不同 Ray actor/线程，不能依赖普通内存事件。

FA-0 应定义显式协议：

```text
update_epoch
phase = ACTIVE / PAUSING / UPDATING / RESUMING
old_version / target_version / active_version
window_started_at / window_completed_at
fencing_token
```

Proxy 只有在失败与已知更新窗口重叠、响应未交付、恢复后版本满足预期时，才能内部重生成。否则必须按不可归因故障处理。

3. **DIS 有效 token 比例无法在 ready queue 阶段计算**

计划要求 DIS 有效 token 比例超限时“不进 ready queue / TrainBatch”，见 [执行计划:95](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/05-fully-async-execution-plan.md:95)。但 DIS ratio 需要当前训练模型的 logprob，通常到 trainer forward 才能得到。BatchAssembler 此时只有 rollout logprob、token 和版本事实。

建议首版明确分层：

```text
ready queue 准入：
  provenance、完整组、版本跨度、current-version staleness

trainer forward：
  计算 current logprob、faithful DIS ratio、token mask

训练决定：
  正常反向传播，或在全局有效 token 为 0 时跳过整个 optimizer step
```

`90%` 首版应作为监控和黄灯阈值，不应直接成为 ready queue 硬门。若以后坚持按它换 batch，需要新增“两阶段 logprob 预检”或“forward 后取消并重新取 batch”的 trainer 协议，复杂度明显更高。

4. **Batch 消费缺少 lease 和 trainer acknowledgement**

计划只写 `peek → preflight → consume`，见 [执行计划:83](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/05-fully-async-execution-plan.md:83)。这无法处理 trainer 崩溃：

- 提交前删除会丢 batch。
- 训练完成后删除又可能在重启后重复训练。
- Ray future 成功不等于 checkpoint 与队列状态已经原子提交。

至少需要：

```text
READY
  -> RESERVED(batch_lease_id, expires_at)
  -> SUBMITTED(optimizer_step_id)
  -> TRAINED
  -> ACKED / RELEASED
```

恢复语义也要定案：建议采用 at-least-once 提交，加 `batch_id + optimizer_step_id` 去重；不要声称实现严格 exactly-once，除非队列账本与 trainer checkpoint 能原子提交。

**其他重要修正**

5. `RolloutAttemptOutcome.behavior_policy_version` 不能是单值。一个 execution 可以跨多个版本。应保存逐 turn 引用或版本序列，并分别派生：

```text
intra_execution_version_span
current_version_at_finalize
current_version_at_consume
worst_token_lag
```

现有 `BackendHandshake.policy_version` 也是单值，见 [handshake.py:96](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/contracts/handshake.py:96)，FA-0 应升级 schema，不能把多版本事实压回单值。

6. `present_trainable` 会复制 `EligibilityReport` 的权威结论。Outcome 应记录 `present`，并引用 `eligibility_report_id`；在线训练资格仍只能由 EligibilityReport 决定。

7. Faithful DIS 验收不能只对拍 forward loss。还要固定：

- loss 正负号；
- importance ratio 是否 `detach`；
- 越界 token 的梯度是否精确为零；
- denominator 是否包含被拒 token；
- top-p replay 是否参与 current logprob；
- DP/CP/VPP 下归约是否一致；
- 每个 token 的梯度与手算结果是否一致。

论文 coding-agent 参数是 `epsilon_low=0.8`、`epsilon_high=3.0`，不是模糊的“论文默认”。计划应写明初始区间及来源。

8. 完全异步后，slime 的名义 epoch 和学习率调度会漂移。当前 `train_iters` 按名义 rollout 数推导，而数据源会为 reserve/rejected groups 继续推进。应以已确认 optimizer step、已消费 RolloutExecution 或有效 token 为训练进度权威，同时分别记录 attempted/trained prompt coverage。

9. `ready queue TTL` 不能只按版本。若 trainer 停住且权重不更新，版本 TTL 永远不会过期。应同时有：

```text
policy_version_ttl
wall_clock_ttl
```

并分别限制 active sandbox、模型调用、评分容器、pending groups 和 ready groups，不能只设一个全局并发池。

10. 同意“训中不评”，但建议训练结束后依次评测保留的周期 checkpoint，而不只是最终 checkpoint。否则无法判断中途能力峰值或后期退化。

11. `DISABLE_COMPACT=1` 主要关闭 auto/manual compact；Claude Code 的 microcompact/context-collapse 是其他路径。计划已有“上下文收缩即拒绝”的兜底，这条必须保留，不能只凭环境变量宣布 compaction 已关闭。

12. 文档声称 reward/K 已全仓清理，但正式实验设计仍有旧表述；[repoharness_validation_experiment_design.md:469](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/training_design/repoharness_validation_experiment_design.md:469) 尚未修正。项目状态文档也还有一处把遗留任务写成 S2-0b，属于低风险账目问题。

**可以保持不变的部分**

FA/S2 分离、完整 PromptGroup 才进 ready queue、branch 不计作 rollout、reward 整体广播配 rollout 级分母、`build_dp_schedule` 差分验证、禁用 `--release-train`、不做成员补采、FA-5 与 S2 共用租卡窗口，这些设计都合理。

我的建议是先让 Claude 把前四项写回计划，再开 FA-0。FA-3 的纯 Python schedule 差分测试可以提前并行；FA-4 可以先做公式和梯度级小张量测试，但在 DIS 时序与 denominator 定案前，不应开始最终 custom loss 接线。本轮我只做了审阅，没有修改文件。


---

## 轮次 4（2026-07-12：FA-0 实现审查 → 12 项全部采纳，follow-up 随 commit 落地）

> 原文全文转录（tmp/FA-0_codex.md，gitignore 不入库故迁此）。处置见 `fa/implementation-notes.md` 的 "FA-0 follow-up" 节：严重 1（staleness clamp 掩盖矛盾 → fail-closed + provider 注入点）、严重 2（session 级收缩误杀子 agent → 叶链级硬拒绝 + session 级 audit-only）、严重 3（RuntimeFailureCategory 13 值独立枚举）+ 一般/测试项逐条修复；测试 684 → 692。

**结论**

FA-0 的总体设计正确，不需要推翻；三层身份和逐 turn 版本事实值得保留。但目前还不能把它视为正式链契约已经完全闭合。存在 3 个进入 FA-1 前应修复的问题，以及若干契约和测试缺口。

FA-3 离线调度预检、FA-4 合成张量对拍可以继续并行；FA-1 真实异步接线最好等下面前三项修完。

**严重问题**

1. **finalize 当前版本仍是静态配置，不是真实运行时版本**

[generate.py:1258](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/adapters/slime/generate.py:1258) 只检查 `config.policy_version` 是数字；[generate.py:1737](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/adapters/slime/generate.py:1737) 又直接拿它计算 staleness，没有在 finalize 调用 `engine.get_weight_version`。

我构造了反例：

```text
config current version = 3
turn weight_versions = [5]
结果 staleness_steps = 0
staleness_within_threshold = true
```

这实际上是事实矛盾，却被判定为健康。修复建议：

- 注入 `CurrentPolicyVersionProvider`，在 finalize/消费时读取真实版本。
- `seen_version > current_version` 必须 fail-closed，不能 `max(..., 0)`。
- 区分 `current_version_at_finalize` 和 FA-3 的 `current_version_at_consume`。
- 在实时 provider 接入前，不应把当前 handshake 称为“真实 staleness”。

2. **上下文收缩检测会误杀 Claude Code 子 agent 或合法分叉**

[generate.py:591](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/adapters/slime/generate.py:591) 把同一 session 的所有 turn 按序排列，和全局最大 prompt 长度比较。

但 Claude Code 的所有请求共享同一个 `ANTHROPIC_AUTH_TOKEN=session_id`，见 [claude_code.py:62](/Users/roger/Desktop/claude-code-verl-stage0h/reference/slime/slime/agent/harness/claude_code.py:62)；Anthropic adapter 又直接用该 token 作为 session id，见 [anthropic.py:192](/Users/roger/Desktop/claude-code-verl-stage0h/reference/slime/slime/agent/adapters/anthropic.py:192)。因此子 agent 启动较短上下文时，很可能被误判为 compaction。

建议：

- 检测必须按逻辑会话 lineage/消息图分支执行，不能跨 branch 比较。
- 在没有 lineage 信息前，token 数骤降只能作为 audit 信号，不宜作为正式硬拒绝。
- 真正的硬规则先依赖 `DISABLE_COMPACT=1` 验真和明确 compaction hook/event。
- 增加“主 agent 长上下文后启动短上下文子 agent，不得拒绝”的负测试。

3. **执行故障错误复用了评分故障枚举**

[fa_runtime.py:133](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/contracts/fa_runtime.py:133) 使用 `GradingFailureCategory`，但它只有四种评分结果，见 [grading.py:36](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/contracts/grading.py:36)。

它无法表达：

- model proxy 或 inference 服务失败
- sandbox/harness/worker 崩溃
- capture、token alignment、staleness 失败
- security、anti-cheat、身份冲突

这会让 FA-2 的组终结、重试和熔断无法可靠决策。应新增独立的 `RuntimeFailureCategory`，评分失败作为其中一个来源或 evidence ref，而不是让评分枚举统治整个 rollout 生命周期。

**一般问题**

- `present` 没有强制 `current_version_at_finalize`，与字段说明冲突，见 [fa_runtime.py:178](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/contracts/fa_runtime.py:178)。
- `TrainingRuntimeWindow` 允许 `old_version == target_version` 后宣布 `ACTIVE`，并未真正保证版本前进，见 [fa_runtime.py:250](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/contracts/fa_runtime.py:250)。
- `ModelCallAttempt(delivered)` 没有强制 `weight_version`，见 [fa_runtime.py:309](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/contracts/fa_runtime.py:309)。
- abort attempt 只记录 `update_epoch`，没有回链具体窗口或 `fencing_token`，不足以证明它确实与最新更新窗口重叠。
- `context_shrink_ratio` 没有范围和有限数校验；`0` 会彻底关闭检测，`>1` 会误报正常等长 prompt。
- `require_real_weight_versions=True` 并不会强制 `reject_context_shrink=True`，所谓“正式配置必须开启”目前只是注释。
- 非正式路径确实允许真实版本与 fallback 混合，例如 `["3", "wv_fallback"]`；这与代码注释和 commit 中“不拼混合序列”的表述不一致。

**测试问题**

[test_fully_async_surface.py:21](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/tests/contract_slime_async/test_fully_async_surface.py:21) 在 `reference/slime` 不存在时整文件跳过。该仓库目前未被父仓库追踪，干净 clone 中这 7 条关键 pin 很可能全部 skip，而且没有检查 HEAD 必须为 `e848052a`。

建议未来 `inspect-rh2-fa`：

- 缺少 slime 源码时 fail，而不是 skip。
- 验证精确 commit/digest。
- 源码正则只作为补充，FA-5 再做真实行为测试。

此外，[test_slime_generate.py:1528](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/tests/adapters/test_slime_generate.py:1528) 名称声称测试“轨迹收口为 abort”，实际只直接调用了检测函数，没有运行 orchestrator，也没有断言 `remove_sample=True`。

**可以保持不变**

三层身份、eligibility 单一权威、消费时版本事实不回写 finalize 记录、non-delivered attempt 不进入 capture 训练面、逐 turn `weight_version` 透传、`routed_experts_start_len` 非零 fail-closed，这些设计都合理。

验证结果：

```text
聚焦测试：81 passed
全套测试：684 passed
inspect-rh2-s1：PASS
```

因此 S1 没有回归。建议把上述问题做成一个很小的 `FA-0 follow-up`，修完再进入 FA-1；FA-3 离线部分与 FA-4 数学对拍不必等待。没有修改任何文件。
