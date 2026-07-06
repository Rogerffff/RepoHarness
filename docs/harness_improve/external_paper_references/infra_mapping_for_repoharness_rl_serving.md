# RepoHarness 强化学习推理与训练基础设施映射报告

本文把本次粘贴的四份基础讲义中涉及的长上下文、推理服务、低精度、MTP、OPD / MOPD 等基础设施内容，映射到 RepoHarness 的长期架构和后续训练设计中。本文不讨论模型结构本身如何实现，因为 RepoHarness 的目标不是训练一个新模型架构，而是在现成模型、训练框架和推理服务之上，构建可执行、可审计、可导出的软件工程智能体训练环境。

本文重点回答三个问题：

```text
1. 哪些基础设施问题会影响 RepoHarness 的环境、rollout 和训练样本设计？
2. 哪些能力已经由 verl、slime、vLLM、SGLang 或 Megatron 这类框架和服务承担？
3. RepoHarness 自己应该实现什么，应该记录什么，应该避免自研什么？
```

## 1. 总体结论

RepoHarness 不应该自己实现模型架构、推理内核、KV cache 管理、prefill / decode 拆分、MTP、低精度量化内核、训练权重同步或分布式训练队列。这些能力属于训练框架和推理服务的责任范围。

但是，RepoHarness 必须把这些能力对训练样本可信度的影响显式写进运行期契约。也就是说，RepoHarness 不实现底层推理系统，但它必须知道并记录：

```text
1. 模型实际看到的 prompt token ids。
2. 模型实际采样出的 response token ids。
3. 每个 response token 的 logprob 来源、精度和对齐状态。
4. 哪些 token 进入 loss，哪些 token 只是工具观察、环境反馈或 padding。
5. 这次模型调用使用的 sampling_params、上下文预算、推理后端和权重版本。
6. 该 rollout 属于哪个 task、group、session、policy version 和训练后端消费批次。
7. 这条轨迹是否因为 staleness、低精度风险、logprob 缺失、reward 归因不足或安全问题被拒绝进入训练。
```

因此，当前高层设计文档中提出的方向仍然合理：

```text
Prime-style composable environment
+ Polar-style rollout / model boundary capture
+ renderers-style token fidelity
+ verl / slime 等训练后端适配器
```

但在落地时需要补上一层非常清晰的认识：推理基础设施不是 RepoHarness 的内部实现细节，而是训练资格的一部分。一个 rollout 能不能训练，不只取决于环境是否成功完成，也取决于它的 token、logprob、权重版本、sampling 参数、后端精度和训练消费状态是否可证明。

## 2. 本次讲义中的基础设施主题

### 2.1 长上下文不是能力本身，而是训练环境能否扩展的前提

软件工程智能体任务往往包含仓库文件、任务描述、工具 schema、历史命令、测试输出、失败日志和多轮修复过程。长上下文让模型可以看到更多状态，但也会显著增加：

```text
1. prefill 计算成本。
2. KV cache 显存和带宽成本。
3. 多轮工具调用后的 append-prefill 成本。
4. logprob 重算和训练 forward 成本。
5. teacher model 在 OPD / MOPD 中重新读取长上下文的成本。
```

对 RepoHarness 的含义是：不能把“支持更长上下文”等同于“把所有 observation 无限制塞回 prompt”。RepoHarness 需要的是上下文预算策略、观察结果投影、prefix 结构化记录和训练样本 token 级可追溯，而不是在环境层实现新的长上下文模型结构。

### 2.2 Agent rollout 的瓶颈常常在推理服务和环境等待，而不只在 trainer

普通监督微调可以提前准备样本。Agent 强化学习必须让当前策略在环境里行动，产生新轨迹，再把轨迹交给训练框架。对于长程软件工程任务，单条轨迹可能包含几十次模型调用和大量工具执行等待。因此总体吞吐受以下部分共同限制：

```text
rollout 推理吞吐
+ 工具和沙箱执行速度
+ verifier / reward 速度
+ 训练框架消费速度
+ 权重同步和 policy staleness
+ teacher serving 或 logprob 重算速度
```

这就是为什么 RepoHarness 的长期架构不能只是一个 Python 函数式 harness。它需要在近期以 `trainer_native` 方式被 verl 或 slime 调用，在长期保留服务化 rollout 的空间，并且所有路径都要产出同一类可审计 `TrajectoryArtifact`。

### 2.3 prefill、decode、KV cache、PD disaggregation 是推理服务职责

