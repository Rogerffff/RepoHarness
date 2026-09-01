# Miles GPU spike 实验范围（Claude + Codex 合并版）

日期：2026-08-31

状态：**合并候选版，待 Owner 确认本文第 8 节后生效**

本文合并以下两份输入：

- `miles_spike/gpu_spike_scope_v1_claude.md`；
- `tmp/miles_gpu_spike_experiment_scope_draft_20260831.md`。

本文只定义：**本次实验要回答什么、必须测试什么、为什么必须在远程八卡 GPU
上测试，以及每项结果能支持什么结论**。它不定义机器供应商、镜像制作步骤、
启动命令、任务 fixture、运行时长、数值阈值、证据文件格式或验收器实现。

现有 `launch.sh`、`thresholds.md`、`positive_control.md`、
`g1_acceptance.py` 以及旧 G0/G1/G2/G3 编号均不构成本文前提。本文经 Owner
确认后，下一轮必须从本文反向设计这些实现；旧文件中未出现在本文的默认值、
工具开关和验收语义不得自动继承。

---

## 0. 主问题、结论边界与实验组织

### 0.1 本次唯一主问题

本次 GPU spike 要回答：

> 当前 RH2 + Miles integration tree，能否在目标八卡硬件上，用真实 SWE agent
> 负载完整运行 Miles fully-async 训练链，并保持关键训练语义和系统行为正确，
> 从而让后续 fully-async 开发主线从未完成的 Slime FA 迁到 Miles？

主交付是：

```text
Development-Migration-Go
或 Conditional Go
或 No-Go / 回本地修复
```

`Development-Migration-Go` 的含义是：停止继续建设 Slime FA 主线，后续异步训练
infra 开发转到 Miles；它**不等于** RH2 已经可以正式长训。

### 0.2 当前 execution mode 决定了结论上限

当前实现中：

- `s1_compat` 会完成真实评分和训练交付，但不启用 FA 的
  `RuntimeQuiescenceBarrier`、冻结 artifact 和 finalization receipt；
- `fa_audit_only` 会在评分前返回 abort 样本，不能形成训练正链；
- `fa_formal` 是长期目标，但当前启动阶段仍会因前置未闭合而主动拒绝。

因此，本次主资格作业若采用 `s1_compat`，最多能证明：

> RH2 的真实数据/算法正链可以运行在 Miles fully-async 训练后端上，Miles 足以成为
> 后续开发主底座。

它不能证明：

- `fa_formal` 已验证；
- `rh2_s2_signal_trusted` 或 `rh2_formal_training_allowed` 可以翻转；
- 正式冻结评分、finalization receipt、checkpoint 冷恢复或无人值守长训已合格；
- 短跑 reward 能说明模型能力提升。

首次长训练资格应是迁移后的独立闸门，见第 7 节。

### 0.3 三类测试角色

- **【判定级】**：Development-Migration-Go 的硬门。未通过时不能用其他配置下的
  局部成功替代。
- **【数据级】**：为成本、拓扑、正式采样参数或后续阈值收集事实。缺少数据时，
  对应决策不能关闭，但不必把一个事先排除在主目标外的能力事后解释成失败。
- **【条件级】**：只在核心正路径已经完成后执行，或者只在失败时用于定位；不允许
  反过来给主资格作业“加分”。

### 0.4 防止“拼接式假绿”：一个主资格作业

最终 Migration-Go 不能由多套配置拼接得出。例如，不能用作业 A 的 R3、作业 B
的 faithful DIS、作业 C 的真实 SWE、作业 D 的 multi-span 合成“全链通过”。

必须有一个连续的**主资格作业**，在相同的：

```text
source/runtime identity
+ model/tokenizer
+ 八卡拓扑
+ sampling 配置
+ training objective 组成
+ pause mode
+ R3-on
+ RH2 execution mode
```

下同时闭合：

```text
真实 SWE / Claude Code / Docker / grading
→ RH2 capture、治理与分组
→ Miles 持续 producer 和 buffer
→ faithful DIS + R3 replay
→ 第一次真实非零 optimizer update 与 publish
→ 一个在途的单 HTTP 请求跨过该 publish，产生 multi-span
→ 该 multi-span 样本进入后续 actor loss
→ 第二次真实非零 optimizer update
→ 新版本继续 rollout
→ 系统正常停止并自行清理
```

全局零信号负控可以是同一 runtime、拓扑和训练 driver 上的独立伴随探针；失败定位
探针可以另跑，但两者都不能替代主资格作业。

本次 Migration-Go 还受当前 faithful DIS 实现的明确支持边界约束：主资格作业使用
faithful-DIS policy objective only、默认 actor-group trainer、`CP=1`，并关闭
`calculate_per_token_loss`；`MILES_EXPERIMENTAL_FT_TRAINER` 必须未启用。MTP、OPD、
KL、entropy 和 MoE auxiliary 等 objective 不混入本次资格 update。这个限定是为了
让 Q3/Q5 的 loss 与梯度归因可解释，并如实反映当前实现能力；它不决定未来正式训练
永远不能启用其他 objective、trainer 或并行配置，后者需要单独扩展资格。

