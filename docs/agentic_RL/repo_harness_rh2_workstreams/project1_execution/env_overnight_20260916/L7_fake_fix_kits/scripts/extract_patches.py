#!/usr/bin/env python3
"""从 s2 四面材料抽出 gold / test_patch，并打印题级事实。只读，不改任何上游文件。"""
import json, os, sys

ING = "${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest"
OUT = "${REPO_ROOT}/runs/env_overnight_20260916/L7_fake_fix_kits/patches"

def load(fn, ids):
    got = {}
    with open(os.path.join(ING, fn)) as f:
        for line in f:
            if not line.strip():
                continue
            d = json.loads(line)
            if d.get("instance_id") in ids:
                got[d["instance_id"]] = d
    return got

def main(ids):
    ids = set(ids)
    pub = load("public_bundles_v0.jsonl", ids)
    gra = load("grading_bundles_v2_v0.jsonl", ids)
    val = load("validation_bundles_v0.jsonl", ids)
    os.makedirs(OUT, exist_ok=True)
    facts = {}
    for iid in sorted(ids):
        p, g, v = pub.get(iid), gra.get(iid), val.get(iid)
        if not (p and g and v):
            print(f"[MISS] {iid} pub={bool(p)} grading={bool(g)} val={bool(v)}")
            continue
        with open(os.path.join(OUT, f"{iid}.gold.diff"), "w") as f:
            f.write(v["golden_patch"])
        with open(os.path.join(OUT, f"{iid}.test_patch.diff"), "w") as f:
            f.write(g["test_patch"])
        facts[iid] = {
            "instance_id": iid, "repo": p["repo"], "image": p["image"],
            "base_commit": p["base_commit"], "workdir": p.get("workdir", "/testbed"),
            "version": g.get("version"), "python_version": g.get("python_version"),
            "eval_cmd": g.get("eval_cmd"),
            "fail_to_pass": g["fail_to_pass"], "pass_to_pass": g["pass_to_pass"],
            "f2p_n": len(g["fail_to_pass"]), "p2p_n": len(g["pass_to_pass"]),
            "test_patch_paths": sorted({l.split(" b/", 1)[1].strip()
                                        for l in g["test_patch"].splitlines()
                                        if l.startswith("diff --git ")}),
            "gold_paths": sorted({l.split(" b/", 1)[1].strip()
                                  for l in v["golden_patch"].splitlines()
                                  if l.startswith("diff --git ")}),
        }
    with open(os.path.join(OUT, "_facts.json"), "w") as f:
        json.dump(facts, f, ensure_ascii=False, indent=1)
    print(json.dumps({k: {kk: vv for kk, vv in vd.items()
                          if kk not in ("fail_to_pass", "pass_to_pass")}
                      for k, vd in facts.items()}, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main(sys.argv[1:])
