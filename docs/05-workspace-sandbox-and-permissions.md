# Workspace, Sandbox, And Permissions

## 设计目标

这一层负责回答两个不同问题：

- permission：这次工具调用是否允许执行？
- sandbox：即使允许执行，它应该在什么边界内执行？

这两个概念必须分开。权限不是隔离，Docker execution mode 也不是生产级安全沙箱。

## Workspace 生命周期

未来实现中，一次任务运行必须采用 source checkout、setup workspace、agent run workspace 三阶段生命周期，并在正式验收时额外创建 verification workspace。前三者负责避免依赖安装、baseline 检查和模型修改互相污染；verification workspace 只负责 strict patch replay 和 final verifier，不是模型继续操作的工作区：

```text
source checkout
  -> setup workspace
      -> setup command
      -> dependency_state
      -> baseline verifier
      -> baseline artifacts
  -> agent run workspace
      -> restore dependency_state
      -> agent_start_snapshot
      -> agent loop
      -> final.patch / final.diff from agent_start_snapshot
  -> verification workspace
      -> restore dependency_state
      -> apply final.patch
      -> final verifier
```

阶段职责：

1. 创建 run directory。
2. 从任务 `repo` 和可选 `base_commit` 创建 source checkout。
3. 从 source checkout 创建 setup workspace，执行 dependency setup，并在 setup command 结束后、baseline verifier 运行前捕获 `dependency_state`。
4. Verifier 通过 Workspace Adapter 运行 baseline verifier，保存 `BaselineResult`、baseline 日志和 baseline verifier artifact。baseline 运行产生的测试缓存、日志、覆盖率文件和其他副作用只能作为 baseline artifact 或 excluded diff 处理，不能进入之后恢复到 agent run workspace 的 `dependency_state`。
5. 如果 `BaselineResult.status` 是 `valid`，从 source checkout 创建 agent run workspace，并恢复 `dependency_state`。
6. 在 agent run workspace 中建立 `agent_start_snapshot`，之后模型的工具调用才开始进入正式 trajectory。
7. agent 停止后先生成 `final.patch` 和 `final.diff`，其基线必须是 `agent_start_snapshot`。这一步必须发生在正式 final verifier 之前，避免测试缓存、覆盖率文件、快照更新或格式化副作用污染最终补丁。
8. 正式评测模式应从 source checkout 创建 verification workspace、恢复合法依赖状态、应用 `final.patch` 后再运行 final verifier，也就是 `final_verifier_mode = "strict_patch_replay"`。
9. 快速调试模式可以在 agent run workspace 上直接运行 final verifier，但必须先捕获 `final.patch` / `final.diff`，并记录 `final_verifier_mode`，不能把这种模式的结果伪装成严格复现验收。
10. 清理临时环境，保留 run artifacts、summary 和必要 workspace 引用。

## 执行模式

local process mode 用于快速开发和调试。它在本机任务工作区中执行命令，必须仍然遵守路径约束和 timeout。

Docker execution mode 用于本地或离线批量评测。它把任务工作区挂载到容器中执行测试命令和允许的 shell 命令。文档中应称为 Docker-based executable repository environment。它面向可复现执行，不面向对抗性代码隔离。

local process mode 的网络策略必须保守表述。`network_policy = "deny_agent_run"` 在第一版主要通过命令解析、权限规则和 allowlist 阻止 `curl`、`wget`、`git clone`、`git fetch`、`ssh`、`scp` 等网络入口，不表示已经实现操作系统级断网。Docker execution mode 如果要求 agent run 或 final verifier 断网，应在对应阶段使用 `--network=none` 或等价受控网络配置，并把网络策略写入 workspace event、permission event 和 summary。

## 权限模式

第一版只设计四种模式：

- `plan`：只允许读工具和计划生成，不允许修改文件或执行任意 bash。
- `ask`：写文件或任意 bash 前需要确认。批量 evaluation runner 默认不应使用这个模式，否则会因为等待人工确认而卡住。
- `auto`：允许任务工作区内的写入和任务测试命令。
- `deny`：非交互拒绝风险操作模式。它允许明确安全的只读工具，拒绝需要确认的写操作、风险命令和 workspace 外访问。这里的 `deny` 是运行模式，不等同于单次 `PermissionDecision.decision = "deny"`。

权限判断只负责返回允许、拒绝、需要询问和原因。它不直接执行命令，也不直接修改文件。

