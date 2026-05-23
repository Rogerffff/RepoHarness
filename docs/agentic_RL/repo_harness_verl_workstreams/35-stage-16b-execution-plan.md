# Stage 16B 执行计划：persistent diagnostic session 生命周期

创建时间：2026-05-23

## 1. 阶段定位

Stage 16A 已经把正式训练主线中的 `execute_bash` 收紧成“安全最小 shell 面”。它只允许少量可审计、可脱敏、不会污染共享依赖环境的命令。Stage 16B 不应该反向放宽 `execute_bash`，也不应该把完整产品态 Bash 直接塞回正式训练工具面。

Stage 16B 的目标是实现一个单独的 persistent diagnostic session 能力，用来承接真实软件工程智能体经常需要的“同一道题内部持续诊断环境”：

```text
第一次诊断：创建复现文件、运行测试、查看错误。
第二次诊断：继续使用同一个题目内 HOME / TMP / cache / Docker container 状态。
题目结束：强制清理 session，不跨题复用，不跨 run 复用。
```

本阶段的核心不是扩大训练规模，也不是替代 Stage 16C 的公开测试入口或 Stage 16D 的 official verifier healthcheck。它只解决 persistent diagnostic session 的协议、后端生命周期、工具路由、隔离和证据链。

## 2. 关键结论和默认决策

### 2.1 工具面决策

第一版采用下面的分工：

```text
execute_bash：
  保持 Stage 16A 的安全最小 shell 面。
  不新增完整 shell、依赖安装、项目脚本或持久会话能力。

diagnostic_shell：
  新增或恢复为 Stage 16B 的高权限诊断工具。
  只在显式启用的 diagnostic profile、smoke fixture 或后续训练配置中可见。
  必须走 persistent diagnostic session 后端。
  不能静默 fallback 到普通 fresh run_command。
```

如果实现时发现当前分支没有 `diagnostic_shell` 工具，需要新增它；如果已有旧工具名或旧 schema，需要将其升级为 Stage 16B 版本。不要把 `diagnostic_shell` 伪装成 `execute_bash` 的隐藏模式。

### 2.2 两类 persistent session

本阶段实现两个后端：

```text
Docker persistent diagnostic session：
  同一道题内部复用同一个长期运行 container。
  后续命令通过 docker exec 进入同一 container。
  工作区在容器内固定为 /workspace。
  不挂载 RepoHarness run directory。
  timeout 后强制销毁 container，并标记 session invalidated。

Local filesystem-persistent diagnostic session：
  不实现真正常驻 shell 进程。
  每次命令仍是新进程，但同题复用同一个 HOME、TMPDIR、PIP_CACHE_DIR、UV_CACHE_DIR。
  同题内工作区文件、临时目录和 cache 状态持久。
  不承诺 cd、export、source activate 这类 shell 进程状态跨命令持久。
```

这个区别必须写进模型可见工具描述和结构化事实，避免执行 agent 或训练样本把 local 后端误解成“完整常驻 shell”。

### 2.3 训练资格口径

本阶段允许 `diagnostic_shell` 进入受控 `real_episode` smoke，但每条样本必须携带工具面事实：

```text
tool_surface_profile = persistent_diagnostic_session
diagnostic_session_backend = docker_persistent_container 或 local_filesystem_persistent
diagnostic_session_persistent = true
run_dir_mount_enabled = false
diagnostic_session_cleanup_status = completed / failed / invalidated
session_invalidated = false
```

只有满足下面条件的 terminal sample，才可以进入 formal online RL 候选：

```text
diagnostic_session_cleanup_status = completed
session_invalidated = false
background_process_cleanup_status = completed
workspace_projection_sync_status = completed
visibility、token provenance、reward boundary 和 formal online RL gate 全部通过
```

如果出现 cleanup failed、timeout invalidated、session state uncertain、background process uncertain、projection sync failed，则该样本默认：

```text
invalid_for_training = true
invalid_for_online_rl = true
等价机器验收字段必须包含 invalid_for_training=true 与 invalid_for_online_rl=true。
sample_destination = diagnostic_side_channel
```

也就是说，使用 `diagnostic_shell` 的样本可以作为后续训练候选，但前提是资源生命周期、projection 写回和安全边界都已经收口。Stage 16B 不承诺这些样本已经适合大规模训练。进入代表性训练前，还需要 Stage 16C、Stage 16D、Stage 16E 和 Stage 16.5 的后续门槛。

## 3. 本阶段不做

Stage 16B 不做下面这些事情：

```text
不放宽 Stage 16A 的 execute_bash allowlist。
不实现 run_public_tests / run_project_test 的正式路由。这个属于 Stage 16C。
不实现 official verifier / gold patch / no-op healthcheck。这个属于 Stage 16D。
不实现 patch hygiene 的最终过滤策略。这个属于 Stage 16E。
不把 diagnostic session 状态写入 final.patch、SFT target、preference pair 或 reward evidence。
不实现跨题、跨 run、跨进程 durable shell session。
不让 local filesystem-persistent session 在 hidden-evaluator 或 final-only SWE-Bench 路径中默认开启。
不修改 reference/verl。
```

