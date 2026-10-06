"""在统一 prepare 槽内导出两个固定镜像，不改 tag 或镜像配置。"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import time
from pathlib import Path


IMAGES = {
    "actor": "sha256:fdd298b61309ae2df4cb9f528351526b7b3817c42fc34f47f98152a92a520881",
    "grader": "sha256:625b404c6c1c40da31df4edfea6052a10fbd30b7fb49d58072b6ee2b215fab13",
}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    base = Path("/work/rh2-category2-20261003/packages/swe_dask/image_exports")
    assert args.out.parent.parent == base and args.out.name == "export" and not args.out.is_symlink()
    args.out.mkdir(parents=True, exist_ok=False)
    status = {"state": "inspect", "started_at": time.time(), "images": IMAGES}

    def save() -> None:
        temp = args.out / "status.json.tmp"
        temp.write_text(json.dumps(status, indent=2) + "\n")
        temp.replace(args.out / "status.json")

    save()
    try:
        inspections = {}
        for role, image in IMAGES.items():
            result = subprocess.run(["docker", "image", "inspect", image], check=True, capture_output=True, timeout=60)
            rows = json.loads(result.stdout)
            assert len(rows) == 1 and rows[0]["Id"] == image
            inspections[role] = rows[0]
            (args.out / f"{role}.inspect.json").write_bytes(result.stdout)
        required = sum(item["Size"] for item in inspections.values()) + 2 * 1024**3
        free = shutil.disk_usage(args.out).free
        assert free >= required, f"insufficient export disk: {free} < {required}"
        status.update(state="saving", disk_free_before=free, conservative_bytes_required=required)
        save()
        temp = args.out / "dask7138-fixed-images.tar.gz.partial"
        with (args.out / "docker_save.stderr").open("wb") as stderr:
            child = subprocess.Popen(["docker", "image", "save", *IMAGES.values()], stdout=subprocess.PIPE, stderr=stderr)
            try:
                assert child.stdout is not None
                with temp.open("xb") as raw:
                    with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=1, mtime=0) as target:
                        shutil.copyfileobj(child.stdout, target, length=8 * 1024 * 1024)
                child.stdout.close()
                assert child.wait(timeout=60) == 0, "docker save failed; see docker_save.stderr"
            except BaseException:
                child.terminate()
                try:
                    child.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
                raise
        status.update(state="verifying_archive", archive_bytes=temp.stat().st_size)
        save()
        with tarfile.open(temp, "r:gz") as tar:
            stream = tar.extractfile("manifest.json")
            assert stream is not None
            manifest = json.load(stream)
            actual_ids = set()
            for item in manifest:
                stream = tar.extractfile(item["Config"])
                assert stream is not None
                actual_ids.add("sha256:" + hashlib.sha256(stream.read()).hexdigest())
            assert actual_ids == set(IMAGES.values()), (actual_ids, IMAGES)
        archive_sha = digest(temp)
        target = args.out / "dask7138-fixed-images.tar.gz"
        assert not target.exists()
        os.replace(temp, target)
        target.chmod(0o444)
        for image in IMAGES.values():
            result = subprocess.run(["docker", "image", "inspect", "--format", "{{.Id}}", image], check=True, capture_output=True, text=True, timeout=60)
            assert result.stdout.strip() == image
        status.update(state="complete", finished_at=time.time(), archive_path=str(target), archive_sha256=archive_sha,
                      archive_bytes=target.stat().st_size, manifest_config_ids=sorted(actual_ids),
                      archive_manifest=manifest, worker_sha256=digest(Path(__file__)))
        save()
        print(json.dumps(status))
    except BaseException as error:
        status.update(state="failed_export_not_task_result", finished_at=time.time(), error_type=type(error).__name__, error=str(error))
        save()
        raise


if __name__ == "__main__":
    main()
