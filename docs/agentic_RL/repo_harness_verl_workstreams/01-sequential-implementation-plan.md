# RepoHarness 接入 verl 的顺序实施计划

本文档把 RepoHarness 接入 verl 的实现路线从“两个并行 worktree”改为“单一路线、分阶段执行”。目标是避免 agent 之间缺少沟通时接口跑偏，同时覆盖 Harness 侧为了支持在线强化学习 rollout 必须做的训练提速改造。

```text
status: design_plan_v1_contract_hardened
scope: planning_only_not_current_implementation
depends_on:
  - shared_contracts/01-episode-contract.md
  - shared_contracts/02-llm-gateway-contract.md
  - shared_contracts/03-training-view-and-audit-ref-contract.md
  - shared_contracts/04-timing-and-resource-contract.md
  - shared_contracts/05-acceptance-contract.md
  - shared_contracts/06-contract-hardening-v1.md
```

## 1. 总体路线

第一版不直接并行开发 verl adapter 和 Harness training fast，而是按照下面顺序推进：

```text
Stage 0：冻结 shared contracts 和验收 fixture
Stage 0H：contract hardening v1，补齐 token / mask / logprob / visibility / cancellation / throughput 硬门槛
Stage 1：新增训练后端无关的 schema 包和最小 LLMGateway contract
Stage 2：抽出 RepoHarnessRuntime.run_episode(...)
Stage 3：实现 run_mode 与 training_fast recorder
Stage 4：实现 timing/resource summary
Stage 5：完善 LLMGateway route 实现和模型后端迁移
Stage 6：实现 workspace/container 复用和训练环境加速
Stage 7：实现 verifier worker pool 和 reward 边界
Stage 8：实现训练预算、no-progress 控制和上下文瘦身
Stage 9：实现并发安全和资源租约
Stage 10：实现 TrainingView 到 AgentLoopOutput 的转换
Stage 11：实现 RepoHarnessVerlAgentLoop 与 VerlLLMGateway
Stage 11.5：接通真实 RepoHarness episode runtime bridge
Stage 12：端到端 smoke、性能 smoke 和 visibility 验收
Stage 12.5：同步高吞吐基线加固，补齐依赖环境缓存、共享 workspace cache、verifier / recorder 热路径和吞吐 profile
Stage 12.6：Stage 12.5 修改后远端 RL 链路回归 smoke
Stage 13：fully async 分阶段演进，先固定异步生命周期 contract，再接入 verl fully async 训练路径
Stage 14：fully async 可复现验收与 partial rollout / resume 前置能力
```

这条路线的核心思想是：先让 RepoHarness 自己成为稳定、可复用、可审计、可加速的 episode runtime，再让 verl adapter 调用它。不要让 verl adapter 成为第二套 Harness。

## 2. 当前慢点和必须覆盖的 Harness 改造

RepoHarness 现在面向评测和审计的运行方式可以完成真实任务，但如果直接用于在线强化学习 rollout，会遇到下面几类吞吐瓶颈：

| 慢点 | 当前风险 | 顺序计划中的改造 |
| --- | --- | --- |
| 模型调用等待 | 如果推理后端吞吐不足、排队严重或者单次生成过长，单条轨迹仍会成为 rollout 吞吐瓶颈。第一版在线训练主线优先走 verl 管理的本地推理服务，不默认走外部 API | `LLMGateway`、verl `LLMServerClient`、vLLM / SGLang batching、sticky session / prefix cache、generation timeout、max output tokens 和推理服务并发控制 |
| 每条任务创建容器和 workspace | 即使 image 已经构建好，每条 episode 仍要创建容器、materialize workspace、做 setup | workspace snapshot、dependency cache、copy-on-write episode workspace、可选 warm container pool |
| baseline 和 final verifier 固定成本 | 每条任务都完整执行 verifier 会占用大量非模型时间 | baseline cache 策略、verifier worker pool、同步等待 reward 的第一版边界 |
| full audit artifact 写入 | 完整 raw model request、raw model response、可选推理痕迹和超大 prepared messages 会拖慢训练 | `run_mode=training_fast`、轻量 recorder、hash/ref/压缩/抽样策略 |
| 上下文准备和大文件读取 | 大文件进入模型上下文会放大后续 token 成本 | tool 输出裁剪、range read、ranked snippets、context budget 和 file size policy |
| 无进展探索 | 长时间只读搜索、重复 grep、没有 patch progress 的轨迹会浪费 rollout 资源 | no-progress stop、max turns、重复工具调用限制、patch progress heuristic |
| 串行 rollout | 单条轨迹慢时，在线 RL 必须靠并发 | run directory 隔离、workspace lease、artifact lock、推理 route 并发限制、后续 fully async |
| 指标缺失 | 没有结构化 timing/resource summary 时很难判断瓶颈 | 每条 episode 输出 timing summary 和 resource summary |

这些改造都必须进入第一版实施计划。否则即使 verl adapter 能跑通，训练吞吐仍然会被 Harness 固定成本卡住。

Stage 12 已经用于证明真实链路可以跑通，但它不是最终吞吐形态。进入 Stage 13 fully async 之前，必须增加 Stage 12.5，先处理已经暴露出来的训练吞吐问题；Stage 12.5 提交后还必须通过 Stage 12.6 的远端回归 smoke，确认这些吞吐和安全改造在真实 GPU 训练链路中仍然可用：

- `real_episode` 目前主要复用源码 snapshot 和 workspace lease，没有真正复用已经安装好的依赖环境。
- 如果没有显式传入共享 `WorkspaceSnapshotManager` 或共享 cache root，默认 snapshot cache 仍可能落在每条 run directory 下，不适合训练时跨 episode 复用。
- workspace lease 当前仍以整棵目录复制和整棵目录删除作为正确性基线，大仓库、构建产物或前端依赖目录会放大文件系统开销。
- final verifier 虽然已经有 worker pool 能力，但真实训练脚本必须默认接入有界 verifier pool，否则 pytest 等验证命令会成为 CPU 阻塞点。
- `training_fast` 已经降低 raw provider artifact 风险，但命令输出、artifact manifest 和 run evidence 仍可能在热路径上产生大量小文件写入。
- Stage 12 的 trainer 配置是正确性 smoke，不是吞吐 profile；小 batch、单 agent worker、低推理并发和较大的固定 padding 都会让 GPU 和 Ray worker 吃不满。
- 推理服务侧的 queue wait、prefill、decode、prefix cache、KV cache eviction、preemption 和 GPU 利用率必须单独观测，否则容易把推理服务吞吐问题误判成 RepoHarness runtime 问题。
- tokenizer、chat template 和 prompt build 是多轮 agent 的 CPU 热点。每轮都重新构造增长中的 messages、套 chat template、tokenize，会在高并发 rollout 时明显占用 CPU。
- Ray worker、AgentLoopWorker、RepoHarness runtime、默认线程池和 verifier pool 的共享边界必须清楚，否则 `agent.num_workers` 提高后可能只是把阻塞从 GPU 端转移到本地线程池、文件系统或 verifier 队列。
- DataProto 固定 padding、有效 token 比例和 loss mask 利用率必须进入 profile，否则 batch 看似变大，实际有效训练 token 可能很少。
- `TimingSummary` / `ResourceSummary` 必须进一步解释 setup、source hash、snapshot materialization、dependency restore、tool、verifier、artifact write 和 valid sample filtering，否则无法判断 Stage 13 的异步化是否真的解决了瓶颈。

Stage 12.5 触碰了共享依赖环境、模型命令策略、隐藏 runtime 目录、formal batch validator、batch refill 和训练侧 profile helper。这些改动本地单元测试可以覆盖规则，但不能完全证明远端真实推理服务、真实模型、Ray worker、DataProto 组 batch 和 trainer 小步路径仍然保持闭环。因此 Stage 12.5 提交后、Stage 13 之前，必须新增 Stage 12.6 远端回归 smoke，优先复用此前 `2 * RTX PRO 6000` 或等价 GPU 环境，重新验证当前提交哈希下的完整 RL 链路。

## 3. Stage 0：冻结 shared contracts 和 canonical fixture

目标：先固定所有后续阶段共同遵守的对象边界。

需要完成：

1. 确认 `shared_contracts/` 中的 contract 版本号。
2. 确认 `RepoHarnessEpisodeRequest`、`RepoHarnessEpisodeResult`、`LLMGatewayRequest`、`LLMGatewayResponse`、`TrainingView`、`GenerationRecord`、`AuditRef`、`TimingSummary`、`ResourceSummary`、`ResponseSpan` 的必填字段和可选字段。
3. 增加 canonical JSON fixture：

```text
tests/fixtures/repo_harness_verl/
  canonical_episode_request.json
  canonical_episode_result.json
  canonical_training_view.json
  canonical_audit_ref.json
  canonical_llm_gateway_request.json
  canonical_llm_gateway_response.json
  canonical_multiturn_tool_episode_result.json
  canonical_response_overflow_invalid_result.json
  canonical_empty_response_invalid_result.json
  canonical_mixed_logprob_batch_rejected.json
  canonical_audit_path_access_denied.json
  sha256_manifest.json
```

4. 所有后续阶段必须运行同一套 fixture serialization test。
5. 明确 visibility denylist：hidden verifier、gold patch、完整 reward metadata、accepted label、provider secret、evaluator-only logs 不能进入模型可见 prompt、response target、`raw_prompt` 或可传播 `extra_fields`。
6. 为每个 contract 字段补充字段级契约：`required`、`optional`、`default`、缺失时是 schema error / runtime invalid / adapter default、是否允许进入 verl non-tensor batch、是否模型可见、是否 evaluator-only。
7. 固定唯一 `LLMGateway.route` 枚举：`verl`、`openai`、`deepseek`、`local_vllm`、`local_sglang`、`replay`、`mock`。route=verl 内部使用 `inference_backend=sglang|vllm` 区分真实推理后端，不再使用 `verl_llm_server_client` 作为 route 值。
8. 固定版本治理矩阵：`verl_commit`、Python 版本、Ray 版本、vLLM 版本、SGLang 版本、transformers 版本、torch 版本、训练模型 tokenizer / processor / chat template 来源。Mac 本地可以只跑 `verl-lite` 结构验收；Vast.ai 训练前必须记录真实 GPU 环境矩阵。
9. 为 `extra`、`extra_fields`、`provider_options`、`tracing` 等开放字段定义 allowlist 或 `repo_harness_*` 命名空间策略，不允许自由透传未知 evaluator-only 字段。

### 3.1 Contract hardening v1 硬门槛

进入 Stage 1 代码实现前，必须先把下面硬门槛写入 shared contracts、canonical fixture 和验收测试。这个小阶段是本 review 后新增的 contract hardening gate，用来避免“接口能跑但训练语义错误”。

**训练张量形状不变量：**

```text
len(prompt_ids) <= rollout.prompt_length
0 < len(response_ids) <= rollout.response_length，除非 invalid_for_training=true
len(response_ids) == len(response_mask)
正式 PPO / GRPO batch 中所有样本都必须有 response_logprobs
len(response_logprobs) == len(response_ids)
所有 response_mask=0 的工具 observation token 对应 response_logprobs=0.0
response_ids 为空且 reward_score 非空的样本必须在进入 verl 前被拦截
```

如果超过 `rollout.prompt_length` 或 `rollout.response_length`，第一版不允许静默截断后继续训练。必须明确写入 `status_reason`、`budget_consumption.stop_reason` 和 audit diagnostics；默认标记 `invalid_for_training=true`，除非后续显式实现 span-aware truncation 并通过专门验收。

**span 级 token provenance：**

`TrainingView` 或 `RepoHarnessEpisodeResult` 必须携带 `response_spans`，用于解释 `response_ids` 中每个连续片段的来源。每段至少包含：

```text
start
end
source_type: assistant_generation | tool_observation | environment_observation | padding_excluded | truncated_excluded
model_call_id
tool_call_id
artifact_ref
response_mask_value
logprob_policy
policy_version
global_steps
min_global_steps
max_global_steps
```

多轮工具调用 canonical fixture 必须覆盖：初始 prompt、assistant 生成工具调用、tool observation、下一轮 assistant 最终回答，以及对应的 `response_ids`、`response_mask`、`response_logprobs` 和 `response_spans`。Mac 可以用小 tokenizer 做结构验收；Vast.ai 必须使用真实训练模型 tokenizer / processor / chat template 做同类验收。

**audit opaque reference 和工具不可达性：**

audit artifact 必须位于模型 workspace 之外，默认不能被模型工具访问。进入 `AgentLoopOutput.extra_fields` 的 audit 信息必须是 opaque reference，也就是不可由模型工具直接解析成本地路径的非透明引用标识；不要把绝对 `run_dir`、reward metadata 路径、final verifier 路径或 gold patch 路径直接放入 verl batch。

工具层必须增加 denylist 或 capability check，覆盖 run directory、acceptance bundle、reward metadata、final verifier artifact、hidden selector、hidden test patch、gold patch、evaluator-only raw output。Stage 12 visibility test 必须模拟模型调用 `read_file`、`grep`、`read_tool_result_artifact` 访问这些路径，并稳定拒绝。

**DataProto 和 TransferQueue 可见性：**

visibility 验收不能只检查 `TrainingView.extra_fields`。第一版必须覆盖普通 `AgentLoopWorker._agent_loop_postprocess(...)`、`main_ppo_sync.py` / TransferQueue 路径、`DataProto` concat / select / pop 后的 tensor batch、non-tensor batch 和 meta_info。`RepoHarnessVerlAgentLoop` 构造 request 时必须对 `kwargs` 使用 allowlist，第一版只允许：

```text
raw_prompt
agent_name
task_id
run_config_ref
budget_ref
agent_policy_ref
episode_seed
```

Stage 11 / Stage 11.5 第一版不启用模型可见 context refs。后续如果需要启用这类字段，必须先新增明确的 schema 投影字段、visibility 测试和 request mapping 测试，不能只把字段加入 allowlist。

`raw_prompt` 只允许模型可见内容。其他 evaluator-only 字段只能留在 RepoHarness run artifact 中，由 opaque `AuditRef` 间接回查。

阶段出口：

- 文档和 fixture 对齐。
- 字段变化必须先更新 shared contracts，再进入代码。
- 上述 contract hardening v1 fixture 和 visibility tests 通过。

第一版默认决策：

- canonical fixture 放在 `tests/fixtures/repo_harness_verl/`。文档目录只保留说明和字段解释，不作为测试 fixture 的唯一来源。

## 4. Stage 1：新增训练后端无关的 schema 包和最小 LLMGateway contract

目标：让 RepoHarness core 暴露和 verl 无关的 RL episode schema，避免被 verl 绑定死。

建议新增：

```text
src/repo_harness/rl/
  __init__.py
  episode.py
  gateway.py
  training_view.py
  timing.py
  visibility.py
```

职责：

- `episode.py`：定义 `RepoHarnessEpisodeRequest`、`RepoHarnessEpisodeResult`、状态码、错误类型。
- `gateway.py`：定义 `LLMGatewayRequest`、`LLMGatewayResponse`、`GenerationRecord`。
- `training_view.py`：定义 `TrainingView`、`AuditRef`、训练输出约束。
- `timing.py`：定义 `TimingSummary`、`ResourceSummary`。
- `visibility.py`：定义模型可见字段、训练可传播字段和禁止字段检查。

同时定义最小 `LLMGateway` protocol 和 fake/mock gateway，供 Stage 2 的 runtime facade 测试使用：

```python
class LLMGateway:
    async def generate_turn(
        self,
        request: LLMGatewayRequest,
    ) -> LLMGatewayResponse:
        ...
```

第一版 fake/mock gateway 只需要稳定返回可测试的 `LLMGatewayResponse`，用于验证 runtime、recorder、reward 和 `GenerationRecord` 构造；真实模型后端和 route=verl 可以放到 Stage 5 和 Stage 11。

阶段出口：

- schema 能构造、序列化、反序列化。
- canonical fixture sha256 稳定。
- schema 包不 import verl。
- `LLMGateway.generate_turn(...)` 命名和 shared contract 对齐。
- fake/mock gateway 能支持最小 runtime 单元测试。

## 5. Stage 2：抽出 RepoHarnessRuntime.run_episode(...)

目标：把当前 CLI / evaluation runner 的运行任务流程抽成可复用 runtime facade。

建议接口：

```python
class RepoHarnessRuntime:
    async def run_episode(
        self,
        request: RepoHarnessEpisodeRequest,
        *,
        llm_gateway: LLMGateway,
    ) -> RepoHarnessEpisodeResult:
        ...
```

第一版可以内部复用现有同步 agent loop、workspace、verifier 和 recorder，但外层接口建议面向 async。原因是 verl `AgentLoopBase.run(...)` 本身是异步函数，后续 fully async 也需要中断、恢复和取消。

需要改造：

1. 从当前 evaluation runner / CLI run task 中拆出下面步骤：

```text
parse task/config
  -> build RepoHarnessEpisodeRequest
  -> materialize workspace
  -> prepare context
  -> run agent loop
  -> run final verifier
  -> compute reward
  -> record artifacts
  -> build RepoHarnessEpisodeResult
```

