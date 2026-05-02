# V3 Stage 02 Docker Backend Factory And Base Facts

## 目标

阶段 2 的目标是引入可执行 Docker workspace backend 的基础能力：新增 backend factory、保留 local backend、增加独立 `DockerWorkspaceAdapter`，让 runner、tools、verifier 和 context builder 依赖 workspace protocol / facade，而不是依赖 `LocalWorkspaceAdapter` 具体类型。本阶段只实现 Docker 生命周期和基础 facts，不提前实现阶段 3 的完整 phase coverage matrix、verifier patch / test patch replay 或 SWE-Bench-like final verifier。

## 实现内容

新增 `DockerWorkspaceAdapter`。当前实现采用受边界约束的 run directory bind mount：源码、artifact 和 run metadata 仍落在 host run directory；命令执行全部通过 `docker run --rm` 进入容器。每次容器执行记录 command id、container id、image id、requested platform、container `uname -m`、command、workdir、exit code、timeout、duration、network policy、mount policy 和 cleanup status。

新增 `workspace.backend_factory.create_workspace_adapter`，由 `RunConfig.runtime.execution_mode` 选择 local 或 Docker backend。Docker 初始化失败被包装为 `DockerBackendInitializationError`，runner 会持久化 `docker_backend_status.json` 和兼容的 `docker_stage_status.json`，然后重新抛出 `WorkspaceError`，不会静默回退到 `local_process`。

扩展 workspace protocol，显式覆盖当前实际调用面：`run_command`、`read_text`、`write_text`、`list_files`、`resolve_workspace_path`、`apply_patch`、`capture_final_patch`、`create_source_checkout`、`create_setup_workspace`、`capture_dependency_state`、`create_agent_workspace`、`create_verification_workspace`、`restore_dependency_state` 和 `cleanup_workspaces`。

Runner、tools、verifier 和 context builder 改造如下：

- `evaluation.runner.run_task` 通过 backend factory 创建 adapter，不再硬编码 `LocalWorkspaceAdapter`。
- `ToolExecutionContext` 使用 `WorkspaceAdapter` protocol。
- `PytestVerifier` 使用 `WorkspaceAdapter` protocol。
- `ToolExecutor` 的 `list_files` 和 `grep` 通过 workspace facade 读文件和列文件。
- `ContextBuilder` 在 Docker mode 下必须通过 workspace facade 读取 repository context；没有 facade 时不会用裸宿主机 `Path.read_text()` 读取 container path。
- `build_local_environment_fingerprint` 支持记录 Docker backend execution facts，Docker run 的 `run_config_facts.json` 中 workspace backend 为 `docker`。

扩展 `inspect-workspace-backend`。`--assert-docker-backend` 现在不仅检查 summary 字段，还会重新读取 `docker_backend_facts_ref` 和 `container_execution_facts_refs`，并校验 evidence 文件存在、JSON schema、container architecture、cleanup status、image id、image platform 和 requested platform 与 status 一致。它会拒绝 Docker VM 内存低于 16 GiB、`evaluation.concurrency != 1`、effective SWE workers != 1、container architecture 缺失、cleanup status 缺失或非 completed、evidence ref 缺失或 evidence schema 错误。

## 主要修改文件

- `src/repo_harness/workspace/docker_adapter.py`
- `src/repo_harness/workspace/backend_factory.py`
- `src/repo_harness/workspace/backend_status.py`
- `src/repo_harness/workspace/protocol.py`
- `src/repo_harness/workspace/adapter.py`
- `src/repo_harness/workspace/schemas.py`
- `src/repo_harness/workspace/__init__.py`
- `src/repo_harness/evaluation/runner.py`
- `src/repo_harness/context/builder.py`
- `src/repo_harness/tools/minimal.py`
- `src/repo_harness/verifier/runner.py`
- `src/repo_harness/run_metadata/fingerprint.py`
- `src/repo_harness/config/schemas.py`
- `tests/unit/test_workspace_backend.py`
- `tests/unit/test_context_builder.py`
- `tests/unit/test_experiment_config.py`
- `tests/integration/test_docker_mode_rejected.py`
- `tests/integration/test_eval_runner_quality_gate.py`
- `tests/integration/test_docker_backend_e2e.py`
- `tests/fixtures/run_configs/v3/docker_experiment_smoke.yaml`
- `tests/fixtures/run_configs/v3/docker_run_task_smoke.yaml`
- `docs/v3/implementation-log/02-stage-02-docker-backend-factory.md`
- `docs/v3/review/implementation/stage-02-review.md`

