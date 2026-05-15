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
Stage 12：端到端 smoke、性能 smoke 和 visibility 验收
Stage 13：为 fully async 演进预留中断、恢复和异步 reward 设计
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
明确声明的模型可见 context refs
```

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
2. `RepoHarnessVerlAgentLoop` 构造 request 时必须对 `kwargs` 使用 allowlist，只允许 `raw_prompt`、`agent_name`、`task_id`、`run_config_ref`、`budget_ref`、`agent_policy_ref`、`episode_seed` 和明确声明的模型可见 context refs。
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

## 15. Stage 12：端到端 smoke、性能 smoke 和 visibility 验收

目标：确认整条链路可以训练消费，而不是只在局部测试通过。

端到端 smoke：

```text
verl dataloader sample
  -> RepoHarnessVerlAgentLoop.run(...)
  -> RepoHarnessRuntime.run_episode(...)
  -> VerlLLMGateway
  -> tool/workspace
  -> final verifier
  -> reward_score
  -> TrainingView
  -> AgentLoopOutput
  -> verl postprocess
  -> DataProto
```

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

### Stage 12-A：Mac 本地结构验收

Mac 本地开发阶段使用 `verl-lite` 验收，不要求安装 vLLM、SGLang、flash-attn、liger-kernel 或 CUDA 相关依赖。它的目标是证明 RepoHarness 和 verl adapter 的接口、字段和训练视图转换正确。

Mac 本地必须通过：

```text
RepoHarnessRuntime.run_episode(...)
  -> fake/mock LLMGateway
  -> TrainingView
  -> AgentLoopOutput
  -> response_ids / response_mask / response_logprobs 长度检查
  -> extra_fields / AuditRef / raw_prompt visibility 检查
```

以及：

```text
RepoHarnessVerlAgentLoop.run(...)
  -> fake LLMServerClient.generate(...)
  -> fake TokenOutput
  -> RepoHarness tool/workspace/verifier/reward
  -> AgentLoopOutput
```

Mac 本地验收边界：

- 可以安装 verl 基础包或使用 `pip install --no-deps -e reference/verl` 加必要最小依赖。
- 不要求启动真实 vLLM / SGLang server。
- 不要求跑真实 PPO / GRPO trainer。
- 不要求验证真实 Ray GPU resource scheduling。
- 允许使用 fake logprobs 做长度和 mask 对齐测试，但这只能算 debug smoke。

### Stage 12-B：Vast.ai GPU 训练前验收

Vast.ai 或其他 Linux GPU 实例负责真实训练前验收。它的目标是证明 route=verl 在真实推理服务和真实 trainer 入口下可用。

Vast.ai 训练前必须通过：

```text
verl server manager
  -> vLLM / SGLang AsyncLLMServer
  -> real LLMServerClient.generate(...)
  -> real TokenOutput.token_ids
  -> real TokenOutput.log_probs
  -> RepoHarnessVerlAgentLoop.run(...)
  -> RepoHarnessRuntime.run_episode(...)
  -> TrainingView
  -> AgentLoopOutput
  -> verl postprocess
  -> DataProto
  -> PPO / GRPO batch smoke
