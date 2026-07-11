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
