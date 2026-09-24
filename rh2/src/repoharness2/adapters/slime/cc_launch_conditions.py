"""Claude Code 启动条件的**单一写入者**（基座探针决策包 §8，2026-09-24 用户批准）。

- #10 工具面：首版 SWE 只提供 Bash / Read / Edit / Write / NotebookEdit，用 CC 的 `--tools` 真正限定请求里的
  工具集合（`--allowedTools` 只是权限放行、不改请求；`--disallowedTools` 与 `--tools` 逐字节等价，但后者是白名单，
  不随 CC 新增工具漂移）。去掉 Skill 同时去掉 Skill 清单消息与 system 的 "# Session-specific guidance" 一节。
- #9 auto-memory：`CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`（启动时读；与 settings `autoMemoryEnabled:false` 逐字节等价），
  system 不再有 "# Memory" 一节、init 不再有 `memory_paths`、不再创建记忆目录。不禁止模型自己写笔记，不改 census。

正式启动（`bringup.launch_claude_code` / `claude_code_launch_env`）与探针脚本都从这里取值；`SLIME_AGENT_CC_EXTRA_ARGS`
只承载 max-turns 之类的作业参数，不再是工具面的来源。CC 版本钉死在 2.1.205（`RH2_CLAUDE_CODE_VERSION`）：
这些开关的行为随版本重验。
"""

from __future__ import annotations

CC_TOOL_SURFACE: tuple[str, ...] = ("Bash", "Read", "Edit", "Write", "NotebookEdit")

# 启动层常量（vendored ClaudeCodeHarness.static_env 之后、进程级 SLIME_AGENT_CC_EXTRA_ENVS 之前并入）
CC_RH2_STATIC_ENV: dict[str, str] = {
    "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1",  # #9
}


def cc_tool_surface_args(tools: tuple[str, ...] = CC_TOOL_SURFACE) -> str:
    """`--tools Bash,Read,Edit,Write,NotebookEdit`：拼进 CC 命令行（vendored launch_flags 之后、extra args 之前）。"""

    if not tools or any((not t) or ("," in t) or (" " in t) for t in tools):
        raise ValueError(f"非法工具名列表 {tools!r}")
    return "--tools " + ",".join(tools)


# #8(ii)(iv)：CC 的上下文窗口认知与服务容量对齐（决策包 §8）。2.1.205 实测：`CLAUDE_CODE_MAX_CONTEXT_TOKENS` 对非
# `claude-` 模型名生效（改 modelUsage.contextWindow，本身不触发压缩）；主动压缩阈值 = `CLAUDE_CODE_AUTO_COMPACT_WINDOW`
# − `CLAUDE_CODE_MAX_OUTPUT_TOKENS`（默认预留 20,000）− 13,000（CC 内部常量）；`AUTO_COMPACT_WINDOW` 低于 100,000 会被
# 抬到 100,000，所以三者必须一起给。`CLAUDE_CODE_FILE_READ_MAX_OUTPUT_TOKENS` 把 Read 上限从面向 200K 的 25,000 调到与
# 窗口相称的值。数值是作业配置（max_context_len / max_new_tokens / 配置字段），这里只做映射；CC 版本变化须重验。
CC_CONTEXT_WINDOW_ENV = "CLAUDE_CODE_MAX_CONTEXT_TOKENS"
CC_AUTO_COMPACT_WINDOW_ENV = "CLAUDE_CODE_AUTO_COMPACT_WINDOW"
CC_MAX_OUTPUT_TOKENS_ENV = "CLAUDE_CODE_MAX_OUTPUT_TOKENS"
CC_FILE_READ_MAX_OUTPUT_TOKENS_ENV = "CLAUDE_CODE_FILE_READ_MAX_OUTPUT_TOKENS"
CC_AUTO_COMPACT_FIXED_RESERVE = 13_000  # CC 2.1.205 内部常量，只用于报告余量


def cc_context_env(*, max_context_len: int, max_new_tokens: int | None, file_read_max_output_tokens: int | None) -> dict[str, str]:
    """按作业配置生成逐 execution 注入的窗口环境；`max_context_len<=0`（未配置）时不注入任何窗口变量。"""

    if max_context_len <= 0:
        return {}
    env = {CC_CONTEXT_WINDOW_ENV: str(int(max_context_len)), CC_AUTO_COMPACT_WINDOW_ENV: str(int(max_context_len))}
    if max_new_tokens is not None and int(max_new_tokens) > 0:
        env[CC_MAX_OUTPUT_TOKENS_ENV] = str(int(max_new_tokens))
    if file_read_max_output_tokens is not None and int(file_read_max_output_tokens) > 0:
        env[CC_FILE_READ_MAX_OUTPUT_TOKENS_ENV] = str(int(file_read_max_output_tokens))
    return env


def cc_compaction_margin(*, max_context_len: int, max_new_tokens: int | None) -> int | None:
    """报告用：CC 主动压缩阈值（窗口 − 输出预留 − 13,000）；未配置窗口时 None。"""

    if max_context_len <= 0:
        return None
    reserve = int(max_new_tokens) if max_new_tokens else 20_000
    return int(max_context_len) - reserve - CC_AUTO_COMPACT_FIXED_RESERVE
