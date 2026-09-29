"""私有模拟评分（不是正式评分）：按评分包的 F2P/P2P 名单，逐项读 pytest -rA 的 PASSED/FAILED 行。
用法：python simgrade.py <semantic_control 输出目录> <grading_bundles_v2_v0.jsonl> [--cmd t1_test_validators]
"""
import json
import re
import sys
from pathlib import Path

out_dir, bundles = Path(sys.argv[1]), sys.argv[2]
cmd = sys.argv[sys.argv.index("--cmd") + 1] if "--cmd" in sys.argv else "t1_test_validators"
iid = "pydantic__pydantic-8567"
g = next(json.loads(x) for x in open(bundles) if json.loads(x)["instance_id"] == iid)
f2p, p2p = g["fail_to_pass"], g["pass_to_pass"]
rows = {}
for vd in sorted(p for p in out_dir.iterdir() if p.is_dir()):
    text = (vd / f"{cmd}.out").read_text()
    status = {}
    # -vv 逐项行：`tests/x.py::name PASSED`（与正式 eval 命令同一格式）
    for m in re.finditer(r"^(tests/\S+) (PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\b", text, re.M):
        status.setdefault(m.group(1), m.group(2))
    f2p_ok = sum(status.get(t) == "PASSED" for t in f2p)
    p2p_ok = sum(status.get(t) == "PASSED" for t in p2p)
    missing = [t for t in f2p + p2p if t not in status]
    fail_line = next((ln for ln in text.splitlines() if ln.startswith("E ") or ln.startswith("E   ")), "")
    rows[vd.name] = {"reward": int(f2p_ok == len(f2p) and p2p_ok == len(p2p)), "f2p": f"{f2p_ok}/{len(f2p)}",
                     "p2p": f"{p2p_ok}/{len(p2p)}", "missing": len(missing), "first_E_line": fail_line[:200]}
for k, v in rows.items():
    print(k, json.dumps(v, ensure_ascii=False))
(out_dir / "simgrade.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n")
