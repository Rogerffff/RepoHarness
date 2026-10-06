"""经 prepare 槽核冻结来源镜像；只补缺失别名，不覆盖已有别名或改依赖。"""
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", type=Path, required=True)
    ap.add_argument("--release-manifest-sha256", required=True)
    ap.add_argument("--instance-id", required=True)
    ap.add_argument("--expected-image-id", required=True)
    ap.add_argument("--statement-sha256", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--run-id", required=True)
    ns = ap.parse_args()
    assert re.fullmatch(r"dask__dask-\d+", ns.instance_id)
    assert re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{5,78}", ns.run_id)
    assert hashlib.sha256((ns.release / "manifest.json").read_bytes()).hexdigest() == ns.release_manifest_sha256
    ns.out.mkdir(parents=True, exist_ok=False)
    state = {"scope": "current_frozen_source_image_preparation_only", "run_id": ns.run_id,
             "instance_id": ns.instance_id, "release_manifest_sha256": ns.release_manifest_sha256,
             "started_at": time.time(), "status": "running", "steps": []}
    child = None
    name = "rh2-dask-source-" + ns.run_id
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(ns.release / "repo/rh2/src")}

    def save():
        (ns.out / "status.json").write_text(json.dumps(state, indent=2) + "\n")

    def stop(signum, _frame):
        state["signal_received"] = signum
        save()
        if child is not None and child.poll() is None:
            child.send_signal(signum)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    def run(label, command, timeout, missing_allowed=False):
        nonlocal child
        row = {"name": label, "command": [str(x) for x in command], "started_at": time.time()}
        state["steps"].append(row)
        save()
        with (ns.out / (label + ".log")).open("wb") as stdout, (ns.out / (label + ".stderr")).open("wb") as stderr:
            child = subprocess.Popen(row["command"], stdout=stdout, stderr=stderr, env=env)
            try:
                code = child.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                child.terminate()
                try:
                    child.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=20)
                raise
        child = None
        row.update(returncode=code, finished_at=time.time())
        save()
        assert not state.get("signal_received"), "cancelled:" + label
        if code and missing_allowed and code == 1 and b"No such image" in (ns.out / (label + ".stderr")).read_bytes():
            return None
        assert code == 0 and not state.get("signal_received"), "command_incomplete:" + label
        return (ns.out / (label + ".log")).read_bytes()

    def inspect(label, image, missing_allowed=False):
        raw = run(label, ["docker", "image", "inspect", image], 120, missing_allowed)
        if raw is None:
            return None
        rows = json.loads(raw)
        assert len(rows) == 1 and rows[0]["Id"] == ns.expected_image_id
        assert pinned in rows[0].get("RepoDigests", [])
        return rows[0]

    try:
        run("verify_release", [sys.executable, "-B", ns.release / "verify_release.py"], 120)
        sys.path.insert(0, str(ns.release / "repo/rh2/src"))
        from repoharness2.envpack.swe_material_revisions import load_trusted_swe_revision_outputs

        public = next(p for p in load_trusted_swe_revision_outputs(ns.release / "repo").result.public_bundles
                      if p.instance_id == ns.instance_id)
        assert hashlib.sha256(public.problem_statement.encode()).hexdigest() == ns.statement_sha256
        repository = public.image.rsplit("@", 1)[0].rsplit(":", 1)[0]
        pinned = repository + "@" + public.image_manifest_digest
        current = inspect("inspect_digest_cache", pinned, True)
        state["source_digest_cache_present"] = current is not None
        if current is None:
            run("pull_digest", ["docker", "pull", pinned], 1800)
            current = inspect("inspect_digest_pulled", pinned)
        alias = inspect("inspect_source_alias_before", public.image, True)
        state["source_alias_created"] = alias is None
        if alias is None:
            run("create_missing_source_alias", ["docker", "tag", pinned, public.image], 120)
        inspect("inspect_source_alias_after", public.image)
        facts = run("image_checkout", ["docker", "run", "--rm", "--name", name,
                    "--label", "rh2.run_id=" + ns.run_id, "--network", "none", "--init", "--cpus", "2",
                    "--memory", "4g", "--memory-swap", "4g", "--pids-limit", "512", "--entrypoint", "bash",
                    ns.expected_image_id, "-c", "cd /testbed && echo HEAD=$(git rev-parse HEAD) && echo PORCELAIN_BEGIN && git status --porcelain; echo PORCELAIN_RC=$?"], 180)
        expected = ("HEAD=" + public.base_commit + "\nPORCELAIN_BEGIN\nPORCELAIN_RC=0\n").encode()
        assert facts == expected
        image = {"instance_id": ns.instance_id, "image_id": current["Id"], "repo_digests": current["RepoDigests"],
                 "rootfs_layers": current["RootFS"]["Layers"], "pinned_image": pinned, "base_commit": public.base_commit,
                 "public_bundle_digest": public.digest(), "statement_sha256": ns.statement_sha256,
                 "initial_worktree": facts.decode(), "dependency_changes": [], "source_alias": public.image}
        (ns.out / "image.json").write_text(json.dumps(image, indent=2) + "\n")
        state["status"] = "base_image_pulled_and_clean_checkout_verified"
    except BaseException as error:
        state.update(status="stopped_needs_diagnosis", error=repr(error))
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
        assert query.returncode == final.returncode == 0 and not final.stdout.strip(), "own_cleanup_unconfirmed"


if __name__ == "__main__":
    main()
