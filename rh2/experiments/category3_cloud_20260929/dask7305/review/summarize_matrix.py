"""汇总 run_private.py matrix 的输出：每个候选一行，列出失败的用例与原因。

用法：python summarize_matrix.py <matrix 输出目录> [候选...]
"""
import json
import sys
from pathlib import Path

out = Path(sys.argv[1])
names = sys.argv[2:] or sorted(p.stem for p in out.glob("*.jsonl"))
for name in names:
    p = out / f"{name}.jsonl"
    if not p.exists():
        print(f"{name}: (no output)")
        continue
    recs = []
    for line in p.read_text().splitlines():
        if line.startswith("{"):
            recs.append(json.loads(line))
    fails, small = [], None
    for r in recs:
        if r["case"] == "small_int":
            small = r.get("divisions", r.get("error"))
            continue
        if not r.get("ok"):
            why = r.get("error") or ",".join(sorted(r.get("detail", {})))
            extra = ""
            if "d_first" in r:
                extra = f" ({r['d_first']:+d}/{r['d_last']:+d})" if isinstance(r["d_first"], int) else ""
            if r.get("lost"):
                extra += f" lost={r['lost']}"
            fails.append(f"{r['case']}[{why}{extra}]")
    print(f"{name}: {len(recs) - 1} cases, {len(fails)} fail; small_int={small}")
    for f in fails:
        print("    " + f)
