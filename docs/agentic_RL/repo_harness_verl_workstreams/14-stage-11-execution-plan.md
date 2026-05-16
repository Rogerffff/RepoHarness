# Stage 11 执行计划：RepoHarnessVerlAgentLoop 与 VerlLLMGateway

状态：已实施并通过本地验证和 sub agent 只读复核。本文件记录 Stage 11 的执行计划、边界和验收要求。

前置状态：

- Stage 0H 到 Stage 9 已完成，并且已经提交。
- Stage 10 已完成 `TrainingView -> AgentLoopOutput` 转换、verl postprocess visibility、TransferQueue visibility、DataProto shape smoke 和正式 online RL batch 闸门，提交为 `3fe6b065 feat: add stage10 verl output conversion`。
- 当前阶段可以开始实现真正的 verl adapter，但仍然不能启动真实 Ray、vLLM、SGLang 或完整 PPO / GRPO trainer smoke。这些留到 Stage 12。

## 1. 阶段目标

Stage 11 的目标是在 Stage 10 converter 之上，实现两个真正的 verl adapter 组件：

```text
RepoHarnessVerlAgentLoop(AgentLoopBase)
VerlLLMGateway
```

目标数据流是：

```text
verl sample kwargs / sampling_params
  -> Stage 11 kwargs allowlist 和 visibility 检查
  -> RepoHarnessEpisodeRequest
  -> RepoHarnessVerlAgentLoop.run(...)
  -> VerlLLMGateway
  -> verl LLMServerClient.generate(...)
  -> LLMGatewayResponse
  -> RepoHarnessRuntime.run_episode(...)
  -> RepoHarnessEpisodeResult
  -> Stage 10 episode_result_to_agent_loop_output(...)
  -> AgentLoopOutput
```

完成后应该能证明：

1. `RepoHarnessVerlAgentLoop.run(...)` 可以从 verl 传入的 `sampling_params` 和 `kwargs` 构造安全的 `RepoHarnessEpisodeRequest`。
2. `VerlLLMGateway` 可以包装 verl 已经管理的 `LLMServerClient.generate(...)`，并把返回的 token ids、log probabilities、stop reason、policy metadata 和 `extra_fields` 转成正式 `LLMGatewayResponse`。
3. route=`verl` 的 prompt token 和 response token 有可追溯来源：`GenerationRecord.prompt_ids` 必须等于当轮传给 `LLMServerClient.generate(...)` 的 `prompt_ids`，`GenerationRecord.output_token_ids` 必须等于当轮返回的 `TokenOutput.token_ids`。
4. sticky session 使用 episode 级稳定 `request_id`，不能混淆 verl server 内部每轮生成请求使用的临时 request id。
5. Stage 10 已经固定的 `AgentLoopOutput`、TransferQueue、DataProto 和 visibility 规则继续生效，不因为 Stage 11 adapter 接入而放松。

## 2. 必须保持的边界

1. Stage 11 不实现真实 Ray actor 调度，不启动 vLLM / SGLang server，不做完整 trainer 端到端训练，不做 Vast.ai GPU 验收。这些内容留给 Stage 12。
2. Stage 11 不重写 RepoHarness runtime，不绕过 `RepoHarnessRuntime.run_episode(...)`，不直接调用 CLI 级 `run_task(...)` 作为 adapter 主路径。
3. `src/repo_harness/rl/` 仍然不能静态 import `verl`。所有依赖 `AgentLoopBase`、`AgentLoopOutput`、`LLMServerClient` 或 `TokenOutput` 的代码必须放在可选 adapter 包 `src/repo_harness_verl/` 中。
4. `src/repo_harness_verl/__init__.py` 不能 eager import 需要完整 verl 依赖的 heavy module。普通 RepoHarness CLI import 不能因为安装了 adapter 包而强制安装 `torch`、`ray`、`tensordict` 或完整 verl 依赖。
5. `VerlLLMGateway` 不启动、不停止、不重建 verl server，只调用外部传入的 `LLMServerClient` 或兼容 fake client。
6. Stage 11 不通过最终 assistant 文本重新分词伪造正式训练 token。prompt ids 只能来自当前 turn 实际传给 `LLMServerClient.generate(...)` 的 token 列表，response ids 和 response log probabilities 只能来自当轮 `TokenOutput`。
7. `mock`、`replay`、`openai`、`deepseek`、`local_vllm` 和 `local_sglang` 仍不能进入 formal online RL 样本。Stage 11 adapter 主路径默认构造 route=`verl`。
8. invalid、timeout、infrastructure error 或缺失 log probability 的 episode 不能被 adapter 悄悄转换成可训练 `AgentLoopOutput`。第一版采取保守策略：formal online RL 输出失败时抛出结构化 adapter error，Stage 12 再决定 trainer 侧是丢弃、重采样还是做 diagnostic-only 输出。

