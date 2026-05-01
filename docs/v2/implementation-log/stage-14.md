# Stage 14: finalize workspace backend path

## 本阶段目标

本阶段目标是在前面已经落地的 Workspace Adapter 协议、source materialization、本地执行环境事实和任务集验收基础上，完成 Docker execution mode 扩展路径的可审计收口。

本阶段选择 `interface_only` 完成方式，也就是：

- 不实现 `DockerWorkspaceAdapter`。
- 不声称 Docker backend 已经可用。
- 保留 `runtime.execution_mode = "docker"` 的清晰拒绝错误。
- 确认拒绝发生在 workspace 创建之前，不会静默降级到 `local_process`。
- 生成 `docker_stage_status.json`，并用 `inspect-workspace-backend --assert-stage-complete` 做机器检查。

本阶段不做：

- 不实现 Docker 后端端到端执行。
- 不实现远程容器平台。
- 不实现生产级安全沙箱、沙箱逃逸防护或操作系统级断网证明。

## 本阶段实现内容

- 新增 `workspace.backend_status`：
  - `DockerStageStatus`
  - `WorkspaceBackendTestStatus`
  - `build_workspace_backend_status`
  - `write_workspace_backend_status`
  - `inspect_workspace_backend_status`
  - `load_workspace_backend_status`
  - `detect_docker_availability`
- 新增 CLI：
  - `repo-harness workspace-backend-status --output <docker_stage_status.json> --mode interface-only`
  - `repo-harness workspace-backend-status --output <docker_stage_status.json> --mode docker-backend`
  - `repo-harness inspect-workspace-backend --status-file <docker_stage_status.json> --assert-interface-only`
  - `repo-harness inspect-workspace-backend --status-file <docker_stage_status.json> --assert-docker-backend`
  - `repo-harness inspect-workspace-backend --status-file <docker_stage_status.json> --assert-stage-complete`
- 固定 CLI 枚举映射：
  - `--mode interface-only` 写入 JSON `mode = "interface_only"`。
  - `--mode docker-backend` 写入 JSON `mode = "docker_backend"`。
- `--assert-stage-complete` 当前可接受：
  - `mode = "interface_only"`
  - `status = "passed"`
  - `docker_execution_mode_behavior = "clearly_rejected"`
  - `local_process_mode_regression = "passed"`
  - `production_sandbox_claimed = false`
  - `workspace_backend_protocol`、`local_process_workspace_lifecycle` 和 `docker_mode_rejected` 测试证据均为 `passed`
- `--assert-stage-complete` 会拒绝：
  - `status != "passed"`。
  - `mode = "docker_backend"` 但 Docker 后端测试未通过。
  - `mode = "docker_backend"` 但 Docker 不可用。
  - 声称 Docker execution mode 是生产级安全沙箱。
  - interface-only 状态缺少 Docker 拒绝测试证据。
- 将 `WorkspaceAdapter` 标记为 `@runtime_checkable`，用于 Stage 14 协议收口测试。
- 让 `WorkspaceBackendError` 继承 `RepoHarnessError`，使 CLI 可以用统一错误路径返回失败。
- 更新 `run_task` 的 Docker 模式错误信息：
  - 明确说明 `runtime.execution_mode=docker` 是为 Docker-based executable repository environment 保留的后端接口。
  - 明确说明当前 Stage 14 是 `interface_only`。
  - 明确说明不会静默降级为 `execution_mode=local_process`。
- 新增测试：
  - `tests/unit/test_workspace_backend.py`
  - `tests/integration/test_docker_mode_rejected.py`

## 修改的主要文件

- `src/repo_harness/workspace/backend_status.py`
- `src/repo_harness/workspace/protocol.py`
- `src/repo_harness/workspace/__init__.py`
- `src/repo_harness/evaluation/runner.py`
- `src/repo_harness/cli/main.py`
- `tests/unit/test_workspace_backend.py`
- `tests/integration/test_docker_mode_rejected.py`

## 生成的机器可读产物

Stage 14 Docker stage status：

- `runs/v2-docker-stage-20260501T222345Z/docker_stage_status.json`

关键字段：

- `schema_version = "repo_harness_docker_stage_status_v2_v0"`
- `stage = 14`
- `mode = "interface_only"`
- `status = "passed"`
- `docker_available = true`
- `docker_available_reason = "docker_server_responded"`
- `docker_execution_mode_behavior = "clearly_rejected"`
- `docker_backend_implemented = false`
- `docker_execution_mode_description = "Docker-based executable repository environment"`
- `local_process_mode_regression = "passed"`
- `production_sandbox_claimed = false`
- `workspace_adapter_protocol_reviewed = true`
- `local_workspace_adapter_backend = "local_process"`

## 运行的验证命令

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_workspace_backend.py -q
PATH=.venv/bin:$PATH python -m pytest tests/integration/test_docker_mode_rejected.py -q
PATH=.venv/bin:$PATH python -m pytest tests/integration/test_workspace_lifecycle.py -q
PATH=.venv/bin:$PATH python -m pytest tests/integration/test_eval_runner_quality_gate.py::test_docker_execution_mode_is_rejected_in_v1 -q
PATH=.venv/bin:$PATH python -m compileall src

RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)
DOCKER_STATUS_DIR="runs/v2-docker-stage-$RUN_ID"
DOCKER_STATUS_FILE="$DOCKER_STATUS_DIR/docker_stage_status.json"
mkdir -p "$DOCKER_STATUS_DIR"
PATH=.venv/bin:$PATH repo-harness workspace-backend-status \
  --output "$DOCKER_STATUS_FILE" \
  --mode interface-only