讲义中的 prefill / decode 基础说明了一个重要事实：

```text
prefill 负责处理 prompt 并生成 KV cache。
decode 负责基于 KV cache 一个 token 一个 token 生成后续内容。
KV cache 决定长上下文并发能力、decode latency、session locality 和 prefix reuse 价值。
```

prefill-decode disaggregation 可以把 prefill worker 和 decode worker 拆开，避免长 prompt 阻塞 decode。但它也会引入 KV transfer 成本，因此不是所有规模都应该一开始采用。

对 RepoHarness 的含义是：

```text
RepoHarness 不实现 prefill / decode 拆分。
RepoHarness 不实现 KV cache 池。
RepoHarness 不实现 PagedAttention、chunked prefill 或 KV transfer。
RepoHarness 应该把 task prefix、session_id、group_id、prompt token 数、response token 数、prefix cache 命中统计和推理后端配置记录成事实。
```

这样当 verl、slime、vLLM 或 SGLang 启用 prefix caching、chunked prefill、PD disaggregation 或 consistent hashing 时，RepoHarness 可以提供稳定的调度提示和审计信息，而不是把底层策略写死在环境层。

### 2.4 低精度影响的不只是速度，还影响训练信号可信度

低精度和量化可以降低权重、activation、KV cache、logits 和 teacher model 的内存与带宽成本。它对 rollout 扩展非常重要，尤其是 FP8 KV cache、FP8 / INT8 rollout、量化 teacher serving 等。

但对强化学习和 OPD / MOPD 来说，低精度不能只当作“省显存开关”。它会影响：

```text
1. rollout policy 的采样分布。
2. response_logprobs 的数值偏差。
3. old_log_probs / rollout_log_probs / current log_probs 的比值稳定性。
4. KL、importance sampling、advantage 和 policy loss。
5. teacher logits 或 teacher_log_probs 的分布质量。
6. tool call JSON、代码编辑、命令字符串等格式敏感输出。
```

对 RepoHarness 的含义是：低精度策略应该由训练框架和推理服务执行，但 RepoHarness 需要记录推理后端精度、logprob 生产方式、teacher 精度、KV cache 精度配置摘要，以及失败是否可能来自数值或后端行为变化。否则后续训练失败时无法区分“模型能力不足”和“rollout 服务数值配置改变”。

### 2.5 MTP 和 speculative decoding 是吞吐优化，不是 RepoHarness 核心能力

MTP 可以作为 speculative decoding 的 drafter，提高 decode 吞吐。它对 agent 强化学习重要，因为 agent rollout 需要大量 decode。

但 MTP 需要模型结构、推理服务和训练 recipe 支持。它还会受到 policy drift 影响：如果 RL 过程中策略持续更新，而 draft 分布没有同步更新，acceptance rate 会下降，推理加速会失效。

对 RepoHarness 的含义是：

```text
RepoHarness 不实现 MTP heads。
RepoHarness 不实现 speculative decoding 接受 / 拒绝规则。
RepoHarness 应记录 speculative decoding 相关后端统计，例如 draft token 数、accept token 数、acceptance rate、使用的 speculative algorithm。
RepoHarness 必须继续以最终被目标模型接受的 response token ids 和 logprobs 为训练事实，不能把 draft token 当成训练 token。
```

slime 的 `Sample.SpecInfo` 已经记录 `spec_accept_token_num`、`spec_draft_token_num`、`spec_verify_ct` 和 `completion_token_num`。这类字段对 RepoHarness 很有参考价值，但它们应该作为后端运行事实进入 artifact 或 training runtime record，而不是改变环境语义。

### 2.6 OPD / MOPD 是算法，也是 teacher serving 系统

OPD / MOPD 不只是一个 KL loss 公式。它要求在 student rollout 之后让 teacher model 给出 token-level log probability、logits 或更完整的分布信号。对于长上下文 agent rollout，这会带来很高的 teacher serving 成本。

对 RepoHarness 的含义是：

```text
RepoHarness 不应该一开始实现完整 multi-teacher full-vocabulary distillation。
RepoHarness 应该先支持 selected-token 或 response-span 级别的 teacher_log_probs。
RepoHarness 应通过 backend_tensors 注册制承接 teacher_log_probs、top_p_mask、routed_experts 这类训练后端张量。
RepoHarness 应记录 teacher model id、teacher precision、teacher weight version、teacher scoring span 和 teacher logprob 对齐状态。
```

