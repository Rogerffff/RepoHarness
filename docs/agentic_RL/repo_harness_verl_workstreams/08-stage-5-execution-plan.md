# Stage 5 执行计划：完善 LLMGateway route 实现和模型后端迁移

状态：已完成。当前完成范围覆盖旧 `ModelClient` 到 async `LLMGateway` 的受控 adapter、deterministic `MockLLMGateway`、provider/replay wrapper、未实现 route 的 structured unsupported response，以及 provider route 默认不可作为 formal online RL 样本的测试边界；真实 `VerlLLMGateway`、`RepoHarnessVerlAgentLoop`、Ray / vLLM / SGLang server 管理仍留到后续阶段。
前置状态：Stage 0H、Stage 1、Stage 2、Stage 3、Stage 4 已完成。Stage 4 已在提交 `a7834689` 中完成 timing/resource summary、runtime facade 对账和相关测试。Stage 5 可以在这个基础上处理真实模型调用路径和 `LLMGateway` route 迁移。

## 1. 阶段目标

Stage 5 的目标是把 RepoHarness 现有模型调用体系逐步迁移到训练后端无关的 `LLMGateway` route 体系中。

本阶段要完成的事情是：

1. 让现有 `mock`、`replay`、`openai`、`deepseek` 这类已有模型后端可以通过 `LLMGateway` contract 被调用。
2. 明确 provider route 产生的 token、log probability 和训练可用性边界。
3. 为后续 Stage 11 的 `VerlLLMGateway` 留出稳定接口，但不在 Stage 5 实现真正的 verl adapter。
4. 让旧 `AgentLoop` / `ModelClient` 路径可以在不大规模重写的情况下逐步迁移到 gateway。

Stage 5 完成后，RepoHarness 应该能做到：

```text
现有 provider client / replay / mock
-> LLMGateway route wrapper
-> LLMGatewayResponse
-> GenerationRecord / TrainingView / runtime facade
```

同时仍然保证：

```text
正式 online PPO / GRPO 样本只允许 route=verl
provider route 默认 invalid_for_online_rl=true
```

## 2. 必须保持的边界

1. Stage 5 不能引入 `verl` import，也不能实现 `RepoHarnessVerlAgentLoop`。
2. Stage 5 不能启动、停止或管理 vLLM / SGLang / Ray / verl server。
3. Stage 5 不能把 OpenAI、DeepSeek 或其他 provider route 伪装成当前 rollout policy sample。
4. Stage 5 不能用最终 transcript 重新分词来构造正式训练 token。
5. `LLMGatewayResponse.output_token_ids` 必须表示该次 gateway 调用的模型输出 token；如果 provider route 无法提供可信 token ids 和 log probabilities，必须明确标记为 diagnostic / offline 用途。
6. `LLMGatewayResponse.response_mask` 仍然只能表示模型生成 token，必须全为 `1`。工具 observation token 只能在 episode 级 `TrainingView` 中拼接并设置 `response_mask=0`。
7. `LLMGatewayResponse.extra_fields` 可以保留 gateway 侧信息，但不能包含 hidden verifier、gold patch、provider secret、完整 reward metadata 或本地绝对路径。
8. `TrainingView.extra_fields` 和未来 `AgentLoopOutput.extra_fields` 只能保留 `repo_harness_*` 扁平标量和 `rh://` opaque refs。

## 3. 本阶段不做什么

Stage 5 不做以下工作：

- 不实现真实 `VerlLLMGateway`。
- 不实现 `RepoHarnessVerlAgentLoop`。
- 不实现 `TrainingView` 到 `AgentLoopOutput` 的转换器。
- 不实现 workspace/container 复用。
- 不实现 verifier worker pool。
- 不实现 Ray 调度、vLLM server 管理或 SGLang server 管理。
- 不改变 reward、verifier、workspace 权威语义。

这些内容分别留给 Stage 6、Stage 7、Stage 10、Stage 11 和 Stage 12。

## 4. 需要先阅读和确认的代码位置

实施前先只读检查：

