# 第 2 讲：架构与长上下文为什么会影响 post-training

这一讲的目标不是系统学习模型架构。我们不展开 MoE、Attention、Mamba、DSA、Lightning Attention、MTP、FP4/FP8 的完整数学细节，而是回答一个更工程化的问题：

> 为什么这些看似“pretraining / inference 架构”的设计，会直接决定后训练、agent RL、OPD/MOPD、coding agent 环境训练能不能 scale？

第 0、1 讲我们讲的是能力空间。第 2 讲开始进入系统约束：**同样的 RL 算法、同样的任务环境，如果模型架构和推理系统不支持高吞吐长轨迹 rollout，agentic post-training 就跑不起来。**

---

## 1. 本讲核心结论

先给结论：

**agentic post-training 不是只受训练 FLOPs 限制，而是同时受以下六个成本限制：**

```text
1. 每 token forward/backward 成本
2. 长上下文 prefill 成本
3. 多轮 decode 成本
4. KV cache 显存/内存成本
5. rollout 延迟和环境等待成本
6. teacher serving / logprob collection 成本
```

所以现代报告里反复出现这些关键词：

* MoE active parameters；
* long context；
* sparse attention / hybrid attention；
* MTP / speculative decoding；
* FP4 / FP8；
* prefill-decode disaggregation；
* KV cache pool；
* asynchronous rollout；
* prefix-tree merging；
* teacher offload / hidden-state cache。

它们表面上是架构或推理优化，实际影响的是：**一个模型能不能以可承受成本生成大量 agent trajectories，并把这些 trajectories 用于 RL/OPD/MOPD 更新。**

---

# 2. 为什么 agent RL 比普通 SFT 更吃架构和推理系统？

普通 SFT 的训练样本大致是：

```text
prompt → answer
```

长度相对可控，训练时主要关心 batch size、sequence length、GPU memory。

但 agent RL 的样本是：

```text
task
→ plan
→ tool call
→ observation
→ retry
→ more tool calls
→ more observations
→ artifact
→ reward
```

它有几个特殊问题。

第一，**trajectory 很长**。coding agent 可能要读多个文件、跑多次测试、处理多次 traceback。search/browser agent 可能要访问多个页面。office/slides agent 可能要生成和反复修改 artifact。

第二，**rollout 是在线生成的**。SFT 可以提前准备数据，agent RL 需要当前 policy 去环境里行动，生成新轨迹，然后才能训练。这意味着推理吞吐直接影响训练速度。

第三，**每一步都可能需要 logprob**。GRPO/RLVR 要知道当前策略对生成 token 的概率；OPD/MOPD 还要 teacher logits 或 teacher distribution。于是 inference service 不只是生成文本，还要支持 logprob collection、teacher serving、checkpoint freshness。

第四，**长上下文会反复 prefill**。多轮 agent 轨迹里，大量 prefix 是共享的：system prompt、task、历史 observation、前几轮工具调用。如果每个 sample 都重新算 prefix，会极其浪费。MiniMax-M2 的 prefix-tree merging 就是为了解决多轮 agent trajectories 中共享 prefix 被重复计算的问题。它把共享 prefix 合并成一棵树，只计算一次，再分支到不同 response segment；报告强调这在数学上等价于独立样本训练，但减少了冗余计算。([arXiv][1])

所以第一个重要观点是：

> **agentic RL 的瓶颈常常不是“反向传播一次有多慢”，而是“能否持续、低成本、稳定地产生足够多高质量长轨迹”。**

---

# 3. active parameters：为什么“总参数”和“激活参数”要分开看？

现代开源模型报告里常见两个数字：

```text
total parameters
activated parameters per token
```

比如：

* NVIDIA Nemotron 3 Ultra：550B total，55B active；
* Kimi K2：1T total，32B activated；
* MiniMax-M2：229.9B total，9.8B active；
* Qwen3-Coder-Next：80B total，3B active；
* MiniMax-M1：456B total，45.9B active。([NVIDIA][2])

为什么这对 agent RL 特别重要？

因为 rollout 阶段的主要成本更接近：

```text
每 token 激活计算成本 × 生成 token 数 × rollout 数量
```

而不是单纯看 total parameters。

对于 agent 训练，你不是只生成一条答案，而是要对同一个任务采样多个 rollouts。例如 GRPO 常常需要 group sampling；OPD/MOPD 还需要 student rollout 后再对 teacher 求分布。这样 token 数会爆炸。

所以 MoE 的价值在 agent RL 里特别明显：

