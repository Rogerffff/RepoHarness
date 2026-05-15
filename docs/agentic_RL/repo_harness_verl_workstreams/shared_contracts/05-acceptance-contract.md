# Shared Contract 05：Acceptance 与阶段门槛

本文档定义分阶段实现 shared contracts 后必须满足的验收标准。

```text
contract_version: repo_harness_verl_shared_contracts_v0
status: design_contract_v0
scope: planning_only_not_current_implementation
```

## 1. 为什么需要 acceptance contract

这次不是普通功能开发，而是把 RepoHarness 变成 online reinforcement learning 的软件工程环境和轨迹生产层。最危险的问题不是代码能不能跑，而是：

- token、mask、reward 对齐错了但训练还在继续。
- hidden verifier 或 reward metadata 泄漏进模型可见上下文。
- training_fast 为了加速删掉审计引用，导致样本不可追溯。
- 并发 episode 污染工作区或 run directory。
- 基础设施失败被当成模型负样本训练。

因此，每个实现阶段都必须经过 contract 验收，不能只靠局部 smoke test。

## 2. shared contracts 文档验收

当前文档阶段必须满足：

1. `shared_contracts/` 中每份文档都声明 `contract_version` 和 `status`。
2. 每份 contract 都明确“计划中接口，不代表当前已经实现”。
3. 每份 contract 都有不变量。
4. HTML 汇报页必须包含 shared contracts 摘要，方便人工审核。
5. 如果后续修改 contract，必须同步更新顺序实施计划文档。

## 3. Harness runtime 和 training_fast 阶段验收

Harness runtime 和 training_fast 阶段最小验收建议：

1. 新增 runtime facade 或等价入口，能够接收 `RepoHarnessEpisodeRequest`。
2. 支持 `run_mode=full_audit | training_fast | training_debug`。
3. `training_fast` 默认关闭明文 reasoning trace 和超大 raw artifact 写入，但保留关键 hash 与 audit_ref。
4. 每条 episode 输出 `TimingSummary`。
5. 支持 no-progress stop，并把结果标记为 `status=no_progress` 或 diagnostics。
6. 支持 provider request deadline 和 max output tokens 训练预算。
7. 如果实现 workspace snapshot，必须有 clean snapshot key 和 copy-on-write 隔离测试。
8. 如果实现 verifier worker pool，第一版必须 await final reward 后再返回 `EpisodeResult`。
9. 并发运行两条 episode 时，run directory、workspace 和 artifact manifest 不互相污染。
10. `agent_policy` 中的 scaffold、工具、权限、上下文和反馈策略必须由 request 显式传入或引用，不能由 runtime 自行猜默认值。
11. `training_fast` 相比同一任务的 `full_audit` artifact bytes 至少下降 50%，或者在 artifact manifest 中逐类说明为什么无法达到该阈值。
12. fake gateway 固定成本 benchmark 必须能跑 8 条最小 episode，并报告非模型 p95 wall time。第一版默认验收阈值是 180 秒，后续可以根据 Vast.ai 实测调整。
13. 每条 `TimingSummary` 必须解释至少 95% 的 outer wall time；无法解释的部分必须进入 `timing_unattributed_seconds` 和 diagnostics。
14. `RepoHarnessRuntime.run_episode(...)` 必须定义 cancellation / timeout / cleanup contract。取消、超时或清理失败不能只留下 Ray exception 或线程异常，必须返回最小 `EpisodeResult`，或者产出明确的 infrastructure error artifact。

## 4. verl adapter 阶段验收

verl adapter 阶段最小验收建议：

