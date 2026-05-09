# 第 3 章：Docker 环境和命令执行

## 本章链路图

```text
RunConfig.runtime.execution_mode=docker
-> create_workspace_adapter
-> DockerWorkspaceAdapter.__init__
-> docker_backend_facts.json
-> create_source_checkout / setup workspace / agent workspace
-> workspace_adapter.run_command
-> docker run
-> command output artifact
-> container_execution_facts/<command_id>.json
-> container_execution_facts/manifest.json
```

## 本章实际运行或查看的命令

```bash
PATH=.venv/bin:$PATH repo-harness run-task \
  runs/v3-core-realrepo-deepseek-20260504T000000Z/agent_loop_runs/v3_core_realrepo_local_buggy_calculator_deepseek_docker_v2/task.yaml \
  --config runs/v3-core-realrepo-deepseek-20260504T000000Z/generated_inputs/realrepo_local_buggy_calculator_deepseek_docker_v2.yaml \
  --output-dir runs/tutorial-v4-deep-dive-20260505T082937Z \
  --run-id tutorial_realrepo_docker

PATH=.venv/bin:$PATH repo-harness inspect-run \
  runs/tutorial-v4-deep-dive-20260505T082937Z/tutorial_realrepo_docker

jq '{schema_version, backend, requested_container_platform, image_ref, image_platform, network_policy, mount_policy, cleanup_status, docker_cli_version, docker_server_version}' \
  runs/tutorial-v4-deep-dive-20260505T082937Z/tutorial_realrepo_docker/docker_backend_facts.json

jq '{entry_count, entries: [.entries[] | {command_id, command_semantics, phase, exit_code, timeout, cleanup_status}][0:20]}' \
  runs/tutorial-v4-deep-dive-20260505T082937Z/tutorial_realrepo_docker/container_execution_facts/manifest.json
```

真实复跑结果：

- 新 run：`runs/tutorial-v4-deep-dive-20260505T082937Z/tutorial_realrepo_docker`
- `inspect-run`：run outcome 为 `success`，final verifier status 为 `accepted`，reward 为 `0.996`。
- Docker backend：`backend=docker`，requested platform 为 `linux/arm64`。
- image：`repo-harness-v3-python:stage2`。
- network policy：`deny_agent_run`。
- effective mount policy：`run_dir_read_only_workspace_read_write`。
- Docker CLI / server：`29.4.1`。
- container execution facts 数量：`42`。

## 源码入口和对象流

关键入口：

- `src/repo_harness/workspace/backend_factory.py:21`：按 `runtime.execution_mode` 创建 adapter。
- `src/repo_harness/workspace/docker_adapter.py:118`：`DockerWorkspaceAdapter`。
- `src/repo_harness/workspace/docker_adapter.py:191`：创建 source checkout。
- `src/repo_harness/workspace/docker_adapter.py:223`：创建 agent workspace。
- `src/repo_harness/workspace/docker_adapter.py:371`：路径解析和 workspace boundary。
- `src/repo_harness/workspace/docker_adapter.py:508`：`run_command`。
- `src/repo_harness/workspace/docker_adapter.py:661`：实际执行 `docker run`。
- `src/repo_harness/workspace/docker_adapter.py:780`：workspace 读写挂载参数。
- `src/repo_harness/permissions/system.py:25`：权限检查入口。
- `src/repo_harness/permissions/system.py:211`：bash 命令拒绝原因。

关键理解：

- run directory 只读挂载到容器 `/repo-harness-run`。
- 当前 workspace 子目录读写挂载，模型工具只能通过 workspace adapter 访问这个边界内的路径。
- 每条容器命令都有 `command_semantics`，例如 `source_checkout`、`setup`、`verifier_baseline`、`fail_to_pass_test_execution`、`pass_to_pass_test_execution`、`agent_tool`、`file_read`。
- Docker backend 不做静默 fallback。配置要求 Docker 时，如果 Docker 不可用，应写结构化失败并中止。

## 面试追问与推荐回答

问：你们是怎样执行模型请求的 bash 命令的？

答：模型的 `bash` tool call 先经过 schema 校验、权限系统和 workspace boundary 检查。允许后调用 `WorkspaceAdapter.run_command`。Docker mode 下会构造一次 `docker run`，挂载 run directory 和 workspace，设置 workdir，执行命令并记录 stdout、stderr、exit code、timeout、duration 和 container execution facts。

问：Docker backend 是安全沙箱吗？

答：不能这样描述。它是 Docker-based executable repository environment，用于可复现执行和证据记录。项目不宣称它是生产级安全沙箱。

问：为什么要记录 container execution facts？

答：因为训练轨迹的可信度依赖真实执行证据。只记录工具结果文本不足以审计命令是否真的在 Docker 中执行、使用哪个镜像、哪个平台、什么网络策略、是否超时、是否清理容器。
