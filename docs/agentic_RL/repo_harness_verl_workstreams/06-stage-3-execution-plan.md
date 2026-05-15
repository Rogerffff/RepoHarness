# Stage 3 执行计划：实现 run_mode 与 training_fast recorder

状态：待执行  
前置状态：Stage 0H、Stage 1、Stage 2 已完成。Stage 2 已经新增 `RepoHarnessRuntime.run_episode(...)` 的异步 runtime facade，并且保留了 `LLMGateway` 作为训练后端无关的模型调用边界。

## 1. 阶段目标

Stage 3 的目标是让 RepoHarness 在不改变任务语义、不改变 verifier / reward 权威边界、不引入 verl 依赖的前提下，支持不同运行模式对应的记录策略。

本阶段需要实现三类 `run_mode` 的第一版 recorder 行为：

```text
full_audit
training_fast
training_debug
```

核心目标是：

- `full_audit` 继续保留完整审计材料，适合评测、复查和人工调试。
- `training_fast` 面向在线训练 rollout，默认减少大体积原始 artifact 写入，但仍保留训练复查所需的 hash、引用、patch、reward、verifier summary、artifact manifest 和 timing summary 引用。
- `training_debug` 作为中间模式，允许在明确配置下保留采样或截断后的调试材料，但不能绕过模型可见性和 batch 可传播字段规则。

Stage 3 不是性能系统重写，也不是 verl adapter 实现。本阶段只建立 run mode 到 recorder policy 的正式边界，并补齐必要测试，保证后续 Stage 4 到 Stage 12 可以在稳定记录契约上继续推进。

需要特别说明的是，顺序计划和 hardening contract 已经把 `training_fast` artifact bytes 下降、8 条 fake gateway smoke，以及 `TimingSummary` 至少解释 95% outer wall time 列为验收门槛。Stage 3 因此需要为本阶段覆盖的 runtime facade / deterministic recorder 路径实现最小 timing attribution，使这些路径的 `timing_explained_ratio >= 0.95`。Stage 4 仍然负责把 timing/resource 统计扩展到完整 workspace、Docker、tool、verifier 和 cleanup 维度。

## 2. 必须保持的边界

1. `run_mode` 只能影响记录粒度、artifact 保留策略、预算和执行记录方式，不能改变任务输入、workspace 语义、verifier 规则或 reward 计算语义。
2. `training_fast` 不能通过删除关键 evidence 来制造体积下降。patch、reward metadata 引用、final verifier 引用、trajectory 引用、artifact manifest、关键 hash 和 `AuditRef` 仍然必须可追溯。
3. `training_fast` 默认不保存外部 provider 的明文 reasoning trace / thinking trace。
4. `training_fast` 默认不保存完整 raw provider request / response 明文；需要保存 hash、大小、截断预览或 projection 引用。
5. `TrainingView.extra_fields` 仍然只允许短小、扁平、`repo_harness_*` 命名空间字段和 opaque refs，不能放入嵌套 `audit_ref` 对象、绝对路径、完整 reward metadata 或隐藏 verifier 材料。
6. 本阶段不能引入 `verl` import，也不能提前实现 `RepoHarnessVerlAgentLoop`、`AgentLoopOutput` 转换器、Ray/vLLM/SGLang 调度或真实训练侧 rollout。
7. 本阶段不能把缺失 token / logprob 的旧 provider 结果伪装成正式 online RL 样本。缺失正式 token 证据的路径仍然只能作为 diagnostic result 或 offline data 使用。
8. Stage 3 需要为自己新增或改造的 runtime facade / recorder smoke 路径提供最小 `TimingSummary` 解释率，至少解释 95% outer wall time。Stage 4 才负责完整 `TimingSummary` 和 `ResourceSummary` 的生产级统计，包括 workspace materialization、Docker setup、tool execution、verifier、reward compute、artifact writer、cleanup 和资源使用细分。

## 3. 需要先阅读和确认的代码位置

实施前先只读检查这些文件，确认当前实现风格和测试边界：

