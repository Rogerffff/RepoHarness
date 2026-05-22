# Stage 16A 执行计划：工具动作空间与防泄漏边界

本文是 Stage 16A 的具体执行计划。它承接
`docs/agentic_RL/training_design/post_stage15_training_infra_stage_plan.md` 中
Stage 16A 的高层路线，并建立在 Stage 15.2 已经跑通
`partial_rollout=True` 远端 smoke 的基础上。

Stage 16A 的目标不是扩大训练规模，也不是一次性修完所有 SWE-Bench 评测差距。
它的目标是把正式训练主线中模型可见的 shell 类工具协议先固定下来，并建立
一个安全最小 `execute_bash` 工具面。这个工具面要能进入 `real_episode` 和 verl
训练链路，但不能把完整产品态 Bash、persistent shell、任意项目命令或任意 Python
复现脚本一次性放开。Stage 16A 的核心是先封住 Git 历史、hidden verifier、run
directory、共享依赖环境、隐藏路径、runtime-private 路径和越界路径等泄漏边界。

Stage 16A 通过后，后续 Stage 16B 才继续处理 persistent diagnostic session
生命周期；Stage 16C 处理公开环境提示；Stage 16D 处理 official verifier
healthcheck；Stage 16E 处理 patch hygiene。

## 1. 阶段目标和非目标

### 1.1 必须完成的目标

Stage 16A 必须完成下面几件事：

1. 明确正式训练主线里的模型可见 shell 工具名称和协议。
   第一版默认使用 `execute_bash` 作为正式训练工具名。另一个 worktree 中的
   `diagnostic_shell` 可以作为实现参考或兼容别名，但不能继续以
   “score gap diagnostic” 的语义直接进入正式训练主线。
2. 明确 `execute_bash` 第一版是安全最小 shell 面，而不是完整 persistent shell。
   它只允许经过 command policy 证明可审计、可脱敏、不会污染共享依赖环境的命令。
3. 把 Claude Code 式工具分工写入正式训练 scaffold：

   ```text
   读文件 -> read_file
   搜索 -> grep 或 list_files / glob_files
   编辑 -> edit_file
   查看补丁 -> git_diff
   测试和复杂诊断 -> execute_bash 的安全最小子集，后续再接 run_public_tests / persistent shell
   ```

   因此，Stage 16A 不应为了追平 `diagnostic_shell` 轨迹而直接允许 `cat`、`sed`、
   `find`、`grep -R`、`cat > /tmp/*.py`、`bash -lc source conda ...`、`pip install`
   或任意项目命令。
4. 建立统一 command policy，允许 Stage 16A 内可证明安全的少量命令，例如：

   ```text
   受限 rg / grep
   git diff
   git status
   git grep
   git ls-files
   pytest / python -m pytest / python -m unittest
   受限 python -c / 强引用 Python heredoc
   ```

   同时拒绝历史、隐藏、越界、runtime-private、共享环境污染、环境路径枚举和二次执行行为。
5. 确保模型可见工具注册表、provider / verl tool schema、AgentLoop 实际执行注册表
   三者一致。
6. 为 shell 工具输出建立 visibility 和 path leak 检查。模型可以看到公开 stdout /
   stderr，但不能看到 runtime-private path、run directory、hidden verifier 或
   evaluator-only 字段。
7. 保留旧 `bash` / `diagnostic_shell` 相关路径的兼容解释，避免破坏另一个 worktree
   正在进行的 SWE-Bench 测评。

### 1.2 本阶段不做

Stage 16A 不做下面这些事情：

- 不实现完整 persistent diagnostic session 生命周期。这个属于 Stage 16B。
- 不实现 public environment context builder 和模型行为提示优化。这个属于 Stage 16C。
- 不实现 official image / gold patch / no-op healthcheck。这个属于 Stage 16D。
- 不实现 patch hygiene 的最终过滤策略。这个属于 Stage 16E。
- 不迁移旧 `repo-harness run-task`、`run-batch` 或离线 export 主实现。这个属于 Stage 19.5。
- 不改变 Stage 15.2 的 fully async / partial rollout 训练语义。
- 不把 `execute_bash` 扩成完整产品态 Bash。多行脚本、`cd && ...`、任意 `cat` / `sed`、
  任意 `find`、任意临时脚本、依赖安装、项目构建命令和完整 persistent shell 都必须在
  Stage 16B 或后续受控工具阶段单独验收。
