"""任务二：actor 侧派生镜像（公开开发依赖装进解题解释器；不带 gold / 隐藏测试 / 评分脚本）。

与 base_probe_20260922/build_derived.py 的 grader 派生不同：grader 派生只 COPY wheel、在评分安装段才装；
actor 派生必须在镜像里**装好**，解题 shell 一启动就是修订后的版本。流程：
  1. 用题目镜像自己的解释器下载 wheel（`--no-deps --only-binary=:all:`，ABI 随镜像），逐个记 sha256，
     与 `expected_wheels` 比对（给了就必须一致）；
  2. Dockerfile：FROM base → COPY wheels → 解释器 `pip install --no-index --no-deps` → 删 wheel；
  3. 记录：base / 派生 image ID、基础层是否保留、装前装后 `pip freeze` 差异、`pip check`、/testbed HEAD 与 porcelain。

plan.json：[{"name": "actor_dask8597_v1", "instance_id": "...", "image": "...", "python": "/opt/miniconda3/envs/testbed/bin/python",
             "pins": ["pytest==7.4.4"], "expected_wheels": {"pytest-7.4.4-py3-none-any.whl": "b090…"}, "basis": "…",
             "files": [{"url": "https://…/x.tar.gz", "sha256": "…", "name": "x.tar.gz"}],   # 可选：宿主下载并核 sha256，COPY 到 /opt/rh2/actor-files/
             "run": ["tar -C /usr/share -xzf /opt/rh2/actor-files/x.tar.gz"]}]              # 可选：root 构建步骤（只做公开工具链 / 入口）
用法：build_actor.py plan.json --out-dir /work/task2/derived
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path


def run(cmd: list[str], log, timeout: int = 1800) -> str:
    log.write(f"$ {' '.join(cmd)}\n")
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    log.write(p.stdout[-20000:] + p.stderr[-20000:] + f"[rc={p.returncode}]\n")
    log.flush()
    if p.returncode != 0:
        raise SystemExit(f"failed: {' '.join(cmd)}\n{p.stderr[-2000:]}")
    return p.stdout


def in_image(image: str, script: str, log) -> str:
    return run(["docker", "run", "--rm", "--entrypoint", "bash", image, "-c", script], log, timeout=600)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--out-dir", required=True)
    ns = ap.parse_args()
    out_root = Path(ns.out_dir)
    for item in json.loads(Path(ns.plan).read_text(encoding="utf-8")):
        name, image, py, pins = item["name"], item["image"], item["python"], list(item["pins"])
        od = out_root / name
        od.mkdir(parents=True, exist_ok=True)
        with open(od / "build.log", "w", encoding="utf-8") as log:
            base_id = run(["docker", "image", "inspect", image, "--format", "{{.Id}}"], log).strip()
            freeze_before = in_image(image, f"{py} -m pip freeze --all 2>/dev/null | sort", log)
            with tempfile.TemporaryDirectory() as td:
                wd = Path(td) / "wheels"
                wd.mkdir()
                if pins:
                    run(["docker", "run", "--rm", "-v", f"{wd}:/wheels", "--entrypoint", py, image, "-m", "pip", "download", "--no-deps",
                         "--only-binary=:all:", "-d", "/wheels", *pins], log)
                wheels = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(wd.iterdir())}
                fd = Path(td) / "files"
                fd.mkdir()
                files = {}
                for f in item.get("files") or []:
                    run(["curl", "-fsSL", "-o", str(fd / f["name"]), f["url"]], log, timeout=1800)
                    got = hashlib.sha256((fd / f["name"]).read_bytes()).hexdigest()
                    if got != f["sha256"]:
                        raise SystemExit(f"{name}: file sha256 mismatch {f['name']} {got}")
                    files[f["name"]] = got
                exp = item.get("expected_wheels") or {}
                mismatch = {k: (v, wheels.get(k)) for k, v in exp.items() if wheels.get(k) != v}
                if mismatch:
                    raise SystemExit(f"{name}: wheel sha256 mismatch {mismatch}")
                df = "ARG BASE_IMAGE\nFROM ${BASE_IMAGE}\n"
                if wheels:
                    df += ("COPY wheels/ /opt/rh2/actor-wheels/\n"
                           f"RUN {py} -m pip install --no-index --no-deps /opt/rh2/actor-wheels/*.whl && rm -rf /opt/rh2/actor-wheels\n")
                if files:
                    df += "COPY files/ /opt/rh2/actor-files/\n"
                for line in item.get("run") or []:
                    df += f"RUN {line}\n"
                if files:
                    df += "RUN rm -rf /opt/rh2/actor-files\n"
                (Path(td) / "Dockerfile").write_text(df, encoding="utf-8")
                (od / "Dockerfile").write_text(df, encoding="utf-8")
                tag = f"rh2-task2/{name}:20260925"
                run(["docker", "build", "--build-arg", f"BASE_IMAGE={image}", "-t", tag, td], log, timeout=3600)
            built = json.loads(run(["docker", "image", "inspect", tag], log))[0]
            base = json.loads(run(["docker", "image", "inspect", image], log))[0]
            freeze_after = in_image(tag, f"{py} -m pip freeze --all 2>/dev/null | sort", log)
            pip_check = subprocess.run(["docker", "run", "--rm", "--entrypoint", py, tag, "-m", "pip", "check"], capture_output=True, text=True)
            tree = in_image(tag, "cd /testbed && echo HEAD=$(git rev-parse HEAD) && git status --porcelain; echo PORCELAIN_RC=$?", log)
            b, a = set(freeze_before.splitlines()), set(freeze_after.splitlines())
            rec = {**item, "base_id": base_id, "tag": tag, "image_id": built["Id"],
                   "base_layers_preserved": built["RootFS"]["Layers"][: len(base["RootFS"]["Layers"])] == base["RootFS"]["Layers"],
                   "wheels": wheels, "files_sha256": files, "freeze_removed": sorted(b - a), "freeze_added": sorted(a - b),
                   "pip_check_rc": pip_check.returncode, "pip_check": (pip_check.stdout + pip_check.stderr)[-2000:], "worktree_after": tree}
            (od / "image.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
            print(json.dumps({k: rec[k] for k in ("name", "image_id", "base_layers_preserved", "freeze_removed", "freeze_added", "pip_check_rc")},
                             ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
