# Stage 13.1 Execution Plan: RepoHarness Async Episode Facade Prototype

本阶段目标是在 RepoHarness 内部增加一个最小异步 episode facade，让调用方可以启动、查询、等待、取消和快照化一个 episode。它仍然允许底层真实 `AgentLoop`、工具、workspace、final verifier、reward boundary 和 recorder 暂时运行在受控 executor 或已有 worker pool 中。

Stage 13.1 不是 verl fully async Rollouter / MessageQueue 接入阶段，也不是远端 GPU 训练阶段。它只证明 RepoHarness runtime 本身已经具备 fully async 接入所需的 episode lifecycle 形状。

## 1. 前置状态

Stage 13.0 已完成并提交：

```text
53d0859c feat: add stage13 fully async contracts
```

Stage 13.0 已提供：

- `AsyncEpisodeSnapshot`
- `AsyncEpisodeHandleRef`
- `AsyncEpisodeLifecycleFacts`
- `ResumeCapability`
- `SampleIdentity`
- `RewardFinalityFacts`
- `FormalAsyncOnlineRLSample`
- formal async online RL batch validator
- fully async interface inventory
- fully async queue / RolloutSample visibility helper

Stage 13.1 必须复用这些 contract，不重新发明另一套异步状态 schema。

## 2. 本阶段要实现什么

### 2.1 新增 runtime facade

在 `src/repo_harness/rl/runtime.py` 或相邻小模块中新增：

```python
async def RepoHarnessRuntime.start_episode(
    request: RepoHarnessEpisodeRequest,
    *,
    llm_gateway: LLMGateway,
) -> AsyncEpisodeHandle
```

`start_episode(...)` 不直接等待 episode 终态，而是：

1. 校验 request。
2. 创建一个唯一的 `sample_attempt_id`。
3. 生成 `AsyncEpisodeHandleRef`。
4. 在后台任务中调用现有 `run_episode(...)`。
5. 返回 `AsyncEpisodeHandle`。

第一版可以把现有 `run_episode(...)` 当作底层执行函数，不要求把 `AgentLoop.run(...)` 自身改成异步。

### 2.2 新增 AsyncEpisodeHandle

建议新增 `AsyncEpisodeHandle` runtime-only 对象。它可以放在：

```text
src/repo_harness/rl/async_runtime.py
```

也可以先放在 `runtime.py` 中；如果对象超过轻量封装，优先拆到 `async_runtime.py`，避免 `runtime.py` 继续膨胀。

`AsyncEpisodeHandle` 第一版至少提供：

```python
handle_ref: AsyncEpisodeHandleRef

def status(self) -> AsyncEpisodeStatus
def snapshot(self) -> AsyncEpisodeSnapshot
async def wait_result(self, timeout: float | None = None) -> RepoHarnessEpisodeResult
async def cancel(self, reason: str = "cancel_requested") -> AsyncEpisodeSnapshot
```

语义要求：

- `status()` 必须是非阻塞读。
- `snapshot()` 必须是非阻塞读，并且不能包含本机绝对路径。
- `wait_result(...)` 返回最终 `RepoHarnessEpisodeResult`。
- 如果底层任务失败，`wait_result(...)` 仍应尽量返回结构化 terminal result；只有真正无法构造 episode result 的 runtime bug 才可以抛异常。
- `cancel(...)` 第一版可以请求取消并等待安全边界，不承诺强杀已经进入同步线程的 `AgentLoop`。

### 2.3 新增 lifecycle state machine

Stage 13.1 不需要完整 workflow engine，但需要一个清晰的 runtime-only lifecycle 状态机。建议内部状态至少覆盖：

```text
created
queued
running
cancelling
cancelled
timeout
failed
final_verifier_running
final_verifier_completed
reward_finalized
cleanup_running
completed
orphaned
```

这些状态应该投影到 Stage 13.0 的 `AsyncEpisodeSnapshot.async_status`。

第一版允许较粗粒度状态，例如底层 `run_episode(...)` 是一个整体后台任务时：

