# V3 Stage 03 Implementation Review

## 审查范围

本审查覆盖阶段 3 的 Docker command、file、patch、verification workspace 和 phase coverage：

- Docker read/write/list file execution。
- Docker patch apply 和 model final patch apply。
- Docker final patch capture。
- Docker verification workspace creation。
- fail-to-pass / pass-to-pass 单测 selector execution facts。
- `container_execution_facts/manifest.json`。
- `docker_phase_coverage_matrix.json`。
- `inspect-workspace-backend --assert-docker-backend` 的 manifest、matrix、facts 交叉校验。

本审查不覆盖阶段 4 task adapter、阶段 5 source materialization 或阶段 6 SWE-Bench-like final verifier。

## 审查命令

只读子代理和本地自审使用了以下命令：

- `git status --short --untracked-files=normal`
- `git diff --stat`
- `git diff --name-status`
- `git diff -- src/repo_harness/... tests/...`
- `rg -n "_record_docker_agent_tool_phase|python.*-c.*pass|command_semantics=\"agent_tool\"|rglob\\(" src/repo_harness/workspace src/repo_harness/tools`
- `jq` 检查 `runs/v3-stage-03-docker-phase-20260502T162635Z/v3-stage-03-docker-phase/docker_phase_coverage_matrix.json`
- `jq` 检查 `runs/v3-stage-03-docker-phase-20260502T162635Z/v3-stage-03-docker-phase/container_execution_facts/manifest.json`
- `PATH=.venv/bin:$PATH python -m pytest tests/unit/test_workspace_backend.py -q`
- `PATH=.venv/bin:$PATH python -m pytest tests/integration/test_docker_backend_e2e.py::test_docker_backend_replay_smoke_records_facts -q`
- `PATH=.venv/bin:$PATH repo-harness inspect-workspace-backend --status-file runs/v3-stage-03-docker-phase-20260502T162635Z/v3-stage-03-docker-phase/docker_backend_status.json --assert-docker-backend`

## 第一轮发现

### P1

Docker `list_files` 没有通过容器执行。`DockerWorkspaceAdapter.list_files` 直接用 host `Path.rglob` 遍历 workspace，后续 agent tool no-op 只能证明跑过一个空容器命令，不能证明 list_files 行为本身通过 Docker backend。

修复：`DockerWorkspaceAdapter.list_files` 改为通过 `_execute_in_container` 执行容器内 Python 列表逻辑，并以 `command_semantics="agent_tool"` 记录 facts。宿主机只做敏感路径和 pattern 过滤。

### P2

Inspect 对 manifest 和矩阵一致性校验偏弱。它没有校验 matrix 的 manifest ref 与 status 一致、manifest entry_count、manifest refs 属于 status refs、matrix facts refs 属于 manifest。

修复：`_assert_docker_phase_coverage` 新增上述交叉校验。单元测试覆盖 manifest entry_count 漂移和 matrix manifest ref 漂移。

### P2

阶段覆盖可被 no-op 命令标记为 passed。`agent_tool` 覆盖由 `python -c pass` 补点，不是真实工具操作。

修复：删除 ToolExecutor 中人工 `agent_tool` no-op。新 run 中 `agent_tool` 的 command semantics 为 `file_read` 和 `file_write`，由真实工具文件操作产生。`source_checkout` 和无 setup command 的 setup 仍使用显式 no-op 作为 lifecycle marker；该行为记录为 lifecycle marker，不替代真实 file/tool phase。

## 最终复核

只读子代理最终复核确认：

- `DockerWorkspaceAdapter.list_files` 已通过容器执行，并生成 container execution facts。
- `ToolExecutor` 中人工 `agent_tool` no-op 已移除。
- Inspect 已校验 matrix manifest ref、manifest entry_count、manifest refs 与 status refs、matrix facts refs 与 manifest refs。
- 新 run 的 matrix 覆盖 12 个 phase。
- `agent_tool` 由真实 `file_read` / `file_write` 操作提供，没有人工 no-op。

最终复核结论：

- P1：无。
- P2：无。
- P3：无新的技术阻断项。
- 技术修复点允许进入阶段 4。

## 范围记录

工作树仍存在与 Stage 3 无关的既有文档删除、新增文档目录、`.vscode` 和 `uv.lock`。这些不属于阶段 3 范围，不得进入阶段 3 commit。

## 结论

阶段 3 满足当前 V3 实施计划要求，可以进入阶段 4。阶段 4 必须开始实现真实 repository-level task adapter 和 SWE-Bench-like fixed adapter，不能继续用 Docker micro replay smoke 替代真实任务集。
