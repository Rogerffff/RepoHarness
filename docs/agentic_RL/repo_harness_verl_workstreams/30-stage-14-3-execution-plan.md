# Stage 14.3 执行计划：RepoHarness pause / resume facade 原型

## 1. 阶段定位

Stage 14.3 的目标是在 Stage 14.2 已经固定 `PartialEpisodeCheckpoint` contract 之后，为 RepoHarness runtime 增加第一版可测试的 pause / resume facade。

这个阶段只证明一件事：

```text
RepoHarness 能在安全的 turn boundary 生成 partial checkpoint，
保持 workspace / run directory / recorder ownership，
随后在同一进程内从该 checkpoint 恢复，并完成 episode。
```

Stage 14.3 不是生产级恢复系统，也不是 verl 真实 `partial_rollout=True` 远端 smoke。真实 verl partial rollout 应放到 Stage 15。

## 2. 前置状态

Stage 14.2 已提交：

```text
commit: d9c589ae
message: feat: add stage14.2 partial checkpoint contract
```

Stage 14.2 已经提供：

```text
PartialEpisodeCheckpoint
DurableWriterLeaseFacts
RecorderCursorFacts
WorkspaceCheckpointFacts
ToolPairingState
CheckpointTokenProvenance
CheckpointRewardFinalityFacts
PartialCheckpointQueueFacts
canonical / invalid fixtures
policy-loss rejection tests
model_copy tamper revalidation
```

Stage 14.3 必须复用这些 contract，不重新发明一套 pause checkpoint schema。

## 3. 非目标

Stage 14.3 不做：

```text
不修改 reference/verl
不启用 verl partial_rollout=True
不启动远端 GPU smoke
不做 KV cache resume
不支持跨进程或跨机器耐久 resume
不支持模型请求执行中热迁移
不支持 shell / pytest / Docker command 执行中热迁移
不支持 final verifier / reward / cleanup 执行中热迁移
不把 partial checkpoint 送入 policy loss
不迁移旧 CLI / offline export / SWE-Bench 评测路径
```

如果实现中发现必须改动 `reference/verl` 或远端 trainer 行为，必须停止并另写 Stage 15 或后续阶段计划，不能在 Stage 14.3 内顺手完成。

## 4. 第一版成功定义

Stage 14.3 完成时应能本地证明：

```text
1. 一个 episode 可以在安全 turn boundary 生成 PartialEpisodeCheckpoint。
2. 暂停状态下 workspace lease、run directory writer 和 recorder cursor 不被错误释放。
3. 从 checkpoint resume 后，episode 可以继续运行到终态。
4. resume 后的终态 RepoHarnessEpisodeResult 可以生成合法 TrainingView 和 GenerationRecord。
5. 恢复前 checkpoint 仍然只能进入 diagnostic / resume_preparation，不能进入 policy loss。
6. 恢复后终态样本只有通过 formal online RL / formal async validator 后才可以成为 valid sample。
7. 篡改 checkpoint、workspace lease 丢失、recorder cursor 不匹配、generation record digest 不匹配、stale checkpoint 都会得到结构化失败。
```

## 5. 安全 turn boundary 定义

第一版只允许下面的 pause 点：

```text
LLMGateway.generate_turn(...) 已经返回
当轮 assistant generation 的 GenerationRecord 已经写入 collector
如果该 assistant response 产生 tool call，则对应 tool result 已经执行完成
tool observation 已经写入 transcript / recorder，并且 observation token projection 已经稳定
如果 assistant response 是 final answer，则 final verifier 尚未启动
recorder 已经 flush 到一致状态
没有 final verifier 正在运行
没有 reward metadata 正在写入
没有 cleanup 正在执行
workspace lease 仍由当前 runtime 持有
run directory single writer 仍由当前 runtime 持有
```

不允许的 pause 点：

```text
gateway call in flight
tool command in flight
artifact manifest write in flight
final verifier in flight
reward boundary in flight
cleanup in flight
run directory writer already released
workspace lease already released
```

如果调用方请求 pause，但当前没有安全 boundary，runtime 应返回结构化状态：

```text
pause_status = waiting_for_turn_boundary
checkpoint = None
```

不能为了满足 pause 请求而强行中断正在运行的模型请求、工具命令、verifier 或 cleanup。

final answer 也是一个允许的 turn boundary，但只能在 final verifier 尚未启动前暂停。resume 后应从 checkpoint 继续进入 final verifier / reward boundary，而不是把 final answer checkpoint 当成终态 `RepoHarnessEpisodeResult`。

## 6. 建议新增或修改文件

建议新增：