```text
大 total params = 容量大
小 active params = 每 token 成本低
```

MiniMax-M2 的标题 “Mini Activations Unleashing Max Real-World Intelligence” 就是这个逻辑。它的 flagship M2 只有 9.8B activated parameters per token，但面向 agentic deployment 设计，配套 agent-driven data pipeline、Forge RL 系统和 self-evolution。([arXiv][1])

Qwen3-Coder-Next 也是一个非常好的例子。它是 80B 总参数，但每 token 只激活 3B 参数，目标是用小 active footprint 支持 coding agents；它的报告摘要明确说通过大规模可验证 coding tasks 和 executable environments 做 agentic training，使模型可以从 environment feedback 中学习。([arXiv][3])

对于你自己的 RepoHarness / SWE RL 环境，这个启发非常直接：

> 如果你的目标是大量 rollout，而不是单次生成最强答案，那么“小 active 参数 + 足够强的 agent 数据训练”可能比“巨大 dense 模型”更适合做实验。

---

# 4. 长上下文：为什么 coding agent 特别需要，但又特别昂贵？

长上下文对 agentic model 很重要，原因是 agent 需要保留很多状态：

```text
repo 结构
issue 描述
已读文件
测试输出
traceback
前几轮修改
工具调用历史
失败尝试
当前计划
最终 patch
```

如果上下文太短，模型会忘记之前看过什么、改过什么、为什么失败。
但上下文越长，prefill、attention、KV cache 成本越高。

这就是为什么几篇报告都在强调长上下文：

* NVIDIA Nemotron 3 Ultra 支持最高 1M context，并且页面强调它在 1M RULER 上表现强，同时使用 Hybrid Mamba-Attention、MTP 和 NVFP4 等设计来支持高吞吐推理。([NVIDIA][2])
* MiniMax-M1 原生支持 1M context，并把 Lightning Attention 与 test-time compute scaling 绑定起来；报告说它适合处理长输入和长时间思考，并在 sandbox-based real-world software engineering environments 上做大规模 RL。([arXiv][4])
* GLM-5 的摘要说它采用 DSA 来显著降低训练和推理成本，同时保持 long-context fidelity，并用异步 RL 基础设施从复杂长程交互中学习。([arXiv][5])
* Qwen3-Coder-Next 的第三方部署文档显示其面向 fast agentic coding/local use 支持 256K context，并强调适合 long-horizon reasoning、complex tool use 和从执行失败中恢复。([Unsloth - Train and Run Models Locally][6])

但要注意一个误区：

> 长上下文不是 agent 能力本身，只是 agent 能力的基础设施。

长上下文可以让模型“看见更多历史”，但模型还必须学会：

* 选择哪些历史重要；
* 丢弃哪些噪声；
* 把 traceback 和代码位置关联起来；
* 不被早期错误假设污染；
* 在长上下文中稳定调用工具；
* 不因为上下文太长而重复、跑偏、过早终止。

所以第 2 讲的重点不是“1M context 越长越好”，而是：

> **agent RL 需要长上下文，但长上下文必须和 trajectory compression、KV cache、prefix reuse、异步 rollout、reward 设计一起看。**

---

# 5. Attention 结构：为什么 DSA、Lightning Attention、Mamba-Attention 会影响 RL 成本？

我们先不讲完整数学，只讲直觉。

标准 Transformer attention 在长序列上成本高，因为每个 token 都要和大量历史 token 建立关系。长上下文越长，attention 计算和 KV cache 压力越明显。

所以不同报告尝试不同方向：

## 5.1 MiniMax-M1：Lightning Attention

MiniMax-M1 使用 hybrid MoE + Lightning Attention，支持 1M context。报告摘要明确说 Lightning Attention 让 test-time compute 可以更高效扩展，使 M1 适合长输入和长思考任务；它还说 M1 的 RL 包括 sandbox-based real-world software engineering environments。([arXiv][4])

对 agent RL 的意义是：

```text
更便宜的长上下文
→ 更长的 reasoning / tool-use trajectory
→ 更多可承受的 RL rollouts
→ 更容易训练长程纠错能力
```

## 5.2 GLM-5：DSA

GLM-5 摘要明确说 DSA 用来降低训练和推理成本，同时保持 long-context fidelity；同时 GLM-5 还用异步 RL 基础设施，把 generation 和 training 解耦，以更高效学习复杂长程交互。([arXiv][5])

这里的关键不是 DSA 具体公式，而是它服务的系统目标：

