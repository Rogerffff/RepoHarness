"""汇总私有行为矩阵：行为用例，列为变体；单元格 ok=Y、违例=N、只记事实=·（附关键观测）。

用法：python summarize_behavior.py <semantic_vN/out 目录> [变体...]
另输出每个变体的 orig_file／rev_file 结果行（pytest 摘要与失败的测试 ID）。
"""
import json
import re
import sys
from pathlib import Path

ORDER = ["base", "gold", "alt_modqual", "alt_hookfirst", "alt_up2024", "alt_pickle", "alt_docs",
         "w_value", "w_noval", "w_hash", "w_name", "w_str"]


def load(vdir):
    rows = {}
    f = vdir / "behavior.out"
    if not f.is_file():
        return rows
    for line in f.read_text().splitlines():
        if line.startswith("{"):
            r = json.loads(line)
            rows[r["case"]] = r
    return rows


def cell(r):
    if r is None:
        return "?"
    ok = r.get("ok")
    mark = {True: "Y", False: "N", None: "·"}[ok]
    if "error" in r:
        return "N(err)"
    for k in ("got", "tokens_equal", "keys_equal", "names_equal", "honored", "equal", "enum_enum_equal"):
        if k in r and r["case"].startswith(("samename", "hook", "class", "consequence")):
            v = r[k]
            if k == "got":
                v = ",".join(str(x).replace("from ", "") for x in v)
            return f"{mark} {k[:4]}={v}"
    return mark


def pytest_line(vdir, name):
    f = vdir / f"{name}.out"
    if not f.is_file():
        return None
    text = f.read_text(errors="replace")
    summary = [ln for ln in text.splitlines() if re.match(r"^=+ .*(passed|failed|error).* =+$", ln)]
    failed = sorted(set(re.findall(r"^(?:FAILED|ERROR) (\S+)", text, re.M)))
    return (summary[-1].strip("= ") if summary else "no summary"), failed


def main():
    out = Path(sys.argv[1])
    names = sys.argv[2:] or [n for n in ORDER if (out / n).is_dir()]
    data = {n: load(out / n) for n in names}
    cases = []
    for n in names:
        for c in data[n]:
            if c not in cases and c != "_env":
                cases.append(c)
    print("case".ljust(62) + " | " + " | ".join(names))
    for c in cases:
        print(c[:62].ljust(62) + " | " + " | ".join(cell(data[n].get(c)) for n in names))
    print()
    for n in names:
        for t in ("orig_file", "rev_file"):
            res = pytest_line(out / n, t)
            if res:
                print(f"{n:14} {t:9} {res[0]}  failed={res[1]}")


if __name__ == "__main__":
    main()
