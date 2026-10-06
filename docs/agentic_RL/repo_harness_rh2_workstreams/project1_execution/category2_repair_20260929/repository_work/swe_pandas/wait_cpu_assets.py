"""准备作业外等待共享名额；只对忙态75重试，不绕过cpu_slot或自动重试失败。"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import subprocess
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", required=True)
    parser.add_argument("--controller", required=True)
    parser.add_argument("--instance-id", required=True)
    parser.add_argument("--max-attempts", type=int, default=30)
    parser.add_argument("--wheel-source", help="可选的本包私有预恢复 wheel 目录")
    args = parser.parse_args()
    package = Path(args.package_root)
    manifest = json.loads((package / "cpu_preparation_input_manifest.json").read_text())
    for ref in manifest["files"]:
        observed = "sha256:" + hashlib.sha256((package / ref["package_path"]).read_bytes()).hexdigest()
        if observed != ref["sha256"]:
            raise RuntimeError("准备快照发生变化: " + ref["package_path"])
    attempts = package / "prepare_attempts.jsonl"
    for _ in range(args.max_attempts):
        job = "pandas" + args.instance_id.rsplit("-", 1)[-1] + "-assets-" + secrets.token_hex(6)
        out = package / "outputs" / job
        command = ["python3", args.controller, "--mode", "prepare", "--package", "swe_pandas", "--job", job,
                   "--", "python3", str(package / "prepare_cpu_assets.py"),
                   "--input", str(package / "cpu_asset_input.json"), "--output", str(out),
                   "--instance-id", args.instance_id]
        if args.wheel_source:
            command.extend(["--wheel-source", args.wheel_source])
        print("prepare attempt:", job, flush=True)
        result = subprocess.run(command)
        record = {"job_id": job, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                  "exit_code": result.returncode, "output": str(out), "instance_id": args.instance_id}
        with attempts.open("a") as handle:
            handle.write(json.dumps(record) + "\n")
        if result.returncode == 0:
            (package / "prepare_result.json").write_text(json.dumps(record, indent=2) + "\n")
            return
        if result.returncode != 75:
            (package / "prepare_result.json").write_text(json.dumps(record, indent=2) + "\n")
            raise SystemExit(result.returncode)
        # wrapper已经退出，未持有作业锁；间隔重试，避免轮询占用共享名额。
        time.sleep(180)
    (package / "prepare_result.json").write_text(json.dumps({"status": "still_busy_after_bounded_wait",
                                                            "instance_id": args.instance_id}, indent=2) + "\n")
    raise SystemExit(75)


if __name__ == "__main__":
    main()