```text
src/repo_harness/trajectory/recorder.py
src/repo_harness/trajectory/schemas.py
src/repo_harness/model_client/mock.py
src/repo_harness/model_client/replay.py
src/repo_harness/model_client/providers/common.py
src/repo_harness/model_client/provider_private_state.py
src/repo_harness/context/manager.py
src/repo_harness/agent_loop/loop.py
src/repo_harness/rl/runtime.py
src/repo_harness/export/exporter.py
src/repo_harness/export/audit.py
src/repo_harness/export/schemas.py
```

同时用 `rg` 搜索以下关键词，避免遗漏现有 artifact 写入点：

```text
raw_provider_request
raw_provider_response
prepared_messages
reasoning_trace
thinking_trace
provider_private_state
write_artifact
write_json_artifact
retention_policy
artifact_budget_exhausted
```

当前 export / audit 相关逻辑主要在 `src/repo_harness/export/exporter.py` 和 `src/repo_harness/export/audit.py`，不要引用不存在的 `src/repo_harness/training_export.py`。如果实际搜索结果显示某些 export helper 已经继续拆分到其他文件，需要按搜索结果补充阅读对应文件。

## 4. 设计方案

### 4.1 Recorder profile

新增或扩展一个训练后端无关的 recorder profile / recorder policy 结构，用于表达当前运行模式下 artifact 的保留策略。

建议字段包括：

```text
mode
save_raw_provider_request
save_raw_provider_response
save_reasoning_trace
save_prepared_messages
prepared_messages_retention
artifact_compression
artifact_sampling_policy
raw_artifact_preview_chars
```

默认策略：

- `full_audit`：保留完整审计材料，尽量延续现有行为。
- `training_fast`：关闭明文 reasoning trace；raw provider request / response 默认只保留 hash、大小、截断预览或 projection；大型 prepared messages 默认只保留 hash、压缩引用、采样引用或 projection 引用。
- `training_debug`：默认比 `full_audit` 更节制，比 `training_fast` 更便于排查；可以保留采样或截断后的原始材料，但需要在 manifest 中清楚标记。

具体类的位置需要结合现有代码风格决定。优先考虑放在 `src/repo_harness/trajectory/recorder.py` 或新建 `src/repo_harness/trajectory/retention.py`，不要放到 verl 相关命名空间中。

### 4.2 Artifact manifest 扩展

当前 artifact manifest 已经记录 `artifact_id`、`relative_path`、`kind`、`sha256`、`size_bytes`、`retention_policy` 等字段。Stage 3 需要让 manifest 或 artifact 事件能够表达：

```text
complete
truncated
sampled
compressed
hash_only
projection_only
profile
original_size_bytes
preview_size_bytes
```

实现时必须保持向后兼容。第一版推荐采用“单独 facts artifact + event metadata”的方式，而不是直接把未知字段塞进 `artifacts.json` 的 `ArtifactRef` entry：

- `artifacts.json` 中的每条记录仍然保持 `ArtifactRef` 可校验形态，避免破坏 `verify_artifact_manifest(...)`。
- 对于 `hash_only`、`projection_only`、`truncated`、`sampled`、`compressed` 这些事实，写入小型 JSON artifact，例如 `artifact_retention_facts` 或 `artifact_projection_facts`。
- facts artifact 必须有真实落盘文件，不能创建没有文件的 manifest entry。
- facts artifact 中记录原始 artifact kind、原始大小、原始 hash、preview 大小、retention 原因、run mode 和 profile 名称。
- 如果后续确实需要扩展 `ArtifactRef` schema，新增字段必须是可选字段或有安全默认值，并且必须同步更新 manifest 校验测试。

### 4.3 Runtime run_mode 传递

`RepoHarnessEpisodeRequest.run_mode` 已经由 Stage 1 schema 固定。Stage 3 需要把它传递到 recorder profile：

```text
RepoHarnessEpisodeRequest.run_mode
-> RepoHarnessRuntime.run_episode(...)
-> recorder profile / recorder policy
-> RunRecorder artifact writing behavior
```

第一版可以只接通 Stage 2 runtime facade 的最小路径和现有 recorder 写入点，不要求一次性改完整 CLI 执行路径。但如果现有 `run_task(...)` 入口已经能安全接收 recorder profile，应优先使用同一个 profile，避免形成两套记录语义。

