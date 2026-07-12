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


---

## 轮次 4（2026-07-12：对 s2/s2_1_data_ingestion_execution_plan.md 的开工前审查 → 全部采纳）

> 用户转达，原文要点转录。处置：4 个硬阻塞全部核实成立并修入执行文档（§1/§2/§3.0/§3.1/§4）；四门规格修正（硬门=empty/golden/determinism，假阳性降为 probe 层四态结果）；执行完整性 8 项全部采纳；O-1 改判不并入、O-2 改判 50/216 同实例、O-3 N=3 双门、O-4 probe 化。

### 硬阻塞（4 项，均经源码核实）

1. **冻结元数据缺四门所需字段**：`meta/swe_gym_lite.jsonl` 只有 8 列（instance_id/repo/base_commit/version/problem_statement/hints_text/F2P/P2P），缺 patch/test_patch/created_at——既不能构造 BundlePair 也不能跑 golden 门。改为：按冻结 revision 重抓完整 11 列 → 不可变 raw archive + digest → 全字段 strip_spec fail-closed；裁剪版 meta 不作字段覆盖验证依据。
2. **镜像清单无法提供稳定身份**：`image_refs_swegym.txt` 是 Full 2438 条无键 `:latest` 列表、无 manifest digest，而 `PublicTaskBundle` 强制 `image_manifest_digest`。改为：生成键控解析清单（instance_id/source_image_ref/resolved_manifest_digest/resolved_at/platform/registry_evidence_ref），运行期按 digest 拉取比对；`_s_` 规则只作映射校验。
3. **validation_only 与 grader_only 归属冲突**：`PrivateGradingBundle.v1` 强制含 `golden_patch`（bundles.py:152），违反 strip_spec:24 的 validation_only 归属。改为 v2 三分体系（PublicTaskBundle 复用 / PrivateGradingBundleV2 无 golden / ValidationOnlyBundle 持 golden+mutation fixtures / EnvironmentPackage digest 关联）；冻结 v1 不改，"只加构造器不改 schema"的原表述不成立。
4. **grader 缺受控 patch 入口**：`grade()` 只从 agent workspace 导出 patch（manager.py:356 WorkspaceRunner）。新增 `grade_controlled_patch(patch_bytes, patch_origin, patch_digest, validation_run_id)` 与原入口共用 image check/clean checkout/apply/eval/parser；不为四门伪造 workspace。

### 四门修正

- empty 门前提 = 测试真实运行且 parser 成功解析 + ≥1 F2P 失败；infra_failure/patch_apply_failed 不算门正确失败。
- golden 门 = 全部 F2P 通过 ∧ P2P 零失败（RESOLVED_FULL），不只是 F2P>0。
- 3a 的 /tmp 文件不构成 repo patch → 改仓库内可 clean-apply 的无关文件变更。
- 3b 删末 hunk 不保证是错误解（可能是冗余清理）→ 改名 mutation probe，四态（rejected/suspicious_pass/fixture_invalid/infra_failure），suspicious_pass 人工复核不自动剔题。
- 8 题基线只硬要求 empty/golden/determinism；probe 验证 runner 诚实分类。
- 确定性 = empty 与 golden 各 N=3、全新容器、比较语义 verdict + F2P/P2P 集合（不比日志文本）。

### 执行完整性（全部采纳）

50 题按 repo/golden hunk 数/F2P、P2P 规模分层 + 固定 seed（不取前 50）；幂等键 (instance_id, gate, fixture_digest, image_digest, validator_config_digest, attempt)；原子写 + 断点续跑；只重试 infra failure；日志 digest 必须对应留存 artifact；EnvValidationReport 用五态枚举非布尔；provenance 全量（source revision/三 bundle digest/image digest/swebench+parser 版本/runtime fingerprint/validator config digest）；新建 s2_1 manifest 回链 v0.1（不向冻结 manifest 追加）；新 schema 注册 EXTRA_SCHEMA_REGISTRY 扩展面（S1 核心 15 契约冻结不动）。

### O-1~O-4 定案

- O-1 **不并入** held-out（542 中 450 题是 R2E：需另一套 ingestion、parent 断言实战、scaleswe grader；并入 = 216→758 题 / 4500+ 次评分，成本失效）。S2-1 只保证 runner 可复用；静态门打标（无 docker）任意线程可先行。
- O-2 T0~T3 本机；**T4 50 题与 T5 216 同一 x86 实例**（不得 ARM 校准后换 x86 判题）。
- O-3 N=3，empty/golden 各 3 次。
- O-4 3a 保留为控制探针，3b 非强制 mutation probe + 人工复核。

### 保持项

T0 冻结账本自检、D5 代码级重验、leakage_watch 透传、先 8 题再 50 题再全量、逐题报告与漏斗账、S2/FA 文件边界。


---

## 轮次 5（2026-07-12：FA-3 离线 / FA-4 对拍实现审查 → 12 项全部采纳）

> 原文全文转录（tmp/FA3/4_codex.md）。处置见 `fa/implementation-notes.md` "FA-3/FA-4 follow-up" 节。最重要裁决：DIS 信任区间按论文式 3 原文核实为 (1−ε_ℓ, 1+ε_h) 开区间 = (0.2, 4.0)——轮次 3 的"直接 ratio 边界"读法与我方闭区间实现均错误，已修正。codex 附加验证：5000 例随机调度差分全部一致。

**结论**

两个提交的核心方向正确，但目前更准确的状态应是：

- FA-3：**调度镜像原型完成，正式队列接线前仍需加固**
- FA-4：**标量 DIS 参考原型完成，尚未达到论文忠实和分布式训练验收**

没有必要推翻实现。FA-1 的 worker/proxy 工作可以继续，但不要直接把当前 FA-3 接入 lease/ACK，也不要基于当前 FA-4 开始正式 custom loss 接线。

**严重问题**

1. **FA-4 的 DIS 阈值与论文原文不一致**

[faithful_dis.py:12](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/training/faithful_dis.py:12) 实现 `[0.8, 3.0]` 闭区间。

但 SAO 论文公式 3 是：

```text
1 - eps_low < ratio < 1 + eps_high
```

coding 配置给出 `eps_low=0.8, eps_high=3.0`，按字面应为 `(0.2, 4.0)` 开区间。当前测试还把闭区间钉成正确行为，见 [test_faithful_dis.py:171](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/tests/training/test_faithful_dis.py:171)。

必须在接线前定案：

- 按论文原文实现 `(0.2, 4.0)`；或
- 若有作者代码证明参数是直接 ratio bounds，则保留 `[0.8,3.0]`，但明确称 RH2 变体，暂时不能叫 faithful DIS。

2. **FA-3 `ok` 没有说明实际选择和延后了哪些 execution**

[batch_admission.py:189](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/adapters/slime/batch_admission.py:189) 整除得到 step 数，尾部 execution 被忽略。比如 25 个 execution、`gbs=20` 返回 `ok`，但结果没有说明后 5 个未训练。

这不能支撑异步队列的 lease/ACK。建议：

- 首版一个 lease 严格只取一个完整 step；或
- 返回 `selected_execution_ids`、`deferred_execution_ids` 及对应 sample positions。
- ACK 只确认 selected，deferred 必须回到 READY，不能记成丢弃。

3. **FA-3 没有使用 FA-0 的稳定 PromptGroup 身份**

[BranchDelivery](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/adapters/slime/batch_admission.py:267) 只有 `group_index`，没有 `prompt_group_id`；归一化也按整数 `group_index` 分组。

多个 worker、数据源重启或回放时，`group_index` 可能复用。应携带完整 `ExecutionIdentity`，以 `prompt_group_id` 为 GRPO 权威键，`group_index` 只作为 slime 本批次编号。同时拒绝重复的 `(prompt_group_id, rollout_execution_id, branch_id)`。

4. **FA-4 没有实现 execution 级归约层次**

[faithful_dis_loss](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/training/faithful_dis.py:78) 把传入 token 全部除以单一分母，没有 execution/branch 身份，也不消费 FA-3 产生的 rollout denominator。

因此尚未证明：

```text
branch numerator
-> RolloutExecution 共享 denominator
-> batch execution mean
-> DP/CP/microbatch 归约
```

需要补 branch split、fan-out 数量变化、DP partition invariance 测试，并让参考层显式接收 execution 分区或 `rollout_mask_sums`。

5. **torch 对拍的全零路径会产生 NaN**

[test_faithful_dis.py:125](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/tests/training/test_faithful_dis.py:125) 直接除以 `mask.sum()`。我实测全 mask=0 时 loss 和梯度均为 NaN；现有“无 NaN”测试只测 Python 标量实现。

正式实现必须全局归约 numerator/denominator，只有全局有效 token 为零才跳 step；局部空 CP rank 仍需返回连接 logits 的可微零，避免 collective/backward 死锁。

**重要遗漏**

- top-p replay 没有进入对拍；测试从预先给定的 `logp_current` 开始。
- 没有跨版本双 turn 场景。
- 没有 DP/CP/VPP 归约测试。
- 没有“正式配置禁用 DIS 必须启动失败”的负测试。
- FA-3 真 slime 差分在 `reference/slime` 不存在时全部 skip，而且该目录未被父仓库追踪。正式 FA inspector 必须验证源码存在及 HEAD/digest。
- 随机差分只验证“两边都失败”，没有真正比较失败类别；也没有比较 selected/deferred sample 集合。
- P3 分母回归使用 `response_lengths`，正式分母应来自 `loss_mask` 中的 1 数量。

**输入校验**

