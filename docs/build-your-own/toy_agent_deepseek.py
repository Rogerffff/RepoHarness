"""
最小 agent loop（教学玩具）—— DeepSeek HTTP 版本。

与 00-overview.md 中的 Anthropic 版本逻辑等价，只是把协议从
Anthropic 的 `tool_use` / `tool_result` 换成了 DeepSeek（OpenAI 兼容）
的 `tool_calls` / `role:"tool"`，并改用 urllib 直接打 HTTP。

依赖：仅 Python 3 标准库（urllib + json）。
API key：优先读环境变量 DEEPSEEK_API_KEY，否则回退到
reference/deepseek_api.md 第一行 "DEEPSEEK_API key:sk-..." 的格式。
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import TextIO

# ────────────────────────────────────────────────────────────
# 配置
# ────────────────────────────────────────────────────────────
API_BASE = "https://api.deepseek.com"
ENDPOINT = f"{API_BASE}/chat/completions"
MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")

# 把仓库根（脚本所在目录的祖父目录）视作 workspace 边界。
# RepoHarness 真实实现里这是 Docker container 的 /workspace 挂载点。
WORKSPACE_ROOT = Path(__file__).resolve().parents[2]


def load_api_key() -> str:
    if key := os.environ.get("DEEPSEEK_API_KEY"):
        return key.strip()
    key_file = WORKSPACE_ROOT / "reference" / "deepseek_api.md"
    text = key_file.read_text()
    match = re.search(r"sk-[A-Za-z0-9]+", text)
    if not match:
        raise RuntimeError(f"no API key found in {key_file}")
    return match.group(0)


API_KEY = load_api_key()


# ────────────────────────────────────────────────────────────
# 工具定义（核心 4 件套：name / description / parameters / 执行函数）
# ────────────────────────────────────────────────────────────
def tool_read_file(args: dict) -> str:
    """读取 workspace 内的文本文件（截断到 4000 字符）。"""
    raw = Path(args["path"]).expanduser()
    if not raw.is_absolute():
        raw = WORKSPACE_ROOT / raw
    try:
        abs_path = raw.resolve()
        abs_path.relative_to(WORKSPACE_ROOT)
    except ValueError:
        return f"ERROR: path '{raw}' is outside workspace boundary {WORKSPACE_ROOT}"
    if not abs_path.is_file():
        return f"ERROR: not a file: {abs_path}"
    text = abs_path.read_text(errors="replace")
    return text[:4000] + ("\n...[truncated]" if len(text) > 4000 else "")


# OpenAI / DeepSeek 的 function tool schema：外层包一层 {"type":"function","function":{...}}
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Read a text file from the workspace. The path must be within the "
                "workspace root; paths outside it will be rejected."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "relative (to workspace root) or absolute path within workspace",
                    }
                },
                "required": ["path"],
            },
        },
    }
]

TOOL_HANDLERS = {"read_file": tool_read_file}


# ────────────────────────────────────────────────────────────
# HTTP 调用（urllib，无第三方依赖）
# ────────────────────────────────────────────────────────────
def call_deepseek(messages: list[dict]) -> dict:
    body = json.dumps(
        {
            "model": MODEL,
            "messages": messages,
            "tools": TOOLS,
            "tool_choice": "auto",
            "max_tokens": int(os.environ.get("DEEPSEEK_MAX_TOKENS", "8192")),
            "temperature": 0.0,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        ENDPOINT,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"DeepSeek HTTP {e.code}: {detail}") from e


# ────────────────────────────────────────────────────────────
# Agent Loop —— 整套核心
# ────────────────────────────────────────────────────────────
# ────────────────────────────────────────────────────────────
# Trace writer —— 把交互过程结构化地写到 markdown
# ────────────────────────────────────────────────────────────
class Tracer:
    """Append-mode markdown writer with flush-after-each-section."""

    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.f: TextIO = path.open("w", encoding="utf-8")

    def close(self) -> None:
        self.f.close()

    def heading(self, level: int, text: str) -> None:
        self.f.write(f"\n{'#' * level} {text}\n\n")
        self.f.flush()

    def kv(self, **fields) -> None:
        for k, v in fields.items():
            self.f.write(f"- **{k.replace('_', ' ')}:** {v}\n")
        self.f.write("\n")
        self.f.flush()

    def fenced(self, body: str, lang: str = "") -> None:
        # 用 4 个反引号围栏，避免 body 里嵌套 ``` 把围栏打断
        fence = "````"
        self.f.write(f"{fence}{lang}\n{body}\n{fence}\n\n")
        self.f.flush()

    def quote(self, text: str) -> None:
        for line in text.splitlines() or [""]:
            self.f.write(f"> {line}\n")
        self.f.write("\n")
        self.f.flush()

    def hr(self) -> None:
        self.f.write("\n---\n")
        self.f.flush()

    def text(self, text: str) -> None:
        self.f.write(text)
        if not text.endswith("\n"):
            self.f.write("\n")
        self.f.write("\n")
        self.f.flush()


def default_trace_path() -> Path:
    if env := os.environ.get("DEEPSEEK_TRACE_FILE"):
        return Path(env).expanduser().resolve()
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    return WORKSPACE_ROOT / "docs" / "build-your-own" / "runs" / f"run-{stamp}.md"


def agent_loop(
    user_msg: str,
    max_turns: int = 30,
    trace_path: Path | None = None,
) -> tuple[str, Path]:
    trace_path = trace_path or default_trace_path()
    tr = Tracer(trace_path)

    system_prompt = (
        f"You are a helpful coding assistant. Workspace root is {WORKSPACE_ROOT}. "
        "Use the read_file tool when you need to inspect file contents. "
        "Reply in the same language the user used."
    )
    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_msg},
    ]

    # —— Trace 文件头
    tr.heading(1, f"Toy Agent Run — {_dt.datetime.now().isoformat(timespec='seconds')}")
    tr.kv(
        Model=f"`{MODEL}`",
        Endpoint=f"`{ENDPOINT}`",
        WorkspaceRoot=f"`{WORKSPACE_ROOT}`",
        MaxTurns=max_turns,
    )
    tr.heading(2, "User prompt")
    tr.quote(user_msg)
    tr.heading(2, "System prompt")
    tr.fenced(system_prompt)

    final_answer = "[max turns reached]"
    try:
        for turn in range(max_turns):
            print(f"  turn {turn + 1} → calling {MODEL} ...",
                  file=sys.stderr, flush=True)

            # ① 调模型
            resp = call_deepseek(messages)
            choice = resp["choices"][0]
            msg = choice["message"]

            # —— Trace: 这一轮的元数据
            tr.hr()
            tr.heading(2, f"Turn {turn + 1}")
            tr.kv(
                finish_reason=f"`{choice.get('finish_reason')}`",
                message_keys=f"`{list(msg.keys())}`",
            )
            tr.heading(3, "Usage")
            tr.fenced(
                json.dumps(resp.get("usage", {}), ensure_ascii=False, indent=2),
                "json",
            )

            # —— Trace: 完整的 thinking（reasoning_content）
            tr.heading(3, "Reasoning content (thinking)")
            if msg.get("reasoning_content"):
                tr.fenced(msg["reasoning_content"])
            else:
                tr.text("_(empty)_")

            # —— Trace: assistant 可见文本
            tr.heading(3, "Assistant content (visible text)")
            if msg.get("content"):
                tr.fenced(msg["content"], "markdown")
            else:
                tr.text("_(empty — pure tool-call turn)_")

            # —— Trace: 完整的 tool_calls JSON
            if msg.get("tool_calls"):
                tr.heading(3, "Tool calls (raw JSON from model)")
                tr.fenced(
                    json.dumps(msg["tool_calls"], ensure_ascii=False, indent=2),
                    "json",
                )

            # ② 把 assistant 整段消息原样追加进历史
            # DeepSeek/OpenAI 协议里，assistant 消息必须保留 tool_calls 字段，否则下一轮拿
            # role:"tool" 回灌时模型对不上 tool_call_id；thinking 模型还要求把
            # reasoning_content 原样传回（否则会 400 invalid_request_error）。
            assistant_entry: dict = {
                "role": "assistant",
                "content": msg.get("content") or "",
            }
            if msg.get("tool_calls"):
                assistant_entry["tool_calls"] = msg["tool_calls"]
            if msg.get("reasoning_content") is not None:
                assistant_entry["reasoning_content"] = msg["reasoning_content"]
            messages.append(assistant_entry)

            tool_calls = msg.get("tool_calls") or []

            # ③ 没有 tool_calls → 模型说完了 → 返回文本
            if not tool_calls:
                final_answer = msg.get("content") or ""
                print(f"  turn {turn + 1} → finish_reason=stop, exiting loop.",
                      file=sys.stderr, flush=True)
                break

            # ④ 跑工具，构造 tool_result blocks（DeepSeek 用 role:"tool" 而非 user）
            tr.heading(3, "Tool results (local execution)")
            for tc in tool_calls:
                name = tc["function"]["name"]
                raw_args = tc["function"]["arguments"]
                try:
                    args = json.loads(raw_args or "{}")
                except json.JSONDecodeError as e:
                    output = f"ERROR: invalid JSON arguments: {e}"
                else:
                    handler = TOOL_HANDLERS.get(name)
                    if handler is None:
                        output = f"ERROR: unknown tool {name}"
                    else:
                        try:
                            output = handler(args)
                        except Exception as e:
                            output = f"ERROR: {type(e).__name__}: {e}"

                tr.heading(4, f"`{name}` — `{tc['id']}`")
                tr.kv(arguments=f"`{raw_args}`")
                tr.fenced(output)

                # ⑤ tool_result 必须用 role:"tool" + tool_call_id 配对回灌
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": output,
                    }
                )

            print(
                f"  turn {turn + 1} → finish_reason=tool_calls, "
                f"ran {len(tool_calls)} tool call(s).",
                file=sys.stderr, flush=True,
            )

        # —— Trace: 最终回答
        tr.hr()
        tr.heading(2, "Final answer")
        tr.text(final_answer)
        return final_answer, trace_path
    finally:
        tr.close()


# ────────────────────────────────────────────────────────────
# 跑一下
# ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    user_msg = (
        " ".join(sys.argv[1:])
        or "请读取 docs/00-reading-guide.md 的开头，告诉我这是什么项目。"
    )
    answer, trace_path = agent_loop(user_msg)
    print(f"\n[trace written to: {trace_path}]", file=sys.stderr)
    print("\n──────── Final answer ────────")
    print(answer)
