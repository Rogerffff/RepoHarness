#!/usr/bin/env python3
"""在 cpu_slot prepare 名额内拉取固定摘要源镜像；不执行测试或评分。"""

import argparse
import json
from pathlib import Path
import re
import subprocess
import time


def inspect(reference):
    result = subprocess.run(
        ["docker", "image", "inspect", reference],
        text=True, capture_output=True, timeout=60,
    )
    if result.returncode:
        return None
    return json.loads(result.stdout)[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    task = json.loads(args.manifest.read_text())
    digest = task["source_image_manifest_digest"]
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", digest):
        parser.error("需要已记录的完整源镜像摘要")
    repository = task["source_image"].rsplit(":", 1)[0]
    reference = repository + "@" + digest
    record = {
        "schema": "coveragepy.source_image_preparation.v1",
        "instance_id": task["instance_id"],
        "source_reference": reference,
        "source_base_commit": task["source_base_commit"],
        "started_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "preparing",
        "formal_acceptance": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)

    def save():
        temporary = args.output.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(record, indent=2) + "\n")
        temporary.replace(args.output)

    save()
    try:
        image = inspect(reference)
        record["already_present"] = image is not None
        if image is None:
            print("拉取固定摘要源镜像：" + reference, flush=True)
            subprocess.run(["docker", "pull", reference], check=True, timeout=3600)
            image = inspect(reference)
        if image is None or reference not in image.get("RepoDigests", []):
            raise RuntimeError("源镜像 RepoDigests 未能核对到指定摘要")
        if image.get("Architecture") != "amd64" or image.get("Os") != "linux":
            raise RuntimeError("源镜像平台不是 linux/amd64")
        record.update(
            status="source_image_ready",
            image_id=image["Id"],
            repository_digests=image["RepoDigests"],
            architecture=image["Architecture"],
            os=image["Os"],
            size_bytes=image["Size"],
            rootfs_diff_ids=image["RootFS"]["Layers"],
        )
        print(json.dumps({k: record[k] for k in ("instance_id", "status", "image_id", "size_bytes")}), flush=True)
    except Exception as exc:
        record.update(status="source_image_preparation_failed", error=str(exc))
        raise
    finally:
        record["finished_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        save()


if __name__ == "__main__":
    main()