---

## 1. 已有证据如何复用

### 1.1 本地阶段已经证明的部分

当前本地 spike 已经覆盖：RH2/Miles 数据形状和身份转换、版本区间 parser、
sampling mask 与 R3 tape 的 dtype/shape、faithful DIS 标量公式、dynamic filter、
buffer 状态机、单进程零信号状态冻结、vendor patch 重建和双 lane 测试。

这些单元级与负例矩阵不应在租卡后完整重跑。GPU 实验要证明的是：这些语义跨过
真实 SGLang、Ray、Megatron、CUDA、NCCL 和多 rank 边界后仍然成立。

### 1.2 P3 可以提供历史数量级，不能替代 Miles 资格

P3 已在 8×RTX PRO 6000（sm_120）上证明同类 30B MoE 训推分区可以落卡，并给出：

- 完整 step 约 1387 秒；
- trainer 等 rollout 的比例约 0.82；
- harness 时长约 280～1116 秒；
- 尾部 GPU 空闲约 26%～28%；
- 同类 checkpoint 约 380～399GB，保存约 373 秒。

这些数据说明 fully async 有明确成本动机，也可作本次资源和墙钟 sanity check。
但 P3 使用的是旧 Slime/SGLang 组合，并曾暴露治理过滤后 batch schedule 与 GRPO
分组语义问题；它不能作为当前 Miles integration tree、当前 kernel 组合、R3 replay
或 faithful DIS 的通过证据。

### 1.3 远端实际运行身份必须是受审查的树

主作业必须记录并核对实际 import 到的 RH2、Miles、SGLang、Megatron、镜像、
kernel wheel、模型和 tokenizer 身份，以及工作树是否有未登记修改。只写一个预期
commit，或在远端临时修补后继续沿用旧证据，都会破坏迁移结论。

现场若修复普通 build/wheel 问题，应产生新的不可变运行身份并重新执行受影响的
主资格范围；不同 build 的证据不能无说明拼接。

---

## 2. 为什么必须使用远程八卡 GPU

目标不是证明 Python 接口能 import，而是验证训练与推理同时常驻的 30B
fully-async 系统。少量卡加额外量化、offload 或 colocate 会改变显存、权重传输、
训推重叠和长尾问题，不能替代目标部署资格。

| 必须回答的问题 | 本地为什么无法给出结论 |
| --- | --- |
| 当前 30B 训推栈能否同时装入并执行 | 本地没有目标 sm_120/CUDA 环境，也没有训练权重、optimizer state、推理权重与 KV cache 的组合显存压力 |
| Megatron 多 rank 训练是否正确 | TP/DP/EP/PP、NCCL collective、MoE dispatcher、混合精度 optimizer 和 rank 间一致性不能由 world-size=1 stub 证明 |
| SGLang 是否真实生产 sampling support、spans 和 R3 tape | 本地只能构造 wire 数据，不能证明目标 GPU sampler 和更新路径真的产生这些事实 |
| faithful DIS 是否使用真实模型分子/分母 | 本地 current logprob 来自构造 logits 或小模型，未执行 30B Megatron forward、GPU softmax 和分布式归约 |
| R3 是否被真实 MoE forward/backward 消费 | CPU shape 测试只能证明 tape 到达 trainer 门口，不能证明 replay 队列在 forward、backward recompute 中被消费并耗尽 |
| 单请求跨真实权重发布是否成立 | 需要真实参数改变、权重传输、SGLang pause/retract/resume、KV 重算和仍在途的 HTTP generation request |
| fully async 是否真的穿越 SWE 长尾 | 只有真实 30B generation、SWE 执行、trainer、publish 的墙钟竞争才能证明区间重叠和快任务越过慢任务 |
| 全局零信号能否跨 rank 安全跳步 | 需要真实 CUDA 梯度、collective、Megatron optimizer/scheduler 和 driver publish gate 共同运行 |
| 系统能否自行退出 | Ray actor、CUDA context、HTTP 请求、Claude Code 子进程和 Docker container 的真实清理无法由桩进程证明 |
| 成本是否可接受 | GPU-hour、有效 group 产量、显存/RAM/object-store 水位、尾部空闲和 tape 开销没有可信的本地替代 |

Claude Code、Docker 和 grading 单独并不是“只能在 GPU 上测”。它们进入八卡主作业，
是为了验证它们与真实 30B generation、Ray transport 和分布式 trainer 连在一起时的
纵向正链，而不是为了在昂贵机器上重跑 sandbox 单元测试。

---

## 3. 主资格作业：Development-Migration-Go 的硬范围

### Q1【判定级】目标运行栈、资源闭包与引擎三类一手事实

**测试内容**

