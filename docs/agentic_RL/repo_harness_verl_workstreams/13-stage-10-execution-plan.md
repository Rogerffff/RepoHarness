# Stage 10 执行计划：TrainingView 到 verl AgentLoopOutput 的转换

状态：待实施。本文件只定义 Stage 10 的执行计划，还没有开始代码实现。

前置状态：

- Stage 0H 到 Stage 8 已完成。
- Stage 9 已完成资源租约、并发安全、cleanup / verifier 取消语义、workspace snapshot 符号链接硬化、正式 online RL batch 闸门和相关测试，主提交为 `cc804acc`。
- 剩余同步改动已提交为 `78c03de7`，其中 `reference/verl` 子模块指向本地文档整理提交 `ba8cfb6d`。

## 1. 阶段目标

Stage 10 的目标是在真正实现 `RepoHarnessVerlAgentLoop` 和 `VerlLLMGateway` 之前，先把 RepoHarness 已经稳定下来的 `TrainingView` 转换成 verl agent loop 可消费的 `AgentLoopOutput`，并验证经过 verl 自己的 postprocess 和 batch 组装路径后，训练字段和可见性边界仍然成立。

核心转换关系是：

```text
TrainingView.prompt_ids        -> AgentLoopOutput.prompt_ids
TrainingView.response_ids      -> AgentLoopOutput.response_ids
TrainingView.response_mask     -> AgentLoopOutput.response_mask
TrainingView.response_logprobs -> AgentLoopOutput.response_logprobs
TrainingView.reward_score      -> AgentLoopOutput.reward_score
TrainingView.num_turns         -> AgentLoopOutput.num_turns
TrainingView.verl_metrics      -> AgentLoopOutput.metrics
TrainingView.extra_fields      -> AgentLoopOutput.extra_fields
AuditRef                       -> 只投影为 repo_harness_* opaque refs
```

完成后应该能证明：

1. `TrainingView` 可以稳定转换为本地 `reference/verl` 中真实的 `AgentLoopOutput`，而不是只转换成 RepoHarness 自己定义的模拟对象。
2. `AgentLoopOutput.as_dict()` 之后会生成 verl 期望的 `prompts`、`responses`、`response_mask`、`rollout_log_probs` 和 `rm_scores`。
3. `AgentLoopWorker._agent_loop_postprocess(...)` 自动加入的 `extra_fields.raw_prompt`，以及 `main_ppo_sync.py` / TransferQueue 路径通过 `field.update(kwargs)` 合并进去的顶层 `raw_prompt`，都通过模型可见性检查。
4. `AgentLoopWorker._postprocess(...) -> DataProto` 后，tensor batch、non-tensor batch 和 meta_info 的 batch 维度、序列长度和 visibility 仍然正确。
5. `main_ppo_sync.py` / TransferQueue 路径不会因为 `field.update(kwargs)` 把 hidden verifier、gold patch、accepted label、完整 reward metadata 或本地绝对路径带进训练队列。

## 2. 必须保持的边界

