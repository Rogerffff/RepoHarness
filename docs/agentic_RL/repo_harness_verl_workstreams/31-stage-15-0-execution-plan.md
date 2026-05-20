# Stage 15.0 执行计划：verl partial rollout 接口盘点和集成方案

## 1. 阶段定位

Stage 15.0 的目标是在真正改代码接入 `partial_rollout=True` 之前，先把当前 `reference/verl` fully async 路径里的 partial rollout 语义盘点清楚，并形成 RepoHarness 的最小接入方案。

这一阶段只回答下面几个问题：

```text
1. verl 原生 partial_rollout=True 到底在什么层级触发？
2. abort / aborted / length / stop 等停止原因是否能到达 RepoHarnessVerlAgentLoop？
3. RepoHarness PartialEpisodeCheckpoint 应该进入哪个 queue、side channel 或 scheduler？
4. resumed completed sample 应该由哪个路径进入 policy-loss MessageQueue？
5. 如果需要 patch / wrapper，应该改哪里、如何启用、如何回退、如何验收？
```

Stage 15.0 不应该直接实现远端 partial resume，也不应该把 `FullyLLMServerClient` 底层自动续生成误认为 RepoHarness 的 `PartialEpisodeCheckpoint`。

## 2. 前置状态

Stage 14.2 已经固定 partial checkpoint contract：

```text
commit: d9c589ae
message: feat: add stage14.2 partial checkpoint contract
```

Stage 14.3 已经完成本地同进程 turn-boundary pause / resume facade：

```text
commit: eed69eb3
message: feat: add stage14.3 pause resume facade
```

Stage 14.3 证明的是：

```text
RepoHarness 能在安全 turn boundary 暂停，
生成 PartialEpisodeCheckpoint，
保持 workspace / run directory / recorder ownership，
随后在同一进程内 resume 并完成 episode。
```

Stage 15.0 必须复用 Stage 14.2 / Stage 14.3 的对象和边界，不重新发明 checkpoint schema，也不把 partial checkpoint 放进 policy loss。

## 3. 非目标

Stage 15.0 不做：

```text
不启动远端 GPU smoke
不运行真实 fully_async_main 多步训练
不实现 RepoHarnessPartialRolloutProducer
不实现 RepoHarnessResumeScheduler
不修改 policy-loss MessageQueue 的真实消费路径
不实现跨进程、跨机器或 Ray actor 迁移 resume
不实现 KV cache resume
不支持模型请求中、工具执行中、verifier 执行中、reward 写入中或 cleanup 执行中的热迁移
不迁移旧 run-task / run-batch / run-experiment / 离线 export CLI
不放松 Stage 0H 到 Stage 14 已固定的 route、logprob、generation record、response span、reward finality、visibility 和 path leak 规则
```

如果 Stage 15.0 发现必须修改 `reference/verl`，本阶段只产出 patch plan。实际 patch 应放到 Stage 15.1 或后续执行计划中，并且必须登记到 patch manifest。

## 4. 本阶段产物

Stage 15.0 完成后，至少新增一个本地验收目录：

```text
runs/repo-harness-verl-stage15-0-<timestamp>/
```

目录内至少包含：

```text
stage15_0_command_log.jsonl
stage15_0_static_scan_report.json
fully_async_partial_rollout_interface_inventory.json
stage15_partial_rollout_patch_plan.json
stage15_partial_rollout_risk_matrix.json
stage15_0_acceptance_summary.json
```

建议新增一个小型本地 inventory builder，但不强制命名：

```text
src/repo_harness_verl/stage15_inventory.py
tests/unit/test_repo_harness_verl_stage15_0_inventory.py
tests/unit/test_repo_harness_verl_stage15_0_patch_plan.py
```

如果执行时选择脚本形式，也可以使用：

```text
scripts/stage15/build_partial_rollout_inventory.py
```

无论采用模块还是脚本，输出 JSON 的字段必须稳定、可测试、可被后续 Stage 15.1 实施计划引用。