在一个 Owner 批准的八卡候选拓扑中，同时启动并保持目标 30B-A3B、Miles
fully async、SGLang、Megatron、Ray、真实 RH2 generate、Claude Code harness 和
Docker/grading，并至少完成一条真实请求。训练侧 attention、MoE、optimizer、通信
kernel 都必须实际执行，不能以编译或加载成功代替。

同一 SGLang engine 必须真实返回：

1. sampling support mask 与 support-normalized behavior logprob；
2. SGLang 原始 `meta_info["weight_versions"]`，以及 RH2 规范化后的单请求
   `weight_version_spans`；
3. 非占位 R3 routed-experts tape。

同时记录每卡显存、host RAM、Ray object store、磁盘和容器水位。

**原因**

当前栈与 P3 的 TE、FA2、SGLang、Megatron 组合不同；P3 的 sm_120 结果只能说明
“重编 kernel 的方法曾经可行”，不能证明本次实际组合可执行。三类数据又是后续
版本记账、faithful DIS 和 MoE replay 的共同输入；任何一类只在 fixture 中存在，
后面都可能整体假绿。

### Q2【判定级】真实 RH2 端到端、credit assignment 与过滤后补采

**测试内容**

主作业必须真实运行：

```text
SWE task
→ 独立 Docker workspace
→ Claude Code 多轮模型调用与工具执行
→ SGLang generation
→ capture / stage / commit
→ 独立 grading container
→ projection / Eligibility / prompt-group assembly
→ Miles 持续 worker / buffer
→ train-data conversion
→ faithful DIS + R3
→ optimizer / publish
```

不能用手工构造 `Sample` 替代前半段。至少同时包含：

- **普通真实 SWE workload**：用于证明实际任务链和长尾；它必须完成真实
  Claude Code、sandbox 和 grading，并根据 reward 事实被正确交付、过滤或消费。
  若自然产生非全等奖励 group，该 group 必须真正进入 trainer；若早期模型只产生
  全等奖励，正确的 dynamic-filter drop 也算链路事实，不能因为模型未解题而把 infra
  判为失败。非零 update 的确定性硬门由下一项受控 group 承担。
- **受控非零信号 groups**：至少形成两个 reward 形状有区分力的 prompt group，
  使正确的组内 normalization 与错误的跨组 flatten 会产生不同结果。它们仍走真实
  SWE environment、真实 Claude Code、真实 sandbox 和正常 grading boundary；必须
  产生可解释的 reward 方差、有效 provenance token 和 `accepted_tokens > 0`，并能
  分别归因到实际 applied batch。禁止直接写 `Sample.reward`。
- **真实 dynamic-filter drop + 补采**：至少一个完整 group 被正常过滤路径拒绝，
  持续 producer 随后补足一个满足真实 DP/microbatch schedule 的训练 batch，并成功
  update。不能手工准备一个恰好整除的 batch 绕过该边界。这是 P3 曾经失败的真实
  状态边界。

实际入训轨迹还必须覆盖两个已经本地修过、但尚未跨真实 SGLang/CC 链证明的形态：

- 工具调用后的 observation token 使用单例 sampling support，且 loss mask 与 token
  行对齐；
- 至少一次真实 rewrite/drop 轮经过 capture identity、叶链线性化和 projection 后，
  没有把已丢弃轮的 logprob/version/support 串到存活轮。

这两项不要求 fan-out。

至少抽取一个实际入训 leaf，沿稳定 identity 联结：

```text
execution / leaf
↔ workspace
↔ final.patch digest
↔ grading input 与结果 artifact
↔ reward
↔ Miles Sample
↔ trainer batch leaf
```

并在新的独立 grading container 中复核一次该 leaf 的 reward。可以复用现有 identity
和 artifact，不要求为 spike 新建正式 ledger；但不能只证明每一段“数量相等”。

每个进入 applied batch 的 assistant token 还必须能回溯到本次目标 SGLang engine
的具体 request、token、logprob、sampling support、weight-version span 和 R3
provenance。外部 provider 或 fallback 产生的 token 不得混入本次训练资格 batch；
否则“真实 SWE 跑通”和“目标 engine 完成训练”可能来自两条不同链路。

**原因**

真实早期 SWE reward 可能全为 0；如果没有经正常环境与评分链产生的非零正控，无法
区分“模型没解出任务”和“trainer 没收到训练信号”。反过来，如果只运行短正控，
而普通 SWE 没有完成到 grading 和正确的 filtered/consumed 终态，也不能证明实际
workload 已经闭环。过滤后补采则直接验证此前 P3 的 batch schedule 阻塞在 Miles
持续队列下已经真正关闭。

### Q3【判定级】GRPO 分组与 faithful DIS 的真实分布式对拍

**测试内容**

从实际入训 artifact 一直核对到 Megatron loss：

1. 至少选取两个 reward 形状有区分力的 prompt group，按原始 `group_index` 和 reward
   独立重算 GRPO normalization/advantage；错误地跨 group flatten 时必须会得到不同
   结果。
2. 资格作业使用 Owner 批准且 `top_p < 1` 的 sampling 配置，sampled token 全部在
   对应 support 内。
