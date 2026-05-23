# Stage 16B.5 执行计划：远端 Docker-capable 训练执行后端验证

本文是 Stage 16B.5 的具体执行计划。它插在 Stage 16B 和 Stage 16C 之间，
目标是验证正式远端训练应优先使用的 Docker-capable 执行后端，而不是继续把普通
`local_process` 或 local filesystem-persistent session 打磨成完整训练隔离层。

前一版路线曾考虑在 Vast.ai 这类无法稳定使用 Docker-in-Docker 的远端实例上继续加固
remote-local filesystem-persistent profile。经过重新评估，这条路线会把下面这些问题都压到
RepoHarness 自己实现：

```text
文件系统隔离
进程清理
HOME / TMP / cache 隔离
并发 episode 隔离
路径脱敏
敏感路径拒绝
共享依赖环境只读
网络限制
资源限制
workspace 清理
```

这些能力更适合由 Docker、NVIDIA Container Toolkit 和具备完整 root 权限的远端 VM / 裸机 /
完整机器承担。RepoHarness 应该验证和使用这个执行后端，而不是自己实现半个容器运行时。

Stage 16B.5 的新 profile 名称固定为：

```text
remote_docker_capable_training_backend
```

## 1. 阶段目标

Stage 16B.5 必须完成下面几件事：

1. 在低成本单卡 GPU 远端实例上验证 root 权限、Docker daemon、NVIDIA Container Toolkit、
   `docker run --gpus all` 和容器内 `nvidia-smi`。
2. 验证 RepoHarness Docker workspace backend 和 Stage 16B 的 Docker `diagnostic_shell`
   能在远端实例上运行。
3. 验证 Docker container 提供正式训练所需的底层隔离：
   - workspace mount 隔离；
   - `HOME`、`TMPDIR`、cache 隔离；
   - run directory 不挂载；
   - hidden verifier、runtime-private artifact 和宿主敏感路径不可见；
   - timeout / cancel / cleanup 后容器和后台进程不残留。
4. 至少跑通一个真实路径：

   ```text
   RepoHarnessVerlAgentLoop
   -> real_episode
   -> Docker workspace backend
   -> diagnostic_shell
   -> final verifier
   -> TrainingView
   -> AgentLoopOutput
   -> formal online RL gate
   ```

5. 验证至少两个 episode 并发或近并发运行时，容器、workspace、`HOME`、`TMPDIR`、cache、
   artifact manifest、final patch 和 run directory 不互相污染。
6. 生成本地和远端 evidence，并新增机器验收命令或等价 inspector。

## 2. 非目标

Stage 16B.5 不做下面这些事情：

- 不继续投入完整 remote-local filesystem-persistent training profile。
- 不把普通 `local_process` 或 local filesystem-persistent session 标记为正式训练安全后端。
- 不实现 Stage 16C 的公开环境提示和 `run_public_tests`。
- 不实现 Stage 16D 的 official verifier / gold patch / no-op healthcheck。
- 不实现 Stage 16E 的 patch hygiene。
- 不执行 fully async 多卡训练吞吐测试。
- 不要求租用多卡 A100、H100 或 RTX PRO 6000。
- 不放宽 Stage 16A 的 `execute_bash`。
- 不扩大 Stage 16B 的 `diagnostic_shell` 权限。
- 不让 shared dependency environment 变成可写环境。
- 不修改 `reference/verl`。

## 3. 分层范围

### 3.1 Stage 16B.5-A：远端 Docker 能力预检

Stage 16B.5-A 只验证远端机器是否适合承载正式训练执行后端，不运行完整训练。

必须验证：

```text
ssh 可进入实例。
当前用户或 root 具备安装、启动和管理 Docker 的权限。
Docker daemon 正常运行。
NVIDIA driver 可见。
NVIDIA Container Toolkit 可用。
docker run --gpus all 可以启动容器。
容器内 nvidia-smi 成功。
容器内可以看到 GPU 型号、驱动版本和 CUDA 能力。
容器退出后不会残留异常容器。
```

必须记录：

```text
remote_backend_provider
instance_id
gpu_model
gpu_count
driver_version
cuda_version
docker_version
nvidia_container_toolkit_version
base_os
root_access_verified
docker_daemon_status
docker_gpus_all_status
container_nvidia_smi_status
preflight_image
preflight_image_digest
remote_docker_backend_preflight_passed
```

### 3.2 Stage 16B.5-B：RepoHarness Docker diagnostic session smoke

