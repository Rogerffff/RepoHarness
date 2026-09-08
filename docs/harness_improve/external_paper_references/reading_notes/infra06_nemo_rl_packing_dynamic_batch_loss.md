# Infra06 · NeMo RL：packing、动态 batch 与分布式 loss 消费

**精读日期：2026-09-08。** 这是绑定源码版本的系统专题，不是 NeMo 全仓审计，也不是某份 Nemotron 报告的实验复现。本文沿真实配置与训练入口，追踪原始序列如何变为 DP shard、microbatch、packed/CP 张量，最后怎样进入损失、梯度累积和参数更新。

**核心结论：packing 的正确性不是“token 没丢”这么简单。** 它同时依赖优化步边界、序列与概率字段的对应关系、跨 rank 调度、样本边界、全局分母，以及后端 reducer 的缩放。当前 NeMo RL 对主损失做了明确的全局归一化；但不能因此推出每个可选辅助项、每种模型或每种数据面均自动等价。本次找到了一个可选正样本 NLL 局部分母的具体反例，也确认了一个置换文档问题并未被当前 TQ 调用消费。

已运行 **10 个独立 CPU 语义探针**，全部满足其预期断言，包括负对照。它们不导入 NeMo，不执行 Transformer、NCCL 或 GPU kernel，不是上游测试通过证明。代码、结果与覆盖边界均保存，供进一步复核。