PATH=.venv/bin:$PATH repo-harness inspect-workspace-backend \
  --status-file "$DOCKER_STATUS_FILE" \
  --assert-interface-only
PATH=.venv/bin:$PATH repo-harness inspect-workspace-backend \
  --status-file "$DOCKER_STATUS_FILE" \
  --assert-stage-complete
```

提交前还会运行：

```bash
PATH=.venv/bin:$PATH python -m pytest -q
git status --short
git diff --check
git diff --cached --check
```

## 验证结果

- `tests/unit/test_workspace_backend.py` 通过，8 个测试通过。
- `tests/integration/test_docker_mode_rejected.py` 通过，1 个测试通过。
- `tests/integration/test_workspace_lifecycle.py` 通过，8 个测试通过。
- `test_docker_execution_mode_is_rejected_in_v1` 回归测试通过。
- `python -m compileall src` 通过。
- `workspace-backend-status --mode interface-only` 成功生成 `docker_stage_status.json`。
- `inspect-workspace-backend --assert-interface-only` 通过。
- `inspect-workspace-backend --assert-stage-complete` 通过。
- 全量测试通过，344 个测试通过。

## 正例证据

- `runtime.execution_mode=docker` 在 `run_task` 开始阶段被拒绝，拒绝发生在 `load_task` 和 workspace 创建之前。
- Docker 模式拒绝后不会创建 run directory，不会落入 `LocalWorkspaceAdapter`。
- `LocalWorkspaceAdapter.backend == WorkspaceBackend.local_process`。
- `isinstance(LocalWorkspaceAdapter(...), WorkspaceAdapter)` 通过，证明现有本地适配器满足 Stage 01 已定义的协议。
- `docker_stage_status.json` 明确记录 `mode = "interface_only"`，没有把配置可加载写成 Docker backend 已实现。
- `docker_backend` 模式生成的状态为 `failed`，`--assert-docker-backend` 和 `--assert-stage-complete` 不会接受它。
- 伪造的 `mode = "docker_backend"`、`status = "passed"` 和 `docker_backend_end_to_end = "passed"` 状态会被拒绝，因为当前构建没有实现 Docker backend。
- 缺少 `schema_version` 或 `workspace_backend_version` 等关键字段的状态文件会被拒绝，不会被 Pydantic 默认值静默补齐。
- `production_sandbox_claimed = true` 会被检查器拒绝。
- interface-only 状态缺少或未通过 `docker_mode_rejected` 证据时会被检查器拒绝。

## 负例证据

- 本阶段没有新增 `DockerWorkspaceAdapter`。
- 本阶段没有创建 Docker container execution context。
- 本阶段没有把 Docker execution mode 写成生产级安全沙箱。
- 本阶段没有改变 local process workspace lifecycle、final patch freeze 或 strict patch replay 路径。
- 本阶段没有改动 provider、export、task set 或 scaffold 行为。

## 允许降级项

- 第二版 Stage 14 当前选择 `interface_only`，因此 Docker 后端端到端执行是未实现项，但这是 `docs/v2/implementation-plan.md` 明确允许的完成方式。
- 本机 Docker 可用只记录为环境事实，不因此声称 Docker backend 已经完成。

## 禁止降级项

- 不能把 `runtime.execution_mode=docker` 静默回退到 `local_process`。
- 不能把 `mode = "docker_backend"` 且 `status = "failed"` 或 Docker 不可用的状态当作通过。
- 不能把 `docker_stage_status.json` 中的配置预留字段解释为 Docker 后端已实现。
- 不能声称 Docker execution mode 是生产级安全沙箱、沙箱逃逸防护或完整网络隔离。

## 已知限制

- 当前没有 Docker 后端端到端能力；后续如选择实现，必须新增独立 `DockerWorkspaceAdapter` 或等价 backend，并真实使用 container execution context。当前检查器会拒绝任何 `docker_backend` 通过声明。
- 当前 `workspace-backend-status` 不运行 pytest，它记录的是按阶段验收流程已经运行的命令证据。阶段验收必须先运行测试命令，再生成 status 文件。
- 当前 Docker 可用性检测只用于状态记录；在 `interface_only` 模式下，Docker 可用或不可用都不改变拒绝逻辑。

## 是否偏离设计文档

未发现需要记录的设计冲突。本阶段选择 `docs/v2/implementation-plan.md` 明确允许的 `interface_only` 路径，没有提前实现 Docker backend，也没有把 Docker execution mode 夸大为生产级安全沙箱。

## sub agent 审查结论

已安排只读 sub agent 审查。审查 agent 没有修改文件。

审查发现：

- P1：未发现。
- P2：发现 2 个，均已修复。
  - `inspect-workspace-backend --assert-stage-complete` 初始实现对伪造的 `docker_backend` 通过状态过度信任。修复后，当前构建会拒绝任何 `docker_backend` 通过声明，除非后续真正实现 Docker backend 并更新检查器为带容器执行证据的验收路径。
  - `docker_stage_status.json` 初始 schema 对部分关键字段使用默认值，导致缺字段可能被补齐。修复后，加载 status 文件时会先检查原始 JSON 必须显式包含关键字段。
- P3：`workspace-backend-status` 记录的是阶段验收命令证据，不直接运行 pytest。此项记录为后续改进，不阻断当前阶段，因为阶段日志和验收流程已经明确要求先运行测试命令再生成 status 文件。

审查记录保存到 `docs/v2/review/implementation/stage-14-review.md`。

## 是否可以进入下一阶段

可以进入 Stage 15。进入下一阶段前，Stage 14 commit 必须只包含当前阶段相关代码、测试、阶段日志和审查记录。
