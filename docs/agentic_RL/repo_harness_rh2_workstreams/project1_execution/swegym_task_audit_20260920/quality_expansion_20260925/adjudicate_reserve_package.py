"""Apply explicit coordinator adjudication data to a completed reserve package; stdlib only."""
import argparse
import hashlib
import json
import runpy
from pathlib import Path

B = Path(__file__).resolve().parent
H = runpy.run_path(str(B / "coordination_metadata.py"))
ROOT = H["ROOT"]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def adjudicate(package):
    a = H["load"]()
    plan = json.loads((B / "reserve20_packages.json").read_text())
    group = next(p for p in plan["packages"] if p["package_id"] == package)
    config = json.loads((B / "coordinator_adjudications" / (package + ".json")).read_text())
    assert set(config["tasks"]) == set(group["instance_ids"])
    revision_dir = B / "coordinator_revisions" / package
    assert not revision_dir.exists(), "Coordinator archive already exists; do not overwrite provenance"
    at = H["now"]()
    revision_log = {"package": package, "by": "/root", "at": at,
        "scope": "mutable final card/record only", "sealed_initials_changed": False, "tasks": []}
    writes = []
    for tid, choice in config["tasks"].items():
        roles = {role: next(r for r in a["assignments"] if r["role"] == role and tid in r["instance_ids"])
                 for role in ("public_reader", "investigator", "reviewer")}
        for role in roles.values():
            assert role["status"] == "completed"
            for sealed in role["sealed_outputs"]:
                H["snapshot"](sealed["file"], sealed["sha256"])
        out = B / "results" / tid
        review_path = out / "review.md"
        review_sha = sha(review_path.read_bytes())
        review_delivered = {x["file"]: x["sha256"] for x in roles["reviewer"]["output_completion_snapshots"]}
        assert review_delivered[str(review_path.relative_to(ROOT))] == review_sha
        delivered = {x["file"]: x["sha256"] for x in roles["investigator"]["output_completion_snapshots"]}
        before = {}
        for filename in ("card.md", "screening_record.json"):
            path = out / filename
            raw = path.read_bytes()
            assert delivered[str(path.relative_to(ROOT))] == sha(raw)
            archived = revision_dir / tid / filename
            before[filename] = {"file": str(archived.relative_to(ROOT)), "sha256": sha(raw)}
            writes.append((archived, raw))
        card = (out / "card.md").read_text()
        for old, new in choice.get("card_replacements", []):
            assert card.count(old) == 1, (tid, old)
            card = card.replace(old, new)
        card += "\n\n" + choice["card_append"] + "\n"
        record = json.loads((out / "screening_record.json").read_text())
        if isinstance(record["facts_ref"], list):
            record["facts_ref"] = {"main_evidence_refs": record["facts_ref"]}
        record["facts_ref"]["independent_review"] = {"file": str(review_path), "sha256": review_sha,
            "phase": "sealed independent initial followed by explicitly released cross-review"}
        record["facts_ref"]["reviewer"] = "completed; main private-exposure statement remains as-of its delivery"
        record["facts_ref"]["coordinator_adjudication"] = {"by": "/root", "at": at,
            "report": str(B / config["report"]), "revision_log": str(revision_dir / "revision_log.json"),
            "read_scope": str(B / "reserve20_coordinator_read_notes.md")}
        record["disposition"].update(reviewer_status="completed", static_classification=choice["classification"], ready_for_probe=False)
        record["disposition"].update(choice.get("disposition", {}))
        record["usage"]["coordinator_exposure"] = {"public_and_private_task_materials": True,
            "sealed_role_outputs": True, "history_scope": "selected task fields as documented in coordinator read notes",
            "actual_actor_answer_exposure": "unknown", "training_or_formal_evaluation_admission": False}
        for number, fields in choice.get("checks", {}).items():
            entry = record["checks"].setdefault(number, {"evidence_refs": []})
            entry.update(fields)
            entry["by"] = "/root / coordinator adjudication after independent cross-review"
            for ref in (str(review_path), str(B / config["report"])):
                if ref not in entry["evidence_refs"]:
                    entry["evidence_refs"].append(ref)
        for category, fields in choice.get("issue_updates", {}).items():
            matches = [x for x in record["issues"] if x["category"] == category]
            assert len(matches) == 1, (tid, category)
            matches[0].update(fields)
        record["issues"].extend(choice.get("add_issues", []))
        for path_parts, value in choice.get("record_overrides", []):
            target = record
            for part in path_parts[:-1]:
                target = target[part]
            target[path_parts[-1]] = value
        after = {}
        for filename, raw in (("card.md", card.encode()),
                ("screening_record.json", (json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode())):
            path = out / filename
            after[filename] = {"file": str(path.relative_to(ROOT)), "sha256": sha(raw)}
            writes.append((path, raw))
        revision_log["tasks"].append({"instance_id": tid, "before": before, "after": after, "changes": choice["changes"]})
    # Validate the entire package before writing any archive or final file.
    for path, raw in writes:
        assert path.is_relative_to(B)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    (revision_dir / "revision_log.json").write_text(json.dumps(revision_log, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"package": package, "tasks": len(config["tasks"]), "archived_and_revised": 2 * len(config["tasks"])}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", required=True)
    adjudicate(parser.parse_args().package)
