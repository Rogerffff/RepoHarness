# Stage 12.5 执行计划：同步高吞吐基线加固

本文是 Stage 12.5 的具体实施计划。它承接
`01-sequential-implementation-plan.md` 中已经新增的高层阶段定义，用于指导下一轮代码实现、测试和远端证据收集。

Stage 12 已经证明：

- `real_episode` runtime bridge 可以跑真实 workspace、工具、final verifier 和 reward boundary。
- `RepoHarnessVerlAgentLoop` 可以和真实 `verl` 形状对接。
- 远端 GPU 上已经跑通过真实模型 episode、真实小任务池和小步 trainer smoke。

Stage 12.5 的目标不是重新证明“能跑通”，而是建立进入 Stage 13 fully async 之前必须具备的同步高吞吐基线：

```text
依赖环境可复用
-> workspace 快速安全物化
-> verifier / recorder / tool 热路径可观测并降本
-> 推理服务、tokenizer、Ray worker、系统资源可 profile
-> batch 有效样本补齐和 DataProto padding 可审计
-> 形成本地和远端 evidence bundle
```

## 1. 阶段边界

Stage 12.5 必须坚持下面边界：

- 不实现 fully async AgentLoop。episode interrupt、resume、async reward backfill、跨参数版本 trajectory 处理仍属于 Stage 13。
- 不放松 Stage 0H 到 Stage 12 固定的训练安全规则。正式在线 PPO / GRPO 样本仍必须来自 `route=verl`，必须有 `response_logprobs`，必须通过 formal batch validator 和 visibility gate。
- 不把依赖环境真实路径、workspace 真实路径、run directory、setup log、secret、完整 reward metadata 放入 `TrainingView.extra_fields`、`AgentLoopOutput.extra_fields`、DataProto non-tensor batch 或 meta_info。
- 不把 `training_hot` 做成新的 `RepoHarnessEpisodeRequest.run_mode`。它只能是 `RecorderProfile` 或 runtime-only recorder variant，不能进入 request schema、`TrainingView`、`AgentLoopOutput` 或 DataProto batch。
- 不把大型 SWE-Bench 训练吞吐作为本阶段目标。本阶段使用极小真实仓库任务、小任务池和远端吞吐 profile 证明机制有效。
- 不通过“关闭 log probability、关闭 verifier、关闭 artifact evidence、跳过 visibility check”的方式制造吞吐提升。

## 2. 产物范围

### 2.1 可能新增或修改的代码模块

优先保持模块边界清晰，建议落点如下：

- `src/repo_harness/workspace/dependency_environment.py`
  - 新增 dependency environment key、facts、manager、runtime-only spec 和 report helper。
  - 依赖环境管理涉及 virtualenv、安装命令、cache root、命令环境注入和 workspace adapter，默认归属 workspace 层。
- `src/repo_harness/rl/runtime.py`
  - 编排 dependency environment、共享 workspace cache root、受控 executor、热路径 timing 和 Stage 12.5 runtime options。
  - `repo_harness.rl` core 只消费 opaque environment handle / facts，不拥有依赖环境生命周期。
- `src/repo_harness/rl/timing.py`
  - 补充 setup、dependency restore、snapshot、artifact、tool、verifier、tokenization 等耗时字段或 summary builder。
- `src/repo_harness/rl/training_view.py`
  - 只在必要时补 batch padding profile helper，不改变 Stage 0H 不变量。
- `src/repo_harness/workspace/reuse.py`
  - 扩展 shared cache root、materialization strategy 和 fast materialization safety checks。
- `src/repo_harness/trajectory/recorder.py`
  - 增加 `training_hot` runtime profile 或 manifest batch flush 机制。
- `src/repo_harness/verifier/pool.py`
  - 确认默认接入路径、queue wait 和 worker facts。
- `src/repo_harness_verl/`
  - 增加 Stage 12.5 trainer helper、DataProto padding report、inference profile 和 refill / resample helper。
- `tests/unit/` 和 `tests/integration/`
  - 增加 Stage 12.5 专用测试，同时保留 Stage 0H 到 Stage 12 回归。

如果实现中发现某个 helper 更适合放在已有模块中，可以按现有代码风格调整，但不能把训练后端专属逻辑塞进 `src/repo_harness/rl` core。

### 2.2 本地 evidence

本地实现完成后至少生成或验证：

```text
runs/stage12_5-local-<timestamp>/
  environment_cache_report.json
  workspace_cache_report.json
  verifier_recorder_tool_hot_path_report.json
  dataproto_padding_profile.json
  visibility_and_batch_validation_report.json
  stage12_5_local_acceptance_summary.json
```

本地 evidence 可以使用 fake gateway、mock verifier 和极小 fixture，但必须覆盖 schema、路径不可见性、cache hit / miss、安全回退和 formal batch validator。

### 2.3 远端 GPU evidence

远端运行完成后必须生成：

```text
runs/stage12_5-throughput-<timestamp>/
  environment_cache_report.json
  workspace_cache_report.json
  concurrent_episode_report.json
  trainer_throughput_profile.json
  verifier_recorder_tool_hot_path_report.json
  batch_refill_resample_report.json
  dataproto_padding_profile.json
  inference_metric_source_inventory.json
  inference_server_profile.json
  tokenization_profile.json
  ray_worker_resource_profile.json
  system_resource_profile.json
  visibility_and_batch_validation_report.json
  stage12_5_acceptance_summary.json
```