1. Stage 10 不实现 `RepoHarnessVerlAgentLoop`，不实现 `VerlLLMGateway`，不启动 Ray、vLLM、SGLang 或真实 verl trainer。
2. Stage 10 不改写 RepoHarness core 的 LLM 调用逻辑，不重新实现 runtime，不绕过 Stage 1 到 Stage 9 已经固定的 schema、runtime、resource、budget、visibility 和 reward 边界。
3. `src/repo_harness/rl/` 仍然不能静态 import `verl`。任何依赖真实 verl 类型的转换代码必须放在可选 adapter 层，建议放在 `src/repo_harness_verl/`。
4. 普通 RepoHarness CLI、外部 provider 评测和 teacher data 路径不能因为 Stage 10 强制安装完整 verl 依赖。
5. Stage 10 不通过最终文本重新分词来伪造正式训练 token。转换只能使用 `TrainingView` 中已有的 `prompt_ids`、`response_ids`、`response_mask`、`response_logprobs` 和 `response_spans`。
6. 不在 RepoHarness 自己的 `AgentLoopOutput.extra_fields` 中提前写 `raw_prompt`。在普通 `AgentLoopWorker._agent_loop_postprocess(...)` 路径中，`raw_prompt` 会从 `kwargs["raw_prompt"]` 写入 `extra_fields.raw_prompt`；在 `main_ppo_sync.py` / TransferQueue 路径中，`raw_prompt` 会通过 `field.update(kwargs)` 成为顶层 field。Stage 10 必须同时验证这两个位置的可见性。
7. `AuditRef` 不能作为嵌套对象进入 `AgentLoopOutput.extra_fields`、DataProto non-tensor batch 或 TransferQueue field。只能投影为 `repo_harness_*` namespaced flat scalar 和 opaque refs。
8. 正式 online PPO / GRPO 第一版只允许 `route=verl`，并且必须有 `response_logprobs`。`mock`、`replay`、`openai`、`deepseek`、`local_vllm`、`local_sglang` 产生的样本不能被 converter 误标成 formal online RL 可训练样本。
9. invalid 样本不能悄悄参与 policy loss。如果 Stage 10 第一版选择拒绝 invalid 样本，这是最保守路线；如果选择输出 diagnostic-only `AgentLoopOutput`，必须显式设置不可训练字段并在 DataProto 检查中可见。

## 3. 建议新增模块

建议新增可选 adapter 包：

```text
src/repo_harness_verl/
  __init__.py
  conversion.py
  visibility.py
```

职责建议：

```text
conversion.py:
  training_view_to_agent_loop_output(...)
  episode_result_to_agent_loop_output(...)
  build_agent_loop_metrics(...)
  project_audit_refs_for_extra_fields(...)
  validate_training_view_for_agent_loop_output(...)

visibility.py:
  validate_agent_loop_output_extra_fields(...)
  validate_postprocessed_extra_fields(...)
  validate_dataproto_visibility(...)
  validate_transfer_queue_field_visibility(...)
```

导入策略：

- `repo_harness_verl.conversion` 可以在函数内部或模块顶部 import `verl.experimental.agent_loop.agent_loop.AgentLoopOutput` 和 `AgentLoopMetrics`。
- `repo_harness.rl` 不能 import `repo_harness_verl`，避免 core 反向依赖 adapter。
- 测试使用 `PYTHONPATH=src:reference/verl` 或等价方式加载本地 `reference/verl`。
- 如果本地环境缺少 verl 运行所需依赖，Stage 10 的第一项工作是补齐明确的测试依赖或给出可执行的本地 preflight，而不是退回到自定义 dataclass 假对象。

## 4. 转换规则

### 4.1 正式 online RL 转换入口

建议提供严格入口：

```python
def training_view_to_agent_loop_output(
    training_view: TrainingView,
    *,
    audit_ref: AuditRef | None = None,
    formal_online_rl: bool = True,
) -> AgentLoopOutput:
    ...
```

当 `formal_online_rl=True` 时必须先调用现有 helper：

```python
validate_training_view_for_online_rl(training_view, require_explicit_eligibility=True)
```

随后还必须检查：

- `response_ids` 非空。
- `reward_score` 非空。
- `response_logprobs` 非空。
- `response_ids`、`response_mask`、`response_logprobs` 长度一致。
- `len(prompt_ids) <= rollout.prompt_length` 和 `len(response_ids) <= rollout.response_length` 的检查要么由调用方传入 rollout limits，要么使用 `TrainingView.rollout_limits`。
- `response_mask=0` 的 token 对应 `response_logprobs=0.0`。
- `extra_fields["repo_harness_llm_gateway_route"] == "verl"`。

如果任何检查失败，converter 必须抛出结构化错误或返回明确 invalid，不允许截断后继续训练。