2. CLI 保留，但改成调用 `RepoHarnessRuntime.run_episode(...)`。
3. 后续 verl adapter 也调用同一个 runtime，不直接调用 CLI。
4. `RepoHarnessEpisodeRequest.agent_policy` 必须显式固定 scaffold、工具、权限、上下文、反馈策略和预算，不能由 CLI 和 adapter 各自猜默认值。
5. `RepoHarnessEpisodeResult.status` 必须区分：

```text
succeeded
failed
no_progress
timeout
infrastructure_error
invalid_task
cancelled
```

6. Stage 2 必须前置定义 cancellation / timeout / cleanup contract，不能等到 Stage 9 并发安全阶段再补。外层 coroutine 被取消、episode timeout、provider timeout、verifier timeout、Docker command timeout、workspace cleanup 失败时，都必须有明确 ownership。
7. `run_episode(...)` 内部必须有 `try/finally` 或等价资源保护，确保释放 workspace lease、container lease、artifact writer 和 verifier worker future。
8. 清理失败不能覆盖原始 episode 状态，但必须写入 diagnostics 和 `ResourceSummary.cleanup_status`。
9. 如果内部临时用 executor 包同步逻辑，必须配置 executor 最大并发数，受 Ray worker、CPU、Docker daemon、file descriptor 和 verifier worker pool 限制共同约束。

阶段出口：

- CLI run task 仍能跑。
- 新 runtime facade 可以用 fake gateway 跑最小 episode。
- 失败状态不会被误当成普通模型失败样本。
- fake gateway cancellation smoke 通过：在 agent loop 中途取消，仍能看到 run directory、workspace lease、artifact manifest 和 cleanup diagnostics 的确定状态。
- timeout 后必须产出最小 `RepoHarnessEpisodeResult` 或明确 infrastructure error artifact，不能留下只有 Ray exception 而没有 audit ref 的样本。

第一版默认决策：

- runtime facade 第一版放在 `src/repo_harness/rl/runtime.py`。不放在 `src/repo_harness/evaluation/runtime.py`，避免 verl、slime 和本地 batch runner 依赖 evaluation 模块语义。
- `run_episode(...)` 第一版外层使用 async 接口；内部可以先复用同步 agent loop、workspace、verifier 和 recorder，并用 executor 或等价方式包起来。
- cancellation 后第一版优先返回 `EpisodeResult(status=cancelled, invalid_for_training=true)`；只有无法构造最小 result 的基础设施崩溃才向外抛出异常。

## 6. Stage 3：实现 run_mode 与 training_fast recorder

目标：保留 RepoHarness 的可审计能力，同时把训练 rollout 的 artifact 固定成本降下来。

支持模式：

```text
run_mode=full_audit
  面向评测和复查，保留完整 transcript、events、raw model response、可选推理痕迹和完整 artifact。

run_mode=training_fast
  面向在线训练，保留必要 hash、引用、patch、reward、verifier summary、timing summary；减少或异步处理大体积 artifact。

run_mode=training_debug
  面向调试，介于 full_audit 和 training_fast 之间，可以抽样保留更多原始材料。
```

training_fast 默认策略：

1. 不保存外部 provider 可能返回的明文 reasoning / thinking trace。
2. 不默认保存完整 raw model request / response；保留 hash、大小、截断 preview 和 artifact reference。
3. 超大 prepared messages 使用 hash、压缩、抽样或 projection ref。
4. transcript、events、artifact manifest、reward metadata、final verifier、patch、timing summary 必须保留稳定引用。
5. `AuditRef` 中只放短引用，不放完整大文本。
6. `TrainingView.extra_fields` 中只放短小、稳定、可传播的引用。

需要改造：

- RunRecorder 支持 recorder profile。
- artifact manifest 标记 artifact 是否完整、压缩、抽样、截断或仅 hash。
- export / training export 能识别 `training_fast` artifact，不把缺失的 raw response 误判为审计失败。
- visibility test 覆盖 `raw_prompt`、`extra_fields`、transcript projection 和 export projection。

阶段出口：

- 同一条任务用 `full_audit` 和 `training_fast` 都能跑。
- `training_fast` artifact 体积达到量化门槛：同一任务相比 `full_audit` 至少下降 50%，或者在 artifact manifest 中逐类说明为什么达不到该阈值。
- fake gateway 固定成本 benchmark 通过：8 条最小 episode 并发运行时，非模型 p95 wall time 必须低于人工配置阈值；第一版默认阈值为 180 秒，后续可以根据 Vast.ai 实测调整。
- 每条 `TimingSummary` 必须能解释至少 95% 的 outer wall time；否则必须把缺口写入 `timing_unattributed_seconds` 和 diagnostics。
- 结构化 `AuditRef` 和进入 batch 的 opaque refs 仍然能反查关键证据。

第一版默认决策：

- `training_fast` 默认不保存完整 raw model response，只保存 hash、大小、截断 preview 和 artifact reference。抽样保存只允许在显式开启的调试配置中发生。
- `training_fast` 禁止保存外部 provider 可能返回的明文 reasoning / thinking trace。`training_debug` 可以显式开启这类材料，但只用于外部 provider 调试；route=verl 主线不依赖这类字段。
- 如果 artifact 写入仍然占比高，`training_fast` 可以引入异步或批量 artifact writer，但 crash 后必须仍能通过 audit ref 找到关键证据，或者把 sample 明确标记为 invalid。

## 7. Stage 4：实现 TimingSummary 和 ResourceSummary

目标：每条 episode 都能解释时间花在哪里、资源如何使用。

TimingSummary 至少覆盖：

```text
rollout_wall_seconds
workspace_materialization_seconds
docker_setup_seconds
dependency_restore_seconds
baseline_verifier_seconds
context_prepare_seconds
model_call_seconds
tool_seconds
final_verifier_seconds
reward_compute_seconds
artifact_write_seconds
cleanup_seconds
queue_wait_seconds
```

ResourceSummary 至少覆盖：

```text
workspace_backend
docker_image_ref
docker_image_digest
container_id_or_lease_id
snapshot_key
snapshot_cache_hit
snapshot_restore_strategy
dependency_cache_key
dependency_cache_hit
baseline_cache_hit
container_reuse_hit
network_policy_ref
permission_policy_ref
cpu_limit
memory_limit
disk_limit
inference_route
inference_concurrency_slot
verifier_worker_pool_id
```

要求：

- 优先从现有 event duration、model call duration、workspace command result、verifier result 汇总，不要只用外层 wall clock 猜。
- timing summary 写入 artifact，并通过结构化 `AuditRef` 和 `TrainingView.extra_fields.repo_harness_timing_summary_ref` 回指。
- RepoHarness 详细 metrics 不能硬塞进 verl `AgentLoopMetrics` 后丢失，只把能直接映射的字段放入 `verl_metrics`。

阶段出口：

- 成功、失败、timeout、infrastructure error 都有 timing/resource summary。
- 后续可以用这些 summary 判断训练吞吐瓶颈。

## 8. Stage 5：完善 LLMGateway route 实现和模型后端迁移

目标：在 Stage 1 已经定义最小 `LLMGateway` contract 和 fake/mock gateway 的基础上，把 RepoHarness agent loop 中的真实模型调用逐步迁移到 gateway。完成后，同一套 agent loop 在线强化学习主线优先走 route=verl，也就是通过 `VerlLLMGateway` 调用 verl 已经管理的 `LLMServerClient`、vLLM 或 SGLang；OpenAI / DeepSeek 等外部 provider route 只作为评测、调试或离线兼容路线保留，避免 RepoHarness 被某一个训练后端或某一个商业 API 绑定死。

接口方向：

```python
class LLMGateway:
    async def generate_turn(self, request: LLMGatewayRequest) -> LLMGatewayResponse:
        ...
```

需要支持的 route：

```text
verl
openai
deepseek
local_vllm
local_sglang
replay
mock
```

route=verl 内部的真实推理后端通过 `inference_backend=sglang|vllm` 区分，不再使用 `verl_llm_server_client` 作为 route 名称。canonical fixture 和 pydantic schema 必须拒绝未登记 route。

要求：

1. RepoHarness core 只依赖 `LLMGateway` contract，不直接 import verl。
2. route=verl 时，`VerlLLMGateway` 使用 verl tokenizer / processor / chat template 和 `LLMServerClient.generate(...)`。
3. 每次模型调用产生 `GenerationRecord`，记录 turn、model_call_id、prompt ids、output token ids、log probabilities、stop reason、route、inference_backend、policy version、`global_steps`、`min_global_steps`、`max_global_steps`、request hash 和 response ref。
4. 正式训练 token 不能从最终 transcript 重新分词伪造，必须来自真实 rollout generation 路径。
5. `sticky_session_id` 建议使用 `episode_id`，帮助 verl server manager / vLLM / SGLang 命中 prefix cache。
6. 第一版固定 RepoHarness tool call parser 为权威 tool semantics。`LLMGatewayResponse.output_token_ids` 必须保留模型原始生成 token；parser 后的 `assistant_message` 和 `tool_calls` 只能作为结构化解释，不能反过来用于构造训练 token。
7. 如果 parser 修复 malformed tool call，必须记录原始 output token ids、parser id、parser repair type、repair 是否进入模型可见 observation，以及该段 response mask 是否仍然为 `1`。
8. 正式 online PPO / GRPO 路径只允许 route=verl。provider route 产出的 `TrainingView` 默认 `invalid_for_online_rl=true`，除非明确证明 token provenance 和 log probability 满足正式训练要求。

阶段出口：

- 现有模型调用路径通过 gateway 仍能跑。
- fake/mock gateway 可以稳定生成测试轨迹。
- route=verl 的具体实现可以等 Stage 11，但 contract 必须先稳定。
- provider route 样本不会被伪装成 rollout policy sample。它可以进入 SFT export、preference data、teacher data generation 或 offline diagnostic replay，但默认不能进入 PPO / GRPO policy loss。

第一版默认决策：

- 第一版保留现有 provider client 入口作为兼容层，避免破坏当前外部 API 测评和 V5 debug；同时新增 `ProviderLLMGateway` 包装现有 provider client。后续再逐步把公开主路径迁移到 `LLMGateway`。

## 9. Stage 6：workspace/container 复用和训练环境加速

目标：解决“已经有 Docker image，但每条任务仍要创建容器、workspace、setup、baseline、verifier 导致很慢”的问题。

第一版不要把它做成不可控的全局共享环境，而是做成可审计的 snapshot / lease 系统。

建议 snapshot key：

```text
snapshot_key =
  repo_ref
  + base_commit
  + environment_id
  + docker_image_digest
  + setup_command_hash
  + dependency_lock_hash
  + toolchain_version
```

分层设计：

```text
Docker image:
  系统依赖和基础工具层。

dependency cache:
  pip / uv / npm / pnpm / pytest cache 等依赖缓存。

clean workspace snapshot:
  已经 checkout 到 base commit，完成允许的 setup，且通过 clean-state 校验的只读或可复制快照。

episode workspace:
  每条 rollout 从 clean snapshot 派生的独立可写工作区。

container lease:
  可选。训练模式可以复用 warm container 或 worker process，但每条 episode 必须拿到干净 workspace。
```

需要改造：

1. workspace manager 支持 snapshot create / lookup / materialize。
2. Docker backend 支持基于 image digest 和 snapshot key 的缓存命中。
3. dependency cache 有明确路径、大小限制、清理策略和 hash。
4. episode workspace 必须 copy-on-write 或等价隔离，不能污染下一条样本。
5. final verifier 必须在 clean-state 语义下运行，不能被前一条 episode 的 patch、缓存或环境变量污染。
6. baseline verifier 可以缓存，但必须绑定 `repo_ref + base_commit + environment_id + verifier_config_hash`，并在 audit 中记录 cache hit。
7. cleanup 失败必须进入 diagnostics，不能静默吞掉。

阶段出口：

- 第一条任务可以创建 snapshot。
- 后续同 key 任务可以复用 snapshot。
- 并发两条 episode 不共享可写 workspace。
- `ResourceSummary` 记录 snapshot key、snapshot cache hit、dependency cache hit、baseline cache hit、container reuse hit、snapshot restore strategy、lease id 和 cleanup 结果。

第一版默认决策：

- 第一版环境复用优先做 workspace snapshot 和 dependency cache；warm container pool 放到后续优化阶段。
- macOS 本地第一版使用普通目录复制作为正确性基线；可选支持 APFS clone。不要默认使用 hardlink 作为可写 workspace 派生方式，避免写入污染；overlayfs 只作为 Linux / Vast.ai 环境的可选 backend。

## 10. Stage 7：verifier worker pool 和 reward 边界

目标：第一版仍然在 episode 返回前拿到 reward，但 verifier 执行层可以池化、限流和记录排队时间。

第一版策略：

```text
submit final verifier
  -> verifier worker pool 执行
  -> await result
  -> compute reward
  -> build RepoHarnessEpisodeResult
  -> return TrainingView / AgentLoopOutput
```

明确不做：

```text
第一版不做 async reward backfill。
第一版不返回没有 reward 且看起来像普通成功的 online RL 样本。
```

需要改造：

- verifier worker pool 支持 timeout、queue wait、worker id、pool id。
- final verifier 结果和 reward metadata 写入 artifact，并通过 `AuditRef` 回指。
- infrastructure error、timeout、invalid task 与模型任务失败分开。
- verifier 失败不能伪装成模型负样本，除非策略明确声明。
- reward 只进入 `reward_score` 和 reward artifact，不能进入模型可见 prompt、response ids 或 `raw_prompt`。

阶段出口：

- reward 可同步返回。
- verifier queue wait 和执行耗时进入 TimingSummary。
- 基础设施错误标记为 invalid，不误训模型。

第一版默认决策：

- no-progress 默认保守处理：`status=no_progress` 且 `invalid_for_training=True`。只有在 reward policy 显式声明时，部分 no-progress 才可以作为 negative sample 进入训练；基础设施错误、工具系统错误、workspace 污染和 verifier 失败不能伪装成模型负样本。

## 11. Stage 8：训练预算、no-progress 控制和上下文瘦身

目标：减少长时间无效 rollout 和大上下文带来的 token 成本。

训练默认预算建议：

```text
max_turns: 12 到 20 起步
generation_timeout_seconds: 按推理 route 和模型单独配置
generation_retry_budget: 限制推理失败重试次数
reasoning_effort / thinking_mode: 仅在外部 provider route 支持时作为兼容配置，route=verl 主线不依赖这类字段
max_output_tokens: 比 full_audit 更小
max_prompt_tokens: 限制单轮 prompt 上限
max_total_tokens: 限制整条 episode token 总量
max_model_calls: 限制整条 episode 模型调用次数
max_tool_output_chars: 限制单次工具观察
max_tool_observation_tokens: 限制进入训练序列的工具观察 token
max_verifier_seconds: 限制 verifier 执行时间
max_workspace_materialization_seconds: 限制 workspace materialization 时间
max_read_file_bytes: 默认范围读取
max_repeated_searches: 限制重复搜索
max_read_only_turns_without_patch: 限制连续只读探索
```

需要改造：

1. agent loop budget manager 支持训练模式参数。
2. tool system 支持 range read、结构化片段读取、短 grep context、ranked snippets。
3. context builder 避免整文件泛读，把大文件以 hash、snippet ref 或分段摘要进入上下文。
4. no-progress detector 记录触发原因：

```text
repeated_search
read_only_loop
no_patch_after_budget
tool_error_loop
generation_timeout_loop
context_too_large
```

5. 提前停止后必须有明确 status、diagnostics 和 reward 策略。

阶段出口：

- 训练模式不会默认跑 60 轮无进展探索。
- 大文件不会默认完整进入后续模型上下文。
- no-progress 样本可审计、可过滤。

## 12. Stage 9：并发安全和资源租约

目标：让多条 episode 可以并发运行，为后续在线 RL rollout 和 fully async 做基础。

需要改造：

1. run id、episode id、workspace id、artifact manifest path 全部唯一。
2. recorder 写入有 lock 或单 writer 约束。
3. workspace lease 支持 acquire / release / cleanup / diagnostics。
4. verifier worker pool 有 queue wait 和 worker id。
5. 推理 route 有 concurrency limit、rate limit 和 retry budget。
6. 取消和 timeout 能清理 workspace / container lease / artifact writer。
7. 两条 episode 并发时不能互相污染 patch、env var、cache metadata 或 artifact manifest。

阶段出口：

- 两条极小 episode 并发运行通过。
- cleanup 失败有 diagnostics。
- ResourceSummary 能反查资源租约。

## 13. Stage 10：TrainingView 到 AgentLoopOutput 的转换

目标：在真正接 verl 前，先把 RepoHarness 的训练视图转换成 verl agent loop 可消费的输出形态。

转换规则：

```text
TrainingView.prompt_ids -> AgentLoopOutput.prompt_ids
TrainingView.response_ids -> AgentLoopOutput.response_ids
TrainingView.response_mask -> AgentLoopOutput.response_mask
TrainingView.response_logprobs -> AgentLoopOutput.response_logprobs
TrainingView.reward_score -> AgentLoopOutput.reward_score
TrainingView.verl_metrics -> AgentLoopOutput.metrics
TrainingView.extra_fields + AuditRef opaque refs -> AgentLoopOutput.extra_fields
```

要求：