远端 evidence 必须包含命令日志、代码提交哈希、镜像信息、模型标识、任务清单、运行配置、失败分类和可复查的 summary。

## 3. 实施顺序

Stage 12.5 按下面顺序实施，不要先跳到远端吞吐调参。

### 3.1 Stage 12.5-0：基线 profile 和 acceptance contract

目标：先固定当前同步链路的基线和验收口径，避免优化后无法比较。

需要完成：

- 新增 Stage 12.5 专用 acceptance contract 或 acceptance helper。
- 明确 Stage 12.5 evidence bundle 的字段、文件名和 required / optional / default 策略。
- 增加当前同步路径的 baseline profile，记录未优化前的：
  - dependency setup seconds。
  - workspace materialization seconds。
  - verifier queue wait 和 execution seconds。
  - artifact count、artifact bytes、manifest rewrite count。
  - tool execution seconds。
  - model call seconds。
  - tokenizer / prompt build 时间，如果本地 fake 路径无法测量，则写 unsupported diagnostics。
- 对已有 Stage 12 evidence 中暴露的问题做清晰分类：
  - `run_status.json` 生命周期问题已经由独立提交修复，Stage 12.5 只需要回归验证未来 run 会 finalize。
  - Stage 12 旧 evidence 中的历史 `RUNNING` 状态不回写修改，只在报告中说明它属于历史运行产物。

验收测试建议：

```text
tests/unit/test_repo_harness_rl_stage12_5_acceptance_contract.py
tests/unit/test_repo_harness_rl_stage12_5_baseline_profile.py
```

### 3.2 Stage 12.5-1：DependencyEnvironmentManager

目标：新增 runtime-only dependency environment cache，避免每条 episode 重复安装第三方依赖。

建议新增结构：

```text
DependencyEnvironmentKey
DependencyEnvironmentFacts
DependencyEnvironmentHandle
DependencyEnvironmentManager
DependencyEnvironmentReport
DependencyEnvironmentSpec
```

key 必须拆成三层：

```text
base_environment_key
overlay_environment_key
source_snapshot_key
```

这些 key 不能由 manager 临时猜测仓库结构，也不能硬编码 fixture。第一版必须新增 runtime-only `DependencyEnvironmentSpec` 或 `RealEpisodeEnvironmentSpec`，由 source resolver、task adapter 或 Stage 12.5 trainer helper 在 episode 启动前构造，并传给 `DependencyEnvironmentManager`。

`DependencyEnvironmentSpec` 至少包含：

- lockfile 列表和每个 lockfile 的相对路径、sha256、是否 required。
- setup command 拆分结果：
  - 第三方依赖安装命令。
  - 源码绑定命令。
  - workspace 写入命令。
  - 不支持或必须禁用的命令。
- Python source roots，例如 workspace root、`src/`、`lib/` 或任务显式声明的 source roots。
- package manager 类型和版本来源，例如 pip、uv、npm、pnpm。
- environment variable allowlist，以及每个变量是否只记录去敏摘要。
- cache policy，例如 `read_only_hit`、`create_if_missing`、`disable_cache`。
- Node / JavaScript dependency policy。Stage 12.5 第一版默认只实现 Python / uv / pip dependency environment；Node 生态先记录 unsupported diagnostics，除非同一阶段同时设计 pnpm store、npm cache、`node_modules` overlay 和写隔离策略。
- 命令环境注入策略，例如 Python path entries、cache directory、HOME / XDG cache 隔离策略。
- schema version。

`base_environment_key` 至少包含：

- Python 版本、平台、CPU 架构。
- 操作系统发行版、glibc 或 musl 版本。
- CUDA、torch、compiler ABI；Docker 模式还必须包含 image digest。
- 执行模式：`local_process`、`docker`、`remote_worker` 或后续等价值。
- pip、uv、npm、pnpm 等包管理器版本。
- dependency lock hash，例如 `uv.lock`、`requirements.txt`、`pyproject.toml`、`package-lock.json`、`pnpm-lock.yaml`。
- package index 的非 secret 摘要。不得记录 token、账号或私有 registry secret。
- 影响依赖解析的 environment allowlist 去敏摘要。
- schema version。

`overlay_environment_key` 至少包含：

- setup command hash。
- overlay strategy，例如 `none`、`pythonpath_only`、`copy_declared_paths` 或后续 `overlay_venv`。
- 与仓库相关但不应进入 base environment 的 setup facts。

`source_snapshot_key` 至少包含：

- source tree hash 或 archive sha256。
- base commit、dataset task revision 或等价 source identity。

实现要求：

- 使用本地 lock、临时目录写入、facts 文件校验后原子发布。
- cache hit 时必须读取 facts 并校验 key，一致才可复用。
- cache miss 时只能在临时目录创建环境，发布后再变成 shared environment。
- shared environment 默认只读；如果平台权限无法可靠保护，必须写入 diagnostics。
- episode runtime 中禁止对 shared environment 执行安装、卸载或写入操作。命令策略或 wrapper 至少要拦截：
  - `pip install`
  - `uv pip install`
  - `pip uninstall`
  - `uv pip uninstall`
  - `npm install`
  - `pnpm install`
  - `yarn install`