需要注意：当前 Stage 2 runtime facade 本身主要负责 episode schema、gateway 调用和结果投影，并不天然创建 `RunRecorder` 或写大量 artifact。因此 Stage 3 的 artifact bytes 对比验收不能只依赖当前 runtime facade。第一版应该新增一个 deterministic recorder test path：使用 `RunRecorder`、固定大 payload、固定 raw provider request / response、固定 prepared messages 和固定 reasoning trace facts，分别以 `full_audit` 和 `training_fast` 运行同一组写入动作，然后比较落盘 artifact bytes。这个 test path 用来验证 recorder policy 的体积下降和保留事实；runtime facade 只负责把 `run_mode` 映射到同一个 recorder profile，避免两套规则。

### 4.4 Raw provider request / response 投影

对 raw provider request / response 的处理规则：

- `full_audit`：保留现有完整记录行为。
- `training_fast`：默认保存 hash、原始大小、截断预览、projection artifact 或 opaque artifact ref，不保存完整明文。
- `training_debug`：允许保存截断或采样后的内容，并在 manifest 中标记采样和截断事实。

如果 provider 响应中存在 reasoning trace / thinking trace：

- `training_fast` 默认必须拒绝明文写入。
- 可以保留不可逆 hash、长度、是否存在的布尔事实。
- 不得把 reasoning trace / thinking trace 放入模型可见字段或 batch 可传播字段。
- `src/repo_harness/model_client/provider_private_state.py` 中显式 opt-in 的 reasoning trace training export 路径，不能在 `training_fast` 下被默认打开。只有 `full_audit` 或明确 diagnostic/export policy 才能保留明文 reasoning trace source，而且必须继续保持现有 explicit opt-in 语义。

### 4.5 Prepared messages 策略

`prepared_messages` 可能包含大体积 prompt、工具上下文或投影后的模型输入。Stage 3 需要给它明确 retention policy：

- `full_audit` 保留完整或当前已有行为。
- `training_fast` 默认保留 hash、大小、截断预览或 projection ref。
- `training_debug` 可以保留采样或截断版本。

当前 export / audit 对 `prepared_messages_ref` 有强依赖：exporter 会读取 `model_input_snapshot` 中的 `prepared_messages_ref`，并校验 `prepared_messages_sha256` 和 `model_input_hash`；audit 也会确认对应文件存在、sha 匹配、JSON 可解析并包含期望 tool call / observation。因此 Stage 3 实施时必须遵守以下兼容规则：

- 不能把现有 `prepared_messages_ref` 静默替换成无法通过旧 audit 的 hash-only artifact。
- 如果 Stage 3 要降低 `prepared_messages` 体积，必须同时新增显式 projection artifact，例如 `prepared_messages_projection` 或 `prepared_messages_retention_facts`，并更新 export / audit 逻辑，使 training_fast record 能按 projection policy 校验。
- 如果本阶段没有完成 export / audit 对 projection 的支持，则 `training_fast` 仍需保留完整 `prepared_messages`，并在 artifact bytes 分类报告中说明 `prepared_messages` 因现有 export / audit 强依赖暂未降级。
- 无论选择哪条路径，`model_input_hash` 不能被重新解释成另一个 payload 的 hash。

不能通过最终文本重新分词来伪造 `TrainingView.response_ids` 或 `response_logprobs`。如果某一路径没有真实 token 和 log probability 证据，仍然应保持 `invalid_for_online_rl=true`。

### 4.6 最小 TimingSummary attribution

为满足当前 hardening gate，Stage 3 需要给本阶段覆盖的 runtime facade / recorder smoke 路径补上最小 timing attribution：

- `rollout_wall_seconds` 记录本次 episode 或 recorder smoke 的外层耗时。
- `model_call_seconds` 记录 gateway 调用耗时，fake gateway 也要计入。
- `artifact_write_seconds` 记录 recorder 写入耗时。
- `cleanup_seconds` 记录 runtime 或 recorder 自己可控的清理耗时。
- `timing_explained_ratio` 至少达到 `0.95`；如果没有达到，需要写入 diagnostics，并且 Stage 3 不应标记完成。

Stage 4 会继续扩展 workspace、Docker、baseline verifier、tool execution、final verifier、reward compute、resource summary 等细分字段。Stage 3 的最小实现不能阻碍 Stage 4 继续加严。

## 5. 建议修改文件

预计主要修改：

