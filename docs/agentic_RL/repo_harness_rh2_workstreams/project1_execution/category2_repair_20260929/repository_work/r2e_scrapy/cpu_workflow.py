"""Scrapy a95a 的薄执行编排：消费不可变发布版，复用原构建、评分与actor入口。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

IID = "scrapy__a95a338eeada7275a5289cf036136610ebaf07eb"
TASK = "r2e_gym_subset::" + IID
PACKAGE_ROOT = Path("/work/rh2-category2-20261003/packages/r2e_scrapy")
TEST_TREE = "sha256:e6f17ed8b7f80a0c0d6654f35d60e42bfd39a187f8c2442b854e388206349aeb"
EXPECTED_SHA = "sha256:95f7d31faf0fa9838958db3a8121edc60a6181b7194f4801d674ef41802fe8e9"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def owned(path):
    value = Path(path).resolve()
    assert value != PACKAGE_ROOT and PACKAGE_ROOT in value.parents, "输出或输入必须属于本包"
    return value


def bound_release(args):
    release = Path(args.release).resolve()
    assert sha(release / "manifest.json") == args.manifest_sha256
    manifest = json.loads((release / "manifest.json").read_text())
    repo = release / "repo"
    for name, item in manifest["files"].items():
        path = repo / name
        assert path.is_file() and not path.is_symlink() and sha(path) == item["sha256"], name
    sys.path.insert(0, str(repo / "rh2/src"))
    from repoharness2.envpack.ingest_r2e_subset import load_trusted_r2e_ingest_outputs
    trusted = load_trusted_r2e_ingest_outputs(repo)
    grading = next(x for x in trusted.result.grading_bundles if x.instance_id == IID)
    assert {x.revision_id for x in trusted.revisions[IID]} == {"r2e-mr-066", "r2e-mr-067"}
    assert grading.hidden_tests_tree_sha256 == TEST_TREE
    assert grading.expected_output_json_sha256 == EXPECTED_SHA
    return repo, {"release_id": manifest["release_id"], "manifest_sha256": args.manifest_sha256,
                  "revision_ids": ["r2e-mr-066", "r2e-mr-067"], "hidden_tests_tree_sha256": TEST_TREE,
                  "expected_output_sha256": EXPECTED_SHA, "workflow_sha256": sha(__file__)}


def command(repo, out, name, argv, *, run_id):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(repo / "rh2/src"), MILES_RH2_RUN_ID=run_id)
    with (out / (name + ".stdout.log")).open("w") as stdout, (out / (name + ".stderr.log")).open("w") as stderr:
        result = subprocess.run(argv, env=env, cwd=repo / "rh2", stdout=stdout, stderr=stderr)
    record = {"command": argv, "run_id": run_id, "exit_code": result.returncode}
    save(out / (name + ".command.json"), record)
    print(json.dumps({"step": name, "exit_code": result.returncode}), flush=True)
    if result.returncode:
        raise RuntimeError(name + " failed; preserve original logs and stop this run")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["trusted-prepare", "grade", "actor"], required=True)
    parser.add_argument("--release", required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--inputs", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--prepared-run", default=None)
    parser.add_argument("--actor-commands", default=None)
    args = parser.parse_args()
    repo, binding = bound_release(args)
    inputs, out = owned(args.inputs), owned(args.out)
    inventory = json.loads((inputs / "input_inventory.json").read_text())
    for item in inventory["files"]:
        assert "sha256:" + sha(inputs / item["path"]) == item["sha256"]
    out.mkdir(parents=True, exist_ok=False)
    save(out / "binding.json", {**binding, "phase": args.phase, "run_id": args.run_id,
                               "inputs": str(inputs), "input_inventory_sha256": sha(inputs / "input_inventory.json")})
    replay = str(repo / "rh2/scripts/replay_grade.py")
    if args.phase == "trusted-prepare":
        command(repo, out, "trusted_prepare", [sys.executable, replay, "prepare", "--repo-root", str(repo),
                "--out-dir", str(out / "prepared"), "--private-dir", str(out / "private"),
                "--sources", "r2e_gym_subset", "--task-ids", TASK], run_id=args.run_id)
        command(repo, out, "export_gold", [sys.executable, replay, "export-gold", "--ingest-dir",
                str(repo / "docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/ingest"),
                "--instance-ids", IID, "--out-dir", str(out / "gold")], run_id=args.run_id)
        assert sha(out / "gold" / (IID + ".gold.patch")) == sha(inputs / "candidates/gold.patch")
    else:
        prepared = owned(args.prepared_run)
        previous = json.loads((prepared / "binding.json").read_text())
        assert previous["manifest_sha256"] == binding["manifest_sha256"]
        facts = json.loads((prepared / "derived" / IID / "facts.json").read_text())
        assert facts["ok"], "须先通过已发布的共用构建/检查入口"
        common = ["--prepared-summary", str(prepared / "prepared/replay_summary.json")]
        overlays = str(prepared / "derived/overlays.jsonl")
        if args.phase == "grade":
            matrix = json.loads((inputs / "acceptance_matrix.json").read_text())
            assert len(matrix["rows"]) == sum(x["repeats"] for x in matrix["rows"]) == 8
            for row in matrix["rows"]:
                name = row["candidate"]
                candidate = "noop" if name == "noop" else "gold-dir:" + str(prepared / "gold") if name == "gold" else "patch:" + str(inputs / row["staged_patch"])
                command(repo, out, "grade_" + name, [sys.executable, replay, "run", *common, "--task-ids", IID,
                        "--candidate", candidate, "--image-overlays", overlays, "--eval-log-dir", str(out / (name + "_logs")),
                        "--artifacts-dir", str(out / (name + "_artifacts")), "--ledger", str(out / (name + ".jsonl"))],
                        run_id=args.run_id + "-" + name)
        else:
            actor_commands = owned(args.actor_commands)
            save(out / "actor_commands_binding.json", {"path": str(actor_commands), "sha256": sha(actor_commands),
                                                     "private_positive_control_not_model_context": True})
            command(repo, out, "actor_C1", [sys.executable, str(repo / "rh2/experiments/r2e_actor_20260925/r2e_devcheck.py"),
                    *common, "--overlays", overlays, "--task", IID, "--commands", str(actor_commands),
                    "--out-dir", str(out / "actor"), "--attempt-id", args.run_id, "--stub-port", "18197"], run_id=args.run_id)
    save(out / "steps_completed.json", {"phase": args.phase, "steps_completed": True,
                                       "task_acceptance_requires_evidence_review": True, "probe_ready": False})


if __name__ == "__main__":
    main()
