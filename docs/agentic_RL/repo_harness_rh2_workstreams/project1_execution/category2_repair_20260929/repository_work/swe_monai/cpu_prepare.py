"""MONAI 固定镜像准备；通过 cpu_slot.py prepare 启动，不作正式验收。"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time
import urllib.request


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inputs", required=True, type=Path)
    p.add_argument("--task", required=True, choices=["2446", "3715", "6975"])
    p.add_argument("--job", required=True)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{0,100}", a.job):
        p.error("unsafe job identifier")
    a.out.mkdir(parents=True, exist_ok=False)
    state = {"task": a.task, "job": a.job, "status": "preparing", "steps": [],
             "started_at": time.time(), "scope": "image and source identity only",
             "actor_verified": False, "new_test_executed": False,
             "formal_acceptance_passed": False}
    active = None
    container = "rh2-swe-monai-" + a.job
    label = "rh2.run_id=" + a.job

    def save():
        temp = a.out / "preparation.json.tmp"
        temp.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")
        temp.replace(a.out / "preparation.json")

    def interrupted(signum, _frame):
        if active is not None and active.poll() is None:
            os.killpg(active.pid, signal.SIGTERM)
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)

    def run(name, args, seconds=300, check=True):
        nonlocal active
        logfile = a.out / (name + ".log")
        start = time.time()
        with logfile.open("wb") as f:
            active = subprocess.Popen(args, stdout=f, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                rc = active.wait(timeout=seconds)
            except subprocess.TimeoutExpired:
                os.killpg(active.pid, signal.SIGTERM)
                try:
                    active.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    os.killpg(active.pid, signal.SIGKILL)
                    active.wait()
                rc = 124
            finally:
                active = None
        state["steps"].append({"name": name, "command": args, "rc": rc,
                                "seconds": time.time() - start, "log_sha256": digest(logfile)})
        save()
        if check and rc != 0:
            raise RuntimeError(name + " failed: " + str(rc))
        return logfile, rc

    def inspect(name, image):
        path, _ = run(name, ["docker", "image", "inspect", image], 60)
        value = json.loads(path.read_text())[0]
        if value["Architecture"] != "amd64" or value["Os"] != "linux":
            raise RuntimeError("unexpected platform")
        return value

    save()
    created = False
    try:
        manifest = json.loads((a.inputs / "input_manifest.json").read_text())
        for rel, entry in manifest["files"].items():
            path = (a.inputs / rel).resolve()
            if not path.is_relative_to(a.inputs.resolve()) or not path.is_file():
                raise RuntimeError("invalid input: " + rel)
            if path.stat().st_size != entry["bytes"] or digest(path) != entry["sha256"]:
                raise RuntimeError("input changed: " + rel)
        state["input_manifest_sha256"] = digest(a.inputs / "input_manifest.json")
        config = manifest["tasks"][a.task]
        source = config["source_image"]
        run("pull", ["docker", "pull", source], 3600)
        base = inspect("base_inspect", source)
        if source not in base.get("RepoDigests", []):
            raise RuntimeError("immutable source digest not present")
        state.update(source_image=source, base_image_id=base["Id"])
        image = base["Id"]
        if a.task == "2446":
            build = a.out / "build"
            wheels = build / "wheels"
            wheels.mkdir(parents=True)
            expected = json.loads((a.inputs / "recovery2446/wheel_manifest.json").read_text())[0]
            wheel = wheels / expected["name"]
            archived = a.inputs / "recovery2446/wheels" / expected["name"]
            if archived.is_file():
                shutil.copyfile(archived, wheel)
                wheel_source = "already hashed archived wheel from prior preparation"
            else:
                with urllib.request.urlopen("https://pypi.org/pypi/nibabel/4.0.2/json", timeout=60) as response:
                    metadata = json.load(response)
                matches = [x for x in metadata["urls"] if x["filename"] == expected["name"]]
                if len(matches) != 1 or matches[0]["digests"]["sha256"] != expected["sha256"]:
                    raise RuntimeError("wheel index identity differs")
                with urllib.request.urlopen(matches[0]["url"], timeout=120) as response:
                    wheel.write_bytes(response.read())
                wheel_source = matches[0]["url"]
            if wheel.stat().st_size != expected["bytes"] or digest(wheel) != expected["sha256"]:
                raise RuntimeError("downloaded wheel differs")
            state["wheel"] = dict(expected, source=wheel_source)
            dockerfile = build / "Dockerfile"
            dockerfile.write_bytes((a.inputs / "recovery2446/Dockerfile.recovery").read_bytes())
            tag = "rh2-category2-20261003/swe-monai-2446:" + a.job
            run("build", ["docker", "build", "--pull=false", "--network=none", "--build-arg",
                          "BASE_IMAGE=" + source, "--label", "rh2.package=swe_monai", "--label", label,
                          "-t", tag, str(build)], 1800)
            derived = inspect("derived_inspect", tag)
            if derived["RootFS"]["Layers"][:len(base["RootFS"]["Layers"])] != base["RootFS"]["Layers"]:
                raise RuntimeError("source layer prefix changed")
            image = derived["Id"]
            state.update(tag=tag, dockerfile_sha256=digest(dockerfile))
        state["actual_image_id"] = image
        # 只证明镜像中的来源初态与依赖身份；root 容器不能代替 actor 权限检查。
        probe = """import os,sys,json,subprocess,hashlib,importlib.metadata as m
