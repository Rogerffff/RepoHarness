# Stage 12-A 执行计划：Mac 本地真实 runtime bridge smoke

## 1. 当前本地可测性结论

Stage 12-A 可以先在当前 Mac 本地执行，不需要立刻租用 GPU 实例。原因是 Stage 12-A 的目标不是启动真实 vLLM、SGLang、Ray GPU worker 或 PPO / GRPO trainer，而是验证：

```text
RepoHarnessVerlAgentLoop
-> RepoHarnessRuntime(runtime_execution_mode=real_episode)
-> RepoHarness agent loop
-> VerlLLMGateway
-> fake LLMServerClient
-> real TokenOutput shape
-> tools / final verifier / reward
-> TrainingView
-> real AgentLoopOutput / postprocess / visibility checks
```

本地预检结果：

```text
当前项目默认 uv --extra dev 环境不能直接导入 reference/verl：
缺少 numpy、torch、ray、tensordict 等 verl 依赖。

使用 uv --with 显式补齐 CPU 依赖后：
torch_available 2.12.0
torch.cuda.is_available() == False
AgentLoopOutput / AgentLoopMetrics / AgentLoopBase / AgentLoopWorker / TokenOutput / LLMServerClient 可以导入。
repo_harness_verl.agent_loop 可以导入。
TrainingView -> AgentLoopOutput -> as_dict() 可以产生 CPU tensor。
VerlLLMGateway + fake TokenOutput 可以产生 route=verl 的 LLMGatewayResponse。
```

因此，Stage 12-A 本地验收的正确策略是：

- 使用 CPU 依赖预检命令确认真实 `reference/verl` 接口可导入。
- 不要求安装 CUDA、flash-attn、liger-kernel、vLLM 或 SGLang。
- 不启动真实推理服务。
- 不进入 trainer loss。
- 不把 reference stubs 作为唯一证据；stubs 只能作为补充单元测试工具。

GPU 实例仍然需要留给 Stage 12-B 和 Stage 12-C，用于真实模型、真实推理服务和小 batch trainer smoke。

## 2. 阶段目标

Stage 12-A 的目标是证明本地真实 runtime bridge 和 verl adapter contract 可以连接起来，而不是只证明局部 schema 或 fake facade 可用。

必须完成两条 smoke 路径。

第一条是本地 runtime 诊断路径：

```text
RepoHarnessRuntime.run_episode(...)
-> runtime_execution_mode=real_episode
-> mock / fake LLMGateway
-> 独立 workspace snapshot 和 workspace lease
-> 真实 RepoHarness agent loop
-> 真实工具调用
-> 真实 final verifier
-> Stage 7 reward boundary
-> RepoHarnessEpisodeResult
-> TrainingView / AuditRef / TimingSummary / ResourceSummary
```

这条路径可以使用 `route=mock`，但它只能证明本地真实 RepoHarness episode runtime 可运行。它不能进入 formal online RL converter，也不能作为 PPO / GRPO 可训练样本证据。

第二条是本地 verl adapter 结构路径：

```text
RepoHarnessVerlAgentLoop.run(...)
-> RepoHarnessRuntime.run_episode(...)
-> runtime_execution_mode=real_episode
-> RepoHarness agent loop
-> LLMGatewayModelClientAdapter
-> VerlLLMGateway
-> fake LLMServerClient.generate(...)
-> real TokenOutput shape
-> route=verl 的 LLMGatewayResponse
-> GenerationRecordCollector
-> final verifier / reward
-> TrainingView
-> AgentLoopOutput
-> AgentLoopOutput.as_dict()
-> verl postprocess / TransferQueue / DataProto visibility checks
```

如果要验证 formal online RL conversion，必须使用第二条路径。也就是说，formal 样本必须由 `RepoHarnessVerlAgentLoop + fake LLMServerClient` 产生 `route=verl` 的 token、mask 和 log probability 事实，不能用 `mock` route 或最终 transcript 重新分词伪造。

## 3. 明确不做的事情

Stage 12-A 不做下面这些事情：

- 不启动真实 vLLM server。
- 不启动真实 SGLang server。
- 不启动真实 Ray GPU 集群。
- 不下载或加载真实大模型。
- 不执行 PPO / GRPO trainer loss。
- 不要求模型真实修复任务。
- 不把 `runtime_execution_mode=minimal_gateway` 当成端到端证据。
- 不把 `route=mock` 样本放进 formal online RL batch。

这些内容分别属于 Stage 12-B 或 Stage 12-C。

