"""在 CPU 作业内复用冻结构建入口；只准备镜像，不运行评分或模型。

Docker run 经过本包小包装器补独立标签和准备期资源限制，便于超时后
仅清理本作业。构建源码、镜像 digest、wheel 与原配方保持独立可核身份。
外层必须使用 cpu_slot.py --mode prepare，输出只写本包。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path


SHIM = '''#!/usr/bin/env python3
import json,os,subprocess,sys,uuid
from pathlib import Path
args=sys.argv[1:]
if args and args[0]=="run":
 name="rh2-dask-prep-"+uuid.uuid4().hex[:12]
 extra=["--name",name,"--label","rh2.run_id="+os.environ["DASK_PREP_RUN_ID"],"--pids-limit","512"]
 if "--cpus" not in args:extra += ["--cpus","2"]
 if "--memory" not in args:extra += ["--memory","2g"]
 if "--memory-swap" not in args:extra += ["--memory-swap","2g"]
 args=["run",*extra,*args[1:]]
 with Path(os.environ["DASK_PREP_RUN_RECORD"]).open("a") as f:
  f.write(json.dumps({"name":name,"args":args})+"\\n")
raise SystemExit(subprocess.call([os.environ["DASK_PREP_REAL_DOCKER"],*args]))
'''


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", type=Path, required=True)
    ap.add_argument("--release-manifest-sha256", required=True)
    ap.add_argument("--input-root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--run-id", required=True)
    ns = ap.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}", ns.run_id):
        ap.error("run-id 格式不合法")
    assert hashlib.sha256((ns.release / "manifest.json").read_bytes()).hexdigest() == ns.release_manifest_sha256
    source = ns.release / "repo/rh2"
    plans = ns.input_root / "runs/swegym_cpu_preprobe_20260929/task_inputs/dask__dask-7656"
    ns.out.mkdir(parents=True, exist_ok=False)
    real_docker = shutil.which("docker")
    assert real_docker
    shims = ns.out / "docker_cli"
    shims.mkdir()
    (shims / "docker").write_text(SHIM)
    (shims / "docker").chmod(0o700)
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(source / "src"),
           "DASK_PREP_RUN_ID": ns.run_id, "DASK_PREP_RUN_RECORD": str(ns.out / "run_containers.jsonl"),
           "DASK_PREP_REAL_DOCKER": real_docker, "PATH": str(shims) + ":" + os.environ["PATH"]}
    state = {"scope": "image_preparation_only_not_actor_or_scoring", "run_id": ns.run_id,
             "release_manifest_sha256": ns.release_manifest_sha256, "started_at": time.time(),
             "status": "running", "steps": []}

    def save() -> None:
        write_json(ns.out / "status.json", state)

    def run(name: str, args: list, timeout: int) -> None:
        step = {"name": name, "args": list(map(str, args)), "started_at": time.time()}
        state["steps"].append(step)
        save()
        with (ns.out / (name + ".log")).open("wb") as log:
            result = subprocess.run(list(map(str, args)), stdout=log, stderr=subprocess.STDOUT, env=env, timeout=timeout)
        step.update(returncode=result.returncode, finished_at=time.time())
        save()
        if result.returncode:
            raise RuntimeError(f"{name} 失败；停止并保留本作业证据")

    def interrupted(signum, _frame):
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        run("verify_release", [sys.executable, "-B", ns.release / "verify_release.py"], 120)
        run("grader_build", [sys.executable, source / "experiments/base_probe_20260922/build_derived.py",
            "--plan", plans / "grader_build_plan.json", "--out-dir", ns.out / "grader_build", "--tag-suffix", ns.run_id], 6000)
        actor = json.loads((plans / "actor_build_plan.json").read_text())
        assert len(actor) == 1 and actor[0]["instance_id"] == "dask__dask-7656"
        actor[0]["name"] = "swe_dask_7656_actor_" + ns.run_id
        write_json(ns.out / "actor_build_plan.json", actor)
        run("actor_build", [sys.executable, source / "experiments/task2_swegym_dev_20260925/build_actor.py",
             ns.out / "actor_build_plan.json", "--out-dir", ns.out / "actor_build"], 6000)
        state["status"] = "images_built_pending_readback"
    except BaseException as exc:
        state.update(status="stopped_needs_diagnosis", error=repr(exc))
        raise
    finally:
        selected = subprocess.run([real_docker, "ps", "-aq", "--filter", "label=rh2.run_id=" + ns.run_id], capture_output=True, text=True, timeout=60)
        cleanup = {"query_rc": selected.returncode, "selected_containers": selected.stdout.split()}
        if selected.returncode == 0 and selected.stdout.strip():
            rm = subprocess.run([real_docker, "rm", "-f", *selected.stdout.split()], capture_output=True, text=True, timeout=120)
            cleanup.update(rm_rc=rm.returncode, stderr=rm.stderr[-1500:])
        remaining = subprocess.run([real_docker, "ps", "-aq", "--filter", "label=rh2.run_id=" + ns.run_id], capture_output=True, text=True, timeout=60)
        cleanup.update(final_query_rc=remaining.returncode, residual=remaining.stdout.split())
        state.update(cleanup=cleanup, finished_at=time.time())
        save()
        if selected.returncode or remaining.returncode or remaining.stdout.strip():
            raise RuntimeError("准备容器清理未确认；停止接续派发")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