## 4. 设计约束

### 4.1 session ownership

每个 diagnostic session 必须绑定到一个明确的 ownership scope：

```text
run_id
task_id
episode_id 或 workspace lease id
workspace host path digest
backend
session_id
```

同题内可以复用；不同题、不同 run、不同 workspace digest 必须隔离。即使两个任务使用同一个 repository snapshot，也不能共享 diagnostic session。

### 4.2 run directory 不挂载

Docker persistent session 必须满足：

```text
run_dir_mount_enabled = false
容器内不存在 /repo-harness-run
容器内不能通过 mount、env、find、ls 等方式看到 run directory path
公开 stdout / stderr 不能泄漏 run directory path
```

如果实现为了调试保留 runtime-private raw artifact，这些 raw artifact 必须只存在于 runtime-private evidence 中，不能进入模型可见 observation、TrainingView、AgentLoopOutput、DataProto 或公开 acceptance summary。

### 4.3 timeout invalidation

Docker 后端第一版不尝试在容器内精细清理进程组。规则固定为：

```text
任意 docker exec 超时：
  docker rm -f 当前 diagnostic container
  session_invalidated = true
  session_cleanup_status = completed 或 failed
  后续命令不能复用旧 container
```

Local 后端规则固定为：

```text
任意命令超时：
  杀死当前进程组
  session_invalidated = true
  后续命令必须重新创建新的 session state directory，或返回 structured denied
```

不能出现“超时后继续复用状态不可解释的 session”。

### 4.4 keep_workspace 不等于 keep_session

`keep_workspace=True` 只允许保留可审计的 workspace 文件。它不能保留活动 Docker container，也不能保留 active local session directory。

验收必须覆盖：

```text
keep_workspace=True
-> cleanup_workspaces 或 episode cleanup 被调用
-> Docker diagnostic container 已删除
-> local diagnostic session directory 已删除或标记为 completed cleanup
-> workspace 可按 keep_workspace 策略保留
```

### 4.5 local backend 的共享依赖环境边界

Local filesystem-persistent session 必须继承 Stage 12.5 和 Stage 16A 的共享依赖环境原则：

```text
共享依赖环境：跨题复用，只读，模型不能修改。
每题 session HOME / TMP / cache：每题独立，可写，题目结束后清理。
```

如果当前 episode 使用共享依赖环境，但 runtime 没有提供可校验的 `shared_dependency_environment_roots`，则 local diagnostic session 必须 fail closed。不能因为缺少 roots 就静默放开 `pip install`、`uv sync`、`npm install` 或直接写共享环境路径。

如果该 episode 可以安全降级为 no shared environment 或 per-episode private environment，则允许先禁用共享依赖环境注入，再运行 local diagnostic session，并在 facts 中记录：

```text
shared_dependency_environment_requested = true
shared_dependency_environment_injected = false
shared_dependency_environment_disabled_reason = missing_roots_for_diagnostic_session
```

不允许在 roots 缺失时继续保留共享环境注入。

### 4.6 hidden-evaluator / final-only 任务边界

Local diagnostic shell 不能默认用于 hidden-evaluator 或 final-only SWE-Bench 路径。拒绝条件至少包括：

```text
swe_bench_like_final_only = true
final_only = true
hidden evaluator refs 非空
official selector refs 非空且当前 backend 不是 Docker isolated diagnostic session
task visibility policy 标记存在 evaluator-only artifacts
```

Docker backend 也不能读取 evaluator-only artifacts，但 Docker 可以作为以后 SWE-Bench 评测诊断的默认后端，因为它不挂载 run directory，并且工作区布局更接近 `/workspace`。

### 4.7 diagnostic shell 的模型可见文件系统视图

Stage 16B 的 `diagnostic_shell` 比 Stage 16A 的 `execute_bash` 更接近完整 shell。因此，Git 历史和 runtime-private 防泄漏不能只依赖命令文本拦截。只要模型可以在 shell 中访问 `.git` 对象库，它就可以通过 `cat .git/logs/HEAD`、`find .git`、`python -c "open('.git/...')"` 等方式绕过 `git log` / `git show` 的命令策略。

所以 Stage 16B 必须新增一个硬约束：

```text
diagnostic_shell 看到的模型可见 workspace 视图不能暴露 Git object database、Git refs、Git logs、runtime-private 内容、evaluator-only artifact 或任何可恢复隐藏事实的文件。
```

这个模型可见 workspace projection 必须至少排除或隐藏：