导航：[版本与覆盖](#scope) · [实际入口](#entry) · [规划与调度](#planning) · [packed/CP 布局](#layout) · [损失与缩放](#loss) · [流式消费](#streaming) · [发现与反例](#findings) · [测试证据](#tests) · [项目意义](#project)

<a id="scope"></a>
## 1. 来源、版本与阅读边界

### 1.1 固定版本

| 来源 | 固定版本与用途 |
| --- | --- |
| **NeMo RL** | `NVIDIA-NeMo/RL@13182a5f24a47856aa9191f651510d0df249c9c0`；本次 main 快照，提交时间 2026-09-08；所有 C 链接固定此版本 |
| **Megatron Bridge** | 沿上述版本的 gitlink 取得 `NVIDIA-NeMo/Megatron-Bridge@5ed97996cc2b422904d18179375b6d7366915097`；只用于确定依赖与框架职责，不称作完整阅读 |
| **Megatron Core** | 再沿 Bridge 的 gitlink 取得 `NVIDIA/Megatron-LM@1e7598cbfae888cdd3d741a351aae588d56f66c0`；定点核查 pipeline scheduler 的 loss 缩放，避免仅相信调用方注释 |
| **官方文档** | 主读同一 NeMo RL commit 下的设计 Markdown；发布站的 latest/nightly 只作交叉定位，不能覆盖已固定的代码事实 |
| **RepoHarness 项目映射** | 连接器可见的 `miles-migration@da82518af1de11ebe6fa054c0cb7b73f9502a0a0`，其中 CURRENT-STATE-BRIEF 更新于 2026-09-05；不是用户所说但本轮未能辨认的新工作分支 |

本轮两次分支列表与一次分支搜索均仅看到 `main`、`miles-migration`、`codex/repo-harness-verl-stage0h`。因此没有把任何一个旧分支冒认为用户的新分支；成果采用隔离的文档分支交付，不修改现有业务分支和共享 README。项目实现建议只适用于上述可见快照，不能推定新分支仍使用相同后端或接口。

### 1.2 证据层级

正文明确区分：**文档主张、固定提交的实现事实、由代码推导的条件性结论、独立 CPU 探针、尚未执行的 GPU／上游实验**。源码有某分支只证明其存在；配置开启某机制不证明对应旗舰训练一定采用该提交，更不证明收益。

这是源码专题，没有待通读的单篇 PDF。实际覆盖如下；大文件只承诺列出的函数／区段，不以“全部取到文本”代替整仓审计。

| 材料 | 实际阅读范围 | 主要定位 |
| --- | --- | --- |
| 设计文档 | sequence-packing-and-dynamic-batching 全篇，配置、限制、示例和 loss 包装说明 | [D1] |
| 实际入口与配置 | run_grpo.py 全文；grpo_math_1B.yaml 前 290 行；stage2_swe2.yaml 全部配置 | [C1]–[C3] |
| Policy 驱动 | 后端选择、拓扑检查、packing 参数、训练／logprob sharding、结果恢复 | [C4] `Policy` |
| 公共数据容器 | 数据字段、重排、按优化步切分、跨 DP packing/dynamic 规划；重点阅读前 180、370–920 行 | [C5] `BatchedDataDict` |
| packing 算法 | 四个 packer、bin 数调整、MFFD 主体与 factory 全文 | [C6] |
| TQ 数据面 | preshard 全文；TQPolicy 元数据调度与训练／logprob 入口、split API 定义 | [C7]、[C8] |
| Megatron 数据处理 | microbatch 迭代、global mask 统计、普通 packed/CP 处理、routing 对齐、padding 参数 | [C9]；非所有 VLM 辅助分支 |
| 损失准备与包装 | 普通和 fused wrapper；LOGPROB 准备、packed targets、逐段 shift；ClippedPGLossFn 主体至 metrics | [C10]–[C12] |
| 全局归约基础 | masked_mean、同题 baseline 的已读部分 | [C13] |
| Megatron 执行 | forward/postprocess、packed/fused 选择、MCore 缩放补偿；worker 普通 train 与 split-step 主路径 | [C14]、[C15] |
| 真实依赖核查 | MCore schedules.py 的 forward_step_calc_loss；NeMo setup 中 per-token/SUM 配置定位 | [M1]、[C16] |
| DTensor v2 对照 | Automodel forward 准备、CP canonical/局部布局、backward 缩放、dummy 处理 | [C17]，约 1–300、350–655 行；未整仓追 Automodel dependency |
| 上游测试 | TQ seqpack 等价测试全文；fusion 测试前 340 行的 fixture、logits 梯度及 prepacked 用例 | [T1]、[T2] |
| 项目导航 | AGENTS、阅读模板、CURRENT-STATE-BRIEF 的有关章节 | 只用于文末映射与文档约定 |

未执行上游 pytest、分布式 GPU 单测、真实训练、性能压测或独立 reviewer 审查。没有下载模型权重或安装整个 NeMo 环境。具体自查见 [记录](reviews/infra06_nemo_rl_self_check_20260908.md)。

<a id="entry"></a>
## 2. 先分清训练单位与真实入口

### 2.1 同一个“batch”在这里至少有六种含义

| 名称 | 本文的严格含义 | 容易混淆的对象 |
| --- | --- | --- |
| prompt group | 同一题的多次采样，用于上游优势估计 | 不是 bin，也不要求恰好落在同一 DP rank |
| 逻辑序列／数据行 | 交给 policy 的一条 input_ids 及对应训练字段 | 不自动等于真实 agent 的完整 episode；harness 拆段归属是更上游责任 |
| train global batch | 一次 optimizer update 计划消费的逻辑序列集合 | 不等于一次 rollout 的所有输出，也不等于一条 streaming chunk |
| DP shard | 同一 global batch 分给某个数据并行副本的行集合 | CP/TP/PP 复制或分片不能算作更多独立样本 |
| microbatch／packing bin | 一次模型 forward 的执行单元 | 可以包含多条逻辑序列；packed 模型维度 B=1 不代表只训练一个样本 |
| streaming chunk | split API 的一次新增数据交付 | 内部仍可能再拆成多个 microbatch，不能按调用次数计算更新次数 |

`PackedTensor` 这类数据运输容器也不能仅凭名称等同于 attention sequence packing。本文关注的是源代码中的执行布局和最终损失，不把表示层名称当作算法定义。[C4]、[C5]、[C8]

### 2.2 可定位的训练入口

`examples/run_grpo.py` 读取配置、解析 override、setup policy/generation/data，然后根据 async 和 data-plane 选项选择训练路径。默认数学配置当前实际为 **Qwen2.5-1.5B + DTensor v2**，不是 Megatron。因此不能只读默认 YAML，再声称已追踪 Megatron 示例。[C1]、[C2]

用于明确 Megatron 实际配置的参照是：

```text
examples/run_grpo.py
  --config examples/nemo_gym/nemotron-3-super/stage2_swe2.yaml
```

这是**源代码中的配置入口，不是本轮运行过的命令**。其关键设置为：

| 字段组 | 固定配置值 | 解读 |
| --- | --- | --- |
| 采样与更新 | 16 prompts × 32 generations；GBS=512；train MBS=1 | 三个计数分别属于问题、轨迹和更新 |
| 训练布局 | Megatron enabled；DTensor disabled；packing=true；dynamic batching=false | 主读 packed Megatron 路径 |
| token 预算 | max_total_sequence_length=196608；train/logprob bin token 预算同为该值；logprob_chunk_size=2048 | 不是 8 卡建议值 |
| 并行 | TP=8、CP=16、PP=1、EP=16、expert TP=1、SP=true | 不能将 EP 再随意乘进 Policy 的 PP×DP×CP×TP 计数 |
| 对齐 | make_sequence_length_divisible_by=2×CP×TP=256 | 来自这组 CP+TP+SP 配置，不是所有模型统一按 256 |
| 算法／辅助项 | token-level loss；force_on_policy_ratio；TIS；MTP=5、detached heads | 本文不据此推断每项算法带来了多少收益 |
| 执行环境 | NeMo Gym 的 SWE/OpenHands；200 turns、3600 秒 timeout | 外层 max_rollout_turns=1 不等于 agent 只调用一次工具 |
| 开放性 | 模型、数据和镜像路径仍是占位符；配置含大集群资源 | 是可阅读配方，不是完整独立可复现资产 |

以上都是 [C3] 的配置事实；没有用它们估算用户机器的运行时间，也没有把该文件的配置当作 Nemotron 论文某一次实际运行的已核记录。

### 2.3 三条交汇的代码路径

```text
环境／rollout／优势估计
    ↓ 逻辑行与 token_mask、sample_mask、advantages、概率字段
普通数据面                           TQ 数据面
Policy._shard_for_train              TQPolicy.train_from_meta
    ↓                                   ↓
BatchedDataDict.shard_by_batch_size ← shard_meta_for_dp 的同一规划器
    ↓ 行重排 + 每 rank 的 microbatch 元数据
worker.train / train_presharded
    ├─ Megatron 数据准备 → THD / CP → LossPostProcessor → MCore → optimizer
    └─ DTensor v2 数据准备 → Automodel / CP → LossPostProcessor → autograd/FSDP
```

TQ 是运输与访问方式的变化，不天然构成新的优化目标。它以稳定 sample key 写入／读取字段；packing 计划必须和对应字段一起到达 worker。普通路径则直接传 sharded 数据，并在 logprob 返回后恢复原始顺序。[C4]、[C5]、[C7]、[C8]

注意：动态 **sampling** 是根据奖励等条件挑选训练数据，动态 **batching** 是在已确定的数据上规划执行布局。run_grpo 对 async 模式的 dynamic sampling 限制，不能写成“异步不支持动态 batch”。[C1]

<a id="planning"></a>
## 3. Driver 先规划，不在这里真正拼接模型输入

### 3.1 优化步边界先于装箱

`shard_by_batch_size` 接收 `batch_size` 时，先按这一大小处理各个 global batch，再分别排序、分配或装箱。训练入口传 train GBS；logprob 入口传 `None`，可以把整次前向请求一起平衡，因为它不在中间更新权重。[C4]、[C5]

这个顺序有实质意义：若把本来属于两个 optimizer step 的序列混着装箱，再按新的排列切 step，即使所有 token 都出现一次，**看到每条样本时的参数状态也会改变**。它不是语义保持的纯布局优化。

packing 后每个 rank 的逻辑行数可以不同，因此 `elem_counts_per_gb` 保存每一步在该 rank 上实际分得多少行。worker 取 global batch 时不能简单按 `GBS / DP` 连续切数组。需要等量的是正确的 collective 调用关系，而不是每个 rank 永远持有相同行数。[C5]、[C9]

这里保留的是 **optimizer-step 集合**；同题 group 的统计应当在适当的上游完成，并随行携带其结果。本专题没有证明任意 harness fan-out 的 group 语义自动得到保护。

### 3.2 所有随行字段必须共用置换

input_ids、长度、advantages、sample_mask、generation/previous/reference logprob，以及必要的 routing、模态侧信息，必须按同一个行映射移动。只按长度排 input_ids，却保留旧的 reward／概率顺序，是静默的训练问题。

NeMo 把排序与分片放在公共 BatchedDataDict 层，并为后续 worker 保留 microbatch indices、lengths 和 global-batch 行计数。这比在每种模型后端各写一次数据排序更易复用，但正确性仍依赖新字段被纳入同一数据契约。[C5]

## 4. Sequence packing：三个目标，不只是最少 bins

### 4.1 算法和约束

当前提供 Concatenative、First Fit Decreasing、First Fit Shuffle 和 Modified First Fit Decreasing（MFFD）。MFFD 将长度按容量的一半、三分之一、六分之一分层，优先放大项，随后组合剩余项。工厂和算法主体均已读。[C6]

DP 装箱还设置 **min_bin_count=DP、bin_count_multiple=DP**。若初始 bins 太少，会从已有 bin 中移动序列，形成更多非空 bins；不是复制样本填满各 rank。样本不足以形成所需非空 bins 时抛错。

因此，它至少同时优化或约束三件事：容量、各 rank 的 forward 调用数量、逻辑样本不丢不重。为了满足后两者，可以牺牲局部装箱率。

**不要从函数名推导形式保证。** 当前 MFFD leftovers 代码注释称 FFD，但实现维护按已用容量排序的 Python list，优先检查最空 bin，且使用 `pop(0)`／`insert`。这既不能直接等同于按原 bin 顺序 first-fit，也不能仅因二分查找就认定整个循环严格 O(n log n)。本轮没有评价其最坏界、产出质量或 CPU 瓶颈；这是对实现命名和性能论证的限定，而不是另行宣称发现影响训练的错误。[C6] 的末尾约 615–655 行

### 4.2 装箱前必须考虑对齐后的长度

规划使用的不是仅有意义的原始 token 数。例如容量 192、两条序列都长 65：原始总长 130 能放入，但按 64 对齐后为 128+128=256，已经不能共用该 bin。探针 P10 保存了这个反例。

packing 参数来自实际 Policy 配置中的 `make_sequence_length_divisible_by`；不能只改一个看起来相近的 `sequence_length_round` 就假定 Megatron 的 CP/SP 对齐也改变了。[C4]、[C5]

在普通 Megatron helper 中，最小单序列对齐因子是：

$$
a_{\min}=\begin{cases}2C,&C>1\\1,&C=1\end{cases}
\times\begin{cases}T,&T>1\ \text{且 SP 开启}\\1,&\text{其他}\end{cases}
$$

其中 C 为 CP size，T 为 TP size。TP 开启但 SP 关闭时，不应无条件再乘 T。另有 FP8 recipe 和 HybridEP 的 bin-level 对齐要求；PP>1 时还需要统一的 packed sequence 通信长度。[C9] 的 `_get_pack_sequence_parameters_for_megatron`

### 4.3 分配到 rank 和执行顺序

规划后将 bins 分给 DP ranks，每个 rank 保存自己的 bin→行关系。`microbatch_order=largest_first` 只改变已分给同一 rank 的 bin 执行顺序，不改变 bin 内容、rank 归属或总对齐 token。文档的动机是让较小形状复用先前较大分配器区域。[D1]、[C5]

这可以成为窄性能实验，但不能直接保证加速；同时，改变累加顺序仍可能改变浮点舍入、随机数消费和模型内部状态。**声明目标不变，不等于所有数值逐位相同。**

### 4.4 容量只是代理约束

`train_mb_tokens` 和 `logprob_mb_tokens` 分别约束训练与概率前向的执行计划。相同 token 数并不必然相同显存或耗时：单条极长序列与多条短序列、MoE routing、激活重计算、词表 logits、FP8 对齐和 PP 通信都可能改变成本。

所以，packing utilization 应与真实 token、对齐 token、物理执行 token、有效 loss token 分开测量。本轮未完整审计 `packing/metrics.py` 的每个公式，不把这项建议伪写成现有指标已经覆盖了四者。

## 5. Dynamic batching：跨 DP 共同决定边界

### 5.1 它仍是 padded batch，不是变长 attention 拼接

dynamic batching 对相近长度的行组成一个小 batch，再按该 batch 的最大长度 padding。其 token 成本模型主要形如：

$$\text{batch 行数}\times\text{对齐后的最长序列长度}.$$

packing 则使用 varlen／THD 等模型接口把独立序列拼接，边界由额外元数据表达。这是两个不同执行机制。当前 Policy 明确禁止同时启用；dynamic 路径还显式要求 PP=1。[C4]、[C5]

### 5.2 为什么不能每张卡独立决定 microbatch 数

所读实现先对每个 global batch 按长度排序，再分配到各 rank；随后在同一行位置取跨 rank 的最大长度，按这个共同上界推进 microbatch 边界。这样各 rank 的调用数和边界一致。[C5]

独立示意：rank 0 长度 `[2,2,2,2]`，rank 1 为 `[2,2,7,7]`，容量 10。独立规划可分别得到 1 个、3 个 microbatch；共同计划采用 `[[0,1],[2],[3]]`，两边各 3 个且满足示意预算。P04 实际运行了这个独立例子，**未调用 NeMo 原规划器**。

这里的取舍是：rank 0 局部效率可能降低，但 collective 顺序得到协调。单个 rank 的最优 batching 不等于全局最优，更不等于能安全运行。

### 5.3 元数据也可能产生大分配

TQ preshard 不运输真实 token 来规划，而是构造占位 BatchedDataDict 调用相同规划器。当前 dynamic 分支为避免用宽度 1 把真实长度夹掉，按 token 预算创建足够宽的 input_ids 占位张量。**这一修正已经在固定提交中存在，不是尚待修复的当前缺陷。**[C7]

不过占位并不等于零成本。512×32768 的 int64 dense tensor 本体为 128 MiB；这只是可计算的示例大小，未测真实峰值。可研究只以长度与行索引规划的接口，但要先检查选行、连续性和元数据消费，不能简单用 `expand` 替代就宣布问题解决。

<a id="layout"></a>
## 6. Worker 如何产生 packed / CP 模型输入

### 6.1 原始行和模型布局同时保留

Megatron 的 ProcessedMicrobatch 同时包含原始 `data_dict` 和模型侧 `input_ids`、CP-sharded input、position/attention 信息、PackedSeqParams 等。packing 的模型输入通常为 `[1,T_packed]`，原始行上的 mask／advantages 仍用于损失恢复。[C9]

真实长度与物理偏移必须区分：例如长度 5、9、1，按 CP=2 所需的 4 对齐，为 8、12、4。真实总 token=15，而 packed 物理长度=24。末尾还可能为了整 bin 对齐把额外 padding 吸收到最后一个物理段。

当前 `_pack_sequences_for_megatron` 内部保留 raw `cu_seqlens` 与 padded offsets，但交给 PackedSeqParams 的 q/kv 和 q/kv_padded 都使用 padded 边界。**不能仅按字段名字推定 `cu_seqlens_q` 永远等于原始长度累计。** 本版本还传 total_tokens 以支持 Mamba 类状态在样本边界重置。[C9]

这说明 packing 不只需 attention 避免跨样本，还要模型的其他递归／状态机制认识边界。本文没有完整审计每种混合架构的内核支持。

### 6.2 CP 是逐序列切分，再连接到 rank

普通 packed 路径把每条已 padding 序列分成 `2C` 个块，CP rank r 取第 r 块与第 `2C-r-1` 块，然后把各条序列对应的本地块连接。它不是对整个大拼接串一刀切。[C9]

上述 5/9/1 例子在 CP=2 时，两张卡各拿到 12 个物理 token；P05 验证了 15 个真实 token 的 `(sample,position)` 标签不丢不重。这个检查没有运行 attention，也没有验证 CP 的实际通信与反向。

### 6.3 next-token shift 不得越过样本边界

直接对 `[10,11,12,20,21]` 整串左移会得到 `[11,12,20,21,10]`，使第一条样本的末尾预测第二条样本开头，最后又绕回第一条。应按边界去掉这些目标位置，并由正确的 token mask 排除。[C11] 的 `roll_packed_seq_dim`

当前普通与 prepacked 路径采取不同入口：普通行先逐条 shift/pack；Energon 已预先打包的输入保持物理布局，由 helper 依据其源边界进行移位。相同的“一行张量”并不意味着可以套用同一 target 构造逻辑。[C11] 的 `prepare_packed_loss_input`；[T2]

工具输出、prompt、padding 不应因为出现在模型输入里就自动产生 policy-gradient loss。它们可以是有必要的上下文，但是否提供训练监督由声明的目标决定。单独的 observation CE 或其他辅助项需要自己的语义，不能借 packing 顺便改变 mask。

### 6.4 routing 与概率字段不是同一种 shift

MoE expert indices 绑定原始 token 的路由位置，按同一 padded/CP 布局移动，**不做 next-token target shift**。当前 helper 对 pad routing 使用合法、不重复的 top-k 路由占位，而不是随意填重复零或 -1；debug identity 也按同一布局移动。[C9] 的 `_shard_routed_experts_for_cp`

概率字段则有明确身份：generation、previous policy、current policy、reference 不能互换。prepare 路径也会区分 filtered actor logprob 与用于 KL 的 unfiltered logprob。packing 应保持这些身份和位置，不负责替算法决定它们是什么。[C11]、[C12]

### 6.5 三种“融合”要分开

**varlen attention packing** 降低 padding；**SequencePackingFusionLossWrapper** 合并损失准备／调用；**fused linear-logprobs** 避免完整词表 logits。它们的兼容性和节省来源不同。当前 fused loss 只支持特定 LOGPROB 输入，而 custom prepare（例如 value 模型）有明确拒绝条件。[C11]、[C14]

默认 `sequence_packing.fuse_loss` 缺省为 false；不能把可选 fused 路径写成所有训练都走的默认实现。

<a id="loss"></a>
## 7. 主 loss 的全局分母：布局等价的核心条件

### 7.1 计数发生在真实优化步的数据上

Megatron 的 `process_global_batch` 先取得该 global batch 的原始行，再统计：

$$N_{seq}=\sum_i s_i,\qquad N_{tok}=\sum_i\sum_{t\geq1}s_i m_{it}.$$

其中 `s_i=sample_mask[i]`，`m=token_mask`；第一位置不作为下一 token 目标，源码使用 `token_mask[:,1:]`。统计在 **DP group** 上求和，不把 TP/PP/CP 上的复制再次当成独立样本。[C9]

普通 policy loss 要求这些 mask；某些通用 helper 的无 token_mask fallback 不能据此替代多轮 RL 的动作 mask。样本是否删除、在组统计中是否有效、梯度是否为零，是更上游需要明确的不同决定。

### 7.2 两种目标本来就不同

忽略展示用的稳定项，令每个动作位置的 clip/IS surrogate 为 `u_it`：

$$L_{token}=\frac{\sum_{i,t}s_i m_{it}u_{it}}{N_{tok}},$$

$$L_{sequence}=\frac{1}{N_{seq}}\sum_i s_i\frac{\sum_t m_{it}u_{it}}{\sum_t m_{it}}.$$

实际 `masked_mean` 的分母加 `1e-8`，不是 `clamp(min=1)`。token-level 使较多有效动作 token 的序列贡献更多；sequence-level 先每条平均，再按样本平均。P02 的两条长度 1/3、位置损失 1/3 的例子分别约为 **2.5 与 2.0**。这不是舍入误差，更不能为了让两条路径相等而任意改变其中一个目标。[C12]、[C13]

sample_mask=1 但有效 token 为零的序列，在 sequence denominator 中仍可能占一份；其有限值分子为零。是否应提前剔除必须依据算法合同，而不是悄悄让 packing 层替你决定。

### 7.3 为什么逐条调用 loss 可以保持主目标

SequencePackingLossWrapper 把 packed logits 切回原始序列，逐条调用 prepare/loss，但**每次传同一 global_valid_toks / global_valid_seqs**，最后累加。这样 token 目标的每个调用贡献 `numerator_i / N_global`，不会变成每条局部均值的无权累加。[C10]

FusionLossWrapper 一次准备所有序列的 logprob，再调用 loss。两者等价要求：目标对原始序列可分、同一个全局分母、相同有效位置和输入概率、所有非可加的中间统计已处理正确。DPO 这样的成对目标不能仅靠“逐条 loss 能运行”就继承这个保证。[D1]、[C10]、[T2]

P01 在同一 float64 张量上比较三种分割，主 token loss 和梯度相同；故意改成两个局部均值再平均，得到 **5.10 而非 7.8333**。它是已执行的代数反例，不是 NeMo 模型梯度对拍。

### 7.4 筛除权重不必然改变分母

当前 ClippedPGLossFn 的 TIS/ICEPOP 等处理改变 importance weights；其中被置零的贡献仍使用传入的全局 mask 计数，而不是自动除以保留下来的 IS token 数。两种做法是不同目标，不能笼统称“屏蔽后都会重新平均”。[C12]

同理，已经预先归一化到全局分母的 microbatch metrics 应按其定义聚合，不能又做一次无权平均。主 loss 的 metrics 解释也不能自动延伸到所有辅助 metrics，见 §10。

## 8. 分布式缩放：Megatron 与 Automodel 不能共用一个口诀

### 8.1 Megatron 的两层 CP 因子与调度器补偿

令 L 为已按全局分母计算的某次局部 loss，C 为 CP size，M 为该次 forward-backward 的 microbatch 数。当前 LossPostProcessor 默认 `cp_normalize=true`，先返回 `L/C`，再乘 `M/C`，用于抵消 MCore 的调度平均。[C14]

这不是只读注释得来的结论。本次沿实际依赖 pin 回到 MCore：`forward_step_calc_loss` 的 **两个返回值分支**确实再乘 `C/M`。因此这三步合并为：

$$L\ \longrightarrow\ \frac{L}{C}\frac{M}{C}\frac{C}{M}=\frac{L}{C}.$$

两个 `1/C` 的角色不同：一个处理 CP loss consumers 的重复贡献，另一个只是抵消 scheduler 的 `×C`。最终如何映射到参数梯度，还依赖前向 gather／反向通信和梯度 finalization，不能把这条标量恒等式等同于已经验证真实 CP 训练。[M1]、[C14]

MCore 的三个返回值分支对 token count 有不同处理。**单看 `calculate_per_token_loss=true` 不能判断当前两返回值路径是否会除 M。** 改了 loss 返回接口或依赖版本，就必须重新核查。

NeMo 的 Megatron setup 当前采用 `calculate_per_token_loss` 对应的 **DDP SUM** 路径，`average_in_collective=false`；已经全局归一化的分子由 SUM 聚合。不能再照搬 FSDP 的平均补偿，额外乘一次 DP size。[C16]、[C15]

### 8.2 DTensor v2 / Automodel 的分母与 fanout

Automodel 不经过 MCore pipeline scheduler，而是 PyTorch autograd。当前 backward 使用：

$$L_{backward}=L\times\frac{D\,C}{F},$$

其中 D 为 DP size；F 是 `cp_gradient_fanout`。FSDP 在其 DP×CP mesh 上平均梯度，需要补回 D×C；对于每个 CP rank 都消费完整 canonical loss 的分支，F=C，避免复制 loss consumers 重复计数；分区消费时 F=1。[C17]

当前实现对 LOGIT、LOGPROB、同 tokenizer DISTILLATION 等输入类型显式设定 fanout；新目标必须追其实际 canonical／partitioned 布局，不应机械按 CP size 猜。

| 位置 | Megatron 本文路径 | Automodel 本文路径 |
| --- | --- | --- |
| microbatch 调度平均 | 两返回值 MCore 分支乘 C/M，NeMo 显式补偿 | 不用 MCore scheduler |
| DP 梯度聚合 | 当前 SUM 配置 | FSDP 在 DP×CP mesh 平均 |
| CP loss 复制 | 默认 cp_normalize 除 C，并依赖实际通信路径 | 使用输入类型相关的 fanout |
| 空执行／dummy | 需结合实际 iterator 和 mask | dummy 仍运行但 loss 乘零，metrics 特殊处理 |
| 复核重点 | scheduler 返回签名、finalize、共享参数与 aux | sharder 的 canonical/局部分工、autograd fanout |

本次 P07 只复算这些缩放的标量关系，没有运行 FSDP、NCCL 或真实 CP autograd。

### 8.3 多种辅助损失不能仅跟主 loss 一起“统一除一次”

MoE aux、MTP、draft、正样本 NLL 等可能拥有不同的统计单位或独立梯度路径。Megatron worker 已为部分辅助项设置专用 scale；这本身说明主 loss 数值一致不足以证明整个参数更新一致。[C15]

全零主 mask 在有限输入下返回零，但不自动保证该 step 不改变参数：优化器状态、weight decay、aux loss 或状态更新是否仍执行，要看完整调用。本文没有声称已经在上游复现“空 batch 改了模型”；将其保留为真实 GPU 验证项。

<a id="streaming"></a>
## 9. 流式 split-step：分母晚到时，如何避免每个 chunk 变成一步

当前 TQPolicy 暴露 `begin_train_step → train_microbatches_from_meta(N 次) → finish_train_step`，另有 abort。普通 `train_from_meta` 仍是完整 step 的入口，二者不能按同一个 API 调用次数统计训练步。[C8]

Megatron worker 的 split 主路径为：[C15]

1. **begin** 清梯度、建立唯一 open-step 状态，暂存并调整 `grad_sync_func`、`no_sync_func`、`finalize_model_grads_func`，避免 scheduler 每个 chunk 自行归约。
2. **chunk** 累计本地 sample/token mask 计数，先用占位分母 1 做 forward/backward，梯度累计在本地。每个 chunk 内仍可有 packed/pipeline microbatches。
3. **finish** 在 DP 上求真正计数，按主目标选择 N，先对累计梯度乘 `1/N`，再执行真实 finalization 和 optimizer.step。
4. **异常／abort** 恢复保存的 hooks，并清理当前 step 状态；本轮只读相关主函数，未故障注入完整事务路径。

关键顺序是 **按真实 N 归一化 → 梯度裁剪 → optimizer.step**。若先裁剪再缩放，通常不是同一个优化过程。

更深的工程细节是：`finalize_model_grads_func` 不只负责 DP reduce。它还涉及 TP/SP 参数、PP 共享 embedding、router bias 等后处理。只用一次 `finish_grad_sync()` 替换它，可能省掉了其他必要动作。当前代码保留真实 hook 并在每个 optimizer step 最后调用一次；overlap 情形另启动同步并等待通信完成。[C15]

**适用前提：**用占位 N 后统一缩放，要求先累计的是能以同一 N 归一化的量。不同分母的辅助项不能不加处理地共享这个规则。当前 detached MTP 参数有额外调整；本文没有把这项已读适配泛化为“所有混合目标都已解决”。浮点累积与 `1e-8` 稳定项也使这段代数不是位级相同承诺。

<a id="findings"></a>
## 10. 发现、反例与源码说明差异

### F1 · 可选正样本 NLL 的局部分母依赖调用划分

**证据级别：源码事实 + 独立 reduction/梯度反例；未执行完整 NeMo loss 或生产训练。**

ClippedPGLossFn 在 `positive_example_nll_weight>0` 且存在 rewards 时，选 reward>0 的位置，再在**当前 loss 调用内**计算 `correct_valid_toks=correct_mask.sum()`，以它归一化 NLL。这与主 loss 接收全局计数的方式不同。[C12] 的约 724–742 行

两条正样本的有效 token 长度为 1、3，负 logprob 分别是 `[1]` 与 `[3,3,3]`。一次合并调用：

$$L_{NLL}=\frac{1+3+3+3}{4}=2.5.$$

逐序列 wrapper 的两个调用再相加：

$$L_{NLL}=\frac11+\frac{3+3+3}{3}=4.$$

对应有效位置梯度分别约为 `[-1/4,-1/4,-1/4,-1/4]` 与 `[-1,-1/3,-1/3,-1/3]`。P08 实际验证了这一差异，结果中的极小偏差来自 EPS。

**影响范围必须限缩：**默认配置 μ=0，本文实际引用的 fusion fixture 也没有启用该项；不能据此说默认 GRPO 的 packing 已错误。当前 fused/逐序列调用方式与这个局部目标存在结构性冲突，但完整配置可达性、下游放大程度、已有修复 PR 仍应在提上游之前验证。

可行的修正方向也不能擅自定案：先确认设计目标究竟是全局正 token 平均、正样本平均还是其他加权；再给对应全局统计、fusion 对照和不同 microbatch 的梯度测试。仅把结果除 bin 内序列数，不能一般地恢复全局 token 目标。

### F2 · preshard 返回置换与文档消费方式不一致，但当前 TQ 未使用它

`BatchedDataDict.reorder_data` 内部对参数求逆序（argsort），所以它需要的语义是 new-position→old-position 的正向置换。`shard_meta_for_dp` 另返回逆置换，文档却提示交给同名恢复接口；再次取逆会恢复错误。[C5]、[C7]

P03 使用非自逆置换 `[2,0,3,1]`，证明二次求逆不能恢复原顺序。这个例子特意不使用交换两个元素那种自逆情况，否则错误可能被测试掩盖。

但本次继续追到 TQPolicy：logprob 结果按 sample key 写回，实际 `metas,_` 丢弃该置换；训练输出为聚合指标，也不依赖它。[C8]

**所以最终分类是接口／文档风险，不是已经发现当前 TQ 训练 logprob 错配。** 普通 Policy 的 logprob 路径则使用 BDD 返回的正向排列恢复，函数局部变量叫 `unsorted_data_indices` 不改变其真实约定。[C4]

合适的低风险候选是明确 permutation 方向、加入长度至少 3 的非自逆测试、删去误导示例。不能把“读到了一个危险返回值”直接算作生产 bug。

### F3 · 元数据规划存在可计算的 host 分配，尚未证明是瓶颈

preshard 的占位 input_ids 不是模型真实 token，但可按 N×token-cap 分配内存。P10 的 128 MiB 只计算这一张量本体，未包含复制、其他字段或 allocator，也不是测出的峰值。[C7]

可比较 lengths-only planner 与当前路径的 plan 一致性、峰值 RSS、CPU 时间和大 batch 行为。若当前开销很小，不应为了这项可能性扩大公共 API 或建另一套数据平面。

### F4 · 文档兼容性不能替代版本化的代码矩阵

设计文档仍有“DTensor CP+packing 为 WIP”等较宽泛限制；当前代码已经区分 v1/v2、Automodel CP、不同 input type，以及模型自带 packing/CP 的情况。另一方面，Policy 中 dynamic 与 packing 互斥、dynamic PP=1 等检查确实存在。[D1]、[C4]、[C9]、[C17]

这不意味着可以反过来宣布当前所有模型都支持 CP+packing。应将**明确拒绝、存在代码路径、存在测试、已运行验证**分开登记；完整支持矩阵需要在具体模型、后端、依赖和精度上验证。

### F5 · 上游“等价测试”的名字不等于证明全部等价

TQ transport 测试比较共同 planner 的输出，再 roundtrip 张量和 metadata；它不独立检查 planner 的语义，也不经过完整 loss。其头部对剩余分歧来源作了更广泛说明，但从实际断言只能推出该 fixture 的运输等价。[T1]

fusion 测试更强，比较 forward loss 与 **对 logits 的梯度**，并覆盖 CP/TP 的构造；但该 fixture 仍是合成 logits，而非完整模型参数、optimizer 和 MoE 状态，也未启用 F1 的可选正 NLL。[T2]

这是测试范围判断，不是对测试价值的否定。两者很适合复用思想，但需要补上真正关心的反例。

<a id="tests"></a>
## 11. 上游测试与本次执行记录

### 11.1 已读但未执行的上游测试

| 测试 | 它实际检查什么 | 不能从中推出什么 |
| --- | --- | --- |
| `test_seqpack_equivalence.py` | 64 条变长数据、DP=4；同一 sharder 结果经过 TQ 读写后，seed tensor 和 metadata 相同；含 packing、dynamic、普通路径 | 全套 preshard API 无错；独立 planner 正确；真实模型梯度或训练收敛相同 |
| `test_sequence_packing_fusion.py` 已读部分 | prepacked target 路径；合成 logits 的逐序列/fused loss 和 backward 梯度；CP/TP fixture，误差阈值约 1e-5 | 全部可选 loss/模型都等价；辅助项不同分母无影响；完整 optimizer 一致 |

本轮没有声称这些 tests 在当前容器 PASS，也没有将它们的测试名数量记入我们的 10 个探针。[T1]、[T2]

### 11.2 本次真实执行的十个独立 CPU 探针

运行环境：**Python 3.13.5、PyTorch 2.10.0+cpu、CUDA 不可用**。脚本仅依赖 torch 与 Python 标准库；没有网络、模型下载、Ray 或 NeMo 导入。

```bash
python docs/harness_improve/external_paper_references/reading_notes/probes/nemo_rl_semantics_probe.py \
  --output /tmp/nemo_rl_semantics_probe_results.json
```

脚本：[nemo_rl_semantics_probe.py](probes/nemo_rl_semantics_probe.py)；本次结果：[JSON](probes/nemo_rl_semantics_probe_results.json)。

| 探针 | 实际观察 | 证据边界 |
| --- | --- | --- |
| P01 global token reduction | 三种分区梯度最大差 0；错误局部均值平均 5.10，参考 7.8333 | 同一 float64 张量的独立归约 |
| P02 sequence vs token | 约 2.0 vs 2.5 | 证明目标定义不同 |
| P03 permutation | 正向参数可恢复；已求逆再传入不能恢复 | 反例针对接口约定；TQ 当前忽略此返回 |
| P04 dynamic coordination | 独立计划 1/3 个 microbatch；协调计划 3/3 | 说明 collective 调度约束，不调用原规划器 |
| P05 CP token identity | 原长 5/9/1→pad 8/12/4；两个 rank 各 12 物理 token；15 真实标签恰一次 | 只检查布局，不执行 attention/通信 |
| P06 boundary shift | 原串全局 roll 跨样本；逐段清边界去掉交叉目标 | 真实 loss 还必须屏蔽无效位置 |
| P07 scale algebra | MCore 补偿、FSDP averaging/fanout 的标量关系成立 | 不代表分布式 autograd 已测 |
| P08 positive NLL | 约 2.5 vs 4.0，梯度不同 | 仅隔离当前源码同型局部 NLL，不运行完整 loss |
| P09 zero mask / NaN | 有限输入全屏蔽为 0；NaN 乘零仍为 NaN | finite 前提反例，不声称上游实际产生 NaN |
| P10 aligned budget / skeleton | raw 130≤192，aligned 256>192；指定占位张量 128 MiB | 预算与存储算术，不是生产性能数据 |

**10 PASS 的含义是每个断言都满足，包括故意构造的“不相等”负例。** 不是十种 NeMo 训练配置都正确。

### 11.3 下一步真正需要的 GPU 验证

先固定一个小模型、权重、token、mask、advantages、概率字段和 RNG 条件，比较普通 padded、dynamic、packing、fused/逐序列，再逐项扩到 CP/TP。应同时比较模型输出、标量 loss、参数梯度和一次 optimizer update；先关闭 MoE aux/MTP/draft，再分别开启，避免主目标通过掩盖辅助项问题。

一旦改变 group 成员、有效样本集合或优化步划分，就不是纯布局对照，应改报实际学习过程变化。容差也应按 dtype、kernel 和浮点非结合性解释，不能把恰好非零的差异都判成错误。

## 12. 性能证据与可复用优化的优先级

官方设计文档给出 agent/reasoning 数据 padding 浪费、packing 加速等量级性描述，但本次未取得对应完整硬件、模型、数据分布与测量协议；不将其写成已经独立证实的 2–3× 端到端训练收益。[D1]

对性能应分别度量：规划 CPU 时间与 host 峰值、各 rank bin/µ 数、真实/对齐/物理/有效 loss token、forward/backward 时间、logprob 时间、通信与峰值显存，最后才是完整 step 和学习质量。

若 trainer 本来只占端到端时间比例 f，将其提速 a 倍的理想上界为 `1 / ((1-f)+f/a)`，还未计入交互重叠和新开销。这只是 Amdahl 式推算，不代入旧 P3 的历史比例作为当前事实。

| 候选 | 为什么值得考虑 | 先做什么 | 当前不应声称什么 |
| --- | --- | --- | --- |
| 分母与分区不变性回归 | 最贴近正确训练消费，CPU 可先验证 | 固定逻辑行，变 µ/pack/DP 分配；包含辅助项 | 所有梯度已在 GPU 等价 |
| F1 正 NLL 的上游测试／修正 | 有源码路径和明确负例 | 导入真实 loss+wrapper，补 rewards/μ fixture；确认设计目标 | 默认 GRPO 已损坏或已经是唯一新 bug |
| F2 permutation 接口说明 | 小而明确，适合文档和测试 PR | 非自逆置换；核查所有返回值消费者和已有 PR | 当前 TQ 正在错配样本 |
| lengths-only metadata planning | 可能减少 host 大张量及复制 | 先做精确 plan parity 与 RSS/CPU 基准 | 128 MiB 就是当前性能瓶颈 |
| largest-first / µ token budget | 不必改变算法的窄性能开关 | 固定样本与资源，比较 allocator、rank-tail、吞吐 | 总 token 相同必然等时／同显存 |
| CP/TP sidecar 对齐测试 | agent长上下文与MoE尤为相关 | token、概率、routing 身份随布局 roundtrip | token IDs 对齐就证明数值一致 |

任何上游 issue/PR 都应先检查最新 main 与现有修复。本轮没有发送 issue、PR 或改动 NVIDIA 代码，也没有完成这些候选的上游重复问题检索。

<a id="project"></a>
## 13. 对 RepoHarness 的条件化映射

这一节只依据本轮可见的 2026-09-05 miles 快照与用户给定的单节点八卡条件；**用户当前新分支未被识别，所以不声称这里描述了新分支已经采用的实现**。

NeMo RL 的价值不是要求 RepoHarness 增加第二个生产训练后端。可优先复用的是它将执行布局与目标消费分开的方式，以及能够检查这种分离的测试。

### 13.1 最值得补的证据，而不是新平台

**第一，固定逻辑样本集合的消费测试。** 对同一组轨迹在不同 fan-out／packing／microbatch 组织下检查组身份、mask、概率、loss 分母与权重。rh2 自有 loss 合同与 NeMo 的目标未必一样；不能为与 NeMo 数值一致而修改已定分母。

**第二，把轨迹和执行行的数量分开记录。** packing ratio、训练叶子数、有效 token、完整组数都是不同分母。系统优化后“训练行更多”不一定表示更多独立学习经验。

**第三，只在测到 trainer 瓶颈后移植性能技巧。** 单节点 PCIe 的通信和显存配置与大规模 CP/EP 的示例不同。若主要等待仍在环境、评分或推理，就先利用这篇做正确性回归，不必马上投入新的 packer 或复杂 CP。

**第四，主 loss 外的任何新监督都单独过分母检查。** 以后加入 OPD、观察 CE、正样本 SFT 或多目标混合时，先定义统计单位，再让 packing 与分布式 reducer 消费；不能默认公共 wrapper 会替目标作者解决它。

### 13.2 三个可先安排的小实验

| 实验 | 数据与操作 | 成功判据 | 是否需要正式 RL |
| --- | --- | --- | --- |
| 消费布局对拍 | 冻结少量可信多轮轨迹，生成多种合法分片；保留同一逻辑组与优化步 | 按本项目声明目标，CPU参考与实际loss/grad在容差内一致；负例能被检出 | 否，短GPU可补实际后端 |
| 真实长度分布重放 | 只使用本项目已采样长度和侧信息形状，比较现有planner与候选预算/顺序 | 峰值、µ数、rank-tail有可重复差异，数据集合和目标不变 | 否，先CPU/固定权重 |
| 辅助目标分母矩阵 | 在声明的简单目标上逐项加入KL/OPD/CE等，而非一次全开 | 改变µ和packed布局不意外改变辅助项权重；不同目标的合理差异被显式解释 | 否，先张量级再模型级 |

以上只是可验证候选，不新增训练门禁、审批系统或常驻平台，不改变 miles/verl 迁移决策。若未来发现必要修正落在上游公共消费路径，先形成最小反例与窄补丁；若仅是本项目字段没接好，就准确归为集成问题。

## 14. 检索索引与未解决事项

| 常见问题 | 本文位置 | 直接源码 |
| --- | --- | --- |
| packing 为何不能跨 optimizer step 随意排序？ | §3 | C4、C5、C9 |
| 动态 batch 为什么需要跨 rank 协调？ | §5 | C5、C7 |
| 单序列 padding 到底乘不乘 TP？ | §4.2 | C9 `_get_pack_sequence_parameters_for_megatron` |
| cu_seqlens 的 raw/padded 如何区分？ | §6 | C9、C11 |
| 工具 observation、routing、target shift 怎样不同？ | §6 | C9、C11、C12 |
| 为什么全局分母不是局部均值平均？ | §7 | C10、C12、C13 |
| Megatron 为何先除 CP 又乘 M/CP？ | §8 | C14 与真实依赖 M1 |
| FSDP 为什么乘 DP×CP/fanout？ | §8 | C17 |
| 分母最后才知道时怎么办？ | §9 | C8、C15 |
| 哪些 findings 有实际CPU证据？ | §10–11 | 独立 probes 与结果；不是上游运行 |

未解决项包括：用户新分支的实际实现；完整NeMo配置可达性矩阵；所有模型/精度的packing支持；上游端到端训练与性能；辅助loss完整 GPU 对拍；最新issues/PR重复性；独立reviewer。后续不应因笔记完成而将这些状态改为已验证。

本稿的可复用结论是：**把算法意义上的样本与执行意义上的张量分开；用明确全局统计维持目标，再沿真实后端检查缩放与通信。** 这比泛泛地说“packing 能提升利用率”更接近项目一所需的系统能力证据。

## 官方源码与文档

[D1]: https://github.com/NVIDIA-NeMo/RL/blob/13182a5f24a47856aa9191f651510d0df249c9c0/docs/design-docs/sequence-packing-and-dynamic-batching.md
[C1]: https://github.com/NVIDIA-NeMo/RL/blob/13182a5f24a47856aa9191f651510d0df249c9c0/examples/run_grpo.py
[C2]: https://github.com/NVIDIA-NeMo/RL/blob/13182a5f24a47856aa9191f651510d0df249c9c0/examples/configs/grpo_math_1B.yaml
[C3]: https://github.com/NVIDIA-NeMo/RL/blob/13182a5f24a47856aa9191f651510d0df249c9c0/examples/nemo_gym/nemotron-3-super/stage2_swe2.yaml
[C4]: https://github.com/NVIDIA-NeMo/RL/blob/13182a5f24a47856aa9191f651510d0df249c9c0/nemo_rl/models/policy/lm_policy.py
[C5]: https://github.com/NVIDIA-NeMo/RL/blob/13182a5f24a47856aa9191f651510d0df249c9c0/nemo_rl/distributed/batched_data_dict.py
[C6]: https://github.com/NVIDIA-NeMo/RL/blob/13182a5f24a47856aa9191f651510d0df249c9c0/nemo_rl/data/packing/algorithms.py
[C7]: https://github.com/NVIDIA-NeMo/RL/blob/13182a5f24a47856aa9191f651510d0df249c9c0/nemo_rl/data_plane/preshard.py
[C8]: https://github.com/NVIDIA-NeMo/RL/blob/13182a5f24a47856aa9191f651510d0df249c9c0/nemo_rl/models/policy/tq_policy.py
[C9]: https://github.com/NVIDIA-NeMo/RL/blob/13182a5f24a47856aa9191f651510d0df249c9c0/nemo_rl/models/megatron/data.py
[C10]: https://github.com/NVIDIA-NeMo/RL/blob/13182a5f24a47856aa9191f651510d0df249c9c0/nemo_rl/algorithms/loss/wrapper.py
[C11]: https://github.com/NVIDIA-NeMo/RL/blob/13182a5f24a47856aa9191f651510d0df249c9c0/nemo_rl/algorithms/loss/utils.py
[C12]: https://github.com/NVIDIA-NeMo/RL/blob/13182a5f24a47856aa9191f651510d0df249c9c0/nemo_rl/algorithms/loss/loss_functions.py
[C13]: https://github.com/NVIDIA-NeMo/RL/blob/13182a5f24a47856aa9191f651510d0df249c9c0/nemo_rl/algorithms/utils.py
[C14]: https://github.com/NVIDIA-NeMo/RL/blob/13182a5f24a47856aa9191f651510d0df249c9c0/nemo_rl/models/megatron/train.py
[C15]: https://github.com/NVIDIA-NeMo/RL/blob/13182a5f24a47856aa9191f651510d0df249c9c0/nemo_rl/models/policy/workers/megatron_policy_worker.py
[C16]: https://github.com/NVIDIA-NeMo/RL/blob/13182a5f24a47856aa9191f651510d0df249c9c0/nemo_rl/models/megatron/setup.py
[C17]: https://github.com/NVIDIA-NeMo/RL/blob/13182a5f24a47856aa9191f651510d0df249c9c0/nemo_rl/models/automodel/train.py
[M1]: https://github.com/NVIDIA/Megatron-LM/blob/1e7598cbfae888cdd3d741a351aae588d56f66c0/megatron/core/pipeline_parallel/schedules.py#L286-L356
[T1]: https://github.com/NVIDIA-NeMo/RL/blob/13182a5f24a47856aa9191f651510d0df249c9c0/tests/unit/data_plane/test_seqpack_equivalence.py
[T2]: https://github.com/NVIDIA-NeMo/RL/blob/13182a5f24a47856aa9191f651510d0df249c9c0/tests/unit/algorithms/test_sequence_packing_fusion.py