- 第三方依赖安装可以进入 base environment。
- 绑定源码路径、执行 editable install、生成仓库本地构建产物、写入 episode workspace 的 setup 必须进入 overlay 或 source facts，不能污染 base environment。
- 第一版默认不支持 shared base environment 中的 editable install。仓库源码通过 `environment_spec.pythonpath_entries` 暴露给工具和 verifier。
- 安装命令拦截必须是语义拦截，不只是字符串前缀拦截。除 `pip install`、`uv pip install`、`npm install`、`pnpm install` 外，还必须覆盖 `python -m pip install`、`python -m pip uninstall`、`uv add`、`uv sync`、`npm ci`、`npm add`、`pnpm add`、`yarn install` 等会修改共享环境或锁文件的等价命令。实现时应先解析可执行文件、子命令、目标环境和工作目录，再决定是否允许执行。

命令环境注入要求：

```text
VIRTUAL_ENV=<opaque runtime env path>
PATH=<env>/bin:$PATH
PYTHONNOUSERSITE=1
PYTHONPATH=<environment_spec.pythonpath_entries joined by os.pathsep>
PYTHONDONTWRITEBYTECODE=1
```

`PYTHONPATH` 不能固定假设所有项目都是 flat layout。`environment_spec.pythonpath_entries` 可以包含 workspace root、`src/`、任务声明的 source roots 或 source resolver 识别出的 Python package roots。所有条目都只能作为 runtime command environment 使用，不能进入 batch 可传播字段。

如果使用 pip / uv cache，cache 路径必须是 runtime-only 配置，不能进入 batch 可传播字段。必要时每条 episode 使用隔离的 `HOME`、`XDG_CACHE_HOME`、`PIP_CACHE_DIR` 或 `UV_CACHE_DIR`。

可见性要求：

- `ResourceSummary` 只记录 `repo_harness_environment_ref`、`dependency_cache_key`、`dependency_cache_hit`、`dependency_restore_seconds` 等 opaque / scalar 字段。
- `TrainingView.extra_fields`、`AgentLoopOutput.extra_fields`、DataProto non-tensor batch 和 meta_info 中不能出现本机环境绝对路径。

验收测试建议：

```text
tests/unit/test_repo_harness_rl_stage12_5_dependency_environment.py
tests/unit/test_repo_harness_rl_stage12_5_command_environment.py
```

重点用例：

- key 中 secret 被去敏。
- cache miss 创建新环境，cache hit 复用同一 key。
- 并发创建同一 key 时不会损坏 cache。
- 未完成临时目录不会被当作可用环境。
- shared environment 中的安装命令被拒绝。
- 工具和 verifier 使用注入环境，而不是当前进程 Python。
- `ResourceSummary` 和 batch 字段不泄漏真实路径。

### 3.3 Stage 12.5-2：共享 workspace cache 和快速物化

目标：让训练 helper 可以跨 episode 复用 snapshot cache，并为后续快速物化策略保留安全入口。

需要完成：

- `RepoHarnessRuntimeOptions` 或 Stage 12.5 trainer helper 支持 runtime-only shared workspace cache root。
- `WorkspaceSnapshotManager` 能被多个 episode 复用，而不是每条 episode 在自己的 run directory 下新建 cache。
- snapshot key 必须绑定：
  - source identity。
  - dependency lock facts。
  - setup command facts。
  - environment identity。
- directory copy 保留为默认安全基线。
- fast materialization strategy 第一版可以先实现 profile / opt-in，不必默认开启。
- 如果实现 hardlink、reflink、`rsync --link-dest`、Git worktree 或 overlay workspace，必须先补完整写隔离测试。

快速物化安全要求：

- hardlink 策略只能显式开启，不能默认替代 directory copy。
- 修改 lease 中的文件不能污染 snapshot 或其他 lease。
- symlink 越界检查、敏感路径拒绝、snapshot / lease 一致性检查必须继续生效。
- Git worktree 策略如果实现，必须证明 `.git` metadata、共享分支状态、index lock 和未提交修改不会跨 episode 串扰。
- cleanup 失败必须产生 orphan diagnostics。

验收测试建议：

```text
tests/unit/test_repo_harness_rl_stage12_5_workspace_cache.py
tests/unit/test_workspace_reuse_stage12_5_fast_materialization.py
```

重点用例：

- shared cache root 被多个 episode 命中。
- source snapshot facts 校验失败时拒绝复用。
- lease 路径不进入模型可见字段或 batch 字段。
- hardlink opt-in 修改不污染 snapshot。
- cleanup 失败时 resource summary 写入结构化 diagnostics。

### 3.4 Stage 12.5-3：Verifier、recorder 和 tool hot path

目标：降低最明显的同步固定成本，并让 hot path 成本可观测。

Verifier 要求：