```text
.git
runtime_private
.repo_harness_env_overlay
.repo_harness_runtime
.env
run directory
hidden verifier
gold patch
test patch
official selector
evaluator-only artifact
symlink escape
```

允许的实现方式包括：

```text
1. 为 diagnostic_shell 创建不含 .git、runtime_private 和 evaluator-only artifact 的可写执行视图，final patch 仍由 host-side baseline 或 RunRecorder 计算。
2. 将 .git 和 runtime-private 路径替换为模型不可读的占位路径，并确保 read / find / python open 都无法访问真实内容。
3. 使用 adapter 级文件系统隔离，让 .git、runtime_private、run directory 和 evaluator-only artifact 在 diagnostic_shell 容器或 local session 中不可见，但宿主侧仍可用于 patch capture。
```

不允许的实现方式：

```text
只拦截 git log / git show / git cat-file 命令，但保留可读 .git 目录。
只在 tool 层做字符串 denylist，但允许任意 Python / cat / find 读取 .git。
把 .git 作为 runtime-private raw artifact 保留在公开 mounted workspace 内。
直接把含 .git / runtime_private / evaluator-only artifact 的原始 lease workspace 挂载给 Docker 或 local diagnostic_shell。
```

验收必须覆盖：

```text
diagnostic_shell: find .git -> 不存在、permission denied 或结构化拒绝
diagnostic_shell: cat .git/config -> 不存在、permission denied 或结构化拒绝
diagnostic_shell: python -c "open('.git/config').read()" -> 不存在、permission denied 或结构化拒绝
diagnostic_shell: find runtime_private .repo_harness_env_overlay .repo_harness_runtime -> 不存在、permission denied 或结构化拒绝
diagnostic_shell: python -c "open('.env').read()" -> 不存在、permission denied 或结构化拒绝
diagnostic_shell: git log --oneline -> 结构化拒绝
final patch capture -> 仍然可以由 harness 正确生成
```

### 4.8 diagnostic-visible projection 的写回语义

模型可见 projection 必须是“可写且可审计”的工作视图，不能变成和 verifier / patch capture 脱节的临时副本。Stage 16B 必须固定下面的语义：

```text
diagnostic-visible writable projection 必须是本 episode public workspace 的唯一模型可写视图；
或者必须有受控同步回 lease workspace / verifier workspace 的机制。
```

硬性要求：

```text
diagnostic_shell 写入的公开源码变更，必须被后续 edit_file、final verifier、final patch capture、TrainingView 和 audit evidence 看见。
diagnostic_shell 中用于复现的临时脚本、session HOME/TMP/cache 文件、依赖 cache、诊断日志，默认不能进入 final.patch。
如果 projection 到 lease workspace 的同步失败，episode 必须变成 infrastructure_error 或 diagnostic failure，不能进入 policy loss。
如果 final verifier 看到的 workspace 和 diagnostic_shell 测试过的 workspace 不一致，样本必须 invalid_for_training=true。
```

允许的实现方式：

```text
1. projection 本身就是 lease workspace 的安全视图，公开源码写入会同步反映到 host-side lease workspace。
2. projection 是独立目录，但每次 diagnostic_shell 命令后或 final verifier 前执行受控 rsync / copyback，只同步 public source allowlist。
3. edit_file 和 diagnostic_shell 都操作同一个 public workspace projection，host-side patch capture 从该 projection 与 baseline 计算最终 patch。
```

不允许的实现方式：

```text
diagnostic_shell 在 projection 里测试通过，但 final verifier 在另一个未同步 workspace 上运行。
diagnostic_shell 写出的源码修复没有进入 final.patch。
把 diagnostic-only 临时脚本、cache、home/tmp 文件同步进 final.patch。
```

验收必须覆盖：

```text
diagnostic_shell 修改源码 -> final verifier 能看到该修改。
diagnostic_shell 修改源码 -> final.patch 包含该公开源码修改。
diagnostic_shell 创建 tmp/repro.py 或 session HOME 文件 -> final.patch 不包含该诊断文件。
projection sync failed -> 样本进入 diagnostic side channel，不进入 policy loss。
```

### 4.9 后台进程和正常返回后的残留进程

Stage 16B 第一版不支持模型启动长期后台服务。原因是 persistent session 中的后台进程可能影响后续命令、占用端口、写文件、污染测试结果，甚至在 cleanup 后继续存活。

第一版默认策略：

```text
禁止或结构化拦截后台执行入口：
  &
  nohup
  disown
  setsid
  tmux
  screen
  daemon
  coproc
  bg / fg / jobs 控制
  sh -c "... &"
  bash -lc "... &"
```

如果实现选择允许极少数后台进程，必须同时实现：

```text
每次命令后枚举 session-owned process tree。
只允许明确白名单进程存活。
非白名单后台进程必须被终止。
cleanup 后必须证明没有 session-owned process 存活。
```

