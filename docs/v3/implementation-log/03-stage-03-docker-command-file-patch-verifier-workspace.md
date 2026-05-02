# V3 Stage 03 Docker Command File Patch And Verifier Workspace

## 目标

阶段 3 的目标是在阶段 2 Docker backend factory 和基础 facts 已通过的基础上，补齐 Docker command、file、patch、verification workspace 的可审计执行闭环，并生成 `container_execution_facts/manifest.json` 和 `docker_phase_coverage_matrix.json`。本阶段不实现真实仓库 task adapter、SWE-Bench-like fixed adapter、source materialization hardening 或 RepoHarness 自有 fail-to-pass / pass-to-pass final verifier；这些属于后续阶段。

## 实现内容

Docker backend 的文件和命令执行路径继续收紧：

- `DockerWorkspaceAdapter.read_text` 通过容器内 Python 读取文件，而不是宿主机直接读取 container path。
- `DockerWorkspaceAdapter.write_text` 通过容器内 Python 写入文件，而不是宿主机直接写入 workspace 文件。
- `DockerWorkspaceAdapter.list_files` 通过容器内 Python 列文件，并生成 container execution facts；不再由宿主机 `Path.rglob` 直接返回结果。
- `DockerWorkspaceAdapter.apply_patch` 支持调用方传入 `command_semantics`，verification workspace 中 model final patch apply 记录为 `model_final_patch_apply`。
- `capture_final_patch` 的 git diff / patch stats 命令记录为 `final_patch_capture`。
- verification workspace creation 明确记录 `verification_workspace_creation` facts。
- 单个 fail-to-pass / pass-to-pass selector 的执行分别记录 `fail_to_pass_test_execution` 和 `pass_to_pass_test_execution`。

新增 Docker execution manifest 和 phase coverage matrix：

- `container_execution_facts/manifest.json` 汇总每条 container execution facts ref、command semantics、phase、exit code、timeout 和 cleanup status。
- `docker_phase_coverage_matrix.json` 汇总必需 phase 覆盖情况。
- `verifier_patch_apply` 和 `test_patch_apply` 在当前 replay micro task 中结构化标记为 `not_applicable`，并带 reason；这不是完整 SWE-Bench-like final verifier 声明。

增强 `inspect-workspace-backend --assert-docker-backend`：

- 重新读取 `container_execution_facts/manifest.json` 和 `docker_phase_coverage_matrix.json`。
- 校验 matrix 中的 `container_execution_manifest_ref` 与 status 一致。
- 校验 manifest `entry_count` 与 entries 数量一致。
- 校验 manifest refs 必须属于 status 中的 `container_execution_facts_refs`。
- 校验 status refs 必须全部出现在 manifest 中。
- 校验 matrix facts refs 必须属于 manifest。
- 拒绝必需 phase 缺失、`status=missing`、passed phase 缺 facts refs、not applicable phase 缺 structured reason。

## 主要修改文件

- `src/repo_harness/workspace/docker_adapter.py`
- `src/repo_harness/workspace/backend_status.py`
- `src/repo_harness/workspace/schemas.py`
- `src/repo_harness/workspace/protocol.py`
- `src/repo_harness/workspace/adapter.py`
- `src/repo_harness/evaluation/runner.py`
- `src/repo_harness/tools/minimal.py`
- `src/repo_harness/verifier/runner.py`
- `tests/unit/test_workspace_backend.py`
- `tests/integration/test_docker_backend_e2e.py`
- `docs/v3/implementation-log/03-stage-03-docker-command-file-patch-verifier-workspace.md`
- `docs/v3/review/implementation/stage-03-review.md`

## 机器产物

正式阶段 smoke run：

- `runs/v3-stage-03-docker-phase-20260502T162635Z/v3-stage-03-docker-phase/`

关键机器产物：

- `runs/v3-stage-03-docker-phase-20260502T162635Z/v3-stage-03-docker-phase/docker_backend_status.json`
- `runs/v3-stage-03-docker-phase-20260502T162635Z/v3-stage-03-docker-phase/docker_stage_status.json`
- `runs/v3-stage-03-docker-phase-20260502T162635Z/v3-stage-03-docker-phase/docker_backend_facts.json`
- `runs/v3-stage-03-docker-phase-20260502T162635Z/v3-stage-03-docker-phase/container_execution_facts/manifest.json`
- `runs/v3-stage-03-docker-phase-20260502T162635Z/v3-stage-03-docker-phase/container_execution_facts/*.json`
- `runs/v3-stage-03-docker-phase-20260502T162635Z/v3-stage-03-docker-phase/docker_phase_coverage_matrix.json`
- `runs/v3-stage-03-docker-phase-20260502T162635Z/v3-stage-03-docker-phase/final.patch`
- `runs/v3-stage-03-docker-phase-20260502T162635Z/v3-stage-03-docker-phase/final.diff`
- `runs/v3-stage-03-docker-phase-20260502T162635Z/v3-stage-03-docker-phase/run_config_facts.json`
- `runs/v3-stage-03-docker-phase-20260502T162635Z/v3-stage-03-docker-phase/run_metadata.json`

Phase coverage summary：

