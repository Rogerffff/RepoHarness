"""等共享机器空闲后构建五个配方变体，再经冻结RH2串行评分。"""

from pathlib import Path
import hashlib
import json
import os
import signal
import subprocess
import time

ROOT = Path(os.environ.get("RH2_ENV_REPAIR_ROOT", "/work/env_recipe_repair_20260919/round2"))
OLD = Path("/work/full216_20260919")
PRIOR = ROOT.parent
CASES = [
    ("dvc4778-install-v2", "iterative__dvc-4778", "dvc4778"),
    ("mypy11966-wheels-v1", "python__mypy-11966", None),
    ("moto6913-wheels-v1", "getmoto__moto-6913", None),
    ("monai1121-numpy-v2", "Project-MONAI__MONAI-1121", "monai1121"),
    ("dask7138-pytest-v1", "dask__dask-7138", None),
]


def capture(args, timeout=120):
    return subprocess.check_output(args, text=True, timeout=timeout)


def save(name, data):
    (ROOT / "evidence" / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def busy():
    processes = capture(["ps", "-eo", "args"])
    return bool(capture(["docker", "ps", "-q"]).strip()) or "chainfix_verify" in processes


def source_content(image):
    return capture(["docker", "run", "--rm", "--init", "--network", "none", image, "bash", "-c",
                    "cd /testbed && git rev-parse HEAD && git diff && "
                    "sha256sum /opt/miniconda3/envs/testbed/bin/python3 && "
                    "/opt/miniconda3/envs/testbed/bin/python -I -c 'import sys;print(sys.version)' "])


def run():
    (ROOT / "logs").mkdir(exist_ok=True)
    deadline = time.time() + 7200
    save("dependency_batch_status.json", {"state": "waiting_for_shared_machine", "at": time.time()})
    while busy():
        if time.time() >= deadline:
            raise TimeoutError("共享机器仍在运行其它作业；没有切换内核或打断对方。")
        time.sleep(30)
    time.sleep(15)
    assert not busy(), "其它作业重新启动，暂不构建"
    prior = json.loads((PRIOR / "evidence/images.json").read_text())
    meta = Path("/sys/module/overlay/parameters/metacopy")
    original_meta = meta.read_text().strip()
    images = {}
    save("dependency_batch_status.json", {"state": "building", "at": time.time()})
    try:
        meta.write_text("N")
        for name, task, parent in CASES:
            # BuildKit会将裸sha256镜像ID误当作registry名称；用已核对身份的本地tag。
            base = prior[parent]["tag"] if parent else json.loads(
                (ROOT / "evidence" / task / "image.json").read_text())["RepoDigests"][0]
            base_id = json.loads(capture(["docker", "image", "inspect", base]))[0]["Id"]
            if parent:
                assert base_id == prior[parent]["image_id"]
            recipe = ROOT / "assets" / ("Dockerfile." + name)
            tag = "rh2-envrepair/" + name + ":20260919"
            with (ROOT / "logs" / (name + ".build.log")).open("w") as log:
                subprocess.run(["docker", "build", "--pull=false", "--force-rm", "--build-arg", "BASE_IMAGE=" + base,
                                "-f", str(recipe), "-t", tag, str(ROOT / "assets")],
                               stdout=log, stderr=subprocess.STDOUT, check=True, timeout=1200)
            image = json.loads(capture(["docker", "image", "inspect", tag]))[0]["Id"]
            before, after = source_content(base_id), source_content(image)
            assert before == after, "构建改变了原源码或解释器内容：" + name
            images[name] = {"task": task, "base": base, "base_id": base_id, "image_id": image, "tag": tag,
                            "representative_content": after,
                            "recipe_sha256": hashlib.sha256(recipe.read_bytes()).hexdigest()}
            save("dependency_images.json", images)
            print("BUILT", name, image, flush=True)
    finally:
        meta.write_text(original_meta)
        save("dependency_metacopy_restored.json", {"value": meta.read_text().strip(), "at": time.time()})

    py = str(OLD / "code/rh2/.venv/bin/python")
    for name, task, _ in CASES:
        for kind in (("noop", "gold", "canary") if name.startswith("dvc") else ("noop", "gold")):
            dest = ROOT / "runs" / (name + "-" + kind)
            dest.mkdir(parents=True, exist_ok=False)
            candidate = "noop" if kind == "noop" else "gold-dir:" + str(OLD / "replay/gold")
            if kind == "canary":
                patch = dest / "candidate.patch"
                patch.write_text((OLD / "replay/gold" / (task + ".gold.patch")).read_text() + "\n" +
                                 (ROOT / "canary/setup-canary.patch").read_text())
                candidate = "patch:" + str(patch)
            if name.startswith("dvc"):
                command = [py, str(ROOT / "replay_with_install_recipe.py"), "--code-root", str(OLD / "code/rh2"),
                           "--recipe", str(ROOT / "assets/dvc4778-install-v1.json"), "--audit-dir", str(dest / "recipe"), "--"]
            else:
                command = [py, str(OLD / "code/rh2/scripts/replay_grade.py")]
            command += ["run", "--prepared-summary", str(OLD / "replay/prepared/replay_summary.json"),
                        "--task-ids", task, "--candidate", candidate, "--derived-image", images[name]["image_id"],
                        "--derived-image-recipe", name + ("+dvc4778-install-v1.json" if name.startswith("dvc") else ""),
                        "--eval-log-dir", str(dest / "eval_logs"), "--artifacts-dir", str(dest / "artifacts"),
                        "--ledger", str(dest / "ledger.jsonl")]
            save("dependency_batch_status.json", {"state": "grading", "at": time.time(), "case": name, "kind": kind,
                                                   "command": command})
            with (dest / "driver.log").open("w") as log:
                subprocess.run(command, env=dict(os.environ, MILES_RH2_RUN_ID="er19-r2-" + name + "-" + kind),
                               cwd=OLD / "code/rh2", check=True, timeout=4800, stdout=log, stderr=subprocess.STDOUT)
            row = json.loads((dest / "ledger.jsonl").read_text())
            assert row["cleanup"]["removed"]
            assert row["stage_error"] is None, row["stage_error"]
            print("GRADED", name, kind, json.dumps({"report": row.get("report"), "install": row.get("install"),
                  "probe": (row.get("observations") or {}).get("RH2_OBS_INSTALL_PROBE")}), flush=True)
    save("dependency_batch_done.json", {"at": time.time(), "attempts": 11, "meaning": "execution finished; results require review"})


if __name__ == "__main__":
    def terminate(signum, frame):
        raise KeyboardInterrupt(f"signal {signum}")

    signal.signal(signal.SIGTERM, terminate)
    try:
        run()
    except BaseException as exc:
        save("dependency_batch_failed.json", {"at": time.time(), "type": type(exc).__name__, "detail": str(exc)})
        raise