```text
降低长上下文成本
→ 支撑 agentic engineering
→ 让异步 RL 的 rollout 更可承受
```

## 5.3 NVIDIA：Hybrid Mamba-Attention

NVIDIA Nemotron 3 Ultra 采用 Mixture-of-Experts Hybrid Mamba-Attention 架构，支持 1M context，并强调在 8k input / 64k output 设置下相较其他大模型有更高吞吐。([NVIDIA][2])

Mamba/SSM 类结构的直觉价值是：对长序列建模更高效。Hybrid Mamba-Attention 的目标不是完全替代 attention，而是在长上下文、吞吐、质量之间找折中。

对 agent RL 来说，这类设计的工程意义是：

```text
长上下文不只是能放进去
还要能以足够吞吐生成和训练
```

---

# 6. MTP / speculative decoding：为什么它不是普通推理优化？

MTP 是 Multi-Token Prediction。直觉上，模型不仅预测下一个 token，还训练辅助模块预测后续多个 token。推理时可以用它做 speculative decoding，也就是先草拟多个 token，再由主模型验证，从而提高生成速度。

这对 agent RL 特别重要，因为 agent rollout 大量依赖 decode，而不是只依赖 prefill。

MiniMax-M2 报告说 M2 有 MTP 模块，既提供更丰富训练信号，也支持 speculative decoding；在 RL 阶段，它们还持续用 KL loss 共同训练 MTP 模块，以防 RL policy 变化导致 draft acceptance rate 下降。([arXiv][1])

这句话非常关键。它说明：

> 在 RL 过程中，policy 是不断变化的。如果 speculative decoding 的 draft model 跟不上 policy，推理加速会失效。

所以 MTP 在 agent RL 中不是“推理工程师的附加优化”，而是要和 RL policy 联动维护：

```text
policy update
→ token distribution changes
→ draft model stale
→ acceptance rate drops
→ rollout throughput drops
→ RL training slows
```

NVIDIA Nemotron 3 Ultra 也明确把 MTP layers 用于 native speculative decoding，作为 key features 之一。([NVIDIA][2])

对你未来做小规模系统的启发是：

* 初期可以不实现 MTP；
* 但要意识到 decode throughput 会限制 RL；
* 如果 rollout 很慢，优先优化 inference batching、KV cache、环境并发，而不是先纠结复杂 RL 算法。

---

# 7. KV cache：agent RL 中最容易被低估的资源

KV cache 是 transformer 推理中缓存历史 token key/value 的机制。它的作用是避免每生成一个新 token 都重新计算全部历史。

在普通聊天里，KV cache 已经重要。
在 agent RL 里，它更重要，因为 agent 轨迹有大量长历史和共享 prefix。

例如一个 SWE task 的多个 rollout 可能共享：

```text
system prompt
tool schema
problem statement
repo summary
initial observations
```

如果每个 rollout 都重新 prefill 这些 prefix，会浪费大量计算。

MiniMax-M2 的 prefix-tree merging 正是训练侧的共享 prefix 优化；其 Global L3 KV Cache Pool 则是推理侧的共享 prefix 优化。报告说它使用分布式 global KV cache，结合 group-level rollout scheduling，提高 prefix cache 命中率，避免多轮 agent interactions 中重复 prefill。([arXiv][1])

这对 RepoHarness 类系统非常重要。你可以把它抽象成：

```text
同一 task 的 N 个 rollouts
  共享 system prompt + task + repo context
  分叉在不同 action sequence
```

理想系统应该尽量复用共享部分。小规模实现时不一定做 global KV cache，但至少要意识到：

* batch 内同任务 rollout 可以共享前缀；
* 工具 observation 要避免无意义膨胀；
* repo context 不应每轮完整重复；
* trajectory 存储要支持 replay 和 compression；
* 长上下文不是“随便塞”，而是要有上下文预算策略。

---

# 8. FP4 / FP8 / quantization：为什么低精度会影响 post-training？

低精度在这里有两种场景：

1. **训练/预训练/推理中的低精度计算**；
2. **部署/rollout 中的量化模型**。

NVIDIA Nemotron 3 Ultra 页面显示它使用 NVFP4 预训练，并释放 post-trained 和 NVFP4 quantized checkpoint；它还强调高吞吐和 1M context 支持。([NVIDIA][2])

Qwen3-Coder-Next 的部署文档则从实际使用角度显示量化对本地 agentic coding 的意义：80B/3B active 模型可以在 46GB RAM/VRAM/unified memory 的 4-bit 设置下运行，并且 vLLM/SGLang 中 FP8 dynamic quant 还可以通过 FP8 KV cache 降低 KV cache memory。([Unsloth - Train and Run Models Locally][6])