## 机器产物

正式阶段 smoke run：

- `runs/v3-stage-02-docker-smoke-20260502T155725Z/v3-stage-02-docker-smoke/`

关键机器产物：

- `runs/v3-stage-02-docker-smoke-20260502T155725Z/v3-stage-02-docker-smoke/docker_backend_facts.json`
- `runs/v3-stage-02-docker-smoke-20260502T155725Z/v3-stage-02-docker-smoke/docker_backend_status.json`
- `runs/v3-stage-02-docker-smoke-20260502T155725Z/v3-stage-02-docker-smoke/docker_stage_status.json`
- `runs/v3-stage-02-docker-smoke-20260502T155725Z/v3-stage-02-docker-smoke/container_execution_facts/*.json`
- `runs/v3-stage-02-docker-smoke-20260502T155725Z/v3-stage-02-docker-smoke/run_config_facts.json`
- `runs/v3-stage-02-docker-smoke-20260502T155725Z/v3-stage-02-docker-smoke/run_metadata.json`
- `runs/v3-stage-02-docker-smoke-20260502T155725Z/v3-stage-02-docker-smoke/final.patch`
- `runs/v3-stage-02-docker-smoke-20260502T155725Z/v3-stage-02-docker-smoke/final.diff`

Docker status 中记录的关键事实：

- `docker_context`: `desktop-linux`
- `docker_server_platform`: `linux`
- `docker_server_architecture`: `arm64`
- `docker_mem_total_bytes`: `33598365696`
- `requested_container_platform`: `linux/arm64`
- `container_uname_m`: `aarch64`
- `image_platform`: `linux/arm64`
- `network_policy`: `deny_agent_run`
- `mount_policy`: `workspace_read_write_tmp_only`
- `cleanup_status`: `completed`
- `evaluation_concurrency`: `1`
- `swebench_like_effective_max_workers`: `1`
- container execution facts refs: `36`

## 验证命令和结果

