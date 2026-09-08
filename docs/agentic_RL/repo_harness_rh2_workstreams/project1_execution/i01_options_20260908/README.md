# I01 讨论：REALIGN、最终奖励与多轮轨迹的三种处理路线

日期：2026-09-08。最新状态：**用户已确认首版采用 B，C 暂缓，不排专门 B/C 对比实验；实现与接入验证待办。** 定案见 [A 决策记录](../infra.md#6-用户决定)。下文保留定案前的调查论证，历史“候选/未定”措辞以此最新状态为准。

**同日补充：[miles TITO、真实成本与 thinking 保留策略](miles_tito_followup.md)。** 上一轮漏查了已选 miles 基座的进程内 tokenizer/matcher，现已核对并运行真实 Qwen tokenizer 小探针；run8 单条轨迹的 B 表示量实测为现状的 1.728 倍，不是 GPU 时间倍数。补充稿讨论 B/C 组合与 thinking 政策，最终首版选择以上述用户定案为准。

本地基线：`ac0e2e64163fbe49411540e901df439aea16b6b0`，`miles-migration`。本次只讨论 [I01](../issue_inventory_20260908/README.md#i01消息重渲染后旧轮动作可能整轮失去-loss)，与 I18 路由来源、I19 历史压缩有明确接缝。用户背景材料：[侧边栏讨论](../tmp/侧边栏codex关于realign的讨论.md)。

## 1. 我的建议与理由

优先评估“精确前缀合并、漂移拆行”这条路线：**模型仍按 harness 实际提交的上下文生成；训练组装时，完整 token 前缀一致才合并，不一致就保留旧训练行并新开一行。** 每次实际生成的合格动作保留一次，仍按原 execution/member 计算奖励、优势和 loss 分母。

这是候选建议，不是“关掉阈值就已经完成修复”的结论。当前 slime 的 `fork_threshold_tokens=0` 恰好能关闭 REALIGN 和消息 rewrite merge 两个销毁点，可以作为最小验证入口；RH2 正式 bringup 还没有传入这个参数。身份导出已有同源参数与多行路径，无需先替换训练后端。

理由有四个：

1. 最终 reward 不能补回被删除的策略梯度项；只看训练 reward 上涨不能验证早期决策是否学到了。
2. 新一轮输出长度不是旧动作重要性的可靠代理；当前 1024 规则没有训练质量消融支持。
3. 保留真实请求条件，能把“训练数据有没有忠实表达实际采样”与“要不要改变 Claude Code 的上下文管理”分开判断。
4. 精确前缀合并仍可省计算。确有重复前缀成本后，再决定是否值得做在线追加、模板修正或更复杂的共享前缀训练。

用户提出的“先监控”有价值，适合做小规模诊断基线；我不建议把它定义成“正式训练照旧，等能力明显受损再改”。那会把可直接测量的动作缺失，拖到昂贵且混杂因素很多的最终训练结果里判断。

## 2. 1024 到底在判断什么

当前代码有两个不同的入口，不能合成一句“短响应会被丢弃”。

| 入口 | 比较对象 | 满足条件后发生什么 |
|---|---|---|
| token REALIGN | **新一轮** `len(turn.output_ids) < 1024`；同时必须已有 token 漂移，且首次分歧没有早于最近旧响应起点 | 将最近旧响应从起点起整体替换为新 prompt 内容，mask/logprob 归零，再加入新响应 |
| 消息 rewrite merge | **旧响应**小于 1024；还要求单个 assistant 子节点、生成过的叶等结构条件 | 把旧生成节点改成上下文节点，清掉旧 `TurnRecord` 和 `turn_index` |

源码：[分类与覆盖](../../../../../rh2/src/slime/agent/trajectory.py#L169)、[消息合并](../../../../../rh2/src/slime/agent/trajectory.py#L370)。

REALIGN 的顺序是：

1. 第一轮真实生成 `P1 → A1`，有原始 token 和 logprob。
2. 第二轮完整重渲染得到 `P2`，它可能把 A1 的 thinking 去掉，或重排工具参数。
3. 模型已经基于 P2 生成 A2。
4. 会话结束后组装训练 Sample，才比较 token，并使用已经知道的 **A2 长度**决定 REALIGN/FORK。

所以这个条件并非推理前预测“下一轮会不会超过 1024”；它是事后选择如何表达已经生成的轨迹。消息 rewrite 则更早，在每轮 `record_turn` 时发生。

假设分歧位置都符合 REALIGN 的位置要求：

- A1 长 5000 token，A2 长 20 token：仍可能把 A1 整段屏蔽。
- A1 长 20 token，A2 长 1500 token：会 FORK，保留两段。
- 完全没有 token 漂移：不管新输出多短，都是 CLEAN，不触发 REALIGN。

因此不能把 1024 解读成“最多只损失 1024 个旧 token”，更不能把短新输出解读成“旧动作无关紧要”。

## 3. 最初为什么这样设计：历史中确实有解释

本次补查提交历史，修正了侧边栏讨论中“未找到理由/实验”的过宽说法。

- 早期实现想减少短分支形成独立训练 Sample 的碎片和重复上下文。2026-06-08 的一份提交还提到，当时按叶均分奖励，短 stub leaf 会稀释其余叶的奖励。**当前 `get_trajectory` 已向每个 Sample 广播全额 reward；RH2 另按 execution 归约，旧的均分奖励动机不能原封不动套用。** [历史提交](https://github.com/THUDM/slime/commit/4fcbb24133af33682613d4db653e835fff602f8a)
- 早期 rewrite 作者自报：20 个 SWE 任务、阈值 1024，合并了 5 次改写，屏蔽 3164 token，assistant-role forks 从 15 降至 6。这说明确有工程观测，**但不是当前 REALIGN 条件的阈值消融，也没有最终学习质量结果**。[提交与观测](https://github.com/THUDM/slime/commit/5e59c254e1ef6805db68a5bc239c226956d1d123)
- 2026-06-12，作者明确把“漂移尾长”改成“新一轮完整输出长度”，理由是和 rewrite merge 一样使用完整响应长度口径。两处实际指向不同轮，所以这个代码整齐性理由仍不能证明训练语义合理。[变更提交](https://github.com/THUDM/slime/commit/36fa60e82d20e5853feb617319381ea278b2a932)

准确结论是：**有历史工程动机和早期小规模 rewrite 结果；尚未找到“新输出 1024”足以控制动作损失风险的证据。** 不能说作者毫无考虑，也不能把这个默认值当成经过 GRPO 验证的合理近似。

完整历史锚点、上游 main 与本地对照见 [Production Tracer](slime_tracer.md)。当前 main 的 `trajectory.py` 与 RH2 vendor 字节相同，故直接升级上游并不会自动消除此问题。

## 4. GRPO 的最终奖励能否让它影响很小

**影响可能很小，也可能很大；但“最终才给奖励”不是它无害的理由。** 最终奖励提供的是优势信号，loss mask 决定这个信号作用于哪些实际采样动作。

把当前链路写成简化形式：

```text
某次 execution 的贡献
  = - A_execution / D_execution
    × Σ(该 token 的 loss_mask × DIS 权重 × log πθ(动作 | 真实输入前缀))
```

这里只突出动作覆盖：A 在给定采样组中固定，DIS 权重按现行实现 detach；不把此式称为无偏策略梯度证明。当前 D 是该 execution 全部 sibling 的 provenance token 总数，后端再对 execution 等权平均。[现行 loss 接线说明](../../../../../rh2/src/repoharness2/adapters/miles/faithful_dis_loss.py#L11)

如果同一次实际采样动作在该 execution 的**全部训练行中都没有可训练副本**，其直接策略损失项就是 0。最终 reward=1，也不会给这个动作自动补一项 logprob。某一行 mask=0、另一行仍保留该动作，则可能只是正确的共享前缀去重。

具体例子：

1. 第一阶段，策略选择去检查正确文件还是错误文件。
2. 第二阶段，另一组参数负责生成修复；最终 reward 取决于第一步是否选对。
3. 同题两个 member 的最终 reward 是 1 和 0，组中心化 advantage 为 +0.5、−0.5。
4. 若两条执行的第一阶段动作都被 mask，控制选文件概率的参数得不到这两条动作对应的梯度；保留第一阶段则有正向区分信号。

[数学窄探针](terminal_reward_probe.py)固定这个采样组，有限差分得到目标函数对第一阶段参数的导数：保留动作为约 0.25，屏蔽后为 0。这是参数分离的反例，证明“最终奖励必然补回信用”不成立；不是对真实大模型损失幅度的估算。

真实网络共享参数，所以更精确的说法是：旧内容即便 mask=0，仍可作为后续动作的 attention 上下文，后续 loss 也可能通过共享参数间接改变早期策略。**缺的是旧动作自身的直接奖励信用，不是早期行为永远不可能变化。**

另一个影响来自分母。例如原本 10 个可训练动作 token 被删掉 8 个，剩余 2 个在 execution 内各占 1/2，而不是原来的 1/10。删动作可能改变梯度方向；若分母随最终 mask 重算，还会改变剩余 token 的归一化系数。剩余 token 彼此之间的相对权重未必改变，梯度方向也不一定改变；但不能把这种选择性缺失当成仅仅少用了若干随机 token。

风险大小取决于缺失动作是否冗余、是否与成功/失败和轨迹长度相关、是否落在重要工具调用上，以及其他轨迹能否提供类似训练信号。几个定位 token 很短但可能决定任务能否解决；大量格式 token 缺失则可能影响较小。不能只用 token 总比例下结论。

## 5. P3 能证明什么

这次主审回读了一条具体旧证据：`django__django-11099`，执行目录 `00be4692-dfa2-41fe-a270-`。

- [capture_records.json](../../preflight/remote_evidence_20260708/preflight_evidence/preflight_j4_fail_converter_signature_/artifacts/rollouts/00be4692-dfa2-41fe-a270-/capture_records.json)记录六轮输出长度 `[458, 307, 199, 401, 349, 553]`，共 2267。
- [trajectory_projection.json](../../preflight/remote_evidence_20260708/preflight_evidence/preflight_j4_fail_converter_signature_/artifacts/rollouts/00be4692-dfa2-41fe-a270-/trajectory_projection.json)只引用 t2–t5，mask=1 合计 1502；前两轮共 765 未被该投影覆盖。

这是实际轨迹覆盖缺口，不只是合成测试。但该数据来自失败的 converter-signature 尝试，**不能声称这 765 个 token 已从一次成功训练更新中丢失**，也不能仅凭最终投影反推出一定是 token REALIGN 而非消息 rewrite 等原因。

侧边栏进一步统计的“50 个投影中 32 个无 t0”，来自两次失败尝试。它不是 REALIGN 发生率，不是当前候选题单的抽样估计，更不是训练效果消融。原始漂移事件与完整输入 token 未齐备时，不应继续算出一个似乎精确的质量风险数字。

## 6. 需要区分的三种处理方式

设真实采样是：

```text
第一轮：P1 → A1
第二轮：P2 = P1 + A1′ + 工具观察 → A2
其中 A1′ 是 A1 经历史重渲染后的形式，token 不相同。
```

| 路线 | 第一轮如何训练 | 第二轮实际推理/训练条件 | 主要代价 |
|---|---|---|---|
| 当前 REALIGN | A1 可能整体失去 loss | 仍以实际 P2 为条件训练 A2 | 保持少量行，但选择性减少动作覆盖 |
| **精确前缀合并，漂移时拆行** | 保留 `P1 → A1` | 独立保留 `P2 → A2`；完全相同的前缀才合并 | 重复前缀计算、更多训练行与 packing 压力 |
| **在线追加原始 token** | 保留 A1 | 在 A2 生成之前就构造 `P1+A1+新观察`，让推理和训练都用它 | adapter 需负责模板边界、分支、压缩和上下文变更；模型实际看到的历史也变了 |

第三种路线原则上成立。它在生成之前定义真实输入，训练也用同一输入，可以一致；只是行为分布已不同于原来的全历史重渲染，所以训练和 eval 都需要用同一规则。

**还有一种容易混入的错误操作**：A2 已按 `P1+A1′+观察` 采样，事后却在训练行里把 A1′ 换回 A1，并沿用 A2 的 rollout logprob。这样保住了动作 ID，却改变了动作的条件输入。不能仅凭“所有原始 output IDs 都在”证明训练保真。

本次对固定版本 Polar 原始 builder 做了 [合成 Trace 反例](conditional_prefix_probe.py)：

```text
实际：P1=[10]，A1=[20,99]
实际：P2=[10,21,99,30]，A2=[40,99]
构造的训练序列：[10,20,99,30,40,99]
于是 A2 的训练条件成了 [10,20,99,30]，与实际 P2 不同。
```

99 表示 EOT。原类只检查前轮 prompt 的前缀，并从下一轮 canonical 尾里切出观察；探针命中正常完整重建分支，所有 sampled output 都在，但第二轮条件不同。[结果](conditional_prefix_result.json)

这个证据只针对固定 builder、合成输入和“P2 确为实际 prompt”前提。没有运行 Polar 生产作业，也不能推断其论文实验的发生率或整体训练效果。它支持一个局部原则：**输出保真和条件前缀保真必须分别核对。**

## 7. 外部框架实际提供了哪些参考

这里查的是固定版本的相关调用路径，不是全面框架验收；当前公开代码也不自动代表论文实验版本或 RH2 所用 pin。

| 对象 | 与 I01 直接相关的做法 | 对本项目的含义与限制 |
|---|---|---|
| verifiers v1 + Prime RL | graph 按完整累计 token 前缀复用节点；漂移则分出物理训练路径。导出训练行时，同一实际采样节点跨路径只计一次。renderer 能安全续接时也可用增量扩展。 | 支持“精确时合并，其他情况保留”的路线。当前 TrainClient 限 chat-completions dialect，不能因仓库有 Claude Code harness 就断言已完整支持我们现有 Anthropic 训练入口。[graph](https://github.com/PrimeIntellect-ai/verifiers/blob/27bbd216df0af719a43705866b2cf6139bcc95de/verifiers/v1/graph.py#L659)、[导出](https://github.com/PrimeIntellect-ai/prime-rl/blob/04a61d3b75c3c99f263b2c133e822f998909adf7/src/prime_rl/orchestrator/trajectories.py#L91) |
| verl ToolAgentLoop | 当前代码经 Continuous Tokenization 维护连续 token，新增工具/用户观察；明确拒绝已有消息历史缩短或前缀改变。某些模型还会修正边界 token。 | 用户记得的追加方向是对的；但这是对所管理消息和模板的约束，不能直接拿来包住任意 CC 压缩/子 agent。也不能把它概括为任何情况下一个旧 token 都不动。[当前入口](https://github.com/verl-project/verl/blob/0d3f56a8980a55bfbbf1214ea54fa1b32ca1405c/verl/experimental/agent_loop/tool_agent_loop.py) |
| slime #2287 / #2288 | 在线保存每个 sid 的原始历史，恢复 assistant 内容，渲染新后缀接回历史；作者报告明显减少训练 Sample 和 token 数。 | 方向合理，但 PR 仍未合并，合法 compaction/subagent 明确不在其范围。内部仍完整渲染历史来定位后缀；不是“只 tokenize 新消息”。[PR](https://github.com/THUDM/slime/pull/2287)、[范围与作者实验](https://github.com/THUDM/slime/issues/2288) |
| Polar / ProRL-Agent-Server | 使用 slime 训练，但有自己的 gateway 和轨迹 builder；提供 per-request 与 prefix-merging 两种表达。 | 不能把“基于 slime”理解成使用同一 REALIGN 路径。其效率实验说明重复前缀成本值得重视；当前 builder 的条件前缀边界需单独检查，见 §6。[论文 §3.4](https://arxiv.org/html/2605.24220v1)、[固定源码](https://github.com/NVIDIA-NeMo/ProRL-Agent-Server/blob/6a1ead6bfac054fce6c1e62d1a77b330d96c58db/src/polar/trajectory/builder/prefix_merging.py) |
| Agent Lightning v1 | 实际 adapter 检查 `next_prompt` 是否以前一条完整 `prompt+response` 开头；不成立就提交原训练行，再从当前真实 prompt 开始。各行保持同一 rollout 标识。 | 与推荐的最低改动路线直接相符。相关方法值得复用，不必引入它的整个服务平台；其余去重、截断和算法细节没有因此获本项目认可。[论文](https://arxiv.org/html/2608.17528v1)、[固定实现](https://github.com/microsoft/agent-lightning/blob/218f1f7c0bac0800de4d5a4e5e6f61cf7b5038b4/agentlightning/verl/rollout_adapter.py#L509) |

verifiers/Prime RL、verl 的具体限制及独立反证见 [Falsifier](alternatives_falsifier.md)。现阶段不建议为 I01 更换整套后端，也不把任何外部加速倍数当作本项目收益预测。

## 8. 子 agent 和压缩如何处理

先区分三个层次：**一次任务 execution、其中的实际模型请求、表达这些请求的训练行**。它们没有一一对应要求。消息树叶也不等于 Sample：一次 token FORK 可以把一条消息链拆成两行，而没有多出一个消息树叶。

### 8.1 子 agent

```text
父链：任务 → 调用子 agent → 收到子 agent 结果 → 继续修改
子链：自己的 system/任务/上下文 → 搜索或修改 → 返回摘要
```

子 agent 的输入不是父链末尾的普通文本追加。按 HTTP 请求完成顺序把两条链拼在一起，会把互不属于同一上下文的动作混合。

候选规则是：各请求保留自己的真实输入和输出；仅在完整前缀与真实生成身份都能对应时共享。子 agent 若由被训练策略生成并被此次训练范围纳入，其动作在自己的条件下训练；返回父链的结果副本是观察，不再当作父模型新采样的动作训练。

共享祖先若确实只生成过一次，其策略项只算一次；两个独立采样恰好有相同文本/输入，仍是两个事件，不能只按字符串相同去重。这里需要真实身份与图结构；没有可靠 branch ID 时，独立请求行是安全的表达基线，不必猜出一条链。

同一个任务最终 reward 可继续赋给这次 execution 的相关目标策略动作；拆行不应凭空增加 GRPO member 数，或让开更多分支的任务自动获得更高 execution 权重。粗粒度信用分配的效果是另一个问题，不因拆行本身就需要新增奖励算法。

### 8.2 压缩

压缩将长上下文 P_old 替换为较短 P_summary；这是合法地改变未来模型输入。候选表达是：

- 压缩前已经实际生成的动作，仍保存在其原始条件下。
- 压缩后新动作，以实际 P_summary 为输入，形成新的训练段。
- 若摘要本身由目标策略真实生成且属于本次训练范围，单独保留这次调用；若由固定程序或外部 teacher 产生，则不能当作目标策略 RL 动作。

这样不要求把旧历史硬塞回新窗口，也不要求把压缩前动作丢掉。若未来采用在线追加，也应在明确的分支/压缩段内部追加，在合法边界切段。

**但这仍是表示层建议，不是当前 RH2 已支持压缩的声明。** 当前还有 I19 的历史收缩拒绝与资格语义；threshold=0 不会自动解除它们。首次训练是否纳入子 agent/压缩、哪些辅助模型调用入 loss，以及 MoE 路由能否准确回填，仍需按 I18/I19 单独决定和验证。

## 9. 下一步怎样取得足以决策的证据

先做一个窄对比，避免先投入长训练再凭总 reward 猜原因。

1. **收集一小批代表性真实请求。** 覆盖普通工具往返、system-reminder、长短响应与已允许的分支；压缩若仍被禁，可先用离线边界例子。记录点应在 `record_turn` 改写之前，否则旧 TurnRecord 已删，事后数 Sample 看不到损失来源。
2. **同一批完整采样记录分别重放 1024 和 0。** 使用独立的干净树，不能复用带 `response_trained` 状态的对象。这个对比不需要先跑两次不同的随机 rollout。
3. **输出一张小表。** 分开计数 token REALIGN / 消息 rewrite；列实际生成与保留的 turn/token、首轮及工具动作覆盖、按 reward/轮次/长度分层的缺失；同时列每 execution 的行数、总输入 token、最长行和重复前缀量。保留旧动作也会带回其旧权重版本，需看最旧版本与 staleness 准入损耗；不能为了让版本看起来更新而把旧动作隐式删掉。
4. **检查训练身份和计权。** 新增行仍属同一 member；相同采样事件只算一次；原始 prompt/输出/logprob/support/version 对得上；rollout 分母跨所有 sibling 正确计算；新增行不能因为长度上限或丢弃路径又消失。I18 的 MoE routing 来源另核，不能只看 tensor 形状。
5. **CPU 结果清楚后做窄 GPU 对拍。** 测真实 forward/packing/显存与 wall time，以及同版本 logprob 差异；通过后才用短训练比较学习质量。单次 replay 的 token 减少不等于端到端加速，少量 step 也不足以估计最终模型收益。

先看这些测量再选策略：

| 观察到的情况 | 我倾向的下一步 |
|---|---|
| 默认路径有重要动作缺失，0 的计算成本可接受 | 选精确合并/漂移拆行作为训练基线 |
| 0 导致普遍逐轮拆行、显存或吞吐明显受损 | 对占主流的模型＋harness 做在线追加/模板边界适配，并明确分支与压缩边界 |
| 默认缺失很少且集中于可解释冗余内容 | 可保留为受控消融选项；仍需证明保留它的成本收益，不因“上游默认”自动认可 |
| 仅某个模板设置或消息转换造成确定漂移 | 先检查能否在真实推理入口修正该局部原因；修正前后分别保存实际输入证据 |

不建议现在新增大量永久闸门、哈希对账或训练前缀树内核。先复用已有 capture 和身份体系，把“丢了什么”与“保留要花多少成本”测出来。

## 10. 本轮验证与未完成事项

- Production Tracer 核对生产入口、slime 历史/main/PR，并运行真实 vendor manager＋身份导出＋backfill 的 8 个 CPU 小例子。[探针](threshold_probe.py)、[作者运行结果](threshold_probe.txt)。
- 主审独立重跑这 8 案，exit 0；两类销毁路径均随阈值 0 关闭，CLEAN 仍合并。[主审结果](threshold_probe_root.txt)。这些小例子没有证明全链路 GPU 训练已支持该配置。
- 主审运行固定 Polar 类的合成输入反例与终局奖励数学例子，均 exit 0；Falsifier 独立检查了 Polar 条件前缀推导。
- 正文经过上述两名 reviewer 各一轮定点复核；已消除方案编号歧义，并将“mask=0”限定为所有训练行都没有可训练副本，收紧了梯度方向与分母系数的表述。
- 外部代码按提交定位；下载副本仅供本次证据核对，未替换任何运行依赖。正文对框架的结论均限定到所读路径。
- 本轮没有正式训练、Docker 作业、标准测试套件扩充、源码/配置修改、提交或推送，也没有新增 owner 定案。尚需选择的核心是：先以哪条路线建立真实采样与训练消费的基线，以及允许哪些 harness 上下文变化。

复现主审探针（从仓库根运行）：

```bash
PYTHONDONTWRITEBYTECODE=1 rh2/.venv/bin/python docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/i01_options_20260908/threshold_probe.py
python3 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/i01_options_20260908/conditional_prefix_probe.py
python3 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/i01_options_20260908/terminal_reward_probe.py
```
