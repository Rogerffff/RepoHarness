"""把 run_review.py 的 out/*/record.json 汇总成 results.md（私有对照与私有模拟评分，不是正式评分）。

用法：python summarize_review.py out > results.md
"""
import json
import sys
from pathlib import Path

ORDER = ["base", "gold", "ctx", "parity", "ctx_list", "rv_dynamotype",
         "top_only", "siblings", "depth2", "list_as_names", "null_only", "shape", "rootkey", "swallow",
         "skip_s_subtree", "rv_swallow_attr", "rv_depth4", "rv_scalar_s", "rv_tagparent", "rv_shape_key",
         "rv_top_or_null", "rv_break_after_s"]
VERSIONS = ["orig", "v2", "v2s", "v3"]
PROBE_COLS = [
    ("L.ex2_nested_S_null", "例2 嵌套"),
    ("L.deep3_S", "三层 map"),
    ("L.S_holding_map", "S 的值是 map"),
    ("L.list_map_S", "list 内 map"),
    ("K.hashM_nested_S", "主键名 M＋嵌套 S"),
    ("K.hashS_nested_S", "主键名 S＋嵌套 S"),
    ("L.batch_nested_S", "batch"),
    ("L.transact_nested_S", "transact"),
    ("N.bad_nonkey_S_dict", "非主键 S→dict"),
    ("N.bad_attrS_then_nested_N_int", "S 在前＋嵌套 N 整数"),
    ("N.bad_mapS_then_N_int", "同一 map 内 S 在前＋N 整数"),
]


def cell_probe(p, legal):
    if p is None:
        return "?"
    put = p.get("put", "?")
    if put == "ok":
        if legal:
            return "ok" if p.get("equal") else "ok≠"
        return "**存入**" if p.get("stored") else "ok"
    if put.startswith("SerEx"):
        return "SerEx"
    if put.startswith("EXC:"):
        return put[4:].replace("AttributeError", "AttrErr")
    return put.replace("TransactionCanceledException", "TxCancel")


def cell_test(g):
    if g is None:
        return "?"
    if g["reward"] == 1:
        return "**1**"
    line = next((e.split(":")[1] for e in g.get("excerpt", []) if e.startswith("tests/")), "?")
    return f"0@{line}"


def main():
    out = Path(sys.argv[1])
    recs = {}
    for v in ORDER:
        f = out / v / "record.json"
        if f.exists():
            recs[v] = json.loads(f.read_text())
    meta = json.loads((out / "meta.json").read_text()) if (out / "meta.json").exists() else {}
    print("| 版本 | 候选 sha256 | " + " | ".join(VERSIONS) + " | P2P（四版） |")
    print("|---|---|" + "---|" * len(VERSIONS) + "---|")
    for v, r in recs.items():
        tests = r.get("tests", {})
        p2p = sorted({tests[x]["p2p"] for x in VERSIONS if x in tests})
        sha = (r.get("candidate_sha256") or "—")[:8]
        print(f"| `{v}` | {sha} | " + " | ".join(cell_test(tests.get(x)) for x in VERSIONS) + f" | {'/'.join(p2p)} |")
    print()
    print("| 版本 | " + " | ".join(name for _, name in PROBE_COLS) + " |")
    print("|---|" + "---|" * len(PROBE_COLS))
    for v, r in recs.items():
        pr = r.get("probe", {})
        print(f"| `{v}` | " + " | ".join(cell_probe(pr.get(k), not k.startswith("N.bad")) for k, _ in PROBE_COLS) + " |")
    print()
    suites = {v: r["suite"]["tail"][0] for v, r in recs.items() if r.get("suite") and r["suite"].get("tail")}
    if suites:
        print("tests/test_dynamodb 全套：" + "；".join(f"`{v}` {t}" for v, t in suites.items()))
    errors = {v: r["error"] for v, r in recs.items() if r.get("error")}
    if errors:
        print("运行错误：", errors)
    if meta:
        print()
        print("测试补丁 sha256：" + "，".join(f"{k} `{v[:12]}`" for k, v in meta["tests_sha256"].items())
              + f"；gold `{meta['gold_sha256'][:12]}`；解析命令 `{meta['eval_cmd']}`，P2P {meta['p2p_count']} 项")


if __name__ == "__main__":
    main()