权限判定顺序必须确定，第一版建议：

1. schema 校验和工具输入规范化，例如路径规范化、命令解析、cwd 解析和工具参数类型检查。
2. 不可绕过安全检查。危险路径、敏感文件、workspace boundary、未授权网络、命令解析失败、破坏性 Git 子命令、未支持的 shell 语法等必须先被拦截。显式 allow、显式 ask、任务 allowlist 和 `auto` 模式都不能绕过这一层。
3. 显式 deny 规则。
4. 工具自身 `check_permissions`。
5. 显式 allow / ask 规则和任务级 allowlist。
6. 当前权限模式 fallback：`plan`、`ask`、`auto`、`deny`。
7. 无法确定时，在交互单任务中进入 ask，在非交互批量评测中默认 deny。

如果 `ask` 出现在批量 evaluation runner 中，必须被配置校验拒绝或降级为非交互策略，不能让运行无限等待人工输入。

## 命令安全规则

默认可由 `bash` 处理的非测试命令类型：

- 非测试类诊断命令，例如 `ruff`、`mypy`、`python -m compileall`。
- 任务 schema 中明确声明为普通诊断的命令。
- 只读文件系统查询命令，例如 `pwd`、`ls`、`find` 的受限形式。

测试类命令必须特殊处理：

- 如果模型通过 `bash` 请求运行任务 `test_command`，或者请求 `pytest`、`python -m pytest`、`npm test`、`pnpm test` 等可识别测试命令，Tool System 应默认路由到 `run_tests`。
- 如果实现允许用户显式把测试类命令作为普通 `bash` observation 运行，结果只能进入模型上下文和 events，不能计入 success rate、reward metadata、fail-to-pass 或 pass-to-pass 统计。
- `run_tests` 和 final verifier 才能产生结构化 `VerifierResult`。

默认拒绝或强约束：

- `rm -rf`
- `sudo`
- `curl`
- `wget`
- `ssh`
- `scp`
- `curl | sh`
- 写入 home directory
- 访问任务 workspace 外路径
- 无 timeout 的长时间命令

所有命令必须有 timeout。所有文件写入必须解析为 workspace 内路径。

Git 命令必须按子命令和 flag 级别处理，而不是只按字符串粗略拒绝。第一版建议只允许受限只读 Git 子命令：

- `git status`
- `git diff`
- `git show`
- `git log`
- `git ls-files`

未列入白名单的 Git 子命令默认拒绝，包括但不限于 `git clone`、`git fetch`、`git pull`、`git remote add`、`git checkout`、`git reset`、`git clean`、`git commit`、`git tag`、`git branch`、`git apply`、`git worktree add` 和 `git submodule update`。允许的只读 Git 命令仍必须通过 workspace boundary 检查、timeout、输出截断和 artifact 记录。`git diff` 输出应同时提供模型可见 preview 和完整 `ArtifactRef`。

命令解析不能只依赖简单字符串包含。第一版可以保守处理：

- 只允许任务配置中声明的测试命令通过 `run_tests` 执行。
- `bash` 默认只允许诊断命令和受限只读命令。
- 复杂 shell compound command、管道、重定向、子命令、后台任务和环境变量覆盖，如果不在 allowlist 中，应拒绝或要求显式配置。
- 命令执行必须记录工作目录、环境变量白名单、timeout、stdout/stderr artifact、exit code 和是否被截断。

`bash` 的 cwd 和环境变量语义必须保守：

- `bash` input 使用显式 `cwd` 字段，不从上一条命令继承隐式 shell 状态。
- `cwd` 必须解析到 agent run workspace 内。相对路径以 workspace root 为基准，解析后记录 `requested_cwd` 和 `effective_cwd`。
- 第一版默认拒绝 `cd`、`pushd`、`popd`、任意 PATH 修改、任意环境变量前缀、复杂 compound command 和后台任务，除非任务配置显式 allowlist。
- 允许的环境变量覆盖必须来自任务配置或 RunConfig 白名单，并记录 `env_policy_version`、`env_overrides` 和 `shell_parser_status`。
- 每次命令执行都必须独立构造受控环境；模型不能通过一次命令修改后续命令的 cwd、PATH 或环境变量。

网络策略必须显式记录：

