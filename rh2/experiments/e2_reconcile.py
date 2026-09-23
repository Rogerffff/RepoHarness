"""e2 对账：rh2 真实链账本 vs 两组 oracle（原组 gate=candidate、投影组 gate=candidate_projected），并汇总 A/C 组。

用法：python experiments/e2_reconcile.py --e2-dir <runs/.../e2> --oracle <cc_candidate_grading.jsonl> [--out reconcile.md]
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def _rows(path: Path):
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def _short(task_id: str) -> str:
    return task_id.split("::")[-1]


def _rh2_verdict(row: dict) -> str:
    rep = row.get("report") or {}
    if row.get("stage_error"):
        return f"stage_error:{row['stage_error']}"
    if (row.get("candidate") or {}).get("apply_method") == "apply_failed":
        return "apply_failed"
    if row.get("classification") and row["classification"].get("verdict") != "projectable":
        return f"unsafe:{','.join(row['classification'].get('reason_codes') or [])}"
    if not rep:
        return "no_report"
    if rep.get("outcome") == "resolved":
        return "resolved"
    if rep.get("outcome") == "unresolved":
        return f"unresolved:{rep.get('failure_category')}"
    return f"failed_to_grade:{rep.get('failure_category')}:{(rep.get('infra_failure_detail') or '')[:80]}"


def _oracle_verdict(o: dict | None) -> str:
    if o is None:
        return "-"
    return f"{o['result']}:{o['verdict']}"


def _agree(rh2: str, oracle: str) -> str:
    if oracle == "-":
        return "?"
    o_res = oracle.split(":")[0]
    if rh2 == "resolved":
        return "同" if o_res == "resolved" else "异"
    if rh2.startswith("unresolved"):
        return "同" if o_res == "unresolved" else "异"
    return "不可比"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--e2-dir", required=True)
    ap.add_argument("--oracle", required=True)
    ap.add_argument("--out", default=None)
    ns = ap.parse_args()
    e2 = Path(ns.e2_dir)
    oracle: dict[str, dict[str, dict]] = defaultdict(dict)
    for r in _rows(Path(ns.oracle)):
        oracle[r["instance_id"]][r["gate"]] = {"result": r.get("result"), "verdict": r.get("official_verdict"),
                                              "f2p_missing": (r.get("strict") or {}).get("f2p_missing"), "p2p_missing": (r.get("strict") or {}).get("p2p_missing"),
                                              "dropped": (r.get("fixture_note") or "").split("projected_dropped=")[-1] if "projected_dropped=" in (r.get("fixture_note") or "") else None}
    out: list[str] = []
    P = out.append

    # ---- B 组：真实候选 ----
    P("## B 组：24 条 DeepSeek 候选 — rh2 vs oracle\n")
    P("| 题 | 尝试 | rh2 判定 | reward | 原组 oracle | 投影组 oracle | 同/异（原） | 同/异（投影） | apply | 投影忽略 | F2P | P2P | 参考缺席 | install rc / s | test rc / s | 备注 |")
    P("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    counts = Counter()
    brows = _rows(e2 / "ledger_e2_B.jsonl") + _rows(e2 / "ledger_e2_B_repeat.jsonl")
    for row in sorted(brows, key=lambda r: (_short(r["task_id"]), r.get("run_id", ""), r.get("attempt", 0))):
        iid = _short(row["task_id"])
        rep = row.get("report") or {}
        v = _rh2_verdict(row)
        o1, o2 = oracle.get(iid, {}).get("candidate"), oracle.get(iid, {}).get("candidate_projected")
        a1, a2 = _agree(v, _oracle_verdict(o1)), _agree(v, _oracle_verdict(o2))
        counts[(v.split(":")[0], a2)] += 1
        inst = row.get("install") or {}
        tst = row.get("test") or {}
        proj = row.get("projection") or {}
        ignored = ",".join(e.get("path", "?") if isinstance(e, dict) else str(e) for e in (proj.get("ignored_paths") or []))
        notes = "; ".join(row.get("notes") or [])
        if row.get("candidate_touched_conftest_or_fixture"):
            notes += " conftest/fixture 触碰"
        P(f"| {iid} | {row.get('run_id','')}/{row.get('attempt')} | {v} | {rep.get('reward')} | {_oracle_verdict(o1)} | {_oracle_verdict(o2)} | {a1} | {a2} | "
          f"{(row.get('candidate') or {}).get('apply_method')} | {ignored or '-'} | {rep.get('f2p_pass')}/{rep.get('f2p_total')} | {rep.get('p2p_fail')}/{rep.get('p2p_total')} | "
          f"{row.get('reference_missing_count') if row.get('reference_missing_count') is not None else len((row.get('verdict_diagnostics') or {}).get('reference_missing') or [])} | "
          f"{inst.get('install_rc_last_command')} / {inst.get('install_seconds')} | {tst.get('rc')} / {tst.get('seconds')} | {notes} |")
    P("")
    P("汇总（rh2 判定 × 与投影组 oracle 同/异）：" + ", ".join(f"{k[0]}·{k[1]}={n}" for k, n in sorted(counts.items())))
    P("")

    # ---- A 组：gold / noop ×2 ----
    P("## A 组：9 题 gold / noop ×2\n")
    P("| 题 | 候选 | 尝试 | 判定 | reward | 参考缺席 | 导入路径 | 运行器变化 | install rc / s | test rc / s | 阶段秒（setup/test/cleanup） | 峰值 MB |")
    P("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for row in sorted(_rows(e2 / "ledger_e2_A.jsonl"), key=lambda r: (_short(r["task_id"]), (r.get("candidate") or {}).get("kind", ""), r.get("attempt", 0))):
        rep = row.get("report") or {}
        inst, tst, ph = row.get("install") or {}, row.get("test") or {}, row.get("phases") or {}
        obs = row.get("observations") or {}
        P(f"| {_short(row['task_id'])} | {(row.get('candidate') or {}).get('kind')} | {row.get('attempt')} | {_rh2_verdict(row)} | {rep.get('reward')} | "
          f"{len((row.get('verdict_diagnostics') or {}).get('reference_missing') or [])} | {obs.get('RH2_OBS_IMPORT_PATH','-')} | {row.get('runner_integrity_changed')} | "
          f"{inst.get('install_rc_last_command')} / {inst.get('install_seconds')} | {tst.get('rc')} / {tst.get('seconds')} | "
          f"{ph.get('grader_trusted_setup')}/{ph.get('test')}/{ph.get('grader_cleanup')} | {(row.get('resource') or {}).get('mem_peak_mb')} |")
    P("")

    # ---- C 组 + 派生 ----
    P("## C 组反例与派生镜像\n")
    P("| 账本 | 题 | 候选 | 镜像 | 判定 | reward | infra detail / stage_error | 参考缺席 | test rc / s | 峰值 MB | shm |")
    P("|---|---|---|---|---|---|---|---|---|---|---|")
    for name in ("ledger_e2_C.jsonl", "ledger_e2_C_shm1g.jsonl", "ledger_e2_derived.jsonl"):
        for row in _rows(e2 / name):
            rep = row.get("report") or {}
            tst = row.get("test") or {}
            P(f"| {name} | {_short(row['task_id'])} | {(row.get('candidate') or {}).get('kind')} | {row.get('image_ref')} | {_rh2_verdict(row)} | {rep.get('reward')} | "
              f"{(rep.get('infra_failure_detail') or row.get('stage_error') or '-')[:100]} | {len((row.get('verdict_diagnostics') or {}).get('reference_missing') or [])} | "
              f"{tst.get('rc')} / {tst.get('seconds')} | {(row.get('resource') or {}).get('mem_peak_mb')} | {(row.get("policy") or {}).get("shm_bytes", "-")} |")
    text = "\n".join(out) + "\n"
    if ns.out:
        Path(ns.out).write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
