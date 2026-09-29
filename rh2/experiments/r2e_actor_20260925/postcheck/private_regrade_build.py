"""R2E 候选的私有复核（不计入 reward，不交给求解者）：在派生镜像的一次性容器里（root、不联网）应用候选补丁，
可选地先执行一条构建命令，再像评分那样放入隐藏测试（r2e_tests/ 与 run_tests.sh）并运行，用评分同一解析器与期望逐键比对。

    .venv/bin/python private_regrade_build.py --image <派生镜像 ID> --private-dir <私有包目录> --patch <候选.patch> \
        [--build-cmd ".venv/bin/python setup.py build_ext --inplace"] --out <结果.json>

用途：判断"只改编译扩展源码（如 .pyx）的修复"在构建之后是否正确。正式评分不重新编译（RH2_INSTALL_SKIPPED=1），
所以这类修复的 reward 与"构建后是否正确"是两件事，这里只回答后者。
与正式评分的差异：以 root 运行（正式评分以 uid 54322），不走 grader 的阶段、预算与账本。结论单独成列，不覆盖 reward。
退出码：0 = 逐键与期望一致，1 = 不一致，2 = 补丁、构建或运行出错。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import uuid
from pathlib import Path

from repoharness2.envpack.r2e_parsers import normalize_status_map, parse_log_pytest


def dk(*args: str, input_bytes: bytes | None = None, timeout: int = 1800) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], input=input_bytes, capture_output=True, timeout=timeout)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--private-dir", required=True)
    ap.add_argument("--patch", default=None)
    ap.add_argument("--build-cmd", default=None)
    ap.add_argument("--out", required=True)
    ns = ap.parse_args()
    priv = Path(ns.private_dir)
    name = f"rh2-private-regrade-{uuid.uuid4().hex[:10]}"
    rec: dict = {"image": ns.image, "private_dir": str(priv), "patch": ns.patch, "build_cmd": ns.build_cmd, "user": "root"}
    rc = 2
    try:
        run = dk("run", "-d", "--name", name, "--network", "none", "--label", "rh2.b_r2e=private_regrade",
                 "--entrypoint", "sleep", ns.image, "infinity")
        if run.returncode != 0:
            rec["error"] = run.stderr.decode(errors="replace")[-400:]
            return 2
        if ns.patch:
            app = dk("exec", "-i", "-w", "/testbed", name, "git", "apply", "-v", "-", input_bytes=Path(ns.patch).read_bytes())
            rec["apply_rc"] = app.returncode
            rec["apply_tail"] = (app.stdout + app.stderr).decode(errors="replace")[-600:]
            if app.returncode != 0:
                return 2
        if ns.build_cmd:
            b = dk("exec", "-w", "/testbed", name, "bash", "-c", ns.build_cmd)
            rec["build_rc"] = b.returncode
            out = (b.stdout + b.stderr).decode(errors="replace")
            rec["build_tail"] = out[-1500:]
            rec["build_cythonized"] = [ln for ln in out.splitlines() if "Cythonizing" in ln or "cythoning" in ln.lower()][:20]
            if b.returncode != 0:
                return 2
        dk("exec", name, "rm", "-rf", "/testbed/r2e_tests", "/testbed/run_tests.sh")
        for src, dst in ((priv / "hidden_tests", "/testbed/r2e_tests"), (priv / "run_tests.sh", "/testbed/run_tests.sh")):
            cp = dk("cp", str(src), f"{name}:{dst}")
            if cp.returncode != 0:
                rec["error"] = f"docker cp {src.name}: " + cp.stderr.decode(errors="replace")[-300:]
                return 2
        t = dk("exec", "-w", "/testbed", name, "bash", "run_tests.sh")
        log = (t.stdout + t.stderr).decode(errors="replace")
        rec["tests_rc"] = t.returncode
        rec["log_tail"] = log[-3000:]
        observed = normalize_status_map(parse_log_pytest(log))
        expected = normalize_status_map(json.loads((priv / "expected_output.json").read_text(encoding="utf-8")))
        diff = {k: {"expected": expected.get(k), "observed": observed.get(k)}
                for k in sorted(set(expected) | set(observed)) if expected.get(k) != observed.get(k)}
        rec["expected_total"] = len(expected)
        rec["expected_match"] = sum(1 for k, v in expected.items() if observed.get(k) == v)
        rec["mismatched"] = diff
        rc = 0 if not diff and observed else 1
        return rc
    finally:
        dk("rm", "-f", name, timeout=120)
        rec["exit_code"] = rc
        Path(ns.out).parent.mkdir(parents=True, exist_ok=True)
        Path(ns.out).write_text(json.dumps(rec, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(json.dumps({"patch": ns.patch, "build": bool(ns.build_cmd), "build_rc": rec.get("build_rc"),
                          "match": f"{rec.get('expected_match')}/{rec.get('expected_total')}",
                          "mismatched": sorted(rec.get("mismatched", {})), "exit_code": rc}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
