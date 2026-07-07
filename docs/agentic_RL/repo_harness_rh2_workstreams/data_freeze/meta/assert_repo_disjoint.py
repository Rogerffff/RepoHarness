#!/usr/bin/env python3
"""DF-1 断言：训练候选 repo / held-out repo / Verified repo 三方互斥。
纯 stdlib；输出 meta/repo_disjoint_report.json，任一断言失败以非零退出（fail-closed）。
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent


def repos(path, key):
    out = set()
    for line in (HERE / path).read_text().splitlines():
        if line.strip():
            out.add(json.loads(line)[key].split("/")[-1].lower())
    return out


verified = repos("verified.jsonl", "repo")
swe_gym = repos("swe_gym_full.jsonl", "repo")          # Lite ⊂ Full，断言用 Full 即覆盖
r2e = repos("r2e_subset.jsonl", "repo_name")

# E5 定案的 held-out 切分（冻结提案 DF-7 的输入）
heldout = {"tornado", "pyramid", "hydra", "bokeh"}
train_pool = (swe_gym | r2e) - heldout

report = {
    "verified_repos": sorted(verified),
    "swe_gym_repos": sorted(swe_gym),
    "r2e_repos": sorted(r2e),
    "heldout_repos": sorted(heldout),
    "assertions": {
        "train_pool ∩ verified": sorted(train_pool & verified),
        "heldout ∩ verified": sorted(heldout & verified),
        "train_pool ∩ heldout": sorted(train_pool & heldout),
        "heldout ⊆ 数据集": sorted(heldout - (swe_gym | r2e)),
        "跨源重复 repo（swe_gym ∩ r2e，需去重注意）": sorted(swe_gym & r2e),
    },
}
ok = (
    not report["assertions"]["train_pool ∩ verified"]
    and not report["assertions"]["heldout ∩ verified"]
    and not report["assertions"]["train_pool ∩ heldout"]
    and not report["assertions"]["heldout ⊆ 数据集"]
)
report["verdict"] = "PASS" if ok else "FAIL"
(HERE / "repo_disjoint_report.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2)
)
print(json.dumps(report["assertions"], ensure_ascii=False, indent=2))
print("verdict:", report["verdict"])
sys.exit(0 if ok else 1)