Stage 16B 第一版建议直接失败关闭后台执行入口，等 Stage 16C 或后续 project command routing 再决定是否支持 server-style tests。

验收必须覆盖：

```text
python server.py & -> denied 或 background_process_rejected
sleep 999 & -> denied 或 background_process_rejected
nohup pytest ... -> denied 或 background_process_rejected
Docker cleanup 后没有 session container 或 session-owned process 存活。
Local cleanup 后没有 session-owned process 存活。
正常返回的命令如果留下后台进程，样本 invalid_for_training=true。
```

### 4.10 依赖安装和每题私有环境边界

Stage 16B 比 Stage 16A 更接近真实 SWE 诊断，但依赖安装仍然必须有明确边界。

规则如下：

```text
pip / uv / npm / pnpm / yarn / conda 等命令如果写入共享依赖环境，必须拒绝。
如果写入每题私有 virtualenv、session HOME/cache 或 per-episode private environment，可以允许，但必须显式启用。
如果无法证明安装目标是每题私有环境，必须 fail closed。
如果 Stage 16B 第一版暂不实现依赖安装支持，必须返回 dependency_mutation_unsupported_in_stage16b，而不是假装完整诊断 shell 已支持依赖安装。
```

允许每题私有依赖变更时，必须记录：

```text
dependency_mutation_allowed = true
dependency_mutation_scope = session_private / per_episode_private_environment
dependency_mutation_command_family = pip / uv / npm / conda / ...
dependency_mutation_artifact_ref
shared_dependency_environment_written = false
```

这些 dependency mutation facts 可以用于诊断和后续 Stage 16.5 分析，但不能把 session HOME/cache 或私有 virtualenv 内容直接放进 final.patch、SFT target、preference pair 或 reward evidence。

## 5. 代码实施步骤

### Step 0：只读 inventory

执行前先确认当前代码形状：

```bash
rg -n "execute_bash|diagnostic_shell|run_command|cleanup_workspaces|ContainerExecutionFacts|ExecutionResult" \
  src/repo_harness tests
```

需要确认：

```text
当前是否已经存在 diagnostic_shell 工具。
execute_bash 的 Stage 16A 策略不能被 Stage 16B 修改或放宽。
workspace protocol 是否已有可扩展的 run_command 和 cleanup_workspaces。
ExecutionResult / ContainerExecutionFacts 如何记录 backend facts。
Docker adapter 是否已有 container facts artifact。
Local adapter 是否已有 runtime-private path redaction 和 shared environment guard。
```

### Step 1：新增 persistent diagnostic session schema

建议新增或扩展下面的结构：

```text
src/repo_harness/workspace/schemas.py
src/repo_harness/workspace/protocol.py
```

新增 facts 字段建议：

```text
DiagnosticSessionFacts
  schema_version
  session_id
  backend
  run_id
  task_id
  episode_id
  workspace_digest
  workspace_mount_point
  run_dir_mount_enabled
  persistent
  reused
  invalidated
  invalidation_reason
  cleanup_status
  session_state_root_ref
  shared_dependency_environment_roots_present
  local_filesystem_process_state_persistent
  workspace_projection_sync_status
  background_process_cleanup_status
  dependency_mutation_scope
  docker_container_id_runtime_private_ref
  docker_container_name_runtime_private_ref
```

`session_state_root_ref`、Docker container id 和 Docker container name 只能进入 runtime-private artifact 或 opaque projection，不允许把真实本机路径、真实 container id、真实 container name 塞进模型可见 observation、TrainingView、AgentLoopOutput 或 DataProto。

`ExecutionResult` 可以新增：

```text
diagnostic_session_facts_ref
diagnostic_session_id
diagnostic_session_backend
```

如果为了保持 schema 更窄，也可以只通过 artifact facts ref 记录，但工具 typed metadata 必须能投影 batch-safe facts。

### Step 2：新增 workspace adapter 协议方法

在 workspace protocol 中新增可选但显式的方法：

```python
run_diagnostic_command(
    workspace_path,
    command,
    *,
    timeout_sec,
    recorder,
    cwd=".",
    command_semantics="diagnostic_shell",
    artifact_metadata=None,
    session_metadata=None,
) -> ExecutionResult

cleanup_diagnostic_sessions() -> None
```

要求：

```text
不支持的 backend 必须结构化拒绝，不能 fallback 到 run_command。
run_diagnostic_command 必须写 stdout / stderr artifact。
run_diagnostic_command 必须写 session facts。
cleanup_diagnostic_sessions 必须幂等。
cleanup_workspaces 必须先或同时调用 cleanup_diagnostic_sessions。
```

### Step 3：实现 Local filesystem-persistent session

建议在下面位置实现：

```text
src/repo_harness/workspace/diagnostic_session.py
src/repo_harness/workspace/adapter.py
```