## 3. 建议新增或扩展的模块

建议继续使用可选 adapter 包：

```text
src/repo_harness_verl/
  __init__.py
  agent_loop.py
  gateway.py
  request_mapping.py
  errors.py
```

职责建议：

```text
agent_loop.py:
  RepoHarnessVerlAgentLoop(AgentLoopBase)
  Hydra / verl agent loop registry 注册
  async run(sampling_params, **kwargs) -> AgentLoopOutput

gateway.py:
  VerlLLMGateway
  VerlLLMGatewayOptions
  token_output_to_llm_gateway_response(...)
  prompt message -> prompt_ids 构造边界

request_mapping.py:
  RepoHarnessVerlSample
  validate_repo_harness_verl_kwargs(...)
  build_episode_request_from_verl_kwargs(...)
  build_safe_episode_identifiers(...)

errors.py:
  RepoHarnessVerlAdapterError
  RepoHarnessVerlRequestMappingError
  RepoHarnessVerlGatewayError
```

导入策略：

- `repo_harness_verl.agent_loop` 可以 import `verl.experimental.agent_loop.agent_loop.AgentLoopBase` 和 `register`。
- `repo_harness_verl.gateway` 可以使用结构化 duck typing 支持 fake `LLMServerClient`，测试中不要求启动真实 server。
- `repo_harness_verl.conversion` 继续作为 Stage 10 converter，不在 Stage 11 中重新定义 `AgentLoopOutput` 映射。
- `repo_harness.rl` 不能 import `repo_harness_verl`，避免 core 反向依赖 adapter。

## 4. RepoHarnessVerlAgentLoop 设计

建议第一版实现：

```python
class RepoHarnessVerlAgentLoop(AgentLoopBase):
    async def run(self, sampling_params: dict[str, Any], **kwargs: Any) -> AgentLoopOutput:
        validate_repo_harness_verl_kwargs(kwargs)
        request = build_episode_request_from_verl_kwargs(
            kwargs,
            sampling_params=sampling_params,
            trainer_config=self.config,
            rollout_config=self.rollout_config,
        )
        gateway = VerlLLMGateway(
            server_manager=self.server_manager,
            tokenizer=self.tokenizer,
            processor=self.processor,
            inference_backend=request.inference_backend,
            sampling_params=sampling_params,
            prompt_ids_builder=self._build_prompt_ids_for_gateway_request,
        )
        result = await self.runtime.run_episode(request, llm_gateway=gateway)
        return episode_result_to_agent_loop_output(result, formal_online_rl=True)
```

实现要点：