## 5. 需要盘点的 reference/verl 接口

### 5.1 fully async 配置入口

必须静态盘点下面配置项的真实位置、默认值、远端命令覆盖方式和当前 Stage 14 smoke 使用方式：

```text
async_training.partial_rollout
async_training.trigger_parameter_sync_step
async_training.require_batches
async_training.staleness_threshold
rollout.total_rollout_steps
actor_rollout_ref.hybrid_engine
data.train_batch_size
data.gen_batch_size
actor_rollout_ref.rollout.calculate_log_probs
actor_rollout_ref.actor.use_rollout_log_probs
actor_rollout_ref.rollout.agent.agent_loop_config_path
actor_rollout_ref.rollout.multi_turn.enable
actor_rollout_ref.rollout.name
trainer.nnodes
trainer.n_gpus_per_node
rollout.nnodes
rollout.n_gpus_per_node
checkpoint_engine.backend
```

盘点结果必须记录到 `fully_async_partial_rollout_interface_inventory.json`：

```json
{
  "config_inventory": {
    "async_training.partial_rollout": {
      "default_value": true,
      "source_path": "reference/verl/...",
      "current_stage14_override": false,
      "stage15_required_override": true,
      "notes": "..."
    }
  }
}
```

这里的 `source_path` 使用仓库相对路径，不写本机绝对路径。

### 5.2 参数同步和推理服务中断触发链

必须盘点 `partial_rollout=True` 在真实参数同步路径中的触发链，而不能只看 agent loop 或 message queue：

```text
FullyAsyncTrainer._fit_update_weights(...)
-> checkpoint_manager.update_weights(...)
-> CheckpointEngineManager.update_weights(...)
-> RolloutReplica.abort_all_requests(...)
-> vLLM / SGLang / TRT-LLM rollout server abort_all_requests(...)
-> trainer / rollout weight sync
-> RolloutReplica.resume_generation(...)
-> rollout server resume_generation(...)
```

必须检查和记录：

```text
FullyAsyncTrainer._fit_update_weights(...)
CheckpointEngineManager.update_weights(...)
RolloutReplica.abort_all_requests(...)
RolloutReplica.resume_generation(...)
vLLM backend abort_all_requests(...) / resume_generation(...)
SGLang backend abort_all_requests(...) / resume_generation(...)
TRT-LLM backend abort_all_requests(...) / resume_generation(...)
checkpoint_engine.backend
weight_sync_strategy
```

inventory 中必须包含：

```json
{
  "native_partial_rollout_trigger_chain": {
    "weight_sync_calls_checkpoint_manager_update_weights": true,
    "checkpoint_manager_aborts_inflight_requests": true,
    "checkpoint_manager_abort_gated_by_partial_rollout": false,
    "server_resume_generation_after_weight_sync": true,
    "fully_llm_client_continue_gated_by_partial_rollout": true,
    "partial_rollout_config_gate_location": "reference/verl/...",
    "abort_stop_reason_visible_to_agent_loop": false,
    "repo_harness_checkpoint_implication": "..."
  }
}
```

这条链的结论必须写得非常明确：

```text
如果中断发生在 checkpoint engine / rollout server 层，
并且 abort / aborted 被 FullyLLMServerClient 内部自动续生成消费，
那么 RepoHarnessVerlAgentLoop 不会天然看到一个可保存 PartialEpisodeCheckpoint 的 turn boundary。
Stage 15.1 不能只在 MessageQueue 或 final AgentLoopOutput 层补逻辑。
```

如果某个 backend 没有实现 `resume_generation(...)`，或者实现语义与 vLLM / SGLang 不同，inventory 必须记录为 backend-specific risk，不能用另一个 backend 的行为推断。`TRT-LLM` 后端如果当前实现是 `NotImplemented` 或语义未验证，也必须显式记录，不能按 vLLM / SGLang 行为外推。

### 5.3 FullyLLMServerClient 和 TokenOutput 停止原因