```text
created -> queued -> running -> completed
created -> queued -> running -> cancelling -> cancelled
created -> queued -> running -> timeout
```

但必须留下字段表达更细粒度状态，不要在 Stage 13.1 把 schema 写死成只能描述单个 task。

### 2.4 result 与 reward finality 边界

`AsyncEpisodeHandle.wait_result(...)` 返回终态 `RepoHarnessEpisodeResult` 后，调用方仍必须通过 Stage 13.0 的 formal async validator 才能进入 policy loss。

Stage 13.1 不应该在 pending 状态下生成可训练样本：

- pending / running episode 只能进入 observability。
- cancelled / timeout / orphaned episode 默认不可训练。
- `RepoHarnessEpisodeResult.training_view` 只有在终态 result 存在后才允许被转换为 formal async online RL sample。
- `formal_async_online_rl_sample_from_episode_result(...)` 和 `validate_formal_async_online_rl_batch(...)` 仍是唯一训练前闸门。

### 2.5 取消和资源释放语义

取消语义必须保守。

如果 `cancel()` 发生时底层同步工作已经进入 executor：

- 不能假装它已经被强制停止。
- snapshot 必须表达 `async_status=cancelling` 或 `cleanup_running`。
- 如果底层 worker 仍可能访问 workspace，`verifier_worker_may_still_access_workspace=True` 或等价字段必须为真。
- workspace lease、run directory writer 和 resource lease 不能在底层工作仍可能写入时被标为安全释放。
- `wait_result(...)` 最终必须等待 `run_episode(...)` 的 cleanup 保护逻辑完成，或者返回带 orphan diagnostics 的结构化状态。

第一版 `cancel()` 可以采用：

```text
task.cancel()
await shielded cleanup / run_episode cancellation path
```

`cancel()` 第一版只保证记录取消请求，并推动底层 task 进入取消路径；它返回的 snapshot 可以是
`cancelling`、`cleanup_running` 或后续终态，但这个返回值不表示底层同步 worker 已经停止，
也不表示 workspace、run directory 或 resource lease 已经安全释放。最终结构化
`RepoHarnessEpisodeResult` 只能通过 `wait_result()` 获取。
`cancel()` 默认应快速返回当前 snapshot，不等待 terminal result。如果实现需要等待某个安全边界，
必须使用短 timeout 或 bounded wait；超时后返回 `cancelling` 或 `cleanup_running` snapshot。

测试中必须证明：取消后资源不会被提前释放，且 `wait_result()` 不会永久挂起。

### 2.6 timeout 语义

`wait_result(timeout=...)` 的 timeout 只表示调用方等待超时，不等于 episode 本身 timeout。

需要区分：

```text
handle.wait_result(timeout=0.01) 超时
-> 必须抛 asyncio.TimeoutError
-> episode 继续运行

RepoHarnessRuntimeOptions.episode_timeout_seconds 到期
-> episode result.status=timeout
-> snapshot.async_status=timeout 或 cleanup_running
```

实现约束：

- `wait_result(timeout=...)` 必须使用 `asyncio.shield(...)` 或等价保护等待底层 episode task。
- 等待超时只能影响本次等待调用，不能向底层 task 注入 cancellation。
- 不能把调用方等待超时误转换成 `RepoHarnessEpisodeResult.status=cancelled`。
- `wait_result(timeout=...)` 等待超时时不能返回 diagnostic 对象，也不能构造
  `RepoHarnessEpisodeResult`。调用方如果需要观察当前状态，应在捕获 `asyncio.TimeoutError`
  后调用 `snapshot()`。

Stage 13.1 测试必须覆盖这两个 timeout 语义，不能混淆。

### 2.7 resume 语义

Stage 13.1 不实现真实 resume。

`snapshot().resume` 必须使用 Stage 13.0 的第一版语义：

```text
resume_supported=false
resume_status=unsupported_in_stage13_1
resume_ref=None
```

不要在本阶段引入半成品 resume 数据结构。

## 3. 模块改动建议

### 3.1 新增或修改文件

建议新增：

