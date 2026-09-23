# CLAUDE.md（Claude 会话入口）

更新：2026-09-15。每次会话自动载入。项目定位、当前阶段、主线入口、代码与精读目录、共同协作规则以 AGENTS.md 为唯一来源，直接引入：

@AGENTS.md

以下只补充 Claude 会话额外需要的内容。决策分级与决策包格式、轮次报告模板、审查回应与熔断规则都在 [协作协议](docs/agentic_RL/repo_harness_rh2_workstreams/collaboration-protocol.md) 与 [审查标准](docs/agentic_RL/repo_harness_rh2_workstreams/review-standards.md)，本文不复制；冲突时以它们为准。

## 会话纪律

- 文档、注释与解释用清晰的中文，保留必要术语、命令、文件名、字段名与代码标识符；解释易混概念时配具体数值、路径、命令或例子。
- 分工是默认值：默认 Claude 实现、Codex 独立审查，但 Claude 同样参与设计与讨论，Codex 也可能承担实施或实验；以用户在当批任务里的授权为准。
- 协议 §4 的五段报告只用于轮次收尾与阶段收口；日常问答、设计讨论和中间进展不套模板。
- 不主动 commit、push、rebase 或切分支；用户要求时才做，且只包含本任务路径。
- 凭据只从已 git-ignore 的文件读取；密钥、token、本机私有路径不写进任何文档、报告、日志、账本或提交。
- 报告区分建议、已决定、已实施、已验证；结论指向可核对的文件或命令输出。

## 开工与记录

1. 读所属主线记录（infra.md 或 env_data_eval.md）的最新条目与当批决定，再用代码、提交和审查证据核对；AGENTS.md 与会话摘要里的快照可能过时。
2. 会话分叉或压缩后，先核对摘要提到的文件、分支和机器是否仍存在。
3. 设计决策、偏离、权衡与开放问题追加到所属主线记录或当批目录 README，只记重要事项；不另建 implementation-notes.md。
4. 机器地址、密钥路径等本机信息放不跟踪的 CLAUDE.local.md。

## 仓库提醒

- `rh2/` 使用自带的 `rh2/.venv`；测试与 ruff 从 `rh2/` 运行，具体命令以当批记录为准。
- `rh2/experiments/` 是未跟踪的实验与诊断脚本；`runs/`、`tmp/` 是 git-ignore 的本地证据与临时目录。
- 精读可能只在远端分支（如 `origin/research/*`）；先 `git fetch`，从分支读取，不擅自合并。
