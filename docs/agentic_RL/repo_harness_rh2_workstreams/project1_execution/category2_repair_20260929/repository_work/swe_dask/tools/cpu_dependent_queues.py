"""串行等待固定的 cpu_wait_for_slot 配置；完整作业始终由 cpu_slot 持槽。"""
import argparse
import json
import signal
import subprocess
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    state = {"schema": "dask_serial_cpu_queues.v1", "started_at": time.time(), "status": "running", "jobs": []}
    child = None
    cancelled = False

    def save():
        temporary = args.plan.parent / "status.json.tmp"
        temporary.write_text(json.dumps(state, indent=2) + "\n")
        temporary.replace(args.plan.parent / "status.json")

    def stop(signum, _frame):
        nonlocal cancelled
        cancelled = True
        state["signal_received"] = signum
        save()
        if child is not None and child.poll() is None:
            child.send_signal(signum)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    save()
    prior = plan.get("wait_for_prior_status")
    if prior:
        state["status"] = "waiting_prior_package_batch_no_cpu_slot"
        save()
        for _ in range(120):
            previous = json.loads(Path(prior).read_text())
            if previous.get("finished_at") is not None and previous["status"] in ("complete", "partial_or_interrupted_needs_readback"):
                state["prior_terminal_status"] = previous["status"]
                break
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline and not cancelled:
                time.sleep(max(0.0, min(1.0, deadline - time.monotonic())))
            if cancelled:
                break
        else:
            state.update(status="prior_batch_wait_limit_no_job_started", finished_at=time.time())
            save()
            return 75
        if cancelled:
            state.update(status="cancelled_before_job", finished_at=time.time())
            save()
            return 130
        state["status"] = "running"
        save()
    for item in plan["configs"]:
        if cancelled:
            break
        config = Path(item)
        row = {"config": str(config), "started_at": time.time()}
        state["jobs"].append(row)
        save()
        with (config.parent / "scheduler.stdout").open("wb") as stdout, (config.parent / "scheduler.stderr").open("wb") as stderr:
            child = subprocess.Popen(["python3", "-B", plan["queue_script"], "--config", str(config)], stdout=stdout, stderr=stderr)
            code = child.wait()
        child = None
        row.update(returncode=code, finished_at=time.time())
        save()
        independent = str(config) in plan.get("continue_on_failure_configs", [])
        if code in (75, 130) or cancelled or (code != 0 and not independent):
            break  # 等待达到上限或取消后，不让下一题再次争抢资源。
    codes = [row.get("returncode") for row in state["jobs"]]
    complete = not cancelled and len(codes) == len(plan["configs"]) and all(code == 0 for code in codes)
    state.update(status="complete" if complete else "partial_or_interrupted_needs_readback", finished_at=time.time())
    save()
    return 0 if complete else 130 if cancelled else 1


if __name__ == "__main__":
    raise SystemExit(main())