边界探针确认当前会接受：

- `NaN reward`，产生 NaN advantage；
- `NaN advantage`，产生 NaN DIS loss；
- 重复 branch，重复累计 denominator；
- execution 总 trainable token 为 0；
- 负 `max_tokens_per_gpu`；
- 非法并行配置可能直接 `ZeroDivisionError`。

另外，有限 logprob 差也可能让 `math.exp` 溢出。应在 log-ratio 空间先判断阈值，只对已确认在区间内的值执行 `exp`。

**可保留的优点**

FA-3 的调度镜像本身质量很好：我额外做了 **5000 组随机受支持参数差分**，与真实 `build_dp_schedule` 的准入和 microbatch 数全部一致。execution 级 reward 广播与 branch 共享分母方向也正确。

FA-4 的 loss 符号、detach 后解析梯度、越界 token 零梯度、provenance mask 不变等标量语义是自洽的。只是 detach 应记录为明确算法决策，因为论文没有显式写 stop-gradient。

验证结果：

```text
聚焦测试：32 passed
全套测试：724 passed
inspect-rh2-s1：PASS
5000 例额外调度差分：全部一致
```

建议先做两个小型 follow-up：`FA-3 hardening` 与 `FA-4 formula/reducer correction`。FA-1 可以并行推进，但 FA-2/FA-3 队列接线必须等前者，custom loss 接线必须等后者。没有修改文件。


---

## 轮次 5（2026-07-12：T0 验收审查 → T0 可验收、T1 解锁；一个实质遗漏 + 三条证据工程建议）

- **实质遗漏（已在 T1a 修复为正式断言）**：`assert_repo_disjoint.py` 先 `train_pool = (swe_gym | r2e) - heldout` 再查 `train_pool ∩ heldout`，数学上必空——不构成"216 survivor 不含 held-out 题"的证明。codex 独立补跑真实关联检查（216 唯一、join 全中、held-out 命中 0，PASS）；正式机器断言 = survivors → join Lite by instance_id → repo ∩ {hydra,bokeh,tornado,pyramid} == ∅，已实现于 `rh2/experiments/s2_1_ingestion/fetch_raw_lite.py` 第 4 步，T0 报告已补注。
- **证据工程建议（登记 S2-8/T2）**：① inspector 只读重算，不原地重写被检 evidence；② T0 收编为机器可重算项（manifest 自 digest / 24 项通过数 / 脚本 digest / survivor 级 D5 / 报告前后 digest）；③ 正式数据身份用规范化完整 repo identity，不用 basename。
- **codex 独立验证**：脚本运行前后 digest 24/24 PASS、报告前后 digest 一致、216 survivor 真实 D5 PASS、inspect-rh2-s1 PASS（22 evidence + 55 code）。结论：T0 结果可信，遗漏并入 T1/T2 正式 checker，不阻塞 T1。


---

## 轮次 6（2026-07-13：T1 验收审查 → 数据产物可信，但 T1 不应完全验收；三个严重问题 + 计划要求未完成）

- **严重 1 续跑 fail-open**：resolver 只按 instance_id 跳过，不校验旧条目；codex 反例（digest 改 "bad" → ALL PASS 216/216；塞 unexpected_extra → ALL PASS 217/216）。【v2 修复：加载即逐条严格校验 + 完成断言 set(entries)==set(survivors)】
- **严重 2 重跑非幂等**：完整文件上重跑把 platform_sample 覆盖为空列表（codex 复现 resume_byte_idempotent=false）。【v2 修复：header 由事实重建含 schema_id，幂等】
- **严重 3 非原子写**：直接覆盖 JSON，中途死亡留损坏文件。【v2 修复：temp+fsync+os.replace】
- **计划要求未交付**：真实 platform（原口径仅命名约定）与 registry_evidence_ref（0/216）。【followup 补齐：manifest GET + config blob 断言 linux/amd64 + evidence jsonl 回链；183/216 后限额停车可续跑】
- **一般**：pyproject 缺 data 依赖声明【已加 data group】；缺 schema_id【v2 已加】；raw archive 覆盖不设防【immutable 守卫 + 原子写】；"当前 sha == pin"未在脚本内实现【已加信息性核对】；(repo,base_commit,F2P) 仍不宜作自动去重主键，应 task_id + duplicate cluster 人工/规则判定【T2 落实，plan 与 notes 已记】。
- **codex 独立确认正确**：raw 230/11 列/一致性、216 映射唯一覆盖、digest 全合法、214 唯一 + 两对共享（题面/F2P/test_patch/gold 均异）、父 manifest 四项 digest 匹配、pytest 749、inspect-rh2-s1 PASS。


---

## 轮次 6（2026-07-13：FA-1 实现审查 → 全项采纳，follow-up 随 commit 落地）

> 原文全文转录（tmp/FA1_codex.md）。处置见 `fa/implementation-notes.md` "FA-1 follow-up" 节：严重 1~6（生产接线薄壳 / sink durable fallback+halt / 生命周期收口 / attempt 全局身份 / capture 两阶段事务 / target_version 校验）+ 遗漏项与测试缺口逐条修复；场景 21 的落点从 orchestrator 修正到 FA 入口（S1 eval 面是 E10 正式定案，不得破坏）。测试 749 → 768。

**结论**

FA-1 的组件设计方向合理，但当前不能判定为“FA-1 完成”。更准确的状态是：

```text
FA-1 本地运行时组件原型完成
FA-1 生产链接线与生命周期闭环未完成
```

建议先做一个 `FA-1 follow-up`。FA-2 可以并行设计纯状态机，但不要冻结 worker→assembler 接口，也不要进入实际接线。

**严重问题**

1. **FA-1 组件目前完全没有进入生产路径**

仓库检索表明 [async_worker.py](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/adapters/slime/async_worker.py) 只被测试引用。当前 glue 没有使用：

- `ContinuousExecutionWorker`
- `ModelCallProxy`
- `ResourceLimits`
- `BoundedDeliveryQueue`
- FA fully-async `rollout-function-path`

[glue.py:404](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/experiments/s1_7a_bringup/glue.py:404) 仍然构造原来的 `RolloutOrchestrator`，只接了 compaction 和两个布尔开关。这与计划 [FA-1 第 1 条](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/05-fully-async-execution-plan.md:51) 不一致。

将整个 slime 薄壳推迟到 FA-5 风险太高：FA-5 应验证真实 GPU 行为，不应第一次发现接口根本没有接通。

2. **worker 的“失败必有账”实际上不成立**

[async_worker.py:539](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/adapters/slime/async_worker.py:539) 先增加 `failed`，然后调用 `failure_sink`；sink 失败后异常被直接吞掉。

结果是：

```text
ledger_balanced() == true
但没有 RolloutAttemptOutcome 或任何持久化失败记录
```

这仍然属于 N1 的“任务静默消失”，只是从 task 层转移到了 failure sink 层。必须有内部 durable fallback；fallback 也失败时应 `run_halt`，不能继续训练。

3. **worker 对取消、task source 故障没有收口**

最小探针已复现：

- 被取消的 execution 使 [task.exception()](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/adapters/slime/async_worker.py:537) 抛 `CancelledError`，worker 本体退出。
- `task_source()` 抛异常会直接终止 worker。
- worker 自身被取消时，没有 `finally` 取消并 await 所有 in-flight task。
- 消费者死亡且交付队列满时，stop 后也会永久等待。

需要明确 shutdown protocol：停止 top-up、给在途任务 deadline、持久化 pending、取消并 drain、最终对账。

4. **ModelCallProxy 的 attempt 身份会跨 rollout 冲突**

[async_worker.py:326](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/adapters/slime/async_worker.py:326) 只用：

```text
logical_turn_id + attempt_number
```

多个并发 rollout 通常都从 `turn_0` 开始。我并发调用两次后得到：

```text
turn_0_a1
turn_0_a1
```

这会覆盖 `audit_artifacts`，也无法唯一回链 capture。attempt id 至少必须包含 `rollout_execution_id/session_id`。

5. **capture 引用不是事务性的，已经出现悬空 evidence**

响应缺 `weight_version` 时，[async_worker.py:342](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/adapters/slime/async_worker.py:342) 生成：

```text
evidence_refs = ["audit:turn_x_a1"]
```

但 `audit_artifacts` 中没有该对象。`capture_record_ref()` 自身抛错时，ledger 和 audit 也都为空。

更根本的问题是：proxy 在真实 capture 成功前就写入 `capture_record_ref`。如果后续 capture 失败，会留下“声称存在但实际不存在”的引用。建议：

```text
proxy 返回 delivered attempt draft
-> capture 持久化成功
-> finalize ModelCallAttempt
```

6. **恢复条件没有验证 abort 窗口的目标版本**

[async_worker.py:441](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/adapters/slime/async_worker.py:441) 只要求恢复版本大于调用开始版本，没有要求达到 `abort_window.target_version`。

我构造了：

```text
调用前 active=3
abort window target=5
恢复窗口 active=4
```

proxy 错误放行并交付版本 4。应验证：

```text
same epoch:
  active_version == abort_window.target_version
later epoch:
  active_version >= abort_window.target_version
  且 epoch/fencing 单调一致
```

**重要遗漏**