对后训练系统来说，低精度的意义是：

```text
更低显存
→ 更大 batch / 更长 context / 更多并发 rollout
→ 更低成本收集 trajectories
```

但也有风险：

* logprob 精度可能影响 RL 稳定性；
* teacher logits 精度可能影响 OPD/MOPD；
* 低精度模型可能在 tool-call 格式上更容易出错；
* 量化模型用于 rollout，训练模型用于 update，可能产生 train-inference mismatch。

所以实际工程中要区分：

```text
rollout policy precision
training policy precision
reference policy precision
teacher precision
reward model precision
```

这在 OPD/MOPD 里尤其重要，因为 teacher distribution 是训练信号来源。

---

# 9. prefill-decode disaggregation：为什么 agent 推理要拆 prefill 和 decode？

在 LLM 推理里，prefill 和 decode 的计算特征不同：

* **prefill**：一次处理长 prompt，吞吐/矩阵计算密集；
* **decode**：每次生成一个或少量 token，受 latency、KV cache、batching 影响大。

agent rollout 同时有大量长 prompt prefill 和长时间 decode。如果混在一起调度，会互相干扰，尤其在 MoE 结构下更明显。

MiniMax-M2 报告明确提出 heterogeneous prefill-decode disaggregation，把 prefill 和 decode 解耦成独立调度实例，分别采用适合自身计算特征的并行策略，以提高整体吞吐和降低尾延迟。([arXiv][1])

对 agent RL 来说，这一点非常关键。因为 rollout 阶段不是一次性请求，而是：

```text
prefill task + history
→ decode action
→ wait tool
→ append observation
→ prefill/decode next action
→ ...
```

如果系统不能很好处理 prefill/decode 交替，GPU 会被大量小请求、长请求、工具等待、context 增长搞得很低效。

小规模系统不一定需要完整 PD disaggregation，但应该至少做三件事：

1. rollout 和 training 解耦；
2. environment step 和 model generation 异步；
3. 同类请求尽量 batch。

---

# 10. 架构/推理设计如何影响 OPD/MOPD？

OPD/MOPD 比普通 RL 更吃推理系统。

普通 RLVR 需要：

```text
student rollout
→ reward
→ student logprob
→ update
```

OPD/MOPD 还需要：

```text
student rollout
→ teacher forward / teacher logits
→ KL / distillation loss
→ update student
```

如果是 full-vocabulary distillation，teacher 输出不是一个 token 的概率，而是整个词表分布。这样成本非常高。

所以 OPD/MOPD 的瓶颈包括：

* teacher model 数量；
* teacher active params；
* teacher serving latency；
* full-vocab logits 存储；
* teacher/student context 对齐；
* long trajectory 上每个 token 是否都蒸馏；
* teacher 是否需要隐藏状态缓存；
* rollout 是否足够新鲜。

NVIDIA Nemotron 3 Ultra 把 MOPD 放在 post-training pipeline 中，使用 multiple specialist teachers 提供 dense guidance；这意味着其架构和推理吞吐必须支撑多 teacher 的 serving。([NVIDIA][2])

这也解释了为什么 DeepSeek-V4、NVIDIA 这类 OPD/MOPD 路线通常不能只看算法公式。公式可能是 KL，但真正难点是：

```text
如何让 teacher 在大规模 student rollout 上可承受地跑起来？
```

对于你的小规模实验，最现实的简化方式是：

```text
先只蒸馏 selected tokens / selected turns
再尝试 small teacher
再尝试 cached logits
最后才考虑 full-vocabulary OPD
```

第 11 讲会详细展开 OPD/MOPD，这里先记住：**OPD 是算法，也是 serving 系统。**

---

# 11. 各报告在第 2 讲中的定位

下面这张表是本讲核心对比表。