- setup 阶段可以按任务配置允许网络，例如安装公开依赖。
- agent run 阶段默认关闭或强限制网络。
- 默认拒绝模型在 agent run 中执行 `git clone`、`git fetch`、`curl`、`wget`、`ssh`、`scp` 等会引入外部状态或泄漏任务信息的命令。
- local process mode 的 agent run 网络限制是命令层和配置层约束，不应声称为操作系统级网络隔离。
- Docker execution mode 可以在 setup 阶段允许网络，在 agent run 和 formal final verifier 阶段使用无网络或受控网络配置。
- 如果未来允许网络，必须记录 `network_policy`、允许域名、命令、时间、输出 artifact 和触发事件。

## Workspace Adapter 执行边界

Workspace Adapter 负责统一处理：

- 路径规范化和 workspace boundary 检查。
- 符号链接解析。
- 工作目录设置。
- 环境变量白名单或覆盖。
- 命令 timeout 和进程中断。
- process group kill 或等价进程树清理。
- 容器执行时的容器停止和清理。
- stdout、stderr preview 与完整输出落盘。
- Git diff、patch 和 workspace state 捕获。

具体工具不得各自实现另一套路径边界或命令执行逻辑。这样才能保证 permission 事件、工具事件、verifier 事件和最终 diff 使用同一套执行事实。

workspace 内部也需要敏感路径策略。第一版应定义 `sensitive_path_policy`：

- 默认拒绝或脱敏读取 `.git/`、`.env`、`.env.*`、`*id_rsa*`、`*.pem`、`*.key`、包管理器认证文件、GitHub CLI 认证文件、npm token、pip 配置中的凭据和其他明确 secret 文件。
- 默认拒绝写入 `.git/`、`.git/hooks/`、`.git/refs/`、`.git/config`、认证文件、私钥文件和 workspace 内声明为只读的任务元数据。
- 如果某个任务确实需要读取内部配置文件，必须在 task schema 中显式声明，并且进入模型上下文前仍要经过 redaction policy。
- 被拒绝或脱敏的路径必须记录到 permission event、tool event 和 artifact redaction metadata，便于后续分析权限拒绝率和训练样本过滤。

timeout 语义必须分层：

- 工具 timeout：单次工具调用超时，返回 `ToolResult(status = "timeout")`。
- 命令 timeout：Workspace Adapter 负责终止进程树并保存 interrupted artifact。
- verifier timeout：生成 `VerifierResult(timeout = true)`，并进入 final verifier status 或 feedback verifier event。
- 单任务全局 timeout：终止 agent loop，未完成 tool call 必须补齐 interrupted tool result。

测试缓存、诊断缓存和构建产物默认不进入 `final.diff` 和训练 patch。`excluded_diff_paths` 应同时适用于 setup 阶段和 agent run 阶段的测试缓存，例如 `.pytest_cache/`、`.coverage`、`coverage/`、`dist/`、`build/`、`node_modules/`、`.mypy_cache/`。如果任务本身要求修改生成文件或快照文件，必须在 task schema 中显式声明。

## 结果记录

每次 permission decision 都要写入 events，包括：

- `decision_id`
- `tool_call_id`
- `tool_name`
- `requested_tool_name`
- `effective_tool_name`
- `decision`
- `reason`
- `mode`
- `matched_rule`
- `policy_version`
- `rule_source`
- `normalized_input_hash`
- `resolved_paths`
- `command_category`
- `network_policy`
- `requested_cwd`
- `effective_cwd`
- `non_interactive_resolution`
- `workspace_path`

这样后续可以分析权限拒绝率、命令路由、策略版本变化、网络策略、cwd 解析、失败样本和训练数据过滤原因。

## 保守表述

可以写：

- Docker-based executable repository environment。
- task-level separated workspace。
- task-level workspace boundary。
- command timeout and path-boundary checks。

不要写：

- 生产级安全沙箱。
- 完整网络隔离。
- 沙箱逃逸防护。
- 企业级权限系统。
- 多租户 Kubernetes 安全平台。

## Claude Code 参考

参考模块：

- `reference/claude-code-docs/claude-doc/05-permissions-and-security.md`
- `reference/claude-code-docs/claude-code-ai-core-codex/03-tools-permissions-and-plan-mode.md`
- `reference/claude-code-typescript-src/utils/permissions/permissions.ts`
- `reference/claude-code-typescript-src/tools/BashTool/bashPermissions.ts`
- `reference/claude-code-typescript-src/tools/BashTool/bashSecurity.ts`

RepoHarness 不复制 Claude Code 的企业权限、自动分类器或远程权限回传。
