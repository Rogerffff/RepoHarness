"""仅检查已同步的 actor 原件；不启动 Docker/CC，不读取自动验收结论代替重算。"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[6]
BASE = ROOT / "runs/category2_repair_20260929"
CODE = BASE / "frozen_d6_v1/code_v1"
CPU = BASE / "remote/d6/cpu_acceptance_v1"
EVIDENCE = BASE / "remote/d6/actor_acceptance_v1"
sys.path.insert(0, str(CODE / "rh2/src"))
sys.dont_write_bytecode = True

from repoharness2.adapters.slime.prepared_task_face import PreparedTaskFace
from repoharness2.contracts.baseline_manifest import BaselineWorkspaceManifestV1, compute_baseline_manifest_digest
from repoharness2.contracts.frozen_patch import FrozenPatchArtifactV1, compute_frozen_patch_digest
from repoharness2.contracts.scoring_projection import classify_frozen_patch
from repoharness2.grading.manager import FrozenDeltaSource, SWEGradingManager
from repoharness2.grading.trusted_projection import build_trusted_scoring_projection


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def marked(path, prefix):
    values = [json.loads(line[len(prefix):]) for line in path.read_text().splitlines() if line.startswith(prefix)]
    assert len(values) == 1
    return values[0]


def main():
    actor_path = BASE / "tools/d6_actor_acceptance_v1/actor_acceptance.py"
    loader = importlib.util.spec_from_file_location("d6_actor_review", actor_path)
    actor = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(actor)
    ns = SimpleNamespace(code_root=CODE, code_manifest=CODE.parent / "code_v1_manifest.json")
    Registry, _, _ = actor.binding_components(ns)
    assignment_type = sys.modules["repoharness2.adapters.miles.attempt_assignment"].AttemptAssignment
    summary = read(CPU / "prepared/replay_summary.json")
    face = PreparedTaskFace.load(prepared_dir=CPU / "prepared", manifest_sha256=summary["prepared_manifest_sha256"],
                                 host_grading_path=CPU / "private/host_grading_views.jsonl",
                                 host_grading_sha256=summary["host_grading_artifact_sha256"],
                                 prompt_data_path=CPU / "prepared/prompts.jsonl", time_budget_seconds=900)
    rows = []
    for iid, task in actor.TASKS.items():
        folder = EVIDENCE / iid
        if not (folder / "recordmanifest.json").exists():
            rows.append({"task": iid, "state": "pending"})
            continue
        manifest, rec = read(folder / "recordmanifest.json"), read(folder / "attempt.json")
        for rel, expected in manifest["files"].items():
            path = folder / rel
            assert sha(path) == expected["sha256"] and path.stat().st_size == expected["bytes"], rel
        assert rec["actor_runner_sha256"] == sha(actor_path)
        assert rec["code_manifest_sha256"] == sha(ns.code_manifest)
        assert rec["prepared_summary_sha256"] == sha(CPU / "prepared/replay_summary.json")
        dispatch = read(folder / "dispatch.json")
        assignment = assignment_type(**dispatch["assignment"])
        assert rec["assignment"] == dispatch["assignment"]
        registry = Registry(verify_dispatch=face.verify_dispatch, capacity=1)
        registry.bind(assignment)
        resolved = registry.resolve_for_sample(dispatch["sample_metadata"])
        spec, rollout = face.grading_spec(resolved), face.rollout_spec(resolved.task_id)
        assert rollout.grading_spec is None
        assert rec["prompt_sha256"] == hashlib.sha256(rollout.prompt.encode()).hexdigest()
        join = read(folder / "frozen_material_join.json")
        assert join["grading_materials_identity"] == spec.grading_materials_identity
        assert join["grading_revision"] == spec.grading_revision.diagnostics(None)
        assert join["assignment"] == dispatch["assignment"]
        baseline = BaselineWorkspaceManifestV1.model_validate_json((folder / "baseline_manifest.json").read_text())
        frozen = FrozenPatchArtifactV1.model_validate_json((folder / "frozen_patch.json").read_text())
        assert not frozen.entries and not frozen.excluded_pathset_changed
        assert frozen.baseline_manifest_digest == compute_baseline_manifest_digest(baseline)
        assert frozen.runtime_image_digest == task["image_id"] == rec["runtime_image_id"]
        assert frozen.physical_attempt_id == assignment.physical_attempt_id
        assert frozen.rollout_execution_id == assignment.rollout_execution_id
        assert frozen.public_bundle_digest == assignment.public_bundle_digest == rollout.public_bundle_digest
        projection, split = build_trusted_scoring_projection(frozen, spec.hygiene)
        classification, _ = classify_frozen_patch(frozen, baseline)
        assert classification.model_dump(mode="json") == read(folder / "classification.json")
        assert classification.verdict == "projectable"
        assert not split.ignored_entries and not split.unsupported_shape_reasons
        assert projection.model_dump(mode="json") == read(folder / "projection.json") == join["projection"]
        assert compute_frozen_patch_digest(frozen) == join["frozen_patch_digest"]
        assert sha(folder / "frozen_patch.json") == join["frozen_patch_file_sha256"]
        assert sha(folder / "baseline_manifest.json") == join["baseline_file_sha256"]
        SWEGradingManager._verify_frozen_delta_binding(None, spec, FrozenDeltaSource(
            frozen_patch=frozen, baseline_manifest=baseline, projection=projection,
            frozen_patch_digest=compute_frozen_patch_digest(frozen)))
        events = [json.loads(line) for line in (folder / "harness/trajectory.jsonl").read_text().splitlines()]
        calls = [block for event in events if event["type"] == "assistant" for block in event["message"]["content"] if block["type"] == "tool_use"]
        expected = actor.script_for(actor.commands_for(task))[:3]
        assert [{"kind": "tool_use", "name": c["name"], "input": c["input"]} for c in calls] == expected
        result = [event for event in events if event["type"] == "result"]
        assert len(result) == 1 and result[0]["subtype"] == "success" and not result[0]["is_error"]
        stub = read(folder / "stub/stub_log.json")
        assert len(stub) == 4
        assert sum(e["type"] == "stream_event" and e["event"]["type"] == "message_start" for e in events) == 4
        for index, item in enumerate(stub):
            path = folder / "stub/requests" / f"messages_{index:03d}.json"
            assert path.stat().st_size == item["bytes"]
            request = read(path)
            assert request["messages"][0]["content"][1]["text"] == rollout.prompt
            assert len(request["messages"]) == 1 + 2 * index
            request_text = path.read_text()
            for forbidden in ("grading_materials_identity", "host_grading_views", "fail_to_pass", "pass_to_pass", "C1: disable", "grading_revision"):
                assert forbidden not in request_text, forbidden
        log = rec["launch_facts"]["harness_log"]
        assert log["log_complete"] and log["exec_state"] == "exited" and log["inspect"]["ExitCode"] == 0 and not log["inspect"]["Running"]
        assert (folder / "harness/trajectory.jsonl").stat().st_size == log["stdout_bytes"]
        assert (folder / "harness/stderr.log").stat().st_size == log["stderr_bytes"] == 0
        for capture in rec["commands_result"]:
            path = folder / "captures" / (capture["id"] + ".full")
            assert capture["rc"] == 0 and capture["complete"]
            assert path.stat().st_size == capture["bytes"] == capture["declared_bytes"] and sha(path) == capture["sha256"]
        identity = marked(folder / "captures/identity.full", "D6_IDENTITY=")
        assert identity["uid"] == identity["gid"] == 54321 and identity["cwd"] == "/testbed" and identity["home"] == "/home/agent"
        assert identity["conda"] == "testbed" and identity["prefix"] == rollout.expected_interpreter_prefix
        assert identity["python"] == rollout.expected_interpreter_prefix + "/bin/python"
        assert identity["bash_env"] == "/rh2/bash_env" and all(p["uid"] == 0 and not p["writable"] for p in identity["control_paths"])
        observed = marked(folder / "captures/module_sources.full", "D6_MODULES=")
        hashes = {entry.path: entry.content_digest for entry in baseline.entries}
        assert {m["name"] for m in observed["modules"]} == set(task["modules"])
        for module in observed["modules"]:
            assert module["path"].startswith("/testbed/") and module["path"].endswith(".py")
            assert hashes[module["path"].removeprefix("/testbed/")] == "sha256:" + module["sha256"]
        assert hashes[task["public_file"]] == "sha256:" + observed["public_file"]["sha256"]
        states = {node: state for state, node in re.findall(r"^(PASSED|FAILED|SKIPPED|XFAIL|XPASS) (\S+)", (folder / "captures/public_cases.full").read_text(), re.M)}
        references = spec.grading_revision.diagnostics(None)["partitions"]["added_p2p"]["references"]
        assert states == {node: "PASSED" for node in references}
        quiescence = read(folder / "quiescence.json")
        assert quiescence["result_type"] == "QuiescenceConfirmed"
        stop = quiescence["termination"]["barrier_stop"]
        assert stop["residual"] == 0 and not stop["timed_out"]
        assert set(quiescence["evidence_refs"]) == {"agent_processes_zero", "workspace_digest_stable_double_read"}
        assert rec["direct_stub_session_close"]["stub_exited"] and not rec["direct_stub_session_close"]["relay_close_failures"]
        assert rec["released_after_durable_freeze"]["rc"] == 0
        cleanup = rec["cleanup"]
        assert not cleanup["errors"] and not cleanup["active_assignments_after"] and cleanup["assignment_released"]
        for kind in ("containers", "networks"):
            assert cleanup[kind]["query_rc"] == 0 and not cleanup[kind]["stdout"].strip()
        assert manifest["exit_code"] == 0
        registry.release(assignment.physical_attempt_id)
        batch = "cpu_acceptance_v1" if iid.endswith("10424") else "cpu_acceptance_v2"
        replay_path = next((BASE / "remote/d6" / batch / iid / "noop/artifacts").rglob("baseline_manifest.json"))
        replay_baseline = BaselineWorkspaceManifestV1.model_validate_json(replay_path.read_text())
        actor_fields, replay_fields = baseline.model_dump(mode="json"), replay_baseline.model_dump(mode="json")
        differences = {key: {"actor": actor_fields[key], "completed_replay": replay_fields[key]}
                       for key in actor_fields if actor_fields[key] != replay_fields[key]}
        rows.append({"task": iid, "files_verified": len(manifest["files"]), "trajectory_sha256": sha(folder / "harness/trajectory.jsonl"),
                     "frozen_digest": compute_frozen_patch_digest(frozen), "material_identity": spec.grading_materials_identity,
                     "states": states, "state": "public_freeze_pure_binding_verified_fresh_rebuild_pending",
                     "actor_baseline_digest": compute_baseline_manifest_digest(baseline),
                     "completed_replay_baseline_digest": compute_baseline_manifest_digest(replay_baseline),
                     "cross_path_baseline_differences": differences})
    print(json.dumps(rows, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