Stage 16B.5-B 在通过预检的远端机器上验证 RepoHarness 自己的 Docker backend。

必须验证：

```text
RepoHarness Docker workspace backend 可启动。
Docker diagnostic_shell 可用。
diagnostic_shell session 不挂载真实 run directory。
模型可见 workspace 不暴露 .git object database、runtime_private、.repo_harness_runtime、.repo_harness_env_overlay 或 hidden evaluator artifact。
public source 修改可以被 final verifier、final patch capture、TrainingView 和审计证据看到。
临时脚本、HOME、TMP、cache 和诊断私有文件不会进入 final patch。
命令输出和 typed metadata 经过路径脱敏。
cleanup 后容器被移除。
timeout 或 cancel 后容器被移除，并且样本不可训练。
```

必须跑通至少一个 terminal sample：

```text
diagnostic_session_backend = docker
diagnostic_session_profile = remote_docker_capable_training_backend
remote_docker_backend_preflight_passed = true
remote_docker_diagnostic_profile_verified = true
run_dir_mount_enabled = false
workspace_projection_sync_status = completed
diagnostic_session_cleanup_status = completed
container_cleanup_status = completed
background_process_cleanup_status = completed
path_leak_scan_passed = true
visibility_scan_passed = true
final_verifier_status = accepted
formal_online_rl_gate_passed = true
invalid_for_training = false
```

## 4. 训练资格硬门槛

使用远端 Docker `diagnostic_shell` 的 terminal sample 只有满足下面条件时，才能进入正式在线强化学习候选：

```text
diagnostic_session_profile == remote_docker_capable_training_backend
remote_docker_backend_preflight_passed == true
remote_docker_diagnostic_profile_verified == true
docker_gpus_all_status == passed
container_nvidia_smi_status == passed
run_dir_mount_enabled == false
workspace_projection_sync_status == completed
diagnostic_session_cleanup_status == completed
container_cleanup_status == completed
background_process_cleanup_status == completed
session_invalidated == false
shared_dependency_environment_written == false
hidden_path_guard_passed == true
path_leak_scan_passed == true
visibility_scan_passed == true
token_provenance_passed == true
reward_boundary_passed == true
formal_online_rl_gate_passed == true
```

任何一个条件失败，都必须：

```text
invalid_for_training = true
invalid_for_online_rl = true
sample_destination = diagnostic_side_channel
```

如果远端 Docker 能力预检失败，Stage 16B.5 不能标记完成。该机器可以作为临时
local diagnostic fallback 使用，但不能作为正式训练执行后端。

## 5. 共享依赖环境边界

Stage 16B.5 不要求在第一版远端 smoke 中启用共享依赖环境。更安全的默认策略是：

```text
如果共享依赖环境只读边界已有机器证据，可以注入只读共享环境。
如果无法证明共享环境只读，禁用共享环境注入，退回每题私有环境或结构化拒绝。
不能证明只读时，不应该禁用 Docker backend；应该禁用共享环境复用模式。
```

必须记录：

```text
shared_dependency_environment_requested
shared_dependency_environment_injected
shared_dependency_environment_readonly_verified
shared_dependency_environment_disabled_reason
per_episode_private_environment_enabled
dependency_mutation_attempted
dependency_mutation_policy_result
shared_dependency_environment_written
```

训练资格要求：

```text
shared_dependency_environment_written == false

如果 shared_dependency_environment_injected == true：
  shared_dependency_environment_readonly_verified 必须为 true。

如果 shared_dependency_environment_readonly_verified != true：
  shared_dependency_environment_injected 必须为 false。
  shared_dependency_environment_disabled_reason 必须非空。

dependency_mutation_policy_result 必须是 not_attempted 或 rejected_before_execution。
```

## 6. 远端路径脱敏

公开 evidence、模型可见输出、ToolResult preview、TrainingView、AgentLoopOutput 和 DataProto
都不能包含远端真实路径。

必须脱敏：

```text
远端 workspace path
Spheron / 其他平台实例默认工作目录
/root
~/.ssh
~/.aws
/proc/self/environ
run directory
runtime_private
Docker mount path
container workspace mount path
container HOME
container TMPDIR
container cache
shared virtualenv path
other episode workspace
other run directory
.repo_harness_runtime
.repo_harness_env_overlay
```

runtime-private raw log 可以保留真实路径，但必须放入 `runtime_private/`，并且只能通过 private manifest 和 sha256 引用，不能进入公开 summary。

