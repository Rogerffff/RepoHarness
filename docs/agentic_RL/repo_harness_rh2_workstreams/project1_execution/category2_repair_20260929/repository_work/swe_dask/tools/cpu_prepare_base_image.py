"""固定原镜像的拉取和读回；不改依赖，不运行评分。外层使用 prepare 槽。"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", type=Path, required=True)
    ap.add_argument("--release-manifest-sha256", required=True)
    ap.add_argument("--input-root", type=Path, required=True)
    ap.add_argument("--instance-id", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--run-id", required=True)
    ns = ap.parse_args()
    assert re.fullmatch(r"dask__dask-\d+", ns.instance_id)
    assert re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{5,78}", ns.run_id)
    assert hashlib.sha256((ns.release / "manifest.json").read_bytes()).hexdigest() == ns.release_manifest_sha256
    public_path = ns.input_root / "runs/swegym_quality_expansion_20260925/public" / ns.instance_id / "public_bundle.json"
    public = json.loads(public_path.read_text())
    pinned_image = public["image"].split("@", 1)[0].split(":", 1)[0] + "@" + public["image_manifest_digest"]
    ns.out.mkdir(parents=True, exist_ok=False)
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(ns.release / "repo/rh2/src")}
    state = {"scope": "fixed_base_image_preparation_only", "run_id": ns.run_id, "instance_id": ns.instance_id,
             "release_manifest_sha256": ns.release_manifest_sha256, "started_at": time.time(), "status": "running", "steps": []}
    container_name = "rh2-dask-prepare-" + ns.run_id
    child = None

    def save() -> None:
        (ns.out / "status.json").write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")

    def stop(signum, _frame):
        state["signal_received"] = signum
        save()
        if child is not None and child.poll() is None:
            child.send_signal(signum)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    def run(name: str, command: list[str], timeout: int) -> str:
        nonlocal child
        record = {"name": name, "started_at": time.time(), "command": list(map(str, command))}
        state["steps"].append(record)
        save()
        with (ns.out / (name + ".log")).open("w") as stdout, (ns.out / (name + ".stderr")).open("w") as stderr:
            child = subprocess.Popen(list(map(str, command)), stdout=stdout, stderr=stderr, env=env)
            try:
                rc = child.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                child.terminate()
                try:
                    child.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=20)
                raise
        child = None
        record.update(returncode=rc, finished_at=time.time())
        save()
        if rc or state.get("signal_received"):
            raise RuntimeError(f"{name} 未正常完成；停止并保留输出")
        return (ns.out / (name + ".log")).read_text()

    try:
        run("verify_release", [sys.executable, "-B", ns.release / "verify_release.py"], 120)
        sys.path.insert(0, str(ns.release / "repo/rh2/src"))
        from repoharness2.envpack.ingest_swegym_lite import load_trusted_ingest_outputs

        trusted = load_trusted_ingest_outputs(ns.release / "repo")
        official = next(b for b in trusted.result.public_bundles if b.instance_id == ns.instance_id)
        assert official.model_dump(mode="json") == public
        run("pull_image", ["docker", "pull", pinned_image], 3600)
        inspected = json.loads(run("inspect_image", ["docker", "image", "inspect", pinned_image], 120))[0]
        assert pinned_image in inspected["RepoDigests"]
        facts = run("image_checkout", ["docker", "run", "--rm", "--name", container_name,
                    "--label", "rh2.run_id=" + ns.run_id, "--network", "none", "--init", "--cpus", "2", "--memory", "4g",
                    "--memory-swap", "4g", "--pids-limit", "512", "--entrypoint", "bash", inspected["Id"], "-c",
                    "cd /testbed && echo HEAD=$(git rev-parse HEAD) && echo PORCELAIN_BEGIN && git status --porcelain; echo PORCELAIN_RC=$?"], 180)
        assert facts == "HEAD=" + public["base_commit"] + "\nPORCELAIN_BEGIN\nPORCELAIN_RC=0\n"
        image = {"instance_id": ns.instance_id, "image_id": inspected["Id"], "repo_digests": inspected["RepoDigests"],
                 "rootfs_layers": inspected["RootFS"]["Layers"], "pinned_image": pinned_image, "base_commit": public["base_commit"],
                 "public_bundle_digest": official.digest(), "initial_worktree": facts, "dependency_changes": []}
        (ns.out / "image.json").write_text(json.dumps(image, indent=2) + "\n")
        state["status"] = "base_image_pulled_and_clean_checkout_verified"
    except BaseException as exc:
        state.update(status="stopped_needs_diagnosis", error=repr(exc))
        raise
    finally:
        query = subprocess.run(["docker", "ps", "-aq", "--filter", "label=rh2.run_id=" + ns.run_id], capture_output=True, text=True, timeout=60)
        state["cleanup"] = {"query_rc": query.returncode, "selected": query.stdout.split()}
        if query.returncode == 0 and query.stdout.strip():
            removed = subprocess.run(["docker", "rm", "-f", *query.stdout.split()], capture_output=True, text=True, timeout=120)
            state["cleanup"]["rm_rc"] = removed.returncode
        final = subprocess.run(["docker", "ps", "-aq", "--filter", "label=rh2.run_id=" + ns.run_id], capture_output=True, text=True, timeout=60)
        state["cleanup"].update(final_query_rc=final.returncode, residual=final.stdout.split())
        state["finished_at"] = time.time()
        save()
        if query.returncode or final.returncode or final.stdout.strip():
            raise RuntimeError("本次镜像准备清理未确认；停止接续")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
