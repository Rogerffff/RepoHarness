#!/usr/bin/env python3
"""把中央复跑得到的 R13（重复一致性）结果写回逐题 `screening_record.json`（验收步骤，Claude 运行）。

输入：`--tasks-dir`（含 `<iid>/facts.json`，需先用 `collate_facts.py --extra-evidence …` 并入复跑账本）。
规则：
- 只处理 `checks.R13.status == "unknown"` 或 `disposition.pending_checks` 含 "R13" 或 `disposition.state_if_r13_passes` 存在的记录；
- facts 的 `auto_checks.R13_repeat_noop` 与 `R13_repeat_gold` 都 pass → `checks.R13 = pass`（证据引用取自 facts），
  从 `pending_checks` 移除 R13。**只更新重复性事实，不替人给资格**（Codex 09-24 R1 更正）：只有审查者在记录里
  显式写了 `state_if_r13_passes`、且 `disposition.open_items` 为空时才改 `disposition.state`；其余一律保持原状态，
  列入"待人工确认资格"。旧版在没有显式目标时把 unknown 兜底提升为 environment_qualified，会把"已归因但未修好"
  的开发故障（例：numpy `43e333e2` 相关公开测试收集失败）算成合格——已撤掉。
- 任一为 issue → `checks.R13 = issue`（note 带汇总器说明），`disposition.state` 保持 unknown，列出待人工；
- 任一仍 unknown（复跑没覆盖）→ 不改，列出。
每次改动追加 `review_notes`。`--dry-run` 只打印。
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tasks-dir", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--by", default="Claude（验收，apply_r13.py）")
    args = ap.parse_args(argv)
    tasks_dir = Path(args.tasks_dir).resolve()
    today = datetime.now(timezone.utc).date().isoformat()
    summary = {"promoted": [], "needs_manual_state": [], "r13_issue": [], "r13_unknown": [], "untouched": []}
    for d in sorted(p for p in tasks_dir.iterdir() if p.is_dir()):
        rp, fp = d / "screening_record.json", d / "facts.json"
        if not (rp.is_file() and fp.is_file()):
            continue
        rec = json.loads(rp.read_text(encoding="utf-8"))
        facts = json.loads(fp.read_text(encoding="utf-8"))
        disp = rec.setdefault("disposition", {})
        pending = disp.get("pending_checks") or []
        r13_rec = (rec.get("checks") or {}).get("R13") or {}
        wants = r13_rec.get("status") == "unknown" or "R13" in pending or "state_if_r13_passes" in disp
        if not wants:
            summary["untouched"].append(d.name)
            continue
        ac = facts.get("auto_checks") or {}
        noop, gold = ac.get("R13_repeat_noop") or {}, ac.get("R13_repeat_gold") or {}
        statuses = {noop.get("status"), gold.get("status")}
        refs = sorted(set((noop.get("evidence_refs") or []) + (gold.get("evidence_refs") or [])))
        note = f"noop: {noop.get('note')}; gold: {gold.get('note')}"
        if statuses == {"pass"}:
            rec.setdefault("checks", {})["R13"] = {"status": "pass", "note": note, "evidence_refs": refs, "by": "collate_facts.py（中央复跑并入）"}
            old_state = disp.get("state")
            explicit = disp.get("state_if_r13_passes")
            if "R13" in pending:
                disp["pending_checks"] = [x for x in pending if x != "R13"]
            if explicit and not disp.get("open_items"):
                disp["state"] = explicit
                rec.setdefault("review_notes", []).append({"by": args.by, "at": today, "change": f"R13 由中央复跑并入：pass；按审查者显式写的 state_if_r13_passes，disposition.state {old_state!r} → {explicit!r}"})
                summary["promoted"].append((d.name, old_state, explicit))
            else:
                rec.setdefault("review_notes", []).append({"by": args.by, "at": today, "change": "R13 由中央复跑并入：pass；资格不自动改，待人工确认"})
                summary["needs_manual_state"].append((d.name, old_state))
        elif "issue" in statuses:
            rec.setdefault("checks", {})["R13"] = {"status": "issue", "note": note, "evidence_refs": refs, "by": "collate_facts.py（中央复跑并入）"}
            rec.setdefault("review_notes", []).append({"by": args.by, "at": today, "change": "R13 由中央复跑并入：issue（同条件运行结果不一致），处置保持 unknown，待人工归因"})
            summary["r13_issue"].append((d.name, note))
        else:
            summary["r13_unknown"].append((d.name, note))
            continue
        if not args.dry_run:
            rp.write_text(json.dumps(rec, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for k, v in summary.items():
        print(f"{k}: {len(v)}")
        for item in v:
            print("   ", item if k != "untouched" else item)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
