# Stage 6 执行计划：workspace/container 复用和训练环境加速

状态：待实施。本文件只定义 Stage 6 的执行计划，还没有开始代码实现。
前置状态：Stage 0H、Stage 1、Stage 2、Stage 3、Stage 4、Stage 5 已完成。Stage 5 已在提交 `714e290a` 中完成 `LLMGateway` route wrapper、旧 `ModelClient` 到 `LLMGateway` 的迁移边界、正式 online RL route 闸门和相关测试。

## 1. 阶段目标

Stage 6 的目标是降低训练场景中每条 episode 重复创建 workspace、重复恢复依赖、重复执行 setup 的成本，同时保持 RepoHarness 当前最重要的 clean-state、audit 和 verifier 可信边界。

本阶段要解决的问题是：

```text
同一个 repo_ref + base_commit + environment_id + setup/dependency 组合
每条 episode 都重新 checkout、复制 workspace、执行 setup、恢复依赖
-> 训练吞吐太慢
```

Stage 6 第一版要把这条路径改成可审计的 snapshot / cache / lease 体系：

```text
source materialization
-> clean workspace snapshot
-> dependency cache / dependency state facts
-> 每条 episode 派生独立可写 workspace
-> ResourceSummary 记录 snapshot key、cache hit、restore strategy、lease id、cleanup status
```

完成后应该能做到：

1. 第一条任务可以创建 clean workspace snapshot。
2. 后续相同 snapshot key 的 episode 可以复用 snapshot。
3. 并发两条 episode 不能共享同一个可写 workspace。
4. cleanup 失败、snapshot miss、dependency cache miss 都能进入 diagnostics 或 summary facts。
5. `ResourceSummary` 能解释本 episode 的环境复用事实，而不是只写一个模糊的 workspace backend。

## 2. 必须保持的边界

1. Stage 6 不能改变任务语义、agent loop 语义、verifier 权威边界或 reward 计算语义。
2. Stage 6 不能把上一次 rollout 的 patch、测试输出、临时文件、缓存状态或环境变量暴露给下一条 episode。
3. Stage 6 不能让多条 episode 共享同一个可写 workspace。
4. Stage 6 不能默认使用 hardlink 作为可写 workspace 派生方式。hardlink 容易因为写入污染源 snapshot 或其他派生 workspace，第一版禁止作为默认策略。
5. macOS 本地第一版使用普通目录复制作为正确性基线。APFS clone 可以作为可选优化，但必须有明确 fallback；overlayfs 只作为 Linux / Vast.ai 环境的后续可选 backend。
6. warm container pool 不在 Stage 6 第一版实现。第一版可以保留字段和占位 summary，但不要实际引入长期运行容器池。
7. baseline verifier cache 可以规划，但不要让它影响 final verifier 权威语义。final verifier 必须在 clean-state 派生 workspace 中运行。
8. 本地绝对路径不能进入 `TrainingView.extra_fields`、未来 `AgentLoopOutput.extra_fields` 或 batch 可传播字段。
9. `ResourceSummary.workspace_path`、`run_dir`、snapshot ref 等如果需要传播，只能使用相对路径、短 id 或 `rh://` opaque ref。
10. 本阶段不能引入 `verl` import，不能实现 `RepoHarnessVerlAgentLoop`、`VerlLLMGateway`、Ray / vLLM / SGLang server 管理，也不能提前实现 Stage 7 verifier worker pool。

## 3. 第一版覆盖范围

Stage 6 第一版建议聚焦在本地可重复、可测试、不会破坏现有 SWE-Bench 跑法的范围。

必须覆盖：

- workspace snapshot key 计算。
- clean workspace snapshot create / lookup / materialize。
- 每条 episode 独立可写 workspace 派生。
- dependency cache / dependency state facts 的最小审计字段。
- cleanup 成功和失败 diagnostics。
- `ResourceSummary` 中的 snapshot/cache/lease 字段。
- 并发或伪并发测试，证明两个 episode workspace 互不污染。

可以只做接口或占位，不做真实优化：