- 真实训练 runtime helper 默认使用有界 `VerifierWorkerPool`。
- 记录 `pool_id`、`worker_id`、queue wait、execution seconds、timeout、error type、release status。
- final verifier timeout 后底层同步 callable 不能被伪装成已经安全终止。如果无法强杀，必须记录 diagnostics，并确保 workspace 生命周期不会早于 verifier callable 结束。
- pytest verifier 避免不必要的重复执行。第一版可以保留安全回退，但必须记录是否发生补跑。

Recorder 要求：

- 新增 runtime-only `training_hot` recorder profile，或者实现 manifest batch flush / finalize。
- `training_hot` 不进入 request schema、`TrainingView`、`AgentLoopOutput` 或 DataProto。
- hot path 默认保留：
  - final patch。
  - final verifier summary。
  - reward boundary summary。
  - timing summary。
  - resource summary。
  - training view。
  - opaque audit refs。
- 命令 stdout / stderr 可以保存投影、截断或合并输出；完整原文只在 debug profile 或抽样审计中保留。
- 必须记录写放大指标：
  - `manifest_rewrite_count_per_episode`
  - `manifest_bytes_written_per_episode`
  - `artifact_write_seconds_p50`
  - `artifact_write_seconds_p95`
  - `artifact_count_per_episode`
  - `artifact_bytes_per_episode`

Tool timing 要求：

- `tool_seconds` 不能继续用固定 `0.0` 占位。
- tool timing 必须来自 `events.jsonl`、tool execution facts 或等价结构化事件。
- 对 `read_file`、`grep`、`edit_file`、`git_diff`、shell command 等高频工具记录：
  - call count。
  - wall seconds。
  - command count。
  - output artifact count。
  - output artifact bytes。

验收测试建议：

```text
tests/unit/test_repo_harness_rl_stage12_5_verifier_pool_default.py
tests/unit/test_repo_harness_rl_stage12_5_recorder_hot_path.py
tests/unit/test_repo_harness_rl_stage12_5_tool_timing.py
```

### 3.5 Stage 12.5-4：推理服务、tokenizer、Ray worker 和系统资源 profile

目标：把非 RepoHarness 内部瓶颈也纳入观测，避免只优化 workspace 和 artifact，却不知道推理服务或 tokenizer 已经成为瓶颈。

推理服务 profile 必须记录：

```text
inference_server_queue_wait_seconds_p50
inference_server_queue_wait_seconds_p95
prefill_seconds_p50
prefill_seconds_p95
decode_seconds_p50
decode_seconds_p95
prefix_cache_hit_rate
kv_cache_eviction_count
num_preempted
tokens_per_second
gpu_utilization_p50
gpu_utilization_p95
batched_token_count_p50
batched_token_count_p95
```

指标来源策略：

Stage 12.5 第一版必须先从当前 `reference/verl` 和远端镜像实际后端中建立一张指标来源表。已知当前代码直接暴露的字段如下：

- `reference/verl/verl/workers/rollout/replica.py` 中 `TokenOutput` 暴露 `token_ids`、`log_probs`、`stop_reason`、`num_preempted` 和 `extra_fields`。
- `reference/verl/verl/workers/rollout/vllm_rollout/vllm_async_server.py` 中 vLLM `generate(...)` 会从 `final_res.outputs[0].num_preempted` 投影到 `TokenOutput.num_preempted`，并把 `global_steps` 放入 `TokenOutput.extra_fields`。
- `reference/verl/verl/workers/rollout/sglang_rollout/async_sglang_server.py` 中 SGLang `generate(...)` 当前返回 `TokenOutput` 时没有设置 `num_preempted`，只把 `global_steps` 和可选 `prompt_logprobs` 放入 `extra_fields`。
- `reference/verl/verl/experimental/agent_loop/single_turn_agent_loop.py` 和 `tool_agent_loop.py` 使用 `simple_timer("generate_sequences", ...)` 记录一次 server generate 调用总耗时。
- `reference/verl/verl/experimental/agent_loop/tool_agent_loop.py` 还使用 `simple_timer("tool_calls", ...)` 记录工具调用总耗时。
- `reference/verl/verl/experimental/agent_loop/agent_loop.py` 的 `_performance_metrics(...)` 会汇总 `agent_loop/generate_sequences/*`、`agent_loop/tool_calls/*`、`agent_loop/compute_score/*` 和 `agent_loop/num_preempted/*`。
- `reference/verl/verl/workers/rollout/llm_server.py` 的 `LLMServerClient._acquire_server(...)` 和 `generate(...)` 是 sticky session / load balancing 的统一入口，可以在 RepoHarness adapter 侧记录 client-side server acquire wait 和 end-to-end server generate wall time。
- `reference/verl/verl/workers/rollout/sglang_rollout/async_sglang_server.py` 在 `config.prometheus.enable` 时设置 `args["enable_metrics"] = True` 并调用 `add_prometheus_middleware(app)`，因此 SGLang 当前路径应从 rollout server 的 `/metrics` 抓取后端指标。
- `reference/verl/verl/workers/rollout/vllm_rollout/vllm_async_server.py` 在 `config.prometheus.enable` 时设置 `served_model_name`，因此 vLLM 当前路径应从 rollout server 的 Prometheus `/metrics` 或 vLLM engine logs 抓取后端指标。