1. `RepoHarnessVerlAgentLoop` 应继承真实 `AgentLoopBase`，并沿用它的 `trainer_config`、`server_manager`、`tokenizer`、`processor`、`dataset_cls` 和 `data_config` 初始化参数。
2. 为单元测试和 fake smoke 预留 `runtime` 注入点。测试可以传入 fake runtime，真实路径默认构造 `RepoHarnessRuntime`。
3. `run(...)` 必须是异步函数，不能把同步 runtime 或同步 gateway 调用直接阻塞在 event loop 里。当前 `RepoHarnessRuntime.run_episode(...)` 已经是异步入口，应直接 await。
4. `run(...)` 返回前必须使用 Stage 10 `episode_result_to_agent_loop_output(...)`。不要在 Stage 11 重写 reward placement、response mask、rollout log probability 或 `extra_fields` 规则。
5. adapter 不能自己写 `output.extra_fields["raw_prompt"]`。普通 verl worker 会在 `_agent_loop_postprocess(...)` 中从 `kwargs["raw_prompt"]` 自动写入，TransferQueue 路径会把 `raw_prompt` 作为顶层字段合并。
6. 如果 `episode_result_to_agent_loop_output(...)` 拒绝 invalid 样本，Stage 11 第一版应抛出 `RepoHarnessVerlAdapterError`，并保留 `episode_id`、`run_id`、`status` 和 `status_reason` 作为异常诊断字段，不能返回看起来可训练的假样本。

## 5. kwargs 白名单和 request 构造

`RepoHarnessVerlAgentLoop` 构造 `RepoHarnessEpisodeRequest` 时必须使用白名单，而不是黑名单。第一版需要区分两层字段：

1. **request 构造字段**：允许进入 `RepoHarnessEpisodeRequest`，或者用于构造其中的安全标识符。
2. **verl worker / TransferQueue 控制字段**：允许真实 verl worker、TransferQueue 或 trace 使用，但默认不能进入 `RepoHarnessEpisodeRequest.raw_prompt`、模型可见内容、`TrainingView.extra_fields` 或 `AgentLoopOutput.extra_fields`。如果需要用于派生 `episode_id` / `run_id`，只能使用经过类型校验和安全标识符归一化后的值。

第一层 request 构造字段只允许：

```text
raw_prompt
agent_name
task_id
repo_harness_task_id
repo_harness_task_ref
repo_harness_run_config_ref
repo_harness_budget_ref
repo_harness_agent_policy_ref
repo_harness_episode_seed
repo_harness_run_mode
repo_harness_dataset_name
repo_harness_dataset_split
repo_harness_dataset_revision
```

第二层 verl worker / TransferQueue 控制字段只允许：

```text
index
uid
session_id
global_steps
```

兼容说明：

- `task_id` 可以作为 verl dataset 侧普通字段接收，但构造 request 后应投影到 `RepoHarnessEpisodeRequest.task_id`。
- 新增字段优先使用 `repo_harness_*` namespace，避免和 verl 自身字段或 dataset 字段冲突。
- `raw_prompt` 只能包含模型可见内容。必须复用 Stage 10 visibility helper，确保 hidden verifier、gold patch、accepted label、provider secret、完整 reward metadata、evaluator-only logs 和本地绝对路径都不能出现在 `raw_prompt` 中。
- `index` 是真实 `AgentLoopWorker.generate_sequences(...)` 使用的样本分组字段，类型必须是整数或可安全转换为整数的标量。它可以用于派生 `episode_id` / `run_id`，但不能作为模型可见内容。
- `uid` 是 `main_ppo_sync.py` / TransferQueue 路径使用的样本唯一标识，类型必须是字符串或可安全字符串化的标量，并且归一化后必须通过安全标识符校验。它可以作为 opaque rollout 控制字段传播，但不能包含本地路径、reward 信息或 evaluator-only 内容。
- `session_id` 是 `main_ppo_sync.py` 路径区分同一 prompt 多个 rollout session 的控制字段，第一版只接受整数。它可以参与派生 `episode_id`，但不能进入模型可见 prompt。
- `global_steps` 是 trainer 当前步数，类型必须是非负整数。它可以作为 trace / diagnostics / gateway metadata 使用，但不能进入 `RepoHarnessEpisodeRequest.raw_prompt`，也不能覆盖 `TokenOutput.extra_fields.global_steps` 的事实来源。
- Stage 11 如果扩展 Stage 10 的 TransferQueue visibility helper 来允许 `uid`、`index`、`session_id` 和 `global_steps`，必须保持 flat scalar 限制，并继续拒绝这些字段下的嵌套 dict / list。
- `repo_harness_model_visible_context_refs` 暂不进入 Stage 11 第一版 allowlist。后续如果 schema 明确增加模型可见 context refs 投影字段，再重新启用；当前直接拒绝，避免调用方误以为该字段已经生效。