- `attempts_ledger` 和 `audit_artifacts` 永久保存在内存，后者还保存完整半截输出。长训练会持续增长。应写 artifact store，只在内存保留引用和有界指标。
- `ResourceLimits` 没有接入 worker、proxy、sandbox 或评分生命周期；目前只是独立 semaphore 类，不能声称五类限额已经生效。
- `max_pending_out` 使用 `>` 而不是 `>=`，且不校验负值，实际积压可超过命名上限。
- `retry_local_operation` 只按操作名重试，不区分异常是否可重试。认证失败、契约冲突、digest mismatch 等永久错误也会重试。需要 `retry_if(exception)` 或 typed retryable error。
- `RetrySpec` 没有校验次数和 delay；`max_attempts=0` 最终得到 `AssertionError("unreachable")`。
- `ModelCallProxy` 没有每 attempt timeout，模型请求永久挂起会长期占用资源。
- glue 对布尔环境变量只认字符串 `"1"`；拼错或写 `"true"` 会静默关闭正式防线，应严格解析并拒绝未知值。
- glue 没有给 `RolloutOrchestrator` 注入 `current_policy_version_provider`。权重更新后仍以启动探针版本作为 current，正式多 step 链会错误拒绝或计算错误 staleness。
- 全局验收场景 21“eval 进入 FA 路径必须 fail-fast”尚未实现。

**测试缺口**

当前 17 条测试没有覆盖：

- execution task cancellation；
- task source / failure sink 持久化失败；
- worker 被取消后的 in-flight 清理；
- 消费者死亡与 shutdown deadline；
- 重复 `logical_turn_id` 的并发调用；
- capture callback 失败与 evidence 存在性；
- coordinator 快照回退、非数值恢复版本、目标版本未达到；
- raw audit 内存上限；
- 五类 `ResourceLimits` 的真实生命周期接线；
- 正式 env 配置解析；
- worker→Outcome→FA-2 assembler 的端到端交付；
- `evaluation=True` fail-fast；
- 真实 slime `_key` 和 rollout-function-path。

**可以保留**

以下实现基础不错：

- 非阻塞 `try_put` + pending 列表的反压方向；
- execution 并发上限；
- abort 响应不交付旧 token；
- 更新风暴重生成上限；
- retry 默认不在白名单就只运行一次；
- S1 行为保持不变。

验证结果：

```text
FA-1 专项：17 passed
rh2 全套：749 passed
inspect-rh2-s1：PASS
```

建议下一步先补 `FA-1 follow-up`，至少关闭生产接线、durable failure ledger、取消/退出语义、全局 attempt identity、capture 事务和窗口 target 校验。FA-2 可同时编写状态机与报告 schema，但暂时不要绑定当前 worker 输出形状。没有修改文件。


---

## 轮次 7（2026-07-13：T1-followup 复审 → 三修复确认正确；新严重缺口 = manifest↔evidence 引用完整性；T1 保持 OPEN 正确）

- **严重 1 引用完整性缺失**：is_enriched 只查非空 ref 字符串；codex 反例——evidence 文件缺失 → ALL PASS 且自动写出空 evidence；digest 全改错 → ALL PASS 保留错误 evidence。真实 183 条经其独立交叉核对为 0 mismatch，漏洞影响续跑/恢复/防篡改。【v3 修复：enriched = 形状 ∧ evidence 存在 ∧ 逐字段交叉 ∧ 无多余/重复】
- **严重 2 双文件非事务**：先 manifest 后 evidence，两次 replace 之间死亡 → "声称 enriched 但 evidence 未写"且会被接受。【v3 修复：evidence 先写 → digest+行数入 header → manifest 最后为提交记录；load 重算 evidence digest；崩溃唯一方向（evidence 超前）按提交记录恢复】
- **严重 3 evidence_ref 路径错**：写 `image_registry_evidence.jsonl#id` 但文件在 `raw/` 下。【v3 修复：`raw/image_registry_evidence.jsonl#imgev-<id>` + 稳定 evidence_id】
- **应补测试**：七类无网络场景。【已补：tests/taskset/test_image_manifest_store.py，13 项】
- **一般**：报告顶行"全 PASS"与 OPEN 矛盾【已改"T1a PASS；T1b 184/216，T1 未验收"】；config blob 内容哈希未验【v3 下载原始字节重算 == config_digest 并入 evidence】；evidence 加 schema/version + evidence_id【已加】。
- **codex 独立确认**：三个旧修复正确、183 条 entry/evidence 零 mismatch、草稿账本 5 项 digest 正确、768 passed、inspect-rh2-s1 PASS。


---

## 轮次 7（2026-07-13：FA-1 第二轮审查（生产接线与 CC HTTP 边界）→ 五 P0 全部采纳）

> 原文全文转录（tmp/FA1_codex.md 第二版）。处置见 `fa/implementation-notes.md` "FA-1 follow-up 2"：同步入口 + 真 call_rollout_fn 契约测试 / glue ensure_fa_started + sampling params / 持久化 service 零丢失 / proxy 接入 capture wire + SessionPoisonRegistry + episode deadline + 发前 ACTIVE 等待 / provider 权威化（engine /get_weight_version + registry 交叉检查）。含 codex 本机 CC 2.1.205 重试实测数据（留档供 FA-5 复测）。测试 768 → 797。

**结论**

当前不能把 FA-1 判定为真正完成。基础组件质量已经明显改善，但生产入口和 Claude Code HTTP 边界仍有四个阻塞问题。其中两个会让 FA-5 真机启动直接失败，另一个会导致预取 rollout 静默丢失。

**严重问题**

1. **P0：rollout 入口与 slime 的同步接口不兼容。**

新入口是 `async def`：[rollout_entry.py:305](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/experiments/fa_bringup/rollout_entry.py:305)，但 slime 的 `call_rollout_fn()` 是同步调用，不会 `await`：[base_types.py:19](/Users/roger/Desktop/claude-code-verl-stage0h/reference/slime/slime/rollout/base_types.py:19)。

我用 slime 真实 `call_rollout_fn` 做了探针，结果是：

```text
rollout_fn_samples_type=coroutine
is_coro=True
```

需要提供同步外壳，例如：

```python
def generate_rollout(...):
    return run(_generate_rollout_async(...))
```

并使用 slime 真实 `call_rollout_fn` 写接口契约测试。

2. **P0：新入口启动时拿不到 orchestrator 和 sampling params。**

`_build_service()` 要求 `args.rh2_orchestrator` 和 `args.rh2_sampling_params` 已存在：[rollout_entry.py:268](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/experiments/fa_bringup/rollout_entry.py:268)。

但 orchestrator 目前只在旧 `custom_generate` 第一次执行时才挂载：[glue.py:693](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/experiments/s1_7a_bringup/glue.py:693)，而新入口绕过了这一步。仓库中也没有任何代码写入 `rh2_sampling_params`。因此修完同步接口后，真实启动仍会立即 fail-fast。

3. **P0：当前生产薄壳并不 fully async，而且会丢预取结果。**

`collect_batch()` 每次调用都新建 worker、queue 和 collector，收够当前 batch 后立即停止 worker：[rollout_entry.py:194](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/experiments/fa_bringup/rollout_entry.py:194)。它没有跨 optimizer step 保温。

更严重的是，worker 已经投进局部 queue、但尚未被当前 batch 消费的结果会随函数返回而消失。我构造了 `rollout_batch_size=1, concurrency=8` 的探针：

```text
returned_groups=1
executed_members=16
source_remaining=4
```

即返回 1 个组，却已经执行 16 个成员，其余结果没有进入下一批，也没有 abandoned 账目。

正确形态是让 worker、delivery queue、PromptGroupAssembler 和 ready queue 都由持久 `FaRolloutService` 拥有；`collect_batch()` 只从 ready queue 取批次，不停止 worker。这个修复适合与 FA-2 一起完成。

4. **P0：ModelCallProxy 仍未接入真实 Claude Code HTTP 请求链。**

`ModelCallProxy` 目前只有单元测试引用。真实 capture wire 仍直接调用 SGLang：[capture_wire.py:102](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/experiments/s1_7a_bringup/capture_wire.py:102)。

因此以下能力当前都没有在生产路径生效：

- 同一个 Claude Code HTTP 请求内透明重生成。
- 不可归因故障后终止 execution。
- session poison 和后续请求拒绝。
- episode 剩余 deadline 传播。
- 发送前等待 coordinator 回到 `ACTIVE`。
- cancellation 与 `RolloutAttemptOutcome` 的完整对账。

`ModelCallProxy.call()` 现在会在读取窗口后立即发送请求，即使窗口处于 `UPDATING`：[async_worker.py:454](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/adapters/slime/async_worker.py:454)。等待更新又使用独立固定 60 秒 deadline：[async_worker.py:579](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/adapters/slime/async_worker.py:579)。

5. **P0：`current_policy_version_provider` 不是 current version。**

当前实现取“历史 capture 响应报告过的最大版本”：[glue.py:427](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/experiments/s1_7a_bringup/glue.py:427)。

如果 trainer 已更新到版本 8，但更新后还没有成功响应，registry 最大值仍可能是 7。系统就会把陈旧轨迹错误计算成 `lag=0`。正式链必须使用 TrainingRuntimeCoordinator 或 `engine.get_weight_version()` 的权威版本，capture 最大值只能做交叉检查。

**一般问题**