```text
src/repo_harness/rl/gateway.py
src/repo_harness/rl/runtime.py
src/repo_harness/rl/training_view.py
src/repo_harness/rl/visibility.py
src/repo_harness/model_client/protocol.py
src/repo_harness/model_client/schemas.py
src/repo_harness/model_client/factory.py
src/repo_harness/model_client/mock.py
src/repo_harness/model_client/replay.py
src/repo_harness/model_client/providers/common.py
src/repo_harness/model_client/providers/openai.py
src/repo_harness/model_client/providers/deepseek.py
src/repo_harness/agent_loop/loop.py
src/repo_harness/evaluation/runner.py
src/repo_harness/context/auto_compact.py
```

需要重点确认：

- 当前 `AgentLoop` 在哪里调用 `model_client.generate(...)`。
- 当前 `ModelRequestContext` 如何构造 prepared messages、tool schema、provider options、timeout、retry policy 和 recorder policy。
- 当前 OpenAI / DeepSeek provider client 是否能返回真实 token ids 和 log probabilities。
- 当前 mock / replay client 的 raw request / raw response artifact 写入策略是否满足 `training_fast`。
- Stage 2 已有的 `LLMGatewayModelClientAdapter` 是“旧 `ModelClient` 接口调用新 `LLMGateway`”方向；Stage 5 还需要“新 `LLMGateway` 包装旧 `ModelClient`”方向。

## 5. 建议新增或调整的模块

建议优先在 `src/repo_harness/rl/` 内新增训练后端无关 adapter 文件，例如：

```text
src/repo_harness/rl/provider_gateway.py
```

可以包含：

```text
ModelClientLLMGateway
ProviderLLMGateway
ReplayLLMGateway
MockLLMGateway
build_llm_gateway_for_route(...)
```

命名可以按代码实际风格调整，但职责必须清楚：

- `ModelClientLLMGateway`：把 `LLMGatewayRequest` 转成 `ModelRequestContext`，调用现有 `ModelClient.generate(...)`，再转回 `LLMGatewayResponse`。
- `ProviderLLMGateway`：面向 OpenAI / DeepSeek 等 provider route 的薄包装，可以复用 `ModelClientLLMGateway`。
- `ReplayLLMGateway` / `MockLLMGateway`：稳定测试用 route wrapper，不能依赖真实外部 API。
- `build_llm_gateway_for_route(...)`：根据 route 和 runtime-only options 构造 gateway，但不把本地绝对路径写入 request schema、training view 或 batch 字段。

如果发现现有 `LLMGatewayModelClientAdapter` 可以承接部分逻辑，也可以提取共享转换函数，避免两个方向各写一份不一致的映射。

调用旧 `ModelClient` 时必须统一使用关键字参数：

```python
model_client.generate(request=model_request, recorder=recorder)
```

不能写成位置参数调用。当前 `MockProviderClient`、OpenAI provider client、DeepSeek provider client 等实现都使用 `generate(*, request=..., recorder=...)` 形态，位置参数调用会直接破坏这些实现。

`ModelClientLLMGateway.generate_turn(...)` 是 async 接口，但旧 `ModelClient.generate(...)` 是同步接口。包装旧 client 时必须使用受控 executor 或 `asyncio.to_thread(...)`，并且要有最大并发限制，不能无界创建线程。adapter 必须提供显式 `close()` / `aclose()` 或等价生命周期接口，方便训练侧长期持有并在退出时释放线程资源。取消语义也必须和 Stage 2 保持一致：外层 coroutine 被取消或 episode timeout 时，可以返回结构化 cancelled / timeout result 和 cleanup diagnostics，但不能假装已经强制中断了底层同步 provider 调用。

## 6. route 处理策略

Stage 5 必须明确固定 route 行为：