- 不把 shell 开成无限制 root shell。它仍然必须受 workspace、timeout、资源限制、
  command policy、visibility scan 和 artifact audit 约束。

## 2. 输入材料和同步边界

### 2.1 需要参考的本 worktree 文档

本阶段以这些文档为主要依据：

```text
docs/agentic_RL/training_design/post_stage15_training_infra_stage_plan.md
docs/agentic_RL/training_design/RL_algorithm_design.md
docs/agentic_RL/training_design/实验设计.md
docs/agentic_RL/repo_harness_verl_workstreams/19-stage-12-5-execution-plan.md
docs/agentic_RL/repo_harness_verl_workstreams/33-stage-15-2-execution-plan.md
```

其中 Stage 12.5 的共享依赖环境保护边界仍然有效。Stage 16A 只允许受限 inline
Python，用于轻量诊断；文件读取、路径枚举、环境枚举、共享依赖环境探测或运行时私有路径探测，
必须通过结构化工具或后续受控 launcher 处理，不能通过裸 `python -c` 放开。

### 2.2 需要参考的另一个 worktree

另一个 worktree 路径：

```text
/Users/roger/Desktop/claude-code
```

重点参考：

```text
/Users/roger/Desktop/claude-code/docs/resume/swebench-verified-score-gap-investigation-progress.md
/Users/roger/Desktop/claude-code/docs/resume/pre-verl-persistent-diagnostic-session-implementation-plan.md
/Users/roger/Desktop/claude-code/src/repo_harness/tools/minimal.py
/Users/roger/Desktop/claude-code/src/repo_harness/workspace/adapter.py
/Users/roger/Desktop/claude-code/src/repo_harness/workspace/docker_adapter.py
/Users/roger/Desktop/claude-code/src/repo_harness/workspace/protocol.py
/Users/roger/Desktop/claude-code/src/repo_harness/scaffolds/patch_focused_react.py
/Users/roger/Desktop/claude-code/tests/unit/test_tools.py
/Users/roger/Desktop/claude-code/tests/unit/test_scaffold_patch_focused_react.py
```

执行时不能盲目同步整个 worktree。必须先生成只读 diff / inventory，明确：

```text
需要迁移的能力
不需要迁移的诊断-only 能力
会和 Stage 12.5 / Stage 15.2 冲突的旧实现
需要重新命名或重包一层的接口
```

`reference/verl` 子模块改动仍然不属于 Stage 16A 同步范围。

## 3. 核心设计决策

### 3.1 模型可见工具名

第一版正式训练工具名固定为：

```text
execute_bash
```

原因：

1. `diagnostic_shell` 这个名字带有 score-gap 排查语义，不适合作为正式训练工具名。
2. `execute_bash` 更接近模型需要理解的动作含义。
3. 后续可以保留 `diagnostic_shell` 作为 legacy / diagnostic alias，但正式 RL scaffold、
   provider tool schema 和 verl tool parser 应优先暴露 `execute_bash`。

### 3.2 Stage 16A 与 Stage 16B 的分界

Stage 16A 负责：

```text
工具 schema
命令策略
泄漏防护
输出脱敏
可见注册表 / 执行注册表一致性
安全最小 shell 执行事实
结构化工具优先原则
```

Stage 16B 负责：

```text
同题 session 复用
Docker persistent container 生命周期
local filesystem-persistent session 生命周期
timeout 后 session invalidation
session cleanup
```

因此，Stage 16A 可以为 `execute_bash` 记录 session 相关字段，但不能把完整
persistent session 生命周期作为本阶段通过条件。

### 3.3 与 Claude Code 工具系统的对齐口径

对照 `reference/claude-code-typescript-src`，Claude Code 的工具系统不是只给模型一个
万能 Bash。它同时暴露 `Read`、`Grep`、`Glob`、`Edit`、`Write` 和 `Bash` 等工具，并在
`BashTool` 提示词中明确要求：