1. 能通过 Hydra config 注册 `RepoHarnessVerlAgentLoop`。
2. `RepoHarnessVerlAgentLoop.run(...)` 能从 verl non-tensor fields 构造 `RepoHarnessEpisodeRequest`。
3. `VerlLLMGateway` 能包装 verl `LLMServerClient.generate(...)`，并返回 token ids、log probabilities、stop reason 和 extra fields。
4. 能把 `RepoHarnessEpisodeResult.training_view` 转成 verl `AgentLoopOutput`。
5. `AgentLoopOutput.extra_fields` 至少携带 `repo_harness_episode_id`、`repo_harness_run_id`、`repo_harness_task_id`、`repo_harness_audit_manifest_ref`、`repo_harness_status` 和 `repo_harness_invalid_for_training`。
6. smoke test 中一条极小任务能从 verl agent loop 进入 RepoHarness runtime，并返回 reward。
7. 单元测试覆盖 response mask：assistant token 为 `1`，tool observation 为 `0`。
8. 单元测试覆盖 hidden verifier / reward metadata 不进入 prompt、response target 或 non-tensor visible fields。
9. 单元测试覆盖经过 verl `_agent_loop_postprocess(...)` 后的最终 `AgentLoopOutput.extra_fields`，尤其是自动加入的 `raw_prompt` 只能包含模型可见 prompt。
10. `RepoHarnessVerlAgentLoop` 构造 request 时必须对 `kwargs` 使用 allowlist，防止 hidden metadata、gold patch、accepted label、evaluator-only fields 进入 request、raw_prompt、TransferQueue 或 DataProto non-tensor batch。
11. `AgentLoopOutput.extra_fields` 只允许 `repo_harness_*` namespaced flat scalar 和 opaque refs，不允许嵌套 `audit_ref` 对象或模型工具可读取的本地绝对路径。
12. 正式 online PPO / GRPO 路径只允许 `route=verl`。provider route 样本默认 `invalid_for_online_rl=true`，不能伪装成当前 rollout policy sample。

## 5. 顺序阶段 gate

后续开发按顺序推进时，每个阶段至少应通过对应 gate：

| 阶段 | 最小 gate |
| --- | --- |
| Stage 0 | shared contracts、contract hardening v1 和 canonical fixture sha256 固定。 |
| Stage 1 | schema 可以构造、序列化、反序列化；fake/mock `LLMGateway.generate_turn(...)` 可用于测试。 |
| Stage 2 | `RepoHarnessRuntime.run_episode(...)` 可以通过 fake gateway 跑最小 episode。 |
| Stage 3 | `training_fast` artifact profile 生效，并且没有删除关键 audit reference。 |
| Stage 4 | `TimingSummary` 和 `ResourceSummary` 在成功、失败和 timeout 情况下都存在。 |
| Stage 5 | 现有 provider 路径通过 `LLMGateway` 仍能运行，并保留 token provenance 所需记录。 |
| Stage 6 | workspace snapshot、dependency cache、baseline cache 和 container lease 的 cache hit / lease 事实可审计，且不污染并发 episode。 |
| Stage 7 | verifier worker pool 同步返回 reward，queue wait 和 worker id 可追踪。 |
| Stage 8 | 训练预算、no-progress 和上下文瘦身策略可触发、可审计、可过滤。 |
| Stage 9 | 两条 episode 并发运行时 run directory、workspace、artifact manifest 和 resource lease 不冲突。 |
| Stage 10 | `TrainingView -> AgentLoopOutput` 转换通过 mask、reward、log probability、overflow、empty response、nested extra fields 和 DataProto shape 检查。 |
| Stage 11 | `RepoHarnessVerlAgentLoop` 和 `VerlLLMGateway` 可以通过 fake 或小型本地 server smoke。 |
| Stage 12 | 端到端 smoke 形成 `DataProto`，并可通过 opaque refs 和结构化 `AuditRef` 反查 RepoHarness 轨迹。 |
| Stage 13 | 中断、恢复、policy version、staleness 和异步 reward backfill 的预留字段不阻断后续 fully async 设计。 |

## 6. 端到端前共同门槛

进入端到端 smoke 前必须共同满足：

