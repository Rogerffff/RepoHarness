# RepoHarness 接入 verl 顺序实施计划复核报告

```text
status: review_complete_with_required_followups
reviewed_plan: docs/agentic_RL/repo_harness_verl_workstreams/01-sequential-implementation-plan.md
review_date: 2026-05-13
scope: planning_review_only
```

## 1. 结论

当前顺序实施计划的总体方向是合理的，也具备落地基础。最重要的方向选择是正确的：

1. 先冻结 shared contracts 和 canonical fixture。
2. 再把现有 CLI 级 `run_task(...)` 抽成可复用的 `RepoHarnessRuntime.run_episode(...)`。
3. 再把现有 provider 调用迁移到训练后端无关的 `LLMGateway`。
4. 最后在 verl 侧实现 `RepoHarnessVerlAgentLoop` 和 `VerlLLMGateway`。

这个路线避免把 RepoHarness 重写成 verl 内部工具，也避免把 verl 的训练逻辑搬进 RepoHarness。它让 RepoHarness 成为可复用 episode runtime，让 verl 只负责 rollout 调度、推理服务、DataProto 组 batch 和 PPO / GRPO 训练。这个边界符合项目目标。

但是，当前计划还不能直接进入实现。它缺少几类会影响真实在线强化学习训练正确性的硬门槛：

1. `TrainingView -> AgentLoopOutput -> DataProto` 的 token、mask、log probability、长度、截断和 batch 一致性规则还不够严格。
2. hidden verifier、gold patch、reward metadata 的防泄漏规则主要覆盖字段内容，但没有充分覆盖 audit artifact 路径是否能被模型工具读取。
3. 普通 verl agent loop 之外，fully async / TransferQueue 路径也会传播 `kwargs` 和 `extra_fields`，当前 visibility 验收覆盖不够。
4. `RepoHarnessRuntime.run_episode(...)` 虽然设计成 async facade，但取消、超时、线程池、Docker / workspace / verifier 清理的规则应从 Stage 2 就固定，不能等到并发安全阶段再补。
5. `training_fast` 的目标正确，但缺少量化吞吐门槛。当前真实 pre-verl 运行目录显示部分单条 run artifact 体积可以达到数百 MB 到 GB 级；并非所有 run 都达到这个量级，最低样本约 94 MB。仅靠“明显减少”这个表述不足以证明在线 rollout 可用。

因此，本报告给出的判断是：计划可以作为主线继续推进，但进入代码实现前应先补一轮 contract hardening。

## 2. 检查依据

本次检查覆盖以下材料：