注意：Stage 0H 的旧 canonical `canonical_training_view.json` 缺少 `extra_fields.repo_harness_llm_gateway_route`，因此不能直接当作 formal online RL 样本。它只用于 schema roundtrip 和字段稳定性测试。formal online RL 转换测试必须使用 Stage 10 专用样本，该样本可以基于 canonical fixture 显式补入 `repo_harness_llm_gateway_route="verl"`，也可以从 `canonical_episode_result.json` 的 `generation_records` 明确投影得到。用 `generation_records` 投影 route 时，必须先确认 `generation_records` 非空，并且所有 `generation_records[*].gateway_route` 都是 `verl`；不能只看第一条记录。converter 不能自己隐式猜测 route。

### 4.2 metrics 映射

`TrainingView.verl_metrics` 只能映射到 verl `AgentLoopMetrics` 已支持字段：

```text
generate_sequences
tool_calls
compute_score
num_preempted
```

其他 RepoHarness 详细 metrics 不应该硬塞进 `AgentLoopMetrics`。这些字段必须通过以下方式保留：

```text
TrainingView.repo_harness_metrics_ref
TrainingView.extra_fields.repo_harness_timing_summary_ref
TrainingView.extra_fields.repo_harness_resource_summary_ref
RepoHarnessEpisodeResult.audit_ref
```

如果 `TrainingView.verl_metrics` 中出现 verl 不支持的字段，第一版应拒绝或记录 diagnostics，不要静默丢弃。

### 4.3 extra_fields 和 AuditRef 投影

转换后的 `AgentLoopOutput.extra_fields` 只能包含：

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
repo_harness_metrics_ref
repo_harness_status
repo_harness_invalid_for_training
repo_harness_invalid_reason
repo_harness_invalid_for_online_rl
repo_harness_llm_gateway_route
```

如需从 `AuditRef` 补字段，只能补 opaque refs。例如：

```text
AuditRef.important_artifact_refs["artifacts_manifest"]
  -> extra_fields["repo_harness_audit_manifest_ref"]
```

禁止：

```text
extra_fields["audit_ref"] = {...}
extra_fields["repo_harness_audit_ref"] = {...}
extra_fields["run_dir"] = "/Users/..."
extra_fields["reward_metadata_path"] = "/Users/..."
extra_fields["final_verifier_path"] = "/Users/..."
```

转换后必须复用 Stage 1 到 Stage 9 的 `validate_batch_extra_fields(...)` 和可见性 denylist。

还要特别处理 verl 自身的保留字段：

- 不使用 `teacher_ids` 和 `teacher_logprobs` 作为 RepoHarness 字段名。`AgentLoopOutput.as_dict()` 会从 `extra_fields` 中取出这些字段并放入 tensor 输出，使用这两个名字会改变 batch 语义。
- 不使用 `raw_prompt` 作为 RepoHarness 自己的 converter 输出字段。该字段由 `AgentLoopWorker._agent_loop_postprocess(...)` 从 `kwargs["raw_prompt"]` 写入。
- 不把 `reward_extra_info`、`reward_extra_keys`、`extra_info`、`ground_truth` 或 `accepted_label` 当作 RepoHarness 审计字段传播。verl reward 路径会读取这些名字，RepoHarness 的完整 reward 证据必须通过 opaque ref 反查。
- converter 输出前后都要检查 `extra_fields` 没有被 `as_dict()` 的特殊逻辑悄悄改写成不同语义。测试中应当使用一个副本调用 `as_dict()`，避免同一个 `AgentLoopOutput` 对象被原地修改后影响后续断言。

### 4.4 raw_prompt 处理

Stage 10 不负责构造 `RepoHarnessEpisodeRequest`，但必须验证未来 Stage 11 会遇到的 postprocess 行为。

测试要模拟两条真实 verl 路径。

第一条是普通 agent loop worker postprocess：

```text
AgentLoopOutput.extra_fields 由 converter 生成
AgentLoopWorker._agent_loop_postprocess(...) 自动执行：
  output.extra_fields["raw_prompt"] = kwargs["raw_prompt"]