```text
Read files: Use Read (NOT cat/head/tail)
Edit files: Use Edit (NOT sed/awk)
Write files: Use Write (NOT echo >/cat <<EOF)
```

`GrepTool` 也明确要求搜索任务使用 `Grep`，不要通过 Bash 调 `grep` 或 `rg`。因此
RepoHarness 的正式训练工具面也应采用同样分层：

```text
read_file / grep / list_files 或 glob_files / edit_file / git_diff 是高频动作主路径。
execute_bash 是少量 shell 诊断和测试入口的安全最小子集。
persistent diagnostic shell、run_public_tests、python_probe 和 project command routing 是后续阶段。
```

这里的 `grep` 指的是 harness-owned 结构化搜索工具或 safe grep 工具，不是
`execute_bash` 中裸露的系统 `grep` 命令。Stage 16A 中允许的裸 `rg` / `grep`
只是极窄的过渡子集，只能用于公开 workspace-relative 搜索；它不能替代后续主路径里的
结构化搜索工具，也不能通过 shell 参数自行放开隐藏文件、ignore bypass、递归目录搜索、
pattern file 或 runtime-private 路径。

这不是为了增加模型学习负担，而是为了减少模型在 shell 语法、权限绕过、路径泄漏和工具误用上的
训练噪声。执行 agent 在 Stage 16A 中不应通过无限追加 denylist 的方式，把完整 shell
能力塞进 `execute_bash`。

### 3.4 inline Python 的安全口径

Stage 16A 可以允许轻量 inline Python，例如：

```bash
python -c "print('ok')"
python -c "import os; print(os.getcwd())"
python - <<'PY'
print('$literal')
PY
```

但下列行为不能通过 Stage 16A 的裸 inline Python 放开：

```text
枚举 os.environ
枚举 sys.path / site.getsitepackages() / sysconfig.get_paths()
通过 importlib / __import__ 探测环境
通过 subprocess 间接调用 git history 命令
读取 open(...) / pathlib.Path(...).read_text()
枚举 os.listdir / os.walk / Path.rglob
pip / uv / npm / pnpm / yarn 写共享环境
读取 .repo_harness_env_overlay
读取 .repo_harness_runtime
读取 run directory
```

第一版可以采用保守策略：

1. 普通 workspace shell 中只允许轻量 inline Python，输出必须经过 path redaction。
2. 文件读取、路径枚举、环境探测类 Python 命令必须改用结构化工具或后续受控 launcher。
3. 任何 shell stdout / stderr artifact 都必须统一脱敏。

### 3.5 Stage 16 子阶段边界

当前 Stage 16 被拆成多个可单独验收的阶段。Stage 16A 的实现和测试只能覆盖第一行的范围，
不能把后续阶段的能力提前伪装成已经完成。

```text
Stage 16A：
  固定 execute_bash schema、工具注册表一致性、安全最小 shell allowlist、拒绝语义、
  stdout / stderr 脱敏、Git history / evaluator-only / runtime-private / shared environment 防泄漏。

Stage 16B：
  persistent diagnostic session 生命周期，包括 Docker persistent session、
  local filesystem-persistent session、同题复用、跨题隔离、timeout invalidation 和 cleanup。

Stage 16C：
  public environment context builder、公开测试入口提示、run_public_tests / run_project_test
  或 task-declared project command 的受控 routing。

Stage 16D：
  official verifier、gold patch healthcheck、no-op / empty patch healthcheck、
  proxy verifier 与 official verifier 差异治理。

Stage 16E：
  patch hygiene，过滤 patch.txt、*.orig、临时备份、仓库内依赖目录和诊断脚本产物，
  防止它们进入 final.patch、SFT target、preference pair 或 reward evidence。

Stage 16.5：
  20 到 30 题代表性 harness 诊断扩展，用真实任务统计权限误拦截、验证环境问题、
  patch hygiene 问题和 proxy / official verifier disagreement。
```

因此，Stage 16A 的通过条件是“安全最小 `execute_bash` 可以进入
`real_episode` 和 verl tool schema，并且防泄漏边界可机器验收”。Stage 16A 通过
不代表完整 shell、持久 shell、项目公开测试 routing、受控 Python 复现工具或 official verifier
健康检查已经完成。