3. behavior logprob 使用 T0-B 已定的 support-normalized 正式列；full-vocab logprob
   只作诊断。trainer current logprob 必须在同一 support 上重新归一化。
4. 在同权重版本下，behavior/current ratio 应在下一轮预注册的硬件数值容差内接近
   1；不能要求浮点字面相等。旧版本或 multi-span 样本应形成真实 ratio。
5. 使用真实 batch 独立重算最终 faithful DIS 标量，并对拍 trainer 实际输入。
6. 至少包含 provenance 长度不同的多个 execution，并跨 microbatch/DP 分片，证明
   execution 等权，而不是错误的全 token 扁平平均。
7. 受控正信号 group 自身必须存在接受 token，并实际贡献到 applied step；不能仅仅
   与另一个有效 group 同批后借用其梯度。
8. loss、grad 和各 rank 归约结果有限、一致。

主资格作业显式关闭 speculative decoding；当前 sampling-mask 纵链尚未资格化 spec
decode 的 token 计数与 support 语义，不能把它作为一个未声明变量混入结果。

GPU 负责产生真实 SGLang/Megatron artifact；独立标量重算、交换 group/leaf tape、
损坏 support 后必须拒绝等验收器自证应在 artifact 下载后本地完成，不占八卡时间。

**原因**

finite loss 不是正确性证明。support 错一位、behavior 用成 full-vocab 值、GRPO 跨组
归一化或 execution 分母被扁平化，都可能继续产生有限数值，但训练目标已经改变。

### Q4【判定级】R3-on 真实 MoE routing replay

**测试内容**

主资格作业从第一条训练路径起保持 R3-on，并证明：

- SGLang 真正生成非占位 routed-experts tape；
- tape 与 leaf identity、token 行和 source digest 精确联结，叶间对调不能假绿；
- RH2 转换后的 dtype/shape 和 ownership 满足 Miles/Megatron 合同；
- 拥有相应 MoE 层的 trainer rank 在 logprob forward、训练 forward 和 backward
  recompute 中实际消费 tape；
- replay 队列最终耗尽；
- 至少一个真实 applied update 与该消费事实联结。

R3-off 只允许在 R3-on 失败后用于定位，不能产生 Migration-Go。

**原因**

R3 是本项目选择 SGLang/Megatron 路径的重要原因，也是 30B MoE 训推一致性的必要
部分。只把 tape 运到 trainer 门口不能证明它改变了真实 forward/backward 路由。

### Q5【判定级】真实 publish、单 HTTP 请求 multi-span 与权重内容一致

**测试内容**

主作业至少完成两个非零 applied optimizer update。两个 step 不是稳态性能的充分
长度，但它们构成下面的最小版本闭环：

```text
v_k 的真实非零 group 完成 step 1
→ 参数改变并发布 v_k+1
→ 一个已经生成部分 token 的单 HTTP request 跨过该 publish
→ 请求产生至少两个非空、连续、无重叠的 spans
→ 该 multi-span sample 进入后续 actor loss，并有接受 token/实际梯度贡献
→ step 2 完成并发布后续版本
→ 新 request 使用新版本继续 generation
```

multi-span 不能靠随机等待碰运气，也不能用同一 agent execution 中的两个 HTTP 请求
冒充。需要确定性触发，并核对：

- spans 只覆盖该 HTTP request 本次生成的 token；
- capture、`Sample.weight_versions`、buffer oldest version 和 trainer 证据逐层一致；
- support mask、behavior logprob 和 R3 tape 在 pause/update/resume 后仍逐 token 对齐；
- 没有重复 turn、评分、入队或消费。

发布侧还必须证明：

- bootstrap 初始同步与训练后 publish 被区分；
- applied optimizer step、update 调用、publish 和 version 符合实际 interval 守恒；
- 全 skip 区间不发布、不增加 version；
- 至少一次训练后 publish 确有参数变化；
- 启用 Miles 现有的完整 trainer→SGLang weight-equality checker，完成全参数名闭包和
  每个映射 tensor 的一致性检查；任何 skip/tolerance 都必须预先批准且无未解释参数。

本轮只资格化一种 pause mode；`retract` 与 `in_place` 不能互相借结果。

**原因**

版本号递增并不能证明权重完整到达。单请求 multi-span 又是 fully async 最危险的
版本边界：若只保留尾版本，前段旧 token 的 lag 会被低报，DIS 和审计也会失去真实
来源。

### Q6【判定级】持续 producer、真实训推重叠与长尾穿越

**测试内容**

使用单调时钟的一手事件证明：

```text
冷启动，buffer 为空
→ 持续 producer 产生多个 group
→ trainer 消费已完成 group
→ trainer forward/backward 时仍有 generation 在途或新 group 完成
→ 快 execution 在慢 SWE execution 尚未结束时进入下游 filter/buffer，若合格则训练
→ publish 时仍有受控在途请求
→ publish 后 producer、buffer、trainer 继续推进
```