必须拒绝：

```text
hidden_verifier
gold_patch
accepted_label
provider_secret
evaluator_only_logs
complete_reward_metadata
reward_model
ground_truth
reward_extra_info
reward_extra_keys
extra_info
audit_ref
run_dir
final_verifier_path
reward_metadata_path
```

还必须复用 Stage 10 的 TransferQueue reserved-key 规则，拒绝 `kwargs` 覆盖这些训练关键字段：

```text
prompts
responses
response_mask
rollout_log_probs
rm_scores
extra_fields
teacher_ids
teacher_logprobs
loss_mask
input_ids
position_ids
multi_modal_inputs
```

request 映射规则：

1. `episode_id` 和 `run_id` 必须是安全标识符。若 `kwargs` 没有显式给出，第一版可以从 `task_id`、`index`、`uid`、`session_id`、`global_steps` 或随机短 id 构造，但必须先完成类型校验、归一化和 `validate_safe_identifier(...)`。
2. `task_ref.task_path` 不能接受绝对本地路径。真实本地路径只能由 runtime-only resolver 或 `RepoHarnessRuntimeOptions` 持有，不能通过可传播 request schema 进入 batch。
3. `llm_gateway_route` 固定为 `verl`。
4. `inference_backend` 必须从明确配置读取，第一版只允许 `sglang` 或 `vllm`。缺失时应拒绝 request，而不是猜测。
5. `run_mode` 默认使用 `training_fast`，除非配置或样本明确指定并通过 allowlist。
6. `EpisodeBudgets.max_output_tokens` 应从 `sampling_params` 和 rollout response length 中取更严格的边界，不能让单条样本无限生成。
7. `visibility_policy` 只能描述模型可见和 batch 可传播字段，不允许携带 evaluator-only 明文。

## 6. VerlLLMGateway 设计

`VerlLLMGateway` 的职责是把 RepoHarness 的 `LLMGatewayRequest` 转成 verl `LLMServerClient.generate(...)` 调用，再把 `TokenOutput` 转回 `LLMGatewayResponse`。

建议接口：

```python
class VerlLLMGateway:
    async def generate_turn(self, request: LLMGatewayRequest) -> LLMGatewayResponse:
        prompt_ids = await self.prompt_ids_builder(request)
        token_output = await self.server_manager.generate(
            request_id=request.sticky_session_id or request.episode_id,
            prompt_ids=prompt_ids,
            sampling_params=merged_sampling_params,
            image_data=image_data,
            video_data=video_data,
        )
        return token_output_to_llm_gateway_response(...)
```

关键规则：