```

Vast.ai 真实验收必须检查：

- tokenizer / processor / chat template 与训练模型一致。
- `response_ids` 来自真实生成路径，不从最终 transcript 重新分词伪造。
- `response_logprobs` 非空，并与 `response_ids`、`response_mask` 长度对齐。
- `rollout_log_probs` 出现在 DataProto tensor batch 中，形状等于 `[batch_size, rollout.response_length]`。
- `rm_scores` 存在，或者样本被明确过滤；invalid 样本不能悄悄参与 policy loss。
- PPO / GRPO smoke 必须记录 `actor_rollout_ref.rollout.calculate_log_probs=True` 或当前 verl 版本等价配置。
- sticky session / prefix cache 的 `request_id` 语义正确。
- Ray actor、server manager、LLM server、RepoHarness workspace worker 可以在同一台或多台 GPU 实例上并发运行。
- workspace snapshot backend 在 Linux 文件系统上通过 preflight；支持 `cp --reflink=auto`、overlayfs、Docker volume snapshot 或安全回退到目录复制。
- `training_fast` artifact 体积下降，但 `AuditRef` 可以回查 run directory、transcript、events、patch、reward 和 timing/resource summary。
- `TimingSummary` 能看到 model/tool/workspace/verifier/artifact 拆分。
- `ResourceSummary` 能看到 inference route、container lease、snapshot key、cache hit 和 verifier worker pool。
- SGLang 真实 smoke 和 vLLM contract smoke 同阶段完成，允许一个作为主验收、另一个作为 parity smoke；如果 Vast.ai 镜像条件只支持其中一个，必须在 preflight 中记录原因和补齐计划。

因此，Mac 本地验收通过只表示“接口正确”；Vast.ai 验收通过才表示“真实训练前可用”。

## 16. Stage 13：fully async 演进预留

目标：第一版先跑通同步 reward 的 agent loop，后续再演进 fully async。

fully async 需要新增或加强：

- episode interrupt / resume contract。
- partial `AgentLoopOutput` 或等价 checkpoint。
- rollout pending queue / processor worker / trainer message queue 的状态边界。
- policy version、`global_steps`、`min_global_steps`、`max_global_steps` 和 staleness 统计。
- async verifier reward backfill。
- cancelled / resumed / stale trajectory 的训练过滤策略。
- workspace lease 在中断、恢复和取消时的生命周期。
- `actor_rollout_ref.actor.use_rollout_log_probs=True` 或当前 verl 版本等价配置的记录。
- `algorithm.rollout_correction.bypass_mode` 的选择记录。
- stale trajectory 的过滤、丢弃或权重策略记录。
- 如果一条 trajectory 跨多个参数版本，必须能按 token span 或 model call span 追踪版本范围。

第一版只需要不阻断这些演进：

- `GenerationRecord` 保留 policy version、`global_steps`、`min_global_steps`、`max_global_steps` 字段。
- `LLMGatewayResponse.extra_fields` 保留 verl `TokenOutput.extra_fields` 中的版本信息。
- `RepoHarnessEpisodeResult.status` 能表达 `cancelled` 和 `timeout`。
- `AuditRef` 能指向恢复所需状态 artifact。
- async reward backfill 第一版不做，但未来实现时不能把无 reward 样本伪装成普通成功样本。

## 17. 已采纳的第一版默认决策

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
11. Vast.ai 真实训练前验收第一版以 SGLang smoke 为主，同时保留 vLLM contract parity smoke；若镜像条件相反，可以先跑 vLLM，但必须记录 preflight 原因。
12. 正式 PPO / GRPO smoke 不允许 `response_logprobs=None`；fake logprobs 只允许用于 Mac 本地 debug smoke。
13. `AuditRef` 内部保持结构化对象；进入 `AgentLoopOutput.extra_fields` 时采用 namespaced flat scalar 字段，例如 `repo_harness_episode_id`、`repo_harness_run_id`、`repo_harness_audit_manifest_ref`、`repo_harness_timing_summary_ref` 和 `repo_harness_resource_summary_ref`。不要把绝对 `run_dir` 直接放入 verl batch。
14. 正式 online PPO / GRPO 路径只允许 route=verl；provider route 默认 `invalid_for_online_rl=true`，主要用于 SFT export、preference data、teacher data generation 和 offline diagnostic replay。
15. Vast.ai preflight 必须记录 verl commit、Python、Ray、vLLM、SGLang、transformers、torch、tokenizer / chat template 来源和镜像信息。

## 18. 最小成功定义

第一版成功不是“训练出模型”，而是完成下面闭环：

```text
一条软件工程任务
  -> RepoHarnessRuntime.run_episode(...)
  -> training_fast artifact
  -> reward_score
  -> TrainingView
  -> AgentLoopOutput
  -> verl postprocess
  -> DataProto
  -> 可进入 PPO/GRPO trainer 的 batch
  -> 可以通过 opaque audit refs 和结构化 AuditRef 回查完整轨迹证据
```

如果这个闭环跑通，并且 timing/resource summary 能说明主要瓶颈，才进入更大规模 rollout 和 fully async 设计。
