# Shared Contract 06：Contract Hardening V1

本文档把审查报告中要求前置的硬性规则集中成一个 gate。它不新增新的高层对象，而是约束 `RepoHarnessEpisodeRequest`、`RepoHarnessEpisodeResult`、`LLMGatewayRequest`、`LLMGatewayResponse`、`TrainingView`、`GenerationRecord`、`AuditRef`、`TimingSummary` 和 `ResourceSummary` 的训练安全边界。

```text
contract_version: repo_harness_verl_shared_contracts_v0
status: design_contract_v0_hardening_gate
scope: planning_only_not_current_implementation
```

## 1. 进入代码实现前必须冻结的规则

Stage 1 代码实现前，必须先通过本 gate。否则容易出现“接口可以跑通，但 token、mask、log probability、reward 或隐藏字段在训练中语义错误”的情况。

必须冻结：

1. 训练张量形状不变量。
2. span 级 token provenance。
3. audit opaque reference 和模型工具不可达性。
4. `kwargs`、`raw_prompt`、TransferQueue 和 DataProto non-tensor fields 的 allowlist。
5. `run_episode(...)` 的取消、超时和资源清理 contract。
6. `training_fast` 的量化吞吐验收。
7. route 枚举、版本锁定和 Mac / Vast.ai 分层验收。

## 2. 训练张量形状不变量

正式 PPO / GRPO batch 必须满足：

```text
len(prompt_ids) <= rollout.prompt_length
0 < len(response_ids) <= rollout.response_length，除非 invalid_for_training=true
len(response_ids) == len(response_mask)
正式 PPO / GRPO batch 中所有样本都必须有 response_logprobs
len(response_logprobs) == len(response_ids)
所有 response_mask=0 的工具 observation token 对应 response_logprobs=0.0
response_ids 为空且 reward_score 非空的样本必须在进入 verl 前被拦截
```

如果超过 `rollout.prompt_length` 或 `rollout.response_length`，第一版不允许静默截断后继续训练。必须写入 `status_reason`、`budget_consumption.stop_reason` 和 audit diagnostics，并默认标记 `invalid_for_training=true`。

Stage 10 和 Stage 12 必须验证：

```text
rollout_log_probs: Tensor[batch_size, rollout.response_length]
rm_scores: 存在，或者 invalid 样本已被过滤
response_mask: Tensor[batch_size, rollout.response_length]
non_tensor_batch: batch 维度对齐
meta_info: 不包含 evaluator-only hidden 字段
```

## 3. Span 级 token provenance

`TrainingView` 或 `RepoHarnessEpisodeResult` 必须携带 `response_spans`。每段至少包含：

