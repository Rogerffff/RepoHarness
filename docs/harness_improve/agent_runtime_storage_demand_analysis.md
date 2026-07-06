# Agent 运行数据与存储需求研究报告

生成日期：2026-06-24

本报告只研究“agent 任务运行会产生哪些数据、这些数据如何被保存或者缓存、最终会映射到哪些硬件层级”。本报告不提供股票买卖建议，不判断任何公司的投资价值，也不做外部市场占有率分析。

研究范围限定在本仓库已有材料，主要包括：

- `reference/claude-code-docs/`
- `reference/claude-code-typescript-src/`
- `reference/codex/`
- `reference/verl/`
- `reference/slime/`
- `reference/ProRL-Agent-Server/`
- `reference/renderers/`
- `reference/lmcache/`
- `src/repo_harness/` 和 `docs/agentic_RL/` 中与轨迹、训练投影、上下文和 artifact 有关的实现或说明

## 结论摘要

Agent 运行对存储的需求不能只用“上下文变长”概括。更准确的拆法是三层：

1. **推理热状态层**：长上下文进入模型推理后，最主要压力落在 GPU 高带宽显存，也就是 HBM，尤其是键值缓存、prefix cache 的真实缓存块、活跃模型权重、临时 logits、attention 工作区和训练中的 tensor batch。这一层速度要求最高。普通 vLLM、SGLang 或 Transformers 后端里，KV cache 通常不是可审计长期数据；但是 LMCache 这类项目会把 KV cache 外挂成可复用、可观测、可迁移的分层缓存对象，所以 KV cache 也可能向 CPU 内存、本地 NVMe、远端缓存和对象存储扩展。
2. **运行轨迹和审计层**：会话消息、工具调用、工具结果、压缩摘要、工作区差异、artifact manifest、transcript 和 completion JSON 等主要落在 CPU 内存和本地 NVMe 上，并可以进一步归档到网络文件系统、对象存储或者冷存储。这一层强调可复盘、可恢复、可导出。
3. **训练数据和 checkpoint 层**：只有带真实 `response_ids`、逐 token `loss_mask`、逐 token `rollout_log_probs`、reward、参数版本或者权重版本的轨迹，才直接构成训练存储需求。模型和优化器 checkpoint 通常比单条轨迹大得多，是训练系统中最容易支配持久容量和写入带宽的部分。

因此，agent 任务规模化以后，对硬件的影响会分裂成几类不同需求：

- **HBM 容量和带宽**：由上下文长度、并发序列数、模型层数、KV head 数、head 维度、精度共同驱动。长上下文 agent 最容易把压力推向这一层。
- **KV cache 分层缓存层**：当采用 LMCache 这类外部缓存层时，KV cache 会从纯显存驻留扩展到 L1 CPU pinned memory 或 GDS NVMe slab，以及 L2 文件系统、S3、Redis/Valkey、Mooncake、InfiniStore、NIXL 等后端。这会把部分 prefill 重算压力转成跨层缓存命中率、跨设备搬运带宽和远端存储 I/O 问题。
- **本地 NVMe**：承接工具大输出、会话 JSONL、trajectory、artifact、workspace snapshot、临时 checkpoint 和调试样本。它需要低延迟、高随机读写和较好的顺序写入能力。
- **网络文件系统或者对象存储**：承接大规模训练样本、长期轨迹语料、模型 checkpoint 保留和跨机器训练恢复。它的重点是吞吐、可用性、生命周期管理和成本。
- **CPU 内存**：承接消息队列、运行时 `DataProto`、`Sample`、`SessionStore`、上下文准备和训练数据拼装。它不一定是最终持久层，但会影响 rollout 和 trainer 之间的吞吐。

## 数据分类

