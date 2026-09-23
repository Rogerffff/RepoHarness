#!/usr/bin/env python3
"""比对机器 3 上 gold gate 的两次独立运行（a1 / a2，同条件、各自一次性容器）。

逐键比对 `status_map.json`（r2e_probe 解析产物），并统计被 parser 丢弃的
SKIPPED / XFAIL / XPASS 行是否在两次之间波动。
输出 docs/.../M3/M3_gold_repeat.json。
"""
import json, os, re
from collections import Counter

ROOT = "${REPO_ROOT}"
LEDGER = os.path.join(ROOT, "runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl")
LOGS = os.path.join(ROOT, "runs/env_overnight_20260916/M3/gold_ledger/logs_r2e")
PKG = os.path.join(ROOT, "docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/M3")
OUT = os.path.join(PKG, "M3_gold_repeat.json")
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def norm(d):
    d = {ANSI.sub("", k): v for k, v in d.items()}
    return {k.split(" - ")[0]: d[k] for k in sorted(d)}


def drops(txt):
    if "short test summary info" not in txt:
        return {"skipped_cases": 0, "skipped_lines": 0, "xfail_lines": 0, "xpass_lines": 0, "reasons": []}
    seg = txt.split("short test summary info")[1]
    sk = re.findall(r"^SKIPPED \[(\d+)\](.*)$", seg, re.M)
    return {"skipped_cases": sum(int(x[0]) for x in sk), "skipped_lines": len(sk),
            "xfail_lines": len(re.findall(r"^XFAIL", seg, re.M)),
            "xpass_lines": len(re.findall(r"^XPASS", seg, re.M)),
            "reasons": sorted({x[1].strip()[:70] for x in sk})[:5]}


def main():
    rows = [json.loads(l) for l in open(LEDGER)]
    by = {}
    for r in rows:
        by.setdefault(r["commit_hash"][:12], {})[r["attempt"]] = r
    out = []
    for c12 in sorted(by):
        a = by[c12]
        r1, r2 = a.get(1), a.get(2)
        rec = {"commit12": c12, "repo": (r1 or r2)["repo"], "gate": "gold"}
        if not (r1 and r2):
            rec["status"] = "missing_attempt"
            out.append(rec)
            continue
        d = os.path.join(LOGS, rec["repo"], c12, "gold")
        m1 = m2 = None
        for att, tgt in ((1, "a1"), (2, "a2")):
            p = os.path.join(d, tgt, "status_map.json")
            if os.path.exists(p):
                m = norm(json.load(open(p)))
                if att == 1:
                    m1 = m
                else:
                    m2 = m
        t1 = open(os.path.join(d, "a1", "test_output.txt"), errors="replace").read() if os.path.exists(os.path.join(d, "a1", "test_output.txt")) else ""
        t2 = open(os.path.join(d, "a2", "test_output.txt"), errors="replace").read() if os.path.exists(os.path.join(d, "a2", "test_output.txt")) else ""
        rec.update({
            "reward_a1": r1["reward"], "reward_a2": r2["reward"],
            "result_a1": r1["result"], "result_a2": r2["result"],
            "reward_same": r1["reward"] == r2["reward"],
            "parsed_n_a1": (r1.get("reward_details") or {}).get("parsed_n"),
            "parsed_n_a2": (r2.get("reward_details") or {}).get("parsed_n"),
            "expected_n": r1.get("expected_n"),
            "t_test_a1": r1.get("t_test"), "t_test_a2": r2.get("t_test"),
            "test_rc_a1": r1.get("test_rc"), "test_rc_a2": r2.get("test_rc"),
            "log_sha_same": r1.get("log_sha256") == r2.get("log_sha256"),
            "fixture_digest_same": r1.get("fixture_digest") == r2.get("fixture_digest"),
            "image_digest_same": r1.get("image_digest_actual") == r2.get("image_digest_actual"),
            "drops_a1": drops(t1), "drops_a2": drops(t2),
        })
        if m1 is not None and m2 is not None:
            rec["map_identical"] = (m1 == m2)
            rec["keys_only_a1"] = sorted(set(m1) - set(m2))[:10]
            rec["keys_only_a2"] = sorted(set(m2) - set(m1))[:10]
            rec["status_flips"] = [(k, m1[k], m2[k]) for k in m1 if k in m2 and m1[k] != m2[k]][:10]
            rec["n_status_flips"] = sum(1 for k in m1 if k in m2 and m1[k] != m2[k])
            rec["n_key_diff"] = len(set(m1) ^ set(m2))
            # 分类：键集差异是否能用 SKIPPED/XFAIL 波动解释
            ds = rec["drops_a1"]["skipped_cases"] != rec["drops_a2"]["skipped_cases"] or \
                 rec["drops_a1"]["xfail_lines"] != rec["drops_a2"]["xfail_lines"]
            rec["drops_changed"] = ds
            if rec["map_identical"]:
                rec["category"] = "identical"
            elif rec["n_key_diff"] and ds:
                rec["category"] = "key_set_changed_with_skip_drift"
            elif rec["n_key_diff"]:
                rec["category"] = "key_set_changed_no_skip_drift"
            else:
                rec["category"] = "status_flip_only"
        else:
            rec["map_identical"] = None
            rec["category"] = "status_map_missing"
        out.append(rec)
    doc = {"schema": "rh2.env_overnight.m3.gold_repeat.v1", "machine": "机器 3",
           "note": "两次 gold 各自从原镜像起一次性容器、--network none、同一 r2e_probe/0.3 副本；"
                   "a1 用 3 workers、a2 用 4 workers，其余条件相同",
           "n": len(out),
           "summary": {
               "reward_same": dict(Counter(r.get("reward_same") for r in out)),
               "map_identical": dict(Counter(r.get("map_identical") for r in out)),
               "log_sha_same": dict(Counter(r.get("log_sha_same") for r in out)),
               "category": dict(Counter(r.get("category") for r in out)),
           },
           "tasks": out}
    json.dump(doc, open(OUT, "w"), ensure_ascii=False, indent=1)
    print("wrote", OUT, len(out))
    print(json.dumps(doc["summary"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