具体 canonical metric 到当前来源的映射如下：

| canonical metric | RepoHarness / verl 直接来源 | SGLang 当前来源 | vLLM 当前来源 | 不可用时 diagnostics |
| --- | --- | --- | --- | --- |
| `inference_server_queue_wait_seconds_*` | client-side：包住 `LLMServerClient._acquire_server(...)` 和 `server.generate.remote(...)` 前等待；server-side：后端 metrics | `/metrics` 中 scheduler / queue / waiting / pending 相关时间或数量指标；实施脚本必须记录实际 metric name | vLLM Prometheus `/metrics` 中 queue / waiting / pending 相关时间或数量指标；实施脚本必须记录实际 metric name | `server_queue_wait_metric_unavailable` |
| `prefill_seconds_*` | `generate_sequences` 只能作为总生成耗时，不能拆分 prefill | `/metrics` 或 scheduler log 中 prefill、time-to-first-token 或等价字段；记录实际 metric name | vLLM `/metrics` 或 engine log 中 prefill、time-to-first-token 或等价字段；记录实际 metric name | `prefill_metric_unavailable` |
| `decode_seconds_*` | `generate_sequences` 只能作为总生成耗时，不能拆分 decode | `/metrics` 或 scheduler log 中 decode、inter-token latency、time-per-output-token 或等价字段；记录实际 metric name | vLLM `/metrics` 或 engine log 中 decode、inter-token latency、time-per-output-token 或等价字段；记录实际 metric name | `decode_metric_unavailable` |
| `prefix_cache_hit_rate` | sticky session 可从 `LLMServerClient.generate(request_id=episode_id, ...)` 是否稳定传入验证，但不能证明命中率 | `/metrics` 中 prefix cache / radix cache hit 相关字段；若只有 hit/miss counter，实施脚本计算 ratio 并记录字段名 | vLLM `/metrics` 中 prefix cache hit / request cache hit 相关字段；若只有 hit/miss counter，实施脚本计算 ratio 并记录字段名 | `prefix_cache_hit_rate_unavailable` |
| `kv_cache_eviction_count` | RepoHarness 只能记录 clear / flush 调用次数，不能替代后端 eviction | `/metrics` 或 scheduler log 中 KV cache eviction / cache flush / evicted block 相关字段；记录实际 metric name | vLLM `/metrics` 或 engine log 中 KV cache eviction / block eviction / cache usage 相关字段；记录实际 metric name | `kv_cache_eviction_metric_unavailable` |
| `num_preempted` | `TokenOutput.num_preempted`，再进入 `AgentLoopMetrics.num_preempted` 和 `_performance_metrics(...)` | 当前 SGLang `TokenOutput` 未设置该字段，除非后端 metrics 提供 preemption counter | vLLM `final_res.outputs[0].num_preempted -> TokenOutput.num_preempted` | `num_preempted_metric_unavailable` |
| `tokens_per_second` | `len(output.token_ids) / measured_generate_seconds` 可作为 client-side estimate | `/metrics` token throughput 字段优先；否则用 client-side estimate 并标注口径 | vLLM `/metrics` token throughput 字段优先；否则用 client-side estimate 并标注口径 | `tokens_per_second_backend_metric_unavailable` |
| `gpu_utilization_*` | RepoHarness 不直接提供 | `nvidia-smi dmon`、DCGM、Ray node metrics 或 Prometheus exporter | `nvidia-smi dmon`、DCGM、Ray node metrics 或 Prometheus exporter | `gpu_utilization_metric_unavailable` |
| `batched_token_count_*` | DataProto 和 prompt / response length profile 提供 batch 侧 token 数 | `/metrics` 或 scheduler log 中 batched tokens / running tokens 字段；记录实际 metric name | vLLM `/metrics` 或 engine log 中 batched tokens / running tokens 字段；记录实际 metric name | `batched_token_count_metric_unavailable` |

实施脚本必须在远端 preflight 中抓取一次后端 `/metrics` 原文或日志摘要，生成 `inference_metric_source_inventory.json`，内容至少包含：

```text
backend_name
backend_version
server_address
metrics_endpoint_checked
raw_metric_names_matched
canonical_metric_mapping
unsupported_diagnostics
```

如果某项指标当前后端不提供，不能填 `0`，必须写入 unsupported diagnostics，例如：

- `prefix_cache_hit_rate_unavailable`
- `kv_cache_eviction_metric_unavailable`
- `num_preempted_metric_unavailable`

`inference_server_profile.json` 必须记录后端名称、后端版本、指标来源、实际字段名和口径说明，避免把 SGLang 和 vLLM 的不同统计口径直接混算。

Sticky session 和 prefix cache 要求：

- 验证 `sticky_session_id=episode_id` 或 adapter 等价字段确实传到后端请求路径。
- 多轮 episode 必须记录 prefix cache 命中率，或说明后端无法提供指标。
- prefix cache 未命中时要能分类：
  - 后端不支持。
  - request id 不稳定。
  - chat template 不稳定。
  - prompt prefix 不稳定。
  - cache eviction。

Tokenizer 和 prompt build profile：

