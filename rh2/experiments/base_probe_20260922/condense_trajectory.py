#!/usr/bin/env python3
"""基座探针：把 CC 的 stream-json 轨迹（含逐 token 的 partial 事件）压成可读的逐轮转写 transcript.md。

只做展示层压缩：保留每个 assistant 消息的 thinking / text / tool_use 输入全文，tool_result 超长时保留首尾；
原始 trajectory.jsonl 不改，分析时以原件为准。用法：condense_trajectory.py <attempt_dir> [--limit 6000]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    head, tail = text[: limit * 2 // 3], text[-limit // 3:]
    return f"{head}\n…[省略 {len(text) - len(head) - len(tail)} 字符]…\n{tail}"


def block_text(content) -> str:
    if isinstance(content, str):
        return content
    out = []
    for b in content or []:
        if isinstance(b, dict):
            out.append(b.get("text") or json.dumps(b, ensure_ascii=False))
        else:
            out.append(str(b))
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("attempt_dir")
    ap.add_argument("--limit", type=int, default=6000)
    ns = ap.parse_args()
    adir = Path(ns.attempt_dir)
    lines = (adir / "trajectory.jsonl").read_text(encoding="utf-8", errors="replace").splitlines()
    out: list[str] = [f"# 轨迹转写：{adir}", ""]
    turn = 0
    stray: list[str] = []
    seen_msg_ids: set[str] = set()
    for ln in lines:
        ln = ln.strip()
        if not ln.startswith("{"):
            if ln:
                stray.append(ln[:300])
            continue
        try:
            ev = json.loads(ln)
        except Exception:  # noqa: BLE001
            stray.append(ln[:300])
            continue
        kind = ev.get("type")
        if kind == "system" and ev.get("subtype") == "init":
            out += ["## init", "```json", json.dumps({k: ev.get(k) for k in ("model", "cwd", "permissionMode", "claude_code_version", "tools") if k in ev}, ensure_ascii=False), "```", ""]
        elif kind == "assistant":
            msg = ev.get("message") or {}
            mid = msg.get("id")
            turn += 1
            out.append(f"## assistant #{turn}" + (f"（同一消息 {mid} 的后续块）" if mid in seen_msg_ids else ""))
            if mid:
                seen_msg_ids.add(mid)
            for b in msg.get("content") or []:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "thinking":
                    out += ["**thinking**", "", clip(b.get("thinking") or "", ns.limit), ""]
                elif b.get("type") == "text":
                    out += ["**text**", "", clip(b.get("text") or "", ns.limit), ""]
                elif b.get("type") == "tool_use":
                    out += [f"**tool_use `{b.get('name')}`** id={b.get('id')}", "```json", clip(json.dumps(b.get("input"), ensure_ascii=False, indent=1), ns.limit), "```", ""]
            usage = msg.get("usage") or {}
            if usage:
                out += [f"_usage: in={usage.get('input_tokens')} cache_read={usage.get('cache_read_input_tokens')} out={usage.get('output_tokens')} stop={msg.get('stop_reason')}_", ""]
        elif kind == "user":
            for b in (ev.get("message") or {}).get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    flag = "（is_error）" if b.get("is_error") else ""
                    out += [f"### tool_result{flag} for {b.get('tool_use_id')}", "```", clip(block_text(b.get("content")), ns.limit), "```", ""]
                elif isinstance(b, dict) and b.get("type") == "text":
                    out += ["### user text", "", clip(b.get("text") or "", ns.limit), ""]
        elif kind == "result":
            out += ["## result", "```json", json.dumps({k: v for k, v in ev.items() if k not in ("modelUsage",)}, ensure_ascii=False)[:3000], "```", ""]
    if stray:
        out += ["## 非 JSON 行（stderr 等，前 40 行）", "```", *stray[:40], "```"]
    (adir / "transcript.md").write_text("\n".join(out), encoding="utf-8")
    print(f"{adir}/transcript.md turns={turn} chars={sum(len(x) for x in out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