- `len(prompt_ids) <= rollout.prompt_length`。
- `0 < len(response_ids) <= rollout.response_length`，除非 `invalid_for_training=true`。
- `response_ids`、`response_mask`、`response_logprobs` 长度对齐。
- assistant generated token 的 mask 为 `1`。
- tool observation token 和 padding 的 mask 为 `0`，并且对应 `response_logprobs=0.0`。
- 正式 PPO / GRPO batch 中所有样本都必须有 `response_logprobs`，不允许同一个 batch 内部分样本有、部分样本没有。
- `response_ids` 为空但 `reward_score` 非空的样本必须在进入 verl 前拦截，不能触发 verl `rm_scores[-1]` 的空序列问题。
- `AuditRef` 不能作为嵌套对象进入 `extra_fields`。进入 `AgentLoopOutput.extra_fields` 的只允许 `repo_harness_*` namespaced flat scalar 字段和 opaque references。
- 不在我们自己的 `extra_fields` 里提前写 `raw_prompt`；`raw_prompt` 由 verl postprocess 从 `kwargs["raw_prompt"]` 写入。
- visibility test 必须检查 postprocess 后最终 `AgentLoopOutput.extra_fields`。
- converter 必须使用本地 `reference/verl` 的 `AgentLoopOutput` 和 postprocess 行为做测试，而不仅是自定义 dataclass 模拟。
- DataProto smoke 必须检查 `rollout_log_probs`、`rm_scores`、`response_mask`、`non_tensor_batch` 和 `meta_info` 的 batch 维度、序列长度和 padding 规则。

阶段出口：

- canonical TrainingView fixture 转换结果稳定。
- overflow fixture 通过：超过 `response_length` 的样本不能静默截断后继续训练，必须看到明确 `status_reason`、`budget_consumption.stop_reason` 和 audit diagnostics。
- mixed log probability batch rejection fixture 通过：同一 batch 中 log probability 存在性不一致时必须被拒绝或全部标记 invalid。
- nested object 不进入 `extra_fields` 的检查通过。

## 14. Stage 11：RepoHarnessVerlAgentLoop 与 VerlLLMGateway

目标：在 Harness runtime 和训练视图稳定之后，再接入 verl。

新增 adapter 包位置：

```text
src/repo_harness_verl/
```

原则：

- RepoHarness core 不因为普通 CLI 使用而强制安装 verl 全量依赖。
- verl adapter 可以依赖 RepoHarness core 和 verl。
- RepoHarness core 只暴露 shared contract schema、runtime facade 和 gateway contract。

`RepoHarnessVerlAgentLoop.run(...)` 伪代码：

```python
async def run(self, sampling_params: dict, **kwargs) -> AgentLoopOutput:
    request = RepoHarnessEpisodeRequest.from_verl_kwargs(kwargs)
    gateway = VerlLLMGateway(
        server_manager=self.server_manager,
        tokenizer=self.tokenizer,
        processor=self.processor,
        sampling_params=sampling_params,
    )
    result = await runtime.run_episode(request, llm_gateway=gateway)
    return to_agent_loop_output(result.training_view, result.audit_ref)
```

关键约束：

1. `kwargs["raw_prompt"]` 只能包含模型可见 prompt。
2. `RepoHarnessVerlAgentLoop` 构造 request 时必须对 `kwargs` 使用 allowlist，只允许 Stage 11 明确支持的 request 构造字段和 verl 控制字段。`repo_harness_model_visible_context_refs` 第一版不启用；后续如果要启用，必须先新增 schema 投影字段、visibility 测试和 request mapping 测试。
3. `agent_name`、`task_id`、`run_config_ref`、`budget_ref`、`agent_policy_ref` 必须稳定映射到 `RepoHarnessEpisodeRequest`。
4. `VerlLLMGateway` 不启动、不停止、不重建 verl server，只调用 verl 已有 `LLMServerClient`。
5. route=verl 时，token provenance 必须来自当轮真实 `LLMServerClient.generate(...)` 返回。
6. postprocess 后自动加入的 `extra_fields.raw_prompt` 必须通过 visibility 检查。
7. adapter 必须通过 Hydra config 注册。
8. fake `LLMServerClient.generate(...)` 返回 `TokenOutput` 后必须能构造 `GenerationRecord`。
9. sticky session 使用 `LLMServerClient.generate(request_id=episode_id, ...)` 的外层 `request_id`，不要混淆 server 内部每轮生成 request id。

阶段出口：

- Mac 本地 fake `LLMServerClient` smoke 通过。
- Mac 本地小型 verl agent loop smoke 通过，不要求启动真实 vLLM / SGLang server。
- `AgentLoopOutput.extra_fields` 中的 `repo_harness_*` opaque refs 可由离线审计工具反查 RepoHarness run directory。
- adapter import 不强迫普通 RepoHarness CLI 安装完整 verl。
- `kwargs` allowlist 生效，hidden metadata、gold patch、accepted label 和 evaluator-only fields 不能进入 request、raw_prompt、TransferQueue field 或 DataProto non-tensor batch。

第一版默认决策：

- adapter 包第一版放在独立 `src/repo_harness_verl/`，并通过可选 extra 安装。RepoHarness core 不因为普通 CLI 或外部 API 测评而强制安装 verl 全量依赖。
- Vast.ai 真实训练前验收第一版以 SGLang smoke 为主，因为 verl 的 agentic / multi-turn 示例更偏 SGLang 路线；vLLM 作为第二个 parity smoke 保留。若 Vast.ai 镜像环境已经预装 vLLM 而没有 SGLang，可以临时以 vLLM 作为首个 smoke，但必须在 preflight 记录原因。

## 15. Stage 11.5：真实 RepoHarness episode runtime bridge

目标：在进入 Stage 12 端到端验收前，把前序 Stage 3 到 Stage 9 已经实现的 recorder、timing/resource、workspace、tool、verifier、reward、budget 和 resource lease 能力真正接入 `RepoHarnessRuntime.run_episode(...)` 的可执行路径。

新增这一阶段的原因是：Stage 11 完成后，verl adapter 已经可以调用 RepoHarness，但当前 `run_episode(...)` 第一版仍可能只是单轮 `minimal_gateway` facade。这个 facade 可以用于 schema、gateway、conversion 和 DataProto 结构验收，但不能代表真实软件工程 episode。Stage 12 如果要声称“端到端 smoke”，必须先有一条真实路径能完成 workspace materialization、多轮 agent loop、工具调用、final verifier 和 reward 计算。

Stage 11.5 需要固定两种 runtime-only execution mode 的语义。这里的 mode 建议命名为 `runtime_execution_mode` 或 `episode_runtime_mode`，它只属于 `RepoHarnessRuntimeOptions` 或等价 runtime-only 配置，不能和 `RepoHarnessEpisodeRequest.run_mode` 混用。`RepoHarnessEpisodeRequest.run_mode` 已经用于 `full_audit`、`training_fast` 和 `training_debug` 的记录策略。

```text
runtime_execution_mode=minimal_gateway:
  用于 contract smoke、adapter smoke、DataProto shape smoke。
  只允许证明 LLMGateway token / mask / logprob / visibility contract 正确。
  不能用于声称完整 RepoHarness episode 端到端可用。

runtime_execution_mode=real_episode:
  用于 Stage 12 前置真实 runtime smoke。
  必须进入 workspace、tool、agent loop、verifier、reward 和 artifact 路径。
```

需要接通的能力：

1. workspace runtime bridge：把 Stage 6 的 workspace snapshot、dependency cache、copy-on-write episode workspace 和 lease cleanup 接入 `run_episode(...)`。`RepoHarnessEpisodeRequest` 仍不能承载本地绝对路径；本地 resolver、snapshot manager、cache root 和执行环境配置必须留在 runtime-only options。
2. agent loop bridge：让真实 RepoHarness agent loop 可以通过 `LLMGatewayModelClientAdapter` 调用 `LLMGateway`，避免旧 provider client 绕过 gateway。多轮工具调用、tool observation、context revision、budget state 和 no-progress stop 必须保持 RepoHarness 原有语义。
3. tool/workspace bridge：工具读取、写入、搜索、测试命令和 workspace command 必须作用在当前 episode 的独立 writable workspace 上，不能污染 snapshot 或其他 episode。
4. recorder bridge：`full_audit`、`training_fast` 和 `training_debug` 的 recorder profile 必须用于真实 agent loop 产物，而不只用于最小 fake gateway 路径。
5. verifier/reward bridge：把真实 final verifier callable 从 task、workspace 和 runtime-only config 中构造出来，并通过 Stage 7 verifier worker pool 或受控 direct path 执行。reward boundary 必须使用真实 `VerifierResult`，不能用 `minimal_final_verifier_status` 占位值伪装成真实 reward。
6. timing/resource bridge：`TimingSummary` 和 `ResourceSummary` 必须能反映真实 workspace、tool、context prepare、model call、verifier、reward、artifact 和 cleanup 事实。无法获得的字段要有 diagnostics，不能用静态占位值冒充。
7. cancellation/cleanup bridge：取消、timeout、verifier timeout、workspace cleanup failure 和 run directory lock conflict 仍然遵守 Stage 2、Stage 7、Stage 9 已固定的状态和资源释放语义。
8. token provenance bridge：`real_episode` 的 `TrainingView` 不能从最终 transcript 重新分词生成。必须由每轮 `LLMGatewayResponse`、`GenerationRecord` 和工具 observation token projection 汇总得到，并保留每段 token 的来源、mask 和 log probability 策略。

阶段出口：

- `runtime_execution_mode=real_episode` 可以在本地用 fake/mock gateway 跑通至少一条极小仓库任务：真实 materialize workspace、真实执行工具、真实产生 patch 或 workspace state、真实运行 verifier、真实生成 reward、真实写入 artifact / timing / resource evidence。
- `runtime_execution_mode=minimal_gateway` 继续存在，但文档、测试和报告必须明确它只覆盖 contract / adapter / DataProto 结构，不覆盖完整软件工程任务闭环。
- `ResourceSummary` 能反查 snapshot key、workspace lease、cleanup status 和可公开的 workspace reference；不能泄漏本地绝对路径。
- `TimingSummary` 至少能区分 model、tool、workspace、verifier、reward、artifact、cleanup 和 queue wait 的主要分桶；如果某个分桶为 0，必须是因为该 episode 确实没有执行对应动作。
- `TrainingView.response_spans` 能解释多轮 agent loop 中 assistant generation 和 tool observation 的 token 来源；工具 observation token 的 mask / log probability 规则继续遵守 Stage 0H contract。

边界：

- Stage 11.5 不启动真实 Ray、SGLang、vLLM 或 PPO / GRPO trainer；这些仍属于 Stage 12。
- Stage 11.5 不要求 warm container pool 或分布式资源租约；它先证明真实 episode runtime bridge 的正确性。
- Stage 11.5 不把 `minimal_gateway` 删除。它仍用于快速结构测试，但不能作为端到端训练可用性的证据。

## 16. Stage 12：端到端 smoke、性能 smoke 和 visibility 验收

目标：确认整条链路可以训练消费，而不是只在局部测试通过。

端到端 smoke：

```text
verl dataloader sample
  -> RepoHarnessVerlAgentLoop.run(...)
  -> RepoHarnessRuntime.run_episode(...)
  -> real_episode runtime bridge
  -> workspace / tool / RepoHarness agent loop
  -> VerlLLMGateway
  -> LLMServerClient.generate(...)
  -> TokenOutput
  -> agent loop continues or stops
  -> final verifier
  -> reward_score
  -> TrainingView
  -> AgentLoopOutput
  -> verl postprocess
  -> DataProto
```

这里的 `LLMServerClient.generate(...)` 表示 agent loop 中的一轮或多轮模型调用。真实 episode 可能经历多次模型生成、工具调用和工具 observation，再在 agent loop 结束后执行 final verifier 和 reward boundary；不要把它理解成一次生成后立刻完成整条软件工程任务。

必须验收：

- `prompt_ids` 非空。
- `response_ids` 非空，或有明确终止原因。
- `response_mask` 长度正确。
- `reward_score` 可用，或 episode 明确 invalid。
- `extra_fields` 中的 `repo_harness_*` opaque refs 可由离线审计工具反查 run directory；不能直接暴露模型工具可读的本地绝对路径。
- postprocess 后 `extra_fields.raw_prompt` 通过 visibility 检查。
- 普通 `AgentLoopWorker._agent_loop_postprocess(...)` 路径和 `main_ppo_sync.py` / TransferQueue 路径都通过 visibility test。
- DataProto 的 tensor batch、non-tensor batch 和 meta_info 都通过字段 visibility 和 batch dimension 检查。
- invalid 样本不会进入有效 PPO / GRPO loss；如果选择置零 loss weight 而不是丢弃，必须在 tensor / metrics 中显式可见。
- `TimingSummary` 可以拆分 model、tool、workspace、verifier、artifact 时间。
- `ResourceSummary` 可以反查 snapshot key、container lease、workspace id。
- `training_fast` artifact 体积小于同等 `full_audit`，但审计引用完整。
- workspace 隔离验收必须覆盖至少两个 episode 复用同一个 snapshot key 并发运行，确认 workspace、patch、artifact manifest、lease cleanup 和 run directory 不互相污染。

Stage 12 的验收必须分层。Mac 本地通过只表示本地真实 runtime bridge 和 adapter contract 正确；GPU / Vast.ai 或同类环境通过，才表示真实训练前链路可用。

性能 smoke 不要求第一版达到大规模训练吞吐，但必须证明后续可以定位瓶颈：

```text
每条 episode 都有 timing_summary.json
每条 episode 都有 resource_summary.json
summary 中能看到 model/tool/workspace/verifier/artifact 拆分
training_fast artifact 体积有明显下降
```

Stage 12 还必须显式记录资源关系：

```text
Ray placement
CPU worker
GPU server
workspace worker
verifier worker pool
artifact writer
```

### Stage 12-A：Mac 本地真实 runtime bridge smoke

Mac 本地开发阶段使用 `verl-lite` 或 reference stubs 验收，不要求安装 vLLM、SGLang、flash-attn、liger-kernel 或 CUDA 相关依赖。它的目标不是验证真实 GPU 推理吞吐，而是证明 Stage 11.5 的 `real_episode` runtime bridge 能跑真实 RepoHarness episode。

Mac 本地必须通过：

```text
RepoHarnessRuntime.run_episode(...)
  -> fake/mock LLMGateway
  -> real_episode runtime bridge
  -> workspace snapshot / lease
  -> RepoHarness agent loop
  -> tool execution
  -> final verifier
  -> reward boundary
  -> RepoHarnessEpisodeResult / TrainingView
  -> extra_fields / AuditRef / raw_prompt visibility 检查
```

这条 fake/mock LLMGateway 路径只用于 debug / diagnostic runtime smoke。`mock` route 不能进入 formal online RL converter，也不能作为正式 PPO / GRPO 样本可训练性的证据。

以及：

```text
RepoHarnessVerlAgentLoop.run(...)
  -> RepoHarnessRuntime.run_episode(...)
  -> real_episode runtime bridge
  -> RepoHarness agent loop
  -> VerlLLMGateway
  -> fake LLMServerClient.generate(...)
  -> fake TokenOutput
  -> route=verl 的 token facts / GenerationRecord
  -> tool / workspace / verifier / reward
  -> AgentLoopOutput
  -> response_ids / response_mask / response_logprobs 长度检查
```

如果要验证 formal online RL converter，必须走 `RepoHarnessVerlAgentLoop + fake LLMServerClient` 这条路径，并由 adapter 产生 `route=verl` 的 token、mask 和 log probability 事实。

Mac 本地验收边界：

- 可以安装 verl 基础包或使用 `pip install --no-deps -e reference/verl` 加必要最小依赖。
- 不要求启动真实 vLLM / SGLang server。
- 不要求跑真实 PPO / GRPO trainer。
- 不要求验证真实 Ray GPU resource scheduling。
- 允许使用 fake logprobs 做长度和 mask 对齐测试，但这只能算 debug smoke。
- 允许使用 fake server、fake `TokenOutput` 或 reference stubs 降低本地依赖成本，但不能伪造 `AgentLoopOutput.as_dict()`、verl postprocess、TransferQueue 或 DataProto visibility 这类核心转换逻辑。
- 必须真实执行 workspace、tool、verifier 和 reward 路径，不能再只用 `minimal_gateway` facade 冒充端到端。

### Stage 12-B：GPU / Vast.ai 真实模型端到端 smoke

Vast.ai 或其他 Linux GPU 实例负责真实训练前验收。它的目标是证明 route=verl 在真实推理服务、真实模型、真实极小仓库任务、verl postprocess 和 DataProto 组装路径下可用。真正进入 PPO / GRPO trainer loss 路径的验收放到 Stage 12-C，避免把真实模型 episode smoke 和 trainer batch smoke 混在一起。

第一轮真实模型建议从较小的代码模型开始，例如 `Qwen2.5-Coder-7B-Instruct` 或同等级别的 instruct code model。这个选择用于调试链路，不代表最终训练模型固定。首批任务建议使用极小仓库任务，而不是直接上 SWE-Bench 或大型真实仓库。现有或可同步的候选目录是：

```text
/Users/roger/Desktop/claude-code/tests/fixtures/repos
```

首批任务池可以优先选择：

```text
buggy_calculator
import_config_bug
missing_helper_file
```

随后再加入边界任务：

```text
baseline_invalid
flaky_counter
security_probe
```