| 数据类型 | 典型内容 | 直接证据 | 存储含义 |
|---|---|---|---|
| 长上下文 | 原始 messages、工具结果、系统提示、历史 assistant 输出、下一轮 prompt token | Claude Code 查询前会经过 compact、tool result budget、microcompact 等预处理；见 `reference/claude-code-docs/claude-doc/03-query-engine.md` 和 `reference/claude-code-docs/claude-doc/10-context-memory-session.md` | CPU 内存中拼装，本地盘保存 transcript，进入推理时变成 token tensor 和 KV cache 压力 |
| 压缩摘要 | AutoCompact summary、Session Memory、compact boundary、post-compact attachments | Claude Code AutoCompact 会在上下文接近阈值时生成摘要；`reference/claude-code-docs/claude-doc/10-context-memory-session.md:19` | 摘要降低后续 prompt 和 KV cache 压力，但会产生新的摘要 artifact、compact record 和恢复边界 |
| 工具结果 | stdout、stderr、grep 结果、文件读取结果、web fetch 结果、tool_result block | Claude Code 单个工具结果和聚合工具结果都有落盘预算；`reference/claude-code-docs/claude-doc/13-applyToolResultBudget-detail.md:12` | 大输出不应该长期留在模型上下文里；完整内容落本地盘，模型看到 preview，需要时再读取 |
| 会话轨迹 | JSONL transcript、rollout JSONL、events、completion records | Codex `RolloutRecorder` 将 canonical session rollout 写成 JSONL；`reference/codex/codex-rs/rollout/src/recorder.rs:64` | 本地 NVMe 是主要落点，SQLite 或索引表用于快速检索 |
| 工作区差异 | `final.patch`、`final.diff`、workspace snapshot、source hash | RepoHarness 的 artifact writer 记录 `sha256`、大小和 manifest；`src/repo_harness/trajectory/recorder.py:228` | 主要是本地盘和归档存储需求，通常只有作为上下文重新提供给模型时才进入 HBM |
| token tape | `prompt_ids`、`response_ids`、`response_mask`、`response_logprobs`、span | RepoHarness `TrainingView` 明确定义这些字段；`src/repo_harness/rl/training_view.py:77` | 对训练最关键，必须保持逐 token 对齐；短期在 CPU 内存和 GPU tensor 中，长期可进训练样本存储 |
| 逐 token logprob | rollout engine 返回的每个 response token 的 log probability | ProRL 到 Slime 的 adapter 要求 trainable token 缺少 logprob 时直接报错；`reference/ProRL-Agent-Server/src/slime_bridge/adapter.py:264` | 直接影响 policy loss，可训练轨迹必须保存或可恢复 |
| loss mask | 哪些 response token 进入训练损失 | Slime `Sample` 有 `loss_mask`，训练转换时校验长度等于 response length；`reference/slime/slime/ray/rollout.py:714` | 体积不大，但语义价值很高。没有 mask 的文本轨迹不能可靠进入训练 |
| reward | 标量 reward、多维 reward、raw reward、token-level reward | Slime `Sample.reward` 可为浮点或字典；`reference/slime/slime/utils/types.py:31` | 对容量压力小，但对样本有效性和筛选非常关键 |
| 键值缓存 | vLLM、SGLang、Transformers 推理时的 KV block；LMCache 管理的 L1/L2 KV cache object | verl vLLM adapter 明确 `resume` 和 `release` 管理 weights 或 `kv_cache`；`reference/verl/verl/workers/rollout/vllm_rollout/vllm_rollout.py:150`。LMCache 明确把 KV cache 存到 GPU、CPU、disk、S3 等层级；`reference/lmcache/AGENTS.md:7` | 普通后端主要是 GPU HBM 热状态；引入 LMCache 后，KV cache 会变成可外部化、可驱逐、可跨后端复用的缓存对象 |
| prefix cache | prefix cache 真实块、chunk 命中统计、L0/L1/L2 token hit rate | verl 默认启用 `enable_prefix_caching`；`reference/verl/verl/workers/config/rollout.py:253`。Slime 的 `PrefixCacheInfo` 只是统计字段；`reference/slime/slime/utils/types.py:101`。LMCache 明确把 vLLM GPU prefix cache 视为 L0，并统计 L1+L2 命中；`reference/lmcache/docs/source/mp/observability/metrics.rst:237` | 真实缓存块不一定长期归档；但在 LMCache 模式下，命中 token、chunk 生命周期、L0/L1/L2 搬运吞吐都成为重要存储指标 |
| checkpoint | 模型参数、优化器状态、scheduler、extra state、HF checkpoint | verl fully async trainer 保存到 `default_local_dir/global_step_<version>/actor`，可选远端目录；`reference/verl/verl/experimental/fully_async_policy/fully_async_trainer.py:700` | 持久容量和写入带宽的大头之一，本地 NVMe、共享文件系统、对象存储都可能参与 |
| 数据集样本 | prompt、label、metadata、tokenized batch、rollout sample | verl `DataProto` 是 `TensorDict + non_tensor_batch + meta_info`；`reference/verl/verl/protocol.py:318` | 大规模离线数据适合对象存储或数据湖，训练热 batch 在 CPU 内存和 HBM 中流动 |

## 关键证据

### Claude Code：上下文压缩、工具结果落盘和会话持久化

Claude Code 的上下文治理是多层策略，不是单一截断。

- AutoCompact 会在上下文 token 数接近阈值时 fork 子 agent 生成结构化摘要，然后用摘要替换原始消息。文档还说明预留摘要输出 token 和 13,000 token 缓冲区；见 `reference/claude-code-docs/claude-doc/10-context-memory-session.md:19`。
- Session Memory 维护一个 markdown 文件作为当前会话笔记，达到 10,000 token 后初始化，后续按 token 增长和工具调用数量更新；见 `reference/claude-code-docs/claude-doc/10-context-memory-session.md:223`。
- 会话消息以 JSONL 存在 `~/.claude/projects/<path>/<sessionId>.jsonl`，子 agent 轨迹在 `<sessionId>/subagents/agent-<agentId>.jsonl`；见 `reference/claude-code-docs/claude-doc/10-context-memory-session.md:250`。
- 工具结果有两层预算：单个工具结果超过阈值会写入 `<sessionDir>/tool-results/<id>.txt`，模型只看到 `<persisted-output>` 预览；聚合预算限制同一 wire-level user message 的工具结果总量；见 `reference/claude-code-docs/claude-doc/13-applyToolResultBudget-detail.md:12` 和 `reference/claude-code-docs/claude-doc/13-applyToolResultBudget-detail.md:58`。
- `ContentReplacementState` 会记录 `seenIds` 和 `replacements`，跨 `query()` 调用复用同一替换字符串，以保护 prompt cache 稳定性；见 `reference/claude-code-docs/claude-doc/13-applyToolResultBudget-detail.md:225`。

