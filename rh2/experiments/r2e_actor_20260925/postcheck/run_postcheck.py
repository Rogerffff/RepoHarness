"""R2E 候选的事后复核入口（不交给求解者，不改评分）：在派生镜像的一次性容器里（root、不联网）应用候选补丁，
用 /testbed/.venv 的 python 运行对应的检查脚本，保存完整输出与判定。

    python run_postcheck.py --task numpy__18b7cd9d  --image <派生镜像 ID> --patch <候选.patch> --out <结果.json>
    python run_postcheck.py --task aiohttp__61833518 --image <派生镜像 ID> --patch <候选.patch> --out <结果.json>
    python run_postcheck.py --task aiohttp__1c1c0ea3 --image <派生镜像 ID> --patch <候选.patch> --out <结果.json>
    python run_postcheck.py --task coveragepy__97997d2c --image <派生镜像 ID> --patch <候选.patch> --out <结果.json>

--patch 省略时检查 base（不应用补丁）。退出码：0 = 通过，1 = 未通过，2 = 补丁应用失败或运行出错。
原始 reward 仍以评分账本为准；本检查的结论单独成列，不覆盖 reward。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHECKS = {"numpy__18b7cd9d": HERE / "numpy_18b7cd9d_behavior.py", "aiohttp__61833518": HERE / "aiohttp_61833518_c3.py",
          "aiohttp__1c1c0ea3": HERE / "aiohttp_1c1c0ea3_cleanup_error.py", "coveragepy__97997d2c": HERE / "coveragepy_97997d2c_paths.py"}


def dk(*args: str, input_bytes: bytes | None = None, timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], input=input_bytes, capture_output=True, timeout=timeout)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True, choices=sorted(CHECKS))
    ap.add_argument("--image", required=True)
    ap.add_argument("--patch", default=None)
    ap.add_argument("--out", required=True)
    ns = ap.parse_args()
    name = f"rh2-postcheck-{uuid.uuid4().hex[:10]}"
    rec: dict = {"task": ns.task, "image": ns.image, "patch": ns.patch, "check_script": CHECKS[ns.task].name}
    rc = 2
    try:
        run = dk("run", "-d", "--name", name, "--network", "none", "--label", "rh2.b_r2e=postcheck", "--entrypoint", "sleep", ns.image, "infinity")
        if run.returncode != 0:
            rec["error"] = run.stderr.decode(errors="replace")[-400:]
            return 2
        if ns.patch:
            patch = Path(ns.patch).read_bytes()
            app = dk("exec", "-i", "-w", "/testbed", name, "git", "apply", "-v", "-", input_bytes=patch)
            rec["apply_rc"] = app.returncode
            rec["apply_tail"] = (app.stdout + app.stderr).decode(errors="replace")[-600:]
            if app.returncode != 0:
                return 2
        res = dk("exec", "-i", "-w", "/tmp", name, "/testbed/.venv/bin/python", "-", input_bytes=CHECKS[ns.task].read_bytes())
        out = res.stdout.decode(errors="replace")
        rec["check_rc"] = res.returncode
        rec["stderr_tail"] = res.stderr.decode(errors="replace")[-1500:]
        line = next((ln for ln in out.splitlines() if ln.startswith("RH2_POSTCHECK=")), None)
        rec["result"] = json.loads(line.split("=", 1)[1]) if line else None
        if rec["result"] is None:
            return 2
        rc = 0 if rec["result"]["verdict"] == "pass" else 1
        return rc
    finally:
        dk("rm", "-f", name, timeout=120)
        rec["exit_code"] = rc
        Path(ns.out).parent.mkdir(parents=True, exist_ok=True)
        Path(ns.out).write_text(json.dumps(rec, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        verdict = (rec.get("result") or {}).get("verdict")
        print(json.dumps({"task": ns.task, "patch": ns.patch, "verdict": verdict, "failed": (rec.get("result") or {}).get("failed"),
                          "exit_code": rc}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