- 顺序实施计划：`docs/agentic_RL/repo_harness_verl_workstreams/01-sequential-implementation-plan.md`
- shared contracts：`docs/agentic_RL/repo_harness_verl_workstreams/shared_contracts/*.md`
- RepoHarness 当前实现：`src/repo_harness/evaluation/runner.py`、`src/repo_harness/agent_loop/loop.py`、`src/repo_harness/model_client/protocol.py`、`src/repo_harness/reward/*.py`、`src/repo_harness/trajectory/*.py`
- 本地 verl 参考实现：`reference/verl`，当前 HEAD 为 `f400fb76`
- 最新 pre-verl 运行产物：`runs/pre-verl-dev23-formal-reasoning-trace-deepseek-pro-20260512T202939Z/` 和 `runs/pre-verl-swebench-verified-gate50-environment-profiles-20260513T102000Z/`
- 官方 verl 文档：[Agent Loop](https://verl.readthedocs.io/en/latest/advance/agent_loop.html) 和 [Fully Async Policy Trainer](https://github.com/verl-project/verl/blob/main/docs/advance/fully_async.md)

官方 verl 文档说明 Agent Loop 仍处于 alpha 状态，API 未来可能变化；同时明确 `AgentLoopBase.run(...)` 返回 `AgentLoopOutput`，并且多轮训练中不能用最终 chat history 重新分词替代真实每轮 token 拼接。Fully async 文档还明确要求关注 staleness、partial rollout、`use_rollout_log_probs=True` 和 rollout log probability 对算法正确性的作用。

## 3. 已经覆盖较好的部分

### 3.1 shared contract 覆盖面基本完整

计划已经覆盖用户提出的核心对象：

- `RepoHarnessEpisodeRequest`
- `RepoHarnessEpisodeResult`
- `LLMGatewayRequest`
- `LLMGatewayResponse`
- `TrainingView`
- `GenerationRecord`
- `AuditRef`
- `TimingSummary`
- `ResourceSummary`

这些对象分别放在 `shared_contracts/01-episode-contract.md` 到 `shared_contracts/04-timing-and-resource-contract.md` 中，主计划 Stage 0 到 Stage 4 也把它们作为第一批落地内容。这个设计是正确的。

### 3.2 `RepoHarnessRuntime.run_episode(...)` 的职责方向合理

当前 CLI 级 `run_task(...)` 已经串起 task loading、workspace materialization、baseline、agent loop、final verifier、reward、metrics、run metadata 和 artifact finalization。计划要求抽出 `RepoHarnessRuntime.run_episode(request, llm_gateway)`，而不是让 verl adapter 长期调用 CLI，这个判断正确。

这个 runtime facade 能同时服务：

- CLI 测评：CLI 可以构造 request 后调用 runtime。
- ProviderLLMGateway：OpenAI、DeepSeek 和 replay / mock 仍可作为评测、teacher data generation 或调试路径。
- VerlLLMGateway：在线强化学习主线通过 verl 管理的 `LLMServerClient` 调用 vLLM / SGLang。
- 未来 slime 或其他训练后端：只需要实现新的 gateway 和训练视图适配器。

### 3.3 reward 与 verifier 权威边界总体正确

计划明确第一版仍同步等待 final verifier 和 reward，不做 async reward backfill，也不把 verifier 失败伪装成模型负样本。这个边界符合当前 RepoHarness 的 final-only 软件工程任务语义。

当前 RepoHarness 的 `RewardMetadata` 已有 `invalid_for_training` 和 `invalid_reason`，`compute_reward_metadata(...)` 也会把 final verifier timeout、patch apply failed、environment error、low parser confidence 等情况标记为训练无效样本。这为后续 `RepoHarnessEpisodeResult.reward` 和 `TrainingView.reward_score` 打下了基础。

### 3.4 Mac 本地验收和 Vast.ai GPU 验收的分层思路正确

Mac 本地只验证 schema、fake gateway、fake `LLMServerClient`、mask、log probability 长度和 visibility，这是合理边界。真实 vLLM / SGLang、Ray actor、GPU 调度、真实 log probability 和 PPO / GRPO batch smoke 必须放到 Linux GPU 环境验收，这个划分正确。

## 4. 必须修复的问题

### 问题一：`TrainingView -> AgentLoopOutput -> DataProto` 的形状契约还不够严格

严重程度：高。

相关证据：

- `01-sequential-implementation-plan.md` 第 506 到 529 行只要求 `response_ids`、`response_mask`、`response_logprobs` 长度对齐。
- `03-training-view-and-audit-ref-contract.md` 第 107 到 120 行允许 `response_logprobs=None`，但没有定义同一个 batch 中部分样本缺失 log probability 时的规则。
- `reference/verl/verl/experimental/agent_loop/agent_loop.py` 第 572 到 575 行只在 `response_logprobs` 不为空时 padding；第 800 到 802 行只看第一个样本是否有 `response_logprobs` 来决定整个 batch 是否拼 `rollout_log_probs`。
- `reference/verl/verl/experimental/agent_loop/agent_loop.py` 第 822 到 828 行只有所有样本都有 reward score 时才写 `rm_scores`。

当前计划遗漏的具体风险：

1. `TrainingView.response_ids` 超过 `rollout.response_length` 时，计划没有规定是提前终止、截断、标记 invalid，还是让 verl postprocess 处理。静默截断会让 reward、mask 和 patch trajectory 不再一致。
2. `response_logprobs` 在正式 PPO / GRPO 路径中不能部分存在。如果同一个 batch 第一个样本有 log probability、第二个样本没有，verl 当前拼 batch 时容易出现语义错误或运行时错误。
3. 工具 observation token 的 log probability 应统一填 `0.0`，不能让 log probability 数组只覆盖 assistant token。
4. `response_ids` 为空但 `reward_score` 非空时，`AgentLoopOutput.as_dict()` 会尝试把 reward 放到 `rm_scores[-1]`，这类样本必须在进入 verl 前拦截。
5. `prompt_ids` 超过 `rollout.prompt_length` 时也需要明确处理，不能只在 LLMGateway contract 中提醒。

建议补强：

1. Stage 0 contract 增加硬性不变量：
   - `len(prompt_ids) <= rollout.prompt_length`
   - `0 < len(response_ids) <= rollout.response_length`，除非 `invalid_for_training=true`
   - `len(response_ids) == len(response_mask)`
   - 正式 PPO / GRPO batch 中所有样本都必须有 `response_logprobs`
   - `len(response_logprobs) == len(response_ids)`
   - 所有 `response_mask=0` 的工具 observation token 对应 `response_logprobs=0.0`
2. Stage 10 增加 overflow fixture：构造超过 `response_length` 的样本，验收必须看到明确 `status_reason`、`budget_consumption.stop_reason` 和 audit diagnostics。
3. Stage 12 GPU smoke 必须验证 `rollout_log_probs` 出现在 DataProto tensor batch 中，并且形状等于 `[batch_size, rollout.response_length]`。

### 问题二：`AuditRef` 路径可能通过模型工具间接泄漏

严重程度：高。

相关证据：

- `03-training-view-and-audit-ref-contract.md` 第 273 到 300 行定义 `AuditRef` 包含 `run_dir`、`reward_metadata_path`、`final_verifier_path`、`patch_path` 等路径。
- 同一文档第 183 到 216 行规定 `extra_fields` 只放短引用，但建议字段里包含 `audit_ref`。
- `01-episode-contract.md` 第 120 到 129 行禁止 hidden 内容进入 `task_ref`，但没有明确 audit artifact 所在路径是否对模型工具可达。

当前计划已经禁止 hidden verifier、gold patch、reward metadata 直接进入 prompt、response target 和 `extra_fields`，这是必要但不充分的。软件工程 agent 拥有文件读取、grep、list_files、read_tool_result_artifact 等工具。如果 `AuditRef` 暴露的路径可以从模型 workspace 访问，模型仍可能通过工具读取 evaluator-only artifact。

建议补强：

1. 明确 audit artifact 必须位于模型 workspace 之外，且默认不能被模型工具访问。
2. 进入 `AgentLoopOutput.extra_fields` 的 audit 信息必须是 opaque reference，也就是不可由模型工具直接解析成本地路径的非透明引用标识，不是可由模型工具直接读取的本地绝对路径。
3. 工具层增加 denylist 或 capability check，覆盖：
   - run directory
   - acceptance bundle
   - reward metadata
   - final verifier artifact
   - hidden selector
   - hidden test patch
   - gold patch
   - evaluator-only raw output
4. Stage 12 visibility test 不只检查字段内容，还要模拟模型调用 `read_file`、`grep`、`read_tool_result_artifact` 访问这些路径，期望稳定拒绝。

### 问题三：普通 agent loop 之外的 TransferQueue / fully async 路径也会传播隐藏字段

严重程度：高。

相关证据：

- `01-sequential-implementation-plan.md` 第 699 到 718 行把 fully async 放到 Stage 13 预留。
- `reference/verl/verl/trainer/main_ppo_sync.py` 第 414 到 420 行调用 `output.as_dict()` 后执行 `field.update(kwargs)`，这会把 dataset non-tensor fields 继续传播到 TransferQueue。
- 同文件第 353 到 365 行支持 `AgentLoopOutput | list[AgentLoopOutput]`，并且第 384 行仍有 `TODO: Support output:list[AgentLoopOutput]`。
- `reference/verl/verl/protocol.py` 第 461 到 477 行要求 `non_tensor_batch` 是与 batch size 对齐的 `numpy.ndarray`。

当前 shared contracts 已经注意到普通 `_agent_loop_postprocess(...)` 会把 `kwargs["raw_prompt"]` 加到 `extra_fields`。但是 fully async / `main_ppo_sync.py` 路径还会把整个 `kwargs` 更新进 TransferQueue field。这样 hidden metadata、gold patch、accepted label 或大体积字段如果进入 dataset non-tensor fields，就可能绕过 `TrainingView.extra_fields` 检查。

建议补强：

1. Stage 12 visibility 验收同时覆盖：
   - `AgentLoopWorker._agent_loop_postprocess(...)`
   - `main_ppo_sync.py` / TransferQueue 路径
   - DataProto concat / select / pop 后的 non-tensor fields
2. `RepoHarnessVerlAgentLoop` 构造 request 时对 `kwargs` 使用 allowlist，而不是 denylist。第一版只允许：
   - `raw_prompt`
   - `agent_name`
   - `task_id`
   - `run_config_ref`
   - `budget_ref`
   - `agent_policy_ref`
   - `episode_seed`
   - 明确声明的模型可见 context refs
3. `raw_prompt` 只允许模型可见内容。其他 evaluator-only 字段必须只留在 RepoHarness run artifact 中，由 `AuditRef` 间接回查。
4. 对 fully async 的多输出、空输出、cancelled、resumed、stale trajectory，先定义过滤策略，再允许进入训练。

### 问题四：`RepoHarnessRuntime.run_episode(...)` 的取消和清理边界需要前移

严重程度：高。

相关证据：

- `01-sequential-implementation-plan.md` 第 151 到 193 行允许 async facade 内部暂时包同步 agent loop、workspace、verifier 和 recorder。
- 同文档第 486 到 499 行把取消、timeout 和 cleanup 放到 Stage 9 并发安全阶段。
- 当前 `src/repo_harness/evaluation/runner.py::run_task(...)` 在一条同步流程中负责 workspace 创建、agent loop、final verifier、reward 和 `adapter.cleanup_workspaces()`。

把同步流程包进 executor 是可行的过渡方案，但在 verl 的 Ray worker 和 asyncio agent loop 内有几个必须提前固定的问题：

1. 外层 coroutine 被取消时，内部线程中的 workspace 命令、provider 请求、final verifier 是否会继续跑。
2. task timeout 后谁负责 kill 工具进程、Docker 容器、verifier worker。
3. executor 最大并发数如何受 Ray worker、CPU、Docker daemon 和 file descriptor 限制。
4. recorder finalization 和 artifact manifest 写入是否一定执行。
5. cancellation 后返回 `EpisodeResult(status=cancelled)`，还是抛异常交给 verl 标记失败。

建议补强：

1. Stage 2 就定义 cancellation contract，不等 Stage 9。
2. `RepoHarnessRuntime.run_episode(...)` 内部必须有 `try/finally`，确保释放 workspace lease、container lease、artifact writer 和 verifier worker future。
3. `EpisodeResult.status` 需要区分：
   - `timeout`
   - `cancelled`
   - `infrastructure_error`
   - `provider_timeout`
   - `verifier_timeout`
   - `cleanup_failed`
4. 清理失败不能覆盖原始 episode 状态，但必须写入 diagnostics 和 `ResourceSummary.cleanup_status`。
5. Stage 2 fake gateway smoke 应加入取消测试：在 agent loop 中途取消，检查 run directory、workspace lease 和 artifact manifest 状态。

### 问题五：`training_fast` 缺少量化验收，无法证明在线 rollout 吞吐可用

严重程度：中到高。

相关证据：

- `01-sequential-implementation-plan.md` 第 195 到 238 行定义 `training_fast` 减少 raw request / response 和 reasoning trace。
- 同文档第 622 到 629 行只要求 artifact 体积有明显下降。
- `05-acceptance-contract.md` 第 115 到 116 行允许“减少明确类别的大体积 artifact，或达到人工设定的体积下降阈值”，但没有给出第一版阈值。
- 本次抽样 `runs/pre-verl-dev23-formal-reasoning-trace-deepseek-pro-20260512T202939Z/run_task_runs/*`，23 条 run 中单条 run 目录约 94 MB 到 2.1 GB，多条达到数百 MB 到 GB 级。
- 同一批 23 条 run 中，最大 `turn_count=60`，最大 `tool_call_count=66`，有 2 条因为 `budget_exhausted_empty_patch` 标记 `invalid_for_training=true`。

当前计划已经覆盖 workspace snapshot、dependency cache、baseline cache、verifier pool、context slimming、no-progress 和并发安全，但验收仍偏定性。在线强化学习会被固定成本直接卡住，需要可量化门槛。

建议补强：

1. Stage 12 增加固定成本 benchmark，使用 fake gateway 排除模型等待，单独测：
   - workspace materialization seconds
   - setup / dependency restore seconds
   - baseline verifier seconds
   - final verifier seconds
   - artifact write seconds
   - cleanup seconds
2. 第一版建议设定人工阈值，例如：
   - 同一任务 `training_fast` artifact bytes 比 `full_audit` 下降至少 50%，或者明确说明为什么某类任务做不到。
   - fake gateway 下 8 条最小 episode 并发运行，非模型 p95 wall time 必须低于某个预设秒数。
   - 每条 `TimingSummary` 必须能解释至少 95% 的 outer wall time。
3. no-progress 策略需要从“可审计”进一步变成“可训练过滤”：`no_progress` 默认 invalid，只有显式 reward policy 才能作为 negative sample。
4. 如果 artifact 写入仍然占比高，`training_fast` 应支持异步或批量 artifact writer，但必须保证 crash 后仍能通过 audit ref 找到关键证据或明确标记 sample invalid。

### 问题六：多轮 token provenance 需要 span 级别契约

严重程度：中到高。

相关证据：

- `02-llm-gateway-contract.md` 第 140 到 142 行已经禁止使用最终 transcript 重新分词。
- `03-training-view-and-audit-ref-contract.md` 第 232 到 272 行定义 `GenerationRecord`。
- 官方 verl Agent Loop 文档明确指出，对最终 chat history 重新套 chat template 可能得到和每轮真实拼接不同的 token ids，这会让 PPO 轨迹偏离 policy model 分布。

当前 `GenerationRecord` 能记录每轮 `prompt_ids` 和 `output_token_ids`，但还不足以解释最终 `TrainingView.response_ids` 中每个片段来自哪里，尤其是工具 observation token、context compaction token 和截断 token。

建议补强：

1. 在 `TrainingView` 或 `RepoHarnessEpisodeResult` 中增加 `response_spans`，每段至少包含：
   - `start`
   - `end`
   - `source_type`: `assistant_generation`、`tool_observation`、`environment_observation`、`padding_excluded`、`truncated_excluded`
   - `model_call_id`
   - `tool_call_id`
   - `artifact_ref`
   - `response_mask_value`
   - `logprob_policy`
   - `policy_version`
2. Stage 0 canonical fixture 增加至少一个真实多轮工具调用样例：
   - 初始 prompt
   - assistant 生成工具调用
   - tool observation
   - 下一轮 assistant 生成最终回答
   - 对应 `response_ids`、`response_mask`、`response_logprobs` 和 `response_spans`
3. Mac 本地可用小 tokenizer 做结构验收，Vast.ai 必须用真实训练模型 tokenizer / chat template 做同一类验收。

### 问题七：`extra_fields.audit_ref` 和 namespaced flat scalar 字段存在文档内冲突

严重程度：中。

相关证据：

- `03-training-view-and-audit-ref-contract.md` 第 187 到 207 行建议 `extra_fields` 包含 `audit_ref`。
- `01-sequential-implementation-plan.md` 第 735 行要求进入 `AgentLoopOutput.extra_fields` 时采用 namespaced flat scalar 字段。
- `reference/verl/verl/experimental/agent_loop/agent_loop.py` 第 847 到 864 行会把 extra fields 收集成 numpy object arrays，键集合会跨样本合并。

这里的 namespaced flat scalar 字段，是指 `repo_harness_run_id` 这类带命名空间前缀、值为字符串、布尔值或数字的扁平字段，不放嵌套对象。嵌套 `audit_ref` 对象技术上可能能传，但对 DataProto concat、日志、跨进程序列化、TransferQueue、可见性检查和下游过滤都更脆弱，也更容易误带大对象或本地路径。

建议补强：

1. 统一规定：`AgentLoopOutput.extra_fields` 只允许 namespaced flat scalar 字段。
2. 完整结构化 `AuditRef` 留在 `RepoHarnessEpisodeResult.audit_ref` 和 audit artifact 中。
3. 推荐字段：
   - `repo_harness_episode_id`
   - `repo_harness_run_id`
   - `repo_harness_task_id`
   - `repo_harness_audit_manifest_ref`
   - `repo_harness_reward_metadata_ref`
   - `repo_harness_final_verifier_ref`
   - `repo_harness_patch_ref`
   - `repo_harness_timing_summary_ref`
   - `repo_harness_resource_summary_ref`
   - `repo_harness_status`
   - `repo_harness_invalid_for_training`
   - `repo_harness_invalid_reason`
4. 不要把绝对 `run_dir` 直接放入 verl batch。可以放 opaque run ref，由离线审计工具解析。

### 问题八：route 枚举不一致，后续 schema fixture 容易漂移

严重程度：中。

相关证据：

- `02-llm-gateway-contract.md` 第 57 到 68 行定义 route 为 `verl`、`openai`、`deepseek`、`local_vllm`、`sglang`、`replay`、`mock`。
- `01-sequential-implementation-plan.md` 第 310 到 318 行使用 `local_sglang` 和 `verl_llm_server_client`。

建议补强：

1. 在 shared contract 中固定唯一枚举：
   - `verl`
   - `openai`
   - `deepseek`
   - `local_vllm`
   - `local_sglang`
   - `replay`
   - `mock`
2. 如果需要区分 `verl` 后端内部的 vLLM / SGLang，应使用 `inference_backend` 字段，不要通过 route 名称混用。
3. canonical fixture 和 pydantic schema 必须拒绝未登记 route。

### 问题九：Mac 与 Vast.ai 验收划分合理，但版本锁定和 vLLM parity 需要更早

严重程度：中。

相关证据：

- `01-sequential-implementation-plan.md` 第 631 到 662 行定义 Mac 本地结构验收。
- 同文档第 664 到 697 行定义 Vast.ai GPU 训练前验收。
- 官方 verl Agent Loop 文档声明 Agent Loop added in version 0.4.2 且为 alpha，API 未来可能变化。
- 本地 `reference/verl` 当前 HEAD 是 `f400fb76`，并且 `git status` 显示 `CLAUDE.md` 存在 typechange，另有未跟踪的 `AGENT.md`。

当前分层是正确的，但需要补上版本治理：

1. Stage 0 应固定 verl commit、Python 版本、Ray 版本、vLLM 版本、SGLang 版本、transformers 版本和 tokenizer / chat template 来源。
2. Mac `pip install --no-deps -e reference/verl` 只能证明导入层面，不足以证明 Hydra registry、DataProto、AgentLoopWorker postprocess 和 TransferQueue 路径可用。
3. Vast.ai 第一轮以 SGLang 为主可以接受，但同一阶段应至少跑一条 vLLM contract smoke，验证真实 `TokenOutput.token_ids`、`log_probs`、`stop_reason`、`extra_fields.global_steps` 的映射。
4. 如果镜像里先有 vLLM 而没有 SGLang，可以先用 vLLM，但必须记录 preflight 原因和后续 SGLang parity 任务。

### 问题十：fully async 预留还缺少与算法正确性直接相关的字段门槛

严重程度：中。

相关证据：

- `01-sequential-implementation-plan.md` 第 703 到 718 行只列出 policy version、global steps、staleness 和 async reward backfill 等预留项。
- `reference/verl/verl/workers/rollout/llm_server.py` 第 231 到 249 行在 partial rollout 合并时写入 `global_steps`、`min_global_steps` 和 `max_global_steps`。
- 官方 fully async 文档说明 `actor_rollout_ref.actor.use_rollout_log_probs=True` 用于确保 old log probability 对应 rollout 参数和 token；`staleness_threshold` 与 `partial_rollout` 会影响样本新鲜度。

建议补强：

1. `GenerationRecord` 不只保留一个 `policy_version` 对象，还应保留原始 verl 字段：
   - `global_steps`
   - `min_global_steps`
   - `max_global_steps`
2. 如果一条 trajectory 跨多个参数版本，必须能按 token span 或 model call span 追踪版本范围。
3. Stage 13 前置验收应检查：
   - `actor_rollout_ref.actor.use_rollout_log_probs=True`
   - `algorithm.rollout_correction.bypass_mode` 的选择被记录
   - stale trajectory 的过滤或权重策略被记录
   - partial rollout 中断后 workspace lease 不会丢失或污染
4. async reward backfill 第一版不做是正确的，但需要明确未来实现时不能把无 reward 样本伪装成普通成功样本。

### 问题十一：required / optional / default 字段级契约仍偏粗

严重程度：中。

相关证据：

- `01-sequential-implementation-plan.md` 第 62 到 64 行要求确认必填字段和可选字段。
- `05-acceptance-contract.md` 第 124 到 125 行要求新增字段标记 required / optional / default。
- 但当前 shared contract 的大多数字段列表还没有逐字段标注缺失时的行为。

建议补强：

1. Stage 0 为每个字段补充：
   - `required`
   - `optional`
   - `default`
   - 缺失时是 schema error、runtime invalid，还是允许 adapter 填默认值
   - 是否允许进入 verl non-tensor batch
   - 是否模型可见
   - 是否 evaluator-only
2. 对 `extra`、`extra_fields`、`provider_options`、`tracing` 这类开放字段必须加 allowlist 或 namespaced policy。

### 问题十二：Reward、accepted label 和 run outcome 的训练可见性需要更细分

严重程度：中。

计划已经禁止 accepted label 进入 prompt，这是正确的。但 training result 里仍然需要 reward scalar、status、invalid reason、final verifier ref。这里需要区分“训练器消费”和“模型可见”：

1. `reward_score` 可以进入 `rm_scores`。
2. `repo_harness_status`、`repo_harness_invalid_for_training` 可以进入 non-tensor batch 用于过滤。
3. `accepted`、`final_verifier_status`、`run_outcome` 是否进入 non-tensor batch，需要明确用途。如果只是日志和筛选，应放在 namespaced 字段并确保不会进入 prompt 或工具 observation。
4. `raw_prompt` 不能带 accepted label，也不能带隐藏测试名称、隐藏 selector 或 gold patch 片段。
5. verl 不会因为 non-tensor metadata 中的 `invalid_for_training=true` 自动过滤样本。因此在 DataProto 进入 PPO / GRPO 有效 batch 前，必须有显式过滤、置零 loss weight 或丢弃策略，并在 smoke 中验证 invalid 样本不会参与 loss。

建议补强：

1. 建立 `training_visibility_policy`，把字段分成：
   - model visible
   - trainer tensor
   - trainer non-tensor filter
   - audit only
   - forbidden
2. Stage 12 postprocess test 检查最终 DataProto 的 tensor batch、non-tensor batch 和 meta_info。

### 问题十三：现有 provider route 与正式 online RL route 的训练可用性要更硬地区分

严重程度：中。

`ProviderLLMGateway` 包装 OpenAI / DeepSeek provider client 对评测和 teacher data generation 有价值，但大多数 provider 路径不能可靠返回每个 token 的真实 token ids 和 log probability。计划已经要求标记 `token_source=provider_unavailable` 或 `re_tokenized_debug_only`，但验收还应更硬。

建议补强：

1. 正式 online PPO / GRPO 路径只允许 `route=verl`。
2. provider route 产出的 `TrainingView` 默认 `invalid_for_online_rl=true`，除非明确证明 token provenance 和 log probability 满足要求。
3. provider route 可以进入：
   - SFT export
   - preference data
   - teacher data generation
   - offline diagnostic replay
4. provider route 不能伪装成 rollout policy sample，也就是不能伪装成由当前训练 policy 在 rollout server 中真实采样得到、可用于 PPO / GRPO policy loss 的样本。

### 问题十四：tool parser 责任边界还需要写入 contract

严重程度：中。

相关证据：

- `02-llm-gateway-contract.md` 第 201 到 215 行提到 route=verl 时可能复用 RepoHarness tool parser 或 verl tool parser，并建议保持 RepoHarness tool contract 为准。
- 官方 verl Agent Loop 文档指出 tool parser 可能改变 assistant message 内容，导致重新编码后的 token ids 和真实生成 token ids 不一致。

建议补强：

1. 第一版固定 RepoHarness tool call parser 为权威 tool semantics。
2. `LLMGatewayResponse.output_token_ids` 必须保留模型原始生成 token。
3. `assistant_message` 和 `tool_calls` 可以是 parser 后的结构化结果，但不能反过来用于构造训练 token。
4. 如果 parser 修复了 malformed tool call，应记录：
   - 原始 output token ids
   - parser id
   - parser repair type
   - repair 是否进入模型可见 observation
   - 该段 response mask 是否仍然为 1

### 问题十五：current run 产物说明训练前优化优先级应更明确

严重程度：中。

本次抽样最新 pre-verl 23 题运行产物得到：

```text
run count: 23
final_verifier_status:
  accepted: 10
  rejected: 11
  not_executed: 2
reward invalid_for_training: 2
invalid reason:
  budget_exhausted_empty_patch: 2
max turn_count: 60
max tool_call_count: 66
largest sampled run directory size: 2.1 GB
```

这些事实说明 RepoHarness 现在已经能产出真实、可审计的 agent trajectory，但还不是天然适合 online RL rollout 的 runtime。计划中 `training_fast`、workspace snapshot、context slimming、no-progress 和并发安全都很必要。建议在计划中明确第一版优化顺序：

1. 先用 fake gateway 压测非模型固定成本。
2. 再用 route=verl 压测真实模型等待和 server batching。
3. 最后才尝试 PPO / GRPO trainer batch。

## 5. 建议修改的阶段门槛

### Stage 0 应新增的门槛

1. 每个字段标注 required / optional / default / visibility / batch propagation。
2. 固定唯一 route 枚举。
3. 增加 canonical fixture：
   - 单轮成功样本
   - 多轮工具调用样本
   - final verifier rejected 样本
   - infrastructure error 样本
   - empty response invalid 样本
   - response overflow invalid 样本
   - mixed log probability batch rejection 样本
   - audit path access denial 样本
4. 增加 `response_spans` 或等价 span 级 token provenance fixture。这里的 span 级 token provenance，是指把 `response_ids` 按连续片段标明来源，例如某一段来自 assistant 生成、某一段来自工具观察、某一段因为超长被排除。
5. 固定 verl commit 和 GPU 环境依赖矩阵。

### Stage 2 应新增的门槛

1. cancellation contract。
2. executor 并发上限。
3. workspace / container / verifier / recorder cleanup 的 ownership。
4. cancellation smoke。
5. timeout 后仍能产出最小 `EpisodeResult` 或明确 infrastructure error artifact。

### Stage 3 应新增的门槛

1. `training_fast` 体积下降阈值。
2. artifact 类别级统计。
3. fake gateway 固定成本 benchmark。
4. crash 后 audit ref 完整性检查。

### Stage 10 应新增的门槛

1. 使用真实本地 `reference/verl` 的 `AgentLoopOutput` 和 postprocess 行为做测试，而不是只用自定义 dataclass 模拟。
2. 检查 `rollout_log_probs`、`rm_scores`、`response_mask`、`non_tensor_batch`、`meta_info`。
3. 检查 batch 内所有样本的 log probability 一致性。
4. 检查 nested object 不进入 `extra_fields`。

### Stage 11 应新增的门槛

1. `RepoHarnessVerlAgentLoop` 通过 Hydra config 注册。
2. adapter import 不强迫普通 RepoHarness CLI 安装完整 verl。
3. `kwargs` allowlist 生效。
4. fake `LLMServerClient.generate(...)` 返回 `TokenOutput` 后能构造 `GenerationRecord`。
5. sticky session 使用 `LLMServerClient.generate(request_id=episode_id, ...)` 的外层 `request_id`，不要混淆内部 server request id。

### Stage 12 应新增的门槛

1. 普通 `AgentLoopWorker` 路径和 `main_ppo_sync.py` / TransferQueue 路径都做 visibility test。
2. SGLang 真实 smoke 和 vLLM contract smoke 同阶段完成，允许一个主验收、一个 parity smoke。
3. PPO / GRPO smoke 明确要求：
   - `actor_rollout_ref.rollout.calculate_log_probs=True`
   - `rollout_log_probs` 存在
   - `rm_scores` 存在或样本被过滤
   - invalid 样本不进入有效 batch，或者进入前被明确置零训练权重并在 metrics 中可见
4. 记录 Ray placement、CPU worker、GPU server、workspace worker 的资源关系。

## 6. 总体建议

建议先不要直接开始 Stage 1 代码实现。更稳妥的下一步是新增一个 `contract_hardening_v1` 文档补丁，修改 shared contracts 和顺序实施计划，重点补下面六件事：

1. 严格的 token / mask / log probability / length / batch shape 规则。这里的 batch shape，是指进入 verl `DataProto` 后各个 tensor 和 non-tensor field 的 batch 维度、序列长度和 padding 规则必须一致。
2. audit ref 的工具不可达性和 opaque reference 规则。
3. `kwargs`、`raw_prompt`、TransferQueue、DataProto non-tensor fields 的 allowlist。
4. `run_episode(...)` 的取消、超时和资源清理 contract。
5. `training_fast` 的量化吞吐验收。
6. 多轮工具调用的 span 级 token provenance fixture。

补完这些后，当前路线可以进入实现。实现顺序仍建议保持原计划：contract fixture、schema 包、runtime facade、training_fast、timing/resource、LLMGateway、环境复用、verifier pool、预算和 no-progress、并发安全、TrainingView converter、verl adapter、端到端 smoke、fully async 预留。

## 7. Subagent 复核状态

本报告在初稿前已经经过一个只读 subagent 独立复核。该 subagent 的主要结论是：总体计划合理，但需要优先补强 token/log probability/DataProto 形状契约、audit 路径工具可达性隔离、TransferQueue / fully async visibility 覆盖、runtime cancellation contract、`training_fast` 量化门槛、多轮 tokenizer golden fixture、vLLM / SGLang parity、route 枚举一致性和字段 required / optional / default 标注。

本报告初稿完成后，又经过第二个只读 subagent 检查。第二次检查确认覆盖面和证据链基本完整，并要求修正 run 目录体积范围、闭合 subagent 复核状态、补充 invalid 样本进入 trainer 前的硬过滤门槛，以及补充 opaque reference、namespaced flat scalar 字段、policy sample、batch shape 和 span 级 token provenance 的中文解释。当前版本已经吸收这些修正。后续如果 shared contracts 或 verl 版本发生变化，需要重新复核。