## 7. 建议实现归属

### 7.1 Docker backend 和 workspace adapter

重点文件：

```text
src/repo_harness/workspace/docker_adapter.py
src/repo_harness/workspace/diagnostic_session.py
src/repo_harness/tools/minimal.py
```

需要新增或确认：

```text
remote_docker_capable_training_backend profile facts
remote docker preflight helper
docker run --gpus all probe
container nvidia-smi probe
container cleanup verification
remote path redaction source list
Docker diagnostic_shell training eligibility facts
```

### 7.2 RL result 和 formal gate

重点文件：

```text
src/repo_harness/rl/runtime.py
src/repo_harness/rl/episode.py
src/repo_harness/rl/training_view.py
src/repo_harness_verl/conversion.py
```

需要确保：

```text
Docker diagnostic facts 可以进入 RepoHarnessEpisodeResult 的安全 diagnostics。
TrainingView 不携带 runtime-private 路径。
AgentLoopOutput formal_online_rl=True 时仍要求 generation_records 和 token provenance。
invalid Docker diagnostic sample 不进入 policy loss。
```

### 7.3 Acceptance inspector

建议新增：

```text
src/repo_harness_verl/stage16b5_acceptance.py
```

并提供命令：

```text
repo-harness inspect-stage16b5-docker-backend-acceptance <evidence.tar.gz|dir> --assert-complete
```

如果当前 CLI 入口命名不同，可以使用等价命令，但最终执行报告必须写清楚。

## 8. 本地实施步骤

### Step 1：实现 Docker backend profile facts

本地先实现 profile schema 和验收器，不需要远端 GPU。

验收：

```text
remote_docker_capable_training_backend facts 可以序列化。
普通 local_process 不能获得 remote_docker_diagnostic_profile_verified=true。
Docker backend 缺失 run_dir_mount_enabled=false 时不可训练。
Docker cleanup failed 时不可训练。
path leak scan failed 时不可训练。
```

### Step 2：实现或补齐 Docker preflight 报告格式

本地可用 fake probe 或无 GPU skip，但 schema 必须固定。

报告至少包含：

```text
stage16b5_docker_preflight_report.json
```

字段包括：

```text
root_access_verified
docker_daemon_status
docker_version
nvidia_container_toolkit_version
docker_gpus_all_status
container_nvidia_smi_status
preflight_image
preflight_image_digest
preflight_passed
```

### Step 3：formal online RL gate 兼容测试

构造一个 Docker diagnostic facts 全部通过的 `RepoHarnessEpisodeResult`，验证：

```text
TrainingView route=verl。
generation_records 非空。
response_ids / response_logprobs 来自 gateway collector。
episode_result_to_agent_loop_output(formal_online_rl=True) 通过。
validate_formal_online_rl_batch(...) 通过。
```

同时构造负例：

```text
remote_docker_backend_preflight_passed=false -> rejected
container_cleanup_status=failed -> rejected
run_dir_mount_enabled=true -> rejected
path_leak_scan_passed=false -> rejected
shared_dependency_environment_written=true -> rejected
```

## 9. 远端实施步骤

### 9.1 远端实例选择

第一版建议选择低成本单卡 GPU，而不是多卡训练机器。选择标准：

```text
完整 root 权限。
可以安装或启动 Docker。
可以安装或使用 NVIDIA Container Toolkit。
可以执行 docker run --gpus all。
容器内可以执行 nvidia-smi。
磁盘空间足够拉取基础镜像和 RepoHarness 代码。
支持 SSH 和文件传输。
```

Spheron 文档说明其 GPU 云平台提供完整 root access、VM / bare metal 形态和多种 GPU 选择，这类实例适合作为 Stage 16B.5 的候选远端后端。

### 9.2 远端预检命令

执行计划实施时需要按实际系统调整命令，但 evidence 必须覆盖：

```bash
whoami
id
docker --version
docker info
nvidia-smi
nvidia-ctk --version || nvidia-container-toolkit --version || true
docker run --rm --gpus all <cuda-or-nvidia-image> nvidia-smi
```

如果 Docker 或 NVIDIA Container Toolkit 缺失，可以安装；安装步骤必须写入 sanitized command log。
如果安装失败，Stage 16B.5 失败，不继续冒充 Docker-capable backend。

### 9.3 RepoHarness Docker diagnostic session smoke

远端 smoke 使用极小仓库任务，例如：