- warm container pool。
- Docker volume snapshot。
- overlayfs backend。
- baseline verifier cache 的真实结果复用。
- 分布式 worker 间的全局资源租约。

如果实施时发现需要接入完整 `evaluation/runner.py` 路径，应保持保守迁移：先新增可选 workspace reuse policy，不改变现有默认 CLI 行为。

## 4. 需要先阅读和确认的代码位置

实施前先只读检查：

```text
src/repo_harness/workspace/materialization.py
src/repo_harness/workspace/adapter.py
src/repo_harness/workspace/docker_adapter.py
src/repo_harness/workspace/schemas.py
src/repo_harness/workspace/source_hash.py
src/repo_harness/workspace/backend_factory.py
src/repo_harness/workspace/protocol.py
src/repo_harness/rl/timing.py
src/repo_harness/rl/runtime.py
src/repo_harness/evaluation/runner.py
src/repo_harness/tasks/schemas.py
src/repo_harness/run_metadata/schemas.py
tests/unit/test_repo_materialization.py
tests/integration/test_workspace_lifecycle.py
tests/integration/test_repo_materialization_smoke.py
tests/unit/test_workspace_backend.py
```

需要重点确认：

- 当前 `LocalWorkspaceAdapter.create_source_checkout(...)` 和 `DockerWorkspaceAdapter` 如何调用 `materialize_source(...)`。
- 当前 `DependencyState` 如何记录 strategy、cache key、artifact ref、restored paths 和 excluded diff paths。
- 当前 `ResourceSummary` 已经有哪些 Stage 6 所需字段，例如 `snapshot_key`、`snapshot_cache_hit`、`dependency_cache_hit`、`container_reuse_hit`、`snapshot_restore_strategy`、`lease_id`。
- 当前 `SourceCheckoutFacts`、source tree hash、archive hash 和 task metadata 中有哪些字段可以参与 snapshot key。
- 当前 `keep_workspace`、cleanup、workspace path 生成方式是否会影响复用实现。

## 5. 建议新增或调整的模块

建议新增：

```text
src/repo_harness/workspace/reuse.py
```

建议包含以下结构：

```text
WorkspaceSnapshotKey
WorkspaceSnapshotFacts
WorkspaceLease
WorkspaceReusePolicy
WorkspaceSnapshotManager
WorkspaceReuseDiagnostics
```

职责建议：

- `WorkspaceSnapshotKey`：根据 repo、commit、environment、Docker image、setup command、dependency lock、toolchain 和 harness version 生成稳定 key。
- `WorkspaceSnapshotFacts`：记录 snapshot 创建来源、source tree hash、dependency state ref、restore strategy、created_at、policy version、clean-state 校验结果。
- `WorkspaceLease`：表示一条 episode 当前持有的可写 workspace，包含 `lease_id`、`workspace_id`、`snapshot_key`、`workspace_path`、`cleanup_status`。
- `WorkspaceReusePolicy`：控制是否启用 snapshot、是否启用 dependency cache、restore strategy、cache root、cleanup policy、最大 cache bytes。
- `WorkspaceSnapshotManager`：负责 create / lookup / materialize / release / cleanup。

如果现有 `materialization.py` 中已有函数可以复用，应把复制逻辑沉到底层 helper，避免 `adapter.py`、`docker_adapter.py` 和新 manager 各自实现一套不一致的目录复制规则。

`WorkspaceSnapshotManager` 还必须明确本地并发语义。相同 snapshot key 被两个进程或两个线程同时创建时，不能让两个 writer 同时写入同一个目标 snapshot 目录。第一版至少需要本地 lock 文件或等价机制，并采用临时目录写入、校验完成后原子发布的流程。

## 6. snapshot key 设计

Stage 6 第一版的 snapshot key 必须稳定、可审计，并且不能依赖本地绝对路径。

建议 key 输入：

```text
repo_ref
base_commit
environment_id
docker_image_digest
setup_command_hash
dependency_lock_hash
toolchain_version
harness_version
source_tree_hash
workspace_reuse_policy_version
```

