"""本批本地增量收集器；不派发任务，不修改远端，不同步镜像和 wheel。"""
import datetime
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "runs/swegym_cpu_preprobe_20260929"
cfg = json.loads((OUT / "connection.local.json").read_text())
ssh = f"ssh -i {Path(cfg['ssh_key']).expanduser()} -p {cfg['ssh_port']} -o BatchMode=yes -o IdentitiesOnly=yes -o ConnectTimeout=15"
remote = f"{cfg['ssh_user']}@{cfg['ssh_host']}:{cfg['remote_root']}/"
deadline = time.monotonic() + 12 * 3600
while time.monotonic() < deadline and not (OUT / "stop_sync").exists():
    cmd = ["rsync", "-az", "--exclude=code_v1/", "--exclude=cc/", "--exclude=context/",
           "--exclude=wheels/", "--exclude=assets/", "--exclude=*.whl", "--exclude=*.tgz",
           "-e", ssh, remote, str(OUT / "remote") + "/"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        record = {"at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  "returncode": result.returncode, "stderr": result.stderr[-1500:]}
    except subprocess.TimeoutExpired:
        record = {"at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "error": "sync_timeout"}
    (OUT / "sync_status.json").write_text(json.dumps(record, indent=2) + "\n")
    with (OUT / "sync_events.jsonl").open("a") as handle:
        handle.write(json.dumps(record) + "\n")
    time.sleep(45)