```text
src/repo_harness/rl/pause_resume.py
tests/unit/test_repo_harness_rl_stage14_3_pause_resume_contract.py
tests/unit/test_repo_harness_rl_stage14_3_async_pause_facade.py
tests/unit/test_repo_harness_rl_stage14_3_real_episode_turn_boundary.py
tests/unit/test_repo_harness_rl_stage14_3_resume_policy_gate.py
tests/fixtures/repo_harness_verl/stage14_3/
```

可能需要修改：

```text
src/repo_harness/rl/async_contracts.py
src/repo_harness/rl/async_runtime.py
src/repo_harness/rl/runtime.py
src/repo_harness/agent_loop/loop.py
src/repo_harness/rl/__init__.py
```

`src/repo_harness/agent_loop/loop.py` 只有在确实需要插入“tool result 写入后、下一次 model request 前”的协作式 boundary callback 时才修改。修改必须非常窄，不能重写 agent loop。

## 7. 新增 contract / runtime-only 对象

建议在 `pause_resume.py` 中新增 runtime-only 对象：

```text
PauseRequest
PauseOutcome
PauseStatus
ResumeRequest
ResumeOutcome
ResumeStateRef
ResumeStateStore
TurnBoundaryPauseController
```

建议状态枚举：

```text
pause_not_requested
pause_requested
waiting_for_turn_boundary
checkpoint_ready
paused
pause_rejected
resume_requested
resume_running
resume_completed
resume_failed
```

这些对象是 runtime facade 的控制对象，不应进入 verl batch。可传播字段只能是 opaque ref、digest 和 batch-safe flat scalar。

`TurnBoundaryPauseController` 必须是线程安全对象。当前 `real_episode` 仍然运行在同步 worker thread 中，因此控制面不能从 worker thread 直接 `await asyncio.Event`，也不能跨线程直接操作 `asyncio.Lock`。第一版应使用 `threading.Event`、`queue.Queue`、`concurrent.futures.Future`、`loop.call_soon_threadsafe(...)` 或等价线程安全机制在 async runtime 和 worker thread 之间传递 pause / resume 信号。

## 8. AsyncEpisodeHandle API 计划

建议扩展 `AsyncEpisodeHandle`：

```python
async def request_pause_at_next_turn_boundary(
    self,
    reason: str = "pause_requested",
    timeout: float | None = None,
) -> PauseOutcome

async def resume(
    self,
    checkpoint: PartialEpisodeCheckpoint,
    *,
    llm_gateway: LLMGateway,
    timeout: float | None = None,
) -> ResumeOutcome
```

第一版语义：

```text
request_pause_at_next_turn_boundary(...) 只请求协作式暂停，不取消底层 episode。
timeout 只表示等待 checkpoint ready 的时间上限，不表示 episode 失败。
超时后返回 waiting_for_turn_boundary 或 pause_timeout，不生成 terminal RepoHarnessEpisodeResult。
pause wait timeout 不会自动撤销 pause request；后续到达安全 turn boundary 时仍然可以生成 checkpoint。
如果调用方要撤销 pause request，必须调用 cancel_pause_request(...) 或等价显式动作。
handle.wait_result(timeout=...) 在 paused 状态下不能返回 terminal result。
handle.wait_result(timeout=...) 如果等待超时，必须抛 asyncio.TimeoutError，且不能改变 paused 状态。
只有 resume 后 episode 运行到终态，wait_result(...) 才能返回 RepoHarnessEpisodeResult。
resume(...) 只能在当前 handle 已经 paused 且 checkpoint 通过校验后调用。
resume(...) 成功后继续同一个 logical trajectory，但必须记录新的 resume_attempt_id。
```

如果实现上更适合把 resume 放在 `RepoHarnessRuntime.resume_episode(...)`，也可以接受。但执行计划必须保证调用方不会把 partial checkpoint 误当作 terminal result。

## 9. Snapshot / ResumeCapability 投影

`AsyncEpisodeSnapshot.resume` 需要从 Stage 13.1 的默认 unsupported 状态升级为可表达状态：

```text
resume_supported=false, resume_status=unsupported_in_stage13_1
```

变成：

```text
resume_supported=true / false
resume_status=waiting_for_turn_boundary | checkpoint_ready | paused | resume_running | resume_failed
resume_ref=rh://partial-checkpoints/<checkpoint_id> 或 None
```

规则：

```text
只有 checkpoint 已经通过 Stage 14.2 schema、visibility、digest 和 writer lease 校验后，resume_supported 才能为 true。
snapshot 里不能嵌入完整 PartialEpisodeCheckpoint 对象。
snapshot 只能携带 opaque resume_ref、checkpoint digest、状态和必要 diagnostics。
```