任务集合必须包含真实的明显长短差异；不要求用 subagent 或 fan-out 人工制造长尾。
两个短正控 update 只能证明版本闭环，不能证明 fully async 稳态。warm-up 后还必须有
一个预注册观察窗口，覆盖连续多个 publish cycle；普通真实 SWE group 要持续完成并
按 reward 事实进入 filtered 或 consumed 终态，受控 group 则持续提供可归因 update，
且 queue/staleness 不持续单调增长。具体 cycle 数和时长在下一轮阈值设计中确定。

队列还要满足全局守恒：每个 produced group 最终恰好进入 filtered/rejected、仍在
pending，或 consumed 其中一类；任何 admitted group 最多消费一次。正常结束时 pending
项按 Q8 的 cancel/discard 规则收口，不能靠只检查 multi-span 样本隐藏其他重复消费。

**原因**

P3 的实际成本问题是 280～1116 秒 rollout 长尾和 26%～28% 尾部空闲。只设置
`--fully-async`、保持 engine actor 不变或预取一个完整 batch，都不能证明持续生产
真的让快任务越过慢任务。

### Q7【判定级观测 + 数据级策略输入】staleness 四时点真值

**测试内容**

版本事实按 group 真正到达的阶段记录，不能强迫一个在 put 前被过滤的 group 携带它
结构上不可能拥有的 trainer 字段：

```text
所有完成 group：
  oldest_behavior_version
  buffer_put_attempt_version
  buffer_put_decision（filtered / admitted / rejected / ...）+ reason
  final_destination（filtered / buffered / trained / ...）

dynamic-filter drop：
  drop reason
  buffer_get_decision_version = NOT_APPLICABLE
  trainer_pre_forward_version = NOT_APPLICABLE

真正进入 buffer 的 group：
  buffer_get_decision_version
  buffer_get_decision（keep / drop / retry + reason）

真正进入 trainer 的 group：
  trainer_pre_forward_version
```

`NOT_APPLICABLE` 必须是明确阶段状态，不能用普通 `null` 混淆“未到达后续阶段”和
“证据缺失”。
据此给出真实 lag、multi-span 和 DIS 接受分布，并证明版本事实没有负 lag、低报或
不可解释跳变。

当前 `train_async.py` 会在训练当前 batch 时预取下一批。下一批可能在旧版本下完成
buffer-get 判定，当前 batch 随后发布新版本，预取批才进入 trainer；因此 get 时
lag=`k` 的边界 group，在 pre-forward 时可能已是 `k+1`。buffer-get 版本不能冒充
trainer consumption 版本。

**本次建议的分期**

- Development-Migration 主作业只采集和核对上述事实，不启用在线
  `max_weight_staleness` 硬拒绝；
- 正式 staleness gate 仍以 trainer consumption 时点为准，首次长训前另行资格化；
- 版本区间只用于 staleness/记账，faithful DIS 的 token 接受仍由真实
  behavior/current ratio 决定，不能用版本号直接替代。

若 Owner 预先确认这一分期，未测试在线硬拒绝不自动把 Development-Migration-Go
降为 Conditional；但观测缺失、时点串账或真实 lag 无法解释仍是主资格失败。

**原因**

本地可以构造版本号，却无法形成持续 producer、buffer 预取、trainer 和 publish 的
真实 interleaving，也无法获得目标 workload 下的 lag 分布。

### Q8【判定级】正常停止与系统自行清理

**测试内容**

主作业正常停止后，在预注册 deadline 内、外部强杀之前，证明：

- 系统先停止新增 dispatch；
- Ray job、SGLang engine、rollout/grading worker、Claude Code 子进程和 Docker
  sandbox 已退出；
- GPU 显存释放；
- 无仍可能继续执行或稍后误入训练的 HTTP request、pending capture draft 或孤儿
  容器；
- shutdown 时尚未消费的 active/buffer item 不要求全部训练完，也不要求可恢复，但
  必须逐类得到 `drained` 或显式 `discarded` 终态，并留下数量、identity 和 reason，
  总数守恒，不能成为账外工作；
- `s1_compat` 下只能证明进程退出前可查询的内存态没有 pending capture draft；没有
  durable finalization receipt，不能把这一项表述成正式 finalization 已通过；
- 系统给出明确完成/失败状态，而不是无限等待。

只有固定完系统自身 verdict 后，租卡 wrapper 才允许执行 `ray stop --force`、kill 或
Docker 删除作机器兜底清理。兜底后的“零进程”不能洗绿系统自身的 hang 或泄漏。

**原因**

持续 worker 是 Miles fully async 的核心组成。只能启动、不能干净停止的系统不适合
成为后续开发主底座；本地 asyncio 桩也无法证明 CUDA/Ray/HTTP/Docker 资源会释放。

### Q9【判定级容量 + 数据级成本】至少一个可接受的八卡部署范围

**测试内容**

至少一个 Owner 批准的八卡拓扑必须完成 Q1～Q8，并同时采集：