```

第二条是 `main_ppo_sync.py` / TransferQueue 路径：

```text
field = output.as_dict()
field.update(kwargs)
raw_prompt 作为顶层 field 进入 TransferQueue，而不是进入 extra_fields.raw_prompt
```

要求：

- `kwargs["raw_prompt"]` 只能包含模型可见内容。
- postprocess 后的 `extra_fields.raw_prompt` 必须通过 visibility 检查。
- TransferQueue 顶层 `raw_prompt` 也必须通过 visibility 检查。
- hidden verifier、gold patch、accepted label、provider secret、完整 reward metadata、evaluator-only logs 不得出现在任意位置的 `raw_prompt`、`extra_fields`、TransferQueue field 或 DataProto non-tensor batch 中。

## 5. verl 真实行为测试要求

Stage 10 的测试不能只验证自定义转换对象。至少要使用本地 `reference/verl` 的这些真实对象或方法：

```text
verl.experimental.agent_loop.agent_loop.AgentLoopOutput
verl.experimental.agent_loop.agent_loop.AgentLoopMetrics
AgentLoopOutput.as_dict()
AgentLoopWorker._agent_loop_postprocess(...)
AgentLoopWorker._postprocess(...)
```

如果直接实例化 `AgentLoopWorker` 依赖较重，可以在测试中创建最小对象并绑定必要属性，但调用的 postprocess 方法必须来自 `reference/verl` 源码本身。

建议测试方式：

1. 用最小 fake tokenizer 实现 `pad(...)`、`decode(...)` 和 `pad_token_id`，只服务 Stage 10 结构测试。
2. 用最小 fake rollout config 提供 `prompt_length` 和 `response_length`。
3. monkeypatch `_compute_score(...)`、`_compute_teacher_logprobs(...)`、`_compute_multi_modal_inputs(...)` 和 `_compute_position_ids(...)`，避免启动真实模型或 reward loop。
4. 调用真实 `_agent_loop_postprocess(...)`，验证 padding、attention mask、response mask、response_logprobs、extra_fields 和 raw_prompt。
5. 调用真实 `_postprocess(...)`，验证 `DataProto.batch`、`DataProto.non_tensor_batch` 和 `meta_info`。

这类 monkeypatch 只允许绕开模型、tokenizer 或 reward loop 重计算，不允许替换 `AgentLoopOutput.as_dict()`、`_agent_loop_postprocess(...)` 或 `_postprocess(...)` 的核心 batch 行为。

执行实现前还需要做一个真实 verl import preflight：

```bash
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
from verl.experimental.agent_loop.agent_loop import AgentLoopOutput, AgentLoopMetrics
print(AgentLoopOutput, AgentLoopMetrics)
PY
```

如果本地环境继续缺少 `packaging`、`numpy`、`ray`、`tensordict`、`torch`、`hydra-core`、`omegaconf`、`pillow`、`transformers`、`codetiming`、`datasets`、`cachetools`、`uvicorn`、`fastapi` 或其他 verl 依赖，执行结果中必须记录缺少的依赖和采用的解决方式。不能因为依赖较重就把 Stage 10 验收降级成 RepoHarness 自定义 dataclass 测试。

## 6. DataProto 和 TransferQueue 可见性

Stage 10 必须新增 batch 级 visibility helper，而不是只检查单条 `TrainingView.extra_fields`。

建议 helper：

```python
validate_dataproto_visibility(data_proto: Any) -> None
validate_dataproto_shapes(data_proto: Any, *, batch_size: int, prompt_length: int, response_length: int) -> None
validate_transfer_queue_field_visibility(field: Mapping[str, Any]) -> None
```

检查内容：

- `batch["prompts"]` 形状为 `[batch_size, prompt_length]`。
- `batch["responses"]` 形状为 `[batch_size, response_length]`。
- `batch["response_mask"]` 形状为 `[batch_size, response_length]`。
- 正式 online RL 样本的 `batch["rollout_log_probs"]` 存在，形状为 `[batch_size, response_length]`。
- 有 reward 的样本必须产生 `batch["rm_scores"]`，并且 reward 位于最后一个真实 response token。
- `non_tensor_batch` 中的 `repo_harness_*` 字段必须是 flat scalar array 或 opaque ref array。
- `non_tensor_batch`、`meta_info` 和 TransferQueue field 中不能出现 hidden verifier、gold patch、accepted label、完整 reward metadata、provider secret、本地绝对路径或嵌套 AuditRef。
- `raw_prompt` 如果存在，必须只包含模型可见内容。

特别注意 `reference/verl/verl/trainer/main_ppo_sync.py` 中的 TransferQueue 路径会执行：

```python
field = output.as_dict()
field.update(kwargs)
```

因此 Stage 10 必须测试 `kwargs` allowlist 的预期边界，即使 Stage 11 才会真正构造 `RepoHarnessVerlAgentLoop`。第一版可以在 Stage 10 提供 visibility helper 和测试样例，Stage 11 再接入真实 adapter。

`kwargs` 合并必须采用 default-deny 规则。Stage 10 至少要明确拒绝 `kwargs` 覆盖以下字段：

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

这些字段要么是 converter 生成的训练张量，要么是 verl 自身有特殊语义的保留字段。未来 Stage 11 adapter 如果需要传入 dataset 字段，必须通过 allowlist，并且要证明该字段只包含模型可见内容或 batch 可传播的 opaque metadata。

## 7. 测试计划

建议新增：

```text
tests/unit/test_repo_harness_verl_stage10_agent_loop_output.py
tests/unit/test_repo_harness_verl_stage10_postprocess_visibility.py
tests/unit/test_repo_harness_verl_stage10_dataproto_shapes.py
```

必须覆盖：

1. canonical `canonical_training_view.json` 只用于 schema roundtrip 和字段稳定性测试，不能直接作为 formal online RL 转换样本。
2. Stage 10 专用 formal online RL 样本可以基于 canonical fixture 显式补入 `repo_harness_llm_gateway_route="verl"`，或从 `canonical_episode_result.json` 的 `generation_records` 明确投影后转换为真实 `AgentLoopOutput`。从 `generation_records` 投影前必须确认列表非空，并且所有 `generation_records[*].gateway_route` 都是 `verl`。
3. `AgentLoopOutput.as_dict()` 产生 `prompts`、`responses`、`response_mask`、`rollout_log_probs` 和 `rm_scores`，dtype 和长度符合 verl 预期。
4. `response_mask=0` 的工具 observation token 对应 `response_logprobs=0.0`，转换后不参与 loss mask。
5. 空 `response_ids` 且带 reward 的样本在 converter 前被拒绝，不触发 `rm_scores[-1]` 空序列问题。
6. response overflow fixture 被拒绝，不能静默截断后进入 `AgentLoopOutput`。
7. mixed log probability batch fixture 被拒绝。
8. `TrainingView.online_rl_eligible=False`、`online_rl_eligible=None`、`repo_harness_invalid_for_online_rl=True` 都不能进入 formal online RL converter。
9. `mock`、`replay`、provider route 或缺失 `response_logprobs` 的样本不能进入 formal online RL converter。
10. 嵌套 `audit_ref`、绝对 `run_dir`、reward metadata path、final verifier path、gold patch path 不能进入 `AgentLoopOutput.extra_fields`。
11. `AgentLoopWorker._agent_loop_postprocess(...)` 后的 `extra_fields.raw_prompt` 通过 visibility 检查。
12. TransferQueue field 模拟 `field.update(kwargs)` 后，顶层 `raw_prompt` 通过 visibility 检查，hidden metadata、gold patch、accepted label、provider secret 和 evaluator-only logs 被拒绝。
13. TransferQueue field 模拟 `field.update(kwargs)` 后，`kwargs` 不能覆盖 `prompts`、`responses`、`response_mask`、`rollout_log_probs`、`rm_scores`、`extra_fields`、`teacher_ids`、`teacher_logprobs`、`loss_mask`、`input_ids`、`position_ids` 或 `multi_modal_inputs`。
14. `_postprocess(...) -> DataProto` 后，tensor batch、non-tensor batch 和 meta_info 的 batch 维度一致。
15. DataProto 中 `rollout_log_probs` 的形状为 `[batch_size, response_length]`，`rm_scores` 的形状为 `[batch_size, response_length]`。
16. `src/repo_harness/rl` 仍无 `import verl` 或 `from verl`。
17. 普通 RepoHarness CLI import 不需要安装完整 verl 依赖。

## 8. 验收命令

Stage 10 完成时至少运行：

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
from verl.experimental.agent_loop.agent_loop import AgentLoopOutput, AgentLoopMetrics
print(AgentLoopOutput, AgentLoopMetrics)
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
  tests/unit/test_repo_harness_verl_stage10_dataproto_shapes.py

rg -n '(^|\s)(import|from)\s+verl' src/repo_harness/rl && exit 1 || true
git diff --check -- \
  src/repo_harness/rl \
  src/repo_harness_verl \
  tests/unit/test_repo_harness_verl_stage10_agent_loop_output.py \
  tests/unit/test_repo_harness_verl_stage10_postprocess_visibility.py \
  tests/unit/test_repo_harness_verl_stage10_dataproto_shapes.py
```