## 10. Checkpoint 构造规则

Stage 14.3 必须通过 Stage 14.2 的 `PartialEpisodeCheckpoint` 生成 checkpoint。不能新增一套简化 checkpoint。

checkpoint builder 必须从真实 runtime facts 构造：

```text
episode_id / run_id / task_id / sample_attempt_id
turn_index / context_revision
generation records
response_ids / response_mask / response_logprobs / response_spans
workspace snapshot / workspace lease / dependency environment refs
recorder cursor / artifact manifest / transcript / events refs
tool pairing state
durable writer lease facts
reward finality facts
policy version / global steps / parameter versions
visibility scan digest
content digest / trajectory digest
```

如果某项事实缺失，不允许伪造默认值。应返回：

```text
pause_status = pause_rejected
reason = missing_<fact_name>
```

例如：

```text
missing_generation_records
missing_recorder_cursor
missing_workspace_lease
missing_tool_observation_projection
missing_visibility_scan_digest
```

## 11. 同进程 ResumeStateStore

Stage 14.3 第一版只要求同进程恢复。建议新增 runtime-private `ResumeStateStore`：

```text
checkpoint_id -> runtime-private resume state
```

runtime-private resume state 可以包含：

```text
workspace lease handle
run directory writer ownership
recorder cursor handle 或可恢复 refs
agent loop message state
tool result state
generation record collector state
budget state
context revision
```

这些内容不能进入 public checkpoint、DataProto、TransferQueue、AgentLoopOutput 或 acceptance summary。

如果 checkpoint 来自另一个进程、另一个 runtime、另一个 worker，第一版必须返回：

```text
resume_supported=false
resume_status=unsupported_cross_process_resume_in_stage14_3
```

`resume(checkpoint)` 不能只靠 checkpoint schema 通过就启动。它必须同时找到当前 runtime 的 `ResumeStateStore` entry，并校验：

```text
checkpoint_id 匹配
content_digest 匹配
run_id 匹配
workspace lease token 匹配
recorder cursor digest 匹配
generation_record_digest 匹配
```

没有 `ResumeStateStore` entry 的 checkpoint，即使 schema 合法，也必须返回 `unsupported_cross_process_resume_in_stage14_3` 或等价结构化状态。

不要假装已经支持耐久跨进程恢复。

## 12. Workspace 和 run directory lifecycle

暂停成功后必须满足：

```text
workspace lease 仍然 active
run directory writer 仍然 active
recorder cursor 已 flush，但 run 未 finalization
cleanup 未执行
同一个 run_id 不能启动另一个 episode
```

恢复完成并得到终态后：

```text
final verifier 可以运行
reward boundary 可以 final
run_status.json 必须最终不是 RUNNING
workspace lease 可以释放
cleanup_status 必须可解释
```

取消暂停中的 episode 时：

```text
如果 checkpoint 已生成但未 resume，cancel 必须释放 workspace lease
run directory writer 必须 finalize 或写入 cancelled 状态
checkpoint 只能进入 diagnostic / cancelled side channel
```

## 13. Resume 后的 sample identity 和 digest

resume 后不能把旧 prefix 伪装成新的 fresh trajectory。

必须记录：

```text
原 sample_attempt_id
新的 resume_attempt_id
logical episode_id / run_id
resume checkpoint_id
resume checkpoint content_digest
resume checkpoint trajectory_digest
resume 前后的 generation_record_digest
resume 后最终 trajectory_digest
```

resume 后进入 queue 前必须重新计算：

```text
终态 content_digest
终态 trajectory_digest
终态 generation_record_digest
staleness
parameter version window
reward finality
visibility scan digest
formal online RL validator
formal async online RL validator
```

旧 checkpoint 的 `content_digest`、`trajectory_digest`、`generation_record_digest` 只能作为 provenance 记录，用来说明恢复从哪里开始。它们不能作为 resume 后终态样本的新鲜度、reward finality、visibility 或 policy-loss 有效性的依据。resume 后的终态 digest 必须从最终 `TrainingView`、最终 `GenerationRecord`、最终 sample identity、最终 response spans 和最终 reward binding 重新计算，并与 formal validator 使用的实际 batch facts 绑定。

如果 resume 时当前参数版本已经超过阈值，结果必须进入 rejected / diagnostic side channel，不能进入 policy loss。

## 14. Policy-loss 边界

Stage 14.3 必须保留 Stage 14.2 的边界：