存储含义：

- 长上下文不只是让模型请求变长，也会让本地 transcript、工具结果目录和摘要记录增长。
- 大工具输出更像本地 NVMe artifact，而不是长期留在模型上下文中的文本。
- 压缩摘要和工具预览减少了 HBM 中 KV cache 的增长，但增加了可审计文件和恢复状态。

### Codex：rollout JSONL、状态索引和压缩事件

Codex 的参考实现更强调“可重放 rollout 日志 + 索引数据库”。

- `RolloutRecorder` 明确把 canonical session rollout items 写为 JSONL，可用 `jq` 或 `fx` 检查；见 `reference/codex/codex-rs/rollout/src/recorder.rs:64`。
- Codex compact 代码定义 summarization prompt、summary prefix、20,000 token 的 compact user message 上限，并区分压缩后是否重新注入 initial context；见 `reference/codex/codex-rs/core/src/compact.rs:46`。
- SQLite `threads` 表记录 `rollout_path`、创建和更新时间、provider、cwd、tokens_used、归档状态和 git 信息；见 `reference/codex/codex-rs/state/migrations/0001_threads.sql:1`。

存储含义：

- Codex 的会话主体是 JSONL，SQLite 更像轻量索引和列表查询层。
- 这种设计的持久压力主要是本地会话文件、索引数据库、归档线程和可能的 compact 后历史。
- `tokens_used` 等字段适合做每个 agent 任务的存储和上下文增长统计。

### verl：DataProto、rollout 队列、KV cache 和 checkpoint

verl 的核心视角是训练数据流和 rollout worker。

- `DataProto` 是函数和模块之间的标准交换协议，包含 `batch: TensorDict`、`non_tensor_batch` 和 `meta_info`；见 `reference/verl/verl/protocol.py:318`。
- `DataProto` 可以通过 `torch.save` 序列化 tensor，也可以 `pickle.dump` 到磁盘；见 `reference/verl/verl/protocol.py:377` 和 `reference/verl/verl/protocol.py:426`。
- rollout config 中有 `prompt_length`、`response_length`、`gpu_memory_utilization`、`max_num_batched_tokens`、`free_cache_engine` 等直接影响显存和吞吐的字段；见 `reference/verl/verl/workers/config/rollout.py:187`。
- verl 默认启用 chunked prefill 和 prefix caching；见 `reference/verl/verl/workers/config/rollout.py:253`。
- fully async 的 `MessageQueue` 是 Ray actor 内的 `deque`，最大队列大小默认为 1,000；见 `reference/verl/verl/experimental/fully_async_policy/message_queue.py:26`。
- rollouter 把 `rollout_sample` 用 `ray.cloudpickle.dumps` 放入队列；见 `reference/verl/verl/experimental/fully_async_policy/fully_async_rollouter.py:620`。
- fully async trainer checkpoint 路径是 `default_local_dir/global_step_<current_param_version>/actor`，也可以拼出远端路径，并写 `latest_checkpointed_iteration.txt`；见 `reference/verl/verl/experimental/fully_async_policy/fully_async_trainer.py:700`。
- vLLM adapter 的 `resume` 和 `release` 直接描述为恢复或者释放 GPU memory 中的 weights 或 `kv_cache`；见 `reference/verl/verl/workers/rollout/vllm_rollout/vllm_rollout.py:150`。

存储含义：

- 训练热路径中，`DataProto`、rollout sample、Ray queue 主要是 CPU 内存或 Ray 对象存储压力。
- 进入模型训练或推理后，tensor batch、KV cache、活跃权重和 attention 工作集转化为 HBM 压力。
- checkpoint 是持久化大头，尤其当保存 optimizer、extra state 或多个版本时，本地 NVMe 和远端存储都会被放大。

### Slime：Sample、loss mask、prefix cache 统计和 partial rollout

Slime 的核心训练样本是 `Sample`。

- `Sample` 保存 `tokens`、`response_length`、`reward`、`loss_mask`、`weight_versions`、`rollout_log_probs`、`metadata`、`train_metadata` 和 `session_id`；见 `reference/slime/slime/utils/types.py:8`。
- `PrefixCacheInfo` 只记录 `cached_tokens` 和 `total_prompt_tokens`，它是统计字段，不是真实 KV block；见 `reference/slime/slime/utils/types.py:101`。
- Slime 训练数据转换会生成 `tokens`、`response_lengths`、`rewards`、`raw_reward`、`truncated`、`sample_indices`、`rollout_ids`，并校验 `loss_mask` 长度等于 `response_length`；见 `reference/slime/slime/ray/rollout.py:702`。
- SGLang engine 的权重更新函数说明真实权重从 GPU 直接复制，HTTP server 只发送 metadata；见 `reference/slime/slime/backends/sglang_utils/sglang_engine.py:264`。