1. `request.route` 必须是 `verl`，`request.inference_backend` 必须是 `sglang` 或 `vllm`。
2. prompt ids 的构造由 adapter 层负责，并且必须使用当前 verl tokenizer / processor / chat template 的同一条路径。第一版可以通过 `RepoHarnessVerlAgentLoop` 注入 `prompt_ids_builder`，内部复用 `AgentLoopBase.apply_chat_template(...)` 或等价 tokenizer helper。
3. 不能在 episode 结束后用最终 transcript 重新分词来生成 `prompt_ids`。每一轮 `LLMGatewayResponse.prompt_ids` 必须等于当轮实际传给 `LLMServerClient.generate(...)` 的列表。
4. `LLMServerClient.generate(...)` 的 `request_id` 使用 `request.sticky_session_id or request.episode_id`，保证同一 episode 多轮请求尽量落到同一个后端 server。不要使用 server 内部每轮生成 request id 作为 sticky session id。
5. `TokenOutput.token_ids` 映射为 `LLMGatewayResponse.output_token_ids`。
6. `TokenOutput.log_probs` 映射为 `LLMGatewayResponse.output_logprobs`。如果缺失，必须返回 structured error 或让 runtime 标记为不可 online RL，不能伪造 log probability。
7. `LLMGatewayResponse.response_mask` 必须全部为 `1`。工具 observation token 只能由 episode 级 `TrainingView` 拼接，并使用 `response_mask=0`。
8. `TokenOutput.extra_fields` 中的 `global_steps`、`min_global_steps`、`max_global_steps` 可以投影到 `LLMGatewayResponse` 对应字段。其他字段不能只依赖 core 的 `validate_gateway_extra_fields(...)`，因为该 helper 不是 Stage 10 的嵌套 TransferQueue / DataProto 严格检查。Stage 11 必须新增 adapter 专用 helper，或复用 Stage 10 的递归可见性规则，递归拒绝 `ground_truth`、`groundTruth`、`reward_extra_info`、`rewardExtraInfo`、`reward_extra_keys`、`extra_info`、完整 reward metadata、accepted label、hidden verifier、gold patch、provider secret 和 evaluator-only logs。
9. `TokenOutput.routed_experts` 如果存在，可以进入 `LLMGatewayResponse.routed_experts`，用于后续分析；它不能变成模型可见 prompt。
10. `TokenOutput.num_preempted` 当前没有 `LLMGatewayResponse` 或 `GenerationRecord` 的正式字段。Stage 11 第一版不承诺把它保存进 `GenerationRecord`，也不承诺自动进入 `TrainingView.verl_metrics["num_preempted"]`。如果实现需要保留它，只能作为 gateway-only flat scalar diagnostic，例如 `LLMGatewayResponse.extra_fields["num_preempted"]`，并且必须通过 adapter 专用 visibility helper；后续如果要让它进入 `AgentLoopMetrics.num_preempted`，需要新增显式 runtime 投影路径和测试，不能靠隐式 extra fields。
11. `assistant_message.content` 可以用 tokenizer decode 由 `output_token_ids` 得到，供 RepoHarness agent loop 继续解析工具调用或最终回答。decode 只能服务交互文本，不是训练 token 的来源。
12. `duration_ms` 应记录实际 `LLMServerClient.generate(...)` 调用耗时，而不是 provider 报告值或硬编码值。

## 7. Hydra / verl 注册

Stage 11 需要让 verl 能通过配置找到 `RepoHarnessVerlAgentLoop`。

建议实现：

```python
from verl.experimental.agent_loop.agent_loop import register

@register("repo_harness")
class RepoHarnessVerlAgentLoop(AgentLoopBase):
    ...
```

同时准备最小配置说明或测试 fixture。当前 `reference/verl` 的真实自定义 agent loop 配置入口是：

```text
rollout.agent.agent_loop_config_path
```

该路径指向一个 agent loop config 列表，每个元素包含 `name` 和 `_target_`。示例：

```yaml
actor_rollout_ref:
  rollout:
    agent:
      default_agent_loop: repo_harness
      agent_loop_config_path: /abs/or/resolved/path/to/repo_harness_agent_loop.yaml
```

`repo_harness_agent_loop.yaml` 示例：

```yaml
- name: repo_harness
  _target_: repo_harness_verl.agent_loop.RepoHarnessVerlAgentLoop
```

`custom_async_server.path` 是自定义 async server 的入口，不是 Stage 11 `AgentLoopBase` adapter 的主要注册入口。计划和测试不能把它当成 `RepoHarnessVerlAgentLoop` 的配置方式。

