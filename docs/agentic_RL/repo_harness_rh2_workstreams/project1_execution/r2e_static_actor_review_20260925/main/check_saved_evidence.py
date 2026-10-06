"""Recompute saved candidate rewards and actor facts; read-only outside review output."""

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

BASE = ROOT / "runs/r2e_actor_20260925"
trusted = load_trusted_r2e_ingest_outputs(ROOT)
gradings = {g.instance_id: g for g in trusted.result.grading_bundles}
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
        log = BASE / "grader/eval_logs" / Path(row["log"]["path"]).name
        data = log.read_bytes()
        assert sha(data) == row["log"]["sha256"], log
        assert not row["log"]["partial"] and not row["stage_error"], ledger
        verdict = parse_eval_log_r2e(gradings[iid], data.decode("utf-8", "replace"))
        report = row["report"]
        assert verdict.reward == report["reward"], ledger
        assert verdict.expected_match.match_count == report["expected_match"], ledger
        assert verdict.expected_match.total_count == report["expected_total"], ledger
        assert row["image_id_actual"] == row["overlay"]["derived_image_id"], ledger
        assert row["cleanup"]["removed"], ledger
        candidate = row["candidate"]
        if candidate["kind"] == "gold":
            patch = validation[iid].golden_patch.encode()
        else:
            patch_file = BASE / "grader/cands" / Path(candidate["origin"]).name
            patch = patch_file.read_bytes()
        assert sha(patch) == candidate["patch_sha256"], ledger
        rows.append({
            "ledger": str(ledger.relative_to(ROOT)), "instance_id": iid,
            "kind": candidate["kind"], "reward": verdict.reward,
            "match": verdict.expected_match.match_count, "total": verdict.expected_match.total_count,
            "mismatched": verdict.expected_match.mismatched,
            "log_sha256": sha(data), "patch_sha256": sha(patch),
            "recipe_id": row["overlay"]["recipe_id"],
        })
assert len(rows) == 26

actors = []
for path in sorted((BASE / "devcheck").glob("*/orig/attempt.json")):
    row = json.loads(path.read_text())
    prelaunch = json.loads((path.parent / "prelaunch.json").read_text())
    probe_facts = prelaunch["probe_facts"]
    assert probe_facts["ACTIVATION_WRITE"] == "DENIED", path
    assert probe_facts["UID"] == "54321", path
    assert row["harness_exit_code"] == 0 and row["result"] == "ran", path
    assert row["checks"]["image_is_overlay_derived_id"], path
    assert row["checks"]["r2e_preflight_ok"] and row["checks"]["all_commands_ran"], path
    assert not row["r2e_preflight"]["failures"], path
    assert all((path.parent / "captures" / (c["id"] + ".out")).is_file()
               for c in row["commands_result"]), path
    actors.append({
        "attempt": str(path.relative_to(ROOT)), "task_id": row["task_id"],
        "harness_exit_code": row["harness_exit_code"], "checks": row["checks"],
        "commands_count": len(row["commands_result"]),
        "prelaunch_agent_activation_write_denied": probe_facts["ACTIVATION_WRITE"] == "DENIED",
        "cleanup_residual": (row.get("cleanup") or {}).get("residual_after_force"),
    })
assert len(actors) == 8

doc = {
    "scope": "Existing local logs, patches and actor records only; no new container or inference.",
    "candidate_rows": rows, "actor_rows": actors,
    "summary": {
        "grading_rows": len(rows), "task_count_with_new_grading": len({r["instance_id"] for r in rows}),
        "candidate_kinds": dict(Counter(r["kind"] for r in rows)),
        "rewards": dict(Counter(r["reward"] for r in rows)),
        "actor_attempts": len(actors),
        "bashenv_denied_observed_in_CC_tool_capture": sum(r["checks"]["bashenv_denied_for_agent"] for r in actors),
        "activation_write_denied_in_prelaunch_agent_probe": sum(r["prelaunch_agent_activation_write_denied"] for r in actors),
    },
}
(HERE / "saved_evidence.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(doc["summary"], ensure_ascii=False))
