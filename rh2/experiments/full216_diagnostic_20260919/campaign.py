"""CPU 诊断调度：远端独立运行、分波下载、真实评分 worker、旁路资源观测。"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import hashlib
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import traceback

from worker import append, write_json, best_effort

ACTIVE_WORKERS: list[dict] = []


def stop_worker(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=180)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait(timeout=10)


def command(args: list[str], timeout: float = 30) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout)


def host_sample(root: Path) -> dict:
    mem = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        key, value = line.split(":", 1)
        if key in {"MemTotal", "MemAvailable", "Cached", "SwapFree"}:
            mem[key + "_kib"] = int(value.split()[0])
    sample = {"at": time.time(), "memory": mem, "disk_free_bytes": shutil.disk_usage(root).free,
              "loadavg": list(os.getloadavg()), "containers": []}
    try:
        ps = command(["docker", "ps", "-q", "--filter", "label=rh2.run_id"], 8)
        if ps.returncode:
            raise RuntimeError(ps.stderr)
        ids = ps.stdout.split()
        if ids:
            result = command(["docker", "inspect", *ids], 8)
            if result.returncode:
                raise RuntimeError(result.stderr)
            for obj in json.loads(result.stdout):
                run_id = (obj["Config"].get("Labels") or {}).get("rh2.run_id", "")
                if not run_id.startswith("f216-"):
                    continue
                record = {"id": obj["Id"], "name": obj["Name"], "run_id": run_id,
                          "pid": obj["State"]["Pid"], "oom_killed": obj["State"]["OOMKilled"],
                          "memory_limit": obj["HostConfig"]["Memory"], "shm_bytes": obj["HostConfig"]["ShmSize"]}
                try:
                    lines = Path(f"/proc/{record['pid']}/cgroup").read_text().splitlines()
                    rel = next(x[3:] for x in lines if x.startswith("0::"))
                    cg = Path("/sys/fs/cgroup") / rel.lstrip("/")
                    record["cgroup"] = {k: (cg / k).read_text().strip() for k in
                                        ["memory.current", "memory.peak", "memory.events", "cpu.stat", "io.stat", "pids.current"]}
                except (OSError, StopIteration) as exc:
                    record["cgroup_unavailable"] = str(exc)
                sample["containers"].append(record)
    except (subprocess.TimeoutExpired, RuntimeError, ValueError) as exc:
        sample["docker_observation_error"] = str(exc)
    return sample


def pull_one(image: str, out: Path) -> dict:
    start = time.monotonic()
    result = {"image": image, "started_at": time.time(), "attempts": []}
    for attempt in range(1, 3):
        filename = image.replace("/", "_").replace(":", "_") + f".{attempt}.log"
        with (out / filename).open("w") as log:
            try:
                rc = subprocess.run(["docker", "pull", image], stdout=log, stderr=subprocess.STDOUT, timeout=1500).returncode
            except subprocess.TimeoutExpired:
                rc = 124
        result["attempts"].append({"attempt": attempt, "rc": rc, "log": filename})
        if rc == 0:
            break
    result.update(rc=rc, seconds=time.monotonic() - start)
    if rc == 0:
        ins = command(["docker", "image", "inspect", image], 30)
        if ins.returncode == 0:
            obj = json.loads(ins.stdout)[0]
            result.update(image_id=obj["Id"], repo_digests=obj.get("RepoDigests"), size=obj.get("Size"))
    return result


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def summarize(out: Path, planned: list[dict]) -> dict:
    terminal = {}
    for events in (out / "workers").glob("*/events.jsonl"):
        for e in read_rows(events):
            if e.get("event") == "finished":
                terminal[e["job"]["key"]] = e
    ledger_rows = [r for f in (out / "workers").glob("*/ledger.jsonl") for r in read_rows(f)]
    counts = {}
    for e in terminal.values():
        report = e.get("report") or {}
        key = str(report.get("outcome") or e.get("stage_error") or "no_report")
        counts[key] = counts.get(key, 0) + 1
    result = {"at": time.time(), "planned": len(planned), "finished_calls": len(terminal),
              "ledger_rows": len(ledger_rows), "outcomes": counts,
              "unfinished_jobs": [j for j in planned if j["key"] not in terminal],
              "halt": (out / "HALT.json").read_text() if (out / "HALT.json").exists() else None}
    write_json(out / "summary.json", result)
    return result


def run(ns: argparse.Namespace) -> int:
    root = Path(ns.root)
    out = root / "replay" / ns.name
    out.mkdir(parents=True, exist_ok=False)
    for sub in ("workers", "jobs", "pulls"):
        (out / sub).mkdir()
    halt = out / "HALT.json"
    rows = [json.loads(s) for s in (root / "code/docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest/environment_packages_v0.jsonl").read_text().splitlines()]
    order = {r: i for i, r in enumerate(["python/mypy", "dask/dask", "conan-io/conan", "iterative/dvc",
                                        "pydantic/pydantic", "getmoto/moto", "Project-MONAI/MONAI", "modin-project/modin", "pandas-dev/pandas"])}
    rows.sort(key=lambda x: (order.get(x["repo"], 99), x["instance_id"]))
    if ns.task_ids:
        wanted = set(ns.task_ids.split(","))
        rows = [r for r in rows if r["instance_id"] in wanted]
        if len(rows) != len(wanted):
            raise ValueError("requested tasks are missing")
    jobs = [{"task_id": r["task_id"], "instance_id": r["instance_id"], "image": r["image"],
             "candidate": "noop" if kind == "noop" else "gold-dir:" + str(root / "replay/gold"),
             "kind": kind, "attempt": attempt,
             "key": f"{r['task_id']}|{kind}|{attempt}"}
            for r in rows for attempt in range(1, ns.repeat + 1) for kind in ("noop", "gold")]
    write_json(out / "planned.json", jobs)
    write_json(out / "config.json", {"args": vars(ns), "diagnostic_code_sha256": {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [Path(__file__), Path(__file__).with_name("worker.py")]
    }})
    completed_images = set()
    for wave_index, start in enumerate(range(0, len(rows), ns.wave_size)):
        if halt.exists():
            break
        wave_rows = rows[start:start + ns.wave_size]
        wave_ids = {r["task_id"] for r in wave_rows}
        wave_jobs = [j for j in jobs if j["task_id"] in wave_ids]
        sample = host_sample(root)
        append(out / "host.jsonl", sample)
        if sample["containers"] or sample.get("docker_observation_error"):
            write_json(halt, {"reason": "containers or unknown Docker state before wave", "sample": sample})
            break
        # 只回收本 campaign 已处理镜像的引用；不使用全局 docker prune。
        if sample["disk_free_bytes"] < 200 * 1024**3:
            for image in sorted(completed_images):
                rm = command(["docker", "image", "rm", image], 120)
                append(out / "image_removal.jsonl", {"image": image, "rc": rm.returncode, "stderr": rm.stderr})
            completed_images.clear()
        images = sorted({r["image"] for r in wave_rows})
        with ThreadPoolExecutor(max_workers=2) as pool:
            pulls = list(pool.map(lambda image: pull_one(image, out / "pulls"), images))
        write_json(out / f"pulls_wave_{wave_index}.json", pulls)
        failed_images = {p["image"] for p in pulls if p["rc"]}
        for job in wave_jobs:
            if job["image"] in failed_images:
                append(out / "not_executed.jsonl", {"job": job, "reason": "image_pull_failed", "wave": wave_index})
        wave_jobs = [j for j in wave_jobs if j["image"] not in failed_images]
        if shutil.disk_usage(root).free < 80 * 1024**3:
            write_json(halt, {"reason": "insufficient disk after pulls", "wave": wave_index})
            break
        workers = []
        for slot in range(ns.workers):
            # 同题 noop/gold 留在同一 worker，仍各用 fresh 容器。
            task_ids = {r["task_id"] for r in wave_rows[slot::ns.workers]}
            selected = [j for j in wave_jobs if j["task_id"] in task_ids]
            if not selected:
                continue
            name = f"w{wave_index:02d}-{slot}"
            jobfile = out / "jobs" / (name + ".json")
            write_json(jobfile, selected)
            run_id = f"f216-{ns.name}-{name}"
            log = (out / "workers" / (name + ".log")).open("w")
            proc = subprocess.Popen([sys.executable, str(Path(__file__).with_name("worker.py")),
                                     "--root", str(root), "--out", str(out / "workers" / name),
                                     "--jobs", str(jobfile), "--run-id", run_id, "--halt-file", str(halt)],
                                    stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            record = {"name": name, "run_id": run_id, "proc": proc, "log": log, "started": time.time()}
            workers.append(record)
            ACTIVE_WORKERS.append(record)
        while any(w["proc"].poll() is None for w in workers):
            sample = host_sample(root)
            append(out / "host.jsonl", sample)
            if sample["disk_free_bytes"] < 40 * 1024**3 or sample["memory"]["MemAvailable_kib"] < 2 * 1024**2:
                write_json(halt, {"reason": "host resource low; stop new dispatch", "sample": sample})
            for w in workers:
                proc = w["proc"]
                if proc.poll() is not None:
                    if proc.returncode:
                        write_json(halt, {"reason": "worker failed", "worker": w["name"], "rc": proc.returncode})
                    continue
                statefile = out / "workers" / w["name"] / "status.json"
                state = json.loads(statefile.read_text()) if statefile.exists() else {}
                elapsed = time.time() - state.get("phase_started", w["started"])
                limit = 6600 if state.get("phase") == "attempt" else 240
                if elapsed > limit:
                    write_json(halt, {"reason": "external worker deadline", "worker": w["name"], "state": state})
                    stop_worker(proc)
            time.sleep(10)
        for w in workers:
            w["log"].close()
            ps = command(["docker", "ps", "-aq", "--filter", f"label=rh2.run_id={w['run_id']}"], 20)
            ids = ps.stdout.split()
            append(out / "worker_exit.jsonl", {"worker": w["name"], "rc": w["proc"].returncode,
                                              "residue_ids": ids, "inspect_rc": ps.returncode})
            if w["proc"].returncode or ids or ps.returncode:
                write_json(halt, {"reason": "worker exit or residue", "worker": w["name"], "residue_ids": ids})
            if ids:
                ins = command(["docker", "inspect", *ids], 20)
                # 已确认属于本 worker 的残留，先留证再收口。
                (out / f"residue_{w['name']}.json").write_text(ins.stdout)
                rm = command(["docker", "rm", "-f", *ids], 90)
                append(out / "residue_cleanup.jsonl", {"ids": ids, "rc": rm.returncode, "stderr": rm.stderr})
                check = command(["docker", "ps", "-aq", "--filter", f"label=rh2.run_id={w['run_id']}"], 20)
                append(out / "residue_cleanup.jsonl", {"run_id": w["run_id"], "recheck_rc": check.returncode,
                                                       "remaining_ids": check.stdout.split()})
        ACTIVE_WORKERS.clear()
        completed_images.update(images)
        summarize(out, jobs)
    result = summarize(out, jobs)
    rc = 0 if not result["unfinished_jobs"] and not halt.exists() else 2
    write_json(out / "done.json", {"at": time.time(), "exit_code": rc, "finished": result["finished_calls"]})
    print(json.dumps({"campaign": ns.name, "exit_code": rc, "finished": result["finished_calls"], "planned": len(jobs)}), flush=True)
    return rc


def entry(ns: argparse.Namespace) -> int:
    out = Path(ns.root) / "replay" / ns.name
    def interrupted(sig, frame):
        raise SystemExit(128 + sig)
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, interrupted)
    try:
        return run(ns)
    except BaseException as exc:
        # 覆盖监督器自身的信号/IO异常：独立 session 的 worker 必须一并收口。
        if out.exists():
            try:
                write_json(out / "HALT.json", {"reason": "supervisor failure", "type": type(exc).__name__, "detail": str(exc)})
                (out / "supervisor_failure.txt").write_text(traceback.format_exc())
            except OSError:
                best_effort(traceback.print_exc)
        for w in ACTIVE_WORKERS:
            try:
                stop_worker(w["proc"])
                ps = command(["docker", "ps", "-aq", "--filter", f"label=rh2.run_id={w['run_id']}"], 20)
                ids = ps.stdout.split()
                best_effort(append, out / "emergency_cleanup.jsonl", {"run_id": w["run_id"], "inspect_rc": ps.returncode, "ids": ids})
                if ids:
                    try:
                        ins = command(["docker", "inspect", *ids], 20)
                        best_effort((out / f"emergency_residue_{w['name']}.json").write_text, ins.stdout)
                    except (OSError, subprocess.TimeoutExpired):
                        best_effort(traceback.print_exc)  # inspect 只是留证；已确认归属的 ID 仍须清理。
                    rm = command(["docker", "rm", "-f", *ids], 90)
                    check = command(["docker", "ps", "-aq", "--filter", f"label=rh2.run_id={w['run_id']}"], 20)
                    best_effort(append, out / "emergency_cleanup.jsonl", {"run_id": w["run_id"], "rm_rc": rm.returncode,
                                                                        "recheck_rc": check.returncode, "remaining_ids": check.stdout.split()})
            except BaseException:
                best_effort(traceback.print_exc)
        try:
            summarize(out, json.loads((out / "planned.json").read_text()))
            write_json(out / "done.json", {"at": time.time(), "exit_code": 2, "supervisor_failure": True})
        except (OSError, ValueError):
            best_effort(traceback.print_exc)
        return 2


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--wave-size", type=int, default=32)
    p.add_argument("--task-ids", default="")
    p.add_argument("--repeat", type=int, default=1)
    ns = p.parse_args()
    if ns.workers < 1 or ns.wave_size < 1 or ns.repeat < 1:
        p.error("workers, wave-size and repeat must be positive")
    raise SystemExit(entry(ns))
