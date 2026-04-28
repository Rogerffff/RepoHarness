# Workspace, Sandbox, And Permissions

## 设计目标

这一层负责回答两个不同问题：

- permission：这次工具调用是否允许执行？
- sandbox：即使允许执行，它应该在什么边界内执行？

这两个概念必须分开。权限不是隔离，Docker execution mode 也不是生产级安全沙箱。

## Workspace 生命周期

未来实现中，一次任务运行的 workspace 生命周期是：

1. 创建 run directory。
2. 复制或 checkout 初始仓库。
3. 初始化 Git 状态，用于 diff 和 patch 捕获。
4. 执行 agent tools。
5. 运行 verifier。
6. 保存 final diff、patch、metrics 和 summary。
7. 清理临时环境，保留 run artifacts。

## 执行模式

local process mode 用于快速开发和调试。它在本机任务工作区中执行命令，必须仍然遵守路径约束和 timeout。

Docker execution mode 用于本地或离线批量评测。它把任务工作区挂载到容器中执行测试命令和允许的 shell 命令。文档中应称为 Docker-based executable repository environment。它面向可复现执行，不面向对抗性代码隔离。

## 权限模式

第一版只设计四种模式：

- `plan`：只允许读工具和计划生成，不允许修改文件或执行任意 bash。
- `ask`：写文件或任意 bash 前需要确认。批量 evaluation runner 默认不应使用这个模式，否则会因为等待人工确认而卡住。
- `auto`：允许任务工作区内的写入和任务测试命令。
- `deny`：非交互拒绝风险操作模式。它允许明确安全的只读工具，拒绝需要确认的写操作、风险命令和 workspace 外访问。这里的 `deny` 是运行模式，不等同于单次 `PermissionDecision.decision = "deny"`。

权限判断只负责返回允许、拒绝、需要询问和原因。它不直接执行命令，也不直接修改文件。

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
- `ssh`
- `scp`
- `curl | sh`
- 写入 home directory
- 访问任务 workspace 外路径
- 无 timeout 的长时间命令

所有命令必须有 timeout。所有文件写入必须解析为 workspace 内路径。

## Workspace Adapter 执行边界

Workspace Adapter 负责统一处理：

- 路径规范化和 workspace boundary 检查。
- 符号链接解析。
- 工作目录设置。
- 环境变量白名单或覆盖。
- 命令 timeout 和进程中断。
- stdout、stderr preview 与完整输出落盘。
- Git diff、patch 和 workspace state 捕获。

具体工具不得各自实现另一套路径边界或命令执行逻辑。这样才能保证 permission 事件、工具事件、verifier 事件和最终 diff 使用同一套执行事实。

## 结果记录

每次 permission decision 都要写入 events，包括：

- `tool_name`
- `decision`
- `reason`
- `mode`
- `matched_rule`
- `workspace_path`

这样后续可以分析权限拒绝率和失败模式。

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