## 4. 实施步骤

### Step 0：只读 inventory 和同步计划

新增或生成一份 Stage 16A inventory，建议输出到：

```text
runs/repo-harness-verl-stage16a-<timestamp>/stage16a_sync_inventory.json
```

内容至少包含：

```text
source_worktree
candidate_files
candidate_tests
capability_name
source_symbol
target_symbol
sync_action
reason
risk
```

`sync_action` 取值建议：

```text
reuse_as_is
adapt_and_rename
rewrite_for_rl_runtime
diagnostic_only_do_not_sync
defer_to_stage16b
defer_to_stage16c
```

此步骤只读，不改代码。

### Step 1：定义 `execute_bash` 工具协议

需要在工具层新增或重包正式协议：

```text
tool_name = execute_bash
arguments:
  command: string
  cwd: string | null
  timeout_sec: int | null
  purpose: string | null
```

`cwd` 是高风险字段，第一版必须采用 fail-closed 规则：

```text
cwd 必须是 workspace-relative path。
cwd 不能是绝对路径。
cwd 不能包含 .. 路径穿越。
cwd 不能指向 home、run directory、runtime-private path 或共享依赖环境。
cwd resolve 后必须仍位于当前 episode workspace 内。
cwd 中任何 symlink 越界都必须拒绝。
```

模型可见说明必须包含：

```text
默认从仓库根目录执行
优先使用相对路径
可以运行公开测试和自写复现
可以使用 git diff / git status 检查自己的改动
不能访问 Git 历史
不能访问 hidden verifier / gold patch / test patch / official selector
不能读取 RepoHarness run directory
不能向共享依赖环境写入
```

工具结果 typed facts 至少包含：

```text
shell_execution = true
command_policy_decision
command_category
timeout_sec
exit_code
stdout_artifact_ref
stderr_artifact_ref
stdout_truncated
stderr_truncated
path_redaction_applied
run_dir_mount_enabled
shared_dependency_write_blocked
```

如果底层使用 legacy `diagnostic_shell` 实现，typed facts 必须同时记录：

```text
legacy_backend = diagnostic_shell
formal_tool_name = execute_bash
```

### Step 2：实现统一 command policy

命令策略必须区分 allow、deny 和 diagnostic-only。

共享依赖环境写保护不能只靠模型可见文本或字符串猜测。执行层必须从 runtime-only
facts 获取共享依赖环境根路径：

```text
shared_dependency_environment_roots
shared_dependency_environment_ref
dependency_environment_mode
overlay_environment_ref
```

这些 facts 不能从模型可见字段、命令输出或 shell 环境变量中反推。如果当前 episode
声明使用共享依赖环境，但 runtime 没有提供可校验的
`shared_dependency_environment_roots`，必须禁用共享依赖环境复用，退回每个 episode
私有环境或结构化拒绝，不能静默放开写入。

第一版允许的是安全最小 shell 面，而不是完整产品态 Bash：

```text
git diff / git status / git grep / git ls-files 的安全子集
pytest / python -m pytest / python -m unittest 的 workspace-relative 公开目标
受限 rg / grep 搜索，不允许隐藏文件、ignore bypass、follow symlink 或递归 grep
轻量 python -c / 强引用 Python heredoc，只允许 print、字面量、os.getcwd() 等安全诊断
```

第一版拒绝：

```text
任意 cat / sed / awk / ls / find / shell script / Python script 执行
多行 shell、未引用命令组合符、动态 shell 展开、管道二次解释器、输入重定向执行
项目构建脚本、项目 package script、task-declared command 的裸执行
git log
git show
git cat-file
git rev-list
git reflog
git checkout
git switch
git reset
git cherry-pick
git format-patch
git merge-base
git branch
git tag
直接读取 .git/**
读取 /repo-harness-run 或 run directory
读取 hidden verifier / official verifier evidence
读取 gold patch / test patch / FAIL_TO_PASS / PASS_TO_PASS selector
访问 workspace 外路径
写共享依赖环境
写 runtime-private overlay
网络下载或 curl/wget 访问外网，除非任务环境显式允许
读取或枚举环境变量、sys.path、site package 路径、runtime-private 路径、共享依赖环境路径
```