```text
PartialEpisodeCheckpoint -> policy loss: 永远拒绝
PartialCheckpointQueueFacts.valid_for_policy_loss: 永远 false
resume 前 checkpoint: diagnostic / resume_preparation only
resume 后完整 EpisodeResult: 只有 formal validator 通过才可能 valid
```

需要补充测试：

```text
pause checkpoint 不能进入 FormalOnlineRLSample
pause checkpoint 不能进入 FormalAsyncOnlineRLSample
pause checkpoint 不能进入 RepoHarnessFullyAsyncQueueFacts valid path
resume 后终态样本如果缺 logprob / generation record / visibility digest，必须被 formal gate 拒绝
```

## 15. AgentLoop 集成策略

优先实现协作式 boundary hook，而不是从外部杀线程。

第一版推荐策略是“线程内协作式阻塞”，而不是让 AgentLoop 完全退出后再重建内部状态：

```text
1. 在 AgentLoop 中增加极窄的 optional turn_boundary_callback。
2. callback 只在工具调用和工具 observation 已经写入后触发。
3. callback 到达安全 boundary 后构造 checkpoint，并把状态切换为 paused。
4. AgentLoop 所在 worker thread 阻塞等待 resume / cancel 信号。
5. workspace lease、run directory writer、recorder handle 和 generation record collector 仍留在原 runtime state 中。
6. resume(...) 只释放同进程 pause gate，让同一个 AgentLoop 继续执行。
```

不推荐第一版把 AgentLoop 完全退出成 `PausedAgentState` 后再重建。那会要求保存和恢复完整 AgentLoop 内部状态，容易提前演变成跨进程 durable resume。只有在线程内阻塞方案被证明不可行时，才可以设计 `EpisodePaused` / `PausedAgentState`，并且必须另行列出需要保存的完整状态和回退边界。

如果当前 agent loop 很难安全插入工具后 callback，第一版可以只支持“无 pending tool call 的 turn boundary”，但必须在执行报告中明确限制。不能把“模型刚输出 tool call、工具还没执行”的位置当成安全 checkpoint。

## 16. 测试计划

### 16.1 Contract 和 helper 测试

新增：

```text
tests/unit/test_repo_harness_rl_stage14_3_pause_resume_contract.py
```

覆盖：

```text
PauseRequest / PauseOutcome / ResumeRequest / ResumeOutcome schema roundtrip
resume_ref 必须是 opaque ref
snapshot 不能嵌入完整 checkpoint
checkpoint tamper 后 resume request 被拒绝
cross-process checkpoint 返回 unsupported
合法 schema 但缺少 ResumeStateStore entry 的 checkpoint 返回 unsupported_cross_process_resume_in_stage14_3
```

### 16.2 Async facade 测试

新增：

```text
tests/unit/test_repo_harness_rl_stage14_3_async_pause_facade.py
```

覆盖：

```text
handle.request_pause_at_next_turn_boundary(...) 快速返回等待状态
wait_result(timeout=...) 不会把 pause wait timeout 当成 terminal result
pause 成功后，handle.wait_result(timeout=短时间) 必须抛 asyncio.TimeoutError
resume 后，handle.wait_result(timeout=...) 才返回 terminal RepoHarnessEpisodeResult
request_pause_at_next_turn_boundary(timeout=短时间) 超时后 pause request 仍然保留
cancel_pause_request 或等价显式动作可以撤销尚未到达 boundary 的 pause request
paused handle.snapshot() 中 resume_supported=true
paused handle.snapshot() 必须显示 run_directory_writer_active=true
paused handle.snapshot() 必须显示 workspace_lease_safely_released=false
paused checkpoint 的 recorder cursor 可以是 flushed，但不能是 finalized
paused 状态下 run directory single writer 仍归当前 runtime
paused 时同 run_id 第二个 start_episode 被拒绝
cancel paused handle 会释放 workspace / writer ownership
resume 后 terminal result 正常 unregister
```

### 16.3 real_episode turn boundary 测试

新增：

```text
tests/unit/test_repo_harness_rl_stage14_3_real_episode_turn_boundary.py
```

覆盖：

```text
fake gateway + 极小仓库任务在 turn boundary 生成 checkpoint
checkpoint 包含真实 generation records、response spans、workspace refs、recorder cursor 和 durable lease facts
assistant final answer 且 final verifier 尚未启动时可以生成 checkpoint
final answer checkpoint resume 后继续进入 final verifier / reward boundary
resume 后 episode 继续运行到 final verifier accepted
resume 后 TrainingView.response_ids / response_logprobs 来自 generation records，不是最终文本重新分词
resume 后 run_status.json 不停留在 RUNNING
```

### 16.4 负例测试

新增：

