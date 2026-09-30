"""生成本批新写的候选补丁（相对 base 的 coverage/jsonreport.py，git apply 格式）。

用法：python _make_cands.py <base 的 coverage/jsonreport.py> <输出目录>
每个候选只改 coverage/jsonreport.py；编辑都以 base 原文片段为锚（每个锚恰好出现一次）。
"""
import difflib
import sys
from pathlib import Path

base = Path(sys.argv[1]).read_text()
out = Path(sys.argv[2])

INIT = "        self.total = Numbers()\n        self.report_data = {}\n"
TOTALS_BR = (
    "            self.report_data[\"totals\"].update({\n"
    "                'num_branches': self.total.n_branches,\n"
    "                'num_partial_branches': self.total.n_partial_branches,\n"
    "            })\n"
)
TOTALS_LINES = "            'excluded_lines': self.total.n_excluded,\n        }\n"
FILE_BR = (
    "        if coverage_data.has_arcs():\n"
    "            reported_file['summary'].update({\n"
    "                'num_branches': nums.n_branches,\n"
    "                'num_partial_branches': nums.n_partial_branches,\n"
    "            })\n"
)
for anchor in (INIT, TOTALS_BR, TOTALS_LINES, FILE_BR):
    assert base.count(anchor) == 1, anchor


def totals_with(covered, missing, extra=""):
    return (
        "            self.report_data[\"totals\"].update({\n"
        "                'num_branches': self.total.n_branches,\n"
        "                'num_partial_branches': self.total.n_partial_branches,\n"
        f"                'covered_branches': {covered},\n"
        f"                'missing_branches': {missing},\n"
        f"{extra}"
        "            })\n"
    )


GOLD_TOTALS = totals_with("self.total.n_executed_branches", "self.total.n_missing_branches")

CANDS = {
    # 只对单文件成立：逐文件计数用赋值代替累加（A1 的一字之差），totals 只剩最后一个文件的数
    "LF": [
        (INIT, INIT + "        self.covered_branches = 0\n        self.missing_branches = 0\n"),
        (TOTALS_BR, totals_with("self.covered_branches", "self.missing_branches")),
        (FILE_BR, "        if coverage_data.has_arcs():\n"
                  "            self.covered_branches = nums.n_executed_branches\n"
                  "            self.missing_branches = nums.n_missing_branches\n"
                  + FILE_BR[len("        if coverage_data.has_arcs():\n"):]),
    ],
    # 对称写法的错误版：每文件 summary 写的是累加到当前文件为止的总数（单文件时恰好等于本文件）
    "FC": [
        (TOTALS_BR, GOLD_TOTALS),
        (FILE_BR, "        if coverage_data.has_arcs():\n"
                  "            reported_file['summary'].update({\n"
                  "                'num_branches': nums.n_branches,\n"
                  "                'num_partial_branches': nums.n_partial_branches,\n"
                  "                'covered_branches': self.total.n_executed_branches,\n"
                  "                'missing_branches': self.total.n_missing_branches,\n"
                  "            })\n"),
    ],
    # 阈值：没有任何分支时省略两键（分支模式、零分支）
    "NB": [
        (TOTALS_BR, TOTALS_BR
         + "            if self.total.n_branches:\n"
           "                self.report_data[\"totals\"].update({\n"
           "                    'covered_branches': self.total.n_executed_branches,\n"
           "                    'missing_branches': self.total.n_missing_branches,\n"
           "                })\n"),
    ],
    # 行模式也输出两键（值为 0）
    "LM": [
        (TOTALS_LINES, "            'excluded_lines': self.total.n_excluded,\n"
                       "            'covered_branches': self.total.n_executed_branches,\n"
                       "            'missing_branches': self.total.n_missing_branches,\n"
                       "        }\n"),
    ],
    # totals 另加一个题面没点名的键（分支覆盖率），两键本身正确
    "XP": [
        (TOTALS_BR, totals_with(
            "self.total.n_executed_branches", "self.total.n_missing_branches",
            "                'percent_covered_branches': (\n"
            "                    100.0 * self.total.n_executed_branches / self.total.n_branches\n"
            "                    if self.total.n_branches else 100.0\n"
            "                ),\n")),
    ],
}

for name, edits in CANDS.items():
    text = base
    for old, new in edits:
        assert text.count(old) == 1, (name, old)
        text = text.replace(old, new)
    diff = difflib.unified_diff(
        base.splitlines(keepends=True), text.splitlines(keepends=True),
        fromfile="a/coverage/jsonreport.py", tofile="b/coverage/jsonreport.py")
    (out / f"{name}.patch").write_text("diff --git a/coverage/jsonreport.py b/coverage/jsonreport.py\n" + "".join(diff))
    print(name, "ok")