- Audit FIFO 淘汰会制造悬空 `evidence_refs`：[async_worker.py:429](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/adapters/slime/async_worker.py:429)。我的探针确认第一条 `audit:` 引用在下一条失败后已经不可解析。外部 artifact sink 成功时应直接返回持久引用，不能继续引用会被淘汰的内存键。
- `unfinalized_deliveries` 没有 abandon/fail 接口。响应 flush、capture commit 或客户端连接中断时，需要显式关闭 draft。
- 失败的 interim group 没有从 `_buckets` 删除：[rollout_entry.py:99](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/experiments/fa_bringup/rollout_entry.py:99)。探针创建 1000 个失败组后，`open_group_count` 仍为 1000。
- “dead consumer” 测试在 worker 启动前就设置了 stop，实际 `dispatched=0`，属于空验证：[test_async_worker.py:593](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/tests/adapters/test_async_worker.py:593)。
- `ResourceLimits` 虽已接入类，但生产 `_build_service()` 没有构造或传入 limits，真实路径仍不生效。

**Claude Code 重试**

另一个线程的分析是正确的，而且当前尚未处理完成。

Claude Code 自己有重试机制并不意味着无法控制，因为我们控制它访问的 adapter endpoint。首版最稳妥的设计是：

```text
可归因的更新窗口 abort
-> proxy 在同一个 HTTP handler 内部重生成
-> Claude Code 只收到一次成功响应

不可归因故障
-> 原子地把 session 标为 POISONED
-> 通知 orchestrator 终止当前 execution
-> 后续所有 Claude Code 自动重试均被拒绝
-> 当前 execution 记为 missing_after_local_retry
```

仅做 `logical_turn_id` 去重不够，因为 Claude Code 重试时可能轻微修改请求。execution 已经判为缺员后，直接 poison 整个 session 更清楚。

现有底层取消链有一部分是正确的：aiohttp 开启了 `handler_cancellation=True`，capture wire 捕获 `CancelledError` 后会调用 SGLang `/abort_request`。但还需要把取消写入 attempt/outcome 账目，并触发 session poison 和 execution 停止。

FA-5 应负责测量真实 Claude Code 的重试次数、退避和超时，不应负责第一次发现这些防线还没有实现。

先在本地测了一次claude code cli:
codex:
会。**如果 proxy 在同一个 HTTP 请求内等待或重生成时间过长，Claude Code 最终可能先触发客户端超时，取消当前请求，然后按自己的策略重试或退出进程。**所以“同一 HTTP 请求内透明重生成”并不意味着可以无限等待。

**本地实测**

本机 Claude Code 版本是 `2.1.205`。我让它连接本地 fake Anthropic endpoint，全程不访问真实 API。

延迟成功测试：

```text
server 建立连接后等待 12 秒
Claude Code 请求数：1
没有并行重试
12 秒后收到合法 SSE
Claude Code exit code：0
总耗时：13.33 秒
```

这说明连接保持正常时，Claude Code 至少能等待 12 秒，不会因为短暂无响应立即重试。

连续返回 `500` 时：

```text
请求时间：0.93s, 1.51s, 2.67s, 4.75s, 9.55s, 17.75s
退避间隔：0.58s, 1.17s, 2.08s, 4.80s, 8.20s
20 秒内请求 6 次，仍未自行放弃
```

它确实有指数退避式重试。因此如果 proxy 抛出 `5xx` 而 session 仍然开放，Claude Code 会重新提交 HTTP 请求，当前实现无法安全处理这种情况。

**对 Proxy 的影响**

当前设计中一次 turn 的最坏时间不是只有 `wait_timeout_seconds=60`：

```text
attempt_1 生成时间
+ 等权重更新最多 60 秒
+ attempt_2 生成时间
+ 可能再次等待和生成
```

SGLang 单次读取超时又是 900 秒。这个组合可能超过：

- Claude Code 自己的 HTTP timeout；
- 整个 episode 的 600～900 秒预算；
- slime harness 的外层运行预算。

因此必须把 deadline 从 episode 传到 HTTP session 和 proxy：

```text
remaining = episode_deadline - now

attempt_timeout =
  min(configured_attempt_timeout, remaining)

update_wait_timeout =
  min(configured_update_wait_timeout, remaining)

没有足够时间完成下一次重生成
-> 不再尝试
-> poison session
-> execution 进入缺员
```

还应在发送 attempt 前等待 coordinator 进入 `ACTIVE`，避免明知正在更新还启动一个大概率被 abort 的请求。

**Claude Code 超时后的处理**

如果 Claude Code 先取消请求，正确链路应是：

```text
Claude Code 取消 HTTP 请求
-> aiohttp handler 收到 CancelledError
-> 取消当前 proxy wait/send
-> 调用 SGLang /abort_request
-> 不 commit capture
-> 不产生 delivered ModelCallAttempt
-> poison 当前 session
-> 终止当前 RolloutExecution
```

现有 capture wire 已经实现了 cancellation 后调用 `/abort_request` 的底层部分，但 proxy 尚未接入真实 HTTP handler，也没有 session poison 和 execution 终止。

**本地可以测什么**

完全可以在本地用同一个 Claude Code CLI 和 fake endpoint 系统测试：

- 延迟 30/60/120/300 秒时的客户端超时阈值。
- `500`、`429 + Retry-After` 的重试次数和退避。
- 建连后立即断开。
- 返回一半 SSE 后断开。
- 请求期间一直不发送响应头。
- 每次重试的 request body 是否完全一致。
- 重试是否增加 adapter turn count。
- 失败后是否启动新的 HTTP 请求。
- proxy 内部成功重生成时是否始终只有一个 Claude Code 请求。

不过结果必须按 Claude Code 版本记录。正式 FA-5 使用的容器二进制若不是本机 `2.1.205`，需要用相同 tarball 再跑一遍。

最终边界应是：**本地测试用于确定 timeout/retry 参数；session poison 和 episode deadline 是代码层必备防线；FA-5 只验证真实环境行为，不能依赖 Claude Code “通常会等足够久”。**



**建议顺序**

先暂停“FA-1 已完成”的判定。立即修复同步入口、BringupService 初始化、sampling params 来源和 proxy HTTP 接线；持久 worker、ready queue 与无丢失交付则和 FA-2 一起完成。完成本地 HTTP 故障注入后再进入 FA-5 真机验证。

验证方面，现有测试本身全绿：定向测试 `36 passed`，全套 `768 passed`，`inspect-rh2-s1` 通过。但上述反例说明当前测试没有覆盖真实 slime 调用契约和跨 batch 生命周期。未修改任何文件。


---

## 轮次 8（2026-07-13：v3 复审 → 大部分修复正确；1 严重 + 2 一般 + 1 补强）

- **严重：evidence_file_sha256 不真正约束已提交行**——恢复路径只查 id 集合与多余行，删除后不重序列化回验 SHA；反例 = 改已提交行 fetched_at（不在 cross_check 内）保留旧 SHA → 接受且 recovered_drop=0。【v3.1：已提交集合规范化重序列化回验 SHA，不符即拒；新增"已提交行被修改"回归测试】
- **一般 1：manifest 重复 instance_id 静默覆盖**。【v3.1 显式拒绝】
- **一般 2：header 机器账目（count/enriched_count/evidence_line_count）不对账**——全改 999 仍加载成功。【v3.1 对账；enriched_count 严格检查以 reverify_count 标记区分 v3.0 旧口径一次性迁移】
- **补强：manifest 原始字节 sha256 == Docker-Content-Digest**。【v3.1 实证并入 evidence（manifest_blob_sha256_verified）；旧 184 条归 reverify 通道，本轮限额窗口重置后全部补验，零漂移；185/216 fully-verified】
- codex 独立验证：13 定向 + 781 全套通过、inspect-rh2-s1 PASS、184 条内部交叉核对通过；T1 保持 OPEN、T2 可并行的判定与我方一致。


---

## 轮次 9（2026-07-13：v3.1 复审 → 四项修复正确；1 严重 = 严格性可被删字段降级绕过）

- **严重：v3.1 可伪装成旧 v3**——严格对账挂在可选字段（reverify_count 等）上；四个反例（删 evidence_file_sha256 / 删 reverify_count+改 enriched_count=999 / 删 source_refs_file_sha256 / 改 evidence_file 路径）均被接受，组合反例（删提交 SHA + 改已提交 evidence）也被接受。【v4 修复：显式新 schema，header 十字段必填必验；v2/v3 直接加载拒绝；migrate_v3_manifest 仅接受 sha256 pin 命中的已知产物并立即重写 v4；+14 回归测试（33 项全绿）；真实产物已 pin 迁移，185 条无损，现 186/216】
- 其余确认正确：已提交行 SHA 回验 / 重复 id 拒绝 / header 计数（标记在场时）/ manifest 字节哈希；真实产物 216/185/零 legacy/零恢复丢弃、6 项 digest 匹配、19+797 通过、inspect-rh2-s1 PASS。
- 小问题：s2_1_manifest 的"13 项无网络单测"过时。【已更新为 33 项】
- 建议"最后 31 条拉取前先升版，避免收口后再迁移整份账本"——已照做（本轮先迁移后续富化）。


---

## 轮次 10（2026-07-13：v4 复审 → 降级绕过修复确认；1 严重 + 2 一般，均已修复；T1b 随后收满）

- **严重：无归属 evidence 静默丢弃**——digest-only entry 名下的 evidence 行被 v4 加载接受但不消费，下次 flush 静默删除（codex 用公开 API 复现：561 bytes → load 返回 0 条 → 再 flush 0 bytes）。【v4.1：flush 写盘前逐条归属+交叉校验；严格加载要求 evidence 全量被消费；丢弃仅限显式迁移路径且计数】
- **一般 2：迁移只 pin manifest**——旧产物无内嵌提交 SHA 时 evidence 可在 pin 后被替换（codex 复现 fetched_at 替换后迁移成功）。【v4.1：双 pin + 旧 header 内嵌 SHA 与 pin 互检】
- **一般 3：计数字段无严格类型**——216.0/True/False 均被 == 接受。【v4.1：type(v) is int ∧ >=0 + 计数链 enriched+reverify <= evidence <= count】
- 回归 +10，store 43 项全绿；本轮限额窗口重置，剩余 30 条收满——**T1b 216/216 fully-verified，ALL PASS**。