```text
tests/unit/test_repo_harness_rl_stage14_3_resume_policy_gate.py
```

覆盖：

```text
gateway call in flight 时请求 pause 不生成 checkpoint
tool command in flight 时请求 pause 不生成 checkpoint
final verifier in flight 时请求 pause 被拒绝或等待
artifact manifest write in flight 时请求 pause 不生成 checkpoint
reward metadata 写入中请求 pause 不生成 checkpoint
cleanup 执行中请求 pause 不生成 checkpoint
tampered checkpoint 被拒绝
lost workspace lease 被拒绝
recorder cursor mismatch 被拒绝
generation record digest mismatch 被拒绝
stale checkpoint 被拒绝
partial checkpoint 进入 policy loss path 被拒绝
```

## 17. 验收命令

本地实现完成后至少运行：

```bash
PYTHONPATH=src:tests/unit PATH=.venv/bin:$PATH python -m compileall -q src

PYTHONPATH=src:tests/unit PATH=.venv/bin:$PATH python -m pytest -q \
  tests/unit/test_repo_harness_rl_stage14_2_partial_checkpoint_schema.py \
  tests/unit/test_repo_harness_rl_stage14_2_partial_checkpoint_visibility.py \
  tests/unit/test_repo_harness_rl_stage14_2_partial_checkpoint_tamper.py \
  tests/unit/test_repo_harness_rl_stage14_2_partial_checkpoint_policy_gate.py \
  tests/unit/test_repo_harness_rl_stage14_3_pause_resume_contract.py \
  tests/unit/test_repo_harness_rl_stage14_3_async_pause_facade.py \
  tests/unit/test_repo_harness_rl_stage14_3_real_episode_turn_boundary.py \
  tests/unit/test_repo_harness_rl_stage14_3_resume_policy_gate.py
```

关键前置回归：

```bash
PYTHONPATH=src:tests/unit PATH=.venv/bin:$PATH python -m pytest -q \
  tests/unit/test_repo_harness_rl_stage13_1_async_facade.py \
  tests/unit/test_repo_harness_rl_stage13_1_async_snapshot.py \
  tests/unit/test_repo_harness_verl_stage13_2_fully_async_bridge.py \
  tests/unit/test_repo_harness_verl_stage13_2_message_queue.py \
  tests/unit/test_repo_harness_verl_stage13_3a_async_producer.py \
  tests/unit/test_repo_harness_verl_stage13_3a_message_queue_filter.py \
  tests/unit/test_repo_harness_verl_stage14_acceptance.py \
  tests/unit/test_repo_harness_verl_stage14_task_pool.py
```

导入边界：

```bash
PYTHONPATH=src PATH=.venv/bin:$PATH python - <<'PY'
import sys
import repo_harness.rl
loaded = sorted(name for name in ("verl", "torch", "ray", "tensordict") if name in sys.modules)
if loaded:
    raise SystemExit(f"unexpected_heavy_imports={loaded}")
print("ordinary_import_ok")
PY

if rg -n '(^|\s)(import|from)\s+verl' src/repo_harness/rl src/repo_harness/agent_loop; then
  exit 1
else
  echo no_core_verl_imports
fi
```

格式检查：

```bash
git diff --check -- \
  src/repo_harness/rl \
  src/repo_harness/agent_loop \
  tests/unit/test_repo_harness_rl_stage14_3_*.py \
  docs/agentic_RL/repo_harness_verl_workstreams/30-stage-14-3-execution-plan.md
```

## 18. 子代理审查重点

实现完成后交给子代理做只读审查，重点检查：

```text
1. pause 是否只发生在真正安全的 turn boundary。
2. paused 状态是否错误释放 workspace lease 或 run directory writer。
3. resume 是否重新校验 checkpoint，而不是信任已构造对象。
4. resume 后是否重新计算 staleness、visibility、reward finality 和 formal validator。
5. partial checkpoint 是否仍不能进入 policy loss。
6. cancel / timeout / tamper / lost lease 是否都有结构化失败。
7. 是否越界实现了 reference/verl partial_rollout 或远端 GPU 逻辑。
```

## 19. 通过后进入下一阶段的条件

只有下面条件全部满足，才可以进入 Stage 15：

```text
Stage 14.3 本地 pause / resume facade 通过
resume 后终态样本 formal validator 通过
partial checkpoint policy-loss gate 仍然拒绝
workspace / recorder / run directory lifecycle 无泄漏
subagent 未发现 P1 / P2
```

Stage 15 才开始设计真实 `partial_rollout=True` 远端 smoke。Stage 14.3 不应该提前打开真实 fully async partial rollout。