- 记录 prompt build、chat template、tokenize 的 p50 / p95 时间。
- 记录 prompt token length distribution。
- 评估 system prompt、tool schema、task prompt 等稳定前缀的缓存可能性。
- 第一版只要求 profile，不要求实现 prefix token cache。
- 如果实现 prefix token cache，必须证明模型可见 prompt 内容完全一致，并且不会绕过 `raw_prompt` visibility 检查。

Ray worker 和线程池要求：

- 明确每个 Ray worker 内 `RepoHarnessRuntime` 是单例复用，还是每条 episode 新建。
- 明确下面 manager 在 Ray worker 内如何共享：
  - `WorkspaceSnapshotManager`
  - `DependencyEnvironmentManager`
  - `VerifierWorkerPool`
  - `ResourceLeaseManager`
  - gateway route limiter
- 明确跨 Ray worker 是否共享 cache root，以及用什么 lock / atomic publish 保护。
- `RepoHarnessRuntimeOptions.executor_max_workers` 如果继续存在，必须真正约束 `real_episode` worker thread pool。
- 如果当前实现使用 `asyncio.to_thread` 默认 executor，Stage 12.5 必须修正为受控 executor，或者重命名 / 移除误导性配置。
- 记录：
  - `active_agent_loop_threads`
  - `agent_loop_worker_queue_wait_seconds_p50`
  - `agent_loop_worker_queue_wait_seconds_p95`
  - Ray actor CPU 使用率。
  - 本地线程池 queue wait。

系统资源 profile：

- 文件描述符数量。
- 磁盘读写字节数。
- run directory 文件数量。
- cleanup orphan 数量和 diagnostics。
- workspace cleanup seconds。
- verifier subprocess count。

验收测试建议：

```text
tests/unit/test_repo_harness_verl_stage12_5_inference_profile.py
tests/unit/test_repo_harness_verl_stage12_5_tokenization_profile.py
tests/unit/test_repo_harness_verl_stage12_5_ray_worker_resources.py
```

本地测试可以使用 fake metrics source；远端必须使用真实 SGLang 或 vLLM 日志 / metrics。

### 3.6 Stage 12.5-5：有效样本补齐和 DataProto padding profile

目标：让 trainer 只消费 formal-valid 样本，并且能解释无效样本、padding 和 token 利用率。

有效样本分类：

- `valid_trainable_sample`
- `infrastructure_failure`
- `invalid_task`
- `model_format_failure`
- `verifier_rejected`
- `timeout`
- `context_or_length_invalid`
- `missing_logprobs`
- `mixed_route`
- `visibility_rejected`

Refill / resample 规则：

- 第一版默认由 `src/repo_harness_verl` 中的 Stage 12.5 trainer helper 负责收集和补齐 valid samples。
- RepoHarness core 只提供 sample classification、formal validator、reward / validity facts 和 audit evidence，不负责组织 verl trainer batch，也不把 verl trainer 的 refill 逻辑塞进 core runtime。
- verl sampler 只消费已经通过 formal batch validator 的样本。
- 必须配置：
  - target valid sample count。
  - maximum attempts。
  - maximum wall seconds。
  - task sampling dedup rule。
  - 是否允许同一 task retry。
  - insufficient valid batch 的结构化失败字段。
- invalid 样本进入 audit evidence 和诊断统计，但不能进入有效 policy loss。
- 如果 attempt 或 wall time 用尽仍不足 valid samples，必须结构化失败，不能用 invalid 样本补齐。

Formal batch validator 要求：

- `generation_records` 非空。
- `generation_records[*].gateway_route` 全部为 `verl`。
- `TrainingView.online_rl_eligible=True`。
- `repo_harness_invalid_for_online_rl` 不能为 `True`。
- `response_ids`、`response_mask`、`response_logprobs` 长度一致。
- tool observation token 必须 `response_mask=0` 且 `response_logprobs=0.0`。
- missing logprobs、mixed route、overflow、empty response 必须在进入 trainer 前过滤或拒绝。
- token provenance 必须和 `generation_records` 对齐，不能从 assistant 文本重新分词伪造。

DataProto padding profile 必须记录：

```text
actual_prompt_tokens_p50
actual_prompt_tokens_p95
actual_response_tokens_p50
actual_response_tokens_p95
padded_token_ratio
loss_mask_token_ratio
response_mask_zero_ratio
length_overflow_filtered_sample_count
```

如果启用 `use_remove_padding` 或当前 verl 版本等价配置，必须重新验证 Stage 0H 的 token、mask、log probability 长度不变量。

验收测试建议：

```text
tests/unit/test_repo_harness_verl_stage12_5_batch_refill.py
tests/unit/test_repo_harness_verl_stage12_5_dataproto_padding.py
tests/unit/test_repo_harness_rl_stage12_5_formal_batch_gate.py
tests/unit/test_repo_harness_verl_stage12_5_transferqueue_visibility.py
```

还必须覆盖 TransferQueue / `main_ppo_sync.py` 字段传播路径，以及 DataProto `concat`、`select`、`pop` 后的 visibility 和 batch 维度不变量。测试需要证明 batch refill、padding profile、postprocess、TransferQueue 和 DataProto 操作之后，本机路径、hidden verifier、gold patch、accepted label、完整 reward metadata 和 evaluator-only fields 都不会进入 non-tensor batch 或 meta_info。