slime 的 OPD 示例已经展示了两种 teacher 路径：外部 SGLang teacher server 在 rollout 时返回 teacher logprobs，或者 Megatron 在训练 forward 阶段加载 teacher 并计算 teacher logprobs。RepoHarness 可以借鉴这种“teacher 是训练后端或推理服务拥有的模型，RepoHarness 只保存对齐事实和张量引用”的边界。

## 3. 现成框架和服务已经覆盖的能力

### 3.1 verl 已覆盖或正在覆盖的能力

本地 `reference/verl` 中已经能看到多个和 RepoHarness 直接相关的基础设施点。

关键代码和文档位置：

```text
reference/verl/AGENTS.md
reference/verl/verl/experimental/agent_loop/agent_loop.py
reference/verl/verl/experimental/agent_loop/tool_agent_loop.py
reference/verl/verl/workers/config/rollout.py
reference/verl/verl/workers/config/disaggregation.py
reference/verl/verl/experimental/fully_async_policy/
reference/verl/verl/trainer/ppo/rollout_corr_helper.py
reference/verl/verl/trainer/ppo/core_algos.py
reference/verl/examples/prefix_grouper/README.md
reference/verl/docs/data/transfer_queue.md
reference/verl/docs/README_vllm0.8.md
```

已经具备参考价值的能力包括：

```text
1. AgentLoopOutput 已包含 prompt_ids、response_ids、response_mask、response_logprobs 和 reward_score。
2. ToolAgentLoop 会把模型生成 token 的 response_mask 置 1，把工具 observation 或 padding 的 response_mask 置 0。
3. RolloutConfig 默认 rollout mode 为 async，并包含 temperature、top_p、top_k、response_length、dtype、gpu_memory_utilization、logprobs_mode、calculate_log_probs、enable_chunked_prefill、checkpoint_engine、MTP、QAT、disaggregation 等配置入口。
4. FullyAsyncPolicy 路径中存在 rollouter、trainer、MessageQueue、staleness threshold、reset_staleness 等运行期协调逻辑。
5. rollout_corr_helper 支持基于 rollout_log_probs 和 old_log_probs 的 importance sampling、rejection sampling 和 off-policy / staleness 相关校正。
6. PrefixGrouper 示例说明训练侧可以按相同 prompt prefix 合并或减少重复 attention 计算。
7. TransferQueue 文档说明 verl 生态正在向更细粒度的 producer-consumer 数据流、KV-style storage 和 streaming dataloader 演进。
```

对 RepoHarness 的判断：

```text
近期使用 verl 时，RepoHarness 应优先走 trainer_native。
verl 拥有 rollouter、MessageQueue、推理资源池、权重同步、staleness 控制和训练消费节奏。
RepoHarness 提供一个 verl 自定义 AgentLoop 或 episode runner，产出能投影成 AgentLoopOutput / DataProto 的训练视图。
VerlAdapter 不是简单格式转换器，它还要把 RepoHarness 的 token provenance、loss mask、reward facts、group_id、staleness facts 和 backend rejection reason 映射到 verl 能消费和能审计的字段。
```

### 3.2 slime 已覆盖或正在覆盖的能力

本地 `reference/slime` 中能看到 slime 更偏 SGLang-native 的训练运行时设计。

关键代码和文档位置：

```text
reference/slime/AGENTS.md
reference/slime/train_async.py
reference/slime/slime/ray/rollout.py
reference/slime/slime/rollout/sglang_rollout.py
reference/slime/slime/rollout/fully_async_rollout.py
reference/slime/slime/utils/types.py
reference/slime/slime/backends/megatron_utils/actor.py
reference/slime/docs/en/blogs/introducing_slime.md
reference/slime/docs/en/examples/qwen3-4B.md
reference/slime/examples/fully_async/README.md
reference/slime/examples/on_policy_distillation/README.md
reference/slime/examples/delta_weight_sync/README.md
```

已经具备参考价值的能力包括：

