"""汇总 run_private.py grade 的结果：候选 × 测试版本的私有模拟得分，以及 F2P 失败时第一处失败的断言行。

用法：python summarize_grade.py <grade 输出目录>
"""
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path

out = Path(sys.argv[1])
rows = OrderedDict()
tests = []
for line in (out / "results.jsonl").read_text().splitlines():
    r = json.loads(line)
    rows.setdefault(r["candidate"], {})[r["test"]] = r
    if r["test"] not in tests:
        tests.append(r["test"])


def first_fail(cand, test):
    p = out / f"{cand}__{test}.log"
    txt = p.read_text(errors="replace")
    m = re.search(r"_{5,} test_set_index_interpolate _{5,}(.*?)(?:\n_{5,} |\n={5,})", txt, re.S)
    if not m:
        return ""
    block = m.group(1)
    calls = [ln.strip() for ln in block.splitlines() if ln.startswith(">")]
    errs = [ln.strip() for ln in block.splitlines() if ln.startswith("E ")]
    call = next((c for c in calls if "_assert_exact_int_divisions(" in c), calls[0] if calls else "")
    inner = calls[-1] if calls else ""
    return f"{call[1:].strip()[:110]} | {inner[1:].strip()[:60]} | {errs[0][1:].strip()[:70] if errs else ''}"


print("candidate".ljust(22) + "".join(t[:14].ljust(16) for t in tests))
for cand, per in rows.items():
    cells = []
    for t in tests:
        r = per.get(t)
        if r is None:
            cells.append("-".ljust(16))
            continue
        tag = str(r["reward"])
        if r.get("p2p_bad"):
            tag += f" (P2P bad {len(r['p2p_bad'])})"
        cells.append(tag.ljust(16))
    print(cand.ljust(22) + "".join(cells))
print()
for cand, per in rows.items():
    for t in tests:
        r = per.get(t)
        if r and r["reward"] == 0 and any(v != "PASSED" for v in r["f2p"].values()):
            print(f"{cand} / {t}: {first_fail(cand, t)}")
        if r and r.get("p2p_bad"):
            print(f"{cand} / {t}: P2P not passed: {sorted(r['p2p_bad'])}")
