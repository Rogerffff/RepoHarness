# Stage 0H 执行单：Contract Hardening V1

```text
status: execution_brief_ready_for_stage0h
scope: planning_and_acceptance_gate_not_runtime_implementation
owner: RepoHarness core / verl adapter integration
depends_on:
  - 01-sequential-implementation-plan.md
  - shared_contracts/02-llm-gateway-contract.md
  - shared_contracts/03-training-view-and-audit-ref-contract.md
  - shared_contracts/05-acceptance-contract.md
  - shared_contracts/06-contract-hardening-v1.md
```

## 1. Stage 0H 在做什么

Stage 0H 是 Stage 0 和 Stage 1 之间的实施关口。Stage 0 冻结对象名称、字段范围和共享 contract 文档；Stage 0H 进一步把这些字段的训练语义、安全边界和验收方式固定下来。它不实现完整 `RepoHarnessRuntime.run_episode(...)`，不接入真实 verl server，也不提前编写 `TrainingView -> AgentLoopOutput` 的完整转换器。

这一阶段要回答的问题是：一条 RepoHarness 轨迹在进入 verl 训练之前，必须满足哪些不可商量的条件。如果这些条件没有提前固定，后续很容易出现“接口可以调用，但是 token、mask、log probability、reward、hidden metadata 或 audit reference 已经错了”的情况。这样的错误通常不会在最小 smoke test 中立即暴露，但会在 PPO / GRPO batch、verl postprocess、TransferQueue 或 DataProto 组装阶段造成训练语义错误。

## 2. 本阶段必须交付的文件

Stage 0H 的主要交付物是 fixture、最小测试和验收报告位置，不是大规模功能代码。

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

tests/unit/
  test_repo_harness_verl_contract_fixtures.py
  test_repo_harness_verl_stage0h_shape_rules.py
  test_repo_harness_verl_stage0h_visibility.py
```

建议验收产物输出到：

```text
runs/repo-harness-verl-stage0h-<timestamp>/
  stage0h_command_log.jsonl
  contract_fixture_sha256_report.json
  shape_rule_report.json
  visibility_matrix_report.json
  blocked_by_stage_report.json