这些任务用于分别覆盖正常修复、invalid task、flaky verifier 和 evaluator-only / visibility 边界。最终具体任务格式和 fixture freeze 规则由 Stage 12 执行计划单独定义。

如果这些任务来自另一个 worktree，最终验收前必须同步或冻结到当前 RepoHarness 可审计的位置，不能让 Stage 12 依赖另一个工作区中的可变路径。

Vast.ai 训练前必须通过：

```text
verl dataloader sample
  -> RepoHarnessVerlAgentLoop.run(...)
  -> RepoHarnessRuntime.run_episode(...)
  -> real_episode runtime bridge
  -> RepoHarness agent loop
  -> VerlLLMGateway
  -> verl server manager
  -> vLLM / SGLang AsyncLLMServer
  -> real LLMServerClient.generate(...)
  -> real TokenOutput.token_ids / log_probs
  -> agent loop continues or stops
  -> final verifier
  -> reward boundary
  -> TrainingView
  -> AgentLoopOutput
  -> verl postprocess
  -> DataProto
  -> DataProto shape / visibility / logprob provenance smoke
```

Vast.ai 真实验收必须检查：

- tokenizer / processor / chat template 与训练模型一致。
- `response_ids` 来自真实生成路径，不从最终 transcript 重新分词伪造。
- `response_logprobs` 非空，并与 `response_ids`、`response_mask` 长度对齐。
- `rollout_log_probs` 出现在 DataProto tensor batch 中，形状等于 `[batch_size, rollout.response_length]`。
- `rm_scores` 存在，或者样本被明确过滤；invalid 样本不能悄悄参与 policy loss。
- sticky session / prefix cache 的 `request_id` 语义正确。
- Ray actor、server manager、LLM server、RepoHarness workspace worker 可以在同一台或多台 GPU 实例上并发运行。
- workspace snapshot backend 在 Linux 文件系统上通过 preflight；支持 `cp --reflink=auto`、overlayfs、Docker volume snapshot 或安全回退到目录复制。
- `training_fast` artifact 体积下降，但 `AuditRef` 可以回查 run directory、transcript、events、patch、reward 和 timing/resource summary。
- `TimingSummary` 能看到 model/tool/workspace/verifier/artifact 拆分。
- `ResourceSummary` 能看到 inference route、container lease、snapshot key、cache hit 和 verifier worker pool。
- SGLang 真实 smoke 和 vLLM contract smoke 同阶段完成，允许一个作为主验收、另一个作为 parity smoke；如果 Vast.ai 镜像条件只支持其中一个，必须在 preflight 中记录原因和补齐计划。

Stage 12-B 的结果判定必须把“基础设施链路是否跑通”和“模型是否成功修复任务”分开。极小任务中应至少包含一个极易成功的正例任务，但模型单次没有修复任务时应记为模型失败样本或 rejected episode，不能误判为基础设施失败。

如果 Stage 12-B 使用从其他 worktree 同步来的极小仓库任务，正式验收必须生成 fixture manifest 和 sha256 report，确保真实 smoke 使用的任务输入可复查、可复现。

### Stage 12-C：小 batch trainer smoke

Stage 12-B 证明单条或少量真实模型 episode 可用后，Stage 12-C 再验证小 batch 可以进入 PPO / GRPO trainer 的关键路径。这个 smoke 不要求模型收敛，不要求产出有统计意义的训练结果，只要求 batch 语义正确、invalid 样本处理明确、loss 输入形状和 log probability 来源正确。

需要确认：

- `DataProto.batch` 中 `prompts`、`responses`、`response_mask`、`rollout_log_probs` 和 `rm_scores` 的形状符合当前 verl trainer 要求。
- `DataProto.non_tensor_batch` 和 `meta_info` 通过 visibility 检查。
- PPO / GRPO smoke 必须记录 `actor_rollout_ref.rollout.calculate_log_probs=True` 或当前 verl 版本等价配置。
- 进入 trainer 前必须显式运行 formal batch validator：所有 valid 样本必须 `route=verl`、`response_logprobs` 非空、`generation_records` 全部来自 `verl` route；invalid 样本过滤、重采样或置零 loss weight 的策略必须可审计。
- invalid、timeout、infrastructure error、no-progress 和缺失 log probability 的样本不会悄悄进入有效 policy loss。
- 若采用丢弃样本、重采样或置零 loss weight，必须在 metrics 和 audit evidence 中可见。

因此，Mac 本地验收通过只表示“本地真实 runtime bridge 和 adapter contract 正确”；GPU / Vast.ai 真实模型与小 batch trainer smoke 通过后，才表示“真实训练前可用”。

## 17. Stage 12.5：同步高吞吐基线加固

目标：在 Stage 12 已经证明真实 episode、真实模型和小 batch trainer smoke 可用之后，先补齐训练吞吐所需的缓存、并发、热路径和 profile 能力，再进入 Stage 13 的 fully async 设计。

新增这一阶段的原因是：Stage 12 的验收重点是“链路能跑通、训练 batch 语义正确、visibility 安全”，不是“训练吞吐已经适合更大规模 rollout”。如果直接进入 Stage 13，会把依赖安装、workspace 物化、artifact 写入、verifier 执行和 trainer 配置这些同步瓶颈带进 fully async 设计里，后续很难区分是异步架构问题，还是底层训练热路径本身没有加速。

Stage 12.5 必须保持下面边界：

- 不重写完整 async AgentLoop；episode interrupt、resume、async reward backfill 和跨参数版本 trajectory 处理仍属于 Stage 13。
- 不放松 Stage 0H 到 Stage 11.5 固定的正式训练安全约束。正式 PPO / GRPO 样本仍然必须来自 `route=verl`，必须有 `response_logprobs`，并通过 visibility gate。
- 不把依赖环境真实路径、workspace 真实路径、run directory、setup log、secret、reward metadata 明文放进 `TrainingView.extra_fields`、`AgentLoopOutput.extra_fields`、DataProto non-tensor batch 或 meta_info。
- 不把共享 dependency environment 当作 episode 可写目录。episode 可以通过 `PATH`、`VIRTUAL_ENV`、`PYTHONPATH` 使用共享环境，但不能在共享环境里执行会污染后续样本的安装命令。
- 不把大型 SWE-Bench 正式训练作为本阶段目标。本阶段使用极小仓库任务、小任务池和远端吞吐 profile 证明机制有效。

### Stage 12.5-A：依赖环境缓存

当前 `real_episode` 路径已经有源码 snapshot 和 workspace lease，但没有真正的 dependency environment cache。Stage 12.5 必须新增训练可复用的依赖环境层，建议命名为 `DependencyEnvironmentManager` 或等价 runtime-only manager。

推荐分层：

```text
source snapshot
  只保存干净源码树和 source facts

dependency environment cache
  保存已经准备好的第三方依赖环境，例如 Python virtualenv、uv environment 或容器 layer

episode workspace lease
  每条 episode 从 source snapshot 派生可写 workspace，通过环境变量使用 dependency environment
```

dependency environment key 第一版必须拆成三类，避免源码小改动导致纯第三方依赖环境不必要失效：

```text
base_environment_key
  描述纯第三方依赖环境

overlay_environment_key
  描述仓库相关 setup overlay

source_snapshot_key
  描述源码快照身份
```

`base_environment_key` 至少应该包含：

- Python 版本、平台和 CPU 架构。
- 操作系统发行版、glibc 或 musl 版本。
- CUDA、torch、compiler ABI 或 Docker image digest。
- 本地执行模式，例如 `local_process`、`docker` 或 `remote_worker`。Docker 模式下必须包含 image digest。
- pip、uv、npm、pnpm 等包管理器版本。
- dependency lock hash，例如 `uv.lock`、`requirements.txt`、`pyproject.toml`、`package-lock.json`、`pnpm-lock.yaml` 或任务显式声明的依赖锁。
- package index URL 的非 secret 摘要。不得把 token、账号、私有 registry secret 写入 key 或 facts。
- 影响依赖解析的 environment allowlist 摘要，例如 `PIP_INDEX_URL` 是否存在、`UV_INDEX_URL` 是否存在、Node / Python 版本选择，但只记录去敏摘要。
- RepoHarness dependency environment schema version。

`overlay_environment_key` 至少应该包含：

- setup command hash。
- overlay strategy，例如 none、PYTHONPATH-only、copy-declared-paths 或后续 overlay venv。
- 与仓库相关但不应该进入 base environment 的 setup facts。

setup command 的归属必须按实际语义拆分：如果 setup command 只是安装第三方依赖，可以进入 `base_environment_key`；如果 setup command 绑定当前源码路径、执行 editable install、生成仓库本地构建产物，或者写入 episode workspace 相关路径，则必须进入 `overlay_environment_key` 或 `source_snapshot_key` 的 facts，不能污染 base environment。

`source_snapshot_key` 至少应该包含：

- source tree hash 或 source archive sha256。
- base commit、dataset task revision 或等价 source identity。

实现要求：

- 使用本地 lock、临时目录写入、facts 文件校验后原子发布。
- cache hit 时必须读取并校验 facts，不能覆盖已有环境。
- 环境发布后默认只读；如果平台无法可靠只读，必须记录 diagnostics，并禁止 episode 在共享环境中执行安装命令。
- 命令执行层必须禁止 episode 对共享 environment 执行安装、卸载或写入操作。如果只靠文件权限无法可靠保护，必须通过 command policy、wrapper 或等价机制拦截 `pip install`、`uv pip install`、`npm install`、`pnpm install` 等会写入共享 environment 的命令。
- 不允许默认在共享环境中执行 `pip install -e <episode_workspace>`，因为 editable install 会把某条 episode 的 workspace 路径写入共享环境。当前仓库源码优先通过 `PYTHONPATH=<episode_workspace>` 暴露给工具和 verifier。
- 如果确实需要 editable install，只能作为后续 overlay environment 方案，不能混入 Stage 12.5 第一版默认路径。
- 建议把依赖环境拆成“纯第三方依赖 base environment”和“仓库相关 setup overlay”。第一版可以只实现 base environment，但计划和 facts schema 必须预留 overlay 字段，避免把某个 episode workspace 的路径写入全局共享环境。
- `LocalWorkspaceAdapter`、Docker workspace 或 runtime command environment 必须能注入 `VIRTUAL_ENV`、`PATH=<env>/bin:$PATH`、`PYTHONNOUSERSITE=1` 和 `PYTHONPATH=<episode_workspace>`。
- `TimingSummary` 必须记录 environment prepare / dependency restore 时间。
- `ResourceSummary` 只能记录 opaque ref，例如 `repo_harness_environment_ref=rh://environment/<env_key>`、`dependency_cache_hit` 和 `dependency_cache_key`，不能记录本机绝对路径。

### Stage 12.5-B：共享 workspace cache 和快速物化

当前 Stage 12 证明了 workspace snapshot / lease 的正确性，但训练吞吐需要跨 episode 共享 cache，并减少每条 episode 的目录复制成本。

需要完成：

- 训练入口必须支持显式传入共享 `WorkspaceSnapshotManager` 或共享 cache root。默认训练 helper 不应让每条 episode 在自己的 run directory 下创建独立 snapshot cache。
- `RepoHarnessVerlAgentLoop` 或 Stage 12.5 runtime helper 必须把共享 cache root 作为 runtime-only 配置传入，不能让它进入 request schema 或 batch 字段。
- snapshot key 必须绑定 source identity、dependency lock facts、setup command facts 和 environment identity；不能只写固定 `environment_id="local_process"`。
- `WorkspaceSnapshotManager.acquire_workspace(...)` 保留安全的 directory copy 基线，同时增加可配置快速物化策略，例如 hardlink copy、reflink、`rsync --link-dest`、Git worktree 或 overlay workspace。
- hardlink copy 只能作为显式 opt-in 策略，必须有只读 snapshot、写前断链或等价保护，不能让 episode 写入通过硬链接污染 snapshot 或其他 lease。
- 快速物化策略必须保留 Stage 6 已固定的 symlink 越界检查、敏感路径拒绝、lease cleanup、snapshot / lease 一致性检查和路径不可见性检查。
- 写隔离验收必须覆盖：episode 修改 hardlink 文件后 snapshot 内容不变，另一个 lease 中同一路径内容不变，symlink 越界仍被拒绝，敏感文件仍被拒绝，cleanup 失败会产生 orphan diagnostics。
- 如果实现 Git worktree 策略，必须证明 `.git` metadata、共享分支状态、index lock 和未提交修改不会在不同 episode 之间串扰。
- 冷缓存和热缓存都必须输出 resource facts：`snapshot_cache_hit`、`source_tree_hash`、`workspace_lease_id`、`workspace_materialization_seconds` 和 cleanup status。

### Stage 12.5-C：verifier、recorder 和工具热路径

Stage 12.5 不要求重写工具系统，但必须降低最明显的同步固定成本。

verifier 要求：

- 真实训练 runtime helper 默认使用有界 `VerifierWorkerPool`，不能让每条 episode 无控制地直接同步跑 final verifier。
- verifier pool 必须记录 `pool_id`、`worker_id`、queue wait、execution seconds、timeout、error type 和 release status。
- pytest 类 verifier 应优先避免重复执行“完整测试命令 + 每个声明测试再单独执行”的固定模式。第一版可以保留安全回退，但必须记录是否发生补跑。
- verifier timeout 后底层同步线程不可强杀的风险必须继续体现在 diagnostics 中，不能把超时样本伪装成普通 rejected sample。

recorder 和 artifact 要求：

- 在 `training_fast` 基础上新增 `training_hot` recorder 子配置，或者把 training path 下的 artifact manifest 写入改成批量 flush / finalize 机制，避免每个 artifact 都完整读写 manifest。`training_hot` 不是新的 `RepoHarnessEpisodeRequest.run_mode`，第一版 `run_mode` 仍只使用 `full_audit`、`training_fast` 和 `training_debug`。`training_hot` 只能是 `RecorderProfile` 或 runtime-only recorder variant，不能进入 request schema，也不能成为 `TrainingView`、`AgentLoopOutput` 或 DataProto batch 字段。
- 命令输出 artifact 在 hot path 下默认保存投影、截断或合并输出；完整 stdout / stderr 可通过 debug profile 或抽样审计保留。
- 必须保留 final patch、final verifier、reward boundary、timing summary、resource summary、training view 和 opaque audit refs。
- 不能因为减少 artifact 就破坏 Stage 0H visibility 和 audit ref 规则。
- recorder hot path 必须记录 manifest 写放大指标：`manifest_rewrite_count_per_episode`、`manifest_bytes_written_per_episode`、`artifact_write_seconds_p50`、`artifact_write_seconds_p95`、`artifact_count_per_episode` 和 `artifact_bytes_per_episode`。

工具路径要求：

- Stage 12.5 第一版可以不做同一轮 tool call 并行执行，但必须记录 tool execution seconds，避免工具耗时继续全部混入 `agent_loop_seconds`。
- tool timing 必须从 `events.jsonl`、tool execution facts 或等价结构化事件汇总，不能继续用固定 `0.0` 占位。
- 对高频只读工具和 `git_diff` 等多命令工具，应记录命令数量和 artifact 数量，为后续优化提供依据。

### Stage 12.5-D：训练侧吞吐 profile 和有效样本补齐

Stage 12 的 trainer smoke 可以使用保守配置证明正确性；Stage 12.5 必须新增吞吐 profile，证明系统知道如何把资源用起来，并能定位瓶颈。

吞吐 profile 至少包含：

- correctness smoke：保持小 batch、低并发，验证语义和 visibility。
- cold cache profile：第一次准备 dependency environment 和 source snapshot。
- warm cache profile：复用 dependency environment 和 source snapshot，验证 setup 不再每条 episode 重做。
- concurrent episode profile：至少 2 到 4 条真实极小仓库 episode 并发运行，验证 workspace lease、run directory、artifact manifest、route limiter、verifier pool 和 cleanup 不互相污染。
- trainer profile：提高 `agent.num_workers`、`train_batch_size`、`max_num_seqs`、`max_num_batched_tokens` 和 `gpu_memory_utilization` 到适合小模型 smoke 的值，并记录 Ray、SGLang / vLLM、RepoHarness runtime 和 GPU 侧指标。

吞吐 profile 至少固定下面这些指标名称，便于不同远端运行之间比较：

- `valid_samples_per_minute`
- `rollout_tokens_per_second`
- `model_call_seconds_p50` / `model_call_seconds_p95`
- `workspace_materialization_seconds_p50` / `workspace_materialization_seconds_p95`
- `dependency_restore_seconds_p50` / `dependency_restore_seconds_p95`
- `verifier_queue_wait_seconds_p50` / `verifier_queue_wait_seconds_p95`
- `artifact_bytes_per_episode`
- `artifact_count_per_episode`
- `warm_cache_hit_rate`
- `manifest_rewrite_count_per_episode`
- `manifest_bytes_written_per_episode`
- `prompt_build_seconds_p50` / `prompt_build_seconds_p95`
- `chat_template_seconds_p50` / `chat_template_seconds_p95`
- `tokenize_seconds_p50` / `tokenize_seconds_p95`
- `padded_token_ratio`
- `loss_mask_token_ratio`

有效样本补齐要求：

