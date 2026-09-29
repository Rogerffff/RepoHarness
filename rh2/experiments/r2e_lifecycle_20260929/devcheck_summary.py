#!/usr/bin/env python3
"""汇总 devcheck 结果（2026-09-29，单题闭环试行）：每题 attempt.json 的 checks 是否全真、不符的命令、私有 gold 对照各命令退出码。
用法：devcheck_summary.py <本地 devcheck 根目录>   （目录下每题一个 <instance_id>/，含 orig/attempt.json 与 private_control.json）
"""
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
out = {}
for d in sorted(root.iterdir()):
    if not d.is_dir() or "__" not in d.name or d.name.startswith("_"):
        continue
    att = d / "orig" / "attempt.json"
    row = {"attempt": att.is_file()}
    if att.is_file():
        a = json.loads(att.read_text())
        checks = a.get("checks") or {}
        row["checks_all_true"] = bool(checks) and all(checks.values())
        row["checks_false"] = sorted(k for k, v in checks.items() if not v)
        cmds = a.get("commands") or []
        res = a.get("command_results") or a.get("results") or {}
        row["n_commands"] = len(cmds)
        mism = []
        for c in cmds:
            r = res.get(c["id"]) if isinstance(res, dict) else None
            if isinstance(r, dict) and r.get("matches_expect") is False:
                mism.append(c["id"])
        row["mismatched_commands"] = mism
    pc = d / "private_control.json"
    if pc.is_file():
        p = json.loads(pc.read_text())
        row["private_gold_rc"] = {k: v.get("rc") for k, v in (p.get("results") or {}).items()}
    out[d.name] = row
    flag = "OK " if row.get("checks_all_true") else "BAD"
    print(flag, d.name[:40], "false=", row.get("checks_false"), "mism=", row.get("mismatched_commands"), "gold_rc=", row.get("private_gold_rc"))
(root / "summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