字段来源建议：

- `repo_ref`、`base_commit`、`environment_id` 优先来自 task schema。
- `docker_image_digest` 来自 Docker backend facts；本地模式可以为 `None`。
- `setup_command_hash` 使用 setup command 文本的稳定 hash；没有 setup command 时使用固定 marker。
- `dependency_lock_hash` 可以从 `requirements.txt`、`pyproject.toml`、`uv.lock`、`package-lock.json`、`pnpm-lock.yaml`、`yarn.lock` 等 lock file 的内容 hash 组合得到；找不到时记录缺失 diagnostics。
- `toolchain_version` 第一版可以来自 Python version、harness version、workspace backend version 和 Docker image facts。
- `source_tree_hash` 可以复用现有 `compute_source_tree_hash(...)`。

`source_tree_hash` 需要采用两阶段规则，避免“必须先 materialize 才能 lookup snapshot”的顺序矛盾：

```text
prelookup key:
  优先使用 task 已声明的 source_archive_sha256、mirror_sha256、source_tree_hash、
  repo_ref、base_commit 和 environment spec 生成可预查 key。

post-materialization verification:
  materialize 后用 SourceCheckoutFacts.source_tree_hash 或等价 source tree hash
  校验 snapshot facts，确认命中的 snapshot 确实对应同一份 clean source。
```

如果 task 或 source spec 缺少可预查 hash：

- 本地源目录可以先计算源目录 hash，再 lookup snapshot。
- 如果计算源目录 hash 成本过高或源状态不可确定，可以退化为 snapshot miss。
- 退化为 miss 时必须记录 diagnostics，说明缺少可预查 hash 或 source hash 无法安全计算。
- snapshot hit 后仍必须校验 published facts，不能只凭目录名复用。

禁止：

- 把 `/Users/...`、临时目录、run directory、workspace directory 直接放入 key。
- 在 key 中混入 provider secret、hidden verifier、gold patch 或 evaluator-only artifact。
- 只用 `task_id` 当作 snapshot key，因为同一个 task id 背后的 source 或环境可能变化。

### 6.1 snapshot 创建和发布语义

snapshot 创建必须是可恢复、可审计、并且对本地并发安全的。

第一版发布流程建议：

```text
acquire snapshot-key local lock
  -> 如果目标 snapshot 已存在，读取 facts 并校验 key / source hash / policy version
  -> 如果 facts 合法，直接复用
  -> 如果不存在，写入 .tmp/<snapshot-key>.<creator-id> 临时目录
  -> materialize source / restore dependency / run clean-state check
  -> 写入 snapshot facts 和 manifest
  -> fsync 或等价确保关键 facts 可读
  -> 原子 rename / publish 到 snapshots/<snapshot-key>
  -> release lock
```

要求：

- 不允许直接在最终 snapshot 目录内边写边发布。
- 如果 publish 时发现目标 snapshot 已存在，必须读取并校验现有 facts；合法则复用，不能覆盖。
- 如果现有 facts 损坏或 key 不一致，必须返回 structured diagnostics，不能静默删除或覆盖。
- 临时目录 cleanup 失败必须进入 diagnostics。
- lock 文件路径是 runtime-only 信息，不能进入 batch 可传播字段。

## 7. workspace 派生策略

第一版 restore strategy 建议固定为：

```text
directory_copy
```

语义：

- clean snapshot 目录只作为只读来源使用。
- 每条 episode 创建自己的可写 workspace 目录。
- 派生 workspace 使用普通目录复制生成。
- cleanup 只删除或标记当前 lease 对应的 episode workspace，不能删除仍在使用的 snapshot。

后续可以增加：

```text
apfs_clone_optional
linux_reflink_optional
overlayfs_optional
docker_volume_snapshot_optional
```

但第一版不应默认启用。任何可选策略都必须满足：

- fallback 到 `directory_copy`。
- 派生 workspace 写入不会污染 snapshot。
- 两条并发 episode 写入同名文件时互不影响。
- strategy 进入 `ResourceSummary.snapshot_restore_strategy`。