```text
start
end
source_type
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

多轮工具调用 canonical fixture 必须覆盖：

```text
初始 prompt
assistant 生成工具调用
tool observation
下一轮 assistant 最终回答
response_ids
response_mask
response_logprobs
response_spans
GenerationRecord
```

route=verl 时，不能在 episode 结束后使用最终 transcript 重新分词伪造正式训练 token。`GenerationRecord.prompt_ids` 必须等于当轮传给 `LLMServerClient.generate(...)` 的 token ids，`GenerationRecord.output_token_ids` 必须等于当轮 `TokenOutput.token_ids`。

## 4. Audit opaque reference 和模型工具不可达性

完整 `AuditRef` 留在 `RepoHarnessEpisodeResult.audit_ref` 和 audit artifact 中。进入 verl batch 的只允许 `repo_harness_*` namespaced flat scalar 和 opaque refs。

允许进入 `AgentLoopOutput.extra_fields` 的示例：

```text
repo_harness_episode_id
repo_harness_run_id
repo_harness_task_id
repo_harness_audit_manifest_ref
repo_harness_reward_metadata_ref
repo_harness_final_verifier_ref
repo_harness_patch_ref
repo_harness_timing_summary_ref
repo_harness_resource_summary_ref
repo_harness_status
repo_harness_invalid_for_training
repo_harness_invalid_reason
```

禁止进入 verl batch：

```text
嵌套 AuditRef 对象
绝对 run_dir
reward metadata 本地绝对路径
final verifier 本地绝对路径
gold patch 路径
hidden test selector
provider secret
evaluator-only raw output
```

audit artifact 必须位于模型 workspace 之外。Stage 12 visibility test 必须模拟模型工具访问 run directory、reward metadata、final verifier artifact、hidden selector、hidden test patch、gold patch 和 evaluator-only raw output，并稳定拒绝。

## 5. kwargs、raw_prompt、TransferQueue 和 DataProto 可见性

`RepoHarnessVerlAgentLoop` 构造 `RepoHarnessEpisodeRequest` 时必须使用 allowlist，而不是 denylist。第一版允许：

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

`raw_prompt` 只允许模型可见内容。普通 `AgentLoopWorker._agent_loop_postprocess(...)` 和 `main_ppo_sync.py` / TransferQueue 路径都必须做 visibility test。最终 `DataProto.tensor_batch`、`DataProto.non_tensor_batch` 和 `meta_info` 都不能携带 hidden verifier、gold patch、完整 reward metadata、accepted label 或 evaluator-only logs。

## 6. cancellation / timeout / cleanup contract

`RepoHarnessRuntime.run_episode(...)` 从 Stage 2 开始就必须定义取消、超时和资源清理规则。

要求：

1. 内部必须有 `try/finally` 或等价资源保护。
2. 外层 coroutine 取消、episode timeout、provider timeout、verifier timeout、Docker command timeout、workspace cleanup 失败都必须有明确 ownership。
3. cleanup 失败不能覆盖原始 episode 状态，但必须写入 diagnostics 和 `ResourceSummary.cleanup_status`。
4. executor 最大并发数必须受 Ray worker、CPU、Docker daemon、file descriptor 和 verifier worker pool 限制约束。
5. cancellation smoke 必须在 agent loop 中途取消后，检查 workspace lease、container lease、artifact manifest、artifact writer、verifier future 和 cleanup diagnostics。

第一版默认：取消后优先返回 `EpisodeResult(status=cancelled, invalid_for_training=true)`；只有无法构造最小 result 的基础设施崩溃才向外抛出异常。

## 7. training_fast 量化验收

`training_fast` 不能只写“体积明显下降”，必须有量化 gate：

```text
同一任务 training_fast artifact bytes 比 full_audit 下降至少 50%，或者逐类说明为什么无法达到
fake gateway 下 8 条最小 episode 并发运行，非模型 p95 wall time 低于人工配置阈值
第一版默认阈值：180 秒
每条 TimingSummary 解释至少 95% 的 outer wall time
```

如果 artifact 写入仍然占比较高，可以引入异步或批量 artifact writer。但 crash 后必须仍能通过 audit ref 找到关键证据，或者把 sample 明确标记为 invalid。

## 8. route、版本和两层验收

唯一 route 枚举：

```text
verl
openai
deepseek
local_vllm
local_sglang
replay
mock
```

`route=verl` 的真实推理后端通过 `inference_backend=sglang|vllm` 表示。正式 online PPO / GRPO 路径只允许 `route=verl`。provider route 默认 `invalid_for_online_rl=true`，主要用于评测、SFT export、preference data、teacher data generation 和 offline diagnostic replay。

Stage 0 必须记录版本治理矩阵：

```text
verl_commit
Python
Ray
vLLM
SGLang
transformers
torch
tokenizer / processor / chat template 来源
镜像信息
```

验收分两层：

```text
Mac 本地：
  fake / mock gateway、fake LLMServerClient、schema、converter、visibility 和 DataProto shape 结构验收。

Vast.ai 或同类 Linux GPU 环境：
  真实 verl server manager、真实 vLLM / SGLang、真实 TokenOutput.token_ids / log_probs、Ray GPU scheduling、PPO / GRPO batch smoke。
```

Mac 本地通过只说明接口正确；Vast.ai 真实 smoke 通过后，才说明训练前可用。
