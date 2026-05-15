# Stage 2 执行计划：抽出 RepoHarnessRuntime.run_episode(...)

状态：待执行。前置条件是 Stage 1 已完成：`src/repo_harness/rl/` schema 包、async `LLMGateway.generate_turn(...)` contract、Stage 0H fixture roundtrip、visibility 拒绝规则和 Stage 1 回归测试已经通过。

## Stage 2 要做什么

Stage 2 的目标是从现有 CLI / evaluation runner 的任务运行链路中抽出可复用 episode runtime facade：

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

第一版可以在内部复用现有同步 agent loop、workspace、verifier、reward 和 recorder 逻辑，但外层接口必须是 async，方便后续 verl `AgentLoopBase.run(...)` 调用，也方便 Stage 13 的 fully async 演进。

## 第一项工作

先做只读梳理，不直接重写 runner。必须读清楚当前运行链路：

- `src/repo_harness/evaluation/runner.py`
- `src/repo_harness/agent_loop/loop.py`
- `src/repo_harness/model_client/protocol.py`
- `src/repo_harness/workspace/backend_factory.py`
- `src/repo_harness/trajectory/recorder.py`
- `src/repo_harness/reward/schemas.py`
- `src/repo_harness/verifier/schemas.py`

梳理结果应先落成最小 runtime facade 边界，而不是直接把 CLI 整段搬进 `rl/runtime.py`。

## Stage 2 实施前必须固定的执行边界

Stage 2 不能只新增一个 async 函数外壳，然后继续在内部绕回旧 provider client。执行前必须先固定下面五个边界。

### 1. `LLMGateway` 和现有 `AgentLoop` 的接入策略

当前 `AgentLoop` 接收旧的同步 `ModelClient`，并调用 `model_client.generate(...)`。Stage 2 的新入口接收异步 `LLMGateway`。因此 Stage 2 必须选择并显式实现下面的受控策略，不能绕过 `llm_gateway` 直接构造旧 provider client：

- 新增临时 `LLMGatewayModelClientAdapter`，由 runtime 层持有，用于把旧 `ModelRequestContext` 映射成 `LLMGatewayRequest`，再把 `LLMGatewayResponse` 映射回旧 `ModelResponse`，让现有 `AgentLoop` 可以在不重写内部循环的情况下使用新 gateway contract。
- 如果完整 legacy agent loop 桥接在 Stage 2 中风险过大，则只能先交付受控的 fake gateway 最小 runtime path，并在测试和文档中明确说明“完整 `AgentLoop` 尚未接入 `LLMGateway`”。这种情况下不能把 Stage 2 描述成已经完成完整 agent loop gateway 接入。

第一优先选择是临时 adapter，因为它能让 `run_episode(...)` 的 `llm_gateway` 参数真正参与运行；但该 adapter 只解决新旧接口接缝，不迁移真实模型后端，不引入 vLLM / SGLang / Ray / verl server，这些仍属于 Stage 5 和 Stage 11。

### 2. `RepoHarnessEpisodeRequest` 到现有 runner 输入的映射

现有 `run_task(...)` 需要 `task_path`、`config_path`、`output_dir` 和 `run_id`。Stage 1 的 `RepoHarnessEpisodeRequest` 只有 `task_ref.task_path`、`run_config_ref`、`run_id` 等字段，其中 `run_config_ref` 是 contract 引用，不应该被默认当成本地绝对 `config_path`。

Stage 2 应新增 `RepoHarnessRuntimeOptions` 或等价 runtime-only 配置，承载本地执行需要但不应该进入训练 batch 的信息：

- `config_path`：本地 RepoHarness 配置文件路径，由 runtime options 提供，不能偷偷从 CLI 默认值推断。
- `output_dir`：本地运行输出目录，由 runtime options 提供，不能写入 `RepoHarnessEpisodeRequest` 的 batch 可传播字段。
- `project_root` 或 `workspace_root`：如实现需要，必须属于 runtime options 或内部解析结果，不能塞进 `TrainingView.extra_fields`。
- `task_path`：优先来自 `request.task_ref.task_path`，如果使用 `task_ref.task_ref` 或其他 opaque ref，则必须在 runtime options 中显式提供 resolver。

原则是：episode request 描述可移植 episode 事实；runtime options 描述当前机器上的执行路径和资源位置。Stage 2 不应为了复用 `run_task(...)` 而把绝对路径、run directory 或 evaluator-only path 加进可传播 schema。

### 3. cancellation、executor 和 cleanup 的真实语义

如果 Stage 2 使用 `asyncio.to_thread(...)` 或 executor 包装现有同步 runner，必须明确它只是把同步逻辑放入受控线程执行。外层 coroutine 被取消时，底层线程不会被 Python 自动强制停止。因此 Stage 2 不能假装“取消 coroutine 就一定中断任意同步 `run_task(...)`”。

