#!/usr/bin/env python3
"""汇总 env probe 账本为 Markdown 表（供报告与人工复核）。"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path


def load(p):
    rows = []
    if Path(p).exists():
        for ln in open(p):
            try:
                rows.append(json.loads(ln))
            except Exception:
                pass
    return rows


def fmt(v):
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:.1f}"
    return str(v)


def swegym(rows, out):
    out.append("## SWE-Gym 官方脚本探针（fork 242429c1，fresh 容器）\n")
    # facts
    facts = [r for r in rows if r["gate"] == "facts"]
    if facts:
        out.append("### 环境事实（facts）\n")
        out.append("| instance | digest 一致 | arch | HEAD==base | tags | remotes | base 之后仍可达的提交 | 不可达对象 | python | pypi(默认网络) | 根目录控制文件(conftest/pytest.ini/setup.cfg/pyproject/tox) |")
        out.append("|---|---|---|---|---:|---:|---:|---:|---|---|---|")
        for r in sorted(facts, key=lambda x: x["instance_id"]):
            f = r.get("facts", {})
            ctl = "/".join(f.get(k, "?") for k in ("conftest_root", "pytest_ini", "setup_cfg", "pyproject", "tox_ini"))
            out.append(f"| {r['instance_id']} | {r.get('image_digest_match')} | {r.get('image_arch')} | {r.get('head_equals_base')} | {f.get('tags')} | {f.get('remotes')} | {f.get('commits_not_ancestor_of_base')} | {f.get('unreachable')} | {f.get('python')} | {f.get('egress_pypi')} | {ctl} |")
        out.append("")
    # gates
    gates = [r for r in rows if r["gate"] != "facts"]
    by = defaultdict(list)
    for r in gates:
        by[(r["instance_id"], r["gate"], r["variant"])].append(r)
    out.append("### 门结果（每格：结果计数 / 官方判定 / 严格判定 / install rc / t_install / t_test）\n")
    out.append("| instance | gate | variant | n | results | official | strict | rc_install | t_install(s) | t_test(s) | parsed cases | ref missing(f2p/p2p) | skipped ref | patch apply |")
    out.append("|---|---|---|---:|---|---|---|---|---|---|---|---|---|---|")
    for (iid, gate, variant), rs in sorted(by.items()):
        res = Counter(r.get("result") for r in rs)
        off = Counter(r.get("official_verdict") for r in rs)
        st = Counter((r.get("strict") or {}).get("strict_full") for r in rs)
        rci = Counter(r.get("rc_install") for r in rs)
        ti = [r.get("t_install") for r in rs if isinstance(r.get("t_install"), (int, float))]
        tt = [r.get("t_test") for r in rs if isinstance(r.get("t_test"), (int, float))]
        pc = Counter(r.get("parsed_cases") for r in rs)
        miss = Counter(f"{(r.get('strict') or {}).get('f2p_missing')}/{(r.get('strict') or {}).get('p2p_missing')}" for r in rs)
        sk = Counter((r.get("strict") or {}).get("ref_skipped") for r in rs)
        pa = Counter(r.get("patch_apply") for r in rs)
        d = lambda c: ",".join(f"{k}×{v}" for k, v in c.items())  # noqa: E731
        out.append(f"| {iid} | {gate} | {variant} | {len(rs)} | {d(res)} | {d(off)} | {d(st)} | {d(rci)} | {fmt(statistics.mean(ti)) if ti else '-'} | {fmt(statistics.mean(tt)) if tt else '-'} | {d(pc)} | {d(miss)} | {d(sk)} | {d(pa)} |")
    out.append("")
    # summary counters
    out.append("### 汇总\n")
    tot = Counter((r["gate"], r["variant"], r.get("result")) for r in gates)
    out.append("| gate | variant | result | n |")
    out.append("|---|---|---|---:|")
    for (g, v, res), n in sorted(tot.items()):
        out.append(f"| {g} | {v} | {res} | {n} |")
    out.append("")
    # timing distribution per repo (default variant, gold)
    per_repo = defaultdict(list)
    for r in gates:
        if r["variant"] == "default" and isinstance(r.get("elapsed_s"), (int, float)):
            per_repo[r["repo"]].append((r.get("t_install") if isinstance(r.get("t_install"), (int, float)) else 0, r.get("t_test") if isinstance(r.get("t_test"), (int, float)) else 0, r["elapsed_s"]))
    out.append("### 每仓库耗时（default 变体，秒；均值/最大）\n")
    out.append("| repo | n | install 均值/最大 | test 均值/最大 | 单次总耗时 均值/最大 |")
    out.append("|---|---:|---|---|---|")
    for repo, xs in sorted(per_repo.items()):
        ins = [x[0] for x in xs]
        tst = [x[1] for x in xs]
        tot_ = [x[2] for x in xs]
        out.append(f"| {repo} | {len(xs)} | {statistics.mean(ins):.1f}/{max(ins):.1f} | {statistics.mean(tst):.1f}/{max(tst):.1f} | {statistics.mean(tot_):.1f}/{max(tot_):.1f} |")
    out.append("")
    # determinism: for (iid,gate,variant) with n>=2 compare official+strict+f2p_status
    out.append("### 重复一致性（同 instance/gate/variant 多次运行，比较官方判定 + 严格判定 + F2P 逐 case 状态）\n")
    incons = []
    for (iid, gate, variant), rs in sorted(by.items()):
        if len(rs) < 2:
            continue
        sig = {(r.get("official_verdict"), (r.get("strict") or {}).get("strict_full"), json.dumps((r.get("strict") or {}).get("f2p_status"), sort_keys=True)) for r in rs}
        if len(sig) > 1:
            incons.append((iid, gate, variant, len(rs), [r.get("result") for r in rs]))
    if incons:
        out.append("| instance | gate | variant | n | results |")
        out.append("|---|---|---|---:|---|")
        for x in incons:
            out.append(f"| {x[0]} | {x[1]} | {x[2]} | {x[3]} | {x[4]} |")
    else:
        out.append("所有重复运行的判定一致。")
    out.append("")


def r2e(rows, out):
    out.append("## R2E-Gym 探针（预期状态映射精确匹配）\n")
    facts = [r for r in rows if r["gate"] == "facts"]
    if facts:
        out.append("### 环境事实\n")
        out.append("| repo | commit | HEAD 是修复提交的父提交 | 修复提交在历史中 | remotes | tags | HEAD 之后仍可达提交 | 工作区脏文件行数 | venv python | /r2e_tests 文件 | /testbed/r2e_tests | pypi(默认网络) |")
        out.append("|---|---|---|---|---:|---:|---:|---:|---|---:|---:|---|")
        for r in sorted(facts, key=lambda x: (x["repo"], x["commit_hash"])):
            f = r.get("facts", {})
            out.append(f"| {r['repo']} | {r['commit_hash'][:12]} | {f.get('head_is_parent_of_fix')} | {f.get('fix_reachable')} | {f.get('remotes')} | {f.get('tags')} | {f.get('commits_after_head')} | {f.get('status_lines')} | {f.get('venv_python')} | {f.get('r2e_tests_root')} | {f.get('r2e_tests_in_testbed')} | {f.get('egress_pypi')} |")
        out.append("")
    gates = [r for r in rows if r["gate"] != "facts"]
    by = defaultdict(list)
    for r in gates:
        by[(r["repo"], r["commit_hash"], r["gate"])].append(r)
    out.append("### 门结果\n")
    out.append("| repo | commit | gate | n | results | reward | parsed/expected | mismatch | missing | extra | gold 与 git diff 一致 | t_test(s) |")
    out.append("|---|---|---|---:|---|---|---|---|---|---|---|---|")
    for (repo, cm, gate), rs in sorted(by.items()):
        res = Counter(r.get("result") for r in rs)
        rw = Counter(r.get("reward") for r in rs)
        d = lambda c: ",".join(f"{k}×{v}" for k, v in c.items())  # noqa: E731
        det = (rs[0].get("reward_details") or {})
        tt = [r.get("t_test") for r in rs if isinstance(r.get("t_test"), (int, float))]
        out.append(f"| {repo} | {cm[:12]} | {gate} | {len(rs)} | {d(res)} | {d(rw)} | {det.get('parsed_n')}/{det.get('expected_n')} | {det.get('n_mismatch')} | {det.get('n_missing')} | {det.get('n_extra')} | {rs[0].get('gold_matches_git_diff_changed_lines', '-')} | {fmt(statistics.mean(tt)) if tt else '-'} |")
    out.append("")


def cc(rows, out):
    out.append("## Claude Code 2.1.205 + DeepSeek 参考求解（api_reference_run，不进任何成功率）\n")
    out.append("| instance | result | grade | official | strict | turns | tool calls | patch files | touches tests | cost CNY | t_cc(s) | cc subtype |")
    out.append("|---|---|---|---|---|---:|---:|---:|---|---|---|---|")
    for r in sorted(rows, key=lambda x: x["instance_id"]):
        cr = r.get("cc_result") or {}
        turns = r.get("num_turns") or cr.get("num_turns") or r.get("assistant_turns")
        out.append(f"| {r['instance_id']} | {r.get('result')} | {r.get('grade_result')} | {r.get('official_verdict')} | {r.get('strict_full')} | {turns} | {r.get('tool_calls_total')} | {len(r.get('patch_files') or [])} | {bool(r.get('patch_touches_tests'))} | {r.get('cost_cny')} | {r.get('t_cc_s')} | {cr.get('subtype')} |")
    out.append("")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger-dir", default="/work/ledger")
    ap.add_argument("--out", default="/work/ledger/summary.md")
    args = ap.parse_args()
    d = Path(args.ledger_dir)
    out = ["# env probe 汇总（自动生成）\n"]
    sw = load(d / "swegym_ledger.jsonl")
    if sw:
        swegym(sw, out)
    # R2E：facts 来自 v1 账本（parser 无关）；门结果优先取最终版 v3（两侧对称去 ANSI），其次 v2/v1
    r2_facts = [r for r in load(d / "r2e_ledger.jsonl") if r.get("gate") == "facts"]
    r2_gates = []
    for name in ("r2e_ledger_v3.jsonl", "r2e_ledger_v2.jsonl", "r2e_ledger.jsonl"):
        r2_gates = [r for r in load(d / name) if r.get("gate") != "facts"]
        if r2_gates:
            out.append(f"（R2E 门结果账本：{name}）\n")
            break
    if r2_facts or r2_gates:
        r2e(r2_facts + r2_gates, out)
    ccr = load(d / "cc_reference_ledger.jsonl")
    if ccr:
        cc(ccr, out)
    Path(args.out).write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