```text
src/repo_harness/trajectory/recorder.py
src/repo_harness/trajectory/schemas.py
src/repo_harness/rl/runtime.py
```

根据只读检查结果，可能需要修改：

```text
src/repo_harness/model_client/mock.py
src/repo_harness/model_client/replay.py
src/repo_harness/model_client/providers/common.py
src/repo_harness/model_client/provider_private_state.py
src/repo_harness/context/manager.py
src/repo_harness/agent_loop/loop.py
src/repo_harness/export/exporter.py
src/repo_harness/export/audit.py
src/repo_harness/export/schemas.py
```

预计新增测试：

```text
tests/unit/test_repo_harness_rl_stage3_training_fast_recorder.py
```

如果实际修改触及 export audit、prepared messages、provider artifact binding 或 artifact manifest 读取器，需要补充对应现有测试或新增更聚焦的测试。优先覆盖：

```text
tests/unit/test_run_recorder.py
tests/unit/test_provider_artifact_binding.py
tests/unit/test_export.py
tests/integration/test_export_from_run.py
tests/integration/test_v3_export_audit.py
```

## 6. 实施顺序

1. 先补测试草案，锁定 `full_audit`、`training_fast`、`training_debug` 三种 run mode 的 recorder profile 默认值。
2. 实现 recorder profile / recorder policy，并为 `RunRecorder` 增加可选 profile 参数，默认保持当前 `full_audit` 行为。
3. 为 artifact 写入增加 profile-aware retention 行为，确保 `training_fast` 可以写入 hash、大小、截断预览或 projection，而不是完整明文大 artifact。
4. 新增 retention facts / projection facts artifact，让每个被压缩、采样、截断或 hash-only 的 artifact 都能说明原因和原始大小，同时保持 `ArtifactRef` manifest entry 兼容旧校验。
5. 将 `RepoHarnessEpisodeRequest.run_mode` 传递到 Stage 2 runtime facade 使用的 recorder profile。不能把绝对路径或完整 audit 对象放进 `TrainingView.extra_fields`。
6. 检查并更新 raw provider request / response、prepared messages、provider private state、reasoning trace 写入点，使其遵守 recorder profile。
7. 更新 export / audit 检查：`full_audit` 缺少关键原始材料仍然应被视为审计风险；`training_fast` 缺少完整 raw provider response 不应自动失败，但必须存在 hash、大小、retention policy 和可追溯引用。
8. 如果降低 `prepared_messages` 体积，同一 patch 必须同时更新 export / audit 对 projection policy 的支持；如果没有完成这部分支持，则 `prepared_messages` 暂时保持完整，并在 bytes 分类解释中明确说明原因。
9. 增加 artifact 体积对比测试：同一个 deterministic recorder write path 在 `training_fast` 下的 artifact bytes 至少比 `full_audit` 少 50%；如果测试 fixture 本身太小或某类关键 artifact 不能降级，必须在 manifest 或报告中给出分类解释。
10. 增加 8 条 fake gateway 最小 episode 的固定成本 smoke。这个 smoke 不依赖真实模型和 GPU，只验证 runtime facade / recorder 路径不会引入明显固定开销；默认阈值沿用 180 秒，同时报告实际 p95、artifact bytes 总量和 artifact kind 分类。
11. 为 Stage 3 覆盖的 runtime facade / recorder smoke 路径填充最小 `TimingSummary` attribution，并断言 `timing_explained_ratio >= 0.95`。
12. 新增 Stage 3 专用 fixture 或测试样例覆盖 `full_audit`、`training_fast`、`training_debug` 的默认映射和序列化稳定性。不要修改 Stage 0H 已冻结 canonical fixture 的语义和 sha256 manifest。
13. 复跑 Stage 2、Stage 1、Stage 0H 相关回归测试，确认 schema、visibility 和 runtime facade 没有被破坏。

## 7. 验收标准

Stage 3 完成时，需要满足：