---

## 轮次 8（2026-07-13：FA-1 第三轮审查 + 源码引导 CC 实验 → 6 P0 全部采纳）

> 原文全文转录（tmp/FA1_codex.md 第三版）。处置见 `fa/implementation-notes.md` "FA-1 follow-up 3"：finalize 移到 commit / poison+非零 exit 强制缺员 / 统一 poison + episode deadline / 逐 attempt rid / worker 崩溃不静默重启 / capture FIFO 去覆盖 / CC 四变量训练守卫 + 不返 404 + 版本固定。CC 2.1.205 行为证据（两份报告 + 探针套件 + 34 JSON）随本轮入库，是版本画像/漂移检测器。测试 797 → 831。

**结论**

`6b5d0354` 确实修复了上一轮指出的主要问题，`797` 项测试和 S1 inspector 均通过。但“5 个 P0 全部闭合”这个结论仍然过早：我确认还有 **6 个会影响真实 fully async 链路正确性的 P0**。目前不建议直接进入 FA-2 后就租卡，应该先补一轮本地接线修复与集成测试。

**P0 阻塞问题**

1. **模型结果在真正交付给 Claude Code 前就被标记为 delivered**

[capture_wire.py:232](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/experiments/s1_7a_bringup/capture_wire.py:232) 在 `registry.stage()` 后立刻调用 `finalize_delivered()`；但真正写 HTTP/SSE 响应发生在 [common.py:359](/Users/roger/Desktop/claude-code-verl-stage0h/reference/slime/slime/agent/adapters/common.py:359)。

客户端若在两者之间断开，会出现：

```text
ModelCallAttempt = delivered
但 Claude Code 没收到响应
Trace 也没有 commit 这一轮
```

而且成功 attempt 的引用形如 `staged:{session}:t1`，同一 session 的多个正常 turn 会重复使用该引用。

建议把 `ProxyCallResult` 放进 `PendingTurn`，只在 `_respond()` 成功且 `record_turn/registry.commit` 完成后 finalize；取消、断连和 unregister 路径必须调用 `abandon_delivered()`。capture ref 应使用真实 request/turn/capture record ID。

2. **session poison 没有真正终止 harness execution**

`SessionPoisonRegistry` 当前只是字典和请求入口检查，[async_worker.py:274](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/adapters/slime/async_worker.py:274) 没有向 execution owner 发取消信号。

更危险的是 [generate.py:1410](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/adapters/slime/generate.py:1410) 记录了非零 harness exit code，却没有据此强制拒绝轨迹。若先产生几个有效 turn，之后 session 中毒并导致 Claude Code 失败退出，已有部分轨迹仍可能进入评分和训练。

需要建立：

```text
poison session
-> 原子标记 execution failed
-> 取消 Claude Code / sandbox execution
-> harness 返回后再次检查 poison
-> 强制该 execution 缺员
```

不能依赖 HTTP 状态码让 Claude Code 自行退出。

3. **并非所有不可归因错误都会 poison，且恢复等待无视 episode deadline**

发前等待 ACTIVE 超时、版本恢复超时、fencing 不符、版本回退等分支会抛 `UnattributableModelCallError`，但不会统一 poison。

我构造的探针结果是：

```text
presend deadline exceeded -> poisoned=False
episode deadline=5s，但版本恢复等待跑到 60s -> poisoned=False
```

应在 `ModelCallProxy.call()` 外层统一捕获所有不可归因终止，执行 poison + attempt 落账；`_wait_version_advance()` 必须接收同一个绝对 episode deadline，而不是独立使用固定 60 秒。

4. **内部重生成重复使用同一个 SGLang request ID**

[capture_wire.py:172](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/experiments/s1_7a_bringup/capture_wire.py:172) 在 `_send_once()` 外构造一次 payload/rid，后续 attempt 忽略 `attempt_number`，因此 attempt 1 和 attempt 2 使用相同 rid。

每个 proxy attempt 必须生成独立 rid，并让 `/abort_request` 精确指向对应 attempt。当前没有真实 wire 测试覆盖这一点。

5. **worker 在两个 batch 之间崩溃会被静默重启**

[rollout_entry.py:219](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/experiments/fa_bringup/rollout_entry.py:219) 发现旧 worker task 已完成时直接覆盖，没有读取 `.result()`。

我复现到：

```text
batch1 正常
worker 随后以 WorkerHalted 崩溃
batch2 自动启动新 worker 并继续训练
```

这违反“sink/task source 故障后训练不得继续”。如果旧 task 已结束，必须先传播其异常；只能通过显式、可审计的 recovery API 重启。

6. **同一 session 的并发模型请求仍会破坏 capture 对账**

`CaptureRegistry.pending` 以 `session_id` 为唯一 key。Claude Code subagent 或并发请求共享 session 时，第二个请求会覆盖第一个 pending turn，导致第一个 `record_turn()` 提交错误数据。

应以 `request_id/logical_turn_id` 为 key，并从 HTTP handler 一直传递到 `record_turn()`。单独增加 `turn_seq` 不能解决覆盖问题。

**P1 问题**

- [glue.py:454](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/experiments/s1_7a_bringup/glue.py:454) 在 asyncio 请求路径里同步执行 `requests.get(..., timeout=5)`，可能阻塞整个 adapter。并且它查询的是 router URL，尚未证明等价于所有 SGLang engine 已完成权重同步。长期应由 coordinator 发布所有 engine ACK 后的 consensus version。
- audit tombstone、`weight_versions`、`session_deadlines`、`turn_seq`、poison registry 和 dropped group 记录仍会无限增长。测试中 `max_audit_artifacts=1` 写入 100 项后字典仍有 100 个 key。
- `FaRolloutService.shutdown()` 目前只有测试调用，没有接到 trainer/eval 切换或进程退出生命周期。
- 当前没有 production-level `capture_wire` 集成测试，因此 797 项测试全绿并不能覆盖响应提交、断连、rid、真实 poison 和版本端点。

**Claude Code 本地补测**

我使用 Claude Code `2.1.205` 和本地 fake Anthropic endpoint 补测，结果如下：

- 完全不发送响应头，延迟 `30/60/120` 秒后返回成功：均只有 1 个请求且正常退出。因此客户端 timeout **大于 120 秒**，精确边界仍未知。
- 连续 HTTP 500：20 秒内 6 次请求，约按 `0.60/1.05/2.32/4.51/9.21s` 退避，请求 body 相同。
- HTTP 429 + `Retry-After: 2`：至少 5 次请求，前两次约等待 2 秒。
- 响应头前断连：会自动重试，请求 body 相同。
- 发送部分 SSE 后断连：约 7ms 后重试，但第二次请求发生了 `stream=true -> false` 等 body 变化。因此不能仅靠 body hash 去重。
- 挂起请求期间终止 Claude Code：server 能观察到客户端关闭，只有 1 个请求。

这进一步证明：

```text
proxy 内部重生成期间不能提前发送响应头或 SSE heartbeat
不可归因错误必须 poison + 终止 execution
不能依赖 body 相同进行重试去重
cancellation 必须 abort SGLang attempt 且不 commit capture
```

详细报告在 [claude_code_http_retry_local_baseline.md](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/fa/claude_code_http_retry_local_baseline.md)。这些探针和证据当前尚未提交。

**建议顺序**

先修上述 P0，并补一个本地 adapter 集成测试，至少覆盖：

```text
proxy attempt1 abort -> attempt2 新 rid -> 单次 HTTP 成功
响应提交前客户端取消 -> abandon、不 finalize
不可归因错误 -> poison -> harness 被取消 -> execution 缺员
同 session 两个并发请求不串账
worker 跨 batch 崩溃不得静默重启
```

完成后再进入 FA-2。FA-5 只需复测容器内实际 Claude Code tarball 行为，而不应再承担发现这些本地可验证接线错误的职责。




补充的claude code cli实验和结论：
**结论**

源码引导的补测完成。它进一步证明 `6b5d0354` 仍不能视为 FA-1 P0 全部关闭，除了上一轮发现的生产接线问题，还缺少 Claude Code 客户端重试 ownership 的正式控制。

下面这段可以直接发给 Claude。

---

## 给 Claude 的复核结论

### 一、源码与黑盒实验的新结论

基于 `reference/claude-code-typescript-src` 和固定 Claude Code `2.1.205` 的本地测试，确认正式训练子进程必须强制注入：

```json
{
  "DISABLE_COMPACT": "1",
  "CLAUDE_CODE_MAX_RETRIES": "0",
  "CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK": "1",
  "CLAUDE_CODE_UNATTENDED_RETRY": "0"
}
```

当前 RH2 只在 [generate.py:581](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/adapters/slime/generate.py:581) 强制注入 `DISABLE_COMPACT=1`，其余三项尚未进入生产子进程环境，因此“proxy 是唯一模型调用重试 owner”目前还不是运行时硬事实。

`2.1.205` 的实际实验结果：

| 场景 | 上述防线启用后请求数 |
|---|---:|
| HTTP 500 | 1 |
| HTTP 429 | 1 |
| 响应头前断连 | 1 |
| 部分 SSE 后断连 | 1 |
| 延迟后成功 | 1 |
| HTTP 404 | **2**，先 stream，随后 non-stream |

