"""本批宿主只读资源观察；缺失读数保留 null，不解释为零。"""
import argparse
import json
import os
import shutil
import subprocess
import time
from pathlib import Path


def call(args):
    p = subprocess.run(args, capture_output=True, text=True, timeout=20)
    return {"rc": p.returncode, "stdout": p.stdout, "stderr": p.stderr[-500:]}


def read(path):
    try:
        return Path(path).read_text().strip()
    except OSError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    while True:
        tick = {"at": time.time(), "loadavg": read("/proc/loadavg"),
                "meminfo": read("/proc/meminfo"), "disk_free": shutil.disk_usage("/work").free,
                "containers": []}
        try:
            listing = call(["docker", "ps", "-q"])
            tick["docker_ps_rc"] = listing["rc"]
            for cid in listing["stdout"].split():
                info = call(["docker", "inspect", cid])
                if info["rc"]:
                    tick["containers"].append({"id": cid, "inspect_error": info})
                    continue
                d = json.loads(info["stdout"])[0]
                pid = d["State"]["Pid"]
                cg = read(f"/proc/{pid}/cgroup") if pid else None
                cgpath = next((line[3:] for line in (cg or "").splitlines() if line.startswith("0::")), None)
                item = {"id": d["Id"], "name": d["Name"], "state": d["State"],
                        "limits": {k: d["HostConfig"].get(k) for k in
                                   ("Memory", "NanoCpus", "PidsLimit", "ShmSize", "Tmpfs")},
                        "cgroup_path": cgpath}
                if cgpath:
                    base = Path("/sys/fs/cgroup") / cgpath.lstrip("/")
                    item["cgroup"] = {k: read(base / k) for k in
                                      ("memory.current", "memory.peak", "memory.events", "pids.current",
                                       "pids.peak", "pids.events", "cpu.stat")}
                tick["containers"].append(item)
        except Exception as exc:
            tick["error"] = repr(exc)
        with dest.open("a") as f:
            f.write(json.dumps(tick) + "\n")
        time.sleep(15)


if __name__ == "__main__":
    main()
