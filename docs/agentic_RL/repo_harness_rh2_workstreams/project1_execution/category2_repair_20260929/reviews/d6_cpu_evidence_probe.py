"""只读本地同步原始证据；不读 run_acceptance 的 review.json，不触发评分。"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
CODE = ROOT / "runs/category2_repair_20260929/frozen_d6_v1/code_v1"
EVIDENCE = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "runs/category2_repair_20260929/remote/d6/cpu_acceptance_v1"
REMOTE = "/work/category2_repair_20260929/d6/" + EVIDENCE.name + "/"
sys.path.insert(0, str(CODE / "rh2/src"))
sys.dont_write_bytecode = True

from repoharness2.adapters.slime.prepared_task_face import build_grading_spec_from_host_view
from repoharness2.contracts.baseline_manifest import BaselineWorkspaceManifestV1, compute_baseline_manifest_digest
from repoharness2.contracts.frozen_patch import FrozenPatchArtifactV1, compute_frozen_patch_digest
from repoharness2.envpack.prepared_tasks import load_host_grading_views, load_prepared_manifest, load_prepared_rollout_views
from repoharness2.envpack.training_view import TrustedTaskController
from repoharness2.grading.manager import grading_scripts_digest


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def local(remote):
    assert remote.startswith(REMOTE)
    return EVIDENCE / remote[len(REMOTE):]


def main():
    summary = read(EVIDENCE / "prepared/replay_summary.json")
    manifest = load_prepared_manifest(EVIDENCE / "prepared", expected_sha256=summary["prepared_manifest_sha256"])
    views = load_prepared_rollout_views(EVIDENCE / "prepared", manifest)
    hosts = load_host_grading_views(EVIDENCE / "private/host_grading_views.jsonl",
                                    expected_sha256=summary["host_grading_artifact_sha256"], manifest=manifest)
    controller = TrustedTaskController.from_repo_root(CODE)
    for tid in hosts:
        expected = controller.grading_view(tid, environment_package_digest=views[tid].environment_package_digest)
        assert hosts[tid] == expected, tid
    result = {"prepared_source_join": True, "rows": [], "pending": []}
    for iid in ("python__mypy-10424", "python__mypy-17071"):
        tid = "swe_gym_lite::" + iid
        view, host = views[tid], hosts[tid]
        spec = build_grading_spec_from_host_view(host, image=view.public.image, image_manifest_digest=view.public.image_manifest_digest)
        for variant in ("noop", "gold", "C1"):
            directory = EVIDENCE / iid / variant
            if not (directory / "ledger.jsonl").exists():
                result["pending"].append(iid + "/" + variant)
                continue
            lines = (directory / "ledger.jsonl").read_text().splitlines()
            assert len(lines) == 1
            row, report = json.loads(lines[0]), read(directory / "report.json")
            assert row["stage_error"] is None
            assert report["report_id"] == row["report"]["report_id"]
            log_path = local(row["log"]["path"])
            assert digest(log_path) == row["log"]["sha256"] == report["eval_log_ref"]["sha256"]
            assert log_path.stat().st_size == report["eval_log_ref"]["byte_size"]
            log = log_path.read_text()
            segment = log.split(">>>>> Start Test Output", 1)[1].split(">>>>> End Test Output", 1)[0]
            states = dict((node, state) for state, node in re.findall(r"^(PASSED|FAILED|SKIPPED|XFAIL|XPASS) (\S+)", segment, re.M))
            expected_refs = set(host.grading.fail_to_pass + host.grading.pass_to_pass)
            assert set(states) == expected_refs
            added = {case.node_id for case in host.grading.revision.added_mypy_cases}
            expected_states = {node: "FAILED" if (variant == "noop" and node in host.grading.fail_to_pass)
                               or (variant == "C1" and node in added) else "PASSED" for node in expected_refs}
            assert states == expected_states
            assert report["reward"] == (1.0 if variant == "gold" else 0.0)
            assert row["test"]["rc"] == (0 if variant == "gold" else 1)
            assert report["grading_semantics"] == "swe_f2p_p2p" and report["reward_scale_version"] == "binary_v1"
            diag = read(local(row["diagnostics_ref"]))
            assert diag["grading_revision"] == row["grading_revision"]
            for key in ("environment_package_digest", "grading_bundle_digest", "public_bundle_digest", "registry_sha256",
                        "parent_grading_digest", "revision_id", "materials_identity", "test_command", "parser_version"):
                assert row["grading_revision"][key] == spec.grading_revision.diagnostics(None)[key], key
            assert row["scripts_digest"] == grading_scripts_digest(spec)
            for key, refs in (("original_f2p", set(host.grading.fail_to_pass)),
                              ("original_p2p", set(host.grading.pass_to_pass) - added), ("added_p2p", added)):
                part = diag["grading_revision"]["partitions"][key]
                assert set(part["references"]) == refs
                assert set(part["result"]["success"]) == {n for n in refs if states[n] == "PASSED"}
                assert set(part["result"]["failure"]) == {n for n in refs if states[n] == "FAILED"}
                assert not any(part["result"][n] for n in ("missing", "skipped", "unaccounted"))
            frozen_paths = list((directory / "artifacts").rglob("frozen_patch.json"))
            assert len(frozen_paths) == 1
            frozen = FrozenPatchArtifactV1.model_validate_json(frozen_paths[0].read_text())
            baseline = BaselineWorkspaceManifestV1.model_validate_json((frozen_paths[0].parent / "baseline_manifest.json").read_text())
            projection = read(frozen_paths[0].parent / "projection.json")
            assert compute_baseline_manifest_digest(baseline) == frozen.baseline_manifest_digest
            assert compute_frozen_patch_digest(frozen) == projection["frozen_patch_digest"] == row["projection"]["frozen_patch_digest"]
            assert frozen.public_bundle_digest == baseline.public_bundle_digest == view.public_bundle_digest
            assert frozen.runtime_image_digest == baseline.runtime_image_digest == row["image_id_actual"]
            if variant == "noop":
                assert not frozen.entries
            else:
                assert digest(frozen_paths[0].parent / "candidate.patch") == row["candidate"]["patch_sha256"]
            source_hashes = {e.path: e.content_digest for e in baseline.entries}
            for e in frozen.entries:
                if e.operation == "delete":
                    source_hashes.pop(e.path, None)
                elif e.content_b64 is not None:
                    source_hashes[e.path] = "sha256:" + hashlib.sha256(base64.b64decode(e.content_b64)).hexdigest()
            extra = read(directory / "supplemental_observation.json")
            assert extra["user"] == "54322"
            obs = None
            if extra.get("exit_code") == 0:
                obs = json.loads(next(line[len("D6_AUDIT="):] for line in extra["stdout"].splitlines() if line.startswith("D6_AUDIT=")))
                assert all(source_hashes[m["path"].removeprefix("/testbed/")] == "sha256:" + m["sha256"] for m in obs["modules"])
                for case in host.grading.revision.added_mypy_cases:
                    observed = next(p for p in obs["protected"] if p["path"] == case.path)
                    assert case.base_sha256 == "sha256:" + observed["sha256"]
                    assert observed["uid"] == 0 and not observed["writable"]
            assert row["cleanup"]["removed"] and row["phases"]["grader_cleanup"] is not None
            close_path = EVIDENCE / iid / "manager_close.json"
            closed = read(close_path) if close_path.exists() else None
            if closed is not None:
                assert not closed["manager_close"]["containers_open"]
                assert closed["residue_query_rc"] == 0 and not closed["residue_stdout"].strip()
                assert not closed["manager_close"]["cleanup_failures"]
            result["rows"].append({"instance_id": iid, "variant": variant, "reward": report["reward"],
                                   "log_sha256": digest(log_path), "states": states,
                                   "frozen_entry_paths": [e.path for e in frozen.entries],
                                   "material_identity": spec.grading_materials_identity,
                                   "source_hashes_observed": obs["modules"] if obs else None, "install": row["install"],
                                   "supplemental_observation_complete": obs is not None,
                                   "supplemental_observation_error": None if obs else extra,
                                   "task_final_cleanup_verified": closed is not None,
                                   "batch_final_exit_code": closed["final_status"]["exit_code"] if closed else None})
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
