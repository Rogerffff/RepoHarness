"""通用：按 09-19 离线安装配方的 Dockerfile 文本（COPY wheels + PIP_NO_INDEX/FIND_LINKS）重建派生镜像。

与 rebuild_install_wave1.py 相同的配方文本，但 wheel 固定版本由命令行给出（用于原清单未上传、只能等效重建的配方，
例如 pydantic_v1 的构建后端 wheel）。输出 <out>/image.json：base/derived 身份、层保留、wheel 名称/摘要/字节。
--kind compat 时改用 09-19 compat 配方文本（COPY wheels/ /opt/rh2/compat-wheels/，不设 ENV；见
rh2/experiments/env_recipe_repair_20260919/run_compat_cases.py），供 compat_v1/compat_v2b 这类“固定依赖版本”配方使用。
用法：python rebuild_wheel_layer.py --image IMG --image-id ID --python 3.8 --tag TAG --out DIR --pin pkg==ver [...] [--kind build|compat]
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

RECIPES = {
    "build": ('ARG BASE_IMAGE\nFROM ${BASE_IMAGE}\nCOPY wheels/ /opt/rh2/build-wheels/\n'
              'ENV PIP_NO_INDEX=1 PIP_FIND_LINKS=/opt/rh2/build-wheels\n'),
    "compat": 'ARG BASE_IMAGE\nFROM ${BASE_IMAGE}\nCOPY wheels/ /opt/rh2/compat-wheels/\n',
}
ap = argparse.ArgumentParser()
ap.add_argument("--kind", choices=sorted(RECIPES), default="build")
for a in ("--image", "--image-id", "--python", "--tag", "--out"):
    ap.add_argument(a, required=True)
ap.add_argument("--pin", action="append", required=True)
ns = ap.parse_args()
RECIPE = RECIPES[ns.kind]
out = Path(ns.out)
ctx = out / "context"
(ctx / "wheels").mkdir(parents=True, exist_ok=False)
cache = out / "wheel_cache"
cache.mkdir(parents=True, exist_ok=True)
manifest = []
for spec in ns.pin:
    pkg, version = spec.split("==")
    subprocess.run([sys.executable, "-m", "pip", "download", "--no-deps", "--only-binary=:all:", "--python-version", ns.python,
                    "--dest", str(cache), spec], check=True, capture_output=True, text=True)
    norm = pkg.replace("-", "_").lower()
    files = [f for f in cache.glob("*.whl") if f.name.lower().startswith(norm + "-" + version.lower() + "-")]
    assert len(files) == 1, (spec, [f.name for f in cache.glob("*.whl")])
    data = files[0].read_bytes()
    (ctx / "wheels" / files[0].name).write_bytes(data)
    manifest.append({"name": files[0].name, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
(ctx / "Dockerfile").write_text(RECIPE)
base = json.loads(subprocess.check_output(["docker", "image", "inspect", ns.image], text=True))[0]
assert base["Id"] == ns.image_id, (base["Id"], ns.image_id)
with (out / "build.log").open("w") as log:
    subprocess.run(["docker", "build", "--pull=false", "--force-rm", "--build-arg", "BASE_IMAGE=" + base["RepoDigests"][0],
                    "-t", ns.tag, str(ctx)], stdout=log, stderr=subprocess.STDOUT, timeout=900, check=True)
derived = json.loads(subprocess.check_output(["docker", "image", "inspect", ns.tag], text=True))[0]
assert derived["RootFS"]["Layers"][:-1] == base["RootFS"]["Layers"]
info = {"base_image": ns.image, "base_id": base["Id"], "base_digest": base["RepoDigests"][0], "derived_tag": ns.tag,
        "derived_id": derived["Id"], "recipe": RECIPE, "python": ns.python, "wheels": manifest,
        "base_layers_preserved": True, "derived_layers": len(derived["RootFS"]["Layers"])}
(out / "image.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(info, ensure_ascii=False))
