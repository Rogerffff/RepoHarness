"""只核本批已回传证据；不启动容器、不改运行产物。"""

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "rh2/src/repoharness2").is_dir())
sys.path.insert(0, str(ROOT / "rh2/src"))
from repoharness2.envpack.ingest_r2e_subset import load_trusted_r2e_ingest_outputs
from repoharness2.envpack.scoring import parse_eval_log_r2e

BATCH = HERE.parent.parent / "r2e_static_review_batch2_20260925"
BASE = ROOT / "runs/r2e_actor_20260925"
assignments = json.loads((BATCH / "assignments.json").read_text())
tasks = set(assignments["tasks"])
trusted = load_trusted_r2e_ingest_outputs(ROOT)
grading = {g.instance_id: g for g in trusted.result.grading_bundles}
validation = {g.instance_id: g for g in trusted.result.validation_bundles}


def sha(data):
    return "sha256:" + hashlib.sha256(data).hexdigest()


rows = []
for ledger in sorted((BASE / "grader").glob("ledger*.jsonl")):
    for raw in ledger.read_text().splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw)
        iid = row["instance_id"]
        if iid not in tasks:
            continue
        log = BASE / "grader/eval_logs" / Path(row["log"]["path"]).name
        data = log.read_bytes()
        assert sha(data) == row["log"]["sha256"], ledger
        assert not row["log"]["partial"] and not row["stage_error"], ledger
        verdict = parse_eval_log_r2e(grading[iid], data.decode("utf-8", "replace"))
        report = row["report"]
        assert verdict.reward == report["reward"], ledger
        assert verdict.expected_match.match_count == report["expected_match"], ledger
        assert verdict.expected_match.total_count == report["expected_total"], ledger
        saved_match = row["verdict_diagnostics"]["expected_match"]
        for key in ("missing", "unexpected", "mismatched"):
            assert sorted(getattr(verdict.expected_match, key)) == sorted(saved_match[key]), (ledger, key)
        assert row["runner_integrity_changed"] is False, ledger
        assert row["image_id_actual"] == row["overlay"]["derived_image_id"], ledger
        assert row["cleanup"]["removed"], ledger
        candidate = row["candidate"]
        patch_source = None
        if candidate["kind"] == "gold":
            patch = validation[iid].golden_patch.encode()
            patch_source = "trusted_validation_bundle"
        elif candidate["kind"] == "noop":
            assert candidate["patch_sha256"] is None
            patch = None
        else:
            patch_file = BASE / "grader_cands" / Path(candidate["origin"]).name
            if not patch_file.exists():
                patch_file = BASE / "grader/cands" / Path(candidate["origin"]).name
            patch = patch_file.read_bytes()
            patch_source = str(patch_file.relative_to(ROOT))
        if patch is not None:
            assert sha(patch) == candidate["patch_sha256"], ledger
        rows.append({
            "ledger": str(ledger.relative_to(ROOT)), "instance_id": iid,
            "kind": candidate["kind"], "reward": verdict.reward,
            "match": verdict.expected_match.match_count,
            "total": verdict.expected_match.total_count,
            "mismatched": verdict.expected_match.mismatched,
            "missing": verdict.expected_match.missing,
            "unexpected": verdict.expected_match.unexpected,
            "log_sha256": sha(data), "patch_sha256": candidate["patch_sha256"],
            "patch_source": patch_source, "recipe_id": row["overlay"]["recipe_id"],
        })
assert len(rows) == 81, len(rows)

actors = []
for iid in sorted(tasks):
    path = BASE / "devcheck" / iid[:40] / "orig/attempt.json"
    row = json.loads(path.read_text())
    prelaunch = json.loads((path.parent / "prelaunch.json").read_text())
    facts = prelaunch["probe_facts"]
    assert facts["ACTIVATION_WRITE"] == "DENIED" and facts["UID"] == "54321", path
    assert row["harness_exit_code"] == 0 and row["result"] == "ran", path
    assert row["checks"]["image_is_overlay_derived_id"], path
    assert row["checks"]["r2e_preflight_ok"] and row["checks"]["all_commands_ran"], path
    assert not row["r2e_preflight"]["failures"], path
    assert all((path.parent / "captures" / (c["id"] + ".out")).is_file()
               for c in row["commands_result"]), path
    actors.append({
        "instance_id": iid, "attempt": str(path.relative_to(ROOT)),
        "checks": row["checks"], "commands_count": len(row["commands_result"]),
        "cleanup_residual": (row.get("cleanup") or {}).get("residual_after_force"),
    })

required = ["public_read.md", "analysis_before_history.md", "card.md",
            "old_findings_delta.md", "screening_record.json", "reviewer_initial.md", "review.md"]
roles = []
for iid in sorted(tasks):
    paths = [BATCH / "results" / iid / n for n in required]
    assert all(p.is_file() and p.stat().st_size for p in paths), iid
    record = json.loads(paths[4].read_text())
    assigned = [a for a in assignments["agents"] if iid in a["tasks"]]
    assert Counter(a["role"] for a in assigned) == Counter(
        {"public_reader": 1, "investigator": 1, "reviewer": 1}), iid
    assert all(a["status"] == "done" for a in assigned), iid
    roles.append({"instance_id": iid, "artifacts": len(paths), "sessions": len(assigned)})

summary = {
    "grading_rows": len(rows), "grading_tasks": len({r["instance_id"] for r in rows}),
    "kinds": dict(Counter(r["kind"] for r in rows)),
    "rewards": dict(Counter(r["reward"] for r in rows)),
    "unique_task_patch_pairs": len({(r["instance_id"], r["kind"], r["patch_sha256"]) for r in rows}),
    "actor_tasks": len(actors), "actor_commands": sum(r["commands_count"] for r in actors),
    "role_sessions": len(assignments["agents"]), "role_artifacts": sum(r["artifacts"] for r in roles),
    "per_task": {t: {"rows": sum(r["instance_id"] == t for r in rows),
                      "rewards": dict(Counter(r["reward"] for r in rows if r["instance_id"] == t))}
                 for t in sorted(tasks)},
}
(HERE / "evidence_audit.json").write_text(json.dumps({
    "scope": "现成证据离线重算。开发核对为真实 CC + 桩端点，不是 Qwen 自主解题；role 文件存在不等于可证明会话从未接触私有上下文。",
    "summary": summary, "rows": rows, "actors": actors, "roles": roles,
}, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(summary, ensure_ascii=False, indent=2))
