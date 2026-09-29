# 本次公开阅读材料说明

这是待交付修订题面的静态公开包，用于独立阅读，不是实际容器、正式摄入结果或模型请求捕获。`user_prompt.txt` 使用本题来源提示外壳与待交付修订题面；题面 SHA256 为 `f8701d3a4322270fde2618cc7cfc094460c9a5f1ec874e400c5bfaeef9ec7199`。

`public_task.json` 是公开任务字段的静态副本，其 `problem_statement` 已同步为该修订题面。`public_hints`、工具、工作目录和镜像等字段沿用来源元数据；它们不证明当前 Claude Code 已实际接收到这些提示，也不证明当前 actor 位置、权限、激活或资源已满足。当前正式 consumer 的实际消息、actor 身份和运行条件由主线程另行核对。

`worktree/` 逐字复制自 2026-09-24 v3 本题公开工作树：base 跟踪文件加来源镜像初态中的改动和构建文件；不含 `.git`、被 `.gitignore` 忽略的构建产物、`.venv` 或隐藏评分材料。缺失情况见 `worktree_manifest.json`。这里的文件只代表该历史公开快照，不表示现在线上的容器。

来源环境阶段曾观测：工作目录 `/testbed`，Python 3.7.9，解释器位于 `/testbed/.venv/bin/python`，有 pip、无出网，解题身份 agent（uid 54321），默认2 CPU/4 GiB、`/tmp` 1 GiB；涉及 Qt 的 widget 测试使用 `QT_QPA_PLATFORM=minimal xvfb-run --auto-servernum`。这些是历史条件，当前机器与正式入口未在本包重新验证；仅供提出开发条件和命令时参考。不能把一般“纯库调用不用Qt前缀”自动套到会导入 widget 模块的本题函数。

请只据本目录公开材料独立读出需求和最小验证路径，区分可从源码推出的事实、历史环境事实与当前待验证条件。不要访问本目录之外的题目调查材料。
