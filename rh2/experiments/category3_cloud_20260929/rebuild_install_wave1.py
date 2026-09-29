"""在云端按 09-19 install_wave1 原配方重建离线安装派生镜像（仅 COPY 固定版本 wheel + PIP_NO_INDEX/FIND_LINKS）。

配方文本与 run_install_wave1.py 逐字相同；wheel 从 PyPI 下载，若给出 --expect（name=sha256）则逐个核对。
输出 <out>/<instance_id>/image.json：base/derived 身份、层保留检查、wheel 清单。不评分。
用法：python rebuild_install_wave1.py --instance-id ID --out DIR [--expect name=sha ...]
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
RECIPE = ('ARG BASE_IMAGE\nFROM ${BASE_IMAGE}\nCOPY wheels/ /opt/rh2/build-wheels/\n'
          'ENV PIP_NO_INDEX=1 PIP_FIND_LINKS=/opt/rh2/build-wheels\n')

ap = argparse.ArgumentParser()
ap.add_argument("--instance-id", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--expect", action="append", default=[])
ns = ap.parse_args()
plans = json.loads((REPO / "docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_recipe_repair_20260919/installation_wave1.json").read_text())
plan = next(p for p in plans if p["instance_id"] == ns.instance_id)
expect = dict(x.split("=", 1) for x in ns.expect)
dest = Path(ns.out) / ns.instance_id
ctx = dest / "context"
(ctx / "wheels").mkdir(parents=True, exist_ok=False)
cache = Path(ns.out) / "wheel_cache"
cache.mkdir(parents=True, exist_ok=True)
manifest = []
for pkg, version in plan["pins"].items():
    spec = f"{pkg}=={version}"
    subprocess.run([sys.executable, "-m", "pip", "download", "--no-deps", "--only-binary=:all:", "--python-version", plan["python"],
                    "--dest", str(cache), spec], check=True, capture_output=True, text=True)
    norm = pkg.replace("-", "_").lower()
    files = [f for f in cache.glob("*.whl") if f.name.lower().startswith(norm + "-" + version.lower() + "-")]
    assert len(files) == 1, (spec, [f.name for f in cache.glob("*.whl")])
    data = files[0].read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    if files[0].name in expect:
        assert expect[files[0].name] == sha, (files[0].name, sha)
    (ctx / "wheels" / files[0].name).write_bytes(data)
    manifest.append({"name": files[0].name, "sha256": sha, "bytes": len(data),
                     "expected_match": (expect.get(files[0].name) == sha) if files[0].name in expect else None})
(ctx / "Dockerfile").write_text(RECIPE)
base = json.loads(subprocess.check_output(["docker", "image", "inspect", plan["image"]], text=True))[0]
assert base["Id"] == plan["image_id"], (base["Id"], plan["image_id"])
tag = "rh2-envrepair/install-wave1-" + ns.instance_id.lower() + ":c3cloud"
with (dest / "build.log").open("w") as log:
    subprocess.run(["docker", "build", "--pull=false", "--force-rm", "--build-arg", "BASE_IMAGE=" + base["RepoDigests"][0],
                    "-t", tag, str(ctx)], stdout=log, stderr=subprocess.STDOUT, timeout=900, check=True)
derived = json.loads(subprocess.check_output(["docker", "image", "inspect", tag], text=True))[0]
assert derived["RootFS"]["Layers"][:-1] == base["RootFS"]["Layers"]
info = {"instance_id": ns.instance_id, "base_image": plan["image"], "base_id": base["Id"], "base_digest": base["RepoDigests"][0],
        "derived_tag": tag, "derived_id": derived["Id"], "recipe": RECIPE, "pins": plan["pins"], "wheels": manifest,
        "base_layers_preserved": True, "derived_layers": len(derived["RootFS"]["Layers"])}
(dest / "image.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(info, ensure_ascii=False))