```text
Contract schema tests:
  EpisodeRequest / EpisodeResult / TrainingView / AuditRef / TimingSummary 可以构造、序列化、反序列化。

Canonical fixture tests:
  shared schema JSON fixture 和 sha256 固定；adapter 生成的 RepoHarnessEpisodeRequest 与 runtime 反序列化后的对象逐字段一致。

Visibility tests:
  hidden verifier、gold patch、reward metadata 不进入模型可见上下文和训练 target。
  模型工具尝试读取 run directory、reward metadata、final verifier artifact、hidden selector、hidden test patch、gold patch 和 evaluator-only raw output 时必须被拒绝。

Postprocess visibility tests:
  TrainingView -> AgentLoopOutput -> verl postprocess 后，extra_fields、raw_prompt、mask、reward 和 hidden visibility 仍满足 contract。
  普通 AgentLoopWorker postprocess 和 main_ppo_sync.py / TransferQueue 路径都要覆盖。

Mask tests:
  assistant token、tool observation token、padding token 的 mask 语义正确。
  `response_mask=0` 的 token 对应 `response_logprobs=0.0`。
  正式 PPO / GRPO batch 中所有样本都必须有 `response_logprobs`，并且 `len(response_logprobs) == len(response_ids)`。

Token provenance tests:
  route=verl 时，prompt_ids 和 response_ids 来自真实 rollout generation 路径，不允许用最终 transcript 重新分词伪造正式训练 token；每个 GenerationRecord.prompt_ids 必须等于当轮传给 LLMServerClient.generate(...) 的 prompt_ids。
  多轮工具调用 fixture 必须包含 `response_spans`，能解释 assistant generation、tool observation、truncated excluded 和对应 policy version / global steps。

LLMGateway route tests:
  fake/mock gateway 和 route=verl 都必须能产生可追踪的 GenerationRecord；provider route 如果暂时不能返回 token ids 和 log probability，必须显式标记不能作为正式 PPO / GRPO token provenance。
  唯一 route 枚举为 verl、openai、deepseek、local_vllm、local_sglang、replay、mock；route=verl 的真实推理后端用 inference_backend=sglang|vllm 表示。

Audit tests:
  每条 training sample 可以通过 opaque refs 和离线审计工具找到 run directory、transcript、events、artifact manifest、reward metadata 和 final verifier。
  这些 opaque refs 不能是模型工具可直接读取的本地绝对路径。

Resource reuse tests:
  snapshot_cache_hit、dependency_cache_hit、baseline_cache_hit、container_reuse_hit、snapshot_restore_strategy 和 lease_id 必须进入 ResourceSummary，并证明并发 episode 不共享可写 workspace。

Training fast artifact tests:
  training_fast 相比 full_audit 必须减少明确类别的大体积 artifact，并达到第一版默认 50% 体积下降阈值；如果无法达到，必须在 artifact manifest 中逐类解释，同时 opaque refs 和结构化 AuditRef 仍能反查关键证据。

DataProto shape tests:
  `rollout_log_probs` 必须出现在正式 route=verl 的 DataProto tensor batch 中，形状为 `[batch_size, rollout.response_length]`。
  `rm_scores` 必须存在，或者 invalid 样本已经被明确过滤。
  `response_mask`、tensor batch、non-tensor batch 和 meta_info 的 batch 维度必须一致。
  invalid 样本不能悄悄参与 policy loss；如果选择置零 loss weight，必须在 tensor 或 metrics 中显式可见。

Failure tests:
  infrastructure_error、timeout、invalid_task 不会被误当成普通模型失败样本。
  cancellation smoke 必须覆盖 agent loop 中途取消后的 workspace lease、container lease、artifact writer、verifier future 和 cleanup diagnostics。

Outcome distinction tests:
  status=succeeded 只表示轨迹和 reward 可消费，不等于任务成功；当 verifier_summary.accepted=false 时，不能被统计成 task_success。

Schema evolution tests:
  新增字段必须显式标记 required / optional / default，并说明是否需要 contract version bump。

Smoke test:
  至少一条极小软件工程任务可以从 verl 自定义 agent loop 调用 RepoHarness，得到 reward、结构化 AuditRef 和进入 batch 的 opaque refs。
```

## 7. 第一版不变量

1. 没有 reward 或明确 invalid 状态的 episode 不能作为普通 online RL 样本返回。
2. 没有结构化 AuditRef 或进入 batch 的 opaque refs 的 episode 不能进入训练样本。
3. 没有 timing_summary 的 episode 不能声称支持训练吞吐分析。
4. `training_fast` 不能绕过 RepoHarness 的 visibility policy 和 export/audit denylist。
5. `RepoHarnessVerlAgentLoop` 不能直接调用 CLI 级 `run_task(...)` 作为长期方案。
6. `training_fast` 不能绕过 final verifier 权威边界；如果 final verifier 无法执行，必须把样本标记为 invalid 或 infrastructure error。
7. 所有阶段必须运行同一套 shared contract fixture tests，不能只各自运行 smoke test。
8. verl postprocess 后新增的 `extra_fields.raw_prompt` 也必须纳入 visibility 和 artifact 体积审查。
9. 没有 `response_logprobs` 的样本不能进入正式 online PPO / GRPO batch。
10. `response_ids` 为空但带有 reward 的样本必须在进入 verl 前拦截。
11. `AuditRef` 不能作为嵌套对象进入 `AgentLoopOutput.extra_fields`；进入 batch 的只能是 `repo_harness_*` opaque refs。
12. Stage 12 必须分成两层验收：Mac 本地 fake / lite 结构验收，以及 Vast.ai 或同类 Linux GPU 环境的真实 vLLM / SGLang smoke。Mac 通过不等于真实训练前可用。
