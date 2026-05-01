# Stage 14 只读审查记录

## 审查方式

本阶段安排了只读 sub agent 审查。审查 agent 没有修改文件。主流程根据审查结论修复了 P2 问题，并重新运行相关验证。

## 审查重点

- 是否严格符合 `docs/v2/implementation-plan.md` Stage 14 和 `docs/v2/scope-and-roadmap.md` 的边界。
- 是否继续清晰拒绝 `runtime.execution_mode=docker`，且没有静默 fallback 到 `local_process`。
- `inspect-workspace-backend --assert-stage-complete` 是否会接受合格 `interface_only` 状态，并拒绝失败状态、缺字段、伪造 Docker backend 和生产级安全沙箱声明。
- `LocalWorkspaceAdapter` 是否仍明确是 `local_process` backend，没有混入 Docker 逻辑。
- 是否破坏第一版 replay-only 路径、run metadata、export、provider 或 Stage 13 task set。
- 是否缺少 Stage 14 验收测试或机器产物证据。

## 审查发现

### P1

未发现 P1。

### P2

1. `docker_backend` 验收可以被伪造的状态文件骗过。
   - 风险：伪造 `mode=docker_backend`、`status=passed`、`docker_available=true`、`docker_execution_mode_behavior=docker_backend_active` 和 `docker_backend_end_to_end=passed` 时，初始检查器会返回 `stage_complete=passed`。
   - 处理：已修复。当前构建没有实现 Docker backend，因此 `_assert_docker_backend()` 会拒绝任何 `docker_backend` 通过声明。后续如果真正实现 Docker backend，必须新增容器执行证据字段和交叉验证逻辑。

2. 状态 schema 对部分关键字段使用默认值，导致缺字段可能被补齐后通过。
   - 风险：缺少 `schema_version` 或 `workspace_backend_version` 等关键字段的 interface-only 状态文件可能被默认值补齐。
   - 处理：已修复。`load_workspace_backend_status()` 会先检查原始 JSON 是否显式包含关键字段，再做 Pydantic 校验。

### P3

1. `workspace-backend-status` 生成的测试证据字段是阶段流程证据，不直接读取 pytest 退出码。
   - 处理：记录为后续改进。当前阶段日志已经明确要求先运行测试命令，再生成 `docker_stage_status.json`。

2. 工作区存在大量与 Stage 14 无关的既有文档迁移和删除。
   - 处理：提交时只 stage 当前阶段相关文件，不纳入无关既有改动。

## 审查正例证据

- Stage 14 选择 `interface_only` 模式，符合 `docs/v2/implementation-plan.md` 允许的完成方式。
- `runtime.execution_mode=docker` 在 `run_task` 早期被清晰拒绝，错误信息明确说明不会静默降级为 `execution_mode=local_process`。
- `tests/integration/test_docker_mode_rejected.py` 断言 Docker 模式被拒绝后不会创建 run directory。
- `LocalWorkspaceAdapter.backend == WorkspaceBackend.local_process`。
- `RunWorkspace.execution_mode` 仍写为 `local_process`。
- `workspace-backend-status` 和 `inspect-workspace-backend` 命令覆盖计划要求。
- `runs/v2-docker-stage-20260501T222345Z/docker_stage_status.json` 记录：
  - `mode = "interface_only"`
  - `status = "passed"`
  - `docker_execution_mode_behavior = "clearly_rejected"`
  - `docker_backend_implemented = false`
  - `production_sandbox_claimed = false`
  - `docker_backend_end_to_end = "not_applicable"`

## 审查负例证据

- 没有新增 `DockerWorkspaceAdapter`。
- 没有真实创建 Docker container execution context。
- 没有把 Docker execution mode 声称为生产级安全沙箱。
- 伪造 `docker_backend` 通过状态会被拒绝。
- 缺少关键字段的 status 文件会被拒绝。

## 修复后验证

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_workspace_backend.py tests/integration/test_docker_mode_rejected.py tests/integration/test_workspace_lifecycle.py -q
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH repo-harness workspace-backend-status --output runs/v2-docker-stage-20260501T222345Z/docker_stage_status.json --mode interface-only
PATH=.venv/bin:$PATH repo-harness inspect-workspace-backend --status-file runs/v2-docker-stage-20260501T222345Z/docker_stage_status.json --assert-interface-only
PATH=.venv/bin:$PATH repo-harness inspect-workspace-backend --status-file runs/v2-docker-stage-20260501T222345Z/docker_stage_status.json --assert-stage-complete
```

验证结果：

- Stage 14 相关测试通过，17 个测试通过。
- `python -m compileall src` 通过。
- `inspect-workspace-backend --assert-interface-only` 通过。
- `inspect-workspace-backend --assert-stage-complete` 通过。

## 结论

Stage 14 的 `interface_only` 完成路径没有剩余 P1 或 P2。Docker backend 没有实现，且没有被伪装成已实现。Stage 14 可以进入 Stage 15。