- 训练侧必须区分 infrastructure failure、invalid task、model format failure、verifier rejected 和 valid trainable sample。
- refill / resample 第一版默认由 RepoHarness batch collector 或 Stage 12.5 trainer helper 负责，verl sampler 只消费已经通过 formal batch validator 的样本。如果后续改由 verl sampler 负责，必须先另写 request / response contract。
- refill policy 必须明确目标 valid sample 数、最大 attempt 数、最大 wall time、任务采样去重规则、是否允许同一 task 多次重采样，以及 insufficient valid batch 时的结构化失败字段。
- 如果正式 batch 需要固定数量 valid samples，必须有可审计的 refill / resample 策略：继续收集直到达到 valid sample 数量，或达到 attempt / time budget 后结构化失败。
- invalid 样本可以进入 audit evidence 和诊断统计，但不能悄悄进入有效 policy loss。
- valid sample rate、invalid reason distribution、refill attempts 和 insufficient valid batch reason 必须进入 Stage 12.5 汇总报告。

log probability 和 batch padding 要求：

- Stage 12.5 不能为了吞吐关闭正式 online RL 所需的 rollout log probability provenance。
- 如果尝试使用 verl 的 rollout correction bypass、actor old logprob 复用或等价配置，必须先写清 contract 影响，并确认不会破坏 `response_ids`、`response_mask`、`response_logprobs` 的 Stage 0H 不变量。
- Stage 12.5 可以先缩短极小任务 smoke 的 `prompt_length` 和 `response_length`，并记录真实 token 长度分布；更深的 padding-free batch 改造不作为本阶段默认目标。
- DataProto padding profile 必须记录 `actual_prompt_tokens_p50`、`actual_prompt_tokens_p95`、`actual_response_tokens_p50`、`actual_response_tokens_p95`、`padded_token_ratio`、`loss_mask_token_ratio`、`response_mask_zero_ratio` 和 `length_overflow_filtered_sample_count`。
- 如果启用 `use_remove_padding` 或当前 verl 版本等价配置，必须重新验证 Stage 0H 的 token、mask、log probability 长度不变量和 visibility 检查。

### Stage 12.5-E：推理服务、tokenization、Ray worker 和系统资源 profile

Stage 12.5 必须把同步高吞吐基线观测补齐，不能只看 RepoHarness 自己的 workspace 和 verifier。这个小节专门覆盖真实训练时常见的非模型代码瓶颈、推理服务瓶颈和系统资源瓶颈。

推理服务 profile 必须记录：

- `inference_server_queue_wait_seconds_p50` / `inference_server_queue_wait_seconds_p95`
- `prefill_seconds_p50` / `prefill_seconds_p95`
- `decode_seconds_p50` / `decode_seconds_p95`
- `prefix_cache_hit_rate`
- `kv_cache_eviction_count`
- `num_preempted`
- `tokens_per_second`
- `gpu_utilization_p50` / `gpu_utilization_p95`
- `batched_token_count_p50` / `batched_token_count_p95`

SGLang / vLLM 指标映射要求：

- Stage 12.5 详细执行计划必须列出当前 SGLang 和 vLLM 版本中这些指标的来源字段、日志字段或 API 字段。
- 如果某个后端版本无法提供某项指标，不能静默填 `0`；必须写入 unsupported diagnostics，例如 `prefix_cache_hit_rate_unavailable`、`kv_cache_eviction_metric_unavailable` 或 `num_preempted_metric_unavailable`。
- 不同后端的指标口径必须在 `inference_server_profile.json` 中记录，避免把 SGLang 和 vLLM 的不同统计口径直接混算。

sticky session / prefix cache 要求：

- 必须验证 `sticky_session_id=episode_id` 或当前 adapter 等价字段是否真的传到 SGLang / vLLM 请求路径。
- 多轮 agent episode 必须记录 prefix cache 命中率或后端无法提供该指标的 diagnostics。
- 如果 prefix cache 没有命中，必须能区分是后端不支持、request id 不稳定、chat template 变化、prompt prefix 不稳定，还是 cache 被 eviction。

tokenizer 和 chat template 要求：

- 必须记录 prompt build、chat template、tokenize 的 p50 / p95 时间。
- 必须记录 prompt token length distribution。
- 必须评估 system prompt、tool schema、task prompt 等稳定前缀 token 的缓存可能性；第一版可以只做 profile，不要求实现 prefix token cache。
- 如果后续实现 prefix token cache，必须证明不会改变模型可见 prompt 内容，也不会绕过 `raw_prompt` visibility 检查。

Ray worker 和本地线程池要求：

- Stage 12.5 详细执行计划必须明确每个 Ray worker 内 `RepoHarnessRuntime` 是单例复用，还是每条 episode 新建。
- 必须明确 `WorkspaceSnapshotManager`、`DependencyEnvironmentManager`、`VerifierWorkerPool`、`ResourceLeaseManager` 和 route limiter 在 Ray worker 内如何共享，以及跨 worker 是否共享。
- 必须记录 `active_agent_loop_threads`、`agent_loop_worker_queue_wait_seconds_p50`、`agent_loop_worker_queue_wait_seconds_p95`、Ray actor CPU 使用率和本地线程池队列等待。
- `RepoHarnessRuntimeOptions.executor_max_workers` 如果继续存在，必须真正约束 `real_episode` worker thread pool；如果不能约束默认 executor，必须在 Stage 12.5 修正命名或实现，避免给训练调参造成假信号。

系统资源 profile 必须记录：

- 文件描述符数量。
- 磁盘读写字节数。
- run directory 文件数量。
- cleanup orphan 数量和 orphan diagnostics。
- workspace cleanup seconds。
- verifier subprocess count。

### Stage 12.5-F：验收标准

Stage 12.5 本地实现完成时必须有本地 evidence。远端 GPU evidence 由 Stage 12.6 作为单独的提交后回归 gate 生成；本小节中的远端清单保留为 Stage 12.6 具体执行计划必须覆盖的 evidence envelope，避免 Stage 12.5 本地实现和远端真实训练 smoke 混在同一次提交里。

本地必须通过：

- dependency environment key、facts、atomic publish、cache hit / miss、只读语义和路径不可见性测试。
- command environment 注入测试，证明工具和 verifier 使用 dependency environment，而不是隐式使用当前进程 Python。
- workspace shared cache root、snapshot hit、lease fast materialization、安全回退、symlink 越界和 cleanup 测试。
- verifier worker pool 默认接入测试。
- recorder hot path 的 artifact 数量、artifact bytes 或 manifest 写入次数下降测试。
- tool timing 从结构化事件汇总的测试。
- DataProto padding profile 和 `use_remove_padding` 等价配置下的不变量回归测试。
- Ray worker / runtime manager 共享边界测试，至少证明单 worker 内 snapshot manager、dependency manager 和 verifier pool 可以复用。
- Stage 0H 到 Stage 12 的关键回归，尤其是 visibility、formal batch validator、real_episode runtime bridge、Stage 12-A 本地 smoke。
- Stage 12.5 详细执行计划必须同步更新 shared acceptance contract 或新增 Stage 12.5 专用 acceptance contract，避免阶段 gate 仍停留在 Stage 12 直接进入 Stage 13 的旧表述。

Stage 12.6 远端回归 smoke 至少生成或等价覆盖：

```text
runs/stage12_6-remote-<timestamp>/
  stage12_6_preflight.json
  stage12_6_command_log.sanitized.jsonl
  runtime_private/stage12_6_command_log.raw.jsonl
  git_state_before_after.json
  environment_cache_report.json
  workspace_cache_report.json
  concurrent_episode_report.json
  command_policy_and_runtime_visibility_report.json
  trainer_throughput_profile.json
  verifier_recorder_tool_hot_path_report.json
  batch_refill_resample_report.json
  dataproto_padding_profile.json
  evidence_path_leak_scan_report.json
  real_episode_task_pool_report.json
  formal_batch_and_refill_report.json
  dataproto_and_trainer_smoke_report.json
  inference_server_profile.json
  tokenization_profile.json
  ray_worker_resource_profile.json
  system_resource_profile.json
  visibility_and_batch_validation_report.json
  stage12_6_acceptance_summary.json
```

Stage 12.6 具体执行计划可以把同类报告合并成更少文件，但必须在 `stage12_6_acceptance_summary.json` 中列出“canonical evidence item -> 实际文件路径”的映射。不能因为文件名合并而丢失 `concurrent_episode_report`、`trainer_throughput_profile`、`verifier_recorder_tool_hot_path_report`、`batch_refill_resample_report`、`dataproto_padding_profile`、`tokenization_profile` 或 `visibility_and_batch_validation_report` 对应内容。

Stage 12.6 远端验收至少证明：

- cold cache 会创建 dependency environment，warm cache 会命中同一个 environment key。
- warm run 中每条 episode 不再重复执行完整 dependency setup。
- 远端任务池至少包含三类极小真实仓库任务：无外部依赖的基线任务、带第三方 Python 依赖的任务、需要从当前 episode workspace 源码 import 的任务。这样才能同时验证 dependency environment cache、workspace source import 和共享环境不被 episode 污染。
- 多条并发 real episode 复用 snapshot / environment，但 workspace、patch、artifact manifest、run directory 和 cleanup 相互隔离。
- `TrainingView`、`AgentLoopOutput`、DataProto non-tensor batch 和 meta_info 中没有本机绝对 environment path 或 workspace path。
- full trainer 小步 profile 至少完成一个 global step，并记录有效样本数量、invalid 样本过滤、GPU / Ray / SGLang 或 vLLM 指标。
- 推理服务 profile 能区分 queue wait、prefill、decode、prefix cache、KV cache eviction、preemption 和 tokens per second。
- tokenizer profile 能解释 prompt build、chat template 和 tokenize 的 CPU 耗时。
- Ray worker profile 能解释 runtime manager 复用、agent loop thread 数、queue wait 和 CPU 占用。
- DataProto profile 能解释 actual token length、padding ratio、loss mask ratio 和 overflow filtered sample count。
- `TimingSummary` 能解释 setup、snapshot、dependency restore、model、tool、verifier、artifact 和 cleanup 的主要耗时。

Stage 12.5 本地实现和本地回归完成后，还不能直接进入 Stage 13 fully async。必须先完成 Stage 12.6 的远端 RL 链路回归 smoke；否则 Stage 13 必须先声明它只是异步接口预研，不能声称已经建立高吞吐 agentic RL infra。

## 18. Stage 12.6：Stage 12.5 修改后远端 RL 链路回归 smoke

目标：在 Stage 12.5 提交后，使用远端 GPU 环境重新验证当前代码提交下的完整 RepoHarness + verl 训练链路。这个阶段不是新增大规模训练，也不是提前进入 fully async；它是 Stage 13 前的远端回归 gate，用来证明 Stage 12.5 对共享依赖环境、命令策略、隐藏 runtime 目录、formal batch validator 和 batch refill 的修改没有破坏真实在线强化学习路径。

新增这一阶段的原因：

- Stage 12.5 修改了 `real_episode` 的 workspace / dependency environment 准备方式，本地测试可以证明路径不可见性和缓存语义，但不能证明远端训练脚本、Ray worker、推理服务和真实任务命令都能顺利使用这些环境。
- Stage 12.5 收紧了共享环境下的模型命令策略，例如拦截安装命令、环境探测命令、Python 脚本执行和高风险 `python -c` 诊断。本地测试能覆盖规则，但远端 smoke 必须确认真实模型任务不会因为策略过严而变成基础设施失败；如果模型被拦截，应明确分类为 command policy blocked 或 model behavior failure，而不是 verifier / trainer infrastructure failure。
- Stage 12.5 强化了 formal batch validator 和 batch refill，必须在真实 `RepoHarnessVerlAgentLoop -> RepoHarnessRuntime(real_episode) -> VerlLLMGateway -> LLMServerClient -> TrainingView -> AgentLoopOutput -> DataProto -> trainer` 路径中再次验证。
- Stage 12.5 增加隐藏 runtime 目录和输出脱敏，必须确认 `TrainingView.extra_fields`、`AgentLoopOutput.extra_fields`、DataProto non-tensor batch、meta_info、模型可见 tool 输出和命令 artifact 中都没有本机绝对 environment path、workspace path、run directory 或 `.repo_harness_runtime` / `.repo_harness_env_overlay` 明文泄漏。

环境建议：

- 使用新租用的 `2 * RTX PRO 6000` Vast.ai 实例，并参考此前已经验证过的硬件和配置。不能假设 Stage 12-B/C 旧实例上的模型缓存、Ray 状态、workspace、环境变量或进程仍然存在。
- 如果新实例不是 `2 * RTX PRO 6000`，也可以使用等价 GPU 环境，但必须在 preflight 中记录 GPU 型号、驱动、CUDA、Python、torch、Ray、verl、SGLang / vLLM、transformers、tokenizer / chat template 来源、Docker / container image id 或 digest、RepoHarness commit 和 reference/verl commit。
- 第一版仍建议使用 `Qwen2.5-Coder-7B-Instruct` 或同等级别小型 code instruct model，避免把大模型吞吐调参和 Stage 12.5 回归验证混在一起。

实施边界：

- 不要求模型收敛，不要求训练出有统计意义的 checkpoint。
- 不扩大到大型 SWE-Bench 正式训练。
- 不关闭 log probability、formal batch validator、visibility gate、verifier、reward boundary 或 artifact evidence 来制造通过结果。
- 不因为模型没有修复任务就判定基础设施失败。模型格式错误、工具调用错误、verifier rejected 和真实 infrastructure error 必须分开统计。
- 不在远端 smoke 中顺手修改 contract 或绕过 Stage 12.5 的保守命令策略。如果发现策略过严，应记录为 follow-up 设计问题，除非它阻断所有真实任务 smoke。

远端 smoke 至少覆盖：

- cold cache run：创建 dependency environment、source snapshot 和 workspace lease，记录 environment key、snapshot key、cache miss、dependency restore seconds 和 workspace materialization seconds。
- warm cache run：复用同一个 dependency environment key 和 source snapshot key，证明每条 episode 不再重复完整 setup。
- 真实任务池必须至少包含三类任务：无外部依赖基线任务、带第三方 Python 依赖的极小任务、需要从当前 episode workspace 源码 import 的任务。任务输入必须固定到 fixture 或 run artifact，并生成 manifest / sha256 报告。
- 并发 episode run：至少 2 到 4 条极小真实仓库任务并发运行，验证 workspace、patch、artifact manifest、run directory、dependency runtime 目录、verifier worker 和 cleanup 不互相污染。
- 命令策略 smoke：真实任务中如果触发共享环境命令拦截，必须记录被拦截命令、拦截原因和可见输出；命令输出中不能出现真实 dependency environment 路径、workspace 路径、run directory、`.repo_harness_runtime` 或 `.repo_harness_env_overlay`。
- 命令策略受控负例：具体执行计划必须包含不进入 trainer batch 的 diagnostic task 或脚本化 episode，显式触发 `env`、`which python`、`python -c "import sys; print(sys.executable)"`、`python -m pip install ...` 等命令，证明它们被结构化归类为 `command_policy_blocked` 或等价安全拒绝原因，并且可见输出和 command artifact 不泄漏真实路径。
- formal batch smoke：所有 valid 样本必须 `route=verl`，必须有 `response_logprobs`，必须有 `generation_records` 和 `response_spans`，并通过 formal batch validator。缺失 log probability、mixed route、overflow、invalid_for_online_rl 或路径 visibility 失败的样本必须被结构化拒绝。
- batch refill / resample smoke：如果有效样本不足，必须记录 refill attempts、invalid reason distribution、最终 valid sample 数量和 insufficient valid batch reason，不能把 invalid 样本悄悄放进有效 policy loss。
- trainer smoke：至少完成一个小步 trainer global step，记录 DataProto shape、loss mask、padding ratio、有效样本数、invalid 样本过滤、GPU / Ray / SGLang 或 vLLM 指标。这里的 trainer smoke 不能降级成只调用 `compute_advantage`、`compute_policy_loss` 或等价低层 loss 函数；必须证明真实 `DataProto -> trainer -> global step` 路径跑过。

建议 evidence 目录：

```text
runs/stage12_6-remote-<timestamp>/
  stage12_6_preflight.json
  stage12_6_command_log.sanitized.jsonl
  runtime_private/stage12_6_command_log.raw.jsonl
  git_state_before_after.json
  environment_cache_report.json
  workspace_cache_report.json
  concurrent_episode_report.json
  command_policy_and_runtime_visibility_report.json
  trainer_throughput_profile.json
  verifier_recorder_tool_hot_path_report.json
  batch_refill_resample_report.json
  dataproto_padding_profile.json
  evidence_path_leak_scan_report.json
  real_episode_task_pool_report.json
  formal_batch_and_refill_report.json
  dataproto_and_trainer_smoke_report.json
  inference_server_profile.json
  tokenization_profile.json
  ray_worker_resource_profile.json
  system_resource_profile.json
  visibility_and_batch_validation_report.json
  stage12_6_acceptance_summary.json
```

如果具体执行计划为了减少文件数量而合并报告，必须在 `stage12_6_acceptance_summary.json` 中给出 canonical evidence item 到实际文件的映射，并说明哪些字段被合并到 `formal_batch_and_refill_report.json`、`dataproto_and_trainer_smoke_report.json`、`system_resource_profile.json` 或其他报告中。验收时以 canonical evidence item 是否完整覆盖为准，而不是只看文件名是否逐字匹配。