测试至少要验证在 `PYTHONPATH=src:reference/verl` 且依赖满足时，导入 `repo_harness_verl.agent_loop` 后 registry 中能看到 `repo_harness`，或者通过 `agent_loop_config_path` 指向的配置文件把 `_target_ = repo_harness_verl.agent_loop.RepoHarnessVerlAgentLoop` 加入 registry，并能按当前 verl 注册机制实例化该类。

普通 RepoHarness CLI import 只应触发 `repo_harness` 和 `repo_harness.rl`，不应触发 `repo_harness_verl.agent_loop` 的 heavy import。

## 8. fake LLMServerClient smoke

Stage 11 的本地 Mac smoke 不需要真实 vLLM / SGLang server，但必须使用和真实 `LLMServerClient.generate(...)` 一致的 async 签名：

```python
async def generate(
    self,
    request_id: str,
    *,
    prompt_ids: list[int],
    sampling_params: dict[str, Any],
    image_data: list[Any] | None = None,
    video_data: list[Any] | None = None,
    **kwargs: Any,
) -> TokenOutputLike:
    ...
```

fake `TokenOutputLike` 至少包含：

```text
token_ids
log_probs
stop_reason
extra_fields
num_preempted
routed_experts
```

必须验证：

1. fake client 收到的 `request_id` 等于 `episode_id` 或明确的 `sticky_session_id`。
2. fake client 收到的 `prompt_ids` 等于 gateway response 和 `GenerationRecord` 中记录的 `prompt_ids`。
3. fake client 返回的 `token_ids`、`log_probs`、`stop_reason`、`global_steps` 和 `routed_experts` 能进入 `LLMGatewayResponse`；其中 `prompt_ids`、`token_ids`、`log_probs`、`stop_reason`、route 和 backend 进入 `GenerationRecord`。
4. fake client 返回的 `num_preempted` 只作为 gateway-only diagnostic 或暂不保存，不能被测试写成“进入 `GenerationRecord`”。
5. fake client 缺失 `log_probs` 时，adapter 不会生成 formal online RL 可训练输出。
6. fake client 不应该暴露 `start_server`、`stop_server` 或重建 server 的调用路径；如果 fake 上有这些方法，测试要确认 Stage 11 adapter 没有调用它们。

## 9. 测试计划

建议新增：

```text
tests/unit/test_repo_harness_verl_stage11_request_mapping.py
tests/unit/test_repo_harness_verl_stage11_gateway.py
tests/unit/test_repo_harness_verl_stage11_agent_loop.py
```

必须覆盖：

