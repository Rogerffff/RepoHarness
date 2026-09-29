# miles v0.1.1：训练语义与性能复用审查

整理日期：2026-09-29。角色：Training Semantics Reviewer。状态：**只读评估与复用建议；未升级、未回植、未改变配方或准入。** 本文交由主审与运行时、简化反证报告去重裁定。

## 结论

**v0.1.1 不是 RH2 faithful DIS 的现成替代。** 当前 fork 已含 sampling-support logprob 原语（#2200）、支持集运输（#2595）、RH2 自定义 loss 运输补丁与 execution 等权归一化。新版完善的是默认 `policy_loss`、FSDP 与 session 等接入面；直接换树既会启动失败，也会在删掉保护或漏移植局部补丁后改变训练行为。

对当前主链最明确的小回植候选是 **#3125 的 PP 末级判定**。其余性能项应按真实配置筛选：BF16 logits 的训练优化默认不覆盖 `custom_loss`；true-on-policy 分块需要另外启用该模式与正的 chunk size；colocate、NVMe、量化缓存、PPO、OPD、LoRA 都有当前未启用的前提。没有本项目 GPU 测量，不能把 release 中的显存或内存数字写成本项目收益。

**I18 仍未解决。** #2834 扩大 Miles session 增量 R3 的使用范围，未接入 RH2 的 capture/backfill 路径，也不证明异步 publish、历史重 prefill 与单请求 retract 下的路由来源正确。

建议分三层处理：

- **现在窄回移**：优先安排 #3125；校正 top-k 容量表述并把真实 cap 检查放回既定 GPU 诊断。#2764 先按 E5 测阶段峰值，只有值得时才单独适配 `custom_loss`，不以此次评估作为改 dtype 的授权。
- **整栈迁移时一起处理**：新版 replay 开关/调用方 mask、Sample 结构、FT 与事件接口、exact-zero-signal/weights_dirty，以及诊断消费者；先证明这些接缝守恒，再谈删旧 patch。新版默认 policy_loss/FSDP/session 的改进在对应入口才有价值。
- **后置**：#2825 的 true-on-policy 模式、colocate、NVMe、TE 量化、PPO/OPD/LoRA、多租户，以及 I18 的路线选择。它们各有独立需求或配方前提，当前不必为“跟上版本”引入。

## 依据与当前配方

- 上游只读快照：tag `v0.1.1`，commit `2806267d060d51b1d3b62f85a1f9b145047aeef9`；release 原文在 [release.md](../../../../../runs/miles_v0_1_1_review_20260929/release.md)。
- 实际 fork：`reference/miles-rh2-integration` HEAD `275e31eb21ecceeb27cb0d1a522c6a59f348dc2e`；基线 `f2b7c7929` + 4 个上游选择 + 20 个 RH2 patch，见 [integration_base_manifest.json](../../miles_spike/integration_base_manifest.json)。#2595 采用合并版 `29c2c3aee`；#2200 已在 base 的祖先历史内。
- 实际 loss 是 [faithful_dis_loss.py](../../../../../rh2/src/repoharness2/adapters/miles/faithful_dis_loss.py)，不是 `adapters/miles/loss.py`。当前与新版公共 dispatcher 均为 `miles/backends/training_utils/loss.py`，均已使用 `loss_hub`；这次不能把既有目录结构当成新增 API 搬家。
- [launch.sh](../../../../../rh2/experiments/miles_gpu_spike/launch.sh) 当前为 Qwen3-30B-A3B、BF16 全参、GRPO 优势、faithful DIS `custom_loss`，KL/entropy/MTP/OPD/MoE aux 均为零或关闭，Adam；`top_p=0.8`、默认 `top_k=151936`，8 prompts × 8 executions，global batch 32，每轮两步。默认 PP=3、TP=1、CP=1；6+2 或 4+4 训推分离、fully async。这里是既有诊断/spike 入口事实，不等于正式配方新定案。
- E5 诊断档保留额外 actor logprob forward；效率档只加 `--use-rollout-logprobs`。`--skip-actor-forward-only` 因 `custom_loss` 与每轮两步仍不适用，见 [E5 Brief](../batch6_efficiency_20260921/e5_efficiency_profile_brief_20260924.md) 与 [forward_profile.py](../../../../../rh2/src/repoharness2/adapters/miles/forward_profile.py)。