os.chdir('/testbed')
files = json.loads(sys.argv[1])
versions={}
for name in ['numpy','torch','nibabel','pytest','pytorch-ignite']:
 try: versions[name]=m.version(name)
 except m.PackageNotFoundError: versions[name]=None
print(json.dumps({'uid':os.getuid(),'executable':sys.executable,
 'head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
 'porcelain':subprocess.check_output(['git','status','--porcelain'],text=True),
 'source_sha256':{x:hashlib.sha256(open(x,'rb').read()).hexdigest() for x in files},
 'versions':versions,'nifti_exists':os.path.isfile('tests/testing_data/ref_avg152T1_LR.nii.gz')},sort_keys=True))
"""
        run("create_identity", ["docker", "create", "--name", container, "--network", "none",
                               "--cpus", "2", "--memory", "4g", "--pids-limit", "512",
                               "--label", label, "--label", "rh2.package=swe_monai", "--entrypoint",
                               "/opt/miniconda3/envs/testbed/bin/python", image, "-I", "-c", probe,
                               json.dumps(list(config["source_sha256"]))], 120)
        created = True
        run("container_inspect", ["docker", "inspect", container], 60)
        path, _ = run("source_identity", ["docker", "start", "-a", container], 600)
        facts = json.loads(path.read_text())
        if facts["head"] != config["base_commit"] or facts["source_sha256"] != config["source_sha256"]:
            raise RuntimeError("source identity differs from frozen materials")
        if a.task == "2446" and facts["versions"]["nibabel"] != "4.0.2":
            raise RuntimeError("compatibility wheel not active")
        state["source_identity"] = facts
        state["status"] = "image_prepared_not_task_accepted"
    except BaseException as exc:
        state.update(status="preparation_failed", error=repr(exc))
        raise
    finally:
        # 名称和标签均只针对本次作业，不使用全机 prune 或全机空闲断言。
        if created:
            _, rc = run("remove_identity", ["docker", "rm", "-f", container], 120, check=False)
        else:
            rc = None
        path, query_rc = run("cleanup_query", ["docker", "ps", "-aq", "--filter", "label=" + label], 60, check=False)
        remaining = path.read_text().split() if query_rc == 0 else None
        state["cleanup"] = {"rm_rc": rc, "query_rc": query_rc, "remaining": remaining}
        state["finished_at"] = time.time()
        save()
        if query_rc != 0 or remaining or (created and rc != 0):
            raise RuntimeError("image preparation container cleanup unconfirmed")


if __name__ == "__main__":
    main()
