# 汇总私有行为矩阵：从 <out>/<variant>/c1_matrix.out 中取出 JSON（候选可能在其前打印告警），
# 输出紧凑表格与 rc 汇总。用法：python summarize_matrix.py <semantic_out_dir>
import json
import sys
from pathlib import Path

out = Path(sys.argv[1])
summary = json.loads((out / "summary.json").read_text())
lines = []
for v, rcs in summary.items():
    text = (out / v / "c1_matrix.out").read_text()
    start = text.index("{\n")
    d, end = json.JSONDecoder().raw_decode(text, start)
    noise = (text[:start] + text[end:]).strip()
    lines.append("===== {}  rc={}".format(v, json.dumps(rcs)))
    if noise:
        lines.append("  [other output] " + noise.replace("\n", " | ")[:200])
    for k, r in d.items():
        runs = "; ".join("{} :: {}".format(w, c) for w, c in r["runs"]) or "(none)"
        exc = r["exception"] or "-"
        if len(exc) > 60:
            exc = exc[:60] + "…"
        cwd = "restored" if r["cwd_restored"] else "LEAKED->" + r["cwd_after"]
        src = "" if r["source_folder_unchanged"] else " SOURCE_FOLDER_CHANGED"
        lines.append("  {:26s} runs=[{}] exc={} cwd={}{}".format(k, runs, exc, cwd, src))
text = "\n".join(lines) + "\n"
(out / "matrix_summary.txt").write_text(text)
print(text)