```text
mock:
  可用于测试和本地 smoke。
  可以产生稳定 deterministic token facts。

replay:
  可用于 offline diagnostic replay。
  如果 replay script 没有真实 token/logprob provenance，则默认 invalid_for_online_rl=true。

openai / deepseek:
  可用于 evaluation、teacher data generation、SFT export、preference data、offline diagnostic replay。
  默认 invalid_for_online_rl=true。
  不得伪装成 route=verl 的 rollout policy sample。

local_vllm / local_sglang:
  Stage 5 可以先固定 schema 和 adapter 占位行为。
  如果没有实现真实本地 server client，应返回结构化 unsupported route error，而不是静默 fallback 到 provider route。

verl:
  Stage 5 只保留 contract 和 route 校验。
  真实 VerlLLMGateway 留到 Stage 11。
```

## 7. token 和 log probability 策略

Stage 5 的核心风险是“看起来有 token，实际不是训练可用 token”。必须使用下面的策略：

1. provider route 如果只能提供文本，不能把重新分词结果标记为正式 online RL token provenance。
2. 如果为了 diagnostic 或 export 需要 token ids，可以设置：

```text
token_source = provider_text_retokenized_debug_only
output_logprobs = None
```

3. provider route 即使有 token ids，只要缺少当轮 rollout policy log probability，也必须 `invalid_for_online_rl=true`。
4. route=verl 未来才允许使用 verl tokenizer / server 返回的 prompt ids、output token ids 和 log probabilities 作为正式 online RL token provenance。
5. `GenerationRecord` 必须记录 route、inference_backend、policy version、global step 范围和 token provenance 相关事实。

旧 `ModelClient` wrapper 的转换结果要单独写清楚。现有 `ModelResponse` 主要包含 assistant message、tool calls、raw artifact refs、token usage 和 `ModelCallEvent`，通常没有正式 `output_token_ids` 和 `output_logprobs`。因此：

- 如果旧 client 拿不到真实 token ids 和 log probabilities，`ModelClientLLMGateway` 只能返回 diagnostic / offline `LLMGatewayResponse`。
- 允许设置 `token_source=provider_unavailable` 或 `token_source=provider_text_retokenized_debug_only`，但这类 token 不能进入 formal online RL batch。
- `output_logprobs=None` 时，runtime / `TrainingView` 必须标记 `invalid_for_online_rl=true`。
- deterministic `MockLLMGateway` 可以为了测试提供稳定 token ids 和 log probabilities，但这和“包装旧 `MockProviderClient`”不是同一条语义路径，不能混为一谈。

## 8. AgentLoop 迁移策略

Stage 5 不建议一次性重写整个 `AgentLoop`。建议采用保守迁移：

1. 先实现 `ModelClientLLMGateway`，让新 runtime / tests 可以通过 gateway 调旧 provider client。
2. 再复用 Stage 2 的 `LLMGatewayModelClientAdapter`，让旧 `AgentLoop` 可以在需要时通过旧 `ModelClient.generate(...)` 接口调用 gateway。
3. 增加一个受控配置开关或测试专用构造函数，证明旧 `AgentLoop` 可以在不绕过 gateway 的情况下完成一次 mock / replay episode。
4. 保留旧 `create_model_client(...)` 和 CLI 默认路径，避免破坏当前 SWE-Bench / V5 测试。
5. 最终迁移状态应该是：核心模型调用转换逻辑集中在 gateway adapter，不在 runtime、runner、agent loop 中重复散落。

## 9. 安全和可见性验收

Stage 5 必须补测试证明：

- 未登记 route 被 schema 拒绝。
- `route=verl` 必须搭配 `inference_backend=sglang|vllm`。
- provider route 默认 `invalid_for_online_rl=true`。
- provider route 缺失 `output_logprobs` 时不能进入正式 online RL batch。
- provider route response 不能包含本地绝对路径、provider secret、hidden verifier、gold patch 或完整 reward metadata。
- route mismatch 仍然返回结构化 invalid / infrastructure error，不能进入训练。
- `raw_request_ref`、`raw_response_ref`、`model_call_event_ref` 必须是 `rh://` opaque refs。
- `training_fast` 下 raw provider artifact 仍然遵守 Stage 3 的 retention / projection policy。

## 10. 实施顺序

