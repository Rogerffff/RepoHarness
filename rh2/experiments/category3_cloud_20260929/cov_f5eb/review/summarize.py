# 汇总复核者私有模拟评分：逐个日志切分测试版本、逐键评分，写 grades.jsonl 并打印表格
import json, sys, glob, os
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from grade import grade
M = HERE / "materials"
EXP = {"v0": M / "expected_v0.json", "v8": M / "expected_cur.json", "rc2": M / "expected_rc2.json",
       "rb2": M / "expected_rc2.json", "rc3": M / "expected_rc3.json", "rb3": M / "expected_rc3.json",
       "rc3h": M / "expected_rc3.json", "rb3h": M / "expected_rc3.json"}
short = lambda k: {"JsonReportTest.test_branch_coverage": "BC", "JsonReportTest.test_simple_line_coverage": "LINE",
                   "JsonReportTest.test_context_relative": "CTX_R", "JsonReportTest.test_context_non_relative": "CTX_NR",
                   "JsonReportTest.test_branch_totals_count_branch_arcs": "K1",
                   "JsonReportTest.test_branch_totals_from_saved_branch_data": "K2",
                   "JsonReportTest.test_branch_totals_add_up_across_files": "K3",
                   "JsonReportTest.test_branch_totals_without_branches": "K4"}.get(k, k)
rows = []
for log in sorted(HERE.glob("logs/*__*.log")):
    if log.name.startswith("probe__") or log.name.startswith("pre__"):
        continue
    tag, cand = log.stem.split("__", 1)
    res = grade(str(log), {k: str(v) for k, v in EXP.items()})
    for tv, r in res.items():
        rows.append({"tag": tag, "cand": cand, "material": tv, **r})
with open(HERE / "grades.jsonl", "w") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
order = ["v0", "v8", "rc2", "rb2", "rc3", "rb3", "rc3h", "rb3h"]
table = {}
uid_rows = [r for r in rows if r["tag"].startswith("u")]
for r in rows:
    if r["tag"].startswith("u"):
        continue  # uid 54322 的重跑单独列出
    cell = str(r["rh2_reward"])
    if r["prime_reward"] != r["rh2_reward"]:
        cell += "!prime=%s" % r["prime_reward"]
    bad = sorted(short(k) for k in r["mismatch"]) + ["+" + short(k) for k in r["unexpected"]]
    if bad:
        cell += "(" + ",".join(bad) + ")"
    table.setdefault(r["cand"], {})[r["material"]] = cell
mats = [m for m in order if any(m in v for v in table.values())]
print("cand".ljust(16) + " | ".join(m.ljust(16) for m in mats))
for c in sorted(table):
    print(c.ljust(16) + " | ".join(table[c].get(m, "-").ljust(16) for m in mats))
print()
print("uid 54322 重跑：")
for r in uid_rows:
    print(" ", r["cand"], r["material"], r["rh2_reward"], sorted(short(k) for k in r["mismatch"]))