通过标准：

- 远端仓库代码基于明确 commit，执行前后工作区状态可审计。
- 远端执行前后必须记录 `git rev-parse HEAD` 和 `git status --short`。正式通过原则上要求远端工作区干净；如果远端必须带未提交 patch，必须把 patch 文件纳入 evidence，并明确标记为非正式通过或带条件通过。
- 至少一轮 cold cache 和一轮 warm cache 完成，并能看到 dependency environment / workspace snapshot 的 cache hit / miss 事实。
- 至少一组并发 real episode 完成，且没有 workspace、run directory、artifact manifest、hidden runtime directory 或 cleanup 串扰。
- 至少产生一个通过 formal batch validator 的 valid online RL sample，并完成一个 trainer global step。
- 该 valid online RL sample 必须来自真实 `route=verl`、真实 `response_logprobs`、真实 formal batch validator 和真实 trainer 输入路径，不能来自 mock server、fake log probability、debug fixture 或手工构造的 DataProto。
- 所有进入有效 policy loss 的样本都满足 Stage 0H 到 Stage 12.5 的 token、mask、log probability、route、generation record、response span 和 visibility 不变量。
- invalid、timeout、infrastructure error、model format failure、verifier rejected 和 command policy blocked 的分类可审计。
- `TrainingView`、`AgentLoopOutput`、DataProto non-tensor batch、meta_info 和模型可见 tool 输出中没有本机绝对 dependency environment path、workspace path、run directory、`.repo_harness_runtime` 或 `.repo_harness_env_overlay`。
- `stage12_6_command_log.sanitized.jsonl`、command artifact、profile JSON、acceptance summary 和其他可传播 evidence JSON 本身也必须经过路径泄漏扫描，不能暴露真实 dependency environment path、workspace path、run directory、`.repo_harness_runtime` 或 `.repo_harness_env_overlay`。
- 路径泄漏扫描必须分层报告：用户可传播或可上传的 summary evidence 必须脱敏；runtime-private raw evidence 如果为了远端调试保留真实路径，必须明确标记为本地私有，不进入 batch、不进入公开报告、不进入 Stage 12.6 acceptance summary 的可传播字段。

只有 Stage 12.6 通过后，才进入 Stage 13 fully async。否则 Stage 13 必须先记录远端 smoke 的阻断原因，并把 fully async 降级为接口预研或问题修复前置工作。

## 19. Stage 13：fully async 分阶段演进

目标：在 Stage 12.6 已经证明同步真实链路可用之后，把 RepoHarness 接入 verl fully async 训练路径。Stage 13 不能一次性把现有同步 `real_episode` 直接改成完整 fully async；必须先固定异步 episode 生命周期、reward finality、样本身份、资源租约和 evidence gate，再逐步接入 verl 的 Rollouter、MessageQueue、Trainer 和 parameter synchronization。

Stage 13 延续前面阶段的执行节奏：每一个子阶段都必须先由执行 agent 编写独立实施计划文档，审查通过后再实现；实现完成并通过本地或远端验收后，才进入下一个子阶段。建议后续文档命名为：

```text
21-stage-13-0-execution-plan.md
22-stage-13-1-execution-plan.md
23-stage-13-2-execution-plan.md
24-stage-13-3-a-execution-plan.md
25-stage-13-3-b-execution-plan.md
```

Stage 13 的总边界：

- 不因为追求异步吞吐而放松 Stage 0H 到 Stage 12.6 固定的 token、mask、log probability、route、generation record、response span 和 visibility 不变量。
- 不把 `reward_score=None`、pending verifier、provisional reward、stale reward 或无法绑定 final verifier evidence 的样本放进有效 policy loss。
- 不把 `actor_rollout_ref.rollout.mode=async` 误写成 RepoHarness fully async 已完成。前者只是 verl / SGLang 或 vLLM rollout 服务配置；RepoHarness fully async 还必须覆盖 workspace、tool、verifier、reward、recorder 和 audit 生命周期。
- 不把同步 `AgentLoop.run()`、同步工具执行、本地命令、workspace 物化、依赖环境准备、同步 verifier 或 recorder 写入直接塞进事件循环。它们在被分阶段异步化之前，必须继续通过 executor、worker pool、Ray actor 或单写入者队列隔离。
- 不在 Stage 13.0 到 Stage 13.2 中要求模型收敛或大规模 SWE-Bench 训练。第一版仍使用极小真实仓库任务和短步数 smoke 验证 contract。

### Stage 13.0：fully async 前置 contract hardening

目标：先补齐 fully async 会依赖的安全 contract 和 hardening，不启动真实 fully async trainer。

必须固定的 contract：

- `AsyncEpisodeHandle` 或等价对象，至少表达 `episode_id`、`run_id`、`sample_attempt_id`、`status`、`wait_result`、`cancel`、`resume`、`snapshot`、resource lease 状态和 audit refs。
- `resume` 第一版可以先是可表达但不一定可执行的能力。例如允许返回 `resume_supported=false`、`resume_status=unsupported_in_stage13_1` 或等价结构化状态，避免 Stage 13.0 / Stage 13.1 被迫提前实现完整轨迹恢复。
- reward finality contract，明确区分 `pending_verifier`、`final_verifier_completed`、`invalid_reward`、`cancelled`、`timeout` 等状态。
- formal online RL batch 只允许 `final_verifier_completed` 的样本；即使 `reward_score` 是非空数值，也必须有可信 `final_verifier_ref`、`reward_metadata_ref`、`reward_job_id` 和 `reward_score_source=trusted_final_verifier` 或等价事实。
- `sample_id -> episode_id / run_id / sample_attempt_id` 的稳定映射。重采样、重复 task、迟到 reward、恢复运行都不能因为只看 `episode_id` 而绑定错样本。
- final verifier 超时后的 workspace 生命周期。同步 verifier callable 如果还在运行，workspace lease 和相关资源不能提前删除；如果需要快速释放，必须使用可强制终止的进程 worker 并在终止确认后释放。
- real episode 最终审计写入和 `finalize_run` 必须仍在 run directory single writer 保护内。不能先释放 `run_id` 资源锁，再写 final verifier、reward metadata 或 summary。
- cleanup deadline、recorder lock timeout、orphan diagnostics 和 hidden runtime directory cleanup 需要进入 schema 或 diagnostics，避免 fully async 并发放大后资源无界积累。
- 当前 verl fully async interface inventory 必须成为 Stage 13.0 验收项。实施计划需要记录 `verl.experimental.fully_async_policy.fully_async_main`、`FullyAsyncRollouter`、`MessageQueue`、`RolloutSample`、`FullyAsyncTrainer._fit_generate(...)`、`actor_rollout_ref.actor.use_rollout_log_probs`、`algorithm.rollout_correction.bypass_mode`、`data.gen_batch_size`、`data.train_batch_size`、`async_training.require_batches`、`async_training.staleness_threshold` 和 `async_training.partial_rollout` 的当前字段、默认值和调用形状。

建议新增测试：

- pending reward 样本被 formal batch validator 拒绝。
- 有数值 `reward_score` 但没有 final verifier / reward metadata 绑定时被拒绝。
- 迟到 reward 的 `reward_job_id`、`sample_attempt_id` 或 `trajectory_digest` 不匹配时被拒绝。
- 同一个 `episode_id` 多次 attempt 时，reward 只能绑定对应 attempt。
- final verifier 超时后，workspace lease 不会在底层 verifier 仍可能访问 workspace 时提前释放。
- final audit 写入完成前，同一个 `run_id` 不能被新 episode 复用。
- async reward queue、result queue、backfill ledger 和 DataProto 路径继续拒绝 hidden verifier、完整 reward metadata、ground truth 和本机绝对路径。

Stage 13.0 通过后，只表示 fully async 的安全 contract 已经稳定；还不能宣称 RepoHarness 已经接入 verl fully async trainer。

### Stage 13.1：RepoHarness async episode facade 原型

目标：在 RepoHarness 内部提供最小异步 episode facade，让 episode 可以被启动、查询、取消、等待和审计，但仍然允许底层真实 AgentLoop 暂时运行在线程池或 worker pool 中。

第一版需要做到：

- 新增 `RepoHarnessRuntime.start_episode(...)` 或等价入口，返回 `AsyncEpisodeHandle`，而不是直接等待终态 `RepoHarnessEpisodeResult`。
- 支持 `handle.status()`、`handle.wait_result()`、`handle.cancel()`、`handle.snapshot()` 和审计引用查询。
- 取消语义必须保守：如果底层同步 AgentLoop、工具、verifier 或 recorder 不能立刻停止，资源 lease 必须保持到安全结束或强制终止确认后再释放。
- 同步组件继续留在受控 executor、worker pool 或进程 worker 中，不能阻塞主事件循环。
- final verifier、reward boundary、artifact 写入和 cleanup 的生命周期必须可审计。
- `TrainingView` 只能在终态 reward finality 满足后进入 formal online RL batch；pending episode 只能进入诊断或 observability，不进入 policy loss。

Stage 13.1 的本地 smoke 可以使用 fake gateway、小仓库任务和短 verifier，不需要启动 Ray、SGLang、vLLM 或 fully async trainer。

### Stage 13.2：fully async RolloutSample / MessageQueue / DataProto 结构路径

目标：把 RepoHarness 的异步 episode 终态结果投影成 verl `fully_async_policy` 可以消费的 `RolloutSample`、MessageQueue payload 和 DataProto assembly 前结构，先完成本地结构性 smoke 和安全校验，不追求吞吐。

Stage 13.2 只完成 `RolloutSample` / MessageQueue payload / DataProto assembly 的结构路径和安全校验，不代表已经接通真实 `FullyAsyncRollouter` / `FullyAsyncTrainer` runtime。真实 producer loop、trainer-side filtering 接入、多步 trainer global step 和 parameter synchronization 属于 Stage 13.3-A / Stage 13.3-B。

需要明确的边界：

- 使用 verl fully async 入口 `python -m verl.experimental.fully_async_policy.fully_async_main`，而不是普通 `main_ppo` 加 `actor_rollout_ref.rollout.mode=async` 的旧路径。
- Rollouter 生成的 `sample_id` 必须在进入 `RepoHarnessVerlAgentLoop.run(...)` 前映射到 `sample_attempt_id`、`episode_id` 和 `run_id`。
- MessageQueue 中只能传播 batch-safe 字段、opaque audit refs 和必要的版本事实；不能传播完整 `AuditRef`、本机路径、hidden verifier、完整 reward metadata 或 evaluator-only 信息。
- `RolloutSample` 或等价对象必须能关联 `generation_record_digest`、`trajectory_digest`、`reward_state`、`reward_job_id`、`min_global_steps`、`max_global_steps`、staleness facts 和 visibility scan status。当前 `reference/verl` 的 `RolloutSample` 主要包含 `full_batch`、`sample_id`、`epoch` 和 `rollout_status`，因此第一版优先通过 `rollout_status` 或 `DataProto.non_tensor_batch` 中的 `repo_harness_*` namespaced 字段承载这些事实；不要直接大改 verl dataclass，除非对应子阶段实施计划明确说明需要 patch verl 并补充兼容测试。
- `actor_rollout_ref.actor.use_rollout_log_probs=True` 或当前 verl 版本等价配置必须显式记录；不能为了 fully async 关闭 rollout log probability provenance。
- `algorithm.rollout_correction.bypass_mode` 的选择必须记录，并说明是否改变 old log probability 来源。
- stale trajectory、cancelled trajectory、partial trajectory、pending reward trajectory 的过滤、丢弃、延迟或权重策略必须可审计。
- refill / resample 只统计 `final_verifier_completed` 且通过 formal validator 的样本；pending、timeout、missing logprobs、non-verl、visibility rejected、stale reward 样本不能进入 valid sample count。

Stage 13.2 的 smoke 可以使用本地或单机 Ray 结构测试，重点是 MessageQueue、DataProto、visibility 和 sample identity，不要求远端长时间训练。

### Stage 13.3-A：fully async runtime adapter 本地实现

目标：先补齐 RepoHarness 与 verl fully async runtime 的真实 adapter 代码，让 Stage 13.2 已完成的样本桥接、安全闸门和 visibility gate 接入一个可执行的 producer / trainer-side filtering 路径。这个阶段仍然以本地结构测试、fake MessageQueue、fake trainer control loop 或轻量单机测试为主，不启动远端 GPU 多步训练，也不能宣称 parameter synchronization 已经在真实 trainer 中跑通。

新增这一阶段的原因是：Stage 13.2 已经完成的是下面这段本地桥接：

```text
RepoHarnessEpisodeResult
-> FormalAsyncOnlineRLSample
-> RepoHarnessFullyAsyncQueueFacts
-> RolloutSample.full_batch.non_tensor_batch
-> MessageQueue bytes payload visibility gate
-> DataProto assembly 前结构校验
```

它还没有实现下面这段真实运行时链路：

```text
RepoHarness async episode producer
-> MessageQueueClient.put_sample(...)
-> FullyAsyncTrainer 从 queue 取样本
-> trainer-side valid sample filtering
-> 多个 trainer global step
-> parameter synchronization
-> sync 后继续 rollout
```

Stage 13.3-A 第一版需要实现或明确固定：

- RepoHarness fully async rollout producer。它需要从任务池取样，调用 `RepoHarnessRuntime.start_episode(...)`，等待 `AsyncEpisodeHandle.wait_result(...)`，并把终态结果转换成 `RolloutSample`。
- MessageQueue producer loop。它必须通过 Stage 13.2 的 `build_queue_facts_from_episode_result(...)`、`attach_queue_facts_to_rollout_sample(...)`、`serialize_rollout_sample_for_message_queue(...)` 或等价 helper，把样本写入真实或 fake `MessageQueueClient.put_sample(...)`。
- trainer-side sample filter。trainer 从 queue 取样本后，必须复用 Stage 13.2 的 formal async validator 和 queue facts validator，保证 invalid、partial、stale、visibility rejected、pending reward、timeout、cancelled 或 missing logprob 样本不计入 `required_samples`，也不进入 policy loss。
- 第一版优先在 `src/repo_harness_verl` 中实现 trainer-side helper、wrapper 或 adapter 层，不直接修改 `reference/verl` 核心训练逻辑。如果必须修改 `reference/verl` 的 queue consumption、rollout sample path 或 trainer sample path，执行计划必须单独列出 diff 归属、兼容性测试和回退边界。
- 参数版本 facts 投影。每个样本必须携带或可解释 `min_global_steps`、`max_global_steps`、`global_steps`、`trajectory_param_versions`、`current_param_version` 或当前 `reference/verl` 可承载的等价字段。第一版可以先使用 `repo_harness_*` namespaced non-tensor 字段和 adapter-side diagnostics，但必须为 Stage 13.3-B 的真实 parameter synchronization smoke 留出清晰接口。
- partial rollout 第一版策略。`partial_rollout_supported=false` 时，partial trajectory 必须在 policy loss 之前被拒绝，并记录 `partial_rollout_status` 和 rejection reason。不要在 Stage 13.3-A 顺手实现 resume。
- stale trajectory 统计。即使本地 fake trainer 不真正更新参数，也必须能构造参数版本变化或 global step 变化，验证 stale sample 被分类、过滤和报告。
- resource lifecycle。producer loop 取消、MessageQueue 写入失败、trainer-side 过滤失败或 refill 失败时，`AsyncEpisodeHandle`、workspace lease、run directory lock、recorder finalization 和 cleanup diagnostics 必须仍然可审计。

Stage 13.3-A 不应该做：

- 不启动远端 GPU 实例。
- 不把普通 `main_ppo` 或 `actor_rollout_ref.rollout.mode=async` 当成 RepoHarness fully async 完成。
- 不要求真实模型收敛。
- 不要求真实 `update_weights(...)` 已经发生。
- 不放松 `route=verl`、`response_logprobs`、generation records、response spans、formal batch validator 或 visibility gate。

Stage 13.3-A 通过标准：

- 本地 fake MessageQueue 或轻量单机 harness 能跑通 `AsyncEpisodeHandle -> RolloutSample -> MessageQueue payload -> trainer-side filtering -> selected valid samples`。
- 构造超过 `required_samples` 的 queue payload backlog，其中同时包含 valid、invalid、partial、stale、visibility rejected、pending reward 和 diagnostic 样本；trainer-side filter 必须只选择 valid 样本。
- valid sample count 必须满足本地 fake trainer step 的 `required_samples`，不能因为 queue 中有 rejected 或 diagnostic 样本就把坏样本算作有效占位。
- `RolloutSample.sample_id`、`repo_harness_sample_id`、`sample_attempt_id`、`reward_job_id`、`trajectory_digest` 和 `generation_record_digest` 绑定一致。
- producer loop 取消和 queue 写入失败不会泄漏 workspace、run directory、hidden runtime directory 或 recorder lock。
- 输出本地 evidence，例如 `stage13_3a_local_adapter_report.json`、`stage13_3a_message_queue_filter_report.json`、`stage13_3a_resource_lifecycle_report.json` 和 `stage13_3a_acceptance_summary.json`。

只有 Stage 13.3-A 通过后，才进入 Stage 13.3-B 的远端 GPU 多步 fully async smoke。

### Stage 13.3-B：远端 GPU 多步 fully async smoke

