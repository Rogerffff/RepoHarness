"""在一个CPU名额内串行调用冻结的私有行为入口；不生成reward。"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--job", required=True)
    args = parser.parse_args()
    release = args.root / "releases/cat2-cpu-r2e064065-swe5-20261003-v1"
    manifest = release / "manifest.json"
    assert hashlib.sha256(manifest.read_bytes()).hexdigest() == "282021962a92b510f077385660ac56acedcd7fac1d97e63db3baa98e4dcc057f"
    relative = "rh2/experiments/swegym_cpu_preprobe_20260929/private_behavior.py"
    runner = release / "repo" / relative
    assert hashlib.sha256(runner.read_bytes()).hexdigest() == json.loads(manifest.read_text())["files"][relative]["sha256"]
    out = args.root / "packages/swe_mypy/attempts" / args.job
    out.mkdir(parents=True, exist_ok=False)
    python = args.root / "runtime_cpu_v2/rh2/.venv/bin/python"
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(release / "repo/rh2/src")}

    def interrupted(signum, _frame):
        raise KeyboardInterrupt(f"signal {signum}")

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    for iid in ("python__mypy-10174", "python__mypy-15184"):
        spec = args.root / "packages/swe_mypy/private_calibration_v1" / (iid + ".json")
        with (out / (iid + ".log")).open("wb") as log:
            proc = subprocess.Popen([str(python), "-B", str(runner), str(spec), "--out", str(out / iid)],
                                    stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True)
            try:
                rc = proc.wait(timeout=1800)
            except BaseException:
                if proc.poll() is None:
                    os.killpg(proc.pid, signal.SIGTERM)
                    proc.wait(timeout=300)
                raise
        if rc:
            raise RuntimeError(f"{iid}: private runner rc={rc}; stop and audit cleanup")


if __name__ == "__main__":
    main()