### 3.7 Stage 12.5-6：本地端到端 smoke

目标：在不依赖 GPU 的情况下证明 Stage 12.5 新增机制不会破坏 Stage 12 的正确链路。

本地 smoke 组合：

- fake `LLMServerClient`。
- `RepoHarnessVerlAgentLoop`。
- `RepoHarnessRuntime(runtime_execution_mode=real_episode)`。
- shared dependency environment manager。
- shared workspace snapshot manager。
- verifier pool。
- `training_fast` 或 runtime-only `training_hot` recorder profile。
- formal batch validator。
- DataProto padding profile helper。

本地验收必须证明：

- cold cache miss 会创建 dependency environment。
- warm cache hit 会复用 dependency environment。
- warm cache 下不重复执行完整 dependency setup。
- workspace lease 和 run directory 相互隔离。
- artifact 写放大指标能产生。
- tool timing 不是固定占位。
- invalid 样本不会进入 formal batch。
- `repo_harness_environment_ref` 是 opaque ref，真实路径没有进入 batch。

### 3.8 Stage 12.5-7：远端 GPU throughput smoke

目标：在 Vast.ai 或等价远端 GPU 环境中，使用真实模型和真实 `verl` trainer 路径收集吞吐 profile。

推荐环境：

- 镜像：`verlai/verl:sgl056.latest` 或当前已验证等价镜像。
- 模型：`Qwen/Qwen2.5-Coder-7B-Instruct` 或同等级小模型。
- 任务：Stage 12 已经使用过的极小真实仓库任务池，必要时增加 2 到 4 个简单任务。
- GPU：单卡或双卡均可。双卡优先用于 trainer profile，不要求本阶段证明多机扩展。

远端运行顺序：

1. 拉取最新分支，记录 commit hash。
2. 运行依赖和 import preflight。
3. 冷缓存 real episode smoke。
4. 热缓存 real episode smoke。
5. 2 到 4 条并发 real episode profile。
6. 小 batch trainer profile，至少完成一个 global step。
7. valid sample refill / resample profile。
8. DataProto padding profile。
9. SGLang 或 vLLM inference profile。
10. tokenizer / Ray worker / system resource profile。
11. 生成 `stage12_5_acceptance_summary.json`。

远端验收必须明确：

- 哪些指标是真实后端提供。
- 哪些指标当前后端不支持，并写 diagnostics。
- 有多少样本 valid。
- 有多少样本被过滤，原因是什么。
- 是否发生 refill / resample。
- warm cache 命中率是多少。
- 是否完成 trainer global step。
- GPU、Ray、推理服务、RepoHarness runtime 中主要瓶颈在哪里。

## 4. 测试矩阵

### 4.1 新增测试

建议新增：

```text
tests/unit/test_repo_harness_rl_stage12_5_acceptance_contract.py
tests/unit/test_repo_harness_rl_stage12_5_baseline_profile.py
tests/unit/test_repo_harness_rl_stage12_5_dependency_environment.py
tests/unit/test_repo_harness_rl_stage12_5_command_environment.py
tests/unit/test_repo_harness_rl_stage12_5_executor_limits.py
tests/unit/test_repo_harness_rl_stage12_5_workspace_cache.py
tests/unit/test_workspace_reuse_stage12_5_fast_materialization.py
tests/unit/test_repo_harness_rl_stage12_5_verifier_pool_default.py
tests/unit/test_repo_harness_rl_stage12_5_recorder_hot_path.py
tests/unit/test_repo_harness_rl_stage12_5_tool_timing.py
tests/unit/test_repo_harness_verl_stage12_5_inference_profile.py
tests/unit/test_repo_harness_verl_stage12_5_tokenization_profile.py
tests/unit/test_repo_harness_verl_stage12_5_ray_worker_resources.py
tests/unit/test_repo_harness_verl_stage12_5_batch_refill.py
tests/unit/test_repo_harness_verl_stage12_5_dataproto_padding.py
  tests/unit/test_repo_harness_rl_stage12_5_formal_batch_gate.py
tests/unit/test_repo_harness_verl_stage12_5_transferqueue_visibility.py
```

测试数量可以根据实际实现合并，但覆盖面不能减少。

### 4.2 前置阶段回归