## 8. dependency cache 策略

Stage 6 第一版不需要做复杂的包管理器全局缓存，但必须把 dependency state 的审计语义固定下来。

建议第一版策略：

```text
none:
  不复用依赖，只记录 cache miss。

rerun_setup:
  沿用当前语义，重新执行 setup，但记录 setup_command_hash 和 dependency_lock_hash。

copy_declared_paths:
  可选，只复制明确声明的依赖目录，例如 .venv、node_modules 或 package manager cache。
```

要求：

- cache key 必须绑定 snapshot key、dependency lock hash、setup command hash 和 backend。
- cache 命中必须进入 `DependencyState.cache_key` 和 `ResourceSummary.dependency_cache_hit`。
- cache miss 也必须明确记录，不能留空让后续审计无法判断。
- cache restore 失败必须变成 structured diagnostics，不能静默回退后假装命中。
- 默认不能复制 `.env`、`.ssh`、`.aws`、provider credentials、token 文件或其他敏感路径。应复用 `DEFAULT_EXCLUDED_DIFF_PATHS` 和敏感路径 denylist。

`copy_declared_paths` 还必须明确 symlink 和越界路径规则：

- 声明路径必须先解析到允许的 workspace 或 dependency cache root 内。
- 不允许跟随指向 home directory、host secret、cache root 外部路径、run directory 或 snapshot 管理目录的 symlink。
- 如果保留 symlink，symlink target 也必须通过边界校验。
- 如果复制目录时使用 `symlinks=True`，测试必须证明越界 symlink 不会让模型 workspace 访问 host secret。
- 声明路径中出现敏感路径、绝对路径或 `..` 越界时必须拒绝或跳过并记录 diagnostics，不能静默复制。

## 9. ResourceSummary 和 TimingSummary 接入

Stage 6 应复用 Stage 4 已有字段，不要再创造一套并行 summary。

`ResourceSummary` 至少需要填：

```text
snapshot_key
snapshot_cache_hit
snapshot_restore_strategy
dependency_state_key
dependency_cache_key
dependency_cache_hit
baseline_cache_hit
container_reuse_hit
lease_id
workspace_backend
cleanup_status
```

第一版 warm container pool 不实现时：

```text
container_reuse_hit = False
```

如果 baseline cache 不实现：

```text
baseline_cache_hit = False
```

`TimingSummary` 至少需要填：

```text
workspace_materialization_seconds
dependency_restore_seconds
cleanup_seconds
```

要求：

- snapshot lookup、copy restore、dependency restore、cleanup 的耗时应使用实测 wall time。
- `workspace_materialization_seconds` 和 `dependency_restore_seconds` 必须是互斥分桶，不能重复计算。
- 如果 runtime facade 尚未接入完整 workspace manager，也要在测试中通过 manager helper 直接验证 timing facts。
- 路径泄漏测试不能只覆盖 `TrainingView.extra_fields`。Stage 6 必须显式测试 `ResourceSummary.workspace_path`、`ResourceSummary.run_dir`、snapshot facts 投影字段和 lease 投影字段都不会泄漏 `/Users/...`、临时目录绝对路径或 host cache root。

## 10. LocalWorkspaceAdapter 接入策略

建议先接入 local process backend，因为它最容易做确定性测试。

建议修改点：

```text
src/repo_harness/workspace/adapter.py
```

第一版可以增加可选参数：

```text
workspace_reuse_policy
snapshot_manager
```

行为建议：

- 默认行为保持不变，避免破坏现有 CLI 和 SWE-Bench 测试。
- 启用 reuse policy 后，`create_source_checkout(...)` 可以先 lookup snapshot。
- snapshot miss 时，按当前 `materialize_source(...)` 创建 source checkout，再创建 clean snapshot facts。
- snapshot hit 时，从 clean snapshot 派生 episode workspace。
- `create_agent_workspace(...)` 和 `create_verification_workspace(...)` 必须拿到各自独立 workspace，不能复用同一个可写目录。

