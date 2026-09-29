#!/usr/bin/env python3
"""把一轮已落正式修订单的题的验收候选排成正式评分计划（2026-09-29，单题闭环试行）。

每题的候选取自 results/<题>/revision_draft.json 的 acceptance：noop、gold 走 replay_grade 自带的 noop / gold-dir；
其余候选（替代正对照、合理替代解、已知错误解）按题内顺序分到槽位 s1、s2…，每个槽位一个 patch-dir
（<iid>.diff），一路评分进程跑一个槽位里的全部题。补丁用试跑时远端实际用过的那一份（试跑记录里的 patch 路径），
远端建槽位时核对摘要，与本地来源（有的话）一致。

用法：formal_round_plan.py --ids <iid,...> --round <名> --out runs/r2e_lifecycle_20260929/formal_<名>/plan.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

R = Path(__file__).resolve().parents[3]
B = R / "docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", required=True)
    ap.add_argument("--round", required=True)
    ap.add_argument("--out", required=True)
    ns = ap.parse_args()
    rows, slots = [], {}
    for iid in ns.ids.split(","):
        d = json.loads((B / "results" / iid / "revision_draft.json").read_text())
        k = 0
        for name, a in d["acceptance"].items():
            if "@" in name or (isinstance(a, dict) and a.get("materials") == "current"):
                continue  # 现材料上的对照，只作修订前后比较，不进本轮正式评分
            if not isinstance(a, dict) or "expected_score" not in a:
                raise SystemExit(f"{iid}: acceptance[{name}] 缺 expected_score")
            trial = B / "results" / iid / a["trial"].split("（")[0].strip()
            t = json.loads(trial.read_text())
            remote = t.get("patch") or t.get("candidate_patch") or (t.get("args") or {}).get("patch")
            local = a.get("patch") or a.get("candidate_patch")
            local_sha = None
            if local and local not in ("none", "None") and (R / local).is_file():
                local_sha = hashlib.sha256((R / local).read_bytes()).hexdigest()
            if name == "noop" or remote in (None, "none"):
                if name != "noop":
                    raise SystemExit(f"{iid}: {name} 没有补丁")
                spec, slot = "noop", "noop"
            elif name == "gold":
                spec, slot = "gold-dir", "gold"
            else:
                k += 1
                slot = f"s{k}"
                spec = "patch-dir"
                slots.setdefault(slot, []).append(iid)
            rows.append({"instance_id": iid, "candidate": name, "slot": slot, "spec": spec, "expected_score": int(a["expected_score"]),
                         "remote_patch": remote if spec != "noop" else None, "local_patch": local if local_sha else None,
                         "local_sha256": local_sha, "trial": str(trial.relative_to(R)), "positive_control": d.get("positive_control")})
    out = {"round": ns.round, "rows": rows, "slots": {s: v for s, v in sorted(slots.items())}}
    Path(ns.out).write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(f"{len(rows)} 行，槽位 {', '.join(f'{s}×{len(v)}' for s, v in sorted(slots.items()))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