```text
1. slime 以 SGLang server 和 sgl-router 为核心，支持把 SGLang 参数通过 --sglang-* 透传给底层服务。
2. Sample 包含 tokens、response_length、loss_mask、rollout_log_probs、teacher_log_probs、rollout_routed_experts、weight_versions、status、session_id、spec_info 和 prefix_cache_info。
3. sglang_rollout.generate 使用 input_ids 调用 SGLang，设置 return_logprob=True，并直接读取 output_token_logprobs 中的 token id 和 logprob，避免重新分词。
4. session_id 可以通过 consistent hashing 路由，帮助后端保持 session locality。
5. Dynamic sampling 支持 over-sampling、过滤完整 rollout group，并通过 SGLang 的 /abort_request 终止不再需要的请求。
6. Partial rollout 可以把被中止的样本放入 buffer，后续继续或重新使用。
7. train_async.py 采用 Ray future 做训练和下一轮 rollout 的双缓冲式异步。
8. fully_async_rollout 通过后台 asyncio worker 保持固定数量的 in-flight generation，减少长尾样本拖慢训练步。
9. OPD 示例展示了 teacher_log_probs 可以在外部 SGLang teacher 或 Megatron teacher 路径中产生，并进入训练侧。
10. delta weight sync 示例说明 slime 在训练 / 推理解耦时已经考虑增量权重同步。
```

对 RepoHarness 的判断：

```text
未来使用 slime 时，RepoHarness 应优先成为 slime custom_generate 或 rollout function 里的环境执行组件。
slime 拥有 SGLang router、训练和推理资源划分、data buffer、partial rollout、动态采样、权重同步和 Megatron 训练。
RepoHarness 提供 task materialization、sandbox、工具权限、用户模拟、verifier、reward facts 和 token-faithful trajectory。
SlimeAdapter 应负责把 TrajectoryArtifact 投影成 slime.Sample 或 RolloutBatch 所需字段，尤其是 tokens、loss_mask、rollout_log_probs、teacher_log_probs、rollout_id、session_id、status 和 metadata。
```

### 3.3 vLLM 和 SGLang 应承担的能力

本次没有必要把 vLLM 或 SGLang 源码重新纳入 RepoHarness 主架构。原因是 verl 和 slime 已经通过配置、server client 和 router 把这些服务暴露给训练链路。

vLLM / SGLang 这类推理服务应承担：

```text
1. continuous batching。
2. KV cache 和 paged KV cache 管理。
3. prefix caching 或 radix cache。
4. chunked prefill。
5. logprob 返回。
6. speculative decoding 或 MTP 相关推理路径。
7. FP8 KV cache、FP8 / INT8 / INT4 等推理量化支持。
8. prefill / decode disaggregation 或相关实验功能。
9. 多模型或 teacher server 部署。
10. SGLang router、consistent hashing、request abort 等服务端能力。
```

RepoHarness 对这些服务的正确使用方式是：

```text
1. 通过训练后端管理的 client 调用服务。
2. 传入明确的 sampling_params 和上下文预算。
3. 请求 token ids 和逐 token logprobs。
4. 保存后端返回的 token、logprobs、finish_reason、weight_version、prefix cache 和 speculative decoding 统计。
5. 不把服务端没有承诺的行为伪装成 token-faithful 训练事实。
```

## 4. 主题到 RepoHarness 责任边界的映射

