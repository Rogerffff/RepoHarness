# V3 Stage 02 Implementation Review

## 审查范围

本审查覆盖阶段 2 的 Docker backend factory 和基础 facts：

- `DockerWorkspaceAdapter`
- `create_workspace_adapter` backend factory
- workspace protocol / facade 扩展
- local backend 兼容
- `docker_backend_status.json` 和兼容 `docker_stage_status.json`
- `DockerBackendFacts` 和 `ContainerExecutionFacts`
- runner、tools、verifier、context builder 对 `WorkspaceAdapter` protocol 的接入
- Docker mode 初始化失败结构化 status
- Docker replay smoke run
- 相关单元测试和集成测试

本审查不覆盖阶段 3 的完整 Docker command/file/patch coverage matrix，不覆盖阶段 4 之后的 task adapter、source materialization 或 SWE-Bench-like final verifier。

## 审查命令

只读子代理和本地自审使用了以下命令：

- `git status --short`
- `git diff --stat`
- `git diff --name-only`
- `git diff -- src/repo_harness/... tests/...`
- `PATH=.venv/bin:$PATH pytest tests/unit/test_workspace_backend.py tests/unit/test_context_builder.py tests/unit/test_experiment_config.py tests/integration/test_docker_mode_rejected.py -q`
- `PATH=.venv/bin:$PATH pytest tests/integration/test_docker_backend_e2e.py -q`
- `PATH=.venv/bin:$PATH pytest tests/unit/test_workspace_backend.py tests/integration/test_docker_mode_rejected.py tests/integration/test_eval_runner_quality_gate.py::test_docker_execution_mode_missing_image_fails_without_local_fallback -q`
- `PATH=.venv/bin:$PATH repo-harness inspect-workspace-backend --status-file runs/v3-stage-02-docker-smoke-20260502T155725Z/v3-stage-02-docker-smoke/docker_backend_status.json --assert-docker-backend`
- `PATH=.venv/bin:$PATH repo-harness inspect-workspace-backend --status-file runs/v3-stage-02-docker-smoke-20260502T155725Z/v3-stage-02-docker-smoke/docker_stage_status.json --assert-docker-backend`
- host path probe over Docker smoke prepared messages.
- 临时伪造 evidence，验证 inspect 对 container architecture、cleanup status、image id、image platform、requested platform 和 evidence ref 缺失的拒绝。

最终提交前验证：

- `PATH=.venv/bin:$PATH python -m compileall src`
- `PATH=.venv/bin:$PATH python -m pytest -q`
- `PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete`
- `PATH=.venv/bin:$PATH repo-harness inspect-v3-swebench-fixture --fixture-dir tests/fixtures/v3/swebench_lite_fixed --evidence-dir docs/v3/evidence/swebench-lite-fixed --manifest tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/v3_feasibility_input_manifest.json --assert-frozen`

## 第一轮发现

### P1

未发现。

### P2

Docker 初始化失败没有持久化结构化状态。`run_task` 只有在 adapter 构造成功后才写 backend status；Docker 不可用或 image missing 且 `build_if_missing=false` 时会抛出，但没有落 `docker_backend_status.json` 或 `docker_stage_status.json`。

修复：backend factory 将 Docker 初始化失败包装为 `DockerBackendInitializationError`；runner 捕获后写入 failed `docker_backend_status.json` 和 `docker_stage_status.json`，记录 structured failure reason，并重新抛出 `WorkspaceError`。测试确认不会创建 agent workspace，也不会生成 metrics。

### P2

Inspect 只校验 evidence schema，不拒绝 container execution facts 中空 `container_uname_m` 或 `cleanup_status=skipped`。

修复：`inspect-workspace-backend --assert-docker-backend` 现在重新读取 `docker_backend_facts_ref` 和每个 `container_execution_facts_ref`，并拒绝空 container architecture、cleanup status 非 completed、image id 不一致、requested platform 不一致和 evidence 缺失。

### P2

当前工作树存在与 Stage 2 无关的既有文档删除、未跟踪文档目录、`.vscode` 和 `uv.lock`。这些不能进入 Stage 2 commit。

处理：记录为既有无关工作区状态，不回滚、不删除、不提交。Stage 2 commit 只 stage Docker backend 相关代码、测试、fixture、run 机器产物和阶段文档。

### P3

未跟踪文档中有生产级安全沙箱表述。如果这些文档进入 Stage 2，会与 V3 当前口径冲突。

处理：该文档不属于 Stage 2 范围，不纳入本阶段 commit。Stage 2 文档只声明 Docker-based executable repository environment，不声明生产级安全沙箱。

## 第二轮发现

### P2

`docker_backend_facts_ref.image_platform` 与 `docker_backend_status.json.image_platform` 不一致时，inspect 仍会通过。

修复：新增 backend facts image platform 与 status 一致性校验，并新增负例测试。最后一轮只读复核用临时伪造 evidence 验证该情况已被拒绝。

## 最终复核

最终只读子代理复核结论：

- P1：无。
- P2：无。
- P3：无新的 Stage 2 阻断问题。
- 允许进入阶段 3。

复核确认：

- Docker unavailable / image missing / `build_if_missing=false` 初始化失败会持久化 `docker_backend_status.json` 和 `docker_stage_status.json`。
- Docker mode 没有静默回退到 local process。
- Inspect 会重新读取 Docker evidence refs，并拒绝空 `container_uname_m`、cleanup 非 completed、image id 不一致、image platform 不一致、requested platform 不一致和 evidence 缺失。
- V2 interface-only status / inspect 入口仍可用。
- Docker smoke prepared messages 未发现 host path 泄露。

## 结论

阶段 2 满足当前 V3 实施计划要求，可以进入阶段 3。阶段 3 必须继续补齐 Docker command、file、patch、verification workspace 和 phase coverage matrix，不得把阶段 2 smoke 误写成完整 Docker verifier phase coverage。