目标：在远端 GPU 环境中运行最小 fully async 多步 smoke，证明 RepoHarness 的异步 episode producer、MessageQueue、trainer-side filtering、FullyAsyncTrainer 和 parameter synchronization 可以共同工作。这个阶段才验证真实 `FullyAsyncTrainer` 多步训练和参数同步，不再只验证结构桥接。

远端 smoke 建议沿用 Stage 12.6 的保守硬件和模型选择：

- 小模型，例如 `Qwen2.5-Coder-7B-Instruct` 或同等级 code instruct model。
- 极小真实仓库任务池。
- 短上下文、短 response、极小 batch。
- 运行 3 到 4 个 fully async trainer global step，不要求收敛。
- 建议 `trigger_parameter_sync_step=2` 或等价保守配置，至少验证一次 parameter synchronization。

必须生成或等价覆盖的 evidence：

- `stage13_3b_preflight.json`
- `fully_async_rollouter_profile.json`
- `fully_async_message_queue_report.json`
- `async_episode_lifecycle_report.json`
- `reward_backfill_ledger_report.json`
- `stale_and_partial_trajectory_report.json`
- `formal_batch_and_visibility_report.json`
- `trainer_global_step_report.json`
- `parameter_sync_report.json`
- `resource_cleanup_and_orphan_report.json`
- `stage13_3b_parameter_sync_report.json`
- `stage13_3b_trainer_steps_report.json`
- `stage13_3b_message_queue_backlog_report.json`
- `stage13_3b_valid_sample_filter_report.json`
- `stage13_3b_visibility_report.json`
- `stage13_3b_resource_lifecycle_report.json`
- `stage13_3b_acceptance_summary.json`

其中参数同步和队列 evidence 至少需要记录：

```text
current_param_version
trigger_parameter_sync_step
trajectory_param_versions
min_global_steps
max_global_steps
post_sync_sample_count
stale_sample_count
filtered_stale_sample_count
valid_sample_count
rejected_sample_count
completed_trainer_step_count
```

Stage 13.3-B 通过标准：

- 至少一个真实 `route=verl` 样本完成 `AsyncEpisodeHandle -> final_verifier_completed -> TrainingView -> AgentLoopOutput -> MessageQueue -> DataProto -> trainer global step`。
- `FullyAsyncTrainer` 或当前 `reference/verl` 等价真实 trainer 路径完成 3 到 4 个 global step。
- 每个成功 trainer step 都必须消费至少一个有效 `route=verl` RepoHarness 样本；不能只用同一个样本或一个 step 证明整条多步训练链路。
- evidence 必须报告总 valid sample count、rejected sample count、diagnostic sample count 和 completed trainer step count。
- 至少发生一次 parameter synchronization，`current_param_version` 或等价版本事实至少达到 1；如果当前 verl 版本使用不同字段名，必须在 evidence 中说明真实字段来源。
- parameter synchronization 后，rollouter 或 RepoHarness producer 仍然可以继续把新样本写入 MessageQueue。
- `DataProto` 或 `non_tensor_batch` 中的 `trajectory_param_versions`、`min_global_steps`、`max_global_steps`、`global_steps` 或等价 `repo_harness_*` 字段可以解释每条 trajectory 的参数版本窗口。
- stale trajectory 有统计或过滤报告，不能只依赖 trainer 日志中的隐式丢弃。
- Stage 13.3-B 第一版仍默认 `partial_rollout_supported=false`。partial trajectory、resume-required trajectory 和 incomplete episode 不能进入 policy loss；如果 `reference/verl` 配置或真实 rollout 路径产生 partial rollout，RepoHarness 必须把它分类为 diagnostic 或 rejected sample。
- pending reward、stale reward、取消样本、超时样本和 visibility rejected 样本都被正确分类，不进入有效 policy loss。
- 第一版远端 happy path 可以只依赖少量真实模型样本。pending reward、stale reward、cancelled、timeout、visibility rejected 等负例可以通过受控构造样本、短路径注入或 diagnostic episode 验证，不要求全部由真实模型自然触发。
- MessageQueue、DataProto non-tensor batch、meta_info 和可传播 evidence 均通过 visibility 检查。
- 资源租约、workspace、hidden runtime directory、run directory、recorder 和 verifier worker 没有并发串扰或 orphan 泄漏。
- 如果 fully async 失败，必须归类为 adapter incompatibility、reward backfill mismatch、message queue shape failure、parameter sync failure、trainer failure、resource lifecycle failure 或模型行为失败，不能只写笼统 infrastructure error。

只有 Stage 13.3-B 通过后，才能说 RepoHarness 已经完成第一版 verl fully async agentic RL 链路 smoke。Stage 13.0 到 Stage 13.2 通过只能说明异步 contract 和本地结构已经准备好；Stage 13.3-A 通过只能说明 runtime adapter 和本地 producer / filtering 路径已经准备好。

## 20. Stage 14：fully async 可复现验收与 partial rollout / resume 前置能力

目标：在 Stage 13.3-B 已经证明“真实 fully async trainer 多步和参数同步可以跑通”之后，把这条链路从一次远端 smoke 升级成可复现、可检查、可多任务扩展的小规模训练验收层，并为后续 partial rollout / resume 做安全前置。Stage 14 不是直接追求模型收敛，也不是直接打开 `partial_rollout=True` 后让 partial trajectory 进入 policy loss。

Stage 14 的核心判断是：

```text
Stage 13.3-B:
  证明真实 fully async 链路能跑通一次

Stage 14:
  证明这条链路可以被脚本化复现、机器检查、多任务扩展，并且开始具备安全 checkpoint / resume 设计

Stage 15:
  在 checkpoint / resume contract 稳定后，再正式接入真实 verl partial_rollout=True 的远端 smoke

Stage 16 或独立路线:
  再规划旧 CLI / offline export 与 RepoHarnessRuntime.run_episode(...) 的统一
```

新增这一阶段的原因是：Stage 13.3-B 的远端证据已经足以说明第一版链路成立，但它仍然是短步数 smoke。当前证据中只有少量真实 episode，远端运行脚本、SGLang / LoRA merge 参数、环境 preflight、evidence manifest、日志扫描和实例生命周期仍需要进一步产品化。如果跳过这些加固直接做 partial rollout，后续很容易把恢复状态、reward finality、token provenance、workspace 生命周期和 trainer queue 过滤问题混在一起调试。

Stage 14 延续前面阶段的执行节奏：每个子阶段都必须先由执行 agent 编写独立实施计划文档，审查通过后再实现；实现完成并通过本地或远端验收后，才进入下一个子阶段。建议后续文档命名为：

```text
26-stage-14-0-execution-plan.md
27-stage-14-1-execution-plan.md
28-stage-14-2-execution-plan.md
29-stage-14-3-execution-plan.md
```

Stage 14 的总边界：

- 不把 Stage 13.3-B 的一次通过误写成稳定小规模训练系统已经完成。
- 不在 checkpoint / resume contract 稳定前打开真实 `partial_rollout=True` 并允许 partial trajectory 进入 policy loss。
- 不把 Stage 14.0 已跑通的 `2 * 96GB GPU + SGLang + Qwen2.5-Coder-1.5B-Instruct + full training + lora_rank=0 + NIXL CUDA weight sync` 误写成正式训练唯一配置。它只是 Stage 14.0 用来产品化脚本、验收器和 evidence schema 的开发 smoke baseline。`7B LoRA + merged weight sync` 是历史尝试或后续候选 profile；未来 `8 * 96GB GPU`、7B 全参 RL、不同 rollout 后端或不同参数同步策略必须通过独立 profile evidence 决定。
- 不允许 pending reward、pending verifier、timeout、cancelled、visibility rejected、missing logprob、non-verl route 或 stale reward 样本补位成 valid sample。
- 不允许 policy loss 入口只依赖 payload 自己声明的 `repo_harness_valid_for_policy_loss=true`。Stage 14 必须明确实现不可绕过的 policy-loss gate：要么在 `MessageQueueClient.put_sample(...)` 之前完成 source gate，只把 valid 样本写入真实 policy-loss queue；要么显式修改或包装 trainer 取样路径，让它验证外部 visibility ledger 和 queue facts，并持续取样直到凑够 required valid samples。只做事后 inspect 不算通过。
- rejected / diagnostic 样本必须走物理隔离的 side channel，例如独立 report、独立 artifact 或独立 queue actor。不能先把坏样本放入真实 policy-loss MessageQueue，再指望 `FullyAsyncTrainer` 自动理解 RepoHarness 字段并过滤。
- MessageQueue 满队列导致的 drop 必须可审计。Stage 14 默认要求 `message_queue_dropped_sample_count=0`；如果执行计划允许受控 drop，必须有逐样本 produced / consumed / dropped ledger，并且 dropped 样本不能被计入 valid、post-sync 或 trainer step 统计。
- 不把 hidden verifier、gold patch、完整 reward metadata、本机绝对路径、dependency environment 路径、workspace 路径、run directory 或 provider secret 放入模型可见字段、MessageQueue、DataProto、meta_info 或可传播 evidence。
- 不要求模型收敛，不做大规模 SWE-Bench 训练，不把多节点或 4 卡扩展作为第一目标。
- 不把传统 `repo-harness run-task`、`run-batch`、`run-experiment` 和离线 export 的全面迁移混进 Stage 14。旧 CLI / export 与 `RepoHarnessRuntime.run_episode(...)` 的统一应单独规划，避免同时改动训练主线和评测主线。

### Stage 14.0：fully async 远端链路验收器和脚本化

目标：把 Stage 13.3-B 的远端成功经验从一次性 run artifact，沉淀为仓库内可复用、可复查、可机器验收的远端 fully async smoke 流程。

需要完成或明确固定：

- 远端 preflight、训练启动、日志采集、evidence 打包、实例暂停或停止的脚本化入口。脚本必须记录代码 commit、镜像、Python、Ray、torch、transformers、SGLang、verl 来源、模型、tokenizer / chat template、GPU、驱动、CUDA、`PYTHONPATH` 和关键环境变量。
- Stage 14.0 的默认远端配置固定为开发 smoke baseline，建议 profile 名称为 `dev_smoke_2x96gb_small_full_sync`。这个 profile 复用 Stage 14.0 远端最终跑通的 `2 * 96GB GPU`、SGLang、`Qwen2.5-Coder-1.5B-Instruct`、`lora_rank=0` full training 和 NIXL CUDA weight sync 路径，用来稳定脚本、验收器、evidence schema 和 fully async 链路回归。
- 固化 `dev_smoke_2x96gb_small_full_sync` 的第一版成功路径，包括 `flashinfer`、`checkpoint_engine.backend=nixl`、`checkpoint_engine.engine_kwargs.nixl.device=cuda`、`multi_turn.enable=True`、`calculate_log_probs=True`、`actor.use_rollout_log_probs=True`、`repo_harness` agent loop 注册和参数同步配置。
- 远端运行脚本不能把具体 GPU 数量、训练策略、rollout 后端或参数同步方式散落写死。必须引入训练 profile 或等价配置层，至少能表达 `dev_smoke_2x96gb_small_full_sync`，并为后续 `future_8x96gb_full_param_candidate`、`future_8x96gb_lora_or_adapter_candidate` 或其他正式训练候选 profile 预留字段。
- `future_8x96gb_full_param_candidate` 只是后续正式训练候选，不是 Stage 14.0 通过条件。若后续准备在 `8 * 96GB GPU` 上对 7B 模型做全参 RL，必须另跑 profile preflight 和吞吐 / 参数同步证据，不能直接沿用双卡 LoRA smoke 的结论。
- Stage 14.0 必须实现最小可执行的正式 inspect 命令或等价验收脚本，规范名称建议为 `inspect-stage14-fully-async-acceptance`。`inspect-stage13-3b-acceptance` 可以作为兼容别名，但 Stage 14 的正式验收入口应使用 Stage 14 命名。只写设计文档或只规划命令不算通过。它必须机器检查 trainer step、parameter synchronization、MessageQueue、valid sample count、formal validator rejected count、diagnostic sample count、visibility、日志负例、evidence hash、resource cleanup 和 canonical evidence mapping。
- 把 Stage 13.3-B 中运行产物里的 runtime helper、agent loop config、run script 和 source map 生成逻辑收口到仓库内正式脚本或 builder，不能长期依赖手工复制远端脚本。
- 远端 evidence 必须区分可传播 summary evidence 和 runtime-private raw evidence。可传播 evidence 不能泄漏真实 workspace、dependency environment、run directory 或 provider secret；runtime-private raw evidence 若保留真实路径，必须明确标记为本地私有，不进入训练 batch 或公开报告。
- 验收器必须扫描完整 evidence tarball、summary JSON、日志、脚本、source map、profile、sanitized command log 和公开报告。环境变量只能按 allowlist 投影；真实路径只能以 hash、相对 ref 或 `rh://` opaque ref 出现。验收器不能在本地反序列化不可信的 `cloudpickle` payload，只能检查外层 ledger、digest、manifest 和安全摘要。
- 远端运行必须固定 `RepoHarness` commit、`reference/verl` commit 或实际安装包版本、远端补丁 manifest、补丁 sha256、模型 revision、tokenizer / chat template revision、fixture manifest 和任务 manifest。远端临时补丁如果没有进入 manifest，验收必须失败，避免用 dirty remote patch 产生不可复现通过结果。
- Stage 14.0 就必须检查 stale trajectory，而不是等到 partial checkpoint 阶段。验收器需要读取 staleness threshold、每条样本的 `min_global_steps` / `max_global_steps` / `trajectory_param_versions` / `current_param_version`，并统计 stale、filtered stale 和最大 observed staleness。
- Stage 14.0 也必须检查真实 trainer batch 中 policy loss 使用的 token / log probability provenance。至少要在 `_update_actor` 前或等价 hook 处记录 batch digest，证明 rollout log probability tensor 或 old log probability tensor，与 response ids、response mask、response spans、generation records、tokenizer、chat template、sampling params 和 policy version digest 对齐。如果需要修改 `reference/verl`、monkey patch trainer hook 或注入远端 helper，必须把 patch 文件、sha256、启用方式和回退方式写入 `remote_patch_manifest`；没有登记的远端 trainer hook patch 不能通过验收。

Stage 14.0 acceptance summary 至少需要包含：

```text
acceptance_passed
repo_harness_commit
verl_commit_or_package_version
remote_patch_manifest_sha256
training_profile_name
gpu_count
gpu_memory_gb_per_device
inference_backend
training_strategy
weight_sync_strategy
model_revision
fixture_manifest_sha256
completed_trainer_step_count
parameter_sync_count
current_param_version
valid_sample_count
final_verifier_rejected_trainable_count
formal_validator_rejected_count
diagnostic_sample_count
policy_loss_queue_invalid_sample_count
message_queue_dropped_sample_count
post_sync_valid_sample_count
staleness_threshold
stale_sample_count
filtered_stale_sample_count
max_observed_staleness
trainer_batch_logprob_provenance_passed
trainer_batch_digest
visibility_scan_passed
evidence_tarball_sha256
```

通过标准：

- 可以在一台新的远端实例上按脚本从 preflight 到 evidence collect 完成短步数 fully async smoke。
- 机器验收命令能够在本地下载后的 evidence 目录上独立判断通过或失败，而不是依赖人工阅读日志。
- 验收器能拒绝缺失 parameter synchronization、缺失 valid sample count、缺失 formal validator rejected count、缺失 diagnostic sample count、缺失 visibility report、日志出现关键错误、evidence hash 不匹配、dirty patch 未登记、MessageQueue drop 未解释或 summary 与底层报告不一致的证据包。
- `policy_loss_queue_invalid_sample_count` 必须等于 0；默认 `message_queue_dropped_sample_count` 必须等于 0；`trainer_batch_logprob_provenance_passed` 必须为 true；超过 staleness threshold 的样本必须进入 filtered stale 统计，不能进入 policy loss。

### Stage 14.1：多任务 real episode 扩展和远端负例 side channel

目标：把 Stage 13.3-B 的“少量样本链路跑通”扩展到多个唯一真实 episode、多种任务形态和受控负例，证明 fully async 训练链路不仅能跑一次，而且能在小任务池上稳定分类和过滤样本。

任务池至少需要覆盖：

- 无外部依赖的基线任务。
- 有轻量第三方 Python 依赖的任务。
- `src/` layout 或等价 workspace import 任务。
- final verifier accepted 的成功任务。
- final verifier rejected 的可信模型失败任务。只有模型行为导致的可信任务失败，且 final verifier 已完成、`verifier_summary.status="rejected"`、reward finality 完成、route / logprob / generation record / response span / visibility 全部通过时，才可以作为 trainable negative sample 候选。
- 可信 final verifier rejected 样本可以是 valid training sample，但 reward / outcome 是负向。报告必须区分 `trainable_negative_eligible_count` 和 `trainable_negative_consumed_count`，不能把“可作为负样本候选”和“已经被本次 policy loss batch 消费”混在一起。
- 模型格式失败、timeout、missing logprob、non-verl route、visibility rejected、partial、cancelled 或 stale 的受控负例。负例可以走 diagnostic side channel，不要求自然由真实模型触发。
- timeout、cancelled、format failure、no-progress、infrastructure error、visibility rejected、pending reward、pending verifier、missing logprob、non-verl route、partial 和 stale trajectory 一律不能作为 trainable negative sample，只能进入 diagnostic side channel 或 formal validator rejected 统计。

