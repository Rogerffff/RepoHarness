"""冻结修订题面的实际公开 actor 字节交付；不向 actor 传私有测试或候选。"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def text_blocks(content) -> list[str]:
    if isinstance(content, str):
        return [content]
    return [block["text"] for block in content if isinstance(block, dict) and block.get("type") == "text"] if isinstance(content, list) else []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--release-manifest-sha256", required=True)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--image-readback", type=Path, required=True)
    parser.add_argument("--statement-sha256", required=True)
    parser.add_argument("--instance-id", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--cc-tarball", type=Path, required=True)
    parser.add_argument("--stub-host", default="172.17.0.1")
    parser.add_argument("--stub-port", type=int, default=18191)
    ns = parser.parse_args()
    assert re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{5,78}", ns.attempt_id)
    assert sha(ns.release / "manifest.json") == ns.release_manifest_sha256
    ns.out.mkdir(parents=True, exist_ok=False)
    assert re.fullmatch(r"dask__dask-\d+", ns.instance_id)
    task_id = "swe_gym_lite::" + ns.instance_id
    repo = ns.release / "repo"
    rh2 = repo / "rh2"
    task_dir = ns.input_root / "docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/repository_work/swe_dask/tasks" / ns.instance_id
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(rh2 / "src"),
           "SLIME_AGENT_CC_PLATFORM_TARBALL": str(ns.cc_tarball),
           "RH2_BRINGUP_ARTIFACT_DIR": str(ns.out / "actor/bringup_artifacts")}
    sys.path.insert(0, str(rh2 / "src"))
    from repoharness2.envpack.swe_material_revisions import load_trusted_swe_revision_outputs

    trusted = load_trusted_swe_revision_outputs(repo)
    parent_public = next(p for p in trusted.result.public_bundles if p.instance_id == ns.instance_id)
    public = parent_public.model_dump(mode="json")
    statement = (task_dir / "effective_statement.txt").read_bytes()
    assert hashlib.sha256(statement).hexdigest() == ns.statement_sha256
    assert public["problem_statement"].encode() == statement
    image_state = json.loads((ns.image_readback / "status.json").read_text())
    assert image_state["status"] == "base_image_pulled_and_clean_checkout_verified" and not image_state["cleanup"]["residual"]
    image = json.loads((ns.image_readback / "image.json").read_text())
    assert image["instance_id"] == ns.instance_id and image["base_commit"] == public["base_commit"]
    assert image["public_bundle_digest"] == parent_public.digest() and image["dependency_changes"] == []
    assert image["pinned_image"] in image["repo_digests"]
    assert image["pinned_image"].endswith("@" + public["image_manifest_digest"])
    assert image["initial_worktree"] == "HEAD=" + public["base_commit"] + "\nPORCELAIN_BEGIN\nPORCELAIN_RC=0\n"
    state = {"scope": "actual_current_public_actor_only_no_private_revision_or_model_inference", "attempt_id": ns.attempt_id,
             "release_manifest_sha256": ns.release_manifest_sha256, "actor_image_id": image["image_id"],
             "base_image_id": image["image_id"], "started_at": time.time(), "status": "running", "steps": []}
    child = None

    def save() -> None:
        write_json(ns.out / "status.json", state)

    def stop(signum, _frame):
        state["signal_received"] = signum
        save()
        if child is not None and child.poll() is None:
            child.send_signal(signum)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    def run(name: str, command: list) -> None:
        nonlocal child
        step = {"name": name, "started_at": time.time(), "command": list(map(str, command))}
        state["steps"].append(step)
        save()
        with (ns.out / (name + ".log")).open("wb") as log:
            child = subprocess.Popen(list(map(str, command)), stdout=log, stderr=subprocess.STDOUT, env=env)
            rc = child.wait()
        child = None
        step.update(returncode=rc, finished_at=time.time())
        save()
        if rc or state.get("signal_received"):
            raise RuntimeError(f"{name} 未正常完成；停止并保留输出")

    try:
        run("verify_release", [sys.executable, "-B", ns.release / "verify_release.py"])
        run("prepare_current_materials", [sys.executable, "-B", rh2 / "scripts/replay_grade.py", "prepare", "--repo-root", repo,
             "--out-dir", ns.out / "prepared", "--private-dir", ns.out / "host_private", "--sources", "swe_gym_lite", "--task-ids", task_id])
        commands = json.loads((task_dir / "public_actor_commands_20261003.json").read_text())
        write_json(ns.out / "public_actor_commands.json", commands)
        prompt = public["public_hints"] + "\n\n" + public["problem_statement"]
        (ns.out / "public_actor_prompt.txt").write_text(prompt)
        with socket.socket() as probe:
            probe.settimeout(1)
            assert probe.connect_ex((ns.stub_host, ns.stub_port)) != 0, "预留桩端口已被监听；不终止其它进程"
        run("actor", [sys.executable, "-B", rh2 / "experiments/task2_swegym_dev_20260925/devcheck.py",
             "--prepared-summary", ns.out / "prepared/replay_summary.json", "--task", task_id,
             "--commands", ns.out / "public_actor_commands.json", "--image", image["image_id"], "--out-dir", ns.out / "actor",
             "--attempt-id", ns.attempt_id + "-actor", "--stub-host", ns.stub_host, "--stub-port", str(ns.stub_port), "--wall-seconds", "1800", "--prompt", prompt])
        actual = json.loads((ns.out / "actor/attempt.json").read_text())
        assert actual.get("harness_exit_code") == 0 and not actual.get("cleanup", {}).get("residual_after_force")
        observations = actual.get("commands_result") or []
        assert len(observations) == len(commands)
        for expected, observed in zip(commands, observations):
            assert observed["id"] == expected["id"] and observed["status"] != "not_run"
            if expected["expect"] == "zero":
                assert observed["rc"] == 0
            elif expected["expect"] == "nonzero":
                assert observed["rc"] not in (0, 124, 137, None)
            else:
                assert expected["expect"] == "any" and observed["rc"] not in (124, 137, None)
        assert actual["effective_profile"]["cpus"] == 2 and actual["effective_profile"]["memory_bytes"] == 4 * 1024**3
        initial_worktree = actual["image_facts"]["initial_worktree"]
        assert initial_worktree == "HEAD=" + public["base_commit"] + "\nPORCELAIN_BEGIN\nPORCELAIN_RC=0\n"
        state["public_commands_result"] = observations
        first = json.loads((ns.out / "actor/stub/requests/messages_000.json").read_text())
        user_texts = [s for message in first["messages"] if message.get("role") == "user" for s in text_blocks(message.get("content"))]
        exact = any(public["problem_statement"] in s for s in user_texts)
        normalized = any(public["problem_statement"].replace("\r\n", "\n") in s.replace("\r\n", "\n") for s in user_texts)
        state["actual_public_prompt"] = {"statement_exact_match": exact, "statement_normalized_newlines_match": normalized,
             "current_problem_statement_sha256": public["problem_statement_sha256"], "first_request_sha256": sha(ns.out / "actor/stub/requests/messages_000.json"),
             "model_inference": "scripted_stub_no_baseline_model"}
        assert exact and normalized
        state["actual_public_prompt"]["original_CRLF_preserved_in_current_statement"] = statement.count(b"\r\n")
        assert statement.count(b"\r\n") == 162
        state["status"] = "current_public_actor_development_complete_no_formal_matrix_acceptance"
    except BaseException as exc:
        state.update(status="stopped_needs_diagnosis", error=repr(exc))
        raise
    finally:
        state["finished_at"] = time.time()
        save()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
