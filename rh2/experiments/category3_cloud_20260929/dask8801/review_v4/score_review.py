"""dask__dask-8801 v4 聚焦复核：按评分包参考名单（F2P 2 项、P2P 41 项）给私有运行逐项判分（私有模拟评分）。

用法：python score_review.py <输出目录>  → 打印表格，并写 <输出目录>/scores.json
判分：F2P 两项与 P2P 41 项都在 pytest -rA 摘要里为 PASSED 记 1，否则 0；缺项也记 0。
另列：解析出的测试数、不在参考名单内的非 PASSED 项（如 root 下的两项权限测试）、F2P 失败处的首条断言。
"""

import json
import re
import sys
from pathlib import Path

EV = Path("/home/user/RepoHarness/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/"
          "category3_diagnosis_20260929/tasks/dask__dask-8801/evidence")
refs = json.loads((EV / "materials/refs.json").read_text())
F2P = [t.split("::")[1] for t in refs["f2p"]]
P2P = [t.split("::")[1] for t in refs["p2p"]]
out = Path(sys.argv[1])


def parse(p: Path):
    txt = p.read_text(errors="replace")
    res = {}
    for line in txt.splitlines():
        m = re.match(r"^(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS) dask/tests/test_config.py::(\S+)", line)
        if m:
            res[m.group(2)] = m.group(1)
    why = {}
    for t in F2P:
        m = re.search(r"_{3,} " + re.escape(t) + r" _{3,}\n(.*?)(?=\n_{3,} \S+ _{3,}\n|\n={5,})", txt, re.S)
        if m:
            lines = m.group(1).splitlines()
            gt = [ln.strip() for ln in lines if ln.startswith(">")]
            el = [ln[1:].strip() for ln in lines if ln.startswith("E ")]
            why[t] = ((gt[-1] if gt else "") + " | " + (el[0] if el else ""))[:220]
    return res, why


scores = {}
for vd in sorted(d for d in out.iterdir() if d.is_dir()):
    row = {}
    for f in sorted(vd.glob("*_*.out")):
        res, why = parse(f)
        f2p = sum(res.get(t) == "PASSED" for t in F2P)
        p2p = sum(res.get(t) == "PASSED" for t in P2P)
        row[f.stem] = {
            "sim": int(f2p == len(F2P) and p2p == len(P2P)),
            "f2p": f"{f2p}/{len(F2P)}",
            "p2p": f"{p2p}/{len(P2P)}",
            "n": len(res),
            "nonref_not_passed": sorted(t for t, s in res.items() if s != "PASSED" and t not in F2P + P2P),
            "why": why,
        }
    scores[vd.name] = row

(out / "scores.json").write_text(json.dumps(scores, ensure_ascii=False, indent=1) + "\n")
cols = ["orig_nobody", "orig_root", "v4_nobody", "v4_root", "v4rva_nobody", "v4rva_root", "v4rvb_nobody", "v4rvb_root"]
print(f"{'variant':26s} " + " ".join(f"{c:>12s}" for c in cols))
for v, row in scores.items():
    cells = []
    for c in cols:
        r = row.get(c)
        cells.append(f"{(str(r['sim']) + ' ' + r['f2p'] + ' ' + r['p2p'].split('/')[0]) if r else '-':>12s}")
    print(f"{v:26s} " + " ".join(cells))