必须检查：

```text
LLMServerClient.generate(...)
FullyLLMServerClient.generate(...)
LLMServerManager.get_client(fully_async=True)
TokenOutput.stop_reason
abort
aborted
length
stop
completed
global_steps
min_global_steps
max_global_steps
num_preempted
```

重点确认下面这条真实逻辑：

```text
如果 output.stop_reason 是 abort / aborted，
并且 async_training.partial_rollout=True，
FullyLLMServerClient 会继续内部生成循环，
直到返回非 abort / aborted 或达到长度限制。
```

必须在 inventory 中明确回答：

```text
1. abort / aborted 是否会作为中间状态到达 RepoHarnessVerlAgentLoop？
2. 如果不会到达，RepoHarness 是否无法仅凭 AgentLoop 看到 verl 原生 partial rollout？
3. 如果需要让 RepoHarness 感知中断，最小 patch / wrapper 位置在哪里？
4. length / stop / completed 是否可以作为安全 turn boundary 的触发信号？
```

建议记录格式：

```json
{
  "llm_server_stop_reason_inventory": {
    "fully_async_client_class": "FullyLLMServerClient",
    "abort_auto_continues_inside_fully_llm_server_client": true,
    "abort_visible_to_repo_harness_agent_loop": false,
    "completed_stop_reason_mapping_checked": true,
    "evidence": [
      {
        "source_path": "reference/verl/verl/workers/rollout/llm_server.py",
        "line_hint": "stop_reason not in ('aborted', 'abort') or not partial_rollout"
      }
    ],
    "stage15_implication": "RepoHarness partial checkpoint 不能把底层自动续生成当作 checkpoint 触发证据。"
  }
}
```

### 5.4 FullyAsyncRollouter 生命周期和 pause 机制

必须盘点：

```text
FullyAsyncRollouter.__init__(...)
FullyAsyncRollouter.set_max_required_samples(...)
FullyAsyncRollouter._feed_worker(...)
FullyAsyncRollouter._processor_worker(...)
FullyAsyncRollouter._process_single_sample_streaming(...)
FullyAsyncRollouter.pause(...)
FullyAsyncRollouter.resume(...)
FullyAsyncRollouter.reset_staleness(...)
FullyAsyncRollouter._should_pause_generation(...)
pending_queue
active_tasks
paused
_resume_event
message_queue_client.put_sample(...)
```

必须回答：

```text
1. FullyAsyncRollouter 自己的 paused / resume_event 是控制 rollout 生产速度，还是能保存 RepoHarness episode 状态？
2. active_tasks 被 abort、pause 或 reset_staleness 影响时，RepoHarnessVerlAgentLoop 是否还有 live handle？
3. RolloutSample 在什么时刻构造？
4. RolloutSample 入 MessageQueue 之前，是否存在插入 RepoHarness queue facts / diagnostic side channel 的稳定 hook？
5. 如果 producer 要把 partial checkpoint 放到 resume queue，应该在 rollouter、agent loop、runtime，还是 message queue 旁路上实现？
```

盘点中必须明确：

```text
Stage 15 第一版 resume scheduler 必须和 active AsyncEpisodeHandle 处于同一个 runtime ownership scope。
如果 RepoHarnessVerlAgentLoop.run(...) 已经返回，或者当前 worker registry 没有 live handle，
checkpoint 只能进入 diagnostic side channel，不能被另一个进程或另一个 Ray actor 接管。
```

这里的“同一 Ray actor”默认指承载 `RepoHarnessVerlAgentLoop` 和 `RepoHarnessRuntime` active handle registry 的同一个 `AgentLoopWorker` Ray actor，不能泛化成 `FullyAsyncRollouter` actor 或其他 worker 可以直接接管 live handle。

### 5.5 MessageQueue 和 FullyAsyncTrainer 取样语义

必须盘点：