如果 Stage 10 需要为本地 `reference/verl` 补测试依赖，必须把依赖安装方式或 `uv --with ...` 命令写进执行结果，不能用“跳过真实 verl postprocess 测试”代替验收。

如果上述 `uv --with ...` 仍然因为 `reference/verl` 的真实依赖继续缺包，执行 agent 必须把实际缺包名称、补充后的完整命令和最终通过的 preflight 输出写入执行结果。不能把真实 verl import preflight 标记为可选。

## 9. 阶段出口

Stage 10 完成后必须满足：

1. canonical `TrainingView` fixture 继续用于 schema roundtrip 和字段稳定性测试，不能被误当作 formal online RL 样本。
2. Stage 10 专用 formal online RL 样本可以转换成真实 `AgentLoopOutput`，并且 route 必须由 `repo_harness_llm_gateway_route="verl"` 明确给出，或在确认 `generation_records` 非空且所有 `generation_records[*].gateway_route` 都是 `verl` 后明确投影得到。
3. `AgentLoopOutput.as_dict()` 后的 tensor 字段满足 verl 预期。
4. verl postprocess 后 `extra_fields.raw_prompt`、TransferQueue 顶层 `raw_prompt`、`response_mask`、`rollout_log_probs` 和 `rm_scores` 通过检查。
5. DataProto smoke 可以证明 batch 维度、padding、reward placement 和 rollout log probability shape 正确。
6. nested `AuditRef`、本地绝对路径、hidden verifier、gold patch、完整 reward metadata、accepted label、provider secret 不能进入 `AgentLoopOutput.extra_fields`、TransferQueue field、DataProto non-tensor batch 或 meta_info。
7. `kwargs` allowlist 能阻止 dataset 或 adapter 字段覆盖 `prompts`、`responses`、`response_mask`、`rollout_log_probs`、`rm_scores`、`extra_fields`、`teacher_ids`、`teacher_logprobs`、`loss_mask`、`input_ids`、`position_ids` 和 `multi_modal_inputs`。
8. invalid、overflow、empty response、missing log probability、non-`verl` route 样本不能作为 formal online RL `AgentLoopOutput` 输出。
9. `src/repo_harness/rl` 仍然无 verl import，普通 RepoHarness 使用不需要安装 verl。
10. Stage 11 可以在这个 converter 上实现 `RepoHarnessVerlAgentLoop.run(...)`，而不需要重新定义训练视图、reward placement 或 visibility 规则。

## 10. 不进入 Stage 10 的内容

以下内容留到后续阶段：

- Stage 11：`RepoHarnessVerlAgentLoop`、`VerlLLMGateway`、Hydra config 注册、fake `LLMServerClient` smoke。
- Stage 12：端到端 verl dataloader sample、真实 `DataProto` trainer smoke、Mac / Vast.ai 分层验收、真实性能 smoke。
- Stage 13：fully async、partial rollout、中断恢复、参数版本跨越和长期 trajectory 的演进接口。