Local session state root 建议位于 run directory 之外或 runtime-private 区域，且只通过 opaque ref 记录：

```text
<system tmp>/repo-harness-diagnostic-sessions/<session_id>/
  home/
  tmp/
  cache/pip/
  cache/uv/
```

每次命令注入稳定环境变量：

```text
HOME=<session>/home
TMPDIR=<session>/tmp
TEMP=<session>/tmp
TMP=<session>/tmp
PIP_CACHE_DIR=<session>/cache/pip
UV_CACHE_DIR=<session>/cache/uv
PYTHONPYCACHEPREFIX=<session>/pycache
PYTHONDONTWRITEBYTECODE=1
PYTHONNOUSERSITE=1
```

Local backend 必须明确：

```text
local_filesystem_process_state_persistent = false
local_filesystem_state_persistent = true
```

也就是说，`touch "$TMPDIR/a"` 这种文件状态可复用；`cd subdir`、`export FOO=1`、`source .venv/bin/activate` 这种 shell 进程状态不保证复用。

Local diagnostic session 的执行目录不能是直接暴露 `.git`、`runtime_private`、`.repo_harness_env_overlay`、`.repo_harness_runtime`、`.env` 或 evaluator-only artifact 的原始宿主 workspace。实现必须先创建 diagnostic-visible writable projection，或通过 adapter 级隔离让这些路径不可见。Host-side baseline、snapshot、RunRecorder 或 workspace diff 仍然负责最终 patch capture；模型可见 projection 不需要也不允许读取 Git object database。

Local backend 还必须实现 projection 写回或唯一写视图语义：diagnostic_shell 对公开源码的修改必须进入 final verifier 和 final patch capture；session HOME/TMP/cache、诊断脚本和私有依赖环境不能进入 final.patch。

### Step 4：实现 Docker persistent session

建议在下面位置实现：

```text
src/repo_harness/workspace/docker_adapter.py
```

第一次命令前创建长期 container：

```text
docker run -d
  --name repo-harness-diag-<stable-safe-id>
  --label repo-harness.session_kind=diagnostic_shell
  --label repo-harness.run_id=<run_id>
  --label repo-harness.task_id=<task_id>
  --label repo-harness.workspace_digest=<sha256>
  --network <existing policy>
  -v <diagnostic_visible_workspace_projection>:/workspace:rw
  -w /workspace
  <image_ref>
  sleep infinity
```

后续命令：

```text
docker exec -w /workspace/<cwd> <container> sh -lc <command>
```

Docker session 必须：

```text
不挂载 run_dir。
不直接挂载含 .git / runtime_private / evaluator-only artifact 的原始 lease workspace。
只挂载 diagnostic-visible workspace projection。
projection 中的公开源码写入必须能同步回 host-side verifier / patch capture 看到的 public workspace。
记录 run_dir_mount_enabled=false。
固定 workspace mount 为 /workspace。
timeout 后 docker rm -f。
cleanup 时按 session id 和 label 删除容器。
启动时只清理 ownership scope 完全匹配且 registry 判定 stale 的 orphan container。
```

orphan cleanup 至少要匹配：

```text
run_id
task_id
episode_id 或 workspace lease id
backend
session_id
workspace_digest
```

不能只按 workspace digest 删除容器，否则两个不同 run 使用同一个 source snapshot 时可能互相删除活动容器。

Docker backend 还必须对后台进程执行失败关闭或命令后清理。如果允许任何后台进程，必须在 facts 中记录 process cleanup 结果；否则命令正常返回但留下后台进程时，样本不能进入训练。

### Step 5：工具层接入

修改：

```text
src/repo_harness/tools/minimal.py
src/repo_harness/scaffolds/patch_focused_react.py
src/repo_harness/scaffolds/registry.py
```

新增或升级：

```text
diagnostic_shell 工具定义
diagnostic_shell 输入 schema
diagnostic_shell permission metadata
diagnostic_shell model-visible prompt
diagnostic_shell tool registry
diagnostic_shell scaffold variant
```

`diagnostic_shell` 输入建议：

```text
command: string
cwd: string | null
timeout_sec: int | null
```

`cwd` 约束沿用 Stage 16A：

```text
必须是 workspace-relative。
拒绝绝对路径、..、隐藏路径、runtime-private 路径、symlink 越界。
```

工具执行必须：

```text
先做 evaluator-only / hidden marker / Git history / run_dir marker command text guard。
再调用 workspace_adapter.run_diagnostic_command。
返回脱敏 stdout / stderr 给模型。
raw stdout / stderr 只进入 recorder artifact。
typed metadata 包含 diagnostic session facts 的 batch-safe projection。
```

### Step 6：命令策略和可见性

Stage 16B 的 `diagnostic_shell` 不是 Stage 16A `execute_bash` allowlist。它可以支持真实 SWE 诊断中常见的 shell 语义，例如：