执行约束如下：

- executor 必须是受控、有限并发的 executor，不能使用无界任务堆积。
- cancellation smoke 第一版只能验证 runtime 自己可控的 fake gateway / minimal path，或者验证 runtime 能标记 `cancelled` 并安排 cleanup；不能声称已经可以强杀所有同步 Docker / verifier / provider 调用。
- runtime 管理的 workspace、container、artifact writer、recorder、verifier future 和临时资源必须放进 `try/finally` 或等价资源保护结构。
- cleanup 失败不能覆盖原始 episode 状态；例如原状态是 `timeout`，清理失败只能进入 diagnostics 和 `ResourceSummary.cleanup_status`。

### 4. 状态映射表

Stage 2 需要把现有 runner 的结果和异常明确映射到 `RepoHarnessEpisodeResult.status`。第一版映射如下：

| 输入事实或失败类别 | Stage 2 result status | 训练语义 |
| --- | --- | --- |
| final verifier accepted | `succeeded` | 可以训练，前提是 `TrainingView` token、mask、log probability 完整且 visibility 合法 |
| final verifier rejected | `failed` | 可以作为失败样本，前提是 `TrainingView` 完整且不是 provider diagnostic path |
| agent stop reason 明确为 no progress，且没有被 timeout / cancellation 覆盖 | `no_progress` | 默认不可进入正式 online RL，后续 Stage 8 再加严策略 |
| episode timeout、provider timeout、model call timeout、verifier timeout、Docker command timeout | `timeout` | 默认 `invalid_for_training=true` 和 `invalid_for_online_rl=true` |
| baseline invalid、setup invalid、任务定义不合法、任务引用无法解析 | `invalid_task` | 默认 `invalid_for_training=true` 和 `invalid_for_online_rl=true` |
| Docker 初始化失败、workspace materialization 失败、文件系统错误、recorder 写入失败、verifier 基础设施异常、未知基础设施异常 | `infrastructure_error` | 默认 `invalid_for_training=true` 和 `invalid_for_online_rl=true` |
| 外层 runtime cancellation | `cancelled` | 默认 `invalid_for_training=true` 和 `invalid_for_online_rl=true` |

如果同一个 episode 同时出现多个事实，优先级应是：`cancelled` / `timeout` / `infrastructure_error` / `invalid_task` 这类执行完整性状态优先于模型任务成败；cleanup 失败不提升为主状态，只写入 cleanup diagnostics。

### 5. `TrainingView` 第一版构造边界

Stage 2 不能通过最终文本重新分词来伪造 online RL 所需 token，也不能给没有 log probability 的旧 provider / replay 路径补一个看似合法的训练 batch。

第一版规则如下：

- fake gateway smoke 可以直接使用 `LLMGatewayResponse.prompt_ids`、`output_token_ids`、`output_logprobs` 和 `response_mask` 构造最小 `TrainingView`。
- 通过临时 `LLMGatewayModelClientAdapter` 的 legacy agent loop path，只能使用 gateway 返回的真实 token 事实构造 `GenerationRecord` 和后续 `TrainingView`。
- 如果真实旧 provider / replay 路径无法提供 token ids 和 log probability，则 result 必须标记 `invalid_for_online_rl=true`，只能作为 diagnostic result、SFT / preference / offline replay 的候选证据，不能进入正式 PPO / GRPO online batch。
- provider route 仍默认 `invalid_for_online_rl=true`；Stage 2 不负责把 OpenAI、DeepSeek 或本地 provider 迁移成正式 rollout policy route。

## 计划新增或修改模块

- `src/repo_harness/rl/runtime.py`：新增 `RepoHarnessRuntime`、runtime options、最小 `run_episode(...)` facade、状态映射 helper，以及必要的临时 `LLMGatewayModelClientAdapter`。
- `src/repo_harness/rl/__init__.py`：导出 `RepoHarnessRuntime`。
- `tests/unit/test_repo_harness_rl_stage2_runtime.py`：新增 fake gateway 最小 episode、`LLMGateway` 不被绕过、request 到 runtime options 映射、状态映射、timeout / cancellation / cleanup contract、TrainingView 构造边界的单元测试。
- 必要时小范围修改 `src/repo_harness/evaluation/runner.py`：只做 CLI 到 runtime facade 的桥接准备，不改变现有 CLI 行为。

## 实施顺序

