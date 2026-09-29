#!/usr/bin/env python3
"""从子代理会话记录里取出被宿主拒绝落盘的 Write 调用内容（2026-09-29，单题闭环试行）。
只写到给定的 results/<题>/ 目录下；目标文件已存在且内容相同则跳过，不同则另存为 <名>.from_transcript 并报告
（子代理写入后又用 Edit 改过时，磁盘上的才是终稿，.from_transcript 只是较早的写入稿，核对后删掉）。
用法：extract_writes.py <会话记录 .output> <允许的目标目录>
"""
import json
import sys
from pathlib import Path

T, allowed = Path(sys.argv[1]), Path(sys.argv[2]).resolve()
last: dict[str, str] = {}
for line in T.read_text().splitlines():
    try:
        o = json.loads(line)
    except Exception:
        continue
    msg = o.get("message") or {}
    content = msg.get("content")
    if not isinstance(content, list):
        continue
    for c in content:
        if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("name") == "Write":
            last[c["input"].get("file_path", "")] = c["input"].get("content", "")
for fp, body in last.items():
    p = Path(fp).resolve()
    if p.parent != allowed:
        print("skip (outside allowed dir):", fp)
        continue
    if p.exists():
        if p.read_text() == body:
            print("same:", p.name, len(body))
        else:
            alt = p.with_name(p.name + ".from_transcript")
            alt.write_text(body)
            print("DIFFERS, saved as:", alt.name, len(body))
    else:
        p.write_text(body)
        print("saved:", p.name, len(body))