```text
buggy_calculator 或等价 micro repo
```

建议第一版允许 fake `LLMServerClient`，因为本阶段重点是 Docker 后端，不是模型能力。但必须满足：

```text
仍然走 RepoHarnessVerlAgentLoop。
仍然走 real_episode。
仍然走 Docker workspace backend。
仍然走 diagnostic_shell。
仍然产生 route=verl。
generation_records 非空。
response_ids 非空。
response_logprobs 非空。
不能退化成 route=mock、minimal_gateway 或无 token provenance 样本。
```

如果使用真实小模型，也必须记录模型 id、token facts 和 logprob provenance。

### 9.4 远端正例

正例必须证明：

```text
diagnostic_session_backend=docker。
diagnostic_session_profile=remote_docker_capable_training_backend。
remote_docker_backend_preflight_passed=true。
remote_docker_diagnostic_profile_verified=true。
docker_gpus_all_status=passed。
container_nvidia_smi_status=passed。
run_dir_mount_enabled=false。
workspace_projection_sync_status=completed。
diagnostic_session_cleanup_status=completed。
container_cleanup_status=completed。
background_process_cleanup_status=completed。
path_leak_scan_passed=true。
final_verifier.accepted=true。
invalid_for_training=false。
formal_online_rl_gate_passed=true。
```

### 9.5 远端负例

至少覆盖：

```text
Docker preflight failed -> Stage 16B.5 incomplete。
run_dir_mount_enabled=true -> 样本不可训练。
容器内访问 hidden evaluator 或 runtime_private -> 拒绝或不可训练。
容器内路径泄漏到模型可见输出 -> 样本不可训练。
命令 timeout 后容器未清理 -> 样本不可训练。
后台进程残留 -> 样本不可训练。
projection sync failed -> 样本不可训练。
共享依赖环境写入 -> 样本不可训练。
```

负例可以通过受控 tool call 或短路径注入构造，不要求真实模型自然触发。

### 9.6 并发隔离

远端至少构造两个并发或近并发 episode：

```text
episode A 写入 HOME/cache/workspace 标记。
episode B 不能看到 A 的 HOME/cache/workspace 标记。
episode A final patch 不包含 B 的文件。
episode B final patch 不包含 A 的文件。
两个 episode 的 container id、workspace、artifact manifest、run directory 不同。
cleanup 后两个容器均不存在。
```

## 10. Evidence 要求

本地 evidence：

```text
runs/repo-harness-verl-stage16b5-docker-local-<timestamp>/
```

远端 evidence：

```text
runs/repo-harness-verl-stage16b5-docker-remote-<timestamp>/
```

canonical files 至少包含：

```text
stage16b5_acceptance_summary.json
stage16b5_docker_preflight_report.json
stage16b5_docker_diagnostic_smoke_report.json
stage16b5_path_redaction_report.json
stage16b5_shared_dependency_guard_report.json
stage16b5_concurrency_isolation_report.json
stage16b5_container_cleanup_report.json
stage16b5_formal_online_rl_gate_report.json
stage16b5_negative_cases_report.json
stage16b5_training_eligibility_report.json
stage16b5_command_log.sanitized.jsonl
stage16b5_canonical_evidence_map.json
stage16b5_remote_patch_manifest.json
fixture_manifest.json
fixture_sha256_report.json
runtime_private/stage16b5_command_log.raw.jsonl
runtime_private/raw_container_logs_manifest.json
```

如果远端执行使用未提交 helper、临时 patch、monkey patch 或 runtime shim，
`stage16b5_remote_patch_manifest.json` 必须记录文件路径、sha256、用途、启用方式和回退方式。

`stage16b5_acceptance_summary.json` 至少包含：

```text
stage = "16B.5"
profile = "remote_docker_capable_training_backend"
repo_commit
remote_backend_provider
remote_instance_id
remote_image_or_os
gpu_model
gpu_count
driver_version
cuda_version
docker_version
nvidia_container_toolkit_version
remote_docker_backend_preflight_passed
remote_docker_diagnostic_profile_verified
docker_gpus_all_status
container_nvidia_smi_status
valid_docker_diagnostic_sample_count
invalid_docker_diagnostic_sample_count
diagnostic_side_channel_sample_count
formal_online_rl_gate_passed
public_path_leak_scan_passed
runtime_private_evidence_present
instance_final_status
```