- 冷启动和模型加载时间；
- 有效 group、训练 provenance token、applied update 的单位 GPU-hour 产量；
- trainer wait、rollout wait、真实重叠时长和尾部 idle GPU-card-seconds；
- generation、actor train、pause/update/resume 的分段墙钟；若本配置实际启用
  reference-logprob 阶段则单列，否则明确 `NOT_APPLICABLE`；
- queue size、在途 group、filter/drop/retry、staleness；
- 每卡利用率、显存、功耗，以及 host RAM、Ray object store、磁盘峰值；
- real-SWE、受控非零组和零信号探针各自的完成曲线与成本；条件级故障探针若执行则
  单列，若未纳入则明确记为 `not_run_by_scope`；
- 权重更新导致的重算/作废 token 和 request 成本；
- sampling mask 与 R3 tape 的 support cardinality、bytes/token、bytes/group，以及
  capture、canonicalize、序列化、Ray 传输、train conversion 的主要开销。

不能把短正控的高产量与普通 SWE 混成一个平均数。功能正确但每个有效 update 的
成本不可接受，也不能支持迁移；具体数值阈值应在下一轮运行设计中于租卡前批准。

**拓扑边界**

本文不自动继承旧脚本的 6+2 或 4+4：

- 一个主拓扑完整通过是框架迁移硬门；
- 第二拓扑只有在本次还要同时决定首训卡数分配时，才在主路径成功后做短 matched
  window；它是成本决策实验，不是框架正确性硬门；
- 当前单 engine 通过只能资格化单 engine 部署范围，不能外推多 engine；
- 若 Owner 要求首次训练立即使用多 engine，应先闭合 router affinity/abort/version
  查询，再把它纳入新的硬范围。

当前先验只能用于选实验顺序，不能代替数据：P3 workload 明显 rollout-bound，
所以更多 rollout 卡可能有利；但 4+4 当前对应一个 TP4 engine，6+2 又减少 rollout
资源。主拓扑和第二数据点的准确选择留第 8 节确认。

---

## 4. 伴随硬探针：全局零信号语义

### Z1【判定级】正常 step → 全局零梯度 step → 正常 step

这个探针可复用已经启动的同一 30B trainer，不需要为零信号再支付一轮完整 SWE
rollout；但它必须使用与主资格作业相同的 build、拓扑、Megatron optimizer、训练
driver 和 publish 路径。

顺序为：

```text
真实非零 step，先形成 optimizer momentum
→ 所有 microbatch/backward/rank reduction 完成后的全局 total gradient 精确为零
→ 后续真实非零 step 正常恢复
```

中间零信号 step 必须证明：

- 所有 trainer rank 一致判定 `SKIPPED_ZERO_SIGNAL`；
- 零贡献 microbatch 只继续累积，不在 microbatch 粒度抛错；
- batch 被消费，但 optimizer call/progress、Adam state、scheduler、训练权重和 engine
  version 均不前进；
- 不调用 publish；
- 系统不 hang，后续非零 step 可以再次更新和发布。

正常 step 的各计数按各自真实语义核对，不能笼统要求“全部 +1”：optimizer/Adam
通常按 applied step 前进，scheduler 可能按 `num_rollouts` 前进，weight version 按
实际 publish interval 前进。

零梯度扫描自身的墙钟开销在本探针中顺带采集，决定以后是否需要 fused 优化，不另
开昂贵专项。

**目标组成限制**

zero scan 判断的是 **total gradient**。本资格探针建议只启用 faithful DIS policy
objective，并关闭会独立产生梯度的 MTP、OPD、KL、entropy、MoE auxiliary 等项。
这只是为了让零信号 oracle 可解释，不等于提前决定正式训练算法。若本次同时启用
其他 objective，必须先由 Owner 重新定义“零信号”究竟指 policy signal 还是所有
objective 的 total signal。

reward 全等 group 的 dynamic-filter 语义已经能在本地测试；主作业 Q2 只需验证一次
真实过滤后补采。本探针验证的是不同边界：已经进入 trainer 的全局零梯度 step。

---

## 5. 数据级与条件级附加项

### 5.1 sampling-support 成本回填【数据级】

已定 T0-A 是：本次硬件 spike 主配置暂用
`top_k := effective vocabulary size`，实测 mask、显存和吞吐后再决定正式训练采样
配置。该决策不在本文重新打开。

主作业必须采集 Q9 中的 support/tape 成本。主作业成功后，可追加一个较小有限
`top_k` 的短诊断点，用来估计缩小 support 的收益；Claude 草案提出 `top_k=32`，但
它只是候选数据点，是否采用及其运行长度在下一轮运行方案中确认。这个诊断不能替代
主配置的训练语义资格，也不能单独产生 Migration-Go。

`temperature/top_p/min_p` 的准确值仍需在运行方案中确认；无论取值如何，主资格必须
真实启用截断 support（`top_p < 1`）并保持生成侧和训练侧参数一致。

### 5.2 第二拓扑【数据级，可选】