必须包含 false-positive 回归：

```text
test_patches.py 这类公开文件名不能因为包含 test_patch 子串而被拒绝
普通 pytest 路径不能因为 tests 名称被误判为 hidden tests
git diff / git status 不能因为使用 git 命令被误判为 Git 历史访问
```

### Step 3：接入 workspace execution 和输出脱敏

`execute_bash` 的底层执行必须经过 workspace adapter，不允许直接绕过 recorder 或
artifact system。

Stage 16A 第一版不能在普通 `local_process` 后端中默认启用 `execute_bash`。原因是本地
`subprocess` 即使初始 `cwd` 在 workspace 内，shell 或 inline Python 仍然可以通过动态
路径计算访问 run directory、宿主虚拟环境或其他 workspace 外文件。普通 Docker 后端如果
仍把完整 run directory 挂载到容器内，也不能算作安全后端。正式路径必须使用 workspace-only
mount 的 Docker 执行模式或等价受控 launcher，并由 runtime-only facts 标记
`execute_bash_workspace_isolation_verified=true`。仅单元测试可以通过 runtime-only 测试标记
临时允许未隔离本地执行，且该标记不能来自模型可见输入。

shell 输出必须分成两层：

```text
model_visible_observation:
  脱敏、截断、经过 visibility scan 的 stdout / stderr 摘要。
  可以进入下一轮模型上下文。

raw_command_artifact:
  runtime-private 或受限 audit artifact。
  可以保留完整 stdout / stderr 供本地审计。
  默认不能进入 TrainingView、AgentLoopOutput、DataProto、SFT export、preference export
  或公开 evidence。
```

任何从 raw artifact 投影到模型可见 observation 的路径，都必须记录 redaction 和
truncation facts。

需要检查并补齐：

```text
LocalWorkspaceAdapter.run_command(...)
DockerWorkspaceAdapter.run_command(...) 或 run_diagnostic_command(...)
RunRecorder artifact 写入
stdout / stderr / combined command_output artifact
ResourceSummary.tool_seconds
TimingSummary.tool_seconds
```

输出脱敏至少覆盖：

```text
本机绝对路径，例如 /Users/roger/...
远端绝对路径，例如 /workspace/...
run directory 路径
.repo_harness_env_overlay
.repo_harness_runtime
共享依赖环境真实路径
hidden verifier artifact 路径
official verifier evidence 路径
```

如果某些 raw artifact 为 runtime-private 保留真实路径，必须标记为
`runtime_private`，不能进入 TrainingView、AgentLoopOutput、DataProto、
SFT export 或公开 evidence。

### Step 4：接入 AgentLoop / real_episode / tool schema snapshot

需要保证下面几处看到同一套工具事实：

```text
scaffold.allowed_tools
ToolRegistry
ToolExecutor
provider / verl tool schema
AgentLoop allowed_tool_definitions
Run metadata tool schema snapshot
TrainingView.extra_fields 中的 batch-safe tool facts
```

Stage 16A 必须新增工具注册表一致性检查：

```text
visible_tool_names == executable_tool_names
execute_bash in visible_tool_names
execute_bash in executable_tool_names
legacy diagnostic_shell 不在正式 RL scaffold 默认工具列表中，除非明确是 diagnostic profile
```

同时需要确保 `RepoHarnessVerlAgentLoop` 的真实模型 tool parser 能接受
`execute_bash` 工具调用，并继续对工具参数做 Stage 10 / Stage 12-A 已有的递归
visibility 检查。

### Step 5：最小 real_episode smoke

Stage 16A 的 smoke 不要求 20 到 30 题代表性诊断。它只证明链路可跑。

建议准备 3 到 5 个极小任务：

```text
execute_bash_runs_safe_pytest
execute_bash_runs_lightweight_python_diagnostic
execute_bash_reports_git_diff_after_edit
shell_blocks_git_history
shell_blocks_hidden_marker
```

其中前 3 个是正例，后 2 个是受控负例。

正例必须证明：