存储含义：

- `Sample` 作为训练样本，文本只是其中一部分；token、mask、logprob、reward 和版本信息才是训练存储的核心。
- prefix cache 的统计字段可以落日志或训练样本；真实缓存块在普通推理后端里仍属于显存管理，但在 LMCache 这类外部缓存层里会进入更完整的分层缓存系统。
- partial rollout 会把中断样本留在数据 buffer 或 debug 文件中，这会增加 CPU 内存和本地盘压力，但不是长期训练语料的全部。

### LMCache：KV cache 从临时热状态变成分层缓存对象

LMCache 是本次研究中最贴近“KV cache 如何落到硬件层级”的参考项目。

- LMCache 项目说明直接定义它是 LLM inference 的 KV cache management layer，会把 KV cache 从 temporary state 变成可持久存储、可跨 serving engine 复用、可观测、可转换的对象；见 `reference/lmcache/README.md:47`。
- README 进一步说明它支持 engine-independent deployment，LMCache 作为 standalone daemon 管理 KV cache，推理引擎崩溃时 KV cache 不必和引擎命运绑定；见 `reference/lmcache/README.md:61`。
- README 明确描述 persistent, tiered KV cache offloading and reuse：把 KV cache 从 GPU memory 移到 CPU memory、local storage 和 remote backends 组成的层级里；见 `reference/lmcache/README.md:63`。
- README 列出的后端包括 CPU RAM、local disk SSD、Redis/Valkey、Mooncake、InfiniStore、S3-compatible object storage、NIXL 和 GDS；见 `reference/lmcache/README.md:67`。
- LMCache multiprocess 配置文档把 `--l1-size-gb` 定义为 L1 tier 大小，默认是 pinned DRAM；如果设置 `--gds-l1-path`，L1 medium 会切换为通过 GPUDirect Storage 访问的 NVMe slab file；见 `reference/lmcache/docs/source/mp/configuration.rst:191` 和 `reference/lmcache/docs/source/mp/configuration.rst:225`。
- L2 adapter 配置支持重复传入 `--l2-adapter <JSON>`，注册类型包括 `nixl_store`、`fs`、`fs_native`、`mooncake_store`、`aerospike`、`s3`、`resp`、`raw_block`、`dax` 等；见 `reference/lmcache/docs/source/mp/configuration.rst:346` 和 `reference/lmcache/docs/source/mp/configuration.rst:350`。
- `StorageManager` 代码初始化 `L1Manager`、L2 adapter、L1 eviction controller、L2 eviction controller、store controller 和 prefetch controller；见 `reference/lmcache/lmcache/v1/distributed/storage_manager.py:63`、`reference/lmcache/lmcache/v1/distributed/storage_manager.py:88`、`reference/lmcache/lmcache/v1/distributed/storage_manager.py:135` 和 `reference/lmcache/lmcache/v1/distributed/storage_manager.py:144`。
- L2 adapter 抽象要求实现非阻塞的 store、lookup_and_lock、load，并维护总容量和按 `cache_salt` 统计的字节数；见 `reference/lmcache/lmcache/v1/distributed/l2_adapters/base.py:78`、`reference/lmcache/lmcache/v1/distributed/l2_adapters/base.py:82`、`reference/lmcache/lmcache/v1/distributed/l2_adapters/base.py:119` 和 `reference/lmcache/lmcache/v1/distributed/l2_adapters/base.py:357`。
- 文件系统 L2 adapter 把每个 `ObjectKey` 映射成单独 `.data` 文件，文件中保存 raw tensor bytes；见 `reference/lmcache/lmcache/v1/distributed/l2_adapters/fs_l2_adapter.py:1` 和 `reference/lmcache/lmcache/v1/distributed/l2_adapters/fs_l2_adapter.py:242`。
- S3 L2 adapter 使用 AWS CRT Python binding 实现 L2 adapter 接口；RESP adapter 对应 Redis/Valkey；见 `reference/lmcache/lmcache/v1/distributed/l2_adapters/s3_l2_adapter.py:1` 和 `reference/lmcache/lmcache/v1/distributed/l2_adapters/resp_l2_adapter.py:37`。
- 观测指标文档明确说明 LMCache 的 L1+L2 token-level hit rate 不包含 L0，因为 L0 是 vLLM 拥有的 GPU prefix cache；见 `reference/lmcache/docs/source/mp/observability/metrics.rst:237`。
- 同一份指标文档还定义了 L0 GPU block lifecycle histogram、L0 到 L1 的 GPU 和 CPU copy throughput，以及 L1 到 L2 的端到端吞吐；见 `reference/lmcache/docs/source/mp/observability/metrics.rst:282`、`reference/lmcache/docs/source/mp/observability/metrics.rst:313` 和 `reference/lmcache/docs/source/mp/observability/metrics.rst:344`。
- Kubernetes operator 设计文档说明 multiprocess mode 是一个独立 server process，vLLM 通过 `kv-transfer-config` 连接；它还要求 `hostIPC: true` 以支持 CUDA IPC；见 `reference/lmcache/operator/DESIGN.md:5`、`reference/lmcache/operator/DESIGN.md:156` 和 `reference/lmcache/operator/DESIGN.md:286`。