1. 先画清现有 `run_task(...)` 的数据流：task/config、workspace materialization、context、agent loop、final verifier、reward、artifact 和 summary。
2. 先定义 `RepoHarnessRuntimeOptions`，明确 `config_path`、`output_dir`、本地 path resolver 和 executor 设置来自 runtime-only 配置，不塞进 episode request 或训练 batch。
3. 新增 `RepoHarnessRuntime.run_episode(...)` async facade，第一版允许内部调用同步逻辑，但必须通过 `LLMGateway` 或明确标记的 fake/minimal path，不能直接绕回旧 provider client。
4. 新增临时 `LLMGatewayModelClientAdapter`，把旧 `ModelRequestContext` 映射成 `LLMGatewayRequest`，把 `LLMGatewayResponse` 映射回 `ModelResponse`；如果这一步暂缓，必须在 Stage 2 result 和测试里明确完整 `AgentLoop` 尚未接入 gateway。
5. 用 Stage 1 的 async `FakeLLMGateway` 构造最小 runtime smoke，验证能返回 `RepoHarnessEpisodeResult`，并验证 fake gateway 确实被调用。
6. 实现状态映射 helper，按本计划中的状态映射表覆盖 accepted、rejected、no progress、timeout、invalid task、infrastructure error 和 cancelled。
7. 前置 cancellation / timeout / cleanup contract：外层 coroutine 取消、episode timeout、provider timeout、verifier timeout、Docker command timeout 和 cleanup 失败都要有明确归属。
8. 保证 cleanup 失败不能覆盖原始 episode 状态，但必须进入 diagnostics 和 `ResourceSummary.cleanup_status`。
9. 明确 `TrainingView` 构造边界：只能使用 gateway token 事实；缺少 token / log probability 的 legacy provider path 必须 `invalid_for_online_rl=true`。
10. 最后再考虑让 CLI run task 调用 runtime facade；如果风险过大，Stage 2 可以先保留 CLI 原路径，并用 tests 标明桥接仍是后续小步迁移。

## 出口标准

- `RepoHarnessRuntime.run_episode(...)` 是 async 接口，并接收 `RepoHarnessEpisodeRequest` 和 `LLMGateway`。
- 本地执行路径和资源位置通过 runtime options 或显式 resolver 提供，不能把绝对 `config_path`、`output_dir`、`run_dir` 放入 batch 可传播 schema。
- Stage 2 测试能证明 runtime 没有绕过 `llm_gateway`：要么通过 `LLMGatewayModelClientAdapter` 进入现有 agent loop，要么明确只交付 fake/minimal path 且不声称完整 agent loop 已接入。
- fake gateway 最小 episode 能产出结构化 `RepoHarnessEpisodeResult`。
- `cancelled`、`timeout`、`invalid_task`、`infrastructure_error` 都默认 `invalid_for_training=true` 和 `invalid_for_online_rl=true`。
- cancellation smoke 能看到确定的 cleanup diagnostics 或最小 infrastructure error artifact，但不能声称外层 coroutine cancellation 可以强制停止任意同步 `run_task(...)` 线程。
- `TrainingView` 第一版只能从 gateway token 事实构造；缺少 token ids 或 log probability 的 legacy provider / replay path 必须标记 `invalid_for_online_rl=true`。
- CLI run task 仍保持原有可用性；如果 CLI 尚未完全改为 runtime facade，必须在测试和文档里说明保守边界。
- Stage 0H 与 Stage 1 回归测试继续通过。

## Stage 2 明确不做

- 不实现 `training_fast` recorder 和 artifact bytes 降低目标；这是 Stage 3。
- 不实现 `TimingSummary` / `ResourceSummary` 95% wall time 解释率；这是 Stage 4。
- 不迁移真实模型后端到完整 gateway route；这是 Stage 5。Stage 2 的临时 adapter 只处理新旧接口接缝，不负责把 OpenAI、DeepSeek、本地 vLLM 或本地 SGLang 做成完整 route 实现。
- 不做 workspace/container 复用、verifier worker pool、并发租约或 no-progress 策略加严；这些属于 Stage 6 到 Stage 9。
- 不实现 `TrainingView -> AgentLoopOutput` converter；这是 Stage 10。
- 不实现 `RepoHarnessVerlAgentLoop`、`VerlLLMGateway` 或真实 verl / vLLM / SGLang 接入；这是 Stage 11。
- 不通过最终文本重新分词来伪造 `prompt_ids`、`response_ids` 或 `response_logprobs`。

## 验收命令

```bash
uv run --extra dev python -m compileall -q src
uv run --extra dev python -m pytest -q tests/unit/test_repo_harness_rl_stage2_runtime.py
uv run --extra dev python -m pytest -q tests/unit/test_repo_harness_rl_stage1_schema_roundtrip.py tests/unit/test_repo_harness_rl_stage1_visibility_gateway.py
uv run --extra dev python -m pytest -q tests/unit/test_repo_harness_verl_contract_fixtures.py tests/unit/test_repo_harness_verl_stage0h_shape_rules.py tests/unit/test_repo_harness_verl_stage0h_visibility.py
```
