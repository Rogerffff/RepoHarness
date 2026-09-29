"""把 semantic_control 的输出汇总成矩阵（私有对照 + 私有模拟评分）。

用法：python summarize_semantic.py <semantic 输出目录> [--json 输出文件]
私有模拟评分：在 b2/b3/b4 的 pytest -rA 摘要里按参考名单（F2P 1 项、P2P 34 项，含合并键 `[set`）逐项判定，
reward=1 当且仅当 F2P 与全部 P2P 都是 PASSED。只是私有模拟，不是正式评分。
"""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
IID = "getmoto__moto-6185"
d = Path(sys.argv[1])
refs = None
for line in (REPO / "docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest/grading_bundles_v2_v0.jsonl").open():
    row = json.loads(line)
    if row["instance_id"] == IID:
        refs = row
        break
F2P, P2P = refs["fail_to_pass"], refs["pass_to_pass"]


def parse_ra(text):
    """按冻结 parser 的做法：-rA 摘要行 `STATUS name`，键取 split()[1]。"""
    status = {}
    for line in text.splitlines():
        m = re.match(r"^(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS) (\S+)", line)
        if m:
            status[m.group(2)] = m.group(1)
    return status


def sim(text):
    st = parse_ra(text)
    f2p = [st.get(k, "MISSING") for k in F2P]
    p2p_bad = [k.split("::")[-1] for k in P2P if st.get(k) != "PASSED"]
    reward = int(all(s == "PASSED" for s in f2p) and not p2p_bad)
    fail_line = ""
    m = re.search(r"test_dynamodb_exceptions\.py:(\d+): in test_put_item__string_as_integer_value", text)
    if m:
        fail_line = "L" + m.group(1)
    err = re.findall(r"^E   (.*)$", text, re.M)
    return {"reward": reward, "f2p": f2p[0], "p2p_not_passed": p2p_bad, "f2p_fail_at": fail_line,
            "first_error": err[0][:160] if err else ""}


out = {}
for vd in sorted(p for p in d.iterdir() if p.is_dir()):
    v = vd.name
    row = {"rc": json.loads((vd / "rc.json").read_text()) if (vd / "rc.json").exists() else None}
    beh = (vd / "b1_behavior.out").read_text() if (vd / "b1_behavior.out").exists() else ""
    summ = beh.split("=== SUMMARY\n", 1)[1] if "=== SUMMARY\n" in beh else ""
    row["behavior"] = dict(line.split(": ", 1) for line in summ.strip().splitlines() if ": " in line)
    for cid, key in [("b2_hidden_orig", "orig"), ("b3_hidden_v1", "v1"), ("b4_hidden_v1s", "v1s")]:
        p = vd / f"{cid}.out"
        if p.exists():
            row[key] = sim(p.read_text())
    p = vd / "b5_dynamodb_suite.out"
    if p.exists():
        t = p.read_text().strip().splitlines()
        row["dynamodb_suite"] = t[-1] if t else ""
        row["dynamodb_suite_failed"] = re.findall(r"^FAILED (\S+)", p.read_text(), re.M)
    out[v] = row

if "--json" in sys.argv:
    Path(sys.argv[sys.argv.index("--json") + 1]).write_text(json.dumps(out, ensure_ascii=False, indent=1))


def cell(s):
    if s is None:
        return "-"
    if s.startswith("ok"):
        return "ok" if "get_equal=False" not in s else "ok/≠"
    if s.startswith("ClientError:SerializationException"):
        return "SerEx"
    if s.startswith("ClientError:TransactionCanceled"):
        return "TxCancel"
    if s.startswith("AttributeError"):
        return "AttrErr"
    return s.split(":", 1)[0]


variants = list(out)
keys = []
for v in variants:
    for k in out[v]["behavior"]:
        if k not in keys:
            keys.append(k)
print("| 行 | " + " | ".join(variants) + " |")
print("|---" * (len(variants) + 1) + "|")
for k in keys:
    print(f"| {k} | " + " | ".join(cell(out[v]["behavior"].get(k)) for v in variants) + " |")
for key in ("orig", "v1", "v1s"):
    print(f"| 私有模拟 {key} | " + " | ".join(
        (str(out[v][key]["reward"]) + ("@" + out[v][key]["f2p_fail_at"] if out[v][key]["f2p_fail_at"] else "")
         + ("" if not out[v][key]["p2p_not_passed"] else f"(P2P×{len(out[v][key]['p2p_not_passed'])})"))
        if key in out[v] else "-" for v in variants) + " |")
print("| dynamodb 全套 | " + " | ".join(out[v].get("dynamodb_suite", "-").replace("=", "").strip()[:40] for v in variants) + " |")
