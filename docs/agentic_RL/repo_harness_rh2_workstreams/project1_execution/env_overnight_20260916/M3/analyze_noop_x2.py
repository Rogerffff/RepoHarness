#!/usr/bin/env python3
"""对比机器 3 上同一容器内连续两次 `run_tests.sh`（noop）的解析结果。

解析规则逐字沿用 rh2/experiments/env_probe_20260909/r2e_probe.py 的 parse_pytest_output /
normalize_map / r2e_reward（Prime 口径 + 0.3 版对称去 ANSI），只读不改。
输出 runs/env_overnight_20260916/M3/noop_repeat.json。
"""
import json, os, re
from collections import Counter

ROOT = "${REPO_ROOT}"
FACTS = os.path.join(ROOT, "runs/env_overnight_20260916/M3/facts")
OUT = os.path.join(ROOT, "runs/env_overnight_20260916/M3/noop_repeat.json")
CANDS = [os.path.join(ROOT, "runs/env_probe_20260909_codex_backup/data/r2e_candidates_full.jsonl"),
         os.path.join(ROOT, "runs/env_probe_stage1_20260910/r2e_expansion_preparation/r2e_candidates_full.jsonl")]
L4 = os.path.join(ROOT, "docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L4_r2e")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def parse_pytest_output(output: str) -> dict:
    out = {}
    if "short test summary info" not in output:
        return out
    for line in output.split("short test summary info")[1].strip().split("\n"):
        if "PASSED" in line:
            out[".".join(line.split("::")[1:])] = "PASSED"
        elif "FAILED" in line:
            out[".".join(line.split("::")[1:]).split(" - ")[0]] = "FAILED"
        elif "ERROR" in line:
            parts = line.split("::")
            name = ".".join(parts[1:])
            out[name.split(" - ")[0]] = "ERROR"
    return out


def normalize_map(d: dict) -> dict:
    d = {ANSI_RE.sub("", k): v for k, v in d.items()}
    return {k.split(" - ")[0]: d[k] for k in sorted(d)}


def summary_drops(output: str):
    """统计 parser 丢弃的 SKIPPED / XFAIL / XPASS 行。"""
    if "short test summary info" not in output:
        return {"skipped_cases": 0, "xfail_lines": 0, "xpass_lines": 0, "reasons": []}
    seg = output.split("short test summary info")[1]
    sk = re.findall(r"^SKIPPED \[(\d+)\](.*)$", seg, re.M)
    return {"skipped_cases": sum(int(x[0]) for x in sk),
            "skipped_lines": len(sk),
            "xfail_lines": len(re.findall(r"^XFAIL", seg, re.M)),
            "xpass_lines": len(re.findall(r"^XPASS", seg, re.M)),
            "reasons": sorted({x[1].strip()[:80] for x in sk})[:6]}


def main():
    expected = {}
    for p in CANDS:
        for ln in open(p):
            r = json.loads(ln)
            try:
                expected[r["commit_hash"][:12]] = json.loads(r["expected_output_json"]) if r.get("expected_output_json") else {}
            except Exception:
                expected[r["commit_hash"][:12]] = {}
    tasks = {t["commit_hash"][:12]: t for t in json.load(open(os.path.join(L4, "r2e_tasks_48.json")))["tasks"]}
    rows = []
    for c12 in sorted(os.listdir(FACTS)):
        d = os.path.join(FACTS, c12, "noop_x2")
        if not os.path.isdir(d):
            continue
        rec = {"commit12": c12, "repo": tasks.get(c12, {}).get("repo"), "group": tasks.get(c12, {}).get("group")}
        st = open(os.path.join(d, "_P4STATUS")).read().strip() if os.path.exists(os.path.join(d, "_P4STATUS")) else "MISSING"
        rec["status"] = st
        rcf = os.path.join(d, "rc.txt")
        if os.path.exists(rcf):
            for ln in open(rcf):
                if "=" in ln:
                    k, v = ln.strip().split("=", 1)
                    rec[k] = v
        maps = []
        for i in (1, 2):
            f = os.path.join(d, f"out{i}.txt")
            if not os.path.exists(f):
                maps.append(None); continue
            txt = open(f, errors="replace").read()
            m = normalize_map(parse_pytest_output(txt))
            maps.append(m)
            rec[f"parsed_n{i}"] = len(m)
            rec[f"drops{i}"] = summary_drops(txt)
            rec[f"status_counts{i}"] = dict(Counter(m.values()))
            rec[f"log_bytes{i}"] = len(txt)
        exp = normalize_map(expected.get(c12, {}))
        rec["expected_n"] = len(exp)
        if maps[0] is not None and maps[1] is not None:
            m1, m2 = maps
            rec["run1_eq_run2"] = (m1 == m2)
            rec["keys_only_in_run1"] = sorted(set(m1) - set(m2))[:8]
            rec["keys_only_in_run2"] = sorted(set(m2) - set(m1))[:8]
            rec["status_flips_run1_run2"] = [(k, m1[k], m2[k]) for k in m1 if k in m2 and m1[k] != m2[k]][:8]
            rec["n_status_flips"] = sum(1 for k in m1 if k in m2 and m1[k] != m2[k])
            for i, m in ((1, m1), (2, m2)):
                rec[f"vs_expected{i}"] = {
                    "n_missing": sum(1 for k in exp if k not in m),
                    "n_extra": sum(1 for k in m if k not in exp),
                    "n_mismatch": sum(1 for k in exp if k in m and m[k] != exp[k]),
                    "mismatch_sample": [(k, exp[k], m[k]) for k in exp if k in m and m[k] != exp[k]][:5],
                    "missing_sample": [k for k in exp if k not in m][:5],
                    "extra_sample": [k for k in m if k not in exp][:5],
                }
                # 复刻 r2e_probe 的 reward：长度相等且每个非空键状态一致
                rw = 1
                if len(m) != len(exp):
                    rw = 0
                else:
                    for k in m:
                        if k and (k not in exp or m[k] != exp[k]):
                            rw = 0; break
                rec[f"noop_reward{i}"] = rw
        for name in ("cache_before", "cache_mid", "cache_after"):
            f = os.path.join(d, name + ".txt")
            rec[name] = open(f, errors="replace").read().strip().splitlines()[0][:70] if os.path.exists(f) else None
        f = os.path.join(d, "status_after.txt")
        if os.path.exists(f):
            rec["worktree_after_lines"] = len([l for l in open(f, errors="replace") if l.strip()])
            rec["worktree_after"] = [l.strip() for l in open(f, errors="replace") if l.strip()][:12]
        rows.append(rec)
    doc = {"schema": "rh2.env_overnight.m3.noop_repeat.v1", "machine": "机器 3",
           "parser": "r2e_probe/0.3 同规则（本地复刻）", "n": len(rows), "tasks": rows}
    json.dump(doc, open(OUT, "w"), ensure_ascii=False, indent=1)
    print("wrote", OUT, len(rows))


if __name__ == "__main__":
    main()