- `source_checkout`: `passed`
- `setup`: `passed`
- `agent_tool`: `passed`，由真实 `file_read` / `file_write` 容器操作提供，不再使用 no-op。
- `run_tests`: `passed`
- `final_patch_capture`: `passed`
- `verification_workspace_creation`: `passed`
- `verifier_patch_apply`: `not_applicable`，当前 replay micro task 没有 verifier patch。
- `test_patch_apply`: `not_applicable`，当前 replay micro task 没有 test patch。
- `model_final_patch_apply`: `passed`
- `fail_to_pass_test_execution`: `passed`
- `pass_to_pass_test_execution`: `passed`
- `final_verifier`: `passed`

## 验证命令和结果

- `PATH=.venv/bin:$PATH python -m compileall src`：通过。
- `PATH=.venv/bin:$PATH python -m pytest tests/unit/test_workspace_backend.py tests/integration/test_docker_backend_e2e.py -q`：`11 passed`。
- `PATH=.venv/bin:$PATH python -m pytest tests/unit/test_workspace_backend.py tests/integration/test_docker_backend_e2e.py tests/integration/test_docker_mode_rejected.py tests/integration/test_eval_runner_quality_gate.py::test_docker_execution_mode_missing_image_fails_without_local_fallback -q`：`13 passed`。
- `PATH=.venv/bin:$PATH python -m pytest -q`：`401 passed`。
- `PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-v3-swebench-fixture --fixture-dir tests/fixtures/v3/swebench_lite_fixed --evidence-dir docs/v3/evidence/swebench-lite-fixed --manifest tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/v3_feasibility_input_manifest.json --assert-frozen`：通过。
- `PATH=.venv/bin:$PATH repo-harness run-task tests/fixtures/tasks/task_001.yaml --config tests/fixtures/run_configs/v3/docker_run_task_smoke.yaml --output-dir runs/v3-stage-03-docker-phase-20260502T162635Z --run-id v3-stage-03-docker-phase`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-workspace-backend --status-file runs/v3-stage-03-docker-phase-20260502T162635Z/v3-stage-03-docker-phase/docker_backend_status.json --assert-docker-backend`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-workspace-backend --status-file runs/v3-stage-03-docker-phase-20260502T162635Z/v3-stage-03-docker-phase/docker_stage_status.json --assert-docker-backend`：通过。

## 正例证据

- Docker file read/write/list behavior 都通过容器命令执行，并产生 container execution facts。
- `agent_tool` phase 由 `file_read` 和 `file_write` facts 支撑，不再使用人工 `python -c pass` no-op。
- `docker_phase_coverage_matrix.json` 覆盖 12 个必需 phase。
- `container_execution_facts/manifest.json` 的 `entry_count` 与 entries 数量一致。
- `inspect-workspace-backend --assert-docker-backend` 重新读取 status、backend facts、execution facts、manifest 和 phase matrix。
- 当前 micro replay smoke 没有被表述成完整 SWE-Bench-like final verifier 或公开榜单可比结果。

## 负例证据

单元测试覆盖以下拒绝场景：

- matrix 缺少必需 phase 时失败。
- manifest `entry_count` 与 entries 数量不一致时失败。
- matrix `container_execution_manifest_ref` 与 status 不一致时失败。
- matrix facts refs 不属于 manifest 时失败。
- manifest facts refs 不属于 status 时失败。
- container execution facts 缺失、架构为空、cleanup 非 completed、image id / platform / requested platform 与 status 不一致时失败。

## 允许降级项

当前 replay micro task 没有 verifier patch 或 test patch，所以 `verifier_patch_apply` 和 `test_patch_apply` 以结构化 `not_applicable` 进入矩阵。该降级只适用于阶段 3 micro smoke；后续 SWE-Bench-like task 和 final verifier 阶段必须提供真实 verifier / test patch apply evidence。

## 禁止降级项

- 不允许用宿主机文件系统遍历或读写冒充 Docker file operation。
- 不允许用 no-op container command 冒充 agent tool phase 的真实执行。
- 不允许 `inspect-workspace-backend` 只信 summary 或 matrix，不重新读取 manifest 和 facts refs。
- 不允许把当前 micro replay smoke 表述为完整 SWE-Bench-like final verifier、完整 SWE-Bench Lite 复现或生产级安全沙箱。
- 不允许提交工作树中与阶段 3 无关的既有文档删除、新增文档目录、`.vscode` 或 `uv.lock`。

## 已知限制

阶段 3 只证明 Docker backend 的 command/file/patch/verifier workspace 基础调用面和 phase coverage 机制。真实 repository-level task set、SWE-Bench-like task adapter、fixed source materialization、test patch / verifier patch 的真实应用和 RepoHarness 自有 fail-to-pass / pass-to-pass final verifier仍属于阶段 4 到阶段 6。

## 设计偏离

没有偏离阶段 3 范围。`verifier_patch_apply` 和 `test_patch_apply` 对当前 micro smoke 为 `not_applicable` 是因为当前任务本身不包含这些隐藏补丁；该事实被结构化记录，没有伪装为 passed。

## 审查结论

只读子代理第一轮发现 1 个 P1 和 2 个 P2：

- P1：Docker `list_files` 仍由宿主机遍历完成。
- P2：inspect 对 manifest 和 matrix 的一致性校验偏弱。
- P2：部分 phase coverage 可被 no-op 命令标记为 passed。

修复后只读子代理复核结论：P1 无，P2 无；技术修复点允许进入阶段 4。工作树中仍存在无关既有改动，提交时必须继续排除。
