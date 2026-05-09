# Docker 环境和命令执行

## Docker backend 的定位

RepoHarness 当前的 Docker backend 应该准确描述为：

```text
Docker-based executable repository environment
```

它不是生产级安全沙箱，也不是远程分布式执行集群。它的目标是让每个任务在可记录、可复现、与宿主机主流程隔离的容器环境中执行 setup、工具命令和 verifier 命令。

主要实现文件：

```text
src/repo_harness/workspace/backend_factory.py
src/repo_harness/workspace/protocol.py
src/repo_harness/workspace/docker_adapter.py
src/repo_harness/workspace/schemas.py
```

## backend 是在哪里切换的

`run_task` 调用：

```text
create_workspace_adapter(config=config, run_id=actual_run_id, run_dir=run_dir)
```

`create_workspace_adapter` 根据：

```yaml
runtime:
  execution_mode: docker
```

创建 `DockerWorkspaceAdapter`。如果 Docker 初始化失败，它不会静默回退到 local process，而是写初始化失败 evidence，然后抛出明确错误。

这点很重要：如果配置说要 Docker，就必须真的使用 Docker；否则 evidence 不能伪装成 Docker run。

## DockerRuntimeConfig

Docker 相关配置在 `src/repo_harness/config/schemas.py` 的 `DockerRuntimeConfig`：

```text
image_ref: repo-harness-v3-python:stage2
build_base_image: python:3.12-slim
build_if_missing: true
requested_container_platform: linux/amd64 或 linux/arm64
network_policy: deny_agent_run
mount_policy: workspace_read_write_tmp_only
cleanup_policy: remove_containers_keep_images
command_timeout_sec: 120
max_parallel_runs: 1
```

需要注意两个细节：

- 配置里的 `mount_policy` 会被记录，但 Docker adapter 当前实际使用的 effective mount policy 是 `run_dir_read_only_workspace_read_write`。
- `network_policy=deny_agent_run` 会映射成 Docker 的无网络或受限网络模式，具体由 `_docker_network_mode` 决定。

## Docker image 怎么来

`DockerWorkspaceAdapter.__init__` 会做这些事：

```text
检查 docker CLI
-> 检查 docker server
-> 决定 requested_container_platform
-> ensure image
-> probe container uname -m
-> 写 docker_backend_facts.json
```

如果镜像不存在且 `build_if_missing=true`，它会用内置 Dockerfile 构建镜像。默认 base image 是：

```text
python:3.12-slim
```

默认 Dockerfile 会安装一些基础依赖，例如：

```text
git
pytest
mpmath
```

这说明当前 Docker backend 是面向 Python / pytest 主路径优化的基础环境。不同语言的 GitHub PR / issue 任务如果需要 Go、Node.js、Rust 等工具链，就必须通过更明确的 environment lock strategy 或后续镜像扩展来解决。

## run directory 和容器路径

Docker backend 有一个固定容器根路径：

```text
/repo-harness-run
```

宿主机 run directory 会被只读挂载：

```text
-v <host_run_dir>:/repo-harness-run:ro
```

具体 workspace 子目录会被读写挂载：

```text
-v <host_workspace>:/repo-harness-run/workspaces/<workspace_name>:rw
```

因此：

- run-level evidence 对容器只读。
- 当前命令要操作的 workspace 对容器可写。
- container workdir 是 `/repo-harness-run/...` 下的 workspace 路径。
- 宿主机仍然能在 `runs/.../workspaces/...` 看到文件变化。

## source checkout、setup workspace、agent workspace、verification workspace

一次运行不是只有一个目录，而是多个生命周期不同的工作区：

```text
source checkout
  原始源码物化结果

setup workspace
  用于运行 setup 和 baseline verifier

agent workspace
  模型通过工具实际读写的工作区

verification workspace
  final patch 重放和 formal final verifier 使用的干净工作区
```

Docker adapter 中对应方法：

- `create_source_checkout`
- `create_setup_workspace`
- `capture_dependency_state`
- `create_agent_workspace`
- `create_verification_workspace`

`create_agent_workspace` 会从 source checkout 复制源码，恢复 dependency state，然后创建 git baseline commit。这个 baseline 是之后捕获 final patch 的 diff base。

`create_verification_workspace` 会从 source checkout 重新复制源码，恢复 dependency state，然后应用 agent final patch。这样 final verifier 不会被 agent workspace 中的临时产物、缓存或未记录副作用污染。

## 命令是怎样进入容器的

所有工具命令和 verifier 命令最后都会走 workspace adapter 的：

```text
run_command(...)
```

在 Docker backend 中，它会调用 `_execute_in_container`，最终执行类似：

```text
docker run --rm
  --name <container_name>
  --platform <linux/amd64 或 linux/arm64>
  --network <network_mode>
  -e PYTHONDONTWRITEBYTECODE=1
  -e GIT_CONFIG_COUNT=1
  -e GIT_CONFIG_KEY_0=safe.directory
  -e GIT_CONFIG_VALUE_0=*
  -v <run_dir>:/repo-harness-run:ro
  -v <workspace>:/repo-harness-run/workspaces/<workspace>:rw
  -w <container_workdir>
  <image_ref>
  <command...>
```