| 报告簇                          | 架构/推理关键词                                                                                                              | 对 agent RL / OPD 的意义                                                             |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| **NVIDIA Nemotron 3 Ultra**  | 550B total / 55B active、Hybrid Mamba-Attention、LatentMoE、MTP、NVFP4、1M context                                         | 大模型容量 + 高吞吐长上下文 + MOPD，代表“高性能多教师 agent post-training”路线。([NVIDIA][2])            |
| **MiniMax-M1**               | 456B total / 45.9B active、Lightning Attention、1M context、CISPO、40K/80K thinking budget                                | 长上下文 reasoning RL 到 SWE sandbox RL 的桥梁，强调 test-time compute 和 RL 成本。([arXiv][4]) |
| **GLM-5**                    | DSA、异步 RL、generation/training 解耦、long-context fidelity                                                                | 说明长上下文成本优化必须和异步 agent RL 一起设计。([arXiv][5])                                       |
| **MiniMax-M2**               | 229.9B total / 9.8B active、192K context、MTP、Forge、windowed FIFO、prefix-tree merging、PD disaggregation、global KV cache | 最清楚展示“agent RL 系统吞吐优化”的报告之一。([arXiv][1])                                         |
| **Qwen3-Coder-Next**         | 80B total / 3B active、256K context、local fast agentic coding、FP8/KV cache 部署                                          | 代表“小 active 参数 + coding agent 专项训练”的高性价比路线。([arXiv][3])                          |
| **Kimi K2**                  | 1T total / 32B active、MuonClip、15.5T tokens、agentic data synthesis                                                    | 强调大容量 MoE + 稳定预训练 + agentic post-training。([arXiv][7])                           |
| **Kimi K2.5**                | multimodal agentic model、joint text-vision RL、Agent Swarm、4.5× latency reduction                                      | 把架构/推理问题扩展到 visual agent 和 parallel agent orchestration。([arXiv][8])             |
| **Microsoft MAI-Thinking-1** | 不是本讲架构主案例，更偏 training/eval/hill-climbing machine                                                                      | 它提醒我们：架构不是单独优化目标，最终要服务 data、RL、eval、安全的完整爬坡系统。([Microsoft AI][9])                |

---

# 12. 用一个简化公式理解 agent RL 成本

不做严格数学，只给一个工程近似。

一次 agent RL 的成本可以粗略理解为：

```text
总成本 ≈ rollout 成本 + 环境成本 + 训练更新成本 + reward/verifier 成本 + teacher 成本
```

展开一点：

```text
rollout 成本
≈ tasks × samples_per_task × trajectory_tokens × active_model_cost

训练成本
≈ selected_trajectory_tokens × backward_cost

OPD/MOPD teacher 成本
≈ distilled_tokens × num_teachers × teacher_active_cost
```

这解释了为什么以下设计会反复出现：

* MoE：降低 active_model_cost；
* long-context attention 优化：降低 trajectory_tokens 的边际成本；
* MTP/speculative decoding：降低 rollout decode latency；
* KV cache：降低重复 prefill；
* prefix-tree merging：降低共享 prefix 的训练冗余；
* async RL：降低环境长尾导致的 GPU idle；
* FP4/FP8：降低显存和推理成本；
* teacher cache/offload：降低 OPD/MOPD teacher 成本。

所以第 2 讲的核心工程逻辑是：

> **agent RL 的每一点算法改进，都可能被 rollout 成本吃掉；每一点推理/架构优化，都可能放大可训练轨迹数量。**

---

# 13. 对 RepoHarness / 小规模系统的直接启发

如果你要做 RepoHarness 类 SWE agent RL 环境，不需要一开始复现 NVIDIA / MiniMax / GLM 的完整系统，但要从第 2 讲吸收这些原则。

## 13.1 优先选小 active 模型做 rollout

Qwen3-Coder-Next 这种 3B active 的 coding agent 模型非常适合作为“高吞吐 rollout policy”的参考方向。它证明了小 active footprint 也可以通过 coding-agent 专项训练获得强 agentic coding 性能。([arXiv][3])

## 13.2 上下文预算比盲目长上下文更重要

你可以支持很长上下文，但训练时仍应控制：

```text
system prompt
task
repo summary
relevant files
tool history
test output
diff
```

不要把所有 observation 无脑塞回上下文。否则模型会被无关日志污染，KV cache 和训练成本也会爆炸。

## 13.3 trajectory 存储要为 prefix reuse / replay 预留结构

即使初版不做 prefix-tree merging，也应该把 trajectory 结构化保存：

```text
task prefix
turns
tool calls
observations
artifacts
reward
```

这样未来才能做：

* replay；
* filtering；
* OPD；
* logprob recomputation；
* shared prefix batching；
* reward hacking audit。

## 13.4 rollout 和训练要尽早解耦

不要让训练 loop 同步等待每个环境完成。GLM-5 和 MiniMax-M2 都说明了长尾 rollout 会造成严重调度问题。小规模系统也应该至少做：

```text
rollout workers
→ trajectory queue
→ reward workers
→ trainer
```

