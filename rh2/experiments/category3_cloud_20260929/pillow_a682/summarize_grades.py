"""把 run_matrix.py 的 grades.jsonl 汇总成 候选 × 隐藏测试版本 的表（私有模拟分数）。

每格：上游口径 prime_calculate_reward 的 reward，括号里是不符的键（缩写）。
另核对 RH2 生产口径（scoring.expected_map_matches：键集相等且逐键相等才得 1）：
reward==1 当且仅当 mismatch 与 unexpected 都为空；两种口径不一致时在格内标 [口径不一致]。
用法：python summarize_grades.py <grades.jsonl> [版本 id,...]
"""
import json
import sys

rows = [json.loads(line) for line in open(sys.argv[1])]
mats = sys.argv[2].split(",") if len(sys.argv) > 2 else [k for k in rows[0] if k != "variant"]
seen = {}
for r in rows:  # 同一候选重复出现时取最后一次
    seen[r["variant"]] = r
print("| 候选 | " + " | ".join(mats) + " |")
print("|" + " --- |" * (len(mats) + 1))
disagree = 0
for v, r in seen.items():
    cells = []
    for m in mats:
        g = r.get(m)
        if not isinstance(g, dict) or "reward" not in g:
            cells.append(str(g))
            continue
        union_ok = not g["mismatch"] and not g["unexpected"] and g["n_parsed"] > 0
        flag = "" if (g["reward"] == 1.0) == union_ok else " [口径不一致]"
        disagree += bool(flag)
        bad = sorted(set(g["mismatch"]) | set(g["unexpected"]))
        short = ", ".join(k.replace("test_", "") for k in bad)
        cells.append(f"{int(g['reward'])}" + (f"（{short}）" if bad else "") + flag)
    print(f"| {v} | " + " | ".join(cells) + " |")
print(f"\n口径不一致的格数：{disagree}")