- `PATH=.venv/bin:$PATH python -m pytest tests/unit/test_workspace_backend.py tests/unit/test_context_builder.py tests/unit/test_tools.py tests/unit/test_experiment_config.py tests/unit/test_config_schema.py tests/integration/test_docker_mode_rejected.py tests/integration/test_docker_backend_e2e.py -q`：`38 passed`。
- `PATH=.venv/bin:$PATH repo-harness run-task tests/fixtures/tasks/task_001.yaml --config tests/fixtures/run_configs/v3/docker_run_task_smoke.yaml --output-dir runs/v3-stage-02-docker-smoke-20260502T155725Z --run-id v3-stage-02-docker-smoke`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-workspace-backend --status-file runs/v3-stage-02-docker-smoke-20260502T155725Z/v3-stage-02-docker-smoke/docker_backend_status.json --assert-docker-backend`：通过，返回 `docker_backend=passed`。
- `PATH=.venv/bin:$PATH repo-harness inspect-workspace-backend --status-file runs/v3-stage-02-docker-smoke-20260502T155725Z/v3-stage-02-docker-smoke/docker_stage_status.json --assert-docker-backend`：通过，返回 `docker_backend=passed`。
- `PATH=.venv/bin:$PATH repo-harness inspect-run runs/v3-stage-02-docker-smoke-20260502T155725Z/v3-stage-02-docker-smoke`：通过，run outcome 为 `success`，final verifier status 为 `accepted`。
- Prepared messages host path probe：未发现 `/Users/`、`/private/`、`/var/folders/` 或 `/tmp/` 宿主路径。
- `PATH=.venv/bin:$PATH python -m compileall src`：通过。
- `PATH=.venv/bin:$PATH python -m pytest -q`：`401 passed in 145.49s`。
- `PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-v3-swebench-fixture --fixture-dir tests/fixtures/v3/swebench_lite_fixed --evidence-dir docs/v3/evidence/swebench-lite-fixed --manifest tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/v3_feasibility_input_manifest.json --assert-frozen`：通过。

## 正例证据

- Docker replay smoke 在 Docker backend 下完成基础 workspace lifecycle、agent tool execution、`run_tests`、final patch freeze、verification workspace 和 final verifier。
- `docker_backend_status.json` 和兼容的 `docker_stage_status.json` 都能通过 `inspect-workspace-backend --assert-docker-backend`。
- Docker smoke 的 `run_config_facts.json` 记录 `workspace_backend.backend = docker`。
- `docker_backend_status.json` 记录 Docker context、server platform、server architecture、Docker VM memory、requested container platform、container uname、image id、image platform、build mode、network policy、mount policy、timeout、cleanup policy、cleanup status、evaluation concurrency 和 effective SWE workers。
- `container_execution_facts/` 下有逐命令 facts 文件，inspect 会重新读取这些 evidence refs。
- Docker mode context builder 测试证明 repository context 通过 workspace facade 读取，不使用裸宿主机 `Path.read_text()` 读取 container path。
- V2 interface-only inspect 入口仍保留，V2 acceptance 回归通过。

## 负例证据

单元和集成测试覆盖以下拒绝场景：

- Docker backend status 缺少必需 summary fields 时失败。
- `--assert-docker-backend` 在 status 不是 passed 时失败。
- Docker VM memory 低于 16 GiB 时失败。
- `evaluation.concurrency != 1` 时失败。
- effective SWE workers != 1 时失败。
- status 缺少 `container_uname_m` 时失败。
- container execution facts 中 `container_uname_m` 为空时失败。
- container execution facts 中 `cleanup_status != completed` 时失败。
- `docker_backend_facts_ref.image_platform` 与 status 不一致时失败。
- container execution facts 的 image id 或 requested platform 与 status 不一致时失败。
- evidence ref 缺失或越界会失败。
- Docker image missing 且 `build_if_missing=false` 时，runner 写入 `docker_backend_status.json` 和 `docker_stage_status.json`，不创建 agent workspace，不生成 metrics，不静默回退到 local process。

## 允许降级项

本阶段允许仅证明 Docker backend factory、基础 workspace lifecycle、container execution facts 和 replay smoke，不要求完成阶段 3 的 `docker_phase_coverage_matrix.json` 或 SWE-Bench-like fail-to-pass / pass-to-pass final verifier。

本阶段使用 run directory bind mount 模式，不声明生产级安全沙箱。

## 禁止降级项

- 不允许 Docker mode 静默回退到 `local_process`。
- 不允许 Docker 不可用、镜像缺失或初始化失败时只抛异常而不持久化结构化 status。
- 不允许 `inspect-workspace-backend --assert-docker-backend` 只信 summary 字段，不重读 evidence refs。
- 不允许内存低于 16 GiB、并发大于 1、effective SWE workers 大于 1、container architecture 缺失、cleanup status 缺失或 evidence schema 错误被标记为通过。
- 不允许把 V2 `interface_only` 路径当成 V3 Docker backend 通过。
- 不允许提交工作树中与阶段 2 无关的既有文档删除、`.vscode`、`docs/build-your-own`、`docs/resume`、`docs/v1` 或 `uv.lock`。

## 已知限制

阶段 2 的 Docker backend 已能执行 replay smoke，但 phase coverage 还不是阶段 3 要求的完整矩阵。`source_checkout` 和 copy lifecycle 仍在 host run directory 上完成，命令执行在容器中完成；阶段 3 会继续扩展 command/file/patch/verifier workspace 的逐 phase coverage 和严格检查。

当前 Docker image 是本地构建的 `repo-harness-v3-python:stage2`，用于轻量 Python/pytest/git smoke。真实仓库任务、SWE-Bench-like adapter 和固定 source materialization 仍属于阶段 4 到阶段 6。

## 设计偏离

没有偏离阶段 2 范围。为避免过早扩大范围，本阶段没有实现 `docker_phase_coverage_matrix.json`，也没有声明完整 repository-level task set 或 SWE-Bench-like final verifier。

## 审查结论

只读子代理第一轮发现 3 个 P2 和 1 个 P3：

- P2：Docker 初始化失败没有持久化结构化 status。
- P2：inspect 对 evidence 内部 container architecture 和 cleanup status 约束不够强。
- P2：工作树存在无关既有文档和配置改动，不能进入 Stage 2 commit。
- P3：未跟踪文档中存在生产级安全沙箱表述，如果提交会冲突。

修复后第二轮发现 1 个 P2：`docker_backend_facts_ref.image_platform` 与 status 不一致时 inspect 仍可通过。已补充一致性校验和负例测试。

最终只读子代理复核结论：P1 无，P2 无，P3 无新的 Stage 2 阻断问题，允许进入阶段 3。提交前必须只 stage Stage 2 相关文件。
