"""把 semantic_control 输出的 b1_behavior.out 汇总成表（按公开要求判定，不以 gold 为准）。

判定：
- pq_*：端点精确（ends_ok）且有序、在 [min,max] 内、dtype 保持 → ok；
- si_*：divisions 两端精确、每行落在自己的区间、内容与 pandas 一致（不丢行）→ ok；
- small_int：列出 x 的 divisions 集合；auto_path、min_dtype 只记录。
用法：python summarize_behavior.py <semantic 输出目录> [变体...]
"""
import json
import sys
from pathlib import Path


def verdict(r):
    if "error" in r:
        return "ERR"
    kind = r.get("kind")
    if kind == "pq":
        ok = r["ends_ok"] and r["sorted"] and r["within"] and r["dtype_ok"]
        return "ok" if ok else f"x({r['first_minus_min']:+d}/{r['last_minus_max']:+d})"
    if kind == "si":
        ok = r["div_ends_ok"] and r["rows_in_bounds"] and r["content_ok"]
        lost = "" if r["content_ok"] else " lost"
        return "ok" if ok else f"x({r['div_first_minus_min']:+d}/{r['div_last_minus_max']:+d}{lost})"
    if kind == "small":
        return "{" + ",".join(map(str, r["x_set"])) + "}" + ("" if r["x_assert_eq"] is True else " ae!")
    if kind == "auto":
        return f"first_eq_min={r['div_first_eq_min']} rows={r.get('rows')}/{r.get('rows_expected')}"
    if kind == "min_dtype":
        return f"series_min={r['series_min'][1]} index_min={r['index_min'][1]}"
    return "?"


def main():
    out = Path(sys.argv[1])
    variants = sys.argv[2:] or sorted(p.name for p in out.iterdir() if (p / "b1_behavior.out").exists())
    table, cases = {}, []
    for v in variants:
        rows = {}
        for line in (out / v / "b1_behavior.out").read_text().splitlines():
            if not line.startswith("{"):
                continue
            r = json.loads(line)
            rows[r["case"]] = verdict(r)
            if r["case"] not in cases:
                cases.append(r["case"])
        table[v] = rows
    print("| case | " + " | ".join(variants) + " |")
    print("|---" * (len(variants) + 1) + "|")
    for c in cases:
        print(f"| {c} | " + " | ".join(table[v].get(c, "-") for v in variants) + " |")


if __name__ == "__main__":
    main()