1. `validate_repo_harness_verl_kwargs(...)` 接受最小安全 kwargs，并拒绝 hidden verifier、gold patch、accepted label、complete reward metadata、provider secret、evaluator-only logs 和本地绝对路径。
2. `validate_repo_harness_verl_kwargs(...)` 接受真实 verl worker / TransferQueue 控制字段 `index`、`uid`、`session_id` 和 `global_steps`，并验证它们是 flat scalar、类型正确、不会进入模型可见内容。
3. `validate_repo_harness_verl_kwargs(...)` 拒绝 Stage 10 reserved training fields，例如 `prompts`、`responses`、`response_mask`、`rollout_log_probs`、`rm_scores`、`extra_fields`、`teacher_ids`、`teacher_logprobs`、`loss_mask`、`input_ids`、`position_ids` 和 `multi_modal_inputs`。
4. `build_episode_request_from_verl_kwargs(...)` 构造 route=`verl`、合法 `inference_backend`、安全 `episode_id` / `run_id`、相对 `task_ref` 和 `training_fast` 默认 run mode。
5. 绝对 `task_path` 被拒绝，不能进入 `RepoHarnessEpisodeRequest`。
6. 缺失或非法 `inference_backend` 被拒绝，不能默认猜成 `vllm` 或 `sglang`。
7. `VerlLLMGateway.generate_turn(...)` 使用 fake `LLMServerClient.generate(...)` 的 async 签名，并传入 sticky `request_id`。
8. `VerlLLMGateway.generate_turn(...)` 返回的 `LLMGatewayResponse.prompt_ids` 等于 fake client 实际收到的 `prompt_ids`。
9. fake `TokenOutput.token_ids`、`log_probs`、`stop_reason`、`extra_fields.global_steps` 和 `routed_experts` 被正确投影。
10. fake `TokenOutput.num_preempted` 不会被错误断言为 `GenerationRecord` 字段；如保留，只能作为 gateway-only diagnostic。
11. `TokenOutput.log_probs=None` 时，结果不能进入 formal online RL converter。
12. `TokenOutput.extra_fields` 中出现 reward metadata、ground truth、groundTruth、reward_extra_info、rewardExtraInfo、reward_extra_keys、extra_info 或 evaluator-only 字段时被递归拒绝。
13. `RepoHarnessVerlAgentLoop.run(...)` 在 fake runtime + fake gateway 路径下返回真实 `AgentLoopOutput`，并可继续通过 Stage 10 postprocess visibility 测试。
14. `RepoHarnessVerlAgentLoop.run(...)` 不写 `extra_fields.raw_prompt`，由真实 verl postprocess 后再写入并检查 visibility。
15. Hydra / verl registry 能通过 `agent_loop_config_path` 或当前注册机制找到 `repo_harness` agent loop。
16. `src/repo_harness/rl` 无 `import verl` 或 `from verl`。
17. 普通 `python -c "import repo_harness.rl"` 不需要导入 `repo_harness_verl.agent_loop`。

## 10. 验收命令

Stage 11 完成时至少运行：

```bash
PYTHONPATH=src uv run --extra dev python -m compileall -q src

PYTHONPATH=src uv run --extra dev python - <<'PY'
import repo_harness.rl
import repo_harness_verl
print("ordinary_import_ok")
PY

PYTHONPATH=src uv run --extra dev python -m pytest -q \
  tests/unit/test_repo_harness_verl_contract_fixtures.py \
  tests/unit/test_repo_harness_verl_stage0h_shape_rules.py \
  tests/unit/test_repo_harness_verl_stage0h_visibility.py \
  tests/unit/test_repo_harness_rl_stage1_schema_roundtrip.py \
  tests/unit/test_repo_harness_rl_stage1_visibility_gateway.py \
  tests/unit/test_repo_harness_rl_stage2_runtime.py \
  tests/unit/test_repo_harness_rl_stage3_training_fast_recorder.py \
  tests/unit/test_repo_harness_rl_stage4_timing_resource.py \
  tests/unit/test_repo_harness_rl_stage5_gateway_routes.py \
  tests/unit/test_repo_harness_rl_stage5_provider_gateway.py \
  tests/unit/test_workspace_reuse_stage6.py \
  tests/unit/test_repo_harness_rl_stage6_resource_summary.py \
  tests/unit/test_repo_harness_rl_stage7_reward_boundary.py \
  tests/unit/test_verifier_worker_pool_stage7.py \
  tests/unit/test_repo_harness_rl_stage8_budget_policy.py \
  tests/unit/test_agent_loop_stage8_no_progress_stop.py \
  tests/unit/test_context_stage8_training_slimming.py \
  tests/unit/test_repo_harness_rl_stage9_resource_leases.py \
  tests/unit/test_repo_harness_rl_stage9_concurrency_runtime.py

PYTHONPATH=src:reference/verl uv run --extra dev \
  --with packaging \
  --with numpy \
  --with torch \
  --with tensordict \
  --with ray \
  --with hydra-core \
  --with omegaconf \
  --with pillow \
  --with transformers \
  --with codetiming \
  --with datasets \
  --with cachetools \
  --with uvicorn \
  --with fastapi \
  python - <<'PY'
from verl.experimental.agent_loop.agent_loop import AgentLoopBase, AgentLoopOutput, AgentLoopMetrics
from verl.workers.rollout.llm_server import LLMServerClient
print(AgentLoopBase, AgentLoopOutput, AgentLoopMetrics, LLMServerClient)
PY

PYTHONPATH=src:reference/verl uv run --extra dev \
  --with packaging \
  --with numpy \
  --with torch \
  --with tensordict \
  --with ray \
  --with hydra-core \
  --with omegaconf \
  --with pillow \
  --with transformers \
  --with codetiming \
  --with datasets \
  --with cachetools \
  --with uvicorn \
  --with fastapi \
  python -m pytest -q \
  tests/unit/test_repo_harness_verl_stage10_agent_loop_output.py \
  tests/unit/test_repo_harness_verl_stage10_postprocess_visibility.py \
  tests/unit/test_repo_harness_verl_stage10_dataproto_shapes.py \
  tests/unit/test_repo_harness_verl_stage11_request_mapping.py \
  tests/unit/test_repo_harness_verl_stage11_gateway.py \
  tests/unit/test_repo_harness_verl_stage11_agent_loop.py

rg -n '(^|\s)(import|from)\s+verl' src/repo_harness/rl && exit 1 || true

git diff --check -- \
  src/repo_harness/rl \
  src/repo_harness_verl \
  tests/unit/test_repo_harness_verl_stage11_request_mapping.py \
  tests/unit/test_repo_harness_verl_stage11_gateway.py \
  tests/unit/test_repo_harness_verl_stage11_agent_loop.py
```