```

`blocked_by_stage_report.json` 用于记录那些已经确定必须测试、但要等 Stage 1、Stage 2、Stage 3、Stage 10 或 Stage 12 才能真正执行的检查。允许存在 blocked 项，但每一项必须写清楚解除阶段、解除条件和对应测试文件。

## 3. 必须立即通过的检查

Stage 0H 完成时，下面检查必须已经可以运行并通过：

1. 所有 fixture 都是合法 JSON。
2. `sha256_manifest.json` 覆盖全部 canonical fixture，并且重复运行时 hash 稳定。
3. fixture 中不出现绝对 `run_dir`、本地 reward metadata 绝对路径、final verifier 绝对路径、gold patch 路径或嵌套 audit ref 对象。
4. fixture 中的 `LLMGateway.route` 只使用 `verl`、`openai`、`deepseek`、`local_vllm`、`local_sglang`、`replay`、`mock`。
5. provider route fixture 默认带有 `invalid_for_online_rl=true` 或等价的训练无效标记，不能伪装成当前 rollout policy sample。
6. `canonical_multiturn_tool_episode_result.json` 必须包含 `response_spans`，并能解释 assistant generation、tool observation、environment observation、padding excluded 或 truncated excluded 的 token 来源。每段至少包含 `start`、`end`、`source_type`、`model_call_id`、`tool_call_id`、`artifact_ref`、`response_mask_value`、`logprob_policy`、`policy_version`、`global_steps`、`min_global_steps` 和 `max_global_steps`。
7. `canonical_response_overflow_invalid_result.json` 必须明确 `invalid_for_training=true`、`status_reason`、`budget_consumption.stop_reason` 和 audit diagnostics。
8. `canonical_empty_response_invalid_result.json` 必须证明空 `response_ids` 不能带着普通有效 `reward_score` 进入训练。
9. `canonical_mixed_logprob_batch_rejected.json` 必须表达同一正式 PPO / GRPO batch 中部分样本缺失 `response_logprobs` 时应被拒绝或整体标记 invalid。
10. visibility denylist 基线必须覆盖 hidden verifier、gold patch、accepted label、完整 reward metadata、provider secret、evaluator-only logs、绝对 run directory 和 final verifier artifact。

## 4. 允许先记录为 blocked-by-stage 的检查

下面检查不要求 Stage 0H 当场全部实现，但必须先在测试名称、fixture 输入和期望失败原因上固定下来：

| 检查 | 解除阶段 | Stage 0H 必须先记录的内容 |
| --- | --- | --- |
| `RepoHarnessEpisodeRequest`、`TrainingView`、`AuditRef` 的正式 schema roundtrip | Stage 1 | fixture 路径、期望字段、非法字段拒绝原因、contract version。 |
| `RepoHarnessRuntime.run_episode(...)` 中途取消 smoke | Stage 2 | 取消发生点、最小 `EpisodeResult` 字段、cleanup diagnostics 字段。 |
| timeout 后最小 result 或 infrastructure error artifact | Stage 2 | episode timeout、provider timeout、verifier timeout、Docker command timeout 的 ownership。 |
| `training_fast` 量化门槛 | Stage 3 | benchmark 输入、同一任务 `full_audit` 与 `training_fast` artifact bytes 对比字段、fake gateway 8 条最小 episode 非模型 p95 wall time 字段、`TimingSummary` 解释率字段、未达到 50% / 180 秒 / 95% 阈值时的失败原因字段。 |
| `TrainingView -> AgentLoopOutput` converter shape check | Stage 10 | `prompt_ids`、`response_ids`、`response_mask`、`response_logprobs`、`reward_score` 和 `extra_fields` 的期望映射。 |
| verl postprocess 后 `raw_prompt` visibility | Stage 10 / Stage 12 | `kwargs["raw_prompt"]` 的 allowlist、postprocess 后检查点和泄漏拒绝原因。 |
| TransferQueue / DataProto visibility | Stage 12 | `tensor_batch`、`non_tensor_batch`、`meta_info` 的字段 visibility、batch dimension 和 invalid 样本处理规则。 |
| DataProto shape | Stage 10 / Stage 12 | `rollout_log_probs`、`rm_scores`、`response_mask`、`tensor_batch`、`non_tensor_batch` 和 `meta_info` 的 batch 维度、padding 规则、`[batch_size, rollout.response_length]` 形状要求，以及 invalid 样本过滤或置零 loss weight 的显式记录方式。 |
| Mac 本地结构验收与 Vast.ai 真实训练前验收分层 | Stage 12-A / Stage 12-B | Mac 本地只证明 fake / lite 结构、字段和 visibility 正确；Vast.ai 或同类 Linux GPU 环境必须证明真实 verl server manager、vLLM / SGLang、真实 log probability、Ray GPU scheduling 和 PPO / GRPO batch smoke 可用。 |
| Vast.ai 真实 route=verl log probability 和 `rollout_log_probs` shape | Stage 12-B | 真实 tokenizer / chat template、真实 `TokenOutput.token_ids`、真实 `TokenOutput.log_probs` 和 `[batch_size, rollout.response_length]` 形状要求。 |

## 5. 建议验收命令

Stage 0H 最小验收命令如下。若某个测试文件在首次执行时还不存在，Stage 0H 的第一项代码工作就是创建该测试文件；不能用“暂无实现”悄悄跳过。

```bash
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_repo_harness_verl_contract_fixtures.py
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_repo_harness_verl_stage0h_shape_rules.py
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_repo_harness_verl_stage0h_visibility.py
```

如果 Stage 0H 实现时还没有正式 schema 包，测试可以只做 JSON、hash、字段存在性、字段禁止项和 blocked-by-stage report 检查。等 Stage 1 创建 `src/repo_harness/rl/` 后，再把同一批 fixture 接入 schema roundtrip。

## 6. 不允许做的事情

1. 不允许把 provider route 样本当作正式 online PPO / GRPO rollout policy sample。
2. 不允许把完整 `AuditRef` 嵌套对象放入 `AgentLoopOutput.extra_fields`。
3. 不允许把绝对 `run_dir`、reward metadata 本地路径、final verifier 本地路径或 gold patch 路径放入可传播 batch 字段。
4. 不允许在没有 `response_logprobs` 的情况下声称样本可进入正式 PPO / GRPO batch。
5. 不允许让空 `response_ids` 且带普通有效 `reward_score` 的样本进入 verl postprocess。
6. 不允许用最终 transcript 重新分词来伪造 route=verl 的正式训练 token provenance。
7. 不允许把 hidden verifier、gold patch、accepted label 或 evaluator-only logs 放进 `raw_prompt`、response target、TransferQueue 或 `DataProto.non_tensor_batch`。
8. 不允许用“后续再补”替代 blocked-by-stage 记录；每个未实现检查都必须有解除阶段。

## 7. 进入 Stage 1 的判定标准

只有同时满足下面条件，才允许进入 Stage 1 的 schema 包和最小 `LLMGateway` 实现：

1. 本执行单列出的 fixture 文件已经创建，JSON 可解析，sha256 manifest 稳定。
2. 三个 Stage 0H 最小测试文件已经存在，并且所有不依赖后续阶段的检查通过。
3. 所有依赖 Stage 1、Stage 2、Stage 3、Stage 10 或 Stage 12 的检查都写入 `blocked_by_stage_report.json`。
4. 文档、fixture 和 HTML 汇报页中的 route 枚举、visibility denylist、opaque audit ref、`response_spans`、provider `invalid_for_online_rl`、`training_fast` 量化门槛、DataProto shape 和 Mac / Vast.ai 分层验收保持一致。
5. 没有残留旧式字段传播说法，例如把嵌套 audit ref 对象、绝对 `run_dir` 或 provider route online RL 样本放入 `AgentLoopOutput.extra_fields`。

满足这些条件后，Stage 1 的实现 agent 可以开始创建 `src/repo_harness/rl/episode.py`、`gateway.py`、`training_view.py`、`timing.py` 和 `visibility.py`，并用 Stage 0H 的 fixture 作为第一批 schema roundtrip 和非法字段拒绝测试输入。