```text
cd && pytest
cat / sed / head / tail 读取 workspace 内公开文件
find workspace 内公开文件
多行 heredoc 创建本题临时复现脚本
python -c 和 python scratch script
```

但它必须继续拒绝：

```text
Git history：git log / git show / git cat-file / git grep HEAD:path / git diff @:path
run directory：/repo-harness-run、run_dir 真实路径、runtime_private
evaluator-only marker：FAIL_TO_PASS、PASS_TO_PASS、gold patch、test patch、hidden verifier、official selector
共享依赖环境写入；未显式启用 per-episode private environment 时的依赖安装
后台进程入口：&、nohup、disown、setsid、tmux、screen、daemon
越界路径：绝对宿主路径、~、.. symlink escape
网络下载，除非后续任务 metadata 显式允许并有下载审计
```

这里可以复用 Stage 16A 的 marker 检查、path redaction 和 shared dependency guard，但不要复用 Stage 16A 的最小 allowlist，否则 persistent diagnostic shell 的目标会被掐掉。

### Step 7：上下文和模型提示

修改或新增 context/scaffold 文案：

```text
diagnostic_shell 是同题持久诊断 shell。
Docker 后端：同题内 container 持久，工作区为 /workspace。
Local 后端：同题内 HOME / TMP / cache 持久，但 shell 进程状态不持久。
不要读取 /repo-harness-run。
不要读取 hidden verifier、gold patch、test patch、official selector。
不要把临时复现脚本或依赖目录当作最终 patch 目标。
```

不能把 hidden verifier、official verifier 结果、gold patch 或 test patch 写进模型可见 prompt。

### Step 8：RunRecorder 和 evidence

新增本地验收 evidence 目录：

```text
runs/repo-harness-verl-stage16b-<timestamp>/
  stage16b_acceptance_summary.json
  stage16b_command_log.sanitized.jsonl
  runtime_private/stage16b_command_log.raw.jsonl
  stage16b_diagnostic_session_report.json
  stage16b_visibility_report.json
  stage16b_cleanup_report.json
  stage16b_tool_registry_report.json
  stage16b_real_episode_smoke_report.json
```

公开 evidence 必须通过 path leak scan。runtime-private raw evidence 可以保留真实路径，但必须标记为 runtime-private，不能进入公开 summary。

Acceptance summary 至少包含：

```text
stage = 16B
code_commit
git_status_short
docker_backend_tested
local_backend_tested
same_task_session_reuse_passed
cross_task_session_isolation_passed
timeout_invalidation_passed
cleanup_passed
keep_workspace_cleanup_passed
background_process_cleanup_passed
workspace_projection_sync_passed
diagnostic_temp_artifact_excluded_from_final_patch = true
run_dir_mount_enabled_any = false
run_dir_path_leak_detected = false
runtime_private_path_leak_detected = false
git_metadata_visible_to_diagnostic_shell = false
shared_dependency_write_guard_passed
dependency_mutation_scope_valid
hidden_evaluator_guard_passed
public_path_leak_scan_passed
real_episode_smoke_passed
```

## 6. 测试计划

### 6.1 新增测试文件

建议新增：

```text
tests/unit/test_repo_harness_stage16b_diagnostic_session_schema.py
tests/unit/test_repo_harness_stage16b_local_diagnostic_session.py
tests/unit/test_repo_harness_stage16b_diagnostic_shell_tool.py
tests/unit/test_repo_harness_stage16b_session_visibility.py
tests/integration/test_repo_harness_stage16b_docker_diagnostic_session.py
tests/integration/test_repo_harness_stage16b_real_episode_smoke.py
```

如果 Docker 在当前本地环境不可用，Docker integration 可以使用 `pytest.importorskip` 或明确 skip，但不能把 Docker lifecycle 标记为通过。Stage 16B 最终验收必须在至少一个 Docker 可用环境中证明 Docker session 生命周期，或者在 acceptance summary 中明确 `docker_backend_tested=false` 且 Stage 16B 不标记 complete。

### 6.2 Local backend 必测项

```text
同一 episode 两次 diagnostic_shell 使用同一个 session_id。
两次命令的 HOME / TMPDIR / PIP_CACHE_DIR / UV_CACHE_DIR 一致。
第一次命令写入 TMPDIR marker，第二次能读到。
第一次命令写入 workspace marker，第二次能读到。
cleanup 后 local session directory 不存在或被标记为 cleaned。
cleanup 后同路径新 episode 不能继承旧 session marker。
hidden-evaluator / final-only task metadata 下 local diagnostic_shell 被拒绝。
共享依赖环境 roots 缺失时 fail closed。
共享依赖环境 roots 存在时，写入 roots 的命令被拒绝。
stdout / stderr 中 session state root、run_dir、workspace host path 被脱敏。
diagnostic shell 可见 workspace 中 `.git` 对象库不可读。
diagnostic shell 可见 workspace 中 runtime_private、.repo_harness_env_overlay、.repo_harness_runtime、.env 不可见。
diagnostic_shell 修改公开源码后，final verifier 和 final.patch 能看到该修改。
diagnostic_shell 创建 session HOME/TMP/cache 或诊断脚本后，final.patch 不包含这些诊断文件。
后台进程入口被拒绝，或命令后 session-owned process tree 被清理。
依赖安装如果未显式落到 per-episode private environment，则被结构化拒绝。
```