如果为了降低 Stage 6 风险，也可以先不改 `LocalWorkspaceAdapter` 默认构造，而是在 `reuse.py` 中提供独立 manager 测试。真正接入 adapter 的入口可以作为本阶段第二步。

## 11. DockerWorkspaceAdapter 接入策略

Docker 第一版只记录 facts 和保持兼容，不做 warm container pool。

建议修改点：

```text
src/repo_harness/workspace/docker_adapter.py
```

第一版目标：

- 把 Docker image id / digest / platform 纳入 snapshot key 输入。
- Docker backend 的 episode workspace 仍从 clean snapshot 派生。
- 每条命令仍使用现有 Docker 执行隔离策略，不引入长期运行容器。
- `container_reuse_hit=False`，`lease_id` 可以记录 workspace lease id，而不是 container id。

不要做：

- 不要复用长期运行容器。
- 不要绕过当前 Docker mount policy。
- 不要把 host 的 dependency cache 以不受控 bind mount 暴露给模型命令。

## 12. cleanup 和 lease 语义

Stage 6 需要把 cleanup 从“最好清一下”提升为可审计事实。

每个 `WorkspaceLease` 至少有：

```text
lease_id
workspace_id
snapshot_key
workspace_path
created_at
released_at
cleanup_status
cleanup_error
```

状态建议：

```text
active
released
cleanup_failed
orphaned
```

这里要区分两个层面的状态：

- `WorkspaceLease` lifecycle status 可以使用 `active`、`released`、`cleanup_failed`、`orphaned` 这类生命周期词汇。
- `ResourceSummary.cleanup_status` 应尽量对齐现有 Docker 和 recorder 事实中的稳定状态名，例如 `completed`、`failed`、`skipped`、`not_started`。

如果实现中需要在两套状态之间转换，必须有一个小型映射函数或常量表，并有测试覆盖。不要在不同报告里让同一 cleanup 语义随机出现两套名字。

要求：

- `release(...)` 可以重复调用，重复调用不能删除不属于自己的 workspace。
- cleanup 失败必须进入 diagnostics 或 `ResourceSummary.cleanup_status`。
- 异常路径、timeout、cancelled 路径也必须 release lease。
- 并发测试中两个 lease id 必须不同，两个 workspace path 必须不同。

## 13. 建议新增测试

建议新增：

```text
tests/unit/test_workspace_reuse_stage6.py
tests/unit/test_repo_harness_rl_stage6_resource_summary.py
```

可选新增：

```text
tests/integration/test_workspace_reuse_stage6.py
```

测试重点：

1. 相同输入生成相同 snapshot key。
2. 改变 base commit、environment id、setup command、dependency lock 或 Docker image digest 会改变 snapshot key。
3. 第一条 episode 创建 snapshot，第二条相同 key episode 命中 snapshot。
4. 两条 episode 从同一 snapshot 派生不同可写 workspace。
5. 在 episode A 写入文件，不会出现在 episode B。
6. cleanup 成功时 `cleanup_status=completed` 或等价状态。
7. cleanup 失败时产生 diagnostics，且不会影响 snapshot facts。
8. `ResourceSummary` 包含 snapshot key、cache hit、restore strategy、dependency cache hit、container reuse hit、lease id。
9. `TrainingView.extra_fields` 不出现本地绝对 workspace path。
10. `ResourceSummary.workspace_path`、`ResourceSummary.run_dir`、snapshot facts 投影字段和 lease 投影字段不出现本地绝对路径。
11. `copy_declared_paths` 遇到越界 symlink、敏感路径、绝对路径或 `..` 越界时不会复制到 episode workspace。
12. 同一个 snapshot key 被两个创建者同时请求时，只会有一个合法 published snapshot；另一个创建者校验 facts 后复用。
13. Docker route 不实现 warm container pool 时，`container_reuse_hit=False`。

## 14. 建议实施顺序

建议按下面顺序实施：

