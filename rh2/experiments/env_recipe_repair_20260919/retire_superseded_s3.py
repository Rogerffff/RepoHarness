"""等旧PID512对照当前driver清理完成后，停止已暂停的父派发器；不杀评分过程。"""

import json
import os
from pathlib import Path
import signal
import subprocess
import time

ROOT = Path("/work/env_recipe_repair_20260919")
BATCH = ROOT / "modin_s3_compat_v1"
RUN = BATCH / "tasks/modin-project__modin-6937/noop"
UNIT = "rh2-envrepair-modin-s3-compat-v1-20260919.service"


def main():
    deadline = time.monotonic() + 7200
    while time.monotonic() < deadline:
        footer = None
        log = RUN / "driver.log"
        for line in log.read_text().splitlines() if log.exists() else []:
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict) and "manager_close" in value:
                footer = value
        if footer is None:
            time.sleep(10)
            continue
        assert not footer.get("halted") and not footer.get("cleanup_failures"), footer
        assert not footer["manager_close"].get("containers_open"), footer
        assert not footer["manager_close"].get("cleanup_failures"), footer
        ledger = json.loads((RUN / "ledger.jsonl").read_text())
        assert ledger["cleanup"]["removed"] and ledger["stage_error"] is None, ledger
        run_id = "er19-modin_s3_compat_v1-modin-project__modin-6937-noop"
        assert not subprocess.check_output(
            ["docker", "ps", "-aq", "--filter", "label=rh2.run_id=" + run_id],
            text=True, timeout=30).strip()
        pid = int(subprocess.check_output(
            ["systemctl", "show", UNIT, "-p", "MainPID", "--value"], text=True, timeout=30))
        proc = Path("/proc") / str(pid)
        assert pid > 1 and "/modin_s3_compat_v1/run_compat_cases.py" in proc.joinpath("cmdline").read_bytes().decode()
        children = proc.joinpath("task", str(pid), "children").read_text().split()
        if any(Path("/proc", child).exists() and "State:\tZ" not in Path("/proc", child, "status").read_text()
               for child in children):
            time.sleep(1)
            continue
        record = {
            "at": time.time(), "pid": pid, "unit": UNIT,
            "completed_run": "tasks/modin-project__modin-6937/noop", "driver_close": footer,
            "reason": "PID512 failure reproduced; remaining cases superseded by isolated PID1024 v2",
            "not_run": ["6937/gold", "5940/noop", "5940/gold"],
            "scope": "dispatcher only, after active driver exit and actual container removal",
        }
        (BATCH / "superseded.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
        (BATCH / "failed.json").write_text(json.dumps({
            "at": time.time(), "disposition": "superseded", "error": record["reason"],
            "remaining_cases_not_run": record["not_run"],
        }, ensure_ascii=False, indent=2) + "\n")
        os.kill(pid, signal.SIGTERM)
        os.kill(pid, signal.SIGCONT)
        print(json.dumps(record, ensure_ascii=False), flush=True)
        return
    raise TimeoutError("old driver did not finish safely; held dispatcher remains for inspection")


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:
        (ROOT / "retire_superseded_s3_failed.json").write_text(
            json.dumps({"at": time.time(), "error": repr(exc)}, ensure_ascii=False, indent=2) + "\n")
        raise
