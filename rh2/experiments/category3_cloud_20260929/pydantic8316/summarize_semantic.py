"""汇总 pydantic-8316 私有行为矩阵（semantic_control.py 输出目录）。
每个变体：
  - to_snake 各输入的输出（从 b1_behavior.out 的 BEHAVIOR_JSON 解析）；
  - 私有模拟评分：s_orig / s_rev1 / s_rev2 三条命令（应用对应测试补丁后跑 tests/test_utils.py -rA），
    按参考名单（F2P 1 项、P2P 143 项，来自 ingest 评分包）逐项计分；不是正式评分；
  - b2 相关公开测试（test_utils、test_aliases、test_config，未应用 test_patch）的汇总行。
用法：python summarize_semantic.py <semantic 输出目录> <grading_bundles_v2_v0.jsonl>
输出：<目录>/semantic_summary.json，并在终端打印 Markdown 表。
"""
import json
import re
import sys
from pathlib import Path

IID = "pydantic__pydantic-8316"
out_dir, bundles = Path(sys.argv[1]), Path(sys.argv[2])
ref = next(json.loads(ln) for ln in bundles.read_text().splitlines() if IID in ln)
F2P, P2P = ref["fail_to_pass"], ref["pass_to_pass"]


def statuses(text: str) -> dict:
    st = {}
    for m in re.finditer(r"^(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS) (tests/\S+)", text, re.M):
        st[m.group(2)] = m.group(1)
    return st


def simgrade(text: str) -> dict:
    st = statuses(text)
    f2p_ok = all(st.get(t) == "PASSED" for t in F2P)
    p2p_fail = [t for t in P2P if st.get(t) != "PASSED"]
    first_fail = next((ln.strip() for ln in text.splitlines() if ln.startswith("E ") and "assert" in ln), None)
    tail = next((ln.strip() for ln in reversed(text.splitlines()) if re.search(r"\d+ (passed|failed)", ln)), None)
    return {"reward": int(f2p_ok and not p2p_fail), "f2p": f"{int(f2p_ok)}/{len(F2P)}",
            "p2p_pass": f"{len(P2P) - len(p2p_fail)}/{len(P2P)}", "p2p_fail": p2p_fail[:5],
            "first_assert": first_fail, "pytest_tail": tail}


rows = {}
for vd in sorted(p for p in out_dir.iterdir() if p.is_dir()):
    rec = {"rc": json.loads((vd / "rc.json").read_text()) if (vd / "rc.json").exists() else None}
    b1 = vd / "b1_behavior.out"
    if b1.exists():
        line = next((ln for ln in b1.read_text().splitlines() if ln.startswith("BEHAVIOR_JSON=")), None)
        rec["behavior"] = json.loads(line.split("=", 1)[1]) if line else None
    b2 = vd / "b2_public_related.out"
    if b2.exists():
        t = b2.read_text()
        rec["public_related_tail"] = next((ln.strip() for ln in reversed(t.splitlines()) if re.search(r"\d+ (passed|failed)", ln)), None)
    for tag in ("s_orig", "s_rev1", "s_rev2"):
        f = vd / f"{tag}.out"
        if f.exists():
            rec[tag] = simgrade(f.read_text())
    rows[vd.name] = rec
(out_dir / "semantic_summary.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n")

print("| 变体 | 相关公开测试 | 私有模拟 原测试 | v1 | v2 | v1/v2 首条失败断言 |")
print("| --- | --- | --- | --- | --- | --- |")
for name, r in rows.items():
    cells = []
    for tag in ("s_orig", "s_rev1", "s_rev2"):
        s = r.get(tag) or {}
        cells.append(f"{s.get('reward')}（F2P {s.get('f2p')}，P2P {s.get('p2p_pass')}）")
    fa = (r.get("s_rev2") or {}).get("first_assert") or (r.get("s_rev1") or {}).get("first_assert") or ""
    print(f"| {name} | {r.get('public_related_tail')} | {' | '.join(cells)} | {fa[:90]} |")
