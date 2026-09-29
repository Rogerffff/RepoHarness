#!/usr/bin/env python3
"""基座探针：在新机器上按 09-19 环境维修的原配方重建 COPY-only 派生镜像（旧实例已删除，镜像需重建）。

配方形状与原批一致（`runs/env_recipe_repair_20260919/<batch>/tasks/<iid>/image.json` 的 recipe 字段）：
  dvc_install_v1c：COPY wheels/ /opt/rh2/build-wheels/ + ENV PIP_NO_INDEX=1 PIP_FIND_LINKS=/opt/rh2/build-wheels
  sqs_v1        ：COPY wheels/ /opt/rh2/compat-wheels/
wheel 用**题目镜像自己的 testbed 解释器**下载（ABI / Python 版本随镜像），`--no-deps --only-binary=:all:`；
有历史 assets 清单时逐个核 sha256。新镜像 ID 与历史 ID 不同是预期的（层时间戳），因此本次要重新做 noop/gold 对照，
历史资格账本不能冒充新镜像的资格。

plan.json：[{"instance_id","image","pins":[…],"style":"dvc_install_v1c|sqs_v1","expected_wheels":{name:sha256}?}]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

STYLES = {
    "dvc_install_v1c": ("/opt/rh2/build-wheels/", "ENV PIP_NO_INDEX=1 PIP_FIND_LINKS=/opt/rh2/build-wheels\n"),
    "sqs_v1": ("/opt/rh2/compat-wheels/", ""),
    "install_wave1": ("/opt/rh2/build-wheels/", "ENV PIP_NO_INDEX=1 PIP_FIND_LINKS=/opt/rh2/build-wheels\n"),
    "compat_v1": ("/opt/rh2/compat-wheels/", ""),
}


def sh(cmd: list[str], *, log, timeout: int) -> None:
    log.write(("$ " + " ".join(cmd) + "\n").encode())
    log.flush()
    subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=timeout)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--tag-suffix", default="20260922")
    ns = ap.parse_args(argv)
    out = Path(ns.out_dir).resolve()
    results = {}
    for item in json.loads(Path(ns.plan).read_text(encoding="utf-8")):
        iid, image, pins, style = item["instance_id"], item["image"], list(item["pins"]), item["style"]
        dest, env_line = STYLES[style]
        tdir = out / iid
        wheels = tdir / "context" / "wheels"
        wheels.mkdir(parents=True, exist_ok=True)
        with open(tdir / "build.log", "ab") as log:
            sh(["docker", "pull", image], log=log, timeout=3600)
            base = json.loads(subprocess.check_output(["docker", "image", "inspect", image], text=True))[0]
            sh(["docker", "run", "--rm", "--init", "--memory", "2g", "--cpus", "2", "-v", f"{wheels}:/cache", image,
                "/opt/miniconda3/envs/testbed/bin/python", "-I", "-m", "pip", "download", "--index-url", "https://pypi.org/simple",
                "--no-deps", "--only-binary=:all:", "-d", "/cache", *pins], log=log, timeout=1200)
            got = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(wheels.glob("*.whl"))}
            expected = item.get("expected_wheels") or {}
            mismatch = {n: (expected[n], got.get(n)) for n in expected if got.get(n) != expected[n]}
            recipe = f"ARG BASE_IMAGE\nFROM ${{BASE_IMAGE}}\nCOPY wheels/ {dest}\n{env_line}"
            (tdir / "context" / "Dockerfile").write_text(recipe, encoding="utf-8")
            tag = f"rh2-baseprobe/{style.replace('_', '-')}-{iid.lower()}:{ns.tag_suffix}"
            sh(["docker", "build", "--pull=false", "--build-arg", f"BASE_IMAGE={base['RepoDigests'][0]}", "-t", tag,
                str(tdir / "context")], log=log, timeout=1200)
            built = json.loads(subprocess.check_output(["docker", "image", "inspect", tag], text=True))[0]
            preserved = built["RootFS"]["Layers"][: len(base["RootFS"]["Layers"])] == base["RootFS"]["Layers"]
        results[iid] = {
            "style": style, "base_image": image, "base_id": base["Id"], "base_repo_digests": base.get("RepoDigests"),
            "historical_base_id": item.get("historical_base_id"), "base_id_matches_history": item.get("historical_base_id") in (None, base["Id"]),
            "tag": tag, "image_id": built["Id"], "recipe": recipe, "base_layers_preserved": preserved,
            "wheels": got, "expected_wheel_mismatch": mismatch, "pins": pins,
        }
        (tdir / "image.json").write_text(json.dumps(results[iid], ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps({iid: {k: results[iid][k] for k in ("image_id", "base_layers_preserved", "base_id_matches_history", "expected_wheel_mismatch")}}, ensure_ascii=False), flush=True)
    bad = [i for i, r in results.items() if not r["base_layers_preserved"] or r["expected_wheel_mismatch"]]
    (out / "derived_images.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