必须记录：

```text
unique_real_episode_count
unique_task_id_count
trajectory_digest_count
valid_sample_count
final_verifier_rejected_trainable_count
trainable_negative_eligible_count
trainable_negative_consumed_count
formal_validator_rejected_count
diagnostic_sample_count
accepted_count
invalid_reason_distribution
post_sync_valid_sample_count
post_sync_final_verifier_rejected_trainable_count
policy_loss_queue_valid_sample_count
policy_loss_queue_invalid_sample_count
message_queue_produced_sample_count
message_queue_consumed_sample_count
message_queue_dropped_sample_count
side_channel_sample_count
```

通过标准：

- 远端 evidence 至少包含 `unique_real_episode_count >= 3` 且 `unique_task_id_count >= 3` 的真实 run directory，不能只复用一条成功轨迹证明多步 trainer。
- 至少包含 1 个 final verifier accepted 样本、1 个可信 final verifier rejected trainable negative 候选、1 个受控 diagnostic 或 formal validator rejected side-channel 样本，以及至少 2 个 parameter synchronization 之后产生的 valid 样本。
- 每个进入 policy loss 的样本都能回查到 `route=verl`、非空 response、可信 `response_logprobs`、generation records、response spans、final verifier / reward finality 和 visibility scan digest。
- rejected / diagnostic side channel 可以包含坏样本，但真实 policy-loss MessageQueue 不能接收这些坏样本。`policy_loss_queue_invalid_sample_count` 必须为 0。
- `message_queue_dropped_sample_count` 默认必须为 0。若执行计划为了测试 overflow 特意制造 drop，必须把该用例放入 diagnostic side channel，并证明 dropped 样本没有影响 valid sample count、trainer step count 或 post-sync 统计。
- 参数同步后仍有新的 RepoHarness 样本进入 MessageQueue，并且报告中能区分同步前和同步后的样本。
- 如果 Stage 14.1 采用 trainer-side filter 而不是 source gate，filter 不能只读取 `required_samples` 条原始 queue entry 就停止；它必须继续读取，直到选中的 valid sample count 达到 `required_samples`，或者遇到 termination signal、max dequeue limit 或 timeout。
- Stage 14.1 多任务池仍优先保持短步数 smoke，默认继续使用 `dev_smoke_2x96gb_small_full_sync`。只有吞吐、显存或 parameter synchronization profile 报告证明必要时，才升级到更多 GPU 或其他训练 profile。

### Stage 14.2：partial checkpoint contract

目标：先定义和验证 RepoHarness 自己的 partial episode checkpoint，不急着接入 verl `partial_rollout=True`。这一阶段解决“中途状态能否安全落盘、校验、恢复前置审计和拒绝篡改”的问题。

Stage 14.2 必须新增 shared contract 文档或 Stage 14 专用 canonical fixture。它需要覆盖 partial checkpoint roundtrip、visibility、tamper rejection、digest binding、durable writer lease、reward finality 和不可训练状态，延续 Stage 0H 以来先固定 contract 再实现 runtime 行为的做法。

第一版 `PartialEpisodeCheckpoint` 或等价 schema 至少需要表达：

- `episode_id`、`run_id`、`sample_attempt_id`、`task_id`、dataset identity、policy version、global step 和参数版本窗口。
- 当前 turn、context revision、budget state、no-progress state、tool state summary 和 recorder cursor。
- durable writer lease facts，包括 lease token、owner、epoch、heartbeat、acquired_at、last_heartbeat_at 和 atomic release 状态。单进程内存集合不能作为远端 Ray / 多进程 / resume 的唯一 writer 保护。
- recorder cursor digest、artifact manifest digest、transcript digest、events digest 和 finalization state。
- 已提交的 transcript 记录、模型可见 messages 摘要、tool result refs、workspace snapshot / lease refs。
- workspace snapshot digest、source snapshot digest、dependency environment opaque ref 和 workspace lease digest。
- pending tool call / tool result 配对状态。未闭合的 tool call、重复 tool result、缺失 observation token projection 或 tool result visibility 失败都必须让 checkpoint 不可训练。
- 已完成模型回合的 `GenerationRecord`、response token ids、response mask、response logprobs、response spans 和 trajectory digest。
- token / logprob digest、generation record digest、response span digest、prompt digest、sampling params digest、tokenizer / chat template digest 和 policy version digest。
- workspace 状态引用和 patch 基准引用。不能把本机绝对 workspace 路径、dependency environment 路径或 run directory 作为可传播字段。
- checkpoint visibility scan digest、checkpoint content digest、generation record digest、trajectory digest 和篡改检测结果。
- reward finality 状态。partial checkpoint 默认没有 final reward，不能伪装成可训练终态样本。
- parameter clock，包括 `min_global_steps`、`max_global_steps`、`trajectory_param_versions`、`current_param_version_at_checkpoint` 和 resume 时需要重新计算的 staleness facts。
- resume attempt id。新的 resume attempt 只能表示一次恢复尝试，不能把旧 prefix 伪装成新的 fresh trajectory。

必须固定的安全规则：

- checkpoint 只能保存模型可见内容、batch-safe opaque refs 和 runtime-only 私有引用的受控投影。
- checkpoint 不能包含 hidden verifier、gold patch、完整 reward metadata、accepted label 细节、provider secret、evaluator-only logs 或真实本机路径。
- checkpoint 不能绕过 run directory single writer。只要底层 worker、tool、verifier、recorder 或 cleanup 仍可能写入，checkpoint 必须表达 writer 仍 active 或 checkpoint 不可恢复。远端或多进程实现必须使用 durable lease token、文件锁或等价机制，不能只依赖当前进程内的 `ResourceLeaseManager` 内存状态。
- checkpoint 与当前 run directory、artifact manifest、transcript、generation records 和 workspace facts 的 digest 必须绑定。`model_copy(...)`、字段删除、token 重排、logprob 伪造和 span 伪造都必须被拒绝。
- resume 前和 resume 后进入 queue 前，必须重新计算 `current_param_version - max_global_steps` 或等价 staleness 指标。超过阈值的 checkpoint / resumed sample 必须进入 diagnostic / rejected side channel，不能通过新的 `sample_attempt_id` 伪装成 fresh sample。
- token / logprob provenance 必须最终绑定到真实 policy loss batch 使用的 tensor。Stage 14 的 inspector 需要验证进入 `_update_actor` 前的真实 batch 中 rollout log probability tensor 或 old log probability tensor，与 response ids、response mask、response spans、generation records、tokenizer、chat template、sampling params 和 policy version digest 对齐。

通过标准：

- 本地构造 partial checkpoint 可以 roundtrip、hash、visibility scan 和 tamper reject。
- 缺少 token provenance、缺少 recorder cursor、缺少 workspace facts、缺少 run writer 状态、缺少 visibility digest 或 reward finality 伪造的 checkpoint 会被拒绝。
- partial checkpoint 只能进入 diagnostic / resume preparation，不进入 policy loss。
- 负例测试必须覆盖 forged valid flag、missing external visibility ledger、absolute path leak、MessageQueue drop、stale disguised as fresh、partial disguised as complete、logprob reorder、token reorder、reward_job_id mismatch 和 durable lease token mismatch。

### Stage 14.3：RepoHarness pause / resume facade 原型

目标：在 checkpoint contract 稳定后，为 RepoHarness runtime 增加最小 pause / resume facade。第一版只支持 turn boundary pause，不支持正在运行的 shell、pytest、Docker command、verifier 或模型请求的热迁移。

第一版允许的 pause 点：

```text
模型回合已经完成
工具调用已经完成或本轮没有工具调用
recorder 已经 flush 到一致状态
generation records 已经收集
workspace lease 仍由 runtime 持有或 checkpoint 明确绑定
run directory single writer 未释放或已安全转移
```

不允许的 pause 点：

```text
LLMGateway.generate_turn(...) 正在执行
tool command 正在执行
final verifier 正在执行
reward metadata 正在写入
artifact manifest 正在写入
cleanup 正在执行
```

第一版 resume 语义：

- `AsyncEpisodeHandle.snapshot()` 可以返回可恢复 checkpoint facts，但 `resume()` 只有在 checkpoint 验证、workspace facts、recorder cursor、generation record digest 和 visibility scan 全部通过后才能启动。
- resume 后的轨迹必须保留同一个 logical trajectory identity，并记录新的 `sample_attempt_id` 或 resume attempt id。
- resume 前后的 token、mask、logprob、generation records、response spans 和参数版本窗口必须重新绑定到最终 trajectory digest。
- resume 后写入 queue 前必须重新计算 staleness、parameter version window、reward finality、visibility scan digest 和 formal validator 结果；旧 checkpoint 的 fresh 状态不能沿用。
- resume 完成前，样本仍是 partial / diagnostic；只有 final verifier 完成、reward finality 完成、formal validator 通过后，才可以成为 valid online RL sample。

通过标准：

- 本地 fake gateway 或小仓库任务可以在 turn boundary 生成 checkpoint，停止，再从 checkpoint 恢复并完成 episode。
- resume 后的完整 episode 可以生成合法 `RepoHarnessEpisodeResult`、`TrainingView` 和 generation records。
- 恢复前的 partial checkpoint 不能进入 policy loss；恢复后的终态样本只有在 formal validator 通过后才能进入 valid sample count。
- 取消、超时、checkpoint 篡改、workspace lease 丢失、recorder cursor 不匹配和 generation record digest 不匹配都有结构化失败结果。
- Stage 14.3 通过只表示 RepoHarness 具备第一版 turn-boundary pause / resume 原型，不表示生产级 resume 已完成，也不表示真实 verl `partial_rollout=True` 样本已经可以进入 policy loss。真实 partial rollout 远端 smoke 应放到 Stage 15。

Stage 14 不应该做：

- 不支持工具执行中、verifier 执行中、cleanup 执行中或模型请求执行中的热迁移。
- 不承诺 KV cache resume。
- 不做大规模远端训练或模型收敛验收。
- 不把动态 SGLang LoRA adapter loading 修复作为主目标。当前 Stage 14.0 默认成功路径是小模型 full training + `lora_rank=0` + NIXL CUDA weight sync；`7B LoRA + merged weight sync` 可以作为历史尝试或后续独立候选 profile。
- 不把旧 CLI / offline export 全面迁移到 `run_episode(...)`。这条路线应单独规划，例如 Stage 16 或独立路线，不能和 Stage 15 的真实 partial rollout 远端 smoke 混在一起。

只有 Stage 14.0 和 Stage 14.1 通过后，才能说 fully async 远端链路从一次 smoke 升级为可复现、多任务、可机器验收的小规模训练路径。只有 Stage 14.2 和 Stage 14.3 通过后，才能进入真实 verl `partial_rollout=True` 的远端训练 smoke。

## 21. 已采纳的第一版默认决策

这些决策已经按当前讨论固定为第一版默认选择。后续 agent 应按下面的选择实施；如果需要改变，必须先更新本文档和对应 shared contracts。

1. canonical fixture 放在 `tests/fixtures/repo_harness_verl/`，文档目录只放说明。
2. `RepoHarnessRuntime.run_episode(...)` 第一版放在 `src/repo_harness/rl/runtime.py`。
3. `run_episode(...)` 第一版外层使用 async 接口，内部可以暂时包同步逻辑。
4. `LLMGateway.route` 唯一枚举固定为 `verl`、`openai`、`deepseek`、`local_vllm`、`local_sglang`、`replay`、`mock`；route=verl 的内部后端用 `inference_backend` 表示。
5. `training_fast` 默认不保存完整 raw model response，只保存 hash、大小、截断 preview 和 artifact reference。
6. `training_fast` 禁止保存明文 reasoning / thinking trace；`training_debug` 可以显式开启外部 provider 的调试材料。
7. 环境复用第一版优先做 workspace snapshot 和 dependency cache，warm container pool 后置。
8. macOS 本地 snapshot 第一版使用目录复制作为正确性基线，可选 APFS clone；Linux / Vast.ai 通过 preflight 选择 `cp --reflink=auto`、overlayfs、Docker volume snapshot 或安全回退。
9. no-progress 默认标记 `invalid_for_training=True`；只有显式 reward policy 才能把部分 no-progress 当作 negative sample。
10. adapter 包第一版放在独立 `src/repo_harness_verl/`，通过可选 extra 安装。
11. Stage 11.5 是 Stage 12 的前置阶段。只有 `real_episode` runtime bridge 跑通真实 workspace、tool、verifier、reward 和 artifact 路径后，Stage 12 才能声称端到端 smoke。
12. `runtime_execution_mode=minimal_gateway` 继续用于 contract、adapter 和 DataProto 结构测试，但不能作为完整软件工程任务闭环的验收依据。
13. GPU / Vast.ai 真实训练前验收第一版以 SGLang smoke 为主，同时保留 vLLM contract parity smoke；若镜像条件相反，可以先跑 vLLM，但必须记录 preflight 原因。
14. Stage 12-B 第一轮真实模型 smoke 建议从 `Qwen2.5-Coder-7B-Instruct` 或同等级别小型 code instruct model 开始，并使用极小仓库任务调试链路。
15. 正式 PPO / GRPO smoke 不允许 `response_logprobs=None`；fake logprobs 只允许用于 Mac 本地 debug smoke。
16. `AuditRef` 内部保持结构化对象；进入 `AgentLoopOutput.extra_fields` 时采用 namespaced flat scalar 字段，例如 `repo_harness_episode_id`、`repo_harness_run_id`、`repo_harness_audit_manifest_ref`、`repo_harness_timing_summary_ref` 和 `repo_harness_resource_summary_ref`。不要把绝对 `run_dir` 直接放入 verl batch。
17. 正式 online PPO / GRPO 路径只允许 route=verl；provider route 默认 `invalid_for_online_rl=true`，主要用于 SFT export、preference data、teacher data generation 和 offline diagnostic replay。
18. Vast.ai preflight 必须记录 verl commit、Python、Ray、vLLM、SGLang、transformers、torch、tokenizer / chat template 来源和镜像信息。
19. Stage 12.5 是 Stage 13 的本地实现和同步高吞吐基线前置阶段。只有依赖环境缓存、共享 workspace cache、verifier pool 默认接入、recorder hot path 和吞吐 profile 建立后，Stage 13 才能把 fully async 作为吞吐演进，而不是用异步包装未加速的同步瓶颈。
20. Stage 12.6 是 Stage 13 的远端回归前置阶段。Stage 12.5 提交后必须在远端 GPU 环境重新跑真实 RL 链路 smoke，确认共享依赖环境、隐藏 runtime 目录、命令策略、formal batch validator、batch refill、DataProto 和 trainer 小步路径仍然完整可用。
21. Stage 13 必须按 `13.0 -> 13.1 -> 13.2 -> 13.3-A -> 13.3-B` 顺序推进。每个子阶段都要先编写独立实施计划文档，审查通过后再实现；实现完成并通过对应本地或远端验收后，才能进入下一个子阶段。不能把 contract hardening、RepoHarness async episode facade、verl fully async Rollouter / MessageQueue 结构桥接、fully async runtime adapter 本地实现和远端多步 fully async smoke 合并成一次大改。
22. Stage 14 必须按 `14.0 -> 14.1 -> 14.2 -> 14.3` 顺序推进。先做 fully async 远端链路可复现验收和多任务扩展，再做 partial checkpoint contract 和 pause / resume facade；不能在 checkpoint / resume contract 稳定前把 `partial_rollout=True` 样本放进 policy loss。
23. Stage 15 的自然主线是：在 Stage 14 的 checkpoint / resume contract 和 pause / resume facade 通过后，进入真实 verl `partial_rollout=True` 的远端 smoke。Stage 15 不能被旧 CLI / offline export 迁移任务占用。
24. 传统 `repo-harness run-task`、`run-batch`、`run-experiment` 和离线 export 目前仍可继续沿用旧 `evaluation.runner.run_task(...)` 与 run directory 契约。它们和 `RepoHarnessRuntime.run_episode(...)` 的统一属于 Stage 16 或独立路线，不能在 Stage 14 或 Stage 15 中顺手替换。

## 22. 最小成功定义

第一版成功不是“训练出模型”，而是完成下面闭环：

```text
一条软件工程任务
  -> RepoHarnessRuntime.run_episode(...)
  -> real_episode runtime bridge
  -> isolated workspace / tools / multi-turn agent loop
  -> real final verifier
  -> reward boundary
  -> training_fast artifact
  -> reward_score
  -> TrainingView
  -> AgentLoopOutput
  -> verl postprocess
  -> DataProto
  -> visibility gate / invalid sample filtering
  -> 可进入 PPO/GRPO trainer 的 batch
  -> 可以通过 opaque audit refs 和结构化 AuditRef 回查完整轨迹证据
```

如果这个闭环跑通，并且 timing/resource summary 能说明主要瓶颈，才进入 Stage 13.0 的 fully async contract hardening。只有 Stage 13.3-B 远端 GPU 多步 fully async smoke 通过后，才能把 RepoHarness 接入 verl fully async agentic RL 链路视为第一版成立。Stage 14 的成功定义是在这个第一版成立的基础上，进一步证明链路可以脚本化复现、机器验收、多任务扩展，并为 partial checkpoint / resume 提供安全前置。
