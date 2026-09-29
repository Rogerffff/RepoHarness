"""在两个 fresh 容器中只改变共享内存容量，保留每次原始输出。"""
from pathlib import Path
import argparse
import json
import subprocess
import time
from datetime import datetime, timezone

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--out", required=True, help="本轮独立输出目录，不覆盖原对照")
ap.add_argument("--run-tag", required=True)
ap.add_argument("--image", default="xingyaoww/sweb.eval.x86_64.project-monai_s_monai-763:latest")
args = ap.parse_args()
if not args.run_tag.replace("_", "").replace("-", "").isalnum():
    ap.error("run-tag 只允许字母、数字、下划线和短横线")
image = args.image
out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
for shm in ["64m", "1g"]:
    name = "rh2probe_" + args.run_tag + "_loader_" + shm
    started = time.monotonic()
    record = {"condition": shm, "run_tag": args.run_tag, "network": "none", "memory": "8g", "cpus": "3", "image_ref": image, "at_utc": datetime.now(timezone.utc).isoformat()}
    try:
        subprocess.run(["docker", "run", "-d", "--name", name, "--shm-size", shm, "--network", "none",
                        "--memory", "8g", "--memory-swap", "8g", "--cpus", "3",
                        image, "sleep", "infinity"], check=True, capture_output=True, timeout=90)
        record["image_id"] = subprocess.check_output(["docker", "inspect", "--format", "{{.Image}}", name], text=True, timeout=15).strip()
        record["shm_bytes"] = int(subprocess.check_output(["docker", "inspect", "--format", "{{.HostConfig.ShmSize}}", name], text=True, timeout=15))
        subprocess.run(["docker", "cp", str(Path(__file__).with_name("dataloader_only.py")), name + ":/tmp/codex_dataloader.py"], check=True, capture_output=True, timeout=30)
        result = subprocess.run(["docker", "exec", name, "bash", "-c",
            "source /opt/miniconda3/bin/activate && conda activate testbed && cd /testbed && timeout -k 10 180 python /tmp/codex_dataloader.py"], capture_output=True, timeout=210)
        (out / (shm + ".stdout.txt")).write_bytes(result.stdout)
        (out / (shm + ".stderr.txt")).write_bytes(result.stderr)
        record["return_code"] = result.returncode
        record["loader_result"] = next((json.loads(ln[len("CODEX_LOADER_RESULT "):]) for ln in result.stdout.decode(errors="replace").splitlines() if ln.startswith("CODEX_LOADER_RESULT ")), None)
    except Exception as exc:
        record["driver_error"] = str(exc)
    finally:
        try:
            cleanup = subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=30)
            record["cleanup_return_code"] = cleanup.returncode
            if cleanup.returncode:
                record["cleanup_error"] = cleanup.stderr.decode(errors="replace")[-500:]
        except Exception as exc:
            record["cleanup_error"] = str(exc)
    record["elapsed_s"] = round(time.monotonic() - started, 3)
    (out / (shm + ".json")).write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(record, ensure_ascii=False), flush=True)
