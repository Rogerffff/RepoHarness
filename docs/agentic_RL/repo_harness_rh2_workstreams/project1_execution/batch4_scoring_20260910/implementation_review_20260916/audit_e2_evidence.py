"""独立复核 e2/回归账本数量、日志摘要和 B 组来源 oracle；只读既有 evidence。"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "rh2/pyproject.toml").is_file())
E2 = ROOT / "runs/swe_grading_wiring_20260915/e2"


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def category(row):
    report = row.get("report") or {}
    if report:
        return report.get("failure_category") or report["outcome"]
    return (row.get("candidate") or {}).get("apply_method") or row.get("stage_error") or "no_report"


def main():
    files = {}
    mismatch, missing, checked = [], [], 0
    all_rows = []
    for path in sorted(E2.glob("**/ledger*.jsonl")):
        data = rows(path)
        all_rows.extend(data)
        files[str(path.relative_to(E2))] = {
            "rows": len(data),
            "categories": dict(Counter(map(category, data))),
            "ledger_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for row in data:
            for key in ("log", "diagnostics_ref"):
                ref = row.get(key)
                remote = ref.get("path") if isinstance(ref, dict) else ref
                if not remote:
                    continue
                local = path.parent / "eval_logs" / Path(remote).name
                if not local.is_file():
                    missing.append(str(local.relative_to(ROOT)))
                    continue
                if key == "log":
                    checked += 1
                    digest = "sha256:" + hashlib.sha256(local.read_bytes()).hexdigest()
                    if digest != ref.get("sha256"):
                        mismatch.append({"file": str(local.relative_to(ROOT)), "actual": digest, "expected": ref.get("sha256")})

    oracle_path = ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_probe_20260909/ledger/cc_candidate_grading.jsonl"
    oracle = {(r["instance_id"], r["gate"]): r for r in rows(oracle_path)}
    b_result = []
    for row in rows(E2 / "ledger_e2_B.jsonl"):
        report = row.get("report") or {}
        source = oracle.get((row["instance_id"], "candidate_projected"), {})
        comparable = report.get("outcome") in ("resolved", "unresolved")
        b_result.append({
            "instance_id": row["instance_id"],
            "category": category(row),
            "comparable": comparable,
            "agreement": report.get("outcome") == source.get("result") if comparable else None,
        })

    old = {}
    for row in rows(E2 / "ledger_e2_A.jsonl") + rows(E2 / "ledger_e2_B.jsonl"):
        old[(row["task_id"], row["candidate"]["kind"])] = row
    regression = []
    for name in ("gold", "noop", "cc"):
        for row in rows(E2 / "reg" / f"ledger_reg_{name}.jsonl"):
            before = old.get((row["task_id"], row["candidate"]["kind"]))
            if before is None:
                regression.append({"task_id": row["task_id"], "kind": name, "before": "not_found"})
                continue
            keys = ("outcome", "reward", "f2p_pass", "f2p_total", "p2p_fail", "p2p_total", "failure_category")
            a, b = before.get("report") or {}, row.get("report") or {}
            changed = {k: [a.get(k), b.get(k)] for k in keys if a.get(k) != b.get(k)}
            regression.append({"task_id": row["task_id"], "kind": name, "changed": changed,
                               "before_category": category(before), "after_category": category(row)})

    result = {
        "files": files,
        "e2_rows": sum(v["rows"] for k, v in files.items() if not k.startswith("reg/")),
        "regression_rows": sum(v["rows"] for k, v in files.items() if k.startswith("reg/")),
        "reports": sum(bool(r.get("report")) for r in all_rows),
        "log_sha256_checked": checked,
        "log_digest_mismatches": mismatch,
        "missing_log_refs": missing,
        "B_unique_rows": b_result,
        "B_comparable": sum(r["comparable"] for r in b_result),
        "B_agree": sum(r["agreement"] is True for r in b_result),
        "regression_comparison": regression,
    }
    (HERE / "ledger_verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in ("files", "B_unique_rows", "regression_comparison")}, ensure_ascii=False, indent=2))
    print("regression_changes:", json.dumps([r for r in regression if r.get("changed") or r.get("before")], ensure_ascii=False))


if __name__ == "__main__":
    main()
