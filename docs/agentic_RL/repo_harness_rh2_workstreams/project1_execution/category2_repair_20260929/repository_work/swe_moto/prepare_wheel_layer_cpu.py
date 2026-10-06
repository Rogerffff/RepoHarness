"""在全局 prepare 槽内，以核定的原配方和离线 wheel 构建单题镜像。"""

import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect(image):
    return json.loads(subprocess.check_output(
        ["docker", "image", "inspect", image], text=True))[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--instance", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    plan = json.loads(args.plan.read_text())
    task = next(t for t in plan["tasks"] if t["instance_id"] == args.instance)
    if not args.tag.startswith("rh2-swe-moto-20261003/"):
        raise ValueError("必须使用本工作包的独立 tag")
    actual_files = {p.relative_to(args.context).as_posix():
                    {"sha256": sha(p), "bytes": p.stat().st_size}
                    for p in args.context.rglob("*") if p.is_file()}
    if actual_files != plan["files"] or any(p.is_symlink() for p in args.context.rglob("*")):
        raise ValueError("构建上下文与固定 SHA／长度清单不符")
    recipe = ("ARG BASE_IMAGE\nFROM ${BASE_IMAGE}\n"
              "COPY wheels/ /opt/rh2/build-wheels/\n"
              "ENV PIP_NO_INDEX=1 PIP_FIND_LINKS=/opt/rh2/build-wheels\n")
    if (args.context / "Dockerfile").read_bytes() != recipe.encode():
        raise ValueError("必须保持历史 COPY-only 配方原字节")
    base = inspect(task["image"])
    if task["image"] not in base.get("RepoDigests", []) or (
            base["Architecture"], base["Os"]) != ("amd64", "linux"):
        raise ValueError("固定原镜像 digest／平台不符，先单独准备原镜像")
    (args.output / "base_inspect.json").write_text(json.dumps(base, indent=2) + "\n")
    try:
        inspect(args.tag)
    except subprocess.CalledProcessError:
        pass
    else:
        raise FileExistsError("本次 tag 已存在，不覆盖历史镜像")
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with (args.output / "build.log").open("w") as log:
        result = subprocess.run(
            ["docker", "build", "--pull=false", "--network=none", "--force-rm",
             "--build-arg", "BASE_IMAGE=" + task["image"],
             "-t", args.tag, str(args.context)], stdout=log, stderr=subprocess.STDOUT,
            timeout=900)
    record = {"instance_id": args.instance, "scope": "image_preparation_only",
              "formal_cpu_accepted": False, "started_at_utc": started,
              "returncode": result.returncode, "base_digest": task["image"],
              "base_id": base["Id"], "derived_tag": args.tag,
              "dockerfile_sha256": sha(args.context / "Dockerfile"),
              "wheel_manifest_sha256": sha(args.context / "wheel_manifest.json"),
              "wheels": plan["wheels"], "original_vendor_install": "make init"}
    if result.returncode == 0:
        derived = inspect(args.tag)
        (args.output / "derived_inspect.json").write_text(json.dumps(derived, indent=2) + "\n")
        record.update(derived_id=derived["Id"],
                      base_layers_preserved=(derived["RootFS"]["Layers"][:-1] ==
                                             base["RootFS"]["Layers"]),
                      offline_env_present={"PIP_NO_INDEX=1", "PIP_FIND_LINKS=/opt/rh2/build-wheels"}.issubset(
                          set(derived["Config"].get("Env", []))))
        if not record["base_layers_preserved"] or not record["offline_env_present"]:
            record["identity_error"] = "继承层或离线 ENV 不符"
    record["finished_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    (args.output / "image.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(record, ensure_ascii=False))
    return result.returncode or (1 if record.get("identity_error") else 0)


if __name__ == "__main__":
    raise SystemExit(main())
