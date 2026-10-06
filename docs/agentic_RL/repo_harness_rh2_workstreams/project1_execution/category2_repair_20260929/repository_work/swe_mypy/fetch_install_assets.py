"""恢复两题历史 wheel 字节；不安装、不执行包、不下载项目或容器镜像。"""

from __future__ import annotations

import hashlib
import io
import json
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from email.parser import Parser
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "rh2/src/repoharness2").is_dir())
OLD = ROOT / "runs/env_recipe_repair_20260919/install_wave1"
OUT = ROOT / "runs/category2_repair_20260929/repository_work/swe_mypy/install_assets_20261003"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(row: dict) -> dict:
    package, version = Path(row["path"]).parent.name.split("==")
    filename = Path(row["path"]).name
    destination = OUT / "wheels" / filename
    url = "https://pypi.org/pypi/" + urllib.parse.quote(package) + "/" + version + "/json"
    with urllib.request.urlopen(url, timeout=30) as response:
        metadata = json.load(response)
    matched = [f for f in metadata["urls"] if f["filename"] == filename
               and f["digests"]["sha256"] == row["sha256"] and f["size"] == row["bytes"]]
    assert len(matched) == 1, filename
    download_url = matched[0]["url"]
    assert urllib.parse.urlsplit(download_url).hostname == "files.pythonhosted.org"
    if destination.exists():
        data = destination.read_bytes()
    else:
        with urllib.request.urlopen(download_url, timeout=30) as response:
            data = response.read(row["bytes"] + 1)
    assert len(data) == row["bytes"] and sha256(data) == row["sha256"], filename
    with zipfile.ZipFile(io.BytesIO(data)) as wheel:
        # setuptools 带 vendored 依赖元数据；这里只核 wheel 顶层发行包。
        members = [name for name in wheel.namelist()
                   if name.endswith(".dist-info/METADATA") and name.count("/") == 1]
        assert len(members) == 1, filename
        info = Parser().parsestr(wheel.read(members[0]).decode())
        assert info["Version"] == version
        assert info["Name"].lower().replace("_", "-") == package.lower().replace("_", "-")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    return {"distribution": package, "version": version,
            "path": str(destination.relative_to(ROOT)), "sha256": "sha256:" + row["sha256"],
            "bytes": len(data), "source_url": download_url,
            "matches_historical_asset_manifest": True}


def main() -> None:
    tasks = ("python__mypy-10174", "python__mypy-15184")
    pins = {}
    for iid in tasks:
        pins[iid] = json.loads((OLD / "tasks" / iid / "image.json").read_text())["pins"]
    wanted = {package + "==" + version for task_pins in pins.values()
              for package, version in task_pins.items()}
    manifest_path = OLD / "assets_manifest.json"
    historical = json.loads(manifest_path.read_text())
    rows = [row for row in historical if Path(row["path"]).parent.name in wanted]
    assert len(rows) == len(wanted)
    with ThreadPoolExecutor(max_workers=3) as pool:
        verified = list(pool.map(fetch, rows))
    manifest = {"as_of": "2026-10-03", "status": "payload_verified_not_installed",
                "historical_asset_manifest": str(manifest_path.relative_to(ROOT)),
                "historical_asset_manifest_sha256": "sha256:" + sha256(manifest_path.read_bytes()),
                "task_pins": pins, "assets": verified,
                "total_bytes": sum(row["bytes"] for row in verified),
                "scope": "wheel字节/SHA/元数据验证；不是全依赖锁、镜像恢复或安装验收"}
    (HERE / "install_assets_20261003.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"verified_wheels": len(verified), "bytes": manifest["total_bytes"],
                      "installed": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