而不是：

```text
generate one batch
→ wait all envs
→ train
```

## 13.5 OPD 先做简化版

不要一开始 full-vocabulary 多 teacher OPD。可以先做：

```text
selected-turn distillation
sampled-token distillation
single teacher
small teacher
offline teacher logits cache
```

然后再逐步接近 full-vocab / multi-teacher / on-policy。

---

# 14. 本讲总结

第 2 讲需要记住七句话：

1. **agent RL 的瓶颈不只是训练 FLOPs，而是 rollout、长上下文、KV cache、环境等待、teacher serving 的综合成本。**
2. **MoE 的 total params 决定容量，active params 决定每 token rollout 成本。**
3. **长上下文是 agent 能力基础设施，但不是能力本身；还需要状态管理、上下文压缩和 trajectory 设计。**
4. **DSA、Lightning Attention、Hybrid Mamba-Attention 这类设计的核心意义，是让长轨迹推理和训练可承受。**
5. **MTP/speculative decoding 对 agent RL 很关键，因为 rollout 大量消耗 decode。**
6. **KV cache、prefix-tree merging、prefill-decode disaggregation 是 agent RL 从“能跑”到“能 scale”的关键系统设计。**
7. **OPD/MOPD 不只是 KL 公式问题，更是 teacher serving、logit 存储、长轨迹对齐和推理吞吐问题。**

---

# 本讲笔记快照 v2

```text
已讲主题：
- 第 0 讲：agentic post-training 总系统图
- 第 1 讲：agentic capability 定义与能力分层
- 第 2 讲：架构与长上下文为什么会影响 post-training

本讲新增关键概念：
- total parameters vs activated parameters
- long-context fidelity
- rollout cost
- prefill cost
- decode cost
- KV cache
- MTP / speculative decoding
- prefix-tree merging
- prefill-decode disaggregation
- FP4 / FP8
- teacher serving cost

本讲核心判断：
- agent RL 的主要瓶颈经常在 rollout/inference/environment，而不只在 trainer。
- 小 active 参数模型更适合作为高吞吐 rollout policy。
- 长上下文必须配合上下文预算、KV cache、prefix reuse 和异步 rollout。
- OPD/MOPD 是算法问题，也是 serving 系统问题。

报告定位更新：
- NVIDIA：高吞吐长上下文 + MOPD 主案例
- MiniMax-M1：Lightning Attention + long-context RL 成本主案例
- GLM-5：DSA + async RL 主案例
- MiniMax-M2：Forge + prefix-tree/KV/PD disaggregation 主案例
- Qwen3-Coder-Next：小 active coding-agent rollout 主案例
- Kimi K2/K2.5：agentic MoE 与 Agent Swarm 扩展案例
- Microsoft：系统爬坡框架，非本讲架构主案例

下一讲：
- 第 3 讲：数据与任务合成 I——coding / SWE / repo repair
```

下一讲会进入和你的 RepoHarness 最直接相关的部分：**coding/SWE/repo repair 任务到底如何从 GitHub issue、PR、commit、test、environment 中构造出来，并变成可用于 SFT/RL/OPD 的训练样本。**

[1]: https://arxiv.org/html/2605.26494v1 "The MiniMax-M2 Series: Mini Activations Unleashing Max Real-World Intelligence"
[2]: https://research.nvidia.com/labs/nemotron/Nemotron-3-Ultra/ "NVIDIA Nemotron 3 Ultra - NVIDIA Nemotron"
[3]: https://arxiv.org/abs/2603.00729 "[2603.00729] Qwen3-Coder-Next Technical Report"
[4]: https://arxiv.org/abs/2506.13585 "[2506.13585] MiniMax-M1: Scaling Test-Time Compute Efficiently with Lightning Attention"
[5]: https://arxiv.org/abs/2602.15763 "[2602.15763] GLM-5: from Vibe Coding to Agentic Engineering"
[6]: https://unsloth.ai/docs/models/qwen3-coder-next "Qwen3-Coder-Next: How to Run Locally | Unsloth Documentation"
[7]: https://arxiv.org/abs/2507.20534 "[2507.20534] Kimi K2: Open Agentic Intelligence"
[8]: https://arxiv.org/abs/2602.02276 "[2602.02276] Kimi K2.5: Visual Agentic Intelligence"
[9]: https://microsoft.ai/news/introducing-mai-thinking-1/?utm_source=chatgpt.com "Introducing MAI-Thinking-1 | Microsoft AI"