如果 `reference/verl` 的依赖发生变化，执行结果必须记录实际缺少的依赖、补充后的 `uv --with ...` 命令和最终通过的 preflight 输出。不能把真实 verl import preflight 降级成自定义 fake class 测试。

## 11. 阶段出口

Stage 11 完成后必须满足：

1. `RepoHarnessVerlAgentLoop` 可以通过当前 `reference/verl` 的 agent loop 注册机制被发现或实例化。
2. `RepoHarnessVerlAgentLoop.run(...)` 可以从安全 kwargs 构造 `RepoHarnessEpisodeRequest`，并拒绝隐藏评测、完整 reward metadata、gold patch、accepted label、provider secret 和保留训练字段。
3. `VerlLLMGateway` 可以调用 fake `LLMServerClient.generate(...)`，并返回符合 Stage 1 gateway schema 的 `LLMGatewayResponse`。
4. `GenerationRecord.prompt_ids` 等于当轮传给 `LLMServerClient.generate(...)` 的 prompt ids。
5. `GenerationRecord.output_token_ids` 和 `output_logprobs` 等于当轮 `TokenOutput` 返回的 token facts。
6. sticky session 使用 episode 级稳定 `request_id`。
7. adapter 返回真实 `AgentLoopOutput`，并继续通过 Stage 10 `as_dict()`、postprocess、TransferQueue 和 DataProto visibility 检查。
8. 缺失 log probability、非 `verl` route、invalid episode、overflow episode 和 hidden metadata episode 不能进入 formal online RL 输出。
9. `src/repo_harness/rl` 仍然无 verl import，普通 RepoHarness CLI 不需要完整 verl 依赖。
10. Stage 12 可以在此基础上做端到端 smoke、Mac / Vast.ai 分层验收和真实性能 visibility 验收，而不需要重新定义 adapter contract。

## 12. 不进入 Stage 11 的内容

以下内容留到后续阶段：

- Stage 12：真实 verl dataloader sample、真实 `DataProto` trainer smoke、真实 Ray / vLLM / SGLang server smoke、Mac / Vast.ai 分层验收和性能 smoke。
- Stage 13：fully async、partial rollout、中断恢复、参数版本跨越、长期 trajectory 和异步 reward backfill。
- 后续性能优化：warm container pool、跨 episode prefix cache 策略、长期 worker recycle、真实 GPU 吞吐 benchmark。