命令结束后会记录：

- exit code。
- stdout preview 和 stderr preview。
- 完整输出 artifact。
- duration。
- timeout。
- container name。
- cleanup status。
- command semantics。
- container execution facts ref。

这些数据进入：

```text
artifacts/<...>_command_output.txt
container_execution_facts/<command_id>.json
events.jsonl
```

## command_semantics 的意义

RepoHarness 不只是记录“执行了一条命令”，还记录这条命令属于哪个语义阶段，例如：

- `docker_backend_probe`
- `source_checkout`
- `setup`
- `baseline_verifier`
- `bash_diagnostic`
- `feedback_verifier`
- `git_diff`
- `final_patch_capture`
- `model_final_patch_apply`
- `final_verifier`
- `fail_to_pass_test_execution`
- `pass_to_pass_test_execution`

这些 semantics 会被后续 evidence 检查使用，例如 Docker phase coverage matrix 会检查关键阶段是否真的有容器命令证据。

## bash 工具不是任意 shell

模型可见的工具里有 `bash`，但它不是一个开放 shell。

执行前会经过：

```text
ToolExecutor.validate_input
-> PermissionSystem.check
-> WorkspaceAdapter.resolve_workspace_path
-> workspace_adapter.run_command
```

权限系统会拒绝：

- 管道：`|`
- 重定向：`>`、`<`
- 命令拼接：`&&`、`||`、`;`
- shell 变量和命令替换：`$`、反引号
- 多行命令
- 后台执行：`&`
- home 路径：`~`
- 网络或远程命令：`curl`、`wget`、`ssh`、`scp`
- 特权命令：`sudo`
- 删除命令：`rm`
- 任意 `python -c`
- `find`

允许的方向更像“诊断命令”：

- `pwd`
- `ls`
- 受限 `git status` / `git diff` / `git show` / `git log` / `git ls-files`
- `python -m compileall`
- `ruff`
- `mypy`
- 经过 policy 认可的 pytest 命令

如果模型通过 `bash` 输入的命令被识别为当前任务 test command，它会被路由到 `run_tests`，而不是作为普通 shell 命令直接执行。

## setup command 和 test command policy

任务定义里的 setup command 和 test command 也有静态校验：

```text
src/repo_harness/tasks/command_policy.py
```

setup command 当前只允许比较受控的形式，例如：

```text
python <repo_script.py>
```

test command 主要允许：

```text
pytest ...
python -m pytest ...
```

这体现了当前实现仍然以 Python / pytest verifier 为主路径。GitHub PR / issue 任务里如果涉及 Go、Node.js、Rust，V4 task freeze 可以记录候选和环境策略，但真正变成可稳定执行的正式任务时，需要对应语言工具链、命令 policy 和 verifier parser 的支持。

## pytest 在哪里执行

pytest 有三个常见入口：

1. baseline verifier：
   - 在 setup workspace 中运行。
   - 用于判断初始任务是否有效。

2. feedback verifier：
   - agent 调用 `run_tests` 时运行。
   - 根据 policy 决定 public feedback 或 oracle hidden feedback。

3. final verifier：
   - agent loop 结束后运行。
   - 在 clean verification workspace 中重放 final patch 后执行。

普通任务走：

```text
src/repo_harness/verifier/runner.py::PytestVerifier
```

SWE-Bench-like final-only 任务走：

```text
src/repo_harness/v3_agent_runtime.py::run_swebench_like_final_verifier
```

## 路径边界和敏感路径

Docker adapter 的 `resolve_workspace_path` 会做路径检查：

- 将容器路径和宿主机路径互相转换。
- 确认目标路径在当前 run directory 内。
- 确认模型请求的路径没有逃出 workspace。
- 拒绝敏感路径或符号链接逃逸。

这意味着即使模型传入绝对路径，也不能随意读宿主机文件或 evaluator-only artifact。

## 你需要能复述的底层链路

当模型调用：

```json
{"command": "pytest -q", "cwd": ".", "timeout_sec": 60}
```

真实发生的是：

```text
ToolExecutor 收到 tool call
-> schema 校验 command/cwd/timeout_sec 类型
-> normalize，发现它匹配任务 test command
-> effective tool 改成 run_tests
-> 检查 scaffold 当前 phase 是否允许 run_tests
-> PermissionSystem 记录 permission_decision
-> PytestVerifier.run_feedback 或 run_feedback_public
-> DockerWorkspaceAdapter.run_command
-> docker run 在 agent workspace 中执行 pytest
-> stdout/stderr 写 artifact
-> pytest parser 解析测试结果
-> VerifierResult 写 feedback_verifier_result artifact
-> ToolResult 回流给模型
-> transcript 和 events 记录这次工具观察
```

这比“模型调用 bash 跑 pytest”更准确。
