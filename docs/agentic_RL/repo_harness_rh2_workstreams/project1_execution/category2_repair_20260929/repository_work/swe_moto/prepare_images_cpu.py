"""在 cpu_slot.py 的 prepare 锁内，按固定 digest 准备单题原镜像。"""

import argparse
import datetime
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--instance", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    task = next(x for x in plan["tasks"] if x["instance_id"] == args.instance)
    image = task["image"]
    if not image.startswith("xingyaoww/sweb.eval.x86_64.getmoto_s_moto-") or "@sha256:" not in image:
        raise ValueError("必须使用登记的 Moto 原镜像 digest")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise FileExistsError("本次镜像记录不得覆盖历史")
    record = {"instance_id": args.instance, "requested_image": image,
              "started_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "scope": "image_preparation_only", "formal_cpu_accepted": False}
    result = subprocess.run(["docker", "pull", "--platform", "linux/amd64", image])
    record["pull_returncode"] = result.returncode
    if result.returncode == 0:
        inspected = subprocess.check_output(["docker", "image", "inspect", image], text=True)
        actual = json.loads(inspected)[0]
        record.update(actual_image_id=actual["Id"], repo_digests=actual.get("RepoDigests", []),
                      architecture=actual["Architecture"], os=actual["Os"],
                      size_bytes=actual["Size"], layer_count=len(actual["RootFS"]["Layers"]))
        record["manifest_digest_matches"] = any(
            digest.endswith("@" + task["image_manifest_digest"]) for digest in record["repo_digests"])
        if not record["manifest_digest_matches"] or record["architecture"] != "amd64":
            record["identity_error"] = "原镜像 digest 或架构不符"
    record["finished_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    args.output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    return result.returncode or (1 if record.get("identity_error") else 0)


if __name__ == "__main__":
    raise SystemExit(main())