```text
MessageQueue.put_sample(...)
MessageQueueClient.put_sample(...)
MessageQueueClient.get_sample(...)
FullyAsyncTrainer._get_samples_from_queue(...)
assemble_batch_from_rollout_samples(...)
addition_process(...)
RolloutSample.sample_id
RolloutSample.rollout_status
RolloutSample.full_batch
DataProto.non_tensor_batch
DataProto.meta_info
```

必须记录一个关键事实：

```text
FullyAsyncTrainer._get_samples_from_queue(...) 会收集 required_samples 条 raw queue entry，
然后直接 cloudpickle.loads(...) 并组装 batch。
它本身不会理解 RepoHarness 的 partial、diagnostic、stale 或 visibility rejected 样本。
```

因此 Stage 15 patch plan 必须明确下面二选一：

```text
方案 A：真实 policy-loss MessageQueue 源头只允许放 valid completed sample；
       partial / diagnostic / rejected / stale 进入 side channel 或 resume queue。

方案 B：在 FullyAsyncTrainer 取样前增加 wrapper / filter；
       wrapper 必须继续读取直到凑够 required valid completed samples，
       或遇到 termination signal、max dequeue limit 或 timeout。
```

默认推荐方案是方案 A，除非 Stage 15.0 inventory 证明真实 trainer hook 更安全、更小。

### 5.6 RepoHarnessVerlAgentLoop 和 AsyncEpisodeHandle 生命周期

必须盘点当前本地实现：

```text
RepoHarnessVerlAgentLoop.run(...)
RepoHarnessRuntime.start_episode(...)
AsyncEpisodeHandle.request_pause_at_next_turn_boundary(...)
AsyncEpisodeHandle.resume(...)
AsyncEpisodeHandle.wait_result(...)
ResumeStateStore
PartialEpisodeCheckpoint
```

必须回答：

```text
1. RepoHarnessVerlAgentLoop.run(...) 当前是否只返回 terminal AgentLoopOutput？
2. 如果一个 episode 在 turn boundary pause，run(...) 是否还持有 live handle，还是已经返回？
3. Stage 15 resume scheduler 应该归属于 RepoHarnessVerlAgentLoop 实例、rollouter worker、Ray actor，还是独立 runtime manager？
4. checkpoint 中哪些字段可以公开传播，哪些字段只能 runtime-private 保存？
5. resume 后如何重新计算 trajectory digest、generation record digest、reward finality 和 staleness？
```

如果 inventory 不能证明 `run(...)` 返回后仍可访问 live handle，则 patch plan 必须写清楚：

```text
RepoHarness partial checkpoint 不能在 run(...) 返回后由另一个 actor 接管。
Stage 15.1 第一版必须让 pause / resume 完成后再返回 terminal AgentLoopOutput，
或者引入同 actor 内部的 side-channel scheduler。
```

## 6. patch plan 要求

`stage15_partial_rollout_patch_plan.json` 必须列出所有候选接入点，并选出一个默认推荐方案。

每个候选方案至少包含：

```json
{
  "patch_id": "stage15_candidate_a",
  "target": "reference/verl/... 或 src/repo_harness_verl/...",
  "kind": "wrapper | monkey_patch | source_patch | adapter_only | no_patch_required",
  "purpose": "...",
  "why_needed": "...",
  "enables": ["partial_checkpoint_side_channel", "resume_scheduler", "valid_completed_sample_queue"],
  "risks": ["..."],
  "compatibility_tests": ["..."],
  "rollback_plan": "...",
  "patch_manifest_required": true
}
```

候选方案至少要覆盖：

```text
1. AgentLoop / RepoHarnessRuntime 侧 pause request hook。
2. FullyAsyncRollouter 侧 sample production hook。
3. MessageQueue policy-loss source gate。
4. diagnostic / resume side channel。
5. FullyLLMServerClient stop_reason wrapper 或不采用该 wrapper 的理由。
6. CheckpointEngineManager / RolloutReplica abort-resume 链路 wrapper 或不采用该 wrapper 的理由。
```

如果 patch plan 声称“不需要修改 reference/verl”，必须同时证明：