## 4. 本地依赖预检

新增一个明确的本地预检脚本或测试，建议命名为：

```text
tests/unit/test_repo_harness_verl_stage12a_local_verl_preflight.py
```

预检必须覆盖：

1. 普通 RepoHarness 导入仍然轻量：

```bash
PYTHONPATH=src uv run --extra dev python - <<'PY'
import repo_harness.rl
import repo_harness_verl
print("ordinary_import_ok")
PY
```

这条命令不能要求 `torch`、`ray`、`tensordict` 或 `reference/verl`。

2. 真实 `reference/verl` CPU 依赖导入可用：

```bash
PYTHONPATH=src:reference/verl uv run --extra dev \
  --with numpy \
  --with torch \
  --with ray \
  --with tensordict \
  --with hydra-core \
  --with omegaconf \
  --with pillow \
  --with transformers \
  --with datasets \
  --with torchdata \
  --with codetiming \
  --with cachetools \
  --with uvicorn \
  --with fastapi \
  --with requests \
  --with aiohttp \
  --with prometheus-client \
  python - <<'PY'
import torch
from verl.experimental.agent_loop.agent_loop import (
    AgentLoopBase,
    AgentLoopMetrics,
    AgentLoopOutput,
    AgentLoopWorker,
)
from verl.workers.rollout.replica import TokenOutput
from verl.workers.rollout.llm_server import LLMServerClient

assert torch.cuda.is_available() is False
print(
    "verl_cpu_import_ok",
    AgentLoopOutput.__name__,
    AgentLoopMetrics.__name__,
    AgentLoopBase.__name__,
    AgentLoopWorker.__name__,
    TokenOutput.__name__,
    LLMServerClient.__name__,
)
PY
```

如果这条命令失败，Stage 12-A 不能继续冒充真实 `verl` 本地 smoke。失败时必须输出缺失依赖名、失败模块和下一步建议。

3. 真实 `AgentLoopOutput.as_dict()` 使用 CPU tensor：

```text
TrainingView fixture
-> repo_harness_verl.training_view_to_agent_loop_output(...)
-> real AgentLoopOutput
-> output.as_dict()
-> prompts / responses / response_mask / rollout_log_probs / rm_scores 均为 CPU tensor
```

4. `VerlLLMGateway` 可以接受真实 `TokenOutput` shape：

```text
fake LLMServerClient.generate(...)
-> verl.workers.rollout.replica.TokenOutput(token_ids=[...], log_probs=[...])
-> VerlLLMGateway.generate_turn(...)
-> LLMGatewayResponse(route="verl", inference_backend="sglang")
```

## 5. 本地极小仓库任务输入

Stage 12-A 优先使用当前 worktree 已存在的 fixture，不依赖另一个 worktree 的可变路径。

候选目录：

```text
tests/fixtures/repos/buggy_calculator
tests/fixtures/repos/import_config_bug
tests/fixtures/repos/missing_helper_file
tests/fixtures/repos/security_probe
```

首个正例建议使用：

```text
tests/fixtures/tasks/task_001.yaml
tests/fixtures/repos/buggy_calculator
```

原因是这个任务足够小，问题清楚，final verifier 可以用 `pytest -q` 验证，适合先证明 workspace、工具、patch、verifier 和 reward 路径可用。

如果 Stage 12-A 需要新增专用任务 fixture，必须放在当前仓库中，例如：

```text
tests/fixtures/repo_harness_verl/stage12a/
```

并生成或更新 sha256 manifest。不能把 `/Users/roger/Desktop/claude-code/tests/fixtures/repos` 作为正式验收输入路径。

## 6. Fake LLMServerClient 设计

Stage 12-A 的 fake `LLMServerClient` 必须模拟真实 verl 调用形状，而不是重新发明一套不兼容接口。

接口形状：

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
) -> TokenOutput:
    ...