```text
src/repo_harness/rl/async_runtime.py
tests/unit/test_repo_harness_rl_stage13_1_async_facade.py
tests/unit/test_repo_harness_rl_stage13_1_async_cancellation.py
tests/unit/test_repo_harness_rl_stage13_1_async_snapshot.py
```

建议修改：

```text
src/repo_harness/rl/runtime.py
src/repo_harness/rl/__init__.py
```

其中：

- `async_runtime.py` 放 runtime-only handle、state container、snapshot builder。
- `runtime.py` 只增加 `start_episode(...)` 入口和最小调用胶水。
- `__init__.py` 只导出轻量对象，不能让普通 `import repo_harness.rl` 拉起重依赖。

### 3.2 AsyncEpisodeHandle 内部字段

建议内部保存：

```python
request: RepoHarnessEpisodeRequest
task: asyncio.Task[RepoHarnessEpisodeResult]
created_at: datetime
updated_at: datetime
handle_ref: AsyncEpisodeHandleRef
sample_attempt_id: str
status: AsyncEpisodeStatus
result: RepoHarnessEpisodeResult | None
diagnostics: list[str]
cancel_requested: bool
cleanup_status: str | None
```

这些字段是 runtime-only。不要把完整 request、local run directory、workspace path、callable 或 `asyncio.Task` 放进 `TrainingView.extra_fields`、`AgentLoopOutput.extra_fields` 或 DataProto。

### 3.3 sample_attempt_id 生成

第一版可以用稳定、可测试的本地计数：

```text
<episode_id>:attempt-<n>
```

要求：

- 同一个 `RepoHarnessRuntime` 内，同一个 `episode_id` 多次 `start_episode(...)` 必须产生不同 `sample_attempt_id`。
- `sample_attempt_id` 必须通过 `validate_safe_identifier(...)`。
- `run_id` 仍然来自 request，不能自动复用未 finalize 的 run directory。
- 如果同一个 `run_id` 正在运行，必须依赖 Stage 9 `ResourceLeaseManager` 或本阶段新增的 async registry 阻止并发写入。

### 3.4 active handle registry

建议在 `RepoHarnessRuntime` 内维护 runtime-owned registry：

```python
_async_episode_counter_by_episode_id: dict[str, int]
_async_handles_by_ref: dict[str, AsyncEpisodeHandle]
_async_handles_by_run_id: dict[str, AsyncEpisodeHandle]
_async_registry_lock: asyncio.Lock
```

边界：

- 不允许两个 active handle 同时使用同一个 `run_id`，除非已有 resource lease manager 明确拒绝第二个。
- 因为 `ResourceLeaseManager` 是可选的，`_async_handles_by_run_id` 不能只是审计索引。
  `start_episode(...)` 必须先在 registry 中原子占用 `run_id`，再创建和调度后台 task。
- 如果同一个 `run_id` 已有非终态 handle，第二次 `start_episode(...)` 必须立即拒绝，
  或返回一个结构化 terminal error handle；不能先启动第二个 `run_episode(...)`。
- 原子占用和释放必须由 `asyncio.Lock` 或等价机制保护，避免两个并发调用同时通过检查。
- registry 项在 handle terminal 后可以保留一小段时间供审计查询，但不能无限增长。
- Stage 13.1 第一版可以只在进程内实现，不做跨进程持久 registry。

### 3.5 audit refs 与 snapshot

`snapshot()` 必须返回 `AsyncEpisodeSnapshot`。

如果 result 已经完成：

- `episode_status` 来自 `RepoHarnessEpisodeResult.status`。
- `audit_refs` 可以投影 opaque refs，例如 `rh://async/<episode_id>/result`、`rh://audit/...`。
- `final_audit_write_completed=True` 只应在终态 result 已经由 `run_episode(...)` 完成后设置。
- `run_directory_writer_active=False` 只有 final audit 完成后才允许。

如果 result 未完成：

