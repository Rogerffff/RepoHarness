"""只读复核：历史与当前 R2E 材料的混合账本；输出仅写本轮审查目录。"""
from __future__ import annotations

import collections
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[6]
OUT = ROOT / "runs/r2e_t0_batch2_review_20260924"
SOURCE = ROOT / "runs/r2e_t0_batch2_20260924"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    old = SOURCE / "reconcile_versioned/rf_three_tasks_local.jsonl"
    mixed = [old]
    mixed += sorted((ROOT / "runs/r2e_t0_revisions_20260924/replay").glob("ledger_t0_*_local.jsonl"))
    mixed += sorted((SOURCE / "replay_b3").glob("ledger_b3_*_local.jsonl"))
    mixed += sorted((SOURCE / "replay_b2").glob("ledger_watch1c1c_*_local.jsonl"))
    summaries = {}
    for name, ledgers in (("old_six", [old]), ("mixed_32", mixed)):
        cmd = [str(ROOT / "rh2/.venv/bin/python"), "scripts/reconcile_r2e.py", "--repo-root", "..",
               "--m3-root", str(ROOT / "runs/env_overnight_20260916/M3"), "--out", str(OUT / name)]
        for ledger in ledgers:
            cmd.extend(["--ledger", str(ledger)])
        proc = subprocess.run(cmd, cwd=ROOT / "rh2", capture_output=True, text=True, check=True)
        (OUT / f"{name}.log").write_text(proc.stdout + proc.stderr)
        rows = json.loads((OUT / name / "reconcile.json").read_text())
        counted = [r for r in rows if r.get("comparisons") and not r.get("hidden_tests_revised")]
        summary = {
            "rows": len(rows), "counted": len(counted), "agree": sum(r["agree"] for r in counted),
            "revised_hidden_rows": sum(bool(r.get("hidden_tests_revised")) for r in rows),
            "versions": dict(collections.Counter(r["material_version"]["version"] for r in rows)),
            "ledger_contradictions": sum(r.get("reference_ledger_consistent") is False for r in rows),
            "ledgers": [str(p.relative_to(ROOT)) for p in ledgers],
        }
        assert all(r["agree"] for r in counted), summary
        assert summary["ledger_contradictions"] == 0, summary
        assert summary["versions"].get("unmatched", 0) == 0, summary
        assert (len(rows), len(counted)) == ((6, 6) if name == "old_six" else (32, 20)), summary
        summaries[name] = summary
    (Path(__file__).parent / "reconcile_summary.json").write_text(json.dumps(summaries, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summaries, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
