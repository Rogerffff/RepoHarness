"""受cpu_slot包装的单题镜像准备；不评分，不启动长期容器。"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--instance-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads((args.input_root / "image_plan.json").read_text())[args.instance_id]
    args.output.mkdir(parents=True, exist_ok=False)
    state = {"instance_id": args.instance_id, "state": "preparing",
             "scope": "镜像准备，不是安装/actor/grader或题级验收",
             "started_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

    def save() -> None:
        temp = args.output / "image_prepare.json.tmp"
        temp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
        temp.replace(args.output / "image_prepare.json")

    def command(label: str, argv: list[str], timeout: int) -> None:
        state["stage"] = label
        save()
        with (args.output / (label + ".log")).open("wb") as out:
            proc = subprocess.run(argv, stdout=out, stderr=subprocess.STDOUT, timeout=timeout)
        state[label + "_returncode"] = proc.returncode
        save()
        if proc.returncode:
            raise RuntimeError(f"{label} failed: {proc.returncode}")

    def inspect(image: str) -> dict:
        result = subprocess.run(["docker", "image", "inspect", image],
                                check=True, text=True, capture_output=True, timeout=60)
        return json.loads(result.stdout)[0]

    try:
        for wheel in plan["wheels"]:
            path = args.input_root / plan["context"] / "wheels" / wheel["filename"]
            data = path.read_bytes()
            assert hashlib.sha256(data).hexdigest() == wheel["sha256"]
            assert len(data) == wheel["bytes"]
        command("pull", ["docker", "pull", plan["base_digest"]], 3600)
        base = inspect(plan["base_digest"])
        (args.output / "base_image.json").write_text(json.dumps(base, indent=2) + "\n")
        assert base["Id"] == plan["expected_base_image_id"]
        assert base["Architecture"] == "amd64"
        assert plan["base_digest"] in base["RepoDigests"]
        command("build", ["docker", "build", "--pull=false", "--force-rm",
                          "--build-arg", "BASE_IMAGE=" + plan["base_digest"],
                          "-t", plan["tag"], str(args.input_root / plan["context"])], 900)
        derived = inspect(plan["tag"])
        (args.output / "derived_image.json").write_text(json.dumps(derived, indent=2) + "\n")
        assert derived["RootFS"]["Layers"][:-1] == base["RootFS"]["Layers"]
        assert derived["Config"]["WorkingDir"] == base["Config"]["WorkingDir"]
        assert derived["Config"]["User"] == base["Config"]["User"]
        assert "PIP_NO_INDEX=1" in derived["Config"]["Env"]
        assert "PIP_FIND_LINKS=/opt/rh2/build-wheels" in derived["Config"]["Env"]
        state.update(state="image_prepared", base_image_id=base["Id"],
                     base_digest=plan["base_digest"], image_id=derived["Id"], tag=plan["tag"],
                     base_layers_preserved=True, recipe_sha256=plan["recipe_sha256"],
                     wheel_count=len(plan["wheels"]), finished_at_utc=time.strftime(
                         "%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        save()
    except BaseException as exc:
        state.update(state="failed", error=str(exc),
                     finished_at_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        save()
        raise


if __name__ == "__main__":
    main()
