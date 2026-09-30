"""汇总私有模拟结果：grades.jsonl（逐键评分）+ probe.out（行为矩阵）+ pub_test_json.out（公开测试）→ summary_table.json。

用法：python summarize.py <run_matrix 的输出目录>
"""
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
out = Path(sys.argv[1]).resolve()
SHORT = {
    "JsonReportTest.test_branch_coverage": "BC",
    "JsonReportTest.test_simple_line_coverage": "LINE",
    "JsonReportTest.test_context_relative": "CTX_R",
    "JsonReportTest.test_context_non_relative": "CTX_NR",
    "JsonReportTest.test_branch_totals_count_branch_arcs": "K1",
    "JsonReportTest.test_branch_totals_from_saved_branch_data": "K2",
    "JsonReportTest.test_branch_totals_add_up_across_files": "K3",
}
grades = {}
for line in (out / "grades.jsonl").read_text().splitlines():
    g = json.loads(line)
    grades.setdefault(g["cand"], {})[g["material"]] = {
        "reward": g["reward"], "fail": sorted(SHORT.get(k, k) for k in g["mismatch"]),
        "n_parsed": g["n_parsed"], "n_expected": g["n_expected"], "unexpected": g["unexpected"]}

table = {}
for cand, mats in grades.items():
    d = out / cand
    diff = (d / "candidate.diff").read_bytes()
    patch = HERE / f"{cand}.patch"
    probe = {}
    for line in (d / "probe.out").read_text().splitlines():
        if line.startswith("PROBE {"):
            p = json.loads(line[len("PROBE "):])
            probe[p["scenario"]] = p["result"]

    def tb(s):
        r = probe.get(s, {})
        if "error" in r:
            return "error: " + r["error"]
        t = r.get("totals_branch", {})
        return "%s/%s (num %s)" % (t.get("covered_branches"), t.get("missing_branches"), t.get("num_branches"))

    s2 = probe.get("S2_two_files", {})
    pub = (d / "pub_test_json.out").read_text()
    m = re.search(r"^=* ?(\d+ (?:passed|failed).*?) in [\d.]+ seconds", pub, re.M)
    table[cand] = {
        "patch_sha256": hashlib.sha256(patch.read_bytes()).hexdigest() if patch.exists() else None,
        "exported_diff_sha256": hashlib.sha256(diff).hexdigest() if diff else None,
        "rewards": {k: v["reward"] for k, v in mats.items()},
        "fail_keys": {k: v["fail"] for k, v in mats.items()},
        "all_parsed": all(v["n_parsed"] == v["n_expected"] and not v["unexpected"] for v in mats.values()),
        "probe_totals_cov_miss": {s: tb(s) for s in ["S1_single_branchy", "S2_two_files",
                                                     "S3_saved_reload_no_branch_cfg", "S4_cli_run_branch_then_json",
                                                     "S5_branch_mode_zero_branches", "S6_line_mode_two_files"]},
        "probe_files_S2": s2.get("files"),
        "probe_extra_keys_S2": {"totals": s2.get("totals_extra_keys"), "files": s2.get("files_extra_keys")},
        "xml_S2": s2.get("xml"),
        "public_test_json": m.group(1) if m else "?",
        "public_test_json_failed": sorted(set(re.findall(r"^FAILED tests/test_json.py::JsonReportTest::(\w+)", pub, re.M))),
    }
(out / "summary_table.json").write_text(json.dumps(table, ensure_ascii=False, indent=1) + "\n")
for cand, t in table.items():
    print(cand, t["rewards"], "| S2:", t["probe_totals_cov_miss"]["S2_two_files"], "| pub:", t["public_test_json"],
          t["public_test_json_failed"])
