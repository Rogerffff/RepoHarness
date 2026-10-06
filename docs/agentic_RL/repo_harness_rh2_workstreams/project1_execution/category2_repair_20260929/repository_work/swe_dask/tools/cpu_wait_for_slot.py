"""本包有界退让：每次仍经统一 cpu_slot，不提前占槽或后台启动容器。"""
from __future__ import annotations

import argparse
import fcntl
import json
import signal
import subprocess
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    out = args.config.parent
    state = {"scope": "bounded_wait_for_existing_cpu_slot", "started_at": time.time(), "attempts": [], "status": "waiting"}
    child = None
    cancelled = False

    def save() -> None:
        tmp = out / "status.json.tmp"
        tmp.write_text(json.dumps(state, indent=2) + "\n")
        tmp.replace(out / "status.json")

    def stop(signum, _frame):
        nonlocal cancelled
        cancelled = True
        state["signal_received"] = signum
        save()
        if child is not None and child.poll() is None:
            child.send_signal(signum)  # cpu_slot 会继续把信号转给其完整子进程组并保留清理。

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    with (out / "queue.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        save()
        for index in range(1, int(config["max_attempts"]) + 1):
            if cancelled:
                break
            job = config["job_prefix"] + f"-q{index:02d}"
            command = ["python3", config["slot_control"], "--mode", config["mode"], "--package", "swe_dask", "--job", job, "--", *config["command"]]
            attempt = {"job": job, "started_at": time.time()}
            state["attempts"].append(attempt)
            state["status"] = "slot_attempt_or_running"
            save()
            with (out / f"attempt_{index:02d}.stdout").open("wb") as stdout, (out / f"attempt_{index:02d}.stderr").open("wb") as stderr:
                child = subprocess.Popen(command, stdout=stdout, stderr=stderr)
                rc = child.wait()
            child = None
            attempt.update(returncode=rc, finished_at=time.time())
            save()
            if rc != 75:
                state.update(status="command_finished" if rc == 0 else "stopped_needs_diagnosis", returncode=rc, finished_at=time.time())
                save()
                return rc
            state["status"] = "waiting_resource_busy"
            save()
            # 低频、有界等待；收到取消后不再发起新作业。
            deadline = time.monotonic() + int(config["retry_interval_s"])
            while time.monotonic() < deadline and not cancelled:
                time.sleep(max(0.0, min(1.0, deadline - time.monotonic())))
        state.update(status="cancelled" if cancelled else "resource_wait_limit_reached", returncode=130 if cancelled else 75, finished_at=time.time())
        save()
        return int(state["returncode"])


if __name__ == "__main__":
    raise SystemExit(main())