- `final_audit_write_completed=False`。
- `run_directory_writer_active=True`，除非状态仍是 `created` 或 `queued`。
- `workspace_lease_safely_released=False`。
- `resume` 使用 unsupported 默认值。
- 当 runtime mode 是 `real_episode` 且底层 task 未完成时，即使 facade 无法精确知道当前处于
  AgentLoop、final verifier 还是 cleanup 子阶段，也必须保守设置
  `verifier_worker_may_still_access_workspace=True` 和 `workspace_lease_safely_released=False`。

### 3.6 visibility

Stage 13.1 的 handle 和 snapshot 是 runtime observability，不是模型可见字段。

但 snapshot 中所有可序列化字段仍不能包含：

- 本机绝对路径。
- hidden verifier。
- gold patch。
- complete reward metadata。
- provider secret。
- evaluator-only logs。

测试必须对 `snapshot().model_dump_json()` 做 visibility 扫描，至少确认没有 `/Users/`、`/tmp/`、`hidden_verifier`、`ground_truth` 等内容。

## 4. 测试计划

### 4.1 新增 Stage 13.1 单元测试

建议新增：

```text
tests/unit/test_repo_harness_rl_stage13_1_async_facade.py
```

覆盖：

- `start_episode(...)` 立即返回 handle，不等待 episode 完成。
- `handle.status()` 初始为 `queued` 或 `running`。
- `handle.wait_result()` 返回 `RepoHarnessEpisodeResult`。
- 成功 episode 的 final snapshot 为 `completed`。
- `handle.handle_ref.handle_ref` 是 opaque ref，不包含本机路径。
- 同一 `episode_id` 多次 start 产生不同 `sample_attempt_id`。

建议新增：

```text
tests/unit/test_repo_harness_rl_stage13_1_async_cancellation.py
```

覆盖：

- cancel running episode 后，snapshot 进入 `cancelling`、`cancelled`、`cleanup_running` 或 terminal diagnostic 状态。
- 取消后 `wait_result()` 不永久挂起。
- cleanup callback 被取消或延迟时，资源 lease 不提前标为安全释放。
- final verifier / real episode worker 仍可能访问 workspace 时，snapshot 不显示 workspace 已安全释放。
- `handle.wait_result(timeout=0.01)` 超时后，底层 episode 继续运行；随后再次
  `handle.wait_result()` 可以拿到非 `cancelled` 的最终结果。
- 两个并发 `start_episode(...)` 使用同一个 `run_id` 时，第二个不会启动第二个 writer；
  这个用例必须覆盖没有显式传入 `ResourceLeaseManager` 的路径。

建议新增：

```text
tests/unit/test_repo_harness_rl_stage13_1_async_snapshot.py
```

覆盖：

- pending snapshot 没有 final audit completion。
- terminal snapshot 有 final audit completion。
- final audit 完成前 writer active。
- snapshot JSON 不泄漏本机路径或 evaluator-only 字段。
- `resume_supported=false`。

### 4.2 前置回归

实施完成后必须继续运行：

```text
tests/unit/test_repo_harness_rl_stage13_0_async_contracts.py
tests/unit/test_repo_harness_rl_stage13_0_reward_finality.py
tests/unit/test_repo_harness_rl_stage13_0_async_batch_gate.py
tests/unit/test_repo_harness_rl_stage13_0_sample_identity.py
tests/unit/test_repo_harness_rl_stage13_0_async_lifecycle.py
tests/unit/test_repo_harness_verl_stage13_0_fully_async_inventory.py
tests/unit/test_repo_harness_verl_stage13_0_async_visibility.py
```

还需要运行至少这些关键回归：

```text
tests/unit/test_repo_harness_rl_stage9_resource_leases.py
tests/unit/test_repo_harness_rl_stage9_concurrency_runtime.py
tests/unit/test_repo_harness_rl_stage11_5_real_episode_runtime.py
tests/unit/test_repo_harness_rl_stage12_5_formal_batch_gate.py
tests/unit/test_repo_harness_rl_stage12_5_executor_limits.py
tests/unit/test_repo_harness_verl_stage10_agent_loop_output.py
```

原因：