存储含义：

- 在没有 LMCache 这类系统时，KV cache 主要是推理后端内部的 HBM 热状态；引入 LMCache 后，KV cache 会被拆成 L0 GPU prefix cache、L1 CPU pinned memory 或 GDS NVMe slab、L2 本地或远端后端。
- 这不会让 KV cache 自动变成训练样本。KV cache 仍然是为降低 prefill 重算、改善 TTFT 和吞吐服务的缓存对象，不等价于 `response_ids`、`loss_mask`、`rollout_log_probs` 这类 policy loss 证据。
- 对硬件的含义是：长上下文 agent 不只推高 HBM，也可能推高 CPU 内存、NVMe、Redis/Valkey、S3-compatible object storage、RDMA/NIXL 网络和 GPUDirect Storage 路径的价值。

### ProRL-Agent-Server 和 renderers：token provenance 与可训练轨迹

ProRL-Agent-Server 和 renderers 体现了 agentic RL 中最重要的 token 级要求：不能只保存文本后再重新分词。

- ProRL 到 Slime 的 adapter 从 `Trace` 取 `prompt_ids` 和 `response_ids`，构造 `Sample(tokens=prompt_ids + response_ids)`，同时传入 `response_length`、reward、`loss_mask` 和 `rollout_log_probs`；见 `reference/ProRL-Agent-Server/src/slime_bridge/adapter.py:96`。
- 如果 trainable token 缺少 rollout logprob，adapter 会抛出 `RolloutLogprobError`；如果 `loss_mask` 长度和 `response_len` 不一致，也会报错；见 `reference/ProRL-Agent-Server/src/slime_bridge/adapter.py:264`。
- `SessionStore` 是 active gateway session 的线程安全内存存储；completion writer 只是后台 best-effort JSON 落盘，队列满时会丢弃持久化副本，内存副本仍然是权威；见 `reference/ProRL-Agent-Server/src/polar/gateway/storage.py:28` 和 `reference/ProRL-Agent-Server/src/polar/gateway/completion_writer.py:1`。
- renderers 的 `RenderedTokens` 明确保存 `token_ids`、`message_indices`、`sampled_mask`、`is_content`、`message_roles` 和多模态 sidecar；见 `reference/renderers/renderers/base.py:305`。
- `build_training_sample()` 默认用 `sampled_mask` 构造 loss mask，也支持只监督工具正文而不监督工具包装 token；见 `reference/renderers/renderers/base.py:1500`。
- `bridge_to_next_turn()` 的契约是保留上一轮 `previous_prompt_ids + previous_completion_ids` 的 token 前缀，不重新渲染模型已经采样的 token；见 `reference/renderers/renderers/base.py:714`。

存储含义：

- 可训练轨迹必须保存真实采样 token 和对齐的 mask、logprob、reward。只有自然语言 transcript 不够。
- token provenance 是训练样本的“可审计证据”，它的体积不一定最大，但决定样本是否能进入 policy loss。
- completion JSON 可以作为审计补充，但若缺少 token id 和 logprob，就不能直接等价为训练样本。

### RepoHarness 自身：TrainingView、artifact 和 AutoCompact

RepoHarness 已经有一部分与本研究直接相关的主链路设计。

- `TrainingView` 定义 `prompt_ids`、`response_ids`、`response_mask`、`response_logprobs`、`response_spans` 和 `reward_score`，并校验 `response_logprobs` 必须和 `response_ids` 对齐；见 `src/repo_harness/rl/training_view.py:77`。
- `response_mask=0` 的 token 必须使用 `response_logprobs=0.0`，这说明工具 observation、padding 或其他非训练 token 不应该伪造真实 logprob；见 `src/repo_harness/rl/training_view.py:100`。
- `RunRecorder.write_artifact()` 会记录 artifact 类型、大小、截断策略和 artifact id；见 `src/repo_harness/trajectory/recorder.py:228`。
- AutoCompact 记录 `tokens_before`、`tokens_after`、`summary_artifact_ref`、`rebuilt_messages_ref` 和 compact 状态；见 `src/repo_harness/context/auto_compact.py:432`。

存储含义：

- RepoHarness 的直接存储对象更偏“可审计、可导出、可训练投影”的文件和 JSON 数据。
- HBM、真实 KV cache 和推理后端 prefix cache 的压力主要来自 verl、vLLM、SGLang 和 LMCache 参考链路，不是 RepoHarness 当前持久化文件本身。

## 数据类型到硬件层级映射