1. 只读梳理现有 workspace materialization、dependency state、local adapter、Docker adapter 和 `ResourceSummary` 字段。
2. 新增 Stage 6 测试，先覆盖 snapshot key、snapshot hit/miss、workspace 隔离和 cleanup diagnostics。
3. 先补两阶段 snapshot key 和 source hash 规则测试，证明 prelookup key 和 post-materialization verification 都有覆盖。
4. 新增 `workspace/reuse.py`，实现 snapshot key、snapshot facts、reuse policy、lease、manager、本地 lock 和原子 publish。
5. 使用普通目录复制实现 `directory_copy` restore strategy。
6. 为 dependency path copy 补 symlink 边界、敏感路径和越界路径测试；未实现 `copy_declared_paths` 时也要明确拒绝或标记 unsupported。
7. 接入 `LocalWorkspaceAdapter` 的可选 reuse policy，默认行为保持不变。
8. 将 snapshot/cache/lease facts 投影到 `ResourceSummary`。
9. 补 `TimingSummary.workspace_materialization_seconds` 和 `dependency_restore_seconds` 的实测对账。
10. 对 Docker backend 先补 image facts 到 snapshot key 和 `container_reuse_hit=False` summary，不实现 warm container pool。
11. 运行 Stage 6 新测试和 Stage 0H 到 Stage 5 回归。
12. 安排 sub agent 做只读审查，重点检查 clean-state、可写 workspace 隔离、路径泄漏、cleanup 语义、原子发布和是否提前实现 Stage 7 / Stage 9。

## 15. 验收命令

Stage 6 实施完成后至少运行：

```bash
PATH=.venv/bin:$PATH python -m compileall -q src
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_workspace_reuse_stage6.py
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_repo_harness_rl_stage6_resource_summary.py
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_repo_harness_rl_stage5_gateway_routes.py tests/unit/test_repo_harness_rl_stage5_provider_gateway.py
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_repo_harness_rl_stage4_timing_resource.py
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_repo_harness_rl_stage3_training_fast_recorder.py
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_repo_harness_rl_stage2_runtime.py
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_repo_harness_rl_stage1_schema_roundtrip.py tests/unit/test_repo_harness_rl_stage1_visibility_gateway.py
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_repo_harness_verl_contract_fixtures.py tests/unit/test_repo_harness_verl_stage0h_shape_rules.py tests/unit/test_repo_harness_verl_stage0h_visibility.py
rg -n "(^|\\s)(import|from)\\s+verl" src/repo_harness/rl src/repo_harness/workspace || true
```

如果实施接入了 local 或 Docker workspace adapter，还需要运行：

```bash
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_repo_materialization.py
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_workspace_backend.py
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_docker_adapter_image_platform.py
PATH=.venv/bin:$PATH python -m pytest -q tests/integration/test_workspace_lifecycle.py
PATH=.venv/bin:$PATH python -m pytest -q tests/integration/test_repo_materialization_smoke.py
```

如果新增 integration 测试依赖 Docker，可保持可跳过，但跳过条件必须清楚，不能把 Docker 缺失误报为通过真实 Docker 复用验收。

## 16. 阶段出口

Stage 6 可以视为完成的条件：

- 已有稳定 snapshot key schema 和 facts。
- 第一条 episode 可以创建 clean snapshot。
- 后续同 key episode 可以命中 snapshot。
- 每条 episode 都从 snapshot 派生独立可写 workspace。
- 伪并发或并发测试证明两个 episode workspace 互不污染。
- cleanup 成功和失败都有结构化记录。
- `ResourceSummary` 包含 snapshot key、snapshot cache hit、dependency cache hit、baseline cache hit、container reuse hit、snapshot restore strategy、lease id 和 cleanup status。
- `TimingSummary` 至少记录 workspace materialization、dependency restore 和 cleanup 的实测耗时。
- 默认 CLI / SWE-Bench 路径没有被强制改成新的复用策略。
- `src/repo_harness/rl` 和 workspace 复用新增代码没有引入 `verl` import。

Stage 6 完成后，才适合进入 Stage 7 的 verifier worker pool 和 reward 边界优化。
