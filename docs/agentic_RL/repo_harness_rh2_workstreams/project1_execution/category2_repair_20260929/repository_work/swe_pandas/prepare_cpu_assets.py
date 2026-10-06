"""仅在 cpu_slot.py 的 prepare 槽内执行：固定镜像及已验 E19 离线 wheel。"""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import urllib.request


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def download_wheels(manifest, destination):
    destination.mkdir(parents=True, exist_ok=True)
    for expected in manifest:
        path = destination / expected["name"]
        if path.exists() and digest(path) == expected["sha256"]:
            continue
        distribution, version = expected["name"].split("-")[:2]
        request = urllib.request.Request(
            "https://pypi.org/pypi/" + distribution + "/" + version + "/json",
            headers={"User-Agent": "RH2-Pandas-asset-restoration"},
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            metadata = json.load(response)
        candidates = [item for item in metadata["urls"]
                      if item["filename"].lower() == expected["name"].lower()
                      and item["digests"]["sha256"] == expected["sha256"]]
        if len(candidates) != 1:
            raise RuntimeError("没有唯一匹配已验摘要的 wheel: " + expected["name"])
        temporary = path.with_suffix(path.suffix + ".partial")
        with urllib.request.urlopen(candidates[0]["url"], timeout=120) as response:
            temporary.write_bytes(response.read())
        if temporary.stat().st_size != expected["bytes"] or digest(temporary) != expected["sha256"]:
            raise RuntimeError("wheel 长度/摘要不符: " + expected["name"])
        temporary.replace(path)
        print("wheel verified:", expected["name"], flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--instance-id", required=True)
    parser.add_argument("--wheel-source", help="可选的预恢复 wheel 目录；仍须逐文件核历史长度和SHA")
    args = parser.parse_args()
    source = json.loads(Path(args.input).read_text())
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=False)
    (out / "input.json").write_text(json.dumps(source, ensure_ascii=False, indent=2) + "\n")
    selected = [image for image in source["images"] if image["instance_id"] == args.instance_id]
    if len(selected) != 1:
        raise RuntimeError("输入中必须有唯一的指定题目镜像")
    images = []
    for image in selected:
        print("pulling fixed image:", image["instance_id"], flush=True)
        subprocess.run(["timeout", "--signal=TERM", "--kill-after=30s", "2400",
                        "docker", "pull", image["pull_ref"]], check=True)
        values = json.loads(subprocess.check_output(["docker", "image", "inspect", image["pull_ref"]]))
        value = values[0]
        if image["pull_ref"] not in value.get("RepoDigests", []):
            raise RuntimeError("实际 RepoDigests 不含登记摘要: " + image["instance_id"])
        if value.get("Architecture") != "amd64" or value.get("Os") != "linux":
            raise RuntimeError("镜像平台不符: " + image["instance_id"])
        images.append({**image, "actual_image_id": value["Id"],
                       "repo_digests": value["RepoDigests"], "size_bytes": value["Size"],
                       "architecture": value["Architecture"], "os": value["Os"]})
        (out / "images.json").write_text(json.dumps(images, ensure_ascii=False, indent=2) + "\n")
    wheels = source["pandas48106_wheels"] if args.instance_id == "pandas-dev__pandas-48106" else []
    if wheels and args.wheel_source:
        supplied = Path(args.wheel_source)
        (out / "compat-wheels").mkdir()
        for expected in wheels:
            path = supplied / expected["name"]
            if path.stat().st_size != expected["bytes"] or digest(path) != expected["sha256"]:
                raise RuntimeError("预恢复 wheel 长度/摘要不符: " + expected["name"])
            shutil.copy2(path, out / "compat-wheels" / expected["name"])
    if wheels:
        download_wheels(wheels, out / "compat-wheels")
    for expected in wheels:
        assert digest(out / "compat-wheels" / expected["name"]) == expected["sha256"]
    derived = None
    if wheels:
        context = out / "grader_build_context"
        context.mkdir()
        shutil.copytree(out / "compat-wheels", context / "compat-wheels")
        dockerfile = "FROM " + selected[0]["pull_ref"] + "\nCOPY compat-wheels/ /opt/rh2/compat-wheels/\n"
        (context / "Dockerfile").write_text(dockerfile)
        # output 的末级目录是唯一 job ID；父目录 outputs 会让不同作业互相覆盖标签。
        tag = "rh2/category2-pandas48106-meta-v3:" + out.name
        subprocess.run(["docker", "build", "--pull=false", "--network=none", "-t", tag, str(context)], check=True)
        built = json.loads(subprocess.check_output(["docker", "image", "inspect", tag]))[0]
        parent = json.loads(subprocess.check_output(["docker", "image", "inspect", selected[0]["pull_ref"]]))[0]
        assert built["RootFS"]["Layers"][:len(parent["RootFS"]["Layers"])] == parent["RootFS"]["Layers"]
        derived = {"tag": tag, "actual_image_id": built["Id"], "base_image_id": parent["Id"],
                   "base_layers_preserved": True, "dockerfile_sha256": "sha256:" + digest(context / "Dockerfile"),
                   "scope": "grader COPY-only 离线资产层；没有安装包、源码/测试修改或 actor 资格"}
    (out / "assets.json").write_text(json.dumps({
        "status": "fixed_images_and_wheels_prepared", "images": images,
        "pandas48106_wheels": wheels,
        "wheel_origin": "sha_verified_preloaded_copy" if wheels and args.wheel_source else
                        "pypi_exact_historical_sha" if wheels else "not_required",
        "grader_derived_image": derived,
        "scope": "镜像/安装资产准备；未安装候选、运行测试或进行正式评分",
    }, ensure_ascii=False, indent=2) + "\n")
    print("Pandas fixed image prepared; verified wheels:", len(wheels), flush=True)


if __name__ == "__main__":
    main()