训练不变量：每条 execution 的全部 sibling 行使用相同 provenance-token 分母；batch 按 execution 数归一化；当前与 behavior logprob 都在当时采样支持集上归一化；DIS 的截断权重 detached；全局精确零梯度不执行 optimizer/scheduler，也不因此发布新权重版本。新版默认 GRPO/PPO 目标不自动等于这套契约。

## 逐项复用判断

| 改动 | 当前分类 | 真实消费者与本项目边界 | 采用前最小验证 |
|---|---|---|---|
| [#2200](https://github.com/radixark/miles/pull/2200)：支持集 logprob 原语 | **已具备** | `loss_hub/logit_processors.py → math_utils.py`；RH2 `faithful_dis_loss_function` 显式传 `rollout_sampling_mask`。 | 保留 target∈support、singleton、非动作位、温度、空分片与 CP 对齐验证；不重复为已具备能力升级。 |
| [#2595](https://github.com/radixark/miles/pull/2595)：Sample/CSR/wire 运输 | **已具备** | 已选入 fork；RH2 经 `capture_wire → sampling_mask_assembly → canonicalize → train_data_conversion` 运输 IDs/offsets。patch 0001 使 `custom_loss` 也收得到。 | 升级时同一 capture 的 support-normalized behavior、mask、response 行必须逐位对齐；工具/环境 token 仍为 singleton。 |
| [#3354](https://github.com/radixark/miles/pull/3354)：bounded replay 完整接线 | **主链核心已具备；新入口升级后用** | 新版默认 `policy_loss`、FSDP、session 请求校验与 replay 接线更完整；replay 开关从只看 top-p 改为 `top_p<1 OR top_k>0`。当前 top-p 0.8 不受触发条件扩展影响。新版 backward 的 mask 运输仍只照顾 `policy_loss`，不可覆盖 RH2 patch 0001。 | 单独比较当前 RH2 最终请求校验与新版校验；核目标 SGLang 的 support 容量；按 custom-loss 路径跑真运输负例。无需为新增默认入口重写现有 RH2 入口。 |
| [#3125](https://github.com/radixark/miles/pull/3125)：优势计算按真实 PP stage 判定 | **应该回植的窄候选** | `compute_advantages_and_returns` 在非末级直接返回。当前效率档各 PP stage 持有 `rollout_log_probs`，旧函数也会在非末级计算优势；CPU 原函数探针复现。当前零 KL、无 whitening 配方未显示数值错误，主要清除多余计算与错误的阶段归属假设。 | 诊断/效率两档、末级/非末级、两 optimizer steps 的原控制流；末级 loss/梯度不变、非末级不生成优势。无需先升级整树；不把它夸大成已观察到的训练错误。 |
| [#2764](https://github.com/radixark/miles/pull/2764)，连同 [#2818](https://github.com/radixark/miles/pull/2818)：模型精度 logits | **升级后部分可用；自定义训练收益需窄适配** | 新版 actor `compute_log_prob` 调 `forward_only(fp32_output=False)`，诊断额外 forward 可受益。但训练调用明确 `fp32_output=args.loss_type not in ("policy_loss","sft_loss")`；RH2 `custom_loss` 仍是 True。分块内转 FP32 保证 softmax/温度数值路径，不能只改模型输出 dtype。 | 先分阶段测显存：额外 forward / train forward-backward。若要让 custom loss 也保留 BF16 logits，须另做类型与温度、masked TP logprob、fanout、CP 空分片及实际梯度对拍；重新检查 RH2 `0.0 * logits.sum()` 空分片保护。当前不承诺 release 的 768→304 MiB 数字。 |
| [#2825](https://github.com/radixark/miles/pull/2825)：true-on-policy logprob 分块 | **升级后按模式使用；当前无即时收益** | `_calculate_log_probs_and_entropy_true_on_policy` 新增 chunk 参数，修复该模式忽略 chunk 的问题。当前 launch 未启用 `true_on_policy_mode`，默认 chunk 也是 -1。名字不表示自动解决 fully-async 的策略陈旧度。 | CPU TP=1 masked logprob/entropy/梯度 chunk -1/2 完全相同；实际使用仍需 TP gather/backward 与峰值显存测量。源码先 gather 全 vocab，再分行 softmax，因此不是全张量内存的严格 chunk 上界。 |
| [#3655](https://github.com/radixark/miles/pull/3655)：rollout-logprobs 下诊断 | **当前 custom_loss 不适用；默认 policy_loss 升级后用** | 只改 `policy_loss_function`：诊断用独立 trainer score，避免 rollout baseline 与自身相减得假零。RH2 不调用该函数；当前 G1 依赖独立 `logprob_compare` 事件，效率档明确记不可用。 | 若以后增加 custom-loss 内诊断，需要定义是否同版本、哪个 optimizer step 与哪些动作位；不能把更新后 current-vs-behavior 差称作纯训推数值误差。不要因该 PR 把效率档 G1 parity 改为 PASS。 |
| [#2834](https://github.com/radixark/miles/pull/2834)：非 retract 的增量 R3 | **当前入口不适用；可借鉴设计** | `SessionServer/Core` 以 `routed_experts_start_len` 取增量，merge 校验连续覆盖；当前 RH2 自己捕获每轮并在 `backfill_leaf_sample` 取最后一轮全量 tape。 | 真正采用前需把早轮动作、历史上下文、publish、retract、FORK/压缩分行的语义逐一对齐；这属于 I18 的未定方案，不能当运输优化直接接。 |
| [#2781](https://github.com/radixark/miles/pull/2781) / [#3100](https://github.com/radixark/miles/pull/3100)：colocate host-memory 峰值 | **当前不适用** | 同步 `train.py` 的训推 offload/onload 交接把重叠峰值从 CPU 搬到 GPU；#3100 支持 LoRA grad buffer。当前走 `train_async.py`，训推分离、无双侧 offload；该入口仍明确禁止 colocate。 | 若以后另批 colocate，须同时量 host 峰值、GPU 交接余量、KV 生命周期、吞吐；降低 CPU 峰值会增加 GPU 瞬时占用，不是无条件减少总需求。 |
| [#2739](https://github.com/radixark/miles/pull/2739)：Muon NVMe offload | **当前不适用** | `dist_muon` + chunked optimizer offload + 正的 offload fraction；当前 Adam 无此消费者。 | 更换 optimizer 是配方变更；若另行采用，测 grad/state/save-resume 与磁盘吞吐，不为使用该补丁而改算法。 |
| [#2653](https://github.com/radixark/miles/pull/2653)：Adam main 参数流式初始化 | **有容量瓶颈时升级后用** | `setup_model_and_optimizer` 设 `defer_main_param_initialization`，`nvme_stream.setup_optimizer_state_streaming` 逐 bucket 写 main params，避免先生成完整主参数再搬走。当前没有启用 streaming。 | 需 distributed Adam、真实本机 NVMe；核 mmap/page cache/每 rank staging、初始化与 step 峰值、I/O 时长、checkpoint 同拓扑恢复。保持 FP32 moments 才能沿用上游的等价目标；改窄 moments 精度不是纯容量优化。 |
| [#2142](https://github.com/radixark/miles/pull/2142)：TE 量化权重缓存清理 | **当前不适用；未来量化 offload 可复用** | `actor.sleep()` 清 `_fp8_workspaces`，条件为开关开启、TransformerEngine、无 CUDA graph。当前 BF16 且无 train offload，不经过有用分支。 | 量化 + offload 时比对 sleep/wake 后数值、缓存重建成本与 host peak；开启 CUDA graphs 时保留其禁用条件，不能移除地址稳定性保护。 |
| PPO [#2878](https://github.com/radixark/miles/pull/2878) / [#2891](https://github.com/radixark/miles/pull/2891) | **当前不适用** | bridge critic 接线与 shared actor/critic 禁用 indep-DP；当前 GRPO 不使用 critic。 | 改 PPO 时另定 value/reward/GAE/loss、训练资源与 offload 生命周期；不能把 critic 支持算作当前 RL 闭环收益。 |
| OPD / reference KL | **当前不适用，且与新版 replay 明确不兼容** | 新版参数验证拒绝 replay + `use_opd` / `use_kl_loss` / 非零 `kl_coef`；理由是这些目标还要 full-policy actor score，现 replay 接口只给支持集归一化 score。 | 若未来研究，应显式运输两种 score 并确定目标，不关闭 support 校验绕过。当前零 KL 单目标配方不受此限制新增影响。 |
| LoRA / Multi-LoRA v2 / Tinker | **当前不适用；另有需求时升级后评估** | adapter slots、独立 optimizer/checkpoint、Tinker loss dispatch 与模型 target selection；当前全参单作业没有消费者。 | 单 LoRA 能否节省本模型训练资源需实测；改变 trainable 参数属配方变化。多租户收益只有共享 base 模型、多个独立 job 才成立，不能据此承诺当前 coding agent 更快或更准。 |

### 支持集容量的特别纠正

当前 RH2 请求验证已检查 top-k 正数、请求值不超过会话配置、温度一致及不支持的 logit 变换；不能把 #3354 的这部分全部当成缺失功能。**但旧注释把 top-k 称为支持集的“硬上界”不够准确。** 新版 [CLI 说明](https://github.com/radixark/miles/blob/2806267d060d51b1d3b62f85a1f9b145047aeef9/miles/utils/arguments.py#L579) 和 [replay 文档](https://github.com/radixark/miles/blob/2806267d060d51b1d3b62f85a1f9b145047aeef9/docs/advanced/sampling-support-replay.md) 指出 cutoff ties 可使支持集超过 top-k；实际返回容量由 SGLang `sampling-mask-max-tokens` 决定。此次没有检查目标 SGLang 的 cap 默认值或真实溢出行为。

RH2 当前默认 K 等于有效词表大小，是已定的兼容配置，不意味着小支持集成本。容量收益需要记录动作位 support 大小分布、累计 CSR 字节与每条 response 长度；不能默默把 K 改成 64/128，也不能裁剪返回 mask——二者会改变采样或 loss 的概率空间。新 SGLang cap 引起的拒绝应按实际是否新增样本拒绝另行评估，不能只用“bounded”命名替代分析。

## 升级必须保留的训练接缝

以下是 `conditional_future` 迁移条件：当前未执行升级，不能称为当前生产故障。

### 1. 先修接口，再证明语义；不能只让 import 通过

- RH2 导入的 `miles.utils.sampling.top_p_sampling_replay_enabled` 模块、`enable_experimental_ft_trainer` 名称在新树已不存在。`rh2_event_log` 是 fork 私有接口，上游没有；当前 RH2 的 ImportError fallback 只是不发事件，不代表满足正式验收。主审静态扫描见 [rh2_import_scan.json](../../../../../runs/miles_v0_1_1_review_20260929/rh2_import_scan.json)。
- 新版 `get_log_probs_and_entropy` 调用签名仍接收 mask，`custom_loss(args,batch,logits,reducer)` 签名也保留；不是 loss API 全面移除。实际风险是 caller 的字段选择：新版 [model.py:436](https://github.com/radixark/miles/blob/2806267d060d51b1d3b62f85a1f9b145047aeef9/miles/backends/megatron_utils/model.py#L436) 仅为 `policy_loss` 选择 mask 字段。RH2 patch 0001 中“按 replay、不按 loss_type”的条件必须保留，落点从旧 `train_one_step` 移到新 `run_forward_backward_pass`。缺字段会被真实 reader 抛 `ValueError`，当前保护存在时不是静默 full-vocab 降级。
- 新 dispatcher 若收到 `batch["loss_fn"]`，Tinker 分支优先于 `args.loss_type`；普通 RH2 转换不产生该字段。当前不是可达缺陷，但迁移不能引入 Tinker batch 键或 multi-LoRA 模式后仍假设 faithful loss 与 execution 归一化照旧。

### 2. execution 权重可以保留，但零信号处理不会自动保留

新版 dispatcher 仍消费 `rollout_mask_sums` 与 `num_rollouts`，`aggregate_train_losses` 仍按 rollout 数聚合；`advantages.py` 与当前 fork 相比无 diff。CPU 原函数探针用两 executions、三训练行、两 microbatches 对照，loss 都为 7，token 梯度都为 `[1/6,0,1/6,1/6,1/2]`。这说明该接缝可以迁移，**不证明整个多轮转换/训练端到端已验证**。

但新版 [train_one_step:630](https://github.com/radixark/miles/blob/2806267d060d51b1d3b62f85a1f9b145047aeef9/miles/backends/megatron_utils/model.py#L630) 对 valid step 调 `optimizer.step()` 与 scheduler，没有 RH2 `SKIPPED_ZERO_SIGNAL` / `weights_dirty` 契约。漏移植 patch 0002/0003 会使精确零 policy 梯度也可能被 Adam 动量或 weight decay 更新，并推进 scheduler/发布。这是真正可能静默改变配方的迁移风险；不能用“新版 GRPO 已支持 support replay”替代它。新版发布计数 guard 与合法跳过发布的交互由运行时报告单独覆盖。

验收至少覆盖：零信号全局归约后所有 rank 仍完成 backward；零信号不 step、不增 scheduler、不发布；非零正控确有更新；fanout 行拆分与 CP 分片不改变 execution 计权；DIS accepted 数、候选信号数与真实非零梯度不混为一谈。

### 3. `Sample.weight_versions` 已改为逐调用、绝对 token 区间

新树 [types.py:88](https://github.com/radixark/miles/blob/2806267d060d51b1d3b62f85a1f9b145047aeef9/miles/utils/types.py#L88) 是 `list[WeightVersionsPerCall]`，每个 span 包含 `version/abs_start/abs_end`；RH2 [canonicalize.py](../../../../../rh2/src/repoharness2/adapters/miles/canonicalize.py) 当前第 417 行直接复制 `list[str]`，第 620 行将该列表与 capture 的结构化事实互检。新版还移除了 `Sample.adapter`，现有 dataclass 允许集会先拒绝这种漂移。

CPU 调用了真实新版 Sample：直接填旧字符串列表后，`oldest_weight_version` 抛出 `'str' object has no attribute 'spans'`；使用 `from_dict` 读取旧 dump 会把列表保存到 `legacy_weight_versions`，活动 spans 为空、oldest 为 None。后者是旧工件可读机制，**不是可用于 staleness 的数据迁移器**。不能通过清空旧列表或跳过双账核对让升级“跑通”。

迁移需把已捕获的逐轮区间，按 RH2 identity spans / token 装配结果映射到各训练行的绝对位置；处理 observation gaps、精确前缀合并、FORK/压缩后分行与多版本单轮，保留 capture provenance 和严格的覆盖校验。上游 #3334 staleness 指标依赖新结构，不能独立贴到当前 `list[str]` 树里。最低验收是最老版本、每动作位版本与现有两本账一致，缺来源仍显式失败，诊断不能把 unknown 算零。

### 4. 训推诊断不能替代路由来源或同版本证明

新版 #3655 的 current/trainer-vs-rollout 比较是正确修复默认 loss 的假零，但只要经历 optimizer step 或跨版本样本，它同时包含 policy 更新与 staleness。当前 G1 的同版本 `logprob_compare`、E5 的不可用状态，以及 R3 fill/consume/exhausted 证据仍须迁移。新版 session 的增量 R3 只在稳定前缀、不 retract 的假设下拼接；其参数检查仍警告 retract-mode weight-update R3 存在 SGLang 已知问题。

RH2 当前 [generate.py:1495](../../../../../rh2/src/repoharness2/adapters/slime/generate.py) 的 last-full-tape 与早轮 behavior logprob/version 混合来源，正是 [I18](../batch3_training_signal_20260909/README.md) 尚未定案的问题。升级框架不能代替这个决定，也不能把一次形状/coverage 校验当作行为 forward 的路由保真证明。

## 验证、边界与停止条件

本轮执行 [training_probe.py](../../../../../runs/miles_v0_1_1_review_20260929/training_probe.py)，结果 [training_probe.json](../../../../../runs/miles_v0_1_1_review_20260929/training_probe.json) 含受测源码 SHA256。命令：`rh2/.venv/bin/python runs/miles_v0_1_1_review_20260929/training_probe.py`。使用已有 Python 3.12 / torch 2.13；没有安装依赖、修改源码或维护测试。

验证范围：AST 提取当前/新版原函数与表达式，CPU、CP=TP=DP=1；自定义 dispatcher 探针用已知线性 token 分子，明确不冒充真实 faithful DIS 全链；true-on-policy 使用原 masked/gather/softmax 函数，TP=None；Sample 使用上游真实类。结果为上述分母/梯度相同、mask caller 差异、PP 阶段差异、skip-forward 拒绝、chunk 数值相同和版本结构不兼容。

未验证：GPU memory/吞吐、Megatron 模型 forward、分布式 TP/CP/PP、真实 SGLang support cap、MoE 路由、NVMe/TE/LoRA 生命周期、正式训练质量。release 的 H200/GB300/B200 数字和模型配置只能证明上游特定试验，不能推算当前八卡 Qwen3-30B-A3B 的节省比例。

适用审查维度以 B/D/F/G/H/I/L/M/N 为主；A/E 用窄 CPU 反例与正控，K 评估迁移边界，J 只核与行为有关的说明，C 没有挡板变化。未开展全仓实现验收或训前审计。**停止条件已满足：相关训练语义、真实消费者、性能前提与升级失配均有源码或限定探针证据；不继续扩大到上游全仓 bug 排查。**
