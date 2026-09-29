"""汇总 semantic_control 的输出：behavior.py 的 JSON 与各 pytest 命令的逐测试结果。

用法：python summarize_semantic.py <semantic 输出目录> [<参考名单 refs.json>]
输出 <目录>/semantic_summary.json，并在终端打印紧凑表格。
"""

import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
refs = json.loads(Path(sys.argv[2]).read_text()) if len(sys.argv) > 2 else None
STATUS = re.compile(r"^(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS) (\S+)")


def pytest_status(path: Path):
    out = {}
    if not path.exists():
        return out
    for line in path.read_text().splitlines():
        m = STATUS.match(line)
        if m:
            out[m.group(2)] = m.group(1)
    return out


def short_case(c):
    cy = c["collect_yaml"]
    if cy["exc"] is None:
        s = "ok " + cy["merged"]
    else:
        flags = []
        flags.append("path" if cy["path_in_msg"] else "NOPATH")
        if cy["repr_path_in_msg"]:
            flags.append("repr")
        if cy.get("problem_in_rendered_tb") is not None:
            flags.append("reason-tb" if cy["problem_in_rendered_tb"] else "NOREASON-tb")
        if cy.get("mentions_dict_or_mapping"):
            flags.append("dict/mapping")
        ph = [k for k, v in cy["phrases"].items() if v]
        if ph:
            flags.append("phr:" + "+".join(p.split()[-1] for p in ph))
        if cy.get("names_b_instead"):
            flags.append("NAMES-b.yaml")
        s = f"{cy['exc']}[{','.join(flags)}]"
    if c.get("warnings"):
        s += f" warn{len(c['warnings'])}"
    col = c["collect"]
    if col["exc"]:
        s += f" | collect:{col['exc']}"
    return s


summary = {}
for vd in sorted(p for p in root.iterdir() if p.is_dir()):
    row = {}
    b1 = vd / "b1_behavior.out"
    if b1.exists():
        try:
            beh = json.loads(next(ln for ln in b1.read_text().splitlines() if ln.startswith('{"cases"')))
        except Exception as exc:  # noqa: BLE001
            beh = {"error": repr(exc)}
        row["behavior"] = beh
    for f in sorted(vd.glob("b*_*.out")):
        if f.name.startswith("b1_"):
            continue
        st = pytest_status(f)
        failed = sorted(k.split("::")[-1] for k, v in st.items() if v != "PASSED")
        row[f.stem] = {"n": len(st), "not_passed": failed}
        if refs:
            f2p = [st.get(t, "MISSING") for t in refs["f2p"]]
            p2p = [st.get(t, "MISSING") for t in refs["p2p"]]
            row[f.stem]["sim_reward"] = int(all(s == "PASSED" for s in f2p + p2p))
            row[f.stem]["f2p"] = f"{sum(s == 'PASSED' for s in f2p)}/{len(f2p)}"
            row[f.stem]["p2p"] = f"{sum(s == 'PASSED' for s in p2p)}/{len(p2p)}"
    summary[vd.name] = row

(root / "semantic_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n")

KEYS = ["mapping", "empty", "comment_only", "falsy_zero", "syntax_brace", "list", "str", "int"]
for name, row in summary.items():
    beh = row.get("behavior", {})
    print(f"== {name}")
    if "cases" in beh:
        for k in KEYS:
            print(f"   {k:14s} {short_case(beh['cases'][k])}")
        for k, c in beh["order"].items():
            print(f"   order:{k:8s} {short_case(c)}")
        for k, c in beh["fresh_import"].items():
            print(f"   import:{k:22s} rc={c['rc']} {c['stdout'][-40:]!r} {(c['stderr_tail'] or [''])[-1][:110]}")
    for k, v in row.items():
        if k != "behavior":
            print(f"   {k}: {v}")