`404` 是重要例外。即使：

```text
CLAUDE_CODE_MAX_RETRIES=0
CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK=1
```

Claude Code 仍会立即发起第二个非流式请求。源码 [claude.ts:2607](/Users/roger/Desktop/claude-code-verl-stage0h/reference/claude-code-typescript-src/services/api/claude.ts:2607) 的 404 fallback 分支确实没有检查禁用变量。

因此 adapter 所有错误路径都不得返回 404。若必须返回 HTTP 错误，应使用非 404 状态并附 `x-should-retry:false`；但真正的边界仍是 poison session 并主动终止 execution。

### 二、超时结论

`API_TIMEOUT_MS=1000` 对“尚未收到响应头”有效：约一秒后客户端取消，且 `MAX_RETRIES=0` 时只有一次请求。

但收到部分 SSE 后 body 永久停止时，`API_TIMEOUT_MS` 不生效。源码中的 stream watchdog 虽然在二进制中存在：

```text
CLAUDE_ENABLE_STREAM_WATCHDOG=1
CLAUDE_STREAM_IDLE_TIMEOUT_MS=1000
```

实际 `2.1.205` 在 3 至 5 秒窗口内仍未终止。探针已使用 HTTP/1.1 chunked framing 排除普通 body 缓冲问题。

这只能登记为“源码意图与黑盒行为不一致”，不能把 watchdog 当成正式正确性依赖。必须保持：

```text
proxy_deadline < Claude API timeout < harness hard-kill deadline
```

动态 episode deadline、handler cancellation、SGLang abort 和 capture rollback 都仍需 RH2 自己实现。

### 三、仍未关闭的 P0

1. [capture_wire.py:232](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/experiments/s1_7a_bringup/capture_wire.py:232) 在真正向 Claude Code flush SSE 前就 `finalize_delivered()`。客户端在 flush 前断开会形成虚假 delivered。应在 `_respond()` 成功和 capture commit 后 finalize，失败路径调用 `abandon_delivered()`。

2. `SessionPoisonRegistry` 没有通知 execution owner 终止 Claude Code/sandbox。非零 harness exit 也没有强制现有 partial trace 缺员。poison 必须触发 execution cancellation，并在 harness 返回后再次检查。

3. 发前 ACTIVE 超时、版本恢复超时、fencing 错误等不可归因分支没有统一 poison；版本恢复等待也没有受 episode 绝对 deadline 限制。

4. proxy 内部重生成重复使用同一个 SGLang rid。每个 attempt 必须生成独立 rid，并让 `/abort_request` 指向对应 attempt。

5. persistent worker 在两个 batch 之间以 `WorkerHalted` 崩溃后会被静默替换。启动下一 worker 前必须读取旧 task `.result()` 并传播错误，禁止无审计自动恢复。

6. `CaptureRegistry.pending` 只按 `session_id` 索引。同 session 的并发 subagent 请求会互相覆盖，必须改为 request/logical-turn 级身份。

7. 正式 Claude Code 子进程环境没有强制关闭客户端 retry/fallback，也没有 inspector 验证真实子进程收到这些值。

8. 当前 [host_launch.sh:23](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/experiments/s1_7a_bringup/host_launch.sh:23) 仍下载 npm `latest`。FA-5 必须固定版本和 digest。

### 四、版本冻结建议

建议 FA-5 固定：

```text
Claude Code version = 2.1.205
Linux x64 tarball sha256 =
d3dadfa9cde294ac82c755eb6d889291228849180bac5d677ad1a4027aca1bc4
```

容器启动时必须检查：

```text
tarball sha256
bootstrap/platform 版本一致
claude --version == 2.1.205
训练守卫环境变量进入真实子进程
```

任一不符都应 fail-fast。

---

完整分析在 [claude_code_retry_timeout_source_guided_validation.md](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/fa/claude_code_retry_timeout_source_guided_validation.md)。

新增了可重复套件 [claude_code_http_probe_suite.py](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/experiments/fa_bringup/claude_code_http_probe_suite.py)，固定版本下执行 10 个场景，结果 `hard_pass=true`，证据安全扫描零命中。`py_compile` 通过；当前环境未安装 `ruff`，因此没有运行 ruff。所有新增实验、报告和证据尚未提交。



---

## 轮次 11（2026-07-13：v4.1 复审 → 数据资产达标确认；1 运行错误 + 1 对称性问题，修复后 T1 代码面同步达标）

- **严重：迁移 CLI 与双 pin API 脱节**——CLI 单 pin 调用双 pin 函数，触发即 TypeError；报告表述与代码不符。【处置：CLI 迁移入口移除（codex 首选方案）；函数留 store 审计化使用；报告修正】
- **一般：writer/loader 不对称**——enriched entry 缺 evidence 可写出、loader 必拒（计数链不成立）。【修复：flush 对称守卫 set(evidence)==owned_ids 双向拒绝 + 新测试；store 44 项全绿】
- codex 最终资产核验：216/216/216 三集合相等、双哈希标志全 True、214 唯一 digest（两对共享符合预期）、6 项 digest 匹配、inspect-rh2-s1 PASS；指出上轮提交信息 822 为过时口径（实际 831，账本一致）。
- 判定：**T1 数据交付达标**；本轮代码修复后 T1 可正式关闭评审。


---

## 轮次 9（2026-07-13：FA-1 第四轮审查 → 2 确定性 P0 + 4 接线缺口，全部采纳）

> 原文全文转录（tmp/FA1_codex.md 第四版）。处置见 `fa/implementation-notes.md` "FA-1 follow-up 4"。本轮最重要教训：轮次 8 的 deadline 修复**静默失败**（无 assert 文本替换）且配套测试**假阳性**（在目标分支前就退出）——修复必须配"真进目标分支"的断言。FIFO 串账改 overlap fail-closed（request 级归属 = FA-2 第一验收项）；formal 链强制拒绝非零 exit（纠正轮次 8 的错误理由：任务失败负样本 = exit 0 + reward 0）；poison 主动取消 harness task；404 middleware 真接线；host_launch 每次校验 + 原子 mv；StaticActiveCoordinator TTL 缓存；poison/tombstone/weight_versions 有界。测试 831 → 835。

**结论**

`d3319573` 修复了 rid、worker 异常传播和 CC 环境守卫等真实问题，但“六个 P0 全部闭合”仍不成立。我复现出 **2 个确定性 P0**，另外有 **4 个生产接线缺口**。建议先补完这些，再把 FA-1 标为完成；FA-2 可以同步设计，但 request 级 capture 归属必须成为 FA-2 第一项。

以下内容可以直接返回给 Claude。

---

## P0-1：episode deadline 仍未传进版本恢复等待

[async_worker.py:751](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/adapters/slime/async_worker.py:751) 调用：

```python
await self._wait_version_advance(
    attempts, scoped, attempt_number, window_now
)
```

漏传了 `deadline_monotonic`。虽然函数签名新增了该参数，但真实调用仍使用默认 `None`，继续独立等待 `wait_timeout_seconds=60`。

确定性探针结果：

```text
episode deadline = 3s
wait_timeout = 50s
实际失败时 fake clock = 50s
预期 = 3s
```

现有 `test_recovery_wait_respects_episode_deadline` 是假阳性：它设置 deadline=3，但默认 `min_attempt_budget_seconds=5`，调用在第一次发送前就以预算不足退出，根本没有进入版本恢复等待；测试又只断言任意 `UnattributableModelCallError`，所以仍然通过。

修复要求：

```python
await self._wait_version_advance(
    attempts,
    scoped,
    attempt_number,
    window_now,
    deadline_monotonic,
)
```

测试必须额外断言：

```text
send 被调用一次
reason_code == version_did_not_advance
clock_at_failure <= episode deadline
```

## P0-2：FIFO 仍会在并发完成乱序时静默串账

[capture_wire.py:130](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/experiments/s1_7a_bringup/capture_wire.py:130) 的 `commit(sid)` 没有请求身份，只能弹出最早 stage 的记录。

真实 slime [common.py:318](/Users/roger/Desktop/claude-code-verl-stage0h/reference/slime/slime/agent/adapters/common.py:318) 会把同 session 请求作为独立 asyncio task 放进 `inflight`，没有 per-session 串行锁。因此合法顺序可能是：

```text
A stage
B stage
B 先完成 SSE flush
record_turn(B) -> commit(sid) -> FIFO 弹出 A
```

确定性探针已经复现：

```text
B completion 实际 commit = request_A_slow
预期 = request_B_fast
silent_misattribution = true
```

这比覆盖丢失更危险，因为它会生成结构合法但 token、logprob、weight version 属于另一请求的训练轨迹。

FA-2 必须首先改成 request 级归属。可选方案：

- 给 `record_turn` 传播 `request_id`；
- 使用 `ContextVar` 在每个 asyncio request task 中保存 rid；
- 以 `TurnRecord` 对象身份建立 pending 映射。

在精确归属完成前，检测到 pending overlap 应 fail-closed，不应使用 FIFO 猜测。

## P0-3：formal 链没有启用非零 harness exit 拒绝

虽然新增了 `reject_on_nonzero_harness_exit`，但默认值是 `False`，而 [glue.py:364](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/experiments/s1_7a_bringup/glue.py:364) 构造 formal config 时没有设置它。因此即使 `RH2_REQUIRE_REAL_WEIGHT_VERSIONS=1`，非零退出仍不会拒绝。

“非零 exit 可能是合法任务失败负样本”这个理由不准确：