```text
RepoHarness 可以在不修改 reference/verl 的情况下收到 partial trigger；
partial checkpoint 不会进入真实 policy-loss MessageQueue；
resumed completed sample 会进入真实 policy-loss MessageQueue；
FullyAsyncTrainer 不会把 partial / diagnostic 样本计入 required_samples；
远端 evidence 能证明上述路径。
```

如果无法证明，上述结论必须是：

```text
reference/verl patch_or_wrapper_required = true
```

## 7. 风险矩阵要求

`stage15_partial_rollout_risk_matrix.json` 至少要覆盖下面风险：

```text
verl 原生 abort / aborted 被 FullyLLMServerClient 内部消费，RepoHarness 不可见。
CheckpointEngineManager.update_weights(...) 在参数同步时中断推理服务，但 RepoHarness 无法感知安全 turn boundary。
RepoHarnessVerlAgentLoop.run(...) 返回后 live handle 丢失。
partial checkpoint 被误放入 policy-loss MessageQueue。
diagnostic / stale / visibility rejected 样本被 FullyAsyncTrainer 计入 required_samples。
resume 后样本 stale，但仍进入 policy loss。
同一个 checkpoint 被重复 resume 并重复计入 policy loss。
policy_loss_consumed_sample_id 不唯一。
resume_attempt_id 不唯一。
source_partial_checkpoint_id 不唯一。
reward finality 和 resumed trajectory digest 不匹配。
generation record digest 与 resumed response ids / logprobs 不匹配。
patch 漂移导致远端 reference/verl 行号或接口变化。
公开 evidence 泄漏远端绝对路径、workspace path、dependency environment path 或 evaluator-only 字段。
remote patch manifest 漏登记 reference/verl patch、sitecustomize 或 helper script。
```

每条风险至少包含：

```json
{
  "risk_id": "stage15_risk_invisible_abort",
  "severity": "P1",
  "failure_mode": "...",
  "detection": "...",
  "mitigation": "...",
  "owner_stage": "15.0 | 15.1 | 15.2",
  "acceptance_gate": "..."
}
```

## 8. 本地验收和测试计划

Stage 15.0 应新增或更新测试，覆盖：

```text
1. inventory JSON 字段完整，包含 config、CheckpointEngineManager abort-resume 链、FullyLLMServerClient、rollouter、trainer、message queue、agent loop lifecycle。
2. inventory 中记录 abort / aborted 在 partial_rollout=True 下的自动续生成行为。
3. inventory 中记录 `completed` stop reason 映射，不能只记录 abort / aborted / length / stop。
4. inventory 如果没有覆盖 CheckpointEngineManager / RolloutReplica / backend abort_all_requests / resume_generation 链路，acceptance 必须失败。
5. patch plan 不能在 evidence 不足时声明 no_patch_required。
6. patch plan 如果登记 reference/verl patch，必须包含 target、purpose、compatibility_tests、rollback_plan 和 patch_manifest_required。
7. risk matrix 包含上述 P1 风险。
8. acceptance summary 只有在三个核心产物都存在、字段完整、没有路径泄漏时才能 passed=true。
```

建议测试文件：

```text
tests/unit/test_repo_harness_verl_stage15_0_inventory.py
tests/unit/test_repo_harness_verl_stage15_0_patch_plan.py
tests/unit/test_repo_harness_verl_stage15_0_acceptance.py
```

inventory builder 必须通过静态读取源码、正则扫描或轻量 AST 解析来盘点 `reference/verl`。它不能 import 真实 `verl`，也不能 import `torch`、`ray`、`tensordict`。Stage 15.0 是本地接口 inventory 阶段，不能因为执行盘点脚本而拉起重依赖、初始化 Ray、加载 CUDA 或受远端镜像环境影响。

前置回归建议至少执行：