| 基础设施主题 | 对软件工程智能体训练的重要性 | 现成框架或服务通常承担什么 | RepoHarness 应该承担什么 | RepoHarness 不应该承担什么 |
| --- | --- | --- | --- | --- |
| 长上下文 | 仓库任务、工具历史、测试日志和多轮修复都依赖上下文，但上下文越长成本越高。 | 模型支持的最大上下文、长上下文 attention、推理服务的 `max_model_len` 和训练框架的序列并行。 | 上下文预算、observation 投影、prompt token 数记录、截断原因、任务 prefix digest、历史压缩策略。 | 新模型结构、长上下文 attention kernel、Mamba / DSA / Lightning Attention 实现。 |
| prefill / decode | agent 每轮工具调用后都要 append 新观察，再生成下一步动作。 | vLLM / SGLang 负责 prefill、decode、continuous batching、chunked prefill、KV cache。 | 记录每次模型调用的 prompt 长度、response 长度、session_id、后端拓扑摘要和失败原因。 | 自己拆 prefill / decode worker，自己传 KV cache。 |
| KV cache 与 prefix caching | 同一任务的多个 rollout 共享 system prompt、工具 schema、仓库摘要和任务描述。 | 推理服务负责 KV cache、prefix cache、session locality。 | 提供稳定 group_id、session_id、task_prefix_digest；记录 cached_tokens、total_prompt_tokens、prefix cache 命中统计。 | 自研 global KV cache pool 或 PagedAttention。 |
| prefix-tree / PrefixGrouper | 长 prefix 在 GRPO 多样本训练里会被重复计算。 | verl 的 PrefixGrouper 或训练后端 attention patch 负责训练侧优化。 | 保证同一 task / group 的样本有稳定 uid、prefix digest 和 rollout group 信息，方便 adapter 分组。 | 在环境层实现训练 attention 合并。 |
| 异步 rollout / training | 长尾环境会拖慢 trainer，权重更新和 rollout 生成不在同一时钟上。 | verl 的 FullyAsyncRollouter、MessageQueue、staleness；slime 的 train_async、RolloutManager、data buffer、fully_async worker。 | 记录 `TrainingRuntimeRecord`、policy version、weight_version_seen_by_engine、staleness、backend_rejection_reason、FailureRecord。 | 重写训练框架的权重同步、队列、Ray 调度、partial rollout 核心。 |
| low precision / quantization | 影响 rollout 吞吐、KV cache 容量、logprob 偏差和 teacher logits 质量。 | Megatron / FSDP / vLLM / SGLang / Transformer Engine 负责 BF16、FP8、INT8、INT4、FP8 KV cache 等实现。 | 记录 rollout policy precision、training precision、KV cache precision、teacher precision、logprob source 和数值配置摘要；把低精度作为实验变量。 | 自研量化格式、FP8 / FP4 kernel、loss scaling recipe。 |
| MTP / speculative decoding | 可能提高 decode 吞吐，但受 acceptance rate 和 policy drift 影响。 | 模型和推理服务负责 MTP heads、draft、verify、accept / reject。 | 记录 speculative algorithm、draft token 数、accepted token 数、acceptance rate；只使用最终被接受的 response token 作为训练事实。 | 自己实现 MTP head 或 speculative sampling 规则。 |
| logprob collection | PPO / GRPO / OPD 都依赖 token-level logprob。 | vLLM / SGLang 返回 logprobs；verl / slime 也可在训练侧重算 old_log_probs、ref_log_probs、teacher_log_probs。 | 校验 response_ids 与 response_logprobs 逐 token 对齐；缺失时降级训练资格；记录 logprob_alignment_status。 | 用重新分词文本伪造 logprob 对齐。 |
| OPD / MOPD teacher serving | teacher logits 或 teacher_log_probs 是训练信号，成本很高。 | slime OPD、verl teacher_loop、外部 SGLang teacher、Megatron teacher 负责 teacher forward。 | 通过 backend_tensors 注册 teacher_log_probs；记录 teacher model、precision、span、对齐状态和可见性。 | 一开始实现 full-vocabulary multi-teacher distillation 服务。 |
| dynamic sampling / group filtering | GRPO / DAPO 等常需要组内通过率过滤和 early exit。 | slime dynamic sampling、partial rollout、abort_request；verl 训练驱动或算法层处理 group 和 rejection。 | 输出 raw reward facts、group_id、parent_rollout_id、rollout_loss_denominator、backend_rejection_reason。 | 把 reward normalizer 或 group pass-rate 过滤写进环境核心。 |
| artifact / queue / streaming data | 异步训练需要生产者和消费者解耦。 | verl MessageQueue、TransferQueue、DataProto；slime Ray future、data buffer、RolloutBatch。 | 定义 `TrajectoryArtifact`、可审计 artifact store、adapter 输出契约和 public-safe projection。 | 假设所有训练后端都必须使用同一个 MessageQueue。 |

## 5. 对 RepoHarness 内部设计的具体影响

### 5.1 CompletionRecord 应成为“模型调用事实”的唯一入口

每一次模型调用都应该形成一个 `CompletionRecord` 或等价记录。该记录不只是保存文本，而是保存训练需要的事实：

```text
prompt_ids
response_ids
response_logprobs
loss eligibility span
sampling_params
sampling_params_digest
tokenizer / chat_template 信息
serving_backend
serving_backend_version
inference_engine_name
behavior_policy_version
weight_version_seen_by_engine
finish_reason
prompt_token_count
response_token_count
token_provenance_status
logprob_alignment_status
```

如果未来要记录 prefix cache、speculative decoding 或低精度信息，可以采用小的后端事实扩展段，而不是把所有字段塞进松散 metadata。例如：

```text
serving_runtime_facts:
  prefix_cache_cached_tokens
  prefix_cache_total_prompt_tokens
  speculative_draft_tokens
  speculative_accepted_tokens
  speculative_acceptance_rate
  rollout_precision_policy_digest
  kv_cache_precision
  pd_topology_summary
```

这些字段不是为了让 RepoHarness 控制 vLLM 或 SGLang，而是为了让后续训练结果可解释、可复现、可过滤。