```text
任务没有解决 -> Claude Code 正常 exit 0，grader 给 reward=0
Claude Code exit 非零 -> harness/API/进程执行失败
```

除非存在经过验证的特定非零业务退出码，否则首版 formal baseline 应全部拒绝。建议在 `require_real_weight_versions=True` 时启动断言要求该开关同时为真。

## P0-4：poison 仍没有主动终止 execution

当前新增的是：

```text
await harness_driver.run(...)
-> harness 返回
-> session_poison_check
-> partial trace 作废
```

这保护了训练准入，但没有实现：

```text
proxy poison
-> 立即取消 Claude Code
-> 终止 sandbox execution
```

若 Claude Code 没有快速退出，worker 仍会一直等到 episode hard timeout。`MAX_RETRIES=0` 降低了概率，但 404 fallback 和未来版本漂移证明不能依赖客户端自退。

这可以留到 FA-5 真机验收，但执行 owner cancellation 的代码必须在 FA-5 前实现，FA-5 应验证它，而不是现场才开始写。

## 一般问题

1. `assert_adapter_status_not_404()` 全仓只有测试调用，没有生产调用点。它目前是未接线 helper，不能支持“adapter 任何错误路径不得返回 404”的结论。建议用 aiohttp middleware 转换 404，或做路由级集成测试并确保未知模型路径返回 503 + `x-should-retry:false`。

2. [host_launch.sh:28](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/experiments/s1_7a_bringup/host_launch.sh:28) 只在 tarball 不存在时校验 SHA。volume 中已有错误、旧版或中断下载留下的非空文件会完全绕过校验。应每次都校验，下载采用临时文件，验证成功后原子 `mv`，并核对 tarball 内 `package.json` 和容器内 `claude --version`。

3. `_latest_engine_version()` 仍在同步执行 `requests.get(timeout=5)`。注释称会经线程池，但代码没有 `asyncio.to_thread`；而 `StaticActiveCoordinator.current_window()` 在 proxy 热路径会反复调用它。32 路并发下可能串行阻塞 adapter event loop。FA-4 应以 coordinator 发布的 engine consensus version 取代这里的同步轮询。

4. `SessionPoisonRegistry._poisoned` 没有清理接口，`CaptureRegistry.unregister()` 也没有删除 poison。长训练中每个失败 session 都永久留在内存。audit tombstone 同样仍然随 attempt 总数增长。

## 验证结果

我实际执行了：

```text
完整 pytest：831 passed
inspect-rh2-s1：PASS
Claude Code 2.1.205 行为套件：hard_pass=true，10 cases
py_compile：PASS
host_launch.sh bash -n：PASS
```

测试全绿没有抓到上述问题的原因很明确：

- deadline 测试在进入恢复等待前就提前失败；
- FIFO 测试只覆盖 stage 与 commit 同序；
- 404 测试只测试未接线 helper；
- 没有 formal config 的非零 exit 端到端测试；
- 没有 cached tarball 反例测试。

**建议顺序**

1. 立即修 deadline 参数漏传和假阳性测试。
2. formal config 强制拒绝非零 exit。
3. 把 request 级 capture 归属设为 FA-2 第一验收项；完成前 overlap 必须拒绝。
4. 接通 404 middleware/路由守卫和缓存 tarball 校验。
5. FA-2 其余 assembler 工作继续。
6. FA-5 前实现 execution-owner cancellation，再用真实 Linux Claude Code 和 SGLang 验证。



---

## 轮次 10（2026-07-13：FA-1 第五轮审查 → 双线程拓扑 4 P0 全部采纳）

> 原文全文转录（tmp/FA1_codex.md 第五版）。处置见 `fa/implementation-notes.md` "FA-1 follow-up 5"。主题：既有测试全在单事件循环，生产是 Ray actor loop + aiohttp adapter 线程——跨线程取消（call_soon_threadsafe）、middleware 生产序直挂、registry 锁原子化、active poison 不淘汰 + release 归档。glue 持久 artifact_sink、容器内版本精确比较随本轮落地。测试 835 → 852。

**结论**

`60c6b3fd` 正确修复了 deadline 传参、formal 非零 exit、FIFO 猜测和 tarball 缓存校验。但 FA-1 仍不能关闭：我确认有 **2 个生产路径 P0**，以及 poison registry 的并发与淘汰设计问题。现有测试都在单事件循环中运行，没有覆盖真实的“Ray actor loop + aiohttp adapter thread”拓扑。

以下可直接返回给 Claude。

---

## P0-1：主动取消在真实双线程拓扑中不生效

真实架构在 [glue.py:298](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/experiments/s1_7a_bringup/glue.py:298) 明确把 adapter 放在独立线程：

```text
Ray actor event loop：harness_task
aiohttp adapter thread：proxy / poison()
```

但 [generate.py:1495](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/adapters/slime/generate.py:1495) 注册的回调直接执行：

```python
lambda _sid, _reason: harness_task.cancel()
```

`asyncio.Task.cancel()` 不是跨线程安全 API。生产中 poison 从 adapter 线程调用该回调，不能直接取消 actor loop 中的 task。

确定性双线程探针结果：

```text
task_done = false
task_cancelled = false
cancel_handler_seen = false
subscriber_removed = true
```

更严重的是 [async_worker.py:327](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/adapters/slime/async_worker.py:327) 吞掉 callback 异常，因此账面显示 subscriber 已处理，实际 harness 仍在运行。

当前 e2e 测试是假拓扑：poison 和 harness task 在同一个 pytest event loop，无法覆盖生产问题。

正确实现：

```python
owner_loop = asyncio.get_running_loop()

def cancel_from_any_thread(_sid, _reason):
    owner_loop.call_soon_threadsafe(harness_task.cancel)
```

测试必须从真实 `threading.Thread` 调用 `registry.poison()`，并断言 actor loop 中的 harness 收到 `CancelledError`。

## P0-2：404 middleware 没装到首个生产 adapter

[glue.py:290](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/experiments/s1_7a_bringup/glue.py:290) 的顺序是：

```python
self.adapter = AnthropicAdapter(...)
install_capture_wire(self.registry)
```

但 `install_capture_wire()` 只是 monkeypatch 未来的 `BaseAdapter.__init__`。已经构造好的 `self.adapter` 不会获得 middleware。

确定性探针：

```text
adapter_created_before_install_has_guard = false
adapter_created_after_install_has_guard = true
```

而生产中只有这一个先创建的 adapter。因此当前正式 adapter 仍会暴露 aiohttp 默认 404，Claude Code 仍可能绕过 fallback 开关再发一次请求。

建议不要靠构造器 monkeypatch。直接：

```python
self.adapter = AnthropicAdapter(...)
self.adapter.app.middlewares.append(rh2_no_404_middleware)
```

并在 `run_app_in_thread()` 前断言 middleware 在场。测试应使用与生产相同的“先构造 adapter，再 install”顺序，而不是手工创建已经带 middleware 的测试 app。

## P0-3：SessionPoisonRegistry 跨线程存在丢通知竞态

`subscribe()` 和 `poison()` 会从不同线程调用，但内部 dict 没有锁：

```text
actor thread：检查 sid 尚未 poisoned
adapter thread：写入 poisoned，发现没有 subscriber
actor thread：随后写入 subscriber
```

此时 poison 已发生，但 callback 永远不会执行。

需要使用 `threading.Lock` 将以下操作原子化：

```text
检查 poisoned + 注册 subscriber
首次 poison + 提取 subscriber
unsubscribe
is_poisoned / reason
```

callback 应复制出来后在锁外调用，避免死锁。

## P0-4：poison FIFO 会淘汰仍活跃的安全事实

[async_worker.py:318](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/adapters/slime/async_worker.py:318) 达到 `max_entries` 后无条件删除最旧 poison，并假设其 execution 已终止，但代码没有 termination ACK。

最小反例：

```text
max_entries = 1
poison active session A
poison session B
A_still_poisoned = false
```

如果 A 的主动取消失败或仍在清理，后续请求会重新通过 `check()`，orchestrator post-check 也可能看不到 poison。

不要淘汰 active poison。建议：

```text
active poison：保留直到 execution cleanup ACK / unregister
archived poison：只保存有界摘要
```

active 数量自然受 rollout concurrency 限制，不需要 FIFO 猜测生命周期。

## 一般问题

1. **audit 引用会变悬空。**  
   tombstone 超过 `8 × max_artifacts` 后直接删除，但 glue 构造 `ModelCallProxy` 时没有配置 `artifact_sink`。探针中 `audit:a0` 已无法解析。formal 链应强制配置持久 artifact sink，不能让 `ModelCallAttempt.evidence_refs` 指向已删除对象。

2. **容器内版本检查仍未实现。**  
   host tarball SHA 每次校验已修好，但 [glue.py:121](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/experiments/s1_7a_bringup/glue.py:121) 只运行 `claude --version`，没有比较结果。`host_launch.sh` 自己也写明这仍待 container 侧完成。应比较精确版本 `2.1.205` 并把结果写入启动 evidence。

3. **TTL 只减少同步阻塞，没有消除它。**  
   `StaticActiveCoordinator` 每次 TTL 到期仍会在 adapter event loop 中同步执行最长 5 秒的 `requests.get`。FA-4 的真实 coordinator 必须彻底替换这条轮询，且版本应是全部推理 engine ACK 后的 consensus version。

4. **request 级 capture 归属仍是 FA-2 硬前置。**  
   当前 overlap fail-closed 本身是合理临时方案；两条 draft 确实都会 abandon，队列不会继续 commit。但修复跨线程 poison 前，它不能保证主动终止 harness。