只有 Owner 希望本次同时裁决初始卡数分配时，才运行第二个短 matched window。
两边使用相同 workload 语义、sampling、预算和计量口径；因训练/rollout 卡数不同，
并行参数可按可行性调整，不能要求字面相同。

第二拓扑失败不会推翻已在批准主拓扑上成立的框架语义，但会把支持范围限制在主拓扑，
并影响生产拓扑决策。

### 5.3 真实 actor 故障【条件级，可选】

在全部核心正路径证据固定后，可以终止一个有在途请求的 rollout/SGLang actor，验证：

- 残缺数据不进入训练；
- 作业按当前承诺明确 run-fatal，不无限 hang；
- 最终能清理 GPU、Ray、HTTP 和 Docker 资源。

这只证明故障隔离，不证明 actor 自动恢复。自动重建、exactly-once 和 mid-flight
recovery 属于首次长训闸门。

### 5.4 失败定位探针【条件级，只在失败时】

- R3-on 失败后，可用同配置 R3-off 区分基础训练与 routing replay；R3-off 下相应
  routed-experts 字段必须明确为 `None`，不能残留旧 tape。R3-off 不给 Go。
- 目标栈失败后，可运行最小 kernel、SGLang 或 stock Miles probe，区分机器、上游与
  RH2 adapter。
- 不默认运行 Slime FA matched 对照；旧 Slime FA 尚未接完，不能在租期中假装直接
  切换。只有一条预先确认可执行的 P3 基础 smoke 才可作为机器诊断，且不能用来声明
  Slime/Miles 性能优劣。

任一早期硬门失败后，不应在 GPU 现场大段改业务代码。应保全 artifact，判断是可快速
闭合的部署问题还是需要回本地修复；后者应尽早释放机器。

---

## 6. 明确不纳入本次 Development-Migration 硬门

- S2 安全与 signal-trusted、正式训练闸门翻转；
- `fa_formal` 解禁、正式冻结评分与 finalization receipt；
- checkpoint 冷恢复、active/buffer 持久化、exactly-once 或自动 actor recovery；
- 多节点、多 engine、弹性容灾、长时间无人值守 soak；
- 两种 pause mode 同时资格化；
- R3-off 主资格；
- Slime matched 性能 A/B；
- before/after 模型能力结论；短跑只需证明新权重可推理；
- 强制把 buffer 塞满的远程故障战役；容量、cancel、唤醒等状态机负例继续留本地；
- 完整 governed-buffer/ledger 治理系统；
- 所有 CP/VPP/DeepEP/FP8/量化组合矩阵；
- 强制 multi-leaf fan-out、FORK、compaction 或 subagent 工具。

最后一项需要特别说明：GRPO 的多个独立 rollout 不等于一次 agent execution 分叉出
多个 leaf。本次是否启用 subagent、FORK/compaction 和相应工具面，必须来自 Owner
确认的 harness profile，不能由旧 `launch.sh` 默认。如果批准的 profile 自然产生
multi-leaf，主链必须正确处理；但没有产生 fan-out 不构成“未执行”，也不需要人为
促发或申请豁免。本地已有 fan-out 形状契约测试，未来真正启用该 harness 语义时再设
远程扩展资格门。

---

## 7. 本轮之后仍需单独关闭的首次长训练闸门

若第 3～5 节全部通过，只能得到 Development-Migration-Go。要进一步声称
Miles/RH2 backend 已可作为首次长时间训练候选，至少还要另行完成：

1. `fa_formal` 最小解禁与正式治理正链；
2. trainer-consumption 时点的正式 staleness gate，以及阈值和 drop/retry 语义；
3. 一个明确的 checkpoint/quiescence/recovery 协议；
4. active task、completed buffer 和 data-source cursor 的可审计恢复边界；
5. 生产所需拓扑、engine 数和故障承诺的资格；
6. 独立的 S2 signal-trusted 与安全闸门。

Miles 当前并不持久化 fully-async active tasks 和 completed buffer。为了决定是否迁移
开发主线，不应现在先建设 quiescence、inventory 或 exactly-once ledger；不做这些，
就必须诚实地把 checkpoint/cold-resume 标为未资格化，不能把普通 checkpoint 文件
可读冒充完整恢复。

---

## 8. 写运行环境、脚本与验收器前需由 Owner 确认的事项

### 8.1 已有决策与已知实现硬约束，本文不重新打开

1. **T0-A**：硬件 spike 主配置使用
   `top_k := effective vocabulary size`；根据实测成本再决定正式采样配置。
2. **T0-B**：`behavior_support_logprob` 是 faithful DIS/TIS 正式分母；
   `model_full_vocab_logprob` 只作诊断。
3. **F2 零信号语义**：dynamic filter 在 trainer 前过滤等 reward group；trainer 在
   optimizer 边界按全局 total gradient 判断 skip，不在单 microbatch 抛错；全 skip
   不推进 optimizer/scheduler/version/publish，并可继续后续训练。