| 数据类型 | 单次调用内 | 单个任务内 | 跨会话或训练长期保存 | 主要硬件层级 |
|---|---|---|---|---|
| 原始长上下文 | CPU 内存中组装，进入推理后生成 token tensor 和 KV cache | transcript 和 prepared messages 继续增长 | 可以归档为 JSONL 或训练轨迹 | CPU 内存、本地 NVMe、HBM |
| 压缩摘要 | CPU 内存中生成和替换，下一轮 prompt 会进入模型 | compact record、summary artifact 保存 | 可作为恢复和审计材料 | CPU 内存、本地 NVMe，进入推理时短暂占用 HBM |
| 工具大输出 | 工具进程 stdout/stderr 先在内存中形成 | 超预算后完整输出落盘，模型看到 preview | 可归档为 artifact 或清理 | 本地 NVMe、CPU 内存 |
| 会话 JSONL 和 rollout JSONL | 追加写入 | 支持 resume、列表、审计 | 可转存对象存储或冷存储 | 本地 NVMe、对象存储 |
| 工作区 diff 和 patch | CPU 内存中计算 | `final.patch`、`final.diff` 和 manifest 保存 | 长期归档用于复盘或训练数据集 | 本地 NVMe、对象存储 |
| token tape | CPU 内存对象、Ray 对象、DataProto、Sample | 训练前拼装成 batch | 作为训练样本或 projection 保存 | CPU 内存、HBM、本地 NVMe、对象存储 |
| loss mask 和 logprob | 与 token tape 同步传递 | 进入 loss 计算或过滤逻辑 | 训练样本必须保留 | CPU 内存、HBM、本地 NVMe |
| reward | 内存中计算或由 evaluator 写入 | 和 trace、sample 绑定 | 可进入训练数据和评估报告 | CPU 内存、本地 NVMe、对象存储 |
| KV cache | prefill 和 decode 热状态；LMCache 模式下可被 store、lookup、prefetch、load | 普通后端里可能被 engine sleep、resume、evict、flush；LMCache 模式下可进入 L1/L2 分层缓存 | 通常不作为训练审计数据；LMCache 可以让缓存对象跨请求、跨会话、跨 engine instance 复用 | HBM、CPU pinned memory、GDS NVMe slab、本地 NVMe、Redis/Valkey、S3-compatible object storage、RDMA/NIXL 网络 |
| prefix cache | 后端热缓存块在 HBM 中，命中统计在样本或日志里；LMCache 统计 L1+L2 token hit rate | 命中率影响吞吐、HBM 驻留、L1/L2 预取和淘汰 | 统计可长期保存；真实块是否保存取决于是否部署外部缓存层 | HBM、CPU 内存、本地 NVMe、远端缓存或对象存储 |
| 模型 checkpoint | 训练进程生成 state dict 或 sharded state | 本地 checkpoint 目录和 tracker 文件 | 网络文件系统、对象存储、冷存储保存版本 | 本地 NVMe、网络存储、对象存储、HBM 加载目标 |
| 数据集样本 | dataloader、collator、DataProto 在 CPU 内存中 | tokenized batch 进入 HBM | 大规模样本保存在对象存储或数据湖 | 对象存储、本地 NVMe、CPU 内存、HBM |

## 可量化指标

为了把“agent 运行对存储的影响”从定性描述变成可以跟踪的指标，建议按下面几组采集。

### 上下文指标

- 每轮 `prompt_ids` 长度。
- 每轮 `response_ids` 长度。
- 每轮模型请求的 messages 字节数和 token 估算值。
- `tokens_before`、`tokens_after`、压缩触发次数和压缩失败次数。
- prompt cache 或 prefix cache 的命中 token 数、命中率。
- 被截断、被 microcompact、被 AutoCompact 替换的消息数量。

### 工具结果和 artifact 指标

- 每个任务的工具调用次数。
- 每个工具结果的原始字节数、preview 字节数、落盘字节数。
- `<persisted-output>` 或 replacement 触发次数。
- artifact 数量、artifact 总字节数、最大 artifact 字节数。
- `read_tool_result_artifact` 或类似恢复读取工具的调用次数。
- stdout、stderr、patch、diff、workspace snapshot 的独立字节统计。

### 轨迹和训练样本指标

- turn 数、model call 数、tool call 数。
- transcript JSONL 字节数。
- `response_mask` 中 1 的比例，也就是有效 loss token 比例。
- `rollout_log_probs` 缺失率和长度不匹配次数。
- reward 缺失率、失败轨迹比例、`invalid_for_training` 原因分布。
- 每个训练样本的 token 总数、response token 数、mask 字节数、logprob 字节数。

### checkpoint 和训练 I/O 指标

- checkpoint 总字节数。
- checkpoint shard 数。
- checkpoint 写入耗时、读取耗时和有效带宽。
- 同时保留 checkpoint 版本数量。
- 是否保存 optimizer state、extra state、HF model copy。
- 对象存储上传和下载吞吐。

### KV cache 估算指标

键值缓存可以用下面的粗略公式估算：

```text
KV cache bytes
= token 数
× 层数
× 2（Key 和 Value）
× KV head 数
× head_dim
× 每个元素字节数
× 并发序列数
```