```bash
PYTHONPATH=src uv run --extra dev python -m compileall -q src

PYTHONPATH=src uv run --extra dev python -m pytest -q \
  tests/unit/test_repo_harness_rl_stage14_2_partial_checkpoint_schema.py \
  tests/unit/test_repo_harness_rl_stage14_2_partial_checkpoint_visibility.py \
  tests/unit/test_repo_harness_rl_stage14_2_partial_checkpoint_tamper.py \
  tests/unit/test_repo_harness_rl_stage14_2_partial_checkpoint_policy_gate.py \
  tests/unit/test_repo_harness_rl_stage14_3_pause_resume_facade.py \
  tests/unit/test_repo_harness_verl_stage13_2_fully_async_bridge.py \
  tests/unit/test_repo_harness_verl_stage13_3a_async_producer.py \
  tests/unit/test_repo_harness_verl_stage13_3a_message_queue_filter.py \
  tests/unit/test_repo_harness_verl_stage13_3a_parameter_versions.py \
  tests/unit/test_repo_harness_verl_stage13_3a_resource_lifecycle.py

PYTHONPATH=src uv run --extra dev python - <<'PY'
import sys
import repo_harness.rl
import repo_harness_verl
for name in ("torch", "ray", "tensordict", "verl"):
    if name in sys.modules:
        raise SystemExit(f"unexpected heavy import: {name}")
print("ordinary_import_ok")
PY

if rg -n '(^|\s)(import|from)\s+verl' src/repo_harness/rl; then
  exit 1
fi
```

如果新增 inventory builder 或 acceptance inspector，还必须执行对应新测试。

## 9. 验收标准

Stage 15.0 只有在下面条件全部满足时才算完成：

```text
1. fully_async_partial_rollout_interface_inventory.json 存在，并能明确说明 verl 原生 partial_rollout=True 与 RepoHarness PartialEpisodeCheckpoint 的关系。
2. stage15_partial_rollout_patch_plan.json 存在，并明确 Stage 15.1 的推荐接入点、patch / wrapper 归属、启用方式和回退方式。
3. stage15_partial_rollout_risk_matrix.json 存在，并覆盖 invisible abort、trainer required_samples 污染、cross actor resume、duplicate resume、stale resumed sample、path leak 和 patch drift。
4. stage15_0_acceptance_summary.json 中 passed=true，并记录 code_commit、git_status_short、reference_verl_commit、reference_verl_dirty_status、inventory_sha256、patch_plan_sha256、risk_matrix_sha256。`reference_verl_commit` 建议由 `git -C reference/verl rev-parse HEAD` 取得，`reference_verl_dirty_status` 建议由 `git -C reference/verl status --short` 取得。
5. 公开 JSON 中不能出现本机或远端绝对 workspace path，不能包含 hidden verifier、gold patch、完整 reward metadata 或 evaluator-only 字段。
6. 现有 Stage 14.2、Stage 14.3、Stage 13.3-A 关键回归通过。
7. src/repo_harness/rl 仍然不 import verl。
```

如果任何关键事实无法静态确认，acceptance summary 不能写 `passed=true`。它必须写：

```text
passed=false
blocked_by=<具体缺失事实>
next_required_action=<需要远端 dry run、reference/verl patch 或源码阅读的位置>
```

## 10. Stage 15.0 到 Stage 15.1 的交接

Stage 15.0 完成后，Stage 15.1 执行计划必须直接引用本阶段产物，而不是重新猜测接入方式。

Stage 15.1 开始前必须已经明确：

```text
RepoHarness partial checkpoint 的生产者是谁。
resume queue / diagnostic side channel 的 owner 是谁。
resume scheduler 是否仍然持有同一 runtime active handle registry。
policy-loss MessageQueue 的 source gate 在哪里。
FullyAsyncTrainer 是否需要 wrapper。
reference/verl 是否需要 patch。
远端 patch manifest 应登记哪些文件。
```

如果 Stage 15.0 得出的结论是“必须修改 reference/verl”，Stage 15.1 实施计划必须先列出最小 diff 和回退方案，再允许写代码。