### 5.2 TokenTapeBuilder 和 RendererBinding 仍然重要

即使底层推理服务可以返回 token ids 和 logprobs，RepoHarness 的白盒 harness 仍然需要 TokenTapeBuilder 或 RendererBinding。原因是软件工程智能体不是单次 generate，而是：

```text
system prompt
task prompt
model action
tool observation
model action
tool observation
...
```

每一轮都要证明：

```text
1. 模型当时看到的上下文是什么。
2. 哪些 token 来自模型采样。
3. 哪些 token 来自工具或环境。
4. append 到下一轮上下文时是否发生 template drift、布尔值变化、转义变化或重新分词漂移。
5. 最终 loss_mask 是否只覆盖模型生成的 response token。
```

verl 的 ToolAgentLoop 和 slime 的 SGLang rollout 都证明了这一点：训练框架最终要的是 token ids、response_mask / loss_mask、rollout_log_probs 和 reward，而不是一段事后拼出来的 transcript。

### 5.3 VerlAdapter 和 SlimeAdapter 都应该是训练后端协商层

`VerlAdapter` 不应只做字段改名。它需要和 verl 的运行时状态对齐：

```text
RepoHarness TrainingView / TrajectoryArtifact
-> verl AgentLoopOutput 或 DataProto
-> response_mask / rollout_log_probs / reward_score / extra_fields
-> MessageQueue、FullyAsyncTrainer 或未来 TransferQueue 消费
```

它还要处理：

```text
1. policy version 和 weight version 对齐。
2. staleness 超阈值时拒绝或降权。
3. reward facts 到 verl reward tensor 的映射。
4. group_id 与 rollout.n / GRPO group 的关系。
5. backend_rejection_reason 的回写。
6. logprob 缺失或 retokenized 轨迹的 fail-closed。
```

`SlimeAdapter` 则应面向 slime 的 `Sample` 和 `RolloutBatch`：

```text
TrajectoryArtifact
-> slime.Sample
   tokens
   response_length
   loss_mask
   rollout_log_probs
   teacher_log_probs
   rollout_id
   session_id
   status
   metadata
-> RolloutBatch
-> Megatron actor / critic
```

它要特别注意 slime 的 sibling rollout、partial rollout、dynamic sampling 和 `rollout_mask_sums` 语义，避免 fan-out segment 重复放大奖励或 loss。

### 5.4 Gateway 应该是轻量、可观测、可透传的边界

RepoHarness 的模型调用 gateway 不应该成为第二个 vLLM / SGLang router。更合理的职责是：

```text
1. 接收 RepoHarness 的生成请求。
2. 透传 sampling_params、max_new_tokens、stop、logprob 请求、session_id 和 backend hints。
3. 调用训练后端管理的 client，例如 verl 管理的 vLLM / SGLang client，或 slime 管理的 SGLang router。
4. 保存后端返回的 token ids、logprobs、finish_reason、weight_version 和运行统计。
5. 将失败结构化为 FailureRecord，而不是吞掉异常或只写字符串。
```

这和 Polar / ProRL-Agent-Server 的 model API capture 思路一致，但 RepoHarness 的白盒路径可以更强：因为 RepoHarness 自己控制 agent loop，可以在每轮调用时直接记录 token tape 和环境状态，不必只依赖事后 proxy 捕获。

### 5.5 ContextBudgetPolicy 是 RepoHarness 应该拥有的能力

底层推理服务可以支持很长上下文，但 RepoHarness 仍然需要拥有上下文预算策略。至少要明确：

```text
1. 每个 task profile 的最大 prompt token budget。
2. 工具 observation 的截断规则。
3. 测试日志、grep 输出、文件内容、diff 和 traceback 的优先级。
4. 历史轮次什么时候压缩、摘要、丢弃或保留原始 token。
5. 截断是否影响训练资格或 reward 解释。
```

这是环境层职责，不是推理服务职责。推理服务只负责在给定输入上高效生成；RepoHarness 要负责决定什么信息应该进入模型视野，并记录这个决定。

### 5.6 Prefix-aware scheduling 是控制面提示，不是环境核心逻辑

多个 rollout 如果来自同一个 task，它们通常共享大量 prefix。RepoHarness 可以向训练后端提供：

```text
task_id
group_id
task_prefix_digest
harness_spec_digest
tool_schema_digest
workspace_snapshot_digest
session_id
```

这些信息可以帮助后端做 prefix caching、consistent hashing、group-level batching 或 PrefixGrouper。但 RepoHarness 不应该把具体 GPU scheduling 算法写进环境运行时。正确边界是：

