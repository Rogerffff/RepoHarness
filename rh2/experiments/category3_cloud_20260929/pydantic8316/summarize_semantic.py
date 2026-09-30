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


EXPECTED_COLLECTED = 173  # tests/test_utils.py 在 base 与补丁后的收集数（159 passed + 14 skipped 或含失败），正式日志同此


def simgrade(text: str) -> dict:
    """本镜像装有 pytest-pretty，-q -rA 不输出逐项 PASSED 行；因此按 FAILURES 段的失败标题 + 结果计数判定：
    收集总数必须等于 EXPECTED_COLLECTED，参考项不在失败集合里即视为通过。若有经典 PASSED 行则优先用逐项状态。"""
    st = statuses(text)
    failed = set(re.findall(r"^_{3,} (\S+) _{3,}$", text, re.M))
    counts = {k: int(v) for v, k in re.findall(r"^\s+(\d+) (passed|failed|skipped|errors?|xfailed|xpassed)\s*$", text, re.M)}
    collected = sum(counts.values())
    complete = collected == EXPECTED_COLLECTED and not counts.get("error") and not counts.get("errors")
    if st:
        ok = lambda t: st.get(t) == "PASSED"  # noqa: E731
    else:
        ok = lambda t: complete and t.split("::", 1)[1] not in failed  # noqa: E731
    f2p_ok = all(ok(t) for t in F2P)
    p2p_fail = [t for t in P2P if not ok(t)]
    first_fail = next((ln.strip() for ln in text.splitlines() if ln.startswith("E ") and "assert" in ln), None)
    return {"reward": int(f2p_ok and not p2p_fail), "f2p": f"{int(f2p_ok)}/{len(F2P)}",
            "p2p_pass": f"{len(P2P) - len(p2p_fail)}/{len(P2P)}", "p2p_fail": p2p_fail[:5],
            "failed_tests": sorted(failed), "counts": counts, "complete": complete, "first_assert": first_fail}


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
        c = {k: int(v) for v, k in re.findall(r"^\s+(\d+) (passed|failed|skipped|errors?|xfailed|xpassed)\s*$", t, re.M)}
        rec["public_related_tail"] = "、".join(f"{v} {k}" for k, v in c.items()) or None
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