```

返回值要求：

- 使用真实 `verl.workers.rollout.replica.TokenOutput`，或字段完全一致的对象。
- `token_ids` 非空。
- `log_probs` 非空，并与 `token_ids` 长度一致。
- `extra_fields` 只能包含通过 Stage 10 / Stage 11 visibility 检查的安全字段，例如 `global_steps`。
- 不允许返回 `ground_truth`、`reward_extra_info`、`reward_extra_keys`、`accepted_label`、`gold_patch`、`provider_secret` 或 evaluator-only 信息。

fake server 需要支持多轮输出队列，用于模拟：

- 第一轮读取文件或运行测试。
- 第二轮写入补丁或执行修复。
- 第三轮提交 final answer 或触发停止。

fake `LLMServerClient` 的职责只是在每次 `generate(...)` 调用时返回排队的 `TokenOutput`。`model_call_id`、`turn`、`context_revision` 这些 per-turn runtime facts 必须来自 `LLMGatewayRequest`、`VerlLLMGateway` 和 `GenerationRecordCollector`，不能硬塞进 `TokenOutput.extra_fields`。测试应断言 collector 最终保存了每一轮独立的 `model_call_id`、`turn`、`context_revision` 和 `GenerationRecord`。

## 7. Token provenance 要求

Stage 12-A 必须继续硬化 Stage 11.5 的 token provenance 边界。

要求：

- `TrainingView.response_ids` 必须来自 `GenerationRecordCollector` 中保存的每轮 `LLMGatewayResponse.output_token_ids` 和工具 observation token projection。
- `TrainingView.response_logprobs` 必须来自 `LLMGatewayResponse.output_logprobs`，工具 observation token 对应 `0.0`。
- assistant generation span 的 token 和 log probability 必须能逐段对齐到 `generation_records`。
- tool observation span 必须有 `response_mask=0`。
- 不能从最终 assistant 文本或 transcript 重新分词来补 token。
- `response_logprobs=None` 的 episode 必须 `invalid_for_online_rl=True`，formal batch validator 必须拒绝。

新增测试需要覆盖伪造场景：

```text
generation_records.output_token_ids = [111]
training_view.response_ids = [999]
```

这个样本必须在 schema 或 converter 阶段被拒绝。

## 8. Visibility 验收

Stage 12-A 必须覆盖三层 visibility。

第一层：模型可见内容。

- `raw_prompt` 只能包含模型应该看到的 issue、文件片段和工具 observation。
- 不允许出现 hidden verifier、gold patch、accepted label、完整 reward metadata、provider secret 或 evaluator-only logs。

第二层：verl postprocess。

- `AgentLoopWorker._agent_loop_postprocess(...)` 写入的 `extra_fields.raw_prompt` 必须通过 visibility 检查。
- 嵌套字段也要检查，不能只检查顶层 key。

第三层：TransferQueue / DataProto。

- `field.update(kwargs)` 后的顶层 `raw_prompt` 必须检查。
- `extra_fields` 只能包含允许的 `repo_harness_*` flat scalar 和 opaque refs。
- `DataProto.batch`、`DataProto.non_tensor_batch` 和 `DataProto.meta_info` 必须全部通过 visibility 检查。
- `ground_truth`、`reward_extra_info`、`reward_extra_keys`、`extra_info` 等字段即使藏在嵌套字典里也必须拒绝。

## 9. Resource 和 artifact 验收

每条 Stage 12-A real episode 都必须产出或可回查：

- `TimingSummary`
- `ResourceSummary`
- `AuditRef`
- final verifier summary
- reward metadata summary
- artifact manifest
- patch 或 workspace state evidence

要求：

- `ResourceSummary.workspace_path` 和 `ResourceSummary.run_dir` 不能是本地绝对路径。
- `TrainingView.extra_fields` 不能包含本地绝对路径。
- `AuditRef` 可以保留结构化内部对象，但进入 batch 的只能是 opaque refs。
- `training_fast` artifact bytes 相比同等 `full_audit` 至少下降 50%；如果极小任务因为原始 artifact 太少无法稳定下降 50%，必须写入 diagnostics 解释原因。
- cleanup 完成后 workspace lease、route slot、episode slot 和 run directory lock 都必须释放。

## 10. 并发 smoke

Stage 12-A 至少要跑一个本地并发 smoke：

```text
episode A: buggy_calculator
episode B: buggy_calculator
共享同一个 snapshot key
使用不同 run_id / episode_id / workspace lease
并发执行
```

验收点：

- 两个 writable workspace 不相同。
- 两个 artifact manifest 不相同。
- 两个 run directory 不相同。
- 任意一个 episode cleanup 失败不会删除另一个 episode 的 workspace。
- route limiter 只包住真实 gateway 调用，不包住 workspace、verifier、reward 或 cleanup。

## 11. 建议新增测试文件

建议新增或扩展：

```text
tests/unit/test_repo_harness_verl_stage12a_local_preflight.py
tests/integration/test_repo_harness_verl_stage12a_real_episode_smoke.py
tests/integration/test_repo_harness_verl_stage12a_visibility_dataproto.py
tests/integration/test_repo_harness_verl_stage12a_concurrency.py
```

如果某些测试因为真实 `reference/verl` CPU 依赖较重而不适合每次默认运行，可以使用明确 marker，例如：

```text
@pytest.mark.verl_local_cpu
```

但是 Stage 12-A 验收命令必须显式运行这些测试，不能只跑默认轻量测试。

## 12. 验收命令

基础回归：

```bash
PYTHONPATH=src uv run --extra dev python -m compileall -q src

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
  tests/unit/test_repo_harness_rl_stage6_resource_summary.py \
  tests/unit/test_workspace_reuse_stage6.py \
  tests/unit/test_repo_harness_rl_stage7_reward_boundary.py \
  tests/unit/test_verifier_worker_pool_stage7.py \
  tests/unit/test_repo_harness_rl_stage8_budget_policy.py \
  tests/unit/test_agent_loop_stage8_no_progress_stop.py \
  tests/unit/test_context_stage8_training_slimming.py \
  tests/unit/test_context_budget.py \
  tests/unit/test_repo_harness_rl_stage9_resource_leases.py \
  tests/unit/test_repo_harness_rl_stage9_concurrency_runtime.py \
  tests/unit/test_repo_harness_verl_stage10_agent_loop_output.py \
  tests/unit/test_repo_harness_verl_stage10_postprocess_visibility.py \
  tests/unit/test_repo_harness_verl_stage10_dataproto_shapes.py \
  tests/unit/test_repo_harness_verl_stage11_request_mapping.py \
  tests/unit/test_repo_harness_verl_stage11_gateway.py \
  tests/unit/test_repo_harness_verl_stage11_agent_loop.py \
  tests/unit/test_repo_harness_rl_stage11_5_real_episode_runtime.py \
  tests/unit/test_run_recorder.py \
  tests/unit/test_provider_artifact_binding.py \
  tests/unit/test_export.py \
  tests/integration/test_export_from_run.py \
  tests/integration/test_v3_export_audit.py