例如，一个使用 grouped-query attention 的模型如果有 80 层、8 个 KV head、`head_dim=128`、`bfloat16` 或 `float16` 两字节元素：

- 32,000 token、并发 1 条序列时，KV cache 约为 9.8 GiB。
- 128,000 token、并发 1 条序列时，KV cache 约为 39.1 GiB。
- 128,000 token、并发 8 条序列时，理论总量约为 312.5 GiB。

这些数值是工程估算，不等于某个具体后端的实际显存占用。实际占用还会受到 tensor parallel、paged attention block size、prefix cache 复用、quantized KV cache、chunked prefill、eviction 策略和后端内存碎片影响。

### LMCache 分层缓存指标

如果部署 LMCache 或类似外部 KV cache 管理层，建议单独采集下面这些指标：

- L0 GPU block lifetime、idle-before-evict、reuse gap。
- L0 到 L1 的 store throughput 和 load throughput，单位可以用 GB/s。
- L1 read chunk 数、write chunk 数、evicted chunk 数。
- L1 当前使用字节数、总容量、eviction trigger watermark 和 eviction ratio。
- L2 store submitted、store completed、prefetch lookup、prefetch hit、prefetch load completed、load completed、evicted objects。
- L2 每个 adapter 的 `l2_usage_bytes`、每个 `cache_salt` 的使用字节数和 quota 命中情况。
- L1+L2 token-level hit rate，也就是 `lookup_hit_tokens / lookup_requested_tokens`。
- L1 到 L2 的端到端吞吐和延迟。这个值包含 adapter queue、网络和磁盘 I/O，不等于裸设备顺序带宽。
- 每个 L2 后端的失败率，例如 L1 allocation failure、L1 read failure、L2 prefetch failure。
- chunk size、hash algorithm、cache salt 粒度、serde 压缩或量化方式，以及是否启用 GDS L1、NIXL、RESP、S3、文件系统或 raw block 后端。

## 对未来 agent 规模化存储需求的判断

### 判断一：长上下文首先推高 HBM 需求，而不是传统意义的磁盘容量

长上下文会增加 transcript 和 JSONL 文件大小，但这些文本通常可以压缩，成本相对可控。真正昂贵的是模型推理阶段的 KV cache。只要 agent 任务需要保留大量历史、并发多个长任务，HBM 容量和缓存调度就会成为关键瓶颈。

这解释了为什么 AutoCompact、microcompact、tool result preview、prefix cache、chunked prefill 这些机制会同时出现：它们都在试图降低每轮请求重新消耗的 token 和 KV cache 压力。

### 判断二：工具调用会显著增加本地 NVMe 和 artifact 管理需求

软件工程 agent 会频繁读取文件、运行测试、搜索代码、生成日志和 patch。工具输出大小高度不稳定，一个失败测试或 grep 结果可能比模型回复大很多。Claude Code 的工具结果落盘机制说明，成熟 harness 不会让所有工具输出长期留在上下文，而是把完整输出转成可恢复 artifact。

因此，本地 NVMe 需求不是只来自模型 checkpoint，也来自高频小文件、JSONL 追加、工具 stdout/stderr、workspace snapshot 和 artifact manifest。这类负载更看重低延迟和稳定写入，而不只是最大容量。

### 判断三：训练样本的关键不是文本，而是 token 级 provenance

verl、Slime、ProRL-Agent-Server 和 renderers 都指向同一个结论：训练可用轨迹必须保存真实采样 token、loss mask、logprob 和 reward。只有自然语言 transcript 或 completion 文本，并不能证明可以进入 policy loss。

这会带来两类存储需求：

- 可训练样本需要额外保存 token 数组、mask 数组、logprob 数组和版本元数据。
- 轨迹审计需要保存足够证据，证明这些 token 不是从后处理文本重新渲染出来的。

这些数组单条样本体积不一定很大，但对数据质量极其关键。规模化以后，它们会成为训练数据湖的一部分。

### 判断四：checkpoint 容量和带宽仍然是训练侧最大持久压力之一

Agentic RL 的单条轨迹可能很长，但模型 checkpoint 仍然容易支配持久容量。特别是在保存 optimizer state、多个 actor 版本、critic、reference model、HF 导出副本和 extra state 时，checkpoint 容量会远大于单批 rollout 样本。

verl fully async trainer 的 checkpoint 路径和 tracker 文件说明，训练系统需要可靠的本地落点和可选远端目录。Slime 也支持通过磁盘 checkpoint 同步权重。这会推高本地 NVMe、网络文件系统和对象存储的吞吐需求。

### 判断五：prefix cache 会把一部分“算力问题”转成“缓存驻留和缓存命中问题”

prefix cache 命中率高时，可以减少重复 prefill 成本。但真实 prefix cache block 仍然要占用推理后端的内存资源。Slime 的 `PrefixCacheInfo` 只是统计字段，不能把它误认为真实缓存块已经持久化。