- `RepoHarnessEpisodeRequest.run_mode=full_audit | training_fast | training_debug` 都能被 runtime facade 识别并映射到明确 recorder profile。
- `full_audit` 默认保持现有完整审计记录行为。
- `training_fast` 默认不保存明文 reasoning trace / thinking trace。
- `training_fast` 默认不保存完整 raw provider request / response 明文，而是保存 hash、大小、截断预览、projection 或 opaque artifact ref。
- `training_fast` 仍保留 patch、reward metadata 引用、final verifier 引用、trajectory 引用、artifact manifest、关键 hash 和 `AuditRef`。
- `training_fast` artifact bytes 相比 `full_audit` 至少下降 50%，或者 manifest / 测试报告明确说明各类 artifact 为什么无法下降。
- `training_fast` 对 `prepared_messages` 的处理不会破坏现有 export / audit：要么完整保留现有 `prepared_messages_ref`，要么提供已被 export / audit 正式支持的 projection policy。
- `training_debug` 的采样、截断或保留行为有明确 profile，不会隐式变成 `full_audit` 或绕过 visibility 规则。
- 8 条 fake gateway 最小 episode 的非模型固定成本 smoke 通过，默认阈值为 180 秒。
- Stage 3 覆盖的 runtime facade / recorder smoke 路径输出 `TimingSummary`，并且 `timing_explained_ratio >= 0.95`。
- `TrainingView.extra_fields` 没有出现嵌套 `audit_ref`、绝对路径、完整 reward metadata、hidden verifier、provider secret 或 evaluator-only log。
- `src/repo_harness/rl` 和新增 recorder 代码不 import `verl`。
- Stage 0H、Stage 1、Stage 2 的既有回归测试继续通过。

## 8. 非目标

Stage 3 明确不做：

- 不实现生产级完整 `TimingSummary` / `ResourceSummary` 统计体系；Stage 3 只为本阶段覆盖的 runtime facade / recorder smoke 路径提供最小 95% timing attribution，完整 workspace、Docker、tool、verifier、reward 和 resource 统计仍是 Stage 4 的职责。
- 不实现 `ResourceSummary` 的完整资源统计；这是 Stage 4 的职责。
- 不实现 workspace / container 复用；这是 Stage 6 的职责。
- 不实现 verifier worker pool；这是 Stage 7 的职责。
- 不实现训练预算 no-progress 控制；这是 Stage 8 的职责。
- 不实现并发资源租约；这是 Stage 9 的职责。
- 不实现 `TrainingView` 到 `AgentLoopOutput` 的转换；这是 Stage 10 的职责。
- 不实现 `RepoHarnessVerlAgentLoop` 或 `VerlLLMGateway`；这是 Stage 11 的职责。
- 不通过重新分词最终文本来伪造正式训练 token、mask 或 log probability。

## 9. 建议验收命令

基础命令：

```bash
uv run --extra dev python -m compileall -q src
uv run --extra dev python -m pytest -q tests/unit/test_repo_harness_rl_stage3_training_fast_recorder.py
```

Stage 2、Stage 1、Stage 0H 回归命令：

```bash
uv run --extra dev python -m pytest -q \
  tests/unit/test_repo_harness_rl_stage2_runtime.py \
  tests/unit/test_repo_harness_rl_stage1_schema_roundtrip.py \
  tests/unit/test_repo_harness_rl_stage1_visibility_gateway.py \
  tests/unit/test_repo_harness_verl_contract_fixtures.py \
  tests/unit/test_repo_harness_verl_stage0h_shape_rules.py \
  tests/unit/test_repo_harness_verl_stage0h_visibility.py
```

如果修改触及 trajectory、artifact manifest 或 training export，还需要根据实际变更补跑相关测试。优先用 `rg` 找到现有测试，再补充运行，例如：

```bash
uv run --extra dev python -m pytest -q \
  tests/unit/test_run_recorder.py \
  tests/unit/test_provider_artifact_binding.py \
  tests/unit/test_export.py
```

如果修改了 export / audit 的 integration 行为，需要补跑：

```bash
uv run --extra dev python -m pytest -q \
  tests/integration/test_export_from_run.py \
  tests/integration/test_v3_export_audit.py
```

最终汇报时需要列出：

- 实际修改的文件。
- 每个文件新增或修改了哪些函数、类和测试。
- `full_audit` 与 `training_fast` 的 artifact bytes 对比结果。
- fake gateway 固定成本 smoke 的 p95 结果。
- 哪些 Stage 4 相关验收仍然是后续阶段职责，不能在 Stage 3 中误标为完成。