### 6.3 Docker backend 必测项

```text
同一 episode 两次 diagnostic_shell 进入同一个 container。
不同 episode 或不同 workspace digest 不复用 container。
container 内 /workspace 文件修改持久。
container 内 /tmp marker 持久。
container 内不存在 /repo-harness-run。
mount 输出不包含 run directory。
container 内 `.git` 对象库不可读或不存在。
container 内 runtime_private、.repo_harness_env_overlay、.repo_harness_runtime、.env 不可见。
container 内修改公开源码后，host-side final verifier 和 final patch capture 能看到修改。
timeout 后 container 被 docker rm -f。
timeout 后 session_invalidated=true。
timeout 后后续命令不能复用旧 container。
keep_workspace=True 时 container 仍会被清理。
后台进程入口被拒绝，或 container cleanup 后无 session-owned process 存活。
orphan label cleanup 只能清理 ownership scope 完全匹配且 registry 判定 stale 的旧 container。
ContainerExecutionFacts / DiagnosticSessionFacts 记录 run_dir_mount_enabled=false。
```

### 6.4 工具层和可见性测试

```text
diagnostic_shell 出现在专用 scaffold 的 model-visible tool schema 中。
默认 Stage 16A execute_bash scaffold 不自动暴露 diagnostic_shell。
ToolRegistry 和 ToolExecutor 都能执行 diagnostic_shell。
provider / verl tool schema snapshot 包含 diagnostic_shell 的正确输入 schema。
diagnostic_shell 输出进入模型前已脱敏。
raw command artifact 不进入 TrainingView / AgentLoopOutput / DataProto。
命令文本包含 gold_patch、test_patch、FAIL_TO_PASS、PASS_TO_PASS、hidden_verifier 时拒绝。
命令尝试 git log、git show、git cat-file、git grep HEAD:path 时拒绝。
命令尝试通过 cat / find / Python 读取 .git 时拒绝或只能看到不可读占位。
命令尝试通过 cat / find / Python 读取 runtime_private、.repo_harness_env_overlay、.repo_harness_runtime、.env 时拒绝或只能看到不可读占位。
命令尝试启动后台进程时拒绝或标记为 background_process_rejected。
命令尝试写共享依赖环境时拒绝；写每题私有环境时必须有 dependency mutation facts。
```

### 6.5 real_episode smoke

准备 2 到 3 个极小任务：

```text
diagnostic_session_tmp_marker：
  第一轮 diagnostic_shell 写 TMPDIR marker。
  第二轮 diagnostic_shell 读取 marker。
  edit_file 修复极小 bug。
  final verifier accepted。

diagnostic_session_workspace_marker：
  第一轮 diagnostic_shell 写 workspace 复现脚本。
  第二轮 diagnostic_shell 运行该复现脚本。
  final patch 不包含诊断脚本。

diagnostic_session_source_writeback：
  diagnostic_shell 修改公开源码。
  final verifier 能看到该修改。
  final.patch 包含该公开源码修改。
  session HOME/TMP/cache 文件不进入 final.patch。

diagnostic_session_cleanup_negative：
  人工触发 timeout。
  session invalidated。
  样本标记为 diagnostic failure，不进入 policy loss。

diagnostic_session_background_process_negative：
  diagnostic_shell 尝试 `sleep 999 &` 或 `nohup pytest ...`。
  命令被结构化拒绝，或 cleanup 后无 session-owned process 存活。
  样本不进入 policy loss。
```

真实链路必须覆盖：

```text
RepoHarnessVerlAgentLoop
-> real_episode
-> diagnostic_shell
-> edit_file
-> final verifier
-> TrainingView / AgentLoopOutput
```

## 7. 前置回归命令

现有前置回归建议：

```bash
PYTHONPATH=src uv run --extra dev python -m pytest -q \
  tests/unit/test_command_policy.py \
  tests/unit/test_repo_harness_stage16a_execute_bash.py \
  tests/unit/test_scaffold_patch_focused_react.py \
  tests/unit/test_tools.py \
  tests/unit/test_workspace_command_output_artifacts.py \
  tests/unit/test_repo_harness_rl_stage12_5_command_environment.py \
  tests/unit/test_repo_harness_rl_stage11_5_real_episode_runtime.py \
  tests/unit/test_repo_harness_verl_stage15_2_agent_loop_partial.py \
  tests/integration/test_workspace_lifecycle.py
```

