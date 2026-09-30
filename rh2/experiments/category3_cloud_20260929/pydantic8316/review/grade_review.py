"""汇总复核者私有对照（run_review.py 的输出）：按 ingest 评分包的参考名单（F2P 1 项、P2P 143 项）逐项判分。
这是私有模拟评分（root、原镜像、断网），不是正式评分。逐项状态取自 -vv classic 输出的 “<nodeid> PASSED/FAILED” 行。
用法：python grade_review.py <review/out/sem> <grading_bundles_v2_v0.jsonl>
输出：<sem>/../review_summary.json，并打印 Markdown 表。
"""
import json
import re
import sys
from pathlib import Path

IID = "pydantic__pydantic-8316"
sem, bundles = Path(sys.argv[1]), Path(sys.argv[2])
ref = next(json.loads(ln) for ln in bundles.read_text().splitlines() if IID in ln)
F2P, P2P = ref["fail_to_pass"], ref["pass_to_pass"]
STATUS = re.compile(r"^(tests/test_utils\.py::.+?) (PASSED|FAILED|SKIPPED|ERROR|XFAIL|XPASS)(?:\s+\[\s*\d+%\])?\s*$", re.M)


def grade(text: str) -> dict:
    st = {m.group(1): m.group(2) for m in STATUS.finditer(text)}
    f2p_ok = all(st.get(t) == "PASSED" for t in F2P)
    p2p_fail = [t for t in P2P if st.get(t) != "PASSED"]
    missing = [t for t in F2P + P2P if t not in st]
    first = next((ln.strip() for ln in text.splitlines() if ln.startswith("E ") and "assert" in ln), None)
    return {"reward": int(f2p_ok and not p2p_fail), "f2p": f"{int(f2p_ok)}/{len(F2P)}",
            "p2p": f"{len(P2P) - len(p2p_fail)}/{len(P2P)}", "ref_missing": len(missing), "collected": len(st),
            "first_assert": first}


rows = {}
for vd in sorted(p for p in sem.iterdir() if p.is_dir()):
    rec = {"rc": json.loads((vd / "rc.json").read_text()) if (vd / "rc.json").exists() else None}
    b1 = (vd / "b1_behavior.out").read_text() if (vd / "b1_behavior.out").exists() else ""
    line = next((ln for ln in b1.splitlines() if ln.startswith("REVIEW_BEHAVIOR_JSON=")), None)
    rec["behavior"] = json.loads(line.split("=", 1)[1]) if line else None
    for tag in ("s_orig", "s_v2", "s_v3", "s_v3_uid54322"):
        f = vd / f"{tag}.out"
        rec[tag] = grade(f.read_text()) if f.exists() else None
    rec["candidate_diff_sha256"] = None
    rows[vd.name] = rec
(sem.parent / "review_summary.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1, sort_keys=True))

print("| 变体 | 原测试 | v2 | v3 草案 | v3（UID 54322） | v2／v3 首条失败断言 |")
print("| --- | --- | --- | --- | --- | --- |")
for name, r in rows.items():
    cells = []
    for tag in ("s_orig", "s_v2", "s_v3", "s_v3_uid54322"):
        g = r[tag]
        cells.append("—" if g is None else f"{g['reward']}（F2P {g['f2p']}，P2P {g['p2p']}，缺 {g['ref_missing']}）")
    fa = (r["s_v2"] or {}).get("first_assert") or ""
    fb = (r["s_v3"] or {}).get("first_assert") or ""
    print(f"| {name} | " + " | ".join(cells) + f" | {fa} ／ {fb} |")
