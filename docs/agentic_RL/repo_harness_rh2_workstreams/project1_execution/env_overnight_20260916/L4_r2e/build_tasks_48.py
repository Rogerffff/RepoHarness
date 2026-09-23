#!/usr/bin/env python3
"""L4：合并 R2E 48 题清单（旧 24 主批 + 新 24 扩展），只读本地证据，不联网不起容器。"""
import json, hashlib
from pathlib import Path

ROOT = Path("${REPO_ROOT}")
DOCS = ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams"
OUT = DOCS / "project1_execution/env_overnight_20260916/L4_r2e"

V3 = DOCS / "project1_execution/env_probe_20260909/ledger/r2e_ledger_v3.jsonl"
OLD_MANIFEST = DOCS / "project1_execution/b_probe_preparation_20260909/candidate_manifest.jsonl"
NEW_MANIFEST = ROOT / "runs/env_probe_stage1_20260910/r2e_expansion_preparation/candidate_manifest.jsonl"
NEW_FULL = ROOT / "runs/env_probe_stage1_20260910/r2e_expansion_preparation/r2e_candidates_full.jsonl"
SUBSET_META = DOCS / "data_freeze/meta/r2e_subset.jsonl"
IMG48 = DOCS / "project1_execution/env_overnight_20260916/r2e_images_48.txt"


def jl(p):
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def main():
    v3 = jl(V3)
    old_manifest = {r["candidate_key"].split("::", 1)[1]: r for r in jl(OLD_MANIFEST) if "R2E" in r["source"]}
    new_manifest = {r["source_commit_hash"]: r for r in jl(NEW_MANIFEST)}
    subset = {r["commit_hash"]: r for r in jl(SUBSET_META)}

    # 新 24 的完整源行（含 expected_output_json / modified_files / parsed_commit_content）
    new_full = {}
    with NEW_FULL.open() as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                new_full[r["commit_hash"]] = r

    old_rows = {}
    for r in v3:
        old_rows.setdefault(r["commit_hash"], []).append(r)

    tasks = []
    for commit, rows in old_rows.items():
        r0 = rows[0]
        m = old_manifest.get(commit, {})
        exp_statuses = {}
        for r in rows:
            d = r.get("reward_details") or {}
            if d.get("expected_statuses"):
                exp_statuses = d["expected_statuses"]
                break
        tasks.append({
            "task_id": f"r2e::{commit}",
            "group": "core24",
            "source": "R2E-Gym/R2E-Gym-Subset",
            "source_revision": r0["source_revision"],
            "task_revision": "upstream",
            "repo": r0["repo"],
            "commit_hash": commit,
            "image_ref": r0["image_ref"],
            "image_digest_observed": r0.get("image_digest_actual"),
            "workdir": "/testbed",
            "expected_n": r0.get("expected_n"),
            "expected_status_counts": exp_statuses,
            "run_tests_sh": r0.get("run_tests_sh"),
            "problem_statement_chars": len(subset.get(commit, {}).get("problem_statement") or "") or None,
            "coverage_reason": m.get("coverage_reason"),
            "selection_status": m.get("selection_status"),
            "materials_refs": {
                "ledger": "docs/.../env_probe_20260909/ledger/r2e_ledger_v3.jsonl",
                "logs_root": "runs/env_probe_20260909_final_sync/ledger/logs_r2e/<repo>/<commit12>/<gate>/a<n>/",
                "candidate_manifest": "docs/.../b_probe_preparation_20260909/candidate_manifest.jsonl",
                "problem_statement": "docs/.../data_freeze/meta/r2e_subset.jsonl",
                "source_row_full": "absent_locally",
            },
        })

    for commit, m in new_manifest.items():
        full = new_full.get(commit, {})
        tasks.append({
            "task_id": f"r2e::{commit}",
            "group": "night_expansion24",
            "source": m["source"],
            "source_revision": m["source_revision"],
            "task_revision": "upstream",
            "repo": m["repo"],
            "commit_hash": commit,
            "image_ref": m["image_ref"],
            "image_digest_observed": None,
            "workdir": "/testbed",
            "expected_n": m.get("expected_count"),
            "expected_status_counts": m.get("expected_status_counts") or {},
            "run_tests_sh": None,
            "problem_statement_chars": len(full.get("problem_statement") or subset.get(commit, {}).get("problem_statement") or "") or None,
            "coverage_reason": m.get("coverage_reason"),
            "selection_status": m.get("selection_status"),
            "selection_quantile": m.get("selection_quantile"),
            "materials_refs": {
                "ledger": "runs/env_probe_stage1_20260910/ledger/{r2e_preflight_20260911,r2e_remainder_20260911,r2e_failure_repeats_20260911}/results.jsonl",
                "logs_root": "runs/env_probe_stage1_20260910/ledger/<batch>/logs_r2e/<repo>/<commit12>/<gate>/a<n>/",
                "candidate_manifest": "runs/env_probe_stage1_20260910/r2e_expansion_preparation/candidate_manifest.jsonl",
                "source_row_full": "runs/env_probe_stage1_20260910/r2e_expansion_preparation/r2e_candidates_full.jsonl",
                "fixture_snapshot": f"runs/env_probe_stage1_20260910/ledger/r2e_fixture_snapshots_20260911/{commit}/",
            },
        })

    # 补：新 24 的 run_tests.sh 来自本地 fixture 快照
    snap_root = ROOT / "runs/env_probe_stage1_20260910/ledger/r2e_fixture_snapshots_20260911"
    for t in tasks:
        if t["group"] == "night_expansion24":
            f = snap_root / t["commit_hash"] / "testbed/run_tests.sh"
            if f.exists():
                t["run_tests_sh"] = f.read_text().strip()

    tasks.sort(key=lambda t: (t["repo"], t["commit_hash"]))

    imgs = [l.strip() for l in IMG48.read_text().splitlines() if l.strip()]
    got = sorted(t["image_ref"] for t in tasks)
    doc = {
        "schema": "rh2.env_overnight.l4.r2e_tasks.v1",
        "generated_by": "docs/.../env_overnight_20260916/L4_r2e/build_tasks_48.py",
        "source": "R2E-Gym/R2E-Gym-Subset",
        "source_revision": "e8b9fcbce43eaca0dc2c0d4798ee6f3e965f590a",
        "task_revision": "upstream",
        "reconciliation": {
            "core24_commits": sum(1 for t in tasks if t["group"] == "core24"),
            "night_expansion24_commits": sum(1 for t in tasks if t["group"] == "night_expansion24"),
            "total": len(tasks),
            "duplicate_commits": len(tasks) - len({t["commit_hash"] for t in tasks}),
            "all_same_source": len({t["source"] for t in tasks}) == 1,
            "all_same_source_revision": len({t["source_revision"] for t in tasks}) == 1,
            "matches_coordinator_r2e_images_48": got == sorted(imgs),
            "image_ref_equals_repo_final_colon_commit": all(
                t["image_ref"].endswith(":" + t["commit_hash"]) for t in tasks),
            "per_repo": {r: sum(1 for t in tasks if t["repo"] == r) for r in sorted({t["repo"] for t in tasks})},
            "note": "两批均来自 R2E-Gym/R2E-Gym-Subset 同一冻结 revision；不是跨来源候选表（SWE-Gym 的 24 题在 b_probe_preparation 的同一 manifest 里，已按 source 过滤剔除）",
        },
        "tasks": tasks,
    }
    p = OUT / "r2e_tasks_48.json"
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    print("wrote", p)
    print(json.dumps(doc["reconciliation"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
