"""This batch's stdlib metadata helpers; no task execution or tool dispatch."""
import datetime
import hashlib
import json
from pathlib import Path

B = Path(__file__).resolve().parent
# Resolve by fixed workspace marker instead of relying on the caller cwd.
ROOT = next(p for p in B.parents if (p / "rh2/src/repoharness2").is_dir())


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def load():
    return json.loads((B / "assignments.json").read_text())


def save(a):
    roles = {r["agent_id"]: r for r in a["assignments"]}
    closed = {p["package_id"] for p in a["packages"]
              if p["status"] in ("static_review_completed", "static_review_accepted_by_parent")}
    for task in a["tasks"]:
        if task["stage"] != "reserve20":
            continue
        current = {}
        for role in ("public_reader", "investigator", "reviewer"):
            record = roles.get(task.get(role))
            if record:
                current[role] = record
                task.setdefault("role_states", {})[role] = {
                    "agent_id": record["agent_id"], "status": record["status"], "phase": record["phase"]}
        if task["package_id"] in closed:
            continue
        main, review, public = (current.get(k, {}) for k in ("investigator", "reviewer", "public_reader"))
        if main.get("status") == review.get("status") == "completed":
            task["status"] = "roles_completed_coordinator_adjudication_pending"
        elif review.get("phase") == "cross_review":
            task["status"] = "cross_review"
        elif main.get("phase") == "history_delta_and_final":
            task["status"] = "main_history_delta_and_final"
        elif main or review:
            task["status"] = "independent_review_in_progress"
        elif public.get("status") == "completed":
            task["status"] = "public_sealed_waiting_private_roles"
        elif public:
            task["status"] = "independent_public_read"
    a["live_role_status"] = {
        "running": [{"agent_id": r["agent_id"], "phase": r["phase"]}
                    for r in a["assignments"] if r["status"] == "running"],
        "waiting_release": [r["agent_id"] for r in a["assignments"] if r["status"] == "waiting_release"],
    }
    a["updated_at"] = now()
    (B / "assignments.json").write_text(json.dumps(a, ensure_ascii=False, indent=2) + "\n")


def snapshot(rel, expected):
    p = ROOT / rel
    actual = hashlib.sha256(p.read_bytes()).hexdigest()
    if actual != expected:
        raise ValueError(f"SHA mismatch: {rel}: {actual}")
    return {"file": rel, "sha256": actual,
            "saved_mtime_utc": datetime.datetime.fromtimestamp(p.stat().st_mtime, datetime.timezone.utc).isoformat(),
            "verified_at": now()}


def register(name, role, ids, output_names, phase, inputs):
    a = load()
    assert not any(r["agent_id"] == name for r in a["assignments"])
    at = now()
    outputs = [str((B / "results" / tid / filename).relative_to(ROOT)) for tid in ids for filename in output_names]
    a["assignments"].append({"agent_id": name, "id_kind": "canonical_agent_name_returned_by_tool",
        "role": role, "instance_ids": ids, "model": "gpt-6-astra", "reasoning_effort": "high",
        "fork_turns": "none", "fresh_context_requested": True,
        "configuration_basis": "explicit spawn arguments accepted; no independent backend verification",
        "started_at": at, "started_at_basis": "registered after successful spawn", "ended_at": None,
        "status": "running", "phase": phase, "inputs": inputs, "outputs": outputs, "sealed_outputs": []})
    for t in a["tasks"]:
        if t["instance_id"] in ids:
            t[role] = name
            t["status"] = phase
    a["events"].append({"at": at, "type": role + "_started", "agent_id": name,
                        "instance_ids": ids, "requested_model": "gpt-6-astra", "requested_reasoning_effort": "high", "fork_turns": "none"})
    save(a)


def seal(name, reported, public_complete=False):
    a = load(); r = next(r for r in a["assignments"] if r["agent_id"] == name)
    snapshots = [snapshot(p, h) for p, h in reported.items()]
    assert len(snapshots) == len(r["instance_ids"])
    assert not r["sealed_outputs"]
    for s in snapshots: s["immutable_after_seal"] = True
    r["sealed_outputs"] = snapshots; r["phase"] = "all_initials_sealed_waiting_release"
    at = now()
    if public_complete:
        assert r["role"] == "public_reader"
        r.update(status="completed", phase="completed", ended_at=at,
                 ended_at_basis="final report observed and output SHA verified")
    else:
        r["status"] = "waiting_release"
    a["events"].append({"at": at, "type": r["role"] + "_initials_sealed", "agent_id": name,
                        "instance_ids": r["instance_ids"], "outputs": snapshots})
    save(a)


def release(name, kind, refs):
    # Caller must invoke this only AFTER followup_task actually accepted the release.
    a = load(); r = next(r for r in a["assignments"] if r["agent_id"] == name)
    assert len(r["sealed_outputs"]) == len(r["instance_ids"])
    for s in r["sealed_outputs"]: snapshot(s["file"], s["sha256"])
    assert kind in ("history", "cross_review")
    at = now(); r[kind + "_release_at"] = at; r[kind + "_refs_released"] = refs
    r["status"] = "running"
    r["phase"] = "history_delta_and_final" if kind == "history" else "cross_review"
    a["events"].append({"at": at, "type": kind + "_released", "agent_id": name,
                        "instance_ids": r["instance_ids"], "refs": refs, "delivery": "followup_task accepted"})
    save(a)


def complete(name, reported):
    a = load(); r = next(r for r in a["assignments"] if r["agent_id"] == name)
    snapshots = [snapshot(p, h) for p, h in reported.items()]
    for s in r.get("sealed_outputs", []): snapshot(s["file"], s["sha256"])
    at = now(); r.update(status="completed", phase="completed", ended_at=at,
                         ended_at_basis="final report observed and output SHAs verified", output_completion_snapshots=snapshots)
    a["events"].append({"at": at, "type": r["role"] + "_completed", "agent_id": name,
                        "instance_ids": r["instance_ids"], "outputs": snapshots})
    save(a)