```text
RepoHarnessVerlAgentLoop
-> real_episode
-> execute_bash
-> edit_file 或受控代码修改
-> pytest / python -m pytest / git diff 等 Stage 16A allowlist 内命令
-> final verifier 或最小 verifier
-> TrainingView / AgentLoopOutput
```

负例必须证明：

```text
被拒绝的 shell 行为不会执行
拒绝原因结构化
拒绝输出不泄漏 hidden 内容
样本默认不能进入 policy loss
```

## 5. 测试计划

### 5.1 新增测试建议

本阶段当前实现可以集中在这些测试文件中：

```text
tests/unit/test_command_policy.py
tests/unit/test_repo_harness_stage16a_execute_bash.py
tests/unit/test_scaffold_patch_focused_react.py
```

其中 `test_repo_harness_stage16a_execute_bash.py` 必须清楚覆盖 schema、policy、
visibility、工具执行和 AgentLoop smoke；`test_command_policy.py` 固定通用命令策略；
`test_scaffold_patch_focused_react.py` 固定正式 scaffold 的工具暴露边界。

### 5.2 必须覆盖的正例

```text
execute_bash 允许 python -m pytest / pytest 的 workspace-relative 公开测试目标
execute_bash 允许轻量 inline Python 诊断，例如 print、os.getcwd、字面量输出
execute_bash 允许强引用 Python heredoc 中的轻量字面量诊断
execute_bash 允许 git diff
execute_bash 允许 git status
execute_bash 允许 git grep
execute_bash 允许 git ls-files
execute_bash 允许受限 rg / grep 搜索公开 workspace-relative 路径
execute_bash stdout / stderr artifact 进入 recorder 并被脱敏
provider / verl tool schema 中出现 execute_bash
ToolRegistry 和 ToolExecutor 都能执行 execute_bash
```

### 5.3 必须覆盖的负例

```text
git log 被拒绝
git show 被拒绝
git cat-file 被拒绝
直接读取 .git/HEAD 被拒绝
命令文本包含 gold_patch 被拒绝
命令文本包含 FAIL_TO_PASS / PASS_TO_PASS 被拒绝
读取 /repo-harness-run 被拒绝
读取 workspace 外绝对路径被拒绝
写共享依赖环境被拒绝
写 .repo_harness_env_overlay 被拒绝
python subprocess 间接调用 git log 被拒绝或被结构化标记
rg --hidden / --no-ignore / --unrestricted / -uu / --follow 被拒绝
rg -g.env / rg --glob .env / grep -R / grep -d recurse 被拒绝
python open / pathlib read_text / os.listdir / os.walk / Path.rglob 被拒绝
python sys.path / site.getsitepackages / sysconfig.get_paths 等环境路径枚举被拒绝
命令输出中的 runtime-private path 被脱敏
```

inline Python 负例必须显式覆盖：

```bash
python -c "import os; print(os.environ)"
python -c "import sys; print(sys.path)"
python -c "__import__('subprocess').run(['git','log'])"
python - <<'PY'
from pathlib import Path
Path('/envs/shared-python').write_text('x')
PY
```

最后一个用例中的 `/envs/shared-python` 在实际测试中应替换为 runtime-only facts
提供的共享依赖环境根路径。测试不能把真实共享环境路径写进模型可见 fixture。

### 5.4 false-positive 回归

必须证明下面这些公开行为不会被误拦截：

```text
python -m pytest -q lib/matplotlib/tests/test_patches.py
rg "test_patch" docs/public_note.txt
git diff -- src/example.py
git status --short
git grep "FAIL_TO_PASS" -- docs/public_readme.md
```

其中 `git grep "FAIL_TO_PASS"` 的处理需要谨慎：如果 grep 的目标文件和输出是公开文件，
命令不应仅因 query 字符串被拒绝；但如果命令尝试读取 evaluator-only selector artifact，
必须拒绝。执行计划实施时需要把“公开文本搜索”和“hidden selector 访问”区分开。

## 6. 验收 evidence

Stage 16A 完成后建议生成：

```text
runs/repo-harness-verl-stage16a-<timestamp>/
  stage16a_acceptance_summary.json
  stage16a_sync_inventory.json
  stage16a_command_policy_matrix.json
  stage16a_tool_registry_consistency_report.json
  stage16a_visibility_report.json
  stage16a_real_episode_smoke_report.json
  stage16a_command_log.sanitized.jsonl
  runtime_private/stage16a_command_log.raw.jsonl
```

