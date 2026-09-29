"""汇总 dask__dask-8801 正式评分账本。

用法：python summarize_formal.py <formal 目录> <参考名单 refs.json> [候选顺序...]
对每个 ledger_<候选>.jsonl：reward、F2P/P2P、参考缺席、安装与测试退出码、清理、候选补丁 sha256；
再从评分日志的 short test summary 逐项取状态，得出：
- 两项未计分的权限测试 test_collect_yaml_permission_errors[directory]/[file] 的状态；
- 若把这两项加入 P2P（修订建议之一），按同一日志推算的 reward（“推算”，不是正式 reward）；
- 未通过测试的第一条失败摘要。
输出 <目录>/formal_summary.json 并打印表格。
"""

import json
import re
import sys
from pathlib import Path

root, refs_path = Path(sys.argv[1]), Path(sys.argv[2])
order = sys.argv[3:]
refs = json.loads(refs_path.read_text())
PERM = [
    "dask/tests/test_config.py::test_collect_yaml_permission_errors[directory]",
    "dask/tests/test_config.py::test_collect_yaml_permission_errors[file]",
]
LINE = re.compile(r"^(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS) (dask/\S+)(?: - (.*))?$")

rows = {}
for ledger in sorted(root.glob("ledger_*.jsonl")):
    name = ledger.stem[len("ledger_"):]
    r = json.loads(ledger.read_text().splitlines()[-1])
    rep = r["report"]
    log = Path(r["log"]["path"])
    status, first_fail = {}, {}
    in_summary = False
    for ln in log.read_text(errors="replace").splitlines():
        if "short test summary info" in ln:
            in_summary = True
            continue
        if in_summary:
            m = LINE.match(ln)
            if m:
                status[m.group(2)] = m.group(1)
                if m.group(1) != "PASSED" and m.group(3):
                    first_fail[m.group(2).split("::")[-1]] = m.group(3)
    f2p_ok = all(status.get(t) == "PASSED" for t in refs["f2p"])
    p2p_ok = all(status.get(t) == "PASSED" for t in refs["p2p"])
    perm = {t.split("[")[-1].rstrip("]"): status.get(t, "MISSING") for t in PERM}
    rows[name] = {
        "reward": rep["reward"],
        "f2p": f"{rep['f2p_pass']}/{rep['f2p_total']}",
        "p2p": f"{rep['p2p_total'] - rep['p2p_fail']}/{rep['p2p_total']}",
        "reference_missing": r["reference_missing_count"],
        "install_rc": r["install"]["install_rc_last_command"],
        "test_rc": r["test"]["rc"],
        "segment_completed": r["test"]["segment_completed"],
        "parsed_tests": r["verdict_diagnostics"]["num_parsed_tests"],
        "cleanup_removed": r["cleanup"]["removed"],
        "apply_method": r["candidate"]["apply_method"],
        "patch_sha256": r["candidate"]["patch_sha256"],
        "grader_version": rep["grader_version"],
        "run_id": r["run_id"],
        "log": log.name,
        "log_sha256": r["log"]["sha256"],
        "permission_tests": perm,
        "projected_reward_with_perm_in_p2p": int(f2p_ok and p2p_ok and all(v == "PASSED" for v in perm.values())),
        "log_says_resolved_consistent": (f2p_ok and p2p_ok) == (rep["reward"] == 1.0),
        "not_passed": {k: v for k, v in first_fail.items()},
    }

(root / "formal_summary.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n")
names = [n for n in order if n in rows] + [n for n in rows if n not in order]
print(f"{'candidate':17s} rew  F2P  P2P    miss inst test perm(dir,file)  proj  clean  sha")
for n in names:
    x = rows[n]
    print(
        f"{n:17s} {x['reward']:.0f}   {x['f2p']:4s} {x['p2p']:6s} {x['reference_missing']}    {x['install_rc']}    "
        f"{x['test_rc']}    {x['permission_tests']['directory'][:4]},{x['permission_tests']['file'][:4]}       "
        f"{x['projected_reward_with_perm_in_p2p']}     {x['cleanup_removed']!s:5s}  {(x['patch_sha256'] or '-')[:12]}"
        f"{'' if x['log_says_resolved_consistent'] else '  !!inconsistent'}"
    )
    for t, why in x["not_passed"].items():
        print(f"      {t}: {why[:110]}")