在普通推理后端里，这主要提高了对 HBM 管理、缓存淘汰策略和多租户隔离的要求。LMCache 则进一步说明，一旦把 KV cache 外挂成 L1/L2 分层缓存，问题会扩展到 CPU pinned memory、NVMe、远端缓存、对象存储、RDMA/NIXL 网络、GDS I/O、缓存命中率和跨进程 GPU 数据搬运。

### 判断六：LMCache 代表一种新的 KV cache 存储基础设施需求

Claude Code、Codex、RepoHarness 更偏 agent 轨迹、工具结果和上下文压缩；verl、Slime、ProRL-Agent-Server 更偏训练样本、logprob、loss mask 和 checkpoint；LMCache 则把注意力放在最底层的 KV cache 生命周期。

它说明长上下文 agent 的存储需求可能出现两条不同路径：

- 如果只使用推理后端内置缓存，KV cache 主要消耗 HBM，落盘的是 transcript、artifact、训练样本和 checkpoint。
- 如果部署 LMCache 这类外部缓存层，KV cache 本身会成为可观测、可驱逐、可复用、可跨后端迁移的缓存对象，存储需求会向 CPU 内存、本地 NVMe、远端键值存储、对象存储和高速网络扩散。

这个结论不等于“KV cache 可以替代训练数据”。它只说明在服务端推理和 agent 多轮长上下文场景里，减少 prefill 重算可能会制造新的缓存容量、缓存带宽和缓存一致性需求。

## 直接事实与工程推断边界

### 直接事实

- Claude Code 文档明确描述工具结果落盘、聚合预算、`ContentReplacementState`、会话 JSONL 和子 agent JSONL。
- Codex 源码明确有 rollout JSONL recorder 和 SQLite `threads` 索引。
- verl 源码明确有 `DataProto`、Ray `MessageQueue`、rollout config、prefix caching 开关、checkpoint 路径和 `kv_cache` resume/release。
- Slime 源码明确有 `Sample`、`loss_mask`、`rollout_log_probs`、`PrefixCacheInfo` 和训练数据转换。
- ProRL-Agent-Server 和 renderers 明确要求 token id、loss mask、logprob 对齐，避免重新渲染历史 sampled token。
- LMCache 文档和源码明确有 KV cache management layer、L1/L2 分层存储、L2 adapter 抽象、文件系统/S3/RESP 等后端、L0/L1/L2 命中和吞吐指标，以及 vLLM multiprocess connector。
- RepoHarness 自身明确有 `TrainingView`、artifact writer 和 AutoCompact record。

### 工程推断

- HBM 是普通推理后端中 KV cache 和活跃推理状态的主要承载层，这是根据 vLLM、SGLang、Transformers 的常见执行模型，以及 verl 和 Slime 对 `kv_cache`、weights、GPU memory 的管理接口推断。LMCache 证明这不是唯一形态，KV cache 也可以被专门系统外部化到 L1/L2 分层缓存。
- 对象存储和冷存储适合长期保存轨迹、数据集和 checkpoint，这在本仓库中只有部分路径直接出现，例如 `default_hdfs_dir`，其余属于规模化训练系统的合理外推。
- 工具结果和 transcript 更偏本地 NVMe，这来自 Claude Code、Codex 和 RepoHarness 的文件化记录方式；不同产品可以把这些文件进一步同步到远端。
- KV cache 不应和可训练轨迹混淆。即使 LMCache 可以持久化或远端化 KV cache，它仍主要服务推理加速和缓存复用，不等价于包含 `response_ids`、`loss_mask`、`rollout_log_probs`、reward 和参数版本的训练样本。

## 最终结论

从现有仓库内的 agent harness 和 RL 框架看，agent 任务对存储硬件的影响可以概括为：

1. **长上下文和多轮任务主要推高 HBM 需求**，因为 KV cache 随 token 数、层数、KV head 数和并发序列数增长。
2. **工具调用主要推高本地 NVMe 和 artifact 管理需求**，因为 stdout、stderr、搜索结果、测试日志、patch 和 workspace snapshot 会频繁落盘。
3. **训练化 agent 轨迹主要推高 token 级数据存储需求**，因为可训练样本必须保留 `response_ids`、`loss_mask`、`rollout_log_probs`、reward 和版本信息。
4. **RL 训练 checkpoint 仍然是持久容量和写入带宽的大头**，尤其当需要保存多个版本、optimizer state 和远端副本时。
5. **prefix cache、KV cache 外部化和上下文压缩不会消灭存储需求，而是改变需求位置**：它们减少重复 token 和 prefill 成本，但会增加摘要、replacement、cache metadata、显存驻留、L1/L2 分层缓存、远端后端和缓存淘汰管理的重要性。

如果后续要把本报告变成可运行的度量工具，优先应采集每个任务的 token 长度、工具结果字节数、artifact 字节数、有效 loss token 数、logprob 对齐状态、checkpoint 字节数、KV cache 估算值，以及 LMCache 类系统的 L0/L1/L2 命中率、逐层吞吐、逐层容量和 eviction 次数。这些指标比单纯统计“会话文本长度”更能反映 agent 任务对存储体系的真实影响。
