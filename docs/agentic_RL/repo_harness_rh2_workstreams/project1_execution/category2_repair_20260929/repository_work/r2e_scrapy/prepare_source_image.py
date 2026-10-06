"""在 cpu_slot prepare 锁内拉取并核对本题来源镜像，不构建派生材料。"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

SOURCE = "namanjain12/scrapy_final:a95a338eeada7275a5289cf036136610ebaf07eb@sha256:cd01a127a7c83ad8e59e0380f34dbf20e7469fe0ae4ebb051c83993dbc4d067d"
OUTPUT = Path(__file__).resolve().parent / "source_image.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--relay-image", default=None, help="固定发布版profile的digest引用，供公开actor桩使用")
    args = parser.parse_args()
    if args.relay_image:
        assert re.fullmatch(r"[a-z0-9._/:\-]+@sha256:[0-9a-f]{64}", args.relay_image), "relay必须固定digest"
    assert not OUTPUT.exists(), "使用新的作业输入目录，不能覆盖历史镜像准备记录"
    started = datetime.now(timezone.utc).isoformat()
    subprocess.run(["docker", "pull", SOURCE], check=True, timeout=3600)
    result = subprocess.run(["docker", "image", "inspect", SOURCE], check=True, capture_output=True, text=True, timeout=60)
    image = json.loads(result.stdout)[0]
    expected = SOURCE.split("@", 1)[1]
    assert any(ref.endswith("@" + expected) for ref in image.get("RepoDigests", [])), "来源 digest 不符"
    assert image["Os"] == "linux" and image["Architecture"] == "amd64", "来源平台不符"
    record = {"scope": "source_image_preparation_only", "source_image_ref": SOURCE,
              "image_id_actual": image["Id"], "manifest_digest_expected": expected,
              "repo_digests": image["RepoDigests"], "size_bytes": image["Size"],
              "os": image["Os"], "architecture": image["Architecture"],
              "started_at_utc": started, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
              "formal_acceptance": "not_run", "derived_material_image": False}
    if args.relay_image:
        subprocess.run(["docker", "pull", args.relay_image], check=True, timeout=1800)
        relay_result = subprocess.run(["docker", "image", "inspect", args.relay_image], check=True,
                                      capture_output=True, text=True, timeout=60)
        relay = json.loads(relay_result.stdout)[0]
        assert any(ref.endswith("@" + args.relay_image.split("@", 1)[1]) for ref in relay.get("RepoDigests", []))
        assert relay["Os"] == "linux" and relay["Architecture"] == "amd64"
        record["relay_image"] = {"ref": args.relay_image, "image_id_actual": relay["Id"],
                                 "repo_digests": relay["RepoDigests"], "size_bytes": relay["Size"]}
        record["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    OUTPUT.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"source_digest_verified": True, "scope": record["scope"], "size_bytes": image["Size"]}))


if __name__ == "__main__":
    main()
