"""Verify reserve20 outputs only; preserves first12 verifier and submission snapshots."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path

B = Path(__file__).resolve().parent
ROOT = next(p for p in B.parents if (p / "rh2/src/repoharness2").is_dir())
FILES = (
    "public_read.md", "analysis_before_history.md", "old_findings_delta.md",
    "card.md", "screening_record.json", "reviewer_initial.md", "review.md",
)
FIELDS = {
    "task_id", "task_revision", "source_adapter_ref", "recipe_ref", "code_snapshot_ref",
    "facts_ref", "checks", "issues", "file_rules", "revision_refs", "disposition",
    "usage", "costs",
}
STATES = {"not_checked", "pass", "issue", "unknown", "not_applicable"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(package=None):
    manifest = json.loads((B / "manifest.json").read_text())
    assignments = json.loads((B / "assignments.json").read_text())
    plan = json.loads((B / "reserve20_packages.json").read_text())
    package_tasks = {p["package_id"]: p["instance_ids"] for p in plan["packages"]}
    selected_ids = set(manifest["reserve20_task_ids"] if package is None else package_tasks[package])
    selected = [t for t in manifest["tasks"] if t["instance_id"] in selected_ids]
    assert len(selected) == len(selected_ids), "Reserve selection mismatch"
    assert selected, "No selected tasks"
    errors, tasks = [], []
    assert sha(B / "manifest.json") == assignments["manifest_sha256"]
    for task in selected:
        tid = task["instance_id"]
        output = ROOT / task["output_dir"]
        hashes = {}
        for filename in FILES:
            path = output / filename
            if not path.is_file() or not path.stat().st_size:
                errors.append(f"{tid}: missing or empty {filename}")
            else:
                hashes[filename] = sha(path)
        path = output / "screening_record.json"
        if path.is_file():
            try:
                record = json.loads(path.read_text())
                assert FIELDS <= record.keys(), "required fields missing"
                assert record["task_id"] in (tid, "swe_gym_lite::" + tid), "task ID mismatch"
                for number, check in record["checks"].items():
                    assert str(number).isdigit() and 1 <= int(number) <= 40, "check number"
                    assert check["status"] in STATES, "check status"
                    assert {"status", "evidence_refs", "by"} <= check.keys(), "check fields"
                    assert check["by"], "empty check attribution"
                for issue in record["issues"]:
                    assert {"category", "scope", "evidence_refs", "proposed_action", "status"} <= issue.keys(), "issue fields"
                assert record["file_rules"]["additional_exclusions"] == [], "unapproved exclusions"
                assert record["revision_refs"] == [], "unexpected task revision"
                assert record["disposition"]["scope"] == "static_review", "disposition scope"
                assert record["disposition"]["state"] == "needs_review", "unapproved readiness"
                assert record["usage"]["intended_use"] == "development_diagnostic", "usage scope"
            except (AssertionError, KeyError, TypeError, ValueError) as exc:
                errors.append(f"{tid}: record shape: {exc}")
        roles = []
        for role in ("public_reader", "investigator", "reviewer"):
            matches = [a for a in assignments["assignments"]
                       if a["role"] == role and tid in a["instance_ids"]]
            if len(matches) != 1:
                errors.append(f"{tid}: {len(matches)} {role} assignments")
                continue
            agent = matches[0]
            roles.append({"role": role, "agent_id": agent["agent_id"], "status": agent["status"]})
            if agent["status"] != "completed":
                errors.append(f"{tid}: {role} not completed")
            if (agent["model"], agent["reasoning_effort"], agent["fork_turns"]) != ("gpt-6-astra", "high", "none"):
                errors.append(f"{tid}: requested role configuration differs")
            if len(agent.get("sealed_outputs", [])) != len(agent["instance_ids"]):
                errors.append(f"{tid}: package initial seals incomplete")
            for sealed in agent.get("sealed_outputs", []):
                if sha(ROOT / sealed["file"]) != sealed["sha256"]:
                    errors.append(f"{tid}: immutable seal changed: {sealed['file']}")
            if role != "public_reader":
                key = "history_release_at" if role == "investigator" else "cross_review_release_at"
                if not agent.get(key):
                    errors.append(f"{tid}: {role} release record missing")
                elif any(s["verified_at"] > agent[key] for s in agent.get("sealed_outputs", [])):
                    errors.append(f"{tid}: release preceded all initial seals")
        tasks.append({"instance_id": tid, "artifact_sha256": hashes, "roles": roles})
    return {
        "schema": "quality_expansion.output_verification.v1",
        "checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scope": package or "reserve20", "task_count": len(selected),
        "passed": not errors, "errors": errors, "tasks": tasks,
        "limits": "Shape, requested configuration, timing and hash checks only; no semantic acceptance, actual actor verification or backend model attestation.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--package")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    target = (B / args.output).resolve()
    assert target.parent == B, "Write this batch directory only"
    result = verify(args.package)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("scope", "task_count", "passed", "errors")}, ensure_ascii=False))
    raise SystemExit(0 if result["passed"] else 1)