4. **R3-on 是迁移硬门**：R3-off 只作定位。
5. **sampling-mask 当前不支持 spec decode 资格**：主作业显式关闭 speculative
   decoding；这是已知 integration 约束，不是由旧启动脚本继承的默认值。
6. **当前 faithful DIS 资格支持面**：默认 actor-group trainer、`CP=1`、
   `calculate_per_token_loss=False`，且不启用 `MILES_EXPERIMENTAL_FT_TRAINER`。
   超出这组实现边界需要另做扩展资格，不能用本次结果外推。

### 8.2 仍需确认的语义与支持边界

1. **主结论强度**：建议按本文只做 Development-Migration；若要求本轮直接得到
   长训资格，需要先增加第 7 节的本地开发与 GPU 范围。
2. **execution mode**：建议接受 `s1_compat` 的 pre-formal 边界，不用
   `fa_audit_only` 冒充训练，也不为迁移决策提前解禁 `fa_formal`。
3. **pause mode**：建议主资格先用 `retract`。它会重算 KV，语义更保守；
   `in_place` 在 RH2 custom request 路径上仍有 KV/weight-version 隔离适配前置。
4. **staleness**：建议本次只采集四时点，不启用在线硬拒绝；首次长训前再按
   trainer-consumption 语义资格化。若本次就启用阈值，租卡前必须先补 consumption
   时点二次准入。
5. **harness profile 与 taskset**：subagent、FORK/compaction、工具面、SWE 任务、
   受控非零信号 group 和长短任务构成必须显式确认，不能继承旧脚本。
6. **训练 objective**：主资格作业和 Z1 均使用 faithful DIS policy objective only；
   这不决定未来是否加入 MTP/OPD/KL/entropy/MoE auxiliary，而是保证本次
   advantage、loss、梯度和 applied update 可以归因。
7. **主八卡拓扑与支持 engine 数**：至少选一个真实候选拓扑；确认单 engine 是否
   足以支持本次迁移结论，以及是否需要第二拓扑数据点。
8. **sampling 其余参数**：确认主配置的 `temperature/top_p/min_p`，以及是否追加
   较小 `top_k` 诊断点。
9. **故障范围**：正常 shutdown 是硬门；确认本轮是否追加 actor-kill run-fatal
   隔离探针。自动恢复不在本轮。

这些确认的目的不是扩大 T0，而是防止实现阶段把一个普通参数默认值悄悄升级为训练
语义或支持承诺。

---

## 9. 结果如何映射到迁移决策

### Development-Migration-Go

满足以下条件：

- 同一主资格作业完整通过 Q1～Q9；
- Z1 全局零信号探针通过；
- 没有依赖 R3-off、手工 `Sample`、直接注入 reward、只增加版本号或外部强杀清理等
  绕行；
- 资源/成本达到下一轮预注册的可接受范围；
- 所有未测能力都已在实验前明确排除，并写成支持边界。

结论：后续 fully-async 开发主线迁到 Miles，Slime FA 保留为历史回退面，不再并行
建设同一套异步基础设施。

### Conditional Go

只用于：已经纳入 Development-Migration 目标的必测项证据仍不完整，或只能依赖一个
明确的临时绕行，但核心架构没有被证伪。必须写清限制、补齐责任人和重新开闸条件。

一个能力如果在实验前已被排除，例如 checkpoint、multi-engine 或 actor 自动恢复，
不能事后既用它把结果降成 Conditional，又声称整体已经通过。

### No-Go / 回本地修复

出现以下任一情况：

- 目标 30B 训推栈在批准硬件范围内无法稳定运行；
- 真实 RH2 E2E、过滤后补采或 credit assignment 无法闭合；
- faithful DIS、GRPO 分组、R3 replay、multi-span、权重发布内容、全局零信号等核心
  训练语义失败；
- fully async 没有真实重叠/长尾穿越，或 queue/staleness 持续发散；
- 正常停止依赖外部强杀，或单位有效 update 成本超过预注册范围。

普通 wheel/kernel build 问题不应第一次失败就被夸大成框架 No-Go；但修复后必须以新
运行身份重跑受影响硬门。若确认需要本地开发，应释放 GPU，回本地决定修 Miles
integration 还是恢复 Slime FA 剩余工作；不能假设租期内可直接切到尚未接完的
Slime FA-5。

---

## 10. 本文确认后的下一轮

```text
Owner 确认第 8 节
→ 选择主拓扑、harness/task fixture 与 sampling/pause 语义
→ 冻结远端 runtime/source/build identity
→ 为 Q1～Q9、Z1 定义一手证据和数值阈值
→ 重写或逐项映射 launch / collector / acceptance
→ 用本地反例证明验收器不会假绿
→ 再租卡
```

下一轮应优先把一次主资格作业和一个 Z1 伴随探针做成最小可执行实验包；条件式诊断
只在相应失败后启动。这样既能获得足以决定是否迁移的完整证据，也不会为了本次
spike 提前建设 checkpoint、formal governance、multi-engine 或完整恢复系统。
