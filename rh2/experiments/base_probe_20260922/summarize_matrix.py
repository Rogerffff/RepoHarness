#!/usr/bin/env python3
"""基座探针：从回传的 attempt.json / 评分账本 / 网关留证汇总 N、V、S（设计稿 §6 口径）。

N = 派发的尝试；V = 有完整有效判分的尝试（attempt 正常 ran、评分账本有 report、无 stage_error、且网关留证里没有
首字节后中断的流）；S = V 中 RH2 原分为 1 的尝试。infra / 未知单列，不补成 0。用法：
  summarize_matrix.py <runs_root>/matrix <gateway_root> [--out summary.json]
"""

from __future__ import annotations

import argparse
import glob
import json
from collections import defaultdict
from pathlib import Path


def truncated_sessions(gateway_root: Path) -> dict[str, str]:
    bad: dict[str, str] = {}
    for f in glob.glob(str(gateway_root / "*" / "bp22-*" / "responses.jsonl")):
        sid = Path(f).parent.name
        for ln in open(f, encoding="utf-8"):
            try:
                r = json.loads(ln)
            except Exception:  # noqa: BLE001
                continue
            if r.get("seq") is None or r.get("retried"):
                continue
            if r.get("stream_error") or (r.get("status") == 200 and r.get("stop_reason") is None):
                bad[sid] = f"seq{r.get('seq')}:{(r.get('stream_error') or 'no_stop_reason')[:80]}"
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("matrix_root")
    ap.add_argument("gateway_root")
    ap.add_argument("--out", default=None)
    ns = ap.parse_args()
    root = Path(ns.matrix_root)
    bad = truncated_sessions(Path(ns.gateway_root))
    rows = []
    for aj in sorted(glob.glob(str(root / "attempts" / "*" / "*" / "a*" / "attempt.json"))):
        adir = Path(aj).parent
        if ".incomplete-" in adir.name:
            continue
        a = json.loads(Path(aj).read_text(encoding="utf-8"))
        task, solver, k = adir.parts[-3], adir.parts[-2], adir.name
        led = adir / "grading_v2" / "ledger.jsonl"  # 候选清洗后重评（镜像基线脏文件被剔除）优先；原 grading/ 保留
        regraded = led.exists()
        if not regraded:
            led = adir / "grading" / "ledger.jsonl"
        g = None
        if led.exists():
            lines = [x for x in led.read_text(encoding="utf-8").splitlines() if x.strip()]
            g = json.loads(lines[-1]) if lines else None
        rep = (g or {}).get("report") or {}
        ts = a.get("trajectory_summary") or {}
        ccr = ts.get("cc_result") or {}
        status = "valid"
        if a.get("result") != "ran":
            status = f"infra:{a.get('result')}"
        elif a.get("attempt_id") in bad:
            status = f"infra:upstream_stream_truncated({bad[a['attempt_id']]})"
        elif g is None or not rep or rep.get("reward") is None:
            status = f"unknown:no_valid_grade({(g or {}).get('stage_error')})"
        elif (g or {}).get("stage_error"):
            status = f"unknown:stage_error({g.get('stage_error')})"
        rows.append({
            "task": task, "solver": solver, "attempt": k, "status": status, "reward": rep.get("reward"),
            "f2p": [rep.get("f2p_pass"), rep.get("f2p_total")], "p2p_fail": rep.get("p2p_fail"), "p2p_total": rep.get("p2p_total"),
            "termination": a.get("termination"), "cc_subtype": ccr.get("subtype"), "num_turns": ccr.get("num_turns"),
            "solve_seconds": a.get("solve_seconds"), "tool_calls": ts.get("tool_calls_total"),
            "tool_result_errors": ts.get("tool_result_errors"), "tools_used": ts.get("tool_calls"),
            "candidate_bytes": (a.get("candidate") or {}).get("bytes"), "candidate_empty": (a.get("candidate") or {}).get("empty"),
            "touches_tests": bool((a.get("candidate") or {}).get("touches_tests")), "harness_out": a.get("harness_out", "in_tree"),
            "actor_env": a.get("actor_env"), "image_override": a.get("image_override"), "regraded_v2": regraded,
            "apply_method": ((g or {}).get("candidate") or {}).get("apply_method"),
            "usage": (ccr.get("usage") or {}), "cost_usd_cc_estimate": ccr.get("total_cost_usd"),
        })
    cells: dict[tuple[str, str], dict] = defaultdict(lambda: {"N": 0, "V": 0, "S": 0, "vector": [], "infra_or_unknown": []})
    for r in rows:
        c = cells[(r["task"], r["solver"])]
        c["N"] += 1
        if r["status"] == "valid":
            c["V"] += 1
            c["S"] += int(r["reward"] == 1.0)
            c["vector"].append(int(r["reward"] == 1.0))
        else:
            c["vector"].append(None)
            c["infra_or_unknown"].append(f"{r['attempt']}:{r['status']}")
    table = [{"task": t, "solver": s, **c, "mixed": (0 < c["S"] < c["V"])} for (t, s), c in sorted(cells.items())]
    by_solver: dict[str, dict] = defaultdict(lambda: {"N": 0, "V": 0, "S": 0, "solve_seconds": [], "turns": []})
    for r in rows:
        b = by_solver[r["solver"]]
        b["N"] += 1
        if r["status"] == "valid":
            b["V"] += 1
            b["S"] += int(r["reward"] == 1.0)
        if r.get("solve_seconds"):
            b["solve_seconds"].append(r["solve_seconds"])
        if r.get("num_turns"):
            b["turns"].append(r["num_turns"])
    solver_table = {s: {"N": b["N"], "V": b["V"], "S": b["S"],
                        "median_solve_seconds": sorted(b["solve_seconds"])[len(b["solve_seconds"]) // 2] if b["solve_seconds"] else None,
                        "median_turns": sorted(b["turns"])[len(b["turns"]) // 2] if b["turns"] else None,
                        "hit_turn_cap": sum(1 for x in b["turns"] if x and x >= 61)} for s, b in by_solver.items()}
    out = {"attempts": rows, "cells": table, "by_solver": solver_table, "truncated_sessions": bad}
    if ns.out:
        Path(ns.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    solvers = sorted({r["solver"] for r in rows})
    print("| 题目 | " + " | ".join(solvers) + " |")
    print("| --- | " + " | ".join("---" for _ in solvers) + " |")
    for t in sorted({r["task"] for r in rows}):
        line = [t]
        for s in solvers:
            c = cells.get((t, s))
            if not c or not c["N"]:
                line.append("—")
                continue
            vec = "".join("·" if v is None else str(v) for v in c["vector"])
            line.append(f"S/V/N={c['S']}/{c['V']}/{c['N']} [{vec}]")
        print("| " + " | ".join(line) + " |")
    print(json.dumps(solver_table, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