## 已确认修好的部分

- `deadline_monotonic` 已真实传入 `_wait_version_advance()`。
- 新 deadline 测试已进入 abort→恢复分支，不再是假阳性。
- formal 链启动断言已要求 `reject_on_nonzero_harness_exit=True`。
- overlap 不再使用 FIFO 猜测，改为 fail-closed。
- cached tarball 每次校验、临时下载和原子替换已实现。

## 验证

```text
FA 定向测试：108 passed
当前完整工作树：847 passed
inspect-rh2-s1：PASS
py_compile：PASS
host_launch.sh bash -n：PASS
```

完整测试数高于 commit 声明的 835，是因为当前工作树还有并行 S2 变更；FA 文件本身没有未提交修改。

**建议顺序**

先修跨线程 cancellation、poison registry 原子性和 middleware 安装顺序，再关闭 FA-1。FA-2 可以并行开始设计，但 request 级 capture 归属必须保持第一验收项。artifact sink 和容器版本断言应在 FA-5 租卡前完成，而不是留到真机现场编写。



---

## 轮次 12（2026-07-13：T2-a/b 复审 → vendor 与 T1 关闭正确；2 关键 + 2 一般，T2-c 开工前修复）

- **严重 1：包构造缺身份交叉核对**——public.repo/base_commit 与 grading 不一致仍组包成功（反例 evil/other 仓库）。【修复：逐字相等断言 + 负测试；T2-c 登记 resolved-package validator（对 T1 键控清单核 image 身份）与消费期重验义务】
- **严重 2：vendor 路径与 eval_cmd 自声明**——spec_vendor_file 接受 /tmp/attacker.py；报告计划 importlib 按路径加载 = 注入入口。【修复：spec_vendor_id 封闭枚举 + 固定注册表；构建期提取 JSON、运行期只读（永不 exec vendored Python）；eval_cmd 注册表派生 + 互检】
- **一般 3：provenance**——source_url 指 main 会漂移；2000 行 MIT 代码只留一句注记。【修复：immutable commit URL + LICENSE 全文入库 + digest 登记】
- **一般 4：报告数字无机器复算**——vendor 33/808、216/216、官方 0/216 只在文字里。【修复：test_vendor_specs.py 7 项复算断言 + 3 个 CLI marker 测试】
- codex 确认正确：T1 关闭记账、vendor 逐字节一致（三方 sha 同值）、大小写投影、golden/grading 结构分离、8 项 digest 匹配、28+847 通过。


---

## 轮次 11（2026-07-13：FA-1 第六轮审查 → 2 正式链阻塞 + 2 身份/生命周期项，全部采纳）

> 原文全文转录（tmp/FA1_codex.md 第六版）。处置见 `fa/implementation-notes.md` "FA-1 follow-up 6"。启动探针 list 形状崩溃（single_pending_turn 形状权威）；正式链 sink fail-closed（ArtifactSinkWriteError + sha256 文件名 + 原子落盘 + 启动探针）；SID 复用兜底（subscribe 查归档、register 拒毒）；release 移到容器清理后（真 ACK）。FA-2 第一项硬验收更新为 execution 唯一身份 + request 级 capture 归属。测试 852 → 870。

**结论**

`4976ea70` 的四项跨线程修复基本正确，但 **FA-1 仍不能宣告闭合**。我确认有两个正式链阻塞问题、两个需要在 FA-2 首项解决的问题。

**严重问题**

1. **启动探针必然触发 `AttributeError`**

[glue.py:604](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/experiments/s1_7a_bringup/glue.py:604) 仍把 `registry.pending[sid]` 当成单个 `PendingTurn`：

```python
pending = self.registry.pending.get(probe_sid)
data = pending.raw_response
```

但当前结构已经是 `list[PendingTurn]`。真实启动进入 `_run_startup_checks()` 后会在 GPU 训练前直接崩溃。

应改为：

```python
pending = self.registry.pending.get(probe_sid)
if not pending or len(pending) != 1:
    raise RuntimeError(...)
turn = pending[0]
data = turn.raw_response
probe_params = turn.capture_params
```

必须补一条调用真实 `_run_startup_checks` 数据形状的本地测试。当前 852/866 条测试没有覆盖这个入口。

2. **正式链的持久 artifact sink 仍然 fail-open**

[async_worker.py:599](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/adapters/slime/async_worker.py:599) 会吞掉 sink 的磁盘错误，退回内存 `audit:` 引用；正式链在 [glue.py:471](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/experiments/s1_7a_bringup/glue.py:471) 只检查“配置了 sink”，不检查它能否成功写入。

确定性探针结果：

```text
sink_failure_raised = false
returned_ref = audit:a0
first_ref_resolvable = false
```

也就是说，磁盘满、权限错误或路径冲突时训练继续，稍后 evidence 引用会悬空。

正式链应：

- sink 写失败立即 fail-closed，并 poison 当前 execution；
- 启动时执行一次 write/read/delete 探针；
- 使用临时文件、`fsync`、原子 `rename`；
- 文件名加入完整 `attempt_id` 的 SHA256，避免清洗和截断碰撞；
- 文件保存完整 payload digest，而不只是 `repr(payload)[:4096]`；
- 返回 opaque artifact ID，不返回本机绝对路径。

**身份与生命周期问题**

3. **session ID 会复用，与 poison 归档语义冲突**

[_session_id()](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/adapters/slime/generate.py:2156) 在存在 `index/group_index` 时产生稳定 ID：

```text
rh2-{task_id}-{index}-{group_index}
```

因此同一题下一次补采、下一批或下一 epoch 可能复用旧 SID。但：

- `subscribe()` 只检查 active poison，不检查 archived poison；
- archived poison 达到容量后又会被淘汰；
- `register()` 不拒绝复用 SID。

探针已经复现：

```text
archived_is_poisoned = true
resubscribe_fired = false
subscriber_retained = true
```

结果可能是：复用后 harness 先启动，直到第一次模型调用才被拒绝；归档被淘汰后，旧 poisoned SID 又可能“复活”。

建议将 SID 绑定到唯一的 `RolloutExecutionIdentity + attempt_number/nonce`，禁止跨 execution 复用。poison 也应以 execution identity 为键。这个应成为 **FA-2 的第一项硬验收**，不能只修 `subscribe()`。

4. **`release()` 并不是真正的 execution cleanup ACK**

[capture_wire.py:141](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/experiments/s1_7a_bringup/capture_wire.py:141) 在 `drop_session` 时归档 poison，但容器清理发生在之后的 [generate.py:1680](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/adapters/slime/generate.py:1680)。

若要称为 execution cleanup ACK，应在 harness 已终止、adapter 已撤销、容器清理完成后释放。否则应改名为 `adapter_session_closed`，避免把它当成完整 execution 生命周期确认。

**一般问题**

- [glue.py:131](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/experiments/s1_7a_bringup/glue.py:131) 使用子串判断版本，`12.1.205-malicious` 也能通过期望 `2.1.205`。应解析版本 token 后精确比较。
- `cc_version_observed` 实际没有写入 `startup_evidence.json`；当前注释和完成报告所说的“结果进 startup evidence”不成立。
- `notify_failures += 1` 没有受锁保护，也没有向控制面发出 halt/failure fact。它目前只是内部计数，不能保证取消通知失败后及时终止 execution。
- `StaticActiveCoordinator` 的同步 TTL 轮询和多引擎 consensus 仍是 FA-4 接线事项，这一项如实递延即可。

**确认有效的修复**

这轮以下修复确实成立：

- `call_soon_threadsafe(task.cancel)` 正确处理 adapter 线程到 actor loop 的取消；
- 404 middleware 已挂到现有生产 adapter，而不再只依赖构造器 monkeypatch；
- poison 的检查、订阅、写入已在同一把锁下原子化；
- active poison 不再被容量策略淘汰。

验证结果：

```text
相关定向测试：101 passed
当前全套测试：866 passed
inspect-rh2-s1：PASS
py_compile / bash -n：PASS
```

全套数量高于报告中的 852，是因为当前 HEAD 还包含之后的 S2 提交。没有修改任何文件。建议先修前两个阻塞问题，再进入 FA-2；FA-2 首项同时完成 execution 唯一身份和 request 级 capture 归属。



---

## 轮次 13（2026-07-13：轮次 12 修复复审 → 大体正确；2 关键 + 2 一般，T2-c 前修复）

- **严重 1：eval_cmd 互检是可选调用**——builder 只调 vendor_pin 不调 verify_grading_eval_cmd，恶意 eval_cmd（rm -rf / #）仍组包成功。【修复：builder 强制互检 + build_private_grading_bundle 派生构造器 + 恶意命令不能组包负测试；消费期两道防线义务保持登记】
- **严重 2：运行期 JSON 不进 wheel**——parents[4] 推算仓库根，codex 实构 wheel 验证 contains_vendor_json=False。【修复：JSON 移入 envpack/data/ 包内数据 + importlib.resources；本地 wheel 重建实证 True；资源存在性测试】
- **一般 3：缺"重提取 == JSON"机器验证**（codex 独立重算相等）。【修复：re-extraction 逐字节等价测试（exec 仅测试/构建期）】
- **一般 4：provenance 旧措辞**。【已更新】
- codex 确认正确：身份错配拒绝、路径注入拒绝、immutable URL、LICENSE、覆盖复算、10 项 digest、42 定向 + 866 全套、隔离快照 inspect-rh2-s1 通过；工作区单个失败来自 FA 线程未提交文件（与 T2 无关）。