Docker 可用时追加：

```bash
PYTHONPATH=src uv run --extra dev python -m pytest -q \
  tests/integration/test_docker_backend_e2e.py
```

基础检查：

```bash
PYTHONPATH=src uv run --extra dev python -m compileall -q src

PYTHONPATH=src uv run --extra dev python - <<'PY'
import sys
import repo_harness.rl
import repo_harness_verl
loaded = [name for name in ("verl", "torch", "ray", "tensordict") if name in sys.modules]
print("ordinary_import_ok", loaded)
PY

if rg -n '(^|\s)(import|from)\s+verl' \
  src/repo_harness/rl src/repo_harness/agent_loop src/repo_harness/workspace src/repo_harness/verifier; then
  exit 1
else
  echo no_core_verl_imports
fi

git diff --check -- \
  docs/agentic_RL/repo_harness_verl_workstreams/35-stage-16b-execution-plan.md \
  src/repo_harness \
  tests
```

## 8. 提交边界

Stage 16B 提交应只包含：

```text
persistent diagnostic session schema / facts
workspace protocol 方法
local filesystem-persistent session backend
Docker persistent diagnostic session backend
diagnostic_shell tool / scaffold / schema
context builder 的模型可见说明更新
Stage 16B 测试
Stage 16B 本地 evidence
```

不应混入：

```text
Stage 16C public environment prompt builder
Stage 16D official verifier healthcheck
Stage 16E patch hygiene
Stage 16.5 代表性诊断
Stage 17 数据 registry
reference/verl 修改
无关 HTML 汇报页
Vast.ai CLI 文档修改
```

## 9. 子代理复核问题

Stage 16B 实现完成后，子代理必须重点检查：

```text
1. Stage 16B 是否无意放宽了 Stage 16A execute_bash allowlist。
2. Docker session 是否可能看到 run directory、hidden verifier、gold patch、test patch 或 official selector。
3. Docker / Local diagnostic shell 是否可能读取 `.git` 对象库或 Git refs / logs。
4. Docker / Local diagnostic shell 是否可能读取 runtime_private、.repo_harness_env_overlay、.repo_harness_runtime、.env 或 symlink escape。
5. diagnostic-visible projection 写入的公开源码变更是否能被 final verifier 和 final patch capture 看到。
6. diagnostic-only 临时脚本、session HOME/TMP/cache、私有依赖环境是否被排除在 final.patch、SFT target 和 reward evidence 外。
7. Local session 是否可能污染共享依赖环境或宿主 HOME / TMP / cache。
8. 依赖安装命令是否只允许写入 per-episode private environment，并且记录 dependency mutation facts。
9. 后台进程入口是否被拒绝，或命令后 / cleanup 后没有 session-owned process 存活。
10. timeout 后是否一定 invalidates session，且不会继续复用状态不明的 container 或 local session。
11. keep_workspace=True 时是否仍会清理 active diagnostic session。
12. 不同题、不同 run、不同 workspace digest 是否严格隔离。
13. orphan cleanup 是否只清理 ownership scope 完全匹配且 stale 的 session。
14. raw artifact 和 model-visible observation 是否正确分层，公开 evidence 是否通过 path leak scan。
15. 使用 diagnostic_shell 的 real_episode 样本是否仍然通过 visibility、reward boundary 和 formal online RL gate。
```

## 10. 进入 Stage 16C 的条件

只有满足下面条件，才进入 Stage 16C：

```text
Local filesystem-persistent session 生命周期通过。
Docker persistent session 生命周期在 Docker 可用环境中通过，或明确未完成且不标记 Stage 16B complete。
同题复用、跨题隔离、timeout invalidation、cleanup 和 keep_workspace cleanup 都有测试。
projection 写回语义有测试：diagnostic_shell 源码修改可被 final verifier / final patch capture 看到，诊断临时文件不会进入 final.patch。
后台进程入口或残留进程清理有测试。
依赖安装范围有测试：共享环境写入拒绝，每题私有环境写入必须有 facts。
run_dir_mount_enabled=false 有机器可读 evidence。
hidden evaluator / Git history / shared dependency write guard 对 diagnostic_shell 仍然生效。
diagnostic_shell 模型可见 workspace 不暴露可读 `.git` object database、refs 或 logs。
diagnostic_shell 模型可见 workspace 不暴露 runtime_private、.repo_harness_env_overlay、.repo_harness_runtime、.env 或 symlink escape。
cleanup failed、timeout invalidated、projection sync failed 或 background process uncertain 的样本不能进入 policy loss。
至少一个 real_episode smoke 使用 diagnostic_shell 完成 final verifier accepted。
Stage 16A execute_bash 安全最小工具面没有被放宽。
```