`stage16a_acceptance_summary.json` 至少包含：

```text
stage = stage16a
execute_bash_schema_present
execute_bash_visible_to_model
execute_bash_executable
tool_registry_consistency_passed
command_policy_positive_case_count
command_policy_negative_case_count
command_policy_false_positive_regression_passed
path_leak_scan_passed
hidden_marker_leak_scan_passed
real_episode_smoke_count
real_episode_smoke_passed_count
diagnostic_profile_legacy_tools_present
formal_rl_profile_legacy_diagnostic_shell_excluded
```

## 7. 验收命令

本地基础检查：

```bash
PYTHONPATH=src uv run --extra dev python -m compileall -q src
git diff --check -- \
  src/repo_harness \
  src/repo_harness_verl \
  tests \
  docs/agentic_RL/repo_harness_verl_workstreams/34-stage-16a-execution-plan.md
```

Stage 16A focused tests：

```bash
PYTHONPATH=src uv run --extra dev python -m pytest -q \
  tests/unit/test_command_policy.py \
  tests/unit/test_repo_harness_stage16a_execute_bash.py \
  tests/unit/test_scaffold_patch_focused_react.py
```

关键前置回归：

```bash
PYTHONPATH=src uv run --extra dev python -m pytest -q \
  tests/unit/test_tools.py \
  tests/unit/test_repo_harness_rl_stage12_5_command_environment.py \
  tests/unit/test_repo_harness_verl_stage12b_tool_parser.py \
  tests/unit/test_repo_harness_verl_stage11_gateway.py \
  tests/unit/test_repo_harness_rl_stage11_5_real_episode_runtime.py \
  tests/unit/test_repo_harness_verl_stage15_2_agent_loop_partial.py
```

如果某个测试文件在当前 worktree 尚不存在，实施时必须先新增对应测试，或者在执行报告中明确列出替代测试文件和覆盖关系。

普通导入边界：

```bash
PYTHONPATH=src uv run --extra dev python - <<'PY'
import sys
import repo_harness.rl
import repo_harness_verl

loaded = set(sys.modules)
for forbidden in ("verl", "torch", "ray", "tensordict"):
    if forbidden in loaded:
        raise SystemExit(f"unexpected heavy import: {forbidden}")
print("ordinary_import_ok")
PY
```

RepoHarness core 不能直接依赖 verl：

```bash
if rg -n '(^|\s)(import|from)\s+verl' \
  src/repo_harness/rl \
  src/repo_harness/agent_loop \
  src/repo_harness/tools \
  src/repo_harness/workspace; then
  exit 1
fi
```

## 8. 提交边界

Stage 16A 提交应只包含：

```text
execute_bash 工具协议和实现
command policy / visibility guard / output redaction
必要的 workspace adapter 接入
必要的 AgentLoop / tool registry / tool schema snapshot 接入
Stage 16A 测试
Stage 16A evidence
```

不应混入：

```text
Stage 16B persistent session 完整生命周期
Stage 16C public environment prompt builder
Stage 16D official verifier healthcheck
Stage 16E patch hygiene
Stage 17 数据 registry
Stage 19 reward builder
Stage 19.5 old CLI export bridge
reference/verl 子模块修改
无关 HTML 汇报页
```

## 9. 进入下一阶段的条件

只有满足下面条件，才进入 Stage 16B：

1. `execute_bash` 工具协议和执行路径存在。
2. 工具可见注册表和实际执行注册表一致。
3. command policy 的正例、负例和 false-positive 回归都有测试。
4. shell 输出脱敏和 public evidence path leak scan 通过。
5. 至少一个 `real_episode` smoke 证明 `execute_bash` 能在 RepoHarness-verl 链路中运行。
6. 旧 `diagnostic_shell` 的保留或排除边界有结构化说明。

Stage 16A 通过不表示 persistent shell 生命周期已经完成。Stage 16B 仍然必须单独验收同题复用、跨题隔离、timeout invalidation 和 cleanup。