```

Stage 12-A 新测试：

```bash
PYTHONPATH=src:reference/verl uv run --extra dev \
  --with numpy \
  --with torch \
  --with ray \
  --with tensordict \
  --with hydra-core \
  --with omegaconf \
  --with pillow \
  --with transformers \
  --with datasets \
  --with torchdata \
  --with codetiming \
  --with cachetools \
  --with uvicorn \
  --with fastapi \
  --with requests \
  --with aiohttp \
  --with prometheus-client \
  python -m pytest -q \
    tests/unit/test_repo_harness_verl_stage12a_local_preflight.py \
    tests/integration/test_repo_harness_verl_stage12a_real_episode_smoke.py \
    tests/integration/test_repo_harness_verl_stage12a_visibility_dataproto.py \
    tests/integration/test_repo_harness_verl_stage12a_concurrency.py
```

Import boundary：

```bash
PYTHONPATH=src uv run --extra dev python - <<'PY'
import repo_harness.rl
import repo_harness_verl
print("ordinary_import_ok")
PY

if rg -n '(^|\s)(import|from)\s+verl' \
  src/repo_harness/rl \
  src/repo_harness/agent_loop \
  src/repo_harness/workspace \
  src/repo_harness/verifier; then
  exit 1
fi
```

空白检查：

```bash
git diff --check -- \
  docs/agentic_RL/repo_harness_verl_workstreams/16-stage-12-a-execution-plan.md \
  src/repo_harness \
  src/repo_harness_verl \
  tests/unit \
  tests/integration
```

## 13. 完成标准

Stage 12-A 完成时必须能清楚回答：

1. 当前 Mac 本地能否导入真实 `reference/verl` 的关键 CPU 接口。
2. 普通 RepoHarness 导入是否仍然不需要 `verl` 重依赖。
3. `RepoHarnessRuntime(runtime_execution_mode=real_episode)` 是否真实执行 workspace、工具、final verifier 和 reward。
4. `RepoHarnessVerlAgentLoop + fake LLMServerClient` 是否能产生 `route=verl` 的 token facts。
5. `TrainingView -> AgentLoopOutput -> postprocess -> DataProto` 是否通过 shape 和 visibility 检查。
6. invalid、timeout、missing log probability、mock route 和 mixed route 样本是否被 formal online RL gate 拒绝。
7. workspace、artifact、run directory 和 resource lease 是否在并发 smoke 中互相隔离。

只有这些都通过，才能进入 Stage 12-B 的 GPU / Vast.ai 真实模型 smoke。