```text
RepoHarness 负责稳定身份、结构化 lineage 和可审计 digest。
verl / slime / vLLM / SGLang 负责具体 batching、routing、cache 和 attention 优化。
```

### 5.7 低精度和后端配置必须进入实验可复现记录

后续如果比较不同训练结果，必须能回答：

```text
这批 rollout 是 BF16 还是 FP8？
KV cache 是否用了 FP8？
teacher model 是 BF16、FP8 还是量化模型？
response_logprobs 是服务端直接返回，还是训练侧重算？
logprobs_mode 是 processed_logprobs 还是其他模式？
同一条轨迹的 rollout policy 和 training policy 是否使用不同精度？
```

这些信息不一定都属于核心 `CompletionRecord` 字段，但必须在 `TrainingRuntimeRecord`、backend config digest 或 artifact manifest 中可追溯。否则训练不稳定时很难定位原因。

## 6. 对现有高层架构文档的关系

当前主设计文档 `docs/harness_improve/repo_harness_repositioning_after_polar.md` 已经覆盖了本文中的很多关键点：

```text
1. 双拓扑：近期 trainer_native，长期 service_driven。
2. CompletionRecord：记录 token ids、logprobs、sampling_params、token provenance 和 logprob alignment。
3. backend_tensors：注册 teacher_log_probs、routed_experts、top_p_mask、多模态输入等后端张量。
4. TrainingRuntimeRecord：记录训练后端、队列类型、policy version、weight version 和 staleness。
5. FailureRecord：结构化失败归因。
6. TokenTapeBuilder / RendererBinding：白盒路径中保证 token tape 和 prefix preservation。
7. reward 归一化、group pass-rate 过滤、partial rollout 和 staleness 默认归属训练后端。
```

本文不建议再新增一个庞大的“Serving Plane”。更稳妥的做法是在已有对象中补充或检查少量字段：

```text
CompletionRecord:
  serving_backend
  serving_backend_version
  inference_engine_name
  prompt_token_count
  response_token_count
  sampling_params
  weight_version_seen_by_engine

TrainingRuntimeRecord:
  training_backend
  queue_or_buffer_kind
  behavior_policy_version
  rollout_started_weight_version
  rollout_completed_weight_version
  staleness_status
  backend_rejection_reason

backend_tensors:
  teacher_log_probs
  routed_experts
  top_p_mask
  multimodal_train_inputs

可选后端运行事实:
  prefix_cache_stats
  speculative_decoding_stats
  precision_policy_digest
  pd_topology_summary
```

也就是说，基础设施影响应当进入“字段、校验、adapter、运行记录”，而不是在 RepoHarness 内部复制 vLLM、SGLang、verl 或 slime 的实现。

## 7. 建议的近期实现顺序

### P0：先保证训练样本可信

```text
1. 确认白盒路径每次 LLM 调用都能保存 prompt_ids、response_ids、response_logprobs、sampling_params 和 weight_version_seen_by_engine。
2. 确认 loss_mask / response_mask 只覆盖模型生成 token，不覆盖工具 observation、环境反馈或 padding。
3. 确认缺失 logprob、retokenized、captured_text_only、weight_version unknown 的轨迹默认不能进入 formal online RL。
4. 确认 TrainingRuntimeRecord 能记录 staleness、queue kind、backend rejection 和 FailureRecord。
5. 确认低精度、KV cache 精度、logprobs_mode 和推理后端版本至少能通过 config digest 或 runtime facts 追踪。
```

### P1：把 verl trainer-native 路径做实

```text
1. RepoHarness 自定义 AgentLoop 使用 verl 管理的 vLLM / SGLang client。
2. Gateway 透传 sampling_params，并请求逐 token logprobs。
3. RepoHarness episode 结束后投影为 verl AgentLoopOutput / DataProto 所需字段。
4. VerlAdapter 记录 MessageQueue / FullyAsyncTrainer 消费状态。
5. 使用 verl 的 staleness、rollout correction 和训练队列机制，不在 RepoHarness 重写。
```

### P2：做 slime adapter 对照

```text
1. custom_generate 调用 RepoHarness episode。
2. 输出 slime.Sample 需要的 tokens、loss_mask、rollout_log_probs、reward、status、session_id。
3. 若启用 OPD，则把 teacher_log_probs 放入 backend_tensors 并投影到 slime.Sample。
4. 保留 slime 的 dynamic sampling、partial rollout、data buffer 和 weight sync 所有权。
5. 用同一批 RepoHarness task 对比 verl 和 slime 后端消费同一类轨迹的差异。
```

