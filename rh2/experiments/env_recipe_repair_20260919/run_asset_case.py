"""MONAI-3205的COPY-only资产变体；保持主机配置，不改其它作业。"""

from pathlib import Path
import hashlib
import json
import os
import subprocess
import time

ROOT = Path("/work/env_recipe_repair_20260919/round2")
OLD = Path("/work/full216_20260919")
TASK = "Project-MONAI__MONAI-3205"


def capture(args):
    return subprocess.check_output(args, text=True, timeout=120)


def save(name, data):
    (ROOT / "evidence" / name).write_text(json.dumps(data, indent=2) + "\n")


def run():
    base = json.loads((ROOT / "evidence" / TASK / "image.json").read_text())
    meta = Path("/sys/module/overlay/parameters/metacopy")
    before_meta = meta.read_text().strip()
    tag = "rh2-envrepair/monai3205:20260919-assets-v1"
    recipe = ROOT / "assets/Dockerfile.monai3205-assets-v1"
    (ROOT / "logs").mkdir(exist_ok=True)
    with (ROOT / "logs/monai3205_build.log").open("w") as log:
        subprocess.run(["docker", "build", "--pull=false", "--force-rm", "--build-arg",
                        "BASE_IMAGE=" + base["RepoDigests"][0], "-f", str(recipe), "-t", tag,
                        str(ROOT / "assets")], stdout=log, stderr=subprocess.STDOUT, check=True, timeout=600)
    original = json.loads(capture(["docker", "image", "inspect", base["Id"]]))[0]
    image = json.loads(capture(["docker", "image", "inspect", tag]))[0]
    assert image["RootFS"]["Layers"][:-1] == original["RootFS"]["Layers"]
    script = "cd /testbed && git rev-parse HEAD && git diff && sha256sum /opt/miniconda3/envs/testbed/bin/python3 monai/apps/datasets.py"
    contents = [capture(["docker", "run", "--rm", "--init", "--read-only", "--network", "none", ref,
                         "bash", "-c", script]) for ref in [base["Id"], image["Id"]]]
    assert contents[0] == contents[1]
    assert meta.read_text().strip() == before_meta
    save("monai3205_image.json", {"base": base["Id"], "base_digest": base["RepoDigests"][0],
                                 "image_id": image["Id"], "tag": tag, "base_layers_preserved": True,
                                 "representative_contents": contents, "metacopy_unchanged": before_meta,
                                 "recipe_sha256": hashlib.sha256(recipe.read_bytes()).hexdigest()})
    for kind in ("noop", "gold"):
        dest = ROOT / "runs" / ("monai3205-assets-v1-" + kind)
        dest.mkdir(parents=True, exist_ok=False)
        command = [str(OLD / "code/rh2/.venv/bin/python"), str(OLD / "code/rh2/scripts/replay_grade.py"), "run",
                   "--prepared-summary", str(OLD / "replay/prepared/replay_summary.json"), "--task-ids", TASK,
                   "--candidate", "noop" if kind == "noop" else "gold-dir:" + str(OLD / "replay/gold"),
                   "--derived-image", image["Id"], "--derived-image-recipe", recipe.name,
                   "--eval-log-dir", str(dest / "eval_logs"), "--artifacts-dir", str(dest / "artifacts"),
                   "--ledger", str(dest / "ledger.jsonl")]
        env = dict(os.environ, MILES_RH2_RUN_ID="er19-r2-monai3205-" + kind)
        save("monai3205_current.json", {"at": time.time(), "kind": kind, "command": command})
        with (dest / "driver.log").open("w") as log:
            subprocess.run(command, cwd=OLD / "code/rh2", env=env, check=True, timeout=4800,
                           stdout=log, stderr=subprocess.STDOUT)
        row = json.loads((dest / "ledger.jsonl").read_text())
        assert row["cleanup"]["removed"]
        assert row["stage_error"] is None, row["stage_error"]
        print("GRADED", kind, json.dumps(row.get("report")), flush=True)
    save("monai3205_done.json", {"at": time.time(), "attempts": 2})


if __name__ == "__main__":
    try:
        run()
    except BaseException as exc:
        save("monai3205_failed.json", {"at": time.time(), "type": type(exc).__name__, "detail": str(exc)})
        raise