Stage 12.5 会触碰 runtime、workspace、verifier、recorder、training view、verl adapter 和 DataProto，因此最终本地回归必须至少包含：

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
  tests/unit/test_verifier_worker_pool_stage7.py \
  tests/unit/test_repo_harness_rl_stage7_reward_boundary.py \
  tests/unit/test_repo_harness_rl_stage8_budget_policy.py \
  tests/unit/test_agent_loop_stage8_no_progress_stop.py \
  tests/unit/test_context_stage8_training_slimming.py \
  tests/unit/test_repo_harness_rl_stage9_resource_leases.py \
  tests/unit/test_repo_harness_rl_stage9_concurrency_runtime.py \
  tests/unit/test_repo_harness_verl_stage10_agent_loop_output.py \
  tests/unit/test_repo_harness_verl_stage10_dataproto_shapes.py \
  tests/unit/test_repo_harness_verl_stage10_postprocess_visibility.py \
  tests/unit/test_repo_harness_verl_stage11_request_mapping.py \
  tests/unit/test_repo_harness_verl_stage11_agent_loop.py \
  tests/unit/test_repo_harness_verl_stage11_gateway.py \
  tests/unit/test_repo_harness_rl_stage11_5_real_episode_runtime.py \
  tests/unit/test_repo_harness_verl_stage12a_local_preflight.py \
  tests/unit/test_repo_harness_verl_stage12b_tool_parser.py \
  tests/integration/test_repo_harness_verl_stage12a_real_episode_smoke.py \
  tests/integration/test_repo_harness_verl_stage12a_visibility_dataproto.py \
  tests/integration/test_repo_harness_verl_stage12a_concurrency.py \
  tests/integration/test_v3_acceptance_stage12.py
```

如果某个测试文件在实际仓库中名称不同，实施 agent 必须先用 `rg --files tests | rg <stage>` 确认实际文件名，不得在验收命令里保留不存在的路径。

### 4.3 Recorder / export / workspace 回归

```bash
PYTHONPATH=src uv run --extra dev python -m pytest -q \
  tests/unit/test_run_recorder.py \
  tests/unit/test_provider_artifact_binding.py \
  tests/unit/test_export.py \
  tests/integration/test_export_from_run.py \
  tests/integration/test_v3_export_audit.py
```

### 4.4 Import 和 verl 依赖边界

普通导入不能要求 `torch`、`ray`、`tensordict` 或 `reference/verl`：

```bash
PYTHONPATH=src uv run --extra dev python - <<'PY'
import repo_harness.rl
import repo_harness_verl
print("ordinary_import_ok")
PY
```

RepoHarness core 不能直接 import `verl`：

```bash
if rg -n '(^|\s)(import|from)\s+verl' \
  src/repo_harness/rl \
  src/repo_harness/agent_loop \
  src/repo_harness/workspace \
  src/repo_harness/verifier
then
  exit 1
fi
```

## 5. 远端执行建议

远端 Stage 12.5 不应该直接使用 Stage 12 的“正确性 smoke”脚本原样结束，而要生成吞吐 evidence。

推荐远端命令结构：

```bash
git fetch origin
git checkout <stage12_5_branch_or_commit>
PYTHONPATH=src:reference/verl uv run --extra dev python -m compileall -q src

# 依赖、模型和 verl import preflight
PYTHONPATH=src:reference/verl uv run --extra dev python scripts/stage12_5/preflight.py

# 冷缓存和热缓存 real episode profile
PYTHONPATH=src:reference/verl uv run --extra dev python scripts/stage12_5/run_real_episode_cache_profile.py

# 并发 episode profile
PYTHONPATH=src:reference/verl uv run --extra dev python scripts/stage12_5/run_concurrent_episode_profile.py

# 小 batch trainer throughput profile
PYTHONPATH=src:reference/verl uv run --extra dev python scripts/stage12_5/run_trainer_throughput_profile.py

# 汇总 acceptance
PYTHONPATH=src:reference/verl uv run --extra dev python scripts/stage12_5/build_acceptance_summary.py
```

具体脚本文件名可以在实施时调整，但必须保留相同的 evidence 输出和命令日志。

远端运行完成后：

- 将 evidence 写入 `runs/stage12_5-throughput-<timestamp>/`。
- 提交可复现脚本、测试和必要的小型 evidence summary。
- 大型日志或模型缓存不要提交到 Git。
- 如果需要保存完整远端 evidence，可以压缩后下载到本地 `runs/`，或使用已有远端同步流程。

## 6. 完成定义

Stage 12.5 只有在下面条件全部满足时才算完成：

- 本地 dependency environment cache、workspace shared cache、verifier pool、recorder hot path、tool timing、batch refill、DataProto padding 和 visibility 测试通过。
- Stage 0H 到 Stage 12 关键回归通过。
- 普通 import 不引入 heavy `verl` 依赖。
- RepoHarness core 没有直接 import `verl`。
- 远端 GPU evidence 证明 cold cache / warm cache / concurrent episode / trainer profile 可运行。
- 远端 evidence 中没有本机绝对 dependency environment path 或 workspace path 进入可传播 batch 字段。
- full trainer 小步 profile 至少完成一个 global step，并记录 valid sample 数、invalid sample 过滤、GPU / Ray / SGLang 或 vLLM 指标。
- `stage12_5_acceptance_summary.json` 明确标出通过项、未支持指标、已知风险和是否允许进入 Stage 13。

如果某个吞吐优化没有完成，但证据已经能定位瓶颈，必须在 acceptance summary 中写成 `pending_with_diagnostics`，不能写成 `passed`。

## 7. 不进入 Stage 12.5 的事项

下面事项不要在 Stage 12.5 中提前实现：

- fully async AgentLoop。
- async reward backfill。
- 多版本 policy trajectory reconciliation。
- 大规模 SWE-Bench 训练。
- 分布式 cache service。
- 远端跨机器 workspace lease 协议。
- 自动调参系统。
- 为了吞吐绕过 formal batch validator 或 visibility gate。
