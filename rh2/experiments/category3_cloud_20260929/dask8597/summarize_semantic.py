"""汇总私有矩阵：behavior（逐实例）与 orig_file／rev_file（按参考名单逐 ID 的私有模拟评分）。

用法：python summarize_semantic.py <semantic 输出目录 out/> [orig_file|rev_file]
私有模拟评分：从 pytest -rA 的结果行取每个测试 ID 的状态；F2P 全 PASSED 且 P2P 全 PASSED 记 1。
这只是私有模拟，不是正式评分（见 environment.md §3）。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path("/home/user/RepoHarness")
BUNDLE = ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest/grading_bundles_v2_v0.jsonl"
NONREF = ["dask/array/tests/test_slicing.py::test_getitem_avoids_large_chunks",
          "dask/array/tests/test_slicing.py::test_slicing_integer_no_warnings"]


def refs():
    for line in BUNDLE.open():
        d = json.loads(line)
        if d["instance_id"] == "dask__dask-8597":
            return d["fail_to_pass"], d["pass_to_pass"]


def statuses(text):
    st = {}
    for m in re.finditer(r"^(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS) (\S+)", text, re.M):
        st.setdefault(m.group(2), m.group(1))
    return st


def main():
    out = Path(sys.argv[1])
    which = sys.argv[2] if len(sys.argv) > 2 else "orig_file"
    f2p, p2p = refs()
    rows = {}
    for vd in sorted(p for p in out.iterdir() if p.is_dir()):
        row = {}
        tf = vd / f"{which}.out"
        if tf.exists():
            st = statuses(tf.read_text())
            f2p_ok = sum(st.get(t) == "PASSED" for t in f2p)
            p2p_fail = [t.split("::")[1] for t in p2p if st.get(t) != "PASSED"]
            row["sim_reward"] = int(f2p_ok == len(f2p) and not p2p_fail)
            row["f2p"] = f"{f2p_ok}/{len(f2p)}"
            row["p2p_fail"] = p2p_fail
            row["nonref"] = {t.split("::")[1]: st.get(t) for t in NONREF}
            m = re.search(r"=+ (.*(?:passed|failed).*) in [\d.]+s", tf.read_text())
            row["pytest_tail"] = m.group(1) if m else None
        bf = vd / "behavior.out"
        if bf.exists() and which == "orig_file":
            recs = [json.loads(line) for line in bf.read_text().splitlines() if line.startswith("{")]
            row["behavior_fail"] = [
                f"{r['case']}|{r['cfg'].get('array.slicing.split-large-chunks', '-')}" for r in recs if not r["ok"]
            ]
        rows[vd.name] = row
    print(json.dumps(rows, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
