"""Verify coordinator final edits against archived investigator outputs; stdlib only."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path

B = Path(__file__).resolve().parent
ROOT = next(p for p in B.parents if (p / "rh2/src/repoharness2").is_dir())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    assignments = json.loads((B / "assignments.json").read_text())
    rows, errors = [], []
    for path in sorted((B / "coordinator_revisions").glob("*/revision_log.json")):
        log = json.loads(path.read_text())
        for task in log["tasks"]:
            tid = task["instance_id"]
            main = next(a for a in assignments["assignments"]
                        if a["role"] == "investigator" and tid in a["instance_ids"])
            original_hashes = {s["file"]: s["sha256"] for s in main["output_completion_snapshots"]}
            for name, before in task["before"].items():
                after = task["after"][name]
                try:
                    assert sha(ROOT / before["file"]) == before["sha256"], "archive bytes changed"
                    assert original_hashes[after["file"]] == before["sha256"], "archive differs from main delivery"
                    assert sha(ROOT / after["file"]) == after["sha256"], "current final differs from adjudication"
                    rows.append({"instance_id": tid, "artifact": name, "archive": before, "final": after})
                except (AssertionError, KeyError, OSError) as exc:
                    errors.append(f"{tid}/{name}: {exc}")
    expected = {(t["instance_id"], name) for t in assignments["tasks"]
                if t["stage"] == "first12" for name in ("card.md", "screening_record.json")}
    observed = {(row["instance_id"], row["artifact"]) for row in rows}
    if len(observed) != len(rows):
        errors.append("duplicate task/artifact provenance entries")
    if observed != expected:
        errors.append(f"provenance coverage mismatch: missing={sorted(expected-observed)}, extra={sorted(observed-expected)}")
    return {"schema": "quality_expansion.revision_provenance.v1",
            "checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "passed": not errors, "errors": errors, "artifact_count": len(rows), "artifacts": rows,
            "limits": "Byte identity and recorded authorship chain only; does not certify semantic correctness or actual actor qualification."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    target = (B / args.output).resolve()
    assert target.parent == B, "Write this batch directory only"
    result = verify()
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("passed", "errors", "artifact_count")}, ensure_ascii=False))
    raise SystemExit(0 if result["passed"] else 1)
