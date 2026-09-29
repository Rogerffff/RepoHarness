#!/usr/bin/env python3
"""私有行为对照（2026-09-29，单题闭环试行）：在派生镜像的一次性容器里（不联网）应用候选补丁后跑一段检查脚本。
**不是评分**，只给主审作违例证据，不进解题者材料。镜像与 trial_grade.py 同样取 /work/r2e/derived/*/<题>/facts.json
里排序最前、ok 的那次构建（即当前正式材料的镜像）。

用法（远端，从 rh2/）：
  .venv/bin/python experiments/r2e_lifecycle_20260929/private_check.py --task <instance_id> --patch <文件|none|gold>
      --script <检查脚本.py> --out <结果.json> [--timeout 600] [--user root|agent]
脚本在 /testbed 下以镜像解释器从标准输入运行（/testbed/.venv/bin/python -B -）；gold = /work/r2e/gold/<题>.gold.patch。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import uuid
from pathlib import Path

DERIVED_ROOT = Path("/work/r2e/derived")


def dk(*args: str, timeout: int = 900) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout)


def derived_image(iid: str) -> tuple[str, str | None]:
    for facts in sorted(DERIVED_ROOT.glob(f"*/{iid}/facts.json")):
        d = json.loads(facts.read_text())
        if d.get("ok"):
            return d["derived_image_id"], d.get("recipe_id")
    raise SystemExit(f"{iid}: /work/r2e/derived 下没有 ok 的派生镜像")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--patch", required=True)
    ap.add_argument("--script", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--user", choices=("root", "agent"), default="root")
    ap.add_argument("--cwd", default="/testbed", help="脚本运行目录（缺省 /testbed；要看 /testbed 以外有没有另装一份包时用 /）")
    ap.add_argument("--interp", choices=("python", "bash"), default="python", help="python = 镜像解释器从标准输入读；bash = 按 shell 脚本跑")
    ns = ap.parse_args()
    patch = f"/work/r2e/gold/{ns.task}.gold.patch" if ns.patch == "gold" else ns.patch
    img, recipe = derived_image(ns.task)
    name = f"r2e-pcheck-{uuid.uuid4().hex[:10]}"
    res: dict = {"task": ns.task, "image": img, "recipe_id": recipe, "patch": patch, "script": ns.script,
                 "kind": "private_behavior_check_not_grading", "user": ns.user}
    t0 = time.time()
    try:
        r = dk("run", "-d", "--name", name, "--network", "none", "--label", "rh2.r2e_lifecycle=pcheck",
               "--entrypoint", "sleep", img, "infinity")
        if r.returncode != 0:
            res["verdict"] = f"container_failed:{r.stderr[-300:]}"
            return 1
        dk("exec", name, "git", "config", "--global", "--add", "safe.directory", "/testbed")
        if patch != "none":
            dk("cp", patch, f"{name}:/tmp/cand.patch")
            a = dk("exec", "-w", "/testbed", name, "bash", "-c",
                   "git apply --exclude='r2e_tests/*' -v /tmp/cand.patch 2>&1 | tail -20; echo RH2_APPLY_RC=${PIPESTATUS[0]}")
            res["apply"] = a.stdout[-3000:]
            if "RH2_APPLY_RC=0" not in a.stdout:
                res["verdict"] = "patch_apply_failed"
                return 1
        dk("cp", ns.script, f"{name}:/tmp/check.py")
        dk("exec", name, "chmod", "a+r", "/tmp/check.py")
        user = ["-u", "54321:54321", "-e", "HOME=/tmp"] if ns.user == "agent" else []
        if ns.user == "agent":
            dk("exec", name, "chown", "-R", "54321:54321", "/testbed")
        # 从标准输入读脚本（python -B -）：sys.path[0] 为当前目录，与主审给的命令一致；
        # 直接跑 /tmp/check.py 时 sys.path[0] 是 /tmp，源码在 /testbed 而未装进 venv 的题会 import 失败
        run = (f"cd {ns.cwd} && /testbed/.venv/bin/python -B - < /tmp/check.py" if ns.interp == "python"
               else f"cd {ns.cwd} && export PATH=/testbed/.venv/bin:$PATH && bash /tmp/check.py")
        res.update(cwd=ns.cwd, interp=ns.interp)
        r = dk("exec", *user, "-w", "/testbed", name, "timeout", str(ns.timeout), "bash", "-c", run, timeout=ns.timeout + 60)
        res.update(rc=r.returncode, stdout=r.stdout[-8000:], stderr=r.stderr[-4000:], verdict="ran")
        return 0
    finally:
        dk("rm", "-f", name)
        res["seconds"] = round(time.time() - t0, 1)
        Path(ns.out).parent.mkdir(parents=True, exist_ok=True)
        Path(ns.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps({k: res.get(k) for k in ("task", "patch", "verdict", "rc", "seconds")}, ensure_ascii=False))
        print(res.get("stdout", "")[-1500:])


if __name__ == "__main__":
    sys.exit(main())