### P3：再考虑 prefix、PD、MTP 和量化实验

这些属于吞吐优化，不应阻塞可信训练样本闭环：

```text
1. prefix-aware task grouping 和 session_id consistent hashing。
2. PrefixGrouper 或训练侧 prefix 合并。
3. FP8 KV cache / rollout quantization ablation。
4. speculative decoding metrics 记录。
5. PD disaggregation 或更复杂 KV cache pool，只在观测到 prefill / decode 互相阻塞后再评估。
```

## 8. 明确不建议 RepoHarness 自研的内容

以下内容不应该进入 RepoHarness 核心实现：

```text
1. 自研 attention、Mamba、DSA、Lightning Attention、MoE routing、MTP heads。
2. 自研 vLLM / SGLang 替代品。
3. 自研 PagedAttention、KV cache pool、prefill / decode KV transfer。
4. 自研 FP8 / FP4 / INT4 kernel 或量化训练 recipe。
5. 自研 Megatron / FSDP / NCCL 权重同步。
6. 把所有训练后端强制抽象成同一个 MessageQueue。
7. 在 RepoHarness 核心里做 reward normalization、group pass-rate filtering 或 partial rollout 策略。
8. 用文本 transcript 重新分词后伪造 token-faithful 训练样本。
```

RepoHarness 的核心价值不是“成为一个新的训练框架”，而是让软件工程环境产生可信、可审计、可训练、可导出的智能体轨迹。底层训练和推理基础设施越复杂，RepoHarness 越应该把自己的边界保持清晰。

## 9. 供后续阅读的关键文件清单

RepoHarness 主设计：

```text
docs/harness_improve/repo_harness_repositioning_after_polar.md
docs/harness_improve/external_reference_code_analysis_for_repositioning.md
docs/harness_improve/environment_production_and_quality_pipeline_design.md
docs/agentic_RL/training_design/warm_start_offline_data_filtering_design.md
```

verl：

```text
reference/verl/AGENTS.md
reference/verl/verl/experimental/agent_loop/agent_loop.py
reference/verl/verl/experimental/agent_loop/tool_agent_loop.py
reference/verl/verl/workers/config/rollout.py
reference/verl/verl/workers/config/disaggregation.py
reference/verl/verl/experimental/fully_async_policy/fully_async_rollouter.py
reference/verl/verl/experimental/fully_async_policy/fully_async_trainer.py
reference/verl/verl/trainer/ppo/rollout_corr_helper.py
reference/verl/verl/trainer/ppo/core_algos.py
reference/verl/examples/prefix_grouper/README.md
reference/verl/docs/data/transfer_queue.md
reference/verl/docs/README_vllm0.8.md
```

slime：

```text
reference/slime/AGENTS.md
reference/slime/train_async.py
reference/slime/slime/ray/rollout.py
reference/slime/slime/rollout/sglang_rollout.py
reference/slime/slime/rollout/fully_async_rollout.py
reference/slime/slime/utils/types.py
reference/slime/slime/backends/megatron_utils/actor.py
reference/slime/docs/en/blogs/introducing_slime.md
reference/slime/docs/en/examples/qwen3-4B.md
reference/slime/examples/fully_async/README.md
reference/slime/examples/on_policy_distillation/README.md
reference/slime/examples/delta_weight_sync/README.md
```

本次粘贴讲义对应主题：

```text
架构与长上下文为什么影响 post-training
LLM serving 基础：prefill、decode、KV cache、PD disaggregation
LLM 低精度训练 / 推理 / 量化基础
MTP 与 speculative decoding 基础
```

## 10. 最终判断

这些基础设施材料不会推翻 RepoHarness 当前高层方向。相反，它们加强了当前方向的必要性：

```text
RepoHarness 必须拥有环境、任务、权限、用户模拟、verifier、reward facts、artifact safety 和 token-faithful trajectory。
verl、slime、vLLM、SGLang、Megatron 应拥有训练运行时、推理服务、KV cache、低精度、MTP、权重同步、异步队列和数据并行。
RepoHarness 与训练框架之间的 adapter 必须既做格式投影，也做运行时事实协商和训练资格校验。
```

换句话说，RepoHarness 的正确定位不是“替代 verl / slime / vLLM / SGLang”，而是成为这些训练基础设施之上的软件工程智能体环境和轨迹可信层。