- Stage 13.1 会新增后台 task 和 handle registry，最容易影响 resource lease 和 run directory single writer。
- Stage 11.5 的 real episode runtime 是 Stage 13.1 最重要的底层执行路径。
- Stage 13.0 的 formal async validator 仍是训练前 gate，不能被 async facade 绕过。

## 5. 验收命令

建议实施完成后运行：

```bash
PYTHONPATH=src uv run --extra dev python -m compileall -q src

PYTHONPATH=src uv run --extra dev python -m pytest -q \
  tests/unit/test_repo_harness_rl_stage13_1_async_facade.py \
  tests/unit/test_repo_harness_rl_stage13_1_async_cancellation.py \
  tests/unit/test_repo_harness_rl_stage13_1_async_snapshot.py \
  tests/unit/test_repo_harness_rl_stage13_0_async_contracts.py \
  tests/unit/test_repo_harness_rl_stage13_0_reward_finality.py \
  tests/unit/test_repo_harness_rl_stage13_0_async_batch_gate.py \
  tests/unit/test_repo_harness_rl_stage13_0_sample_identity.py \
  tests/unit/test_repo_harness_rl_stage13_0_async_lifecycle.py \
  tests/unit/test_repo_harness_verl_stage13_0_fully_async_inventory.py \
  tests/unit/test_repo_harness_verl_stage13_0_async_visibility.py \
  tests/unit/test_repo_harness_rl_stage9_resource_leases.py \
  tests/unit/test_repo_harness_rl_stage9_concurrency_runtime.py \
  tests/unit/test_repo_harness_rl_stage11_5_real_episode_runtime.py \
  tests/unit/test_repo_harness_rl_stage12_5_formal_batch_gate.py \
  tests/unit/test_repo_harness_rl_stage12_5_executor_limits.py \
  tests/unit/test_repo_harness_verl_stage10_agent_loop_output.py
```

普通 import 验收：

```bash
PYTHONPATH=src uv run --extra dev python - <<'PY'
import sys
before = {name for name in ("torch", "ray", "tensordict", "verl") if name in sys.modules}
import repo_harness.rl
import repo_harness_verl
after = {name for name in ("torch", "ray", "tensordict", "verl") if name in sys.modules}
print("ordinary_import_ok", sorted(before), sorted(after))
PY
```

verl import 边界扫描：

```bash
if rg -n '(^|\s)(import|from)\s+verl' src/repo_harness/rl; then
  exit 1
fi
```

diff 检查：

```bash
git diff --check -- \
  src/repo_harness/rl \
  tests/unit \
  docs/agentic_RL/repo_harness_verl_workstreams/22-stage-13-1-execution-plan.md
```

## 6. 完成标准

Stage 13.1 可以标记完成，必须同时满足：

- `RepoHarnessRuntime.start_episode(...)` 或等价入口可用。
- handle 可以查询状态、快照、取消和等待结果。
- pending snapshot 不会被误当作 final reward 样本。
- terminal result 仍必须通过 Stage 13.0 formal async validator 才能进入 policy loss。
- 取消或 timeout 不会提前释放仍可能被同步 worker 使用的 workspace、run directory 或 resource lease。
- `wait_result(timeout=...)` 和 episode 自身 timeout 语义分离。
- unsupported resume 以结构化字段表达。
- snapshot 和 handle refs 不泄漏本机绝对路径或 evaluator-only 字段。
- 普通 import 不要求 `torch`、`ray`、`tensordict` 或 `reference/verl`。
- `src/repo_harness/rl` 不 import `verl`。

## 7. 明确不做的事

Stage 13.1 不做：

- 不启动 Ray。
- 不接入 verl `MessageQueue`。
- 不实现 `FullyAsyncRollouter` adapter。
- 不修改 `reference/verl`。
- 不启动 SGLang 或 vLLM。
- 不运行远端 GPU。
- 不实现真实 resume。
- 不实现 async reward backfill worker。
- 不把 pending episode 转成可训练 batch。
- 不把同步 `AgentLoop.run(...)` 改写成 fully async agent loop。

这些内容留给 Stage 13.2 和 Stage 13.3。
