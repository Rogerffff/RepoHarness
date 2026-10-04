# Infra07 · 训练—推理一致性：从报告值走到固定样本、可运行的最小检查

**精读与执行日期：2026-09-08。** 本文是版本化源码与一手实践专题，不是另一种 RL 算法，也不宣称完成真实 GPU 训练认证。关键结论是：同一个 `logprob` 字段可能表示原始模型概率、温度缩放后的概率或采样保留集上的条件概率；在确定输入、概率语义与实际权重身份之前，直接比较数值会将不同问题混在一起。批次不变、可重复生成、训推 forward 对齐、同样本梯度一致和完整训练可复现，也是五个不同目标。

本次新增独立诊断脚本，实际完成 **33 个 CPU／本地 mock HTTP 测试，0 failure、0 error、0 skip**。覆盖身份与 token 错配、支持集、温度、mask、数值归约、梯度及打分协议；真实 SGLang/vLLM、HF 模型、Megatron 和 GPU 测试均未运行。对 RepoHarness 的直接启示不是再建治理平台：当前捕获与 faithful DIS 路径已经使用支持集归一化概率；应保留原始诊断列，分别测两类分布，并以已有导出点接入最小检查。

导航：[版本与覆盖](#scope) · [一致性的层次](#definitions) · [一手实践](#sources) · [真实代码路径](#code) · [概率与指标](#math) · [最小实验](#protocol) · [已运行检查](#tests) · [项目适用性](#project)

<a id="scope"></a>
## 1. 来源、版本和范围

### 1.1 固定身份

| 来源 | 本轮固定版本／访问状态 |
| --- | --- |
| RepoHarness 项目映射 | `miles-migration@d2df06d49e42b93436d10d1b7a12d4e1f0ae3be5`；这是可见集成基线，不冒认为用户未给名称的新工作分支 |
| 项目依赖记录 | `integration_base_manifest.json`：miles base `f2b7c79298a53c53861514d099f7def73bd29f4a`；SGLang `4e230c3d85cefdab5b65eeb6f6f87793a707a6fb`；Megatron `235952df607b3820716e5e67728a5ab470ca33ae`；镜像 `v0.5.18` |
| SGLang 当前对照 | `sgl-project/sglang@554f817948c26e8e9c8338b4a33e94a609d6f0fb`；与项目 pin 分开，不自动替项目升级 |
| miles 当前对照 | `radixark/miles@3de96596f16b9e6d23ba550c4c47de3479c9f14c`；定点检查 loss、TIS、debug dump、prefill recompute |
| vLLM | 版本化 v0.25.0 文档、两个 RFC 和 #49577 的状态／说明；**没有整库源码审计** |
| 运行环境 | Python 3.13.5、PyTorch `2.10.0+cpu`；CUDA 不可用，未安装 transformers |

用户说已经进入新分支，但连接器只显示旧工作分支及 `research/nemo-rl-packing-loss-20260908`。后者属于任务6。因此本任务采用独立研究分支交付，不覆盖任务6、不更改共享 README、不改生产 loss／配置。基线身份是为了说明映射适用范围，不要求项目增加新的审批流程。

复用 [N11 miles 既有笔记](N11_miles_agentic_rollout.md)、[O01 SkyRL-Agent](O01_skyrl_agent_sa_swe.md) 和当前项目简报的导航；旧调查中的“一致性包络”只是选题线索，不作为上游当前实现证据。正文用 **S** 标明网页／问题讨论，用 **C** 标明固定源码，用 **P** 标明项目代码。由这些材料推导的诊断设计和本次 CPU 结果单独说明。

### 1.2 一手来源覆盖

| 来源 | 实际阅读范围 | 没有声称完成的部分 |
| --- | --- | --- |
| S1 Thinking Machines：*Defeating Nondeterminism in LLM Inference*，Horace He 与团队，2025-09-10 | 全文静态正文、目录、代码片段、性能表、RL 实验文字及限制；涵盖浮点归约、batch invariance、RMSNorm/GEMM/attention、实现和实验 | 未运行 companion kernels；未逐帧核验交互动画与曲线原始数据；不是现代所有 MoE 的审计 |
| S2 LMSYS/SGLang：*Towards Deterministic Inference in SGLang and Reproducible RL Training*，2025-09-22/24 | 全文静态正文与三组表、chunk prefill、attention、采样、slime、future work | 曲线图的逐点数据未复现；不将文中 2025 支持矩阵视为 2026 当前事实 |
| S3 SGLang deterministic inference 官方文档 | 使用、测试命令、attention/cache 兼容限制及结果解释 | 与当前 main 有版本差别；没有运行文档 GPU 命令 |
| S4 vLLM v0.25.0 `ModelConfig.logprobs_mode` | 原始／处理后的 logits/logprobs 定义 | 未全文审查该版本全部模型配置，更未复现 MRV2 sampler |
| S5 vLLM #48305 | 六类问题、各子项、完成条件、状态与时间，完整 issue 正文 | 子链接不是全部逐一审查；路线图不等于已实现 |
| S6 vLLM #42259 | 2026-09-08 的完整 issue 正文；前四条评论，重点核采样支持集与下游问题 | 后续评论未完整读；列表中的每项 bug/PR 未逐个复现或核验 |
| S7 vLLM PR #49577 | 正文、实验说明、限制、合并状态和时间 | 未审查全部24个文件；未核图中逐点数据；不据此确认某个下游 release 已采用 |
| S8 Open-Instruct #1473 | 完整报告、启动脚本、状态、时间与评论数 | 附图未做逐点分析；没有公开根因可恢复，不执行报告中的 Slurm 脚本 |

这些主来源是网页／代码，没有待遗漏的单篇 PDF 附录。本次不以“没有新训练数据漏斗”强行补写环境生产或教师蒸馏配方。实际训练证据属于来源作者；本文没有更新任何模型权重。

### 1.3 固定源码阅读范围

首次列出完整路径，后文以编号及函数定位。C1–C4 为 SGLang，C5–C8 为 miles；P1–P4 为本项目。

| 编号 | 路径与函数／范围 |
| --- | --- |
| C1 | SGLang 项目 pin 的 `python/sglang/srt/layers/sampler.py`，`Sampler.forward` 至主要采样分支（1–275行） |
| C2 | SGLang 当前 main 的同一路径，`forward`、`_sample_from_probs`、sampling mask capture、greedy 与条件概率写出（1–535行）；未完整审查所有 backend helper |
| C3 | SGLang 项目 pin 的 `python/sglang/srt/layers/logprob_processor.py`，行归一化、top/selected logprob、speculative accepted token 对应、`InputLogprobProcessor` 与 chunk 主体（1–290、360–620行） |
| C4 | SGLang 当前 main 的 `python/sglang/srt/arg_groups/attention_hook.py`，兼容性定位及 `handle_deterministic_inference`；不是完整 arg resolution 审计 |
| C5 | miles 当前 `miles/rollout/generate_utils/prefill_logprobs.py` 全文 |
| C6 | miles 当前 `miles/backends/training_utils/debug_dump.py` 全文 |
| C7 | miles 当前 `miles/backends/training_utils/loss_hub/losses.py::policy_loss_function` 前310行，重点概率身份、mask、dump、TIS；未完整审其他 loss 类型 |
| C8 | miles 当前 `miles/backends/training_utils/loss_hub/corrections.py` 全文 |
| P1 | 项目 `docs/agentic_RL/repo_harness_rh2_workstreams/miles_spike/integration_base_manifest.json` 版本与补丁映射段 |
| P2 | 项目 `rh2/src/repoharness2/adapters/slime/capture_wire.py`，模块说明与1100–1345行的实际响应处理、支持集替换、stage/commit |
| P3 | 项目 `rh2/src/repoharness2/adapters/miles/faithful_dis_loss.py`，模块语义说明与540–790行实际入口、支持集计算、有限性检查、ratio 与分子 |
| P4 | 当前简报、AGENTS 与 reading_notes 模板，用于约定与项目映射，不用过时进度代替现状 |

没有读取未给名称的新分支工作树，也没有在网络下载失败后编造“本地完整 checkout”。源码分散读取但固定到 SHA；细读与仅定位的范围如上。

<a id="definitions"></a>
## 2. 必须先定义：到底要求谁与谁一致

以下是本专题的诊断分解，不是声称各来源采用同一术语。

### 2.1 五种不同的成功标准

| 层次 | 固定／改变什么 | 能证明什么 | 不能证明什么 |
| --- | --- | --- | --- |
| 同条件重复性 | 同输入、同状态、同执行条件，重复 forward | 当前路径的 run-to-run 稳定性 | 换 batch、TP 或缓存后仍稳定 |
| 批次／调度不变性 | 固定目标请求，改变相邻请求、批次大小或顺序 | 目标请求结果对指定执行变化不敏感 | trainer 与 inference 是同一个数值函数 |
| 训推 forward 一致 | 同 token 前缀、同概率语义、同权重状态，在两端打分 | 指定位置的 logprob 对齐 | 全词表 KL、完整 routing 或梯度正确 |
| 同样本梯度一致 | 再固定目标函数、优势值、mask、分母和参数映射 | 实际更新信号相容 | Adam状态、数据调度及完整训练曲线必然一致 |
| 完整训练可复现 | 还固定采样流、数据消费顺序、环境与优化器状态 | 一次声明范围内的训练复现 | 换硬件、版本或任务分布仍逐位相同 |

贪心输出相同仅说明 argmax 没变，许多不同分布都能有同一 argmax。反过来，接近并列的两个 token 可能被很小的数值差异翻转，后续整段自由生成立刻分叉。因此比较自由生成的第100个 token，通常不能定位第一个数值分歧：两边可能早已不是同一个条件前缀。

### 2.2 本实验真正需要固定的对象

**输入不是一段可见文字。** 它包括精确 token IDs、实际上下文、模板及特殊 token、position IDs、causal/segment attention 关系；多模态还需要实际特征与处理配置。文本 decode 后再 encode 只能检验另一条序列，不能给原轨迹的旧 logprob 重新分配身份。

**权重身份不是一个整数标签。** 应确认推理副本确实装载了预期参数、adapter、量化 scale、router 状态和模型配置；版本号、文件名或完成日志只能提供声明，不能自动证明 GPU 张量一致。调试不一定每次全量传回权重，但“未验证”应保留。

**执行状态也不全在参数里。** dropout/train-eval 模式、缓存、计算 dtype、算子选择、TP/EP/CP、通信归约、speculation、seed 与采样状态会改变输出。尤其是更新权重后复用旧 KV：即使新 token 标成版本2，其条件计算也未必等价于用版本2从头计算整个前缀。本次没有审完整权重发布与 KV 失效链，不声称这个问题已在当前项目触发或解决。

### 2.3 “learning_rate=0”为什么不是完整固定样本实验

S8 的报告是在一个长训练作业里，将学习率设零后继续观察 aggregate logprob 差值。它仍可能消费不同任务、不同长度与不同并发组合，也可能有在途权重更新和状态变化。原文自己是故障报告，没有冻结相同 token、逐副本参数与所有运行状态的证据。

所以正确结论是：**不能只用学习率变化解释该报告中的现象，需要进一步控制变量。** 不能据此认定是某个 kernel 的 bug，更不能声称已找到 OLMo-3 的普遍根因。[S8]

<a id="sources"></a>
## 3. 一手实践分别提供了什么证据

### 3.1 Thinking Machines：数值稳定的对象必须包含批次条件

S1 区分固定执行的确定性与用户请求的批次不变性，具体追踪 RMSNorm、GEMM 和 attention 的归约分割；attention 还要跨 prefill/decode 保持划分方式。实验中，Qwen3-235B-A22B-Instruct-2507 的一个贪心提示重复1000次，普通实现出现80种输出，修改后为1种。Qwen3-8B 的1000请求性能例子为26秒对42秒；RL 例子比较无修正、IS 与精确对齐，但未给可直接搬到本项目的完整训练配方。[S1]（算子、Implementation、Experiments）

这支持“精确对齐可以是有成本的对照条件”。文中关于典型 forward kernel 的论述不能扩成所有现代 MoE/EP、量化或跨硬件路径都确定；并行归约不是其完整处理范围。本文后面的 CPU 反例是独立数学检查，不是重现作者 GPU 实验。

### 3.2 SGLang 2025 实践：两种加速分母与一个支持范围

S2 的 **2.8×** 是 deterministic 模式内开关 CUDA Graph 的对比：Qwen3-8B、TP1、H100、16请求、1024输入/输出。另一组是 H200 上正常与 deterministic 模式的差别，后者有额外开销；不能将2.8×解释为开启确定性比普通服务更快。50次输出测试中的单一结果只覆盖其测试条件。正文脚注明确当时部分后端关闭 radix，future work 还列 MoE 和更大 TP。[S2]（Results、Future Work）

该文还分别配置 deterministic sampling、训练 backward、Megatron 和 PyTorch，以实现作者报告的训练复现。这和“训推分别用同一数值计算”不是同一句话。2025年的训练通信配置写 `NCCL_ALGO=Ring`；本次读取的2026 SGLang推理代码使用 tree 与固定channel数，两者针对不同版本和层，不应拼成一套未经验证的推荐设置。[S2]、[C4]（RL Framework Integration）

### 3.3 当前文档和代码：开关名称不是不变性证明

S3 给出了 single/prefix/radix 等测试入口；成功首先是输出唯一性。当前 C4 会因 deterministic 配置调整 sampling/attention backend，必要时禁用 radix，TP>1 时更改 all-reduce 设置并固定channel数。这些行为不是零成本，也不是只影响 RNG。

硬件限制需要单独核验：C4 对 absorbed-MLA 的某个 FA4 确定性路径要求 SM100/SM110。项目目标是 SM120，不能从“Blackwell”这一共同大类推断该路径支持；也不能直接使用只针对Hopper设计的FA3配置。本文不提供一个声称适配所有目标模型的 GPU 启动配方。[S3]、[C4]（`handle_deterministic_inference`）

### 3.4 vLLM 两个 RFC：架构议题不是已完成能力清单

S5（#48305）将问题分为 token/logprob、MoE routing、DSA index、数据面、hidden states、dtype 六项。它仍为 open。某项打勾、某项有 PR 或某个 exit criterion，代表的证据等级不同。尤其“OPD 需要隐藏状态导出”应理解为该 RFC 关注的实现路线，不能推广为所有 sampled-token/full-vocab OPD 都必须导出 hidden states。[S5]

S6（#42259）截至2026-09-08已重写为 **MRV2及共享路径**的未关闭问题追踪，明确排除部分旧路径和已经合并的修复。旧摘要里的“全部未解决事项”不能覆盖这个新范围。其条目涵盖 raw/processed、top-k并列、流式丢token概率、all-reduce/attention/EP批次敏感性，以及下游框架的不匹配。每个条目仍需要各自最小复现，不能把追踪表整体叫作vLLM的已证错误集合。[S6]

S7（#49577）已于2026-08-13合并，提供 CSR sampling mask；正文明确这是词表支持集，不是 attention mask，并列出当时 MRV2、processed logprobs、正温度等限制。作者报告概率和ratio对齐，不声称已证明下游任务质量提高。本次只核其描述、状态和边界，未独立运行其训练或审完24个变更文件；也没有验证所有已发布版本或下游pin都包含它。[S7]

### 3.5 Open-Instruct：保留观察，不虚构根因

S8 在 OLMo-3-7B 相关 GRPO 复现中报告约450步后差值增加、约550步超时；resume和零学习率均没有消除。其脚本是8节点×8卡，划分出judge、learner和48个单卡推理engine，不能写成64卡全部用于训练。该issue于2026-02-25以completed关闭，评论数为0；本轮未找到该线程给出的公开根因和修复。[S8]

这个案例的价值在于提示建立固定token replay，不在于用“关闭”推断已证明修复。也不据一条故障报告断言确定性开关就能解决它。

<a id="code"></a>
## 4. 真实路径：一个概率从哪里产生，最终在哪里消费

### 4.1 SGLang 生成端有两条不同的概率列

C1 的 `Sampler.forward` 先应用可能的logits处理器，再处理温度和采样。`SGLANG_RETURN_ORIGINAL_LOGPROB` 控制返回温度前还是温度后的概率；这里的original也不能在不检查前置处理器时直接叫裸模型raw。普通nongreedy路径的返回logprob与真正过滤后的采样分布，并不是凭字段名就保证相同。

C2 更清楚地分开：

```text
模型 logits → 前置处理 → 温度 → 概率 → top-k/top-p/min-p 等过滤 → sampled token
                     ↘ 一般 output logprob             ↘ 保留集 + sampling logprob
```

`_attach_sampling_mask_to_output` 使用正权重支持集及其质量，计算 `log(selected_weight / support_mass)`；greedy 分支的采样支持集为一个token，其sampling logprob=0。但greedy的一般logprob仍是模型log-softmax中的值，通常不为0。两个字段分别回答不同问题。[C1]、[C2]

当前FlashInfer联合过滤的capture部分还有明确的不变量注释：分别构造的过滤支持必须与实际fused sampler的cutoff/tie/joint语义一致。代码中有这个要求并不代表本轮已经验证所有数值边界。特别是top_logprobs返回的若干备选项不是采样完整支持集。

### 4.2 prefill scoring 与 decode scoring 的输入和实现不同

C3 的 `InputLogprobProcessor` 对已给定token串进行teacher forcing，使用对应前一位置的logits计算目标token概率；这不等于重新自由生成。其输入logprob路径与生成侧的温度／过滤分支不同，初始比较宜采用 **temperature=1、全词表、无额外processor**，避免先测了不同分布。

C3 为降低内存还提供行normalizer与chunk处理；开启deterministic时会关闭某个fast input logprob路径，以避免不同归约顺序破坏prefill/decode一致性。`(logit-max)-logsumexp(logits-max)` 也不应随意替换成 `logit-logsumexp(logits)`：巨大共同偏置下浮点舍入可以不同。本次CPU测试给出明确反例，但不是对SGLangGPU kernel的基准测试。[C3]

若序列为 $(x_0,x_1,\ldots)$，常规causal模型中 $x_j$ 的概率来自logits第 $j-1$ 行；打分列表的第一个None通常意味着缺少可定义的前缀，而不是应该补成0。不能将生成端output数组与prefill数组直接按零起点zip。[C3]、[C5]

### 4.3 miles 的 recompute 选项会改变“rollout_log_probs”来源

C5 构造全token prefill请求，设 `max_new_tokens=0`、`temperature=0`，从 `prompt_len-1` 开始取input logprob尾部，检查目标token和None。结果写回 `sample.rollout_log_probs`，并标注 `rollout_log_probs_source="sglang_prefill_recompute"`。批量路径按prompt起点和LoRA分组，并在组前flush cache。

这是一个实际来源转换点：**重算后的数值不是原来生成瞬间的数值**。它可能服务于框架明确选择的算法模式，但不能在诊断中把重算列同时当“原始行为概率”，然后宣布差异消失。

本轮没有审完该选项的全部参数互斥条件，所以不将其认定为上游bug，也不建议开启。最小要求是：独立保存原始decode列与recompute列，记录各自权重、上下文、概率语义和cache条件。**本专题的HTTP脚本不会flush共享训练服务，也不会覆盖原始capture。**[C5]

### 4.4 miles 中至少有三种概率身份

C7 实际区分：

- `rollout_old_log_probs`：sample带入的生成侧列；
- `trainer_scored_log_probs`：更新前actor重算，或特定skip模式下用当前forward.detach；
- `log_probs`：当前有梯度的forward。

`use_rollout_logprobs` 会改变PPO分母。TIS路径还比较actor旧概率与rollout概率。不能只看叫 `old_log_probs` 的局部变量就推定它代表固定哪一种policy。[C7]、[C8]

另一个诊断注意点：已读的C7分支在 `get_mismatch_metrics or use_tis` 下调用TIS函数，并接回修改后的 `pg_loss`。因此 **不要仅凭名字认定某个metrics开关没有训练副作用**。这里没有审完全部参数校验和其余调用路径，尚不宣称“只开该flag必然改变任意训练作业”；应在实际配置和最小测试中验证。

C7对某些中间量使用 `nan_to_num`，而debug dump还留有原始logprob列。诊断应检查原值，不因为清洗后的ratio有限就判为正常。这是当前通用上游路径，不代表本项目custom loss也做同样清洗。[C6]、[C7]、[P3]

### 4.5 已有 debug dump 能复用，但还不是全身份 replay 文件

C6 将TP rank0的policy loss数据写出；CP各rank保存自己的token片段。包含当前／旧／rollout logprob、advantage、local mask和中间loss；`index` 是本次microbatch内的位置。当前所读函数**不包含精确token IDs、稳定全局sample identity、支持集和版本全事实**，且 `detach().float().cpu()` 不能保留原始低精度张量的逐位形态。[C6]

所以它是好的导出起点，但不能将不同rank、不同call的index0直接视为同一轨迹。建议以已有rh2身份补充一个窄导出，而不是再建数据服务。CP>1时先按真实全局位置重建，禁止简单拼接rank0、rank1的张量。

### 4.6 项目已经修正了最明显的 raw/support 混用，不能重复推荐

P2 的实际响应代码先读 `output_token_logprobs`；开启sampling mask时再调用 `parse_turn_sampling_support`，把 `output_log_probs` 切换为support-normalized值，而原始response保留供诊断。stage后在 `record_turn` 完成时commit，防止将没有进入真实轨迹的响应当作训练样本。

P3 实际入口要求sampling replay，读CSR支持集，在gather前校验target属于support，再将mask传入上游 `get_log_probs_and_entropy`；行为列取 `batch["rollout_log_probs"]`。它检查非有限输入，不用0填补；ratio先detach，再按开放信任区间保留权重，被拒token仍留在既定provenance分母。[P2]、[P3]

**因此，下面的全词表最小probe是独立数值诊断，不是让正式faithful DIS关闭sampling replay。** 它不能直接导入该custom loss当同一个配方。正式链需要另做同一真实保留集上的概率对照，见§7。当前项目版本标签与CPU检查已经存在，也不能据此宣布硬件上全部概率一致。

<a id="math"></a>
## 5. 概率语义、重要性比率和容易误读的指标

本节是从概率定义作出的推导，并非替某论文补写未披露算法。

### 5.1 raw、温度、过滤、返回值与目标分布

设同一前缀下模型logits为 $z$，温度 $T>0$。先忽略额外processor：

$$
p_T(v)=\frac{\exp(z_v/T)}{\sum_u\exp(z_u/T)},\quad
S_K=\sum_{u\in K}p_T(u),\quad
q_K(v)=\frac{p_T(v)\mathbf{1}[v\in K]}{S_K}.
$$

对于实际采到的 $a\in K$，

$$
\log p_T(a)-\log q_K(a)=\log S_K.
$$

例如 $p=(0.6,0.3,0.1)$、保留前两项，真实质量是0.9；传入top-p=0.8也可以保留到0.9。若误把分子按全词表算、分母按保留集算，固定权重下ratio仍为0.9。连续16个这样的位置，乘积为 $0.9^{16}\approx0.1853$，**不是普遍的 $top\_p^{16}$**。实际多步应使用 $\prod_t S_{K_t}$，top-k/min-p/penalty组合还会进一步改变它。S6评论中的具体测量只属于其报告配置。[S4]、[S6]、[S7]（本次MathTests）

### 5.2 冻结采样支持集与重算当前top-p不是同一件事

若训练目标定义为在生成时保留集 $K_b$ 上比较当前分布，则应计算当前logits在**同一 $K_b$**上的归一化。重新从当前logits生成 $K_\theta$ 会改变分布支持，不能把由此产生的变化称为单纯数值误差。跨越cutoff还可能带来离散变化。

但冻结 $K_b$ 也有理论边界：它定义的是保留集上的条件目标，不自动等于完整词表策略。若目标 $p$ 在行为 $q$ 支持集之外仍有正质量，使用 $p/q$ 不能从完全未采到的区域恢复无偏期望。裁剪、拒绝采样或TIS同样不会创造缺失的数据。这不判定项目目标错误，而是要求准确描述它优化的对象。

### 5.3 greedy 与 temperature=0 的特殊性

理想greedy行为是delta分布，选中token的行为logprob为0；API返回该token在模型softmax中的logprob则通常小于0。即使没有任何数值偏差，两者也不应相等。SGLang当前代码分别输出这两种值；因此baseline概率比较使用正温度／全支持，不将一个greedy采样报告值当一般IS行为概率。[C1]、[C2]

### 5.4 当前、actor旧分布与行为分布可以逐点分解，不能混名

在所有条件变量已对齐的前提下，令 $\ell_b$ 为行为概率，$\ell_a$ 为actor旧概率，$\ell_\theta$ 为当前概率：

$$
\exp(\ell_\theta-\ell_b)
=\exp(\ell_\theta-\ell_a)\exp(\ell_a-\ell_b).
$$

第一项可以承载实际策略更新，第二项可能包含实现差异、版本差异或概率语义差异。这个恒等式不会自动告诉我们第二项的根因。异步场景里某一轮跨权重更新，多个token可能有不同生成版本；把整个response都贴最后一个version会掩盖这一事实。

参考策略用于KL、教师用于蒸馏，又是另外身份。它们与行为概率不应因字段都叫logprob而共用解释。用于数值parity时首先选择同权重、无在途更新；用于真实训练观察时版本差异本来就是预期变量，不应统统计为实现错误。

### 5.5 七个“看起来正常”的假阳性

| 观察 | 为什么不足 |
| --- | --- |
| 平均有符号差值约0 | 正负误差会相消；同时看绝对差、分位数、最大值和位置 |
| ESS接近1 | 归一化ESS对整体常数倍缩放不敏感；所有ratio=0.1也能ESS=1 |
| 贪心输出完全相同 | argmax相同不能证明分布相同 |
| 只有已采样token对齐 | 没有验证完整词表分布、其他动作或路由权重 |
| mask后loss有限 | `0*NaN`仍为NaN；若先nan_to_num又可能掩盖问题 |
| 全部token都被过滤，差值为0 | 没有证据而非完美对齐；返回INSUFFICIENT |
| loss标量相同 | detach位置不同仍可有不同梯度，见CPU反例 |

平均logprob差不能随意叫KL。即使用非负形式 `expm1(Δ)-Δ`，其作为特定KL估计的解释仍依赖采样分布、支持条件和Δ方向。此脚本故意不输出一个混淆这些前提的 `kl` 字段。

### 5.6 容差应随实验定义，不应照抄“1e-7”

bitwise测试、同backend重复测试、跨dtype forward测试和实际梯度对照，需要不同判据。先测同路径重复的数值底噪，再预先设阈值；不能观察结果后逐步放宽到通过。

均匀上界 $|\Delta_t|\le\epsilon$ 可推出选定token乘积比率位于 $[e^{-n\epsilon},e^{n\epsilon}]$；但tokenwise PPO并不直接使用整串乘积，GSPO等归一化方式也不同。因此“长序列误差会累积”的说法必须配合实际目标，不将序列比率的极端界自动当成训练崩溃预测。

本比较器的PASS只表示用户指定绝对logprob容差下的**所给固定样本**通过，不是硬件认证或模型发布门槛。

## 6. MoE、稀疏注意力和低精度：需要按失败路径加测

**MoE routing。** 两端token相同仍可能选择不同专家；应检查每token、每层的route IDs、选择顺序、gate权重与有效token对应。R3能固定选路这一类离散差异，但不保证expert计算、gate数值、EP通信或capacity/token dropping一致。只记录“返回过routing tensor”不等于训练实际回放。当前项目已有routing运输线，本次未完整审其模型内部消费，不标已验证。[S5]、[S6]、[P1]

**DSA或其他索引。** 索引可能是另一个需要重放的离散状态，但先确认目标模型确实存在该机制。不要为当前不采用的架构增加强制字段；RFC中的forward-looking条目不是本项目当前必要任务。[S5]

**dtype与量化。** 将最后返回值cast成fp32不能恢复bf16/FP8中已经损失的信息；raw logits的lm_head精度、log-softmax归约、KV dtype与量化scale更新分别需要记录。跨架构实现可以有合理数值差，重要的是是否与声明目标和梯度容差相容。

**随机性。** 固定seed可帮助重复，但许多采样实现的随机流受batch调度影响；应分别测试固定token的概率与自由生成的样本。确定性debug不能把所有组成员都设成同一seed、再把重复轨迹误认为8次独立探索。

**性能代价。** 更稳定的归约、禁用fused路径、记录支持集/routing和重算prefix都消耗资源。比较时应同时报告实验范围内的wall time、峰值显存及实际有效token，不将debug模式的高保真自动作为最终吞吐配置。

<a id="protocol"></a>
## 7. 最小可运行检查：按层定位，不一次开齐所有变量

### 7.1 四条轨道各自回答一个问题

| 轨道 | 主要材料与对照 | 失败后优先查什么 |
| --- | --- | --- |
| A 原始分布数值诊断 | 固定原始token，T=1/full vocab/无processor；同服务重复、同backend不同布局、再跨backend | 输入shift、cache、dtype、计算布局与权重一致性 |
| B 实际行为／目标分布 | 固定同一采样保留集与温度，比较生成时effective logprob与trainer条件概率 | 支持集真值、归一化、字段运输、实际目标定义 |
| C 同样本梯度 | 固定A/B所选语义，再固定advantage、mask、分母、参数映射和optimizer边界 | detach、丢样本、packing、CP/DP归约与辅助loss |
| D 在线作业观察 | 固定规则但允许策略更新，记录原始行为、重算、当前概率和版本分层 | staleness、重试、数据组成变化、缓存／发布状态 |

A通过不能代替B；B通过不能代替C；D的平均值变化不能代替固定样本的A–C诊断。A是独立服务probe，**不得为了跑A临时改正式faithful DIS的sampling contract**。

### 7.2 先冻结一个很小但有辨识力的fixture

首批建议用实际模型捕获的若干短序列：普通文本、工具调用控制token、多轮tool observation、停止标记边界，以及一个上下文改写后的真实LLM-call。每个case保存完整实际前缀和要比较的位置；不同case长度可以覆盖一个真实chunk边界，但不一上来保存32K×完整词表logits。

从相同decode轨迹取原始token，不让teacher和student各自生成。保留未被clipping筛选的合法位置作为诊断总体，避免只看幸存token。需要隐藏材料的任务先脱敏或改用合成fixture，本诊断无需真实私有代码／用户资料。

本次HTTP/HF桥只支持**纯文本、无padding、普通causal位置**。复杂attention mask、position改写、多模态、routing回放、树状prefix和CP布局必须由真实训练端适配，脚本会拒绝冒充这些情况的输入，而不是静默丢字段。

### 7.3 实验顺序与逐项控制

1. **单服务重复打分。** 冻结权重并排空更新，固定input_ids，重复prefill scoring。A/A不通过时不要急着跨backend比较。
2. **同服务布局变化。** 改客户端并发、相邻请求长度与请求顺序；记录实际GPU batch遥测，客户端并发数不等于GPU batch size。
3. **cache／prefill变化。** 用隔离debug服务分别测cache开关、chunk、CUDA graph。HTTP脚本不自动flush生产服务；单纯prefill打分也可能走特殊cache路径，必须记录真正命中的路径。
4. **decode与prefill。** 保存生成时原始token及logprob，随后固定序列重算。不能先把生成列覆写再比较；服务的打分API不自动等于真实decode replay。
5. **跨实现。** 同权重、token和概率语义比较HF、SGLang与真实trainer。HF eager只作额外参照，不充当Megatron正确性的权威oracle。
6. **MoE与TP/CP。** 在前面最小条件稳定后，再逐个开启routing replay、TP/EP、packed或CP。不同拓扑同时改变很难归因。
7. **参数更新前后。** 只有A–C清楚后，才把实际staleness与权重发布加入。这个阶段接受合理的策略差异，不要求所有ratio恒为1。

不需要把这些组合做完整笛卡尔积。先沿实际工作负载的最小失败条件二分；配对改变一个层次能比几十组无记录的flags提供更有用的证据。

### 7.4 从现有 miles dump 到可比较文件

最小新增导出应复用C6/P2的现有identity，补齐该call的原始input_ids、全局response位置、原始behavior列、effective behavior列、actor-old/current列和对应mask；支持集/routing可独立引用已有capture，不重复构造一套事实源。

CP恢复需要按真实全局offset定位，局部空片段不能提前退出collective。权重标签按token provenance填写，不把整个样本强制标最后版本。若某段原始call前缀已经丢失，状态应为缺证据；不能以merge后的当前消息重新渲染来补造历史。

这次没有提交生产导出器：字段怎样进入既有debug路径属于项目实现决策，且新的工作分支尚未被准确识别。提供的离线schema只是测试夹具，不是新增跨后端公共IR。

<a id="tests"></a>
## 8. 本次实际交付与运行证据

### 8.1 文件与功能

[运行说明](probes/infra07/README.md)、[比较与打分脚本](probes/infra07/replay_check.py)、[测试](probes/infra07/test_replay_check.py)、[CPU结果](probes/infra07/cpu_results_20260908.json)。

| 功能 | 实际状态 |
| --- | --- |
| 离线JSON配对比较 | 已运行测试；严格核对身份、token、位置、mask、概率合同、支持集及已有routing信息 |
| 数学／autograd反例 | 已在CPU torch执行；支持集质量、IS分解、grad detach、mask NaN、log-softmax、shift |
| SGLang prefill HTTP调用代码 | 已用本地mock服务检验请求和返回解析、并发与错误分支；**未连接真实SGLang** |
| 本地HF eager打分入口 | 已语法检查；未安装transformers、未加载模型、**未执行** |
| CUDA／TP／EP／CP／真实训练 | 未执行；CPU测试不是替代证据 |
| 性能收益与上游bug复现 | 没有测得；不从33个测试推断新加速比或上游故障已复现 |

### 8.2 33项测试覆盖

**21项合同与指标测试**：正常配对、按身份恢复顺序、重复／缺失记录、同长不同token、可见文字相同的误导、位置0、概率语义不同、版本不同、全零mask、NaN、工具观察占位、正负误差相消、ESS比例盲区、支持集缺目标或改变、routing不同、超大log-ratio、输入根损坏、上下文mask不同、拒绝capture不支持的复杂位置。

**9项数学／autograd测试**：真实支持质量非top-p参数、缺失支持不能用IS恢复、三概率恒等式、greedy行为概率、相同forward不同梯度、`0*NaN`、softmax下溢、共同偏置下归一化次序，以及causal logits的前一行索引。

**3项本地HTTP测试**：固定输入／明确起点／不生成新token；服务返回错误token时拒绝；并发请求与重复试验的身份保持。测试服务仅模拟JSON协议，不模拟GPU kernel、scheduler或SGLang实现。

合计实际执行 **33 tests，0 failures，0 errors，0 skipped**，结果文件保存了测试名、Python/torch环境、完整输出与数值。新增反例都是独立构造，不等同导入上游函数做回归测试。

### 8.3 结果的几个具体含义

在合成概率 $(0.6,0.3,0.1)$ 上，保留集质量0.9导致约−0.10536的logprob偏置；16位置的比率约0.18530，而0.8的16次方约0.02815。二者明显不同，验证了必须记录真实支持质量。

一个配对样本的差值为+0.1与−0.1时，有符号均值约0，但比较器正确返回FAIL。全部有效位置都偏移−1时，归一化ESS仍为1，但ratio检查并不正常。所有mask为0时返回INSUFFICIENT，而非PASS。

两个表达式 `-stopgrad(exp(x+1))*x` 与 `-exp(x+1)*x` 在x=−1的forward相等，梯度分别为−1与0。因此只对拍loss值不足以证明DIS/TIS的stop-gradient语义。

### 8.4 脚本退出状态不是训练门禁

`PASS`=0、`FAIL`=1、`INCOMPARABLE`=2、`INSUFFICIENT`=3。容差必须显式传入，无默认“1e-7即合格”。标签匹配是必要而非充分证据：脚本无法远程验证操作者给的checkpoint标签是否真实；未提供route也不意味着已证明route一致。字段和工具应服务一次可解释实验，不应变成阻塞所有训练的新审批系统。

<a id="project"></a>
## 9. 对 RepoHarness 的直接结论与候选改进

### 9.1 哪些旧建议需要收紧

**“只要精确token就保证正确”不成立。** 当前还有支持集、温度、前缀状态和目标函数语义；TITO主要解决序列身份。

**“固定权重后应该所有logprob均为零差”需要范围。** 必须同分布、同输入、相容实现；跨dtype或kernel可有合理差异，不能从数学理想直接选一个适用于所有配置的阈值。

**“上游sampling mismatch意味着我们需要新实现”不成立。** P2/P3已经实现有效行为列和固定支持集消费；下一步应验证这条真实路径，而非再造一套支持集重放。

**“某个async设置与sync同样本更新必须相等”不能无条件成立。** 更新顺序、目标定义、样本集合和归一化可能被设计为不同；应先说明是在验证语义保持优化，还是在比较不同学习策略。

### 9.2 最值得做的三项窄工作

| 候选 | 已有基础 | 本次建议的增量与证据 | 不在本次范围 |
| --- | --- | --- | --- |
| 原始／effective／重算列并存的固定样本导出 | capture raw_response、sampling support、miles dump、既有identity | 在现有debug出口关联完整call与训练位置，给出原始保留列；验证不开优化器时也能重放 | 不增WAL、通用IR、服务或第二版staleness权威 |
| 正式模型的双轨parity | 项目SGLang pin、faithful DIS支持集目标 | 独立全词表debug服务查数值；正式接口按原K/温度查loss概率，分别报告 | 不为跑debug修改正式loss合同、不假定最新main已采用 |
| 只对测得的高占比差异做最小复现 | 已有CPU检查与上游测试入口 | 保留一个真实失败fixture，比较backend/TP/cache单变量，再判断是否提上游PR | 不预设每个线程必须发现bug；不直接发送issue或升级依赖 |

R3、backend、低精度等只有在具体失败路径需要时才扩读。当前机器的瓶颈若仍主要是环境执行，数值检查仍是必要诊断，但不能据此承诺吞吐改善。

### 9.3 什么能写成工程成果

本次成果是**一套可复核的分析与诊断基线**，不是已经完成的训推一致性优化。真正的后续系统贡献可以是：用真实样本定位一个上游／集成差异，给出最小复现和窄修复，在相同计算条件下保持语义并降低成本。它不必每项都声称获得“新智能”；但凡改了样本分布、mask、loss或实际工具信息，就需要补学习或行为结果，不能只报告速度。

## 10. 未决项、补读位置与审查状态

| 未决项 | 为什么尚未得出结论 | 最小补充 |
| --- | --- | --- |
| 用户新工作分支确切身份 | 当前可见研究分支属于另一任务 | 后续集成时按实际branch/commit更新项目映射 |
| 真实GPU的误差量级与容差 | 本环境CPU，无目标模型／引擎 | 先一组固定token A/A，再A/B；保留失败与成本 |
| 项目R3模型内部回放／KV失效 | 本轮仅核capture和loss边界 | 追实际模型、发布与缓存消费路径，不按字段存在推定 |
| C5 recompute所有允许组合 | 未完整审参数验证与全部调用者 | 针对实际启动配置补一个小路径检查 |
| C7 metrics开关实际训练副作用 | 已见loss分支接回，但未审所有guard | 最小配置对拍目标/梯度，先不要直接定性上游bug |
| vLLM所有PR与现代release支持 | RFC和一个合并PR并不足够 | 按目标版本检查实际feature+tests，不逐项扫全生态 |
| 真正固定权重状态 | 标签、manifest是声明，非GPU张量证明 | 对debug作业记录加载完成和必要的参数/scale校验 |
| 独立审查 | 当前工具没有独立sub-agent | 交另一线程／本地Codex复核，不编造审查通过 |

**作者自查完成、独立审查未完成**。自查范围与已执行记录见 [infra07自查](reviews/infra07_train_inference_self_check_20260908.md)。本次没有执行任何收费API、远程GPU训练、生产参数变更或上游PR提交。

## 11. 一手链接与快速回查

以下引用稳定到版本或明确访问日期；issue正文会变化，状态仅代表2026-09-08所见。源码的函数和阅读范围见§1.3，不能将链接整文件等同整文件都被审查。

[S1]: https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/
[S2]: https://www.lmsys.org/blog/2025-09-22-sglang-deterministic/
[S3]: https://docs.sglang.io/docs/advanced_features/deterministic_inference
[S4]: https://docs.vllm.ai/en/v0.25.0/api/vllm/config/model/
[S5]: https://github.com/vllm-project/vllm/issues/48305
[S6]: https://github.com/vllm-project/vllm/issues/42259
[S7]: https://github.com/vllm-project/vllm/pull/49577
[S8]: https://github.com/allenai/open-instruct/issues/1473
[C1]: https://github.com/sgl-project/sglang/blob/4e230c3d85cefdab5b65eeb6f6f87793a707a6fb/python/sglang/srt/layers/sampler.py
[C2]: https://github.com/sgl-project/sglang/blob/554f817948c26e8e9c8338b4a33e94a609d6f0fb/python/sglang/srt/layers/sampler.py
[C3]: https://github.com/sgl-project/sglang/blob/4e230c3d85cefdab5b65eeb6f6f87793a707a6fb/python/sglang/srt/layers/logprob_processor.py
[C4]: https://github.com/sgl-project/sglang/blob/554f817948c26e8e9c8338b4a33e94a609d6f0fb/python/sglang/srt/arg_groups/attention_hook.py
[C5]: https://github.com/radixark/miles/blob/3de96596f16b9e6d23ba550c4c47de3479c9f14c/miles/rollout/generate_utils/prefill_logprobs.py
[C6]: https://github.com/radixark/miles/blob/3de96596f16b9e6d23ba550c4c47de3479c9f14c/miles/backends/training_utils/debug_dump.py
[C7]: https://github.com/radixark/miles/blob/3de96596f16b9e6d23ba550c4c47de3479c9f14c/miles/backends/training_utils/loss_hub/losses.py
[C8]: https://github.com/radixark/miles/blob/3de96596f16b9e6d23ba550c4c47de3479c9f14c/miles/backends/training_utils/loss_hub/corrections.py
[P1]: https://github.com/Rogerffff/RepoHarness/blob/d2df06d49e42b93436d10d1b7a12d4e1f0ae3be5/docs/agentic_RL/repo_harness_rh2_workstreams/miles_spike/integration_base_manifest.json
[P2]: https://github.com/Rogerffff/RepoHarness/blob/d2df06d49e42b93436d10d1b7a12d4e1f0ae3be5/rh2/src/repoharness2/adapters/slime/capture_wire.py
[P3]: https://github.com/Rogerffff/RepoHarness/blob/d2df06d49e42b93436d10d1b7a12d4e1f0ae3be5/rh2/src/repoharness2/adapters/miles/faithful_dis_loss.py
[P4]: https://github.com/Rogerffff/RepoHarness/blob/d2df06d49e42b93436d10d1b7a12d4e1f0ae3be5/docs/agentic_RL/repo_harness_rh2_workstreams/CURRENT-STATE-BRIEF.md