建议按下面顺序执行：

1. 只读梳理现有 `ModelClient`、provider、mock、replay 和 `AgentLoop` 调用路径。
2. 新增 Stage 5 单元测试，先覆盖 provider route 默认不可作为 online RL 样本、mock/replay gateway roundtrip、route mismatch 和 missing logprob。
3. 实现 `ModelClientLLMGateway` 或等价 adapter，把 `LLMGatewayRequest` 映射到 `ModelRequestContext`；调用旧 client 时必须使用 `model_client.generate(request=model_request, recorder=recorder)`。
4. 实现 `ModelResponse` 到 `LLMGatewayResponse` 的转换，并明确 token provenance、logprob 缺失和 raw artifact ref 投影；没有真实 token/logprob 时只能产出 diagnostic / offline response。
5. 为 mock/replay route 提供 deterministic gateway，确保本地测试不依赖外部 API。
6. 为 openai/deepseek route 提供 provider gateway wrapper，但真实 API smoke 应保持可跳过、成本受控、凭据不落盘。
7. 接入 runtime facade 或受控测试入口，验证 gateway route 可以生成 `GenerationRecord` 和 `TrainingView`。
8. 增加 visibility / contract tests，证明 provider route 不会进入 formal online RL batch。
9. 运行 Stage 5 新测试以及 Stage 0H 到 Stage 4 回归测试。
10. 安排 sub agent 只读审查，重点检查 route 边界、token provenance、provider route 默认 invalid 和是否提前实现 Stage 11。

## 11. 建议新增测试

建议新增：

```text
tests/unit/test_repo_harness_rl_stage5_gateway_routes.py
tests/unit/test_repo_harness_rl_stage5_provider_gateway.py
```

测试重点：

- `mock` route 通过 gateway 返回稳定 `LLMGatewayResponse`。
- `replay` route 通过 gateway 保留 replay alignment error 和 raw refs。
- `openai` / `deepseek` provider route 默认不可进入 online RL。
- provider route 缺失 logprob 时，`TrainingView` 保持 diagnostic / offline，而不是 formal online RL。
- route=response mismatch 被拒绝。
- `provider_secret`、绝对路径和 evaluator-only marker 无法通过 request / response / extra fields。
- `LLMGatewayModelClientAdapter` 和新增反向 adapter 不产生字段漂移。

## 12. 验收命令

Stage 5 实施完成后至少运行：

```bash
PATH=.venv/bin:$PATH python -m compileall -q src
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_repo_harness_rl_stage5_gateway_routes.py
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_repo_harness_rl_stage5_provider_gateway.py
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_repo_harness_rl_stage4_timing_resource.py
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_repo_harness_rl_stage3_training_fast_recorder.py
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_repo_harness_rl_stage2_runtime.py
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_repo_harness_rl_stage1_schema_roundtrip.py tests/unit/test_repo_harness_rl_stage1_visibility_gateway.py
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_repo_harness_verl_contract_fixtures.py tests/unit/test_repo_harness_verl_stage0h_shape_rules.py tests/unit/test_repo_harness_verl_stage0h_visibility.py
rg -n "(^|\\s)(import|from)\\s+verl" src/repo_harness/rl || true
```

如果 Stage 5 改动触及 `AgentLoop` 或 provider client，还需要额外运行：

```bash
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_run_recorder.py
PATH=.venv/bin:$PATH python -m pytest -q tests/integration/test_export_from_run.py
```

## 13. 阶段出口

Stage 5 可以视为完成的条件：

- 新增 gateway route wrapper 或等价 adapter。
- mock/replay/provider route 至少有本地可重复测试。
- provider route 默认 `invalid_for_online_rl=true` 的规则有 schema 或 runtime 测试覆盖。
- 旧 `ModelClient` 和新 `LLMGateway` 的双向 adapter 边界清楚。
- 没有 `verl` import。
- 没有提前实现 Stage 10 或 Stage 11。
- Stage 0H 到 Stage 4 回归测试通过。
- sub agent 审查没有指出阻断问题。