远端 evidence 打包或最终验收前必须重新采集实例状态。
如果 `stage16b5_acceptance_summary.json` 中仍然记录 `instance_final_status=running`，
即使事后实例已经停止，也不能通过 `--assert-complete`。

## 11. 新增测试计划

建议新增或等价覆盖：

```text
tests/unit/test_repo_harness_stage16b5_docker_backend_profile.py
tests/unit/test_repo_harness_stage16b5_training_gate.py
tests/unit/test_repo_harness_stage16b5_path_redaction.py
tests/unit/test_repo_harness_stage16b5_acceptance.py
tests/integration/test_repo_harness_stage16b5_docker_remote_smoke.py
```

重点用例：

```text
普通 local_process 没有 remote Docker facts -> 不可训练。
local filesystem-persistent testing facts 不能让样本可训练。
Docker preflight failed -> 不可训练。
Docker cleanup failed -> 不可训练。
run_dir_mount_enabled=true -> 不可训练。
path redaction failed -> 不可训练。
shared dependency written -> 不可训练。
remote Docker facts 全部通过 -> 可进入 formal online RL candidate。
remote Docker valid sample 能通过 episode_result_to_agent_loop_output(formal_online_rl=True)。
```

## 12. 既有回归测试

Stage 16B.5 实现完成后，至少运行：

```bash
PYTHONPATH=src uv run --extra dev python -m pytest -q \
  tests/unit/test_repo_harness_stage16b_diagnostic_shell_tool.py \
  tests/integration/test_repo_harness_stage16b_docker_diagnostic_session.py \
  tests/unit/test_repo_harness_stage16a_execute_bash.py \
  tests/unit/test_command_policy.py \
  tests/unit/test_repo_harness_rl_stage12_5_formal_batch_gate.py \
  tests/unit/test_repo_harness_verl_stage10_agent_loop_output.py \
  tests/unit/test_repo_harness_rl_stage14_3_pause_resume_facade.py
```

如果本机 Docker 不可用，可以 skip 本机 Docker integration，但远端 Docker-capable profile 必须单独通过。

## 13. 远端验收通过标准

Stage 16B.5 只有满足下面条件才算完成：

```text
低成本单卡远端 GPU 实例执行通过。
root 权限通过。
Docker daemon 通过。
NVIDIA Container Toolkit 通过。
docker run --gpus all 通过。
容器内 nvidia-smi 通过。
RepoHarness Docker diagnostic session smoke 通过。
至少一个 Docker diagnostic_shell terminal sample 通过 formal online RL gate。
至少一个 Docker diagnostic_shell terminal sample 完成 final verifier accepted。
至少两个 episode 的 Docker 后端并发隔离通过。
负例全部进入 diagnostic side channel，不进入 policy loss。
公开 evidence 无真实路径泄漏。
runtime_private raw evidence 存在且不进入公开 summary。
cleanup 后无残留容器和 session-owned process。
实例最终状态记录为 stopped / exited / paused 等非 running 状态。
repo-harness inspect-stage16b5-docker-backend-acceptance --assert-complete 通过，或等价机器验收通过。
```

## 14. 提交范围

Stage 16B.5 提交应只包含：

```text
36-stage-16b-5-execution-plan.md
remote Docker backend profile facts
Docker backend training eligibility gate
Docker backend acceptance inspector
Stage 16B.5 测试
Stage 16B.5 本地和远端 evidence
必要的 Stage 16C 文档编号顺延
```

不要混入：

```text
未跟踪 HTML 资料
training_design 临时资料
vastai_cli.md
pyrightconfig.json
Stage 16C 公开环境 prompt 实现
Stage 16D official verifier healthcheck
Stage 16E patch hygiene
reference/verl 修改
```

## 15. 进入 Stage 16C 的条件

只有满足下面条件，才进入 Stage 16C：

```text
Stage 16A execute_bash 安全最小工具面仍然通过。
Stage 16B diagnostic_shell 协议和 Docker lifecycle 仍然通过。
Stage 16B.5 remote_docker_capable_training_backend 在远端通过。
远端 Docker diagnostic session 可以生成至少一个 formal online RL eligible terminal sample。
远端 Docker 负例不会进入 policy loss。
远端公开 evidence 无路径泄漏。
共享依赖环境只读或禁用逻辑有机器证据。
cleanup / timeout / cancellation / container cleanup 有机器证据。
```

Stage 16B.5 通过不表示模型已经具备更好的公开环境理解。公开测试入口和模型行为提示仍然必须在 Stage 16C 单独实现和验收。
